# ladder-v3: mapgen fitted to the 170-map pool (2026-11-12)

`node tools/mapgen/mapgen.mjs suite --mix ladder-v3` makes fresh maps that match the 170-map ranked pool, the 42 `05*`
maps included. Fresh-map gates can opt in with `tools/fgate.py --pool v3`. The default (`--pool v2`, ladder-v2) is
unchanged.

## Play shares: uniform, so the 05 maps are a quarter of ranked play, not half

big-arm's capture.db, ranked games from 2026-11-11 23:10 (the 05 maps going live) to 11-12 08:36:

- 113,965 games over all 170 maps, 28,183 (24.7%) on the 05 maps, which are 42/170 = 24.7% of the pool.
- Per map: 609-745 games, mean 670, sd 23 (Poisson 26). Chi-square for uniform: p 0.98.
- Top teams play the same mix. 05 share: both teams in the top 8, 26.4% of 905 games; one top-8 team, 25.4% of 460;
  both in the top 20, 24.1%; our team, 29.8% of 285.
- [ranked-per-map.csv](ranked-per-map.csv): map, games, games with both teams in the top 8, games with a team in the
  top 20.

So each of the 170 maps weighs the same: 128 old, 42 new. Ladder-v2 already matches the 128 at equal weights, so
ladder-v3 is ladder-v2's 256 maps plus 84 maps in the 05 style (2 per 05 map, as ladder-v2 has 2 per old map): 340 maps
a suite, 24.7% of them 05-style. If the final should weigh the 05 maps more than ranked play does, `--mix ladder-05`
makes the 05 part alone, and the two can be mixed at any ratio.

## The generator

- **mapgen.mjs.** `LADDER_V3_PLAN` = `LADDER_PLAN` plus `P05_PLAN` (`ladder05` 63, `{ mutate: 'random05' }` 21). Plan
  entries may carry their own `calib` and `over` (the third element), so ladder-v3's first 18 entries are ladder-v2's,
  with the same candidate seeds: a ladder-v3 suite at seed S holds the ladder-v2 suite at S byte for byte, plus 84
  maps (checked on 7320001: 256/256 identical). `random05` mutates one of the 40 05 maps pinned in
  `tools/ladder05.txt`. 05chiseled_brick and 05rocket were not captured when the maps were cut; a later fetch must not
  change the pin, or the seeds stop remaking their suites.
- **Calibration 4** (generate.mjs `DEFAULTS_V4`, `--calib 4`) is calibration 3 refitted to the 40 05 maps
  ([groups05.mjs](groups05.mjs) measures them):
  - 3x3 spawns only. Every camp, monsters included, sits 5 or more tiles from a spawn. `starter` (30%) places a group
    right at 5, so about half the maps have one there (05 maps: 48%). One map in 30 has a group 1-3 tiles away
    (05poker_chip).
  - Make-ups from `GROUPS_05`: the 05 maps' own shares. Mostly one wolf or elk guarding a block of 2-8 clusters;
    `big:` means 10 or more cells. Shapes come from `SHAPES_05`: L (3), 2x2 (4), plus (5), 2x3 (6), 3x3 less two (7),
    3x3 (9), with the monster on the best-connected cell. Per-map multipliers make most maps all-guarded and put
    singletons and pairs (`single_mult` scales both under calibration 4) and cluster-only groups on a few maps, as
    on 05ant-farm, 05crop-circle, 05mosaic and 05nest. Monoliths come from `monoliths` (38% of maps), not the table.
  - Shared groups almost only on mirrored maps (rotational 4%: 1 of the 26 rotational 05 maps has one).
  - More walls (`wall_density` up to 0.3, more open maps), fewer holes (none on 2 maps in 3), bushes absent or
    plentiful (`bush_amount` drawn from bands up to 0.25).
  - Size, aspect, symmetry, picks, altars and spawn distance stay calibration 3's. The 05 maps match them.
- Tuning: two rounds of 336-672 `ladder-05` maps (seeds 7310001-7310016) against the 40 maps. Round 1 already had no
  numeric mismatch; round 2 added the starter group, tied pairs to singletons and trimmed big groups and bushes.
  Validation used seeds held out from tuning: 7320001-7320008.

