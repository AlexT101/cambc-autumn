#pragma once
#include <optional>
#include "util.h"

namespace aph {

class World;
class Pathing;

struct Memory {
};

// `world` is as of the turn's start; ask cambc for anything that changes after acting.
void play_turn(const World& world, Pathing& pathing, Memory& memory);

} // namespace aph
