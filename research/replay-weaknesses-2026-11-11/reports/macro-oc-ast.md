# Macro: turns, gems, cohesion, control, losses

Set: replays/batch-20261111-190708-ab-oc-vs-ast-40k-ladder (128 games, 64 clusters, focus ocean). Sides: ocean vs opponent in the same game (128 pairs). Paired by game: the focus team against its opponent.

Every number is read from the replay alone (no bot traces). Turn classes are per champion-round, first match wins: dead, lost (stunned/out of fuel/error), fight (dealt or took champion damage), tribute/recall/teleport channel, camp (hit a camp), walk_bag/walk (moved, carrying gems or not), hold (still on a claimable group tile), spawn (still on own spawn), idle. Distances are Chebyshev unless noted; camp control uses walking distance. Differences are mean ocean minus opponent with a 95% cluster-bootstrap CI over map pairs or ladder groups.

## Macro metrics, paired

| metric | ocean | opponent | ocean - opponent [95% CI] | ocean higher | games | definition |
| --- | --- | --- | --- | --- | --- | --- |
| mt_walk | 57.8% | 59.7% | -1.9pt [-3.1pt .. -0.9pt] | 34% | 128 | alive turns walking (with or without gems) |
| mt_walk_bag | 26.7% | 22.8% | +3.9pt [+2.4pt .. +5.8pt] | 67% | 128 | alive turns walking while carrying gems |
| mt_work | 26.5% | 24.9% | +1.6pt [+0.6pt .. +2.8pt] | 63% | 128 | alive turns at work: hitting camps, holding captures, tributing |
| mt_fight | 5.3% | 5.5% | -0.2pt [-0.5pt .. +0.2pt] | 41% | 128 | alive turns in fights (dealt or took champion damage) |
| mt_wait | 2.9% | 2.3% | +0.6pt [+0.3pt .. +1.0pt] | 67% | 128 | alive turns waiting still by a respawning or live camp, or by an altar, without hitting or holding |
| mt_idle | 1.3% | 1.0% | +0.3pt [+0.1pt .. +0.6pt] | 68% | 128 | alive turns idle elsewhere off spawn |
| mt_spawn | 1.2% | 1.4% | -0.2pt [-0.3pt .. -0.1pt] | 26% | 128 | alive turns standing on own spawn |
| mt_recall | 4.7% | 5.0% | -0.3pt [-0.6pt .. +0.0pt] | 42% | 128 | alive turns channelling recalls |
| mt_dead | 7.9% | 13.1% | -5.2pt [-8.0pt .. -2.7pt] | 30% | 128 | champion turns dead |
| regroup_share | 13.2% | 12.3% | +0.9pt [+0.0pt .. +1.7pt] | 59% | 128 | alive turns on walks that end next to an ally who was 9+ away at the start (walking to allies) |
| walk_waste | 28.3% | 27.1% | +1.2pt [-0.6pt .. +3.1pt] | 60% | 128 | walked steps beyond the straight (Chebyshev) line of each walk leg / steps |
| walk_per_gem | 3.0 | 9.3 | -6.3 [-14.8 .. -1.5] | 29% | 126 | walk turns per gem earned (captures and kills) |
| earned_per100 | 129 | 99.8 | 28.8 [15.0 .. 43.4] | 73% | 128 | gems earned (capture shares + kill bags) per 100 rounds |
| conversion | 82.2% | 69.6% | +12.6pt [+4.7pt .. +21.4pt] | 67% | 126 | tributed / earned gems |
| gem_latency | 78.9 | 63.8 | 15.2 [-1.6 .. 31.0] | 69% | 119 | mean rounds a tributed gem was carried (gem-weighted) |
| gem_exposed | 37.3% | 36.1% | +1.1pt [-1.8pt .. +3.8pt] | 58% | 126 | carried gem-rounds in sight of an enemy / carried gem-rounds |
| carry_top | 57.9% | 66.7% | -8.8pt [-14.0pt .. -3.0pt] | 35% | 126 | share of the team's carried gem-rounds on its top carrier |
| nn_dist | 5.5 | 5.9 | -0.3 [-0.5 .. -0.1] | 37% | 128 | distance to the nearest living ally (alive, off spawn; mean) |
| isolated | 21.0% | 23.6% | -2.6pt [-3.9pt .. -1.3pt] | 37% | 128 | alive champion-rounds off spawn with no ally within 8 |
| outnumbered | 12.8% | 17.9% | -5.2pt [-8.1pt .. -2.0pt] | 35% | 128 | contact champion-rounds (an enemy within 8) with more enemies than allies within 8 |
| outnumbering | 61.6% | 53.0% | +8.5pt [+4.0pt .. +13.2pt] | 64% | 128 | contact champion-rounds with more allies than enemies within 8 |
| control | 52.1% | 47.9% | +4.3pt [+0.8pt .. +7.8pt] | 59% | 128 | camp value nearer (walking) to our champions than theirs, gems + gold/4 per respawn, sampled |
| control_own | 77.9% | 75.2% | +2.7pt [-0.2pt .. +5.7pt] | 61% | 124 | own-half camp value under our control |
| enemy_half | 12.3% | 10.2% | +2.1pt [+0.3pt .. +3.9pt] | 57% | 128 | alive champion-rounds on the enemy half |
| own_lost | 16.0% | 25.9% | -10.0pt [-17.0pt .. -3.4pt] | 27% | 118 | gems of own-half captures taken by the enemy / own-half captured gems |
| contest_win | 59.2% | 40.8% | +18.3pt [+9.1pt .. +29.0pt] | 62% | 125 | contested camp cycles (both teams hit, held or contested) we captured |
| fight_turnout | 52.6% | 52.6% | -0.0pt [-2.1pt .. +2.1pt] | 54% | 126 | own alive champions within 8 of a fight at its start / own alive champions |
| fight_outnum | 30.4% | 38.4% | -7.9pt [-13.1pt .. -2.6pt] | 36% | 126 | fights started with fewer own champions present |
| lonely_death | 29.3% | 31.6% | -2.2pt [-9.8pt .. +4.7pt] | 38% | 98 | deaths to champions with no living ally within 8 |

