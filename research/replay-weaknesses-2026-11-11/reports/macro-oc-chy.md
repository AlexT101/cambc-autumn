# Macro: turns, gems, cohesion, control, losses

Set: replays/batch-20261111-183545-ab-chy-vs-ocean-d18-hold (240 games, 121 clusters, focus ocean-chybase). Sides: ocean-chybase vs opponent in the same game (240 pairs). Paired by game: the focus team against its opponent.

Every number is read from the replay alone (no bot traces). Turn classes are per champion-round, first match wins: dead, lost (stunned/out of fuel/error), fight (dealt or took champion damage), tribute/recall/teleport channel, camp (hit a camp), walk_bag/walk (moved, carrying gems or not), hold (still on a claimable group tile), spawn (still on own spawn), idle. Distances are Chebyshev unless noted; camp control uses walking distance. Differences are mean ocean-chybase minus opponent with a 95% cluster-bootstrap CI over map pairs or ladder groups.

## Macro metrics, paired

| metric | ocean-chybase | opponent | ocean-chybase - opponent [95% CI] | ocean-chybase higher | games | definition |
| --- | --- | --- | --- | --- | --- | --- |
| mt_walk | 59.7% | 57.7% | +2.0pt [+0.9pt .. +3.1pt] | 61% | 240 | alive turns walking (with or without gems) |
| mt_walk_bag | 30.2% | 29.2% | +1.0pt [-0.0pt .. +2.0pt] | 56% | 240 | alive turns walking while carrying gems |
| mt_work | 26.7% | 27.8% | -1.2pt [-1.9pt .. -0.4pt] | 40% | 240 | alive turns at work: hitting camps, holding captures, tributing |
| mt_fight | 3.1% | 3.0% | +0.1pt [-0.0pt .. +0.2pt] | 57% | 240 | alive turns in fights (dealt or took champion damage) |
| mt_wait | 3.1% | 4.3% | -1.1pt [-2.0pt .. -0.4pt] | 43% | 240 | alive turns waiting still by a respawning or live camp, or by an altar, without hitting or holding |
| mt_idle | 1.3% | 1.2% | +0.0pt [-0.1pt .. +0.1pt] | 51% | 240 | alive turns idle elsewhere off spawn |
| mt_spawn | 1.2% | 1.1% | +0.1pt [+0.0pt .. +0.1pt] | 57% | 240 | alive turns standing on own spawn |
| mt_recall | 4.7% | 4.6% | +0.1pt [-0.0pt .. +0.3pt] | 60% | 240 | alive turns channelling recalls |
| mt_dead | 9.5% | 6.3% | +3.2pt [+1.7pt .. +4.6pt] | 56% | 240 | champion turns dead |
| regroup_share | 14.1% | 13.9% | +0.3pt [-0.4pt .. +1.0pt] | 51% | 240 | alive turns on walks that end next to an ally who was 9+ away at the start (walking to allies) |
| walk_waste | 28.7% | 28.2% | +0.5pt [-0.6pt .. +1.5pt] | 54% | 240 | walked steps beyond the straight (Chebyshev) line of each walk leg / steps |
| walk_per_gem | 3.1 | 2.6 | 0.4 [-0.0 .. 0.8] | 65% | 240 | walk turns per gem earned (captures and kills) |
| earned_per100 | 139 | 158 | -18.8 [-26.3 .. -10.1] | 35% | 240 | gems earned (capture shares + kill bags) per 100 rounds |
| conversion | 69.1% | 76.8% | -7.7pt [-13.0pt .. -1.7pt] | 42% | 240 | tributed / earned gems |
| gem_latency | 74.7 | 130 | -55.5 [-68.1 .. -40.7] | 30% | 240 | mean rounds a tributed gem was carried (gem-weighted) |
| gem_exposed | 30.2% | 30.9% | -0.7pt [-2.9pt .. +1.3pt] | 48% | 240 | carried gem-rounds in sight of an enemy / carried gem-rounds |
| carry_top | 61.7% | 67.8% | -6.1pt [-8.5pt .. -2.9pt] | 36% | 240 | share of the team's carried gem-rounds on its top carrier |
| nn_dist | 5.5 | 5.4 | 0.1 [0.0 .. 0.2] | 57% | 240 | distance to the nearest living ally (alive, off spawn; mean) |
| isolated | 21.0% | 20.2% | +0.8pt [+0.1pt .. +1.4pt] | 57% | 240 | alive champion-rounds off spawn with no ally within 8 |
| outnumbered | 15.4% | 13.2% | +2.2pt [+0.2pt .. +4.3pt] | 54% | 235 | contact champion-rounds (an enemy within 8) with more enemies than allies within 8 |
| outnumbering | 57.8% | 61.1% | -3.3pt [-6.6pt .. -0.1pt] | 43% | 235 | contact champion-rounds with more allies than enemies within 8 |
| control | 48.9% | 51.1% | -2.2pt [-3.7pt .. -0.4pt] | 39% | 240 | camp value nearer (walking) to our champions than theirs, gems + gold/4 per respawn, sampled |
| control_own | 82.3% | 84.2% | -1.8pt [-3.2pt .. -0.3pt] | 38% | 240 | own-half camp value under our control |
| enemy_half | 7.8% | 8.7% | -0.9pt [-1.9pt .. +0.1pt] | 38% | 240 | alive champion-rounds on the enemy half |
| own_lost | 14.8% | 11.4% | +3.4pt [+0.9pt .. +5.8pt] | 52% | 240 | gems of own-half captures taken by the enemy / own-half captured gems |
| contest_win | 47.6% | 52.4% | -4.8pt [-11.5pt .. +4.2pt] | 40% | 208 | contested camp cycles (both teams hit, held or contested) we captured |
| fight_turnout | 51.9% | 51.8% | +0.1pt [-1.6pt .. +2.0pt] | 49% | 229 | own alive champions within 8 of a fight at its start / own alive champions |
| fight_outnum | 37.4% | 32.4% | +5.0pt [+0.0pt .. +9.2pt] | 53% | 229 | fights started with fewer own champions present |
| lonely_death | 23.9% | 29.0% | -5.1pt [-11.4pt .. +0.3pt] | 38% | 163 | deaths to champions with no living ally within 8 |

