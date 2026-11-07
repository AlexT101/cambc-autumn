# Fuel campaign 12, agent B: economy, pathing and world upkeep (ocean)

Copy: `bots/variants/oc-fuel12-b` (oc-base13 plus one change). Bench tag `b1` (frozen as `variants/oc-fuel12-b1`, same src).

## Kept change

### b1: relative_efficiency computes its powers only when an input changes

- **File and function:** `economy/capture.cc`, `relative_efficiency`.
- **Idea:** the function runs again whenever the round or our gold changes, which happens on most farm turns. Each run took `std::pow(e / mean, efficiency_power)` for every ally, about 200 fuel a `powf` and about 1k a run. Every efficiency comes from `kept_efficiency`, which is memoized per ally and rarely changes. Now the per-ally efficiencies, the ally count and the mask of counted allies (alive or self) are compared with the last run's, and the powers are rebuilt only when one of them differs.
- **Why it is exact:** the output depends only on those inputs. The mean is computed from the same values in the same order, and `pow(e / mean, p)` is the same float sequence as the old `rel /= mean; rel = pow(rel, p)`.
  - Efficiencies are at least 1 times a positive rate, so they are never NaN or -0, and `==` on the floats is identity.
  - A team has at most 5 picks (rules `picks`), and the key has room for 8.
- **Consumers:** farm's `per_gold` (the f.s.prices segment) and `holder_value` (capture).

#### Identity at 100M against `base-<set>-100M.json`

`bench.py compare` reports "identical games" on all six sets.

| Set | Total fuel | Mean | p90 | p99 | Max | Round 1 mean |
|---|---|---|---|---|---|---|
| def | -0.86% | 53206 → 52755 | 86591 → 86541 | 99626 → 98980 | 219512 → 218551 | +0.0% |
| wide | -0.79% | 51856 → 51445 | 86471 → 86417 | 107211 → 106803 | 286819 → 286068 | +0.0% |
| pool | -0.77% | 55825 → 55300 | 87140 → 87098 | 111592 → 110713 | 374122 → 373161 | +0.0% |
| big | -0.82% | 63950 → 63426 | 87683 → 87647 | 105831 → 105172 | 321720 → 320824 | +0.0% |
| heavy | -0.73% | 52854 → 52467 | 87286 → 87238 | 119834 → 119204 | 341265 → 340648 | +0.0% |
| td | -0.69% | 55378 → 54992 | 86984 → 86948 | 104380 → 103946 | 242519 → 241605 | +0.0% |

- About 400 fuel a play turn on average.
- Round 1 does not change (+11 fuel from the key), since the first run computes every power anyway.
- Coverage: all six sets hit the function on every farm turn. It has no branch tied to a map class or a champion.

#### Real budget (benches diverge: direction only)

| Set | OOF play turns (base → b1) | farm-partial-evaluation (base → b1) |
|---|---|---|
| pool | 855 → 875 | 19368 → 19097 |
| big | 317 → 307 | 8483 → 8143 |
| heavy | 790 → 781 | 10657 → 10399 |
| td | 393 → 280 | 7316 → 6165 |
| total | 2355 → 2243 (-4.8%) | |

These games diverge, so the totals are noisy. The A/B below is the number to use.

## A/B

`ab.py variants/oc-fuel12-b1 variants/oc-base13 --no-test-draft --suites maps/suites/merged/fc12-b --name fc12-b-b1`: 10,240 games on fresh ladder-mix suites 910100-910119, at the real budget. `oc-fuel12-b1` was a frozen copy with the same src as `oc-fuel12-b`.

- **Win rate:** 50.3% (5148-5092), 95% CI 49.3-51.2. That is level, as a fuel-only change should be.
- **Out-of-fuel turns:** 82513 → 78933 (-4.3%), in 7558 → 7443 games.
- **Failures:** no failed matches and no broken draft handoffs. DRAFT-CAPPED is 78 games for both.

Shortcuts by kind (`SHORTCUT` lines, both sides of every game; tally script `/home/ubuntu/tmp-offload/fc12b/sc.py`, run inside the batch dir):

