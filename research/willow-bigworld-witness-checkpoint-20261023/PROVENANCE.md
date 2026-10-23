# Big World witness checkpoint provenance

This checkpoint preserves the compact evidence and final source instrumentation for the canonical337f physical-A Big World witness. It is a bounded diagnostic for rounds35–75. It does not include generated fuel tables, stdout dumps, WASM binaries, or replay bundles; those remain in the ignored replay workspace listed below and are pinned by SHA-256.

## Evidence and fidelity limits

- All 205 actor/round recorder segments match the trace by wrapper call count and hash: actors0–4, rounds35–75. Four native rollover points match, with no `@!` through round75.
- The recorder stdout ends partway through round267. The trace's first missing-tail records are at round268 (`@! tail 4 267 268`, followed by the corresponding fuel marker); do not interpret later wrapper errors as evidence about the target window.
- Fuel is not exact: recorder-vs-original candidate-A has actor3 round4 +40 (92,163 vs 92,123) and actor4 round470 +896 (53,894 vs 52,998). Strict fuel trust ends after round3. This trace is explicitly action/state-equivalent.
- Against both original and recorder, first action/input mismatch is round279 (actor4 Move `(76,9)->(75,10)` in trace vs `(76,9)->(75,8)` original); first round-state hash mismatch is round280. Thus the requested window precedes the first difference.
- At round41 Prism0 assigns local claim8 to group12 while Willow3 remains on group4; both start at 700 HP. Willow's remembered Prism position is stale/invisible (source round38), and Prism's remembered Willow position is stale/invisible (source round39). Prism's belief HP first falls to620 at round45, after the split. At round46 Willow sees Prism's current position and claim12, enters branch `h`, and clears its local claim to -1. The trace does not show rejected alternatives, internal rankings, or a specific support/heal recipient.

The checked-in table/report and raw `BW-*` rows are copied here. Machine-readable validation, phase2 fuel comparison, recorder coverage, and wrapper pins are also copied here. The v4 trace source manifest plus full `bot.cpp` diff and `bigworld_witness.h` reproduce the source instrumentation without relying on an incremental patch alone.

## Source and build pins

- Frozen gameplay source: `bots/variants/willow-fbda803-integrated-work/src`, 29 files, aggregate SHA-256 `337f42a54beb5890109e56b755237d8ea0d07abb240d095778f01e2098ab7b39`. Per-file hashes: `candidate-source-manifest.json`.
- Frozen emulator source: `bots/variants/hyperion-fish-roster-emulator-fbda803/src`, aggregate SHA-256 `10e5eeaabd57580f2ccd59240f36341209c2337fa9f190c8ea310b79943c90ac`. Per-file hashes: `emulator-source-manifest.json`.
- Final trace source manifest recipe aggregate: `e27b52f8c6f8c1efd3541cd727cabae267dc57d314565f00669f0834d195a6e7` (SHA-256 over sorted per-file SHA-256 hex strings).
- Final trace source standard aggregate: `12a6ae812694f6ab14248b56c72878bd00b7a71ea0945a8a800b139fbdaf09b2` (`shasum -a 256 src/* | shasum -a 256`). Keep these recipes distinct; both are reproduced in `build-pins.json`.
- Frozen emulator raw/injected WASM: `22fc50dfd1ab33d1e442e8882b1fe89572d61cb96980a7b629f774a5c255169b` / `f7873b5a06649bc0dfd9ae3bd9575fb629834b9b47e7823a09f517d0f5833175`. These Release identities were checked again after its debug-workspace build.
- Trace debug raw/injected WASM: `117870ecd5b168287d6e689d7220fe7df8dfac86460a859573ba373a508fd3f2` / `6ed8ae4b7465ea30cea21a89a0bc4ffaae4d06d1c4cd8340ac28ba380908cdfa`.
- CLI `cambc-3.0.5` SHA-256 `69617aa6a074415bd8ba8e254d1584df3392d95d1f9e2e2d46db66ff6e187171`; pinned v1.0.3 engine SHA-256 `029ecd290dc400e75418178ec386d72cbd7d9f2fc2a2e451bf594ca23566df48`.

