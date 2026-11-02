# fastrunner: a drop-in, fuel-exact runner for cambc 4.0.0

2026-11-01. Code: [tools/fastengine/runner/](../../tools/fastengine/runner/). It plays matches like `cambc run` /
`cambc run-batch` and writes the same replay bundles, byte for byte, with cambc's own engine. Two ways to run the
bots, both exact: on wasmtime 49.0.2 (default), or translated to C and compiled natively (`FASTRUNNER_MODE=native`).
Background: [DESIGN.md](DESIGN.md) (route B, §6).

## Summary

Whole machine, CPUs 1-11 (CPU 0 left free), demeter vs bots/variants/astraeus-d7d9dab, all of `tools/ab.py`'s default
suites (ladder, `maps/gen`, `maps/gen-s1`, both sides): 1164 games, run through ab.py as an A/B runs them, final build.

| runner | wall | games/h | vs stock |
|---|---|---|---|
| stock cambc (`run_batched.py`, a `run-batch` per match, 11 slots) | 255.4 s | 16,410 | 1.0x |
| fastrunner, wasmtime (exact, default) | 74.0 s | 56,630 | 3.45x |
| fastrunner, native (`FASTRUNNER_MODE=native`) | 54.1 s | 77,460 | 4.72x |

Round 1, ladder + gen only (652 games, quiet machine before a reboot): stock 15,430 games/h, stock + turbo 22,020
(1.43x), exact 48,600 (3.15x), native 70,060 (4.54x), native in one run-batch 86,900 (5.6x).

- **Exact.** On the final build, every member of all 1164 bundles (`replay.repl26a`, both `.fuel`, `.stdout`,
  `.debug`) equals stock's, in both modes; winners 1164/1164 (neither bot draws; a bot that does gets an empty
  `.debug`, see "Differences from stock"). Fuel probes (probe-fuel with quanta 37k, 100k and
  250k, probe-fuel-ops, -firstturn, -fueladjust-b, -memory, release build): identical in both modes. Probes whose
  draft bot yields without picking now match too: fastrunner makes stock's seeded picks for it (see "Differences
  from stock" for this and the other fixes after the verification).
- **Not 10x.** The machine is bound by its 6 physical cores (2 fast, 4 dense): one worker per core gives the same or
  better throughput than eleven (80.5k vs 74.2k games/h in a direct run; SMT adds at most 7% on the dense cores), and
  nothing else saturates. What is left per game is the bots' own code and cambc's engine (below).

## How to use

```
cd tools/fastengine/runner && ./setup_vendor.sh && cargo build --release      # once (~3 min)
tools/fastengine/runner/fastrunner run demeter astraeus --map 00ambush -o /tmp/out
tools/fastengine/runner/fastrunner run-batch MANIFEST --jobs 11                # cambc's manifest format
CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native py tools/ab.py ...
```

- `fastrunner` is a launcher script: it runs the installed `cambc` with `LD_PRELOAD=libfastrunner.so` and
  `FASTRUNNER_MAIN=1`. The preloaded library replaces cambc's `main` for `run`, `run-batch`, its own `__worker` and
  `__fastrunner`; every other command (`build`, `bundle`, ...) runs as stock cambc.
