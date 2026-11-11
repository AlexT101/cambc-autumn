# Charybdis fuel D — closed without shipping, 2026-11-11

Worked alone in `/home/ubuntu/wt/charybdis-fuelD`, branch
`charybdis-fuelD-20261111`, from `556463738` on `charybdis-20261111`.
The user requested wrap-up before further work. **The 10% exhaustion target
was not reached. No bot changes were shipped.** `bots/charybdis` remains
source-identical to the starting commit and `variants/chary-fuelD-base`.

The best small screen did not generalize: the larger development run had
essentially unchanged exhaustion. A conditional identity failure also remains
in the deferred movement-guard change. Candidate patches are research artifacts,
not approved replacements for Charybdis. No CHANGES entry is appropriate.

Read the rules, tool guide, FUEL-GATES, Charybdis fuel C, and the 2026-11-10
third through sixth and next fuel campaigns. Their main lessons held: avoid
whole unnecessary queries; generic caches and extra bounds often cost more
than they save. Screens are selection evidence, not confirmation.

## Real-budget evidence

Each row compares against the same frozen opponent, both arms on their own
drafts. Debug builds record shortcuts; cambc 5.0.1, native fast runner, jobs
86 sharing the machine-wide slot pool. These are not release win-rate gates.

| Candidate | Games | Exhausted turns REF → CAND | Shortcuts REF → CAND |
|---|---:|---:|---:|
| support3 screen | 1,024 | 6,775 → 6,567 (-3.07%) | 277,219 → 269,176 (-2.90%) |
| combo screen | 1,024 | 6,775 → 6,784 (+0.13%) | 277,219 → 261,652 (-5.62%) |
| combo-recovery screen | 1,024 | 6,775 → 6,454 (-4.74%) | 277,219 → 264,381 (-4.63%) |
| combo3 screen | 1,024 | 6,775 → 6,419 (-5.25%) | 277,219 → 264,655 (-4.53%) |
| **combo3 independent development** | **4,096** | **22,629 → 22,677 (+0.21%)** | **1,014,533 → 1,000,001 (-1.43%)** |

Development map-paired bootstrap 95% intervals: exhaustion **-4.59 to +5.23%**,
shortcuts **-3.09 to +0.27%**. After normalizing for game length, exhaustion
changes -0.95% (-5.57 to +3.92%) and shortcuts -2.57% (-4.03 to -1.02%).
Mean fuel falls 0.58% (-0.93 to -0.22%). None establishes the requested
reduction in exhausted turns. Full counts, labels, draft/early-loss checks and
intervals are in `results/combo3-dev.json`; the screen JSONs retain their results.

True exhaustion uses **every** runner `Out of fuel: A ... B ...` line.
Bench inference and stdout recovery markers miss consecutive exhausted turns.
Shortcuts count events, excluding `out-of-fuel` and malformed `SLOT` labels.
The bootstrap resamples maps, keeping both sides together: 10,000 samples,
seed 20261111. Stdout caps can censor shortcuts; `results/stdout-audit.json`
records the affected development games (one baseline stream and three candidate
streams). Runner exhaustion counts are unaffected. Neither development arm has a failed
game, broken/capped draft, or game ending by round five.

Screen seeds 4711100–4711101 contain 512 fresh ladder-v2 maps. Development
seeds 4711102–4711109 contain 2,048 additional maps and are now **used**.
Confirmation seeds 4711110–4711117 remain reserved, ungenerated and unplayed.
No final fresh confirmation or standard release A/B was run, because the
candidate failed to establish the target and no bot change is being retained.

## Bundles

Names below have prefix `variants/chary-fuelD-`.

- `combo`: support3, nearspan, guardreuse (including guardpoint), stuns, floor,
  turnformula and exit.
- `combo-recovery`: combo plus earlier stale-turn recovery checks.
- `combo2`: combo plus firesplit.
- `combo3`: combo-recovery plus firesplit; this is the larger development candidate.

Patches under `patches/` name their parent. Apply from the copied bot directory
with `patch -p1`; freeze the reference with `./copybot`, excluding `.cambc/`.
`results/source-hashes.json` fingerprints all experimental source trees and the
unchanged working bot. Raw bench results are `replays/fuel/fuelD/NAME.json`,
bundles and complete runner logs `replays/fuel/games/NAME/`.

## Identity and conditional coverage

