# Agent guide

## Where to look

- [cambc-rules.yaml](cambc-rules.yaml): engine-verified declarative ruleset. The source of truth for rules; it overrides `docs/`.
- [docs/api/cpp.md](docs/api/cpp.md): C++ API reference. [sdk/cpp/cambc.h](sdk/cpp/cambc.h) is the SDK header.

Work from these two. Read `docs/` or `rules-verification/` only if they can't answer the question or the user asks.

## Language

The bot is **C++ only**, in [bots/aphelios/](bots/aphelios/); `bots/starter-cpp` is reference only. Ignore `sdk/rust`, `sdk/python`, `sdk/ocaml` and non-C++ pages in `docs/`. Relevant docs, if needed:

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

Options: `--threads N` (default 16), `--one-side` (one game per map, sides drawn by `--side-seed`), `--maps-dir`, `--fuel`, `--timeout SECONDS`, `--no-replays`. Results go to `replays/batch-TIMESTAMP/`: `results.json` (wins from bot 1's view, then per match), `<n>-<map>-<12|21>.repl26a` (`12` means bot 1 is team A), `run.log`, and `*.error.log` for failed matches. The exit code is non-zero if any match failed.

## Competitor replays

[fetch_replays.py](fetch_replays.py) downloads ladder match replays through the site's public API (no sign-in):

```
py fetch_replays.py --list                          # ladder: rank, rating, record, team id, name
py fetch_replays.py --top 10 --team "Mite"          # newest 20 ranked groups per team
```

Options: `--kind ranked|unranked|all`, `--since 2026-10-13`, `--max-groups N` (0 for all), `--out` (default `replays/ladder/`), `--threads`. Each five-game group gets a folder `<time>-<teamA>-vs-<teamB>-<id>/` with `<n>-<map>.repl26a` and `group.json` (per-game outcome, sides, draft, gem and champion stats). Groups already downloaded are skipped.

## Replay analysis

[tools/replay/extract.mjs](tools/replay/extract.mjs) decodes replays (ladder and local) with the engine WASM into cached tables under `replays/.analysis/`: per game `meta.json` (teams, draft, result, engine statistics, validation), `events.jsonl.gz` (actions, damage, deaths, captures, tributes, recalls, shopping) and `rounds.json.gz` (per-round champion state and vision), plus shared map files:

```
node tools/replay/extract.mjs replays/ladder replays/batch-TIMESTAMP   # skips games already extracted
node tools/replay/extract.mjs --update-engine                          # refresh engine/ from `cambc view` after a cambc update
```

[tools/replay/analyze.py](tools/replay/analyze.py) turns them into Markdown reports and CSVs under `replays/.analysis/reports/<timestamp>/` (tempo, fights, audits, draft, and a gap report for `--team` against `--vs`): `py tools/replay/analyze.py replays/batch-TIMESTAMP --vs replays/ladder --team aphelios`.

Schema and units: [tools/replay/README.md](tools/replay/README.md).

## Docs

[docs/](docs/README.md) mirrors the online handbook, champion pages, guides and API reference (all four languages), with images. Regenerate with `cd tools/docs-sync && npm install && node sync.mjs`; never edit by hand. WebFetch can't read the site; use `docs/`.

## Rules verification

Avoid `rules-verification/` unless necessary: its conclusions are already in the YAML. The engine is closed source, so behaviour is settled by probes. [rules-verification/](rules-verification/) holds the engine tests behind the YAML (keep investigation material there): [summary.md](rules-verification/summary.md) (doc conflicts, open questions), [findings.md](rules-verification/findings.md) (evidence) and probe bots in `probes/`. Run probes by path with a large `--fuel`, e.g. `cambc run rules-verification/probes/<A> rules-verification/probes/<B> --map <map> --fuel 50000000`.

Fuel: WASM-side loops, sorting and hashing are costly; host bitboard and distance-field calls are cheap (costs in `findings.md`).

If engine behaviour contradicts the YAML, tell the user immediately. Then confirm it with a probe and update both the YAML and `findings.md`.
