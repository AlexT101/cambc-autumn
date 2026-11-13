# Macro: turns, gems, cohesion, control, losses

Set: replays/batch-20261113-020034-ab-mac13-nyx-basedbg-ladder (128 games, 127 clusters). Sides: winner vs loser in the same game (128 pairs). Without --team each game is read winner against loser, which partly measures winning.

Every number is read from the replay alone (no bot traces). Turn classes are per champion-round, first match wins: dead, fight (dealt or took champion damage), lost (stunned), tribute/recall/teleport channel, camp (hit a camp), walk_bag/walk (moved, carrying gems or not), lost (out of fuel or bot error without moving or hitting), hold (still on a claimable group tile), spawn (still on own spawn), idle. Distances are Chebyshev unless noted; camp control uses walking distance. Differences are mean winner minus loser with a 95% cluster-bootstrap CI over map pairs or ladder groups.

## Macro metrics, paired

| metric | winner | loser | winner - loser [95% CI] | winner higher | games | definition |
| --- | --- | --- | --- | --- | --- | --- |
| mt_walk | 54.9% | 60.4% | -5.5pt [-6.8pt .. -4.0pt] | 19% | 128 | alive turns walking (with or without gems) |
| mt_walk_bag | 26.3% | 26.8% | -0.5pt [-1.5pt .. +0.6pt] | 46% | 128 | alive turns walking while carrying gems |
| mt_work | 29.2% | 25.6% | +3.6pt [+2.6pt .. +4.4pt] | 76% | 128 | alive turns at work: hitting camps, holding captures, tributing |
| mt_fight | 3.6% | 4.0% | -0.5pt [-0.7pt .. -0.3pt] | 31% | 128 | alive turns in fights (dealt or took champion damage) |
| mt_wait | 5.0% | 2.8% | +2.1pt [+0.9pt .. +3.3pt] | 77% | 128 | alive turns waiting still by a respawning or live camp, or by an altar, without hitting or holding |
| mt_idle | 1.4% | 1.4% | +0.1pt [-0.2pt .. +0.3pt] | 50% | 128 | alive turns idle elsewhere off spawn |
| mt_spawn | 1.4% | 1.4% | -0.0pt [-0.2pt .. +0.3pt] | 34% | 128 | alive turns standing on own spawn |
| mt_recall | 4.4% | 4.3% | +0.2pt [-0.0pt .. +0.3pt] | 54% | 128 | alive turns channelling recalls |
| mt_dead | 4.7% | 14.0% | -9.2pt [-11.0pt .. -7.4pt] | 10% | 128 | champion turns dead |
| regroup_share | 12.6% | 12.7% | -0.2pt [-1.0pt .. +0.8pt] | 53% | 128 | alive turns on walks that end next to an ally who was 9+ away at the start (walking to allies) |
| walk_waste | 29.7% | 33.9% | -4.2pt [-5.6pt .. -2.8pt] | 27% | 128 | walked steps beyond the straight (Chebyshev) line of each walk leg / steps |
| walk_per_gem | 2.2 | 5.0 | -2.8 [-3.9 .. -1.8] | 10% | 125 | walk turns per gem earned (captures and kills) |
| earned_per100 | 163 | 100 | 62.6 [53.9 .. 70.4] | 92% | 128 | gems earned (capture shares + kill bags) per 100 rounds |
| conversion | 88.6% | 45.4% | +43.1pt [+39.1pt .. +47.6pt] | 92% | 125 | tributed / earned gems |
| gem_latency | 164 | 82.4 | 81.8 [56.6 .. 106] | 75% | 120 | mean rounds a tributed gem was carried (gem-weighted) |
| gem_exposed | 38.9% | 34.0% | +4.9pt [+2.2pt .. +7.4pt] | 59% | 125 | carried gem-rounds in sight of an enemy / carried gem-rounds |
| carry_top | 77.0% | 68.4% | +8.6pt [+5.2pt .. +12.4pt] | 68% | 125 | share of the team's carried gem-rounds on its top carrier |
| nn_dist | 5.4 | 5.6 | -0.2 [-0.4 .. -0.0] | 45% | 128 | distance to the nearest living ally (alive, off spawn; mean) |
| isolated | 20.5% | 22.2% | -1.7pt [-2.6pt .. -0.8pt] | 39% | 128 | alive champion-rounds off spawn with no ally within 8 |
| outnumbered | 11.3% | 18.2% | -6.9pt [-9.9pt .. -3.7pt] | 33% | 128 | contact champion-rounds (an enemy within 8) with more enemies than allies within 8 |
| outnumbering | 63.1% | 52.9% | +10.2pt [+5.8pt .. +14.7pt] | 68% | 128 | contact champion-rounds with more allies than enemies within 8 |
| control | 54.4% | 45.6% | +8.8pt [+6.7pt .. +10.6pt] | 76% | 128 | camp value nearer (walking) to our champions than theirs, gems + gold/4 per respawn, sampled |
| control_own | 83.2% | 75.9% | +7.3pt [+5.2pt .. +9.6pt] | 71% | 126 | own-half camp value under our control |
| enemy_half | 11.3% | 8.0% | +3.3pt [+2.2pt .. +4.3pt] | 64% | 128 | alive champion-rounds on the enemy half |
| own_lost | 9.9% | 24.2% | -14.3pt [-18.4pt .. -10.0pt] | 25% | 122 | gems of own-half captures taken by the enemy / own-half captured gems |
| contest_win | 59.3% | 40.7% | +18.5pt [+10.5pt .. +27.1pt] | 67% | 122 | contested camp cycles (both teams hit, held or contested) we captured |
| fight_turnout | 53.5% | 53.3% | +0.2pt [-1.6pt .. +2.0pt] | 48% | 127 | own alive champions within 8 of a fight at its start / own alive champions |
| fight_outnum | 26.4% | 40.3% | -13.9pt [-19.4pt .. -9.1pt] | 24% | 127 | fights started with fewer own champions present |
| lonely_death | 31.2% | 29.4% | +1.8pt [-5.6pt .. +10.7pt] | 33% | 91 | deaths to champions with no living ally within 8 |

