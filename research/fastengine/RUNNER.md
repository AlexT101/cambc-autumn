# fastrunner: a drop-in, fuel-exact runner for cambc 5.0.1

2026-11-01. Code: [tools/fastengine/runner/](../../tools/fastengine/runner/). It plays matches like `cambc run` /
`cambc run-batch` and writes the same replay bundles, byte for byte, with cambc's own engine. Two ways to run the
bots, both exact: on wasmtime 49.0.2 (default), or translated to C and compiled natively (`FASTRUNNER_MODE=native`).
Background: [DESIGN.md](DESIGN.md) (route B, §6). Built for cambc 4.0.0, ported to 5.0.0 on 2026-11-05 and to 5.0.1 on
2026-11-09 (see "Port to cambc 5.0.0" and "Port to cambc 5.0.1"); the numbers before those sections are 4.0.0's.

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

- **On a 96-core AMD EPYC 9R45 (alext, 2026-11-03):** native is exact there too (512 `maps/gen` games, every bundle
  member equal to stock's) and 6.8x stock per game (118 against 805 game-seconds, median 6.9x), 5.5x wall on that
  batch. `FASTRUNNER_CFLAGS=-march=native` (AVX-512) gave 6.6x: no gain, so the build keeps `x86-64-v3`. ab.py runs
  of ~52k games (ladder, gen, gen-s1, 100 fresh suites) take ~3 minutes, ~290 games/s.

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
- Native builds are profile-guided (`FASTRUNNER_PGO`, default on; 0 = off): ~2 s more a new bot, ~30% faster bot
  code (round 3 below). Needs clang's `llvm-profdata` (`clang -print-prog-name=llvm-profdata`); without it, or if
  anything in the training fails, the bot is compiled without a profile (a warning on stderr) and that plain library
  is what the cache keeps under the profile-guided key: delete `~/.cache/fastrunner/native/<wasm hash>-*.so` to retry.
- Options: `--jobs N` (worker processes, each playing many games), `--rounds`, `--log-limit`, `--release`,
  `--fuel-quantum Q` / `--fuel Q` (checked against stock at 37k and 250k), per-line `--statistics PATH`. Accepted and
  ignored: `--color`, `--timeout` (a game cannot hang: every turn is fuel-bounded).
- Round-2 switches (all exact, on by default): `FASTRUNNER_NATIVE_DF`, `FASTRUNNER_SHADOW` (0 = off),
  `FASTRUNNER_CHECK_SHADOW=1`, `fastrunner __fuzzdf N SEED` (distance-field fuzzer).
- Other environment: `FASTRUNNER_STATS=1` (timings, host-call and memory totals), `FASTRUNNER_TRACE_FUEL=FILE` (fuel
  counter at every host call; with `FASTRUNNER_TRACE_SITES=1` in native mode, the calling wasm function and offset),
  `FASTRUNNER_MEMO=0` / `FASTRUNNER_NATIVE=0` (read memo / native bitboard ops off), `FASTRUNNER_CC`,
  `FASTRUNNER_COPT`, `FASTRUNNER_CFLAGS`, `FASTRUNNER_UNITS`, `FASTRUNNER_KEEP_C=1` (keep the generated C).
- Linux x86-64 only, and only cambc 5.0.1 (build-id `a4f85bb9...`; checked at start: under any other build,
  `fastrunner` and `CAMBC_BIN` run that cambc stock, so results stay right but are not faster).

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
  wasmtime's counter; checks (out of gas at >= 0) at function entry, loop headers, after bulk operations whose
  size cost was deferred, and (cambc 5.0.1's host trampolines) after every import call;
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
  `Game_Statistics_GetSummary`. The engine records statistics only for a job that asks for a `.camstat`: the
  summary is computed from game state, every word of it identical either way (round 3).
- The bundle's zip container differs (libdeflate level 1, ~25% smaller than stock's); members are identical.

## Differences from stock

From the verification of 2026-11-01 (480 games of 12 bot pairings in both modes, 160 release-build games, the
options, and probe bots; the ones for the fixes below are in `tools/fastengine/runner/probes/`):

- **Debug drawings are not recorded**: `team-a.debug` / `team-b.debug` are always empty (`bundle.rs`). Games,
  fuel and stdout are unaffected; only the viewer's overlays are lost (river and hermes draw; astraeus and demeter
  only with `debug_draw` on). Accepted: A/Bs never read them.
- **Out-of-fuel line** (2026-11-08): after each `[+] TEAM X WIN` line, `    Out of fuel: A n B n` gives each team's
  play turns (not draft turns) that ended out of fuel, which `run_batched.py` stores as `oof_turns` (needed for
  `--release` A/Bs, whose bots print no `OOF` lines). Bundles are unchanged (12 debug and 12 release games identical to
  the previous build's).
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

Tried without gain (2026-11-02; astraeus vs demeter, 38 games on CPU 1, runs alternated, noise ~2%):
- **C fast paths for hot imports** in the generated code (memo hits, Bitboard Test/Set, DistanceField Get,
  `fuel_*`, `my_team`; exact on 12 games): 2-4% more CPU inlined, 4% as direct calls to out-of-line helpers. A
  trampoline already serves a memo hit in ~30 instructions, so C saves only the indirect call and three pushes, and
  inlined copies grow the bots' text 14%.
- 8, 22, 48 or 96 compilation units, -O3, -march=native, -mtune=znver5, and fat LTO with one codegen unit for the
  runner: within noise. Units default to twice the CPUs the building process may use, so a cache entry built
  under `taskset -c 1` has 2 (~2% slower).
- Left, each under 2%: the bundle's deflate (1.5%), re-zeroing a pooled 4 MiB memory per spawn in `Guest::new`
  (1.1%), the shadow-cast cache's atomic busy flag and table misses (~2%).

## Round 3: profile-guided bots, fewer page faults, smaller bundles (2026-11-03)

Branch `tool-speed`. Every change exact: against the previous runner, every bundle member identical on 10,240
games of a 20-suite ab.py run (demeter vs baselines/v66, own drafts), 5,120 more, 1,196 games of ladder + gen + gen-s1
with per-suite wins, out-of-fuel counts and failures identical, 684 games of astraeus vs v67 (ladder + gen-s1,
100x100 maps), 40 games in exact (wasmtime) mode, and bench.py's wide set with test drafts (Cassi & Issac in 17 of
52 games) at 100M and at the real budget (JSONs identical).

