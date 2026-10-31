// Crews on strong camp groups: who takes the camps' hits, the trips home that health costs, and
// the crew farm expects when it proposes an operation.
#include "../bot_parts.h"

namespace aph {

namespace {

// Camp damage taken per point a camp deals, as far as we can read it (Jungle, Durability).
float crew_taken(const ChampionBelief& a) { return a.is_self ? camp_hit_factor() : a.camp_taken; }

// Camp damage a champion can take before `line`, and per trip home, over crew_trip_risk.
float crew_budget(const ChampionBelief& a, float line) {
    const float health = a.is_self ? my_health() : a.health, max_health = a.is_self ? my_max_health() : a.max_health;
    return std::max(0.0f, health - line * max_health) / params::crew_trip_risk;
}
float crew_usable(const ChampionBelief& a, float line) {
    return (a.is_self ? my_max_health() : a.max_health) * (1.0f - line) / params::crew_trip_risk;
}

int extra_trips(float damage, float budget, float usable) {
    if (damage <= budget) return 0;
    if (usable <= 0) return 99;
    return static_cast<int>(std::min(99.0f, std::ceil((damage - budget) / usable)));
}

// Rounds until a champion's basic attack reaches the group's nearest member, as the crow flies.
int crew_arrival(const World& world, const ChampionBelief& a, int g) {
    return std::max(0, steps_to(world.map().groups[g], a.is_self ? my_position() : a.pos) - a.facts().attack_range());
}

bool crew_in_reach(const World& world, int g, vec2 p, int range) {
    const auto& G = world.map().groups[g];
    const auto& c = world.camps[g];
    for (std::size_t i = 0; i < G.members.size(); ++i)
        if ((c.state == CampState::respawning || c.health[i] > 0) && dist(p, G.members[i].pos) <= std::max(range, G.members[i].reach))
            return true;
    return false;
}

bool crew_member(const World& world, const ChampionBelief& a, int g, std::span<const int> extra) {
    if (a.is_self) return true;
    if (!a.alive) return false;
    // Extras are counted in by the caller's rules (the first turn's unseen allies included).
    if (std::find(extra.begin(), extra.end(), a.index) != extra.end()) return true;
    return a.visible && comms::claim_of(world, a.index) == g;
}

// The tank's score: health above the line per camp damage taken, melee preferred (it stands
// nearest, so the camps' nearest-champion hits find it anyway). A fixed line, so that every
// member names the same tank whatever enemies it sees.
float tank_score(const ChampionBelief& a) {
    const float health = a.is_self ? my_health() : a.health, max_health = a.is_self ? my_max_health() : a.max_health;
    const float score = (health - params::crew_tank_line * max_health) / std::max(0.01f, crew_taken(a));
    return a.facts().walk_and_attack_independent() ? score * 1.5f : score;
}

const ChampionBelief* crew_tank(const World& world, int group, std::span<const int> extra) {
    const ChampionBelief* best = nullptr;
    float best_score = 0;
    // Allies are in index order: ties stay with the lower index.
    for (const auto& a : world.allies) {
        if (!crew_member(world, a, group, extra)) continue;
        if (const float s = tank_score(a); !best || s > best_score) best = &a, best_score = s;
    }
    return best;
}

// Farm's gold farmers (farm_turn's gold_farmer): they take the gold-only groups whatever a crew offers.
bool farms_gold(const World& world, const ChampionBelief& a) {
    const auto& f = a.facts();
    return (f.passive == Passive::linked_pair && !f.walk_and_attack_independent())
           || (economy_three(world) && f.passive == Passive::remote_shop && map_economy(world.map()).tavi_map());
}

// An ally free to join an operation on g: in sight within crew_available_radius of its centre and
// claiming nothing, a harmless group nearby, or holding a cleared group nearby. On the first turn
// everyone starts on spawn: any living ally with no claim yet. Also one in sight within
// crew_available_radius of us claiming nothing or a harmless group: it arrives about when we do
// (on spawn after a heal, most often). Never a gold farmer.
bool crew_available(const World& world, const ChampionBelief& a, int g) {
    if (a.is_self || !a.alive || farms_gold(world, a)) return false;
    const auto& map = world.map();
    const vec2 centre = map.groups[g].centre;
    const int claim = comms::claim_of(world, a.index);
    if (claim == g) return false;
    if (world.round == world.first_round && claim < 0) return true;
    if (!a.visible) return false;
    const int n = static_cast<int>(map.groups.size());
    const bool harmless = claim < 0 || (claim < n && map.groups[claim].strength <= 0);
    if (harmless && dist(a.pos, my_position()) <= params::crew_available_radius) return true;
    if (dist(a.pos, centre) > params::crew_available_radius) return false;
    if (claim < 0) return true;
    if (claim < n && map.groups[claim].strength <= 0 && dist(map.groups[claim].centre, centre) <= params::crew_near_radius) return true;
    const int on = map.group_at(a.pos);
    return on >= 0 && world.camps[on].state == CampState::cleared && dist(map.groups[on].centre, centre) <= params::crew_near_radius;
}

// The camps hit whoever tanks at the time, and the tank is the member with the best tank_score, so
// over a clear the hits level the members' scores (water filling): each member absorbs its score
// above the final level, over its melee weight (pre-emblem damage). The pool is us and the members
// in reach no later than 2 rounds after us; a later one cannot take the first hits.
void share_damage(const World& world, int g, float line, CrewPlan& p) {
    struct Member {
        const ChampionBelief* a;
        float score, weight;
    };
    std::array<Member, 16> pool;
    int n = 0;
    const int mine = crew_arrival(world, world.me(), g);
    const auto add = [&](const ChampionBelief& a) {
        if (n == static_cast<int>(pool.size())) return;
        if (!a.is_self && (a.visible || in_bounds(a.pos)) && crew_arrival(world, a, g) > mine + 2) return;
        const float health = a.is_self ? my_health() : a.health, max_health = a.is_self ? my_max_health() : a.max_health;
        const float weight = a.facts().walk_and_attack_independent() ? 1.5f : 1.0f;
        pool[n++] = {&a, (health - line * max_health) / std::max(0.01f, crew_taken(a)) * weight, weight};
    };
    for (const auto& a : world.allies) {
        if (!a.is_self && !a.alive) continue;
        const bool expected = std::find(p.expected.begin(), p.expected.begin() + p.n_expected, a.index) != p.expected.begin() + p.n_expected;
        // Claimers out of sight add output only: their health and arrival are unknown.
        if (a.is_self || expected || (a.visible && comms::claim_of(world, a.index) == g)) add(a);
    }
    std::sort(pool.begin(), pool.begin() + n, [](const Member& x, const Member& y) { return x.score > y.score; });
    // The level L where the top j absorb the damage: sum over them of (s - L) / w = damage.
    float a_sum = 0, b_sum = 0, level = 0;
    for (int j = 0; j < n; ++j) {
        a_sum += pool[j].score / pool[j].weight, b_sum += 1.0f / pool[j].weight;
        level = (a_sum - p.damage) / b_sum;
        if (j + 1 == n || level >= pool[j + 1].score) break;
    }
    p.trips = 0, p.my_damage = 0;
    for (int j = 0; j < n; ++j) {
        const auto& m = pool[j];
        const float absorbed = std::max(0.0f, (m.score - level) / m.weight);
        if (m.a->is_self) p.my_damage = absorbed;
        p.trips += extra_trips(absorbed * crew_taken(*m.a), crew_budget(*m.a, line), crew_usable(*m.a, line));
    }
}

CrewPlan plan_crew(const World& world, int g, float my_output, float line, bool expect, int cap) {
    CrewPlan plan;
    plan.output = my_output;
    // A claimer long out of sight may be healing or banking anywhere: it is not counted on.
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive && comms::claim_of(world, a.index) == g && (a.visible || a.pos_round >= world.round - params::crew_seen_rounds))
            plan.output += camp_output(a), ++plan.claimers;
    const auto price = [&](CrewPlan& p) {
        p.damage = min_camp_damage(world, g, p.output, &p.rounds);
        // Only the traces read the tank.
        debug_block({ p.tank = crew_tank(world, g, {p.expected.data(), static_cast<std::size_t>(p.n_expected)}); });
        share_damage(world, g, line, p);
    };
    price(plan);
    if (!expect || plan.trips == 0) return plan;
    // Nearest first, while each one more still saves the crew a trip.
    std::array<std::pair<int, int>, 16> free{};
    int n_free = 0;
    const vec2 centre = world.map().groups[g].centre;
    for (const auto& a : world.allies)
        if (n_free < static_cast<int>(free.size()) && crew_available(world, a, g)) free[n_free++] = {dist(a.pos, centre), a.index};
    std::sort(free.begin(), free.begin() + n_free);
    for (int i = 0; i < n_free && 1 + plan.claimers + plan.n_expected < cap && plan.trips > 0; ++i) {
        CrewPlan more = plan;
        more.expected[more.n_expected++] = free[i].second;
        more.output += camp_output(world.allies[free[i].second]);
        price(more);
        if (more.trips >= plan.trips) break;
        plan = more;
    }
    return plan;
}

bool farm_monolith(const World& world, int g) {
    const auto& map = world.map();
    return g >= 0 && g < static_cast<int>(map.groups.size()) && map.groups[g].has_monolith && !map.monolith_only;
}

// We are hit while no nearer than the nearest covering member: stepping out a tile a turn, that is
// its distance less ours, and one more hit to spare.
int mono_trapped(const World& world, Safety& safety, const Memory& memory, float health) {
    const int g = memory.claim;
    if (memory.siege || !farm_monolith(world, g) || world.camps[g].state != CampState::alive) return -1;
    const auto& G = world.map().groups[g];
    const auto& c = world.camps[g];
    const vec2 here = my_position();
    if (!test(G.threat(), here)) return -1;
    const auto striker_dist = [&](vec2 p) {
        int d = unreachable;
        for (std::size_t i = 0; i < G.members.size(); ++i)
            if (G.members[i].strength > 0 && c.health[i] > 0) d = std::min(d, dist(p, G.members[i].pos));
        return d;
    };
    int cover = unreachable;
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive && a.visible && a.channel != Channel::teleport && !real_recall(a) && test(G.threat(), a.pos))
            cover = std::min(cover, striker_dist(a.pos));
    const int mine = striker_dist(here);
    if (cover == unreachable || mine == unreachable) return -1;
    const float dps = safety.camp_damage(here);
    return health + my_live_shield(world) <= dps * static_cast<float>(std::max(0, cover - mine) + 1);
}

} // namespace

} // namespace aph
