# Local Release map comparison: f475 and Khaos_v34

The approved 80-row run completed with 80/80 games and zero failed rows. Every game used the normal native draft, Release mode, and fuel quantum 100,000. This is a controlled local source comparison; it does not establish which server source produced any ladder replay.

Across the 80 games, local v48 won 44 and local f475 won 36. v48 was 25–15 as physical A and 19–21 as physical B. Completed rounds ranged from 457 to 2,000 (median 985). The native replay audit found 275 v48 play rollovers and 241 f475 play rollovers, with zero Bot errors for both; draft/other-phase rollover and error counts were zero. Statistics botFaults were zero for both sides.

The four SDK/workspace pins (cambc.h, imports.h, CMakeLists.txt, cambc.toml) retained both SHA-256 and mtimes. f475 and v48 source aggregates and raw/injected Release WASM hashes matched the pre-run pins.

## Paired results by map

| Map | f475 A vs v48 B | v48 A vs f475 B | v48 wins |
|---|---|---|---:|
| 00ambush | A=f475 353, B=v48 1000, winner=v48, rounds=871 | A=v48 818, B=f475 1009, winner=f475, rounds=1106 | 1–1 |
| 00collision | A=f475 1283, B=v48 66, winner=f475, rounds=1133 | A=v48 1283, B=f475 66, winner=v48, rounds=1133 | 1–1 |
| 00contest | A=f475 800, B=v48 600, winner=f475, rounds=2000 | A=v48 1000, B=f475 200, winner=v48, rounds=1493 | 1–1 |
| 00corners | A=f475 1013, B=v48 189, winner=f475, rounds=826 | A=v48 1013, B=f475 189, winner=v48, rounds=826 | 1–1 |
| 00eight | A=f475 1571, B=v48 298, winner=f475, rounds=1371 | A=v48 263, B=f475 993, winner=f475, rounds=2000 | 0–2 |
| 00elkring | A=f475 374, B=v48 1001, winner=v48, rounds=670 | A=v48 374, B=f475 1001, winner=f475, rounds=670 | 1–1 |
| 00expanse | A=f475 453, B=v48 1009, winner=v48, rounds=895 | A=v48 597, B=f475 1016, winner=f475, rounds=992 | 1–1 |
| 00fragment | A=f475 1018, B=v48 54, winner=f475, rounds=1271 | A=v48 1018, B=f475 54, winner=v48, rounds=1271 | 1–1 |
| 00gem-fields | A=f475 1000, B=v48 983, winner=f475, rounds=635 | A=v48 1000, B=f475 983, winner=v48, rounds=635 | 1–1 |
| 00gemfight | A=f475 1026, B=v48 82, winner=f475, rounds=842 | A=v48 1060, B=f475 193, winner=v48, rounds=808 | 1–1 |
| 00great-wall | A=f475 748, B=v48 1014, winner=v48, rounds=985 | A=v48 588, B=f475 1036, winner=f475, rounds=968 | 1–1 |
| 00interlock | A=f475 1033, B=v48 193, winner=f475, rounds=944 | A=v48 1033, B=f475 193, winner=v48, rounds=944 | 1–1 |
| 00lanes | A=f475 1000, B=v48 628, winner=f475, rounds=853 | A=v48 1000, B=f475 628, winner=v48, rounds=853 | 1–1 |
| 00lost-world | A=f475 49, B=v48 1008, winner=v48, rounds=460 | A=v48 1001, B=f475 724, winner=v48, rounds=985 | 2–0 |
| 00monolith | A=f475 1275, B=v48 635, winner=f475, rounds=1092 | A=v48 1275, B=f475 635, winner=v48, rounds=1092 | 1–1 |
| 00packs | A=f475 204, B=v48 1006, winner=v48, rounds=817 | A=v48 204, B=f475 1006, winner=f475, rounds=817 | 1–1 |
| 00pilgrimage | A=f475 1057, B=v48 540, winner=f475, rounds=1599 | A=v48 1024, B=f475 585, winner=v48, rounds=1740 | 1–1 |
| 00quadrants | A=f475 562, B=v48 1053, winner=v48, rounds=498 | A=v48 1032, B=f475 426, winner=v48, rounds=457 | 2–0 |
| 00reverse-spiral | A=f475 282, B=v48 1003, winner=v48, rounds=1104 | A=v48 1058, B=f475 407, winner=v48, rounds=1151 | 2–0 |
| 00road-of-riches | A=f475 1024, B=v48 274, winner=f475, rounds=757 | A=v48 1024, B=f475 274, winner=v48, rounds=757 | 1–1 |
| 00rows | A=f475 382, B=v48 1000, winner=v48, rounds=1230 | A=v48 382, B=f475 1000, winner=f475, rounds=1230 | 1–1 |
| 00rushbait-v2 | A=f475 386, B=v48 1022, winner=v48, rounds=1292 | A=v48 1020, B=f475 464, winner=v48, rounds=1216 | 2–0 |
| 00split | A=f475 990, B=v48 1007, winner=v48, rounds=732 | A=v48 990, B=f475 1007, winner=f475, rounds=732 | 1–1 |
| 00stampede | A=f475 506, B=v48 240, winner=f475, rounds=2000 | A=v48 506, B=f475 240, winner=v48, rounds=2000 | 1–1 |
| 00swirl | A=f475 136, B=v48 1019, winner=v48, rounds=787 | A=v48 60, B=f475 1071, winner=f475, rounds=765 | 1–1 |
| 01big-world | A=f475 719, B=v48 1012, winner=v48, rounds=1017 | A=v48 554, B=f475 1000, winner=f475, rounds=888 | 1–1 |
| 01boss-battle | A=f475 0, B=v48 1161, winner=v48, rounds=1152 | A=v48 227, B=f475 2332, winner=f475, rounds=1249 | 1–1 |
| 01broken-curve | A=f475 1000, B=v48 365, winner=f475, rounds=678 | A=v48 1000, B=f475 365, winner=v48, rounds=678 | 1–1 |
| 01concentrated-wealth | A=f475 1049, B=v48 78, winner=f475, rounds=973 | A=v48 1020, B=f475 73, winner=v48, rounds=896 | 1–1 |
| 01corridors | A=f475 1046, B=v48 436, winner=f475, rounds=1177 | A=v48 1046, B=f475 436, winner=v48, rounds=1177 | 1–1 |
| 01elk-arena | A=f475 216, B=v48 1008, winner=v48, rounds=1443 | A=v48 108, B=f475 1008, winner=f475, rounds=1293 | 1–1 |
| 01fracture | A=f475 1038, B=v48 375, winner=f475, rounds=1137 | A=v48 1003, B=f475 326, winner=v48, rounds=1185 | 1–1 |
| 01gold-rush | A=f475 1001, B=v48 374, winner=f475, rounds=1812 | A=v48 1001, B=f475 374, winner=v48, rounds=1812 | 1–1 |
| 01hooks | A=f475 44, B=v48 1012, winner=v48, rounds=1011 | A=v48 44, B=f475 1012, winner=f475, rounds=1011 | 1–1 |
| 01islands | A=f475 971, B=v48 1037, winner=v48, rounds=867 | A=v48 1025, B=f475 525, winner=v48, rounds=723 | 2–0 |
| 01shortcut | A=f475 1234, B=v48 128, winner=f475, rounds=1126 | A=v48 1234, B=f475 128, winner=v48, rounds=1126 | 1–1 |
| 01starfish | A=f475 1038, B=v48 44, winner=f475, rounds=939 | A=v48 1038, B=f475 44, winner=v48, rounds=939 | 1–1 |
| 01starvation | A=f475 1002, B=v48 218, winner=f475, rounds=1440 | A=v48 252, B=f475 1000, winner=f475, rounds=1624 | 0–2 |
| 01the-farm | A=f475 520, B=v48 1107, winner=v48, rounds=858 | A=v48 520, B=f475 1107, winner=f475, rounds=858 | 1–1 |
| 01yellow-brick-road | A=f475 575, B=v48 1006, winner=v48, rounds=775 | A=v48 1046, B=f475 704, winner=v48, rounds=683 | 2–0 |