- `run_batched.py` uses `CAMBC_BIN` when set (unset = the `cambc` on PATH, unchanged). If `CAMBC_BIN __fastrunner`
  answers, the whole batch goes to one `run-batch --jobs THREADS --slot-dir <cpu_slots dir> --slots N`, which takes
  a CPU slot (tools/cpu_slots.py's flock) per game, so ab.py's concurrent suites still share the slots game by
  game. results.json and the replay files are as before.
- `FASTRUNNER_MODE=exact` (default: wasmtime) or `native` (needs clang; each bot is translated and compiled once,
  ~7 s on 11 cores, cached in `~/.cache/fastrunner/native/` by wasm hash and translator/flags). `nofuel` exists but
  changes games (winner agreed 150/240) and is no faster; don't use it.
- Options: `--jobs N` (worker processes, each playing many games), `--rounds`, `--log-limit`, `--release`,
  `--fuel-quantum Q` / `--fuel Q` (checked against stock at 37k and 250k), per-line `--statistics PATH`. Accepted and
  ignored: `--color`, `--timeout` (a game cannot hang: every turn is fuel-bounded).
- Round-2 switches (all exact, on by default): `FASTRUNNER_NATIVE_DF`, `FASTRUNNER_SHADOW` (0 = off),
  `FASTRUNNER_CHECK_SHADOW=1`, `fastrunner __fuzzdf N SEED` (distance-field fuzzer).
- Other environment: `FASTRUNNER_STATS=1` (timings, host-call and memory totals), `FASTRUNNER_TRACE_FUEL=FILE` (fuel
  counter at every host call; with `FASTRUNNER_TRACE_SITES=1` in native mode, the calling wasm function and offset),
  `FASTRUNNER_MEMO=0` / `FASTRUNNER_NATIVE=0` (read memo / native bitboard ops off), `FASTRUNNER_CC`,
  `FASTRUNNER_COPT`, `FASTRUNNER_CFLAGS`, `FASTRUNNER_UNITS`, `FASTRUNNER_KEEP_C=1` (keep the generated C).
- Linux x86-64 only, and only cambc 4.0.0 (build-id `207dc997...`; checked at start).

## How it works

- **Inside cambc.** The engine's thread-locals use the local-exec TLS model, so the cambc binary cannot be
  `dlopen`ed safely. cambc stays the executable and the runner is preloaded: its `__libc_start_main` hook calls the
  real one with our `main`. The engine's C API (`Game_*`, `Bitboard_*`, `DistanceField_*`, 181 functions) is called
  through addresses from cambc's symbol table. No game rule is reimplemented.
- **wasmtime 49.0.2**, vendored with a patch ([wasmtime-49.0.2-cambc.patch](../../tools/fastengine/runner/wasmtime-49.0.2-cambc.patch))
  reproducing cambc's modified `out_of_gas`, with cambc's engine configuration.
- **Workers**: `run-batch --jobs N` starts N worker processes and hands them games one at a time.

### cambc's fuel model (reverse-engineered, reproduced exactly)

- A store starts with 100G fuel and `fuel_async_yield_interval(Q)` (Q = 100,000 by default, `--fuel`): wasmtime
  injects fuel in chunks of Q and suspends the guest when one runs dry. cambc's `out_of_gas` also counts chunks:
  `chunks += 1 + overshoot / Q`, and carries `overshoot % Q` into the next chunk, charged on resume.
- A turn has `budget = scale * quanta_per_turn` chunks (scale 100 for a draft bot's first turn, 2 for a champion's
  first turn, else 1). At `chunks >= budget` the turn ends out of fuel and resumes there next turn.
- `yield`: fuel used = `min(chunks * Q + (Q - active), budget * Q)`, then a fresh chunk. Out of fuel: `budget * Q`.
  Trap or exit: the counter at that point.
- `fuel_remaining` = `min(active, Q) + Q * (budget - chunks - 1)`; `charge_fuel(n)` (host prices) rolls into whole
  chunks; debug builds' `fuel_pause/resume/adjust` give a debug block `Q * quanta * 1000` free fuel.
- A bot's linear memory is capped at 256 MiB (probe-memory; `cambc-rules.yaml` does not say so).

### Native mode (aot.rs, aot_rt.h, native.rs)

The bot's wasm (MVP, bulk memory, SIMD, exceptions with `try_table`/`throw_ref`) is translated to C, one C function
per wasm function, compiled by clang (`-O2 -ffp-contract=off -fno-math-errno -march=x86-64-v3`) in ~20 units in
parallel, linked into a shared library and `dlopen`ed. Fuel is metered as wasmtime-internal-cranelift 49.0.2
meters it, operator by operator:

- every function starts with 1 fuel consumed ("even empty functions should consume at least some fuel"), checked at
  entry; every reachable operator costs 1 except nop, drop, block, loop, unreachable, return, else, end and
  memory.grow (cambc's table);
- the cost is buffered and added to a local fuel variable at wasmtime's points (calls, return, throw, unreachable,
  loop, if, br, br_if, br_table, end, else); the variable is saved to the instance before calls, returns, throws and
  unreachable, and reloaded after calls and on entering a catch handler, so host calls, traps and handlers see
  wasmtime's counter; checks (out of gas at >= 0) at function entry, loop headers and after bulk operations whose
  size cost was deferred;
- memory.copy/fill charge 1 per byte, either up front (constant size up to 128 bytes, no check) or afterwards with a
  check. Which applies depends on whether Cranelift's SSA value for the size is a constant, which can see through
  `local.get`; the translator does not guess: a vendored wasmtime-internal-cranelift
  ([patch](../../tools/fastengine/runner/wasmtime-internal-cranelift-49.0.2-cambc.patch)) records Cranelift's decision
  per operator offset while the module is compiled once, and translation fails if any bulk operation has no record.

Runtime: each guest has an 8 GiB memory reservation with only the wasm-visible pages accessible (no bounds checks;
a fault inside it becomes a wasm trap via a SIGSEGV handler), and runs `_start` on its own 8 MiB fiber stack (a
16-line assembly context switch); `yield` and running out of fuel switch back to the runner. Exceptions are a
pending-exception word checked after calls to functions that can throw. Imports are direct calls through a table to
Rust trampolines generated from the same closures as the wasmtime imports (api_defs.rs, host_defs.rs, included
twice). The out-of-gas handler does the runner's chunk accounting in place and only switches stacks when the turn
ends. Modules using anything not translated (other proposals, multi-value functions, start sections) fail to build
with a message instead of running differently.

Exact except: a guest that recurses past cambc's 1 MiB wasm stack (~21,800 frames of a small function) traps at
a different depth, since native frames differ in size and native runs on 8 MiB; and a load clang proves dead traps
only when its value is dropped at once (`load; drop`), not when it flows into dead code. Neither occurs in our bots.
Float min/max follow Cranelift's x86 sequences bit for bit, NaN payloads included (probe `fprobe`).

### Other runner behaviour that matters for identical bundles

- **Turn loop** (`runner::Game::run`): `Game_Runner_Init`, then `GetState`/`EndTurn(kind)`/`Advance`; `EndTurn` kind
  0 after a yield, 1 out of fuel, 2 after an exit or trap; runner events 0xd/0xe/0xf; a champion that exits or traps
  is restarted with its fuel meter; a resign (`HostExit`) removes it.
- **Team stdout**: one NUL per replay-timeline step since the previous write; WASI `fd_write` writes only the first
  non-empty iovec; stderr is not bundled. cambc flushes stdout on a tokio worker thread, so a write never changes
  the bot's last engine error (fastrunner saves and restores it); the debug_block overrun notice goes to stderr.
- **Imports**: 150 SDK imports re-implemented from cambc's closures (argument checks, error codes, 40 host price
  formulas). Speed work, all exact: altar-lock scan over set bits only; reads memoised within a turn; native bitboard
  ops; a shadow-cast cache; guest memory through a cached pointer; last error written to the engine's TLS slot.
