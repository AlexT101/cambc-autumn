# s1 farm calibration: 2048 traced team-games, 513933 choices (250.9/tg), 240.0/tg priced

### Champion time by outcome (all choices)

| outcome | choices/tg | rounds/tg | % of choice time | median rounds | share gems/tg |
|---|---|---|---|---|---|
| ours | 54.7 | 1271 | 33 | 20 | 892.3 |
| ally | 6.7 | 152 | 4 | 18 | 0.0 |
| enemy | 11.4 | 181 | 5 | 10 | 0.0 |
| switched | 170.3 | 2006 | 53 | 8 | 0.0 |
| died | 4.9 | 100 | 3 | 14 | 0.0 |
| gameend | 3.0 | 92 | 2 | 15 | 0.0 |

### Switched-away choices by stage

| stage | choices/tg | rounds/tg | median rounds | priced R (med) |
|---|---|---|---|---|
| a before arrival | 109.1 | 879 | 5 | 39 |
| b clearing | 12.6 | 215 | 13 | 29 |
| c cleared, left before payout | 40.2 | 762 | 16 | 27 |
| d at a respawning group | 8.4 | 150 | 14 | 26 |

| what became of the group | choices/tg | rounds/tg | median rounds |
|---|---|---|---|
| enemy captured it after | 4.4 | 44 | 4 |
| enemy cleared it | 8.5 | 137 | 11 |
| nothing happened to it | 109.1 | 1001 | 5 |
| team captured it after | 45.2 | 762 | 15 |
| team cleared, no payout in window | 3.1 | 62 | 16 |

Switched rounds not spent closing on the next choice (upper bound): 1509/tg of 2006/tg.
Flip-flops (A, B, back to A within 20 rounds): 22.6/tg, 213 rounds/tg.

Switched within 2 rounds: 35.8/tg (21% of switches), 50 rounds/tg.

### Priced value deciles (priced choices)

| decile | v range | n/tg | ours % | priced gem rate (part x gems / pay rounds) | real gem rate (share gems / rounds, all) | ratio |
|---|---|---|---|---|---|---|
| 1 | 0.000-0.089 | 24.0 | 7 | 0.145 | 0.010 | 0.07 |
| 2 | 0.089-0.169 | 24.0 | 8 | 0.195 | 0.037 | 0.19 |
| 3 | 0.169-0.252 | 24.0 | 11 | 0.245 | 0.063 | 0.26 |
| 4 | 0.252-0.350 | 24.0 | 14 | 0.293 | 0.091 | 0.31 |
| 5 | 0.350-0.476 | 24.0 | 17 | 0.349 | 0.121 | 0.35 |
| 6 | 0.476-0.656 | 24.0 | 21 | 0.421 | 0.167 | 0.40 |
| 7 | 0.656-0.940 | 24.0 | 25 | 0.500 | 0.237 | 0.47 |
| 8 | 0.940-1.431 | 24.0 | 31 | 0.582 | 0.345 | 0.59 |
| 9 | 1.431-2.559 | 24.0 | 38 | 0.679 | 0.481 | 0.71 |
| 10 | 2.559-594.166 | 24.0 | 47 | 1.014 | 0.677 | 0.67 |

### By mode

