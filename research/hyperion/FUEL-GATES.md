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
| step-guard-entry, -sim, -look + `costliest` | `step_guard` (built on first need, CHANGES 110; in the strike search only once a tile it may cover counts, 189) | up to 25 simulations; narrowing it (CHANGES 176) lost on out-of-fuel turns | measured limit; unsimulated tiles guarded iff `safety.lethal(q)`; needs cheaper sims |
| prey-cut-short | `prey` | up to 8 simulations, best candidate first; narrowing it (CHANGES 176) lost on out-of-fuel turns | measured limit; needs cheaper sims |
| farm-partial-evaluation | `farm` | the camp evaluation loop | always evaluate, once the loop on many-group maps is cheap (TODO 1; CHANGES 175 bounds it but for banking turns) |
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
- main.cpp skips the turn end (`note_turn_end`), comms send and the queue below `late_floor` (1500).
- `step_towards_funded` sets its route cap from fuel left (see siege-route-fuel).
- `fight_cost_estimate`, `query_cost_estimate`, `search_cost_estimate`, `costliest_field/unseen/fight_`,
  `step_guard`'s `costliest`: estimators only gates read; delete them with their gates.
- Done (CHANGES 166): reads of what the warm-up had made. `note_upkeep`'s and `kite_productive_action`'s
  `from_ally_spawn_ready()`, farm's heal trip by Chebyshev distance without a centre field, `approach_steps`' centre
  field and spawn sum, the crow-flies farm walk after a failed search, `steps_warm` and `FarmContext::warm`, group
  hops (-1 until the warm-up), and the turn-start ward and `ward_bushes` reading only found bush clusters. With the
  warm-up off, replays at 100M are byte-identical to it on. CHANGES 168 took the cost back out of the second
  turn: upkeep's spawn steps are folded in only when damage makes them count, group hops follow a timetable (one a
  turn, read only on schedule), and the turn-start ward is only a planned one.
- Done (CHANGES 167): `prepare_walk`'s `walk_first_floor` (40k) before the decision. The walk to the farm choice is
  searched at every turn's start (dropping it is not exact: the approach field is searched out to our tile, and
  `goal_field`, Willow's `work_route` and farm-kept-target read whether it is ready); the queue usually made it at
  the turn end before. `warm_reach` and its floor are gone.

Fuel reads that do not change play stay: the end-of-turn queue (`TurnEndQueue` and the fills it calls), the draft bot's
`analyse`, and debug output (`FuelMeter`, inside `debug_block`).

## Remaining phases

Each is its own commit and A/B.

- **The end-of-turn queue.** Done (CHANGES 166-167, 169). `TurnEndQueue` (main.cpp) runs every spare-fuel cache fill
  in one order: fight tables around visible enemies, next turn's walk (`prepare_next_turn`), the map warm-up (spawn
  field, group hops), centre, altar and hop fields, attack tiles and bush clusters, then tables around us. Its floor
  rises by the turn's fuel above the real budget, so it fills the same at 100M. Every reader makes what it needs
  when the cache is missing: with the queue off, the 52 wide-bench replays at 100M are byte-identical to it on.
  The fills keep their own `fuel_ok` checks against the floor the queue passes.
- **Fight simulations.** step-guard and prey-cut-short get measured limits with their fallbacks, after the sims are
  cheaper (TODO 2).
- **Farm.** Always evaluate; if a cold evaluation plus a fight turn can exceed 100k, build the first centre fields
  in the champion's first turn (200k) rather than add a limit.
- **End of turn.** `comms::send` always re-reads vision after moving; `set_turn_order` and `ward_bushes` lose their
  gates.
- **Clean-up.** Delete `fuel_ok`, `end_reserve`, `last_reserve`, the estimators and
  `note_shortcut`'s callers; keep the out-of-fuel counter. `grep fuel bots/astraeus/src` should then show only the
  queue, the draft, `FuelMeter` and debug output. Update AGENTS.md's Fuel section and the bench docstring.

## Done when

- No turn above ~95k at 100M fuel on ladder and `maps/gen`.
- Out-of-fuel turns at the real budget no higher than the frozen baseline's, counted with `tools/fuel/oof.py` on a
  full A/B.
- Level or better against the frozen baseline, so 100M and real-budget games agree.
