# astraeus_teacher: unlimited fuel and wip accuracy fixes

Created from `bots/astraeus` at `8c0343f5ebc7e73e200d2701ea246ebcec2906fd`.
Accuracy changes were merged from `bots/astraeus_wip` (last bot change
`5b66bde03`, CHANGES 401), using `57194754` as their common source base.
Astraeus was not edited. After the port and regression fix, `astraeus_wip` was
removed at the user’s request; its source remains in git history and its hashes
are recorded in `sources.json`.

## Port

The teacher carries the wip assumption fixes from CHANGES 362–401, including:

- Walking distances for capture races, crews, support, combat reach, intercepts,
  tribute races, lock-aware banking, and paired champions' handoffs.
- Capture shares, remainder and Prospector accounting; Capture hold history;
  shields and cooldowns on arrival; awake-camp fire before the first attack.
- Shared camp targeting by distance and turn order, including channel arrivals;
  pathing invalidation after a camp dies during the turn.
- Combat simulation with actual spell/basic reach, first-turn movement affecting
  second-turn sight, Heart of Ruin health scaling, camp retargeting, and heals.
- Escape landings that account for terrain and unseen threats, and shop estimates
  keyed by income and remaining horizon with damage-weighted healing trips.

This includes wip's lock resets and share-based tribute deadlines, which were
withdrawn from the normal-fuel astraeus in CHANGES 411. The teacher port follows
the request to include all wip assumption fixes.

Current astraeus's draft5 model, tuned constants, gold-efficiency allocation,
emblem fight value, reveal ward, recall repricing and recall-feint fixes remain.
The draft and play share astraeus's health reserve. The old crew radius constants
are removed because wip's crew availability uses arrival times.

## Unlimited computation

Fuel predicates and fuel-dependent early exits are removed, including partial
farm evaluation, guard and priority skips, deferred vision refresh, route funding,
draft preparation, and bush/field preparation. The end-of-turn warm-up queue is
removed; caches are populated on demand. Stale-turn recovery remains a crash guard.

The strike search has no node or exact-query budget. Plan leaves grow as needed;
all 64 possible enemy-removal sets fit the frontier, and spell-center alternatives
fit the complete casting window. Local unit/group masks are widened to 128 bits
and their storage covers every tile in the radius-five window. Camp wakers grow
as needed, and unseen targets fit all six bodies' admitted possibilities. These
replace the old 14-unit, 16-group, 48-member, 24-unseen and 512-leaf truncations.
Legal action depth, uncertainty policy and strategic scoring remain.

Long enemy walks use complete fields after the short-walk cache, unseen reach
beyond the cached layers uses a field, support formation searches the full map,
and camp approach searches can cover every map tile. Exact caches and dominance
pruning remain.

## Unequal-fuel runner

`tools/teacher_ab.py` runs the teacher under
`FASTRUNNER_UNLIMITED_BOTS=astraeus_teacher`, with `FASTRUNNER_MODE=native`.
The fast runner selects the bot by its directory name, including frozen copies.
It meters actual work for the replay's `.fuel` files, but never suspends that bot
for fuel and replenishes its lifetime store fuel. `fuel_remaining()` reports
`INT64_MAX`. The opponent's program and normal metering remain unchanged,
including draft/champion first-turn multipliers and exhaustion/resumption.

This replaces `cap_variant.py` for teacher A/Bs: that older helper patches the
opponent and leaves a resumed remainder temporarily uncapped. The new mode is
native-only and works in debug and release builds.

```sh
python3 tools/fastengine/runner/scripts/check_unlimited.py
python3 tools/teacher_ab.py astraeus_teacher astraeus \
  --maps maps/teacher-20261106 --name astraeus-teacher-v1-10k --seed 861000
```

## Validation and benchmark

The dedicated runner check passed: normal native output matches stock byte for
byte (replay, fuel and stdout); a bounded-work probe completes in its own turn
with unlimited fuel on either side, while the unchanged opponent exhausts fuel.
Teacher builds passed. Four full smoke games on corners and ambush, both sides,
completed with zero teacher fuel exhaustions or shortcut reports. They are a
correctness check, not a strength estimate.

The benchmark uses exactly 5,000 maps sampled without replacement (seed 861000)
from 5,120 new ladder-mix maps generated with seeds 861001–861020. Each map is
played from both sides: 10,000 games, both bots on their own drafts, no early stop.
The input map hashes and runner hash are recorded in
`replays/ab/astraeus-teacher-v1-10k/teacher.json`; both bot sources are frozen by
the standard A/B harness.

Completed **10,000/10,000 games**, with no failed matches. The teacher won
**4,738 (47.38%)** and lost 5,262; 95% Wilson interval **46.40–48.36%**.
Teacher fuel exhaustions: **0**. Astraeus fuel exhaustions: **46,484 turns in
6,195 games**. Wall time: 174.6 seconds, using the shared CPU-slot pool.

This initial build was weaker because the merge omitted crew-index bookkeeping.
The diagnosis and fix below supersede that build. Its results remain in
`summary.json` / `summary.md`, source hashes in `sources.json`, and provenance
in `inputs.json`.