## ocean-chybase in its wins and losses

92 wins, 148 losses. Opponent columns are the same games from the other side.

| metric | ocean-chybase won | ocean-chybase lost | opponent when ocean-chybase won | opponent when ocean-chybase lost |
| --- | --- | --- | --- | --- |
| mt_walk | 57.8% | 60.9% | 61.2% | 55.5% |
| mt_walk_bag | 29.9% | 30.4% | 29.6% | 28.9% |
| mt_work | 27.8% | 26.0% | 25.5% | 29.3% |
| mt_fight | 3.1% | 3.1% | 3.3% | 2.8% |
| mt_wait | 4.1% | 2.6% | 3.0% | 5.1% |
| mt_idle | 1.3% | 1.3% | 1.3% | 1.2% |
| mt_spawn | 1.1% | 1.2% | 1.1% | 1.1% |
| mt_recall | 4.6% | 4.7% | 4.2% | 4.8% |
| mt_dead | 4.8% | 12.4% | 10.6% | 3.7% |
| regroup_share | 13.9% | 14.3% | 13.7% | 13.9% |
| walk_waste | 27.1% | 29.7% | 31.9% | 25.8% |
| walk_per_gem | 2.2 | 3.6 | 3.6 | 2.0 |
| earned_per100 | 177 | 115 | 133 | 173 |
| conversion | 88.9% | 56.7% | 53.9% | 91.0% |
| gem_latency | 109 | 53.5 | 82.6 | 160 |
| gem_exposed | 34.2% | 27.7% | 29.5% | 31.8% |
| carry_top | 65.3% | 59.5% | 61.0% | 72.1% |
| nn_dist | 5.5 | 5.5 | 5.4 | 5.4 |
| isolated | 20.5% | 21.3% | 20.8% | 19.8% |
| outnumbered | 12.6% | 17.2% | 16.8% | 10.9% |
| outnumbering | 63.7% | 54.0% | 56.8% | 63.8% |
| control | 52.8% | 46.5% | 47.2% | 53.5% |
| control_own | 83.3% | 81.8% | 79.4% | 87.2% |
| enemy_half | 11.2% | 5.7% | 8.1% | 9.0% |
| own_lost | 9.8% | 17.8% | 17.6% | 7.5% |
| contest_win | 62.1% | 38.6% | 37.9% | 61.4% |
| fight_turnout | 52.8% | 51.3% | 53.2% | 50.8% |
| fight_outnum | 32.6% | 40.6% | 37.5% | 29.1% |
| lonely_death | 24.8% | 25.6% | 29.8% | 29.4% |

