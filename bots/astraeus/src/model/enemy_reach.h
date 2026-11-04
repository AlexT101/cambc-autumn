// Terrain-aware enemy reach: how far an enemy champion really is from a tile, by the walk it needs
// round walls, holes and altars (and across the lines a dash jumps). The one model for every test
// of whether, or how soon, an enemy beyond its next turn can get at a tile: Safety::approach
// (stands, pursuers), may_reach_within (recall and hold keeps, the recall line) and the travel dash's clearance.
// An enemy's next turn on the map is Reach's (safety.h), which sees units too.
//
// distance(e, from, p) is the Chebyshev distance at which, on open ground, e standing at `from` would
// reach p as soon as it does here:
//     D = max(dist(from, p), act + min{ S(q) : dist(q, p) <= act })    (D = dist(from, p) within act)
// S: static king steps from `from` over the tiles open to it (StaticMap::blocked_for_them); for a
// dasher also over the hole and altar tiles its dash jumps (their_dash_walls), at the two steps the
// dash is. act: how far it damages or stuns without moving. Units and camps are left out, as they
// move or die, so S never exceeds its real walk. On open ground min S = dist - act, so D = dist and a
// Chebyshev test `dist <= X` reads the same as `D <= X`: only terrain raises D. No walk bringing it
// within `act` of p: `far`.
#pragma once
#include <cambc.h>
#include "../champions.h"
#include "../util.h"

namespace aph {

class World;
struct ChampionBelief;

namespace enemy_reach {

inline constexpr int far = 1 << 14;

struct Profile {
    int act = 0;        // act_range()
    bool dasher = false; // walks over the tiles its dash jumps
    // Walks our side's static walls (StaticMap::our_walls by `dash_kind`), not the enemy's: an ally.
    bool ours = false;
    int dash_kind = 0;
};
// The farthest it damages or stuns from where it stands: its basic attack (with Varg's splash), a
// damage or stun spell's range and area, a landing dash's radius.
int act_range(const ChampionFacts& f);
Profile profile(const ChampionFacts& f);
// An ally's, over our side's walls by its own dash kind, whoever asks.
Profile ally_profile(const ChampionFacts& f);
// Every live enemy's at once, the widest act and a dasher if any is: for a unit whose type is unknown.
Profile widest(const World& world);

// D (above) when it is at most `limit`, else some value above `limit` (`far` once no walk gets
// within act of p). `limit` past dist(from, p) costs a host search per step at most, each kept for
// the game while the enemy stands on `from`.
int distance(const World& world, const Profile& who, vec2 from, vec2 p, int limit);
int distance(const World& world, const ChampionBelief& e, vec2 from, vec2 p, int limit);
// distance(...) <= x, by one test.
bool within(const World& world, const Profile& who, vec2 from, vec2 p, int x);
bool within(const World& world, const ChampionBelief& e, vec2 from, vec2 p, int x);
// Where a visible enemy acts from: a seen teleport's landing, else its tile (its last, unseen).
vec2 origin(const ChampionBelief& e);

// Builds their_dash_walls while more than `fuel_floor` remains, if an enemy has a dash; true once
// nothing is left to build.
bool warm_up(const World& world, std::uint64_t fuel_floor);

} // namespace enemy_reach

} // namespace aph
