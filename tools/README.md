# Tools

Run every script from the repo root.

## A/B: ab.py and run_batched.py

```
py tools/ab.py orch/my-branch main --name my-change            # two git refs
py tools/ab.py HEAD hecate                                     # against the reference bot
py tools/ab.py main HEAD~1 --no-test-draft --suites ladder,gen # each on its own draft
```

- **CAND / REF:** a git ref, whose `bots/hyperion` (`bots/hecate` before the rename) is exported with `git archive` (never the working tree) to `bots/variants/ab-<name>-<cand|ref>-<sha7>/` with `params::test_draft` on; or a bot under `bots/`, used as is. Run it from the primary checkout (worktree branches resolve there).
- **Options:** `--name`, `--threads` (22), `--suites` (default `ladder,gen,fresh`: `maps/`, `maps/gen/`, each `maps/gen-s*/`; or a directory of maps), `--no-test-draft`, `--fuel N`.
- **Output:** CAND's win % with a 95% Wilson interval, overall and per suite, failed matches, out-of-fuel turns per bot and wall time; `replays/ab/<name>/` holds `summary.json`, `summary.md` and the logs. The exit code is non-zero if a match failed.
- **By map class:** `py tools/ab_classes.py <name> [--by preset,access] [--list access=teleport]` joins an A/B (or batch dirs) with the maps' `index.json`: CAND's win %, the share reaching round 2000 and, once extracted, both bots' mean tributed gems per kind, preset, access, gated, camp mode, spawn or economy.

