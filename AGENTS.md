# Agent guide

## Where to look

Always read `cambc-rules.yaml` if you haven't already. Your next message should mention reading the Cambridge Battlecode rules.

- [cambc-rules.yaml](cambc-rules.yaml): engine-verified declarative ruleset. The source of truth for rules; it overrides `docs/`.
- [docs/api/cpp.md](docs/api/cpp.md): C++ API reference. [sdk/cpp/cambc.h](sdk/cpp/cambc.h) is the SDK header.

Work from these two. Read `docs/` or `rules-verification/` only if they can't answer the question or the user asks.

## Language

The bots are **C++ only**: [bots/aphelios/](bots/aphelios/) and [bots/morgana/](bots/morgana/), which was built from aphelios to play like the top ladder teams (one champion per camp, farming its own half, capture recalls, early retreat from packs, altar locks) and out-farms rather than out-fights. `bots/starter-cpp` is reference only. Frozen snapshots of earlier versions, used as sparring partners, go in `bots/baselines/<name>/` (`vN` for aphelios, e.g. `bots/baselines/v8`; `morgana-vN` for morgana); never edit them. `v8-aggro` is v8 plus chasing the weakest visible enemy within 8 when above half health: a sparring partner that fights, since our baselines rarely do. Ignore `sdk/rust`, `sdk/python`, `sdk/ocaml` and non-C++ pages in `docs/`. Relevant docs, if needed:

- [docs/handbook/](docs/handbook/) and [docs/champions/](docs/champions/): game rules, superseded by the YAML
- [docs/guides/cpp/](docs/guides/cpp/): C++ guides

## Comments

Don't comment unless absolutely necessary. Self-evident code should stand for itself; counterintuitive behaviour or reasoning can get a concise comment.

## Testing bots

[run_batched.py](run_batched.py) builds two bots with `cambc build`, then plays them on every map in `maps/`, once from each side, through `cambc run-batch` (whose own builds fail on Windows):

```
py run_batched.py <bot1> <bot2>      # names under bots/, or paths
py run_batched.py --watch            # live progress of the newest batch, from another terminal
```

