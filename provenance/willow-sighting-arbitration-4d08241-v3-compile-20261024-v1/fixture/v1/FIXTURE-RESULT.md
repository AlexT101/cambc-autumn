# Production protocol fixture result

The source-bound host C++ fixture passed all 10 scenarios. It extracts the exact production `comms.cpp` slice from `namespace aph::comms` through the functions before `void bag(int gems)`, then compiles and runs those functions against declared thin mocks.

The positive round-765 witness replaced a duplicate Heart of Ruin contact with a locally actionable Vesper contact. It preserved unrelated bag, camp, and claim masks, left the ordinary generation unchanged, set the single-replacement marker, and refused a second same-round replacement. The moved/no-refresh case refused replacement; the unmoved case used cached observations without calling `observe()`. Other scenarios cover normal publication freshness and generation wrap, missed-turn dating and alias rejection, and tribute/teleport/winning/nonlocal/stale-candidate exclusions.

This checks the production protocol functions with mocked observations. It does not exercise WASI/native SDK execution, real shared-memory scheduling, or match strength. Compiler warnings were limited to two unused mock constants. See `fixture/FIXTURE-RESULT.json` for source, generated-code, and compiler pins.
