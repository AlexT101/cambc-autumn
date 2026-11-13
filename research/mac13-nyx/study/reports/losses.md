# Loss episodes: where value is lost, clustered and priced

Set: replays/batch-20261113-020034-ab-mac13-nyx-basedbg-ladder (128 games, 127 clusters); 128 games, loser won 0. Each side's losses are split into disjoint episodes priced in gems (deaths: bag + kill gold/4 + dead time at the game's earn rate; camp deaths; camps lost to the enemy; stalls of 10+ rounds), tagged with the situation and clustered. Costs are per game; "excess" is loser minus winner in the same games, with a 95% cluster-bootstrap CI over map pairs or ladder groups. Without --team the focus side is each game's loser, which partly measures losing. Examples are `analysis dir rROUND #champion (cost)`: open them with `py tools/replay/triage.py DIR --team NAME` (the game's turning points) or `py tools/replay/narrate.py` for a turn-level transcript.

Earn rate (gems per alive champion-round, both teams): mean 0.270, so a 60-round death costs about 16.2 gems of time.

## Cost by kind

| kind | loser cost/game | winner cost/game | excess | loser in its wins | loser in its losses |
| --- | --- | --- | --- | --- | --- |
| death | 728 | 188 | 539 | - | 728 |
| camp_death | 10.4 | 4.8 | 5.6 | - | 10.4 |
| camp_lost | 581 | 289 | 292 | - | 581 |
| stall | 11.9 | 45.3 | -33.4 | - | 11.9 |

## Top weaknesses: clusters by excess cost

Every episode kind, clustered by champion and situation (deaths: bag and what the victim was doing the round before the fatal damage began). Sorted by loser's cost per game minus winner's for the same cluster in the same games; clusters with fewer than 4 focus episodes or 3 games are left to the list of single expensive episodes below. "mix" gives each secondary tag's most common value among the focus episodes. cf columns: share of the cluster's focus bag gems that a recall in the safe window / a tribute at the last altar passed would have saved.

