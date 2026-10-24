# Incoming losses: three actor-own windows

2026-10-24 UTC, Astra. **The windows distinguish an economic occupancy/combat mismatch, a failed disengagement with a support-range gap, and support followed by camp/pursuit attrition. They do not establish opponent adaptation or certify a winning escape.** One narrow alternative is certified: Fracture648 can preserve an existing recall instead of canceling and restarting without another action. That improves channel progress, not demonstrated survival.

Read the Cambridge Battlecode rules and `gold-capture-decision-review-20261024-v1.md`. The latter maps current Astraeus source only. All public submission/source/build/fuel identities remain unknown; no branch, claim, remembered threat, price or C++ state is attributed to these replays. This review only reads exported JSON, exporter semantics and existing summaries. No engine, extra export, build, script or EXPERIMENTS edit.

## Evidence and interpretation limits

Paths are beneath `replays/incoming-loss-followup-20261024-v1/metadata/`. All hashes independently verified; all33 turns end normally (`end_turn`), with no rollover/error in these windows.

| Actor/window | Relative export | SHA-256 |
|---|---|---|
| Gold Rush A/Vesper1,10–24 | `public-source-unverified-goldrush-10-24-v1/actor-windows-v4/goldrush-actor1-r10-24.json` | `230837ef89c25e9eea5b378957e11755c00c15e6819449e7237eb0756a651a55` |
| Starvation A/Prism0,445–453 | `public-source-unverified-windows-v3/actor-windows-v1/starvation-actor0-r445-453.json` | `90eb4c1f33ec599bf8f334410e9c9a93de6a118ab4df39ef2d29df42a16794ed` |
| Fracture B/Willow8,642–650 | `public-source-unverified-windows-v3/actor-windows-v1/fracture-actor8-r642-650.json` | `fc5b6523ac79fee4f2df732c96b6fef3497ca69536179c02e4751db63af513f3` |

Positions below are **raw map coordinates**. Exported Fracture camp/terrain positions use rotated own-frame coordinates; they must not be compared directly to raw champion/action coordinates. Turn observations precede that actor's ordered actions. Basic attack targets are omitted by this exporter; all selected-action snapshot arrays are empty. Health changes constrain, but do not identify, every omitted hit. `static_map_only` combines no dynamic camp record/visibility, so it does not itself certify a visible cleared tile. Native `can_move`, blocked boards, full tile visibility and private memory are absent. Actual moves certify those actual moves only. Channeling can suppress the initial attack-ready flag; subsequent successful actions after cancellation establish availability at execution.

Tables list all actions in order. `C` cancels a channel; `R` starts recall; `B` is a basic attack with target unspecified; `P(n)` sets next-round priority. Cooldowns are the two displayed ability-slot cooldowns at observation.

## Gold Rush: clearing, allied ownership, then trading beside the enemy holder

Vesper has1000HP,55Strength,100Focus, no items and zero gold through the beginning of19. No enemy is visible10–15. HoR2 is visible on group1's `(13,13)` tile12–19. The existing global summary attributes the group1 final clear to Vesper13 and payout to HoR19; this is compatible with remote clearing while an ally already occupies the group. Vesper is not an established holder in this window, and claim/handoff prerequisites are unknown.

| Round | Start position / HP / cooldowns | Ordered actions |
|---|---|---|
| 10 | `(12,9)` /1000 /0,7 | C → B → reset → B → R |
| 11 | `(12,9)` /1000 /7,6 | C → move `(13,10)` → R |
| 12 | `(13,10)` /1000 /6,5 | C → B → R |
| 13 | `(13,10)` /1000 /5,4 | C → B → R |
| 14 | `(13,10)` /1000 /4,3 | C → move `(14,11)` → R |
| 15 | `(14,11)` /1000 /3,2 | C → move `(14,12)` → R |
| 16 | `(14,12)` /1000 /2,1 | C → move `(15,13)` → R |
| 17 | `(15,13)` /1000 /1,0 | C → B → R |
| 18 | `(15,13)` /1000 /0,0 | C → dash `(17,15)` → B → R → P(14) |
| 19 | `(17,15)` /1000 /0,7 | C → B → reset → B → R |
| 20 | `(17,15)` /835 /7,6 | B → R → P(1) |
| 21 | `(17,15)` /780 /6,5 | B → R → P(-7) |
| 22 | `(17,15)` /725 /5,4 | B → R |
| 23 | `(17,15)` /670 /4,3 | B → R → P(-15) |
| 24 | `(17,15)` /615 /3,2 | B → R |

