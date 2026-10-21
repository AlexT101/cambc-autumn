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
// `group`: only that group's camps. `safety`: the turn's Safety; with it, a reset that does not
// kill is held while a visible enemy can hit us and mend_due() (null: never held).
bool reset_and_attack_enemy(const World& world, bool stunning_only = false, Safety* safety = nullptr);
bool reset_and_attack_camp(const World& world, Safety* safety, int group);
// A camp tile lies within `range` of p.
bool camp_in_reach(const World& world, vec2 p, int range);

// Travel: dash to the landing nearest the goals if it gains at least 2 steps and no enemy is near
// enough to want the dash for a fight or an escape. Goals more than `max_steps` away are not searched for.
bool dash_towards(const World& world, Pathing& pathing, const bitboard& goals, int max_steps = unreachable);
bool dash_towards(const World& world, Pathing& pathing, const Field& field);
// Over a hole or altar line beside us (StaticMap::crossable) where `field` gains: unlike a travel
// dash, with enemies near, as long as the landing is no deeper in their reach.
bool dash_across(const World& world, Pathing& pathing, const Field& field);
// Into attack range of `target`; attack after it.
bool dash_to_attack(const World& world, Pathing& pathing, const ChampionBelief& target);
// Out of the reach of visible enemies and awake camps, tie-broken towards `home`.
bool dash_away(const World& world, Pathing& pathing, const Field& home);

// A heal restoring `gain` of `amount` to an ally at `fraction` of its health is worth the cooldown.
bool worth_healing(float amount, float gain, float fraction);
// The one heal and shield valuer: casts the heal or shield due here, if any. A heal is due on the
// ally it restores most, if worth_healing; a shield while shield_cap against the real hits here is
// above 0: visible enemies' blows, camps that pick us (Safety::tile), and every member in reach of
// a group we hit this turn (`farmed`, the group farm chose, hit from attack range; once our attack
// is spent, any group in attack range). Never a shield on our spawn. `site` (debug MEND lines):
// d before the goal, m on spawn after the hits, r a retreat the search did not plan (a reset that
// may kill holds the shield), a the turn's end.
bool mend(const World& world, Safety& safety, int farmed, char site = 'a');
// Whether mend() would cast here, casting nothing.
bool mend_due(const World& world, Safety& safety, int farmed);

} // namespace aph
