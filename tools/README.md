# Tools

Usage details for the scripts AGENTS.md points to. The scripts in the repo root (`run_batched.py`, `fetch_replays.py`, `bulk_replays.py`, `scrim_ladder.py`) are covered here too.

## run_batched.py

Builds two bots with `cambc build`, then plays them on every map in `maps/`, once from each side, through `cambc run-batch` (whose own builds fail on Windows).

```
py run_batched.py <bot1> <bot2>      # names under bots/, or paths
py run_batched.py --watch            # live progress of the newest batch, from another terminal
```

- **Options:**
  - `--threads N` (default 16);
  - `--one-side`: one game per map, sides drawn by `--side-seed`;
  - `--maps-dir` (default `maps/`, skipping `maps/gen*/`);
  - `--gen [N]`: the generated maps in `maps/gen/` instead, all of them or N drawn by `--gen-seed`;
  - `--fuel`, `--timeout SECONDS`, `--no-replays`.
- **Results** go to `replays/batch-TIMESTAMP/`:
  - `results.json`: wins from bot 1's view, then per match;
  - `<n>-<map>-<12|21>.repl26a` (`12` means bot 1 is team A);
  - `run.log`, plus `*.error.log` for failed matches.
- The exit code is non-zero if any match failed.

## tools/ab.py

The full A/B: CAND against REF through run_batched.py on every suite, both sides, wins counted from CAND's side.

```
py tools/ab.py orch/my-branch main --name my-change     # two git refs
py tools/ab.py HEAD hecate                              # a ref against hecate (hyperion at the 2026-10-21 session start)
py tools/ab.py main HEAD~1 --no-test-draft --suites ladder,gen    # each on its own compiled-in draft
```

- **CAND / REF:** a git ref (branch, sha, `main`), whose `bots/hyperion` (`bots/hecate` in commits before the rename) is exported with `git archive` (never the working tree) to `bots/variants/ab-<name>-<cand|ref>-<sha7>/` with `params::test_draft` set to true; or a bot directory under `bots/`, used as it is. Refs resolve in the shared repo, so worktree branches work; run it from the primary checkout.
- **Options:** `--name` (default `<cand>-vs-<ref>`), `--threads` (default 22), `--suites` (default `ladder,gen,fresh`: `maps/`, `maps/gen/`, and each `maps/gen-s*/`; a directory of maps also works), `--no-test-draft` (leave copies untouched, so each plays its own draft), `--fuel N`.
- **Debug builds:** games always run local (non-`--release`) builds. `--phases` also turns `debug_phases` on in the copies that have it, so the same run gives out-of-fuel paths for `tools/fuel/oof_phases.py`; those copies then spend about 1% more fuel.
- **Output:** a summary of at most 25 lines: CAND's win % with a 95% Wilson interval overall and per suite, failed matches, out-of-fuel turns per bot (`oof.py`) and wall time. `replays/ab/<name>/` gets `summary.json`, `summary.md` and each suite's run_batched log; batches go to `replays/batch-<time>-ab-<name>-<suite>/`.
- The exit code is non-zero if any match failed.

## Maps and tools/mapgen

`maps/` holds the 35 ladder maps under the names SDK updates ship them with (`00ambush`, `01big-world`, ...). Delete any uuid-suffixed copies an update adds. Ladder replays name maps without the prefix, and extract.mjs and mapgen accept either.

`maps/gen/` (suite seed 7207) is 256 symmetric maps that load and play to completion. Every camp group, altar and the enemy spawn is reachable on foot.
- 165 come from exotic presets: shaped playable areas, mazes, spirals, pillars, Voronoi cells, tunnels, city blocks, corridors, open fields and long thin maps, with varied spawns and economies.
- 58 come from ladder-like presets, including `monolith-only` and `shared-gems`.
- 33 are mutations of ladder maps.
- Every preset varies `altar_mode`: each spawn's nearest altar is central on 129 maps and on our own side on 127.
- `maps/gen/index.json` records each map's preset, spec, metrics, `kind` and nearest ladder map.