## ocean in its wins and losses

93 wins, 35 losses. Opponent columns are the same games from the other side.

| metric | ocean won | ocean lost | opponent when ocean won | opponent when ocean lost |
| --- | --- | --- | --- | --- |
| mt_walk | 57.5% | 58.4% | 61.5% | 54.9% |
| mt_walk_bag | 26.6% | 26.9% | 22.0% | 24.7% |
| mt_work | 26.9% | 25.5% | 23.2% | 29.3% |
| mt_fight | 4.7% | 6.9% | 5.3% | 5.8% |
| mt_wait | 3.3% | 1.9% | 2.3% | 2.4% |
| mt_idle | 1.3% | 1.4% | 1.0% | 0.8% |
| mt_spawn | 1.2% | 1.3% | 1.4% | 1.3% |
| mt_recall | 4.9% | 4.3% | 5.0% | 5.2% |
| mt_dead | 5.0% | 15.6% | 15.6% | 6.3% |
| regroup_share | 13.9% | 11.2% | 13.1% | 10.3% |
| walk_waste | 26.3% | 33.6% | 27.8% | 25.1% |
| walk_per_gem | 2.4 | 4.5 | 12.1 | 2.0 |
| earned_per100 | 145 | 84.7 | 79.4 | 154 |
| conversion | 92.4% | 56.1% | 60.1% | 94.3% |
| gem_latency | 93.4 | 51.3 | 45.2 | 107 |
| gem_exposed | 37.0% | 39.6% | 34.4% | 40.6% |
| carry_top | 58.8% | 54.3% | 63.3% | 75.3% |
| nn_dist | 5.8 | 4.9 | 6.1 | 5.4 |
| isolated | 22.1% | 17.9% | 24.9% | 20.2% |
| outnumbered | 12.6% | 13.4% | 18.3% | 17.0% |
| outnumbering | 62.4% | 59.2% | 52.4% | 54.8% |
| control | 55.3% | 43.8% | 44.7% | 56.2% |
| control_own | 82.6% | 65.9% | 74.3% | 77.5% |
| enemy_half | 10.8% | 16.1% | 6.4% | 20.3% |
| own_lost | 7.2% | 36.8% | 29.6% | 17.4% |
| contest_win | 68.3% | 35.5% | 31.7% | 64.5% |
| fight_turnout | 50.4% | 58.5% | 52.6% | 52.6% |
| fight_outnum | 30.1% | 31.3% | 38.7% | 37.5% |
| lonely_death | 33.6% | 18.8% | 33.4% | 32.6% |

## Rounds 1-150, paired

The same quantities over the first 150 rounds only (most break rounds come later), with ocean's win rate in the games where its value was higher or lower than opponent's.

