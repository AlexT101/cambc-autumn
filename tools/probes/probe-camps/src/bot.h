#pragma once
#include <cambc.h>
#include <cstddef>
#include <vector>

// One scripted step: walk to `tile`; once there, attack the camp spawned at `target`
// (attack: 0 never, 1 once on arrival, 2 every turn); stay `wait` rounds after arrival (-1 = forever).
struct Step {
    cambc::vec2 tile;
    int attack = 0;
    cambc::vec2 target{ -1, -1 };
    int wait = -1;
    int min_round = 0;   // do not attack or finish this step before this round
    bool cast = false;   // use a ready camp-targeting ability instead of a basic attack
};

// Defined in scenario.h; returns this champion's script.
std::vector<Step> script(int side, int idx);

class Bot {
    int side = -1, idx = -1, arrived = -1;
    bool attacked_this_step = false;
    std::size_t cur = 0;
    std::vector<Step> steps;
public:
    void play_turn();
};
