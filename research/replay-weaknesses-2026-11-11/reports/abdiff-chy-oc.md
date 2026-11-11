# Behaviour diff: charybdis (A) against ocean (B)

128 paired games (map and side). Opponents: A ['astraeus'], B ['astraeus'].

Win rate A 73.4%, B 72.7%; flips: 19 games A won and B lost, 18 A lost and B won, 91 the same.

Columns: mean A, mean B, mean A - B with a 95% bootstrap CI over maps; "flip assoc." = mean (A - B) in the games A won and B lost minus that in the games A lost and B won (large when the change goes with the flips). Sorted by |diff| / CI half-width.

## Behaviour metrics

| metric | A | B | A - B [95% CI] | flip assoc. | definition |
| --- | --- | --- | --- | --- | --- |
| carry_top | 70.1% | 57.6% | +12.5pt [+8.4pt .. +17.2pt] | +16.9pt | share of the team's carried gem-rounds on its top carrier |
| gem_latency | 126 | 82.4 | +44.0 [+23.1 .. +70.0] | +161 | mean rounds a tributed gem was carried (gem-weighted) |
| mt_walk_bag | 25.0% | 26.7% | -1.7pt [-2.8pt .. -0.5pt] | -0.1pt | alive turns walking while carrying gems |
| mt_wait | 3.8% | 2.9% | +0.9pt [+0.2pt .. +1.9pt] | -0.0pt | alive turns waiting still by a respawning or live camp, or by an altar, without hitting or holding |
| gem_exposed | 40.7% | 37.7% | +3.0pt [+0.4pt .. +6.0pt] | -6.5pt | carried gem-rounds in sight of an enemy / carried gem-rounds |
| loss_stall_per100 | 2.7 | 1.0 | +1.6 [+0.4 .. +3.6] | +0.3 | stall cost (still, off spawn, 10+ rounds) per 100 rounds |
| earned_per100 | 138 | 129 | +9.8 [+0.9 .. +20.3] | +92.0 | gems earned (capture shares + kill bags) per 100 rounds |
| control_own | 79.1% | 77.9% | +1.2pt [+0.0pt .. +2.6pt] | +12.8pt | own-half camp value under our control |
| regroup_share | 12.4% | 13.2% | -0.8pt [-1.7pt .. +0.0pt] | +1.3pt | alive turns on walks that end next to an ally who was 9+ away at the start (walking to allies) |
| loss_camp_death_per100 | 1.3 | 0.8 | +0.6 [+0.0 .. +1.2] | +0.1 | camp death cost per 100 rounds |
| own_lost | 13.4% | 16.0% | -2.5pt [-5.2pt .. +0.4pt] | -35.0pt | gems of own-half captures taken by the enemy / own-half captured gems |
| control | 53.3% | 52.1% | +1.2pt [-0.2pt .. +2.9pt] | +17.1pt | camp value nearer (walking) to our champions than theirs, gems + gold/4 per respawn, sampled |
| loss_bag_per100 | 16.6 | 12.3 | +4.3 [-1.4 .. +11.4] | -45.5 | carried gems lost on death per 100 rounds |
| mt_recall | 4.6% | 4.7% | -0.1pt [-0.3pt .. +0.1pt] | +0.8pt | alive turns channelling recalls |
| enemy_half | 13.0% | 12.3% | +0.7pt [-0.3pt .. +1.8pt] | +7.1pt | alive champion-rounds on the enemy half |
| walk_per_gem | 3.8 | 3.0 | +0.8 [-0.2 .. +2.8] | -5.1 | walk turns per gem earned (captures and kills) |
| mt_spawn | 1.4% | 1.2% | +0.2pt [-0.1pt .. +0.7pt] | -1.6pt | alive turns standing on own spawn |
| mt_walk | 57.2% | 57.8% | -0.6pt [-1.8pt .. +0.5pt] | -5.0pt | alive turns walking (with or without gems) |
| mt_idle | 1.5% | 1.3% | +0.2pt [-0.1pt .. +0.6pt] | -0.8pt | alive turns idle elsewhere off spawn |
| mt_fight | 5.1% | 5.3% | -0.2pt [-0.6pt .. +0.3pt] | -2.0pt | alive turns in fights (dealt or took champion damage) |
| walk_waste | 29.0% | 28.3% | +0.7pt [-0.9pt .. +2.3pt] | -11.3pt | walked steps beyond the straight (Chebyshev) line of each walk leg / steps |
| lonely_death | 32.6% | 29.7% | +2.8pt [-3.4pt .. +10.1pt] | +11.3pt | deaths to champions with no living ally within 8 |
| mt_work | 26.2% | 26.5% | -0.3pt [-1.2pt .. +0.5pt] | +8.6pt | alive turns at work: hitting camps, holding captures, tributing |
| loss_camp_lost_per100 | 43.4 | 46.3 | -2.9 [-10.5 .. +5.5] | -107 | camps lost to the enemy (stolen, contested, own half invaded) per 100 rounds |
| loss_death_per100 | 42.2 | 38.4 | +3.9 [-6.5 .. +15.7] | -102 | death episode cost (bag + gold/4 + dead time) per 100 rounds |
| nn_dist | 5.5 | 5.5 | -0.1 [-0.3 .. +0.1] | +0.4 | distance to the nearest living ally (alive, off spawn; mean) |
| outnumbering | 62.4% | 61.6% | +0.8pt [-2.1pt .. +3.7pt] | +1.8pt | contact champion-rounds with more allies than enemies within 8 |
| cf_recall_gems_per100 | 2.8 | 3.3 | -0.5 [-2.8 .. +1.7] | -10.7 | gems lost in deaths a recall in sight of the killer would have saved, per 100 rounds |
| outnumbered | 12.4% | 12.8% | -0.4pt [-1.9pt .. +1.6pt] | -3.6pt | contact champion-rounds (an enemy within 8) with more enemies than allies within 8 |
| loss_total_per100 | 89.6 | 86.5 | +3.1 [-11.8 .. +20.5] | -208 | gems lost to episodes (deaths, camp deaths, camps lost, stalls) per 100 rounds |
| isolated | 20.8% | 21.0% | -0.2pt [-1.4pt .. +1.0pt] | +1.0pt | alive champion-rounds off spawn with no ally within 8 |
| mt_dead | 7.7% | 7.9% | -0.1pt [-1.5pt .. +1.1pt] | -13.1pt | champion turns dead |
| contest_win | 59.6% | 59.8% | -0.2pt [-5.7pt .. +5.5pt] | +49.3pt | contested camp cycles (both teams hit, held or contested) we captured |
| fight_outnum | 29.8% | 29.9% | -0.1pt [-2.5pt .. +2.8pt] | -8.3pt | fights started with fewer own champions present |
| conversion | 82.6% | 82.5% | +0.2pt [-4.9pt .. +5.9pt] | +72.3pt | tributed / earned gems |
| fight_turnout | 52.9% | 52.9% | +0.0pt [-1.4pt .. +1.7pt] | -4.9pt | own alive champions within 8 of a fight at its start / own alive champions |
| cf_altar_gems_per100 | 0.0 | 0.0 | 0.0 [0.0 .. 0.0] | 0.0 | gems lost in deaths after passing an altar, no enemy within 8, where a tribute would have completed, per 100 rounds |