| situation | loser n/game | winner n/game | loser cost/game | winner cost/game | excess [95% CI] | mix | cf recall | cf altar | look at | examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Prism killed with 200+ gems while walking with gems | 0.16 | 0.01 | 69.9 | 4.8 | 65.2 [35.1 .. 97.0] | alone v2+ 45%, seen 6+ 50%, own half 70%, held its ground 65%, heading elsewhere 60% | 46% | 3% | economy/bank.cc carry_bag / banks_bag (route and when to bank); combat/fight.cc want_home | 9af6ba6844bffaa0 r985 #4 (891); 1a53508aef8b96ee r942 #2 (884); 7370caf6b518da93 r948 #4 (634) |
| camp invaded (own half): ours within 8 | 2.03 | 0.91 | 67.2 | 23.4 | 43.8 [17.6 .. 67.3] | 1G 18% | - | - | economy/farm.cc farm (target choice and map coverage); economy/altar_guard.cc guard_turn | 1c9a6c8dd8810a58 r960 (192); 1c9a6c8dd8810a58 r564 (189); 1c9a6c8dd8810a58 r824 (189) |
| camp invaded (own half): ours 9-20 away | 2.49 | 1.88 | 72.0 | 40.4 | 31.6 [12.8 .. 56.5] | 1G 29% | - | - | economy/farm.cc farm (target choice and map coverage); economy/altar_guard.cc guard_turn | 9b1594455a9da4c8 r486 (201); f148cc299e8ab50c r96 (137); 2afefb4402074152 r652 (132) |
| Prism killed with 200+ gems while fighting | 0.09 | 0.01 | 33.7 | 2.2 | 31.5 [11.1 .. 56.1] | grouped, even+ 64%, seen 6+ 64%, own half 45%, walked toward them 64%, heading toward an altar 45% | 47% | 0% | combat/plan.cc (strike search) and combat/fight.cc prey / chase_with_guard (who to engage) | b29a405bf7050285 r613 #2 (758); 9af6ba6844bffaa0 r1655 #4 (554); 923d73083d01616b r489 #9 (457) |
| camp contested (mid half): ours left, outnumbered | 0.49 | 0.23 | 42.3 | 11.1 | 31.1 [8.3 .. 60.4] | 2G 1W 6% | - | - | economy/capture.cc contest_capture / yield_capture; combat/plan.cc (fight on the tiles) | 7370caf6b518da93 r1573 (614); 7370caf6b518da93 r1833 (565); d4195fbd3a9ebe7b r1678 (353) |
| Cassi killed with 0 gems while walking | 0.61 | 0.16 | 41.5 | 10.8 | 30.7 [17.2 .. 44.4] | grouped, even+ 47%, seen 6+ 42%, own half 81%, walked toward them 54%, heading toward an altar 45% | - | - | model/safety.cc (threat model), combat/guard.cc guard_work / step_safely (step guard) | 8e562f12bb1b18dc r271 #6 (113); 3e14056889eb2885 r503 #6 (100.0); 8e562f12bb1b18dc r486 #6 (99.5) |
| Prism killed with 50-199 gems while walking with gems | 0.19 | 0.00 | 28.5 | 0.0 | 28.5 [18.6 .. 42.6] | grouped, even+ 42%, seen 6+ 42%, own half 54%, walked toward them 46%, heading elsewhere 54% | 38% | 4% | economy/bank.cc carry_bag / banks_bag (route and when to bank); combat/fight.cc want_home | 656bf4a601ee85dc r506 #3 (246); ba65207c151a66eb r289 #10 (227); 8e8e28c10a03ecfc r488 #4 (227) |
| Willow killed with 0 gems while walking | 0.70 | 0.22 | 35.9 | 12.6 | 23.3 [12.2 .. 33.7] | grouped, even+ 62%, unseen 40%, own half 67%, walked toward them 45%, heading elsewhere 52% | - | - | model/safety.cc (threat model), combat/guard.cc guard_work / step_safely (step guard) | 68b75ec6707c94c6 r496 #5 (101); 7a0ffd6c9eedb37e r503 #4 (97.9); 9dc5d284db263751 r515 #5 (94.7) |
| camp contested (own half): ours within 3, outheld | 0.20 | 0.03 | 22.8 | 1.7 | 21.1 [7.9 .. 37.8] | 2G 1W 12% | - | - | economy/capture.cc contest_capture / yield_capture; combat/plan.cc (fight on the tiles) | 2692060add585070 r612 (696); 5db4c0f488e86898 r1341 (428); a58a7ed3a6099bcf r707 (277) |
| camp contested (mid half): ours died | 0.23 | 0.02 | 22.7 | 1.9 | 20.8 [7.0 .. 36.1] | 3G 17% | - | - | economy/capture.cc contest_capture / yield_capture; combat/plan.cc (fight on the tiles) | 7370caf6b518da93 r1198 (582); 9ec0ae15fa61ae36 r541 (295); 9ec0ae15fa61ae36 r1101 (249) |
| Prism killed with 0 gems while walking | 0.44 | 0.02 | 20.3 | 0.7 | 19.7 [11.6 .. 27.9] | grouped, outnumbered 52%, seen 6+ 59%, own half 71%, walked toward them 64%, heading toward an altar 68% | - | - | model/safety.cc (threat model), combat/guard.cc guard_work / step_safely (step guard) | 9af6ba6844bffaa0 r1279 #4 (99.3); aaf560afa5f83192 r912 #3 (90.5); 68b75ec6707c94c6 r1070 #4 (72.7) |
| camp contested (mid half): ours left at even numbers or better | 0.27 | 0.23 | 31.7 | 13.4 | 18.3 [-3.2 .. 46.6] | 4$ 6E 10G 11% | - | - | economy/capture.cc contest_capture / yield_capture; combat/plan.cc (fight on the tiles) | 7370caf6b518da93 r626 (565); d4195fbd3a9ebe7b r1427 (353); d4195fbd3a9ebe7b r1529 (353) |
| Prism killed with 200+ gems while tributing | 0.03 | 0.01 | 23.7 | 6.0 | 17.7 [-7.6 .. 47.2] | grouped, even+ 100%, unseen 75%, own half 100%, held its ground 75%, heading - 75% | 18% | 0% | economy/bank.cc submit_here / continue_tribute (start or keep a tribute with enemies near) | 4e007ea7c5c7aa71 r1318 #4 (1157); 07392d3aa07e8439 r479 #8 (736); 3e14056889eb2885 r503 #8 (580) |
| camp invaded (own half): ours 21+ away | 1.83 | 1.46 | 61.0 | 45.9 | 15.2 [3.9 .. 29.1] | 1G 27% | - | - | economy/farm.cc farm (target choice and map coverage); economy/altar_guard.cc guard_turn | 15443f167808fed8 r513 (201); 15443f167808fed8 r643 (201); 15443f167808fed8 r994 (201) |
| camp stolen (mid half): ours died | 0.29 | 0.05 | 17.1 | 2.4 | 14.7 [5.5 .. 25.3] | 1G 11% | - | - | economy/capture.cc holding_capture / contest_capture; economy/crew.cc (who stays to hold) | 0d12a736e63873c5 r845 (222); 935f3ca55ed714ea r201 (164); 935f3ca55ed714ea r483 (164) |
| camp contested (enemy half): ours left, outnumbered | 0.64 | 0.39 | 30.0 | 15.8 | 14.2 [3.8 .. 26.4] | 1$ 1W 11% | - | - | economy/capture.cc contest_capture / yield_capture; combat/plan.cc (fight on the tiles) | af0a63f092cb1e80 r1094 (282); 4fcd1f03c195af7b r301 (181); a75f6de8c6bf9c04 r1160 (163) |
| Marcella killed with 0 gems while walking | 0.36 | 0.05 | 16.4 | 2.3 | 14.2 [6.3 .. 23.2] | grouped, even+ 48%, seen 6+ 52%, own half 61%, walked toward them 59%, heading toward an altar 52% | - | - | model/safety.cc (threat model), combat/guard.cc guard_work / step_safely (step guard) | c80107034b26bada r428 #3 (74.0); 1a53508aef8b96ee r942 #3 (70.9); 1a53508aef8b96ee r1745 #3 (62.1) |
| Prism killed with 1-49 gems while walking with gems | 0.22 | 0.03 | 15.0 | 2.2 | 12.7 [6.5 .. 20.1] | grouped, outnumbered 32%, seen 6+ 43%, own half 71%, walked toward them 39%, heading elsewhere 46% | 31% | 0% | economy/bank.cc carry_bag / banks_bag (route and when to bank); combat/fight.cc want_home | 19c60caa19c0ceac r563 #7 (103); 68b75ec6707c94c6 r1180 #4 (101); 2d744e0395520e04 r353 #7 (90.4) |
| Ryth killed with 0 gems while walking | 0.36 | 0.11 | 18.3 | 6.0 | 12.2 [4.4 .. 20.9] | grouped, outnumbered 48%, seen 6+ 54%, own half 67%, held its ground 46%, heading elsewhere 46% | - | - | model/safety.cc (threat model), combat/guard.cc guard_work / step_safely (step guard) | 68b75ec6707c94c6 r982 #0 (72.4); 7f9d634c89c94417 r465 #6 (68.6); 15443f167808fed8 r989 #5 (68.5) |
| Cassi killed with 1-49 gems while fighting | 0.19 | 0.06 | 16.3 | 4.2 | 12.0 [3.8 .. 22.2] | grouped, outnumbered 50%, seen <6 50%, own half 88%, held its ground 46%, heading elsewhere 54% | 11% | 0% | combat/plan.cc (strike search) and combat/fight.cc prey / chase_with_guard (who to engage) | 1a53508aef8b96ee r1669 #0 (145); ba65207c151a66eb r185 #8 (119); a218de6c1c08aa5b r458 #1 (118) |
| Prism killed with 50-199 gems while fighting | 0.08 | 0.00 | 11.6 | 0.0 | 11.6 [4.7 .. 20.9] | grouped, outnumbered 60%, seen <6 60%, own half 80%, walked toward them 50%, heading toward an altar 50% | 28% | 0% | combat/plan.cc (strike search) and combat/fight.cc prey / chase_with_guard (who to engage) | 05aff64b0d7974f2 r466 #2 (236); c80107034b26bada r338 #2 (198); 01fee0eb3cbaa2d5 r466 #10 (181) |
| Vesper Vale killed with 0 gems while walking | 0.27 | 0.09 | 15.3 | 3.8 | 11.5 [3.4 .. 20.1] | grouped, even+ 37%, seen 6+ 66%, own half 66%, walked toward them 54%, heading toward an altar 60% | - | - | model/safety.cc (threat model), combat/guard.cc guard_work / step_safely (step guard) | 7370caf6b518da93 r1035 #0 (102); 7370caf6b518da93 r1196 #0 (72.9); 30d0f1dec52d626f r383 #4 (70.4) |
| camp contested (own half): ours died | 0.20 | 0.07 | 15.4 | 4.1 | 11.3 [3.6 .. 19.3] | 2G 1W 8% | - | - | economy/capture.cc contest_capture / yield_capture; combat/plan.cc (fight on the tiles) | af0a63f092cb1e80 r1129 (275); 1c9a6c8dd8810a58 r749 (224); f63836d4dce3adad r1006 (111) |
| Issac killed with 1-49 gems while walking with gems | 0.18 | 0.05 | 15.6 | 4.5 | 11.1 [3.4 .. 18.9] | grouped, even+ 43%, unseen 35%, own half 74%, walked toward them 52%, heading toward an altar 48% | 18% | 0% | economy/bank.cc carry_bag / banks_bag (route and when to bank); combat/fight.cc want_home | 9dc5d284db263751 r515 #3 (123); 7370caf6b518da93 r1053 #2 (122); 9af6ba6844bffaa0 r1953 #3 (117) |
| camp stolen (own half): ours left at even numbers or better | 0.38 | 0.23 | 17.7 | 6.9 | 10.9 [1.6 .. 23.5] | 2$ 12% | - | - | economy/capture.cc holding_capture / contest_capture; economy/crew.cc (who stays to hold) | 7739b987eb85b2ed r772 (702); 9af6ba6844bffaa0 r801 (143); 958e0035cff5a201 r457 (93.2) |

