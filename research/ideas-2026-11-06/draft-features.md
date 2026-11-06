# Draft-side features: the PlanFacts channel (2026-11-06)

The draft's first turn has 10M fuel and a champion's first turn 200k. Map facts and constants that play would
otherwise compute on a champion's first turn are computed in the draft and passed through the 1024-byte draft memory
(`DraftPlan`, written in the draft, read-only in play). Bots: `bots/variants/oc-draftcond` (the channel, frozen),
`bots/variants/oc-draftfin` (the channel, plus the done bit and the draft-finish work). Code: `src/draft/draft.h`
(`PlanFacts`) and `draft.cc` (`measure_facts`, `PlanFacts::write/read`, `condition_on_map`).

## Layout

The draft memory is one bit stream, least significant bit of each byte first:

| Bits | What |
|---|---|
| 82 | `PlanHeader`: check (16, a hash of `current_version` and the map), field layers, flags, Rice parameters, section offsets |
| 1 | `done`: the draft's precompute (`analyse`) finished in its first turn (oc-draftfin) |
| 1 | `present`: the facts follow |
| 56 | facts, if `present`: spawn_dist 14 (16383 = none), altars 10, gems 16, big_gems 16 |
| 5 | n, the number of outputs (at most 31) |
| 16 × n | outputs: constant k of the bot's list is `lo + (hi - lo) * code / 65535` (`PlanFacts::encode` / `decode`) |
| rest | the sections (steps, attack tiles, leads and dash steps, wards, the index at the end): `plan_body_at()` |

Play reads the facts only when the header's check matches the map (`plan_check`). Otherwise, or when `present` is 0,
it measures them on the first turn (`measure_facts`). The values are exact integers, so either path derives the
same doubles (checked 768/768 against oc-base10, and FACTCHECK 4236/4236).

## Adding a field

- **A fact** (a map quantity, known when the facts block is written, right after `StaticMap::build()` in `analyse`):
  1. Add the member and its width to `PlanFacts`, and add the width to `fact_bits`.
  2. Add a range test to `fits()`.
  3. Put it at the end in `write()` and `read()`.
  4. Measure it in `measure_facts` (the first-turn fallback uses the same function).
  5. Bump `DraftPlan::current_version`.

  Use integers, or codes of an exact quantity, never floats computed differently on the two paths.
