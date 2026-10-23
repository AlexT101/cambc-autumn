# BigWorld A: initial roster-control mechanism

Read-only comparison of existing extracted games,2026-10-23. Latest Willow337f loss is `analysis/4cb49d0749686d58`; old-draft b8108db1 win is `analysis/a65627b1f2e060b3`, both under `replays/fish-roster-emulator-panel-20261023`. They use the same frozen opposing roster emulator, **not Fish's private implementation**. No new run, extraction, script or source change. One paired deterministic map is a mechanism witness, not a general win-rate claim.

Willow ends905 at588–1006; old draft ends989 at1006–824. Comparing final actor totals alone gives the winner84 additional turns. The following comparisons use the same completed round. Capital means submitted plus currently held gems; it is not guaranteed future score.

| Round | Own submitted W / old | Own capital W / old | Opponent capital W / old | Own earned gold W / old |
| --- | ---: | ---: | ---: | ---: |
| 200 | 72 /81 | 128 /143 | 159 /151 | 801 /928 |
| 400 | 203 /234 | 278 /309 | 352 /285 | 1812 /2311 |
| 600 | 281 /402 | 433 /516 | 591 /456 | 3125 /3505 |
| 800 | 487 /639 | 711 /768 | 892 /635 | 4866 /5018 |
| 905 | 588 /770 | 875 /923 | 1050 /726 | 5667 /6061 |

At905 the own score improvement182 decomposes into48 additional owned gems plus134 fewer unconverted gems. Meanwhile the opponent has324 fewer owned gems. This is a mixture of reward allocation/conversion and a slower opposing economy; it is not explained by the replacement actor's large final damage alone. Own total camp damage reconstructed from rounded event `cdmg` is about42.4k/42.2k at400,70.4k/72.6k at600, and115.1k/123.2k at905 (Willow/old). Thus total damage is initially similar and eventually only about7% higher, although the fourth actor's output is much larger. `cdmg` is rounded in extraction and differs slightly from exact final engine counters; use it for approximate equal-round comparisons only.

## A concrete productive ownership sequence

Group6 contains two Elk, one Wolf, two gold clusters and one gem cluster:41 gems/260 base gold, six members near59–61,10–11. Group7 mirrors it. Existing map export `analysis/maps/c890c7d4607bc45c.json` supplies these public facts.

| Group6 cycle | Willow337f | Old draft |
| --- | --- | --- |
| First | Prism clears107; Prism receives41gems/260gold at115 | Prism clears63; Vendetta receives41gems/260gold at69 |
| Second | Clear294 by Vesper; Marcella receives41/312 at300 | Vendetta clears174 and receives41/312 at180 |
| Third | Marcella clears399 and receives41/312 at405 | Vesper clears280 and receives41/398 at286 |
| Fourth | Willow clears484; Prism receives41/260 at491 | Vesper clears369 and receives41/397 at376 |

The old-draft first clear uses approximate group6 damage Prism1826/Marcella1305/Vendetta1663/HoR1716. The Willow first clear uses Prism2980/Marcella1785/Willow1745, with no HoR group6 damage. Faster focused completion and holder selection give the new melee worker an early growth start: by100 Vendetta has260 earned gold and118 Strength; Willow has0 and55. This is not a solo-Vendetta clear.

The third old-draft cycle is particularly informative: group6 damage during240–286 is Prism1927/Marcella1305/Vendetta2353/Vesper925, but **Vesper alone receives the payout**. In the fourth cycle Vendetta and Vesper deal3239 and3271 respectively, and Vesper again receives the payout. In the Willow second cycle175–300, Prism supplies4914 group6 damage and Vesper379; Vesper lands the final clear, but Marcella receives the capture reward. A final hit is not reward ownership, and global shared damage is not proof of a shared claim.

At400 Vesper has captured8 versus93 gems despite doing9261 versus6386 camp damage. At905 he has66 versus234 captured/submitted gems and625 versus1670 earned gold, with nearly equal total camp damage21508 versus22004. His final296 collected gems/2068gold include another84 turns and should not replace this equal-round comparison. The changed crew/holder distribution concretely explains why his reward and growth can rise much more than his damage.

Conversely the old-draft role displaces some Prism/Marcella production: at905 Prism's earned gold1840 falls to930 and Marcella's2488 falls to523. Aggregate own gold rises only394. The mechanism is not simply adding2240 Vendetta gold to an otherwise unchanged team economy.

## Conversion and the opposing economy

Prism retains287 gems and has submitted0 when the Willow game ends905. **Old-draft Prism also has submitted0 at905**, holding116; his116-gem tribute completes953 and raises own score to985. The old win therefore does not demonstrate an earlier Prism banking fix. A slower opponent leaves time for the later tribute. More rewards initially go to nonretaining workers who already submit normally, reducing the team's unconverted concentration before that final Prism tribute.

The opposing side also changes its autonomous ownership: first group7 is cleared by emulator Vendetta in both games, but its initial payout goes to Vendetta in the Willow game and HoR in old draft. Its second payout is276 versus619; by905 it pays eight times versus four. That alone is164 fewer captured gems. Opponent total earned gold is5209 versus3047 at905. These are observed allocation and timing differences under a fixed source, not proof of direct suppression by our Vendetta.

Our first old-draft kill is524 (HoR kills the linked pair); the opponent's gold deficit is already visible at200–400. In the Willow game HoR kills that pair earlier469 and again785. Neither team-A roster suffers a death in either game. Consequently extra successful combat or death prevention is not the demonstrated explanation for the early economic divergence. Changed live interactions, turn order, camp ownership and self-directed opposing routes can all affect the subsequent economy. Actor own-view/claims would be needed to distinguish those causes.

