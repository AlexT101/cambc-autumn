# Host calls priced below their work, and what pathing could gain (2026-11-03)

Question: which host imports (or WASM operators) charge little fuel for the computation they do, and can
pathfinding use that? Short answer: several calls are 10-90x underpriced, but the pathing ones are
already what astraeus uses. Pathing is ~8% of all fuel and its host searches ~2-3%; the fuel-only
rewrites found here would save at most ~1-2% of total fuel.

## Prices (cambc 4.0.0; formulas exact, from `tools/fastengine/runner/src/api_defs.rs`)

C = chunks = ceil(W/8)·ceil(H/8). WASM: 1 fuel per operator, SIMD v128 included; `memory.copy` and
`memory.fill` 1 per byte; `memory.grow` free. Bot JIT throughput is ~3.5 fuel/ns (DESIGN.md).

| Call | Fuel |
|---|---|
| DistanceField Compute / ComputeTo | min((L+16)·C, 40000), L = levels expanded |
| Bitboard ReachableMask | (L+2)·span_x·span_y + C; span = chunk columns/rows the *requested* window [p-d, p+d] touches |
| ShadowCast | scan/2 + 2C |
| board_vision_mask, board_ward_vision_mask | 2C, flat |
| whole-board ops, linear/raw import/export | C |
| GetSetBits | C + n |
| DrawChebyshev / DrawCircle | chunk-window area |
| DistanceField Copy | 16C (field bytes / 8) |
| DistanceField Get/Set, Bitboard Test/Set/Toggle, game reads | 0 (bot-side wrapper only) |

## Native cost against fuel

`host-bench.c` calls the engine's own functions in-process (dlopen of a PIE-cleared cambc copy) on
all 86 ladder and `maps/` maps, 200 random open tiles each, walls read from the draft perspective.
"x" = ns·3.5 / fuel: roughly how many times more fuel the same work would cost in bot WASM. It is a
lower bound, since the host is native code. Medians by map size: small ≤25 chunks (30 maps),
mid 26-80 (40), big >80 (16).

| Call | small: ns / fuel / x | mid | big |
|---|---|---|---|
| vision_mask | 1006 / 40 / **90x** | 1140 / 96 / 42x | 1330 / 241 / 20x |
| ward_vision_mask | 782 / 40 / 73x | 32x | 14x |
| export_linear | 270 / 20 / 52x | 43x | 1376 / 120 / 41x |
| draw_chebyshev r8 | 92 / 7 / 47x | 43x | 43x |
| shadow_cast r8 | 1242 / 125 / 33x | 24x | 1623 / 356 / 15x |
| shadow_cast r4 | 22x | 14x | 7.5x |
| df full (Compute) | 4538 / 1016 / 16x | 11x | 32390 / 17354 / 7.3x |
| df_to random goal | 15x | 11x | 7.2x |
| shift_right | 15x | 8.2x | 5.2x |
| reach full | 5.9x | 5.6x | 5.2x |
| reach d8 | 216 / 86 / 8.8x | 237 / 126 / 6.8x | 254 / 203 / 4.3x |
| df_to goal ≤6 away | 432 f / 5.1x | 1000 f / 2.6x | 3216 f / 1.7x |
| df cap 8 | 480 f / 3.1x | 1152 f / 1.9x | 2892 f / 1.1x |
| union | 8.3x | 3.5x | 1.9x |
| get_set_bits | 3.4x | 3.4x | 3.4x |
| df_copy | 0.7x | 0.5x | 0.6x (still 1/8 of a WASM memcpy) |

Notes:
- **Vision is the most underpriced.** vision_mask and ward_vision_mask cost 2C whatever the radius,
  bushes or walls. ShadowCast also charges scan/2.
- **Distance fields are cheap per level** (C per level, i.e. 1 fuel per 64 tiles). The fixed 16C makes
  short or capped searches the worst value: a cap-8 field on a big map is barely below native cost.
- **ReachableMask is priced on the window, not the map.** reach d8 costs 5-15x less fuel than df cap 8
  for the same flood. It gives the reachable set, not distances.