## Rounds 1-150, paired

The same quantities over the first 150 rounds only (most break rounds come later), with ocean-chybase's win rate in the games where its value was higher or lower than opponent's.

| r1-150 | ocean-chybase | opponent | ocean-chybase - opponent [95% CI] | ocean-chybase win rate when higher | ocean-chybase win rate when lower |
| --- | --- | --- | --- | --- | --- |
| walk | 54.9% | 54.3% | +0.6pt [-0.0pt .. +1.1pt] | 38% (n=128) | 39% (n=112) |
| work | 33.4% | 34.0% | -0.6pt [-1.1pt .. +0.1pt] | 38% (n=102) | 39% (n=137) |
| wait | 1.5% | 1.6% | -0.1pt [-0.3pt .. +0.1pt] | 37% (n=104) | 40% (n=125) |
| dead | 2.3% | 2.3% | -0.0pt [-0.8pt .. +0.8pt] | 20% (n=51) | 57% (n=46) |
| isolated | 15.7% | 14.7% | +1.0pt [-0.1pt .. +1.9pt] | 35% (n=132) | 43% (n=108) |
| outnumbered | 12.1% | 12.2% | -0.1pt [-3.4pt .. +3.1pt] | 32% (n=88) | 46% (n=81) |
| control | 50.6% | 49.4% | +1.2pt [-0.2pt .. +2.7pt] | 39% (n=131) | 38% (n=109) |

## By map family

Maps by family (the name without its trailing seed and `gen-` prefix); ocean-chybase minus opponent per game, mean. Win rate is the focus team's.

| family | games | ocean-chybase won | d mt_walk | d mt_work | d mt_dead | d control | d outnumbered | d own_lost | d contest_win | ocean-chybase losses: top cause |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ladder | 144 | 40% | +2.1pt | -1.6pt | +3.7pt | -2.9pt | +1.8pt | +6.0pt | -4.2pt | farm 70/87 |
| classic | 60 | 40% | +1.5pt | -0.1pt | +2.3pt | -0.3pt | -0.1pt | -0.9pt | -8.2pt | farm 23/36 |
| contested-centre | 8 | 25% | +6.8pt | -1.8pt | +8.6pt | -6.7pt | +9.8pt | -4.6pt | -6.7pt | fight 3/6 |
| huge | 8 | 12% | +1.3pt | -0.9pt | +0.7pt | -3.7pt | +10.5pt | +2.2pt | -16.7pt | farm 5/7 |
| mut-the-front | 5 | 40% | +1.9pt | -1.2pt | +5.7pt | -3.2pt | +6.7pt | +9.8pt | -13.4pt | farm 3/3 |
| altar-poor | 4 | 25% | -0.4pt | -0.6pt | -0.3pt | +2.5pt | +14.2pt | -2.0pt | +13.6pt | fight 3/3 |
| caves | 4 | 50% | +1.5pt | +0.0pt | -1.0pt | -0.9pt | -0.7pt | +2.5pt | -25.0pt | bank 1/2 |
| jungle | 4 | 50% | +1.3pt | -2.2pt | -2.4pt | -0.8pt | +5.2pt | +0.2pt | +40.0pt | fight 2/2 |
| mut-swirl | 2 | 50% | -1.1pt | -1.2pt | -1.7pt | +1.1pt | +1.5pt | -15.4pt | +21.2pt | farm 1/1 |
| mut-terraces | 1 | 0% | +4.0pt | -1.4pt | +0.0pt | -0.0pt | +0.0pt | +0.0pt | - | farm 1/1 |

## Where the turns go

Share of all champion-rounds (dead included), whole game and per phase.

