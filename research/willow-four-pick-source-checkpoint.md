# Fixed native four-pick Willow source arm

2026-10-23. Root authorized the isolated fixed arm from `willow-four-pick-fixed-arm-study.md`. New source-only child: `bots/variants/willow-four-pick-work/src`, copied directly from frozen a00fff, **not** the Monolith child. Only `draft.cpp` changes,5 insertions/2 deletions. No gameplay, itemization, map selector, opponent-pick heuristic, Monolith policy, scripts, builds, runtime, canonical/release or EXPERIMENTS changes.

| Artifact | SHA-256 |
| --- | --- |
| Frozen a00fff parent aggregate | `a00fff454c1e48520968c9ba2d4c1ecdae0212ce019724dc06a6e959ddc3412e` |
| **Child source aggregate** | **`157f5f79cddb45424ff2c25ce707e705d315c324267c5587a3f7b711f06ab06b`** |
| Changed `src/draft.cpp` | `bc31a6ab512fb25d40205cba3ed182552ce4e7da94b81b8ac20c770cd7a6745a` |
| Full delta `research/willow-four-pick-source.patch` | `2a2d11dc1dbe98504da248dfcbd1a5eceede55c4acdbc3b32f14de66e26366f3` |
| Independent29-file `research/willow-four-pick-source-manifest.sha256` | `157f5f79cddb45424ff2c25ce707e705d315c324267c5587a3f7b711f06ab06b` |

Aggregate convention is `shasum -a 256 src/* | shasum -a 256` from the bot directory; manifest contains the exact first command's output. Parent unchanged. Child contains only `src`, no `.cambc`.

In `draft_order`256, the native four-pick branch retains the parent's swap/fallback ordering, then replaces only fourth pick HoR with Willow. Result: **Prism / Vesper / Marcella / Willow**. First three picks remain unchanged. The unused fifth fallback remains the parent's Ryth/Vendetta choice. The five-pick branch remains P/V/M/W/HoR; three-pick/default preferences and test compositions are untouched. `params::test_draft` remains false, preserving actual native-draft evaluation; normal test-draft composition runs would not test this arm.

Read the actual sole-hunk delta; whitespace check emits no diagnostics. All28 other source files are byte-identical to a00fff, including full existing support/transit/ready-heal/optional97 behavior and item model. No compiler or game was invoked. This is a prospective draft-plus-existing-service experiment, not a claimed gain or qualification. Root/Astra source review precedes Luna's native four-pick screens/broad/fresh panels and actual roster checks, as described in the study. The Monolith source is independently held for review and is not part of this candidate.
