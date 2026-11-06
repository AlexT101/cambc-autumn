# Fuel round 6: bounded cheaper work that changes decisions (ocean, 2026-11-05)

Goal: fewer out-of-fuel (OOF) turns and fewer farm loops cut short, by doing less or cheaper work under fixed,
fuel-independent conditions (no fuel gates). Base `variants/oc-fuel4` (= `bots/ocean`, CHANGES 415); dev copy
`variants/oc-fuel6-dev` with `params::fuel6::` knobs, all off byte-identical to oc-fuel4 at 100M (default 16/16,
wide 52/52, pool 128/128). These change play, so they are judged by A/B.

Scripts: `replays/fuel/ocfuel6/` (`bench.sh`, `ab.sh`) and `fuel6-tools/` (`mk.sh` makes a knob variant
`variants/oc-f6-NAME`, `try.sh` benches it, `an.py` summarises a bench: OOF turns, mean fuel, farm cut share,
and at 100M the decision change rate against oc-fuel4; `wr.py` reads a running A/B). A/B suites: dev 528000-528039
(`maps/suites/merged/oc-fuel5-dev`), confirm 528100-528139 (`oc-fuel5-conf`), varied 530000-530009
(`oc-fuel6-varied`), panel `panel-check-514510` (PANEL.md, astraeus-now-1105 as its astraeus).

## Measures

- **OOF turns, mean fuel**: bench.py at the real budget on the wide (52 games) and pool (128) sets. Once a decision
  changes the games diverge, and these small benches then swing by ±10% (h13: wide +10%, pool -14%), so OOF is
  read from the A/Bs' counts (20k games).
- **Farm cut short**: `farm-partial-evaluation` SHORTCUT lines per farm-branch turn (D lines 'F'). oc-fuel4: wide
  6.7%, pool 11.8%.
- **Decision change rate at 100M**: each game against oc-fuel4's on the same map and side, until the first round
  where our D lines or the opponent's stdout differ; changes per turn of exposure.

## What the probes say (oc-fuel4, before any candidate)

- **Farm cuts are not fight turns.** Probe on the pool set at the real budget (32k cuts): 80% see no enemy, 58% are
  the banking loop (`farm_turn<false, true>`), mostly on big classic and huge maps. The loop is cut after 42% of the
  groups with 42.7k fuel left (p10 25.5k): its reserve (`loop_floor + walk_reserve + search_cost_estimate(steps +
  max_detour)`) is that size on 100x100 maps. Fuel spent before farm on those turns is 17k (median), mostly
  `World::update`. So cheaper fights leave farm's cuts about where they are; only a cheaper loop or post-loop walk
  would move them. EXPERIMENTS "What fuel is worth to astraeus" puts the gates' cuts at ~6 points and OOF at ~0.5.
- **Cross-turn fight memo: dropped before coding.** Hashing `trade()`'s whole input (both sides, kits, flags): 9.6%
  of 127k sims at 100M repeat a sim of an earlier turn (6.1% the previous round), 7.0% of sim fuel. Sims are 4.1k
  mean, so a ~500-fuel content key saves nothing. Fuel campaign 6 round 6 found the same (6.5%).
- **want_home's stand** (pool, 100M, 142k stands past the early returns): no roster 80k calls at 2.7k (216M); hit
  now 33k at 14.4k (481M, lost 41%); walkers only 28k at 9.8k (278M, lost 31%). Walkers-only stands send us home a
  third of the time, so skipping them is not a small change.
- **The strike search** (pool, real budget, 31k searches): one-node searches (walk-only, strike_free 4) are 25% of
  search fuel at 12.9k, two thirds of them ending in "stay" (length 0), which hands the walk to the goal; searches of
  10+ nodes are 11% of its fuel.

## Candidates

| Knob | Change | Expected | Risk |
|---|---|---|---|
| K1 `walk_only_stay` | a ranged walker with no strike from any end tile skips the search and stays (the goal walks) | up to a quarter of search fuel; the search oracle is -54% OOF, so perhaps -5..-10% | the third of walk-only searches that pick a safer step lose it; the goal's step guard still keeps lethal tiles off |
| K2 `fight_horizon` 13 / 9 | every fight simulation plays 13 or 9 own turns instead of 17 | the sim oracle is -45% OOF; long sims shorten | fights decided after turn 9/13 read as not lost: bolder stands and chases |
| K3 `stand_horizon` | only want_home's fresh stand trades (walkers or camps, never memo-shared) on a shorter horizon | part of K2, aimed at the stand (oracle -50%) | as K2, for walkers-only stands only |
| K4 `max_nodes` / `max_exact_queries` | the search's caps 24 -> 12 nodes, 10 -> 6 queries | the 10+ node searches are 11% of search fuel | deep plans (dash-reset chains) cut |

