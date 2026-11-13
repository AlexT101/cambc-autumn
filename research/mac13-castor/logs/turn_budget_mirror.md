# Turn budget: 1023 games from replays/batch-20261113-020109-ab-mac13-castor-mirror-dbg-study

Mirror mode: identical replays (a map pair swapped between two copies of one bot) count once; sides are the game winner (W) and loser (L).

Trace: 7 of 2046 team stdouts truncated (1 MiB cap or D lines end before the last round), 0 missing; 0.0% of champion-rounds have no D line (branch `?`); 0 D-line champion ids outside the printing team.

## 1. Turn budget (% of champion-rounds)

| class | all W | all L | r1-150 W | r1-150 L | r151-400 W | r151-400 L | r401-800 W | r401-800 L | r801+ W | r801+ L | r1-300 W | r1-300 L |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dead | 4.6 | 12.2 | 1.9 | 3.3 | 4.0 | 7.6 | 5.5 | 14.8 | 6.4 | 22.2 | 2.8 | 5.0 |
| fight | 3.6 | 3.5 | 3.2 | 3.2 | 3.3 | 3.2 | 3.7 | 3.5 | 4.5 | 4.2 | 3.3 | 3.2 |
| tribute | 3.9 | 1.4 | 0.5 | 0.5 | 2.0 | 1.5 | 5.3 | 1.8 | 7.3 | 1.4 | 1.0 | 0.9 |
| recall | 4.0 | 3.6 | 4.1 | 4.0 | 5.0 | 4.7 | 4.0 | 3.5 | 2.8 | 2.2 | 4.6 | 4.4 |
| hold+recall | 2.0 | 1.9 | 2.5 | 2.4 | 2.7 | 2.6 | 1.7 | 1.6 | 1.0 | 0.8 | 2.7 | 2.6 |
| teleport | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| camp | 17.9 | 16.3 | 27.7 | 27.1 | 21.0 | 19.9 | 15.3 | 13.2 | 9.5 | 7.0 | 24.9 | 24.1 |
| hold | 4.9 | 4.4 | 5.2 | 5.0 | 5.3 | 4.7 | 4.8 | 4.2 | 4.4 | 3.7 | 5.2 | 4.9 |
| spawn-heal | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| bag->altar | 14.9 | 13.9 | 9.8 | 9.7 | 17.4 | 16.4 | 17.1 | 15.7 | 12.2 | 10.8 | 13.4 | 12.9 |
| bag->camp | 6.2 | 5.9 | 5.4 | 5.3 | 8.4 | 7.8 | 6.5 | 6.2 | 3.4 | 3.2 | 6.9 | 6.6 |
| bag-other | 3.3 | 3.8 | 2.1 | 2.1 | 3.4 | 3.6 | 3.6 | 4.5 | 3.7 | 4.5 | 2.7 | 2.8 |
| empty->camp | 17.9 | 17.1 | 26.4 | 26.2 | 16.2 | 16.1 | 16.1 | 15.2 | 16.2 | 14.0 | 21.3 | 21.2 |
| empty->spawn | 3.1 | 3.5 | 2.5 | 2.6 | 2.5 | 2.8 | 3.2 | 3.6 | 4.4 | 5.1 | 2.5 | 2.7 |
| empty-other | 6.6 | 8.0 | 6.0 | 6.1 | 5.3 | 5.7 | 6.6 | 8.1 | 9.1 | 12.4 | 5.6 | 5.8 |
| idle-off | 6.4 | 4.1 | 2.5 | 2.5 | 3.5 | 3.2 | 6.3 | 3.8 | 13.8 | 7.1 | 2.9 | 2.8 |
| idle-spawn | 0.4 | 0.4 | 0.2 | 0.2 | 0.2 | 0.2 | 0.3 | 0.3 | 1.2 | 1.2 | 0.2 | 0.2 |

By attack type (all rounds):

| class | melee W | melee L | ranged W | ranged L |
|---|---|---|---|---|
| dead | 5.6 | 12.9 | 4.0 | 11.8 |
| fight | 4.3 | 4.1 | 3.1 | 3.1 |
| tribute | 2.2 | 1.4 | 5.1 | 1.4 |
| recall | 4.4 | 3.9 | 3.8 | 3.4 |
| hold+recall | 2.3 | 2.2 | 1.8 | 1.6 |
| teleport | 0.0 | 0.0 | 0.0 | 0.0 |
| camp | 19.3 | 17.5 | 16.9 | 15.4 |
| hold | 4.4 | 3.8 | 5.3 | 4.8 |
| spawn-heal | 0.0 | 0.0 | 0.0 | 0.0 |
| bag->altar | 14.5 | 13.3 | 15.2 | 14.2 |
| bag->camp | 5.4 | 5.0 | 6.8 | 6.5 |
| bag-other | 3.3 | 3.6 | 3.3 | 4.0 |
| empty->camp | 18.3 | 17.1 | 17.7 | 17.1 |
| empty->spawn | 2.7 | 3.0 | 3.5 | 3.9 |
| empty-other | 6.3 | 7.7 | 6.9 | 8.1 |
| idle-off | 5.9 | 3.5 | 6.7 | 4.5 |
| idle-spawn | 1.0 | 0.9 | 0.1 | 0.1 |

