#include "safety.h"
#include <algorithm>
#include <bit>
#include <cmath>
#include <cstring>
#include <limits>
#include <memory>
#include <vector>
#include "world.h"

namespace aph {

using namespace safety_params;

namespace {

constexpr int max_fighters = 6; // one team's bodies

// What casting a slot adds to a turn's basic attack.
struct CastEffect {
    float value = 0; // the choice between ready slots: the most valuable, if any above 0
    float damage = 0, heal = 0;
    bool heals_self = false; // a shield; a heal goes to the weakest hurt ally
    bool stuns = false;
    int hits = 1;
    int duration = 0; // a shield's own turns
};

// A champion's casts, fixed for a turn.
struct Kit {
    std::array<CastEffect, 2> cast;
    std::array<int, 2> preference; // slots by value, ties to slot 0
};

// Turns are counted per side from 0, so cooldowns and arrivals are turn indices rather than
// counters to tick down.
struct Fighter {
    const Kit* kit;
    float strength;
    std::array<int, 2> ready_at; // own turn from which the slot can be cast
    int next_cast;               // own turn from which a slot worth casting is ready
    int arrives_at;              // own turns spent walking into reach first
    bool idle;                   // never acts
    bool stun_immune, linked;
    float health, max_health;
    float shield;
    int shield_until;  // own turn at whose start the shield is lost
    float retaliation; // Ren: damage back per hit taken
    int link;          // Cassi or Issac: the other body, which dies with this one
};

// Fixed storage, as WASM heap work is costly; only the first `count` fighters are written, as the
// engine charges for every byte.
struct Side {
    union {
        std::array<Fighter, max_fighters> fighters;
    };
    int count = 0;
    int alive = 0; // members with health above 0; the fallen stay down
    int turn = 0; // own turns taken
    int self = -1; // our own fighter
    int stunned = 0; // members that lose their next turn
    float camp = 0;  // camp damage taken with each of the other side's turns
    // Own turns before `quiet_until` are only the basic attacks, `quiet_damage` from `quiet_hits`
    // hits, while nobody is stunned and `alive` stays `quiet_alive`.
    int quiet_until = 0, quiet_alive = -1, quiet_hits = 0;
    float quiet_damage = 0;

    Side() {}

