# Macro: turns, gems, cohesion, control, losses

Set: /tmp/claude-1000/-home-ubuntu-cambc-autumn/1f5203f4-9fa0-4339-988d-e59ceccee865/scratchpad/live-src (351 games, 71 clusters, focus v115). Sides: v115 vs opponent in the same game (351 pairs). Paired by game: the focus team against its opponent.

Every number is read from the replay alone (no bot traces). Turn classes are per champion-round, first match wins: dead, fight (dealt or took champion damage), lost (stunned), tribute/recall/teleport channel, camp (hit a camp), walk_bag/walk (moved, carrying gems or not), lost (out of fuel or bot error without moving or hitting), hold (still on a claimable group tile), spawn (still on own spawn), idle. Distances are Chebyshev unless noted; camp control uses walking distance. Differences are mean v115 minus opponent with a 95% cluster-bootstrap CI over map pairs or ladder groups.

## Macro metrics, paired

| metric | v115 | opponent | v115 - opponent [95% CI] | v115 higher | games | definition |
| --- | --- | --- | --- | --- | --- | --- |
| mt_walk | 56.9% | 58.5% | -1.6pt [-2.6pt .. -0.6pt] | 42% | 351 | alive turns walking (with or without gems) |
| mt_walk_bag | 27.4% | 22.8% | +4.6pt [+3.7pt .. +5.6pt] | 72% | 351 | alive turns walking while carrying gems |
| mt_work | 27.7% | 23.7% | +4.1pt [+3.2pt .. +5.0pt] | 67% | 351 | alive turns at work: hitting camps, holding captures, tributing |
| mt_fight | 4.4% | 4.6% | -0.2pt [-0.4pt .. -0.1pt] | 42% | 351 | alive turns in fights (dealt or took champion damage) |
| mt_wait | 3.9% | 0.5% | +3.5pt [+2.9pt .. +4.0pt] | 96% | 351 | alive turns waiting still by a respawning or live camp, or by an altar, without hitting or holding |
| mt_idle | 1.3% | 0.3% | +1.0pt [+0.9pt .. +1.1pt] | 90% | 351 | alive turns idle elsewhere off spawn |
| mt_spawn | 1.2% | 1.4% | -0.3pt [-1.0pt .. +0.2pt] | 68% | 351 | alive turns standing on own spawn |
| mt_recall | 4.5% | 6.4% | -1.9pt [-3.0pt .. -0.9pt] | 32% | 351 | alive turns channelling recalls |
| mt_dead | 8.3% | 11.3% | -3.0pt [-4.5pt .. -1.8pt] | 40% | 351 | champion turns dead |
| regroup_share | 12.1% | 12.7% | -0.6pt [-1.3pt .. +0.1pt] | 47% | 351 | alive turns on walks that end next to an ally who was 9+ away at the start (walking to allies) |
| walk_waste | 28.6% | 26.8% | +1.7pt [+0.5pt .. +2.9pt] | 58% | 351 | walked steps beyond the straight (Chebyshev) line of each walk leg / steps |
| walk_per_gem | 4.1 | 6.2 | -2.1 [-5.1 .. 0.4] | 35% | 350 | walk turns per gem earned (captures and kills) |
| earned_per100 | 134 | 109 | 25.6 [17.3 .. 32.6] | 66% | 351 | gems earned (capture shares + kill bags) per 100 rounds |
| conversion | 82.1% | 73.0% | +9.1pt [+5.2pt .. +12.9pt] | 61% | 350 | tributed / earned gems |
| gem_latency | 99.5 | 66.9 | 32.6 [23.3 .. 44.1] | 59% | 336 | mean rounds a tributed gem was carried (gem-weighted) |
| gem_exposed | 37.1% | 35.9% | +1.3pt [-0.4pt .. +2.8pt] | 52% | 349 | carried gem-rounds in sight of an enemy / carried gem-rounds |
| carry_top | 63.1% | 51.3% | +11.8pt [+9.0pt .. +14.8pt] | 69% | 349 | share of the team's carried gem-rounds on its top carrier |
| nn_dist | 5.7 | 4.9 | 0.8 [0.6 .. 1.1] | 68% | 351 | distance to the nearest living ally (alive, off spawn; mean) |
| isolated | 22.1% | 17.6% | +4.6pt [+3.3pt .. +6.0pt] | 69% | 351 | alive champion-rounds off spawn with no ally within 8 |
| outnumbered | 17.4% | 15.3% | +2.2pt [+0.2pt .. +4.4pt] | 55% | 351 | contact champion-rounds (an enemy within 8) with more enemies than allies within 8 |
| outnumbering | 58.9% | 62.3% | -3.3pt [-6.8pt .. -0.3pt] | 42% | 351 | contact champion-rounds with more allies than enemies within 8 |
| control | 54.2% | 45.8% | +8.4pt [+7.0pt .. +9.9pt] | 76% | 351 | camp value nearer (walking) to our champions than theirs, gems + gold/4 per respawn, sampled |
| control_own | 81.6% | 74.1% | +7.5pt [+6.1pt .. +8.8pt] | 73% | 345 | own-half camp value under our control |
| enemy_half | 12.4% | 12.8% | -0.4pt [-1.5pt .. +0.7pt] | 50% | 351 | alive champion-rounds on the enemy half |
| own_lost | 12.6% | 24.7% | -12.1pt [-15.1pt .. -9.5pt] | 22% | 332 | gems of own-half captures taken by the enemy / own-half captured gems |
| contest_win | 53.9% | 46.1% | +7.8pt [+2.3pt .. +14.2pt] | 52% | 324 | contested camp cycles (both teams hit, held or contested) we captured |
| fight_turnout | 52.7% | 53.4% | -0.7pt [-2.3pt .. +0.6pt] | 45% | 351 | own alive champions within 8 of a fight at its start / own alive champions |
| fight_outnum | 36.5% | 35.2% | +1.3pt [-2.6pt .. +5.4pt] | 53% | 351 | fights started with fewer own champions present |
| lonely_death | 26.7% | 31.4% | -4.6pt [-9.0pt .. +0.3pt] | 33% | 263 | deaths to champions with no living ally within 8 |

