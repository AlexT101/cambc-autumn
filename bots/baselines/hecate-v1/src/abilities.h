// Damage and stun casts: Ryth, Prism, Stellar, Marcella's slot 1, Tavi, Ren and Cassi.
#pragma once

namespace aph {

class World;
struct ChampionBelief;

// The best enemy-hitting cast this turn, if worth it. With `keep_walk`, an excludes-walking cast
// must be worth the walk (a kill or a cancelled tribute) or stun every visible enemy that could
// reach us next turn. `hold`: a tributer hit only to kill it.
bool cast_at_enemies(const World& world, bool keep_walk = false, const ChampionBelief* hold = nullptr);

// A damage or stun cast on the group being farmed (-1: the group of a camp in attack range),
// held while enemies are near. Call only when not walking this turn.
// `attackers_only`: target only members with Strength.
// `any_value`: even a cast worth less than usual, as on a group's last hit points.
bool cast_at_camp(const World& world, int group, bool attackers_only = false, bool any_value = false);

// A visible enemy tributing a bag that wins them the game.
bool enemy_tribute_wins(const World& world, const ChampionBelief& e);

} // namespace aph
