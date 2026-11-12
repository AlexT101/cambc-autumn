# Keeping the Prism alive without making it passive (prismlife, charybdis = 519, 2026-11-12)

The request: Prism deaths are a major cause of our losses, and making the Prism safer has made it passive. Find a
fresh way to keep it alive, and keep it from running out of fuel mid-fight.

Base and REF: `variants/charybdis-p3` (= bots/charybdis, CHANGES 519), re-frozen as `variants/chy-519` for the gates.
Everything below is at the real 100k budget against the rt bodies (Flp4, Mt3q) unless it says otherwise.
Results: EXPERIMENTS.md "Prism deaths on charybdis".

## What was found

1. **The Prism dies in failed retreats, not in fights it should have refused.** 86% of its turns straight before a
   death are retreat turns; 74% of its retreats begin at 70%+ health (a lost stand or a pack's zone, not the recall
   line); 2.5% of retreats reach our spawn (the walk home is 24 steps on average).
2. **Its retreat policy is at a local optimum.** Less retreat loses (no lost-stand retreat: deaths x2.2, -6.05 points).
   More retreat loses too (retreat on until no enemy can reach within 3 or 5 turns: deaths -16 to -24%, -2.5 to -4.8
   points; the same only below 20, 50 or 100 gems: -0.4 to -1.1). The Prism's time in the field is worth more than the
   deaths that leaving saves. Six micro changes were level or worse (table below).
3. **A fifth of its deaths are fuel.** With the Prism alone at 200k (every other champion at 100k) its deaths fall
   19% and it collects 10.6% more gems, the team's total unchanged. Across every fuel arm its deaths follow its gems.
4. **The starved step was a fuel test that guards nothing.** Farm's carry picks (an ally's capture the Prism takes over,
   'G'; one left for it, 'L'; a clear under way, 'Q') were dropped unless the fuel left covered a new distance field
   and the loop's reserve (32-55k), though `Pathing::to_group` is cached for the game and a made field reads free.
   Skipping the test when the field is made gives the Prism +8% gems and -8 to -13% deaths, with out-of-fuel turns
   unchanged (`chy-carry`).
5. **Two changes that cost the Prism no time stack on it** (`chy-life`): it leaves a stand it falls in even where the
   team wins (as Cassi and Issac do), and its shards are Health until it is as sturdy as the sturdiest base body (a
   Focus shard is 8 Focus; a carried gem is 1.5, and it carries a median 67 at round 150 and 170 at round 300).

## How the Prism dies (REF, 2,560 games: fgate batch 0 parts p0-p1, both bodies)

`deaths.py`, `onset.py`, `xtab.py`, `zones.py` on the extraction; `dl.py`, `rruns.py`, `reasons.py`, `trace.py`,
`rstart.py`, `homeward.py`, `yoyo.py`, `allies.py` on debug builds (`variants/pl-trace`, 1,280 games each).

- 0.373 deaths a Prism game. Games without one are won 92.9%, with one 60.4%, with two or more 31.1%.
- 86% of its turns before a death are retreats (`R`); 8 rounds before, 46% already are.
- Retreats: 5-7 a game, mean 4 rounds. By trigger: lost stand 76% (5.0% die, 58% of retreat deaths), pack zone 11%
  (16.5%, 28%), recall line 7.5% (11.6%, 13%). 74% begin at 70%+ health.
- Its own model sees it coming: where its turn ends with `worst_damage` at 70%+ of its health it dies before its next
  turn 7-65% of the time. On the last turn before a death 60% had every step lethal and 10% were stunned; two turns
  before, 87% stood on a tile the model called survivable. It is run down over 4-12 rounds, not one-shot.
- With an enemy in sight nearer our spawn than the Prism (15% of retreats) 13.5-17% die, against 4.3%.
- Alone (no ally within 6) the hazard is 0.63 deaths per 1000 rounds against 0.39 with two or more allies; in the middle
  band of the map 1.13 against 0.56. Below 100 gems it is 0.78, at 300+ 0.21.
- Half the deaths follow a chain with a return to work between retreats; half are one straight chase.
- It sees its killers: 73-89% of the hitters 8-2 rounds before the death are in its own sight; a teammate alone sees
  5-12%.
- The linear risk price is calibrated: it takes 0.276 of `worst_damage` on turns ended in reach (priced at 0.234).

## Arms that did not win (variants/pl-*, knobs in `patches/pl-base.patch`; `mkarm.sh`, `arm.sh`, `quick.py`)

Paired with base on the same games: set a = batch 0 parts p0-p1 (2,560 games), set b = p2-p5 (5,120). Win change in
points, Prism deaths a Prism game against base 0.373 (a) and 0.425 (b).

