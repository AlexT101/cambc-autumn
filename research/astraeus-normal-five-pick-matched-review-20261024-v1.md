# Normal five-pick Astraeus: matched ranked losses

2026-10-24. **The strongest concrete loss mechanism is Pilgrimage's central group12 economy: at the same horizon our captures fall440→88 gems while the opponent's rise176→704. More Willow healing did not preserve control of that group.** Two exact map/side/draft cells changed from wins to losses, with the first substantive accepted-action forks on our side. This establishes changed play and a lost economic objective, not yet attribution to uploaded f7/v47 or a proved source regression. Neither team's submission ID is available. Willow-first manipulation batches are excluded by user instruction.

Artifacts: `provenance/ladder-history-replays-20261024-v1/prepared-inputs.json`, `extract/astraeus/index.json`, four payload directories and `audit/astraeus/native-status-compact.json`. Standard v2 extraction, pinned1.0.3 engine `029ecd290dc400e75418178ec386d72cbd7d9f2fc2a2e451bf594ca23566df48`, all four validation passes with no notes. No new runtime was performed by this reviewer.

| Cell | Earlier win / payload directory | Recent loss / payload directory | Final own–enemy score / round |
|---|---|---|---|
| Fish Elkring B | `67fc71af-7d66-40e8-8c82-a0d400cbea6f` / `bbb81e199d59829f` | `deb4ae94-edc6-480f-a0e9-03fd944841bd` / `56be01a6e30d3a98` |1155–902/r855 →539–1001/r741 |
| :3 Pilgrimage A | `9da66955-6268-428c-a955-1549cd080c33` / `4ca5aa1e2eeecd1d` | `62589f4b-d504-4bf7-b641-f3e9de95ce9c` / `e546793a8c82d0bb` |1010–476/r1468 →392–1035/r1403 |

Elkring has **six enemy bodies** because Cassi & Issac split: own Prism6, Vesper7, Marcella8, Willow9, HoR10. The earlier metadata-only actor nominations5/8 were incorrect and are superseded. Pilgrimage own Prism0/Vesper1/Marcella2/Willow3/HoR4.

## Initial forks and limits

On Elkring the extracted event sequence, excluding absolute step index, matches until r132: our Prism6 walks from21,25 to20,25 in the old game, versus20,24 in the new. The routes rejoin at15,25 in r137. At round160 end, all exported champion fields for all11 bodies match; that does not prove identical private memories or cached vision. The next event fork is our Willow9 r161: after the same10,26→9,25 move, the new game adds Attack reset and55 damage to enemy Ryth5 at9,22; the old game does neither. Enemy Ryth's next move differs at162. The preceding160 enemy AoE stun/hit is the same. This is not the f7 stationary-Prism basic-attack branch: the divergent actor is Willow, using a cast after walking.

On Pilgrimage r2 changes only the interleaving of our Vesper1 and Willow3 with the same per-actor actions. At r80, after both games' r79 Vesper dash+attack, old Vesper advances23,45→23,46, resets and attacks enemy Marcella9 at26,49 for55; new Vesper retreats to24,44 without that attack. Enemy Marcella then chooses a different move later in r80. This is the first material event fork, not evidence that the enemy opening changed first. Private state, order scheduling and unrecorded query/fuel dependencies still prevent a branch/source attribution.

Authorized paired own-view requests: both Elkring Willow9 r158–167 and both Pilgrimage Vesper1 r77–86, four windows total, ten rounds each. No additional Prism window requested. Known-info review will check threat/HP/readiness/channel/priority and useful consequences, rather than equating the first fork with the cause of defeat.

## Economic and fault evidence so far

Own play rollovers fall Elkring2→0 and Pilgrimage2→1; opposing Fish has0→0, :3 has202→207 across different match lengths. Native BotErrors and caught-action errors are zero on both sides; draft rollovers/errors are zero. These losses do not show a new whole-game own OOF collapse. Smaller code/fuel differences can still alter existing decision cutoffs without a rollover.

