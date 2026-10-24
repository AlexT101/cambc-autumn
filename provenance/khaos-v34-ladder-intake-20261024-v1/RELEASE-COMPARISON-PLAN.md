# Local Release comparison plan (not run)

Created for root review. No build, SDK refresh, match, or output row was executed. The plan has **80 f475-vs-v48 rows** (all 40 published `*.map26a` maps in both physical orientations) and **5 v48-vs-frozen-v33 rows** on specified recent-loss map/side cells.

The exact A/B assignments, output paths, map hashes, source aggregates, raw and injected WASM pins, and CLI/engine pins are in `release-comparison-plan.json`. The two pending manifests preserve that order row by row.

The 40-map comparison pairs the frozen f475 Release artifact against the local Khaos_v34 source build (same source aggregate) and swaps A/B for each map. The five opponent controls put v48 on Gem Fields A, Fracture B, Ambush A and B, and Concentrated Wealth B; v33 occupies the opposite side. Every row uses normal native drafts.

Proposed runner settings are `--jobs 1 --release --fuel-quantum 100000` under `nice -n 19`. The `run-batch` command is proposed only. Before execution, root should confirm that it consumes the existing pinned `.cambc/build-release/bot-injected.wasm` artifacts without rebuilding the source projects or refreshing SDK files. No result or competitiveness claim follows from this plan.