| mclass | choices/tg | ours % | ally % | enemy % | switched % | died % | priced R (med) | real rounds ours (med) | real/priced R ours (med) | priced gems ours | real gems ours | gem rate priced | gem rate real | real/priced | team-attr real/priced | value-unit real/priced | rounds sunk/tg | gems got/tg |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| crew-join | 84.0 | 18 | 4 | 3 | 72 | 2 | 22 | 20 | 1.18 | 10.2 | 21.0 | 0.404 | 0.255 | 0.63 | 1.08 | 0.93 | 908 | 318.1 |
| crew-propose | 11.6 | 5 | 2 | 2 | 88 | 2 | 52 | 34 | 0.81 | 21.9 | 38.4 | 0.417 | 0.118 | 0.28 | 0.74 | 0.56 | 151 | 20.3 |
| other-G | 1.3 | 93 | 1 | 0 | 6 | 0 | 5 | 5 | 1.00 | 20.7 | 22.0 | 4.520 | 4.864 | 1.08 | 1.16 | 1.06 | 0 | 26.3 |
| other-L | 1.1 | 67 | 9 | 0 | 24 | 0 | 10 | 8 | 0.82 | 18.1 | 19.3 | 1.800 | 2.173 | 1.21 | 1.84 | 1.21 | 1 | 14.1 |
| other-Q | 2.4 | 52 | 1 | 0 | 46 | 0 | 12 | 11 | 0.92 | 21.2 | 22.9 | 1.478 | 1.285 | 0.87 | 1.33 | 0.86 | 7 | 27.9 |
| other-T | 0.7 | 74 | 6 | 0 | 19 | 0 | 5 | 5 | 1.00 | 11.9 | 11.8 | 2.856 | 2.075 | 0.73 | 1.16 | 1.04 | 1 | 6.5 |
| solo | 127.4 | 24 | 2 | 6 | 64 | 2 | 37 | 22 | 0.83 | 12.2 | 12.8 | 0.369 | 0.193 | 0.52 | 0.93 | 0.85 | 1264 | 396.7 |
| solo-kite | 11.5 | 19 | 1 | 5 | 72 | 2 | 59 | 24 | 0.84 | 15.8 | 17.6 | 0.237 | 0.222 | 0.94 | 1.39 | 0.97 | 111 | 38.6 |

### By group type

| kind | choices/tg | ours % | ally % | enemy % | switched % | died % | priced R (med) | real rounds ours (med) | real/priced R ours (med) | priced gems ours | real gems ours | gem rate priced | gem rate real | real/priced | team-attr real/priced | value-unit real/priced | rounds sunk/tg | gems got/tg |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| cluster | 77.1 | 29 | 2 | 6 | 59 | 2 | 23 | 16 | 0.88 | 8.0 | 10.1 | 0.404 | 0.212 | 0.52 | 0.81 | 0.84 | 642 | 227.1 |
| elk | 52.7 | 17 | 3 | 4 | 73 | 2 | 37 | 25 | 0.87 | 23.8 | 31.7 | 0.470 | 0.315 | 0.67 | 1.16 | 0.86 | 648 | 285.8 |
| golem | 6.9 | 14 | 2 | 4 | 75 | 3 | 43 | 29 | 0.86 | 47.4 | 59.5 | 0.743 | 0.470 | 0.63 | 1.02 | 0.73 | 93 | 58.4 |
| monolith | 2.7 | 5 | 9 | 1 | 79 | 4 | 104 | 47 | 1.02 | 143.4 | 185.6 | 1.433 | 0.465 | 0.32 | 0.99 | 0.46 | 41 | 22.5 |
| wolf | 100.7 | 20 | 3 | 4 | 70 | 2 | 35 | 22 | 0.88 | 9.6 | 12.7 | 0.239 | 0.167 | 0.70 | 1.24 | 1.09 | 1018 | 254.8 |

### By priced walk steps

