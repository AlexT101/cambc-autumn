# Three-pick screen: next bounded draft experiment

2026-10-24. Existing source-pinned result/economy records only; no new code, games or tool implementation. Evidence: `provenance/khaos-v34-ladder-intake-20261024-v1/fixed-three-role-screen-v1/RESULT.{md,json}`, native audits there, `f475-v33-complete-output-v1/RESULT.json`, and symmetry-correct `economy-inventory-v2/RESULT.json`.

## What the completed controls establish

Verified the reused P/V/HoR f475 control is **7/12 against v33**. New Stellar is3/12 against f475 and4/12 against v33; Cassi7/12 and5/12; Marcella6/12 and6/12. All72 accepted drafts/body counts match, no runner failures or native bot errors. Play rollovers remain (candidate S15/20, C24/30, M15/12 against f475/v33 respectively); no fuel-equivalence claim.

Common-v33 results below are physical A/B wins, not pooled across opponents. Map rewards are entire public-layout ordinary rewards, not accessible shares.

| Map | Ordinary gems/gold | P | S | C | M |
|---|---:|---|---|---|---|
|Collision|280/1700|W/L|W/W|L/W|W/L|
|Fragment|68/540|L/L|W/L|L/L|W/W|
|Packs|148/1120|L/W|L/L|L/L|L/L|
|Broken Curve|346/1920|W/W|L/L|L/W|L/W|
|Gold Rush|66/720|L/W|L/W|W/W|W/W|
|The Farm|682/3940|W/W|L/L|L/W|L/L|

The strongest repeated local mechanisms to investigate are **Marcella Fragment A/B wins against both opponents** and **Cassi Gold Rush A/B wins against both opponents**. These are four deterministic cells each, not confidence estimates. Marcella supplies immediate damage/reset and stun immunity without requiring an initial gem bag; Cassi supplies a fourth body at the cost of linked death and divided control. Those are hypotheses for the observed results, not established explanations without timelines.

An economy-only cutoff is premature: Fragment68 and GoldRush66 ordinary gems are similar, yet Cassi fails Fragment against v33 while winning both GoldRush sides against both opponents. Fragment has only2 gem clusters/6 gold clusters, versus GoldRush6/28, and geometry/distribution differ. Stellar's Fragment benefit is A-only; on GoldRush its winning side flips between opponents. Cassi's overall advantage against f475 disappears against v33. High-gem BrokenCurve/TheFarm strongly retain P against v33, but no whole-layout threshold establishes what Prism can actually collect. All alternatives failing Packs against v33 is a useful negative control; do not replace P globally.

## Primary recommendation:32-row revealed-prefix feasibility screen

Use exact f475 gameplay with **P/V/HoR, M/V/HoR, V/HoR/P, V/HoR/M**, on **Fragment and Packs, both physical sides**, against two separately frozen f475-gameplay roster proxies:

1. Marcella/Vendetta/Tavi, the observed Mite three-pick recipe.
2. Vesper/HoR/Vendetta, the observed Fish three-pick recipe.

This is4 recipes×2 maps×2 sides×2 proxies =32 new rows. Pin all sources and actual accepted picks. These are observable-recipe proxies, explicitly not replicas of Mite/Fish code, source, adaptation or future picks. Their fixed nature is appropriate for this mechanism test.

The two delayed-carry recipes commit Vesper then HoR, and choose the last slot only after two opposing picks could legally be observed. Rules hide a simultaneous pick until both teams finish that round. Compare delayed P with early P and delayed M with early M: changing order changes IDs, tie initiative, starting allocation and claims, so a gain from V/HoR/M alone is not evidence of counterdrafting. Compare P versus M at the same order and same proxy to test a composition interaction. Fragment is a repeatable immediate-output opportunity; Packs is the failed-alternative stress case. This gives a practical falsifier rather than a threshold tuned to every map.