## v115 in its wins and losses

235 wins, 116 losses. Opponent columns are the same games from the other side.

| metric | v115 won | v115 lost | opponent when v115 won | opponent when v115 lost |
| --- | --- | --- | --- | --- |
| mt_walk | 55.3% | 60.3% | 59.2% | 57.2% |
| mt_walk_bag | 27.2% | 27.6% | 22.9% | 22.5% |
| mt_work | 29.1% | 25.1% | 22.9% | 25.2% |
| mt_fight | 4.2% | 4.8% | 4.8% | 4.3% |
| mt_wait | 4.4% | 3.0% | 0.5% | 0.5% |
| mt_idle | 1.3% | 1.1% | 0.3% | 0.2% |
| mt_spawn | 1.1% | 1.2% | 1.8% | 0.7% |
| mt_recall | 4.5% | 4.3% | 6.6% | 5.8% |
| mt_dead | 5.5% | 13.9% | 13.9% | 6.1% |
| regroup_share | 11.9% | 12.6% | 12.0% | 14.0% |
| walk_waste | 27.6% | 30.4% | 28.5% | 23.6% |
| walk_per_gem | 2.5 | 7.4 | 8.0 | 2.5 |
| earned_per100 | 153 | 95.8 | 92.4 | 142 |
| conversion | 93.0% | 59.7% | 64.9% | 89.8% |
| gem_latency | 119 | 61.9 | 69.6 | 61.4 |
| gem_exposed | 38.2% | 35.1% | 35.4% | 36.9% |
| carry_top | 66.0% | 57.4% | 51.8% | 50.2% |
| nn_dist | 5.6 | 6.0 | 4.9 | 5.0 |
| isolated | 21.4% | 23.7% | 17.7% | 17.2% |
| outnumbered | 15.9% | 20.5% | 16.6% | 12.7% |
| outnumbering | 61.5% | 53.8% | 60.5% | 65.9% |
| control | 57.0% | 48.6% | 43.0% | 51.4% |
| control_own | 82.8% | 79.1% | 70.9% | 80.5% |
| enemy_half | 14.1% | 9.0% | 12.4% | 13.8% |
| own_lost | 9.4% | 18.9% | 30.1% | 13.1% |
| contest_win | 62.5% | 37.5% | 37.5% | 62.5% |
| fight_turnout | 52.8% | 52.6% | 54.1% | 52.0% |
| fight_outnum | 33.7% | 42.2% | 37.1% | 31.4% |
| lonely_death | 28.5% | 30.2% | 31.3% | 33.7% |

## Rounds 1-150, paired

The same quantities over the first 150 rounds only (most break rounds come later), with v115's win rate in the games where its value was higher or lower than opponent's.

| r1-150 | v115 | opponent | v115 - opponent [95% CI] | v115 win rate when higher | v115 win rate when lower |
| --- | --- | --- | --- | --- | --- |
| walk | 53.2% | 54.5% | -1.2pt [-2.3pt .. -0.3pt] | 62% (n=156) | 71% (n=194) |
| work | 33.4% | 29.9% | +3.5pt [+2.6pt .. +4.7pt] | 72% (n=224) | 58% (n=125) |
| wait | 1.7% | 0.3% | +1.4pt [+1.2pt .. +1.6pt] | 66% (n=283) | 73% (n=41) |
| dead | 4.7% | 3.8% | +0.9pt [-0.3pt .. +1.9pt] | 52% (n=104) | 84% (n=85) |
| isolated | 17.3% | 10.4% | +6.9pt [+5.5pt .. +8.3pt] | 65% (n=272) | 74% (n=77) |
| outnumbered | 22.5% | 12.0% | +10.6pt [+7.5pt .. +13.8pt] | 63% (n=180) | 75% (n=115) |
| control | 52.7% | 47.3% | +5.5pt [+3.8pt .. +7.5pt] | 71% (n=229) | 60% (n=122) |

