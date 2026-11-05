# Z: exact fuel savings in the farm turn (ocean, 2026-11-05)

Track Z of the idea programme. Make the farm turn's evaluation cheaper *exactly*, so that at the real budget the
loop cuts less often or later. Every decision at unlimited fuel stays the same. Base `variants/oc-base1`; dev copy
`variants/oc-fuel-dev`; seeds 513000-513999.

## Evidence

**The loop is worth ~3 points, and each 25% of it saved is worth ~1.** Five diagnostic A/Bs on fresh-513001..513010
(5,120 games each). The first four are astraeus 5b66bde with the gate view (`fuel()` reads the real-budget view
under `--fuel 10000000`) against the real-budget cap. The fifth is ocean.

| Copy | Win % | 95% CI |
|---|---|---|
| gate view, unchanged | 51.2 | |
| loop 25% cheaper (`DiscountFuel` refunds 25% of what it spends) | 52.1 | 50.8-53.5 |
| loop 50% cheaper | 53.3 | 51.9-54.6 |
| loop free (`FreeFuel` around it) | 54.4 | 53.0-55.8 |
| ocean, never cut, at the real budget (oc-fuel-nocut vs oc-base1) | 50.1 | 48.7-51.5 |

Never cutting is level: OOF turns rise from 52.6k to 340.9k and take back the gain. The gain must come from
cheaper work, not from a later cut.

**Where cut turns' fuel goes.** Measured with a patched private fastrunner that records exact fuel and execution
counts per wasm basic block, filed by turn. A cut turn is one whose loop hit `farm-partial-evaluation`; there are
~810 a game, both teams. The bot was built `-g` and the blocks were symbolised. 24 games on fresh-513000.

- A cut turn spends ~71k fuel in blocks (host fees not counted). farm_turn is 21k of that: the loop 14-15k, the rest
  before the loop.
- **Fuel saved anywhere before the loop goes to the loop**, because `room()` cuts at a fixed reserve. 1k saved
  there buys about half a group's evaluation.
- The race chain: `race_left` is 2.6M fuel a game, about 6 calls and ~520 fuel each per cut turn. `gems_share` is
  1.06M. Both run before the loop, through `prices()`, `home_trip`, `farm_recall` and `closing`. They loop over
  allies (and comms bags) whose state changes only at `World::update`/`observe`. Memoised, ~4.5k a cut turn comes
  back (~20% of the loop).
- Stage probes inside the loop (oc-fuel-prof2, 64 games, 57.6k cut loops). A cut loop spends 21.7k and evaluates
  k≈9 of n≈25 groups. 54% of cut loops carry a bag (banking: 24.5k each, against 18.3k).
  - ~1.7k a group before clearing: the head and filters 244, the later-turn bound 132, facts 114, fastest and bank
    185, steps 160, `live_steps` 325, respawn/idle 117, via 84, the prune 159.
  - Crew work ~5.8k a cut loop (27%):
    - `crew_work` 1.5k a call;
    - `plan_crew` 0.9-2.5k;
    - the crewable bound's `crew_available` loop ~1k;
    - the claimed bound ~0.6k.
- Small exact items in the loop (the line profile on cut turns, per cut turn): `strong()` 370, `kited()` 210,
  `walk_range()` 180, `exposure()`'s `home_side` 260, `too_late`'s `tribute_turns` 230. ~1.2k together.

## Design

Each step is exact: at 100M fuel, bench.py's replays (default and wide sets) stay byte-identical to oc-base1's.
`params::fuel::` switches each step, for attribution; all off is oc-base1.

1. **race**: memoise the allies' parts of `gems_short` (pending tributes, by horizon), `race_left` (posted bags) and
   `gems_share` (allies alive), and `World::ally_rate`, by `(world.observations, world.round)`. `my_gems()` is
   still read each call: a kill mid-turn changes it.
2. **loop**: per-group memos in the loop for `strong`, `kited`, `exposure` and `walk_range`. Use
   `known.chained_tribute` in `too_late`. Read the dash state once for `travel_turns`.
3. **crew**: memoise `crew_work`, `plan_crew` and the crewable bound per group and turn where their inputs are
   fixed within the turn (the loop runs up to twice a turn: banking and not).
4. **steps**: a fast path for `live_steps`/`approach_slot` when the camps version is unchanged.
5. Others as the profile then shows: before the loop on cut turns (`camp_output`, `altar_usable`, `main_stat`,
   `crew_allies`, `update_champion`) and in the loop.

Steps that save little are dropped once the farm-partial count shows they move no cuts.

## Fuel estimate and expected gain

Steps 1-4 total ~8-10k a cut turn, 40-50% of the loop in equivalent fuel. By the diagnostics that is +1.5 to +2
points against oc-base1. A single step under ~25% (~5k) is below what an A/B can resolve (±0.7 at 20k games), so
steps are measured by bench (farm-partial count, mean, p99, OOF) one by one and by A/B cumulatively.

## Grid

- dev-1: race; dev-2: + loop; dev-3: + crew; dev-4: + steps; ...
- A/B each cumulative stage against oc-base1 at the real budget, SPRT 0.50/0.51, on fresh-513011 and up.
- Confirm the final one at ≥20k games on unused seeds, plus `--mix varied`, plus the panel (astraeus, proteus).

## Results

Kept: `variants/oc-fuel-s5`, the same as `oc-fuel-dev` with every `params::fuel::` knob on. Details, the step table
and what lost are in EXPERIMENTS.md, "Farm turn fuel (ocean, 2026-11-05)".

- Exact: all 52 wide-set bench replays at 100M are byte-identical to oc-base1's.
- Fuel at 100M: the mean turn went from 55,771 to 54,344 (-2.6%), and p99 from 119,182 to 114,978 (-3.5%).
  Farm-partial turns at the real budget went from 16,259 to 12,370 (-24%).
- Confirm on unused seeds: 50.5% (49.8-51.2) over 20,480 games. On `--mix varied`: 51.9% (50.5-53.3) over 5,120.
- Panel, on the same suites: against astraeus 55.2 vs oc-base1's 54.5; against proteus 53.9 vs 52.0.
- Why it stopped there: the loop's cuts are worth ~3 points in all, about +1 per 25% of cut-loop fuel saved, and never
  cutting is level. What is left before the loop is diffuse (no repeated inputs), so nothing else would move the cuts
  enough to show.
