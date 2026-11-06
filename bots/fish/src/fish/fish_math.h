// Intercontinental Fish's shared definitions (research/fish-2026-11-05/FISH_MODEL.md section 2),
// as its imitation rules measure them: health fraction, band, one-turn damage reach D, danger,
// kill available, acceptable tiles, side EHP ratio and the holder and priority ranks. D ignores
// terrain, blockers, items and camps, as the rules were fitted with it (tools/fish/combat_common.py).
#pragma once
#include "../model/world.h"

namespace aph::fish {

// Fitted thresholds (FISH_MODEL 9.1, 10.1).
inline constexpr float accept_health = 0.49f;
inline constexpr float accept_danger = 0.28f;
inline constexpr float gem_health_factor = 0.65f;

inline float ehp(const ChampionBelief& c) { return c.health + c.shield; }
inline float health_fraction(const ChampionBelief& c) { return c.max_health > 0 ? c.health / c.max_health : 0.0f; }
inline float gem_health(const ChampionBelief& c) { return health_fraction(c) * (c.gems > 0 ? gem_health_factor : 1.0f); }

// 0..3: max(0, floor(4 (1 - min(1, EHP / max) x (0.65 carrying)))).
int band(float health, float shield, float max_health, int gems);
inline int band(const ChampionBelief& c) { return band(c.health, c.shield, c.max_health, c.gems); }

// The most damage `c` deals in one turn to a unit at Chebyshev distance d, its slots as ready in
// `round`: a basic (melee with a walk: reach 2; ranged 3), doubled by a ready reset; a plain dash
// adds 2 to the basic's reach; a ready damage spell within 4 (ground 5) plus a basic within range;
// Heart of Ruin's landing within 4 plus a basic. One cast a turn; Heart of Ruin's passive applies.
float reach_damage(const ChampionBelief& c, int d, int round);

// Our D's reach: the farthest distance at which reach_damage can be positive for any kit.
inline constexpr int max_reach = 5;

// Sum of D of the visible enemies (not stunned for their next turn) at `tile`, over `own_ehp`.
float danger(const World& world, vec2 tile, float own_ehp);
// The sum of D of every visible enemy at `tile` (contact level's threat, stuns not excluded).
float threat(const World& world, vec2 tile);

// A kill from tile p for us, who start the turn at `start` (combat_tiles.py): a melee champion hits
// enemies adjacent to p or to `start`; a ranged one those within 3 of p if it stays or has a reset
// ready; a kill when D at basic range covers the enemy's EHP.
bool kill_available(const World& world, vec2 start, vec2 p);
// A kill from p, or h > 0.49 and danger(p) <= 0.28.
bool acceptable(const World& world, vec2 start, vec2 p);

// (our EHP + visible allies' within 8) / visible enemies' EHP within 8; huge with none.
float side_ehp_ratio(const World& world, vec2 at);

// Capture holder rank, 0 highest: Marcella > Vesper Vale > Vendetta > Heart of Ruin > Cassi > Issac
// > Willow; the rest (unranked) 7.
int holder_rank(cambc::champion_type type);

// Fish's priority rank of ally `index`: 2 + its place in the team sorted by base max health,
// descending, ties by type index, but Heart of Ruin before Varg.
int priority_rank(const World& world, int index);

} // namespace aph::fish
