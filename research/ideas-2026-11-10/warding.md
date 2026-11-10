# Warding: Mite r5, Ad Astra, and ocean498 (2026-11-10)

**Status16:56UTC:** closed for these tested ideas; no ward change promoted. Bush-only rejects; tile/camp arms have no established gain; bounded late200k screen holds with no100k resume/extension. The final conclusion below supersedes the earlier parallel-gate plan.

The observed policies justify targeted tests, not a conclusion that Ocean needs more wards. Ad Astra's sampled wards are exclusively in bushes. Mite places substantially more wards and often leaves one on a camp without gaining immediate information. Ocean has at least as much observed ward-only basic-attack use in these descriptive samples.

## Evidence and limitations

Artifacts: `~/tmp-offload/warding-2026-11-10/`. `jobs.json` names every game, side, map, timestamp and decoded source; `audit.json` contains every measured ward and validation counts. `warding-tools/select_replays.py` selects the sample from existing copied archives; `warding-tools/audit.py` reproduces the analysis with `python3 tools/pooled.py 4 -- python3 research/ideas-2026-11-10/warding-tools/audit.py`. No new platform scrims or downloads were needed.

Forty deterministic hash-selected common map/side cells from 55 available cells compare Mite r5's fixed-v105 games (Nov10 ~06:00) with the latest available Ad Astra game for each cell (Nov9 02:00–22:00). Ocean-v105 is the opposing side in the Mite games. Ad Astra's opponents and both teams' drafts vary. These are descriptions of policies and their realized use, not matched strength or causal ward-value estimates. Five Ad Astra games predate the platform's 05:25 engine change; a matched 35-cell sensitivity subset excluding them preserves the findings below.

| Forty games per team | Mite r5 | Ad Astra | Ocean v105 |
|---|---:|---:|---:|
| Wards | 6,982 | 4,030 | 4,086 |
| Wards per 100 alive champion-rounds | 4.22 | 2.45 | 2.54 |
| On bush tiles | 62.9% | 100% | 74.9% |
| On camp tiles (may also be bush) | 15.6% | 0.4% | 1.5% |
| New visible tiles per placement | 29.15 | 28.39 | 32.37 |
| New bush tiles per placement | 5.24 | 5.78 | 6.16 |
| Placement with a visible enemy within 4 | 4.4% | 13.7% | 5.8% |
| Confirmed ward-only basic attacks / all champion attacks | 344/4,122 (8.35%) | 278/5,409 (5.14%) | 389/4,332 (8.98%) |
| Wards subsequently enabling at least one such attack | 139 (1.99%) | 122 (3.03%) | 143 (3.50%) |

On the 35 cells after the engine change: bush placement remains 64.6% / 100% / 76.8%; camp placement 14.3% / 0.3% / 1.4%; confirmed ward-only attack shares 7.95% / 5.43% / 9.84%, respectively. This is a sensitivity check, not an independent sample.

A ward's new tiles are exact shadowcast sight minus the actor's current personal and previous ward sight. The future-use measurement counts only basic attacks with an identified champion target, not spells, movement, retreat, camp intelligence or effects on teammates' communicated beliefs. Nine attacks (2 Mite, 7 Ocean) had no reconstructed personal or ward sight and are excluded from the confirmed numerator. All 120 decoded cohort views passed extractor hard validation, and every reconstructed placement is within radius 2. Ignoring `teleport_start.f` is necessary: that extractor field can contain an uninitialized (0,0), whereas `teleport_end.to` is authoritative. There is no engine-rule contradiction.

Mite's camp wards add only 2.13 immediate tiles on average; 769/1,088 add none. This supports an information-retention hypothesis, not an immediate-reveal hypothesis. The geometric maximum-new-bush candidate score is descriptive only: it ignores hidden blockers and allied-ward occupancy. It also is not necessarily the opponent's objective. Ocean already achieves that geometric maximum more often than the others in the whole sample.

## Placement timing

