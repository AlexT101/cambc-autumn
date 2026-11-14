# A faster, fuel-exact engine for cambc 4.0.0: measurements and design

2026-11-01. Investigation, then Stage 0 and 0b of the plan (§5). Machine: AMD Ryzen AI 7 445 laptop (6 cores, 12 threads), cambc 4.0.0
(build-id `207dc997…`). Raw numbers are in measurements.json; every tool used is under
[tools/fastengine/](../../tools/fastengine/) (see "Reproducing" at the end).

## Verdict

- **10x is not reachable for our bots while staying fuel-exact.** The bots' own compiled WASM is 13-19% of a game's
  time today (six games profiled), and a fuel-exact engine must run *that same machine code*: upstream wasmtime
  49.0.2, configured as cambc is, produces compiled modules byte-identical to cambc's. Even if everything except
  the bot code cost nothing, a game could get at most 5.4-7.8x faster. Realistic targets are lower.
- **A ~2.4x gain is available now, proven byte-exact** (Stage 0 and 0b, §5). An in-process patch of stock cambc
  ([turbo.c](../../tools/fastengine/turbo/turbo.c); `CAMBC_TURBO=1` in `tools/cambc_env.py`, or `LD_PRELOAD`)
  replaces cambc's export lookups, guest-pointer checks and altar-lock scan with exact C versions and memoises the
  hottest game read.
  - One core: demeter v astraeus on 00ambush 1.13 → 0.47 s (2.38x); 2.1-2.6x over six games.
  - The A/B corpus, 4 games at once: 1.92x CPU (1.70x wall) in release builds, 1.53x in debug builds.
  - Parity: on 1164 A/B games in release builds, the same 1164 in debug builds (as `ab.py` plays), 100 games against
    `bots/idle` and 26 fuel-probe runs, every replay file came out byte-identical to stock's.
- **A rewritten runner is no longer worth building.** It was estimated at 2.0-2.7x per game (2.3-2.7x with a read
  memo); the patch now reaches that. A runner can only remove host-call glue, ~21% of a patched game (bot code is
  ~40% and the engine ~30%, the same machine code either way), so it would add at most ~1.25x.
- **The reported ~10x is probably measured against cambc without its compile cache.** Uncached, cambc spends
  6.4-6.6 CPU-s a game compiling both bots with Cranelift, against 1.13 CPU-s cached. A runner that caches
  compiled modules and trims the host glue is about 10x faster than *that*. Our tools already use the cache
  (`tools/cambc_env.py`), so most of that gain is already ours. The claim itself is unverified.

**Recommendation:** run A/Bs with `CAMBC_TURBO=1` on Linux, re-run `verify.py` on the corpus after any cambc or patch
change, and do not build a new runner (Stage 1) unless bot-code time itself becomes the target.

## 1. How cambc runs a game

The binary keeps its symbols, so its structure is readable.

- **Game logic** is a C++ library (namespaces `Engine::`, `Deep::`) behind a C API of 181 functions: `Game_Runner_*`,
  `Game_Action_*`, `Game_API_*`, `Bitboard_*`, `DistanceField_*`, `Game_SaveReplay`. It is linked natively into
  cambc. The same library, compiled to WASM, is the visualiser's engine (`tools/replay/engine/v2_0_0.wasm` exports
  the same API, `Game_Runner_*` included).
  - Rules, turn order, vision, camps, combat, draft and replay encoding all live there.
  - Idle vs idle plays 2000 rounds in 0.03 s.
- **The runner** is Rust: crates `runner` (`runner::api` holds ~200 import closures, covering the C++ SDK's 99 env
  imports plus variants for GC languages; `runner::engine::ffi` holds the engine bindings) and `wasm_runtime` (`Runtime::{start, run_turn_scaled}`, `FuelMeter`, `charge_fuel`).
  - It embeds wasmtime 49.0.2 (a vendored copy; see §4 for why that does not matter).
  - Each bot is a WASI command whose `_start` runs on a wasmtime fiber via `call_async`.
  - `yield` (end turn) is an async import.
  - Fuel is set with `set_fuel`, and running out suspends through `fuel_async_yield_interval`. Both are public
    wasmtime APIs, called from `Runtime::start` and the yield import.
- **Host prices:**
  - Only primitive imports charge, through `wasm_runtime::charge_fuel(caller, amount)`. It multiplies the amount
    (as f64) by the language multiplier and sets the store's fuel, leaving 0 when the price exceeds what is left.
  - Game reads (`champion`, `champion_gems`, `bc_round_number`, ...) charge nothing on the host side; their cost
    is the bot-side WASM around the call.
  - Prices observed with the charge hook (§2.3):
    - Whole-board ops cost the board's 8x8-chunk count: 169, 81, 63 and 24 on the four maps measured.
    - Distance fields cost a multiple of the chunk count, depending on the expansion count.
    - Shadow casts cost 56-394, depending on the scan count.
    - List results cost 3 per element (`altar_locks`, `wards`, `allies`).
    - `read_shared_memory` and `write_shared_memory` cost 1; draft memory 128.
- **Operator costs** are wasmtime's defaults except `memory.grow`, which is free (flat and per page). This was
  recovered from the engine section of cambc's cached modules (`floor costs`).