## Regression diagnosis and fix

The wip `crew_allies()` reader filled the ally records but did not populate
astraeus’s newer `claiming[]` / `n_claiming` index. The retained optimized farm
code iterated that index in `crew_work()` and its claimed-group bound. It therefore
read zero allied work after building the crew table, even when allies were
already claiming the camp. The no-table path and `plan_crew()` still saw those
allies, so two parts of the same valuation disagreed. The teacher overvalued
joining camps that allies would finish before it arrived and repeatedly changed
its target.

The fix resets and rebuilds the index with the ally records. It keeps wip’s exact
walks, availability calculation, arrival fire and all other assumption changes.
It does not restore computation limits or the end-turn warm-up. A separate fix
checks an ally’s current visibility before turn-order evaluation reads its shield:
our own move can hide an ally that was visible at turn start. That error reproduced
at rounds 816 and 1317 on `gen-classic-86100101018`, team B; the visibility fix
removed the turn-order errors across the original 10,000-game suite.

Every completed A/B below uses 10,000 games against unchanged, normal-fuel astraeus,
with own drafts, native fastrunner, both sides, and no early stop. Diagnostic rows
use the same 5,000 maps as v1; these are paired ablations, not independent confirmations.

| Candidate | Wins | Win rate |
| --- | ---: | ---: |
| Initial teacher | 4,738 | 47.38% |
| Unmodified astraeus, generous fuel control | 5,273 | 52.73% |
| Teacher with old search budgets | 4,730 | 47.30% |
| Teacher with current-visibility fix | 4,735 | 47.35% |
| Teacher with original combat planner | 4,731 | 47.31% |
| Teacher with original crew calculation | 5,325 | 53.25% |
| Teacher with original shop pricing | 4,717 | 47.17% |
| Teacher with eagerly warmed caches | 4,728 | 47.28% |
| Teacher with original crew recruitment policy | 4,772 | 47.72% |
| Original crew calculation plus exact walks | 5,343 | 53.43% |
| **Teacher with crew index fixed (current)** | **5,248** | **52.48%** |

The fuel control uses a per-bot 10,000,000 quantum and exhausted fuel zero times.
This avoids passing `INT64_MAX` to the original bot’s int-valued fuel-derived
search budgets. All other candidates use true unlimited fuel. The corrected
runner’s default stock parity and both asymmetric modes passed
`check_unlimited.py`. One earlier stock-planner attempt failed to build during
API adaptation; it played no games and is excluded.

The index fix gains **5.10 percentage points** over v1 on matched games; its
paired interval (map as the cluster) is recorded in `ablations.json`. The fixed
teacher logged **811,771** crew joins versus v1’s **4,820,383**, over comparable
numbers of turns; the original-crew control logged 812,541. V1’s 70 capped stdout
files make its count a lower bound. The fixed build has no capped files in either
final run. These diagnostic counts support the target-switching explanation;
the paired win-rate comparison measures the effect.

## Confirmation

The exact fixed source (`replays/frozen/a299d95209c9/astraeus_teacher`) won
**5,262 / 10,000 = 52.62% (95% Wilson 51.64–53.60%)** on the newly generated
ladder-mix suites `maps/teacher-confirm-20261106/862001` through `862020`,
sampling 5,000 maps with seed 862000. Teacher fuel exhaustion and failed matches
were both **zero**; the normal opponent exhausted fuel 42,591 times in 6,136 games.
The original-map fix run was **52.48% (51.50–53.46%)**, also with zero failed
matches and zero teacher fuel exhaustion.

A content-hash audit found three generated layouts repeated from the diagnostic
suite despite distinct generation seeds. Excluding their six games leaves
**5,258 / 9,994 = 52.61% (51.63–53.59%)** on unseen layouts. Both actual benchmark
runs still contain exactly 10,000 games. Details: `confirmation-overlap.json`.
No strategy was tuned on the confirmation results.

Final evidence: `fixed-summary.*`, `confirmation-summary.*`, `fixed-sources.json`,
`fixed-inputs.json`, `confirmation-inputs.json`, `fixed-crew-metrics.json` and
`final-runtime.json`. `compare.py`, `crew_metrics.py` and `summarize.py` reproduce
the analyses from the local replays. The source bot astraeus is unchanged.

For a finite fuel control, `teacher_ab.py --teacher-fuel N` sets
`FASTRUNNER_BOT_FUEL=teacher-directory:N`; the default remains unlimited.
The runner applies the quantum per program, including first-turn multipliers
and fuel-exhaustion resumption, without patching the opponent.


The final replay audit records no teacher turn-order exceptions and five games
with a caught visibility error during action selection (normal opponent: 93 games
with caught errors). These are recovered action errors, distinct from failed
matches. The teacher’s largest recorded turn used 12,091,657 fuel, including draft
turns. Its 165 `farm-kept-target` log entries follow a fully searched unreachable
route; no remaining fuel predicate triggers that fallback.