A second pass over the same 120 cohort views separates current-turn reveal from retained information (`warding-tools/timing.py`, artifacts `timing.json` and `timing.log`). Ad Astra moves before 3,551/4,030 placements (88.1%); no observed placement is followed by movement or a cast by that actor in the same turn, and only 14 are followed by a basic attack. None of its 278 confirmed ward-only champion attacks uses a ward placed in that same turn. Mite has 19 immediate ward-only attacks enabled by 12 placements, versus 325 later attacks; Ocean has 23 immediate attacks enabled by 21 placements, versus 366 later attacks.

Thus Ad Astra's higher frequency of placements near visible enemies does not establish an aggressive early-reveal policy. In these games, its observed attack use is entirely later-turn information. Ocean's current early reveal mechanism has measurable immediate use and remains enabled in all experimental arms. Spells and non-attack information value remain unmeasured; this timing comparison inherits the cohort confounds above.

## Current Ad Astra cross-check

A separate 40-game sample from eight completed ranked groups on **November 10, 09:27–10:40 UTC** confirms the placement/timing pattern: **4,017/4,017 wards are in bushes** (18 also overlap a camp tile), 3,546 follow movement, none are followed by movement or a cast, and only one is followed by a basic attack in the same actor-turn. All 334 confirmed ward-only basic attacks use an older ward; zero immediate ward-only attacks are observed. The ward rate is 2.69 per 100 alive champion-rounds. Combined with the dated archive sample, all 8,047 observed Ad Astra placements are bush placements, but neither the groups nor placements should be treated as independent strength trials.

This is a separate current-policy cross-check, not a matched extension of the earlier cohort comparison: it faces eight different opponents, five games each. Public group metadata withholds submission versions, so the result confirms observed behavior, not an unchanged build identity. Existing local folders had metadata but no replay bodies; forty existing ranked replays were downloaded through the supported replay/CLI path, with no new scrim groups or submission changes. All forty decoded games pass hard validation. Exact group selection, match IDs and analysis are in artifact `current-group-selection.json`, `current-adastra-jobs.json`, `current-adastra-timing.json` and `current-adastra.log`; the reproducible analysis is `warding-tools/current_adastra.py`.

## Potential camp information

`warding-tools/camp_information.py` counts clear/capture/respawn transitions for which the owner's ward sees a group member while the owner's personal sight sees none. These are **potential first-hand observations**, not proof that the bot read or acted on them, and not necessarily new team knowledge: a teammate could already know and communicate the state. Each owner/transition pair counts separately. The ward remains active while its owner is dead, which is reported separately.

| Forty games per team | Mite r5 | Ad Astra | Ocean v105 |
|---|---:|---:|---:|
| Ward-only camp-state observer/transition pairs | 3,510 | 3,648 | 3,727 |
| Of those while the owner is dead | 821 | 923 | 1,068 |
| Alive-owner observations per 100 alive champion-rounds | 1.62 | 1.66 | 1.65 |
| Wards covering at least one such transition | 1,564/6,982 | 1,132/4,030 | 1,075/4,086 |

Mite's camp-tile wards cover 705 of its observer/transition pairs; 215/1,088 cover at least one transition. Ocean's non-bush wards account for 1,649/3,727 pairs (1,095 while alive), despite only 1,027/4,086 placements being non-bush. Thus the bush-only ablation trades away substantial potential camp coverage; more frequent Mite placements do not establish a higher overall information rate. Information value, opponent coverage, camp rewards, durations and decision use differ, so these descriptive counts cannot replace the game gates. Artifacts are `camp-information.json` and `camp-information.log`.

## Prior null results and new experimental questions

The [earlier Mite study](../ideas-2026-11-08/mite-wards.md) tested extra fresh-bush wards, broad camp wards and removing the reveal-ward combat gate on the older oc-base25. Their large samples were approximately level. Broad camp scanning increased out-of-fuel turns by 36%. These variants therefore do not blindly repeat those implementations. CHANGES473 already made planned-ward site scores and ward sight masks exact, but explicitly deferred exact turn-end bush tile ranking for fuel risk.

All new arms derive from **`variants/oc-campsh-498`**, the full frozen working498 including fuel497. Commit2905 alone omits fuel497. No arm stacks another ward experiment, modifies opponent bodies, changes drafts, or modifies working Ocean.

