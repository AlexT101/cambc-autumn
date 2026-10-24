# Current-sighting arbitration: independent source review

2026-10-24. Cambridge Battlecode rules read. Source-only review; no build, fixture, game, extraction or runtime claim. Willow-first ladder-manipulation batches are excluded.

**Verdict: v3 is source-ready for the isolated protocol fixtures and whole-team runtime comparison. No remaining concrete source blocker found.** This clears the implementation for testing, not promotion or a claim that Willow survives the motivating Pilgrimage sequence.

## Pins and scope

- Parent: `bots/baselines/astraeus-4d08241`, aggregate `f599a31faa0251321beb97a726918286e266218ceb3e183b8271e41c5c84718c`.
- Reviewed child: `bots/variants/willow-sighting-arbitration-4d08241-work`, independently recomputed aggregate `a439a6c2d1d1d2ef1004f3a463b243d1f48d2daa65eada801d83f55c5c17a2df`.
- Immutable patch: `research/willow-sighting-arbitration-4d08241-source-v3.patch`, independently verified SHA256 `59632c96d7e62f2605ab8b42eebc1e0248990f2de80cb418802bef5ed87dbf37`; source manifest is the sibling `source-v3-manifest.sha256`.
- Only `comms.cpp` and `comms.h` differ from the parent. Source/counter-case receipt: `research/willow-sighting-arbitration-4d08241-source-checkpoint-20261024-v1.md`.

## Corrected blocker and protocol reasoning

The original v1/v2 missed-reader exception preserved an ambiguous current-parity record only when its replacement-used bit was set. A returning reader seeing an aliased **unused** record could instead publish another normal generation. Several returning readers could therefore consume enough generations within a healthy reader's gap to defeat the proposed modulo-four bound. V3 `comms.cpp:245–247` conservatively retains **any** nonempty current-parity record for a nonconsecutive reader. This resolves that blocker; a genuinely old same-parity record may wait one round.

Normal publication advances the two-bit generation and clears the used marker; replacement retains generation and sets used (`70–75`). A replacement then blocks later same-round replacements (`181–182`). With the returning-reader correction, an ordinary consecutive reader's ABBA gap spans at most two normal publications, insufficient to alias modulo four. Long gaps can still alias; unchanged bits are ignored, and changed bits use the existing earliest parity-compatible dating (`138–149`). Replacement requires that conservative date to equal the current round. This is bounded conservative dating, not an absolute timestamp.

The separate previous-*received* payload and round (`214–220`) avoid treating our own preceding publication as an independent repeated incoming fix. The payload excludes generation/parity, so an unchanged enemy/location/quantized-health observation can qualify as redundant even when its normal publication counter advances. Sight, bag, capture, claim and support masks remain disjoint (`38–52`); no unrelated field layout changes.

## Freshness, relevance and cost

Different-enemy replacement requires a repeated incoming payload, a nonlocal incumbent, a currently seen local alternative, and no known winning carrier/tribute/teleport protection (`181–197`). Same-enemy changed direct confirmation updates that identity without displacing it. Known high-value protection is not a promise about unseen changed inventory, bags or channels.

A moved sender needs the existing refresh permission; it observes and recomputes nomination before replacement (`254–262`). One selected `visible_record` read confirms native visibility/life and packs current position/health, handling own attacks even without movement (`264–276`). Stale-round checks precede publication. V3 also requires an ally's position to belong to the current vision board (`169–172`), because `World::observe` may retain an already-current ally record across the sender's move. The final confirmation does not mutate World or introduce a full enemy scan.

The new work consists of small roster/ability loops, at most one conditional existing observation and one selected native champion read. There are no path fields, fight simulations, large allocations or new fuel gates. Actual cost is unmeasured. `strike_reach` is a cheap publication-priority geometry, not an exact legal combat/escape certificate; it does not replace Safety. Approximation can preserve a less useful incumbent or miss a useful replacement, without asserting a forced engagement.

## Focused validation implications

Fixtures must construct the new protocol from logical fields, including generation, marker and previous-received state. Old raw count bits or one new actor among old-protocol teammates are not a valid counterfactual. Cover marker-zero and marker-one returning readers, generation wrap, a healthy ABBA gap, one replacement followed by another writer, unchanged same-enemy payload, protected incumbent, stale moved observation and ally leaving current vision. These should use independent expected transitions, not duplicate implementation predicates.

The trusted Pilgrimage evidence and limitations remain in `research/willow-pilgrimage-trusted-trace-sighting-design-20261024-v1.md`. Marcella's round-765 sender distance six to the visible ready-dash Vesper fits this policy's reach-plus-pursuit geometry, but refreshed visibility, intervening writers and earlier divergence still determine actual publication. The first useful runtime observation is delivery of the newer fix and the receiving Willow's changed belief/guard. Neither survival nor an improvement in match result follows from source eligibility alone. Claims and transient retreat commitment remain outside this patch.