Recent Elkring Prism collected396, banked0 and died0; Willow healed8808.6 versus8489.2 in the longer old game, banked66 versus44 and died0 versus1. Those totals reject a simple loss-of-heal-volume story, not every support/allocation issue. Old Prism ultimately banked440 at855 after earlier tribute starts/cancellations; the new game ended114 rounds sooner. At700 new Prism has396 at23,8, team score462 against946; at741 he remains full-health1540 with396. His final bag plus team539 is935, insufficient to win even under instantaneous banking. No new-game tribute start was recorded for him.

Current f7 `retaining_gems` (`bot.cpp:700–703`) deliberately retains a Prism bag until `winning_bag` or `closing`; `race_left` (`668–681`) estimates our own team's remaining race from ally bags and recent tribute rate, not an exact enemy finish prediction. Thus zero tribute is not proof of a stuck route or a missed immediately winning channel. It remains a conversion question; this bounded review has not established a safe, timely, superior banking alternative.

Observer-only team-wide check, including every carried allied bag:

| Round | Own score | Prism bag | Other allied bags | Score + all bags |
|---|---:|---:|---:|---:|
|700|462|396|33 (Willow11,HoR22)|891|
|720|495|396|22 (Vesper)|913|
|732|539|396|0|935|
|741|539|396|22 (Marcella)|957|

Across all741 recorded round ends, the maximum score-plus-allied-bags is957. This rules out an observed round-end team-wide instantaneous cash-in win, not a hypothetical better trajectory produced by earlier banking. These global bags are not asserted as Prism's knowledge. `gems_short` (`bot.cpp:436–442`) counts self plus visible allies already tributing; `race_left` additionally considers other allies' visible bags or `comms::bag_of`. The latter is a last-posted value rounded up to four (`comms.h:29–34`, `comms.cpp:214–224`), with message contention/reminder timing. No late Prism own-view/comms trace was requested, so exact freshness and perceived altar safety remain unresolved.

Recent Pilgrimage Willow heals9920.1 versus7267.6 but farms15673.8 monster damage versus27996.6 and banks37 versus89; HoR banks121 versus506 and Marcella83 versus385. Prism banks0 in both; he dies0 in the new game versus3 in the old. These are unequal-duration final totals, useful for nominating economic/service conversion rather than estimating an isolated treatment effect. Common-horizon selectors and actor-known windows are pending from the sole runtime/helper worker.

## Pilgrimage's main economic loss is one contested group

Existing capture events at the **same horizon1403**, not unequal game ends, locate the dominant difference. Group12 is the shared northern block at x23–26/y56–59: four Elk, eight Gold clusters and four Gem clusters, worth88 gems/520 base gold, respawning60 rounds after payout.

| Group / side | Old captures / gems through1403 | New captures / gems through1403 |
|---|---:|---:|
|12 / ours|5 /440|1 /88|
|12 / opponent|2 /176|8 /704|
|10 / ours|19 /285|18 /270|
|11 / opponent|15 /225|15 /225|
|15 / ours|1 /33|3 /99|
|16 / opponent|9 /297|9 /297|

Group12 alone removes352 own capture gems and adds528 enemy capture gems, an880 net capture-reward swing. This is loss of control/conversion on the main shared group, not uniform farm inactivity. Old own payouts occur989,1133,1214,1295,1377; new own payout only1076. Enemy first payout advances471→394 and it repeats at641,784,902,996,1171,1246,1384. Every recorded group12 clear converts within6–8 rounds and no group12 capture-reset event appears in either timeline. The first-order failure is not a cleared camp repeatedly abandoned just before payout.

Ownership explains the role-income change: old group12 pays Marcella220gems/1560gold, Willow44/312, HoR176/1248. New it pays our Vesper44/397 and HoR44/312, with no share to Marcella/Willow. Enemy Prism goes from no group12 reward to367gems/2496gold, repeatedly landing the final clear. Reward dominance is not proof he supplied all clearing damage.

