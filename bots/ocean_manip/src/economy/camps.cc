// Camps: attacks on them, what clearing one costs in rounds and damage taken, and what it is worth.
#include "../bot_parts.h"
#if defined(__wasm_simd128__)
#include <wasm_simd128.h>
#endif

namespace aph {

namespace {

// The member of group G on tile p, or -1.
int member_at(const CampGroup& G, vec2 p) {
    for (int i = 0; i < static_cast<int>(G.members.size()); ++i)
        if (G.members[i].pos == p) return i;
    return -1;
}

// A member on a live tile: full health while our belief still holds it dead (it respawned unseen).
float live_health(const World& world, int g, int i) {
    const float hp = world.camps[g].health[i];
    return hp > 0 ? hp : world.map().groups[g].members[i].max_health;
}

// The members in reach of a basic attack, of groups `allowed` accepts, best first: most damage
// removed per point of health, Varg's splash adding the members beside it in the same units. With
// `resources`, harmless groups' members also go there, leaving the ordinary list as it was.
template <class Allowed> CampAttackTargets camp_attack_targets(const World& world, Allowed allowed, CampAttackTargets* resources) {
    CampAttackTargets targets;
    if (!my_can_attack()) return targets;
    const int range = world.me().facts().attack_range();
    const vec2 here = my_position();
    if (!camp_in_reach(world, here, range)) return targets;
    const bool splash = world.me().facts().passive == Passive::splash_attack;
    const float hit = splash ? my_strength() * damage_scale(world.me().facts().passive, my_health(), my_max_health()) * camp_dealt_factor() : 0.0f;
    const auto& map = world.map();
    // Ranked as they come, ties in scan order, so a full list keeps the best rather than the first.
    const auto insert = [](CampAttackTargets& list, const CampAttackTarget& t) {
        constexpr int cap = static_cast<int>(std::tuple_size_v<decltype(list.found)>);
        int i = list.n < cap ? list.n++ : cap;
        for (; i > 0 && list.found[i - 1].score < t.score; --i)
            if (i < cap) list.found[i] = list.found[i - 1];
        if (i < cap) list.found[i] = t;
    };
    for (auto p : positions_within(live_camp_tiles(), here, range)) {
        const int g = map.group_at(p);
        if (g < 0 || (map.groups[g].has_monolith && g != siege_group())) continue;
        const bool ordinary = allowed(g);
        const bool resource = resources && !map.groups[g].has_monolith && map.groups[g].strength <= 0;
        if (!ordinary && !resource) continue;
        const auto& members = map.groups[g].members;
        const int i = member_at(map.groups[g], p);
        if (i < 0) continue;
        float score = members[i].strength / std::max(1.0f, live_health(world, g, i));
        if (splash) {
            // The main score is per point of our hit; a splashed member takes the hit up to its health.
            // Another group's only once fully awake: the splash wakes a sleeping one (rules camps.wake).
            for (int dy = -1; dy <= 1; ++dy)
                for (int dx = -1; dx <= 1; ++dx) {
                    const vec2 q{p.x + dx, p.y + dy};
                    if ((dx == 0 && dy == 0) || !in_bounds(q)) continue;
                    const int h = map.group_at(q);
                    if (h < 0 || (h != g && (world.camps[h].state != CampState::alive || !world.camps[h].fully_awake()))) continue;
                    const int j = member_at(map.groups[h], q);
                    if (j < 0) continue;
                    const float hp = world.camps[h].health[j];
                    if (hp > 0) score += map.groups[h].members[j].strength * std::min(1.0f, hp / std::max(1.0f, hit)) / std::max(1.0f, hp);
                }
        }
        if (ordinary) insert(targets, {g, i, score});
        if (resource) insert(*resources, {g, i, score});
    }
    return targets;
}

bool attack_camp_target(const World& world, const CampAttackTarget& target) {
    throw_if_stale();
    try {
        cambc::self().attack(world.map().groups[target.group].camp(target.member));
        ++camp_hits();
        return true;
    } catch (const cambc::error&) {
    }
    return false;
}

int attack_camp_targets(const World& world, const CampAttackTargets& targets) {
    for (int k = 0; k < targets.n; ++k)
        if (attack_camp_target(world, targets.found[k])) return targets.found[k].group;
    return -1;
}

// Attack the best camp_attack_targets that will take the hit; the group attacked, or -1.
template <class Allowed> int attack_camp(const World& world, Allowed allowed) {
    return attack_camp_targets(world, camp_attack_targets(world, allowed));
}

// A static field counts camps as cleared, so its walk can end at a live camp holding the only way
// on. When every step down the field is onto one, hit the weakest in reach if we outlast the fire
// of its group's members that reach us for as long as our basic attacks take to kill it. Camps
// never regenerate: a retreat and return still make progress.
// Our first hit wakes the group and we stand here until our turn after the kill: one camp phase per
// turn, the last without the killed member.
bool breach(const World& world, const Field& field) {
    if (!my_can_attack()) return false;
    const vec2 here = my_position();
    const int at = field.at(here);
    if (at == 0 || at == unreachable) return false;
    const auto& map = world.map();
    const auto& live = live_camp_tiles();
    int group = -1, member = -1;
    float weakest = 0;
    for (const auto d : directions) {
        const vec2 p = here + d;
        if (!in_bounds(p) || field.at(p) >= at) continue;
        if (!test(live, p)) return false; // something else holds this way on
        const int g = map.group_at(p);
        if (g < 0 || map.groups[g].has_monolith) return false;
        const int i = member_at(map.groups[g], p);
        if (i < 0) continue;
        const float hp = live_health(world, g, i);
        if (group < 0 || hp < weakest) group = g, member = i, weakest = hp;
    }
    if (group < 0) return false;
    // Hitting any member wakes the group.
    float fire = 0, target_fire = 0;
    const auto& members = map.groups[group].members;
    for (int i = 0; i < static_cast<int>(members.size()); ++i)
        if (world.camps[group].health[i] > 0 && dist(here, members[i].pos) <= members[i].reach) {
            fire += members[i].strength;
            if (i == member) target_fire = members[i].strength;
        }
    const int hits = static_cast<int>(std::ceil(weakest / std::max(1.0f, my_strength() * damage_scale(world.me().facts().passive, my_health(), my_max_health()) * camp_dealt_factor())));
    // A turn lands two hits whenever the reset is ready (reset_and_attack_camp): from its cooldown, then
    // every cooldown.
    const auto& f = world.me().facts();
    const int reset = f.slot_of(AbilityKind::attack_reset);
    int in = reset < 0 ? -1 : my_cooldown(reset);
    if (in == 0 && !my_can_cast()) in = 1; // the cast is spent this turn
    int turns = 0;
    for (int landed = 0; landed < hits; ++turns) landed += 1 + (in >= 0 && turns >= in && (turns - in) % ability_cooldown == 0);
    if (camp_hit_factor() * (fire * static_cast<float>(turns) - target_fire) >= my_health_and_shield(world)) return false;
    if (!attack_camp_target(world, {group, member, 0})) return false;
    reset_and_attack_camp(world, group);
    return true;
}

// Damage to camps per point: damage_scale() with Monster and Collectors in place of the
// champion-only Skirmish. Ours from the items held now.
float camp_scale(const ChampionBelief& c) {
    return damage_scale(c.facts().passive, c.health, c.max_health) * (c.is_self ? camp_dealt_factor() : c.camp_dealt);
}

// output() on camps, at least 1: a divisor for clear times.
float camp_output(const ChampionBelief& c) { return std::max(1.0f, c.facts().raw_output(c.strength, c.focus) * camp_scale(c)); }

struct OwnFactors {
    float camp_hit, camp_dealt, champion_dealt;
};
const OwnFactors& own_factors() {
    static unsigned read_at = ~0u;
    static OwnFactors f;
    if (read_at != items_bought) {
        read_at = items_bought;
        const auto& owned = my_items();
        const auto dealt = dealt_with(owned);
        f = {(has_family(owned, jungle) ? jungle_camp_taken : 1.0f) * (has_family(owned, durability) ? durability_taken : 1.0f),
             dealt.camp, dealt.champion};
    }
    return f;
}

} // namespace

float camp_hit_factor() { return own_factors().camp_hit; }
float camp_dealt_factor() { return own_factors().camp_dealt; }
float champion_dealt_factor() { return own_factors().champion_dealt; }

namespace {

float rate(const World& world, float worth, float rounds) {
    static float horizon = 0;
    if (horizon <= 0) horizon = cycle_horizon(world.map());
    rounds = std::max(rounds, 1.0f);
    return worth / (rounds * (1.0f + rounds / horizon));
}

// A living camp member, for min_camp_damage's clear order.
struct CampLeft {
    float health, strength;
    int member;
    float fire; // damage a round from the strikers still alive that reach where we stand to kill it (clear_fire)
    float home_fire; // the same at its spawn stand (StandReach::home_hits); -1 without one
};

// Damage taken clearing a group alone at `strength` a turn (callers pass camp_output, spells
// included), killing the deadliest first; also the rounds it takes. `reflect`: damage each hit on us
// returns to its monster (Ren). `left`: the living members, deadliest first; the reflect path wears it down.
// A member hit from its spawn stand, where a camp phase's fire is at most `survivable`, costs nothing:
// each turn end there heals it (rules rounds.turn_end).
float min_camp_damage(CampLeft* left, int n, float strength, float* rounds, float reflect, float survivable) {
    float damage = 0, elapsed = 0;
    const auto at_home = [&](const CampLeft& m) { return m.home_fire >= 0 && m.home_fire <= survivable; };
    if (reflect <= 0) {
        for (int i = 0; i < n; ++i) {
            const float k = std::ceil(left[i].health / strength);
            elapsed += k;
            if (!at_home(left[i])) damage += left[i].fire * k;
        }
        // Our first hit wakes the group: nothing hits us that round.
        if (n > 0 && !at_home(left[0])) damage -= left[0].fire;
        *rounds = elapsed;
        return damage;
    }
    // Only members that strike take the reflection.
    int attackers = n;
    while (attackers > 0 && left[attackers - 1].strength <= 0) --attackers;
    // Each round we hit the first living target, then every living attacker hits us and takes the
    // reflection. Stepped from one death to the next.
    for (int i = 0; i < n;) {
        const float own = left[i].strength > 0 ? reflect : 0.0f;
        float k = std::max(1.0f, std::ceil(left[i].health / (strength + own)));
        for (int j = i + 1; j < attackers; ++j)
            if (left[j].health > 0 && left[j].strength > 0) k = std::min(k, std::max(1.0f, std::ceil(left[j].health / reflect)));
        // Our hit in round k fells it before it strikes; otherwise it struck every round. From its spawn
        // stand the hits still reflect, but heal.
        const float hits = left[i].health - k * strength - (k - 1) * own <= 0 ? k - 1 : k;
        const float taken = at_home(left[i]) ? 0.0f : 1.0f;
        damage += left[i].strength * hits * taken;
        left[i].health -= k * strength + hits * own;
        for (int j = i + 1; j < attackers; ++j)
            if (left[j].health > 0 && left[j].strength > 0) damage += left[j].strength * k * taken, left[j].health -= k * reflect;
        elapsed += k;
        while (i < n && left[i].health <= 0) ++i;
    }
    *rounds = elapsed;
    return damage;
}

// Per group and range, built once: which strikers (bit k: the group's k-th, the first 32) reach the
// tile a clear stands on to hit each member: `range` from it on the side away from the group's
// middle (a line's end is hit from beyond it), inside the map. Walls are ignored. A member in range
// and sight of a spawn tile of ours is hit from there instead when its fire allows (`homes`: the
// spawn tile with the least fire with every striker alive).
struct StandReach {
    std::vector<std::uint32_t> hits; // per member
    // Each member with a spawn stand: few groups have any, and an empty vector allocates nothing.
    struct Home {
        int member;
        std::uint32_t bits;  // the strikers reaching its stand
        std::uint64_t tiles; // bit k: ally_spawn_tiles[k] has it in range and sight (the first 64)
    };
    std::vector<Home> homes;
    // The walk home from the nearest stand where fire is taken off our spawn (a member without a
    // spawn stand, hit within its strikers' reach): the static walk from our spawn, at least a step;
    // unreachable without one. Worked out by home_gap once the spawn field is made (-2 until then)
    // from `exposed`: the stands nearest our spawn's box, and their members' tiles.
    int gap = -2;
    std::array<std::pair<vec2, vec2>, 4> exposed{};
    std::array<int, 4> exposed_box{};
    int n_exposed = 0;
    // The strikers reaching member i's spawn stand, -1 without one.
    std::int64_t home_bits(int i) const {
        for (const auto& h : homes)
            if (h.member == i) return h.bits;
        return -1;
    }
    std::vector<std::int8_t> slot;   // per member: its striker bit, -1 if none
    std::vector<float> strength;     // per striker bit
    // The striker bits by strength, when there are at most 4 strengths, all whole and summing below
    // 2^24: every float sum of them is then exact, so a sum in any order is the bit-by-bit one.
    int kinds = -1; // -1: sums bit by bit
    std::array<float, 4> kind_strength{};
    std::array<std::uint32_t, 4> kind_bits{};
};

const StandReach& stand_reach(const StaticMap& map, int g, int range) {
    static std::array<std::vector<StandReach>, 2> tables; // melee, ranged
    auto& table = tables[range > 1];
    if (table.size() < map.groups.size()) table.resize(map.groups.size());
    auto& t = table[g];
    const auto& group = map.groups[g];
    const int n = static_cast<int>(group.members.size());
    if (static_cast<int>(t.slot.size()) == n) return t;
    t.hits.assign(n, 0), t.slot.assign(n, -1), t.strength.clear();
    t.homes.clear(), t.gap = -2, t.n_exposed = 0;
    vec2 lo = group.members[0].pos, hi = lo;
    for (const auto& m : group.members)
        lo = {std::min(lo.x, m.pos.x), std::min(lo.y, m.pos.y)}, hi = {std::max(hi.x, m.pos.x), std::max(hi.y, m.pos.y)};
    for (int i = 0; i < n && t.strength.size() < 32; ++i)
        if (group.members[i].strength > 0) t.slot[i] = static_cast<std::int8_t>(t.strength.size()), t.strength.push_back(group.members[i].strength);
    t.kinds = 0, t.kind_bits = {};
    float total = 0;
    for (int b = 0; b < static_cast<int>(t.strength.size()) && t.kinds >= 0; ++b) {
        const float s = t.strength[b];
        total += s;
        int k = 0;
        while (k < t.kinds && t.kind_strength[k] != s) ++k;
        if (k == static_cast<int>(t.kind_strength.size()) || s != std::floor(s) || !(total < 16777216.0f)) {
            t.kinds = -1;
            break;
        }
        if (k == t.kinds) t.kind_strength[t.kinds++] = s;
        t.kind_bits[k] |= 1u << b;
    }
    const auto away = [](int v, int sum) { return 2 * v > sum ? 1 : 2 * v < sum ? -1 : 0; };
    // The strikers' tiles and reaches by bit, padded with reach -1, which no tile is within: every
    // member against every striker is ~n^2 pairs (100k+ for a big group member by member), so sixteen
    // strikers a vector: coordinates below 100 and their differences fit a signed byte.
    const int strikers = static_cast<int>(t.strength.size());
    alignas(16) std::array<std::int8_t, 32> sx, sy, sr;
    for (int b = 0; b < 32; ++b) sx[b] = sy[b] = 0, sr[b] = -1;
    for (int j = 0; j < n; ++j)
        if (const int b = t.slot[j]; b >= 0)
            sx[b] = static_cast<std::int8_t>(group.members[j].pos.x), sy[b] = static_cast<std::int8_t>(group.members[j].pos.y),
            sr[b] = static_cast<std::int8_t>(group.members[j].reach);
    const int chunks = (strikers + 15) / 16;
    const auto reaching = [&](vec2 at) {
        std::uint32_t bits = 0;
#if defined(__wasm_simd128__)
        const v128_t ax = wasm_i8x16_splat(static_cast<std::int8_t>(at.x)), ay = wasm_i8x16_splat(static_cast<std::int8_t>(at.y));
        for (int c = 0; c < chunks; ++c) {
            const v128_t d = wasm_i8x16_max(wasm_i8x16_abs(wasm_i8x16_sub(wasm_v128_load(&sx[16 * c]), ax)),
                                            wasm_i8x16_abs(wasm_i8x16_sub(wasm_v128_load(&sy[16 * c]), ay)));
            bits |= static_cast<std::uint32_t>(wasm_i8x16_bitmask(wasm_i8x16_le(d, wasm_v128_load(&sr[16 * c])))) << (16 * c);
        }
#else
        for (int b = 0; b < 16 * chunks; ++b)
            if (std::max(std::abs(sx[b] - at.x), std::abs(sy[b] - at.y)) <= sr[b]) bits |= 1u << b;
#endif
        return bits;
    };
    const auto& spawn = map.ally_spawn_tiles;
    vec2 slo = spawn.empty() ? vec2{-1, -1} : spawn[0], shi = slo;
    for (const auto s : spawn) slo = {std::min(slo.x, s.x), std::min(slo.y, s.y)}, shi = {std::max(shi.x, s.x), std::max(shi.y, s.y)};
    for (int i = 0; i < n; ++i) {
        const vec2 p = group.members[i].pos;
        int dx = away(p.x, lo.x + hi.x), dy = away(p.y, lo.y + hi.y);
        if (dx == 0 && dy == 0) dy = 1;
        const vec2 at{std::clamp(p.x + dx * range, 0, map.width - 1), std::clamp(p.y + dy * range, 0, map.height - 1)};
        t.hits[i] = reaching(at);
        if (spawn.empty()) continue;
        if (std::max({slo.x - p.x, p.x - shi.x, slo.y - p.y, p.y - shi.y}) <= range) {
            // A basic attack needs sight of its camp (rules turn.attack), and sight is symmetric.
            const bitboard seen = map.sight_off_bushes(p, range);
            float least = -1;
            std::uint32_t best = 0;
            std::uint64_t tiles = 0;
            for (std::size_t k = 0; k < spawn.size(); ++k) {
                const vec2 s = spawn[k];
                if (dist(s, p) > range || !test(seen, s)) continue;
                if (k < 64) tiles |= std::uint64_t{1} << k;
                const std::uint32_t bits = reaching(s);
                float f = 0;
                for (std::uint32_t b = bits; b; b &= b - 1) f += t.strength[std::countr_zero(b)];
                if (least < 0 || f < least) least = f, best = bits;
            }
            if (least >= 0) {
                t.homes.push_back({i, best, tiles});
                continue;
            }
        }
        // Fire is taken off spawn only where a member without a spawn stand is hit from a tile its
        // strikers reach.
        if (t.hits[i] == 0) continue;
        const int box = std::max({0, slo.x - at.x, at.x - shi.x, slo.y - at.y, at.y - shi.y});
        // The 4 nearest, in order.
        if (t.n_exposed == 4 && box >= t.exposed_box[3]) continue;
        int k = t.n_exposed < 4 ? t.n_exposed++ : 3;
        for (; k > 0 && t.exposed_box[k - 1] > box; --k) t.exposed[k] = t.exposed[k - 1], t.exposed_box[k] = t.exposed_box[k - 1];
        t.exposed[k] = {at, p}, t.exposed_box[k] = box;
    }
    return t;
}

// StandReach::gap. Before the spawn field is made (the first turn: ~10k), the distance to our spawn's
// box as the crow flies, a bound.
// Bit k: ally_spawn_tiles[k] is a spawn stand of a live member of g (StandReach::homes); 0 for most groups.
std::uint64_t home_reach(const World& world, int g, int range) {
    std::uint64_t tiles = 0;
    const auto& c = world.camps[g];
    for (const auto& h : stand_reach(world.map(), g, range).homes)
        if (c.state == CampState::alive && c.health[static_cast<std::size_t>(h.member)] > 0) tiles |= h.tiles;
    return tiles;
}

int home_gap(const StaticMap& map, int g, int range) {
    const auto& t = stand_reach(map, g, range);
    if (t.gap != -2) return t.gap;
    if (t.n_exposed == 0) return const_cast<StandReach&>(t).gap = unreachable;
    if (!map.from_ally_spawn_ready()) return std::max(1, t.exposed_box[0]);
    // A wall on the stand reads from the member, `range` nearer.
    int gap = unreachable;
    const auto& from_spawn = map.from_ally_spawn();
    for (int k = 0; k < t.n_exposed; ++k) {
        const auto [at, p] = t.exposed[k];
        int walk = from_spawn.at(at);
        if (walk == unreachable && (walk = from_spawn.at(p)) != unreachable) walk -= range;
        if (walk != unreachable) gap = std::min(gap, std::max(1, walk));
    }
    return const_cast<StandReach&>(t).gap = gap;
}

// The summed Strength of group g's live members a clear hits from a spawn stand (StandReach) whose
// fire, from the strikers alive now, is at most `survivable`: the turn end there heals it.
float home_free(const World& world, int g, int range, float survivable) {
    const auto& map = world.map();
    const auto& t = stand_reach(map, g, range);
    const auto& G = map.groups[g];
    const auto& c = world.camps[g];
    const auto alive = [&](std::size_t i) { return c.state == CampState::respawning || (c.state == CampState::alive && c.health[i] > 0); };
    std::uint32_t living = 0;
    for (std::size_t i = 0; i < G.members.size(); ++i)
        if (t.slot[i] >= 0 && alive(i)) living |= 1u << t.slot[i];
    float free = 0;
    for (const auto& h : t.homes) {
        if (!alive(static_cast<std::size_t>(h.member))) continue;
        float fire = 0;
        for (std::uint32_t b = h.bits & living; b; b &= b - 1) fire += t.strength[std::countr_zero(b)];
        if (fire <= survivable) free += G.members[static_cast<std::size_t>(h.member)].strength;
    }
    return free;
}

// Each living member's `fire` in clear order: the strikers from it on that reach its stand tile.
// Sorts deadliest first, ties to the least fire with every member alive (a line's ends before its middle).
void clear_fire(const StaticMap& map, int g, CampLeft* left, int n, int range) {
    const auto& t = stand_reach(map, g, range);
    const auto fire = [&](std::uint32_t bits) {
        float f = 0;
        if (t.kinds >= 0) {
            for (int k = 0; k < t.kinds; ++k) f += t.kind_strength[k] * static_cast<float>(std::popcount(bits & t.kind_bits[k]));
            return f;
        }
        for (; bits; bits &= bits - 1) f += t.strength[std::countr_zero(bits)];
        return f;
    };
    std::uint32_t living = 0;
    for (int i = 0; i < n; ++i)
        if (t.slot[left[i].member] >= 0) living |= 1u << t.slot[left[i].member];
    for (int i = 0; i < n; ++i) left[i].fire = fire(t.hits[left[i].member] & living);
    if (n > 1)
        std::sort(left, left + n, [](const CampLeft& a, const CampLeft& b) {
            const float x = a.strength * b.health, y = b.strength * a.health;
            return x != y ? x > y : a.fire < b.fire;
        });
    for (int i = 0; i < n; ++i) {
        const int m = left[i].member;
        left[i].fire = fire(t.hits[m] & living);
        const auto bits = t.homes.empty() ? -1 : t.home_bits(m);
        left[i].home_fire = bits >= 0 ? fire(static_cast<std::uint32_t>(bits) & living) : -1.0f;
        if (t.slot[m] >= 0) living &= ~(1u << t.slot[m]);
    }
}

// Whether `sorted`, a build's clear order of `n` living members, is what a build now would give, its
// health then updated: the same members live and, for each member whose health moved, every comparison
// of clear_fire's sort with it has the same outcome (the fire tie-break reads only the living set).
// std::sort's permutation is a function of its comparisons' outcomes and its input order (member order),
// and the fire passes read only the order and the living set.
[[gnu::noinline]] bool order_holds(const CampGroup& group, const CampBelief& belief, bool fresh, CampLeft* sorted, int n) {
    int living = 0;
    for (std::size_t i = 0; i < group.members.size(); ++i)
        living += (fresh ? group.members[i].max_health : belief.health[i]) > 0;
    if (living != n) return false;
    constexpr int most = 8; // more moved members: a sort is about as cheap
    std::array<int, most> at;
    std::array<float, most> now;
    int moved = 0;
    for (int p = 0; p < n; ++p) {
        const int m = sorted[p].member;
        const float hp = fresh ? group.members[m].max_health : belief.health[m];
        if (hp == sorted[p].health) continue;
        if (!(hp > 0) || moved == most) return false;
        at[moved] = p, now[moved++] = hp;
    }
    const auto order = [](float sa, float ha, float sb, float hb) {
        const float x = sa * hb, y = sb * ha;
        return x > y ? 1 : x < y ? -1 : 0;
    };
    for (int k = 0; k < moved; ++k) {
        const float s = sorted[at[k]].strength, before = sorted[at[k]].health, after = now[k];
        for (int q = 0, j = 0; q < n; ++q) {
            float h = sorted[q].health, h_now = h;
            if (j < moved && at[j] == q) h_now = now[j++];
            if (q != at[k] && order(s, before, sorted[q].strength, h) != order(s, after, sorted[q].strength, h_now)) return false;
        }
    }
    for (int k = 0; k < moved; ++k) sorted[at[k]].health = now[k];
    return true;
}

// Kept per group, strength and range while the group's belief is unchanged; the sorted members, for
// the last group and range asked, while its belief is. `range`: the clearer's, ours if negative;
// `survivable`: the clearer's home_survivable, ours if negative.
float min_camp_damage(const World& world, int g, float strength, float* rounds, float reflect, int range, float survivable) {
    const auto& group = world.map().groups[g];
    const auto& belief = world.camps[g];
    if (range < 0) range = world.me().facts().attack_range();
    // Without spawn stands survivable changes nothing: one cache key for every clearer. Whether a group
    // has any is static, read once a group and range class (0: unread, 1: none, 2: some).
    static std::array<std::array<std::int8_t, 2>, 256> stands{};
    std::int8_t known = static_cast<std::size_t>(g) < stands.size() ? stands[g][range > 1] : 0;
    if (known == 0) {
        known = stand_reach(world.map(), g, range).homes.empty() ? 1 : 2;
        if (static_cast<std::size_t>(g) < stands.size()) stands[g][range > 1] = known;
    }
    if (known == 1) survivable = 0;
    else if (survivable < 0) survivable = home_survivable(world.me());
    struct Slots {
        std::uint32_t version = ~0u;
        int count = 0, next = 0;
        std::array<float, 4> strength{}, reflect{}, survivable{}, damage{}, rounds{};
        std::array<int, 4> range{};
    };
    // Static storage starts filled for free, where a vector pays to fill its slots.
    static std::array<Slots, 256> cache;
    static Slots uncached;
    const bool kept = static_cast<std::size_t>(g) < cache.size();
    auto& c = kept ? cache[g] : uncached;
    if (c.version != belief.version || !kept) {
        c.version = belief.version;
        c.count = c.next = 0;
    }
    for (int i = 0; i < c.count; ++i)
        if (c.strength[i] == strength && c.reflect[i] == reflect && c.range[i] == range && c.survivable[i] == survivable) {
            *rounds = c.rounds[i];
            return c.damage[i];
        }
    // Kept per group and range (melee or ranged) for its version, each in its own part of one static
    // pool (zeroed for free, where allocating and filling cost per group): a group asked again on a
    // later call or turn reuses its sort without a copy. Past the pool, one spare part is shared.
    struct Sorted {
        std::uint32_t version;
        int range, n, at; // range 0: never built; `at`: its part of the pool, from 1
    };
    static std::array<std::array<Sorted, 2>, 256> table;
    static std::array<CampLeft, 8192> pool;
    static int pool_used = 0;
    static std::vector<CampLeft> spare, worn;
    static Sorted spare_slot;
    static int spare_group = -1;
    const int size = static_cast<int>(group.members.size());
    Sorted* slot = &spare_slot;
    if (static_cast<std::size_t>(g) < table.size()) {
        auto& kept_slot = table[static_cast<std::size_t>(g)][range > 1];
        if (kept_slot.at == 0 && pool_used + size <= static_cast<int>(pool.size())) kept_slot.at = pool_used + 1, pool_used += size;
        if (kept_slot.at > 0) slot = &kept_slot;
    }
    if (slot == &spare_slot) {
        if (static_cast<int>(spare.size()) < size) spare.resize(group.members.size());
        if (spare_group != g) spare_group = g, spare_slot.range = 0;
    }
    CampLeft* const sorted = slot == &spare_slot ? spare.data() : pool.data() + (slot->at - 1);
    if (slot->range != range || slot->version != belief.version) {
        const bool fresh = belief.state == CampState::respawning;
        const bool same_order = slot->range == range && order_holds(group, belief, fresh, sorted, slot->n);
        slot->version = belief.version, slot->range = range;
        if (!same_order) {
            int living = 0;
            for (std::size_t i = 0; i < group.members.size(); ++i) {
                const float hp = fresh ? group.members[i].max_health : belief.health[i];
                if (hp > 0) sorted[living++] = {hp, group.members[i].strength, static_cast<int>(i), 0.0f, -1.0f};
            }
            slot->n = living;
            clear_fire(world.map(), g, sorted, living, range);
        }
    }
    const int n = slot->n;
    // The reflect path wears its members' health down: it gets a copy.
    CampLeft* left = sorted;
    if (reflect > 0) {
        if (static_cast<int>(worn.size()) < size) worn.resize(group.members.size());
        left = worn.data(), std::copy_n(sorted, n, left);
    }
    const int i = c.next;
    c.next = (c.next + 1) % static_cast<int>(c.strength.size());
    c.count = std::max(c.count, i + 1);
    c.strength[i] = strength;
    c.reflect[i] = reflect;
    c.range[i] = range;
    c.survivable[i] = survivable;
    c.damage[i] = min_camp_damage(left, n, strength, &c.rounds[i], reflect, survivable);
    *rounds = c.rounds[i];
    return c.damage[i];
}

// Clear damage taken (`damage`, after our emblems, over `rounds`) less what a self-shield of
// `shield` (self_shield_amount) absorbs: a cast `ready_in` rounds in, then one a cooldown, each
// holding at most its amount or the fire over its window, the last cut off by the clear's end.
// Constant time; it rises with the damage, so a lower bound on that bounds this too.
float shielded_clear(float damage, float rounds, float shield, float ready_in) {
    if (shield <= 0 || rounds <= 0 || ready_in >= rounds) return damage;
    constexpr float duration = static_cast<float>(facts(cambc::champion_type::varg).abilities[1].duration);
    static_assert(facts(cambc::champion_type::heart_of_ruin).abilities[0].duration == facts(cambc::champion_type::varg).abilities[1].duration);
    static_assert(duration <= ability_cooldown); // windows never overlap: all but the last are whole
    constexpr auto cooldown = static_cast<float>(ability_cooldown);
    const float rate = damage / rounds, casts = std::ceil((rounds - ready_in) / cooldown);
    const float last = std::min(duration, rounds - ready_in - (casts - 1) * cooldown);
    return damage - (casts - 1) * std::min(shield, rate * duration) - std::min(shield, rate * last);
}

// A group's side of the map: d_enemy / (d_ally + d_enemy) over the walks from the two spawns
// (home_ground's), 0.5 at the middle. Kept per group.
float home_side(const StaticMap& map, int g, bool first_turn) {
    static std::array<float, 256> cache = [] {
        std::array<float, 256> a;
        a.fill(-1);
        return a;
    }();
    float uncached = -1;
    auto& side = static_cast<std::size_t>(g) < cache.size() ? cache[g] : uncached;
    if (side < 0) {
        int from_us = map.ally_steps(g);
        int from_them = first_turn ? map.enemy_steps_of(g) : map.enemy_steps(g);
        if (from_us == unreachable) {
            from_us = dist(map.ally_spawn_centre, map.groups[g].centre);
            from_them = dist(map.enemy_spawn_centre, map.groups[g].centre);
        }
        side = from_them == unreachable ? 1.0f
               : from_us + from_them > 0 ? static_cast<float>(from_them) / static_cast<float>(from_us + from_them) : 0.5f;
    }
    return side;
}

// A group's weight by its side of the map: 1 in our half, falling towards the enemy spawn. Kept
// per group. The first turn reads one group's enemy steps; the turn end then decodes them all,
// since a play turn's farm weighs nearly every group.
float home_ground(const StaticMap& map, int g, bool first_turn) {
    struct Kept {
        float weight = -1; // until read
    };
    static std::array<Kept, 256> cache;
    float uncached = -1;
    auto& weight = static_cast<std::size_t>(g) < cache.size() ? cache[g].weight : uncached;
    if (weight < 0) {
        int from_us = map.ally_steps(g);
        int from_them = first_turn ? map.enemy_steps_of(g) : map.enemy_steps(g);
        // Beyond our walk (a crystal's region), both as the crow flies: else the enemy's doorstep counts in full.
        if (from_us == unreachable) {
            from_us = dist(map.ally_spawn_centre, map.groups[g].centre);
            from_them = dist(map.enemy_spawn_centre, map.groups[g].centre);
        }
        weight = 1.0f;
        if (from_us != unreachable && from_them != unreachable) {
            const float share = std::min(1.0f, 2.0f * static_cast<float>(from_them) / static_cast<float>(from_us + from_them));
            weight = std::pow(share, params::home_power);
        }
    }
    return weight;
}

// Damage spells a turn on camps, spread over their cooldown.
float spell_output(const ChampionBelief& c) {
    float damage = 0;
    for (const auto& a : c.facts().abilities)
        if (a.kind == AbilityKind::damage) damage += a.multiplier * c.focus / static_cast<float>(ability_cooldown);
    return damage * camp_scale(c);
}

// Basic attacks a turn on camps, with the reset spread over its cooldown.
float basic_output(const ChampionBelief& c) {
    return c.strength * camp_scale(c) * (c.facts().has_attack_reset() ? 1.0f + 1.0f / static_cast<float>(ability_cooldown) : 1.0f);
}

// Bit i: member i deals no damage and a basic attack of `range` reaches it from a tile out of the
// reach of every member that does. Static, so kept per group.
std::uint32_t safe_targets(const StaticMap& map, int g, int range) {
    struct Kept {
        std::array<std::int64_t, 2> bits{-1, -1}; // until read
    };
    static std::array<Kept, 256> cache;
    std::int64_t uncached = -1;
    auto& bits = static_cast<std::size_t>(g) < cache.size() ? cache[g].bits[range > 1] : uncached;
    if (bits < 0) {
        bits = 0;
        const auto& members = map.groups[g].members;
        bool harmless = false;
        for (const auto& m : members) harmless |= m.strength <= 0;
        if (harmless) {
            static bitboard open{cambc::uninitialized}, reach{cambc::uninitialized};
            reach.clear();
            for (const auto& m : members)
                if (m.strength > 0) reach.draw_chebyshev(m.pos, m.reach);
            or_into(map.standable, reach, open);
            open ^= reach; // standable & ~reach
            for (std::size_t i = 0; i < members.size() && i < 32; ++i)
                if (members[i].strength <= 0 && any_within(open, members[i].pos, range)) bits |= std::int64_t{1} << i;
        }
    }
    return static_cast<std::uint32_t>(bits);
}

// Rounds to clear a group alone without taking a hit: damage spells from ability_range on the
// members that attack, basic attacks on the others from out of the attackers' reach, or once they
// are dead. Negative without spells or a live attacker, or if one reaches as far as our spells.
// `spells` and `basic`: our spell_output and basic_output (at least 1), with `range` our attack range.
float spell_clear_rounds(const StaticMap& map, int g, const CampBelief& belief, int range, float spells, float basic) {
    if (spells <= 0) return -1;
    const auto& members = map.groups[g].members;
    const auto safe = safe_targets(map, g, range);
    const bool fresh = belief.state == CampState::respawning;
    float attackers = 0, reachable = 0, rest = 0;
    for (std::size_t i = 0; i < members.size(); ++i) {
        const float hp = fresh ? members[i].max_health : belief.health[i];
        if (hp <= 0) continue;
        if (members[i].strength > 0 && members[i].reach >= ability_range) return -1;
        if (members[i].strength > 0) attackers += hp;
        else if (i < 32 && (safe >> i & 1)) reachable += hp;
        else rest += hp;
    }
    if (attackers <= 0) return -1;
    return std::max(attackers / spells, reachable / basic) + rest / (basic + spells);
}

// Kept per group while its belief and our output hold.
float spell_clear_rounds(const World& world, int g, int range, float spells, float basic) {
    struct Kept {
        std::uint32_t version = ~0u;
        int range = 0;
        float spells = 0, basic = 0, rounds = 0;
    };
    static std::array<Kept, 256> kept;
    Kept uncached;
    auto& k = static_cast<std::size_t>(g) < kept.size() ? kept[g] : uncached;
    const auto& belief = world.camps[g];
    if (k.version != belief.version || k.range != range || k.spells != spells || k.basic != basic)
        k = {belief.version, range, spells, basic, spell_clear_rounds(world.map(), g, belief, range, spells, basic)};
    return k.rounds;
}

// No clear is quicker than the group's health over our whole output. Kept per group while its
// belief and our output hold.
float fastest_clear(const World& world, int g, float strength) {
    struct Kept {
        std::uint32_t version = ~0u;
        float strength = 0, rounds = 0;
    };
    static std::array<Kept, 256> kept;
    Kept uncached;
    auto& k = static_cast<std::size_t>(g) < kept.size() ? kept[g] : uncached;
    const auto& belief = world.camps[g];
    if (k.version == belief.version && k.strength == strength) return k.rounds;
    const auto& members = world.map().groups[g].members;
    float rounds = 0;
    if (belief.state != CampState::cleared)
        for (std::size_t i = 0; i < members.size(); ++i)
            rounds += (belief.state == CampState::respawning ? members[i].max_health : belief.health[i]) / strength;
    k = {belief.version, strength, rounds};
    return rounds;
}

// Ren's clear alone (min_camp_damage's reflect path) is quicker than fastest_clear: each round
// our hit and every living attacker's reflection, and the rest once the attackers are dead, so
// no quicker than this. Shaved for the steps' float rounding.
float reflected_clear(const World& world, int g, float strength, float reflect) {
    const auto& members = world.map().groups[g].members;
    const auto& belief = world.camps[g];
    if (belief.state == CampState::cleared) return 0;
    const bool fresh = belief.state == CampState::respawning;
    float attackers = 0, rest = 0;
    int count = 0;
    for (std::size_t i = 0; i < members.size(); ++i) {
        const float hp = fresh ? members[i].max_health : belief.health[i];
        if (hp <= 0) continue;
        if (members[i].strength > 0) attackers += hp, ++count;
        else rest += hp;
    }
    return 0.999f * (attackers / (strength + reflect * static_cast<float>(count)) + rest / strength);
}

// Our share of the gems still to farm before either team reaches the win or the game ends, at the
// team's tribute rate and at our own pace.
float gems_share(const World& world) {
    // Everything it reads changes only with an observation, but for our bag (a kill mid-turn).
    static std::uint32_t observations = ~0u, gems = 0;
    static int round = -1;
    static float kept = 0;
    const std::uint32_t bag = my_gems();
    if (observations == world.observations && round == world.round && gems == bag) return kept;
    observations = world.observations, round = world.round, gems = bag;
    int alive = 0;
    for (const auto& a : world.allies) alive += a.alive;
    const int rounds = bag_rounds_left(world);
    int left = std::min(gems_short(world), static_cast<int>(cambc::constants::winning_gems) - world.score.enemy);
    if (const float rate = world.ally_rate(); rate > 0) left = std::min(left, static_cast<int>(rate * static_cast<float>(rounds)));
    return kept = std::min(static_cast<float>(std::max(0, left)) / static_cast<float>(std::max(1, alive)),
                           static_cast<float>(rounds) / rounds_per_gem);
}

// A live group, awake or maybe, whose monsters not read asleep reach p.
bool awake_over(const World& world, int g, vec2 p) {
    const auto& c = world.camps[g];
    const auto& G = world.map().groups[g];
    if (c.state != CampState::alive || c.awake == Awake::asleep || !test(G.threat(), p)) return false;
    // G.threat() also covers dead and harmless members.
    for (std::size_t i = 0; i < G.members.size(); ++i)
        if (c.health[i] > 0 && G.members[i].strength > 0 && !c.member_asleep(i) && dist(p, G.members[i].pos) <= G.members[i].reach) return true;
    return false;
}

// Retreating from an awake camp takes its hits anyway, and the clear is lost. Every awake group in
// reach counts: a nearly cleared harmless one next to an elk that is hitting us is no reason to stay.
bool finishing_camp(const World& world) { return finishing_camp(world, my_position()); }
bool finishing_camp(const World& world, vec2 here) {
    if (winning_bag(world)) return false;
    bool any = false;
    float damage = 0, soften = 0, strength = 0, reflect = 0;
    world.each_stirring([&](int g) {
        if (!awake_over(world, g, here)) return;
        if (!any) soften = camp_hit_factor(), strength = camp_output(world.me()), reflect = world.me().retaliation();
        float rounds = 0;
        damage += soften * min_camp_damage(world, g, strength, &rounds, reflect);
        any = true;
    });
    return any && damage < params::finish_camp_health_fraction * my_health_and_shield(world);
}

} // namespace

} // namespace aph