## Loss episode clusters (gems per game)

| cluster | A | B | A - B [95% CI] | flip assoc. |
| --- | --- | --- | --- | --- |
| camp contested (enemy half): ours within 3, outheld | 24.7 | 11.5 | +13.2 [+3.7 .. +25.8] | -17.4 |
| Ren killed with 0 gems while walking | 2.8 | 7.5 | -4.7 [-9.7 .. -0.8] | -7.3 |
| camp stolen (own half): ours left, outnumbered | 11.1 | 5.3 | +5.8 [+0.9 .. +12.1] | -35.1 |
| Willow waiting 10+ rounds, facing enemies within 9 | 1.5 | 0.0 | +1.5 [+0.2 .. +3.3] | -4.6 |
| camp contested (enemy half): ours left, outnumbered | 25.2 | 32.9 | -7.8 [-16.6 .. +0.6] | -28.9 |
| Marcella killed with 1-49 gems while fighting | 0.0 | 1.2 | -1.2 [-2.7 .. 0.0] | -5.0 |
| camp stolen (enemy half): ours died | 4.3 | 14.1 | -9.8 [-22.2 .. +0.5] | -45.9 |
| Issac killed with 1-49 gems while walking | 5.4 | 11.8 | -6.4 [-13.0 .. +1.8] | -5.3 |
| Prism waiting 10+ rounds, facing enemies within 9 | 1.1 | 0.0 | +1.1 [+0.1 .. +2.7] | -1.9 |
| Issac killed with 0 gems while fighting | 6.2 | 1.7 | +4.6 [-0.4 .. +10.5] | -14.8 |
| camp stolen (own half): ours left at even numbers or better | 4.5 | 7.9 | -3.4 [-8.0 .. +0.2] | -10.5 |
| Vesper Vale killed with 1-49 gems while walking | 0.0 | 1.3 | -1.3 [-3.1 .. 0.0] | 0.0 |
| Ren killed with 0 gems while farming | 1.3 | 2.4 | -1.1 [-2.7 .. +0.0] | 0.0 |
| Willow killed with 0 gems while walking | 12.7 | 8.2 | +4.6 [-0.4 .. +10.6] | -38.1 |
| Prism killed with 50-199 gems while walking with gems | 11.4 | 20.9 | -9.5 [-20.7 .. +2.5] | -57.5 |
| camp stolen (enemy half): ours within 3, outheld | 7.0 | 4.0 | +3.0 [-0.2 .. +7.2] | +3.1 |
| Cassi killed by a Elk camp | 1.2 | 0.5 | +0.7 [-0.1 .. +1.7] | 0.0 |
| Cassi waiting 10+ rounds, by a tributing ally | 3.5 | 0.4 | +3.2 [+0.2 .. +8.0] | -5.8 |
| Ryth killed with 0 gems while walking | 3.5 | 1.4 | +2.1 [-0.5 .. +4.7] | -11.6 |
| Vesper Vale killed by a Wolf camp | 1.0 | 0.3 | +0.7 [0.0 .. +1.7] | -1.7 |

