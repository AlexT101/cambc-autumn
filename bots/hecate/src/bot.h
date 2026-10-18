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
    bool farm_spell = false; // selected spell-clear mode, revalidated before ranged passing hits
    vec2 farm_station{-1, -1}; // the latest locally executable spell station
    int worked_group = -1, worked_round = -1; // actual recent farm work, for an empty local reward
    int claim = -1;       // the group we told allies we work towards, or -1
    bool crew = false;    // joining an ally's claim rather than our own
    bool siege = false;   // our claim is a Monolith the team attacks together
    int staged_since = -1; // round we started waiting near the Monolith for the others
    int escort_waited = 0; // rounds our bag has waited for escorts
    vec2 ward{-1, -1};    // our latest ward
    vec2 bushes_watched{-1, -1}; // a tile whose bushes in ward reach are all in our cluster or our ward's
};

// `world` is as of the turn's start; ask cambc for anything that changes after acting.
void play_turn(const World& world, Pathing& pathing, Memory& memory);
// With the turn's spare fuel: the walk to our farm choice from where we ended, so that a costly
// turn next round still walks it well.
void prepare_next_turn(const World& world, Pathing& pathing, const Memory& memory);

} // namespace aph
