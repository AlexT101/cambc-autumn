# Constant tuning (SPSA, fast runner, no compiles)

```
python3 research/diana-2026-11-03/tunify.py bots/BOT [NAME...]   # once: chosen params.h constants -> a patchable block
python3 tools/tune/tune.py init --run R --bot bots/BOT --opps variants/a,baselines/v67,... [--maps 64 --pairs 4]
python3 tools/tune/tune.py run --run R --hours 6                  # resumes; touch replays/tune/R/STOP to end after a batch
python3 tools/tune/tune.py status --run R
python3 tools/tune/tune.py play --run R --games 4000              # current values vs defaults, one scored batch
python3 tools/tune/tune.py apply --run R --out bots/variants/BOT-R # a copy with the current values as its defaults
```

- **No compiles per candidate.** `tunify.py` turns each chosen `inline constexpr float|int NAME = V;` into a reference
  to `diana_tune.f[i]` / `.i[j]`, a global behind a 16-byte magic (`src/tune.h`, list in `src/tune.json`). `patch.py`
  rewrites that block in the release wasm and in the fast runner's cached native library and wasmtime module for it
  (both hold the wasm's data segment verbatim), saved under the patched wasm's cache hash (`fnv128`, as runtime.rs).
  A patched candidate plays byte-identical replays and fuel to a fresh build of the same values (checked 2026-11-03:
  0.4 s against 15.7 s for the native compile). Its cache files are deleted after its batch (`patch.forget`).
- **Games.** Release builds (`--release`, as the platform). Each iteration draws `maps_per_iter` maps from the pool
  (default ladder, `maps/gen`, `maps/gen-s1`, `maps/suites/fresh/fresh-92001..92100`), plays each against every opponent with a
  random side, and every candidate plays exactly those games (common random numbers). All of an iteration's games are
  one `fastrunner run-batch` holding a CPU slot per game, so other jobs keep their fair share (`CAMBC_SLOT_WEIGHT`
  scales ours). Per-game stats come from `--statistics` camstats (`cambc summary`); replays are deleted.
- **Score**, from the tuned bot's side, balanced around 0: `win * (+1/-1/0) + gems * (ours - theirs) / (ours +
  theirs)` of tributed gems `+ gold *` the same of earned gold; weights in `config.json` (default 0.7 / 0.2 / 0.1).
- **SPSA** in the [0, 1]-scaled space of each range (`config.json` `params`: `[lo, hi, kind]`, default half to double
  the default, fractions below 0.95, ints at least +-2): `pairs` sign vectors a batch, gradient from each pair's
  paired score difference, `a_k = a / (k + 1 + A)^0.602`, `c_k = c / (k + 1)^0.101`. `config.json` is re-read every
  iteration, so ranges, gains, weights and games can be changed while it runs. `history.jsonl` has every iteration
  (means, x); `games.jsonl` has every game (an iteration a line: its names, sign vectors `deltas`, per-name `cn`,
  `games` as [map, opponent, side], each candidate's per-game score), about 40 KB an iteration at 64 maps x 4
  opponents, for map-conditioned analysis (research/ideas-2026-11-05/mapcond.md).
- **Judge the result** with a normal A/B (`apply`, then `ab.py` on suites the pool never used, `--no-test-draft`):
  the tuning score is against its panel, on its pool.

The single reviewed [504 economy/crew/shop run](../../research/ideas-2026-11-10/tune504/README.md) adds an exact-site source map for selected constants outside params.h, preserves mutable map-conditioned defaults, exports ordinary constants, and checks source/config/map seals. Its isolated launcher schedules default/export release100M identity, fixed600-iteration100k training, and a first200k exported-candidate gate. It acquires fair shared slots for metadata parsing too. This is an explicitly authorized one-off protocol, not an automatic tuning chain.
