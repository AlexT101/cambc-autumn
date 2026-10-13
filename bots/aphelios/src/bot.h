// Decision entry point. All combat, macro, shopping and ward logic lives behind play_turn.
#pragma once
#include <optional>
#include "util.h"

namespace aph {

class World;
class Pathing;

// Per-instance intent that persists across this champion's turns.
struct Memory {
    int shard_stat = -1; // placeholder build: which power shard to keep buying
};

// The world is the start-of-turn belief; query cambc directly for anything that changes after
// acting (position, allowances, fresh vision).
void play_turn(const World& world, Pathing& pathing, Memory& memory);

} // namespace aph
