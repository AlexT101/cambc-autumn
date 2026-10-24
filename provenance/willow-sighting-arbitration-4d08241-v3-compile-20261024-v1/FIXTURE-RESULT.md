# Production protocol fixture v3

The v3 source-bound host C++ fixture passes all 13 scenarios. It compiles and executes the exact production `comms.cpp` protocol functions against thin declared mocks; it does not reimplement the policy. V3 supersedes the archived v1 and v2 receipts and keeps both generated C++ files.

The round-765 positive witness uses Vesper’s actual publication reach: basic attack 3, dash bonus 2, and three pursuit steps. The contact is six Chebyshev cells away. After the first replacement, the fixture presents the same Vesper as a changed current visible contact with a new position and health. Without the same-round marker, that direct-confirmation path would write the new payload; with the marker, bits remain unchanged.

For missed-reader behavior, the fixture seeds the exact same nonempty sighting in `state.last` and current shared memory at an older read round. It verifies the sighting freshness mask is zero and the turn is nonconsecutive before calling production `send()`. Marker-0 and marker-1 cases both preserve the stale sighting and generation; the next healthy consecutive turn publishes normally. A separate normal sender case verifies generation advancement and wrap, alongside the unchanged-contact reader checks.

Guard-sensitivity runs remove each production guard only in generated test C++ and confirm the associated assertion fails: marker removal fails the changed same-enemy second-write case, and nonconsecutive-guard removal fails the exact-alias marker-0 case. Production source and fixture runner remain unchanged by these temporary mutations.

The host fixture does not exercise WASI/native SDK execution, real engine scheduling, caller-side dispatch, match strength, or fuel impact. Full source/compiler and mutant hashes are in [the v3 receipt](fixture/v3/FIXTURE-RESULT.json).
