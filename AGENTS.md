# Agent guide

Always read `cambc-rules.yaml` if you haven't already. Your next message should mention reading the Cambridge Battlecode rules.

- [cambc-rules.yaml](cambc-rules.yaml): the game rules, engine-verified; it overrides `docs/`. Each entry states its rule on its own, with no citations, cross-references or sources (those go in `tools/probes/README.md`).
- [docs/api/cpp.md](docs/api/cpp.md) and [sdk/cpp/cambc.h](sdk/cpp/cambc.h): the C++ API.
- [tools/README.md](tools/README.md): every script.
- The rest of `docs/` (a generated mirror of the game site) and `tools/probes/` only when these can't answer.

The engine is cambc 5.0.1.

## Bots

C++ only.
- **charybdis** is our main bot: a stable version holding only changes we are committed to keeping. Try ideas in copies (`bots/variants/`, gitignored) and commit to it only what has passed its gate. Each shipped change is in [CHANGES.md](research/CHANGES.md), tagged with its bot and date, with its evidence in [EXPERIMENTS.md](research/EXPERIMENTS.md); the latest entry for a bot names the frozen copy that equals it.
- **ocean** is charybdis's ancestor (charybdis branched from ocean 506 with a Prism gem-carry macro and its own draft), and **astraeus** is ocean's. **scylla** is charybdis 525 without Prism, around a fed Vesper Vale: a sparring opponent. The other bots are older experiments kept for reference; retired ones are in `bots/archives/` (pass them as `archives/NAME`).
- Their `src/`: `bot.cc` is the turn (`decide`); its branches are in `economy/` and `combat/`, sharing `bot_parts.h`; `model/` is the world, pathing and safety; `draft/` the draft. `unity.cpp` includes every `.cc`: a new one goes there.
- Drafts are compiled in; charybdis's comes from a draft-lab model (`tools/draftlab`). With `params::test_draft` on, a bot plays ladder compositions (`tools/draftlab/test_comps.py`) in place of its own draft; every committed bot's is off.
- Copy a bot with `./tools/copybot SRC DST` (`-f` replaces DST, `-r REF` copies a commit's). It leaves out `.cambc/`, whose CMake cache breaks the build.
- `ab.py`'s git refs build `bots/ocean` unless `--bot` names another (e.g. `--bot charybdis`). To A/B a working tree, pass bot directories: the working one and a frozen copy, e.g. `./tools/copybot -r <sha> charybdis variants/charybdis-<sha7>`.
- `.htb` bots (`bots/archives/htb-starter`) are edited in their `.htb` files, never `src/`; run `py tools/htb/hgen.py <bot>` after.

Comment only counterintuitive behaviour or reasoning, concisely.

## Testing

- **Judge a change** with `py tools/ab.py CAND REF --suites DIR,...` against a frozen copy, on 20k+ games of fresh suites (`maps/suites/`), or with `fgate.py`; noise is about ±1.5 points at 1280 games. Without `--suites` it plays only the 256 ladder games, a quick check. Single maps and small samples are noise, and local games are deterministic, so reruns add nothing.
- **A/Bs play release builds** (`debug_block` compiled out, as on the platform). `ab.py --debug` plays debug builds when you need their traces; compare only like with like.
- **SPRT screens on one suite share their first games** unless each run passes its own `--sprt-seed` (default 0): give each screen its own seed and confirm on held-out maps.
- **Use the fast runner** (Linux x86-64): build [fastrunner](tools/fastengine/runner/) once (`cd tools/fastengine/runner && ./setup_vendor.sh && cargo build --release`), then prefix every `ab.py`, `solo.py` or `run_batched.py` with `CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native` for ~4.7x the games an hour. Replays, fuel and stdout match stock cambc's. Run stock (unset `CAMBC_BIN`) only for debug drawings (`team-?.debug` is empty under fastrunner) or on another platform. Details: [RUNNER.md](research/notes/RUNNER.md).
- **Fresh-map gates** use `py tools/fgate.py CAND REF` (bot dirs, `test_draft` off): batches of 2,560 unused fresh `--mix ladder-v2` maps plus the 128 ladder maps, both sides, against the Fish and Mite bodies. It reads REJECT / ZONE / ACCEPT after each batch: `--max-batches N` caps it, `--screen` stops at ACCEPT, `--first-batch J` plays maps earlier gates have not. Ordinary two-bot A/Bs use `ab.py`.
- **Match the drafts:** both bots on test drafts, or both on their own drafts, never one of each. `ab.py` turns `test_draft` on in the copies it builds from git refs but leaves a bot directory's `params.h` alone, so pass `--no-test-draft` for bot directories. The exception is deliberate: our own draft against a `test_draft` opponent, to measure play against ladder compositions.
- **Confirm a gain** on a suite no A/B has used: `node tools/mapgen/mapgen.mjs suite --out DIR --seed S` (at most ~30k maps per command; larger runs can exhaust memory), then `--suites DIR`. `--mix ladder-v2` matches the ladder better than the default `ladder`, and the two don't share win rates; `--mix varied` tests robustness on stress maps.
- **Labs** fit the draft (`tools/draftlab`), constants (`tools/tune`) and emblem choices (`tools/emblab`) from many games. Run them sparingly: they risk overfit and only help when the bot has changed significantly since the last fit.
- **Name a live upload for its bot and code, not for its test:** the bot, then the CHANGES number or 7-character commit, then whatever it adds, in a few words: `Charybdis 522 (de94a7f)`, `Charybdis 520 + psafe-a + emblem lab 6`.
- **Record** results in [research/EXPERIMENTS.md](research/EXPERIMENTS.md), which also lists what already won or lost.
- `cambc run --map NAME` finds only maps directly under `maps/`, by full name (`00interlock`); pass a path (`maps/suites/.../<file>.map26a`) for generated ones.

## Overfit

- **Arbitrary changes risk overfit**: a tweak that wins on our suites and opponents can lose on the ladder. Tie each change to a strategy or game mechanic you can state. Avoid magic numbers, special cases that patch one map or matchup, and workarounds for a symptom you haven't explained. Prefer constants derived from the rules or a measured quantity.
- **Live tests are small samples** (about 500 games, against tens of thousands locally), so a live result carries several points of noise, and live-testing many small changes works like rerolling. Keep them for large changes or batches of related ones that a local A/B can't answer.

## Fuel

Each turn has 100k fuel (the first 200k); running out loses the rest of the turn.
- **Fuel-aware code is allowed when it wins by A/B win rate**: budgets per subsystem, anytime searches on the fuel left, dynamic reserves, a cheaper method on a short turn. Out-of-fuel recovery stays as the crash guard.
- **Fuel cuts need no gate**: saving fuel is a strict improvement, but fuel-only changes must leave `tools/fuel/bench.py`'s replays byte-identical (at 100M).
- **Draft precompute** must finish in the draft's first turn (10M). Local builds find `sdk/cpp/cambc_local.h`; the platform's SDK has none. With it, a bot resigns locally on an unfinished draft or an unusable plan (`DRAFT-UNFINISHED`, `PLAN-CHECK`), which the A/B tools flag as early losses; `DRAFT-CAPPED` marks a first turn whose last-resort cap cut sections. Check headroom with `tools/draftlab/firstturn.py --need` ([DRAFT-FEATURES.md](research/notes/DRAFT-FEATURES.md)).
- **Tracing:** wrap output in `debug_block({ ... });` and build without `--release` (plain printf changes the game). Output is in the replay zip as `team-a.stdout` / `team-b.stdout`. A block costs ~8 fuel and debug codegen differs, so fuel-gated decisions can change. For a fuel-exact trace of a real game, use the [replay harness](tools/replay/harness/README.md).
- **Costs:** ~1 fuel per WASM instruction and per memset/memcpy byte; an allocation ~130 plus ~290 to free; a thrown and caught `cambc::error` ~3.9k; `std::cout` ~11k of static initialisation (use printf).
- **Host calls** cost a flat price whatever work they do, so moving a loop into bitboard, field or shadow-cast calls is usually the biggest saving; per-tile tests still beat building a board for a few tiles. Prices are in tools/README.md.

## Rules verification

The engine is closed source; rules are settled by probe bots in `tools/probes/` ([README](tools/probes/README.md): how to run them, and which probe checks which rule). If the engine contradicts the YAML, tell the user immediately, then confirm with a probe, update the YAML and add the probe to the README's table.
