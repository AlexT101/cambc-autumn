# Replay harness (live versions)

Re-runs a live submission's scrim games with our real code against a puppet of the opponent's recorded inputs,
proves each re-run reproduces its game, and plays an instrumented copy of our bot (the trace bot) against the same
puppets for per-turn decision lines.

Every script takes `--version` (default: the newest version [versions.py](versions.py) finds). A live version (v87 on)
has no commit of its own: `versions.py` registers every version the scheduler's
`~/tmp-offload/handoff/sched/gates.jsonl` lists, with its `src` the version's frozen build workspace (outside the
repo), and every `bots/baselines/v<N>` holding a live upload's masked source (`src/model/prio_stream.h`). A version that gates.jsonl records twice with
different workspaces is left out; the release re-runs then prove the attribution.

**Engine by date:** ladder games before ~05:25 UTC on 2026-11-09 reproduce only under cambc 5.0.0 and later ones only
under 5.0.1. The two stop out-of-fuel turns at different points, so a champion's turn after one differs in fuel, and so
can the draft's 10M first turn (research/notes/RUNNER.md). Run the harness with the `cambc` on `PATH` that matches.

## The chain

```
py tools/replay/harness/pipeline.py --version v112 --jobs 32 [--opps fish,mite] [--skip direct,...]
```

| step | script | output under `replays/<v>/` |
|---|---|---|
| manifest | `scrim_manifest.py`: the version's finished scrims against `--opps` from the scrim log | `ladder/`, `manifest.json` |
| setup | `setup_ws.py`: the workspace, its two patches and the release bot | `ws/`, `ladder-list.json` |
| decode | `decode_all.mjs`: each game's input streams | `inputs/ladder/` |
| batch | `batch.py`: puppets, release re-runs, validation | `runs/batch/` |
| tracebot | `live_trace_bot.py`: the source plus the combat lab's CS / CC / HG lines | `trace-bot/` |
| direct | `direct_batch.py`: the trace bot against each puppet, trusted rounds per game | `runs/direct/` |
| extract | `extract_all.py --kinds ladder`: the ladder replays' tables (outcomes) | `extract/ladder/` |

Every step skips finished work, so rerun the pipeline after new downloads. `batch.py` redoes a game when either bot's
wasm changes (`stamp.json`), and `direct_batch.py` when the trace bot's does. Every step takes `--keys K1,K2` to work
on some games only and `--force` to redo work; `batch.py --stages gen,build,release,validate,summary` runs part of it.

**Prerequisites:** Python 3, Node 22+ and `cambc` on `PATH`; the scrim log's replays and `.fuel` files
(`ladder_scrims.py` downloads them).

## Why release re-runs and direct traces

- **Release re-runs** are exact, with identical per-turn fuel, in all 2,690 games of v105, v106, v108, v109 and v111.
- **Debug builds do not reproduce the games under cambc 5.0.1.** Debug codegen and the debug refund no longer track
  release fuel closely enough: plain debug builds keep 43% of rounds trusted. (The older recorder and tracer, which
  virtualised fuel for cambc 3.0.5 submissions, kept 25% and were removed on 2026-11-14.)
- **What works:** direct re-runs of the release code against the puppet, with logging added by `live_trace_bot.py`
  (default `--release-guard 2`). A `RELEASE_CODE` marker in the bot makes the patched cmake drop `CAMBC_DEBUG`. Each
  log statement then runs inside `fuel_pause(); ...; fflush(stdout); fuel_adjust(2); fuel_resume();`.
  - `fuel_adjust(x)` refunds x, and 2 a block cancels the guard's own cost.
  - The flush must happen inside the window. Otherwise the buffered write is charged at turn end, about 110 fuel a
    turn.
  - With both, 85% of turns are fuel-identical to the ladder. 1,968 of 2,384 games are exact, and 81% of rounds are
    trusted.
  - `live_trace_bot.py` patches the source by exact text, so a version whose fight code differs stops with the
    unmatched line; port the lines to it then.
- **Trust.** `direct_batch.py` trusts each game through the round before its first input or round-hash difference
  from the ladder replay (`ladder_trusted_through` in `direct.json`). After it the game is a different one.

## What `setup_ws.py` does

It is idempotent. From nothing it:

1. runs `cambc init --yes`, then copies the manifest's maps from the repo's `maps/` (byte-identical to the pool;
   `ws/maps` names use `-` where the manifest uses `_`);
2. patches `cmake/CMakeLists.txt`: a bot directory with a `RELEASE_CODE` file is compiled without `CAMBC_DEBUG` even
   in a debug run;
3. patches `sdk/cpp/cambc.h`: `DebugGuard`'s refund becomes the macro `CAMBC_DEBUG_REFUND` (10 by default,
   `--refund 2` restores stock), plus a `cambc_debug_depth` counter that nothing reads now but keeps existing
   workspaces' wasm unchanged;
