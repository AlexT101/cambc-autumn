# Boss route altar-field reuse: source checkpoint v1

This is a source-only child of the frozen, source-reviewed approach candidate. It changes only altar-field storage lifetime; it does not change route selection, admission, pricing, pathing, damage/health gates, cached-home fields, or runtime inputs.

- Frozen parent candidate: `bots/variants/willow-phased-boss-approach-4d08241-work`; aggregate (`shasum -a 256 src/* | shasum -a 256`): `fbbdabd00d4726d36feb4c6bb87475d2e4fc9a1b118bcf59a4a577da9c3a275f`.
- Child: `bots/variants/willow-phased-boss-route-cache-4d08241-work`; same aggregate recipe: `5c47f2fce2f6097e5efd16f4b2fa53d6468276aa00cfc168faa877ad8224f149`.
- Delta: [`willow-phased-boss-route-cache-4d08241-source-v1.patch`](willow-phased-boss-route-cache-4d08241-source-v1.patch), SHA-256 `6c50c4f778d97b9e559a1e40f522f4401edcd03366f7ca6236366990f9bb7f8e`.
- Only changed source file: `src/phased_boss.inc`; unchanged files are inherited from the frozen child tree.

The logical switch gate and `cold_round` rejection still execute before any field reuse. A switch still clears the active home field and now clears an explicit `altar_active` flag while retaining the physical altar field and its exact existing altar-open-set key. If transit, spawn-distance, or another earlier check fails, the flag stays false, so stale physical storage cannot satisfy the returning-job precheck. Once route preparation reaches the altar stage, it reuses the field only when the original key matches; otherwise it rebuilds with the original goal set and key calculation. The active flag becomes true at the same point the former pointer became non-null (before the existing bank-distance result check), preserving the prior return-path precondition even when the bank check then fails.

This is a bounded one-entry altar cache. Alternating altar signatures still rebuild and may thrash. Home fields are unchanged and still rebuild on logical switches. No build, fixture, replay, or performance measurement has been run for this child; the repeated field construction remains a hypothesis pending review and measurement. The frozen `fbbdabd...` source was not edited.
