# Fresh Claudus Monolith: allocation and prior-work reconciliation

2026-10-24 UTC, Astra. Existing extracts and canonical source only; no engine, new actor-view export, public query, script, gameplay edit or EXPERIMENTS edit. **The fresh game supports a continuing objective-allocation problem, but does not supply a new certified own-actor boss opportunity or justify reopening the rejected local-crew arm unchanged.** Both live submissions/source identities remain unknown.

Match `185baabf-117b-4d3f-a50a-627f6a46bc34`, our physical A, replay SHA `a628df34062b909e813cb3115df410cb015aac527bae463437ea8e58e886e728`, map hash `c199d1fc490a2d4c`; existing extract `replays/incoming-loss-adaptation-20261023-v1/analysis/a628df34062b909e/`. Ours P/V/Marcella/Willow/HoR loses716–1113 at1002 despite ten kills and zero deaths. Canonical comparison is aggregate4db4eecbda37e23dbce0b162d2cf7441a3d32a554d6534cf196e3ffbedcdf2fd, not recovered live source.

## What is new in this game

Only enemy Vesper5 has extracted damaging actions against boss camps0/1:98 such events, starting670 at `(4,0)` against boss0 `(1,1)`. Boss0 hits84 times in total and always targets Vesper5; boss1 has no hit/death/capture event. Vesper gets both256-gem payouts771 and975. His first clear is **solo attrition with a heal trip**, not the nearer-HoR tank division demonstrated in the earlier Fish loss.

At end670 he has4300/4300HP and375 Strength. By700 he has520HP; at703 he dashes `(4,0)→(6,0)` and walks to `(7,0)`, then finishes recall709 with142HP before arriving healed. The group sleeps705 and retains its damage. He walks back, kills the Monolith757, clears the remaining group764, captures771, and banks798. On the second cycle he begins922 with5200HP/460 Strength, kills the Monolith960 at412HP remaining, clears resources968, captures975, and banks1002. These are global events/end-round states; actor knowledge, exact admission and exit certificate still require an own-view window.

This separates at least three jobs: damaging the dangerous boss, moving/clearing harmless clusters, and capture/banking. A full-group fixed-station certificate can reject a feasible phased job, and a full-clear current-health certificate can reject attrition with an affordable heal trip. Neither simplification should be relaxed merely because an opponent succeeded: the extra travel, known safe exit, unchanged boss HP after a break, capture delay and opportunity cost all need pricing.

Our Vesper's economic capacity differs substantially: at670 he has1218/1400HP,245 Strength; at922,2274.8/2300HP,340 Strength. Willow has700 maxHP,120 Focus and79 Strength at670, not a large safe tank/heal budget. Prism remains productive on ordinary camps (249 held gems at the finish,49,435 camp damage). Our entire team does172,557 camp damage against their171,418, so aggregate output alone misses which reward is unlocked. Final716+249 held=965 still cannot beat1113 by instant banking. No draft swap or retention reversal follows.

## Current-source predicates, not live attribution

The mixed-resource gate is already documented in the previous research. `world.cpp:980–986` makes `monolith_only` false when an ordinary group contains gems; this map has ordinary15-gem groups alongside256-gem boss groups. `siege_candidate:3531` rejects live non-sealing Monoliths in that category before pricing. `siege_ready:3564` independently gives them zero allowed clear rounds; ordinary farm `2163` excludes Monoliths, and ordinary camp targeting `233` excludes one outside `siege_group`. Capture-only/sealing paths are exceptions. Exact sealing depends on the actor's altar-access belief and bag, so it is not certified false for every historical turn here.

Simply removing those gates remains wrong: siege admission uses every living ally's output and maximumHP, including distant allies, then can engage on a gathering timeout. It also preempts ordinary farm rather than comparing economic rates. Willow/Prism support and banking/shopping/combat can return before siege. No fresh trace identifies which earlier return ran in this public game. Source-known exclusions are the strongest hypothesis; a draft/capability or retreat failure is not established.

## Preserve the completed prior investigation

Read `research/willow-policy-wonk-monolith-own-view-diagnosis.md`, `research/willow-fish-monolith-loss-review.md`, `research/willow-local-monolith-crew-design.md`, the focused diagnostic summary and `replays/willow-local-monolith-reject-trace/cert-reason-v2/diagnostic-summary.md` before proposing an arm.

The prior local-crew candidate56f17feceab5d8aa7278a9ff71bdc607a25b8e771fb8d28c72e30889d83a85d7 againsta00fff had five Debug nominations, zero positive admissions, zero selected boss work; neither side attacked a boss in the four Debug/Release games. Its later diagnostic did not fail claims, tank HP or enemy exposure first: only Willow entered the worker list. At783/785 every endpoint failed reach to the boss; at784 the two endpoints reaching the boss could not reach a harmless cluster. Anchor, exposure and bailout checks were never reached. Matching34226 extracted events is not native-state or Release/fuel equivalence. This was an unactivated, incomplete mechanism, not evidence that merely weakening a claim filter would help.

The prior Fish actor view demonstrates a different feasible pattern:465-Strength Vesper attacks while a visible adjacent HoR takes damage. Its Willow415 service opportunity already has its own priced safe-heal arm. Fresh Claudus succeeds without either a healer or a boss tank crew. Therefore more generic Willow following/healing is not supported as the first boss remedy. A radius5 boss plus adjacent tank forces range4 Willow healing inside the hazard; the prior design correctly declines imaginary free support.

## Cheapest next step and conditional candidate

Do not build another broad mixed-boss admission patch from this outcome. The cheapest next step is one positive actor-known phased-job witness, then reuse the existing local descriptor/rate comparison infrastructure. A narrowly revised candidate would price **dangerous-member clearing followed by bounded harmless cleanup/capture**, instead of requiring one endpoint to reach every member forever. Keep real local workers, native readiness, current-health/exit reserve, ordinary-work comparison and per-observation revalidation. Do not credit an absent tank, future Willow heals or all-team maximumHP. The old sole-Willow nomination could still fail its later health/anchor checks after coverage is fixed; do not promise activation.

Claudus's heal-trip attrition is a separate, larger candidate. It would need one locally known persistent boss job, an actual safe disengagement, paid round-trip time and a reason it beats ordinary farming. It must not be smuggled into the small endpoint correction by ignoring the health budget. No source change is nominated as ready for implementation from this review.

Two bounded own-view windows, if later authorized:

1. **Enemy Vesper5/B,698–710**, same fresh replay: inspect actual boss knowledge, live readiness, mitigation/items, danger at the retreat boundary, legal dash/walk and recall completion. This tests the newly observed solo-attrition mechanism, without assuming the death-free global outcome made every action safe.
2. **Our HoR4/A,687–695**: reaches `(46,40)` at689, distance8 from boss1, with1260/1400HP,44 Strength and472 Focus; Willow is globally `(41,38)`,700HP/120 Focus. Determine whether the boss is actually visible through occlusion/ward sight, which local work/capture is protected, and whether any current local crew exists. Other allied damage actors are globally far away. This is a visibility/job nomination, not a proven missed siege or invitation to force Willow into range. An alternative earlier Vesper371 window has only734/1000HP and135 Strength at `(5,8)`, so it is a weak positive-admission candidate.

No extraction was performed. These windows should replace speculation only if the strategic task is resumed after the current runtime queue; the existing unactivated local-crew branch need not be rerun unchanged.
