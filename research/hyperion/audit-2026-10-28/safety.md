# Audit: safety (`bots/astraeus/src/model/safety.cc`, `safety.h`)

## Changed

### Cleanup (commit "astraeus audit (safety): cleanup"): byte-identical, 8/8 bench replays
Total fuel 2,211,802,776 -> 2,211,720,334 (-0.004%), within noise.
- `make_kit`: works out damage and heal first and makes `value` their sum plus a stun's worth. The float sums are in the same order. Notes that Heart of Ruin's passive scales damage, not its shield.
- `link_bodies()`: one helper for the Cassi/Issac link that `Side::add` and `fill` both duplicated.
- `acts_from(e)`: one helper for the four copies of "the teleport destination if one is pending, else the position" (`approach`, `credible_enemy_may_hit_within`, `walk_allies_in`).
- `threats_at`: `top = min(radius, reach)` was always `radius`, because `unseen_radius` already clamps to the reach. Dropped it.
- Removed `join_allies` (unused) and a redundant close and reopen of the anonymous namespace.
- Comments:
  - `hit_strength`/`hit_focus` also carry Skirmish and Collectors (`scale` includes `dealt`), not only Heart of Ruin.
  - `fight_horizon` no longer carries measurement figures.
  - The `Cap` doc comment sat on `rounded_up`; it is now on `Cap`.
  - `trade()`'s "only the order where they strike first" was stale: `stand()` passes `they_first=false`.
  - Header: `fight()` named a nonexistent `Trade::cut`.
  - Header: `threatened()` said it returns a chance, but it returns a bool against `recall_risk`.

### Fixes (commit "astraeus audit (safety): fixes"): a pending enemy teleport used inconsistently
`blow()`, `approach()` and `credible_enemy_may_hit_within()` place a teleporting visible enemy at `tp_dest`, using its Strike from there. Some code still measured from `e.pos`:
- **Prefilters:** `late()`, `stand()` and `turns_to_kill_idle()` prefiltered with `dist(p, e.pos) - reach`. They could drop an enemy that `approach()` would bring into the fight from its destination.
- **`avoid_within()`:** checked a visible enemy against `e.pos`.
- **`enemy_area()`:** drew the square around `e.pos` with the Reach radius, built at `e.pos`.

All of these now use `acts_from(e)`. `enemy_area` draws `strike.reach` around the destination, as `blow()` does. These games have no teleports, so the bench stayed identical (8/8 replays). Total fuel rose 0.02% against the baseline (+0.017% over the cleanup), from the extra `teleport_pending` checks.

## Considered, not changed
- **A generic "each live enemy" iterator** for the seven `live_enemies()`/`gone()` loops. Several loops return early from the member function, so a lambda would hurt readability and could change inlining.
- **`fill` vs `Side::add`.** `fill` keeps its counts in locals for fuel, so I only shared the link step.
- **The redundant-looking `out - 1 < reach` in `find_members`.** It is implied by the second test, but it short-circuits `first(o)`, which costs host slot reads.
- **`bound().threat` vs `threatened()`.**
  - `bound()` gates an unseen enemy on `any_within(possible, p, reach)`.
  - `threatened()` gates on its field, which is capped at `unseen_radius` (no more than the reach).
  - So `bound().threat` can be true where `threatened()` is false, although the header says they are the same. The gap is small: past the radius the chance is below about 0.5, and one threat needs a chance of at least 0.8 to reach `recall_risk`. Two such threats can combine to cross it. Left alone as a judgement call; aligning it costs one `any_within` per unseen threat.

## Suggestions