The same without the champion (kind and situation only):

| situation | loser n/game | winner n/game | loser cost/game | winner cost/game | excess [95% CI] | mix | examples |
| --- | --- | --- | --- | --- | --- | --- | --- |
| any champion killed with 0 gems while walking | 3.66 | 0.94 | 198 | 52.7 | 146 [101 .. 184] | grouped, even+ 45%, seen 6+ 47%, own half 71%, walked toward them 50%, heading toward an altar 45% | 8e562f12bb1b18dc r271 #6 (113); 7370caf6b518da93 r1035 #0 (102) |
| any champion killed with 200+ gems while walking with gems | 0.20 | 0.02 | 83.8 | 6.8 | 77.0 [43.3 .. 115] | alone v2+ 44%, seen 6+ 48%, own half 76%, held its ground 60%, heading elsewhere 60% | 9af6ba6844bffaa0 r985 #4 (891); 1a53508aef8b96ee r942 #2 (884) |
| any champion killed with 1-49 gems while walking with gems | 1.36 | 0.39 | 101 | 29.0 | 71.5 [49.7 .. 95.8] | grouped, even+ 43%, seen 6+ 44%, own half 75%, walked toward them 47%, heading elsewhere 44% | 41ed6cd8fb4bf99c r515 #7 (134); 1a53508aef8b96ee r1292 #0 (134) |
| any champion killed with 50-199 gems while walking with gems | 0.48 | 0.08 | 67.8 | 11.8 | 56.0 [33.4 .. 81.5] | grouped, even+ 39%, seen 6+ 39%, own half 67%, walked toward them 51%, heading elsewhere 46% | 656bf4a601ee85dc r506 #3 (246); ba65207c151a66eb r289 #10 (227) |
| camp invaded (own half): ours within 8 | 2.03 | 0.91 | 67.2 | 23.4 | 43.8 [17.6 .. 67.3] | 1G 18% | 1c9a6c8dd8810a58 r960 (192); 1c9a6c8dd8810a58 r564 (189) |
| any champion killed with 200+ gems while fighting | 0.09 | 0.01 | 35.9 | 2.2 | 33.7 [13.9 .. 58.4] | grouped, even+ 58%, seen 6+ 58%, own half 50%, walked toward them 67%, heading toward an altar 50% | b29a405bf7050285 r613 #2 (758); 9af6ba6844bffaa0 r1655 #4 (554) |
| camp invaded (own half): ours 9-20 away | 2.49 | 1.88 | 72.0 | 40.4 | 31.6 [12.8 .. 56.5] | 1G 29% | 9b1594455a9da4c8 r486 (201); f148cc299e8ab50c r96 (137) |
| any champion killed with 0 gems while fighting | 0.89 | 0.36 | 49.8 | 18.6 | 31.2 [16.2 .. 49.5] | grouped, outnumbered 40%, seen 6+ 63%, own half 70%, walked toward them 66%, heading toward an altar 48% | 1a53508aef8b96ee r1669 #3 (103); 7370caf6b518da93 r1035 #4 (102) |
| camp contested (mid half): ours left, outnumbered | 0.49 | 0.23 | 42.3 | 11.1 | 31.1 [8.3 .. 60.4] | 2G 1W 6% | 7370caf6b518da93 r1573 (614); 7370caf6b518da93 r1833 (565) |
| any champion killed with 1-49 gems while fighting | 0.46 | 0.15 | 35.8 | 10.1 | 25.6 [15.2 .. 38.7] | grouped, outnumbered 44%, seen 6+ 47%, own half 64%, walked toward them 53%, heading elsewhere 53% | a218de6c1c08aa5b r597 #2 (161); 1a53508aef8b96ee r1669 #0 (145) |
| camp contested (own half): ours within 3, outheld | 0.20 | 0.03 | 22.8 | 1.7 | 21.1 [7.9 .. 37.8] | 2G 1W 12% | 2692060add585070 r612 (696); 5db4c0f488e86898 r1341 (428) |
| camp contested (mid half): ours died | 0.23 | 0.02 | 22.7 | 1.9 | 20.8 [7.0 .. 36.1] | 3G 17% | 7370caf6b518da93 r1198 (582); 9ec0ae15fa61ae36 r541 (295) |
| camp contested (mid half): ours left at even numbers or better | 0.27 | 0.23 | 31.7 | 13.4 | 18.3 [-3.2 .. 46.6] | 4$ 6E 10G 11% | 7370caf6b518da93 r626 (565); d4195fbd3a9ebe7b r1427 (353) |
| any champion killed with 200+ gems while tributing | 0.03 | 0.01 | 23.7 | 6.0 | 17.7 [-7.6 .. 47.2] | grouped, even+ 100%, unseen 75%, own half 100%, held its ground 75%, heading - 75% | 4e007ea7c5c7aa71 r1318 #4 (1157); 07392d3aa07e8439 r479 #8 (736) |
| any champion killed with 50-199 gems while fighting | 0.13 | 0.02 | 19.5 | 1.8 | 17.7 [6.6 .. 29.8] | grouped, outnumbered 41%, seen <6 59%, own half 71%, walked toward them 47%, heading toward an altar 53% | 05aff64b0d7974f2 r466 #2 (236); 403edf589c042995 r553 #9 (218) |

