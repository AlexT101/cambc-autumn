# Camp crew initiation before the tank arrives

Wakecold was selected under the user's judgment-zone policy after its independent small gain and merged by queue ops as CHANGES500, commit `fd8892b65`. The approved camp-partner shield stays in place. Frozen current `oc-wakecold-500` also preserves the separately user-authorized Skirmish499 table; the earlier wakecold/498 confirmation does not test that interaction. The informative live arm is separately v107 plus only wakecold, same mask/pins and explicit107 baseline. Queue ops owns launches and main edits; this owner owns research interpretation. Earlier self/broader candidates remain preserved below.

| Candidate | Real budget | 200k diagnostic |
|---|---|---|
| `c107-wakeheal2` | NARROWED (ZONE crossed): +0.330 ±0.250 pp, 3,712 fresh units | NARROWED: 0.000 ±0.224 pp fresh, 1,024 units |
| `c107-wakecrew3` | NARROWED (ZONE crossed): +0.224 ±0.250 pp, 4,352 fresh units | NARROWED: −0.024 ±0.229 pp, 1,024 fresh units |

Both gates use standard fgate, fresh ladder-v2, Flp4/Mt3q, release/own drafts and engine 5.0.1. High H0 alone is not rejection. The doubled-fuel result is unresolved, not a demonstrated gain or statistical rejection; ladder +0.195 ±0.244 pp, pooled +0.098 ±0.166. All intervals here are 95% half-widths. The real-budget wakeheal2 result is judgment-eligible: Fish +0.323 ±0.327 pp, Mite +0.337 ±0.370, ladder +0.007 ±0.302, pooled +0.168 ±0.196; low LLR +6.998, high −4.537, no screen/live-bar pass. It is retained as a small-gain fallback while the extension is judged, not automatically promoted. Source seals, admissions, logs and large artifacts live under `~/tmp-offload/camp107-mechanism/`.

The broader 200k diagnostic also finished: fresh −0.024 ±0.229 pp, Fish 0.000 ±0.358, Mite −0.049 ±0.345, ladder +0.220 ±0.257, pooled +0.098 ±0.172; eight blocks, no rejection or acceptance. The broader normal-budget gate finished at 34 blocks: Fish +0.115 ±0.332 pp, Mite +0.333 ±0.369, ladder −0.138 ±0.294, pooled +0.043 ±0.193; low LLR +5.367, high −6.166. A post-hoc paired comparison on the 29 noise blocks both arms completed reads the extension versus self guard at −0.135 ±0.138 pp fresh (Fish −0.175 ±0.199, Mite −0.094 ±0.196). This diagnostic does not establish harm or serve as a new gate. It supports retaining the simpler, better-supported self guard for confirmation; the extra rescue and conservative waits remain documented as separate future work.

## Exact reported failure

Fish 03honeycomb, our side A, match `01a1c508-acce-73ac-ad07-55e9090bca53`. The exact live source (`live-wd-campsh-gen`), platform SDK, committed mask and puppet opponent reproduce all 21,011 inputs and all 681 round-start hashes in release and debug. Queue ops owns the aggregate v107/v105 readout (commit `b3797c31b`); this investigation covers the mechanism.

At round 28, Issac has 200 HP and dashes from (2,14) to (2,16), then wakes the Elk at (2,17). The group also contains gem and gold clusters; hitting any member wakes the Elk. Four camp phases kill Issac at 32 and linked Cassi, who still has 600 HP. No shield partner withdraws on the initiating turn.

The exact trace says `CREW PICK 28 2 g20 J trips 0 tank 0 expected 1 output 236 damage 0 hp 200/900`. Vesper is the planned tank but remains outside Elk range. The damage-sharing plan admits allies arriving up to two walking rounds later, and ignores Issac's immediate travel dash. More fundamentally, charging a future healing trip does not require that trip before an unsafe first engagement: correcting arrival estimates raises the price to 780 damage and one trip, but Issac still enters and dies.

## Self-initiation guard

