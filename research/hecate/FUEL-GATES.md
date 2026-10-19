# hecate: removing fuel gates

Goal: hecate plays the same in the same game state, whatever fuel is left. Today about 25 places read `fuel()` and
choose worse when it is short (`note_shortcut`), and a few more let fuel set a search depth or a cache's timing without
a tag. Play then depends on how much an unrelated earlier step cost, so behaviour is hard to trace and any fuel change
reroutes games.

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

Since every gate passes at 100M fuel, **hecate at 100M fuel is the gate-free bot** (apart from the fuel-derived values
listed below). So the bench at 100M already shows which turns a gate-free hecate would run out on: every turn above
100k. After the work, a game at 100M and at the real budget play identically as long as no turn exceeds 100k.

## Inventory

Tagged gates (`note_shortcut`) and where each goes:

| Gate | Where | What it guards | Fate | Phase |
|---|---|---|---|---|
| fight-cut | `simulate` (safety.cpp) | one simulation (24 turns a side, 6 fighters a team) | remove | 3 |
| home-no-fight-sim, home-no-pursuit | `want_home` | 2 simulations; the estimate asks up to ~96k in big fights | remove; these always run | 3 |
| step-guard (2 sites) + `static costliest` | `step_guard` | up to 25 simulations | measured limit; unsimulated tiles guarded iff `safety.lethal(q)` | 3 |
| prey-cut-short | `prey` | up to 8 simulations, best candidate first | measured limit | 3 |
| enemy-cast, camp-cast | abilities.cpp | cast search: estimate 12k+, real ~1.5k mean, 14k max | remove | 1 |
| turn-order | `set_turn_order` | 10k reserve for a small bounded pass | remove | 1 |
| travel-dash | `dash_towards` | one search | remove (keep `failed_search_pause`) | 1 |
| static-descend, route-retry | pathing.cpp | one route search; up to 3 on hidden blockers | remove (retries stay at 3) | 1 |
| crow-flies-kite (2 sites) | `kite` | an approach field, then routes | remove | 1 |
| farm-no-route, farm-kept-target, crow-flies-farm | `farm` / `walk_on` | routes and approach fields capped at steps + 16 | remove | 1 |
| farm-no-attack-tiles, siege-no-tiles, spell-clear-no-tiles | `prepare_member` | bush-cluster growth inside `viewers` | remove once clusters are on demand within bound | 2 |
| ward-no-bushes-fuel, ward-no-bushes-clusters | `ward_bushes` | cluster growth | remove | 2 |
| siege-route-fuel | `step_towards_funded` | an uncapped route | remove; fixed cap (see below) | 2 |
| farm-no-evaluation (-cold), farm-partial-evaluation | `farm` | the camp evaluation; the mini-farm fallback walks to the nearest group | always evaluate; delete the mini-farm | 4 |
| comms-stale-vision | `comms::send` / main.cpp | `World::observe` after moving | always observe | 5 |
| out-of-fuel | main.cpp | not a gate | keep, count | — |

Gates without a tag, added by fuel round 3 (hecate-v5): `step_guard` keeps `act_reserve` (20k) before its fights and
checks `floor + 1000` a foe before each exact tile look; main.cpp skips the turn end (`note_turn_end`), comms send and
prepare below `late_floor` (1500), and warm reach below `end_reserve + 8000`. They go with phase 3 (step_guard) and
phase 2/5 (main.cpp).

Untagged fuel dependences:

- `farm` weights groups by `home_ground` only once `pathing.centres_ready()` (bot.cpp, `weight = ... ? known.home :
  1.0f`). Warm-up finishes on leftover fuel (19-54 rounds on 100x100), so early camp choice depends on fuel. But
  `home_ground` reads only the drafted spawn steps: use it always. (Phase 2, a play change in the opening.)
- `Pathing::approach` sets its depth from fuel left when the distance is unknown (`affordable`): use width + height.
- `step_towards_funded` sets its route cap from fuel left. Use a fixed cap: uncapped (at most one full field, ~26k on
  100x100) unless phase 0 shows that is too dear, then 2 x static steps + `max_detour`. Its per-move fuel check goes.
