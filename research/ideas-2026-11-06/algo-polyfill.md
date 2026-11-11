# Algorithm polyfills (ocean, 2026-11-06)

The user's idea: `bots/archives/fushia/src/algo/topk.h` replaces `std::sort` and `std::partial_sort` with versions that cost
less fuel; look through ocean (`variants/oc-base10` = `bots/ocean`) for the same kind of saving: sorts, heaps, maps,
allocation, BFS queues, per-turn scans, large memsets, float maths. Exact changes only (bench replays identical to
oc-base10 at 100M).

Files: `/home/ubuntu/tmp-offload/algo/` (`prof-*` raw profiles, `fn*.txt` / `lines-*.txt` / `incl-all.txt` tables,
`bench.sh`, `stages.sh`, `mknoq.sh`, `ab.sh`, `j/` bench JSONs). Variants: `variants/oc-algo-1`, `oc-algo-2`, queue-off
copies `oc-algo-{b10q,1q,2q}`, profiling copies `oc-algo-prof`, `oc-algo-profq` (`CXXFLAGS=-g`).

## What topk.h does

Fuel is 1 per wasm instruction, SIMD included, so it works on whole vectors of 16- or 32-bit integer keys: K <= 16
keeps the K best so far sorted in SIMD registers, and a scan of eight vectors at a time lets through only the keys
that beat the K-th; larger K picks a threshold from 16 sampled keys, moves the keys at or before it to the front and
sorts those with sorting networks and vector merges. Records are sorted as packed keys (`score << 10 | index`), which
also makes every key distinct, so the result is a total order and doesn't depend on how the algorithm breaks ties.
It wins where a bot sorts hundreds of keys a turn (fushia's distance-field top-k).

## Where ocean's fuel goes

Function profiler (`replays/fuel/fc7/prof`, patched fast runner), self-play at the real budget on fuel11's 57 maps.
Line-level from a `-g` build of the same source.

| Turn set | Turns | Mean fuel |
|---|---|---|
| All turns | 514,597 | 49.0k |
| Heavy (>= 95k, OOF continuations merged) | 1,646 | 151k |
| All turns, turn-end queue off (`oc-algo-profq`) | 499,848 | 38.8k |

The turn-end queue (warm-up of static windows, sight masks, viewer rows) costs ~10k of the 49k. It spends spare fuel
down to a floor, also at 100M, so **mean fuel with the queue on hides savings**: a change that makes a warmed item
cheaper warms more tiles in the same fuel. To measure the decision path, both bots are benched with the queue off
(`mknoq.sh`; the queue never changes play, so replays stay comparable).

Decision path (queue off), self fuel per turn:

| Function | /turn | Share | Calls/turn | /call |
|---|---|---|---|---|
| `farm_turn<false,false,false>` + banking `<false,true,false>` | 7,254 | 18.7% | 0.7 | ~10k |
| `World::update_champion` | 2,367 | 6.1% | 15.9 | 149 |
| `World::update_camps` + `update_camp` | 1,854 | 4.8% | 2.1 | ~900 |
| `Pathing::route_around` | 1,001 | 2.6% | 0.6 | 1,558 |
| `set_turn_order` | 952 | 2.5% | 1.0 | 960 |
| `decide` / `play_turn` | 1,389 | 3.6% | 1.0 | |
| `World::read_priorities` | 680 | 1.8% | 1.0 | 678 |
| `Safety::find_members` | 575 | 1.5% | 0.9 | 629 |
| `World::rank_turns` | 493 | 1.3% | 0.4 | 1,107 |
| **powf** | 422 | **1.1%** | 3.0 | 139 |
| `build_windows` + `pick_second` | 691 | 1.8% | 0.6 | ~1.1k |

Below that the profile is flat: 1,300 functions, none above 1%. Inside `farm_turn` the biggest lines are its branch
and bound (`pre_bounds`, the SIMD `PreLanes` blocks, `stop_from`'s binary search over a sorted order): the
algorithmic pruning is already there. `update_champion` and `update_camp(s)` are mostly host-call reads.

### The categories in the brief

| Category | Fuel on the decision path | Heavy turns | Notes |
|---|---|---|---|
| `std::sort`, `stable_sort`, insertion sorts | ~5/turn (0.01%) | ~60 | 9 sites, all on a few items (crew pool, camps left, landing tiles, exposed tiles, options); the profile's `__wrap_iter<unsigned short*>` "sort" is `groups_near`'s copy |
| `priority_queue`, `std::map/set`, `unordered_map` | 0 | 0 | none outside the draft; one `std::deque` (bush clusters, rare) |
| malloc / free | 74/turn (0.19%) | 224 | ~0.3 allocations a turn: buffers are already static and reused |
| memset / memcpy (bulk memory) | ~0 | ~0 | per-function self minus line fuel (bulk charges have no line) is <= 30/turn for every function: no large per-turn fills |
| `memcmp`, `vector::assign` | ~60/turn | ~600 | `altar_usable`'s fire key, `kite_plan`; already memoised behind them |
| BFS / distance fields | host calls already (`distance_field`, `reach_each`, `dilate`, shadow casts) | | `World::walk` falls back to a capped field |
| Per-turn scans | memoised (`Observed`, `kept_efficiency`, `gems_short`, `groups_near`, `home_ground`, `Reach::at`'s memo) | | |
| Float maths | powf 422/turn (1.1%); `sqrtf` is one instruction | 816 | `relative_efficiency` raises each ally's ratio to `efficiency_power` once a round |

So the topk idea has almost nothing to work on in ocean: its sorts, heaps, allocation and bulk memory together are
under 0.5% of the decision path. Seven fuel campaigns already moved the rest into host calls, SIMD and memos.

## Candidates

| # | Site | Est. fuel | Replacement | Exactness risk | Status |
|---|---|---|---|---|---|
| 1 | `relative_efficiency` powf (capture.cc) | ~400/turn | per-ally memo keyed on the input's bits (fuel11 step 1) | none: same input, same call | in oc-algo-1 |
| 2 | turn windows (`build_windows`, `pick_second`) | ~700/turn, 3.2k on heavy turns | keep while every input they read is unchanged; scalar small loops (they were auto-vectorised); `ranks_before` closed form; insertion sort of the unseen (a strict order) (fuel11 step 1) | input list must be complete: checked by identity | in oc-algo-1 |
| 3 | `attack_viewers` | 1.4k/turn (mostly warm-up) | memo per (tile, range 2-4): terrain alone decides it | none | oc-algo-2: saves ~0 (the warm-up already caches viewer rows for the two common ranges) |
| 4 | `sight` near mask of a bush tile | ~200/turn | memo per tile | none | oc-algo-2: ~0 |
| 5 | `rank_turns` | 493/turn | SIMD across ranks, or a memo | memo misses: it runs only when priorities changed; SIMD across ranks costs the same ~50 instructions a member | dropped |
| 6 | `static_window` misses | 2k/turn, warm-up | wider loads | none | dropped: warm-up only (spare fuel), and the row extraction is already ~85 instructions a row |
| 7 | powf for a constant exponent | ~140/call left | musl's powf specialised to y = 1.4653788 | must copy musl's tables and order exactly | dropped: after #1 few calls are left |
| 8 | `World::prune` per observe | ~150-350/enemy/observe on 100x100 | skip when vision and `possible` are unchanged | every write to `possible` would need a version counter (43 sites) | dropped: risk for a small gain |

## Results

100M benches against oc-base10 (def 16, wide 52 with test drafts, pool 128 and heavy 50 against oc-base9):

| Variant | Identity | Fuel, queue on | Decision fuel (queue off, against oc-base10 queue off) |
|---|---|---|---|
| oc-algo-1 (#1, #2) | 246/246 | def -0.35% | def -0.40%, wide -0.33%, pool -0.28%, heavy -0.27% |
| oc-algo-2 (+ #3, #4) | 246/246 | def +0.12%, wide +0.02%, pool +0.13%, heavy -0.00% | def -0.41%, wide -0.33%, pool -0.28%, heavy -0.27% |

oc-algo-2's memos save nothing on the decision path and make the warm-up dearer; oc-algo-1 is the candidate.
Real-budget bench out-of-fuel turns (fuel11's runs of the same source): 2,552 -> 2,552.

A/B, oc-algo-1 against oc-base10, fresh `maps/suites/merged/algo-a` (s620000-620039, `--mix ladder`), own drafts,
fast runner, real budget: **50.3% (49.6-50.9) of 20,480**, out-of-fuel turns 196,767 against 192,923 (+2.0%),
farm-partial-evaluation firings 3.28M against 3.36M (-2.2%). Level, as an exact change should read; with fuel11's
49.7% on fuel11-a, 50.0 pooled over 40,960. A saving of ~0.3% doesn't reduce out-of-fuel turns: those are set by
which branch a turn takes (want_home, the strike search, the farm loop), not by the fuel spent before it.

Recommendation: nothing to merge. Neither change ports to astraeus, which has neither the per-ally powf nor the
turn windows.
