# Ocean fuel improvements (2026-11-10, CHANGES 503)

Reference: Ocean 502. Measurements use cambc 5.0.1 and the native fast runner.
The objective was fewer exhausted turns and shortcuts; average fuel was secondary.

## Changes kept

- Reuse ability-range viewer windows for basic attacks; calculate adjacent bush
  connectivity with a packed 3x3 mask. Use capped distance fields for the static
  radius-four terrain dilations and reject enemies beyond maximum strike reach
  before constructing their geometry.
- Cache static escape terrain windows; read live camps separately. Chase plans
  omit unused first-move tables. Once a chase runner has taken one hit, compute
  only its zero-hit future paths because the answer is capped at two hits.
  Retreat plans omit first-move dash tables when no dash can be cast now.
- Key farm attack-tile caches by camp state and version, removing the old
  256-member limit. Alive groups use geometry_version; other states require the
  health version because they can retain positive unseen member health.
  Ally arrival caches depend on geometry_version rather than health amounts.
- Cache map dimensions and chunk counts once per instance.
- Raise the non-quiet turn-order reserve from 10k to 12k; retain the 6k quiet
  reserve. Draft10 and strategic parameters are unchanged.

## Results

| Measurement | Games | Exhausted turns REF → CAND | Change | Shortcuts REF → CAND |
|---|---:|---:|---:|---:|
| Fresh paired debug bench | 4,096 | 27,710 → 24,267 | **-12.43%** | 1,225,630 → 1,194,571 (**-2.53%**) |
| Fresh release A/B | 4,096 | 25,939 → 23,665 | **-8.77%** | compiled out |
| Standard release A/B | 1,280 | 7,463 → 7,188 | **-3.68%** | compiled out |
| Development paired bench | 4,096 | 27,841 → 24,841 | **-10.78%** | 1,240,620 → 1,200,655 (**-3.22%**) |

The fresh maps were reserved until selection. Fresh bench mean fuel falls 1.44%;
paired 95% bootstrap CIs are -15.76..-9.14% for exhaustion and -4.12..-0.97% for
shortcuts. Excluding five pairs with stdout capped at 1 MiB still gives shortcuts
-2.33%. Runner counts include consecutive exhausted turns; shortcut counts exclude
OOF recoveries and malformed SLOT lines. Both arms use matched draft modes.

Fresh release wins: 2,061/4,096 (50.32%, CI 48.79–51.85). Standard release:
663/1,280 (51.80%, CI 49.06–54.52). No failures, early losses or broken/capped drafts
in all 5,376 release games. The 10% point-estimate target is met in the paired
bench; the release gain is smaller.

## Correctness checks

At 100M fuel, 93/96 ordinary and 105/108 conditional replays are byte-identical
to 502. Coverage includes all 13 champion bodies, matched 3/4/5-pick drafts,
40/64/100 maps and camp groups of 112/208/352 members. The six exceptions are the
existing fuel-dependent next-turn preparation coupling: all disappear in paired
diagnostics omitting only prepare_next_turn. That omission is not shipped.
The final cleanup matches the tested core's replay bytes and every draft/play
fuel sample in all 204 games.

Cache oracles recomputed at least 15,360 attack-tile hits and 14,336 arrival hits
without a mismatch. The escape oracle reran the complete recurrence over 19,599
retreat builds and 53,305 chase builds: no result mismatch or read of an omitted
table. All 256 adjacent bush configurations passed the packed-mask equivalence
check. First draft turn across 640 standard maps: max 9,385,011 / 10M, none over.

## Lessons and rejected changes

- An earlier bundle's 13.23% exhaustion reduction on the screen became only 1.88%
  on fresh maps. Small means and small screens did not predict the expensive tail.
- A 15k turn-order reserve reduced development exhaustion 11.86% but increased
  shortcuts 3.16%. Restricting it to two nearby enemies was weaker than the kept
  12k reserve. Rechecking late-action fuel between optional steps added little.
- Warming every escape window raised average fuel about 2.8% and worsened the
  combined result. Keep the static cache without broad prewarming.
- Ending the backward escape recurrence when all paths vanish was exact but
  cost 10 more fuel on average and 97 more on heavy turns: checks rarely paid off.
- Geometry versions alone were incorrect for non-alive camp attack caches.
  Cache keys must follow what consumers actually read, including unseen health.
- Raw SDK-storage reads, generic rank caches, larger route histories and tiny
  memo tables repeated earlier failures: lookup, copying and invalidation costs
  outweighed savings. Extra farm reserve erased shortcut gains for little benefit.
- Exact turn-order prunes saved only 13 mean / 90 heavy fuel and were left out.
  Recovery labels misattributed queued work; the instrumented census identified
  the actual exhausted scopes and the under-reserved turn-order tail.
