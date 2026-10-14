// Damage and stun casts: Ryth, Prism, Stellar, Marcella's slot 1, Tavi, Ren and Cassi.
#pragma once

namespace aph {

class World;

// An excludes-walking damage or stun slot is ready and still castable this turn.
bool exclusive_cast_ready(const World& world);

// The best enemy-hitting cast this turn, if worth it. With `keep_walk`, an excludes-walking cast
// must be worth the walk (a kill or a cancelled tribute).
bool cast_at_enemies(const World& world, bool keep_walk = false);

// A damage or stun cast on the group being farmed (-1: the group of a camp in attack range),
// held while enemies are near. Call only when not walking this turn.
bool cast_at_camp(const World& world, int group);

} // namespace aph
