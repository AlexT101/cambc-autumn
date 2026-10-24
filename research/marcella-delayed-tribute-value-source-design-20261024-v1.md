# Marcella delayed tribute value: bounded source design

2026-10-24, source-only proposal for normal Astraeus f7. **Unimplemented and lower priority than the observed mixed-Monolith opportunity.** Mite's Big World loss does not demonstrate that this omission caused its defeat: the winning enemy Marcella banks a distinct 228-gem boss reward, while Mite leads gold. This file specifies a separable economic hypothesis, not a recovered Mite policy.

## Existing objective and units

`bot.cpp:879` returns `worth / (rounds * (1 + rounds / horizon))`; horizon is100 on maps up to50 and scales with the longest dimension. Farm worth is gem-equivalent, not raw damage or raw gold. `prices().per_gold` (`1344–1362`) is remaining modeled gem share × upkeep saving / next emblem cost, in gem-equivalent per gold. `farm` multiplies it by `gold_paid` (Treasure/Vesper) and then group base gold (`1961`,`2216`). `known.gems` clips reward to the score still needed and applies the same home-ground/stickiness weight. Thus a new passive-gold term must use `prices().per_gold`, not an arbitrary gold/gem constant.

`HomeTrip` (`1407–1431`) subtracts modeled healing/emblem value from a recall-to-spawn-before-altar trip. Its `gold_in` is capture gold that can exist before that shop. Marcella's passive gold does not exist until tribute completes; **never pass it to this pre-tribute `gold_in`**. The same capture gold already appears in farm worth; the existing HomeTrip interaction is documented in source and must not be expanded silently.

For a carried bag, the ordinary farm comparison subtracts `bank_now` and compares marginal chaining against a new cycle from the altar (`2266`,`2375–2384`). Simply adding future tribute income for the next group ignores that chaining also delays the existing bag's income. It can perversely reward more delay. First arm therefore excludes carried bags entirely.

## Narrow first-arm contract

Eligible only while ordinary farm evaluates a new economic route and all are true:

* Self is Marcella, `my_gems()==0`, not winning/closing, not in a crew/siege/banking job, and `prices().per_gold > 0`.
* Group is non-Monolith, harmless (`strength==0`), has gems but zero base gold, is single-holder under existing `holders`, is not an allied claim, and is not already held by an eligible Prism or any visible ally. This targets the unambiguous pure-gem group family and avoids changing mixed gold accounting in the first arm.
* Existing belief/route and ordinary risk/deadline filters pass. No visible enemy occupies or threatens the work; do not bypass existing pack-zone/step guard. No known enemy altar lock or active avoided altar may invalidate the common nearest-altar route used by this quote. The selected path must have finite group→altar and own-spawn→group distances.
* The full modeled spend-and-return interval fits the existing `bag_rounds_left` horizon. This is a future-value quote, not a promise that unseen enemies will never interfere; normal observation and banking safety remain authoritative.

No identity or exact named-map branch. Public terrain/group layout, own champion/items/gold, known camp/lock state, current claims and visible units supply the conditions. An enemy draft filter is unnecessary: a correct own-income model should apply wherever the eligible state occurs.

## Quote and comparison

Keep the baseline worth and cycle exactly intact. For an eligible single-holder pure-gem group, let:

* `q = group.gems` (only if less than the remaining winning requirement; a winning capture gets no investment bonus).
* `w = known.weight` and `v = prices(world).per_gold`.
* `b = 2 * (Treasure ? 1.2 : 1.0) * q`, the future passive gold. Equivalently `2 * paid * q` for Marcella; **do not multiply by Treasure a second time** if reusing farm's already-paid `per_gold`.
* `T = steps + wait + clear_rounds + capture_rounds`, actual work-to-payout estimate. No HomeTrip utility subtraction.
* `D = T + group_to_altar + tribute_turns(q) + recall_turns + heal_turn + spawn_to_group`. `heal_turn` is one only if currently hurt; harmless work adds no modeled camp damage. This deliberately prices income only after tribute, a separate recall/shop, and returning to productive work. No speculative overlap of recall with tribute.

Compare `baseline_rate + rate(world, w * v * b, D)` with other ordinary farm values. This is a small, explicitly heuristic delayed marginal-income term; it does not replace the score term or assert a physical payout clock. Zero it if `D` is nonfinite/unreachable or exceeds the race horizon. It never mutates gold, items, claims or the actual banking sequence.

The pure-gem/single-holder/empty-bag restriction avoids assigning passive income to a group a crew only damages, to a split reward, to another actor's eventual tribute, or to a bag already valued in a previous choice. Existing `prism_capture_holder` and allied-claim exclusions remain ahead of this branch. An arriving claimant or changed holder must invalidate the quote on re-observation; no promise to seize the payout from Prism.

## Integration and cost discipline

Use the already-computed `steps`, `wait`, `clear_rounds`, `capture_rounds`, `known.weight`, `paid`, and `per_gold`. `pathing.centre_to_altar(g)` is already queried by `too_late`; Marcella has no dash, so its walking distance semantics fit. `map.ally_steps(g)` returns draft distances or the existing cached spawn field. Evaluate these once per eligible candidate and retain the existing cache/invalidation rules; no new native unit queries, per-enemy scans, memory message, or fuel gate is needed. There may be a first-use route-field cost when draft geometry is unavailable; do not pretend it is free or gate behavior on available fuel.

The early optimistic prunes at approximately2245,2270,2347 must include a valid upper bound on the added rate. For empty-bag eligibility, using `baseline_worth + nominal_bonus` in the existing no-horizon upper numerator and omitting the added bank/shop latency is optimistic, hence safe for pruning. Keep final scoring separate and delayed; do not insert the nominal bonus into `known.gold`, `HomeTrip`, crew value or current gold. A pure helper can return eligibility/nominal/delay inputs so all prune and final paths agree. No fresh cache key is required if the small quote is computed from current per-gold/items/claims each evaluation.

## Required activation evidence before a broad run

First record one exact normal-f7 own-view route choice where an eligible harmless gem group loses under baseline but wins under the delayed quote. Record both candidate groups, shares/ownership exclusions, distance/clear/capture/tribute/shop-return terms, score horizon, current items and both final rates. Check that the proposed path actually banks the gems and spends the resulting income; unchanged choice means nonactivation, not rejection. Use the already-authorized runtime worker for any eventual build/replay test. Do not combine this arm with Monolith admission, a draft swap, new aggression, or a fixed Marcella item build.