At17 Vesper sees group2's camp5 at `(17,16)`,40HP, awake; his55Strength can kill it, and the global summary records his final group2 clear that round. Enemy Vesper4 is already visible16–17 at `(16,19)`, then18 at `(17,18)`, a group2 tile. Our dash lands at `(17,15)`, outside group2; its nearest member tile is `(17,16)`. Enemy Vesper stays visibly at `(17,18)` throughout18–24. Enemy HP at19–24 is945,835,780,725,670,615, while our HP becomes equal from20 onward. The known enemy has55Strength,100Focus and both slots ready at18. This is a prolonged nonlethal exchange while only the enemy occupies the gold group; the global summary supplies his payout23. It is not150 rounds of opening inactivity, and the repeated recalls here do not produce an observed spawn departure.

**Candidate, not certified better sequence:** value locally known cleared-group contest/occupancy when choosing a ranged combat position or deciding whether to spend the walk on a nonlethal basic. A direct18 dash to `(17,16)` is **illegal by range**: it is three king steps from `(15,13)`, while dash permits at most two. The geometrically relevant alternative is the actual dash to `(17,15)` followed by a walk onto `(17,16)` instead of the basic, or an earlier approach. Static terrain around that route has no wall/hole/altar obstruction, and the visible enemy at `(17,18)` could still basic from either tile. But the export does not certify free landing/step state, post-dash native movement allowance or the complete threat change. Camp deaths marked only static and absent enemy readiness/turn-order details prevent declaring a safe capture sequence. Contest would deny progress while occupied; it would not immediately give us income. Test a narrowly legal, similarly exposed occupancy tie-break in a source-known fixture before changing pickup/contest priority. Do not force Vesper to displace HoR or raise a blanket gold multiplier.

## Starvation: attack commitment, chase, and an unavailable heal rendezvous

Prism carries74 gems throughout, with1060maxHP,35Strength,191Focus, Jungle Health emblem and one Durability Health shard. No dynamic camp is known in the local export. Vendetta9 is visible and adjacent at `(37,6)` while Prism remains `(38,5)`445–448. The enemy has82Strength,1500maxHP and a ready dash by447; it is not a basic-kill target. Enemy Vesper6 is visible at131HP445,96HP thereafter, moving away; missing attack targets prevent attributing every basic.

| Round | Start position / HP / cooldowns | Ordered actions |
|---|---|---|
| 445 | `(38,5)` /677 /6,5 | B → R |
| 446 | `(38,5)` /595 /5,4 | B → R |
| 447 | `(38,5)` /513 /4,3 | B → R |
| 448 | `(38,5)` /431 /3,2 | move `(37,4)` → R → P(16) |
| 449 | `(37,4)` /267 /2,1 | move `(36,3)` → R |
| 450 | `(36,3)` /185 /1,0 | move `(35,2)` → R → P(17) |
| 451 | `(35,2)` /103 /0,0 | CC `(36,3)` → B → R → P(20) |
| 452 | `(35,2)` /103 /7,0 | C → move `(34,1)` → R → P(15) |
| 453 | `(34,1)` /21 /6,0 | move `(33,0)` → R → P(23) |

The three early basics spend the ranged walk while HP falls by82 per round. Later retreat does not break contact: Vendetta follows to `(38,5)`, `(37,4)`, `(36,3)` and `(35,2)`. Its available reset at448 coincides with the164HP loss before449. The451 CC is explicitly targeted at Vendetta; next observation shows stun and HP917.5, down321.5 =191×1.5+35, while Prism retains103HP. The CC buys one interval, then pursuit resumes. CC excludes walking, so “stun and walk451” is not a legal alternative. The existing summary records the74-gem death after the453 move.

