# Equal-ray geometry fixture (v1)

Run `python3 build_fixture.py` from any directory. The script verifies the reviewed source aggregate, extracts the exact `Pathing::CampEscape::at` body, the shortest-ray update loop, the post-loop exactness assignment, and `directions[8]`, emits `fixture.cpp` and `SOURCE-PINS.json`, then compiles and runs the assertions. A host mock supplies the `any_within` query. The two-ray ranking witness uses an independent exposure/home oracle; it does not copy the production caller's ranking implementation.

Cases cover the old unique-ray labels, two equal shortest rays, refusal to retain a longer ray, a blocked ray, a nearer off-ray goal that makes the ray bound non-exact, mocked field-label `at()` behavior, exhausted/uninitialized results, off-ray/beyond-ray uncertainty, and refusal to use a stale result after invalidation. The positive ranking witness chooses the east ray even though north was discovered first because east has a lower mock exposure.

This executes exact production excerpts against declared host geometry mocks. It does not execute `Pathing::camp_escape`'s cache-key/rebuild logic, native distance-field construction, the actual route-ranking caller, SDK/executor behavior, or gameplay. The stale-result check flips `valid=false`; it is not a cache invalidation integration test. See `SOURCE-PINS.json` for the complete limits.
