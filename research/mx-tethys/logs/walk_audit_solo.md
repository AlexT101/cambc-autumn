# Walk audit: 2720 games, 5.5 champions per game, 3444 champion-rounds per game

## 1. Walk legs

192 legs per game, 1801 walking rounds per game (52.3% of champion-rounds); mean 9.4 rounds, 9.3 steps; median 5.

Walking rounds by leg length: 1-4 9.4%, 5-9 14.5%, 10-19 28.4%, 20-39 30.0%, 40+ 17.6%

| origin | destination | legs/game | rounds/leg | steps/leg | rounds/game | % of walking | % with bag |
|---|---|---|---|---|---|---|---|
| recall arrival | idle | 7.1 | 16.2 | 16.1 | 115 | 6.4 | 61.4 |
| recall arrival | camp:Wolf | 8.0 | 13.9 | 13.9 | 112 | 6.2 | 66.0 |
| camp | camp:Wolf | 21.1 | 5.2 | 5.2 | 111 | 6.2 | 39.0 |
| camp | idle | 7.8 | 12.9 | 12.8 | 101 | 5.6 | 32.9 |
| recall arrival | camp:Elk | 5.8 | 15.8 | 15.8 | 91.4 | 5.1 | 60.8 |
| camp | camp:Elk | 12.0 | 5.5 | 5.5 | 66.3 | 3.7 | 37.5 |
| payout | idle | 4.8 | 12.9 | 12.8 | 62.1 | 3.4 | 64.8 |
| recall arrival | altar | 3.8 | 16.3 | 16.3 | 61.7 | 3.4 | 100.0 |
| recall cancelled | idle | 4.0 | 14.0 | 14.0 | 56.4 | 3.1 | 56.5 |
| payout | altar | 5.2 | 10.2 | 10.2 | 53.5 | 3.0 | 56.0 |
| payout | camp:Wolf | 5.3 | 8.7 | 8.7 | 46.2 | 2.6 | 70.8 |
| left hold | idle | 2.6 | 13.6 | 13.5 | 35.3 | 2.0 | 37.9 |
| left hold | camp:Wolf | 3.8 | 9.2 | 9.2 | 35.2 | 2.0 | 34.8 |
| payout | camp:Elk | 3.3 | 10.2 | 10.2 | 33.3 | 1.8 | 74.7 |
| recall cancelled | camp:Wolf | 3.1 | 10.6 | 10.6 | 33.1 | 1.8 | 67.8 |
| camp | camp:GemCl | 4.6 | 7.1 | 7.1 | 32.6 | 1.8 | 34.6 |
| idle | idle | 2.5 | 11.8 | 11.7 | 29.5 | 1.6 | 37.4 |
| tribute | idle | 2.3 | 12.5 | 12.4 | 29.2 | 1.6 | 0.0 |
| recall arrival | camp:GemCl | 1.5 | 18.2 | 18.1 | 27.2 | 1.5 | 65.0 |
| camp | recall | 4.8 | 5.7 | 5.6 | 26.9 | 1.5 | 33.5 |
| recall cancelled | camp:Elk | 2.1 | 12.3 | 12.3 | 26.1 | 1.4 | 67.9 |
| start | camp:Elk | 1.9 | 12.6 | 12.5 | 23.5 | 1.3 | 0.0 |

By origin: recall arrival 27.2%, camp 24.5%, payout 14.7%, recall cancelled 10.5%, left hold 7.3%, idle 5.6%, tribute 5.3%, start 3.6%, fight 0.6%, spawn 0.3%, respawn 0.3%, teleport 0.0%

By dest: camp 53.7%, idle 24.1%, altar 9.7%, hold 5.2%, recall 5.0%, end 1.3%, fight 0.7%, teleport 0.2%, died 0.1%, spawn 0.0%

## 2. Walks to a camp: detours and pass-bys

(0.2 to-camp legs per game go to a group with no walking path (dash-only), left out.)

