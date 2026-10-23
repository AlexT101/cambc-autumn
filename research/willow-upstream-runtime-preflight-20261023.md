# Willow upstream worktree runtime preflight (2026-10-23)

This is a read-only environment preflight plus a small opt-in update to `tools/run_batched.py`. No bot build or match was run; the first native panel is pending actual source-review clearance.

## Worktree and source pins

- Worktree: `/Users/yufan/Desktop/Development/CambridgeBattlecode2026/willow-upstream-development`
- Branch/HEAD: `codex/willow-upstream-20261023` / `8be8eaa11fdfe6b63668be6235bf9364be2ce05c`
- The checkout already contains unrelated root work: modified `research/EXPERIMENTS.md`, untracked `bots/baselines/hyperion-upstream-8be8eaa/`, `research/willow-upstream-coordinated-source-checkpoint.md`, and `research/willow-upstream-coordinated-source.patch`. This preflight did not edit those files.
- Candidate: `bots/variants/willow-upstream-coordinated-work`, canonical `shasum -a 256 src/* | shasum -a 256` aggregate `1670a7e8ea2c11424ec9b6759dc0fa6af14115cc2842eb60f63a310b6c6b534b`.
- Frozen reference: `bots/baselines/hyperion-upstream-8be8eaa`, same aggregate recipe yields `d8d3cc1da72aaf62eb65fc5de8402b9c3a98a8aade1fabeb5cd9841b3ff01e2c`.
- No `.cambc` build cache was found in either bot directory.

## Runtime and build compatibility

I read `cambc-rules.yaml`, `tools/README.md`, the root `AGENTS.md`, and the local CMake project. The rules set a 100,000 fuel budget per ordinary turn; native drafts are compiled into each bot. The workspace uses C++20 and compiles bot sources against `sdk/cpp` through `cmake/CMakeLists.txt`.

The pinned CLI is `/Users/yufan/Desktop/Development/CambridgeBattlecode2026/current-autumn/tools/runtime/cambc-3.0.5/cambc`, version `cambc 3.0.5`, SHA-256 `69617aa6a074415bd8ba8e254d1584df3392d95d1f9e2e2d46db66ff6e187171`. The local `tools/replay/engine/v1_0_3.wasm` is SHA-256 `029ecd290dc400e75418178ec386d72cbd7d9f2fc2a2e451bf594ca23566df48`; the CLI and engine match the previously used runtime pins. The published local map pool contains 40 `.map26a` files, with canonical path/hash manifest SHA-256 `d91015b45d05872848f3e7e09149c474b5af78dbfe4c7471a524fac70822784a`.

The current `tools/run_batched.py` did not support exact CLI selection or Release mode: it resolved `cambc` from `PATH`, built without `--release`, and ran `run-batch` without `--release`. I added opt-in `--cli PATH` and `--release` flags. When selected, `--cli` pins the executable and the script records path, version, SHA-256, and the actual build/run-batch argument lists in `results.json`; `--release` reaches both `cambc build` and `cambc run-batch`. Defaults remain PATH-resolved debug mode. Syntax and `--help` checks pass (`python3 -m py_compile tools/run_batched.py`). CLI help confirms `--release` is accepted by both build and run-batch.

Once source review clears the candidate, use the existing runner from this worktree with one process, one build worker, pinned CLI, and Release/default fuel:

```sh
nice -n 19 env CMAKE_BUILD_PARALLEL_LEVEL=1 python3 tools/run_batched.py \
  bots/variants/willow-upstream-coordinated-work \
  bots/baselines/hyperion-upstream-8be8eaa \
  --release \
  --cli /Users/yufan/Desktop/Development/CambridgeBattlecode2026/current-autumn/tools/runtime/cambc-3.0.5/cambc \
  --threads 1 \
  --output replays/willow-upstream-coordinated-vs-8be8eaa/batch-run-01-release-published40
```

This is the planned 40-map, both-sides native-draft panel; the runner will exclude `maps/gen*` directories. Afterward, run the compact native-status and both-side caught-act-error audits and pin source/map/runtime/result hashes.

## Match metadata availability

CLI help documents `cambc matches list --json` and `cambc matches show --json`; the list help says it includes map, teams, and draft choices. A read-only `matches list --team me --kind ranked --limit 1 --json` request returned HTTP 503 twice, so I could not inspect a current match response or verify whether it carries a submission/source-version field. No match group was queued and no submission command was called.
