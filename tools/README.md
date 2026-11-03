# Tools

Run every script from the repo root.

## A/B: ab.py and run_batched.py

```
py tools/ab.py orch/my-branch main --name my-change            # two git refs
py tools/ab.py astraeus baselines/v66 --no-test-draft          # two bot directories
py tools/ab.py main HEAD~1 --no-test-draft --suites ladder,gen # each on its own draft
py tools/ab.py astraeus variants/astraeus-38aa25c --no-test-draft --sprt --sprt-stop low  # stop a loser early
```

- **CAND / REF:** a git ref, whose `bots/hyperion` (`bots/hecate` in commits before the 2026-10-21 rename) is exported with `git archive` (never the working tree) to `bots/variants/ab-<name>-<cand|ref>-<sha7>/` with `params::test_draft` on; or a bot under `bots/`, used as is. Run it from the primary checkout (worktree branches resolve there).
- **Options:** `--name`, `--threads` (all CPU slots), `--suites` (default `ladder,gen,fresh`: `maps/`, `maps/gen/`, each `maps/gen-s*/`; or a directory of maps), `--no-test-draft`, `--fuel N`. The suites play at once, sharing the CPU slots (one after another on Windows).
- **Output:** CAND's win % with a 95% Wilson interval, overall and per suite, failed matches, out-of-fuel turns per bot and wall time; `replays/ab/<name>/` holds `summary.json`, `summary.md` and the logs. The exit code is non-zero if a match failed.
- **Early stopping:** `--sprt [P0,P1]` (default `0.50,0.52`: CAND's win rate under H0 and H1) ends every suite once a sequential probability ratio test, over all suites together, decides. It uses maps both of whose games have finished, each scoring CAND's mean x in {0, 0.5, 1}, since a map's two sides are correlated: over N maps with mean m and variance v (floored at 0.001), LLR = N (P1 - P0)(2m - P0 - P1) / (2v) (fishtest's normal approximation), accepting H0 at LLR <= ln(beta / (1 - alpha)) and H1 at LLR >= ln((1 - beta) / alpha), ±2.94 at the defaults. `--sprt-alpha`, `--sprt-beta` (0.05 each); `--sprt-stop low` stops only on H0 (not a P1 gain), `high` only on H1, `both` (default) on either, the other only reported; `--sprt-min-games N` (200) never stops sooner; `--sprt-seed` (0) shuffles the map order (`run_batched.py --shuffle`). An extra SPRT line gives the LLR, its bounds, the map pairs used, the outcome and whether it stopped the run; killed suites are not failures. After a stop the win rates are from a partial sample that mixes the suites by how fast each got CPU slots (about evenly, the first to finish building sooner), not by their sizes. Not on Windows.
- **Farming against the opponent:** `py tools/ab_farm.py <name> [--json OUT]` extracts the run's replays (once, ~8 min for 1164 games) and pairs CAND with REF per game: gold earned @150/300/600/end, capture gold @300 (all, and groups with an Elk or Golem), gold the other side captured on groups one did most of the damage on, camp damage, gold per 1k camp damage, tributed gems @600, deaths to camps; mean CAND - REF with a bootstrap 95% CI, overall and per suite.
- **By map class:** `py tools/ab_classes.py <name> [--by preset,access] [--list access=teleport]` joins an A/B (or batch dirs) with the maps' `index.json`: CAND's win %, the share reaching round 2000 and, once extracted, both bots' mean tributed gems per kind, preset, access, gated, camp mode, spawn or economy.

