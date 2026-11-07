# Agent guide

Always read `cambc-rules.yaml` if you haven't already. Your next message should mention reading the Cambridge Battlecode rules.

- [cambc-rules.yaml](cambc-rules.yaml): the game rules, engine-verified; it overrides `docs/`. It is a declarative source of truth: each entry states the rule on its own, with no citations, references to other keys, probe names or sources (those go in `tools/probes/README.md`).
- [docs/api/cpp.md](docs/api/cpp.md) and [sdk/cpp/cambc.h](sdk/cpp/cambc.h): the C++ API.
- [tools/README.md](tools/README.md): every script.
- The rest of `docs/` (a generated mirror; WebFetch can't read the site) and `tools/probes/` only when these can't answer.

## Bots

C++ only.
- **astraeus** and **ocean** are our main bots. Changes often move between them: each shipped change is in [CHANGES.md](research/hyperion/CHANGES.md), tagged with its bot and date, with its evidence in [EXPERIMENTS.md](research/EXPERIMENTS.md); open work is in [TODO.md](research/hyperion/TODO.md). Frozen copies for A/Bs live in `bots/variants/`. ocean is `variants/oc-base16` (CHANGES 457: Willow follows the group and hands captures to allies, on 456).
- **fish** tests replicating Intercontinental Fish's behaviour ([PLAN.md](research/fish-bot-2026-11-06/PLAN.md)).
- The other bots are older experiments and baselines, kept for reference.
- Their `src/`: `bot.cc` is the turn (`decide`); its branches are in `economy/` and `combat/`, sharing `bot_parts.h`; `model/` is the world, pathing and safety; `draft/` the draft. `unity.cpp` includes every `.cc`: a new one goes there.
- `ab.py`'s git refs build `bots/hyperion` (the main bot before astraeus). To A/B astraeus or ocean, pass bot directories: the working one and a frozen copy of a commit's, e.g. `./copybot -r <sha> astraeus variants/astraeus-<sha7>`.
- Drafts are compiled in. ocean drafts from draft7's F92 model (draft6's ladder-mix lab repeated with oc-base10 the player; CHANGES 454, oc-base14); astraeus stays on draft5. With `params::test_draft` on, a bot plays ladder compositions (`tools/draftlab/test_comps.py`) in place of its own draft; every bot directory's is off.
- The engine is cambc 5.0.0; frozen baselines and `tools/replay/harness` trace bots keep their 2.0.0 stat tables.
- `bots/baselines/` holds frozen A/B baselines: never edit them; delete one once current bots beat it ~80% of the time.
- When copying a bot, leave out `.cambc/` (its CMake cache breaks the build): `./copybot SRC DST` does (`-f` replaces DST, `-r REF` copies a commit's).
- `.htb` bots (`bots/htb-starter`) are edited in their `.htb` files, never `src/`; run `py tools/htb/hgen.py <bot>` after.

Comment only counterintuitive behaviour or reasoning, concisely.

## Testing

- **Judge a change** with `py tools/ab.py CAND REF` against a frozen baseline: 1280 games (the 128 ladder maps, `maps/gen`, `maps/gen-s1`, both sides), noise about ±1.5 points. There are no feature flags; single maps and small samples are noise, and local games are deterministic, so reruns add nothing.
- **SPRT screens on one suite share their first games** unless each run passes its own `--sprt-seed` (default 0), so their early H1s aren't independent: give each screen its own seed and confirm held out.
- **Use the fast runner by default** (Linux x86-64, cambc 5.0.0): build [fastrunner](tools/fastengine/runner/) once (`cd tools/fastengine/runner && ./setup_vendor.sh && cargo build --release`), then prefix every `ab.py`, `solo.py` or `run_batched.py` with `CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native` for ~4.7x the games an hour. Replays, fuel and stdout match stock cambc's. Run stock (unset `CAMBC_BIN`) only for debug drawings (`team-?.debug` is empty under fastrunner) or on another platform. Processes still show as `cambc run-batch`: the runner preloads `libfastrunner.so` into it. Differences and numbers: [RUNNER.md](research/fastengine/RUNNER.md).
- **Match the drafts:** both bots on test drafts, or both on their own drafts, never one of each. `ab.py` turns `test_draft` on in the copies it builds from git refs but leaves a bot directory's `params.h` alone (every bot directory's is off). Check the directory's `test_draft`, and pass `--no-test-draft` when it is off. Main on test drafts against v44 on its own read 30.6%; with both on their own it was 49.1%. The exception is a deliberate one: our own draft against a `test_draft` opponent, to measure play against ladder compositions.
- **Confirm a gain** on a suite no A/B has used: `node tools/mapgen/mapgen.mjs suite --out DIR --seed S`, then `--suites DIR` (at most ~30k maps per mapgen command; larger runs can exhaust memory). Suites made from 2026-11-05 on are ladder-like (`--mix ladder`, the default); don't compare their win rates with earlier `maps/fresh-*` (`--mix varied-v1` remakes those). Add `--mix varied` to test robustness on stress maps.
- **Record** results in [research/EXPERIMENTS.md](research/EXPERIMENTS.md), which also lists what already won or lost.
- `cambc run --map NAME` finds only maps directly under `maps/`, by full name (`00interlock`); pass `maps/gen/<file>.map26a` for generated ones.

## Fuel

Each turn has 100k fuel (the first 200k); running out loses the rest of the turn.
- **Fuel-aware code is allowed when it wins by A/B win rate** (relaxed 2026-11-06): budgets per subsystem, anytime searches on the fuel left, dynamic reserves, a cheaper method on a short turn. Exact savings are still checked by `bench.py` identity at 100M; out-of-fuel recovery stays as the crash guard ([FUEL-GATES.md](research/hyperion/FUEL-GATES.md)).
- **Fuel-only changes** must leave `tools/fuel/bench.py`'s replays byte-identical.
- **Draft precompute** must finish in the draft's first turn (10M). Local builds find `sdk/cpp/cambc_local.h`; the platform's SDK has none. A bot with the guard (oc-draftfin) resigns locally on an unfinished draft or an unusable plan (`DRAFT-UNFINISHED`, `PLAN-CHECK`), which ab.py, run_batched, bench, tune.py and the lab flag as early losses. `DRAFT-CAPPED` marks a first turn whose last-resort cap cut sections. Check headroom with `tools/draftlab/firstturn.py --need` ([draft-features.md](research/ideas-2026-11-06/draft-features.md)).
- **Tracing:** wrap output in `debug_block({ ... });` and build without `--release` (plain printf changes the game). Output is in the replay zip as `team-a.stdout` / `team-b.stdout`. It is not free: a block costs ~8 fuel beyond the SDK's refund and debug codegen differs, so fuel-gated decisions can change ([EXPERIMENTS.md](research/EXPERIMENTS.md#fuel)). For a fuel-exact trace of a real game, use the replay harness ([tools/replay/harness](tools/replay/harness/README.md)).
- **Costs:** ~1 fuel per WASM instruction and per memset/memcpy byte; an allocation ~130 plus ~290 to free; a thrown and caught `cambc::error` ~3.9k; `std::cout` ~11k of static initialisation (use printf).
- **Host calls** cost a flat price whatever work they do, so moving a loop into bitboard, field or shadow-cast calls is usually the biggest saving; per-tile tests still beat building a board for a few tiles. Prices are in tools/README.md.

## Rules verification

The engine is closed source; rules are settled by probe bots in `tools/probes/` ([README](tools/probes/README.md): how to run them, and which probe checks which rule). If the engine contradicts the YAML, tell the user immediately, then confirm with a probe, update the YAML and add the probe to the README's table.
