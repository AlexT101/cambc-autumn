#pragma once
#include "util.h"

namespace aph {

class World;
class Pathing;

struct Memory {
    int round = -1;    // of our previous turn
    float health = 0;  // at its end
    float damage = 0;  // taken since, as of this turn's start
    bool banking = false; // our bag headed for an altar rather than another capture last turn
    int farm_group = -1;  // farm's latest choice: kept when near tied, walked to on short fuel
    int claim = -1;       // the group we told allies we work towards, or -1
    int live_claim = -1;  // our claim observed alive at the start of our previous turn
    bool crew = false;    // joining an ally's claim rather than our own
    bool siege = false;   // our claim is a Monolith or a group sealing the altars (seals()), attacked by the team together
    int staged_since = -1; // round we started waiting near it for the others
    int wait_altar = -1, wait_since = -1;   // the altar we wait at for a safe tribute, since when
    int avoid_altar = -1, avoid_until = -1; // one we gave up waiting at, skipped until that round
    bool wants_crystal = false; // a crystal hop to an altar would have beaten walking to bank
    int hop_refused = -1, hop_refused_until = -1; // a farm hop no safe landing was found for, skipped until then
    int recovery_start = -1, recovery_turns = 0;
    int recovery_group = -1, recovery_closed_group = -1;
    bool recovery_reentry = false;
    float recovery_health = 0, recovery_closed_health = -1;
    int formation_start = -1, formation_turns = 0;
    vec2 ward{-1, -1};    // our latest ward
    vec2 bushes_watched{-1, -1}; // a tile whose bushes in ward reach are all in our cluster or our ward's
};

// `world` is as of the turn's start, observed again after a ward; ask cambc for anything that
// changes after acting.
void play_turn(World& world, Pathing& pathing, Memory& memory);
// With the turn's spare fuel, each step only while more than `fuel_floor` would remain: the walk
// to our farm choice from where we ended, the farm loop's order and the altar walk.
void prepare_next_turn(const World& world, Pathing& pathing, const Memory& memory, std::uint64_t fuel_floor);

} // namespace aph
