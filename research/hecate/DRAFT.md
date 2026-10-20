# Draft search (2026-10-20, SDK 3.0.2)

hecate's fixed draft after the week 2 patch and the Heart of Ruin nerf (1.0.1), found by hecate-vs-hecate games with
only `params::draft_preference` changed (`tools/variants/matrix.py`).

**Chosen order:** Heart of Ruin, Marcella, Vesper, Ryth, Stellar, then Willow, Cassi and Issac, Varg, Ren, Vendetta,
Tavi, Prism. Previous order: Ren, Stellar, Cassi and Issac, Ryth, Varg, Prism, Vesper, Vendetta, Marcella, Willow, Tavi.

## Method

- Each stage is scored only on maps of its pick count: picks 1-3 on 3-pick maps, the 4th on 4-pick maps, the 5th on
  5-pick maps. Maps: the 35 ladder maps plus the 256 of `maps/gen` (seed 7207), 89 / 94 / 108 maps with 3 / 4 / 5
  picks.
- Each pick-count set is split (seed 20261020, ladder and gen sampled separately) into a screen half (45%: 40 / 42 /
  49 maps) and a held-back half (49 / 52 / 59 maps). Candidates play both sides of the screen maps; only close ones
  play the held-back maps. Win rates below are from the row's side; noise (1 sd) is about ±5.5 points on 80 games,
  ±5 on 98-118, ±3.5 on 178-216.
- Search: single swaps from a starting team, a round-robin of the best combinations, then the leader's untested
  neighbours (one champion different); the next pick is added to the chosen team. Prism and Tavi were dropped after
  stage 1 (bottom or near bottom in every slot).

## Stage 1: picks 1-3 (3-pick maps)

Single swaps from Heart of Ruin, Stellar, Cassi (screen, 80 games each, vs that trio):

| replaced | ryth | vesper | vendetta | prism | marcella | willow | ren | varg | tavi |
|---|---|---|---|---|---|---|---|---|---|
| Heart of Ruin | 38.8 | 41.3 | 35.0 | 12.5 | 47.5 | 25.0 | 35.0 | 28.8 | 22.5 |
| Stellar | 56.3 | 55.0 | 50.0 | 33.8 | 62.5 | 45.0 | 52.5 | 58.8 | 36.3 |
| Cassi | 62.5 | 50.0 | 42.5 | 31.3 | 56.3 | 37.5 | 41.3 | 38.8 | 35.0 |

Round-robin of combined swaps (screen, 80 games per cell; all with Heart of Ruin):

| trio | mean | vs HoR/Marc/Cassi |
|---|---|---|
| HoR, Marcella, Cassi | 63.9 | - |
| HoR, Marcella, Ryth | 57.3 | 35.0 |
| HoR, Stellar, Marcella | 56.1 | 43.8 |
| HoR, Marcella, Varg | 51.6 | 47.5 |
| HoR, Stellar, Ryth | 46.6 | 32.5 |
| HoR, Stellar, Cassi | 42.3 | 37.5 |
| HoR, Varg, Cassi | 41.4 | 25.0 |
| HoR, Varg, Ryth | 40.7 | 31.2 |

Neighbours of HoR/Marcella/Cassi (screen, vs it): Vesper for Cassi 47.5, Ryth for HoR 46.3, Vendetta for Cassi 40.0,
Ren for Cassi 36.3, Varg for HoR 33.8.

All 89 three-pick maps (178 games), the two finalists against the same opponents:

| vs | HoR, Marcella, Cassi | HoR, Marcella, Vesper |
|---|---|---|
| Ren, Stellar, Cassi (old draft) | 69.7 | 72.5 |
| HoR, Stellar, Cassi | 61.2 | 64.0 |
| HoR, Marcella, Ryth | 59.0 | 55.6 |
| HoR, Stellar, Marcella | 53.9 | 50.6 |
| head to head | 50.0 | 50.0 |

HoR/Stellar/Ren (a common ladder trio) lost 64.3 / 70.4 / 72.5 to HoR/Marcella/Cassi, HoR/Marcella/Ryth and
HoR/Stellar/Marcella on the held-back maps (98 games). Cassi and Vesper tie as the third pick; stage 2 decided it.

## Stage 2: 4th pick (4-pick maps)

Screen (84 games) against HoR, Marcella, Cassi, Vesper:

| team | win rate |
|---|---|
| HoR, Marcella, Vesper, **Ryth** | 59.5 |
| HoR, Marcella, Cassi, Ryth | 52.4 |
| HoR, Marcella, Vesper, Vendetta | 52.4 |
| HoR, Marcella, Cassi, Vendetta | 48.8 |
| HoR, Marcella, Cassi, Willow | 46.4 |
| HoR, Marcella, Cassi, Varg | 46.4 |
| HoR, Marcella, Cassi, Stellar | 45.2 |
| HoR, Marcella, Cassi, Ren | 41.7 |

All 94 four-pick maps: HoR/Marcella/Vesper/Ryth vs HoR/Marcella/Cassi/Vesper 53.2 (188; 48.1 on the held-back
maps alone), vs HoR/Marcella/Cassi/Ryth 51.0 and vs HoR/Marcella/Vesper/Vendetta 53.8 (held-back, 104).
HoR/Marcella/Cassi/Ryth vs HoR/Marcella/Cassi/Vesper 53.7 (188). Ryth wins as the 4th either way; Vesper vs Cassi
stays level, and Vesper was taken with Ryth.

## Stage 3: 5th pick (5-pick maps)

Against HoR, Marcella, Vesper, Ryth + Cassi:

| 5th pick | screen (98) | all 108 maps (216) |
|---|---|---|
| **Stellar** | 52.0 | 57.9 |
| Willow | 54.1 | 52.8 |
| Varg | 49.0 | 47.7 |
| Ren | 41.8 | |
| Vendetta | 38.8 | |

Held-back maps (118): Stellar vs Willow 49.2, Willow vs Varg 66.1. Stellar and Willow are level head to head;
Stellar beats Cassi by more, so it is 5th and Willow 6th.

## Picks 6-12

Willow, Cassi and Issac, Varg, Ren, Vendetta, Tavi, Prism: by the stage 3 and stage 1 results. Draft picks cannot
fail in practice, so these only matter if a pick is ever refused.

## Validation

Fresh-seed suite (`mapgen suite --seed 8101`, 256 maps, both sides), new draft vs the old draft: pending.

Raw results: `replays/matrix-20261020-1724*` to `-1818*` (local, gitignored), map split in `replays/draftmaps/`.
