# Gem Fields Prism action-realization trace

An AR-only source-instrumented (no quote-log patch), normal-debug run of f475 on physical A against the existing recorded physical-B puppet reached a trusted cap through round 7. It reused the existing recorder prefix; no recorder or full match was rerun.

The tracer matched all 225 accepted inputs through round 7 and all 9 round-start hashes through round 8. Its inner replay payload SHA-256 was `6b2adf13426090a8a27a99d4e035a63a102f97ffc77a4cc757279f7d4a25ff7f`, identical to the trusted recorder payload. Host validation matched 45/45 segments with no mismatch, forced-OoF point, native rollover, or bot error in the observed prefix. The capped EngineError18 is the expected end-of-timeline.

In round 6, Prism selected group 4 and reached the approach-cast logic. The source saw 8 targets but only 1 harmful member. Seven already-evaluated ground centers failed the production requirement of at least two harmful hits; the highest rejected value was 400 at `(21,23)` with one harmful hit. No cast was selected, so the code continued to available attack tiles and moved on the `attack-tiles` route. In round 7, the first rejection was a live damaging member of group 4 at distance 4 with reach 4; the same attack-tiles route was available and moved.

The raw log renders the count as `rejected_lt27`: this is the literal tag `rejected_lt2` followed by integer count `7`, not twenty-seven. The AR trace is a source-bound diagnostic only; it does not establish competitive value.

See `TRACE-RESULT.json`, `PRESERVATION-MANIFEST.json`, and `TRACE-ROW.final.json` (the original pending row is retained as history) for pins and exact execution inputs. The accidental-function-rename patch and superseded row remain preserved as correction history.
