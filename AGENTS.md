# Agent guide

## Where to look

- [cambc-rules.yaml](cambc-rules.yaml): engine-verified declarative ruleset. The source of truth for rules; it overrides `docs/`.
- [docs/api/cpp.md](docs/api/cpp.md): C++ API reference. [sdk/cpp/cambc.h](sdk/cpp/cambc.h) is the SDK header.

Work from these two. Read `docs/` or `rules-verification/` only if they can't answer the question or the user asks.

## Language

The bot is **C++ only**, in [bots/aphelios/](bots/aphelios/); `bots/starter-cpp` is reference only. Ignore `sdk/rust`, `sdk/python`, `sdk/ocaml` and non-C++ pages in `docs/`. Relevant docs, if needed:

- [docs/handbook/](docs/handbook/) and [docs/champions/](docs/champions/): game rules, superseded by the YAML
- [docs/guides/cpp/](docs/guides/cpp/): C++ guides

## Testing bots

[run_batched.py](run_batched.py) builds two bots with `cambc build`, then plays them on every map in `maps/`, once from each side, through `cambc run-batch` (whose own builds fail on Windows):

```
py run_batched.py <bot1> <bot2>      # names under bots/, or paths
py run_batched.py --watch            # live progress of the newest batch, from another terminal
```

Options: `--threads N` (default 16), `--one-side` (one game per map, sides drawn by `--side-seed`), `--maps-dir`, `--fuel`, `--timeout SECONDS`, `--no-replays`. Results go to `replays/batch-TIMESTAMP/`: `results.json` (wins from bot 1's view, then per match), `<n>-<map>-<12|21>.repl26a` (`12` means bot 1 is team A), `run.log`, and `*.error.log` for failed matches. The exit code is non-zero if any match failed.

## Docs

[docs/](docs/README.md) mirrors the online handbook, champion pages, guides and API reference (all four languages), with images. Regenerate with `cd tools/docs-sync && npm install && node sync.mjs`; never edit by hand. WebFetch can't read the site; use `docs/`.

## Rules verification

Avoid `rules-verification/` unless necessary: its conclusions are already in the YAML. The engine is closed source, so behaviour is settled by probes. [rules-verification/](rules-verification/) holds the engine tests behind the YAML (keep investigation material there): [summary.md](rules-verification/summary.md) (doc conflicts, open questions), [findings.md](rules-verification/findings.md) (evidence) and probe bots in `probes/`. Run probes by path with a large `--fuel`, e.g. `cambc run rules-verification/probes/<A> rules-verification/probes/<B> --map <map> --fuel 50000000`.

Fuel: WASM-side loops, sorting and hashing are costly; host bitboard and distance-field calls are cheap (costs in `findings.md`).

If engine behaviour contradicts the YAML, tell the user immediately. Then confirm it with a probe and update both the YAML and `findings.md`.