Exact clear→capture / paid holders, through1403 (A=ours,B=opponent; ids from native metadata):

| Old win | New loss |
|---|---|
|465→471 B HoR5/Ryth7 (44 each)|388→394 B Prism6 (88)|
|673→679 B Ryth7 (88)|634→641 B Vesper8 (88)|
|983→989 A HoR4 (88)|777→784 B Prism6 (88)|
|1127→1133 A Willow3/HoR4 (44 each)|896→902 B Prism6/Ryth7/Vesper8 (30/29/29)|
|1208→1214 A Marcella2 (88)|990→996 B Prism6/Marcella9 (44 each)|
|1289→1295 A Marcella2/HoR4 (44 each)|1070→1076 A Vesper1/HoR4 (44 each)|
|1371→1377 A Marcella2 (88)|1163→1171 B Prism6 (88)|
|—|1240→1246 B HoR5/Prism6/Ryth7 (30/29/29)|
|—|1378→1384 B Marcella9 (88)|

The decisive territory transitions occur much later than the first r80 micro fork. In the old game enemy Prism dies at946 near35,53, transferring103 carried gems to our HoR; our first group12 takeover follows at989. In the new game our Willow dies770 at19,57 and Marcella777 at19,59 to enemy Vesper, before enemy's784 group12 payout. Later our HoR dies1129 and1314, Marcella1138, Willow1365 around the same northern contest. These nominate specific service, exposure and clearing opportunities; they do not show that a forced engagement, more grouping, or more healing would have succeeded.

Actionable next analysis is whether our northern clearing force can maintain useful damage and safe access while Willow serves it, versus healing/retreat loops that concede group12 to an enemy Prism economy. Preserve the productive side camps and ordinary safety. An improvement needs an actor-known missed safe continuation or a concrete valuation/allocation error on the exact source; neither the global reward swing nor the r80 fork supplies that proof by itself. No additional own-view windows are requested until the already-authorized four have been reviewed.

Subsequent root authorization adds **one** concrete group12 window: new Pilgrimage Willow3 r763–772 (five total Astraeus windows). Events769 show a heal from18,57 to Marcella21,57, then a step to19,57; actual enemy Vesper22,54 attacks295 late769 and attacks/resets first770, killing Willow before her next turn. Remaining at18,57 would be Chebyshev4 from that actual enemy position, but this is only a geometric nomination: the enemy may move/dash, and Willow's end769 enemy-visibility list is empty. The extra window must establish her then-available threat/ward/ally information before judging the movement. No defect is asserted using the observer's enemy coordinate.

## Completed actor-known review

All five exports are now in `provenance/ladder-history-replays-20261024-v1/actor-window-exports-v1/`; hashes, replay identities and authorized intervals are in `actor-window-run-receipt.json`. They record native first-turn observations/actions, not private World memory, shared-memory words or evaluator branches.

**Elkring r161:** the entire exported observation (self, visible champions, local terrain/camps) matches between old and new. Willow is540/700HP with22gems, both abilities ready, no visible ally and one visible Ryth at9,22,763HP, cooldowns6/0. Both walk to9,25. New resets/attacks55; old instead finishes with next priority14, while new retains−41. In162 old Willow acts before Ryth and moves8,25; new acts after Ryth has advanced9,23 and moves10,26. Through167 old remains540HP; new reaches450HP after Ryth closes. This is a concrete cast/initiative/pursuit interaction, not a failed heal opportunity.

