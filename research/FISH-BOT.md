# How Intercontinental Fish's bot plays

Reverse-engineered from replays on 2026-10-19, as rules we could reimplement. [FISH.md](FISH.md) covers why hecate loses to Fish; this file covers what Fish's bot does.

## Data and method

- **Sample.** 459 ranked games of Fish against the other top-15 teams on 2026-10-18, from `replay-bulk/2026-10-18/*Intercontinental-Fish*`. Fish won 64%.
- **Baseline.** Each figure is compared with the opponents in the same games.
- **Reproducing.** Extract with `node tools/replay/extract.mjs replay-bulk/2026-10-18/*Intercontinental-Fish*`.
- **Method.** Positions and hp were rebuilt for every event, not just once per round. Positions matched the round tables in all 102k checks. Each action was judged against the units that were on the board and visible at that moment.
- **Thresholds** below are best fits to Fish's choices, not its literal constants.
- **Two versions:**
  - **Old.** Ladder groups before 20261018-2010: 393 games, 66% won.
  - **New.** From then on: 66 games, 89% won. It drafts Stellar before Ren, buys Home, and sets turn priority from health and bag. Differences are noted inline.
- **Determinism.** Fish's bot is deterministic. On the same map, side and version, its bodies follow identical paths in every game until they first see an enemy.

## The bot in one page

1. **Draft per map.**
   - Most maps: Ren, Stellar, Cassi & Issac, Ryth, Varg, as many as the map allows.
   - Expanse: Cassi & Issac, Stellar, Varg. Rows: Cassi & Issac, Stellar, Varg, Ren. Contest and stampede: Stellar, Tavi, Prism, Cassi & Issac, Ren.
   - The new version picks Stellar first, and on rows takes Stellar, Prism, Cassi & Issac, Varg.
2. **Open on the best elk-sized group,** usually with all six bodies.
   - Ren dashes ahead on round 1, wakes the group, tanks it and recalls below 30% hp.
3. **Clear from range:**
   - Spells from range 4-5 open the fight.
   - Stuns keep landing on the monster that deals damage.
   - Basic attacks always hit the lowest-hp camp in range, so clusters die first.
