// Camps: attacks on them, what clearing one costs in rounds and damage taken, and what it is worth.
#include "../bot_parts.h"

namespace aph {

namespace {

// Keep the ordinary list's bound and order even when farm also collects harmless alternatives.
template <class Allowed> CampAttackTargets camp_attack_targets(const World& world, Allowed allowed, CampAttackTargets* resources) {
    CampAttackTargets targets;
    if (!my_can_attack()) return targets;
    const int range = world.me().facts().attack_range();
    const vec2 here = my_position();
    if (!camp_in_reach(world, here, range)) return targets;
    const bool splash = world.me().facts().passive == Passive::splash_attack;
    const auto& map = world.map();
    for (auto p : positions_within(live_camp_tiles(), here, range)) {
        const int g = map.group_at(p);
        if (g < 0 || (map.groups[g].has_monolith && g != siege_group())) continue;
        const bool ordinary = allowed(g);
        const bool resource = resources && !map.groups[g].has_monolith && map.groups[g].strength <= 0;
        if (!ordinary && !resource) continue;
        const auto& members = map.groups[g].members;
        const auto& health = world.camps[g].health;
        for (int i = 0; i < static_cast<int>(members.size()); ++i) {
            if (members[i].pos != p) continue;
            const float hp = health[i] > 0 ? health[i] : members[i].max_health;
            float score = members[i].strength / std::max(1.0f, hp);
            if (splash) {
                int near = 0;
                for (int j = 0; j < static_cast<int>(members.size()); ++j)
                    near += j != i && health[j] > 0 && dist(members[i].pos, members[j].pos) <= 1;
                score += static_cast<float>(near);
            }
            if (ordinary && targets.n < static_cast<int>(targets.found.size())) targets.found[targets.n++] = {g, i, score};
            if (resource && resources->n < static_cast<int>(resources->found.size())) resources->found[resources->n++] = {g, i, score};
        }
    }
    const auto rank = [](CampAttackTargets& list) {
        std::stable_sort(list.found.begin(), list.found.begin() + list.n,
                         [](const CampAttackTarget& a, const CampAttackTarget& b) { return a.score > b.score; });
    };
    rank(targets);
    if (resources) rank(*resources);
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

// A camp in range of a group `allowed` accepts; the group attacked, or -1. Removing the most
// damage per hit goes first; Varg's splash wants the most live members next to its target.
template <class Allowed> int attack_camp(const World& world, Allowed allowed) {
    return attack_camp_targets(world, camp_attack_targets(world, allowed));
}

// A static field counts camps as cleared, so its walk can end at a live camp holding the only way
// on. When every step down the field is onto one, hit the weakest in reach if we outlast the fire
// of its group's members that reach us for as long as our basic attacks take to kill it. Camps
// never regenerate: a retreat and return still make progress.
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
        const auto& members = map.groups[g].members;
        for (int i = 0; i < static_cast<int>(members.size()); ++i) {
            if (members[i].pos != p) continue;
            const float hp = world.camps[g].health[i] > 0 ? world.camps[g].health[i] : members[i].max_health;
            if (group < 0 || hp < weakest) group = g, member = i, weakest = hp;
        }
    }
    if (group < 0) return false;
    // Hitting any member wakes the group.
    float fire = 0;
    const auto& members = map.groups[group].members;
    for (int i = 0; i < static_cast<int>(members.size()); ++i)
        if (world.camps[group].health[i] > 0 && dist(here, members[i].pos) <= members[i].reach) fire += members[i].strength;
    const float turns = std::ceil(weakest / std::max(1.0f, my_strength() * damage_scale(world.me().facts().passive, my_health(), my_max_health()) * camp_dealt_factor()));
    if (camp_hit_factor() * fire * turns >= my_health_and_shield(world)) return false;
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
float camp_output(const ChampionBelief& c) { return std::max(1.0f, raw_output(c.facts(), c.strength, c.focus) * camp_scale(c)); }

bool has_family(const cambc::enum_map<cambc::item_type>& owned, int family) {
    return owned[emblem_of(family, strength_stat)] + owned[emblem_of(family, focus_stat)] + owned[emblem_of(family, health_stat)] > 0;
}

// Camp damage dealt per point owning `owned` and an emblem of `added` (-1: none): Monster's, and
// Collectors' per family owned.
float camp_dealt_with(const cambc::enum_map<cambc::item_type>& owned, int added) {
    float dealt = added == monster || has_family(owned, monster) ? monster_camp_dealt : 1.0f;
    if (added == collectors || has_family(owned, collectors)) {
        int families = added >= 0 && !has_family(owned, added);
        for (int f = monster; f <= collectors; ++f) families += has_family(owned, f);
        dealt *= 1.0f + collectors_dealt * static_cast<float>(families);
    }
    return dealt;
}

// Basic-attack damage to champions per point owning `owned`: Skirmish's, and Collectors' per family
// owned (world.cc's emblems() reads the same for others).
float champion_dealt_with(const cambc::enum_map<cambc::item_type>& owned) {
    float dealt = has_family(owned, skirmish) ? skirmish_dealt : 1.0f;
    if (has_family(owned, collectors)) {
        int families = 0;
        for (int f = monster; f <= collectors; ++f) families += has_family(owned, f);
        dealt *= 1.0f + collectors_dealt * static_cast<float>(families);
    }
    return dealt;
}

} // namespace

float camp_hit_factor() {
    const auto& owned = my_items();
    return (has_family(owned, jungle) ? jungle_camp_taken : 1.0f) * (has_family(owned, durability) ? durability_taken : 1.0f);
}

float camp_dealt_factor() { return camp_dealt_with(my_items()); }
float champion_dealt_factor() { return champion_dealt_with(my_items()); }

namespace {

float rate(const World& world, float worth, float rounds) {
    static float horizon = 0;
    if (horizon <= 0) {
        const auto& map = world.map();
        horizon = cycle_horizon * std::max(1.0f, static_cast<float>(std::max(map.width, map.height)) / 50.0f);
    }
    // A guard: farm floors its trip, so a cycle is at least the capture.
    rounds = std::max(rounds, 1.0f);
    return worth / (rounds * (1.0f + rounds / horizon));
}

// Damage taken clearing a group alone at `strength` a turn (callers pass camp_output, spells
// included), killing the deadliest first; also the rounds it takes. `reflect`: damage each hit on us
// returns to its monster (Ren). `left`: the living members, deadliest first; the reflect path wears it down.
float min_camp_damage(CampLeft* left, int n, float strength, float* rounds, float reflect) {
    float damage = 0, elapsed = 0;
    if (reflect <= 0) {
        for (int i = 0; i < n; ++i) {
            const float k = std::ceil(left[i].health / strength);
            elapsed += k;
            damage += left[i].fire * k;
        }
        // Our first hit wakes the group: nothing hits us that round.
        if (n > 0) damage -= left[0].fire;
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
        // Our hit in round k fells it before it strikes; otherwise it struck every round.
        const float hits = left[i].health - k * strength - (k - 1) * own <= 0 ? k - 1 : k;
        damage += left[i].strength * hits;
        left[i].health -= k * strength + hits * own;
        for (int j = i + 1; j < attackers; ++j)
            if (left[j].health > 0 && left[j].strength > 0) damage += left[j].strength * k, left[j].health -= k * reflect;
        elapsed += k;
        while (i < n && left[i].health <= 0) ++i;
    }
    *rounds = elapsed;
    return damage;
}

// Per group and range, built once: which strikers (bit k: the group's k-th, the first 32) reach the
// tile a clear stands on to hit each member: `range` from it on the side away from the group's
// middle (a line's end is hit from beyond it), inside the map. Walls are ignored.
struct StandReach {
    std::vector<std::uint32_t> hits; // per member
    std::vector<std::int8_t> slot;   // per member: its striker bit, -1 if none
    std::vector<float> strength;     // per striker bit
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
    vec2 lo = group.members[0].pos, hi = lo;
    for (const auto& m : group.members)
        lo = {std::min(lo.x, m.pos.x), std::min(lo.y, m.pos.y)}, hi = {std::max(hi.x, m.pos.x), std::max(hi.y, m.pos.y)};
    for (int i = 0; i < n && t.strength.size() < 32; ++i)
        if (group.members[i].strength > 0) t.slot[i] = static_cast<std::int8_t>(t.strength.size()), t.strength.push_back(group.members[i].strength);
    const auto away = [](int v, int sum) { return 2 * v > sum ? 1 : 2 * v < sum ? -1 : 0; };
    for (int i = 0; i < n; ++i) {
        const vec2 p = group.members[i].pos;
        int dx = away(p.x, lo.x + hi.x), dy = away(p.y, lo.y + hi.y);
        if (dx == 0 && dy == 0) dy = 1;
        const vec2 at{std::clamp(p.x + dx * range, 0, map.width - 1), std::clamp(p.y + dy * range, 0, map.height - 1)};
        for (int j = 0; j < n; ++j)
            if (t.slot[j] >= 0 && dist(at, group.members[j].pos) <= group.members[j].reach) t.hits[i] |= 1u << t.slot[j];
    }
    return t;
}

// Each living member's `fire` in clear order: the strikers from it on that reach its stand tile.
// Sorts deadliest first, ties to the least fire with every member alive (a line's ends before its middle).
void clear_fire(const StaticMap& map, int g, CampLeft* left, int n, int range) {
    const auto& t = stand_reach(map, g, range);
    const auto fire = [&](std::uint32_t bits) {
        float f = 0;
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
        left[i].fire = fire(t.hits[left[i].member] & living);
        if (t.slot[left[i].member] >= 0) living &= ~(1u << t.slot[left[i].member]);
    }
}

// Kept per group, strength and range while the group's belief is unchanged; the sorted members, for
// the last group and range asked, while its belief is. `range`: the clearer's, ours if negative.
float min_camp_damage(const World& world, int g, float strength, float* rounds, float reflect, int range) {
    const auto& group = world.map().groups[g];
    const auto& belief = world.camps[g];
    if (range < 0) range = world.me().facts().attack_range();
    struct Slots {
        std::uint32_t version = ~0u;
        int count = 0, next = 0;
        std::array<float, 4> strength{}, reflect{}, damage{}, rounds{};
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
        if (c.strength[i] == strength && c.reflect[i] == reflect && c.range[i] == range) {
            *rounds = c.rounds[i];
            return c.damage[i];
        }
    static std::vector<CampLeft> sorted, worn;
    static int sorted_group = -1, sorted_range = -1, n = 0;
    static std::uint32_t sorted_version = 0;
    if (sorted_group != g || sorted_version != belief.version || sorted_range != range) {
        sorted_group = g, sorted_version = belief.version, sorted_range = range;
        if (sorted.size() < group.members.size()) sorted.resize(group.members.size()), worn.resize(group.members.size());
        int living = 0;
        CampLeft* out = sorted.data();
        const bool fresh = belief.state == CampState::respawning;
        for (std::size_t i = 0; i < group.members.size(); ++i) {
            const float hp = fresh ? group.members[i].max_health : belief.health[i];
            if (hp > 0) out[living++] = {hp, group.members[i].strength, static_cast<int>(i), 0.0f};
        }
        n = living;
        clear_fire(world.map(), g, sorted.data(), n, range);
    }
    CampLeft* left = sorted.data();
    if (reflect > 0) left = std::copy_n(sorted.data(), n, worn.data()) - n;
    const int i = c.next;
    c.next = (c.next + 1) % static_cast<int>(c.strength.size());
    c.count = std::max(c.count, i + 1);
    c.strength[i] = strength;
    c.reflect[i] = reflect;
    c.range[i] = range;
    c.damage[i] = min_camp_damage(left, n, strength, &c.rounds[i], reflect);
    *rounds = c.rounds[i];
    return c.damage[i];
}

// Clear damage taken (`damage`, after our emblems, over `rounds`) less what a self-shield of
// `shield` (self_shield_amount) absorbs: one cast a cooldown, each holding at most its amount or
// its duration's share of the fire. Constant time; it never takes more than duration / cooldown
// of the damage, and it rises with the damage, so a lower bound on that bounds this too.
float shielded_clear(float damage, float rounds, float shield) {
    if (shield <= 0 || rounds <= 0) return damage;
    constexpr float duration = static_cast<float>(facts(cambc::champion_type::varg).abilities[1].duration);
    static_assert(facts(cambc::champion_type::heart_of_ruin).abilities[0].duration == facts(cambc::champion_type::varg).abilities[1].duration);
    return damage - rounds / static_cast<float>(ability_cooldown) * std::min(shield, duration * damage / rounds);
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

// Damage spells a turn on camps, spread over their cooldown: they reach 4, past the camps' 3.
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
        bool mixed = false;
        for (const auto& m : members) mixed |= m.strength <= 0;
        if (mixed) {
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

// Rounds to clear a group alone without taking a hit: damage spells from 4 on the members that
// attack, basic attacks on the others from out of the attackers' range, or once they are dead.
// Negative if no spell can reach an attacker, or one reaches as far as our spells. `spells` and `basic`: our spell_output and
// basic_output (at least 1), with `range` our attack range.
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
    int alive = 0;
    for (const auto& a : world.allies) alive += a.alive;
    const int rounds = bag_rounds_left(world);
    int left = std::min(gems_short(world), static_cast<int>(cambc::constants::winning_gems) - world.score.enemy);
    if (const float rate = world.ally_rate(); rate > 0) left = std::min(left, static_cast<int>(rate * static_cast<float>(rounds)));
    return std::min(static_cast<float>(std::max(0, left)) / static_cast<float>(std::max(1, alive)),
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
bool finishing_camp(const World& world) {
    if (winning_bag(world)) return false;
    const vec2 here = my_position();
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