[Wakeheal2](wakeheal2.patch) checks the actual position before waking a sleeping crew target, including after movement/reveal and before the attack. It compares health with both estimated solo-clear damage and straight-walk retreat exposure from every living striker. If neither fits, it commits the existing camp retreat until a heal. It skips our spawn and requires proximity to a static camp tile within attack range; that tile can be a dead member. Monolith staging stays separate. There is no map key or fixed HP threshold. The retreat exposure is an estimate, not a terrain-aware escape proof.

The historical counterfactual is identical through Issac's round-28 dash. At step 6567, it replaces his Elk attack with retreat. He keeps 200 HP through recall and is healed by round 34; Cassi survives. Release and debug are identical across the resulting 569 rounds. The later puppet win is not strength evidence.

## Another ally can still wake the camp

On fresh `gen-ladder-131200200111`, the paired debug baseline and wakeheal2 match until round 493, when Issac defers his Golem attack. HoR also preheals. Prism nevertheless wakes the Golem at 494 while they recall nearby. Baseline Issac and linked Cassi die at 497; wakeheal2 delays the deaths to 501. This is an existing failure that self-initiation protection does not resolve, not a newly introduced death. Both selected games eventually win; those outcomes are not strength evidence.

[Wakecrew3](wakecrew3.patch) extends wakeheal2 to a sleeping group with one living striker. Before a basic attack or camp spell, it identifies the current nearest champion using the next camp phase's tie order. If that is another ally who cannot survive the estimated retreat exposure, it defers the wake. It allows actual finishing damage, credits a stun of that striker, exempts the ally's spawn and directly confirms asleep state before refusing. Thus stale beliefs after an earlier action cannot suppress damage to an already-awake camp.

This extension matches wakeheal2 until Prism's round-494 attack, waits during 494–497, and lets Issac and HoR recall and heal at 498. Cassi survives. Prism then wakes the camp, takes its own hits, and escapes with 90.9 HP at 503. Its historical honeycomb release also preserves the precise round-28 fix.

## Fuel and behavior diagnostics

The 100M wide benchmark plays 52 games against fixed Flp4. Behavior changes mean these are not fuel-only equivalence claims.

| Comparison | Identical replays | Fuel change on identical games | All-game mean |
|---|---:|---:|---:|
| Wakeheal2 vs full 498 | 44/52 | +0.06% | +0.2%, behavior-confounded |
| Wakecrew3 vs full 498 | 44/52 | +0.09% | +0.3%, behavior-confounded |
| Wakecrew3 vs wakeheal2 | 50/52 | +0.03% | +0.1%, behavior-confounded |

Each candidate also played a bounded 256-game debug census on fresh f0 against fixed Flp4, with two shared CPU slots and no errors. This measures mechanism frequency, not release strength.

- Wakeheal2: six preheal calls in five games (1.95%); one before round 50. Five guarded champions reach a heal before their next death; the retained Golem case is the exception.
- Wakecrew3: the same six preheal calls. Ally protection adds 11 basic/spell refusals over six distinct champion-rounds in two games. Episodes last four and two rounds; no prolonged wait was observed.
- The second ally trigger, `gen-classic-131200301015` at 688, is conservative: baseline's stun and Prism taking over the hits already keep 120-HP Cassi alive. The extension delays two rounds and lets her recall at 695. It is not counted as a saved death. Its debug outcome flips to a win, but changed trajectories do not establish why.

[summarize_guards.py](summarize_guards.py) reproduces the census counts. `census2-recovery.json`, `census2-trajectories.json`, `censuscrew3-guards.json`, `failure-base-compare.json`, `wakecrew3-vs-wakeheal2-failure.json`, `second-case-compare.json` and paired decoded replays retain the local evidence.

## Failed hypotheses and superseded sketches

| Sketch | Finding |
|---|---|
| [Arrival0](arrival0.patch) | Removing two-round arrival tolerance raises priced damage 0→52 but leaves the reported death unchanged; first action divergence is round 91. |
| [Arrivaldash](arrivaldash.patch) | Crediting the ready dash raises pricing to 780 damage/one trip, still without enforcing a heal before entry. Same unchanged death. |
| [Crewstart](crewstart.patch), crewstart2 | Taking the cheapest member's own damage incorrectly treats a harmless cluster as a harmless wake. Moving the check before pocket routing does not fix this geometry error. No preheal action; no gate. |
| [Wakeheal](wakeheal.patch) | Precise reported-case success, then superseded before either gate launched to exempt spawn and require attack reach. Old sources/evidence remain distinct. |
| Wakecrew, wakecrew2 | A full-health-only condition misses the retained Golem, which had already been damaged and gone back to sleep. No waits in that case; no gate. |

