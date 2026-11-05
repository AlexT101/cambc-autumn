# Removing fuel gates

> Out of date since CHANGES 359 (the work veto is gone) and fuel campaigns 5-6. The current plan, from the
> 2026-11-05 census, is [GATE-PLACEMENT.md](GATE-PLACEMENT.md).

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
4. **The out-of-fuel recovery stays** (`is_stale`, `StaleTurn`, the resume in main.cc) as a crash guard. Target: zero
   out-of-fuel turns.

Since every gate passes at 100M fuel, **astraeus at 100M fuel is the gate-free bot** (apart from the untagged
dependences below). So the bench at 100M shows which turns a gate-free bot would run out on: every turn above 100k.

Every gate removal so far was level at 100M but multiplied out-of-fuel turns (EXPERIMENTS Fuel): the gates are the
turn's last brakes, firing on turns the fight steps have already drained. Remove each only once the work it guards is
cheap enough, one at a time with an A/B and `oof.py`.

Retest after CHANGES 217's late finish ended the shared-gem livelocks (fuel round 3, 2026-10-29; real budget against
m2, out-of-fuel turns on the wide set / OOF set / OOF set without shared-gem maps, m2 666 / 2423 / 1178): all gates
removed gave 6.0x / 4.1x / 4.4x and won 11 of the OOF set's 32 games against 17. The gates are real brakes even
without livelocks: removing one moves the shortfall to the next. Per gate, in the table's Plan column.

## Remaining gates

Tagged (`note_shortcut`), roughly most frequent first on the wide bench. Percentages are out-of-fuel turns with the
gate removed in the round-3 retest (wide / OOF set / OOF set without shared-gem maps).

Fuel campaign 3 (2026-11-01, fuel-campaign-3/NOTES.md) removed no gate: it made the guarded work cheaper, so every
gate fires less. Firings per bot in the 10,240-game real-budget A/B on fresh-11000..11019, fc3b (4a7c25f6) -> the
campaign's final bot (CHANGES 268): farm-partial-evaluation 2,601,718 -> 1,766,494, step-guard-entry 295,700 ->
275,834, comms-stale-vision 280,121 -> 182,349, turn-order 224,421 -> 141,268, farm-no-route 107,731 -> 57,462,
prey-cut-short 81,505 -> 77,458, ward-no-bushes-clusters 76,605 -> 56,280, crow-flies-farm 69,455 -> 66,038.

Fuel campaign 4 (2026-11-03, fuel-campaign-4/NOTES.md "Fuel gates") removed none either: plain removals still raised
OOF 6-46% (comms-stale-vision +8%, turn-order +46%, ward-no-bushes-clusters +7%, static-descend +6%, farm-no-route
+9%). It lowered three reserves to the measured cost of what they guard, each level on OOF in a 10k A/B against fc4b:
comms-stale-vision 493k -> 88k, ward-no-bushes-clusters 69k -> 47k, step-guard-entry 471k -> 432k (its estimate now
decays on a cut).