All identity benches use 100M fuel. `results/identity.csv` reports direct replay
identities and fuel savings only on matching games, excluding round one.
Heavy turns are baseline turns >=95k; they are not necessarily turns that
exhaust at the real budget. The wide suite has 52 games per draft mode.
`results/identity-diagnostics.json` preserves comparison counts and differing maps.

- combo2: **47/52 own-draft**, **52/52 test-draft**; saves 239 mean and 738 heavy
  fuel on matching own-draft turns, 156 mean and 831 heavy on test drafts.
- combo3: **47/52 own-draft**; saves 187 mean and 414 heavy on matching turns.
  Recovery checks cost roughly 52 mean/324 heavy fuel relative to combo2.
- support3 and nearspan: **52/52** in paired diagnostic copies with only the
  `prepare_next_turn` call removed from both arms. Their direct own-draft
  identities are 47/52 and 51/52. This isolates the known coupling between
  real-budget-adjusted preparation and later field-readiness decisions; it
  does not make the original replays byte-identical.
- Conditional combo2: **119/128** directly; **127/128** after paired removal
  of `prepare_next_turn`. Ren occurs in every forced composition, other picks
  cycle all champion bodies. Maps include ordinary ladder/generated maps,
  40/64/100-square stress maps with 112/208/352-member groups, and 26 fresh maps.
  `coverage-probe.json` records actual mixed-group fire-partition executions.

The remaining conditional difference is `gen-classic-471110001009`, side A.
It persists with **all** warm-up work removed from both arms, and after
removing firesplit. Removing the guard changes restores **2/2** identities on
that map. Restoring only guardpoint produces **1/2** again. First gameplay
separation: round 717, champion 0, from (34,34), baseline moves to (33,33),
candidate to (33,35); contest versus farm branch. `coverage-firstdiff.json`
contains the states. A cover probe found no tested outside-cover tile that
was actually denied, but this does not explain the internal-history change.
**Do not ship guardpoint or guardreuse as proven exact.** Cost-history-dependent
route selection is a possible explanation, not an established diagnosis.

No clean full conditional identity gate was completed for a bundle excluding
the guard changes. The single-map ablation is not that gate. Nearspan also
needs a final audit of callers that might invalidate its cached span with
another nearby-group query.

## Experiment inventory

Positive savings are fuel saved per matching wide own-draft turn after round
one, mean / heavy. These are diagnostic measurements, not real-budget gains.

| Variant | Result and disposition |
|---|---|
| exit | Reuse camp exit fields when walls/goals/cap agree; 52/52, +66 / +15. Small candidate, not shipped. |
| nearest | SIMD nearest-other distance for small camp groups; 52/52, -119 / +52. Drop. |
| searchcap | Stop children at node cap; 52/52, negligible loss. Drop. |
| reachhits | Boolean Reach shortcut before full damage query; 52/52, -11 / -62. Drop. |
| stuns | Skip camp-stun refresh scans when no own cast could stun; 52/52, +4 / +25. Small candidate. |
| floor | Positive nextafter toward zero via IEEE representation; 52/52, +2 / +12. Small candidate. |
| heap | Immutable end-tile bound heap, preserving ties; 52/52, -7 / -38. Drop. |
| campfields | Host fields for nearest/earlier other champion; 52/52, -680 / -1,272. Drop. |
| support / here / lazy / support2 | Successive support-station sharing, current-tile restriction and lazy construction; superseded by support3. |
| support3 | Lazy station reads, enemy-only guard, rank before risk, deferred heal viewers, on-camp Prism hold query; +112 / +293 on 47 matches. Known preparation coupling; inconclusive screen. |
| sorts | Stable insertion sort for eight retreat tiles; 52/52, slight loss. Drop. |
| far | Distance gates before stand/idle/late enemy reads; 52/52, -18 / -154. Drop. |
| nearspan / near4 | Return cached nearby-group span without vector copy; nearspan +38 / +77 on 51 matches. Four cache entries add no gain. |
| campobs / refresh | Track own actions to reuse camp observations and Safety refresh; exact but roughly 100 mean fuel dearer. Drop. |
| guardpoint / guardreuse | Defer full guard outside its cover, reuse cover/FirstPass; 52/52 wide, +15 / +157 together. Conditional failure above; unresolved. |
| winbound | Extra farm bound; 52/52, slight loss. Drop. |
| helpbound / bounds | Further farm bounds; 41/52 direct, helpbound still 42/52 without preparation. Reject. |
| compact / strikeref | Strike storage/reference changes; 52/52, heavy turns dearer. Drop. |
| turnformula | Direct inclusive endpoint turn count instead of loop; 52/52, +11 / +33. Small candidate. |
| deposit | Deposit calculation change; 52/52, negligible. Drop. |
| recovery | Earlier stale checks in emblem/reach/escape/camp work, publish caches after completion; 52/52, -53 / -311 alone. Larger development does not establish OOF benefit. |
| campmemo / deadread / campzero | Camp memo, omitted reads, range-zero precheck; no useful gain. Campzero also differs directly. Drop. |
| firetail / firesplit | Skip harmless tail fire work, then partition positive-strength attackers before sorting; firesplit 52/52, +18 / +250. Small candidate; conditional guard failure prevents declaring its whole bundle exact. |
| groupstate | Group-state read simplification; 52/52, +12 / +5. Tiny. |
| hazards | Remove unused hazard zeroing/preclip reach; 52/52, negligible. Drop. |
| duel | General one-versus-one simulation specialization; 52/52, +10 / +13. Three-million-case existing oracle passes; too little benefit. Drop. |
| renprune | Harmless-group Ren pre-prunes; 49/52, -40 / -39. Repeated fuel C's failed idea; drop. |
| settlelarge | Extend settled-group reuse beyond 64 members; 52/52, -44 / -73. Drop. |
| stationdirect | Remove broad credible-enemy precheck, on combo3; only +4 / +12 relative to parent. Not selected. |
| guardmemo | Cache completed guard under generation/origin/radius, on combo2; costs another 20 / 30. Drop. |
| lethalstop | Early exit from any-threat and lethal threshold scans; 52/52, +5 / +8. Tiny. |
| ordergeom | Reuse geometry to bypass fresh order-holds scans; 52/52, -12 / -130. Drop. |
| farmnoflat / plannoflat / worldnoflat | Remove flatten attributes; all dearer, farm about -636 / -1,069. Drop. |

