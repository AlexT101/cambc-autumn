# Charybdis fuel, 2026-11-13

Worked alone, starting from charybdis 527 at `e3e127c1d`.
The independent pursuit change, charybdis 528 at `c047d10b1`, is preserved in
the final candidate and its reference. No draft, reserve, search budget or
strategic threshold is changed.

Shipped as **charybdis 529**, frozen at `variants/chy-fuel-529`. Its source
matches the tested `variants/chy-fuel528-oneturn` and release copy. The
concurrent 528 pursuit fix is preserved; the user explicitly confirmed that
no additional A/B was needed for concurrent bot changes.

**Independent confirmation meets the target.** On 4,096 fresh games, release
exhaustion falls **12.22%**, 30,821 → 27,056. Debug bench exhaustion falls
**12.95%**, 33,813 → 29,433, and shortcuts fall **7.35%**, 2,346,213 → 2,173,803.
Mean fuel falls 1.09%. Release wins are 50.34% (48.81–51.87%); no failed games,
broken/capped drafts or losses by round five.

## Changes

`variants/chy-fuel528-oneturn` contains:

- Prism premium: cache the exponential by its actual horizon, since different
  gem amounts usually have the same win horizon. Reject non-Prisms before
  reading their bags. Calculate farming premiums after the post-combat return
  to an existing target; the farm memo contexts still advance before that return.
- Emblem pricing: share the build, upkeep basis, baseline value, best stat
  emblem and passive price across the pins of one `best_emblem` call.
- Altar stands: filter camp members once by the triangle-inequality reach
  bound before testing each possible stand.
- Ward placement: retain completed site geometry, remember exact negative
  searches with no allied wards in placement range, and select the best
  candidate without sorting all candidates. Refused placements still try
  the remaining candidates in the original order, including draft-site ties.
- Camp retreat: settle low-health cases and adjacent open exits without
  building the escape field.
- Threats: a visible champion that has acted, a stunned champion, or a
  teleport landing after this round cannot act twice before our next turn.
  Queries needing only that predicate avoid building enemy turn windows;
  queries needing the exact number retain the original calculation.

The bounded ward caches affect retention only. Entries are exact-key checked;
site geometry is retained only after all required bush clusters are complete.
Large maps retain the uncached/fallback paths. Cache storage does not construct
hundreds of boards or thousands of records on the first turn.
The shop and altar changes adopt and verify the existing
`research/fuel-2026-11-13/patches/02-shop-memo.diff` and `01-stands.diff`.

## Method and artifacts

All games use cambc 5.0.1 and the native fast runner. Both sides use their own
drafts, except the explicit forced-composition coverage runs. Bench defaults
to 100M fuel for identity; real-budget runs pass `--fuel 0`. Exhaustion counts
come from runner `Out of fuel: A ... B ...` lines, which include consecutive
exhausted turns. Stdout recovery markers and bench's inferred count miss those.
Shortcuts exclude exhaustion and malformed `SLOT` suffixes.
The ordinary benches hold the opponent fixed at 527 for both candidates and
references; release A/Bs directly pit the final candidate against 528.

`bench.sh` reproduces the runs. Full bench JSON, replay bundles and runner logs
are under `replays/fuel/chy527/`. Frozen copies are under `bots/variants/`.

- Wide identity: bench's 26 ladder/stress maps, both sides (52 games).
- Development: 512 fresh ladder-v2 maps, seeds 5271310–5271311, both sides
  (1,024 games); `maps-dev.txt`.
- Conditional coverage: 54 maps, both sides (108 games), with the all-champion
  prior from `research/fuel-2026-11-10-fourth/tools/coverage-prior.json`.
  Includes large/shared camp groups, monoliths, bushes, teleports and map
  sizes 40/64/100. `maps-cov.txt` is the exact manifest.
- Independent confirmation: 2,048 unused ladder-v2 maps, seeds
  5271410–5271417, both sides (4,096 games); `maps-final.txt`.
- Release A/Bs are separate from debug bench: `chy-fuel528-combo1-screen`
  and `chy-fuel528-oneturn-final` under `replays/ab/`.

`measure.py` reproduces the final numbers and bootstraps whole maps, keeping
both sides together. Compact evidence is in `results/bench-final.json` and
`results/release-final.json`. The 95% intervals are -15.97..-9.95% for debug
exhaustion, -8.57..-6.08% for shortcuts, and -15.44..-9.09% for release
exhaustion. Debug play turns increase 0.44%; per-turn exhaustion falls 13.34%
and shortcuts fall 7.76%. The point estimates exceed 10%; the exhaustion
intervals include gains slightly smaller than 10%.