An initial historical diagnostic was stopped before play after detecting the wrong SDK from its launch directory. Its corrected platform copy has a distinct identity. The first external-output census played zero games because run-batch could not find its project; its 256 error entries are not outcomes. A task-owned project file and SDK/cmake links corrected the environment before the successful `census2` run. None of these failures is statistical evidence.

## Queue provenance

Wakeheal2 normal and doubled gates were admitted at 12:48:19 UTC and started at 13:05/13:06. Old wakeheal entries were held before launch. Final files: `fg-wakeheal2.log` / `wakeheal2gate.pid`, `fg-wakeheal2200.log` / `wakeheal2200.pid`; seal `wakeheal2-source.json`, admission `admission-wakeheal2.json`.

Wakecrew3 gates were admitted separately at 13:16:43 after bush200k, preserving active jobs and all previous source/cache identities. Files: `fg-wakecrew3.log` / `wakecrew3gate.pid`, `fg-wakecrew3200.log` / `wakecrew3200.pid`; seal `wakecrew3-source.json`, admission `admission-wakecrew3.json`. Neither gate was independently launched by this owner.

## Independent review

Version-check’s read-only review found no blocking correctness issue for continuing these experiments. Next-round NPC tie order, direct asleep confirmation and the single-striker finishing exemption were checked. Conservative limitations remain: a basic attack that cleaves from a harmless target may kill the striker without receiving the finishing exemption; Marcella’s enhanced-basic stun is not credited; allies may move, receive shields/heals or hand off the target before the estimated exposure occurs. A stalled wounded ally can theoretically suppress a wake indefinitely, although the observed waits are at most four rounds. The self guard’s static-tile proximity includes dead members and can therefore request a heal before a living member is attackable. Its cached solo-clear/shield estimates are existing heuristics, not a safety guarantee. No frozen gate source was changed in response to review.

## Unused-map confirmation (prepared before selection)

After both normal-budget gates finished, the coordinator selected wakeheal2 for this prospective confirmation, before any confirmation outcomes. The broader arm remains unresolved rather than rejected. A fixed, separate confirmation is prepared: 4,096 unused ladder-v2 maps from seeds 63671800–63671815, shuffled into eight disjoint 512-map blocks with noise bodies 1–8; each map plays both sides against Flp4 and Mt3q, for both full498 and the selected candidate. That is 32,768 release games at 100k, own drafts and engine 5.0.1, with the standard shared CPU pool. The base still matches ocean's source at preparation. No confirmation outcomes inform candidate selection.

The expanded content audit checked 733,239 distinct existing files: all discoverable offload maps, registered worktree maps, 53 prior draft/emblem/tune configurations' pool/holdout roots, and ladder/gen/gen-s1/bench maps. A same-size filter required hashing 156,246 files. Twenty original generated maps byte-matched prior maps and were replaced, without deleting them, from a shuffled reserve at seed 63671816; the reserve also had one excluded collision. Final 4,096 maps are unique and have zero hash overlap within that audited inventory. This is not a universal claim over the full historical repo map archive (over 12 million files / 228 GiB) or ephemeral /tmp workspaces. New seeds also avoid the reviewed seed registry and reserved localq ranges. The fixed sample uses new maps rather than another noise pass over fgate's 1,024-map pool.

[seal_heldout.py](seal_heldout.py) records maps, assignments, all source seals and launcher hash under `~/tmp-offload/camp107-mechanism/heldout/`. [heldout.py](heldout.py) validates those seals, exact cell coverage, matching build/fuel/engine metadata, source paths and zero draft handoff failures. Its independent fixed-sample report uses fgate's paired-map estimator and 95% interval, with Fish/Mite separate; it does not make interim stopping decisions. Early-loss/capped-draft counts remain visible for validity review. Queue ops owns launch after selection is sealed. The manifest was updated before selection or play to incorporate independent runtime-review checks; the previous pre-review manifest is retained.

