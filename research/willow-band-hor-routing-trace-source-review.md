# Band HoR routing trace: independent source review

2026-10-23, Astra. **Source review passes for the narrow economic-group versus route distinction; runtime qualification remains mandatory.** No blocking policy or duplicated-work defect found. This does not establish fuel neutrality or explain the observed reversal. Read the applicable agent guidance, Cambridge Battlecode rules, nomination, checkpoint, actual patch, relevant parent/candidate control flow and replay-harness caveats. No build, game, extraction or tooling implementation performed.

Verified identities using the checkpoint's `shasum -a 256 src/* | shasum -a 256` convention:

| Artifact | SHA-256 |
|---|---|
| Canonical parent `bots/hyperion` | `4db4eecbda37e23dbce0b162d2cf7441a3d32a554d6534cf196e3ffbedcdf2fd` |
| Source-only child `bots/variants/willow-band-hor-routing-trace-work` | `46ab555f9637c1d5d86bcb7da1fa55bbf541515b023966d1e45ee8d2dc44e414` |
| `provenance/willow-band-hor-routing-trace-20261023-v1/candidate-v1-vs-4db.patch` | `03c88aa944de107fd3c65495aef680065520781e4b02c300c67664f2a51bb7ee` |
| Nominated replay, as pinned in nomination/checkpoint | `cdbd5b2619aa504fcaf8ede78ac48ca8d0a85cdda4dad436a75f28c25b879ac7` |

Both 29-file snapshot manifests verify; snapshots equal their respective live source trees byte for byte. Only `bot.cpp` and `pathing.cpp` differ. Target is physical A, actor2 HoR, rounds17–22 of `gen-gen-band-102305906-candidate-A.repl26a` (extract `cdbd5b2619aa504f`). The replay itself was not rehashed or decoded in this review.

The route wrappers preserve Boolean short circuiting and original call order, including ignored cleared-dash results, attack after a successful dash, failed live-route fallbacks and restoration of the previous group. The move wrapper invokes the native move once, retaining successful invalidation, hidden-blocker handling and the caught-error path. Logging does not repeat a guard predicate or force a lazy guard solely to print it. No new gameplay import, visibility/field read, Safety/model computation, group scan, route computation, action or fuel gate was found. All added output is inside `debug_block`; values are cached state, existing locals or scalar/static metadata. Format types and empty-array handling are consistent with their definitions.

The trace can separate selected economic group from actual fallback group: read `farm-enter`, `selected`/`no-choice`, each completed `route`, `previous-route-fallback`, and `decide-done` together. Path logs describe existing field descent/live search and actual move attempts. A stable selected group with routes to a different previous group must not be reported as one unchanged effective target. Conversely, repeated selection of one group with opposing accepted moves is useful evidence of movement toward the same economic work, once the prefix is qualified.

Interpretation limits:

- **Same group is not identical route goals.** Attack tiles, adjacent tiles, approach range, avoidance and occupancy can differ. The patch does not serialize/hash goal bitboards or identify field-cache versions. It can distinguish changing groups from movement under one group; it cannot alone prove that identical geometric inputs produced oscillation.
- **Guard absence is not permission.** `guard-refused` records only `try_move` rejection. Descent filters guarded neighbors before this point, and live search incorporates the guard into walls. Zero candidates or an unreachable route does not isolate guard versus terrain/occupancy/cap. No new probe should be inferred from missing output.
- Route labels follow their call's inner path output and retain that function's return contract. A successful step may be `make_way` yielding to an ally rather than progress along a field; use move coordinates and source context. The logged descent next-value belongs to its first candidate, not necessarily a later attempted neighbor. A false route result alone does not identify the cause.
- Group62 output is a cached belief with observation dates, not current native truth or an affordability verdict. It is reached only after pickup/early-work/stale exits. `decide-done` likewise exists only on normal return; generic path logs can also arise outside farm. Cached `world.round` can lag an actual resumed segment, so join by harness scheduling rather than the printed round alone.
- **Fuel effects are unresolved.** Helper calls, scalar argument evaluation and result wrappers are outside the paused debug body; debug guards are entered even when the actor/window gate rejects. Code generation can change throughout the game. The output gate does not protect round1 or prove unchanged later fuel decisions.

Minimum runtime qualification before diagnosis: pin exact map, engine1.0.3/asset, original injected binaries, parent and child sources, then use the existing fuel-exact recorder/tracer workflow in isolation. Establish the frozen-parent replay prefix against the nominated game; establish recorder equivalence to that prefix; establish tracer equivalence to its recorder through the end of round22. Compare both teams' phase-aware inputs/actions and state hashes, import order/count/hash and responses, fuel observations and exhaustion/resumption points. Explicitly verify actor2's round1 rollover and subsequent interleaving; visible position or acted end-round status is insufficient. Inspect recorder `@x` entry artifacts and first mismatch, and stop causal attribution at the earliest untrusted segment. Matching tracer-to-recorder alone does not qualify recorder-to-original.

Only then classify the witness as changing economic work, incumbent fallback, fixed-group movement, or inconclusive. No safe group62 attack, legal productive dash, specific guard failure, upstream source cause or gameplay repair is established here. The source remains frozen and unbuilt by this review.
