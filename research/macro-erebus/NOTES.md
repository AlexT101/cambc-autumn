# EREBUS: macro refactor of charybdis (2026-11-11)

Worktree `/home/ubuntu/wt/macro-o5`, branch `macro-o5-20261111`. Reference `bots/variants/charybdis-ref` (= charybdis
at 81fc6f968). Every A/B: `tools/ab.py CAND variants/charybdis-ref --no-test-draft --fuel 200000`, release, fast
runner, own drafts. Dev suite `maps/macro-dev` (5,120 maps, 10,240 games); holdout `maps/macro-holdout` + standard
suites for confirmation. Study suite `maps/macro-study` (mapgen ladder-v2 seeds 87000-87003, 1,024 maps) for debug
traces and smoke tests only.

## Evidence 1: 1,024 charybdis mirror games (debug, maps/macro-study; scripts in the session scratchpad)

- Winner vs loser: deaths 2.5 vs 7.2, kills 7.2 vs 2.4, capture gems 1050 vs 822, gems lost at death 66 vs 279.
  Time: walking ~50% for both, camp 18.6/16.8%, dead 4.5/12.0%.
- Both teams draft Prism in 898/1024 games. **The first Prism to die loses 88%** (592 games with a Prism death).
  Its killer is the enemy Prism in 67%. Median round 370, bag 144.
- The first team to hold a winning bag (score + bag >= 1000) wins 90.6%: the end-game tribute is rarely the lever
  (only 95 of 1009 games reversed).
- Collected gems per team vs half the map's supply: 0.47 at r100, 0.81 at r150, 1.14 at r200 (respawns included):
  the economy is close to supply-bound early, so leads come from contested camps and kills.
- Early lead predicts: team collected-gem ratio >=1.5 at r150 wins 72%, at r300 90%.
- First-dying Prism by Focus ratio (victim/other): <0.8 224, **0.8-1.25 291**, >=1.25 77. Half of the decisive
  Prism deaths happen at parity: a coin flip decided by tactics.
- Prism-on-Prism engagements (2,916 openers, first hit after 20 quiet rounds): at distance 4 (1,216) or 5 (1,667,
  AoE only). In parity first deaths the first hitter is the killer 69% (169 vs 77). How the victim came to be in
  reach at the hitter's turn start: walked from 6+ into <=5 and ended there ~30%; started and ended at <=5 with a
  spell ready, not hitting, ~35% (the enemy Prism visible to it in ~70% of those); the hitter had a double turn ~26%.
- Prism-on-Prism openers at parity, by allies within 6 (hitter, victim): a victim with no ally near dies within 15
  rounds 21-31%, with 1-2+ allies 9-21%; but 460 of 828 parity openers are (2+, 2+) team fights, so escorting the
  Prism would move few deaths.
- Captures by zone (share of spawn distance; own < 0.4 < mid <= 0.6 < enemy): own-side captures are equal for winner
  and loser (98/97 gems by r150, 230/219 late); **mid captures make the difference** (56 vs 46 by r150, 161 vs 104
  r150-400, 276 vs 154 later). Enemy-side captures are rare (~1 a game).
- Killers: the winning team's Prism kills 4.19 of the loser's champions a game (190 gems taken), Vesper 1.17, every
  other type <0.4. Of 3,490 non-Prism deaths to the enemy Prism, the Prism's 2.5x Focus combo (stun 1.5 + AoE 1.0) was
  already lethal at its first hit in 89%; the victims had mostly ended their turn at distance 4-5 (or 4-6 before a
  double turn).

## Experiments
- Loss study (read-only agent, 1,024 mirror games; scripts in the session scratchpad `study/`): between r80 and the
  first decisive event (first Prism death or a lasting 1.5x gem lead) the faller (loses 78% after) differs in:
  (1) its Prism loses a first exchange and stays out wounded (<50% HP for 5+ rounds off spawn in 64/227 vs 22; Willow
  near in 0 of those; camp damage taken in the 40 rounds before: 131 vs 46); (2) it loses a body first (Cassi & Issac
  pair deaths 117 vs 34 within 60 rounds of the event); (3) then it cedes mid camps: mid captures in the last 30
  rounds 0.53 vs 1.41, retreat share 9% vs 4.7% (half the retreating at 70%+ HP, while seen). Not distinctive: team
  spread, Prism alone, champions away banking/shopping.

A/Bs are cheap: 10,240 dev games in ~1 minute of play (plus ~2-3 min to build), so the bottleneck is implementation.