Options: `--threads N` (default 16), `--one-side` (one game per map, sides drawn by `--side-seed`), `--maps-dir` (default `maps/`, skipping `maps/gen*/`), `--gen [N]` (play the generated maps in `maps/gen/` instead: all, or N drawn by `--gen-seed`), `--central` (play `maps/gen-central/` instead), `--fuel`, `--timeout SECONDS`, `--no-replays`. Results go to `replays/batch-TIMESTAMP/`: `results.json` (wins from bot 1's view, then per match), `<n>-<map>-<12|21>.repl26a` (`12` means bot 1 is team A), `run.log`, and `*.error.log` for failed matches. The exit code is non-zero if any match failed.

The 9 maps in `maps/` are too few to avoid overfitting, and tournament maps differ, so also test on `maps/gen/` (committed, 120 symmetric maps that load and play to completion). Normally play all of them with `--gen` (240 games): single maps and small samples are too noisy to judge a change. `--gen N --gen-seed S` samples N for quick smoke tests. On 102 of them the nearest altar is on our own side, but on 5 of the 9 ladder maps it is central (and those are where we lose most), so also check `--central`: `maps/gen-central/`, 40 maps (80 games) where each spawn's nearest altar is 0.4-0.6 of the way between the spawns by walking distance (the `altar=` zone in `check`), mutated from collision, elkring, interlock, monolith and corners, from the other ladder maps with their altars moved to the centre, and from presets with `--set altar_zone=mid`. [tools/mapgen/mapgen.mjs](tools/mapgen/mapgen.mjs) builds them through the engine WASM's map builder (seeded, reproducible):

```
node tools/mapgen/mapgen.mjs list                                  # presets (small-brawl, maze, classic, vaults, ...)
node tools/mapgen/mapgen.mjs gen maze --seed 3 [--set picks=5] --out x.map26a --show
node tools/mapgen/mapgen.mjs mutate expanse --op "walls*0.5" --op "camps*1.3" --out x.map26a   # mirror-preserving edits of a map (--op altars=mid centres altars)
node tools/mapgen/mapgen.mjs check maps maps/gen                   # validity, reachability and metrics of any maps
node tools/mapgen/mapgen.mjs suite [central]                       # rebuild maps/gen (or maps/gen-central) from its PLAN (only changed files are rewritten)
```

`cambc run --map NAME` resolves bare names only directly under `maps/`; pass `maps/gen/<file>.map26a` for generated maps.

The draft is compiled in (`params::draft_preference`), so forced drafts are separate bot copies. [tools/variants/make_variant.py](tools/variants/make_variant.py) copies a bot (any snapshot with that array) to `bots/variants/<name>/` (gitignored) with a given pick order; drafts under 5 are padded in enum order (name ends `-pad`) and `manifest.json` records source, git state and draft. [tools/variants/matrix.py](tools/variants/matrix.py) plays variants against each other through run_batched.py, one batch per distinct pair, and writes a win-rate matrix with per-map tables to `replays/matrix-TIMESTAMP/` (`matrix.md`, `matrix.csv`, `cells.csv`, `pairs/`):

```
py tools/variants/make_variant.py varg,willow,ryth --source baselines/v8
py tools/variants/matrix.py varg,tavi,ryth,stellar,ren baselines/v8@willow,ren --one-side   # specs [BOT@]DRAFT, or BOT@ for its own draft
py tools/variants/matrix.py --focus --cols baselines/v8@      # each champion first pick + --filler, vs v8's own draft
py tools/variants/matrix.py --resume replays/matrix-TIMESTAMP # finish unfinished pairs (--report: rewrite reports only)
```

Rows use `--bot` (default aphelios), columns default to the row drafts on `--vs-bot`; run_batched options pass through. Identical row and column entries play mirror matches, reported as team A's win rate: with both sides played, each map should go to the same team twice.

## Competitor replays

[fetch_replays.py](fetch_replays.py) downloads ladder match replays through the site's public API (no sign-in):

```
py fetch_replays.py --list                          # ladder: rank, rating, record, team id, name
py fetch_replays.py --top 10 --team "Mite"          # newest 20 ranked groups per team
py fetch_replays.py --mine                          # all our groups (PTN Hyperion), ranked and unranked, into replays/mine/
```

Options: `--kind ranked|unranked|all`, `--since 2026-10-13`, `--max-groups N` (0 for all), `--out` (default `replays/ladder/`), `--threads`; `--mine` changes the defaults to `all`, 0 and `replays/mine/`, and explicit options still override them. Each five-game group gets a folder `<time>-<teamA>-vs-<teamB>-<id>/` with `<n>-<map>.repl26a` and `group.json` (per-game outcome, sides, draft, gem and champion stats). Groups already downloaded are skipped.

## Replay analysis

[tools/replay/extract.mjs](tools/replay/extract.mjs) decodes replays (ladder and local) with the engine WASM into cached tables under `replays/.analysis/`: per game `meta.json` (teams, draft, result, engine statistics, validation), `events.jsonl.gz` (actions, damage, deaths, captures, tributes, recalls, shopping) and `rounds.json.gz` (per-round champion state and vision), plus shared map files:

```
node tools/replay/extract.mjs replays/ladder replays/batch-TIMESTAMP   # skips games already extracted
node tools/replay/extract.mjs --update-engine                          # refresh engine/ from `cambc view` after a cambc update
```

[tools/replay/analyze.py](tools/replay/analyze.py) turns them into Markdown reports and CSVs under `replays/.analysis/reports/<timestamp>/` (tempo, fights, audits, draft, economy (camp DPS, camp damage, time budget, captures, bags), a camp table, and a gap report for `--team` against `--vs`; `--reports economy,camps` for a quick subset): `py tools/replay/analyze.py replays/batch-TIMESTAMP --vs replays/ladder --team aphelios`.

Schema and units: [tools/replay/README.md](tools/replay/README.md).

## Docs

[docs/](docs/README.md) mirrors the online handbook, champion pages, guides and API reference (all four languages), with images. Regenerate with `cd tools/docs-sync && npm install && node sync.mjs`; never edit by hand. WebFetch can't read the site; use `docs/`.

## Rules verification

Avoid `rules-verification/` unless necessary: its conclusions are already in the YAML. The engine is closed source, so behaviour is settled by probes. [rules-verification/](rules-verification/) holds the engine tests behind the YAML (keep investigation material there): [summary.md](rules-verification/summary.md) (doc conflicts, open questions), [findings.md](rules-verification/findings.md) (evidence) and probe bots in `probes/`. Run probes by path with a large `--fuel`, e.g. `cambc run rules-verification/probes/<A> rules-verification/probes/<B> --map <map> --fuel 50000000`.

Fuel: WASM-side loops, sorting and hashing are costly; host bitboard and distance-field calls are cheap (costs in `findings.md`).

If engine behaviour contradicts the YAML, tell the user immediately. Then confirm it with a probe and update both the YAML and `findings.md`.
