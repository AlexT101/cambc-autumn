# Boss Battle: altar access precedes the carry question

2026-10-24. Read-only analysis of the source-pinned generalist-support edge screen. This is not a ladder source-attribution claim or a new draft threshold.

## Evidence and limits

All paths below are relative to `provenance/khaos-v34-ladder-intake-20261024-v1/edge-economy-draft-screen-v1/`:

- `BOSSBATTLE-PS-ECONOMY.{md,json}` and its readouts; native final statistics are authoritative.
- `bossbattle-replay-analysis/index.json`: support-P A `ef551e97b6b5d827`, P B `961aa249c92c14aa`, support-S A `e6a5c10ddd2fc8c4`, S B `c8e396e5fd500336`; existing events and round snapshots under those hashes.
- Static map `bossbattle-replay-analysis/maps/5234744d216fb538.json`; opening own-views `opening-own-view/support-p-A-prism-r30-34.json` and `support-s-A-vesper-r30-34.json` beneath the analysis directory.

The helper flags one S-A HoR derived-gold mismatch (9304 versus native 8344), and an ambiguous dynamic-group/static-reward join. Use actual paid shares and native balances, not the flagged nominal reward join. Empty explicit Willow-heal event lists do not mean no healing. End-round `sees` is not actor-start knowledge. Collected gems can include recirculated stolen bags.

## The physical bank gate

In raw physical coordinates, the sole altar is `(25,20)`. Its eastern neighbors `(26,19),(26,20),(26,21)` are walls; `(24,19),(25,19),(24,21),(25,21)` are holes. The only remaining adjacent standable tile is `(24,20)`, initially occupied by Monolith camp 20. Camp 27 is at `(23,20)`. The altar itself is not a standing/landing tile; tribute requires adjacency. Consequently there is no legal tribute position before camp 20 dies. P-A's zero banking before round 570 cannot be diagnosed as Prism refusing an available bank.

| Arm | Relevant clearing and altar-control chronology |
|---|---|
| P A | HoR4 kills outer camp27 at 514. Enemy Marcella7 kills inner camp20 at 570, clearing the group. Own lock (placed198) is destroyed578; enemy lock placed227 has no destruction event. Enemy Willow8 starts the first tribute at593 and finishes605 with113 gems. Own side never banks. |
| P B | Own Vesper6 kills27 at513; own HoR9 kills20 at533. Enemy lock falls534. HoR9 starts tribute540 with683 gems and finishes609; Marcella7 later banks332, reaching1015 at655. |
| S A | Enemy Marcella7 kills inner20 at546; enemy lock falls562. Own Willow3 starts tribute572 and finishes574 with16 gems. Own Vesper1 kills outer27 at577; group capture585 pays400 split between Stellar0 and Marcella2. Enemy replaces lock588; substantial later banking is not an immediate opening payoff. |
| S B | Enemy Marcella2 kills27 at554 and enemy Prism0 kills20 at584. Own Marcella7's first successful tribute finishes696 with499. First own boss-group capture is much later,1220. Opening the entrance and capturing the entire group are distinct. |

P-A and S-A ordinary captures at round400 are close:524 versus528, with no own deaths and no banking in either. P-A subsequently loses HoR4's203 gems at518, Marcella2's347 at566, Prism0's155 at574, Vesper1's494 at579 and Willow3's15 at594. Enemy Prism5's bag rises136→339 on the first kill, while Focus rises436→740.5: exactly203×1.5 additional Focus. That is a concrete carry-growth feedback after the gate fight, not proof the earlier farm allocation alone caused the loss. P-A ends with1376 collected, zero banked and60 deaths. P-B instead wins with Prism retaining849 and no own deaths, demonstrating why retained Prism gems alone are not a banking defect.

## Opening allocation does have a measurable effect

Both A arms first clear at26 and capture at32. P's Prism receives30 gems/220 gold and its Focus rises80→125; S's Vesper receives30 gems/292 gold. The72 difference is consistent with the33% eligible capture-gold bonus, including flooring. It is not evidence of a hidden strategy or sole-worker clear. Both opening own-views show ordinary recall-stub cancellation/movement after capture. This does not explain the later access/control failure by itself.

## Existing source already recognizes sealing groups

The reviewed f475-derived P source, `bots/variants/willow-v47-generalist-support-work/src/bot.cpp`, already implements `altar_access` (479), `altars_sealed` (646), `seals` (655), `siege_candidate` (3542), and sealing-aware `siege_ready` (3586–3594). A live Monolith can qualify off a Monolith-only map when it seals an altar. Therefore no new Boss-Battle classification is proposed. The unresolved question is the actual commitment, safety and execution decision under newly revealed opposition, not absence of a gate concept.

## One requested actor-known window

Request **P A HoR4 rounds510–518 inclusive**, from payload `ef551e97b6b5d827`. At510–513 it approaches under a shield; at514 it moves26,17→25,18 then dashes23,19, damages camp20 and kills27. At515 it attacks20; at516 it attacks20 again; at517 there is no accepted own action; at518 enemy Prism kills it. End-round HP/shield:5141980/914,5151980/914,5161693/0,517265.4/0. End-round enemy visibility is empty at514 and all five enemies at515; a ward is placed515. This does **not** prove the dash knowingly entered those enemies. `blocked` records alone also do not prove a failed retreat movement.

Inspect actor-start visible enemies, readiness/stun, camp state, legal exits and activation order at515–518. The useful question is whether newly revealed threats were handled by normal combat/retreat versus continuing an exposed siege, and whether a known feasible exit existed. If private caller state remains material, request only that branch after the own-view. Do not force retreat, assume guaranteed escape, or treat ordinary recall stubs as retreat intent.

For later draft work, the separate three-pick losses motivate a small P/V/HoR versus Stellar/V/HoR, Cassi/V/HoR and Marcella/V/HoR screen across all six published three-pick maps/both sides with fixed opponents. Five-pick Willow substitution cannot answer those cells; no selector threshold follows from this Boss Battle pair.
