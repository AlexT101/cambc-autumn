# M+H vs f475, full 1,104-cell frame

The frame combines 1,024 new `gen`/`gen-s1` games with the exact 80 published40 M+H/f475 rows listed in `REUSE-80.tsv`. The two generated suites are development maps, not an untouched holdout. Results below use explicit source identities and the tested source-side aggregator. Scores are submitted gems; they are not a separate game-score measure.

Overall: 542/1104 M+H wins.

|Suite|Cells|M+H wins|M+H A-side wins|M+H B-side wins|Mean rounds|M+H submitted gems|f475 submitted gems|
|---|---:|---:|---:|---:|---:|---:|---:|
|gen|512|249|112|137|1084.92|392179|401206|
|gen-s1|512|249|133|116|1157.16|392774|398021|
|published40|80|44|29|15|1085.08|59695|55776|

|Native picks per side|Cells|M+H wins|M+H A-side wins|M+H B-side wins|Mean rounds|M+H submitted gems|f475 submitted gems|
|---:|---:|---:|---:|---:|---:|---:|---:|
|3|348|171|82|89|1140.66|258122|266855|
|4|330|167|87|80|1118.8|251197|243672|
|5|426|204|105|99|1100.0|335329|344476|

## Native replay phase audit

The 1,024 new cells were scanned with the pinned v1_0_3 compact-timeline auditor. Across those cells, M+H had 2647 play rollovers and f475 had 2672; there were no bot errors in play, draft, or other phases. The exact 80 reused published cells have 258 M+H and 248 f475 play rollovers, with zero errors. Full-frame source and physical-side counts are in `NATIVE-PHASE-RESULT.json`.
