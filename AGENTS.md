# Agent guide

Always read `cambc-rules.yaml` if you haven't already. Your next message should mention reading the Cambridge Battlecode rules.

- [cambc-rules.yaml](cambc-rules.yaml): the game rules, engine-verified; it overrides `docs/`. It is a declarative source of truth: each entry states the rule on its own, with no citations, references to other keys, probe names or sources (those go in `tools/probes/README.md`).
- [docs/api/cpp.md](docs/api/cpp.md) and [sdk/cpp/cambc.h](sdk/cpp/cambc.h): the C++ API.
- [tools/README.md](tools/README.md): every script.
- The rest of `docs/` (a generated mirror; WebFetch can't read the site) and `tools/probes/` only when these can't answer.

## Bots

C++ only.
- **astraeus** is the bot we work on, the main bot: hyperion plus v44's Willow work (2026-10-23), with ocean's draft, plan-check resign and farm recall changes (CHANGES 402-404) since 2026-11-05 (CHANGES 409: 55.0% against a790c441, 20,480 games). Its shipped changes are in [CHANGES.md](research/hyperion/CHANGES.md), tagged "(astraeus, date)"; direction, the keep rule and open work are in [TODO.md](research/hyperion/TODO.md). Its `test_draft` is off.
  - Its `src/`: `bot.cc` is the turn (`decide`); its branches are in `economy/` and `combat/`, sharing `bot_parts.h`; `model/` is the world, pathing and safety; `draft/` the draft. `unity.cpp` includes every `.cc`: a new one goes there.
  - `ab.py`'s git refs build `bots/hyperion`, not astraeus. To A/B astraeus, pass bot directories: the working `bots/astraeus` and a frozen copy of a commit's, e.g. `./copybot -r <sha> astraeus variants/astraeus-<sha7>`.
- **astraeus_wip** is astraeus plus the phases replacing assumptions by calculations (CHANGES 362-397, 399 and on, astraeus_wip's own). 50.7% against astraeus at 10M fuel a turn, 44.7% at the real budget (6c8746a4): the loss is out-of-fuel turns (EXPERIMENTS "Phase 1-2 fuel"). astraeus is 57194754 (CHANGES 361) plus the changes that cost no fuel: CHANGES 398 (362, 364-368, 370, 371, 382) and 400 (EXPERIMENTS "Fuel-neutral changes back in astraeus").
- **ocean** (its 402-404 are in astraeus: CHANGES 409) is astraeus 5b66bde0 plus the draft5 draft with no team lock (CHANGES 402), the resign on a failed plan check (403), farm's recall out while carrying and its re-weighed pick during the channel (404), SPSA run oc2's 61 constants (405), and the idea programme's winners (`research/ideas-2026-11-05/`): exact farm-turn fuel savings (406), home Monolith sieges from the spawn (407) and altar control on one-altar maps (408), plus the gold-pricing audit's winners (`research/ideas-2026-11-05/value.md` round 2): a fight value for emblem stats (413) and farm's gold funnelled to the richer body (414). Own drafts, ladder-mix suites: 405 read 53.2% against `variants/oc-base1` (402-404), 56.8% against astraeus and 55.0% against proteus (20,480 games each); 406-408 read 51.3% against `variants/oc-base2` (402-405; 20,480 games), and about 57.5% against astraeus and 56% against proteus (10,240 each); 413-414 read 53.8% against `variants/oc-combo2` (402-408; 20,480 games), 53.0% on `--mix varied`, panel mean +2.9, with 11% more out-of-fuel turns. `variants/oc-base1`, `variants/oc-base2`, `variants/oc-combo2` and `variants/oc-base3` (= ocean, 2026-11-05) are frozen bases; `bots/ocean_tune` is the tunified copy the tuner ran on. Its `test_draft` is off.
- **demeter** is a copy of astraeus as of 2026-11-02 (38aa25ce, CHANGES 294, which took demeter's pair-yield: EXPERIMENTS "demeter reset"). The gold lean (`demeter-pair-yield-gold-2026-11-02.diff`) adds gold at level wins and is left out. Judge it against an idle opponent with `py tools/solo.py demeter <ref>` (`bots/idle` never acts) as well as by `ab.py`.
- **proteus** is astraeus as of d04b171 (CHANGES 334) plus a cheaper slot scorer, plus enemy turn windows (`model/turn_window.{h,cc}`: next-round earliest/latest slot per enemy, unseen enemy turns left this round, second-turn picks, a tighter double-blow estimate) and team slot assignment (allies claim next-round slots through a shared ledger in comms, so two don't bid for the same one, scored over the enemy orders that are actually possible). 53.1% vs f22811d over 1196 `ab.py` games (CI 50.3-55.9); about 50% more out-of-fuel turns than main. It predates main's CHANGES 326-334.
- The engine is cambc 5.0.0 (balance patch 4.0.0, 2026-11-04: CHANGES 389); frozen baselines and `tools/replay/harness` trace bots keep their 2.0.0 stat tables.
- **hyperion** is the main bot before astraeus; `py tools/ab.py main ...` builds it.
- **diana** is astraeus fc99b847 plus the ostrich with its `params.h` constants made patchable, the base for `tools/tune` (SPSA, the exploiter league). Tuned values are ported back into astraeus as `constexpr` (CHANGES 321).
- Older bots kept for reference: `hermes`, `river` and `river_ac` (.htb), `starter-cpp`.
- Drafts are compiled in: astraeus drafts from the draft lab's model (`draft_model.h`, draft5 on cambc 5.0.0), else its per-pick-count table, with no team lock: Cassi & Issac is no longer forced, nor Stellar banned (CHANGES 402). With `test_draft` on it plays `test_compositions` instead, the top 15 teams' 16 most common ladder compositions per pick count, chosen by map with their frequency as weight (`tools/draftlab/test_comps.py`, refreshed 2026-11-05).
- `bots/baselines/` holds frozen A/B baselines: never edit them; delete one once current bots beat it ~80% of the time.
- When copying a bot, leave out `.cambc/` (its CMake cache breaks the build): `./copybot SRC DST` does (`-f` replaces DST, `-r REF` copies a commit's).
- `.htb` bots (`bots/htb-starter`) are edited in their `.htb` files, never `src/`; run `py tools/htb/hgen.py <bot>` after.

Comment only counterintuitive behaviour or reasoning, concisely.

## Testing

- **Judge a change** with `py tools/ab.py CAND REF` against a frozen baseline: 1280 games (the 128 ladder maps, `maps/gen`, `maps/gen-s1`, both sides), noise about ±1.5 points. There are no feature flags; single maps and small samples are noise, and local games are deterministic, so reruns add nothing.
- **Use the fast runner by default** (Linux x86-64, cambc 5.0.0): build [fastrunner](tools/fastengine/runner/) once (`cd tools/fastengine/runner && ./setup_vendor.sh && cargo build --release`), then prefix every `ab.py`, `solo.py` or `run_batched.py` with `CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native` for ~4.7x the games an hour. Replays, fuel and stdout match stock cambc's. Run stock (unset `CAMBC_BIN`) only for debug drawings (`team-?.debug` is empty under fastrunner) or on another platform. Processes still show as `cambc run-batch`: the runner preloads `libfastrunner.so` into it. Differences and numbers: [RUNNER.md](research/fastengine/RUNNER.md).
- **Match the drafts:** both bots on test drafts, or both on their own drafts, never one of each. `ab.py` turns `test_draft` on in the copies it builds from git refs but leaves a bot directory's `params.h` alone (every bot directory's is off). Check the directory's `test_draft`, and pass `--no-test-draft` when it is off. Main on test drafts against v44 on its own read 30.6%; with both on their own it was 49.1%. The exception is a deliberate one: our own draft against a `test_draft` opponent, to measure play against ladder compositions.
- **Confirm a gain** on a suite no A/B has used: `node tools/mapgen/mapgen.mjs suite --out DIR --seed S`, then `--suites DIR` (at most ~30k maps per mapgen command; larger runs can exhaust memory). Suites made from 2026-11-05 on are ladder-like (`--mix ladder`, the default); don't compare their win rates with earlier `maps/fresh-*` (`--mix varied-v1` remakes those). Add `--mix varied` to test robustness on stress maps.
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