## Selected cells

- `00gem-fields`: A=f475 1000, B=v48 983, winner=f475, rounds=635; swapped: A=v48 1000, B=f475 983, winner=v48, rounds=635.
- `01fracture`: A=f475 1038, B=v48 375, winner=f475, rounds=1137; swapped: A=v48 1003, B=f475 326, winner=v48, rounds=1185.
- `00ambush`: A=f475 353, B=v48 1000, winner=v48, rounds=871; swapped: A=v48 818, B=f475 1009, winner=f475, rounds=1106.
- `01concentrated-wealth`: A=f475 1049, B=v48 78, winner=f475, rounds=973; swapped: A=v48 1020, B=f475 73, winner=v48, rounds=896.
- `00eight`: A=f475 1571, B=v48 298, winner=f475, rounds=1371; swapped: A=v48 263, B=f475 993, winner=f475, rounds=2000.
- `01starvation`: A=f475 1002, B=v48 218, winner=f475, rounds=1440; swapped: A=v48 252, B=f475 1000, winner=f475, rounds=1624.

Machine-readable per-game results and payload hashes are in `batch-summary.json`; native rollover/error classifications are in `native-status-audit-80.json`; SDK/source/WASM postflight pins are in `batch-postflight.json`. Replays and full statistics remain in `planned-output/` as raw local artifacts.
