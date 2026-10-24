# Published 40-map static economy inventory

Corrected whole-map native data for the exact `published40` set. The native decoder returns canonical team-A storage; this version expands through existing `Grid.allCamps()` / `Grid.groups()`, deduplicating self-mirrored centerline camps and groups. Group reward totals use the existing grid group member reward sums; ordinary totals exclude any group containing a monolith. These are whole-layout supplies, not a claim that one team can access or capture them. This static parse does not infer accessible share, capture timing, combat effort, or weighted-selection eligibility.

| Map | Size | Picks/team | Wolf | Elk | Golem | Gem clusters | Gold clusters | Monoliths | Ordinary gems | Ordinary gold | Ordinary groups | Ordinary mixed groups |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 00ambush | 100×100 | 5 | 2 | 10 | 0 | 16 | 18 | 0 | 270 | 1340 | 12 | 12 |
| 00collision | 41×41 | 3 | 8 | 10 | 0 | 14 | 24 | 0 | 280 | 1700 | 20 | 20 |
| 00contest | 50×50 | 5 | 0 | 0 | 0 | 0 | 32 | 2 | 0 | 640 | 12 | 12 |
| 00corners | 71×71 | 5 | 14 | 18 | 0 | 10 | 32 | 0 | 396 | 2820 | 30 | 26 |
| 00eight | 41×30 | 5 | 6 | 10 | 0 | 8 | 8 | 0 | 230 | 1300 | 8 | 8 |
| 00elkring | 30×30 | 5 | 0 | 10 | 0 | 10 | 10 | 0 | 220 | 1100 | 10 | 10 |
| 00expanse | 80×80 | 5 | 10 | 14 | 0 | 16 | 34 | 0 | 362 | 2340 | 24 | 22 |
| 00fragment | 30×30 | 3 | 6 | 2 | 0 | 2 | 6 | 0 | 68 | 540 | 6 | 6 |
| 00gem-fields | 50×40 | 5 | 6 | 4 | 0 | 40 | 0 | 0 | 364 | 600 | 18 | 6 |
| 00gemfight | 30×30 | 4 | 4 | 2 | 0 | 22 | 8 | 0 | 200 | 500 | 19 | 5 |
| 00great-wall | 50×40 | 5 | 8 | 8 | 4 | 44 | 12 | 4 | 576 | 1920 | 15 | 15 |
| 00interlock | 40×40 | 4 | 6 | 8 | 0 | 8 | 12 | 0 | 200 | 1200 | 14 | 12 |
| 00lanes | 90×30 | 5 | 30 | 6 | 0 | 12 | 36 | 0 | 294 | 2460 | 42 | 42 |
| 00lost-world | 35×31 | 5 | 8 | 2 | 1 | 42 | 24 | 1 | 364 | 1140 | 33 | 23 |
| 00monolith | 50×50 | 5 | 18 | 2 | 0 | 24 | 22 | 2 | 158 | 1340 | 18 | 16 |
| 00packs | 31×31 | 3 | 8 | 4 | 0 | 8 | 22 | 0 | 148 | 1120 | 8 | 8 |
| 00pilgrimage | 50×65 | 5 | 6 | 6 | 0 | 10 | 48 | 0 | 184 | 1740 | 23 | 23 |
| 00quadrants | 45×45 | 5 | 16 | 4 | 2 | 81 | 0 | 0 | 763 | 1320 | 21 | 17 |
| 00reverse-spiral | 30×30 | 4 | 12 | 4 | 2 | 22 | 6 | 0 | 334 | 1280 | 14 | 8 |
| 00road-of-riches | 40×40 | 5 | 12 | 8 | 2 | 74 | 34 | 2 | 646 | 2200 | 49 | 27 |
| 00rows | 50×50 | 4 | 18 | 0 | 0 | 16 | 18 | 2 | 114 | 1080 | 8 | 8 |
| 00rushbait-v2 | 30×80 | 4 | 10 | 8 | 0 | 14 | 12 | 0 | 258 | 1360 | 18 | 18 |
| 00split | 45×35 | 5 | 16 | 6 | 2 | 32 | 28 | 2 | 422 | 1980 | 30 | 14 |
| 00stampede | 60×50 | 5 | 0 | 6 | 0 | 10 | 32 | 0 | 160 | 1180 | 13 | 13 |
| 00swirl | 45×30 | 4 | 24 | 24 | 0 | 26 | 32 | 0 | 638 | 3760 | 22 | 22 |
| 01big-world | 100×100 | 5 | 22 | 8 | 0 | 32 | 28 | 2 | 376 | 2160 | 22 | 22 |
| 01boss-battle | 50×41 | 5 | 30 | 44 | 0 | 0 | 82 | 2 | 780 | 6800 | 30 | 30 |
| 01broken-curve | 40×40 | 3 | 10 | 12 | 0 | 18 | 22 | 2 | 346 | 1920 | 20 | 20 |
| 01concentrated-wealth | 61×61 | 5 | 12 | 3 | 0 | 12 | 18 | 0 | 177 | 1110 | 11 | 9 |
| 01corridors | 51×40 | 5 | 22 | 12 | 0 | 12 | 20 | 2 | 324 | 2360 | 11 | 11 |
| 01elk-arena | 50×50 | 5 | 0 | 2 | 0 | 6 | 54 | 0 | 72 | 1260 | 29 | 27 |
| 01fracture | 61×71 | 5 | 16 | 16 | 0 | 20 | 32 | 2 | 444 | 2720 | 26 | 24 |
| 01gold-rush | 31×31 | 3 | 6 | 0 | 0 | 6 | 28 | 1 | 66 | 720 | 14 | 10 |
| 01hooks | 31×31 | 4 | 0 | 4 | 0 | 4 | 20 | 0 | 88 | 760 | 12 | 12 |
| 01islands | 60×60 | 5 | 24 | 22 | 0 | 26 | 46 | 0 | 608 | 3860 | 46 | 42 |
| 01shortcut | 40×40 | 4 | 6 | 20 | 0 | 38 | 20 | 2 | 520 | 2440 | 19 | 19 |
| 01starfish | 50×50 | 5 | 18 | 10 | 0 | 16 | 12 | 0 | 334 | 1860 | 16 | 8 |
| 01starvation | 80×80 | 5 | 4 | 4 | 0 | 8 | 22 | 2 | 132 | 960 | 12 | 10 |
| 01the-farm | 50×40 | 3 | 24 | 26 | 0 | 30 | 32 | 2 | 682 | 3940 | 26 | 26 |
| 01yellow-brick-road | 40×30 | 5 | 30 | 16 | 0 | 16 | 98 | 0 | 472 | 4600 | 28 | 28 |

