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

// What teammates posted since our previous turn, merged into the world.
void receive(World& world);
// With `refresh`, re-read vision first, but only if there is a slot to fill.
void send(World& world, bool refresh);
// The gems we carry, posted when it changes.
void bag(int gems);
// The gems an ally (by index) carries as it last posted, -1 if never, 0 while dead.
int bag_of(const World& world, int ally);
// The group we work towards (-1 for none), posted when it changes.
void claim(int group);
// The group an ally (by index) claims, -1 for none or while it is dead.
int claim_of(const World& world, int ally);

// Post the enemy (by index) we fight this turn: it takes the sighting slot over plain sightings.
void post_rally(int enemy);

} // namespace comms
} // namespace aph
