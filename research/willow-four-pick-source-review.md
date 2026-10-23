# Fixed four-pick Willow source review

2026-10-23. Source-only independent review; no build/runtime. Independently reproduced child aggregate `157f5f79cddb45424ff2c25ce707e705d315c324267c5587a3f7b711f06ab06b`. Read full patch `research/willow-four-pick-source.patch` SHA `2a2d11dc1dbe98504da248dfcbd1a5eceede55c4acdbc3b32f14de66e26366f3` and actual draft selection.

No source blocker. The five-insertion/two-deletion `draft.cpp` delta keeps the parent's native four-pick swap then replaces only slot3 with Willow. Slots0–2 remain Prism/Vesper/Marcella, unused slot4 retains Ryth/Vendetta, five picks still use P/V/M/W/HoR, and three picks still return `draft_preference`. Existing caching and fallback flow remain intact. `params::test_draft` is false; it still takes precedence if a harness changes it, so runtime must verify actual native rosters rather than merely the candidate label.

This is a direct a00fff draft-only child, separate from local Monolith changes. It is suitable for authorized compile/comparison, not a claim of improvement or release qualification. Compare native four-pick cells on both sides, preserve other draft strata, and confirm any gain on an unused generated suite as specified in the fixed-arm study.