- No call ever reached the 40000 cap in play.

## Where astraeus's fuel goes

The host share comes from an `LD_PRELOAD` hook on cambc's fuel charges. The pathing shares come from
inclusive fuel meters in a scratch copy (`bots/variants/astraeus-pathmeter`, gitignored). Both used
astraeus self-play on 00ambush, 00breadcrumbs, 01big-world, 00swirl, 00pilgrimage and 00interlock:
6 games, both sides, ~3.5B fuel.

Host-charged fuel is 11.7% of the total; the rest is bot WASM. By import:

| Import | Share of all fuel |
|---|---|
| ComputeTo | 2.3% |
| Union | 1.8% (873k calls) |
| Compute | 1.7% |
| ShadowCast | 1.1% |
| Intersect | 0.9% |
| ReachableMask | 0.4% |

Average levels per ComputeTo: 19-24 on big maps, 8-9 on small ones.

Pathing, inclusive (bot WASM plus host):

| Site | Share of all fuel | Calls | Fuel per call |
|---|---|---|---|
| `step_towards(goals)` | 7.7% | 31.7k | 8.2k |
| `route_around` | 6.7% (big maps 7-9%, small 2.4-4%) | 40.7k | 5.6k |
| its `compute_to` (host + wrapper) | 2.2% | 24.6k | 3.1k |
| `occupied_into` (wall board rebuild) | 1.3% | 45.1k | 1.0k |
| `travel` (dash planning) | 1.5% | 17.8k | 2.9k |
| `make_field` | 1.0% | 2.7k | 12.4k |
| `World::update`, for comparison | 12.3% | 61.3k | 6.8k |

## Pathing options, with ceilings

1. **Short single-tile routes by ReachableMask.**
   - Method: reach(goal, cheb(me, goal)), then test(me) (free). If it is reached, the distance is the
     Chebyshev distance. A second reach(goal, d-1) gives the first steps: our neighbours inside it.
   - Cost: ~2·((d+2)·9 + C), against (d+16)·C. On a 169-chunk map at d = 8 that is ~520 against ~4100.
   - Limits: multi-tile goals need a C-priced intersect per probe. A reach cannot be kept as a field
     across turns (`kept_steps`).
   - Ceiling: below the route search's 2.2% (3.5% on big maps), depending on how many routes go to
     one tile.
2. **`occupied_into`: build the per-turn part once.** blocked_for_us, camps, live camps, teleports and
   enemy occupancy, recomputed only where `invalidate()` already is. Each rebuild would drop from ~10
   whole-board ops to ~2-3. Ceiling ~0.9%.
3. **Sight by vision_mask instead of ShadowCast**, where the cast is a champion's sight. This drops the
   scan/2 part, about a third of ShadowCast's 1.1%, so ≤0.4%. First a probe must show the masks equal
   the bot's `walls_and_bushes` cast, radius and bush rule included.
4. **Zero-level searches.**
   - Size: ComputeTo calls whose goals are all walled pay a bare 16C. They are 19% of calls and 8-11%
     of ComputeTo fuel, 0.22% of all fuel.
   - Verdict: not worth a generic precheck. "Some goal is open" costs 2-3 whole-board ops on every
     call, about what it saves.
5. **`search_cost_estimate` = 4000 + C·(20+L)** overstates a search on small maps:
   - with C = 16 it estimates ~4.5k for ~0.5k actually spent;
   - on big maps the overstatement is ~1.8x.
   
   It feeds fuel gates, so correcting it is a behaviour change: judge it by A/B, not as fuel-only.

Options 1-3 are fuel-only if done exactly: `tools/fuel/bench.py` replays must stay byte-identical.
Together they would save ~1-2% of total fuel. That matters only through fuel-gated choices and
out-of-fuel turns, and is well under `ab.py`'s noise as a win-rate effect. The bigger pathing cost is
route_around's own bookkeeping: ~3.4% of fuel outside its search and wall rebuild.
