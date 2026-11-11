# Macro: turns, gems, cohesion, control, losses

Set: replays/batch-20261111-183545-ab-chy-vs-ocean-d18-hold (240 games, 121 clusters, focus charybdis-5564637). Sides: charybdis-5564637 vs opponent in the same game (240 pairs). Paired by game: the focus team against its opponent.

Every number is read from the replay alone (no bot traces). Turn classes are per champion-round, first match wins: dead, lost (stunned/out of fuel/error), fight (dealt or took champion damage), tribute/recall/teleport channel, camp (hit a camp), walk_bag/walk (moved, carrying gems or not), hold (still on a claimable group tile), spawn (still on own spawn), idle. Distances are Chebyshev unless noted; camp control uses walking distance. Differences are mean charybdis-5564637 minus opponent with a 95% cluster-bootstrap CI over map pairs or ladder groups.

## Macro metrics, paired

| metric | charybdis-5564637 | opponent | charybdis-5564637 - opponent [95% CI] | charybdis-5564637 higher | games | definition |
| --- | --- | --- | --- | --- | --- | --- |
| mt_walk | 57.7% | 59.7% | -2.0pt [-3.1pt .. -0.9pt] | 39% | 240 | alive turns walking (with or without gems) |
| mt_walk_bag | 29.2% | 30.2% | -1.0pt [-2.0pt .. +0.0pt] | 44% | 240 | alive turns walking while carrying gems |
| mt_work | 27.8% | 26.7% | +1.2pt [+0.4pt .. +1.9pt] | 60% | 240 | alive turns at work: hitting camps, holding captures, tributing |
| mt_fight | 3.0% | 3.1% | -0.1pt [-0.2pt .. +0.0pt] | 36% | 240 | alive turns in fights (dealt or took champion damage) |
| mt_wait | 4.3% | 3.1% | +1.1pt [+0.4pt .. +2.0pt] | 57% | 240 | alive turns waiting still by a respawning or live camp, or by an altar, without hitting or holding |
| mt_idle | 1.2% | 1.3% | -0.0pt [-0.1pt .. +0.1pt] | 48% | 240 | alive turns idle elsewhere off spawn |
| mt_spawn | 1.1% | 1.2% | -0.1pt [-0.1pt .. -0.0pt] | 42% | 240 | alive turns standing on own spawn |
| mt_recall | 4.6% | 4.7% | -0.1pt [-0.3pt .. +0.0pt] | 40% | 240 | alive turns channelling recalls |
| mt_dead | 6.3% | 9.5% | -3.2pt [-4.6pt .. -1.7pt] | 36% | 240 | champion turns dead |
| regroup_share | 13.9% | 14.1% | -0.3pt [-1.0pt .. +0.4pt] | 49% | 240 | alive turns on walks that end next to an ally who was 9+ away at the start (walking to allies) |
| walk_waste | 28.2% | 28.7% | -0.5pt [-1.5pt .. +0.6pt] | 46% | 240 | walked steps beyond the straight (Chebyshev) line of each walk leg / steps |
| walk_per_gem | 2.6 | 3.1 | -0.4 [-0.8 .. 0.0] | 35% | 240 | walk turns per gem earned (captures and kills) |
| earned_per100 | 158 | 139 | 18.8 [10.1 .. 26.3] | 65% | 240 | gems earned (capture shares + kill bags) per 100 rounds |
| conversion | 76.8% | 69.1% | +7.7pt [+1.7pt .. +13.0pt] | 57% | 240 | tributed / earned gems |
| gem_latency | 130 | 74.7 | 55.5 [40.7 .. 68.1] | 70% | 240 | mean rounds a tributed gem was carried (gem-weighted) |
| gem_exposed | 30.9% | 30.2% | +0.7pt [-1.3pt .. +2.9pt] | 49% | 240 | carried gem-rounds in sight of an enemy / carried gem-rounds |
| carry_top | 67.8% | 61.7% | +6.1pt [+2.9pt .. +8.5pt] | 64% | 240 | share of the team's carried gem-rounds on its top carrier |
| nn_dist | 5.4 | 5.5 | -0.1 [-0.2 .. -0.0] | 43% | 240 | distance to the nearest living ally (alive, off spawn; mean) |
| isolated | 20.2% | 21.0% | -0.8pt [-1.4pt .. -0.1pt] | 42% | 240 | alive champion-rounds off spawn with no ally within 8 |
| outnumbered | 13.2% | 15.4% | -2.2pt [-4.3pt .. -0.2pt] | 45% | 235 | contact champion-rounds (an enemy within 8) with more enemies than allies within 8 |
| outnumbering | 61.1% | 57.8% | +3.3pt [+0.1pt .. +6.6pt] | 56% | 235 | contact champion-rounds with more allies than enemies within 8 |
| control | 51.1% | 48.9% | +2.2pt [+0.4pt .. +3.7pt] | 61% | 240 | camp value nearer (walking) to our champions than theirs, gems + gold/4 per respawn, sampled |
| control_own | 84.2% | 82.3% | +1.8pt [+0.3pt .. +3.2pt] | 60% | 240 | own-half camp value under our control |
| enemy_half | 8.7% | 7.8% | +0.9pt [-0.1pt .. +1.9pt] | 58% | 240 | alive champion-rounds on the enemy half |
| own_lost | 11.4% | 14.8% | -3.4pt [-5.8pt .. -0.9pt] | 30% | 240 | gems of own-half captures taken by the enemy / own-half captured gems |
| contest_win | 52.4% | 47.6% | +4.8pt [-4.2pt .. +11.5pt] | 50% | 208 | contested camp cycles (both teams hit, held or contested) we captured |
| fight_turnout | 51.8% | 51.9% | -0.1pt [-2.0pt .. +1.6pt] | 48% | 229 | own alive champions within 8 of a fight at its start / own alive champions |
| fight_outnum | 32.4% | 37.4% | -5.0pt [-9.2pt .. -0.0pt] | 36% | 229 | fights started with fewer own champions present |
| lonely_death | 29.0% | 23.9% | +5.1pt [-0.3pt .. +11.4pt] | 42% | 163 | deaths to champions with no living ally within 8 |

