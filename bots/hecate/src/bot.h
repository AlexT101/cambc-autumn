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
    bool crew = false;    // joining an ally's claim rather than our own
    bool siege = false;   // our claim is a Monolith or a group sealing the altars (seals()), attacked by the team together
    int staged_since = -1; // round we started waiting near it for the others
    int wait_altar = -1, wait_since = -1;   // the altar we wait at for a safe tribute, since when
    int avoid_altar = -1, avoid_until = -1; // one we gave up waiting at, skipped until that round
    bool wants_crystal = false; // a crystal hop to an altar would have beaten walking to bank
    vec2 ward{-1, -1};    // our latest ward
    vec2 bushes_watched{-1, -1}; // a tile whose bushes in ward reach are all in our cluster or our ward's
};

// `world` is as of the turn's start; ask cambc for anything that changes after acting.
void play_turn(const World& world, Pathing& pathing, Memory& memory);
// With the turn's spare fuel: the walk to our farm choice from where we ended, so that a costly
// turn next round still walks it well.
void prepare_next_turn(const World& world, Pathing& pathing, const Memory& memory);

} // namespace aph
