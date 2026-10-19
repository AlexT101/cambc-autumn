# Why hecate loses to Intercontinental Fish

Analysis of 2026-10-19, from our ladder scrims against Intercontinental Fish (#1 on the ladder) in the 18 hours to 19:56 UTC.

## Data

- **Sample.** 18 groups (90 games, 60 distinct) from six `scrim_ladder.py` runs: `replays/scrims/20261018-231915` and `replays/scrims/20261019-{074736,143241,152704,153559,154258}`. They cover submissions 24-29 ([SUBMISSIONS.md](SUBMISSIONS.md)); submission 30 has not been scrimmed against Fish.
- **Record.** We went **9-81**. In the same runs we went roughly level with Mite and Sneaky Bush Campers, and 5-7 of 15 against the rest.
- **Sides.** We are always team A (the requester). The scrim runs share map seeds, so many games are byte-identical across runs.
- **No traces.** Ladder builds are release builds, so `team-a.stdout` and `.debug` are empty. Every instance below was read from the replay events and rounds. Code links come from reading the code, not from traces.
- **Draft.** Fish drafts what we draft: Stellar, Ren, Cassi & Issac, Ryth, Varg (fewer picks on maps with fewer). On contest and stampede it takes Stellar, Tavi, Prism, Cassi & Issac, Ren. **The gap is play and itemisation, not the draft.**
- **Reproducing.** Extract with `node tools/replay/extract.mjs <the run dirs>`. Game ids below are `replays/.analysis/<dir>` prefixes.

## Where the gems go (60 distinct games)

| | Us | Fish |
|---|---|---|
| Gems from captures | 40.0k | 57.0k |
| Captures | 1,300 | 1,852 |
| Carried gems lost on death | 7.6k | 3.3k |
| Deaths (contest alone: 47-70 of ours a game) | 840 | 405 |
| Deaths from ≥90% hp within one round | 69 | 9 |
| Deaths carrying 40+ gems | 62 | 34 |
| Groups mostly damaged by one side, captured by the other | 33 (2.1k gems) | 70 (4.35k gems) |
| Dead share of champion-rounds | 19% | 11% |
| Mean gems per tribute (most maps) | ~30-40 | ~45-60 |

**Captures by walking-distance side.** A group counts as one side's when it is at least 3 steps nearer that spawn. `groups[].side` in the extracted maps uses Chebyshev distance, which mislabels swirl and contest.

| Groups | Fish | Us |
|---|---|---|
| Fish's half | 33.1k (their own) | 1.06k |
| Our half | 3.9k | 27.7k (our own) |
| Middle (central camps, rushbait, stampede, Monoliths) | 20.0k | 11.2k |
| Of which contest's Monoliths | 6.0k | 0.8k |

- **Their own half.** Fish takes about 20% more from its own half than we take from ours: wolf groups 17.2k vs 14.5k, elk groups 17.1k vs 14.0k.
- **The middle.** Fish wins it by about 9k.
- **Raids on our half** are small, about 2.9k net. In 82 of Fish's 85 gem raids there we could see the capturer, and we contested the tile only twice.

**Fights.**
- Engagements we start: 171 kills for us, 279 for Fish. Engagements Fish starts: 93 for us, 350 for Fish.
- Below 25% hp, Fish champions survive 70% of the time, ours 51%.
- 501 of our 654 deaths to champions are in our own half; only 92 of Fish's 294 are in theirs.

**Gold and shards** (excluding contest):
- Lifetime gold: Fish +17% at r300 and +31% at r500.
- Shards bought over 50 games (not contest or stampede): Fish about 6.9k, us about 5.0k.

| Shards bought | Us | Fish |
|---|---|---|
| Stellar, Power Focus | 772 | 1,969 |
| Ren, Power Focus | 437 | 1,490 |
| Ren, Durability Health | 461 | 230 |
| Jungle (any) | ~1,050 | 0 |
| Home / Bruiser Health | 0 | 491 / 732 |

## Causes, ranked by cost

### 1. Builds: Fish stacks Focus on its spellcasters and one-shots ours

- **Builds by champion.** Fish puts its gold into Focus on Stellar and Ren, and Health (Bruiser, Home, Durability) on the rest. We spread ours across Jungle, Power and Durability.
- **Effect at r300.** Our Stellar averages 959 max hp and 221 Focus against 1,315 and 280. Our Stellar and Cassi often stay at their base 700-750 hp all game.
- **Who kills us.** Fish's Stellar landed the killing blow in 240 of our 629 deaths to champions. Of our 69 deaths from ≥90% hp in one round, Stellar did 34 and Tavi 27. In 31 of those 69 the killer was not seen in the 3 rounds before, and 23 were cast from a bush.
- **Code.** [bot.cpp:787](../bots/hecate/src/bot.cpp#L787) `best_emblem` scores emblems only by camp-clearing upkeep (`upkeep_cost`, `siege_upkeep`). Fight value, burst survival, Home and Bruiser are never considered. On Monolith-only maps the Monolith's 200-damage hits make Durability Health win even for Stellar.

**Instances**
- **Fragment `033746ff` r555-557.** Fish's Stellar (Focus ~800) sits unseen in the bush at (14,20)-(14,21). One area spell kills our full-hp Cassi; the next damage spell kills our full-hp Stellar.
- **Contest `a0bb704c` r1136-1174.** Fish's Tavi (Focus ~1,580) kills Cassi and Stellar with one nuke each, and Varg with two.

### 2. We give up capture tiles and camps we're standing next to

- **Stuck on the tile.** A champion holding or contesting a capture cannot walk or dash ([bot.cpp:2860](../bots/hecate/src/bot.cpp#L2860) sets `intent.anchored`; [plan.cpp:264](../bots/hecate/src/plan.cpp#L264) then disables both). `hold_capture` only attacks camps. It cannot step to another tile of the same group to hit the enemy contesting it.
- **Everyone else leaves.** `capture_taken` ([bot.cpp:2267](../bots/hecate/src/bot.cpp#L2267)) counts allies nearer the group, `big_holders = 3`. Once that is met, `kite()` returns false and the rest go to `farm()`, even with enemies 1-3 tiles off the tiles.
- **We retreat on our own half.** `home_retreat_ratio = 2` ([params.h:43](../bots/hecate/src/params.h#L43), applied in pack_boxes at [bot.cpp:1661](../bots/hecate/src/bot.cpp#L1661) on own ground). Through `want_home` it overrides holding a capture; only paying_soon is exempt, which needs no enemy within 3. Elsewhere `retreat_ratio = 100`, so a healthy champion away from home never yields to a pack.
- **Contesting is passive.** `contest_capture` ([bot.cpp:2618](../bots/hecate/src/bot.cpp#L2618)) runs after want_home and chase. It only steps toward a free tile, never attacks a weak holder, and fails on single-tile groups.

**Instances**
- **Stampede `ef4f8d21` r133-144.** Varg stands on (56,23) for 11 rounds with 490-670 hp. Fish's Prism (290-485 hp) is 2 tiles away, with free tiles next to it. Varg only shields, then leaves, and Fish captures 360 gems and 960 gold, which decides the game.
  - In the game we won (`11ab8b3f`), Varg happened to stand one tile *off* the group. He stepped in, hit Prism, and Stellar killed it.
- **Stampede `768ee446` r250-262.** Six of ours at full hp against four of theirs. Stellar, Ryth and Prism take the tiles; Ren, Cassi and Issac walk south. Ryth and Stellar die, and Fish captures 360. The same split happened at r116-119 in that game, and at r271-276 in `ef4f`.
- **Eight `32798dcef0` r453-466.** We did all 8,200 damage to the 132-gem group. Varg holds it, then walks off with 3 hold rounds left as Fish's Stellar and Cassi approach. A lone Fish Cassi takes 132 gems and 515 gold while Varg, Ryth, Issac and Cassi watch from 5-8 tiles.
- **Fragment `47ec8bbb` r612-620.** A Fish Ren on 99 hp holds our ElkWolf for 7 rounds. Our Cassi (701 hp) sees him every round from 4 tiles and neither attacks nor steps on the free tile.
- **Fragment `7195e2d9` r375-396.** We did all 3,750 damage to our ElkWolf. Stellar clears it but never steps on a tile once Fish appears at 6-7 tiles. Fish's Ren takes the 58 gems while our Ren, Cassi and Issac stand 3-4 tiles off.

### 3. Carriers fight, shop and walk alone through Fish

- **Fighting while carrying.** In 29 of our 46 deaths to a champion while carrying 40+, we had dealt champion damage in the 3 rounds before: we were fighting, not fleeing.
- **Code.** `carry_bag` tries `chase()` before banking when a tribute isn't safe ([bot.cpp:2753](../bots/hecate/src/bot.cpp#L2753)). `capture_recall` ([bot.cpp:2142](../bots/hecate/src/bot.cpp#L2142)) recalls to shop whenever the capture's gold buys an emblem "bag and all", whatever the bag.

**Instances**
- **Eight `c0ca6d0b` r118-387.** Our Stellar captures 132 gems at r118 and walks alone to the only altar three times, into 4-6 waiting Fish champions. Each time it is cut to 187-300 hp and recalls. On the third walk it trades with Fish's Varg at about 300 hp and dies at r236; Fish takes the 132.
  - Our allies were at spawn or 6 tiles off. Fish banked its own 132 at r266 with all five escorting.
  - It happened again: 132 captured at r354, lost at r387 walking home on 15 hp. Our score never moved from 204 after r400.
- **Contest `cd7f9d6a`.** We capture a Monolith four times, each with one holder taking all 200 gems. All four carriers die (r699, r970, r1251, r1488), and **800 of Fish's 1000 points are our bags**.
  - r676: Stellar recalls, shops, then walks 20 tiles into five Fish and casts at them while carrying.
  - r1473: Varg starts a 20-turn tribute with three Fish within 9.
- **Collision `bff622f8` r613-625.** Stellar (44 gems) keeps walking to the central altar after seeing Fish's Ren at 5 tiles and dies. Our Ren (80 gems) then chases a 491-hp Fish Ren into Stellar and Cassi and dies.
- **Stampede `ef4f8d21` r516-526.** Stellar, Cassi and Issac recall carrying 120 each and walk out unescorted through the bush passage at x14-16, y9-11. Fish's Prism has waited in our half since r511. Cassi and Issac die with 240, which Fish tributes for its 1140. Our healthy Ren, Ryth and Varg were 30 tiles away.

### 4. We farm less efficiently even when nobody fights

- **Nobody gathers on mid-sized gem groups.**
  - `big_gems = 150` ([params.h:76](../bots/hecate/src/params.h#L76)) keeps 72-120-gem elk groups out of team sieges.
  - farm() offers a partner only to an unclaimed ally within 12 tiles, and helps only an ally in sight within 8 steps.
  - With no affordable group it falls back to the best risky group by gem rate.
  - So each body walks off alone. Fish puts 3.2-4.3 attackers on elk groups and one on wolves; we put about 2 on each.
- **Long solo spell-casting from range.** A body that can't afford to basic-attack casts from outside the camp's reach ([bot.cpp:1378](../bots/hecate/src/bot.cpp#L1378)): one cast per 8 rounds, idle in between. Across lanes, expanse, ambush and monolith we spent 501 champion-rounds this way, Fish 42.
- **Recall pricing leaves out the walk back.** `capture_recall` ([bot.cpp:2151](../bots/hecate/src/bot.cpp#L2151)) compares `lands - payout + from_spawn` against the walk to an altar. It never counts the walk from spawn back to the farm, which is longer than the walk from the altar.
  - On lanes that is 32-35 steps against 6-9, so a recall priced at about 1 round costs about 22.
  - The shopping branch fires even when only one shard is missing.

**Instances**
- **Ambush `6cf8f2e7`, lost 716-1000.**
  - Issac, Ren, Stellar and Ryth all go to the farthest gem group (EEGG at (56,34): 5,800 hp, 64 steps), arriving one at a time between r41 and r70. Issac dies to an elk at r53, and Cassi dies with him. Varg spends r1-106 on gold-only camps (245 gold).
  - Our first gem capture is at r175; Fish has 238 banked by r200 to our 0. Fish had all six bodies on the nearer EGGW (53 steps) by r42-56.
  - Our Ren earned 0 gems and 0 gold in 499 rounds, walking out and recalling four times. 17 of our 20 trips home were empty-handed.
- **Lanes `7d6031ce`, lost 888-1022.**
  - Every one of ours goes home after one capture around r55-82, and we capture nothing from r69 to r114 while Fish chains 2-3 captures per trip. By r100 Fish has captured 234 gems to our 124, about the final gap.
  - 21 of our 25 recalls timed to a payout carried 36 gems or fewer, many at 85%+ hp (Cassi r348: full hp, 22 gems, bought one shard). The extra walking cost about 108 gems.
- **Expanse `61b7edd8`, lost 994-1004.**
  - Cassi spends r336-470 casting alone at EEGG (71,4), idle for 91 of those rounds, and ends the game with 22 gems against Fish Cassi's 182. Stellar does the same at (8,60) in r74-164.
  - Meanwhile wolves 7 and 17 steps from our spawn sat alive and unhit for 310 and 350 rounds; Fish left its mirror camps alone for 32 and 85.
  - At r543 we needed only 6 gems, but Stellar walked for 57 rounds without attacking, and Fish's winning tributes started first.
- **Monolith `c043d3ae`** is not a farming loss. We captured more (1062 vs 1008) but lost 7 bodies to 2, with 318 champion-rounds dead after r300 to Fish's 96.

### 5. Contest and stampede

- **Contest: 0-1000 every game, 47-70 deaths.**
  - **The opener decides it.** In 7 of 10 contest scrims we die first (r35-46) and finish with 0 gems; in the 3 where Fish dies first we collect 600-1,200.
  - **The latest version (`a0bb704c` r30-52) splits up.** Ren goes to a single 35-gold cluster at (19,3) while melee Ryth walks alone into six Fish at (26,22), is stunned four times and dies at r42. After that we trickle back one at a time from spawn.
  - **Results.** We are dead 46% of champion-rounds; 39 of 57 deaths were outnumbered within 7 tiles, and 35 came within 60 rounds of the last respawn or death. The team earned 1,590 gold to Fish's ~13k.
  - **How Fish takes Monoliths.** One ranged champion chips them with spells from range 4-5, outside the Monolith's reach of 3, which works because camps never regenerate. Then 4-5 finish one in 10-25 rounds. Fish bought 325 Power Focus shards; we bought 3.
  - **Code.** `siege_ready` ([bot.cpp:2354](../bots/hecate/src/bot.cpp#L2354)) never passes with half the team dead, and the range-4 cast branch only runs inside a siege. We left a 7.6k-hp Monolith alone for 170 rounds before Fish's Stellar finished it solo.
  - **Fish's Ren.** At Focus 480 every hit on him reflects 96: 8.4k reflected damage over `a0bb`, and he went 17-0. We still fight him in melee 1v1 (r1272-1279).
- **Stampede: whoever wins the first fight over the shared group's tiles (r116-150) gets 360 gems and 960 gold and the game.**
  - That fight is lost by cause 2: anchoring and splitting off.
  - **Early retreats.** Our recalls in these fights start at 215-385 hp, Fish's at 35-160. `want_home`'s 35% `low` test spares a champion holding a capture but not one contesting it. In `768ee` we left Prism on 60 hp and Ren on 35 alive.
  - **Centre gold.** Fish parks Issac on the two axis gold camps all game (980-1,260 gold); we captured neither in any game.
  - **Versions.** `768ee` was submission 26's spellcaster draft, already reverted. `ef4f` was submission 24, which also ran out of fuel inside the deciding fight (since fixed).

## What to try, in order

1. **Let a holder move within the group.** A champion holding or contesting a capture may move to another tile of the same group to attack an enemy contesting it (plan.cpp:264 / bot.cpp:2860).
2. **Keep the team together near enemies.** `capture_taken` should keep every nearby ally while enemies are within about 4 tiles of the group.
3. **Value fights in builds.** `best_emblem` should add fight value: Focus on Stellar, Cassi, Ren and Tavi, and health where we are one-shot. Consider Home for anyone who recalls a lot.
4. **Fix recall pricing.** Charge recalls for the walk back from spawn to the next farm. Don't recall a 100+ bag to shop. Escort or hold big bags rather than walking them alone.
5. **Crew mid-sized gem groups.** Lower `big_gems`, or form crews for elk groups too big to solo. Avoid long solo range-casting while nearby small camps sit idle.
6. **Contest.** Open as one group with no single-cluster detours before about r80. Chip Monoliths with spells from range 4. Split Monolith bags across holders.

Judge each with the usual A/B (ladder + `--gen` + `--central`, both sides). Our local bots don't burst or contest the way Fish does, so confirm on ladder scrims too.
