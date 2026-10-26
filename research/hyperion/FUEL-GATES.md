# Removing fuel gates

Goal: astraeus (and hyperion, which shares every gate below) plays the same in the same game state, whatever fuel is
left. A gate is code that reads `fuel()` and chooses worse when it is short (`note_shortcut`); play then depends on
how much an unrelated earlier step cost, so behaviour is hard to trace and any fuel change reroutes games.

## Rules

1. **Decision code reads no fuel.** Work whose worst case is known just runs.
2. **Repeated work gets a limit set from measurements**, not from fuel: fight simulations and the cold farm
   evaluation. A limit is set so that it almost never binds (target: under 0.5% of calls); where it binds more often,
   make the work cheaper rather than raise the limit. Each limit has a deterministic fallback.
3. **Spare fuel goes to one end-of-turn queue** of precomputation that never changes play: centre, approach, altar
   and spawn fields, attack tiles, bush clusters, Reach static windows and sight masks, next turn's walk. This queue
   holds the only `fuel()` check in play. Every reader of those caches computes what it needs on demand when the
   cache is empty, within its worst case, so the queue changes how much fuel a turn spends, never what it decides.
4. **The out-of-fuel recovery stays** (`is_stale`, `StaleTurn`, the resume in main.cpp) as a crash guard. Target: zero
   out-of-fuel turns.

Since every gate passes at 100M fuel, **astraeus at 100M fuel is the gate-free bot** (apart from the untagged
dependences below). So the bench at 100M shows which turns a gate-free bot would run out on: every turn above 100k.

Every gate removal so far was level at 100M but multiplied out-of-fuel turns (EXPERIMENTS Fuel): the gates are the
turn's last brakes, firing on turns the fight steps have already drained. Remove each only once the work it guards is
cheap enough, one at a time with an A/B and `oof.py`.

## Remaining gates

Tagged (`note_shortcut`), roughly most frequent first on the wide bench:

| Gate | Where | What it guards | Plan |
|---|---|---|---|
| step-guard (3 sites) + `costliest` | `step_guard` (built on first need, CHANGES 110) | up to 25 simulations | measured limit; unsimulated tiles guarded iff `safety.lethal(q)`; needs cheaper sims |
| prey-cut-short | `prey` | up to 8 simulations, best candidate first | measured limit; needs cheaper sims |
| farm-partial-evaluation | `farm` | the camp evaluation loop | always evaluate, once the loop on many-group maps is cheap (TODO 1) |
| comms-stale-vision | `comms::send` / main.cpp | `World::observe` after moving | always observe |
| ward-no-bushes-fuel, ward-no-bushes-clusters | `ward_bushes` | cluster growth | remove once clusters are on demand within bound |
| turn-order | `set_turn_order` | 10k reserve for a small bounded pass | remove (alone it was +13% out-of-fuel turns) |
| farm-no-route, farm-kept-target, crow-flies-farm | `farm` / `walk_on` | routes and approach fields capped at steps + 16 | remove; farm-kept-target also fires at 100M (a no-approach fallback) |
| static-descend | pathing.cpp | one route search | remove |
| siege-route-fuel | `step_towards_funded` | an uncapped route | fixed cap: uncapped (at most one full field, ~26k on 100x100), else 2 x static steps + `max_detour` |
| farm-no-attack-tiles, siege-no-tiles, spell-clear-no-tiles | `prepare_member` | bush-cluster growth inside `viewers` | remove once clusters are on demand |
| fight-cut | `simulate` | one simulation | remove (almost never fires) |
| out-of-fuel | main.cpp | not a gate | keep, count |

Untagged:

- `step_guard` keeps `act_reserve` (20k) before its fights and checks `floor + 1000` a foe before each exact tile look.
- main.cpp skips the turn end (`note_turn_end`), comms send and prepare below `late_floor` (1500), and warm reach below
  `end_reserve + 8000`.
- `step_towards_funded` sets its route cap from fuel left (see siege-route-fuel).
- `prepare_walk` before the decision with `walk_first_floor` (40k). Dropping it is not exact (the approach field is
  searched out to our tile, EXPERIMENTS Fuel): move it into the queue, so it runs at the end of the turn before.
- `fight_cost_estimate`, `query_cost_estimate`, `search_cost_estimate`, `costliest_field/unseen/fight_`,
  `step_guard`'s `costliest`: estimators only gates read; delete them with their gates.
- Done (CHANGES 166): reads of what the warm-up had made. `note_upkeep`'s and `kite_productive_action`'s
  `from_ally_spawn_ready()`, farm's heal trip by Chebyshev distance without a centre field, `approach_steps`' centre
  field and spawn sum, the crow-flies farm walk after a failed search, `steps_warm` and `FarmContext::warm`, group
  hops (-1 until the warm-up), and the turn-start ward and `ward_bushes` reading only found bush clusters. With the
  warm-up off, replays at 100M are byte-identical to it on. Approach readiness (`goal_field`, Willow's
  `work_route`, farm-kept-target) still depends on `prepare_walk` having run.

Fuel reads that do not change play stay: the warm-up and cache fills (to move into the queue), the draft bot's
`analyse`, and debug output (`FuelMeter`, inside `debug_block`).

## Remaining phases

Each is its own commit and A/B.

- **The end-of-turn queue.** Half done. CHANGES 109's `TableQueue` (main.cpp) fills the terrain-only tables a fight
  reads (Reach static windows, sight masks, the search's viewer rows) around visible enemies, then around us, bounded
  by the fuel spent this turn so it fills the same at any budget. Still separate, each with its own `fuel_ok` floor and
  run in this order before it: `prepare_next_turn` (next turn's walk, the farm loop's order, the altar walk),
  `warm_reach` (now a subset of the queue's work), and the warm-up (`warm_centres`, `StaticMap::warm_up`,
  `Pathing::warm_up`, `find_all_bush_clusters`: centre, our spawn and altar fields, group and attack tiles, hop fields,
  bush clusters). Fold them into the one queue in a fixed priority order. Their readers no longer depend on what
  they made (CHANGES 166): with all four off, 52/52 replays at 100M are byte-identical. Check after the fold: with
  the queue off, replays at 100M are byte-identical to it on.
- **Fight simulations.** step-guard and prey-cut-short get measured limits with their fallbacks, after the sims are
  cheaper (TODO 2).
- **Farm.** Always evaluate; if a cold evaluation plus a fight turn can exceed 100k, build the first centre fields
  in the champion's first turn (200k) rather than add a limit.
- **End of turn.** `comms::send` always re-reads vision after moving; `set_turn_order` and `ward_bushes` lose their
  gates.
- **Clean-up.** Delete `fuel_ok`, `end_reserve`, `last_reserve`, `walk_first_floor`, the estimators and
  `note_shortcut`'s callers; keep the out-of-fuel counter. `grep fuel bots/astraeus/src` should then show only the
  queue, the draft, `FuelMeter` and debug output. Update AGENTS.md's Fuel section and the bench docstring.

## Done when

- No turn above ~95k at 100M fuel on ladder and `maps/gen`.
- Out-of-fuel turns at the real budget no higher than the frozen baseline's, counted with `tools/fuel/oof.py` on a
  full A/B.
- Level or better against the frozen baseline, so 100M and real-budget games agree.