## Rounds 1-150, paired

The same quantities over the first 150 rounds only (most break rounds come later). Win-rate columns: the share of games the winner had the higher or lower value.

| r1-150 | winner | loser | difference [95% CI] | winner higher | winner lower |
| --- | --- | --- | --- | --- | --- |
| walk | 54.4% | 54.8% | -0.4pt [-1.1pt .. +0.4pt] | 100% (n=59) | 100% (n=68) |
| work | 32.7% | 32.5% | +0.2pt [-0.5pt .. +1.0pt] | 100% (n=70) | 100% (n=57) |
| wait | 1.7% | 1.6% | +0.1pt [-0.1pt .. +0.4pt] | 100% (n=67) | 100% (n=55) |
| dead | 2.5% | 4.1% | -1.7pt [-3.1pt .. -0.0pt] | 100% (n=20) | 100% (n=42) |
| isolated | 15.9% | 16.6% | -0.7pt [-1.8pt .. +0.5pt] | 100% (n=60) | 100% (n=67) |
| outnumbered | 10.2% | 12.4% | -2.3pt [-5.9pt .. +1.5pt] | 100% (n=46) | 100% (n=58) |
| control | 50.5% | 49.5% | +1.0pt [-0.7pt .. +2.9pt] | 100% (n=66) | 100% (n=62) |

## By map family

Maps by family (the name without its trailing seed and `gen-` prefix); winner minus loser per game, mean. Without --team the first side is the winner, so the win rate is 100%.

