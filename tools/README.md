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

`run_batched.py` plays two bots on every map, once from each side (it builds them with `cambc build`, since `cambc run-batch`'s own builds fail on Windows):

```
py tools/run_batched.py <bot1> <bot2>   # names under bots/, or paths
py tools/run_batched.py --watch         # progress of the newest batch, from another terminal
```

- **Options:** `--threads N` (16), `--one-side` (sides by `--side-seed`), `--maps-dir` (default `maps/`, skipping `maps/gen*/`), `--gen [N]` (`maps/gen/`, all or N by `--gen-seed`), `--fuel`, `--timeout SECONDS`, `--no-replays`.
- **Output** in `replays/batch-TIMESTAMP/`: `results.json` (wins from bot 1's view, then per match; `winner` is the 0-based bot index), `<n>-<map>-<12|21>.repl26a` (`12`: bot 1 is team A), `run.log` and `*.error.log`.

## Maps: tools/mapgen

- `maps/` holds the ladder maps as SDK updates ship them (`00ambush`, `01big-world`, ...); delete any uuid-suffixed copies an update adds. Ladder replays drop the prefix; extract.mjs and mapgen accept either.
- `maps/gen/` (seed 1021) and `maps/gen-s1/` are 256-map generated suites: exotic and ladder-like presets plus ladder mutations, symmetric, everything reachable on foot. `index.json` records each map's preset, spec and metrics.
- [mapgen.mjs](mapgen/mapgen.mjs) builds maps through the engine WASM's map builder, seeded; presets in [generate.mjs](mapgen/generate.mjs), shapes in [shapes.mjs](mapgen/shapes.mjs).

```
node tools/mapgen/mapgen.mjs list                                  # presets
node tools/mapgen/mapgen.mjs gen donut --seed 3 [--set altar_mode=central] --out x.map26a --show   # north at the top
node tools/mapgen/mapgen.mjs mutate expanse --op "walls*0.5" --op "camps*1.3" --out x.map26a   # mirror-preserving edits
node tools/mapgen/mapgen.mjs check maps maps/gen                   # validity, reachability, metrics
node tools/mapgen/mapgen.mjs diversity maps/gen DIR                # map sets against the ladder maps
node tools/mapgen/mapgen.mjs suite [--out DIR --seed S]            # rebuild maps/gen, or a fresh suite
```

## Forced drafts: tools/variants

The draft is compiled in, so a forced draft is a bot copy in `bots/variants/<name>/` (gitignored). Make variants from hyperion: hecate's `params::test_draft` overrides any forced draft.

```
py tools/variants/make_variant.py varg,willow,ryth                        # drafts under 5 are padded (-pad)
py tools/variants/matrix.py varg,tavi,ryth,stellar,ren willow,ren --one-side   # [BOT@]DRAFT specs; BOT@ = its own draft
py tools/variants/matrix.py --focus --cols hecate@                        # each champion first, + --filler
py tools/variants/matrix.py --resume replays/matrix-TIMESTAMP             # --report: rewrite reports only
```

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

- **bench.py:** `--maps` takes ladder names or paths; `--set wide` is 26 maps (12 ladder, 12 gen, 2 gen-s1); `--test-draft` gives both bots the ladder test compositions; `all` counts play turns from round 2. Wide-set baselines (bbf6f05): `replays/fuel/wide-base-100M.json`, `wide-base-real.json`.
- The 16-game bench swings by ±20 out-of-fuel turns and has no shared-gem map: judge out-of-fuel turns on a full A/B.
- hyperion prints `SHORTCUT round champion what` where fuel made it choose worse and `OOF round phase` for each turn that ran out (both in `debug_block`). `debug_fuel` in util.h gives per-phase costs (`FuelMeter`, ~170 a meter). Where the fuel goes: [FUEL-PROFILE.md](../research/hyperion/FUEL-PROFILE.md).
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

## Ladder replays and scrims

```
py tools/fetch_replays.py --list                      # ladder: rank, rating, record, team id, name
py tools/fetch_replays.py --top 10 --team "Mite"      # newest 20 ranked groups per team
py tools/fetch_replays.py --mine                      # our groups into replays/mine/
py tools/bulk_replays.py                              # unpack replay-bulk-zip/ into replay-bulk/<day>/
py tools/scrim_ladder.py --dry-run                    # top 5 teams x 3 groups: maps and commands, nothing queued
py tools/scrim_ladder.py --teams 5 --sets 3 --seed 7  # asks before queuing (--yes skips)
py tools/scrim_ladder.py --resume replays/scrims/TIMESTAMP
```

- **fetch_replays.py** needs `cambc login` and `--threads 1` (downloads rate-limit). Options: `--kind ranked|unranked|all`, `--since`, `--max-groups N`, `--out` (`replays/ladder/`). Each group gets `<time>-<teamA>-vs-<teamB>-<id>/` with `<n>-<map>.repl26a` and `group.json`.
- **bulk_replays.py** keeps ranked games between two of the day's top 15 teams and deletes each zip once extracted.
- **scrim_ladder.py spends the team's unranked quota** (`cambc match-groups quota`): dry-run first. We are always team A; replays go to `replays/scrims/<timestamp>/`.

## Replay analysis: tools/replay

```
node tools/replay/extract.mjs replays/ladder replays/batch-TIMESTAMP   # decode into replays/.analysis/
node tools/replay/extract.mjs --update-engine                          # after a cambc update
py tools/replay/analyze.py replays/batch-TIMESTAMP --vs replays/ladder --team hyperion   # --reports economy,camps
py tools/replay/ab_compare.py <variant name> batch-A batch-B           # both bots of an A/B in the same games
```

Schema and units: [replay/README.md](replay/README.md).

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
