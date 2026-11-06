# Why ocean v78 loses to Fish and Mite (core set, 2026-11-06)

This note is analysis only: no bot was changed.

The data is the pinned scrim set: ocean v78 ("HER", `bots/ocean` = `variants/oc-retest-clean`) against Intercontinental Fish (01a1af35) and Mite (01a1af36), on the 40 core maps with both sides played.
- Fish: 40-40.
- Mite: 47-33.

The replays were extracted with `tools/replay/extract.mjs` into the session scratchpad. The scripts are in `.../scratchpad/losses/scripts/`:
- `metrics.py` and `agg.py`: economy, deaths, engagements, captures, altars, timing and fuel;
- `deaths.py` and `death_act.py`: the context of each death;
- `react.py`: back-to-back turns;
- `eng.py`: initiation;
- `spread.py`: spacing;
- `locks.py`: lock share;
- `marc*.py` and `lethal.py`: Fish's Marcella;
- `chan.py`: big tribute channels.

Notation:
- "us/op" means ocean / opponent.
- "Losses" and "wins" are ocean's.
- A game id is `map-side`, where side `a` means ocean is team A.

## Summary

Against Fish we lose fights, not the economy.
- Fish's farm is no better than ours until fights start feeding it. Its tributes on gap > 4 maps (separate altars) are the one exception, covered in failure mode 6.
- In our losses we die 12.3 times a game against Fish's 5.1, and we drop about 300 gems a game in bags.
- Most of those deaths have two causes:
  1. Fish's Marcella, a Focus-stacked range-4 nuke: we keep ending turns inside its range while it is ready.
  2. Our own initiations into packs that are locally stronger.
- On top of that we have two altar failures:
  - We let enemy tribute channels of hundreds of gems run to completion while we watch and carry an altar lock. 03homonoliths-a is the clearest case.
  - We lose the lock war on shared altars.

Fuel is not a main cause. The draft matters only at the margin.

Mite does not lock and is as spread out as we are. We lose to it mainly by feeding huge Vesper bags, and by the same channel-watching.

## Results by slice (Fish)

| slice | games | W | deaths us/op | gems lost in bags us/op |
|---|---|---|---|---|
| all losses | 40 | 0 | 12.3 / 5.1 | 299 / 135 |
| all wins | 40 | 40 | 4.4 / 9.4 | |
| multi-altar | 52 | 22 | | |
| 70x70 and bigger | 16 | 6 | | |
| altar gap > 4 (separate altars) | 20 | 7 | 7.2 / 3.6 in losses | |

Lost both ways to both teams: 00lanes, 00quarry, 02the_pack.

## Failure modes

### 1. Feeding: deaths with big bags (largest driver)

Against Fish:
- In our losses we die 12.3 times a game against Fish's 5.1. In our wins the figures are 4.4 against 9.4.
- In losses we lost 11,953 gems in bags (about 300 a game, 24 a death). Fish lost 5,393 in the same games.
- 62% of the gems we lost were in bags of 100 or more.
- By champion:
  - Prism lost 5,445 gems over 63 deaths, 86 gems a death. The Prism hoard is the single biggest leak.
  - Vesper lost 1,584.
  - Varg lost 1,432 in 8 deaths.

Against Mite, our Vesper alone fed 9,235 gems. 01boss_battle had single deaths with bags of 3,056 and 2,618, and 81% of the gems lost to Mite were in bags of 100 or more.

Early game against Fish (losses):

| | r100 | r200 |
|---|---|---|
| deaths us/op | 0.55 / 0.17 | 1.27 / 0.57 |
| gold us/op | 384 / 473 | 828 / 1,056 |

Many of these early deaths are to Fish's opening pack, at own/enemy counts within 6 of 1/5, 2/5 and 2/6. Kill gold plus bags is the whole economic gap: by r400 Fish's gold lead in our losses comes from kills.

### 2. Fish's Marcella nuke: we stand in its range

