# Charybdis draft fuel — 2026-11-12, CHANGES 523

Worked alone, from CHANGES 522 (`variants/chy-draftfuel-base`, source equal to `chy-psafe`).
The tested candidate is `variants/chy-draftfuel-final`; shipped to `bots/charybdis` and frozen as
`variants/chy-draftfuel-523`. Source hashes, numeric results and coverage counts are in
[results/summary.json](results/summary.json). No behavior exceptions were needed.

## Changes kept

- **Distance buffers:** `mapfeat::Distances` uses an allocator that leaves default-inserted integers
  uninitialized. Every resize consumer writes the entire field before reading it: the SDK export/widen,
  mirrored rows, and travel export. The native BFS still explicitly assigns -1. This removes redundant
  zero-fills across the five map-sized fields, without changing allocation sizes or field values.
- **Sight gap:** compile the 40 sampled-line masks into constants, with exact integer rounding. Try the
  first two/three BFS layers inside one 49-bit word before constructing the full 11x11 search. A path of
  at most three steps cannot leave the 7x7 core. If all targets are reached, their contribution to `far`
  is zero and the original step count is exactly two/three. Otherwise run the original flood. Read the
  four outer rows only for that fallback, and skip sources with no clear targets. The structural budget's
  `Work.sight_steps` is identical, including when the shortcut succeeds.
- **Camp facts:** sort each useful group's `(health, strength)` members once into one flat array, shared
  by every champion's lead estimates, partner clears and the opening planner. Cache attacking/harmless
  health sums and whether the attackers can be kited. Sorting and floating-point accumulation retain
  their original order. Monolith and reward-free groups remain excluded.
- **Empty ward scores:** return no ward immediately when the site's `far` target board is empty.
  `near` is a subset of `far`, so every candidate would score zero. Bush discovery already happened
  before this function; the return omits no deferred map work.

No strategy, search iteration limit, structural allowance, fuel reserve or draft model changed.

## Headroom

Uninstrumented **release** bots, native fast runner, cambc 5.0.1, draft-only self games on all 168 maps
directly under `maps/` plus 5,120 maps in `maps/suites/merged/ocft-1950`, both seats. These are existing
fuel development maps, not a new strength gate. `check.py --plain` reads the complete first turn from
the replay's fuel file, including plan serialization and the pick. Unlike the `firstturn.py` checkpoints,
these figures are not limited to the code before `write_plan`.

| First draft turn, 10,576 observations | Before | After |
|---|---:|---:|
| Median | 3,631,224 | 3,359,726 |
| p99 | 7,363,797 | 6,971,127 |
| p99.9 | 8,327,753 | 7,900,847 |
| Maximum | 8,765,019 | 8,356,306 |
| Buffer below 10M at the maximum | 1,234,981 | 1,643,694 |

The observed maximum falls **408,713 (4.66%)**, increasing the buffer **33.09%**. Every first turn is
cheaper: mean saving **279,887**, range **120,938–653,450**. The same map remains the worst:
`gen-ladder-195001300060`, side B. This is an observed maximum, not a bound for all legal maps.

All 10,576 candidate drafts also finish at the real budget, with all 3/4/5 picks and no cap diagnostics;
the maximum is again 8,356,306. Later draft turns peak at 15,302 (before: 15,283). The small later-turn
overhead comes with the new cache check. The unlimited and real-budget fuel readings can differ by a
few instructions; their full plans, features and picks agree. `firstturn.py --need` independently
reports every analysis finished and none capped (logs in `results/`).

## Exactness and conditional coverage

- **170/170 full-game `bench.py` replays byte-identical at 100M:** 52 wide own-draft, 52 wide matched
  test-draft, 54 heavy, 12 large-group stress. Compare outputs are in `results/compare-*.txt`.
- **47,638 complete 1024-byte draft plans identical**, across every draft round of those 10,576 team
  drafts. All 92 raw features, all structural work counters and every ordered pick also match. The
  candidate at the real budget matches the same baseline plans. Probes use separate copies.
- The bench covers **all 12 champion picks / 13 bodies**, 3/4/5 picks, all symmetries, dense bushes,
  hole paths and the crystal fallback (`05border`). Heavy maps are the 24 largest baseline first-turn
  cases plus border, fracture and the-front. Stress adds six 40/64/100-square maps with 112/208/352-member
  camp groups, each at 3 and 5 picks, from `fc13-largegroups-v2`.
- A separate probe on the **same 59 own-draft bench maps** records 44 two-step sight shortcuts, 35,196
  three-step shortcuts, **2,520 full-flood fallbacks**, and **228 empty ward sites**. Thus both optimized
  and fallback paths are exercised by the full-game bench, not merely by native unit cases.
