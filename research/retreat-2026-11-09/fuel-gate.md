# The escape planner's fuel gate (2026-11-09)

Question: the planner (CHANGES 478, `model/escape.cc`) builds only with `params::escape::min_fuel` (50k) left and
runs its slack pass only with `slack_fuel` (40k) left. Lower build gates ran out of fuel (OOF) more often and lost.
Why, and would a smarter gate help?

**Answer: no gate change helps measurably.** The 50k gate is wrong in both directions, but correcting it in either
direction reads level:
- For the walk's ask it is too strict. Planning more of those turns reads level.
- For the dash's ask it is too loose. Planning fewer of those turns cuts OOF turns but reads level or slightly worse.

The planner's remaining gap to its unlimited-fuel 53.1% is ocean's general OOF cost, which the reference pays too.

## Measurement

The instrumented copies are debug builds of `oc-esc-478`: `bots/variants/fg-inst50`, `fg-inst20` (gates 20k/12k)
and `fg-inst-site` (the new gate), all untracked. Checkpoints, all inside `debug_block` and frozen once a turn
resumes late:
- `fuel()` at every step of `retreat()` and `retreat_step`, the end of `act`, `set_turn_order` and the turn's end;
- every plan ask: the fuel at the ask, the build's cost, gated or built, and which caller asked;
- for each OOF turn, the last checkpoint passed.

The patch script is `tools/fg_instrument.py` (`fg_instrument_478.py` patches the old gate), the parsers `tools/fg_parse.py`, `fg_summary.py` and `fg_hazard.py`. Each run is
800 games on a 400-map sample of `merged/retreat-911000b` against `oc-cl2-seat5m`.

Retreat turns at the 50k gate (267k finished in 800 games, ~334 a game):

| Part of the turn | mean | p90 | p99 |
|---|---:|---:|---:|
| turn start to decide | 9.4k | 12.8k | 16.5k |
| decide to `retreat()` | 20.0k | 31.7k | 44.4k |
| `retreat()` | 24.0k | 39.3k | 53.8k |
| after `retreat()` in act (ward, lock, recall feint) | 1.6k | 2.6k | 5.4k |
| `set_turn_order` | 3.6k | 5.7k | 10.5k |
| whole turn without the queue | 59.1k | 81.4k | 93.4k |

- **Builds.** 53% of retreat turns build a plan (141k turns), and 8% have their first ask gated (21.7k).
  - A build costs 9.8k mean, p90 13.3k, p99 17.0k, max 27k (the slack pass 0.3k).
  - The fuel at the first ask is 65.8k mean.
  - The callers' first asks: retreat_step (the walk) 68%, escape_landings (the dash, early in `retreat()`) 32%.
- **What runs after the plan.**
  - From the first ask to the end of act, less the plan: mean 17.6k, p99 37.5k.
  - Most of it is retreat_step's option pricing: 12.9k mean, p99 23.5k.
  - Without a plan (gated turns) the same span is 16.7k mean, so the plan adds almost nothing downstream beyond
    its own cost.
- **What the turn loses.** At 20k/12k, 6,213 OOF turns fell in retreat, against 1,304 at 50k; total OOF turns were
  12,165 against 7,907.
  - 4,580 of them ran out before the move: 2,931 in retreat_step's pricing (add, HomeWalk, full pricing), 673 in
    its avoid checks, 507 among its tries, 358 in the dash or escape branch.
  - Losing the move means a fleeing champion stands still in reach.
  - The rest ran out after the move and lost the ward, lock, recall feint or turn order (881 in act's tail, 250 in
    turn order).
  - At 50k, 889 ran out before the move.

### The hazard depends on the fuel left after the plan, and on the caller

X is the fuel left after the turn's last active build (X = the fuel at the ask less the build). The share of planned
turns that then ran out, pooled over the 20k and 50k runs (oofB: before the move; all: any OOF):