In our losses, Fish's Marcella:
- averages 7.1 kills, 1.0 deaths and 3,487 gold a game (in our wins: 1.4 kills, 3.0 deaths);
- killed 171 of the 492 champions we lost: Cassi 46, Marcella 26, Issac 25;
- never died in 11 of 24 losses where she was drafted, against 7 of 28 wins.

How she kills:
- 139 of her 210 kills were a single slot-1 cast with no other damage that turn. Slot 1 is unit damage at 2x Focus, range 4.
- 83 of those kills were from distance 4, and 69 from distance 2.
- Her Focus has a median of 420 and reaches about 1,140 by r950 on 04sunburst. Her build is about 46 Focus shard-equivalents, against our Marcella's ~17 (Fish buys Focus emblems outright, per FISH_MODEL).
- 119 of the 139 victims had her in sight at the start of their last turn.

`lethal.py` counts round ends where one of our champions sat inside her lethal range (distance ≤ 4, HP ≤ 2x her Focus) with her cast ready:
- 298 such round ends in losses;
- 79% of them with her visible to that champion;
- 57% of those champions died within 2 rounds.

Fish's champions did the same against our Marcella only 49 times in all 80 games. Ocean treats an enemy at distance 4 as out of fight range, but this nuke kills from there.

### 3. Initiating fights we lose locally

Engagements are first champion damage between groups. In Fish losses:
- We initiated 560 engagements, giving K149 / D326.
- In 310 of them, our effective HP within 8 of the fight was below Fish's. Those went K69 / D219.
- Fish initiated 222 engagements in our losses, going K166 / D54 in its favour.
- Fish initiates only 27-28% of the fights in which its own champions die.
- In our wins, our initiations go K240 / D93.

This is not a vision gap: the share of enemies unseen at initiation is about 19% in both wins and losses. Ryth's initiations in losses went K11 / D41.

### 4. Big enemy channels completed under our eyes

`chan.py` looks at tribute channels of 100 gems or more that completed. The opponents completed 180 against us:
- the mean length was 17 rounds;
- 22 of them won the game;
- we saw 100 of them while they ran, and one of ours was within 8 of the altar for 103;
- in 172 of them at least one of our champions carried an altar lock.

That leaves 15 game-winning channels that we saw while carrying a lock. A lock placed within 2 of the altar, or a stun, cancels the channel. The worst cases:
- **03homonoliths-a (Fish), r609-729.** Fish's Vesper tributed 1,200 gems in a 120-round channel. We saw it for 80 rounds, our nearest champion was at distance 9-10, and all 4 of our living champions carried a lock. Before that, our Prism held a 600-gem bag from its r280 capture until Fish's Vesper killed it at r604: that bag was the 1,200.
- **03homonoliths-b (Fish).** We cancelled the channel with locks at r632 and r696, then lost sight. A 100-round channel from r758 completed.
- 00reverse_spiral-a (Fish), r1409-1475: 660 gems, seen for 23 rounds, nearest 9, 4 lock carriers.
- 02treasure_box-a (Mite), r728-774: 675 gems, seen for 28 rounds, nearest 6.
- 02the_pond-a (Mite), r1563-1616: 782 gems, nearest 18.
- 01boss_battle-a/b (Mite): 400 and 200 gems, nearest 6 and 3.
- 02guardians-a (Mite): 452 gems, nearest 3.
- 02harvest-a and 01starvation-a (Fish): 269 and 200 gems, nearest 3.

Why ocean does nothing about these:
- `economy/altar_guard.cc` runs only on maps with exactly one altar tile: `guarded_altar` returns -1 otherwise. Several maps have multiple altar tiles that form one site (within 3 of each other):
  - 00quarry, 03homonoliths and 04plaza (2 tiles each);
  - 03the_front (34 tiles);
  - 00great_wall (4 tiles in 2 sites).
