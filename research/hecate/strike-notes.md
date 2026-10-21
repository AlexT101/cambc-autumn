# Strike search: handoff notes

Phase 1 (search core) on branch `orch/strike-p1`. Spec: [STRIKE-SEARCH.md](STRIKE-SEARCH.md).

## What exists (plan.cpp)

- `plan_strikes` = `Search::read` -> `grow` (DFS) -> pricing -> execution. The old fixed menu is gone; it survives
  only as `menu_shape()` (a filter over the debug enumerator) for the dominance check.
- **Grid.** Moves end within 3 of the start: a 7x7 bitboard in a `uint64` (`Grid`, bit (y+3)*7+x+3). `free_`
  (walk/land: `pathing.blocked()` | guard), `pass_` (dash path: not wall or visible camp), `landings(c)` by dilation.
- **Legality per unit** as grids: `Unit::legal` (basic attack, range + sight), `cast_legal` (unit casts, range 4).
  Sight is `attack_viewers()` (new, safety.cpp): exact, except viewers in a bush beyond a step are dropped
  (conservative). Our ward's sight is not used (an option lost, never a refused attack).
- **DFS over symbolic moves.** Walk (W) and plain dashes (D) are not expanded per tile: each attack/cast after a
  move ANDs its legality grid into the move's requirement (`req_w`, `req_d`, `req_e`), and `settle()` resolves every
  end tile a leaf can reach (segments `at_start, walked, dashed, walked_dashed, dashed_walked`). Landings that hit
  (Heart of Ruin, `land_hits`) are expanded concretely. Ground casts: excluding-walking only, from the start, best
  centre per set of foes damaged (exact: nothing can move after).
- **Actions/rules covered:** W, A, R, D, S (unit and ground), Cassi's stun anywhere, melee W A R A and every W
  interleaving, ranged W R A, A then D (Vesper), A W D / A D W, attack + cast in both orders (cast priced on health
  after the attack), Marcella's armed attack stun (`arms`), Vendetta's kill refresh (reset and dash ready again,
  the cast spent refunded via `pending`; one cast a turn still holds), Varg splash both ways, camps as targets only
  for Vendetta (killable) and Varg (splash onto a foe).
- **Wake pricing** (`wake`, `find_wakers`): touched groups' sleeping strikers target the nearest of us at E, visible
  allies, enemies held in place (acted or channelling); bans: sleeping Monolith member, ally recalling/tributing/
  on a cleared camp tile, a lethal woken hit. Landing-stunned members skip. Memoised per end tile (`wake_at`).
- **Leaf score** = today's: hits (`hit_worth`, stun_worth) - cast 40 / dash 2*step / reset 0 + shield_worth(start)
  if the cast is unused + step if the walk is unused; then + progress - camps - 0.25 x Reach blow (HoR foes scaled by
  their new damage_scale) - unseen threats (`threats_at`) for end tiles 2+ away.
- **Pricing:** tiles picked by bound (raw + progress), camps subtracted when picked, foes priced largest Strike
  share first and cut once the tile cannot win. `max_exact_queries` is uncapped (`1 << 30`). Distance-3 winners
  must pass `Safety::lethal`.
- **Execution:** the chosen leaf's concrete sequence (`Search::concrete`). A walk/dash refused by a hidden unit
  takes the best priced leaf with the same executed prefix that avoids that tile; else `strike_enemy`.
  `Pathing::try_move` gained a `refused` out-param to tell hidden blockers from errors.
- Removed: `enemy_cast_value`/`cast_chosen` (abilities.cpp); `strike_after` now re-asks `cast_at_enemies` when
  the search valued a cast from the start tile and we are still there.

## Debug checks (all in debug_block, `debug_search`)

- `SRCH-EXH`: `exhaust()` enumerates every sequence on concrete tiles (no grouping) each strike turn; per end tile
  its best raw value must equal the search's. `SRCH-DOM`: the old menu's best, scored the same way (search's danger
  at priced tiles, camps only at unpriced ones), must not beat the choice. `SRCH-REFUSED`: an action that threw or
  was refused other than by a hidden unit. Debug code reuses the search's grids and
  never touches Safety, Pathing or sight caches, so the game stays byte-identical to release.
- Result on 6 validation games (hecate vs hecate-v7: 00packs, gen-huge-shared-720707800, gen-monolith-720700901,
  both sides) plus ~10 single packs games while optimising: 0 EXH, 0 DOM; REFUSED 0 in the last builds (3 seen
  earlier, before belief health replaced live reads; recheck).
- `SRCH r handle fuel .. read .. grow .. price .. act ..` per call. Summariser used: a ~40-line script reading
  `team-*.stdout` from the replay zips (not committed; trivial to redo).

## Fuel (the blocker)

- 6 validation games, before the wake memo: per search mean 18.4k, p50 9.0k, p90 52.6k, max 60.8k (read 6.2k,
  grow 20.6k, price 8.2k mean); **58 out-of-fuel turns vs 0 for hecate-v7** (oof.py), 45 of them on 00packs
  (Heart of Ruin landings near wolf packs). Old planner: 6k mean, 25k max. Not ready for an A/B.
- Fuel is ~1 per WASM instruction and 1 per byte copied: Node is 64 bytes (bitfields), legality is pre-checked
  before a child is copied, `Tables` are static (no per-turn zeroing), offers store a leaf index, not a sequence.
- Remaining costs, largest first: (1) HoR dash leaves: each concrete hitting landing x attack order x end tiles,
  with wake pricing per (leaf, E) (memo added last, unmeasured); (2) fixed pricing cost ~3-8k even with 1 tile
  (strike_of/awake_members/goal_field/field reads per tile - measure which); (3) read ~5k (geometry boards,
  groups_near, sight windows, damage_amount reads).
- Ideas: process leaves in falling value so each end tile is offered once when no wake applies; group HoR landing
  leaves per landing tile; read field values only for tiles that can still win; share `blocked()`/sight with
  step_guard. Then set `max_exact_queries` (queries were small: mean 2.8, max 19).

## Gotchas

- Window (9x9, safety.cpp) vs Grid (7x7, plan.cpp) layouts differ; `to_grid` converts row by row.
- `hit_unit` mutates `h` before it can fail: callers restore `h = saved`.
- `land_hits` marks landings within the radius of a foe or a live camp member; other landings are "plain" and
  stay symbolic. A Vendetta refresh enables D only when `moves` and a dash slot exist.
- Not done: the probe that no second cast is allowed after a Vendetta refresh (modelled per the YAML: one cast);
  the Strike-equals-Reach shortcut; stunned/capture-holding enemies as "fixed" wake targets (acted/channelling only).

## Next phase needs

Fuel first (back under the old planner's OOF count on the A/B maps), then the phase 1 A/B, then phase 2 (heal and
shield as leaf options; `shield_value` is today's start-tile shield_worth).