No strategic constants, reserve or fuel gate were changed in the candidates.
The user permitted arbitrary-order changes; firesplit can change order among
equal-key attackers, but the unresolved guard difference is not assumed arbitrary.

## Profiling lessons

Instrumented copies `census-wide`, `census-fine`, `census-deep` recorded actual
exhaustion stacks. Do not treat their OOF totals as performance: instrumentation
can prevent inlining and inflate the apparent strike-readiness cost. The deeper
profile attributed roughly 10.6k self fuel per exhausted turn to the farm loop,
5.1k to simulation, 4.6k to strike construction/readiness, 3.9k to camp updates,
3.4k to camp threat members, 2.7k to local support and 2.4k to Reach queries.
All 340 exhaustion events in that deeper census occurred during decide, not the
warm-up queue. Most were late in the match; chambers maps were prominent.

A catch-logging copy was 52/52 byte-identical and found only 64 caught SDK errors
in the wide suite. Exceptions were not a significant remaining lead. General
caches, broad extra bounds and flatten removal repeated earlier disappointments.
Savings concentrated in the wrong turns do not imply fewer real exhausted turns.

## Reproduction and remaining work

Activate `/home/ubuntu/venv/bin/activate`; `tools/bench.sh` sets the native fast
runner automatically. Examples from this report's root-relative paths:

```sh
bash research/charybdis-fuelD/tools/bench.sh own variants/chary-fuelD-combo2 combo2-wide-own
bash research/charybdis-fuelD/tools/bench.sh td variants/chary-fuelD-combo2 combo2-wide-td
bash research/charybdis-fuelD/tools/bench.sh dev variants/chary-fuelD-combo3 combo3-dev
python research/charybdis-fuelD/tools/identity.py
python research/charybdis-fuelD/tools/paired.py BASE.json CAND.json BASE-run-batch.log CAND-run-batch.log OUT.json
```

`--set wide` takes precedence over `--maps`; for a single-map diagnosis call
bench.py directly without `--set`. The coverage prior must first be compiled
into copies of both arms using `tools/draftlab/test_comps.py`; the bench then
uses `--test-draft`. Map generation and stress-map scripts are under `tools/`.

If revisiting, first resolve or exclude guardpoint and finish the span lifetime
audit, then validate any selected bundle under the relevant conditional maps
and champions. Only after a credible real-budget development result should the
unused confirmation suite and standard release A/B be spent. The target remains
open; this report makes no claim that any saved candidate should be merged.
