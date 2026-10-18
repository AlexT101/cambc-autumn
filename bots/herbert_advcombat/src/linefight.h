// The user's line model (sim_core.h Battle::run_line) on Aph's beliefs (hyperion): each unit fights its focus on a
// line by the user's matchup rules, ours acting before theirs except a saved double turn. It decides engaging (prey)
// and disengaging (want_home); Aph's awareness supplies the sides (credible threats, unseen ones placed by tracking).
#pragma once
#include "util.h"

namespace aph {

class World;
class Safety;
struct ChampionBelief;

namespace line {

struct Outcome {
    bool any_enemy = false; // there was a fight to simulate
    bool we_win = false;    // every enemy dead within the horizon, or they lose the larger share of their hp
    bool i_die = false;     // our own unit dies within the horizon
    bool wiped = false;     // every unit of our side dies within the horizon
    int rounds = 0;
    double margin = 0;      // our hp share left minus theirs
};

// The fight if we stood at `at`: us and the 4 nearest visible allies within 5, against the 5 nearest credible threats
// (visible within 7; unseen ones at their possible tile nearest `at`, within their reach + 1). A fixed work budget
// (the user's fuel rule): the model is O(units^2) a round. `double_turn`: we hold a saved double turn.
Outcome evaluate(const World& world, Safety& safety, vec2 at, bool double_turn, int horizon = 8);

// The fight where we stand at `p` this turn, as Helios simmed it (the user's design): one sim per turn and tile, horizon
// 10, our saved double turn included ("part of every fight we sim"). Retreat, the ladder and kill checks all read it.
const Outcome& at(const World& world, Safety& safety, vec2 p);

// Its live shield (in sight; 0 out of it).
float shield_of(const ChampionBelief& b);

} // namespace line
} // namespace aph