## By map family

Maps by family (the name without its trailing seed and `gen-` prefix); v115 minus opponent per game, mean. Win rate is the focus team's.

| family | games | v115 won | d mt_walk | d mt_work | d mt_dead | d control | d outnumbered | d own_lost | d contest_win | v115 losses: top cause |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 00rushbait_v2 | 4 | 50% | -0.9pt | +4.0pt | +6.1pt | +4.5pt | +7.4pt | - | -33.9pt | farm 2/2 |
| 04bowls | 4 | 50% | +2.8pt | -0.5pt | -2.3pt | +3.8pt | -9.9pt | -4.4pt | +12.8pt | fight 2/2 |
| 03twisty | 4 | 50% | -0.8pt | +5.2pt | -6.2pt | -0.6pt | +10.0pt | -29.4pt | +37.5pt | farm 2/2 |
| 02treasure_box | 4 | 25% | +13.4pt | -5.9pt | +0.7pt | +1.6pt | +6.8pt | -0.2pt | -58.5pt | fight 3/3 |
| 01starvation | 4 | 100% | -6.8pt | +6.9pt | -12.6pt | +1.3pt | +2.9pt | -22.1pt | +29.3pt | - |
| 04passageway | 4 | 100% | -9.0pt | +13.0pt | -4.1pt | +13.9pt | +7.1pt | -40.0pt | +16.8pt | - |
| 04sunburst | 4 | 25% | +1.6pt | +1.1pt | +20.5pt | -12.0pt | +11.9pt | +42.2pt | -65.0pt | farm 2/3 |
| 03colosseum | 4 | 100% | -11.1pt | +15.4pt | -11.3pt | +31.7pt | -11.3pt | -53.5pt | +23.7pt | - |
| 00corners | 4 | 75% | -3.1pt | +6.0pt | -0.1pt | +7.5pt | -3.9pt | -18.7pt | +31.4pt | fight 1/1 |
| 00collision | 4 | 25% | +5.8pt | +1.8pt | +6.8pt | -1.0pt | -1.2pt | -3.3pt | -22.1pt | fight 2/3 |
| 03homonoliths | 4 | 75% | -2.2pt | +16.4pt | -2.5pt | -0.2pt | -22.2pt | +0.0pt | +100.0pt | farm 1/1 |
| 04braided_river | 4 | 50% | +4.5pt | -2.5pt | +0.5pt | +8.7pt | +1.2pt | -6.8pt | +22.4pt | bank 1/2 |
| adgato_gemcombat5 | 4 | 50% | +1.3pt | -0.9pt | +1.3pt | -1.6pt | +1.5pt | +2.9pt | +0.0pt | fight 1/2 |
| 03shrines | 4 | 25% | +2.7pt | +4.2pt | +3.8pt | +0.8pt | +1.8pt | -8.3pt | +4.2pt | fight 2/3 |
| 03reef | 4 | 75% | +3.5pt | +0.0pt | -2.3pt | +3.4pt | -2.3pt | -8.9pt | +0.0pt | fight 1/1 |
| 04hollows | 4 | 100% | -1.4pt | +7.3pt | -4.7pt | +15.9pt | -13.3pt | -19.3pt | +18.6pt | - |
| 02the_pond | 4 | 25% | +2.7pt | -5.3pt | +2.5pt | -0.6pt | +8.0pt | -24.1pt | -26.3pt | fight 3/3 |
| 00reverse_spiral | 4 | 75% | -1.8pt | +9.7pt | -5.8pt | +25.5pt | +4.4pt | -30.0pt | -12.2pt | fight 1/1 |
| 03the_front | 4 | 75% | -5.6pt | +5.9pt | -0.5pt | +11.9pt | +2.6pt | -12.2pt | +3.7pt | camp 1/1 |
| 04wheel | 4 | 50% | +6.1pt | +0.2pt | -1.8pt | +4.8pt | -9.4pt | -13.7pt | -13.3pt | fight 2/2 |
| 03ambush_field | 4 | 100% | -1.0pt | +5.8pt | -12.0pt | +13.4pt | -8.2pt | -23.4pt | +3.2pt | - |
| 03one_gem | 4 | 100% | -18.5pt | +18.8pt | -24.1pt | +33.5pt | +1.0pt | - | +68.4pt | - |
| 00ambush | 4 | 100% | -0.6pt | +1.6pt | +2.2pt | +6.9pt | +28.9pt | -3.5pt | -26.7pt | - |
| 04plaza | 4 | 100% | +12.3pt | +0.2pt | -17.1pt | +18.7pt | -20.7pt | -0.2pt | -23.0pt | - |
| 00gem_fields | 4 | 100% | -6.6pt | +11.1pt | -4.5pt | +15.6pt | +11.8pt | -21.8pt | -1.9pt | - |