- **`variants/oc-wtile-498`** keeps the existing bush cluster selection, replacement trigger and candidate restriction. Within that chosen cluster, it ranks candidate tiles by actual ward sight covering tiles within ability range of the actor and its claimed work. Stable ties preserve the first tile; a 7,000-fuel floor bounds the search, and existing first-three placement fallback remains. This tests the previously deferred exact tile ranking, including its runtime cost.
- **`variants/oc-wbush-498`** disables only planned wards on non-bush tiles and falls back to Ocean's existing bush policy. Bush planned wards and combat reveal wards stay unchanged. This Ad Astra-inspired ablation asks whether non-bush planned wards are useful relative to conserving/reusing the ward for bushes; it is not a reconstruction of Ad Astra's whole policy.
- **`variants/oc-wcamp-498`** adds a fallback only when no planned ward applies and the existing bush policy placed nothing. It looks only at camp tiles within radius 2, requires a known cleared/respawning group, and keeps an existing ward within 8 tiles. Its fixed local board scan avoids the older whole-map camp scan. A 7,000-fuel floor bounds attempts. This tests a cheap form of Mite-style retained camp information; it intentionally does not copy every camp placement.

`warding-tools/prepare.py` reproduces these source changes and refuses to overwrite existing arms. `warding-tools/sources.json` records the sealed source fingerprints; the artifact `source-manifest.json` lists every source file hash, with exact patches beside it. The frozen base source fingerprint must equal the queue's known full 498 fingerprint `d0a0755075bf4010dc1ac96e7b209aafd3791ba1a8bc1c3b625d56e55f38a23e`.

## Alive-camp follow-up

The event-level camp-state audit (`warding-tools/camp_timing.py`, artifact `camp-timing.json`) shows that Mite placed 686/1,088 camp wards on **alive** groups, 269 on cleared groups and 133 on respawning groups; only two replaced a ward on the same group. This uses actual `group_clear`, `capture` and `group_respawn` transitions, not copied reward metadata. Spot-checked event sequences place the ward before subsequent monster deaths, confirming that the alive classification is meaningful.

Accordingly **`variants/oc-wcampall-498`** adds a matched ablation of the dead-group restriction: it copies the sealed cheap camp arm and removes only that condition. Its radius-2 scan, nearby-old-ward retention, fuel floor and priority below planned/bush wards are unchanged. The original dead-camp arm is retained unchanged, so their separate gates can show whether alive-camp information is worth including. Both get normal and doubled fuel gates. This follows the observed Mite policy more closely without reviving the previous expensive whole-map scan.

## Planned-ward timing ablation

Ocean already places its routine end ward after movement, strike search, healing and shielding. Its early planned-work ward call and early reveal call are the distinct cases. The five ward helpers are byte-identical between frozen v105 and full 498 (`ward-helper-identity.json`), so the live timing sample is relevant to the current policy. At least 379/4,086 Ocean placements (9.3%) are observably early: a move, attack or cast follows. Of those, 179 are non-bush and therefore planned-work wards; 200 bush placements can be planned or reveal. Ad Astra has only 14/4,030 such cases in the archive sample and 1/4,017 today. Placements with no later action do not reveal which internal phase placed them.

**`variants/oc-wlate-498`** removes only the pre-decision `place_ward(world, memory, false)` call and its immediate re-observation. Planned wards remain enabled at turn end, from the chosen end position and updated work; early reveal stays enabled. This differs from the bush-only arm because non-bush planned wards remain available. Deferral also avoids the early check's fuel cost and can let reveal use the ward first; the resulting effect is not a pure isolated clock-time intervention. It is a narrow implementation ablation of that early planned call.

Sixteen additional release smoke games pass error, draft-handoff and hard replay checks; all sixteen ordered drafts match the base. On the same eight cells per budget:

| Mechanism | Base normal | Late planned normal | Base doubled | Late planned doubled |
|---|---:|---:|---:|---:|
| Total placements | 1,171 | 1,149 | 1,120 | 1,076 |
| Followed by movement/attack/cast | 132 | 16 | 140 | 17 |
| Of those, non-bush | 90 | 0 | 96 | 0 |
| All non-bush placements | 448 | 451 | 425 | 410 |
| Immediate ward-only basic attacks | 8 | 7 | 3 | 3 |

