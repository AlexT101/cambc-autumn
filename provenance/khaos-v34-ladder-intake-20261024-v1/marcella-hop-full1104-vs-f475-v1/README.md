# M+H versus f475 full1104 comparison

This extends the completed M+H versus frozen f475 published40 comparison to the exact published40 + gen + gen-s1 full1104 map frame. The published40 section reuses 80 exact source-pinned A/B cells from the completed 480-row panel; 1,024 generated-map games were newly run. Generated suites are development maps, not an untouched holdout.

`PLAN.json`, `ROWS.tsv`, `RUN.manifest`, and `REUSE-80.tsv` preserve the approved ordered rows and source/map pins. `EXECUTION-STATUS.json` records the completed six-worker native release run. `FULL-RESULT.json` and `.md` aggregate native statistics across all 1,104 cells using explicit source labels; `NATIVE-PHASE-RESULT.json` combines the new per-replay native phase audit with the prior exact-80 reuse audit. Raw replays and per-game statistics remain under `outputs/` for local verification.