## charybdis-5564637 in its wins and losses

148 wins, 92 losses. Opponent columns are the same games from the other side.

| metric | charybdis-5564637 won | charybdis-5564637 lost | opponent when charybdis-5564637 won | opponent when charybdis-5564637 lost |
| --- | --- | --- | --- | --- |
| mt_walk | 55.5% | 61.2% | 60.9% | 57.8% |
| mt_walk_bag | 28.9% | 29.6% | 30.4% | 29.9% |
| mt_work | 29.3% | 25.5% | 26.0% | 27.8% |
| mt_fight | 2.8% | 3.3% | 3.1% | 3.1% |
| mt_wait | 5.1% | 3.0% | 2.6% | 4.1% |
| mt_idle | 1.2% | 1.3% | 1.3% | 1.3% |
| mt_spawn | 1.1% | 1.1% | 1.2% | 1.1% |
| mt_recall | 4.8% | 4.2% | 4.7% | 4.6% |
| mt_dead | 3.7% | 10.6% | 12.4% | 4.8% |
| regroup_share | 13.9% | 13.7% | 14.3% | 13.9% |
| walk_waste | 25.8% | 31.9% | 29.7% | 27.1% |
| walk_per_gem | 2.0 | 3.6 | 3.6 | 2.2 |
| earned_per100 | 173 | 133 | 115 | 177 |
| conversion | 91.0% | 53.9% | 56.7% | 88.9% |
| gem_latency | 160 | 82.6 | 53.5 | 109 |
| gem_exposed | 31.8% | 29.5% | 27.7% | 34.2% |
| carry_top | 72.1% | 61.0% | 59.5% | 65.3% |
| nn_dist | 5.4 | 5.4 | 5.5 | 5.5 |
| isolated | 19.8% | 20.8% | 21.3% | 20.5% |
| outnumbered | 10.9% | 16.8% | 17.2% | 12.6% |
| outnumbering | 63.8% | 56.8% | 54.0% | 63.7% |
| control | 53.5% | 47.2% | 46.5% | 52.8% |
| control_own | 87.2% | 79.4% | 81.8% | 83.3% |
| enemy_half | 9.0% | 8.1% | 5.7% | 11.2% |
| own_lost | 7.5% | 17.6% | 17.8% | 9.8% |
| contest_win | 61.4% | 37.9% | 38.6% | 62.1% |
| fight_turnout | 50.8% | 53.2% | 51.3% | 52.8% |
| fight_outnum | 29.1% | 37.5% | 40.6% | 32.6% |
| lonely_death | 29.4% | 29.8% | 25.6% | 24.8% |

## Rounds 1-150, paired

The same quantities over the first 150 rounds only (most break rounds come later), with charybdis-5564637's win rate in the games where its value was higher or lower than opponent's.

