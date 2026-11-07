# Ocean fuel investigation, 2026-11-07

Goal: reduce out-of-fuel turns by at least 20%, prioritising the tail and large maps. No subagents.
Initial baseline: `variants/oc-fuel13-base`, after CHANGES 452–453, before draft7.
Final reference: `variants/oc-fuel13-current`, matching ocean after CHANGES 454, including draft7.
The shipped changes preserve draft7. Final candidate: `variants/oc-fuel13-viewgrid`.
Bench driver and raw evidence: `replays/fuel/fc13/bench.sh`, `*-{def,wide,pool,big,heavy,td}-100M.json`,
real-budget `*-{pool,big,heavy,td}-real.json`, and replay bundles under `g/`.
The six identity suites contain 342 games; wide and td use both bots' test drafts. Big has 8100+ tile maps;
heavy includes shared-gem groups and other historically expensive maps.

## Lessons used

Read cambc-rules.yaml, campaign 12's notes, campaign 7's detailed measurements, earlier campaign searches,
and `research/ideas-2026-11-06/algo-polyfill.md`. Most obvious caches, sort replacements, unrolling and
small-loop changes have already been tried. Low repeat rates make cross-turn fight caches unattractive.
The turn-end queue's fuel-limited progress changes cache availability even at 100M. A cheaper warm-up
can therefore change decisions that explicitly depend on a cache being ready. Do not call that byte identity.
Do not change fuel gates or burn fuel to imitate the old costs.

## Experiments

| Tag / variant suffix | Change | Evidence / disposition |
|---|---|---|
| split (`work`) | Stop flattening Search::read into plan_strikes | Negligible saving; dropped. |
| cap | Stop generating more children once the strike search has settled its node limit | Heavy 50/50 identical, total fuel effectively unchanged; dropped. |
| dash | Batch four adjacent dash danger queries in SIMD, preserving hazard summation order | Small net regression; dropped. |
| cluster | Harmless groups with no reflection: sum integral clear turns directly, bypass stands and sorting | Heavy 50/50 identical; mean 52385→52357, round-one mean 235865→233853. Def/big also run. Kept in final. |
| pack | First bit-packing prototype | Incorrect overlapping OR masks; superseded immediately by pack2. Never apply. |
| pack2 | Pack four bytes into four nine-bit rows; assemble a 9×9 window from four 8×8 board chunks | **342/342 byte-identical**. Mean -0.4–0.7%; p90 -0.1–0.2%; tail nearly unchanged. 32,000 randomized chunk/offset windows match the scalar bit oracle. Kept in final. |
| dilate | Grow square dilation by contiguous intervals, using logarithmically many shifts | **342/342 identical**; play fuel almost unchanged. Small first-turn savings. Not a meaningful route to the target. |
| terrain | Reuse the static window's bush mask and wall-presence test in sight and attack_viewers | Added an unintended global initialization loop (~256k per body's first turn). Superseded by terrain2. |
| terrain2 | As terrain, with constant initialization restored (`walls = false`) | Mean -2.1–3.2%, p90 -0.6–0.8%. **338/342 identical**, four cache-availability differences (below). First-turn fuel restored. Real-budget OOF events 2596→2393 (-7.8%) in 274 games, indicative only. Not approved as an exact change. |
| stamps | Lazy settled camp health timestamps, with readers updated and old visibility masks committed on change | **342/342 identical**, but mean +0.0–0.1%, tail slightly worse. Dropped. |
| bounds | Fight survival bounds use effective HP after Durability; reflection upper bound for one watched body counts only its attacks | Completed identity suites pass; no FIGHT-EXIT-MISMATCH in debug full-simulation checks. Mean saving only 10–21 fuel/turn, p99 -0.0–0.2%. Default suite rerun after concurrent CMake failure. Kept in final. |
| quiet | Quiet basic-attack turns apply reflection directly instead of building and replaying a hit-count tape | Def/heavy/td identical, tiny tail saving; included in combo. |
| bigcamp / bigcamp2 | Extend settled-camp shortcut beyond 64 members, then isolate its slow path out of line | 210/210 identical in each; common-path mean +0.05–0.13% / +0.02–0.07%. Later coverage audit found no group over 64 in these suites, so the large-group branch was not measured. Not applied. |
| freebound | Tighten strike_free for spent walks and mutually exclusive reset/dash | 342/342 identical; mean unchanged or 1 fuel worse, no useful tail saving. Dropped. |
| viewgrid | Cache viewer windows directly and compact 9-bit rows to the search’s 7-bit rows in three parallel steps | 342/342 identical against combo. Additional mean -0.35–0.49%, p90 -0.08–0.12%. Kept in final. |

Applied pack2, cluster, bounds, quiet and viewgrid to `bots/ocean` (CHANGES 455). **The 20% OOF target remains unmet.**

## Current profile