- **Statistics** (`.camstat`) via cambc's own `runner::summary::{collect, encode}`; **winner** from
  `Game_Statistics_GetSummary`.
- The bundle's zip container differs (deflate level 1); members are identical.

## Differences from stock

From the verification of 2026-11-01 (480 games of 12 bot pairings in both modes, 160 release-build games, the
options, and probe bots; the ones for the fixes below are in `tools/fastengine/runner/probes/`):

- **Debug drawings are not recorded**: `team-a.debug` / `team-b.debug` are always empty (`bundle.rs`). Games,
  fuel and stdout are unaffected; only the viewer's overlays are lost (river and hermes draw; astraeus and demeter
  only with `debug_draw` on). Accepted: A/Bs never read them.
- **`--statistics X.json --json`**: `--json` is ignored; the file is binary CAMSTAT as without it.
- **Console and options**: `fastrunner run` prints its status line, not stock's results table or "draft bot
  yielded" lines; `--timeout`, `--color`, `--view`, `--jsonl` are ignored (a turn is fuel-bounded, so a game cannot
  hang); `--fuel` / `--fuel-quantum` are accepted by both commands.
- **Native-mode limits** above (deep recursion, dead loads).
- **WASI edge cases no libc call makes**: a null pointer is a fault (stock accepts address 0); an `env` import the
  runner lacks traps when called (stock silently never runs such a bot).

Fixed after the verification (each re-checked against stock with games or probe bots, both modes):
- WASI: the clocks (`clock_time_get` 0, `clock_res_get` 1) and `random_get` (zeros, 1 fuel a byte) succeed as in
  cambc, so `std::chrono` and `std::random_device` work; `fd_read` (stdin empty), `fd_filestat_get`, `fd_tell`,
  `fd_prestat_get`, `fd_fdstat_set_flags`, `path_open` and `sched_yield` give stock's results (they trapped).
- Draft: a failed draft bot's picks come from cambc's own shuffle (`runner::Game::default_draft`: Fisher-Yates over
  0..11 with splitmix64, seeded with FNV-1a-64 of the map file, one state for both teams), not the first legal
  champion; 36 probe games over every failure mode and 16 fuchsia (debug: it aborts in the draft) vs demeter games
  match. A draft bot that resigns ends the game as in stock (fastrunner failed the match).
- Exact mode uses cambc's 1 MiB wasm stack (was wasmtime's 512 KiB), so deep recursion traps at stock's depth.
- The engine's last error: stdout writes no longer clear it; the debug_block overrun notice no longer goes into team
  stdout (probe `leprobe`).