| r1-150 | charybdis-5564637 | opponent | charybdis-5564637 - opponent [95% CI] | charybdis-5564637 win rate when higher | charybdis-5564637 win rate when lower |
| --- | --- | --- | --- | --- | --- |
| walk | 54.3% | 54.9% | -0.6pt [-1.1pt .. +0.0pt] | 61% (n=112) | 62% (n=128) |
| work | 34.0% | 33.4% | +0.6pt [-0.1pt .. +1.1pt] | 61% (n=137) | 62% (n=102) |
| wait | 1.6% | 1.5% | +0.1pt [-0.1pt .. +0.3pt] | 60% (n=125) | 63% (n=104) |
| dead | 2.3% | 2.3% | +0.0pt [-0.8pt .. +0.8pt] | 43% (n=46) | 80% (n=51) |
| isolated | 14.7% | 15.7% | -1.0pt [-1.9pt .. +0.1pt] | 57% (n=108) | 65% (n=132) |
| outnumbered | 12.2% | 12.1% | +0.1pt [-3.1pt .. +3.4pt] | 54% (n=81) | 68% (n=88) |
| control | 49.4% | 50.6% | -1.2pt [-2.7pt .. +0.2pt] | 62% (n=109) | 61% (n=131) |

## By map family

Maps by family (the name without its trailing seed and `gen-` prefix); charybdis-5564637 minus opponent per game, mean. Win rate is the focus team's.

| family | games | charybdis-5564637 won | d mt_walk | d mt_work | d mt_dead | d control | d outnumbered | d own_lost | d contest_win | charybdis-5564637 losses: top cause |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ladder | 144 | 60% | -2.1pt | +1.6pt | -3.7pt | +2.9pt | -1.8pt | -6.0pt | +4.2pt | farm 27/57 |
| classic | 60 | 60% | -1.5pt | +0.1pt | -2.3pt | +0.3pt | +0.1pt | +0.9pt | +8.2pt | farm 14/24 |
| contested-centre | 8 | 75% | -6.8pt | +1.8pt | -8.6pt | +6.7pt | -9.8pt | +4.6pt | +6.7pt | bank 1/2 |
| huge | 8 | 88% | -1.3pt | +0.9pt | -0.7pt | +3.7pt | -10.5pt | -2.2pt | +16.7pt | farm 1/1 |
| mut-the-front | 5 | 60% | -1.9pt | +1.2pt | -5.7pt | +3.2pt | -6.7pt | -9.8pt | +13.4pt | farm 2/2 |
| altar-poor | 4 | 75% | +0.4pt | +0.6pt | +0.3pt | -2.5pt | -14.2pt | +2.0pt | -13.6pt | fight 1/1 |
| caves | 4 | 50% | -1.5pt | -0.0pt | +1.0pt | +0.9pt | +0.7pt | -2.5pt | +25.0pt | fight 2/2 |
| jungle | 4 | 50% | -1.3pt | +2.2pt | +2.4pt | +0.8pt | -5.2pt | -0.2pt | -40.0pt | bank 1/2 |
| mut-swirl | 2 | 50% | +1.1pt | +1.2pt | +1.7pt | -1.1pt | -1.5pt | +15.4pt | -21.2pt | farm 1/1 |
| mut-terraces | 1 | 100% | -4.0pt | +1.4pt | +0.0pt | +0.0pt | +0.0pt | +0.0pt | - | - |

## Where the turns go

Share of all champion-rounds (dead included), whole game and per phase.

| class | charybdis-5564637 | opponent | charybdis-5564637 r1-150 | charybdis-5564637 r151-400 | charybdis-5564637 r401-800 | charybdis-5564637 r801+ | opponent r1-150 | opponent r151-400 | opponent r401-800 | opponent r801+ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dead | 6.8% | 10.0% | 2.3% | 5.1% | 7.9% | 11.9% | 2.2% | 6.9% | 13.3% | 16.6% |
| lost | 0.2% | 0.2% | 0.3% | 0.2% | 0.2% | 0.3% | 0.3% | 0.2% | 0.2% | 0.2% |
| fight | 2.9% | 2.9% | 2.3% | 2.6% | 3.0% | 4.1% | 2.3% | 2.6% | 2.9% | 4.0% |
| tribute | 2.4% | 1.7% | 0.3% | 1.3% | 3.4% | 4.6% | 0.7% | 1.4% | 2.0% | 2.5% |
| recall | 4.1% | 4.1% | 4.6% | 5.1% | 3.8% | 2.6% | 4.7% | 5.1% | 3.7% | 2.6% |
| teleport | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| camp | 18.8% | 18.0% | 29.5% | 21.9% | 15.6% | 9.0% | 28.7% | 21.3% | 14.4% | 8.7% |
| hold | 3.1% | 2.9% | 3.3% | 3.5% | 3.0% | 2.4% | 3.3% | 3.2% | 2.7% | 2.3% |
| walk_bag | 27.9% | 28.3% | 19.1% | 32.2% | 30.6% | 24.6% | 19.9% | 31.8% | 30.1% | 27.5% |
| walk | 26.8% | 26.5% | 34.2% | 23.5% | 25.5% | 27.4% | 34.0% | 23.3% | 25.0% | 27.0% |
| spawn | 1.0% | 1.0% | 1.1% | 1.1% | 0.9% | 0.9% | 1.1% | 1.1% | 1.0% | 0.9% |
| wait_camp | 2.6% | 2.0% | 1.5% | 2.4% | 3.0% | 3.3% | 1.4% | 2.1% | 2.2% | 2.2% |
| wait_altar | 2.0% | 1.2% | 0.0% | 0.2% | 1.8% | 7.4% | 0.0% | 0.1% | 1.2% | 3.9% |
| idle | 1.3% | 1.3% | 1.4% | 1.0% | 1.3% | 1.5% | 1.4% | 1.0% | 1.3% | 1.6% |

