#pragma once

#include "../../../params.h"
#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <limits>
#include <memory>
#include <optional>
#include <span>
#include <vector>
#include "../../comms.h"

namespace aph {
class World;
struct Aims;
}

namespace aph {
namespace {
bool place_ward(const World& world, Aims& aims, bool grow = true);

bool try_ward(vec2 p);

// Our latest ward, as the engine lists them; off the map if none.
vec2 our_ward();

// What the allies' wards other than ours see (rules: wards.vision): a shadowcast of ward_vision_radius,
// walls and bushes opaque but a ward's own cluster, which it sees across. The wards are those in sight
// and those comms tells (a ward in a bush is seen only from its cluster). A cluster not found yet counts
// as opaque. Into `out`.
void other_wards_vision(const World& world, vec2 ours, bitboard& out);

// Attackers in a bush stay unseen from outside it, and a ward inside sees across its cluster.
// Our one ward never expires, so replace it only by a cluster with more tiles in ability range of
// here and of our work (claimed group or waited-at altar), where we will be again.
// Without `grow`, only if every cluster that needs is found already.
bool ward_bushes(const World& world, Aims& aims, bool grow);

bool place_ward(const World& world, Aims& aims, bool grow);

}
}