| legs | per game | % not to nearest available | extra steps (those) | extra steps/game | % nearer had >= gems | dest gems | nearer gems | % passed an available group | gems passed | % ally on same group |
|---|---|---|---|---|---|---|---|---|---|---|
| all to-camp legs | 102.9 | 33.3 | 9.3 | 318 | 38.1 | 27.8 | 36.6 | 15.8 | 47.5 | 65.2 |
| destination available at start | 32.2 | 37.9 | 10.1 | 123 | 47.4 | 21.1 | 34.6 | 18.5 | 44.9 | 22.8 |
| destination respawning/cleared at start | 70.8 | 31.2 | 8.8 | 194 | 33.0 | 31.4 | 37.6 | 14.6 | 49.0 | 84.4 |

Available destinations by type:

| type | legs | % not nearest | extra steps | steps/leg | % passed another |
|---|---|---|---|---|---|
| Wolf | 37007 | 35.7 | 9.5 | 8.6 | 16.9 |
| Elk | 17114 | 43.6 | 10.8 | 10.5 | 21.7 |
| GemCl | 14967 | 43.7 | 10.7 | 9.3 | 22.1 |
| GoldCl | 14594 | 30.3 | 9.0 | 7.2 | 15.0 |
| Golem | 2982 | 39.4 | 11.2 | 10.7 | 19.1 |
| Monolith | 788 | 46.8 | 15.9 | 18.2 | 17.3 |

## 3. Crews

Camp-hit champion-rounds on a group another ally hits the same round: 58.0%; to-camp legs whose group an ally works or heads to meanwhile: 65.2%; mean clear 12.3 rounds from first hit.

## 4. Banking trips (last group worked -> altar -> next group worked)

15.2 tributes per game, mean bag 68.5 (median 29); 31.8% under 20 gems.

| tributes | n | rounds to altar | rounds back | trip (no recall) | direct walk last->next group | overhead/trip | overhead rounds/game | best walk via any altar | recall+walk alt | % used altar 3+ farther than nearest | extra altar dist | % recall alt < actual | % recall alt < best walk | trip rounds per gem |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all | 41014 | 14.3 | 11.4 | 17.2 | 14.3 | 3.0 | 18.5 | 18.7 | 43.4 | 12.0 | 1.8 | 5.3 | 1.8 | 0.5 |
| bag < 20 | 13055 | 11.2 | 10.7 | 14.9 | 12.5 | 2.3 | 5.7 | 14.1 | 36.9 | 13.0 | 1.8 | 7.3 | 1.8 | 1.9 |
| bag 20-59 | 19128 | 13.6 | 11.4 | 17.1 | 14.7 | 2.4 | 6.8 | 19.7 | 45.2 | 12.5 | 1.9 | 4.2 | 1.9 | 0.7 |
| bag 60+ | 8831 | 20.6 | 12.3 | 23.8 | 17.3 | 6.5 | 6.0 | 28.2 | 55.4 | 9.4 | 1.6 | 3.5 | 1.7 | 0.2 |

Trips with a recall in them: 46.9%; next group is the same as the last: 9.4%.

## 5. Recalls

9.2 real recalls per champion per game (85.9% complete); 43.7% start on a capture tile (hold+recall).

Recall detour: recall rounds off a capture tile + walk spawn->next group - walk last group->next group = mean 0.3 rounds (n=113197; 313 rounds/game where positive; recall faster in 54.5%). Bag recalls then walked to an altar: 3.8/game taking 26.7 rounds (recall + walk) vs 24.7 to walk from the last group to its nearest altar; 31.4 rounds/game lost.

| recalls | per champion-game | walk dist from spawn at start | % with bag | % shop on arrival | rounds arrival -> next camp | walk-out distance | % back to the same group | recall+walk-out rounds/game |
|---|---|---|---|---|---|---|---|---|
| all completed | 7.9 | 24.6 | 53.0 | 57.0 | 20.6 | 18.5 | 7.0 | 1085 |
| hp < 50% | 1.3 | 29.8 | 42.2 | 44.2 | 22.2 | 22.6 | 15.0 | 183 |
| hp 50-80% | 1.3 | 27.3 | 49.0 | 62.6 | 21.0 | 20.1 | 4.9 | 180 |
| hp >= 80% | 5.4 | 22.7 | 56.5 | 58.6 | 20.1 | 17.1 | 5.7 | 722 |

