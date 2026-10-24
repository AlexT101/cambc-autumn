# Equal-ray native screen results

The 80-game candidate-v33 panel produced 43/80 equal-ray wins (candidate-side A 20, B 23). The four candidate-A execution-parent stress cells produced 3/4 wins. These are diagnostics, not a release threshold.

## Matched 80-cell comparisons

- Equal-ray 43/80 versus f475-v33 complete 80 45/80: 12 gains, 14 losses, 54 unchanged exact map/physical-side cells.
- Equal-ray 43/80 versus connected escape full vs v33 37/80: 15 gains, 9 losses, 56 unchanged exact map/physical-side cells.
- Equal-ray 43/80 versus connected escape execution-only vs v33 38/80: 14 gains, 9 losses, 57 unchanged exact map/physical-side cells.

## Common-v33 comparison with M+H

The exact M+H arm (`marcella-hop`, source aggregate `709ba31a…`) has 52/80 wins on these same 40 maps and physical sides; frozen f475 has 45/80. M+H recovers 12 cells f475 lost and gives up 5 cells f475 won. Equal-ray recovers 12 and gives up 14. The arms share 6 recovered cells and 1 lost cell. M+H has 6 unique recoveries and 4 unique regressions; equal-ray has 6 unique recoveries and 13 unique regressions. This is a descriptive cell comparison only, not a causal or strength claim. Full cell lists and the correction record are in `RESULT.json` and `COMPARISON-CORRECTION.json`.

## Execution-parent stress cells

- 01elk-arena: A equal-ray 1020–B execution parent 276; winner equal-ray candidate A; 1550 completed rounds.
- 01fracture: A equal-ray 290–B execution parent 1103; winner execution parent B; 1152 completed rounds.
- 00reverse-spiral: A equal-ray 1005–B execution parent 466; winner equal-ray candidate A; 1288 completed rounds.
- 01hooks: A equal-ray 1045–B execution parent 143; winner equal-ray candidate A; 1400 completed rounds.

## Native and draft audit

All 84 statistics files have native roster draft bodies with matching pick counts for A/B; picks per side were 3 in 12 games, 4 in 18, and 5 in 54. Statistics report zero bot faults for both teams in all 84 games.
In the 80-game v33 panel, equal-ray had 246 play rollovers and 0 play errors; v33 had 553 play rollovers and 0 play errors. Both bots had 0 draft rollovers/errors and 0 other-phase rollovers/errors.
In the four-game execution-parent panel, equal-ray and the execution parent each had 38 play rollovers and 0 play errors. Both bots had 0 draft rollovers/errors and 0 other-phase rollovers/errors.

The fixture demonstrates that the second equally short ray becomes label-available, and an independent ranking oracle prefers it in a controlled case. These match outcomes do not establish that the mechanism activated in any native game.
