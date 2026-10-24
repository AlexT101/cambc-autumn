# Remembered-camp routing: 112-cell panel and focused follow-up

2026-10-24 UTC. Read-only independent review; no engine execution, decoding, build, helper implementation, or gameplay edits. Cambridge Battlecode rules read. Panel, source and the three bounded actor-known investigations are complete. The abandoned live-draft question is outside scope.

**Keep the demonstrated routing repair, but do not claim a competitive gain.** Both arms win57/112; seven gains offset seven losses. Band A already proves restored HoR farming and200 banked gems where both unpatched controls produce zero. The panel now supplies changed losses to investigate without discarding that useful behavior or introducing map-name exceptions.

## Verified panel boundary

Evidence root: `replays/willow-astraeus-remembered-camp-route-cb61-v33-panel-preflight-20261024-v3/`. Final receipt SHA256 `b96bc42f457dbdcf48faa4a0b7dc6efcd79d21c3104045bea9321ce85e4446f6`; paired outcomes SHA256 `225e4957ba723fbac24735f357315907408d3aba318f296a86135f65e763cc06`. Manifest SHA256 `8e340c68c9dc11481b27056248ab97e7576764b2850027293bad51c20e917244`.

Frozen source aggregates remain cb61 base `369742e3f54259c675c0d4b508a02c0c4517eef6e1cb3ef6f42fa776194180ea`, route `2a475721c8985cfcbd189e683ffac90ac05cdbf06280289899d21d9be851204e`, and v33 opponent `a00fff454c1e48520968c9ba2d4c1ecdae0212ce019724dc06a6e959ddc3412e`. Source/raw/injected postpins match. The subsequently merged f7 Prism change is not in these test arms.

| Matched physical-side outcomes | Cells |
|---|---:|
| Both win | 50 |
| Both lose | 48 |
| Base loss → route win | 7 |
| Base win → route loss | 7 |

A wins25→27; B wins32→30. Seventy-nine cells have identical round counts, which does not prove identical actions. Mean duration changes by+0.73 rounds and median0; neither is a quality metric. These56 maps/112 sides include retained mechanism witnesses and are diagnostic regression coverage, not independent held-out qualification.

Fresh audit totals cover109 base and111 route games, so comparing300 versus325 candidate rollovers directly uses unequal coverage. Existing reused audit rows reconcile the full112-cell sets:

| Full matched panel play rollovers | Base | Route |
|---|---:|---:|
| Candidate A | 150 | 141 |
| Candidate B | 160 | 191 |
| Candidate total | 310 | 332 |
| Reference total | 656 | 608 |

Base adds BandA6, GoldA1, GoldB3 to300; route adds BandA7 to325. Reference additions are5+15+4 versus3. Reused audit source: `replays/willow-astraeus-mechanism-band-gold-20261024-v1/audit-logs/{cb61-base,cb61-band}/native-status.json`. Native BotErrors, caught action errors and turn-order markers are zero. These are whole-match counts after trajectories diverge, not matched-turn instruction-cost measurements.

## Three paired cells selected for actor-known review

All six replay paths are `outputs/<cell>.repl26a` under the panel root. No other new pairs are requested.

| Pair | Outcome / rounds, base → route | Candidate rollovers | Why inspect |
|---|---|---|---|
|041 Band B|win996 → loss1120|5→5|Opposite side of the verified productive Band A repair: distinguish useful departure followed by worse conversion from a new route defect.|
|038 Starvation A|win2000 → loss1425|5→3|Large timing change on a support/farming setting: inspect route destination and ally/service separation rather than infer failure from low personal income.|
|040 Yellow Brick Road A|loss890 → win853|8→8|Gain control; B also changes loss→win, but only A is requested initially. Check useful camp work and payout conversion, not merely forward movement.|

Replay SHA256 pins:

- `041-cb61-base-gen-band-102305906-candidate-B`: `c1e09d47166dad86da19598b2d9d6139ad439b18824e451b8fe805fd36b5e3c3`; route counterpart `041-cb61-remembered-camp-route-gen-band-102305906-candidate-B`: `7628aab2b146d8da060b44745e40a74817fdfbe213162f0dd376ca1f043fa63d`.
- `038-cb61-base-01starvation-candidate-A`: `acb7ac57ba19deb331baa11fa50a3e2cfaa551496e9408a428a87098263388c1`; route counterpart `038-cb61-remembered-camp-route-01starvation-candidate-A`: `9472057214519e256150115e2f507f27c0ea4e67e58c3c3b85548fae44c4a7a8`.
- `040-cb61-base-01yellow-brick-road-candidate-A`: `71792ae8bc025c6545d54303b5ee2cb8f5c0206e220dd4513a9d962f295cd8d8`; route counterpart `040-cb61-remembered-camp-route-01yellow-brick-road-candidate-A`: `7ca998e3cd6cd938b94ae5a1c2e8411de829ace349289230d94c7e90ecb1f466`.

