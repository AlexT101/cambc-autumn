# Fuel budgeting (ocean, 2026-11-06)

Goal: win rate from fuel. Out-of-fuel (OOF) turns and gate cuts are part of the win rate, so every change is judged by
A/B; OOF and cut counts are diagnostics. On 2026-11-06 the user relaxed the "no new fuel gates" rule: fuel-aware code
(per-subsystem budgets, anytime searches, dynamic reserves, a cheaper method on a short turn) is allowed when it wins.

Base for Phase 1: `variants/oc-tuned4` (= `bots/ocean` until 2026-11-06). Phase 2 on: `variants/oc-retest-clean`
(oc-tuned4 + holder-choice efficiency + efficiency funnel + reveal ward, shipped as ocean).

Tools: `fuelbud-tools/` (`mksuites.sh`, `mkgv.py` oracle copies, `ab.sh`, `oracles*.sh`, `census.sh`, `paired.py`).
Logs and shortcut counts in `replays/fuel/fuelbud/`.

Suites (ladder mix unless noted; merged dirs in `maps/suites/merged/`):

| use | seeds | merged dir |
|---|---|---|
| dev (SPRT) | 533000-533039 | `fuelbud-dev` |
| confirm | 533100-533139 | `fuelbud-conf` |
| varied (`--mix varied`) | 533200-533209 | `fuelbud-varied` |
| oracles (Phase 1) | 533300-533319 | `fuelbud-oracle` |
| census | 533400 (first 128 maps, both sides) | |

## Phase 1: ocean's prize (oc-tuned4)

All at `--fuel 10000000` against `variants/oc-fb-cap` (`cap_variant.py`: oc-tuned4 charged back to the real budget,
so it plays as at the real budget; 72-75k OOF turns in 10,240 games), own drafts, 10,240 games each on
`fuelbud-oracle`. "gv" copies are the gate view (EXPERIMENTS "What fuel is worth to astraeus"): `fuel()` reads what
the real budget would leave, so gates cut as there, and a turn past it plays on. A family under `FreeFuel` reads the
whole 10M inside and is refunded on leaving. `bNNN`: the gate view at a budget of NNN thousand a turn (2x on the first
turn; the queue still fills as at 100k, its floor rises by the excess).

| copy | what is free | win % (CI) | paired vs gate view (CI) |
|---|---|---|---|
| oc-tuned4 at 10M (ceiling) | everything: no cuts, no OOF | **53.6** (52.6-54.5) | +2.0 (+0.7..+3.3) |
| gate view | OOF only | **51.6** (50.6-52.6) | |
| b125 | OOF, and 25% more budget for the gates | **53.6** (52.7-54.6) | +2.0 (+0.8..+3.3) |
| b150 | OOF, 50% more | 53.7 (52.7-54.7) | +2.1 (+0.9..+3.4) |
| farm (`farm_turn`) | | 52.6 (51.6-53.6) | +1.0 (-0.2..+2.3) |
| the farm group loop | | 53.0 (52.0-53.9) | +1.4 (+0.1..+2.6) |
| the loop, non-banking only | | 52.8 (51.8-53.7) | +1.2 (0.0..+2.4) |
| the loop, banking only | | 52.1 (51.1-53.1) | +0.5 (-0.5..+1.5) |
| prey | | 52.4 (51.4-53.4) | +0.8 (-0.3..+1.9) |
| step guard | | 52.3 (51.3-53.3) | +0.7 (-0.4..+1.8) |
| strike search (`plan_strikes`) | | 51.7 (50.7-52.6) | +0.1 |
| turn order | | 51.7 (50.7-52.6) | +0.1 |
| want_home's stand (`stand_lost_at`) | | 51.6 (50.6-52.6) | 0.0 |
| turn-end queue | | 51.2 (50.3-52.2) | -0.4 |

- **ocean's prize is 3.6 points, not astraeus's 6.3**: the fuel rounds since (4-6, CHANGES 406, 415, 422) took much of
  it. It splits into **OOF turns ~1.6** (gate view against the real budget, 50) and **gate cuts ~2.0** (ceiling
  against gate view). On astraeus 5b66bde OOF turns were worth ~0.5: ocean runs out more (its fights are dearer) and
  its cuts cost less.