| dist | choices/tg | ours % | ally % | enemy % | switched % | died % | priced R (med) | real rounds ours (med) | real/priced R ours (med) | priced gems ours | real gems ours | gem rate priced | gem rate real | real/priced | team-attr real/priced | value-unit real/priced | rounds sunk/tg | gems got/tg |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0-5 | 32.2 | 41 | 3 | 2 | 51 | 2 | 11 | 9 | 0.90 | 9.9 | 12.3 | 0.710 | 0.460 | 0.65 | 1.09 | 0.93 | 201 | 163.4 |
| 11-20 | 76.4 | 19 | 3 | 5 | 69 | 2 | 29 | 24 | 0.88 | 12.6 | 17.2 | 0.394 | 0.215 | 0.55 | 0.96 | 0.81 | 792 | 255.1 |
| 21-35 | 50.2 | 15 | 2 | 6 | 74 | 2 | 43 | 35 | 0.88 | 16.0 | 20.2 | 0.343 | 0.170 | 0.50 | 0.84 | 0.71 | 602 | 149.5 |
| 36+ | 29.5 | 10 | 2 | 7 | 79 | 1 | 70 | 50 | 0.88 | 19.1 | 23.0 | 0.254 | 0.120 | 0.47 | 0.78 | 0.64 | 394 | 64.8 |
| 6-10 | 51.8 | 28 | 3 | 3 | 63 | 2 | 19 | 16 | 0.87 | 11.2 | 15.1 | 0.515 | 0.299 | 0.58 | 1.02 | 0.87 | 453 | 215.6 |

### By map side (group nearer our spawn = own)

| sideL | choices/tg | ours % | ally % | enemy % | switched % | died % | priced R (med) | real rounds ours (med) | real/priced R ours (med) | priced gems ours | real gems ours | gem rate priced | gem rate real | real/priced | team-attr real/priced | value-unit real/priced | rounds sunk/tg | gems got/tg |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| enemy | 54.7 | 9 | 1 | 12 | 75 | 3 | 37 | 21 | 0.90 | 13.7 | 17.6 | 0.342 | 0.123 | 0.36 | 0.58 | 0.45 | 552 | 82.8 |
| mid | 33.2 | 15 | 2 | 9 | 69 | 3 | 34 | 23 | 0.91 | 17.4 | 23.0 | 0.494 | 0.213 | 0.43 | 0.73 | 0.58 | 415 | 117.6 |
| own | 152.1 | 28 | 3 | 1 | 65 | 1 | 28 | 20 | 0.88 | 11.6 | 15.2 | 0.367 | 0.264 | 0.72 | 1.25 | 1.04 | 1475 | 648.1 |

### By side fraction (dist to our spawn / sum of both)

| side5 | choices/tg | ours % | ally % | enemy % | switched % | died % | priced R (med) | real rounds ours (med) | real/priced R ours (med) | priced gems ours | real gems ours | gem rate priced | gem rate real | real/priced | team-attr real/priced | value-unit real/priced | rounds sunk/tg | gems got/tg |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| a <.35 | 83.0 | 32 | 3 | 0 | 63 | 1 | 26 | 18 | 0.88 | 11.0 | 14.2 | 0.363 | 0.291 | 0.80 | 1.42 | 1.16 | 733 | 374.2 |
| b .35-.45 | 48.3 | 25 | 3 | 2 | 66 | 2 | 31 | 22 | 0.88 | 12.3 | 16.1 | 0.355 | 0.241 | 0.68 | 1.15 | 0.94 | 506 | 196.7 |
| c .45-.55 | 68.6 | 17 | 2 | 8 | 69 | 3 | 34 | 23 | 0.90 | 15.5 | 20.4 | 0.451 | 0.206 | 0.46 | 0.77 | 0.62 | 815 | 231.2 |
| d .55-.65 | 24.9 | 9 | 1 | 12 | 74 | 3 | 36 | 20 | 0.90 | 13.1 | 16.8 | 0.344 | 0.120 | 0.35 | 0.56 | 0.43 | 254 | 37.3 |
| e >.65 | 15.2 | 4 | 0 | 13 | 80 | 3 | 42 | 22 | 0.90 | 13.5 | 17.0 | 0.274 | 0.062 | 0.23 | 0.33 | 0.27 | 133 | 9.1 |

### By champion