Final pre-play manifest: `1e4ea8bdac601ca61351906b4a67f11c193678ffe21d904240f76621fc4bd8fa`; `selection.json` chooses wakeheal2 against full498. Source/map/selection/launcher checks passed before queue admission. The frozen launcher reports `result.json` only after all 32,768 games and exact coverage checks. Intermediate pre-audit suites/manifests remain preserved and were never played.

The first launcher stopped after 25 complete batches (25,600 games, zero run errors) because its added zero-handoff assertion was too strict. On block 6, both opponent bodies fail their draft guard on both sides of `gen-classic-6367180801025`, identically against full498 and wakeheal2; our own handoff counts are zero. The preserved pruned stdout flags and round-one results establish ordinary opponent early losses, which standard ab.py counts. They are not corrupt games and their matched paired contribution is zero.

Before any aggregate strength read, the coordinator approved [heldout_resume.py](heldout_resume.py): a separately sealed launcher that removes only the overstrict assertion and exposes handoff counts alongside early losses/capped drafts. It reuses all 25 completed summaries and plays exactly the seven unplayed batches, retaining all original cells, maps, sources, selection, seeds, estimator and fixed sample. Original launcher/error/manifests remain intact. Resume manifest `22305d00c5908d37c3beb9c76a34d784948fc4753a3eb406c41ec8e535056ac0`; `paired-handoff-diagnosis.json` records the cause. No bad-map exclusions or candidate reselection.

## Fixed confirmation result

Wakeheal2's independent 4,096-map / 32,768-game confirmation completed at 13:57:31 UTC: **−0.104 ±0.241 pp** (95% equivalent 49.656–50.137%), Fish **−0.330 ±0.339**, Mite **+0.122 ±0.348**. The shared-pool small gain did not confirm on this unused map sample. This is unresolved overall rather than confident rejection; recommendation is no merge now, while preserving the exact-case rescue and known limits. No extra samples were appended or selected.

Final coverage is complete with zero run errors. Own base and candidate handoff/early losses are zero; opponent handoff/early losses are eight against each arm (16 total), on identical cells of two maps, and contribute exactly zero paired difference. All remain in the fixed estimate. Opponent capped drafts total 564 across both arms; own capped drafts are zero. `result.json`, `complete-validity.json`, `units.json`, original/resume admissions and immutable manifests retain the complete result. Sources/maps/selection were checked again at completion.

## Changed-game development after confirmation

The completed confirmation is now development evidence and will not be reused as an unused confirmation for a refined variant. Twenty release retrieval games on five representative maps reproduce every original winner and round count. Six cells change outcome: three first diverge at a rollover, one at a farm claim/priority choice, and two at an actual preheal. Outcome labels alone do not establish a conservative mistake.

- On contested-centre, Willow's round-52 first difference is baseline rollover at 100,000 fuel versus the candidate's routine recall at 99,742. She has full 700 HP amid harmless gold clusters; this is not a lethal-wake refusal.
- A monolith-heavy map's loss first differs at round 14: baseline moves, candidate rolls over. The preset called monolith-only actually also has wolves/Elk/Golem, so it is not treated as a no-op control merely from its name.
- Both rollover-loss pairs become completely identical in inputs, round state and result between full498 and wakeheal2 at 200k. These four diagnostic games add no strength sample.
- A ladder gain also first differs at a round-one rollover. The remaining classic side-A loss first differs in Prism's advertised farm claim at round 56 while full health, before a lethal-wake refusal.
- On harvest, Cassi's genuine round-85 preheal avoids 360 camp damage and returns healed six rounds earlier; both builds have fuel headroom. The baseline survives, so this is a health/tempo example, not a saved death.
- Classic side B's genuine Willow preheal at round 419 avoids a Golem hit. Baseline survives one hit with allied stuns and later target handoff, and still heals Cassi. No harmful conservative cost is established just from the eventual loss.