loser's single most expensive episodes (rare situations the clusters above leave out):

| game / round | episode | cost | tags |
| --- | --- | --- | --- |
| 4e007ea7c5c7aa71 r1318 #4 | Prism killed carrying 200+ gems while tributing, grouped, even+, killer unseen | 1157 | first hit r1317, warned -1 rounds, held its ground, heading -, allies 8/16: 2/0, enemies 8: 1, altar 1 away |
| 9af6ba6844bffaa0 r985 #4 | Prism killed carrying 200+ gems while walking with gems, alone v2+, killer seen 6+ | 891 | first hit r985, warned 20 rounds, held its ground, heading elsewhere, allies 8/16: 0/0, enemies 8: 3, altar 4 away; recall from r978 would have landed (closest enemy 5) |
| 1a53508aef8b96ee r942 #2 | Prism killed carrying 200+ gems while walking with gems, grouped, outnumbered, killer seen 6+ | 884 | first hit r942, warned 32 rounds, held its ground, heading elsewhere, allies 8/16: 1/0, enemies 8: 4, altar 2 away; recall from r910 would have landed (closest enemy 4) |
| b29a405bf7050285 r613 #2 | Prism killed carrying 200+ gems while fighting, grouped, even+, killer seen <6 | 758 | first hit r612, warned 2 rounds, walked toward them, heading toward an altar, allies 8/16: 2/0, enemies 8: 1, altar 6 away |
| 07392d3aa07e8439 r479 #8 | Prism killed carrying 200+ gems while tributing, grouped, even+, killer unseen | 736 | first hit r479, warned -1 rounds, held its ground, heading -, allies 8/16: 1/4, enemies 8: 2, altar 1 away |
| 7739b987eb85b2ed r772 | stolen 10G 2M group (own half): ours left at even numbers or better | 702 | GGGGGGGGGGMM(25,24)e, our damage share 58%, 4 of ours v 1 within 8 at their hold |
| 2692060add585070 r612 | contested 48W group (own half): ours within 3, outheld | 696 | WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW(18,22)e, our damage share 24%, 4 of ours v 4 within 8 at their hold |
| 9d6fc57971ae72fb r1001 #6 | Prism killed carrying 200+ gems while holding, alone v1, killer seen <6 | 673 | first hit r999, warned 0 rounds, walked toward them, heading toward an altar, allies 8/16: 0/3, enemies 8: 1, altar 5 away |
| c5bd21512c1a1d42 r737 #8 | Prism killed carrying 200+ gems while recalling, grouped, even+, killer unseen | 663 | first hit r737, warned -1 rounds, held its ground, heading elsewhere, allies 8/16: 4/1, enemies 8: 2, altar 9 away |
| 7370caf6b518da93 r948 #4 | Prism killed carrying 200+ gems while walking with gems, grouped, even+, killer seen 6+ | 634 | first hit r945, warned 59 rounds, walked toward them, heading toward an altar, allies 8/16: 3/0, enemies 8: 4, altar 4 away |
| 36ef14d67dccfe77 r552 #4 | Prism killed carrying 200+ gems while walking with gems, grouped, even+, killer seen 6+ | 625 | first hit r550, warned 50 rounds, held its ground, heading elsewhere, allies 8/16: 3/1, enemies 8: 4, altar 1 away; recall from r542 would have landed (closest enemy 6) |
| 7370caf6b518da93 r811 | stolen 2M group (mid half): ours left, outnumbered | 614 | MM(24,20)m, our damage share 75%, 2 of ours v 4 within 8 at their hold |
| 7370caf6b518da93 r1573 | contested 2M group (mid half): ours left, outnumbered | 614 | MM(24,20)m, our damage share 11%, 4 of ours v 6 within 8 at their hold |
| 4191a660ddfda314 r549 #3 | Prism killed carrying 200+ gems while walking with gems, alone v2+, killer unseen | 605 | first hit r549, warned -1 rounds, held its ground, heading elsewhere, allies 8/16: 0/1, enemies 8: 4, altar 4 away |
| 7370caf6b518da93 r1198 | contested 2M group (mid half): ours died | 582 | MM(24,20)m, our damage share 29%, 2 of ours v 5 within 8 at their hold |

## Deaths by situation

Death episodes only (killed by champions), one tag at a time. cost = bag + kill gold/4 + dead time.

**champion**