| X | walk ask: oofB | walk ask: all | dash ask: oofB | dash ask: all |
|---|---:|---:|---:|---:|
| 24-26k | 5.3% | 14.3% | 48% | 65% |
| 28-30k | 1.3% | 4.1% | 21% | 34% |
| 32-34k | 0.5% | 1.5% | 10.9% | 18% |
| 34-36k | 0.16% | 0.99% | 6.6% | 10.7% |
| 38-40k | 0.05% | 0.32% | 4.2% | 6.2% |
| 44-46k | 0.01% | 0.06% | 1.6% | 2.3% |
| 52-54k | 0 | 0.01% | 0.73% | 0.95% |
| 58-60k | 0 | 0 | 0.23% | 0.39% |

- **The curves match with and without a plan.** Gated turns, bucketed by their fuel at the ask, run out at the
  same X as planned turns (walk ask: X 25-30k 2.6% against 2.2%; 20-25k 14.6% against 15.0%).
- So lowering the gate lost because a lower gate leaves less for the same work after the plan. The plan creates no
  extra work after it.
- **The dash's ask needs ~18k more than the walk's.** It comes before the dash, the re-read of vision, the reset and
  all of retreat_step. After a dash, retreat_step also builds again at the landing tile, since the cache key holds
  the tile; at 50k that second build was gated on 2,897 of 3,507 turns.
- **The flat 50k gate leaves X ≈ 40k at the mean build.** For the walk's ask that is a hazard of 0.3%, more than
  needed. For the dash's ask it is ~3%.
- **Turns the gate skipped.** 21.7k first asks were gated, at 44.3k median: 17.7k from retreat_step, 4.0k from the
  dash. Most of the walk asks among them would have finished with a plan. A walk ask at 45-50k leaves X ≈ 35-40k,
  under 1% hazard.

## Design (tested, not merged: `tools/fg-site.patch` against oc-esc-478)

Each caller states the fuel its turn still needs after the plan (`plan(..., reserve)`, `want_slack(reserve)`). The
build runs only if the fuel left pays for the reserve plus the build's measured cost.
- **The cost** is a running mean (1/8) of this instance's active builds, measured after the game's one-off static
  boards. The slack pass keeps its own mean. Both follow a cheaper build automatically: if the build drops to 5k,
  every gate drops by ~5k with no edit.
  - A cost read across a turn that ran out and resumed in a later round is discarded; its fuel reads the new budget.
- **The reserves** (params::escape) are the measured 1%-all-OOF points of the table above:
  - `walk_reserve` 35k: retreat_step's ask, before its pricing;
  - `dash_reserve` 53k: escape_landings, before the dash and all of retreat_step;
  - `priced_reserve` 16k: retreat_step's slack pass, after the pricing. 16.4k is the p99 of that tail through
    `set_turn_order`.
- **A plan skipped for fuel is kept as short_of_fuel.** The next ask with the same cache key tries the gate again.
  For example, the walk's ask at the tile where the dash's ask was gated and no dash followed.

The reserves depend on what runs after the plan, not on the build's cost, so a sibling's cheaper build needs no
retune. A change to retreat_step's pricing or the turn's tail would need them measured again (`tools/fg_hazard.py`).

A read-only audit found one real bug, which is fixed: the first version could take a resumed turn's fuel as a
negative cost, which wraps to 2^64 and switches the planner off for the game. With these reserves a build cannot
overrun its turn, and no game showed it. The audit also noted that the mean build, not an expensive one, is
reserved for. That was left: the reserves come from 2k buckets, and the mean's error is ~±3k.

### Second-order effects (debug, 800 games against oc-cl2-seat5m, fg-inst-site against fg-inst50)

- **Plans move from the dash to the walk.** Walk asks gated at 45-50k now plan (+8.3k plans, +9% of walk plans).
  Dash asks under ~63k are now gated (-13.6k, -30% of dash plans), and their dash falls back to the old danger
  ranking. Planned turns: 132k against 141k.