## What the walking was for

Walk turns by what the walk led to (the class of the first turn after the leg), as a share of alive turns. "regroup" counts the walks that end within 3 of an ally who was more than 8 away when the walk began, by destination.

| walk led to | charybdis-5564637 | opponent | charybdis-5564637 regroup | opponent regroup |
| --- | --- | --- | --- | --- |
| camp | 24.3% | 24.6% | 5.7% | 5.8% |
| hold | 2.3% | 2.0% | 0.3% | 0.3% |
| tribute | 3.8% | 5.3% | 1.3% | 1.2% |
| fight | 8.5% | 9.9% | 2.1% | 2.6% |
| recall | 4.2% | 4.1% | 0.6% | 0.6% |
| spawn | 0.0% | 0.0% | 0.0% | 0.0% |
| wait_camp | 9.7% | 9.1% | 3.2% | 3.2% |
| wait_altar | 1.1% | 0.7% | 0.3% | 0.2% |
| idle | 3.7% | 3.8% | 0.8% | 0.8% |
| dead | 0.2% | 0.4% | 0.1% | 0.1% |
| other | 0.9% | 1.0% | 0.3% | 0.2% |

## Champion roles

Per champion type, pooled over games: turn mix (alive turns), share of the team's capture gems and of its carried gem-rounds.

**charybdis-5564637**

| type | rounds | walk | walk_bag | camp | hold | fight | recall | wait | idle | dead | capture gems | gem-rounds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Cassi | 194217 | 38% | 25% | 22% | 3% | 2% | 3% | 3% | 1% | 10% | 9% | 3% |
| Issac | 194217 | 33% | 25% | 24% | 4% | 3% | 5% | 3% | 1% | 10% | 10% | 3% |
| Prism | 149250 | 7% | 48% | 14% | 6% | 4% | 4% | 4% | 1% | 5% | 37% | 75% |
| Vesper Vale | 138416 | 14% | 37% | 24% | 4% | 3% | 6% | 6% | 1% | 3% | 20% | 10% |
| Willow | 125524 | 56% | 12% | 14% | 1% | 1% | 2% | 10% | 3% | 5% | 1% | 1% |
| Heart of Ruin | 77740 | 30% | 29% | 21% | 3% | 6% | 4% | 3% | 1% | 6% | 5% | 2% |
| Vendetta | 58040 | 21% | 35% | 23% | 4% | 2% | 7% | 3% | 2% | 4% | 6% | 2% |
| Ren | 45673 | 25% | 30% | 23% | 3% | 5% | 5% | 5% | 2% | 7% | 2% | 1% |
| Marcella | 35431 | 30% | 30% | 11% | 3% | 6% | 5% | 11% | 0% | 5% | 3% | 1% |
| Ryth | 32881 | 22% | 29% | 20% | 3% | 6% | 4% | 12% | 0% | 7% | 3% | 1% |
| Varg | 27376 | 28% | 36% | 20% | 3% | 2% | 5% | 2% | 0% | 5% | 3% | 1% |
| Tavi | 12238 | 38% | 23% | 20% | 5% | 5% | 3% | 2% | 0% | 8% | 1% | 0% |

**opponent**