| ctype | choices/tg | ours % | ally % | enemy % | switched % | died % | priced R (med) | real rounds ours (med) | real/priced R ours (med) | priced gems ours | real gems ours | gem rate priced | gem rate real | real/priced | team-attr real/priced | value-unit real/priced | rounds sunk/tg | gems got/tg |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Cassi | 43.8 | 13 | 2 | 4 | 77 | 3 | 34 | 24 | 0.93 | 10.0 | 12.0 | 0.308 | 0.103 | 0.33 | 1.03 | 0.34 | 503 | 67.7 |
| Heart of Ruin | 12.8 | 18 | 2 | 5 | 71 | 2 | 43 | 23 | 0.81 | 9.1 | 12.3 | 0.249 | 0.135 | 0.54 | 1.09 | 0.60 | 148 | 29.1 |
| Issac | 47.2 | 14 | 2 | 5 | 76 | 3 | 36 | 21 | 0.82 | 10.3 | 12.5 | 0.324 | 0.129 | 0.40 | 0.92 | 0.41 | 473 | 82.6 |
| Marcella | 5.7 | 27 | 3 | 7 | 60 | 2 | 26 | 17 | 0.92 | 10.8 | 14.0 | 0.461 | 0.252 | 0.55 | 0.89 | 0.59 | 55 | 22.0 |
| Prism | 35.8 | 40 | 2 | 4 | 51 | 1 | 27 | 18 | 0.89 | 19.7 | 26.6 | 0.656 | 0.714 | 1.09 | 1.28 | 1.09 | 236 | 385.2 |
| Ren | 5.9 | 24 | 2 | 5 | 67 | 1 | 34 | 23 | 0.83 | 8.4 | 10.5 | 0.325 | 0.153 | 0.47 | 0.85 | 0.58 | 60 | 14.8 |
| Ryth | 11.5 | 26 | 3 | 5 | 63 | 2 | 29 | 20 | 0.86 | 8.6 | 11.5 | 0.396 | 0.184 | 0.46 | 0.97 | 0.62 | 116 | 33.7 |
| Stellar | 1.7 | 19 | 3 | 3 | 73 | 1 | 31 | 23 | 0.91 | 11.2 | 16.0 | 0.368 | 0.207 | 0.56 | 1.26 | 0.65 | 17 | 5.2 |
| Tavi | 4.8 | 26 | 3 | 6 | 61 | 3 | 24 | 18 | 0.96 | 6.3 | 8.5 | 0.402 | 0.142 | 0.35 | 0.73 | 0.56 | 48 | 10.5 |
| Varg | 5.8 | 21 | 2 | 3 | 70 | 1 | 41 | 26 | 0.85 | 12.3 | 14.9 | 0.370 | 0.175 | 0.47 | 1.10 | 0.57 | 69 | 18.5 |
| Vendetta | 10.1 | 32 | 2 | 3 | 61 | 1 | 31 | 21 | 0.84 | 9.7 | 12.7 | 0.370 | 0.245 | 0.66 | 1.01 | 0.86 | 87 | 41.0 |
| Vesper Vale | 27.6 | 40 | 3 | 5 | 50 | 1 | 26 | 19 | 0.88 | 9.3 | 12.0 | 0.409 | 0.293 | 0.72 | 1.01 | 1.21 | 211 | 132.5 |
| Willow | 27.2 | 2 | 6 | 7 | 82 | 2 | 30 | 18 | 1.07 | 8.6 | 11.5 | 0.360 | 0.013 | 0.04 | 0.58 | 0.04 | 419 | 5.7 |

### Prism vs others

| prism | choices/tg | ours % | ally % | enemy % | switched % | died % | priced R (med) | real rounds ours (med) | real/priced R ours (med) | priced gems ours | real gems ours | gem rate priced | gem rate real | real/priced | team-attr real/priced | value-unit real/priced | rounds sunk/tg | gems got/tg |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Prism | 35.8 | 40 | 2 | 4 | 51 | 1 | 27 | 18 | 0.89 | 19.7 | 26.6 | 0.656 | 0.714 | 1.09 | 1.28 | 1.09 | 236 | 385.2 |
| other | 204.2 | 19 | 3 | 5 | 70 | 2 | 32 | 21 | 0.88 | 9.6 | 12.2 | 0.340 | 0.147 | 0.43 | 0.94 | 0.86 | 2206 | 463.3 |