**Completed bounded worker output:** all six event/round extractions validated in `replays/willow-astraeus-route-selected-six-extract-v1-20261024/analysis/index.json`; paired locator is `paired-mechanism-summary.json`. Own views are in `replays/willow-astraeus-route-six-ownview-v1-20261024/`, with exact inputs in `ownview-manifest.json` and summary SHA256 `fda72f7d534ac1160615588fabbabd3a57d53cbe5d3e9934c807de9b73a0bee7`. Windows are Band B HoR5 r131–139, Starvation A Vesper1 r1–3, Yellow Brick Road A Marcella2 r79–87, each arm. The findings below check per-actor actions and native turn endings, not global action interleaving.

## Actor-known findings and next direction

**Band B: the first changed decision improves local production despite the eventual loss.** Both HoR5 actors finish the same14-gem tribute at r133, start at raw(41,44),960HP, bag0, gold40 and dash cooldown6. No other champion is visible throughout r131–139; no visible enemy or missing ally support explains the first movement difference. Base walks(42,45), then reverses to(41,44) at r134. Route walks(40,43), then(39,44),(38,43),(38,42), starting camp work at r136 instead of base r137. By r139 route has killed g30 camps44/46/48/50 (480HP total); base has killed48/50 (240HP total). This is actual useful work, not merely pocket departure. Existing event records further show route g30 clear r139, capture hold r140 and HoR5 payout28gems/0gold r145; base clears r147, holds r148 and receives the same payout r153. The repair improves this local payout by eight rounds.

Camp/terrain positions in these B own-view exports use the actor's rotated frame, while action endpoints are raw. At r133 g30 camps44/48/50 have own-view-known dynamic state; camp46 is static-map-only. At r136 the attacked camp50 is own-view-known. Static layout is not an observation of a hidden camp's current HP, and the export does not expose World belief, selected farm group, exact mask or route caller. The local result supports retaining the repair. It does not identify why the game later loses or justify a global allocation change.

**Starvation A: a concrete first-action fuel regression precedes any tactical split.** Vesper1's r1 snapshots match: raw(2,48),1000HP,0bag/0gold, both abilities ready, all four allies visible at identical positions, no visible enemy and no local camp records. Base moves(3,49) and ends normally; route emits no action and ends `fuel_rollover`. This is not benign actor scheduling. At r2 the missed move already changes ally occupancy: Willow is(3,51) in base versus(3,49) in route, while Vesper walks(4,50) versus(3,48). By r3 each follows its resulting path. Fewer whole-match route rollovers (3 versus5) do not erase this opening failure, but the first failure alone does not prove the eventual loss was caused by it.

The next narrow improvement target is **the cost of producing a legal farm step while preserving the new obstacle semantics**. `pathing.cpp:371–383` now imports native occupancy and vision, complements vision and combines remembered live camps on every farm call; `walking_blocked` can repeat that work for descent/fallback, and `live_camps():97` may update changed groups. These costs occur before the existing `FuelMeter{"route"}` at476. Existing search reserve checks at664 and the farming callers have not gained a measured overlay allowance. This is a source-grounded cost hypothesis, not proof r1 reached that helper: cold initialization, changed search topology, repeated fallback or generated-code cost can also produce the rollover. A bounded paired r1 Vesper diagnostic should record fuel at turn entry, first farm caller, occupancy/vision/live-camp overlay completion, search start/end, and immediately before the first accepted move, plus counts of overlay builds and searches. Reuse already computed values; do not enumerate more state. If no farm helper is reached, reject the overlay hypothesis and locate the earlier cold-start boundary. If repeated unchanged reads dominate, an action/vision/World-version-aware reuse can be tested; if the first necessary update dominates, account for its measured cost in the existing reserve rather than introduce a new broad fuel gate. Any optimization must preserve current visible emptiness, post-move/post-kill freshness and remembered unseen live camps, and retain the Band productive witnesses. No gameplay implementation or additional execution is requested in this review.