| class | ocean-chybase | opponent | ocean-chybase r1-150 | ocean-chybase r151-400 | ocean-chybase r401-800 | ocean-chybase r801+ | opponent r1-150 | opponent r151-400 | opponent r401-800 | opponent r801+ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dead | 10.0% | 6.8% | 2.2% | 6.9% | 13.3% | 16.6% | 2.3% | 5.1% | 7.9% | 11.9% |
| lost | 0.2% | 0.2% | 0.3% | 0.2% | 0.2% | 0.2% | 0.3% | 0.2% | 0.2% | 0.3% |
| fight | 2.9% | 2.9% | 2.3% | 2.6% | 2.9% | 4.0% | 2.3% | 2.6% | 3.0% | 4.1% |
| tribute | 1.7% | 2.4% | 0.7% | 1.4% | 2.0% | 2.5% | 0.3% | 1.3% | 3.4% | 4.6% |
| recall | 4.1% | 4.1% | 4.7% | 5.1% | 3.7% | 2.6% | 4.6% | 5.1% | 3.8% | 2.6% |
| teleport | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| camp | 18.0% | 18.8% | 28.7% | 21.3% | 14.4% | 8.7% | 29.5% | 21.9% | 15.6% | 9.0% |
| hold | 2.9% | 3.1% | 3.3% | 3.2% | 2.7% | 2.3% | 3.3% | 3.5% | 3.0% | 2.4% |
| walk_bag | 28.3% | 27.9% | 19.9% | 31.8% | 30.1% | 27.5% | 19.1% | 32.2% | 30.6% | 24.6% |
| walk | 26.5% | 26.8% | 34.0% | 23.3% | 25.0% | 27.0% | 34.2% | 23.5% | 25.5% | 27.4% |
| spawn | 1.0% | 1.0% | 1.1% | 1.1% | 1.0% | 0.9% | 1.1% | 1.1% | 0.9% | 0.9% |
| wait_camp | 2.0% | 2.6% | 1.4% | 2.1% | 2.2% | 2.2% | 1.5% | 2.4% | 3.0% | 3.3% |
| wait_altar | 1.2% | 2.0% | 0.0% | 0.1% | 1.2% | 3.9% | 0.0% | 0.2% | 1.8% | 7.4% |
| idle | 1.3% | 1.3% | 1.4% | 1.0% | 1.3% | 1.6% | 1.4% | 1.0% | 1.3% | 1.5% |

## What the walking was for

Walk turns by what the walk led to (the class of the first turn after the leg), as a share of alive turns. "regroup" counts the walks that end within 3 of an ally who was more than 8 away when the walk began, by destination.

| walk led to | ocean-chybase | opponent | ocean-chybase regroup | opponent regroup |
| --- | --- | --- | --- | --- |
| camp | 24.6% | 24.3% | 5.8% | 5.7% |
| hold | 2.0% | 2.3% | 0.3% | 0.3% |
| tribute | 5.3% | 3.8% | 1.2% | 1.3% |
| fight | 9.9% | 8.5% | 2.6% | 2.1% |
| recall | 4.1% | 4.2% | 0.6% | 0.6% |
| spawn | 0.0% | 0.0% | 0.0% | 0.0% |
| wait_camp | 9.1% | 9.7% | 3.2% | 3.2% |
| wait_altar | 0.7% | 1.1% | 0.2% | 0.3% |
| idle | 3.8% | 3.7% | 0.8% | 0.8% |
| dead | 0.4% | 0.2% | 0.1% | 0.1% |
| other | 1.0% | 0.9% | 0.2% | 0.3% |

## Champion roles

Per champion type, pooled over games: turn mix (alive turns), share of the team's capture gems and of its carried gem-rounds.

**ocean-chybase**

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

**opponent**

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

## Gem flow

Per game means. tributed = captured + taken by kills - lost to champions - lost to camps - carried at the end (the identity holds exactly in every game unless noted).

| gems | ocean-chybase | opponent |
| --- | --- | --- |
| cap | 879 | 979 |
| kill | 146 | 192 |
| lost_champ | 192 | 146 |
| lost_camp | 6.6 | 7.1 |
| carried_end | 128 | 149 |
| tributed | 698 | 870 |

## Cohesion and map control by phase