## Games A lost and B won (regressions)

Open with `py tools/replay/triage.py DIR --team NAME` (A dir with the A team, B dir with the B team).

| map | side | A dir | B dir | episode cost A - B | largest cluster differences |
| --- | --- | --- | --- | --- | --- |
| the-pond | A | 95c011537a8c16a6 | 27dd6e797c690d18 | 9272 | Prism killed with 200+ gems while fighting +4314; Cassi killed with 200+ gems while walking with gems +1573; Cassi killed with 200+ gems while tributing +1505 |
| vault | A | cf83bc03a332f810 | b2abc4f48fbd45fb | 3867 | camp contested (own half): ours within 3, outheld +686; camp stolen (own half): ours died +428; camp contested (own half): ours died +428 |
| elk-arena | A | 7e711959ce70e970 | 8fac968680eb36c2 | 2688 | camp contested (mid half): ours within 3, outheld +1251; Tavi killed with 0 gems while walking +166; Cassi killed with 0 gems while walking +130 |
| stampede | A | cd8d6415acc329a0 | 2e38ef4da0a3ee32 | 1863 | camp contested (mid half): ours left, outnumbered +707; camp stolen (mid half): ours left at even numbers or better +422; camp contested (mid half): ours died +344 |
| stampede | B | 8c80be48a3a8806f | e46f69d9a5fd9ad2 | 1854 | camp contested (mid half): ours left, outnumbered +1740; Marcella killed with 50-199 gems while walking with gems -129; camp stolen (mid half): ours left at even numbers or better +80 |
| the-line | B | 97023efa58a88f5e | 38c0e7132e27b113 | 1463 | camp contested (enemy half): ours within 3, outheld +603; Issac killed with 200+ gems while walking with gems +248; camp contested (enemy half): ours died +201 |
| quadrants | B | b52e4d5eab425915 | c38ea4af746231f2 | 616 | Prism killed with 50-199 gems while walking with gems +229; Ryth killed with 50-199 gems while recalling +124; Cassi killed with 0 gems while walking +80 |
| the-farm | A | dc82b550dd5f19ae | 12668382df513185 | 461 | camp stolen (own half): ours left, outnumbered +290; camp contested (mid half): ours left, outnumbered -180; Cassi killed with 50-199 gems while fighting -162 |
| the-pack | B | 927e73b257e3f2d6 | 9b311cd08ed277e9 | 449 | Issac killed by a Wolf camp +263; Ryth killed by a Wolf camp -125; Cassi killed with 1-49 gems while fighting +76 |
| galaxy | A | c8567621f9bd388a | 463b1ac1d6054a80 | 427 | Heart of Ruin killed with 1-49 gems while walking with gems +139; Willow killed with 0 gems while walking +104; Marcella killed with 1-49 gems while walking with gems +103 |
| monolith | A | d9c5a24c8a086b43 | 5eeee5c183deaf46 | 425 | Prism killed with 200+ gems while walking with gems +418; camp contested (enemy half): ours left, outnumbered -14; camp invaded (own half): ours within 8 +12 |
| famine | A | 10d377257b9f2740 | b337e9e89a7b104f | 304 | camp invaded (own half): ours 21+ away +190; Issac killed with 1-49 gems while walking -63; Prism killed with 1-49 gems while fighting +62 |
| the-pond | B | b6263141b16cd04f | 3b2d7fcab8f6c74e | 229 | Prism killed with 50-199 gems while fighting +203; Issac killed with 1-49 gems while walking -171; Issac killed with 50-199 gems while walking with gems +152 |
| fields | A | 3b0cc50b04b3bca8 | 133344a447504fe1 | 197 | Issac killed with 1-49 gems while walking +77; camp invaded (own half): ours 9-20 away +66; camp stolen (own half): ours within 3, outheld +26 |
| big-world | A | b09becb63f3da71c | a66598f11cdbac33 | -189 | camp invaded (own half): ours 21+ away -342; camp invaded (own half): ours 9-20 away +232; Issac waiting 10+ rounds, facing enemies within 9 -68 |