| F1 `farm_head` / `farm_window` | past the loop's first head groups, only a rotating window of the rest a turn | fewer farm cuts on big maps | a better group in the tail found a few turns late |

Farm loop (before F1): Its cuts come from a reserve sized for an uncached route search on big maps; a lower
reserve is a gate change, and the loop's per-group cold facts were already worked on (GATE-PLACEMENT item D).

Each candidate: bench (OOF, fuel, farm cut, change rate), SPRT 0.50/0.51 on the dev suite, then the 20,480-game
confirm, varied and the panel for a winner. Keep bar: a 20k-game win on unused seeds, no loss on varied or the panel.

## Results: K1 wins, frozen as `variants/oc-fuel6`; everything else lost or was level

**Bench** (bench.py against oc-fuel4; real budget: OOF turns, farm cut share; 100M: decision change rate). oc-fuel4:
OOF 632 wide / 1049 pool, farm cut 6.7% / 11.8%. Off (every knob false/0): identical 16/16, 52/52, 128/128.

| Variant | OOF wide / pool | Farm cut wide / pool | Changes at 100M, wide / pool |
|---|---|---|---|
| K1 `walk_only_stay` | 694 / 982 | 6.7% / 11.9% | 1 per 2,101 / 1,683 turns |
| K2 `fight_horizon` 13 | 694 / 898 | 6.7% / 11.7% | 1 per 2,340 / 948 |
| K2 `fight_horizon` 9 | 607 / 924 | 6.4% / 11.7% | 1 per 1,693 / 684 |
| K3 `stand_horizon` 9 | 636 / 906 | 7.2% / 12.3% | 1 per 2,465 / 1,366 |
| K4 12 nodes, 6 queries (c1) | 646 / 885 | 6.8% / 11.8% | 1 per 10,785 / 9,300 |
| K5 `no_walk_leaf` | 564 / 903 | 6.8% / 11.8% | 1 per 3,703 / 3,269 |
| F1 head 8, window 4 | 554 / 1014 | 4.3% / 9.0% | 1 per 2,463 / 1,971 |
| F1 head 12, window 4 | 591 / 1067 | 4.9% / 10.1% | 1 per 4,509 / 3,879 |
| F1 head 20, window 4 | 566 / 988 | 6.0% / 11.9% | 1 per 15,222 / 13,315 |

The small benches' OOF counts swing ±10-15% once games diverge (K1: wide +10%, pool -6%), so OOF is read from the
A/Bs. Fuel on the same states (turns before each game's first divergence at 100M) barely moves (K2 13: -0.03% wide,
-0.04% pool; `replays/fuel/ocfuel6/try1.log`): those turns are mostly before first contact, where the fight variants
start to change play.

**F1** is the round's farm candidate (added after the cut probe above): past the loop's first `farm_head` groups,
nearest to last turn's choice, it weighs only `farm_window` of the rest a turn, a window rotating by round, plus our
choice and the groups claimed or held. It applies on every turn of a map with more groups than head + window.

**A/Bs** (own drafts, fast runner, real budget, against oc-fuel4; SPRT 0.50/0.51 on `oc-fuel5-dev`):

