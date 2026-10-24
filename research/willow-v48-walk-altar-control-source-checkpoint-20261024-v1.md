# v48 walking-altar control source checkpoint

2026-10-24. Cambridge Battlecode rules read. Source-only regression isolation; no build, runtime, submission, tooling/helper implementation, canonical change or EXPERIMENTS edit. Farm-hop remains held.

Parent: frozen released `bots/Khaos_v34`, 29-file source aggregate verified before and after copying: `781fe3641afc4333d8c8a1b42f1344b4ba19edf9d96ae092e9e62069b9083d68`.

Child: `bots/variants/willow-v48-walk-altar-control-work`, src only, no `.cambc`. Its 29-entry manifest is `research/willow-v48-walk-altar-control-source-v1-manifest.sha256`; aggregate `c156da50c65ca11bf3da3ddec09a9cb285d02d5562dee1a72d45dfba8ab7bb4f`.

Patch: `research/willow-v48-walk-altar-control-source-v1.patch`, SHA256 `99dcde0bab5c48de062beac8ba770e97b025de8912a6afb63e54cd72cedb3641`.

Only `src/pathing.cpp` changes: 1 insertion, 2 deletions. `Pathing::centre_to_altar` again tries `map().drafted_altar_steps(group)` whenever its cache entry is empty, removing only the has-dash/crossable conditional and its explanatory comment. The existing own-field fallback remains. The resulting complete pathing.cpp is byte-identical to archived v47's file; other 28 source files match Khaos_v34 byte-for-byte.

The finishing-recall, shield-pricing, bound-elsewhere capture-allocation and midturn killed-enemy changes are retained. This controls the altar-distance lookup only; actual dash movement/routing is untouched. Params and draft sources are unchanged; default production draft remains selected (`test_draft=false`). No whitespace diagnostics, patch rejects, backup files or `.cambc` directories remain. These are source checks, not compilation or behavior results.
