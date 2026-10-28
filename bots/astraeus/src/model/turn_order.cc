#include "turn_order.h"
#include <algorithm>
#include <array>
#include <bit>
#include <vector>
#include "../params.h"
#include "safety.h"
#include "world.h"

namespace aph {

namespace {

// One scale for every ally: teacher_priority's danger (14..23), dead (13) and idle (at most 12)
// values, with two bands above them. A kill or a cancelled channel outranks saving a life; each
// needs us to act before some enemy next round. Only non-teacher champions bid for the bands.
enum Band : int { none, protect, kill };
constexpr int band_width = 10000;

teacher_priority::Unit priority_self(const World& world) {
    teacher_priority::Unit self;
    self.type = static_cast<int>(world.me().type);
    self.alive = world.me().alive && is_alive(world.me().handle);
    if (!self.alive) return self;
    const auto& info = my_record();
    self.x = info.x;
    self.y = info.y;
    self.health = info.health;
    self.max_health = info.max_health;
    self.strength = info.strength;
    self.focus = info.focus;
    self.shield = shield_value(world.me().handle);
    for (std::uint32_t slot = 0; slot < 2; ++slot) {
        static std::int32_t cooldown;
        ok(cambc::detail::sdk_champion_cooldown(my_handle(), slot, &cooldown));
        self.cooldowns[slot] = cooldown;
    }
    return self;
}

static_assert(static_cast<int>(cambc::champion_type::ryth) == teacher_priority::ryth);
static_assert(static_cast<int>(cambc::champion_type::vesper_vale) == teacher_priority::vesper_vale);
static_assert(static_cast<int>(cambc::champion_type::vendetta) == teacher_priority::vendetta);
static_assert(static_cast<int>(cambc::champion_type::cassi) == teacher_priority::cassi);
static_assert(static_cast<int>(cambc::champion_type::issac) == teacher_priority::issac);
static_assert(static_cast<int>(cambc::champion_type::stellar) == teacher_priority::stellar);
static_assert(static_cast<int>(cambc::champion_type::prism) == teacher_priority::prism);
static_assert(static_cast<int>(cambc::champion_type::marcella) == teacher_priority::marcella);
static_assert(static_cast<int>(cambc::champion_type::willow) == teacher_priority::willow);
static_assert(static_cast<int>(cambc::champion_type::ren) == teacher_priority::ren);
static_assert(static_cast<int>(cambc::champion_type::varg) == teacher_priority::varg);
static_assert(static_cast<int>(cambc::champion_type::tavi) == teacher_priority::tavi);
static_assert(static_cast<int>(cambc::champion_type::heart_of_ruin) == teacher_priority::heart_of_ruin);

// An enemy yet to act this round moves before our next turn anyway: acting before its turn next
// round denies it only a second one.
constexpr float unacted_share = 0.5f;
struct Wish {
    int band = none;
    float value = 0;

