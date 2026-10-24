# Sighting arbitration fixture: independent source review

2026-10-24. Read-only review; no fixture execution, build, script implementation, game or replay extraction. Willow-first manipulation batches are excluded.

**Verdict:** the initial fixture meaningfully exercises extracted production functions, but its reported pass does not yet establish the actual round-765 geometry or the two critical publication bounds. These are fixture coverage corrections, not new gameplay-source blockers or reasons to expand/delay the first native pair. Root has assigned a preserved, versioned fixture revision to Luna.

Evidence directory: `provenance/willow-sighting-arbitration-4d08241-v3-compile-20261024-v1/fixture/`. Independently checked initial runner `production_protocol_fixture.py` SHA256 `ab620976a5e6ac61c0e73bfee10cb038073aa30898a42926bc2ff1d39a4fd51a`, initial `FIXTURE-RESULT.json` SHA256 `f64bec0e9515713189e472d5956b49fd3c473e2bb4f722d7745e146df65006f8`. Production `comms.cpp` SHA256 `c048d09fd718e21b3d46258533d157ee4a196d40a20e037444ae2bfac9a1b77a` matches the receipt and frozen v3 aggregate `a439a6c2d1d1d2ef1004f3a463b243d1f48d2daa65eada801d83f55c5c17a2df`.

## What the initial assertions establish

The runner extracts the actual namespace through `send`, rather than duplicating the arbitration algorithm. Its independent bit encoder/decoder gives useful checks of enemy-index replacement, unchanged generation, used-marker setting and bag/capture/claim preservation. Direct protective cases exercise tribute, teleport, a known winning bag, distant candidate and stale candidate stats. Moved/no-refresh and unmoved cases check whether observation is requested. Changed records after missed turns are dated conservatively; unchanged aliases are not treated as fresh. These are concrete checks under the supplied mocks.

## Three narrow corrections

1. **Use real Vesper geometry.** Runner line101 assigns basic range5 and dash range3, yielding publication reach11 including pursuit. Production facts are ranged basic3 and dash2 (`champions.h:69,88,126–127`), with pursuit3 (`params.h:58`): reach8. The historical sender `(19,56)` or post-move `(19,57)` is distance6 from Vesper `(25,56)`, so it still qualifies. Correct the mocked facts/slot rather than describing the oversized fixture as the original witness. The synthetic incumbent `(80,80)` and quantized health also make this a logical scenario, not an exact replay reconstruction.

2. **Exercise the corrected missed-reader send path.** `missed_gap()` at lines145–150 only calls `expect/receive`. It never reaches v3 `send`'s `!state.consecutive` occupied-record rule. The faulty v1 would also pass this receive-only assertion. After a marker-zero aliased current-parity receive, call production `send` with a visible alternative and assert the incumbent generation/payload stay unchanged; cover marker-one in the same bounded scenario and ordinary publication after the later parity change. This tests the actual v3 correction without an engine match.

3. **Make the second rewrite otherwise eligible.** The second same-round `send` at line127 receives no changed live contact. Even if the marker refusal were removed, native confirmation can find the same payload and retain it, so this assertion does not independently prove the one-replacement bound. Change the current/native same-enemy fix before the second send, or give a second logical writer a qualifying alternate fix, then assert the used marker prevents the rewrite. The expected result should be stated independently of the production nomination predicate.

The normal-publication loop alternates parity and resets reader state each iteration; its wrap assertion confirms counter arithmetic, but it is not a multi-writer ABBA scheduling test. This limitation should remain explicit rather than inflating the existing result into a complete protocol proof. The targeted send-bound corrections above are the useful immediate work.

## Scope limits retained

Mock `observe()` only increments a counter, so the pass does not demonstrate actual visibility recomputation, disappearance after movement, or stale-world interruption. No current ally is used to qualify the witness, so the current-vision ally check is source-reviewed rather than exercised here. The protected cases are valid counterexamples under explicit known beliefs; they do not prove hidden high-value information is available. Support payload behavior and native scheduling are outside this fixture's thin mocks.

New-protocol fields are constructed logically; there is no old raw counter injection or old-protocol teammate mixture. Keep that property in the revision. The source review remains `research/willow-sighting-arbitration-4d08241-source-review-20261024-v3.md`; runtime fuel, actual receiver guard changes and match effects remain separate evidence.
