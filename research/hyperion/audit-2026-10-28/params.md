# Audit: bots/astraeus/src/params.h

## Changed

Commit `astraeus audit (params): cleanup` (77fa6d1e). Comments only. Bench replays byte-identical (8/8), fuel +0.00%.

- Dropped transient references ("as before the model", "as in v61", "about one ladder solo chip visit") and the meaningless "Unrelated to recall_health_fraction, though both are 0.35".
- Added comments for constants that had none: `draft_preference` (the fallback order), `recall_health_fraction` (go-home line, and the health above it is what camps may cost), `siege_respawn_wait`, `brake_bag`.
- Fixed comments that had drifted from the code:
  - `gold_farmer_weight` said Cassi only; Tavi on `tavi_map` 3-pick maps gets it too (draft.cc:148, farm.cc:297).
  - `hurt_health_fraction` described only two of its uses; it also judges enemies (fight.cc:270), allies (capture.cc:139,147), Willow's heals (self_abilities.cc:473) and untargeted dash-ins (self_abilities.cc:379).
  - `pack_ally_radius` and the others hard-coded "below half health" instead of naming `hurt_health_fraction`.
  - `life_value` and the rest: the teleport case (abilities.cc:111) was missing.
  - `heal_trip_fraction` said "below this health" where it means a share of max health.
- Rewrote the siege block's run-on comment so it says which constant does what, as `siege_ready` (siege.cc:97-110) computes them. The pool is the team's *max* health, and the health check is skipped while the enemy is in reach.
- Noted the two compile-time constraints other files rely on: `pursuit_steps <= 3` (safety.cc:2240, 2-bit packing), and the value constants' residues mod 15 (turn_order.cc:85).

## Considered, not changed

- **Renaming constants** (e.g. `max_wait` to `camp_return_wait`, `big_holders` to `max_holders`). Other files use these names, so a rename would cross files; the comments now carry the meaning.
- **Merging `camp_risk` and `recall_health_fraction`.** They mean different things (a damage weight and a health line) and are equal only by chance.
- **Deriving `brake_bag` and `chain_bag_limit` from the tribute rule** (`ceil(gems/10)`). Possible, but they are tuning knobs, not exact rules. The comment records why `brake_bag` is 11.
- **Moving the static_asserts here.** They test values against layouts private to safety.cc and turn_order.cc, so they belong there.

## Suggestions

1. **attack_target's kill worth ignores the bag** (combat/self_abilities.cc:224). `worth` scores a kill as `s.health + life_value`, with no `gem_value * pair_gems`. Everywhere else (abilities.cc:91 `hit_worth`, plan.cc, turn_order.cc:265) a kill includes the bag. So reset-and-attack and Varg splash target choice will not prefer finishing a gem carrier over an empty-handed body of similar health. Chip damage also uses raw `useful_damage` rather than the `kill_distance` curve that the rest of the combat valuation uses. Fix: add the bag (cheap; `pair_gems` needs the belief, which `Seen` would have to carry), or use `kill_distance`. Severity: low to medium. Effort: small.
2. **`track_horizon` is a fixed 10 rounds** (world.cc:1949; capture.cc:137,155). "Could be anywhere" really depends on map size and on how fast the champion moves (dash champions grow `possible` faster). On a 100x100 map, 10 rounds of walking covers a 21x21 square, nowhere near the whole map. An exact test: stop tracking once `possible` covers the reachable map, or bound the work per belief rather than by rounds. Severity: low to medium (vision and pressure judgments go blind early on big maps). Effort: medium.
3. **One `recall_health_fraction` for every champion** (fight.cc:182, farm.cc:273, support.cc:146/415, shop.cc:197/213, draft.cc:145). Heart of Ruin deals up to +50% damage at low health and has a self-shield, so its best recall line is lower. Glass bodies (Prism 700, Stellar 650, Cassi 600) are at 0.35 x 700 = 245, which an Elk plus a ranged champion's spell can take in two rounds. A per-champion line, or one in effective hit counts (health against the strongest credible hit), would fit every draft. Severity: medium (judgement-heavy, needs A/B). Effort: medium.
4. **Shields don't count in health thresholds.** `hurt_health_fraction` is checked against raw health (fight.cc:194, fight.cc:270, guard.cc:79 `pz.health`, capture.cc:139). A Varg (2.5 x Focus shield) or Heart of Ruin with a shield up reads as hurt and retreats or skips chases it could take. The check could use health plus live shield, as `finishing_camp` already does (camps.cc:517, `my_health_and_shield`). Severity: low. Effort: small, but changes behaviour, so it needs an A/B.
5. **`siege_ready` uses the team's max health** (siege.cc:105-109). A half-dead team commits to a Monolith as readily as a fresh one. Unseen allies' current health is unknown (personal vision), but the last-seen health, or one's own current health for self, is available. Severity: low. Effort: small.
6. **`kite` measures with a straight-line distance** (siege.cc:430). `steps = dist(here, centre)` is a Chebyshev distance, compared against `wait` with `kite_early`. Elsewhere (`siege_candidate`, farm) path steps are used, so behind walls it sets out too early or picks the wrong group. Severity: low. Effort: small (`map.ally_steps` or a pathing field).
7. **`holders` ignores the Tribute emblem** (capture.cc:60, `tribute_turns(..., false)`). A Tribute-emblem holder's shorter channel could allow fewer holders. Severity: low. Effort: small.
8. **The gold-farmer test is written twice**, differently: draft.cc:148 (Cassi by type, `team_size() == 3`) and farm.cc:297 (`linked_pair && !melee`, `economy_three`). A shared `gold_farmer(type, map)` helper would stop them drifting. Severity: low. Effort: small.