- `bank.cc` and `fight.cc` cancel only a channel that is already in reach. Nothing walks a champion to a long enemy channel, even one that wins the game.

The opponents leave ours alone too (17 of our game-winning channels were seen by a lock carrier). But theirs are bigger, because our deaths fed the bags.

### 5. Losing the lock war on shared altars (Fish only; Mite never locks)

Fish buys a lock whenever the altar gap is 4 or less. These maps account for 60 games, of which we won 33.
- When a Fish lock sat on our nearest or shared altar for more than 60% of rounds, we went 1-9. The nine losses:

  | game | Fish lock share |
  |---|---|
  | 04sunburst-a | 83% |
  | 04sunburst-b | 65% |
  | 04wheel-a | 88% |
  | adgato-a | 94% |
  | 04bowls-a | 78% |
  | 04courtyard-a | 72% |
  | 01boss_battle-b | 72% |
  | 03ultrastarvation-b | 72% |
  | 00reverse_spiral-b | 60% |

- Fish's lock share is 23% in our wins and 45% in our losses. Ours is 62% and 40%.
- We lose 4-5 locks a game to Fish's attacks. We are slower to break Fish's locks (5 basic attacks) and to re-lock.

### 6. Separate-altar maps: Fish out-farms us

On gap > 4 maps we went 7-13 against Fish but beat Mite on most of them. The Fish losses were lanes, harvest, gem_fields, ambush_field, canyons, shrines and ambush-a.

| (our losses on these maps) | us | Fish |
|---|---|---|
| tributed gems by r400 | 270 | 400 |
| tributed gems by r600 | 448 | 701 |
| gems banked per tribute | 21 | 35 |
| camp damage | | about 12% higher |
| deaths | 7.2 | 3.6 |

Fish concentrates gold on one carry: its top earner takes 0.55-0.57 of the team's gold, against our 0.39-0.45. On 02the_pack:
- Fish's Vesper reached 135k damage to monsters;
- Fish's team gold was 10-12k against our 3-4k.

### 7. Spacing

Before r200, Fish's nearest ally is within 4 tiles in 77-80% of turns, against 63% for ours. On big maps after r200:

| | us | Fish |
|---|---|---|
| median distance to nearest ally | 8 | 4 |
| nearest ally within 4 | 33% of turns | 53% |
| nearest ally 10 or more away | 44% | 26% |

But deaths "alone against 2 or more" are 20-27% of deaths for both teams, in wins and losses alike. Spacing matters through failure mode 3 (we initiate without the bodies nearby), not as isolation in itself. Mite is as spread out as we are.

### 8. Back-to-back turns

- 36.8% of Fish's kills used a back-to-back pair (the killer's turn closing round R-1 directly followed by its turn opening round R). The figure for ours is 19-24%.
- Fish made 3,007 such same-champion pairs at round boundaries over the 80 games, against our 1,689.
- But the fish-bot round 1 transplanted Fish's priority encoding into astraeus, and it cost about 4 points there (research/fish-bot-2026-11-06/LOG.md). It only pays together with Fish's other choices.

### 9. The draft (marginal)

Against Fish, by our pick:

| our pick | record |
|---|---|
| Ryth | 7-13 |
| HoR | 13/34 |
| Vesper | 15/34 |
| Varg | 9/14 |
| Prism | 35/66 |

Against Mite, Ryth went 13-7. Fish has Marcella, who is stun-immune, in 52 of 80 games, and Ryth's value is its stuns. Fish's draft is a fixed per-map order, so it can be read off round 0.

### 10. Fuel (not a cause)

- Out-of-fuel turns run 1-3 per 1,000 turns: 3.1 a game in Fish big-map losses against 1.2 on small maps.
- Mean fuel a turn is about 56k on big maps and 45k on small ones.
- Outliers:
  - 04sunburst: 58 and 59;
  - 02the_pack: 35 and 26, and 75 against Mite;
  - adgato: 30-51;
  - 03the_front: 102, in a win.
