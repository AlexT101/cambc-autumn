// Damage and stun casts: Ryth, Prism, Stellar, Marcella's slot 1, Tavi, Ren, Cassi and Heart of Ruin's
// dash landing.
#pragma once
#include <algorithm>
#include <cmath>
#include "../params.h"
#include "../util.h"

namespace aph {

class World;
struct ChampionBelief;

// What taking a target at `health` of `full` (with `bag` on it) down to a kill is worth: a hit is
// worth the fall in this, the same summed in any order. From full health it is the kill's worth,
// full + life + bag; damage counts params::chip_value of itself plus a share of the rest growing as
// the square root of the health taken off, so damage on a weak target counts most.
inline float kill_distance(float health, float full, float bag) {
    if (health <= 0) return 0;
    full = std::max(full, health);
    const float rest = (1.0f - params::chip_value) * full + params::life_value + bag;
    return params::chip_value * health + rest * std::sqrt(health / full);
}

// The best enemy-hitting cast this turn, if worth it. An excludes-walking cast must also be worth
// `walk`, the walk it forgoes, unless it stuns every visible enemy that could reach us next turn.
// `lethal_landings_only`: only a dash landing whose area kills a visible enemy (engine damage).
// `attempted`: a native cast was tried.
bool cast_at_enemies(const World& world, float walk = 0, bool lethal_landings_only = false, bool* attempted = nullptr);

// A quoted escape walk is available: keep nonexclusive casts, but certify a walk-consuming
// unit cast only when it kills or effectively stuns the sole modeled threat (`enemy`, else -1).
// Ground casts are not certified by this narrow proof. `attempted` means a native cast was tried.
bool cast_at_enemies_for_escape(const World& world, int enemy, float walk, bool& attempted);

// A damage or stun cast on the group being farmed, held while enemies are near.
// Call only when not walking this turn. `attackers_only`: target only members with Strength.
// `any_value`: even a cast worth less than usual, as on a group's last hit points.
bool cast_at_camp(const World& world, int group, bool attackers_only = false, bool any_value = false);

// A ranged caster's safe approach: a harmful unit target or at least two harmful ground targets.
bool cast_at_camp_on_approach(const World& world, int group);

// A visible enemy tributing a bag that wins them the game.
bool enemy_tribute_wins(const World& world, const ChampionBelief& e);

// What killing e is worth beyond its health and bag: the tribute it cancels.
float kill_stops(const World& world, const ChampionBelief& e);

// What stunning e is worth, in enemy health points: nothing on a blow that kills it, which takes
// kill_stops instead. `damaging`: the hit's worth already counts a cancelled recall.
float stun_worth(const World& world, const ChampionBelief& e, bool damaging);

// A dash landing at p would hit a member of a sleeping group that strikes, waking it.
bool landing_wakes(const World& world, vec2 p, int radius);

// The least an enemy-hitting cast must be worth, in enemy health: it stands for what the slot could
// do in its next ability_cooldown rounds, but is a tuned flat value, not worked out from them.
inline constexpr float cast_cost = 40;

constexpr int max_unseen_tiles = 9; // unseen enemies spread over more tiles are not aimed at

// e is tracked, unseen and on few tiles, and its retaliation would kill us at `health`.
bool unseen_suicidal(const ChampionBelief& e, float health, float taken = 1);

} // namespace aph