### By game phase (choice round)

| phase | choices/tg | ours % | ally % | enemy % | switched % | died % | priced R (med) | real rounds ours (med) | real/priced R ours (med) | priced gems ours | real gems ours | gem rate priced | gem rate real | real/priced | team-attr real/priced | value-unit real/priced | rounds sunk/tg | gems got/tg |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1-100 | 33.6 | 22 | 2 | 3 | 71 | 1 | 34 | 22 | 0.87 | 10.0 | 14.3 | 0.317 | 0.193 | 0.61 | 1.15 | 1.04 | 370 | 107.6 |
| 1001+ | 20.0 | 20 | 2 | 6 | 65 | 4 | 28 | 17 | 0.92 | 9.3 | 11.6 | 0.368 | 0.157 | 0.43 | 0.74 | 0.54 | 207 | 45.4 |
| 101-300 | 61.6 | 23 | 3 | 4 | 69 | 1 | 31 | 21 | 0.88 | 12.3 | 16.4 | 0.368 | 0.247 | 0.67 | 1.16 | 0.99 | 604 | 235.6 |
| 301-600 | 78.6 | 23 | 3 | 5 | 67 | 2 | 31 | 20 | 0.88 | 14.0 | 17.9 | 0.414 | 0.266 | 0.64 | 1.07 | 0.88 | 781 | 317.9 |
| 601-1000 | 46.2 | 20 | 3 | 6 | 66 | 3 | 30 | 19 | 0.90 | 12.5 | 15.7 | 0.390 | 0.207 | 0.53 | 0.91 | 0.70 | 481 | 142.1 |

### By group state at choice

| state | choices/tg | ours % | ally % | enemy % | switched % | died % | priced R (med) | real rounds ours (med) | real/priced R ours (med) | priced gems ours | real gems ours | gem rate priced | gem rate real | real/priced | team-attr real/priced | value-unit real/priced | rounds sunk/tg | gems got/tg |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| alive | 137.2 | 19 | 2 | 6 | 69 | 2 | 33 | 19 | 0.85 | 11.3 | 15.3 | 0.356 | 0.208 | 0.58 | 0.94 | 0.96 | 1324 | 405.6 |
| cleared | 9.5 | 47 | 5 | 7 | 38 | 2 | 10 | 6 | 0.90 | 14.6 | 14.9 | 1.782 | 0.866 | 0.49 | 0.91 | 0.64 | 42 | 66.2 |
| respawning | 93.3 | 23 | 3 | 3 | 69 | 2 | 31 | 23 | 0.91 | 13.3 | 17.4 | 0.373 | 0.228 | 0.61 | 1.11 | 0.85 | 1076 | 376.7 |

### By bag (banking: the bank cycle is priced in)

| bank | choices/tg | ours % | ally % | enemy % | switched % | died % | priced R (med) | real rounds ours (med) | real/priced R ours (med) | priced gems ours | real gems ours | gem rate priced | gem rate real | real/priced | team-attr real/priced | value-unit real/priced | rounds sunk/tg | gems got/tg |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| banking | 2.6 | 18 | 5 | 9 | 62 | 5 | 27 | 21 | 0.87 | 8.0 | 9.8 | 0.367 | 0.105 | 0.29 | 0.63 | 0.62 | 32 | 4.5 |
| carrying | 1.4 | 8 | 3 | 2 | 60 | 2 | 53 | 20 | 1.00 | 64.8 | 48.6 | 2.524 | 0.273 | 0.11 | 0.41 | 0.11 | 17 | 5.5 |
| empty | 236.0 | 22 | 3 | 5 | 68 | 2 | 31 | 20 | 0.88 | 12.3 | 16.1 | 0.366 | 0.232 | 0.63 | 1.08 | 0.92 | 2393 | 838.5 |

