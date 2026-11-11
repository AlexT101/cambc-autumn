# ATLAS: macro refactor of charybdis (2026-11-11)

Every A/B: `tools/ab.py CAND variants/charybdis-ref --no-test-draft --fuel 200000`, release builds, fast runner native,
`maps/macro-dev` (5,120 fresh ladder-v2 maps, 10,240 games) unless noted. Holdout: `maps/macro-holdout` (2,560 games) +
`--suites ladder,gen,fresh`.

## 1. Where charybdis-vs-charybdis games are decided (measured)

1,000 distinct mirror games (`maps/macro-sp`, a random 1,000 of macro-dev; charybdis vs charybdis-ref = identical code,
exactly 50.0%). Winner vs loser per game (P = share of games where the side with more of it won):

| metric | winner | loser | P(win \| more) |
|---|---|---|---|
| kills | 6.5 | 2.0 | 0.88 |
| deaths | 3.1 | 8.9 | 0.14 |
| gems lost at death | 58 | 271 | 0.11 |
| Prism deaths | 0.1 | 1.3 | 0.04 |
| Prism gems lost | 28 | 195 | 0.04 |
| champion damage dealt | 18.3k | 12.6k | 0.77 |
| lifetime gold | 5.6k | 4.3k | 0.80 |
| captured gems own half / enemy half / middle | 759 / 127 / 150 | 690 / 70 / 76 | 0.66 / 0.75 / 0.74 |
| Prism Focus at r300 | 478 | 388 | 0.64 |

Games last 838 rounds on average; 2.2% reach round 2000. 11.3 champion kills a game (pair deaths counted twice).

Deaths to champions (11,331), context the round before:
- 74% die on their own half; the losers' deaths outnumber the winners' about 2:1 in every 200-round bin from the start.
- Mean enemies within 4 / 8: 1.38 / 2.64; allies within 4 / 8: 1.16 / 1.77 -- allies are usually near, but only 0.84
  allies hit an enemy champion in the 10 rounds before the death.
- Prism deaths (1,424, mean bag 150; 521 with 100+ gems, mean bag 373): 46% by a single attacker, 60% with no ally
  hitting an enemy in the 10 rounds before.

Reading: the game is decided by fights, specifically by bag transfers when a Prism dies; allies are near but do not
fight. This matches the Fish study (research/ideas-2026-11-11/fishfight): the teacher-like team's edge is the whole pack
turning on the target, with ocean-code's pair, Willow and others hanging back or hitting camps.

## 2. Experiments

Prism-on-Prism kills (1,037 in 1,000 games) by the killer/victim Focus ratio the round before: below 1.5 (347 kills)
the victims carry 250-600 gems on average (the decisive events: a big Prism one-shot by an equal or *weaker* one);
above 3 (513 kills) they carry 15-60 (mop-ups). Late Prisms have Focus 700-1300, so one stun (1.5x) or AoE (1x, reach 5)
kills any champion. Lethal exposure: a champion standing (round snapshot) within one-cast lethal reach of a visible
enemy Prism with that slot ready dies within a round 34% of the time; ~14 such champion-rounds a game, and they account
for about two thirds of all Prism kills. Examples: a 748-gem Prism steps from distance 6 to 5 of a visible enemy Prism
and dies to its AoE (exactly its health); a Prism stands at 4-5 for two rounds hitting camps and is stunned for its health.

### Probes: one-knob directions (10,240 games each)

All level: the reference's constants sit at a local optimum, as expected; gains need structure.

| variant | change | win % (95% CI) |
|---|---|---|
| mo1-hp1 | home_power 1.89 -> 1.0 (less enemy-ground discount) | 50.3 (49.3-51.3) |
| mo1-hp0 | home_power 0 (no side discount) | 47.9 (46.9-48.9) |
| mo1-gv2 | gem_value x2 | 49.5 (48.6-50.5) |
| mo1-lv15 | life_value x1.5 | 49.8 (48.8-50.8) |
| mo1-ret15 | hurt/home retreat ratios x1.5 (give way less) | 50.5 (49.5-51.4) |
| mo1-wf | Willow's early fights all game | 49.2 (48.2-50.2) |
| mo1-ps1 | pursuit_steps 2 -> 1 | 49.9 (48.9-50.9) |

### Interim snapshots (before audit)