| family | games | winner won | d mt_walk | d mt_work | d mt_dead | d control | d outnumbered | d own_lost | d contest_win | winner losses: top cause |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dunes | 2 | 100% | -17.9pt | +7.3pt | -21.6pt | +5.8pt | -35.0pt | +4.1pt | +15.5pt | - |
| ambush | 1 | 100% | -3.3pt | +5.0pt | +3.1pt | +0.4pt | -4.6pt | -0.6pt | +0.0pt | - |
| anvil | 1 | 100% | -3.9pt | +5.3pt | -5.1pt | +6.6pt | +3.3pt | -43.7pt | +33.3pt | - |
| breadcrumbs | 1 | 100% | -1.4pt | -2.1pt | -9.1pt | +7.7pt | -3.0pt | -2.6pt | -10.0pt | - |
| collision | 1 | 100% | +0.3pt | -0.9pt | -2.6pt | +3.5pt | +19.6pt | -2.1pt | +4.8pt | - |
| contest | 1 | 100% | -1.3pt | +1.8pt | -9.2pt | +9.5pt | +1.2pt | -100.0pt | +63.6pt | - |
| corners | 1 | 100% | +0.7pt | -1.1pt | -0.7pt | -3.2pt | -14.0pt | -7.8pt | +33.3pt | - |
| crater | 1 | 100% | -8.4pt | +6.5pt | -18.7pt | +27.0pt | -7.1pt | -30.2pt | +60.0pt | - |
| eight | 1 | 100% | -14.5pt | -1.9pt | -9.2pt | -5.3pt | -19.7pt | +9.9pt | -5.3pt | - |
| elkring | 1 | 100% | -5.1pt | +6.2pt | -16.6pt | +4.9pt | -12.0pt | -10.9pt | +60.0pt | - |
| expanse | 1 | 100% | +0.4pt | +0.8pt | +1.2pt | -3.8pt | -36.4pt | +0.3pt | -33.3pt | - |
| fragment | 1 | 100% | -5.1pt | +5.5pt | -9.5pt | +10.3pt | -1.9pt | -46.9pt | +57.1pt | - |
| galaxy | 1 | 100% | -3.1pt | +2.4pt | -1.0pt | +6.6pt | -0.7pt | -13.6pt | +75.0pt | - |
| gem-fields | 1 | 100% | -4.9pt | +5.1pt | -11.7pt | +11.9pt | +6.2pt | -20.9pt | +14.3pt | - |
| gemfight | 1 | 100% | -10.0pt | +10.4pt | -25.2pt | +20.1pt | -14.6pt | -12.2pt | +25.0pt | - |
| great-wall | 1 | 100% | -2.7pt | +1.8pt | -8.2pt | +8.8pt | +11.6pt | +0.0pt | -100.0pt | - |
| happy-halloween | 1 | 100% | -5.7pt | +6.0pt | -8.8pt | +9.2pt | -8.2pt | +12.0pt | +0.0pt | - |
| interlock | 1 | 100% | -3.4pt | +3.1pt | +3.4pt | +5.3pt | +14.4pt | -18.8pt | +0.0pt | - |
| lanes | 1 | 100% | +0.8pt | -2.0pt | -9.3pt | +3.8pt | -21.1pt | -10.7pt | +50.0pt | - |
| lost-world | 1 | 100% | -9.3pt | +8.0pt | -14.8pt | +13.4pt | -11.6pt | -48.0pt | +52.4pt | - |
| monolith | 1 | 100% | -3.1pt | +0.9pt | -2.4pt | +5.7pt | +15.3pt | +1.1pt | -20.0pt | - |
| oasis | 1 | 100% | -7.3pt | +6.8pt | -6.5pt | +16.0pt | +2.0pt | -37.3pt | +39.1pt | - |
| packs | 1 | 100% | -3.8pt | -0.0pt | -5.4pt | +15.3pt | -6.6pt | -50.9pt | +60.0pt | - |
| pilgrimage | 1 | 100% | -0.0pt | +0.3pt | -2.2pt | +12.4pt | +7.0pt | +0.0pt | +50.0pt | - |
| quadrants | 1 | 100% | +6.4pt | -6.5pt | -0.8pt | -5.4pt | +9.0pt | +21.9pt | +60.0pt | - |

(102 more rows in `macro-families.csv`)

## Where the turns go

Share of all champion-rounds (dead included), whole game and per phase.

| class | winner | loser | winner r1-150 | winner r151-400 | winner r401-800 | winner r801+ | loser r1-150 | loser r151-400 | loser r401-800 | loser r801+ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dead | 4.8% | 13.9% | 2.3% | 5.1% | 5.4% | 5.5% | 4.0% | 9.8% | 16.7% | 22.7% |
| lost | 0.2% | 0.1% | 0.1% | 0.2% | 0.2% | 0.1% | 0.1% | 0.1% | 0.1% | 0.1% |
| fight | 3.4% | 3.3% | 3.5% | 3.2% | 3.3% | 3.9% | 3.4% | 3.1% | 3.2% | 3.6% |
| tribute | 3.0% | 0.8% | 0.3% | 1.3% | 3.9% | 6.0% | 0.3% | 0.8% | 1.0% | 0.7% |
| recall | 4.0% | 3.6% | 4.4% | 5.1% | 3.8% | 2.4% | 4.2% | 4.7% | 3.3% | 2.0% |
| teleport | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| camp | 17.7% | 15.7% | 26.9% | 20.8% | 15.8% | 9.4% | 26.3% | 19.2% | 12.9% | 6.7% |
| hold | 5.1% | 4.2% | 4.5% | 5.2% | 4.9% | 5.9% | 4.5% | 4.3% | 3.7% | 4.6% |
| walk_bag | 25.0% | 23.7% | 17.0% | 28.0% | 27.8% | 22.7% | 17.1% | 26.9% | 25.1% | 22.1% |
| walk | 28.2% | 29.5% | 36.6% | 25.8% | 26.5% | 27.5% | 35.9% | 26.5% | 28.9% | 29.6% |
| spawn | 1.5% | 1.3% | 1.2% | 1.3% | 1.4% | 2.3% | 1.2% | 1.2% | 1.2% | 1.6% |
| wait_camp | 3.4% | 2.5% | 1.6% | 2.6% | 3.7% | 5.1% | 1.5% | 2.2% | 2.4% | 4.1% |
| wait_altar | 2.1% | 0.2% | 0.0% | 0.2% | 1.8% | 6.7% | 0.0% | 0.1% | 0.2% | 0.4% |
| idle | 1.6% | 1.3% | 1.4% | 1.1% | 1.5% | 2.5% | 1.4% | 1.1% | 1.3% | 1.7% |