| r1-150 | ocean | opponent | ocean - opponent [95% CI] | ocean win rate when higher | ocean win rate when lower |
| --- | --- | --- | --- | --- | --- |
| walk | 55.3% | 56.2% | -1.0pt [-2.0pt .. +0.1pt] | 67% (n=55) | 77% (n=73) |
| work | 30.6% | 29.7% | +0.9pt [-0.2pt .. +2.0pt] | 76% (n=75) | 67% (n=52) |
| wait | 1.7% | 1.6% | +0.1pt [-0.3pt .. +0.5pt] | 77% (n=60) | 69% (n=59) |
| dead | 4.3% | 5.9% | -1.6pt [-3.6pt .. +0.3pt] | 55% (n=31) | 85% (n=48) |
| isolated | 16.6% | 17.1% | -0.5pt [-2.0pt .. +1.0pt] | 78% (n=58) | 69% (n=70) |
| outnumbered | 14.1% | 17.6% | -3.4pt [-8.3pt .. +1.4pt] | 71% (n=56) | 75% (n=60) |
| control | 48.5% | 51.5% | -3.1pt [-6.4pt .. +0.3pt] | 82% (n=57) | 65% (n=71) |

## By map family

Maps by family (the name without its trailing seed and `gen-` prefix); ocean minus opponent per game, mean. Win rate is the focus team's.

| family | games | ocean won | d mt_walk | d mt_work | d mt_dead | d control | d outnumbered | d own_lost | d contest_win | ocean losses: top cause |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ambush | 2 | 100% | -3.6pt | +2.9pt | +0.1pt | -1.2pt | -4.8pt | -6.0pt | +26.7pt | - |
| anvil | 2 | 100% | -6.7pt | +2.2pt | -12.3pt | +11.1pt | +17.4pt | -27.3pt | +53.4pt | - |
| breadcrumbs | 2 | 0% | +5.7pt | -5.6pt | +14.7pt | -11.8pt | +8.8pt | +26.9pt | -2.1pt | farm 1/2 |
| collision | 2 | 50% | +2.8pt | -2.8pt | -4.1pt | -6.6pt | -14.6pt | +1.4pt | -11.4pt | fight 1/1 |
| contest | 2 | 100% | -11.5pt | +9.4pt | -14.9pt | +12.1pt | -8.4pt | -83.3pt | +46.5pt | - |
| corners | 2 | 50% | -1.1pt | +0.9pt | +3.2pt | -6.5pt | -10.4pt | -7.1pt | -1.3pt | farm 1/1 |
| crater | 2 | 100% | -6.4pt | +8.1pt | -18.8pt | +20.9pt | -14.9pt | -49.7pt | +84.2pt | - |
| dunes | 2 | 100% | -7.8pt | +7.5pt | -13.9pt | +24.5pt | -15.2pt | -51.2pt | +70.0pt | - |
| eight | 2 | 100% | -1.9pt | +3.0pt | -10.4pt | +5.4pt | -3.9pt | -2.4pt | -5.6pt | - |
| elkring | 2 | 100% | +1.6pt | -2.3pt | -4.8pt | +2.0pt | +5.9pt | -5.1pt | +43.3pt | - |
| expanse | 2 | 50% | -1.0pt | +1.8pt | +0.0pt | -2.2pt | +37.6pt | -0.4pt | -33.3pt | farm 1/1 |
| fragment | 2 | 100% | -10.0pt | +6.8pt | -30.3pt | +34.9pt | +4.7pt | -75.0pt | +72.9pt | - |
| galaxy | 2 | 50% | +1.8pt | -1.7pt | -1.7pt | -8.1pt | -6.5pt | +15.5pt | -7.5pt | fight 1/1 |
| gem-fields | 2 | 0% | +2.8pt | -4.6pt | +19.5pt | -17.5pt | +10.8pt | +19.4pt | -11.1pt | farm 1/2 |
| gemfight | 2 | 50% | -2.1pt | +1.5pt | -6.2pt | +2.6pt | -29.2pt | -18.3pt | +17.1pt | fight 1/1 |
| great-wall | 2 | 50% | +0.9pt | -1.1pt | -0.0pt | -3.3pt | -12.3pt | -5.2pt | -25.0pt | fight 1/1 |
| happy-halloween | 2 | 50% | +1.0pt | -1.4pt | +5.0pt | -7.3pt | -1.0pt | -4.2pt | +37.5pt | bank 1/1 |
| interlock | 2 | 100% | -3.0pt | +2.2pt | -18.4pt | +10.7pt | -16.8pt | -38.7pt | +35.0pt | - |
| lanes | 2 | 100% | -2.8pt | +3.5pt | -6.7pt | +7.6pt | -2.7pt | -12.7pt | +38.0pt | - |
| lost-world | 2 | 50% | +3.7pt | -0.6pt | -6.2pt | +1.3pt | -3.2pt | -8.3pt | +3.3pt | farm 1/1 |
| monolith | 2 | 100% | -1.6pt | +1.6pt | -6.7pt | +5.1pt | -3.7pt | -2.1pt | -20.0pt | - |
| oasis | 2 | 100% | -11.2pt | +13.4pt | -17.1pt | +30.3pt | -23.4pt | -54.4pt | +50.0pt | - |
| packs | 2 | 0% | +4.0pt | -0.3pt | +5.9pt | -11.6pt | -17.9pt | +43.6pt | -36.4pt | farm 2/2 |
| pilgrimage | 2 | 100% | -3.2pt | +2.9pt | -4.5pt | +15.7pt | -8.6pt | +0.0pt | +71.4pt | - |
| quadrants | 2 | 100% | +2.9pt | -2.1pt | -11.6pt | +1.4pt | -8.2pt | -2.3pt | +50.0pt | - |