### Solo (S/K) by group type

| kind | choices/tg | ours % | ally % | enemy % | switched % | died % | priced R (med) | real rounds ours (med) | real/priced R ours (med) | priced gems ours | real gems ours | gem rate priced | gem rate real | real/priced | team-attr real/priced | value-unit real/priced | rounds sunk/tg | gems got/tg |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| cluster | 60.6 | 29 | 2 | 7 | 59 | 2 | 26 | 17 | 0.85 | 7.7 | 8.1 | 0.374 | 0.162 | 0.43 | 0.70 | 0.78 | 521 | 142.5 |
| elk | 19.9 | 22 | 2 | 6 | 66 | 2 | 54 | 30 | 0.80 | 29.7 | 31.5 | 0.548 | 0.353 | 0.64 | 1.05 | 0.80 | 241 | 136.4 |
| golem | 2.2 | 26 | 2 | 7 | 59 | 3 | 53 | 32 | 0.81 | 56.4 | 59.2 | 1.079 | 0.683 | 0.63 | 0.89 | 0.71 | 29 | 33.3 |
| monolith | 0.1 | 8 | 70 | 3 | 17 | 2 | 12 | 6 | 0.67 | 329.8 | 198.4 | 19.841 | 2.853 | 0.14 | 1.88 | 0.28 | 1 | 2.0 |
| wolf | 56.1 | 19 | 2 | 5 | 71 | 2 | 49 | 27 | 0.81 | 10.7 | 11.3 | 0.228 | 0.133 | 0.58 | 1.11 | 1.06 | 584 | 121.0 |

### Crew (C/J) by group type

| kind | choices/tg | ours % | ally % | enemy % | switched % | died % | priced R (med) | real rounds ours (med) | real/priced R ours (med) | priced gems ours | real gems ours | gem rate priced | gem rate real | real/priced | team-attr real/priced | value-unit real/priced | rounds sunk/tg | gems got/tg |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| cluster | 15.4 | 27 | 3 | 3 | 65 | 2 | 12 | 15 | 1.49 | 6.9 | 16.4 | 0.560 | 0.356 | 0.64 | 0.93 | 0.91 | 120 | 66.8 |
| elk | 31.5 | 12 | 3 | 3 | 78 | 2 | 32 | 25 | 1.00 | 16.1 | 32.4 | 0.363 | 0.243 | 0.67 | 1.26 | 0.94 | 405 | 124.1 |
| golem | 4.6 | 7 | 2 | 2 | 84 | 2 | 40 | 27 | 1.01 | 29.8 | 59.2 | 0.494 | 0.272 | 0.55 | 1.07 | 0.70 | 64 | 20.1 |
| monolith | 2.5 | 4 | 6 | 1 | 82 | 4 | 111 | 50 | 1.05 | 126.2 | 184.4 | 1.290 | 0.430 | 0.33 | 0.68 | 0.46 | 41 | 20.4 |
| wolf | 41.6 | 18 | 4 | 3 | 73 | 2 | 23 | 20 | 1.14 | 7.2 | 14.6 | 0.243 | 0.179 | 0.74 | 1.29 | 1.11 | 430 | 107.0 |

### Parts by mode (paid choices)

