# Fish draft controls: independent actual-source review

2026-10-23. **No source blocker found in either child.** Source review only; no build, game, exporter or gameplay edit. Runtime authorization remains with root. The conditional is an observable-prefix experiment, not detection of Fish or its complete roster.

Recomputed source aggregates and compared all source files against canonical337f42a54beb5890109e56b755237d8ea0d07abb240d095778f01e2098ab7b39. Each child changes only `draft.cpp`; the actual diffs match the pinned patches.

| Child | Aggregate | Patch SHA-256 |
|---|---|---|
| `willow-fish-old-draft-control-work` | `b8108db1504bc94d7125bb7af22d85b965cc7e66ac83e82f21218cbec1a9d48f` | `7eabd8ed8841c37cf8f8955b15ca635d285fae58054f66d1cd1a0817d06bd3cd` |
| `willow-fish-prefix-draft-work` | `2797a671218912fd2499227996293711e3db012284b3b09a464c79867d23dd36` | `a9089065ca9a4b2bf30c6a7296393a64358ab7d49b243a8a4398b61f29f4a23d` |

Checkpoint SHA: `56d1d91d3875b413558c58c56a49c9773d4bf12f07052d1f53eb8bef286f490b`.

The control's1+/2- substitution restores `teacher_draft_roles(native_draft_counts())` for native five-pick drafting: P/V/M, density-selected Ryth or Vendetta, HoR. Four-pick already used that expression and retains its swap; three-pick and test-draft paths are unchanged. All gameplay source is identical to337f. The additional five-pick count read is the existing bounded public-map reader, cached during initial preference construction. This is suitable for the authorized comparison against unchanged Willow and exact4c4.

The conditional's29+/1- change keeps the default public order cache but evaluates completed picks outside its initializer (`draft.cpp:260–286`). Only native five-pick reaches it; `test_draft` remains false and its earlier return is unchanged. Exactly three completed allied picks must match P/V/M. Exactly three completed enemy picks must equal ordered Vesper/Vendetta/HoR. It then changes only slot3 using the existing density rule. It neither waits for nor assumes Varg/Cassi, and it has no map-area or opponent-identity predicate.

The SDK `current_draft` (`sdk/cpp/cambc.h:5140`) returns an owning vector, skips unavailable16, and throws other errors. No vector reference escapes the call. An incomplete/nonmatching enemy vector keeps Willow and latches the decision. A thrown enemy/count read also keeps Willow because `decided` is set before those reads and slot3 is assigned only after their success. A failed allied read can be retried on the next existing call; an observation first succeeding with four completed picks cannot activate the counterdraft. The broad catch encloses only optional detection/count work, not draft-plan writes or submission, and retains the current order.

Once four allied picks are successfully read, actual fourth Willow/Ryth/Vendetta replaces slot3 before the preference scan. Thus ordinary and substituted fourth picks both leave HoR as the next unpicked preferred champion; an actual Willow fallback does not leave an unpicked teacher ahead of HoR. These are normal successful-read guarantees, not promises that the intended roster survives arbitrary engine pick/query failures. Existing `pick_first_available`, `play_draft`, `ensure_picked`, and write-before-pick ordering are unchanged.

Manual source cases covered: three/four/test bypass; own count0–2; exact match at3; reordered/short/mismatched enemy prefix; repeated calls after latch; thrown optional reads; first observation after fourth; actual Willow and teacher fourth. The dynamic path adds owning draft scans until commitment and one late cached map-count read on activation, so actual roster and native rollover/error audit remain necessary in runtime. No gameplay state, mailbox, support policy, fuel gate, turn-order policy or future-pick knowledge was added.
