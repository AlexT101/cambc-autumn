# Matched v33 cells and single-change controls

Both approved batches completed without failed rows. Every game used normal native drafts, Release mode, jobs=1, and fuel quantum 100,000. Scores below name physical A and B explicitly.

## Matched v33 common cells

18 games cover nine map/side cells. Both local f475 and local v48 faced frozen v33 in the same physical orientation for each cell. This is a local controlled source comparison; it does not identify the source used by ladder replays.

| Map | Physical A source | A score | Physical B source | B score | Winner | Round |
|---|---|---:|---|---:|---|---:|
| 00gem-fields | f475 | 1040 | v33 | 592 | f475 | 537 |
| 00gem-fields | v48 | 1040 | v33 | 592 | v48 | 537 |
| 01fracture | v33 | 1030 | f475 | 221 | v33 | 984 |
| 01fracture | v33 | 627 | v48 | 1020 | v48 | 1435 |
| 00ambush | f475 | 724 | v33 | 1005 | v33 | 1131 |
| 00ambush | v48 | 724 | v33 | 1014 | v33 | 1156 |
| 00ambush | v33 | 260 | f475 | 1004 | f475 | 1049 |
| 00ambush | v33 | 545 | v48 | 1084 | v48 | 962 |
| 01concentrated-wealth | v33 | 1017 | f475 | 181 | v33 | 1030 |
| 01concentrated-wealth | v33 | 1027 | v48 | 77 | v33 | 1072 |
| 00eight | f475 | 1021 | v33 | 78 | f475 | 1047 |
| 00eight | v48 | 1021 | v33 | 78 | v48 | 1047 |
| 00eight | v33 | 1004 | f475 | 279 | v33 | 932 |
| 00eight | v33 | 316 | v48 | 1083 | v48 | 969 |
| 01starvation | f475 | 796 | v33 | 448 | f475 | 2000 |
| 01starvation | v48 | 64 | v33 | 1008 | v33 | 1218 |
| 01starvation | v33 | 1052 | f475 | 308 | v33 | 1743 |
| 01starvation | v33 | 572 | v48 | 1000 | v48 | 1936 |

Across these 18 rows: f475 won 4, v48 won 6, and v33 won 8. Native statuses are audited separately for f475-v33 and v48-v33 in the corresponding `native-status-*.json` files.

## 00eight and 01starvation control ablation

Eight games compare the two reviewed single-change controls against f475 with both physical sides on the maps where v48 went 0–2. This isolates local candidate behavior and is not a ladder benchmark.

| Map | Physical A source | A score | Physical B source | B score | Winner | Round |
|---|---|---:|---|---:|---|---:|
| 00eight | v47_recall | 263 | f475 | 993 | f475 | 2000 |
| 00eight | v48_walk_altar | 263 | f475 | 993 | f475 | 2000 |
| 00eight | f475 | 1023 | v47_recall | 338 | f475 | 991 |
| 00eight | f475 | 1571 | v48_walk_altar | 298 | f475 | 1371 |
| 01starvation | v47_recall | 312 | f475 | 1008 | f475 | 1750 |
| 01starvation | v48_walk_altar | 1124 | f475 | 304 | v48_walk_altar | 1892 |
| 01starvation | f475 | 312 | v47_recall | 1008 | v47_recall | 1750 |
| 01starvation | f475 | 312 | v48_walk_altar | 1008 | v48_walk_altar | 1750 |

On 00eight, f475 won all four cells. On 01starvation, v47+recall lost as A and won as B; v48+walk-altar won in both orientations. Native status is audited separately for each control/f475 pair.

## Batch pins

All outcomes use normal drafts and reviewed ordered manifests. Per-game statistics/replay SHA-256s are in the machine-readable summaries; native rollover/error counts are in the four status audit JSONs. No puppet game has been run.