- mo1-fight-s1 (pair and Willow strike caution relaxed when engaged with an ally): 49.1% of 10,240 (48.1-50.1); OOF 609 vs 495.
- mo1-join-s1 (fight post in comms; allies within J=10 of a fresh post walk to it): 50.1% of 10,240 (49.1-51.1).
- mo1-join (final, audited; join episodes 5.3 a game, 57% arrive, 25% hit a champion): **49.2% of 10,240 (48.3-50.2)**;
  OOF 592 vs 498. Converging on fights does not pay, as in every earlier assist/summon attempt.

### Lethal-reach analysis (trace copy mo1-trace, debug, 1,000 games, trace side)

6,611 turn ends inside a visible enemy Prism's one-cast kill reach; 1,684 kills by that Prism; 76k gems lost.
`Safety::lethal()` models the reach correctly; the deaths come from model gaps:
1. Turn order after a stun (246 kills, 7.3k gems): a stunned enemy that has not acted still sets its priority, and the
   bot reads its stale next_priority, so `lethal()` assumes it acts after us; it takes the first slot and kills (44%).
2. The fight simulation aims all enemy damage at our weakest fighter (>=47 kills, 9.4k gems, mean bag ~200): a carrier's
   `self_falls` reads false while the enemy one-shots it.
3. `lethal()` adds one enemy turn; a stun then the next cast is not lethal to it (101 kills, 13.5k gems).
4. Retreat casts (walk-excluding) instead of a survivable step when no untouched step exists (81 kills, 5.7k gems).
5. Retreat at walking pace from a Prism whose cooldown is about to end (most of 550 no-walk-out kills, small bags).
Deliberate: `stop_game_ender` (3,747 exposures, 723 kills) and winning-bag tributes.
- mo1-fight (final, audited; Cassi/Issac relaxed ~22 turns a game each, Willow ~7): **49.5% of 10,240 (48.6-50.5)**;
  OOF 583 vs 483. Making the pair and Willow fight like ordinary champions when the pack is engaged is level.
  With join also level, the Fish "whole pack fights" lever does not transfer against the mirror.
- mo1-pz-s1 (lethal fixes 1, 2, 4 before audit): 50.5% of 10,240 (49.6-51.5); OOF 515 vs 484.
- mo1-pz35-s1 (lethal fixes 3, 5 before audit): 50.6% of 10,240 (49.6-51.6); OOF 800 vs 476.

mo1-pz-s1's first 1,000 games (the slowest maps) against REF: deaths 8.9 vs 9.4, Prism deaths 0.8 vs 1.0, kills 6.9 vs 6.5,
gems lost at death 167 vs 178; captures equal. The fixes work as meant but move few deaths.

### Big tributes (mirror, 1,000 games)
300+ gem tributes: 4,991 starts (93% Prism), mean channel 70 turns, **17% complete**; cancels: stun 877, manual 729,
lock 387 (of 2,009 in 500 games). Completion by enemies within 8 at the start: 0: 41%, 1: 12%, 2: 6%, 3+: 5%. Cancelled
attempts last 15 rounds on average: ~4 failed attempts a game cost the Prism ~60 rounds of farming. The winners' last
tribute: median 187 gems, mean 363 (43% of games end on a 300+ tribute).

### Deaths outside a visible Prism's single cast (trace copy mo1-trace2, 400 debug games, macro-px200)
1,108 deaths (31k gems) remain after Prism single casts (521) and camps (79):
- Retreat chase-downs: 552 deaths (12k gems); triggers stand-lost 273, pack zone 163, recall line 85; the pursuer keeps
  pace from behind, spawn 12-40 away; ranged victims fire 0.85 times in ~6 retreat turns. 163 of 308 Vesper kills and
  194 of 364 pair deaths.
- stop_game_ender (deliberate) 170; two-turn bound missing the second slot's spell (threat_strike) 59; stunned last
  turn 78; turn order under-predicted 68; unseen attacker 98.
- Pair: in 66% of pair deaths the two bodies were 6+ apart.
`lethal(end)` with no non-lethal tile in reach: 42% die before the next turn; lethal with a safe tile available: 16%;
not lethal but fight lost: 1.9%; won: 0.11%.

Enemy Prism with both slots down (2+ rounds) and our champion within 5: 9,692 rounds in 400 games; we damage it in 18%.
- Shopping probe (Prism carries ~110 / 233 / 308 unspent gold at r300 / 500 / 800): shop_gain_scale x2 (mo1-sg15) 48.2% of
  3,582 and x4 (mo1-sg30) 46.6% of 3,608, stopped early as losers. More trips home cost more than the shards return.
