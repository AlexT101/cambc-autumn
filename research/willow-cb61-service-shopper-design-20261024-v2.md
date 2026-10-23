# cb61 Willow: one service-aware shopper experiment

2026-10-24 UTC. Source-only implementation proposal on aggregate `369742e3f54259c675c0d4b508a02c0c4517eef6e1cb3ef6f42fa776194180ea`. Cambridge Battlecode rules read. This supersedes the instrumentation-only recommendation in `willow-cb61-service-quote-proposal-20261024-v1.md`; retain that file's evidence reconciliation. No code, build, run, or new extraction performed.

**Implement one isolated shopper arm that adds observed marginal ally-recovery value to existing own-upkeep savings, then compare it experimentally.** A positive cb61 ranking witness is a runtime activation check, not a prerequisite to implementation. The conversion is the existing fractional-recall model extended to allies, with explicit limits—not healing HP treated as farm damage.

## Why this is the next item experiment

Cb61 fixes heal visibility/readiness and some post-move service decisions. More accessible healing may make Focus useful more often, but the amount depends on actual recipient deficits and scheduling. The shopper is unchanged: Willow's non-damaging heal contributes nothing to `main_stat` or `raw_output`, so Strength wins through personal farming; Health already reduces estimated own recovery cost. Canonical cb61 has **no fixed first-Focus override**.

Earlier selected Focus cases did not uniformly increase healing or reduce recalls. The completed Focus-plus-make-way compound finished518–586 against its parent's524–580 on the same1104-game panel, so there is no demonstrated overall gain to port blindly. Health+Focus's002-B win combined lower Willow income with higher team capital and useful service, while002-A regressed. These observations motivate valuing service and lost farming together, not a universal Focus, Health, or income-recipient rule.

## Utility and comparison

For an exact proposed `Build b`, use:

`saved(b) = upkeep_cost(now) − upkeep_cost(b) + service(b) − service(now)`

`service(b) = sum over retained successful-cast snapshots [effectiveHP(selected_target(b), cap(b)) × recipientTripWeight] / observedAliveTurns`

`recipientTripWeight = (recipientRecallTurns + cachedSpawnReturnSteps) / (recipientMaxHP × (1 − recall_health_fraction))`

This produces estimated recipient recovery rounds per Willow alive turn, the same units as `upkeep_cost`'s own clearing/recovery rounds per turn. It assumes an ally round and Willow round have equal value and that fractional healing reduces recall/return expense. Neither assumption proves a recall was avoided or later work completed. Use the known recipient's fast-recall setting, recorded maxHP and an already-ready spawn field. If the needed route/stat data are unavailable, exclude that snapshot consistently from **all** candidate service evaluations and report missing coverage; do not initialize a field for this estimate. Keep excluded time in the exposure denominator.

Add **fresh Bruiser Focus** to the existing candidate comparison only after Treasure is owned. Evaluate all existing candidates with the same signed utility, since Bruiser completion can add Focus even to Strength/Health builds. Preserve begun-item precedence, ordinary strict tie order, and exact cost/completion arithmetic. Do not automatically require a first or second Focus. A Health build with unchanged Focus gets no direct service bonus; it retains its own-upkeep benefit.

## Small, bounded profile and shared quote plumbing