[mapgen.mjs](mapgen/mapgen.mjs) builds maps through the engine WASM's map builder (seeded and reproducible). Presets are in [generate.mjs](mapgen/generate.mjs), shapes in [shapes.mjs](mapgen/shapes.mjs).

```
node tools/mapgen/mapgen.mjs list                                  # presets
node tools/mapgen/mapgen.mjs gen donut --seed 3 [--set altar_mode=central] --out x.map26a --show
node tools/mapgen/mapgen.mjs mutate expanse --op "walls*0.5" --op "camps*1.3" --out x.map26a   # mirror-preserving edits (--op altars=mid centres altars)
node tools/mapgen/mapgen.mjs check maps maps/gen                   # validity, reachability and metrics
node tools/mapgen/mapgen.mjs diversity maps/gen DIR                # map sets against the ladder maps
node tools/mapgen/mapgen.mjs suite [--out DIR --seed S]            # rebuild maps/gen from its PLAN, or a fresh suite
```

`show` prints north (+y) at the top, without row labels.

## Forced drafts: tools/variants

The draft is compiled in (`params::draft_preference`), so a forced draft is a separate bot copy.
- [make_variant.py](variants/make_variant.py) copies a bot to `bots/variants/<name>/` (gitignored) with a given pick order. Drafts under 5 are padded in enum order (the name ends `-pad`); `manifest.json` records the source, git state and draft.
- [matrix.py](variants/matrix.py) plays variants against each other through run_batched.py, one batch per distinct pair. It writes a win-rate matrix to `replays/matrix-TIMESTAMP/`.
- Rows use `--bot` (default hyperion); columns default to the row drafts on `--vs-bot`.
- Identical row and column entries play mirror matches, reported as team A's win rate.
- hecate's `params::test_draft` overrides any forced draft, so make variants from hyperion (the default `--source`).

```
py tools/variants/make_variant.py varg,willow,ryth
py tools/variants/matrix.py varg,tavi,ryth,stellar,ren willow,ren --one-side   # specs [BOT@]DRAFT, or BOT@ for its own draft
py tools/variants/matrix.py --focus --cols hecate@       # each champion first pick + --filler, vs hecate's own (test) drafts
py tools/variants/matrix.py --resume replays/matrix-TIMESTAMP # finish unfinished pairs (--report: rewrite reports only)
```

## Fuel: tools/fuel

```
py tools/fuel/bench.py run hyperion --out replays/fuel/base.json          # 16 games vs hecate, 8 maps, both sides, 100M fuel
py tools/fuel/bench.py run variants/x --out replays/fuel/x.json           # a modified copy of hyperion
py tools/fuel/bench.py compare replays/fuel/base.json replays/fuel/x.json  # identical replays, fuel change
py tools/fuel/bench.py run hyperion --fuel 0 --out replays/fuel/real.json # the real budget: counts shortcuts and lost turns
py tools/fuel/oof.py replays/batch-A replays/batch-B replays/batch-C       # out-of-fuel turns per bot in run_batched.py batches
py tools/fuel/oof_phases.py replays/batch-A replays/fuel/games/real        # the same turns by Phase path (batches, bundle dirs or bundles)
py tools/fuel/oof_costs.py replays/batch-A --by-champion                  # what spent those turns' fuel, and that of turns over 60k
```