    void offer(int b, float v) {
        if (b > band || (b == band && v > value)) band = b, value = v;
    }
    int priority() const { return band * band_width + std::clamp(static_cast<int>(value), 0, band_width - 1); }
};

// Only the order within the team matters, so a raw priority is renumbered by a code that keeps the
// order of every value it can take: idle, dead and danger in [lowest_raw, highest_raw]; in a band,
// int(a life, tribute or recall value + 15 x gems), or of half a kill's, which is 0, 7 or 10 mod 15
// (0 or 10 when protecting), with the clamped band_width - 1 above all.
constexpr int lowest_raw = teacher_priority::role(-1) + idle_step * (1 - health_buckets);
constexpr int highest_raw = teacher_priority::dead_priority + teacher_priority::danger_buckets;
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
static_assert(params::gem_value == 15 && static_cast<int>(params::life_value) % 15 == 0
              && static_cast<int>(params::tribute_value) % 15 == 10 && static_cast<int>(params::recall_value) % 15 == 0
              && unacted_share == 0.5f && static_cast<int>(params::life_value * unacted_share) % 15 == 0);
static_assert(rank_code(band_width - 1) < rank_code(band_width));

// The latest rank set_turn_order chose: kept when it skips a turn short of fuel.
int turn_rank = 0;
bool turn_rank_valid = false; // set_turn_order has chosen a rank this match

// Above the payload, the code relative to raw 0's, then 7 - our index so that equal codes still tie
// by id. Bots read a champion they have not seen as priority 0, so raw 0 stays 0 (no payload) and
// every other priority keeps its sign.
std::int32_t packed_priority(int raw, int index, std::uint32_t payload) {
    if (raw == 0) return 0;
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

// The enemies in sight at turn start that our turn has not killed.
const teacher_priority::Enemies& live_start_enemies(const World& world) {
    static teacher_priority::Enemies out;
    const auto& start = world.priority_start_enemies;
    out.count = 0;
    for (int i = 0; i < start.count; ++i) {
        static std::int32_t alive;
        const auto h = static_cast<std::uint32_t>(world.priority_start_handles[static_cast<std::size_t>(i)]);
        if (cambc::detail::sdk_champion_is_alive(h, &alive) == 0 && alive == 0) continue;
        out.units[static_cast<std::size_t>(out.count++)] = start.units[static_cast<std::size_t>(i)];
    }
    return out;
}

// Ourselves as we end the turn, moved. The fields read here only:
// copying a belief copies its bitboards.
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

// A champion's index in next round's turns at team rank `rank`, as World::slot counts them: the
// teams alternate, the larger one's extra champions last.
int next_slot(const World& world, bool ally, int rank) {
    const bool first = ally == we_start(world, world.round + 1);
    const int others = static_cast<int>(ally ? world.enemies.size() : world.allies.size());
    return rank < others ? 2 * rank + (first ? 0 : 1) : others + rank;
}

// Ally `a`'s rank next round with us at packed priority `ours` (packed_priority, no payload): the
// allies whose next priority outranks its own. Each acts by its next priority as last read, which
// is final once it has acted this round. Our packed priorities differ above the payload but for
// 0, where ties go by id.
int ally_next_rank(const World& world, const ChampionBelief& a, std::int32_t ours) {
    const auto order = [&](const ChampionBelief& c) { return (c.is_self ? ours : c.next_priority) >> priority_payload_bits; };
    const int own = order(a);
    int rank = 0;
    for (const auto& b : world.allies)
        if (&b != &a) rank += order(b) > own || (order(b) == own && b.handle < a.handle);
    return rank;
}

// At most `e`'s rank next round: 0 while its priority can change; else the enemies whose next
// priority is final and outranks it. Final once it has acted this round, or if its team never
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

// Damage our next turn and those of the allies we see could deal to a tile, each walking first:
// only allies acting before slot `before` next round, with us at packed priority `packed`.
float side_damage(const World& world, const ChampionBelief& self, const Strike& ours, vec2 p, Strikes& allies, int before,
                  std::int32_t packed) {
    float total = ours.at(dist(self.pos, p));
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive && a.visible && next_slot(world, true, ally_next_rank(world, a, packed)) < before)
            total += next_strike(world, a, allies).at(dist(a.pos, p));
    return total;
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
        const float value = params::life_value + params::gem_value * static_cast<float>(pair_gems(world, *e));
        const float kill_value = e->acted ? value : unacted_share * value;
        if (const auto p = packed(kill_value);
            can_act_before(world, their, p) && side_damage(world, self, ours, e->pos, allies, their, p) * e->taken >= health)
            wish.offer(kill, kill_value);
        // A channel completes at its owner's turn start: here, its next.
        if (e->channel_end_round != world.round + 1) continue;
        if (e->channel == Channel::tribute && ours.stuns[d] && e->facts().passive != Passive::stun_immune)
            offer(params::tribute_value + params::gem_value * static_cast<float>(e->gems));
        if (e->channel == Channel::recall && (ours.at(d) > 0 || ours.stuns[d])) offer(params::recall_value);
        if (e->channel == Channel::teleport && ours.stuns[d] && e->facts().passive != Passive::stun_immune)
            offer(params::recall_value);
    }
}

bool channel_ending(cambc::champion_state state) {
    using cambc::champion_state;
    return (state.contains(champion_state::recalling) || state.contains(champion_state::submitting_gems)
            || state.contains(champion_state::teleporting))
           && my_channel_time() == 1;
}

// Our ending channel completes at our next turn's start, unless an enemy acting first cancels it:
// any damage cancels a recall, only a stun (Marcella is immune) a tribute or a teleport.
void offer_channel(const ChampionBelief& self, cambc::champion_state state, Safety& safety, Wish& wish) {
    using cambc::champion_state;
    const bool recall = state.contains(champion_state::recalling), tribute = state.contains(champion_state::submitting_gems);
    if (!recall && self.facts().passive == Passive::stun_immune) return;
    std::array<Safety::ThreatAt, 16> threats;
    const int n = safety.threats_at(self.pos, threats);
    for (int i = 0; i < n; ++i) {
        const auto& b = threats[i].blow;
        if (!b.hits || !(recall || b.stuns)) continue;
        const float gems = params::gem_value * static_cast<float>(my_gems());
        wish.offer(protect, (tribute ? params::tribute_value : params::recall_value) + gems);
        return;
    }
}

// No strike reaches past Strike::max_reach: with no enemy in sight and none possibly that near,
// offer_escape finds nothing hits. Checked before the threats are built, which works out each
// enemy's strike (~400 fuel each). Not for a healer: its turn end may read this turn's Safety
// again (play_turn's see_again), and a strike once worked out is kept through it.
[[gnu::noinline]] bool out_of_reach(const World& world, const ChampionBelief& self, Safety& safety) {
    if (safety.built() || safety.seen_enemies() || self.facts().heals()) return false;
    for (auto left = safety.live_enemies(); left; left &= left - 1)
        if (any_within(world.enemies[static_cast<std::size_t>(std::countr_zero(left))].possible, self.pos, Strike::max_reach)) return false;
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
    float damage = safety.camp_damage(self.pos, true, true);
    bool hit = false;
    for (const auto& e : world.enemies) {
        if (!e.alive || !(e.visible || e.tracked)) continue;
        const auto& s = safety.strike_of(e);
        const int d = e.visible ? dist(self.pos, e.pos) : 0;
        if (!s.hits(d)) continue;
        hit = true;
        damage += s.damage[static_cast<std::size_t>(d)] * (e.visible && !e.acted && !turn_lost(e) && turns_before_ours(world, e) < 2 ? 2.0f : 1.0f) * taken;
    }
    return hit && damage >= self.health + self.shield;
}

// Enemies yet to act this round strike before our next turn whatever the order; acting first
// next round denies the second strike of those, and the only one of the others.
void offer_escape(const World& world, const ChampionBelief& self, Safety& safety, Wish& wish) {
    if (out_of_reach(world, self, safety)) return;
    float damage = safety.camp_damage(self.pos, true, true);
    bool enemy = false;
    std::array<Safety::ThreatAt, 16> threats;
    const int n = safety.threats_at(self.pos, threats);
    for (int i = 0; i < n; ++i) {
        const auto& t = threats[i];
        if (!t.blow.hits) continue;
        enemy = true;
        const auto& e = world.enemies[t.enemy];
        // With two turns before ours, the blow already covers both.
        damage += t.blow.damage * (e.visible && !e.acted && !turn_lost(e) && turns_before_ours(world, e) < 2 ? 2.0f : 1.0f) * self.taken;
    }
    if (enemy && damage >= self.health + self.shield) wish.offer(protect, params::life_value + params::gem_value * static_cast<float>(my_gems()));
}

// A heal before the enemies' turns keeps an ally alive whom they would otherwise kill.
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
        float damage = 0;
        for (const auto& [e, health] : enemies) damage += next_strike(world, *e, strikes).at(dist(e->pos, ally.pos));
        if (damage >= ally.health && damage < std::min(ally.health + heal, ally.max_health))
            wish.offer(protect, params::life_value + params::gem_value * static_cast<float>(ally.gems));
    }
}

} // namespace

