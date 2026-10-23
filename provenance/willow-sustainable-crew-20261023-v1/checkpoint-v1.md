# Sustainable crew candidate v1

Exclusive variant: `bots/variants/willow-sustainable-crew-work`.

Frozen parent: `bots/variants/willow-comms-cached-endpoints-work`.
Parent and unchanged canonical source hash: `a67dc0a32d4b9d001a8c514dc86aa1d9f4aa9d91bc380f2df2ce59b649ce6d21`.
Candidate source hash: `fc9e0a067eea78f7c8dabc36992300698f2b892a10378c805233f4098a4f7608`.
Hash convention: run `shasum -a 256 src/* | shasum -a 256` inside the bot directory.

Only `src/bot.cpp`, function `farm`, changes:

- Harmless groups keep unconditional passing admission. A damaged ranged crew incumbent is deferred from the movement-spending early basic to ordinary ranking. Nonincumbent ranged passing cannot use Boolean allied occupancy to bypass its solo health budget; melee's free passing behavior stays intact.
- The existing shared arrival, remaining-health, damage-share and camp-loss calculations are factored into `CrewClear`, `crew_clear`, and `crew_hits`, without changing their arithmetic. Same-group owner partner admission remains unchanged.
- Nonclaimed ranked work that still exceeds spare health goes to the existing risky tier. Boolean allied occupancy cannot promote it to the affordable tier. Existing joint-output and spell-kite admission remain available.
- Nearest struggling-ally help must pass that same grouped camp-loss budget, remaining-work check, and the existing banking deadline before it overrides another job. A forecast/certificate already calculated during ordinary shared ranking is retained. If pruning skipped certification, only the final nearest help proposal receives a lazy certificate.

Cost bound: no new map/group traversal, allocations, fuel gates, or tracing. Existing shared calculations are reused; at most one selected group's crew forecast and cached `min_camp_damage` query are added after pruning, plus at most one cached centre-to-altar lookup for its deadline. A previously computed nearest-help crew forecast is retained rather than recalculated.

Invariants: harmless passing DPS, free melee passing, existing retreat/heal/capture priority, real spell kiting, risky fallback, source visibility/arrival evidence, and existing partner claims are preserved. No future healing, unseen position truth, new team/group exceptions, or remote Willow-follow preference is introduced.

Preserved artifacts before any build:

- `parent-src/` and `parent-files.sha256`: complete initial parent source and per-file hashes.
- `candidate-src-v1/` and `candidate-v1-files.sha256`: complete candidate source and per-file hashes.
- `candidate-v1-vs-parent.patch`: complete source diff against frozen parent.

Checks performed: parent hash matched a67; canonical still matches a67; candidate snapshot is byte-identical to the working candidate; variant is ignored; diff whitespace check emitted no diagnostics. No build, runtime, replay, or gameplay tests have run. Static Astra review and root-directed heavy-worker validation remain pending.
