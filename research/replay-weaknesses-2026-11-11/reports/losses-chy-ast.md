# Loss episodes: where value is lost, clustered and priced

Set: replays/batch-20261111-190139-ab-chy-vs-ast-40k-ladder (128 games, 64 clusters, focus charybdis); 128 games, charybdis won 94. Each side's losses are split into disjoint episodes priced in gems (deaths: bag + kill gold/4 + dead time at the game's earn rate; camp deaths; camps lost to the enemy; stalls of 10+ rounds), tagged with the situation and clustered. Costs are per game; "excess" is charybdis minus opponent in the same games, with a 95% cluster-bootstrap CI over map pairs or ladder groups. Examples are `analysis dir rROUND #champion (cost)`: open them with `py tools/replay/triage.py DIR --team NAME` (the game's turning points) or `py tools/replay/narrate.py` for a turn-level transcript.

Earn rate (gems per alive champion-round, both teams): mean 0.257, so a 60-round death costs about 15.4 gems of time.

## Cost by kind

| kind | charybdis cost/game | opponent cost/game | excess | charybdis in its wins | charybdis in its losses |
| --- | --- | --- | --- | --- | --- |
| death | 428 | 806 | -379 | 278 | 841 |
| camp_death | 15.4 | 7.1 | 8.4 | 15.2 | 15.9 |
| camp_lost | 403 | 654 | -250 | 256 | 811 |
| stall | 33.2 | 10.6 | 22.6 | 37.5 | 21.4 |

## Top weaknesses: clusters by excess cost

Every episode kind, clustered by champion and situation (deaths: bag and what the victim was doing the round before the fatal damage began). Sorted by charybdis's cost per game minus opponent's for the same cluster in the same games; clusters with fewer than 4 focus episodes or 3 games are left to the list of single expensive episodes below. "mix" gives each secondary tag's most common value among the focus episodes. cf columns: share of the cluster's focus bag gems that a recall in the safe window / a tribute at the last altar passed would have saved.

| situation | charybdis n/game | opponent n/game | charybdis cost/game | opponent cost/game | excess [95% CI] | mix | cf recall | cf altar | look at | examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Prism killed with 200+ gems while fighting | 0.04 | 0.03 | 39.1 | 21.8 | 17.3 [-15.8 .. 71.1] | grouped, even+ 60%, unseen 60%, own half 80%, held its ground 80%, heading - 60% | 5% | 0% | combat/plan.cc (strike search) and combat/fight.cc prey / chase_with_guard (who to engage) | 95c011537a8c16a6 r1274 #2 (1465); 95c011537a8c16a6 r1413 #2 (1461); 95c011537a8c16a6 r1112 #2 (1389) |
| camp contested (enemy half): ours within 3, outheld | 0.25 | 0.18 | 24.7 | 17.3 | 7.3 [-4.0 .. 22.3] | 3$ 12% | - | - | economy/capture.cc contest_capture / yield_capture; combat/plan.cc (fight on the tiles) | 1c58e209f5aabf3e r73 (343); 1c58e209f5aabf3e r279 (343); 4b90f13b008fa74c r730 (228) |
| Issac killed with 50-199 gems while fighting | 0.03 | 0.00 | 5.9 | 0.0 | 5.9 [0.0 .. 14.0] | alone v2+ 50%, seen <6 75%, own half 75%, held its ground 50%, heading elsewhere 75% | 33% | 0% | combat/plan.cc (strike search) and combat/fight.cc prey / chase_with_guard (who to engage) | 95c011537a8c16a6 r96 #1 (256); 1c58e209f5aabf3e r235 #5 (203); 8240ccf660bbeab8 r351 #8 (161) |
| Issac killed by a Wolf camp | 0.04 | 0.02 | 5.5 | 0.3 | 5.2 [-0.6 .. 16.2] | 200+ gems 40%, camp only 100% | 0% | 0% | economy/camps.cc (camp damage and clear time), combat/fight.cc camp_exit_way, economy/farm.cc rated_beaten | bbd31c8ccc3dba89 r443 #3 (318); 927e73b257e3f2d6 r412 #6 (263); bbd31c8ccc3dba89 r991 #3 (53.2) |
| camp stolen (enemy half): ours left, outnumbered | 0.38 | 0.33 | 12.3 | 7.6 | 4.7 [-1.2 .. 10.4] | 1G 18% | - | - | economy/capture.cc holding_capture / contest_capture; economy/crew.cc (who stays to hold) | 96bfa0c3f5a08ab0 r547 (111); 4f085c6602768d97 r800 (96.5); 47e5a71d53a2f76c r934 (93.2) |
| Stellar waiting 10+ rounds, by a tributing ally | 0.21 | 0.00 | 3.6 | 0.0 | 3.6 [0.0 .. 10.1] | r801+ 81%, then fight 59% | - | - | bot.cc decide (no branch acted), economy/farm.cc farm (no target chosen or waiting for a respawn) | 47e5a71d53a2f76c r491 #9 (45.7); c49d103a85cd6f63 r1452 #3 (36.7); 47e5a71d53a2f76c r886 #9 (35.4) |
| Willow waiting 10+ rounds, by a tributing ally | 0.16 | 0.05 | 5.4 | 1.9 | 3.5 [0.2 .. 9.0] | r801+ 62%, then walk 52% | - | - | bot.cc decide (no branch acted), economy/farm.cc farm (no target chosen or waiting for a respawn) | c49d103a85cd6f63 r1381 #5 (250); 47e5a71d53a2f76c r1106 #11 (73.7); c49d103a85cd6f63 r1090 #5 (69.8) |
| camp stolen (mid half): ours left, outnumbered | 0.25 | 0.27 | 15.0 | 11.8 | 3.2 [-7.5 .. 18.9] | 2G 1W 12% | - | - | economy/capture.cc holding_capture / contest_capture; economy/crew.cc (who stays to hold) | b928dfe5d6910bd2 r589 (295); b928dfe5d6910bd2 r807 (249); b928dfe5d6910bd2 r1196 (249) |
| Cassi waiting 10+ rounds, by a tributing ally | 0.17 | 0.04 | 3.5 | 0.9 | 2.6 [0.4 .. 5.8] | r801+ 59%, then walk_bag 36% | - | - | bot.cc decide (no branch acted), economy/farm.cc farm (no target chosen or waiting for a respawn) | c49d103a85cd6f63 r1450 #1 (104); 95c011537a8c16a6 r935 #0 (94.1); 47e5a71d53a2f76c r862 #7 (70.7) |
| Tavi killed with 0 gems while walking | 0.06 | 0.03 | 3.6 | 1.3 | 2.3 [0.0 .. 6.6] | grouped, even+ 62%, seen 6+ 75%, own half 75%, held its ground 38%, heading elsewhere 38% | - | - | model/safety.cc (threat model), combat/guard.cc guard_work / step_safely (step guard) | cf83bc03a332f810 r276 #4 (72.0); cf83bc03a332f810 r478 #4 (72.0); 7e711959ce70e970 r999 #5 (59.5) |
| Prism waiting 10+ rounds, farmable group in reach | 0.09 | 0.00 | 2.3 | 0.0 | 2.3 [0.0 .. 6.5] | r801+ 73%, then fight 55% | - | - | bot.cc decide (no branch acted), economy/farm.cc farm (no target chosen or waiting for a respawn) | 47e5a71d53a2f76c r1026 #10 (98.7); 47e5a71d53a2f76c r953 #10 (66.3); 47e5a71d53a2f76c r1106 #10 (28.0) |
| Willow killed by a Elk camp | 0.05 | 0.01 | 2.3 | 0.3 | 2.1 [-0.4 .. 5.8] | 0 gems 67%, camp only 83% | 0% | 0% | economy/camps.cc (camp damage and clear time), combat/fight.cc camp_exit_way, economy/farm.cc rated_beaten | c49d103a85cd6f63 r832 #5 (226); c6daa6c908e08d51 r158 #4 (15.6); c6daa6c908e08d51 r228 #4 (15.6) |
| Issac killed with 0 gems while fighting | 0.08 | 0.08 | 6.2 | 4.2 | 2.0 [-4.4 .. 7.3] | alone v2+ 60%, seen 6+ 50%, own half 50%, walked toward them 80%, heading toward an altar 40% | - | - | combat/plan.cc (strike search) and combat/fight.cc prey / chase_with_guard (who to engage) | 95c011537a8c16a6 r1692 #1 (203); dc82b550dd5f19ae r1516 #1 (105); e8585d3510dd4ca6 r1063 #2 (99.5) |
| Willow waiting 10+ rounds, farmable group in reach | 0.08 | 0.01 | 2.1 | 0.1 | 1.9 [0.0 .. 5.5] | r801+ 90%, then walk 90% | - | - | bot.cc decide (no branch acted), economy/farm.cc farm (no target chosen or waiting for a respawn) | 47e5a71d53a2f76c r1032 #11 (91.3); 47e5a71d53a2f76c r952 #11 (70.7); 47e5a71d53a2f76c r541 #11 (35.4) |
| Issac waiting 10+ rounds, by a tributing ally | 0.16 | 0.02 | 2.0 | 0.2 | 1.8 [0.1 .. 5.0] | r801+ 52%, then walk_bag 38% | - | - | bot.cc decide (no branch acted), economy/farm.cc farm (no target chosen or waiting for a respawn) | 47e5a71d53a2f76c r491 #8 (38.3); c49d103a85cd6f63 r1450 #2 (33.2); c49d103a85cd6f63 r1537 #2 (26.6) |
| Vesper Vale waiting 10+ rounds, farmable group in reach | 0.05 | 0.00 | 1.7 | 0.0 | 1.7 [0.0 .. 4.9] | r801+ 100%, then walk 57% | - | - | bot.cc decide (no branch acted), economy/farm.cc farm (no target chosen or waiting for a respawn) | 47e5a71d53a2f76c r1027 #6 (95.8); 47e5a71d53a2f76c r961 #6 (53.0); 47e5a71d53a2f76c r1109 #6 (17.7) |
| Willow waiting 10+ rounds, facing enemies within 9 | 0.20 | 0.02 | 1.5 | 0.1 | 1.4 [0.2 .. 3.2] | r801+ 81%, then walk 81% | - | - | bot.cc decide (no branch acted), economy/farm.cc farm (no target chosen or waiting for a respawn) | 4f085c6602768d97 r1060 #8 (32.0); cd8d6415acc329a0 r1574 #4 (20.6); 4f085c6602768d97 r1187 #8 (18.7) |
| camp contested (mid half): ours left at even numbers or better | 0.12 | 0.11 | 5.6 | 4.3 | 1.3 [-2.9 .. 6.1] | 4$ 27% | - | - | economy/capture.cc contest_capture / yield_capture; combat/plan.cc (fight on the tiles) | 74f8d19ee673b049 r571 (197); 6e42b32af00f513a r399 (98); 3ff29252e472e62a r245 (54.5) |
| Vesper Vale waiting 10+ rounds, by a tributing ally | 0.16 | 0.02 | 1.7 | 0.5 | 1.2 [0.0 .. 3.4] | r801+ 90%, then fight 62% | - | - | bot.cc decide (no branch acted), economy/farm.cc farm (no target chosen or waiting for a respawn) | 47e5a71d53a2f76c r871 #6 (54.5); 47e5a71d53a2f76c r1138 #6 (26.5); c49d103a85cd6f63 r1174 #0 (19.6) |
| Cassi killed with 50-199 gems while walking with gems | 0.05 | 0.03 | 6.2 | 5.1 | 1.1 [-7.2 .. 7.8] | alone v2+ 33%, seen 6+ 50%, own half 50%, held its ground 50%, heading elsewhere 100% | 29% | 0% | economy/bank.cc carry_bag / banks_bag (route and when to bank); combat/fight.cc want_home | 4f085c6602768d97 r676 #5 (155); 8240ccf660bbeab8 r625 #7 (139); 9522fa37cb176a13 r489 #6 (131) |
| Prism waiting 10+ rounds, facing enemies within 9 | 0.14 | 0.02 | 1.1 | 0.3 | 0.9 [-0.0 .. 2.5] | r801+ 56%, then walk_bag 39% | - | - | bot.cc decide (no branch acted), economy/farm.cc farm (no target chosen or waiting for a respawn) | 642403ca0958b294 r999 #2 (23.5); 642403ca0958b294 r869 #2 (20.5); 4f085c6602768d97 r1187 #7 (16.4) |
| Heart of Ruin waiting 10+ rounds, facing enemies within 9 | 0.08 | 0.01 | 0.9 | 0.0 | 0.8 [-0.0 .. 2.6] | r801+ 90%, then fight 50% | - | - | bot.cc decide (no branch acted), economy/farm.cc farm (no target chosen or waiting for a respawn) | 642403ca0958b294 r769 #4 (40.4); 642403ca0958b294 r992 #4 (31.0); 4f085c6602768d97 r1126 #9 (15.1) |
| camp stolen (enemy half): ours within 3, outheld | 0.18 | 0.14 | 7.0 | 6.4 | 0.7  | 1G 22% | - | - | economy/capture.cc holding_capture / contest_capture; economy/crew.cc (who stays to hold) | eadcdb9ea6ef0e34 r546 (224); c49d103a85cd6f63 r1473 (93.2); ab4d5f8d6fe40cf6 r358 (69.2) |
| Willow killed with 0 gems while farming | 0.03 | 0.02 | 1.7 | 1.0 | 0.7  | grouped, even+ 50%, unseen 75%, own half 100%, walked toward them 75%, heading toward an altar 50% | - | - | combat/fight.cc want_home (leave a camp under threat); economy/farm.cc farm (target risk) | 4b641393b4c1f13a r624 #3 (99.4); b6263141b16cd04f r533 #7 (45.5); 3c01857a346f19df r675 #4 (38.2) |
| Cassi killed with 1-49 gems while walking with gems | 0.17 | 0.18 | 14.5 | 13.9 | 0.6  | grouped, even+ 55%, seen 6+ 41%, own half 55%, held its ground 45%, heading elsewhere 64% | 19% | 0% | economy/bank.cc carry_bag / banks_bag (route and when to bank); combat/fight.cc want_home | cf83bc03a332f810 r94 #0 (123); 8240ccf660bbeab8 r960 #7 (114); e8585d3510dd4ca6 r342 #1 (104) |

The same without the champion (kind and situation only):

| situation | charybdis n/game | opponent n/game | charybdis cost/game | opponent cost/game | excess [95% CI] | mix | examples |
| --- | --- | --- | --- | --- | --- | --- | --- |
| any champion waiting 10+ rounds, by a tributing ally | 1.07 | 0.23 | 17.6 | 5.2 | 12.3 [1.8 .. 30.6] | r801+ 69%, then fight 29% | c49d103a85cd6f63 r1381 #5 (250); c49d103a85cd6f63 r1450 #1 (104) |
| camp contested (enemy half): ours within 3, outheld | 0.25 | 0.18 | 24.7 | 17.3 | 7.3 [-4.0 .. 22.3] | 3$ 12% | 1c58e209f5aabf3e r73 (343); 1c58e209f5aabf3e r279 (343) |
| any champion killed by a Wolf camp | 0.09 | 0.06 | 7.5 | 1.2 | 6.2 [-0.3 .. 18.5] | 1-49 gems 58%, camp only 75% | bbd31c8ccc3dba89 r443 #3 (318); 927e73b257e3f2d6 r412 #6 (263) |
| camp stolen (enemy half): ours left, outnumbered | 0.38 | 0.33 | 12.3 | 7.6 | 4.7 [-1.2 .. 10.4] | 1G 18% | 96bfa0c3f5a08ab0 r547 (111); 4f085c6602768d97 r800 (96.5) |
| any champion waiting 10+ rounds, facing enemies within 9 | 0.70 | 0.14 | 5.1 | 0.8 | 4.3 [0.9 .. 10.5] | r801+ 66%, then walk 46% | 642403ca0958b294 r769 #4 (40.4); 4f085c6602768d97 r1060 #8 (32.0) |
| any champion waiting 10+ rounds, farmable group in reach | 0.30 | 0.07 | 6.4 | 3.2 | 3.2 [-5.1 .. 15.1] | r801+ 85%, then walk 54% | 47e5a71d53a2f76c r1026 #10 (98.7); 47e5a71d53a2f76c r1027 #6 (95.8) |
| camp stolen (mid half): ours left, outnumbered | 0.25 | 0.27 | 15.0 | 11.8 | 3.2 [-7.5 .. 18.9] | 2G 1W 12% | b928dfe5d6910bd2 r589 (295); b928dfe5d6910bd2 r807 (249) |
| any champion killed with 200+ gems while fighting | 0.05 | 0.05 | 43.5 | 41.1 | 2.4 [-24.8 .. 35.9] | grouped, even+ 67%, unseen 50%, own half 67%, held its ground 67%, heading - 50% | 95c011537a8c16a6 r1274 #2 (1465); 95c011537a8c16a6 r1413 #2 (1461) |
| any champion waiting 10+ rounds, nothing in reach | 0.34 | 0.03 | 1.5 | 0.1 | 1.3 [0.0 .. 3.6] | r801+ 82%, then walk 68% | 8c80be48a3a8806f r1096 #10 (16.1); 8c80be48a3a8806f r1096 #11 (16.1) |
| camp contested (mid half): ours left at even numbers or better | 0.12 | 0.11 | 5.6 | 4.3 | 1.3 [-2.9 .. 6.1] | 4$ 27% | 74f8d19ee673b049 r571 (197); 6e42b32af00f513a r399 (98) |
| any champion killed by a Elk camp | 0.19 | 0.19 | 6.0 | 4.8 | 1.2 [-2.6 .. 5.7] | 0 gems 58%, camp only 58% | c49d103a85cd6f63 r832 #5 (226); 8240ccf660bbeab8 r750 #8 (88.1) |
| camp stolen (enemy half): ours within 3, outheld | 0.18 | 0.14 | 7.0 | 6.4 | 0.7 [-5.8 .. 7.5] | 1G 22% | eadcdb9ea6ef0e34 r546 (224); c49d103a85cd6f63 r1473 (93.2) |
| any champion idle 10+ rounds, nothing in reach | 0.09 | 0.02 | 0.7 | 0.1 | 0.6 [0.0 .. 1.7] | r401-800 64%, then walk_bag 55% | 8c80be48a3a8806f r1332 #8 (59.3); 7a539aff33783c84 r601 #5 (5.1) |
| any champion killed by a Golem camp | 0.03 | 0.00 | 0.5 | 0.0 | 0.5 [0.0 .. 1.0] | 0 gems 100%, camp only 75% | 3a1223679369f1ec r91 #0 (27.0); beb80b3006184733 r166 #10 (16.4) |
| any champion idle 10+ rounds, by a tributing ally | 0.12 | 0.01 | 0.5 | 0.0 | 0.4 [0.0 .. 0.9] | r801+ 81%, then end 56% | dc82b550dd5f19ae r1493 #1 (10.2); dc82b550dd5f19ae r1147 #1 (9.6) |

charybdis's single most expensive episodes (rare situations the clusters above leave out):

| game / round | episode | cost | tags |
| --- | --- | --- | --- |
| 47e5a71d53a2f76c r737 #10 | Prism killed carrying 200+ gems while walking with gems, alone v2+, killer seen <6 | 2204 | first hit r734, warned 5 rounds, walked toward them, heading toward an altar, allies 8/16: 0/0, enemies 8: 5, altar 4 away |
| 47e5a71d53a2f76c r565 #9 | Stellar killed carrying 200+ gems while walking with gems, grouped, even+, killer seen <6 | 1946 | first hit r564, warned 2 rounds, walked toward them, heading elsewhere, allies 8/16: 4/1, enemies 8: 1, altar 2 away |
| 95c011537a8c16a6 r1517 #0 | Cassi killed carrying 200+ gems while walking with gems, alone v1, killer unseen | 1573 | first hit r1517, warned -1 rounds, walked away, heading toward own spawn, allies 8/16: 0/0, enemies 8: 1, altar 3 away |
| 95c011537a8c16a6 r1181 #0 | Cassi killed carrying 200+ gems while tributing, grouped, even+, killer seen <6 | 1505 | first hit r1170, warned 1 rounds, held its ground, heading -, allies 8/16: 1/0, enemies 8: 1, altar 3 away |
| 95c011537a8c16a6 r1274 #2 | Prism killed carrying 200+ gems while fighting, grouped, even+, killer unseen | 1465 | first hit r1234, warned -1 rounds, held its ground, heading -, allies 8/16: 1/0, enemies 8: 1, altar 2 away |
| 95c011537a8c16a6 r1413 #2 | Prism killed carrying 200+ gems while fighting, grouped, even+, killer unseen | 1461 | first hit r1389, warned -1 rounds, held its ground, heading -, allies 8/16: 1/2, enemies 8: 1, altar 1 away |
| 95c011537a8c16a6 r1112 #2 | Prism killed carrying 200+ gems while fighting, grouped, even+, killer unseen | 1389 | first hit r1072, warned -1 rounds, held its ground, heading -, allies 8/16: 2/0, enemies 8: 1, altar 2 away |
| e8585d3510dd4ca6 r927 #3 | Prism killed carrying 200+ gems while walking with gems, grouped, even+, killer seen 6+ | 858 | first hit r921, warned 41 rounds, walked away, heading toward own spawn, allies 8/16: 1/0, enemies 8: 2, altar 7 away; recall from r898 would have landed (closest enemy 5) |
| 47e5a71d53a2f76c r473 #6 | Vesper Vale killed carrying 200+ gems while walking with gems, grouped, outnumbered, killer seen 6+ | 854 | first hit r473, warned 19 rounds, held its ground, heading elsewhere, allies 8/16: 2/3, enemies 8: 4, altar 2 away |
| 47e5a71d53a2f76c r479 | contested 2M group (mid half): ours died | 614 | MM(24,20)m, our damage share 9%, 2 of ours v 4 within 8 at their hold |
| c49d103a85cd6f63 r479 #0 | Vesper Vale killed carrying 200+ gems while tributing, grouped, even+, killer seen 6+ | 603 | first hit r478, warned 18 rounds, held its ground, heading -, allies 8/16: 5/0, enemies 8: 3, altar 2 away |
| 12de28e3c5aa7800 r462 #1 | Cassi killed carrying 200+ gems while fighting, grouped, even+, killer seen <6 | 566 | first hit r452, warned 4 rounds, walked away, heading toward own spawn, allies 8/16: 1/0, enemies 8: 2, altar 8 away |
| c49d103a85cd6f63 r1367 #0 | Vesper Vale killed carrying 200+ gems while tributing, grouped, even+, killer seen <6 | 559 | first hit r1363, warned 4 rounds, held its ground, heading -, allies 8/16: 5/0, enemies 8: 2, altar 1 away; tribute at r1337 (279 gems, 28 rounds) would have completed |
| cf83bc03a332f810 r256 | contested 49G group (own half): ours died | 428 | GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG(15,14)o, our damage share 31%, 3 of ours v 3 within 8 at their hold |
| cf83bc03a332f810 r722 | stolen 49G group (own half): ours died | 428 | GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG(15,14)o, our damage share 69%, 2 of ours v 2 within 8 at their hold |

## Deaths by situation

Death episodes only (killed by champions), one tag at a time. cost = bag + kill gold/4 + dead time.

**champion**

| champion | charybdis deaths/game | opponent deaths/game | charybdis cost/game | opponent cost/game | excess [95% CI] | examples |
| --- | --- | --- | --- | --- | --- | --- |
| Stellar | 0.08 | 0.10 | 21.6 | 6.5 | 15.2 [-16.1 .. 59.1] | 47e5a71d53a2f76c r565 #9 (1946); 47e5a71d53a2f76c r642 #9 (124) |
| Tavi | 0.12 | 0.05 | 9.4 | 1.9 | 7.5 [0.6 .. 19.5] | cf83bc03a332f810 r371 #4 (268); 508e5af5aebbfdfa r538 #5 (106) |
| Vendetta | 0.21 | 0.44 | 12.3 | 25.9 | -13.5 [-33.8 .. 7.4] | d917dc4655fe3dc8 r231 #7 (157); 8240ccf660bbeab8 r514 #6 (115) |
| Varg | 0.09 | 0.22 | 5.6 | 21.3 | -15.7 [-51.7 .. 6.8] | 4a9300967bf36c85 r392 #9 (77.9); eeb49c48aeb6af13 r376 #4 (73.8) |
| Ryth | 0.20 | 0.52 | 11.1 | 27.2 | -16.1 [-30.3 .. -0.9] | b52e4d5eab425915 r254 #6 (124); 74f8d19ee673b049 r464 #0 (113) |
| Ren | 0.20 | 0.48 | 10.5 | 27.1 | -16.5 [-32.1 .. -2.0] | 0e66036be1191398 r485 #11 (88.0); 17570bf58af33674 r452 #11 (82.1) |
| Willow | 0.44 | 0.77 | 23.2 | 47.8 | -24.6 [-55.2 .. -0.3] | 47e5a71d53a2f76c r717 #11 (139); 47e5a71d53a2f76c r796 #11 (124) |
| Heart of Ruin | 0.33 | 0.90 | 18.7 | 49.2 | -30.5 [-57.9 .. -6.3] | 4f085c6602768d97 r900 #9 (327); c2bacc1ee79e7099 r939 #11 (94.5) |
| Cassi | 0.86 | 1.59 | 101 | 132 | -31.1 [-63.4 .. 4.8] | 95c011537a8c16a6 r1517 #0 (1573); 95c011537a8c16a6 r1181 #0 (1505) |
| Vesper Vale | 0.45 | 0.73 | 41.2 | 80.9 | -39.7 [-106 .. 4.7] | 47e5a71d53a2f76c r473 #6 (854); c49d103a85cd6f63 r479 #0 (603) |
| Issac | 0.70 | 1.36 | 57.5 | 119 | -61.4 [-103 .. -24.2] | 95c011537a8c16a6 r96 #1 (256); 97023efa58a88f5e r680 #7 (248) |
| Marcella | 0.16 | 1.02 | 9.4 | 75.3 | -65.9 [-109 .. -34.9] | 4fa3a6858118873f r198 #4 (160); c8567621f9bd388a r410 #3 (83.7) |
| Prism | 0.49 | 1.41 | 106 | 192 | -86.4 [-152 .. -16.4] | 47e5a71d53a2f76c r737 #10 (2204); 95c011537a8c16a6 r1274 #2 (1465) |

**bag**

| bag | charybdis deaths/game | opponent deaths/game | charybdis cost/game | opponent cost/game | excess [95% CI] | examples |
| --- | --- | --- | --- | --- | --- | --- |
| 50-199 | 0.33 | 0.55 | 47.0 | 82.3 | -35.3 [-65.1 .. -8.3] | cf83bc03a332f810 r371 #4 (268); 95c011537a8c16a6 r96 #1 (256) |
| 200+ | 0.16 | 0.25 | 136 | 190 | -54.1 [-108 .. -2.5] | 47e5a71d53a2f76c r737 #10 (2204); 47e5a71d53a2f76c r565 #9 (1946) |
| 1-49 | 1.41 | 2.45 | 110 | 187 | -76.5 [-126 .. -30.5] | 47e5a71d53a2f76c r927 #7 (234); 95c011537a8c16a6 r488 #0 (231) |
| 0 | 2.44 | 6.32 | 134 | 347 | -213 [-307 .. -132] | 47e5a71d53a2f76c r765 #7 (213); 47e5a71d53a2f76c r1095 #8 (213) |

**doing before the first hit**

| doing before the first hit | charybdis deaths/game | opponent deaths/game | charybdis cost/game | opponent cost/game | excess [95% CI] | examples |
| --- | --- | --- | --- | --- | --- | --- |
| ? | 0.00 | 0.01 | 0.0 | 0.3 | -0.3 [-0.9 .. 0.0] |  |
| respawning | 0.00 | 0.02 | 0.0 | 0.8 | -0.8 [-2.1 .. 0.0] |  |
| idle | 0.01 | 0.05 | 0.6 | 2.2 | -1.6 [-3.1 .. -0.1] | 3ff29252e472e62a r831 #3 (73.9) |
| stunned/oof | 0.02 | 0.05 | 1.0 | 3.5 | -2.5 [-6.1 .. 0.3] | 7e711959ce70e970 r716 #5 (59.2); 21b5bc3001e44d09 r167 #7 (40.1) |
| holding | 0.05 | 0.10 | 4.2 | 9.4 | -5.2 [-12.5 .. -0.0] | 09122bfd84a200ea r211 #2 (137); c8b7aa64806268bc r229 #3 (89.7) |
| recalling | 0.12 | 0.14 | 10.8 | 22.6 | -11.9 [-40.2 .. 5.9] | 4f085c6602768d97 r900 #9 (327); b52e4d5eab425915 r254 #6 (124) |
| farming | 0.27 | 0.59 | 20.1 | 36.2 | -16.1 [-30.0 .. -4.0] | 47e5a71d53a2f76c r683 #8 (221); 47e5a71d53a2f76c r1095 #8 (213) |
| waiting | 0.12 | 0.17 | 8.5 | 28.1 | -19.6 [-48.0 .. -2.6] | 95c011537a8c16a6 r488 #0 (231); 95c011537a8c16a6 r1746 #3 (93.8) |
| tributing | 0.05 | 0.09 | 22.2 | 46.6 | -24.4 [-77.5 .. 19.7] | 95c011537a8c16a6 r1181 #0 (1505); c49d103a85cd6f63 r479 #0 (603) |
| fighting | 0.95 | 1.88 | 112 | 167 | -54.4 [-103 .. 11.2] | 95c011537a8c16a6 r1274 #2 (1465); 95c011537a8c16a6 r1413 #2 (1461) |
| walking with gems | 0.98 | 1.77 | 147 | 222 | -75.0 [-135 .. -24.5] | 47e5a71d53a2f76c r737 #10 (2204); 47e5a71d53a2f76c r565 #9 (1946) |
| walking | 1.76 | 4.71 | 101 | 268 | -167 [-243 .. -104] | 6b5e2c26cc0976dc r1117 #5 (252); 95c011537a8c16a6 r724 #0 (215) |

**numbers at the first hit**

| numbers at the first hit | charybdis deaths/game | opponent deaths/game | charybdis cost/game | opponent cost/game | excess [95% CI] | examples |
| --- | --- | --- | --- | --- | --- | --- |
| alone v2+ | 0.89 | 1.71 | 91.1 | 138 | -47.3 [-88.2 .. -8.8] | 47e5a71d53a2f76c r737 #10 (2204); c49d103a85cd6f63 r594 #4 (401) |
| alone v1 | 0.41 | 0.78 | 45.3 | 98.9 | -53.6 [-113 .. -7.7] | 95c011537a8c16a6 r1517 #0 (1573); d9c5a24c8a086b43 r754 #4 (418) |
| grouped, even+ | 2.11 | 4.38 | 225 | 363 | -138 [-287 .. 9.6] | 47e5a71d53a2f76c r565 #9 (1946); 95c011537a8c16a6 r1181 #0 (1505) |
| grouped, outnumbered | 0.92 | 2.70 | 66.3 | 206 | -140 [-196 .. -90.7] | 47e5a71d53a2f76c r473 #6 (854); 12de28e3c5aa7800 r433 #3 (284) |

**warning**

| warning | charybdis deaths/game | opponent deaths/game | charybdis cost/game | opponent cost/game | excess [95% CI] | examples |
| --- | --- | --- | --- | --- | --- | --- |
| unseen | 0.83 | 1.97 | 102 | 188 | -85.5 [-127 .. -37.4] | 95c011537a8c16a6 r1517 #0 (1573); 95c011537a8c16a6 r1274 #2 (1465) |
| seen <6 | 1.23 | 2.64 | 155 | 248 | -92.6 [-160 .. -26.4] | 47e5a71d53a2f76c r737 #10 (2204); 47e5a71d53a2f76c r565 #9 (1946) |
| seen 6+ | 2.28 | 4.96 | 170 | 371 | -201 [-326 .. -104] | e8585d3510dd4ca6 r927 #3 (858); 47e5a71d53a2f76c r473 #6 (854) |

**half**

| half | charybdis deaths/game | opponent deaths/game | charybdis cost/game | opponent cost/game | excess [95% CI] | examples |
| --- | --- | --- | --- | --- | --- | --- |
| mid | 0.70 | 1.42 | 71.6 | 134 | -62.2 [-137 .. -8.5] | 95c011537a8c16a6 r1517 #0 (1573); 47e5a71d53a2f76c r473 #6 (854) |
| enemy | 1.05 | 1.62 | 98.6 | 188 | -89.9 [-182 .. -26.5] | 47e5a71d53a2f76c r565 #9 (1946); c49d103a85cd6f63 r479 #0 (603) |
| own | 2.59 | 6.53 | 257 | 484 | -227 [-338 .. -107] | 47e5a71d53a2f76c r737 #10 (2204); 95c011537a8c16a6 r1181 #0 (1505) |

## Avoidable bag losses

Deaths with gems where the replay shows a rule-checked alternative, had the enemy acted the same. **recall window**: a killer was in the victim's sight with no damage or stun to it for 6+ rounds before the first hit, so a recall started at the window's start (5 turn ends; only damage or a stun cancels it) would have landed first; with an enemy within 4 during the window the recall may itself have drawn the attack, so those gems are also given apart. **altar**: within 40 rounds before dying it stood within 1 of an altar the enemy had not locked, carrying at least half the final bag, and a tribute started then (ceil(bag/10) turn ends; only a stun cancels it) would have completed before the death, with no stun on it in that span; split by whether an enemy was within 8 then (with one near, the tribute itself may have drawn the attack sooner). Look at: recall combat/fight.cc want_home / recall_line (recall on sight with a bag); economy/bank.cc continue_recall; altar economy/bank.cc banks_bag / retaining_gems / submit_here (bank at the altar passed).

| side | bag gems lost/game | recall window/game | gems | gems, no enemy within 4 in the window | altar, no enemy within 8/game | gems | altar, enemy within 8/game | gems |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| charybdis | 179 | 0.46 | 22.7 | 8.1 | 0.00 | 0.0 | 0.05 | 3.8 |
| opponent | 265 | 0.89 | 65.9 | 8.6 | 0.01 | 0.1 | 0.09 | 4.4 |

Largest charybdis recall-avoidable deaths:

- e8585d3510dd4ca6 r927 #3 Prism bag 781: killer in sight from r880, no damage from r898 (closest enemy 5), first hit r921; walking with gems, grouped, even+, own half
- d9c5a24c8a086b43 r754 #4 Prism bag 382: killer in sight from r742, no damage from r742 (closest enemy 3), first hit r751; walking with gems, alone v1, enemy half
- 12de28e3c5aa7800 r433 #3 Prism bag 232: killer in sight from r417, no damage from r418 (closest enemy 4), first hit r429; fighting, grouped, outnumbered, mid half
- b52e4d5eab425915 r261 #9 Prism bag 177: killer in sight from r250, no damage from r253 (closest enemy 4), first hit r261; walking with gems, grouped, even+, own half
- 1c58e209f5aabf3e r235 #5 Issac bag 118: killer in sight from r224, no damage from r224 (closest enemy 3), first hit r230; fighting, alone v2+, own half
- ae3e2120a71e22d4 r279 #6 Prism bag 98: killer in sight from r267, no damage from r267 (closest enemy 5), first hit r276; walking with gems, grouped, outnumbered, enemy half
- ae3e2120a71e22d4 r656 #6 Prism bag 77: killer in sight from r631, no damage from r631 (closest enemy 4), first hit r656; walking with gems, alone v2+, enemy half
- eeb49c48aeb6af13 r765 #0 Cassi bag 73: killer in sight from r746, no damage from r757 (closest enemy 4), first hit r763; walking with gems, grouped, outnumbered, enemy half

Largest charybdis altar-avoidable deaths:

- c49d103a85cd6f63 r1367 #0 Vesper Vale bag 479: by an altar at r1337 with 279 (tribute 28 rounds, 3 enemies within 8), died 30 rounds later, tributing
- 75e1ac2b73d2a70b r608 #0 Vendetta bag 69: by an altar at r600 with 69 (tribute 7 rounds, 2 enemies within 8), died 8 rounds later, walking with gems
- 9522fa37cb176a13 r306 #8 Prism bag 65: by an altar at r287 with 57 (tribute 6 rounds, 1 enemies within 8), died 19 rounds later, fighting
- c8567621f9bd388a r410 #3 Marcella bag 49: by an altar at r396 with 49 (tribute 5 rounds, 2 enemies within 8), died 14 rounds later, walking with gems
- 4b90f13b008fa74c r746 #5 Varg bag 22: by an altar at r728 with 22 (tribute 3 rounds, 2 enemies within 8), died 18 rounds later, tributing
- f6f780c045b4c567 r792 #7 Vendetta bag 4: by an altar at r779 with 4 (tribute 1 rounds, 2 enemies within 8), died 13 rounds later, fighting

## Death hazard by activity

Champion-rounds spent on each activity (analysis/macro.py turn classes) and deaths to champions whose fatal damage began right after that activity, per 1000 such rounds, so a side is not penalised for doing more of something. Gems = bag gems lost in those deaths.

| activity | charybdis rounds/game | charybdis deaths per 1000 | charybdis gems lost/game | opponent rounds/game | opponent deaths per 1000 | opponent gems lost/game |
| --- | --- | --- | --- | --- | --- | --- |
| walking | 1489 | 1.18 | 3.9 | 1623 | 2.90 | 6.8 |
| fighting | 220 | 4.29 | 55.0 | 215 | 8.71 | 59.1 |
| walking with gems | 1122 | 0.88 | 91.7 | 935 | 1.89 | 123 |
| farming | 854 | 0.32 | 2.6 | 733 | 0.81 | 3.2 |
| waiting | 199 | 0.59 | 1.1 | 101 | 1.71 | 14.1 |
| recalling | 205 | 0.61 | 4.4 | 201 | 0.70 | 12.8 |
| holding | 198 | 0.28 | 1.3 | 183 | 0.55 | 4.2 |
| tributing | 93.2 | 0.50 | 18.5 | 52.7 | 1.63 | 41.5 |
| stunned/oof | 10.8 | 2.17 | 0.0 | 10.0 | 5.47 | 1.0 |
| idle | 79 | 0.10 | 0.1 | 46.6 | 1.01 | 0.2 |
| ? | 0.0 | - | 0.0 | 0.0 | - | 0.0 |

## Bag exposure

Champion-rounds alive carrying a bag of each size, and deaths with that bag per 1000 such rounds (a hazard rate, so a side that carries more is not penalised for carrying).

| champion | bag | charybdis rounds/game | charybdis deaths | charybdis per 1000 | opponent rounds/game | opponent deaths | opponent per 1000 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Cassi | 1-49 | 259 | 56 | 1.69 | 157 | 68 | 3.39 |
| Cassi | 50-199 | 13.7 | 9 | 5.15 | 3.0 | 4 | 10.31 |
| Cassi | 200+ | 1.8 | 4 | 16.95 | 0.7 | 3 | 32.61 |
| Heart of Ruin | 1-49 | 103 | 12 | 0.91 | 89.3 | 19 | 1.66 |
| Heart of Ruin | 50-199 | 19.5 | 0 | 0.00 | 9.2 | 4 | 3.39 |
| Heart of Ruin | 200+ | 2.2 | 1 | 3.57 | 3.0 | 1 | 2.57 |
| Issac | 1-49 | 272 | 38 | 1.09 | 138 | 57 | 3.22 |
| Issac | 50-199 | 11.6 | 6 | 4.05 | 5.2 | 7 | 10.42 |
| Issac | 200+ | 6.4 | 3 | 3.65 | 0.3 | 1 | 27.03 |
| Marcella | 1-49 | 43.3 | 5 | 0.90 | 112 | 33 | 2.31 |
| Marcella | 50-199 | 10.2 | 1 | 0.77 | 12.5 | 8 | 5.00 |
| Marcella | 200+ | 0.5 | 0 | 0.00 | 4.1 | 2 | 3.80 |
| Prism | 1-49 | 114 | 19 | 1.31 | 171 | 58 | 2.65 |
| Prism | 50-199 | 183 | 17 | 0.72 | 150 | 27 | 1.41 |
| Prism | 200+ | 238 | 10 | 0.33 | 88.9 | 19 | 1.67 |
| Ren | 1-49 | 58.3 | 10 | 1.34 | 40.2 | 20 | 3.89 |
| Ren | 50-199 | 3.2 | 1 | 2.43 | 3.2 | 2 | 4.84 |
| Ryth | 1-49 | 82.3 | 9 | 0.85 | 46.8 | 6 | 1.00 |
| Ryth | 50-199 | 10.1 | 2 | 1.55 | 7.9 | 2 | 1.99 |
| Ryth | 200+ | 1.4 | 0 | 0.00 | 1.3 | 0 | 0.00 |
| Stellar | 1-49 | 11.8 | 0 | 0.00 | 5.0 | 1 | 1.57 |
| Stellar | 50-199 | 6.4 | 0 | 0.00 | 0.2 | 1 | 32.26 |
| Stellar | 200+ | 1.0 | 1 | 8.20 | 0.0 | 0 | - |
| Tavi | 1-49 | 25.4 | 3 | 0.92 | 5.1 | 0 | 0.00 |
| Tavi | 50-199 | 1.8 | 2 | 8.93 | 1.0 | 0 | 0.00 |
| Tavi | 200+ | 1.4 | 0 | 0.00 | 0.0 | 0 | - |
| Varg | 1-49 | 38.2 | 6 | 1.23 | 33.7 | 3 | 0.70 |
| Varg | 50-199 | 2.8 | 0 | 0.00 | 5.7 | 1 | 1.36 |
| Varg | 200+ | 0.0 | 0 | - | 0.8 | 2 | 19.23 |
| Vendetta | 1-49 | 87.2 | 8 | 0.72 | 64.9 | 12 | 1.44 |
| Vendetta | 50-199 | 24.8 | 2 | 0.63 | 11.8 | 7 | 4.65 |
| Vendetta | 200+ | 1.6 | 0 | 0.00 | 0.0 | 0 | - |
| Vesper Vale | 1-49 | 206 | 24 | 0.91 | 169 | 28 | 1.30 |
| Vesper Vale | 50-199 | 46.8 | 2 | 0.33 | 25.9 | 4 | 1.21 |
| Vesper Vale | 200+ | 10.8 | 3 | 2.17 | 6.0 | 4 | 5.21 |
| Willow | 1-49 | 43.4 | 8 | 1.44 | 47.3 | 20 | 3.30 |
| Willow | 50-199 | 2.3 | 0 | 0.00 | 9.0 | 4 | 3.47 |
| Willow | 200+ | 3.2 | 1 | 2.46 | 1.1 | 0 | 0.00 |

## Fights lost

Engagements (analysis/fights.py) the side lost on net swing (kill gems + gold/4 - bags lost); these overlap the death episodes. numbers = own minus enemy champions within 8 at the start; absent = own champions 9-16 away at the start that never joined.

| numbers | initiator | help in reach | charybdis lost/game | charybdis gems/game | opponent lost/game | opponent gems/game | excess | examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| +1 | they started | no ally 9-16 | 0.18 | 69.9 | 0.44 | 65.8 | 4.2 | 95c011537a8c16a6 r1517 (2781); 95c011537a8c16a6 r1217 (2727) |
| +2+ | we started | absent ally 9-16 | 0.07 | 8.6 | 0.10 | 9.5 | -0.9 | cf83bc03a332f810 r370 (442); 74f8d19ee673b049 r452 (166) |
| +1 | we started | absent ally 9-16 | 0.10 | 11.8 | 0.13 | 13.2 | -1.4 | 4f085c6602768d97 r874 (494); b52e4d5eab425915 r256 (379) |
| -2- | we started | absent ally 9-16 | 0.14 | 15.2 | 0.33 | 20.0 | -4.9 | c49d103a85cd6f63 r592 (709); ae3e2120a71e22d4 r276 (221) |
| +0 | we started | absent ally 9-16 | 0.20 | 16.6 | 0.33 | 23.0 | -6.4 | b6263141b16cd04f r564 (304); eeb49c48aeb6af13 r1143 (208) |
| +2+ | they started | absent ally 9-16 | 0.13 | 7.1 | 0.23 | 14.0 | -6.9 | 4a9300967bf36c85 r481 (179); 4a9300967bf36c85 r644 (124) |
| -2- | we started | no ally 9-16 | 0.06 | 7.9 | 0.30 | 15.4 | -7.5 | cd8d6415acc329a0 r1735 (348); 47e5a71d53a2f76c r734 (290) |
| +0 | we started | no ally 9-16 | 0.23 | 18.6 | 0.36 | 27.4 | -8.9 | d9c5a24c8a086b43 r746 (789); b6263141b16cd04f r108 (165) |
| -1 | we started | absent ally 9-16 | 0.18 | 23.2 | 0.20 | 33.3 | -10.1 | 12de28e3c5aa7800 r451 (999); d917dc4655fe3dc8 r218 (320) |
| +2+ | they started | no ally 9-16 | 0.16 | 47.7 | 0.37 | 59.1 | -11.3 | 47e5a71d53a2f76c r564 (3673); c49d103a85cd6f63 r478 (1113) |
| +1 | we started | no ally 9-16 | 0.08 | 4.9 | 0.21 | 20.4 | -15.5 | 27820ea685b2446e r167 (141); 17570bf58af33674 r541 (101) |
| -1 | we started | no ally 9-16 | 0.13 | 5.5 | 0.34 | 21.3 | -15.8 | da8cc97e14d30b84 r279 (111); 4fa3a6858118873f r489 (85) |
| +0 | they started | absent ally 9-16 | 0.39 | 48.2 | 0.67 | 68.0 | -19.8 | 95c011537a8c16a6 r1389 (2735); 97023efa58a88f5e r679 (468) |
| -2- | they started | no ally 9-16 | 0.14 | 13.1 | 0.49 | 36.6 | -23.4 | c49d103a85cd6f63 r829 (241); eeb49c48aeb6af13 r762 (225) |
| +0 | they started | no ally 9-16 | 0.27 | 26.9 | 0.87 | 54.4 | -27.5 | e8585d3510dd4ca6 r921 (1616); 4b641393b4c1f13a r624 (197) |
| +2+ | we started | no ally 9-16 | 0.10 | 3.0 | 0.16 | 32.7 | -29.7 | 7e711959ce70e970 r1038 (53.5); a578f670aaacf4eb r673 (41.2) |
| +1 | they started | absent ally 9-16 | 0.29 | 35.2 | 0.47 | 70.3 | -35.1 | 95c011537a8c16a6 r1060 (2550); 6b5e2c26cc0976dc r1116 (425) |
| -2- | they started | absent ally 9-16 | 0.32 | 28.1 | 0.84 | 69.7 | -41.6 | 47e5a71d53a2f76c r468 (1134); 93d98c5273bbe201 r443 (521) |
| -1 | they started | no ally 9-16 | 0.19 | 12.7 | 0.48 | 60.2 | -47.5 | 75e1ac2b73d2a70b r606 (163); 508e5af5aebbfdfa r535 (141) |
| -1 | they started | absent ally 9-16 | 0.42 | 26.0 | 0.59 | 83.3 | -57.3 | d44e24a7c7a32da9 r264 (241); ea93af28b22f718f r275 (233) |

Absent allies 9-16 away in lost fights, by what they were doing: charybdis: walking 180, walking with gems 134, farming 74, holding 30, recalling 16, waiting 15; opponent: walking 301, walking with gems 198, farming 112, recalling 47, holding 39, waiting 13.

## charybdis's losses against its wins

Cluster cost per game in the focus team's losses minus its wins (top 12): the situations that most separate a loss from a win. Partly reverse causality (a losing side is behind and fights at a disadvantage); the round column shows when they happen.

| situation | in losses | in wins | difference | median round |
| --- | --- | --- | --- | --- |
| Prism killed carrying 200+ gems while fighting, grouped, even+, killer unseen | 127 | 0.0 | 127 | 1274 |
| contested 4$ 6E 10G group (mid half): ours left, outnumbered | 85.3 | 0.0 | 85.3 | 1060 |
| Cassi killed carrying 200+ gems while walking with gems, alone v1, killer unseen | 46.3 | 0.0 | 46.3 | 1517 |
| Cassi killed carrying 200+ gems while tributing, grouped, even+, killer seen <6 | 44.3 | 0.0 | 44.3 | 1181 |
| contested 2E 6G group (mid half): ours within 3, outheld | 36.8 | 1.6 | 35.2 | 781 |
| Prism killed carrying 200+ gems while walking with gems, grouped, even+, killer seen 6+ | 25.2 | 0.0 | 25.2 | 927 |
| invaded 1G group (own half): ours 9-20 away | 24.2 | 3.8 | 20.5 | 432 |
| contested 49G group (own half): ours within 3, outheld | 20.2 | 0.0 | 20.2 | 356 |
| contested 30$ group (enemy half): ours within 3, outheld | 18.6 | 0.0 | 18.6 | 77 |
| contested 23G group (enemy half): ours within 3, outheld | 17.7 | 0.0 | 17.7 | 489 |
| Cassi killed carrying 200+ gems while fighting, grouped, even+, killer seen <6 | 16.6 | 0.0 | 16.6 | 462 |
| invaded 5$ group (own half): ours within 8 | 16.2 | 0.0 | 16.2 | 500 |
