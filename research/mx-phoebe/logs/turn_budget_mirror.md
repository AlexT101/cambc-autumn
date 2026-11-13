# Turn budget: 1360 games from replays/batch-20261113-142239-ab-mx-phoebe-mirror-study

Mirror mode: identical replays (a map pair swapped between two copies of one bot) count once; sides are the game winner (W) and loser (L).

Trace: 5 of 2720 team stdouts truncated (1 MiB cap or D lines end before the last round), 0 missing; 0.0% of champion-rounds have no D line (branch `?`); 0 D-line champion ids outside the printing team.

## 1. Turn budget (% of champion-rounds)

| class | all W | all L | r1-150 W | r1-150 L | r151-400 W | r151-400 L | r401-800 W | r401-800 L | r801+ W | r801+ L | r1-300 W | r1-300 L |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dead | 4.8 | 14.0 | 1.9 | 2.9 | 4.2 | 8.2 | 5.8 | 17.2 | 6.9 | 28.0 | 2.9 | 5.0 |
| fight | 3.4 | 3.3 | 3.0 | 3.0 | 3.0 | 2.9 | 3.4 | 3.3 | 4.5 | 4.1 | 3.0 | 3.0 |
| tribute | 4.6 | 1.4 | 0.5 | 0.5 | 2.2 | 1.5 | 6.4 | 2.0 | 9.3 | 1.3 | 1.1 | 0.9 |
| recall | 4.4 | 3.9 | 4.5 | 4.5 | 5.3 | 5.0 | 4.2 | 3.6 | 3.2 | 2.4 | 5.0 | 4.8 |
| hold+recall | 2.0 | 1.9 | 2.5 | 2.5 | 2.7 | 2.5 | 1.8 | 1.5 | 1.1 | 0.9 | 2.7 | 2.6 |
| teleport | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| camp | 18.8 | 17.1 | 28.9 | 28.4 | 22.0 | 20.5 | 15.5 | 13.4 | 9.5 | 7.2 | 26.1 | 25.1 |
| hold | 4.4 | 3.9 | 4.9 | 4.7 | 5.0 | 4.5 | 4.3 | 3.7 | 2.9 | 2.4 | 4.9 | 4.6 |
| spawn-heal | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| bag->altar | 14.0 | 13.2 | 9.0 | 9.0 | 16.1 | 15.4 | 16.3 | 14.9 | 11.4 | 10.8 | 12.3 | 12.0 |
| bag->camp | 6.1 | 5.9 | 5.6 | 5.5 | 8.4 | 7.9 | 6.1 | 5.9 | 3.3 | 3.3 | 7.1 | 6.7 |
| bag-other | 3.2 | 3.7 | 1.9 | 2.0 | 3.2 | 3.6 | 3.6 | 4.3 | 3.6 | 4.5 | 2.5 | 2.7 |
| empty->camp | 17.6 | 16.8 | 26.5 | 26.2 | 16.5 | 16.2 | 15.6 | 14.7 | 14.2 | 12.5 | 21.6 | 21.4 |
| empty->spawn | 3.0 | 3.3 | 2.4 | 2.4 | 2.5 | 2.8 | 3.1 | 3.5 | 4.4 | 4.8 | 2.4 | 2.6 |
| empty-other | 6.4 | 7.8 | 5.9 | 6.1 | 5.3 | 5.9 | 6.6 | 8.1 | 8.5 | 11.6 | 5.5 | 6.0 |
| idle-off | 7.0 | 3.7 | 2.4 | 2.3 | 3.4 | 3.1 | 7.1 | 3.8 | 16.7 | 5.8 | 2.8 | 2.6 |
| idle-spawn | 0.2 | 0.1 | 0.1 | 0.1 | 0.1 | 0.1 | 0.2 | 0.1 | 0.5 | 0.4 | 0.1 | 0.1 |

By attack type (all rounds):

| class | melee W | melee L | ranged W | ranged L |
|---|---|---|---|---|
| dead | 5.9 | 14.6 | 4.1 | 13.5 |
| fight | 4.0 | 3.7 | 3.0 | 2.9 |
| tribute | 2.3 | 1.4 | 6.2 | 1.5 |
| recall | 4.7 | 4.2 | 4.1 | 3.7 |
| hold+recall | 2.4 | 2.1 | 1.8 | 1.7 |
| teleport | 0.0 | 0.0 | 0.0 | 0.0 |
| camp | 20.5 | 18.3 | 17.6 | 16.3 |
| hold | 3.9 | 3.4 | 4.7 | 4.2 |
| spawn-heal | 0.0 | 0.0 | 0.0 | 0.0 |
| bag->altar | 13.6 | 12.6 | 14.2 | 13.6 |
| bag->camp | 5.3 | 5.1 | 6.8 | 6.5 |
| bag-other | 3.2 | 3.4 | 3.2 | 3.8 |
| empty->camp | 18.4 | 16.9 | 17.1 | 16.8 |
| empty->spawn | 2.6 | 3.0 | 3.3 | 3.6 |
| empty-other | 6.2 | 7.6 | 6.6 | 7.9 |
| idle-off | 6.6 | 3.3 | 7.3 | 4.0 |
| idle-spawn | 0.4 | 0.3 | 0.0 | 0.0 |

