# Fuel in fights on charybdis 520 (fightfuel, 2026-11-12)

The request: fix fuel behaviour in fight scenarios, especially the Prism's (worst-case fuel, how budgets and reserves
are split, the cheaper logic that runs when fuel is short), following the four leads prismlife left open.

Base and REF: `variants/chy-life` (= bots/charybdis, CHANGES 520). Real 100k budget, rt bodies (Flp4, Mt3q), fgate
pool batch 0 for arms and profiles (parts p0-p7: 2,560 maps, 10,240 games an arm), batches 1-6 and 75-86 for gates
(REF's half cached). Results: EXPERIMENTS.md "Fuel in fights on charybdis 520".

## What was found

1. **The Prism's own fuel no longer decides anything.** The Prism alone at 200k (everyone else at 100k) reads -0.20
   ±0.45 with its deaths -4%; before 520 the same arm was +0.68 with deaths -19%. Its step guard, escape plan and chase
   verdict made free where their fuel tests cut them read -0.09, +0.12 and -0.40. 520's carry fix took the Prism's share.
2. **The rest of the prize is the team's, and it is spread thin.** Everyone at 200k is +1.52 ±0.46 (Prism deaths -10%);
   the other champions alone +1.20. By part, none separable from noise: turns with an enemy in sight +0.56, turns
   without +0.13, rounds 1-100 +0.68, the first turn +0.18, no turn running out (every gate still cutting) +0.34, the
   six main gates free +0.31.
3. **One gate has a price: the step guard (+0.89 free, +0.74 for the non-Prism champions alone), and it cannot be
   bought with the turn's own fuel.** Its entry keeps back 35-45k for work that costs 0.4k at the median (9k on the
   turns it is cut); a cut turn ends decide with 19-20k unused. Three staged gates that keep back only what the turn
   spends after the guard (20k, 16k, 12k) pass 45% more placings and are level on 122,880 games each (-0.11, -0.07,
   +0.05, ±0.3): the guards they add pay for themselves in turn-order cuts and out-of-fuel turns. 74% of the cut
   placings would have guarded nothing.
4. **Turns that reach decide's goal steps with too little to finish them were run out for nothing.** With under 4k
   left at the goal steps, or under 6k at the siege and farm, the turn ran out 98% and 99.7% of the time: 0.7 turns a
   game, a ninth of all out-of-fuel turns, each losing its posts (claim, bag, turn order, the memory next turn's damage
   reads) and its recall. Not starting the step (`chy-gs`) is identical at 100M (52/52 wide replays), takes
   **out-of-fuel turns down 10%** at the real budget and is level (49.94%, 49.80-50.09, of 122,880 gate games).
5. **The four open leads are closed.** Heavy fight turns: item 1. Carry fields made at the turn's end (`chy-cf2`):
   +0.14 ±0.20 on batches 1-6, -0.00 ±0.14 held out on 75-86 (368,640 games in all): level. Fuel tests that guard
   cached results: the audit found none left; the step guard's entry over-reserves but relaxing it is level (item 3).
   Escape planner gate: the plan free where the gate cuts it reads +0.12 ±0.45 with Prism deaths -3%: a cheaper plan
   would buy nothing.

## Where a fight turn's fuel goes (profile, debug builds at 100k; `instr.py`, `fzread.py`)

Inclusive fuel a turn with an enemy in sight, finished turns (the Prism | the others), 2,560-5,120 games:

| scope | Prism, 3+ enemies in sight | others, any enemy in sight |
|---|---|---|
| world update | 10.4k | 9.0k |
| want_home (stand_lost_at inside) | 14.2k, p90 26k (11.1k) | 10.1k, p90 20k (7.0k) |
| strike search, when it runs (31% / 25% of turns) | p50 5.5k, p90 30k, p99 43k | p50 4.9k, p90 26k, p99 42k |
| prey and its chase verdict (58% / 61%) | p50 9.0k, p90 30k | p50 1.9k, p90 21k |
| retreat, when it runs (15% / 22%) | p50 19k, p90 38k | p50 26k, p90 40k |
| farm, when it runs (55% / 50%) | p50 8.9k, p90 31k | p50 21k, p90 39k |
| turn order | 4.2k | 3.2k |

- Out-of-fuel turns: 5.9 a game, 4.8 with an enemy in sight, 0.95 the Prism's (0.04 in its retreat). By step: farm
  1.85 (half entered with under 10k), strike search 0.90 (entered with 43k at the median), the turn's tail 0.73,
  retreat 0.63, turn order 0.19. By round the rate falls from 2.1% of fight turns in rounds 21-50 to 0.3% after 400.
- With 3+ enemies in sight the Prism runs out on 1.2% of turns and ends decide under 10k on 8.4%.
- Cuts per 1000 fight turns (the Prism | the others): farm-partial-evaluation 65 | 54, chase verdict not built 62 | 26,
  step-guard-entry 49 | 70, prey-cut-short 34 | 22, escape slack pass 27 | 31, turn-order 21 | 21, escape plan 11 | 21.
  A third of the Prism's chases are taken without the verdict.
