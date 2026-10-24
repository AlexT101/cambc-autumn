# Generalist Willow support: stable client binding

2026-10-24. Source-only design on frozen f475 (`provenance/willow-astraeus-clock-recovery-20261024-v1/workspace/bots/service-base-f7/src`). No implementation or runtime. A fixed Prism→Stellar/Cassi draft substitution currently changes both the champion and access to dedicated Willow formation/recovery; it is therefore a joint policy test, not a pure kit comparison.

## Small practical experiment

Retain the existing two-endpoint service contract and replace its support-client type binding with one deterministic, immutable roster binding. For the proposed fixed-role menu: choose Prism when drafted; otherwise Stellar; otherwise Cassi; otherwise no dedicated client. Choose Willow as healer. Resolve once from the complete actual allied roster, consistently for all actors, and keep the chosen index through death, invisibility, healing cooldown and recall. Do not promote another body when the chosen client becomes unavailable. This preserves the baseline pairing and supplies one explicit alternate client; it is not a claim those priorities are an optimal general team scheduler.

Expose/reuse a single selector for both `comms.cpp:78–101` and `bot.cpp:4432,4645–4655,4896–4909`, rather than duplicating subtly different type scans. The existing private endpoints implementation already caches stable indices. It can become the common binding interface with no new native reads, persistent wire fields or per-turn all-camp search. Missing client/Willow returns no dedicated pairing and preserves ordinary behavior.

In local_support, use a separate `support_client` identity for the existing recovery branch, not a global replacement of the `prism` concept. In decide, change only the formation entry/client-mate lookup. All Prism-specific gem retention, capture-holder preference, item economics and other tactical logic remain attached to actual Prism. Rename mailbox role0 conceptually client if useful, without changing its bit layout or parity: exactly one client requests and one Willow offers. Existing request/available getters keep their two-role semantics.

## Why the current recovery arithmetic can be reused

`recovered_for_work` (bot.cpp:4449–4458) uses actual health, Safety damage, current farm group, actual floored output and camp-hit factor. It has no carried-gem-specific subsidy. The local recovery quote (4708–4733) uses actual available heal gain, maxHP, home distance, recall duration, detour and teammate activation timing. The saved-time heuristic is imperfect but equally explicit for another ranged body; do not introduce a new conversion coefficient to make Stellar qualify.

Retain current visibility/native-alive/readiness, safe-station and heal-worth checks; protected capture/contest/banking/shop (`support_work`,4638); maximum recovery/formation duration, no-progress closure and reentry handling; no forced pursuit of a hidden client; and opportunity to heal a more useful visible ally. `heal_views` enumerates all allies and local_support's target tie only favors the bound client after equal gain/fraction. The mailbox is evidence of current safe service availability, not a promise that Willow must spend its cast on the client. Willow's independent heal movement and generic tail healing continue.

Do not accidentally broaden `mate_eligible` suppression to every teammate. It is presently about this one paired mate. Local_support sets support_owned and may clear Willow's claim/crew, so a changed binding can redirect useful farming; this is the intended experimental mechanism to measure, not free support.

## Cassi and Issac require an explicit limited choice

Cassi is the designated client for this first alternate binding, while Issac retains ordinary work/retreat and remains an ordinary heal target. Both bodies cannot publish the one requester slot: a second same-role writer would misattribute requests and a health-based switch would leave stale mailbox/recovery memory with no encoded endpoint identity. A two-body dynamic client scheduler would require identity/epoch/reset design and is outside this small arm.

Their linked death is still a material limitation: keeping Cassi healthy does not certify Issac safe, and a local Cassi retreat must not claim it coordinates Issac. If Issac dies the engine kills Cassi too; existing endpoint alive/respawn reset then clears the pair. The Cassi-bound experiment is a concrete service policy, not proof that C&I received all support needed for a kit-only comparison. A later Issac-bound control can test that choice without a scheduler rewrite if evidence warrants it.

## Independent approach-spell confound

`abilities.cpp:604` also limits approach casting to Prism. Do not silently grant that policy to Stellar/Cassi in this support arm. Record it as another intentional baseline asymmetry. The separate mixed-camp qualifier is now supported by the trusted r6 value400 rejection trace; r7 retains a distinct exposure refusal. A later capability-based ground-approach experiment can be paired with Stellar, but should have its own source delta because casts consume that turn's walk and Cassi has no ground AoE. This support-binding proposal alone does not resolve the action-realization difference.

## Minimal useful controls

1. Original P/V/M/W/HoR versus generic-binding P/V/M/W/HoR: behavior/pair must remain the same; compare any actual divergence before attributing kit results (refactor cost can change existing cutoffs).
2. Fixed S/V/M/W/HoR with original service disabled by absence of Prism versus the same draft with Stellar binding. This directly measures regained service, not merely changed roster.
3. Fixed C&I/V/M/W/HoR with no dedicated pair versus Cassi binding; inspect both bodies' deaths/bags, not only Cassi healing.

Use a few already-planned five-pick economy contrasts and both physical sides, then test relevant combinations with the selected routing arm. No requirement that each single win first. Missing Willow, client death/respawn, invisible/client-channel state, protected banking/capture, a more urgent nonclient heal, and Issac's inability to publish a client request are small meaningful production-contract checks. Measure offered/requested/actual useful healing, patient work resumed versus delay, Willow's lost/continued farm work and payout, ordinary capture conversion and cost. Do not credit raw healing as farm DPS or infer improved coordination from total heals alone. This is sufficient for an isolated prototype; no unavailable private ladder memory is required.