| champion | loser deaths/game | winner deaths/game | loser cost/game | winner cost/game | excess [95% CI] | examples |
| --- | --- | --- | --- | --- | --- | --- |
| Prism | 1.57 | 0.09 | 241 | 18.0 | 223 [162 .. 285] | 4e007ea7c5c7aa71 r1318 #4 (1157); 9af6ba6844bffaa0 r985 #4 (891) |
| Cassi | 1.63 | 0.71 | 133 | 58.3 | 74.8 [46.7 .. 104] | 656bf4a601ee85dc r406 #0 (414); 48f7f38f4aeac9ba r644 #7 (287) |
| Issac | 1.03 | 0.48 | 85.7 | 39.1 | 46.5 [28.8 .. 64.0] | 5db4c0f488e86898 r1263 #1 (506); 1579c4582be74df1 r260 #1 (287) |
| Willow | 1.06 | 0.36 | 58.3 | 21.1 | 37.1 [22.8 .. 50.3] | 5db4c0f488e86898 r75 #3 (205); 9af6ba6844bffaa0 r1213 #5 (107) |
| Ryth | 0.76 | 0.20 | 45.3 | 10.8 | 34.5 [19.8 .. 53.0] | 4191a660ddfda314 r563 #0 (138); a218de6c1c08aa5b r597 #0 (125) |
| Marcella | 0.65 | 0.15 | 40.4 | 7.0 | 33.3 [17.4 .. 52.0] | 403edf589c042995 r553 #9 (218); 656bf4a601ee85dc r398 #4 (213) |
| Vesper Vale | 0.62 | 0.20 | 45.1 | 13.5 | 31.5 [15.2 .. 50.4] | 7370caf6b518da93 r962 #0 (435); 07985783285c2de2 r417 #0 (185) |
| Heart of Ruin | 0.47 | 0.13 | 24.9 | 6.3 | 18.6 [7.8 .. 30.7] | 60e12c9ad2ba1a46 r933 #11 (122); f4bf9a7fc0c7f3eb r455 #9 (111) |
| Vendetta | 0.29 | 0.11 | 18.4 | 7.1 | 11.3 [2.8 .. 20.4] | 07985783285c2de2 r406 #1 (283); 64761cfcb1f559a6 r565 #1 (122) |
| Ren | 0.20 | 0.05 | 11.2 | 2.9 | 8.3 [1.8 .. 17.0] | 41ed6cd8fb4bf99c r943 #9 (120); 7a0ffd6c9eedb37e r474 #5 (82.6) |
| Stellar | 0.12 | 0.02 | 9.2 | 1.0 | 8.2 [-0.2 .. 20.3] | 7370caf6b518da93 r946 #3 (195); 07985783285c2de2 r429 #4 (171) |
| Tavi | 0.16 | 0.04 | 8.1 | 1.8 | 6.3 [0.5 .. 13.2] | 07392d3aa07e8439 r507 #11 (85.1); 8e562f12bb1b18dc r287 #11 (79.3) |
| Varg | 0.09 | 0.02 | 6.7 | 1.3 | 5.3 [-0.9 .. 12.9] | 30d0f1dec52d626f r342 #5 (262); 4fca5c568349ce1d r469 #11 (117) |

**bag**

| bag | loser deaths/game | winner deaths/game | loser cost/game | winner cost/game | excess [95% CI] | examples |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 5.09 | 1.57 | 278 | 88.5 | 190 [135 .. 241] | 958e0035cff5a201 r732 #4 (115); 7a0ffd6c9eedb37e r503 #1 (113) |
| 200+ | 0.35 | 0.04 | 160 | 17.2 | 143 [91.4 .. 194] | 4e007ea7c5c7aa71 r1318 #4 (1157); 9af6ba6844bffaa0 r985 #4 (891) |
| 1-49 | 2.49 | 0.84 | 188 | 63.8 | 125 [92.4 .. 161] | a218de6c1c08aa5b r597 #2 (161); 1a53508aef8b96ee r1669 #0 (145) |
| 50-199 | 0.72 | 0.13 | 101 | 18.7 | 82.4 [57.2 .. 113] | 656bf4a601ee85dc r506 #3 (246); 05aff64b0d7974f2 r466 #2 (236) |

**doing before the first hit**

| doing before the first hit | loser deaths/game | winner deaths/game | loser cost/game | winner cost/game | excess [95% CI] | examples |
| --- | --- | --- | --- | --- | --- | --- |
| walking with gems | 2.03 | 0.49 | 252 | 48.0 | 204 [139 .. 269] | 9af6ba6844bffaa0 r985 #4 (891); 1a53508aef8b96ee r942 #2 (884) |
| walking | 4.03 | 1.11 | 228 | 69.4 | 159 [114 .. 200] | 9dc5d284db263751 r569 #4 (178); d34bbecc7b7feb90 r568 #2 (123) |
| fighting | 1.58 | 0.53 | 141 | 32.8 | 108 [69.4 .. 146] | b29a405bf7050285 r613 #2 (758); 9af6ba6844bffaa0 r1655 #4 (554) |
| tributing | 0.08 | 0.02 | 26.9 | 7.3 | 19.5 [-5.0 .. 47.1] | 4e007ea7c5c7aa71 r1318 #4 (1157); 07392d3aa07e8439 r479 #8 (736) |
| recalling | 0.16 | 0.06 | 19.5 | 4.4 | 15.0 [2.9 .. 31.9] | c5bd21512c1a1d42 r737 #8 (663); 40a33b982838645a r732 #4 (335) |
| farming | 0.41 | 0.23 | 28.1 | 16.3 | 11.8 [-0.4 .. 23.8] | 69780a2ecc7683f1 r308 #2 (158); c650911d42d4b140 r185 #8 (142) |
| holding | 0.12 | 0.03 | 14.0 | 3.1 | 10.8 [0.5 .. 25.2] | 9d6fc57971ae72fb r1001 #6 (673); e22c82ae7d91303f r296 #8 (191) |
| idle | 0.06 | 0.01 | 6.2 | 0.4 | 5.9 [0.6 .. 14.2] | 656bf4a601ee85dc r406 #0 (414); 02e8f2ccb4fdf0c7 r91 #1 (92.6) |
| stunned/oof | 0.06 | 0.01 | 3.2 | 0.8 | 2.4 [-0.4 .. 5.1] | 0fda5644b2fb900c r692 #10 (65.6); 69780a2ecc7683f1 r384 #1 (64.3) |
| respawning | 0.02 | 0.00 | 1.2 | 0.0 | 1.2 [0.0 .. 3.3] | 15443f167808fed8 r619 #6 (95.7); 7881f2e90f94ca7d r1367 #5 (57.6) |
| on spawn | 0.02 | 0.01 | 1.4 | 0.5 | 0.9 [0.0 .. 2.4] | 15443f167808fed8 r957 #6 (95.7); ac82af6e0c879e87 r459 #7 (82.4) |
| waiting | 0.09 | 0.07 | 5.8 | 5.3 | 0.5 [-5.7 .. 6.6] | 9d6fc57971ae72fb r252 #5 (122); 40a33b982838645a r481 #3 (98.5) |