- The Prism's deaths follow its retreats (5.7% of retreat turns near an enemy are followed by its death within 3
  rounds, 0.1% of farm and chase turns: `hazard.py`). Its big-fight retreats (3.9 enemies in sight on average) are the
  ones that skip the escape plan: world update 11k and want_home 27k leave under 50k at the step. With the plan free
  there, nothing changes (h16).
- By champion type the pressure is even (0.3-1.1% of fight turns run out). By function, heavy turns are flat: the
  largest self cost is farm_turn's 7.5%, then make_field 4.2% (`lprof.sh`, tools/fuel/fuelprof).

## Budget arms (`mkff.py`, `mkarm.sh`, `arm.sh`, `quick.py`)

Debug builds under `--fuel 200000`, every instance charging itself back to 100k (`tools/fuel/cap_variant.py`) but for
the arm's exemption; paired with `ff-base` on the same 10,240 games; a paired read moves by about ±0.45.

| arm | win, points | Prism deaths a Prism game (base 0.333) | out-of-fuel turns (base 61.4k) |
|---|---|---|---|
| everyone at 200k (`ff-all200`) | +1.52 | 0.299 | 0.4k |
| the Prism alone at 200k (`ff-p200`) | -0.20 | 0.320 | 52.6k |
| everyone but the Prism at 200k (`ff-o200`) | +1.20 | 0.321 | 8.7k |
| 100k credited after the world update, an enemy in sight (`ff-fight`) | +0.56 | 0.306 | 13.1k |
| the same with none in sight (`ff-calm`) | +0.13 | 0.326 | 48.0k |
| the first turn at 400k (`ff-t1`) | +0.18 | 0.334 | 57.3k |
| rounds 1-20 at 200k (`ff-r20`) | +0.35 | 0.337 | 54.8k |
| rounds 1-100 at 200k (`ff-r100`) | +0.68 | 0.328 | 43.7k |
| no turn runs out, gates as at 100k (`ff-noof`: fuel() reads 100k low, 100k of overdraft) | +0.34 | 0.324 | 3.1k |

Gates made free: the test passes, 90k is credited where it would have cut, and the fuel is set back after the work, so
the rest of the turn sees what a cut would have left (`ff-h*`). A first version refunded only after the work, so the
capped turn ran out inside it (out-of-fuel x3, `ff-g*`): discarded.

| gate free | win, points | Prism deaths | freed a game; fuel left at the gate; the work (p50, p90) |
|---|---|---|---|
| all six (`ff-h63`) | +0.31 | 0.324 | |
| step guard: entry, sim, look (`ff-h4`) | +0.89 | 0.331 | 82; 36k; 8.9k, 25k |
| step guard, the Prism's only (`ff-h4p`) | -0.09 | 0.328 | |
| step guard, the others' only (`ff-h4o`) | +0.74 | 0.335 | |
| escape plan and its slack pass (`ff-h16`) | +0.12 | 0.329 | 18 + 39; 43k; 12k, 16k |
| chase verdict (`ff-h2`) | -0.40 | 0.336 | 35; 44k; 12k, 16k |
| prey's candidates (`ff-h8`) | +0.08 | 0.331 | 21; 38k; 22k, 51k |
| farm loop (`ff-h1`) | +0.16 | 0.327 | 99; 30k; 7.7k, 27k |
| turn order (`ff-h32`) | -0.21 | 0.340 | 25; 8k; 3.9k, 7.9k |

## The step guard

- `step_guard`'s entry needs `fight_cost_estimate()` (10k or more) + `act_reserve` (20k) + its costliest placing
  lately. A placing costs 0.4k at the median (p90 7.9k, p99 17k): covers and exposures 0.4k (p99 9.9k), a new fight
  4.4k (p90 7.8k, p99 12k), needed on 17% of placings. After the guard a turn spends 12.6k at the median (p75 15k, p90
  18k, p95 21k): `act_reserve` is its p90-95 (`guardafter.py`).
- Cut at the entry 60 times a game (the others 54, the Prism 7), with 34k left at the median; the cut placings would
  have cost 8.9k (two fights) and left 16k or more in 75% of cases. 26% of them guard a tile, 8% of the Prism's
  (`ff-h4log`).
- `sg-a20`, `sg-a16`, `sg-a12` (`mksg.py`): the entry keeps AFTER and an exact look's price a foe, each new fight its
  own estimate and AFTER. On a profiled copy of `sg-a16`: entry cuts 55 -> 4 a game, sim cuts 0.7 -> 29, new fights 54
  -> 74, turn-order cuts 17.6 -> 22.3, out-of-fuel turns 5.25 -> 5.55. Gates against chy-life, batches 1-6:

| candidate | fresh | maps (games) | Fish / Mite |
|---|---|---|---|
| sg-a20 | -0.07 ±0.30 | 15,360 (122,880) | -0.20 / +0.06 |
| sg-a16 | -0.11 ±0.31 | 15,360 (122,880) | -0.28 / +0.07 |
| sg-a12 | +0.05 ±0.31 | 15,360 (122,880) | -0.22 / +0.33 |

  As on astraeus (GATE-PLACEMENT item A) and ocean (fuel ceiling, 2026-11-10): the guard is worth having only at no
  cost; what would pay is a guard whose verdict needs no new fight on these turns.

## Goal steps not started on fuel they cannot finish (`chy-gs`)

`decide` returns before its goal steps (a bag, a shopping trip, a chase, a contest, a siege, the farm) with under
`goal_least` (4k) left, and before the siege and farm with under `farm_least` (6k). The turn's tail, turn order and
posts keep their own checks. From `goalentry.py` (5,120 debug games, turns by the fuel left at the step):

| fuel left | at the goal steps: turns a game, ran out | at the siege and farm: turns a game, ran out |
|---|---|---|
| 0-2k | 0.15, 100% | 0.17, 100% |
| 2-4k | 0.21, 97.3% | 0.21, 100% |
| 4-6k | 0.25, 93.3% | 0.25, 99.1% |
| 6-8k | 0.27, 85.5% | 0.29, 85.1% |
| 8-10k | 0.35, 62.6% | 0.36, 53.7% |
| 10-15k | 1.20, 29.0% | 1.17, 21.9% |

- A turn that runs out there resumes next round inside the step, finds itself stale and unwinds past the posts: the
  claim, bag and turn order are not posted, `Memory::round` and `health` are not updated (next turn reads no damage
  and no engagement), no recall starts, and the turn end and queue are skipped.
- 100M: 52/52 `wide` replays identical against charybdis (`bench.py --opp charybdis`), +9 fuel a turn.
- Real budget, release, batch 0 (10,240 paired games): out-of-fuel turns 62,640 -> 56,061 (**-10.5%**), win -0.09
  (z -0.48, 3.5% of results change), Prism deaths 0.331 -> 0.324, team deaths 4.53 -> 4.42.
- Gate against chy-life, batches 1-6: 49.94% (49.80-50.09) of 122,880 (Fish 50.00, Mite 49.88; ZONE, level);
  out-of-fuel turns 427,568 -> 384,710 (-10.0%, 6.63 -> 5.96 a game).
- Shipped as CHANGES 521: fuel-aware and identical at 100M, as CHANGES 495's tail checks were.
- Higher lines were not taken: from 6k a third to half of these turns still finish (the farm's struck branch, a cut
  loop's walk on), so a skip there trades actions for posts.

## Not built

- The turn's tail still runs out 0.68 times a game: the second strike search 0.19 (entered with 12k at the median),
  the ward 0.12, heal and shield 0.11, the tribute habit's want_home 0.07. Each step's `least` is its cheap path's.
- The strike search runs out 0.9 times a game from 43k at the median (read 5.4k, grow 3.4k, price 4.7k at the median;
  p99 45k in all): an anytime price loop was level on ocean (fuel ceiling, 2026-11-10).
- A fall-back at the guard's cut by roster (open where we outnumber, closed where we do not): the cut placings guard
  a tile 26% of the time; untried, and below what a gate of this size can read.

## Rebuilding

Variants live in the gitignored `bots/variants/`.

- Profiles: `./copybot charybdis variants/fz-prof && python3 instr.py bots/variants/fz-prof/src`, `dbg.sh fz-prof`
  (debug games on batch 0 part p6, replays kept), then `fzread.py BATCHGLOB [--who=prism|other|all] [--seen=N]
  [--dec=R]`, `cuts.py`, `hazard.py`, `oofentry.py`, `farmoof.py`, `guardafter.py`, `goalentry.py`, `srch.py`,
  `cmpcuts.py NAME=GLOB...`. `fz.h` is the scope recorder; `instr_ids.py` the scope names.
- Budget arms: `python3 tools/fuel/cap_variant.py variants/chy-life --run-fuel 200000 --name ff-capall`, copy it to
  `variants/ff-base`, `python3 mkff.py bots/variants/ff-base/src`, `mkarm.sh NAME KNOB=VALUE...`, `drive.sh J ARM...`
  (`arm.sh` each: debug, `--fuel 200000`), `quick.py ff-base ARM...`. `freed.py` reads a logging arm's FREE lines.
- Candidates: `mksg.py SRC AFTER` (staged step guard), `patches/chy-gs.patch`, `patches/chy-cf2.patch`; `gate.sh CAND
  [FIRST N]` runs fgate against chy-life on the cached batches (`FUELARG="--fuel 100000" gate.sh CAND 75 12` for the
  held-out ones). `lprof.sh BOT OUT MAPLIST` is the per-line profile.