Current-source arithmetic explains the priority difference without assuming a new source branch: `combat_priority.h:109–122` bins outgoing/enemy-health and incoming/self-health. At distance3, Ryth's melee/reset cannot hit and AoE is on cooldown. Old reset-ready Willow has110/763 outgoing, bucket1 and priority14; after spending reset she has55/763, bucket0. `idle_priority.h:7–10` with role−1,540/700HP and a nonzero bag yields−41. `turn_order.cpp:89–100` uses turn-start enemy records and live end-turn self cooldowns. Thus a55-damage poke can remove next-turn initiative under the current rule. This is a narrowly testable source seam for pricing post-move attacks while escaping; it does not justify a blanket attack ban, establish the public source, or prove the poke caused the eventual match loss. It is unrelated to the earlier falsified Gold reach-boundary proposal. The f7 four-line change specifically affects stationary Prism, so it is not this Willow reset action.

Actual global activation slots from accepted events (`t`, zero-based), not the round summary's `turn` status codes:

| Round | Old Willow / Ryth slot | New Willow / Ryth slot | Consequence |
|---|---:|---:|---|
|162|0 / 3|8 / 3|Old Willow moves first; new Ryth closes before Willow.|
|163|1 / 0|9 / 0|Ryth starts the odd round in both.|
|164|0 / 1|8 / 1|Old Willow gets the even-round first slot again.|
|165|9 / 0|9 / 0|Both Willow activations are last among five allies.|
|166|0 / 1|8 / 1|The useful even-round escape slot differs again.|
|167|9 / 0|1 / 0|New Willow's recovered priority14 cannot precede the first enemy in an A-first round; Ryth walks14,28 and deals45+45 before Willow moves15,29.|

At r161 Ryth had already moved at slot2 and Willow acts at slot9. His distance3 from her ending tile is **outside his next activation's melee/reset reach2**; this is pursuit/contact risk, not immediate lethal damage. The old game also alternates priority14 and−41 later, so even the old behavior is not a stable escape scheduler. New Willow remains540HP through166 and falls to450 at167; old remains540 through167. Existing allied next priorities after161 are HoR12, Vesper9, Marcella−29, Prism−32: Willow14 is first, Willow−41 last. A higher own-team priority cannot beat the opponent's first champion when that team starts, and does not prove that the later path or match would improve. The separately scoped experimental design is `research/willow-support-contact-priority-design-20261024-v1.md`; it does not preserve a spent reset as fictitious outgoing damage.

**Pilgrimage r80:** the entire exported observation also matches. Vesper is1000HP/empty bag, reset ready and dash cooldown7; enemy Marcella26,49 is1145HP with both spells ready, and own HoR23,37 is distant. Old advances into attack range and deals55 with a reset; new retreats24,44, returns23,45 at81 and retreats24,44 at82. Neither takes damage in the inspected window. This nominates a full-health attack-versus-retreat reversal, not an obviously safe forced engagement: the visible enemy can cast, and HoR is far away. The native observations do not identify which safety/farm/search branch admitted or rejected the steps. No direct causal link to the much later group12 takeover is established.

**Pilgrimage r763–772:** Willow sees no enemy on any alive turn763–769. At769 the only visible ally is Marcella21,57 at1163/1500HP; Willow heals the actual337 deficit from18,57 before moving19,57. Most adjacent group12 members are static-map-only; gem cluster23,59 is known alive120HP. Actual enemy Vesper22,54 occupies a bush tile and placed a personal ward23,54 at764 (observer evidence). Enemy visibility of Willow does not confer reciprocal visibility. She can see ally damage but the window supplies no visible attacker identity/position. She dies before her770 turn, so there is no missed escape turn after taking the first295 hit.

This last case supports a **vision-asymmetric loss of support access**, not “Willow ignored a visible ready Vesper.” Her older sightings/comms may have warned of a threat, but this export does not expose them. A defensible source-known follow-up would ask whether existing unseen-enemy reach/ward uncertainty or ally damage evidence should reject the *post-heal* advance while preserving the delivered heal and productive camp access. It must first reproduce an actual known-information inconsistency; staying at18,57 is not certified safe against a hidden mobile enemy. No gameplay correction or additional runtime is authorized by this review.
