# Does our draft change the result against the real Fish and Mite? (2026-11-11)

Brief: the morning's [draft nudges](../draftnudge/README.md) were priced against bodies that do not fight like the
real teams ([fishfight](../fishfight/README.md), [overruns](../overruns/README.md)). Ask the live games instead:
the pair above all, then any champion or composition the data singles out. Build a per-opponent nudge only on a
clear, explainable effect.

**Answer: no. The live record shows no draft effect against either team that it can separate from zero, for the
pair or for any other champion. Nothing was built and no games were played.**

- Our draft changed at only three versions (v81, v83, v115); v83 to v114 drafted the same team in every cell. The
  three steps, read as changed cells against unchanged cells, are level to within ±11 points a changed cell.
- The pair is not what real Fish punishes beyond its body: it dies early as often against the body (0.31 a game)
  as against Fish (0.35). The live excess falls on Prism, Willow, Marcella and Ren, and no reading prices Prism or
  Willow lower against Fish.
- A live pair could not read a nudge either: one that changes 15% of cells leaves about 38 informative cells an
  opponent, about ±20 points on them.

## Data

- Live scrims (`research/ladder-scrims-2026-11-06/data/games.jsonl`, fillers and repeats dropped): 9,525 games
  against Fish and 9,950 against Mite on the 256 (map, side) cells. Fish is one bot throughout (r1 = r2); Mite has
  six pins. Games are deterministic, so a version adds one game a cell.
- The same step against the nine other teams of the v113/v115 panel (2,022 cells in all).
- Ranked ladder games of every team against Fish (2,812) and Mite (2,826), 11-06 to 11-11, from the big-arm
  archive's local copy (`~/tmp-offload/draftnudge/work/ladder-all.jsonl`), and the same teams' 48,231 games against
  other top-30 teams.
