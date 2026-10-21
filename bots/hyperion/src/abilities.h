// Damage and stun casts: Ryth, Prism, Stellar, Marcella's slot 1, Tavi, Ren, Cassi and Heart of Ruin's
// dash landing.
#pragma once
#include "util.h"

namespace aph {

class World;
struct ChampionBelief;

// The best enemy-hitting cast at a visible enemy this turn, if worth it. An excludes-walking cast
// must also be worth `walk`, the walk it forgoes.
bool cast_at_enemies(const World& world, float walk = 0);

// A damage or stun cast on the group being farmed, held while enemies are near.
// Call only when not walking this turn. `attackers_only`: target only members with Strength.
// `any_value`: even a cast worth less than usual, as on a group's last hit points.
bool cast_at_camp(const World& world, int group, bool attackers_only = false, bool any_value = false);

// A visible enemy tributing a bag that wins them the game.
bool enemy_tribute_wins(const World& world, const ChampionBelief& e);

// What stunning e is worth, in enemy health points. `damaging`: the hit's worth already counts a
// cancelled recall.
float stun_worth(const World& world, const ChampionBelief& e, bool damaging);

// A dash landing at p would hit a member of a sleeping group that strikes, waking it.
bool landing_wakes(const World& world, vec2 p, int radius);

// The tiles within `reach` of `here` that a tracked unseen enemy on at most 9 tiles may hold whose
// retaliation would kill us, none if the cast deals no `raw` damage: its ground or landing area must
// not hit them, though unseen enemies are never aimed at. Up to `size` into `out`; returns how many.
// cast_at_enemies and the strike search share it, so both ban the same centres.
int unseen_retaliators(const World& world, vec2 here, int reach, float raw, vec2* out, int size);

} // namespace aph
