# Band routing masks: independent source review

2026-10-24 UTC, Astra. **PASS for source-only diagnostic scope; runtime equivalence remains unqualified.** Reviewed the actual three-file diff and surrounding parent/candidate control flow, SDK storage/layout access, preceding trace review and frozen checkpoint. No build, replay, extraction or new tooling was run.

Verified source aggregates using `shasum -a 256 src/* | shasum -a 256` inside each bot:

| Source | SHA-256 |
|---|---|
| Immediate trace parent | `46ab555f9637c1d5d86bcb7da1fa55bbf541515b023966d1e45ee8d2dc44e414` |
| Mask child | `28e64f631dfcb873338c63bebf52eb2d25bcad9da7c7c235c98b02ff06598852` |

Frozen parent and candidate snapshots under `provenance/willow-band-hor-routing-masks-20261023-v1/` match their live source trees byte for byte. Only `bot.cpp`, `pathing.cpp` and `pathing.h` change, with 114 insertions and 12 deletions. No blocking gameplay-policy or duplicated-query issue found.

All new output bodies execute within `debug_block` and are gated by cached physical team A, actor index2 and rounds20–22. The mask helper reads raw board storage and immutable cached layout. `sdk/cpp/imports.h:575` returns metadata captured at initialization; it adds no native query. Chunk iteration excludes storage row padding, preserves row/column order and prints the complete 64-bit word. This permits offline reconstruction without calling board test/export APIs.

Native occupancy outputs are logged at their existing production before scratch reuse. Route walls are logged after the original freeing/avoid/guard transformations; the guard log reads `guard_`, never calls `guard()` to obtain diagnostic data. The held live-camp mask is gated by its initialized-version sentinel and is not refreshed for output. Approach records use existing ready/build branches, cache slots and boards. They do not reconstruct unretained old walls or force an approach computation. Farm adjacent-goal output occurs only when the original short-circuited adjacent argument is evaluated.

The `kept_steps` split retains original distance/layer/cap checks before goal equality and preserves later changed-wall comparisons and field reads. Existing branch values are printed without repeating those tests. Making this helper a member adds no object field. Camp-member records read held beliefs with their dates; they do not make those beliefs current native truth. No added gameplay import, Safety computation, guard materialization, cache mutation or fuel gate was found.

This is not a fuel-neutrality certification. Debug guard entry, helper/argument code and compilation changes can alter execution even outside the output window. Cached round labels can lag a resumed native segment. Qualify original → recorder → mask tracer through round22 using the existing phase-aware action/state/import/fuel workflow before causal interpretation. Tracer-to-recorder agreement alone is insufficient. Keep absence of output distinct from absence of a guard, cache or threat. Full qualification requirements remain in `research/willow-band-hor-routing-trace-source-review.md`.
