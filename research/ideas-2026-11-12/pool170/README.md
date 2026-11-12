# The 170-map pool (2026-11-12)

The platform pool grew from 128 to 170 maps: 42 `05*` maps, in ranked play since 2026-11-11 23:10 UTC.

## Getting the maps

- `cambc maps pull` reads `/api/v1/maps/pool`, which still lists only the old 128. `/maps/pool/{id}/file` returns 404 for
  every 05 id, so a pull today changes nothing (checked in a scratch project: the same 128, byte for byte).
  `cambc maps list` and `cambc match-groups quota --json` list all 170.
- Each captured ranked replay on big-arm holds its map's .map26a after a 14-byte header. Each map was cut out where the
  running sha256 equals the map hash in big-arm's daily archive. [fetch_new_maps.py](fetch_new_maps.py) does this for
  every pool map missing from `maps/` (`--install` copies, never overwriting). 40 of 42 are in `maps/`, all passing
  `mapgen check`. 05chiseled_brick and 05rocket had no captured game yet: rerun the script later.
- File names follow the CLI's convention: a pool name with `_` is filed with `-` (`03the_front` becomes
  `03the-front.map26a`). A later `cambc maps pull` will therefore meet the same files, not add second copies. Live
  sets and the API use the underscore names.
- Every tool that reads `maps/` as "the ladder" is pinned to the 128 of 2026-11-05 (`tools/ladder128.txt`,
  `tools/ladder_set.py`; tools/README "Ladder sets"). Use `ladder-new` / `ladder-all` (ab.py, run_batched `--ladder`),
  fgate `--ladder all`, or lab config `"ladder": "all"` to include the new maps. With the pin, mapgen makes the same
  suite for a seed as before (a 256-map ladder-v2 suite, byte-identical).

## Are the 05 maps inside ladder-v2?

[compare-new05.md](compare-new05.md) puts the 40 maps next to the old 128 and 2,000 ladder-v2 maps from the fgate pool
(`research/mapgen-calib3-tools/stats.mjs` + `compare.py`). Ladder-v2 against the old 128 shows 0 mismatches at p < 0.01.
The 05 maps show 13, and they differ from the old 128 in the same ways. Sizes, aspect, picks, altar make-up,
symmetry, spawn distance, monster shares, gem balls and gem/gold shares all match. The differences:

| feature | 05 maps | old 128 | ladder-v2 |
|---|---|---|---|
| guarded share of a map's groups (mean) | 0.80 | 0.60 | 0.62 |
| gold-only groups (mean share) | 0.04 | 0.16 | 0.15 |
| mean group size | 4.97 | 3.38 | 3.36 |
| groups of 3+ (mean share) | 0.82 | 0.57 | 0.58 |
| maps with no singleton group | 72% | 43% | 43% |
| groups of 7+ cells (share of groups) | 23% | 6% | 6% |
| clusters per guarded group | 3.18 | 2.51 | 2.55 |
| line share of 3+ groups / elongation | 0.01 / 1.21 | 0.18 / 1.91 | 0.15 / 1.51 |
| spawn 3x3 | 100% | 82% | 82% |
| a camp group within 3 of a spawn | 2% | 17% | 16% |
| no shared group | 78% | 55% | 56% |
| walls > 15% / no holes / no bushes / bushes > 8% | 35% / 60% / 18% / 30% | 16% / 37% / 3% / 12% | 14% / 36% / 5% / 15% |
| camps per side (mean), gems / gold per side | 44, 286 / 1066 | 34, 235 / 893 | 33, 231 / 837 (p 0.05-0.09) |

In short, the 05 author builds compact blob-shaped groups of one monster (rarely two) with three or four clusters.
They make almost no free singleton or gold-only clusters and no line groups. Spawns are always 3x3, with nothing
within 4 tiles. Few groups are shared. Terrain is wall-heavy or bush-heavy rather than holed, and the economy is
somewhat richer. Ladder-v2 doesn't make maps like these as a population, though it covers each feature's range.
Mapgen would need, without changing calibration 3:

- a group make-up table fitted to the 05 maps: guarded blobs (`LADDER_GROUPS`/`LADDER_SHAPES`, with clusters per
  monster about 3) and fewer unguarded singles and gold-only groups;
- a 3x3-only spawn rule with a camp exclusion radius of about 5;
- a lower shared-group rate;
- terrain tilts: more walls, fewer holes, bimodal bushes;
- the 05 maps' camp count.