`run_batched.py` plays two bots on every map, once from each side (it builds them with `cambc build`, since `cambc run-batch`'s own builds fail on Windows):

```
py tools/run_batched.py <bot1> <bot2>   # names under bots/, or paths
py tools/run_batched.py --watch         # progress of the newest batch, from another terminal
```

- **Options:** `--threads N` (16), `--one-side` (sides by `--side-seed`), `--maps-dir` (default `maps/`, skipping `maps/gen*/`), `--gen [N]` (`maps/gen/`, all or N by `--gen-seed`), `--fuel`, `--timeout SECONDS`, `--no-replays`.
- **Output** in `replays/batch-TIMESTAMP/`: `results.json` (wins from bot 1's view, then per match; `winner` is the 0-based bot index), `<n>-<map>-<12|21>.repl26a` (`12`: bot 1 is team A), `run.log` and `*.error.log`.

## Farming benchmark: solo.py and bots/idle

Mirror A/Bs barely show farming changes, so solo.py plays CAND and REF each against `bots/idle` on the same maps and compares how fast they farm, paired per map:

```
py tools/solo.py astraeus variants/astraeus-<sha7> --name my-change
py tools/solo.py astraeus astraeus --suites ladder --one-side --maps 3   # smoke run, ~15 s
```

- **bots/idle** drafts heart_of_ruin, marcella, vendetta, vesper_vale, ryth in order and ends every champion's turn at once.
- **CAND / REF:** bot directories under `bots/`, used as they are (params.h included, so match their `test_draft`); export a commit as AGENTS.md shows. Games take ~1.5 s, since they end at 1000 gems.
- **Options:** `--name`, `--threads` (22), `--suites` (as ab.py's), `--one-side`, `--maps N` (N maps per suite, by `--map-seed`), `--fuel N`.
- **Metrics,** from the replays (extracted into `replays/solo/<name>/analysis/`): the round tributed gems reach 1000 (never: counted as 2001), tributed and collected (tributed + carried) gems at rounds 150/300/600, lifetime gold earned at 300/600. Per map, CAND - REF averaged over sides (a log ratio for the 1000 round, shown as a % change), mean and bootstrap 95% CI over maps, overall and per suite, and the maps where CAND reaches 1000 faster / slower / identical.
- **Checks:** out-of-fuel turns per bot, and games where our bot damages the idle champions (it pokes them on their spawn on small maps such as yellow-brick-road) or either bot errors. Output: `replays/solo/<name>/summary.json` (every game's metrics) and `summary.md`.

## Maps: tools/mapgen

- `maps/` holds the ladder maps as SDK updates ship them (`00ambush`, `01big-world`, ...); delete any uuid-suffixed copies an update adds. Ladder replays drop the prefix; extract.mjs and mapgen accept either.
- `maps/gen/` (seed 1201) and `maps/gen-s1/` (seed 1202) are 256-map generated suites, regenerated 2026-10-25 on engine 2.0.0 with its ladder maps. `index.json` records each map's kind, preset (or mutated ladder map and its edits), spec and metrics. The kinds:
  - **ladder-like** (~22%): presets close to the competition maps.
  - **mutation** (~12%): a ladder map and its edits, both drawn from the seed.
  - **designed** (~38%): scenarios laid out by [design.mjs](mapgen/design.mjs), each pinning a test:
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
  - **exotic** (~29%): shapes, interiors, spawn distances and economy extremes (gem-drought, gem-flood, gold-flood).
- **Access.** Objectives may need a dash (2 king steps over holes) or a teleport crystal (range 3, any terrain) when the map says so (`g.access`).
  - When any does, each team reaches on foot a gold-paying camp it can take early, so it can always buy a crystal.
  - `metrics.access`, `dash_gems` and `tele_gems` record what a map needs; about 13% of a suite needs more than walking.
  - Camp-plugged routes (kill to pass, like boss-battle) are `gated` in the index.
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
```

## Forced drafts: tools/variants

The draft is compiled in, so a forced draft is a bot copy in `bots/variants/<name>/` (gitignored). Make variants from hyperion: hecate's `params::test_draft` overrides any forced draft.

```
py tools/variants/make_variant.py varg,willow,ryth                        # drafts under 5 are padded (-pad)
py tools/variants/matrix.py varg,tavi,ryth,stellar,ren willow,ren --one-side   # [BOT@]DRAFT specs; BOT@ = its own draft
py tools/variants/matrix.py --focus --cols hecate@                        # each champion first, + --filler
py tools/variants/matrix.py --resume replays/matrix-TIMESTAMP             # --report: rewrite reports only
```

[draft_search.py](variants/draft_search.py) is a library for astraeus's per-pick-count drafts (`params::draft_three/four/five`) against proxies of the top-10 teams (the source bot, `DS_SRC`, playing each team's main drafts), with paired results cached in `DS_DB` (default `replays/ds/db.jsonl`) and keyed by a hash of the source bot and the maps, so a changed bot never reuses old games (method in [DRAFT.md](../research/hyperion/DRAFT.md)).

[ds_run.py](variants/ds_run.py) drives it in stages (`run`/`report`/`combo`/`vehicle`: screen, rest of pool, `--fresh DIR`, a vehicle for an `ab.py` head-to-head on `draft_search.suite_dir(P, ...)`); `--picks 3,4` shares vehicles across pick counts.

matrix.py plays one batch per distinct pair (`--bot` rows, `--vs-bot` columns; identical entries are mirrors, reported as team A's win rate) and writes `replays/matrix-TIMESTAMP/`.

## Fuel: tools/fuel

```
py tools/fuel/bench.py run hyperion --out replays/fuel/base.json          # 16 games vs hecate, 8 maps, 100M fuel
py tools/fuel/bench.py compare replays/fuel/base.json replays/fuel/x.json  # identical replays, fuel change
py tools/fuel/bench.py run hyperion --fuel 0 --out replays/fuel/real.json # the real budget: shortcuts and lost turns
py tools/fuel/bench.py run hyperion --set wide --test-draft --per-map --jobs 8 --out replays/fuel/x.json  # 52 games, ~5 min
py tools/fuel/oof.py replays/batch-A replays/batch-B                      # out-of-fuel turns per bot
py tools/replay/debug_lines.py SRCH-PASS -- replays/batch-A               # any debug_block line prefix per bot (--show N)
py tools/fuel/cap_variant.py hecate --run-fuel 10000000                   # a copy that charges itself back to 100k a turn
py tools/ab.py main variants/hecate-cap100000-at10000000 --fuel 10000000  # so only CAND gets 10M
```

- **bench.py:** `--maps` takes ladder names or paths; `--set wide` is 26 maps (12 ladder, the 14 in `maps/gen-bench/`); `--test-draft` gives both bots the ladder test compositions; `all` counts play turns from round 2. Wide-set baselines (bbf6f05): `replays/fuel/wide-base-100M.json`, `wide-base-real.json`.
- The 16-game bench swings by ±20 out-of-fuel turns and has no shared-gem map: judge out-of-fuel turns on a full A/B.
- hyperion prints `SHORTCUT round champion what` where fuel made it choose worse and `OOF round phase` for each turn that ran out (both in `debug_block`). `debug_fuel` in util.h gives per-phase costs (`FuelMeter`, ~170 a meter). Where the fuel goes: [EXPERIMENTS Fuel](../research/EXPERIMENTS.md#fuel).
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