**numbers at the first hit**

| numbers at the first hit | loser deaths/game | winner deaths/game | loser cost/game | winner cost/game | excess [95% CI] | examples |
| --- | --- | --- | --- | --- | --- | --- |
| grouped, even+ | 3.76 | 1.25 | 329 | 90.0 | 239 [181 .. 302] | 4e007ea7c5c7aa71 r1318 #4 (1157); b29a405bf7050285 r613 #2 (758) |
| grouped, outnumbered | 2.83 | 0.67 | 197 | 53.8 | 143 [83.1 .. 195] | 1a53508aef8b96ee r942 #2 (884); 656bf4a601ee85dc r406 #0 (414) |
| alone v2+ | 1.38 | 0.34 | 132 | 22.7 | 110 [77.6 .. 146] | 9af6ba6844bffaa0 r985 #4 (891); 4191a660ddfda314 r549 #3 (605) |
| alone v1 | 0.70 | 0.32 | 68.9 | 21.9 | 47.0 [25.6 .. 71.1] | 9d6fc57971ae72fb r1001 #6 (673); 9af6ba6844bffaa0 r1655 #4 (554) |

**warning**

| warning | loser deaths/game | winner deaths/game | loser cost/game | winner cost/game | excess [95% CI] | examples |
| --- | --- | --- | --- | --- | --- | --- |
| seen 6+ | 3.91 | 1.11 | 317 | 75.5 | 242 [168 .. 324] | 9af6ba6844bffaa0 r985 #4 (891); 1a53508aef8b96ee r942 #2 (884) |
| seen <6 | 2.66 | 0.78 | 214 | 53.9 | 160 [109 .. 208] | b29a405bf7050285 r613 #2 (758); 9d6fc57971ae72fb r1001 #6 (673) |
| unseen | 2.09 | 0.69 | 197 | 58.9 | 138 [95.0 .. 184] | 4e007ea7c5c7aa71 r1318 #4 (1157); 07392d3aa07e8439 r479 #8 (736) |

**half**

| half | loser deaths/game | winner deaths/game | loser cost/game | winner cost/game | excess [95% CI] | examples |
| --- | --- | --- | --- | --- | --- | --- |
| own | 6.09 | 1.38 | 521 | 110 | 411 [296 .. 526] | 4e007ea7c5c7aa71 r1318 #4 (1157); 9af6ba6844bffaa0 r985 #4 (891) |
| mid | 1.29 | 0.38 | 91.8 | 22.9 | 68.9 [37.0 .. 107] | a218de6c1c08aa5b r531 #3 (488); 747b1f740f4b590a r498 #4 (362) |
| enemy | 1.28 | 0.83 | 115 | 55.3 | 59.4 [33.5 .. 87.2] | 9af6ba6844bffaa0 r1655 #4 (554); d34bbecc7b7feb90 r547 #3 (525) |

## Avoidable bag losses

Deaths with gems where the replay shows a rule-checked alternative, had the enemy acted the same. **recall window**: a killer was in the victim's sight with no damage or stun to it for 6+ rounds before the first hit, so a recall started at the window's start (5 turn ends; only damage or a stun cancels it) would have landed first; with an enemy within 4 during the window the recall may itself have drawn the attack, so those gems are also given apart. **altar**: within 40 rounds before dying it stood within 1 of an altar the enemy had not locked, carrying at least half the final bag, and a tribute started then (ceil(bag/10) turn ends; only a stun cancels it) would have completed before the death, with no stun on it in that span; split by whether an enemy was within 8 then (with one near, the tribute itself may have drawn the attack sooner). Look at: recall combat/fight.cc want_home / recall_line (recall on sight with a bag); economy/bank.cc continue_recall; altar economy/bank.cc banks_bag / retaining_gems / submit_here (bank at the altar passed).

| side | bag gems lost/game | recall window/game | gems | gems, no enemy within 4 in the window | altar, no enemy within 8/game | gems | altar, enemy within 8/game | gems |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| loser | 251 | 0.98 | 85.2 | 35.5 | 0.02 | 3.5 | 0.10 | 6.5 |
| winner | 41.1 | 0.23 | 8.9 | 5.0 | 0.00 | 0.0 | 0.02 | 0.6 |

Largest loser recall-avoidable deaths:

- 9af6ba6844bffaa0 r985 #4 Prism bag 833: killer in sight from r965, no damage from r978 (closest enemy 5), first hit r985; walking with gems, alone v2+, own half
- 1a53508aef8b96ee r942 #2 Prism bag 813: killer in sight from r910, no damage from r910 (closest enemy 4), first hit r942; walking with gems, grouped, outnumbered, own half
- 36ef14d67dccfe77 r552 #4 Prism bag 552: killer in sight from r500, no damage from r542 (closest enemy 6), first hit r550; walking with gems, grouped, even+, own half
- 3e14056889eb2885 r503 #8 Prism bag 505: killer in sight from r491, no damage from r491 (closest enemy 5), first hit r501; tributing, grouped, even+, own half
- 9af6ba6844bffaa0 r1655 #4 Prism bag 496: killer in sight from r1643, no damage from r1649 (closest enemy 4), first hit r1655; fighting, alone v1, enemy half
- 5db4c0f488e86898 r1263 #1 Issac bag 460: killer in sight from r1232, no damage from r1251 (closest enemy 4), first hit r1259; walking with gems, alone v2+, own half
- bbac8b734d040052 r366 #7 Prism bag 416: killer in sight from r322, no damage from r322 (closest enemy 5), first hit r362; walking with gems, alone v2+, enemy half
- 7370caf6b518da93 r962 #0 Vesper Vale bag 362: killer in sight from r900, no damage from r945 (closest enemy 5), first hit r959; walking with gems, alone v2+, own half