- **25% more fuel recovers all of the cut prize** (b125 = ceiling): the cuts are marginal, not deep. A turn needs ~a
  quarter more budget where it cuts, so making the cut-prone work ~20% cheaper, or moving it into turns with slack,
  is the same prize.
- By family, the farm group loop holds the most (+1.4), nearly all of it in non-banking loops (+1.2; banking +0.5,
  as the astraeus banking study found their outcome rarely changes). Prey (+0.8) and the step guard (+0.7) come
  next. The strike search, the stand, the turn order and the queue hold nothing as cuts (their value is in OOF
  turns, which the gate view already frees). Family oracles overlap: refunded fuel is fuel later gates read.
- Gate cuts per game (the cap copy, 10,240 games): farm-partial-evaluation 166, step-guard-entry 60, turn-order 17,
  prey-cut-short 15, step-guard-look 8, comms-stale-vision 6, farm-no-route 5; OOF 7.

**Census** (`variants/oc-fb-cen`: `instrument.py --fine --trace --lenient` on oc-tuned4, against oc-tuned4, real
budget, 128 maps of fresh-533400 both sides, 256 games; `replays/fuel/fuelbud/cen/cen0-*.txt`). 1,458 OOF-first
turns, 471 late, 19,089 heavy finished turns.

| gate | firings | left at firing q10/q50/q90 | turn ran out | left after decide (finished) q10/q50/q90 |
|---|---|---|---|---|
| farm-partial-evaluation | 55,415 | 25.1k / 41.3k / 60.0k | 1.0% | 10.1k / 23.8k / 42.9k |
| step-guard-entry | 13,460 | 18.0k / 33.4k / 49.6k | 3.4% | 7.6k / 20.4k / 37.5k |
| turn-order | 4,342 | 1.9k / 6.6k / 9.5k | 1.5% | 1.7k / 6.2k / 9.1k |
| prey-cut-short | 4,009 | 22.5k / 35.7k / 55.1k | 5.7% | 5.8k / 14.7k / 34.3k |
| farm-no-route | 1,970 | 9.6k / 17.1k / 26.9k | 8.0% | 3.1k / 9.3k / 19.5k |
| step-guard-look | 1,718 | 30.3k / 38.0k / 49.5k | 0.3% | 12.6k / 25.0k / 37.9k |

- **The farm loop's cut keeps back about 2.6x what the turn then spends.** On cut loops' finished turns decide spends
  16.4k p50 / 26.9k p90 / 40.1k p99 after the loop, against 42.8k kept back (p50); on loops that finish, 12.1k p50.
  The median cut turn ends decide with 23.8k unused; the turn-end queue gets it.
- **Where OOF turns run out** (decide-level scope of OOF-first turns): farm 36%, strike_search 12%, act_end 10%, retreat
  6%, strike_after 5%, goal 5%. 56% of OOF turns passed no fuel check: fight turns, strike search 45.6k inclusive on
  71% of them, `stand_lost_at` 22k on 84%; on the rest (with a passed check) the farm loop's last check (11%), the
  farm walk's (`farm.cc:2379`, 8%) and `step_field`'s (`pathing.cc:1787`, 8%).
- OOF-first turns: 32% have no enemy within 6; heart_of_ruin 30%, issac 13%, prism 12%.

## Phase 2-5 on oc-retest-clean

Dev copy `variants/oc-fb-dev` = oc-retest-clean with `params::fuelbud` knobs, every default the shipped behaviour:
bench.py at 100M identical to oc-retest-clean, 16/16 default, 52/52 wide, 128/128 pool. `fuelbud-tools/mk.sh NAME
knob=value...` makes `variants/oc-fb-NAME`. A/Bs against `variants/oc-retest-clean`, own drafts, real budget, fast
runner; SPRT 0.50/0.51 on `fuelbud-dev` unless noted.