Gem cluster strata: {"above-minimum":37,"zero":2,"minimum-positive-2":1}.
Gold cluster strata: {"above-minimum":36,"minimum-positive-6":2,"zero":2}.

Lowest ordinary gold among 26 five-pick maps: 00gem-fields (600).

## Existing mapgen geometry features

These are the existing mapgen summary fields; `reach_frac` and `spawn_dist` depend on walkable geometry, while accessible camp share is not inferred.

| Map | Reachable fraction | Spawn distance | Detour | Choke | Altars | Camp density |
|---|---:|---:|---:|---:|---:|---:|
| 00ambush | 0.754 | 122 | 1.36 | 28 | 4 | 0.61 |
| 00collision | 0.766 | 33 | 0.92 | 20 | 2 | 4.32 |
| 00contest | 0.98 | 38 | 0.93 | 29 | 2 | 1.38 |
| 00corners | 0.972 | 39 | 0.93 | 80 | 5 | 1.51 |
| 00eight | 0.945 | 45 | 1.18 | 25 | 1 | 2.73 |
| 00elkring | 0.948 | 30 | 1.11 | 17 | 2 | 3.48 |
| 00expanse | 0.958 | 84 | 1.17 | 42 | 10 | 1.2 |
| 00fragment | 0.606 | 22 | 0.88 | 11 | 2 | 2.89 |
| 00gem-fields | 0.913 | 40 | 4.44 | 15 | 4 | 2.73 |
| 00gemfight | 0.868 | 45 | 1.8 | 9 | 2 | 4.56 |
| 00great-wall | 0.792 | 84 | 2.33 | 6 | 4 | 5.01 |
| 00interlock | 0.934 | 40 | 1.08 | 22 | 4 | 2.26 |
| 00lanes | 0.962 | 80 | 0.96 | 19 | 18 | 3.22 |
| 00lost-world | 0.77 | 25 | 0.89 | 3 | 3 | 9.24 |
| 00monolith | 0.955 | 48 | 1.12 | 26 | 6 | 2.84 |
| 00packs | 0.984 | 25 | 0.89 | 15 | 6 | 4.4 |
| 00pilgrimage | 0.795 | 122 | 2.71 | 6 | 4 | 2.7 |
| 00quadrants | 0.888 | 49 | 6.13 | 20 | 4 | 5.7 |
| 00reverse-spiral | 0.839 | 0 | 0 | 9 | 2 | 6.02 |
| 00road-of-riches | 0.825 | 242 | 17.29 | 2 | 2 | 9.88 |
| 00rows | 0.907 | 72 | 1.71 | 9 | 2 | 2.36 |
| 00rushbait-v2 | 0.9 | 0 | 0 | 16 | 2 | 2.02 |
| 00split | 0.9 | 83 | 3.77 | 5 | 3 | 6.03 |
| 00stampede | 0.793 | 54 | 1.15 | 12 | 2 | 2.01 |
| 00swirl | 0.707 | 12 | 0.8 | 8 | 2 | 11 |
| 01big-world | 0.878 | 138 | 1.86 | 19 | 6 | 1.05 |
| 01boss-battle | 0.925 | 37 | 1.03 | 16 | 1 | 8.29 |
| 01broken-curve | 0.821 | 35 | 1.3 | 12 | 4 | 4.84 |
| 01concentrated-wealth | 0.935 | 176 | 3.14 | 5 | 2 | 1.29 |
| 01corridors | 0.795 | 52 | 1.41 | 9 | 2 | 4.17 |
| 01elk-arena | 0.904 | 18 | 0.82 | 40 | 2 | 2.72 |
| 01fracture | 0.782 | 159 | 2.45 | 4 | 3 | 2.53 |
| 01gold-rush | 0.912 | 56 | 2.15 | 9 | 4 | 4.63 |
| 01hooks | 0.898 | 33 | 1.27 | 12 | 1 | 3.21 |
| 01islands | 0.566 | 62 | 1.24 | 12 | 10 | 5.76 |
| 01shortcut | 0.678 | 100 | 12.5 | 2 | 2 | 7.85 |
| 01starfish | 0.462 | 40 | 0.93 | 7 | 2 | 4.81 |
| 01starvation | 0.885 | 182 | 2.43 | 3 | 2 | 0.7 |
| 01the-farm | 0.917 | 40 | 0.91 | 14 | 6 | 6.18 |
| 01yellow-brick-road | 0.978 | 28 | 0.88 | 23 | 10 | 13.45 |

The native map schema exposes full map geometry, camp types, groups, and pick count. Team size equals map pick count under the rules. The inventory does not compute pathable/visible share or model team strategy.
