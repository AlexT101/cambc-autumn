# Replay harness (v38, v47, v66)

Every script takes `--version` (default `v38`); [versions.py](versions.py) maps a version to its commit, bot, trace bot and data directory. To add a version, add a row there, then port `trace-bot/`'s instrumentation onto that commit's sources as `trace-bot-v47/` did. The [v47](#v47) and [v66](#v66) sections have their commands; the rest of this page describes v38.

**Engine by date:** ladder games before ~05:25 UTC on 2026-11-09 reproduce only under cambc 5.0.0 and later ones only under 5.0.1 (they stop out-of-fuel turns at different points, so a champion's turn after one differs in fuel, and so can the draft's 10M first turn; research/fastengine/RUNNER.md, "Re-check on 5.0.1"); every script uses the `cambc` on `PATH`, so put the matching one there (an old wheel: `pip download cambc==5.0.0 --no-deps`).

The harness re-runs the 390 ladder games that submission v38 (`bots/hyperion` at 5b02a02) played against top-20 teams. Each re-run pairs an opponent puppet with our real code. The harness proves every re-run reproduces its ladder game, records a per-turn trace of v38's decisions, and joins that trace with the game state in a Python loader.

- **Analysts** studying deaths, fight-sim predictions, ability timing, missed kills, gem losses, target oscillation and ward or bush blindness start at [the loader](#loader-v38libpy) and [EXAMPLES.md](EXAMPLES.md).
- **Trace format:** [TRACE_SCHEMA.md](trace-bot/TRACE_SCHEMA.md).

Status, 2026-10-23: the manifest now holds 830 games, every v38 game against the top 20 of 2026-10-22's ladder (471-359). All are re-run, validated, traced and extracted:
- release re-runs exact against the ladder: 830 / 830;
- recorder runs exact: 788 / 830;
- traces exact against their recorder run: 826 / 830, and 784 exact against the ladder.
  - The 4 others are 2 distinct games (1ad29aed-1, 24da266c-1 and 25933c0a-1 are byte-identical, plus f318bf0f-5). Each departs only in its last round (r520, r701), and `ladder_trusted_through` already stops before that round.

The validation section below describes the first 390 games.

**Layout.** Everything committed lives here:
- the pipeline scripts;
- `manifest.json`, the 390 games;
- `puppet/`, the opponent puppet template;
- `wrappers/`, the recorder and tracer import wrappers;
- `trace-bot/`, the instrumented v38 copy and its schema;
- `v38lib.py`, the loader;
- `calib/`, the calibration probe.

Everything generated goes under the gitignored `replays/v38-top20/`: the workspace `ws/`, `inputs/`, `runs/batch/` and `extract/`.

## To populate the data on your machine

Run everything from the repo root. Each step is idempotent or resumable, so after an interruption rerun the same command.

**Prerequisites:**
- Python 3 (`py`), Node 22+ and git on `PATH`.
- The 390 ladder replays and `.fuel` files at the manifest's paths (`replays/mine/...`, 67 MB and 16 MB). Download them with `py tools/fetch_replays.py --mine` (it needs the website cookie for submission versions). Check with:

  ```
  py -c "import json,os; m=json.load(open('tools/replay/harness/manifest.json',encoding='utf-8'))['games']; print(sum(not os.path.exists(g['replay']) or not os.path.exists(g['fuel']) for g in m), 'missing')"
  ```

### 1. cambc 3.0.5

The ladder ran engine v1_0_3, which ships with cambc 3.0.5, as does the repo's `cambc.toml`. Every harness script calls `cambc` from `PATH`; check with `cambc --version`. `setup_ws.py` still builds its own workspace, `replays/v38-top20/ws`, because it patches that workspace's SDK and cmake (below) and must not touch the tracked ones.

On its first build, cambc downloads wasi-sdk-33, cmake-3.31.8 and ninja-1.12.1 into its cache: `%LOCALAPPDATA%\cambc` on Windows, `~/.cache/cambc` on Linux. Without a proxy this just works. Behind a TLS-intercepting proxy the downloader fails TLS; see [Toolchain behind a proxy](#toolchain-behind-a-proxy).

### 2. The steps

Times: "4 cores" were measured here. "16 threads" is an estimate scaled from those measurements, not measured.

| # | command | 4 cores (measured) | 16 threads (estimate) | output |
|---|---|---|---|---|
| 1 | `py tools/replay/harness/setup_ws.py` | 35 s from nothing; afterwards only rebuilds | 20 s | `replays/v38-top20/ws`: patched SDK and cmake, maps, `bots/v38-release`, `bots/v38-rec` |
| 2 | `node tools/replay/harness/decode_all.mjs --list replays/v38-top20/ladder-list.json --out replays/v38-top20/inputs/ladder --threads 14` | 2 games in 7 s at 2 threads (3.3 s per game per thread) | 2-4 min (HANDOFF measured 4 min on 18 threads) | `inputs/ladder/<key>.json.gz` (110 MB) |
| 3 | `py tools/replay/harness/batch.py --jobs 12` | 41 min at `--jobs 3`: puppet builds 939 s, release runs 218 s, recorder runs 379 s, validation 735-926 s | about 10-15 min | `runs/batch/<key>/{puppet.json, release.repl26a, rec.repl26a, rec.stdout, validation.json, stamp.json}`, `runs/batch/validation.json`, `VALIDATION.md`; 390 puppets `ws/bots/p-<key>` |
| 4 | `py tools/replay/harness/trace_batch.py --all --slots 8` | 5 s per game per slot (16 games: 32 s build + 48 s run, 3.8 ms per round), plus about 32 s for each slot's first build | 390 games, 443k rounds: about 4-6 min at 8 slots; 14 min at the default 2 | `runs/batch/<key>/{trace.stdout.gz, trace.repl26a, trace_validation.json}`, `runs/batch/trace_validation.json` |
| 5 | `py tools/replay/harness/extract_all.py --threads 14` | 390 ladder games 756 s at 2 threads on a loaded machine, about 1.1 s per game per thread idle; 16 re-runs 35 s at 2 threads | 1-2 min | `extract/ladder/`, `extract/rerun/` (about 95 MB each), each with `keys.json` |
| 6 | `py tools/replay/harness/v38lib.py summary` | 1 s | 1 s | per-game availability and trust |
| 7 | `py tools/replay/harness/v38lib.py extract-check` | 4 s for 16 games | about 2 min | ladder vs re-run extract, per game |
| 8 | `py tools/replay/harness/v38lib.py examples --out replays/v38-top20/EXAMPLES.md` | 44 s for 16 games (21k rounds), 250 MB peak | about 15 min (single-threaded; 443k rounds; one game in memory at a time) | the worked examples |

**Expected results** (the engine and the harness are deterministic, so the user's numbers should equal these):
- Step 3 ends with `summary: 390 games, 369 exact in both runs (release 390, rec 369)`.
- In step 4 each game prints `rec EXACT` (the trace matches its recorder run). It prints `ladder EXACT` for the recorder-exact games and `trusted N/rounds` otherwise.
- Step 7 prints identical events and rounds for every game whose `ladder_trusted_through` equals its length.
- Anything else is a finding: the first mismatch is in `trace_validation.json` (`first_mismatch`, `mismatches`).

**Disk:** about 4.5 GB in all.
- `ws/`: 2.3 GB, mostly 390 puppets × 2 builds at about 5.3 MB, plus about 14 MB per tracer slot.
- `runs/batch/`: 1.1 GB before tracing (`rec.stdout` 0.8 GB). Tracing adds about 0.45 GB (`trace.repl26a` and `trace.stdout.gz`, about 0.5 KB each per round).
- `inputs/`: 0.1 GB; `extract/`: 0.2 GB.

**Options:**
- Every step takes `--keys K1,K2` to work on some games only.
- `batch.py --stages gen,build,release,rec,validate,summary` runs part of the pipeline.
- `--force` redoes work.
- `trace_batch.py --slot-prefix NAME` names its slot bots `ws/bots/<NAME><N>`; concurrent runs must use different prefixes, or they rebuild each other's slots.
- `trace_batch.py --level 2 --rounds R0-R1 --keys K --force` adds the level-2 detail (TF, TQ, TE `sides`, `cast_cand`, `farm_cand`) for a round window. Only `rec_data.cpp` is rebuilt.

**After a recorder change** (a new `harness_rec.h` changes the wasm stamps): `batch.py` reruns the recorder runs. A trace whose `rec.stdout` is newer than its `trace_validation.json` is then stale (`Game.trace_stale`), and the next `trace_batch.py` run redoes it.

### Windows

- **Interpreters:** all scripts run their Python helpers with `sys.executable` and look up `cambc` and `node` on `PATH`, so `py` and `cambc.exe` work unchanged. `setup_ws.py` also needs `git` on `PATH`.
- **Command-line length:** `extract_all.py` passes replays to extract.mjs 60 at a time to stay under the 32k-character limit.
- **Path length:** cmake object paths embed the full source path, for example `.cambc/build/CMakeFiles/bot.dir/<abs path>/main.cpp.obj`. If a build fails on path length, enable long paths or use a short clone path.
- **Quoting:** in PowerShell, quote `fuelcmp.py`'s glob as in the examples (`'OUT/*.repl26a'`).

### Toolchain behind a proxy

Fetch the toolchain into cambc's cache under the same directory names. The URLs below were checked (HTTP 200). The cmake and ninja sha256 values are the ones in the cambc 3.0.5 binary, and the extracted wasi-sdk `VERSION` equals the one cambc installs (`33.0+m`, llvm 22.1.0).

```
C=~/.cache/cambc; mkdir -p $C && cd $C
curl -fsSLO https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-33/wasi-sdk-33.0-x86_64-linux.tar.gz
tar xzf wasi-sdk-33.0-x86_64-linux.tar.gz && mv wasi-sdk-33.0-x86_64-linux wasi-sdk-33
curl -fsSLO https://github.com/Kitware/CMake/releases/download/v3.31.8/cmake-3.31.8-linux-x86_64.tar.gz
tar xzf cmake-3.31.8-linux-x86_64.tar.gz      # sha256 630615d8e98ac33eba7fbe472626dff5c899c85af3c024585ae109166a6909d0
curl -fsSLO https://github.com/ninja-build/ninja/releases/download/v1.12.1/ninja-linux.zip
mkdir -p ninja-1.12.1-linux-x86_64 && unzip -o ninja-linux.zip -d ninja-1.12.1-linux-x86_64   # sha256 6f98805688d19672bd699fbbfa2c2cf0fc054ac3df1f0e6a47664d963d530255
```

`count_ops.py` uses `wasi-sdk-33/bin/llvm-objdump` from the same cache.

### What `setup_ws.py` does

It is idempotent. From nothing it does all of this:

1. Runs `cambc init --yes`, then copies the manifest's 40 maps from the repo's `maps/`. They are byte-identical to the pool, and `ws/maps` names use `-` where the manifest uses `_`.
2. Patches `cmake/CMakeLists.txt`: a bot directory with a `RELEASE_CODE` file is compiled without `CAMBC_DEBUG` even in a debug run. The recorder is release code that uses the debug-only `fuel_pause` imports.
3. Patches `sdk/cpp/cambc.h`:
   - `DebugGuard`'s refund becomes the macro `CAMBC_DEBUG_REFUND`, 10 as in the existing workspace (`--refund 2` restores stock);
   - it gains the `cambc_debug_depth` counter the tracer's wrappers read.
4. Creates `bots/v38-release` from `git archive 5b02a02 bots/hyperion` and builds it `--release`.
5. Creates `bots/v38-rec`, the recorder:
   - v38's sources plus `RELEASE_CODE`, `harness_rec.h` and `zz_harness.cpp` from `gen_wrappers.py --mode rec`;
   - built with zero costs, then measured with `count_ops.py --split` into `bots/v38-rec/costs.json`;
   - regenerated with those costs and rebuilt, checking that the counts did not change.

6. Writes `ladder-list.json` if it is missing.

`trace_batch.py` runs it itself when the workspace lacks the SDK patch or the recorder's wrapper table.

## v47

v47 is `bots/astraeus` at f7d54e9e (hyperion's machinery plus the Willow layer; `willow_draft` on, `test_draft` off). Its trace bot is `trace-bot-v47/` (the v38 instrumentation ported, plus Willow-layer events: [TRACE_SCHEMA.md](trace-bot/TRACE_SCHEMA.md#v47-trace-bot-v47)). Data goes under `replays/v47/`, with bots `ws/bots/v47-release`, `v47-rec` and slots `v47-trace-s<N>`.

Its manifest is not committed: `build_manifest.py` builds `replays/v47/manifest.json` from the downloaded group folders (`replays/mine/*` and `replays/scrims/*/*` by default), keeping groups where our submission is 47. Groups whose `group.json` lacks versions (scrim_ladder.py's downloads) are resolved through the website with fetch_replays.py's cookie. Every step skips finished work, so after new downloads rerun the whole chain:

```
py tools/fetch_replays.py --mine --since 2026-10-24T05:17 --threads 1     # or scrim_ladder.py's folders
py tools/replay/harness/build_manifest.py --version v47
py tools/replay/harness/setup_ws.py --version v47                          # first time: ws, release + recorder; afterwards refreshes ladder-list.json
node tools/replay/harness/decode_all.mjs --list replays/v47/ladder-list.json --out replays/v47/inputs/ladder --threads 12
py tools/replay/harness/batch.py --version v47 --jobs 12
py tools/replay/harness/trace_batch.py --version v47 --all --slots 8
py tools/replay/harness/extract_all.py --version v47 --threads 12
py tools/replay/harness/v38lib.py --version v47 summary
```

In Python: `L.use("v47")` after `import v38lib as L` (or `HARNESS_VERSION=v47`).

`py tools/replay/harness/pipeline.py --version v47 [--jobs 12] [--slots 8]` runs the steps after the download in order (manifest, setup, decode, batch, trace, extract, summary).

**Status, 2026-10-24** (320 games in 64 groups: 2 ranked, the 50 scrims of `replays/scrims/20261024-011832` and 12 other unranked groups; `fetch_replays.py --mine` downloads our scrims too, and a group in both places is listed once):
- release re-runs exact against the ladder: 320 / 320. That proves f7d54e9e is the submitted v47 (e72724a0, the website's note, is not).
- recorder runs exact: 302 / 320. 17 of the 18 diverge at or within two rounds of the recorder's own `@x`, as in v38. 3499e13e-3 (00split) has no `@x` and diverges in round 1: champion 3's first move, after first-turn fuel differences of up to -4418. It is unexplained.
- traces exact against their recorder run: 320 / 320, and 302 exact against the ladder. `extract-check`: the 302 extracts are identical, and the other 18 first differ in the round after `ladder_trusted_through`.
- release per-turn fuel differs from the ladder `.fuel` in 39 games, unlike v38 (none). Nearly all are one turn +195 and a later one -195 for the same champion. d7071636-2 (47 turns) and dc868a05-3 (13) are larger. Inputs and hashes still match. A memory-layout difference between our build and the server's (a `memory.grow` landing on another turn) would fit; it is unconfirmed.

**Times** on 24 threads (`--jobs 12 --slots 8`): the first 175 games took decode 102 s, batch 769 s (440 s of it puppet builds) and trace 484 s. The next 145 games took 15 min for the whole chain: decode 93 s, batch 359 s, trace 306 s and extract 236 s. That is about 6-7 s of wall time per game. Disk: `ws/` 1.9 GB, `runs/` 1.3 GB (trace output 1.7 GB raw, gzipped), `extract/` 0.17 GB.

## v66

v66 is the ladder submission `bots/baselines/v66` (byte-identical to `git archive 4a7c25f6 bots/astraeus`; `test_draft` off, so the bots play their own drafts). Its games ran on engine v2_0_0 (patch 2.0.0), and the harness runs them with cambc 4.0.0, as `tools/replay/engine/version.json` lists it. Its trace bot is `trace-bot-v66/`: the instrumentation ported onto v66's layout, plus events for v66's new logic ([TRACE_SCHEMA.md](trace-bot/TRACE_SCHEMA.md#v66-trace-bot-v66)). Data goes under `replays/v66/`, with bots `ws/bots/v66-release`, `v66-rec` and slots `v66-trace-s<N>`.

The manifest is built from `replays/v66-farm/*`, the version row's `folders`: 122 five-game unranked groups, 610 games (412 distinct replays) against Intercontinental Fish (170), Mite (185), Univardisty of Shingtonwash (145) and prism best girl (110). They were played from 2026-10-31 19:21Z to 2026-11-01 15:30Z.

```
py tools/replay/harness/pipeline.py --version v66 --jobs 80 --slots 40     # all steps; or one by one as for v47
```

In Python, call `L.use("v66")` after `import v38lib as L`.

**Changes for cambc 4.0.0 / v66.**
- SDK 4.0.0 adds one import, `camp_group_capture_state`. Its cmake and `DebugGuard` text are unchanged, so `setup_ws.py`'s patches apply as they are.
- Sources with subdirectories are copied recursively by `setup_ws.py` (the recorder) and `trace_batch.py` (the slots).
- The replay decoder already handled the v2_0_0 snapshot.
- `build_manifest.py` takes a version's `folders`.
- One of v66's own debug lines had to change in the trace bot. `CREW GROUP` called `spawn_steps(g)` inside a debug block, and that call memoises a host-call walk. In the debug-built tracer, the later real call then made no host calls, so every game left the recording on champion 0's first turn. The plain v66 source, traced, did the same, which is how the cause was found: by file, enabling the bot's own debug blocks one translation unit at a time.

**Status, 2026-11-01:**
- **Release re-runs:** exact against the ladder in 610 / 610 games (inputs, round hashes, result). Per-turn fuel equals the ladder `.fuel` on every turn of every game. That proves `bots/baselines/v66` is the submitted v66 and that cambc 4.0.0 reproduces engine v2_0_0.
- **Recorder runs:** exact in 472 / 610. All 138 divergences follow an `@x` of the diverging champion:
  - 135 in that round or the one before;
  - 99906c0a-3 and 6228191e-1 (the same replay) diverge 7 rounds after one;
  - 99ed458c-2 diverges 3 rounds after a first-turn `@x`.

  v66 runs out of fuel far more than v38 did. There are 5,027 ladder rollovers in 492 games, and 1,364 `@x` in 387 games (v38: 344 in 134 of 390). 26 games diverge in rounds 1-3, after a first-turn `@x`. The median first diverging round is 185.
- **Traces:**
  - Exact against their recorder run in 609 / 610 games (4,868 / 4,868 out-of-fuel points reproduced), and 472 exact against the ladder.
  - The other one, 329fc48c-5, differs only in the game's last turn (r1614, champion 4). Its recorder segment there ran out of fuel and the game ended before another host call, so no `@r` was logged. Its `ladder_trusted_through` is r687 anyway.
- **Coverage:** 470,879 of 570,056 rounds (82.6%) are trusted. In the 138 diverged games the median trusted share is 19%.
- **`extract-check`:** the 472 exact games' ladder and re-run extracts are identical. In all 138 others, the first difference is the round after `ladder_trusted_through`.

**Times** (this 96-core box, `--jobs 80 --slots 40`, 610 games): about 12.5 min for the whole chain.

| step | time |
|---|---|
| `setup_ws.py` (from nothing) | 77 s |
| decode | 58 s |
| batch | 248 s: puppet builds 42 s, release 43 s, recorder 84 s, validate 72 s |
| trace | 264 s, about 30 s of it each slot's first build |
| extract | 170 s |

**Disk:** 6.9 GB in all.
- `ws/`: 4.3 GB, mostly 610 puppets × 2 builds.
- `runs/`: 2.1 GB. The traces are 3.6 GB raw, gzipped.
- `extract/`: 0.29 GB; `inputs/`: 0.17 GB.

## How the from-scratch path was tested

On 2026-10-23, on this machine (Linux, 4 cores), the whole pipeline ran end to end for two games: c33d9c82-1 (side a, 58 rollovers, 7 `@x`) and 055ecd37-1 (side b, 4v4).

**Isolation.**
- `batch.py`, `trace_batch.py`, `extract_all.py` and `v38lib.py` hardcode `replays/v38-top20/` relative to their own location: the workspace `ws/`, `runs/batch/`, `inputs/` and `extract/`. Only `setup_ws.py --ws DIR` and `trace_batch.py --batch DIR` take other paths.
- So the test used a `git worktree` of HEAD in the scratchpad, with its `replays/v38-top20/ws` deleted and replaced by a symlink to a fresh `setup_ws.py --ws <scratchpad>/ws-fresh`.
- The two games' ladder replay folders were copied in. Every script then ran with its default paths.

**Results.**

| step | result |
|---|---|
| `setup_ws.py` | 35 s; v38-release wasm sha1 `a0005dd0d1960ae2` and v38-rec `df9a1fbc4d243b56`, identical to the workspace that produced the published runs (the stamps in `stamp.json`); recorder sources identical |
| decode | 7 s |
| `batch.py --keys ... --jobs 2` | 60 s: gen 0, build 37, release 7, recorder 10, validate 7. Both games exact in both runs. `rec.stdout`, `puppet.json` and `stamp.json` byte-identical to the published runs. |
| `trace_batch.py --keys ... --slots 2` | 54 s, including both slots' first builds. `rec EXACT ladder EXACT` for both, and `trace.stdout.gz` byte-identical to the published traces. |
| `extract_all.py --keys ...` | 11 s for both kinds |
| loader | `summary`, `extract-check` (identical extracts) and `examples` all ran |

The user's machine needs none of this isolation: it uses the default `replays/v38-top20/ws`.

## Validation (final)

From `runs/batch/validation.json`, `VALIDATION.md` and `trace_validation.json`, 2026-10-23.

| check | result |
|---|---|
| games | 390: 330 distinct replays, because 60 keys are byte-identical rematches of another key |
| release re-run (v38 `--release` against the puppet) exact against the ladder: every input of both teams, every round-start hash, the result | **390 / 390** |
| release per-turn fuel against the ladder `.fuel` | equal on every turn of all 390 games |
| recorder re-run exact against the ladder | **369 / 390** |
| rounds the recorder run shares with the ladder | 423,300 / 442,805 (95.6%) |
| recorder per-turn fuel against the ladder | 261 games and 57,022 turns differ, nearly all of them in the 21 divergent games; in the 369 exact games, 240 games and 525 turns (below) |
| traced games | 16; **16/16 exact against their recorder runs**: 92,970 / 92,970 segments with equal call counts and hashes, identical inputs (rollovers included), round hashes and results; 1118/1118 out-of-fuel points reproduced |
| traced games exact against the ladder | 13 / 16; 1c870553-3, b0a77e05-2 and eb003a5a-1 are trusted through r45, r199 and r683 |
| ladder against re-run extract (`extract-check`) | identical events and per-round state in the 13 exact traced games; the other 3 first differ in the round after `ladder_trusted_through` |
| joins (EXAMPLES.md, 16 games) | turn order from the rules equals every action's turn index (162,159); TB `v` equals the engine's `sees` (324,284 beliefs); TT `p` equals the extract's position on 71,575 of 71,583 turns, the 8 others each the turn after one that ran out of fuel |

### `@x` points

The recorder logs `@r me seg idx round` when a turn runs out of fuel before host call `idx` and resumes in `round`.

- **What `@x` means.** `@x me seg idx` follows an `@r` when the bot stopped at the recorder wrapper's own entry check. An import whose price exceeds the fuel left still completes, at 0 fuel, and the bot keeps running until its next fuel check (a function entry or loop header). So the unwrapped ladder bot would have made call `idx` in the old round at 0 fuel, and possibly ended its turn normally.
- **Why it matters.** From an `@x` on, the recorder's game is only loosely the ladder's, and `ladder_trusted_through` measures how far it still matches.
- **Counts.** There are 344 `@x` in 134 games, and 113 of those games stay ladder-exact.

### The 21 recorder divergences

"First round" is the first differing input or round hash. In the cause class, an `@x` counts in the round its turn ran out (its `@r` round minus 1).

Agent A counts 19 at the diverging champion's `@x` in that round or the next, 52cd89f1-5 three rounds after one, and 8ef1fd8e-3 after a teammate's in round 3. The recount here differs only in how rounds are attributed.

| key | map | rounds | first round | champion | ladder input | re-run input | `@x` | cause class | fuel turns differing |
|---|---|---|---|---|---|---|---|---|---|
| db84c66d-1 | 00ambush | 1049 | 3 | 9 | End turn | Cancel channel | 4 | own `@x`, same or previous round | 5374 |
| f84c4b27-5 | 01boss_battle | 1310 | 3 | 4 | End turn | Cancel channel | 1 | own `@x`, same or previous round | 6527 |
| 68218e06-5 | 00reverse_spiral | 1509 | 3 | 6 | Attack | Turn rollover | 13 | own `@x`, same or previous round | 6026 |
| 18f0204b-4 | 01yellow_brick_road | 613 | 33 | 1 | Recall | Turn rollover | 3 | own `@x`, same or previous round | 13 |
| 18f0204b-1 | 00lost_world | 781 | 34 | 4 | Move | Turn rollover | 1 | own `@x`, same or previous round | 3731 |
| 1c870553-3 | 01elk_arena | 2000 | 46 | 1 | End turn | Cancel channel | 1 | own `@x`, same or previous round | 9750 |
| 8ef1fd8e-3 | 01boss_battle | 1059 | 47 | 0 | Move | Move | 2 | teammate's `@x` (r2) | 1771 |
| 52cd89f1-5 | 00swirl | 1047 | 94 | 3 | Attack | Move | 1 | own `@x` 4 rounds before | 3813 |
| 70ca96ce-4 | 01starfish | 955 | 144 | 3 | Recall | Turn rollover | 8 | own `@x`, same or previous round | 16 |
| b0a77e05-2 | 00reverse_spiral | 1619 | 200 | 4 | Set priority | Turn rollover | 36 | own `@x`, same or previous round | 58 |
| 1c870553-1 | 00contest | 1296 | 214 | 2 | Move | Move | 3 | own `@x`, same or previous round | 5376 |
| ee58f35b-2 | 00fragment | 1698 | 291 | 5 | Attack | Turn rollover | 1 | own `@x`, same or previous round | 1 |
| 9317bf57-2 | 00corners | 1109 | 420 | 2 | Recall | Turn rollover | 3 | own `@x`, same or previous round | 21 |
| 68218e06-1 | 00eight | 1180 | 465 | 9 | Move | Turn rollover | 3 | own `@x` 2 rounds before | 3576 |
| 76b6692e-1 | 01starfish | 1058 | 546 | 8 | Cast ability | Turn rollover | 5 | own `@x`, same or previous round | 2555 |
| 1fd519dc-4 | 00split | 844 | 564 | 9 | Attack | Turn rollover | 2 | own `@x`, same or previous round | 1357 |
| 2fd6c5aa-5 | 01elk_arena | 2000 | 677 | 9 | Attack | Turn rollover | 10 | own `@x`, same or previous round | 39 |
| eb003a5a-1 | 01starfish | 1700 | 684 | 3 | End turn | Attack | 2 | own `@x`, same or previous round | 5083 |
| 2721e800-2 | 00contest | 1452 | 1262 | 9 | Recall | Turn rollover | 3 | own `@x`, same or previous round | 8 |
| bad729ff-1 | 00stampede | 2000 | 1527 | 8 | Recall | Turn rollover | 8 | own `@x`, same or previous round | 14 |
| db84c66d-2 | 01gold_rush | 2000 | 1538 | 2 | Turn rollover | Cast ability | 2 | own `@x`, same or previous round | 1388 |

The release runs of all 21 are exact, so the divergence is the recorder's.

### Recorder fuel mismatches in the 369 exact games

525 turns differ in 240 games. Recounted from `validation.json`:
- 143 draft first turns in 143 games;
- 100 champion first turns;
- 282 later turns.

Agent A's breakdown of the same turns:
- draft first turns in 151 games;
- 104 champion first turns;
- 238 `@x`-resumed turns in 125 games;
- 121 "other" turns in 39 games, small runs such as -15 on several champions in one round, unexplained.

None of them changes an input or round hash, since the games are exact. They matter only where a fuel read gates a decision, and the trace replays the recorder's reads.

## Data

### Trace (summary of TRACE_SCHEMA.md)

The trace is our team's stdout from the traced run, `runs/batch/<key>/trace.stdout.gz`. Each line is a tag followed by `key=value` fields, joined on `r` (round) and `c` (champion id, the same id as in the extract). Absent optional fields mean "no" or "none".

| tag | one per | holds |
|---|---|---|
| `TV` | champion instance | type, team, verbosity level, round window |
| `TT` | champion turn | see the TT fields below |
| `TB` | living enemy per turn (allies at level 2) | belief after the world update and comms merge: visible `v`, position `p`, the fix's round `pr` and source `src` (`s` seen, `c` comms, `i` inferred), health `h/m`, gems, channel, earliest cast rounds `rr`, tracking (`np` possible tiles), `bu` on a bush |
| `TA` | action call | import, int args `x`, engine return code `rc`, `ok` (0 with `rc=0` is a hidden blocker), decision site `s` |
| `TS` | strike-search run | see the TS fields below |
| `TE` | decision event | `decide`, `home` (retreat and `why`), `tribute`, `recall`, `carry`, `prey`, `prey_fight`, `ender`, `farm`, `cast`, `comms_rx`, `comms_tx`; level 2 adds `sides`, `cast_cand`, `farm_cand` |
| `TF`, `TQ` | level 2 only | every fight result and every threat value computed |
| `@v`, `@o`, `@!` | harness | per segment: host-call count and hash; reproduced out-of-fuel points; mismatches (`@! tail` is the expected final segment) |
| `D`, `SRCH`, `FSEED`, ... | v38's own debug lines | positional; the loader keeps them as `Turn.debug` |

**TT fields:**
- start and end position (`p`/`q`) and health (`hp`/`hq`), max health `mh`, shield `sh`;
- gems carried `g`/`gq`, gold `au`;
- the turn's branch `d` (`F` farm, `R` retreat, `C` chase, `A` attack, `B` bank, ...);
- `dmg`, health lost since our previous turn;
- cooldowns `cd`/`cq`, channel `ch`/`chq`, ward `wd`, bush `bu`, vision size `vis`, the last fuel read `fu`;
- the fight sim at the start and end tile, `fs`/`fe` (`lost:tku:tkt:falls:allies:enemies`);
- the lethal bound `ls`/`le` (worst-case damage before our next turn; -1 means the cheap bound proved it below our health);
- camp damage `cs`/`ce`, threatened `ts`, and `ok=0` for a turn that did not complete.

**TS fields:**
- the chosen end tile `ch` and its score `tot`, with `raw` and `gain`;
- the action sequence `seq`;
- `rm`: enemy indices taken out of the end tile's danger, killed or stunned;
- `kl`: the part of `rm` that is killed;
- `alt` (`x,y:total:rm:kl:exact`);
- `kill=` and `stun=`: per enemy handle, the best plan that kills it, or stuns it without killing it, with that plan's value and end tile. An enemy in `kill=` but not in `kl` is a rejected kill.

### Extract

[tools/replay/README.md](../README.md) documents the extract format: `meta.json`, `events.jsonl.gz` (one event per engine step), `rounds.json.gz` (state at each round end) and `maps/`. `extract/<world>/keys.json` maps each key to its cache directory. A camp kill's `death` event carries `camp: <camp id>` and no `by`.

## Loader: `v38lib.py`

The loader uses only the standard library; `to_frame` needs pandas.

```python
import sys; sys.path.insert(0, "tools/replay/harness")
import v38lib as L

g = L.load_game("f974cb55-1")                  # world="ladder" (default) or "rerun"
for d in g.deaths("us"):                        # Death: r, t, v, victim, by, killer, camp, gems, assists, linked, trusted, event
    for t in g.window(d.r, d.v, before=5):      # Turn
        print(t.r, t.tt.d, t.tt.hp, t.actual, t.predicted, t.belief(d.by))
L.games(filter={"map": "00swirl"}, traced=True, distinct=True)
```

| API | returns |
|---|---|
| `manifest()`, `keys()`, `traced_keys()` | manifest rows by key; all keys; keys with an ok trace |
| `load_game(key, world)`, `games(filter, traced, world, distinct)` | `Game`. `filter` is a callable or a dict of manifest fields; `distinct` keeps one key per replay content (624 of the 830), preferring a traced copy; a few rematches have different replay bytes and are not merged. |
| `Game` fields | `key`, `row`, `map_name`, `our_side`, `our_team`, `opponent`, `rounds_played`, `result`, `ours`, `theirs`, `champions` |
| validation | `validation` (the per-game file, or its row of the summary while `batch.py` redoes it), `trace_validation`, `traced`, `trace_stale`, `ladder_trusted_through`, `rec_ladder_trusted_through`, `trusted(r)`, `replay_sha` |
| extract | `has_extract`, `meta`, `map` (with `bush_set`, `wall_set`), `on_spawn(p)`, `events`, `events_in_round(r)`, `events_where(kinds, rounds, actor, about)`, `state(r, c)` (end of round r), `positions(r)`, `positions_at(r, t)` (at the start of turn t, after its timers), `turn_order(r)`, `turn_index(r, c)`, `check_turn_order()` |
| damage | `damage_events(c, (r, t), (r, t))`; `damage_after(r, c)`, also called `actual_damage(r, c)`: health plus shield lost between c's turns in r and r+1 |
| deaths | `deaths(team)`, with `team` `"us"`, `"them"` or `"all"` |
| trace | `records` (every `Rec`), `trace(r, c)` (`{tag: [Rec]}`), `harness` (the `@` lines), `instances` (TV lines), `enemy_index()` (TB index to handle), `to_frame(tag)` |
| turns | `turn(r, c)`, `turns(champ, rounds, trusted_only)`, `window(r, c, before=5, after=0)` |
| `Turn` | `tt`, `tb` (enemies), `tb_allies`, `ta`, `ts`, `te`, `tf`, `tq`, `debug`, `trusted`, `t`, `start` / `end` (extract state), `events` (its own turn's), `actual`, `predicted` (`lethal`, `camp`, `fight` valid at the end tile; `lethal_start`, `fight_start`, `camp_start`; `stayed`), `belief(handle)`, `te_kind(k)`, `ran_out` |
| `Rec` | a dict with attribute access (missing fields read as None), plus `tag` and `line` (the raw line). Values are typed: `(x, y)` tuples, `a/b` and `a,b` pairs, `Fight(lost, tku, tkt, falls, allies, enemies)`, `rm` and `kl` as ints, `seq` as `[{op, slot, target, tile}]`, `alt` as `[{tile, total, rm, kl, exact}]`, `kill` / `stun` as `{handle: (value, tile)}`. `"?"` and `"none"` stay strings. |
| `extract_diff(key)` | the first difference between the ladder and re-run extracts |
| CLI | `py tools/replay/harness/v38lib.py summary [--all]`, `extract-check [K1,K2]`, `examples [--keys] [--out] [--world] [--detail N]` |

**Worlds.** `"ladder"` pairs the trace with the ladder replay's extract, which the trace explains through `ladder_trusted_through` (`trusted(r)`). `"rerun"` pairs it with the traced run's own replay, which it always matches, but after the divergence the opponent puppet replays the ladder's inputs blindly.

**Missing data.** An untraced game has no records, `traced` False, `trusted()` False and `ladder_trusted_through` None, and still full extract access. A game without an extract raises `LookupError` naming the `extract_all.py` command.

**Memory.** A 2000-round game takes about 220 MB loaded, so loop over games and drop each, as the examples do.

## Caveats

- **Trust.** `ladder_trusted_through` is the last round the recorder run, and so the trace, shares with the ladder: one less than the first differing input or round hash. After it the game is a different one. Use `trusted(r)`, or the rerun world.
- **TT `dmg` under-reports.** It is health lost since the previous turn's end:
  - shields hide damage (Heart of Ruin);
  - on our own spawn the turn-end heal comes after `hq` is read, so damage taken there is partly invisible (b0a77e05-2 r1: Vesper took 120 and shows `dmg=10`).

  `Turn.actual`, built from the extract's damage events (health plus shield), is the comparable figure.
- **`?` values.** `?` means asked but not evaluated, `none` means no threat reaches the tile, and an absent field means no or none. `fe` is almost always `?`, so end-tile fight predictions exist only when the champion did not move (`Turn.predicted`).
- **Turns without TT lines.** A turn the bot skips before `play_turn` (a stale world update) prints no TT. In the 16 games' trusted rounds this happens on 19 champion turns, all in a game's last round after the deciding tribute (extract `turn` 0).
- **Out-of-fuel turns.** A turn that runs out of fuel resumes the next round. It prints `TT r=<old> ok=0` in the new round, after the stale turn's actions (168 in trusted rounds), and the new round's TT starts from the position after those actions. `Turn.ran_out` and the `@o` lines mark these turns; use `Turn.actual` rather than their TT end fields.
- **First-turn residuals.** The recorder's first turns use a little more fuel than the ladder's: for example +164 on the draft's first turn and +3 / +9 on two champions' first turns in f974cb55-1. They are most likely chunked-fuel effects on the 2x and 10x first-turn budgets; the cause is unconfirmed. They change no exact game.
- **The 121 "other" fuel turns.** These are recorder fuel differences in exact games that are neither first turns nor `@x`-resumed (agent A, 39 games), for example -15 on several champions in one round. They are unexplained.
- **Rematches.** Many manifest keys are byte-identical to another key's replay (deterministic rematches): 830 keys, 624 distinct. Use `games(distinct=True)` for rates.
- **Blocked steps.** A ladder replay does not record which action a `Movement blocked` step attempted. The puppet tries every feasible action, ward first; with that order all 390 release runs are exact.
- **Engine facts** (probed by agents A and B on engine 1.0.3; none contradicts cambc-rules.yaml):
  - `bc_round_number` clears the engine's last error, so a hook that queries the round between a failing call and `bc_get_last_error` changes the bot's path. The recorder and tracer query the round only after a call that returned 0.
  - An import whose price exceeds the fuel left still completes, leaving fuel at 0. The bot stops only at its next fuel check (a wasm function entry or loop header) and can make more imports, or yield normally, before it. This is why `@x` exists. cambc-rules.yaml says "running out suspends the bot"; this pins down when.
  - `fuel_adjust(+N)` caps only the reading: `fuel_remaining()` never shows more than the budget, but the excess is real hidden fuel (`tools/probes/probe-fueladjust-b`). Agent A's "caps at the budget" describes the reading; agent B's "hidden fuel" is right about what work can be done.
    - At 91312, +20000 reads 100000 and about 11.3k of work runs before the reading drops; +1e7 and +1e9 are likewise spendable in full within the turn.
    - The excess is lost at the turn's end, and a drain (`-2^62`) clears it.
    - A first turn is two 100k chunks. In the first chunk readings cap at 200000, and in the second at 100000. A drain empties only the current chunk: in the first it reads 100000, and a second drain with no fuel check in between still reads 100000. In the second chunk a drain reads 0. The tracer's drain loop has a fuel check at its back-edge, so it empties both chunks.
    - Below the cap, a refund raises the reading by exactly N, whether paused or not.
    - The tracer relies on the hidden fuel, which is real.
    - The recorder's refunds only return fuel the wrapper spent, so they can pass the cap only on a first turn, when a wrapper's unpaused operators straddle a chunk boundary. The excess is then hidden: the bot's next reads show up to that many fuel less than unwrapped, and `fuel_after` overstates the reading. This is a candidate for the first-turn residuals; it is unconfirmed.
  - The turn order and the turn-end spawn heal behave as the rules say (the join checks above).
- **`debug_block` is not free.** An empty block costs about 8 fuel beyond the SDK's refund, and a debug build's codegen differs, so a debug build is not fuel-exact. This is why the harness virtualises fuel from a release-code recorder instead of tracing a debug build. AGENTS.md and research/EXPERIMENTS.md now say so.
- **Re-run extracts** have no ladder `group.json`, so extract.mjs checks only their internal consistency; `extract-check` compares them with the ladder extract.

## Files

| Path | What |
|---|---|
All paths are under `tools/replay/harness/` unless they start with `replays/`.

| Path | What |
|---|---|
| `manifest.json` | the 390 games |
| `README.md`, `EXAMPLES.md`, `trace-bot/TRACE_SCHEMA.md` | docs |
| `setup_ws.py`, `extract_all.py` | workspace setup; extract runner |
| `decode_all.mjs`, `inputs.mjs` | decode ladder input streams |
| `gen_puppet.mjs`, `puppet/` | opponent puppet |
| `batch.py`, `validate_batch.mjs`, `compare.mjs`, `fuelcmp.py` | release and recorder runs, validation |
| `gen_wrappers.py`, `count_ops.py`, `wrappers/` | recorder and tracer import wrappers |
| `trace_data.py`, `trace_batch.py` | tracer data and runner |
| `trace-bot/` | v38 plus read-only decision logging |
| `trace-bot-v47/` | v47 with the same logging (TRACE_SCHEMA.md, section v47) |
| `trace-bot-v66/` | v66 with the logging and v66's own events (TRACE_SCHEMA.md, section v66) |
| `versions.py`, `build_manifest.py`, `pipeline.py` | the version table; a generated manifest from replay folders; the whole chain in one command |
| `v38lib.py`, `v38lib_examples.py` | loader (`use(version)`) and examples |
| `calib/`, `dumpsteps.mjs` | calibration probe; raw step dump |
| `replays/v38-top20/ws/` | generated cambc 3.0.5 workspace: patched `cmake/` and `sdk/`, the maps, `bots/v38-release`, `bots/v38-rec`, puppets `bots/p-<key>` and tracer slots `bots/v38-trace-s<N>` |
| `replays/v38-top20/ladder-list.json`, `inputs/`, `runs/batch/`, `extract/` | generated |

A single game can also be checked by hand, from `replays/v38-top20/ws` (verified):

```
cambc run bots/v38-release bots/p-f974cb55-1 --map 00gem-fields --release -o OUT
node ../../../tools/replay/harness/compare.mjs ../inputs/ladder/f974cb55-1.json.gz OUT/*.repl26a      # "exact": true
py ../../../tools/replay/harness/fuelcmp.py ../../mine/20261022-215614-3-vs-Pantheon-f974cb55/1-00gem_fields.team-a.fuel 'OUT/*.repl26a'    # ndiff 0
```

The puppet comes from:

```
node tools/replay/harness/gen_puppet.mjs replays/v38-top20/inputs/ladder/<key>.json.gz <1 if our_side is a, else 0> replays/v38-top20/ws/bots/p-<key>
```

Then build it with `cambc build`, in debug and also `--release` for the release run.