- `prepare_walk` before the decision with `walk_first_floor` (40k): drop; callers compute on demand, the queue
  prepares it for next turn.
- `farm_evaluation_reserve`, `fight_cost_estimate`, `costliest_field/unseen/fight_`, `step_guard`'s `costliest`:
  estimators only gates read; deleted with them.

Fuel reads that do not change play and stay: the warm-up and cache fills (moved into the queue), the draft bot's
`analyse` (its output is a cache the champions recompute when missing; verify as in phase 2), and debug output
(`log_fight`, `dump_beliefs`, `FuelMeter`, all compiled out or inside `debug_block`).

## Phases

Each phase is its own commit and A/B. Baseline: hecate 4ba1865 (after fuel round 3).

### 0. Measure (no play change)

- Bench current hecate at 100M on the default set, the four largest `maps/gen` maps and the maps where out-of-fuel
  turns concentrate (contest, swirl, corners, pilgrimage), against rival and nemesis-v2. List every turn above 90k with
  its per-phase split (`debug_fuel`).
- Counters inside `debug_block` (free in local builds), each as a distribution with its max:
  - fight simulations per turn and per caller (`want_home`, `step_guard`, `prey`, the planner), and distinct fight
    keys per `step_guard` call;
  - fuel per simulation by fighter count, per Reach build, per `plan_strikes` call;
  - farm evaluation: groups read, fuel per group, from-here field cost by map size;
  - on-demand cost of each cache the queue fills: bush clusters (largest cluster, a cold `ward_bushes`), attack tiles
    per member, approach and centre fields, uncapped siege routes;
  - first-turn cost (start-up plus world init) on 100x100.
- Output: a worst-case budget per step, the limits for phase 3, and the turns that still exceed 100k. Record in
  EXPERIMENTS.md.

Result (2026-10-19, measured on hecate-v4, before fuel round 3; hecate-v5's play turns at 100M are mean 33.8k, p99
92.8k against v4's 41.1k and 108k, so fewer turns are over 90k now). hecate a48e555 = hecate-v4, bench maps at 100M; per-phase meters in a throwaway copy, which add
~3k a turn). Play turns: mean 41.1k, p99 108k. Turns over 90k after round 1: 2.4% vs rival (1464/61674), 2.9% vs
nemesis-v2 (1940/67327), mostly contest (680-1072) and swirl (320-400), then corners, pilgrimage, lanes, ambush.
All of it is in `decide`; world update ~11k (max 25k), turn order ~3.6k (max 14k), comms ~1.3k, ward ~1.2k (max 40k
once). On those turns (mean / p90 / max):

