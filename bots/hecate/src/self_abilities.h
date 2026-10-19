// Attack resets, dashes, heals and shields. Each casts at most once and returns true if it did;
// only one cast succeeds per turn, so call the most valuable first.
#pragma once
#include <optional>
#include "util.h"

namespace aph {

class World;
class Pathing;
class Safety;
struct ChampionBelief;

// The enemy a basic attack from here should hit, read live as vision changes when we move: the
// weakest, or for Varg the most value counting splash. Never one whose retaliation would kill us,
// nor one on its spawn (it heals at its turn end) unless the hit kills it or, with
// `stunnable_only`, stuns it; with that flag, only enemies a stun affects. `hold`: a tributer
// hit only to kill it.
std::optional<cambc::champion> attack_target(const World& world, bool stunnable_only = false,
                                             const ChampionBelief* hold = nullptr);

// With the basic attack spent (by attacking, or by a ranged champion's walk), reset it and attack
// again. Enemies: the weakest in range. Camps: the member nearest death (a Vendetta kill readies
// both abilities), held back while an enemy is close enough to want the reset for a fight.
// `stunning_only`: only a reset whose attack stuns (Marcella), on an enemy it would stun; call it
// before abilities.cpp's casts, which share the one cast per turn, and the plain one after.
// `hold` as for attack_target. `group`: only that group's camps.
bool reset_and_attack_enemy(const World& world, bool stunning_only = false, const ChampionBelief* hold = nullptr);
bool reset_and_attack_camp(const World& world, int group);
// A camp tile lies within `range` of p.
bool camp_in_reach(const World& world, vec2 p, int range);

// Travel: dash to the landing nearest the goals if it gains at least 2 steps and no enemy is near
// enough to want the dash for a fight or an escape.
bool dash_towards(const World& world, Pathing& pathing, const bitboard& goals);
bool dash_towards(const World& world, Pathing& pathing, const Field& field);
// Into attack range of `target`, else of a visible enemy we can finish or are beating (`hold` only
// if we can finish it); attack after it.
bool dash_to_attack(const World& world, Pathing& pathing, const ChampionBelief* target = nullptr,
                    const ChampionBelief* hold = nullptr);
// Out of the reach of visible enemies and awake camps, tie-broken towards `home`.
bool dash_away(const World& world, Pathing& pathing, const Field& home);

// Willow: the ally the heal restores most, if it restores enough or the ally is low.
bool heal_ally(const World& world);
// Varg: before damage from an awake camp, a camp we are hitting or an enemy in reach. `farmed`:
// the group farm chose, which we hit from attack range; another group's camp in attack range is
// hit only if our attack is spent.
bool shield_if_needed(const World& world, Safety& safety, int farmed);

} // namespace aph
