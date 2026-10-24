# Drafts

## Astraeus draft search (2026-10-24)

astraeus drafts from `params::draft_three/four/five` (one table per pick count) and `draft_counters` (our pick in a
round switches when the enemy's earlier picks include a champion). [draft_search.py](../../tools/variants/draft_search.py)
ran it, about 11.8k games.

- **Opponents:** astraeus playing the main drafts of 8 of the top 10 teams (all but us and Univardisty, who vary),
  from 1380 ranked games of 2026-10-24 10:20-17:10Z, equal weight per team. Each (map, side) meets one fixed team, so
  candidates are paired; the noise below is 2 SE of the paired difference.
- **Maps:** every map of the pick count, both sides: ladder, `maps/gen`, `maps/gen-s1` (~360 games, ladder under 15%),
  then a fresh suite (seed 4242, ~170 games) whose pool adds our old drafts and the best new ones as opponents.
- **Steps:** every single swap of the old draft plus each team's draft (40 games), the best and their combinations
  (120), the finalists on all maps, then the fresh suite.

| Picks | Draft | All maps | Fresh suite |
|---|---|---|---|
| 3 | **Marcella Vendetta HoR** (new) | 63.7%, +16.5 ±6.5 | 60.1%, +17.3 ±10.4 |
| 3 | Marcella Vesper HoR | +7.7 ±7.3 | +17.3 ±10.5 |
| 3 | Prism Vesper HoR (old) | 47.3% | 42.9% |
| 4 | **Prism Vesper Marcella HoR** (kept) | 59.0% | |
| 4 | Ryth for HoR | -8.7 ±6.7 | |
| 5 | **Prism Vesper Marcella Willow HoR** (kept) | 52.6% | 48.1% |
| 5 | Tavi for Prism | +2.9 ±6.8 | -0.6 ±9.4 |
| 5 | Ryth for Prism | -0.8 ±6.8 | +2.5 ±10.3 |

- 3 picks: head to head against astraeus c0de6b4, Marcella Vendetta HoR won 61.5% of 532 (Marcella Vesper HoR 55.3%).
- 3 picks: removing Prism, Vesper or HoR one at a time lost (Vendetta was the best single swap, level); the pair
  did not. With Marcella and Vendetta, HoR is the third pick: Cassi -3, Prism -6, Vesper -7, Varg -13 (120 games).
- 4 picks: no swap beat the old draft at 120 games; Ren and Varg lost 15-18, Prism is the core (removing it -16 at 40).
- 5 picks: no swap beat the old draft; at 40 games Stellar, Varg and Ren were the worst additions, Marcella and Vesper
  the worst removals. Willow-less variants were level or worse, so Willow stays.
- Counter picks: no per-team difference of the finalists exceeded its noise (±16-22 on ~45 games per team), so no
  `draft_counters` rule. A rule needs its flexible pick last; our weakest proxies were Claudus on 5 picks (38%, Tavi
  for Prism 47%) and Mite on 4 (45%), but the ladder shows 62% against Claudus on 5 picks.

Win % per proxy team (all maps plus fresh suite, games in brackets; teams' drafts in `draft_search.py` `TEAMS`):

| Picks | Draft | Claudus | Fish | Mite | Sponge | Trzy | new team(4) | policy wonk | prism best girl | All |
|---|---|---|---|---|---|---|---|---|---|---|
| 3 | Marc Vend HoR | 50 (58) | 62 (71) | 70 (70) | 66 (61) | 63 (59) | 61 (59) | 62 (69) | 71 (49) | 63.1 (496) |
| 3 | Marc Vesp HoR | 52 (58) | 51 (71) | 59 (70) | 54 (61) | 59 (59) | 63 (59) | 62 (69) | 55 (49) | 56.9 (496) |
| 3 | Pris Vesp HoR | 41 (58) | 46 (71) | 54 (70) | 49 (61) | 41 (59) | 47 (59) | 45 (69) | 49 (49) | 46.8 (496) |
| 4 | Pris Vesp Marc HoR | 71 (48) | 56 (41) | 45 (49) | 55 (44) | 76 (45) | 57 (49) | 58 (38) | 55 (42) | 59.0 (356) |
| 4 | Pris Vesp Marc Ryth | 46 (48) | 49 (41) | 47 (49) | 48 (44) | 56 (45) | 53 (49) | 55 (38) | 50 (42) | 50.3 (356) |
| 5 | Pris Vesp Marc Will HoR | 38 (74) | 58 (73) | 62 (65) | 60 (60) | 57 (56) | 42 (55) | 45 (64) | 56 (59) | 52.0 (506) |
| 5 | Tavi Vesp Marc Will HoR | 47 (74) | 56 (73) | 55 (65) | 55 (60) | 50 (56) | 51 (55) | 47 (64) | 66 (59) | 53.4 (506) |
| 5 | Ryth Vesp Marc Will HoR | 45 (74) | 63 (73) | 54 (65) | 65 (60) | 32 (56) | 51 (55) | 55 (64) | 46 (59) | 51.6 (506) |

Top-10 drafts on 2026-10-24 (share of top-10 team-games, ours excluded): 3 picks HoR Marcella Vesper 25%, Vesper HoR
Vendetta 22%, Marcella Vendetta Tavi 14%, Marcella Vendetta Ryth 10%; 4 picks HoR Marcella Vesper Ryth 32%, Vesper HoR
Vendetta Tavi 13%; 5 picks Marcella Vendetta Ryth Vesper HoR 31% (three teams), Vesper HoR Vendetta Tavi Marcella 11%,
Vesper Vendetta Ryth Tavi Marcella 11%, Marcella Vesper Tavi Willow HoR 10%. HoR/Ren/Stellar (2026-10-21) is gone, so
`test_compositions` below is stale.

## Draft search (2026-10-20, SDK 3.0.2)

The week-2 draft (CHANGES 30, ladder version 32) was found by hecate-vs-hecate games with only
`params::draft_preference` changed (`tools/variants/matrix.py`). It has been replaced by Khaos's Prism-first draft
(CHANGES 82), which was never searched this way; the results are in EXPERIMENTS' Draft section.

- **Method:** each pick scored only on maps of its pick count (picks 1-3 on 3-pick maps, the 4th on 4-pick maps, the
  5th on 5-pick maps), over the 35 ladder maps and `maps/gen`. Each set was split into a screen half and a held-back
  half; single swaps from a starting team, a round-robin of the best combinations, then the leader's neighbours. Noise
  (1 sd) about ±5.5 points on 80 games, ±3.5 on ~200.
- **Result:** Heart of Ruin, Marcella, Vesper, Ryth, Stellar, then Willow, Cassi and Issac, Varg, Ren, Vendetta, Tavi,
  Prism. 69.3% against the previous draft (Ren, Stellar, Cassi, ...) on a fresh 256-map suite (seed 8101), both
  sides.

## Test drafts (`params::test_draft`)

A/B copies only (`tools/ab.py` sets it): the draft takes one of the 10 most common top-10 compositions for the map's pick count, in its usual order, chosen by a hash of the map and our side (sides usually differ, reruns repeat, the side-swapped game gives each side the same draft). Off, the draft is unchanged (fuel bench replays identical).
Source: 417 ranked games among the top 10, 85 groups from 2026-10-21 03:20-05:30Z (team-games 156 / 142 / 536 at 3 / 4 / 5 picks). Compositions in pick order, with counts (`draft.cpp` `test_compositions`):
- 3: Stellar HoR Ren 78; HoR Ren Ryth 35; Marcella HoR Stellar 13; HoR Vendetta Ren 9; HoR Marcella Vesper 6; HoR Varg Stellar 4; HoR Marcella Ren 4; HoR Ryth Vesper 3; Stellar HoR Cassi 3; HoR Varg Cassi 1.
- 4: HoR Ren Stellar Ryth 83; HoR Vendetta Ren Vesper 12; Marcella HoR Stellar Ren 11; Stellar HoR Ren Cassi 9; HoR Marcella Vesper Ryth 9; HoR Varg Cassi Ryth 7; Vesper Cassi Varg Stellar 3; Marcella Ryth Stellar HoR 3; HoR Ren Ryth Tavi 1; Marcella Ren Stellar Ryth 1.
- 5: HoR Ren Stellar Ryth Varg 152; Marcella HoR Stellar Ren Ryth 132; HoR Ren Ryth Stellar Tavi 46; Stellar HoR Ren Cassi Ryth 43; HoR Marcella Vesper Ryth Stellar 39; HoR Vendetta Ren Vesper Varg 26; HoR Varg Cassi Ryth Stellar 16; Stellar HoR Prism Marcella Ren 12; Stellar HoR Cassi Marcella Willow 12; Vesper Cassi Varg Vendetta Stellar 10.
