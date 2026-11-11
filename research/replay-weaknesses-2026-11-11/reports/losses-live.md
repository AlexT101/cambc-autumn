# Loss episodes: where value is lost, clustered and priced

Set: /tmp/claude-1000/-home-ubuntu-cambc-autumn/1f5203f4-9fa0-4339-988d-e59ceccee865/scratchpad/live-src (351 games, 71 clusters, focus v115); 351 games, v115 won 235. Each side's losses are split into disjoint episodes priced in gems (deaths: bag + kill gold/4 + dead time at the game's earn rate; camp deaths; camps lost to the enemy; stalls of 10+ rounds), tagged with the situation and clustered. Costs are per game; "excess" is v115 minus opponent in the same games, with a 95% cluster-bootstrap CI over map pairs or ladder groups. Examples are `analysis dir rROUND #champion (cost)`: open them with `py tools/replay/triage.py DIR --team NAME` (the game's turning points) or `py tools/replay/narrate.py` for a turn-level transcript.

Earn rate (gems per alive champion-round, both teams): mean 0.251, so a 60-round death costs about 15.0 gems of time.

## Cost by kind

| kind | v115 cost/game | opponent cost/game | excess | v115 in its wins | v115 in its losses |
| --- | --- | --- | --- | --- | --- |
| death | 380 | 439 | -58.5 | 232 | 681 |
| camp_death | 8.8 | 14.1 | -5.2 | 5.4 | 15.8 |
| camp_lost | 346 | 542 | -196 | 254 | 532 |
| stall | 19.2 | 4.9 | 14.3 | 23.0 | 11.4 |

## Top weaknesses: clusters by excess cost

Every episode kind, clustered by champion and situation (deaths: bag and what the victim was doing the round before the fatal damage began). Sorted by v115's cost per game minus opponent's for the same cluster in the same games; clusters with fewer than 4 focus episodes or 3 games are left to the list of single expensive episodes below. "mix" gives each secondary tag's most common value among the focus episodes. cf columns: share of the cluster's focus bag gems that a recall in the safe window / a tribute at the last altar passed would have saved.

| situation | v115 n/game | opponent n/game | v115 cost/game | opponent cost/game | excess [95% CI] | mix | cf recall | cf altar | look at | examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Prism killed with 50-199 gems while walking with gems | 0.13 | 0.02 | 19.8 | 3.0 | 16.8 [10.4 .. 23.5] | grouped, even+ 39%, seen 6+ 55%, own half 61%, held its ground 39%, heading elsewhere 55% | 35% | 9% | economy/bank.cc carry_bag / banks_bag (route and when to bank); combat/fight.cc want_home | a1bb76d0e30e4e12 r734 #3 (239); f7872025c1cdc256 r685 #9 (235); 739e47e6c5d6a79b r939 #6 (226) |
| Willow killed with 0 gems while walking | 0.50 | 0.27 | 24.3 | 12.7 | 11.5 [4.3 .. 18.6] | grouped, even+ 64%, seen 6+ 55%, own half 63%, walked away 40%, heading elsewhere 50% | - | - | model/safety.cc (threat model), combat/guard.cc guard_work / step_safely (step guard) | e9b05b8f2f04b398 r759 #11 (85.9); e9b05b8f2f04b398 r837 #11 (85.9); 750f1fa065a099d2 r533 #3 (77.2) |
| Vesper Vale killed with 200+ gems while walking with gems | 0.01 | 0.01 | 13.1 | 3.0 | 10.1 [-0.6 .. 24.1] | grouped, even+ 60%, seen 6+ 80%, own half 80%, walked away 80%, heading toward own spawn 40% | 35% | 0% | economy/bank.cc carry_bag / banks_bag (route and when to bank); combat/fight.cc want_home | 80883ceb1a204744 r1445 #6 (2429); 3cdc157ddaf83093 r566 #0 (1188); 3cdc157ddaf83093 r385 #0 (490) |
| Prism killed with 50-199 gems while fighting | 0.06 | 0.01 | 9.1 | 1.4 | 7.8 [3.1 .. 11.7] | grouped, even+ 36%, seen 6+ 91%, own half 77%, walked away 55%, heading elsewhere 45% | 64% | 7% | combat/plan.cc (strike search) and combat/fight.cc prey / chase_with_guard (who to engage) | 3f2831555186c5a8 r727 #9 (219); 63bba97ea22a6068 r760 #3 (218); 3a98e2425423d8d5 r739 #3 (192) |
| Prism killed with 200+ gems while walking with gems | 0.03 | 0.01 | 12.2 | 5.0 | 7.2 [-2.5 .. 16.3] | grouped, even+ 64%, unseen 36%, own half 55%, held its ground 64%, heading elsewhere 55% | 32% | 0% | economy/bank.cc carry_bag / banks_bag (route and when to bank); combat/fight.cc want_home | 886f45d053e3ed0b r1134 #4 (714); 18985cd163da1935 r847 #1 (538); c39658a433012b02 r1011 #2 (534) |
| Prism killed with 1-49 gems while walking with gems | 0.11 | 0.01 | 7.6 | 0.7 | 6.9 [4.5 .. 9.4] | grouped, even+ 46%, seen 6+ 77%, own half 72%, walked away 44%, heading elsewhere 56% | 43% | 4% | economy/bank.cc carry_bag / banks_bag (route and when to bank); combat/fight.cc want_home | 736907973bbab604 r497 #9 (103); 14336e0f95fade82 r673 #10 (94.0); 18985cd163da1935 r1177 #1 (93.3) |
| Ryth killed with 0 gems while walking | 0.12 | 0.00 | 5.6 | 0.0 | 5.6 [3.1 .. 8.0] | grouped, even+ 46%, seen 6+ 73%, own half 68%, held its ground 54%, heading elsewhere 44% | - | - | model/safety.cc (threat model), combat/guard.cc guard_work / step_safely (step guard) | e8c78070419ffcce r389 #0 (72.6); b0b7ec1974f88205 r900 #0 (65.3); bcf614332cd62871 r905 #6 (64.0) |
| Prism killed with 200+ gems while fighting | 0.02 | 0.00 | 5.5 | 0.0 | 5.5 [1.8 .. 11.0] | grouped, even+ 50%, seen 6+ 67%, enemy half 67%, held its ground 67%, heading elsewhere 50% | 13% | 0% | combat/plan.cc (strike search) and combat/fight.cc prey / chase_with_guard (who to engage) | 99db761839ce5db1 r1028 #3 (402); 5481f825cb9703c5 r691 #8 (398); e6a4b314ab8199ba r678 #2 (338) |
| camp stolen (mid half): ours left at even numbers or better | 0.18 | 0.05 | 7.8 | 2.6 | 5.2 [1.0 .. 8.7] | 1G 39% | - | - | economy/capture.cc holding_capture / contest_capture; economy/crew.cc (who stays to hold) | 57bea7feb1beb6bb r551 (333); a191621af7141a1e r856 (295); d74428b0e1cacbe9 r450 (218) |
| Issac killed with 1-49 gems while fighting | 0.08 | 0.02 | 6.1 | 1.1 | 5.0 [2.8 .. 7.4] | grouped, outnumbered 36%, seen 6+ 61%, own half 68%, walked toward them 57%, heading elsewhere 64% | 31% | 0% | combat/plan.cc (strike search) and combat/fight.cc prey / chase_with_guard (who to engage) | 917b231327087a60 r426 #2 (110); 3c285506bc276552 r441 #5 (108); 93774a36baf85159 r699 #7 (100) |
| Cassi killed with 1-49 gems while walking with gems | 0.21 | 0.15 | 16.8 | 11.8 | 4.9 [1.1 .. 8.8] | grouped, even+ 36%, seen 6+ 67%, own half 65%, walked away 46%, heading elsewhere 39% | 44% | 0% | economy/bank.cc carry_bag / banks_bag (route and when to bank); combat/fight.cc want_home | c084b20552b4cd49 r484 #5 (139); 709a7797500145dd r110 #0 (139); c39658a433012b02 r891 #0 (128) |
| camp stolen (enemy half): ours left, outnumbered | 0.27 | 0.20 | 10.4 | 5.6 | 4.9 [1.2 .. 8.5] | 1G 14% | - | - | economy/capture.cc holding_capture / contest_capture; economy/crew.cc (who stays to hold) | 53ae4cf628dfcfd1 r619 (169); c084b20552b4cd49 r456 (164); 93cedd5ec874072d r1326 (163) |
| camp contested (enemy half): ours within 3, outheld | 0.11 | 0.11 | 12.1 | 7.3 | 4.8 [-3.6 .. 18.4] | 31$ 21% | - | - | economy/capture.cc contest_capture / yield_capture; combat/plan.cc (fight on the tiles) | d12a1150439eca01 r702 (672); df4a57af740f92b7 r897 (277); df4a57af740f92b7 r742 (244) |
| camp stolen (mid half): ours died | 0.21 | 0.15 | 12.1 | 8.2 | 4.0 [-1.9 .. 9.3] | 1G 27% | - | - | economy/capture.cc holding_capture / contest_capture; economy/crew.cc (who stays to hold) | 3cdc157ddaf83093 r387 (550); d74428b0e1cacbe9 r1160 (243); 058a1dbd7aa299ca r977 (210) |
| camp contested (mid half): ours left at even numbers or better | 0.13 | 0.14 | 10.6 | 6.7 | 3.9 [-0.5 .. 9.0] | 1$ 1W 13% | - | - | economy/capture.cc contest_capture / yield_capture; combat/plan.cc (fight on the tiles) | 80883ceb1a204744 r1469 (590); c0378644a669b963 r643 (307); df4a57af740f92b7 r865 (277) |
| Cassi killed with 1-49 gems while walking | 0.16 | 0.09 | 11.0 | 7.2 | 3.8 [-0.6 .. 8.4] | grouped, even+ 51%, seen 6+ 58%, own half 75%, walked away 47%, heading elsewhere 40% | 40% | 0% | model/safety.cc (threat model), combat/guard.cc guard_work / step_safely (step guard) | c084b20552b4cd49 r813 #5 (116); 4c8c45d16c4f33c1 r690 #1 (107); b193e3c42bc1af03 r741 #4 (106) |
| Prism killed with 1-49 gems while fighting | 0.06 | 0.01 | 3.6 | 0.3 | 3.3 [2.1 .. 4.8] | grouped, even+ 40%, seen 6+ 75%, own half 50%, held its ground 60%, heading elsewhere 55% | 32% | 0% | combat/plan.cc (strike search) and combat/fight.cc prey / chase_with_guard (who to engage) | 4c8c45d16c4f33c1 r826 #3 (87.3); 837f391c35fc9c74 r222 #3 (81.5); 6abd364ecd7c87af r113 #2 (78.8) |
| Prism killed with 0 gems while walking | 0.13 | 0.06 | 6.8 | 3.7 | 3.1 [-2.2 .. 7.8] | grouped, even+ 47%, seen 6+ 69%, own half 78%, held its ground 44%, heading elsewhere 62% | - | - | model/safety.cc (threat model), combat/guard.cc guard_work / step_safely (step guard) | 3cdc157ddaf83093 r558 #4 (93.1); 3cdc157ddaf83093 r768 #4 (93.1); e9b05b8f2f04b398 r669 #10 (85.9) |
| Ryth killed with 0 gems while fighting | 0.07 | 0.00 | 3.1 | 0.0 | 3.1 [1.7 .. 4.7] | grouped, even+ 46%, seen 6+ 88%, own half 77%, held its ground 54%, heading elsewhere 42% | - | - | combat/plan.cc (strike search) and combat/fight.cc prey / chase_with_guard (who to engage) | f6a4b684c23e5cd7 r1117 #4 (64.9); 744ee64d0dd5fa6f r538 #0 (57.8); ff36550a4dd15170 r80 #0 (54.2) |
| Ren killed with 1-49 gems while fighting | 0.05 | 0.00 | 3.0 | 0.0 | 3.0 [1.4 .. 4.5] | grouped, even+ 44%, seen 6+ 67%, own half 50%, held its ground 50%, heading elsewhere 61% | 36% | 0% | combat/plan.cc (strike search) and combat/fight.cc prey / chase_with_guard (who to engage) | bcf614332cd62871 r817 #11 (79.0); c5647b655c498581 r673 #9 (78.8); 67eba95ff7cefbe2 r458 #6 (72.1) |
| Prism killed with 0 gems while fighting | 0.06 | 0.01 | 3.1 | 0.4 | 2.7 [1.2 .. 4.6] | grouped, even+ 50%, seen 6+ 77%, own half 73%, walked toward them 41%, heading elsewhere 41% | - | - | combat/plan.cc (strike search) and combat/fight.cc prey / chase_with_guard (who to engage) | 3cdc157ddaf83093 r670 #4 (92.8); e9b05b8f2f04b398 r751 #10 (85.7); e9b05b8f2f04b398 r995 #10 (85.7) |
| Willow killed with 0 gems while fighting | 0.13 | 0.07 | 5.7 | 3.0 | 2.7 [0.2 .. 5.5] | grouped, even+ 51%, seen 6+ 51%, own half 62%, held its ground 38%, heading elsewhere 47% | - | - | combat/plan.cc (strike search) and combat/fight.cc prey / chase_with_guard (who to engage) | e9b05b8f2f04b398 r678 #11 (85.9); bc187adc11113353 r636 #3 (71.8); b193e3c42bc1af03 r631 #7 (61.7) |
| Willow waiting 10+ rounds, by a tributing ally | 0.20 | 0.00 | 2.5 | 0.0 | 2.5 [1.4 .. 3.9] | r401-800 58%, then walk 31% | - | - | combat/support.cc local_support / support_endpoint (who guards a tribute); economy/bank.cc banks_bag / retaining_gems (the bag size sets the tribute length, ceil(bag/10) turns) | 3cdc157ddaf83093 r478 #5 (47.2); 80883ceb1a204744 r553 #11 (36.1); 80883ceb1a204744 r1078 #11 (36.1) |
| Ryth killed with 1-49 gems while walking with gems | 0.04 | 0.00 | 2.3 | 0.0 | 2.3 [1.0 .. 3.5] | grouped, even+ 57%, seen 6+ 71%, own half 64%, walked toward them 50%, heading elsewhere 36% | 47% | 0% | economy/bank.cc carry_bag / banks_bag (route and when to bank); combat/fight.cc want_home | 179474b757f399fe r1372 #0 (91.1); 3d1517837f98cbe6 r477 #6 (82.3); 8f211f7803fa1d64 r718 #4 (80.1) |
| Tavi killed with 1-49 gems while fighting | 0.06 | 0.02 | 3.8 | 1.5 | 2.3 [-0.3 .. 4.9] | alone v2+ 40%, seen 6+ 75%, own half 45%, held its ground 50%, heading elsewhere 50% | 39% | 0% | combat/plan.cc (strike search) and combat/fight.cc prey / chase_with_guard (who to engage) | 18985cd163da1935 r879 #4 (106); 18985cd163da1935 r482 #4 (102); 4107ec3da1eb03fc r552 #5 (88.3) |

The same without the champion (kind and situation only):

| situation | v115 n/game | opponent n/game | v115 cost/game | opponent cost/game | excess [95% CI] | mix | examples |
| --- | --- | --- | --- | --- | --- | --- | --- |
| any champion killed with 1-49 gems while fighting | 0.55 | 0.29 | 37.8 | 21.0 | 16.7 [10.1 .. 23.9] | grouped, even+ 39%, seen 6+ 64%, own half 61%, held its ground 46%, heading elsewhere 56% | d58e7577b649021d r672 #0 (129); a3d734e3c8baebd7 r664 #1 (126) |
| any champion killed with 200+ gems while walking with gems | 0.05 | 0.05 | 26.8 | 16.2 | 10.7 [-4.0 .. 25.0] | grouped, even+ 61%, seen 6+ 50%, own half 67%, held its ground 39%, heading elsewhere 39% | 80883ceb1a204744 r1445 #6 (2429); 3cdc157ddaf83093 r566 #0 (1188) |
| any champion waiting 10+ rounds, by a tributing ally | 0.79 | 0.00 | 8.0 | 0.0 | 8.0 [4.4 .. 13.0] | r401-800 53%, then fight 32% | 3cdc157ddaf83093 r478 #5 (47.2); e9b05b8f2f04b398 r513 #10 (39.7) |
| any champion killed with 1-49 gems while walking with gems | 0.97 | 0.91 | 69.5 | 64.1 | 5.4 [-4.0 .. 17.0] | grouped, even+ 43%, seen 6+ 65%, own half 67%, walked away 37%, heading elsewhere 43% | 3cdc157ddaf83093 r620 #2 (162); c084b20552b4cd49 r484 #5 (139) |
| any champion waiting 10+ rounds, facing enemies within 9 | 0.72 | 0.01 | 5.3 | 0.1 | 5.2 [2.0 .. 9.4] | r801+ 48%, then walk 43% | 3c285506bc276552 r699 #7 (161); 3c285506bc276552 r696 #6 (157) |
| camp stolen (mid half): ours left at even numbers or better | 0.18 | 0.05 | 7.8 | 2.6 | 5.2 [1.0 .. 8.7] | 1G 39% | 57bea7feb1beb6bb r551 (333); a191621af7141a1e r856 (295) |
| any champion killed with 50-199 gems while walking with gems | 0.26 | 0.25 | 38.2 | 33.3 | 4.9 [-7.8 .. 17.5] | grouped, even+ 40%, seen 6+ 54%, own half 67%, walked toward them 36%, heading elsewhere 43% | 3cdc157ddaf83093 r374 #3 (260); a1bb76d0e30e4e12 r734 #3 (239) |
| camp stolen (enemy half): ours left, outnumbered | 0.27 | 0.20 | 10.4 | 5.6 | 4.9 [1.2 .. 8.5] | 1G 14% | 53ae4cf628dfcfd1 r619 (169); c084b20552b4cd49 r456 (164) |
| camp contested (enemy half): ours within 3, outheld | 0.11 | 0.11 | 12.1 | 7.3 | 4.8 [-3.6 .. 18.4] | 31$ 21% | d12a1150439eca01 r702 (672); df4a57af740f92b7 r897 (277) |
| any champion killed with 50-199 gems while fighting | 0.11 | 0.07 | 14.8 | 10.2 | 4.5 [-1.7 .. 10.0] | grouped, outnumbered 32%, seen 6+ 70%, own half 76%, walked away 35%, heading elsewhere 49% | 3f2831555186c5a8 r727 #9 (219); 63bba97ea22a6068 r760 #3 (218) |
| camp stolen (mid half): ours died | 0.21 | 0.15 | 12.1 | 8.2 | 4.0 [-1.9 .. 9.3] | 1G 27% | 3cdc157ddaf83093 r387 (550); d74428b0e1cacbe9 r1160 (243) |
| camp contested (mid half): ours left at even numbers or better | 0.13 | 0.14 | 10.6 | 6.7 | 3.9 [-0.5 .. 9.0] | 1$ 1W 13% | 80883ceb1a204744 r1469 (590); c0378644a669b963 r643 (307) |
| any champion killed with 200+ gems while fighting | 0.03 | 0.01 | 9.2 | 5.3 | 3.9 [-2.3 .. 10.4] | grouped, even+ 40%, seen 6+ 60%, own half 60%, held its ground 50%, heading elsewhere 30% | c6da33ec1345cea0 r847 #7 (477); 99db761839ce5db1 r1028 #3 (402) |
| any champion waiting 10+ rounds, farmable group in reach | 0.34 | 0.00 | 3.3 | 0.0 | 3.3 [0.9 .. 7.0] | r801+ 41%, then walk 43% | 9f44786c9d4184b6 r502 #1 (150); d38952b76d87c5ec r357 #1 (94.8) |
| any champion killed with 1-49 gems while holding | 0.04 | 0.01 | 3.4 | 0.4 | 3.0 [1.2 .. 5.1] | grouped, even+ 53%, seen <6 33%, enemy half 60%, held its ground 87%, heading elsewhere 60% | 750f1fa065a099d2 r229 #0 (146); 886f45d053e3ed0b r51 #4 (90.2) |

v115's single most expensive episodes (rare situations the clusters above leave out):

| game / round | episode | cost | tags |
| --- | --- | --- | --- |
| 80883ceb1a204744 r1445 #6 | Vesper Vale killed carrying 200+ gems while walking with gems, alone v2+, killer seen 6+ | 2429 | first hit r1442, warned 9 rounds, walked away, heading elsewhere, allies 8/16: 0/1, enemies 8: 2, altar 5 away |
| 3cdc157ddaf83093 r566 #0 | Vesper Vale killed carrying 200+ gems while walking with gems, grouped, even+, killer seen 6+ | 1188 | first hit r566, warned 16 rounds, walked toward them, heading toward an altar, allies 8/16: 4/0, enemies 8: 4, altar 2 away; recall from r560 would have landed (closest enemy 4) |
| a3d734e3c8baebd7 r599 #4 | Prism killed carrying 200+ gems while tributing, alone v2+, killer unseen | 981 | first hit r597, warned -1 rounds, held its ground, heading -, allies 8/16: 0/0, enemies 8: 2, altar 1 away |
| 7a67b5fbc08df162 r597 | invaded 48W group (own half): ours within 8 | 878 | WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW(18,22)e, our damage share 0%, nearest of ours 6 steps (walking with gems) |
| 781adfffff55594b r624 | contested 48W group (enemy half): ours left, outnumbered | 720 | WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW(18,22)e, our damage share 22%, 2 of ours v 3 within 8 at their hold |
| 781adfffff55594b r880 | contested 48W group (enemy half): ours died | 720 | WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW(18,22)e, our damage share 11%, 2 of ours v 3 within 8 at their hold |
| 8f211f7803fa1d64 r597 | contested 48W group (own half): ours left, outnumbered | 720 | WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW(18,22)e, our damage share 30%, 2 of ours v 3 within 8 at their hold |
| 8f211f7803fa1d64 r748 | contested 48W group (own half): ours left, outnumbered | 720 | WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW(18,22)e, our damage share 23%, 1 of ours v 3 within 8 at their hold |
| 886f45d053e3ed0b r1134 #4 | Prism killed carrying 200+ gems while walking with gems, grouped, even+, killer seen 6+ | 714 | first hit r1131, warned 59 rounds, held its ground, heading toward own spawn, allies 8/16: 2/0, enemies 8: 2, altar 1 away; recall from r1124 would have landed (closest enemy 4) |
| d12a1150439eca01 r702 | contested 48W group (enemy half): ours within 3, outheld | 672 | WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW(18,22)e, our damage share 30%, 2 of ours v 4 within 8 at their hold |
| d9b34eca9025e161 r839 | stolen 10G 2M group (enemy half): ours died | 656 | GGGGGGGGGGMM(25,24)e, our damage share 52%, 0 of ours v 4 within 8 at their hold |
| 741f3c7c7c9f22b4 r788 | contested 10G 2M group (own half): ours left, outnumbered | 648 | GGGGGGGGGGMM(25,24)e, our damage share 50%, 2 of ours v 5 within 8 at their hold |
| 7ac2d2e9f993c60b r896 | contested 10G 2M group (enemy half): ours left, outnumbered | 637 | GGGGGGGGGGMM(25,24)e, our damage share 48%, 2 of ours v 4 within 8 at their hold |
| 89ccc180bfc4ee82 r931 | stolen 10G 2M group (own half): ours within 3, outheld | 637 | GGGGGGGGGGMM(25,24)e, our damage share 86%, 1 of ours v 2 within 8 at their hold |
| 3cdc157ddaf83093 r848 | contested 2M group (mid half): ours left, outnumbered | 614 | MM(24,20)m, our damage share 2%, 2 of ours v 6 within 8 at their hold |

## Deaths by situation

Death episodes only (killed by champions), one tag at a time. cost = bag + kill gold/4 + dead time.

**champion**

| champion | v115 deaths/game | opponent deaths/game | v115 cost/game | opponent cost/game | excess [95% CI] | examples |
| --- | --- | --- | --- | --- | --- | --- |
| Prism | 0.64 | 0.14 | 77.7 | 15.1 | 62.6 [43.6 .. 86.1] | a3d734e3c8baebd7 r599 #4 (981); 886f45d053e3ed0b r1134 #4 (714) |
| Ryth | 0.28 | 0.00 | 16.5 | 0.0 | 16.5 [10.2 .. 24.0] | 71b73f018802e389 r1345 #0 (253); 71b73f018802e389 r914 #0 (249) |
| Willow | 0.77 | 0.49 | 39.0 | 25.4 | 13.6 [4.9 .. 23.3] | d2c4f7550d573d11 r633 #4 (146); d5fc5ddf7d3f3913 r381 #1 (137) |
| Ren | 0.25 | 0.09 | 13.3 | 3.7 | 9.5 [4.8 .. 14.7] | c8e90a408203f8ea r1377 #9 (128); 7aa3c57148588a47 r545 #10 (103) |
| Stellar | 0.06 | 0.00 | 7.0 | 0.0 | 7.0 [1.8 .. 14.4] | e9b05b8f2f04b398 r597 #9 (302); 3cdc157ddaf83093 r374 #3 (260) |
| Tavi | 0.30 | 0.29 | 19.4 | 17.4 | 2.0 [-11.5 .. 13.9] | c6da33ec1345cea0 r847 #7 (477); 572ef57800754030 r569 #2 (261) |
| Varg | 0.05 | 0.02 | 2.5 | 1.4 | 1.1 [-0.9 .. 2.9] | 917b231327087a60 r246 #5 (79.1); e29d7479ab801256 r892 #4 (75.4) |
| Issac | 0.71 | 0.97 | 55.7 | 69.6 | -13.9 [-25.0 .. -2.7] | 80883ceb1a204744 r550 #8 (364); a3d734e3c8baebd7 r766 #3 (178) |
| Vesper Vale | 0.39 | 0.62 | 35.0 | 49.7 | -14.7 [-27.0 .. -3.4] | 80883ceb1a204744 r1445 #6 (2429); 3cdc157ddaf83093 r566 #0 (1188) |
| Cassi | 0.94 | 1.12 | 67.5 | 84.9 | -17.3 [-31.8 .. -3.3] | 93774a36baf85159 r428 #6 (186); 6abd364ecd7c87af r371 #0 (175) |
| Marcella | 0.28 | 0.60 | 14.5 | 41.0 | -26.5 [-38.5 .. -15.4] | bc187adc11113353 r652 #2 (158); 18985cd163da1935 r894 #2 (152) |
| Vendetta | 0.23 | 0.83 | 14.5 | 55.6 | -41.1 [-56.0 .. -25.4] | e29d7479ab801256 r915 #1 (277); 28d75ccbf8fe4fac r693 #7 (141) |
| Heart of Ruin | 0.31 | 1.22 | 17.5 | 74.7 | -57.2 [-70.5 .. -42.9] | 5311f2a37bc8c542 r1336 #3 (159); a3d734e3c8baebd7 r638 #5 (136) |

**bag**

| bag | v115 deaths/game | opponent deaths/game | v115 cost/game | opponent cost/game | excess [95% CI] | examples |
| --- | --- | --- | --- | --- | --- | --- |
| 200+ | 0.10 | 0.08 | 44.6 | 31.8 | 12.8 [-4.3 .. 30.2] | 80883ceb1a204744 r1445 #6 (2429); 3cdc157ddaf83093 r566 #0 (1188) |
| 1-49 | 1.95 | 1.85 | 139 | 134 | 4.8 [-11.8 .. 21.3] | 3cdc157ddaf83093 r620 #2 (162); e9b05b8f2f04b398 r1011 #8 (148) |
| 50-199 | 0.43 | 0.44 | 62.1 | 61.1 | 1.0 [-14.4 .. 18.0] | 3cdc157ddaf83093 r374 #3 (260); a1bb76d0e30e4e12 r734 #3 (239) |
| 0 | 2.74 | 4.03 | 135 | 212 | -77.1 [-113 .. -35.0] | 3cdc157ddaf83093 r697 #2 (132); 3cdc157ddaf83093 r779 #1 (132) |

**doing before the first hit**

| doing before the first hit | v115 deaths/game | opponent deaths/game | v115 cost/game | opponent cost/game | excess [95% CI] | examples |
| --- | --- | --- | --- | --- | --- | --- |
| fighting | 1.43 | 1.10 | 97.4 | 73.4 | 23.9 [8.3 .. 41.3] | c6da33ec1345cea0 r847 #7 (477); 99db761839ce5db1 r1028 #3 (402) |
| walking with gems | 1.30 | 1.23 | 135 | 115 | 20.2 [-4.6 .. 50.0] | 80883ceb1a204744 r1445 #6 (2429); 3cdc157ddaf83093 r566 #0 (1188) |
| holding | 0.07 | 0.02 | 5.8 | 1.4 | 4.4 [1.3 .. 7.7] | 2007651f4f21a8a9 r616 #9 (226); bc187adc11113353 r652 #2 (158) |
| tributing | 0.05 | 0.03 | 9.0 | 5.2 | 3.9 [-3.0 .. 11.0] | a3d734e3c8baebd7 r599 #4 (981); e5ff7c2f70246901 r443 #4 (478) |
| waiting | 0.08 | 0.07 | 7.5 | 4.4 | 3.1 [-0.6 .. 8.1] | 80883ceb1a204744 r550 #8 (364); 9f44786c9d4184b6 r280 #0 (258) |
| idle | 0.02 | 0.02 | 1.5 | 0.9 | 0.6 [-0.5 .. 1.7] | e37b81f5f7a1c378 r244 #2 (91.9); e29d7479ab801256 r700 #2 (91.5) |
| ? | 0.00 | 0.00 | 0.0 | 0.2 | -0.2 [-0.5 .. 0.0] |  |
| respawning | 0.00 | 0.00 | 0.0 | 0.2 | -0.2 [-0.5 .. 0.0] |  |
| on spawn | 0.00 | 0.01 | 0.0 | 0.8 | -0.8 [-1.8 .. 0.0] |  |
| farming | 0.12 | 0.34 | 8.9 | 22.9 | -13.9 [-20.4 .. -7.7] | 739e47e6c5d6a79b r630 #6 (356); 8d1d082cbb6592ee r1008 #9 (174) |
| stunned/oof | 0.06 | 0.25 | 4.2 | 20.8 | -16.6 [-27.1 .. -7.4] | 153247954c835d03 r474 #9 (319); b4217335dc288f50 r477 #7 (156) |
| recalling | 0.02 | 0.44 | 1.4 | 32.3 | -30.9 [-39.7 .. -21.8] | 15deeeee6a94ddb9 r213 #5 (194); d5fc5ddf7d3f3913 r381 #1 (137) |
| walking | 2.07 | 2.87 | 109 | 161 | -52.1 [-83.0 .. -20.1] | 3cdc157ddaf83093 r383 #1 (167); 420596424f4b1ae3 r291 #2 (150) |

**numbers at the first hit**

| numbers at the first hit | v115 deaths/game | opponent deaths/game | v115 cost/game | opponent cost/game | excess [95% CI] | examples |
| --- | --- | --- | --- | --- | --- | --- |
| alone v2+ | 0.90 | 1.17 | 74.3 | 79.5 | -5.2 [-23.7 .. 19.5] | 80883ceb1a204744 r1445 #6 (2429); a3d734e3c8baebd7 r599 #4 (981) |
| alone v1 | 0.36 | 0.56 | 29.6 | 39.0 | -9.4 [-18.4 .. 0.2] | c6da33ec1345cea0 r847 #7 (477); 917b231327087a60 r661 #3 (308) |
| grouped, outnumbered | 1.47 | 1.57 | 94.5 | 105 | -10.2 [-29.9 .. 13.0] | 153247954c835d03 r474 #9 (319); e29d7479ab801256 r915 #1 (277) |
| grouped, even+ | 2.48 | 3.09 | 182 | 215 | -33.7 [-68.2 .. -0.5] | 3cdc157ddaf83093 r566 #0 (1188); 886f45d053e3ed0b r1134 #4 (714) |

**warning**

| warning | v115 deaths/game | opponent deaths/game | v115 cost/game | opponent cost/game | excess [95% CI] | examples |
| --- | --- | --- | --- | --- | --- | --- |
| seen 6+ | 3.28 | 3.07 | 225 | 210 | 15.1 [-14.3 .. 50.6] | 80883ceb1a204744 r1445 #6 (2429); 3cdc157ddaf83093 r566 #0 (1188) |
| unseen | 0.70 | 1.40 | 62.9 | 99.4 | -36.5 [-60.4 .. -14.0] | a3d734e3c8baebd7 r599 #4 (981); c39658a433012b02 r1011 #2 (534) |
| seen <6 | 1.24 | 1.93 | 92.1 | 129 | -37.1 [-59.7 .. -16.0] | 18985cd163da1935 r847 #1 (538); 3cdc157ddaf83093 r385 #0 (490) |

**half**

| half | v115 deaths/game | opponent deaths/game | v115 cost/game | opponent cost/game | excess [95% CI] | examples |
| --- | --- | --- | --- | --- | --- | --- |
| own | 3.46 | 3.58 | 252 | 252 | -0.7 [-60.4 .. 61.8] | 3cdc157ddaf83093 r566 #0 (1188); a3d734e3c8baebd7 r599 #4 (981) |
| mid | 0.86 | 0.86 | 55.2 | 60.0 | -4.8 [-21.8 .. 12.3] | 18985cd163da1935 r847 #1 (538); 8fb2a4a530ea5e57 r520 #3 (219) |
| enemy | 0.90 | 1.95 | 73.4 | 126 | -53.0 [-82.8 .. -18.1] | 80883ceb1a204744 r1445 #6 (2429); 5481f825cb9703c5 r691 #8 (398) |

## Avoidable bag losses

Deaths with gems where the replay shows a rule-checked alternative, had the enemy acted the same. **recall window**: a killer was in the victim's sight with no damage or stun to it for 6+ rounds before the first hit, so a recall started at the window's start (5 turn ends; only damage or a stun cancels it) would have landed first; with an enemy within 4 during the window the recall may itself have drawn the attack, so those gems are also given apart. **altar**: within 40 rounds before dying it stood within 1 of an altar the enemy had not locked, carrying at least half the final bag, and a tribute started then (ceil(bag/10) turn ends; only a stun cancels it) would have completed before the death, with no stun on it in that span; split by whether an enemy was within 8 then (with one near, the tribute itself may have drawn the attack sooner). Look at: recall combat/fight.cc want_home / recall_line (recall on sight with a bag); economy/bank.cc continue_recall; altar economy/bank.cc banks_bag / retaining_gems / submit_here (bank at the altar passed).

| side | bag gems lost/game | recall window/game | gems | gems, no enemy within 4 in the window | altar, no enemy within 8/game | gems | altar, enemy within 8/game | gems |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v115 | 116 | 0.88 | 36.6 | 3.1 | 0.03 | 1.9 | 0.08 | 3.2 |
| opponent | 98.3 | 0.67 | 33.8 | 10.3 | 0.00 | 0.0 | 0.09 | 4.4 |

Largest v115 recall-avoidable deaths:

- 3cdc157ddaf83093 r566 #0 Vesper Vale bag 1095: killer in sight from r550, no damage from r560 (closest enemy 4), first hit r566; walking with gems, grouped, even+, own half
- 886f45d053e3ed0b r1134 #4 Prism bag 641: killer in sight from r1072, no damage from r1124 (closest enemy 4), first hit r1131; walking with gems, grouped, even+, own half
- 1d06b2af09eeb43d r568 #4 Prism bag 251: killer in sight from r559, no damage from r559 (closest enemy 3), first hit r567; walking with gems, grouped, even+, enemy half
- 80883ceb1a204744 r550 #8 Issac bag 248: killer in sight from r486, no damage from r486 (closest enemy 5), first hit r545; waiting, grouped, even+, enemy half
- fb2bfd2c46f4a881 r657 #8 Prism bag 245: killer in sight from r635, no damage from r635 (closest enemy 3), first hit r644; walking with gems, alone v2+, own half
- 9f1a7f564373aa40 r423 #9 Prism bag 209: killer in sight from r364, no damage from r416 (closest enemy 2), first hit r423; fighting, grouped, outnumbered, enemy half
- 71b73f018802e389 r998 #1 Vesper Vale bag 200: killer in sight from r976, no damage from r991 (closest enemy 2), first hit r998; walking with gems, grouped, outnumbered, own half
- ea39227ab817abb8 r1529 #7 Vesper Vale bag 200: killer in sight from r1516, no damage from r1518 (closest enemy 1), first hit r1529; walking with gems, grouped, even+, own half

Largest v115 altar-avoidable deaths:

- 9b3af6e2800e9a8b r881 #10 Prism bag 182: by an altar at r861 with 182 (tribute 19 rounds, 1 enemies within 8), died 20 rounds later, walking with gems
- d4d66872c142d4f4 r648 #2 Prism bag 169: by an altar at r609 with 152 (tribute 16 rounds, 0 enemies within 8), died 39 rounds later, walking with gems
- 18985cd163da1935 r1446 #1 Prism bag 134: by an altar at r1431 with 126 (tribute 13 rounds, 2 enemies within 8), died 15 rounds later, walking with gems
- 16d9ea737f4973fc r1130 #8 Prism bag 113: by an altar at r1092 with 113 (tribute 12 rounds, 0 enemies within 8), died 38 rounds later, walking with gems
- 16d9ea737f4973fc r743 #8 Prism bag 109: by an altar at r710 with 101 (tribute 11 rounds, 0 enemies within 8), died 33 rounds later, fighting
- 46ce4dccc43f6dfc r264 #2 Prism bag 96: by an altar at r252 with 88 (tribute 9 rounds, 3 enemies within 8), died 12 rounds later, walking with gems
- 46eb3cad27540a99 r392 #4 Prism bag 82: by an altar at r366 with 82 (tribute 9 rounds, 2 enemies within 8), died 26 rounds later, walking with gems
- f5a63ade56265662 r165 #10 Willow bag 77: by an altar at r147 with 77 (tribute 8 rounds, 2 enemies within 8), died 18 rounds later, walking with gems

## Death hazard by activity

Champion-rounds spent on each activity (analysis/macro.py turn classes) and deaths to champions whose fatal damage began right after that activity, per 1000 such rounds, so a side is not penalised for doing more of something. Gems = bag gems lost in those deaths.

| activity | v115 rounds/game | v115 deaths per 1000 | v115 gems lost/game | opponent rounds/game | opponent deaths per 1000 | opponent gems lost/game |
| --- | --- | --- | --- | --- | --- | --- |
| walking | 1298 | 1.60 | 5.0 | 1557 | 1.85 | 6.0 |
| walking with gems | 1182 | 1.10 | 67.2 | 973 | 1.26 | 49.8 |
| fighting | 185 | 7.70 | 28.2 | 188 | 5.85 | 16.0 |
| farming | 839 | 0.15 | 2.2 | 866 | 0.39 | 4.3 |
| recalling | 189 | 0.09 | 0.7 | 276 | 1.59 | 9.5 |
| stunned/oof | 6.3 | 9.56 | 1.5 | 181 | 1.40 | 8.0 |
| waiting | 180 | 0.43 | 2.6 | 19.6 | 3.63 | 0.8 |
| tributing | 74.2 | 0.69 | 5.9 | 48.0 | 0.71 | 3.4 |
| holding | 212 | 0.32 | 2.2 | 31.9 | 0.54 | 0.4 |
| idle | 56.2 | 0.41 | 0.1 | 12.6 | 1.58 | 0.0 |
| on spawn | 49.2 | 0.00 | 0.0 | 67.9 | 0.17 | 0.0 |
| ? | 0.0 | - | 0.0 | 0.0 | - | 0.0 |

## Bag exposure

Champion-rounds alive carrying a bag of each size, and deaths with that bag per 1000 such rounds (a hazard rate, so a side that carries more is not penalised for carrying).

| champion | bag | v115 rounds/game | v115 deaths | v115 per 1000 | opponent rounds/game | opponent deaths | opponent per 1000 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Cassi | 1-49 | 274 | 180 | 1.87 | 180 | 155 | 2.46 |
| Cassi | 50-199 | 4.7 | 18 | 10.90 | 30.4 | 25 | 2.34 |
| Cassi | 200+ | 1.2 | 0 | 0.00 | 1.5 | 1 | 1.92 |
| Heart of Ruin | 1-49 | 121 | 43 | 1.01 | 242 | 120 | 1.42 |
| Heart of Ruin | 50-199 | 8.4 | 10 | 3.37 | 66.3 | 31 | 1.33 |
| Heart of Ruin | 200+ | 0.3 | 0 | 0.00 | 3.6 | 4 | 3.20 |
| Issac | 1-49 | 288 | 147 | 1.45 | 190 | 133 | 1.99 |
| Issac | 50-199 | 6.4 | 19 | 8.44 | 24.2 | 15 | 1.76 |
| Issac | 200+ | 1.0 | 1 | 2.83 | 2.8 | 1 | 1.03 |
| Marcella | 1-49 | 46.7 | 18 | 1.10 | 135 | 63 | 1.33 |
| Marcella | 50-199 | 5.6 | 5 | 2.56 | 56.8 | 20 | 1.00 |
| Marcella | 200+ | 0.0 | 0 | - | 8.9 | 4 | 1.29 |
| Prism | 1-49 | 132 | 64 | 1.39 | 9.0 | 6 | 1.89 |
| Prism | 50-199 | 187 | 76 | 1.16 | 14.3 | 12 | 2.38 |
| Prism | 200+ | 140 | 22 | 0.45 | 17.7 | 4 | 0.64 |
| Ren | 1-49 | 67.7 | 42 | 1.77 | 5.1 | 9 | 5.04 |
| Ren | 50-199 | 4.2 | 3 | 2.04 | 0.0 | 0 | 0.00 |
| Ren | 200+ | 0.2 | 0 | 0.00 | 0.0 | 0 | - |
| Ryth | 1-49 | 79.1 | 24 | 0.86 | 0.0 | 0 | - |
| Ryth | 50-199 | 7.2 | 2 | 0.79 | 0.0 | 0 | - |
| Ryth | 200+ | 1.3 | 3 | 6.52 | 0.0 | 0 | - |
| Stellar | 1-49 | 10.8 | 8 | 2.12 | 0.0 | 0 | - |
| Stellar | 50-199 | 5.4 | 5 | 2.62 | 0.0 | 0 | - |
| Stellar | 200+ | 1.1 | 1 | 2.59 | 0.0 | 0 | - |
| Tavi | 1-49 | 40.5 | 37 | 2.61 | 40.4 | 37 | 2.61 |
| Tavi | 50-199 | 4.3 | 6 | 3.96 | 6.4 | 7 | 3.12 |
| Tavi | 200+ | 1.6 | 2 | 3.58 | 0.0 | 0 | - |
| Varg | 1-49 | 31.8 | 8 | 0.72 | 0.7 | 3 | 12.88 |
| Varg | 50-199 | 0.9 | 0 | 0.00 | 0.2 | 1 | 11.76 |
| Varg | 200+ | 1.1 | 0 | 0.00 | 1.8 | 0 | 0.00 |
| Vendetta | 1-49 | 118 | 43 | 1.04 | 206 | 75 | 1.04 |
| Vendetta | 50-199 | 7.9 | 2 | 0.72 | 80.2 | 27 | 0.96 |
| Vendetta | 200+ | 0.4 | 1 | 8.06 | 5.9 | 6 | 2.90 |
| Vesper Vale | 1-49 | 291 | 63 | 0.62 | 156 | 65 | 1.19 |
| Vesper Vale | 50-199 | 26.5 | 6 | 0.64 | 87 | 21 | 0.69 |
| Vesper Vale | 200+ | 11.2 | 6 | 1.53 | 26.8 | 8 | 0.85 |
| Willow | 1-49 | 55.0 | 35 | 1.81 | 64.2 | 29 | 1.29 |
| Willow | 50-199 | 0.9 | 3 | 9.84 | 4.2 | 2 | 1.35 |
| Willow | 200+ | 0.3 | 0 | 0.00 | 0.2 | 1 | 11.63 |

## Fights lost

Engagements (analysis/fights.py) the side lost on net swing (kill gems + gold/4 - bags lost); these overlap the death episodes. numbers = own minus enemy champions within 8 at the start; absent = own champions 9-16 away at the start that never joined.

| numbers | initiator | help in reach | v115 lost/game | v115 gems/game | opponent lost/game | opponent gems/game | excess | examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| -2- | we started | absent ally 9-16 | 0.28 | 24.7 | 0.11 | 6.8 | 17.8 | e6a4b314ab8199ba r669 (616); 71b73f018802e389 r994 (482) |
| -1 | they started | absent ally 9-16 | 0.29 | 42.0 | 0.46 | 31.1 | 10.9 | 80883ceb1a204744 r1442 (4753); c084b20552b4cd49 r642 (484) |
| +1 | we started | no ally 9-16 | 0.17 | 18.5 | 0.12 | 7.8 | 10.7 | c39658a433012b02 r1010 (1049); e9b05b8f2f04b398 r595 (540) |
| -1 | we started | no ally 9-16 | 0.20 | 15.4 | 0.09 | 4.8 | 10.6 | 3cdc157ddaf83093 r369 (1198); 84fcf143a2cbdaf9 r519 (267) |
| -1 | we started | absent ally 9-16 | 0.22 | 18.5 | 0.13 | 9.6 | 8.9 | 9f1a7f564373aa40 r422 (524); 71b73f018802e389 r893 (438) |
| +0 | we started | absent ally 9-16 | 0.23 | 19.7 | 0.15 | 12.2 | 7.5 | c6da33ec1345cea0 r845 (880); 917b231327087a60 r654 (546) |
| -2- | we started | no ally 9-16 | 0.18 | 13.6 | 0.08 | 7.0 | 6.6 | 18985cd163da1935 r845 (618); 8f081f0fb97f68ab r269 (379) |
| +2+ | we started | absent ally 9-16 | 0.08 | 8.5 | 0.03 | 2.2 | 6.4 | ea39227ab817abb8 r1528 (441); a1bb76d0e30e4e12 r730 (413) |
| +1 | we started | absent ally 9-16 | 0.15 | 12.1 | 0.07 | 6.3 | 5.7 | 02acb3b556afb169 r599 (612); 85a722ce2993a6ac r768 (266) |
| +2+ | we started | no ally 9-16 | 0.16 | 10.8 | 0.09 | 5.2 | 5.6 | 99db761839ce5db1 r1019 (727); 93774a36baf85159 r427 (248) |
| +2+ | they started | absent ally 9-16 | 0.18 | 18.2 | 0.17 | 13.1 | 5.1 | 420596424f4b1ae3 r612 (720); 71b73f018802e389 r1324 (441) |
| +0 | we started | no ally 9-16 | 0.21 | 19.2 | 0.16 | 18.3 | 0.9 | 5481f825cb9703c5 r688 (725); 739e47e6c5d6a79b r930 (435) |
| +1 | they started | no ally 9-16 | 0.19 | 19.8 | 0.38 | 26.4 | -6.6 | 886f45d053e3ed0b r1131 (1382); 739e47e6c5d6a79b r623 (675) |
| -1 | they started | no ally 9-16 | 0.20 | 18.4 | 0.32 | 25.9 | -7.4 | a3d734e3c8baebd7 r597 (1858); 05d3b061c8590c29 r509 (455) |
| +1 | they started | absent ally 9-16 | 0.20 | 13.7 | 0.31 | 23.7 | -10.0 | 8d1d082cbb6592ee r1005 (308); 849194b4282c1a2b r607 (248) |
| -2- | they started | no ally 9-16 | 0.21 | 13.8 | 0.35 | 25.2 | -11.4 | 153247954c835d03 r471 (554); 46ce4dccc43f6dfc r251 (242) |
| +2+ | they started | no ally 9-16 | 0.20 | 16.7 | 0.38 | 33.1 | -16.4 | 403f47fa246839dd r656 (689); df4a57af740f92b7 r989 (252) |
| +0 | they started | absent ally 9-16 | 0.33 | 25.5 | 0.59 | 42.6 | -17.0 | e5ff7c2f70246901 r442 (880); baec7573ddd9eb5f r518 (425) |
| +0 | they started | no ally 9-16 | 0.28 | 24.6 | 0.57 | 45.1 | -20.6 | 3cdc157ddaf83093 r566 (2244); 9b3af6e2800e9a8b r873 (366) |
| -2- | they started | absent ally 9-16 | 0.37 | 23.9 | 0.60 | 49.7 | -25.8 | fb2bfd2c46f4a881 r641 (545); 2007651f4f21a8a9 r614 (374) |

Absent allies 9-16 away in lost fights, by what they were doing: v115: walking 423, walking with gems 374, farming 252, holding 66, recalling 63, waiting 43; opponent: walking 650, walking with gems 322, farming 263, recalling 100, stunned/oof 81, fighting 27.

## v115's losses against its wins

Cluster cost per game in the focus team's losses minus its wins (top 12): the situations that most separate a loss from a win. Partly reverse causality (a losing side is behind and fights at a disadvantage); the round column shows when they happen.

| situation | in losses | in wins | difference | median round |
| --- | --- | --- | --- | --- |
| contested 31$ group (enemy half): ours within 3, outheld | 15.1 | 0.0 | 15.1 | 715 |
| contested 48W group (own half): ours left, outnumbered | 12.4 | 0.0 | 12.4 | 748 |
| Prism killed carrying 200+ gems while walking with gems, grouped, even+, killer seen 6+ | 12.2 | 0.0 | 12.2 | 656 |
| contested 4$ 6E 10G group (mid half): ours left, outnumbered | 11.5 | 0.0 | 11.5 | 1189 |
| contested 2M group (mid half): ours left, outnumbered | 10.2 | 0.0 | 10.2 | 848 |
| Prism killed carrying 200+ gems while fighting, grouped, even+, killer seen 6+ | 9.8 | 0.0 | 9.8 | 691 |
| Prism killed carrying 200+ gems while walking with gems, grouped, even+, killer unseen | 9.8 | 0.0 | 9.8 | 612 |
| Prism killed carrying 50-199 gems while walking with gems, grouped, even+, killer seen 6+ | 10.4 | 1.0 | 9.3 | 695 |
| Vesper Vale killed carrying 200+ gems while walking with gems, grouped, even+, killer seen 6+ | 10.2 | 1.1 | 9.2 | 566 |
| contested 8$ 4E 4G group (mid half): ours left, outnumbered | 9.1 | 0.0 | 9.1 | 862 |
| Willow killed carrying 0 gems while walking, grouped, even+, killer seen 6+ | 13.6 | 5.1 | 8.5 | 773 |
| Prism killed carrying 50-199 gems while walking with gems, grouped, even+, killer unseen | 8.3 | 0.0 | 8.3 | 590 |