| arm | change (Prism only) | win a / b | deaths a / b |
|---|---|---|---|
| pl-nostand | want_home ignores a lost stand | -6.05 / - | 0.813 / - |
| pl-nopack | drawn_home ignores a pack's zone | +0.20 / - | 0.404 / - |
| pl-pur3 | pursuit_steps 3, every champion | +0.47 / - | 0.375 / - |
| pl-m50, m60, m75, m90 | Safety::lethal against 50-90% of health | +0.62, +0.74, +1.13, +0.62 / m75 -0.35 | 0.382, 0.380, 0.368, 0.375 / 0.438 |
| pl-flee1 (flee2: everyone) | an enemy between us and home: the retreat walks away from the enemies | +0.04 (-0.86) / +0.18 (+0.18) | 0.374 (0.366) / 0.441 (0.424) |
| pl-dis3, dis5 | a retreat goes on until no enemy reaches within 3 or 5 turns | -3.32, -4.80 / -2.46, -3.01 | 0.322, 0.311 / 0.349, 0.323 |
| pl-dl20, dl50, dl100 | dis3 only below 20, 50, 100 gems | -0.43, -0.78, -1.45 / -0.74, -0.64, -0.94 | 0.352, 0.348, 0.333 / 0.400, 0.376, 0.362 |
| pl-shop2, shop4 | shop trips at 2x and 4x the gain | -0.47, -1.64 / -0.61, -1.41 | 0.376, 0.375 / 0.424, 0.403 |
| pl-ws1 (ws2: every caster) | a retreat walk worth only the damage it avoids | +0.31 (-0.70) / -0.41 (-1.37) | 0.401 (0.400) / 0.450 (0.462) |
| pl-pf30, pf38 | escape plan from 30k or 38k fuel, not 50k | +0.04, +0.35 / -0.29, +0.20 | 0.384, 0.368 / 0.432, 0.417 |
| pl-gf1 (gf2: everyone) | the work guard worked out before the goal | +0.94 (-0.74) / +0.10 (+0.18) | 0.365 (0.371) / 0.410 (0.425) |

- pl-m75's +1.13 on set a did not repeat (set b -0.35): a 2,560-game win read moves by about a point. Deaths are the
  steadier mechanism read (about ±5%).
- By the enemy's draft (`split.py`) no cell has the longer retreat winning.
- A recall kept from the tile would have landed in 75% of the hurt, out-of-reach states (`recallcf.py`), but those
  states hold only 3% of the deaths that a landing would have spared.

## Fuel (`oofact.py`, `oofphase.py`, `pf.py`, `pq.py`, `shortcuts.py`, `fk.py`, `escskip.py`, `econ.py`)

- The Prism runs out on 1.6% of its fight turns (hit by a champion this round or the two before): 0.34 a game. The
  cast still goes out (28.8% of those turns, 25.9% of the others); the walk is what is lost (acted 45% against 95%).
  Death within 3 rounds is the same (6.0% against 6.1%).
- Its turn needs over 100k on 2.1% of turns when allowed 200k: 0.8% with no enemy in sight, 8% with three, 21% with
  four or more (`variants/pl-capnpq`).
- With an enemy in sight: world update 10.8k, want_home 15k (p90 27k), strike search 2.4k (p90 20k), goal 18k (p90
  45k), turn end 5k (`variants/pl-prof`). Shortcuts per 1000 such turns: farm-partial-evaluation 61, step-guard-entry
  54, prey-cut-short 35, turn-order 20. A quarter of its planned retreats skip the escape plan below 50k.
- Budget arms (debug builds, 5,120 games, every instance charging itself back to 100k under `--fuel 200000`:
  `tools/fuel/cap_variant.py`, `patches/pl-capnp-on-capall.patch`, `pl-free-on-capall.patch`):

| arm | Prism deaths | Prism gems | win |
|---|---|---|---|
| everyone at 100k (pl-capall) | 0.411 | 544 | 81.68% |
| the Prism alone at 200k (pl-capnp) | -18.8% | +10.6% | +0.68 |
| everyone at 200k | -15.0% | +9.8% | +1.76 |
| refund of one scope: goal, want_home, strike search, step guard, retreat, turn end, turn order | -0.6 to +5.0% | -0.6 to +0.4% | -0.16 to +0.49 |
| refund of the world update | -6.2% | +3.6% | +0.72 |
| 30k credited at the turn's start | -15.0% | +8.4% | +0.75 |
| 30k credited before the goal | -11.4% | +8.1% | +0.5 |
| 30k credited after farm's loop | -8.5% | +8.2% | +0.75 |
| 30k credited after decide | +0.9% | -0.1% | +0.65 |

  A refund comes after its scope has run, so it relaxes no test inside it; a credit does. The credit after farm's loop
  recovers the gems: the loop itself is cut on only 6.4% of the Prism's turns (`fk.py`), and what follows it are the
  carry picks behind `fuel_ok(full_field_cost_estimate() + loop_reserve())`.