Function profiler, base self-play on the 50-game heavy suite at the real budget:
485,534 turns; 1,427 heavy turns (continuations merged), 916 with plan_strikes.
Fight-heavy self costs: plan_strikes 14.9k, act 8.7k, World::update_champion 7.1k,
Reach::build 6.9k, World::update_camp 4.4k, Reach::at 4.3k, find_members 3.9k,
Search::grow 3.8k. Draft work contaminates the all-heavy aggregate, so use fight-heavy for these conclusions.
Raw: `replays/fuel/fc13/prof/`; profiler from `replays/fuel/fc7/prof`.

## terrain2 differences

`firstdiff.mjs` in the raw-evidence directory decodes the first differing replay step.

- pool gen-classic-51903901015, A: round 33, body 5, move (21,12)→(20,12) versus (20,11).
  Base chooses farm, candidate Willow support.
- pool gen-classic-51903901029, A: round 47, body 4, move (22,9)→(23,10) versus (22,10).
  Base chooses farm, candidate Willow support.
- pool gen-contested-centre-51903910000, B: round 287, body 10, recall versus priority;
  base farm versus candidate Willow support.
- td gen-ladder-73102000010, A: round 70, body 0; different farm group and turn-order payload.

Controlled comparison: disable TurnEndQueue::run in both baseq and terrainq, retaining the same opponent.
All eight replays on the four affected maps (both sides, matching test drafts where applicable) are identical.
This supports cache readiness as the cause. Terrain2 is nevertheless excluded from the final exact candidate.
Its decision fuel with the queue off was slightly worse on these diagnostic games (+0.03% / +0.08%).

## Matched draft7 candidate

`oc-fuel13-current` freezes the current ocean draft7 source. `oc-fuel13-combo` combines pack2, bounds, quiet
and cluster without touching the draft. **342/342 byte-identical** to current on all six suites.
No FIGHT-EXIT-MISMATCH in the bounds experiment’s debug full-simulation comparisons.

| Suite | Mean base → combo | p90 base → combo | p99 base → combo | Max base → combo |
|---|---|---|---|---|
| def | 52559 → 52325 | 86412 → 86324 | 97017 → 96882 | 225998 → 224626 |
| wide | 51379 → 51146 | 86408 → 86282 | 106353 → 105968 | 283066 → 283088 |
| pool | 55336 → 55019 | 87081 → 86957 | 108595 → 108410 | 373161 → 368360 |
| big | 63334 → 62891 | 87643 → 87475 | 104474 → 104278 | 316636 → 296108 |
| heavy | 52758 → 52453 | 87245 → 87083 | 118385 → 118122 | 340648 → 339503 |
| td | 54900 → 54574 | 86937 → 86801 | 103449 → 103198 | 239329 → 239313 |

Combo A/B: standard 1280, 49.1%, OOF 8430/8536 (-1.2%), shortcuts 313420/314869 (-0.5%).
Fresh seeds 934137–934140: 2048, 50.7%, OOF 14113/14393 (-1.9%), shortcuts 552600/559460 (-1.2%).
No failed matches or broken draft handoffs; capped drafts 12/12 standard, 16/16 fresh.
The target remains **unmet**. This is a small improvement, not a demonstrated 20% reduction.

`viewgrid` adds packed viewer windows on top of combo. A compiled scalar oracle checks the actual source:
`python3 research/hyperion/fuel-campaign-13/check_windows.py bots/variants/oc-fuel13-viewgrid`
passes 80,000 chunk windows (widths 1–100, edge padding included) and 57,800 viewer-grid translations
(offsets -8..8), with undefined-behavior sanitization. The final ocean source, after renaming viewer-row identifiers to viewer-window identifiers, passes the same oracle.
Final `bench.py compare` runs pass **342/342** against current; every play and draft fuel entry also matches
viewgrid, so the A/B below measures the applied code. No FIGHT-EXIT-MISMATCH or CAMP-AWAKE-MISMATCH in those games.


## Final measurements

Fast runner, real 100k budget, both bots on their own matching draft7. Standard suites are ladder/gen/gen-s1;
confirmation uses four previously unused ladder-like suites, seeds **934141–934144**. No failed matches or broken
draft handoffs. Capped drafts: 12/12 standard, 22/22 fresh. Win rates are level within sampling noise.

| Metric | Standard reference → candidate (1280 games) | Fresh reference → candidate (2048 games) |
|---|---|---|
| Mean fuel / play turn | 50,148 → 49,653 (-0.99%) | 53,349 → 52,783 (-1.06%) |
| p90 fuel / play turn | 86,161 → 85,949 (-0.25%) | 86,779 → 86,556 (-0.26%) |
| Out-of-fuel turns | 8,785 → 8,480 (-3.47%) | 16,989 → 16,402 (-3.46%) |
| All SHORTCUT lines | 316,819 → 311,741 (-1.60%) | 607,203 → 597,260 (-1.64%) |
| Candidate win rate | 49.1% (629/1280), CI 46.4–51.9 | 49.3% (1009/2048), CI 47.1–51.4 |

