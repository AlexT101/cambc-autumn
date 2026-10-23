# v38 replay analysis

Why v38 (`bots/hyperion` at 5b02a02) loses fights, gems and tempo against the top 20 of the 2026-10-22 ladder.

- **Data:** 830 ladder games (471-359), re-run and traced with [the replay harness](../../tools/replay/harness/README.md). Conclusions use trusted rounds only.
- **Cause classes:** each finding is tagged as a decision rule (the bot chose wrong with what it knew), a mis-estimate (a prediction or model was wrong), or missing information (it couldn't know).

## A. Deaths

**Scope.** All 624 distinct games, trusted rounds only. That is 3,266 deaths of ours: 3,042 to champions in 487 games, carrying 81,780 gems, and 224 to camps (2,984 gems, not analysed here). For each champion kill I joined the victim's last living turn and the 5-25 turns before it (TT, TB, TE, TA, TS) with the extract: true positions, damage events, wards and the killing event. Code references are to `bots/hyperion/src`, which is identical to 5b02a02. Scripts are in the analyst's scratchpad (`deaths.py`, `deaths2.py`, `deaths3.py`, `episodes.py`, `rcast.py`, `shortcut.py`), not committed.

**Anatomy, in numbers (3,042 champion kills):**
- **Branch at the last turn:** 81% died on a retreat turn (`d=R`: 2,466 deaths, 41,051 gems). Of the rest, 9% were stopping a game-ending enemy (`E`, 269), 4% farming (`F`, 117), and 1% each banking (`B`) or tributing (`T`).
  - `want_home`'s reason on that turn: `low` 65%, none 13%, `outmatched` 10%, `stand_lost` 6%, `stand_ok` 4%.
- **Speed:**
  - 41% began their last turn under 10% health, so most deaths are the end of a fight that had already been lost.
  - 55% of the fights lasted 6 or more of our own turns (slow trades). 17% were over within one of our turns (burst).
  - In 82% of deaths a single enemy champion dealt all the damage between our last turn and the death.
  - The enemy struck first in 50% of the fights.
- **Vision:** the killer was visible at the victim's last turn in 85% of deaths; 15% died to a killer they could not see (finding A4).
- **Retreats:** 2,790 of the deaths fall inside a retreat episode (a run of turns with `home v=1`). There are 67k such episodes, and 4.2% of them end in death.
  - The rate rises with length: 1% for 1-turn episodes, 5-6% for 3-6 turns, 17% for 10 or more.
  - Most retreats succeed. The deaths concentrate in long, chased ones.
- **Predictions:**
  - `lethal` was not evaluated on 96% of death turns: `want_home` returns on `low` before calling it (bot.cpp:2729).
  - A safety estimate said "safe" on the last turn in only 258 deaths (8.5%): `ls`/`le = -1`, `stand_ok`, or a fight sim `lost=0` (finding A5).

Findings, ranked by gems handed to the enemy:

| # | finding | deaths | games | gems lost | class |
|---|---|---|---|---|---|
| A1 | A winning bag's tribute is kept "at any risk" through channels of 20-213 turns beside visible enemies | 32 | 26 (all 33 tribute deaths) | 24,407 | decision rule |
| A2 | Chased retreats: walking home at speed 1 from faster or ranged pursuers; casting in place while fleeing | 2,027 (retreat of 3+ turns); 158 stand-and-cast | 449; 127 | 32,973; 11,214 | decision rule |
| A3 | Marcella one-cast kills: the threat model misses a cooldown that comes off between an enemy's two turns, and the step guard is skipped for fuel | 821 by Marcella (274 single cast); 203 cooldown blind spot; 17 guard skipped | 284; 144; 15 | 22,081; 4,910; n/a | mis-estimate; fuel gate |
| A4 | Unseen killers: enemy wards (91%), warded bushes, enemies untracked after 10 rounds | 456 (115 untracked; 196 in a warded bush) | 201 | 13,865 | missing information, plus a model choice |
| A5 | "Safe" verdicts before a death are rare and come from A3 and A4 | 258 | 153 | 6,117 | mis-estimate |

### A1. Winning bags tributed at any risk

**Pattern.** 33 deaths happened on a kept tribute (`d=T`), with bags of 58 to 2,490 gems. In 32 of them our score plus the bag reached 1000. Those channels had 1 to 213 turn ends left (median 30). The TE line on every one is `tribute keep=1 why=safe`, and the killer was visible at distance 1-4 in 27 of the 33. The killer takes the whole bag: 24,407 gems in all, and 19 of the 33 games were lost.

**Cause (decision rule).**
- `continue_tribute` (bot.cpp:3936) keeps the channel when `tribute_ok` holds (bot.cpp:660).
- `tribute_ok` returns `any_risk(...) || tribute_safe(...)`. `any_risk` (bot.cpp:656) is true for any `winning_bag`, whatever the channel length, so `tribute_safe`'s visible-enemy kill check (bot.cpp:375) is never consulted.
- A bag of N gems channels for ceil(N/10) turn ends. "Take it at any risk" assumes a tribute that finishes before the enemy can act. For a 500-2,500 gem bag it means standing still for 50-250 turns.
- Trace caveat: the tracer prints `why=safe` whenever `tribute_ok` is true, including the `any_risk` branch (trace-bot bot.cpp:4013).

**Cases.**
- **ddbc8901-3 r1976** (01boss_battle, vs Intercontinental Fish, a win). Our Vesper (c7) holds 2,490 gems at 24,20 with `ch=trib:195`.
  - At r1975, TB shows the enemy Vesper visible at 24,16 (distance 4, full health, `rr=1976,1980`, Strength 4175 in the extract), and TE says `tribute keep=1 why=safe left=195`. Our score was 799, so the bag was a winning bag.
  - At r1976 t1 the enemy walks to 24,17, resets and attacks for 3568.7, killing our Vesper. The kill hands 2,490 gems to the enemy.
  - The same champion had died the same way at r1779 with 1,913 gems (184 turns left).
- **76b6692e-4** (a loss) lost three bags this way in one game:
  - r956: Marcella, 1,573 gems, 149 turns left, killed by a Marcella at distance 1;
  - r990: Vesper, 1,976 gems, 181 left, killed by a Heart of Ruin at distance 1;
  - r1826: Prism, 2,176 gems, 213 left, killed by a Vesper visible at distance 4.

  Each TE line reads `keep=1 why=safe`.

Why bags reach 1000+ before banking (Prism's `retaining_gems`, bot.cpp:649, and the bank logic) belongs to section D. Here, the bag's size is what makes each of these deaths decide the game.

### A2. Chased retreats die walking

**Pattern.**
- The champion turns for home: `outmatched` 948, `stand_lost` 845, `low` 644 at the start of the fatal retreat. It walks toward its own spawn one tile a turn, and a pursuer with range 3-4 or a dash keeps or closes the distance.
- Between the start of the retreat and the last turn, the killer's distance shrank in 1,288 of 2,507 cases and stayed the same in 800.
- The recall started every turn end is cancelled every turn (`recall keep=0 why=home_unsafe`), because `recall_outruns` (bot.cpp:3161) sees an enemy that can walk into reach before it lands. So the retreat really is a 20-50 tile walk.
- 1,057 deaths came after 8 or more consecutive retreat turns.

**Sub-pattern: stand and cast.**
- On the retreat branch, `retreat` (bot.cpp:4002) calls `cast_at_enemies(world, escape_step_value)` before stepping (bot.cpp:4009). Prism's two spells, Marcella's unit spell and Ryth's stun all exclude walking. So a cast worth more than the flat `escape_step_value = 210` enemy health (bot.cpp:33) costs the escape step, however much danger the step would have avoided.
- Prism gains +1.5 Focus per carried gem, so the cast's value, and with it the pull to stand still, grows with the bag.
- 158 deaths had a stand-and-cast on the last turn (85 Prism, 35 Marcella, 29 Ryth), with 11,214 gems, an average of 71 a death.
- Base rate over all 182k trusted retreat turns: dying before the next turn follows a stand-and-cast 2.95% of the time (165 of 5,597), against 1.31% for a retreat turn that moved (2,204 of 168,465). For Prism with 20 or more gems it is 3.7% against 1.7%. This is an association; stand-and-cast turns may also be the closer ones.

**Cases.**
- **a2115cc2-3 r513** (Prism c0, 700 max health). At r507, at full health, a lone Vesper is visible at distance 7; `home why=outmatched` turns it for home, with its spawn about 50 tiles away.
  - The Vesper's distance falls 7, 5, 3, 3, 2, 1, and the Prism takes 210 on three of its turns.
  - At r509 it stood still to cast (TA `cast_enemies`, `p=q`), dealing 2 hits.
  - It died at r513. The Vesper still had 933 of 1600 health.
- **ae727f31-1 r1225** (Prism, 340 health, 54 gems). It retreats from r1213 to r1224 with a Heart of Ruin visible at distance 4-5 on every turn (`outmatched` each turn, recall cancelled each turn).
  - Twice it stops to cast (r1217 and r1224, TA `cast_with_result ... s=cast_enemies`, did not move).
  - After the second, the Heart of Ruin closes and kills it for 340, taking the 54 gems.
- **978b7171-3 r1379** (Prism, 64 gems, 385 health). It turns home at r1373 (`outmatched`) when a Vendetta appears at distance 5.
  - The Vendetta dashes adjacent at r1375 (distance 1).
  - At r1376 the Prism stands to cast (2 hits), and it dies three turns later, still walking.

**Class:** decision rule. The retreat has a single answer, walk home, and does not weigh how far home is against the pursuer's speed and reach. The escape step has a fixed price.

### A3. Marcella's one-cast kills

**Pattern.**
- Enemy Marcellas kill 821 of our champions (27%, 22,081 gems), concentrated in Trzy Kwaterki, Univardisty of Shingtonwash, policy wonk and Noobot games.
- 274 of these were a single cast from 30% health or more. Late-game Focus builds of 700-1400 Focus make a 2×Focus unit spell deal 1,400-2,800, which one-shots any of our champions.
- When it was visible the bot usually knew the danger (`outmatched`/`stand_lost`, Marcella at distance 3-4), and those deaths are A2. The model errors are below.

**A3a. Cooldown blind spot across an enemy's two turns (mis-estimate).**
- `Reach::build` (safety.cpp:1306, 1318) decides each slot's readiness once, at `turn_round = next_turn_round(e)` (safety.cpp:698), and reuses it for the second turn of a `twice` build (safety.cpp:1885).
- `threat_strike` (safety.cpp:822) has the same behaviour through `strike_memo(c, next_turn_round)`.
- So when an enemy acts twice before our next turn and a spell comes off cooldown between its two turns, `lethal`, `stand`, the step guard and the strike search all treat that spell as unavailable.
- In 203 deaths (144 games, 4,910 gems) the killing cast came from a slot the trace believed ready only after the killer's first turn but before the death (TB `rr` against the killer's turn rounds). 196 of these killers were visible. That is 19% of all deaths by cast.
- Cases:
  - **5e559ba0-1 r622** (Heart of Ruin c9, 1000/1000 health).
    - TB: Marcella visible at 25,17, `act=0`, `rr=624,623`.
    - The bot judged its tile safe: `ls=-1`, `home why=stand_ok`, `fs=0:0:0:0:0:0`. It farmed one step to 29,14, distance 4.
    - Marcella acted after it in r622 and first in r623, and cast slot 1 for 1000 at r623 t0.
  - **0b9370f1-5 r421** (Heart of Ruin, 750 health).
    - TB: Marcella `act=0`, `rr=420,421`. The bot read `ls=-1`, `stand_ok`, and chased to 27,16, distance 1.
    - It was killed at r421 t0 by slot 1. The cast was ready at the killer's second turn.

**A3b. Step guard skipped for fuel (fuel gate).**
- `step_guard` (bot.cpp:2761) returns no guard when its fuel estimate is short (`note_shortcut("step-guard")`, bot.cpp:2814, 2884, 2919). A farm or chase step can then end in a lethal tile.
- This happened on 10,334 trusted turns. 17 of them died before their next turn: 0.16%, against 0.11% for all turns, and 0.20% when the champion moved.
- 8 of the 17 were Marcella one-shots: 5e559ba0-1 r512, r622 and r908; 098927ae-2 r1950; 0b9370f1-5 r420; a0bf6932-2 r1021 and r1071; 4929c7e8-4 r314.
- Case: **5e559ba0-1 r908** (Vendetta, 1800/1800).
  - Level-2 trace: `TQ lethal p=28,19 v=-1` at the start tile, with Marcella visible at 23,16 (`rr=916,909`, Focus 1350 in the extract).
  - The debug lines `SHORTCUT 908 8 out-of-fuel` and `SHORTCUT 908 8 step-guard` show the guard was skipped, with `fu=44143`. The farm step went to 27,18, distance 4.
  - Marcella cast for 1800 at r909 t0.
- This is an existing fuel gate in the sense of FUEL-GATES.md.

**A3c. Unexplained (open).** **2612381c-4 r561** (Prism, 1335 health, 330 gems, holding a capture).
- Level 2 shows `TQ threat p=26,10 v=0.0` and `lethal v=-1`, with Marcella visible at 21,8 (distance 5, `act=0`, `rr=561,561`).
- She acted twice before the Prism's next turn: she walked to 22,8 at r561 t8 and cast for 1335.4 at r562 t1. A walk then a cast should be in the `twice` reach, and both slots were ready.
- So this is not A3a. The threat build rated the tile unreachable. It may be `turns_before_ours` (the rank prediction) or `Reach`'s sight test (her walk tiles include bush tiles 22,8 and 22,9). Not resolved.

### A4. Killers we could not see

**Pattern.**
- 456 deaths (15%, 201 games, 13,865 gems) had the killer unseen at the victim's last turn.
- The killer stood 3-4 tiles from our end tile in 61% of them. The killers were Vesper 155, Marcella 140, Prism 45 and Vendetta 41.
- Our end tile lay inside an enemy ward's 13x13 square (occlusion ignored) in 91% of them, against 73% of all deaths.

What the bot believed, from TB at the last turn:

| killer was | deaths | belief |
|---|---|---|
| tracked, ≤20 possible tiles, position within 2 | 130 | knew roughly where it was |
| tracked, more than 20 possible tiles | 199 | diffuse (a large set can fall below `credible_weight` = 0.5, safety.h:30; not logged) |
| untracked | 115 | ignored: `list_enemies` (safety.cpp:1704) counts only visible or `tracked` enemies, and `World::track` (world.cpp:1418) drops tracking 10 rounds after the last fix (`track_horizon`, params.h:25) |

87 of the 456 had `ls=-1` at the start tile.

**Warded bushes.**
- 196 deaths (131 games, 3,841 gems) ended on a bush tile whose cluster held an enemy ward. Only 15 bush-tile deaths had no such ward.
- 163 of the 196 stepped into the bush that turn, 172 of them on a retreat step.
- Mechanism: a bush tile is seen only from its own cluster or by a ward. `Reach`'s blow requires sight (safety.cpp:1504-1525), and only an enemy ward the bot has seen counts (`ward_sees`). So an unseen ward in the bush makes the tile look unhittable.
- This is verified for a farm step (case below). For the retreat steps it is plausible but not shown: `retreat_step`'s candidate values are not traced.

**Cases.**
- **a0bf6932-4 r652** (our Marcella c8, 1509/2000 health). Enemy Marcella visible at 4,17, `rr=652,652`, Focus 1140, so her cast does 2280.
  - The bot knew it could not win: r651 TE `prey_fight e=4 t=1:1:0:1:1:1` means a fight lost in one turn.
  - It farmed from 7,22 (distance 5) to 8,21 (distance 4), a bush tile. The cluster (7-11,21 and the column x=7) held her ward at 7,21, which was invisible from outside the bush.
  - `ls=-1` and `stand_ok`. She cast for 1508.6 at r652 t7.
  - Cause class: missing information (the unseen ward), made worse by a model that assumes no unseen ward.
- **098927ae-3 r1238** (Heart of Ruin, 1500/1500, farming). Enemy Marcella really at 15,9, distance 4 after our step.
  - TB: `p=6,27 pr=1206 src=c`, no `np`. Her last fix was 32 rounds old, so she was untracked and absent from Safety.
  - She one-cast it for 1500.
- **4a126b66-3 r780** (Ryth, 980/1500, farming). Marcella believed at 22,16 from r594, 186 rounds earlier, and untracked; really at 4,10, distance 4. One cast, 980.

### A5. When the estimates said safe

258 deaths (8.5%) followed a "safe" verdict at the last turn. Overall the verdicts are well calibrated:
- `home why=stand_ok` was followed by death before the next turn on 129 of 561,854 trusted turns (0.023%);
- `ls=-1` on a turn that did not move was followed by death on 65 of 825,178 turns.

The misses come from four places:
1. the A3a cooldown blind spot;
2. unseen or untracked killers (A4);
3. warded bushes (A4);
4. the verdict describing the start tile, not the end tile.

On the last point: `ls` is evaluated where the turn began and `le` almost never. Farm and chase steps are checked only by the step guard, and A3b shows that guard is skipped under fuel pressure. 74 of the 258 moved off a tile rated `ls=-1`.

Of the 258, 207 died to a single enemy. 115 of those enemies were visible: mostly Marcella casts (A3a, A3c) and Heart of Ruin dash-landings.

### Not analysed, and open questions

- **`E` deaths** (stopping an enemy's game-ending tribute): 269 deaths, 9,627 gems, 67 games. These are sacrifices by design. Whether they paid off needs the enemy's tribute outcome.
- **A3c** above.
- **Excluded threats:** how many tracked unseen killers `credible_weight` dropped. Safety does not log which threats it excluded.
- **Retreat into warded bushes:** whether `retreat_step` picks bush tiles because of `damage_bound`. A level-2 trace does not include the per-candidate damage values.

## B. Movement

**Scope.** 624 distinct games (`games(distinct=True)`, all traced), trusted rounds only: 666k rounds and 2.81M champion turns. Code references are to `bots/hyperion/src` (identical to 5b02a02).

**Method.**
- An *idle* turn is one where the champion is alive and acting, ends where it started, and lands no hit, cast, tribute or capture share. Holding (`P`), altar waits (`W`), channels (`K`/`T`/`Q`) and spawn heals (`H`) are excluded.
- A *loop* is 10 or more consecutive turns that move at least 6 times, end within 2 tiles of where they began and achieve nothing.
- *Recall chains* come from the extract's `recall_start` / `recall_end` / `recall_cancel` events, joined with TE `recall`.
- *Lost captures* come from `capture_hold` / `capture_reset` / `capture` events.
- The bot's group index equals the extract's group id (checked on 524 of 524 `P` turns of 00f0c307-1).

| # | finding | cost (trusted turns) | games | class |
|---|---|---|---|---|
| B1 | Prism freezes at a camp with under 50 health left | 20.6k idle turns; 4.6k gems held untributed | 56 (9%) | decision rule |
| B2 | Dashers freeze at hole lines (00great_wall, 01islands) | 34.8k turns in episodes of 50+ turns | 86; every great_wall and islands game | decision rule (path model vs move) |
| B3 | Farm target flips with the crew value, which depends on visibility | 37.4k loop turns | 451 | mis-estimate |
| B4a | Capture recall lands one turn after payout: cancelled with 1 turn left, then restarted | 1,962 channel turns (491 restarts) | 276 | decision rule (stale `banking`) |
| B4b | Shop or bank keeps a recall while an enemy closes in | 61 deaths, 1,477 gems | 57 | decision rule |
| B5 | Captures lost after we held or cleared them | 639 groups, 19.1k gems | ~330 | mostly correct retreats; some decision rule |
| B6 | Standoff: a visible enemy freezes farming | 2.2k turns | 72 | decision rule |

Context for the turn costs: idle turns total 192k (6.8% of turns) and loop turns 138k (4.9%). Losses have more of both (idle 7.5% against 6.9% in wins; loops 6.4% against 4.0%). Most short idle runs are legitimate waits (respawns, crews). The findings below are the long, mechanical ones.

### B1. Prism freezes next to a nearly dead camp (spell-clear deadlock)

**Pattern.** A Prism chooses a group whose last attacker has a few health left. It stands at distance 4: outside the monster's reach (3) and its own attack range (3), but inside spell range (4). There it never acts again, for hundreds of rounds, while carrying its retained bag.

**Cause (decision rule: the farm's value model and the cast filter disagree).**
- `farm` picks the group as a spell clear: `kite < clear_rounds + heal` (bot.cpp:2234-2238). It values the group at its few remaining health points, so the value rises as the camp's health falls (v 0.906 to 1.688 in the second case).
- `spell_clear` (bot.cpp:1547-1583) stands on a tile in spell range and outside reach, and calls `hit()` → `cast_at_camp(world, g, attackers_only=true)`.
- In `camp_cast`, `attackers_only` makes `post_basic` false (abilities.cpp:398). So `all_visible` and `sole_finish` are false (399, 440), and the cast must be worth `min_camp_value` = 50 (abilities.cpp:20, 471-472).
- A cast is worth `min(raw, health)`, which is under 50, so it is refused. The basic attack is out of range, and `spell_clear` still returns true.
- A group with a live member never respawns, so nothing changes until something else interrupts.

**Cases.**
- **00f0c307-4** (01big_world, side b, vs Let's LARP again), Prism c5:
  - From r176 to r1115 (940 turns) it stands at 25,79 with 45 gems. Every turn has TE `farm best=19 steps=4`, no TA other than the routine recall, and `cd=0,0`.
  - Group 19 is a wolf at 26,75 (distance 4) and a gold cluster. The extract shows the wolf alive and asleep from r178 with 9.4 health until the trace ends.
  - The Prism's last camp cast was at r175 (`cast_with_result x=0,2,49 s=cast_camp`).
  - The same opening repeats in 8 other 01big_world games, all starting at r176 on the same tile.
- **09de3c49-2** (01concentrated_wealth, loss), Prism c5:
  - From r329 to r1195 (867 turns) it stands at 5,57 with 45 gems.
  - It cast at group 4 until r328: the extract shows 147.5 and 221.3 damage casts. From r329 the group's remaining health is 22.5 and the TE has `farm best=4 v=1.688 steps=4`.
  - The live members at 1,59 and 1,58 are at distance 4. No action follows.

**Frequency.** 84 Prism runs of 8 or more idle turns whose chosen group is alive with under 50 health: 20,602 turns in 56 games (44 of the runs in wins, 40 in losses).
- 34 runs last 100 or more turns (19,052 turns); the median is 49.
- 76 of the 84 carry gems (4,584 in all), so these bags also go untributed for the whole freeze.
- Other champion types show this only 5 times: it needs a caster that clears from out of reach.

### B2. Dashers freeze or ping-pong at a hole line

**Pattern.** On maps with one-tile hole lines between walls, a Heart of Ruin or Vesper chooses a target the bot rates 4-7 steps away. It walks to the hole's edge, then stands or alternates between two tiles indefinitely. While banking it carries its bag the whole time.

**Cause (decision rule: the path model counts a dash, but the move code never dashes).**
- A dasher's static fields treat crossable hole lines as open (`drop(s.dash_walls, s.crossable)`, world.cpp:821; "Our fields price a dash over a hole line", bot.cpp:2279). So farm and bank choose targets that only a dash reaches.
- The only dash that crosses is `dash_across` (self_abilities.cpp:294-310), used at bot.cpp:2281-2282 and 779. It drops every landing that `wakes_camp`. For Heart of Ruin, whose dash lands with an area hit, that is any landing within 1 of a live, sleeping, harmful monster (abilities.cpp:110-119).
- `dash_towards` refuses any goal within dash range ("a walk or two away", self_abilities.cpp:321).
- The walk (`descend` / `step_towards` / `step_safely`) cannot cross the holes, so the turn ends on the same tile or the next one.

**Cases.**
- **9fa0e422-2** (01islands, loss), Heart of Ruin c4:
  - From r315 to r1215 (901 turns, to the end of the trusted trace) it stands at 28,14. TE has `farm best=16 steps=7`, and there is no TA after the walk ended at r314.
  - Directly north (28,15 to 30,15) is a hole line. Every tile a 2-step dash could land on beyond it (28-30,16) is adjacent to the live sleeping camps at 28,17 and 29,17.
  - Its teammate Vesper c1 stood at 18,18 from r963 to r1214 on group 24 (`steps=4`; the elk is at distance 4 across the hole line at row 19). Its dash has no landing hit, so a different guard refused it. The trace does not show which one (candidates: self_abilities.cpp:308's progress test, :321).
- **28c601b7-5** (00great_wall, loss), Heart of Ruin c4:
  - From r432 to r1231 (800 turns) it alternates 30,16 ↔ 31,16, carrying 42 gems with `d=B`, `carry safe=0` and `TA move ... s=step_safely`.
  - The altar at 32,19 lies across the row-17 hole line. The candidate landing tiles at 29-31,18 are adjacent to camps at 29,19 and 30,19.
  - At r1231 it still carried the 42 gems; the game ended at r1232 with no tribute by it after r400.
- The same map shows a non-dasher variant: **03898b90-2** Marcella c7, from r298 to r358, alternates 34,20 ↔ 35,20 with a fixed target (group 4), and the TE `steps` alternates 60/61. The walk steps from the tile rated 60 to the one rated 61, so the walker and the farm's step count disagree. The cause is not determined.

**Frequency.** 210 idle or loop episodes of 50 or more turns by dashers: 34,768 turns in 86 games (46 wins, 40 losses).
- They occur in every 00great_wall game (20 of 20; 84 episodes, all Heart of Ruin) and every 01islands game (14 of 14). They are also in 8 of 17 00ambush games and 8 of 18 01fracture games.
- 98 of the episodes are banking (`B`), and 102 carry gems.

### B3. Farm target flips because the crew value depends on visibility

**Pattern.** On consecutive turns `farm` alternates between its own best group and crewing on an ally's claim (`shared`). It steps one tile toward each in turn and goes nowhere.

**Cause (mis-estimate).**
- A crew value exists only while the claiming ally is visible or has a fresh seen anchor (`work_arrival`, bot.cpp:1877-1881; `crew_work`, 1918-1944). The shared pick then overrides the best one (2270-2271).
- One step changes what we see (into a bush or behind a wall), so the shared candidate appears and disappears with our tile. Stickiness (2090) applies only to `farm_group`, not to the shared pick.

**Cases.**
- **2612381c-5** (00expanse), Ryth c9, r457-537 (81 rounds, 502 of 1300 health):
  - At 54,9: TE `best=10 v=0.347 shared=8 sv=0.509`, so it moves to 55,10 with `cr=1`.
  - At 55,10: `shared=-1`, so `best=10` and it moves back to 54,9.
  - Visible tiles alternate 231 and 240.
- **33916129-4** (01corridors), Marcella c2, r401-431:
  - At 30,3: `shared=7 sv=0.152` beats `best=11 v=0.125`, so it moves to 29,4 (a bush, `bu=1`).
  - At 29,4: `shared=-1`, so it moves back to 30,3.

**Frequency.**
- 2,575 farm-only loops with a group switch: 37,414 turns in 451 games. Most are short: 2,437 last 10-19 turns, and 9 last 50 or more.
- A-B-A farm-group flips within 6 turns: 5,910 in 579 games.
- Not every flip is this mechanism; the two cases are the ones checked.

### B4. Recall and shopping trips

**Context.**
- 27,385 recalls completed (44 per game): 12.0k capture, 10.5k home, 2.4k bank, 2.0k shop and 0.5k siege heal (TE `recall why` on the kept turns).
- Home recalls are mostly `why=low`: 8,342, median health 28%, in line with `recall_health_fraction` 0.35. This analysis does not judge them.
- Chains the bot kept and later cancelled itself wasted 11.2k channel turns (18 per game). The largest part is capture recalls (4.5k turns).

**B4a. A capture recall timed to land one turn after payout is cancelled with 1 turn left and restarted (decision rule).**
- `capture_recall` (bot.cpp:3173-3209) starts the recall while `world.round + channel >= payout` (3181). The capture pays at the start of the round before the recall would land.
- On that turn the champion no longer holds the capture, so `continue_recall` takes the non-holding branch (3985-3992). There `recall_to_bank` returns false at once because `memory.banking` is still false (3151). It becomes true only later in the same turn, in `carry_bag` (4050/4086).
- So the recall is cancelled with 1 turn end left. The champion steps toward an altar, and the turn-end recall is then kept for `bank` from the next turn: 5 more turn ends instead of 1.
- Cases:
  - **24d1a6f9-1** (00road_of_riches), Vesper c6: the capture is held from r71 and pays at r76. The recall is kept for `capture` on r73-75. At r76 TT r75 has no `bk`; the bot cancels with `left=1`, takes 1 `step_safely`, ends with `bk=1` and 8 gems, and keeps a new recall for `bank` from r77.
  - **00f0c307-1** (00stampede), Heart of Ruin c4: the recall is kept for `capture` up to r1797. At r1798 the bot cancels (`ch=rec:1`, gems 0 → 53, `bk=1` at the end) and keeps a new recall for `bank` from r1799. It lands at r1803 instead of r1799.
- Frequency:
  - 1,046 capture recalls were cancelled with 1 turn left, in 448 games. Pattern `PQQQB` accounts for 696 of them.
  - 491 of them (276 games) were followed at once by a new recall that completed: 1,962 extra channel turns.
  - The other ~555 gave up a ride that would have landed the next turn. The data does not show whether walking was better.

**B4b. A shop or bank keep ignores an approaching enemy (decision rule).**
- `continue_recall` keeps a recall for going home only when `!threatened && recall_outruns` (bot.cpp:3977), which requires no enemy able to walk into reach before landing (3161-3169).
- The shop and bank keeps (3986-3989) check only `threatened()` (`wants_shop` 3219, `recall_to_bank` 3153). `threatened()` is a probability that flips from turn to turn as enemies act (`ts=1` then `ts=0`).
- So a retreating champion alternates: a retreat step (`home_unsafe`, cancel), then a standing turn on a recall kept for `shop`, and so on. It moves at half speed toward safety, and the recall is never going to land.
- Cases:
  - **db84c66d-3** (01starvation), Prism c5, 60 gems, 80 health:
    - At r659 and r662: `home why=low`, `recall keep=0 why=home_unsafe`, a retreat step.
    - At r661 and r663: `recall keep=1 why=shop`, `ts=0`, no move. Marcella was visible at distance 3 (r661) and then hidden in a bush at distance 2.
    - Killed at r663 by that Marcella; 60 gems to the killer.
  - **2f411f8f-5** (01starvation), Prism c0, 204 gems, 137 of 1300 health:
    - Heart of Ruin was visible at 43,7, distance 4. Retreat steps at r1374-1375, then the recall was kept for `shop` at r1376-1377 with no move while the Heart of Ruin closed to 41,7.
    - The recall was cancelled at r1378. The Prism died at r1380; 204 gems to the killer.
- Frequency:
  - 61 of our deaths had a recall kept for shop (37) or bank (24) in the last 4 turns: 1,477 gems handed over.
  - 258 strict k-R-k alternations, in 169 games.
  - Damage, stun or death cancelled 224 of the 6,300 shop and bank chains.

### B5. Captures lost after we held or cleared them

- **Size.**
  - 341 gem groups were captured by the enemy after one of our holds (11,988 gems, 227 games).
  - 298 more were cleared by our hit but never held (7,115 gems, 185 games).
  - Together about 31 gems per game, against 24.8k clean captures of ours.
- **After a hold, by what our champions within 3 tiles did in the reset round:**
  - a death of ours in the window: 105 (3.6k gems);
  - a retreat `R`: 187 (5.8k gems; 146 games). Of these, `stand_lost` accounts for about 100 and `outmatched` for 76. 152 had at least one enemy within 4, and 129 had a single champion of ours there;
  - nobody of ours near: 21;
  - pulled away by a game-ender (`E`): 6 (1.0k gems).
- **Cleared but never held:** in 144 cases (2.9k gems) our nearby champion was farming elsewhere (`F`), and in 81 one of ours died.
- **Cases:**
  - **00f0c307-1** (00stampede), r903-914: a Prism at full health (700) holds the 160-gem group 10 alone. It retreats on `stand_lost` against a Vendetta at 697 health, steps back onto the tiles (`G`, r904), then leaves on `outmatched` when a 3500-health Marcella arrives (r905-906). The Marcella holds from r909 and takes 160 gems at r914. Given the fight, the retreat is sound. The loss is having one 700-health body on a 160-gem capture.
  - **1ad29aed-4** (01boss_battle, loss), r1238-1260: our Vesper holds the 400-gem Monolith from r1238. At r1241, two rounds before payout, it leaves (`TE ender e=1 gm=2498`, `d=E`, bot.cpp:4136-4138) to stop an enemy Vesper carrying 2,498 gems. It dies at r1245 with 49 gems. The enemy holds from r1255 and takes 400 at r1260.
  - **00f80df5-4** (00reverse_spiral), r131-147: our Prism clears the 7-gem cluster at 10,11, 3 tiles away, in passing, then walks off.
    - A level-2 re-trace (r130-136) shows `farm_cand g=12 v=0.000 steps=94 worth=0.0`. The group is on the enemy's side, and the enemy-ground discount (`home_ground`, `home_power`=2, bot.cpp:2087-2092) zeroes its worth.
    - The 94-step distance for a group 3 tiles away is unexplained.
    - The enemy took it at r147. Our champion 4 repeats this on the same group at r434 and r1206.
- **Class.** Mostly not movement bugs: retreats the fight sim calls right, and being outnumbered. The never-held cases come from a decision rule: discounted or ignored free captures nearby.

### B6. Standoff: a visible enemy freezes farming

**Cause (decision rule).** With an enemy in strike reach, `decide` runs the strike search (bot.cpp:4167-4190), which can choose to stand with no action. Because a search ran, `farm` skips its evaluation (`evaluated=0`, bot.cpp:2030) and only walks on toward last turn's group (2275). The step guard can forbid the tiles nearer the enemy.

**Case.** **bfabbed2-1** (00stampede, loss), Heart of Ruin c4, r1214-1954 (741 turns):
- It stands at 2,23, two tiles from the last two gold clusters of group 11, which are out of melee range.
- An enemy Heart of Ruin stands at 4,28 (distance 5) the whole time; it is also frozen.
- Every turn shows `decide strikes=1`, TS `seq=- tot=8.2`, `farm best=-1 evaluated=0/0`.

**Frequency.** 89 runs of 8 or more turns that are mostly `strikes=1`: 2,185 turns in 72 games. Outside this case they are short.

### Open questions and notes on the data

- **B2 Vesper.** Which guard refuses the Vesper's crossing is not determined. A level-2 trace does not log pathing internals.
- **B2 walker.** The non-dasher 60/61-step ping-pong on 00great_wall also needs a pathing look.
- **Endgame idle.** In the last ~100-150 rounds, champions with no group they can finish idle near spawn (`farm best=-1`, e.g. 01starvation r1857-2000). This was not pursued.
- **TT `d=k` is ambiguous.** It does not distinguish bank, shop, siege-heal and pocket keeps; read TE `recall why`.
- **Recall counts in the extract.** Because a recall starts at every turn end, the extract's `recall_start` / `recall_cancel` counts are dominated by the routine cancel; only chains with a TE `recall` keep, or a `recall_end`, are real recalls.
- **Harness.** Nothing looked wrong. One level-2 re-trace (00f80df5-4, r130-136) came back `rec EXACT ladder EXACT`.

## C. Combat

**Scope.** 624 distinct games (`games(distinct=True)`, all traced), trusted rounds only: 2.80M champion turns, 3,042 deaths of ours to champions and 4,746 enemy deaths to us. Code references are to `bots/hyperion/src` (identical to 5b02a02).

**Method.**
- A *kill window* is a turn of ours where a visible enemy (TB `v=1`, health plus shield from TB) is within an upper bound of what this champion alone could deal this turn. The bound uses Strength and Focus from the extract, the TT cooldowns, one cast per turn, walk and dash reach, Heart of Ruin's scale and Durability's -10%.
  - The bound ignores blockers and landing tiles, so a window is a candidate. Only the subsets marked *strict* need no movement or ability, or one step for melee.
  - 4,399 windows ended in our kill that turn. 215 more were turns we were stunned.
- *Rejected kills* are TS `kill=` entries outside the chosen `kl`.
- *Holds* are turns with a damaging or stunning slot ready (`cd=0`), a visible enemy in its reach and no cast.
- *Focus* uses the extract's attack and cast damage events per round.

| # | finding | cost (trusted) | games | class |
|---|---|---|---|---|
| C1 | Retreat turns skip the strike search, so one-hit kills in reach are walked away from | 119 strict turns (109 episodes), 74 of those enemies alive 3 rounds later; 287 candidate turns by the bound | 90 strict; 173 by the bound | decision rule |
| C2 | A kill earns a flat 300 over the target's health, so a late-game nuke on a healthy enemy beats a sure kill | 49 turns; in 26 neither target died within 3 rounds | 34 | decision rule |
| C3 | Retreat and channel turns hold nukes and stuns until death: the walk is priced at a flat 210 and a stun at a flat 80 | 603 deaths (20% of deaths to champions) with a ready nuke and the enemy in reach in the last 3 rounds; 42 with a ready stun on the killer itself | 260 / 40 | decision rule |
| C4 | Focus fire is mostly concentrated; the misses are C2 plus bush blindness | 35 rounds where spread damage would have killed if concentrated | 29 | decision rule / missing information |
| C5 | Spells spent on camps just before an enemy shows up | 251 episodes, 145 of those enemies alive 3 rounds later | 150 | mostly missing information |

### C1. Retreat turns walk away from one-hit kills

**Pattern.** When `want_home` says leave (health under 35%, `outmatched`, or a lost stand), the turn never runs the strike search. A visible enemy with less health than one basic attack is left alive while our champion walks or dashes away. Sometimes it is in range without moving; sometimes our own retreat step lands next to it.

**Cause (decision rule).**
- `play_turn` sends `leave` straight to `retreat()` (bot.cpp:4143-4159). `plan_strikes` (bot.cpp:4179) runs only on the non-leave path.
- `retreat()` (bot.cpp:4002-4022) has only these hits:
  - a basic attack before moving, for melee only (`walk_and_attack_independent`, :4008), and only on a target in range of the start tile (`attack_target`, self_abilities.cpp:152);
  - `cast_at_enemies(escape_step_value)` (:4009);
  - `reset_and_attack_enemy` after `dash_away` and the step (:4019, :4021). It needs the attack already spent and a reset ready (self_abilities.cpp:216-220).
- So a ranged champion (51 of the 53 strict ranged turns were Vesper) never basic-attacks on a retreat turn unless its reset is ready. Vesper could attack and then dash, since a dash spends neither the walk nor the attack, but `dash_away` comes first and no attack follows.
- A melee champion attacks from its start tile and then steps. The step never considers a tile next to a dying enemy, and the attack is not held for the post-step tile.
- `want_home` (bot.cpp:2724-2739) never asks whether a kill is available.

**Cases.**
- **4a126b66-5 r585** (00swirl), our Vesper c5:
  - It is at 27,14 with 456/1500 health: TE `home v=1 why=low`, `leave=1`.
  - The enemy Vesper (id 2) is at 29,11, distance 3: TB `v=1 hp=1/2100`. Our basic attack does 103.5 (extract, r584).
  - TA shows only `cast slot 1 → 25,16 s=dash_away` and `move 24,17 s=retreat_step`, with no attack.
  - The enemy started a recall the next round (TB r586 `ch=rec:591`). Our Prism, c4, killed it at r587: the kill came two turns later and from another champion, and could have been lost altogether.
- **77b4141d-4 r518** (00elkring), Vesper c1:
  - It is at 13,6 with 894/1000 health: TE `home v=1 why=outmatched` (5 enemies visible).
  - The enemy Vendetta (id 7) is adjacent at 14,7 with 16/1200 health (TB).
  - TA shows `dash_away` to 11,4 and `retreat_step` to 10,3. In r519 the Vendetta is at distance 5 with the same 16 health (TB) and is not killed.
- **2721e800-5 r44** (01yellow_brick_road), Heart of Ruin c9:
  - It has 210 health, TE `why=low`. The enemy Marcella (id 4) is at 22,9 with 8/1200 health, distance 2. The enemy Tavi (660 health) is adjacent.
  - TA: `attack x=1,3 s=attack_enemy` (41.8 on the Tavi), then `move 21,10 s=flee_camps`. 21,10 is adjacent to the Marcella.
  - Stepping first and then attacking would have killed her. Melee walk and attack are independent, but the attack was already spent.

**Frequency.** Strict windows (one basic attack kills; ranged in range without moving, or melee one step away), on turns with `d=R` and no TS:
- ranged: 53 turns in 37 games (44 episodes); 31 of those enemies were alive 3 rounds later;
- melee, one step: 66 turns in 59 games (Heart of Ruin 22, Vendetta 19, Marcella 13, Ryth 12); 43 alive 3 rounds later;
- by the looser bound (abilities included), 287 retreat turns in 173 games.

Melee kills at distance 1 never appear: `attack_target` takes them.

### C2. A flat kill premium loses to big hits on healthy targets

**Pattern.** The strike search finds a sure kill of a low-health enemy (TS `kill=`) but chooses a plan that kills nothing: a nuke or a full basic attack on a healthier enemy. It happens late, once Strength or Focus has grown (round quartiles 306/782/1006/1350/1959). Marcella's slot-1 nuke accounts for 27 of the 49 turns and Vesper's attacks for 14. The median skipped target had 370 health; the median chosen hit was worth 1,040.

**Cause (decision rule).**
- `hit_worth` (plan.cpp:100-105, and abilities.cpp:90-97 for casts) values a kill at `health + life_value (300) + 15/gem`. Damage that does not kill is worth its full amount (`useful_damage`, world.h:579-581) whatever the target's health, and whether or not it will heal: recalls heal fully at spawn.
- Once one action deals more than `target health + 300`, any non-lethal hit on a big target outscores finishing a small one.
- The search is per champion and scores only this turn (plan.cpp:1161-1226). It has no value for the enemy's 60 dead rounds, its lost recall, or the 100 gold.
- The tile pricing does remove the killed enemy's blows from the expected damage, but that is not enough here. In f974cb55-5 below the skipped target was recalling, so removing it saved nothing.

**Cases.**
- **c4fafdae-5** (00pilgrimage), Marcella c7:
  - r934: TS `kill=0:642.8;2:308.0`, so it can kill the enemy Marcella (383 health) or the Tavi (48 health, distance 3). It chooses `seq=s1:e4 raw=1040`: 1,080 on the Ryth at 2300/2300 (extract), which survives.
  - r950, the same again: the Tavi at 48 health, distance 3, `kill=2:308.0`. The chosen plan is `s1:e4` on the Ryth at 1220/2300, 1,080 damage, which does not kill. Neither enemy died in the next 3 rounds.
- **f974cb55-5 r1447** (01elk_arena), Vesper c1, Strength 535:
  - The enemy Ryth (id 7) is at distance 3 with 119/5000 health, recalling (TB `ch=rec:1451`).
  - TS `kill=7:419.3`, but the chosen plan is `seq=a:e9 raw=535.5`, an attack on the Marcella at 3194/4800 (also recalling).
  - The Ryth completed its recall and was not killed. The same pattern repeats at r1449 (`kill=7:419.3`, chose `a:e9`).
- **Sub-pattern, shield over kill** (7 turns, 6 games): Heart of Ruin shields at full health instead of a landing kill.
  - c5ed6517-4 r851: health 2424/2500. TS `kill=4:396.0` (a 2-health Ryth), but it chose `seq=sh tot=631.5 raw=14`.
  - 9954b27e-2 r1806: health 2000/2000. `kill=0:661.4`, but `sh tot=1361.1`.
  - `shield_at` (plan.cpp:573-575) prices the shield at 5 × `damage_bound(p)`. That bound includes the very enemy the alternative plan kills.

**Frequency.** 113 rejected kills in 59 games. 51 lost only to another kill (one cast, two targets: correct, for example 9317bf57-5 r695).
- In 49 turns (34 games) the chosen plan's value before damage exceeded the kill's and killed nothing.
- 32 of those skipped enemies survived 3 rounds. In 13 the chosen target died within 2 rounds (28cbe9ab-1 r306: the 490-damage hit set up a kill next round). In 26 neither died.
- It is rare per turn, but each one is a full kill (100 gold, bag, 60 rounds) forgone in a late game where the hits are huge.

### C3. Abilities held until death

**Pattern.** In 603 of 3,042 deaths to champions (20%, 260 games), the victim had a damaging or stunning slot ready with an enemy in its reach during its last 3 rounds and did not cast.
- By the last such turn's branch: 546 were retreats (`R`), 23 tributes, 18 game-ender intercepts and 11 recall turns.
- By slot: Prism ground 245, Marcella nuke 168, Prism stun 89, Ryth stun-area 69, Heart of Ruin landing 32.
- In 42 deaths (40 games) the held slot was a stun, the killer was in its range and not stun-immune, and the killing blow came within one round.

**Cause (decision rule).**
- On retreat turns `cast_at_enemies(world, escape_step_value)` (bot.cpp:4009) makes every excluding-walking cast beat `min_value + walk = 40 + 210` (abilities.cpp:18, 281; bot.cpp:33).
- Damage is worth its amount and a stun a flat `stun_value = 80` (abilities.cpp:16, 101-108). Early Prism and Ryth casts (Focus 80-100: 80-150 damage, plus 80 for a stun) therefore never clear 250.
- The one exception is the "free stun" (abilities.cpp:332): only when exactly one visible enemy can reach us next turn. A second enemy anywhere in strike reach disables it.
- Neither value asks whether the walk actually escapes, or whether the stunned enemy's next turn is the one that kills us.
- The base rate: 15,846 retreat turns had such a hold, and 9% died within 3 rounds. So the rule usually buys an escape. The trace cannot say whether casting would have saved the 546. The stun cases below are the clearest losses.

**Cases.**
- **bad729ff-3 r494** (00contest), Prism c5 (Focus 80):
  - It has 110/940 health, TE `why=low`, and `cd=0,0`. The enemy Ryth (id 3), 500/2200 health, is at 28,33, distance 3 from 30,30.
  - It walks to 31,31 (`retreat_step`) with no cast and no TE `cast`. By the rule, its stun was worth 1.5 × 80 + 80 = 200, under 250.
  - The free stun did not apply. Most likely the Marcella at 25,28 also counted as reaching; the trace does not log `n_reaching`.
  - r495 t0: the Ryth casts its area at 30,30, dealing 110 (extract), and our Prism dies. A stun at r494 would have removed that turn.
- **85ff5b52-5 r296** (00contest), Ryth c9 (Focus 100):
  - It has 154/1400 health, `why=low`, and slot 0 is ready (`cd=0,5`). The enemy Vesper (id 0, 264 health) is at 27,19, distance 4.
  - It hits the adjacent Heart of Ruin for 47 (`attack_enemy`) and steps away. By the rule the stun area on the Vesper was worth 100 + 80 = 180.
  - The Vesper dashes in at r296 t1 (80 damage) and kills it at r297 t0 (38.9).
- **Channel holds** (13 of the 42 stun deaths were `T`). A tributing Prism cannot cast without cancelling. `continue_tribute` keeps the channel whenever `tribute_ok` (bot.cpp:3948) and never weighs the stun.
  - 76b6692e-4 r1822-1826: a Prism (Focus 3,720) tributing 2,176 gems (`ch=trib:216`) keeps `tribute keep=1 why=safe` with the enemy Vesper (Strength 1,521) at distance 4. It dies in two hits; 2,176 gems go to the killer, and the game is lost.
  - That misjudgement is a tribute-safety problem (section D); the held stun only compounds it.

### C4. Focus fire

**What happens.** 17,324 rounds had at least two of our champions damaging enemy champions.
- In 12,407 (72%) every attacker's main target was the same enemy.
- 4,917 split; 4,393 of those had no kill by us.
- Counting only actions whose tile was within that action's range of the alternative target, concentration would have killed (damage dealt ≥ the target's health at round start) in just **35 rounds (29 games)**.

**What drives the choice.**
- Each champion runs its own search with linear damage values (C2). An assist has no value, and our turn order is bid only for a kill one champion can see coming (`offer_kills`, turn_order.cpp:174).
- On retreat and spawn-heal turns `attack_target` takes the weakest enemy in range (self_abilities.cpp:203-211), which concentrates by accident.
- Of the 35 misses, 25 are a Marcella or Prism nuke sent to a healthier enemy: the C2 valuation at team level.
  - 4928d148-4 r1375: Marcella's 1,809-damage cast could finish the Ryth at 292 health. TS `kill=2:552.2`, but it chose `s1:e3 raw=1769`. The Ryth died 2 rounds later, to another champion.
  - 00f0c307-1 r1301: three hits took the enemy Marcella from 1,399 to 528. Our Marcella's 1,161 cast went to another enemy.
- Others are missing information. 3f146df4-3 r758: our Vendetta took the enemy Vesper from 356 to 34. Our retreating Vesper c1 reset-attacked the full-health Ryth (5700/5700) for 184. The enemy Vesper at 22,21 stood in a bush: it is absent from c1's visible TB, and c3's next-turn TB shows `bu=1`. It escaped with 34 health.

### C5. Spells spent on camps just before a kill window

**Pattern.** 251 episodes (150 games): a Prism, Marcella or Heart of Ruin cast its nuke on a camp, then within the cooldown met an enemy that the nuke would have finished. 145 of those enemies survived 3 rounds.

**Cause (mostly missing information).**
- Camp casts already wait while a visible enemy is within 6 (`hold_range`, abilities.cpp:22, 396). Only 1 episode had the enemy visible that close at the cast.
- In 83 episodes the enemy was within 6 but unseen (fog or bush); for example, 14736a84-5 r1078, r1229 and r1344, where Marcella cast at camps with the enemy Vesper unseen at distance 4-6. The hold ignores tracked enemies that the bot believes are near.
- In 167 the enemy was farther away and arrived within the 8 rounds.

### Open questions

- **Kills the search did not find.** 165 turns (95 games) had a kill within the bound while the search listed none: 70 Heart of Ruin and 54 Vesper (53 of those at distance 4-5).
  - The bound ignores landing tiles and blockers, so most are probably infeasible.
  - 0f946dfa-3 r732-735 is unexplained: a Heart of Ruin adjacent to a 308-health, 42-gem Issac has its landing ready (1.5 × 172 Focus × 1.21 ≈ 312), yet TS offers only 3 walk tiles and no landing.
  - Level-2 detail does not log landing candidates, so a ban (`land_bad`: within 1 of a sleeping camp, plan.cpp:1146-1150) is a guess.
- **Tribute windows.** In 237 turns (46 games) a champion kept tributing with a killable enemy in reach (`tribute_ok`). Most were long channels where cancelling costs the progress. Whether any should break is a section D trade-off.

## D. Gems

**Scope.** The 624 distinct games, trusted rounds only (all 624 are traced). Code locations are in `bots/hyperion/src` (v38; `git diff 5b02a02` is empty). Scripts and per-game tables: the scratchpad `gems/` folder of this session (`scan.py` builds them).

- **Gem deaths:** 1,004 deaths with a bag, in 363 games, lost 84,764 gems. 81,780 went to the killer and 2,984 were destroyed by camps.
- **Gem totals mislead.** The 184 deaths with 100+ gems hold 61,935 of those gems (73%). Those big bags came 63% from capture shares and 37% from kills made while carrying, and most of the very largest (500 to 2,490 gems) are on `01boss_battle` and `00collision`, where bags pass from team to team through kills. So rank by deaths first and by gems second.
- **Tributes:** 17,640 tributes started, in 601 games, and 17,080 completed. The 491 that failed were cancelled by our own choice (173), by stuns (167), by enemy locks (115), or ended by our death (36). Another 69 were still running when the game ended.

| # | how the bag was lost | deaths | games | gems | median bag | median walk to altar / to spawn | cause class |
|---|---|---|---|---|---|---|---|
| D1 | Prism keeps its bag on purpose (`retaining_gems`) | 371 | 221 | 28,054 | 46 | 8 / 18 | decision rule |
| D2 | killed while tributing (26 of the 38 were winning bags on 16 to 218 turn channels) | 38 | 29 | 24,638 | 454 | 0 / 22 | decision rule |
| D3 | non-Prism carrier caught on the bank walk or the retreat | 393 | 207 | 20,446 | 22 | 9 / 21 | rule + missing info |
| D3b | ... the final hits began while chasing | 74 | 61 | 1,838 | 15 | 7.5 / 21 | decision rule |
| D3c | ... the final hits began while stopping an enemy game-ender (`E`) | 64 | 31 | 6,804 | 36 | 3 / 20 | decision rule (by design) |
| D5 | killed by a camp | 64 | 54 | 2,984 | 22 | 6.5 / 22.5 | mixed |

### D1. Prism carries its bag until the bag wins the game, and dies with it (37% of gem deaths)

**Pattern.** `retaining_gems` (bot.cpp:649) is true for Prism (`Passive::gem_focus`, +1.5 Focus per gem) whenever it carries gems, unless the bag wins the game (`winning_bag`) or the game is closing (`closing`). While it is true:
- `decide` never calls `carry_bag` (bot.cpp:4200).
- `can_tribute_safely` returns false (bot.cpp:3136), so even `retreat()` (bot.cpp:4002) never tributes, and `memory.banking` stays false.

So Prism farms with the bag, and when it must leave it walks to spawn. The bot made this trade on purpose.

**How often.**
- Prism loses 61% as many gems on death as it tributes: 46,399 lost against 76,492 tributed. For the other champions the figure is 5-14%: Ryth 0.05, Heart of Ruin 0.07, Vendetta 0.09, Marcella 0.11, Vesper 0.14.
- The 371 deaths where Prism never banked in its last 15 turns had carried the bag for a median of 231 rounds, at a median of 46 gems.
- In 124 of those deaths (10,806 gems), Prism had stood next to an altar with the bag earlier in the carry. Across all non-tributing Prism gem deaths, **1,105 farm (`F`) turns were spent standing next to an altar with the bag**: a tribute was a step away and was never considered.
- What the bot saw:
  - On its last turn, the killer was visible in 310 of the 371 deaths.
  - `want_home` gave `low` (250) or `outmatched` (55).
  - In 157 deaths it wanted to recall but cancelled the recall as `home_unsafe` (bot.cpp:3977).

**What the data cannot show.** It cannot measure the other side of the trade: the extra spell damage the Focus bought.

**Cases.**
- **bd7dbe97-1, 00lanes, r910, Prism (id 0), 53 gems. We lost the game 932-1002 at r1031.**
  - Prism carried this bag from r70 (840 rounds), with 44 farm turns next to an altar (r237-r855).
  - r902: `home why=outmatched` and `recall keep=0 why=home_unsafe`. It stepped toward spawn with `retreat_step`.
  - r903: stunned (`st=1`, 266 damage) by the enemy Ryth (id 9). The bot saw it at 23,9, in a bush (`bu=1`), its stun slot just used (`rr=910,903`).
  - r904-r906: health fell 454 → 305 → 6, while the bot logged `home why=low` and a `retreat_step` every turn.
  - r907-r910: on 6 hp it walked one tile a turn toward spawn, cancelling the recall each turn (`home_unsafe`), with the Ryth 1-2 tiles behind.
  - It died at 18,3, **one step from a tribute tile and 14 from spawn**. The Ryth took the 53 gems.
- **db8a3f68-2, 00swirl, r745, Prism, 72 gems.**
  - It had carried the bag for 325 rounds, with 12 farm turns next to an altar.
  - The final hits began on a farm turn (r739). At that turn the killer, a Vesper, was not visible: its last fix was at r736, 8 tiles away.
- **The same rule caps Prism's tributes.** Prism starts a tribute only once the bag wins the game or the game is closing. So its tributes are long: Prism started 311 of the 363 tributes longer than 20 turns. Of those 311, 173 completed, 77 were cancelled by our choice, 27 by a stun, 9 by a lock, 6 ran until the game ended, and 19 ended in Prism's death.

### D2. A winning bag is tributed "at any risk", whatever the channel length (26 deaths, 21,656 gems)

**Pattern.** `any_risk` (bot.cpp:656) is true when `winning_bag` is. Then `tribute_ok` (bot.cpp:660) is true, so:
- `submit_here` (bot.cpp:669) starts the tribute;
- `continue_tribute` (bot.cpp:3936) keeps it every turn, logging `TE tribute keep=1 why=safe`.

This holds whether the channel lasts 1 turn or 218 (`ceil(gems/10)`). With an enemy already beside us, or a 200-turn channel, the tribute cannot finish, and keeping it still gives up the bag.

**Outcomes of winning-bag tributes (trusted):**

| channel | starts | completed | game ended first | stunned | locked | died |
|---|---|---|---|---|---|---|
| 1-10 turns | 221 | 188 | 31 | 2 | 0 | 0 |
| 11-50 | 53 | 30 | 1 | 9 | 2 | 11 |
| 51+ | 32 | 6 | 0 | 9 | 2 | 15 |

- 26 of the 36 deaths while tributing were winning bags, in 19 games (10 on `01boss_battle`).
- What the bot saw at the start: in 10 of those 26 no enemy was visible, and in the others the nearest visible enemy was 1-8 tiles away.
- On the final turn of every death while tributing, the trace shows `keep=1 why=safe`, including 18 hp with an enemy adjacent.

**Cases.**
- **3f146df4-3, 01boss_battle, Marcella (id 2), 1,086 gems at the start; we were at 658.**
  - r1097: `carry safe=0 close=1`, and it submitted a 109-turn channel (`chq=trib:109`). Vesper and Tavi were visible 7 tiles away.
  - It kept the channel for 46 turns while standing in camp fire (`cs=76`): health fell from 2522 to 639 by r1138.
  - The enemy Ryth (8,500 max hp) walked from 20,24 to 23,21, next to it.
  - r1142: 18 hp, still `keep=1 why=safe left=64`.
  - r1143: killed. The Ryth took 1,486 gems, because captures paid during the channel had added 400.
  - We won anyway, 1160-378.
- **76b6692e-4, 01boss_battle, r1820, Prism, 2,176 gems, a 218-turn channel.**
  - No enemy was visible at the start, and it died 6 turns in (r1826) to a Vesper.
  - The same game also has a Vesper with 1,976 gems (r973, a 198-turn channel started at 186/1500 hp with a Prism 4 tiles away, died r990) and a Marcella with 1,573 gems (r946, a 158-turn channel, died r956).
  - We lost that game 60-938, at the round limit.
- **Cause class:** decision rule. The comment above `any_risk` reasons that the tribute is the bag's last chance; it does not weigh whether a channel of that length can finish.
- **Upstream cause:** bags grow far past what a channel can safely bank. D1's retention, monolith shares of 100-200, and bags taken by kills all feed this. Tributes of 100+ gems complete only 371 times in 639 starts, against 97% overall.

### D3. Non-Prism carriers caught walking, on the bank walk or the retreat (393 deaths, 20,446 gems)

The 393 include up to 19 Prisms that were banking rather than retaining.

**Pattern.** The carrier's health declines over its last few turns until it dies. For each death, the turn just before the first hit of that final decline shows what the bot was doing (`TT d`):
- banking (`B`) in 187 deaths;
- already retreating (`R`) in 166;
- chasing (`C`) in 74;
- stopping a game-ender (`E`) in 62.

**What the bot saw:**
- When the final decline began on the bank walk, the killer was unseen in 90 of the 190 `B` cases: in a bush or the fog. That part is missing information; `step_safely` and the step guard price only threats the bot can see.
- When it began in a retreat, the killer was visible in 244 of the 302 (`R`, all champions) cases, mostly 2-4 tiles away.
- Once health drops below 35%, `want_home` says `low`, and two rules apply:
  - `continue_recall` refuses the recall (`home_unsafe`, 149 deaths);
  - `retreat()` tributes only if `tribute_safe` passes, and otherwise walks or dashes toward **spawn** (`pathing.to_ally_spawn()`, bot.cpp:4018-4022), a median 21 steps away, while the nearest altar is a median 9 steps away.

**Case: 28cbe9ab-4, 00collision, Vesper (id 4), 671 gems, 1153/2800 hp. We lost 425-1010.**
- r1476-r1478: `carry safe=0 close=1`, walking toward an altar 18 steps away. A 7,200-hp enemy Marcella stayed in view about 6 tiles off.
- r1486: `home why=stand_lost lethal=1` and `recall keep=0 why=home_unsafe`. It retreated.
- r1489: stunned (`st=1`).
- It died 3 steps from spawn, with a bag that needed a 68-turn channel.

**D3b. Chasing while carrying** (`carry_bag`, bot.cpp:4047). When the tribute is not safe, `carry_bag` chases. `prey()` (bot.cpp:3006, accepted at bot.cpp:3105) takes any chase whose fight sim is not lost; the length of the chase and our bag never enter the decision. The kill's value (`life_value` plus the target's gems) only orders the candidates.
- **Case: 03898b90-2, 00great_wall, Marcella (id 7), 38 gems.**
  - r622: a lone Ryth with 0 gems came into view 2 tiles away. The 1v1 sim said we win in 10 turns and they never kill us (`prey_fight t=0:0:10:0:1:1 take=1`).
  - r622-r629: it chased for 8 turns (`d=C`), the sim counting down `0:0:9`, `0:0:8` and so on. Its health went from 1410 to 1032; the Ryth's went from 1700 to 635, alive.
  - From r630 it banked, then retreated (`R`) from r631.
  - It was killed at r636 by the enemy Vesper (id 1), 8 steps from an altar and 48 from spawn. The chase sim had counted only the Ryth (`key=100004`: one enemy).
- **Frequency:** across all trusted carrying turns there are 12,507 chase episodes. 344 of them (2.8%) were followed within 15 rounds by the carrier dying with its bag (17,617 gems in those bags). The trace cannot say how many of those deaths the chase caused.

**D3c. `stop_game_ender`** (bot.cpp:3278) sends carriers into the enemy whatever their bag, as designed: "nothing we gain meanwhile counts". 64 deaths, 6,804 gems.

### D4. Tribute cancels: the tribute safety check models only death, not stuns or locks

**Pattern.** `tribute_safe` (bot.cpp:375) checks two things over the next `min(turns, 6)` turns:
- whether last round's damage rate would kill us;
- `Safety::turns_to_kill_idle` (safety.cpp:2247), a damage-only simulation against the enemies in sight.

Nothing in it checks for a stun, which cancels a tribute (and Ryth's stun is a ground-target area that also hits targets it cannot see), or for a lock placed within 2 of the altar. The bot never reads enemy consumables (the World reads only placed locks, world.cpp:1786), although the rules say a visible champion exposes its items.

**Outcomes of failed tributes, followed to the next tribute or death:**

| cancel | count | stunner or locker at tribute start | afterwards |
|---|---|---|---|
| stun | 167 (106 games) | Ryth 102, Heart of Ruin 21, Marcella 19, Prism 10, Tavi 9, Cassi 6. 55 visible, stun ready, within 6 tiles; 6 visible and ready beyond 6 tiles; 37 visible but on cooldown; 69 unseen. | banked after a median 8 rounds (127); died with the bag first (37) |
| lock | 115 (63 games; 00contest 27) | 60 visible within 7 tiles (32 within 3); 52 unseen; 3 were our own lock (below) | banked after a median 30 rounds (95); died first (17) |
| our choice (`hurt` 71, `home` 66, `fight` 35) | 173 (89 games; 01boss_battle 33) | 98 of the 173 were channels of 21+ turns | banked after a median 45.5 rounds (100); died first (71) |

The failure rate climbs with channel length. Tributes that are not winning bags fail 1.1% of the time at 1-5 turns, 4.8% at 6-10, 32% at 11-20 and 35% at 21-50; of the 69 at 51+ turns, only 18 completed.

**Cases.**
- **6d6e0961-3, 00swirl, r375, Vendetta (id 3), 15 gems, a 2-turn channel.**
  - The strike plan dashed it to 22,11 (`seq=w@23,9|d@22,11|a:e5`). Then `carry safe=1` and it submitted.
  - At that moment the enemy Ryth (id 6) was visible at 19,11, 3 tiles away, with its stun ready (`TB rr=375,375`). The turn's own `ts=1` and `le=338` flagged the tile as threatened.
  - The Ryth cast at r375 t3 and stunned it (event `stun:[1,3]`). The tribute was cancelled with 1 turn left, Vendetta took 342 damage, and it lost its r376 turn: `st=1`, plus two refused `submit_gems` with `rc=45`.
  - It re-tributed at r377 and banked at r379.
- **2612381c-1, r1657, Heart of Ruin (id 10), 200 gems, a 20-turn channel.** The enemy Ryth was visible 3 tiles away at the start, and it placed a lock at r1659, cancelling the channel.

**Our own locks** (`place_lock`, bot.cpp:142) pay off:
- We placed 2,811. 115 of them cancelled an enemy tribute, holding 20,323 gems; enemies spent five attacks each destroying 1,712.
- 3 of ours cancelled an ally's tribute. `place_lock` checks allied channels only through `ally.channel`, which is not current for an unseen ally.
- The enemy placed 905 locks and cancelled 110 of our tributes.

### D5. Camps (64 deaths, 2,984 gems destroyed)

- The victims were 33 Prisms, 12 Vespers, 9 Marcellas, 5 Vendettas, 4 Ryths and 1 Heart of Ruin. On the last turn, `low` triggered in 58 of the 64 deaths (`flee_camps`, `retreat_step`).
- The final hits began while farming (`F`, 25), banking (17) or retreating (8).
- The large ones were sieges of big groups with a 150-340 gem bag:
  - a0bf6932-1 r639, a Prism with 200 gems;
  - 41157050-5 r665, a Prism with 223 gems;
  - c197828c-5 r569, a Prism with 343 gems flipping B/R under camp fire at 60 hp.
- They are minor next to D1-D3.

### D6. Out-of-fuel turns on the ladder

**Volume.**
- **Ladder truth** (extract `turn=6`): 4,169 turns of ours ran out of fuel, in 385 of the 624 games.
  - Over half of them (2,258) fall in untrusted rounds: a recorder `@x` is itself an out-of-fuel artefact and ends trust.
  - So the trace explains 1,911 turns, in 383 games.
- **The ladder `.fuel` files** show 6,496 turns at exactly 100,000. The extra 2,327 used the whole budget yet did not roll over, consistent with the README's "an import completes at 0 fuel" note.
- **Phase:** all but 30 ran out in the `decide` phase (`OOF <round> decide` lines; 28 unmatched, 2 in warm-up).
- **Branch at the abort:**
  - `F` farm: 828;
  - `-`: 562 (the strike search running with an enemy in strike reach, before any branch letter is set);
  - `k`: 191 (the routine recall was cancelled, then the turn ran out);
  - `A`: 154 (after the strike search attacked);
  - `B`: 99 (banking).
- **What was lost:** 1,131 of the 1,911 turns took no action at all in their round. 1,505 had an enemy within 8 tiles.

**What it cost.**

1. **The opening.** 741 of the 1,911 were in rounds 1-99, 306 of them in rounds 1-4 (102 games).
   - Nearly all of the round 1-4 ones are farm (`F`, 292), and 233 lost the whole turn.
   - Every game on `01big_world` (22/22), `00ambush` (17/17) and `01yellow_brick_road` (17/17) has them, as do 12/16 on `01starvation` and 10/21 on `00reverse_spiral`.
   - Example: c33d9c82-1. At r3 the Vendetta ran out after `farm evaluated=28/28`, and at r4 the Prism ran out the same way (`@o 3 2 556 4`, `@o 0 3 529 5`).
   - Each one costs a champion its first walk to a camp.
   - Cause class: mis-estimate (fuel). The farm's first full evaluation does not fit the turn's budget.

2. **Repeating loops in standoffs.** 434 turns fell in streaks of 3 or more consecutive out-of-fuel turns, nearly all strike-search turns (`d=-`, `strikes=1`).
   - When a turn runs out, the stale rest of it resumes in the next round and throws (`TT ok=0`). The new turn then repeats the same search and runs out again (main.cpp:115-121; plan.cpp:1623).
   - **b0a77e05-2, 00reverse_spiral:** Prism (id 4) stood on our spawn at 16,14 at full health (`mend=1` at r89 places it on spawn). Enemies were 2 tiles away, outside it.
     - It ran out in 7-turn streaks repeating every 8 rounds from r75 to r184. Its only completed turns were the ones it started stunned (`st=1`, which skips the search).
     - It lost 119 turns in the trusted window.
   - **c33d9c82-1, 01yellow_brick_road:** Vendetta (id 3) lost 33 consecutive turns (r317-r349) standing at 18,16 at about 1,622/2,000 hp.
     - Camps hit it for 38 a round at the start (r316 `cs=38`, 1735 → 1622 hp).
     - Enemies were 3-6 tiles away, including a 640-hp enemy Vendetta it had listed as prey at r316 (`cand=9:0.27:640`).
     - The streak ended only when it walked off at r350.

3. **Gems: small.**
   - 289 of the turns that ran out were carrying a bag (80 of them banking).
   - Only 4 were followed by a death with gems within 3 rounds (429 gems); 33 by any death.
   - Example: 978b7171-1 r1124. A Prism with 363-384 gems (`close=1`) ran out in `carry_bag`. It resumed, retreated on `stand_lost` at r1126, and was killed at r1127 by a Heart of Ruin hidden in a bush, 46 steps from an altar. The lost turn was not decisive.
   - No turn that ran out cut a tribute short. A channel turn does little work: none of the 1,911 is a `T` turn.

### Data notes

- `TE tribute why=safe` covers both `tribute_safe` and `any_risk` (trace-bot bot.cpp:4013), so the trace cannot tell a judged-safe keep from an at-any-risk keep. D2 inferred any-risk from the score plus the bag.
- `games(distinct=True)` keeps 5 pairs that look like the same game under different replay hashes: same map, side, opponent, length and scores, for example 44b62730-5 and 5d30179b-4, with identical event counts and deaths. Rates here include both.
- The EXAMPLES "(e) Gem losses" channel column (`rec:5`) is the every-turn recall (`start_recall`), not an attempted escape. Use `TE recall keep=` instead.
