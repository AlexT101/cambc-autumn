# BigWorld minimal witness: actual source review

2026-10-23. **Final v4 source review PASS for the bounded action/state-equivalent diagnostic.** Required trace semantics are resolved; runtime validation remains mandatory. Earlier findings below are retained as history. No build/runtime, extraction or source edits by this reviewer.

Reviewed `replays/bigworld-branch-witness-20261023/instrumentation-bot.patch`, `workspace/bots/willow337f-trace/src/bigworld_witness.h`, manifests and `RUNBOOK.md`. Initial trace aggregate independently recomputed as `d7788334d2350105a3015ef459e41246a4260fc19cbd44d4845e43b6ee9ad299`. Patch SHA `8498a844f011a7eae910eb285b3d408f7ab3a7d5d8bd89a16d20c8382251d1b2`; trace-manifest SHA `362359401ec92102fbaf74fddd8981aad506c63127bd097d2479ae26e5ea33d6`; runbook SHA `8b9e0e954b29895c72cb5524a7510f5ba2e032c007e975c58ae37d884224db78`.

The original snapshot and pristine Release source match frozen337f exactly; original emulator snapshot matches10e5. Recorder differs only by the copied `harness_rec.h`. Trace changes only `bot.cpp` plus the witness header and two existing harness headers; wrapper headers match the repository originals. Generated `zz_harness.cpp`/`rec_data.cpp` do not yet exist, so their future generation must be pinned separately; this review cannot certify files not yet generated. The diagnostic deliberately stays337f despite the canonical comms promotion.

## Source behavior

Added rows copy memory/World scalars. `comms::claim_of` is a pure cached-array/alive check, not a host query or evaluator. Loops are bounded by the ally roster and actor0/3, rounds35–75. Formatting arguments/types match. Existing `&&`/`||` conditions and action calls retain their order; the comma-expression incumbent branch becomes the same sequential assignment and call. No added Safety/pathing/farm evaluation, API call, native scratch pointer retention, ownership write or alternate-route enumeration was found.

The row helper's window test/function entry occurs outside `debug_block`, so this is not intrinsically fuel-neutral code. It is appropriate only with the planned recorder/tracer virtualization and segment/replay validation. DebugGuard alone would not establish equivalence. The rows are sufficient for the first same-job/different-job and fallback diagnosis; no broader counterfactual station or full v38 trace port is required now.

## Small required trace corrections

1. `BW-TURN pos/hp` are `world.me()` beliefs, including at `phase=end`; they are not guaranteed current post-action position/HP. Rename to `belief_pos/belief_hp` or define this unambiguously in the schema. Join actual movement/health from validated actions/state later; add no live reads. `actor=me.index` is an ally index and matches native0/3 only for this fixed physical-A setup.
2. `walk_on_kept_previous` currently emits `selected=g`, although the next assignment and movement use `previous`. Record actual target `previous` and, if useful, requested `g` separately. Otherwise the central job-choice witness can be wrong.
3. `passing_attack` and `bank_passing_attack` emit remembered `memory.farm_group` as selected; that does not prove the actual camp hit. Mark actual selected group unknown or label the field remembered job. The existing action import identifies the hit; no extra lookup is needed.
4. The final `walked` summary can be true after the no-search `walk_on(best)` fallback, yet labels it `ranked_route`. Use a neutral `route_result`/success summary; preceding explicit branch rows carry the cause. Likewise a failed direct route followed by a successful dash fallback must not be described as no movement.
5. `BW-CLAIM posted_local` runs before `comms::claim` and far before a possible shared-memory send. Name it next local intent; this is not proof of publication or a newly received claim. The ally claim field is a persistent local belief with an alive filter, not a fresh position report. `evaluated=k/total=evaluated` means scan iterations/scan limit, not number of candidates actually priced (iterations can skip groups); rename or document accordingly.

These are output-semantics fixes, not grounds to add SDK queries or more policy hooks. Capture/support early-return reasons and exact route alternatives remain unlogged; the first witness must acknowledge that limit instead of attributing every skipped farm call to formation.

## Runbook validation details

- After the fixed emulator is built in the debug-enabled workspace using `RELEASE_CODE`, recheck both raw/injected hashes against its original Release pins. The earlier Release-build check alone does not certify the binary selected for recorder/tracer execution. Require default fuel and matching opponent inputs too.
- Trust ends **before** the first differing round/input/state, not “through the first differing input/state.” Require validated prefix through75 for the complete requested window; a later mismatch only permits the earlier trusted portion. Stop if the trace/recorder departs before the route choice being explained.