## What the walking was for

Walk turns by what the walk led to (the class of the first turn after the leg), as a share of alive turns. "regroup" counts the walks that end within 3 of an ally who was more than 8 away when the walk began, by destination.

| walk led to | winner | loser | winner regroup | loser regroup |
| --- | --- | --- | --- | --- |
| camp | 23.1% | 24.7% | 5.2% | 5.4% |
| hold | 3.0% | 2.9% | 0.4% | 0.4% |
| tribute | 3.5% | 2.4% | 1.3% | 0.6% |
| fight | 8.3% | 12.1% | 2.0% | 2.6% |
| recall | 3.6% | 4.1% | 0.5% | 0.6% |
| spawn | 0.0% | 0.0% | 0.0% | 0.0% |
| wait_camp | 9.2% | 9.4% | 2.7% | 2.7% |
| wait_altar | 1.1% | 0.5% | 0.4% | 0.1% |
| idle | 3.3% | 3.9% | 0.8% | 0.8% |
| dead | 0.1% | 0.6% | 0.0% | 0.1% |
| other | 0.5% | 1.1% | 0.1% | 0.3% |

## Champion roles

Per champion type, pooled over games: turn mix (alive turns), share of the team's capture gems and of its carried gem-rounds.

**winner**

| type | rounds | walk | walk_bag | camp | hold | fight | recall | wait | idle | dead | capture gems | gem-rounds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Cassi | 108971 | 38% | 24% | 21% | 4% | 3% | 4% | 3% | 2% | 9% | 9% | 2% |
| Issac | 108971 | 30% | 25% | 22% | 5% | 3% | 5% | 4% | 2% | 9% | 11% | 3% |
| Prism | 87920 | 4% | 48% | 12% | 8% | 4% | 4% | 4% | 2% | 1% | 40% | 82% |
| Willow | 72469 | 62% | 5% | 14% | 2% | 1% | 2% | 10% | 3% | 4% | 1% | 0% |
| Vesper Vale | 70483 | 21% | 27% | 22% | 7% | 5% | 6% | 6% | 1% | 2% | 16% | 8% |
| Ryth | 34983 | 28% | 19% | 19% | 9% | 6% | 5% | 11% | 0% | 5% | 5% | 1% |
| Heart of Ruin | 34216 | 26% | 28% | 20% | 4% | 6% | 4% | 3% | 2% | 3% | 4% | 1% |
| Vendetta | 27382 | 25% | 29% | 22% | 5% | 3% | 7% | 3% | 2% | 3% | 6% | 1% |
| Marcella | 27051 | 30% | 25% | 12% | 5% | 5% | 4% | 15% | 0% | 4% | 4% | 1% |
| Ren | 14966 | 30% | 29% | 20% | 3% | 5% | 5% | 2% | 3% | 3% | 1% | 0% |
| Tavi | 12855 | 33% | 20% | 17% | 13% | 4% | 3% | 7% | 0% | 2% | 2% | 0% |
| Varg | 12450 | 31% | 29% | 23% | 5% | 2% | 5% | 2% | 1% | 2% | 2% | 0% |
| Stellar | 4392 | 23% | 27% | 19% | 4% | 2% | 3% | 15% | 1% | 3% | 1% | 0% |

**loser**

