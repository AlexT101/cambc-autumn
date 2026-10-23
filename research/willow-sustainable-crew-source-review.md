# Sustainable crew: actual source review

2026-10-23. **Corrected source PASS: `69010aea272d211599594c5a9f12b71f54b52ea83ec9f39cbe010541291a7d70`.** Reviewed the complete farm-only delta in `provenance/willow-sustainable-crew-20261023-v1/candidate-v1-vs-parent.patch`, actual candidate source, and final two-correction delta. Independently rehashed v1 as `fc9e0a067eea78f7c8dabc36992300698f2b892a10378c805233f4098a4f7608`; parent is frozen a67. No build/runtime by this reviewer.

## Two required corrections

1. Candidate `src/bot.cpp:2415–2423` lazily computes the nearest help certificate after the final stale-world check at2407. `centre_to_altar` may invoke `to_any_altar` when its cache/draft value is absent; the crew/camp calculations also consume fuel. A rollover here can carry a stale certificate into claim selection and action execution. Move the complete lazy block before the existing final stale check, after the banking early returns. This preserves one existing round check rather than adding a query.
2. `affordable` at1738 changes every ranged invocation of `farm`, including chained banking work called under decision `B`. The bounded contract only changes ordinary ranged farm (`decision == 'F'`). Gate both the damaged-incumbent deferral and removal of the nonincumbent occupancy waiver accordingly; retain parent behavior for melee and nonordinary calls. This is scope preservation, not evidence that the broader policy necessarily loses.

Both corrections were sent to Sol. No additional source blocker found in the remaining delta.

Final correction check: `ordinary_ranged = decision == 'F' && !walk_and_attack_independent()` now scopes both early-admission changes. The complete lazy certificate block now precedes the existing final stale-world check and subsequent claim/crew/farm selection writes. Independently rehashed corrected aggregate69010aea above. Both findings are resolved; no further source correction required before root-authorized compilation/runtime.

## Verified behavior and limits

`crew_clear` preserves the original summed health, respawn waiting, arrival-delayed other damage, remaining health, rounds and raw own share. `crew_hits` preserves the original worked-versus-unworked share and mitigation. Winning reward still uses full value without substituting that full-value share into physical damage. The owner/same-group partner path is unchanged.

The nearest help proposal resets its certificate and retained forecast when replaced. A nonviable or deadline-rejected computed proposal cannot become certified later. A rate-pruned proposal receives at most one final lazy forecast; its already-computed forecast is reused. The lazy deadline is the original formula with zero wait, valid because help nomination requires an alive group. A failed self-affordability check cannot win through unconditional help. This remains the existing proportional crew loss estimate, not a guarantee of teammates' future actions.

Harmless groups retain their first unconditional admission. Existing shared/joint-output and spell-kiting paths remain; excessive nonclaimed damage enters the old risky tier, which remains available when no better choice exists. Actual heal/retreat/capture routines are untouched. The existing partial-resource preference remains. Rejecting help does not prove the actor will retreat or that this game improves.

No new native API, map-wide iteration, persistent ledger or fuel threshold is added. However a newly reached cold existing field lookup can allocate/compute, and factoring can change code generation. Do not read the checkpoint's “no allocations” as a proof of zero transitive cost. Default-fuel tests must measure this; source review cannot certify its performance. No new instrumentation is required before the bounded experiment.
