# Lane B: the farm group loop under a cut (2026-11-10)

Base `bots/variants/oc-ceil-ref` (ocean d4f6e68a6, CHANGES 495). Lane prefix `fgb`. Tools in `laneB-tools/`, run
scripts in `laneB-run/`.

## Measurement 1: the loop's share of the farm's prize

`variants/fgb-fzloop` = `oc-fz2-dev` with `FreeScope<9>` around the group loop only (from `int k = 0` through the
loop's closing brace), `fz_scope = 9`. Played as the other fz2 arms: 10M quantum, gates reading the 1x budget, against
oc-ceil-ref on `merged/fceil-2020` (20,480 games, release, own drafts). Paired by map (`laneB-tools/pair.py`) against
`replays/ab/fz2-view/fceil-2020.log`:

| freed | win % | paired diff (95%) | results changed |
|---|---|---|---|
| farm (`farm`, `farm_reprice`; step 0) | 52.75 | +1.11 ±0.89 | 45% |
| the group loop only (`fgb-fzloop`) | 52.29 | **+0.65 ±0.88** | 43% |
| farm against loop only | | +0.46 ±0.84 | 37% |
| the loop finished, the rest of the turn as at the cut (`fgb-flcut`, release) | 52.16 | **+0.52 ±0.87** | 42% |
| farm against loop finished | | +0.59 ±0.87 | 40% |

In `fgb-fzloop` the loop's free fuel also reaches the work after it (the refund holds for the rest of the turn).
`fgb-flcut` (measurement 2's diagnostic, release build: its traces compiled out) removes that: an uncut loop gets
no refund, and after a cut the rest of the turn reads exactly the fuel it had at the view's cut. So **finishing every
cut loop is worth +0.52 ±0.87**, not significant, and under half of the farm's +1.11. This agrees with lane C's
`fgc-fzpre` (+43k at farm entry, cut loops -77%, +0.31).

**Go / no-go: no-go.** The whole prize of this lane is about half a point, within noise. A lever that finishes a
fraction of the cut loops would be worth a tenth of a point, which no A/B here can see. Candidate 1 below was built
before the second run finished, and its own check shows it does not move the loops it targets.

## Measurement 2: what a cut loop chooses against the whole loop

`variants/fgb-flcut` (diagnostic, from fgb-fzloop): the loop runs free (`FreeScope<9>`); a snapshot is taken where the
1x view (`fuel_outside()`: fuel() without the open scope's refund) would have cut it, by `room()` or a field/hop
`fuel_ok`. After the loop the rest of the turn reads exactly what it would have at the cut (or, uncut, gets no
refund), so play outside the loop is the real bot's with the whole loop's choice. Its own bookkeeping is charged to
`flc_diag` and refunded. Debug builds, 1,280 games (640 maps from `fceil-2020`) at 10M against oc-ceil-ref; parser
`laneB-tools/flcut_an.py`. Round 1 (`replays/ab/fgb-flcut-dbg`) and round 2 (`-dbg2`, with parts) agree; numbers from
round 2 unless noted.

- **7.4% of loops are cut** (150k of 2.04M; 196k cut loops in the traces).
- **26% of cut loops are not the loop's:** cut at k = 0 with the free loop also stopping at 0 (48k), because the fuel
  at entry is already under the loop's reserve. 99% of them have no pick at full either. That is pre-loop fuel.
- **Of the rest (the free loop went further), the pick is the same in 82.3%.** It differs in 28k (17.7%, ~22 a game
  per team):
  - full pick: S 58%, J (share) 26%, C 6%, K 6%, H 3%;
  - by value the cut's pick is a median 0.63 of the full pick's (p25 0.40);
  - the full pick lies at position k (17%), k+1 (14%), k+2 (11%): one more group reaches 21% of differing picks, two
    34%, four 54%, eight 78%. A position past the cut costs a median 775.
  - the cut loop's prefix spends a median 13.4k (k median 5 of 21), the free loop 23.0k (to position 16).
- **Lead (c), a cut with no pick:** k > 0 and nothing set: 7.0k (3.6% of cut loops). The bot then only steps off a
  respawning group (`leave_respawning`). The free loop has no pick either in 54%; where it has one it is spread over
  positions k..k+9 (k: 584, k+1: 503, ...), never last turn's choice (which was weighed first and rejected). No
  fallback picks it: **no-go** (~2.6 such turns a game per team, and no rule finds the pick).
  - With k = 0 and a free loop that went on (~0.7k), the full pick is last turn's choice in 70%: the existing
    walk-on is right.
- **Lead (d), last turn's values for unweighed groups:** D = the unweighed group whose last value (within 5 rounds)
  beats the cut's pick. It exists in 13.8% of cut loops; it is the full pick in 1.3k and wrong where the cut's pick was
  right in 24.9k. 91% of the D are not priced at all by the whole loop now (pruned or ineligible this turn).
  **No-go**, even as an extra candidate.
- **Prefix fuel by part (mean per cut loop):** live_steps 1.4k (4.7 calls), plan_crew 1.9k (0.29 claimed + 0.33
  crewable calls), crew_work 1.0k, min_camp_damage (clearing) 0.65k.
- **Prefix fuel by the iteration's furthest stage:** pruned before facts 12.5% (615 each), lost after steps 9% (1.5k),
  lost after the trip bound 10% (1.5k), claimed lost 7% (3.8k), claimed and set as the share 15% (9.9k each), priced
  to the end and lost 22% (3.2k), priced to the end and set best 20% (3.7k).
- **Lead (a), crew plans across turns** (every plan_crew call, all loops; a stale plan is priced through the same
  value formula and decision):
  - claimed: 626k calls, 2.35k each; 79% have a plan from the round before. The plan is identical in 53%, the value
    within 2% in 87%. The decision flips in 0.43% (age 1), **0.19% with the same claimers**;
  - crewable: 251k calls, 2.78k each; flips 0.96%, **0.88% with the same claimers**;
  - reusable (age 1, same claimers): 644 fuel a loop over all loops; in cut loops 578 a prefix, but concentrated:
    present in 16% of them, ~5k where present.
  - Exact keys (same position, belief version and claimers) match in 4% of calls: an exact memo would almost never
    hit, as the brief expected.

## Candidate 1: `fgb-plan` (lead a), built, does not change what it targets

[fgb-plan.patch](fgb-plan.patch) against oc-ceil-ref. In farm_turn, `crew_plan(g, expect)` replaces both plan_crew
calls. On a loop with under `plan_reuse_margin` (30k) above its reserve, it reuses the plan made for g last round when
our output, the group's claimers in sight (`crew_claimer_bits`) and `expect` are unchanged. A reused plan is not kept
again, so a plan is at most a round old. Traces (debug only): `SHORTCUT farm-plan-reused`, `FLK round champion k n
pick` at each cut (also in the trace-only base `fgb-trbase`).

- **Stale-plan error** (measurement 2): with the same claimers the pick flips in 0.19% (claimed) / 0.88% (crewable) of
  calls.
- **100M identity:** 96/96 replays identical against oc-ceil-ref (`research/fuel-2026-11-10/tools/maps-id.txt`,
  bench in `laneB-run/bench/`); fuel +0.13% (the check's claimer bits and fuel read).
- **Mechanism check** (debug, real budget, 1,280 games each on the 640-map subset against oc-ceil-ref; `laneB-tools/
  mech_an.py`):

| copy | reuses a game | cut loops a game | k mean (median) | k = 0 | OOF turns (cand / ref) |
|---|---|---|---|---|---|
| fgb-trbase (base + traces) | 0 | 144.8 | 7.81 (4) | 25.5% | 14,583 / 14,584 |
| fgb-plan | 64.4 | 144.5 | 7.62 (4) | 26.1% | 15,633 / 14,831 |

  It fires, but cut loops neither fall nor reach further. In cut loops the reusable fuel is 578 a prefix and is
  present in only 16% of them, so the saving lands mostly in loops that were not going to be cut.
- **Risks:** a stale plan misprices a share after an ally's position or health changes (claimers' arrival and the
  expected allies are not in the key). OOF +7% is inside the ±5% noise of 1,280 games, but it points the wrong way.
- **Not a past failure re-run:** it prunes nothing and keeps no stale value (unlike the stale-value prune) and does
  not carry the loop across turns. But it fails on its own terms.
- **Recommendation:** do not gate it. At most keep it for stacking, as fb1 was.

## Other leads

- **(b) a cheaper order inside a group:** every loop's fuel by the iteration's furthest stage (round 3, `-dbg3`,
  FLSEG): groups pruned before facts 442 each, 32% of all loop fuel; a claimed share set as the share 7.9k (crew_work
  1.9k, plan 2.4k, after the plan 1.2k, steps 1.2k); priced to the end and lost 2.7k (clearing estimate 1.0k). The
  crewable bound already skips the plan in most losing groups (60% of crewable plans lose, ~550 a cut prefix). What
  is left is exact speed-up work, not ordering, and the prize above does not pay for it.
- **(c)** and **(d):** no-go by measurement 2 (above).

## Open

- The farm's prize sits outside the loop: farm against the finished loop reads +0.59 ±0.87, and lane C sees the
  same. That includes `farm_reprice` inside continue_recall, and the step guard's and route searches' fuel that the farm
  calls.
- 26% of cut loops stop at k = 0 because the fuel at entry is already under the loop's reserve: those are pre-loop
  (lane C).

## Files

- Copies: `variants/fgb-fzloop` (scope 9 refund), `fgb-flcut` (diagnostic and loop-finished arm), `fgb-plan`
  (candidate), `fgb-trbase` (base + FLK trace).
- Tools: `laneB-tools/pair.py` (pair two ab logs by map), `flcut_an.py` (FLCUT/FLCREW/FLPART), `mech_an.py`.
- Runs: `laneB-run/*.sh` and outputs; results `replays/ab/fgb-{fzloop,flcut-rel,flcut-dbg,flcut-dbg2,flcut-dbg3,
  mech-trbase,mech-plan}/`.
- The debug runs' batches hold every replay (`--keep-replays 0`, ~1.3k each): deletable once read.