1. **The two-turn widening misses dash-first plans, so Strike is not an upper bound** (`safety.cc` `threat_strike`, about line 905; `Reach::build_ways` turn loop). High severity, moderate effort.
   - **What it models:** `widened[d] = max(s2.at(d-1), s.at(d) + (d <= basic+walk ? s : 0))`. On the first of two turns the enemy only walks one step, or adds a second basic only within plain basic reach.
   - **What it misses:** a dash on turn 1, then a strike on turn 2 from the landing.
   - **Vendetta** (70 Strength, reset and dash both ready), at d = 3 to 4: turn 1 walk + dash + attack, turn 2 reset + 2 attacks gives 3s (210). The model gives s (70) at d = 4 and 2s at d = 3.
   - **Vesper** at d = 5: dash + attack, then reset + 2 attacks gives 3s. The model gives s.
   - **Who it hits:** every dash champion (Vesper, Vendetta, Ren, Issac, Heart of Ruin), whenever the enemy has two turns before ours, which is common.
   - **Reach** has the same gap (turn-2 ways start only from walked sets), so the REACH-BOUND debug check stays silent.
   - **Fix:** for d in the dash band, add the second turn's best from within basic reach of the target. Exactly: max over turn-1 moves (walk, or dash + walk) of turn-1 damage plus `s2` without the dash slot at the remaining distance.
   - `most_damage` (`k.at(0) + hs`) happens to still bound it.
   - Any fix changes threat levels everywhere, so it needs an A/B.
2. **Camps we wake this turn are not seen after `refresh()`** (`Safety::refresh`, `find_members`). Medium severity, small to medium effort.
   - `find_members` walks `world.each_stirring()`, which is alive and not asleep as of `observe()`.
   - When we hit or stun a member of an asleep group, rules `camps.wake` wake the whole group. `refresh()` only checks deaths and stuns, so `camp_damage`, `camp_area` and `lethal` keep treating the group as asleep for the rest of our turn (guard steps after attacking, melee walk after attack).
   - **Fix:** World (or the attack path) records the groups we damaged this turn, and `refresh()` treats them as stirring and re-runs `find_members`.
   - The fix lives in World and the attack code, not here.
3. **`find_members` lets champions who have not acted shield us at their current tiles** (`safety.cc` about lines 1750-1755). Medium severity, small effort.
   - A member's reach toward us is cut to `d - first(o)` by any visible champion nearer the monster.
   - Champions yet to act this round (`!acted`) can walk or dash away before the next camp phase, leaving us the nearest.
   - **Sound version:** count `o` only if it has acted, or use `d + its move` (1, or 3 with a ready dash) for unacted ones.
   - This under-states camp danger next to allies or enemies.
4. **Heart of Ruin's passive is frozen in fights** (`make_fighter`: `strength = c.strength * c.scale`). Low to medium severity, small effort.
   - The Trade sim keeps its Strength and Focus at their starting scale. In reality it grows to +50% as it loses health, so fights against or with Heart of Ruin understate its late damage.
   - **Fix:** a per-fighter `missing_bonus`, applied in `act()` when `max_health > 0`. It is off the plain path anyway, because Heart of Ruin's shield makes its kit not plain.
5. **Existing fuel gate in `trade()`.** Low severity, medium effort.
   - With `fuel_floor = end_reserve`, `simulate` returns {-1, -1} and the fight reads as lost and as our fall ("fight-cut").
   - The sim is already bounded (`fight_horizon`, quiet-turn fast paths). A hard cap on the work per fight (half-turns times fighters) would let us drop the floor rather than choose worse.
6. **Turn-scoped static caches in `fighting_allies()` and `Reach::build` go stale** (they are keyed on `world.round`). Low severity, small effort.
   - After `see_again()` (we moved and see new allies), allies who just came into sight are not in fights or Reach blockers until next round.
   - **Fix:** key them on a World observe counter instead.
7. **`engagement_near()` measures the enemy strike from `e.pos`** (`safety.cc` about line 882). Low severity, small effort.
   - For a teleporting enemy the strike applies from `tp_dest`.
   - It is left alone because our own reach to it is correctly from `e.pos`. The fix would split the two distances.
8. **Unseen weight is heuristic** (`unseen_weight`, `unseen_radius`). Low severity, medium effort.
   - **Ignores map edges:** `(2r+1)^2 / tiles` counts window tiles off the map.
   - **Approximate radius:** `unseen_radius` approximates where the true chance `count_within(possible, p, reach) / tiles` crosses `credible_weight`.
   - **Exact alternative:** `field.compute` already gives distances. One `count_within` at the radius boundary tiles, or a box-sum over a `possible` prefix table, would place the cut exactly, at a cost comparable to the field.
9. **Varg's splash and the fights.** Low severity, a modelling note.
   - Trade focuses all damage on the weakest member, so Varg's splash onto a second adjacent body (rules `varg.passive`) and our own splash are ignored.
   - With items, these are the main things the sim leaves out, along with positioning.