4. **One holder per capture,** the first body on a tile. Higher-id allies step off the tiles.
5. **Spend gold at once.** When a payout lifts gold to 150, the price of five shards (one emblem), that body recalls, even carrying gems. It buys a fixed build per champion, then walks to the altar.
6. **Recall rules.** Recall at 30% hp. Otherwise never recall without a reason.
7. **Next group:** the one it can hit soonest, counting groups still respawning. Bodies arrive 1-4 rounds before the respawn.
8. **Fight rule.** Fight if hp is at least about 30% (300 after the visible enemies' burst) and either the local hp ratio is at least 1.5 or a hit is ready on the nearest enemy. Otherwise walk away, and recall once out of reach.
9. **Targets:**
   - Basic attacks: the lowest hp + shield.
   - Stun-damage spells: a killable enemy, else the biggest threat.
   - Cassi's stun: the highest Strength.
   - Nukes: a killable enemy (the healthiest if several).
   - Stun first, then damage. AoE only if it hits two or more champions.
10. **Turn priority** goes to the body that can kill, so it acts before its victim.
11. **Chase** low-hp enemies and gem carriers into the enemy half. Contest an enemy capture by killing the holder, not by stepping on a free tile.
12. **Never used:** altar locks, consumables (except one teleport on pilgrimage), and wards on bushless maps.

## Opening and route

**The whole team goes to one elk-sized group, not the nearest wolf.**

| map | Fish's opener | opponents' usual opener |
|---|---|---|
| eight | EE(13,3), all six, 34 of 34 games | W(9,15) |
| corners | E(18,22), all six | W(10,41) |
| ambush | EGGW(21,44), all six | |

- **When two groups score about the same, Fish splits:**
  - monolith: four bodies on E(13,38), Ren and Cassi on W(3,39).
  - lanes: one body per wolf.
  - contest: three pairs on gold camps.
- **New version:** sends one body solo to a side target, such as Stellar to corners W(10,41) or Issac to stampede's axis gold.
- **Side matters.** On corners, Ren goes to W(10,41) from side A but to E(12,16) from side B.
- **Ren opens.**
  - `364a043c` (eight), r1-18: Ren dashes on round 1 and wakes EE(27,3) with his stun from range 3 at r10. He tanks both elks alone (900 → 240 hp) while the others arrive at r13-19, then dashes out and recalls with 0 gems. He does this in every eight game.
  - In the old version Ren takes 68% of camp hits when allies are present, mostly because the lowest id wins aggro ties.
  - His reflect puts 1.66M damage on camps, against 0.77M for opponents' Ren.
- **First-target formula (rough fit).** Maximise gems / (steps + hp/300 + 6) over own-side groups with at most about 5000 hp and nobody contesting them nearby. It fits 10 maps, needs the contested exclusion on fragment and rushbait, and fails on swirl.
- **Next group.**
  - The best simple predictor is the group it can hit soonest, max(walking steps, rounds until respawn): 50% (opponents 47%).
  - A logit fit (54% on held-out data) adds +1.3 for respawning groups and +0.5 for already-damaged groups, and gives gold-only groups -2.1.
- **Arriving before the respawn.** 43% of next-group choices are groups still respawning. Of bodies 12+ tiles away 20 rounds before a respawn and within 3 at it, 86% arrived 1-4 rounds early (opponents 55%).
  - `364a043c`: Stellar captures EE at r33 (due back r93), recalls at r63 still carrying 72, walks back, waits next to it from r91 and casts at r93.
- **Old version never touched the biggest groups:**
  - expanse's 120-gem EEGGs: 0 captures in 22 games, apart from a fixed solo Varg dive at r304 that always fails.
  - rows' GGMM: 0 of 21. The monolith map's Monolith group: 0 of 24.
  - stampede's 360-gem shared group: before r332, or never.
  - The new version chips them from range 4 (rows GGMM from r156, stampede from r43). This is most of why the new version wins 89%.

## Clearing a camp

- **Basic attacks hit the lowest-hp camp in range.**
  - With a cluster and a monster both in range, Fish hits the cluster 95% of the time (opponents 16%).
  - So a body already stands on a freed tile when the last monster dies: 90% against 64% on Elk + 2 gem clusters + Wolf. The hold starts the next round.
  - The cost: the monster keeps attacking until the end. On 2 Elk + 2 gem clusters, Fish takes 434 elk damage per 1,000 elk hp destroyed, against 217.
  - hecate does the opposite: `attack_camp` ([bot.cpp:150](../bots/hecate/src/bot.cpp#L150)) hits the highest Strength/hp first.
- **Openers from range.**
  - 37% of Fish's first wakes come from distance 4 or more, and the waker ends its turn out of reach (opponents 18% and 17%).
  - Elk openers are Stellar or Ryth AoE from distance 5, Cassi's stun from 4, and Ren's stun from 3-4. Opponents open with melee basic attacks 51% of the time.
- **Stuns on the monster.** Stuns cancelled 19.4k camp attacks with a champion in reach (opponents 11.0k), avoiding about 14% of the camp damage Fish would have taken.
  - Fish's Cassi stuns camps 4.3 times per 100 alive rounds, opponents' 1.4.
  - `d161987f` (elkring), r1-10: the Elk + gold cluster opener goes Ryth AoE (r1), Ren stun (r2), Cassi stun (r4), Ryth AoE (r9), Ren stun (r10). The Elk lands 5 hits in a 10-round, six-body clear.
- **Engine fix found here.** A damage-free stun wakes a sleeping group. It is now in [cambc-rules.yaml](../cambc-rules.yaml) and [findings.md](../rules-verification/findings.md) (`probe-stunwake`).
- **Positions.** Melee stand at distance 1 and casters at 3 (80% of caster turns).
- **Crews.**
  - Wolf groups 1.8-2.8 bodies (opponents 1.6-1.9); elk groups 3.0-4.1 (2.0-3.0).
  - Median clear time is 2-4 rounds shorter.
  - Solo clears are faster too: Issac clears an Elk in 9 rounds, against 15.
- **Camp damage per gem is about even** (13.8 vs 12.5). Fish trades exposure for speed, and earns it back with stuns, range openers and reflect.
- **New version: priority steers camp aggro off carriers.** Empty-handed bodies get priority -1 - floor(10 × (1 - hp/max)), carriers -6 - floor(5 × (1 - hp/max)). Fish therefore acts in that order, and camps, which hit the first actor on ties, hit the healthy empty body.
  - In carrier/non-carrier ties the carrier is hit 301 of 1,506 times (random 734).
- **Monoliths and other huge groups: one caster at exactly range 4.**
  - It casts both spells each cooldown and lets the group fall asleep in between.
  - `ec10b1fd` (rows, new version), r156-310: Stellar at (29,22) AoEs both Monoliths every 8 rounds, joined by Prism from r170. 41k hp destroyed for 0 damage taken; 224 gems each at r310.
  - Opponents beat the old version with exactly this on expanse: `1c0e1aa6`, Mite's Stellar, 24 casts from (66,24) for 40 damage taken.

## Captures and holders

- **One share per capture.** 98% of Fish captures pay a single share (13,253 of 13,516), including all 69 contest Monoliths and 27 of 29 stampede 360s.
  - The holder is the first body on a tile.
  - A higher-id ally on the tiles steps off the same round or the next: 375 of 386 leavers had a higher id than the holder. No messages are needed, since the lowest id also gets the share remainder.
- **The crew moves on together.** Only 26% are still within 3 at payout, and 68% head for the same next group.
- **Handoffs.** Issac, Varg or Ryth sometimes give the tile to Stellar, Cassi or Ren: the receiver steps onto a second tile and the holder steps off (`d161987f` r39-41).
- **Fish does not anchor on the tiles.** With a visible enemy within 6, Fish steps off 34% of turns (opponents 23%), even at full hp, half the time to fight.
  - Watched holds pay 49% against 69%, but Fish retakes the group in 760 of 1,397 walk-offs.
  - The same dithering loses groups: `6a808233` (interlock), r190-196, Ren idles 3 tiles from his free tile and Mite's Varg takes 72.

## Recall, shop, bank

- **Recall to shop at 150 gold.**
  - After a payout that lifts gold to 150 or more, Fish recalls within a round 83% of the time (3,099 of 3,733; opponents 19%). Below 120 it is 1% for both.
  - This triggers 47% of all Fish recalls.
  - The only exception: a carrier within 5 steps of an altar tributes first (41%).
  - `94a2efa6` (eight), r33-38: Stellar is paid 72 gems and 320 gold, recalls carrying the 72, buys two emblems, and banks at r138.
- **Low-hp recall at 30%.** It is a cliff: 1,036 recalls at 27.5-30% hp against 243 at 30-32.5%.
  - Fish almost never recalls healthy, empty-handed and poor: 185 times, against 8,243 for opponents (41% of theirs).
  - Fish cancels 7% of its recalls, opponents 41%.
- **Recalls start out of reach.**
  - 77% start with no enemy visible, and only 2% with one within 5.
  - Completion by nearest visible enemy: 86-89% at 6-8 tiles (opponents 58-76%); 93% with none visible (60%).
  - With an enemy within 4-5, Fish cancels its own recall and walks or dashes away instead of letting damage cancel it (404 times).
- **Lazy banking.**
  - Bags are banked at a median age of 40 rounds (opponents 22). Fish carries 16.9 gems per body-round against 9.7, yet loses half as many on death (21.6k vs 43.5k).
  - Without gold to spend, it banks next only once the bag is about 5 gems per step to the altar.
  - Usual cycle: capture, recall with the bag, shop, walk out to the altar.
- **Altars and escorts are not distinctive:** the nearest altar 80%, an escort for big bags 52%, tributes together 19%.
- **Where lazy banking costs.**
  - Pilgrimage: 376 recalls carrying 40+, then a walk of about 56 tiles from spawn to the top altar.
  - Close games: the first team to start a tribute that would reach 1000 won 97 of 99. Fish's winning attempts are 66-132-gem bags (7-14 turns); opponents' are 22-48 (3-5 turns).
    - `9e7cb430` (rows): Fish's Varg starts 132 at r353. Mite's Ren starts 33 at r356 and wins at r360.

## Builds

Fish spends everything on every visit (under 30 gold on all 14,686 spawn exits) and always shops while dead (352 of 352). Each champion's build is fixed:

| champion | build |
|---|---|
| Ren | Bruiser Health, Durability Health, Power Focus x4+ |
| Stellar | Power Focus, Durability Health, Power Focus ... |
| Cassi | Bruiser Health, Durability Focus, Power Focus |
| Issac, Varg | Power Strength, Durability Health, Power Strength |
| Ryth | Bruiser Health, Durability Health, Power Strength |
| Tavi (contest, stampede) | Treasure Focus, Durability Focus, Power Focus |
| Prism (contest, stampede) | Power Focus, Durability Health, Power Focus |

- Expanse and rows open with a Monster emblem, then buy Power only.
- The new version makes Home Health the second emblem for Stellar, Issac, Varg and Prism, so their recalls take 3 turns instead of 5. The old version never bought Home.
- Consumables: none, except a 10-gold teleport crystal into pilgrimage's walled GGWW(16,46) pocket. `92670e4a` r364-406: Ren solos it and recalls out with 92 gems.

## Fights

**When it fights.**
- Fit over 112k turns with a visible enemy within 5, right 71% of the time (baseline 58%):
  ```
  engage  if  hp - visible enemies' one-turn burst >= 300  and  (local hp ratio >= 1.5  or  a ready hit on the nearest enemy)
  ```
- Opponents fit the same shape with a higher floor (hp after their burst ≥ 400, or about 50% hp). Best hp floor by team: Fish 0.30, Nyx 0.40, Mite and procless 0.50, new team(4), Univ and Boost 0.60.
- At 30-40% hp with a 3:1 hp edge, Fish engages 62% of the time, opponents 31%.
- Against casters it waits at 6-7 tiles: 39-43% of its retreats from Stellar, Cassi or Tavi start at exactly 6.

**Targets** (actions with 2+ visible enemies in range; random-pick baseline in brackets):

| action | rule | Fish | opponents |
|---|---|---|---|
| basic attack | lowest hp + shield | 92% (49%) | 79% |
| Ren, Tavi, Prism stun-damage | killable, else max(Strength, damage of its ready spell) | 83% (48%) | 57% |
| Cassi's stun | highest Strength | 78% (52%) | 49% |
| Stellar, Cassi 2x nuke | killable, then in range 3, then lowest hp | 85% (48%) | 68% |

- **Stuns ignore low hp and read enemy cooldowns.**
  - Scoring spells on cooldown as threat drops the fit to random.
  - `f0fc9830` (rushbait), r275: Ren stuns a 1,125-hp Stellar with both spells ready rather than a 455-hp Issac.
  - Cassi's stuns go to Varg, Issac, Ryth and Ren.
- **No overkill.** With several killable targets, the nuke takes the healthiest (77%; opponents pick the lowest 74%).
  - `7599c12d` r282: Stellar kills a 700-hp Cassi, which also kills Issac, rather than a 92-hp Stellar.
- **Stun, then damage.**
  - Cassi follows her own stun with damage 46% of the time (opponents 28%, usually damage first).
  - Stuns are stacked on one target: 543 runs of 2+ lost turns against opponents, 215 against Fish. `9ad43b15` r379-381: Ren, Cassi, then Ryth stun the same Ryth.
  - An enemy Fish stuns dies within 2 rounds 12% of the time (opponents' stuns 5%).
- **Stellar's AoE rule.** AoE only if it hits 2+ champions (95% of AoEs do). Blind AoE casts at unseen champions: 14, against 112 for opponents.
- **Dashes go toward the fight:** Issac 74%, Ren 73% with an enemy within 8 (opponents 37% and 53%).
- **Kills.** Fish takes a kill available that turn 97% of the time, opponents 79% (counting spells).
  - Our check counting basic attacks alone gives 93% and 90%, so the gap must come from spells; the spell part is unconfirmed.
  - Kills are not steered to a carry: kill shares track damage shares.
- **Turn priority.**
  - Priority is 0 with no enemy within about 6. Otherwise it rises with kill potential, roughly min(10, 10 × my one-turn damage / hp of the weakest enemy within 6). The fit is loose: exact on 46% of rows.
  - The killer acts before its victim in 74% of Fish kills (45% of opponents' kills), and is its team's first actor in 67%.
  - `12ea13aa` (elkring) r207-210: Ren, Ryth and Cassi chain stuns on a Tavi, then Stellar at priority 10 acts first and kills it before its turn.
  - hecate already ranks kills highest in [turn_order.cpp](../bots/hecate/src/turn_order.cpp).
- **Not distinctive:**
  - Focus fire: one Fish body per victim-round 85% of the time.
  - Raw burst: median 125 per victim-round, p99 1,010, against 112 and 920.
  - Holding cooldowns: Fish spends spells on camps and starts fights with fewer ready.
  - Ambush from bushes.

## Disengaging and chasing

**Disengage.**
- Of drops below 25% hp in combat, 62% of Fish champions survive 30 rounds, against 36% of opponents'. Fish's Stellar survives 61%, opponents' 30%.
- The pattern: walk away first, recall only once out of reach. Allies stun a chaser within 6 for a third of survivors.
- `0261b162` (eight), r170-187: Ren holds 108 gems at the central altar under three procless champions.
  - He steps back one tile per turn, reflecting damage, while Cassi and Ryth stun the chasers.
  - He starts a recall, cancels it himself with an enemy 2 tiles off, dashes clear, recalls again from 6 tiles, and gets home with all 108.

**Chasing.**
- Fish follows a fleeing enemy within 6 59% of the time (opponents 49%): 72% if the target is below 25% hp, 74% if it is below 50% and carrying 40+.
- It has no leash: it follows more in the enemy half (66%) and stops only near the enemy spawn.
- Chases kill the target 31% of the time (12%), and carriers 29% of the time (6%).
- Fish's 3+-round episodes in the enemy half end 1,538 kills to 278 deaths (opponents 641 to 581). They are chases and steals, not planned raids.

**Contesting enemy captures.**
- Fish hits the holder in 24% of episodes and steps onto a free tile in only 3%.
- It steals by killing or chasing off the farmer, then finishing the camp: 559 steals (20.9k gems), against 396 (14.7k).
- `f5b6c700` (ambush), r515-532: Ren dashes onto Sneaky's Cassi and Issac, follows them and kills both, while Stellar finishes their 120-gem group from range 4-5 and holds it alone.

## Vision, locks, channels

- **Altar locks:** 0 bought or placed in 459 games. Opponents placed 544, mostly to protect their own tributes.
  - Fish breaks locks (306 destroyed), e.g. `2e69bd92` r176-184: a stun on the locker, then 3 basic attacks.
- **Wards:** half as many as opponents (17.8 per 1,000 alive rounds vs 35.4), and none on collision or expanse.
  - 94% go on a bush tile at full range 2, the turn a bush cluster first comes within 2. Carriers ward the bushes in front of their altar.
- **Enemy tributes and recalls are not special to Fish.** It engages a channelling enemy about as often as any other (52-53% vs 51%) and has no routine for stopping a game-winning tribute.
  - `c158a100` r536-552: Ryth stuns a 118-gem tribute once, then paces 6-7 tiles away with the stun ready while the restarted tribute wins the game.
- **Dithering.** With an enemy visible, 12.9% of Fish's consecutive moves undo the previous one, against 8.0%. It costs holds and the occasional game.

## How Fish loses

Most of its 165 losses are farming and banking races, not fights: deaths are about even in its losses.

- **Expanse (3 of 26)** and **stampede (9 of 27)**, old version: it skips the 120- and 360-gem groups (see Opening and route). Opponents chip them from range 4, and also take Fish's own-side EEGGs uncontested (`d850652f`, `1770ed48`).
  - On stampede all 19 single-holder 360-gem tributes against Fish completed, with Fish 12+ tiles away.
- **Contest (11 of 20):**
  - Mite (6-0) never touches the Monoliths, holds the centre with five bodies and farms the gold camps. It wins on gold at round 2000 (`baddea56`: 0-0 in gems, gold 18k to 2.2k, deaths 69 to 8).
  - Fish's single 200-gem holders die carrying the bag (`cccba396`: 4 of 4).
- **Pilgrimage, corners, interlock, fragment:** the shared or exposed elk groups go to whoever clears and holds. Fish's tanks take elk hits while the other side chips from range, and Fish's dithering holders lose the tile (`830e403e`, `6a808233`, `f7c6aa17`).
- **End race:** big, slow final tributes (see Recall, shop, bank), self-cancelled tributes when an enemy appears (210, e.g. `cdda7e71`), and no locks or interrupts.
- **Not weaknesses:** fuel (0 turns run out of fuel), idle bodies, or linked Cassi & Issac deaths.

## Against hecate: what to try

Ordered by expected value. Each needs the usual A/B.

1. **Recall to shop at 150 gold.** FISH.md item 4 called this a hecate weakness, but Fish does it more often and wins with it.
   - The difference is the walk: Fish heads to the soonest-hittable group from spawn and banks lazily.
   - Before cutting the shop recall, try pricing in the walk back while keeping it.
2. **Builds.** Copy Fish's fixed builds as a baseline for `best_emblem`: Focus on the casters, Bruiser and Durability Health on the front line, Home in the new version.
3. **Camp targeting.** Basic-attack the lowest-hp camp in range (clusters first), so a body is on a tile when the group dies. Stun the monster that deals damage; open from range 4-5.
4. **Fight thresholds.** Engage down to about 30% hp when the local hp ratio is at least 1.5 or a hit is ready; walk out before recalling.
5. **Chase** low-hp enemies and carriers without a leash.
6. **Respawn timing.** Count respawning groups in the next-group choice and arrive 1-4 rounds early.
7. **Exploit Fish's weaknesses:**
   - Bank small bags first in the end race.
   - Lock its altars; it never locks ours but breaks locks.
   - Chip shared groups from range 4 and hold the clear.
   - On contest, consider Mite's gold turtle.

## Corrections to FISH.md

- **The draft is map-dependent.** Expanse, rows, contest and stampede differ, and the new version picks Stellar first.
- **Crews are bigger than FISH.md says:** about 2 bodies on wolves, 3-4 on elks.
- **The Home shards are all from the new version.**
- **Long solo range-casting:** Fish rarely does it on ordinary camps, but it is how the new version takes Monoliths and other huge groups.