| type | rounds | walk | walk_bag | camp | hold | fight | recall | wait | idle | dead | capture gems | gem-rounds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Cassi | 194217 | 36% | 27% | 22% | 2% | 2% | 4% | 3% | 1% | 15% | 9% | 4% |
| Issac | 194217 | 31% | 28% | 24% | 4% | 3% | 5% | 2% | 1% | 15% | 11% | 4% |
| Prism | 149250 | 10% | 47% | 18% | 6% | 4% | 5% | 3% | 1% | 9% | 30% | 71% |
| Vesper Vale | 138416 | 18% | 37% | 22% | 3% | 4% | 6% | 5% | 1% | 6% | 21% | 8% |
| Willow | 125524 | 57% | 16% | 14% | 0% | 1% | 2% | 6% | 3% | 7% | 1% | 1% |
| Heart of Ruin | 77740 | 29% | 31% | 21% | 3% | 6% | 4% | 2% | 1% | 7% | 6% | 3% |
| Vendetta | 58040 | 23% | 35% | 21% | 4% | 2% | 7% | 3% | 2% | 5% | 7% | 2% |
| Ren | 45673 | 23% | 31% | 22% | 3% | 4% | 5% | 8% | 2% | 7% | 3% | 1% |
| Marcella | 35431 | 34% | 32% | 11% | 3% | 7% | 5% | 4% | 1% | 10% | 4% | 2% |
| Ryth | 32881 | 26% | 33% | 18% | 3% | 7% | 5% | 3% | 0% | 9% | 3% | 2% |
| Varg | 27376 | 31% | 34% | 19% | 3% | 2% | 5% | 2% | 0% | 4% | 3% | 1% |
| Tavi | 12238 | 41% | 24% | 15% | 5% | 6% | 4% | 2% | 1% | 12% | 1% | 0% |

## Gem flow

Per game means. tributed = captured + taken by kills - lost to champions - lost to camps - carried at the end (the identity holds exactly in every game unless noted).

| gems | charybdis-5564637 | opponent |
| --- | --- | --- |
| cap | 979 | 879 |
| kill | 192 | 146 |
| lost_champ | 146 | 192 |
| lost_camp | 7.1 | 6.6 |
| carried_end | 149 | 128 |
| tributed | 870 | 698 |

## Cohesion and map control by phase

| phase | charybdis-5564637 isolated | charybdis-5564637 outnumbered | charybdis-5564637 control | opponent isolated | opponent outnumbered | opponent control |
| --- | --- | --- | --- | --- | --- | --- |
| r1-150 | 15% | 12% | 49% | 16% | 13% | 51% |
| r151-400 | 22% | 12% | 51% | 23% | 14% | 49% |
| r401-800 | 24% | 13% | 52% | 25% | 17% | 48% |
| r801+ | 25% | 14% | 53% | 26% | 20% | 47% |

isolated: field champion-rounds with no ally within 8; outnumbered: contact rounds with more enemies than allies within 8; control: share of camp value nearer by walking to that team's champions.

## Who turns up to fights

At each engagement's first round (analysis/fights.py clustering), every own champion alive and more than 8 from the fight, by what it was doing; "joined later" are those that dealt or took damage in it anyway. Distances are to the fight's first location.

| absent ally was | charybdis-5564637 per fight | opponent per fight |
| --- | --- | --- |
| walking >16 | 0.79 | 0.78 |
| walking <=16 | 0.56 | 0.56 |
| dead | 0.41 | 0.64 |
| camp >16 | 0.24 | 0.23 |
| camp <=16 | 0.20 | 0.19 |
| channel >16 | 0.06 | 0.07 |
| channel <=16 | 0.06 | 0.05 |
| hold >16 | 0.05 | 0.05 |
| joined later | 0.04 | 0.04 |
| hold <=16 | 0.04 | 0.03 |
| waiting >16 | 0.03 | 0.03 |
| waiting <=16 | 0.03 | 0.02 |
| idle >16 | 0.02 | 0.02 |
| idle <=16 | 0.01 | 0.02 |
| spawn >16 | 0.01 | 0.01 |
| another fight >16 | 0.01 | 0.01 |
| spawn <=16 | 0.01 | 0.01 |
| another fight <=16 | 0.01 | 0.01 |
| other <=16 | 0.00 | 0.00 |
| other >16 | 0.00 | 0.00 |

Net swing (gems from kills - own bags lost + gold/4) by champions present at the start, own minus enemy:

| numbers | charybdis-5564637 fights | charybdis-5564637 mean swing | opponent fights | opponent mean swing |
| --- | --- | --- | --- | --- |
| -2 or fewer | 919 | -1.4 | 1291 | -13.6 |
| -1 | 1219 | -1.8 | 1450 | -5.0 |
| +0 | 1834 | 9.3 | 1834 | -9.3 |
| +1 | 1450 | 5.0 | 1219 | 1.8 |
| +2 or more | 1291 | 13.6 | 919 | 1.4 |

## Camp contests

A camp cycle (from respawn to capture) is contested when both teams hit its monsters or held its tiles, or a hold was reset as contested. Steals: captured by the team that did not land the clearing blow.

