// Damage and stun casts: Ryth, Prism, Stellar, Marcella's slot 1, Tavi, Ren, Cassi and Heart of Ruin's
// dash landing.
#pragma once
#include "util.h"

namespace aph {

class World;
class Pathing;
struct ChampionBelief;

// The best enemy-hitting cast at a visible enemy this turn, if worth it. An excludes-walking cast
// must also be worth `walk`, the walk it forgoes.
bool cast_at_enemies(const World& world, Pathing& pathing, float walk = 0);

// A damage or stun cast on the group being farmed, held while enemies are near.
// Call only when not walking this turn. `attackers_only`: target only members with Strength.
// `any_value`: even a cast worth less than usual, as on a group's last hit points.
bool cast_at_camp(const World& world, Pathing& pathing, int group, bool attackers_only = false, bool any_value = false);

// What a hit of `damage` on an enemy at `health` is worth in enemy health points: a kill takes the
// bag (`bag`, gems x gem_value) and its life; other damage counts only off its spawn (it heals at
// its turn end), as far as it takes Cassi or Issac below `partner`, plus `recall` for a cancelled recall.
float hit_worth(float damage, float health, bool spawn, float bag, float partner, float recall = 0);

// Ren's passive deals 0.2 x its Focus back to whoever damages it, even as it dies. Whether a blow
// dealing `damage` to enemies whose retaliation sums to `back` kills us at `health`: never taken.
inline bool retaliation_kills(float damage, float back, float health) { return damage > 0 && back >= health; }

// A visible enemy tributing a bag that wins them the game.
bool enemy_tribute_wins(const World& world, const ChampionBelief& e);

// What stunning e is worth, in enemy health points. `damaging`: the hit's worth already counts a
// cancelled recall.
float stun_worth(const World& world, const ChampionBelief& e, bool damaging);

// A dash landing at p would hit a member of a sleeping group that strikes, waking it.
bool landing_wakes(const World& world, vec2 p, int radius);

constexpr int max_unseen_tiles = 9; // unseen enemies spread over more tiles are not kept off

// The tiles within `reach` of `here` that a tracked unseen enemy on at most max_unseen_tiles may hold
// whose retaliation would kill us at `health`, none if the cast deals no `raw` damage: its ground or
// landing area must not hit them, though unseen enemies are never aimed at. Up to `size` into `out`;
// returns how many. cast_at_enemies and the strike search share it, so both ban the same tiles.
int unseen_retaliators(const World& world, vec2 here, int reach, float raw, float health, vec2* out, int size);

} // namespace aph
