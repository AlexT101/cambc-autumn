# Skirmish fifth-emblem policy on full Ocean498

The teammate's policy has a small positive but unconfirmed lead. It can be tested on full498 without carrying any other old behavior: the original reference's emblem table is byte-identical to full498's. Nothing is merged or promoted.

The original `oc-emb4-f4-skirmish` versus `ocean-b0eeff1` changes only `economy/emblem_table.h`: place Skirmish in the champion's usual stat at ordinal4 (the fifth new emblem), for the37 rows without Skirmish by then. Two other rows already have it. Later duplicate passive-family choices fall back to existing logic. There is no new fitting or ordinal selection in this follow-up.

Older evidence remains separate:

- The teammate reported50.55% over61,440 held-out games across three suites. This was one of several families/ordinals considered; it is supporting evidence with a selection history.
- The original normal-fuel Flp4/Mt3qro gate was continued from its existing32 blocks, preserving every cell. At82 blocks/10,496 fresh units it reached ZONE: fresh+0.326±0.382 percentage points, Fish+0.562±0.522, Mite+0.091±0.552. No acceptance screen/live bar. This continuation is the same accumulated evidence, not another independent confirmation.
- Full498 contains later changes, and the current fixed Mite body is Mt3q. Neither this base change nor the body change permits pooling old and new results.

Frozen `oc-skirmish5-498` copies full `oc-campsh-498` and replaces only that table with the exact original candidate table. All37 changed cells are at ordinal4, belong to Skirmish family11 and have no earlier Skirmish in the original row. Aggregate source seals and the reconstructing patch are in [skirmish-tools](skirmish-tools/); per-file hashes and old/current source differences are retained under `~/tmp-offload/skirmish-498-2026-11-10/`. Base source remains `d0a0755075bf4010dc1ac96e7b209aafd3791ba1a8bc1c3b625d56e55f38a23e`; candidate is `acb1529659de24147f0c569cc068f15ae764df3f5cd6b268c844bad39690a6ba`.

Release build passed. Sixteen normal-fuel smoke cells cover four maps, both sides and Flp4/Mt3q; the matching16 full498 cells were reused from the reserve study. All32 replays pass hard validation, all16 ordered draft pairs match, and there are zero game errors, early losses or draft handoff failures. Twelve event trajectories change and four remain identical. Among our champions completing five emblems, Skirmish appears by the fifth in28/28 candidate instances versus5/31 base instances. Different trajectories change who reaches five, so these are mechanism observations, not a strength estimate.

The prespecified next test is one standard transfer gate: full498 reference, fixed Flp4/Mt3q, release own drafts, engine5.0.1/native, normal100k fuel, seed311 and the standard fresh-map stopping rules. Run names are new; source seals are checked at startup. This uses the established gate map pool, so it is not a new independent map confirmation. Any promising result must be confirmed on genuinely unused ladder-v2 maps, on the then-current frozen Ocean source before a strength or merge claim. No extra ordinal/family variants are being selected from these results.

Queue ops admitted the command in `queue-command.json` at14:57:39 UTC after already-ready behavior work, including the reserve bundle, and before draft10 continuation/new draft/tune rounds. An independent locked reread verified unique ID, exact argv and ordering; `admission.json` and `admission-verification.json` retain the record. Command: `python3 research/ideas-2026-11-10/skirmish-tools/run_gate.py oc-skirmish5-498 --jobs 4`. This owner retains interpretation; ops owns launch and health. There is no new live queue entry, submission change or repin.

To reconstruct an absent candidate, use `./copybot variants/oc-campsh-498 variants/oc-skirmish5-498`, then apply `skirmish-tools/skirmish5.patch` with `git apply --directory=bots/variants/oc-skirmish5-498`. Never replace an existing sealed variant.