| per game | charybdis-5564637 | opponent |
| --- | --- | --- |
| won | 3.71 | 3.44 |
| lost | 3.44 | 3.71 |
| won_gems | 97.65 | 81.62 |
| lost_gems | 81.62 | 97.65 |
| steals | 0.96 | 0.92 |
| stolen | 0.92 | 0.96 |
| captured gems, own half | 745 | 697 |
| captured gems, mid half | 124 | 89.7 |
| captured gems, enemy half | 110 | 93.2 |

| group | charybdis-5564637 won | charybdis-5564637 lost | charybdis-5564637 share |
| --- | --- | --- | --- |
| $$ | 43 | 52 | 45% |
| GGW | 49 | 37 | 57% |
| $$WW | 42 | 36 | 54% |
| GGGGG | 41 | 31 | 57% |
| $W | 39 | 31 | 56% |
| GW | 29 | 37 | 44% |
| $$W | 25 | 37 | 40% |
| GG | 21 | 37 | 36% |
| $EG | 29 | 24 | 55% |
| GGGG | 23 | 27 | 46% |
| W | 17 | 27 | 39% |
| $$$ | 22 | 18 | 55% |
| GWW | 14 | 25 | 36% |
| $$$E | 22 | 16 | 58% |
| GGGGGG | 23 | 15 | 61% |

(81 more rows in `macro-contest_types.csv`)

## Which camps get taken