- Keep the last **eight successful ordinary `heal_ally` cast snapshots**, each containing the already-read in-range eligible ally records, including records rejected by the current cap threshold. Copy deficit, HP fraction, recipient trip weight and scan order from the existing live-record loop before further imports. Retain the existing eligibility exclusions. Commit only if the actual cast succeeds in the same observation/turn; unknown/failing casts give no sample. Eight is a fixed resource bound, not a gameplay threshold. Use the supported roster bound; no allocation, second ally scan, all-map work, or new communications.
- For each candidate cap, replay only that small scalar target comparison: apply `worth_healing`, maximize clipped gain, then the existing fraction/order tie rules. This includes a changed target or no target. Preserve both positive and negative differences. Ordinary bank/formation/independent-step heals already pass through this seam. `plan.cpp`'s `Op::heal` uses older construction-time records: initially record its count as uncovered and grant it no measured service, rather than adding a native read or pretending those deficits are fresh. The experiment must report this coverage bias.
- Track exposure using existing `Upkeep.turns` and sample alive-turn ordinals. Before the ring fills, use the collecting inventory epoch's start; after eviction, begin immediately after the evicted cast. End at publication, so long periods without service dilute the score. Collect in a pending profile; invalidate pending samples across unknown turn gaps or provider inventory/stat changes. A same-turn shop loop must retain one frozen profile.
- Publish the pending profile **on entry to a shop visit**, before any chooser call, and hold it fixed until the next visit. This deliberately avoids repricing farm targets after every heal. Use an explicit published-profile revision in `Prices::Key`; `best_emblem`, `affordable_prefix`, and `prices` consume exactly that same snapshot and utility. Before a first usable profile, service is zero. During buying, apply `bought` and real partial/completion effects against the frozen observations. The samples are historical estimates, not current demand guarantees.
- Factor the signed Build utility once. `best_emblem` evaluates full completion; `affordable_prefix` evaluates the actual affordable partial Build with the same function; `prices` retains the actual chosen saving/cost. Cache service results for distinct candidate Focus values within one quote evaluation if useful. The work is at most eight samples times the small roster and existing candidate count, with scalar comparisons and no pathfinding. Measure its fuel; do not introduce a new low-fuel gameplay gate.

The first arm **does not change the first Treasure's stat**. Before Treasure ownership, bypass the service term/new candidate and retain the original chooser, including `Treasure.stat = best.stat`. Thus neither its passive timing nor its initial stat is intentionally changed. After ownership, the new term competes with ordinary protection/Strength/Health choices; no extra first-protection rule is introduced. Preserve actual begun partials even if a later profile prefers another item.

## Non-monotone healing and lost farm work

The existing60% threshold is mandatory. For cap300 versus360, deficit190 at recipient health≥50% yields190 versus **zero**; the low-health exception changes that result below50%. For completed Bruiser Strength versus Focus relative to today's capH, compare H+15 against H+75—not H against H+60. The cap advantage is at most60, the ordinary acceptance floor rises36, and deficit-limited casts may gain nothing. Prefixes use their actual caps.

The completed Focus alternative loses12 Strength and keeps the same50HP. Leave that lost clear speed and resulting own injury/recall expense in `upkeep_cost`; never add healing to `raw_output` or safety admission. On a fixed successful-cast schedule, a larger heal uses the same cast and movement. A suppressed heal receives zero service but no invented replacement-reset credit. Changed future cooldown schedules, support detours and HoR's missing-health damage response are outside this first-order model and must be checked in outcomes. Do not simultaneously change the local three-basic independent-heal heuristic.

## Runtime tests and the Vesper allocation question

Inspect actual new-candidate ranking/purchases and prefix quotes; signed cap uplift, threshold suppression, target changes, covered/unknown/planner heal share, profile age and estimated recovery rounds. Then compare completed recipient recalls and resumed farming/captures, Willow own camp damage/captures/banked gems/deaths, team collected/submitted gems, and fuel/failed actions. No activation is an informative result. More healing without better recipient work, or gains outweighed by lost Willow farming, falsifies the utility. A local ranking reversal is not full-panel strength evidence.

Existing low-income Willow examples do **not** yet establish an income-conditioned Treasure exception. In002-B, lower Willow income coexists with useful distributed service and a team win, but the histories diverge and Treasure remains incomplete; this does not compare buying its remaining shards with the alternative on the same future capture opportunities. A support role may collect little because it should serve allies, because access is broken, or because buying priorities changed. Those mechanisms imply different Treasure choices. The smallest separate measurement is future **personal capture-derived income after the prospective purchase**, remaining cost/time to complete, and the actual alternative's marginal benefit on a source-known matched history. Realized past income alone cannot supply that forecast.

Keep that economy question separate from this first arm. Concentrating rewards on Vesper may help some formations, but it can also deny Willow a purchase whose measured service keeps other farmers working. This shopper experiment estimates one missing marginal value; it neither orders all gold toward Vesper nor bans economy items on other champions.
