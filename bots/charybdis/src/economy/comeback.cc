// Cooked comebacks (research/ideas-2026-11-05/comeback.md): while far behind, normal play rarely wins,
// so a gambit that lifts the comeback rate pays even if it loses more of the games already lost.
// The cook comes from the scores (every body reads the same); while it lasts, farm's mirror pull and
// denial (economy/farm.cc mirror_pull) and accept_lost's snipe are on.
#include "../bot_parts.h"

namespace aph {

namespace {

namespace comeback {

namespace {

namespace P = params::comeback;

struct Cook {
    int round = -1;
    bool on = false;
};
Cook cook;

// Read every turn by decide(), so the hysteresis sees each round's scores.
void refresh(const World& world) {
    if (cook.round == world.round) return;
    cook.round = world.round;
    const int us = world.score.ally, them = world.score.enemy, lead = them - us;
    cook.on = cook.on ? lead >= P::gap_off : them >= P::enemy_min && lead >= P::gap;
}

} // namespace

bool cooked(const World& world) {
    refresh(world);
    return cook.on;
}

// The play-out stops at our first fall, so a lost fight's own kill turn is mostly unknown: the bar is how
// long we last (their turns to kill one of us, played out with them striking first). Only for a bag worth
// the risk: a carrier's kill takes it. World's belief of a bag is the one last read in sight.
bool accept_lost(const World& world, const Trade& t, const ChampionBelief& target) {
    if (!cooked(world)) return false;
    if (static_cast<float>(t.turns_to_kill_us) < P::bar) return false;
    if (pair_gems(world, target) < P::bar_bag) return false;
    int alive = 0, near = 0;
    const vec2 here = my_position();
    for (const auto& a : world.allies) {
        if (a.is_self || !a.alive) continue;
        ++alive;
        near += a.visible && dist(a.pos, here) <= P::pack_radius;
    }
    return near >= std::min(alive, 2);
}

} // namespace comeback

} // namespace

} // namespace aph