| type | rounds | walk | walk_bag | camp | hold | fight | recall | wait | idle | dead | capture gems | gem-rounds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Cassi | 108971 | 41% | 24% | 20% | 3% | 3% | 3% | 2% | 2% | 19% | 9% | 4% |
| Issac | 108971 | 35% | 25% | 21% | 4% | 3% | 4% | 2% | 1% | 19% | 10% | 4% |
| Prism | 87920 | 12% | 49% | 14% | 7% | 4% | 4% | 4% | 2% | 13% | 43% | 73% |
| Willow | 72469 | 67% | 8% | 14% | 1% | 1% | 2% | 3% | 3% | 11% | 2% | 1% |
| Vesper Vale | 70483 | 24% | 29% | 22% | 7% | 4% | 6% | 5% | 1% | 7% | 13% | 7% |
| Ryth | 34983 | 32% | 22% | 19% | 9% | 7% | 5% | 3% | 0% | 16% | 5% | 2% |
| Heart of Ruin | 34216 | 32% | 28% | 20% | 4% | 6% | 4% | 2% | 1% | 10% | 3% | 2% |
| Vendetta | 27382 | 30% | 28% | 21% | 3% | 4% | 7% | 3% | 2% | 9% | 5% | 2% |
| Marcella | 27051 | 35% | 30% | 12% | 5% | 6% | 5% | 3% | 1% | 18% | 5% | 2% |
| Ren | 14966 | 23% | 31% | 18% | 3% | 5% | 5% | 10% | 2% | 10% | 2% | 1% |
| Tavi | 12855 | 38% | 19% | 16% | 15% | 5% | 3% | 2% | 0% | 9% | 1% | 0% |
| Varg | 12450 | 33% | 31% | 21% | 3% | 2% | 5% | 2% | 1% | 5% | 2% | 1% |
| Stellar | 4392 | 22% | 39% | 19% | 7% | 2% | 4% | 5% | 0% | 20% | 1% | 1% |

## Gem flow

Per game means. tributed = captured + taken by kills - lost to champions - lost to camps - carried at the end (the identity holds exactly in every game unless noted).

| gems | winner | loser |
| --- | --- | --- |
| cap | 1058 | 741 |
| kill | 251 | 41.1 |
| lost_champ | 41.1 | 251 |
| lost_camp | 1.5 | 3.5 |
| carried_end | 198 | 191 |
| tributed | 1069 | 337 |

## Cohesion and map control by phase

| phase | winner isolated | winner outnumbered | winner control | loser isolated | loser outnumbered | loser control |
| --- | --- | --- | --- | --- | --- | --- |
| r1-150 | 16% | 10% | 50% | 17% | 13% | 50% |
| r151-400 | 23% | 12% | 52% | 24% | 15% | 48% |
| r401-800 | 23% | 11% | 55% | 26% | 18% | 45% |
| r801+ | 21% | 8% | 55% | 27% | 24% | 45% |

isolated: field champion-rounds with no ally within 8; outnumbered: contact rounds with more enemies than allies within 8; control: share of camp value nearer by walking to that team's champions.

## Who turns up to fights

At each engagement's first round (analysis/fights.py clustering), every own champion alive and more than 8 from the fight, by what it was doing; "joined later" are those that dealt or took damage in it anyway. Distances are to the fight's first location.

| absent ally was | winner per fight | loser per fight |
| --- | --- | --- |
| walking >16 | 0.60 | 0.57 |
| walking <=16 | 0.58 | 0.53 |
| dead | 0.27 | 0.78 |
| camp >16 | 0.21 | 0.18 |
| camp <=16 | 0.20 | 0.17 |
| hold <=16 | 0.08 | 0.06 |
| channel >16 | 0.07 | 0.06 |
| channel <=16 | 0.07 | 0.05 |
| joined later | 0.05 | 0.05 |
| hold >16 | 0.05 | 0.04 |
| waiting <=16 | 0.03 | 0.02 |
| idle >16 | 0.02 | 0.02 |
| waiting >16 | 0.03 | 0.02 |
| spawn >16 | 0.02 | 0.02 |
| another fight >16 | 0.02 | 0.02 |
| another fight <=16 | 0.01 | 0.01 |
| spawn <=16 | 0.01 | 0.01 |
| idle <=16 | 0.01 | 0.01 |
| other <=16 | 0.00 | 0.00 |
| other >16 | 0.00 | 0.00 |

Net swing (gems from kills - own bags lost + gold/4) by champions present at the start, own minus enemy:

| numbers | winner fights | winner mean swing | loser fights | loser mean swing |
| --- | --- | --- | --- | --- |
| -2 or fewer | 479 | 21.1 | 872 | -32.3 |
| -1 | 715 | 12.9 | 863 | -14.8 |
| +0 | 1360 | 15.7 | 1360 | -15.7 |
| +1 | 863 | 14.8 | 715 | -12.9 |
| +2 or more | 873 | 32.3 | 479 | -21.1 |