(39 more rows in `macro-families.csv`)

## Where the turns go

Share of all champion-rounds (dead included), whole game and per phase.

| class | ocean | opponent | ocean r1-150 | ocean r151-400 | ocean r401-800 | ocean r801+ | opponent r1-150 | opponent r151-400 | opponent r401-800 | opponent r801+ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dead | 7.7% | 13.0% | 4.3% | 6.7% | 8.6% | 10.9% | 5.9% | 10.9% | 15.2% | 19.0% |
| lost | 0.3% | 0.2% | 0.3% | 0.2% | 0.2% | 0.4% | 0.3% | 0.2% | 0.2% | 0.3% |
| fight | 4.7% | 4.6% | 4.5% | 4.6% | 4.4% | 6.1% | 4.3% | 4.5% | 4.4% | 5.8% |
| tribute | 1.5% | 1.1% | 0.4% | 1.1% | 1.9% | 2.7% | 0.4% | 0.8% | 1.5% | 1.5% |
| recall | 4.4% | 4.3% | 4.3% | 5.1% | 4.2% | 3.3% | 4.5% | 5.2% | 4.1% | 3.3% |
| teleport | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| camp | 18.1% | 15.8% | 24.3% | 19.3% | 16.9% | 12.4% | 22.9% | 17.6% | 13.9% | 9.5% |
| hold | 3.9% | 3.8% | 4.3% | 4.6% | 3.9% | 2.7% | 4.4% | 4.5% | 3.7% | 2.1% |
| walk_bag | 24.3% | 19.2% | 15.6% | 27.3% | 27.5% | 20.6% | 14.4% | 22.1% | 20.6% | 15.9% |
| walk | 30.1% | 33.9% | 38.0% | 26.8% | 27.2% | 34.6% | 39.1% | 30.4% | 32.3% | 38.4% |
| spawn | 1.1% | 1.2% | 1.1% | 1.1% | 1.0% | 0.9% | 1.2% | 1.2% | 1.1% | 1.0% |
| wait_camp | 2.4% | 1.8% | 1.5% | 2.3% | 2.7% | 3.1% | 1.5% | 1.8% | 2.0% | 1.8% |
| wait_altar | 0.1% | 0.1% | 0.0% | 0.1% | 0.1% | 0.5% | 0.0% | 0.1% | 0.1% | 0.1% |
| idle | 1.3% | 0.9% | 1.3% | 0.9% | 1.3% | 1.8% | 1.0% | 0.9% | 0.8% | 1.2% |

## What the walking was for

Walk turns by what the walk led to (the class of the first turn after the leg), as a share of alive turns. "regroup" counts the walks that end within 3 of an ally who was more than 8 away when the walk began, by destination.

| walk led to | ocean | opponent | ocean regroup | opponent regroup |
| --- | --- | --- | --- | --- |
| camp | 24.9% | 24.4% | 6.2% | 5.3% |
| hold | 2.4% | 2.3% | 0.3% | 0.3% |
| tribute | 4.3% | 4.1% | 0.9% | 0.7% |
| fight | 11.0% | 13.9% | 2.5% | 3.6% |
| recall | 3.6% | 4.1% | 0.5% | 0.5% |
| spawn | 0.0% | 0.0% | 0.0% | 0.0% |
| wait_camp | 8.3% | 8.2% | 2.7% | 2.3% |
| wait_altar | 0.3% | 0.3% | 0.1% | 0.0% |
| idle | 3.0% | 2.5% | 0.7% | 0.3% |
| dead | 0.3% | 0.4% | 0.1% | 0.1% |
| other | 0.7% | 0.7% | 0.1% | 0.2% |

## Champion roles

Per champion type, pooled over games: turn mix (alive turns), share of the team's capture gems and of its carried gem-rounds.

**ocean**

