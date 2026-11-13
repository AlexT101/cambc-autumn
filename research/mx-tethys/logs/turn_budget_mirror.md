# Turn budget: 2720 games from replays/batch-20261113-142259-ab-mx-tethys-mirror-study

Mirror mode: identical replays (a map pair swapped between two copies of one bot) count once; sides are the game winner (W) and loser (L).

Trace: 2 of 5440 team stdouts truncated (1 MiB cap or D lines end before the last round), 0 missing; 0.0% of champion-rounds have no D line (branch `?`); 0 D-line champion ids outside the printing team.

## 1. Turn budget (% of champion-rounds)

| class | all W | all L | r1-150 W | r1-150 L | r151-400 W | r151-400 L | r401-800 W | r401-800 L | r801+ W | r801+ L | r1-300 W | r1-300 L |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dead | 4.8 | 13.8 | 1.9 | 3.3 | 4.1 | 8.4 | 5.7 | 16.3 | 6.9 | 26.6 | 2.8 | 5.4 |
| fight | 3.5 | 3.4 | 3.2 | 3.2 | 3.1 | 3.1 | 3.5 | 3.4 | 4.3 | 3.9 | 3.2 | 3.1 |
| tribute | 4.5 | 1.3 | 0.5 | 0.5 | 2.2 | 1.4 | 6.0 | 1.9 | 9.0 | 1.1 | 1.1 | 0.9 |
| recall | 4.4 | 3.9 | 4.5 | 4.3 | 5.4 | 4.9 | 4.2 | 3.7 | 3.0 | 2.2 | 5.0 | 4.7 |
| hold+recall | 2.1 | 1.9 | 2.5 | 2.4 | 2.7 | 2.5 | 1.8 | 1.6 | 1.2 | 0.9 | 2.7 | 2.6 |
| teleport | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| camp | 18.1 | 16.5 | 28.3 | 27.7 | 21.3 | 19.8 | 15.1 | 13.3 | 9.5 | 7.0 | 25.4 | 24.4 |
| hold | 4.5 | 4.0 | 4.9 | 4.7 | 5.1 | 4.5 | 4.4 | 3.8 | 3.5 | 3.0 | 5.0 | 4.6 |
| spawn-heal | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| bag->altar | 13.5 | 12.7 | 8.8 | 8.5 | 15.8 | 14.8 | 15.8 | 14.7 | 10.5 | 10.3 | 12.0 | 11.4 |
| bag->camp | 6.3 | 6.1 | 5.6 | 5.4 | 8.6 | 8.0 | 6.5 | 6.2 | 3.4 | 3.5 | 7.1 | 6.8 |
| bag-other | 3.1 | 3.7 | 2.0 | 2.0 | 3.3 | 3.5 | 3.5 | 4.3 | 3.1 | 4.4 | 2.6 | 2.7 |
| empty->camp | 18.0 | 17.2 | 26.7 | 26.4 | 16.8 | 16.7 | 16.2 | 15.2 | 15.0 | 12.9 | 21.9 | 21.8 |
| empty->spawn | 3.1 | 3.5 | 2.5 | 2.6 | 2.5 | 2.8 | 3.2 | 3.5 | 4.5 | 5.1 | 2.5 | 2.7 |
| empty-other | 6.6 | 8.0 | 6.1 | 6.4 | 5.4 | 6.0 | 6.8 | 8.1 | 8.6 | 12.1 | 5.7 | 6.1 |
| idle-off | 7.1 | 3.8 | 2.4 | 2.4 | 3.6 | 3.2 | 7.0 | 3.8 | 16.5 | 5.8 | 2.8 | 2.7 |
| idle-spawn | 0.4 | 0.4 | 0.1 | 0.1 | 0.2 | 0.2 | 0.3 | 0.3 | 1.0 | 1.0 | 0.1 | 0.1 |

By attack type (all rounds):

| class | melee W | melee L | ranged W | ranged L |
|---|---|---|---|---|
| dead | 5.8 | 14.7 | 4.1 | 13.1 |
| fight | 4.1 | 3.8 | 3.1 | 3.0 |
| tribute | 2.2 | 1.3 | 6.2 | 1.4 |
| recall | 4.7 | 4.2 | 4.1 | 3.7 |
| hold+recall | 2.4 | 2.1 | 1.8 | 1.7 |
| teleport | 0.0 | 0.0 | 0.0 | 0.0 |
| camp | 19.6 | 17.6 | 17.1 | 15.7 |
| hold | 4.0 | 3.4 | 4.9 | 4.4 |
| spawn-heal | 0.0 | 0.0 | 0.0 | 0.0 |
| bag->altar | 13.0 | 12.0 | 13.8 | 13.3 |
| bag->camp | 5.6 | 5.2 | 6.8 | 6.6 |
| bag-other | 3.1 | 3.5 | 3.1 | 3.8 |
| empty->camp | 18.8 | 17.5 | 17.4 | 16.9 |
| empty->spawn | 2.7 | 3.1 | 3.4 | 3.7 |
| empty-other | 6.2 | 7.8 | 6.9 | 8.1 |
| idle-off | 6.9 | 3.2 | 7.2 | 4.2 |
| idle-spawn | 0.7 | 0.6 | 0.2 | 0.2 |