## 6. Idle off spawn

181 idle-off rounds per game (5.3% of champion-rounds).

| where | rounds/game | % of idle | % in runs 1-2 | 3-9 | 10-49 | 50+ | respawn timer left at start |
|---|---|---|---|---|---|---|---|
| by respawning group | 98.7 | 54.5 | 22.9 | 56.9 | 13.2 | 7.0 | 10.7 |
| by live group (awake) | 24.8 | 13.7 | 6.1 | 58.1 | 9.5 | 26.3 | - |
| elsewhere | 22.8 | 12.6 | 13.3 | 41.6 | 24.7 | 20.5 | - |
| by live group (asleep) | 13.3 | 7.4 | 9.8 | 39.8 | 18.5 | 31.9 | - |
| by cleared group, unheld | 9.0 | 5.0 | 10.7 | 47.7 | 16.5 | 25.1 | - |
| by cleared group, held | 6.7 | 3.7 | 20.8 | 42.3 | 21.1 | 15.8 | - |
| at altar | 5.2 | 2.9 | 4.0 | 23.1 | 56.5 | 16.4 | - |
| at altar with bag | 0.3 | 0.2 | 7.7 | 20.5 | 28.5 | 43.3 | - |

## 7. Group utilisation

| groups | respawns | mean rounds up before first hit | gem-weighted | % never hit before game end |
|---|---|---|---|---|
| Q1 (nearest) | 62718 | 35.3 | 45.5 | 8.7 |
| Q2 | 47978 | 51.1 | 81.4 | 10.6 |
| Q3 | 45183 | 88.6 | 131 | 16.6 |
| Q4 (farthest) | 37762 | 326 | 348 | 54.2 |
| Wolf | 78811 | 122 | 97.1 | 23.0 |
| Elk | 37356 | 103 | 101 | 20.1 |
| Golem | 5280 | 155 | 162 | 26.6 |
| Monolith | 1959 | 495 | 501 | 68.2 |
| GemCl | 43115 | 54.0 | 42.1 | 12.1 |
| GoldCl | 27120 | 124 | - | 18.3 |

Captured 1060 gems per game of a supply bound of 2682 (every group farmed on cooldown: gems x rounds / (respawn + typical clear + 6)) = 39.5%; by side own 62.4% of 1129, mid 41.6% of 413, enemy 16.2% of 1139.

## 8. Opening

| metric | mean | median |
|---|---|---|
| round of first capture | 25.6 | 23.0 |
| round of first tribute | 177 | 136 |
| gems captured by r100 | 129 | 110 |
| gems captured by r200 | 310 | 272 |
| gems tributed by r200 | 68.9 | 43.0 |
| round reaching 1000 tributed | 618 | 566 |
| games not reaching 1000 | 21 |  |

## Examples

**Longest detours past a nearer available group**

- `replays/batch-20261113-142527-solo-mx-tethys-solo0-study-ref/1925-gen-shared-gems-6140100414000-12.repl26a` r1 Vesper Vale#0: camp:GoldCl (0 gems) at 169 steps, nearest available 17 steps (0 gems)
- `replays/batch-20261113-142527-solo-mx-tethys-solo0-study-ref/057-gen-classic-6140100001024-12.repl26a` r756 Issac#2: camp:GemCl (7 gems) at 176 steps, nearest available 28 steps (22 gems)
- `replays/batch-20261113-142527-solo-mx-tethys-solo0-study-ref/2694-mut-twisty-6140100217027-12.repl26a` r368 Issac#3: camp:GoldCl (0 gems) at 171 steps, nearest available 27 steps (200 gems)
- `replays/batch-20261113-142527-solo-mx-tethys-solo0-study-ref/2594-mut-road-of-riches-6140100717018-21.repl26a` r128 Heart of Ruin#10: camp:GemCl (21 gems) at 138 steps, nearest available 11 steps (22 gems)
- `replays/batch-20261113-142527-solo-mx-tethys-solo0-study-ref/908-gen-ladder-6140100400107-12.repl26a` r559 Issac#3: camp:GemCl (28 gems) at 149 steps, nearest available 22 steps (30 gems)