Captures per group type against capacity: the cycles each type could give at most (game rounds / (respawn + 6 capture rounds), summed over the map's groups of that type, both halves). Low shares on strong groups are camps nobody farms.

| group | capacity a game | charybdis-5564637 captures | opponent captures | charybdis-5564637 share | opponent share | taken (both) | charybdis-5564637 gems | opponent gems |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| $W | 24.8 | 2.7 | 2.4 | 11% | 10% | 21% | 11.0 | 9.8 |
| $$ | 22.4 | 3.8 | 3.9 | 17% | 17% | 34% | 0.0 | 0.0 |
| GW | 18.6 | 3.9 | 3.4 | 21% | 18% | 39% | 44.7 | 39.8 |
| $$W | 14.3 | 2.1 | 2.2 | 15% | 15% | 30% | 8.4 | 8.7 |
| G | 11.5 | 3.3 | 3.0 | 28% | 26% | 55% | 23.8 | 21.9 |
| $$WW | 10.7 | 1.5 | 1.2 | 14% | 12% | 26% | 12.0 | 9.9 |
| GGW | 10.1 | 2.3 | 2.2 | 23% | 22% | 45% | 45.5 | 43.6 |
| $ | 8.9 | 1.0 | 1.1 | 11% | 12% | 24% | 0.0 | 0.0 |
| GG | 7.9 | 2.7 | 2.5 | 34% | 32% | 66% | 40.8 | 37.3 |
| W | 7.7 | 0.6 | 0.6 | 8% | 8% | 15% | 2.3 | 2.4 |
| $GWW | 7.1 | 1.1 | 1.1 | 16% | 16% | 32% | 17.4 | 17.7 |
| $WW | 6.8 | 1.0 | 0.9 | 15% | 13% | 28% | 8.3 | 6.9 |
| $EG | 6.4 | 1.4 | 1.3 | 22% | 20% | 42% | 32.6 | 29.1 |
| $$$W | 5.4 | 0.9 | 0.9 | 16% | 16% | 32% | 3.5 | 3.5 |
| EGG | 5.1 | 1.0 | 1.0 | 20% | 20% | 40% | 32.6 | 32.3 |
| GGGG | 4.6 | 1.5 | 1.5 | 32% | 32% | 64% | 44.1 | 45.0 |
| $GW | 4.1 | 1.0 | 0.9 | 25% | 23% | 48% | 11.8 | 10.8 |
| $$EE | 3.9 | 0.6 | 0.6 | 15% | 16% | 31% | 17.9 | 18.1 |
| GGWW | 3.7 | 0.7 | 0.6 | 19% | 16% | 35% | 17.2 | 14.0 |
| $$$ | 3.7 | 1.0 | 0.8 | 26% | 21% | 47% | 0.0 | 0.0 |

(124 more rows in `macro-capacity.csv`)

## Why games are lost: charybdis-5564637's losses

The break round is the last round the loser had at least the winner's wealth (tributed + carried gems); 0 means it was never level after round 1. The window is the 100 rounds after it. Its cause is the largest of: farm (capture gems, winner - loser), fight (kill gems taken minus bags lost to champions, winner - loser), camp (bags lost to camps, loser - winner); "bank" when the loser lost while holding at least as much wealth (gems carried, not tributed). Whole-game components are over all rounds.

| cause of the break window | games | share | median break | loser dead | winner dead | loser work | winner work | loser walk | winner walk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| farm | 46 | 50% | 234 | 14% | 3% | 19% | 25% | 57% | 57% |
| fight | 38 | 41% | 407 | 28% | 6% | 17% | 25% | 46% | 50% |
| camp | 0 | 0% | - | - | - | - | - | - | - |
| bank | 8 | 9% | 1030 | - | - | - | - | - | - |

Turn shares are over the windows of that cause (work = camp, hold, tribute). A farm window with a high loser dead share is a farm deficit that follows deaths; one with level dead shares is out-farming with bodies alive.

Break round: median 371 (p25 179, p75 614); 0 never level, 19 in rounds 1-150, 30 in 151-400, 43 after 400.

| component (winner advantage, gems) | whole game | break window |
| --- | --- | --- |
| farm | 170 | 71.0 |
| fight | 294 | 271 |
| camp | 2.2 | 1.6 |
| bank | 116 | - |

Turn mix in the break windows (loser vs winner):

| class | loser | winner |
| --- | --- | --- |
| dead | 20.7% | 4.2% |
| lost | 0.2% | 0.3% |
| fight | 3.3% | 3.6% |
| tribute | 0.9% | 5.3% |
| recall | 3.3% | 4.3% |
| teleport | 0.0% | 0.0% |
| camp | 14.6% | 16.6% |
| hold | 2.2% | 3.4% |
| walk_bag | 24.5% | 29.1% |
| walk | 26.9% | 24.4% |
| spawn | 1.0% | 0.9% |
| wait_camp | 1.5% | 2.5% |
| wait_altar | 0.1% | 4.2% |
| idle | 0.9% | 1.2% |

Loser deaths in the break windows: 115 over 92 games (1.25 a game), by type Prism 32, Cassi 17, Issac 15, Vesper Vale 13, Willow 7, Heart of Ruin 7, Marcella 6, Ren 6, Varg 4, Vendetta 4, Ryth 2, Tavi 2; bag at death median 14, 42 with 50+.

What opened the window: the loser's largest-bag death within 10 rounds of the break, if any:

| trigger | games | share |
| --- | --- | --- |
| no loser death within 10 rounds | 46 | 50% |
| Prism died with 200+ gems | 15 | 16% |
| ended holding the larger wealth | 8 | 9% |
| Prism died with 50-199 gems | 5 | 5% |
| Issac died with <50 gems | 4 | 4% |
| Cassi died with <50 gems | 3 | 3% |
| Prism died with <50 gems | 3 | 3% |
| Ren died with <50 gems | 2 | 2% |
| Ryth died with 50-199 gems | 1 | 1% |
| Cassi died with 50-199 gems | 1 | 1% |
| Tavi died with 200+ gems | 1 | 1% |
| Varg died with <50 gems | 1 | 1% |

(2 more rows in `macro-triggers.csv`)

Largest windows (gap = winner minus loser wealth at the window's end):

| game / break | map | cause | gap | window components | loser deaths in the window |
| --- | --- | --- | --- | --- | --- |
| a6e2109cda1e704c r1135 | gen-caves-331000004000 | fight | 1801 | farm +8 fight +2730 camp +0 | r1136 Prism bag 1365 by Prism |
| b93ae9243fde1d27 r470 | gen-jungle-331000007001 | fight | 1415 | farm -146 fight +1592 camp +0 | r471 Prism bag 590 by Prism; r551 Issac bag 33 by Prism; r558 Vesper Vale bag 115 by Prism |
| 6d7b23c09fce41d0 r1126 | gen-ladder-331000000036 | fight | 1276 | farm -66 fight +1578 camp +0 | r1127 Prism bag 732 by Prism; r1174 Ren bag 32 by Prism; r1207 Cassi bag 18 by Ren; r1217 Prism bag 0 by Prism |
| 1fe75c018cdec6b3 r1312 | gen-ladder-331000000014 | fight | 1266 | farm -14 fight +1288 camp +0 | r1313 Prism bag 618 by Cassi; r1327 Marcella bag 0 by Vesper Vale; r1334 Issac bag 0 by Cassi |
| 383dccc831f852e0 r653 | gen-ladder-331000000034 | fight | 1249 | farm +7 fight +1324 camp +0 | r654 Prism bag 533 by Prism; r656 Cassi bag 4 by Prism; r666 Ren bag 12 by Prism; r693 Vesper Vale bag 81 by Prism |
| 762aee3cf5e9f49a r381 | gen-ladder-331000000031 | fight | 1098 | farm -32 fight +1752 camp +0 | r382 Prism bag 621 by Heart of Ruin; r425 Vesper Vale bag 105 by Cassi; r472 Cassi bag 57 by Vesper Vale; r478 Heart of Ruin bag 36 by Vesper Vale |
| e461d84302229e72 r424 | gen-ladder-331000000027 | fight | 1088 | farm +28 fight +1066 camp +0 | r425 Prism bag 515 by Vesper Vale; r451 Ren bag 18 by Vesper Vale |
| d52aa01386fc2a6e r1174 | gen-classic-331000001023 | fight | 973 | farm -18 fight +1870 camp +0 | r1175 Tavi bag 935 by Marcella; r1249 Cassi bag 0 by Prism; r1251 Willow bag 0 by Prism |
| da301504f48cb738 r624 | gen-ladder-331000000050 | fight | 924 | farm +61 fight +1160 camp +0 | r625 Prism bag 580 by Ryth; r654 Issac bag 0 by Vesper Vale; r709 Willow bag 0 by Vesper Vale; r717 Prism bag 0 by Vesper Vale |
| 9a770f6d72daba7d r794 | gen-ladder-331000000062 | fight | 923 | farm -13 fight +1038 camp +0 | r795 Issac bag 75 by Prism; r796 Prism bag 256 by Vesper Vale; r834 Vesper Vale bag 146 by Vesper Vale |
| 76788d9b65fa4448 r492 | gen-ladder-331000000064 | fight | 786 | farm +3 fight +904 camp +0 | r493 Prism bag 452 by Prism; r494 Vesper Vale bag 0 by Prism; r501 Vendetta bag 0 by Vesper Vale; r534 Heart of Ruin bag 0 by camp |
| e29264bf6ed3d55c r706 | gen-ladder-331000000049 | fight | 726 | farm -40 fight +890 camp +0 | r707 Prism bag 445 by Prism |
| 10bde3a3274409e1 r475 | gen-ladder-331000000041 | fight | 685 | farm +141 fight +558 camp +0 | r488 Prism bag 279 by Prism; r536 Vesper Vale bag 0 by Vesper Vale; r556 Issac bag 0 by Prism |
| 5f7eb96213aa4522 r329 | gen-classic-331000001014 | fight | 625 | farm +311 fight +520 camp +0 | r330 Cassi bag 112 by Prism; r334 Marcella bag 78 by Prism |
| e8da0c0806f8626c r390 | gen-ladder-331000000019 | fight | 577 | farm +78 fight +970 camp +0 | r391 Prism bag 394 by Prism; r409 Issac bag 63 by Prism |
| c30bc8833e01e65a r153 | gen-ladder-331000000006 | fight | 568 | farm +302 fight +332 camp +0 | r154 Prism bag 145 by Issac; r162 Heart of Ruin bag 0 by Cassi; r180 Willow bag 0 by Prism; r195 Cassi bag 0 by Prism |
| d5bb13924247cf68 r243 | gen-classic-331000001010 | fight | 525 | farm +214 fight +418 camp +0 | r244 Prism bag 209 by Prism; r250 Cassi bag 0 by Prism |
| a223e3d82b1aa339 r580 | gen-classic-331000001011 | fight | 517 | farm -145 fight +822 camp +0 | r581 Prism bag 411 by Prism |
| e2bc4f17d7c6bf7e r483 | gen-ladder-331000000016 | fight | 401 | farm +40 fight +376 camp +0 | r484 Prism bag 188 by Prism |
| 28f737927a50f26b r503 | gen-ladder-331000000060 | fight | 398 | farm +22 fight +540 camp +0 | r504 Prism bag 270 by Vesper Vale; r594 Willow bag 0 by Vesper Vale |
| d074490e0b129197 r260 | gen-ladder-331000000043 | fight | 387 | farm +25 fight +382 camp +0 | r261 Prism bag 191 by Prism |
| 0f714f02b91ad2f5 r655 | gen-ladder-331000000045 | farm | 373 | farm +508 fight +0 camp +0 | - |
| b65dda1be10799e5 r156 | gen-ladder-331000000050 | fight | 293 | farm +101 fight +196 camp +0 | r246 Prism bag 98 by Prism |
| 43c1e73ef209bfcd r253 | gen-classic-331000001002 | fight | 289 | farm +137 fight +188 camp +0 | r312 Issac bag 0 by Issac; r313 Willow bag 0 by Prism; r321 Prism bag 94 by Prism |
| 5a05be9e5425212b r67 | gen-ladder-331000000023 | farm | 287 | farm +287 fight +0 camp +0 | r91 Prism bag 0 by Prism |
