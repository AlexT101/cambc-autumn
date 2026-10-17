#pragma once
#include <optional>
#include "util.h"

namespace aph {

class World;
class Pathing;

struct Memory {
    int round = -1;    // of our previous turn
    float health = 0;  // at its end
    float damage = 0;  // taken since, as of this turn's start
    bool banking = false; // our bag headed for an altar rather than another capture last turn
    int farm_group = -1;  // farm's latest choice, kept to walk on when fuel is short
    int claim = -1;       // the group we told allies we work towards, or -1
    bool crew = false;    // joining an ally's claim rather than our own
    bool siege = false;   // our claim is a Monolith the team attacks together
    int staged_since = -1; // round we started waiting near the Monolith for the others
    vec2 ward{-1, -1};    // our latest ward
    vec2 bushes_watched{-1, -1}; // a tile whose bushes in ward reach are all in our cluster or our ward's
};

// `world` is as of the turn's start; ask cambc for anything that changes after acting.
void play_turn(const World& world, Pathing& pathing, Memory& memory);

} // namespace aph