| type | rounds | walk | walk_bag | camp | hold | fight | recall | wait | idle | dead | capture gems | gem-rounds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Cassi | 101540 | 36% | 25% | 22% | 4% | 4% | 4% | 2% | 2% | 12% | 7% | 5% |
| Issac | 101540 | 34% | 23% | 22% | 5% | 4% | 5% | 4% | 1% | 12% | 9% | 5% |
| Vesper Vale | 81150 | 24% | 28% | 21% | 5% | 7% | 6% | 3% | 1% | 3% | 27% | 15% |
| Prism | 67193 | 12% | 46% | 18% | 7% | 5% | 5% | 3% | 1% | 6% | 20% | 57% |
| Willow | 67130 | 62% | 11% | 16% | 1% | 2% | 2% | 3% | 2% | 4% | 2% | 1% |
| Heart of Ruin | 36013 | 27% | 30% | 19% | 3% | 10% | 4% | 2% | 2% | 8% | 5% | 3% |
| Vendetta | 32192 | 26% | 30% | 20% | 4% | 5% | 6% | 3% | 2% | 7% | 7% | 3% |
| Ryth | 30112 | 34% | 23% | 17% | 5% | 9% | 6% | 2% | 1% | 5% | 6% | 3% |
| Ren | 27387 | 26% | 31% | 20% | 3% | 8% | 6% | 2% | 2% | 12% | 4% | 2% |
| Marcella | 18247 | 44% | 21% | 9% | 6% | 8% | 5% | 3% | 0% | 5% | 4% | 1% |
| Varg | 17947 | 33% | 25% | 21% | 5% | 2% | 6% | 2% | 1% | 4% | 5% | 1% |
| Tavi | 16794 | 34% | 21% | 22% | 5% | 6% | 4% | 3% | 1% | 7% | 3% | 2% |
| Stellar | 3144 | 20% | 31% | 22% | 5% | 6% | 4% | 6% | 1% | 9% | 1% | 2% |

**opponent**

| type | rounds | walk | walk_bag | camp | hold | fight | recall | wait | idle | dead | capture gems | gem-rounds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Cassi | 106074 | 49% | 17% | 19% | 3% | 4% | 4% | 2% | 2% | 19% | 7% | 3% |
| Issac | 106074 | 46% | 14% | 21% | 4% | 4% | 6% | 3% | 1% | 19% | 9% | 2% |
| Prism | 79001 | 14% | 43% | 20% | 7% | 5% | 5% | 2% | 1% | 9% | 26% | 69% |
| Vesper Vale | 61415 | 32% | 25% | 17% | 5% | 7% | 6% | 3% | 1% | 8% | 16% | 12% |
| Marcella | 55196 | 43% | 23% | 13% | 4% | 8% | 5% | 2% | 0% | 10% | 11% | 4% |
| Heart of Ruin | 52133 | 41% | 17% | 17% | 4% | 10% | 5% | 2% | 1% | 12% | 7% | 3% |
| Vendetta | 35355 | 41% | 22% | 18% | 3% | 3% | 6% | 2% | 1% | 6% | 9% | 2% |
| Ryth | 32520 | 41% | 19% | 15% | 7% | 8% | 5% | 2% | 0% | 11% | 5% | 1% |
| Willow | 31389 | 48% | 18% | 21% | 3% | 2% | 3% | 2% | 2% | 15% | 2% | 1% |
| Ren | 21736 | 38% | 23% | 15% | 3% | 9% | 5% | 2% | 2% | 13% | 3% | 1% |
| Varg | 15841 | 43% | 24% | 19% | 2% | 1% | 6% | 2% | 0% | 5% | 4% | 1% |
| Stellar | 4264 | 34% | 13% | 24% | 12% | 3% | 6% | 3% | 0% | 0% | 2% | 0% |
| Tavi | 3925 | 47% | 14% | 16% | 2% | 7% | 7% | 3% | 1% | 11% | 0% | 0% |

## Gem flow

Per game means. tributed = captured + taken by kills - lost to champions - lost to camps - carried at the end (the identity holds exactly in every game unless noted).

| gems | ocean | opponent |
| --- | --- | --- |
| cap | 908 | 695 |
| kill | 150 | 100.0 |
| lost_champ | 100.0 | 150 |
| lost_camp | 2.1 | 2.3 |
| carried_end | 73.6 | 77.2 |
| tributed | 882 | 566 |

## Cohesion and map control by phase

| phase | ocean isolated | ocean outnumbered | ocean control | opponent isolated | opponent outnumbered | opponent control |
| --- | --- | --- | --- | --- | --- | --- |
| r1-150 | 17% | 13% | 48% | 18% | 18% | 52% |
| r151-400 | 22% | 12% | 51% | 25% | 19% | 49% |
| r401-800 | 24% | 13% | 53% | 28% | 18% | 47% |
| r801+ | 25% | 15% | 56% | 28% | 17% | 44% |

isolated: field champion-rounds with no ally within 8; outnumbered: contact rounds with more enemies than allies within 8; control: share of camp value nearer by walking to that team's champions.

