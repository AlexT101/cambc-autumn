# Sustainable crew fallback consistency experiment v1

Exclusive ignored variant: `bots/variants/willow-sustainable-crew-fallback-work`.
Parent: frozen `bots/variants/willow-sustainable-crew-work`, aggregate `69010aea272d211599594c5a9f12b71f54b52ea83ec9f39cbe010541291a7d70`.
Candidate aggregate: `fd99d1072c9c57b7d536e4c2602da56cffcfca3c41ac758aff10a552a7583f2f`.
Canonical remains unchanged at `a67dc0a32d4b9d001a8c514dc86aa1d9f4aa9d91bc380f2df2ce59b649ce6d21`.
Aggregate convention: inside each bot, `shasum -a 256 src/* | shasum -a 256`.

Only `farm` in `src/bot.cpp` changes from6901:

- Keep the original farm health read as a scalar. The already-computed ordinary claimed-branch loss that fails the recall reserve can enter one best risky-shared record only for a live, viable, positive-value, timely group, positive spare health, and loss strictly below current health divided by existing camp risk.
- Select affordable own/shared work and certified help first. Only with none available compare the existing risky-own rate to risky-shared; strict greater-than admits shared, so own wins ties. Shared fallback commits `farm_group == claim` and `crew == true`.
- Snapshot previous group/claim/crew at the original fallback-bookkeeping location after early work. Only explicit terminal structural, reachability, wait, remaining-work, deadline, or health rejection with no admissible tier sets `previous_rejected`. Existing risky-own and new bounded risky-shared remain admitted. Competitive value pruning, a partial scan, and loop counter alone never establish rejection.
- With no winner, clear all three identity fields only after positive previous rejection; otherwise retain the previous tuple. A zero-iteration pass still follows its incumbent as before. Cached-route fallback refuses a positively rejected previous target, and a genuine previous-route reuse restores the full previous claim/crew identity.

No new SDK queries, evaluators, map/group scans, allocations, fuel gates, or tracing are introduced by this delta. The existing6901 lazy certificate and its possible cold helper work remain. This is a consistency and recall-reserve experiment under the existing proportional loss model, not a proof of physical survival or an established cause of a saved loss.

Preserved before any build:

- `parent-6901-src/` and `parent-6901-files.sha256`.
- `candidate-src-v1/` and `candidate-v1-files.sha256`.
- `candidate-v1-vs-6901.patch`: exact parent delta.
- `candidate-v1-vs-a67.patch`: cumulative canonical comparison.

Static checks: source snapshot matches candidate; parent and canonical aggregates reverified; ignored destination confirmed; diff whitespace check emitted no diagnostics. Astra reviewed the full actual delta and returned source-only PASS with no blocker. No build/runtime performed; model behavior and fuel remain runtime questions.
