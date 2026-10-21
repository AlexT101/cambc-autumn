# Agent guide

Always read `cambc-rules.yaml` if you haven't already. Your next message should mention reading the Cambridge Battlecode rules.

- [cambc-rules.yaml](cambc-rules.yaml): the game rules, engine-verified; it overrides `docs/`.
- [docs/api/cpp.md](docs/api/cpp.md) and [sdk/cpp/cambc.h](sdk/cpp/cambc.h): the C++ API.
- [tools/README.md](tools/README.md): usage of every script below.

Read the rest of `docs/` (generated; WebFetch can't read the site) or `rules-verification/` only when these can't answer.

## Bots

C++ only; ignore `sdk/rust`, `sdk/python`, `sdk/ocaml` and non-C++ docs.
- **hecate** is the bot we work on: shipped changes in [CHANGES.md](research/hecate/CHANGES.md), direction and the keep rule in [TODO.md](research/hecate/TODO.md).
- **nemesis** is its predecessor.
- Each bot's draft is compiled in (`params::draft_preference`).
- A/B baselines are frozen copies in `bots/baselines/<bot>-vN/`: never edit them, and delete one once the current bots beat it about 80% of the time.
- When copying a bot, leave out `.cambc/`, whose CMake cache breaks the build.

Don't comment unless necessary: only counterintuitive behaviour or reasoning gets a concise comment.

## Testing

```
py run_batched.py <bot1> <bot2>          # every ladder map in maps/, both sides
py run_batched.py <bot1> <bot2> --gen    # the 256 generated maps in maps/gen/
```

- **Judging a change:** there are no feature flags. A/B the change against a frozen baseline on ladder + `--gen` from both sides (582 games, noise about ±2.1 points). Single maps and small samples are noise.
- **Confirming a gain** won on `maps/gen`: test it on a fresh-seed suite (`mapgen.mjs suite --out DIR --seed S`, then `--maps-dir DIR`).
- **Determinism:** local games are deterministic, so rerunning the same maps adds nothing.
- **Recording:** results go in [research/EXPERIMENTS.md](research/EXPERIMENTS.md), which also lists what has already won or lost.
- **Map paths:** `cambc run --map NAME` finds bare names only directly under `maps/` (with their prefix, `00interlock`); pass `maps/gen/<file>.map26a` for generated maps.

## Fuel

Each turn has 100k fuel (the first 200k); running out loses the rest of the turn.
- **No new fuel gates** (code that chooses worse when fuel is short): make work cheap or bounded instead ([FUEL-GATES.md](research/hecate/FUEL-GATES.md)).
- **Fuel-only changes** must leave `tools/fuel/bench.py`'s replays byte-identical.
- **Tracing:** wrap output in `debug_block({ ... });` and run without `--release`. It is then free and the game stays byte-identical; plain printf changes the game. Output lands in the replay zip as `team-a.stdout` / `team-b.stdout`.
- **Costs:**
  - about 1 fuel per WASM instruction, and 1 per byte for memset/memcpy;
  - an allocation ~130, plus ~290 to free;
  - a thrown and caught `cambc::error` ~3.9k;
  - `std::cout` ~11k of static initialisation (use printf).
- **Host calls** are priced flat whatever work they do, so moving a loop into bitboard, field or shadow-cast calls is usually the biggest saving. But per-tile tests beat building a board when only a few tiles are asked about. Prices are in tools/README.md.

## Rules verification

The engine is closed source, so rules are settled by probe bots in `rules-verification/probes/` ([README](rules-verification/README.md): how to run them, and which probe re-checks which rule). If engine behaviour contradicts the YAML, tell the user immediately, then confirm it with a probe, update the YAML and add the probe to the README's table.