- The actual-source native oracle, built with AddressSanitizer/UBSan and FMA contraction disabled,
  checks 2,500 random symmetric terrain maps (dimensions 7–100, all symmetries, varied wall/hole/bush
  density). 2,499 are connected; the one disconnected map throws identically. Every feature, work
  counter and 3/4/5-pick team matches, as do 9,996 full travel fields (both sides, dash/crystal).
  This oracle covers the scalar fallback and allocator; the in-engine probes cover WASM SIMD and camps.

Champion-turn fuel is exactly unchanged on wide, test-draft and large-group benches. On the heavy
bench 31 play turns differ in fuel, totaling +1,392 over 11.57G; all replay bytes still match. No strength
claim or live test is needed for these draft-only savings.

After promotion, `bots/charybdis` builds in release and its own 10,576 real-budget draft fuel records
are identical to the tested copy's. A direct main-bot heavy bench also passes **54/54** replay comparisons.

## Earlier lessons and rejected attempts

Read `cambc-rules.yaml`, the tools/API guides, CHANGES 491/506, their EXPERIMENTS entries, the draft
feature/headroom notes, and the Charybdis fuel C/D and older draft-compute reports. Already shipped:
opening-plan trace reuse and memoization, symmetric candidate floods, cheaper attack casts, SIMD
feature input and travel relaxation. Previous ward caches/window bounds and snapshot-copy rewrites
lost on overhead; they were not repeated.

This pass tested the following in copies. Rejected patches are retained in `rejected/`.

- **Whole-frontier host traversal:** replace tile relaxation with bitboard BFS layers at costs 1/4/8.
  Full fields, gains and work counters match on 1,536 team drafts. But dash travel costs +78,728 on
  average, up to +1.32M: whole-map operations per distance layer punish long, sparse frontiers.
- **Only improved frontiers, seeded by baseline distances:** also exact on 1,536 drafts, but the
  baseline-layer bookkeeping costs still more: +298,610 per dash field on average, up to +1.82M.
- **SIMD gain counting after travel:** removes per-pop coordinate work, but pays for every map tile;
  first-turn mean +18,050 over the 10,576 drafts. It helps the largest case by 52k, but 8,938 drafts
  become dearer. Kept the existing sparse count.
- **Reuse transformed feature values / reject unread search suffixes before memo lookup:** together
  save only 574 per first turn over 1,536 drafts, with 542 regressions and a worst +11,847. Not kept.
- **Certify clear sampled lines instead of flooding:** exact on 1,536 drafts; mean -114,191 over the
  full panel, but 42 drafts get dearer. Replaced by the 49-bit BFS, which also handles short detours
  around holes; its initial version saves 142,420 on average with no regressions.
- Isolated buffer changes save 71,406 on average over the full panel, with no regressions. Shared camp
  facts plus empty ward sites save 51,527 on average on the 1,536-draft development subset, all cheaper.
  These component measurements precede the final combined code; do not add them to infer its result.

## Reproduce

`maps.txt` is the 768-map development subset; `all-maps.txt`, `heavy.txt`, `stress.txt` and `coverage.txt`
retain the exact final map lists. Raw compact rows live under `replays/draftlab/chy-draftfuel-*`;
full-game bundles/JSONs under `replays/fuel/chy-draftfuel-*`. Builds and runs share the machine's CPU slots.

```sh
py research/charybdis-draftfuel/tools/check.py bots/variants/chy-draftfuel-base chy-draftfuel-base-all --maps research/charybdis-draftfuel/all-maps.txt
py research/charybdis-draftfuel/tools/check.py bots/variants/chy-draftfuel-final chy-draftfuel-final-all --maps research/charybdis-draftfuel/all-maps.txt
# Add --plain for complete release fuel, or --real for normal budgets; use separate output names.
py tools/draftlab/firstturn.py maps maps/suites/merged/ocft-1950 --bot bots/variants/chy-draftfuel-final --need --jobs 32 --name chy-draftfuel-final
py tools/fuel/bench.py run variants/chy-draftfuel-final --opp variants/chy-draftfuel-base --set wide --jobs 32 --out replays/fuel/chy-draftfuel-final-wide.json
# Repeat for base, then compare; --test-draft tests matched ladder compositions.
py tools/fuel/bench.py compare replays/fuel/chy-draftfuel-base-wide.json replays/fuel/chy-draftfuel-final-wide.json
c++ -std=c++20 -O2 -ffp-contract=off -fsanitize=address,undefined research/charybdis-draftfuel/tools/features.cc -o /tmp/chy-draftfuel-features
/tmp/chy-draftfuel-features
py research/charybdis-draftfuel/tools/summarize.py
```