The cleanest form is a calibration 4 fitted to all 170 maps, weighting the 05 set by its share of current ranked play
(about half of top teams' games since 11-11), or a `ladder-v3` mix of ladder-v2 plus a 05-style plan.

## Our bots on the 05 maps

[results.md](results.md) ([analyse.py](analyse.py)). Each bot played the Fish and Mite bodies (`rt-Flp4`, `rt-Mt3q`,
unmetered) on the 40 maps, both sides, at noise seeds 76-87: 960 games a bot and body. Those are the seeds of fgate
batches b075-b086's ladder parts, which give the old-128 reads for c520-ps and chy-life. oc-dfuel-506's old-128 read
comes from b000-b033.

| bot | 05 maps (40) | old 128 | 05 minus 128 |
|---|---|---|---|
| c520-ps | 84.7% (83.1-86.3) of 1,920 | 81.1% (80.1-82.0) of 6,144 | +3.7 ±1.9 |
| chy-life (520) | 84.6% (83.0-86.2) of 1,920 | 81.0% (80.0-81.9) of 6,144 | +3.7 ±1.9 |
| oc-dfuel-506 (v115) | 77.2% (75.3-79.1) of 1,920 | 76.0% (75.3-76.6) of 17,408 | +1.3 ±2.0 |

Nothing breaks: every bot wins at least as often on the 05 maps, and charybdis keeps its lead over ocean (+7.5 points
there, +5.1 on the old 128). c520-ps against chy-life is +0.10 ±1.41 on the 05 maps (paired), the same as on the old 128.

Losing maps for charybdis (c520-ps win %, Fish / Mite; ocean 506 in brackets):

- 05poker_chip 35 (54 / 17) [71]: 31x31, 3 picks, 1 mid altar.
- 05border 44 (67 / 21) [88]: 33x33, 4 picks.
- 05ring 46 (38 / 54) [10]: 95x95. Ocean is far worse here.
- 05runway 60 [73], 05burger 62 [42], 05slant 65 [27].

poker_chip and border are small rotational maps that charybdis loses to Mite while ocean wins them. The old 128 hold a
similar outlier (00stampede: charybdis 27, ocean 95). The cause is unverified; the drafts (draft18 against draft10) are
the first suspect. Each map has 48 games a bot, which vary only by body noise and side, so these are map-level
effects. How the real teams play these maps is unknown.

## Integration proposals

**(a) fgate's ladder part.** Keep the 128 (the default now) for every gate in flight and for comparisons with today's
reads. The REF cache key (`fb<eng>-<bot>-<body>-m<maps>b<batch>`) doesn't encode the ladder set, and `games` counts
the ladder maps. An unpinned 170 would have invalidated every cached REF run, and the existing batch configs have no
noise seed for the new maps. `--ladder all` now exists with its own configs and run names (`-Lall`). Because the
ladder runs inside the same ab.py run as the fresh suites, though, it replays REF's whole batch (10,752 games), not
just 680 ladder games. Before making 170 the default, split the ladder into its own per-body runs keyed by set, so
switching replays only ladder games. In any case the ladder is a side read; decisions come from the fresh ladder-v2
units, which don't model 05 style. A distribution change is a pool question: add a 05-style calibration to the fresh
pool, as new batches beyond the 38 so earlier batches keep their maps.

**(b) Live scrims.** Leave `set-v1.json` frozen. Add a second frozen set file, `data/set-p05.json`; a draft is
[set-p05.draft.json](set-p05.draft.json): the 42 maps with platform names and ids, seeded order, as `core`, with
empty `ext`. Then plan `ladder_scrims.py plan --version N --set p05 --sets core --opps fish,mite` for every candidate
and control from now on, alongside the v1 parts.
- Task ids become `vN-p05core-...`, so they never collide with v1's.
- `pair` keys on (opponent, ref set, map, side), so v1 cells keep pairing with every older version, and p05 cells pair
  among the versions that played them. Comparing a new candidate with an older control on p05 needs that control live
  again for its p05 groups.
- Cost: 42 maps make 9 blocks (the last is 2 maps plus 3 fillers), each played both ways: 18 groups an opponent, 36
  groups (180 games) a version for Fish and Mite.
- The quota pool lists all 42 maps with these ids, so match groups can name them. Live ops should confirm with one
  group first.

**(c) `maps/` and `cambc maps pull`.** Done for 40 maps by copying (the old 128 checked by sha256 before and after).
A pull now is a no-op, since the endpoint still serves 128. When it serves the 05 maps, pull in a scratch project first
and compare its files' sha256 with ours (same names, by the CLI's convention). Then pull in the repo, with `--force`
only if they are identical, so `.cambc/map-pool.json` records them. The ladder pin doesn't depend on pull.
