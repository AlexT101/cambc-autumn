# Willow service shopper: bounded activation panel

2026-10-24. This is a six-cell activation and regression investigation, not a strength estimate. All twelve games were already complete before the user's CPU restriction. Follow-up used saved bundles, one low-priority worker and, for native extraction, approximately 0.1 seconds running followed by 0.9 seconds stopped in an isolated process group. No browser renderer or additional games were used for this analysis.

## Sources and results

The control is exact f7 Astraeus `f475b8521cada611754076822402a266c43be8de76ce0f2b504b268ff3335824`; the service candidate is `730051ef2d15d38f6d84abe3ae250586100c3323c3bb439ca2bfcc516ac1737f`. Both play frozen v33. The first Treasure policy and active draft are unchanged.

Control wins 3/6 and candidate wins 2/6. Cells 102306611 A changes from control victory at round 875 to candidate defeat at 891. The other five cells retain their winner and duration. Inner replay payloads are identical on Archipelago 102306009 A, Archipelago 102306002 B, and Gold Rush A/B. Archipelago 102306002 A changes payload while retaining its loss at round 830.

The corrected compact result is `provenance/willow-service-lowcpu-audit-20261024-v1/service-panel-light-audit-v2.json`. Its first version contained an unfilled per-row `candidate_won=false` field; the separately derived paired table was correct. Preserve both, use v2. Fuel readings above 100k include draft/first-turn allowances and are not equivalent to native play rollovers.

Exactly the four differing bundles were extracted. All four validate with no soft notes. Native audits report no BotError or draft/other errors. Play rollovers, physical A/B: Cells control 1/8 versus candidate 2/2; Archipelago control 0/1 versus candidate 0/1. All twelve earlier stdout audits have zero caught-action and turn-order markers. Different late trajectories prevent interpreting whole-game rollover totals as the cost of the change.

## First observed differences

**Cells:** accepted actions match through round 410. At round 411, turn 0, Willow3 moves from (1,25) to (2,24) in control and (1,24) in candidate, then starts recall at the respective endpoint. Her purchases match through the Jungle Strength emblem at round 405. Control next buys two Power Strength shards at 447, completes Power Strength and buys Bruiser Strength at 707; candidate buys Power Strength at 455. This does not establish a Focus-purchase improvement. An unchanged item sequence also does not rule out policy activation: service utility can change the value of prospective purchases and therefore gold or route valuation before any new item is bought.

Willow's whole-game healing changes from 16,559 to 12,180 HP, with 51 versus 40 heal casts. Completed recalls change from 8 to 9; starts/cancellations are 752/743 versus 763/754. Candidate-side camp conversion events change from 61 to 56 while the opponent's change from 55 to 60. These downstream differences are useful conversion outcomes, not an attribution of the loss to one path step or the healing model.

**Archipelago 102306002 A:** the first difference is Willow3's round 5, turn 8. Both cancel recall and move (17,58) to (16,59), but only control places a ward at (14,57). Purchase chronology, healing totals and camp conversion counts match; both teams have 68 conversion events. This occurs before service shopping could explain a different purchase. Existing fuel-based optional work is a candidate explanation; no native fuel rollover occurs on candidate A in either game. A skipped optional action need not exhaust the turn.

Event witness: `provenance/willow-service-bounded-extract-20261024-v1/exact-four-witness-v3.json`, SHA256 `b25d0bd2b5374aa69153c8adcbd7173abe5ab49fb277ac8976fd60e616c7f2c5`. Earlier v2 incorrectly copied the archive hash into a field labelled native payload; v3 separates archive and embedded `replay.repl26a` hashes. The extraction itself is reused; no games were rerun to correct reporting.

## Next correction

Keep both variants. First reduce the service bookkeeping charged to non-Willow and pre-Treasure quotes without changing the active Willow model, signed utility, candidate order or partial purchase arithmetic. Identical Gold Rush replays show mean candidate fuel increases of about 79 on A and 113 on B despite containing no Willow. The source paths are documented in `willow-service-shopper-cost-lifecycle-review-20261024-v1.md`; this is a measured nomination, not an instruction-level cost attribution.

The completed per-actor alignment confirms normal acted turns at both first differences. Cells411 consumes 52,646 fuel in control and 51,306 in candidate. The end-round410 state matches: 700HP, Strength85, Focus120, six gold, no gems, no channel or ability cooldown, and the same Treasure/Jungle Strength emblems. Archipelago5 consumes 92,670 versus 85,299; control's extra ward work contributes to the final total. These final totals cannot identify the fuel available at an earlier optional-work decision. Alignment recipe, native statuses and pins are in `provenance/willow-service-bounded-extract-20261024-v1/willow-actor3-fuel-alignment-v1.json` (SHA256 `714e056b1053665f18ffda725c2c8ee2150d8e0b07d288396c741b4168b09221`).

A source-known quote/profile or a faithful trace is still required to distinguish a changed economic valuation from a fuel shortcut at Cells411. The disabled-utility child `ece3cf9d` passes independent source review; runtime validation remains pending. Do not force Focus purchases, relax coverage, or discard the upgrade solely because of this small panel. No numbered release or server submission follows from these results.