## Recommendation

The initial cell supports the fourth damage role as a **focused-clear plus payout-allocation** hypothesis, with conversion concentration and opposing work distribution as material downstream effects. It does not support forcing Willow into camp fire, assigning future healing value, or globally lowering bank thresholds. A Willow allocation experiment would need to preserve safe service while reproducing some useful mixed-camp completion/ownership; simply counting additional heals cannot recover the shown gold transfers.

For later own-view nomination, group6 first completion/ownership at old63–69 versus Willow107–115 is the earliest clean window. The old240–286 crew is the stronger Vesper reward-sharing witness, but it is too long for the next short export: use its final clear/arrival274–286 only if the control panel makes that ownership question the priority. No new export is requested now. Known native actions and payouts establish the chronology; they do not establish why each actor selected its claim or whether another holder was safely available. Keep the larger paired control panel ahead of a new allocation implementation.

## Early Willow/Prism service check,1–115

Willow is productively engaged, not simply idle: actual attacks initially hit group22's Elk/resources, then group6 from48–61 and90–107. These actions identify work groups, not the unexported memory/comms claim. She casts six real heals totaling2120, all to Marcella:46(320),54/88/96/104/112(360 each). Those casts prove the recipient was visible/eligible at that moment. They establish genuine early service, without showing how much clear time or a recovery trip it saved. There is no Prism heal before115.

Prism does suffer a recovery interruption: HP falls500→420→340→260 at56–59, reaches240 at60–66, then recall completes67. His first subsequent camp attack is83, and group6 only clears107. Willow also takes substantial camp damage, falling640→160 during57–63 and recalling home68. She cannot heal herself. This was not a healthy available healer ignoring an adjacent critically injured partner.

At the recorded end-round checkpoints where Prism is missing at least216HP (57–66), their Chebyshev separation is7,7,7,8,8,10,11,11,11,11; Willow's heal cooldown starts4,3,2,1,0 and remains0. The first injury window is on opposite sides of group6: Prism57,11 versus Willow64,8, later farther apart. Even geometry supplies no current or one-step range4 heal at these checkpoints; fresh action-point vision, terrain and strict safety would impose further constraints. Before that, Prism has only100–120 missingHP at46–55, then200 at56; after returning he has only80 missingHP at100/107. End-round coordinates do not recover turn-local allied visibility or prove every earlier repositioning choice. A hypothetical anticipatory flank change is not a demonstrated legal missed heal, and no station-safety relaxation follows from it.

This narrows the next coordination question to whether a safe earlier common work position could avoid the split/recovery, while preserving the **already real Marcella service** and Willow's own survival. That requires an actor-view/branch witness before code. Vendetta's relevant snowball mechanism is kill-reset, not area damage. The wider initial52-game panel favors Willow32 wins versus teacher control25 (4c4 gets31); this single BigWorld mechanism does not justify a blanket old-draft fallback.

### Existing Prism coordination gates and a possible navigation arm

Current `local_support:4873–4935` requires a living visible mate, a fresh `visible_record`, no kept recall/tribute/teleport, actual heal readiness, worthwhile current injury, strict safe Willow position, and enough saved recovery travel to justify detour/wait. Prism then selects only adjacent safe tiles in actual heal range/LOS, owns a bounded four-turn recovery, and rechecks actual health/readiness. This already handles nearby real recovery. It does not proactively choose a farm flank while healthy or use an unseen healer as a navigation preference.

There is **no existing fresh allied-location report** to use outside vision. `comms.cpp:12–24,211–236` carries enemy sightings, bags, camp respawns, claims, and the alternating one-bit support intent plus two-bit epoch. The sighting sender enumerates `world.enemies`; `World::note_sighting:1325` indexes enemies. AVAILABLE therefore supplies neither Willow coordinates nor a work endpoint. An unseen Willow belief can only provide a last personal sighting/inferred position, not newly reported location. Combining a fresh AVAILABLE bit with an old location does not refresh that location. Publishing a service claim as though it were ordinary farm output would also corrupt crew valuation; do not smuggle a healer promise into a damage claim.

Farm has no general productive-station scorer: the in-range attack/stay paths return before navigation (`1878,2424–2438`). Otherwise it routes to a union of attack goals; existing `Pathing::route:485` and `closer_neighbours:388` use `aim` only to order equally short first steps. A narrow new **navigation-value-only** arm could prefer fresh personally seen Willow among equal original route first steps, with unchanged goals, guard, camp/pack/enemy safety and current output, no waiting or recovery ownership. It must be restricted to the actual normal movement branch and retain original spell-clear/cast/stay behavior. Equal distance to a union of goals alone does not prove equal future member/spell output. If strict equality of output cannot be certified cheaply for that branch, do not claim it; limit the first experiment to no-current-output approach turns and measure subsequent clear time. A fresh nonvisible own sighting could be used only with an explicit short age/source bound as uncertain navigation value, without relaxing heal eligibility or HP admission. Fresh *communicated* navigation would require a separately designed location/work-endpoint protocol; current bits do not supply it.

For this specific split, Prism actually walks continuously from65,7 at40 through64,8;63,9;62,9;61,9;60,9;59,9;58,10;57,11 to56,12 at49, with no attack/cast during40–49. That does not prove group6 was its selected farm job: it could be another group's transit followed by passing work. By57 the healer gap is already beyond one-step recovery. The indispensable short branch witness is therefore the first route choice around41–46: selected group, movement branch, original goals/current membership, equal-first-step count/order, Willow `visible/pos_source/pos_round`, existing support availability and strict safety/output for any alternate. Do not spend the next experiment merely rechecking heal eligibility at57–66; the geometric failure there is already established. No new trace/export or implementation is requested in this review.