### E1 `e1-space`: Prism initiative spacing - LOSES (47.9% of 10,240 dev, CI 47.0-48.9)
Our Prism ends no turn in the enemy Prism's strike reach (5, 6 when it gets two turns; one window of look-ahead) unless
our Focus >= 1.25x its or its combo is under a third of our health; merged into the step and work guards, the hold
tests and an explicit step-out (new `combat/spacing.cc`). Debug smoke (1,000 games): Prism-on-Prism openers suffered
fell 30% (1,432 vs 2,104 of the reference's) but **our Prism died first more often (315 vs 254)**. Avoiding the
opener costs more than the opener: the Prism gives up holds and positions (Focus) and leaves allies unprotected. Same
lesson as macro1's duel/yield/guard: giving way loses.

### E2 `e2-open`: Prism takes the opener - LEVEL (50.2% of 10,240 dev, CI 49.2-51.2)
The strike search ranks plans that open on an enemy Prism in reach above others (below break penalties; kills and
cancels compete on value), stripped on lethal tiles and when outclassed (its Focus >= 1.25x ours and our combo can't
kill it); the retreat branch runs the search in open-only mode first. Eligible turns hit E 84% -> 91% (retreat turns
77% -> 94%), first Prism-on-Prism hit landed in 687 vs 651 games. No result: the opener was already taken in most
eligible turns, and the extra openers don't decide duels.

### Probe batch: 16 one-constant shifts of macro dimensions (10,240 dev games each) - ALL FLAT
Win % vs the reference (CI about +-1): bank floor lower (`bag_swing` 4) 50.1, higher (1) 49.6; `camp_risk` x1.4 50.0,
x0.7 50.1; `carry_reach` doubled 50.4; `crew_cap` 2 50.1; `gem_value` x1.5 50.1; `life_value` x1.5 50.2;
`home_power` 3.8 **48.8**, 0.95 50.3; mid band worth x1.3 50.2; `pursuit_steps` 1 49.6; recall line x1.4 **49.2**,
x0.7 50.3; retreat ratios x1.5 50.4, x0.7 49.6. The tuned constants sit on a flat optimum against the mirror;
only the cautious directions (more enemy-ground discount, higher recall line) cost anything. No knob is worth
pursuing: the mirror needs a structural change, not a re-weighting.
- Probe batch 2: mid band worth x1.6 **47.9**, x2.0 **44.8**, wider band 49.5; stacked flat probes (mid x1.3,
  carry_reach x2, pursuit 1, retreat x1.5) 49.4, plus recall x0.7 49.9. The mid's current weight is the optimum:
  more pull to contested camps loses monotonically.

### E4 `e4-heal`: the Prism keeps out of one-spell range of death
Our Prism's recall line (every reader: want_home, farm's camp budget, crew pricing, work guard) is floored at
min(hurt_health_fraction, 1.5 x enemy Prism Focus / our max health) while an enemy Prism lives. Debug smoke: Prism
deaths 1.18 vs 1.24 a Prism game, rounds under 50% HP off spawn 34.7 vs 39.3, 0.57 trips home a game from it; smoke
50.3%.

### Prism gold (evidence for E5)
Mean unspent gold carried while alive: Prism 176; others 6-76 (Cassi 15, Issac 12, Vendetta 37, Vesper 76). The
Prism keeps its hoard in the field and seldom goes home, so ~6 shards sit unbought.
- E4 on dev: **49.8% of 10,240 (CI 48.8-50.8): level.** Fewer wounded Prism rounds, no win-rate change.

### E3 `e3-reach`: no non-Prism champion ends a turn in a lethal enemy Prism's reach - LEVEL/LOSS (49.0% of 10,240)
E1's machinery for every non-Prism champion (off for our Prism), only where the enemy Prism's 2.5x Focus combo kills
it; exempt when one of our Prisms stuns it first. Non-Prism deaths to the enemy Prism 2.25 vs 2.34 a game (-4%),
smoke 49.7%, dev 49.0%. Third avoidance rule, third non-gain: each death avoided costs as much in ground ceded.

### Prism shopping trips (E5 and r-probes)
- E5 `e5-shop` / `e45`: the Prism's trip value adds its shards' Focus-equivalent (30 gold = 8 Focus = 5.33 kept gems,
  the carried_bonus identity read backwards) in rounds of its gem income. Smoke **40.7% / 39.9%** (2,048 each).
- Trip value scaled (dev, 10,240 each): x2 **47.1%**, x0.5 50.5%, no voluntary Prism trips 50.4%.
- So the Prism's 176 unspent gold is not a waste: its time in the field is worth far more than shards. Fewer trips
  is, if anything, slightly better; more trips loses steeply.
- E5 after its audit fix (Health shards no longer priced as Focus): smoke 43.8% / 42.9%. Debug (first version): the
  Prism's spawn visits while alive 23.9 vs 18.2 a game, unspent gold 84 vs 249, mean bag 267 vs 297, deaths level.
  About six more trips home a game cost ~7-9 points: the Prism's field time is the most valuable thing it has.
- Holdout + standard suites (3,840 games each): no voluntary Prism trips 49.3% (holdout 49.0), half trip value 49.5%.
  Level; the dev +0.4/+0.5 was noise.

### E6 `e6-nofeed`: E3's rule only while no Prism of ours is alive - LEVEL (50.2% of 10,240 dev)

