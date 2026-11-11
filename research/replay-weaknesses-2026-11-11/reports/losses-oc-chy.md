# Loss episodes: where value is lost, clustered and priced

Set: replays/batch-20261111-183545-ab-chy-vs-ocean-d18-hold (240 games, 121 clusters, focus ocean-chybase); 240 games, ocean-chybase won 92. Each side's losses are split into disjoint episodes priced in gems (deaths: bag + kill gold/4 + dead time at the game's earn rate; camp deaths; camps lost to the enemy; stalls of 10+ rounds), tagged with the situation and clustered. Costs are per game; "excess" is ocean-chybase minus opponent in the same games, with a 95% cluster-bootstrap CI over map pairs or ladder groups. Examples are `analysis dir rROUND #champion (cost)`: open them with `py tools/replay/triage.py DIR --team NAME` (the game's turning points) or `py tools/replay/narrate.py` for a turn-level transcript.

Earn rate (gems per alive champion-round, both teams): mean 0.294, so a 60-round death costs about 17.7 gems of time.

## Cost by kind

| kind | ocean-chybase cost/game | opponent cost/game | excess | ocean-chybase in its wins | ocean-chybase in its losses |
| --- | --- | --- | --- | --- | --- |
| death | 496 | 348 | 148 | 311 | 611 |
| camp_death | 12.9 | 12.6 | 0.3 | 10.5 | 14.3 |
| camp_lost | 369 | 329 | 39.6 | 306 | 407 |
| stall | 16.8 | 32.3 | -15.4 | 32.5 | 7.1 |

## Top weaknesses: clusters by excess cost

Every episode kind, clustered by champion and situation (deaths: bag and what the victim was doing the round before the fatal damage began). Sorted by ocean-chybase's cost per game minus opponent's for the same cluster in the same games; clusters with fewer than 4 focus episodes or 3 games are left to the list of single expensive episodes below. "mix" gives each secondary tag's most common value among the focus episodes. cf columns: share of the cluster's focus bag gems that a recall in the safe window / a tribute at the last altar passed would have saved.

| situation | ocean-chybase n/game | opponent n/game | ocean-chybase cost/game | opponent cost/game | excess [95% CI] | mix | cf recall | cf altar | look at | examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Prism killed with 200+ gems while walking with gems | 0.12 | 0.05 | 58.7 | 26.5 | 32.2 [0.0 .. 68.4] | grouped, even+ 53%, seen 6+ 63%, own half 70%, walked toward them 60%, heading toward an altar 50% | 28% | 0% | economy/bank.cc carry_bag / banks_bag (route and when to bank); combat/fight.cc want_home | 590d110dfeba742f r757 #7 (1596); 3d83d7f9bc0e7fcf r503 #3 (790); 8829b6190be197fe r661 #9 (751) |
| Issac killed with 1-49 gems while walking with gems | 0.23 | 0.07 | 18.6 | 5.9 | 12.7 [7.0 .. 19.9] | grouped, even+ 50%, seen 6+ 52%, own half 76%, walked toward them 43%, heading toward an altar 48% | 27% | 0% | economy/bank.cc carry_bag / banks_bag (route and when to bank); combat/fight.cc want_home | a6e2109cda1e704c r747 #8 (160); c2aa1cd814dbf6ad r607 #2 (132); 762aee3cf5e9f49a r321 #8 (131) |
| camp invaded (own half): ours within 8 | 0.91 | 0.60 | 39.4 | 27.9 | 11.5 [-1.9 .. 23.2] | 2$ 10% | - | - | economy/farm.cc farm (target choice and map coverage); economy/altar_guard.cc guard_turn | 6309f33998a7eed1 r643 (143); 0f714f02b91ad2f5 r117 (142); a54a4d627db9535a r378 (117) |
| Vesper Vale killed with 1-49 gems while walking with gems | 0.18 | 0.05 | 13.5 | 3.6 | 9.8 [5.0 .. 15.0] | grouped, even+ 58%, seen 6+ 47%, own half 72%, walked toward them 49%, heading elsewhere 47% | 22% | 0% | economy/bank.cc carry_bag / banks_bag (route and when to bank); combat/fight.cc want_home | 6cd1642de67b6c70 r567 #7 (121); 668d02e95b8a454e r450 #0 (116); 0c604698a62ff9d0 r386 #6 (110) |
| Prism killed with 50-199 gems while walking with gems | 0.15 | 0.09 | 21.9 | 12.5 | 9.4 [-0.9 .. 18.7] | grouped, even+ 53%, seen 6+ 56%, own half 69%, walked toward them 50%, heading elsewhere 47% | 37% | 0% | economy/bank.cc carry_bag / banks_bag (route and when to bank); combat/fight.cc want_home | e41fa249c71d8f56 r297 #9 (244); 9e16da8a6089ae60 r559 #7 (244); db10f4e4b84abbc0 r578 #2 (234) |
| camp stolen (own half): ours died | 0.28 | 0.15 | 16.2 | 7.0 | 9.2 [3.8 .. 15.1] | 2$ 2W 9% | - | - | economy/capture.cc holding_capture / contest_capture; economy/crew.cc (who stays to hold) | 2174fe2c1aa66d0b r466 (282); 13ccfa2d472c2eeb r478 (162); 37f390012887317e r454 (143) |
| Issac killed with 0 gems while walking | 0.30 | 0.15 | 19.4 | 10.3 | 9.0 [1.4 .. 19.3] | grouped, even+ 44%, seen <6 41%, own half 80%, walked toward them 66%, heading toward an altar 56% | - | - | model/safety.cc (threat model), combat/guard.cc guard_work / step_safely (step guard) | 590d110dfeba742f r906 #6 (128); 590d110dfeba742f r1195 #6 (120); 590d110dfeba742f r835 #6 (118) |
| Willow killed with 0 gems while walking | 0.41 | 0.25 | 20.4 | 12.7 | 7.7 [-0.1 .. 16.9] | grouped, even+ 56%, seen 6+ 47%, own half 76%, held its ground 46%, heading elsewhere 53% | - | - | model/safety.cc (threat model), combat/guard.cc guard_work / step_safely (step guard) | 4bf0ccca1978704a r508 #4 (94.1); 409667189052fa9c r669 #4 (87.4); 08383228b8a7836e r951 #9 (70.1) |
| Cassi killed with 1-49 gems while walking with gems | 0.18 | 0.12 | 16.7 | 9.7 | 7.1 [-0.5 .. 13.4] | grouped, even+ 48%, seen 6+ 41%, own half 73%, held its ground 43%, heading elsewhere 39% | 30% | 0% | economy/bank.cc carry_bag / banks_bag (route and when to bank); combat/fight.cc want_home | 0187997b1f435613 r828 #0 (136); b93ae9243fde1d27 r915 #6 (128); 3d83d7f9bc0e7fcf r453 #1 (123) |
| Prism killed with 1-49 gems while walking with gems | 0.15 | 0.05 | 10.0 | 3.2 | 6.8 [1.4 .. 12.4] | grouped, even+ 54%, seen 6+ 51%, own half 73%, held its ground 46%, heading elsewhere 54% | 26% | 3% | economy/bank.cc carry_bag / banks_bag (route and when to bank); combat/fight.cc want_home | 590d110dfeba742f r870 #7 (99.8); f6e66a8cf4de51ea r153 #8 (88.4); d1c79b48722a06c3 r177 #5 (86.9) |
| camp contested (mid half): ours left at even numbers or better | 0.14 | 0.11 | 11.0 | 4.3 | 6.6 [0.2 .. 14.3] | 2G 1W 15% | - | - | economy/capture.cc contest_capture / yield_capture; combat/plan.cc (fight on the tiles) | d52aa01386fc2a6e r695 (300); 9981b25f9b40081f r542 (224); 9981b25f9b40081f r1042 (224) |
| Cassi killed with 0 gems while walking | 0.35 | 0.25 | 22.0 | 15.6 | 6.3 [-3.4 .. 16.4] | grouped, even+ 46%, seen 6+ 65%, own half 80%, walked toward them 46%, heading elsewhere 47% | - | - | model/safety.cc (threat model), combat/guard.cc guard_work / step_safely (step guard) | 409667189052fa9c r552 #0 (99.8); 409667189052fa9c r623 #0 (99.8); 409667189052fa9c r695 #0 (99.8) |
| camp contested (enemy half): ours left, outnumbered | 0.47 | 0.50 | 26.9 | 21.0 | 5.9 [-3.0 .. 14.5] | 1G 1W 6% | - | - | economy/capture.cc contest_capture / yield_capture; combat/plan.cc (fight on the tiles) | 80dc850a5d44d4c0 r721 (307); 13ccfa2d472c2eeb r125 (161); 13ccfa2d472c2eeb r353 (161) |
| Cassi killed with 1-49 gems while fighting | 0.13 | 0.08 | 11.9 | 6.8 | 5.1 [-1.2 .. 12.9] | grouped, even+ 39%, seen 6+ 45%, own half 74%, walked toward them 58%, heading toward an altar 52% | 31% | 0% | combat/plan.cc (strike search) and combat/fight.cc prey / chase_with_guard (who to engage) | 590d110dfeba742f r1048 #5 (164); 668d02e95b8a454e r478 #1 (154); 590d110dfeba742f r493 #5 (141) |
| Vesper Vale killed with 0 gems while walking | 0.17 | 0.07 | 8.1 | 3.7 | 4.4 [1.0 .. 8.6] | grouped, even+ 40%, seen 6+ 50%, own half 75%, walked toward them 52%, heading toward an altar 55% | - | - | model/safety.cc (threat model), combat/guard.cc guard_work / step_safely (step guard) | 590d110dfeba742f r725 #4 (73.8); e8cee75bc53138cf r587 #6 (69.8); 3d83d7f9bc0e7fcf r328 #0 (68.4) |
| Marcella killed with 1-49 gems while walking with gems | 0.07 | 0.02 | 5.4 | 1.4 | 4.1 [-0.1 .. 9.4] | grouped, even+ 56%, seen 6+ 83%, own half 72%, walked toward them 39%, heading elsewhere 39% | 73% | 0% | economy/bank.cc carry_bag / banks_bag (route and when to bank); combat/fight.cc want_home | d1c79b48722a06c3 r751 #6 (105); 9e16da8a6089ae60 r483 #8 (97.5); c5ff627e0c57b81d r181 #8 (84.8) |
| Heart of Ruin killed with 1-49 gems while walking with gems | 0.13 | 0.07 | 8.9 | 4.9 | 4.0 [0.2 .. 7.6] | grouped, even+ 28%, seen 6+ 69%, own half 50%, held its ground 44%, heading elsewhere 47% | 44% | 0% | economy/bank.cc carry_bag / banks_bag (route and when to bank); combat/fight.cc want_home | 054c002144d1fa1d r1808 #4 (97.3); 8829b6190be197fe r710 #11 (88.6); 054c002144d1fa1d r950 #4 (86.3) |
| Prism killed with 200+ gems while fighting | 0.04 | 0.02 | 15.0 | 11.3 | 3.7 [-14.8 .. 19.8] | grouped, even+ 44%, seen <6 67%, own half 44%, walked toward them 67%, heading toward an altar 56% | 24% | 0% | combat/plan.cc (strike search) and combat/fight.cc prey / chase_with_guard (who to engage) | f3e1feed964bcda0 r679 #3 (649); 409667189052fa9c r786 #2 (495); 606d969a8b61b62b r498 #6 (465) |
| Prism killed with 0 gems while walking | 0.22 | 0.15 | 10.6 | 7.1 | 3.5 [-3.9 .. 12.9] | grouped, outnumbered 55%, seen 6+ 70%, own half 92%, walked toward them 51%, heading toward an altar 43% | - | - | model/safety.cc (threat model), combat/guard.cc guard_work / step_safely (step guard) | e8cee75bc53138cf r587 #9 (69.8); e8cee75bc53138cf r824 #9 (68.5); f6e66a8cf4de51ea r286 #8 (61.7) |
| Marcella killed with 0 gems while walking | 0.12 | 0.07 | 6.2 | 3.1 | 3.1 [-1.1 .. 8.1] | grouped, outnumbered 52%, seen 6+ 52%, own half 66%, walked toward them 62%, heading toward an altar 62% | - | - | model/safety.cc (threat model), combat/guard.cc guard_work / step_safely (step guard) | 409667189052fa9c r669 #3 (87.4); e8cee75bc53138cf r814 #10 (68.3); 409667189052fa9c r750 #3 (62.4) |
| camp invaded (own half): ours 21+ away | 2.06 | 2.15 | 71.6 | 68.5 | 3.1 [-9.0 .. 18.3] | 2G 16% | - | - | economy/farm.cc farm (target choice and map coverage); economy/altar_guard.cc guard_turn | d700a65d704e700e r694 (352); 9af5a6bc985093fe r616 (307); 0b2225e77b4f7056 r536 (128) |
| Cassi killed with 50-199 gems while fighting | 0.04 | 0.02 | 5.6 | 2.6 | 3.0 [-1.2 .. 7.3] | grouped, even+ 50%, seen <6 60%, own half 80%, held its ground 70%, heading elsewhere 70% | 30% | 0% | combat/plan.cc (strike search) and combat/fight.cc prey / chase_with_guard (who to engage) | a6e2109cda1e704c r965 #7 (178); 606d969a8b61b62b r125 #4 (159); 2ac618fadde0c138 r111 #0 (146) |
| camp contested (mid half): ours within 3, outheld | 0.13 | 0.09 | 10.1 | 7.1 | 3.0 [-2.6 .. 9.3] | 2G 1W 16% | - | - | economy/capture.cc contest_capture / yield_capture; combat/plan.cc (fight on the tiles) | 0287d0c58dc7b23c r1098 (224); 0287d0c58dc7b23c r412 (224); 43ff3a8f96440182 r511 (186) |
| camp contested (mid half): ours died | 0.13 | 0.08 | 9.3 | 6.3 | 3.0 [-2.3 .. 8.2] | 4$ 2E 12% | - | - | economy/capture.cc contest_capture / yield_capture; combat/plan.cc (fight on the tiles) | 0287d0c58dc7b23c r820 (224); 43ff3a8f96440182 r339 (186); d5bb13924247cf68 r596 (110) |
| Cassi killed with 0 gems while fighting | 0.16 | 0.12 | 9.8 | 7.1 | 2.7 [-4.3 .. 11.3] | grouped, even+ 53%, seen 6+ 61%, own half 87%, walked toward them 63%, heading toward an altar 53% | - | - | combat/plan.cc (strike search) and combat/fight.cc prey / chase_with_guard (who to engage) | 13ccfa2d472c2eeb r467 #8 (79.5); eea272635d75c81e r1102 #2 (75.0); 606d969a8b61b62b r263 #4 (74.6) |

The same without the champion (kind and situation only):

| situation | ocean-chybase n/game | opponent n/game | ocean-chybase cost/game | opponent cost/game | excess [95% CI] | mix | examples |
| --- | --- | --- | --- | --- | --- | --- | --- |
| any champion killed with 1-49 gems while walking with gems | 1.28 | 0.65 | 95.2 | 46.3 | 49.0 [29.5 .. 65.7] | grouped, even+ 51%, seen 6+ 53%, own half 73%, walked toward them 40%, heading elsewhere 44% | a6e2109cda1e704c r747 #8 (160); 0187997b1f435613 r828 #0 (136) |
| any champion killed with 0 gems while walking | 2.00 | 1.43 | 108 | 75.6 | 32.3 [-1.9 .. 67.8] | grouped, even+ 48%, seen 6+ 55%, own half 78%, walked toward them 48%, heading elsewhere 44% | 590d110dfeba742f r906 #6 (128); 590d110dfeba742f r1195 #6 (120) |
| any champion killed with 200+ gems while walking with gems | 0.13 | 0.06 | 59.8 | 29.0 | 30.8 [-1.6 .. 65.9] | grouped, even+ 52%, seen 6+ 61%, own half 71%, walked toward them 61%, heading toward an altar 52% | 590d110dfeba742f r757 #7 (1596); 3d83d7f9bc0e7fcf r503 #3 (790) |
| camp invaded (own half): ours within 8 | 0.91 | 0.60 | 39.4 | 27.9 | 11.5 [-1.9 .. 23.2] | 2$ 10% | 6309f33998a7eed1 r643 (143); 0f714f02b91ad2f5 r117 (142) |
| any champion killed with 1-49 gems while fighting | 0.39 | 0.25 | 28.8 | 17.5 | 11.3 [2.4 .. 20.4] | grouped, even+ 43%, seen 6+ 55%, own half 69%, walked toward them 57%, heading elsewhere 48% | 590d110dfeba742f r1048 #5 (164); 668d02e95b8a454e r478 #1 (154) |
| any champion killed with 50-199 gems while walking with gems | 0.34 | 0.25 | 47.8 | 36.5 | 11.2 [-7.4 .. 30.7] | grouped, even+ 47%, seen 6+ 49%, own half 74%, walked toward them 57%, heading toward an altar 51% | 0187997b1f435613 r1294 #1 (285); 0187997b1f435613 r1618 #0 (244) |
| camp stolen (own half): ours died | 0.28 | 0.15 | 16.2 | 7.0 | 9.2 [3.8 .. 15.1] | 2$ 2W 9% | 2174fe2c1aa66d0b r466 (282); 13ccfa2d472c2eeb r478 (162) |
| any champion killed with 0 gems while fighting | 0.55 | 0.39 | 28.4 | 20.2 | 8.3 [-2.9 .. 21.9] | grouped, outnumbered 41%, seen 6+ 66%, own half 72%, walked toward them 64%, heading toward an altar 52% | 2823b6e0a36021e0 r615 #3 (89.1); 409667189052fa9c r597 #4 (87.4) |
| camp contested (mid half): ours left at even numbers or better | 0.14 | 0.11 | 11.0 | 4.3 | 6.6 [0.2 .. 14.3] | 2G 1W 15% | d52aa01386fc2a6e r695 (300); 9981b25f9b40081f r542 (224) |
| camp contested (enemy half): ours left, outnumbered | 0.47 | 0.50 | 26.9 | 21.0 | 5.9 [-3.0 .. 14.5] | 1G 1W 6% | 80dc850a5d44d4c0 r721 (307); 13ccfa2d472c2eeb r125 (161) |
| any champion killed with 50-199 gems while fighting | 0.14 | 0.08 | 18.5 | 12.9 | 5.6 [-4.9 .. 14.5] | grouped, even+ 45%, seen 6+ 61%, own half 79%, walked toward them 45%, heading toward an altar 45% | a5ec620179e30c72 r406 #3 (221); 409667189052fa9c r986 #2 (188) |
| camp invaded (own half): ours 21+ away | 2.06 | 2.15 | 71.6 | 68.5 | 3.1 [-9.0 .. 18.3] | 2G 16% | d700a65d704e700e r694 (352); 9af5a6bc985093fe r616 (307) |
| camp contested (mid half): ours within 3, outheld | 0.13 | 0.09 | 10.1 | 7.1 | 3.0 [-2.6 .. 9.3] | 2G 1W 16% | 0287d0c58dc7b23c r1098 (224); 0287d0c58dc7b23c r412 (224) |
| any champion killed with 1-49 gems while walking | 0.24 | 0.20 | 18.0 | 15.0 | 3.0 [-2.9 .. 10.0] | grouped, even+ 53%, seen 6+ 58%, own half 61%, held its ground 46%, heading elsewhere 40% | a6e2109cda1e704c r469 #8 (146); 8a1fabe65a0d8d1c r651 #2 (133) |
| camp contested (mid half): ours died | 0.13 | 0.08 | 9.3 | 6.3 | 3.0 [-2.3 .. 8.2] | 4$ 2E 12% | 0287d0c58dc7b23c r820 (224); 43ff3a8f96440182 r339 (186) |

ocean-chybase's single most expensive episodes (rare situations the clusters above leave out):

| game / round | episode | cost | tags |
| --- | --- | --- | --- |
| 0187997b1f435613 r1902 #2 | Prism killed carrying 200+ gems while tributing, alone v1, killer seen <6 | 2023 | first hit r1901, warned 1 rounds, held its ground, heading -, allies 8/16: 0/2, enemies 8: 1, altar 1 away |
| 590d110dfeba742f r757 #7 | Prism killed carrying 200+ gems while walking with gems, grouped, outnumbered, killer seen <6 | 1596 | first hit r751, warned 3 rounds, walked toward them, heading toward an altar, allies 8/16: 2/0, enemies 8: 4, altar 5 away |
| a6e2109cda1e704c r915 #9 | Prism killed carrying 200+ gems while tributing, grouped, even+, killer unseen | 1257 | first hit r912, warned -1 rounds, held its ground, heading -, allies 8/16: 3/1, enemies 8: 3, altar 1 away |
| be8613adeefa3594 r814 #3 | Prism killed carrying 200+ gems while tributing, grouped, even+, killer unseen | 1156 | first hit r811, warned -1 rounds, held its ground, heading -, allies 8/16: 3/0, enemies 8: 1, altar 1 away |
| a6e2109cda1e704c r824 #6 | Vesper Vale killed carrying 200+ gems while tributing, grouped, outnumbered, killer unseen | 1152 | first hit r812, warned -1 rounds, held its ground, heading elsewhere, allies 8/16: 2/1, enemies 8: 4, altar 1 away |
| d52aa01386fc2a6e r1140 #2 | Prism killed carrying 200+ gems while waiting, grouped, outnumbered, killer unseen | 996 | first hit r1136, warned -1 rounds, held its ground, heading elsewhere, allies 8/16: 1/4, enemies 8: 4, altar 1 away |
| 054c002144d1fa1d r1280 #1 | Marcella killed carrying 200+ gems while tributing, grouped, even+, killer unseen | 994 | first hit r1269, warned -1 rounds, held its ground, heading -, allies 8/16: 2/1, enemies 8: 2, altar 1 away |
| 2823b6e0a36021e0 r608 #4 | Prism killed carrying 200+ gems while tributing, grouped, even+, killer seen 6+ | 976 | first hit r607, warned 6 rounds, held its ground, heading -, allies 8/16: 4/0, enemies 8: 2, altar 1 away |
| d1c79b48722a06c3 r1151 #5 | Prism killed carrying 200+ gems while tributing, grouped, even+, killer seen <6 | 934 | first hit r1150, warned 3 rounds, held its ground, heading -, allies 8/16: 4/0, enemies 8: 5, altar 1 away |
| 3d83d7f9bc0e7fcf r503 #3 | Prism killed carrying 200+ gems while walking with gems, alone v2+, killer seen <6 | 790 | first hit r503, warned 3 rounds, walked toward them, heading toward an altar, allies 8/16: 0/0, enemies 8: 3, altar 2 away |
| 8829b6190be197fe r661 #9 | Prism killed carrying 200+ gems while walking with gems, grouped, even+, killer seen 6+ | 751 | first hit r660, warned 14 rounds, held its ground, heading elsewhere, allies 8/16: 2/1, enemies 8: 1, altar 3 away |
| f3e1feed964bcda0 r679 #3 | Prism killed carrying 200+ gems while fighting, grouped, even+, killer seen <6 | 649 | first hit r678, warned 1 rounds, walked toward them, heading toward an altar, allies 8/16: 2/2, enemies 8: 2, altar 3 away |
| 668d02e95b8a454e r485 #3 | Prism killed carrying 200+ gems while walking with gems, grouped, even+, killer seen 6+ | 614 | first hit r484, warned 6 rounds, walked away, heading toward own spawn, allies 8/16: 1/0, enemies 8: 1, altar 12 away |
| 590d110dfeba742f r639 #7 | Prism killed carrying 200+ gems while walking with gems, grouped, even+, killer seen 6+ | 610 | first hit r639, warned 18 rounds, walked toward them, heading toward an altar, allies 8/16: 2/1, enemies 8: 1, altar 1 away; recall from r629 would have landed (closest enemy 3) |
| c2aa1cd814dbf6ad r606 #3 | Prism killed carrying 200+ gems while walking with gems, grouped, even+, killer seen 6+ | 543 | first hit r606, warned 9 rounds, held its ground, heading elsewhere, allies 8/16: 2/0, enemies 8: 2, altar 4 away |

## Deaths by situation

Death episodes only (killed by champions), one tag at a time. cost = bag + kill gold/4 + dead time.

**champion**

| champion | ocean-chybase deaths/game | opponent deaths/game | ocean-chybase cost/game | opponent cost/game | excess [95% CI] | examples |
| --- | --- | --- | --- | --- | --- | --- |
| Prism | 0.97 | 0.54 | 170 | 113 | 57.0 [11.9 .. 99.1] | 0187997b1f435613 r1902 #2 (2023); 590d110dfeba742f r757 #7 (1596) |
| Issac | 0.85 | 0.49 | 67.1 | 39.9 | 27.2 [13.4 .. 40.9] | 0187997b1f435613 r1294 #1 (285); 9e16da8a6089ae60 r581 #6 (224) |
| Cassi | 1.12 | 0.82 | 90.4 | 66.2 | 24.3 [1.4 .. 49.3] | e132010ccdc90093 r1159 #4 (273); 0187997b1f435613 r1618 #0 (244) |
| Marcella | 0.26 | 0.12 | 20.3 | 6.8 | 13.4 [2.2 .. 29.2] | 054c002144d1fa1d r1280 #1 (994); 409667189052fa9c r597 #3 (196) |
| Willow | 0.63 | 0.45 | 33.1 | 24.7 | 8.4 [-2.7 .. 19.3] | 87c807aaaf6c2e10 r550 #5 (136); 4bf0ccca1978704a r508 #4 (94.1) |
| Vesper Vale | 0.55 | 0.28 | 42.6 | 34.8 | 7.9 [-8.2 .. 21.5] | a6e2109cda1e704c r824 #6 (1152); 3d83d7f9bc0e7fcf r453 #0 (167) |
| Heart of Ruin | 0.39 | 0.36 | 23.5 | 18.9 | 4.6 [-3.1 .. 12.8] | e41fa249c71d8f56 r348 #11 (233); 0eb32fdc0663e917 r724 #5 (146) |
| Ren | 0.23 | 0.23 | 16.1 | 12.4 | 3.8 [-2.3 .. 10.7] | fcfc7f1fe137a071 r650 #5 (266); 0287d0c58dc7b23c r1229 #9 (133) |
| Ryth | 0.23 | 0.17 | 13.2 | 10.2 | 3.0 [-2.8 .. 9.9] | 6cd1642de67b6c70 r670 #6 (136); 98692bb109fde7ae r339 #0 (123) |
| Vendetta | 0.19 | 0.16 | 10.2 | 9.0 | 1.2 [-3.8 .. 5.6] | 573522a17f1193a8 r243 #8 (98.3); 3fd3f289f3cff38d r348 #0 (96.2) |
| Varg | 0.08 | 0.10 | 4.5 | 5.5 | -0.9 [-4.3 .. 2.3] | cfd6df385dd2fb72 r706 #9 (78.7); 1a980f86f97a8bc9 r333 #4 (75.9) |
| Tavi | 0.11 | 0.07 | 5.5 | 7.3 | -1.8 [-10.1 .. 5.0] | ea51c8b1b8d86b84 r1056 #5 (104); 2174fe2c1aa66d0b r457 #11 (67.5) |

**bag**

| bag | ocean-chybase deaths/game | opponent deaths/game | ocean-chybase cost/game | opponent cost/game | excess [95% CI] | examples |
| --- | --- | --- | --- | --- | --- | --- |
| 1-49 | 2.08 | 1.22 | 156 | 88.2 | 68.2 [41.0 .. 94.4] | 590d110dfeba742f r1048 #5 (164); 590d110dfeba742f r644 #5 (161) |
| 0 | 2.79 | 2.03 | 149 | 108 | 41.9 [-2.6 .. 85.1] | 590d110dfeba742f r906 #6 (128); 590d110dfeba742f r1124 #6 (128) |
| 200+ | 0.21 | 0.15 | 119 | 96.2 | 22.6 [-8.5 .. 57.2] | 0187997b1f435613 r1902 #2 (2023); 590d110dfeba742f r757 #7 (1596) |
| 50-199 | 0.51 | 0.38 | 71.5 | 56.3 | 15.3 [-8.0 .. 38.3] | 0187997b1f435613 r1294 #1 (285); 0187997b1f435613 r1618 #0 (244) |

**doing before the first hit**

| doing before the first hit | ocean-chybase deaths/game | opponent deaths/game | ocean-chybase cost/game | opponent cost/game | excess [95% CI] | examples |
| --- | --- | --- | --- | --- | --- | --- |
| walking with gems | 1.75 | 0.97 | 203 | 113 | 90.5 [34.3 .. 140] | 590d110dfeba742f r757 #7 (1596); 3d83d7f9bc0e7fcf r503 #3 (790) |
| walking | 2.25 | 1.65 | 128 | 94.6 | 33.5 [-2.3 .. 73.9] | a6e2109cda1e704c r469 #8 (146); b93ae9243fde1d27 r699 #7 (145) |
| fighting | 1.11 | 0.75 | 90.7 | 68.1 | 22.6 [-18.8 .. 49.9] | f3e1feed964bcda0 r679 #3 (649); 409667189052fa9c r786 #2 (495) |
| farming | 0.21 | 0.16 | 13.8 | 10.5 | 3.3 [-1.7 .. 8.2] | e41fa249c71d8f56 r620 #9 (145); 590d110dfeba742f r1124 #6 (128) |
| stunned/oof | 0.04 | 0.02 | 2.7 | 1.1 | 1.7 [-0.5 .. 4.0] | 4e2e0622f49a0fed r659 #8 (202); b0507eae226a8ef3 r508 #2 (86.5) |
| recalling | 0.04 | 0.03 | 3.4 | 2.7 | 0.7 [-2.6 .. 3.7] | 590d110dfeba742f r644 #5 (161); 6d7b23c09fce41d0 r837 #8 (117) |
| on spawn | 0.00 | 0.00 | 0.2 | 0.2 | 0.0 [0.0 .. 0.0] | 904065d9ecade03e r632 #2 (57.3) |
| waiting | 0.10 | 0.08 | 10.5 | 10.7 | -0.1 [-11.8 .. 10.4] | d52aa01386fc2a6e r1140 #2 (996); eea272635d75c81e r682 #2 (105) |
| holding | 0.02 | 0.03 | 1.2 | 1.7 | -0.5 [-2.5 .. 1.2] | 606d969a8b61b62b r516 #4 (106); 13901004cfeb9f26 r1324 #0 (68.5) |
| idle | 0.00 | 0.03 | 0.2 | 1.5 | -1.3 [-2.9 .. -0.2] | ea51c8b1b8d86b84 r1023 #4 (53.4) |
| tributing | 0.06 | 0.06 | 42.1 | 44.5 | -2.3 [-31.2 .. 27.4] | 0187997b1f435613 r1902 #2 (2023); a6e2109cda1e704c r915 #9 (1257) |

**numbers at the first hit**

| numbers at the first hit | ocean-chybase deaths/game | opponent deaths/game | ocean-chybase cost/game | opponent cost/game | excess [95% CI] | examples |
| --- | --- | --- | --- | --- | --- | --- |
| grouped, even+ | 2.73 | 1.87 | 247 | 181 | 66.5 [23.0 .. 104] | a6e2109cda1e704c r915 #9 (1257); be8613adeefa3594 r814 #3 (1156) |
| grouped, outnumbered | 1.68 | 1.07 | 139 | 87.8 | 51.1 [5.1 .. 101] | 590d110dfeba742f r757 #7 (1596); a6e2109cda1e704c r824 #6 (1152) |
| alone v2+ | 0.78 | 0.54 | 69.7 | 52.8 | 16.9 [-8.6 .. 44.0] | 3d83d7f9bc0e7fcf r503 #3 (790); 34d9a8e31c025382 r970 #6 (536) |
| alone v1 | 0.40 | 0.30 | 40.2 | 26.8 | 13.5 [-11.3 .. 42.2] | 0187997b1f435613 r1902 #2 (2023); 0187997b1f435613 r1361 #2 (385) |

**warning**

| warning | ocean-chybase deaths/game | opponent deaths/game | ocean-chybase cost/game | opponent cost/game | excess [95% CI] | examples |
| --- | --- | --- | --- | --- | --- | --- |
| seen 6+ | 2.96 | 2.08 | 238 | 148 | 89.7 [29.9 .. 147] | 2823b6e0a36021e0 r608 #4 (976); 8829b6190be197fe r661 #9 (751) |
| seen <6 | 1.70 | 0.93 | 163 | 98.6 | 64.3 [24.4 .. 106] | 0187997b1f435613 r1902 #2 (2023); 590d110dfeba742f r757 #7 (1596) |
| unseen | 0.93 | 0.77 | 95.6 | 102 | -6.0 [-39.3 .. 18.4] | a6e2109cda1e704c r915 #9 (1257); be8613adeefa3594 r814 #3 (1156) |

**half**

| half | ocean-chybase deaths/game | opponent deaths/game | ocean-chybase cost/game | opponent cost/game | excess [95% CI] | examples |
| --- | --- | --- | --- | --- | --- | --- |
| own | 4.12 | 2.56 | 377 | 243 | 134 [47.3 .. 218] | 0187997b1f435613 r1902 #2 (2023); 590d110dfeba742f r757 #7 (1596) |
| mid | 0.62 | 0.50 | 51.2 | 40.0 | 11.2 [-9.4 .. 31.5] | 9babbe90d8eae8b8 r512 #3 (506); 606d969a8b61b62b r498 #6 (465) |
| enemy | 0.86 | 0.71 | 67.7 | 64.9 | 2.7 [-24.8 .. 30.5] | 8829b6190be197fe r661 #9 (751); 8829b6190be197fe r1115 #9 (487) |

## Avoidable bag losses

Deaths with gems where the replay shows a rule-checked alternative, had the enemy acted the same. **recall window**: a killer was in the victim's sight with no damage or stun to it for 6+ rounds before the first hit, so a recall started at the window's start (5 turn ends; only damage or a stun cancels it) would have landed first; with an enemy within 4 during the window the recall may itself have drawn the attack, so those gems are also given apart. **altar**: within 40 rounds before dying it stood within 1 of an altar the enemy had not locked, carrying at least half the final bag, and a tribute started then (ceil(bag/10) turn ends; only a stun cancels it) would have completed before the death, with no stun on it in that span; split by whether an enemy was within 8 then (with one near, the tribute itself may have drawn the attack sooner). Look at: recall combat/fight.cc want_home / recall_line (recall on sight with a bag); economy/bank.cc continue_recall; altar economy/bank.cc banks_bag / retaining_gems / submit_here (bank at the altar passed).

| side | bag gems lost/game | recall window/game | gems | gems, no enemy within 4 in the window | altar, no enemy within 8/game | gems | altar, enemy within 8/game | gems |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ocean-chybase | 192 | 0.82 | 45.1 | 22.0 | 0.01 | 0.3 | 0.08 | 3.3 |
| opponent | 146 | 0.44 | 18.7 | 3.4 | 0.00 | 0.0 | 0.03 | 1.3 |

Largest ocean-chybase recall-avoidable deaths:

- 590d110dfeba742f r639 #7 Prism bag 536: killer in sight from r621, no damage from r629 (closest enemy 3), first hit r639; walking with gems, grouped, even+, own half
- 08383228b8a7836e r979 #8 Prism bag 497: killer in sight from r919, no damage from r939 (closest enemy 5), first hit r977; walking with gems, grouped, even+, own half
- 8829b6190be197fe r1115 #9 Prism bag 443: killer in sight from r1106, no damage from r1106 (closest enemy 5), first hit r1112; walking with gems, grouped, outnumbered, enemy half
- 1ac3920a45c1fd17 r556 #8 Prism bag 442: killer in sight from r529, no damage from r541 (closest enemy 5), first hit r556; walking with gems, grouped, even+, own half
- 8a1fabe65a0d8d1c r561 #4 Prism bag 433: killer in sight from r542, no damage from r551 (closest enemy 3), first hit r557; walking with gems, grouped, outnumbered, own half
- fb98def7dc7f5b28 r1020 #8 Prism bag 428: killer in sight from r983, no damage from r990 (closest enemy 5), first hit r1016; walking with gems, grouped, even+, own half
- b0507eae226a8ef3 r321 #2 Prism bag 301: killer in sight from r308, no damage from r308 (closest enemy 5), first hit r321; walking with gems, grouped, even+, own half
- 5385a404c1c191aa r539 #10 Prism bag 289: killer in sight from r520, no damage from r523 (closest enemy 6), first hit r538; fighting, alone v1, own half

Largest ocean-chybase altar-avoidable deaths:

- 1540393f83afda40 r570 #6 Prism bag 228: by an altar at r536 with 205 (tribute 21 rounds, 3 enemies within 8), died 34 rounds later, fighting
- 409667189052fa9c r597 #3 Marcella bag 109: by an altar at r582 with 109 (tribute 11 rounds, 3 enemies within 8), died 15 rounds later, walking with gems
- 3d83d7f9bc0e7fcf r453 #0 Vesper Vale bag 84: by an altar at r442 with 84 (tribute 9 rounds, 4 enemies within 8), died 11 rounds later, walking with gems
- b235ee120724acbe r944 #9 Prism bag 65: by an altar at r935 with 65 (tribute 7 rounds, 3 enemies within 8), died 9 rounds later, fighting
- 1d207177e703e6b5 r954 #8 Prism bag 47: by an altar at r946 with 47 (tribute 5 rounds, 0 enemies within 8), died 8 rounds later, fighting
- d1c79b48722a06c3 r177 #5 Prism bag 42: by an altar at r166 with 42 (tribute 5 rounds, 4 enemies within 8), died 11 rounds later, walking with gems
- 590d110dfeba742f r1048 #5 Cassi bag 36: by an altar at r1033 with 25 (tribute 3 rounds, 1 enemies within 8), died 15 rounds later, fighting
- 63271fc5eac82e6d r1299 #10 Marcella bag 36: by an altar at r1294 with 36 (tribute 4 rounds, 3 enemies within 8), died 5 rounds later, tributing

## Death hazard by activity

Champion-rounds spent on each activity (analysis/macro.py turn classes) and deaths to champions whose fatal damage began right after that activity, per 1000 such rounds, so a side is not penalised for doing more of something. Gems = bag gems lost in those deaths.

| activity | ocean-chybase rounds/game | ocean-chybase deaths per 1000 | ocean-chybase gems lost/game | opponent rounds/game | opponent deaths per 1000 | opponent gems lost/game |
| --- | --- | --- | --- | --- | --- | --- |
| walking | 1205 | 1.87 | 4.6 | 1220 | 1.35 | 6.0 |
| walking with gems | 1287 | 1.36 | 110 | 1268 | 0.77 | 60.6 |
| fighting | 131 | 8.46 | 31.4 | 134 | 5.56 | 28.6 |
| farming | 820 | 0.26 | 1.8 | 855 | 0.19 | 1.6 |
| waiting | 143 | 0.73 | 4.8 | 210 | 0.38 | 6.4 |
| tributing | 76.0 | 0.82 | 38.1 | 110 | 0.57 | 40.7 |
| recalling | 187 | 0.20 | 0.9 | 188 | 0.16 | 1.1 |
| stunned/oof | 7.1 | 5.26 | 0.9 | 8.3 | 2.02 | 0.1 |
| holding | 131 | 0.13 | 0.1 | 141 | 0.18 | 0.3 |
| idle | 58.7 | 0.07 | 0.0 | 58.2 | 0.43 | 0.2 |
| on spawn | 46.8 | 0.09 | 0.1 | 45.5 | 0.09 | 0.0 |

## Bag exposure

Champion-rounds alive carrying a bag of each size, and deaths with that bag per 1000 such rounds (a hazard rate, so a side that carries more is not penalised for carrying).

| champion | bag | ocean-chybase rounds/game | ocean-chybase deaths | ocean-chybase per 1000 | opponent rounds/game | opponent deaths | opponent per 1000 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Cassi | 1-49 | 279 | 125 | 1.87 | 251 | 88 | 1.46 |
| Cassi | 50-199 | 6.5 | 23 | 14.64 | 24.1 | 21 | 3.62 |
| Cassi | 200+ | 0.5 | 1 | 8.06 | 1.9 | 1 | 2.14 |
| Heart of Ruin | 1-49 | 139 | 43 | 1.29 | 123 | 25 | 0.84 |
| Heart of Ruin | 50-199 | 7.1 | 6 | 3.50 | 19.6 | 2 | 0.42 |
| Heart of Ruin | 200+ | 0.7 | 0 | 0.00 | 0.2 | 0 | 0.00 |
| Issac | 1-49 | 309 | 105 | 1.41 | 280 | 55 | 0.82 |
| Issac | 50-199 | 7.4 | 15 | 8.49 | 28.2 | 15 | 2.21 |
| Issac | 200+ | 0.0 | 0 | - | 0.0 | 1 | - |
| Marcella | 1-49 | 52.5 | 24 | 1.90 | 49.3 | 6 | 0.51 |
| Marcella | 50-199 | 5.7 | 2 | 1.45 | 10.9 | 4 | 1.53 |
| Marcella | 200+ | 1.8 | 1 | 2.29 | 1.5 | 0 | 0.00 |
| Prism | 1-49 | 133 | 57 | 1.79 | 84.7 | 23 | 1.13 |
| Prism | 50-199 | 182 | 55 | 1.26 | 169 | 32 | 0.79 |
| Prism | 200+ | 152 | 49 | 1.35 | 265 | 31 | 0.49 |
| Ren | 1-49 | 86 | 28 | 1.36 | 86.5 | 20 | 0.96 |
| Ren | 50-199 | 3.8 | 4 | 4.38 | 5.8 | 0 | 0.00 |
| Ren | 200+ | 0.4 | 1 | 10.42 | 0.0 | 0 | - |
| Ryth | 1-49 | 57.9 | 18 | 1.29 | 51.6 | 15 | 1.21 |
| Ryth | 50-199 | 5.8 | 2 | 1.44 | 11.8 | 3 | 1.06 |
| Ryth | 200+ | 1.7 | 0 | 0.00 | 0.1 | 0 | 0.00 |
| Tavi | 1-49 | 14.3 | 3 | 0.87 | 11.1 | 5 | 1.87 |
| Tavi | 50-199 | 1.4 | 1 | 3.07 | 5.4 | 0 | 0.00 |
| Tavi | 200+ | 0.0 | 0 | - | 0.4 | 1 | 11.76 |
| Varg | 1-49 | 51.7 | 8 | 0.64 | 46.4 | 8 | 0.72 |
| Varg | 50-199 | 2.5 | 0 | 0.00 | 10.2 | 0 | 0.00 |
| Varg | 200+ | 0.0 | 0 | - | 0.3 | 0 | 0.00 |
| Vendetta | 1-49 | 123 | 20 | 0.68 | 115 | 11 | 0.40 |
| Vendetta | 50-199 | 6.3 | 2 | 1.32 | 22.7 | 1 | 0.18 |
| Vendetta | 200+ | 0.0 | 0 | - | 0.1 | 0 | 0.00 |
| Vesper Vale | 1-49 | 282 | 68 | 1.00 | 253 | 25 | 0.41 |
| Vesper Vale | 50-199 | 37.5 | 17 | 1.89 | 113 | 20 | 0.74 |
| Vesper Vale | 200+ | 2.7 | 1 | 1.55 | 9.4 | 4 | 1.78 |
| Willow | 1-49 | 97.2 | 32 | 1.37 | 80.8 | 27 | 1.39 |
| Willow | 50-199 | 2.1 | 1 | 1.96 | 2.8 | 1 | 1.49 |

## Fights lost

Engagements (analysis/fights.py) the side lost on net swing (kill gems + gold/4 - bags lost); these overlap the death episodes. numbers = own minus enemy champions within 8 at the start; absent = own champions 9-16 away at the start that never joined.

| numbers | initiator | help in reach | ocean-chybase lost/game | ocean-chybase gems/game | opponent lost/game | opponent gems/game | excess | examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| -1 | they started | no ally 9-16 | 0.41 | 52.8 | 0.20 | 27.6 | 25.2 | a6e2109cda1e704c r812 (2124); 3d83d7f9bc0e7fcf r502 (1542) |
| +1 | they started | absent ally 9-16 | 0.28 | 47.7 | 0.17 | 22.8 | 24.9 | a6e2109cda1e704c r912 (2396); 054c002144d1fa1d r1269 (1925) |
| +0 | we started | absent ally 9-16 | 0.19 | 28.9 | 0.10 | 7.9 | 21.0 | d1c79b48722a06c3 r1138 (1828); f3e1feed964bcda0 r677 (1211) |
| +0 | they started | no ally 9-16 | 0.48 | 50.1 | 0.27 | 32.9 | 17.2 | 1ac3920a45c1fd17 r556 (909); fb98def7dc7f5b28 r1016 (897) |
| +0 | they started | absent ally 9-16 | 0.42 | 48.2 | 0.30 | 31.6 | 16.6 | 0187997b1f435613 r1901 (3954); c2aa1cd814dbf6ad r605 (1091) |
| +0 | we started | no ally 9-16 | 0.20 | 27.0 | 0.12 | 10.9 | 16.1 | b0507eae226a8ef3 r319 (817); 0029cda7c31732f0 r671 (675) |
| +2+ | we started | no ally 9-16 | 0.11 | 20.6 | 0.07 | 4.8 | 15.8 | 2823b6e0a36021e0 r604 (1864); 9babbe90d8eae8b8 r499 (1015) |
| -2- | we started | no ally 9-16 | 0.20 | 23.3 | 0.13 | 13.0 | 10.3 | 409667189052fa9c r785 (891); 8a1fabe65a0d8d1c r555 (810) |
| -2- | they started | no ally 9-16 | 0.35 | 26.6 | 0.15 | 16.4 | 10.1 | 0302a22c88b0fd37 r510 (731); a167db445dea3979 r874 (449) |
| -2- | we started | absent ally 9-16 | 0.23 | 21.5 | 0.15 | 11.5 | 10.0 | 34d9a8e31c025382 r968 (1018); 409667189052fa9c r566 (784) |
| +2+ | they started | no ally 9-16 | 0.26 | 34.3 | 0.17 | 25.9 | 8.4 | be8613adeefa3594 r811 (2210); 63271fc5eac82e6d r1299 (737) |
| -2- | they started | absent ally 9-16 | 0.40 | 45.4 | 0.30 | 39.7 | 5.7 | d52aa01386fc2a6e r1133 (1949); 1ee0f91549531bc1 r651 (855) |
| -1 | we started | no ally 9-16 | 0.15 | 14.0 | 0.13 | 8.3 | 5.7 | a6e2109cda1e704c r459 (926); 054c002144d1fa1d r1514 (285) |
| +2+ | we started | absent ally 9-16 | 0.06 | 9.2 | 0.04 | 3.7 | 5.5 | 606d969a8b61b62b r497 (839); e8cee75bc53138cf r414 (336) |
| +2+ | they started | absent ally 9-16 | 0.16 | 11.3 | 0.12 | 9.0 | 2.3 | 0187997b1f435613 r1618 (330); e41fa249c71d8f56 r612 (218) |
| -1 | they started | absent ally 9-16 | 0.36 | 32.0 | 0.28 | 30.4 | 1.6 | 08383228b8a7836e r977 (1022); 67e52ab3b3e7d814 r577 (668) |
| +1 | we started | no ally 9-16 | 0.10 | 7.7 | 0.11 | 14.0 | -6.3 | 843a3cb81a0305b1 r742 (288); 848bc6d054ddd262 r648 (155) |
| +1 | we started | absent ally 9-16 | 0.05 | 3.4 | 0.08 | 11.3 | -7.9 | a002a0c730014584 r627 (299); ce006c4d280f1855 r362 (104) |
| -1 | we started | absent ally 9-16 | 0.16 | 11.4 | 0.14 | 22.3 | -10.9 | 843a3cb81a0305b1 r854 (270); 84ccdc9c511aaa8c r622 (235) |
| +1 | they started | no ally 9-16 | 0.25 | 20.5 | 0.25 | 31.8 | -11.3 | 668d02e95b8a454e r484 (1124); 946de16d7ecbf661 r477 (383) |

Absent allies 9-16 away in lost fights, by what they were doing: ocean-chybase: walking 294, walking with gems 269, farming 156, recalling 37, holding 30, idle 29; opponent: walking 237, walking with gems 194, farming 141, waiting 25, holding 22, recalling 20.

## ocean-chybase's losses against its wins

Cluster cost per game in the focus team's losses minus its wins (top 12): the situations that most separate a loss from a win. Partly reverse causality (a losing side is behind and fights at a disadvantage); the round column shows when they happen.

| situation | in losses | in wins | difference | median round |
| --- | --- | --- | --- | --- |
| Prism killed carrying 200+ gems while walking with gems, grouped, even+, killer seen 6+ | 29.9 | 9.7 | 20.2 | 577 |
| Prism killed carrying 200+ gems while walking with gems, alone v2+, killer seen 6+ | 11.6 | 0.0 | 11.6 | 827 |
| Prism killed carrying 200+ gems while walking with gems, grouped, outnumbered, killer seen 6+ | 11.3 | 0.0 | 11.3 | 567 |
| Prism killed carrying 200+ gems while walking with gems, grouped, even+, killer seen <6 | 10.1 | 0.0 | 10.1 | 547 |
| Prism killed carrying 200+ gems while fighting, grouped, even+, killer seen <6 | 10.0 | 0.0 | 10.0 | 673 |
| Cassi killed carrying 0 gems while walking, grouped, outnumbered, killer seen 6+ | 8.7 | 0.0 | 8.7 | 740 |
| Marcella killed carrying 200+ gems while tributing, grouped, even+, killer unseen | 6.7 | 0.0 | 6.7 | 1280 |
| Prism killed carrying 50-199 gems while walking with gems, grouped, even+, killer seen 6+ | 9.3 | 2.7 | 6.7 | 484 |
| Prism killed carrying 200+ gems while tributing, grouped, even+, killer seen 6+ | 6.6 | 0.0 | 6.6 | 608 |
| invaded 3$ 8G group (own half): ours 21+ away | 6.5 | 0.0 | 6.5 | 266 |
| Prism killed carrying 0 gems while walking, grouped, outnumbered, killer seen 6+ | 5.9 | 0.0 | 5.9 | 1030 |
| Prism killed carrying 50-199 gems while walking with gems, grouped, even+, killer seen <6 | 6.7 | 1.0 | 5.7 | 632 |