By champion type (% of that type's champion-rounds; walk = all bag/empty walking):

| type | side | rounds | dead | fight | camp | hold | tribute | recall | spawn-heal | idle-spawn | idle-off | walk |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Cassi | W | 2252206 | 8.1 | 2.6 | 19.8 | 3.7 | 1.7 | 3.9 | 0.0 | 0.2 | 4.7 | 54.0 |
| Cassi | L | 2252206 | 19.0 | 2.6 | 16.8 | 3.0 | 0.8 | 3.1 | 0.0 | 0.1 | 3.3 | 50.1 |
| Heart of Ruin | W | 696520 | 4.5 | 6.2 | 19.6 | 4.0 | 1.8 | 4.3 | 0.0 | 1.0 | 4.5 | 52.0 |
| Heart of Ruin | L | 696520 | 9.0 | 5.7 | 18.5 | 3.4 | 1.3 | 3.9 | 0.0 | 1.3 | 3.1 | 51.9 |
| Issac | W | 2252206 | 8.1 | 2.6 | 21.3 | 3.7 | 1.9 | 5.0 | 0.0 | 1.0 | 5.1 | 49.5 |
| Issac | L | 2252206 | 19.0 | 2.3 | 17.9 | 3.0 | 0.9 | 4.1 | 0.0 | 1.0 | 3.0 | 47.3 |
| Marcella | W | 370355 | 4.7 | 6.7 | 11.6 | 5.3 | 3.2 | 4.3 | 0.0 | 0.1 | 11.7 | 50.0 |
| Marcella | L | 370355 | 18.0 | 6.4 | 9.8 | 4.2 | 1.8 | 3.5 | 0.0 | 0.1 | 3.5 | 50.7 |
| Prism | W | 1918833 | 0.9 | 4.2 | 12.2 | 8.3 | 18.0 | 4.7 | 0.0 | 0.1 | 4.2 | 45.6 |
| Prism | L | 1918833 | 13.7 | 4.1 | 12.3 | 8.0 | 2.4 | 4.5 | 0.0 | 0.0 | 3.3 | 50.0 |
| Ren | W | 274220 | 4.6 | 5.0 | 21.1 | 3.6 | 2.3 | 4.7 | 0.0 | 0.2 | 8.0 | 47.7 |
| Ren | L | 274220 | 12.7 | 4.9 | 19.8 | 3.1 | 1.3 | 4.2 | 0.0 | 0.2 | 4.0 | 47.1 |
| Ryth | W | 806103 | 4.6 | 6.9 | 16.4 | 4.5 | 2.4 | 3.9 | 0.0 | 0.1 | 14.1 | 44.2 |
| Ryth | L | 806103 | 16.4 | 6.8 | 15.3 | 4.1 | 1.3 | 3.5 | 0.0 | 0.1 | 3.3 | 46.6 |
| Stellar | W | 95455 | 4.4 | 2.2 | 17.9 | 4.1 | 3.2 | 4.8 | 0.0 | 0.1 | 10.8 | 50.3 |
| Stellar | L | 95455 | 12.2 | 2.0 | 16.9 | 4.0 | 1.6 | 4.5 | 0.0 | 0.0 | 5.0 | 51.7 |
| Tavi | W | 206462 | 5.9 | 5.8 | 18.6 | 8.1 | 2.8 | 3.0 | 0.0 | 0.0 | 7.1 | 47.0 |
| Tavi | L | 206462 | 15.3 | 5.5 | 15.6 | 7.2 | 1.3 | 2.5 | 0.0 | 0.0 | 3.9 | 47.1 |
| Varg | W | 345772 | 2.6 | 1.7 | 21.1 | 3.5 | 2.3 | 5.0 | 0.0 | 0.2 | 3.5 | 57.3 |
| Varg | L | 345772 | 4.9 | 1.7 | 20.3 | 3.3 | 1.8 | 4.9 | 0.0 | 0.0 | 2.6 | 57.8 |
| Vendetta | W | 487477 | 2.8 | 2.0 | 21.7 | 4.4 | 3.1 | 5.8 | 0.0 | 0.5 | 4.9 | 50.1 |
| Vendetta | L | 487477 | 5.6 | 1.9 | 20.9 | 3.9 | 2.2 | 5.7 | 0.0 | 0.1 | 4.0 | 51.4 |
| Vesper Vale | W | 1521488 | 2.2 | 4.4 | 22.3 | 5.6 | 4.1 | 4.6 | 0.0 | 0.1 | 9.5 | 43.0 |
| Vesper Vale | L | 1521488 | 7.5 | 3.9 | 21.5 | 5.0 | 2.3 | 4.4 | 0.0 | 0.4 | 4.2 | 46.8 |
| Willow | W | 1468429 | 4.0 | 0.9 | 13.5 | 0.9 | 0.3 | 3.2 | 0.0 | 0.2 | 12.5 | 64.3 |
| Willow | L | 1468429 | 9.1 | 1.2 | 12.6 | 1.0 | 0.1 | 2.8 | 0.0 | 0.3 | 6.6 | 66.1 |

Bot branch (D lines), % of champion-rounds:

| branch | all W | all L | r1-300 W | r1-300 L |
|---|---|---|---|---|
| `-` | 4.8 | 13.8 | 2.8 | 5.4 |
| `?` | 0.0 | 0.0 | 0.0 | 0.0 |
| `A` | 0.0 | 0.0 | 0.0 | 0.0 |
| `B` | 6.1 | 5.0 | 1.9 | 1.9 |
| `C` | 1.6 | 1.4 | 1.6 | 1.4 |
| `E` | 0.0 | 0.6 | 0.0 | 0.0 |
| `F` | 58.7 | 56.3 | 71.9 | 69.8 |
| `G` | 1.7 | 0.9 | 0.2 | 0.2 |
| `H` | 0.6 | 0.5 | 0.7 | 0.7 |
| `K` | 2.0 | 1.8 | 2.3 | 2.3 |
| `P` | 3.9 | 3.5 | 4.5 | 4.2 |
| `Q` | 1.5 | 1.4 | 2.1 | 2.0 |
| `R` | 4.7 | 6.2 | 4.1 | 4.8 |
| `S` | 0.0 | 0.0 | 0.0 | 0.0 |
| `T` | 3.7 | 0.9 | 0.7 | 0.5 |
| `U` | 4.1 | 1.6 | 0.0 | 0.0 |
| `W` | 0.1 | 0.0 | 0.0 | 0.0 |
| `X` | 0.1 | 0.2 | 0.2 | 0.2 |
| `h` | 5.6 | 5.3 | 6.4 | 6.2 |
| `k` | 0.6 | 0.5 | 0.6 | 0.5 |
| `r` | 0.0 | 0.0 | 0.0 | 0.0 |

Branch x replay class (both sides pooled; % of the branch's rounds, cells under 1% blank):

| branch | n | dead | fight | tribute | recall | hold+recall | teleport | camp | hold | spawn-heal | bag->altar | bag->camp | bag-other | empty->camp | empty->spawn | empty-other | idle-off | idle-spawn |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `-` | 2357043 | 100 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| `?` | 10822 | 3 | 2 | 30 |  |  |  |  | 3 |  |  |  |  | 1 |  |  | 58 | 1 |
| `A` | 62 |  | 35 |  | 2 |  |  |  |  |  | 6 |  | 13 | 18 | 6 | 19 |  |  |
| `B` | 1412492 |  | 4 | 6 |  |  |  | 3 |  |  | 68 | 3 | 7 |  |  |  | 7 |  |
| `C` | 381877 |  | 21 |  |  |  |  |  |  |  | 16 | 5 | 11 | 14 | 6 | 24 |  |  |
| `E` | 87552 |  | 32 |  |  |  |  |  |  |  | 16 |  | 3 | 6 | 2 | 39 | 1 |  |
| `F` | 14601357 |  | 2 |  | 2 |  |  | 27 | 2 |  | 15 | 10 | 3 | 25 | 2 | 8 | 4 |  |
| `G` | 321749 |  | 2 |  | 1 |  |  | 17 |  |  | 5 | 2 | 2 | 30 | 7 | 16 | 18 |  |
| `H` | 147298 |  |  |  | 99 |  |  |  |  |  |  |  |  |  |  |  |  |  |
| `K` | 485388 |  |  |  | 99 |  |  |  |  |  |  |  |  |  |  |  |  |  |
| `P` | 944437 |  | 3 |  |  | 10 |  | 3 | 84 |  |  |  |  |  |  |  |  |  |
| `Q` | 376215 |  |  |  |  | 100 |  |  |  |  |  |  |  |  |  |  |  |  |
| `R` | 1387308 |  | 19 |  | 3 |  |  |  |  |  | 7 | 6 | 18 | 15 | 26 | 5 |  |  |
| `S` | 4862 |  | 2 | 24 | 7 |  |  |  |  |  | 17 | 12 | 17 | 6 | 13 |  |  |  |
| `T` | 590468 |  |  | 99 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| `U` | 716550 |  | 5 |  |  |  |  |  |  |  | 2 |  |  | 3 | 4 | 20 | 65 |  |
| `W` | 15139 |  | 16 | 30 |  |  |  |  |  |  |  |  |  |  |  |  | 54 |  |
| `X` | 36424 |  | 9 |  |  |  |  |  | 13 |  | 7 | 5 | 8 | 21 | 5 | 32 |  |  |
| `h` | 1374782 |  |  |  |  |  |  | 21 |  |  | 3 | 1 | 2 | 34 | 10 | 20 | 8 |  |
| `k` | 134896 |  |  |  | 99 |  |  |  |  |  |  |  |  |  |  |  |  |  |
| `r` | 4331 |  | 14 |  | 1 |  |  | 1 |  |  | 13 | 6 | 16 | 1 | 3 |  | 43 |  |

Replay class -> bot branches (pooled; % of the class's rounds, top 4):

| class | n | branches |
|---|---|---|
| dead | 2357979 | `-` 100, `F` 0, `R` 0, `?` 0 |
| fight | 871958 | `F` 40, `R` 30, `C` 9, `B` 7 |
| tribute | 747209 | `T` 78, `B` 11, `F` 9, `W` 1 |
| recall | 1046194 | `K` 46, `F` 22, `H` 14, `k` 13 |
| hold+recall | 504231 | `Q` 74, `P` 18, `F` 6, `K` 1 |
| teleport | 2052 | `F` 89, `B` 9, `R` 1, `P` 0 |
| camp | 4394268 | `F` 91, `h` 7, `G` 1, `B` 1 |
| hold | 1082187 | `P` 73, `F` 25, `X` 0, `R` 0 |
| spawn-heal | 166 | `H` 67, `F` 19, `B` 7, `C` 4 |
| bag->altar | 3324054 | `F` 64, `B` 29, `R` 3, `C` 2 |
| bag->camp | 1569798 | `F` 89, `R` 5, `B` 3, `C` 1 |
| bag-other | 862935 | `F` 50, `R` 29, `B` 11, `C` 5 |
| empty->camp | 4462877 | `F` 81, `h` 11, `R` 5, `G` 2 |
| empty->spawn | 837366 | `R` 42, `F` 31, `h` 17, `U` 4 |
| empty-other | 1855091 | `F` 63, `h` 15, `U` 8, `C` 5 |
| idle-off | 1380272 | `F` 45, `U` 34, `h` 8, `B` 7 |
| idle-spawn | 92415 | `F` 97, `B` 2, `C` 0, `U` 0 |

## 2. Earnings (per game per side unless noted)

| metric | W | L |
|---|---|---|
| gems captured | 1089 | 879 |
| gems tributed | 1103 | 382 |
| gems taken by kills | 307 | 49.5 |
| gems lost at death to champions | 47.2 | 289 |
| gems lost at death to camps | 3.2 | 6.3 |
| gold earned (lifetime) | 5973 | 4401 |
| r1-300 gems captured | 410 | 357 |
| r1-300 gems tributed | 114 | 93.4 |
| r1-300 gems lost at death | 7.0 | 31.6 |
| gems captured per camp-hit round | 1.3 | 1.1 |
| gems captured per hold round | 5.2 | 4.7 |
| gems captured per (camp+hold) round | 1.0 | 0.9 |
| gems tributed per 100 alive rounds | 24.8 | 9.5 |
| mean bag carried per alive round | 84.8 | 42.1 |
| % alive rounds carrying 30+ | 23.2 | 20.4 |
| tributes per 1000 alive rounds | 3.8 | 2.3 |
| mean bag at tribute | 64.8 | 40.9 |
| walk steps per tributed gem | 2.6 | 7.4 |
| bag-walk rounds per tributed gem | 1.0 | 2.7 |
| bag-walk rounds just before a tribute (mean trip) | 7.6 | 9.2 |
| idle-off rounds in stretches of 50+ (% of idle-off) | 22.9 | 12.6 |
| idle-off rounds in 50+ stretches by branch at its start, per game | `U` 59.1, `F` 11.2, `B` 1.8, `W` 1.7 | `F` 10.9, `U` 10.3, `B` 0.6, `W` 0.2 |
| altar locks placed / tribute attempts blocked, per game | 3.39 / 0.00 | 4.42 / 0.00 |
| real recalls per game (completed) | 57.1 (46.7) | 50.3 (41.8) |
| tribute cancels per game (cause) | death 0.04, lock 1.60, manual 3.04, stun 3.99 | death 0.06, lock 0.26, manual 1.60, stun 0.50 |

By phase:

| per game | side | r1-150 | r151-400 | r401-800 | r801+ |
|---|---|---|---|---|---|
| gems captured | W | 174 | 400 | 376 | 140 |
| gems captured | L | 159 | 329 | 291 | 99.8 |
| gems tributed | W | 25.8 | 196 | 582 | 299 |
| gems tributed | L | 24.6 | 128 | 181 | 49.2 |
| alive champion-rounds | W | 812 | 1308 | 1446 | 878 |
| alive champion-rounds | L | 800 | 1250 | 1283 | 692 |

Real recalls (completed or lasting 2+ rounds; feints excluded) by the branch at their start:

| side | `F` | `P` | `R` | `B` | `G` | `S` | `C` | `U` | `h` | `E` | `W` | `X` | `?` | `-` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| W | 30.6/g, 81.1% done, 51.7% bag, 22.2 from spawn | 17.6/g, 86.6% done, 47.5% bag, 22.8 from spawn | 6.7/g, 76.1% done, 39.5% bag, 24.2 from spawn | 0.6/g, 70.9% done, 100.0% bag, 24.5 from spawn | 0.9/g, 74.3% done, 10.2% bag, 23.5 from spawn | 0.3/g, 87.9% done, 16.4% bag, 29.9 from spawn | 0.1/g, 60.9% done, 68.7% bag, 28.7 from spawn | 0.1/g, 34.6% done, 1.7% bag, 16.0 from spawn | 0.0/g, 56.5% done, 15.3% bag, 18.5 from spawn | 0.0/g, 66.7% done, 83.3% bag, 20.8 from spawn | 0.0/g, 85.7% done, 100.0% bag, 28.6 from spawn | 0.0/g, 9.1% done, 54.5% bag, 16.4 from spawn | 0.0/g, 66.7% done, 16.7% bag, 25.8 from spawn | 0.0/g, 100.0% done, 0.0% bag, 22.2 from spawn |
| L | 27.4/g, 81.7% done, 53.6% bag, 21.8 from spawn | 15.6/g, 88.8% done, 48.8% bag, 22.5 from spawn | 6.1/g, 75.9% done, 44.5% bag, 23.9 from spawn | 0.6/g, 75.9% done, 100.0% bag, 23.5 from spawn | 0.3/g, 72.3% done, 20.1% bag, 27.3 from spawn | 0.2/g, 88.1% done, 17.5% bag, 30.0 from spawn | 0.1/g, 61.2% done, 84.7% bag, 29.2 from spawn | 0.0/g, 57.5% done, 17.5% bag, 20.0 from spawn | 0.0/g, 55.1% done, 15.9% bag, 18.7 from spawn | 0.0/g, 70.6% done, 76.5% bag, 15.9 from spawn | - | 0.0/g, 0.0% done, 100.0% bag, 23.0 from spawn | 0.0/g, 100.0% done, 100.0% bag, 43.0 from spawn | 0.0/g, 100.0% done, 0.0% bag, 26.0 from spawn |

Bag size at tribute (% of tributes): W: 0-19 33.4, 20-39 33.2, 40-59 15.0, 60-79 6.8, 80-99 3.1, 100+ 8.5; L: 0-19 33.1, 20-39 35.7, 40-59 17.1, 60-79 6.8, 80-99 3.0, 100+ 4.3

## 3. Clears and captures

| group type | hitters | n | champ-turns | rounds | turns/gem | r1-300 turns/gem (n) | camp dmg/gem | own capture % | stolen % | uncaptured % | holders at payout | clear->payout | resets/clear | enemy also hit % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Monolith | 1 | 51 | 16.8 | 84.4 | 0.08 | - | 10.9 | 80.4 | 15.7 | 3.9 | 1.0 | 7.7 | 0.04 | 58.8 |
| Monolith | 2 | 141 | 42.5 | 113 | 0.20 | - | 23.5 | 88.7 | 9.9 | 1.4 | 1.1 | 7.7 | 0.09 | 39.7 |
| Monolith | 3+ | 736 | 97.1 | 99.7 | 0.44 | 0.88 (13) | 27.6 | 95.2 | 3.1 | 1.6 | 1.3 | 6.5 | 0.06 | 19.3 |
| Golem | 1 | 1886 | 12.2 | 20.6 | 0.22 | 0.19 (143) | 16.3 | 93.8 | 5.1 | 1.0 | 1.0 | 6.7 | 0.05 | 14.9 |
| Golem | 2 | 1254 | 20.7 | 27.7 | 0.36 | 0.40 (140) | 22.4 | 94.9 | 4.0 | 1.1 | 1.0 | 7.8 | 0.13 | 13.1 |
| Golem | 3+ | 3699 | 47.5 | 32.2 | 0.79 | 1.03 (1584) | 31.9 | 96.8 | 2.6 | 0.5 | 1.1 | 6.4 | 0.09 | 10.5 |
| Elk | 1 | 14344 | 11.0 | 16.9 | 0.36 | 0.43 (2397) | 15.5 | 96.5 | 2.8 | 0.7 | 1.0 | 6.6 | 0.11 | 10.0 |
| Elk | 2 | 13056 | 20.6 | 22.9 | 0.67 | 0.84 (3770) | 24.0 | 97.7 | 1.6 | 0.7 | 1.0 | 6.3 | 0.07 | 7.2 |
| Elk | 3+ | 28008 | 33.2 | 18.7 | 0.98 | 1.16 (15492) | 23.5 | 98.4 | 1.2 | 0.5 | 1.1 | 6.4 | 0.07 | 6.1 |
| Wolf | 1 | 39560 | 13.5 | 17.7 | 1.28 | 2.06 (11292) | 20.0 | 97.3 | 2.0 | 0.7 | 1.0 | 6.7 | 0.05 | 7.7 |
| Wolf | 2 | 35497 | 18.9 | 19.6 | 1.51 | 1.87 (13572) | 19.9 | 97.9 | 1.6 | 0.6 | 1.0 | 6.8 | 0.06 | 6.3 |
| Wolf | 3+ | 37022 | 24.4 | 15.9 | 1.58 | 1.78 (20056) | 17.3 | 98.1 | 1.5 | 0.4 | 1.1 | 6.8 | 0.09 | 6.3 |
| GemCl | 1 | 47505 | 3.5 | 3.9 | 0.25 | 0.25 (21835) | 0.0 | 94.9 | 3.3 | 1.8 | 1.0 | 9.3 | 0.08 | 4.8 |
| GemCl | 2 | 13805 | 5.8 | 8.1 | 0.24 | 0.23 (7164) | 0.0 | 95.5 | 3.4 | 1.0 | 1.0 | 8.3 | 0.16 | 6.4 |
| GemCl | 3+ | 4843 | 8.6 | 6.7 | 0.22 | 0.22 (2998) | 0.0 | 96.1 | 3.3 | 0.6 | 1.1 | 7.6 | 0.20 | 8.3 |
| GoldCl | 1 | 34114 | 3.3 | 4.9 | nan | nan (13772) | nan | 95.5 | 2.3 | 2.2 | 1.0 | 10.2 | 0.03 | 3.8 |
| GoldCl | 2 | 7661 | 4.7 | 19.9 | nan | nan (3512) | nan | 95.3 | 2.0 | 2.7 | 1.0 | 10.7 | 0.07 | 4.5 |
| GoldCl | 3+ | 1139 | 7.4 | 26.2 | nan | nan (542) | nan | 94.5 | 3.9 | 1.7 | 1.1 | 15.2 | 0.23 | 9.7 |

| side | clears/game | solo % | turns/gem | camp dmg/gem | own capture % | stolen from % | steals/game | holders at payout | clear->payout | resets/clear | contested/clear | camp deaths/clear |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| W | 55.4 | 48.5 | 0.82 | 16.2 | 97.3 | 1.7 | 1.39 | 1.0 | 7.8 | 0.07 | 0.01 | 0.005 |
| L | 49.1 | 48.2 | 0.87 | 16.2 | 96.0 | 2.8 | 0.93 | 1.0 | 7.7 | 0.08 | 0.01 | 0.004 |

Clears per game by group side (relative to the clearing team) and type:

| side | own Wolf | own Elk | own Golem | own Monolith | own GemCl | own GoldCl | mid Wolf | mid Elk | mid Golem | mid Monolith | mid GemCl | mid GoldCl | enemy Wolf | enemy Elk | enemy Golem | enemy Monolith | enemy GemCl | enemy GoldCl |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| W | 17.81 | 8.78 | 1.01 | 0.15 | 9.41 | 6.62 | 1.85 | 0.89 | 0.23 | 0.05 | 2.16 | 0.68 | 2.01 | 1.16 | 0.18 | 0.04 | 1.56 | 0.82 |
| L | 16.85 | 8.32 | 0.90 | 0.08 | 8.78 | 6.57 | 1.31 | 0.53 | 0.10 | 0.01 | 1.36 | 0.55 | 1.37 | 0.69 | 0.10 | 0.01 | 1.06 | 0.55 |

## 4. Supply (% of gem-weighted group-rounds in each state, groups by side relative to the team)

`asleep` = monsters up and asleep (nobody within range for 2 camp phases): available, unworked. `unclaimed` = cleared, nobody holding.

all:

| side | groups | asleep | awake | unclaimed | held | respawn |
|---|---|---|---|---|---|---|
| W | own | 58.1 | 8.3 | 1.8 | 2.2 | 29.6 |
| W | mid | 69.0 | 7.5 | 2.3 | 1.5 | 19.7 |
| W | enemy | 59.4 | 7.9 | 1.7 | 2.2 | 28.9 |
| L | own | 59.4 | 7.9 | 1.7 | 2.2 | 28.9 |
| L | mid | 69.0 | 7.5 | 2.3 | 1.5 | 19.7 |
| L | enemy | 58.1 | 8.3 | 1.8 | 2.2 | 29.6 |

r1-300:

| side | groups | asleep | awake | unclaimed | held | respawn |
|---|---|---|---|---|---|---|
| W | own | 61.6 | 7.9 | 1.5 | 2.5 | 26.5 |
| W | mid | 77.9 | 5.7 | 1.7 | 1.4 | 13.3 |
| W | enemy | 62.4 | 7.9 | 1.5 | 2.5 | 25.8 |
| L | own | 62.4 | 7.9 | 1.5 | 2.5 | 25.8 |
| L | mid | 77.9 | 5.7 | 1.7 | 1.4 | 13.3 |
| L | enemy | 61.6 | 7.9 | 1.5 | 2.5 | 26.5 |

By group type (unweighted % of group-rounds; own/mid/enemy relative to the side):

| side | type | own asleep | own awake | own unclaimed | mid asleep | mid awake | mid unclaimed | enemy asleep | enemy awake | enemy unclaimed |
|---|---|---|---|---|---|---|---|---|---|---|
| W | Wolf | 57.8 | 8.5 | 1.5 | 62.9 | 8.8 | 2.1 | 58.1 | 8.5 | 1.7 |
| L | Wolf | 58.1 | 8.5 | 1.7 | 62.9 | 8.8 | 2.1 | 57.8 | 8.5 | 1.5 |
| W | Elk | 46.6 | 9.9 | 1.7 | 58.1 | 10.0 | 2.8 | 46.6 | 10.0 | 1.8 |
| L | Elk | 46.6 | 10.0 | 1.8 | 58.1 | 10.0 | 2.8 | 46.6 | 9.9 | 1.7 |
| W | Golem | 55.3 | 8.4 | 1.2 | 64.0 | 8.7 | 2.3 | 56.7 | 8.4 | 1.3 |
| L | Golem | 56.7 | 8.4 | 1.3 | 64.0 | 8.7 | 2.3 | 55.3 | 8.4 | 1.2 |
| W | Monolith | 85.2 | 5.2 | 0.2 | 88.7 | 3.9 | 0.2 | 88.9 | 3.7 | 0.2 |
| L | Monolith | 88.9 | 3.7 | 0.2 | 88.7 | 3.9 | 0.2 | 85.2 | 5.2 | 0.2 |
| W | GemCl | 34.4 | 3.8 | 5.7 | 32.4 | 5.8 | 8.1 | 35.0 | 3.8 | 6.0 |
| L | GemCl | 35.0 | 3.8 | 6.0 | 32.4 | 5.8 | 8.1 | 34.4 | 3.8 | 5.7 |
| W | GoldCl | 54.6 | 2.5 | 8.0 | 59.2 | 3.0 | 11.1 | 53.7 | 2.6 | 7.8 |
| L | GoldCl | 53.7 | 2.6 | 7.8 | 59.2 | 3.0 | 11.1 | 54.6 | 2.5 | 8.0 |

Upper bound on gems left asleep per game (each asleep round = 1/(respawn+15) of a farm cycle): W: own 943, mid 409, enemy 955; L: own 955, mid 409, enemy 943

| side | own captures/game (gems) | mid captures/game (gems) | enemy captures/game (gems) | r1-300 own/mid/enemy |
|---|---|---|---|---|
| W | 43.6 (804) | 5.9 (161) | 5.8 (124) | 18.4/2.0/1.7 |
| L | 40.9 (734) | 3.7 (80) | 3.5 (65) | 17.6/1.4/1.2 |

## 5. Deaths

| metric | W | L |
|---|---|---|
| deaths/game (to champions + camps) | 2.4 + 0.27 | 8.0 + 0.28 |
| median first-death round (none = length+1) | 380 | 264 |
| % of games this side died first | 31.6 | 59.0 |
| % alone (no ally within 8) | 19.0 | 18.2 |
| % ally within 4 | 62.1 | 63.8 |
| % 2+ enemies within 8 | 72.0 | 82.5 |
| % on own ground | 55.6 | 74.8 |
| % on mid ground | 19.1 | 12.7 |
| % on enemy ground | 25.2 | 12.6 |
| % walking toward spawn (last 4 rounds) | 28.3 | 19.1 |
| % branch R in last 4 rounds | 78.4 | 65.8 |
| % carrying 30+ gems | 10.1 | 19.7 |
| mean enemies within 8 | 2.6 | 3.2 |
| mean gems carried at death | 15.9 | 33.5 |
| r1-300 deaths/game | 0.60 | 1.24 |

Gems lost at death by champion type, per game (% of the side's loss): W: Prism 20.2 (47.8%), Vesper Vale 4.9 (11.5%), Cassi 4.0 (9.6%), Ryth 2.8 (6.7%); L: Prism 205.7 (73.9%), Vesper Vale 20.8 (7.5%), Cassi 13.7 (4.9%), Ryth 9.9 (3.5%)

Deaths carrying 100+ gems: W 0.07/game holding 58.3% of gems lost; L 0.57/game holding 71.5% of gems lost

Branch at death (last D line): W: `R` 69.5%, `F` 13.3%, `E` 4.6%, `B` 2.8%, `U` 2.6%, `K` 1.8%; L: `R` 54.6%, `E` 27.3%, `F` 10.7%, `B` 2.3%, `U` 1.2%, `C` 0.9%

Deaths by (allies within 8, enemies within 8), per 10 games:

| side | allies\enemies | 0 | 1 | 2 | 3+ |
|---|---|---|---|---|---|
| W | 0 | 0.3 | 1.5 | 1.2 | 2.1 |
| W | 1 | 0.5 | 1.3 | 1.2 | 2.2 |
| W | 2 | 0.4 | 1.2 | 1.3 | 2.8 |
| W | 3+ | 0.8 | 1.5 | 2.0 | 6.3 |
| L | 0 | 0.5 | 3.6 | 3.1 | 7.9 |
| L | 1 | 0.6 | 3.4 | 3.6 | 13.0 |
| L | 2 | 0.5 | 2.6 | 3.1 | 14.3 |
| L | 3+ | 0.6 | 2.8 | 3.8 | 19.6 |

## 6. Kills and fights

| side | kills/game | r1-300 kills/game | fights/game | initiated % | won on kills % | lost on kills % | net bag gems/game |
|---|---|---|---|---|---|---|---|
| W | 8.0 | 1.12 | 30.0 | 49.4 | 22.4 | 6.5 | 235 |
| L | 2.4 | 0.50 | 30.0 | 50.6 | 6.5 | 22.4 | -235 |

By fight size (participants, side v enemy): fights per game, then net kills per fight (killed - lost):

| side | 1v1 | 1v2 | 1v3+ | 2v1 | 2v2 | 2v3+ | 3+v1 | 3+v2 | 3+v3+ |
|---|---|---|---|---|---|---|---|---|---|
| W | 15.57 / +0.09 | 2.69 / +0.14 | 0.73 / +0.13 | 3.17 / +0.26 | 2.00 / +0.22 | 1.11 / +0.23 | 1.34 / +0.54 | 1.32 / +0.50 | 2.09 / +0.45 |
| L | 15.57 / -0.09 | 3.17 / -0.26 | 1.34 / -0.54 | 2.69 / -0.14 | 2.00 / -0.22 | 1.32 / -0.50 | 0.73 / -0.13 | 1.11 / -0.23 | 2.09 / -0.45 |
| pooled | 15.57 / +0.00 | 2.93 / -0.08 | 1.03 / -0.30 | 2.93 / +0.08 | 2.00 / +0.00 | 1.21 / -0.17 | 1.03 / +0.30 | 1.21 / +0.17 | 2.09 / +0.00 |

By head-count difference at the start (own minus enemy champions alive within 8 of the fight, previous round end): fights per game / net kills per fight / % won on kills:

| side | -3 | -2 | -1 | 0 | 1 | 2 | 3 |
|---|---|---|---|---|---|---|---|
| W | 1.34 / +0.17 / 20.5 | 2.52 / +0.15 / 19.3 | 5.16 / +0.14 / 18.5 | 8.47 / +0.14 / 18.1 | 6.03 / +0.20 / 23.4 | 3.80 / +0.27 / 29.6 | 2.68 / +0.32 / 34.4 |
| L | 2.68 / -0.32 / 4.9 | 3.80 / -0.27 / 5.5 | 6.03 / -0.20 / 5.8 | 8.47 / -0.14 / 6.0 | 5.16 / -0.14 / 7.7 | 2.52 / -0.15 / 8.2 | 1.34 / -0.17 / 10.4 |
| pooled | 2.01 / -0.16 / 10.1 | 3.16 / -0.10 / 11.0 | 5.60 / -0.04 / 11.7 | 8.47 / +0.00 / 12.1 | 5.60 / +0.04 / 16.2 | 3.16 / +0.10 / 21.0 | 2.01 / +0.16 / 26.4 |

## 7. What decides games

| gems, round | games reaching it | tied | leader wins % | lead 1-49 | lead 50-149 | lead 150+ |
|---|---|---|---|---|---|---|
| tributed r200 | 2720 | 783 | 54.5 | 51.1 (n=1300) | 59.7 (n=566) | 74.6 (n=71) |
| tributed r400 | 2582 | 155 | 62.3 | 54.8 (n=987) | 64.0 (n=1004) | 75.5 (n=436) |
| tributed r600 | 1905 | 70 | 68.0 | 56.8 (n=526) | 62.9 (n=653) | 81.9 (n=656) |
| tributed+carried r200 | 2720 | 163 | 66.6 | 56.3 (n=1435) | 73.1 (n=766) | 93.8 (n=356) |
| tributed+carried r400 | 2582 | 57 | 75.2 | 55.0 (n=838) | 75.4 (n=675) | 91.8 (n=1012) |
| tributed+carried r600 | 1905 | 37 | 81.7 | 59.8 (n=435) | 76.9 (n=415) | 93.0 (n=1018) |

| predictor | win % |
|---|---|
| team that did not die first wins | 65.2 (n=2465) |
| more kills wins | 88.4 (n=2252) |
| more r1-300 kills wins | 74.8 (n=1382) |
| more gems captured wins | 76.2 (n=2706) |
| more r1-300 gems captured wins | 68.8 (n=2618) |
| fewer gems lost at death wins | 87.8 (n=2259) |
| more mid-group captures wins | 78.3 (n=1228) |

Games where neither side tributes 200: 10 (gen-shared-gems-6140100714001, gen-tiny-6140100211004, mut-05birthday-cake-6140100519005, mut-05birthday-cake-6140100619021, mut-05birthday-cake-6140100719014, mut-05birthday-cake-6140100719015, mut-boss-battle-6140100517027, mut-gift-wrapping-6140100117057).

Game length: median 742, quartiles 567-1025, min 206, max 2000; 4.2% reach round 2000; 95.8% end on 1000 gems.

## Examples

**bagdeath** (2332 in all, largest first, one per game):

- `replays/batch-20261113-142259-ab-mx-tethys-mirror-study/729-gen-ladder-6140100000012-12.repl26a` (f392336b3e09cb03) r1990 team B (L): Prism died with 4119 gems (champ, allies<=8 4, enemies<=8 2, branch W)
- `replays/batch-20261113-142259-ab-mx-tethys-mirror-study/4365-mut-05slant-6140100519009-12.repl26a` (3fb3d0610428e52d) r1273 team B (W): Prism died with 3228 gems (champ, allies<=8 4, enemies<=8 1, branch R)
- `replays/batch-20261113-142259-ab-mx-tethys-mirror-study/2701-gen-ladder05-6140100118039-12.repl26a` (8764966c9204cc7e) r828 team A (L): Prism died with 3213 gems (champ, allies<=8 4, enemies<=8 4, branch R)
- `replays/batch-20261113-142259-ab-mx-tethys-mirror-study/535-gen-classic-6140100701025-12.repl26a` (b17d34df91acd1cb) r1765 team B (L): Vesper Vale died with 3005 gems (champ, allies<=8 2, enemies<=8 2, branch R)
- `replays/batch-20261113-142259-ab-mx-tethys-mirror-study/2325-gen-ladder-6140100700026-12.repl26a` (66ed0e2abd0d57f0) r1668 team A (W): Prism died with 2725 gems (champ, allies<=8 4, enemies<=8 1, branch R)
- `replays/batch-20261113-142259-ab-mx-tethys-mirror-study/3493-gen-ladder05-6140100718057-12.repl26a` (1826d585d6fb7438) r757 team B (L): Prism died with 2085 gems (champ, allies<=8 4, enemies<=8 1, branch T)

**stolen** (6320 in all, largest first, one per game):

- `replays/batch-20261113-142259-ab-mx-tethys-mirror-study/4511-mut-boss-battle-6140100517027-12.repl26a` (d650385325c14939) r1452 team A (L): Monolith (400 gems, mid) cleared r1445 stolen
- `replays/batch-20261113-142259-ab-mx-tethys-mirror-study/4515-mut-boss-battle-6140100617000-12.repl26a` (8030ffb24181a543) r752 team A (L): Monolith (400 gems, mid) cleared r724 stolen
- `replays/batch-20261113-142259-ab-mx-tethys-mirror-study/5333-mut-tangle-6140100717045-12.repl26a` (602d79766d827439) r716 team B (L): Golem (284 gems, mid) cleared r706 stolen
- `replays/batch-20261113-142259-ab-mx-tethys-mirror-study/017-gen-altar-poor-6140100416000-12.repl26a` (bffb9630d4e6f97d) r703 team A (W): Monolith (256 gems, enemy) cleared r694 stolen
- `replays/batch-20261113-142259-ab-mx-tethys-mirror-study/3233-gen-ladder05-6140100518053-12.repl26a` (34a7211aa94cf106) r697 team A (L): Monolith (256 gems, own) cleared r688 stolen
- `replays/batch-20261113-142259-ab-mx-tethys-mirror-study/335-gen-classic-6140100401015-12.repl26a` (2477bfbd50901988) r551 team A (W): Monolith (256 gems, enemy) cleared r544 stolen

**idle-off30** (6033 in all, largest first, one per game):

- `replays/batch-20261113-142259-ab-mx-tethys-mirror-study/4125-mut-05birthday-cake-6140100719015-12.repl26a` (fe14ff2a68bcf0da) r92 team A (W): Cassi#0 idle off spawn 1885 rounds at (12, 21) branch F
- `replays/batch-20261113-142259-ab-mx-tethys-mirror-study/4121-mut-05birthday-cake-6140100619021-12.repl26a` (4c5eff6605b64b30) r248 team B (W): Issac#5 idle off spawn 1728 rounds at (18, 27) branch F
- `replays/batch-20261113-142259-ab-mx-tethys-mirror-study/4119-mut-05birthday-cake-6140100519005-12.repl26a` (5623ff782936a8fa) r72 team A (L): Cassi#0 idle off spawn 1617 rounds at (13, 16) branch F
- `replays/batch-20261113-142259-ab-mx-tethys-mirror-study/4087-mut-05abandoned-buildings-6140100319007-12.repl26a` (85188654e0518add) r25 team A (L): Vesper Vale#1 idle off spawn 1406 rounds at (8, 20) branch F
- `replays/batch-20261113-142259-ab-mx-tethys-mirror-study/2185-gen-ladder-6140100600068-12.repl26a` (9fb13699c04c38f6) r714 team B (L): Willow#7 idle off spawn 1268 rounds at (16, 15) branch U
- `replays/batch-20261113-142259-ab-mx-tethys-mirror-study/3869-gen-shared-gems-6140100714001-12.repl26a` (4a0d4e8f78b1914f) r908 team A (L): Willow#4 idle off spawn 1093 rounds at (5, 78) branch F