## Camp contests

A camp cycle (from respawn to capture) is contested when both teams hit its monsters or held its tiles, or a hold was reset as contested. Steals: captured by the team that did not land the clearing blow.

| per game | winner | loser |
| --- | --- | --- |
| won | 6.28 | 3.82 |
| lost | 3.82 | 6.28 |
| won_gems | 190 | 87.57 |
| lost_gems | 87.57 | 190 |
| steals | 1.85 | 1.29 |
| stolen | 1.29 | 1.85 |
| captured gems, own half | 648 | 552 |
| captured gems, mid half | 257 | 110 |
| captured gems, enemy half | 153 | 79.3 |

| group | winner won | winner lost | winner share |
| --- | --- | --- | --- |
| G | 61 | 46 | 57% |
| $$ | 48 | 32 | 60% |
| GGW | 46 | 28 | 62% |
| GGG | 39 | 29 | 57% |
| GG | 38 | 20 | 66% |
| $W | 38 | 15 | 72% |
| $$$ | 24 | 24 | 50% |
| GGGG | 25 | 22 | 53% |
| GGGGG | 27 | 16 | 63% |
| $$WW | 21 | 14 | 60% |
| $$$$ | 18 | 12 | 60% |
| GGGW | 19 | 9 | 68% |
| $EG | 19 | 7 | 73% |
| $ | 16 | 9 | 64% |
| GW | 13 | 12 | 52% |

(98 more rows in `macro-contest_types.csv`)

## Which camps get taken

