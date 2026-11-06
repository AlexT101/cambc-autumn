# Fuel round 5: the strike search and the fights (ocean, 2026-11-05)

Goal: fewer out-of-fuel (OOF) turns in ocean with exact savings in the strike search (`combat/plan.cc`) and the
fight sims behind want_home's stand (`stand_lost_at`). Base `variants/oc-fuel4` (= `bots/ocean`, CHANGES 415); dev
copy `variants/oc-fuel5-dev`.

Exactness check: `tools/fuel/bench.py` at 100M against oc-fuel4, replays byte-identical to oc-fuel4's on the
default (16), wide (52) and pool (128: the first 64 maps of fresh-519039) sets. Scripts in `replays/fuel/ocfuel5/`
(`bench.sh`, `ab.sh`, `census.sh`) and `research/ideas-2026-11-05/fuel5-tools/` (census scopes, tables, oracles).
A/Bs: fresh ladder-mix suites 528000-528039 (dev, `maps/suites/merged/oc-fuel5-dev`) and 528100-528139 (confirm,
`maps/suites/merged/oc-fuel5-conf`). Profiles ran on fresh-525200 (64 maps, both sides, 128 games), which no A/B uses.

## Earlier work

astraeus and astraeus_wip have no strike or fight fuel work since 5b66bde0 that ocean lacks: astraeus's 3076ffa9,
a790c441 and 7950979e are the farm and pre-loop savings fuel round 4 ported (CHANGES 415); the rest is logic. Fuel
campaign 6 (`research/hyperion/fuel-campaign-6/NOTES.md`) already shipped the walk-only search (CHANGES 352) and left
bf8df313 (lazy stand walkers: exact, -0.3..-0.4% total, read -0.73 points on 20,480 games) unshipped. Its round 6
found no repeated sims or blows within a turn, and named the sim itself and the number of stands that reach a sim (a
decision-level change) as the levers left.

## Where the fuel goes (oc-fuel4, real budget)

Census copy `variants/oc-fuel5-cen` (instrument.py `--fine --trace --lenient`, plus `fuel5-tools/strike_scopes.py`'s
scopes inside the search and the stand), 128 games:

- On OOF-first turns, where present: strike_search 37.8k a call (51% of turns; read 14.0k, grow 11.4k, price
  10.5k), want_home's `stand_lost_at` 20.4k (82%; `stand_trade` 13.9k, `stand_reach` 7.5k), the channels 15.1k (68%).
- Inside the search, a turn: read 7.2k (geometry 3.3k, of which the guard cover 2.1k at 4.6k a call; the foe loop
  2.1k), grow 5.2k (2.3k its own, settle 2.0k at 480 a call), price 4.3k (the tile loop 3.7k, its blows 1.7k).
- Search lines (`debug_search`): plans of length 0 are 28% of search fuel (14.3k mean), length 1 35%; searches with
  one node 26%. Walk-only searches (strike_free 4) are 14,620 of the pool set's searches and 20% of search fuel (13.2k
  mean: read 5.6k, grow 1.7k, price 5.5k with 1.6 tiles priced and 0.7 blows).

**Oracles** (fuel paused over a part, debug builds, real budget; OOF turns on wide / pool against oc-fuel4):

| Paused | wide | pool |
|---|---|---|
| nothing (oc-fuel4) | 632 | 1049 |
| the strike search (`plan_strikes`) | 292 | 454 |
| want_home's stand (`stand_lost_at`) | 318 | 432 |
| every fight sim (`trade`) | 347 | 609 |

Each of the three is worth about half the OOF turns, so even a fifth off one would show.

## Plan

Exact cuts only (identical at 100M on the three sets), no fuel gates. In order:

1. The guard cover in the search's read (`step_guard_cover`, 4.6k a call): profile its parts, then cut what repeats
   work the strike pre-check (`strike_free`) or the step guard already does.
2. Walk-only searches: the price loop's fixed costs (tile set-up, camps, ranking) for one or two candidates a tile.
3. The tile loop's set-up and grow's settle in full searches.
4. Then the A/B (SPRT 0.50/0.51 on the dev suite; 20,480-game confirm if promising), with OOF counts.

## Results: nothing shipped, no A/B

Every cut found is exact but worth well under 1% of an OOF turn's fuel, and none was A/B'd: an exact change that
moves total fuel by hundredths of a percent cannot show at SPRT 0.50/0.51, and fuel campaign 6's round 5 (-0.5%
total, -0.7% OOF turns) read 49.6% over 10,240 games. `variants/oc-fuel5-dev` is still oc-fuel4.

- **The profile is flat.** Self fuel on OOF-first turns (2,016 turns, 90.0k mean): the sim (`s.trade`) 6.9%,
  farm's loop 5.3%, Reach builds 3.6%, and then some 30 parts at 1-3% each. The search's own parts are grow 2.5%,
  the guard cover 2.3%, settle 2.1%, the search's body 1.6% and its blows 1.4%. Each is tight code costing a few
  thousand a call, not repeated work.
- **The guard cover** (`step_guard_cover`, 4.6k a call): building its foes 1.2k, the cell loop 3.3k. Timed inside
  it (8 maps, 1,819 calls), radius 1 costs 1.58k a call (the reach window 270, the board clear 36, setting tiles 14)
  for 6 cells visited and 1.7 covered, radius 2 2.88k for 11 and 6: ~150-200 a visited cell, which is the cell test's
  own instructions. Masking the cells by bitwise ops could save perhaps ~600 a call, ~0.3% of an OOF-first turn.
- **L1, lazy stand walkers** (fuel campaign 6's bf8df313, ported to ocean's `stand_reach`: the seen enemies' walks
  only where the roster reads them). Identical at 100M on all three sets (16/16, 52/52, 128/128); total fuel -0.057%
  (default), -0.031% (wide), -0.006% (pool), heavy turns -0.02..-0.06%, with more turns dearer than cheaper (24k
  against 9k on the default set: codegen). Kept as `fuel5-tools/l1-lazy-stand-walkers.diff`, not shipped.
- **G1** (grow saving only the first n unit healths) and **E1** (`plan_strikes` without `flatten`): exact, G1 dearer
  (+0.005..+0.011%), E1 unchanged (heavy -0.002%). Dropped.
- Walk-only searches (20% of search fuel) cost what they price: read's guard cover and the tile loop's blows. Their
  fixed costs (tile set-up 1.4k, camps and ranking 0.9k) are a few percent of the turn at most.

**Why the oracles don't carry over.** Each oracle pauses a whole computation (one ~20-40k block on the turns that run
out); the exact cuts available inside it are ~1% of it. What would buy back the oracles' OOF turns is doing less of
the work (fewer stands reaching a sim, a cheaper search on turns whose plan is "stay": 28% of search fuel goes to
plans of length 0), which is a decision change and needs its own A/B rather than a byte-identity check.

**Leads, not exact:** a cheaper stay-or-walk search when no strike can follow (len-0 and walk-only plans), fewer
stand sims per turn (round 6's "decision-level" lever), and farm's `farm-partial-evaluation` shortcut, which fired
26,049 times in 128 real-budget census games against 1,247 OOF turns: farm cut short by fuel is far more common than
running out.

Tools: `fuel5-tools/` (census scopes, label tables, SRCH parser, `cmp.py`, `try.sh`) and the oracle diffs
`oracle-o1.diff` (strike search), `oracle-o2.diff` (`stand_lost_at`), `oracle-o3.diff` (`trade`). Census summaries in
`replays/fuel/ocfuel5/cen*-census.txt`; the profiling copy `variants/oc-fuel5-cen` is a debug-only census build.
