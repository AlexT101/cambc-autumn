# Bounded stationary crew-work experiment

Exclusive ignored variant: `bots/variants/willow-stationary-crew-work`, cloned src-only from frozen fd99. No latest-upstream or item arms are stacked. Read and implement `research/willow-sustainable-stationary-work-refinement.md` (design SHA `caaa99add465f9f011886b0a0ba7388a3b999f6d62b751f0d58773a529160452`). No canonical edits, build, runtime, script implementation, cleanup or directory moves.

Standard source aggregate (`shasum -a 256 src/* | shasum -a 256` inside each bot):

- Parent: `fd99d1072c9c57b7d536e4c2602da56cffcfca3c41ac758aff10a552a7583f2f`.
- Candidate v1: `10310292c47086367d0d5f30be7d500e30bf7123f87684298b28d6045a25076f`.
- Canonical reverified unchanged: `a67dc0a32d4b9d001a8c514dc86aa1d9f4aa9d91bc380f2df2ce59b649ce6d21`.

Only `src/bot.cpp` changes, in the attack-target enumerator and farm's early attack batch. The enumerator can provide its already-read current position to a two-argument predicate, using C++20 `requires`; existing one-argument predicates retain their original invocation. Farm's passing predicate can report that its original affordability check failed, without changing its own results. The early batch alone may then add the new stationary tier. Later dash/walk passing, full ranking, shared/risky choice, routing and identity handling remain parent code.

The tier requires ordinary ranged farm, no banking bag/active banking/siege, original `taken(g)` exclusion for nonincumbents, alive/current-round/fully-awake cached group work damaged this or last round, a positive fresh visible in-range member, and a visible alive nonself ally with no channel and no different explicit claim in real basic reach of a positive fresh visible member. Acted allies are not excluded. Begun work/awake state remains a belief, not a new native certificate.

One lazy current-tile traversal sums every static damaging camp member in reach across `groups_near`, regardless of cached liveness, sleep, cleared or respawning status. It applies only the already-read owned mitigation. Admission requires current health minus this charge to remain at or above the existing35% recall reserve, with no modeled enemy hit or stun. No camp-risk division, ally protection, proposed kill/stun/reset, future shield or healing discount enters the charge.

The added work is bounded to16 distinct candidate-group eligibility entries per early attack batch; repeated group predicates reuse entries, and overflow declines only the extra tier. There is at most one local static-member traversal and one existing `Safety::threats_at` evaluation. Threat evaluation is skipped if the raw phase already fails the reserve. No field/path query or new native import kind is introduced. Safety may materialize its existing cold caches; fuel is not assumed free. A conditional `world.throw_if_stale` after enumeration and before any target action covers batches that evaluated the extra tier, using the existing round import. It is not a fuel gate.

The memo and exposure are batch-local, so the early tile's safety result cannot be reused after a later dash or walk. Harmless admission, target score/order, native attack/cast/reset checks, existing successful claim/crew writes, and all higher-priority decisions remain. Success authorizes the existing current attack batch; it is not a full-clear survival proof or a guarantee of an escape route through a multi-tile camp band.

Pre-build source preservation:

- `parent-fd99-src/` and `parent-fd99-files.sha256`.
- `candidate-src-v1/` and `candidate-v1-files.sha256`, verified byte-identical to working candidate.
- `candidate-v1-vs-fd99.patch`, SHA `3cb057490b098d85b0265a0aab12e9701816adf347212b88855f717c023f35f3`.
- `candidate-v1-vs-a67.patch`, SHA `65cd946ce7eab31ccd548b7d279c45ee0b861853137a9dff1c89bb1f1dfe24d1`.

Parent/canonical hashes and ignored destination checked; diff whitespace check emitted no diagnostics. Astra reviewed actual10310292 source and returned PASS without a correction. The existing solo min_camp_damage still runs before the new tier, so no fuel saving is claimed. Static dead/respawning charges can miss good work, and visible worker reach is an economic belief rather than a committed future action. No activation, economic gain, fuel improvement or survival outcome is claimed without runtime qualification.