| Kind | REF | CAND | Change |
|---|---|---|---|
| farm-partial-evaluation | 1366683 | 1305949 | -4.4% |
| step-guard-entry | 827102 | 819745 | -0.9% |
| prey-cut-short | 216503 | 218994 | +1.2% |
| turn-order | 187330 | 177821 | -5.1% |
| step-guard-look | 92248 | 92203 | -0.0% |
| out-of-fuel | 82513 | 78933 | -4.3% |
| comms-stale-vision | 65712 | 62541 | -4.8% |
| farm-no-route | 30588 | 29310 | -4.2% |
| static-descend | 26885 | 25604 | -4.8% |
| crow-flies-farm | 14081 | 13701 | -2.7% |
| siege-route-fuel | 4380 | 4281 | -2.3% |

## Measurements (where the fuel goes)

The method was a debug copy with `cambc::fuel_remaining()` differences in `debug_block`s, dumped per champion. The diff is in `/home/ubuntu/tmp-offload/fc12b/meas-copy.diff`. Numbers are self-play at 100M on 20 maps (8 heavy, 4 big, 8 pool), as fuel per play turn.

### World::update

| Part | Fuel a turn | Detail |
|---|---|---|
| champions | ~2.4k | each visible ally ~390, self ~340, hidden enemy ~98 (4.2 a turn), tracked hidden enemy ~1.6k (0.24 a turn) |
| camps | ~2.3k | |
| priorities | 0.64k | |
| rank | 0.5k | max 1.8k; runs only when stale |
| altars | 0.43k | |
| vision | 0.36k | |
| scores | 0.16k | |

- observe costs ~1.3k a call, at 0.64 calls a turn.

### Farm's f.s.prices segment

| Part | Fuel | Calls a turn |
|---|---|---|
| relative_efficiency's recompute | 1.78k a call: kept loop 0.75k, powers 1.0k | 0.64 |
| prices() | ~0.7k a call: gems_share 0.2k, main_stat 0.11k; the best_emblem recompute 3.5k | recompute 0.03 |

### Round 1, all 137 maps, first turns

| Part | Fuel |
|---|---|
| prices()'s first best_emblem | 4.4k |
| relative_efficiency | 3.9k: gold_efficiency 385 an ally, powers 1.0k |
| hidden enemy tracking at the update | 7.0k: one dasher grow ~2.9k, one walker grow ~0.9k, the rest lineage copies (board copies, ~0.4-0.9k each on big maps) |
| ally updates in observe | 3.2k |

On round 1 in the real-budget census, the OOF first turns (12% of first turns) spend:

- 97k in world: static_camps 23.7k, ally_spawn_field 18.8k (one full field), init_beliefs 12.1k, crossings 9.4k;
- 10.2k in f.s.prices;
- 14.3k in siege_kite;
- 23.6k in farm.post (p.walk 11.4k, p.tiles 10k).

The static build has already been taken down to host calls (SIMD member sums, one set_tile a member).

## Tried and dropped

- **Disabling vectorisation in `rank_turns`'s `rank_by` loop** (`#pragma clang loop vectorize(disable)` on the n <= 8 lanes): it is dearer, 481 → 507 a turn at 100M.
- **A memo of `rank_turns` on its input priorities:** dropped unbuilt. It only runs when `read_priorities` found the rank bits changed, so a memo would almost never hit.
- **Skipping observe's update of allies hidden since the full update:** this is exact, since nothing it checks changes within our turn. Dropped as too small: ~79 fuel a call, ~1.7 calls on observe turns.
- **Sharing round-1 grows across enemy types:** the lineage memo already shares them within a type (enemies are fixed at spawn at {1, -1}). Dashers and walkers grow differently, and the copies left are board copies.
- **Other candidates that are already memoized or at the host-call floor** (no exact saving found): `gems_share`/`gems_short` (keyed by bag_key), `main_stat`, `update_camps`/`camp_settled` (settled groups cost one awake read), `route_around` (failed-search reuse, kept routes, spares), the static camp build, and `make_ally_field` (a single full field).

## Merge notes

- **Files touched:** `economy/capture.cc` (relative_efficiency) only. Nothing outside my area.
- **Interactions:** none. Agent A's areas don't read `relative_efficiency`.
- **Divergences:** none at 100M (all six sets byte-identical). No fuel-read switch was involved.
- **Tools left behind:** a census copy of oc-base13 with farm segment scopes, `bots/variants/oc-fuel12-bcen` (f.s.*, f.t.*, p.* scopes on farm_turn). The measurement copy was deleted; its diff is kept as noted above.