| phase | ocean-chybase isolated | ocean-chybase outnumbered | ocean-chybase control | opponent isolated | opponent outnumbered | opponent control |
| --- | --- | --- | --- | --- | --- | --- |
| r1-150 | 16% | 13% | 51% | 15% | 12% | 49% |
| r151-400 | 23% | 14% | 49% | 22% | 12% | 51% |
| r401-800 | 25% | 17% | 48% | 24% | 13% | 52% |
| r801+ | 26% | 20% | 47% | 25% | 14% | 53% |

isolated: field champion-rounds with no ally within 8; outnumbered: contact rounds with more enemies than allies within 8; control: share of camp value nearer by walking to that team's champions.

## Who turns up to fights

At each engagement's first round (analysis/fights.py clustering), every own champion alive and more than 8 from the fight, by what it was doing; "joined later" are those that dealt or took damage in it anyway. Distances are to the fight's first location.

| absent ally was | ocean-chybase per fight | opponent per fight |
| --- | --- | --- |
| walking >16 | 0.78 | 0.79 |
| walking <=16 | 0.56 | 0.56 |
| dead | 0.64 | 0.41 |
| camp >16 | 0.23 | 0.24 |
| camp <=16 | 0.19 | 0.20 |
| channel >16 | 0.07 | 0.06 |
| channel <=16 | 0.05 | 0.06 |
| hold >16 | 0.05 | 0.05 |
| joined later | 0.04 | 0.04 |
| hold <=16 | 0.03 | 0.04 |
| waiting >16 | 0.03 | 0.03 |
| waiting <=16 | 0.02 | 0.03 |
| idle >16 | 0.02 | 0.02 |
| idle <=16 | 0.02 | 0.01 |
| spawn >16 | 0.01 | 0.01 |
| another fight >16 | 0.01 | 0.01 |
| spawn <=16 | 0.01 | 0.01 |
| another fight <=16 | 0.01 | 0.01 |
| other <=16 | 0.00 | 0.00 |
| other >16 | 0.00 | 0.00 |

Net swing (gems from kills - own bags lost + gold/4) by champions present at the start, own minus enemy:

| numbers | ocean-chybase fights | ocean-chybase mean swing | opponent fights | opponent mean swing |
| --- | --- | --- | --- | --- |
| -2 or fewer | 1291 | -13.6 | 919 | -1.4 |
| -1 | 1450 | -5.0 | 1219 | -1.8 |
| +0 | 1834 | -9.3 | 1834 | 9.3 |
| +1 | 1219 | 1.8 | 1450 | 5.0 |
| +2 or more | 919 | 1.4 | 1291 | 13.6 |

## Camp contests

A camp cycle (from respawn to capture) is contested when both teams hit its monsters or held its tiles, or a hold was reset as contested. Steals: captured by the team that did not land the clearing blow.

| per game | ocean-chybase | opponent |
| --- | --- | --- |
| won | 3.44 | 3.71 |
| lost | 3.71 | 3.44 |
| won_gems | 81.62 | 97.65 |
| lost_gems | 97.65 | 81.62 |
| steals | 0.92 | 0.96 |
| stolen | 0.96 | 0.92 |
| captured gems, own half | 697 | 745 |
| captured gems, mid half | 89.7 | 124 |
| captured gems, enemy half | 93.2 | 110 |

| group | ocean-chybase won | ocean-chybase lost | ocean-chybase share |
| --- | --- | --- | --- |
| $$ | 52 | 43 | 55% |
| GGW | 37 | 49 | 43% |
| $$WW | 36 | 42 | 46% |
| GGGGG | 31 | 41 | 43% |
| $W | 31 | 39 | 44% |
| GW | 37 | 29 | 56% |
| $$W | 37 | 25 | 60% |
| GG | 37 | 21 | 64% |
| $EG | 24 | 29 | 45% |
| GGGG | 27 | 23 | 54% |
| W | 27 | 17 | 61% |
| $$$ | 18 | 22 | 45% |
| GWW | 25 | 14 | 64% |
| $$$E | 16 | 22 | 42% |
| GGGGGG | 15 | 23 | 39% |

(81 more rows in `macro-contest_types.csv`)

