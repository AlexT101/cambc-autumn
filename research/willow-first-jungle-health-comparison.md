# A direct Willow Health comparison

2026-10-23. Recommend one isolated sibling of first-protection2ae444fa: **when its existing fresh first-protection winner is Jungle Strength, buy Jungle Health instead**. Compare directly with2ae; keep canonicala67 and the Focus arm separate. This tests the stat of the same first protective family, without assuming the protection-first policy itself is qualified.

The six existing smoke games at `replays/willow-support-item-smoke-20261023-v1/summary-v1.json` give the following purchase evidence. These are selected diagnostics, not a win-rate test; the v1 rollover audit is incomplete and its activation summary starts too late when it counts only completed emblems.

| Protection-arm cell | First relevant purchase | Completion | Interpretation |
|---|---|---|---|
| BigWorld A |3 Jungle Strength shards,494|Jungle792|First protective stat has not been tested as Health; one Treasure Health shard bought later at792 does not change that.|
| Corners B |2 Jungle Strength shards,52|Jungle494|Health could change HP from the first early purchase, hundreds of rounds before mitigation activates.|
| Expanse A |Treasure Strength44; Jungle Strength146|Treasure79; Jungle211|No qualifying protection-before-Treasure purchase. This is not proof of policy nonactivation: quotes can influence work/recall before any purchase.|

The separate Focus arm starts Bruiser Focus shards at836 on Corners and completes1001. Its nominal heal capacity changes with the shards, not just the emblem. It cannot answer the early personal-survival question. Neither arm's smoke outcomes or aggregate healing prove that a particular item prevented a recall or death.

## Exact source contract

Use2ae as the frozen parent. Inside its existing first-protection override in `best_emblem`, substitute only a newly selected Jungle Strength result with `value(jungle, health_stat)`. Keep Willow-only scope, no begun Treasure, neither Jungle nor Durability completed, existing selected protective family and all earlier partial-item returns. A chosen Durability Health remains unchanged. Begun Jungle Strength finishes as Strength; begun Jungle Health finishes as Health. Either completed protection closes this first-protection override; later Treasure and normal build selection resume unchanged. No new inventory ledger is needed.

Return the actual Health candidate's saved value and cost from the existing helper. Do not quote Strength's faster clearing and then buy Health; do not alter `raw_output`, heal formulas, thresholds, draft or the existing price-cache key. `prices` caching can lag changing upkeep; that is a shared pre-existing issue, not part of this comparison. Source-only implementation must preserve complete parent/candidate snapshots and pins.

## What the experiment buys and gives up

For Willow, each30-gold Health shard gives50 maximum HP, versus3 Strength. At own spawn it also restores that50 HP. Full Jungle Health costs the same150 and grants the same completed30% camp reduction as Jungle Strength, exchanging15 Strength for250 HP. Relative to the35% recall line, that adds162.5 usable HP at full health. Corners' initial two shards would nominally supply100 HP instead of6 Strength; no Jungle damage reduction exists until completion.

Willow cannot self-heal. Extra personal HP may preserve service availability, withstand burst or postpone a recovery trip, while Strength speeds her own basics/resets and can reduce how long camps stay alive. Focus and heal cap remain unchanged, as does the ordinary60%-of-heal worthwhile threshold. Health does not fix poor service positioning or authorize teammates to borrow future heals. Different actual Health quotes can alter shopping and farm timing, so even this narrow substitution does not promise identical purchase rounds.

Treasure Health is a reasonable later alternative, but it is a less clean first comparison here. The current Treasure override returns the displaced winner's `best.saved`, whereas `affordable_prefix` prices the actual bought stat. Forcing Treasure Health while preserving that proxy would mix Health with an inconsistent Strength/protection quote; correcting it introduces another pricing difference. The Jungle sibling already returns a truthful candidate through the standard helper and has observed qualifying purchase opportunities. Historical forced-Health tests on other roles caution against generalization but do not settle Willow's support-role tradeoff.

Measure first shard and completion, productive service/farming turns, recalls/deaths, captures/capital and native rollovers. Count actual absorbed healing, without treating a full-cap event as uncapped demand or attribution to the extra HP. No perfect new demand logger is a prerequisite for this bounded comparison. No scripts, engine runs, extraction or source implementation were performed for this note.

## Addendum: cooperative work in the item model

Source check confirms a separate limitation. Ordinary-map `best_emblem:1237–1238` and `affordable_prefix:1379–1380` initialize `others=0`; only synthetic `siege_upkeep` supplies allied output. `upkeep.camp_turns` at5356 increments once if our successful camp basic/cast counter changed that turn, regardless of how many allies worked, their damage, or our share. `upkeep_cost:1199–1206` therefore scales both our clearing-turn cost and observed camp damage by own output ratio `D/(D+deltaD)`.

For a fixed cooperative task with contemporaneous other output O, its completion-time ratio is instead `(D+O)/(D+deltaD+O)`. When O>0 the current ratio overstates that task's shortening from our extra Strength. At O=4D, a55→70 Strength change gives model ratio55/70≈0.786 versus joint ratio275/290≈0.948. Fewer recorded own camp-hit turns reduce the weight of the clearing term, but do not repair this marginal elasticity. Tanking partners reduce the recorded personal injury term; they likewise do not correct its assumed shortening. This helps explain why a low-output support worker may be valued as if it controls the entire remaining clear.

This is a conditional model error, not proof that Strength has negative or universally overstated net value. Extra personal DPS can increase reward share or free a worker for another task, and camp targeting, damage breakpoints and movement can change. The current own-work proxy remains reasonable for solo work and is deliberately cheap. Neither `camp_turns` nor `memory.crew` measures an actual allied damage share.

The smallest future correction concept is a historical **observed joint-work elasticity** for item pricing only: retain the solo ratio for unclassified own-hit turns, and weight a joint ratio only for own-hit intervals with identified same-group contemporaneous contribution. Aggregate the resulting weights in the existing upkeep horizon; do not sum the current roster's nominal DPS or remote claims into every shopping calculation. Equivalently a measured own fraction q uses `1/(1+q*deltaD/D)` for joint intervals. Unknown attribution must remain solo, rather than inventing other work. Existing counters alone cannot supply q; a visible in-range claimant is only a proxy, not measured damage. A later bounded implementation can record already-known successful target/work context, but should explicitly label any proxy and avoid new live queries or a global ledger. Apply the same conceptual ratio consistently to the two pricing consumers; never feed it into physical HP admission or promise future allied actions. This is a limitation and possible follow-up, not an additional change to the frozen Health arm.