## Replay and generated-data index

All paths below are relative to `replays/bigworld-branch-witness-20261023/` in this checkout:

| Artifact | Path | SHA-256 |
|---|---|---|
| Original source-matched game | `release-original/big-world-A.repl26a` | `4cb49d0749686d5855550ef198dbe5352d739ac2168e4be8af04710164b7a672` |
| Recorder game | `phase2-recorder/big-world-A-recorder.repl26a` | `226f2adc2237ac16ec1672b020dcd5dcd1e65778578935e106afa72be2ca5f63` |
| Recorder candidate stdout (truncated partway through r267) | `phase2-recorder/team-a.stdout.txt` | `5b77d627438944961ce31526b32ae0fc71e0d46d9d5ba8f69789735e5c8d50d1` |
| Trace game | `phase3-trace/big-world-A-trace-action-equivalent.repl26a` | `32cf75d4bfe09036305628cbefdeee77e2617d01959343d6260a18bf0737d76d` |
| Trace candidate stdout | `phase3-trace/team-a-stdout.bin` | `c4c12c69f0292ddd3fe368ebbff3b1a80ee6fb27565bc38f29ec9fe5596b6c76` |
| Generated `rec_data.cpp` (51,521 fuel reads, 4 rollovers, 1,336 segments, 6 instances) | `workspace/bots/willow337f-trace/src/rec_data.cpp` | `dae17d2f03ffd1b35036aa53eb3895ef4db620453859689609157a0d3078a626` |

The original match was selected from `replays/fish-roster-emulator-panel-20261023/02-integrated337f-vs-roster-emulator/003-01big-world-12.repl26a`; its payload equals the first row's hash. All these large artifacts remain preserved in the ignored replay tree and were not copied into this checkpoint.

## Reconstruction commands

Use the generic scripts in `tools/replay/harness`; do not run stock `setup_ws.py` or `trace_batch.py`, since they select v38 and manage/delete their own workspace. The source hook patch has no added SDK queries or policy logic. Start from the frozen 29-file source, copy `bigworld_witness.h`, apply `bot.cpp.instrumentation.diff`, and retain the v4 manifest to verify the resulting source. Use a fresh exclusive workspace and the workspace-local generic wrapper SDK patches documented in the original `RUNBOOK.md`.

Recorder and tracer wiring uses the generic harness tools:

```sh
python3 tools/replay/harness/gen_wrappers.py --mode rec --wasm <release-bot.wasm> --sdk <workspace>/sdk/cpp --out <rec-bot>/src/zz_harness.cpp
python3 tools/replay/harness/count_ops.py <rec-bot-wasm> --split
python3 tools/replay/harness/trace_data.py <recorder-team-a-stdout> <trace-bot>/src/rec_data.cpp
python3 tools/replay/harness/gen_wrappers.py --mode trace --all --sdk <workspace>/sdk/cpp --out <trace-bot>/src/zz_harness.cpp --rec-table <rec-bot>/src/zz_harness.json
```

The exact successful one-game manifest is `one-game-manifest-absolute.txt`; it pins the trace bot, fixed emulator, map and replay output. From the isolated workspace, build and run with one worker and low priority:

```sh
nice -n 19 env CMAKE_BUILD_PARALLEL_LEVEL=1 cambc build bots/willow337f-trace
nice -n 19 env CMAKE_BUILD_PARALLEL_LEVEL=1 cambc run-batch <absolute-path-to-one-game-manifest-absolute.txt> --jobs 1 --color never
```

Build and replay details are in `build-pins.json`, `pre-run-pins.json`, `RUNBOOK.md`, and the copied `REPORT.md`. Validate with `validation-window.json`, `phase2-recorder-verification.json`, `recorder-coverage.json`, `recorder-wrapper-pins.json`, both `compare-*.json` files, and `fuel-recorder-vs-trace.json`. Expected result is the target-window match and post-r267 tail boundary stated above.