## Which camps get taken

Captures per group type against capacity: the cycles each type could give at most (game rounds / (respawn + 6 capture rounds), summed over the map's groups of that type, both halves). Low shares on strong groups are camps nobody farms.

| group | capacity a game | ocean-chybase captures | opponent captures | ocean-chybase share | opponent share | taken (both) | ocean-chybase gems | opponent gems |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| $W | 24.8 | 2.4 | 2.7 | 10% | 11% | 21% | 9.8 | 11.0 |
| $$ | 22.4 | 3.9 | 3.8 | 17% | 17% | 34% | 0.0 | 0.0 |
| GW | 18.6 | 3.4 | 3.9 | 18% | 21% | 39% | 39.8 | 44.7 |
| $$W | 14.3 | 2.2 | 2.1 | 15% | 15% | 30% | 8.7 | 8.4 |
| G | 11.5 | 3.0 | 3.3 | 26% | 28% | 55% | 21.9 | 23.8 |
| $$WW | 10.7 | 1.2 | 1.5 | 12% | 14% | 26% | 9.9 | 12.0 |
| GGW | 10.1 | 2.2 | 2.3 | 22% | 23% | 45% | 43.6 | 45.5 |
| $ | 8.9 | 1.1 | 1.0 | 12% | 11% | 24% | 0.0 | 0.0 |
| GG | 7.9 | 2.5 | 2.7 | 32% | 34% | 66% | 37.3 | 40.8 |
| W | 7.7 | 0.6 | 0.6 | 8% | 8% | 15% | 2.4 | 2.3 |
| $GWW | 7.1 | 1.1 | 1.1 | 16% | 16% | 32% | 17.7 | 17.4 |
| $WW | 6.8 | 0.9 | 1.0 | 13% | 15% | 28% | 6.9 | 8.3 |
| $EG | 6.4 | 1.3 | 1.4 | 20% | 22% | 42% | 29.1 | 32.6 |
| $$$W | 5.4 | 0.9 | 0.9 | 16% | 16% | 32% | 3.5 | 3.5 |
| EGG | 5.1 | 1.0 | 1.0 | 20% | 20% | 40% | 32.3 | 32.6 |
| GGGG | 4.6 | 1.5 | 1.5 | 32% | 32% | 64% | 45.0 | 44.1 |
| $GW | 4.1 | 0.9 | 1.0 | 23% | 25% | 48% | 10.8 | 11.8 |
| $$EE | 3.9 | 0.6 | 0.6 | 16% | 15% | 31% | 18.1 | 17.9 |
| GGWW | 3.7 | 0.6 | 0.7 | 16% | 19% | 35% | 14.0 | 17.2 |
| $$$ | 3.7 | 0.8 | 1.0 | 21% | 26% | 47% | 0.0 | 0.0 |

(124 more rows in `macro-capacity.csv`)

## Why games are lost: ocean-chybase's losses

The break round is the last round the loser had at least the winner's wealth (tributed + carried gems); 0 means it was never level after round 1. The window is the 100 rounds after it. Its cause is the largest of: farm (capture gems, winner - loser), fight (kill gems taken minus bags lost to champions, winner - loser), camp (bags lost to camps, loser - winner); "bank" when the loser lost while holding at least as much wealth (gems carried, not tributed). Whole-game components are over all rounds.

| cause of the break window | games | share | median break | loser dead | winner dead | loser work | winner work | loser walk | winner walk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| farm | 107 | 72% | 183 | 12% | 2% | 23% | 29% | 53% | 56% |
| fight | 37 | 25% | 479 | 30% | 5% | 13% | 24% | 48% | 53% |
| camp | 0 | 0% | - | - | - | - | - | - | - |
| bank | 4 | 3% | 886 | - | - | - | - | - | - |

Turn shares are over the windows of that cause (work = camp, hold, tribute). A farm window with a high loser dead share is a farm deficit that follows deaths; one with level dead shares is out-farming with bodies alive.

Break round: median 252 (p25 123, p75 462); 0 never level, 52 in rounds 1-150, 46 in 151-400, 50 after 400.

| component (winner advantage, gems) | whole game | break window |
| --- | --- | --- |
| farm | 268 | 79.9 |
| fight | 334 | 149 |
| camp | 0.5 | 0.4 |
| bank | 37.8 | - |

Turn mix in the break windows (loser vs winner):

| class | loser | winner |
| --- | --- | --- |
| dead | 16.7% | 2.5% |
| lost | 0.1% | 0.2% |
| fight | 2.9% | 3.0% |
| tribute | 0.9% | 2.6% |
| recall | 4.2% | 5.1% |
| teleport | 0.0% | 0.0% |
| camp | 17.5% | 21.7% |
| hold | 2.4% | 3.5% |
| walk_bag | 26.4% | 31.8% |
| walk | 25.2% | 23.7% |
| spawn | 1.0% | 1.1% |
| wait_camp | 1.8% | 2.6% |
| wait_altar | 0.1% | 1.4% |
| idle | 0.9% | 0.8% |

Loser deaths in the break windows: 158 over 148 games (1.07 a game), by type Prism 30, Issac 29, Cassi 27, Vesper Vale 22, Willow 14, Heart of Ruin 11, Ren 7, Vendetta 5, Ryth 5, Marcella 4, Tavi 2, Varg 2; bag at death median 11, 34 with 50+.

What opened the window: the loser's largest-bag death within 10 rounds of the break, if any:

| trigger | games | share |
| --- | --- | --- |
| no loser death within 10 rounds | 104 | 70% |
| Prism died with 200+ gems | 9 | 6% |
| Issac died with <50 gems | 8 | 5% |
| Prism died with 50-199 gems | 7 | 5% |
| ended holding the larger wealth | 4 | 3% |
| Cassi died with <50 gems | 4 | 3% |
| Prism died with <50 gems | 3 | 2% |
| Heart of Ruin died with <50 gems | 2 | 1% |
| Ren died with <50 gems | 2 | 1% |
| Vendetta died with <50 gems | 1 | 1% |
| Marcella died with 200+ gems | 1 | 1% |
| Vesper Vale died with <50 gems | 1 | 1% |

(2 more rows in `macro-triggers.csv`)

Largest windows (gap = winner minus loser wealth at the window's end):

| game / break | map | cause | gap | window components | loser deaths in the window |
| --- | --- | --- | --- | --- | --- |
| 3d83d7f9bc0e7fcf r433 | gen-ladder-331000000015 | fight | 1827 | farm +139 fight +1720 camp +0 | r453 Vesper Vale bag 84 by Prism; r453 Cassi bag 8 by Prism; r460 Ren bag 22 by Prism; r502 Willow bag 14 by Prism |
| f3e1feed964bcda0 r590 | gen-jungle-331000007001 | fight | 1337 | farm +70 fight +1282 camp +0 | r592 Issac bag 25 by Prism; r594 Vesper Vale bag 29 by Prism; r679 Prism bag 593 by Prism |
| 668d02e95b8a454e r433 | gen-huge-331000012002 | fight | 1179 | farm -4 fight +1198 camp +0 | r450 Vesper Vale bag 35 by Vesper Vale; r454 Heart of Ruin bag 32 by Prism; r478 Cassi bag 37 by Vesper Vale; r485 Prism bag 535 by Vesper Vale |
| 8829b6190be197fe r660 | gen-classic-331000001026 | fight | 1175 | farm +36 fight +1564 camp +0 | r661 Prism bag 707 by Prism; r668 Cassi bag 11 by Prism; r710 Heart of Ruin bag 45 by Prism |
| 0302a22c88b0fd37 r503 | gen-altar-poor-331000016001 | fight | 1071 | farm +13 fight +1062 camp +0 | r504 Cassi bag 65 by Heart of Ruin; r512 Prism bag 353 by Prism; r540 Heart of Ruin bag 32 by Prism; r575 Vesper Vale bag 66 by Prism |
| 34d9a8e31c025382 r914 | gen-ladder-331000000067 | fight | 1052 | farm +319 fight +990 camp +0 | r970 Prism bag 495 by Prism; r980 Issac bag 0 by Prism; r1000 Willow bag 0 by Prism |
| 409667189052fa9c r541 | gen-classic-331000001028 | fight | 1004 | farm +14 fight +1002 camp +0 | r552 Cassi bag 0 by Prism; r567 Prism bag 392 by Prism; r597 Marcella bag 109 by Prism; r597 Willow bag 0 by Prism |
| 08383228b8a7836e r978 | gen-classic-331000001019 | fight | 977 | farm -15 fight +994 camp +0 | r979 Prism bag 497 by Prism |
| 9babbe90d8eae8b8 r511 | gen-classic-331000001009 | fight | 879 | farm +57 fight +924 camp +0 | r512 Prism bag 462 by Prism |
| 054c002144d1fa1d r1279 | gen-jungle-331000007000 | fight | 780 | farm -14 fight +1970 camp +0 | r1280 Marcella bag 950 by Prism; r1321 Prism bag 35 by Prism |
| 37f390012887317e r435 | gen-ladder-331000000021 | fight | 697 | farm +200 fight +694 camp +0 | r436 Prism bag 250 by Prism; r443 Vesper Vale bag 97 by Prism |
| 98692bb109fde7ae r253 | gen-ladder-331000000024 | fight | 621 | farm +177 fight +454 camp +0 | r292 Prism bag 101 by Prism; r293 Cassi bag 0 by Prism; r339 Ryth bag 63 by Prism |
| 946de16d7ecbf661 r474 | gen-contested-centre-331000010000 | fight | 545 | farm +206 fight +358 camp +0 | r478 Prism bag 179 by Heart of Ruin |
| 9e16da8a6089ae60 r558 | gen-classic-331000001028 | fight | 533 | farm -65 fight +858 camp +0 | r559 Prism bag 186 by Prism; r581 Issac bag 25 by Prism; r591 Marcella bag 109 by Prism |
| 5feb6cde081668c4 r176 | gen-ladder-331000000024 | farm | 520 | farm +312 fight +212 camp +0 | r177 Prism bag 60 by Issac; r188 Vesper Vale bag 28 by Ryth; r190 Ryth bag 4 by Prism; r192 Issac bag 7 by Cassi |
| e132010ccdc90093 r826 | gen-ladder-331000000012 | fight | 519 | farm +1 fight +700 camp +0 | r827 Prism bag 350 by Prism |
| 2823b6e0a36021e0 r607 | gen-ladder-331000000042 | fight | 497 | farm -27 fight +1836 camp +0 | r608 Prism bag 918 by Prism; r615 Issac bag 0 by Prism; r624 Vesper Vale bag 0 by Vesper Vale |
| d700a65d704e700e r603 | gen-ladder-331000000067 | farm | 443 | farm +494 fight +0 camp +0 | - |
| e41fa249c71d8f56 r316 | gen-classic-331000001009 | fight | 414 | farm +61 fight +380 camp +0 | r348 Heart of Ruin bag 190 by Prism |
| 355fa449489b5a43 r148 | gen-huge-331000012001 | fight | 362 | farm +52 fight +454 camp +0 | r149 Prism bag 227 by Cassi |
| 0eb32fdc0663e917 r334 | gen-classic-331000001022 | fight | 345 | farm +139 fight +230 camp +0 | r337 Heart of Ruin bag 45 by Heart of Ruin; r380 Issac bag 28 by Issac; r388 Prism bag 0 by Prism |
| d0b90ec061c1d023 r569 | gen-ladder-331000000005 | fight | 264 | farm +88 fight +186 camp +0 | r575 Varg bag 0 by Vesper Vale; r583 Cassi bag 18 by Vesper Vale; r585 Vendetta bag 0 by Vesper Vale; r642 Vesper Vale bag 55 by Vesper Vale |
| c5ff627e0c57b81d r288 | gen-ladder-331000000038 | fight | 262 | farm +113 fight +158 camp +0 | r299 Prism bag 79 by Prism |
| bc06dbfbe44a1ec3 r485 | gen-huge-331000012000 | farm | 260 | farm +272 fight +0 camp +0 | - |
| f6e66a8cf4de51ea r123 | gen-ladder-331000000043 | farm | 257 | farm +177 fight +94 camp +0 | r135 Willow bag 0 by Prism; r153 Prism bag 43 by Prism; r169 Issac bag 0 by Prism |