4. copies the version's source into `bots/<v>-release` and builds it `--release`;
5. writes `ladder-list.json` for `decode_all.mjs`.

## The puppet

`gen_puppet.mjs` writes a bot that replays one team's recorded inputs (`inputs.mjs` decodes them from a replay).
A ladder replay does not record which action a `Movement blocked` step attempted, so the puppet tries every feasible
action, ward first, since an allied ward is most often the hidden blocker. With that order all 390 release re-runs
of the first submission studied were exact. A single game by hand, from `replays/<v>/ws`:

```
node tools/replay/harness/gen_puppet.mjs replays/<v>/inputs/ladder/<key>.json.gz <1 if our_side is a, else 0> replays/<v>/ws/bots/p-<key>
cambc run bots/<v>-release bots/p-<key> --map <map> --release -o OUT
node ../../../tools/replay/harness/compare.mjs ../inputs/ladder/<key>.json.gz OUT/*.repl26a      # "exact": true
```

`compare.mjs --fuel LADDER.fuel --team a|b` also compares our per-turn fuel with the re-run bundle's.

## Engine facts the harness relies on

- `bc_round_number` clears the engine's last error, so a hook that queries the round between a failing call and
  `bc_get_last_error` changes the bot's path.
- An import whose price exceeds the fuel left still completes, leaving fuel at 0. The bot stops only at its next fuel
  check (a wasm function entry or loop header) and can make more imports, or yield normally, before it.
- `fuel_adjust(+N)` caps only the reading: `fuel_remaining()` never shows more than the budget, but the excess is
  real, spendable within the turn and lost at its end (`tools/probes/probe-fueladjust-b`). Below the cap a refund
  raises the reading by exactly N, paused or not.
- **`debug_block` is not free.** An empty block costs about 8 fuel beyond the SDK's refund, and a debug build's
  codegen differs, so a debug build is not fuel-exact (AGENTS.md).

## Windows

- **Interpreters:** all scripts run their Python helpers with `sys.executable` and look up `cambc` and `node` on
  `PATH`, so `py` and `cambc.exe` work unchanged.
- **Command-line length:** `extract_all.py` passes replays to extract.mjs 60 at a time to stay under the
  32k-character limit.
- **Path length:** cmake object paths embed the full source path. If a build fails on path length, enable long paths
  or use a short clone path.

## Toolchain behind a proxy

On its first build, cambc downloads wasi-sdk-33, cmake-3.31.8 and ninja-1.12.1 into its cache (`%LOCALAPPDATA%\cambc`
on Windows, `~/.cache/cambc` on Linux). Behind a TLS-intercepting proxy the download fails; fetch them into the cache
under the same names:

```
C=~/.cache/cambc; mkdir -p $C && cd $C
curl -fsSLO https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-33/wasi-sdk-33.0-x86_64-linux.tar.gz
tar xzf wasi-sdk-33.0-x86_64-linux.tar.gz && mv wasi-sdk-33.0-x86_64-linux wasi-sdk-33
curl -fsSLO https://github.com/Kitware/CMake/releases/download/v3.31.8/cmake-3.31.8-linux-x86_64.tar.gz
tar xzf cmake-3.31.8-linux-x86_64.tar.gz      # sha256 630615d8e98ac33eba7fbe472626dff5c899c85af3c024585ae109166a6909d0
curl -fsSLO https://github.com/ninja-build/ninja/releases/download/v1.12.1/ninja-linux.zip
mkdir -p ninja-1.12.1-linux-x86_64 && unzip -o ninja-linux.zip -d ninja-1.12.1-linux-x86_64   # sha256 6f98805688d19672bd699fbbfa2c2cf0fc054ac3df1f0e6a47664d963d530255
```

## Files

All paths are under `tools/replay/harness/` unless they start with `replays/`.

| Path | What |
|---|---|
| `versions.py`, `pipeline.py` | the version table; the whole chain in one command |
| `scrim_manifest.py` | a version's manifest from the scrim log |
| `setup_ws.py` | workspace setup |
| `decode_all.mjs`, `inputs.mjs` | decode ladder input streams |
| `gen_puppet.mjs`, `puppet/` | opponent puppet |
| `batch.py`, `validate_batch.mjs`, `compare.mjs` | release re-runs and validation |
| `live_trace_bot.py` (+ `.inc`), `direct_batch.py` | the trace bot; traced direct re-runs |
| `extract_all.py` | extract.mjs over a version's replays |
| `replays/<v>/ws/` | generated workspace: patched `cmake/` and `sdk/`, the maps, `bots/<v>-release`, puppets `bots/p-<key>` |
| `replays/<v>/ladder/`, `inputs/`, `runs/`, `extract/`, `trace-bot/` | generated |