`heldout-development/first-differences.json`, extracted schema3 replays, `fuel-control200/comparison.json` and `STATE.json` retain exact cases and limitations. This evidence motivates reducing collateral fuel effects before changing the refusal rule.

[Wakeout](wakeout.patch) outlines the entire check. Its 100M wide benchmark preserves 52/52 replays against wakeheal2 but costs +0.08% total fuel; no gate. [Wakebound](wakebound.patch) skips the detailed scan when even static group strength times maximum exit phases, after mitigation, is below current HP plus shield. This is an upper bound, not a tuned HP threshold: each member's exposure is at most its strength times `group.reach+1`, and shielding can only subtract damage. The 100M benchmark preserves 52/52 replays and saves 0.02% total fuel versus wakeheal2. [Wakecold](wakecold.patch) keeps that cheap bound inline and outlines only the remaining rare scan; its benchmark also preserves 52/52 replays and saves 0.03% total fuel (108,144 turns cheaper, 2,877 dearer). All sources have distinct frozen identities.

Wakecold's release historical smoke is exactly identical to the successful wakeheal2 counterfactual: 16,590 inputs and 569 round hashes, including the round-28 Issac/Cassi rescue. Ten development games also finished: the classic side-A goal-selection loss and monolith-heavy side-A rollover loss revert byte-exactly to full498; a fuel-driven ladder gain disappears too. Selected results are not strength evidence. The genuine Willow preheal loss remains.

Queue ops admitted wakecold's standard Flp4/Mt3q gates at 14:42:45 UTC: normal100k seed210/max1000/jobs4 launched in the main shared pool; diagnostic200k seed209/max8/jobs2 is queued after the current ward pair. Source seal `wakecold-gate-source.json`, normal log/PID `fg-wakecold.log` / `wakecoldgate.pid`, diagnostic `fg-wakecold200.log` / `wakecold200.pid`; admission `handoff/codex/queue-ops/wakecold-admission.json`. No merge or promotion. The completed 4,096-map confirmation remains development evidence and cannot confirm this refined variant.


## Wakecold gate result and bound review

Both standard gates completed without source changes. At 100k, wakecold versus full498 is **NARROWED (ZONE crossed), +0.195 ±0.246 pp**, 21 blocks / 2,688 fresh units (95% equivalent 49.949–50.441%). Fish is +0.130 ±0.344, Mite +0.260 ±0.379; ladder −0.093 ±0.288. At 200k, the fixed eight-block diagnostic is **0.000 ±0.224 pp**, 1,024 fresh units; Fish +0.049 ±0.345, Mite −0.049 ±0.317, ladder +0.317 ±0.290. Neither result demonstrates an overall gain or confidently rejects the change. No promotion or merge follows from these gates.

Independent read-only review confirmed the upper-bound argument: static strength sums all members, maximum group reach bounds each member's exposure, mitigation is nonnegative, and shield adjustment cannot increase damage. Dead members and multiple strikers only loosen the bound; strict inequality retains equality cases. The detailed fallback matches sealed wakeheal2. Legal live-member distance and stat ranges leave slack beyond ordinary floating-point roundoff. The 52/52 replay identity supports the proof but does not replace it.

Normal ended at 14:46:34 UTC; the doubled diagnostic was dispatched into the freed main-pool slot at 14:47:23 and finished by 14:49:06. Queue ops preserved the original seed/cache identity and source seals; dispatch record `handoff/codex/queue-ops/wakecold200-main-dispatch.json`. Both final JSON records remain in their owner logs. Camp-death work stays open, including the separate ally-initiated wake hole.


## Prospective wakecold confirmation

The coordinator selected wakecold for a new fixed confirmation before outcomes: 12,288 maps / 98,304 release games, full498 base, 100k, Flp4/Mt3q noise 1–8, both sides. Each of eight disjoint blocks contains 1,536 maps. Scaling the earlier fixed sample's observed standard error gives a planning halfwidth near 0.139 pp; this is only sample-size planning, not a predicted effect or an adaptive stopping rule. [heldout_cold.py](heldout_cold.py) retains every fixed cell and standard draft-guard early-loss accounting, verifies source/map/selection seals and reports only after complete coverage. No interim strength decisions or source changes.