Captures per group type against capacity: the cycles each type could give at most (game rounds / (respawn + 6 capture rounds), summed over the map's groups of that type, both halves). Low shares on strong groups are camps nobody farms.

| group | capacity a game | winner captures | loser captures | winner share | loser share | taken (both) | winner gems | loser gems |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| $$ | 32.4 | 6.6 | 6.1 | 20% | 19% | 39% | 0.0 | 0.0 |
| G | 32.3 | 7.8 | 7.4 | 24% | 23% | 47% | 56.3 | 53.1 |
| $W | 22.3 | 2.9 | 2.3 | 13% | 10% | 23% | 11.4 | 9.3 |
| $ | 22.3 | 1.8 | 1.8 | 8% | 8% | 16% | 0.0 | 0.0 |
| GW | 17.2 | 2.8 | 2.4 | 16% | 14% | 30% | 32.4 | 27.8 |
| $$W | 12.7 | 1.7 | 1.5 | 13% | 12% | 25% | 6.7 | 5.9 |
| W | 9.9 | 1.3 | 1.2 | 13% | 12% | 25% | 5.1 | 4.7 |
| GGG | 9.1 | 2.6 | 2.0 | 28% | 22% | 50% | 57.6 | 46.6 |
| GGW | 9.0 | 1.9 | 1.3 | 21% | 15% | 36% | 36.8 | 25.9 |
| $$$ | 8.9 | 2.4 | 1.9 | 27% | 21% | 48% | 0.0 | 0.0 |
| $WW | 8.7 | 1.0 | 1.0 | 12% | 11% | 23% | 8.2 | 7.8 |
| $$WW | 7.8 | 0.8 | 0.7 | 10% | 9% | 19% | 6.1 | 5.8 |
| GG | 7.6 | 2.7 | 1.8 | 36% | 23% | 59% | 41.6 | 26.4 |
| $$$W | 6.3 | 0.5 | 0.5 | 8% | 8% | 16% | 1.9 | 2.0 |
| GGGG | 4.0 | 1.2 | 0.9 | 30% | 22% | 52% | 35.8 | 26.0 |
| $GWW | 4.0 | 0.8 | 0.8 | 19% | 19% | 38% | 12.0 | 12.2 |
| $EG | 3.9 | 1.2 | 0.9 | 31% | 24% | 55% | 27.0 | 21.4 |
| $$$E | 3.3 | 0.9 | 0.8 | 28% | 25% | 53% | 13.6 | 12.4 |
| $GW | 3.1 | 0.8 | 0.8 | 24% | 25% | 49% | 8.7 | 8.9 |
| EGG | 3.0 | 0.7 | 0.7 | 24% | 22% | 46% | 23.0 | 20.7 |

(166 more rows in `macro-capacity.csv`)

## Why games are lost: all games (loser's view)

The break round is the last round the loser had at least the winner's wealth (tributed + carried gems); 0 means it was never level after round 1. The window is the 100 rounds after it. Its cause is the largest of: farm (capture gems, winner - loser), fight (kill gems taken minus bags lost to champions, winner - loser), camp (bags lost to camps, loser - winner); "bank" when the loser lost while holding at least as much wealth (gems carried, not tributed). Whole-game components are over all rounds.

| cause of the break window | games | share | median break | loser dead | winner dead | loser work | winner work | loser walk | winner walk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| farm | 65 | 51% | 222 | 15% | 4% | 22% | 28% | 52% | 53% |
| fight | 55 | 43% | 365 | 26% | 7% | 18% | 26% | 47% | 52% |
| camp | 1 | 1% | 661 | 30% | 0% | 34% | 47% | 27% | 40% |
| bank | 7 | 5% | 811 | - | - | - | - | - | - |

Turn shares are over the windows of that cause (work = camp, hold, tribute). A farm window with a high loser dead share is a farm deficit that follows deaths; one with level dead shares is out-farming with bodies alive.

Break round: median 310 (p25 147, p75 572); 0 never level, 33 in rounds 1-150, 42 in 151-400, 53 after 400.

| component (winner advantage, gems) | whole game | break window |
| --- | --- | --- |
| farm | 317 | 87.1 |
| fight | 421 | 237 |
| camp | 2.1 | 2.8 |
| bank | -7.4 | - |

Turn mix in the break windows (loser vs winner):

| class | loser | winner |
| --- | --- | --- |
| dead | 19.9% | 5.2% |
| lost | 0.1% | 0.2% |
| fight | 3.4% | 3.6% |
| tribute | 0.8% | 3.9% |
| recall | 3.6% | 4.6% |
| teleport | 0.0% | 0.0% |
| camp | 15.4% | 18.2% |
| hold | 3.7% | 5.1% |
| walk_bag | 22.3% | 26.6% |
| walk | 26.9% | 25.9% |
| spawn | 1.3% | 1.5% |
| wait_camp | 1.4% | 2.5% |
| wait_altar | 0.0% | 1.7% |
| idle | 1.2% | 1.2% |

Loser deaths in the break windows: 173 over 128 games (1.35 a game), by type Prism 48, Cassi 30, Issac 21, Willow 14, Vesper Vale 14, Ryth 11, Marcella 9, Heart of Ruin 7, Vendetta 6, Ren 5, Tavi 4, Varg 2, Stellar 2; bag at death median 11, 57 with 50+.

What opened the window: the loser's largest-bag death within 10 rounds of the break, if any:

| trigger | games | share |
| --- | --- | --- |
| no loser death within 10 rounds | 70 | 55% |
| Prism died with 200+ gems | 17 | 13% |
| ended holding the larger wealth | 7 | 5% |
| Prism died with 50-199 gems | 7 | 5% |
| Cassi died with <50 gems | 6 | 5% |
| Issac died with <50 gems | 4 | 3% |
| Ren died with <50 gems | 3 | 2% |
| Willow died with <50 gems | 2 | 2% |
| Prism died with <50 gems | 2 | 2% |
| Cassi died with 50-199 gems | 2 | 2% |
| Vesper Vale died with <50 gems | 1 | 1% |
| Vesper Vale died with 50-199 gems | 1 | 1% |

(6 more rows in `macro-triggers.csv`)

Largest windows (gap = winner minus loser wealth at the window's end):

| game / break | map | cause | gap | window components | loser deaths in the window |
| --- | --- | --- | --- | --- | --- |
| 4e007ea7c5c7aa71 r1317 | sunburst | fight | 2169 | farm +15 fight +2278 camp +0 | r1318 Prism bag 1103 by Prism; r1340 Vesper Vale bag 0 by Prism; r1352 Cassi bag 0 by Prism; r1358 Ryth bag 36 by Prism |
| 9af6ba6844bffaa0 r984 | eight | fight | 1672 | farm +0 fight +1740 camp +0 | r985 Prism bag 833 by Prism; r1033 Vesper Vale bag 0 by Prism; r1073 Ryth bag 37 by Prism |
| 07392d3aa07e8439 r472 | adgato-gemcombat4 | fight | 1626 | farm +67 fight +1582 camp +0 | r479 Prism bag 686 by Prism; r502 Marcella bag 70 by Prism; r507 Tavi bag 35 by Prism |
| 1a53508aef8b96ee r941 | adgato-gemcombat1 | fight | 1620 | farm +21 fight +1626 camp +0 | r942 Prism bag 813 by Prism; r942 Marcella bag 0 by Prism; r1015 Marcella bag 0 by Prism |
| b29a405bf7050285 r610 | pinwheel | fight | 1404 | farm -21 fight +1430 camp +0 | r613 Prism bag 686 by Prism; r647 Cassi bag 4 by Prism; r678 Willow bag 25 by Issac |
| 3e14056889eb2885 r502 | hollows | fight | 1172 | farm +148 fight +1062 camp +0 | r503 Cassi bag 0 by Prism; r503 Prism bag 505 by Prism; r527 Tavi bag 26 by Prism |
| c5bd21512c1a1d42 r736 | dunes | fight | 1121 | farm +178 fight +1242 camp +0 | r737 Prism bag 621 by Prism; r739 Heart of Ruin bag 0 by Prism; r749 Cassi bag 0 by Prism; r750 Willow bag 0 by Prism |
| dc752b321c68ad46 r738 | uncharted-lands | fight | 1070 | farm +130 fight +982 camp +0 | r739 Cassi bag 0 by Prism; r739 Prism bag 491 by Prism; r754 Ryth bag 0 by Prism; r762 Vesper Vale bag 0 by Prism |
| 656bf4a601ee85dc r317 | gem-caverns | fight | 1001 | farm +7 fight +994 camp +0 | r398 Marcella bag 161 by Prism; r406 Cassi bag 168 by Prism |
| 5db4c0f488e86898 r1262 | vault | fight | 979 | farm +432 fight +920 camp +0 | r1263 Issac bag 24 by Issac |
| d9ca2423cbbe2612 r175 | stalactites | fight | 951 | farm +358 fight +606 camp +0 | r238 Cassi bag 0 by Prism; r243 Prism bag 295 by Prism; r255 Stellar bag 8 by Prism |
| 923d73083d01616b r466 | treasure-box | fight | 883 | farm +93 fight +790 camp +0 | r489 Prism bag 395 by Prism |
| c80107034b26bada r183 | showdown | fight | 831 | farm +261 fight +582 camp +0 | r184 Prism bag 270 by Prism; r257 Cassi bag 0 by Prism |
| 517dbb6bd95f46d3 r543 | ambush | fight | 784 | farm +19 fight +814 camp +0 | r544 Prism bag 407 by Prism |
| 07985783285c2de2 r390 | two-kingdoms | fight | 743 | farm -178 fight +954 camp +0 | r406 Vendetta bag 229 by Prism; r417 Vesper Vale bag 131 by Prism; r429 Stellar bag 117 by Prism |
| f1e5e63d32d9b887 r327 | honeycomb | fight | 732 | farm +302 fight +444 camp +0 | r329 Cassi bag 0 by Prism; r337 Prism bag 211 by Prism |
| 60e12c9ad2ba1a46 r924 | waves | fight | 732 | farm +91 fight +652 camp +0 | r925 Prism bag 291 by Prism; r933 Heart of Ruin bag 88 by Prism; r934 Vesper Vale bag 35 by Prism |
| 92ce4c2ca75369a9 r1046 | terraces | fight | 679 | farm -41 fight +738 camp +0 | r1047 Cassi bag 70 by Heart of Ruin; r1069 Prism bag 277 by Prism |
| bbac8b734d040052 r365 | fault-lines | fight | 653 | farm +19 fight +832 camp +0 | r366 Prism bag 416 by Prism |
| 9cbf734a98ed22e4 r355 | bullseye | fight | 613 | farm +150 fight +468 camp +0 | r404 Issac bag 0 by Prism; r407 Willow bag 0 by Prism; r412 Prism bag 234 by Prism |
| f148cc299e8ab50c r247 | ambush-field | fight | 598 | farm +207 fight +444 camp +0 | r248 Prism bag 222 by Prism; r342 Cassi bag 0 by Prism |
| ba65207c151a66eb r191 | passageway | fight | 584 | farm +90 fight +526 camp +0 | r211 Vesper Vale bag 99 by Prism; r289 Prism bag 178 by Prism |
| 8e8e28c10a03ecfc r451 | contours | fight | 537 | farm +173 fight +366 camp +0 | r488 Prism bag 183 by Prism |
| e22c82ae7d91303f r262 | tidepools | fight | 511 | farm +235 fight +292 camp +0 | r296 Prism bag 146 by Prism |
| a28e2f7cb1b046d5 r284 | adgato-gemcombat2 | fight | 475 | farm +112 fight +364 camp +0 | r376 Prism bag 105 by Prism; r383 Issac bag 49 by Prism; r384 Willow bag 0 by Prism |