Willow3 is visible at `(38,9)`445–447, exactly heal range4, but heal cooldowns are3,2,1. At448 she is ready at `(38,10)`, range5; later the separation grows. This is a concrete readiness/range mismatch, **not proof she ignored a ready in-range heal**. It also does not prove she could safely move closer, saw the same threats, or followed any particular private claim. Specifically: could the445–447 attack/hold policy be anticipating support that does not remain available? That is a hypothesis, not live-code attribution. A future Willow own-view would distinguish failed rendezvous from legitimate support retreat; Prism's perspective cannot settle it. No certified safe alternative route is recovered. The source-known question is earlier disengagement/service rendezvous before the basic spends movement, preserving a profitable kill when actually available. Merely adding Focus or permanent follow does not resolve this witness.

## Fracture: a real heal followed by mixed exposure during retreat

Willow has950maxHP,85Strength,120Focus,22 gems,8 gold, Durability Health/Treasure Strength/Jungle Strength emblems. Enemy Vesper2 is visible in every observation, with255Strength,180Focus and about2800–3000HP; dash cooldown is0 throughout. Marcella7 is the only visible allied service target642–648. Our Prism is not visible. Willow never attacks during these nine turns.

| Round | Start position / HP / heal cooldown | Ordered actions |
|---|---|---|
| 642 | `(23,38)` /458.6 /1 | C → move `(22,38)` → R |
| 643 | `(22,38)` /458.6 /0 | C → heal `(21,39)` → move `(22,39)` → R |
| 644 | `(22,39)` /345.2 /7 | move `(21,40)` → R → P(-57) |
| 645 | `(21,40)` /269.6 /6 | move `(20,41)` → R |
| 646 | `(20,41)` /231.8 /5 | move `(20,42)` → R |
| 647 | `(20,42)` /194.0 /4 | move `(19,41)` → R → P(10630) |
| 648 | `(19,41)` /194.0 /3 | C → R |
| 649 | `(19,41)` /194.0 /2 | C → move `(18,40)` → ward → R |
| 650 | `(18,40)` /194.0 /1 | C → move `(17,39)` → R |

The643 heal is real service: Marcella is290/1400 at `(21,39)`, and next appears650HP. Willow's base360 heal fits exactly. The heal does not consume the observed subsequent move. Willow cannot self-heal; more output to Marcella would not directly restore Willow's health. Awake group15 Elks are known nearby, including Elk49 at raw `(24,41)`,975HP, and Elk47 at `(25,41)`,2400HP. The successive113.4/75.6/37.8/37.8 losses are consistent with3/2/1/1 Elk hits after Jungle×Durability mitigation (60×0.7×0.9=37.8), but the export alone does not identify every incoming action. Enemy Vesper advances from `(25,32)`642 to `(20,37)`647, then remains there in the turn observations. The final650 movement is toward `(17,39)`, where the existing summary records the Vesper kill. No counterfactual escape is certified by these snapshots.

**Certified narrow alternative at648:** the initial recall timer is4; the only actions are cancel and restart. Keeping that channel preserves the same position, health and unused actions while advancing recall one additional turn. This is a local progress defect with no invented movement legality. It is not proof of a save: the actual649/650 movements cancel again, and an uninterrupted recall from647 would still need its full duration. Inspect current `try_keep_recall` and cancellation scheduling before implementation, then establish in a source-known diagnostic why a no-action turn restarts an otherwise preservable recall, without forcing channels through necessary retreat actions.

## Consequences

Prioritize the Gold Rush occupancy/combat nomination for a bounded source-known legality check, then the exact Fracture648 recall-progress case. Starvation nominates earlier service/escape timing but lacks a certified safe step. Preserve the distinction between observed exposure and a usable alternative. None of these windows identifies a new enemy policy or controls source changes; none supports blanket Focus, Health, permanent follow, earlier banking or map-name gates. A candidate is falsified if it does not activate in its exact intended state, cannot legally execute the alternative, worsens native survival/production, or merely shifts reward ownership without improving team conversion.
