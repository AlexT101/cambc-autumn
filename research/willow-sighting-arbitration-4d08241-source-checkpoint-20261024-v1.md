# Current-sighting arbitration source checkpoint

2026-10-24. Cambridge Battlecode rules and Astra's full trusted Pilgrimage design read. Source-only isolated child; no build, runtime, scripts, extraction, SDK/tool edits, canonical changes or release.

Parent `bots/baselines/astraeus-4d08241`, aggregate `f599a31faa0251321beb97a726918286e266218ceb3e183b8271e41c5c84718c`; all29 parent source checksums verified unchanged.
Child `bots/variants/willow-sighting-arbitration-4d08241-work`.
Frozen v3 manifest aggregate `a439a6c2d1d1d2ef1004f3a463b243d1f48d2daa65eada801d83f55c5c17a2df`.
Delta `research/willow-sighting-arbitration-4d08241-source-v3.patch`, SHA256 `59632c96d7e62f2605ab8b42eebc1e0248990f2de80cb418802bef5ed87dbf37`.
V1/v2 patches/manifests preserved. Only comms.cpp and its send documentation in comms.h differ. No whitespace diagnostics from no-index diff check.

## Publication policy

A current occupied report can be replaced once. Different-enemy replacement requires the incoming enemy/position/quantized-health payload to equal the previous received payload from the immediately preceding round, current conservative dating, a nonlocal incumbent and a current directly observed local alternative. The previous received payload is retained separately from our own publications. A changed incoming location/health is protected from different-enemy replacement. Local means ready strike reach plus existing pursuit_steps against the sender or a current visible ally; binary ties preserve normal order. Ready dash plus basic, ready harmful reach, and basic splash use fixed kit facts, not a fight simulation or a path search. Current visible allies must also be in the current vision board: World.observe intentionally does not reread already-current allies, so its old visible flag alone is insufficient after movement.

A directly observed current same-enemy position/health change may instead consume the one replacement. Identical payload does not. This preserves the identity of a protected carrier/channel while updating its direct fix. Known winning carrier, active tribute or teleport beliefs protect an incumbent from different-enemy replacement. An invalid index/position, dead incumbent or absent strict relevance improvement retains the report. Current stats of an unseen incumbent are not required: its packet position, public fixed kit, current cooldown bounds and known channel/bag suffice for those checks. Unknown unseen inventory/changed bags or unobserved channels are not invented or promised absent; the guarantee is protection of known high-value information.

The alternative must be alive, visible, Source::seen and have current pos_round/stats_round. A moved sender only observes for a preliminary qualified replacement if main's existing refresh permission is true, then reruns nomination. Without permission it retains the occupied message. No extra observation merely to keep a report. One selected visible_record read before posted-state mutations confirms live native visibility and packs fresh position/health in a local payload, then checks the same geometry. This handles our own attacks changing health/death without moving; it does not mutate World. Dead/unavailable candidates, changed geometry that loses qualification, or an unchanged same-enemy native payload retain the incumbent.

Normal publication still rotates after the current report's index and advances its generation, with original visibility selection. Claims, bags, captures, support, stale-turn checks and receiver threat logic retain their masks/behavior. No identity, map, round or forced activation rule exists. Debug-only CSIGHT records actual replacements.

## Counter and dating cases: source reasoning, not executed fixtures

Bits59–60 hold normal generation modulo4; bit61 is replacement-used. The existing parity bit and payload widths are unchanged. Normal publication advances generation and clears used; replacement preserves generation and sets used. All later same-round writers retain the used report. Existing changes() compares the entire sighting mask.

| Case | Transition / result |
|---|---|
|Normal unchanged payload|Generation0→1 with used0. Reader sees changed bits even if parity matches.|
|Generation wrap|Normal3→0 still differs from previous normal3.|
|One replacement|Generation g/used0→g/used1; differing payload and marker are visible. Later writers cannot replace it.|
|Healthy ABBA gap|At most two normal publications; generation advances at most2 modulo4 and cannot alias. A replacement does not spend a generation.|
|Four missed normal publications, identical final payload/parity/marker|Bits may alias; changes() ignores them rather than inventing freshness.|
|Long gap with changed bits|Unchanged dated() chooses the earliest parity-compatible round after the last read/write; replacement requires that date to equal the current round.|
|Long-gap alias of current-parity record|Even with changes()==0, a nonconsecutive reader treats any nonempty current-parity record as occupied. This prevents extra normal generations from multiple returning readers and preserves the healthy-reader alias bound.|
|Healthy unchanged old marker|A consecutive reader has no healthy generation alias, so normal publication can resume under the original occupied-slot rule.|
|No selected alternative / tie / protected / no refresh|All sighting bits stay unchanged; other fields may still publish normally.|

The ambiguous-record hold is the only additional normal-publication suppression. It is restricted to a missed-turn reader with an existing nonempty current-parity record, regardless of the used marker. A later parity change or fresh evidence resolves it. A genuinely old same-parity record may wait one round; this prevents several returning readers from creating extra normal generations and undermining the healthy-reader alias bound.

## Cost and witness limits

Added state is one payload, two dates and two flags. There are no fields/bitboards/large caches. Each nomination scans at most the enemy count, two ability slots and currently visible allies; current vision-board tests occur only after geometry qualifies. A moved preliminary nominee may cause exactly one observation under the already-computed permission, followed by one repeat nomination. A final nominee adds at most one native champion read. No native all-enemy scan, Safety simulation, map search or fuel gate is introduced. Actual fuel remains for Luna.

Astra verified existing trusted765 facts: Marcella starts(19,56), sees Vesper at(25,56) with ready rounds770/765, then farm-moves to(19,57). Sender distance6 is within ready dash/basic reach5+pursuit3=8. The old HoR packet duplicates the received764 payload. These are motivating source eligibility facts, not a claim this globally active policy reproduces the same prefix: earlier decisions can diverge, and refreshed visibility/intervening publication still need the runtime check. No round-specific branch forces that window. Claims are outside this patch; Astra's later trusted follow-up found767 resumed group12, so no claim change was added.

V2 added the current vision-board check for ally relevance. Astra identified a concrete v1/v2 protocol blocker: preserving only an ambiguous used marker left marker0 returning readers free to create extra normal generations. V3 retains any nonempty current-parity record for a nonconsecutive reader. Astra independently verified the v3 source and patch pins and found no remaining concrete blocker; verdict: `research/willow-sighting-arbitration-4d08241-source-review-20261024-v3.md`. Runtime fixtures must construct the new generation/used protocol logically; old trace counter bits and mixed old-protocol teammates are not compatible proof inputs.