Thus planned non-bush placement remains, while all remaining observably early placements are bush reveals. Immediate ward use still occurs. These trajectory-dependent smoke counts establish mechanism, not strength; the new arm's normal/doubled out-of-fuel counts are 38/0. Artifacts `late-timing.json`, `late-draft-checks.json`, `verified-late-smokes.json`, and `warding-tools/late_timing.py` reproduce the checks. Two further gates keep budgets separate and the original eight gate commands and sources unchanged.

## Matched fuel gates

Each arm gets separate normal-budget and `--fuel 200000` fresh gates against the same frozen base. Both candidate and reference face the same Flp4/Mt3q bodies, noise blocks, maps and sides within each fuel condition. Both teams receive the selected budget; this scales the engine's first-turn/draft allowance too, so the raised-budget comparison measures the whole game under that budget. Do not pool the two budgets or interpret their difference as a clean estimate of only our ward-search cost.

`fgate.py --fuel` passes the value to ab.py and appends `-fuel200000` to game, lock, log and final result names. Cache acceptance also requires matching summary fuel metadata; normal-budget names remain unchanged. Three tests check unchanged normal names, all nine selected/cached budget combinations, and the actual launched command. Raised-budget `--no-run` reads zero normal-budget cells.

The queue should run these ten behavior gates before pending draft/tuning rounds, without interrupting active jobs. They share reference results only within a matching budget and retain the normal sequential gate interpretation: high-H0 alone is not rejection, and narrow results require judgment. There is no strength conclusion or promotion at preparation time.

## Preparation validation

All three release builds passed. Four maps (`00ambush`, `00breadcrumbs`, `00great-wall`, `00lanes`), both sides against frozen `spar-dvn1-Mt3q`, cover base plus three arms at both budgets: **64 successful games, zero errors, early losses or draft handoff failures**, and identical ordered drafts for every arm/reference cell. The first fixture used replay-normalized `00great_wall` rather than the real `00great-wall` filename; those failed jobs played no games and are excluded. Corrected fixtures passed before queue admission.

All 64 extracted replays pass hard validation. The smoke confirms actual mechanisms: bush-only produces 599/599 bush wards at normal fuel and 617/617 at doubled fuel; camp-watch produces 301/274 camp wards versus base46/42. At doubled fuel, exact tile ranking's first differing event is a different ward destination in four cells, and the other four cells are identical; normal fuel also exhibits earlier fuel-sensitive trajectory changes. The replay checks are in artifact `mechanism.json`, with first divergences and source replay paths.

Normal-budget candidate out-of-fuel turns across the eight games are base34, tile33, camp37, bush45. All are zero at doubled fuel (both teams). These are a mechanism smoke, not a cost benchmark or a win-rate estimate: altered trajectories change both game length and workload. Fresh gates determine usefulness.

`queue-commands.json` in the artifact directory names the ten wrapper commands; queue operations owns admission and ongoing execution. The wrapper checks the sealed base/arm hashes on every start. Neither opponent pinning nor live submission selection is part of these experiments.

The alive-camp follow-up adds 16 successful release smoke games, all with matching drafts and passing hard replay validation. It produces 422/410 camp wards at normal/doubled fuel versus 301/274 for the dead-camp arm on the same eight cells. Its out-of-fuel counts are 26 and 1, respectively; these are trajectory-dependent smoke counts, not a fuel benchmark. Its validation is separate in artifact `verified-campall-smokes.json`, while `mechanism.json` now covers all 80 games.

## Exact tile ranking: completed fuel gates

Both gates finished successfully against the same sealed full 498 reference, fixed Flp4/Mt3q, own drafts, native release 5.0.1. Deltas and interval half-widths below are percentage points from the configured fresh gate.