    void add(const Fighter& f) {
        if (count == max_fighters) return;
        auto& g = fighters[count];
        g = f;
        if (g.linked)
            for (int i = 0; i < count; ++i)
                if (fighters[i].linked) g.link = i, fighters[i].link = count;
        alive += g.health > 0;
        ++count;
    }
    float health() const {
        float total = 0;
        for (int i = 0; i < count; ++i) total += std::max(0.0f, fighters[i].health);
        return total;
    }
    // The living member with the least health and shield, or -1.
    int weakest() const {
        int best = -1;
        for (int i = 0; i < count; ++i)
            if (fighters[i].health > 0
                && (best < 0 || fighters[i].health + fighters[i].shield < fighters[best].health + fighters[best].shield))
                best = i;
        return best;
    }
    // A heal's target: the living member below max health with the least, other than `caster`.
    int weakest_hurt(int caster) const {
        int best = -1;
        for (int i = 0; i < count; ++i)
            if (i != caster && fighters[i].health > 0 && fighters[i].health < fighters[i].max_health
                && (best < 0 || fighters[i].health < fighters[best].health))
                best = i;
        return best;
    }
    // Focused on the weakest, shields first, the excess spilling over to the next. `first`:
    // weakest(), when the caller has it.
    void hurt(float damage, int first = -2) {
        for (int i = damage <= 0 ? -1 : first >= -1 ? first : weakest(); i >= 0; i = damage > 0 ? weakest() : -1) {
            auto& f = fighters[i];
            const float absorbed = std::min(damage, f.shield);
            f.shield -= absorbed;
            damage -= absorbed;
            const float taken = std::min(damage, f.health);
            f.health -= taken;
            damage -= taken;
            if (f.health > 0) continue;
            --alive;
            if (f.link >= 0) {
                alive -= fighters[f.link].health > 0;
                fighters[f.link].health = 0;
            }
        }
    }
};

int next_cast(const Fighter& f) {
    int turn = std::numeric_limits<int>::max();
    for (int s = 0; s < 2; ++s)
        if (f.kit->cast[s].value > 0) turn = std::min(turn, f.ready_at[s]);
    return turn;
}

// A champion as it enters a fight. A heal is valued even with no ally to take it: attack() then
// finds no target and moves on, as if it were worth nothing.
void make_fighter(const ChampionBelief& c, int turn_round, Fighter& f, Kit& kit) {
    const auto& facts = c.facts();
    for (int s = 0; s < 2; ++s) {
        const auto& a = facts.abilities[s];
        auto& e = kit.cast[s];
        e = {};
        e.value = a.stuns ? c.strength : 0;
        switch (a.kind) {
        case AbilityKind::attack_reset: e.value += c.strength; break;
        case AbilityKind::damage:
        case AbilityKind::shield:
        case AbilityKind::heal: e.value += a.multiplier * c.focus; break;
        default: break;
        }
        e.stuns = a.stuns;
        if (a.kind == AbilityKind::shield || a.kind == AbilityKind::heal) e.heal = a.multiplier * c.focus;
        e.heals_self = a.kind == AbilityKind::shield;
        if (a.kind == AbilityKind::attack_reset) e.damage = c.strength;
        if (a.kind == AbilityKind::damage) e.damage = a.multiplier * c.focus;
        e.hits = a.kind == AbilityKind::attack_reset || a.kind == AbilityKind::damage ? 2 : 1;
        e.duration = a.duration;
    }
    kit.preference = kit.cast[1].value > kit.cast[0].value ? std::array<int, 2>{1, 0} : std::array<int, 2>{0, 1};
    f.kit = &kit;
    f.strength = c.strength;
    const bool uncertain = c.cooldowns_uncertain();
    for (int s = 0; s < 2; ++s) f.ready_at[s] = uncertain ? 0 : std::max(0, c.ready_round[s] - turn_round);
    f.next_cast = next_cast(f);
    f.arrives_at = 0;
    f.idle = false;
    f.stun_immune = facts.passive == Passive::stun_immune;
    f.linked = facts.passive == Passive::linked_pair;
    f.health = c.health;
    f.max_health = c.max_health;
    f.shield = 0;
    f.shield_until = -1;
    f.retaliation = c.retaliation();
    f.link = -1;
}

// Fighters made this turn, by slot: allies[i] at i, enemies[i] at 16 + i. Beliefs are fixed for
// the turn, so each is made once and copied into each fight.
struct Fighters {
    union {
        std::array<Fighter, 32> fighter;
    };
    union {
        std::array<Kit, 32> kit;
    };
    Fighters() {}
};

Fighters& made_fighters() {
    static Fighters f;
    return f;
}

// A fighter's basic attack and its most valuable ready cast (one a turn); returns hits landed.
int attack(Fighter& f, int turn, Side& self, Side& other, float& damage) {
    damage += f.strength;
    if (turn < f.next_cast) return 1;
    for (const int s : f.kit->preference) {
        const auto& c = f.kit->cast[s];
        if (f.ready_at[s] > turn || c.value <= 0) continue;
        const bool heals_ally = c.heal != 0 && !c.heals_self;
        const int target = heals_ally ? self.weakest_hurt(static_cast<int>(&f - self.fighters.data())) : -1;
        if (heals_ally && target < 0) continue;
        f.ready_at[s] = turn + ability_cooldown;
        f.next_cast = next_cast(f);
        if (c.stuns) ++other.stunned;
        if (c.heals_self) f.shield = c.heal, f.shield_until = turn + c.duration;
        if (heals_ally) {
            auto& t = self.fighters[target];
            t.health = std::min(t.max_health, t.health + c.heal);
        }
        if (c.damage != 0) damage += c.damage;
        return c.hits;
    }
    return 1;
}

// One side's turn: stunned members (the strongest of those in reach first) skip it.
float act(Side& self, Side& other) {
    const int turn = self.turn++;
    float damage = 0;
    int hits = 0;
    if (self.stunned == 0 && turn < self.quiet_until && self.alive == self.quiet_alive) {
        damage = self.quiet_damage;
        hits = self.quiet_hits;
    } else {
        unsigned skip = 0; // bit i: fighters[i]
        for (int k = 0; k < self.stunned; ++k) {
            int best = -1;
            for (int i = 0; i < self.count; ++i) {
                const auto& f = self.fighters[i];
                if (!(skip >> i & 1) && f.health > 0 && !f.idle && f.arrives_at <= turn && !f.stun_immune
                    && (best < 0 || f.strength > self.fighters[best].strength))
                    best = i;
            }
            if (best < 0) break;
            skip |= 1u << best;
        }
        self.stunned = 0;
        int until = std::numeric_limits<int>::max(), quiet_hits = 0;
        float quiet = 0;
        for (int i = 0; i < self.count; ++i) {
            auto& f = self.fighters[i];
            if (f.shield_until >= 0 && f.shield_until <= turn) f.shield = 0, f.shield_until = -1;
            if (f.health <= 0 || f.idle) continue;
            if (f.arrives_at <= turn && !(skip >> i & 1)) hits += attack(f, turn, self, other, damage);
            if (f.shield_until >= 0) until = std::min(until, f.shield_until);
            if (f.arrives_at > turn + 1) {
                until = std::min(until, f.arrives_at);
                continue;
            }
            quiet += f.strength;
            ++quiet_hits;
            until = std::min(until, f.next_cast);
        }
        self.quiet_until = until;
        self.quiet_alive = self.alive;
        self.quiet_damage = quiet;
        self.quiet_hits = quiet_hits;
    }
    const int target = other.weakest();
    const float back = target >= 0 ? other.fighters[target].retaliation : 0.0f;
    other.hurt(damage, target);
    if (back > 0) self.hurt(static_cast<float>(hits) * back);
    return damage;
}

// Turns each side needs to empty the other's pool, within `horizon` turns each, playing the fight
// out on the sides given. `self_falls`: whether our own fighter dies before their side does.
// `dealt`, for debug_fights: their first turn's damage, ours, then their first five turns', ours.
// {-1, -1} if the fuel left fell below `fuel_floor` first.
std::pair<int, int> simulate(Side& us, Side& them, bool they_first, bool* self_falls = nullptr, int horizon = 24,
                             std::array<float, 4>* dealt = nullptr, std::uint64_t fuel_floor = 0) {
    int ours = 0, theirs = 0;
    for (int t = 0; t < 2 * horizon; ++t) {
        if (fuel_floor && t % 8 == 7 && fuel() < fuel_floor) return {-1, -1};
        const bool their_turn = (t % 2 == 0) == they_first;
        if (their_turn) {
            const float d = act(them, us);
            if (dealt && theirs < 5) (*dealt)[2] += d, (*dealt)[0] += theirs == 0 ? d : 0;
            if (us.camp > 0) us.hurt(us.camp);
            ++theirs;
        } else {
            const float d = act(us, them);
            if (dealt && ours < 5) (*dealt)[3] += d, (*dealt)[1] += ours == 0 ? d : 0;
            ++ours;
        }
        // Ren's reflection can fell the side whose turn it is.
        if (self_falls && us.self >= 0 && us.fighters[us.self].health <= 0) *self_falls = true;
        if (us.alive == 0) return {0, std::max(1, theirs)};
        if (them.count > 0 && them.alive == 0) return {std::max(1, ours), 0};
    }
    return {0, 0};
}

// Only the order where they strike first: `lost` is all callers need.
// Plays the fight out on the sides given, which callers discard: copying them is costly.
Trade trade(Side& us, Side& them, std::uint64_t fuel_floor = 0, bool they_first = true) {
    Trade t;
    t.allies = us.count;
    t.enemies = them.count;
    t.our_health = us.health();
    t.their_health = them.health();
    if (them.count == 0) return t;
    const auto [we_kill, they_kill] = simulate(us, them, they_first, &t.self_falls, 24, debug_fights ? &t.dealt : nullptr, fuel_floor);
    if (we_kill < 0) {
        note_shortcut("fight-cut");
        t.lost = t.self_falls = true;
        return t;
    }
    t.turns_to_kill_them = we_kill;
    t.turns_to_kill_us = they_kill;
    t.lost = they_kill > 0;
    return t;
}

// Us, and the allies we see within fight_ally_radius of p.
bool fights_with(const ChampionBelief& a, vec2 p) {
    return a.alive && (a.is_self || (a.visible && dist(p, a.pos) <= fight_ally_radius));
}

// `made`: bit i, Fighters::fighter[i] is this turn's.
const Fighter& fighter(const World& world, const ChampionBelief& c, std::uint32_t& made) {
    const int slot = (c.side == team::enemy ? 16 : 0) + c.index;
    auto& m = made_fighters();
    if (!(made >> slot & 1)) {
        made |= 1u << slot;
        make_fighter(c, c.is_self ? world.round : next_turn_round(world, c), m.fighter[slot], m.kit[slot]);
    }
    return m.fighter[slot];
}

void join_allies(const World& world, Side& us, vec2 p, std::uint32_t& made) {
    for (const auto& a : world.allies) {
        if (!fights_with(a, p)) continue;
        if (a.is_self) us.self = us.count;
        us.add(fighter(world, a, made));
    }
}

} // namespace

int next_turn_round(const World& world, const ChampionBelief& c) {
    // Read for those in sight; ranks are a guess when priorities change unseen.
    if (c.visible && !c.is_self) return c.acted ? world.round + 1 : world.round;
    return world.slot(c, world.round) > world.slot(world.me(), world.round) ? world.round : world.round + 1;
}

namespace {

// Slot bit i: ability i counts.
Strike compute_strike(const ChampionFacts& f, float s, float focus, unsigned slots) {
    const int range = f.attack_range();
    const int walk = f.ranged ? 0 : 1; // a ranged champion's walk spends its attack
    Strike out;
    const auto add = [&](int reach, float damage, bool stuns) {
        reach = std::min(reach, Strike::max_reach);
        for (int d = 0; d <= reach; ++d) {
            out.damage[d] = std::max(out.damage[d], damage);
            out.stuns[d] = out.stuns[d] || stuns;
        }
        out.reach = std::max(out.reach, reach);
    };
    add(range + walk, s, false);
    for (int slot = 0; slot < 2; ++slot) {
        if (!(slots >> slot & 1)) continue;
        const auto& a = f.abilities[slot];
        switch (a.kind) {
        case AbilityKind::attack_reset:
            add(range + walk, 2 * s, a.stuns);
            if (f.ranged) add(range + 1, s, a.stuns); // walk, reset, attack
            break;
        case AbilityKind::dash: add(range + walk + 2, s, false); break;
        case AbilityKind::damage:
            // Excludes walking but not the basic attack.
            add(a.reach(), a.multiplier * focus, a.stuns);
            add(range, a.multiplier * focus + s, a.stuns);
            break;
        case AbilityKind::stun: add(a.reach() + (a.excludes_walking ? 0 : 1), 0, true); break;
        default: break;
        }
    }
    return out;
}

} // namespace

// Called many times a turn for the same few champions: the last result per champion is kept,
// keyed by everything it depends on.
Strike strike(const ChampionBelief& c, int turn_round) {
    struct Memo {
        cambc::champion_type type;
        std::uint32_t strength, focus;
        unsigned slots = 4; // never a key
        Strike value;
    };
    static std::array<Memo, 16> memo;
    const bool uncertain = c.cooldowns_uncertain();
    const unsigned slots =
        (uncertain || c.ability_ready(0, turn_round) ? 1u : 0u) | (uncertain || c.ability_ready(1, turn_round) ? 2u : 0u);
    const auto s = std::bit_cast<std::uint32_t>(c.strength), focus = std::bit_cast<std::uint32_t>(c.focus);
    auto& m = memo[(c.side == team::enemy ? 8u : 0u) + (static_cast<unsigned>(c.index) & 7u)];
    if (m.slots != slots || m.type != c.type || m.strength != s || m.focus != focus)
        m = {c.type, s, focus, slots, compute_strike(c.facts(), c.strength, c.focus, slots)};
    return m.value;
}

int turns_before_ours(const World& world, const ChampionBelief& c) {
    const auto& me = world.me();
    const bool now = c.visible ? !c.acted : world.slot(c, world.round) > world.slot(me, world.round);
    return (now ? 1 : 0) + (world.slot(c, world.round + 1) < world.slot(me, world.round + 1) ? 1 : 0);
}

Strike threat_strike(const World& world, const ChampionBelief& c) {
    const auto s = strike(c, next_turn_round(world, c));
    if (s.reach < 0 || turns_before_ours(world, c) < 2) return s;
    const auto& f = c.facts();
    const int basic_reach = f.attack_range() + (f.ranged ? 0 : 1);
    Strike out;
    for (int d = 0; d <= Strike::max_reach; ++d) {
        const float walked = s.at(std::max(0, d - 1));
        const float twice = s.hits(d) ? s.at(d) + (d <= basic_reach ? c.strength : 0.0f) : 0.0f;
        out.damage[d] = std::max(walked, twice);
        out.stuns[d] = s.stuns[std::max(0, d - 1)]; // s.stuns holds from 0 out to some distance
    }
    out.reach = std::min(Strike::max_reach, s.reach + 1);
    return out;
}

namespace {

// Window arithmetic by tables where it can: WASM loops and variable shifts cost fuel.
using Window = Reach::Window;
constexpr int win_r = 4, win_n = 2 * win_r + 1;
constexpr Window win_full = ~Window{};
constexpr Window win_bit(int x, int y) { return Window::bit(y * win_n + x); }

struct Tables {
    // [a][b]: columns (rows) a to b of the window; empty if a > b.
    std::array<std::array<Window, win_n>, win_n> columns{}, rows{};
    std::array<Window, win_r + 1> square{}; // [k]: within k of the centre
    std::array<Window, win_n * win_n> bits{};
};

constexpr Tables tables = [] {
    Tables t;
    for (int y = 0; y < win_n; ++y)
        for (int x = 0; x < win_n; ++x) t.bits[static_cast<std::size_t>(y * win_n + x)] = win_bit(x, y);
    for (int a = 0; a < win_n; ++a)
        for (int b = a; b < win_n; ++b)
            for (int i = a; i <= b; ++i)
                for (int j = 0; j < win_n; ++j) {
                    t.columns[a][b] |= win_bit(i, j);
                    t.rows[a][b] |= win_bit(j, i);
                }
    for (int k = 0; k <= win_r; ++k) t.square[k] = t.columns[win_r - k][win_r + k] & t.rows[win_r - k][win_r + k];
    return t;
}();

Window dilate(Window s) {
    const Window h = s | (s.shl(1) & ~tables.columns[0][0]) | (s.shr(1) & ~tables.columns[win_n - 1][win_n - 1]);
    return h | h.shl(win_n) | h.shr(win_n);
}

// The window tiles within r of window tile (cx, cy), which may lie outside it.
Window box(int cx, int cy, int r) {
    const int x0 = std::max(0, cx - r), x1 = std::min(win_n - 1, cx + r);
    const int y0 = std::max(0, cy - r), y1 = std::min(win_n - 1, cy + r);
    if (x0 > x1 || y0 > y1) return {};
    return tables.columns[x0][x1] & tables.rows[y0][y1];
}

// A mask laid out around tile q, read in the window around q - (dx, dy).
Window shift(Window m, int dx, int dy) {
    if (dx <= -win_n || dx >= win_n || dy <= -win_n || dy >= win_n) return {};
    const int k = dx + win_n * dy;
    m = k >= 0 ? m.shl(k) : m.shr(-k);
    if (dx > 0) m &= ~tables.columns[0][dx - 1];
    if (dx < 0) m &= ~tables.columns[win_n + dx][win_n - 1];
    return m;
}

// Static terrain as packed bits, read a window row at a time without host calls (host tests if
// the layout is unclear).
struct Terrain {
    static constexpr std::size_t bytes = 100 * 100 / 8 + 8;
    bool ready = false, packed = false;
    int width = 0, height = 0;
    const StaticMap* map = nullptr;
    std::array<std::uint8_t, bytes> walls, blocked, bushes, camps;