**Longest walk-outs after a recall**

- `replays/batch-20261113-142527-solo-mx-tethys-solo0-study-ref/2619-mut-spiral-moat-6140100517005-21.repl26a` Heart of Ruin#5: 1717 rounds from arrival to the next camp (distance 38)
- `replays/batch-20261113-142527-solo-mx-tethys-solo0-study-ref/390-gen-ladder-6140100000037-12.repl26a` Prism#2: 1585 rounds from arrival to the next camp (distance 9)
- `replays/batch-20261113-142527-solo-mx-tethys-solo0-study-ref/2622-mut-spiral-moat-6140100617049-12.repl26a` Vesper Vale#1: 1162 rounds from arrival to the next camp (distance 9)
- `replays/batch-20261113-142527-solo-mx-tethys-solo0-study-ref/1936-gen-shared-gems-6140100714002-12.repl26a` Cassi#0: 985 rounds from arrival to the next camp (distance 21)
- `replays/batch-20261113-142527-solo-mx-tethys-solo0-study-ref/1884-gen-monolith-only-6140100613001-21.repl26a` Willow#7: 806 rounds from arrival to the next camp (distance 5)

**Longest idle stretches**

- `replays/batch-20261113-142527-solo-mx-tethys-solo0-study-ref/2061-mut-05birthday-cake-6140100619021-12.repl26a` r26 Issac#1 idle 1975 rounds at (16, 27) (by live group (asleep))
- `replays/batch-20261113-142527-solo-mx-tethys-solo0-study-ref/2703-mut-vault-6140100317033-21.repl26a` r163 Tavi#8 idle 1816 rounds at (11, 15) (by respawning group)
- `replays/batch-20261113-142527-solo-mx-tethys-solo0-study-ref/2044-mut-05abandoned-buildings-6140100319007-21.repl26a` r31 Ryth#5 idle 1678 rounds at (73, 63) (by live group (awake))
- `replays/batch-20261113-142527-solo-mx-tethys-solo0-study-ref/2258-mut-boss-battle-6140100617000-21.repl26a` r502 Prism#9 idle 1499 rounds at (25, 33) (elsewhere)
- `replays/batch-20261113-142527-solo-mx-tethys-solo0-study-ref/1913-gen-shared-gems-6140100014000-12.repl26a` r499 Prism#3 idle 1466 rounds at (17, 21) (elsewhere)

**Longest banking trips**

- `replays/batch-20261113-142527-solo-mx-tethys-solo0-study-ref/338-gen-jungle-6140100007001-21.repl26a` r1110 Ryth#5: 2 gems, 853 rounds to the altar + 12 back (best walk 6, recall alt 14)
- `replays/batch-20261113-142527-solo-mx-tethys-solo0-study-ref/2014-gen-tiny-6140100711003-12.repl26a` r1221 Ren#5: 4 gems, 612 rounds to the altar + 0 back (best walk 25, recall alt 35)
- `replays/batch-20261113-142527-solo-mx-tethys-solo0-study-ref/667-gen-ladder-6140100200090-21.repl26a` r1432 Vendetta#5: 27 gems, 362 rounds to the altar + 33 back (best walk 72, recall alt 109)
- `replays/batch-20261113-142527-solo-mx-tethys-solo0-study-ref/2693-mut-treasure-box-6140100317058-21.repl26a` r1004 Ryth#5: 23 gems, 377 rounds to the altar + 0 back (best walk 32, recall alt 37)
- `replays/batch-20261113-142527-solo-mx-tethys-solo0-study-ref/2285-mut-canyons-6140100217000-12.repl26a` r558 Cassi#2: 14 gems, 371 rounds to the altar + 2 back (best walk 19, recall alt 53)

