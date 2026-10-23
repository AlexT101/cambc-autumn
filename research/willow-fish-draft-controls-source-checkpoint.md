# Fish draft controls: source-only checkpoint

Both isolated children copy the current canonical Hyperion source aggregate `337f42a54beb5890109e56b755237d8ea0d07abb240d095778f01e2098ab7b39`. Canonical and all prior variants remain unchanged. Each child contains 29 source files and changes only `src/draft.cpp`; neither has a `.cambc` directory. No build or game was run.

| Child | Source aggregate | Delta from 337f |
| --- | --- | --- |
| `bots/variants/willow-fish-old-draft-control-work` | `b8108db1504bc94d7125bb7af22d85b965cc7e66ac83e82f21218cbec1a9d48f` | 1 insertion / 2 deletions |
| `bots/variants/willow-fish-prefix-draft-work` | `2797a671218912fd2499227996293711e3db012284b3b09a464c79867d23dd36` | 29 insertions / 1 deletion |

The aggregate recipe is `shasum -a 256 src/* | shasum -a 256` from each child directory. Independent file manifests are `willow-fish-old-draft-control-source-manifest.sha256` and `willow-fish-prefix-draft-source-manifest.sha256` in this research directory.

The control restores the existing Alex4c4/fbda native five-pick order: Prism, Vesper, Marcella, Ryth or Vendetta, Heart of Ruin. The original cached density rule chooses Vendetta exactly when `3 * members > 10 * groups`. Four-pick behavior uses that same rule before its existing HoR swap and is unchanged; three-pick and test draft paths are unchanged. This isolates the fourth-slot roster replacement while retaining all current common gameplay logic.

The conditional child starts with the current Willow order. Outside the initial static order construction, native five-pick drafting recomputes completed own picks with `current_draft`. At exactly three completed own picks matching the unchanged first three, it latches one decision from the exact ordered revealed opponent prefix Vesper, Vendetta, HoR. Only that prefix replaces Willow with the existing density-selected Ryth/Vendetta. A missing, differently ordered, incomplete or unavailable prefix retains Willow. A first successful observation after our fourth pick cannot activate the detector. No round-number offset, opponent identity or later pick is inferred.

The latch updates the same order consumed by both `play_draft` and `ensure_picked`. Once four own picks are visible, an actual fourth Willow/Ryth/Vendetta is copied into the fourth slot; thus an actual Willow fallback cannot leave an unpicked substituted champion ahead of HoR on the fifth turn. Existing `pick_first_available` still skips completed own picks and retains its existing error/fallback behavior. No change can guarantee a chosen fifth champion when the engine rejects that pick, but no new duplicate attempt or stale unpicked-Willow fifth is introduced.

Manual source cases checked: native three/four and test draft bypass the new detector; fewer than three completed picks cannot activate; exact matching third prefix substitutes only the fourth slot; reordered/nonmatching/short prefix leaves Willow; repeated calls after the fourth-turn latch do not revise it; ordinary Willow fourth and substituted Ryth/Vendetta fourth both lead to HoR fifth. `params::test_draft` remains false. No item, farm, support, turn-order, safety or map-selection policy changed.

This is a controlled roster experiment and an optional inference from three legally revealed picks, not identification of a complete enemy roster or a demonstrated Fish win. The two children require independent source review before runtime.

Full patches:

- `willow-fish-old-draft-control-from-337f-source.patch`: SHA-256 `7eabd8ed8841c37cf8f8955b15ca635d285fae58054f66d1cd1a0817d06bd3cd`.
- `willow-fish-prefix-draft-from-337f-source.patch`: SHA-256 `a9089065ca9a4b2bf30c6a7296393a64358ab7d49b243a8a4398b61f29f4a23d`.

API/rules boundary: `sdk/cpp/cambc.h` `current_draft` returns an owning completed-pick list on every call, skips DraftUnavailable slots, and propagates other errors. The child catches unavailable/error observations and retains its current order. `cambc-rules.yaml` makes a pick visible after both teams finish that round; our fourth turn can therefore use the first three revealed opponent choices. The code does not query or assume the hidden fourth/fifth picks.
