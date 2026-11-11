# Loss episodes: where value is lost, clustered and priced

Set: replays/batch-20261111-183545-ab-chy-vs-ocean-d18-hold (240 games, 121 clusters, focus charybdis-5564637); 240 games, charybdis-5564637 won 148. Each side's losses are split into disjoint episodes priced in gems (deaths: bag + kill gold/4 + dead time at the game's earn rate; camp deaths; camps lost to the enemy; stalls of 10+ rounds), tagged with the situation and clustered. Costs are per game; "excess" is charybdis-5564637 minus opponent in the same games, with a 95% cluster-bootstrap CI over map pairs or ladder groups. Examples are `analysis dir rROUND #champion (cost)`: open them with `py tools/replay/triage.py DIR --team NAME` (the game's turning points) or `py tools/replay/narrate.py` for a turn-level transcript.

Earn rate (gems per alive champion-round, both teams): mean 0.294, so a 60-round death costs about 17.7 gems of time.

## Cost by kind

| kind | charybdis-5564637 cost/game | opponent cost/game | excess | charybdis-5564637 in its wins | charybdis-5564637 in its losses |
| --- | --- | --- | --- | --- | --- |
| death | 348 | 496 | -148 | 160 | 651 |
| camp_death | 12.6 | 12.9 | -0.3 | 10.9 | 15.2 |
| camp_lost | 329 | 369 | -39.6 | 229 | 489 |
| stall | 32.3 | 16.8 | 15.4 | 40.4 | 19.1 |

## Top weaknesses: clusters by excess cost

Every episode kind, clustered by champion and situation (deaths: bag and what the victim was doing the round before the fatal damage began). Sorted by charybdis-5564637's cost per game minus opponent's for the same cluster in the same games; clusters with fewer than 4 focus episodes or 3 games are left to the list of single expensive episodes below. "mix" gives each secondary tag's most common value among the focus episodes. cf columns: share of the cluster's focus bag gems that a recall in the safe window / a tribute at the last altar passed would have saved.

| situation | charybdis-5564637 n/game | opponent n/game | charybdis-5564637 cost/game | opponent cost/game | excess [95% CI] | mix | cf recall | cf altar | look at | examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Willow waiting 10+ rounds, by a tributing ally | 0.76 | 0.37 | 9.7 | 4.9 | 4.8 [0.6 .. 10.0] | r801+ 65%, then walk 74% | - | - | combat/support.cc local_support / support_endpoint (who guards a tribute); economy/bank.cc banks_bag / retaining_gems (the bag size sets the tribute length, ceil(bag/10) turns) | a6e2109cda1e704c r489 #4 (104); a6e2109cda1e704c r922 #4 (99.9); 054c002144d1fa1d r841 #7 (75.6) |
| camp stolen (enemy half): ours left at even numbers or better | 0.16 | 0.07 | 6.2 | 2.5 | 3.7 [0.9 .. 6.6] | 2$ 13% | - | - | economy/capture.cc holding_capture / contest_capture; economy/crew.cc (who stays to hold) | 3d83d7f9bc0e7fcf r743 (130); 6b20d3a3ede0f4b3 r297 (96.5); f3e1feed964bcda0 r495 (88.5) |
| Prism killed with 200+ gems while tributing | 0.04 | 0.03 | 33.5 | 29.8 | 3.7 [-23.5 .. 27.8] | grouped, even+ 70%, unseen 50%, own half 100%, held its ground 100%, heading - 90% | 0% | 0% | economy/bank.cc submit_here / continue_tribute (start or keep a tribute with enemies near) | 590d110dfeba742f r754 #3 (1496); a6e2109cda1e704c r628 #3 (1114); 054c002144d1fa1d r1075 #5 (945) |
| camp stolen (enemy half): ours left, outnumbered | 0.26 | 0.20 | 11.5 | 8.4 | 3.1 [-1.2 .. 7.9] | 2$ 13% | - | - | economy/capture.cc holding_capture / contest_capture; economy/crew.cc (who stays to hold) | b586c8139dd6000c r388 (135); 74929a731b9be225 r618 (112); 20bb6eff5cf56cb4 r684 (111) |
| Marcella waiting 10+ rounds, by a tributing ally | 0.19 | 0.03 | 3.1 | 0.5 | 2.7 [0.4 .. 6.1] | r401-800 54%, then fight 63% | - | - | combat/support.cc local_support / support_endpoint (who guards a tribute); economy/bank.cc banks_bag / retaining_gems (the bag size sets the tribute length, ceil(bag/10) turns) | 054c002144d1fa1d r951 #6 (39.9); 054c002144d1fa1d r1723 #6 (36.7); 409667189052fa9c r913 #8 (36.2) |
| camp stolen (enemy half): ours within 3, outheld | 0.08 | 0.03 | 3.6 | 1.1 | 2.5 [0.4 .. 4.5] | 2$ 21% | - | - | economy/capture.cc holding_capture / contest_capture; economy/crew.cc (who stays to hold) | 0f714f02b91ad2f5 r213 (152); d5f3e0d2e3015285 r55 (101); 37f390012887317e r615 (87.5) |
| Ryth waiting 10+ rounds, by a tributing ally | 0.31 | 0.03 | 2.8 | 0.3 | 2.5 [0.2 .. 6.3] | r801+ 73%, then fight 80% | - | - | combat/support.cc local_support / support_endpoint (who guards a tribute); economy/bank.cc banks_bag / retaining_gems (the bag size sets the tribute length, ceil(bag/10) turns) | 2823b6e0a36021e0 r634 #6 (29.8); 8a1fabe65a0d8d1c r745 #6 (25.0); 8a1fabe65a0d8d1c r653 #6 (24.3) |
| camp invaded (own half): ours 9-20 away | 1.41 | 1.45 | 59.5 | 57.1 | 2.4 [-12.4 .. 15.3] | 2$ 9% | - | - | economy/farm.cc farm (target choice and map coverage); economy/altar_guard.cc guard_turn | eb2a660ba3c0bb9f r684 (201); 37f390012887317e r420 (158); a54a4d627db9535a r271 (152) |
| Heart of Ruin killed with 0 gems while walking | 0.17 | 0.11 | 7.7 | 5.5 | 2.2 [-1.9 .. 6.7] | grouped, even+ 51%, seen 6+ 56%, own half 59%, held its ground 51%, heading elsewhere 59% | - | - | model/safety.cc (threat model), combat/guard.cc guard_work / step_safely (step guard) | 8829b6190be197fe r1192 #5 (72.4); 67d5cbd0dafe8fa0 r1101 #11 (62.6); 96ad0d0ecdf222f5 r760 #5 (62.4) |
| camp stolen (own half): ours within 3, outheld | 0.10 | 0.07 | 5.1 | 2.9 | 2.2 [-0.9 .. 5.8] | 5G 30% | - | - | economy/capture.cc holding_capture / contest_capture; economy/crew.cc (who stays to hold) | b586c8139dd6000c r167 (154); 8328a5ed4ca9e158 r395 (127); 8328a5ed4ca9e158 r133 (126) |
| Cassi killed with 50-199 gems while walking with gems | 0.05 | 0.04 | 7.6 | 5.6 | 2.0 [-2.8 .. 7.4] | grouped, even+ 58%, seen 6+ 50%, own half 75%, walked toward them 33%, heading toward an altar 50% | 50% | 0% | economy/bank.cc carry_bag / banks_bag (route and when to bank); combat/fight.cc want_home | 5f7eb96213aa4522 r330 #0 (270); 762aee3cf5e9f49a r472 #1 (214); be8613adeefa3594 r666 #7 (158) |
| Prism killed by a Elk camp | 0.02 | 0.02 | 4.6 | 2.8 | 1.8 [-0.1 .. 4.8] | 200+ gems 75%, also hit by champions 50% | 0% | 0% | economy/camps.cc (camp damage and clear time), combat/fight.cc camp_exit_way, economy/farm.cc rated_beaten | 409667189052fa9c r234 #7 (402); 5f7eb96213aa4522 r229 #2 (355); 9e16da8a6089ae60 r176 #2 (256) |
| camp contested (enemy half): ours left at even numbers or better | 0.15 | 0.13 | 7.8 | 6.2 | 1.6 [-2.3 .. 5.0] | 1G 2W 9% | - | - | economy/capture.cc contest_capture / yield_capture; combat/plan.cc (fight on the tiles) | 0f714f02b91ad2f5 r293 (152); 5a23f4e94cb0c8da r564 (128); 0f30bda5e7a5fbdc r364 (112) |
| Issac killed by a Elk camp | 0.03 | 0.01 | 1.9 | 0.3 | 1.5 [0.3 .. 3.7] | 0 gems 33%, camp only 83% | 0% | 0% | economy/camps.cc (camp damage and clear time), combat/fight.cc camp_exit_way, economy/farm.cc rated_beaten | 9e16da8a6089ae60 r264 #1 (167); db10f4e4b84abbc0 r158 #5 (108); 9f4a52856f64f1bb r53 #2 (62.5) |
| Issac waiting 10+ rounds, by a tributing ally | 0.15 | 0.03 | 1.6 | 0.2 | 1.4 [-0.1 .. 4.0] | r801+ 67%, then walk 58% | - | - | combat/support.cc local_support / support_endpoint (who guards a tribute); economy/bank.cc banks_bag / retaining_gems (the bag size sets the tribute length, ceil(bag/10) turns) | 590d110dfeba742f r766 #2 (30.9); 590d110dfeba742f r654 #2 (27.8); 590d110dfeba742f r691 #2 (25.5) |
| Vesper Vale killed with 50-199 gems while walking with gems | 0.05 | 0.05 | 6.8 | 5.4 | 1.4 [-3.7 .. 7.9] | alone v2+ 58%, unseen 50%, own half 92%, walked toward them 75%, heading toward an altar 83% | 11% | 0% | economy/bank.cc carry_bag / banks_bag (route and when to bank); combat/fight.cc want_home | 9a770f6d72daba7d r834 #6 (194); b93ae9243fde1d27 r558 #0 (170); 762aee3cf5e9f49a r425 #0 (162) |
| camp stolen (mid half): ours died | 0.12 | 0.11 | 7.1 | 5.8 | 1.3 [-3.5 .. 8.5] | 4$ 5G 2W 17% | - | - | economy/capture.cc holding_capture / contest_capture; economy/crew.cc (who stays to hold) | 0287d0c58dc7b23c r575 (224); 5a05be9e5425212b r105 (155); 031e6ce6a8cee299 r333 (137) |
| Ren killed with 0 gems while walking | 0.11 | 0.08 | 5.2 | 4.0 | 1.2 [-1.3 .. 4.2] | grouped, outnumbered 58%, seen 6+ 88%, own half 85%, walked toward them 50%, heading toward an altar 54% | - | - | model/safety.cc (threat model), combat/guard.cc guard_work / step_safely (step guard) | a6e2109cda1e704c r822 #5 (98.8); d1c79b48722a06c3 r863 #3 (69.9); 383dccc831f852e0 r1394 #5 (67.9) |
| Heart of Ruin waiting 10+ rounds, by a tributing ally | 0.07 | 0.03 | 1.1 | 0.2 | 0.9 [-0.1 .. 2.5] | r401-800 50%, then end 44% | - | - | combat/support.cc local_support / support_endpoint (who guards a tribute); economy/bank.cc banks_bag / retaining_gems (the bag size sets the tribute length, ceil(bag/10) turns) | 8829b6190be197fe r807 #5 (39.4); 8829b6190be197fe r940 #5 (27.6); 8829b6190be197fe r1462 #5 (25.8) |
| Varg killed with 0 gems while fighting | 0.02 | 0.00 | 0.9 | 0.0 | 0.9 [0.0 .. 1.9] | grouped, even+ 50%, seen 6+ 50%, own half 50%, walked toward them 50%, heading - 50% | - | - | combat/plan.cc (strike search) and combat/fight.cc prey / chase_with_guard (who to engage) | b586c8139dd6000c r465 #11 (64.7); f5666e16527d008a r674 #4 (64.1); 1d207177e703e6b5 r22 #4 (40.5) |
| Willow killed with 1-49 gems while fighting | 0.02 | 0.00 | 1.1 | 0.3 | 0.8 [-0.5 .. 2.0] | grouped, outnumbered 50%, seen <6 50%, own half 75%, walked toward them 75%, heading toward an altar 50% | 50% | 0% | combat/plan.cc (strike search) and combat/fight.cc prey / chase_with_guard (who to engage) | 2823b6e0a36021e0 r544 #11 (88.8); 0c604698a62ff9d0 r193 #4 (76.9); e63fe38b24e7f12d r542 #5 (56.3) |
| Willow waiting 10+ rounds, facing enemies within 9 | 0.09 | 0.05 | 1.1 | 0.3 | 0.8 [0.0 .. 1.8] | r401-800 64%, then walk 86% | - | - | combat/fight.cc want_home / prey (engage or leave a standoff); combat/plan.cc (strike search) | 054c002144d1fa1d r1838 #7 (52.4); 9e16da8a6089ae60 r479 #4 (32.5); 843a3cb81a0305b1 r620 #10 (16.9) |
| camp contested (enemy half): ours died | 0.14 | 0.14 | 9.6 | 8.9 | 0.8 [-5.0 .. 7.4] | 1$ 1W 15% | - | - | economy/capture.cc contest_capture / yield_capture; combat/plan.cc (fight on the tiles) | fcfc7f1fe137a071 r575 (361); 80dc850a5d44d4c0 r795 (275); 5f7eb96213aa4522 r368 (220) |
| Prism waiting 10+ rounds, by a tributing ally | 0.04 | 0.00 | 0.8 | 0.0 | 0.7 [-0.0 .. 2.3] | r801+ 80%, then walk 40% | - | - | combat/support.cc local_support / support_endpoint (who guards a tribute); economy/bank.cc banks_bag / retaining_gems (the bag size sets the tribute length, ceil(bag/10) turns) | 590d110dfeba742f r910 #3 (66.4); a6e2109cda1e704c r836 #3 (30.0); 590d110dfeba742f r1156 #3 (25.5) |
| Prism waiting 10+ rounds, facing enemies within 9 | 0.08 | 0.03 | 0.8 | 0.2 | 0.6 [0.0 .. 1.5] | r801+ 53%, then fight 37% | - | - | combat/fight.cc want_home / prey (engage or leave a standoff); combat/plan.cc (strike search) | 054c002144d1fa1d r1857 #5 (46.3); 9e16da8a6089ae60 r494 #2 (23.9); 20bb6eff5cf56cb4 r706 #8 (13.2) |

The same without the champion (kind and situation only):

| situation | charybdis-5564637 n/game | opponent n/game | charybdis-5564637 cost/game | opponent cost/game | excess [95% CI] | mix | examples |
| --- | --- | --- | --- | --- | --- | --- | --- |
| any champion waiting 10+ rounds, by a tributing ally | 2.03 | 1.07 | 24.8 | 12.9 | 11.9 [0.6 .. 24.1] | r801+ 63%, then walk 46% | a6e2109cda1e704c r489 #4 (104); a6e2109cda1e704c r922 #4 (99.9) |
| camp stolen (enemy half): ours left at even numbers or better | 0.16 | 0.07 | 6.2 | 2.5 | 3.7 [0.9 .. 6.6] | 2$ 13% | 3d83d7f9bc0e7fcf r743 (130); 6b20d3a3ede0f4b3 r297 (96.5) |
| any champion killed by a Elk camp | 0.12 | 0.12 | 9.5 | 6.0 | 3.5 [0.4 .. 7.0] | 0 gems 36%, camp only 82% | 409667189052fa9c r234 #7 (402); 5f7eb96213aa4522 r229 #2 (355) |
| any champion killed with 200+ gems while tributing | 0.05 | 0.04 | 43.2 | 39.9 | 3.3 [-26.7 .. 30.8] | grouped, even+ 67%, unseen 58%, own half 100%, held its ground 100%, heading - 92% | 590d110dfeba742f r754 #3 (1496); be8613adeefa3594 r983 #6 (1325) |
| camp stolen (enemy half): ours left, outnumbered | 0.26 | 0.20 | 11.5 | 8.4 | 3.1 [-1.2 .. 7.9] | 2$ 13% | b586c8139dd6000c r388 (135); 74929a731b9be225 r618 (112) |
| any champion killed with 200+ gems while fighting | 0.03 | 0.04 | 17.5 | 15.0 | 2.5 [-17.1 .. 30.6] | grouped, even+ 83%, seen <6 50%, own half 83%, held its ground 50%, heading - 50% | a6e2109cda1e704c r1136 #3 (1435); a6e2109cda1e704c r881 #0 (1141) |
| camp stolen (enemy half): ours within 3, outheld | 0.08 | 0.03 | 3.6 | 1.1 | 2.5 [0.4 .. 4.5] | 2$ 21% | 0f714f02b91ad2f5 r213 (152); d5f3e0d2e3015285 r55 (101) |
| camp invaded (own half): ours 9-20 away | 1.41 | 1.45 | 59.5 | 57.1 | 2.4 [-12.4 .. 15.3] | 2$ 9% | eb2a660ba3c0bb9f r684 (201); 37f390012887317e r420 (158) |
| any champion killed with 50-199 gems while waiting | 0.01 | 0.00 | 2.2 | 0.0 | 2.2 [0.0 .. 4.9] | grouped, even+ 67%, seen <6 67%, own half 67%, held its ground 33%, heading toward an altar 67% | 355fa449489b5a43 r137 #0 (237); 36e1961039eaa1ab r202 #0 (190) |
| camp stolen (own half): ours within 3, outheld | 0.10 | 0.07 | 5.1 | 2.9 | 2.2 [-0.9 .. 5.8] | 5G 30% | b586c8139dd6000c r167 (154); 8328a5ed4ca9e158 r395 (127) |
| any champion waiting 10+ rounds, facing enemies within 9 | 0.41 | 0.22 | 3.4 | 1.3 | 2.2 [-0.1 .. 4.9] | r801+ 56%, then walk 52% | 054c002144d1fa1d r1838 #7 (52.4); 054c002144d1fa1d r1857 #5 (46.3) |
| camp contested (enemy half): ours left at even numbers or better | 0.15 | 0.13 | 7.8 | 6.2 | 1.6 [-2.3 .. 5.0] | 1G 2W 9% | 0f714f02b91ad2f5 r293 (152); 5a23f4e94cb0c8da r564 (128) |
| any champion killed with 200+ gems while walking | 0.00 | 0.00 | 1.4 | 0.0 | 1.4 [0.0 .. 4.1] | grouped, even+ 100%, seen <6 100%, own half 100%, held its ground 100%, heading elsewhere 100% | e132010ccdc90093 r825 #1 (327) |
| camp stolen (mid half): ours died | 0.12 | 0.11 | 7.1 | 5.8 | 1.3 [-3.5 .. 8.5] | 4$ 5G 2W 17% | 0287d0c58dc7b23c r575 (224); 5a05be9e5425212b r105 (155) |
| any champion killed with 200+ gems while waiting | 0.01 | 0.00 | 5.2 | 4.1 | 1.0 [-9.9 .. 12.6] | grouped, outnumbered 50%, seen <6 50%, enemy half 100%, held its ground 100%, heading - 100% | 1fe75c018cdec6b3 r1313 #9 (653); e461d84302229e72 r425 #8 (588) |

charybdis-5564637's single most expensive episodes (rare situations the clusters above leave out):

| game / round | episode | cost | tags |
| --- | --- | --- | --- |
| 0187997b1f435613 r1735 #6 | Prism killed carrying 200+ gems while walking with gems, alone v2+, killer unseen | 1602 | first hit r1735, warned -1 rounds, held its ground, heading toward an altar, allies 8/16: 0/3, enemies 8: 2, altar 1 away |
| 590d110dfeba742f r754 #3 | Prism killed carrying 200+ gems while tributing, grouped, even+, killer seen <6 | 1496 | first hit r753, warned 4 rounds, held its ground, heading -, allies 8/16: 3/0, enemies 8: 1, altar 1 away |
| a6e2109cda1e704c r1136 #3 | Prism killed carrying 200+ gems while fighting, grouped, even+, killer unseen | 1435 | first hit r1136, warned -1 rounds, held its ground, heading -, allies 8/16: 3/0, enemies 8: 4, altar 1 away |
| be8613adeefa3594 r983 #6 | Vesper Vale killed carrying 200+ gems while tributing, grouped, even+, killer unseen | 1325 | first hit r971, warned -1 rounds, held its ground, heading -, allies 8/16: 4/1, enemies 8: 4, altar 1 away |
| a6e2109cda1e704c r881 #0 | Vesper Vale killed carrying 200+ gems while fighting, grouped, even+, killer seen <6 | 1141 | first hit r880, warned 2 rounds, held its ground, heading -, allies 8/16: 4/0, enemies 8: 3, altar 1 away |
| a6e2109cda1e704c r628 #3 | Prism killed carrying 200+ gems while tributing, grouped, even+, killer unseen | 1114 | first hit r625, warned -1 rounds, held its ground, heading -, allies 8/16: 3/0, enemies 8: 3, altar 1 away |
| d52aa01386fc2a6e r1175 #11 | Tavi killed carrying 200+ gems while tributing, alone v1, killer unseen | 986 | first hit r1167, warned -1 rounds, held its ground, heading -, allies 8/16: 0/4, enemies 8: 1, altar 6 away |
| 054c002144d1fa1d r1075 #5 | Prism killed carrying 200+ gems while tributing, grouped, even+, killer unseen | 945 | first hit r1074, warned -1 rounds, held its ground, heading -, allies 8/16: 3/1, enemies 8: 3, altar 1 away |
| d52aa01386fc2a6e r975 #8 | Prism killed carrying 200+ gems while tributing, grouped, outnumbered, killer unseen | 902 | first hit r973, warned -1 rounds, held its ground, heading -, allies 8/16: 1/2, enemies 8: 4, altar 1 away |
| 6d7b23c09fce41d0 r1127 #3 | Prism killed carrying 200+ gems while tributing, grouped, even+, killer seen 6+ | 769 | first hit r1124, warned 14 rounds, held its ground, heading -, allies 8/16: 3/0, enemies 8: 2, altar 1 away |
| 762aee3cf5e9f49a r382 #3 | Prism killed carrying 200+ gems while walking with gems, alone v2+, killer seen 6+ | 678 | first hit r380, warned 56 rounds, walked away, heading toward own spawn, allies 8/16: 0/0, enemies 8: 3, altar 15 away; recall from r324 would have landed (closest enemy 4) |
| 1fe75c018cdec6b3 r1313 #9 | Prism killed carrying 200+ gems while waiting, grouped, outnumbered, killer seen <6 | 653 | first hit r1309, warned 1 rounds, held its ground, heading -, allies 8/16: 2/0, enemies 8: 5, altar 1 away |
| b93ae9243fde1d27 r471 #3 | Prism killed carrying 200+ gems while tributing, grouped, even+, killer unseen | 645 | first hit r470, warned -1 rounds, held its ground, heading -, allies 8/16: 1/3, enemies 8: 1, altar 1 away |
| d1c79b48722a06c3 r754 #0 | Prism killed carrying 200+ gems while walking with gems, alone v2+, killer unseen | 626 | first hit r753, warned -1 rounds, walked toward them, heading elsewhere, allies 8/16: 0/3, enemies 8: 2, altar 13 away |
| da301504f48cb738 r625 #10 | Prism killed carrying 200+ gems while tributing, grouped, outnumbered, killer seen <6 | 621 | first hit r623, warned 0 rounds, held its ground, heading elsewhere, allies 8/16: 2/1, enemies 8: 4, altar 1 away |

## Deaths by situation

Death episodes only (killed by champions), one tag at a time. cost = bag + kill gold/4 + dead time.

**champion**

| champion | charybdis-5564637 deaths/game | opponent deaths/game | charybdis-5564637 cost/game | opponent cost/game | excess [95% CI] | examples |
| --- | --- | --- | --- | --- | --- | --- |
| Tavi | 0.07 | 0.11 | 7.3 | 5.5 | 1.8 [-5.0 .. 10.1] | d52aa01386fc2a6e r1175 #11 (986); d52aa01386fc2a6e r730 #11 (81.8) |
| Varg | 0.10 | 0.08 | 5.5 | 4.5 | 0.9 [-2.3 .. 4.3] | 1a980f86f97a8bc9 r731 #9 (84.4); d0b90ec061c1d023 r446 #5 (79.8) |
| Vendetta | 0.16 | 0.19 | 9.0 | 10.2 | -1.2 [-5.6 .. 3.8] | 355fa449489b5a43 r137 #0 (237); cfd6df385dd2fb72 r782 #1 (81.9) |
| Ryth | 0.17 | 0.23 | 10.2 | 13.2 | -3.0 [-9.9 .. 2.8] | c932f858c8cf2c32 r301 #0 (123); fb98def7dc7f5b28 r686 #0 (111) |
| Ren | 0.23 | 0.23 | 12.4 | 16.1 | -3.8 [-10.7 .. 2.3] | a6e2109cda1e704c r425 #5 (117); a6e2109cda1e704c r822 #5 (98.8) |
| Heart of Ruin | 0.36 | 0.39 | 18.9 | 23.5 | -4.6 [-12.8 .. 3.1] | 0eb32fdc0663e917 r661 #11 (143); 80dc850a5d44d4c0 r706 #5 (123) |
| Vesper Vale | 0.28 | 0.55 | 34.8 | 42.6 | -7.9 [-21.5 .. 8.2] | be8613adeefa3594 r983 #6 (1325); a6e2109cda1e704c r881 #0 (1141) |
| Willow | 0.45 | 0.63 | 24.7 | 33.1 | -8.4 [-19.3 .. 2.7] | e3a39b895d585083 r386 #4 (117); b93ae9243fde1d27 r712 #4 (102) |
| Marcella | 0.12 | 0.26 | 6.8 | 20.3 | -13.4 [-29.2 .. -2.2] | 5f7eb96213aa4522 r334 #3 (135); e1a2ccd4068108bc r135 #10 (111) |
| Cassi | 0.82 | 1.12 | 66.2 | 90.4 | -24.3 [-49.3 .. -1.4] | 0187997b1f435613 r1759 #4 (356); 5f7eb96213aa4522 r330 #0 (270) |
| Issac | 0.49 | 0.85 | 39.9 | 67.1 | -27.2 [-40.9 .. -13.4] | e132010ccdc90093 r825 #1 (327); 0187997b1f435613 r945 #5 (269) |
| Prism | 0.54 | 0.97 | 113 | 170 | -57.0 [-99.1 .. -11.9] | 0187997b1f435613 r1735 #6 (1602); 590d110dfeba742f r754 #3 (1496) |

**bag**

| bag | charybdis-5564637 deaths/game | opponent deaths/game | charybdis-5564637 cost/game | opponent cost/game | excess [95% CI] | examples |
| --- | --- | --- | --- | --- | --- | --- |
| 50-199 | 0.38 | 0.51 | 56.3 | 71.5 | -15.3 [-38.3 .. 8.0] | 5f7eb96213aa4522 r330 #0 (270); 0187997b1f435613 r945 #5 (269) |
| 200+ | 0.15 | 0.21 | 96.2 | 119 | -22.6 [-57.2 .. 8.5] | 0187997b1f435613 r1735 #6 (1602); 590d110dfeba742f r754 #3 (1496) |
| 0 | 2.03 | 2.79 | 108 | 149 | -41.9 [-85.1 .. 2.6] | a6e2109cda1e704c r756 #1 (115); a6e2109cda1e704c r886 #1 (115) |
| 1-49 | 1.22 | 2.08 | 88.2 | 156 | -68.2 [-94.4 .. -41.0] | a6e2109cda1e704c r990 #1 (172); e461d84302229e72 r417 #6 (133) |

**doing before the first hit**

| doing before the first hit | charybdis-5564637 deaths/game | opponent deaths/game | charybdis-5564637 cost/game | opponent cost/game | excess [95% CI] | examples |
| --- | --- | --- | --- | --- | --- | --- |
| tributing | 0.06 | 0.06 | 44.5 | 42.1 | 2.3 [-27.4 .. 31.2] | 590d110dfeba742f r754 #3 (1496); be8613adeefa3594 r983 #6 (1325) |
| idle | 0.03 | 0.00 | 1.5 | 0.2 | 1.3 [0.2 .. 2.9] | a6a86ef2f3fb6e57 r668 #2 (102); 6d7b23c09fce41d0 r1920 #5 (61.9) |
| holding | 0.03 | 0.02 | 1.7 | 1.2 | 0.5 [-1.2 .. 2.5] | 37f390012887317e r148 #3 (131); 573522a17f1193a8 r159 #2 (66.1) |
| waiting | 0.08 | 0.10 | 10.7 | 10.5 | 0.1 [-10.4 .. 11.8] | 1fe75c018cdec6b3 r1313 #9 (653); e461d84302229e72 r425 #8 (588) |
| on spawn | 0.00 | 0.00 | 0.2 | 0.2 | -0.0 [-0.0 .. 0.0] | 012bacea9c1771a1 r680 #2 (55.2) |
| recalling | 0.03 | 0.04 | 2.7 | 3.4 | -0.7 [-3.7 .. 2.6] | fa418017d2527940 r499 #7 (216); 71f7f7e03e8fe3e3 r374 #2 (110) |
| stunned/oof | 0.02 | 0.04 | 1.1 | 2.7 | -1.7 [-4.0 .. 0.5] | 4f966aedadc68f12 r243 #8 (89.8); eb2a660ba3c0bb9f r568 #7 (71.4) |
| farming | 0.16 | 0.21 | 10.5 | 13.8 | -3.3 [-8.2 .. 1.7] | f3e1feed964bcda0 r640 #7 (124); fb17def467f54ea3 r189 #0 (119) |
| fighting | 0.75 | 1.11 | 68.1 | 90.7 | -22.6 [-49.9 .. 18.8] | a6e2109cda1e704c r1136 #3 (1435); a6e2109cda1e704c r881 #0 (1141) |
| walking | 1.65 | 2.25 | 94.6 | 128 | -33.5 [-73.9 .. 2.3] | e132010ccdc90093 r825 #1 (327); e41fa249c71d8f56 r304 #0 (233) |
| walking with gems | 0.97 | 1.75 | 113 | 203 | -90.5 [-140 .. -34.3] | 0187997b1f435613 r1735 #6 (1602); 762aee3cf5e9f49a r382 #3 (678) |

**numbers at the first hit**

| numbers at the first hit | charybdis-5564637 deaths/game | opponent deaths/game | charybdis-5564637 cost/game | opponent cost/game | excess [95% CI] | examples |
| --- | --- | --- | --- | --- | --- | --- |
| alone v1 | 0.30 | 0.40 | 26.8 | 40.2 | -13.5 [-42.2 .. 11.3] | d52aa01386fc2a6e r1175 #11 (986); 10bde3a3274409e1 r488 #3 (332) |
| alone v2+ | 0.54 | 0.78 | 52.8 | 69.7 | -16.9 [-44.0 .. 8.6] | 0187997b1f435613 r1735 #6 (1602); 762aee3cf5e9f49a r382 #3 (678) |
| grouped, outnumbered | 1.07 | 1.68 | 87.8 | 139 | -51.1 [-101 .. -5.1] | d52aa01386fc2a6e r975 #8 (902); 1fe75c018cdec6b3 r1313 #9 (653) |
| grouped, even+ | 1.87 | 2.73 | 181 | 247 | -66.5 [-104 .. -23.0] | 590d110dfeba742f r754 #3 (1496); a6e2109cda1e704c r1136 #3 (1435) |

**warning**

| warning | charybdis-5564637 deaths/game | opponent deaths/game | charybdis-5564637 cost/game | opponent cost/game | excess [95% CI] | examples |
| --- | --- | --- | --- | --- | --- | --- |
| unseen | 0.77 | 0.93 | 102 | 95.6 | 6.0 [-18.4 .. 39.3] | 0187997b1f435613 r1735 #6 (1602); a6e2109cda1e704c r1136 #3 (1435) |
| seen <6 | 0.93 | 1.70 | 98.6 | 163 | -64.3 [-106 .. -24.4] | 590d110dfeba742f r754 #3 (1496); a6e2109cda1e704c r881 #0 (1141) |
| seen 6+ | 2.08 | 2.96 | 148 | 238 | -89.7 [-147 .. -29.9] | 6d7b23c09fce41d0 r1127 #3 (769); 762aee3cf5e9f49a r382 #3 (678) |

**half**

| half | charybdis-5564637 deaths/game | opponent deaths/game | charybdis-5564637 cost/game | opponent cost/game | excess [95% CI] | examples |
| --- | --- | --- | --- | --- | --- | --- |
| enemy | 0.71 | 0.86 | 64.9 | 67.7 | -2.7 [-30.5 .. 24.8] | a6e2109cda1e704c r881 #0 (1141); 762aee3cf5e9f49a r382 #3 (678) |
| mid | 0.50 | 0.62 | 40.0 | 51.2 | -11.2 [-31.5 .. 9.4] | 2823b6e0a36021e0 r510 #10 (598); 28f737927a50f26b r504 #3 (321) |
| own | 2.56 | 4.12 | 243 | 377 | -134 [-218 .. -47.3] | 0187997b1f435613 r1735 #6 (1602); 590d110dfeba742f r754 #3 (1496) |

## Avoidable bag losses

Deaths with gems where the replay shows a rule-checked alternative, had the enemy acted the same. **recall window**: a killer was in the victim's sight with no damage or stun to it for 6+ rounds before the first hit, so a recall started at the window's start (5 turn ends; only damage or a stun cancels it) would have landed first; with an enemy within 4 during the window the recall may itself have drawn the attack, so those gems are also given apart. **altar**: within 40 rounds before dying it stood within 1 of an altar the enemy had not locked, carrying at least half the final bag, and a tribute started then (ceil(bag/10) turn ends; only a stun cancels it) would have completed before the death, with no stun on it in that span; split by whether an enemy was within 8 then (with one near, the tribute itself may have drawn the attack sooner). Look at: recall combat/fight.cc want_home / recall_line (recall on sight with a bag); economy/bank.cc continue_recall; altar economy/bank.cc banks_bag / retaining_gems / submit_here (bank at the altar passed).

| side | bag gems lost/game | recall window/game | gems | gems, no enemy within 4 in the window | altar, no enemy within 8/game | gems | altar, enemy within 8/game | gems |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| charybdis-5564637 | 146 | 0.44 | 18.7 | 3.4 | 0.00 | 0.0 | 0.03 | 1.3 |
| opponent | 192 | 0.82 | 45.1 | 22.0 | 0.01 | 0.3 | 0.08 | 3.3 |

Largest charybdis-5564637 recall-avoidable deaths:

- 762aee3cf5e9f49a r382 #3 Prism bag 621: killer in sight from r324, no damage from r324 (closest enemy 4), first hit r380; walking with gems, alone v2+, enemy half
- 292661a37171aca9 r632 #6 Prism bag 346: killer in sight from r612, no damage from r622 (closest enemy 4), first hit r632; fighting, grouped, even+, own half
- b65dda1be10799e5 r622 #4 Prism bag 327: killer in sight from r595, no damage from r595 (closest enemy 4), first hit r618; fighting, grouped, outnumbered, own half
- 5f7eb96213aa4522 r330 #0 Cassi bag 182: killer in sight from r317, no damage from r317 (closest enemy 3), first hit r330; walking with gems, grouped, even+, own half
- fa418017d2527940 r945 #7 Prism bag 124: killer in sight from r902, no damage from r920 (closest enemy 1), first hit r935; walking with gems, grouped, even+, own half
- b93ae9243fde1d27 r558 #0 Vesper Vale bag 115: killer in sight from r548, no damage from r549 (closest enemy 3), first hit r557; walking with gems, grouped, outnumbered, own half
- ea51c8b1b8d86b84 r921 #8 Prism bag 111: killer in sight from r911, no damage from r911 (closest enemy 3), first hit r918; walking with gems, grouped, even+, own half
- fcfc7f1fe137a071 r349 #9 Prism bag 108: killer in sight from r318, no damage from r320 (closest enemy 4), first hit r347; walking with gems, grouped, even+, own half

Largest charybdis-5564637 altar-avoidable deaths:

- 43c1e73ef209bfcd r321 #6 Prism bag 94: by an altar at r301 with 94 (tribute 10 rounds, 1 enemies within 8), died 20 rounds later, walking with gems
- b88146b596a02af8 r642 #3 Prism bag 69: by an altar at r626 with 69 (tribute 7 rounds, 2 enemies within 8), died 16 rounds later, fighting
- deaa187b77dcef7a r457 #6 Prism bag 65: by an altar at r419 with 65 (tribute 7 rounds, 3 enemies within 8), died 38 rounds later, walking with gems
- dd0f49653582dee1 r99 #2 Prism bag 29: by an altar at r84 with 29 (tribute 3 rounds, 3 enemies within 8), died 15 rounds later, fighting
- eb2a660ba3c0bb9f r245 #8 Prism bag 23: by an altar at r237 with 23 (tribute 3 rounds, 3 enemies within 8), died 8 rounds later, walking with gems
- 1d207177e703e6b5 r38 #3 Prism bag 15: by an altar at r26 with 15 (tribute 2 rounds, 3 enemies within 8), died 12 rounds later, walking with gems
- 012bacea9c1771a1 r181 #0 Prism bag 14: by an altar at r160 with 14 (tribute 2 rounds, 3 enemies within 8), died 21 rounds later, fighting

## Death hazard by activity

Champion-rounds spent on each activity (analysis/macro.py turn classes) and deaths to champions whose fatal damage began right after that activity, per 1000 such rounds, so a side is not penalised for doing more of something. Gems = bag gems lost in those deaths.

| activity | charybdis-5564637 rounds/game | charybdis-5564637 deaths per 1000 | charybdis-5564637 gems lost/game | opponent rounds/game | opponent deaths per 1000 | opponent gems lost/game |
| --- | --- | --- | --- | --- | --- | --- |
| walking | 1220 | 1.35 | 6.0 | 1205 | 1.87 | 4.6 |
| walking with gems | 1268 | 0.77 | 60.6 | 1287 | 1.36 | 110 |
| fighting | 134 | 5.56 | 28.6 | 131 | 8.46 | 31.4 |
| farming | 855 | 0.19 | 1.6 | 820 | 0.26 | 1.8 |
| waiting | 210 | 0.38 | 6.4 | 143 | 0.73 | 4.8 |
| tributing | 110 | 0.57 | 40.7 | 76.0 | 0.82 | 38.1 |
| recalling | 188 | 0.16 | 1.1 | 187 | 0.20 | 0.9 |
| stunned/oof | 8.3 | 2.02 | 0.1 | 7.1 | 5.26 | 0.9 |
| holding | 141 | 0.18 | 0.3 | 131 | 0.13 | 0.1 |
| idle | 58.2 | 0.43 | 0.2 | 58.7 | 0.07 | 0.0 |
| on spawn | 45.5 | 0.09 | 0.0 | 46.8 | 0.09 | 0.1 |

## Bag exposure

Champion-rounds alive carrying a bag of each size, and deaths with that bag per 1000 such rounds (a hazard rate, so a side that carries more is not penalised for carrying).

| champion | bag | charybdis-5564637 rounds/game | charybdis-5564637 deaths | charybdis-5564637 per 1000 | opponent rounds/game | opponent deaths | opponent per 1000 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Cassi | 1-49 | 251 | 88 | 1.46 | 279 | 125 | 1.87 |
| Cassi | 50-199 | 24.1 | 21 | 3.62 | 6.5 | 23 | 14.64 |
| Cassi | 200+ | 1.9 | 1 | 2.14 | 0.5 | 1 | 8.06 |
| Heart of Ruin | 1-49 | 123 | 25 | 0.84 | 139 | 43 | 1.29 |
| Heart of Ruin | 50-199 | 19.6 | 2 | 0.42 | 7.1 | 6 | 3.50 |
| Heart of Ruin | 200+ | 0.2 | 0 | 0.00 | 0.7 | 0 | 0.00 |
| Issac | 1-49 | 280 | 55 | 0.82 | 309 | 105 | 1.41 |
| Issac | 50-199 | 28.2 | 15 | 2.21 | 7.4 | 15 | 8.49 |
| Issac | 200+ | 0.0 | 1 | - | 0.0 | 0 | - |
| Marcella | 1-49 | 49.3 | 6 | 0.51 | 52.5 | 24 | 1.90 |
| Marcella | 50-199 | 10.9 | 4 | 1.53 | 5.7 | 2 | 1.45 |
| Marcella | 200+ | 1.5 | 0 | 0.00 | 1.8 | 1 | 2.29 |
| Prism | 1-49 | 84.7 | 23 | 1.13 | 133 | 57 | 1.79 |
| Prism | 50-199 | 169 | 32 | 0.79 | 182 | 55 | 1.26 |
| Prism | 200+ | 265 | 31 | 0.49 | 152 | 49 | 1.35 |
| Ren | 1-49 | 86.5 | 20 | 0.96 | 86 | 28 | 1.36 |
| Ren | 50-199 | 5.8 | 0 | 0.00 | 3.8 | 4 | 4.38 |
| Ren | 200+ | 0.0 | 0 | - | 0.4 | 1 | 10.42 |
| Ryth | 1-49 | 51.6 | 15 | 1.21 | 57.9 | 18 | 1.29 |
| Ryth | 50-199 | 11.8 | 3 | 1.06 | 5.8 | 2 | 1.44 |
| Ryth | 200+ | 0.1 | 0 | 0.00 | 1.7 | 0 | 0.00 |
| Tavi | 1-49 | 11.1 | 5 | 1.87 | 14.3 | 3 | 0.87 |
| Tavi | 50-199 | 5.4 | 0 | 0.00 | 1.4 | 1 | 3.07 |
| Tavi | 200+ | 0.4 | 1 | 11.76 | 0.0 | 0 | - |
| Varg | 1-49 | 46.4 | 8 | 0.72 | 51.7 | 8 | 0.64 |
| Varg | 50-199 | 10.2 | 0 | 0.00 | 2.5 | 0 | 0.00 |
| Varg | 200+ | 0.3 | 0 | 0.00 | 0.0 | 0 | - |
| Vendetta | 1-49 | 115 | 11 | 0.40 | 123 | 20 | 0.68 |
| Vendetta | 50-199 | 22.7 | 1 | 0.18 | 6.3 | 2 | 1.32 |
| Vendetta | 200+ | 0.1 | 0 | 0.00 | 0.0 | 0 | - |
| Vesper Vale | 1-49 | 253 | 25 | 0.41 | 282 | 68 | 1.00 |
| Vesper Vale | 50-199 | 113 | 20 | 0.74 | 37.5 | 17 | 1.89 |
| Vesper Vale | 200+ | 9.4 | 4 | 1.78 | 2.7 | 1 | 1.55 |
| Willow | 1-49 | 80.8 | 27 | 1.39 | 97.2 | 32 | 1.37 |
| Willow | 50-199 | 2.8 | 1 | 1.49 | 2.1 | 1 | 1.96 |

## Fights lost

Engagements (analysis/fights.py) the side lost on net swing (kill gems + gold/4 - bags lost); these overlap the death episodes. numbers = own minus enemy champions within 8 at the start; absent = own champions 9-16 away at the start that never joined.

| numbers | initiator | help in reach | charybdis-5564637 lost/game | charybdis-5564637 gems/game | opponent lost/game | opponent gems/game | excess | examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| +1 | they started | no ally 9-16 | 0.25 | 31.8 | 0.25 | 20.5 | 11.3 | a6e2109cda1e704c r625 (2137); b93ae9243fde1d27 r702 (570) |
| -1 | we started | absent ally 9-16 | 0.14 | 22.3 | 0.16 | 11.4 | 10.9 | be8613adeefa3594 r969 (2362); 8829b6190be197fe r655 (451) |
| +1 | we started | absent ally 9-16 | 0.08 | 11.3 | 0.05 | 3.4 | 7.9 | 6d7b23c09fce41d0 r1123 (1436); b65dda1be10799e5 r245 (234) |
| +1 | we started | no ally 9-16 | 0.11 | 14.0 | 0.10 | 7.7 | 6.3 | 76788d9b65fa4448 r492 (954); b65dda1be10799e5 r613 (700) |
| -1 | they started | absent ally 9-16 | 0.28 | 30.4 | 0.36 | 32.0 | -1.6 | 0187997b1f435613 r1735 (3112); fa418017d2527940 r491 (384) |
| +2+ | they started | absent ally 9-16 | 0.12 | 9.0 | 0.16 | 11.3 | -2.3 | 28f737927a50f26b r502 (576); 2823b6e0a36021e0 r435 (143) |
| +2+ | we started | absent ally 9-16 | 0.04 | 3.7 | 0.06 | 9.2 | -5.5 | 0187997b1f435613 r929 (380); 256a5cfcabea259b r702 (85.5) |
| -1 | we started | no ally 9-16 | 0.13 | 8.3 | 0.15 | 14.0 | -5.7 | d5bb13924247cf68 r228 (388); 0eb32fdc0663e917 r646 (233) |
| -2- | they started | absent ally 9-16 | 0.30 | 39.7 | 0.40 | 45.4 | -5.7 | d52aa01386fc2a6e r973 (1715); 383dccc831f852e0 r648 (1117) |
| +2+ | they started | no ally 9-16 | 0.17 | 25.9 | 0.26 | 34.3 | -8.4 | a6e2109cda1e704c r876 (2136); e461d84302229e72 r417 (1146) |
| -2- | we started | absent ally 9-16 | 0.15 | 11.5 | 0.23 | 21.5 | -10.0 | d1c79b48722a06c3 r751 (1017); e1a2ccd4068108bc r243 (123) |
| -2- | they started | no ally 9-16 | 0.15 | 16.4 | 0.35 | 26.6 | -10.1 | 1fe75c018cdec6b3 r1309 (1261); 9a770f6d72daba7d r830 (328) |
| -2- | we started | no ally 9-16 | 0.13 | 13.0 | 0.20 | 23.3 | -10.3 | 762aee3cf5e9f49a r378 (784); 08398e04d95c0a7b r494 (556) |
| +2+ | we started | no ally 9-16 | 0.07 | 4.8 | 0.11 | 20.6 | -15.8 | ea51c8b1b8d86b84 r917 (263); 010a536d79608736 r213 (217) |
| +0 | we started | no ally 9-16 | 0.12 | 10.9 | 0.20 | 27.0 | -16.1 | 292661a37171aca9 r631 (720); 23f5ec36ca607c26 r185 (260) |
| +0 | they started | absent ally 9-16 | 0.30 | 31.6 | 0.42 | 48.2 | -16.6 | d52aa01386fc2a6e r1167 (1898); b93ae9243fde1d27 r470 (1205) |
| +0 | they started | no ally 9-16 | 0.27 | 32.9 | 0.48 | 50.1 | -17.2 | a6e2109cda1e704c r1136 (2755); be8613adeefa3594 r571 (1151) |
| +0 | we started | absent ally 9-16 | 0.10 | 7.9 | 0.19 | 28.9 | -21.0 | 5517c3ebf7646f34 r222 (257); e1a2ccd4068108bc r123 (201) |
| +1 | they started | absent ally 9-16 | 0.17 | 22.8 | 0.28 | 47.7 | -24.9 | 054c002144d1fa1d r1072 (1827); e29264bf6ed3d55c r707 (918) |
| -1 | they started | no ally 9-16 | 0.20 | 27.6 | 0.41 | 52.8 | -25.2 | da301504f48cb738 r623 (1238); a223e3d82b1aa339 r581 (847) |

Absent allies 9-16 away in lost fights, by what they were doing: charybdis-5564637: walking 237, walking with gems 194, farming 141, waiting 25, holding 22, recalling 20; opponent: walking 294, walking with gems 269, farming 156, recalling 37, holding 30, idle 29.

## charybdis-5564637's losses against its wins

Cluster cost per game in the focus team's losses minus its wins (top 12): the situations that most separate a loss from a win. Partly reverse causality (a losing side is behind and fights at a disadvantage); the round column shows when they happen.

| situation | in losses | in wins | difference | median round |
| --- | --- | --- | --- | --- |
| Prism killed carrying 200+ gems while walking with gems, alone v2+, killer unseen | 24.2 | 0.0 | 24.2 | 1735 |
| Prism killed carrying 200+ gems while tributing, grouped, even+, killer seen <6 | 21.6 | 0.0 | 21.6 | 754 |
| invaded 4$ 1E group (own half): ours 21+ away | 21.1 | 1.1 | 20.0 | 711 |
| Prism killed carrying 200+ gems while fighting, grouped, even+, killer unseen | 15.6 | 0.0 | 15.6 | 1136 |
| Vesper Vale killed carrying 200+ gems while fighting, grouped, even+, killer seen <6 | 12.4 | 0.0 | 12.4 | 881 |
| invaded 17$ group (own half): ours 9-20 away | 11.3 | 0.0 | 11.3 | 264 |
| Prism killed carrying 50-199 gems while walking with gems, grouped, even+, killer seen 6+ | 11.4 | 0.6 | 10.9 | 349 |
| Tavi killed carrying 200+ gems while tributing, alone v1, killer unseen | 10.7 | 0.0 | 10.7 | 1175 |
| Cassi killed carrying 0 gems while walking, grouped, even+, killer seen 6+ | 10.6 | 0.4 | 10.2 | 757 |
| Prism killed carrying 200+ gems while tributing, grouped, outnumbered, killer unseen | 9.8 | 0.0 | 9.8 | 975 |
| Prism killed carrying 200+ gems while tributing, grouped, even+, killer unseen | 19.1 | 10.6 | 8.5 | 628 |
| Prism killed carrying 200+ gems while tributing, grouped, even+, killer seen 6+ | 8.4 | 0.0 | 8.4 | 1127 |
