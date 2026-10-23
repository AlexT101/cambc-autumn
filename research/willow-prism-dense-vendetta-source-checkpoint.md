# Dense-pack fifth-pick Vendetta source checkpoint

2026-10-23. The Cambridge Battlecode rules, AGENTS.md and Hyperion TODO were read. This is a separate source-only draft hypothesis, not an active qualifier or release. No builds, engine runs, replay extraction, tests, scripts or tooling changes were performed. Root owns EXPERIMENTS.md and later test scheduling.

Created `bots/variants/willow-prism-dense-vendetta-work` with only a copy of frozen `willow-prism-coordinated-work/src`. There is no `.cambc` directory. No cost children were included.

| Source | Canonical aggregate SHA-256 |
| --- | --- |
| Frozen coordinated parent | `130a17af668a432a8a5582ec0736b1ef13c22e05245bc5742e472f3d02a620a5` |
| Dense Vendetta child | `2dd4084d601fc89138afa7df45372d45260ad8d23313e3e6f56e249f1bb26a69` |

Aggregates use `shasum -a 256 src/* | shasum -a 256` inside each bot directory. Parent was confirmed before copying and again after the edits. Recursive diff finds exactly two changed files:

| Child file | SHA-256 |
| --- | --- |
| `src/draft.cpp` | `216f27819ea0386726fd771952488ffd557543bb9c6e8cc8586a2e50a825cac8` |
| `src/draft_selection.h` | `e42b6b7ef787ffb0d1a9e8cb33b5900b735ff251bb6162bd9a9f7887211f6154` |

`git diff --no-index --check` between the parent and child `src` directories reports no whitespace errors. Gameplay source, native-pick mapping, test-draft code, unusual-size fallback, emergency pick handling, draft-memory writes and all params are byte-identical.

The complete source change is:

```diff
--- parent/src/draft.cpp
+++ child/src/draft.cpp
@@
-            const auto roles = willow_prism_draft_roles(picks);
+            const auto roles = willow_prism_draft_roles(picks, picks == 5 ? native_draft_counts() : DraftCampCounts{});
--- parent/src/draft_selection.h
+++ child/src/draft_selection.h
@@
-inline std::array<DraftRole, 5> willow_prism_draft_roles(int picks) {
+inline std::array<DraftRole, 5> willow_prism_draft_roles(int picks, DraftCampCounts counts) {
@@
+    const bool vendetta = picks == 5 && 3ull * counts.members > 10ull * counts.groups;
     return {DraftRole::prism, DraftRole::vesper_vale, DraftRole::marcella,
-            DraftRole::willow, DraftRole::heart_of_ruin};
+            DraftRole::willow, vendetta ? DraftRole::vendetta : DraftRole::heart_of_ruin};
```

Native three remains Prism/Vesper/HoR, native four remains P/V/Marcella/Willow. Native five keeps those same first four, followed by Vendetta exactly when `3ull * members > 10ull * groups`, otherwise HoR. This exact strict, widened-integer boundary comes from released `bots/Khaos_v29/src/draft_selection.h:28–32`; its interpretation remains provisional. Equality, an empty layout (0/0) and smaller averages retain HoR.

The new five-pick dependency reuses the parent's existing `native_draft_counts()` unchanged, including its one batched SDK camp-layout read, static cache, 90,000-word capacity and oversize check (`draft.cpp:18–27`). It also reuses unchanged `count_draft_camps()` header/member bounds validation (`draft_selection.h:13–23`): require five available header words and enough remaining four-word records before advancing. No new parser or per-member host calls are introduced.

The conditional operator evaluates the camp helper only for five picks; three/four use an empty value without querying camp layout. Selection computes counts inside the existing static chosen-order initializer, before mapping roles to the order array. `play_draft()` calls `draft_order()` before expensive `analyse()` as before. Map summary and order are thus cached once on successful initialization, with no new query on later picks and no dependency on unfinished analysis. Test drafts still return first. Exceptions still reach the existing `ensure_picked()` retries and fallback; no new fuel gate or failure policy was added.

Source review establishes the intended branch and bounded data path; no compilation, parser fixture or runtime result is claimed. Later validation should cover:

- Existing parser with empty layout, valid groups, truncated header, truncated members and oversize count; inspect native fallback on a count failure.
- Exact threshold cases (for example 10 members/3 groups stays HoR; 11/3 chooses Vendetta), zero groups, and three/four ignoring dense counts.
- Actual native roster/ID order on both sides, unchanged first four on five, and unchanged three/four/test-draft/fallback behavior.
- Same frozen gameplay controller against the parent with native drafts/default fuel and both sides; report switched five-pick maps separately, including switch counts, camp-type strata, outcomes, errors and rollovers. Unchanged maps are regression evidence rather than extra evidence of the substitution's strength.
- Repository-required broad qualification and a genuinely untouched suite if the controlled substitution is promising. Keep this arm out of the currently running coordinated qualification, and do not infer improvement from this source checkpoint.