(103 more rows in `macro-families.csv`)

## Where the turns go

Share of all champion-rounds (dead included), whole game and per phase.

| class | v115 | opponent | v115 r1-150 | v115 r151-400 | v115 r401-800 | v115 r801+ | opponent r1-150 | opponent r151-400 | opponent r401-800 | opponent r801+ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dead | 8.7% | 11.1% | 4.6% | 7.6% | 10.3% | 11.4% | 3.8% | 8.5% | 14.0% | 16.4% |
| lost | 0.1% | 3.8% | 0.2% | 0.1% | 0.1% | 0.1% | 3.8% | 4.2% | 3.8% | 3.3% |
| fight | 4.0% | 4.0% | 3.6% | 3.7% | 4.0% | 4.6% | 3.7% | 3.7% | 4.0% | 4.5% |
| tribute | 1.6% | 1.0% | 0.6% | 1.3% | 2.2% | 1.7% | 0.4% | 0.9% | 1.3% | 1.2% |
| recall | 4.0% | 5.8% | 4.3% | 5.0% | 3.8% | 2.8% | 5.4% | 6.0% | 5.7% | 6.1% |
| teleport | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| camp | 17.9% | 18.2% | 27.1% | 20.6% | 15.7% | 9.5% | 27.8% | 21.5% | 15.9% | 8.9% |
| hold | 4.5% | 0.7% | 4.2% | 4.5% | 4.0% | 5.9% | 0.8% | 0.6% | 0.6% | 0.9% |
| walk_bag | 25.3% | 20.5% | 17.6% | 27.8% | 27.4% | 24.3% | 12.9% | 23.2% | 22.1% | 20.4% |
| walk | 27.7% | 32.8% | 33.6% | 24.6% | 26.2% | 29.9% | 40.0% | 29.8% | 31.0% | 34.0% |
| spawn | 1.1% | 1.4% | 1.2% | 1.1% | 1.0% | 0.9% | 1.1% | 1.0% | 0.9% | 3.4% |
| wait_camp | 3.1% | 0.3% | 1.6% | 2.5% | 3.2% | 5.4% | 0.2% | 0.2% | 0.3% | 0.3% |
| wait_altar | 0.7% | 0.1% | 0.0% | 0.1% | 0.9% | 2.0% | 0.0% | 0.1% | 0.2% | 0.2% |
| idle | 1.2% | 0.3% | 1.4% | 1.0% | 1.2% | 1.3% | 0.3% | 0.2% | 0.2% | 0.4% |

## What the walking was for

Walk turns by what the walk led to (the class of the first turn after the leg), as a share of alive turns. "regroup" counts the walks that end within 3 of an ally who was more than 8 away when the walk began, by destination.

| walk led to | v115 | opponent | v115 regroup | opponent regroup |
| --- | --- | --- | --- | --- |
| camp | 23.9% | 29.3% | 5.2% | 7.4% |
| hold | 2.6% | 0.1% | 0.3% | 0.0% |
| tribute | 4.8% | 2.4% | 1.0% | 0.4% |
| fight | 11.0% | 11.8% | 2.5% | 2.7% |
| recall | 3.3% | 7.6% | 0.5% | 1.5% |
| spawn | 0.0% | 0.2% | 0.0% | 0.0% |
| wait_camp | 7.9% | 0.7% | 2.2% | 0.1% |
| wait_altar | 0.6% | 0.5% | 0.2% | 0.1% |
| idle | 2.9% | 0.9% | 0.5% | 0.1% |
| dead | 0.3% | 0.3% | 0.1% | 0.0% |
| other | 0.7% | 6.0% | 0.1% | 1.1% |

## Champion roles

Per champion type, pooled over games: turn mix (alive turns), share of the team's capture gems and of its carried gem-rounds.

**v115**