| change | effect |
|---|---|
| profile-guided native builds (`FASTRUNNER_PGO`) | user cycles -15% a game (bots' code ~-30%) |
| `mallopt`: big allocations stay on the heap | page faults 226k -> 33k per 40 games, kernel cycles -60%, total ~-4% |
| statistics only for a `.camstat` | cycles -5% a game (A/Bs; bench.py still asks for them) |
| libdeflate level 1 for bundles | deflate 1.5x faster (~-0.9% a game), replays -24% on disk |
| slot files kept open between polls | a waiting run-batch's polling CPU about halves |
| oof.py: bytes.find instead of a regex over decoded text | ab.py's out-of-fuel count ~2x faster |

Whole runs, previous runner against this one, back to back: ab.py over ladder, gen and gen-s1 (1,196 games),
steady state: 290 -> 240 CPU-s (-17%), wall 3.6 -> 3.0 s. Ten fresh suites (5,120 games), ABBA: 1,208-1,226 ->
1,016-1,023 CPU-s (-16%), wall 14.7-19.8 -> 12.1-12.3 s. Twenty fresh suites (10,240 games, box at load 130-146):
2,447 -> 2,147 CPU-s (-12%). Games per CPU-second 4.2 -> 4.8-5.0.

- **PGO.** `native::build` compiles the translated C at -O0 with `-fprofile-instr-generate` (~12 CPU-s, 1.5 s),
  plays one self-play game of it on a built-in `maps/00ambush` in a child process (`fastrunner __pgotrain WASM`,
  loading that library through `FASTRUNNER_NATIVE_SO`), merges the profile with `llvm-profdata` and compiles the
  real library with `-fprofile-instr-use`. Clang's frontend profiles do not depend on the optimisation level, so the
  -O0 training gives the same gain as an -O2 one (5.37e10 against 5.22-5.43e10 cycles for 40 games; plain 6.19e10).
  One self-play game is as good as 16 games against another bot on other maps. The generated C keeps its semantics
  (fuel is explicit in it, `-ffp-contract=off`), so the instrumented and the optimised builds both play stock's
  games. Cache keys carry a `pgo1` marker: older runners never load these libraries, and tune.py's patching of
  `<hash>-*.so` covers them.
- **Page faults.** The engine's statistics vectors (`Engine::Game::CaptureStatistic`) grow past glibc's 32 MiB mmap
  ceiling, so every game mapped, faulted in and unmapped ~18 MB (76% of a worker's faults; with 94 workers the
  page allocator's lock showed too). `M_MMAP_MAX` 0 and a 1 GiB trim threshold, set in the runner's `main`, keep
  them on the heap; peak RSS unchanged (138 MB for 40 games).
- **Statistics.** `Game_Statistics_Enable` is called only for a job with `--statistics`. `RunnerEvent` then
  returns 0 without recording and the engine's last error at every turn start is "" as before (180k turns
  checked).
- **Slots.** A coordinator waiting on a full pool re-opened all 94 slot files every 3-8 ms (~4% of a core each;
  10 waiting for 20 s: 10.0-11.4 CPU-s, now 4.1-6.0). Fair share is unchanged (8 slots, 5 processes of one group
  against 1 of another: 4.10 / 3.84 slots, previously 4.13 / 3.82).

- **Build lock.** `native::build` holds `.<key>.lock` in the cache while it builds, so concurrent processes needing
  the same new bot build it once (4 cold processes: one build per bot). This also covers a runner rebuild under a
  running batch: its later workers load the new library, whose cache keys are new, and wait for one build per bot.
- **Switching over:** rebuild (`cargo build --release`; it fetches the `libdeflater` crate) preferably with no batch
  running. Each bot's first batch afterwards builds its profile-guided library under a new key; the plain libraries
  already in `~/.cache/fastrunner/native/` keep their keys and are used only with `FASTRUNNER_PGO=0`.

Where the time goes now (684 games, perf): engine 36%, import layer 24%, bots' code 33%, kernel 4%, libc 3%.

Measured and dropped (40 games, one process, user cycles alternated; noise ~3%):
- PGO for the runner itself (rustc, LLVM 23, trained on 16 games): ~1-2%, within noise; not worth a training step
  in every build.
- -O3 on top of PGO: no change. Transparent huge pages for guest memory (2 MiB-aligned reservations,
  `MADV_HUGEPAGE`) or for the engine's heap (`glibc.malloc.hugetlb=1`): ~0.5%, noise.
- Process start of a worker (~20 ms with both bots), `cambc build` of an unchanged bot (instant), per-game duration
  tails (the longest game < 1 s): nothing to gain. ab.py's out-of-fuel count after the suites is now ~0.3 s for
  1,196 games.

## Speed steps (one game, CPU 1)

| step | seconds |
|---|---|
| stock cambc | 1.74 |
| first identical fastrunner (wasmtime) | 0.64 |
| + altar locks, deflate 1, read memo, native bitboards, cached memory, shadow cache, pooling | 0.38-0.40 |
| native mode | 0.30-0.31 |
| + PGO, heap allocations, no statistics, libdeflate (round 3) | ~0.25 (from -16% CPU in batches; not timed alone) |

## Port to cambc 5.0.0 (2026-11-05)

cambc 5.0.0 (balance patch 4.0.0: champion stats, Skirmish, Greed) is 4.0.0's code relinked. Function by function
(objdump, addresses normalised), the C++ engine, the `runner` and `wasm_runtime` crates, wasmtime 49.0.2 and the
fuel code are identical except: the replay format byte (`Engine::Game::SaveReplay`) and the summary version
(`Game_Statistics_GetSummary`, `runner::summary::readable::format`) go from 2 to 3, and some engine thread-locals
moved (ShadowCast's `s_rows`; the last-error slot stays at fs:0 - 0x5f0). The balance changes are data. The runner
needed only addresses:

- `engine.rs`: the build-id; the shadow-cast patch's symbols are now kept from the symbol table.
- `patch.rs`: ShadowCast and its `.cold` part are found by symbol (5.0.0: 0x4197820, 0x41977f1), and checked against
  5.0.0's FNV-1a (0x795d7b527f5e8e25, 0xb032be59967740a8); the callers' return addresses are now offsets from
  `DrawVision` (+0xfa) and `Bitboard_ShadowCastWithScanCount` (+0x27e), the same in both builds.
- `stats.rs`: serde_json::Value's drop glue, as `runner::Game::statistics_bytes` calls it, at 0x4165900 (its
  `.llvm.N` suffix changes between builds, so it stays an address under the build-id check).
- `default_draft` (0x4169680) and the Rust crate hashes the runner looks up are unchanged.

Parity against stock 5.0.0 (`compare.py --camstat`, both sides, debug builds unless noted), every bundle member and
`.camstat` byte-identical, in both modes:

| bots | maps | games | identical (exact / native) |
|---|---|---|---|
| astraeus vs hyperion | `maps/` (128) + `maps/gen` (256) | 768 | 768 / 768 |
| astraeus_wip vs proteus | `maps/gen-s1` (256) | 512 | 512 / 512 |
| demeter vs hyperion, `--release` | 40 of `maps/` | 80 | 80 / 80 |

`FASTRUNNER_CHECK_SHADOW=1` on 8 games per mode: every hit (about 11k a batch) matched the original, the callers were
attributed (other 0) and the replays equalled stock's. CPU a game on a 96-core EPYC 9R45 (40 jobs, the 768 games): stock
0.87 s, exact 0.25 s (3.5x), native 0.17 s (5.1x, bots already compiled).

## Port to cambc 5.0.1 (2026-11-09)

cambc 5.0.1 (build-id `a4f85bb94ee2629daa3ce9997207bb581b554807`; no patch notes) is a rebuild with the same compilers
(rustc 1.100.0-nightly 5db7f4be8, GCC 14.2.1, LLD 23.1.0). Compared function by function with 5.0.0's wheel (objdump,
addresses, rodata references and jump tables normalised):

- **The C++ engine is unchanged**: every `Engine::*`, `Game_*`, `Bitboard_*` and `DistanceField_*` function is
  identical but ShadowCast, ReachableMask and GetDistanceFieldScratch, whose only change is their thread-local
  offsets; the design tables (`k_championDesigns`, `k_campDesigns`, `k_draftChampions`, `k_copyMasks`) are byte
  for byte the same. The last-error slot stays at fs:0 - 0x5f0. The replay format byte and summary version (3) are
  unchanged. No game rule changes.
