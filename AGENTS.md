# Agent guide

Always read `cambc-rules.yaml` if you haven't already. Your next message should mention reading the Cambridge Battlecode rules.

- [cambc-rules.yaml](cambc-rules.yaml): the game rules, engine-verified; it overrides `docs/`.
- [docs/api/cpp.md](docs/api/cpp.md) and [sdk/cpp/cambc.h](sdk/cpp/cambc.h): the C++ API.
- [tools/README.md](tools/README.md): every script.
- The rest of `docs/` (a generated mirror; WebFetch can't read the site) and `tools/probes/` only when these can't answer.

## Bots

C++ only.
- **astraeus** is the bot we work on, the main bot: hyperion plus v44's Willow work (2026-10-23). Its shipped changes are in [CHANGES.md](research/hyperion/CHANGES.md), tagged "(astraeus, date)"; direction, the keep rule and open work are in [TODO.md](research/hyperion/TODO.md). Its `test_draft` is off.
  - Its `src/`: `bot.cc` is the turn (`decide`); its branches are in `economy/` and `combat/`, sharing `bot_parts.h`; `model/` is the world, pathing and safety; `draft/` the draft. `unity.cpp` includes every `.cc`: a new one goes there.
  - `ab.py`'s git refs build `bots/hyperion`, not astraeus. To A/B astraeus, pass bot directories: the working `bots/astraeus` and a frozen copy of a commit's, e.g. `./copybot -r <sha> astraeus variants/astraeus-<sha7>`.
- **demeter** is astraeus as of 2026-11-02 (e9c37971, CHANGES 292) plus pair-yield ([research/demeter-pair-yield-2026-11-02.diff](research/demeter-pair-yield-2026-11-02.diff); EXPERIMENTS "demeter reset"): the draft always takes Cassi & Issac, Cassi farms with the crew, and the pair yields captures to allies. It is the strongest bot measured, ~53.8% against astraeus. The gold lean (`demeter-pair-yield-gold-2026-11-02.diff`) adds gold at level wins and is left out. Judge it against an idle opponent with `py tools/solo.py demeter <ref>` (`bots/idle` never acts) as well as by `ab.py`.
- **hyperion** is the main bot before astraeus; `py tools/ab.py main ...` builds it.
- Drafts are compiled in (`params::draft_preference`).
- `bots/baselines/` holds frozen A/B baselines: never edit them; delete one once current bots beat it ~80% of the time.
- When copying a bot, leave out `.cambc/` (its CMake cache breaks the build): `./copybot SRC DST` does (`-f` replaces DST, `-r REF` copies a commit's).
- `.htb` bots (`bots/htb-starter`) are edited in their `.htb` files, never `src/`; run `py tools/htb/hgen.py <bot>` after.

Comment only counterintuitive behaviour or reasoning, concisely.

## Testing

- **Judge a change** with `py tools/ab.py CAND REF` against a frozen baseline: ~1100 games (ladder, `maps/gen`, `maps/gen-s1`, both sides), noise about ±1.5 points. There are no feature flags; single maps and small samples are noise, and local games are deterministic, so reruns add nothing.
- **Use the fast runner by default** (Linux x86-64, cambc 4.0.0): build [fastrunner](tools/fastengine/runner/) once (`cd tools/fastengine/runner && ./setup_vendor.sh && cargo build --release`), then prefix every `ab.py`, `solo.py` or `run_batched.py` with `CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native` for ~4.7x the games an hour. Replays, fuel and stdout match stock cambc's. Run stock (unset `CAMBC_BIN`) only for debug drawings (`team-?.debug` is empty under fastrunner) or on another platform. Processes still show as `cambc run-batch`: the runner preloads `libfastrunner.so` into it. Differences and numbers: [RUNNER.md](research/fastengine/RUNNER.md).
- **Match the drafts:** both bots on test drafts, or both on their own drafts, never one of each. `ab.py` turns `test_draft` on in the copies it builds from git refs but leaves a bot directory's `params.h` alone (every bot directory's is off). Check the directory's `test_draft`, and pass `--no-test-draft` when it is off. Main on test drafts against v44 on its own read 30.6%; with both on their own it was 49.1%.
- **Confirm a gain** on a suite no A/B has used: `node tools/mapgen/mapgen.mjs suite --out DIR --seed S`, then `--suites DIR`.
- **Record** results in [research/EXPERIMENTS.md](research/EXPERIMENTS.md), which also lists what already won or lost.
- `cambc run --map NAME` finds only maps directly under `maps/`, by full name (`00interlock`); pass `maps/gen/<file>.map26a` for generated ones.

## Fuel

Each turn has 100k fuel (the first 200k); running out loses the rest of the turn.
- **No new fuel gates** (code that chooses worse when fuel is short): make work cheap or bounded instead ([FUEL-GATES.md](research/hyperion/FUEL-GATES.md)).
- **Fuel-only changes** must leave `tools/fuel/bench.py`'s replays byte-identical.
- **Tracing:** wrap output in `debug_block({ ... });` and build without `--release` (plain printf changes the game). Output is in the replay zip as `team-a.stdout` / `team-b.stdout`. It is not free: a block costs ~8 fuel beyond the SDK's refund and debug codegen differs, so fuel-gated decisions can change ([EXPERIMENTS.md](research/EXPERIMENTS.md#fuel)). For a fuel-exact trace of a real game, use the replay harness ([tools/replay/harness](tools/replay/harness/README.md)).
- **Costs:** ~1 fuel per WASM instruction and per memset/memcpy byte; an allocation ~130 plus ~290 to free; a thrown and caught `cambc::error` ~3.9k; `std::cout` ~11k of static initialisation (use printf).
- **Host calls** cost a flat price whatever work they do, so moving a loop into bitboard, field or shadow-cast calls is usually the biggest saving; per-tile tests still beat building a board for a few tiles. Prices are in tools/README.md.

## Rules verification

The engine is closed source; rules are settled by probe bots in `tools/probes/` ([README](tools/probes/README.md): how to run them, and which probe checks which rule). If the engine contradicts the YAML, tell the user immediately, then confirm with a probe, update the YAML and add the probe to the README's table.