| knob variant | change | games | win % (CI) | OOF cand / ref |
|---|---|---|---|---|
| p1 `prey_after_dup` | prey's check after the repeat-fight skip | 10,542 (H0) | 50.1 (49.2-51.1) | 87.7k / 79.9k |
| p2 p1 + `prey_walk=8000` | prey keeps 8k for the walk, not a 16-layer search | 11,330 (H0) | 50.1 (49.2-51.0) | 92.8k / 86.7k |
| g1 `guard_reserve=12000` | the step guard's entry keeps 12k, not 20k, beside the fight estimate | 8,229 (H0) | 49.9 (48.9-51.0) | 61.7k / 61.0k |
| s1 `strike_floor=40000` | the strike search prices no more tiles below 40k left (anytime: best so far) | 9,933 (H0) | 50.1 (49.1-51.1) | 69.1k / 75.2k (-8%) |
| s2 s1 at 45k + `grow_floor=45000` | also grows no node below 45k | 608 (H0) | 41.3 (37.4-45.2) | |
| r1 `bank_pct=60` | banking loops keep 60% of their walk reserve | 2,672 (H0) | 48.9 (47.0-50.8) | |
| r2 `loop_pct=80` | non-banking loops keep 80% | 9,810 (H0) | 49.9 (48.9-50.9) | 78.5k / 74.4k |
| a1 `spec` | Phase 2 amortisation, below | 3,129 (H0) | 49.0 (47.2-50.7) | 22.9k / 22.5k |
| sp1 `stale_rounds=4` | stale-value prune at 0.7, below | 3,914 (H0) | 49.0 (47.4-50.5) | |
| sp2 `stale_rounds=8`, 0.8 | | 9,826 (H0) | 49.8 (48.8-50.8) | 74.1k / 73.6k |
| sp4 sp3 (more notes) at 8, 0.8 | | 20,480 (fixed) | 49.9 (49.2-50.6) | 155.7k / 156.1k |
| r1 again, fixed | | 20,480 | **50.3** (49.7-51.0) | 160.1k / 156.6k |
| r1 on `fuelbud-conf` | | 20,480 | **50.4** (49.7-51.1) | 158.5k / 154.0k |
| r1b `bank_pct=40` | | 2,236 (H0) | 48.3 (46.2-50.3) | |
| r1c `bank_pct=60, loop_pct=90` | | 20,480 (no decision) | 50.3 (49.7-51.0) | 163.3k / 156.4k |
| r3 `loop_pct=130` | non-banking loops keep 30% more | 4,936 (H0) | 49.2 (47.8-50.6) | |
| g2 `guard_reserve=30000` | the step guard keeps more | 3,304 (H0) | 48.8 (47.1-50.5) | |
| f20 `farm_floor=20000` | farm_turn below 20k left keeps last turn's group (the struck branch) | 4,357 (H0) | 49.7 (48.3-51.2) | |
| f30 `farm_floor=30000` | | 5,285 (H0) | 49.7 (48.4-51.1) | |
| ll4 `light_rounds=4` | light loop, below | 3,520 (H0) | 48.3 (46.6-49.9) | |
| ll8 `light_rounds=8` | | 6,061 (H0) | 49.3 (48.1-50.6) | |
| c1 p2 + g1 + s1 | | 20,480 (fixed) | 49.3 (48.6-49.9) | 157.0k / 157.0k |
| c2 c1 + r1 + sp (8, 0.8) | | 20,480 (fixed) | 50.0 (49.3-50.7) | 160.6k / 156.3k |
| w8 `watch_floor=8000` | the low-fuel watchdog, below | 4,903 (H0) | 49.3 (47.9-50.7) | 26.9k / 35.0k (-23%) |
| w12 `watch_floor=12000` | | 2,770 (H0) | 48.5 (46.7-50.4) | 13.2k / 20.1k |

**a1, the turn-end queue continues a cut loop.** After a turn whose non-banking loop was cut, the queue runs the farm
loop in an evaluation-only mode (`farm_speculate`: a copy of Memory, no actions, its own fuel floor) over the groups
the turn's loop did not reach, from where the turn ended, seeded with the turn's best. A group that beats it is next
turn's hint, weighed once past that turn's own cut. Identical at 100M (no loop is cut there). Real budget, pool set
(128 games): 55k loop cuts, 4,283 queue runs (the rest found no spare fuel), **401 hints (9%)**, 72 used, 52 of them
won the loop. The tail of a cut loop rarely holds a better group: the loop's oracle value is the fuel it spends, which
later work and the queue then lack, not the groups it leaves.