- **Replay bundle:**
  - The bundle is a zip of `replay.repl26a` (written by the engine's `Game_SaveReplay`), `team-{a,b}.stdout`,
    `team-{a,b}.debug` and `team-{a,b}.fuel`.
  - A `.fuel` file is a 13-byte header (`a62leuf…`), then 8 u64 budgets (10M/100k/200k/100k, twice), then fuel
    used per turn: draft turns first, then every champion turn.
  - Local games are deterministic: repeated runs give byte-identical bundles.

## 2. Measurements

### 2.1 Method

- **Timing:** `cambc run A B --map M --release` with a warm `CAMBC_WASMTIME_CACHE` and `RAYON_NUM_THREADS=1`, one
  game at a time, median of 3. The fixed cost of a `cambc run` (build check, process, module load) is 0.01-0.03
  CPU-s.
- **Profile:**
  - samply at 4-20 kHz, user and kernel; kernel time is ~2%.
  - Samples were classified by [prof_analyze.py](../../tools/fastengine/prof_analyze.py) from the leaf frame and
    whether a JIT frame is on the stack. "JIT" means the instruction pointer was in anonymous executable memory,
    i.e. the bots' compiled code, fuel metering included.
  - An earlier user-space-only samply build (from before `perf_event_paranoid` was lowered) gave the same split.
- **Call counts and prices:** [fuelhook.c](../../tools/fastengine/fuelhook/fuelhook.c), an `LD_PRELOAD` hook that
  counts every entry to each import's wasmtime trampoline (all host calls) and every `charge_fuel` (price, caller).
  It adds time but no fuel: replays stayed byte-identical.
- **Fuel:** totals come from the replays' `.fuel` files.

### 2.2 Where a game's time goes

Shares of samples; times are stock cambc, one game at a time.

| game | s | bot JIT | engine work | altar_locks scan | export lookup | other glue | game loop | replay | startup | other |
|---|---|---|---|---|---|---|---|---|---|---|
| demeter v demeter, 00ambush | 1.16 | 15.0% | 21.2% | 26.1% | 19.0% | 13.4% | 2.1% | 1.2% | 1.5% | 0.6% |
| astraeus v hecate, 01big-world | 1.08 | 13.1% | 20.7% | 27.5% | 19.6% | 11.6% | 2.2% | 1.1% | 1.1% | 3.1% |
| astraeus v hecate, 00ambush | 0.87 | 12.8% | 21.2% | 26.7% | 21.3% | 8.9% | 2.5% | 1.3% | 1.5% | 3.6% |
| astraeus v astraeus, gen-huge-shared | 0.67 | 18.6% | 19.8% | 17.2% | 23.8% | 13.3% | 2.7% | 1.6% | 2.2% | 0.9% |
| hecate v hecate, 00pilgrimage | 0.99 | 12.9% | 19.0% | 14.3% | 31.4% | 13.7% | 2.7% | 2.1% | 0.9% | 3.1% |
| demeter v idle, 00swirl | 0.20 | 15.1% | 17.3% | 7.9% | 28.2% | 15.5% | 7.8% | 1.6% | 4.4% | 2.0% |

What the columns are:

- **Bot JIT:** the bots' compiled WASM, fuel checks included. This is the floor (§3).
- **Engine work:** the C++ engine's own work inside host calls. It splits into:
  - distance field, shadow cast and reachability: 4-11%;
  - whole-board bitboard ops: ~2%;
  - the game-API layer (`Game_API_Champion_Get`, `Game::Valid`, `Visible`, `Engine::Result`, ...): 8-12%.
- **altar_locks scan:** `runner::engine::ffi::visible_altar_locks`. Every bot reads altar locks each turn, and the
  runner answers by testing every tile of two occupancy boards (W*H bit tests, twice), ~20 µs a call.
- **Export lookup:** every import fetches the bot's memory with `Caller::get_export("memory")`, which runs two
  SipHash lookups (string pool, export map). That is 5.7M lookups in the demeter game.
- **Other glue:** wasmtime's host-call trampolines and `catch_unwind_and_record_trap`, `guest_ptr` bounds checks,
  `charge_fuel` and `FuelMeter`.
- **Fiber switches** (12k suspend/resume per game) are under 0.2%. **Process start, module cache load and
  instantiation** cost ~13 ms a game.

Confidence: the shares are high-confidence (±1-2 points; stock and user-space-only samply agree within 2 points).
The split of "engine work" into its three parts is medium-confidence (it relies on leaf names).

### 2.3 Host calls and fuel

| game | fuel (M) | of which host-charged | host calls (M) | JIT throughput (G fuel/s) |
|---|---|---|---|---|
| demeter v demeter, 00ambush | 768 | 158 | 4.56 | 3.5 |
| astraeus v hecate, 01big-world | 670 | 192 | 4.09 | 3.4 |
| astraeus v hecate, 00ambush | 552 | 136 | 3.54 | 3.7 |
| astraeus v astraeus, gen-huge-shared | 450 | 53 | 3.20 | 3.2 |
| hecate v hecate, 00pilgrimage | 644 | 126 | 5.99 | 4.1 |
| demeter v idle, 00swirl | 151 | 6 | 1.14 | 4.9 |

- **JIT throughput** is (fuel minus host-charged fuel) / JIT time. It is consistent at 3.2-4.9 G fuel/s, which
  cross-checks the JIT share.
- **Calls per turn:** a game makes ~750 host calls per champion turn.
- **Call mix** in the demeter game (full table; closure-to-engine map in
  import-closures.txt):
  - `champion` 1.13M, `bc_round_number` 0.63M, `champion_gems` 0.42M, `bc_Bitboard_Test` 0.37M,
    `bc_DistanceField_Get` 0.32M, `fuel_remaining` 0.26M, `bc_champion_priority` 0.18M;
  - then a long tail of 90 imports.
  - Distance fields: 8.7k a game, ~8.5 µs each. Shadow casts: 41k, ~0.7 µs each.

### 2.4 Cost of a host call in a lean runner

[floor bench-calls](../../tools/fastengine/floor/src/bench.rs) times, in wasmtime 49.0.2 with cambc's config, a
WASM loop calling an import 20M times:

| | ns per call | fuel off |
|---|---|---|
| loop alone | 0.42 | 0.22 |
| import, no `Caller` | 3.3 | 2.8 |
| import, reads and writes guest memory through a `Memory` handle kept in the store | **6.8** | 6.4 |
| the same, looking memory up with `caller.get_export("memory")` each call (cambc's pattern) | 34.4 | 35.2 |

So 4.5M calls cost ~30 ms in a lean runner, against ~0.4 s of lookup and glue in cambc.

### 2.5 The compile cache

demeter v demeter on 00ambush:

| | wall | CPU |
|---|---|---|
| uncached, all cores | 2.0 s | 6.4-6.6 s |
| uncached, `RAYON_NUM_THREADS=1` | 4.1 s | 4.1 s |
| cached | 1.16 s | 1.13 s |

The replay is identical in all three.

### 2.6 What was not measured, and why

- **A full game of bot code standalone** (the bots' WASM with recorded host results) was not run.
  - Recording every host call's memory effects needs per-import knowledge of output buffers, which is the runner
    rewrite itself.
  - The floor instead comes from in-game sampling (JIT 13-19%), the consistent fuel throughput across six games,
    and the compiled-code identity in §4. A cleaner process might run the same code 10-20% faster (less cache
    pollution); that is not measured.
- **The engine's speed as WASM** (the visualiser build) was not measured.
- **The exact fuel and turn semantics of cambc's runner** were located, not reverse-engineered: `Runtime::start`,
  `run_turn_scaled`, the yield import, `charge_fuel`, `FuelMeter::reported_active`, the per-import price formulas.
- **A profile of the patched cambc** could not be taken at first: samply dropped cambc's mapping once a patch split
  it. Fixed since (§5.1).
- **Performance on a homogeneous many-core server** (where `ab.py` usually runs) is unknown. On this laptop the
  gains shrink as load rises (§5).
- **Windows** was not tried. `LD_PRELOAD` and `dlopen` are Linux-only.

## 3. The floor, and the speedup we can defend

A fuel-exact engine must stop each bot at exactly the same instruction when fuel runs out. It must also report the
same `fuel_remaining` everywhere, because our bots run out ~3 times a game and branch on fuel.

- wasmtime meters fuel during translation to Cranelift IR: each operator adds its cost; checks sit at function
  entries and loop headers; the count is flushed before calls.
- The cheapest way to match it is to run the same wasmtime with the same tunables. That gives the same machine code
  (§4) and therefore the same JIT time.
- **Can the bot code itself run faster?**
  - Cranelift flags (spectre mitigations and so on) don't change fuel semantics, but the code is already
    `opt_level=speed`; at most a few percent.
  - An LLVM ahead-of-time compiler that reproduces wasmtime's fuel placement exactly is possible in principle. It
    would need a wasm2c-class compiler, async suspension, and proof of identical fuel at every check. A plausible
    1.3-2x on the JIT share is not worth that risk.
  - Turning fuel metering off is not an option (it roughly halves a tight loop's cost, §2.4).

Estimated time per game for the faithful-runner routes (§6), from the measured shares, 4.5M calls at 7 ns, and the
engine's work unchanged:

| game | stock | Stage 0 patch (measured) | new runner, est. | + read memo, est. | Stage 0b patch (measured, §5) | ceiling (bot code only) |
|---|---|---|---|---|---|---|
| demeter v demeter, 00ambush | 1.16 s | 0.62 s (1.87x) | 0.51 s (2.3x) | 0.45 s (2.6x) | 2.26x | 6.6x |
| astraeus v hecate, 01big-world | 1.08 s | 0.54 s (1.95x) | 0.47 s (2.3x) | 0.41 s (2.6x) | 2.60x | 7.6x |
| astraeus v hecate, 00ambush | 0.87 s | 0.46 s (1.95x) | 0.40 s (2.2x) | 0.35 s (2.5x) | 2.52x | 7.8x |
| astraeus v astraeus, gen-huge-shared | 0.67 s | — | 0.33 s (2.0x) | 0.27 s (2.5x) | — | 5.4x |
| hecate v hecate, 00pilgrimage | 0.99 s | — | 0.44 s (2.2x) | 0.36 s (2.7x) | — | 7.8x |
| demeter v idle, 00swirl | 0.20 s | — | 0.10 s (1.9x) | 0.09 s (2.3x) | 2.13x | 6.6x |

Notes on the table:

- The patched columns are measured (single game; Stage 0b's ratio is from §5's interleaved runs, whose stock times
  differ from these by a few percent); the two estimate columns are estimates. The patch now matches the estimated
  new runner with a read memo.
- "Read memo" means caching game-API reads within a turn until the bot acts (§6, Stage 2), assumed to remove 75% of
  the API layer.
- Rewriting distance field and shadow cast natively, with identical expansion and scan counts (they set the
  price), could add ~5-10%: about 2.7-3.2x in all.
- These are one-game-at-a-time figures. On this laptop the patch's 1.71x one-at-a-time became 1.35-1.47x at 6-10
  parallel games, so expect a similar shrink for any route when the machine is full.

## 4. Parity

### Proven so far

- **Compiled code.** Upstream wasmtime 49.0.2 with the config below compiles each of `bots/archives/demeter`,
  `bots/astraeus` and `bots/hecate` to a serialized module byte-identical to the one in cambc's own compile cache:
  `.text`, the engine section and the whole artifact (`floor check-cache`). The config:
  - `consume_fuel(true)`;
  - Cranelift `opt_level=speed`;
  - `relaxed_simd_deterministic(true)`;
  - `wasm_component_model(false)`;
  - default operator costs except `MemoryGrow = 0` and `memory_grow_per_page = 0`;
  - default (copying) GC collector.

  Our engine also loads cambc's cached modules directly. Whatever cambc's vendored wasmtime changes, it is not the
  compiled code, fuel instrumentation included. Runtime-side behaviour (the out-of-fuel yield, fibers) is not
  covered by this check and must be confirmed by `.fuel` equality.
- **Patched cambc.** Stage 0: 420 games, every zip member byte-identical to stock:
  - astraeus v hecate on the first 50 and first 20 ladder maps (both sides), at 1, 3, 6 and 10 parallel games;
  - demeter v idle on 50 maps.

  Stage 0b (the final library): the whole A/B corpus in release and in debug builds (2328 games), 100 against idle
  and 26 fuel-probe runs, every replay file byte-identical (§5.7).
- **Native engine.** cambc's native engine is callable from our own process ([dlengine.c](../../tools/fastengine/dlengine/dlengine.c)):
  - load a copy of the binary with `DF_1_PIE` cleared through `dlopen`;
  - resolve `Game_*` addresses from the symbol table;
  - `Game_FromMapFileBytes` (0.12 ms), then `Game_Runner_Init`; `Game_API_Map_GetNumCampGroups` then returns 12 on
    00ambush.

  Game rules therefore never need reimplementing.

### What "the same game" means, and how to check it on hundreds of games

- **Criterion:**
  - Every member of the replay zip is byte-identical: `replay.repl26a`, `team-{a,b}.fuel`, `team-{a,b}.stdout`,
    `team-{a,b}.debug`.
  - The zip container itself may differ (deflate settings).
  - `.fuel` equality is the per-turn fuel check: every turn's fuel used, to the unit.
  - `replay.repl26a` equality is every action, error and result, since the engine encodes the input log.
- **Corpus:**
  - The `ab.py` suites (ladder, `maps/gen`, `maps/gen-s1`, both sides; ~1100 games) for the current main bot
    against a baseline and against `bots/idle`.
  - `maps/gen-bench` and the fuel census maps (heavy in out-of-fuel turns).
  - The fuel probes in `tools/probes/`: `probe-fuel*`, `probe-endturn-fuel`, `probe-fueladjust*`,
    `probe-suspend-*`, `probe-firstturn`.
  - Debug builds (`fuel_pause` imports, `debug_block` output).
  - [verify.py](../../tools/fastengine/turbo/verify.py) already does the paired run-and-compare for the patch;
    the same harness works for a new runner.
- **On a mismatch:**
  - The first differing `.fuel` entry gives the turn.
  - `tools/replay/extract.mjs` on both replays gives the first differing event.
- **When to re-run:** the full corpus on every cambc release, and before any patch or runner is used for A/B
  decisions.

## 5. Stage 0 and 0b, measured: the in-process patch

[turbo.c](../../tools/fastengine/turbo/turbo.c) (`LD_PRELOAD`, or `CAMBC_TURBO=1` through `tools/cambc_env.py`) now
applies four patches. It acts only in a process whose GNU build-id is cambc 4.0.0's, so python, cmake and the wasi-sdk
clang under `~/.cache/cambc` are untouched. Before patching it checks every function it replaces or relies on in full
(FNV-1a of the function's bytes, 16 functions) and every GOT slot it rewrites; a mismatch turns that patch off.

| patch | what it replaces | §  |
|---|---|---|
| 1. altar locks | `visible_altar_locks`' scan of every tile, twice | 5.2 |
| 2. export cache | `Instance::get_export("memory")` (and `"champion_query_memory"`) SipHash lookups | 5.2 |
| 3. guest memory | `runner::api::memory`, 7 `guest_ptr::<T>`, 3 `champion_out::<T>` | 5.3 |
| 4. read memo | `Game_API_Champion_Get`, behind epoch thunks on 111 GOT slots | 5.4 |

Single game, CPU 0, release builds, stock and patched runs interleaved, median of 5 (CPU seconds; all replays
identical to stock's). "Stage 0" is the library before Stage 0b (patches 1-2 as first written); the patches add up
left to right (switched off with `TURBO_NO_*`):

| game | stock | Stage 0 | 1-2 refined | + 3 | + 4 (final) |
|---|---|---|---|---|---|
| demeter v astraeus-d7d9dab, 00ambush | 1.125 | 0.620 (1.81x) | 0.579 (1.94x) | 0.516 (2.18x) | **0.472 (2.38x)** |
| demeter v astraeus-d7d9dab, 01big-world | 1.035 | 0.590 (1.75x) | 0.526 (1.97x) | 0.472 (2.19x) | **0.435 (2.38x)** |
| astraeus v hecate, 01big-world | 1.196 | 0.561 (2.13x) | | | **0.461 (2.60x)** |
| astraeus v hecate, 00ambush | 0.898 | 0.464 (1.94x) | | | **0.357 (2.52x)** |
| demeter v demeter, 00ambush | 1.197 | 0.685 (1.75x) | | | **0.530 (2.26x)** |
| demeter v idle, 00swirl | 0.206 | 0.131 (1.57x) | | | **0.097 (2.13x)** |
| demeter v astraeus-d7d9dab, 00ambush, debug build | 1.725 | 1.110 (1.55x) | | | **0.907 (1.90x)** |

Throughput, 4 games at once (`cambc run-batch --jobs 4` on CPUs 2-5, the laptop's slower cores), demeter v
astraeus-d7d9dab on the first 30 ladder maps from both sides (60 games a configuration, configurations interleaved
by chunks of 12; all 300 replays identical to stock's):

| | stock | Stage 0 | 1-2 refined | + 3 | + 4 (final) |
|---|---|---|---|---|---|
| CPU per game | 1.087 s | 0.726 s (1.50x) | 0.711 s (1.53x) | 0.653 s (1.66x) | **0.573 s (1.90x)** |
| wall (60 games) | 21.1 s | 14.9 s (1.42x) | 14.7 s (1.44x) | 13.7 s (1.54x) | **12.4 s (1.70x)** |

Over the whole A/B corpus (§5.7, chunks of 20): 1.92x CPU and 1.70x wall in release builds, 1.53x and 1.47x in debug
builds. Wall gains trail CPU gains because each chunk ends with idle slots.

Stage 0 (patches 1-2 as first written), measured before Stage 0b:

| run | games | identical | CPU per game, stock → patched | speedup |
|---|---|---|---|---|
| demeter v demeter, 00ambush, single | 1 | yes | 1.16 → 0.62 s | 1.87x |
| astraeus v hecate, 20 maps x 2 sides, 1 job | 40 | 40 | 0.533 → 0.312 | 1.71x |
| same, 3 jobs | 40 | 40 | 0.630 → 0.380 | 1.66x |
| same, 6 jobs | 40 | 40 | 0.840 → 0.571 | 1.47x |
| astraeus v hecate, 50 maps x 2, 6 jobs | 100 | 100 | 0.750 → 0.540 | 1.39x |
| astraeus v hecate, 50 maps x 2, 10 jobs | 100 | 100 | 1.198 → 0.887 | 1.35x (wall 12.8 → 9.4 s) |
| demeter v idle, 50 maps x 2, 10 jobs | 100 | 100 | 0.480 → 0.318 | 1.51x (wall 5.3 → 3.4 s) |

Under load, per-game CPU rises more for patched runs, whose remaining work (bot code, engine) suffers more from shared
caches, SMT and lower all-core clocks. This laptop also mixes core types. A server should be measured before quoting a
throughput figure.

Using it: `CAMBC_TURBO=1 py tools/ab.py ...` (or `CAMBC_TURBO=/abs/turbo.so`, or `LD_PRELOAD=/abs/turbo.so`). Without
it, behaviour is stock. `TURBO_OFF=1` and `TURBO_NO_{ALTAR,EXPORT,GUEST,MEMO}=1` switch patches off; `TURBO_VERBOSE=1`
prints counts at exit; `TURBO_CHECK=1` cross-checks every memo hit against the real call and aborts on a difference.

### 5.1 Profiling the patched binary

The earlier patch made two 2-page ranges of cambc's text writable and back. Each `mprotect` of executable memory emits
a kernel mmap event for the new, split mapping, and samply (fxprof `LibMappings::add_mapping`) drops every mapping it
overlaps, so all of cambc became "JIT". The patch now makes the whole executable segment writable once, writes every
patch, and restores it: the events cover the whole mapping and cambc keeps its symbols. Trampolines and GOT thunks
live in one anonymous page (a few instructions; they show as JIT).

Profile of Stage 0 on demeter v astraeus-d7d9dab, 00ambush (0.59 s; 10 kHz):

- bot JIT 27%; engine 35% (DistanceField 10.7%, `Game_API_Champion_Get` 7.9% inclusive, ShadowCast 5%, `Game::Act`
  4.8%); host-call glue 26%; game loop 4%; replay 2%; startup 3%.
- The glue: `guest_ptr::<T>` 8.4% inclusive (of which the cached export lookup ~4% and `Memory::internal_data_size`
  3.2%), `runner::api::memory` 2.6%, `champion_out` 3.2% (an uncached `get_export("champion_query_memory")` that
  misses for C++ bots, then `memory`), the altar-lock fast path itself 3% (a W/8 x H loop of empty chunks),
  `catch_unwind_and_record_trap` and `array_call_trampoline` self time 8.7% (the closures' bodies are inlined there).

### 5.2 Patches 1-2

As in Stage 0:

1. **`visible_altar_locks`:** every bot reads altar locks each turn, and the runner answers by testing every tile of
   two occupancy boards. The replacement makes the same engine calls in the same order (metadata, ally board,
   `Game_API_GetAltarLock` per set bit, enemy board, per set bit), visiting only the set bits in the original's tile
   order; stable-sorts by the record's u32 at offset 4 as the original does; returns the same count, buffer or
   error. On any engine error it reruns the original, so the engine's last error ends as the original leaves it.
2. **`Instance::get_export`:** the 32-byte `Option<Extern>` is cached per (store, store id, instance index). An
   instance's exports never change.

Refined in Stage 0b:

- **Altar locks** skip a chunk row (8 map rows) whose chunks are all empty before walking its rows; same calls, same
  order.
- **Export cache** also caches an absent export (the `"champion_query_memory"` lookup of every `champion_out`), and now
  caches only `Extern::Memory` and `None`: a `SharedMemory` carries reference counts that a byte copy would not take.

### 5.3 Patch 3: guest memory

`runner::api::memory`, the seven `runner::api::primitives::guest_ptr::<T>` instantiations (element sizes 1, 2, 4, 8,
12, 40, 120) and the three `runner::api::champion_out::<T>` (4, 4, 28 bytes) are replaced by C versions.

- Each original looks the memory up through `get_export`, the store's instance table and
  `Memory::internal_data_size`, then checks the guest pointer.
- The replacement resolves the caller instance's `VMMemoryDefinition` pointer once per (store, store id, instance)
  by the same chain (it is fixed for the instance's life), then reads base and current length from it on every call
  and applies the same checks: pointer non-negative, `count * size` and `ptr + bytes` not overflowing, no null pointer
  with a non-empty range (guest_ptr only), within the length, host address aligned. Errors return the same `Err(-1)`.
- Anything unusual (no plain Memory export, an instance with a `champion_query_memory` export) runs the original.

### 5.4 Patch 4: read memo

`Game_API_Champion_Get` is a quarter of all host calls (1.08M in demeter v astraeus on 00ambush) and the heaviest read
(stat breakdowns with passive callbacks). It is answered from a 512-entry cache while the game is unchanged.

- **Where state changes.** The runner reaches the engine only through its GOT: all 183 `R_X86_64_RELATIVE`
  relocations that target an engine export are in `.got`, and no runner code calls or `lea`s an engine entry point
  directly (both checked over the whole disassembly). The 111 entry points not known to be pure (actions, runner,
  draft, statistics, shared-memory writes, and every read not on the list) are redirected to a 27-byte thunk that
  advances an epoch (`lock incq`, touching only r11 and flags) and jumps on; ~150k thunks run a game.
- **What is pure.** `Bitboard_*` and `DistanceField_*` take no game. The 28 listed `Game_API_*` reads reach, over the
  static call graph, only const `Engine::Game` methods, the plain accessors `Health` and `Runtime`, jump tables, and
  the passive stat callbacks `GemFocus` and `HealthStrength` (pure arithmetic). No getter calls `SyncState`,
  `UpdateVision` or a statistics capture; those come only from actions and turn phases.
- **What a hit must reproduce.** The key is (game handle, perspective, champion id, output pointer non-null) and the
  epoch. The engine writes the 44-byte record only on success, and ends every path with `Engine::Result(code, msg)`,
  which sets a thread-local last-error pointer (`%fs:0 - 0x5f0`, read by `bc_get_last_error`). A hit returns the
  cached code, copies the record on success, and sets that pointer to what the real call left. `Champion_Get` touches
  no other state (no allocation, no statistics).
- **Measured.** 75% of calls hit (805k of 1.08M) on that game. In `TURBO_CHECK` mode every hit also runs the real call
  into a probe buffer with a canary and aborts on any difference in code, last error, record or bytes past it: none in
  140 debug-build games (ladder, both sides, demeter v astraeus) and the ad hoc games run with it.

### 5.5 Tried and not kept

- **Memo of five small reads** (`Champion_GetGems`, `GetGold`, `IsAlive`, `GetPriority`, `GetCooldown`; 0.93M calls,
  each 4 bytes out): only 41% hit (bots read them once a turn around actions), and the cache cost what it saved
  (0.460 → 0.469 s).
- **ShadowCast memo** (`Bitboard_ShadowCastWithScanCount`, 40k calls, 4% of a game): a pure function of map size,
  walls, x, y and distance once its pointer checks pass (it zeroes the whole result first; on success it leaves the
  last error untouched, which `TURBO_CHECK` caught in a first version). 75% of calls repeat over a game, but keyed by
  the 1.4 KB walls board a 256-entry cache hit 7%, and a 4096-entry one (12 MB) hit 53% and still ran slower
  (0.478 → 0.507 s): hashing and comparing the board and the cache misses it causes cost more than a 0.5 µs cast.
- **DistanceField memo:** `ComputeWithExpansionCount` repeats 39% (51% ignoring the visited and distance buffers'
  prior contents), `ComputeToWithExpansionCount` 2%; with ~25 KB of key and output a call, the ShadowCast result says
  it would not pay.
- Not tried, as each is a few percent at most for real parity risk: replacing whole import closures (the remaining
  wasmtime entry and closure glue is ~3 ns of ~10 ns a call), `charge_fuel` (two atomics and a division, ~1%; fuel
  semantics), the replay's deflate (2%; the whole replay file is byte-identical today and stays so), and the module
  cache's zstd decompression (7% of a short game, 1-2% of a long one).

### 5.6 Where the time goes now

demeter v astraeus-d7d9dab on 00ambush and 01big-world, final patch, 10 kHz (the two games within 1.5 points):

| bot JIT | engine work | host-call glue | game loop | replay | startup | other |
|---|---|---|---|---|---|---|
| 40% | 29-30% | 21-22% | 4-5% | 1.5-1.8% | 2.5-2.8% | 0.5% |

- Engine: DistanceField 10%, ShadowCast 4.3%, `Game::Act` (moves and their vision updates) 4.7%, `Champion_Get` 2.1%
  (was 7.9%).
- Glue: `catch_unwind_and_record_trap` self 8.4% (the import closures' own bodies, inlined there), the patch's own
  functions 6.4% (`guest_ptr::<u64>` for bitboard arguments 2.3%, `memory` 1.1%, `guest_ptr::<i32>` 1.0%, the memo
  0.7%), `array_call_trampoline` 3.2%, `charge_fuel` 1.4%.
- So bot code is now the largest share; the rest is spread over many small items (§5.5).

### 5.7 Parity

The final library (`turbo.c` sha256 `bd4f0d29…`), stock cambc as reference, every map from both sides, `cambc
run-batch` with 4 jobs on CPUs 2-5, stock and patched alternating by chunks of 20 games
([verify.py](../../tools/fastengine/turbo/verify.py)). Bots: demeter and astraeus-d7d9dab (both `test_draft` off),
copied outside the repo unchanged.

| corpus | build | games | every member identical | whole replay file identical | CPU per game, stock → patched |
|---|---|---|---|---|---|
| ladder (`maps/*.map26a`), demeter v astraeus | release | 140 | 140 | 140 | |
| `maps/gen` | release | 512 | 512 | 512 | |
| `maps/gen-s1` | release | 512 | 512 | 512 | |
| all three | release | 1164 | 1164 | 1164 | 1.008 → 0.525 s (1.92x; wall 368 → 217 s) |
| the same 1164 | debug (as `ab.py` plays) | 1164 | 1164 | 1164 | 1.540 → 1.009 s (1.53x; wall 531 → 362 s) |
| demeter v `bots/idle`, first 50 ladder maps | release | 100 | 100 | 100 | 0.336 → 0.150 s (2.24x) |
| fuel probes (below), `cambc run` | debug and release | 26 | 26 | | |
| ladder with `TURBO_CHECK=1` (the same patches, before a refactor of the memo install) | debug | 140 | 140 | | |

- Every member: `replay.repl26a`, `team-{a,b}.fuel` (fuel used every turn), `team-{a,b}.stdout`, `team-{a,b}.debug`.
  The zip container is identical too (same writer, same members).
- Fuel probes: `probe-fuel` (default and `--fuel 50000`), `probe-fuel-b`..`-e` (draft and play exhaustion),
  `probe-fuel-ops`, `probe-endturn-fuel`, `probe-fueladjust` (3 rounds at `--fuel 250000`, 400 rounds),
  `probe-fueladjust-b`, `probe-suspend-channel`, `probe-suspend-memory`, `probe-firstturn`, each in debug and, where
  it builds without the debug-only imports, release (`probe-fueladjust` does not).
- Debug builds gain less (1.53x): `debug_block` output and the `fuel_pause` imports add bot work the patch does not
  touch.

## 6. Recommended architecture and staged plan

### Routes considered (question 4)

| route | game rules | bot runtime | parity risk | speed (one game) | effort |
|---|---|---|---|---|---|
| **A. Patch stock cambc in-process** | cambc's | cambc's | very low: cambc still does everything | 2.1-2.6x measured (§5) | days |
| **B. Own runner + cambc's native engine** (`dlopen`) | cambc's machine code | wasmtime 49.0.2, identical codegen | medium: runner semantics (below) | ~2.0-2.3x; 2.3-2.7x with memo | 3-6 weeks |
| C. Own runner + visualiser engine WASM | same source, as WASM | wasmtime 49.0.2 | medium, plus engine-version pairing | engine work maybe 1.5-2.5x slower (unmeasured): ~1.6-2x | 3-6 weeks; portable to Windows |
| D. Reimplement the rules (Rust) | rewrite | wasmtime 49.0.2 | high | ~same as B (game logic is already cheap) | months |

Notes on the routes:

- Route D buys nothing: game logic outside host calls is 2-3% of a game, and every rule (vision and fog, turn order
  including Cassi/Issac and priorities, camps and sleep, capture timing, combat modifiers, spells, items, draft,
  error codes) would become a parity risk.
- Route B (or C) only needs the **runner** rewritten. Hardest first:
  1. **Turn and fuel semantics:**
     - fuel at turn start (100k; 2x a champion's first turn; 100x the draft's first, `--fuel` overrides);
     - suspension on exhaustion via `fuel_async_yield_interval`, and resuming as the next round's turn;
     - a host price larger than the fuel left: finish the call, leave 0, stop at the next check;
     - `end_turn`'s ~40 fuel;
     - the value `fuel_remaining` reports (`FuelMeter::reported_active`);
     - draft exhaustion rules.

     These are all public wasmtime calls with constants to recover from `Runtime::start`, `run_turn_scaled` and the
     yield import (~4 KB of machine code), then confirm with the existing fuel probes and `.fuel` equality.
  2. **Price formulas** for ~40 charging imports: chunk count, expansion and scan counts, per-element and per-byte
     costs. They can be read off each closure before its `charge_fuel` call and checked with the charge hook on many
     maps.
  3. **The 99 env imports' marshalling:**
     - guest-pointer checks and their error codes;
     - struct layouts (the SDK's `imports.h` matches);
     - `bc_get_last_error` strings;
     - which calls clear the engine's last error (the replay harness notes `bc_round_number` does);
     - `visible_altar_locks`' filtering and sort.
  4. **WASI:** cambc overrides `random_get`, `clock_time_get`, `clock_res_get` and `poll_oneoff` (determinism);
     stdout and stderr capped at 1 MiB a team; the debug log format.
  5. **Output writers:** the `.fuel` writer (`runner::fuel::write_header`); the bundle; optional statistics
     (`Game_Statistics_*`).
  6. **Optional:** debug-build imports (`fuel_pause`, `fuel_resume`, `fuel_adjust`) for traced runs; GC-language
     imports are not needed.

### Staged plan

0. **Stage 0: adopt the patch.** Done (§5): `verify.py` on the full ab.py corpus, `CAMBC_TURBO` in `cambc_env.py`,
   documented in `tools/README.md`.
1. **Stage 0b: more exact patches.** Done (§5.2-5.4): guest-memory checks, the `Champion_Get` memo behind GOT epoch
   thunks. A general read memo did not pay beyond `Champion_Get` (§5.5); `charge_fuel` was left alone (~1%).
2. **Stage 1, only if still needed: own runner, route B** (~3-6 weeks; ~3-5k lines of Rust).
   - Pieces:
     - wasmtime 49.0.2 with `floor`'s `cambc_config()`;
     - the cambc engine through `dlopen`, with route C's engine WASM as a portable fallback behind the same trait;
     - imports reading guest memory through a stored `Memory`;
     - one process playing many games with modules compiled once.
   - Milestones:
     1. draft-only games with identical `.fuel` draft entries;
     2. idle vs idle;
     3. our bots on 00ambush;
     4. the full corpus.
   - Expected: ~2.0-2.3x per game, plus ~13 ms a game saved by staying in one process.
3. **Stage 2: inside the runner** (~1-2 weeks).
   - Read memoisation as in 0b.
   - Optionally, native distance field, shadow cast and reachable mask with identical expansion and scan counts,
     fuzzed against the engine's own functions (callable through `dlopen`).
   - Expected: 2.5-3.2x per game.
   - Not recommended: an LLVM compiler for bot code, or rewriting the rules.

## 7. Main risks

- **cambc updates.**
  - The patch is tied to one build-id and switches itself off on any other (stock speed, no breakage); offsets must
    be refound each release (~1-2 hours with the scripts here). It also relies on wasmtime's store layout (instance
    table at +0x528/+0x530, store id at +0x4c0), the engine's last-error TLS slot and the GOT table; each relied-on
    function is hash-checked, so a changed build only turns patches off.
  - Route B depends on the engine's C API (stable names; struct layouts may change), and on a new wasmtime version
    if cambc upgrades (recheck with `floor check-cache`).
  - Route C must pair each cambc release with its visualiser engine build (`extract.mjs --update-engine`).
- **Gains shrink when the machine is full.** Single-game numbers overstate `ab.py` throughput (laptop: Stage 0's 1.71x
  became 1.35x at 10 jobs; the final patch's 2.38x alone is 1.90x at 4 jobs).
- **Silent divergence in a rare path** (a crash, a stdout cap, a GC-language import, a debug build). Mitigation: the
  corpus in §4, and keeping stock cambc as the reference for any result that decides a merge.
- **Platform.** The patch and `dlopen` are Linux-only. Windows users keep stock speed; route C would be the
  portable one.
- **Scope creep.** A new runner is a parallel implementation that must track every cambc release; the patch is a
  few hundred lines.

## 8. Reproducing

All from the repo root; build products go anywhere outside the repo.

```
# profile (needs perf_event_paranoid <= 1) and time games; then classify
nm -C -S --defined-only ~/.local/share/uv/tools/cambc/bin/cambc | grep -E '^[0-9a-f]+ ([0-9a-f]+ )?[TtWw] ' > /tmp/cambc.syms
tools/fastengine/profile_games.sh OUT "demeter demeter 00ambush" "astraeus hecate 01big-world"
python3 tools/fastengine/prof_analyze.py OUT/*.json.gz --syms /tmp/cambc.syms --imports --leaves 30

# host-call counts and prices (no fuel change)
cc -O2 -shared -fPIC -o /tmp/fuelhook.so tools/fastengine/fuelhook/fuelhook.c
objdump -d ~/.local/share/uv/tools/cambc/bin/cambc --start-address=0x4000000 --stop-address=0x4200000 > /tmp/cambc-raw.dis
python3 tools/fastengine/fuelhook/make_tramp_table.py /tmp/cambc.syms /tmp/cambc-raw.dis > /tmp/tramp.tsv
FUELHOOK_TRAMPOLINES=/tmp/tramp.tsv FUELHOOK_CALLS=/tmp/calls.tsv FUELHOOK_OUT=/tmp/charges.tsv \
  LD_PRELOAD=/tmp/fuelhook.so cambc run bots/archives/demeter bots/archives/demeter --map 00ambush --release -o /tmp/r
python3 tools/fastengine/fuelhook/calls_report.py /tmp/cambc.syms /tmp/calls.tsv
python3 tools/fastengine/fuelhook/hook_report.py /tmp/cambc.syms /tmp/charges.tsv

# compiled-code identity, operator costs, host-call cost (wasmtime 49.0.2)
cd tools/fastengine/floor && CARGO_TARGET_DIR=/tmp/floor cargo build --release && cd -
/tmp/floor/release/fastengine-floor check-cache bots/archives/demeter/.cambc/build-release/bot-injected.wasm .git/cambc-wasmtime/modules/wasmtime-49.0.2
/tmp/floor/release/fastengine-floor costs .git/cambc-wasmtime/modules/wasmtime-49.0.2/<file>
/tmp/floor/release/fastengine-floor bench-calls

# the patch: build, verify byte-identity and speed (the A/B corpus, both sides; --debug as ab.py plays)
cc -O2 -shared -fPIC -o /tmp/turbo.so tools/fastengine/turbo/turbo.c
python3 tools/fastengine/turbo/verify.py demeter variants/astraeus-d7d9dab --turbo /tmp/turbo.so --out /tmp/v \
  --suites ladder,gen,fresh [--debug] [--env TURBO_CHECK=1]
# profile it (the patch keeps cambc's symbols for samply)
LD_PRELOAD=/tmp/turbo.so samply record -r 10000 --save-only --unstable-presymbolicate -o /tmp/p.json.gz -- \
  cambc run bots/archives/demeter bots/archives/demeter --map 00ambush --release -o /tmp/r

# the native engine as a library
cp ~/.local/share/uv/tools/cambc/bin/cambc /tmp/cambc-lib   # then clear DF_1_PIE in DT_FLAGS_1 (0x08000000)
cc -O2 -o /tmp/dlengine tools/fastengine/dlengine/dlengine.c -ldl && /tmp/dlengine /tmp/cambc-lib /tmp/cambc.syms maps/00ambush.map26a
```

`floor check-cache` and `floor costs` write `floor-ours-engine.bin` and `cambc-operator-cost.postcard` into the
current directory; run them from a scratch directory.