## Who turns up to fights

At each engagement's first round (analysis/fights.py clustering), every own champion alive and more than 8 from the fight, by what it was doing; "joined later" are those that dealt or took damage in it anyway. Distances are to the fight's first location.

| absent ally was | ocean per fight | opponent per fight |
| --- | --- | --- |
| walking >16 | 0.70 | 0.69 |
| walking <=16 | 0.62 | 0.59 |
| dead | 0.41 | 0.64 |
| camp >16 | 0.20 | 0.20 |
| camp <=16 | 0.18 | 0.16 |
| channel <=16 | 0.07 | 0.07 |
| joined later | 0.07 | 0.07 |
| channel >16 | 0.07 | 0.07 |
| hold <=16 | 0.06 | 0.05 |
| hold >16 | 0.04 | 0.05 |
| waiting <=16 | 0.03 | 0.02 |
| waiting >16 | 0.02 | 0.02 |
| another fight <=16 | 0.02 | 0.02 |
| idle >16 | 0.02 | 0.02 |
| another fight >16 | 0.02 | 0.02 |
| spawn <=16 | 0.01 | 0.01 |
| idle <=16 | 0.01 | 0.01 |
| spawn >16 | 0.01 | 0.01 |
| other <=16 | 0.00 | 0.00 |
| other >16 | 0.00 | 0.00 |

Net swing (gems from kills - own bags lost + gold/4) by champions present at the start, own minus enemy:

| numbers | ocean fights | ocean mean swing | opponent fights | opponent mean swing |
| --- | --- | --- | --- | --- |
| -2 or fewer | 591 | 0.7 | 825 | -9.4 |
| -1 | 962 | 5.5 | 1039 | -4.8 |
| +0 | 1476 | 8.6 | 1476 | -8.6 |
| +1 | 1039 | 4.8 | 963 | -5.5 |
| +2 or more | 825 | 9.4 | 591 | -0.7 |

## Camp contests

A camp cycle (from respawn to capture) is contested when both teams hit its monsters or held its tiles, or a hold was reset as contested. Steals: captured by the team that did not land the clearing blow.

| per game | ocean | opponent |
| --- | --- | --- |
| won | 6.38 | 4.53 |
| lost | 4.53 | 6.38 |
| won_gems | 219 | 115 |
| lost_gems | 115 | 219 |
| steals | 1.73 | 1.53 |
| stolen | 1.53 | 1.73 |
| captured gems, own half | 532 | 471 |
| captured gems, mid half | 233 | 127 |
| captured gems, enemy half | 143 | 97.2 |

| group | ocean won | ocean lost | ocean share |
| --- | --- | --- | --- |
| $$ | 74 | 67 | 52% |
| G | 50 | 46 | 52% |
| $W | 46 | 28 | 62% |
| $$$$ | 37 | 18 | 67% |
| GG | 28 | 17 | 62% |
| GGG | 28 | 17 | 62% |
| EG | 21 | 21 | 50% |
| $$WW | 23 | 17 | 57% |
| $EG | 25 | 15 | 62% |
| GGW | 27 | 13 | 68% |
| $$$ | 19 | 15 | 56% |
| GGGG | 18 | 15 | 55% |
| $$$$E | 16 | 14 | 53% |
| $$W | 19 | 10 | 66% |
| EEGGGGGG | 21 | 8 | 72% |

(71 more rows in `macro-contest_types.csv`)

## Which camps get taken