**Where the loop's fuel goes** (`variants/oc-fb-probe`, 100M, pool set, rounds 150-349, 70,950 loops, 15.2k a loop,
18.6 groups weighed): groups cut at the pre-facts bounds 138 each (6.9% of loop fuel); before the facts 255 (6.9%);
after the facts 831 (4.6%); after `live_steps` (the pre-value and claim bounds, the respawn wait) 1,115 (16.2%); after
`prunes(trip)` (the clear, crew work and plan, then not better) **3,282 (28.8%)**; groups valued 2,277 (34.1%). Of the
groups valued below 0.7x the loop's best, 83% had been below 0.7x in a loop within 4 rounds, and 0.7% of those were
within 5% of the best now.

**SP, the stale-value prune.** A group (not our choice or claim, not claimed, held or a Monolith, no help call) whose
value, or a bound on it, from a loop within `stale_rounds` in the same context and camp belief version is below
`stale_margin` x the best so far is skipped. sp1/sp2 recorded only the loop's last value; sp3-sp5 also the crew
branch's value, its claim bound, the solo branch's and the pre-value bound. Mean fuel at 100M -1.2..-1.5% (wide),
farm-partial-evaluation -9..-17% at the real budget.

**LL, the light loop.** 93% of consecutive loops pick the same best group, 69% of them by a 20% margin. A loop within
`light_rounds` of a full loop that chose the same group by `light_margin` (1.25x) in the same context, claims and camp
belief versions weighs only its first group (the choice) and keeps it; a light loop whose choice lost ground forces
the next loop to be full. At 100M (wide) mean fuel 49.7k against 50.9k, a decision change 1 turn in 290, but the
same-state saving is only 0.5-0.7%: the loop's first groups are the dear ones. Lost (ll4 48.3, ll8 49.3).

**W, the low-fuel watchdog** (Phase 5's "cheaper method on a short turn"). While deciding, the strike search
(`Search::grow` and its price loop), the farm loop's `room()`, `trade()` and `Pathing::route` throw `LowFuel` once fuel
left falls below `watch_floor`; `act()` catches it and plays a fallback: hit an enemy in range, else a camp in range,
else (no enemy seen) step down the approach to last turn's farm group; then the recall and the use count. Identical at
100M (16/16; +0.2% fuel for the checks). At the real budget (wide) it cut OOF turns 662 -> 490 (w8), 23% in the A/B,
and lost: a turn that runs out keeps what it already did and its plan's first actions, which beat a generic
fallback. The OOF turns it leaves are outside the watched work (`stand_lost_at`'s own loops, `act_end`, the walk).

**cen1** (`variants/oc-fb-cen2`, the census on oc-retest-clean against itself): as cen0. Mean 53.5k against 53.1k a
turn, 1,432 OOF-first turns (1,458), the gate table within a few percent (farm-partial-evaluation 54,906 firings at
40.8k left p50; step-guard-entry 13,136; prey-cut-short 3,633, -9%).

**r1 on varied maps and the panel.** `fuelbud-varied` (533200-533209, `--mix varied`): 49.9 (48.5-51.3) of 5,120.
Panel (`panel-check-514510`, 5,120 each), r1 against oc-retest-clean's own rates measured alongside (PANEL.md):

| member | oc-fb-r1 | oc-retest-clean |
|---|---|---|
| astraeus-now-1106 | 52.6 (51.2-54.0) | 53.1 (51.7-54.5) |
| panel-proteus | 64.0 | 63.3 |
| panel-demeter | 66.7 | 66.0 |
| panel-ocean-td | 81.9 | 82.1 |
| baselines/v67 | 77.9 | 77.2 |
| mean | 68.6 | 68.3 |

## Verdict

- No budgeting change wins. r1 (`bank_pct=60`) is the best: +0.35 over 40,960 own-suite games (CI about
  49.9-50.8), -0.1 varied, +0.3 on the panel mean. Level, so `variants/oc-fuelbud` is not frozen and no CHANGES entry
  is drafted; `variants/oc-fb-r1` holds it if a later combination wants it.
- The cut prize (b125 = ceiling) is a fuel-efficiency prize: the same budget moved between the farm loop, prey, the
  step guard, the strike search and the queue reads level every way it was moved, and a 25% larger budget recovers
  it all. The work to do is making the farm loop (its groups pruned after `prunes(trip)` cost 3.3k each, 29% of loop
  fuel), prey and the step guard cheaper with the same answers.
- OOF turns (~1.6 points in the gate view) are not recovered by stopping early: the watchdog cut them 23% and lost.
  What remains is fight turns: the strike search and `stand_lost_at` on 56% of OOF turns that pass no check.