- **Fuel: a host call now ends in a fuel check.** cambc's wasmtime gained a store flag, set by
  `wasm_runtime::Runtime::start` once fuel is configured, and all 295 host trampolines of a bot's store (SDK and
  WASI imports alike, `HostFunc::array_call_trampoline`) now run `libcalls::out_of_gas` right after a host function
  returns `Ok` if the fuel counter is >= 0. In 5.0.0 a host call whose price spent the chunk let the guest run on
  to its next check (function entry or loop header), host calls included. A host call reached after guest code
  spent the chunk does not run in that turn on either version (`tools/probes/probe-hostcall-fuel`, MODE 1). What
  moves is where an out-of-fuel turn stops, so which actions land in it, and the bot's next turn pays for the code
  5.0.0 ran in the (capped) out-of-fuel turn. In a turn of several chunks (the draft's 10M first turn) per-turn fuel
  can move too: see "Re-check on 5.0.1" below. With 5.0.0's runner forced onto 5.0.1 (`FASTRUNNER_ANY_CAMBC=1`), 80
  of the 768 games below differ in their replay and 458 in their `.fuel` (2 winners); at a 37k quantum, 22 of 24.
- The rest is the cambc CLI (account, submissions, map pool, Python packing, `tool_server`), `GuestCtx` growing
  (store fields move by 0x20), wasmtime-wasi and component glue re-inlined, `runner::summary::collect` and
  `default_draft` recompiled (same constants and shuffle), and `runner::api::primitives::gc_copy_in/out` (OCaml and
  Python GC arrays; not imported by C++ bots) inlining `ArrayRef::copy_*`.

The port:
- `engine.rs`: the build-id. `patch.rs`: ShadowCast (5.0.1: 0x41ebfa0, `.cold` 0x41ebf81, same sizes and prologue)
  checked against 5.0.1's FNV-1a (0x1002781ca8f6a7b3, 0xd01963b5f1b65add); the callers' offsets (+0xfa, +0x27e)
  hold. `stats.rs`: serde_json::Value's drop glue at 0x41a7fe0. Only 5.0.1 is supported.
- The fuel check, in both modes: the vendored wasmtime's `array_call_trampoline` runs `out_of_gas` after a host
  call that returns `Ok` with the counter >= 0, on stores with cambc's chunk accounting (`cambc_cell` set, i.e.
  exact mode) ([patch](../../tools/fastengine/runner/wasmtime-49.0.2-cambc.patch)); native code does `FUEL_CHECK()`
  after every import call (`aot.rs`, so the native cache key changes and every bot recompiles once).
- `compare.py --fuel Q` passes `--fuel-quantum Q` to every runner.

Parity against stock 5.0.1 (`compare.py --camstat`, both sides): every bundle member (`replay.repl26a`, both `.fuel`
and `.stdout`) and `.camstat` byte-identical, in both modes:

| bots | maps | games | identical (exact / native) |
|---|---|---|---|
| astraeus vs hyperion, debug | `maps/` (128) + `maps/gen` (256) | 768 | 768 / 768 |
| ocean vs astraeus, `--release` | `maps/gen-s1` (256) | 512 | 512 / 512 |
| ocean vs hyperion, `--release`, `--fuel 37000` (67k out-of-fuel turns) | 12 of `maps/` | 24 | 24 / 24 |
| astraeus vs hyperion, debug | 20 of `maps/` | 40 | 40 / 40 |

`FASTRUNNER_CHECK_SHADOW=1` on a game: all 37,160 hits matched the original, callers attributed (other 0). CPU a game
on the loaded 96-core box (load ~90, the 768 games, 24 jobs): stock 2.52 s, exact 0.31 s, native 0.21 s.


### Re-check on 5.0.1 (2026-11-09, evening)

The installed library (HEAD 79d9b0197) was the one tested; it needed no fix and was not replaced. `compare.py
--camstat`, both sides, stock = cambc 5.0.1 on PATH: every bundle member (`replay.repl26a`, both `.fuel`, `.stdout`)
and `.camstat` byte-identical, every winner equal. The runner's `Out of fuel: A n B n` line was checked against the
`Turn rollover` records in stock's replays (play turns, per team):

| bots | build | maps | games | identical (native / exact) | out-of-fuel turns, runner = stock replay |
|---|---|---|---|---|---|
| oc32s-bsk vs oc-base25 | release | `maps/` + `maps/gen` | 768 | 768 / 768 | 15,761 = 15,761 |
| oc-escv1-unl vs oc32s-bsk | release | `maps/` + `maps/gen` | 768 | 768 / - | 53,539 = 53,539 |
| oc-esc-478 vs v87-esc | release | `maps/gen-s1` | 512 | 512 / - | 9,550 = 9,550 |
| oc32s-bsk vs oc-base25 | debug | 128 of `maps/gen-s1` | 256 | 256 / - | 5,656 = 5,656 |
| oc-escv1-unl vs oc-esc-478, `--fuel 37000` | release | 24 of `maps/` | 48 | 48 / 48 | 98,942 = 98,942 |

Also checked: `run_batched.py` through the launcher (slot dir, `oof_turns` in results.json); `tools/tune` (SPSA): a
candidate patched by `patch.py` (s88's values) plays the same 80 bundles (40 ladder maps, both sides, against
oc-base25) as the runner's own compile of that wasm, native and exact. Two `cambc build --release` runs of one source
can differ in `try_table` label layout (seen in `plan_strikes` and `break_lock`), so compare games, not wasm bytes.

**Ladder re-runs: 5.0.0 against 5.0.1 per-turn fuel.** 44 ladder games (v95-v100), replayed under both stock versions
against opponent puppets, differed by ~2-300 fuel on some turns. Every difference before the two re-runs' inputs
diverge is one of: a turn right after an out-of-fuel turn of the same champion (210: the code between the host call
that spent the fuel and the next check now runs in that next turn), the draft's first turn (9 games, +21 to +83 on
5.0.1), or a later turn of a game that already differed in one of those (80: fuel-aware code reacts). None is
unexplained, and the fast runner gives 5.0.1's values, so it is the engine change, not the runner or the measuring.
The draft-turn case is the same change in a turn of several chunks (`tools/probes/probe-chunk-read`). The bot's own
code crosses a 100k chunk boundary and the next import is an unpriced read (`fuel_remaining()`). 5.0.0 left the
counter overrun: the read reported the chunk as spent to its boundary (9,000,000) and the turn was charged 14 less
(1,004,112). 5.0.1 runs `out_of_gas` after the read: 8,999,993 and 1,004,126, as the fast runner gives in both modes.
A one-chunk turn cannot show this, since any overrun ends it. A champion's first turn (2 chunks) can, but none of the
44 games did.