| mclass | n/tg | walk priced | walk real | clear priced | clear real | hold priced | hold real | total priced (no bank) | total real |
|---|---|---|---|---|---|---|---|---|---|
| crew-join | 15.1 | 11.1 | 7.6 | 6.7 | 8.5 | 1.5 | 6.2 | 19.3 | 22.4 |
| crew-propose | 0.5 | 13.4 | 9.8 | 25.4 | 22.8 | 5.7 | 7.1 | 44.5 | 39.7 |
| other-G | 1.2 | 2.5 | 1.2 | 0.0 | 0.0 | 2.0 | 3.2 | 4.6 | 4.4 |
| other-L | 0.7 | 5.5 | 3.9 | 0.0 | 0.0 | 4.7 | 3.8 | 10.2 | 7.7 |
| other-Q | 1.2 | 6.5 | 3.2 | 2.8 | 1.7 | 4.5 | 6.6 | 13.8 | 12.1 |
| other-T | 0.6 | 2.5 | 1.5 | 0.0 | 0.0 | 2.2 | 2.9 | 4.7 | 4.5 |
| solo | 31.0 | 13.8 | 10.6 | 10.8 | 8.1 | 5.4 | 6.6 | 30.0 | 25.4 |
| solo-kite | 2.2 | 13.0 | 12.9 | 17.0 | 8.3 | 4.7 | 7.4 | 34.7 | 28.8 |

### Parts by group type (paid choices)

| kind | n/tg | walk priced | walk real | clear priced | clear real | hold priced | hold real | total priced (no bank) | total real |
|---|---|---|---|---|---|---|---|---|---|
| cluster | 22.5 | 11.9 | 8.8 | 3.7 | 3.5 | 4.7 | 6.8 | 20.3 | 19.2 |
| elk | 9.0 | 14.5 | 11.0 | 13.8 | 11.6 | 3.5 | 6.0 | 31.8 | 28.7 |
| golem | 1.0 | 15.3 | 12.0 | 17.7 | 14.2 | 3.3 | 5.9 | 36.3 | 32.1 |
| monolith | 0.1 | 16.1 | 13.2 | 35.8 | 37.2 | 1.4 | 5.9 | 53.2 | 56.3 |
| wolf | 20.0 | 11.7 | 8.7 | 13.1 | 10.5 | 3.7 | 6.2 | 28.5 | 25.5 |

### Parts by walk (paid choices)

| dist | n/tg | walk priced | walk real | clear priced | clear real | hold priced | hold real | total priced (no bank) | total real |
|---|---|---|---|---|---|---|---|---|---|
| 0-5 | 13.3 | 3.5 | 1.1 | 5.0 | 4.6 | 3.6 | 6.0 | 12.1 | 11.7 |
| 11-20 | 14.8 | 14.3 | 10.9 | 10.7 | 8.9 | 4.2 | 6.6 | 29.2 | 26.5 |
| 21-35 | 7.4 | 23.4 | 20.0 | 13.5 | 10.6 | 4.6 | 6.5 | 41.5 | 37.3 |
| 36+ | 2.8 | 36.7 | 33.3 | 16.2 | 12.3 | 4.9 | 6.4 | 57.8 | 52.2 |
| 6-10 | 14.3 | 8.0 | 4.7 | 8.4 | 7.4 | 4.0 | 6.6 | 20.4 | 18.8 |

### Parts, Prism vs others (paid choices)

| prism | n/tg | walk priced | walk real | clear priced | clear real | hold priced | hold real | total priced (no bank) | total real |
|---|---|---|---|---|---|---|---|---|---|
| Prism | 14.5 | 11.3 | 8.6 | 7.7 | 5.8 | 4.3 | 6.4 | 23.3 | 20.9 |
| other | 38.1 | 12.7 | 9.4 | 10.0 | 8.6 | 4.0 | 6.4 | 26.7 | 24.6 |

### Parts by state at choice (paid choices)

| state | n/tg | walk priced | walk real | clear priced | clear real | hold priced | hold real | total priced (no bank) | total real |
|---|---|---|---|---|---|---|---|---|---|
| alive | 26.5 | 11.4 | 8.3 | 10.9 | 8.5 | 4.2 | 6.8 | 26.5 | 23.7 |
| cleared | 4.4 | 4.1 | 3.4 | 0.0 | -0.1 | 4.0 | 4.4 | 8.2 | 7.9 |
| respawning | 21.7 | 15.2 | 11.6 | 9.4 | 8.6 | 3.9 | 6.3 | 28.5 | 26.5 |