**Byte identity.** The old generator (HEAD's tools/mapgen extracted to a side directory) and the new one make the same
files, index.json included, for `ladder-v2` 7300001, 7300002, 7300011, 7300012; `ladder` 7300003, 7300013;
`paradigms` 7300014; `varied` 7300015. Every calibration 4 path is gated on `calib >= 4`, or on a table only
calibration 4 uses.

## Validation: [compare-170.md](compare-170.md), [compare-05.md](compare-05.md), [compare-128.md](compare-128.md)

The pool170 feature comparison (`research/mapgen-calib3-tools/stats.mjs` + `compare.py`: 41 numeric metrics, KS, and
33 shares, binomial test) on held-out seeds 7320001-7320008: 2,720 ladder-v3 maps, their 2,048-map ladder-v2 part and
their 672-map 05 part. Because ranked weights are uniform, "the weighted 170" is the 168 maps in `maps/` (128 + 40),
each counted once.

| reference | ladder-v2 | ladder-v3 |
|---|---|---|
| 168 published maps (weighted 170) | 2 at p < 0.01 (groups of 3+ share 5e-04, walls > 0.15 0.002); mean KS D 0.074 | **0** at p < 0.01; mean KS D 0.061 |
| the 40 05 maps (v3: its 05 part) | 12 at p < 0.01; mean D 0.192 | **0**; mean D 0.107 |
| the old 128 | 0; mean D 0.064 | 2 (mean group size 0.005, groups of 3+ 0.006), expected: v3 is not the 128 |

What remains at p < 0.05:

- Against the 170, `spawn_rel` (spawn walk distance over map size), p 0.031. Ladder-v2 has it too (p 0.021): the
  generator makes fewer close spawns (p10 0.63 against 0.43). It comes from calibration 3.
- Against the 05 maps, max group, p 0.031: median 9 cells against 8 (3x3 blocks on more maps).
- Smaller, unflagged: ladder-v3's 05 part has singletons on 39% of maps against 28% (p 0.15), holes on 52% against
  40% (p 0.16), and less spread in mean group size (p10/p90 3.1/6.6 against 2.4/9.1, p 0.08). One designer's 40
  maps can't pin down more than this.

## Does it matter? [results.md](results.md) ([analyse.py](analyse.py))

c520-ps, chy-life (charybdis 520) and oc-dfuel-506 against Fish `rt-Flp4` and Mite `mf-c1` (frozen as
`variants/mf-c1-lv3` at 08:23 so the body can't change mid-run; mf-c1 itself may move on), at 100k fuel. Bodies
unmetered, through fgate. Four v3 batches (pool-v3 b000-b003: 10,240 maps, 2,528 of them 05-style) against four v2
batches of the same size (b073-b074, b087-b088; the v2 pool has whole batches only to b088). 245,760 games in all,
0 failed, 0 lost by round 5.

Win % against both bodies:

| bot | v2 fresh | v3 fresh | v3 minus v2 | v3: ladder-v2 part | v3: 05 part | 05 minus v2 part |
|---|---|---|---|---|---|---|
| c520-ps | 77.1% | 77.4% | +0.3 ±0.6 | 76.8% | 79.4% | +2.6 |
| chy-life | 77.0% | 77.5% | +0.5 ±0.6 | 76.9% | 79.3% | +2.4 |
| oc-dfuel-506 | 68.9% | 69.4% | +0.5 ±0.6 | 69.2% | 69.9% | +0.7 |

Paired differences (map units, 95% CI):

| pair | v2 | v3 | v3's 05 part |
|---|---|---|---|
| c520-ps - chy-life | +0.05 ±0.32 | -0.08 ±0.32 | +0.13 ±0.62 |
| c520-ps - oc-dfuel-506 | +8.21 ±0.58 | +8.07 ±0.58 | +9.56 ±1.10 |
| chy-life - oc-dfuel-506 | +8.15 ±0.58 | +8.15 ±0.58 | +9.43 ±1.11 |

- **Win rates:** every bot reads 0.3-0.5 points higher on v3, within noise. The 05-style quarter is easier for
  charybdis (+2.4 to +2.6 over the v2 part) and hardly easier for ocean (+0.7). The real 05 maps showed the same
  pattern against the older bodies (pool170: c520-ps +3.7, oc-dfuel-506 +1.3 over the 128), so the generated maps
  reproduce the style's effect.
- **Ordering:** unchanged. c520-ps and chy-life are level on both. Charybdis's lead over ocean is +8.1 on both and
  +9.5 on the 05 part.

## fgate opt-in

```
py tools/fgate.py CAND REF --pool v3 [other options as usual]
```

- The pool is `~/tmp-offload/gatebatch/pool-v3`: 43,336 maps from mapgen seeds 2490000-2490127, in
  `~/tmp-offload/gatebatch/generated-v3/{seed}`. That is 16 whole batches of 2,560. Grow it with
  `py tools/fgate_batch.py grow SEEDS DIR... --pool v3`; seeds up to 2490999 are reserved for it.
- Grow interleaves the 05 part at its share, so every batch has exactly 632 of 2,560 (24.7%), not a random draw.
- Batch configs and parts live under `suites-v3/`. Run names and result files end `-Pv3`, so no v2 batch or REF run
  is reused or overwritten. Noise seeds follow v2's rule: fresh map i plays noise i + 1. The ladder side read is the
  same.
- REF runs already cached on pool-v3 b000-b003 at `--fuel 100000`: chy-life and oc-dfuel-506 against Flp4 and
  mf-c1-lv3. c520-ps has runs too.

## Recommendation

Switch new gates to `--pool v3` and keep v2 for gates already in flight. v3 matches the pool the final draws from
(0 mismatches against the 170, against 2 for v2 and 12 for v2 against the 05 maps). It costs nothing, and it moves
neither the bots' win rates beyond noise nor their order. The case is a better target, not a different verdict on
today's bots. It matters most for changes that touch what the 05 style changes: guarded compact groups, no early camp
by the spawn, wall-heavy maps. A v2 gate gives those a quarter less weight than ranked play does.

Two caveats:

- A v3 gate starts REF's cache afresh (16 batches, 4 already played for chy-life).
- If the coordinator believes the final leans to the newest maps beyond their ranked share, ladder-05 can be
  weighted up. Nothing measured here supports that: the devs' pool and ranked play both weigh every map equally.