New generation seeds are 63672900–63672947, with reserve 63672948. Before sealing, the inventory combines refreshed offload (including the old confirmation and all its development games), refreshed registered worktrees, the prior explicit draft/emblem/tune map inventory and standard suites. Cross-inventory and within-generation exact-content collisions are excluded before play, then replaced from the audited reserve. The audit seals its exact target path/hash set, including reserve files, so the sealer can verify coverage. Scope remains explicitly limited to those inventories, not the complete historical repository archive or ephemeral /tmp. Source full498 still matches ocean at preparation. Artifacts: `~/tmp-offload/camp107-mechanism/heldout-cold/`.

## Separate awake-camp follow failure

The existing live107 inventory contains Willow's identical round-41 camp death on `00great_wall` against both opponents. The Fish replay `01a1c4c3-92c4-7db5-ad53-cb104b675864` reproduces exactly with the historical platform source and opponent puppet: 33,344 inputs and 738 round hashes. The debug trace agrees through round 724 (first later difference 725), safely beyond this incident.

At round 36 the crowd-follow branch moves full-health Willow from (17,4) to (18,5), into an already-awake multi-Elk group. She takes 120, 180, 120, 180 and the final 100 HP across rounds 37–41. Follow acts on 37, 39 and 40; a farm fallback acts on 38. She shuffles between exposed tiles and dies without attacking in this interval. This is distinct from the pre-wake cases. `willow_follow` uses the ordinary movement guard; Willow's stations guard excludes only enemy threats, and `guard_work` explicitly skips healers. Healing-station selection separately excludes camp exposure, so it does not cover this later follow branch. No candidate change is inferred solely from the death: preserve legitimate Willow farming when designing any follow-specific fix. Evidence: `willow-death/evidence.json`, exact release/debug comparisons and puppet artifacts. Further implementation is deferred while the fixed wakecold confirmation is prepared. A distinct debug copy adds an explicit `WFOLLOW` call-site tag and retains the same trusted prefix through round724; it identifies follow at36,37,39,40, ruling out confusion with another support branch. No behavior code was changed. A separate release platform mirror is source-file-identical to full498: the same lineup still loses Willow to camp40 at(19,5),40HP, now round43. Thus current-source fuel changes delay this instance but do not remove it; one historical-opponent puppet game establishes persistence, not strength.


The prospective cold manifest was sealed before play as `e87c73291c7db645ab4885f05ff0133156bf79ee978ecb4ec575fe9dc1a45283`. Audit covered 737,591 distinct prior map files; 329,046 matching-size files were hashed against the exact sealed set of 12,544 generated/reserve maps. Eighty-five original maps collided with prior content and were replaced; final 12,288 map hashes are unique and have zero overlap within the audited scope. All inventory files were present. The launcher check passed and queue ops received the immutable launch request. A broad lab-root refresh produced an impractically large path inventory; it is retained separately and was not used to expand the stated audit claim.

The independent reviewer also checked float32 boundaries under actual mitigation factors: 68 single-striker boundary cases and 479,992 conservative multi/dead-member upper bounds passed. The check supports the static bound at legal current stat/map ranges; artifacts `check_wakecold_bound.py` and `wakecold-f32-bound-check.json`. It is not game strength evidence.


## Wakecold fixed confirmation result

The prospective 12,288-map / 98,304-game confirmation completed at 15:32:45 UTC with **+0.175 pp, 95% CI +0.047 to +0.303** (equivalent 50.175%, CI 50.047–50.303). Fish: **+0.114 [−0.063,+0.290]**; Mite: **+0.236 [+0.056,+0.416]**. This independently confirms a small overall gain, consistent in direction across opponents but uncertain for Fish individually. It is a judgment-zone result, below the broad 50.5% acceptance bar. With the demonstrated exact rescue and reviewed bound, recommendation to the coordinator is to consider wakecold under the user's zone discretion; this owner makes no automatic merge or live change.

