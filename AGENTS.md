# Agent guide

## Where to look

Always read `cambc-rules.yaml` if you haven't already. Your next message should mention reading the Cambridge Battlecode rules.

- [cambc-rules.yaml](cambc-rules.yaml): engine-verified declarative ruleset. The source of truth for rules; it overrides `docs/`.
- [docs/api/cpp.md](docs/api/cpp.md): C++ API reference. [sdk/cpp/cambc.h](sdk/cpp/cambc.h) is the SDK header.

Work from these two. Read `docs/` or `rules-verification/` only if they can't answer the question or the user asks.

## Language

The bots are **C++ only**: [bots/aphelios/](bots/aphelios/) and [bots/morgana/](bots/morgana/), which was built from aphelios to play like the top ladder teams (one champion per camp, farming its own half, capture recalls, early retreat from packs, altar locks) and out-farms rather than out-fights. morgana is the stronger bot (about 70% against aphelios) and the base for new work; aphelios is kept as a sparring partner. Its ladder draft is a fixed preference order (`params.h`). `bots/starter-cpp` is reference only. Frozen snapshots of earlier versions, used as sparring partners, go in `bots/baselines/<name>/` (`vN` for aphelios, e.g. `bots/baselines/v8`; `morgana-vN` for morgana); never edit them. `v8-aggro` is v8 plus chasing the weakest visible enemy within 8 when above half health: a sparring partner that fights, since our baselines rarely do. `morgana-univ` is morgana (8b0e1b7) rebuilt to play like the #1 ladder team: it strikes first when it can reach, presses an alive-count lead into the enemy half, farms early camps in crews and builds Focus on Ren and Tavi; level with morgana overall but a stronger fighter. `morgana-v5` is morgana before its one-price farm valuation (ec43299 with a fixed draft), the reference for that rewrite. `nemesis-v1` is nemesis at e647cbd, the baseline for changes from the optimality report. [bots/rival/](bots/rival/) is morgana-v5 rebuilt to play like the top five ladder teams (gold camps, team sieges of Monoliths and big shared groups, bolder camp risk, retreat only when hurt or carrying, every bag banked at the finish); it beats morgana-v5 ~60% and morgana (4708870) ~59%. [bots/nemesis/](bots/nemesis/) is rival with fixes found in top-team replays and turn audits, a sparring partner that beats all three: champions leave camps they cannot outlast (finishing_camp summed every awake group; camp deaths fell ~70%), wait at most 5 rounds for a camp to return (10: -4.5%), give way to packs in their own half (retreat ratio 2 there; aphelios packs won most fights in our half), recall from captures to shop, hit the deadliest camp member first, keep the siege target and split Monolith bags, and stun enemy tributes that would win. On ladder+gen+central, both sides (2026-10-17, ad900b7 bots): 55.9% vs rival (morgana 43.1%), 65.9% vs morgana (rival 56.9%), 86.4% vs aphelios (morgana 79.7%); on a fresh suite pair 61.8/61.0/85.7% against 43.8/56.2/81.5%. Ignore `sdk/rust`, `sdk/python`, `sdk/ocaml` and non-C++ pages in `docs/`. Relevant docs, if needed:

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

The 17 ladder maps in `maps/` are too few to avoid overfitting, and tournament maps differ, so also test on `maps/gen/` (committed, 132 symmetric maps that load and play to completion; suite seed 5301, rebuilt 2026-10-18 after tuning on seed 3107). Normally play all of them with `--gen` (264 games): single maps and small samples are too noisy to judge a change. `--gen N --gen-seed S` samples N for quick smoke tests. On 106 of them the nearest altar is on our own side, but on 11 of the 17 ladder maps it is central (and those are where we lose most), so also check `--central`: `maps/gen-central/` (suite seed 5302; 3108 before), 46 maps (92 games) where each spawn's nearest altar is 0.4-0.6 of the way between the spawns by walking distance (the `altar=` zone in `check`), mutated from collision, elkring, interlock, monolith and corners, from the other ladder maps with their altars moved to the centre, and from presets with `--set altar_zone=mid`. Both suites include maps with no ordinary gem camp, as on the ladder maps contest and stampede (12 in `maps/gen`, 6 in `maps/gen-central`): on half, the only gem sources are Monoliths, one to three per side (the `monolith-only` preset and mutations of contest); on the other half, it is one large group on the symmetry axis shared by both teams (the `shared-gems` preset and mutations of stampede). Every other camp on them is gold-only. [tools/mapgen/mapgen.mjs](tools/mapgen/mapgen.mjs) builds them through the engine WASM's map builder (seeded, reproducible):