- hyperion prints `SHORTCUT round champion what` wherever fuel made it choose worse (`note_shortcut` in util.h), and `OOF round phase` for each turn that ran out. Both are inside `debug_block`.
- With `debug_phases` on in util.h, the OOF line ends `path=decide/chase/prey`, the `Phase` scopes it ran out in. Phases cost about 1k fuel a turn in local builds (+2.7% on the bench at 100M fuel, identical games), so games change while it is on; off, the build is byte-identical.
- `debug_phases` also prints, for a turn that ran out, `OOFCOST round champion total=N phases=N path=inclusive[/self] ...` (paths 3 deep, entries from 1000 fuel) and `OOFSELF ...` (self fuel by Phase name at any depth). With `debug_big_turns` on as well, a turn that spent over 60k without running out prints the same as `BIGTURN ...` (entries from 2000). Those are many: turn off the SRCH (plan.cpp `debug_search`), SLOT and D lines in that copy, or a team's stdout reaches its 1 MiB cap. `oof_costs.py` gives each path's mean and p90 fuel and its share of the turn, per champion with `--by-champion`.
- The bench's 16 games swing by about ±20 out-of-fuel turns and include no shared-gem map, where a third of them happen. Judge out-of-fuel turns on a full A/B with `oof.py`.
- Set `debug_fuel` in util.h for per-phase costs (`FuelMeter`, ~170 fuel per meter).

Measured host prices (50x50, 2026-10-19):

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

## Competitor replays

[fetch_replays.py](../fetch_replays.py) downloads ladder replays. Listings come from the site's public API. Bundles need a signed-in session, so it falls back to `cambc matches download`: run `cambc login` first, and use `--threads 1` because the endpoint rate-limits.

```
py fetch_replays.py --list                          # ladder: rank, rating, record, team id, name
py fetch_replays.py --top 10 --team "Mite"          # newest 20 ranked groups per team
py fetch_replays.py --mine                          # all our groups (Pantheon) into replays/mine/
```

- **Options:** `--kind ranked|unranked|all`, `--since 2026-10-13`, `--max-groups N` (0 for all), `--out` (default `replays/ladder/`), `--threads`.
- Each five-game group gets `<time>-<teamA>-vs-<teamB>-<id>/` with `<n>-<map>.repl26a` and `group.json`. Groups already downloaded are skipped.
- [research/SUBMISSIONS.md](../research/SUBMISSIONS.md) tells our versions apart in `replays/mine/`.

`py bulk_replays.py` unpacks bulk day exports from `replay-bulk-zip/` into `replay-bulk/<day>/`:
- It keeps only ranked games between two of the day's top 15 teams (Bradley-Terry, `ranking.json`).
- It deletes each zip once extracted; `ledger.json` remembers what was done.

[scrim_ladder.py](../scrim_ladder.py) plays our live submission against top ladder teams through `cambc match-groups create`.
- **It spends the team's unranked quota** (`cambc match-groups quota`), so run `--dry-run` first.
- The requester is always team A.
- Replays go to `replays/scrims/<timestamp>/`, with `summary.json`.

```
py scrim_ladder.py --dry-run                        # top 5 teams x 3 groups of 5: maps and commands, nothing queued
py scrim_ladder.py --teams 5 --sets 3 --seed 7      # asks before queuing (--yes skips); --no-wait, --no-download
py scrim_ladder.py --resume replays/scrims/TIMESTAMP
```

## Replay analysis: tools/replay

```
node tools/replay/extract.mjs replays/ladder replays/batch-TIMESTAMP   # decode into replays/.analysis/; skips games already done
node tools/replay/extract.mjs --update-engine                          # refresh engine/ after a cambc update
py tools/replay/analyze.py replays/batch-TIMESTAMP --vs replays/ladder --team hyperion   # reports; --reports economy,camps for a subset
py tools/replay/ab_compare.py <variant name> batch-A batch-B batch-C   # both bots of an A/B in the same games, after extracting
```

- extract.mjs writes, per game, `meta.json`, `events.jsonl.gz` and `rounds.json.gz`.
- analyze.py writes tempo, fights, audits, draft, economy and camp reports, plus a gap report.
- Schema and units are in [replay/README.md](replay/README.md).

## Docs: tools/docs-sync

`cd tools/docs-sync && npm install && node sync.mjs` regenerates `docs/`. Never edit `docs/` by hand.
