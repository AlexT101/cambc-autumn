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
struct CampGroup;
struct ChampionBelief;
struct CampBelief;
class World;
class Pathing;
class Safety;
struct Aims;
}

namespace aph {
namespace {
// Allies other than us in sight on `tiles`; with `below`, only those of a lower index.
int allies_on(const World& world, const bitboard& tiles, int below = 1 << 30);

bool enemy_on(const World& world, const bitboard& tiles);

// Our part of the gems a capture we stand on pays: shares are floored, the lowest id gets the rest.
int capture_share(const World& world, int g);

// A group other than a Monolith too big for one champion or a crew, like stampede's shared block
// of elk and gem clusters.
bool big_group(const CampGroup& G);

// Split until each share's tribute fits the window its safety is judged over (tribute_safe).
int holders(const CampGroup& G);

const ChampionBelief* prism_capture_holder(const World& world, const CampGroup& G);

// Whether a cleared group's capture is ours. Its holders(G) places go first to a Prism keeping its gems
// (prism_capture_holder), then to the allies on its tiles (Heart of Ruin last, so another ally there
// relieves it), most gems carried first, then to the nearest of the others by steps from its centre (as
// the crow flies until the centre fields are warm); ties to the lower index. Every ally works it out the
// same from the same positions and bags.
bool capture_ours(const World& world, Pathing& pathing, int g);

// A hold whose payout falls after the last round never pays.
bool pays_too_late(const CampBelief& c);

// On a cleared group's tile that no lower-id ally also holds, with no enemy on any of its tiles:
// stepping off loses the capture's progress, and it pays within six rounds.
bool holding_capture(const World& world, Pathing& pathing);

// The nearest cleared group whose capture is ours (capture_ours) and that we are not on: reward left, no
// Monolith, no enemy on it, paying before the end. -1 if none.
int our_capture(const World& world, Pathing& pathing);

// A Prism keeping its gems should hold the cleared group we stand on, and nothing is about to hit it: we step off.
bool must_yield(const World& world, Pathing& pathing, Safety& safety, const Aims& aims);

// Off the group we stand on, to a free neighbour no camp hits.
bool step_off_capture(const World& world, Pathing& pathing, Safety& safety, Aims& aims);

// Vesper Vale's landing on the group our Heart of Ruin holds, to take the hold over (capture_ours puts HoR
// last among the allies on it) and free it to farm: off the map if none. It arrives before HoR leaves:
// only HoR's own sight of us releases the hold.
vec2 relief_landing(const World& world, Pathing& pathing, Safety& safety, const Aims& aims);

// Vesper Vale's dash onto the relief landing.
bool relieve_capture(const World& world, Pathing& pathing, Aims& aims, vec2 landing);

// On a cleared group's tile worth contesting while the enemy holds it or stands on another:
// leaving lets their hold pay.
bool contesting(const World& world);

// A capture about to pay is worth finishing while they are still a walk away.
bool paying_soon(const World& world, Pathing& pathing);

// Recall from a capture we hold (holding_capture), timed to land home the turn it pays: the gems
// skip the walk when an altar is nearer by way of home, and the stop heals and shops.
bool capture_recall(const World& world, Pathing& pathing, Safety& safety, Aims& aims);

// Rounds before an enemy hold pays: a body of ours on a camp tile by then stops it.
int enemy_hold_left(const World& world, const CampBelief& c);

// An ally that will not come to group g: tributing, on a recall kept through a turn, or working
// towards another group.
bool bound_elsewhere(const World& world, const ChampionBelief& a, int g);

// Allies in sight on group g's tiles, or free for it and nearer its centre than `here` (ties to
// the lower index), already make enough holders.
bool capture_taken(const World& world, int g, vec2 here);

bool ally_claims(const World& world, int g);

// Of `tiles`, those with no champion we see on them, in a scratch board valid until the next call.
const bitboard& free_tiles(const bitboard& tiles);

// A cleared gem group in sight that the enemy holds or stands on, and that we can reach before the
// hold pays: a body of ours on one of its tiles stops the count. Its gems, denied within a few
// steps, beat any farm cycle's rate, however small the group.
bool contest_capture(const World& world, Pathing& pathing, Aims& aims);

// On a capture we hold or contest: the hold needs no turn, so hit another group in reach that
// cannot hit back or already does.
void hold_capture(const World& world, Aims& aims, bool attacked);

}
}