Largest loser altar-avoidable deaths:

- 656bf4a601ee85dc r406 #0 Cassi bag 336: by an altar at r387 with 168 (tribute 17 rounds, 5 enemies within 8), died 19 rounds later, idle
- f148cc299e8ab50c r248 #4 Prism bag 222: by an altar at r222 with 201 (tribute 21 rounds, 0 enemies within 8), died 26 rounds later, walking with gems
- 656bf4a601ee85dc r506 #3 Prism bag 196: by an altar at r485 with 196 (tribute 20 rounds, 4 enemies within 8), died 21 rounds later, walking with gems
- e22c82ae7d91303f r296 #8 Prism bag 146: by an altar at r258 with 146 (tribute 15 rounds, 0 enemies within 8), died 38 rounds later, holding
- 48f7f38f4aeac9ba r200 #9 Prism bag 105: by an altar at r169 with 105 (tribute 11 rounds, 0 enemies within 8), died 31 rounds later, walking with gems
- 8e562f12bb1b18dc r146 #8 Prism bag 91: by an altar at r130 with 91 (tribute 10 rounds, 5 enemies within 8), died 16 rounds later, fighting
- 3ab79af1af45a071 r385 #8 Prism bag 77: by an altar at r376 with 77 (tribute 8 rounds, 1 enemies within 8), died 9 rounds later, walking with gems
- bbac8b734d040052 r500 #8 Marcella bag 75: by an altar at r488 with 75 (tribute 8 rounds, 4 enemies within 8), died 12 rounds later, walking with gems

## Death hazard by activity

Champion-rounds spent on each activity (analysis/macro.py turn classes) and deaths to champions whose fatal damage began right after that activity, per 1000 such rounds, so a side is not penalised for doing more of something. Gems = bag gems lost in those deaths.

| activity | loser rounds/game | loser deaths per 1000 | loser gems lost/game | winner rounds/game | winner deaths per 1000 | winner gems lost/game |
| --- | --- | --- | --- | --- | --- | --- |
| walking | 1423 | 2.83 | 6.8 | 1361 | 0.82 | 5.2 |
| walking with gems | 1141 | 1.78 | 143 | 1204 | 0.41 | 21.2 |
| fighting | 158 | 10.00 | 51.9 | 165 | 3.22 | 4.9 |
| farming | 755 | 0.55 | 4.1 | 856 | 0.27 | 1.5 |
| recalling | 173 | 0.91 | 10.5 | 193 | 0.32 | 0.9 |
| holding | 203 | 0.62 | 7.1 | 246 | 0.13 | 1.0 |
| waiting | 131 | 0.65 | 2.0 | 263 | 0.27 | 0.5 |
| tributing | 37.9 | 2.06 | 22.4 | 145 | 0.16 | 5.9 |
| stunned/oof | 5.9 | 10.53 | 0.2 | 7.4 | 1.05 | 0.1 |
| idle | 64.2 | 0.97 | 2.9 | 75.3 | 0.10 | 0.0 |
| on spawn | 61.9 | 0.25 | 0.1 | 74.3 | 0.11 | 0.0 |

## Bag exposure

Champion-rounds alive carrying a bag of each size, and deaths with that bag per 1000 such rounds (a hazard rate, so a side that carries more is not penalised for carrying).

| champion | bag | loser rounds/game | loser deaths | loser per 1000 | winner rounds/game | winner deaths | winner per 1000 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Cassi | 1-49 | 225 | 84 | 2.91 | 254 | 45 | 1.38 |
| Cassi | 50-199 | 17.6 | 13 | 5.76 | 29.7 | 7 | 1.84 |
| Cassi | 200+ | 0.6 | 2 | 25.32 | 1.1 | 1 | 7.41 |
| Heart of Ruin | 1-49 | 95.2 | 14 | 1.15 | 105 | 4 | 0.30 |
| Heart of Ruin | 50-199 | 14.4 | 4 | 2.17 | 17.6 | 0 | 0.00 |
| Heart of Ruin | 200+ | 0.0 | 0 | - | 1.3 | 0 | 0.00 |
| Issac | 1-49 | 254 | 63 | 1.94 | 286 | 29 | 0.79 |
| Issac | 50-199 | 22.8 | 8 | 2.74 | 37.8 | 2 | 0.41 |
| Issac | 200+ | 0.0 | 2 | - | 5.2 | 1 | 1.49 |
| Marcella | 1-49 | 66.3 | 19 | 2.24 | 63.1 | 4 | 0.50 |
| Marcella | 50-199 | 14.3 | 10 | 5.47 | 18.7 | 1 | 0.42 |
| Prism | 1-49 | 121 | 40 | 2.59 | 81.0 | 5 | 0.48 |
| Prism | 50-199 | 178 | 43 | 1.89 | 174 | 1 | 0.04 |
| Prism | 200+ | 184 | 38 | 1.62 | 372 | 3 | 0.06 |
| Ren | 1-49 | 47.7 | 12 | 1.96 | 52.1 | 3 | 0.45 |
| Ren | 50-199 | 4.4 | 1 | 1.78 | 6.3 | 0 | 0.00 |
| Ryth | 1-49 | 88.4 | 23 | 2.03 | 77.7 | 5 | 0.50 |
| Ryth | 50-199 | 8.8 | 4 | 3.55 | 7.5 | 0 | 0.00 |
| Ryth | 200+ | 1.4 | 0 | 0.00 | 1.3 | 0 | 0.00 |
| Stellar | 1-49 | 6.3 | 1 | 1.24 | 8.5 | 0 | 0.00 |
| Stellar | 50-199 | 10.5 | 2 | 1.49 | 8.1 | 0 | 0.00 |
| Tavi | 1-49 | 33.9 | 4 | 0.92 | 30.5 | 1 | 0.26 |
| Tavi | 50-199 | 0.8 | 0 | 0.00 | 2.3 | 0 | 0.00 |
| Tavi | 200+ | 0.0 | 0 | - | 0.6 | 0 | 0.00 |
| Varg | 1-49 | 32.2 | 5 | 1.21 | 35.2 | 1 | 0.22 |
| Varg | 50-199 | 7.7 | 1 | 1.01 | 8.5 | 1 | 0.92 |
| Varg | 200+ | 2.4 | 1 | 3.22 | 1.2 | 0 | 0.00 |
| Vendetta | 1-49 | 80.6 | 13 | 1.26 | 87.6 | 2 | 0.18 |
| Vendetta | 50-199 | 7.8 | 1 | 1.01 | 20.1 | 2 | 0.78 |
| Vendetta | 200+ | 1.3 | 1 | 6.02 | 0.7 | 0 | 0.00 |
| Vesper Vale | 1-49 | 210 | 30 | 1.12 | 228 | 9 | 0.31 |
| Vesper Vale | 50-199 | 49.1 | 7 | 1.11 | 43.5 | 4 | 0.72 |
| Vesper Vale | 200+ | 5.6 | 1 | 1.39 | 17.9 | 0 | 0.00 |
| Willow | 1-49 | 48.9 | 20 | 3.20 | 38.4 | 7 | 1.42 |
| Willow | 50-199 | 2.5 | 1 | 3.14 | 0.6 | 0 | 0.00 |

