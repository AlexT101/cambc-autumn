# Map generator against the ladder (2026-11-05)

Do mapgen's maps look like the 128 ladder maps (`maps/*.map26a`), which stand in for the tournament's? Measured on
existing maps only (nothing generated, no games). Generator: tools/mapgen at 52c07aea, unchanged since 2026-10-30.

**In short:** sizes, symmetry, gem and gold totals, groups per side and spawn distance match. Six structural things do
not: **camp group make-up, altar count and parity, altar position, picks, spawn size and winding terrain**. They miss
in the "ladder-like" presets too, and some miss worse there: 47% of ladder-like maps have 6 or more altars, against 8%
of the ladder. Only the mutation family (ladder maps under edits) matches. The newest ladder batch (`04*`, 42 maps
since SDK 5.0.0) is further from the generator than the older maps on most of these.

The fixes are in: [After: calibration 2](#after-calibration-2).

## Sets

| Set | Maps | What |
|---|---|---|
| ladder | 128 | `maps/*.map26a`; `ladder-04` = the 42 `04*` maps added 2026-11-04 |
| gen, gen-s1 | 256 + 256 | the A/B suites (seeds 6001, 6002) |
| fresh3 | 768 | `fresh-6003`, `fresh-10000`, `fresh-147001` |
| oc-d1 | 10,240 | 40 fresh suites merged; split by family as `oc:ladder-like` (1,570), `oc:mutation` (1,020), `oc:rest` (7,650) |

**Ladder play frequency** (big-arm archive, `g_map_hash`): on cambc 5.0.0 (1,235 games, 2026-11-04 and 05) all 128
maps are played, 3 to 22 games each. The CV is 0.33, the Poisson value at uniform draws, so the ladder draws maps
uniformly and the unweighted 128 maps are the right reference. Before the patch: 3,520 games on 96 maps.

## Mismatches, ranked

KS is the Kolmogorov-Smirnov distance, ladder against oc-d1 (0 = same distribution, 1 = disjoint). "Gen" is oc-d1
unless a family is named; gen, gen-s1 and fresh3 agree with it to within a few points (tables below).

| # | Property | Ladder | Generated | Size | Fix in mapgen |
|---|---|---|---|---|---|
| 1 | **Camp group make-up.** Monsters guarding clusters (wolf + gold, wolf + gems, ...) | 60% of groups (`04`: 72%) | 27% (ladder-like 19%) | KS 0.48 on single-camp share | `DEFAULTS.camp_mix` (generate.mjs:973): add `wolf_gold` (wolf + 1-2 gold clusters), `wolf_gems` (wolf + 1-3 gem clusters) and `wolves_gold` (2 wolves + 2 clusters), together about 40% of the weight. Cut `wolf` 3 -> 0.3, `wolf_pair` 2 -> 0.3 and `elk` 2 -> 0.2 |
| | Monster-only groups (a lone wolf or elk, wolf pairs) | 6% of groups | 33% (ladder-like 41%) | | as above |
| | Single-camp groups | 18% of groups (median map 9%); 43% of maps have none | 39% (median map 38%); 9% have none | KS 0.48 | as above |
| | Mean group size | 3.1 | 2.4 | KS 0.35 | target group sizes {1: 18%, 2: 25%, 3: 21%, 4: 16%, 5: 9%, 6+: 11%} |
| | Camp types (share of camps) | elk 6%, gold cluster 33%, golem 0 (31% of maps have one) | elk 10%, gold cluster 22%, golem 48% of maps | KS 0.29 / 0.24 / 0.24 | `golem`, `golem_gold` 0.4 -> 0.2; `elk_gold` 1.5 -> 0.5 |
| 2 | **Altar count** (tiles, both sides) | median 2; 1: 25%, 2: 38%, 3: 10%, 4: 16%, 6 or more: 8% | median 4; 1: 5%, 2: 39%, 3: 2%, 4: 23%, 6 or more: 29% (ladder-like 47%, `classic` 52%) | KS 0.27 | `DEFAULTS.altars` [1, 4] pairs (generate.mjs:971) -> `{1: 6, 2: 3, 3: 1}`. Cap altar scaling in `sampleSpec` (generate.mjs:1175) at 2 pairs, not 5. `altar_mode.many` 0.35 -> 0.1 |
| | Odd count (a self-mirrored altar) | 38% (`04`: 50%) | 12% | | `shared_altar` 0.25 -> 0.4; `altar_mode.single` 0.8 -> 2.5 (generate.mjs:971-972) |
| | 2 or more self-mirrored altars | 8% (one map has 34, all on the axis) | 0-1% | impossible outside mutations | `placeAltars` (generate.mjs:441) places at most one self-mirrored altar. Add an `axis` mode placing 2-3 on the symmetry axis, weight ~0.4 |
| 3 | **Altar position.** Nearest altar contested (walk ratio 0.4 or more) | 76% (`04`: 83%) | 49% (ladder-like 49%) | KS 0.38 on `altar_ratio` | `altar_mode` (generate.mjs:972): `own` 2.5 -> 0.8, `central` 4.5 -> 6; `altar_near` 0.6 -> 0.2. The "20 of 35" calibration (generate.mjs:962) predates the 128 maps. `pickDiverse`'s zone quota follows the candidates (mapgen.mjs:414), so fixing the sampler is enough |
| | Altars in the 0.4-0.5 band (per altar, maps weighted equally) | 83% | 61% | | as above |
| | Altar with 5 or fewer free neighbours | 9% | 32% | KS 0.30 | In `placeAltars`' `free` (generate.mjs:447), require 7 or more walkable neighbours except in altar-clusters and topo-necks |
| 4 | **Picks** | 3: 16%, 4: 20%, 5: 63%. Tied to size: 27 of 29 maps of 4,900 tiles or more pick 5; 3 picks only under 4,900 | 3: 30%, 4: 30%, 5: 40%, independent of size | KS 0.23 | `DEFAULTS.picks` [3, 5] (generate.mjs:965): sample picks by area in `sampleSpec`. Under 1,600 tiles {3: 0.35, 4: 0.4, 5: 0.25}; 1,600-4,900 {3: 0.12, 4: 0.14, 5: 0.74}; 4,900 and up {4: 0.07, 5: 0.93} |
| 5 | **Spawn size** | 3x3 82% (`04`: 100%), 4x4 12%, others 5% | 3x3 51%, 4x4 34%, others 15% | | `DEFAULTS.spawn_size` {3: 1, 4: 1} -> {3: 6, 4: 1} (generate.mjs:965) |
| 6 | **Winding walks with dash shortcuts.** Detour (spawn walk / Chebyshev) of 2 or more | 20% | 7% (ladder-like 1%) | KS 0.18; spawn_rel p90 1.93 vs 1.41 | Give `classic` and the ladder-like terrains a 25% chance of a mutation-style `gaps+N` pass (hole cuts across 1-3 wide passages, mapgen.mjs:177) and of the `serpentine` / `rooms` terrains. The ladder's winding maps: shortcut, reverse-spiral, twisty, meander, comb, terraces, waves, ... |
| | Share of tiles a dash brings 6+ nearer (`dash_short` > 0.1) | 27% | 10% (ladder-like 4%) | KS 0.22 | as above |
| 7 | **Camps by the spawn.** A camp group within 3 (Chebyshev) of a spawn | 17% | 2% (ladder-like 0%) | | **A bug, in effect.** The gap is max(`camp_spawn_gap`, reach + `spawn_reach_gap`) (generate.mjs:543), and `DEFAULTS.camp_spawn_gap` is 5 (generate.mjs:974). So `spawn_reach_gap` 0 or 1 never brings a wolf, elk or golem within 5 of a spawn, and the "camps reaching a spawn's edge" quirk never fires. Fix: sample `camp_spawn_gap` {5: 5, 3: 1, 1: 1}, or apply `spawn_reach_gap` without the max. Also add a home-camp step to `placeCamps` (generate.mjs:682): with p 0.15, one cluster group (optionally wolf-guarded) 1-3 tiles from the spawn. Band placement starts at ratio 0.06, so nothing else puts camps there |
| | Spawn surround partly blocked | 20% | 8% | | `spawn_clear` {2: 5, 1: 2, 0: 1} -> {2: 3, 1: 2, 0: 1.5} (generate.mjs:980) |
| 8 | **Shared camp groups** (self-mirrored) | on 45% of maps; 2 or more on 18% | 25%; 2 or more on 2% | KS 0.21 | `shared_camp` 0.1 -> 0.35 (generate.mjs:974), 1-3 groups (`placeCamps`' `shared_camp` block places one) |
| 9 | **Map extent.** Reachable on foot under half the map | 5% | 32% (ladder-like 0%) | KS 0.33 on `reach_frac` | Deliberate: exotic, designed, topology and scenario maps (75% of a suite). Weighting fix below |
| | Walls over 25% / holes over 30% | 1% / 8% | 24% / 19% | | as above |
| | 1-wide corridor share over 2% (`narrow`) | 1% | 17% | KS 0.36 | as above |
| | Leaky diagonals (`leaky` > 0) | 15% | 39% | KS 0.25 | as above |
| | No bushes | 3% | 17% | | `DEFAULTS.bushes.none` 1 -> 0.2; `EXOTIC` 2 -> 0.5 |
| | Spawns not walk-connected | 0% | 6% | | by design (topo-split, topo-island) |
| 10 | **Small maps.** Long side under 35 | 18% (9 at 30x30, 6 at 31x31) | 6% | KS 0.20 on area | `size` [30, 100] everywhere: put about 15% of `DEFAULTS` mass on 28-31 squares |
| | A side of 28 or 29 | 5% (6 maps) | 0% | impossible | `validate` rejects sides under 30 (generate.mjs:753); the rules allow 29 and the ladder has 28. Lower the bound to 28 |
| 11 | **Gem-only maps** (no gold source) | 5.5% (adgato-gemcombat1-5, 04gem-caverns, 04gem-rush) | 0.6% | near-impossible | Every camp mix has wolves or gold. Add a `gems-only` camp mode (`{gems: 3, gem: 2}` plus gem carpets), weight ~0.06 in `DEFAULTS` |
| 12 | Orientation W > H / H > W | 36% / 9% | 21% / 18% | minor | `sampleSpec` swaps W and H 50/50 (generate.mjs:1170); weight 0.8 to W > H if it matters (recall landing order and turn order are not mirror-invariant) |

**What matches** (KS 0.1 or less, or shares within ~5 points): symmetry (rotational 59%, horizontal 23%, vertical
19% against 54/24/23), gems per side (median 199 vs 184), gold per side (720 vs 750), groups per side (9 vs 9), spawn
walking distance (47 vs 50), monoliths (31% of maps vs 23%), groups of 20 or more camps (9% vs 9%), diagonally
touching groups (8% vs 8%), camps beside altars (12% vs 10%), access needing a dash or crystal (9% vs 13%), dash_gain
and choke_rel.

**Weighting fix (item 9 and the A/B):** `ab.py`'s 1280 games are 256 on the ladder and 1024 on gen and gen-s1, of
which only ~25% are ladder-like or mutation maps, and those miss on items 1-5 too. For a ladder-representative
judgement:
- report the ladder + mutation subset separately;
- or add `suite --mix ladder` to `suiteCounts` (mapgen.mjs:468): family factors mutation x3, ladder-like x3 (after
  items 1-5), the others x0.3.

## Distributions

### Altar tiles per map

| Altars | ladder | ladder-04 | gen | gen-s1 | fresh3 | oc-d1 | oc:ladder-like | oc:mutation | oc:rest |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 25% | 31% | 5% | 3% | 4% | 5% | 2% | 20% | 4% |
| 2 | 38% | 40% | 38% | 47% | 35% | 39% | 28% | 40% | 42% |
| 3 | 10% | 17% | 2% | 0% | 3% | 2% | 3% | 7% | 2% |
| 4 | 16% | 10% | 25% | 23% | 23% | 23% | 18% | 18% | 25% |
| 5 | 2% | 2% | 1% | 2% | 2% | 2% | 3% | 3% | 1% |
| 6 | 4% | 0% | 13% | 11% | 10% | 11% | 17% | 5% | 11% |
| 7-8 | 0% | 0% | 8% | 5% | 9% | 7% | 15% | 1% | 7% |
| 9+ | 4% | 0% | 9% | 8% | 13% | 10% | 16% | 5% | 10% |
| a self-mirrored altar | 43% | 60% | 9% | 10% | 12% | 12% | 16% | 33% | 9% |

By ladder-like preset (oc-d1): median altar tiles are 6 for `classic` (351 maps; 52% have 6 or more), 8 for `huge`,
15 for `altar-rich`, 5 for `contested-centre`, 4 for most others, and 2 only for `altar-poor`. By family the median is
2 for designed, topology and mutation maps and 6 for exotic and quirks maps.

### Categorical

| Property | ladder | ladder-04 | gen | gen-s1 | oc-d1 | oc:ladder-like | oc:mutation |
|---|---|---|---|---|---|---|---|
| 5 picks / 4 / 3 | 63 / 20 / 16% | 67 / 19 / 14% | 38 / 30 / 32% | 38 / 32 / 31% | 40 / 30 / 30% | 36 / 30 / 34% | 49 / 25 / 26% |
| spawn 3x3 / 4x4 / other | 82 / 12 / 5% | 100 / 0 / 0% | 50 / 38 / 12% | 50 / 37 / 14% | 51 / 34 / 15% | 48 / 40 / 11% | 82 / 12 / 6% |
| rotational / horizontal / vertical | 59 / 23 / 19% | 48 / 24 / 29% | 47 / 23 / 30% | 61 / 20 / 19% | 54 / 24 / 23% | 48 / 27 / 26% | 57 / 24 / 20% |
| long side <35 / 35-49 / 50-69 / 70-89 / 90-100 | 18 / 25 / 26 / 17 / 14% | 19 / 19 / 17 / 26 / 19% | 7 / 25 / 30 / 26 / 11% | 6 / 22 / 34 / 27 / 10% | 6 / 22 / 34 / 27 / 11% | 9 / 25 / 45 / 16 / 5% | 17 / 24 / 26 / 18 / 14% |
| access walk / dash / crystal | 91 / 6 / 2% | 98 / 2 / 0% | 86 / 9 / 5% | 83 / 11 / 6% | 87 / 8 / 5% | 96 / 0 / 4% | 76 / 10 / 14% |
| shared groups 0 / 1 / 2+ | 55 / 27 / 18% | 57 / 31 / 12% | 74 / 21 / 5% | 73 / 23 / 4% | 75 / 22 / 2% | 80 / 17 / 3% | 53 / 27 / 20% |
| monoliths per side 0 / 1 / 2+ | 69 / 25 / 3% | 69 / 29 / 0% | 78 / 18 / 1% | 80 / 16 / 1% | 77 / 18 / 3% | 71 / 26 / 3% | 68 / 24 / 4% |

### Group composition (share of a map's groups, maps weighted equally)

| | ladder | ladder-04 | gen | oc-d1 | oc:ladder-like |
|---|---|---|---|---|---|
| monsters + clusters | 60% | 72% | 26% | 27% | 19% |
| clusters only | 34% | 21% | 38% | 38% | 36% |
| lone wolf / wolf pack | 3% / 1% | 2% / 0% | 14% / 9% | 13% / 9% | 15% / 14% |
| lone elk | 0% | 0% | 7% | 6% | 10% |
| lone golem / monolith | 0% / 2% | 1% / 3% | 2% / 1% | 3% / 1% | 2% / 2% |
| size 1 / 2 / 3 / 4 / 5 / 6+ | 18/25/21/16/9/11 | 16/19/25/19/13/8 | 40/26/14/12/2/6 | 39/26/14/11/2/7 | 42/29/12/10/0/6 |

Commonest ladder groups: 2 gold clusters (7.6%), gold cluster + wolf (7.5%), a gem cluster (7.2%), a gold cluster
(5.3%), gem cluster + wolf (5.2%), 2 gold + wolf (3.9%). Commonest generated (oc-d1): lone wolf (13.5%), a gold
cluster (9.2%), a gem cluster (6.5%), 2 gold clusters (6.2%), elk + gold cluster (6.1%), lone elk (5.9%), wolf pair
(5.1%).

### Numeric features (p10 / p50 / p90; KS against the ladder)

Rows marked * are among the draft model's 25 features (tools/draftlab/model.mjs:26).

| Feature | ladder | ladder-04 | gen | oc-d1 | oc:ladder-like | KS gen | KS oc-d1 |
|---|---|---|---|---|---|---|---|
| area* | 921 / 2400 / 7208 | 933 / 2738 / 7225 | 1170 / 2934 / 7128 | 1290 / 3174 / 7254 | 1225 / 2809 / 5929 | 0.16 | 0.21 |
| altars* | 1 / 2 / 4.3 | 1 / 2 / 3.9 | 2 / 4 / 8 | 2 / 4 / 9 | 2 / 4 / 10 | 0.28 | 0.27 |
| altar_ratio* (nearest altar) | 0.17 / 0.49 / 0.50 | 0.17 / 0.50 / 0.50 | 0.08 / 0.34 / 0.49 | 0.06 / 0.39 / 0.50 | 0.08 / 0.38 / 0.50 | 0.44 | 0.38 |
| altar_centre* | 0.00 / 0.35 / 0.82 | 0.00 / 0.31 / 0.87 | 0.08 / 0.47 / 0.79 | 0.08 / 0.51 / 0.80 | 0.33 / 0.64 / 0.88 | 0.23 | 0.23 |
| altar_slots | 7 / 8 / 8 | 7 / 8 / 8 | 4 / 8 / 8 | 4 / 8 / 8 | 4 / 7 / 8 | 0.28 | 0.30 |
| camp_altar* | 1 / 4 / 12 | 2 / 5 / 15 | 2 / 3 / 7.5 | 2 / 3 / 9 | 2 / 3 / 9 | 0.16 | 0.16 |
| camps_side | 15 / 29 / 60 | 18 / 29 / 60 | 8 / 23 / 53 | 8 / 22 / 60 | 9 / 20 / 46 | 0.20 | 0.20 |
| groups_side | 4 / 9 / 17 | 6 / 9 / 18 | 4 / 9 / 20 | 4 / 9 / 22 | 4 / 8 / 14 | 0.07 | 0.06 |
| max_group* | 4 / 6 / 16 | 4 / 6 / 9 | 2 / 5 / 15 | 2 / 5 / 16 | 3 / 5 / 20 | 0.25 | 0.25 |
| big_camp_share* | 0.47 / 0.78 / 1.00 | 0.65 / 0.85 / 0.98 | 0.00 / 0.61 / 0.86 | 0.00 / 0.61 / 0.88 | 0.21 / 0.59 / 0.83 | 0.32 | 0.31 |
| gems_side* | 70 / 199 / 421 | 87 / 202 / 393 | 54 / 187 / 460 | 52 / 184 / 518 | 54 / 164 / 400 | 0.07 | 0.07 |
| gold_side* | 236 / 720 / 1632 | 432 / 725 / 1615 | 210 / 795 / 1845 | 260 / 750 / 2030 | 300 / 680 / 1610 | 0.06 | 0.07 |
| big_share* | 0.00 / 0.08 / 0.69 | 0.00 / 0.15 / 0.74 | 0.00 / 0.23 / 0.77 | 0.00 / 0.22 / 0.78 | 0.00 / 0.14 / 0.74 | 0.13 | 0.13 |
| cluster_share* | 0.15 / 0.41 / 0.84 | 0.15 / 0.43 / 0.68 | 0.01 / 0.31 / 0.70 | 0.00 / 0.28 / 0.64 | 0.00 / 0.26 / 0.60 | 0.18 | 0.20 |
| contested_share* | 0.14 / 0.43 / 0.78 | 0.14 / 0.35 / 0.57 | 0.00 / 0.34 / 0.67 | 0.00 / 0.33 / 0.67 | 0.11 / 0.39 / 0.71 | 0.14 | 0.14 |
| camp_near* | 1.6 / 6 / 19 | 3 / 5 / 16 | 3 / 4 / 13 | 3 / 5 / 14 | 4 / 7 / 15 | 0.14 | 0.13 |
| walls | 0.00 / 0.07 / 0.17 | 0.00 / 0.11 / 0.19 | 0.00 / 0.05 / 0.58 | 0.00 / 0.06 / 0.58 | 0.00 / 0.06 / 0.20 | 0.26 | 0.24 |
| holes* | 0.00 / 0.01 / 0.25 | 0.00 / 0.00 / 0.26 | 0.00 / 0.04 / 0.59 | 0.00 / 0.03 / 0.59 | 0.00 / 0.03 / 0.11 | 0.15 | 0.12 |
| bushes* | 0.01 / 0.04 / 0.09 | 0.01 / 0.03 / 0.08 | 0.00 / 0.02 / 0.14 | 0.00 / 0.03 / 0.16 | 0.00 / 0.06 / 0.14 | 0.27 | 0.24 |
| reach_frac* | 0.63 / 0.86 / 0.95 | 0.70 / 0.86 / 0.92 | 0.25 / 0.71 / 0.96 | 0.27 / 0.77 / 0.96 | 0.71 / 0.88 / 0.98 | 0.37 | 0.33 |
| spawn_dist* | 21 / 47 / 122 | 20 / 53 / 118 | 24 / 47 / 91 | 23 / 50 / 93 | 25 / 46 / 78 | 0.10 | 0.08 |
| spawn_rel | 0.46 / 0.92 / 1.93 | 0.42 / 0.90 / 1.82 | 0.58 / 0.86 / 1.32 | 0.53 / 0.88 / 1.41 | 0.63 / 0.86 / 1.19 | 0.19 | 0.15 |
| detour* | 0.88 / 1.10 / 2.50 | 0.88 / 1.15 / 2.31 | 0.88 / 0.97 / 1.60 | 0.88 / 1.00 / 1.74 | 0.89 / 0.94 / 1.31 | 0.22 | 0.18 |
| choke_rel* | 0.11 / 0.36 / 0.70 | 0.10 / 0.43 / 0.74 | 0.05 / 0.37 / 0.81 | 0.07 / 0.40 / 0.81 | 0.26 / 0.51 / 0.87 | 0.12 | 0.10 |
| openness* | 1.72 / 2.62 / 3.77 | 1.87 / 2.61 / 4.30 | 1.44 / 2.29 / 4.20 | 1.52 / 2.35 / 3.97 | 1.87 / 2.68 / 4.10 | 0.18 | 0.15 |
| narrow* | 0 / 0 / 0.01 | 0 / 0 / 0.01 | 0 / 0.01 / 0.05 | 0 / 0 / 0.04 | 0 / 0 / 0.02 | 0.44 | 0.36 |
| spawn_ring* | 0 / 0 / 0.22 | 0 / 0 / 0.05 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.13 | 0.11 |
| dash_short* | 0 / 0 / 0.58 | 0 / 0 / 0.20 | 0 / 0 / 0.05 | 0 / 0 / 0.09 | 0 / 0 / 0 | 0.23 | 0.22 |
| dash_gain* | 1 / 1 / 1.73 | 1 / 1 / 1 | 1 / 1 / 1.08 | 1 / 1 / 1.10 | 1 / 1 / 1 | 0.09 | 0.08 |
| sight_gap* | 0 / 0 / 0.02 | 0 / 0 / 0.01 | 0 / 0 / 0.01 | 0 / 0 / 0.01 | 0 / 0 / 0.01 | 0.16 | 0.13 |

### Coverage in the draft model's 25-feature space

Distances are RMS over the features, with the model's transforms, in ladder standard deviations. A ladder map's nearest
other ladder map is at median 0.74; 90% of ladder maps have one within 1.03.

| Set | Median distance to nearest ladder map | Beyond 1.03 |
|---|---|---|
| gen / gen-s1 / fresh3 | 0.96 / 0.95 / 0.94 | 43% / 45% / 41% |
| oc-d1 | 0.88 | 35% |
| oc:ladder-like / oc:mutation / oc:rest | 0.76 / 0.49 / 0.97 | 13% / 9% / 44% |

`mapgen diversity maps/gen maps/gen-s1` (its 36 features) agrees: 31% and 37% beyond the ladder's 90th percentile.

The other way round, 8% of ladder maps have no non-mutation oc-d1 map within 1.03. The worst covered (distance, then
the most extreme features):
- 00reverse-spiral 1.53: sight_gap, dash_short;
- 01shortcut 1.37: dash_gain +5.6 sd, detour +4.5;
- 00lost-world 1.18;
- 00road-of-riches 1.16: dash_short;
- adgato-gemcombat1 1.10 and 04gem-caverns 1.08: no gold;
- 01starvation 1.08: camp_near;
- 03one-gem 1.05: gems_side -4.7 sd.

## What the generator can't make, and what the ladder doesn't have

**Ladder properties the generator can't produce** (outside mutations of those very maps):
- sides of 28-29 (6 maps);
- 2 or more self-mirrored altars (10 maps, one with 34 on the axis);
- gem-only economies with no gold source (7 maps: 0.6% generated);
- camps guarding a spawn from 1-3 tiles away (22 maps: 2% generated);
- an 8x2 spawn (03membrane), which only the `wild` preset's `2x8` (weight 0.5) can make: none of the 10,240 has one;
- spawns under 15 walking steps apart outside topo-duel, topo-gatehouse, topo-capital and wild (8 ladder maps; the
  gate keeps 18-20, generate.mjs:1177-1178, whose comment's "18 is the ladder's closest" is stale).

**Generated properties never or rarely on the ladder:**
- spawns not walk-connected (6%; ladder 0);
- under half the map reachable on foot (32% against 5%);
- walls over 25% of the map (24% against 1%);
- 1-wide corridors over 2% (17% against 1%);
- leaky diagonals (39% against 15%);
- 10 or more altars (9% against 4%);
- cramped altars (32% against 9%);
- 600 or more gems a side (7% against 2%);
- 1x9, 2x6 and 3x5 spawns (2% against 1%).

These are deliberate stress tests (README: designed, exotic, topology, scenarios). They are not errors, but they are
three quarters of every suite.

## How mapgen works

**Entry points** (tools/mapgen/mapgen.mjs):
- `gen PRESET`, `mutate MAP|random`, `suite`, `check`, `diversity`, `show`, `list` (USAGE, mapgen.mjs:620).
- Maps are encoded through the engine WASM's MapBuilder. Each one is reloaded and compared tile for tile: `encode`,
  mapgen.mjs:83; wasm.mjs:52.

**Suite PLAN** (mapgen.mjs:18-41): 256 maps as `[preset, count]` entries.

| Family | Share | Presets |
|---|---|---|
| ladder-like | ~16% | `classic` 8, `monolith` 3, and 1-2 each of small-brawl, maze, caves, lanes, lakes, jungle, rows, altar-rich, altar-poor, contested-centre, tiny, huge, random, monolith-only, shared-gems, vaults |
| mutation | 22 maps | `mutate random` |
| designed | ~26% | atoll, archipelago, rivers, fortress, gatekeeper, dungeon, three-lane, arena, farmland, continent, hedges |
| exotic | ~22% | shapes, interiors, spawn distances, economies |
| quirks | ~4% | big-groups, wild |
| topology | ~12% | topology.mjs:765 |
| scenarios | ~12% | scenarios.mjs:646 |

Measured family shares: gen 16 / 7 / 28 / 19 / 2 / 9 / 19% and oc-d1 15 / 10 / 25 / 21 / 4 / 12 / 13%, in the table's
order.
- `SUITES` (mapgen.mjs:43): gen uses seed 6001, gen-s1 seed 6002.
- **`--mix varied`** (default, `suiteCounts`, mapgen.mjs:468): each family and each preset is scaled by a log-normal
  factor (sigma 0.5 per family, 0.6 per preset) drawn from `mix:<seed>`. A preset is dropped with p 0.12, but never a
  family's only entry. The counts are rescaled to the plan's total, capped by the candidate-seed space.
- **`--mix fixed`** keeps the plan's counts.

**Oversampling and diversity selection** (`suite` and `writeSuite`, mapgen.mjs:493-580):
- Each entry gets count x `--oversample` (default 3) candidates, mutations x2. Candidates come from child processes,
  slowest first (`makeCandidates`); seeds are `seed*100000 + idx*100 + j`.
- `pickDiverse` (mapgen.mjs:409) keeps the k most different by greedy farthest-point selection. The space is the
  min-max-normalised `FEATURES` (36 metrics, mapgen.mjs:47), with per-altar-zone quotas proportional to the
  candidates (mapgen.mjs:414).
- `index.json` records each map's kind, preset or mutation ops, spec, metrics and `ladder_nn` (its nearest ladder map
  in z-scored feature space, mapgen.mjs:520-535).

**Sampling a spec** (`sampleSpec`, generate.mjs:1154):
- Layers: `DEFAULTS` (generate.mjs:964), then `EXOTIC` (984) or `DESIGN` (1021), then the preset (`PRESETS`, 1036),
  then a `CAMP_MODES` economy (997), then overrides. Ranges are uniform, objects are weighted choices.
- Size is [30, 100] with aspect square, wide (H 0.55-0.85 of W), lanes (H 30-40) or thin (2.4-3.3), and W and H
  swapped 50/50.
- `scale_counts` scales groups and altar pairs by sqrt(area/2500), altars capped at 5 pairs (generate.mjs:1175).
- `spawn_min` is 18-20, or 0.4-0.45 of the long side (1177-1178).

**Symmetry:** rotational 5 : horizontal 2.5 : vertical 2.5 in `DEFAULTS`.
- Terrain is drawn freely, then `g.symmetrize()` copies each lower-index tile onto its mirror.
- Every later `g.set` writes a tile and its mirror (grid.mjs).
- Camps are stored for team A; `allCamps()` mirrors them, and a camp on a self-mirrored tile is its own mirror.

**Building order** (`generate`, generate.mjs:1182).

Non-designed presets:
1. `shapeMask` (playable-area shape, shapes.mjs) and `TERRAIN[...]`: open, scatter (wall lines, diagonals, ells,
   blocks, pluses), caves (cellular automaton), rooms (recursive division), lanes, rings, rows, and the shapes.mjs
   extras.
2. `holes`: lakes (value noise), a moat with 2 gaps, or pits.
3. `despeckle`.
4. `bushes`: blobs, patches or strips.
5. `symmetrize`.
6. `reserveShared`, for shared-gems and huge-shared: an axis band, 80-180 or 60-520 gems.
7. `pruneBushes` (clusters of 4+, at most `max_bush_clusters`).
8. `placeSpawn` / `placeSpawnMode` (corner, edge or inset; or far, corner, mid, near or touch), clearing a
   `spawn_clear` ring.
9. `connect`: symmetric 2-wide tunnels joining every pocket of 20+ tiles, cheapest through holes; smaller pockets are
   filled.
10. `placeVaults` (crystal-only walled pockets).
11. `placeAltars`.
12. `placeCamps`.
13. `sealPockets`: unreachable walkable tiles become holes.
14. `finish`: `validate`, then `gate`.

Designed presets run the designer (design.mjs:807, topology.mjs:759, scenarios.mjs:673), then `placeSites` (named
objectives), altars and filler camps.

**Altars** (`placeAltars`, generate.mjs:441):
- `altars` is a count of pairs: `DEFAULTS` [1, 4], with an optional single self-mirrored altar (`shared_altar` 0.25).
- `altar_mode`: spread 1.5, own 2.5, central 4.5, contested 1, corners 1, single 0.8, many 0.35.
- Placement takes candidates in walk-contest bands (`BANDS`, generate.mjs:377: near 0.06-0.26, mid 0.22-0.42,
  contested 0.38-0.5, central 0.4-0.5).
- An altar must be `altar_spacing` 5-9 from other altars, 3 or more from the spawns, clear of camps by
  `camp_altar_gap`, and keep the map connected (`stillConnected`).
- `gate` rejects a map whose nearest altar is not in the zone its mode promises.

**Camps** (`placeCamps`, generate.mjs:682).

Order of placement:
1. The shared band.
2. `shared_gold`.
3. `contested_groups`.
4. `shared_camp`: one small group on the centre.
5. Monoliths, in mid or contested bands, optionally ringed by 8 clusters.
6. `groups` [3, 14] templates drawn from `camp_mix`, in bands weighted by `camp_bias`.

Templates (generate.mjs:487) are wolf (1-3), elk (alone, + gold, + gems, pairs), gem and gold clusters (1-4), golem
(+ gold, gems, wolves), monolith (+ ring), and composed `poly`, `snake`, `carpet`, `ring` and `pack` groups of 4-32
cells (`typed` palettes).

`campCellsOk` (generate.mjs:540) checks each group:
- on ground (never bush);
- `camp_spawn_gap` from the spawns, and reach + `spawn_reach_gap` from them;
- not cardinally touching another group, or diagonally either unless `group_gap` is 0;
- `camp_altar_gap` from altars;
- clear of its own mirror;
- leaving the objectives reachable.

Economy modes (generate.mjs:997) swap the mix: golem, monolith, gem-centre, huge-shared, tiny, sparse, dense,
monsters, clusters, poor, rich, gold-rich, gold-poor, jackpot and packs.

**Validity** (`validate`, generate.mjs:751):
- sides 30-100, 3-5 picks, spawns of 9-16 tiles;
- symmetric terrain, clear spawns, no camp on a spawn or a blocked tile, at most 250 stored camps;
- spawns connected, past the camps too unless gated;
- every altar and group reachable at the map's access (walk, dash or teleport), and not enclosed by camps;
- if anything needs more than walking, early on-foot gold (a crystal costs 10).

`gate` (generate.mjs:1258) also requires:
- reach of at least `min_reach` (0.35 default, 0.2 exotic, 0.12 designed);
- spawn distance of at least `spawn_min` and `spawn_rel` of at most 3.5;
- at least `gem_min` gems per side (30);
- camp density of at most 9.5;
- an altar;
- designed maps filling 80% of the frame, and the designer's intents (e.g. an atoll hub not walkable).

**Mutations** (mapgen.mjs:245-405):
- A random current ladder map (`LADDER_NAMES` reads `maps/` at run time, so new ladder maps join automatically).
- `randomOps` draws 1-2 terrain edits (walls, holes or bushes x F, stamps, conversions, doors), often a camp or
  economy edit, sometimes altars, dash gaps, vaults or picks.
- Up to 20 attempts must pass `validate`, keep the altar zone when asked, and keep spawns at least min(18, original)
  apart.

**Calibrated to the ladder, and when:**
- 2026-10-30 (2316775d), on the 70 maps of that day: quirk rates (generate.mjs:977-980).

  | Quirk | Rate then | Now, 128 maps |
  |---|---|---|
  | groups touching diagonally | 10% | 8% |
  | camps beside altars | 16% | 12% |
  | camps reaching a spawn edge | 9% | 17% within 3; the generator makes 2% (item 7) |
  | partly walled spawn surround | 11% | 20% |
  | 4x3 / 5x2 spawns | 7% | 5% |
  | groups of 20+ cells | 14% | 9% |

- The altar-mode mix aims at "about half the maps' nearest altars central (the ladder has 20 of 35)"
  (generate.mjs:962). The 35-map ladder was SDK 3.0.2's; it is 76% now.
- Constants from named ladder maps:
  - spawn_dist 18, "the ladder's closest, elk-arena" (generate.mjs:1177); stale, 8 maps are closer;
  - the camp density cap of twice boss-battle's 8.2 (generate.mjs:1285);
  - composed groups up to vault's 49 cells (generate.mjs:508);
  - spawn rectangles "the ladder has only 3x3, 4x4, 4x3 and 5x2" (generate.mjs:244); 03membrane's 8x2 has since been
    added;
  - presets modelled on single maps: monolith-only on contest, shared-gems on stampede, rows, vaults on collision.
- Not recalibrated since. The ladder grew to 128 maps on 2026-11-04 (08c02417: 42 `04*` maps with SDK 5.0.0), and the
  `04*` maps are the least like the generator: all have 3x3 spawns, 69% have no holes, none has more than 5 altars, 50%
  have an odd altar count, and 72% of their groups are guarded clusters.

## Method

- **Per-map stats:** `stats.mjs` in the scratchpad. It reuses `tools/draftlab/features.mjs`' `mapRow` (mapgen
  `metrics` plus the draft extras) and adds per-altar walk and Chebyshev distances and per-group composition.
- **Tables:** `analyze.py`, `quirks.py` and `coverage.py`; `ladderfreq.py` for the archive tallies. All are in
  `/tmp/claude-1000/-home-ubuntu-cambc-autumn/3650a530-f591-417e-a0c5-31524a1e3260/scratchpad/mapstats/`. A full run
  of 11,648 maps takes ~3 min on one core.
- **Kept in tools?** None. A `mapgen diversity` that also reported altar parity and group composition (items 1-2)
  would catch these regressions; it is worth adding with the fixes.
- **Definitions:**
  - altar counts are altar tiles, both sides;
  - "self-mirrored" means a tile that is its own mirror;
  - group shares weight each map equally;
  - `altar_ratio` is mapgen's: the nearest altar's own-spawn walk distance over the sum of both, with camps blocking.

## After: calibration 2

tools/mapgen gained a second calibration (2026-11-05) and a `--mix ladder` suite, the default of `suite --out`.
Calibration 1 is unchanged: `--mix varied-v1` remade `fresh-192158` map for map (index.json differs only in its
`mix` label), and `gen` / `mutate` take `--calib 1`.

**Reference weighting.** The 128 ladder maps, each weighted equally, as the archive shows the ladder drawing them
uniformly; the 42 `04*` maps are a third of the weight. As a check, the same tables with the `04*` maps counted twice
(170 maps, `04*` half the weight): new mean KS 0.072 (old 0.214), 10% of new maps beyond the p90 (old 39%). Nothing
was tuned to the `04*` maps alone: they differ from the older maps on holes (69% have none, against 37%), spawns (all
3x3) and guarded groups (72%), and the 50/50 weighting would move those three targets halfway.

**What changed** (items above):
- 1, camp make-up: `ladder_group` draws groups from the ladder's make-ups (`LADDER_GROUPS`: wolf + gold, wolf + gems,
  gem and gold carpets, ...), with per-map tilts toward singletons, big groups or clusters.
