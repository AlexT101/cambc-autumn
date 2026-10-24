# Compound Focus plus safe-yield full 1,104 comparison preflight

Prepared only; no build, match, extraction, or engine audit was run. The future output root `/Users/yufan/Desktop/Development/CambridgeBattlecode2026/willow-upstream-development/replays/willow-focus-safe-yield-vs-v33-a00fff-full1104-run01` remains absent. This package is ready for root review before execution.

Candidate: `/Users/yufan/Desktop/Development/CambridgeBattlecode2026/willow-upstream-development/bots/variants/willow-focus-safe-yield-work`, aggregate `9b405b0da9ddb7d9f79e698265546c2e69e42ce19c0fc0ea39bb19940bfa4007`. Frozen reference: `/Users/yufan/Desktop/Development/CambridgeBattlecode2026/willow-upstream-development/bots/baselines/hyperion-deployed-v33-a00fff`, aggregate `a00fff454c1e48520968c9ba2d4c1ecdae0212ce019724dc06a6e959ddc3412e`. Source-only copies of all 29 files per bot are under `source-snapshots/`; copies and external trees were compared file by file. No `.cambc` or compile database was copied. Both source trees declare `test_draft=false`, so native drafts remain unchanged.

The manifest schedules 552 maps: 40 published, 256 `gen` (seed 1023), and 256 `gen-s1` (seed 1024), with both candidate physical sides, for 1,104 unique `(source, opponent, map, side)` tuples and unique absolute replay outputs. All 552 map paths and hashes match the previously reviewed 4db-vs-v33 suite. Bot columns reverse when candidate side is B.

The candidate has no existing Release artifacts and needs a fresh build after authorization. Existing v33 artifacts match the pinned raw/injected hashes. Toolchain and SDK pins are recorded. `commands.json` records exact planned argv, working directories, and separate log paths. Neither command was executed.

Source proof: `/Users/yufan/Desktop/Development/CambridgeBattlecode2026/willow-upstream-development/provenance/willow-focus-safe-yield-20261023-v1/checkpoint-v1.md`; combined patch SHA256 `d47d2ab16dbe855b1180dbbb6d530f3949f483bd4de09eb1b12b5073a2f7c734`. The Focus and safe-yield removal proof file sets were checked against the combined source, with only the intended component file differing.