`run_batched.py` plays two bots on every map, once from each side (it builds them, at once, with `cambc build`, since `cambc run-batch`'s own builds fail on Windows, then compiles each into the WASM cache):

```
py tools/run_batched.py <bot1> <bot2>   # names under bots/, or paths
py tools/run_batched.py --watch         # progress of the newest batch, from another terminal
```

- **Options:** `--threads N` (all CPU slots), `--one-side` (sides by `--side-seed`), `--maps-dir` (default `maps/`, skipping `maps/gen*/`), `--gen [N]` (`maps/gen/`, all or N by `--gen-seed`), `--fuel`, `--timeout SECONDS`, `--no-replays`, `--shuffle SEED` (play the maps in a seeded random order, each map's two sides together, instead of slowest first).
- **Output** in `replays/batch-TIMESTAMP/`: `results.json` (wins from bot 1's view, then per match; `winner` is the 0-based bot index; replaced whole after each match, so it is never half-written), `<n>-<map>-<12|21>.repl26a` (`12`: bot 1 is team A), `run.log` and `*.error.log`.

## Farming benchmark: solo.py and bots/idle

Mirror A/Bs barely show farming changes, so solo.py plays CAND and REF each against `bots/idle` on the same maps and compares how fast they farm, paired per map:

```
py tools/solo.py astraeus variants/astraeus-<sha7> --name my-change
py tools/solo.py astraeus astraeus --suites ladder --one-side --maps 3   # smoke run, ~15 s
```

- **bots/idle** drafts heart_of_ruin, marcella, vendetta, vesper_vale, ryth in order and ends every champion's turn at once.
- **CAND / REF:** bot directories under `bots/`, used as they are (params.h included, so match their `test_draft`); export a commit as AGENTS.md shows. Games take ~1.5 s, since they end at 1000 gems.
- **Options:** `--name`, `--threads` (all CPU slots), `--suites` (as ab.py's), `--one-side`, `--maps N` (N maps per suite, by `--map-seed`), `--fuel N`.
- **Metrics,** from the replays (extracted into `replays/solo/<name>/analysis/`): the round tributed gems reach 1000 (never: counted as 2001), tributed and collected (tributed + carried) gems at rounds 150/300/600, lifetime gold earned at 300/600. Per map, CAND - REF averaged over sides (a log ratio for the 1000 round, shown as a % change), mean and bootstrap 95% CI over maps, overall and per suite, and the maps where CAND reaches 1000 faster / slower / identical.
- **Checks:** out-of-fuel turns per bot, and games where our bot damages the idle champions (it pokes them on their spawn on small maps such as yellow-brick-road) or either bot errors. Output: `replays/solo/<name>/summary.json` (every game's metrics) and `summary.md`.

## Maps: tools/mapgen

- `maps/` holds the ladder maps as SDK updates ship them (`00ambush`, `01big-world`, ...); delete any uuid-suffixed copies an update adds. Ladder replays drop the prefix; extract.mjs and mapgen accept either.
- `maps/gen/` (seed 6001) and `maps/gen-s1/` (seed 6002) are 256-map generated suites, and `maps/fresh-6003` to `fresh-6040` further fresh ones (seeds = their names), 10,240 maps in all, regenerated 2026-10-30 by the generator with the families below. Earlier A/Bs used other maps: seeds 6003-6196 of the older generator, and before that 4001-5120, 2901-2934 and 1201/1202. The suites are not in git (`.gitignore`): rebuild them with the commands below (~2 s a suite). `index.json` records each map's kind (its family), preset (or mutated ladder map and its edits), spec and metrics, and the suite's `mix`.
- **Mix.** `suite --mix varied` (the default) reweighs the plan per seed: each family and each preset is scaled by a random factor and a preset is sometimes dropped, so fresh suites stress different things. `--mix fixed` keeps the plan's counts. The plan's shares:
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
  - camps reaching a spawn's edge (`spawn_reach_gap`);
  - a partly walled spawn surround (`spawn_clear`);
  - 4x3 and 5x2 spawns (`spawn_dims`);
  - composed groups (`poly`, `snake`, `ring`, `carpet`, `pack`).

  Any spawn rectangle of 9-16 tiles loads. Camps are never placed on bush; no ladder map but two (quarry, harvest, one pair each) has one there.
- **Extension modules** (topology.mjs, scenarios.mjs) export `PRESETS`, `DESIGNS`, `CAMP_MODES` and `TEMPLATES`, which generate.mjs merges (a duplicate name throws). A module's presets are its family. A module may import generate.mjs but use it only inside functions, and nothing may import a module before generate.mjs.
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
- [mapgen.mjs](mapgen/mapgen.mjs) builds maps through the engine WASM's map builder, seeded. Presets, placement, validation and metrics are in [generate.mjs](mapgen/generate.mjs), playable-area shapes in [shapes.mjs](mapgen/shapes.mjs), and designers, brushes and cover prefabs in [design.mjs](mapgen/design.mjs).

```
node tools/mapgen/mapgen.mjs list                                  # presets
node tools/mapgen/mapgen.mjs gen donut --seed 3 [--set altar_mode=central] --out x.map26a --show   # north at the top
node tools/mapgen/mapgen.mjs gen atoll --seed 2 --show             # a designed scenario
node tools/mapgen/mapgen.mjs mutate expanse --op "walls*0.5" --op "camps*1.3" --out x.map26a   # mirror-preserving edits
node tools/mapgen/mapgen.mjs mutate random --seed 7 --show          # a seeded ladder map under seeded edits
node tools/mapgen/mapgen.mjs check maps maps/gen                   # validity, reachability, metrics
node tools/mapgen/mapgen.mjs diversity maps/gen DIR                # map sets against the ladder maps
node tools/mapgen/mapgen.mjs suite [gen-s1] [--out DIR --seed S]   # rebuild maps/gen (or gen-s1), or a fresh suite
node tools/mapgen/mapgen.mjs suite --seed 3001-3004,3010 --out maps/fresh-{seed}   # several fresh suites, sharing --jobs (48) processes
node tools/mapgen/mapgen.mjs suite --seed 6003 --mix fixed --out DIR   # the plan's counts, not reweighed
```

## Map fuzzing: tools/fuzz

`py tools/fuzz/fuzz.py run NAME [--screen 400] [--ref hyperion] [--climb 8 --gens 4] [--shrink 2]` hunts for maps on which astraeus farms pathologically against bots/idle.
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
- Details in [fuzz/README.md](fuzz/README.md). A 600-map screen plus a 5-generation climb takes ~12 min on 80 slots and ~1.2 GB.

## Forced drafts: tools/variants

The draft is compiled in, so a forced draft is a bot copy in `bots/variants/<name>/` (gitignored). A bot whose `params::test_draft` is on ignores any forced draft.

```
py tools/variants/make_variant.py varg,willow,ryth                        # drafts under 5 are padded (-pad)
py tools/variants/matrix.py varg,tavi,ryth,stellar,ren willow,ren --one-side   # [BOT@]DRAFT specs; BOT@ = its own draft
py tools/variants/matrix.py --focus --cols astraeus@                      # each champion first, + --filler
py tools/variants/matrix.py --resume replays/matrix-TIMESTAMP             # --report: rewrite reports only
```

[draft_search.py](variants/draft_search.py) is a library for astraeus's per-pick-count drafts (`params::draft_three/four/five`) against proxies of the top-10 teams (the source bot, `DS_SRC`, playing each team's main drafts), with paired results cached in `DS_DB` (default `replays/ds/db.jsonl`) and keyed by a hash of the source bot and the maps, so a changed bot never reuses old games (method in [DRAFT.md](../research/hyperion/DRAFT.md)).

[ds_run.py](variants/ds_run.py) drives it in stages (`run`/`report`/`combo`/`vehicle`: screen, rest of pool, `--fresh DIR`, a vehicle for an `ab.py` head-to-head on `draft_search.suite_dir(P, ...)`); `--picks 3,4` shares vehicles across pick counts.

matrix.py plays one batch per distinct pair (`--bot` rows, `--vs-bot` columns; identical entries are mirrors, reported as team A's win rate) and writes `replays/matrix-TIMESTAMP/`.

## Fuel: tools/fuel

```
py tools/fuel/bench.py run astraeus --out replays/fuel/base.json          # 16 games vs hyperion, 8 maps, 100M fuel
py tools/fuel/bench.py compare replays/fuel/base.json replays/fuel/x.json  # identical replays, fuel change
py tools/fuel/bench.py run astraeus --fuel 0 --out replays/fuel/real.json # the real budget: shortcuts and lost turns
py tools/fuel/bench.py run astraeus --set wide --test-draft --per-map --jobs 8 --out replays/fuel/x.json  # 52 games, ~5 min
py tools/fuel/oof.py replays/batch-A replays/batch-B                      # out-of-fuel turns per bot
py tools/fuel/oof_bot.py replays/batch-A replays/batch-B                  # the same without shared-gem maps, by round, finish gap, run size
py tools/fuel/census/batch_oof.py --bot 1 replays/batch-A                 # one bot's: first-in-streak, by round, phase, branch, map
py tools/replay/debug_lines.py SRCH-PASS -- replays/batch-A               # any debug_block line prefix per bot (--show N)
py tools/fuel/cap_variant.py hyperion --run-fuel 10000000                 # a copy that charges itself back to 100k a turn
py tools/ab.py main variants/hyperion-cap100000-at10000000 --fuel 10000000 # so only CAND gets 10M
```

- **WASM cache** (`tools/cambc_env.py`): every match process used to compile both bots' WASM with Cranelift, ~80% of its CPU. Tools that play matches give cambc `CAMBC_WASMTIME_CACHE` (wasmtime's cache, in the git common dir as `cambc-wasmtime/`, keyed by the module's bytes) and `RAYON_NUM_THREADS=1`; replays are byte-identical. A full A/B went from ~154 s to ~25 s (2026-10-29, 96 cores; plus ~25 s to build a new bot). A script that runs `cambc run`/`run-batch` itself should pass `env=cambc_env.env()`.
- **Turbo** (`CAMBC_TURBO`, opt-in, Linux x86-64): with `CAMBC_TURBO=1`, `cambc_env.env()` preloads [turbo.c](fastengine/turbo/turbo.c), built into the git common dir's `cambc-turbo/` (an absolute path names a built library instead), so `CAMBC_TURBO=1 py tools/ab.py ...` runs every match on a patched cambc 4.0.0: about 2.4x faster a game alone, 1.9x at 4 games at once (1.5x in the debug builds `ab.py` plays), with byte-identical replays (any other cambc build runs stock). Re-check after a cambc or patch change with `python3 tools/fastengine/turbo/verify.py --turbo LIB --out DIR BOT_A BOT_B --suites ladder,gen,fresh [--debug]`; [DESIGN.md](../research/fastengine/DESIGN.md) §5 has the patches and parity runs.
- **CPU slots, fair share** (`cpu_slots.py`; fastrunner mirrors it): concurrent jobs share the 94 slots by job, not by process: a tool and everything it starts is one group (`CAMBC_SLOT_GROUP`, default `job-<pid>` of the first Python tool), weighted by `CAMBC_SLOT_WEIGHT` (default 1; the draft and emblem labs 2). A group keeps a free slot only below its weighted share or when no other waiting group is below its own, so an A/B's 100 suites no longer starve a lab; a lone job still takes every slot, and running games are never stopped. 2026-11-03 tests (8 slots): 10 processes against 1 at equal weights held 4.0 / 4.0; weight 2 against 1, 4.9 / 3.0. `CAMBC_SLOT_DIR` points a test at another pool.
- **fastrunner** (`CAMBC_BIN`, opt-in, Linux x86-64, cambc 4.0.0): `CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native py tools/ab.py ...` plays every match with [the fast runner](fastengine/runner/), cambc's own engine driven by a new runner preloaded into cambc, with stock's replays, fuel, stdout and `.camstat` byte for byte (1164/1164 games, both modes) but no debug drawings (`team-?.debug` is empty). `FASTRUNNER_MODE=native` (needs clang) translates each bot's wasm to C with wasmtime's exact fuel metering and compiles it (about 7 s a bot, cached); the default runs bots on wasmtime. On the whole machine (11 CPUs, 1164 games of the default suites) ab.py ran at 77k games/h native (4.7x) and 57k exact (3.5x), against 16k for stock (turbo was 1.4x). With fastrunner, `run_batched.py` hands a whole batch to one `run-batch`, which takes a CPU slot per game itself; builds still run stock cambc. Build it once: `cd tools/fastengine/runner && ./setup_vendor.sh && cargo build --release`. [RUNNER.md](../research/fastengine/RUNNER.md) has the design, numbers and limits; `tools/fastengine/runner/scripts/compare.py` re-checks it against stock.
- **CPU slots** (`tools/cpu_slots.py`): every bench game and every `run_batched.py` run (so `ab.py`, `solo.py`) takes slots from one machine-wide pool of `CAMBC_SLOTS` (default cores - 2), file locks in the git common dir shared by all worktrees. bench.py holds a slot per game, and so does run_batched.py on Linux and macOS (each match is its own `cambc run-batch`, no slower than sharing one), so `--threads` defaults to the whole pool and concurrent agents share the cores game by game: a slot one run frees goes to whichever is waiting. On Windows every `run-batch` reconfigures both bots' builds as it starts and concurrent ones break each other's, so a batch there is one `run-batch` holding the slots free at its start (at least 4) until it ends. run_batched.py plays copies of the bots in `replays/frozen/<hash of source and SDK>/<name>/`, so editing a bot mid-batch never changes the batch's games, and batches of the same source share one build.
- **bench.py:** `--maps` takes ladder names or paths; `--set wide` is 26 maps (12 ladder, the 14 in `maps/gen-bench/`); `--test-draft` gives both bots the ladder test compositions; `all` counts play turns from round 2. Wide-set baselines (bbf6f05): `replays/fuel/wide-base-100M.json`, `wide-base-real.json`.
- The 16-game bench swings by ±20 out-of-fuel turns and has no shared-gem map: judge out-of-fuel turns on a full A/B.
- hyperion prints `SHORTCUT round champion what` where fuel made it choose worse and `OOF round phase` for each turn that ran out (both in `debug_block`). `debug_fuel` in util.h gives per-phase costs (`FuelMeter`, ~170 a meter). Where the fuel goes: [EXPERIMENTS Fuel](../research/EXPERIMENTS.md#fuel).
- Since CHANGES 217 (late finish) a turn after one that ran out finishes even if it runs out too, and its `OOF round phase` line names the last phase reached, not where fuel ran out (often `queue`). The census records the true stack.
- **Fuel census** (`tools/fuel/census/`): per-component fuel of every heavy or out-of-fuel turn, and the scopes open when fuel ran out. Instrument a debug copy (never a real bot; `instrument.py` fails loudly once the bot's code has moved, so update its patterns), play it at the real budget, then tabulate OOF-first, OOF-late and heavy finished turns by component, branch, champion type and stack:

  ```
  mkdir -p bots/variants/astraeus-cen && cp -r bots/astraeus/src bots/variants/astraeus-cen/  # no .cambc/
  cp tools/fuel/census/census.h bots/variants/astraeus-cen/src/ && py tools/fuel/census/instrument.py bots/variants/astraeus-cen/src --fine
  py tools/fuel/bench.py run variants/astraeus-cen --fuel 0 --maps $(cat tools/fuel/census/maps.txt) --games replays/fuel/cen --out replays/fuel/cen.json
  py tools/fuel/census/census.py replays/fuel/cen
  ```

  `maps.txt` is 28 maps heavy in out-of-fuel turns (2026-10-29); its findings head [TODO.md](../research/hyperion/TODO.md)'s ranked list.
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

astraeus drafts from the model (README's deployment section).

## Constant tuning: tools/tune

SPSA on a bot's params.h constants against a panel of opponents, scored by win, tributed gems and gold. Candidates
are the base build with one data block patched (in the wasm and the fast runner's cached native code), so they cost
no compile; an iteration is one fast-runner batch, pipelined with scoring (~300 games/s on alext alone). Details in
[tune/README.md](tune/README.md).

```
python3 research/diana-2026-11-03/tunify.py bots/BOT              # once: constants -> a patchable block
python3 tools/tune/tune.py init --run R --bot bots/BOT --opps variants/a,baselines/v67
python3 tools/tune/tune.py run --run R --hours 6                  # resumable; replays/tune/R/
python3 tools/tune/tune.py status --run R
```

**Few suites per A/B on alext.** Each suite of `ab.py` is its own fastrunner run-batch, and each one polls the CPU
slots under one global lock (`fair.lock`, scanning every slot and member file): 103 suites at once (fresh-92001..92100
as separate suites) put alext at 85% system time and ~1 game/s for everyone else (2026-11-03). Merge many small
suites into one directory of symlinks (e.g. `maps/fresh-92all`) instead.

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
py tools/replay/analyze.py replays/batch-TIMESTAMP --vs replays/ladder --team hyperion   # --reports economy,camps
py tools/replay/ab_compare.py <variant name> batch-A batch-B           # both bots of an A/B in the same games
py tools/replay/narrate.py replay-bulk/2026-10-24                      # turn-level timelines, fight transcripts, episode files
py tools/replay/stalls.py <ab name or batch> --min 300 [--bot 1]       # champions on one tile, alive and off spawn, 300+ rounds
py tools/replay/macro_stats.py replays/.analysis [--bot NAME] [--json OUT]   # time budget, camp clears and captures, winners vs losers
py tools/replay/turn_budget.py batch-A batch-B [--by-bot]               # after extract.mjs: each turn's class and what it earns (reads the `D` trace lines of non-release builds)
py tools/replay/walk_audit.py batch-X [--team NAME]                     # why champions walk: legs, detours, crews, recall cycles (solo games)
py tools/replay/hold_metrics.py EXTRACT_DIR [...]                      # per bot: captures, hold resets by cause (walked off alive), pressured holds, deaths, A-B-A flips
py tools/replay/fight_metrics.py EXTRACT_DIR [...]                     # per bot: deaths and kills a game, deaths to champions/camps, kill share at equal numbers, captures, captured and tributed gems
```

Schema and units: [replay/README.md](replay/README.md).

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
```

## Rule probes: tools/probes

Probe bots that settle the rules in `cambc-rules.yaml`: how to run them and which probe checks which rule are in
[probes/README.md](probes/README.md).

## Docs: tools/docs-sync

`cd tools/docs-sync && npm install && node sync.mjs` regenerates `docs/` (C++ only). Never edit `docs/` by hand.

## .htb bots: tools/htb

C++ bots written like Java (methods inside classes, no headers); `hgen.py` generates the bot's `src/`. Example `bots/htb-starter`; details in [htb/README.md](htb/README.md).

```
py tools/htb/install.py          # once: generate and build every .htb bot, install the VS Code extension
py tools/htb/hgen.py <bot>       # regenerate src/ (no name: every .htb bot); --watch on save
py tools/htb/htbcheck.py <bot>   # file:line:col errors, without a build
py tools/htb/tests/run.py        # hgen's test suite: run after changing hgen
```

Run hgen before `cambc build`, `run` and `submit`, and commit `src/`.