- **A result found later in the analysis** (a gambit's ambush bush, an altar choice, a hop group): the sections'
  offsets are fixed once the facts block is written, so its length cannot change afterwards.
  1. Reserve a fixed-width slot in the facts block, written as 0 = none.
  2. When the result is known, fill the slot in place: `PlanWriter{plan, slot_at}.put(code, bits)`.

  Tiles take 14 bits (x + 128y, or 16 for a plain index) and groups 8. For dash-kind-dependent results, give each
  dash kind its own slot (kinds 0-2, as `Pathing::static_walls()` distinguishes). Play falls back to computing a
  slot itself when the slot reads 0 or the plan is absent.
- **An output** (a draft-side model's constant):
  1. Set `outputs`, and `output[k] = encode(v, lo, hi)`, before `write()`.
  2. In play, read it with `decode(f.output[k], lo, hi)`, using the same `lo` and `hi`.

  Sixteen bits resolve a range in steps of 1/65535; widen `output_bits` if a constant needs more.

## Byte budget

- The header and facts take 145 bits (18 bytes), plus 2 bytes per output.
- What is left of the 8192 bits goes to the sections. On 768 (map, side) drafts (oc-draftcond, s630410 + ladder),
  the spare bits after every section were: min 1069 (133 B, 00road-of-riches), p10 5433, p50 6778.
- A full stream cuts the sections from the end: first the ward sites that do not fit (they read 0, and play uses
  bush wards), then the index. So every bit a field adds comes out of those, on the few maps where the stream is
  full.
- Budget for the planned additions:
  - 31 outputs at 16 bits: 62 B.
  - Ambush tile and hop group for three dash kinds: 3 × (16 + 8) bits = 9 B.

  Both fit everywhere, with ≥60 B left on the fullest map.

## Fuel: everything must finish in the draft's first turn

- Rule (2026-11-06): all draft precompute fits in the draft's first turn (10M). It must never spill silently to
  later turns or into play.
- `analyse` records whether it finished in round 0 (the `done` bit).
- **Local builds:** every local build (cambc build/run/run-batch, ab.py, bench.py, the draft lab, tune.py; debug or
  `--release`) compiles against `sdk/cpp`, which holds `cambc_local.h`. Bots test for it with
  `__has_include(<cambc_local.h>)` (`util.h` `local_build`). On a missing `done` bit, a local build prints
  `DRAFT-UNFINISHED` and resigns in round 1. With no usable plan, it prints `PLAN-CHECK` and resigns.
- **Ladder:** the platform builds a submission's `src/` against its own SDK, which has no such header, so the bot
  falls back gracefully. Verified: `cambc bundle` holds only `src/`, and the pristine SDK (`cambc init`) has no
  `cambc_local.h`. The bundled oc-draftfin built in a fresh project played an unfinished map to round 596, where the
  local build resigns in round 1.
- **Where failures show up:**
  - ab.py prints `!!! EARLY LOSSES ...` / `!!! BROKEN DRAFT HANDOFFS ...` first and last in its summary, and writes
    `handoff_failures` and `early_losses` to `summary.json` and summary.md.
  - run_batched.py prints a banner and writes `early_losses` to `results.json`.
  - bench.py prints `!!! BROKEN DRAFT HANDOFFS`.
  - tune.py and the draft lab log games over by round 5 per batch.
  - Each tool warns at start if `sdk/cpp/cambc_local.h` is missing.
- **Headroom report:** `py tools/draftlab/firstturn.py MAPS... --bot bots/variants/oc-draftfin --need --jobs 32`
  gives the first turn 10G, so `analyse` always finishes. It prints p50/p99/p99.9/max of the whole first turn's
  fuel, the headroom under 10M and the drafts over it.
  - Run it on the 128 ladder maps plus a few thousand big/huge/maze maps, e.g. `maps/suites/fresh/s630500-11`,
    3072 maps (`node tools/mapgen/mapgen.mjs suite --out DIR --seed S`).
  - In practice the whole first turn must stay under about 9.4M: `analyse` keeps a 500k reserve and checks each
    step's estimate before it starts.

### The last-resort cap (oc-draftfin)

- **When it applies.** In the draft's first turn, every optional part of `analyse`, everything after the steps, starts
  only if the fuel left covers three things over `draft_reserve` (500k):
  - an upper bound on the part's own cost;
  - the index's bound, until the index is written;
  - `cap_margin` (300k).
- **The parts and their bounds:**
  - dash fields: 2 × `field_cost_estimate`;
  - leads: `make_leads`' own estimates;
  - an attack member: 50k (measured at most 14k on average);
  - the index: 250k + 2.5k a group (measured at most 338k at 124 groups);
  - a ward site: 5k + 2k × its box area (measured at most about 1.0 × 5k + 2k a candidate).
- **What a cut does.** It ends that part's section where it is, as a plan cut for room reads, and the analysis goes
  on, so the first turn always finishes. Ward sites left read 0, so play uses bush wards. Attack groups left are
  computed in play.
- **Ladder parity.** A local build prints `DRAFT-CAPPED <sections>` (dash 1, leads 2, attacks 4, index 8, wards 16),
  which ab.py, bench, tune.py and `firstturn.py` count. Nothing prints on the ladder, but the cap cuts there too.
- **Unfinished.** Only the map, the facts, the fields and the steps can still leave a draft unfinished. Those resign
  locally.

### Measured (3200 maps: the 128 ladder maps and s630500-11; 6400 drafts; whole first turn at unlimited fuel)

| Bot | p50 | p99 | p99.9 | max | over 9.5M |
|---|---|---|---|---|---|
| oc-draftcond | 4.15M | 9.99M | 11.97M | 13.86M | 142 |
| oc-draftfin, index before the wards | 4.04M | 9.52M | 11.44M | 13.35M | 72 |
| + unmasked ward scoring, sight_gap blocker table | 3.84M | 9.23M | 11.10M | 12.77M | 49 |
| + SIMD play mask, narrow and sight_gap rows (`firstturn.py --need`, no probe prints) | 3.62M | 8.71M | 10.52M | 12.09M | 10 over 10M |

- The first three rows are measured by a probe whose prints cost ~0.3M on the heaviest maps; the last row by
  `firstturn.py --need`.
- Picks, ward codes and the plan bytes are identical between the oc-draftfin rows (6400/6400).
- The feature passes match draftlab's native parity (3200/3200 maps) and the in-game features of the snapshot
  (`params::draft_parity` FEAT lines, 6400/6400).
- **Features alone** (in-game FEATFUEL, every feature):
  - max 7.60M → 7.24M;
  - p99.9 6.57M → 6.22M;
  - p50 2.24M → 2.15M.
- A neighbour pretest in the clearance BFS lost on the tail (median −8k, up to +170k) and was dropped.
- **At the real budget, final oc-draftfin (6400 drafts):**
  - 6400 finished;
  - 40 capped (0.6%): 34 wards only, 6 wards + index + attacks;
  - 0 of the 256 ladder drafts capped, the ladder's whole first turn at most 8.06M (01big-world);
  - fuel left at the end of the first turn at least 803k (at least 1.92M on the ladder);
  - uncapped drafts' plan bytes are identical to an unlimited first turn's.
- bench.py `--set wide` at 100M: 52/52 replays identical to oc-draftcond.
- Where the fuel goes on the costliest drafts (100x100):
  - The model draft's features, needed before the pick: ~6M, up to 7.9M.
    - clearance BFS ~1.1M
    - dash travel ~1.1M, up to 2.8M
    - sight_gap ~1.0M
    - narrow and the play mask ~0.5M
    - fields, counts and groups ~0.8M
  - Steps: up to 1.0M.
  - Attack tiles: up to 2.1M.
  - Leads: up to 0.6M.
  - Wards: up to 3.3M, about 1.0k a candidate tile and 2.7k a site.
- Even with no wards, everything before them reaches 9.8M on 10 of the 6400 drafts. A cap on the ward search alone
  cannot make every map fit.