## Fights lost

Engagements (analysis/fights.py) the side lost on net swing (kill gems + gold/4 - bags lost); these overlap the death episodes. numbers = own minus enemy champions within 8 at the start; absent = own champions 9-16 away at the start that never joined.

| numbers | initiator | help in reach | loser lost/game | loser gems/game | winner lost/game | winner gems/game | excess | examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| +0 | they started | no ally 9-16 | 0.77 | 94.7 | 0.20 | 13.0 | 81.7 | 7370caf6b518da93 r945 (1487); 07392d3aa07e8439 r479 (1397) |
| -2- | they started | no ally 9-16 | 0.63 | 81.5 | 0.04 | 1.2 | 80.3 | 1a53508aef8b96ee r942 (1726); 9af6ba6844bffaa0 r985 (1707) |
| -2- | they started | absent ally 9-16 | 0.80 | 84.9 | 0.15 | 11.3 | 73.6 | 4191a660ddfda314 r549 (1147); 5db4c0f488e86898 r1259 (948) |
| +0 | they started | absent ally 9-16 | 0.65 | 77.8 | 0.37 | 33 | 44.8 | 9d6fc57971ae72fb r999 (1261); 36ef14d67dccfe77 r550 (1211) |
| -2- | we started | absent ally 9-16 | 0.38 | 50.1 | 0.10 | 6.1 | 43.9 | bbac8b734d040052 r362 (857); 02e8f2ccb4fdf0c7 r651 (619) |
| +2+ | they started | no ally 9-16 | 0.27 | 40.7 | 0.14 | 9.3 | 31.4 | 4e007ea7c5c7aa71 r1317 (2247); f1e5e63d32d9b887 r328 (499) |
| +1 | they started | absent ally 9-16 | 0.33 | 41.4 | 0.16 | 10.3 | 31.0 | 3e14056889eb2885 r501 (1110); dc752b321c68ad46 r739 (1082) |
| +1 | they started | no ally 9-16 | 0.29 | 35.6 | 0.09 | 6.8 | 28.8 | d34bbecc7b7feb90 r546 (943); 60e12c9ad2ba1a46 r923 (607) |
| -1 | they started | no ally 9-16 | 0.52 | 33.6 | 0.09 | 6.0 | 27.5 | 07392d3aa07e8439 r1025 (240); aaf560afa5f83192 r911 (165) |
| -1 | we started | no ally 9-16 | 0.24 | 28.9 | 0.08 | 2.1 | 26.8 | 656bf4a601ee85dc r403 (697); dd6469d822ba8d48 r577 (631) |
| -2- | we started | no ally 9-16 | 0.38 | 25.9 | 0.06 | 2.9 | 23.0 | 68b75ec6707c94c6 r985 (685); b4baaf01dc80ac7b r873 (515) |
| +0 | we started | no ally 9-16 | 0.41 | 24.5 | 0.05 | 3.2 | 21.3 | 07985783285c2de2 r429 (259); 48f7f38f4aeac9ba r196 (235) |
| +0 | we started | absent ally 9-16 | 0.27 | 25.4 | 0.08 | 5.9 | 19.5 | 9af6ba6844bffaa0 r1654 (1033); 6bdf356a5fd4365f r677 (299) |
| -1 | we started | absent ally 9-16 | 0.23 | 23.6 | 0.07 | 4.6 | 19.1 | f148cc299e8ab50c r244 (469); ba65207c151a66eb r286 (381) |
| +2+ | we started | no ally 9-16 | 0.15 | 27.0 | 0.07 | 8.3 | 18.7 | b29a405bf7050285 r610 (1413); 923d73083d01616b r485 (831) |
| +2+ | they started | absent ally 9-16 | 0.23 | 22.9 | 0.09 | 4.3 | 18.6 | c5bd21512c1a1d42 r737 (1292); ba65207c151a66eb r210 (223) |
| -1 | they started | absent ally 9-16 | 0.47 | 37.0 | 0.19 | 20.3 | 16.7 | 7f9d634c89c94417 r463 (641); 07392d3aa07e8439 r576 (277) |
| +1 | we started | absent ally 9-16 | 0.19 | 16.3 | 0.07 | 2.8 | 13.5 | 68b75ec6707c94c6 r603 (501); af0a63f092cb1e80 r1113 (148) |
| +2+ | we started | absent ally 9-16 | 0.05 | 9.8 | 0.01 | 0.3 | 9.5 | 747b1f740f4b590a r495 (686); 9dc5d284db263751 r514 (197) |
| +1 | we started | no ally 9-16 | 0.17 | 11.9 | 0.08 | 3.1 | 8.8 | 12e3714a30a2bb6a r266 (169); 7a0ffd6c9eedb37e r497 (165) |

Absent allies 9-16 away in lost fights, by what they were doing: loser: walking 312, walking with gems 170, farming 125, holding 27, recalling 24, idle 24; winner: walking 85, walking with gems 72, farming 49, holding 21, recalling 15, waiting 8.