**Yellow Brick Road A: ordinary work allocation changes, with enough visible allies to finish the current wolf.** Both Marcella2 actors at r81 start(10,13),1180HP,bag0,gold88, reset ready and damage cooldown6. Both attack camp62 at(9,14) for50. Base resets and attacks it for another50; route instead moves(11,12), retaining reset. All four allies are visible: HoR4(8,14),890HP; Vesper1(8,13),1000HP; Prism0(6,14),700HP; Willow3(6,15),700HP. No enemy is visible. Camp62 is own-view-known at170.8999HP before Marcella's first hit, and camp60 at541.75HP. There is no immediate last-hit guarantee for Marcella and substantial allied damage is physically available. Later accepted actions confirm camp62 dies in the same round in both arms: base to Prism after Vesper, route to Willow after Vesper and Prism. That continuation is evidence of actual shared work, not a claim the bot predicted those exact actions.

Route Marcella stays a step ahead along the outgoing path through r86; both reach raw(16,14) at r87, with health1180 and no extra Marcella attack in r82–87. Base's reset comes ready r89 versus route retaining it throughout. This window proves neither an additional useful farm/capture nor the cause of the eventual win. It does show why simply forcing the skipped50 damage or forcing all allies to stay grouped is unsupported. Without the actual selected group/route-result branch, do not claim the changed route mask directly chose an economically superior task.

**Recommendation:** retain the route variant as a demonstrated repair with neutral panel score, prioritize the precise Starvation first-action fuel witness, and use Band B's eight-round payout improvement plus Band A's recovered farming as regression invariants. No new map-specific rule, camp-belief expiry, forced grouping or route rollback is justified by these three windows. The remaining changed outcomes can stay unexpanded until the first-action cost question is resolved.

## What those frames must distinguish

1. **Obstacle consistency works, but arrival is worse.** Same selected work with a legal detour, followed by real farming, would preserve the repair. Compare arrival timing, currently visible enemy reach/readiness and available ally positions before blaming a later death/score loss on routing. A better path does not guarantee better task allocation.
2. **Conservative knowledge becomes unnecessarily restrictive.** Check whether the actual blocker is currently visible empty (must open), still known alive outside sight (intended block), or has newer actor-available death/clear information not reflected in the route mask. An omniscient dead camp is not evidence the actor could safely open it. Do not add an arbitrary age expiry; a bounded knowledge-refresh improvement would require a specific available fact missed at the decision.
3. **Route/goal or budget mismatch remains.** If the actor repeatedly returns to a target it cannot reach, distinguish the remembered-camp live route from the older approach/goal field and retries. If an earlier rollover interrupts the choice, retain the action timeline; equal/lower whole-match rollover counts do not rule it out. No new fuel gate or broad cache rewrite follows from the aggregate panel.

Improving a changed loss requires an actor-known decision witness in one of these categories. The gain control and existing Band A evidence prevent a proposed repair from simply restoring the old blocked-pocket behavior. Preserve the current variants while investigating.

## f7d54e9 Prism support change

Source diff `git diff f7d54e9^1 f7d54e9 -- bots/astraeus/src/bot.cpp` adds four lines near4835. In the Prism branch of `local_support`, after safe-station selection and support bookkeeping, **only if best==here**, try a basic on a visible enemy; otherwise, while an attack remains, attack a camp whose entire group's static Strength≤0. No move, spell, route policy, goal selection, or support request is changed. Existing native action checks and target enumeration are reused. Camp hits flow through the ordinary `camp_hits`/`Upkeep` accounting and stationary basics through `count_use`.

No concrete route-mask or shopper-interface blocker found. A service-shopper arm must still be compared against the same source parent: this change can reduce Prism's lost work while waiting and can change subsequent deficits, so cb61 service histories are not exact f7 behavior. The route panel's frozen cb61 sources remain valid as their own evidence. Canonical merge identity supplied by the coordinator: `a564c25`, source aggregate `f475b8521cada611754076822402a266c43be8de76ce0f2b504b268ff3335824`.

One precise semantic caveat merits a future targeted fixture: a “free” basic is free of walking/casting opportunity cost, not necessarily HP cost. `attack_target` in `self_abilities.cpp:170–229` permits nonlethal Ren retaliation, rejecting only retaliation≥currentHP. A Ren outside its current strike reach but inside Prism's basic range can therefore cause0.2×Focus retaliation even from a station classified safe; `SupportExposure.safe()` evaluates enemy/camp threat, not the cost of our chosen attack. This may add healing demand while Prism waits. It is a source-derived possible interaction, not an observed regression or a reason to remove all stationary basics. Any fixture should include successful camp attack, successful ordinary enemy attack, and nonlethal-retaliation target; no new execution is requested here.

Upstream reports49.5% of600 and52/52 byte-identical benchmark replays. Its own note says the branch entered31 times and found no target: those byte-identical controls do not validate successful-attack consequences, and “costs nothing” should not be read as zero executed helper cost. Keep the narrow change separate from the routing regression hypotheses and the shopper experiment.
