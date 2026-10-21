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
// `stunnable_only`, stuns it; with that flag, only enemies a stun affects.
std::optional<cambc::champion> attack_target(const World& world, bool stunnable_only = false);

// With the basic attack spent (by attacking, or by a ranged champion's walk), reset it and attack
// again. Enemies: the weakest in range. Camps: the member nearest death (a Vendetta kill readies
// both abilities), held back while an enemy is close enough to want the reset for a fight.
// `stunning_only`: only a reset whose attack stuns (Marcella), on an enemy it would stun; call it
// before abilities.cpp's casts, which share the one cast per turn, and the plain one after.
// `group`: only that group's camps. `safety`: the turn's Safety (W4-A's holds read it); null holds
// as without it.
bool reset_and_attack_enemy(const World& world, bool stunning_only = false, Safety* safety = nullptr);
bool reset_and_attack_camp(const World& world, Safety* safety, int group);
// A camp tile lies within `range` of p.
bool camp_in_reach(const World& world, vec2 p, int range);

// Exposure, read from pathing.safety() (none: not ranked): tile(p).worst(), then the depth in the
// reach of the visible enemies and camps that hit p.
// Travel: dash to the landing nearest the goals if it gains at least 2 steps, no enemy is near
// enough to want the dash for a fight or an escape, and its worst is no more than here's. Goals
// more than `max_steps` away are not searched for.
bool dash_towards(const World& world, Pathing& pathing, const bitboard& goals, int max_steps = unreachable);
bool dash_towards(const World& world, Pathing& pathing, const Field& field);
// Over a hole or altar line beside us (StaticMap::crossable) where `field` gains: unlike a travel
// dash, with enemies near, as long as the enemies (seen and unseen) hit the landing no harder.
bool dash_across(const World& world, Pathing& pathing, const Field& field);
// Into attack range of `target` (a melee walk's step short), least exposed first; attack after it.
bool dash_to_attack(const World& world, Pathing& pathing, const ChampionBelief& target);

// Willow: the ally the heal restores most, if it restores enough or the ally is low.
bool heal_ally(const World& world);
// A heal restoring `gain` of `amount` to an ally at `fraction` of its health is worth the cooldown.
bool worth_healing(float amount, float gain, float fraction);
// Varg: before damage from an awake camp, a camp we are hitting or an enemy in reach. `farmed`:
// the group farm chose, which we hit from attack range; another group's camp in attack range is
// hit only if our attack is spent.
bool shield_if_needed(const World& world, Safety& safety, int farmed);
// The one heal and shield valuer (W4-A): casts the heal or shield due here, if any. Until W4-A,
// heal_ally then shield_if_needed.
bool mend(const World& world, Safety& safety, int farmed);
// Whether mend() would cast here, casting nothing. Until W4-A, shield_if_needed's test.
bool mend_due(const World& world, Safety& safety, int farmed);

} // namespace aph
