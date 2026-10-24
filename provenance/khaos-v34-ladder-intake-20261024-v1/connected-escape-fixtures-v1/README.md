# Connected escape source fixture (v1)

Run `python3 build_fixture.py`, then compile and run `fixture.cpp` with a host C++17 compiler. The builder copies the exact production excerpts for `Pathing::CampEscape::at`, `camp_escape_dash`, and the endpoint-selection lambda/loop in `connected_camp_dash`. `SOURCE-PINS.json` records source hashes and byte/line boundaries. Mocks expose only the fields used by the excerpts.

The independent tiny-grid eight-neighbour BFS supplies detour labels. Tests cover ray labels, off-ray unknown, wall rejection, BFS detour, goal-at-origin, exhausted-unreachable and incomplete labels; dash disabled/wake-causing/suicidal/valid paths; endpoint improvement, landing-plus-walk finish, tie breaking by damage/home steps, higher-damage rejection, unknown endpoint, and no strict improvement.

This host fixture does not execute `camp_escape` cache construction/invalidation, SDK calls, or native gameplay. Cache invalidation remains source-reviewed; oracle labels fed to `at()` do not test the native cache.