- 2-3, altars: the ladder's altar make-ups (`altar_cfg`: pairs plus 0-3 self-mirrored altars; 9 self-mirrored on 1%),
  odd sides forced and mirror symmetry chosen when a map needs them; `hub` and `altar_twin` modes; altars need 7 or
  more open neighbours on 8 maps in 9.
- 4, picks by area (`PICKS_BY_AREA`); 5, spawn_size {3: 6.5, 4: 1}, 8x2 spawns.
- 6, winding: `barriers` (1-3 long walls or hole lines across the spawn axis) and `dash_cuts` (mapgen's `gaps`).
- 7, the spacing bug: `spawn_reach_gap` now applies alone (`camp_spawn_gap` only to camps without reach), and
  `home_camp` puts a group 1-3 tiles from a spawn on 17% of maps.
- 8, shared groups: 0-5 on the axis by symmetry (`SHARED_BY_SYM`).
- 9, extent: the ladder mix has no stress families; a `tidy` pass fills most leaky diagonals and opens most 1-wide gaps
  (also after mutations, keeping the source map's own).
- 10, sizes: the ladder's long-side and aspect bands, sides from 28 (`validate`'s floor under calibration 2).
- 11, gem-only economies (`camp_mode` `gems-only`, 6%); 12, W > H at 4 to 1.

**Sets.** new = 20 held-out `--mix ladder` suites (seeds 507020-507039, 5,120 maps, three quarters generated, a
quarter mutations; seeds 507000-507019 were used while tuning and read the same); old = oc-d1 (above); old
ladder-like + mutation = oc-d1's `oc:ladder-like` and `oc:mutation`, the closest a calibration 1 suite came.

| | old | old ladder-like + mutation | new |
|---|---|---|---|
| mean KS over 39 features | 0.209 | 0.168 | **0.067** |
| worst KS | single_share 0.48 | single_share 0.39 | bushes 0.12 |
| features with KS over 0.12 (n = 128: ~5% noise) | 31 | 24 | 0 |
| median nearest-ladder distance (25 draft features; ladder LOO 0.74) | 0.88 | 0.70 | 0.65 |
| maps beyond the ladder's p90 (1.03) | 35% | 11% | 8% |

| Property | Ladder | Old | New |
|---|---|---|---|
| altars 1 / 2 / 3 / 4 / 6+ | 25 / 38 / 10 / 16 / 8% | 5 / 39 / 2 / 23 / 29% | 24 / 41 / 9 / 16 / 7% |
| a self-mirrored altar / 2 or more | 43 / 8% | 12 / 1% | 40 / 6% |
| nearest altar contested | 76% | 49% | 77% |
| altar with 5 or fewer free sides | 9% | 32% | 6% |
| picks 3 / 4 / 5 | 16 / 20 / 63% | 30 / 30 / 40% | 14 / 19 / 67% |
| picks 5, area 4,900 and up | 93% | 42% | 91% |
| spawn 3x3 / 4x4 / other | 82 / 12 / 5% | 51 / 34 / 15% | 83 / 12 / 5% |
| long side under 35 / a side of 28-29 | 18 / 5% | 6 / 0% | 17 / 3% |
| W > H / H > W | 36 / 9% | 21 / 18% | 35 / 11% |
| guarded groups (share of a map's groups) | 60% | 27% | 57% |
| monster-only groups | 6% | 33% | 5% |
| no singleton groups | 43% | 9% | 42% |
| group sizes 1/2/3/4/5/6+ | 18/25/21/16/9/10 | 39/26/14/11/2/7 | 17/26/24/16/9/8 |
| camp group within 3 of a spawn | 17% | 2% | 17% |
| shared groups 0 / 1 / 2+ | 55 / 27 / 18% | 75 / 22 / 3% | 54 / 24 / 22% |
| gem-only | 5% | 1% | 5% |
| reachable on foot under half | 5% | 32% | 2% |
| walls over 25% / holes over 30% | 1 / 8% | 24 / 19% | 3 / 4% |
| narrow > 0.02 / leaky > 0 | 1 / 15% | 17 / 39% | 4 / 15% |
| detour 2 or more / dash_short > 0.1 | 20 / 27% | 7 / 10% | 16 / 20% |

**Still apart** (all within ~7 points, none with KS above 0.12):
- **Winding** (detour 2+ 16% vs 20%, dash_short > 0.1 20% vs 27%, dash access 2% vs 6%). The ladder's winding maps
  are hand-drawn serpentines and spirals; `barriers` approximates them, and more of them pushed sight_gap and
  openness away from the ladder faster than they closed this.
- **Rotational 53% vs 59%.** Maps with 2 or more self-mirrored altars must be mirrored (a rotation has one
  self-mirrored tile), and the lanes, rows and thin shapes pin a mirror axis.
- **Shared groups 2+ 22% vs 18%**, at the cost of one: 24% vs 27%. Mutations keep their source's shared groups and
  generated maps add theirs, so the two halves don't add up exactly.
- **Camp beside an altar 7% vs 12%, adjacent altars 8% vs 12%.** The 7-open-neighbour rule for altars, which fixed
  the 32% of crowded altars, also keeps camps and other altars away.
- **Bushes** (KS 0.12; no bushes 7% vs 3%): mutations that strip bushes from a ladder map.
- **Spawn ring partly blocked 15% vs 20%** and holes over 30% 4% vs 8%: small; raising either moved reach_frac.
- Not fixable by sampling: the ladder's one-off designs (a 34-altar axis, an 8x2 spawn, 04pinwheel's spiral) appear
  only through mutations.

**Engine check:** 256 astraeus mirror games on one ladder suite (fast runner, cambc 5.0.0, sides from 28) all
completed, 9 at the 2,000-round limit.

