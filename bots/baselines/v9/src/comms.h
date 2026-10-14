// The team's 8 shared bytes. A write is visible at once to teammates who act later; earlier ones
// see it next round. Records carry no full round: each instance processes a record only when its
// bits change, which every teammate sees within a round of the write, so a round parity bit (or
// none) dates it.
#pragma once
#include <optional>
#include "util.h"

namespace aph {

class World;

namespace comms {

// An ally fighting at `pos`, for teammates near enough to join.
struct Rally {
    int round;
    vec2 pos;
};

// An ally attacking a damaging camp group, for teammates near enough to help clear it.
struct Help {
    int round;
    int group;
};

// Teammates' turns since their last read, read and merged into the world.
void receive(World& world);
// With `refresh`, re-read vision first, but only if there is a slot to fill.
void send(World& world, bool refresh);
void post_rally(int round, vec2 pos);
// The latest rally a teammate posted: our own, from a chase we no longer take, leads nowhere.
std::optional<Rally> rally();
void post_help(int round, int group);
// The latest help request read or posted.
std::optional<Help> help();

} // namespace comms
} // namespace aph