- Native: float min/max NaN results; a huge constant memory offset traps when executed instead of failing the
  match; a dropped out-of-bounds load traps (probe `fprobe`).
- `run` and `run-batch` rebuild each bot first, as stock does (they played a stale `.wasm`); `run` finds bots and maps
  from the project root (`cambc.toml`) from any subdirectory, defaults to the first map in `maps/`, and names
  replays `A-vs-B-<epoch ms>` like stock; a one-worker batch takes a CPU slot per game.

## Where the time goes (native mode)

Before round 2 (one process, 4 games, 1209 samples): cambc engine under host calls 39.5% (distance fields 15.4%,
`Game_Action_Move` 7.1% of which its own shadow casts 3.4%, `Champion_Get` 3.2%), bots' native code 29.5%, import
layer 21%, rest ~10%. Round 2 (built by three helper agents, each verified exact on its own, then merged and
re-verified on the 1164 games) took 16% off a native game (1164 games: 64.1 s to 54.1 s):

- **Native distance fields** (src/df.rs): the engine's BFS reproduced bit for bit (levels of 8-neighbour dilation
  within open tiles; every dist u16, the visited board including padding, the expansion count, error 5 on overlapping
  buffers, TLS error untouched), with AVX-512 and AVX2 paths; 2.3x the engine on recorded real calls. Fuzzed with
  `fastrunner __fuzzdf N SEED` (2.4M random cases on all 326 maps' metadata and random sizes up to 528 wide, plus
  52,579 recorded real calls: 0 mismatches). Falls back to the engine for overlapping buffers, w > 512, h > 4096, or
  CPUs without AVX2. `FASTRUNNER_NATIVE_DF=0` turns it off.
- **Engine-level shadow-cast cache** (src/patch.rs): `Engine::Bitboard::ShadowCast` (pure; verified from the
  disassembly) is patched at its entry, after an FNV-1a check of its bytes, to look up a cache keyed on the full
  input contents; the engine's own vision casts hit 86.5%. The API-level cache it replaces never hit for these bots
  and cost ~6% of a game. `FASTRUNNER_SHADOW=0` off, `FASTRUNNER_CHECK_SHADOW=1` checks every hit against the
  original.
- **Import layer**: debug-only work out of the per-call path, guest memory straight from the instance, a
  multiply-free fuel charge when the multiplier is 1.0 and the amount below 2^53, inline memo tables, SSE2 bitboard
  kernels, no per-call allocation in `visible_altar_locks`: 12.9 to 9.0 ns a call in native mode (5.6M calls a game on
  00ambush). It also fixed a latent parity gap: the engine refuses partially overlapping boards in Union/Intersect/
  Xor/Not/IsEqual (error 5), which the native ops had computed; those now go to the engine.
- **ab.py**: its out-of-fuel count after the last suite (3.3 s for a 512-game suite) is split across processes;
  run-batch takes CPU slots on a jittered poll so concurrent suites share them evenly.

Estimated shares now: bots' code ~35%, engine ~34%, import layer ~15%, rest ~16%. To reach 10x from 4.7x needs
2.1x more per game: free bots alone would give ~1.5x, and the engine's remaining third is behind the bots' own calls
(their rate, not the runner, sets it). -O3 and a single compilation unit change the bots' code by 0-2%.

## Speed steps (one game, CPU 1)

| step | seconds |
|---|---|
| stock cambc | 1.74 |
| first identical fastrunner (wasmtime) | 0.64 |
| + altar locks, deflate 1, read memo, native bitboards, cached memory, shadow cache, pooling | 0.38-0.40 |
| native mode | 0.30-0.31 |

## Reproducing

```
python3 tools/fastengine/runner/scripts/compare.py demeter variants/astraeus-d7d9dab --out DIR \
    --suites ladder,gen --jobs 11 --cpus 1-11 --modes exact,native [--turbo /abs/turbo.so]
CAMBC_SLOTS=11 taskset -c 1-11 py tools/ab.py demeter variants/astraeus-d7d9dab --suites ladder,gen   # stock
python3 tools/fastengine/runner/scripts/cmp_bundles.py A.repl26a B.repl26a ...
FASTRUNNER_TRACE_FUEL=a.tr ... ; FASTRUNNER_MODE=native FASTRUNNER_TRACE_SITES=1 FASTRUNNER_TRACE_FUEL=b.tr ...
samply record --save-only -o p.json.gz -- env LD_PRELOAD=.../libfastrunner.so FASTRUNNER_MAIN=1 cambc run-batch M
python3 tools/fastengine/runner/scripts/prof.py p.json.gz
```