- v115's 520 decoded live games and the same bot's 512 against the bodies on the same maps (overruns' death tables).

Intervals are 95%, resampling maps (both sides and all opponents of a map move together).

## 1. The draft steps: changed cells against unchanged cells

Each step shipped play changes too; the cells whose team did not change carry those. Win% is old draft -> new.

| step (old -> new versions) | changed cells: win% | unchanged cells: win% | draft effect on a changed cell (95% CI) of n changed |
|---|---|---|---|
| Fish, v83-114 -> v115 (31 old games a cell) | 62.4 -> 67.6 | 68.3 -> 73.3 | +0.3 (-11.0 to +11.0) of 170 |
| same, holding the cell's old win share fixed | | | -3.3 (-16.9 to +9.1) of 170 |
| Mite, v97-114 -> v115 (cells where Mite's team is r6's) | 58.1 -> 60.0 | 61.7 -> 65.1 | -1.5 (-13.9 to +11.2) of 170 |
| Mite r6 only, v113 -> v115 | 57.1 -> 60.0 | 53.5 -> 65.1 | -8.7 (-25.9 to +8.7) of 170 |
| other nine teams, v113 -> v115 | 81.8 -> 81.6 | 82.4 -> 85.4 | -3.3 (-7.8 to +1.2) of 1,342 |
| Fish, v81-82 -> v83-86 | 56.0 -> 60.9 | 53.5 -> 60.8 | -2.3 (-12.4 to +7.1) of 126 |
| Mite, v81-82 -> v83-86 | 61.5 -> 63.7 | 63.8 -> 67.7 | -1.7 (-11.5 to +8.3) of 126 |
| Fish, v78-80 -> v81-82 | 47.3 -> 55.1 | 56.0 -> 53.0 | +10.8 (-2.6 to +24.6) of 206 |
| Mite, v78-80 -> v81-82 | 61.7 -> 64.6 | 58.0 -> 55.0 | +5.9 (-6.8 to +18.0) of 206 |

- v115's gain over v113 (+5.5 against Fish, +5.9 against Mite) is at least as large on the cells whose team did
  not change (+7.0 and +11.6 against +4.7 and +2.9): the live record credits it to play, not to draft10.
- On our deaths (a finer outcome): the v115 draft moved them by -0.13 a game against Fish (-1.36 to +0.98) and
  -0.56 against Mite (-1.80 to +0.58) on changed cells; the kill margin by +0.66 (-1.13 to +2.76) and +0.11.

## 2. Champions: three independent readings, win points for holding the champion

Centred on the mean champion (a team's picks sum to its pick count, so only differences are identified).
*Within cell*: the swaps of all three draft steps (502 changed cells an opponent). *Between cells*: v83-114's win
share by cell on the team it drafted, pick count held fixed (the map chose the team, so this one is confounded).
*Ladder*: other teams against Fish or Mite, team and cell effects removed, minus the same on their games against
the field.

| against Fish | within cell | between cells | ladder, Fish minus field |
|---|---|---|---|
| Cassi & Issac | -5.0 (-20.4 to +10.6) | -7.4 (-33.0 to +20.5) | +1.7 (-3.6 to +6.9) |
| Prism | +7.4 (-2.8 to +16.4) | -6.4 (-20.1 to +9.1) | -1.7 (-8.9 to +5.5) |
| Willow | -0.7 (-10.8 to +8.9) | +10.9 (-2.2 to +20.9) | -0.4 (-7.1 to +6.3) |
| Vesper Vale | +4.4 (-6.5 to +15.0) | -0.1 (-12.4 to +12.3) | +4.9 (-1.4 to +11.2) |
| Heart of Ruin | -7.1 (-14.6 to +0.7) | -1.1 (-11.8 to +9.9) | -4.5 (-13.0 to +4.0) |
| Marcella | +4.6 (-4.3 to +13.8) | -5.7 (-17.7 to +6.6) | +0.3 (-6.3 to +6.9) |
| Vendetta | +0.6 (-12.7 to +11.6) | +1.9 (-10.6 to +14.8) | +0.1 (-6.8 to +6.9) |
| Ryth | +1.6 (-5.9 to +9.8) | -2.4 (-15.8 to +12.8) | +0.4 (-6.2 to +7.0) |
| Ren | +2.7 (-4.7 to +9.4) | -2.1 (-12.8 to +7.6) | -4.0 (-13.6 to +5.5) |
| Varg | -1.9 (-11.5 to +7.1) | -0.0 (-18.9 to +17.3) | +1.1 (-5.6 to +7.9) |
| Tavi | +2.2 (-6.3 to +9.6) | +2.7 (-10.5 to +15.2) | -0.3 (-11.5 to +10.9) |

| against Mite | within cell | between cells | ladder, Mite minus field |
|---|---|---|---|
| Cassi & Issac | -3.5 (-15.3 to +7.7) | -10.9 (-35.1 to +14.5) | +0.2 (-5.1 to +5.5) |
| Prism | -1.8 (-14.0 to +9.4) | +1.4 (-12.2 to +16.2) | +1.0 (-5.7 to +7.7) |
| Willow | +4.3 (-5.3 to +13.8) | +6.7 (-3.3 to +16.1) | +6.0 (-0.5 to +12.6) |
| Vesper Vale | -1.7 (-12.4 to +7.9) | -12.5 (-23.3 to -1.8) | +3.9 (-2.2 to +10.0) |
| Heart of Ruin | +3.1 (-4.0 to +9.2) | -0.6 (-10.1 to +10.4) | +1.2 (-5.7 to +8.0) |
| Marcella | -1.4 (-9.6 to +6.8) | -1.8 (-12.6 to +8.1) | +0.6 (-5.4 to +6.6) |
| Vendetta | +4.5 (-8.1 to +15.7) | +10.4 (-3.0 to +22.4) | +2.1 (-4.5 to +8.7) |
| Ryth | +1.4 (-5.9 to +8.3) | +6.6 (-8.6 to +20.9) | +0.4 (-5.8 to +6.5) |
| Ren | +4.5 (-3.7 to +12.3) | +3.9 (-7.9 to +14.9) | -3.8 (-12.5 to +4.8) |
| Varg | -2.4 (-15.2 to +11.6) | -6.8 (-27.1 to +15.6) | -1.5 (-7.7 to +4.8) |
| Tavi | -2.4 (-13.3 to +8.4) | +8.6 (-1.7 to +19.2) | +2.1 (-10.6 to +14.7) |

- Of 66 intervals one excludes zero: Vesper Vale against Mite between cells (-12.5), in the confounded reading.
  The within-cell reading puts it at -1.7 and the ladder at +3.9: a map effect, not a pick effect.
- The two nearest leads, neither clear:
  - **Willow against Mite**: positive in all three (+4.3, +6.7, +6.0), none excluding zero. The 44 cells where
    v115 added Willow read +4 (-12 to +21) against Mite net of the unchanged cells. ocean already holds her in 63%.
  - **Heart of Ruin against Fish**: negative in all three (-7.1, -1.1, -4.5), none excluding zero. Draft10 already
    cut her from 51% to 30% of cells; those 60 cells read +5 (-10 to +20) against Fish.
- Single swaps at the v115 step have 6 to 12 cells each and intervals of ±20 to ±60 (`extra.py`).

## 3. The pair

| reading | with the pair | without | |
|---|---|---|---|
| v83-114 cells, Fish | 64.0% of 244 cells | 70.9% of 12 cells | six maps |
| v83-114 cells, Mite | 62.7% of 244 | 75.0% of 12 | |
| v83-114 cells, other nine (v113) | 82.9% of 244 | 84.3% of 12 | |
| v115, Fish | 68.6% of 242 games | 77.8% of 18 | |
| v115, Mite | 61.6% of 242 | 61.1% of 18 | |
| our ranked games, Fish | 58% of 417 | 47% of 43 | versions mixed |
| our ranked games, Mite | 59% of 408 | 50% of 52 | versions mixed |

| the pair entering or leaving a cell at a step | cells | Fish old -> new | Mite old -> new |
|---|---:|---|---|
| v115: left | 8 | 68% -> 62% | 57% -> 62% |
| v115: entered | 4 | 78% -> 75% | 62% -> 50% |
| v83: left | 6 | 67% -> 54% | 92% -> 79% |
| v83: entered | 4 | 88% -> 69% | 100% -> 88% |
| v81: left | 8 | 38% -> 94% | 88% -> 100% |
| v81: entered | 18 | 17% -> 33% | 64% -> 53% |

- We draft the pair on 93-95% of cells, so the live record holds almost no games without it: 12 to 18 cells an
  era, ten maps in all (great_wall, one_gem, shortcut, guardians, anvil, treasure_box, starvation,
  homonoliths, the_pack, gemcombat1).
- Our pair's sign is negative in every scrim reading (-5.0 Fish, -3.5 Mite, -8.1 (-17.2 to +1.1) against the
  other nine at the v115 step), none separable from zero, and no larger against Fish than against anyone else:
  Fish minus Mite on the same cells is +3.5 (-19.4 to +28.4). If the pair is overvalued it is a general question
  for the draft lab, not a Fish nudge.
- Other teams that hold the pair do better against Fish (+6.1, +1.5 to +10.9), as they do against Mite (+4.6) and
  the field (+4.4, +2.7 to +6.3).

## 4. From picks to early deaths (v115; champion kills up to round 250; the pair counts once)

| our champion | games it is in | early deaths a game, live Fish (n) | against the Flp4 body (n) | win% with / without an early death of it, live Fish | live Mite (n) | against Mt3q (n) |
|---|---:|---|---|---|---|---|
| Cassi & Issac | 242 | 0.35 (84) | 0.31 (75) | 63% of 75 / 71% of 167 | 0.38 (92) | 0.29 (70) |
| Prism | 192 | 0.21 (40) | 0.10 (20) | 38% of 37 / 75% of 155 | 0.14 (27) | 0.09 (18) |
| Willow | 164 | 0.20 (33) | 0.09 (15) | 50% of 30 / 71% of 134 | 0.13 (22) | 0.10 (16) |
| Marcella | 56 | 0.30 (17) | 0.11 (6) | 35% of 17 / 72% of 39 | 0.20 (11) | 0.11 (6) |
| Ren | 42 | 0.50 (21) | 0.28 (11) | 69% of 16 / 77% of 26 | 0.12 (5) | 0.33 (13) |
| Heart of Ruin | 78 | 0.27 (21) | 0.31 (24) | 44% of 18 / 72% of 60 | 0.10 (8) | 0.22 (17) |
| Vesper Vale | 178 | 0.08 (15) | 0.07 (12) | 60% of 15 / 73% of 163 | 0.12 (22) | 0.10 (17) |

- The pair is the commonest early death because it is on 93% of our teams and is two bodies. The body kills it as
  often as real Fish does, and a pair death is the one that costs least (63% against 71%). It is our first death in
  21% of games against Fish and 22% against the body.
- What real Fish does and its body does not is kill Prism and Willow (twice as often), Marcella and Ren, and
  those games are lost (Prism 38% against 75%). So the morning's local values that could be flattered are Prism's
  and Willow's, not the pair's. The live readings do not confirm it: Prism against Fish is +7.4 within cell and
  teams holding her gain +5.0 (-1.1 to +12.0) against Fish; Willow is -0.7 within cell and +10.9 between.
- Mite kills the pair somewhat more than its body (0.38 against 0.29) and our Heart of Ruin and Ren less.

## Results against oc-comms-507

| gate | result |
|---|---|
| none | no candidate built, no games played |

## Verdict

No clear draft effect against real Fish or real Mite; no nudge built.

- **Size the record can see.** A draft step is resolved to about ±11 points on its changed cells against Fish and
  ±13 against Mite; a single champion to ±8 to ±15. The morning's light nudges were worth under a point on a
  changed cell locally. A live effect of ten points a changed cell is not excluded for any one champion; none is shown.
- **A live pair would not settle it.** In a draft-only pair the unchanged cells replay identically, so every bit
  of information is in the changed ones: a nudge that changes 15% of cells has about 38 an opponent, read to
  about ±20 points on them (±3 overall).
- **Reach of a per-opponent draft.** Picks are hidden until both teams have picked a round, so the draft can tell
  the opponent only from our second pick on: Fish and Mite open with the same champion on 100 of 256 cells and with
  the same two on 40.
- Not done: no decode of versions before v115 (per-champion deaths exist for v115 only); Mite's ladder games are
  pooled over its bot changes; the ladder reading is other teams' champions, played by their bots.

## Files

- [cells.py](cells.py): the draft steps, champion swaps and pair flips (sections 1 to 3). [between.py](between.py):
  v83-114 between cells. [ladder.py](ladder.py): the archive reading. [extra.py](extra.py): the step holding the old
  share fixed, single swaps, deaths. [picks_deaths.py](picks_deaths.py): section 4.
- Outputs: `~/tmp-offload/livedraft/` (`cells.out`, `between.out`, `ladder.out`, `extra.out`, `deaths.out`,
  `steps.json` one row a cell and step).