All fixed cells completed, with zero run errors and final source/map/selection verification. Own handoff/early losses are zero in both arms. Opponents have 24 draft-guard early losses against each arm (48 total), on identical map/body/side cells across six maps; all are retained and contribute zero paired difference. Opponent capped drafts total 1,522; own zero. `heldout-cold/result.json`, `complete-validity.json`, `units.json`, manifest/admission and logs preserve the final evidence. There was no outcome-based stop, exclusion, appended sample or candidate change. The earlier wakeheal2 confirmation remains separate development evidence.

Operationally, contention initially left this confirmation about two shared slots. The coordinator authorized a temporary program share matching the active training program; allocation rose to roughly 12–17 slots without restarting any process or changing games. Queue ops verified the override removed at 15:32:46, launcher exit0, and all launcher/share-helper PIDs gone. This changes wall time only.


## Willow follow correction: hidden camp damage

A release-exact diagnostic resolves the discrepancy: throughout rounds 38–42, Willow cannot see any teammate or the group's camp tiles through the wall. The group remains the initial alive/asleep/full-health belief while real HP falls 700→580→400→280→100. `Safety::camp_area()` is empty and `camp_damage()` is zero; the existing `camp_may_hit()` correctly reports possible camp exposure. Her follow target comes from remembered/communicated positions. Camps attack through occlusion without revealing themselves, so actual damage does not automatically repair that belief.

[Wfollow-step](wfollow-step.patch) adds the existing camp area to the follow path's avoidance. It fails this case, leaving death at43; its first action difference is292. [Wfollow-exit](wfollow-exit.patch) also commits retreat when the follower is already in that area. Its replay is byte-identical to step. Pathing's connected-danger exception was an initially plausible explanation, but the measured empty danger area is the reason both guards fail here. Neither arm is gated.

[Wfollow-hurt](wfollow-hurt500.patch) instead reacts to actual net HP loss while travelling to follow a teammate in possible live-camp reach. It invokes the existing retreat and camp-fled persistence, stopping re-entry until healed. It acts after the within-two-tiles attack opportunity, preserves ordinary farm and bank branches, and changes no global camp belief or HP threshold. On the full498 release mechanism case, the first decision change is round39's released farm claim; the first different walk is40. Willow exits with100HP at43, walks onto spawn/heals700 at44, heals HoR60 at45 and Ren420 at66, and resumes camp attacks69–70. The baseline dies43. This establishes useful recovery, not strength.

The coordinator approved independent development while the separate wakecold confirmation completed. The latest verified frozen base is now `oc-wakecold-500`, including the separately user-authorized Skirmish499 table and wakecold500. The candidate `c500-wfollow-hurt` is only this three-file Willow diff on that base; the old wakecold/498 confirmation does not claim to cover Skirmish interaction. Source seal `wfollow-hurt500-source.json`, paired 100M wide benchmarks and a fresh500-pair platform mechanism smoke are in progress. The earlier498 prototypes and evidence remain unchanged.


On the new500 pair, the 100M wide benchmark is complete: 37/52 replays identical, total fuel on those +0.0004% (30,291 fuel across roughly8.01billion). The all-game mean falls0.3%, but this is behavior-confounded and not a fuel-saving claim. Fifteen changed games establish this is a behavior patch, not a pure fuel optimization. `bench-base500.json`, `bench-wfollow-hurt500.json` and the comparison retain the measurements. No strength inference is made from this small benchmark.


The500-pair release smoke confirms the same mechanism: baseline Willow dies43, candidate exits with100HP at43 and heals700 at44, then heals allies45/66 and attacks69–70. Exact paired artifacts are `willow-death/{base500,hurt500}.repl26a`, `hurt-base500-compare.json` and `pair500-analysis`. Queue ops admitted both sealed standard conditions at15:51:45: normal seed213/max1000/jobs4 and doubled seed214/max8/jobs2, Flp4/Mt3q, own drafts. They follow already-admitted behavior and precede new training; active jobs and bankviahome are unchanged. `run_wfollow_hurt500.py`, `wfollow500-admission.json`, `fg-wfollow-hurt500.log` / `wfollowhurt500gate.pid`, and `fg-wfollow-hurt500200.log` / `wfollowhurt500200.pid` retain launch provenance. Owner does not duplicate launches. Independent review was requested by the coordinator while gates proceed.


