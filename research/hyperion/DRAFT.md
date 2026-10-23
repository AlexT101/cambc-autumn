# Drafts

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
