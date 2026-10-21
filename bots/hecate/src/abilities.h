// Damage and stun casts: Ryth, Prism, Stellar, Marcella's slot 1, Tavi, Ren, Cassi and Heart of Ruin's
// dash landing.
#pragma once
#include "util.h"

namespace aph {

class World;
struct ChampionBelief;

// The best enemy-hitting cast this turn, if worth it. With `keep_walk`, an excludes-walking cast
// must be worth the walk (a kill or a cancelled tribute) or stun every visible enemy that could
// reach us next turn; a dash landing always must, as it moves us.
bool cast_at_enemies(const World& world, bool keep_walk = false);

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

} // namespace aph