| type | rounds | walk | walk_bag | camp | hold | fight | recall | wait | idle | dead | capture gems | gem-rounds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Cassi | 281382 | 36% | 26% | 21% | 4% | 3% | 4% | 3% | 2% | 12% | 10% | 4% |
| Issac | 281382 | 31% | 25% | 22% | 5% | 4% | 5% | 4% | 1% | 12% | 11% | 4% |
| Vesper Vale | 223795 | 22% | 31% | 22% | 5% | 5% | 6% | 4% | 1% | 4% | 23% | 15% |
| Prism | 206134 | 10% | 45% | 18% | 7% | 4% | 5% | 5% | 1% | 6% | 26% | 64% |
| Willow | 183004 | 61% | 8% | 15% | 1% | 2% | 2% | 7% | 2% | 9% | 2% | 1% |
| Heart of Ruin | 101492 | 28% | 29% | 22% | 4% | 6% | 4% | 3% | 1% | 6% | 5% | 2% |
| Vendetta | 85863 | 22% | 35% | 20% | 5% | 3% | 6% | 3% | 2% | 6% | 6% | 2% |
| Ryth | 77287 | 29% | 26% | 17% | 8% | 7% | 5% | 4% | 0% | 8% | 5% | 2% |
| Ren | 54221 | 25% | 32% | 20% | 3% | 7% | 6% | 2% | 2% | 10% | 3% | 1% |
| Marcella | 53916 | 36% | 25% | 11% | 6% | 8% | 4% | 7% | 0% | 10% | 4% | 1% |
| Tavi | 50031 | 36% | 21% | 19% | 8% | 6% | 3% | 5% | 0% | 13% | 2% | 1% |
| Varg | 33251 | 34% | 23% | 23% | 5% | 2% | 6% | 3% | 1% | 3% | 3% | 1% |
| Stellar | 11219 | 20% | 32% | 21% | 5% | 5% | 3% | 10% | 0% | 11% | 1% | 1% |

**opponent**

| type | rounds | walk | walk_bag | camp | hold | fight | recall | wait | idle | dead | capture gems | gem-rounds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Cassi | 305870 | 46% | 18% | 21% | 1% | 3% | 5% | 0% | 0% | 15% | 8% | 7% |
| Issac | 305870 | 43% | 18% | 22% | 1% | 4% | 5% | 0% | 0% | 15% | 8% | 7% |
| Heart of Ruin | 277132 | 32% | 26% | 21% | 1% | 6% | 6% | 0% | 0% | 10% | 16% | 13% |
| Vendetta | 205609 | 27% | 31% | 20% | 1% | 5% | 9% | 1% | 0% | 9% | 19% | 16% |
| Vesper Vale | 174542 | 22% | 28% | 23% | 1% | 5% | 8% | 1% | 0% | 8% | 24% | 29% |
| Marcella | 156063 | 33% | 31% | 11% | 1% | 7% | 9% | 1% | 0% | 8% | 18% | 12% |
| Willow | 150714 | 53% | 11% | 23% | 1% | 2% | 7% | 1% | 0% | 7% | 2% | 2% |
| Tavi | 55348 | 40% | 20% | 22% | 0% | 5% | 0% | 0% | 0% | 11% | 2% | 1% |
| Prism | 21758 | 15% | 45% | 11% | 2% | 5% | 7% | 0% | 0% | 13% | 3% | 12% |
| Ren | 11851 | 61% | 15% | 10% | 1% | 6% | 6% | 0% | 0% | 17% | 0% | 0% |
| Varg | 2708 | 19% | 20% | 34% | 1% | 5% | 6% | 1% | 0% | 16% | 0% | 0% |

## Gem flow

Per game means. tributed = captured + taken by kills - lost to champions - lost to camps - carried at the end (the identity holds exactly in every game unless noted).

| gems | v115 | opponent |
| --- | --- | --- |
| cap | 921 | 755 |
| kill | 98.3 | 116 |
| lost_champ | 116 | 98.3 |
| lost_camp | 3.9 | 3.5 |
| carried_end | 49.9 | 121 |
| tributed | 850 | 648 |

## Cohesion and map control by phase

| phase | v115 isolated | v115 outnumbered | v115 control | opponent isolated | opponent outnumbered | opponent control |
| --- | --- | --- | --- | --- | --- | --- |
| r1-150 | 17% | 20% | 54% | 10% | 12% | 46% |
| r151-400 | 24% | 17% | 55% | 17% | 14% | 45% |
| r401-800 | 26% | 16% | 54% | 21% | 15% | 46% |
| r801+ | 26% | 15% | 53% | 25% | 18% | 47% |

isolated: field champion-rounds with no ally within 8; outnumbered: contact rounds with more enemies than allies within 8; control: share of camp value nearer by walking to that team's champions.

## Who turns up to fights

At each engagement's first round (analysis/fights.py clustering), every own champion alive and more than 8 from the fight, by what it was doing; "joined later" are those that dealt or took damage in it anyway. Distances are to the fight's first location.

