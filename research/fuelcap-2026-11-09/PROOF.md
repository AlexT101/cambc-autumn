# A fuel bound for v87 (v87-nof), 2026-11-09

The user, verbatim: "i would like a full proof and optimisation / pruning of things that don't fit. once everything is proven in fuel cap we can run a normal fuel a/b", and "except some of the stuff will have to be pruned / approximated like limit X search to Y closest camps or something like this so not necessarily identical replays".

- Bot: v87 = `bots/variants/oc-base25`; the candidate is `bots/variants/v87-nof-final`.
- Census: maps-trc, 640 maps (ladder 128 plus gen/mut), both sides, 1280 games, against oc-base25 at the real budget. Fast runner. The segment census (probes) is a debug build; the OOF census is a release build (`benchrel.py`: `cambc build --release` and `run-batch --release`, as A/Bs play), and counts a play turn after round 1 as out of fuel when its `.fuel` trace reads the whole 100k. bench.py's own count reads the engine's stdout line, which release builds don't carry.
- The candidate is `v87-nof-final.patch` (against oc-base25's src; variants are gitignored).
- Tools are in `tools/` here, copied from `~/tmp-offload/nooof/tools/`; their paths still point there. Also there:
  - `tickgrid.py` puts in the tick grid;
  - `benchrel.py` and `runrel.sh` run the release census;
  - `oofcount.py` counts out-of-fuel turns from the `.fuel` traces.
- The census tools:
  - `mkseg.sh` with `gapinst4.py` makes the segment census;
  - `segan.py`, `oofan.py` and `cutan.py` analyse it;
  - `mkdbg.sh` and `one.sh` trace one map.

## The model

A turn is four phases:

| phase | what runs | deadline floor |
|---|---|---|
| W | world update, comms receive, map conditioning | none |
| D | `aph::play_turn`: act, then turn order and support intent | 21000 / 18000 (11000 / 8000 in v87) |
| E | the essential end: claim, bag, priority post, memory | none |
| T | the tail: turn end, comms send, queue | queue only: 12000, started only above 13500 (3000 in v87) |

- **Engine facts** (tools/README.md host prices, probed):
  - A distance-field search is charged `min((layers + 16) * chunks, 40000)`, where chunks is the map's 8x8 chunks (at most 169).
  - A reachable-tiles mask is charged `(count + 2) * span + chunks` and has no cap.
  - `fuel_remaining` is free.
  - Running out suspends the wasm, and it resumes next round.
- **The mechanism** (`util.h`).
  - `checkpoint(need)` throws `FuelDeadline` when `fuel < floor + need`. It is a no-op while the floor is 0.
  - Every stale check (`throw_if_stale`) and fuel gate (`fuel_ok`) is a checkpoint.
  - `tick<4>()` checkpoints on every fourth call.
  - `aph::play_turn` catches the throw, sets the floor to 0, and runs E.
- **The invariant.** Let S0 be the most plain work between two consecutive checkpoints, A the unwind from a throw to the catch, and E the essential end. If `S0 + A + E <= floor`, then D ends with fuel above 0. Two cases:
  - A checkpoint passes. Then at least `floor + need` was left, and the work up to the next checkpoint costs at most `need + S0`.
  - A checkpoint throws. Then at least `floor - S0` was left on entry to that segment, and the unwind and E cost A + E.
- **Heavy leaves carry their price as need.**
  - Fields use `field_need(L) = min((L + 16) * chunks, 40000) + 1500`, with a proven layer bound L (below).
  - Route searches have their cap fitted to what is left (`fit_layers`, an approximation in place of a cut).
  - Uncapped masks are replaced by fields (`flood_into`) or checkpointed at their own price.

## Proven layer bounds (`util.h` LayerBound, `world.cc` make_ally_field / dash_flood)

The static walls W are `blocked_for_us`, or for dashers `dash_walls` and `landing_dash_walls`, both subsets of `blocked_for_us`.

Definitions:
- `R`: the spawn flood's layer count over W (every tile it reaches is within R of the spawn).
- `span`: the spawn rectangle's Chebyshev span.
- `I`: the open tiles the flood misses.

Bounds, each +2 because a field counts one layer past its deepest:
- **Any goal set:** at most `2R + span + I + 2` layers. A tile t and a goal g on the spawn's component are within `d(t,S) + span + d(S,g)` of each other. A goal off it floods at most I tiles.
- **A single goal g on the spawn component:** at most `d(g,S) + span + R + 2`. `d(g,S)` is read off the spawn field.
- **Dash walls (no flood needed):** take `R' = R + x + 1` and `I' = x`, where x is the open tiles off foot. A walk leaves foot for the last time and then crosses only distinct open off-foot tiles.
- **Dash walls once `dash_flood` has run:** `R' = R + past`, where past is the flood's layer count from foot.

The debug builds check every uncapped `make_field` against its bound (`LAYER-BOUND`). The census found no violations (n9, 1280 games).

## Per-part bounds

Each row is either a price fixed by construction, checked before the work as `checkpoint(need)`, or work that resumes across cuts so that a cut costs progress, never correctness.

| part | bound | how | site |
|---|---|---|---|
| distance fields (every `make_field`) | `min((L+16)*chunks, 40000)` with L the proven layer bound | `field_need(L)` checked before the compute | util.h, world.cc |
| route search | the cap is fitted to the fuel left (`fit_layers`), at least 4 layers or a cut | approximation in place of a cut | pathing.cc route |
| dash floods | `R + past` layers from foot | checked at `field_need` | world.cc dash_flood |
| reachable masks | `(count+3)*chunks + 1500` | checked at their price, or replaced by `flood_into` fields (altar walk, walk deaths, rebuild area) | bank.cc, pathing.cc avoid mask |
| bush clusters | batches priced above the floor | `checkpoint(20000)`, then `grow_cluster` stops at the floor | world.cc bush_cluster |
| guarded altars | link by bitboard dilation (at most altars passes), then one altar a step | resumable, checkpoint per altar (was O(n^2) and starved) | altar_guard.cc |
| spawn stands | one column a step | checkpoint per column | altar_guard.cc stands |
| map economy | one group, or 32 members, a step | resumable (`next` kept) | draft/map_economy.h |
| attack-tile index | one member a step | resumable at group boundaries | world.cc index_attack_tiles |
| member attack tiles, label checks | one shadow cast or one changed tile a step | checkpoint per member / tile | pathing.cc attack_tiles, same_labels |
| clear order (`clear_fire`) | 8 members a step; the sort `400*n` (measured 16.5k at 43 members) | checkpoints, need scaled to n | camps.cc |
| order checks, reflect deaths | one moved member / death a step | checkpoint each | camps.cc |
| farm bound tables | 32 groups a step, filled into a local, kept only when whole | checkpoint every 32 | farm.cc stop_from |
| fire on open tiles | one group, one tile a step | checkpoints | bank.cc fire_on_open |
| caches | key or valid flag written only once the value is whole | abort-safe | bank.cc, camps.cc, world.cc hop list |
| every other function | the tick grid: 503 function entries in combat/, economy/, model/ call `tick<4>()` | a checkpoint every fourth entry | tickgrid.py |

Some caches used to set their key before they were filled; a cut then left them wrong for the rest of the game. Those are behaviour fixes as well as fuel fixes: `race_left`, `access_fire`, the prey field, `gems_share`, `own_factors`, the `min_camp_damage` slot, and the hop list.

## The turn ledger

Fuel left at each boundary of a play turn (100k):

- **W** has no floor. Its work is the world update, and it is measured, not bounded: after round 1 it is at most ~36k.
- **D** runs until a checkpoint finds `fuel < floor + need`.
  - A passed checkpoint leaves `floor + need`, and the work it guards costs at most `need + S0`.
  - The cut then costs A. A is measured at p99 2.7k and at most 4.17k, of which ~3.9k is the exception itself.
  - E is at most ~0.5k.
  - The invariant `S0 + A + E <= floor` holds for every segment S0 up to 21000 - 4200 - 500 = **16.3k** in act, and 13.3k in order. At v87's floors the margins were 6.3k and 3.3k.
- **T** is gated:
  - the send runs only above 6000 (it costs at most ~5.3k);
  - the vision re-read runs only above 10000 (it costs at most ~8.6k);
  - the queue runs under its own floor of 12000, which leaves 7.8k for a segment and its unwind. It starts only above 13500, because a throw at its first checkpoint would cost the ~4k unwind for nothing. Before this gate, a queue started at 1500 left could run out on its own throw.
- **Round 1** (200k) follows the same ledger. Its W, the map conditioning, is the large part: ~185k is typical.

Raising the floors is the pruning step. On a turn that reaches the floor, D stops 10k earlier: that turn loses the last 10k of search and support work. The p99 of play-turn fuel falls from 92.5k to 88.9k, and the mean is unchanged at 54.6k.

## Census

The census is release builds on maps-trc (1280 games, each against oc-base25). A play turn after round 1 counts as out of fuel when its `.fuel` trace reads exactly 100000.

| build | what changed | OOF play turns | per 1k | round-1 turns at 200k |
|---|---|---|---|---|
| oc-base25 (v87) | | 12,608 of 6.23M | 2.02 | 469 |
| v87-nof3e | grid, bounds, rewrites | 210 | 0.033 | 8 |
| v87-nof3f | bush-batch checkpoints, queue floor 6000 | 194 | 0.031 | 8 |
| v87-nof3g | mask and label checkpoints, clear-order sort need, hop list abort-safe | 164 | 0.026 | 8 |
| v87-nof3h | floors 16000 / 13000 | 55 | 0.009 | 9 |
| v87-nof3i | floors 21000 / 18000 | 21 | 0.003 | 5 |
| v87-nof3j | queue floor 12000, gated start | 22 | 0.004 | 5 |
| **v87-nof3k = v87-nof-final** | a checkpoint per crowd walk (make_way at spawn: 40k untouched) | **9 of 6.19M** | **0.0015** | **0** |

The debug censuses (bench.py, which counts the engine's stdout line) read 11,651 for v87 and 150-208 for the nof3 line. Debug codegen differs, so those games diverge from the release ones.

Segment census (n12p, a debug build at floor 11000, 128M segments): 34.6k D segments ran ≥ 7000 past their need; 4,820 ran ≥ 11000 and 2,303 ran ≥ 15000. Part of the large tail is self-limited work, which is checked once and then runs to the floor: bush batches, and route caps fitted to the fuel left.

## Not constructed (measured)

- **S0**, the plain work between consecutive checkpoints.
  - The grid guarantees a checkpoint every fourth entry to a ticked function. A loop that calls no ticked function is bounded only where a checkpoint was added by hand.
  - `model/pathing.cc` and `model/world.cc` are outside the grid, because their caches are not all abort-safe. They carry only the explicit checkpoints listed above.
  - S0's bound is therefore the census: the 16.3k margin covers every D segment the census saw except the tail above.
- **A and E** are measured maxima, not constructed.
- **W** (world update, map conditioning) runs with no floor.
- **The 9 residual turns** are deterministic across builds:
  - round 2 of gen-farmland-144001002707 (4 turns) and of mut-gem-caverns-144000017003 (2): first-use builds of static tables;
  - single turns at 00vault r230, 02the-pack r293 and gen-topo-duel-144001007208 r557.
  - The debug replays don't reproduce them, because debug games diverge.
- **Approximations that change play** (allowed by the brief):
  - the route's layer cap is fitted to the fuel left;
  - turns cut 10k earlier at the raised floors;
  - partial work that resumes on the next turn: guarded altars, map economy, the attack index.