void set_turn_order(const World& world, Safety& safety) {
    world.throw_if_stale();
    Wish wish;
    if (world.me().alive && !fuel_ok(end_reserve)) {
        note_shortcut("turn-order");
        // Never chosen yet, the plain priority rather than the start's 0 (v61).
        if (!turn_rank_valid) {
            const auto self = priority_self(world);
            const int raw = teacher_priority::priority(self, live_start_enemies(world), self.alive ? static_cast<int>(my_gems()) : 0);
            world.throw_if_stale();
            turn_rank = raw;
            turn_rank_valid = true;
        }
        return;
    }
    if (world.me().alive && teacher_priority::role(static_cast<int>(world.me().type)) < 0) {
        cambc::champion_state state{};
        auto& self = live_self(world, state);
        if (self.alive) {
            const auto& enemies = live_enemies(world);
            if (!enemies.empty()) {
                read_strike(world, self);
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
                offer_channel(self, state, safety, wish);
            }
            if (!test(world.map().ally_spawn, self.pos) && may_escape(world, self, safety, seen)) {
                refresh();
                offer_escape(world, self, safety, wish);
            }
        }
    }
    int raw;
    if (wish.band != none) {
        raw = wish.priority();
    } else {
        const auto self = priority_self(world);
        raw = teacher_priority::priority(self, live_start_enemies(world), self.alive ? static_cast<int>(my_gems()) : 0);
        world.throw_if_stale();
    }
    turn_rank = raw;
    turn_rank_valid = true;
}

void publish_turn_order(const World& world, std::uint32_t payload) {
    const std::int32_t priority = packed_priority(turn_rank, world.me().index, payload);
    try {
        static std::int32_t next;
        ok(cambc::detail::sdk_bc_champion_priority(my_handle(), 1, &next));
        if (priority != next) throw_if_stale(), cambc::self().set_priority(priority);
    } catch (const cambc::error&) {
    }
}

} // namespace aph