- The team's `.fuel` files do not list a round's turns in priority order (`ordercheck.py`: the Prism's entry is where
  that order puts it in 8-12% of rounds). Per-champion fuel is read from prints inside the bot here, not from them.

## The candidates

- **`chy-carry`** (`patches/chy-carry.patch`): `Pathing::group_ready` / `group_walking_ready`; farm's 'G', 'L' and 'Q'
  picks, `prism_eta` and `leave_for_prism` hold fuel back only for a field still to make. Identical at unlimited fuel.
- **`chy-life`** (`patches/chy-life-on-carry.patch`): chy-carry, and
  - `stand_lost_at` and `step_guard` count the Prism's own fall as Cassi's and Issac's (pl-falls);
  - `best_emblem`: the Prism's shards are Health below the sturdiest base health, 1200 (pl-hp11; the first two
    emblems). One, two, three or every emblem in Health all cut deaths 5-8%; three or more start to cost wins.

| arm | win a / b | Prism deaths a / b | Prism gems |
|---|---|---|---|
| pl-cf1 (the Prism's picks) | +0.27 / +0.59 | 0.326 / 0.392 | +8.4% / +7.6% |
| pl-cf2 (and the turn-end queue makes the fields) | +0.55 / -0.27 | 0.328 / 0.398 | +9.7% / +9.4% |
| pl-cf3 = chy-carry (and the allies' side) | +0.23 / +0.59 | 0.324 / 0.392 | +8.4% / +7.4% |
| pl-falls | +0.04 / -0.04 | 0.357 / 0.395 | |
| pl-hp9, hp11, hp13, hp15, hpall | +0.08, +0.23, +0.16, +0.78, +0.08 / +1.35, +0.21, +0.12, -0.51, -0.61 | 0.373, 0.344, 0.346, 0.339, 0.346 / 0.400, 0.406, 0.406, 0.415, 0.400 | |
| pl-fh11 (falls + hp11) | +0.00 / +0.21 | 0.329 / 0.368 | |
| pl-all = chy-life | +0.86 / +1.09 | 0.305 / 0.351 | +7.6% / +8.4% |

Out-of-fuel turns: base 15,329 (a) and 30,211 (b); chy-carry 15,384 and 30,276; chy-life 15,018 and 30,614. The Prism's own on set a: out-of-fuel fight turns
695 (base), 726 (chy-carry), 589 (chy-life); with an enemy within 8: 1,750, 1,815, 1,681.

Gates against `variants/chy-519` (fgate, from batch 1: batch 0 chose the arms; fresh units, points):

| candidate | fresh | maps | Fish / Mite | ladder | verdict |
|---|---|---|---|---|---|
| chy-life | +1.23 ±0.35 | 15,360 (122,880 games) | +1.49 / +0.97 | +1.20 | ACCEPT at the screen (batch 3), LIVE BAR H1 after 6 batches (LLR 4.82) |
| chy-carry | +0.59 ±0.25 | 17,920 (143,360 games) | +0.74 / +0.42 | +0.39 | NARROWED: a gain (low LLR +11.0), short of the accept bar alone |

`variants/charybdis-p3`'s cached gate runs predate its last edit (the gate refuses them), so the reference is a fresh
freeze. A head-to-head on 40 fresh suites (`maps/suites/chy-life`, seeds 5412000-5412039) was started and cancelled
when the gate accepted. Shipped as CHANGES 520.

## Rebuilding

Arms live in the gitignored `bots/variants/`: `./copybot variants/charybdis-p3 variants/pl-base`, `patch -p1 -d
bots/variants/pl-base < patches/pl-base.patch` (paths start at `charybdis-p3/src`), then `mkarm.sh NAME KNOB=VALUE...`.
`arm.sh NAME [OUT]` plays an arm on set a (`PARTS=p2,p3,p4,p5` for set b) and writes each game's outcome to
`~/tmp-offload/prismlife/out/`; `quick.py REF ARM...` and `econ.py REF ARM...` compare them. `armdbg.sh` is the same
for debug builds (the self-capping copies), `dbg.sh` plays debug games for stdout traces, `mech.sh` plays and extracts.