- 03colosseum-a (Fish, a win) had 1,477 out-of-fuel turns: Ryth and Willow ran out on about every other turn. The game shows two problems:
  - We reached 996 tributed gems at r499 and then stalled to r1998 (final 1003-0), with Prism holding 146 gems beside the altar while Fish's 6-body pack waited about 6 tiles away. We needed only 4 more gems.
  - We had 1,328 capture resets on groups 25 and 23.
- This is a finishing bug and a fuel-loop bug, but it occurred in a win.

### The three maps lost both ways

- **00lanes** (gap > 4) and **02the_pack** (big): failure modes 6 and 1. Fish's carry funnel out-farms us, while we feed bags in fights we start (the_pack: Fish's gold is 10-12k against our 3-4k). Against Mite on 02the_pack-a, its 116-gem channel completed with us at distance 4.
- **00quarry** (2 adjacent altar tiles, one site): failure modes 4 and 5. altar_guard is off there, because the map has two tiles.

## Ranked candidate changes

The expected sizes are against Fish on the 80-game core set; 1 game is 1.25 points. Every change must also hold up in a local A/B (no regression against astraeus or panel members), because past Fish-style changes lost locally.

### 1. Deny winning or long enemy channels

When an enemy channel is visible and would win the game, or has a large bag and a long time left:
- send the nearest champion able to reach it in time to within 2 of the altar to place a lock, or within range to stun;
- treat altar tiles within 3 of each other as one site for altar_guard.

- Evidence: failure mode 4, with 15 game-winning channels seen while we carried locks (03homonoliths-a/b, 00reverse_spiral-a, 02treasure_box-a, 02guardians-a, 01boss_battle).
- Test plan:
  1. Replay-check 03homonoliths-a with the harness.
  2. Run an A/B on a Monolith or one-site suite.
  3. Run a 1280-game `ab.py` against `variants/oc-base3` for regressions.
  4. Run the live core set.
- Expected size: +3 to +6 games across Fish and Mite. It is cheap, and the evidence is the clearest of any candidate.

### 2. Respect a ready enemy nuke

Add a threat term to safety and pathing for enemy casts that are ready, using their real range and damage (Marcella slot 1 at 2x Focus, range 4; similarly Cassi and Vesper bursts). Then don't end a turn where a visible, ready caster can kill us, unless we are trading for a kill.

- Evidence: failure mode 2:
  - 298 lethal round ends, 57% dying within 2 rounds;
  - 139 lone-cast kills;
  - Fish's Marcella goes 7.1 kills to 1.0 deaths in our losses.
- Test plan:
  1. Run `lethal.py` before and after on the live set.
  2. Run a local A/B against `variants/oc-base3`, plus a solo check that the farm isn't overly timid.
  3. Run the live core set.
- Expected size: +3 to +5 games against Fish, less against Mite. The risk is lost tempo in the mirror.

### 3. Bank or flee with big bags under threat

When a champion carries a large bag (Prism above about 150, or Vesper) and an enemy pack or ready nuke is near, tribute now or break off.

- Evidence: failure mode 1:
  - Prism fed 5,445 gems in Fish losses;
  - Vesper fed 9,235 to Mite;
  - 62% (Fish) and 81% (Mite) of the gems we lost were in bags of 100 or more.
- Past caps without a threat condition lost in the mirror: the 150 retain cap read 46.7% (EXPERIMENTS). So gate this on threat, and judge it live, not only by `ab.py`.
- Expected size: +2 to +4 games, mainly against Mite.

### 4. Initiation gate on local EHP

Don't open a fight when our EHP within 8 is below theirs, unless we have a kill this turn.

- Evidence: failure mode 3. Those initiations went K69 / D219 in Fish losses, against Fish's own rule (engage when h > 0.49 and danger ≤ 0.28).
- Test plan: run `eng.py` before and after, a local A/B, then live.
- Expected size: +2 to +4 games. It overlaps with candidates 2 and 3.

