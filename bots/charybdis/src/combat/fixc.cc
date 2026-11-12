// fix-combat (research/ladder-scrims-2026-11-06/fix-combat.md): hidden bush steps, and a lost retreat fought instead.
#include "../bot_parts.h"

namespace aph {

namespace {

// 0: a bush tile no visible enemy and no enemy ward in sight sees (a bush tile is seen only from its own cluster),
// 1: another bush tile, 2: off bushes. A ward's sight is the engine's mask; an unseen ward is not guessed at.
int fixc_bush_rank(const World& world, vec2 p) {
    const auto& map = world.map();
    if (!test(map.bushes, p)) return 2;
    const BushCluster* c = nullptr;
    const auto sees = [&](vec2 q) {
        if (!in_bounds(q) || !test(map.bushes, q) || dist(p, q) > vision_radius) return false;
        if (!c) c = &map.bush_cluster(p);
        return test(c->tiles, q);
    };
    for (const auto& e : world.enemies)
        if (e.alive && e.visible && sees(e.pos)) return 1;
    for (int i = 0; i < Wards::slots && i < static_cast<int>(world.enemies.size()); ++i)
        if (ward_of(world, i) >= 0 && ward_sees(terrain(map), i, p)) return 1;
    return 0;
}

// Pathing's first-step order: the bush rank breaks ties of pull and aim, or comes first when threatened.
int fixc_bush_order(const World& world, vec2 p, int score) {
    const int rank = fixc_bush_rank(world, p);
    return fixc_bush_threatened ? (rank << 26) + score : score * 4 + rank;
}

// A visible enemy off its spawn with a ready ability's strike, within its reach + bush_threat of us.
bool fixc_bush_threat(const World& world, Safety& safety) {
    const vec2 here = my_position();
    for (const auto& e : world.enemies) {
        if (!e.alive || !e.visible || test(world.map().near_enemy_spawn, e.pos)) continue;
        const auto& s = safety.strike_of(e);
        if (s.reach < 0 || dist(here, e.pos) > s.reach + params::fixc::bush_threat) continue;
        if (s.at(0) > strike_with(e, 0u).at(0)) {
            debug_block({ std::printf("FIXC-BUSHT %d %u e%d d%d\n", world.round, my_handle(), e.index, dist(here, e.pos)); });
            return true;
        }
    }
    return false;
}

// A retreat the pursuers win, so we fight instead: home is s steps off, and the visible enemies within a step of
// their basic reach (each walks as fast as we do) hit for our health and shield in the s - 1 turns before the last
// step heals us, while we kill one of them (kill_turn) with a turn to spare before those hits kill us standing.
// Only hit lately, with one enemy in sight within 8.
bool fixc_commit(const World& world, Pathing& pathing) {
    if (!my_can_attack() || stunned_turn) return false;
    const vec2 here = my_position();
    const int steps = pathing.to_ally_spawn().at(here);
    if (steps == unreachable || steps <= 1) return false;
    const float health = my_health_and_shield(world), taken = world.me().taken;
    if (world.me().hurt_round < world.round - 1) return false;
    float pursuit = 0;
    int first_kill = unreachable, near = 0;
    for (const auto& e : world.enemies) {
        if (!e.alive || !e.visible) continue;
        if (dist(here, e.pos) <= 8 && ++near > 1) return false;
        const auto basic = strike_with(e, 0u);
        if (basic.reach < 0 || dist(here, e.pos) > basic.reach + 1) continue;
        pursuit += basic.at(0) * taken;
        first_kill = std::min(first_kill, kill_turn(world, e, here));
    }
    if (pursuit <= 0 || pursuit * static_cast<float>(steps - 1) < health) return false;
    const int falls = static_cast<int>(std::ceil(health / pursuit)) - 1; // turns we stand before the hits kill us
    if (first_kill > falls - 1) return false;
    debug_block({ std::printf("FIXC-COMMIT %d %u steps %d kill %d falls %d\n", world.round, my_handle(), steps, first_kill, falls); });
    return true;
}

} // namespace

} // namespace aph