```
node tools/mapgen/mapgen.mjs list                                  # presets (small-brawl, maze, classic, vaults, ...)
node tools/mapgen/mapgen.mjs gen maze --seed 3 [--set picks=5] --out x.map26a --show
node tools/mapgen/mapgen.mjs mutate expanse --op "walls*0.5" --op "camps*1.3" --out x.map26a   # mirror-preserving edits of a map (--op altars=mid centres altars)
node tools/mapgen/mapgen.mjs check maps maps/gen                   # validity, reachability and metrics of any maps
node tools/mapgen/mapgen.mjs suite [central]                       # rebuild maps/gen (or maps/gen-central) from its PLAN (only changed files are rewritten)
```

A change picked because it won on `maps/gen` and `maps/gen-central` looks better there than it is, so confirm the size of a gain on suites with a fresh seed (`suite gen --out DIR --seed S`, then `--maps-dir DIR`). For example, crews won +15/240 and +7/80 on the committed suites but +4/240 and +4/80 on fresh ones.

`cambc run --map NAME` resolves bare names only directly under `maps/`; pass `maps/gen/<file>.map26a` for generated maps.

The draft is compiled in (`params::draft_preference`), so forced drafts are separate bot copies. [tools/variants/make_variant.py](tools/variants/make_variant.py) copies a bot (any snapshot with that array) to `bots/variants/<name>/` (gitignored) with a given pick order; drafts under 5 are padded in enum order (name ends `-pad`) and `manifest.json` records source, git state and draft. [tools/variants/matrix.py](tools/variants/matrix.py) plays variants against each other through run_batched.py, one batch per distinct pair, and writes a win-rate matrix with per-map tables to `replays/matrix-TIMESTAMP/` (`matrix.md`, `matrix.csv`, `cells.csv`, `pairs/`):

```
py tools/variants/make_variant.py varg,willow,ryth --source baselines/v8
py tools/variants/matrix.py varg,tavi,ryth,stellar,ren baselines/v8@willow,ren --one-side   # specs [BOT@]DRAFT, or BOT@ for its own draft
py tools/variants/matrix.py --focus --cols baselines/v8@      # each champion first pick + --filler, vs v8's own draft
py tools/variants/matrix.py --resume replays/matrix-TIMESTAMP # finish unfinished pairs (--report: rewrite reports only)
```

Rows use `--bot` (default aphelios), columns default to the row drafts on `--vs-bot`; run_batched options pass through. Identical row and column entries play mirror matches, reported as team A's win rate: with both sides played, each map should go to the same team twice.

## Fuel

Each turn has 100k fuel (the first 200k), and nemesis cuts decisions short when it runs low. [tools/fuel/bench.py](tools/fuel/bench.py) measures fuel per turn and checks fuel optimisations: with its default 100M budget no fuel gate trips, so a change that only saves fuel must leave every replay byte-identical. Use the small default map set; hundreds of maps are not needed for that check.

```
py tools/fuel/bench.py run nemesis --out replays/fuel/base.json          # 16 games vs rival, 8 maps, both sides
py tools/fuel/bench.py run variants/x --out replays/fuel/x.json
py tools/fuel/bench.py compare replays/fuel/base.json replays/fuel/x.json  # identical replays, fuel change
py tools/fuel/bench.py run nemesis --fuel 0 --out replays/fuel/real.json  # the real budget: counts shortcuts and lost turns
```

nemesis prints a `SHORTCUT round champion what` line wherever fuel made it choose worse (`note_shortcut` in util.h), inside `debug_block`, so it is free in local builds and absent from release ones; `--fuel 0` sums them. Set `debug_fuel` in util.h for per-phase costs (`FuelMeter`; each meter costs ~170 fuel itself). Cost model: about 1 fuel per WASM instruction, memset/memcpy 1 per byte, an allocation ~130 plus ~290 to free, a host bitboard operation ~1 per 8x8 chunk plus ~15 (~185 on 100x100), a full distance field ~26k on 100x100, a thrown and caught `cambc::error` ~3.9k, `std::cout` ~11k of static initialisation (use printf). The draft bot fills `DraftPlan` (draft.h, 1024 bytes) with static map data the champions would otherwise compute: per-group walking steps from both spawns and every altar, and attack tiles.

## Competitor replays

[fetch_replays.py](fetch_replays.py) downloads ladder match replays: listings come from the site's public API, but since 2026-10-17 replay bundles need a signed-in session, so it falls back to `cambc matches download` (run `cambc login` first; the endpoint rate-limits, so use `--threads 1`):

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