| Variant | Suite | Games | Win % | 95% CI | OOF cand / ref | Cuts (cand vs ref) |
|---|---|---|---|---|---|---|
| K1 | dev (SPRT H1, LLR 3.50) | 15,524 | **50.9** | 50.1-51.7 | 117.8k / 119.1k (-1.2%) | |
| K1 | **conf 528100-528139** | 20,480 | **51.3** | 50.6-52.0 | 157.8k / 159.5k (-1.0%) | prey-cut-short -12%, step-guard-entry -2%, turn-order -3%, farm-partial +0.1% |
| K1 | varied 530000-530009 | 5,120 | 51.1 | 49.7-52.5 | 45.0k / 45.1k | prey-cut-short -15% |
| K2 13 | dev (H0) | 8,135 | 49.7 | 48.6-50.8 | 60.2k / 61.2k (-1.6%) | |
| K2 9 | dev (H0) | 3,409 | 48.4 | 46.8-50.1 | 23.1k / 24.1k (-4.3%) | |
| K3 9 | dev (H0) | 4,870 | 49.1 | 47.7-50.5 | 35.0k / 35.2k | |
| K4 c1 | dev (H0) | 14,041 | 50.3 | 49.4-51.1 | 97.3k / 107.1k (**-9.1%**) | turn-order -2%, the rest level |
| K5 | dev (H0) | 5,092 | 49.5 | 48.1-50.8 | 35.8k / 37.9k (-5.5%) | |
| F1 8/4 | dev (H0) | 3,373 | 48.2 | 46.5-49.9 | 22.4k / 23.2k | **farm-partial -30.5%**, turn-order -5% |
| F1 12/4 | dev (H0) | 2,330 | 48.2 | 46.2-50.2 | 16.2k / 16.4k | farm-partial -20.8% |

**K1's panel** (panel-check-514510, 5,120 games a member; base = oc-fuel4's rates in PANEL.md; second set
oc4-panel2 for astraeus and proteus):

| Member | K1 | oc-fuel4 | Diff | Second set (oc-fuel4) | Pooled diff |
|---|---|---|---|---|---|
| astraeus-now-1105 | 56.8 | 55.6 | +1.2 | 57.5 (55.3) | +1.7 |
| panel-proteus | 61.4 | 59.2 | +2.2 | 60.8 (59.1) | +2.0 |
| panel-demeter | 63.1 | 62.6 | +0.5 | | |
| panel-ocean-td | 79.7 | 80.5 | -0.8 (fail below 79.0) | | |
| baselines/v67 | 75.3 | 74.8 | +0.5 | | |

Mean +0.72 on panel-check; no member fails. K1 passes the keep bar: a 20k-game win on unused seeds, level-or-better
on varied, the panel passed.

**What it says.**
- K1 is a decision gain, not a fuel one: OOF -1%. A ranged champion with no strike from any end tile used to search
  only to choose a step (two thirds of the time it stayed); the step spends the attack, so a farmer near enemies
  stopped hitting its camp. Staying hands the walk and the attack to the goal, whose step guard keeps lethal tiles
  off. It frees fuel ahead of prey: prey-cut-short -12..-15%.
- K5, the same for a full search (drop the walk-alone leaf when a strike is reachable), loses: there the step away
  is worth taking.
- Fuel-only effects are hard to buy and worth little. The search caps (c1) cut OOF 9% for no win; shorter fight
  horizons cut OOF 2-4% and lose. As EXPERIMENTS "What fuel is worth to astraeus" found, OOF turns are worth ~0.5
  points in all.
- Fewer farm cuts are not worth a cruder loop. F1 removes 21-31% of the farm-partial-evaluation cuts and loses
  ~1.8 points: on the 88% of turns the loop completes, the tail it skips held the best group often enough to cost
  more than the cut turns gain. The farm cut is mostly the banking loop on big maps with no enemy in sight, stopped
  by a reserve sized for an uncached route search; the fight-side variants do not move it (all within ±1%).
- Not built: a cross-turn fight memo (probe above), a stand verdict memo (exact repeats are 6-10% of sims, so an
  approximate one would need positions and cooldowns quantised), and K1 + c1 (c1 alone is level and adds a degraded
  path, so it ships only on a gain).

**Frozen:** `bots/variants/oc-fuel6` (READY) = oc-fuel4 plus K1 alone, hard-coded in `plan_strikes` (no knob):
bench.py identical to `variants/oc-f6-k1` at 100M (16/16, 52/52, 128/128) and at the real budget (52/52, 128/128),
so K1's A/Bs are oc-fuel6's. Shipped into `bots/ocean` (2026-11-06) with spawncamp round 2 as
`variants/oc-base4`, CHANGES 422 (merge A/B 51.1% against oc-fuel4: EXPERIMENTS "oc-base4: CHANGES 416 and 422
merged"). Sources: `replays/ab/f6-*`,
`replays/ab/pchk-f6-k1-vs-*`, `replays/ab/p2-f6-k1-vs-*`, logs and shortcut counts in `replays/fuel/ocfuel6/ab/`,
bench JSONs in `replays/fuel/ocfuel6/bench/`.