## Games A won and B lost

Open with `py tools/replay/triage.py DIR --team NAME` (A dir with the A team, B dir with the B team).

| map | side | A dir | B dir | episode cost A - B | largest cluster differences |
| --- | --- | --- | --- | --- | --- |
| swirl | B | 368185ac2aad2820 | 0545f0930f79f5fd | -3068 | camp invaded (own half): ours 21+ away -973; camp invaded (own half): ours 9-20 away -816; Varg killed with 0 gems while walking -156 |
| hooks | A | c8b7aa64806268bc | fafc377d239c9943 | -2038 | camp invaded (own half): ours within 8 -552; camp contested (enemy half): ours left, outnumbered -205; Cassi killed with 0 gems while walking -190 |
| corners | B | 17570bf58af33674 | 39cb63fd9cff1b73 | -1645 | Cassi killed with 0 gems while walking -187; camp stolen (own half): ours within 3, outheld -171; Issac killed with 1-49 gems while walking with gems -155 |
| gem-fields | B | 0e66036be1191398 | 79d1a727a02a6953 | -1250 | camp invaded (own half): ours within 8 -377; Prism killed with 50-199 gems while walking with gems -205; Cassi killed with 1-49 gems while walking with gems -164 |
| stalactites | B | e7c6806035ce8dde | 7d47850da36491d8 | -947 | camp contested (mid half): ours left at even numbers or better -210; camp contested (mid half): ours died -189; Prism killed with 50-199 gems while fighting -134 |
| galaxy | B | 4fada874f441f8cd | 2cd511553194f8e5 | -745 | Prism killed with 200+ gems while fighting -268; Prism killed with 50-199 gems while fighting -170; camp invaded (own half): ours 9-20 away -68 |
| road-of-riches | B | d917dc4655fe3dc8 | 11b03c489d87bee7 | -701 | Cassi killed with 50-199 gems while walking with gems -189; Vendetta killed with 50-199 gems while walking with gems +157; camp invaded (own half): ours 9-20 away -136 |
| packs | A | 4b641393b4c1f13a | 2f4f0ebb863a5af7 | -692 | camp invaded (own half): ours within 8 -155; camp stolen (own half): ours left, outnumbered -132; Willow killed with 0 gems while farming +99 |
| breadcrumbs | A | a72a0852820298b5 | 4cef40e207e1c66d | -625 | Prism killed with 50-199 gems while holding -169; camp invaded (own half): ours 9-20 away -166; Cassi killed with 1-49 gems while walking -98 |
| rows | B | be8e59109917576b | 81d634b193d0b505 | -624 | camp contested (own half): ours left, outnumbered -702; camp invaded (own half): ours 21+ away +78; Vendetta killed with 1-49 gems while walking with gems +44 |
| rows | A | 90a2ddf8a5941439 | 2c71ae16710a9644 | -599 | camp stolen (enemy half): ours died -702; camp invaded (own half): ours 21+ away +126; camp stolen (enemy half): ours left at even numbers or better -25 |
| vault | B | 1c58e209f5aabf3e | 2808155bc4b9ba5d | -393 | camp contested (enemy half): ours died -367; camp contested (enemy half): ours within 3, outheld +258; Issac killed with 50-199 gems while fighting +203 |
| tangle | A | 744bb4f236ff7ac9 | d22f2f4e5bee9181 | -278 | camp invaded (own half): ours 21+ away -142; Prism killed with 50-199 gems while walking with gems -126; camp invaded (own half): ours 9-20 away +82 |
| gift-wrapping | A | 74f8d19ee673b049 | e78aafafa3c3d4c8 | 236 | camp contested (mid half): ours within 3, outheld -389; camp contested (enemy half): ours died +204; camp contested (mid half): ours left at even numbers or better +197 |
| gemfight | B | 6e42b32af00f513a | ab565e3de0abbff6 | -207 | Prism killed with 200+ gems while walking with gems +255; Prism killed with 50-199 gems while fighting -238; camp stolen (mid half): ours died -216 |
