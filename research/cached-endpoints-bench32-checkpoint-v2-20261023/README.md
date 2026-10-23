# Cached endpoints fuel-bench checkpoint

Pins the reviewed a67 comms optimization, teacher control, canonical 337f parent, emulator, compiler, replay engine, and the 32-game fuel-only comparison. The reviewed a67 source aggregate remains authoritative.

The a67 patch and a67/teacher source manifests are copied byte-for-byte from verified recovery archives. Their 29 per-file hashes were cross-checked against live source trees and source-only archives. Canonical 337f and emulator source and built-WASM pins are also recorded.

The benchmark used the unchanged `tools/fuel/bench.py` default eight-map set against the emulator for both sides, with Release, 100M fuel, one job, and no test-draft. The safe adapter refuses cleanup of existing paths. Results: 16/16 exact unwrapped replay payload matches; total play fuel decreased by 13,638,323 (-0.41%), with 83,785 turns cheaper and 50 dearer. See the reconciliation for each map/side roster, outcome, payload hash and fuel total.

Exact CLI argv, source/manifest pins and binary hashes are in `checkpoint.json`.