A narrow subsequent adaptive prototype can branch on the two **actually revealed** picks, using the tested same-order P/M alternatives. The mechanical hypothesis is that revealed HoR's hard stun increases the relative value of Marcella's immunity, while the other recipe tests whether general immediate damage rather than stun immunity explains the result. Do not hardcode team names, infer hidden third picks, or assign the branch before seeing the controlled interaction. The fixed screen is finite; it need not wait for proof of every public private decision. If the two proxies favor the same choice or order dominates, prefer a simple composition/order improvement instead of inventing a counter rule.

## Separate small synergy option

Marcella-first three-pick plus the approved delayed-tribute-value arm is a meaningful **12-cell common-v33 comparison across all six maps/both sides**, reusing the existing M/V/HoR6/12 control. The current income arm cannot activate in ordinary P/V/HoR; inserting Marcella creates a new actual recipient. Keep this separate from delayed order/proxy changes, and preserve the approved empty-bag, independently affordable, actual-recipient, complete-cycle delay and no-future-budget rules. Measure whether the bonus actually changes a quote and is followed by capture→tribute→purchase, rather than treating a result flip as activation. This is a useful combination experiment if capacity permits, not a prerequisite or strength gate for the primary32 rows.

No new release recommendation follows. Use exact common-opponent rows and first productive decision/capture evidence to decide the next generalist change; public recent batch changes without submission pins remain contextual only.

## Completed 44-row follow-up: no revealed-prefix selector justified yet

Evidence: `provenance/khaos-v34-ladder-intake-20261024-v1/three-pick-order-proxy-income-screen-v1/RESULT.{md,json}`. All44 new rows have the intended rosters/body counts and zero native bot-error steps; play rollovers remain. These proxies retain f475 gameplay and do not reproduce the real teams. W/L below uses the candidate's physical side. MVT and VHV denote the two fixed proxy recipes above.

| Proxy | Map/side | P/V/H | M/V/H | V/H/P | V/H/M |
|---|---|---|---|---|---|
|MVT|Fragment A|W|W|W|W|
|MVT|Fragment B|L|W|L|L|
|MVT|Packs A|L|W|W|W|
|MVT|Packs B|W|W|W|W|
|VHV|Fragment A|W|W|W|W|
|VHV|Fragment B|W|W|L|L|
|VHV|Packs A|W|W|W|W|
|VHV|Packs B|L|W|W|W|

Early M wins all8 cells against both proxies. Delayed P and delayed M have **identical outcome cells**, both losing Fragment B against both proxies and winning the other6. Thus their equal totals do not hide complementary wins. Delaying M loses Fragment B in both matchups relative to early M; substituting M for P after V/H yields no outcome improvement here. Delaying P improves Packs A versus MVT and Packs B versus VHV, but loses Fragment B versus VHV. This is a concrete order/composition interaction, not evidence for a revealed-enemy P/M selector. Early M weakly dominates the tested choices on these eight cells, but the earlier common-v33 six-map screen still favors P overall7/12 versus M6/12; Packs M loses both v33 sides. Do not turn proxy success into a blanket counterdraft or global Marcella-first replacement.

The separate income experiment is M3+income5/12 versus reused M3 6/12: **Packs B is gained; Fragment B and Gold Rush B are lost**, the other9 cells match. Candidate A remains3/6 and B falls3/6→2/6. This does not justify automatically attaching the income overlay to a three-pick Marcella recipe, and does not refute its different-role M+H result in the larger screen. Outcome flips alone do not establish bonus activation or the causal economic chain.

Recommendation: retain early M/V/H as the simple three-pick experimental challenger, with plain P/V/H as its control; leave dynamic prefix branching unimplemented. A bounded macro comparison of **Fragment B early versus delayed M against the same VHV proxy** would isolate an order effect within the same composition if draft diagnosis resumes: inspect opening allocation, first productive capture/tribute and the first accepted-input fork before attributing the result to initiative or farm claims. No extra broad order grid is warranted now. Broader generated validation remains focused on the independently selected M+H arm; keep future three-pick draft validation source-pinned and separate from that gameplay result.