| Play budget | Blocks / fresh paired units | Fresh | Fresh Fish | Fresh Mite | Ladder | Stop |
|---|---:|---:|---:|---:|---:|---|
| 100k | 52 / 6,656 | +0.101±0.249 | +0.060±0.339 | +0.143±0.361 | −0.394±0.295 | NARROWED (ZONE crossed) |
| 200k | 34 / 4,352 | −0.270±0.247 | −0.322±0.326 | −0.218±0.367 | −0.195±0.297 | NARROWED |

There is no established normal-fuel gain; the raised-budget interval is just below zero. Neither arm reached the acceptance screen. Raised low LLR −2.286 did not cross the formal rejection threshold, so its label remains NARROWED. **Do not promote this tile variant or pursue a cheaper version on the theory that extra fuel rescues it.** The independent bush, camp and timing experiments remain pending.

A secondary matched comparison uses the common first 32 complete blocks, balancing all eight fresh slices and averaging repeated noise observations within each of 1,024 maps: normal +0.232±0.317, raised −0.238±0.257, raised-minus-normal−0.470±0.428. These are conditional descriptive map-level intervals, not additional sequential gate decisions. This balanced subset differs from each full terminal sample. Both teams receive the larger budget, including larger initial allowances, so the interaction is about the whole game and cannot isolate ward-search cost.

Actual fgate/ab.py descendants were verified at both starts, including `--fuel 200000`, fixed bodies, own drafts and native private-pool settings. All eight first raised-block summaries (arm/base × opponent × ladder/fresh) report 200k, 256 games each, 0 errors; source seals still match. Raw results: artifact `results/tile-{100000,200000}.json`; secondary comparison `paired-fuel.json`; startup evidence `tile-raised-start-validation.json` and `gate-process-check.json`.

Parent-prioritized wakeheal2 normal/raised work follows tile200k in the queue; the remaining ward/reserve conditions and source seals are retained.

## Bush-only doubled fuel rejected, 2026-11-10 14:46 UTC

`oc-wbush-498` at200k versus full498 crossed the low rejection boundary after130blocks/16,640 fresh paired units: **REJECT**, fresh−0.625±0.391 percentage points, lowLLR−3.141/high−7.852. Fish+0.066±0.528, Mite−1.316±0.574; ladder−0.014±0.381. This arm preserves immediate reveal but forbids non-bush planned wards. Ad Astra's observed all-bush placement does not justify this restriction in Ocean at the tested doubled budget. No promotion. Normal100k remains running and gets its own terminal decision; do not transfer this result to that condition or infer the mechanism from subgroup means alone.

Raw copy: `~/tmp-offload/warding-2026-11-10/results/bush-200000.json`. The released controller slot started cleared-camp200k using the newly reviewed main86 pool; actual fgate790343 has fixed Flp4/Mt3q, full498 and --fuel200000. Existing private bush100k/camp100k processes remain unchanged; the private reservation remains until they drain.

## Bush-only branch closed, 2026-11-10 15:16 UTC

Normal fuel also formally **REJECTED** the bush-only restriction: 216 blocks / 27,648 fresh paired units, fresh **−0.427±0.307 percentage points**, low LLR −3.070 / high −10.701. Fish −0.148±0.419, Mite −0.705±0.446. The old ladder maps read +0.716±0.300, while fresh maps lose; the pooled +0.145±0.215 is therefore not evidence for promotion.

Both normal and doubled fuel reject this arm. Retain planned non-bush wards and close the bush-only branch; no cheaper version is justified by these results. This does not establish which information or action caused the losses, or that the difference between budgets is significant. The separate camp and timing arms continue. Raw terminal copies are `results/bush-100000.json` and `results/bush-200000.json` under the ward artifact directory.

Alive-camp normal has now started as fgate1485551 in main86. Its actual command uses the sealed candidate/full498 reference, fixed Flp4/Mt3q and default normal fuel. Both source seals were rechecked. Cleared-camp normal remains the last private-pool ward controller; no game was restarted.

## Cleared-camp normal gate unresolved, 2026-11-10 16:26 UTC