By champion type (% of that type's champion-rounds; walk = all bag/empty walking):

| type | side | rounds | dead | fight | camp | hold | tribute | recall | spawn-heal | idle-spawn | idle-off | walk |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Cassi | W | 1086931 | 8.1 | 2.5 | 20.7 | 3.4 | 1.7 | 3.9 | 0.0 | 0.1 | 4.4 | 54.0 |
| Cassi | L | 1086931 | 19.3 | 2.4 | 17.5 | 2.6 | 0.7 | 3.2 | 0.0 | 0.0 | 3.1 | 50.0 |
| Heart of Ruin | W | 342571 | 4.9 | 5.9 | 20.7 | 3.7 | 1.9 | 4.2 | 0.0 | 0.1 | 5.0 | 51.6 |
| Heart of Ruin | L | 342571 | 9.0 | 5.5 | 19.7 | 3.6 | 1.3 | 4.0 | 0.0 | 0.1 | 2.9 | 52.0 |
| Issac | W | 1086931 | 8.1 | 2.6 | 22.3 | 3.6 | 2.0 | 5.0 | 0.0 | 0.6 | 4.7 | 49.3 |
| Issac | L | 1086931 | 19.3 | 2.2 | 18.6 | 2.9 | 1.0 | 4.2 | 0.0 | 0.6 | 2.8 | 46.9 |
| Marcella | W | 171036 | 5.3 | 7.5 | 11.1 | 5.1 | 3.7 | 4.3 | 0.0 | 0.1 | 10.6 | 49.8 |
| Marcella | L | 171036 | 14.9 | 7.4 | 9.4 | 4.6 | 2.0 | 3.9 | 0.0 | 0.1 | 4.2 | 51.5 |
| Prism | W | 955687 | 0.8 | 4.2 | 12.4 | 8.2 | 18.2 | 4.7 | 0.0 | 0.0 | 3.9 | 45.8 |
| Prism | L | 955687 | 13.5 | 4.1 | 12.4 | 7.9 | 2.7 | 4.5 | 0.0 | 0.0 | 3.1 | 49.9 |
| Ren | W | 144856 | 3.6 | 5.1 | 20.2 | 3.9 | 2.1 | 4.9 | 0.0 | 0.0 | 9.0 | 48.2 |
| Ren | L | 144856 | 11.7 | 4.8 | 19.4 | 3.4 | 1.3 | 4.4 | 0.0 | 0.1 | 3.9 | 48.4 |
| Ryth | W | 395970 | 5.1 | 7.0 | 17.1 | 4.3 | 2.4 | 3.9 | 0.0 | 0.1 | 13.8 | 43.7 |
| Ryth | L | 395970 | 17.4 | 6.6 | 16.1 | 4.1 | 1.4 | 3.4 | 0.0 | 0.1 | 4.0 | 44.5 |
| Stellar | W | 62686 | 7.6 | 2.1 | 17.3 | 3.6 | 2.5 | 4.5 | 0.0 | 0.0 | 12.6 | 48.0 |
| Stellar | L | 62686 | 15.5 | 1.8 | 17.3 | 3.1 | 1.3 | 4.2 | 0.0 | 0.1 | 6.1 | 48.6 |
| Tavi | W | 86517 | 5.3 | 5.2 | 19.1 | 7.2 | 2.9 | 3.1 | 0.0 | 0.0 | 6.6 | 48.8 |
| Tavi | L | 86517 | 12.9 | 5.1 | 17.3 | 5.0 | 1.5 | 3.0 | 0.0 | 0.0 | 4.8 | 48.8 |
| Varg | W | 167466 | 2.8 | 1.7 | 21.8 | 3.5 | 2.6 | 4.9 | 0.0 | 0.1 | 3.7 | 56.1 |
| Varg | L | 167466 | 6.2 | 1.4 | 20.4 | 3.1 | 1.6 | 4.7 | 0.0 | 0.1 | 2.9 | 57.0 |
| Vendetta | W | 235536 | 2.1 | 1.2 | 23.4 | 4.1 | 3.3 | 6.0 | 0.0 | 0.9 | 3.7 | 50.4 |
| Vendetta | L | 235536 | 4.0 | 1.4 | 22.8 | 4.0 | 2.5 | 6.1 | 0.0 | 0.1 | 3.9 | 50.8 |
| Vesper Vale | W | 750688 | 2.2 | 4.1 | 22.8 | 5.4 | 3.8 | 4.6 | 0.0 | 0.1 | 10.4 | 42.4 |
| Vesper Vale | L | 750688 | 8.5 | 3.7 | 22.0 | 4.8 | 2.2 | 4.4 | 0.0 | 0.1 | 4.2 | 46.2 |
| Willow | W | 697377 | 3.9 | 0.9 | 14.1 | 0.9 | 0.3 | 3.2 | 0.0 | 0.0 | 12.5 | 63.9 |
| Willow | L | 697377 | 9.7 | 1.2 | 13.2 | 0.9 | 0.1 | 2.9 | 0.0 | 0.0 | 6.0 | 65.9 |

Bot branch (D lines), % of champion-rounds:

| branch | all W | all L | r1-300 W | r1-300 L |
|---|---|---|---|---|
| `-` | 4.8 | 14.0 | 2.9 | 5.0 |
| `?` | 0.0 | 0.0 | 0.0 | 0.0 |
| `A` | 0.0 | 0.0 | 0.0 | 0.0 |
| `B` | 6.2 | 5.1 | 1.9 | 2.0 |
| `C` | 1.6 | 1.3 | 1.6 | 1.3 |
| `E` | 0.1 | 0.7 | 0.0 | 0.0 |
| `F` | 58.6 | 56.4 | 71.9 | 70.2 |
| `G` | 1.6 | 0.8 | 0.3 | 0.3 |
| `H` | 0.6 | 0.5 | 0.7 | 0.7 |
| `K` | 2.0 | 1.9 | 2.3 | 2.3 |
| `P` | 3.8 | 3.4 | 4.4 | 4.1 |
| `Q` | 1.5 | 1.4 | 2.0 | 1.9 |
| `R` | 4.6 | 5.9 | 3.9 | 4.6 |
| `S` | 0.0 | 0.0 | 0.0 | 0.0 |
| `T` | 3.8 | 1.0 | 0.7 | 0.5 |
| `U` | 4.3 | 1.6 | 0.0 | 0.0 |
| `W` | 0.1 | 0.0 | 0.0 | 0.0 |
| `X` | 0.1 | 0.1 | 0.2 | 0.2 |
| `h` | 5.6 | 5.2 | 6.4 | 6.3 |
| `k` | 0.6 | 0.5 | 0.6 | 0.6 |
| `r` | 0.0 | 0.0 | 0.0 | 0.0 |

Branch x replay class (both sides pooled; % of the branch's rounds, cells under 1% blank):

| branch | n | dead | fight | tribute | recall | hold+recall | teleport | camp | hold | spawn-heal | bag->altar | bag->camp | bag-other | empty->camp | empty->spawn | empty-other | idle-off | idle-spawn |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `-` | 1162154 | 100 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| `?` | 5069 | 3 | 2 | 33 |  |  |  |  | 2 |  |  |  |  |  |  |  | 58 | 1 |
| `A` | 64 |  | 27 |  |  |  |  |  |  |  |  |  | 3 | 44 | 8 | 19 |  |  |
| `B` | 700144 |  | 4 | 6 |  |  |  | 3 |  |  | 68 | 3 | 7 |  |  |  | 7 |  |
| `C` | 179202 |  | 21 |  |  |  |  |  |  |  | 16 | 5 | 11 | 14 | 6 | 24 |  |  |
| `E` | 47791 |  | 32 |  |  |  |  |  |  |  | 15 |  | 3 | 6 | 3 | 39 | 2 |  |
| `F` | 7116019 |  | 2 |  | 2 |  |  | 28 | 2 |  | 15 | 9 | 3 | 24 | 2 | 8 | 4 |  |
| `G` | 151247 |  | 2 |  | 1 |  |  | 20 |  |  | 5 | 2 | 1 | 31 | 6 | 14 | 18 |  |
| `H` | 72614 |  |  |  | 99 |  |  |  |  |  |  |  |  |  |  |  |  |  |
| `K` | 239917 |  |  |  | 99 |  |  |  |  |  |  |  |  |  |  |  |  |  |
| `P` | 442743 |  | 3 |  |  | 10 |  | 3 | 84 |  |  |  |  |  |  |  |  |  |
| `Q` | 181682 |  |  |  |  | 100 |  |  |  |  |  |  |  |  |  |  |  |  |
| `R` | 647948 |  | 19 |  | 3 |  |  |  |  |  | 6 | 6 | 19 | 14 | 25 | 5 |  |  |
| `S` | 2322 |  | 2 | 27 | 7 |  |  |  |  |  | 13 | 11 | 18 | 6 | 16 |  |  |  |
| `T` | 296850 |  |  | 99 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| `U` | 362165 |  | 5 |  |  |  |  |  |  |  | 2 |  |  | 3 | 4 | 20 | 66 |  |
| `W` | 8633 |  | 13 | 35 |  |  |  |  |  |  |  |  |  |  |  |  | 52 |  |
| `X` | 16019 |  | 10 |  |  |  |  |  | 9 |  | 8 | 4 | 8 | 20 | 6 | 35 |  |  |
| `h` | 667543 |  |  |  |  |  |  | 22 |  |  | 3 | 1 | 2 | 34 | 10 | 20 | 8 |  |
| `k` | 66107 |  |  |  | 99 |  |  |  |  |  |  |  |  |  |  |  |  |  |
| `r` | 2271 |  | 14 |  | 2 |  |  | 1 |  |  | 12 | 6 | 15 | 1 | 3 |  | 43 |  |

Replay class -> bot branches (pooled; % of the class's rounds, top 4):

| class | n | branches |
|---|---|---|
| dead | 1161968 | `-` 100, `F` 0, `R` 0, `?` 0 |
| fight | 413153 | `F` 40, `R` 30, `C` 9, `B` 7 |
| tribute | 373987 | `T` 79, `B` 10, `F` 8, `W` 1 |
| recall | 515184 | `K` 46, `F` 22, `H` 14, `k` 13 |
| hold+recall | 243112 | `Q` 75, `P` 18, `F` 6, `K` 1 |
| teleport | 1350 | `F` 89, `B` 8, `R` 2, `C` 1 |
| camp | 2218076 | `F` 91, `h` 7, `G` 1, `B` 1 |
| hold | 508990 | `P` 73, `F` 25, `B` 0, `R` 0 |
| spawn-heal | 59 | `H` 68, `F` 22, `B` 8, `G` 2 |
| bag->altar | 1679443 | `F` 65, `B` 28, `R` 2, `C` 2 |
| bag->camp | 746415 | `F` 89, `R` 5, `B` 3, `C` 1 |
| bag-other | 424578 | `F` 50, `R` 29, `B` 12, `C` 5 |
| empty->camp | 2128849 | `F` 81, `h` 11, `R` 4, `G` 2 |
| empty->spawn | 393540 | `R` 42, `F` 31, `h` 17, `U` 4 |
| empty-other | 878480 | `F` 63, `h` 15, `U` 8, `C` 5 |
| idle-off | 660517 | `F` 42, `U` 36, `h` 8, `B` 7 |
| idle-spawn | 20803 | `F` 96, `B` 2, `U` 0, `-` 0 |

## 2. Earnings (per game per side unless noted)

| metric | W | L |
|---|---|---|
| gems captured | 1101 | 892 |
| gems tributed | 1094 | 381 |
| gems taken by kills | 311 | 47.9 |
| gems lost at death to champions | 44.9 | 288 |
| gems lost at death to camps | 3.2 | 7.8 |
| gold earned (lifetime) | 5969 | 4473 |
| r1-300 gems captured | 425 | 372 |
| r1-300 gems tributed | 120 | 97.3 |
| r1-300 gems lost at death | 7.8 | 32.8 |
| gems captured per camp-hit round | 1.3 | 1.1 |
| gems captured per hold round | 5.6 | 5.1 |
| gems captured per (camp+hold) round | 1.0 | 0.9 |
| gems tributed per 100 alive rounds | 25.3 | 9.8 |
| mean bag carried per alive round | 88.9 | 43.9 |
| % alive rounds carrying 30+ | 23.7 | 21.2 |
| tributes per 1000 alive rounds | 3.8 | 2.3 |
| mean bag at tribute | 65.7 | 41.9 |
| walk steps per tributed gem | 2.5 | 7.2 |
| bag-walk rounds per tributed gem | 1.0 | 2.7 |
| bag-walk rounds just before a tribute (mean trip) | 7.6 | 9.4 |
| idle-off rounds in stretches of 50+ (% of idle-off) | 20.0 | 10.2 |
| idle-off rounds in 50+ stretches by branch at its start, per game | `U` 56.2, `F` 3.4, `W` 1.8, `B` 1.4 | `U` 11.6, `F` 3.0, `B` 1.8, `G` 0.2 |
| altar locks placed / tribute attempts blocked, per game | 3.41 / 0.00 | 4.41 / 0.00 |
| real recalls per game (completed) | 55.2 (45.6) | 49.4 (41.3) |
| tribute cancels per game (cause) | death 0.03, lock 1.67, manual 3.56, stun 3.67 | death 0.06, lock 0.31, manual 1.27, stun 0.60 |

By phase:

| per game | side | r1-150 | r151-400 | r401-800 | r801+ |
|---|---|---|---|---|---|
| gems captured | W | 181 | 415 | 372 | 133 |
| gems captured | L | 168 | 339 | 289 | 96.1 |
| gems tributed | W | 26.1 | 203 | 608 | 257 |
| gems tributed | L | 25.8 | 132 | 175 | 48.9 |
| alive champion-rounds | W | 814 | 1305 | 1399 | 809 |
| alive champion-rounds | L | 806 | 1251 | 1230 | 626 |

Real recalls (completed or lasting 2+ rounds; feints excluded) by the branch at their start:

| side | `F` | `P` | `R` | `B` | `G` | `S` | `C` | `U` | `h` | `E` | `-` | `X` | `W` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| W | 30.4/g, 81.3% done, 52.4% bag, 22.5 from spawn | 16.6/g, 88.6% done, 48.4% bag, 22.6 from spawn | 6.4/g, 77.0% done, 40.7% bag, 24.4 from spawn | 0.6/g, 73.2% done, 100.0% bag, 26.9 from spawn | 0.7/g, 70.5% done, 9.5% bag, 22.8 from spawn | 0.3/g, 87.1% done, 12.2% bag, 28.1 from spawn | 0.2/g, 54.4% done, 72.1% bag, 29.3 from spawn | 0.1/g, 44.4% done, 2.6% bag, 18.7 from spawn | 0.0/g, 59.3% done, 16.7% bag, 19.4 from spawn | 0.0/g, 80.0% done, 60.0% bag, 31.6 from spawn | 0.0/g, 80.0% done, 0.0% bag, 36.8 from spawn | 0.0/g, 0.0% done, 0.0% bag, 4.0 from spawn | 0.0/g, 100.0% done, 100.0% bag, 49.2 from spawn |
| L | 27.5/g, 81.9% done, 54.1% bag, 21.9 from spawn | 15.1/g, 89.4% done, 50.6% bag, 22.2 from spawn | 5.7/g, 77.6% done, 44.8% bag, 24.6 from spawn | 0.5/g, 79.8% done, 100.0% bag, 23.2 from spawn | 0.3/g, 73.1% done, 13.9% bag, 29.2 from spawn | 0.2/g, 87.2% done, 15.1% bag, 28.1 from spawn | 0.1/g, 64.4% done, 79.8% bag, 28.4 from spawn | 0.0/g, 53.6% done, 14.3% bag, 24.1 from spawn | 0.0/g, 61.1% done, 8.3% bag, 19.0 from spawn | 0.0/g, 57.1% done, 71.4% bag, 17.1 from spawn | 0.0/g, 50.0% done, 58.3% bag, 23.3 from spawn | 0.0/g, 0.0% done, 75.0% bag, 24.0 from spawn | 0.0/g, 100.0% done, 100.0% bag, 23.0 from spawn |

Bag size at tribute (% of tributes): W: 0-19 31.9, 20-39 33.6, 40-59 15.6, 60-79 6.9, 80-99 3.4, 100+ 8.7; L: 0-19 29.8, 20-39 37.6, 40-59 17.7, 60-79 7.0, 80-99 3.7, 100+ 4.2

## 3. Clears and captures

| group type | hitters | n | champ-turns | rounds | turns/gem | r1-300 turns/gem (n) | camp dmg/gem | own capture % | stolen % | uncaptured % | holders at payout | clear->payout | resets/clear | enemy also hit % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Monolith | 1 | 27 | 19.1 | 136 | 0.09 | - | 11.1 | 81.5 | 18.5 | 0.0 | 1.2 | 12.2 | 1.00 | 66.7 |
| Monolith | 2 | 65 | 51.6 | 111 | 0.23 | - | 27.4 | 92.3 | 6.2 | 1.5 | 1.2 | 6.2 | 0.06 | 24.6 |
| Monolith | 3+ | 340 | 101 | 105 | 0.44 | 0.99 (11) | 30.9 | 95.6 | 3.5 | 0.9 | 1.5 | 8.2 | 0.38 | 19.1 |
| Golem | 1 | 914 | 11.7 | 20.4 | 0.20 | 0.19 (68) | 14.8 | 93.9 | 5.1 | 1.0 | 1.0 | 6.5 | 0.05 | 16.6 |
| Golem | 2 | 599 | 22.6 | 31.3 | 0.37 | 0.38 (59) | 24.3 | 95.2 | 3.7 | 1.2 | 1.0 | 7.7 | 0.18 | 14.7 |
| Golem | 3+ | 1667 | 46.9 | 32.4 | 0.79 | 1.02 (740) | 30.8 | 96.5 | 2.9 | 0.5 | 1.1 | 6.6 | 0.10 | 12.3 |
| Elk | 1 | 7719 | 11.1 | 16.1 | 0.37 | 0.41 (1335) | 15.6 | 96.5 | 2.6 | 0.9 | 1.0 | 6.5 | 0.03 | 9.5 |
| Elk | 2 | 6758 | 20.8 | 22.4 | 0.67 | 0.84 (1930) | 23.8 | 97.8 | 1.7 | 0.5 | 1.0 | 6.4 | 0.07 | 6.5 |
| Elk | 3+ | 14561 | 33.1 | 18.4 | 0.99 | 1.16 (8177) | 23.1 | 98.3 | 1.4 | 0.4 | 1.1 | 6.5 | 0.08 | 5.8 |
| Wolf | 1 | 19721 | 13.8 | 17.8 | 1.29 | 2.03 (5777) | 20.3 | 97.4 | 1.9 | 0.8 | 1.0 | 6.7 | 0.04 | 7.2 |
| Wolf | 2 | 17892 | 19.0 | 19.4 | 1.51 | 1.85 (7066) | 20.0 | 97.9 | 1.4 | 0.6 | 1.0 | 6.8 | 0.06 | 6.0 |
| Wolf | 3+ | 18484 | 24.5 | 16.0 | 1.57 | 1.76 (10289) | 16.8 | 98.2 | 1.4 | 0.4 | 1.1 | 6.8 | 0.09 | 6.4 |
| GemCl | 1 | 22480 | 3.8 | 4.3 | 0.24 | 0.25 (10709) | 0.0 | 95.1 | 3.2 | 1.7 | 1.0 | 9.2 | 0.08 | 5.2 |
| GemCl | 2 | 6940 | 5.9 | 7.9 | 0.24 | 0.23 (3714) | 0.0 | 95.7 | 3.2 | 1.0 | 1.0 | 8.2 | 0.14 | 6.5 |
| GemCl | 3+ | 2292 | 8.5 | 6.4 | 0.23 | 0.22 (1426) | 0.0 | 97.2 | 2.1 | 0.7 | 1.1 | 7.4 | 0.13 | 7.0 |
| GoldCl | 1 | 16030 | 3.3 | 4.7 | nan | nan (6511) | nan | 95.3 | 2.2 | 2.5 | 1.0 | 10.3 | 0.03 | 3.3 |
| GoldCl | 2 | 3599 | 4.6 | 19.2 | nan | nan (1644) | nan | 95.1 | 2.1 | 2.8 | 1.0 | 11.4 | 0.06 | 4.0 |
| GoldCl | 3+ | 486 | 6.9 | 23.8 | nan | nan (248) | nan | 95.5 | 2.5 | 2.1 | 1.1 | 8.8 | 0.07 | 8.8 |

| side | clears/game | solo % | turns/gem | camp dmg/gem | own capture % | stolen from % | steals/game | holders at payout | clear->payout | resets/clear | contested/clear | camp deaths/clear |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| W | 54.4 | 47.5 | 0.82 | 16.2 | 97.4 | 1.6 | 1.33 | 1.0 | 7.7 | 0.07 | 0.01 | 0.004 |
| L | 49.0 | 47.7 | 0.87 | 16.0 | 96.2 | 2.7 | 0.87 | 1.0 | 7.7 | 0.07 | 0.01 | 0.004 |

Clears per game by group side (relative to the clearing team) and type:

| side | own Wolf | own Elk | own Golem | own Monolith | own GemCl | own GoldCl | mid Wolf | mid Elk | mid Golem | mid Monolith | mid GemCl | mid GoldCl | enemy Wolf | enemy Elk | enemy Golem | enemy Monolith | enemy GemCl | enemy GoldCl |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| W | 17.85 | 9.10 | 0.93 | 0.14 | 8.96 | 6.13 | 1.77 | 0.95 | 0.22 | 0.05 | 2.00 | 0.72 | 2.04 | 1.21 | 0.16 | 0.04 | 1.48 | 0.68 |
| L | 17.03 | 8.71 | 0.83 | 0.07 | 8.50 | 6.12 | 1.22 | 0.62 | 0.13 | 0.02 | 1.39 | 0.62 | 1.35 | 0.76 | 0.07 | 0.01 | 1.00 | 0.52 |

## 4. Supply (% of gem-weighted group-rounds in each state, groups by side relative to the team)

`asleep` = monsters up and asleep (nobody within range for 2 camp phases): available, unworked. `unclaimed` = cleared, nobody holding.

all:

| side | groups | asleep | awake | unclaimed | held | respawn |
|---|---|---|---|---|---|---|
| W | own | 58.6 | 8.3 | 1.6 | 2.2 | 29.3 |
| W | mid | 67.9 | 7.7 | 1.9 | 1.5 | 20.9 |
| W | enemy | 59.4 | 7.7 | 2.0 | 2.2 | 28.7 |
| L | own | 59.4 | 7.7 | 2.0 | 2.2 | 28.7 |
| L | mid | 67.9 | 7.7 | 1.9 | 1.5 | 20.9 |
| L | enemy | 58.6 | 8.3 | 1.6 | 2.2 | 29.3 |

r1-300:

| side | groups | asleep | awake | unclaimed | held | respawn |
|---|---|---|---|---|---|---|
| W | own | 61.8 | 8.0 | 1.4 | 2.5 | 26.4 |
| W | mid | 76.5 | 5.9 | 1.5 | 1.6 | 14.6 |
| W | enemy | 62.1 | 8.0 | 1.5 | 2.5 | 25.9 |
| L | own | 62.1 | 8.0 | 1.5 | 2.5 | 25.9 |
| L | mid | 76.5 | 5.9 | 1.5 | 1.6 | 14.6 |
| L | enemy | 61.8 | 8.0 | 1.4 | 2.5 | 26.4 |

By group type (unweighted % of group-rounds; own/mid/enemy relative to the side):

| side | type | own asleep | own awake | own unclaimed | mid asleep | mid awake | mid unclaimed | enemy asleep | enemy awake | enemy unclaimed |
|---|---|---|---|---|---|---|---|---|---|---|
| W | Wolf | 58.6 | 8.4 | 1.5 | 62.4 | 9.0 | 1.8 | 58.7 | 8.4 | 1.7 |
| L | Wolf | 58.7 | 8.4 | 1.7 | 62.4 | 9.0 | 1.8 | 58.6 | 8.4 | 1.5 |
| W | Elk | 47.9 | 9.6 | 1.6 | 57.2 | 10.0 | 2.0 | 47.4 | 9.7 | 1.9 |
| L | Elk | 47.4 | 9.7 | 1.9 | 57.2 | 10.0 | 2.0 | 47.9 | 9.6 | 1.6 |
| W | Golem | 59.5 | 7.8 | 1.0 | 63.5 | 8.1 | 1.7 | 59.2 | 8.0 | 1.6 |
| L | Golem | 59.2 | 8.0 | 1.6 | 63.5 | 8.1 | 1.7 | 59.5 | 7.8 | 1.0 |
| W | Monolith | 85.8 | 5.3 | 0.3 | 87.1 | 4.4 | 0.6 | 90.0 | 3.3 | 0.4 |
| L | Monolith | 90.0 | 3.3 | 0.4 | 87.1 | 4.4 | 0.6 | 85.8 | 5.3 | 0.3 |
| W | GemCl | 35.1 | 4.0 | 5.5 | 35.2 | 5.5 | 7.3 | 34.8 | 4.1 | 6.2 |
| L | GemCl | 34.8 | 4.1 | 6.2 | 35.2 | 5.5 | 7.3 | 35.1 | 4.0 | 5.5 |
| W | GoldCl | 53.4 | 2.4 | 9.0 | 55.1 | 3.5 | 9.6 | 53.6 | 2.5 | 8.0 |
| L | GoldCl | 53.6 | 2.5 | 8.0 | 55.1 | 3.5 | 9.6 | 53.4 | 2.4 | 9.0 |

Upper bound on gems left asleep per game (each asleep round = 1/(respawn+15) of a farm cycle): W: own 974, mid 407, enemy 977; L: own 977, mid 407, enemy 974

| side | own captures/game (gems) | mid captures/game (gems) | enemy captures/game (gems) | r1-300 own/mid/enemy |
|---|---|---|---|---|
| W | 42.8 (808) | 5.8 (164) | 5.7 (130) | 18.4/2.0/1.7 |
| L | 40.7 (736) | 3.8 (88) | 3.5 (68) | 17.8/1.5/1.2 |

## 5. Deaths

| metric | W | L |
|---|---|---|
| deaths/game (to champions + camps) | 2.4 + 0.22 | 8.0 + 0.26 |
| median first-death round (none = length+1) | 385 | 266 |
| % of games this side died first | 30.6 | 59.7 |
| % alone (no ally within 8) | 19.9 | 19.4 |
| % ally within 4 | 62.1 | 63.1 |
| % 2+ enemies within 8 | 74.2 | 82.9 |
| % on own ground | 54.7 | 75.2 |
| % on mid ground | 19.9 | 12.6 |
| % on enemy ground | 25.4 | 12.1 |
| % walking toward spawn (last 4 rounds) | 26.8 | 17.8 |
| % branch R in last 4 rounds | 77.7 | 63.9 |
| % carrying 30+ gems | 10.1 | 19.8 |
| mean enemies within 8 | 2.7 | 3.2 |
| mean gems carried at death | 15.5 | 34.0 |
| r1-300 deaths/game | 0.63 | 1.16 |

Gems lost at death by champion type, per game (% of the side's loss): W: Prism 21.4 (52.5%), Cassi 4.0 (9.9%), Vesper Vale 3.8 (9.3%), Ryth 2.9 (7.0%); L: Prism 211.1 (75.6%), Vesper Vale 20.2 (7.2%), Cassi 11.8 (4.2%), Ryth 9.5 (3.4%)

Deaths carrying 100+ gems: W 0.06/game holding 56.5% of gems lost; L 0.55/game holding 71.5% of gems lost

Branch at death (last D line): W: `R` 68.2%, `F` 12.9%, `E` 6.5%, `B` 3.0%, `U` 2.8%, `K` 1.8%; L: `R` 53.2%, `E` 29.6%, `F` 9.9%, `B` 2.4%, `U` 1.0%, `C` 0.9%

Deaths by (allies within 8, enemies within 8), per 10 games:

| side | allies\enemies | 0 | 1 | 2 | 3+ |
|---|---|---|---|---|---|
| W | 0 | 0.3 | 1.5 | 1.4 | 2.0 |
| W | 1 | 0.4 | 1.3 | 1.4 | 2.3 |
| W | 2 | 0.3 | 1.1 | 1.2 | 3.0 |
| W | 3+ | 0.6 | 1.3 | 1.8 | 6.5 |
| L | 0 | 0.4 | 3.7 | 3.2 | 8.6 |
| L | 1 | 0.5 | 3.3 | 3.5 | 13.6 |
| L | 2 | 0.4 | 2.4 | 2.9 | 13.8 |
| L | 3+ | 0.6 | 2.8 | 3.4 | 19.1 |

## 6. Kills and fights

| side | kills/game | r1-300 kills/game | fights/game | initiated % | won on kills % | lost on kills % | net bag gems/game |
|---|---|---|---|---|---|---|---|
| W | 8.0 | 1.05 | 28.2 | 49.6 | 23.5 | 6.9 | 236 |
| L | 2.4 | 0.54 | 28.2 | 50.4 | 6.9 | 23.5 | -236 |

By fight size (participants, side v enemy): fights per game, then net kills per fight (killed - lost):

| side | 1v1 | 1v2 | 1v3+ | 2v1 | 2v2 | 2v3+ | 3+v1 | 3+v2 | 3+v3+ |
|---|---|---|---|---|---|---|---|---|---|
| W | 14.61 / +0.09 | 2.48 / +0.13 | 0.68 / +0.07 | 2.96 / +0.28 | 1.80 / +0.21 | 1.04 / +0.21 | 1.37 / +0.56 | 1.27 / +0.54 | 2.00 / +0.49 |
| L | 14.61 / -0.09 | 2.96 / -0.28 | 1.37 / -0.56 | 2.48 / -0.13 | 1.80 / -0.21 | 1.27 / -0.54 | 0.68 / -0.07 | 1.04 / -0.21 | 2.00 / -0.49 |
| pooled | 14.61 / +0.00 | 2.72 / -0.09 | 1.02 / -0.35 | 2.72 / +0.09 | 1.80 / +0.00 | 1.16 / -0.20 | 1.02 / +0.35 | 1.16 / +0.20 | 2.00 / +0.00 |

By head-count difference at the start (own minus enemy champions alive within 8 of the fight, previous round end): fights per game / net kills per fight / % won on kills:

| side | -3 | -2 | -1 | 0 | 1 | 2 | 3 |
|---|---|---|---|---|---|---|---|
| W | 1.29 / +0.18 / 20.8 | 2.36 / +0.14 / 18.5 | 4.83 / +0.14 / 18.6 | 7.87 / +0.14 / 18.8 | 5.58 / +0.21 / 24.1 | 3.64 / +0.30 / 32.3 | 2.64 / +0.36 / 38.6 |
| L | 2.64 / -0.36 / 4.6 | 3.64 / -0.30 / 5.5 | 5.58 / -0.21 / 5.9 | 7.87 / -0.14 / 6.9 | 4.83 / -0.14 / 8.1 | 2.36 / -0.14 / 9.6 | 1.29 / -0.18 / 11.0 |
| pooled | 1.97 / -0.18 / 9.9 | 3.00 / -0.13 / 10.6 | 5.20 / -0.05 / 11.8 | 7.87 / +0.00 / 12.9 | 5.20 / +0.05 / 16.7 | 3.00 / +0.13 / 23.4 | 1.97 / +0.18 / 29.5 |

## 7. What decides games

| gems, round | games reaching it | tied | leader wins % | lead 1-49 | lead 50-149 | lead 150+ |
|---|---|---|---|---|---|---|
| tributed r200 | 1359 | 382 | 50.6 | 48.2 (n=639) | 54.5 (n=303) | 60.0 (n=35) |
| tributed r400 | 1282 | 71 | 60.5 | 54.4 (n=540) | 58.9 (n=450) | 78.7 (n=221) |
| tributed r600 | 923 | 28 | 70.3 | 56.2 (n=288) | 71.1 (n=308) | 82.9 (n=299) |
| tributed+carried r200 | 1359 | 80 | 64.1 | 56.3 (n=730) | 66.9 (n=356) | 88.6 (n=193) |
| tributed+carried r400 | 1282 | 21 | 76.1 | 58.8 (n=408) | 72.7 (n=344) | 92.3 (n=509) |
| tributed+carried r600 | 923 | 20 | 82.9 | 61.0 (n=213) | 81.2 (n=208) | 93.4 (n=482) |

| predictor | win % |
|---|---|
| team that did not die first wins | 66.1 (n=1228) |
| more kills wins | 86.3 (n=1121) |
| more r1-300 kills wins | 74.6 (n=654) |
| more gems captured wins | 77.8 (n=1353) |
| more r1-300 gems captured wins | 67.4 (n=1317) |
| fewer gems lost at death wins | 86.9 (n=1126) |
| more mid-group captures wins | 76.1 (n=607) |

Games where neither side tributes 200: 1 (mut-one-gem-6142100217064).

Game length: median 719, quartiles 551-982, min 187, max 2000; 3.8% reach round 2000; 96.2% end on 1000 gems.

## Examples

**bagdeath** (1153 in all, largest first, one per game):

- `replays/batch-20261113-142239-ab-mx-phoebe-mirror-study/083-gen-classic-6142100001025-12.repl26a` (6d640b650967ce81) r1956 team A (W): Prism died with 2901 gems (champ, allies<=8 0, enemies<=8 1, branch R)
- `replays/batch-20261113-142239-ab-mx-phoebe-mirror-study/1271-gen-ladder05-6142100018011-12.repl26a` (e5ec026b47f69a80) r1090 team A (L): Prism died with 2455 gems (champ, allies<=8 0, enemies<=8 2, branch E)
- `replays/batch-20261113-142239-ab-mx-phoebe-mirror-study/1363-gen-ladder05-6142100018057-12.repl26a` (ab252d126ed77195) r912 team A (L): Prism died with 2264 gems (champ, allies<=8 4, enemies<=8 2, branch R)
- `replays/batch-20261113-142239-ab-mx-phoebe-mirror-study/1585-gen-ladder05-6142100218042-12.repl26a` (ae40953c3c9875f5) r1069 team B (L): Prism died with 2097 gems (champ, allies<=8 0, enemies<=8 1, branch R)
- `replays/batch-20261113-142239-ab-mx-phoebe-mirror-study/869-gen-ladder-6142100200034-12.repl26a` (4c10bcbd555cd44d) r1179 team A (L): Prism died with 2056 gems (champ, allies<=8 0, enemies<=8 1, branch E)
- `replays/batch-20261113-142239-ab-mx-phoebe-mirror-study/787-gen-ladder-6142100100105-12.repl26a` (36ddd80a7cae0254) r1302 team B (W): Prism died with 1948 gems (champ, allies<=8 0, enemies<=8 3, branch E)

**stolen** (2991 in all, largest first, one per game):

- `replays/batch-20261113-142239-ab-mx-phoebe-mirror-study/2699-mut-vault-6142100317035-12.repl26a` (b121b447be92ea0d) r1319 team A (L): GemCl (343 gems, own) cleared r33 stolen
- `replays/batch-20261113-142239-ab-mx-phoebe-mirror-study/055-gen-classic-6142100001011-12.repl26a` (5b7691563b64a8e2) r794 team B (W): Monolith (256 gems, enemy) cleared r786 stolen
- `replays/batch-20261113-142239-ab-mx-phoebe-mirror-study/1541-gen-ladder05-6142100218020-12.repl26a` (259d75adcfb01705) r442 team B (L): Monolith (256 gems, own) cleared r436 stolen
- `replays/batch-20261113-142239-ab-mx-phoebe-mirror-study/1675-gen-ladder05-6142100318024-12.repl26a` (cc6ae688737ef421) r986 team A (L): Monolith (256 gems, own) cleared r976 stolen
- `replays/batch-20261113-142239-ab-mx-phoebe-mirror-study/1727-gen-ladder05-6142100318050-12.repl26a` (08673a8d983edbe7) r1424 team A (L): Monolith (256 gems, enemy) cleared r1410 stolen
- `replays/batch-20261113-142239-ab-mx-phoebe-mirror-study/1829-gen-monolith-6142100008002-12.repl26a` (b507380b1e314f92) r669 team A (W): Monolith (256 gems, own) cleared r659 stolen

**idle-off30** (2983 in all, largest first, one per game):

- `replays/batch-20261113-142239-ab-mx-phoebe-mirror-study/1135-gen-ladder-6142100300055-12.repl26a` (f5eda1c392eca674) r528 team B (L): Ryth#4 idle off spawn 1456 rounds at (3, 23) branch U
- `replays/batch-20261113-142239-ab-mx-phoebe-mirror-study/1011-gen-ladder-6142100200105-12.repl26a` (41d52620ef5dce12) r569 team A (W): Issac#1 idle off spawn 1430 rounds at (23, 22) branch U
- `replays/batch-20261113-142239-ab-mx-phoebe-mirror-study/945-gen-ladder-6142100200072-12.repl26a` (08b4340afbff777b) r878 team A (L): Ryth#0 idle off spawn 1102 rounds at (16, 17) branch U
- `replays/batch-20261113-142239-ab-mx-phoebe-mirror-study/2309-mut-butterfly-6142100317056-12.repl26a` (9f6881bcd31dcd38) r425 team B (W): Cassi#8 idle off spawn 853 rounds at (46, 32) branch B
- `replays/batch-20261113-142239-ab-mx-phoebe-mirror-study/1847-gen-monolith-6142100208001-12.repl26a` (9cea494390748800) r1159 team A (W): Vesper Vale#0 idle off spawn 842 rounds at (25, 13) branch U
- `replays/batch-20261113-142239-ab-mx-phoebe-mirror-study/2177-mut-05quilt-6142100219002-12.repl26a` (bc334ba1403e0804) r131 team A (L): Vesper Vale#0 idle off spawn 564 rounds at (16, 14) branch F

