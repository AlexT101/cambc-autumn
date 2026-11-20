// Contested groups: who gives way. A stand the team wins is left only when our fall there costs more
// than holding wins; a group the team is invested in and wins the stand at stays the farm's target. Every value is in enemy health points (params::life_value,
// params::gem_value), as the fight and kill pricing elsewhere.
#include "../bot_parts.h"

namespace aph {

namespace {

float fall_cost(const World& world) {
    const auto& me = world.me();
    float gems = static_cast<float>(my_gems());
    // A keeping Prism's bag compounds through its Focus (prism_premium): the killer takes that too.
    if (me.facts().passive == Passive::gem_focus && gems > 0) gems *= 1.0f + prism_premium(world, me, 1);
    float cost = my_max_health() + params::life_value + params::gem_value * gems;
    // Cassi and Issac fall together (rules: cassi_and_issac).
    if (const auto* p = partner(world); p && p->alive) {
        const int other = p->visible ? p->gems : std::max(p->gems, comms::bag_of(world, p->index));
        cost += p->max_health + params::life_value + params::gem_value * static_cast<float>(std::max(0, other));
    }
    return cost;
}

int contested_group(const World& world, vec2 p, int claim) {
    const auto& map = world.map();
    int g = in_bounds(p) ? map.group_at(p) : -1;
    if (g < 0 && claim >= 0 && claim < static_cast<int>(map.groups.size()) && steps_to(map.groups[claim], p) <= safety_params::fight_ally_radius) g = claim;
    if (g < 0) return -1;
    const auto& c = world.camps[g];
    if (c.state == CampState::cleared) return g;
    if (c.state != CampState::alive) return -1;
    // A live group is at stake once work on it is under way: awake, or a member below full health.
    if (c.awake != Awake::asleep) return g;
    const auto& G = map.groups[g];
    for (std::size_t i = 0; i < G.members.size(); ++i)
        if (c.health[i] < G.members[i].max_health) return g;
    return -1;
}

float group_stake(const World& world, int g) {
    // Gems only: gold scores nothing, and the farm's price of it (Prices::per_gold) is our emblem's, not the race's.
    const auto& G = world.map().groups[g];
    const int winning = static_cast<int>(cambc::constants::winning_gems);
    const int ours = std::min(G.gems, std::max(0, winning - world.score.ally));
    const int theirs = std::min(G.gems, std::max(0, winning - world.score.enemy));
    float premium = 0;
    if (world.me().facts().passive == Passive::gem_focus && ours > 0) premium = prism_premium(world, world.me(), ours);
    // In a race a group they take is a loss to us as well as one we take is a gain.
    return params::gem_value * (static_cast<float>(ours) * (1.0f + premium) + static_cast<float>(theirs));
}

// The kills the fight promises are no gain: an enemy losing the stand leaves it (it reads the stand as we
// do), often after taking the body it focused, so only the group the stand decides is won by holding.
bool fall_outweighs(const World& world, vec2 p) {
    const int g = contested_group(world, p, contest_claim);
    if (g < 0) return true;
    const float cost = fall_cost(world), stake = group_stake(world, g);
    debug_block({
        if (cost <= stake)
            std::printf("PRICED-STAY %d %u g%d at %d,%d cost %.0f stake %.0f gems %u\n", world.round, my_handle(), g, p.x, p.y, cost, stake, my_gems());
    });
    return cost > stake;
}

bool priced_fall(const World& world) {
    return partner(world) != nullptr || world.me().facts().passive == Passive::gem_focus
           || params::gem_value * static_cast<float>(bag_at_stake(world)) >= params::life_value;
}

// The camp tile of G nearest p.
vec2 nearest_tile(const CampGroup& G, vec2 p) {
    vec2 best = G.centre;
    int d = 1 << 30;
    for (const auto& m : G.members)
        if (const int k = dist(p, m.pos); k < d) d = k, best = m.pos;
    return best;
}

bool enemy_near_group(const World& world, int g) {
    const auto& G = world.map().groups[g];
    for (const auto& e : world.enemies)
        if (e.alive && e.visible && dist(e.pos, G.centre) <= params::crew_enemy_radius) return true;
    return false;
}

int group_contest(const World& world, Safety& safety, int g) {
    if (g < 0 || static_cast<std::size_t>(g) >= world.map().groups.size()) return 0;
    struct Kept {
        int round = -1;
        std::uint32_t observations = ~0u, generation = ~0u;
        std::array<std::int8_t, 256> read;
    };
    static Kept kept;
    if (kept.round != world.round || kept.observations != world.observations || kept.generation != Safety::generation()) {
        kept.round = world.round, kept.observations = world.observations, kept.generation = Safety::generation();
        kept.read.fill(-1);
    }
    std::int8_t* slot = static_cast<std::size_t>(g) < kept.read.size() ? &kept.read[static_cast<std::size_t>(g)] : nullptr;
    if (slot && *slot >= 0) return *slot;
    const auto answer = [&](int r) {
        if (slot) *slot = static_cast<std::int8_t>(r);
        return r;
    };
    if (!enemy_near_group(world, g)) return answer(0);
    const auto& G = world.map().groups[g];
    const vec2 p = nearest_tile(G, my_position());
    // Whoever is near the group when we get there: the enemies in sight within crew_enemy_radius of it
    // (may_expect's test) against us, the allies the stand at p counts and those in sight as near it.
    std::uint32_t key = safety.fight_allies(p);
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive && a.visible && a.index < 16 && dist(a.pos, p) <= params::crew_enemy_radius) key |= 1u << a.index;
    for (const auto& e : world.enemies)
        if (e.alive && e.visible && e.index < 16 && dist(e.pos, G.centre) <= params::crew_enemy_radius) key |= 1u << (16 + e.index);
    // Short of fuel the stand is unread: as lost, which keeps no choice.
    if (!fuel_ok(safety.fight_cost_estimate() + end_reserve)) return answer(2);
    const bool priced = priced_fall(world);
    const auto t = safety.fight_of(key, true);
    const bool lost = t.lost || (priced && t.self_falls && fall_outweighs(world, p));
    return answer(lost ? 2 : 1);
}

bool team_invested(const World& world, int g, int claim) {
    const auto& G = world.map().groups[g];
    const auto& c = world.camps[g];
    const vec2 here = my_position();
    const auto at = [&](const ChampionBelief& a, vec2 pos) {
        const int range = a.facts().attack_range();
        return c.state == CampState::cleared ? steps_to(G, pos) <= range : crew_in_reach(world, g, pos, range);
    };
    if (at(world.me(), here)) return true;
    bool ally_claims_near = false;
    for (const auto& a : world.allies) {
        if (a.is_self || !a.alive || !a.visible) continue;
        if (comms::claim_of(world, a.index) == g && at(a, a.pos)) return true;
        ally_claims_near |= comms::claim_of(world, a.index) == g && dist(a.pos, here) <= safety_params::fight_ally_radius;
    }
    return claim == g && ally_claims_near;
}

} // namespace

} // namespace aph