### 5. Lock war on shared altars

On altars with a gap of 4 or less:
- break enemy locks promptly, since 5 basic attacks remove one;
- re-lock straight away, and keep a lock carrier near our lock.

- Evidence: failure mode 5, 1-9 above a 60% Fish lock share (04sunburst, 04wheel, adgato, 04bowls, 04courtyard).
- Test plan: run `locks.py` share before and after on the live set. The local A/B is weak here, because the mirror bots rarely lock heavily.
- Expected size: +2 to +3 games against Fish, about 0 against Mite.

### 6. Group up early and on big maps

Keep champions within about 4 of each other before r200 and on 70x70+ maps. This matches Fish's packs, and gives candidate 4's gate the bodies it needs.

- Evidence: failure mode 7, and the early deaths at 1v5 and 2v5.
- Expected size: +1 to +3 games. It costs farm, so it is only worth testing after candidates 2 to 4.

### 7. Funnel gold to the carry on separate-altar maps

Send farm gold and tributes to the richest farmer, as ocean's CHANGES 414 does but harder, and bank in larger tributes.

- Evidence: failure mode 6:
  - Fish's top earner takes 0.55-0.57 of team gold against our 0.39-0.45;
  - Fish banks 35 gems a tribute against our 21;
  - we went 7-13 on gap > 4 maps.
- Expected size: +1 to +2 games.

### 8. Endgame finishing and capture-loop fuel

When the remaining tribute is small, tribute it. Also fix the capture-reset loop: 1,328 resets and 1,477 out-of-fuel turns on 03colosseum-a.

- Expected size: 0 to +1 game (that game was a win anyway), but it is a cheap correctness fix.

### 9. The draft against a visible stun-immune Marcella

Fish's picks are fixed per map, so its round-0 Marcella can be read and answered: lower the weight of stun-reliant picks such as Ryth when it shows.

- Evidence: Ryth went 7-13 against Fish but 13-7 against Mite.
- Expected size: +1 game.
- Test it in the draft lab, then live.

### 10. Back-to-back turn priority

This has the lowest priority, because the transplant cost about 4 points in the fish-bot test. Revisit it only once candidates 2 to 4 are in.

## A local stand-in closer to Fish

What exists:
- `bots/fish` (rounds 1-2) is weak: it read 23.6% against astraeus-37e1eb6, and its farm and combat chunks read 12.6% and 11.2%. Its local win rates do not track the live ones.
- Of the panel, `astraeus-now-1106` is closest: the same games read 57.5% locally against it.

What would work:
1. **The pinned live scrim set is the exact oracle.** It is deterministic: 80 games for about 25 minutes of quota. Use it as the final gate for every candidate above.
2. **Puppet replays for diagnosis.** The replay harness can replay Fish's recorded inputs, putting our bot in the exact states where it fed: 03homonoliths-a r600, and the Marcella lethal-range round ends. This needs a v78 build of the harness trace bot. It answers "what does ocean decide here", not win rates.
3. **An exploit sparring partner.** Take `astraeus-now-1106` and graft on the parts of Fish that hurt us, rather than all of Fish's play (piecemeal Fish features lost inside astraeus, so it will be a weaker bot, but a sharper test):
   - the Marcella Focus build and Fish's per-map draft order;
   - the funnel to Marcella and Vesper;
   - the gap ≤ 4 lock rule, and attacks on enemy locks;
   - pack movement (nearest ally within 4).

   Validate it by correlation: run it on the 40 core maps against ocean v78, and keep it only if its per-map results track live Fish (for example, it wins 00lanes, 00quarry, 02the_pack, 04sunburst and 03homonoliths, and loses where Fish loses). It would take 1-2 days. The Marcella build, the draft order and the lock rule are about 1 day, and they are the parts that carry failure modes 2 and 5.

The recommendation is to do item 1 for every candidate, and item 3 only if quota for the live set is limited.