| absent ally was | v115 per fight | opponent per fight |
| --- | --- | --- |
| walking >16 | 0.66 | 0.70 |
| walking <=16 | 0.59 | 0.59 |
| dead | 0.54 | 0.62 |
| camp >16 | 0.20 | 0.22 |
| camp <=16 | 0.20 | 0.17 |
| channel >16 | 0.07 | 0.08 |
| channel <=16 | 0.07 | 0.08 |
| joined later | 0.07 | 0.06 |
| hold <=16 | 0.06 | 0.01 |
| hold >16 | 0.05 | 0.01 |
| other >16 | 0.00 | 0.05 |
| other <=16 | 0.00 | 0.04 |
| another fight >16 | 0.02 | 0.02 |
| another fight <=16 | 0.02 | 0.02 |
| waiting <=16 | 0.03 | 0.00 |
| waiting >16 | 0.03 | 0.00 |
| spawn >16 | 0.01 | 0.01 |
| spawn <=16 | 0.01 | 0.01 |
| idle >16 | 0.02 | 0.00 |
| idle <=16 | 0.01 | 0.00 |

Net swing (gems from kills - own bags lost + gold/4) by champions present at the start, own minus enemy:

| numbers | v115 fights | v115 mean swing | opponent fights | opponent mean swing |
| --- | --- | --- | --- | --- |
| -2 or fewer | 2065 | -3.8 | 1971 | -6.1 |
| -1 | 2317 | -4.6 | 2204 | -1.2 |
| +0 | 3258 | 3.1 | 3258 | -3.1 |
| +1 | 2204 | 1.2 | 2317 | 4.6 |
| +2 or more | 1971 | 6.1 | 2065 | 3.8 |

## Camp contests

A camp cycle (from respawn to capture) is contested when both teams hit its monsters or held its tiles, or a hold was reset as contested. Steals: captured by the team that did not land the clearing blow.

| per game | v115 | opponent |
| --- | --- | --- |
| won | 4.39 | 3.90 |
| lost | 3.90 | 4.39 |
| won_gems | 144 | 123 |
| lost_gems | 123 | 144 |
| steals | 1.20 | 1.33 |
| stolen | 1.33 | 1.20 |
| captured gems, own half | 568 | 513 |
| captured gems, mid half | 193 | 160 |
| captured gems, enemy half | 160 | 82.7 |

| group | v115 won | v115 lost | v115 share |
| --- | --- | --- | --- |
| G | 101 | 163 | 38% |
| $$ | 83 | 75 | 53% |
| GGW | 72 | 75 | 49% |
| GGG | 66 | 47 | 58% |
| $W | 66 | 45 | 59% |
| $$$ | 82 | 24 | 77% |
| GGGG | 55 | 42 | 57% |
| GG | 39 | 45 | 46% |
| GGGGG | 27 | 45 | 38% |
| $EG | 41 | 29 | 59% |
| $$WW | 36 | 31 | 54% |
| GW | 27 | 36 | 43% |
| GGGW | 27 | 34 | 44% |
| EG | 26 | 24 | 52% |
| EGGG | 26 | 23 | 53% |

(115 more rows in `macro-contest_types.csv`)

## Which camps get taken