Tools: `run_batched.py` and `bench.py` now stop with an error when `CAMBC_BIN` (or bench's built launcher) is the fast
runner but `__fastrunner` does not answer, i.e. under a cambc build it was not ported to. Between 14:44 and 15:19 that
made every batch play stock: slower, and no out-of-fuel counts for release builds. `FASTRUNNER_ALLOW_STOCK=1` plays
stock anyway. ab.py, solo.py and dgate.py go through `run_batched.py`; `tools/tune` calls the launcher directly with
runner-only options (`--slot-dir`, patched bots with no source), so a stock fallback fails there rather than running.

## Reproducing

```
python3 tools/fastengine/runner/scripts/compare.py demeter variants/astraeus-d7d9dab --out DIR \
    --suites ladder,gen --jobs 11 --cpus 1-11 --modes exact,native [--camstat] [--turbo /abs/turbo.so]
CAMBC_SLOTS=11 taskset -c 1-11 py tools/ab.py demeter variants/astraeus-d7d9dab --suites ladder,gen   # stock
python3 tools/fastengine/runner/scripts/cmp_bundles.py A.repl26a B.repl26a ...
FASTRUNNER_TRACE_FUEL=a.tr ... ; FASTRUNNER_MODE=native FASTRUNNER_TRACE_SITES=1 FASTRUNNER_TRACE_FUEL=b.tr ...
samply record --save-only -o p.json.gz -- env LD_PRELOAD=.../libfastrunner.so FASTRUNNER_MAIN=1 cambc run-batch M
python3 tools/fastengine/runner/scripts/prof.py p.json.gz
```

## The wasm engine backend (`FASTRUNNER_ENGINE=wasm`, 2026-11-07)

A second engine for the combat lab: cambc's engine from the viewer's WASM build
([tools/replay/engine/v3_0_0.wasm](../../tools/replay/engine/v3_0_0.wasm), the same engine as cambc 5.0.0),
translated by wabt's `wasm2c` and compiled natively, in place of the native engine inside the cambc binary. Unlike
that engine it has a sandbox (`Game_Sandbox_Teleport`, `Damage`, `Buff`, `GiveGold`, `GiveGems`, `RespawnGroup`,
`CampAttack`, `CampCast`) and its whole state is its linear memory (~1.3-1.9 MiB) plus one global, so it can be
snapshotted and restored with a memcpy. Unset (or `native`), the runner is exactly as before.

- **Build.** `cargo build --release` builds both backends: [build.rs](../../tools/fastengine/runner/build.rs) runs
  `wasm2c` (wabt 1.0.36, `/usr/bin/wasm2c`; it also needs wabt's `wasm-rt.h`) into 8 parts and compiles them with
  clang (`-O2 -march=x86-64-v3 -ffp-contract=off`, ~13 s in parallel, only when the wasm or the glue changes). It
  needs simde headers: `setup_vendor.sh` takes them from libsimde-dev's .deb into `vendor/simde/include` when
  `/usr/include/simde` is missing. Without wasm2c, clang or simde the runner builds without the backend (a cargo
  warning) and `FASTRUNNER_ENGINE=wasm` fails with a message. Code: [src/wengine.rs](../../tools/fastengine/runner/src/wengine.rs)
  (shims, snapshot API), [wengine/glue.c](../../tools/fastengine/runner/wengine/glue.c) (instance, WASI stubs, the 7
  wasm-rt functions: guard-page memory without libwasm-rt-impl, whose `wasm_rt_init` would replace native mode's
  SIGSEGV handler), `engine.rs` (selection).
- **Select:** `FASTRUNNER_ENGINE=wasm` with `fastrunner run` / `run-batch` (workers inherit it), either
  `FASTRUNNER_MODE`.
- **What moves.** Only `Game_*` (118 shims, 2 of them stubs). `Bitboard_*`, `DistanceField_*` (and fastrunner's native distance
  fields, bitboard kernels and shadow-cast cache), `GetLastErrorMsg` and `Engine::Result` stay on the native engine:
  they hold no game state. Each `Game_*` symbol resolves to a shim with the native C signature that writes by-value
  structs (perspective, entity, position: pointers in the wasm API) to a 64 KiB scratch in engine memory, copies
  in/out buffers in before the call and back after it with the size the native call may touch (the import's checked
  size, `cap` x element size for lists, board bytes from the map's metadata), at the host pointer's alignment mod 16,
  null kept null. Larger buffers (a map file, a long shared-memory read) get an `Engine_Malloc` block for the call.
  `Game_FromMapFileBytes` gets its fourth argument (`Map::FromFileBytes`'s flag) as 0, as cambc's runner and the
  viewer pass it (the default backend passes whatever is in `rcx`; games have matched stock, so it is 0 or unused).
- **Last error.** Bots see the native slot (fs:0 - 0x5f0), which native calls and memo hits also write. The wasm
  engine's slot is a static at 106248 (checked at start), written by its `Engine::Result` and read only by
  `GetLastErrorMsg`; a shim sets it to a sentinel before the call and, if the call stored a message, points the
  native slot at it inside engine memory (whose mapping never moves).
- **Stubbed.** `Game_Statistics_Enable` / `RunnerEvent` / `Records` / the `.camstat` encoder (cambc's
  `runner::summary`, which reads the native engine) do not exist for it: with `--statistics` no `.camstat` is
  written (one warning); `RunnerEvent` does what the native one does with statistics off (last error "", returns
  18). `Game_Statistics_GetSummary` (the winner) is exported and used. The shadow-cast patch (patch.rs) only speeds
  the native engine's own vision; the wasm engine's vision runs uncached.
- **Snapshot API** (`crate::wengine`, cfg `wasm_engine`): `snapshot() -> Snapshot`, `snapshot_into(&mut Snapshot)`,
  `restore(&Snapshot)` (memory grown since is zeroed and shrunk back, so later growth sees zero pages as on the
  first run), `instance()` and `memory()` for raw calls, `raw::w2c_engine_<export>` for every export (generated
  from wasm2c's header: `Game_Sandbox_*`, `Game_Runner_Step`, the visualiser API, `Engine_Malloc`/`Free`), `args::`
  helpers that place an entity / position / perspective in scratch, and `shim::*` (the native-signature calls).
  Sandbox edits need an input boundary (error 18 "Sandbox edits require an input boundary" otherwise): a
  champion's turn, after the runner's `Advance` steps. One instance per process; game handles, the error slot's
  sentinel and the scratch are inside the snapshot. Host state that is not: the shims' board size of the last game
  (a function of the map) and the import layer's per-bot memo tables (`api::ApiState`, stamped by turn and action
  count), which a caller restoring mid-turn must treat as stale. `fastrunner __wsnap MAP [ROUNDS]` drafts a game,
  teleports a champion to the centre and an enemy beside it, and plays random rollouts from one snapshot: equal
  seeds give byte-identical engine memory, different seeds differ. Costs (00ambush, 1.8 MiB): a snapshot into an
  existing buffer 44 us, restore 0.1-0.3 ms, 50 rounds of 10 champions' random play 2.7 ms (00anvil, 1.3 MiB:
  28 us, 0.1 ms, 1.3 ms).
- **Identity** (native mode, debug builds, `fastrunner run-batch`, both sides; every bundle member compared with
  `cmp_bundles.py`): 1024/1024 games identical to the default backend: `variants/oc-lab-3642f1d` vs
  `variants/oc-base17` on the 128 ladder maps (256) and on 128 `maps/gen-s1` maps (256), and vs `astraeus` on 128
  `maps/gen` maps (256) and the ladder (256). Exact (wasmtime) mode: 64/64 (vs astraeus, 32 ladder maps). The
  default backend of this build against the previous `libfastrunner.so`: 256/256 (the oc-base17 ladder batch).
- **Speed** (the same 256-game batches, 16 workers, CPU per game, shared 96-core box): default 0.211 / 0.219 /
  0.237 / 0.197 s, wasm 0.255 / 0.266 / 0.289 / 0.252 s: the wasm backend costs ~23% more a game (~0.81x the
  games/h), the engine's share of a game going from ~1/3 to ~45%.

## The scenario layer (`fastrunner scenario`, 2026-11-07)

The combat lab's runner ([PLAN.md](../combat-lab/PLAN.md)), on the wasm backend; code in
[src/scenario.rs](../../tools/fastengine/runner/src/scenario.rs).

```
FASTRUNNER_LIB=.../target-wasm/release/libfastrunner.so FASTRUNNER_ENGINE=wasm FASTRUNNER_MODE=native \
  tools/fastengine/runner/fastrunner scenario SPECS.jsonl --bot-a BOT --bot-b BOT --rollouts N --rounds H \
  --out OUT.jsonl [--jobs J --slot-dir DIR --slots K] [--skip S --limit M] [--marks 10,30] [--hash] [--stdout DIR]
  [--turns] [--first-fuel SCALE] [--replay-all]
```

- **Output.** `OUT.jsonl`, a line per rollout: `id`, `rollout`, `rounds` played, `stop` (`rounds`, `apart`: no
  fighter within 8 tiles (Chebyshev) of an enemy fighter at 3 round starts in a row, `team_dead`, `resign`,
  `game_over`), `end_round`, `champion_turns`, and per fighter `alive`, `deaths`, `kills`, `hp`, `max_hp`, `gems`,
  `gold`, `x`, `y`, `dealt` / `taken` (champion damage, hp + shield lost by an enemy fighter during this fighter's
  turn), `taken_other` (lost in runner steps or in its own turn: camps, Ren's reflection, delayed effects), `fuel`,
  `turns`, `out_of_fuel`, `errors`. `--marks` adds `at.{10,30}` (per team deaths, kills, damage, and each
  fighter's hp at that round start), `--hash` the engine memory's FNV, `flags` any `PLAN-CHECK` / `DRAFT-UNFINISHED`
  line or resignation. A scenario that fails gives one `{"id", "error"}` line. `OUT.setup.jsonl`, a line per
  scenario: timings (CPU and wall), whether each team's draft was cached, the cooldown base, round - 1's turn
  order, and `inexact` (every field that did not land, checked through the API at the last turn of round - 1) and
  `after_round_start` (the same check at the snapshot, after the round's camp phase: camp hits there are real).
  Kills count each body: Cassi and Issac's linked death is two.
- **Workers.** `--jobs J` runs `__scenario_worker` processes fed one scenario at a time (setup and all its
  rollouts in one process), each holding a CPU slot of `tools/cpu_slots.py`'s pool while it plays (the
  coordinator never blocks on a slot with results pending).
- **Setup** (per scenario, from a clean engine snapshot). Draft: `wengine::DRAFT_PICKS` makes `Game_Action_Draft`
  pick the spec's champions whatever the caller asks, so each team's own draft bot plans for the picks it is told it
  made; its 1024-byte draft memory (readable only at the team's champion turns) is cached per (bot wasm, map, team,
  both teams' picks) in `FASTRUNNER_DRAFT_CACHE` (default `~/.cache/fastrunner/draftmem/`) once the first
  rollout's fighters took it without `PLAN-CHECK` / `DRAFT-UNFINISHED` (a cached one they refuse is deleted); later
  scenarios write it at the team's first draft turn and pick directly. Round 1: each champion gets the gold for its
  items, consumables and (fighters) spare gold, and buys them on its spawn (an emblem as 5 shards, Greed 25; gold
  before the purchases so a Treasure emblem's +10% does not apply). Idle rounds (no bots) follow. In round
  `round - EARLY_CAMP` (6) the zone's dead camps die and asleep camps take their lost health, so they are asleep
  again by `round` (damage and kills wake the whole group). Round `round - 1` is played twice from a snapshot of its
  start: once thrown away, to learn its turn order and calibrate the cooldown words (the first champion with a free
  slot casts it on itself, the ground, an ally or a tile within 2; the word that became the API's cooldown, minus
  72 c + 8 s, is confirmed by writing another champion's word and reading it back), then for real: priorities
  (`prio`, applied from the next round), and each fighter's edits at its own turn (teleport, health by
  null-source `Sandbox_Damage` aimed by the last read-back ratio, shield and stun buffs and cooldowns one higher
  for its own turn end, gems, gold); a fighting Tavi buys at that turn instead, on its spawn, before leaving it. At
  the round's last turn: teleports a fighter not yet moved had blocked, non-fighters moved off a fighter's tile (they
  idle on their spawn), and the zone's awake camps (health, or 0.001 damage to wake a full one). Then that turn ends,
  the runner's steps run, and the snapshot is taken at round `round`'s first champion turn.
- **Rollouts.** Restore, `wengine::reset_host()` (the shims' board-size cache, the native last-error slot) and
  `api::reset_game_caches()`, fresh bot instances for the fighters only (first turn at 2x fuel, 100x with `--lab`),
  non-fighters' turns ended unplayed.
- **Not set exactly** (400 bank frames, `replays/combatlab/bank0`): a Vesper's gold can land 1 over (its +33% on
  given gold, in steps of 1.33; 24/400 scenarios); a camp asleep in the spec whose group-mate is awake, or any
  asleep camp with lost health when `round` < 7, reads awake (6/400). Never set: tributed totals, channels,
  disabled wards, altar locks, groups' capture progress and timers, enhanced attack (not in the spec), a dead fighter's
  respawn timer (killed in round - 1, so full), and anything the fighters' bots remembered (each starts fresh mid
  game, with empty team shared memory). Everything else (positions, health, max health, items, consumables,
  gems, cooldowns, stuns, shields with 0 turns left, priorities, camp health and state) landed in every scenario.
- **Determinism.** Rollouts of a scenario are identical (memory hash included): 400/400 bank, 128/128 dev, 4/4
  hand-made scenarios. A cold and a warm draft cache give the same rollouts (40/40; the memory hash differs, the
  draft bots' run leaving another heap layout).
- **Sanity** (ocean `variants/oc-lab-3642f1d` both sides, H = 30, rollout 0 against the frame's `observed`): no
  resignations, crashes or plan refusals; 14 of 1657 fighters never moved nor hit; 1.1% of fighter turns out of
  fuel (89k fuel a turn: fights are expensive). bank0, 400: a death within 10 rounds in 57 rollouts against 71
  real games (agreeing in 341/397), fighter damage 658 vs 946 (corr 0.49), damage lead corr 0.55; within 30 rounds
  1239 vs 1499 (0.54). Without late joiners or a partner outside the zone (62 dev frames): 10 rounds 1078 vs 1265
  (0.67), 30 rounds 2369 vs 2467 (0.71). Rollouts fight less than the real games: fresh bots, teammates idle at
  spawn, and other ocean variants in the source games.
- **Fuel of fresh fighters.** `--turns` adds each fighter's `turn_log`, `[round, fuel, out of fuel, acted]` a
  turn (acted: the timeline advanced); `--first-fuel SCALE` sets the first turn's budget (default 2, the engine's
  rule for a new champion). bank400 at 2: 4.8% of first turns out of fuel, 3.9% of second turns, 3.6 / 2.1 / 1.4%
  for the next three, 0.8% later; fighters spend ~86k a turn for the whole rollout. The same fights in real games
  (oc-lab vs oc-base17, 64 games, 865 frames from `frames.py`, turns located in the bundles' `.fuel`): 0.4% out of
  fuel in each of the fight's first 10 rounds and ~60k a turn (66k on the frame's round). At 10 (or 100: the same
  rollouts) no first turn runs out (up to 523k used), but 4.9% of second turns do, later turns are unchanged
  (84.6k mean either way), and the bank400 comparison moves within noise (10 rounds: damage corr 0.49 -> 0.54,
  death agreement 341 -> 336 of 397, lead corr 0.55 -> 0.49; 30 rounds: 0.54 -> 0.59, 262 -> 256 of 385). The gap
  is ocean's cold caches, not the first turn: its turn-end queue fills map-wide tables with spare fuel bounded by
  the real budget (`main.cc` TurnEndQueue), which a real game finished long before the fight, and its readers build
  missing tables inside the decision.
- **Throughput** (bank0, 400 scenarios x 4 rollouts, H = 30, 16 workers; CPU time, shared box): 179 rollouts/s and
  15.9k champion turns/s a core (63 us a turn, 20 rounds and 89 fighter turns a rollout); setup 6.8 ms CPU median
  (p90 11.4; idle rounds 4.1 ms, a draft bot pair 1.6 ms, calibration 0.3 ms), so 136 rollouts/s a core at 4
  rollouts a scenario. Snapshot ~1.9 MiB. The whole batch took 1.3 s on 16 workers.

### Lab bots (`--lab`)

`py tools/combatlab/labify.py SRC DST` copies an ocean or astraeus directory with `./copybot` and patches it (each anchor must match exactly once, or it stops): `tools/combatlab/lab.h`'s 512-byte
`LabBlock` global behind the magic `CAMBC-LAB-BLK-1`, which the runner finds in the bot's linear memory and reads
and writes between turns at no fuel to the bot. With flags 0 and no inputs the copy plays as the original. Lab ocean
is `bots/variants/lab-v83` (from `bots/baselines/v83`), lab astraeus `bots/variants/lab-astraeus-8c0343f`.

```
fastrunner scenario SPECS --bot-a variants/lab-v83 --bot-b variants/lab-v83 ... --lab [--decisions]
  [--alt K [--alt-fighter ID|all] [--no-fork] | --flip SPANS] [--force-home ID:ROUND:V[:N]] [--force-chase ID:ROUND:V[:N]] [--warm-pre F] [--warm-radius R]
```

- **Warm start** (flag bit 0, on with `--lab`; first turn at 100x). In a fresh instance's first turn, after the world
  update and before comms receive / decide, the turn-end queue (`main.cc` TurnEndQueue) drains unbounded, its last
  step around the fighter at `--warm-radius` (12) instead of vision/20, so the map-wide tables a real game filled
  long before the fight exist. Then `aph::fuel()` reads the host's fuel less an offset, so the decision sees a
  normal turn: 100k less `--warm-pre` (7300, the lab's mean later pre-decision fuel; a fresh world update takes
  ~50k), with the queue's floor not raised by the excess; the offset is cleared once the decision ends, so that
  turn's end also runs on the large budget. The world reads as past its first round. Cost: median 2.14M fuel a
  fighter (mean 2.18M, max 3.8M; 1.18M at radius 0, 4.4M at 20).
- **Fuel** (fighter turns by index, oc-lab both sides; real games: `frames.py` frames of 64 oc-lab vs oc-base17
  games, turns located in the bundles' `.fuel`):

  | | turn 0 | 1 | 2 | 3 | 4 | 5+ | 1+ |
  |---|---|---|---|---|---|---|---|
  | real games (865 frames) | 66.1k | 64.1k | 60.6k | 60.3k | 59.7k | ~59k | 0.42% out of fuel flat |
  | lab, 893 real frames | (warm) | 63.9k, 1.97% | 59.6k, 1.39% | 59.4k, 1.03% | 59.5k, 1.27% | 66.9k, 0.36% | 65.8k, 0.54% |
  | lab, bank400 | (warm) | 64.1k, 2.36% | 59.5k, 1.71% | 59.5k, 1.29% | 59.2k, 0.81% | 65.8k, 0.35% | 64.9k, 0.58% |
  | no lab (2x), bank400 | 188k, 4.77% | 87.7k, 3.93% | 87.5k, 3.59% | 86.9k, 2.09% | 86.1k, 1.40% | 84.0k, 0.49% | 84.6k, 0.93% |

  Turn 0 never runs out (its figure, as read, includes the unbounded turn end). Turns 1-4 still run out 1-2%
  against 0.4%: cold state the queue does not hold. Clearing the offset after the decision moved turn 1 from 2.16%
  to 1.97% (66.1k to 63.9k).
- **Agreement** (bank400, rollout 0, H = 30, against the frames' `observed`; no lab at 2x -> lab):
  10 rounds: a death agrees 296 -> 286 of 397, deaths per team 277 -> 269, fighter damage corr 0.48 -> 0.51
  (mean 1287 -> 1419, real 946), lead corr 0.47 -> 0.54, hp error median 204 -> 236. 30 rounds: 262 -> 265 of
  385, 232 -> 229, damage corr 0.54 -> 0.66 (1239 -> 1376, real 1499), lead 0.57 -> 0.58, hp error 245 -> 281.
  Out-of-fuel turns 393 -> 202. Fighters no longer starved fight harder: correlations up, the first 10 rounds
  overshoot more.
- **Throughput** (bank400 x 4 rollouts, H = 30, 16 workers): 10.9 s CPU without the lab, 12.5 s with it (+15%).
- **Outputs**, each turn (`--decisions` adds each fighter's, turn by turn, to its rollout line): the decide branch
  (`decision`), `want_home`'s verdict (and its own, before a forced one), `stand_lost_at`'s prediction (verdict,
  reason: 1 nobody to fight, 2 a paying hold, 3 no roster, 4 traded; with the trade's falls and turns to kill), the
  chase target, and up to 4 `plan_strikes` calls (site S strike search, K keep_bid, P strike_after): whether it
  searched (`strike_free`'s shortcut otherwise), tiles, exactly priced tiles and candidates, the cap, and the chosen
  candidate (end tile, frontier entry, removed enemies, cast kept, ops, and raw, price, danger, shield, camp, gain,
  total).
- **Inputs:** a ban list (16) for one `plan_strikes` call (champion, round, call index), and forced `want_home` /
  chase verdicts at a champion turn (chase 0: no target; 1: prey, or the nearest visible enemy; applied only where
  ocean reaches `chase()`). Checked: `--force-home 1:62:0` turned a retreat into a fight (own verdict still 1);
  `--force-chase 7:61:0` stopped a chase. With `:N` the verdict holds N rounds: the bot obeys a force only in its own
  round, so the runner moves it to the current round before each of the fighter's turns in the span (no bot fuel).
  A chase forced on with no prey and no visible enemy has no target and stays 0 (in 300 lab-v83 frames, 28% of
  0 -> 1 flips at their first round; a rollout's decisions show whether it applied).
- **Hit log** (`--hitlog`): each rollout line gains each fighter turn's record (round, actor, its tile before and
  after, every fighter's loss in that turn, and the actor's feature block when a `tools/combatlab/labify_reply.py`
  copy filled one that round, base64), the teams' tributed gems at the start and end, and gems and tributed at each
  mark. Read runner-side, at no bot fuel; the reply model's labels (`research/reply-model/`). Off, output is
  byte-identical to the previous build (300 frames, alt mode vs lab-astraeus).
- **Flips** (`--flip SPANS`, e.g. `1,5,30`; not with `--alt`): rollout 0 plays as without it and its line's `flip.first`
  gives each fighter's (or `--alt-fighter`'s) first `want_home` and first chase verdict (round, verdict); then one
  rollout per verdict and span forces the opposite verdict from that round, held that many rounds (`flip`: fighter,
  what, round, from, to, span). Without `--flip` the build's alt output is byte-identical to the previous one's (300
  frames, vs lab-astraeus).
- **Alternatives** (`--alt K`): rollout 0 plays as without `--alt`; then, per fighter (or `--alt-fighter`), rollout
  k bans the candidates rollouts 0..k-1 chose at that fighter's first strike-search decision, up to K, stopping when
  the search finds no other. 100 bank frames, K = 8: rollout 0 equals the plain `--lab` run 100/100 (memory hash);
  193 fighters made a first decision, with {1: 55, 2: 16, 3: 20, 4: 23, 5: 5, 6: 7, 7: 8, 8: 59} distinct
  candidates (mean 4.3, median 4, no repeats; 134 searches ran out before K).
- **Identity:** at a 100M fuel quantum, with the warm start off, lab-v83 vs lab-astraeus-8c0343f and the unpatched
  copies (24 maps, both sides): 48/48 replays and debug identical; stdout differs only in when ocean's own `WARM n
  centres` lines print, `.fuel` by the hooks (median +217 a turn). At the real 100k, 6/48 replays match: the hooks'
  fuel moves fuel-gated decisions, as it would for any instrumented copy.
- **Wards.** `frames.py` specs carry `wards` (owner, team, position, disabled, the owner's recharge from
  `rounds.json.gz`'s `ward`). In setup each enabled ward is placed by its owner at its input boundary (teleported
  within 2, `Game_Action_PlaceWard`, teleported back) in the round that leaves the spec's recharge (round - 1 -
  (10 - k) + 1, or 12 rounds early with a charge left), then checked through the API. 893 real frames: 9333 wards
  placed, every position exact, every recharge equivalent (20 champions acting first in the round read 1/0 against
  the spec's 0/0: the charge returns at their turn start). bank400 regenerated with wards: 4297 placed, 1 with no
  free tile within 2. Wards shift agreement within noise (lab, 10 rounds: death 286 -> 293, damage corr 0.51 ->
  0.48; 30 rounds: 265 -> 260, 0.66 -> 0.59).

### Lab speed (2026-11-07)

Four changes cut the lab's CPU time without changing any output. Rollout lines, memory hashes, turn logs, marks
and decisions are byte-identical to the build before them, and setup lines match in every field but the timings.
The old build is in `target-wasm/`, the new one in `target-speed/`. Measured on bank400w (400 scenarios), K = 8, H = 30, 16 workers, with CPU slots on the shared box (load ~1400). CPU is user + sys
of the whole command (coordinator, workers, setup), interleaved, mean of 3:

| mode | rollouts | before | after | CPU ms a rollout | rollouts / CPU-s |
|---|---|---|---|---|---|
| alt (`--alt 8 --alt-fighter all --rollouts 1`), lab-v83 both | 3930 | 41.9 s | 28.7 s | 10.7 -> 7.3 | 94 -> 137 |
| alt, lab-v83 vs lab-astraeus-8c0343f | 3946 | 44.7 s | 31.5 s | 11.3 -> 8.0 | 88 -> 125 |
| plain (`--rollouts 4`, no `--alt`) | 1600 | 15.0 s | 6.2 s | 9.3 -> 3.9 | 108 -> 259 |
| alt, hold1k (1000 other bank0 frames) | 9695 | 100.2 s | 72.0 s | 10.3 -> 7.4 | 97 -> 135 |

Each change's share, measured by turning the later ones off (`--no-fork`, `FASTRUNNER_TOUCHED=0`, `--replay-all`),
interleaved, mean of 3:

| step | alt | plain |
|---|---|---|
| before | 41.8 s | 14.9 s |
| + decisions written raw | 38.1 s (-8.7%) | 14.0 s (-6%) |
| + touched-page resets | 35.8 s (-6.2%) | 13.0 s (-7%) |
| + fork (alt) / repeat rollout 0 (plain) | 28.7 s (-20%) | 6.2 s (-53%) |

- **Fork** (alt mode; `--no-fork` turns it off). A fighter's alternatives k >= 2 differ from alternative 1 only in
  their ban list. Every one of them has `n_bans > 0` and the same `ban_round` and `ban_call`, so before the decision
  each `lab_bans_on` test fails at the same step with the same fuel. They are therefore identical up to the boundary
  before the fighter's turn in the decision's round. Alternative 1 records the full state at that boundary, and each later alternative
  restores it, zeroes and rewrites the fighter's ban list, and plays on from there. The recorded state is:
  - the engine memory and g0;
  - the wasm backend's host state: `CUR`, whose miss writes the map's metadata into the engine's scratch, and the
    native last-error slot. Without them, 83 of 3930 lines' memory hashes differed;
  - each bot's instance words, its touched memory pages, the used part of its fiber stack, the fiber registers,
    `BotCtx` totals and `ApiState`;
  - its meter;
  - the team logs, truncated back to their length at the boundary;
  - the loop's own tallies.

  The bots must stay the same objects, because their native stacks hold absolute pointers. Rollout 0 cannot seed
  alternative 1: with no bans its `lab_bans_on` fails one step earlier, 5 fuel less on every `plan_strikes` call.
  68% of alt rollouts resume from a fork; each skips the spawn, the warm turns and the prefix.
- **Touched pages** (`FASTRUNNER_TOUCHED=0` turns it off). PAGEMAP_SCAN (Linux 6.7+) lists the bot-memory pages
  that may be non-zero: present pages other than the zero page, or swapped ones (the box swaps). A pooled memory's
  reset zeroes only those, and a bot snapshot saves only those, ~350 of ~1070 pages.
- **Plain mode** repeats rollout 0's line for rollouts 1..N-1, with only `rollout` changed. A scenario's rollouts
  have the same inputs and are deterministic (memory hash included). `--replay-all` plays them all.
- **Decisions written raw.** Each turn keeps the 512-byte control block instead of building a `serde_json::Value`.
  The line is written with a placeholder per fighter, which is replaced by the decisions written in serde_json's own
  format (BTreeMap key order, each leaf by serde_json).

Phases now, as CPU ms per alt rollout (b100, `FR_PHASES=1`):

| phase | ms |
|---|---|
| setup | 0.71 |
| restore | 0.51 (engine 0.10, bots 0.41 per forked rollout) |
| fork capture | 0.18 |
| spawn | 0.14 |
| warm turns | 0.78 |
| other turns | 3.00 |
| runner steps and reads | 0.56 |
| decisions and output | 0.11 |

perf by component, before -> after (share of samples):

| component | before | after |
|---|---|---|
| bot code | 24.6% | 20.8% |
| engine wasm2c | 22.8% | 28.3% |
| memcpy/memset | 12.7% | 17.2% |
| API trampolines and shims | 15.6% | 14.4% |
| JSON | 6.0% | 0.8% |
| malloc/free | 4.8% | 1.1% |

memcpy/memset is ~11 MB a rollout, all of it snapshots: about 4 MB of bot restores, 2.4 MB of fork captures, 3 MB of engine restores and
snapshots, and 1.7 MB of zeroing fresh bots.

Tried, with no gain: userfaultfd async write-protection, to rewrite only the pages written since a snapshot. A bot
writes ~100 of its ~350 snapshot pages and the engine ~25 of its ~500, but a fault costs about as much as copying
the page; re-protecting a bot memory took ~40 us and registering an 8 GiB reservation ~10 ms. Engine PGO, trained
on 200 other frames, gave -0.8% (noise). Bots at -O3 gave +1%.

Left, with estimates:
- Setup's idle rounds: ~6 ms a scenario, 11% of alt and ~50% of plain. This is the engine's runner step (`f694`),
  and the buys, wards and camp edits are per spec, so prefixes are rarely shareable.
- Alternative 1 from rollout 0: up to ~10% of alt. It needs `lab_bans_on` to cost the same fuel with no bans, which
  changes outputs. It also needs a capture at each of the fighter's boundaries until its first `plan_strikes` call,
  at ~11 MB a capture.
- The API and shim layer (~14%): a few % at most.

`FR_PHASES=1` prints each worker's CPU by phase to stderr.

## Forks of real games (`fastrunner forkgame`, 2026-11-08)

`forkgame` plays whole local games on the wasm engine and, at chosen rounds, forks the full state and plays
alternatives from it. The state includes every bot's memory, the shared and capture state, and the channels.
Source: `src/forkgame.rs`. Lab plan: [PLAN2.md](../combat-lab/PLAN2.md) Phase 1. Usage and results:
[lab2-notes.md](../combat-lab/lab2-notes.md).

```
FASTRUNNER_LIB=$PWD/tools/fastengine/runner/target-lab2/release/libfastrunner.so FASTRUNNER_ENGINE=wasm FASTRUNNER_MODE=native \
  tools/fastengine/runner/fastrunner forkgame --bot-a variants/lab-cl2 --bot-b variants/lab-cl2 \
  --maps maps/00ambush.map26a[,...] | --games GAMES.jsonl  [--both-sides] --out OUT.jsonl --jobs 16 \
  [--slot-dir .git/cambc-slots --slots 86] [--trigger near:6,branch:RC] [--decider a|b|both] [--gap 20] [--max-forks 8] \
  [--min-round 2] [--seed S] [--marks 10,30,60] [--arms none,sweep,end,home:V[:N],chase:V[:N]] [--holds 1,3] \
  [--ground all] [--work FPGBTW --work-radius 8] [--lab-flags 2] [--full] [--hash] [--decisions] [--digests] \
  [--save-replays DIR] [--debug]
```

- **Builds.** It needs the wasm engine (`cfg(wasm_engine)`), so it is built into its own target directory with
  `CARGO_TARGET_DIR=target-lab2 cargo build --release`. Bots are release builds unless `--debug` is passed. Games
  in `GAMES.jsonl` are `{"id", "map", "a", "b"}`; `--maps` with `--both-sides` makes both orders.
- **Pass 1** plays the game whole and records, each round, a digest of the champions' state, their alive mask and
  each decision's branch. The digest covers every champion's `Champion_Get` record, alive, gems and cooldowns, plus
  both teams' tributed gems and the timeline position. Triggers on the decider team's champions:
  - `near:D`: an enemy comes within D, at onset;
  - `close:D`: every turn with an enemy within D;
  - `branch:CHARS`: the decision branch is one of CHARS (the lab block's branch chars; `RC` is retreat or chase);
  - `death:N` / `kill:N`: N rounds before one of ours dies, or an enemy dies;
  - `every:K`: every K rounds.

  Candidates whose decider is alive in rounds `--min-round`..end are merged per (round, champion) and kept at least
  `--gap` rounds apart per champion. If more than `--max-forks` remain, a seeded sample is taken.
- **Pass 2** replays the game from scratch and checks every main-line round's digest against pass 1. At a fork's
  boundary (before the decider's turn) it snapshots the state: the engine memory, the host state, every bot (as in
  the scenario layer's fork), the log lengths and the loop's tallies. It plays each arm from that snapshot, then
  restores it and goes on. It stops after the last fork unless `--full` is passed; then it plays to the end and
  compares the final replay bytes with pass 1's.
- **Arms**:
  - `none`: the bots' own play. Its digests are checked against pass 1 over the whole horizon.
  - `sweep`: one arm per legal action of the decider × `--holds`.
  - `end`: the turn is ended at once, × holds.
  - `home:V[:N]` / `chase:V[:N]`: the lab block's forced verdicts for N rounds.

  Each arm plays `max(marks)` rounds.
- **Legal actions** are found by trying each candidate on the engine, cancelling a recall or tribute channel first,
  and restoring after each try. Candidates:
  - the 8 walks;
  - a basic attack on each alive enemy champion;
  - per ready ability slot, by its props' target mask: self, an enemy or ally champion, a ground tile within 4
    (`--ground all`; by default one tile per distinct set of enemies within 1 of it, empty sets dropped), and dashes
    to tiles within 2 that move the caster;
  - `end`.

  Ocean starts every turn mid recall (its feint), so the fork row records `channel_cancelled`.
- **Forced actions** go through a second block in `tools/combatlab/lab.h`, `LabAct` (128 bytes, magic
  `CAMBC-LAB-ACT-1`), which `labify.py` patches in as `lab_act_run` at the start of `decide`:
  - The runner writes up to 4 ops for one round:
    - 1 walk (a step, or `move_towards` for a farther tile);
    - 2 dash;
    - 3 attack a champion;
    - 4 cast on a champion;
    - 5 cast at a tile;
    - 6 cast with no target;
    - 7 end the turn;
    - 8 attack a camp.
  - The op runs, the bot re-reads its world (`see_again`, `see_stuns`) and plays the rest of the turn itself;
    op 7 skips `act` entirely.
  - A hold of N rewrites the ops before each of the decider's next N turns. A held walk heads to the tile N - 1
    steps further on.
  - `res` per op: 0 done, 1 refused by a hidden unit (rc 0, out 0), 2 dead, 3 a far walk found no step, and
    100 + the engine's error code otherwise.
- **Output**, one JSON line per row:
  - `game`: the champions, rounds, winner, deaths, the branch histogram, the checks (`check.main_ok`,
    `none_arms_differing`, and with `--full` `replay_identical`), `fork_errors`, and CPU ms by phase (pass 1,
    pass 2, arms, snapshots, restores, enumeration).
  - `fork`: round, decider, trigger, every champion's state, tributed gems, the legal list, the snapshot size and
    the CPU time of the enumeration.
  - `arm`: label, `first` (branch, `done_round`, `res`, the tile reached, cooldowns, hits as `[id, hp lost, died]`),
    the decider's first 16 branch chars, and per mark:
    - per champion: alive, deaths, kills, hp, max_hp, gems, gold, items, work turns, turns;
    - per team: tributed gems, deaths, kills, gems, gold, items, work.
  - `--hash` adds the engine memory hash; `--decisions` adds the decider's lab block each turn.
- **Rewards** are left to the driver, `tools/combatlab/fork_sweep.py`.
  - Each arm's value at a mark is a weighted sum of parts, as changes since the fork, own team minus enemy:
    tributed gems, gems carried, wealth (gold + items), kills, deaths, work turns, and whether the decider is dead.
  - Regret is the best arm's value minus the `none` arm's.
  - Its default weights are placeholders, not fitted.

### Checks

- **Identity of the lab copy.** `variants/lab-cl2` is `labify.py variants/oc-cl2-base variants/lab-cl2`. Its flags
  are 0 and its `LabAct` round is -1.
  - At a 100M fuel quantum (`run-batch`, 24 ladder maps, lab-cl2 as A and as B against oc-cl2-base), 47 of 48
    replays are identical, stdout and debug included.
  - The odd one, 00elkring with the lab bot as B, parts at round 39 with a one-tile step difference; the result is
    the same.
  - The cause: ocean's turn-end queue budgets to 100k relative to the turn's start fuel, even at 100M. The hooks'
    fuel (median 224-324 a turn) therefore moves how much of its caches it fills.
  - With `FASTRUNNER_UNLIMITED_BOTS=lab-cl2,oc-cl2-base`, all 48 are identical (only `.fuel` differs).
- **Pass 1 against `fastrunner run`** (wasm engine, lab flags 0): the replays are byte-identical, 4 of 4.
- **Determinism**:
  - The `none` arms match pass 1's digests over all 60 rounds in all 254 forks.
  - The main line after the forks matches pass 1 in 32 of 32 games.
  - With `--full`, the final replays are identical.
  - Arm results (marks, memory hash, `first`) do not depend on the order the arms are played in (636 of 636).
  - A rerun gives identical output (684 of 684 arms).
- **The scenario layer is unchanged.** On 60 bank0 frames with lab-v83, `target/` (HEAD) and `target-lab2/` give the
  same rollout lines when sorted: plain, `--alt 4`, and hitlog + decisions + marks + hash + turns. Setup lines
  differ only in timings.

### Speed

Measured with `fork_sweep.py --games 16 --both-sides --seed 1 --holds 1,3`: 32 cl2-dev games, lab-cl2 against
itself, 254 forks, 5466 arms at H = 60, 16 jobs on the shared box.
- 6.2 s wall, 74 s CPU: 3.4 forks/s and 74 arms/s a core.
- With `--holds 1`: 2860 arms, 56 s CPU, 4.5 forks/s.
- An arm costs ~14 ms of CPU for 60 rounds with all 12 champions alive.
- Pass 1 costs ~0.2 s a game.
- A fork's snapshot is 1.3-2.8 MiB of engine and 5-23 MiB of bots. Taking it costs ~2 ms; restoring it costs
  0.3-1.5 ms an arm, ~10% of the arm CPU on the largest maps.
- Enumerating the legal actions costs 2-15 ms a fork.

### Limits

- **Regret is biased.** Each arm is one deterministic continuation of a chaotic game, and the best of ~21 arms
  gains from selection alone. Regret grows with the number of arms: at mark 60 the mean was 66 with holds 1 and 89
  with holds 1,3.
  - No arm is repeated under perturbation.
  - No second opponent is played.
  - No placebo is measured, such as an arm equal to ocean's own first action.

  Read the results across many forks, never as single verdicts.
- **Parts that need a lab bot or have no reading:**
  - `work` needs lab bots on that side, since it is read from the branch char.
  - The gold a champion earned is not readable, so the parts use the current gold plus the items' shop prices.
- **Forced actions:**
  - A forced action is a single op on the first turn, or a hold of the same kind; there are no sequences of
    different ops.
  - Camps are not enumerated as attack or cast targets, although op 8 exists.
  - `end` skips all of `decide`, so the decider places no ward, shops nothing and starts no recall that turn.
- **The lab copy plays differently.** With lab flags 2 (the default, needed for branches), the hooks cost fuel, so
  the main line is the lab copy's own game rather than oc-cl2-base's. At 100M fuel this differs in about 1 of 48
  games.
- **Failures:** a bot that restarts in an arm cannot be restored. The rest of that fork's arms are lost (listed in
  `fork_errors`), and if the main line cannot be restored, the game stops there.
- **Not done:** Front::admit, guard and cap discard logging.