The rest of the proposed sequence is appropriately narrow: pristine direct Release reproduction, calibrated Release-code recorder, then minimal trace using recorded fuel reads and forced rollover points. Keep original files and each failed run in separate directories. Preserve wrapper count/hash checks, `@x`/`@!` reporting and original per-turn fuel comparison. Once corrections are pinned, source review can pass without expanding instrumentation; runtime fidelity still has to be demonstrated.

## V2 bounded recheck

Independently rehashed the 32-file trace source as `9a1226d7b544f24c1878fc8168237ba9be45eb8fe10fe0d3d475a5a79cc8df9d`. V2 patch SHA `e858213de7948004c5d94d65cb2fae542f93994d65a9abd165bcab74648f0539`; manifest SHA `3d389f39cfdd7519681312c68c9f80b1e90c51a7389a425f0ce0dc3cd251bca1`; reviewed runbook SHA `b2f01179a0dfeeeae04f73b7bd69ff0a57059659d1f55bda508cb109cf219891`.

Belief position/HP, previous/requested target, ordinary passing-hit unknown target, scan iteration/limit and local claim labels are resolved. No new SDK/evaluator/action-order change appeared. Four small residual corrections remain before trace evidence approval:

- `bank_passing_attack` still supplies `memory.farm_group` as selected; use unknown `-1` as in `passing_attack`.
- The final `route_result` is the original `walked` flag. The subsequent fallback `walk_on(best)` return is not assigned to it, so result zero can accompany successful fallback movement. Document this exact flag meaning rather than overall movement success; do not change policy or add reads.
- Runbook step3 must recheck raw/injected emulator hashes after its debug-workspace `RELEASE_CODE` build.
- Runbook step5 must stop trust strictly before the first mismatch, with equality through75 required for the complete requested window.

Root reports Phase1 matched the original exactly (37,230 inputs, 906 round hashes, 4,538 fuel values). That clears the independent reproduction prerequisite, not these tracer-label or later recorder/tracer fidelity checks. This reviewer performed no build or game.

## Final v4 source pass

Independently verified the 35-file tree against the manifest aggregate recipe (concatenated sorted file-hash hex strings): `e27b52f8c6f8c1efd3541cd727cabae267dc57d314565f00669f0834d195a6e7`. The usual bot-directory `shasum -a 256 src/* | shasum -a 256` recipe gives `12a6ae812694f6ab14248b56c72878bd00b7a71ea0945a8a800b139fbdaf09b2`; these are different documented recipes, not a source mismatch. Manifest SHA `a2672364eaf559f37479280bf98f711ed4bb623c25a18ec3b2369a51f27772b6`; incremental v4 patch SHA `d518dfeca107628e8618e1e3e3f0b0a3c897823d5ebde301652fa42cc94e79d2`; reviewed RUNBOOK SHA `66e37c6a31c208b61de9df48cdea9c1c75c3717c33815c7cfae2c69515b69af7`.

The original 29-file source still differs only in `bot.cpp`; the six additions are the witness header, two harness headers and three generated wrapper/data artifacts. This bounded recheck does not independently audit every generated record. Both passing-hit rows now use unknown selected group, the ally claim is explicitly `local_cached_claim`, and prior belief/scan/kept-target corrections remain. No added policy query, evaluator or action change was introduced by the final corrections.

Exact route-row interpretation: its field is named `result` and copies the original `walked` variable. The row is emitted **after** the final unassigned dasher `walk_on(best)` fallback; that fallback cannot change `walked`. Thus result zero does not prove no movement. RUNBOOK's description correctly excludes fallback success but its words “emitted before” and “walked field” are minor documentation inaccuracies, not a remaining source blocker.

Runtime acceptance remains: begin at round1 with the pinned Release emulator; require original/recorder/tracer action and round-state equality through75, all actors' segment call-count/hash matches, matching recorded fuel-call lookups, reproduced rollover points, and no wrapper mismatch through75. Exclude the first differing round and everything after it. Complete recorder yield records cover all five actors through75 (and76); the capped later tail is outside this witness. No full-game tracer claim is warranted.

Phase2 has full-game action/state equality but fuel differences at Willow round4 (+40, coincident with wrapper-entry `@x`) and HoR round470 (+896, unexplained). All35–75 turn totals match. The permitted diagnostic is explicitly action/state-equivalent; exact original internal fuel-read/branch identity is not proved by aggregate turn totals. Use validated trace branch and own-belief evidence for the narrow same-job/different-job question, not unlogged counterfactual choices. No additional recorder or broader instrumentation is required for that scope.
