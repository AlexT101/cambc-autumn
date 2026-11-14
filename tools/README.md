# Tools

Run every script from the repo root. The tooling's unit tests (CPU slots, fresh-map gate, run-time opponents, live
scheduler campaigns) are in `tools/tests/`: `python3 -m unittest discover -s tools/tests [-p test_NAME.py]`.

## Running games: the fast runner and CPU slots

```
CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native py tools/ab.py ...   # also solo.py, run_batched.py
./tools/copybot -r REF astraeus variants/astraeus-<sha7>   # a frozen bot (leaves out .cambc/; -f replaces DST)
```

- **fastrunner** (`CAMBC_BIN`, Linux x86-64, cambc 5.0.1; the default for A/Bs, AGENTS.md) plays every match with [the fast runner](fastengine/runner/), cambc's own engine driven by a new runner preloaded into cambc, with stock's replays, fuel, stdout and `.camstat` byte for byte (1164/1164 games on 4.0.0; 1360/1360 on 5.0.0, both modes; on 5.0.1 1344/1344 at the port and 2352/2352 in a re-check on current bots, release and debug, its out-of-fuel counts equal to the replays' 183k rollovers; under any other cambc build the launcher runs stock, which `run_batched.py` and `bench.py` refuse unless `FASTRUNNER_ALLOW_STOCK=1`) but no debug drawings (`team-?.debug` is empty). `FASTRUNNER_MODE=native` (needs clang) translates each bot's wasm to C with wasmtime's exact fuel metering and compiles it (about 7 s a bot, cached); the default runs bots on wasmtime. On the whole machine (11 CPUs, 1164 games of the default suites) ab.py ran at 77k games/h native (4.7x) and 57k exact (3.5x), against 16k for stock (turbo was 1.4x). With fastrunner, `run_batched.py` hands a whole batch to one `run-batch`, which takes a CPU slot per game itself; builds still run stock cambc. Native builds are profile-guided (`FASTRUNNER_PGO=0` turns it off): a new bot takes ~2 s more to build and its code runs ~30% faster; with the engine's statistics recorded only for a `.camstat` and fewer page faults, a game costs ~16% less CPU than before round 3 (2026-11-03), and bundles (libdeflate) ~24% less disk. Build it once: `cd tools/fastengine/runner && ./setup_vendor.sh && cargo build --release` (needs clang's `llvm-profdata` for PGO). [RUNNER.md](../research/notes/RUNNER.md) has the design, numbers and limits; `tools/fastengine/runner/scripts/compare.py` re-checks it against stock (`--camstat` compares `.camstat` too).
- **CPU slots** (`tools/cpu_slots.py`; fastrunner mirrors it): every bench game and every `run_batched.py` run (so `ab.py`, `solo.py`, the labs and the tuner) takes slots from one machine-wide pool of `CAMBC_SLOTS` (default cores - 2), file locks in the git common dir shared by all worktrees, so leave `--threads` at its default (the whole pool) and concurrent agents share the cores game by game. Jobs share by group, not process: a tool and everything it starts is one group (`CAMBC_SLOT_GROUP`, default `job-<pid>` of the first Python tool), weighted by `CAMBC_SLOT_WEIGHT` (default 1; the draft and emblem labs 2). A group keeps a free slot only below its weighted share or when no other waiting group is below its own; a lone job takes every slot, and running games are never stopped (2026-11-03, 8 slots: 10 processes against 1 held 4.0 / 4.0; weight 2 against 1, 4.9 / 3.0). Member records are locked and written before atomic publication, so concurrent cleanup cannot erase a live group's weight. `python3 -m unittest tools.tests.test_cpu_slots` forces the registration race; the runner's `slot_registration_tests` stress concurrent cleanup. `CAMBC_SLOT_DIR` points a test at another pool. A heavy analysis (numpy, scikit-learn) runs as `python3 tools/pooled.py N -- CMD`: it holds up to N slots and sets OpenMP/BLAS threads to the number held, where unpooled it would start a thread per core; a SIGTERM or SIGHUP is passed on to CMD, and pooled keeps the slots until CMD exits. Spaces in `CAMBC_SLOT_GROUP` become `_` in Python but not in the runner, so a name with spaces makes two groups: use none. On Windows every `run-batch` reconfigures both bots' builds as it starts, so a batch there is one `run-batch` holding the slots free at its start (at least 4) until it ends.
- **Few suites per A/B.** Each suite of `ab.py` is its own run-batch polling the slots under one global lock (`fair.lock`): 103 suites at once put the 96-core box at 85% system time and ~1 game/s for everyone else (2026-11-03). Merge many small suites into one directory of symlinks (e.g. `maps/suites/merged/fresh-92all`).
- **Frozen bots:** run_batched.py plays copies in `replays/frozen/<hash of source and SDK>/<name>/`, so editing a bot mid-batch never changes the batch's games, and batches of the same source share one build; `results.json` lists them (`frozen`) and so does ab.py's `summary.json` (each side's `frozen` hashes). `py tools/frozen_janitor.py [--keep-days 7] [--delete]` prunes copies and the fast runner's compile cache (`~/.cache/fastrunner`, shared by every worktree) by last use, a dry run unless `--delete`: an entry goes once unused for `--keep-days` (at least 2; reuse touches a frozen copy, games read its wasm) and no running process refers to it (command line, cwd, open or mapped files, the manifests it names, the bot dirs its ab.py / run_batched.py / solo.py command names); a copy whose `build.lock` is held is skipped. On 2026-11-11 the two held 74 GB and 103 GB. A deleted copy costs its next batch a build (~25 s), a library its next game a native compile (~7 s).
- **WASM cache** (`tools/cambc_env.py`): every match process used to compile both bots' WASM with Cranelift, ~80% of its CPU. Tools that play matches give cambc `CAMBC_WASMTIME_CACHE` (wasmtime's cache, in the git common dir as `cambc-wasmtime/`, keyed by the module's bytes) and `RAYON_NUM_THREADS=1`; replays are byte-identical. A full A/B went from ~154 s to ~25 s (2026-10-29, 96 cores; plus ~25 s to build a new bot). A script that runs `cambc run`/`run-batch` itself should pass `env=cambc_env.env()`.
- **Turbo** (`CAMBC_TURBO`, opt-in, Linux x86-64, cambc 4.0.0 only, so it does nothing under 5.0.x; superseded by fastrunner): with `CAMBC_TURBO=1`, `cambc_env.env()` preloads [turbo.c](fastengine/turbo/turbo.c), built into the git common dir's `cambc-turbo/` (an absolute path names a built library instead), so `CAMBC_TURBO=1 py tools/ab.py ...` runs every match on a patched cambc 4.0.0: about 2.4x faster a game alone, 1.9x at 4 games at once (1.5x in the debug builds `ab.py` plays), with byte-identical replays (any other cambc build runs stock). Re-check after a cambc or patch change with `python3 tools/fastengine/turbo/verify.py --turbo LIB --out DIR BOT_A BOT_B --suites ladder,gen,fresh [--debug]`; [DESIGN.md](../research/notes/FASTENGINE-DESIGN.md) §5 has the patches and parity runs.

## Copying bots: tools/copybot

```
./tools/copybot astraeus my-bot                                  # bots/astraeus -> bots/my-bot
./tools/copybot -f astraeus my-bot                               # replace an existing bots/my-bot
./tools/copybot -r 1c0d627 astraeus variants/astraeus-1c0d627    # bots/astraeus as committed at a ref
```

- **SRC / DST** are names under `bots/` (a leading `bots/` is accepted); they may not overlap. Nothing inside the copy is renamed.
- **Build output is left out:** `.cambc/`, `build/`, `target/`, `.cache/` and `compile_commands.json` at the bot's top level (as `run_batched.py`'s `freeze()`), since they hold the source's absolute paths and a copied CMake cache breaks the build.
- **`-r REF`** copies the bot as committed (`git archive REF:bots/SRC`), not the working tree; a commit's copy is the usual frozen REF for an A/B of a working tree.
- **`-f`** replaces DST, except a frozen baseline under `bots/baselines/`, which it refuses. Without it an existing DST is an error.
- The copy is staged beside DST and renamed into place, so a failed copy leaves DST as it was. `combatlab/labify.py` and `gate_compile_ahead.py` (which seals it in its manifest) call it.

## A/B: ab.py and run_batched.py

```
py tools/ab.py orch/my-branch main --name my-change            # two git refs
py tools/ab.py astraeus baselines/v94 --no-test-draft          # two bot directories
py tools/ab.py main HEAD~1 --no-test-draft --suites maps/suites/merged/SET # each on its own draft
py tools/ab.py astraeus variants/astraeus-38aa25c --no-test-draft --sprt --sprt-stop low  # stop a loser early
```

- **CAND / REF:** a git ref, whose `bots/<--bot>` (default `ocean`; an archived bot such as `archives/hyperion` is also found at `bots/hyperion` in commits before its retirement, and hyperion at `bots/hecate` before 2026-10-21) is exported with `git archive` (never the working tree) to `bots/variants/ab-<name>-<cand|ref>-<sha7>/` with `params::test_draft` on; or a bot under `bots/`, used as is. Run it from the primary checkout (worktree branches resolve there).
- **Options:** `--name`, `--threads` (all CPU slots), `--suites` (default `ladder` alone, a quick check, with a note; `ladder` is the 128 pinned maps below, `ladder-new` the maps under `maps/` outside them, `ladder-all` both; directories of maps; or the legacy `gen` and `fresh`, `maps/suites/legacy/gen/` and each `maps/suites/legacy/gen-s*/`, the default before 2026-11-11), `--bot` (above), `--no-test-draft`, `--fuel N`, `--debug` (below), `--keep-replays N` (below), `--game-timeout S` and `--experiment-config FILE` (the fresh-map gate's run-time opponents, `experiment_config.py` at the end). The suites play at once, sharing the CPU slots (one after another on Windows).
- **Release builds** (the default; `--debug` plays debug builds instead): both bots are built and played as the platform plays them, with `debug_block` compiled out (`run_batched.py --release`: `cambc build --release`, `run-batch --release`). A game costs ~15% less CPU than in debug builds (2026-11-08, ocean vs oc-base29, 12 ladder games on one core: 201 against 236 us a round) and its stdout drops from ~700 KB to almost nothing. Its games differ from debug builds' (a debug block costs fuel), so compare only release with release; use `--debug` when you need the bots' traces (decision lines, `SHORTCUT`, `OOF` phases). Bots print no `OOF` lines in release builds, so the out-of-fuel counts are the fast runner's (each match's `oof_turns` in `results.json`); stock cambc gives none, and the summary then reports an `oof_error`. The runner counts every play turn that ended out of fuel, slightly more than the bots' lines (one per overrun that finished, so two in a row read as one and a game's last is missed): 187 against 172 turns on those 12 debug games.
- **Replay bound:** each suite keeps only its first 1000 finished games' replays (`--keep-replays N`; `0` keeps all, as an agent extracting a whole batch needs). A later game's replay is deleted in batches, before each `results.json` write (a killed run can leave about a second of unlisted replays), after its out-of-fuel, handoff and capped-draft lines are appended to the batch's `pruned-stdout.jsonl` (fsynced first); its match in `results.json` then has `"replay": null` and `"pruned": "<stem>.repl26a"`. `tools/fuel/oof.py` reads that file for any missing replay, so the summary's OOF counts and `oof.py BATCH` cover every game. Failed games' replays are always kept. On 2026-11-08 unbounded SPRT screens (~200 KB a game, ~140 GB/h) filled the 993 GB root disk and crashed ~25 runs. Batches from runs started before the bound, or from other callers named `batch-*-ab-*`, are thinned to their oldest 1000 replays by `py tools/replay_thin.py` (the replay janitor runs it every 15 min; only replays `results.json` lists, 10+ min old, same sidecar first). It skips directories holding `.keep` (pin a batch whose replays you need) or an `oofj.jsonl` (a janitor of its own deletes those). Whole-batch replay readers (`extract.mjs` on a batch, `ab_farm.py`, `solo.py`, `census/`) see only the kept games unless the run passed `--keep-replays 0` or its batch has a `.keep`.
- **Output:** CAND's win % with a 95% Wilson interval, overall and per suite, failed matches, out-of-fuel turns per bot and wall time; `replays/ab/<name>/` holds `summary.json`, `summary.md` and the logs. The exit code is non-zero if a match failed. A run holds `replays/ab/<name>/.run.lock`, so a second ab.py of the same `--name` is refused while it runs. Sides whose `test_draft` differs get a WARNING and a note in the summary (deliberate only when measuring play against ladder compositions).
- **Early stopping:** `--sprt [P0,P1]` (default `0.50,0.52`: CAND's win rate under H0 and H1) ends every suite once a sequential probability ratio test, over all suites together, decides. It uses maps both of whose games have finished, each scoring CAND's mean x in {0, 0.5, 1}, since a map's two sides are correlated: over N maps with mean m and variance v (floored at 0.001), LLR = N (P1 - P0)(2m - P0 - P1) / (2v) (fishtest's normal approximation), accepting H0 at LLR <= ln(beta / (1 - alpha)) and H1 at LLR >= ln((1 - beta) / alpha), ±2.94 at the defaults. `--sprt-alpha`, `--sprt-beta` (0.05 each); `--sprt-stop low` stops only on H0 (not a P1 gain), `high` only on H1, `both` (default) on either, the other only reported; `--sprt-min-games N` (200) never stops sooner; `--sprt-seed` (0) shuffles the map order (`run_batched.py --shuffle`). SPRT screens on the same suite play the same first games unless each passes its own `--sprt-seed`, so their early H1s are not independent (2026-11-06: five H1s at ~2k games on one suite read +0.3-0.6 held out): give each screen its own seed and confirm on held-out maps. An extra SPRT line gives the LLR, its bounds, the map pairs used, the outcome and whether it stopped the run; killed suites are not failures. After a stop the win rates are from a partial sample that mixes the suites by how fast each got CPU slots (about evenly, the first to finish building sooner), not by their sizes. Not on Windows.
- **Farming against the opponent:** `py tools/ab_farm.py <name> [--json OUT]` extracts the run's replays (once, ~8 min for 1164 games) and pairs CAND with REF per game: gold earned @150/300/600/end, capture gold @300 (all, and groups with an Elk or Golem), gold the other side captured on groups one did most of the damage on, camp damage, gold per 1k camp damage, tributed gems @600, deaths to camps; mean CAND - REF with a bootstrap 95% CI, overall and per suite.
- **By map class:** `py tools/ab_classes.py <name> [--by preset,access] [--list access=teleport]` joins an A/B (or batch dirs) with the maps' `index.json`: CAND's win %, the share reaching round 2000 and, once extracted, both bots' mean tributed gems per kind, preset, access, gated, camp mode, spawn or economy.

`run_batched.py` plays two bots on every map, once from each side (it builds them, at once, with `cambc build`, since `cambc run-batch`'s own builds fail on Windows, then compiles each into the WASM cache):

```
py tools/run_batched.py <bot1> <bot2>   # names under bots/, or paths
py tools/run_batched.py --watch         # progress of the newest batch, from another terminal
```

- **`CAMBC_LOG_LIMIT=BYTES`** raises each team's stdout cap (run-batch `--log-limit`, 1 MiB by default) for heavily traced bots.
- **Options:** `--threads N` (all CPU slots), `--one-side` (sides by `--side-seed`), `--maps-dir` (default `maps/`, skipping `maps/gen*/`), `--gen [N]` (`maps/suites/legacy/gen/`, all or N by `--gen-seed`), `--output DIR`, `--fuel`, `--timeout SECONDS`, `--game-timeout` and `--experiment-config` (as ab.py's), `--release` (as ab.py's), `--no-replays`, `--keep-replays N` (keep only the first N finished games' replays, as above; default all), `--shuffle SEED` (play the maps in a seeded random order, each map's two sides together, instead of slowest first).
- **Output** in `replays/batch-TIMESTAMP/`: `results.json` (wins from bot 1's view, then per match; `winner` is the 0-based bot index; replaced whole after each match, so it is never half-written), `<n>-<map>-<12|21>.repl26a` (`12`: bot 1 is team A), `run.log` and `*.error.log`.

## Farming benchmark: solo.py and bots/idle

Mirror A/Bs barely show farming changes, so solo.py plays CAND and REF each against `bots/idle` on the same maps and compares how fast they farm, paired per map:

```
py tools/solo.py astraeus variants/astraeus-<sha7> --name my-change
py tools/solo.py astraeus astraeus --suites ladder --one-side --maps 3   # smoke run, ~15 s
```

- **bots/idle** drafts heart_of_ruin, marcella, vendetta, vesper_vale, ryth in order and ends every champion's turn at once.
- **CAND / REF:** bot directories under `bots/`, used as they are (params.h included, so match their `test_draft`); export a commit as AGENTS.md shows. Games take ~1.5 s, since they end at 1000 gems.
- **Options:** `--name`, `--threads` (all CPU slots), `--suites` (as ab.py's), `--one-side`, `--maps N` (N maps per suite, by `--map-seed`), `--fuel N`, `--debug` (debug builds; release builds, as ab.py's, are the default since 2026-11-11, so earlier solo runs compare only with `--debug` ones). Bots whose `test_draft` differs get a WARNING, as in ab.py.
- **Metrics,** from the replays (extracted into `replays/solo/<name>/analysis/`): the round tributed gems reach 1000 (never: counted as 2001), tributed and collected (tributed + carried) gems at rounds 150/300/600, lifetime gold earned at 300/600. Per map, CAND - REF averaged over sides (a log ratio for the 1000 round, shown as a % change), mean and bootstrap 95% CI over maps, overall and per suite, and the maps where CAND reaches 1000 faster / slower / identical.
- **Checks:** out-of-fuel turns per bot, and games where our bot damages the idle champions (it pokes them on their spawn on small maps such as yellow-brick-road) or either bot errors. Output: `replays/solo/<name>/summary.json` (every game's metrics) and `summary.md`.

## Maps: tools/mapgen

- `maps/` holds the ladder maps as SDK updates ship them (`00ambush`, `01big-world`, ...); delete any uuid-suffixed copies an update adds. Ladder replays drop the prefix; extract.mjs and mapgen accept either.
- **Ladder sets** ([ladder_set.py](ladder_set.py)): from 2026-11-12 `maps/` also holds the platform's 42 `05*` maps (in ranked play since 2026-11-11 23:10 UTC; `cambc maps pull` does not serve them yet, so they were cut, sha256-verified, from captured ranked replays; 40 so far, 05chiseled_brick and 05rocket missing). Every tool that reads `maps/` as "the ladder" uses the 128 maps of 2026-11-05 pinned in `ladder128.txt`, so earlier runs, REF caches and seeded suites stay comparable: run_batched.py and ab.py (`ladder`; `--ladder new|all`, suites `ladder-new`, `ladder-all`), solo.py, fgate (`--ladder all` has its own configs and run names, suffix `-Lall`), tune.py pools naming `maps`, the draft and emblem labs' `maps/*.map26a` (config `"ladder": "all"` for every map) and mapgen (mutation sources and the ladder metrics; same-seed suites are byte-identical to before the 05 maps).
- `maps/suites/legacy/gen/` (seed 6001), `maps/suites/legacy/gen-s1/` (6002; `maps/gen` and `maps/gen-s1` until 2026-11-11) and the `maps/suites/fresh/fresh-<seed>/` are generated 256-map suites, not in git (`.gitignore`): rebuild them with the commands below (~2 s a suite). Generate at most ~30k maps in one command (larger runs can exhaust memory). For a held-out test take seeds no A/B has used (`maps/SUITES.md`, EXPERIMENTS). Suites made from 2026-11-05 on (`--mix ladder`, the new default) are not comparable with earlier fresh suites: `maps/gen`, `maps/gen-s1` and the `maps/suites/fresh/fresh-*` of 2026-10-30 to 2026-11-05 are `varied` suites of calibration 1, which `--mix varied-v1` remakes byte for byte (mutations only when `maps/` holds the same ladder maps: they draw their source from it at run time). Before 2026-10-30, A/Bs used other maps under the same names (seeds 6003-6196 of the older generator, before that 4001-5120, 2901-2934, 1201/1202). `index.json` records each map's kind (its family), preset (or mutated ladder map and its edits), spec and metrics, the suite's `mix`, and from calibration 2 on its `calib` and `select`.
- **Calibration.** generate.mjs has two sets of defaults. Calibration 2 (`DEFAULTS_V2`, `V2_PRESETS`; the default of `gen`, `mutate` and every mix but the -v1 ones) is fitted to the 128 ladder maps of 2026-11-05, each map weighted equally (the 42 `04*` maps of SDK 5.0.0 are a third): ladder sizes and aspects (sides from 28), picks by area, the ladder's altar make-ups (pairs plus 0-3 self-mirrored altars, odd sides forced when a map needs them), the nearest altar contested on ~3 maps in 4, altars with 7+ open neighbours, camp groups drawn from the ladder's make-ups (wolf + gold, wolf + gems, gem carpets, ...; `LADDER_GROUPS`) with per-map tilts, shared groups on the axis by symmetry, home camps 1-3 tiles from a spawn, gem-only economies, winding barriers (walls or dash-crossable hole lines), dash cuts, and a tidy pass that removes most leaky diagonals and 1-wide gaps. It also fixes calibration 1's camp spacing (every camp kept `camp_spawn_gap` 5 away, so `spawn_reach_gap` never brought a monster nearer). Calibration 1 (`DEFAULTS`, the 2026-10-30 rates) is unchanged: `--calib 1` for `gen` and `mutate`. Calibration 3 (2026-11-08; `DEFAULTS_V3`, `V3_PRESETS`, `--calib 3`, `--mix ladder-v2`) is calibration 2 plus: the ladder's group shapes (`LADDER_SHAPES`: 2x2 squares, pluses, 2x3 and 3x3 blocks, monsters on the best-connected cells, big groups as near-full blocks, lines on few maps), gem-only groups of 3+ cells (gem balls) on 30% of maps, not 50% (the ladder: 28%; per-map `ball_mult`, and `gold_mult` for gold-only groups), more shared groups under rotation, slightly more lakes, and classic and monolith-only with bushes and without classic's `shared_camp` (under calibration 2 it failed every classic map without a shared group, so classic came out mostly mirrored). Calibration 2 is unchanged: `--mix ladder` still makes the same maps byte for byte.
- **Mix** (`suite --mix`):
  - `ladder` (the default with `--out`): `LADDER_PLAN`, ladder-like presets (`ladder` 112, `classic` 30, 16 others 2-6 each) and 64 ladder maps under random edits, no stress families, at fixed counts, keeping the first candidates to succeed (1.3x oversampled) so the suite has the sampler's distribution. Every metric of the report is within ~6 points of the ladder (KS 0.11 or less; the ladder's own sampling noise is ~0.12). Use it to judge changes.
  - `ladder-v2`: the same plan under calibration 3. On 41 numeric and 33 share metrics it has no ladder mismatch at p < 0.01, against 8 for `ladder` (gem balls on 50% of maps against 28%, group shapes, cluster-only groups spread over too many maps). Preferred for new programmes; `ladder` stays the default until programmes on it finish, and the two don't share win rates. Its mutations are `ladder`'s.
  - `ladder-v3` (2026-11-12): `ladder-v2`'s 256 maps (the same entries, candidate seeds and maps for a seed) plus 84 in the 05 maps' style (`P05_PLAN`: calibration 4's `ladder05` 63, the 05 maps under random edits 21), 340 a suite. Ranked play draws the 170 pool maps uniformly (113,965 games from 11-11 23:10, top teams' too), so the 42 `05*` maps are 42/170 of it and 84/340 matches. Calibration 4 (`DEFAULTS_V4`, `--calib 4`) is calibration 3 refitted to the 40 05 maps in `maps/` (pinned in `tools/ladder05.txt`): 3x3 spawns with every camp 5+ tiles away and a group right at that limit on about half the maps, make-ups from `GROUPS_05` (mostly one monster guarding a compact block; per-map multipliers keep singletons, pairs and cluster-only groups on few maps) in `SHAPES_05`'s blocks, shared groups almost only on mirrored maps, more walls, fewer holes, bushes absent or plentiful. Against all 168 published maps in `maps/` it shows no mismatch at p < 0.01 on the 41 numeric and 33 share metrics (`ladder-v2`: 2), and its 05 part none against the 05 maps (`ladder-v2`: 12). `--mix ladder-05` makes the 05 part alone.
  - `ladder-v4` (2026-11-12): `ladder-v3` with the full-pool layer (`POOL_FIT` in generate.mjs; plan entries pick it with `{ fit: 'pool' | 'pool05' }`) on its generated entries; the mutated ones are unchanged. A classifier on all 130 per-map metrics still told `ladder-v3` from the 168 maps (AUC 0.63 against a null of 0.50) on what compare.py's list never tested: the ladder keeps its 2-tile frame open (41% of maps, v3 19%), has hole-framed arenas (13% with under half the frame playable, v3 7%) and close spawns (14% under spawn_rel 0.5, v3 4%, which the spawn gates excluded). The layer opens the frame on maps without winding barriers (whose ends it keeps, so their detours stay), adds shaped arenas and `near` spawns, and gives the 05 part fewer barriers. On held-out seeds the classifier no longer separates it (0.54 against 0.50 ± 0.05), and no metric of compare.py's list differs at p < 0.01 against the 168 or the 05 maps.
  - `paradigms` (2026-11-08): `PARADIGM_PLAN`, 12 layouts none of the ladder mixes draws, about 21 maps each, from [paradigms.mjs](mapgen/paradigms.mjs), under calibration 3's ladder rates for everything else (sizes, with sides under 50 weighted 1.35x because the layouts fail more attempts on small maps; symmetry, picks, spawns, altars, camp groups, gems and gold), 1.5x oversampled, first kept. On 2,048 maps against the 128 ladder maps (compare.py, mapfeat.py) every economy, size and count test passes (altar tiles, picks, symmetry, spawn shape, groups and camps per side, shared groups, gem balls, gems, gold, group sizes per map); the layouts differ by design: fewer winding maps (a walk of 2 or more times the spawns' Chebyshev distance on 7%, the ladder 20%), walls and holes on more maps (no holes on 24%, the ladder 37%), wider chokes. Use it for robustness against unfamiliar layouts, not to judge a change. The layouts:
    - ring-road: an impassable core (lake, mesa or walled jungle; lakes now and then with a bridged plaza) ringed by a road and gated walls;
    - colosseum: a walled arena in the middle (gates open, bush or dash), cover inside;
    - isles: islands between hole channels along noise contours, bridged on foot where needed;
    - choke-web: warped Voronoi regions behind thick ridges, joined by passes of 1-5 tiles;
    - corridors: long parallel corridors 3-6 wide with doorways; almost half serpentine (one door a wall, alternate ends);
    - stones: evenly spaced small posts, blocks and pluses of wall, hole or bush;
    - mesa-field: open ground with a few big wall mesas and hole craters;
    - contours: wall and hole lines along noise contours, broken by gaps (terraces, waves);
    - compartments: two or three big rooms a side behind thick gated walls, sometimes round a central plaza;
    - braided-lanes, home-keeps, meander-river (drawn after the spawn, generate.mjs's `post_spawn`): 2-4 lanes from spawn to spawn between bent, broken dividers; a gated courtyard round each spawn, often nested with turned gates; a bending hole river between the spawns with bridges, dash narrows and banks.
  - `varied` and `fixed`: the stress-heavy plan below (three quarters designed, exotic, quirks, topology and scenario maps) under calibration 2, for robustness. `varied` reweighs the plan per seed: each family and each preset is scaled by a random factor and a preset is sometimes dropped, so fresh suites stress different things; `fixed` keeps the plan's counts. Both keep the most different of 3x candidates (`--oversample`).
  - `varied-v1` and `fixed-v1`: the same under calibration 1, as `varied` and `fixed` were before 2026-11-05. `varied-v1` is the default without `--out`, so a rebuild of the legacy `gen` or `gen-s1` keeps them as they are.

  The stress plan's shares:
  - **ladder-like** (~16%): presets close to the competition maps; **mutation** (~9%): a ladder map and its edits, both drawn from the seed.
  - **designed** (~26%): scenarios laid out by [design.mjs](mapgen/design.mjs), each pinning a test:
    - atoll: a treasure island reached only by dash or crystal.
    - archipelago: typed island links.
    - rivers: bridges and dash fords.
    - fortress: a gated keep.
    - gatekeeper: a barrier crossed at open, bush, camp-plugged, dash or crystal gates.
    - dungeon: rooms with loops.
    - three-lane: a MOBA-style layout.
    - arena: fight-centric.
    - farmland: farm-centric.
    - continent: an organic void shape.
    - hedges: vision.
  - **exotic** (~22%): shapes, interiors, spawn distances and economy extremes (gem-drought, gem-flood, gold-flood).
  - **quirks** (~4%, generate.mjs):
    - big-groups: composed groups of 4-32 cells;
    - wild: every relaxed constraint at once, including touching spawns and 1x9 spawns.
  - **topology** (~12%, [topology.mjs](mapgen/topology.mjs)): a graph-first designer and spawn extremes:
    - topo-web, topo-tree: cycle-rich networks against single routes.
    - topo-split: halves joined only by dash or crystal.
    - topo-island: a home left only by dash or crystal.
    - topo-backdoor: own camps a crystal from home, on foot only through enemy ground.
    - topo-toll: a short road past a big camp against a long safe detour.
    - topo-shortcut: a dash or crystal gap cutting a long walk 3x or more.
    - topo-necks: body-blocking (1-wide corridors and exits, altars with 1-2 tribute tiles).
    - topo-odd-spawn: spawn rectangles of 9-16 tiles in cramped surrounds.
    - topo-duel: spawns 0-4 apart.
    - topo-gatehouse: the only route runs through or beside each spawn.
    - topo-capital: central spawns, economy in the corners.
  - **scenarios** (~12%, [scenarios.mjs](mapgen/scenarios.mjs)): vision, mobility and economy layouts:
    - hole-maze: sight and walking disagree.
    - dash-lattice, wall-lattice: dash-only and crystal-only crossings everywhere.
    - leaky-diagonals: corner-cutting.
    - fog-field: one giant bush cluster.
    - shrouded-altars, moated-altars: altars hidden in bush or behind dash or crystal moats.
    - mega-groups: groups of 20-50 cells.
    - altar-clusters: adjacent altars, camps beside them.
    - fuel-stress: ~100x100 with ~240 stored camps.
    - gold-centre, turtle: gold only in the middle; richest at home.
    - far-altars: long carries.
    - cluster-carpets: groups of 15-30 clusters.
- **Constraints** follow the ladder, not mapgen's old habits. Every preset samples, at about the ladder's rates:
  - groups touching diagonally (`group_gap` 0);
  - camps beside altars (`camp_altar_gap` 0);
  - camps reaching a spawn's edge (`spawn_reach_gap`; from calibration 2 also `home_camp`);
  - a partly walled spawn surround (`spawn_clear`);
  - 4x3, 5x2 and (calibration 2) 8x2 spawns (`spawn_dims`);
  - composed groups (`poly`, `snake`, `ring`, `carpet`, `pack`; calibration 2's `ladder_group` 'big:' make-ups).

  Any spawn rectangle of 9-16 tiles loads, and sides from 28 (the ladder's 04pinwheel and 04plaza; `validate` took 30 up before calibration 2). Camps are never placed on bush; no ladder map but two (quarry, harvest, one pair each) has one there.
- **Extension modules** (topology.mjs, scenarios.mjs, paradigms.mjs) export `PRESETS`, `DESIGNS`, `CAMP_MODES` and `TEMPLATES`, which generate.mjs merges (a duplicate name throws); paradigms.mjs also adds terrains (`TERRAIN`) and `POST_SPAWN` structures, which a spec's `post_spawn` draws after the spawn is placed. A module's presets are its family. A module may import generate.mjs but use it only inside functions, and nothing may import a module before generate.mjs.
- **Quirk metrics** (in `metrics`, and in the diversity space):
  - `walk_split`: the spawns are not walk-connected;
  - `dash_gain`, `tele_gain`: walk over dash or crystal travel between the spawns, capped at 10;
  - `narrow`: the share of 1-wide corridor tiles;
  - `leaky`: diagonal leaks per 1000 tiles;
  - `spawn_ring`: the blocked share of the spawn's surround;
  - `max_group`, `diag_groups`: the largest group, and diagonal contacts between groups;
  - `camp_altar`, `altar_gap`, `altar_slots`: the nearest camp to an altar, the nearest altar pair, and the fewest walkable tiles beside an altar;
  - `sight_gap`: of tiles 2-3 away on a clear line, the share 5+ steps longer on foot.
- **Access.** Objectives may need a dash (2 king steps over holes) or a teleport crystal (range 3, any terrain) when the map says so (`g.access`).
  - When any does, each team reaches on foot a gold-paying camp it can take early, so it can always buy a crystal.
  - `metrics.access`, `dash_gems` and `tele_gems` record what a map needs; about 13% of a suite needs more than walking.
  - Camp-plugged routes (kill to pass, like boss-battle) are `gated` in the index.
- **Speed** (2026-10-29, 96 cores): a suite takes ~2 s (120 s before), ten ~9 s, and maps are byte-identical to the serial generator's. Candidates are made in child processes, slowest presets first; a designed map whose reach on foot is already under `min_reach` after its design step fails at once (atoll and archipelago failed most attempts there).
- `maps/gen-bench/` holds the 14 generated maps of the fuel bench's wide set, kept from the older suites so fuel results stay comparable. No A/B suite reads it.
- [mapgen.mjs](mapgen/mapgen.mjs) builds maps through the engine WASM's map builder, seeded. Presets, placement, validation and metrics are in [generate.mjs](mapgen/generate.mjs), playable-area shapes in [shapes.mjs](mapgen/shapes.mjs), designers, brushes and cover prefabs in [design.mjs](mapgen/design.mjs), the tile grid in `grid.mjs` and the engine WASM loader in `wasm.mjs`.

- **How close the mixes are, and whether it matters** (measured 2026-11-05 and 11-12):
  - Ranked play draws the pool's maps uniformly: on cambc 5.0.0 all 128 maps were played 3 to 22 times each, a spread matching uniform draws, and after the 05 maps went live they took 24.7% of 113,965 ranked games, their share of the 170-map pool. Top teams play the same mix. So the unweighted map set is the right reference.
  - Before calibration 2, sizes, symmetry, gem and gold totals, groups per side and spawn distance already matched, but camp group make-up, altar count, parity and position, picks, spawn size and winding terrain did not, even in the ladder-like presets (47% of them had 6 or more altars, against 8% of the ladder). Only mutated ladder maps matched. Calibrations 2-4 fit those.
  - The generator still can't make some ladder features outside mutations: sides of 28-29, two or more self-mirrored altars, an 8x2 spawn. The stress families (`varied`, `fixed`) deliberately make maps the ladder never has: unconnected spawns, maps mostly blocked, walls over a quarter of the map. That is why they are for robustness, not for judging a change.
  - Switching mixes doesn't change verdicts. Charybdis and ocean bots on fresh `ladder-v2`, `ladder-v3` and `ladder-v4` maps (10,240 maps each, against Fish and Mite) moved under 0.5 points between mixes, and their order and gaps held (charybdis over ocean +8.2, +8.1, +8.4). The 05-style quarter is 2-3 points easier for charybdis and under 1 for ocean, as on the real 05 maps. Close-spawn maps run about a point lower for every bot and open frames about a point higher, so the mix cancels in a paired gate. A newer mix is a closer target, not a different answer.

```
node tools/mapgen/mapgen.mjs list                                  # presets
node tools/mapgen/mapgen.mjs gen donut --seed 3 [--set altar_mode=central] --out x.map26a --show   # north at the top
node tools/mapgen/mapgen.mjs gen atoll --seed 2 --show             # a designed scenario
node tools/mapgen/mapgen.mjs mutate expanse --op "walls*0.5" --op "camps*1.3" --out x.map26a   # mirror-preserving edits
node tools/mapgen/mapgen.mjs mutate random --seed 7 --show          # a seeded ladder map under seeded edits
node tools/mapgen/mapgen.mjs check maps maps/suites/legacy/gen                   # validity, reachability, metrics
node tools/mapgen/mapgen.mjs diversity maps/suites/legacy/gen DIR                # map sets against the ladder maps
node tools/mapgen/mapgen.mjs suite --out DIR --seed S             # a fresh ladder-like suite (--mix ladder); without --out it rebuilds the legacy gen, and refuses another --seed or --mix
node tools/mapgen/mapgen.mjs suite --out DIR --seed S --mix ladder-v2   # calibration 3's: nearer the ladder, preferred for new programmes
node tools/mapgen/mapgen.mjs suite --out DIR --seed S --mix ladder-v3   # ladder-v2 plus the 05 maps' style at their share of ranked play (340 maps)
node tools/mapgen/mapgen.mjs suite --out DIR --seed S --mix ladder-v4   # ladder-v3 plus the full-pool layer: open frames, arenas, close spawns (340 maps)
node tools/mapgen/mapgen.mjs suite --out DIR --seed S --mix paradigms   # 12 layouts the ladder mixes lack, ladder economy
node tools/mapgen/mapgen.mjs suite --seed 3001-3004,3010 --out maps/suites/fresh/fresh-{seed}   # several fresh suites, sharing --jobs (48) processes
node tools/mapgen/mapgen.mjs suite --seed 6003 --mix varied --out DIR   # the stress-heavy plan, reweighed per seed (fixed: the plan's counts)
node tools/mapgen/mapgen.mjs suite --seed 150003 --mix varied-v1 --out DIR   # a suite as made before 2026-11-05
node tools/mapgen/mapgen.mjs gen classic --seed 3 --calib 1        # calibration 1's map
```

## Map fuzzing: tools/fuzz

`py tools/fuzz/fuzz.py run NAME [--screen 400] [--ref astraeus] [--climb 8 --gens 4] [--shrink 2]` hunts for maps on which astraeus farms pathologically against bots/idle.
- **Maps:** every preset in `mapgen list` plus `mutate random`, each played from both sides through run_batched.py.
- **Score,** from the extracted replays (higher is worse):
  - gem rate against the typical rate for the map's offer;
  - never reaching 1000;
  - gems hoarded, never tributed;
  - side asymmetry;
  - own groups never captured;
  - stalls;
  - deaths to camps;
  - out-of-fuel turns and errors;
  - with `--ref`, a reference bot's rate on the same map.
- **Search:** hill-climbs the worst maps with single `mapgen mutate` ops.
- **Output** in `replays/fuzz/NAME/`:
  - `report.md`: the worst maps, each with a description; failures by preset; the edits kept; the edit types that made maps worse;
  - `worst/*.map26a`, for `cambc run --map`;
  - `maps.jsonl`.
- **Other commands:** `rescore` re-scores a run without replaying; `vs NAME BOT` plays the worst maps head-to-head.
- Details in [fuzz/README.md](fuzz/README.md); the metrics and score are `score.py`'s. A 600-map screen plus a 5-generation climb takes ~12 min on 80 slots and ~1.2 GB.

## Forced drafts: tools/variants

The draft is compiled in, so a forced draft is a bot copy in `bots/variants/<name>/` (gitignored); the source defaults to ocean. In astraeus and ocean the copy's `draft_order()` returns the forced draft, past their map model, tables, Vesper Vale gate, team lock and `test_draft`; the map model still measures the map, so play is otherwise the source's. In older bots, which only have `draft_preference`, `test_draft` on ignores the forced draft.

```
py tools/variants/make_variant.py varg,willow,ryth                        # drafts under 5 are padded (-pad)
py tools/variants/matrix.py varg,tavi,ryth,stellar,ren willow,ren --one-side   # [BOT@]DRAFT specs; BOT@ = its own draft
py tools/variants/matrix.py --focus --cols astraeus@                      # each champion first, + --filler
py tools/variants/matrix.py --resume replays/matrix-TIMESTAMP             # --report: rewrite reports only
```

[draft_search.py](variants/draft_search.py) is a library for astraeus's per-pick-count drafts (`params::draft_three/four/five`) against proxies of the top-10 teams (the source bot, `DS_SRC`, playing each team's main drafts), with paired results cached in `DS_DB` (default `replays/ds/db.jsonl`) and keyed by a hash of the source bot and the maps, so a changed bot never reuses old games.

[ds_run.py](variants/ds_run.py) drives it in stages (`run`/`report`/`combo`/`vehicle`: screen, rest of pool, `--fresh DIR`, a vehicle for an `ab.py` head-to-head on `draft_search.suite_dir(P, ...)`); `--picks 3,4` shares vehicles across pick counts.

matrix.py plays one batch per distinct pair (`--bot` rows, `--vs-bot` columns; identical entries are mirrors, reported as team A's win rate) and writes `replays/matrix-TIMESTAMP/`.

## Fuel: tools/fuel

```
py tools/fuel/bench.py run astraeus --out replays/fuel/base.json          # 16 games vs astraeus, 8 maps, 100M fuel
py tools/fuel/bench.py compare replays/fuel/base.json replays/fuel/x.json  # identical replays, fuel change
py tools/fuel/stats.py BASE.json CAND.json [...]                          # headline numbers side by side: mean, p99, max, >100k, round 1, OOF, shortcuts
py tools/fuel/bench.py run astraeus --fuel 0 --out replays/fuel/real.json # the real budget: shortcuts and lost turns
py tools/fuel/bench.py run astraeus --set wide --test-draft --per-map --jobs 94 --out replays/fuel/x.json  # 52 games, ~2 s on alext
py tools/fuel/bench.py run astraeus --stock --out replays/fuel/base.json  # on stock cambc, a `cambc run` a game
py tools/fuel/oof.py replays/batch-A replays/batch-B                      # out-of-fuel turns per bot, broken draft handoffs and capped drafts (thinned replays from pruned-stdout.jsonl)
py tools/fuel/oof_bot.py replays/batch-A replays/batch-B                  # the same without shared-gem maps, by round, finish gap, run size
py tools/fuel/census/batch_oof.py --bot 1 replays/batch-A                 # one bot's: first-in-streak, by round, phase, branch, map
py tools/replay/debug_lines.py SRCH-PASS -- replays/batch-A               # any debug_block line prefix per bot (--show N)
py tools/fuel/cap_variant.py astraeus --run-fuel 10000000                 # a copy that charges itself back to 100k a turn
py tools/ab.py astraeus variants/astraeus-cap100000-at10000000 --no-test-draft --fuel 10000000 # so only CAND gets 10M
```

- **bench.py:** plays on the fast runner when it is built (`CAMBC_BIN` if it names one, else `tools/fastengine/runner/fastrunner` here or in the primary checkout; `FASTRUNNER_MODE` defaults to native): all games in one `run-batch` taking a CPU slot per game, each game's draft and winner from its `.camstat`. Its JSONs and bundles equal stock's (2026-11-03, astraeus vs astraeus-fc4b: oof and `--set wide --test-draft`, 100M and `--fuel 0`, 200 games; every bundle member but `.debug` identical) at a quarter of the CPU (~2.5x wall). `--stock`, or `CAMBC_BIN` naming another cambc, plays a `cambc run` per game; games failing on the fast runner are replayed that way. Bots build in place (paths unchanged, so bundles compare with older JSONs) under a lock per bot directory, so concurrent benches sharing a bot (astraeus, the default `--opp`) never build it at once; a bot edited while a bench plays it is not protected. `compare` warns when the two JSONs differ in `fuel` or `test_draft`. A built fast runner that does not answer (a cambc it was not ported to) stops it with an error instead of a silent stock run (`--stock` or `FASTRUNNER_ALLOW_STOCK=1` plays stock). `--maps` takes ladder names or paths; `--set wide` is 26 maps (12 ladder, the 14 in `maps/gen-bench/`); `--test-draft` gives both bots the ladder test compositions; `all` counts play turns from round 2. Fuel campaigns keep their sets and baselines in `replays/fuel/fc<N>/` (`bench.sh`, `ab.sh`, `<set>set.txt`, `base-<set>-{100M,real}.json`; brief and findings in `research/hyperion/fuel-campaign-<N>/`).
- The 16-game bench swings by ±20 out-of-fuel turns and has no shared-gem map: judge out-of-fuel turns on a full A/B.
- astraeus and hyperion print `SHORTCUT round champion what` where fuel made it choose worse and `OOF round phase` for each turn that ran out (both in `debug_block`). `debug_fuel` in util.h gives per-phase costs (`FuelMeter`, ~170 a meter). Where the fuel goes: [EXPERIMENTS Fuel](../research/EXPERIMENTS.md#fuel).
- Since CHANGES 217 (late finish) a turn after one that ran out finishes even if it runs out too, and its `OOF round phase` line names the last phase reached, not where fuel ran out (often `queue`). The census records the true stack.
- **Fuel census** (`tools/fuel/census/`): per-component fuel of every heavy or out-of-fuel turn, and the scopes open when fuel ran out. Instrument a debug copy (never a real bot; `instrument.py` fails loudly once the bot's code has moved, so update its patterns), play it at the real budget, then tabulate OOF-first, OOF-late and heavy finished turns by component, branch, champion type and stack:

  ```
  mkdir -p bots/variants/astraeus-cen && cp -r bots/astraeus/src bots/variants/astraeus-cen/  # no .cambc/
  cp tools/fuel/census/census.h bots/variants/astraeus-cen/src/ && py tools/fuel/census/instrument.py bots/variants/astraeus-cen/src --fine
  py tools/fuel/bench.py run variants/astraeus-cen --fuel 0 --maps $(cat tools/fuel/census/maps.txt) --games replays/fuel/cen --out replays/fuel/cen.json
  py tools/fuel/census/census.py replays/fuel/cen
  ```

  `maps.txt` is 28 maps heavy in out-of-fuel turns (2026-10-29).
  With `instrument.py --trace`, `py tools/fuel/census/trace.py replays/fuel/cen [--site farm.cc:1271]` gives, for each turn that ran out, the last fuel check it passed, what that check needed and the work after it. `py tools/fuel/census/tail.py replays/fuel/cen [A B]` tabulates the same by site (with the work veto's asks after it, given model/pathing.cc's two fuel() lines around `veto_fn_` in the copy), finished turns' spend after decide's last check (CLC) and after the farm loop's (CLF), and the components of OOF turns that passed no check at all.
  `py tools/fuel/census/gates.py replays/fuel/cen` (needs `--trace`): per fuel gate, the fuel left when it fires, how often its turn still ran out, the fuel left after decide, gate order within a turn, and the first gate of turns that ran out.
  `py tools/fuel/census/budget.py DIR [BASEDIR]`: the budget table. `census.h` prints each label's inclusive fuel on every turn as `CHIST` 1k-bucket histograms every 100 rounds (labels in `hist_wanted`, plus `@turn`).
  For each label, budget.py prints the share of turns it ran, p50/p90/p99/p99.9, max and mean; with BASEDIR it prints both side by side.
  The `@slack.*` rows are the fuel left at decide's end on turns a gate cut and that still finished, by the gate's file.
- **Fight-simulation profile** (`tools/fuel/simprof/`): `patch_prof.py` instruments a copy (like the census), `an.py DIR` lists every `simulate()` of turns whose sims cost 8k+, by caller (`rep.py`, `sides.py`: summaries of the same).
- **Per-site fuel profile** (`tools/fuel/fuelprof/`): exact wasmtime fuel by charge site from a patched copy of the native fastrunner (`setup.sh`; the main runner is untouched), symbolised by source line through a `-g` build (`symbolise.py`, `query.py`; `wbodies.py` reads the wasm's function bodies). It also writes the profile of turns that finished on 88k+ and of out-of-fuel episodes (`DIR/heavy`, `DIR/oof`). See setup.sh for use.
- **Fuel by wasm function** without a patched runner: `py tools/fuel/siteprof.py WASM TRACE... [--vs WASM2 TRACE2...]` reads the stock fastrunner's `FASTRUNNER_TRACE_SITES=1 FASTRUNNER_TRACE_FUEL=FILE` traces (native mode): the fuel between host calls, charged to the calling function (not inclusive).
- `py tools/fuel/census/trace_scope.py DIR SCOPE`: per map, the fuel from entering a census scope to the next traced event, on traced out-of-fuel turns.
- cap_variant.py: keep `--run-fuel` at or below 30M (at 100M instances trap near round 1000, `probe-fueladjust`); a turn that ran out resumes uncapped.

Host prices (50x50, 2026-10-19):

| Call | Fuel |
|---|---|
| `is_set` or field get | ~27 |
| set | ~16 |
| whole-board op (clear, union, intersect, not, shift, count) | ~1 per 8x8 chunk + 13 |
| `draw_chebyshev` | ~22 |
| `reachable_tiles` r1-r4 | 70-95 |
| `shadow_cast` r1 / r4 / r8 | 125 / 173 / 270 |
| `positions_into` for 49 tiles | ~180 |
| capped field r2 / r8 | ~900 / 1200 |
| full field | ~2.5k |
| new bitboard | ~260 |

Raw imports without the SDK's check() (2026-10-27): `sdk_Bitboard_Test` ~16 (off the map it fails, ~20), champion
info 12, alive 8, cooldown 9, gems 8, items 8, buff data 15-19, awake/asleep camp board 57. Our own code costs ~2-3
fuel an instruction: reading a board's storage directly is ~30 a tile (~54 with a bounds check), so a host call wins
even per tile. A FuelMeter is ~170; time small parts with raw `sdk_fuel_remaining()` differences.

## Ladder replays and scrims

```
py tools/fetch_replays.py --list                      # ladder: rank, rating, record, team id, name
py tools/fetch_replays.py --top 10 --team "Mite"      # newest 20 ranked groups per team
py tools/fetch_replays.py --mine                      # our groups into replays/mine/
py tools/bulk_replays.py                              # unpack replay-bulk-zip/ into replay-bulk/<day>/
py tools/scrim_ladder.py --dry-run                    # top 5 teams x 3 groups: maps and commands, nothing queued
py tools/scrim_ladder.py --teams 5 --sets 3 --seed 7  # asks before queuing (--yes skips)
py tools/scrim_ladder.py --teams 10 --sets 7x5,3x5    # 7 groups each for the top 5, 3 each for the next 5
py tools/scrim_ladder.py --sides alt --avoid replays/scrims/TIMESTAMP --wait-quota   # both sides, new maps, queue as quota frees
py tools/scrim_ladder.py --resume replays/scrims/TIMESTAMP
py tools/version_record.py 50                        # our version 50's record per opponent: kind, pick count, side
```

- **fetch_replays.py** needs `cambc login` and `--threads 1` (downloads rate-limit). Options: `--kind ranked|unranked|all`, `--since`, `--max-groups N`, `--out` (`replays/ladder/`), `--no-replays` (only `group.json`: no login, any threads). Each group gets `<time>-<teamA>-vs-<teamB>-<id>/` with `<n>-<map>.repl26a` and `group.json`, which holds every game's map, result and both drafts. `--top N` reads as many ladder pages (25 teams each) as it needs.
- **bulk_replays.py** keeps ranked games between two of the day's top 15 teams and deletes each zip once extracted.
- **scrim_ladder.py spends the team's unranked quota** (`cambc match-groups quota`; each group frees about an hour after it was queued): dry-run first. We are side A unless `--sides alt`; `--avoid` takes earlier run folders, so repeated maps go to the side not yet played. Replays go to `replays/scrims/<timestamp>/`.
- **ladder_scrims.py** is the long-running scrim job behind `research/notes/ladder-scrims-2026-11-06/` (README, SET.md):
  `plan --version N --sets core,ext --opps fish,mite` appends five-game tasks of the frozen set (`--maps a,b,c,d,e`
  an ad-hoc map list instead, `--groups K` a cap), `run` (setsid nohup) creates every pending task of the live
  version back to back as far as the rolling 100-groups-an-hour quota allows (keeping `--reserve` free;
  the runner default and `live_restart_runner.sh` reserve zero: use spare capacity, yielding priority when a teammate requests a burst) and the rest as quota frees up, pins each opponent to its
  first group's bot (`--source-group`, usable once that group has played), and downloads every game's bundle and summary;
  `status`, `report --by side,map` and `pair OLD NEW` (paired flips between our versions) read the jsonl data.
  During a live batch the runner checks activation every `--pace` seconds. If queued work remains and quota will
  return within three minutes, the scheduler keeps the candidate active to avoid two unnecessary activations;
  longer quota gaps and fully submitted campaigns restore the latest book. A campaign's `refill_grace`
  may extend that wait in seconds when finishing its live test takes priority; a fully submitted campaign
  still restores the book immediately.
  A scheduler campaign can supply `parts` as `[set, part, priority]` triples to cover a custom map set
  continuously, and `baseline_version` to compare with a completed candidate instead of the legacy control.
  `set-full170.json` covers all 170 ladder maps in five-map chunks, interleaving both opponents and both sides.
  Scheduler `parked_task_ids` remain held across control changes, preserving unfinished lower-priority tests.
  Campaign completion counts only its generated task IDs (or explicit cell-task IDs), so parked tests of the
  same bot on older opponent pins do not block a new-pin campaign.
  - **Outcome-only baselines:** `data/OUTCOME-ONLY-VERSIONS.json` optionally lists versions whose pinned `set`
    games need only outcomes and drafts from group detail. These rows explicitly say `collection: outcome_only`
    and have no replay/summary metrics. Use only for book-free host-loss selection; other versions and all
    opponent checks still download full evidence. Remove the version to restore full collection for future games.
  - **Winning book sources:** `data/WINS-ONLY-TASKS.json` optionally lists exact task IDs whose pinned `set`
    games need full downloads only for possible winning sources. Explicit losses retain outcomes, drafts and
    provenance, with `collection: loss_outcome_only`; their replay/summary downloads are skipped (an already cached
    replay remains linked). Wins and unknown results still download both files. The live version must match the
    task; other tasks and opponent checks remain unchanged. Use only for source-mining tasks, never strength tests
    or replay comparisons. The file is read per collected group; removing an ID restores future full collection,
    but does not backfill previously skipped files. Prefer this task policy over an outcome-only version rule for
    source versions: an existing outcome-only version rule still takes precedence and suppresses winning downloads.
  - **API pacing:** no local token bucket, minimum call gap, or reserved API tokens. The CLI wrapper
    retries server `retry after N seconds` responses with bounded exponential backoff. The platform's rolling
    scrim quota still controls group creation. Source tasks may skip losing replay downloads as above.
    Activation, submission checks and creation take priority over background API calls using shared,
    renewable 90-second leases; crashed owners release priority immediately, and stopped owners expire.
    A read-only 429 before any unconfirmed creates releases the switch lock before backing off, so activation
    can proceed. Confirmation after creates retains the lock and the existing suspect-group protection.
    A successful advisory quota read survives a deferred version check; the live version is always checked
    again under the switch lock. A definite server quota refusal ends the create pass promptly.
  - **Latest book as REST:** `research/notes/ideas-2026-11-13/rbook/loss_live.py upload` uses the tracked
    `live_test.sh --rest` helper after local verification. The uploaded book becomes REST immediately while
    its live checks continue; ranked activation is not evidence that qualification passed. Ordinary strength
    test uploads keep the existing REST. The coordinator serializes use of `~/tmp-offload/rbook-mask/prepared.json`.
  - **To test a version at full rate:** write its number to `sched/REST` (the scheduler activates it between
    candidates and plans its gate on `refsets.json`), or with the scheduler stopped activate it and `plan` its tasks.
- **live_sched.py** is the unattended live-gate scheduler (one at a time: `setsid nohup py tools/live_sched.py >> ~/tmp-offload/handoff/sched/sched.out 2>&1 < /dev/null &`).
  While the live version's gate plays, it builds and smoke-tests the next candidate (the newest `oc-baseNN` ocean
  commit, else the top `~/tmp-offload/live-queue.txt` line) with `livemask/stream_patch.py`; once the gate's groups
  finish it submits, activates and plans the candidate's core and ext sets. The `v87-null-a` queue arm alone uses
  historical Fish r2/Mite r3 to pair with v98; the existing r3 source is validated before upload, with no fallback
  or repin. Other arms use the global defaults. Null-a measures the combined burn plus current-mask reroll,
  not isolated burn with an identical mask. Each live version also compares current opponents with separate
  rolling observation snapshots (see `ladder_opp_check.py` below), logging changes without repinning. It pauses when a version we did not submit
  is live or selected, and restarts a dead runner with `live_restart_runner.sh`. Its state dir (`LIVE_SCHED_DIR`,
  default `~/tmp-offload/handoff/sched`) holds `state.json`, `sched.log`, `gates.jsonl`, `refsets.json` (the ref set
  per opponent new gates use; read each loop), `build/`, and the `STOP` / `PAUSE` / `HOLD` files.
- **live_r6_campaign.py** handles only the explicitly authorized existing-v113 Mite-r6 bridge followed by the
  prepared whole-506 Fish-r2/Mite-r6 gate. Ops installs a hash-bound `r6-campaign.json` after v114 drains and the
  authorized reference transaction. It selects existing113 without uploading, tracks its52 new Mite groups
  separately from historical113 completion, verifies prepared source/SDK/WASM/mask/smoke provenance, then uploads
  that artifact without a build fallback. Upload intent is persisted before the call; an ambiguous interrupted
  upload holds for reconciliation instead of uploading twice. Wrong pins, outside selections, dropped/suspect
  groups or missing collected replays hold; read-only API rate limits wait. It never repins or extends itself.
- **live_opponent_campaign.py**, **live_panel_evidence.py** and **live_panel_observations.py** implement the
  explicitly reviewed conditional113/whole506 fourteen-opponent panel. They are inert without `live-panel.json`
  or before the r6 campaign completes. The complete primary Fish/Mite paired-map results determine entry;
  existing own submissions are reselected, each new opponent's first validated capture is frozen for both arms,
  and reports remain separate by opponent without conditioning on draft choices. Sparse same-own-version hourly
  observations update detector snapshots only. See `research/notes/ideas-2026-11-11/live-opponent-panel.md` for fixed
  scope, quota estimate, recovery barriers and the prospective closeness rule.
- **version_record.py** needs the website cookie (`%APPDATA%/cambc/web-cookie.txt`, as fetch_replays.py): the API shows submission versions only with it. `--kind`, `--json FILE` for per-game rows.

## Draft lab: tools/draftlab

Self-play with per-map forced drafts (vehicles with a generated table), then a model of champion value by map
features, pick count, synergy and counters; Thompson sampling picks later batches' drafts. Details in
[draftlab/README.md](draftlab/README.md).

```
py tools/draftlab/lab.py init --lab night1          # freeze HEAD's astraeus, map features, top-20 ladder prior
py tools/draftlab/lab.py run --lab night1 --hours 8  # resumable; games.jsonl, model.json, report.md
py tools/draftlab/lab.py status --lab night1
node tools/draftlab/model.mjs cpp --lab replays/draftlab/night1    # astraeus's src/draft_model.h from the fit
node tools/draftlab/native.mjs --lab replays/draftlab/night1 maps  # C++ features and team against the JS, no games
py tools/draftlab/parity.py --lab replays/draftlab/night1 maps     # the same in-game: one round per map
```

astraeus, ocean and charybdis draft from lab models (README's deployment section). `init` freezes astraeus unless
the lab's `config.json` names a `source` bot (draft18's is `bots/variants/charybdis-5564637`).
`py tools/draftlab/ladder_prior.py --out LAB/prior.json ...` builds a prior from the per-day ladder archive;
`py tools/draftlab/test_comps.py --prior LAB/prior.json --bot bots/BOT` rewrites a bot's `test_draft` compositions
from one.
Pieces other tools reuse: `vehicle.py` (bot copies with a per-map draft table, `freeze(sha)`), `features.mjs` (map
features and the trainer's map key, bit for bit; `derived.mjs` its squared and product features), `outcome.mjs` (each game's gems at checkpoints and champion
statistics, without a full extraction), `firstturn.py` (the model draft's first-turn fuel; `--need`: the whole first turn at unlimited fuel, the headroom report).

## Emblem lab: tools/emblab

Which emblems (and with them which drafts) win, from games whose drafts and emblem choices are randomised (ocean
from round 4, against itself and the Fish and Mite bodies); it reuses the draft lab's vehicles and outcomes. How it
works and what each round found in [emblab/README.md](emblab/README.md); the step-by-step for a run, with round 4's
pitfalls, in [emblab/RUNBOOK.md](emblab/RUNBOOK.md).

```
py tools/emblab/lab.py init --lab NAME [--source REF]        # freeze REF's bot (config "bot", default ocean), the map table, the prior
py tools/emblab/lab.py run --lab NAME --games 80000 --hours 3   # resumable; `touch <lab>/stop` ends it; status: lab.py status --lab NAME
py tools/emblab/edits.py build --base bots/variants/BOT --out LAB/edits.json [--r4] [--structural]   # round 5: the edit library (table / list: a candidate bot, the registry)
py tools/emblab/elab.py init|drafts|run|status|check --lab LAB   # round 5, the edit lab: whole-policy edits per team-game, release vehicles
py tools/emblab/efit.py fit --lab LAB [--gate] [--by opp]     # its estimates (Bradley-Terry over edits); `step`: the screen's allocation
py tools/emblab/slot_keeper.py job-<lab.py pid> 35 <pid>      # repairs a legacy process whose slot membership was lost before the atomic-publication fix
node tools/emblab/dfit.mjs --labs r4,r4b [--dr | --mapdr] [--fitall]   # per-decision fit, DR / map-keyed selections; streams decisions/*.zst
py tools/emblab/with_slots.py 64 node tools/emblab/dfit.mjs ... --threads '{slots}'   # the fit on CPU slots taken from the pool
py tools/emblab/select.py MODEL.json [--maps] [--on LATER.json]   # selection rules on the fit's dumped sums; --on: replication on later games
py tools/emblab/candidate.py SEL.json --key RULE --buy --source BOT --out bots/variants/NAME   # a candidate bot (--buy: arms at the purchase only)
node tools/emblab/fit.mjs --labs main,pilot [--boot 20]       # round 1: whole-game fit; policy.py writes emblem_table.h
node tools/emblab/ladder_emblems.mjs [replays/ladder]         # top teams' emblem orders
py tools/emblab/pilot.py --lab pilot                          # log checks and effect sizes before a main run
```

Modules behind these: `evehicle.py` (the lab's vehicles), `structural.py` and `typed_r4.py` (round 5's structural
and typed edits, for `edits.py build`), `mapdr.mjs` (map-keyed policies for `dfit.mjs --mapdr`).

## Constant tuning: tools/tune

SPSA on a bot's params.h constants against a panel of opponents, scored by win, tributed gems and gold. Candidates
are the base build with one data block patched (in the wasm and the fast runner's cached native code), so they cost
no compile; an iteration is one fast-runner batch, pipelined with scoring (~300 games/s on alext alone). Details in
[tune/README.md](tune/README.md).

```
python3 tools/tune/tunify.py bots/BOT              # once: constants -> a patchable block
python3 tools/tune/tune.py init --run R --bot bots/BOT --opps variants/a,baselines/v94
python3 tools/tune/tune.py run --run R --hours 6                  # resumable; replays/tune/R/
python3 tools/tune/tune.py status --run R
python3 tools/tune/tune.py apply --run R --out bots/variants/NAME # a bot with the run's current constants
$PY tools/tune/league.py init --run L --from-tune R               # exploiters hunting R's constants ($PY: a python with optuna)
$PY tools/tune/league.py run --run L --hours 0.25
```

- **league.py** (AlphaStar-style): the main agent keeps taking SPSA steps against outside opponents and frozen
  exploiters (PFSP); optuna TPE exploiters search the constants' whole ranges for sets that beat the main, and one
  passing `freeze_at` on a `confirm_maps` replay joins the league. To test fixed constants, set `a` to 0 and
  `main_maps` to 0 in its `config.json`; seed the search with `study.enqueue_trial` (EXPERIMENTS "Exploiter search").
  optuna is not in the repo's venv (`~/venv-tune` on the EC2 box).
- **After a fast-runner rebuild** (new native cache keys) a run whose base bot has not yet played under the new
  runner patches only the old key's library and compiles every candidate (~15 s each): restart it once the base has
  played a game.

## Draft win-rate model: tools/winrate

```
py tools/winrate/fetch.py [--since 2026-10-22] [--threads 8]                                    # every ranked game: replays/winrate/games.jsonl
py tools/fetch_replays.py --top 30 --since 2026-10-22 --max-groups 0 --no-replays --threads 8   # or the top 30's groups, as folders
node tools/winrate/winrate.mjs fit --games replays/winrate/games.jsonl [--focus-dirs replays/ladder] [--since 2026-10-22] [--min-rating R] [--bootstrap 200]
node tools/winrate/winrate.mjs fit [--dirs replays/ladder]                                       # from group.json folders instead
node tools/winrate/winrate.mjs predict --map 00pilgrimage                                      # champions by value there
node tools/winrate/winrate.mjs predict --map 00pilgrimage --a prism,vesper_vale,marcella,willow,heart_of_ruin --b ... [--elo-a R --elo-b R] [--draft-only]
```

- **Model:** P(A wins) = sigmoid(S_A - S_B + e (Elo_A - Elo_B) ln10/400), Elo being each side's `ratingBefore`. A team's S sums, over its picks, the champion's intercept plus its weights on the map's features: area, altar tiles, camp groups, mean group power (sqrt(hp x Strength)), gold and gems per respawn round summed and averaged over groups, bush share of all tiles, and the spawn-to-spawn walk (mapgen's `spawn_dist`). Champion terms are relative to the average champion (both teams pick the same number).
- **Data:** fetch.py lists groups ladder-wide (~45 groups/s, about 460 bytes a game; 2026-10-22 on is ~160k groups) and resumes: a rerun adds only new groups. `--focus-dirs` adds a table comparing, on those groups' games, a fit on all the data against one on those games alone.
- **Fit:** L2-penalised Newton; penalties by leave-one-map-out log loss. `report.md` compares it with Elo-only, intercepts-only and draft-only (no Elo) fits, gives bootstrap intervals over groups and ranks the champions on every map in `maps/`; `model.json` has standardised and raw-unit coefficients and every map's features.

## Replay analysis: tools/replay

```
node tools/replay/extract.mjs replays/ladder replays/batch-TIMESTAMP   # decode into replays/.analysis/
node tools/replay/extract.mjs --update-engine                          # after a cambc update
node tools/replay/drafts.mjs LISTFILE                                  # each replay's draft only, ~250 games/s a process
py tools/replay/analyze.py replays/batch-TIMESTAMP --vs replays/ladder --team hyperion   # --reports economy,camps
py tools/replay/ab_compare.py <variant name> batch-A batch-B           # both bots of an A/B in the same games
py tools/replay/narrate.py replay-bulk/2026-10-24                      # turn-level timelines, fight transcripts, episode files
py tools/replay/stalls.py <ab name or batch> --min 300 [--bot 1]       # champions on one tile, alive and off spawn, 300+ rounds
node --test tools/replay/test_map.mjs                                # canonical/runtime camp mapping, self-mirrored camps and group identities
py tools/replay/macro_stats.py replays/.analysis [--bot NAME] [--json OUT]   # time budget, camp clears and captures, winners vs losers
py tools/replay/macro_card.py GAME [--analysis DIR]                     # one game's macro, both teams side by side
py tools/replay/analyze.py batch-X --reports losses --team NAME       # loss episodes (deaths, camp deaths, camps lost, stalls) priced in gems, clustered, ranked against the opponent, with code areas
py tools/replay/triage.py GAME --team NAME [--top 10]                 # one game's turning points: costliest episodes, what the champion did, the rule-checked alternative, where to look
py tools/replay/abdiff.py --a BATCH-A --a-team CAND --b BATCH-B --b-team REF   # two batches on the same maps and opponent: behaviour and episode changes, and which go with flipped results
py tools/replay/turn_budget.py batch-A batch-B [--by-bot]               # after extract.mjs: each turn's class and what it earns (reads the `D` trace lines of non-release builds)
py tools/replay/walk_audit.py batch-X [--team NAME]                     # why champions walk: legs, detours, crews, recall cycles (solo games)
py tools/replay/hold_metrics.py EXTRACT_DIR [...]                      # per bot: captures, hold resets by cause (walked off alive), pressured holds, deaths, A-B-A flips
py tools/replay/fight_metrics.py EXTRACT_DIR [...]                     # per bot: deaths and kills a game, deaths to champions/camps, kill share at equal numbers, captures, captured and tributed gems
py tools/replay/audit_beliefs.py batch-X                               # a bot's world beliefs (debug_beliefs "BD" lines) against replay truth
py tools/replay/fight_calibration.py batch-X                           # fight-model predictions (debug_fights) against outcomes
py tools/replay/osc_detect.py DIR... [--bot astraeus-trace] [--out replays/osc]  # ping-pong, stuck, branch/claim/prey flips per champion, from bots/variants/astraeus-trace's per-turn D lines
#   --bridge-oof: an out-of-fuel turn prints no D line; don't split the run there (compare bots with it on). Trace hooks for current astraeus: research/hyperion/fuel-campaign-6/trace.patch
py tools/replay/osc_compare.py REF_OUT CAND_OUT...  # osc_detect outputs: episode turns by kind, OOF turns, paired bootstrap CI by game
```

`engine.mjs` (the game's own engine WASM, snapshot decoder) is the library behind these; the Python ones share the `analysis/` package (analyze.py's reports) and `narrative/` (narrate.py's timelines and fights). Schema and units: [replay/README.md](replay/README.md).

## Replay harness: tools/replay/harness

Re-runs our ladder games of a submission (v38 against top-20 teams; v47's ladder and scrim games) with our real
code against a puppet of the opponent's recorded inputs, proves each re-run matches the ladder game, and traces our
per-turn decisions fuel-exactly. Every script takes `--version` (default v38; `versions.py`). `py tools/replay/harness/v38lib.py` loads a game's trace joined with its extract. Setup, pipeline,
validation, loader API and caveats: [replay/harness/README.md](replay/harness/README.md).

```
py tools/replay/harness/setup_ws.py                 # workspace replays/v38-top20/ws (patched SDK, v38 release + recorder)
py tools/replay/harness/batch.py --jobs 12          # puppets, release + recorder re-runs, validation
py tools/replay/harness/trace_batch.py --all --slots 8
py tools/replay/harness/v38lib.py summary           # per-game trace availability and trust
py tools/replay/harness/pipeline.py --version v47   # v47: manifest from replay folders, then the whole chain
py tools/replay/harness/pipeline.py --version v112  # a live version (cambc 5.0.1): scrim manifest to traced direct re-runs
```

The pipeline's other scripts (`decode_all.mjs`, `extract_all.py`, `direct_batch.py`, `scrim_manifest.py`, ...) are in its README.

## Combat lab frame bank: tools/combatlab

```
py tools/combatlab/frames.py replays/batch-X [DIR...] --name NAME [--games N] [--copy] [--gz] [--threads 16]   # -> replays/combatlab/NAME/
python3 tools/combatlab/labify.py baselines/v83 variants/lab-v83                                       # a lab copy of an ocean or astraeus bot
py tools/combatlab/fork_sweep.py --games 16 --both-sides --seed 1 --out DIR [--holds 1,3]             # fork real games, sweep the decider's legal actions
node tools/combatlab/spotcheck.mjs replays/combatlab/NAME/frames.jsonl --n 40                            # specs against the replays' snapshots
```

- Fight starts from local games as scenario specs in [the lab's format](../research/notes/COMBAT-LAB.md), one per line of `frames.jsonl`, with `games.txt` (the games used) and `report.md` (kinds, champions, rounds, fight lengths, observed outcomes by kind, skips by reason, bots). Games come from each batch's `manifest.txt` (or `results.json`), only when both bots match `--bots` (ocean and astraeus variants; never fish), sampled evenly per batch with `--games`; `--copy` keeps the selected replays, with a manifest, under `NAME/replays/` (old batches get deleted; the copies are an input of their own).
- Replays are decoded by `extract.mjs` into `--cache` (default `replays/combatlab/cache/`, shared by banks, ~100 KB a game; `--prune` deletes each game's once used). Engagements are `analysis/fights.py`'s clusters; the frame is the end of round `first_damage - --lead` (2). Fighters: champions dealing or taking champion damage in the first `--core-window` (5) rounds, plus alive champions within `--margin` (4) of one. Skipped: a fighter dead or channelling (a recall cancelled by the frame's round, our bots' every-turn feint, is kept and listed in `context.feints`), a fighter in champion damage between the frame and the first hit, or a champion respawning within 20 rounds near the zone.
- Specs carry every ward on the map (`wards`: owner, team, position, disabled, the owner's recharge), which the runner places as their owners.
- Beyond the spec: champions have `name`, `maxHp`, `prio` and `ward` (`[charges, recharge]`); `fight` has `counts`, `pick_counts` (Cassi and Issac as one), `first_damage`, `length`, `core`; `context` has the bots, tributed gems, groups' capture state, wards, locks, late joiners; `observed` is the real game's next 10 and 30 rounds among the fighters (kills, deaths, gems taken, hp, who left the zone). Per-camp hp comes from camp damage events (scaled to `rounds.json`'s group totals) and per-camp sleep is simulated (clusters sleep as if their range were 3), since `rounds.json` keeps only group totals. `spotcheck.mjs` compares every field with the engine's snapshot at the frame (half its sample from frames with shields, stuns or awake camps).
- About 0.2 s a game on 16 threads for extraction, and the frames under a second per 30 games; output streams, so banks scale with disk.
- Play them with `fastrunner scenario SPECS.jsonl --bot-a BOT --bot-b BOT --rollouts N --rounds H --out OUT.jsonl --jobs J` (`FASTRUNNER_ENGINE=wasm`; output, setup and limits in [RUNNER.md](../research/notes/RUNNER.md#the-scenario-layer-fastrunner-scenario-2026-11-07)).
- `labify.py SRC DST` (names under `bots/`) copies the bot with `./tools/copybot` and patches in `lab.h`'s control block: a warm start, the decision outputs (branch, `want_home`, `stand_lost_at`, `plan_strikes`' choice) and inputs (strike bans, forced `want_home` / chase verdicts) that `fastrunner scenario --lab` reads and writes. Each patch anchor must match once, so a bot whose code moved fails loudly. Rebuild with `cambc build bots/DST`. Details in [RUNNER.md](../research/notes/RUNNER.md#lab-bots---lab).
- `labify.py` also patches in `lab.h`'s forced-action block (`LabAct`, `lab_act_run` at the start of ocean's `decide`): a walk, dash, attack, cast or end of turn that `fastrunner forkgame` sets for a round, after which the bot plays the rest of the turn itself.
- `fork_sweep.py` drives `fastrunner forkgame` (target-lab2's library, wasm engine). It plays real games, forks the full state at triggered rounds (`--trigger near:D,close:D,branch:CHARS,death:N,kill:N,every:K`), plays the bots' own line and every legal action of the deciding champion (× `--holds`) for `max(--marks)` rounds, and scores each arm. It writes `DIR/forks.jsonl` and `DIR/regret.jsonl` (each arm's value and parts, the best arm, and regret against ocean's own choice). `--analyze DIR --weights k=v,...` re-scores without replaying. The runner side is in [RUNNER.md](../research/notes/RUNNER.md#forks-of-real-games-fastrunner-forkgame-2026-11-08).
- Fork analysis (each script's docstring has its usage): `fork_regret.py DIR...` writes a row per fork (ocean's action, every arm's scores net of noise); on those rows `fork_patterns.py` finds situation x action patterns on one half of the games and tests them on the other, `fork_branch_table.py` gives every action class's gain per predicate, `fork_rules.py` scores fixed one-arm rules, `fork_verdicts.py` the forced want_home / chase verdict arms, and `fork_examples.py` replays chosen forks with traces. `mapjson.mjs` decodes maps to JSON for them.
- Scenario reports on `fastrunner scenario --lab --decisions` output: `alt_report.py` (ocean's strike-search choice against its next-best candidates, `--alt K`), `alt_replicate.py` (whether those gains replicate across opponents), `flip_report.py` (flipped want_home / chase verdicts, `--flip`). `labify_reply.py BOT DST` is labify.py plus a reply-model bot's feature block for `--hitlog`.

## Engine speed research: tools/fastengine

The fast runner's source (`runner/`, design in [RUNNER.md](../research/notes/RUNNER.md)) and the probes behind it:

```
python3 tools/fastengine/runner/scripts/compare.py BOT_A BOT_B --out DIR --cpus 0-93   # stock vs fastrunner: replay identity, winners, time
python3 tools/fastengine/runner/scripts/cmp_bundles.py A.repl26a B.repl26a           # member-by-member bundle diff (first differing fuel turn)
python3 tools/fastengine/runner/scripts/bench.py BOT_A BOT_B MAP                     # one match under several runners, pinned, interleaved
python3 tools/fastengine/runner/scripts/prof.py PROFILE.json.gz                      # where a fastrunner game spends its time (samply)
tools/fastengine/profile_games.sh OUTDIR "botA botB map"                             # samply profiles of stock cambc games; prof_analyze.py reads them
```

- `python3 tools/fastengine/runner/scripts/check_unlimited.py`: native unlimited fuel, side swapping and default parity against stock.
- `fuelhook/`: an LD_PRELOAD hook counting every host-call fuel charge (import prices off a real game, unchanged); `hook_report.py` and `calls_report.py` tabulate its output, `make_tramp_table.py` builds its patch table.
- `turbo/` (turbo.c, verify.py), `floor/` (wasmtime cache probes), `dlengine/` (cambc's engine loaded as a library):
  earlier routes to speed, kept for reference.

## Live priority mask: tools/livemask

The live scheduler (`live_sched.py`) runs `stream_patch.py BOT_DIR` on each submission's copy:
it adds `prio_stream.h` (a per-round xor of our priority payload) keyed from `livemask.key`. To rebuild a live version exactly
(e.g. to re-run a live game with traces), run the same patch on a copy of its directory.
- From v106 (2026-11-10) the key is the committed `livemask.key`. v87-v105 used an older key kept outside the repo, in
  `~/.config/cambc-secret/comms.key`: pass `--key-file` with it to rebuild those.
- `--zero` compiles the mask out, for identity checks. `mask_patch.py` / `prio_mask.h` are the older per-game mask (v93-v97).

## Rule probes: tools/probes

Probe bots that settle the rules in `cambc-rules.yaml`: how to run them and which probe checks which rule are in
[probes/README.md](probes/README.md).

## Replay exposure: tools/antire

What our ladder replays show other teams. Replays record priorities but not the shared or draft bytes
(`cambc-rules.yaml` memory.replay). From v93, live builds code ocean's priorities per game: the live scheduler patches
the mask into its build copy (`tools/livemask/`; from v106 with the committed key, earlier with the key in
`~/.config/cambc-secret/`). The code keeps the order of ranks and allies decode it exactly, so play is identical at 100M; at the real
budget its fuel changes some games, as any fuel change does. Bots in the repo are uncoded, so local games are unchanged;
our live replays from v93 on show coded values (any resubmission of the v86 control, `variants/oc-base23`, goes up uncoded).

```
node tools/antire/prio_sets.mjs REPLAY                  # every priority set: round, team, champion index, value
node tools/antire/same_play.mjs A.repl26a B.repl26a      # same game step by step, priority sets aside
python3 tools/antire/fuel_delta.py GAMES_A GAMES_B       # per-turn fuel of B - A on identical bench.py games
```

## Docs: tools/docs-sync

`cd tools/docs-sync && npm install && node sync.mjs` regenerates `docs/` (C++ only; `evaljs.mjs` reads the site bundle's data without running it). Never edit `docs/` by hand.

## .htb bots: tools/htb

C++ bots written like Java (methods inside classes, no headers); `hgen.py` generates the bot's `src/`. Example `bots/archives/htb-starter`; details in [htb/README.md](htb/README.md).

```
py tools/htb/install.py          # once: generate and build every .htb bot directly under bots/, install the VS Code extension
py tools/htb/hgen.py <bot>       # regenerate src/ (e.g. archives/htb-starter; no name: every .htb bot directly under bots/, none now); --watch on save
py tools/htb/htbcheck.py <bot>   # file:line:col errors, without a build
py tools/htb/tests/run.py        # hgen's test suite: run after changing hgen
```

`tools/htb/vscode/` is the VS Code extension's source.

Run hgen before `cambc build`, `run` and `submit`, and commit `src/`.

## Rolling live opponent checks

`ladder_opp_check.py`, called by `live_sched.py`, keeps a detector-only source-group
snapshot for each opponent in scheduler state. Once per own live version, it compares
five identical map/side cells against the current opponent and the last observed
snapshot, using that same own version. The testing context comes from that arm's actual
first core task, including historical overrides, rather than the global defaults.
If the snapshot still equals that testing pin, its existing core group is reused; otherwise one additional explicit-source
`oppcheck` group supplies the baseline. A complete valid difference advances only the
detector snapshot and logs/notifies the coordinator. Unchanged observations retain it.
Neither `refsets.json` nor any repin queue is modified. Detector groups are excluded
from strength gates and the default paired report.

Migration uses the latest valid saved observation through v112: Fish remains equivalent
to r2, while Mite starts from its v112 unpinned group. This is an initial observation,
not evidence of additional uploads between the old checks. Matching requires five
finished non-suspect cells with consistent own version, opponent, maps, sides, source
and engine/seed identity. Interrupted planning repairs missing tasks by stable IDs; snapshot
advancement and a notification outbox are saved together, with event-ID deduplication
in the append-only wake journal. Invalid comparisons hold their snapshot for review.
Tests: `python -m unittest discover -s tools/tests -p test_ladder_opp_check.py -v`.

### Retired hourly v1 checks

Off since 2026-11-10 (`live_sched.py`'s `VERSION_CHECK`; its opp-check replaces it, with no draining).
`ladder_version_check.py` integrates with `live_sched.py`:
it drains ordinary live scrims, temporarily activates platform v1, queues one
unpinned five-map group each against current Mite and Fish, restores the previous
selection mode, and compares saved deterministic game summaries. The first cycle
calibrates; later changes are logged and wake the coordinator. It never repins or
queues a repin. `ladder_coordination.py` shares a creation/switch lock with
`ladder_scrims.py`. Operational state, evidence and recovery instructions are in
[the operator guide](../research/notes/ladder-scrims-2026-11-06/VERSION-CHECK.md). Tests:
`python -m unittest discover -s tools/tests -p test_ladder_version_check.py -v`.


## Fresh-map gate

`py tools/fgate.py CAND REF` (bot dirs under `bots/`, `test_draft` off) is the standard A/B gate. CAND and REF each play the synthetic Fish and Mite bodies on the same fresh `--mix ladder-v2` maps, both sides, and the gate reads a three-way decision off the fresh maps.

- **A batch** is 2,560 fresh maps the gate has not played yet plus the 128 pinned ladder maps (`--ladder all`: every map under `maps/`, its own configs and run names): 21,504 games in four `ab.py` runs (CAND and REF against each body), 20,480 of them on fresh maps. REF's runs are cached by run name (`fb<engine>-<bot>-<body>-m<maps>b<batch>[-fuelN]`) and serve every candidate, so a changed bot needs a new dir: a cached run is reused only if it played the frozen copy (source and SDK hash) the bot has now, from its summary's `frozen` record or, for runs before that record, the copy its suite logs name; otherwise the gate stops and names it (delete `replays/ab/<run>` to replay it), and it stops too if a bot changes mid-gate. CAND and REF must agree on `test_draft`. From a worktree, the gate plays and reads that tree's bots, runs and summaries; the bodies are built where the shared markers say (the primary checkout) and copied in. The same holds for `--blocks`. `--batch-maps N` changes the step and `--max-batches N` caps the gate.
- **Opponents** are compiled once per body version (`variants/rt-Flp4`, `rt-Mt3q`, made from noise body 1 by `research/notes/ideas-2026-11-11/conditional-batch506/runtime_body.py`): the noise seed and draft salt that `spar-dvnK` bakes in are read per game from the runner (`ab.py --experiment-config`). Fresh map i of the pool plays noise seed i + 1; batch j's ladder maps play noise j + 1. The bodies run unmetered, which plays the same games as their ordinary code with unlimited fuel. CAND and REF keep the exact fuel budget: 100k a turn, or `--fuel N`. A bot without the run-time import cannot be configured or unmetered, so an ocean mirror never is.
- **Decision**, read after each batch on the fresh map units (a unit is 0.5 + CAND's mean minus REF's over a map's four paired games): REJECT (low SPRT 0.4975/0.50 at H0), ACCEPT (high SPRT 0.505/0.5075 at H1; the gate then plays on to the LIVE BAR, ln 99, on maps the screen never saw, unless `--screen`), ZONE (low H1 and high H0: judgement; `--zone-stop` ends there), NARROWED (95% half-width ≤ `--ci`, default 0.25 points; 0 disables), IDENTICAL (no paired game differs). It prints Fish, Mite, one-site and multi-site splits, the ladder side read and a "Results against REF" table, and writes `~/tmp-offload/diverse/gate-logs/fgate-<cand>--<ref><bodies>[-fuelN]-batch.json`.
- **Size.** A unit's standard deviation is about 27 points, so a batch narrows the fresh read to ±1.05 points, 4 batches to ±0.52 and 16 to ±0.26. A change of +2 points reaches ACCEPT in about 3 batches, +1.5 in 4, +1 in 9; a loss of 1 point reaches REJECT in about 4. A change within a quarter point of zero runs to NARROWED at about 18 batches. `--max-batches N --ci 0` is a fixed read of at most N batches.
- **Pool:** `~/tmp-offload/gatebatch/pool` (`FGATE_HOME`), 97,535 fresh ladder-v2 maps (mapgen seeds 2417000-2417383; 38 whole batches), byte-new against the ladder and one per layout key, in a fixed shuffled order that every gate walks from batch 0, so early batches are shared by every candidate; `--first-batch J` starts later, on maps earlier gates have not played, for a held-out confirmation. `py tools/fgate_batch.py grow SEEDS DIR...` appends generated maps after the existing ones.
- **`--pool v3`** (opt-in; the default stays v2): fresh batches from `~/tmp-offload/gatebatch/pool-v3`, `--mix ladder-v3` maps (mapgen seeds 2490000-2490127, in `generated-v3/`), with the 05 part interleaved at its share so every batch holds it at that share. Its batch configs and parts are under `suites-v3/`, and its run names and result file end `-Pv3`, so no v2 batch or cached REF run is reused for it. Grow it with `py tools/fgate_batch.py grow SEEDS DIR... --pool v3`.
- **`--pool v4`** (opt-in): the same for `~/tmp-offload/gatebatch/pool-v4`, `--mix ladder-v4` maps (mapgen seeds 2500000-2500127 in `generated-v4/`: 43,327 maps, 16 batches; 2500128-2500999 reserved for growing it), `suites-v4/` and `-Pv4`.
- **Runner:** the batch gate loads `tools/fastengine/runner/target-rt/release/libfastrunner.so` (`FGATE_RUNNER_LIB`), built from this tree with `CARGO_TARGET_DIR=target-rt cargo build --release`. Metered games are byte-identical to the shared library's, which other jobs keep using. A hung unmetered body cannot run out of fuel, so each game has a 600 s watchdog (`--game-timeout`); a timed-out game is a failed game, counted in the report.
- **`--blocks`** is the gate as it was before 2026-11-11, for reproducing older reads: 256-game noise blocks on 1,024 fresh maps and the ladder, a compiled opponent pair a block, metered bodies. The two modes play different opponent populations, so their runs and result files are separate and their win rates against the bodies do not compare.

`fgate.py --blocks CAND REF` forwards the noise-block game/statistical options unchanged to `research/notes/ideas-2026-11-09/freshgate-tools/fgate.py` and prepares opponent compilation ahead of demand. Its default is 16 process workers and the current plus eight future noise blocks; every worker holds one shared CPU slot and uses the normal generated-source and frozen-build locks. `--compile-workers N`, `--compile-lookahead N`, and `--no-compile-ahead` control this resource optimization; `CAMBC_COMPILE_AHEAD=0` also disables scoped integration in queued gates. No extra scored games or warm-up games are played. Ordinary `ab.py` comparisons continue to build their two fixed bots normally.

`gate_compile_ahead.py --plan PLAN [--check]` implements the owner-bound helper and a gate-phase scope. Exact process identity, source/tool seals, a stop marker, and draining outstanding compiles bound its lifetime. Queued conditional, draft, and tuning final gates use this scope; training and mandatory mirror phases do not. The historical research gate stays unchanged for active sealed experiments. Lightweight checks: `tools/tests/test_{gate_compile_ahead,fgate_entrypoint}.py` and conditional lifecycle tests.

`experiment_config.py` validates optional per-map REF-only native opponent inputs for `ab.py` / `run_batched.py --experiment-config FILE`. The runner accepts the resulting per-game `--runtime-config` manifest fields; only explicitly configured synthetic Fish/Mite replicas use unmetered native code. Ocean candidate/reference and mirrors stay metered. Configured preparation uses one-slot C++ builds and a `run-batch --prepare-only` cache preparation holding up to 16 slots (what fair share grants) before ordinary shared-pool games. `--game-timeout SECONDS` provides an opt-in owned-worker timeout (run-batch only), retaining errors without retry. See runtime opponent API and validation for schema, cache/PGO semantics and isolated-library evidence.