Cleared/respawning-camp fallback `oc-wcamp-498` versus full498 completed325blocks/41,600 fresh paired units at normal100k: **NARROWED**, fresh−0.117±0.250pp (Fish+0.036±0.343, Mite−0.270±0.363), ladder−0.008±0.249. LowLLR+0.120/high−11.422; no acceptance, formal rejection or ZONE crossing. No established gain and no promotion. This single-budget result does not resolve the separate alive-camp inclusion or timing hypotheses; doubled cleared-camp and both alive-inclusive conditions retain their own terminal decisions.

The last legacy private-pool controller ended16:26:21. Ops drained and retired its accounting quota before starting alive-inclusive200k in main86 at16:26:48. Independently checked actual fgate3392268 and descendants, exact200k/native/fixed Flp4/Mt3q/base, pool metadata and unchanged source seals. No evidence process restarted. Raw result `~/tmp-offload/warding-2026-11-10/results/camp-100000.json`; start evidence `campall-raised-start-validation.json`. Paired camp-scope analysis waits for both terminal samples and uses only common balanced blocks.

## Alive-inclusive camp normal gate unresolved, 2026-11-10 16:35 UTC

`oc-wcampall-498` at100k versus full498 completed335blocks/42,880 fresh paired units: **NARROWED (ZONE crossed)**, fresh+0.080±0.250pp, Fish+0.375±0.340, Mite−0.215±0.363; ladder−0.120±0.252. LowLLR+3.161/high−8.378. Neither acceptance nor formal rejection; no established overall gain or promotion. More camp placements in the mechanism smoke do not establish usefulness.

Both normal-budget camp arms are now terminal. On common first320blocks, balanced across1024maps and averaging repeated noise within each map, alive-inclusive minus cleared-only is **+0.210±0.340pp** (Fish+0.374±0.445, Mite+0.046±0.464). These conditional descriptive map intervals are not a new sequential decision or independent confirmation; they do not establish that dropping the state restriction helps. Separate full terminal gate samples remain primary. Wait for both doubled-budget conditions before discussing a budget interaction; no extra normal-budget camp arm is justified by this evidence alone.

Read-only terminal cache audits passed exact256-cell map/side coverage and correct source/body/fuel/release metadata for2600 cleared-only summaries and2680 alive-inclusive summaries; zero run errors, early losses and handoff failures. Own capped drafts0; opponent capped counts3615/3725 per corresponding arm/reference, retained unchanged. Shared reference games are not additional independent evidence. Artifacts `results/campall-100000.json`, `campall-normal-terminal-audit.json`, and `paired-camp-scope-normal-terminal.json` under `~/tmp-offload/warding-2026-11-10/`.

## User-corrected screening policy and camp closure, 2026-11-10 16:43 UTC

**200k is the behavioral screen;100k follows only a demonstrated fresh-map gain.** The earlier parallel full-budget programme is superseded. Completed evidence is retained, not rerun or relabelled. No new strength gate is required for fuel-only cuts accepted as behavior-preserving by their implementer, including incidental identity exceptions; the cancelled501 gate is separate from these behavioral screens.

Cleared-camp200k naturally finished before intervention:317blocks/40,576 fresh units, **NARROWED (ZONE crossed)**, fresh+0.143±0.250pp, Fish+0.185±0.339, Mite+0.101±0.366; ladder−0.400±0.245. It has no established gain. Both100k camp arms had already completed without a clear overall gain, and no concrete cheaper camp follow-up was supported. Coordinator closed both current camp implementations. The still-running alive-inclusive200k was policy-stopped16:41:33; its partial observations are retained as stopped/no inference, not rejection or a completed budget interaction.

A queue race had started late-ward100k16:39:18 as cleared-camp200k ended. Ops stopped it at16:41:33, preserving its one completed block and partial batches; it supplies no strength conclusion and remains held. Existing source/body/cache identities stay unchanged. Source-sealed late-ward200k had not played and now runs a bounded screen, launched16:43:18 as fgate3916319 in main86. Its verified command adds `--max-seeds8 --ci0 --ahead0` to the original200k condition, with no extension. A legitimate existing early statistical stop may end before8; an interrupted or erroneous run cannot qualify.

