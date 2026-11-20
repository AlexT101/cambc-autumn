#include "turn_order.h"
#include <algorithm>
#include <array>
#include <bit>
#include <cstdio>
#include <tuple>
#include <utility>
#include <vector>
#include "../params.h"
#include "comms.h"
#include "follow.h"
#include "idle_priority.h"
#include "safety.h"
#include "world.h"

namespace aph {

namespace {

// One scale for every champion, higher acting first, after Fish's (research/fish-2026-11-05/TEAM.md):
// contact when the enemy starts next round, late, idle (idle_priority.h), dead, contact when we start
// it; two bands above them. Late shifts an idle value below every idle one; contact's 17 threat levels
// put the most threatened outermost. A kill or a cancelled channel outranks saving a life; each needs
// us to act before some enemy next round.
enum Band : int { none, protect, kill };
constexpr int band_width = 10000;
constexpr int dead_priority = idle_top + 1;
// An enemy yet to act this round moves before our next turn anyway: acting before its turn next
// round denies it only a second one.
constexpr float unacted_share = 0.5f;

struct Wish {
    int band = none;
    float value = 0;
    int target = -1; // a kill offer's enemy (index), when it has acted
    float need = 0;  // our blow on it, after `taken`

    void offer(int b, float v, int t = -1, float n = 0) {
        if (b > band || (b == band && v > value)) band = b, value = v, target = t, need = n;
    }
    int priority() const { return band * band_width + std::clamp(static_cast<int>(value), 0, band_width - 1); }
};

// Only the order within the team matters, so a raw priority is renumbered by a code that keeps the
// order of every value it can take: contact, late, idle and dead in [lowest_raw, highest_raw]; in a band,
// int(a life, tribute or recall value + 15 x gems), or of half a kill's, which is 0, 7 or 10 mod 15
// (0 or 10 when protecting), with the clamped band_width - 1 above all.
constexpr int contact_levels = 17;
constexpr int idle_span = idle_top - idle_lowest + 1;
constexpr int contact_first = dead_priority + 1;
constexpr int contact_last = idle_lowest - idle_span - 1;
constexpr int lowest_raw = contact_last - (contact_levels - 1);
constexpr int highest_raw = contact_first + contact_levels - 1;
constexpr int idle_codes = highest_raw - lowest_raw + 1;
constexpr int protect_code(int v) { return 2 * (v / 15) + (v % 15 >= 10); }
constexpr int kill_code(int v) { return 3 * (v / 15) + (v % 15 >= 7) + (v % 15 >= 10); }
constexpr int protect_codes = protect_code(band_width - 2) + 2;
constexpr int rank_code(int raw) {
    if (raw < band_width) return std::clamp(raw, lowest_raw, highest_raw) - lowest_raw;
    const bool protecting = raw < 2 * band_width;
    const int v = raw - (protecting ? band_width : 2 * band_width);
    if (protecting) return idle_codes + (v == band_width - 1 ? protect_codes - 1 : protect_code(v));
    return idle_codes + protect_codes + (v == band_width - 1 ? kill_code(band_width - 2) + 1 : kill_code(v));
}
static_assert(params::turn_gem_value == 15 && static_cast<int>(params::turn_life_value) % 15 == 0
              && static_cast<int>(params::turn_tribute_value) % 15 == 10 && static_cast<int>(params::turn_recall_value) % 15 == 0
              && unacted_share == 0.5f && static_cast<int>(params::turn_life_value * unacted_share) % 15 == 0);
static_assert(rank_code(band_width - 1) < rank_code(band_width));

// The latest rank set_turn_order chose: kept when it skips a turn short of fuel.
int turn_rank = 0;
bool turn_rank_valid = false; // set_turn_order has chosen a rank this match

// Above the payload, the code relative to raw 0's, then 7 - our index so that equal codes still tie
// by id. Never 0 (comms reads 0 as no payload), raw 0 included.
std::int32_t packed_priority(int raw, int index, std::uint32_t payload) {
    const int rank = (rank_code(raw) - rank_code(0)) * 8 + (7 - index);
    return rank * (1 << priority_payload_bits) + static_cast<std::int32_t>(payload);
}
static_assert(((rank_code(3 * band_width - 1) - rank_code(0)) * 8 + 7) < 1 << (31 - priority_payload_bits));

struct Enemy {
    const ChampionBelief* belief;
    float health; // shield included
};

// Visible enemies still alive after our turn, with their health and shield now. One raw read
// each: every SDK accessor reads the whole record again.
const std::vector<Enemy>& live_enemies(const World& world) {
    static std::vector<Enemy> out; // kept across turns: growing it reallocates
    out.clear();
    if (!world.enemy_seen()) return out;
    static cambc::detail::champion_info info;
    for (const auto& e : world.enemies) {
        if (!e.alive || !e.visible) continue;
        // A dead champion reads as off the map.
        if (cambc::detail::sdk_champion(static_cast<std::uint32_t>(e.handle), &info) != 0 || info.x < 0 || info.y < 0) continue;
        out.push_back({&e, info.health + (e.shield > 0 ? shield_value(e.handle) : 0.0f)});
    }
    return out;
}

// Ourselves as we end the turn, after moving. Only the fields read here are set: copying the
// whole belief would copy its bitboards.
ChampionBelief& live_self(const World& world, cambc::champion_state& state) {
    static ChampionBelief b;
    const auto& now = world.me();
    b.handle = now.handle;
    b.type = now.type;
    b.side = now.side;
    b.index = now.index;
    b.is_self = true;
    b.visible = now.visible;
    const auto& info = my_record();
    state = cambc::champion_state::from_bits_retain(info.state);
    // Ren's reflected damage can kill us in our own turn: dead, we read as off the map.
    b.alive = now.alive && info.x >= 0;
    b.max_health = info.max_health;
    b.pos = {info.x, info.y};
    b.health = info.health;
    b.strength = info.strength;
    b.focus = info.focus;
    b.taken = now.taken;
    b.dealt = now.dealt;
    b.camp_dealt = now.camp_dealt;
    // Absorbed before our health by every blow before our next turn: it expires only at its start.
    b.shield = now.shield_slot >= 0 ? shield_value(now.handle) : 0.0f;
    return b;
}

// What our strikes next round read, cooldowns restarted by casts included: only needed with an
// enemy in sight.
void read_strike(const World& world, ChampionBelief& b) {
    b.gems = static_cast<int>(my_gems());
    b.scale = damage_scale(b.facts().passive, b.health, b.max_health) * b.dealt;
    for (std::uint32_t s = 0; s < 2; ++s) {
        static std::int32_t cooldown;
        ok(cambc::detail::sdk_champion_cooldown(my_handle(), s, &cooldown));
        b.ready_round[s] = world.round + std::max(0, static_cast<int>(cooldown));
    }
}

bool we_start(const World& world, int round) { return world.map().team_a == (round % 2 == 1); }

// Fish's contested camp: an awake striking member has us in range, and a visible enemy is within its
// range + 1 of an awake striking member of the same group.
bool contested_camp(const World& world, const ChampionBelief& self, const std::vector<Enemy>& enemies) {
    const auto& groups = world.map().groups;
    bool found = false;
    world.each_stirring([&](int g) {
        if (found || groups[g].strength <= 0) return;
        const auto& c = world.camps[g];
        if (c.awake != Awake::awake) return;
        const auto& members = groups[g].members;
        bool in = false, near = false;
        for (std::size_t i = 0; i < members.size(); ++i) {
            const auto& m = members[i];
            if (m.strength <= 0 || c.health[i] <= 0 || c.member_asleep(i)) continue;
            in = in || in_square(self.pos, m.pos, m.reach);
            for (const auto& e : enemies) near = near || in_square(e.belief->pos, m.pos, m.reach + 1);
        }
        found = in && near;
    });
    return found;
}

// Fish's contact: a visible enemy within its reach of us or a visible ally, or within ours of us;
// reach 3 ranged, 2 melee (a walk and a blow). Seats us next round outermost by threat, j sixteenths
// of our health and shield that the enemies' blows take: first (most threatened first) when we start
// the round, last (most threatened last) when they do, so the pair of turns straddles the boundary.
constexpr int no_contact = -1 << 30;
int threat_level(const ChampionBelief& self, float health, float incoming) {
    const float effective = health + self.shield;
    return effective > 0 ? std::min(contact_levels - 1, static_cast<int>(std::floor(16 * incoming * self.taken / effective))) : contact_levels - 1;
}
int contact_priority(const World& world, const ChampionBelief& self, float health, const std::vector<Enemy>& enemies) {
    const auto reach = [](const ChampionBelief& c) { return c.facts().ranged ? 3 : 2; };
    const int own = reach(self);
    bool in_reach = false;
    float incoming = 0;
    for (const auto& [e, left] : enemies) {
        const int d = dist(self.pos, e->pos), theirs = reach(*e);
        in_reach = in_reach || d <= std::max(theirs, own);
        for (const auto& a : world.allies)
            in_reach = in_reach || (!a.is_self && a.alive && a.visible && dist(a.pos, e->pos) <= theirs);
        if (d > Strike::max_reach) continue;
        if (const int turn = next_turn_round(world, *e); turn <= world.round + 1) incoming += strike(*e, turn).at(d);
    }
    if (!in_reach) return no_contact;
    return we_start(world, world.round + 1) ? contact_first + threat_level(self, health, incoming) : contact_last - threat_level(self, health, incoming);
}

int seat_priority(const World& world, const ChampionBelief& self, float health, const std::vector<Enemy>& enemies);

// The priority with no band bid, for a live `self` as read_strike leaves it.
int plain_priority(const World& world, Safety& safety, const ChampionBelief& self, const std::vector<Enemy>& enemies) {
    // On our spawn the turn end heals us to full first (rules rounds.turn_end).
    const float health = test(world.map().ally_spawn, self.pos) ? self.max_health : self.health;
    // Fish's mode selector (TEAM.md 1d): late at a contested camp before contact, contact before idle.
    const bool contested = !enemies.empty() && contested_camp(world, self, enemies);
    if (!contested && !enemies.empty()) {
        if (const int raw = seat_priority(world, self, health, enemies); raw != no_contact) return raw;
        if (const int raw = contact_priority(world, self, health, enemies); raw != no_contact) return raw;
    }
    // At a contested camp we act after every idle ally: the camps' tie hits go to the enemy.
    const int late = contested ? idle_span : 0;
    const float hit = safety.tie_hit(self.pos);
    int enemy_dist = 99; // only ranks us with no camp hit; one out of sight from the tiles it may be on
    if (hit <= 0) {
        for (const auto& e : world.enemies)
            if (e.alive && e.visible) enemy_dist = std::min(enemy_dist, dist(self.pos, e.pos));
        // idle_priority reads enemy_dist / 2, up to max_hits: the gap is searched by those steps, as the
        // even distance of its step.
        for (const auto& e : world.enemies) {
            const int steps = std::min(enemy_dist / 2, max_hits) - 1; // the farthest step that ranks nearer
            if (steps < 0 || !e.alive || e.visible || !e.tracked || !possible_within(e, self.pos, 2 * steps + 1) || !safety.credible_unseen(e))
                continue;
            int lo = 0, hi = steps;
            while (lo < hi) {
                const int mid = (lo + hi) / 2;
                if (possible_within(e, self.pos, 2 * mid + 1)) hi = mid;
                else lo = mid + 1;
            }
            enemy_dist = 2 * lo;
        }
    }
    const int raw = idle_priority(health, self.shield, hit, static_cast<int>(my_gems()), enemy_dist);
    world.throw_if_stale();
    return raw - late;
}

// A champion's index in next round's turns at team rank `rank`, as World::slot counts them: the
// teams alternate, the larger one's extra champions last.
int next_slot(const World& world, bool ally, int rank) {
    const bool first = ally == we_start(world, world.round + 1);
    const int others = static_cast<int>(ally ? world.enemies.size() : world.allies.size());
    return rank < others ? 2 * rank + (first ? 0 : 1) : others + rank;
}

// Ally `a`'s rank next round with us at packed priority `ours` (packed_priority, no payload): the
// allies whose next priority outranks its own. Each acts by its next priority as last read, which
// is final once it has acted this round. Our packed priorities differ above the payload; ties are
// with allies yet to publish one.
int ally_next_rank(const World& world, const ChampionBelief& a, std::int32_t ours) {
    const auto order = [&](const ChampionBelief& c) { return (c.is_self ? ours : c.next_priority) >> priority_payload_bits; };
    const int own = order(a);
    int rank = 0;
    for (const auto& b : world.allies)
        if (&b != &a) rank += order(b) > own || (order(b) == own && b.handle < a.handle);
    return rank;
}

// A lower bound on `e`'s rank next round: 0 while its priority can change; else the enemies whose
// next priority is final and outranks it. Final once it has acted this round, or if its team never
// changes priority.
int enemy_next_rank(const World& world, const ChampionBelief& e) {
    // Read this round after its turn: one first seen after our move keeps an older read.
    const auto settled = [&](const ChampionBelief& c) {
        return !world.enemy_priorities_change || (c.visible && c.acted && c.priority_round == world.round);
    };
    if (!settled(e)) return 0;
    int rank = 0;
    for (const auto& o : world.enemies)
        rank += &o != &e && settled(o) && (o.next_priority > e.next_priority || (o.next_priority == e.next_priority && o.handle < e.handle));
    return rank;
}

// Whether we act before slot `their` next round (an enemy's at its earliest, enemy_next_rank) at
// packed priority `ours` (what set_turn_order would set, no payload): our rank by the allies' next
// priorities.
bool can_act_before(const World& world, int their, std::int32_t ours) {
    return next_slot(world, true, ally_next_rank(world, world.me(), ours)) < their;
}

// For an engaged pair our priority only picks whether we act before the enemy next round (ahead) or
// after it. Until our next turn that is: if it has acted, us then it (our double) or it then us; if
// not, it, us, it or it, it, us (its double). On a gap with equal walks ahead is never worse for us,
// and it decides a blow only where the gap meets the next turn's real reach (Strike: walk, dash,
// reset, spells). Elsewhere 464's alternating doubles stay: they beat always-first. The contact
// seat for our start is ahead in our rounds; in theirs only above its rank: exact once it has acted,
// else its last read rank, even where 464 may pin it first (skipping those cost more than the misses).
int seat_priority(const World& world, const ChampionBelief& self, float health, const std::vector<Enemy>& enemies) {
    const auto& role = chase_role;
    if (!role.fleeing && !role.struck) return no_contact;
    const int next = world.round + 1;
    const bool ours = we_start(world, next);
    const int own = strike(self, next).reach;
    float incoming = 0;
    bool ahead = false;
    for (const auto& [e, left] : enemies) {
        const int g = dist(self.pos, e->pos);
        if (g > Strike::max_reach + 1 || turn_lost(*e) || e->teleport_pending() || test(world.map().enemy_spawn, e->pos)) continue;
        const bool acted = e->acted;
        const int theirs = strike(*e, next).reach;
        if (g <= Strike::max_reach) incoming += strike(*e, acted ? next : world.round).at(g);
        bool decides = false;
        if (role.fleeing) {
            // Its blow on its next turn after ours: from g if it has acted; else from where its turn
            // this round leaves it (a ranged blow from here, or a walk in).
            const int from = acted ? g : (e->facts().ranged && g <= e->facts().attack_range() ? g : std::max(1, g - 1));
            decides = theirs >= 0 && from == theirs;
        } else if (const auto h = static_cast<std::uint32_t>(e->handle); h < 32 && (role.struck >> h & 1u)
                   && (role.chasing || (g >= 2 && e->health < 0.5f * e->max_health))) {
            // Our prey steps away on each of its turns.
            decides = own >= 0 && (acted ? g : g + 1) == own;
        }
        if (!decides || ahead) continue;
        if (ours) {
            ahead = true;
            continue;
        }
        int rank = 0;
        if (acted) {
            rank = enemy_next_rank(world, *e);
        } else {
            if (e->next_rank == 0) continue;
            rank = e->next_rank;
        }
        const int raw = contact_first + threat_level(self, health, incoming);
        ahead = can_act_before(world, next_slot(world, false, rank), packed_priority(raw, self.index, 0));
    }
    return ahead ? contact_first + threat_level(self, health, incoming) : no_contact;
}

// Strikes for next round, by index, each worked out on first use. Slots not used are left
// unwritten: the engine charges for every byte.
struct Strikes {
    unsigned known = 0;
    union {
        std::array<Strike, 8> by_index;
    };
    Strikes() {}
};

const Strike& next_strike(const World& world, const ChampionBelief& c, Strikes& cache) {
    auto& s = cache.by_index[static_cast<std::size_t>(c.index)];
    if (!(cache.known >> c.index & 1)) cache.known |= 1u << c.index, s = strike(c, world.round + 1);
    return s;
}

// An ally's turns this round and next at distance d: a spell cast in the first is not ready again
// for the second.
float two_turns(const World& world, const ChampionBelief& a, int d) {
    unsigned now = 0, next = 0;
    for (int s = 0; s < 2; ++s) {
        if (a.ability_ready(s, world.round)) now |= 1u << s;
        if (a.ability_ready(s, world.round + 1)) next |= 1u << s;
    }
    float best = 0;
    for (unsigned first = now;; first = (first - 1) & now) {
        best = std::max(best, strike_with(a, first).at(d) + strike_with(a, next & ~first).at(d));
        if (first == 0) return best;
    }
}

// An enemy's turns this round and next at distance d, as two_turns prices an ally's: the pair over
// first-turn slots that deals the most, split by turn.
std::pair<float, float> two_blows(const World& world, const ChampionBelief& e, int d) {
    unsigned now = 0, next = 0;
    const bool unsure = e.cooldowns_uncertain();
    for (int s = 0; s < 2; ++s) {
        if (unsure || e.ability_ready(s, world.round)) now |= 1u << s;
        if (unsure || e.ability_ready(s, world.round + 1)) next |= 1u << s;
    }
    std::pair<float, float> best{0.0f, 0.0f};
    for (unsigned first = now;; first = (first - 1) & now) {
        const float a = strike_with(e, first).at(d), b = strike_with(e, next & ~first).at(d);
        // Equal sums (two damage spells in either order): the larger first blow, as the order the
        // heal must outlast is unknown.
        if (const float sum = best.first + best.second; a + b > sum || (a + b == sum && a > best.first)) best = {a, b};
        if (first == 0) return best;
    }
}

// Damage our next turn and those of the allies we see could deal to a tile, each walking first:
// allies yet to act this round, whatever the order, and those acting before slot `before` next
// round, with us at packed priority `packed`.
float side_damage(const World& world, const ChampionBelief& self, const Strike& ours, vec2 p, Strikes& allies, int before,
                  std::int32_t packed) {
    float total = ours.at(dist(self.pos, p));
    for (const auto& a : world.allies) {
        const int d = dist(a.pos, p);
        if (d > Strike::max_reach || a.is_self || !a.alive || !a.visible) continue;
        const bool now = next_turn_round(world, a) == world.round;
        const bool next = next_slot(world, true, ally_next_rank(world, a, packed)) < before;
        if (now && next) total += two_turns(world, a, d);
        else if (now) total += strike(a, world.round).at(d);
        else if (next) total += next_strike(world, a, allies).at(d);
    }
    return total;
}

// The distance our next turn's Strike is read at for a blow on e: its own, or farther when walls,
// units and sight put every tile our basic attack reaches and sees it from more moves away (a walk
// 1, a dash 2, both 3) than open ground would; past max_reach when no walk or dash reaches one. A
// damage spell ready then keeps it: its cast needs no move.
int real_distance(const World& world, const ChampionBelief& self, const ChampionBelief& e, int d) {
    const auto& f = self.facts();
    const int next = world.round + 1;
    for (int s = 0; s < 2; ++s)
        if (f.abilities[s].kind == AbilityKind::damage && self.ability_ready(s, next)) return d;
    const int range = f.attack_range(), need = std::max(0, d - range), dash = f.slot_of(AbilityKind::dash);
    const bool dashes = dash >= 0 && self.ability_ready(dash, next);
    const vec2 here = self.pos;
    // We see it now, from here or our ward, and both stay: the strike search's viewers.
    if (d <= range && e.visible) return d;
    auto viewers = attack_viewers(world, e.pos, range);
    constexpr int r = Reach::Window::radius, w = Reach::Window::width;
    if (const auto* sight = ward_sight(world, static_cast<std::uint32_t>(self.handle)); sight && test(*sight, e.pos))
        viewers |= window_square(range);
    // Dash paths cross holes, altars and allies, but not walls, camps, visible enemies or the enemy
    // spawn (dash_landings_from); a walk then a dash, or a dash then a walk, as far as 3.
    static bitboard camps{cambc::uninitialized}, foes{cambc::uninitialized}, barred{cambc::uninitialized},
        two{cambc::uninitialized}, three{cambc::uninitialized};
    bool built = false;
    int best = 4;
    for (int word = 0; word < 2; ++word)
        for (std::uint64_t bits = word ? viewers.hi : viewers.lo; bits; bits &= bits - 1) {
            const int i = 64 * word + std::countr_zero(bits);
            const vec2 p{e.pos.x - r + i % w, e.pos.y - r + i / w};
            const int k = dist(here, p);
            if (k >= best || k > (dashes ? 3 : 1) || !in_bounds(p) || !test(world.map().open_for_us, p)) continue;
            if (!built) {
                built = true;
                camps_into(camps);
                occupancy_into(team::enemy, foes);
                or_into(world.map().walls, camps, barred);
                or_into(barred, foes, barred);
                or_into(barred, world.map().enemy_spawn, barred);
                if (dashes) barred.reachable_tiles_into(here, 2, two), barred.reachable_tiles_into(here, 3, three);
            }
            if (test(camps, p) || test(foes, p)) continue;
            bool ally = false;
            for (const auto& a : world.allies) ally |= !a.is_self && a.alive && a.visible && a.pos == p;
            if (ally) continue;
            if (k == 1) best = 1;
            else if (k == 2 && test(two, p)) best = 2;
            else if (test(three, p)) best = 3;
        }
    if (best == 4) return Strike::max_reach + 1;
    return d + std::max(0, best - need);
}

// Killing or cancelling a channel needs us to act before its owner.
void offer_kills(const World& world, const ChampionBelief& self, const Strike& ours, const std::vector<Enemy>& enemies,
                 Wish& wish) {
    const auto& enemy_spawn = world.map().enemy_spawn;
    Strikes allies;
    for (const auto& [e, health] : enemies) {
        const int d = dist(self.pos, e->pos);
        if (!ours.hits(d) || test(enemy_spawn, e->pos)) continue;
        // Each offer at the priority it would set: a higher final one only ranks us sooner.
        const int their = next_slot(world, false, enemy_next_rank(world, *e));
        const auto packed = [&](float v) { return packed_priority(Wish{kill, v}.priority(), self.index, 0); };
        const auto offer = [&](float v) {
            if (can_act_before(world, their, packed(v))) wish.offer(kill, v);
        };
        const float value = params::turn_life_value + params::turn_gem_value * static_cast<float>(pair_gems(world, *e));
        const float kill_value = e->acted ? value : unacted_share * value;
        // Read at the real distance only for an offer that would win: one or two a turn.
        if (const auto p = packed(kill_value); (wish.band < kill || kill_value > wish.value) && can_act_before(world, their, p)) {
            const float side = side_damage(world, self, ours, e->pos, allies, their, p);
            if (side * e->taken >= health) {
                const int real = real_distance(world, self, *e, d);
                const float blow = ours.at(real);
                if ((side - ours.at(d) + blow) * e->taken >= health) wish.offer(kill, kill_value, e->acted ? e->index : -1, blow * e->taken);
            }
        }
        // A channel completes at its owner's turn start: here, its next.
        if (e->channel_end_round != world.round + 1) continue;
        if (e->channel == Channel::tribute && ours.stuns[d] && e->facts().passive != Passive::stun_immune)
            offer(params::turn_tribute_value + params::turn_gem_value * static_cast<float>(e->gems));
        if (e->channel == Channel::recall && (ours.at(d) > 0 || ours.stuns[d])) offer(params::turn_recall_value);
        if (e->channel == Channel::teleport && ours.stuns[d] && e->facts().passive != Passive::stun_immune)
            offer(params::turn_recall_value);
    }
}

bool channel_ending(cambc::champion_state state) {
    using cambc::champion_state;
    return (state.contains(champion_state::recalling) || state.contains(champion_state::submitting_gems)
            || state.contains(champion_state::teleporting))
           && my_channel_time() == 1;
}

// Our ending channel completes at our next turn's start, unless an enemy acting first cancels it:
// any damage cancels a recall, only a stun (Marcella is immune) a tribute or a teleport. The bid
// saves nothing if a cancel lands whatever our rank: this round's turn of an enemy in sight yet to
// act, the camp phase on a recall (a bid ranks us first in its ties too), or an enemy we cannot act
// before even so. A cancel keeps the gems carried, so only a tribute prices the bag, as offer_kills.
void offer_channel(const World& world, const ChampionBelief& self, cambc::champion_state state, Safety& safety, Wish& wish) {
    using cambc::champion_state;
    const bool recall = state.contains(champion_state::recalling), tribute = state.contains(champion_state::submitting_gems);
    if (!recall && self.facts().passive == Passive::stun_immune) return;
    if (recall && safety.tie_hit(self.pos) > 0) return;
    const float value = tribute ? params::turn_tribute_value + params::turn_gem_value * static_cast<float>(my_gems()) : params::turn_recall_value;
    const auto packed = packed_priority(Wish{protect, value}.priority(), self.index, 0);
    const auto cancels = [&](const Blow& b) { return b.hits && (recall || b.stuns); };
    std::array<Safety::ThreatAt, 16> threats;
    const int n = safety.threats_at(self.pos, threats);
    bool deniable = false;
    for (int i = 0; i < n; ++i) {
        const auto& t = threats[i];
        if (!cancels(t.blow)) continue;
        const auto& e = world.enemies[t.enemy];
        // With two turns before ours the blow covers both: this round's alone is its plain strike.
        // A teleport's channel turns are not its own (turns_before_ours).
        const bool turn_now = !e.acted && !turn_lost(e) && (!e.teleport_pending() || e.channel_end_round <= world.round);
        if (e.visible && turn_now && (turns_before_ours(world, e) < 2 || cancels(strike(e, world.round).blow(dist(self.pos, e.pos)))))
            return;
        if (!can_act_before(world, next_slot(world, false, enemy_next_rank(world, e)), packed)) return;
        deniable = true;
    }
    if (deniable) wish.offer(protect, value);
}

// No strike reaches past Strike::max_reach: with no enemy in sight and none possibly that near,
// offer_escape finds nothing hits. Checked before the threats are built, which works out each
// enemy's strike (~400 fuel each). Not for a healer: its turn end may read this turn's Safety
// again (play_turn's see_again), and a strike once worked out is kept through it.
[[gnu::noinline]] bool out_of_reach(const World& world, const ChampionBelief& self, Safety& safety) {
    if (safety.built() || safety.seen_enemies() || self.facts().heals()) return false;
    for (auto left = safety.live_enemies(); left; left &= left - 1)
        if (possible_within(world.enemies[static_cast<std::size_t>(std::countr_zero(left))], self.pos, Strike::max_reach)) return false;
    return true;
}

// At least offer_escape's damage, from the strikes alone: no placement, and unseen enemies at
// their most. Before a refresh it still bounds the damage after one unless a visible enemy may have
// died: otherwise our turn only removed camp members.
bool may_escape(const World& world, const ChampionBelief& self, Safety& safety, bool seen) {
    // On the first turn the enemies are on their spawn or a step off it, nearly always out of
    // reach: offer_escape would find nothing, so the ceiling is skipped too. Later it seldom holds.
    if (world.round == world.first_round && out_of_reach(world, self, safety)) return false;
    // With none in sight the ceiling places nothing, and its unseen strikes cost less.
    const float taken = self.taken;
    if (!seen) return safety.damage_ceiling(self.pos, false, taken) >= self.health + self.shield;
    // The camps count only once an enemy hits: their members cost ~10k on many-group maps. Summed
    // after them in enemy order, as the float total always was.
    Unwritten<float, 8> blows;
    int n = 0;
    for (const auto& e : world.enemies) {
        if (!e.alive || !(e.visible || e.tracked) || n == 8) continue;
        const int d = e.visible ? dist(self.pos, e.pos) : 0;
        if (d > Strike::max_reach) continue; // before its strike is worked out
        const auto& s = safety.strike_of(e);
        if (!s.hits(d)) continue;
        blows.a[static_cast<std::size_t>(n++)] = s.damage[static_cast<std::size_t>(d)] * (safety.blow_repeats(e) ? 2.0f : 1.0f) * taken;
    }
    if (n == 0) return false;
    float damage = safety.camp_damage(self.pos, true, true);
    for (int i = 0; i < n; ++i) damage += blows.a[static_cast<std::size_t>(i)];
    return damage >= self.health + self.shield;
}

// Enemies yet to act this round strike before our next turn whatever the order; acting first
// next round denies the second strike of those, and the only one of the others. With what lands
// whatever the order (the camp phase, those strikes) enough to kill us, the bid saves nothing. The
// camps count there at their expected damage, so a worst case alone does not drop a bid that saves us.
void offer_escape(const World& world, const ChampionBelief& self, Safety& safety, Wish& wish) {
    if (out_of_reach(world, self, safety)) return;
    float damage = safety.camp_damage(self.pos, true, true), unavoidable = safety.camp_damage(self.pos, false);
    bool enemy = false;
    std::array<Safety::ThreatAt, 16> threats;
    const int n = safety.threats_at(self.pos, threats);
    for (int i = 0; i < n; ++i) {
        const auto& t = threats[i];
        if (!t.blow.hits) continue;
        enemy = true;
        const auto& e = world.enemies[t.enemy];
        // With two turns before ours, the blow already covers both, and its first turn's share is
        // not known apart: none of it counts as unavoidable.
        const bool now = safety.blow_repeats(e);
        damage += t.blow.damage * (now ? 2.0f : 1.0f) * self.taken;
        // A teleport's channel turns are not its own (turns_before_ours).
        if (now && !e.teleport_pending()) unavoidable += t.blow.damage * self.taken;
    }
    const float health = self.health + self.shield;
    if (enemy && damage >= health && unavoidable < health)
        wish.offer(protect, params::turn_life_value + params::turn_gem_value * static_cast<float>(my_gems()));
}

// A camp member believed alive stands on p (as Pathing::live_camps reads the beliefs).
bool live_camp_on(const World& world, vec2 p) {
    const int g = world.map().group_at(p);
    if (g < 0) return false;
    const auto& c = world.camps[g];
    const auto& members = world.map().groups[g].members;
    for (std::size_t i = 0; i < members.size(); ++i)
        if (members[i].pos == p) return c.state == CampState::alive && c.health[i] > 0;
    return false;
}

// A tile we may heal from next turn has the ally in range and in sight: ours (we see it now), or a
// free tile a step away that sees it, as our ward makes every one.
bool heal_reaches(const World& world, const ChampionBelief& self, vec2 target, int range) {
    if (dist(self.pos, target) <= range) return true;
    const bool ward = own_ward_sees(world, target);
    const auto viewers = ward ? Reach::Window{} : attack_viewers(world, target, range);
    const auto& map = world.map();
    for (int dy = -1; dy <= 1; ++dy)
        for (int dx = -1; dx <= 1; ++dx) {
            const vec2 q{self.pos.x + dx, self.pos.y + dy};
            if (dist(q, target) > range || !in_bounds(q) || !test(map.open_for_us, q) || live_camp_on(world, q)) continue;
            if (!ward && !(viewers & Reach::Window::bit(Reach::Window::at(q.x - target.x, q.y - target.y)))) continue;
            bool free = true;
            for (const auto* side : {&world.allies, &world.enemies})
                for (const auto& o : *side) free = free && !(o.alive && o.visible && o.pos == q);
            if (free) return true;
        }
    return false;
}

// A heal before the enemies' turns next round keeps an ally alive whom they would otherwise kill.
// What lands before the heal whatever we bid: this round's turns of enemies yet to act, and next
// round's of those acting first even so. With that enough to kill it, the bid saves nothing.
void offer_heal(const World& world, const ChampionBelief& self, const std::vector<Enemy>& enemies, Wish& wish) {
    const int slot = self.facts().slot_of(AbilityKind::heal);
    if (slot < 0 || !self.ability_ready(slot, world.round + 1)) return;
    const auto& a = self.facts().abilities[slot];
    const float heal = a.multiplier * self.focus;
    const auto& spawn = world.map().ally_spawn;
    Strikes strikes;
    for (const auto& ally : world.allies) {
        if (ally.is_self || !ally.alive || !ally.visible || test(spawn, ally.pos) || dist(self.pos, ally.pos) > a.range() + 1)
            continue;
        const float value = params::turn_life_value + params::turn_gem_value * static_cast<float>(ally.gems);
        const auto packed = packed_priority(Wish{protect, value}.priority(), self.index, 0);
        float before = 0, total = 0;
        for (const auto& [e, left] : enemies) {
            const int d = dist(e->pos, ally.pos);
            if (d > Strike::max_reach) continue; // neither blow below reaches
            // Its turns before our next: this round's if yet to act, then next round's. A stun takes
            // the first; a teleport's channel turns are not its own (turns_before_ours).
            const int from = e->teleport_pending() ? e->channel_end_round : world.round;
            bool now = !e->acted && from <= world.round, next = from <= world.round + 1;
            if (turn_lost(*e)) (now ? now : next) = false;
            float now_blow = 0, next_blow = 0;
            if (now && next) {
                std::tie(now_blow, next_blow) = two_blows(world, *e, d);
            } else if (now) {
                now_blow = strike(*e, world.round).at(d);
            } else if (next) {
                next_blow = next_strike(world, *e, strikes).at(d);
            }
            if (now_blow <= 0 && next_blow <= 0) continue;
            const bool first = next_blow > 0 && !can_act_before(world, next_slot(world, false, enemy_next_rank(world, *e)), packed);
            total += (now_blow + next_blow) * ally.taken;
            before += (now_blow + (first ? next_blow : 0.0f)) * ally.taken;
        }
        // The shield absorbs first; the heal lifts what health is left, up to the maximum.
        const float shield_left = std::max(0.0f, ally.shield - before), health_left = ally.health - std::max(0.0f, before - ally.shield);
        if (health_left > 0 && total >= ally.health + ally.shield
            && total - before < std::min(health_left + heal, ally.max_health) + shield_left && heal_reaches(world, self, ally.pos, a.range()))
            wish.offer(protect, value);
    }
}

// What this turn's needs bid for; band none if nothing needs us to act early. `self` live, as
// read_strike leaves it with an enemy in sight.
Wish bid(const World& world, Safety& safety, const ChampionBelief& self, cambc::champion_state state, const std::vector<Enemy>& enemies) {
    Wish wish;
    using cambc::champion_state;
    // A tribute or teleport running past our next turn's start takes that turn: no strike to bid for.
    const bool held = (state.contains(champion_state::submitting_gems) || state.contains(champion_state::teleporting))
                      && my_channel_time() > 1;
    if (!enemies.empty() && !held) {
        offer_kills(world, self, strike(self, world.round + 1), enemies, wish);
        offer_heal(world, self, enemies, wish);
    }
    const bool ending = channel_ending(state);
    const bool seen = enemy_seen(world);
    int visible = 0;
    if (seen)
        for (const auto& e : world.enemies) visible += e.alive && e.visible;
    // Out of sight now also reads as off the map.
    const bool died = static_cast<int>(enemies.size()) < visible;
    bool refreshed = false;
    const auto refresh = [&] {
        using cambc::champion_state;
        // Only our attacks and casts kill.
        if (!refreshed && !(state.contains(champion_state::can_attack) && state.contains(champion_state::can_cast)))
            refreshed = true, safety.refresh();
    };
    if (died) refresh();
    if (ending) {
        refresh();
        offer_channel(world, self, state, safety, wish);
    }
    if (!test(world.map().ally_spawn, self.pos) && may_escape(world, self, safety, seen)) {
        refresh();
        offer_escape(world, self, safety, wish);
    }
    return wish;
}

// With no enemy in sight, not healing and no channel ending, the call bids no kill, heal or cancel:
// its cost is linear in the camp members and tracked enemies, 0.6k median, 4.8k at p99.95 and 18.7k
// at most over 3.2M calls (fuel campaign 4). Its reserve covers that and mostly leaves the comms
// refresh its 5k: at 5k, comms-stale-vision rose a third.
constexpr std::uint64_t quiet_reserve = 6000;
// Bidding can spend the old 10k floor before the priority and comms are published.
constexpr std::uint64_t order_reserve = end_reserve + 2000;
bool quiet(const World& world) {
    if (world.enemy_seen() || world.me().facts().heals() || world.round == world.first_round) return false;
    return !channel_ending(cambc::champion_state::from_bits_retain(my_record().state));
}

} // namespace

void set_turn_order(const World& world, Safety& safety) {
    world.throw_if_stale();
    const bool short_of_fuel = world.me().alive && !fuel_ok(order_reserve) && !(fuel_ok(quiet_reserve) && quiet(world));
    if (short_of_fuel) {
        note_shortcut("turn-order");
        // Keeps the last rank; with none yet, the plain priority rather than the start's 0.
        if (turn_rank_valid) return;
    }
    follow::posting = {};
    // Set only once worked out: a throw part-way keeps the last rank.
    const auto rank = [&] {
        if (!world.me().alive) return dead_priority;
        cambc::champion_state state{};
        auto& self = live_self(world, state);
        if (!self.alive) return dead_priority;
        const auto& enemies = live_enemies(world);
        if (!enemies.empty()) read_strike(world, self);
        const Wish wish = short_of_fuel ? Wish{} : bid(world, safety, self, state, enemies);
        if (wish.band == kill && wish.target >= 0) follow::posting = {wish.target, world.round, wish.need};
        return wish.band != none ? wish.priority() : plain_priority(world, safety, self, enemies);
    }();
    turn_rank = rank;
    turn_rank_valid = true;
    follow::own = follow::posting;
}

std::int32_t dead_packed_priority(int index) { return packed_priority(dead_priority, index, 0); }

void publish_turn_order(const World& world, std::uint32_t payload) {
    const std::int32_t priority = packed_priority(turn_rank, world.me().index, payload);
    try {
        static std::int32_t next;
        ok(cambc::detail::sdk_bc_champion_priority(my_handle(), 1, &next));
        if (priority != next) throw_if_stale(), cambc::self().set_priority(priority);
        comms::plain_published(world);
    } catch (const cambc::error&) {
    }
}

} // namespace aph
