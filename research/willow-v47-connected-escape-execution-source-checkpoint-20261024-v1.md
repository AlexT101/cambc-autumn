# Connected-escape execution with original admission: source control

2026-10-24. Source-only mechanism isolation authorized by root. Cambridge Battlecode rules, `research/willow-v47-connected-escape-outcome-diagnostic-20261024-v1.md` and `research/willow-v47-edge-draft-and-arm-diagnostics-20261024-v1.md` read. No build, run, test/helper/script implementation, SDK/tool changes, canonical edit, EXPERIMENTS change, release or submission.

Baseline f475: `provenance/willow-astraeus-clock-recovery-20261024-v1/workspace/bots/service-base-f7`, verified source aggregate `f475b8521cada611754076822402a266c43be8de76ce0f2b504b268ff3335824`. Reviewed full escape input: `bots/variants/willow-v47-connected-escape-work`, verified aggregate `4b5a71e6535bb7b0ccfec3ad26fa6a1c5cef066807576792384e9966efdc0343`. Both remain unchanged.

Child `bots/variants/willow-v47-connected-escape-execution-work`, src only, no `.cambc`. Manifest `research/willow-v47-connected-escape-execution-source-v1-manifest.sha256`, all29 files; aggregate `fcdf6007cebc9c248f8866142b39be614d38c4e273c983083cdfc722eba500d1`.

Patches:

- Versus f475: `research/willow-v47-connected-escape-execution-source-v1.patch`, SHA256 `ea736617a140369b6af734656f1bd9410dfcd8f7df67f929c7f3d0c624496472`; five files,206 insertions/31 deletions.
- Versus reviewed full escape: `research/willow-v47-connected-escape-execution-vs-full-escape-source-v1.patch`, SHA256 `98aac63994579de138c7725df02f7b07d976e9d0a466b6ac1ade963488824ed5`; only bot.cpp differs, restoring admission.

Construction starts from the reviewed f475-derived escape source and restores the exact frozen f475 admission block and caller. Text comparison from the original camp_exit_rounds comment through the end of want_home (including the next unchanged comment) is byte-identical to f475. That includes the old helper/signature, maxReach+1 healthy exemption, one-step test, geometric ring fallback, original ordered low/outmatched/camp_trapped short circuits and all subsequent enemy-standing logic. No new predicate or threshold is introduced.

The other28 files compare byte-identical to reviewed full escape. Its Pathing walking/ray/native-result/cache helpers, self-ability dash helper and their signatures are unchanged. Within bot.cpp, all reviewed flee/connected dash/retreat execution remains unchanged; only the admission replacement is reversed. No whitespace diagnostics, backup/reject or `.cambc` files. Default draft, params and unrelated gameplay remain f475; no v48, recall, hop, mixed-cast, support-binding or roster overlay exists.

## Callers and retained execution

want_home calls the original camp_trapped without Pathing, which uses original camp_exit_rounds. It cannot allocate or search the connected-escape slot. The only bot callers of Pathing::camp_escape now are camp_escape_step (finite descending flee choice), connected_camp_dash (initial quiet camp dash comparison), and that dash's fresh continuation revalidation. All request the reviewed exact-execution mode; current walking blockers/guard and existing Safety camp-safe goals remain authoritative there.

retreat still uses the reviewed connected camp-only dash seam, otherwise the original visible-enemy dash behavior, followed by connected flee or emergency home fallback. Finite known labels, unknown versus exhausted failure, actual cast/wake/suicide checks, endpoint observation/revalidation and prevention of an appended movement that undoes a successful camp dash remain unchanged. Cache allocation stays lazy and belongs to execution, never each farm candidate.

## Intentional old limitations and interpretation

This control deliberately restores the unsound admission assumption that a safe geometric coordinate implies an exit within maxReach+1. Holes, overlapping ranges and occupied corridors can make actual walking escape longer or absent even while camp_trapped permits work. That is the variable being controlled, not a newly endorsed safety proof. Siege/zero-exposure and already-compelled admission shortcuts remain exactly old behavior.

The reviewed execution limitations also remain: exact-ray-only endpoint coverage can suppress an off-ray camp dash; current-tile DPS reserve is heuristic; Safety's current actor-known aggro/sleep/enemy beliefs are not future guarantees; current blockers can change; unlabelled/exhausted or enemy-constrained routes retain emergency fallback. No new admission refinement, camp-clear prediction or transient-blocker rule was added.

Removing admission's connected query also removes its cost and possible cache prewarming before retreat. Hence this is an execution-only source control, not proof that any resulting outcome difference isolates policy from computation. Existing fuel cutoffs/code generation can still differ. The Elk Arena first fork remains action timing/rollover evidence with four visible enemies; the quiet connected dash cannot be assigned that dash without a private caller trace. No source-known causal explanation, safety improvement, fuel saving or strength claim is made here. Luna owns further native comparison and tracing.
