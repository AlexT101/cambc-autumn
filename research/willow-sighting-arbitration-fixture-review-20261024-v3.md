# Sighting arbitration fixture v3: targeted gaps closed

2026-10-24. Source-only review of Luna's preserved fixture and mutation receipts; no execution by reviewer.

**Verdict: all three previously flagged gaps are now closed for the stated host-fixture scope.** No further fixture correction requested. This is not full engine scheduling, caller-dispatch, fuel or match-strength validation.

Evidence under `provenance/willow-sighting-arbitration-4d08241-v3-compile-20261024-v1/fixture/v3/`: independently checked `FIXTURE-RESULT.json` SHA256 `38aac572c2ca1ea90a42ea5255d1201eb4535a8b6ba0239bac2c27b9bdba5fbb`; runner `d0d126c1008b821c25e93429199d94bc791b610097cffafa5efecfae60c7d8cd`; generated C++ `f28e3a296b2fa79d866c56f5d91a8b3982b9ed29f93262921d2b05a1584223fe`. Receipt retains frozen production `comms.cpp` hash `c048d09fd718e21b3d46258533d157ee4a196d40a20e037444ae2bfac9a1b77a` and reports13 passing scenarios.

- Real publication geometry remains basic3 + dash2 + pursuit3, admitting distance6.
- The second same-round send now changes current/native Vesper position to `(26,56)` and health to700/1000. Without the marker, direct same-enemy confirmation would publish a changed position/quantized-health payload. Holding the first record therefore meaningfully tests the marker.
- Both missed-reader cases seed identical nonempty last/current bits, explicitly assert `fresh==0` and nonconsecutive status, then call production `send`. The marker-zero case now reaches the repaired ambiguity rule. The following healthy opposite-parity turn tests normal generation advancement.

Independently inspected the two generated-C++ mutant diffs: each replaces only its targeted guard with `false`. Saved run logs fail the intended assertion respectively: changed same-enemy confirmation blocked by marker, and aliased nonconsecutive contact preserved without another normal generation. These failures distinguish the checks from the previous vacuous challenge setups; production source is unmodified.

Prior v1/v2 findings and receipts remain preserved. This remains a logical snapshot fixture: mocked observation does not exercise actual native visibility changes, and the normal wrap loop is not a full multi-actor ABBA simulation. Those limits are already explicit and do not warrant further test proliferation before interpreting native evidence.
