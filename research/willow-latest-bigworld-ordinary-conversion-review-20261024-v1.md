# Latest parent Big World B: capture output versus lost carry

2026-10-24. Read existing compact outputs only; no new runtime, extraction or scripts. This source-known latest-parent game is separate from the source-unverified Mite comparison and the isolated boss-cache optimization.

Exact latest parent `astraeus-4d08241` aggregate `f599a31faa0251321beb97a726918286e266218ceb3e183b8271e41c5c84718c` is B against frozen v33 A. Existing evidence: `provenance/willow-phased-solo-boss-4d08241-v1/{preflight.json,PAIR-RESULT.md,extracted/index.json}`, extracted parent `15a703f86fd6cbf7/{meta.json,events.jsonl.gz,rounds.json.gz}`. Bundle SHA256 `15a703f86fd6cbf7ca9b14fddc9136f2100bc5afce87520905b274c82cbe670c`; it is not the inner payload SHA. Root verified the inner payload separately and Luna is correcting the native audit's reused bot label. The pinned extraction result is **A1110–B474 at780**;1005 belonged to the separate boss-candidate opponent result.

**Unlike Mite's zero-PvP ordinary-economy loss, this local result is dominated by transferred carried gems.** A captures828 gems, B756: a72-gem production deficit. A kills B HoR9 for21 gems at709 and B Prism5 for261 at744, then banks those282. Neither team ends with unbanked gems. Thus the636-point result gap is72 ordinary-production deficit plus564 from the282-gem transfer counted on both sides. This accounting does not establish a guaranteed counterfactual win if those deaths were avoided.

| Role | v33 A ordinary collected | Latest B ordinary collected | Submitted A / B |
|---|---:|---:|---:|
|Prism|131|261|131 /0|
|Vesper|331 (plus261 stolen)|31|592 /31|
|Marcella|176|183|176 /183|
|Willow|8|42|8 /42|
|HoR|182 (plus21 stolen)|239|203 /218|

B Prism is productive at capture, not an idle farmer: g7 contributes82, g23 45, g9 74, g4 45 and g5 15. B Vesper contributes only g19's16 and g23's15 despite24k monster damage and no death; A Vesper's331 ordinary gems span g6=123, g8=148, g5=30, g22=30. Role allocation and holder choice matter: low Vesper personal captures alone do not prove wasted team work. B actually takes more total capture events,43 versus42, including nine harmless g3 cycles versus A's seven g2 cycles. Neither side converts g14/15 or either Monolith. Therefore the Mite winner's repeated g2/g14/teleport routes are useful external examples, not proof the same missing feature caused this local loss.

## One concrete decision window

Nominate only **latest-parent B Prism5, rounds735–744 inclusive**, with raw map coordinates preserved separately from own-frame export coordinates. Prism holds g5 at raw `(35,56)`,528/1480HP and246 gems. It clears the group733, steps onto a member tile734, and payout occurs740. At735/736 it manually cancels and restarts a Home recall (two turn ends left);737 has no action;738 manually cancels a recall with **one turn left**, then restarts. By740 it has261 gems, stuns visible Vesper1;741 casts ground damage at Willow3. Vesper walks/reset-attacks742 for400. Prism retreats742–744, acts before Vesper744, but Vesper's newly ready dash/basic kills it and steals261. Vesper banks those261 at779.

Round-end `sees` records list enemy Vesper1 and Willow3 for Prism from736 through741. These are a strong nomination for an actor-known check, not a substitute for exact start-of-turn vision/readiness. No own-view has been extracted here. The key question is why the near-complete recall was cancelled at738 while holding a large bag and observing an approaching enemy: legitimate capture timing, recall interception, carry/retention preference, or safety-model decision? Do not infer this branch from timer values alone.

Frozen latest source narrows the candidate branches. `bot.cpp:4154–4192` first handles game-ending actions and `want_home`; a held capture then routes through `capture_recall`, otherwise ordinary banking/shop recall can keep. `capture_recall:3340–3379` refuses departure before payout (`round+channel<payout`) and contains a special Prism retained-gem/shop valuation; `recall_outruns:3328–3337` models recently seen enemies' approach to the channel. `want_home:2849–2869` exempts held captures from the generic low-health test and changes pursuit handling when payout is soon. The real738 cancellation could fit these interactions, but private outputs have not been established. A narrow source-known window can distinguish them without prescribing automatic banking or forcing retreat from every capture.

Native parent status is three B and four A play rollovers, zero bot errors; neither Prism5 nor Vesper6 is among B's rollover actors. This is not the Mite historical343-versus51 profile. The proposed inspection is a more direct next decision diagnostic than treating this local game as an ordinary-farm-only deficit. Keep the independent boss-cache implementation scoped to its already-reviewed storage optimization.