### The Prism's trips home (r-probes, 10,240 dev games each)
| Variant | Change | Win % |
|---|---|---|
| r-norf | the Prism never plans the recall-home-and-walk-out route to a farm group | **46.9** |
| r-nocr | the Prism never rides a held capture home (recall timed to land at the payout, to heal and shop) | **48.8** |
| r-noshop | the Prism takes no voluntary shopping trip | 50.4 (holdout+standard 49.3 of 3,840) |
| r-field | all three together: the Prism goes home only by dying | **33.4** |
Strongly non-additive. The Prism's ~18 spawn visits a game are bundled with travel (recall transport, capture
rides) and carry its heals and shard purchases; with them all gone it never heals or spends, and loses 17 points.
Unbundled trips (E5, trip value x2) lose too. The
same recall-out route forbidden to every champion but the Prism (r-norf-allies) costs only 0.9 (49.1%): transport
by recall matters most for the Prism, whose walks are the team's most valuable turns. So the existing home-visit economy is near its optimum from both sides;
the one-sided levers (drop a route, add trips) all lose.
- Capture ride home valued x2 (r-crx2) 49.5%; the Prism's own hold may ride home in an enemy's possible sight
  (r-crsee) 49.9%. Level.

## Outcome

**No candidate beat `charybdis-ref`; `bots/charybdis` is left unchanged** (identical to the reference). Every
structural change was level or lost on 10,240 dev games, and the few dev readings of +0.4-0.5 were level on the
holdout and standard suites (3,840 games). The target (60%) was not reached.

| Experiment | What | Dev win % (10,240) |
|---|---|---|
| E1 e1-space | our Prism ends no turn in the enemy Prism's reach at parity | 47.9 |
| E2 e2-open | our Prism takes the opener on an enemy Prism in reach | 50.2 (holdout+standard 50.2 of 3,840) |
| E3 e3-reach | no non-Prism ends a turn in a lethal enemy Prism's reach | 49.0 |
| E4 e4-heal | our Prism's recall line floored at one enemy-Prism stun | 49.8 |
| E5 e5-shop | the Prism prices shards' Focus into shopping trips | smoke 43.8 |
| E6 e6-nofeed | E3 only while our Prism is down | 50.2 (holdout+standard 49.8 of 3,840) |
| E7 e7-idle | the Prism's home stop (heal, shop) taken in time it would wait for a respawning target (recall-out route priced free when it lands by the respawn) | 49.9 (first version 50.2); fires ~0.1-0.2 a game |
| E8 e8-gank | an enemy Prism alone (no enemy within 6) with 2+ of ours within 8 whose basic attacks kill it in two turns counts as prey for the chase (other chase guards unchanged) | 50.0 |
| 16 + 5 + 8 probes | one-constant shifts of every macro dimension; Prism trip routes | 33.4 to 50.5 |

## What was learned

1. **The game is the Prism's.** The first Prism to die loses 88%; the first team to hold a winning bag wins 90%;
   mid captures and kills (4.2 a game by the winning Prism) make the difference. Both teams already run the same
   Prism-carry economy, so the mirror is decided by chaos at parity: half the decisive Prism deaths come at Focus
   ratio 0.8-1.25.
2. **Duel tactics don't move it.** Taking more openers (E2) was level; avoiding the enemy Prism's reach (E1, E3, E6)
   cut openers suffered or deaths by 4-30% and still lost or levelled: giving way costs holds, Focus and ground in
   proportion. This repeats macro1's duel/yield/guard results against a different opponent.
3. **The constants are at a flat optimum against the mirror** (16 probes of +-30-100% on retreat, recall, camp
   risk, enemy-ground discount, mid weight, bank floor, crews, life/gem values, carry reach: all within +-0.6 except
   the cautious directions). The mid's weight is optimal from above: x1.6 -2.1, x2 -5.2.
4. **The Prism's home visits are bundled and precious.** Removing its recall-out transport costs 3.1, its capture
   rides 1.2, both plus shopping trips 16.6; adding unbundled shopping trips costs 6-9. The 176 gold it carries is
   the price of field time, not waste.

## Open leads

- The mirror's equilibrium is locally flat: a gain needs a qualitatively different strategy, not a re-weighting.
  The teacher's 65% suggests one exists; without its games it can't be read off. Its replays (or a scrim against
  it) would be the first thing to study.
- Bundling: since bundled home visits are worth so much and unbundled ones lose, a planner that schedules the
  Prism's heal/shop stops onto moments it would be idle anyway might gain where the trip-value knobs could not. E7's
  narrow version (respawn waits only) was level; the existing recall-out and capture-ride routes already take most
  such moments.
- Isolated enemy Prisms (no ally within 6, seen by 2+ of ours within 8) occur 1.55 times a team-game and die within
  15 rounds only 7.7% of the time. E8 widened only the chase's prey verdict for them: level. A gank would need allies
  to converge (comms), not just the champions already in reach to chase; earlier carrier hunts that did converge lost.
- The loss study's patterns (wounded Prism staying out, losing the Cassi & Issac pair, then ceding the mid) are
  real correlates, but the direct fixes for the first two (E4, E3/E6) were level: they may be symptoms of an earlier
  lost exchange rather than causes.
