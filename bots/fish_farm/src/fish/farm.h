// Intercontinental Fish's farm (FISH_MODEL.md 7.2-7.5, 8.1-8.2), defined in fish/farm_turn.cc.
#pragma once
#include "../bot_parts.h"
#include "farm_memory.h"
#include "switches.h"

namespace aph {

namespace {

namespace fish_farm {

// Turn start, before the channels: sightings, the recall timer, and the destination decisions
// (after a payout, after a spawn exit, and re-decisions between them).
void events(World& world, Pathing& pathing, Safety& safety, Memory& memory);
// The farm turn towards the destination; false with none (carry_bag then banks).
bool farm_turn(World& world, Pathing& pathing, Safety& safety, Memory& memory);
// The walk home of a payout's home trip when it is at most 5 steps; true if it took the turn.
bool home_walk(World& world, Pathing& pathing, Safety& safety);
// 7.4's holder rule, standing on cleared group g with no enemy on it.
bool holder_stays(const World& world, Pathing& pathing, int g, vec2 here);
// A turn with nothing better to do than keep the prepared recall (8.1): a capture hold, a respawn
// wait at the destination, or the home trip.
bool recall_idle(const World& world, Pathing& pathing, Safety& safety);
// The home trip is off (the gate failed, or the recall was cancelled for a fight).
void drop_home();
// Turn end, after every action: the visit history and where we stand.
void turn_end(const World& world);

} // namespace fish_farm

} // namespace

} // namespace aph
