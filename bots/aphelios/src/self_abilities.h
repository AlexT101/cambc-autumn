// Attack resets, dashes, heals and shields. Each casts at most once and returns true if it did;
// only one cast succeeds per turn, so call the most valuable first.
#pragma once
#include "util.h"

namespace aph {

class World;
class Pathing;
struct ChampionBelief;

// With the basic attack spent (by attacking, or by a ranged champion's walk), reset it and attack
// again. Enemies: the weakest in range. Camps: the member nearest death (a Vendetta kill readies
// both abilities), held back while an enemy is close enough to want the reset for a fight.
// `stunning_only`: only a reset whose attack stuns (Marcella), on an enemy it would stun; call it
// before abilities.cpp's casts, which share the one cast per turn, and the plain one after.
bool reset_and_attack_enemy(const World& world, bool stunning_only = false);
bool reset_and_attack_camp(const World& world);

// Travel: dash to the landing nearest the goals if it gains at least 2 steps and no enemy is near
// enough to want the dash for a fight or an escape.
bool dash_towards(const World& world, Pathing& pathing, const bitboard& goals);
bool dash_towards(const World& world, Pathing& pathing, const Field& field);
// Into attack range of `target`, else of a visible enemy we can finish or are beating; attack
// after it.
bool dash_to_attack(const World& world, Pathing& pathing, const ChampionBelief* target = nullptr);
// Out of the reach of visible enemies and awake camps, tie-broken towards `home`.
bool dash_away(const World& world, Pathing& pathing, const Field& home);

// Willow: the ally the heal restores most, if it restores enough or the ally is low.
bool heal_ally(const World& world);
// Varg: before damage from an awake camp, a camp we are hitting or an enemy in reach.
bool shield_if_needed(const World& world);

} // namespace aph