By champion type (% of that type's champion-rounds; walk = all bag/empty walking):

| type | side | rounds | dead | fight | camp | hold | tribute | recall | spawn-heal | idle-spawn | idle-off | walk |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Cassi | W | 855997 | 7.6 | 2.8 | 19.0 | 4.3 | 1.7 | 3.4 | 0.0 | 0.1 | 4.7 | 55.2 |
| Cassi | L | 855997 | 17.3 | 2.6 | 16.2 | 3.6 | 0.9 | 2.9 | 0.0 | 0.3 | 3.5 | 51.7 |
| Heart of Ruin | W | 293178 | 5.5 | 7.2 | 19.3 | 3.9 | 1.9 | 4.0 | 0.0 | 0.6 | 3.6 | 52.1 |
| Heart of Ruin | L | 293178 | 9.3 | 6.8 | 18.2 | 3.3 | 1.2 | 3.5 | 0.0 | 0.6 | 3.0 | 52.3 |
| Issac | W | 855997 | 7.6 | 2.8 | 20.5 | 4.3 | 1.7 | 4.5 | 0.0 | 1.9 | 5.2 | 49.8 |
| Issac | L | 855997 | 17.3 | 2.5 | 17.7 | 3.4 | 1.0 | 3.9 | 0.0 | 1.7 | 3.4 | 47.7 |
| Marcella | W | 128545 | 4.6 | 6.8 | 10.3 | 4.9 | 3.4 | 4.2 | 0.0 | 0.2 | 10.9 | 52.4 |
| Marcella | L | 128545 | 14.1 | 6.7 | 9.7 | 4.6 | 2.1 | 3.5 | 0.0 | 0.1 | 3.6 | 53.6 |
| Prism | W | 717576 | 1.0 | 3.8 | 13.3 | 8.8 | 14.3 | 4.3 | 0.0 | 0.0 | 4.6 | 48.2 |
| Prism | L | 717576 | 11.5 | 3.9 | 13.1 | 8.2 | 2.1 | 4.1 | 0.0 | 0.0 | 4.2 | 51.2 |
| Ren | W | 130038 | 4.0 | 4.9 | 20.7 | 3.9 | 2.3 | 4.5 | 0.0 | 0.1 | 7.6 | 49.1 |
| Ren | L | 130038 | 9.8 | 4.9 | 19.8 | 3.3 | 1.4 | 4.2 | 0.0 | 0.1 | 4.6 | 49.1 |
| Ryth | W | 241591 | 4.1 | 8.0 | 17.0 | 5.1 | 2.6 | 3.9 | 0.0 | 0.1 | 10.0 | 46.6 |
| Ryth | L | 241591 | 13.6 | 8.1 | 15.1 | 4.6 | 1.7 | 3.3 | 0.0 | 0.1 | 4.0 | 47.0 |
| Stellar | W | 22510 | 4.8 | 1.0 | 19.1 | 4.6 | 3.0 | 4.5 | 0.0 | 0.1 | 10.0 | 50.4 |
| Stellar | L | 22510 | 7.7 | 1.3 | 19.4 | 4.4 | 1.7 | 4.9 | 0.0 | 0.1 | 10.0 | 48.3 |
| Tavi | W | 92279 | 6.6 | 6.8 | 17.3 | 6.6 | 2.3 | 2.7 | 0.0 | 0.1 | 6.5 | 49.8 |
| Tavi | L | 92279 | 15.4 | 6.4 | 14.5 | 6.7 | 1.2 | 2.2 | 0.0 | 0.0 | 3.5 | 48.7 |
| Varg | W | 115447 | 2.3 | 1.7 | 21.6 | 4.0 | 2.6 | 4.4 | 0.0 | 0.1 | 3.8 | 56.4 |
| Varg | L | 115447 | 4.2 | 1.6 | 20.7 | 4.1 | 2.0 | 4.3 | 0.0 | 0.1 | 2.6 | 57.4 |
| Vendetta | W | 216899 | 2.7 | 2.0 | 20.7 | 4.6 | 3.2 | 5.5 | 0.0 | 0.2 | 4.4 | 52.0 |
| Vendetta | L | 216899 | 5.4 | 1.9 | 20.3 | 4.2 | 2.3 | 5.2 | 0.0 | 0.9 | 3.5 | 51.8 |
| Vesper Vale | W | 601591 | 1.9 | 4.4 | 21.6 | 6.3 | 4.0 | 4.5 | 0.0 | 0.1 | 7.6 | 45.4 |
| Vesper Vale | L | 601591 | 6.4 | 4.2 | 20.3 | 5.6 | 2.4 | 4.4 | 0.0 | 0.1 | 4.7 | 48.1 |
| Willow | W | 568173 | 4.0 | 1.1 | 13.0 | 1.2 | 0.3 | 3.0 | 0.0 | 0.0 | 11.3 | 65.9 |
| Willow | L | 568173 | 9.2 | 1.3 | 11.9 | 1.3 | 0.1 | 2.6 | 0.0 | 0.0 | 6.1 | 67.2 |

Bot branch (D lines), % of champion-rounds:

| branch | all W | all L | r1-300 W | r1-300 L |
|---|---|---|---|---|
| `-` | 4.7 | 12.2 | 2.8 | 5.0 |
| `?` | 0.1 | 0.0 | 0.0 | 0.0 |
| `A` | 0.0 | 0.0 | 0.0 | 0.0 |
| `B` | 6.0 | 4.8 | 1.8 | 1.9 |
| `C` | 1.7 | 1.5 | 1.7 | 1.5 |
| `E` | 0.1 | 0.5 | 0.0 | 0.0 |
| `F` | 59.8 | 57.2 | 71.3 | 69.4 |
| `G` | 1.6 | 1.0 | 0.4 | 0.4 |
| `H` | 0.6 | 0.6 | 0.7 | 0.7 |
| `K` | 2.0 | 1.9 | 2.3 | 2.3 |
| `P` | 4.3 | 3.9 | 4.8 | 4.4 |
| `Q` | 1.5 | 1.4 | 2.0 | 1.9 |
| `R` | 5.1 | 6.6 | 4.3 | 5.0 |
| `S` | 0.0 | 0.0 | 0.0 | 0.0 |
| `T` | 3.1 | 0.9 | 0.6 | 0.6 |
| `U` | 3.2 | 1.7 | 0.0 | 0.0 |
| `W` | 0.1 | 0.0 | 0.0 | 0.0 |
| `X` | 0.2 | 0.2 | 0.2 | 0.2 |
| `h` | 5.6 | 5.4 | 6.5 | 6.3 |
| `k` | 0.4 | 0.3 | 0.4 | 0.3 |
| `r` | 0.0 | 0.0 | 0.0 | 0.0 |

Branch x replay class (both sides pooled; % of the branch's rounds, cells under 1% blank):

| branch | n | dead | fight | tribute | recall | hold+recall | teleport | camp | hold | spawn-heal | bag->altar | bag->camp | bag-other | empty->camp | empty->spawn | empty-other | idle-off | idle-spawn |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `-` | 818043 | 100 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| `?` | 4384 | 2 | 3 | 27 |  |  |  |  | 2 |  |  |  |  |  | 1 | 3 | 57 |  |
| `A` | 10 |  | 100 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| `B` | 521539 |  | 4 | 6 |  |  |  | 3 |  |  | 70 | 3 | 7 |  |  |  | 6 |  |
| `C` | 154794 |  | 22 |  |  |  |  |  |  |  | 16 | 5 | 11 | 15 | 6 | 23 | 1 |  |
| `E` | 25214 |  | 30 |  |  |  |  |  |  |  | 16 |  | 3 | 5 | 2 | 41 | 2 |  |
| `F` | 5663657 |  | 3 |  | 1 |  |  | 26 | 2 |  | 16 | 9 | 3 | 24 | 2 | 8 | 4 |  |
| `G` | 127342 |  | 2 |  |  |  |  | 25 |  |  | 5 | 2 | 1 | 27 | 4 | 12 | 22 |  |
| `H` | 57464 |  |  |  | 99 |  |  |  |  |  |  |  |  |  |  |  |  |  |
| `K` | 188580 |  |  |  | 99 |  |  |  |  |  |  |  |  |  |  |  |  |  |
| `P` | 396407 |  | 2 |  |  | 9 |  | 3 | 86 |  |  |  |  |  |  |  |  |  |
| `Q` | 139392 |  |  |  |  | 100 |  |  |  |  |  |  |  |  |  |  |  |  |
| `R` | 567113 |  | 19 |  | 3 |  |  |  |  |  | 7 | 7 | 19 | 15 | 25 | 5 |  |  |
| `S` | 1341 |  | 3 | 28 | 10 |  |  |  |  |  | 10 | 9 | 27 | 3 | 8 |  |  |  |
| `T` | 196741 |  |  | 99 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| `U` | 236632 |  | 5 |  |  |  |  |  |  |  | 2 |  |  | 2 | 4 | 23 | 64 |  |
| `W` | 3676 |  | 20 | 27 |  |  |  |  |  |  |  |  |  |  |  |  | 53 |  |
| `X` | 15703 |  | 7 |  |  |  |  |  | 16 |  | 8 | 4 | 7 | 21 | 9 | 27 |  |  |
| `h` | 528198 |  |  |  |  |  |  | 19 |  |  | 3 | 1 | 2 | 34 | 11 | 20 | 8 |  |
| `k` | 31670 |  |  |  | 99 |  |  |  |  |  |  |  |  |  |  |  |  |  |
| `r` | 1742 |  | 11 |  | 1 |  |  | 2 |  |  | 12 | 6 | 16 | 1 | 4 |  | 46 |  |

Replay class -> bot branches (pooled; % of the class's rounds, top 4):

| class | n | branches |
|---|---|---|
| dead | 817356 | `-` 100, `F` 0, `R` 0, `B` 0 |
| fight | 347032 | `F` 42, `R` 31, `C` 10, `B` 6 |
| tribute | 257259 | `T` 76, `B` 12, `F` 10, `R` 1 |
| recall | 371379 | `K` 50, `F` 20, `H` 15, `k` 8 |
| hold+recall | 186292 | `Q` 75, `P` 19, `F` 6, `K` 1 |
| teleport | 1582 | `F` 84, `B` 12, `R` 1, `h` 1 |
| camp | 1652892 | `F` 90, `h` 6, `G` 2, `B` 1 |
| hold | 450721 | `P` 75, `F` 23, `X` 1, `B` 0 |
| spawn-heal | 30 | `H` 80, `F` 20 |
| bag->altar | 1393078 | `F` 67, `B` 26, `R` 3, `C` 2 |
| bag->camp | 585089 | `F` 88, `R` 6, `B` 3, `C` 1 |
| bag-other | 346330 | `F` 50, `R` 31, `B` 10, `C` 5 |
| empty->camp | 1694626 | `F` 80, `h` 11, `R` 5, `G` 2 |
| empty->spawn | 321999 | `R` 43, `F` 31, `h` 18, `C` 3 |
| empty-other | 705809 | `F` 64, `h` 15, `U` 8, `C` 5 |
| idle-off | 505848 | `F` 47, `U` 30, `h` 8, `B` 6 |
| idle-spawn | 42320 | `F` 99, `H` 1, `B` 0, `-` 0 |

## 2. Earnings (per game per side unless noted)

| metric | W | L |
|---|---|---|
| gems captured | 1053 | 833 |
| gems tributed | 1084 | 409 |
| gems taken by kills | 239 | 35.0 |
| gems lost at death to champions | 34.8 | 231 |
| gems lost at death to camps | 3.0 | 5.8 |
| gold earned (lifetime) | 5962 | 4438 |
| r1-300 gems captured | 365 | 320 |
| r1-300 gems tributed | 114 | 101 |
| r1-300 gems lost at death | 6.4 | 25.6 |
| gems captured per camp-hit round | 1.2 | 1.1 |
| gems captured per hold round | 4.5 | 4.0 |
| gems captured per (camp+hold) round | 1.0 | 0.9 |
| gems tributed per 100 alive rounds | 24.0 | 9.9 |
| mean bag carried per alive round | 68.7 | 37.8 |
| % alive rounds carrying 30+ | 23.2 | 20.9 |
| tributes per 1000 alive rounds | 3.8 | 2.4 |
| mean bag at tribute | 63.0 | 40.5 |
| walk steps per tributed gem | 2.7 | 7.2 |
| bag-walk rounds per tributed gem | 1.1 | 2.7 |
| bag-walk rounds just before a tribute (mean trip) | 8.4 | 8.7 |
| idle-off rounds in stretches of 50+ (% of idle-off) | 18.9 | 13.3 |
| idle-off rounds in 50+ stretches by branch at its start, per game | `U` 48.9, `F` 6.3, `W` 0.7, `h` 0.5 | `U` 21.2, `F` 3.9, `B` 0.2, `W` 0.2 |
| altar locks placed / tribute attempts blocked, per game | 3.52 / 0.00 | 4.24 / 0.00 |
| real recalls per game (completed) | 53.7 (45.0) | 48.3 (40.7) |
| tribute cancels per game (cause) | death 0.02, lock 1.22, manual 2.09, stun 2.55 | death 0.05, lock 0.25, manual 2.49, stun 0.58 |

By phase:

| per game | side | r1-150 | r151-400 | r401-800 | r801+ |
|---|---|---|---|---|---|
| gems captured | W | 155 | 363 | 388 | 147 |
| gems captured | L | 143 | 299 | 293 | 97.4 |
| gems tributed | W | 27.1 | 184 | 568 | 305 |
| gems tributed | L | 25.9 | 136 | 184 | 63.2 |
| alive champion-rounds | W | 804 | 1300 | 1505 | 902 |
| alive champion-rounds | L | 793 | 1252 | 1357 | 750 |

Real recalls (completed or lasting 2+ rounds; feints excluded) by the branch at their start:

| side | `F` | `P` | `R` | `B` | `G` | `S` | `C` | `U` | `h` | `E` | `W` | `-` | `X` | `?` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| W | 28.3/g, 83.4% done, 52.9% bag, 25.4 from spawn | 17.2/g, 89.0% done, 49.7% bag, 25.6 from spawn | 6.6/g, 75.5% done, 41.4% bag, 25.3 from spawn | 0.5/g, 74.1% done, 100.0% bag, 28.8 from spawn | 0.6/g, 70.5% done, 13.4% bag, 30.4 from spawn | 0.3/g, 88.6% done, 18.5% bag, 35.5 from spawn | 0.2/g, 65.2% done, 72.2% bag, 38.1 from spawn | 0.1/g, 29.8% done, 6.0% bag, 21.0 from spawn | 0.0/g, 54.0% done, 6.0% bag, 18.9 from spawn | 0.0/g, 100.0% done, 100.0% bag, 14.0 from spawn | 0.0/g, 100.0% done, 100.0% bag, 27.9 from spawn | 0.0/g, 100.0% done, 0.0% bag, 48.0 from spawn | 0.0/g, 50.0% done, 50.0% bag, 13.0 from spawn | 0.0/g, 100.0% done, 33.3% bag, 43.0 from spawn |
| L | 25.4/g, 83.7% done, 55.2% bag, 24.9 from spawn | 15.6/g, 89.5% done, 50.7% bag, 24.9 from spawn | 6.2/g, 75.8% done, 42.4% bag, 25.3 from spawn | 0.5/g, 76.9% done, 100.0% bag, 28.0 from spawn | 0.3/g, 70.9% done, 14.6% bag, 28.3 from spawn | 0.2/g, 90.1% done, 15.2% bag, 33.9 from spawn | 0.1/g, 52.9% done, 79.3% bag, 30.8 from spawn | 0.0/g, 67.7% done, 19.4% bag, 27.1 from spawn | 0.0/g, 60.0% done, 20.0% bag, 20.6 from spawn | 0.0/g, 37.5% done, 75.0% bag, 34.6 from spawn | 0.0/g, 100.0% done, 100.0% bag, 19.0 from spawn | 0.0/g, 100.0% done, 50.0% bag, 44.5 from spawn | 0.0/g, 66.7% done, 100.0% bag, 11.0 from spawn | - |

Bag size at tribute (% of tributes): W: 0-19 33.8, 20-39 32.4, 40-59 15.0, 60-79 6.4, 80-99 3.5, 100+ 8.9; L: 0-19 32.7, 20-39 34.7, 40-59 17.3, 60-79 7.3, 80-99 3.5, 100+ 4.4

## 3. Clears and captures

| group type | hitters | n | champ-turns | rounds | turns/gem | r1-300 turns/gem (n) | camp dmg/gem | own capture % | stolen % | uncaptured % | holders at payout | clear->payout | resets/clear | enemy also hit % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Monolith | 1 | 14 | 21.7 | 190 | 0.10 | - | 15.2 | 85.7 | 14.3 | 0.0 | 1.2 | 7.9 | 0.00 | 64.3 |
| Monolith | 2 | 48 | 44.3 | 75.8 | 0.21 | - | 25.0 | 89.6 | 8.3 | 2.1 | 1.0 | 5.2 | 0.04 | 14.6 |
| Monolith | 3+ | 337 | 122 | 89.4 | 0.51 | 1.39 (8) | 35.2 | 96.4 | 2.4 | 1.2 | 1.4 | 6.0 | 0.03 | 16.0 |
| Golem | 1 | 691 | 12.9 | 21.8 | 0.23 | 0.20 (28) | 17.1 | 94.4 | 4.5 | 1.2 | 1.0 | 6.5 | 0.05 | 15.5 |
| Golem | 2 | 440 | 21.7 | 32.8 | 0.40 | 0.56 (39) | 25.0 | 96.8 | 2.7 | 0.5 | 1.0 | 5.8 | 0.07 | 9.3 |
| Golem | 3+ | 1077 | 46.4 | 33.9 | 0.82 | 1.13 (475) | 33.1 | 97.3 | 1.8 | 0.9 | 1.1 | 6.1 | 0.06 | 9.5 |
| Elk | 1 | 6149 | 11.1 | 16.8 | 0.38 | 0.49 (985) | 16.1 | 96.5 | 2.5 | 1.0 | 1.0 | 6.6 | 0.03 | 10.1 |
| Elk | 2 | 5087 | 20.7 | 22.8 | 0.70 | 0.93 (1477) | 24.6 | 97.9 | 1.5 | 0.6 | 1.0 | 6.5 | 0.07 | 7.1 |
| Elk | 3+ | 9396 | 32.6 | 19.5 | 1.02 | 1.25 (5065) | 24.8 | 98.3 | 1.3 | 0.4 | 1.1 | 6.5 | 0.07 | 6.9 |
| Wolf | 1 | 16986 | 13.2 | 17.4 | 1.31 | 2.09 (4725) | 20.5 | 97.4 | 2.0 | 0.7 | 1.0 | 6.7 | 0.04 | 7.4 |
| Wolf | 2 | 14052 | 18.8 | 18.9 | 1.59 | 2.00 (5363) | 21.1 | 98.2 | 1.3 | 0.5 | 1.0 | 6.8 | 0.06 | 5.9 |
| Wolf | 3+ | 12669 | 24.8 | 16.8 | 1.72 | 1.99 (6608) | 19.0 | 97.9 | 1.7 | 0.4 | 1.1 | 6.9 | 0.10 | 6.8 |
| GemCl | 1 | 19070 | 3.4 | 3.5 | 0.24 | 0.24 (8522) | 0.0 | 95.3 | 3.3 | 1.4 | 1.0 | 8.9 | 0.09 | 4.6 |
| GemCl | 2 | 5259 | 5.6 | 7.1 | 0.25 | 0.24 (2669) | 0.0 | 95.7 | 3.2 | 1.2 | 1.0 | 8.2 | 0.15 | 6.6 |
| GemCl | 3+ | 1640 | 8.4 | 6.0 | 0.23 | 0.22 (931) | 0.0 | 95.2 | 4.1 | 0.7 | 1.1 | 8.8 | 0.31 | 10.2 |
| GoldCl | 1 | 17666 | 3.2 | 4.9 | nan | nan (6669) | nan | 95.4 | 2.3 | 2.3 | 1.0 | 10.6 | 0.03 | 3.7 |
| GoldCl | 2 | 4092 | 4.7 | 19.0 | nan | nan (1833) | nan | 95.5 | 1.9 | 2.5 | 1.0 | 10.2 | 0.04 | 4.5 |
| GoldCl | 3+ | 678 | 8.4 | 19.2 | nan | nan (324) | nan | 96.5 | 2.7 | 0.9 | 1.1 | 9.6 | 0.10 | 9.4 |

| side | clears/game | solo % | turns/gem | camp dmg/gem | own capture % | stolen from % | steals/game | holders at payout | clear->payout | resets/clear | contested/clear | camp deaths/clear |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| W | 59.7 | 52.4 | 0.84 | 16.9 | 97.4 | 1.6 | 1.50 | 1.0 | 7.9 | 0.06 | 0.01 | 0.004 |
| L | 53.1 | 52.7 | 0.91 | 17.3 | 96.0 | 2.8 | 0.97 | 1.0 | 7.9 | 0.08 | 0.01 | 0.004 |

Clears per game by group side (relative to the clearing team) and type:

| side | own Wolf | own Elk | own Golem | own Monolith | own GemCl | own GoldCl | mid Wolf | mid Elk | mid Golem | mid Monolith | mid GemCl | mid GoldCl | enemy Wolf | enemy Elk | enemy Golem | enemy Monolith | enemy GemCl | enemy GoldCl |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| W | 18.55 | 8.59 | 0.87 | 0.17 | 9.78 | 9.08 | 1.57 | 1.05 | 0.17 | 0.05 | 1.83 | 1.11 | 2.46 | 1.17 | 0.16 | 0.05 | 1.90 | 1.11 |
| L | 17.42 | 8.02 | 0.79 | 0.08 | 9.19 | 8.97 | 1.07 | 0.64 | 0.08 | 0.02 | 1.33 | 0.83 | 1.66 | 0.70 | 0.09 | 0.02 | 1.35 | 0.83 |

## 4. Supply (% of gem-weighted group-rounds in each state, groups by side relative to the team)

`asleep` = monsters up and asleep (nobody within range for 2 camp phases): available, unworked. `unclaimed` = cleared, nobody holding.

all:

| side | groups | asleep | awake | unclaimed | held | respawn |
|---|---|---|---|---|---|---|
| W | own | 56.6 | 8.5 | 2.2 | 2.2 | 30.4 |
| W | mid | 70.1 | 7.9 | 1.4 | 1.4 | 19.2 |
| W | enemy | 58.4 | 8.2 | 1.9 | 2.2 | 29.3 |
| L | own | 58.4 | 8.2 | 1.9 | 2.2 | 29.3 |
| L | mid | 70.1 | 7.9 | 1.4 | 1.4 | 19.2 |
| L | enemy | 56.6 | 8.5 | 2.2 | 2.2 | 30.4 |

r1-300:

| side | groups | asleep | awake | unclaimed | held | respawn |
|---|---|---|---|---|---|---|
| W | own | 61.3 | 8.8 | 1.7 | 2.5 | 25.6 |
| W | mid | 80.2 | 5.6 | 1.2 | 1.3 | 11.7 |
| W | enemy | 61.9 | 9.0 | 1.5 | 2.5 | 25.2 |
| L | own | 61.9 | 9.0 | 1.5 | 2.5 | 25.2 |
| L | mid | 80.2 | 5.6 | 1.2 | 1.3 | 11.7 |
| L | enemy | 61.3 | 8.8 | 1.7 | 2.5 | 25.6 |

By group type (unweighted % of group-rounds; own/mid/enemy relative to the side):

| side | type | own asleep | own awake | own unclaimed | mid asleep | mid awake | mid unclaimed | enemy asleep | enemy awake | enemy unclaimed |
|---|---|---|---|---|---|---|---|---|---|---|
| W | Wolf | 56.8 | 8.7 | 1.6 | 65.2 | 8.5 | 1.8 | 57.3 | 8.7 | 1.7 |
| L | Wolf | 57.3 | 8.7 | 1.7 | 65.2 | 8.5 | 1.8 | 56.8 | 8.7 | 1.6 |
| W | Elk | 44.0 | 10.3 | 2.0 | 54.6 | 11.9 | 1.6 | 44.7 | 10.2 | 2.0 |
| L | Elk | 44.7 | 10.2 | 2.0 | 54.6 | 11.9 | 1.6 | 44.0 | 10.3 | 2.0 |
| W | Golem | 58.4 | 7.8 | 1.1 | 67.2 | 8.1 | 1.5 | 59.2 | 8.0 | 1.2 |
| L | Golem | 59.2 | 8.0 | 1.2 | 67.2 | 8.1 | 1.5 | 58.4 | 7.8 | 1.1 |
| W | Monolith | 84.0 | 4.9 | 0.2 | 89.2 | 3.7 | 0.2 | 88.0 | 4.2 | 0.2 |
| L | Monolith | 88.0 | 4.2 | 0.2 | 89.2 | 3.7 | 0.2 | 84.0 | 4.9 | 0.2 |
| W | GemCl | 31.4 | 3.8 | 6.1 | 26.3 | 5.5 | 8.1 | 31.4 | 3.9 | 6.5 |
| L | GemCl | 31.4 | 3.9 | 6.5 | 26.3 | 5.5 | 8.1 | 31.4 | 3.8 | 6.1 |
| W | GoldCl | 54.5 | 2.4 | 8.7 | 60.6 | 3.2 | 7.7 | 53.9 | 2.5 | 8.5 |
| L | GoldCl | 53.9 | 2.5 | 8.5 | 60.6 | 3.2 | 7.7 | 54.5 | 2.4 | 8.7 |

Upper bound on gems left asleep per game (each asleep round = 1/(respawn+15) of a farm cycle): W: own 858, mid 407, enemy 870; L: own 870, mid 407, enemy 858

| side | own captures/game (gems) | mid captures/game (gems) | enemy captures/game (gems) | r1-300 own/mid/enemy |
|---|---|---|---|---|
| W | 46.8 (761) | 5.9 (159) | 6.9 (133) | 18.8/1.8/1.8 |
| L | 43.8 (680) | 3.8 (79) | 4.4 (74) | 18.1/1.4/1.4 |

## 5. Deaths

| metric | W | L |
|---|---|---|
| deaths/game (to champions + camps) | 2.4 + 0.23 | 7.2 + 0.26 |
| median first-death round (none = length+1) | 409 | 275 |
| % of games this side died first | 31.8 | 59.2 |
| % alone (no ally within 8) | 20.4 | 19.7 |
| % ally within 4 | 59.2 | 59.8 |
| % 2+ enemies within 8 | 74.1 | 80.7 |
| % on own ground | 54.1 | 70.1 |
| % on mid ground | 21.9 | 15.3 |
| % on enemy ground | 23.9 | 14.6 |
| % walking toward spawn (last 4 rounds) | 30.0 | 23.8 |
| % branch R in last 4 rounds | 81.2 | 71.7 |
| % carrying 30+ gems | 8.9 | 17.8 |
| mean enemies within 8 | 2.7 | 3.1 |
| mean gems carried at death | 11.3 | 29.7 |
| r1-300 deaths/game | 0.60 | 1.16 |

Gems lost at death by champion type, per game (% of the side's loss): W: Prism 11.9 (39.5%), Cassi 4.0 (13.2%), Vesper Vale 4.0 (13.2%), Issac 2.7 (9.1%); L: Prism 164.6 (74.6%), Vesper Vale 14.4 (6.5%), Cassi 11.6 (5.3%), Issac 6.4 (2.9%)

Deaths carrying 100+ gems: W 0.05/game holding 44.9% of gems lost; L 0.47/game holding 70.3% of gems lost

Branch at death (last D line): W: `R` 72.4%, `F` 13.2%, `E` 3.9%, `B` 2.4%, `K` 1.9%, `U` 1.7%; L: `R` 62.0%, `E` 21.2%, `F` 10.0%, `B` 2.0%, `U` 1.0%, `K` 1.0%

Deaths by (allies within 8, enemies within 8), per 10 games:

| side | allies\enemies | 0 | 1 | 2 | 3+ |
|---|---|---|---|---|---|
| W | 0 | 0.2 | 1.5 | 1.5 | 2.2 |
| W | 1 | 0.6 | 1.2 | 1.4 | 2.7 |
| W | 2 | 0.4 | 1.4 | 1.2 | 3.2 |
| W | 3+ | 0.4 | 1.2 | 1.7 | 5.6 |
| L | 0 | 0.4 | 3.5 | 3.4 | 7.3 |
| L | 1 | 0.5 | 3.3 | 4.0 | 10.6 |
| L | 2 | 0.5 | 2.9 | 2.9 | 11.3 |
| L | 3+ | 0.5 | 2.7 | 3.1 | 17.3 |

## 6. Kills and fights

| side | kills/game | r1-300 kills/game | fights/game | initiated % | won on kills % | lost on kills % | net bag gems/game |
|---|---|---|---|---|---|---|---|
| W | 7.2 | 1.02 | 30.0 | 50.1 | 20.3 | 6.8 | 189 |
| L | 2.4 | 0.50 | 30.0 | 49.9 | 6.8 | 20.3 | -189 |

By fight size (participants, side v enemy): fights per game, then net kills per fight (killed - lost):

| side | 1v1 | 1v2 | 1v3+ | 2v1 | 2v2 | 2v3+ | 3+v1 | 3+v2 | 3+v3+ |
|---|---|---|---|---|---|---|---|---|---|
| W | 15.97 / +0.07 | 2.65 / +0.09 | 0.72 / -0.00 | 3.00 / +0.26 | 2.12 / +0.19 | 1.17 / +0.16 | 1.13 / +0.56 | 1.17 / +0.47 | 2.08 / +0.38 |
| L | 15.97 / -0.07 | 3.00 / -0.26 | 1.13 / -0.56 | 2.65 / -0.09 | 2.12 / -0.19 | 1.17 / -0.47 | 0.72 / +0.00 | 1.17 / -0.16 | 2.08 / -0.38 |
| pooled | 15.97 / +0.00 | 2.82 / -0.09 | 0.93 / -0.34 | 2.82 / +0.09 | 2.12 / +0.00 | 1.17 / -0.15 | 0.93 / +0.34 | 1.17 / +0.15 | 2.08 / +0.00 |

By head-count difference at the start (own minus enemy champions alive within 8 of the fight, previous round end): fights per game / net kills per fight / % won on kills:

| side | -3 | -2 | -1 | 0 | 1 | 2 | 3 |
|---|---|---|---|---|---|---|---|
| W | 1.31 / +0.14 / 18.3 | 2.64 / +0.13 / 18.5 | 5.46 / +0.12 / 16.9 | 8.92 / +0.12 / 17.0 | 6.13 / +0.17 / 20.8 | 3.44 / +0.24 / 27.3 | 2.12 / +0.32 / 33.9 |
| L | 2.12 / -0.32 / 4.6 | 3.44 / -0.24 / 5.4 | 6.13 / -0.17 / 6.0 | 8.92 / -0.12 / 6.8 | 5.46 / -0.12 / 7.8 | 2.64 / -0.13 / 8.9 | 1.31 / -0.14 / 10.0 |
| pooled | 1.72 / -0.14 / 9.8 | 3.04 / -0.08 / 11.1 | 5.79 / -0.03 / 11.1 | 8.92 / +0.00 / 11.9 | 5.79 / +0.03 / 14.7 | 3.04 / +0.08 / 19.3 | 1.72 / +0.14 / 24.8 |

## 7. What decides games

| gems, round | games reaching it | tied | leader wins % | lead 1-49 | lead 50-149 | lead 150+ |
|---|---|---|---|---|---|---|
| tributed r200 | 1023 | 271 | 51.5 | 49.8 (n=486) | 50.4 (n=238) | 89.3 (n=28) |
| tributed r400 | 984 | 61 | 56.7 | 49.2 (n=378) | 55.9 (n=390) | 76.8 (n=155) |
| tributed r600 | 765 | 29 | 64.5 | 55.8 (n=233) | 60.2 (n=254) | 77.1 (n=249) |
| tributed+carried r200 | 1023 | 74 | 62.9 | 54.3 (n=554) | 70.4 (n=294) | 88.1 (n=101) |
| tributed+carried r400 | 984 | 28 | 72.6 | 54.8 (n=334) | 71.2 (n=281) | 91.2 (n=341) |
| tributed+carried r600 | 765 | 21 | 79.3 | 54.1 (n=185) | 73.7 (n=175) | 94.0 (n=384) |

| predictor | win % |
|---|---|
| team that did not die first wins | 65.1 (n=931) |
| more kills wins | 86.9 (n=860) |
| more r1-300 kills wins | 75.3 (n=507) |
| more gems captured wins | 79.0 (n=1017) |
| more r1-300 gems captured wins | 68.3 (n=976) |
| fewer gems lost at death wins | 87.9 (n=858) |
| more mid-group captures wins | 77.2 (n=465) |

Games where neither side tributes 200: 6 (gen-ladder-14120200087, gen-shared-gems-14120214001, mut-boss-battle-14120117004, mut-fragment-14120217036, mut-fragment-14120317024, mut-vault-14120117005).

Game length: median 767, quartiles 598-1023, min 242, max 2000; 4.1% reach round 2000; 95.9% end on 1000 gems.

## Examples

**bagdeath** (750 in all, largest first, one per game):

- `replays/batch-20261113-020109-ab-mac13-castor-mirror-dbg-study/1061-gen-ladder-14120300018-12.repl26a` (cf8e09b8ef79c2d6) r1618 team B (L): Prism died with 3040 gems (champ, allies<=8 0, enemies<=8 3, branch R)
- `replays/batch-20261113-020109-ab-mac13-castor-mirror-dbg-study/1009-gen-ladder-14120200104-12.repl26a` (819c06f9312ad11c) r1193 team B (L): Prism died with 3009 gems (champ, allies<=8 1, enemies<=8 1, branch T)
- `replays/batch-20261113-020109-ab-mac13-castor-mirror-dbg-study/341-gen-jungle-14120107000-12.repl26a` (d5b72a66ef775db6) r1178 team A (W): Prism died with 1388 gems (champ, allies<=8 4, enemies<=8 4, branch T)
- `replays/batch-20261113-020109-ab-mac13-castor-mirror-dbg-study/1971-mut-sunburst-14120317056-12.repl26a` (82552c106b41e7f1) r1318 team A (L): Prism died with 1103 gems (champ, allies<=8 2, enemies<=8 1, branch T)
- `replays/batch-20261113-020109-ab-mac13-castor-mirror-dbg-study/827-gen-ladder-14120200013-12.repl26a` (1ddaaa43affef8d6) r704 team A (L): Prism died with 1076 gems (champ, allies<=8 0, enemies<=8 1, branch B)
- `replays/batch-20261113-020109-ab-mac13-castor-mirror-dbg-study/1509-gen-tiny-14120311004-12.repl26a` (38e16056b2a86687) r959 team B (L): Prism died with 1012 gems (champ, allies<=8 3, enemies<=8 3, branch R)

**stolen** (2528 in all, largest first, one per game):

- `replays/batch-20261113-020109-ab-mac13-castor-mirror-dbg-study/1461-gen-small-brawl-14120302002-12.repl26a` (4329a0faec406986) r668 team B (L): Monolith (414 gems, mid) cleared r661 stolen
- `replays/batch-20261113-020109-ab-mac13-castor-mirror-dbg-study/1165-gen-ladder-14120300070-12.repl26a` (b4775c21806ed0d2) r624 team B (L): Monolith (256 gems, enemy) cleared r619 stolen
- `replays/batch-20261113-020109-ab-mac13-castor-mirror-dbg-study/1307-gen-maze-14120103002-12.repl26a` (571cf282dff5e8f6) r684 team A (L): Monolith (256 gems, enemy) cleared r675 stolen
- `replays/batch-20261113-020109-ab-mac13-castor-mirror-dbg-study/195-gen-classic-14120201021-12.repl26a` (c711fe87c6a90fb5) r320 team B (L): Monolith (256 gems, enemy) cleared r309 stolen
- `replays/batch-20261113-020109-ab-mac13-castor-mirror-dbg-study/785-gen-ladder-14120100104-12.repl26a` (93ff7fd6802bb167) r723 team B (L): Monolith (256 gems, own) cleared r713 stolen
- `replays/batch-20261113-020109-ab-mac13-castor-mirror-dbg-study/943-gen-ladder-14120200071-12.repl26a` (d6dc8ead75f8efc7) r412 team B (L): Monolith (256 gems, own) cleared r403 stolen

**idle-off30** (1913 in all, largest first, one per game):

- `replays/batch-20261113-020109-ab-mac13-castor-mirror-dbg-study/615-gen-ladder-14120100019-12.repl26a` (c90e157c9b932b85) r518 team B (L): Vesper Vale#5 idle off spawn 1463 rounds at (23, 16) branch U
- `replays/batch-20261113-020109-ab-mac13-castor-mirror-dbg-study/1587-mut-boss-battle-14120117004-12.repl26a` (6e29edd3cbe0338d) r675 team A (W): Prism#3 idle off spawn 1326 rounds at (38, 11) branch F
- `replays/batch-20261113-020109-ab-mac13-castor-mirror-dbg-study/273-gen-contested-centre-14120010000-12.repl26a` (f16c42fda1506ab2) r822 team A (L): Vesper Vale#0 idle off spawn 1179 rounds at (25, 14) branch U
- `replays/batch-20261113-020109-ab-mac13-castor-mirror-dbg-study/1423-gen-shared-gems-14120214001-12.repl26a` (966b8e7d75d88c2d) r526 team A (L): Issac#2 idle off spawn 1013 rounds at (12, 22) branch F
- `replays/batch-20261113-020109-ab-mac13-castor-mirror-dbg-study/1447-gen-small-brawl-14120102003-12.repl26a` (c2941d231a6cb3a2) r936 team A (L): Prism#3 idle off spawn 988 rounds at (15, 16) branch U
- `replays/batch-20261113-020109-ab-mac13-castor-mirror-dbg-study/1567-mut-anvil-14120317011-12.repl26a` (cc7f3eb99b7d9d5c) r1192 team B (L): Vesper Vale#5 idle off spawn 785 rounds at (19, 8) branch U