- **OOF turns.** In retreat: 1,277 against 1,304. Before the move: 831 against 889. All turns: 7,624 against 7,907.
  The release screens below show the same: OOF -2 to -4% against oc-esc-478.
- **Per-turn cost.** Retreat turns' fuel is unchanged (58.9k against 59.1k without the queue).

## A/B results

Screens: CAND against `variants/oc-esc-478` (= the shipped ocean), `merged/retreat-911000b`, 10,240 games, release,
fast runner, `--no-test-draft`.

| Variant | dash / walk / priced reserve | win % (95% CI) | OOF CAND | OOF REF |
|---|---|---:|---:|---:|
| fg-site | 53k / 35k / 16k | 49.8 (48.8-50.7) | 112,025 | 114,561 |
| fg-site05 (0.5% hazard) | 57k / 38k / 16k | 49.5 (48.6-50.5) | 109,322 | 113,576 |
| fg-walk (dash ask as before) | 40k / 35k / 16k | 49.9 (48.9-50.8) | 118,774 | 115,671 |

- **All three read level with the shipped gate.** Pooled over 30,720 games they read 49.7 (±0.55). The ±1.0 CIs
  of a 10,240-game screen are the same width as the ceiling for gate work: the whole plan made free reads +0.9
  (EXPERIMENTS, fvb against fva).
- **The dash's ask:** tightening it (fg-site, fg-site05) cuts OOF turns by 2-4% and reads 49.5-49.8.
- **The walk's ask:** relaxing it alone (fg-walk) gives 9% more walk plans and +2.7% OOF turns, and reads 49.9.
- **Each turn the gate flips is worth about as much as the OOF risk it carries.** The plan is a small refinement
  of a move retreat_step already ranks, and a lost move costs about what a few dozen plans gain. The shipped 50k gate
  sits on a flat optimum.
- **No final test was run.** The stop condition holds: in neither direction does a gate change help measurably.
  The 40,960 esc2-dev games were not spent on a candidate that reads level.

## Recommendation

Keep the shipped 50k / 40k gate, and do not merge the reserves. The code (`tools/fg-site.patch`, frozen as
`bots/variants/fg-site` and, with the resume fix, `fg-site2` and `fg-walk`) is kept for this case:
- **When the build gets cheaper** (the build-cost agent's work), the flat gate keeps planning the same turns,
  with the saving left over: OOF turns fall, plans don't rise. That is the safe default.
- **To turn the saving into more plans instead,** apply the patch with `dash_reserve` = `walk_reserve` = 40k. That
  gives X ≈ 40k, the shipped gate's at today's 10k build, and the gate then follows the build's measured cost.
  Screen that against the flat gate on the cheaper build. The tables here say to expect level.
- Other fuel work has more to win than the gate: the ~17k of decide before `retreat()`, retreat_step's ~13k of
  pricing, and the double build after a dash. The cache key holds the tile, so a dash then a walk builds twice;
  at 50k the second build is gated 83% of the time.

## What was rejected, and why

- **Gates below 50k** (f2 30k/20k 50.5%, f3 20k/12k 50.0%, f5 40k/15k 50.6%, against f1's 51.9%): they cost the
  dash's ask its fuel. The table shows a dash plan at X 25-35k runs out 18-65% of the time.
- **A tighter dash gate** (fg-site, fg-site05): it cuts OOF turns 2-4% but reads level to -0.5. A dash plan is
  worth its ~2% chance of running out, and the old gate was close to right for it.
- **A reserve learned online** (a per-instance p99 of the work after the plan): each instance plans only ~50 times a
  game, too few to track a 99th percentile. OOF turns would also be censored samples. The fixed reserves are the
  same measurement made offline over 1600 games.
- **Moving the walk's plan after retreat_step's pricing**, so its gate covers only the tries: the hazard curves
  show the plan adds no work downstream. Only the gate's position would move, and that would rewrite retreat_step,
  which the planner-logic agent owns.
- **Fuel checks inside the build (an anytime build):** these are planner internals, which the build-cost agent is
  rewriting.