Fuel distribution excludes draft and round 1 as bench.py does; OOF and shortcuts cover all play rounds.
Shortcuts include the out-of-fuel recovery tag. Count OOF using tools/fuel/oof.py, which handles interrupted
stdout, rather than relying on bench.py's draft-filtered OOF field. One fresh candidate OOF tag is interrupted;
the separate OOF trace gives 16,402, as ab.py reports.

At 100M, all six sets improve mean fuel by 0.8–1.2% and p90 by 0.18–0.30%. On the **8100+ tile** set:
mean 63,334 → 62,579; p90 87,643 → 87,378; p99 104,474 → 104,278; max 316,636 → 296,108 (-6.5%).
First-turn mean improves 0.2–0.8%; a few first-turn maxima rise slightly (up to 250 fuel). This is a small
fuel improvement, not evidence of a 20% reduction.

The 342 identity games cover varied own and test drafts, including Ren, Cassi/Issac,
Heart of Ruin and Willow; the heavy maps include shared-gem groups. The compiled bit oracle covers map widths
1–100, heights through 100, partial chunks with arbitrary padding, all relative viewer offsets -8..8, and
random masks. The simulation's existing debug oracle also checks early exits against full simulation.

Machine-readable results and champion coverage: [results.json](results.json).
Raw A/B summaries: `replays/ab/fc13-viewgrid-{standard,held}/summary.md`; per-turn aggregates and shortcut kinds:
`replays/fuel/fc13/fc13-viewgrid-{standard,held}-stats.json`. Final identity JSONs: `final-*-100M.json` there.

## Correctness review

- Chunk packing inserts a gap after each byte, assembles the four adjacent chunks, then clips both axes to the map.
  Viewer packing clips columns before translating (preventing row wrap), then removes the row gaps. Static masks
  have constant initialization; there is no first-turn initialization loop.
- Harmless-group clear time is a sum of integral attack counts, independent of the order and attack stands.
  Reflection must be zero: tiny positive float residuals after reflected hits can otherwise add an attack.
- Survival bounds use health divided by incoming-damage scale; linked bodies use the smaller effective health.
  A watched body takes reflection from at most its own two hits per turn. The maximum reflection bounds either
  linked body's attacks too. Whole-side bounds retain all living attackers.
- Quiet attacks have no cast or shield expiry before quiet_until. Applying their single reflection directly to
  each living attacker preserves attack order, linked deaths and the weakest-target cache.

## Further experiments after the bundle

- `partner`: avoid cooldown-dependent Cassi/Issac partner reach calculations inside ordinary attack range or
  beyond the longest possible dash. **342/342 identical**, but less than one fuel saved per turn and no useful tail
  gain. Dropped; the branch overhead consumes the saving.
- `localmembers`: large-group strike-search members from a local tile query, sorted back into original member
  order. **146/146 identical** on big/heavy/td; mean effectively unchanged. A coverage audit found these
  suites have at most 49 members per group, so this measured only common-path overhead, not the new branch.
  Targeted tests use stress_maps.mjs (112/208/352-member groups, three map sizes, 3/5 picks and test drafts).
  Targeted result: **12/12 identical**, mean 59,666 → 59,621 (-0.08%), p90 111,896 → 111,822,
  p99 289,731 → 288,926, max unchanged. Individual turns cost up to 12,757 more (and save up to 43,181),
  from index/board preparation and cache timing. Dropped: little aggregate saving and extra cost spikes.
  Isolated in `variants/oc-fuel13-localmembers`, not in ocean.

Coverage audit: decoded final replay statistics confirm Durability emblems on both teams in wide 00ambush A/B and 00contest A.
The generated normal suites’ “large maps” describe area, not group cardinality; do not use them alone to test >64-member paths.


## Targeted large-group stress confirmation

`node research/hyperion/fuel-campaign-13/stress_maps.mjs` builds six maps: 40×40, 64×64, 100×100, with 3 and 5
picks, separated spawns and connected central groups of **112, 208 and 352** harmless members. Both bots use
matching test drafts. This is a conditional correctness/tail test, not a representative win-rate suite.
Final bundle versus current: **12/12 byte-identical** in bench.py (`*-stress2-100M.json`), for **354/354** including
the six normal suites. Mean 60,186 → 59,666; p90 112,886 → 111,896; p99 300,937 → 289,731 (-3.7%); max unchanged
at 761,519. Round-one mean 426,069 → 387,775 (-9.0%), p90 789,237 → 745,420, max 878,552 → 871,466.

The earlier `*-stress-*` files are discarded: that generator used vertical symmetry with a centred spawn,
which overlapped the teams' spawns and kept fights away from the large group. `stress2` uses horizontal symmetry
and is the retained evidence. The generator and live replay group counts were checked; large map area alone
does not establish large-group branch coverage.