Independent review found no blocking correctness issue for the sealed Willow gates. Damage is consecutive-turn net HP loss; death/respawn and gaps cannot retain an old positive loss. Healing can mask damage, and shield-only/current-turn damage is not captured. `camp_may_hit` includes unseen/asleep living strikers and imminent respawns, ignoring walls and nearer tanks; it does not repair beliefs. The retreat flag clears on death, own spawn, or HP exceeding the trigger HP, so "until healed" does not mean full health. Existing higher-priority support/work/bank/siege and the within-two-tile claimed-camp attack remain ahead of this guard. Other-source damage near a sleeping camp remains a possible conservative trigger.

Changed benchmark games expose a concrete throughput cost, without establishing final-result causality. On Pilgrimage B, first divergence301 is after real camp damage (two20 hits), not enemy damage. Baseline walks toward its allies, takes only one further40 damage, then works safely at540HP; it heals Issac at303/311/319. Candidate walks away, recalls307 to700HP, and next heals at369: a66-round later next heal. Neither arm has any nearby death through381. The eventual benchmark outcome flips against the candidate, but that cannot be uniquely attributed to the first decision. On Hooks A, the selected final gain also initially retreats from manageable fire: baseline goes640→580HP then works, while candidate preserves640HP and recalls178. Its first later heal187 versus180 is delayed7rounds. Thus final gains do not automatically establish rescues. The exact Great Wall100HP escape remains the demonstrated rescue; these two cases establish the conservative support-abandonment tradeoff. Frozen gates are unchanged and no refined predicate is selected from these outcomes. Artifacts: `willow-death/bench-compare-{00pilgrimage-b,01hooks-a}.json`, `bench-analysis`, and `bench-willow-stats.json`.


## Narrow Willow arm: unobserved follow target

A two-game diagnostic copy `c500-wfollow-probe` logs at the retreat guard; both replay cores are byte-identical to their broad-guard benchmarks. Pilgrimage301: target observed this turn, predicted camp damage40. Hooks172: target observed, predicted camp damage0 (Safety's target/stun-adjusted model can be zero even after real camp fire). Therefore zero predicted damage alone does not identify hidden camp belief. `probe-bench-evidence.json` retains exact checks and calls.

The separate [blind arm](wfollow-blind500.patch), `c500-wfollow-blind` on frozen500, adds only `!target->visible` to the damage/potential-camp guard. It reacts while following an ally not observed this turn, preserving support when that chosen target has been observed. This targets the demonstrated wall/remembered-position failure without a new HP threshold. Independent review notes that visibility can remain true after a ward replacement removes sight during the turn; this suppresses the guard, a coverage gap. The crowd-ranked target need not be protected Prism, and remote ward visibility counts. This is neither an all-ally visibility rule nor an exhaustive current-sight check. Broader hurt sources/gates remain unchanged.

The platform-SDK release smoke on exact full500 source retains the rescue:100HP exit43,700HP spawn44, heals45/66 and attacks69–70; no Willow death through100. `blind500-mechanism.json`, replay, source manifest and extraction retain proof. The52-game100M benchmark has41 identical replays and11 changed; identical-subset fuel9,011,059,757→9,010,745,416 (−0.0035%). Whole-game averages are behavior-confounded. Hooks A becomes entirely baseline-identical. Pilgrimage B now first differs1014, preserving baseline's303/311/319 support instead of the broad guard's early recall; its selected final outcome is not strength evidence. This validates the targeted cost reduction without declaring a general gain.

The frozen pair is sealed in `wfollow-blind500-source.json` (SHA `6c83cde497bf45c7210d9c424c65cb59fda97c0b3bf4dbfc5f2184cbd85e5d52`). Ops received the separate standard normal seed215/max1000/jobs4 and doubled seed216/max8/jobs2 launch requests, Flp4/Mt3q, own release drafts. `run_wfollow_blind500.py --check` passes; logs/PIDs are `fg-wfollow-blind500{,200}.log` and `wfollowblind500{gate,200}.pid`. No working501 edits or overlays are included; frozen500 remains the exact base. No owner launch or merge.
