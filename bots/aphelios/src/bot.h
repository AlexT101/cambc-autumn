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
};

// `world` is as of the turn's start; ask cambc for anything that changes after acting.
void play_turn(const World& world, Pathing& pathing, Memory& memory);

} // namespace aph