## Development evidence

Against frozen 527, 1,024 paired real-budget debug games:

| Candidate | Exhausted turns | Shortcuts | Interpretation |
|---|---:|---:|---|
| Reference | 8,142 | 601,278 | |
| Premium horizon | 8,136 | 598,511 | Exact; small alone |
| Economy bundle | 7,809 | 592,185 | Premium, shop, altar stands |
| Large negative-ward cache | 9,627 | 595,578 | Rejected: ~50k first-use initialization |
| Compact negative-ward cache | 7,624 | 592,536 | Retained in bundle |
| Late premium calculation | 7,691 | 594,963 | Retained in bundle |
| Ward selection | 7,585 | 588,532 | Retained in bundle |
| Ward site boards + selection | 7,716 | 587,535 | ~1,150 fuel saved on matched >100k turns |
| Bundle 1 | 7,615 | 571,979 | -6.47% exhaustion, -4.87% shortcuts |
| Bundle + at-most-one-turn predicate | 7,251 | 568,345 | -10.94% exhaustion, -5.48% shortcuts |

The last row's paired-game bootstrap 95% intervals are -16.85..-5.43% for
exhaustion and -8.26..-2.93% for shortcuts. Turns increase 2.5%; per-turn
reductions are 13.15% and 7.82%. These are development results, not independent
confirmation.

On 528, bundle 1 gives 7,948 → 7,563 exhausted turns and 594,715 → 568,732
shortcuts in debug bench. Its separate 1,024-game release screen gives
8,094 → 7,113 exhausted turns (-12.12%), 49.9% wins, and no failed games,
broken/capped drafts or losses by round five.
Adding the turn predicate on 528 gives 7,948 → 7,106 (-10.59%) and
594,715 → 561,440 (-5.60%); `results/bench-development-528.json`.

## Identity and lessons

The economy bundle, late-premium move, adjacent-exit change and turn predicate
each preserve all 52 wide replays relative to their immediate reference.
Bundle 1 changes 2/52 production replays (`00corners` A and `00monolith` B).
With only `prepare_next_turn` disabled in **both diagnostic copies**, all
52/52 replays are byte-identical. This isolates the existing turn-end queue's
real-budget floor: even at 100M it warms a different amount of routing work
when earlier work becomes cheaper. The production candidate keeps preparation.
The turn predicate itself is 52/52 identical to bundle 1 without diagnostics.

On 528, the final production candidate matches 48/52 wide replays and 106/108
forced-composition replays. The wide differences are `00interlock` B,
`01boss-battle` B, `gen-chambers-102206117` B and `gen-huge-shared-102107800` A;
the coverage differences are `02stalactites` A and `04horseshoes` B. The
diagnostics match **160/160** (52 wide + 108 coverage) with preparation disabled
in both copies. `results/identity.json` records all four comparisons.
Coverage includes every champion (Cassi/Issac together), notably
Prism, Ren, Varg and Heart of Ruin, and large camp groups through 352 members.
On identical coverage games the candidate saves 4,398 fuel per baseline
turn above 100k. `check_turn_bound.py` also exhausts all 768 combinations
of the turn-count inputs, including stuns and teleport timing.

Past fuel work (495–506 and the subsequent unsuccessful sixth pass) guided
this work: census exhausted turns, distinguish startup from steady-state costs,
use complete runner counts, preserve exact arithmetic and stable ties, and
check both real-budget debug and release builds. Small noisy OOF gains alone
are not enough to select a change.

Rejected or not retained:

- Tighter unclaimed-group Prism pruning: 29/52 identity; discarded.
- Large negative-ward cache: first-use construction erased steady-state gains.
- Clamped ground-search loops, fallback stand-trade memoization, earlier
  search-node-cap exits, explicit health/Fighter copies, and reused Reach
  ordering: negligible savings or higher matched fuel costs.
- Deferring exact retreat damage once its risk rank is known: exact but only
  ~3 mean fuel saved.
- SIMD settled-rank comparisons / rank-window endpoints: exact, but too little
  saving to retain the extra machinery.

Do not rerun deterministic samples as extra evidence. The final fresh suite
is kept separate from selection, and coverage must force champions absent
from the ordinary draft.
