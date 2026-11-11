# Loss episodes: where value is lost, clustered and priced

Set: replays/batch-20261111-190708-ab-oc-vs-ast-40k-ladder (128 games, 64 clusters, focus ocean); 128 games, ocean won 93. Each side's losses are split into disjoint episodes priced in gems (deaths: bag + kill gold/4 + dead time at the game's earn rate; camp deaths; camps lost to the enemy; stalls of 10+ rounds), tagged with the situation and clustered. Costs are per game; "excess" is ocean minus opponent in the same games, with a 95% cluster-bootstrap CI over map pairs or ladder groups. Examples are `analysis dir rROUND #champion (cost)`: open them with `py tools/replay/triage.py DIR --team NAME` (the game's turning points) or `py tools/replay/narrate.py` for a turn-level transcript.

Earn rate (gems per alive champion-round, both teams): mean 0.242, so a 60-round death costs about 14.5 gems of time.

## Cost by kind

| kind | ocean cost/game | opponent cost/game | excess | ocean in its wins | ocean in its losses |
| --- | --- | --- | --- | --- | --- |
| death | 328 | 578 | -250 | 219 | 618 |
| camp_death | 7.5 | 6.8 | 0.7 | 9.1 | 3.3 |
| camp_lost | 390 | 641 | -251 | 262 | 730 |
| stall | 9.0 | 2.3 | 6.7 | 12.0 | 0.9 |

## Top weaknesses: clusters by excess cost

Every episode kind, clustered by champion and situation (deaths: bag and what the victim was doing the round before the fatal damage began). Sorted by ocean's cost per game minus opponent's for the same cluster in the same games; clusters with fewer than 4 focus episodes or 3 games are left to the list of single expensive episodes below. "mix" gives each secondary tag's most common value among the focus episodes. cf columns: share of the cluster's focus bag gems that a recall in the safe window / a tribute at the last altar passed would have saved.

| situation | ocean n/game | opponent n/game | ocean cost/game | opponent cost/game | excess [95% CI] | mix | cf recall | cf altar | look at | examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| camp stolen (mid half): ours within 3, outheld | 0.16 | 0.08 | 13.4 | 4.4 | 9.0 [2.0 .. 16.6] | 4$ 15% | - | - | economy/capture.cc holding_capture / contest_capture; economy/crew.cc (who stays to hold) | 43c2b0345705e999 r1121 (264); bbc86a4a39cd18de r1479 (210); f8e2dedc858e9209 r706 (199) |
| Prism killed with 50-199 gems while walking with gems | 0.14 | 0.12 | 20.9 | 15.3 | 5.6 [-6.6 .. 18.4] | grouped, even+ 50%, seen 6+ 61%, own half 67%, held its ground 50%, heading toward an altar 44% | 30% | 0% | economy/bank.cc carry_bag / banks_bag (route and when to bank); combat/fight.cc want_home | 1209ecea09649572 r484 #2 (215); aaaa6b7034edc1fb r546 #4 (205); 79d1a727a02a6953 r475 #9 (205) |
| camp stolen (enemy half): ours left, outnumbered | 0.40 | 0.24 | 11.5 | 6.5 | 5.0 [0.3 .. 9.5] | 2$ 24% | - | - | economy/capture.cc holding_capture / contest_capture; economy/crew.cc (who stays to hold) | 15b6025c37e8c9bc r112 (162); 6b0c472dcd25fb04 r589 (103); 141eb78d88981184 r442 (94.2) |
| Issac killed with 50-199 gems while walking with gems | 0.03 | 0.01 | 4.2 | 1.1 | 3.0 [0.0 .. 6.6] | grouped, even+ 75%, seen <6 50%, enemy half 50%, walked toward them 75%, heading toward an altar 50% | 0% | 0% | economy/bank.cc carry_bag / banks_bag (route and when to bank); combat/fight.cc want_home | d72f9cdf83c97324 r739 #5 (155); e4680069dba8651e r872 #9 (137); 11b03c489d87bee7 r627 #9 (123) |
| Ren killed with 0 gems while farming | 0.04 | 0.00 | 2.4 | 0.0 | 2.4 [0.0 .. 6.1] | grouped, even+ 60%, unseen 100%, own half 60%, walked toward them 60%, heading elsewhere 60% | - | - | combat/fight.cc want_home (leave a camp under threat); economy/farm.cc farm (target risk) | f14b843fe317876e r977 #2 (69.5); f14b843fe317876e r342 #2 (69.3); f107fc9a888a2712 r913 #2 (67.0) |
| Ren killed with 0 gems while fighting | 0.08 | 0.03 | 4.0 | 1.7 | 2.4 [-1.6 .. 7.4] | grouped, even+ 50%, seen <6 60%, enemy half 60%, walked toward them 80%, heading elsewhere 60% | - | - | combat/plan.cc (strike search) and combat/fight.cc prey / chase_with_guard (who to engage) | dc8cdf53eec009f2 r821 #9 (93.8); dc8cdf53eec009f2 r605 #9 (61.1); e1a17978aba2f30e r696 #4 (56.4) |
| Vendetta killed with 0 gems while walking | 0.12 | 0.11 | 6.9 | 4.6 | 2.3 [-4.6 .. 10.8] | grouped, even+ 50%, seen 6+ 69%, own half 50%, walked toward them 44%, heading elsewhere 56% | - | - | model/safety.cc (threat model), combat/guard.cc guard_work / step_safely (step guard) | f14b843fe317876e r683 #1 (69.5); f14b843fe317876e r879 #1 (69.5); f14b843fe317876e r970 #1 (69.5) |
| Willow waiting 10+ rounds, by a tributing ally | 0.12 | 0.02 | 2.4 | 0.2 | 2.2 [0.1 .. 6.2] | r801+ 53%, then end 80% | - | - | combat/support.cc local_support / support_endpoint (who guards a tribute); economy/bank.cc banks_bag / retaining_gems (the bag size sets the tribute length, ceil(bag/10) turns) | eacc2cbad917081f r561 #11 (90.0); eacc2cbad917081f r482 #11 (87.5); eacc2cbad917081f r873 #11 (56.3) |
| Vendetta killed with 1-49 gems while fighting | 0.05 | 0.02 | 2.9 | 0.8 | 2.1 [-0.4 .. 5.0] | grouped, even+ 50%, seen 6+ 83%, own half 83%, held its ground 50%, heading toward an altar 50% | 4% | 0% | combat/plan.cc (strike search) and combat/fight.cc prey / chase_with_guard (who to engage) | 11b03c489d87bee7 r223 #7 (72.8); dc8cdf53eec009f2 r238 #5 (70.8); a0d6dc110cc8320d r424 #1 (64.9) |
| Issac killed with 1-49 gems while farming | 0.03 | 0.00 | 2.1 | 0.0 | 2.1 [0.4 .. 4.3] | grouped, even+ 100%, seen 6+ 50%, enemy half 50%, held its ground 100%, heading elsewhere 100% | 23% | 0% | combat/fight.cc want_home (leave a camp under threat); economy/farm.cc farm (target risk) | 1209ecea09649572 r349 #1 (77.7); e1a17978aba2f30e r117 #2 (76.8); 69f0866a2273b7a4 r416 #7 (61.4) |
| Cassi killed with 1-49 gems while farming | 0.04 | 0.02 | 2.5 | 0.9 | 1.6 [-1.0 .. 4.0] | grouped, even+ 60%, unseen 80%, enemy half 40%, held its ground 100%, heading - 60% | 0% | 0% | combat/fight.cc want_home (leave a camp under threat); economy/farm.cc farm (target risk) | ab565e3de0abbff6 r410 #5 (75.4); 9d2d008c21f11bb5 r334 #1 (75.1); 2f4f0ebb863a5af7 r458 #0 (72.9) |
| Varg killed with 1-49 gems while walking with gems | 0.03 | 0.00 | 1.5 | 0.0 | 1.5 [0.0 .. 3.4] | grouped, even+ 50%, seen 6+ 100%, own half 75%, walked away 50%, heading elsewhere 75% | 70% | 0% | economy/bank.cc carry_bag / banks_bag (route and when to bank); combat/fight.cc want_home | 55626665ecf01f7b r675 #4 (73.8); 98a968552cf2a6b6 r275 #5 (44.7); df92fecdcfbad9cf r1179 #3 (38.0) |
| camp invaded (own half): ours 21+ away | 1.76 | 1.55 | 59.1 | 57.7 | 1.4 [-22.3 .. 21.0] | 1G 21% | - | - | economy/farm.cc farm (target choice and map coverage); economy/altar_guard.cc guard_turn | 0545f0930f79f5fd r578 (201); 0545f0930f79f5fd r647 (201); a43dc6b485510689 r264 (177) |
| Cassi killed with 1-49 gems while fighting | 0.08 | 0.06 | 6.4 | 5.0 | 1.4 [-3.7 .. 6.1] | grouped, even+ 50%, seen 6+ 50%, own half 70%, walked toward them 60%, heading toward an altar 40% | 30% | 0% | combat/plan.cc (strike search) and combat/fight.cc prey / chase_with_guard (who to engage) | 3ec374f00f893fb4 r521 #7 (107); 12668382df513185 r600 #0 (98.0); 2808155bc4b9ba5d r120 #5 (97.7) |
| Vesper Vale killed with 1-49 gems while fighting | 0.05 | 0.03 | 3.4 | 2.2 | 1.2 [-2.6 .. 5.8] | grouped, even+ 50%, seen 6+ 67%, enemy half 50%, held its ground 67%, heading elsewhere 50% | 26% | 0% | combat/plan.cc (strike search) and combat/fight.cc prey / chase_with_guard (who to engage) | f107fc9a888a2712 r875 #0 (105); e5039182d3d0e6fc r315 #4 (75.1); 39cb63fd9cff1b73 r160 #6 (73.2) |
| camp stolen (enemy half): ours left at even numbers or better | 0.25 | 0.21 | 6.3 | 5.4 | 0.9 [-3.3 .. 4.8] | 2$ 28% | - | - | economy/capture.cc holding_capture / contest_capture; economy/crew.cc (who stays to hold) | 9bc4b25525eb2eb6 r165 (111); 6b0c472dcd25fb04 r723 (104); e4680069dba8651e r227 (64) |
| Heart of Ruin killed with 0 gems while farming | 0.04 | 0.03 | 2.1 | 1.3 | 0.8 [-1.6 .. 4.1] | grouped, even+ 80%, seen 6+ 60%, own half 80%, held its ground 80%, heading elsewhere 60% | - | - | combat/fight.cc want_home (leave a camp under threat); economy/farm.cc farm (target risk) | f14b843fe317876e r626 #3 (69.5); f14b843fe317876e r839 #3 (69.5); f14b843fe317876e r54 #3 (49.0) |
| Vesper Vale waiting 10+ rounds, by a tributing ally | 0.05 | 0.01 | 1.0 | 0.2 | 0.8 [0.0 .. 2.3] | r801+ 50%, then fight 67% | - | - | combat/support.cc local_support / support_endpoint (who guards a tribute); economy/bank.cc banks_bag / retaining_gems (the bag size sets the tribute length, ceil(bag/10) turns) | eacc2cbad917081f r886 #6 (33.8); eacc2cbad917081f r603 #6 (32.5); eacc2cbad917081f r574 #6 (28.8) |
| Issac killed by a Elk camp | 0.08 | 0.02 | 1.3 | 0.6 | 0.7 [-0.2 .. 1.9] | 0 gems 90%, camp only 80% | 0% | 0% | economy/camps.cc (camp damage and clear time), combat/fight.cc camp_exit_way, economy/farm.cc rated_beaten | 38061bba653b7fed r88 #9 (35.5); 6b0c472dcd25fb04 r771 #3 (33.0); 7c1aea3f400c9bfc r544 #9 (22.5) |
| Prism waiting 10+ rounds, by a tributing ally | 0.05 | 0.00 | 0.6 | 0.0 | 0.6  | r401-800 67%, then walk 33% | - | - | combat/support.cc local_support / support_endpoint (who guards a tribute); economy/bank.cc banks_bag / retaining_gems (the bag size sets the tribute length, ceil(bag/10) turns) | eacc2cbad917081f r526 #10 (28.8); eacc2cbad917081f r477 #10 (20.0); 2ca3cb865946166f r485 #4 (18.3) |
| Issac waiting 10+ rounds, by a tributing ally | 0.04 | 0.00 | 0.6 | 0.0 | 0.6  | r401-800 80%, then end 40% | - | - | combat/support.cc local_support / support_endpoint (who guards a tribute); economy/bank.cc banks_bag / retaining_gems (the bag size sets the tribute length, ceil(bag/10) turns) | eacc2cbad917081f r599 #8 (37.5); eacc2cbad917081f r575 #8 (27.5); 37500755903baa5b r630 #3 (4.2) |
| Heart of Ruin killed with 1-49 gems while fighting | 0.05 | 0.03 | 2.6 | 2.1 | 0.5  | grouped, even+ 67%, seen 6+ 50%, enemy half 83%, walked toward them 67%, heading toward an altar 50% | 9% | 0% | combat/plan.cc (strike search) and combat/fight.cc prey / chase_with_guard (who to engage) | 15b6025c37e8c9bc r539 #11 (65.5); 91c6f667f061ccf2 r730 #5 (60.4); e602d876d03a78ec r261 #5 (53.6) |
| Tavi killed with 0 gems while fighting | 0.03 | 0.02 | 1.4 | 1.0 | 0.5  | alone v2+ 50%, seen 6+ 75%, mid half 50%, walked toward them 50%, heading elsewhere 75% | - | - | combat/plan.cc (strike search) and combat/fight.cc prey / chase_with_guard (who to engage) | 2c0e25a59099b806 r457 #5 (55.7); 2da6dd41cca744d7 r900 #5 (55.1); b40f858f5a64b734 r406 #5 (41.5) |
| Cassi waiting 10+ rounds, by a tributing ally | 0.03 | 0.01 | 0.4 | 0.0 | 0.3  | r801+ 50%, then end 100% | - | - | combat/support.cc local_support / support_endpoint (who guards a tribute); economy/bank.cc banks_bag / retaining_gems (the bag size sets the tribute length, ceil(bag/10) turns) | eacc2cbad917081f r888 #7 (37.5); 37500755903baa5b r634 #2 (3.1); d682607acec53f47 r605 #1 (3.0) |
| camp contested (enemy half): ours left at even numbers or better | 0.14 | 0.11 | 6.2 | 5.9 | 0.3  | 2$ 17% | - | - | economy/capture.cc contest_capture / yield_capture; combat/plan.cc (fight on the tiles) | 76092ca28f466d1c r461 (178); df92fecdcfbad9cf r40 (69.5); e805c7539abd97e1 r1420 (67.2) |

The same without the champion (kind and situation only):

| situation | ocean n/game | opponent n/game | ocean cost/game | opponent cost/game | excess [95% CI] | mix | examples |
| --- | --- | --- | --- | --- | --- | --- | --- |
| any champion killed with 50-199 gems while walking with gems | 0.27 | 0.22 | 38.6 | 28.0 | 10.6 [-4.9 .. 29.2] | grouped, even+ 65%, seen 6+ 62%, own half 62%, held its ground 50%, heading toward an altar 44% | 1209ecea09649572 r484 #2 (215); aaaa6b7034edc1fb r546 #4 (205) |
| camp stolen (mid half): ours within 3, outheld | 0.16 | 0.08 | 13.4 | 4.4 | 9.0 [2.0 .. 16.6] | 4$ 15% | 43c2b0345705e999 r1121 (264); bbc86a4a39cd18de r1479 (210) |
| any champion waiting 10+ rounds, by a tributing ally | 0.41 | 0.05 | 6.1 | 0.4 | 5.7 [0.2 .. 15.6] | r401-800 52%, then end 58% | eacc2cbad917081f r561 #11 (90.0); eacc2cbad917081f r482 #11 (87.5) |
| camp stolen (enemy half): ours left, outnumbered | 0.40 | 0.24 | 11.5 | 6.5 | 5.0 [0.3 .. 9.5] | 2$ 24% | 15b6025c37e8c9bc r112 (162); 6b0c472dcd25fb04 r589 (103) |
| any champion killed with 1-49 gems while farming | 0.13 | 0.06 | 8.5 | 3.9 | 4.6 [0.2 .. 8.7] | grouped, even+ 76%, unseen 41%, enemy half 47%, held its ground 82%, heading elsewhere 71% | f14b843fe317876e r580 #1 (90.3); 1209ecea09649572 r349 #1 (77.7) |
| any champion killed with 200+ gems while waiting | 0.01 | 0.01 | 7.3 | 4.2 | 3.1 [0.0 .. 9.4] | grouped, even+ 100%, seen 6+ 100%, own half 100%, held its ground 100%, heading elsewhere 100% | eacc2cbad917081f r556 #9 (934) |
| any champion killed with 50-199 gems while holding | 0.02 | 0.00 | 2.1 | 0.0 | 2.1 [0.0 .. 5.5] | alone v2+ 50%, unseen 50%, own half 100%, held its ground 100%, heading elsewhere 100% | 4cef40e207e1c66d r415 #2 (169); 9d2d008c21f11bb5 r350 #3 (99.0) |
| camp invaded (own half): ours 21+ away | 1.76 | 1.55 | 59.1 | 57.7 | 1.4 [-22.3 .. 21.0] | 1G 21% | 0545f0930f79f5fd r578 (201); 0545f0930f79f5fd r647 (201) |
| any champion killed with 1-49 gems while holding | 0.04 | 0.02 | 3.4 | 2.0 | 1.3 [-1.8 .. 4.3] | grouped, even+ 40%, seen 6+ 60%, enemy half 60%, held its ground 80%, heading elsewhere 80% | 3b2d7fcab8f6c74e r850 #5 (104); f14b843fe317876e r738 #2 (97.3) |
| any champion killed with 50-199 gems while stunned/oof | 0.01 | 0.00 | 1.2 | 0.0 | 1.2 [0.0 .. 3.7] | alone v2+ 100%, seen 6+ 100%, mid half 100%, walked toward them 100%, heading toward an altar 100% | 1f67bc4a74a7dfe2 r925 #3 (156) |
| any champion killed by a Elk camp | 0.24 | 0.19 | 4.0 | 2.9 | 1.0 [-0.9 .. 4.1] | 0 gems 81%, camp only 71% | 38061bba653b7fed r88 #9 (35.5); d8b08736d8704f31 r139 #5 (34.5) |
| camp stolen (enemy half): ours left at even numbers or better | 0.25 | 0.21 | 6.3 | 5.4 | 0.9 [-3.3 .. 4.8] | 2$ 28% | 9bc4b25525eb2eb6 r165 (111); 6b0c472dcd25fb04 r723 (104) |
| any champion killed with 50-199 gems while tributing | 0.01 | 0.00 | 0.7 | 0.0 | 0.7 [0.0 .. 2.1] | alone v2+ 100%, seen <6 100%, own half 100%, walked toward them 100%, heading toward an altar 100% | 892cd5fdb9e76dec r240 #5 (89.2) |
| any champion killed with 50-199 gems while walking | 0.01 | 0.01 | 1.5 | 0.9 | 0.6 [-2.6 .. 3.5] | grouped, even+ 100%, seen <6 100%, own half 100%, walked away 100%, heading toward own spawn 100% | 2da6dd41cca744d7 r1126 #1 (187) |
| any champion idle 10+ rounds, farmable group in reach | 0.30 | 0.05 | 0.7 | 0.1 | 0.6 [0.1 .. 1.3] | r401-800 59%, then walk 79% | 6b7c1334478ca2cc r671 #3 (4.8); 9e1fa751ded0165c r931 #0 (4.6) |

ocean's single most expensive episodes (rare situations the clusters above leave out):

| game / round | episode | cost | tags |
| --- | --- | --- | --- |
| eacc2cbad917081f r637 #6 | Vesper Vale killed carrying 200+ gems while walking with gems, grouped, even+, killer seen <6 | 1225 | first hit r635, warned 5 rounds, walked away, heading toward own spawn, allies 8/16: 3/1, enemies 8: 1, altar 2 away |
| eacc2cbad917081f r556 #9 | Stellar killed carrying 200+ gems while waiting, grouped, even+, killer seen 6+ | 934 | first hit r553, warned 8 rounds, held its ground, heading elsewhere, allies 8/16: 3/2, enemies 8: 2, altar 4 away; recall from r545 would have landed (closest enemy 4) |
| eacc2cbad917081f r633 #10 | Prism killed carrying 200+ gems while tributing, grouped, even+, killer seen <6 | 934 | first hit r632, warned 4 rounds, held its ground, heading -, allies 8/16: 4/1, enemies 8: 1, altar 1 away |
| 2c71ae16710a9644 r859 | stolen 10G 2M group (enemy half): ours died | 702 | GGGGGGGGGGMM(25,24)e, our damage share 84%, 2 of ours v 3 within 8 at their hold |
| 81d634b193d0b505 r871 | contested 10G 2M group (own half): ours left, outnumbered | 702 | GGGGGGGGGGMM(25,24)e, our damage share 12%, 0 of ours v 1 within 8 at their hold |
| 2808155bc4b9ba5d r228 | contested 49G group (enemy half): ours within 3, outheld | 428 | GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG(15,14)o, our damage share 25%, 3 of ours v 2 within 8 at their hold |
| 2e38ef4da0a3ee32 r889 | contested 4$ 6E 10G group (mid half): ours left, outnumbered | 406 | $$$$EEEEEEGGGGGGGGGG(56,25)m, our damage share 41%, 0 of ours v 1 within 8 at their hold |
| eacc2cbad917081f r825 #9 | Stellar killed carrying 200+ gems while walking with gems, grouped, even+, killer seen <6 | 389 | first hit r824, warned 0 rounds, walked toward them, heading toward an altar, allies 8/16: 2/1, enemies 8: 2, altar 1 away |
| 2808155bc4b9ba5d r138 | contested 49G group (enemy half): ours died | 343 | GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG(15,14)o, our damage share 24%, 2 of ours v 3 within 8 at their hold |
| 0132ef020f46240e r857 | stolen 1M group (enemy half): ours died | 307 | M(32,18)e, our damage share 100%, 4 of ours v 4 within 8 at their hold |
| 2da6dd41cca744d7 r791 | stolen 4$ 6E 4G group (mid half): ours died | 301 | $$$$EEEEEEGGGG(24,18)m, our damage share 74%, 2 of ours v 6 within 8 at their hold |
| 2c0e25a59099b806 r451 #3 | Prism killed carrying 200+ gems while walking with gems, grouped, even+, killer unseen | 288 | first hit r451, warned -1 rounds, held its ground, heading toward an altar, allies 8/16: 1/1, enemies 8: 2, altar 7 away |
| 2a5b0266c773f40c r662 #9 | Prism killed carrying 200+ gems while walking with gems, grouped, even+, killer seen 6+ | 280 | first hit r662, warned 47 rounds, walked toward them, heading toward an altar, allies 8/16: 3/0, enemies 8: 3, altar 2 away; recall from r655 would have landed (closest enemy 4) |
| 2cd511553194f8e5 r947 #8 | Prism killed carrying 200+ gems while fighting, grouped, even+, killer seen <6 | 268 | first hit r947, warned 2 rounds, held its ground, heading elsewhere, allies 8/16: 1/0, enemies 8: 2, altar 15 away |
| 43c2b0345705e999 r1121 | stolen 8$ 4E 4G group (mid half): ours within 3, outheld | 264 | $$$$$$$$EEEEGGGG(24,58)m, our damage share 87%, 2 of ours v 4 within 8 at their hold |

## Deaths by situation

Death episodes only (killed by champions), one tag at a time. cost = bag + kill gold/4 + dead time.

**champion**

| champion | ocean deaths/game | opponent deaths/game | ocean cost/game | opponent cost/game | excess [95% CI] | examples |
| --- | --- | --- | --- | --- | --- | --- |
| Stellar | 0.04 | 0.00 | 11.7 | 0.0 | 11.7 [0.0 .. 32.9] | eacc2cbad917081f r556 #9 (934); eacc2cbad917081f r825 #9 (389) |
| Tavi | 0.11 | 0.05 | 7.1 | 2.3 | 4.8 [-3.4 .. 12.9] | 17dc196c089f5e36 r585 #2 (169); 17dc196c089f5e36 r758 #2 (138) |
| Ren | 0.42 | 0.35 | 24.3 | 21.3 | 3.0 [-11.0 .. 20.2] | 39cb63fd9cff1b73 r756 #11 (123); f14b843fe317876e r842 #2 (99.3) |
| Vendetta | 0.29 | 0.32 | 18.8 | 16.9 | 1.8 [-14.9 .. 19.2] | 21d63ca1685ad48d r826 #0 (146); e1a17978aba2f30e r292 #0 (119) |
| Varg | 0.09 | 0.11 | 5.1 | 15.4 | -10.4 [-36.8 .. 7.3] | 38061bba653b7fed r85 #11 (101); 55626665ecf01f7b r675 #4 (73.8) |
| Ryth | 0.16 | 0.48 | 9.7 | 25.4 | -15.7 [-28.8 .. -1.3] | 2808155bc4b9ba5d r163 #4 (174); e4680069dba8651e r781 #6 (91.0) |
| Willow | 0.32 | 0.62 | 16.3 | 38.8 | -22.5 [-43.3 .. -4.7] | 2808155bc4b9ba5d r85 #8 (173); 7d47850da36491d8 r426 #9 (72.1) |
| Heart of Ruin | 0.38 | 0.87 | 20.1 | 44.7 | -24.6 [-44.3 .. -5.6] | f14b843fe317876e r974 #3 (104); f14b843fe317876e r434 #3 (99.5) |
| Cassi | 0.79 | 1.33 | 59.0 | 88.8 | -29.8 [-55.0 .. -6.6] | 11b03c489d87bee7 r445 #8 (189); 2da6dd41cca744d7 r1126 #1 (187) |
| Marcella | 0.12 | 0.79 | 6.8 | 43.5 | -36.7 [-52.2 .. -21.2] | e46f69d9a5fd9ad2 r1195 #10 (129); f107fc9a888a2712 r1055 #1 (84.3) |
| Vesper Vale | 0.35 | 0.65 | 31.3 | 73.1 | -41.8 [-101 .. 1.1] | eacc2cbad917081f r637 #6 (1225); d92759cdc5e6a4e7 r751 #0 (143) |
| Issac | 0.67 | 1.31 | 52.2 | 94.0 | -41.8 [-76.2 .. -12.5] | eacc2cbad917081f r789 #8 (214); d72f9cdf83c97324 r739 #5 (155) |
| Prism | 0.55 | 1.00 | 65.4 | 113 | -47.8 [-91.6 .. -14.4] | eacc2cbad917081f r633 #10 (934); 2c0e25a59099b806 r451 #3 (288) |

**bag**

| bag | ocean deaths/game | opponent deaths/game | ocean cost/game | opponent cost/game | excess [95% CI] | examples |
| --- | --- | --- | --- | --- | --- | --- |
| 50-199 | 0.41 | 0.34 | 57.7 | 47.2 | 10.4 [-12.1 .. 36.1] | 1209ecea09649572 r484 #2 (215); aaaa6b7034edc1fb r546 #4 (205) |
| 1-49 | 1.74 | 2.38 | 127 | 173 | -45.6 [-101 .. 2.5] | eacc2cbad917081f r789 #8 (214); e1a17978aba2f30e r558 #2 (134) |
| 200+ | 0.06 | 0.16 | 35.7 | 91.6 | -55.9 [-99.0 .. -19.2] | eacc2cbad917081f r637 #6 (1225); eacc2cbad917081f r556 #9 (934) |
| 0 | 2.09 | 4.99 | 107 | 266 | -159 [-224 .. -94.9] | dc8cdf53eec009f2 r821 #6 (105); dc8cdf53eec009f2 r821 #9 (93.8) |

**doing before the first hit**

| doing before the first hit | ocean deaths/game | opponent deaths/game | ocean cost/game | opponent cost/game | excess [95% CI] | examples |
| --- | --- | --- | --- | --- | --- | --- |
| respawning | 0.01 | 0.00 | 0.4 | 0.0 | 0.4 [0.0 .. 1.3] | 0545f0930f79f5fd r485 #8 (56.7) |
| on spawn | 0.01 | 0.01 | 0.6 | 0.6 | 0.0 [-1.7 .. 1.7] | dc8cdf53eec009f2 r967 #6 (70.9) |
| ? | 0.00 | 0.01 | 0.0 | 0.3 | -0.3 [-0.9 .. 0.0] |  |
| stunned/oof | 0.03 | 0.08 | 3.0 | 4.1 | -1.1 [-4.2 .. 2.2] | 1f67bc4a74a7dfe2 r925 #3 (156); e1a17978aba2f30e r558 #2 (134) |
| idle | 0.02 | 0.04 | 1.7 | 2.9 | -1.2 [-5.0 .. 2.4] | e805c7539abd97e1 r1271 #2 (95.2); a0d6dc110cc8320d r321 #0 (66.1) |
| holding | 0.09 | 0.09 | 7.9 | 10.7 | -2.8 [-17.4 .. 7.8] | 4cef40e207e1c66d r415 #2 (169); 3b2d7fcab8f6c74e r850 #5 (104) |
| tributing | 0.02 | 0.02 | 8.6 | 12.3 | -3.7 [-26.8 .. 18.3] | eacc2cbad917081f r633 #10 (934); 892cd5fdb9e76dec r240 #5 (89.2) |
| waiting | 0.09 | 0.19 | 13.1 | 16.9 | -3.9 [-9.1 .. 1.9] | eacc2cbad917081f r556 #9 (934); 2a5b0266c773f40c r439 #6 (121) |
| recalling | 0.09 | 0.12 | 5.9 | 10.8 | -4.8 [-14.5 .. 1.2] | 27dd6e797c690d18 r756 #0 (120); f14b843fe317876e r842 #2 (99.3) |
| farming | 0.30 | 0.47 | 17.5 | 31.7 | -14.2 [-29.9 .. 0.2] | f14b843fe317876e r580 #1 (90.3); 1209ecea09649572 r349 #1 (77.7) |
| fighting | 0.93 | 1.55 | 63.2 | 105 | -41.5 [-76.9 .. -6.3] | 2cd511553194f8e5 r947 #8 (268); 2c26c9c2713e6178 r713 #9 (204) |
| walking with gems | 1.15 | 1.62 | 117 | 169 | -51.9 [-107 .. 1.1] | eacc2cbad917081f r637 #6 (1225); eacc2cbad917081f r825 #9 (389) |
| walking | 1.55 | 3.69 | 88.5 | 213 | -125 [-181 .. -75.0] | eacc2cbad917081f r789 #8 (214); 2da6dd41cca744d7 r1126 #1 (187) |

**numbers at the first hit**

| numbers at the first hit | ocean deaths/game | opponent deaths/game | ocean cost/game | opponent cost/game | excess [95% CI] | examples |
| --- | --- | --- | --- | --- | --- | --- |
| alone v2+ | 0.84 | 1.23 | 57.9 | 94.1 | -36.2 [-75.2 .. -6.9] | 2cd511553194f8e5 r333 #8 (170); 4cef40e207e1c66d r415 #2 (169) |
| alone v1 | 0.26 | 0.74 | 19.6 | 63.9 | -44.4 [-74.7 .. -20.0] | f8e2dedc858e9209 r502 #9 (194); 11b03c489d87bee7 r445 #8 (189) |
| grouped, outnumbered | 0.88 | 1.84 | 55.5 | 138 | -82.6 [-160 .. -27.8] | 9d2d008c21f11bb5 r253 #3 (145); ab565e3de0abbff6 r405 #7 (136) |
| grouped, even+ | 2.32 | 4.07 | 195 | 281 | -86.6 [-159 .. -24.1] | eacc2cbad917081f r637 #6 (1225); eacc2cbad917081f r556 #9 (934) |

**warning**

| warning | ocean deaths/game | opponent deaths/game | ocean cost/game | opponent cost/game | excess [95% CI] | examples |
| --- | --- | --- | --- | --- | --- | --- |
| unseen | 0.90 | 1.63 | 67.1 | 117 | -49.6 [-88.5 .. -16.8] | 2c0e25a59099b806 r451 #3 (288); c9a60da7bcbff4d9 r751 #3 (196) |
| seen <6 | 1.08 | 2.11 | 99.1 | 160 | -61.2 [-110 .. -10.1] | eacc2cbad917081f r637 #6 (1225); eacc2cbad917081f r633 #10 (934) |
| seen 6+ | 2.32 | 4.14 | 162 | 301 | -139 [-276 .. -39.0] | eacc2cbad917081f r556 #9 (934); 2a5b0266c773f40c r662 #9 (280) |

**half**

| half | ocean deaths/game | opponent deaths/game | ocean cost/game | opponent cost/game | excess [95% CI] | examples |
| --- | --- | --- | --- | --- | --- | --- |
| enemy | 1.18 | 1.45 | 82.8 | 102 | -18.9 [-60.2 .. 14.1] | 86ce70be5108ef0e r454 #4 (252); 2808155bc4b9ba5d r163 #4 (174) |
| mid | 0.58 | 1.28 | 53.8 | 89.2 | -35.3 [-71.6 .. -4.3] | eacc2cbad917081f r633 #10 (934); eacc2cbad917081f r825 #9 (389) |
| own | 2.54 | 5.15 | 191 | 387 | -196 [-316 .. -88.7] | eacc2cbad917081f r637 #6 (1225); eacc2cbad917081f r556 #9 (934) |

## Avoidable bag losses

Deaths with gems where the replay shows a rule-checked alternative, had the enemy acted the same. **recall window**: a killer was in the victim's sight with no damage or stun to it for 6+ rounds before the first hit, so a recall started at the window's start (5 turn ends; only damage or a stun cancels it) would have landed first; with an enemy within 4 during the window the recall may itself have drawn the attack, so those gems are also given apart. **altar**: within 40 rounds before dying it stood within 1 of an altar the enemy had not locked, carrying at least half the final bag, and a tribute started then (ceil(bag/10) turn ends; only a stun cancels it) would have completed before the death, with no stun on it in that span; split by whether an enemy was within 8 then (with one near, the tribute itself may have drawn the attack sooner). Look at: recall combat/fight.cc want_home / recall_line (recall on sight with a bag); economy/bank.cc continue_recall; altar economy/bank.cc banks_bag / retaining_gems / submit_here (bank at the altar passed).

| side | bag gems lost/game | recall window/game | gems | gems, no enemy within 4 in the window | altar, no enemy within 8/game | gems | altar, enemy within 8/game | gems |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ocean | 100.0 | 0.60 | 25.6 | 2.2 | 0.00 | 0.0 | 0.02 | 1.4 |
| opponent | 150 | 0.70 | 42.5 | 26.1 | 0.00 | 0.0 | 0.06 | 4.2 |

Largest ocean recall-avoidable deaths:

- eacc2cbad917081f r556 #9 Stellar bag 823: killer in sight from r545, no damage from r545 (closest enemy 4), first hit r553; waiting, grouped, even+, own half
- 2a5b0266c773f40c r662 #9 Prism bag 230: killer in sight from r615, no damage from r655 (closest enemy 4), first hit r662; walking with gems, grouped, even+, mid half
- 79d1a727a02a6953 r475 #9 Prism bag 160: killer in sight from r466, no damage from r468 (closest enemy 3), first hit r475; walking with gems, grouped, even+, own half
- aaaa6b7034edc1fb r546 #4 Prism bag 156: killer in sight from r528, no damage from r528 (closest enemy 4), first hit r539; walking with gems, grouped, even+, own half
- 2808155bc4b9ba5d r163 #4 Ryth bag 115: killer in sight from r152, no damage from r156 (closest enemy 3), first hit r163; walking with gems, grouped, even+, enemy half
- 4a7b580f0c9c39e9 r397 #6 Prism bag 114: killer in sight from r383, no damage from r383 (closest enemy 4), first hit r389; walking with gems, grouped, even+, enemy half
- 2808155bc4b9ba5d r85 #8 Willow bag 114: killer in sight from r76, no damage from r76 (closest enemy 6), first hit r84; walking with gems, grouped, even+, own half
- 17dc196c089f5e36 r758 #2 Tavi bag 94: killer in sight from r750, no damage from r751 (closest enemy 3), first hit r758; walking with gems, grouped, even+, own half

Largest ocean altar-avoidable deaths:

- 4cef40e207e1c66d r415 #2 Prism bag 125: by an altar at r392 with 101 (tribute 11 rounds, 2 enemies within 8), died 23 rounds later, holding
- 0545f0930f79f5fd r453 #7 Prism bag 68: by an altar at r445 with 68 (tribute 7 rounds, 1 enemies within 8), died 8 rounds later, walking with gems
- 2da6dd41cca744d7 r776 #3 Prism bag 4: by an altar at r766 with 4 (tribute 1 rounds, 3 enemies within 8), died 10 rounds later, walking with gems

## Death hazard by activity

Champion-rounds spent on each activity (analysis/macro.py turn classes) and deaths to champions whose fatal damage began right after that activity, per 1000 such rounds, so a side is not penalised for doing more of something. Gems = bag gems lost in those deaths.

| activity | ocean rounds/game | ocean deaths per 1000 | ocean gems lost/game | opponent rounds/game | opponent deaths per 1000 | opponent gems lost/game |
| --- | --- | --- | --- | --- | --- | --- |
| walking | 1414 | 1.10 | 5.1 | 1604 | 2.30 | 11.8 |
| walking with gems | 1141 | 1.01 | 57.1 | 909 | 1.78 | 82.9 |
| fighting | 222 | 4.18 | 16.4 | 219 | 7.11 | 21.7 |
| farming | 851 | 0.35 | 1.9 | 745 | 0.63 | 6.6 |
| waiting | 122 | 0.77 | 7.3 | 91.0 | 2.06 | 5.3 |
| recalling | 204 | 0.42 | 1.3 | 205 | 0.61 | 3.7 |
| holding | 185 | 0.51 | 2.4 | 179 | 0.48 | 6.0 |
| stunned/oof | 10.5 | 2.97 | 1.1 | 10.1 | 7.75 | 0.5 |
| idle | 58.7 | 0.40 | 0.3 | 43.3 | 0.90 | 0.5 |
| tributing | 72.2 | 0.32 | 7.0 | 52.8 | 0.44 | 10.9 |
| on spawn | 49.8 | 0.16 | 0.1 | 55.1 | 0.14 | 0.0 |
| ? | 0.0 | - | 0.0 | 0.0 | - | 0.0 |

## Bag exposure

Champion-rounds alive carrying a bag of each size, and deaths with that bag per 1000 such rounds (a hazard rate, so a side that carries more is not penalised for carrying).

| champion | bag | ocean rounds/game | ocean deaths | ocean per 1000 | opponent rounds/game | opponent deaths | opponent per 1000 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Cassi | 1-49 | 279 | 48 | 1.35 | 145 | 52 | 2.79 |
| Cassi | 50-199 | 6.0 | 7 | 9.13 | 4.8 | 4 | 6.47 |
| Cassi | 200+ | 0.3 | 0 | 0.00 | 0.0 | 0 | - |
| Heart of Ruin | 1-49 | 116 | 20 | 1.35 | 83.1 | 22 | 2.07 |
| Heart of Ruin | 50-199 | 14.7 | 1 | 0.53 | 10.0 | 2 | 1.57 |
| Heart of Ruin | 200+ | 0.2 | 0 | 0.00 | 2.3 | 1 | 3.40 |
| Issac | 1-49 | 276 | 50 | 1.42 | 128 | 70 | 4.26 |
| Issac | 50-199 | 6.7 | 5 | 5.79 | 3.0 | 1 | 2.60 |
| Issac | 200+ | 1.5 | 0 | 0.00 | 0.0 | 0 | - |
| Marcella | 1-49 | 35.9 | 8 | 1.74 | 105 | 31 | 2.31 |
| Marcella | 50-199 | 8.2 | 1 | 0.95 | 17.4 | 3 | 1.35 |
| Marcella | 200+ | 0.2 | 0 | 0.00 | 0.2 | 0 | 0.00 |
| Prism | 1-49 | 143 | 24 | 1.31 | 168 | 47 | 2.19 |
| Prism | 50-199 | 162 | 28 | 1.35 | 162 | 23 | 1.11 |
| Prism | 200+ | 90.9 | 5 | 0.43 | 102 | 13 | 0.99 |
| Ren | 1-49 | 87.6 | 18 | 1.60 | 45.9 | 17 | 2.90 |
| Ren | 50-199 | 5.8 | 1 | 1.34 | 2.1 | 2 | 7.38 |
| Ren | 200+ | 0.6 | 0 | 0.00 | 0.0 | 0 | - |
| Ryth | 1-49 | 79.0 | 11 | 1.09 | 60.0 | 16 | 2.08 |
| Ryth | 50-199 | 7.4 | 1 | 1.05 | 2.2 | 0 | 0.00 |
| Ryth | 200+ | 2.4 | 0 | 0.00 | 0.0 | 0 | - |
| Stellar | 1-49 | 6.8 | 1 | 1.15 | 9.4 | 0 | 0.00 |
| Stellar | 50-199 | 4.8 | 0 | 0.00 | 0.3 | 0 | 0.00 |
| Stellar | 200+ | 1.5 | 2 | 10.10 | 0.0 | 0 | - |
| Tavi | 1-49 | 35.6 | 5 | 1.10 | 5.9 | 0 | 0.00 |
| Tavi | 50-199 | 9.1 | 2 | 1.71 | 0.4 | 0 | 0.00 |
| Tavi | 200+ | 1.8 | 0 | 0.00 | 0.0 | 0 | - |
| Varg | 1-49 | 50.4 | 4 | 0.62 | 34.8 | 2 | 0.45 |
| Varg | 50-199 | 3.9 | 1 | 2.00 | 2.7 | 1 | 2.88 |
| Varg | 200+ | 0.0 | 0 | - | 1.3 | 2 | 11.70 |
| Vendetta | 1-49 | 99.9 | 16 | 1.25 | 66.9 | 15 | 1.75 |
| Vendetta | 50-199 | 11.1 | 2 | 1.41 | 7.1 | 1 | 1.11 |
| Vendetta | 200+ | 0.4 | 0 | 0.00 | 0.3 | 0 | 0.00 |
| Vesper Vale | 1-49 | 265 | 23 | 0.68 | 144 | 26 | 1.41 |
| Vesper Vale | 50-199 | 38.5 | 2 | 0.41 | 19.3 | 3 | 1.22 |
| Vesper Vale | 200+ | 10.3 | 1 | 0.76 | 9.9 | 5 | 3.97 |
| Willow | 1-49 | 70.6 | 8 | 0.88 | 50.1 | 21 | 3.27 |
| Willow | 50-199 | 1.7 | 1 | 4.59 | 3.4 | 4 | 9.26 |

## Fights lost

Engagements (analysis/fights.py) the side lost on net swing (kill gems + gold/4 - bags lost); these overlap the death episodes. numbers = own minus enemy champions within 8 at the start; absent = own champions 9-16 away at the start that never joined.

| numbers | initiator | help in reach | ocean lost/game | ocean gems/game | opponent lost/game | opponent gems/game | excess | examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| +2+ | they started | absent ally 9-16 | 0.09 | 42.3 | 0.25 | 22.6 | 19.7 | eacc2cbad917081f r632 (3946); 2da6dd41cca744d7 r1122 (277) |
| +2+ | we started | absent ally 9-16 | 0.08 | 7.9 | 0.06 | 4.8 | 3.1 | d72f9cdf83c97324 r308 (168); 12668382df513185 r497 (165) |
| +1 | we started | absent ally 9-16 | 0.14 | 15.2 | 0.21 | 13.1 | 2.1 | eacc2cbad917081f r824 (574); 2c26c9c2713e6178 r712 (352) |
| +1 | we started | no ally 9-16 | 0.18 | 16.7 | 0.21 | 16.5 | 0.3 | 86ce70be5108ef0e r450 (450); 39cb63fd9cff1b73 r753 (312) |
| +1 | they started | absent ally 9-16 | 0.24 | 19.4 | 0.33 | 20.8 | -1.4 | e4680069dba8651e r402 (216); 17dc196c089f5e36 r758 (216) |
| +0 | we started | absent ally 9-16 | 0.20 | 20.5 | 0.26 | 23.5 | -3.0 | 1209ecea09649572 r471 (371); 79d1a727a02a6953 r472 (345) |
| +2+ | we started | no ally 9-16 | 0.09 | 5.9 | 0.12 | 9.7 | -3.8 | f14b843fe317876e r965 (177); fafc377d239c9943 r373 (117) |
| -2- | we started | absent ally 9-16 | 0.15 | 7.8 | 0.21 | 13.1 | -5.3 | 2cd511553194f8e5 r328 (224); 3ec374f00f893fb4 r512 (122) |
| -1 | we started | no ally 9-16 | 0.08 | 7.5 | 0.23 | 13.7 | -6.2 | 21d63ca1685ad48d r811 (313); 55626665ecf01f7b r669 (191) |
| -2- | we started | no ally 9-16 | 0.08 | 4.2 | 0.16 | 11.3 | -7.1 | d22f2f4e5bee9181 r696 (206); 39cb63fd9cff1b73 r773 (73.2) |
| -1 | we started | absent ally 9-16 | 0.17 | 15.7 | 0.19 | 23.2 | -7.6 | ab565e3de0abbff6 r398 (264); e1a17978aba2f30e r552 (252) |
| -2- | they started | no ally 9-16 | 0.16 | 13.0 | 0.42 | 23.4 | -10.5 | e78aafafa3c3d4c8 r528 (298); 7d47850da36491d8 r356 (197) |
| +2+ | they started | no ally 9-16 | 0.18 | 10.3 | 0.33 | 21.2 | -10.9 | 37500755903baa5b r235 (227); 76092ca28f466d1c r156 (93.5) |
| +0 | we started | no ally 9-16 | 0.15 | 8.1 | 0.28 | 22.2 | -14.1 | dc8cdf53eec009f2 r819 (165); 366f684d81014eae r459 (111) |
| -1 | they started | no ally 9-16 | 0.16 | 11.5 | 0.37 | 29.0 | -17.5 | aaaa6b7034edc1fb r537 (311); d72f9cdf83c97324 r727 (145) |
| -1 | they started | absent ally 9-16 | 0.28 | 14.2 | 0.52 | 34.2 | -20 | 5afe2b85148652c8 r142 (165); 9d2d008c21f11bb5 r341 (137) |
| +1 | they started | no ally 9-16 | 0.16 | 9.8 | 0.42 | 39.5 | -29.7 | a0d6dc110cc8320d r642 (161); 1f67bc4a74a7dfe2 r436 (85.5) |
| +0 | they started | absent ally 9-16 | 0.40 | 26.8 | 0.73 | 59.1 | -32.3 | 11b03c489d87bee7 r428 (277); c36a929370706e72 r531 (183) |
| -2- | they started | absent ally 9-16 | 0.35 | 29.9 | 0.57 | 79.2 | -49.3 | 2cd511553194f8e5 r936 (420); f8e2dedc858e9209 r497 (331) |
| +0 | they started | no ally 9-16 | 0.25 | 18.3 | 0.59 | 68.1 | -49.8 | 2c0e25a59099b806 r451 (511); 4a7b580f0c9c39e9 r389 (253) |

Absent allies 9-16 away in lost fights, by what they were doing: ocean: walking with gems 140, walking 117, farming 63, recalling 29, holding 23, fighting 14; opponent: walking 245, walking with gems 179, farming 115, recalling 44, holding 29, waiting 17.

## ocean's losses against its wins

Cluster cost per game in the focus team's losses minus its wins (top 12): the situations that most separate a loss from a win. Partly reverse causality (a losing side is behind and fights at a disadvantage); the round column shows when they happen.

| situation | in losses | in wins | difference | median round |
| --- | --- | --- | --- | --- |
| invaded 1G group (own half): ours 9-20 away | 29.3 | 0.7 | 28.6 | 368 |
| invaded 2$ 2E group (own half): ours 9-20 away | 21.0 | 0.0 | 21.0 | 651 |
| stolen 10G 2M group (enemy half): ours died | 20.0 | 0.0 | 20.0 | 859 |
| contested 10G 2M group (own half): ours left, outnumbered | 20.0 | 0.0 | 20.0 | 871 |
| Prism killed carrying 50-199 gems while walking with gems, grouped, even+, killer seen 6+ | 19.5 | 2.2 | 17.3 | 475 |
| contested 30$ group (enemy half): ours within 3, outheld | 16.5 | 0.0 | 16.5 | 553 |
| invaded 1E 8G group (own half): ours within 8 | 16.5 | 0.0 | 16.5 | 407 |
| contested 49G group (enemy half): ours within 3, outheld | 12.2 | 0.0 | 12.2 | 228 |
| Issac killed carrying 0 gems while walking, grouped, even+, killer seen 6+ | 12.3 | 0.4 | 11.9 | 482 |
| invaded 5$ 4G group (own half): ours within 8 | 11.6 | 0.0 | 11.6 | 603 |
| invaded 1$ 4E 4G group (own half): ours 21+ away | 11.5 | 0.0 | 11.5 | 647 |
| contested 2E 14G group (mid half): ours within 3, outheld | 11.1 | 0.0 | 11.1 | 356 |