| Step | mean | p90 | max | Dominant step on |
|---|---|---|---|---|
| `step_guard` | 24-26k | 49-53k | 137-154k | 614 / 887 turns |
| `want_home` (incl. the turn's first threat and Reach builds) | 17k | 31k | 57-63k | 359 / 454 |
| `farm` | 23-25k | 33-39k | 74k | 302 / 352 |
| `prey` | 12-13k | 26-27k | 70-72k | 179 / 228 |
| `plan_strikes` | 6k | 12k | 21-27k | — |
| fight simulations, summed (up to 13 a turn) | 16.5-17k | 32k | 78-98k | |
| Reach builds, summed | 13-15k | 30-34k | 72k | |
| `pursuit` | 8k | 13-15k | 24-30k | |
| `enemy_cast` | 1.4k | 3.9k | 12-17k | |

So the fight steps need real cuts (simulations and Reach builds), farm needs its cold cost bounded, and the rest is
small.

### 1. Remove gates on bounded work

The rows marked phase 1. At 100M the bot is byte-identical (the gates never fired there), so the check is the real
budget: out-of-fuel turns no higher than the baseline's (`bench.py --fuel 0`, rival and nemesis-v2).

Removing all of them at once (on hecate-v4) raised out-of-fuel turns 48/36 -> 121/112: each one's work is bounded,
but they fired on turns the fight steps had already drained, and acted as the turn's last brakes. So they go in two
steps:

- **1a, done:** enemy-cast, camp-cast, route-retry, crow-flies-kite (both sites, plus kite's untagged approach gate)
  and travel-dash; `Pathing::approach` has no fuel floor or fuel-derived depth (`prepare_approach` keeps the floor for
  the farm walk and `prepare_walk`, charging `max_approach_cost()` when no distance is known). On hecate-v4: 100M 16/16 identical, out-of-fuel 41/42 (48/36). On hecate-v5:
  100M 16/16 identical, out-of-fuel 0/5 (1/2; all on contest and swirl fight turns), 11/16 real-budget games
  identical to v5's.
- **1b, after phases 3 and 4:** turn-order, farm-no-route, farm-kept-target, crow-flies-farm, static-descend. These
  run costly work on short turns; they come out once the fight steps and farm fit.

### 2. The end-of-turn queue; on-demand caches

- One queue in main.cpp after `set_turn_order`/comms, in a fixed priority order: spawn fields, bush clusters, centre
  fields, attack tiles, altar fields, next turn's walk, Reach statics and sight masks near enemies. It replaces
  `warm_up`, `warm_centres`, `find_all_bush_clusters`, `warm_reach` and `prepare_next_turn`, and holds the one fuel
  check.
- Callers no longer test whether a cache is warm: `prepare_member`, `ward_bushes`, `spell_clear`, siege and farm
  attack tiles compute what is missing.
- The untagged dependences above: `home_ground` always, fixed `approach` depth, fixed siege route cap, no
  `walk_first_floor`.
- Check: with the queue switched off, replays at 100M are byte-identical to it switched on, except the
  `home_ground` change, which goes in its own commit and A/B. Then real-budget out-of-fuel turns and an A/B.

### 3. Fight simulations

- `fight-cut` and `want_home`'s gates go: its two simulations always run, and they come first in the turn.
- `step_guard` and `prey` get the measured limits with their fallbacks.
- If phase 0 shows a limit binding often, cut simulation and Reach cost first (fewer distinct keys by settling with
  bounds, cheaper Reach queries), then set the limit.
- Check: real-budget out-of-fuel turns no higher than the baseline's, then an A/B. Previous removals without limits
  doubled out-of-fuel turns, so this is the phase most likely to need several rounds.

### 4. Farm

- Always evaluate. Cold (centre fields not yet built), build the one field from our tile (~14k mean, 26k max on
  100x100), as farm already does when it can afford it; delete the mini-farm and the per-group loop gate.
- If phase 0 shows a cold evaluation plus a fight turn can exceed 100k, put the first centre fields in the champion's
  first turn (200k) rather than add a limit.

### 5. End-of-turn decisions

`comms::send` always re-reads vision after moving; `set_turn_order` and `ward_bushes` lose their gates.

### 6. Clean-up

Delete `fuel_ok`, `end_reserve`, `last_reserve`, `walk_first_floor`, the estimators and `note_shortcut`'s callers;
keep the out-of-fuel counter. `grep fuel bots/hecate/src` should then show only the queue, the draft, `FuelMeter` and
debug output. Update AGENTS.md's Fuel section and the bench docstring (SHORTCUT counts become out-of-fuel counts only).

## Done when

- No turn above ~95k at 100M fuel on ladder, `maps/gen` and `maps/gen-central`.
- Out-of-fuel turns at the real budget no higher than hecate-v5's, counted with `tools/fuel/oof.py` on a full A/B
  (hecate-v5: ~170 in 390 games; the 16-game bench has no shared-gem map).
- Level or better against hecate-v5 on all maps from both sides (390+ games), so 100M and real-budget games agree.

## Open questions

- The worst fight turn: a Monolith fight with 8-10 champions, the strike planner (up to ~25k), Reach builds and
  `step_guard` in one turn. If it does not fit, `step_guard`'s limit falls and its fallback decides more tiles.
- Whether the queue should also pre-simulate anything. Fights cannot be reused across turns, so probably not.
- If phase 3's limits bind often and cost wins, a single logged fuel-funded extension in `step_guard` (extra tiles
  while fuel lasts, `lethal(q)` otherwise) is the fallback option, kept in one place.
