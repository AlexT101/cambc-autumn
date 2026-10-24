# Connected-escape focused fixture plan (v1)

Source under test: `bots/variants/willow-v47-connected-escape-work/src/pathing.cpp` (`Pathing::CampEscape::at`) and `src/self_abilities.cpp` (`camp_escape_dash`), plus the candidate-selection loop inside `src/bot.cpp::connected_camp_dash`. Bind the fixture to these exact source excerpts and file hashes; do not reimplement their production predicates in the test. An independent tiny-grid BFS/endpoint enumerator supplies expected answers.

This is a host-side source fixture with declared geometry/action mocks, not a native SDK/executor integration test. It should establish topology, legal endpoint selection, and invalidation-sensitive uncertainty handling, not survival or match strength.

| Case | Production behavior exercised | Independent expected result |
|---|---|---|
| Open straight ray, unique nearest goal | Exact ray labels and `CampEscape::at` | Origin has the ray distance; each ray tile has remaining distance; off-ray point is unknown |
| Ray is blocked by one wall, goal remains reachable around it | Exact distance labels after search, not the blocked ray bound | BFS distance follows the detour; wall and unreachable off-component cells are not labeled |
| A closer off-ray goal exists than the ray goal | Ray candidate must remain non-exact and trigger exact search | Shortest off-ray route wins; it cannot be dismissed by the farther ray witness |
| Origin is already in a goal | Zero-step exact result | `at(origin)==0`; escape-step caller declines zero-step route |
| Exhausted disconnected component versus incomplete/unknown labels | `exact`, `exhausted`, and `at` distinction | Exhausted unreachable returns the sentinel; unknown/unlabelled remains `nullopt` |
| Same origin, then changed wall or goal mask | Cache-key/recompute path in `camp_escape` if feasible in the wrapper | Changed key invalidates prior labels; no stale route survives occupancy/goal change |
| Dash lands on an exact improving route tile | Actual `connected_camp_dash` endpoint-selection block with mocked route labels and hazard values | Only strict step improvement and damage no greater than ordinary walk can win; tie breaks by damage then home steps |
| Landing itself is not labeled, but its one-step walk finish is labeled | Endpoint loop's landing-plus-follow-up candidates | Only the improving adjacent finish is admissible; unknown landing data is never treated as distance |
| No improvement, higher damage, or unknown route endpoint | Candidate loop negative controls | No dash candidate is selected |
| Illegal, wake-causing, or suicidal landing | Exact `camp_escape_dash` body with mocked legality/hazard predicates | Dash helper refuses before execution; a valid landing executes one dash only |

Implementation should use a small extractor that copies the exact function bodies/loop region into a generated C++ fixture, recording source SHA-256 and extraction boundaries. Mocks expose only the fields the extracted code reads. Keep the BFS and endpoint oracle separate from the implementation under test. If extracting the full `camp_escape` cache method requires broad `World`/`Pathing` mocks, stop at `CampEscape::at` plus the source-extracted selection loop and mark cache invalidation as source-reviewed rather than claiming it was executed.