    static bool bit(const std::array<std::uint8_t, bytes>& b, int i) { return b[static_cast<std::size_t>(i >> 3)] >> (i & 7) & 1; }
    // Bit k: tile (x0 + k, y), for the window's width.
    std::uint32_t row(const std::array<std::uint8_t, bytes>& b, int x0, int y) const {
        if (y < 0 || y >= height) return 0;
        const int lo = std::max(0, -x0), hi = std::min(win_n, width - x0);
        if (lo >= hi) return 0;
        const int i = x0 + lo + y * width;
        std::uint64_t word;
        std::memcpy(&word, &b[static_cast<std::size_t>(i >> 3)], sizeof word);
        return static_cast<std::uint32_t>((word >> (i & 7)) & ((std::uint64_t{1} << (hi - lo)) - 1)) << lo;
    }
    bool test(const std::array<std::uint8_t, bytes>& b, const bitboard& board, vec2 p) const {
        return packed ? bit(b, p.x + p.y * width) : board.is_set(p);
    }
    bool bush(vec2 p) const { return test(bushes, map->bushes, p); }
    bool inside(vec2 p) const { return p.x >= 0 && p.y >= 0 && p.x < width && p.y < height; }
};

const Terrain& terrain(const StaticMap& map) {
    static Terrain t;
    if (t.ready) return t;
    t.ready = true;
    t.map = &map;
    t.width = map.width;
    t.height = map.height;
    const std::size_t size = bitboard::linear_buffer_size();
    if (size + 8 > Terrain::bytes) return t;
    map.walls.export_linear_buffer({t.walls.data(), size});
    // Bits run from the low end of each byte; check on a set tile.
    if (!map.walls.is_empty()) {
        const vec2 probe = first_tile(map.walls);
        if (!Terrain::bit(t.walls, probe.x + probe.y * t.width)) return t;
    }
    map.blocked_for_them.export_linear_buffer({t.blocked.data(), size});
    map.bushes.export_linear_buffer({t.bushes.data(), size});
    map.camp_tiles.export_linear_buffer({t.camps.data(), size});
    t.packed = true;
    return t;
}

bool live_camp(const World& world, vec2 p) {
    const int g = world.map().group_at(p);
    if (g < 0 || world.camps[g].state != CampState::alive) return false;
    const auto& members = world.map().groups[g].members;
    for (std::size_t i = 0; i < members.size(); ++i)
        if (members[i].pos == p) return world.camps[g].health[i] > 0;
    return false;
}

// Tiles a visible enemy ward sees this round: a target there is in sight of whoever owns it.
const bitboard* ward_sight(const World& world) {
    static int round = -1;
    static bool any = false;
    static bitboard seen{cambc::uninitialized}, wards{cambc::uninitialized}, cast{cambc::uninitialized};
    if (round != world.round) {
        round = world.round;
        cambc::vision::ward_tiles_into(team::enemy, wards);
        any = !wards.is_empty();
        if (any) {
            seen.clear();
            const auto r = static_cast<std::uint16_t>(cambc::constants::ward_vision_radius);
            for (const vec2 w : Tiles<64>{wards}) {
                world.map().walls.shadow_cast_into(w, r, cast);
                seen |= cast;
            }
        }
    }
    return any ? &seen : nullptr;
}

// Who sees p, laid out around p: within 1 (`far` false) or within win_r. Far masks depend only on
// terrain, so they are kept for the game.
Window sight(const World& world, vec2 p, bool far) {
    const auto& t = terrain(world.map());
    if (!far) {
        if (!t.bush(p)) return tables.square[1];
        // A bush tile is seen only from its own cluster; diagonal bushes join through a bush
        // beside both.
        Window m = win_bit(win_r, win_r);
        for (const vec2 d : directions) {
            const vec2 q = p + d;
            if (!t.inside(q) || !t.bush(q)) continue;
            if (d.x == 0 || d.y == 0 || t.bush({p.x + d.x, p.y}) || t.bush({p.x, p.y + d.y}))
                m |= win_bit(win_r + d.x, win_r + d.y);
        }
        return m;
    }
    static std::array<Window, 100 * 100> masks;
    static std::array<std::uint8_t, 100 * 100> known;
    const auto i = static_cast<std::size_t>(p.x + p.y * t.width);
    if (i < known.size() && known[i]) return masks[i];
    const auto& map = world.map();
    // Viewers outside bushes exactly; those inside one by walls alone, as finding the clusters can
    // cost tens of thousands: a viewer in another cluster, or behind bushes, may be counted.
    static bitboard viewers{cambc::uninitialized}, outside{cambc::uninitialized};
    map.walls.shadow_cast_into(p, static_cast<std::uint16_t>(win_r), viewers);
    viewers &= map.bushes;
    if (!t.bush(p)) {
        map.walls_and_bushes.shadow_cast_into(p, static_cast<std::uint16_t>(win_r), outside);
        drop(outside, map.bushes);
        viewers |= outside;
    }
    Window m;
    for (const vec2 q : Tiles<win_n * win_n>{within(viewers, p, win_r)})
        m |= tables.bits[static_cast<std::size_t>((q.y - p.y + win_r) * win_n + q.x - p.x + win_r)];
    if (i < known.size()) masks[i] = m, known[i] = 1;
    return m;
}

} // namespace

int Reach::add(Window from, int range, bool sight, float damage, bool stuns, bool walked) {
    for (int i = 0; i < count_; ++i) {
        auto& w = ways_[static_cast<std::size_t>(i)];
        if (w.range == range && w.sight == sight && w.walked == walked && w.from.lo == from.lo && w.from.hi == from.hi) {
            w.damage = std::max(w.damage, damage);
            w.stuns = w.stuns || stuns;
            return i;
        }
    }
    if (count_ == static_cast<int>(ways_.size())) return -1;
    int extent = win_r;
    while (extent > 0 && !(from & ~tables.square[static_cast<std::size_t>(extent - 1)])) --extent;
    const int far = extent + range;
    ways_[static_cast<std::size_t>(count_)] = {from, damage, static_cast<std::int8_t>(range), static_cast<std::int8_t>(far), sight, stuns, walked};
    reach_ = std::max(reach_, far);
    return count_++;
}

void Reach::build(const World& world, const ChampionBelief& e, int turn_round, bool twice) {
    world_ = &world;
    wards_ = ward_sight(world);
    origin_ = e.pos;
    count_ = 0;
    basic_ = -1;
    static std::uint32_t builds = 0;
    stamp_ = ++builds;
    twice_ = twice;
    strength_ = e.strength;
    reach_ = -1;
    const auto& f = e.facts();
    const bool uncertain = e.cooldowns_uncertain();
    const std::array<bool, 2> ready{uncertain || e.ability_ready(0, turn_round), uncertain || e.ability_ready(1, turn_round)};
    const int dash_slot = f.slot_of(AbilityKind::dash);
    const bool dash = dash_slot >= 0 && ready[static_cast<std::size_t>(dash_slot)];
    // The farthest its moves reach: terrain beyond it is never read.
    const int radius = std::min(win_r, (twice ? 1 : 0) + (dash ? (f.ranged ? 2 : 3) : 1));
    // land: a free tile open to it; pass: a dash path may cross it.
    const auto& t = terrain(world.map());
    Window land, pass, camps;
    const int x0 = origin_.x - win_r;
    for (int wy = win_r - radius; wy <= win_r + radius; ++wy) {
        const int y = origin_.y - win_r + wy;
        std::uint32_t open = 0, through = 0, camp = 0;
        if (t.packed) {
            const int lo = std::max(0, -x0), hi = std::min(win_n, t.width - x0);
            const std::uint32_t valid = y < 0 || y >= t.height || lo >= hi ? 0u : ((1u << hi) - 1) & ~((1u << lo) - 1);
            through = valid & ~t.row(t.walls, x0, y);
            open = valid & ~t.row(t.blocked, x0, y);
            camp = t.row(t.camps, x0, y) & valid;
        } else {
            for (int k = 0; k < win_n; ++k) {
                const vec2 p{x0 + k, y};
                if (!t.inside(p) || world.map().walls.is_set(p)) continue;
                through |= 1u << k;
                if (!world.map().blocked_for_them.is_set(p)) open |= 1u << k;
                if (world.map().group_at(p) >= 0) camp |= 1u << k;
            }
        }
        pass |= Window{through, 0}.shl(wy * win_n);
        land |= Window{open, 0}.shl(wy * win_n);
        if (camp) camps |= Window{camp, 0}.shl(wy * win_n);
    }
    for (int word = 0; word < 2; ++word)
        for (std::uint64_t bits = word ? camps.hi : camps.lo; bits; bits &= bits - 1) {
            const int i = 64 * word + std::countr_zero(bits);
            if (live_camp(world, {origin_.x - win_r + i % win_n, origin_.y - win_r + i / win_n}))
                pass &= ~tables.bits[static_cast<std::size_t>(i)], land &= ~tables.bits[static_cast<std::size_t>(i)];
        }
    for (const auto& a : world.allies)
        if (a.alive && a.visible && !a.is_self && dist(a.pos, origin_) <= win_r)
            land &= ~win_bit(a.pos.x - origin_.x + win_r, a.pos.y - origin_.y + win_r);
    const Window at = win_bit(win_r, win_r);
    const auto walk = [&](Window s) { return s | (dilate(s) & land); };
    const auto dash_from = [&](Window s) {
        const Window first = dilate(s) & pass;
        return s | ((first | (dilate(first) & pass)) & land);
    };
    const Window walked1 = walk(at);
    const Window basic_from = f.ranged ? at : walked1;
    const int range = f.attack_range();
    const float s = e.strength;
    for (int turn = 0; turn < (twice ? 2 : 1); ++turn) {
        const bool walked = turn == 1;
        const auto from = [&](Window x) { return walked ? walk(x) : x; };
        const int basic = add(from(basic_from), range, true, s, false, walked);
        if (!walked) basic_ = basic;
        for (std::size_t slot = 0; slot < 2; ++slot) {
            if (!ready[slot]) continue;
            const auto& a = f.abilities[slot];
            const float spell = a.multiplier * e.focus;
            switch (a.kind) {
            case AbilityKind::attack_reset:
                add(from(basic_from), range, true, 2 * s, a.stuns, walked);
                if (f.ranged) add(from(walked1), range, true, s, a.stuns, walked); // walk, reset, attack
                break;
            case AbilityKind::dash:
                add(from(f.ranged ? dash_from(at) : dash_from(walked1) | walk(dash_from(at))), range, true, s, false, walked);
                break;
            case AbilityKind::damage:
                // Excludes walking but not the basic attack.
                add(from(at), a.reach(), a.target == Targeting::unit, spell, a.stuns, walked);
                add(from(at), range, true, spell + s, a.stuns, walked);
                break;
            case AbilityKind::stun:
                add(from(a.excludes_walking ? at : walked1), a.reach(), a.target == Targeting::unit, 0, true, walked);
                break;
            default: break;
            }
        }
    }
}

Blow Reach::at(vec2 p) const {
    auto& memo = memo_[static_cast<std::size_t>((p.x & 7) | (p.y & 7) << 3)];
    if (memo.stamp == stamp_ && memo.p == p) return memo.blow;
    Blow out;
    const int dx = p.x - origin_.x, dy = p.y - origin_.y;
    if (std::max(std::abs(dx), std::abs(dy)) <= reach_ && terrain(world_->map()).inside(p)) {
        // Who sees p, in this window; worked out on first need. Whoever owns a ward that sees p
        // sees it from anywhere.
        const bool warded = wards_ && wards_->is_set(p);
        Window near, far;
        bool near_known = warded, far_known = warded;
        if (warded) near = far = win_full;
        float single = -1, walked = -1;
        bool basic = false;
        for (int i = 0; i < count_; ++i) {
            const auto& w = ways_[static_cast<std::size_t>(i)];
            if (std::max(std::abs(dx), std::abs(dy)) > w.far) continue;
            auto& best = w.walked ? walked : single;
            if (out.hits && w.damage <= best && (!w.stuns || out.stuns) && !(twice_ && i == basic_)) continue;
            Window from = w.from & box(dx + win_r, dy + win_r, w.range);
            if (!from) continue;
            if (w.sight) {
                if (w.range <= 1) {
                    if (!near_known) near = shift(sight(*world_, p, false), dx, dy), near_known = true;
                    from &= near;
                } else {
                    if (!far_known) far = shift(sight(*world_, p, true), dx, dy), far_known = true;
                    from &= far;
                }
                if (!from) continue;
            }
            best = std::max(best, w.damage);
            basic |= i == basic_;
            out.stuns |= w.stuns;
            out.hits = true;
        }
        if (out.hits) out.damage = std::max({0.0f, walked, single < 0 ? 0.0f : single + (twice_ && basic ? strength_ : 0.0f)});
    }
    memo = {p, out, stamp_};
    return out;
}

Blow Threat::at(vec2 p) const {
    if (reach) return reach->at(p);
    if (visible) return strike.blow(dist(p, pos));
    return strike.blow(steps ? steps->get(p) : unreachable);
}

// An unseen enemy's best chance to be in reach of a tile, or 0 if too slight to count.
float unseen_weight(int reach, int tiles) {
    const float weight = std::min(1.0f, static_cast<float>((2 * reach + 1) * (2 * reach + 1)) / static_cast<float>(tiles));
    return tiles == 0 || weight < credible_weight ? 0.0f : weight;
}

// Next to a compact possible set of side ~sqrt(tiles), the chance of being in reach falls by about
// 1 / sqrt(tiles) per step out; keep the tiles still near the cutoff.
int unseen_radius(int reach, int tiles) {
    return std::clamp(static_cast<int>(static_cast<float>(reach) + 1.5f - credible_weight * std::sqrt(static_cast<float>(tiles))), 0, reach);
}

namespace {

// The most an unseen enemy's threat has cost to build so far, 0 before the first.
std::uint64_t& costliest_unseen() {
    static std::uint64_t cost = 0;
    return cost;
}

std::vector<Threat>& threat_pool() {
    static std::vector<Threat> pool;
    return pool;
}

std::array<Reach, 16>& reach_pool() {
    static std::array<Reach, 16> pool;
    return pool;
}

} // namespace

std::vector<Safety::CampHit>& Safety::member_pool() {
    static std::vector<CampHit> pool;
    return pool;
}

Safety::Safety(const World& world) : world_{world}, threats_{threat_pool()}, members_{member_pool()} {}

const std::vector<Safety::CampHit>& Safety::awake_members() {
    if (!members_known_) {
        members_known_ = true;
        members_.clear();
        // Each monster attacks the nearest champion within range, ties to the one acting first in
        // the round of the next camp phase.
        struct Other {
            vec2 pos;
            bool first;
        };
        union Others { // the first n only: the engine charges for every byte written
            std::array<Other, 2 * max_fighters> at;
            Others() {}
        } others;
        int n = -1;
        const int next = world_.round + 1, self_slot = world_.slot(world_.me(), next);
        static bitboard seen{cambc::uninitialized}, camps{cambc::uninitialized};
        bool reread = false;
        const auto& groups = world_.map().groups;
        world_.each_stirring([&](int g) {
            const auto& c = world_.camps[g];
            if (n < 0) {
                n = 0;
                for (const auto* side : {&world_.allies, &world_.enemies})
                    for (const auto& o : *side)
                        if (n < static_cast<int>(others.at.size()) && o.alive && o.visible && !o.is_self && !gone(o))
                            others.at[n++] = {o.pos, world_.slot(o, next) < self_slot};
                if (refresh_) {
                    reread = true;
                    cambc::vision::visible_tiles_into(seen);
                    cambc::vision::camp_tiles_into(camps);
                }
            }
            const float w = c.awake == Awake::awake ? 1.0f : unknown_camp_weight;
            for (std::size_t i = 0; i < groups[g].members.size(); ++i) {
                const auto& m = groups[g].members[i];
                if (c.health[i] <= 0 || m.strength <= 0 || (reread && seen.is_set(m.pos) && !camps.is_set(m.pos))) continue;
                int reach = camp_attack_range;
                for (int k = 0; k < n; ++k)
                    reach = std::min(reach, dist(others.at[k].pos, m.pos) - (others.at[k].first ? 1 : 0));
                if (reach >= 0) members_.push_back({m.pos, m.strength, w, reach});
            }
        });
    }
    return members_;
}

bool Safety::gone(const ChampionBelief& c) {
    if (!refresh_ || c.side != team::enemy || !c.visible || c.index >= static_cast<int>(gone_.size())) return false;
    auto& known = gone_[static_cast<std::size_t>(c.index)];
    if (known == 0) {
        std::int32_t alive{};
        cambc::detail::check(cambc::detail::sdk_champion_is_alive(static_cast<std::uint32_t>(c.handle), &alive));
        known = alive != 0 ? 1 : 2;
    }
    return known == 2;
}

void Safety::invalidate() {
    built_ = false;
    refresh_ = true;
    reached_ = 0;
    build_cost_ = 0;
    threat_count_ = 0;
    members_known_ = false;
    camp_area_.reset();
    enemy_area_.reset();
    fight_count_ = 0;
    gone_.fill(0);
}

void Safety::refresh() {
    refresh_ = true;
    gone_.fill(0);
    build_cost_ = 0;
    if (!built_ && !members_known_) return;
    bool changed = false;
    for (const auto& e : world_.enemies) changed |= e.alive && gone(e);
    if (!changed && members_known_ && !members_.empty()) {
        static bitboard seen{cambc::uninitialized}, camps{cambc::uninitialized};
        cambc::vision::visible_tiles_into(seen);
        cambc::vision::camp_tiles_into(camps);
        for (const auto& m : members_) changed |= seen.is_set(m.pos) && !camps.is_set(m.pos);
    }
    if (changed) invalidate();
}

Safety::Foe& Safety::foe(const ChampionBelief& e) {
    auto& x = foes_[static_cast<std::size_t>(e.index)];
    if (!(known_ >> e.index & 1)) {
        known_ |= static_cast<std::uint16_t>(1u << e.index);
        x.strike = threat_strike(world_, e);
        x.tiles = 0;
        x.weight = 0;
        x.asked = {-1, -1};
        if (!e.visible && x.strike.reach >= 0) {
            x.tiles = static_cast<int>(e.possible.count());
            x.weight = unseen_weight(x.strike.reach, x.tiles);
        }
    }
    return x;
}

namespace {

Threat& next_threat(std::vector<Threat>& pool, int& count) {
    if (count == static_cast<int>(pool.size())) pool.emplace_back();
    return pool[static_cast<std::size_t>(count++)];
}

} // namespace

void Safety::build() {
    world_.throw_if_stale();
    if (built_) return;
    built_ = true;
    FuelMeter meter{"safety"};
    // One per enemy, reused between builds: a new field allocates and clears ~13k bytes.
    static std::vector<std::unique_ptr<cambc::distance_field>> fields;
    const auto field_of = [&](int i) -> cambc::distance_field& {
        if (fields.size() <= static_cast<std::size_t>(i)) fields.resize(static_cast<std::size_t>(i) + 1);
        auto& field = fields[static_cast<std::size_t>(i)];
        if (!field) field = std::make_unique<cambc::distance_field>();
        return *field;
    };
    for (const auto& e : world_.enemies) {
        if (!e.alive || (!e.visible && !e.tracked) || gone(e)) continue;
        const auto& x = foe(e);
        const auto& s = x.strike;
        const int reach = s.reach;
        if (reach < 0) continue;
        if (e.visible) {
            auto& t = next_threat(threats_, threat_count_);
            t.enemy = e.index;
            t.strike = s;
            t.visible = true;
            t.pos = e.pos;
            t.tiles = 1;
            t.steps = nullptr;
            t.reach = nullptr;
            t.area.clear();
            // A superset: a walls field per enemy each turn would cost ~3k.
            t.reach = &reach_of(e);
            t.area.draw_chebyshev(e.pos, static_cast<float>(t.reach->reach()));
            continue;
        }
        const int tiles = x.tiles;
        const float weight = x.weight;
        if (weight == 0) continue;
        const auto before = fuel();
        auto& t = next_threat(threats_, threat_count_);
        t.enemy = e.index;
        t.strike = s;
        t.visible = false;
        t.pos = {-1, -1};
        t.tiles = tiles;
        t.reach = nullptr;
        const int radius = unseen_radius(reach, tiles);
        auto& field = field_of(e.index);
        t.area.clear();
        field.compute(world_.map().walls, e.possible, t.area, static_cast<std::uint16_t>(radius));
        t.steps = &field;
        if (const auto after = fuel(); after < before) costliest_unseen() = std::max(costliest_unseen(), before - after);
    }
}

std::span<const Threat> Safety::threats() {
    build();
    return {threats_.data(), static_cast<std::size_t>(threat_count_)};
}

// f(enemy, blow) for each enemy build() makes a threat of, the blow at least its threat's at p:
// exact if visible; if unseen, its strike at 0 when a tile it could be on is within its reach of
// p, else none, as its field is capped within the reach. Strikes only weaken with distance, so
// this bounds the threats' damage and hits at p without building them.
template <class F> void Safety::each_threat(vec2 p, F&& f) {
    for (const auto& e : world_.enemies) {
        if (!e.alive || (!e.visible && !e.tracked) || gone(e)) continue;
        auto& x = foe(e);
        const auto& s = x.strike;
        if (s.reach < 0) continue;
        if (e.visible) f(e, blow(e, p));
        else if (x.weight > 0) {
            if (x.asked != p) x.asked = p, x.near = any_within(e.possible, p, s.reach);
            f(e, x.near ? s.blow(0) : Blow{});
        }
    }
}

const Reach& Safety::reach_of(const ChampionBelief& e) {
    auto& r = reach_pool()[static_cast<std::size_t>(e.index)];
    if (!(reached_ >> e.index & 1)) {
        reached_ |= static_cast<std::uint16_t>(1u << e.index);
        r.build(world_, e, next_turn_round(world_, e), turns_before_ours(world_, e) >= 2);
    }
    return r;
}

Blow Safety::blow(const ChampionBelief& e, vec2 p) {
    const auto& s = foe(e).strike;
    if (s.reach < 0 || dist(p, e.pos) > s.reach) return {};
    return reach_of(e).at(p);
}

int Safety::approach(const ChampionBelief& e, vec2 p) {
    const int reach = foe(e).strike.reach;
    return blow(e, p).hits ? 0 : std::max(1, dist(p, e.pos) - reach);
}

int Safety::threats_at(vec2 p, std::array<ThreatAt, 16>& out) {
    int n = 0;
    if (built_) {
        for (const auto& t : threats())
            if (n < static_cast<int>(out.size())) out[n++] = {t.enemy, t.at(p)};
        return n;
    }
    for (const auto& e : world_.enemies) {
        if (!e.alive || (!e.visible && !e.tracked) || gone(e) || n == static_cast<int>(out.size())) continue;
        const auto& x = foe(e);
        if (x.strike.reach < 0) continue;
        if (e.visible) {
            out[n++] = {e.index, blow(e, p)};
        } else if (x.weight > 0) {
            const int radius = unseen_radius(x.strike.reach, x.tiles);
            int d = any_within(e.possible, p, radius) ? 0 : radius + 1;
            while (d < radius && !any_within(e.possible, p, d)) ++d;
            out[n++] = {e.index, x.strike.blow(d <= radius ? d : static_cast<int>(unreachable))};
        }
    }
    return n;
}

bool Safety::any_threat() {
    if (built_) return threat_count_ > 0;
    for (const auto& e : world_.enemies) {
        if (!e.alive || (!e.visible && !e.tracked) || gone(e)) continue;
        const auto& x = foe(e);
        if (x.strike.reach >= 0 && (e.visible || x.weight > 0)) return true;
    }
    return false;
}

float Safety::damage_bound(vec2 p, bool double_unacted) {
    float total = camp_damage(p);
    each_threat(p, [&](const ChampionBelief& e, const Blow& b) {
        total += b.damage * (double_unacted && e.visible && !e.acted ? 2.0f : 1.0f);
    });
    return total;
}

bool Safety::may_be_hit(vec2 p) {
    bool hit = false;
    each_threat(p, [&](const ChampionBelief&, const Blow& b) { hit |= b.hits; });
    return hit;
}

float Safety::chance_in_reach(const Threat& t, vec2 p) {
    if (t.visible) return t.at(p).hits ? 1.0f : 0.0f;
    if (!t.area.is_set(p)) return 0.0f;
    const auto& possible = world_.enemies[t.enemy].possible;
    const auto near = count_within(possible, p, t.strike.reach);
    return std::min(1.0f, static_cast<float>(near) / static_cast<float>(t.tiles));
}

float Safety::camp_damage(vec2 p, bool worst) {
    float total = 0;
    for (const auto& m : awake_members())
        if (dist(p, m.pos) <= m.reach) total += worst ? m.strength : m.strength * m.weight;
    return total;
}

float Safety::worst_damage(vec2 p) {
    float total = camp_damage(p, true);
    for (const auto& t : threats())
        total += t.at(p).damage;
    return total;
}

float Safety::expected_damage(vec2 p) {
    float total = camp_damage(p, false);
    for (const auto& t : threats())
        if (const auto b = t.at(p); b.hits) total += chance_in_reach(t, p) * hit_given_reach * b.damage;
    return total;
}

// The chance of being hit only grows with each factor, so the answer is settled as soon as it
// reaches the line: often by a camp, before the threats are built.
bool Safety::threatened(vec2 p) {
    float safe = 1;
    for (const auto& m : awake_members())
        if (dist(p, m.pos) <= m.reach && 1 - (safe *= 1 - m.weight) >= recall_risk) return true;
    if (!built_ && !may_be_hit(p)) return false;
    for (const auto& t : threats())
        if (t.at(p).hits && 1 - (safe *= 1 - chance_in_reach(t, p) * hit_given_reach) >= recall_risk)
            return true;
    return false;
}

const bitboard& Safety::camp_area() {
    if (!camp_area_) {
        bitboard b;
        for (const auto& m : awake_members())
            if (m.reach > 0) b.draw_chebyshev(m.pos, static_cast<float>(m.reach));
        camp_area_ = std::move(b);
    }
    return *camp_area_;
}

const bitboard& Safety::enemy_area() {
    if (!enemy_area_) {
        bitboard any;
        for (const auto& t : threats())
            any |= t.area;
        enemy_area_ = std::move(any);
    }
    return *enemy_area_;
}

bitboard Safety::avoid() { return camp_area() | enemy_area(); }

// Every unseen threat is credible: unseen_weight() drops the rest. Its area is `possible` grown by
// its radius, so it comes within r of p exactly when `possible` comes within radius + r.
bool Safety::avoid_within(vec2 p, int r) {
    for (const auto& m : awake_members())
        if (m.reach > 0 && dist(p, m.pos) <= m.reach + r) return true;
    if (built_) return any_within(enemy_area(), p, r);
    for (const auto& e : world_.enemies) {
        if (!e.alive || (!e.visible && !e.tracked) || gone(e)) continue;
        const auto& x = foe(e);
        const int reach = x.strike.reach;
        if (reach < 0) continue;
        if (e.visible) {
            if (dist(p, e.pos) <= reach + r) return true;
            continue;
        }
        if (x.weight > 0 && any_within(e.possible, p, unseen_radius(reach, x.tiles) + r)) return true;
    }
    return false;
}

std::uint32_t Safety::fight_key(vec2 p, int exclude) {
    std::uint32_t key = 0;
    bool hit = false;
    for (const auto& t : threats()) {
        if (t.enemy == exclude || !t.at(p).hits) continue;
        hit = true;
        key |= 1u << (16 + t.enemy);
    }
    if (!hit) return no_fight;
    for (std::size_t i = 0; i < world_.allies.size(); ++i)
        if (fights_with(world_.allies[i], p)) key |= 1u << i;
    return key;
}

const Trade* Safety::memo(std::uint32_t key) const {
    for (int i = 0; i < std::min(fight_count_, max_fights); ++i)
        if (fights_[i].key == key) return &fights_[i].trade;
    return nullptr;
}

const Trade* Safety::known_fight(vec2 p) {
    const auto key = fight_key(p, -1);
    if (key == no_fight) {
        static const Trade none{};
        return &none;
    }
    return memo(key);
}

Trade Safety::fight(vec2 p, int exclude) {
    world_.throw_if_stale();
    const auto key = fight_key(p, exclude);
    return key == no_fight ? Trade{} : fight_of(key);
}

Trade Safety::fight_of(std::uint32_t key) {
    if (const auto* t = memo(key)) return *t;
    Side us, them;
    for (std::size_t i = 0; i < world_.allies.size(); ++i) {
        const auto& a = world_.allies[i];
        if (!(key >> i & 1)) continue;
        if (a.is_self) us.self = us.count;
        us.add(fighter(world_, a, made_));
    }
    for (const auto& t : threats()) {
        const auto& e = world_.enemies[t.enemy];
        if (key >> (16 + t.enemy) & 1) them.add(fighter(world_, e, made_));
    }
    const auto before = fuel();
    auto& slot = fights_[fight_count_++ % max_fights];
    slot = {key, trade(us, them, end_reserve)};
    if (const auto after = fuel(); after < before) costliest_fight_ = std::max(costliest_fight_, before - after);
    return slot.trade;
}

std::uint64_t Safety::fight_cost_estimate() {
    if (champions_ < 0) {
        champions_ = 0;
        for (const auto& a : world_.allies) champions_ += a.alive && (a.is_self || a.visible);
        for (const auto& e : world_.enemies) champions_ += e.alive && e.visible;
    }
    const auto champions = static_cast<std::uint64_t>(champions_);
    const auto simulation = std::max({std::uint64_t{10000}, 2000 + 2000 * champions, costliest_fight_ + costliest_fight_ / 4});
    return simulation + build_cost_estimate();
}

std::uint64_t Safety::build_cost_estimate() {
    if (built_) return 0;
    if (build_cost_) return build_cost_;
    std::uint64_t cost = 2000;
    for (const auto& e : world_.enemies) {
        if (!e.alive || (!e.visible && !e.tracked) || gone(e)) continue;
        if (e.visible) cost += 4000; // with its Reach
        else cost += foe(e).weight > 0 ? (costliest_unseen() ? costliest_unseen() + costliest_unseen() / 4 : 3000 + 25 * search_chunks()) : 500;
    }
    build_cost_ = cost;
    return cost;
}

Trade Safety::pursuit(vec2 p, int approach) {
    world_.throw_if_stale();
    Side us, them;
    const auto& spawn = world_.map().near_enemy_spawn;
    for (const auto& e : world_.enemies) {
        if (!e.alive || !e.visible || gone(e) || spawn.is_set(e.pos)) continue;
        const auto& s = foe(e).strike;
        if (s.reach < 0 || dist(p, e.pos) - s.reach > approach) continue;
        const int walk = this->approach(e, p);
        if (walk > approach) continue;
        const int k = them.count;
        them.add(fighter(world_, e, made_));
        if (them.count > k) them.fighters[k].arrives_at = walk;
    }
    if (them.count == 0) return {};
    join_allies(world_, us, p, made_);
    us.camp = camp_damage(p, false);
    return trade(us, them, end_reserve, false);
}

int Safety::turns_to_kill_idle(vec2 p, int horizon) {
    Side us, them;
    us.add(fighter(world_, world_.me(), made_));
    us.fighters[0].idle = true;
    us.camp = camp_damage(p, false);
    for (const auto& e : world_.enemies) {
        if (!e.alive || !e.visible || gone(e)) continue;
        const auto& s = foe(e).strike;
        if (s.reach < 0 || dist(p, e.pos) - s.reach >= horizon) continue;
        const int walk = approach(e, p);
        if (walk >= horizon) continue;
        const int k = them.count;
        them.add(fighter(world_, e, made_));
        if (them.count > k) them.fighters[k].arrives_at = walk;
    }
    if (them.count == 0 && us.camp <= 0) return 0;
    return simulate(us, them, true, nullptr, horizon).second;
}

bool Safety::lethal(vec2 p) {
    const float health = world_.me().health;
    // Most turns no enemy is near enough; skip the threat build then.
    if (!built_ && damage_bound(p) < health) return false;
    return worst_damage(p) >= health;
}

} // namespace aph
