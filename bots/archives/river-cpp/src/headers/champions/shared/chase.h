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
struct Moment;
struct ChampionBelief;
class World;
class Pathing;
class Safety;
struct Aims;
}

namespace aph {
namespace {
// Our steps from `here` to stop a carrier's bag from scoring, unreachable if it scores first. A
// tribute under way: a stun or a lock on its altar cancels it (a lock even Marcella's), a kill
// takes the bag. Walking, it outpaces nobody but stops at an altar, the nearest as the crow
// flies: we must reach that altar before its tribute there lands.
int intercept_steps(const World& world, const ChampionBelief& e, vec2 here);

// The visible enemy whose kill pays most a turn to reach and kill it, among those whose local
// fight we win even when they strike first; never one on or next to its spawn, where it heals.
const ChampionBelief* prey(const World& world, Safety& safety);

bool chase(const World& world, Pathing& pathing, Safety& safety);

// A champion's turn start in `round`, where its channel completes.
Moment turn_start(const World& world, const ChampionBelief& c, int round);

// The earliest our winning bag's win lands: our tribute's end, or, none under way, a walk to the
// nearest altar as the crow flies and a whole channel; and no sooner than the allies' tributes in
// sight that gems_short counts.
Moment win_lands(const World& world);

// A visible enemy whose tribute wins them the game, in reach of a ready stun of ours, and lands
// before our bag's win if ours wins; null if none.
const ChampionBelief* stoppable_winning_tribute(const World& world);

// A visible ally out of channels, acting before an enemy's tribute lands, can stop it alone (its
// game_ender sees the race as we do): a ready stun in reach, or a carried lock within 2 of the
// altar, unless that altar is ours too (its place_lock spares our winning tribute). An enemy in a
// bush is seen only from its cluster: not counted.
bool ally_stops(const World& world, const ChampionBelief& e);

// A visible enemy whose bag (both, for a walking Cassi and Issac) ends the game once tributed and that we
// can stop: nothing we gain meanwhile counts unless our own bag wins first. The nearest; null if none.
const ChampionBelief* game_ender(const World& world);

// Into reach of the enemy whose bag ends the game, whatever the risk: a stun or a lock if it is
// tributing, else attacks, followed until it stops at an altar.
void stop_game_ender(const World& world, Pathing& pathing, Aims& aims, const ChampionBelief& e);

}
}