Captures per group type against capacity: the cycles each type could give at most (game rounds / (respawn + 6 capture rounds), summed over the map's groups of that type, both halves). Low shares on strong groups are camps nobody farms.

| group | capacity a game | ocean captures | opponent captures | ocean share | opponent share | taken (both) | ocean gems | opponent gems |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| $$ | 43.2 | 9.3 | 9.7 | 22% | 22% | 44% | 0.0 | 0.0 |
| $W | 28.5 | 4.2 | 2.9 | 15% | 10% | 25% | 16.9 | 11.6 |
| G | 22.8 | 5.6 | 6.2 | 24% | 27% | 52% | 40.8 | 45.7 |
| $ | 21.7 | 2.3 | 2.4 | 10% | 11% | 22% | 0.0 | 0.0 |
| W | 14.1 | 1.4 | 1.4 | 10% | 10% | 20% | 5.6 | 5.5 |
| GW | 11.9 | 2.5 | 2.8 | 21% | 23% | 44% | 29.0 | 31.8 |
| GG | 7.1 | 2.4 | 1.8 | 33% | 26% | 59% | 35.7 | 28.2 |
| $$$ | 7.0 | 1.5 | 1.4 | 21% | 20% | 42% | 0.0 | 0.0 |
| $$W | 6.1 | 1.3 | 1.1 | 21% | 18% | 39% | 5.1 | 4.4 |
| $EG | 5.7 | 1.6 | 1.3 | 27% | 23% | 50% | 35.5 | 30.0 |
| EGG | 4.9 | 1.0 | 1.0 | 21% | 20% | 42% | 32.5 | 30.9 |
| $$WW | 4.9 | 0.9 | 0.8 | 17% | 17% | 34% | 6.8 | 6.6 |
| GGG | 3.9 | 1.1 | 1.2 | 29% | 30% | 59% | 27.0 | 27.3 |
| EG | 3.7 | 1.3 | 1.0 | 34% | 27% | 61% | 28.8 | 22.8 |
| EEGG | 3.5 | 0.5 | 0.5 | 14% | 14% | 28% | 23.3 | 22.9 |
| $GWW | 3.5 | 0.7 | 0.7 | 20% | 19% | 39% | 10.8 | 10.6 |
| GGW | 3.3 | 0.7 | 0.5 | 22% | 16% | 38% | 14.6 | 10.8 |
| $$E | 3.1 | 0.7 | 0.7 | 23% | 24% | 47% | 10.9 | 11.1 |
| $$EE | 3.1 | 0.6 | 0.5 | 21% | 15% | 35% | 19.0 | 13.8 |
| $WW | 3.0 | 0.3 | 0.3 | 10% | 10% | 20% | 2.4 | 2.4 |

(130 more rows in `macro-capacity.csv`)

## Why games are lost: ocean's losses

The break round is the last round the loser had at least the winner's wealth (tributed + carried gems); 0 means it was never level after round 1. The window is the 100 rounds after it. Its cause is the largest of: farm (capture gems, winner - loser), fight (kill gems taken minus bags lost to champions, winner - loser), camp (bags lost to camps, loser - winner); "bank" when the loser lost while holding at least as much wealth (gems carried, not tributed). Whole-game components are over all rounds.

| cause of the break window | games | share | median break | loser dead | winner dead | loser work | winner work | loser walk | winner walk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| farm | 20 | 57% | 130 | 11% | 5% | 25% | 33% | 53% | 48% |
| fight | 13 | 37% | 332 | 29% | 7% | 17% | 26% | 42% | 50% |
| camp | 0 | 0% | - | - | - | - | - | - | - |
| bank | 2 | 6% | 1000 | - | - | - | - | - | - |

Turn shares are over the windows of that cause (work = camp, hold, tribute). A farm window with a high loser dead share is a farm deficit that follows deaths; one with level dead shares is out-farming with bodies alive.

Break round: median 259 (p25 98, p75 492); 0 never level, 15 in rounds 1-150, 7 in 151-400, 13 after 400.

| component (winner advantage, gems) | whole game | break window |
| --- | --- | --- |
| farm | 381 | 116 |
| fight | 232 | 95.1 |
| camp | -0.8 | 0.0 |
| bank | 54.0 | - |

Turn mix in the break windows (loser vs winner):

| class | loser | winner |
| --- | --- | --- |
| dead | 17.9% | 5.5% |
| lost | 0.3% | 0.3% |
| fight | 5.4% | 5.6% |
| tribute | 0.4% | 3.1% |
| recall | 3.1% | 5.8% |
| teleport | 0.0% | 0.0% |
| camp | 15.5% | 19.5% |
| hold | 5.8% | 7.4% |
| walk_bag | 19.8% | 22.9% |
| walk | 28.7% | 26.2% |
| spawn | 0.9% | 1.4% |
| wait_camp | 1.5% | 1.7% |
| wait_altar | 0.0% | 0.2% |
| idle | 0.7% | 0.6% |

Loser deaths in the break windows: 37 over 35 games (1.06 a game), by type Prism 10, Cassi 6, Vendetta 5, Ren 5, Heart of Ruin 3, Issac 3, Ryth 2, Vesper Vale 1, Tavi 1, Stellar 1; bag at death median 8.0, 10 with 50+.

What opened the window: the loser's largest-bag death within 10 rounds of the break, if any:

| trigger | games | share |
| --- | --- | --- |
| no loser death within 10 rounds | 19 | 54% |
| Prism died with 50-199 gems | 6 | 17% |
| Cassi died with <50 gems | 3 | 9% |
| ended holding the larger wealth | 2 | 6% |
| Vendetta died with 50-199 gems | 1 | 3% |
| Vendetta died with <50 gems | 1 | 3% |
| Ren died with <50 gems | 1 | 3% |
| Prism died with 200+ gems | 1 | 3% |
| Ryth died with <50 gems | 1 | 3% |

Largest windows (gap = winner minus loser wealth at the window's end):

| game / break | map | cause | gap | window components | loser deaths in the window |
| --- | --- | --- | --- | --- | --- |
| 2808155bc4b9ba5d r137 | vault | farm | 906 | farm +783 fight +230 camp +0 | r163 Ryth bag 115 by Prism; r167 Prism bag 0 by Prism |
| 2c0e25a59099b806 r448 | split | fight | 488 | farm +8 fight +486 camp +0 | r451 Prism bag 243 by Prism; r457 Tavi bag 0 by Vesper Vale |
| 81d634b193d0b505 r870 | rows | farm | 468 | farm +475 fight +0 camp +0 | - |
| 2c71ae16710a9644 r858 | rows | farm | 459 | farm +478 fight +0 camp +0 | - |
| e1a17978aba2f30e r283 | gem-fields | farm | 434 | farm +294 fight +150 camp +0 | r292 Vendetta bag 75 by Prism; r310 Ren bag 0 by Prism; r313 Heart of Ruin bag 0 by Prism |
| 79d1a727a02a6953 r474 | gem-fields | fight | 356 | farm +134 fight +336 camp +0 | r475 Prism bag 160 by Marcella; r549 Heart of Ruin bag 8 by Prism; r551 Ren bag 7 by Prism |
| 7d47850da36491d8 r45 | stalactites | farm | 314 | farm +322 fight +0 camp +0 | r76 Stellar bag 0 by Cassi |
| f8e2dedc858e9209 r501 | gift-wrapping | fight | 262 | farm +27 fight +306 camp +0 | r502 Prism bag 153 by Ryth |
| 7cf5b11fe41fc61e r58 | lost-world | farm | 252 | farm +252 fight +0 camp +0 | r149 Cassi bag 0 by Marcella |
| 11b03c489d87bee7 r144 | road-of-riches | fight | 252 | farm +126 fight +128 camp +0 | r147 Ren bag 0 by Cassi; r154 Vesper Vale bag 0 by Issac; r155 Issac bag 7 by Cassi; r223 Vendetta bag 29 by Vendetta |
| 2cd511553194f8e5 r332 | galaxy | fight | 234 | farm +1 fight +266 camp +0 | r333 Prism bag 133 by Marcella |
| ab565e3de0abbff6 r404 | gemfight | fight | 158 | farm +84 fight +214 camp +0 | r405 Prism bag 93 by Ren; r410 Cassi bag 0 by Prism; r482 Issac bag 0 by Prism |
| 2c26c9c2713e6178 r712 | great-wall | fight | 149 | farm -87 fight +316 camp +0 | r713 Prism bag 158 by Vesper Vale |
| 1f67bc4a74a7dfe2 r123 | collision | fight | 144 | farm +60 fight +102 camp +0 | r198 Prism bag 51 by Vesper Vale |
| 55626665ecf01f7b r105 | yellow-brick-road | farm | 139 | farm +145 fight +0 camp +0 | r156 Cassi bag 0 by Cassi |
| f14b843fe317876e r613 | shortcut | farm | 136 | farm +123 fight +16 camp +0 | r626 Heart of Ruin bag 0 by Vesper Vale; r662 Ren bag 8 by Vesper Vale; r683 Vendetta bag 0 by Vesper Vale |
| 5d3a6a32336a4bfd r544 | expanse | farm | 126 | farm +142 fight +0 camp +0 | - |
| 21d63ca1685ad48d r201 | reverse-spiral | fight | 116 | farm +16 fight +186 camp +0 | r202 Issac bag 14 by Marcella; r211 Vendetta bag 22 by Vesper Vale; r281 Prism bag 22 by Vesper Vale |
| 3b4cc5da90965fd3 r34 | packs | farm | 106 | farm +106 fight +0 camp +0 | - |
| 4a7b580f0c9c39e9 r86 | breadcrumbs | fight | 105 | farm +56 fight +70 camp +0 | r87 Cassi bag 21 by Marcella |
| 91c6f667f061ccf2 r807 | harvest | farm | 97 | farm +107 fight +0 camp +0 | - |
| dc8cdf53eec009f2 r192 | reverse-spiral | fight | 95 | farm +43 fight +88 camp +0 | r193 Cassi bag 7 by Vesper Vale; r221 Ren bag 0 by Prism; r238 Vendetta bag 22 by Prism |
| 1209ecea09649572 r483 | crossing | fight | 64 | farm -42 fight +346 camp +0 | r484 Prism bag 173 by Prism |
| e5039182d3d0e6fc r122 | gold-rush | fight | 58 | farm +24 fight +44 camp +0 | r123 Cassi bag 11 by Vesper Vale |
| 39cb63fd9cff1b73 r28 | corners | farm | 55 | farm +55 fight +0 camp +0 | - |
