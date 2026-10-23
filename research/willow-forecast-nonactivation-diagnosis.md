# Willow forecast formation: nonactivation diagnosis

2026-10-23. Bounded read-only source/available-artifact review. No gameplay edits, tracing, scripts, extraction, builds or runtime. These are hypotheses to distinguish with gate counts, not permission to relax safety or change turn order.

## Source and observation binding

- Latest source under review: `bots/variants/willow-fbda803-forecast-work/src`, aggregate **`647a10e00c51290b2ba4a38b4cdc93a5f6c258c331d40cb3b1a23610ddbfeb1d`**, integrated parent `337f42a54beb5890109e56b755237d8ea0d07abb240d095778f01e2098ab7b39`. Its exact94+/1- policy delta matches the old arm; latest integration/experimental-rebase checkpoints pin composition. No latest-base activation result is asserted here.
- Completed observation: old `willow-forecast-formation-work`, aggregate **`0e989629893b451a0c164cac5757cf8b41eb1b2be36ef2766d1afc26a8bdfb59`**, against frozen a00fff. `replays/willow-forecast-formation-vs-a00fff/diagnostic-summary.md` records52 Debug/default-fuel published five-pick games and zero raw/parsed `WFF` rows in104 logs. Largest log717,548 bytes is below the1,048,576 limit. Final scan SHA after the explicit truncation check is `01126c912c3dbec08d026a98fbce3331a93f4ed6af8c8688edab6522583ee3bf`. `WFF` only reports changed moves; absence does not identify which admission gate failed. No Release qualification followed.

## Structural overlap to measure

No logical impossibility was found. The approved geometry remains realizable, but several intersections make normal activation narrow:

1. **Already acted versus useful injury.** In quiet idle priority, an empty/full Willow has7, Marcella11, Vesper9 and Prism8 (`combat_priority.h::role`, `idle_priority.h`). At10% missing health the worker loses8 priority points; higher acts first. Carrying gems further depresses idle priority. Thus many injured M/V/P workers act after a healthy empty-bag Willow and fail the completed-turn gate, while full workers act first but one projected hit often fails heal worth. HoR has idle12 but is shield-capable and excluded. Priorities apply next round, and late high maximum HP can leave a useful absolute deficit below10%, so this is a likely bottleneck rather than a universal exclusion.
2. **It needs another worker.** Parent `local_support` already minimizes range/LOS gap to Prism across the same strict-safe stations. A forecast to Prism itself normally cannot improve that move: if another station can reach Prism, the parent can too, and the parent upper bound preserves equal value. Activation therefore needs nearby M/V or another shield-free worker while Prism independently induces the original zero-gain move. Any current worthy heal target in the original enumeration vetoes the new helper, even when its LOS is unavailable.
3. **Narrow injury band and conservative output veto.** For normal HP fraction at least0.5, heal360 requires216 restored. With projected injury0.63D and no current worthy target, eligible missing HP is `[216−0.63D,216)`: single Wolf20 gives `[203.4,216)`, Elk60 `[178.2,216)`, Golem120 `[140.4,216)`. Early M1200/V700 in those bands are beyond the10% idle-priority bucket. Discrete actual camp damage, mitigation, four-turn expiry and the need for a fresh damaged/awake claimed group narrow it further. The49-cell static output veto also rejects harmless, dead or respawning camp tiles; on a strict-safe origin these conservative cases may dominate its additional rejection. Measure them separately from actual live output before considering a narrower veto.

Changing combat/idle priority just to satisfy the new forecast gate is unjustified. If actual counters show completed-turn is decisive, dropping that requirement could be a separate **value-only** experiment: current visible claim/position would be less likely to persist through the recipient's imminent turn. Even an already-acted ally could move next round, so it was never a healing guarantee. Strict Willow safety, no future-health credit, the already-selected zero-gain move, current-output protection, actual native healing and bounded expiry must remain independent. Measure wasted movement/recipient departure and actual later service rather than treating extra markers as benefit. No such change is implemented.

## Minimal later counter contract

Luna owns instrumentation. Use bounded Debug histograms and values already computed at existing seams; do not call skipped SDK queries, geometry, safety or ranking solely for logging. Counts need denominators and actual passed stages, not just zero final markers:

1. Willow `local_support` funnel: no valid parent; parent stay; positive gain/current target; not ready/leave; expired/active clear; eligible zero-gain move.
2. Existing visible-record worker enumeration: unacted; shield-capable; channel/spawn/other; accepted scalar worker. Retain type/current HP-fraction buckets and actual completed-turn state to test the priority overlap. Count before the current-worth filter so below-threshold recipients remain represented.
3. Helper rejection: visible-enemy or static-camp output veto; no valid fresh claimed awake/damaged group; no unique positive damage or HP≤raw damage; projected-worth failure. Where a static camp cell already supplies its group ID, its existing belief/type may distinguish harmless/dead/respawning over-veto without any new read.
4. Finalist outcome: gain≤parent upper bound; current/parent access; no legal strict-safe alternate; changed move. Preserve one-finalist/no-retry semantics while counting.

Histograms should be globally bounded, with early/late buckets sufficient to compare the HP/priority regimes. Do not add per-turn unbounded logs or production fuel gates.

## First published nomination

Use the old-panel Elk Arena pair of **windows**, initially in `replays/willow-forecast-formation-vs-a00fff/batch-run-01-debug-five-pick/041-01elk-arena-12.repl26a`, physical A Willow actor3:

- **r17–23:** existing stdout records `D19/20/21 3 h`, followed by ordinary farm `F22/23`. This catches formation-to-farm near dense multiworker camps.
- **r212–222:** repeated `h` entries at212/213/215/216/218/220/222 provide a later comparison where increased worker maximum HP may weaken the early priority conflict.

These `h` entries do not establish ready, zero-gain parent moves; counters must establish those conditions before any own-view export or policy conclusion. A latest647a replay on the same published map may follow a different trajectory. Start with bounded early/late counters, wait for the actual rejection distribution, and only then choose a precise latest-base own-view witness. No additional map search or extraction was performed.