Captures per group type against capacity: the cycles each type could give at most (game rounds / (respawn + 6 capture rounds), summed over the map's groups of that type, both halves). Low shares on strong groups are camps nobody farms.

| group | capacity a game | v115 captures | opponent captures | v115 share | opponent share | taken (both) | v115 gems | opponent gems |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| $$ | 35.3 | 7.7 | 6.1 | 22% | 17% | 39% | 0.0 | 0.0 |
| G | 34.3 | 8.5 | 5.9 | 25% | 17% | 42% | 62.3 | 43.2 |
| $W | 23.1 | 2.5 | 2.5 | 11% | 11% | 22% | 10.1 | 10.0 |
| $ | 21.9 | 2.1 | 1.7 | 10% | 8% | 17% | 0.0 | 0.0 |
| GW | 16.8 | 2.4 | 1.9 | 14% | 12% | 26% | 27.6 | 22.4 |
| $$W | 13.1 | 1.5 | 1.3 | 12% | 10% | 22% | 6.2 | 5.2 |
| $$$ | 11.0 | 4.1 | 1.3 | 37% | 12% | 49% | 0.0 | 0.0 |
| GGW | 10.6 | 1.9 | 1.3 | 18% | 12% | 30% | 36.7 | 24.6 |
| W | 9.6 | 1.2 | 1.3 | 12% | 13% | 25% | 4.7 | 5.0 |
| GG | 7.5 | 2.5 | 1.2 | 34% | 16% | 49% | 37.9 | 17.9 |
| GGG | 7.5 | 2.2 | 1.3 | 29% | 18% | 47% | 50.7 | 29.5 |
| $$WW | 7.0 | 0.8 | 0.8 | 12% | 11% | 23% | 6.6 | 6.3 |
| $WW | 6.7 | 1.0 | 1.1 | 14% | 17% | 31% | 7.7 | 9.2 |
| $$$W | 6.6 | 0.7 | 0.9 | 10% | 13% | 23% | 2.6 | 3.4 |
| $GWW | 4.3 | 0.7 | 0.6 | 16% | 15% | 31% | 11.0 | 9.9 |
| $GW | 3.2 | 0.7 | 0.6 | 21% | 18% | 39% | 8.0 | 6.6 |
| $EG | 3.1 | 0.9 | 0.7 | 28% | 21% | 49% | 19.7 | 14.8 |
| GGGG | 3.0 | 1.1 | 0.6 | 36% | 19% | 55% | 33.7 | 17.1 |
| $$E | 3.0 | 0.6 | 0.7 | 20% | 24% | 44% | 9.1 | 10.8 |
| EGG | 2.9 | 0.6 | 0.5 | 20% | 19% | 39% | 18.6 | 16.6 |

(166 more rows in `macro-capacity.csv`)

## Why games are lost: v115's losses

The break round is the last round the loser had at least the winner's wealth (tributed + carried gems); 0 means it was never level after round 1. The window is the 100 rounds after it. Its cause is the largest of: farm (capture gems, winner - loser), fight (kill gems taken minus bags lost to champions, winner - loser), camp (bags lost to camps, loser - winner); "bank" when the loser lost while holding at least as much wealth (gems carried, not tributed). Whole-game components are over all rounds.

| cause of the break window | games | share | median break | loser dead | winner dead | loser work | winner work | loser walk | winner walk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| farm | 57 | 49% | 372 | 18% | 3% | 19% | 23% | 51% | 56% |
| fight | 54 | 47% | 444 | 26% | 9% | 17% | 21% | 47% | 53% |
| camp | 1 | 1% | 424 | 10% | 13% | 3% | 23% | 27% | 49% |
| bank | 4 | 3% | 878 | - | - | - | - | - | - |

Turn shares are over the windows of that cause (work = camp, hold, tribute). A farm window with a high loser dead share is a farm deficit that follows deaths; one with level dead shares is out-farming with bodies alive.

Break round: median 436 (p25 177, p75 649); 0 never level, 25 in rounds 1-150, 29 in 151-400, 62 after 400.

| component (winner advantage, gems) | whole game | break window |
| --- | --- | --- |
| farm | 271 | 84.7 |
| fight | 278 | 164 |
| camp | 5.4 | 2.8 |
| bank | 3.7 | - |

Turn mix in the break windows (loser vs winner):

| class | loser | winner |
| --- | --- | --- |
| dead | 21.5% | 5.5% |
| lost | 0.1% | 6.1% |
| fight | 4.0% | 4.3% |
| tribute | 0.9% | 2.7% |
| recall | 3.2% | 6.1% |
| teleport | 0.0% | 0.0% |
| camp | 14.0% | 18.7% |
| hold | 3.2% | 0.8% |
| walk_bag | 20.9% | 23.1% |
| walk | 28.1% | 31.4% |
| spawn | 1.0% | 0.6% |
| wait_camp | 1.8% | 0.3% |
| wait_altar | 0.1% | 0.2% |
| idle | 1.1% | 0.2% |

Loser deaths in the break windows: 170 over 116 games (1.47 a game), by type Prism 47, Issac 25, Willow 19, Cassi 17, Vesper Vale 12, Heart of Ruin 10, Tavi 9, Ryth 7, Marcella 7, Vendetta 6, Ren 6, Stellar 4, Varg 1; bag at death median 14, 41 with 50+.

What opened the window: the loser's largest-bag death within 10 rounds of the break, if any:

| trigger | games | share |
| --- | --- | --- |
| no loser death within 10 rounds | 51 | 44% |
| Prism died with 50-199 gems | 15 | 13% |
| Prism died with 200+ gems | 12 | 10% |
| Issac died with <50 gems | 9 | 8% |
| Prism died with <50 gems | 6 | 5% |
| Cassi died with <50 gems | 5 | 4% |
| ended holding the larger wealth | 4 | 3% |
| Ryth died with <50 gems | 3 | 3% |
| Vesper Vale died with <50 gems | 2 | 2% |
| Marcella died with <50 gems | 1 | 1% |
| Vendetta died with 50-199 gems | 1 | 1% |
| Vesper Vale died with 200+ gems | 1 | 1% |

(6 more rows in `macro-triggers.csv`)

Largest windows (gap = winner minus loser wealth at the window's end):

| game / break | map | cause | gap | window components | loser deaths in the window |
| --- | --- | --- | --- | --- | --- |
| 3cdc157ddaf83093 r565 | 01boss_battle | fight | 2137 | farm +336 fight +2378 camp +0 | r566 Vesper Vale bag 1095 by Vesper Vale; r620 Issac bag 30 by Vesper Vale; r627 Stellar bag 94 by Tavi |
| 18985cd163da1935 r846 | 02treasure_box | fight | 1139 | farm +98 fight +1176 camp +0 | r847 Prism bag 469 by Vesper Vale; r879 Tavi bag 36 by Vesper Vale; r894 Marcella bag 83 by Vesper Vale; r945 Stellar bag 0 by Vesper Vale |
| e5ff7c2f70246901 r441 | 04two_kingdoms | fight | 971 | farm +2 fight +1010 camp +0 | r443 Prism bag 426 by Prism; r483 Vendetta bag 47 by Prism; r521 Vesper Vale bag 32 by Vesper Vale |
| c39658a433012b02 r1010 | 02the_pond | fight | 840 | farm +0 fight +942 camp +0 | r1011 Prism bag 465 by Vesper Vale; r1012 Willow bag 6 by Vesper Vale |
| c6da33ec1345cea0 r846 | 02guardians | fight | 792 | farm +67 fight +842 camp +0 | r847 Tavi bag 421 by Vendetta |
| ff36550a4dd15170 r49 | 00vault | farm | 694 | farm +694 fight +0 camp +0 | r68 Cassi bag 0 by Prism; r80 Ryth bag 0 by Heart of Ruin |
| 02acb3b556afb169 r601 | 04bowls | fight | 633 | farm +72 fight +604 camp +0 | r602 Prism bag 302 by Vesper Vale |
| 99db761839ce5db1 r977 | 00collision | fight | 632 | farm -47 fight +686 camp +0 | r1028 Prism bag 343 by Marcella |
| 14b6760f1baaceb1 r472 | 03homonoliths | farm | 600 | farm +600 fight +0 camp +0 | - |
| 7618836fb7502470 r706 | 02geodes | fight | 532 | farm +110 fight +432 camp +0 | r716 Prism bag 216 by Cassi |
| d38952b76d87c5ec r424 | 03the_front | camp | 516 | farm +243 fight +0 camp +328 | r425 Prism bag 328 by camp |
| 5481f825cb9703c5 r690 | 04bowls | fight | 485 | farm -51 fight +734 camp +0 | r691 Prism bag 342 by Marcella; r735 Willow bag 0 by Vendetta; r739 Cassi bag 25 by Vendetta |
| c084b20552b4cd49 r642 | 03honeycomb | fight | 448 | farm +70 fight +430 camp +0 | r643 Prism bag 215 by Vesper Vale |
| 7ac2d2e9f993c60b r895 | 00rows | farm | 429 | farm +458 fight +0 camp +0 | - |
| d2c4f7550d573d11 r400 | 04courtyard | fight | 412 | farm +114 fight +304 camp +0 | r432 Prism bag 152 by Marcella; r462 Cassi bag 0 by camp |
| 89ccc180bfc4ee82 r930 | 00rows | farm | 400 | farm +447 fight +0 camp +0 | - |
| 739e47e6c5d6a79b r629 | 02the_pond | fight | 382 | farm +66 fight +386 camp +0 | r630 Prism bag 284 by Vesper Vale |
| 316b237fd44ec524 r282 | 04tidepools | fight | 380 | farm +166 fight +242 camp +0 | r336 Prism bag 135 by Marcella |
| 2007651f4f21a8a9 r615 | 04wheel | fight | 378 | farm +71 fight +362 camp +0 | r616 Prism bag 160 by Vesper Vale; r623 Issac bag 21 by Willow; r664 Willow bag 0 by Vesper Vale |
| 5fc51bff55582d1a r739 | 00great_wall | fight | 368 | farm +31 fight +350 camp +0 | r834 Prism bag 192 by Heart of Ruin |
| baec7573ddd9eb5f r518 | 03shrines | fight | 362 | farm +21 fight +400 camp +0 | r519 Prism bag 200 by Cassi |
| 403f47fa246839dd r655 | 04bridges | fight | 335 | farm -80 fight +648 camp +0 | r656 Prism bag 324 by Marcella |
| 849194b4282c1a2b r578 | 01yellow_brick_road | farm | 274 | farm +178 fight +98 camp +0 | r607 Issac bag 0 by Vendetta; r611 Varg bag 23 by Vendetta; r615 Vendetta bag 11 by Vendetta; r617 Tavi bag 15 by Vendetta |
| 63bba97ea22a6068 r758 | 00great_wall | fight | 270 | farm -90 fight +368 camp +0 | r760 Prism bag 184 by Marcella |
| 46ce4dccc43f6dfc r522 | 00lost_world | farm | 266 | farm +204 fight +34 camp +28 | r523 Tavi bag 17 by Marcella; r602 Cassi bag 28 by camp; r605 Marcella bag 0 by Marcella; r611 Willow bag 0 by camp |