`warding-tools/late_screen.py` is a read-only terminal evaluator. It requires correct source/body/fuel/engine metadata, complete exact map/side cells for both arms/opponents, zero run errors, and agreement between recomputed paired fresh estimate and terminal output. The fresh paired95% lower bound must exceed0pp. It preserves all early-loss/capped outcomes. A positive screen makes100k eligible for **explicit** coordinator admission; completion, NARROWED, a positive point estimate, or a cap without a positive interval does not. Otherwise hold without calling rejection, and do not extend to chase a gain.

The normal late-ward wrapper refuses without `--screen-admission` pointing to an explicit coordinator record that hashes the valid positive proof and matches the frozen sources. It never creates admission itself. Three focused tests cover early-stop/cap validity, interval boundary and rejected admission conditions, all passing. Only the read-only ward watcher restarted to reflect policy-stopped/held states (now3973959); no evidence job was restarted. Artifacts `late-screen-protocol.json`, `late-screen-start.json`, and per-job `policy-stopped.json` retain the transition.

## Programme conclusion: tested warding ideas closed, 2026-11-10 16:56 UTC

No tested ward change supports promotion; retain Ocean's existing ward policy. The Ad Astra and Mite observations motivated useful tests but do not show that their ward choices cause their strength or transfer directly to Ocean.

| Frozen full498 change | Normal100k fresh delta | Doubled200k fresh delta | Conclusion |
|---|---:|---:|---|
| Exact tile ranking inside chosen bush cluster | +0.101±0.249pp, NARROWED(ZONE) | −0.270±0.247pp, NARROWED | No established gain; no cheaper variant justified by a fuel-rescue theory. |
| Bush-only planned wards, keeping early reveals | −0.427±0.307pp, REJECT | −0.625±0.391pp, REJECT | Reject this restriction; retain non-bush planned wards. |
| Cleared/respawning-camp fallback | −0.117±0.250pp, NARROWED | +0.143±0.250pp, NARROWED(ZONE) | No established gain; close current implementation. |
| Camp fallback including alive groups | +0.080±0.250pp, NARROWED(ZONE) | Policy-stopped partial; no inference | No established normal gain or supported cheaper follow-up; close current implementation. |
| Defer early planned wards until turn end | Policy-stopped partial; no inference | Bounded8-block screen−0.439±0.777pp, HOLD | No demonstrated screen gain; no100k admission/resume and no extension. |

The late screen completed1024 fresh paired units at its cap. Its independently recomputed lower95% bound is−1.216pp; all64 summaries have complete exact paired cells, matching source/body/fuel/engine/release metadata and zero run errors. The screen's raw fgate outcome is undecided; HOLD is the programme decision, not formal rejection. `late-screen-proof.json` retains every summary/results hash and draft counters; `results/late-200000.json` preserves the terminal output. The stopped normal partial is not counted as a confirmatory test.

Retained opponent findings: Ad Astra's observed ward placements are consistently in bushes and almost always after movement, with almost no subsequent action; Mite often wards camp tiles, including alive groups, and keeps later camp transitions in owner sight. Ocean already has useful non-bush planned wards and routine post-action placement. Replay-observed sight is not evidence that a bot read or used that information, and public Ad Astra metadata does not prove a single exact build. Fixed local Flp4/Mt3q bodies are useful controls but do not reproduce every latest-live policy.200k changes both teams and initial allowances, so it cannot isolate only our ward computation cost.

There is **no additional ready ward variant supported by this programme**. A concrete remaining diagnostic question is which lost non-bush observation causes the bush-only arm's fresh-map losses; those formal losses support examining existing paired trajectories, not another speculative placement restriction. Likewise, a new retained-camp-information arm would first need an exact replay showing that missing camp state causes a wrong Ocean decision and that a feasible ward supplies it. Placement counts and opponent correlation alone do not meet that bar. No further ward runs are launched or queued from these questions.

The earlier full parallel budget design is superseded by the user's200k-first behavioral screening policy. Sources/caches/complete results and policy-stopped partials remain intact. The now-idle read-only ward watcher3973959 was stopped after exact identity verification; no evidence process changed. Existing reserve, Skirmish and cumulative outcome ownership continues separately.