| Gate | Where | What it guards | Plan |
|---|---|---|---|
| step-guard-entry, -sim, -look + `costliest` | `step_guard` (built on first need, CHANGES 110; in the strike search only once a tile it may cover counts, 189; routes skip it when it cannot change them, 215) | up to 25 simulations; narrowing it (CHANGES 176) lost on out-of-fuel turns | measured limit; unsimulated tiles guarded iff `safety.lethal(q)`; needs cheaper sims. Removed: +143 / +95 / +122%. Campaign 4: `costliest` decays on an entry cut too (entry -8%, look +23%, OOF level); entry without `fight_cost_estimate` +3.9% OOF (placings cost 5.2k median, 19k p99) |
| prey-cut-short | `prey` | up to 8 simulations, best candidate first; narrowing it (CHANGES 176) lost on out-of-fuel turns | measured limit; needs cheaper sims. Removed: +55 / +68 / +72% |
| farm-partial-evaluation | `farm` | the camp evaluation loop | always evaluate, once the loop on many-group maps is cheap (TODO 1: banking turns have no bound; 60-80 groups at 300-900 each). Removed: +90% wide. Campaign 4 (CHANGES 298): the reserve adds 12k for a travel plan when the dash is ready; firings +17%, OOF -30% |
| comms-stale-vision | `comms::send` / main.cc | `World::observe` after moving | campaign 4: reserve 10k -> 5k (`refresh_floor`; observe 1.2k median, 4.3k p99.9, 7.2k max): firings -82%, OOF level; at 3.5k +1.1% OOF, removed +8%. Always observe (~0.75-1.9k). Removed: +26 / +14 / -7%. Retried 2026-10-31 (campaign 2 round 4): wide -13% / OOF set -6% on the small benches, but in the 1164-game A/B against m3 it carried about half of a +25% out-of-fuel rise, nearly all in rounds 1-10; kept |
| ward-no-bushes-clusters | `ward_bushes` | cluster growth (`find_bush_clusters`' floor) | ward-no-bushes-fuel, the first check, is gone (CHANGES 250): A/Bs level with it gone. The turns it stopped now reach this one (A/B 2905 -> 3014 firings). Campaign 4: floor 15k -> 5k, firings -32%, OOF level; unbounded +7% OOF (rounds 1-2 growth up to 92k on blob maps: the whole map's run labelling) |
| turn-order | `set_turn_order` | 10k reserve for a small bounded pass; 6k on a quiet turn (no enemy in sight, not a healer, no channel ending, not round 1: CHANGES 307, firings -41%, OOF level or lower, comms-stale-vision +20%) | campaign 4: removed +46% OOF, 7.5k +0.7% (firings -44%); costly calls are offer_kills, offer_escape, may_escape. Removed: +81 / +45 / +33% (+13% alone before). The tail is the offers, not `find_members` (~4% of its calls start here): `offer_escape`'s `threats_at` Reaches 9-14.5k, `offer_kills` up to 10k, `offer_heal` 5-11.5k, `may_escape` 2-4.7k. Bound those first. A quiet call costs 0.6k median, p99.99 6.7k (`find_members` built late is its tail) |
| farm-no-route | `farm` | routes capped at steps + 16 | removed: +18 / -12 / -5%; removed again 2026-10-31 (campaign 2 round 4): level on the small benches, but about half of the A/B's +25% out-of-fuel rise against m3, rounds 1-10; kept. Needs the opening turns' route search bounded first |
| farm-kept-target, crow-flies-farm | `farm` / `walk_on` | approach fields | fixed (CHANGES 250): with the approach skipped for fuel, the choice stands and descends its cached `from_centre` field, else last turn's approach without rewriting claim and crew; crow-flies only when neither exists. A/B firings against fb0: crow-flies-farm 4425 -> 2101, farm-kept-target 1476 -> 466. farm-kept-target also fires at 100M (a no-approach fallback) |
| static-descend | pathing.cc | one route search | remove (removed: +3 / +33 / +15%) |
| siege-route-fuel | `step_towards_funded` | an uncapped route | fixed cap: uncapped (at most one full field, ~26k on 100x100), else 2 x static steps + `max_detour`. Removed: level, but step-guard-entry fired 3231 -> 6081 |
| farm-no-attack-tiles, siege-no-tiles, spell-clear-no-tiles | `prepare_member` | bush-cluster growth inside `viewers` | remove once clusters are on demand |
| out-of-fuel | main.cc | not a gate | keep, count |

Removed (CHANGES 250, 2026-10-31): fight-cut (`simulate` no longer stops at a fuel floor; `trade` lost its
`fuel_floor` argument) and ward-no-bushes-fuel. Both measured level at the real budget alone and together.

Untagged:

- `step_guard` keeps `act_reserve` (20k) before its fights and checks `floor + 1000` a foe before each exact tile look.
- main.cc skips the turn end (`note_turn_end`), comms send and the queue below `late_floor` (1500).
- `step_towards_funded` sets its route cap from fuel left (see siege-route-fuel).
- `fight_cost_estimate`, `query_cost_estimate`, `search_cost_estimate`, `costliest_field/unseen/fight_`,
  `step_guard`'s `costliest`: estimators only gates read; delete them with their gates. `step_guard_costliest()` also
  picks how `Pathing::route` searches (CHANGES 215, between exact computations): keep it for that.
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

- **The end-of-turn queue.** Done (CHANGES 166-167, 169). `TurnEndQueue` (main.cc) runs every spare-fuel cache fill
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