- mo1-pz-s2 (fixes 1, 2, 4, audited): 50.6% of 5,967 (stopped to free CPU for the merge; s1 was 50.5% of 10,240).
- mo1-pz35-s2 (fixes 3, 5, audited): 50.2% of 6,984 (stopped; the merge's audit found a double-counted stun turn in it).
- mo1-c1 = pz + pz35 merged, with two merge fixes (retreat_step demotes lethal steps when fix 4 hands it the walk) and
  the stun_follow_up double count fixed.
- **mo1-c1-s1: 51.0% of 10,240 (50.0-52.0)**; OOF 763 vs 481 (2x fuel).
- mo1-c1 held out: **51.0% of 3,840 (49.4-52.6)**: macro-holdout 51.1% of 2,560, ladder 52.7% of 256, gen 51.2% of 512,
  gen-s1 49.2% of 512. Committed to bots/charybdis as the first checkpoint.
- mo1-rt (death-march test on retreat: stand or step to an ally when the walk home is predicted fatal; earlier retreat;
  two-turn bound with the second slot's spell; on charybdis): 50.3% of 10,240 (49.4-51.3); OOF 588 vs 520. Marches flagged
  6.9 a game (38% of flagged episodes die within 15 rounds under REF behaviour), but standing instead is level.
- mo1-press (on c1: an enemy whose damaging slots are on cooldown for 2+ rounds becomes prey when the pack's damage over
  that window kills it; no retreat from a verdict that rests on it): 51.1% of 10,240 (50.1-52.1) = c1's 51.0%; OOF 1192 vs
  523. Level on top of c1; not kept.
- mo1-c1 against REF in its first 1,000 kept games (slowest maps): deaths 9.3 vs 9.6, gems lost at death 224 vs 252,
  Prism gems lost 141 vs 158, kills 7.0 vs 6.7, captures and Focus equal. The fixes save bags, not farming.
- mo1-c2 = c1 + rt merged (plus `ally_step` skips lethal tiles; march memos keyed on stun reads).
- mo1-c2 (c1 + rt): **50.9% of 14,080** (dev 50.9% of 10,240; holdout 51.1% of 2,560; ladder 50.8; gen 52.3; gen-s1 49.2);
  OOF 1144 vs 648. Equal to c1 with more code and fuel: rt adds nothing on top of c1.
- mo1-press-s2 (press with the audit fixes, on c1): 51.5% of 10,240 (50.5-52.5); OOF 1071 vs 471.
- mo1-c1 on a further fresh suite (maps/macro-x1, mapgen seeds 83000-83009, ladder-v2): 51.8% of 5,120 (50.4-53.1). c1 pooled over dev + holdout + standard + x1: 51.2% of 19,200.
- **mo1-press-s2 held out: 51.9% of 8,960 (50.9-53.0)**: macro-holdout 52.2% of 2,560, macro-x1 51.5% of 5,120, ladder
  52.7%, gen 53.1%, gen-s1 53.1%; OOF 945 vs 455. On the same held-out maps c1 scored 51.4%. Pooled with dev: 51.7% of
  19,200. Committed to bots/charybdis.

## 3. Final design (bots/charybdis = mo1-press-s2)

charybdis's macro was left as it was (the Prism carry, funnel and holds from macro1-6); every structural macro lever tried
on top of it (zone weights, fight convergence, whole-pack engagement, shopping cadence) was level or lost against the
mirror. What won was measuring *where bags are lost* and correcting the model that decides when a champion stands
within an enemy's reach, then exploiting the windows where the enemy's one-shot is unavailable:
1. Turn order after a stun: a stunned enemy that has not acted can take its team's first slot next round, so it gets a
   turn before ours when its strike reaches us (turn_window.cc).
2. The fight simulation aims an enemy turn that can kill the watched fighter at it, not at our weakest member (a carrier's
   `falls` no longer reads false while the enemy one-shots it) (safety.cc act()).
3. `lethal()` adds the follow-up turn after a stun that lands before our next turn (stun then cast).
4. Retreat with no untouched step falls back to a survivable step instead of a walk-excluding cast; `retreat_step`
   demotes lethal steps when it is handed that walk.
5. Retreat from an enemy whose lethal slot returns within two turns ranks steps by distance beyond its coming reach.
6. Press: an enemy whose damaging slots are on cooldown for 2+ of its turns becomes prey when the pack's damage in that
   window (or the chase trade) kills it; stand-lost / pack-zone / guard verdicts that rest only on that target are
   replayed without it, while kill reaches of other enemies stay guarded.

## 4. Results summary (vs charybdis-ref, 2x fuel)

| candidate | dev (10,240) | held out | notes |
|---|---|---|---|
| c1 (fixes 1-5) | 51.0 | 51.0 of 3,840; 51.8 of 5,120 (x1) | |
| c2 (c1 + death-march) | 50.9 | 51.1 of 2,560 (+ std 50.9 of 1,280) | rt adds nothing |
| press-s2 (c1 + press) | 51.5 | 51.9 of 8,960 | **final**; OOF ~2x REF's at 2x fuel |
- mo1-trib (on c1: no long tribute start with an enemy within 8 seen in the last 3 rounds; hold released after 15 rounds): **50.0% of 10,240** vs c1's 51.0: holding the start loses; dropped.
- **Real budget (100k, default fuel), macro-holdout: press-s2 48.2% of 2,560 (46.3-50.2); OOF 33,052 vs 15,481 turns.** The 2x-fuel gain does not survive the real budget.
- Final (press-s2) on a further fresh suite maps/macro-x2 (seeds 83010-83019): **51.9% of 5,120 (50.5-53.2)** at 2x fuel.
  Pooled over everything at 2x: dev 51.5% of 10,240 + held out 51.9% of 14,080 = **51.7% of 24,320**.
- c1 at the real 100k budget on macro-holdout: 49.7% of 2,560 (47.8-51.7); OOF 18,486 vs 15,230. REF itself runs out on
  ~15k turns a 2,560 games at 100k: charybdis is fuel-bound at the real budget, and the fixes' extra work costs more there
  than they win.
- mo1-pressf (press-s2 with fuel floors: press off below 60k left, the fix 2-5 refinements off below 40k):
  2x fuel dev **51.4% of 10,240** (50.5-52.4; press-s2 51.5), OOF 722 vs 460; real 100k fuel on macro-holdout + macro-x1
  **49.7% of 7,680** (48.6-50.8; holdout 48.9 vs press-s2's 48.2), OOF 65k vs 46k. Same at 2x, less lost at 100k:
  committed to bots/charybdis as the final version.
- **Final (mo1-pressf = bots/charybdis) held out at 2x fuel: 52.2% of 8,960 (51.2-53.3)**: macro-holdout 52.4% of 2,560,
  macro-x2 51.9% of 5,120, ladder 52.3% of 256, gen 53.1% of 512, gen-s1 54.3% of 512; OOF 734 vs 468. With dev:
  **51.8% of 19,200**. At the real 100k budget: 49.7% of 7,680.

## 5. Lessons and open leads

- The mirror is an equilibrium for macro structure: every macro-level lever (side weights, convergence on fights,
  whole-pack engagement, shopping cadence, tribute start discipline, death-march stands) was level or lost. The gains came
  from tracing where bags are lost (one-cast Prism kills: 56% of kills) and fixing the model gaps there, each worth ~0.5.
- Fixing exposure changes deaths only ~5% (9.3 vs 9.6 a game) and lost bags ~11%; most kills come from fights both sides
  accept by design (game-ender stops, chase-downs that standing does not save).
- Fuel: charybdis is fuel-bound at 100k (REF itself runs out ~6 turns a game), so any added model work loses at the real
  budget unless made cheaper. Next: a per-subsystem fuel census of fixes 1-5 and the press at 100k, then cheaper versions
  (memoised lethal() per tile and turn, the stun follow-up from the Reach tables instead of a second Strike build).
- Unexplored: pair (Cassi & Issac) cohesion when either body is threatened (66% of pair deaths have the bodies 6+ apart);
  unseen-attacker deaths (98 in 400 games); the open-plan objective weighting gems held by the Prism (in draft/ code, left
  alone as out of scope).

Final against REF, first 1,000 kept dev games (the slowest maps, where fights pile up; CAND won 52.6% of them): kills 9.4 vs
8.6, deaths 11.7 vs 12.6, gems lost at death 235 vs 262, Prism deaths 1.1 vs 1.3, Prism capture gems 347 vs 328, own-half
capture gems 675 vs 664, tributed score 730 vs 677. The press converts disarmed enemies into kills (c1 alone: kills +0.3);
the bags kept feed a slightly larger Prism and more farming.
