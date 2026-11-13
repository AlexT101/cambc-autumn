# s3 tables

1024 games (922 with a Prism on each side). 494 of the 512 map pairs are the same game played twice (mirror, sides swapped), so the independent sample is ~530 games; counts are over all 1,024.

## Q1 encounters (both Prisms alive within 6; a new one after 20 rounds apart)

| Focus x health ratio | encounters | weak dies <=20 r | strong dies <=20 r |
|---|---|---|---|
| <1.2 | 730 | 6% | 4% |
| 1.2-1.5 | 478 | 12% | 4% |
| 1.5-2 | 496 | 16% | 3% |
| 2-3 | 370 | 21% | 3% |
| 3+ | 1352 | 53% | 1% |

Ratio >= 1.5: 2218 encounters (2.41 a both-Prism game), in 582 games.

Who closed the distance (sum over the 10 rounds before of each Prism's own step against the other's last tile; a side "closed" with a sum <= -2):

| closer | encounters | share | weak dies <=20 r |
|---|---|---|---|
| weak | 1108 | 50% | 57% |
| strong | 491 | 22% | 22% |
| both | 523 | 24% | 23% |
| neither | 96 | 4% | 15% |

By the weak Prism's activity (E if it was in stop_ender in the 10 rounds before, else its branch at the encounter):

| weak doing | n | weak dies | weak closed | strong closed | strong branch % | weak sees strong | seen <=10 r | weak farm target <=4 of strong | <=8 | weak on own ground | weak bag q1/med/q3 | strong bag | strong 2-turn burst >= weak hp | weak burst >= strong hp |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F farm | 947 | 18% | 37% | 24% | F 63 T 13 C 11 P 4 | 59% | 64% | 54% | 79% | 93% | 4 / 49 / 146 | 162 / 328 / 560 | 35% | 2% |
| E stop_ender | 627 | 86% | 93% | 3% | T 98 B 2 | 99% | 100% | 19% | 47% | 97% | 0 / 0 / 62 | 886 / 1214 / 1602 | 87% | 1% |
| R retreat | 257 | 28% | 10% | 55% | F 57 C 26 B 12 U 1 | 93% | 98% | 25% | 59% | 86% | 38 / 106 / 250 | 175 / 311 / 518 | 56% | 1% |
| B bank | 110 | 18% | 49% | 22% | T 38 B 22 F 22 U 11 | 71% | 76% | 0% | 5% | 96% | 17 / 42 / 497 | 492 / 615 / 696 | 60% | 24% |
| C chase | 103 | 21% | 47% | 14% | F 46 C 18 T 16 R 9 | 50% | 51% | 30% | 66% | 90% | 0 / 42 / 111 | 154 / 280 / 490 | 25% | 0% |
| U altar guard | 62 | 52% | 45% | 35% | T 37 B 35 U 13 F 6 | 58% | 58% | 0% | 0% | 97% | 0 / 0 / 16 | 572 / 1148 / 1687 | 77% | 3% |
| P hold | 32 | 31% | 19% | 44% | F 69 C 19 R 6 B 6 | 44% | 44% | 6% | 100% | 81% | 39 / 106 / 206 | 190 / 346 / 420 | 44% | 0% |
| X contest | 31 | 6% | 19% | 19% | F 81 C 13 k 6 | 100% | 100% | 74% | 87% | 94% | 0 / 96 / 215 | 34 / 194 / 362 | 6% | 0% |
| T tribute | 20 | 20% | 0% | 100% | B 70 F 20 C 10 | 80% | 90% | 0% | 20% | 100% | 511 / 827 / 891 | 455 / 639 / 722 | 90% | 60% |
| G siege | 19 | 32% | 63% | 11% | T 32 G 26 W 21 F 21 | 58% | 58% | 16% | 32% | 89% | 0 / 0 / 139 | 349 / 2249 / 2249 | 53% | 11% |
| other | 10 | 20% | 0% | 60% | F 60 G 20 R 20 | 80% | 80% | 40% | 60% | 100% | 51 / 194 / 340 | 305 / 555 / 583 | 60% | 0% |

Weak farming (947): its farm group on its own side 339, middle 289, the strong side 319. Strong Prism standing on its own ground 712.

## Q2 Prism deaths

All Prism deaths by killer: Prism 1109, Vesper Vale 150, Cassi 44, Issac 41, Heart of Ruin 35, Marcella 26, camp 25, Ryth 11

First Prism death in both-Prism games: 532; the victim's team lost 485. Killers: Prism 389, Vesper Vale 51, camp 21, Heart of Ruin 21, Cassi 14, Issac 10.


First Prism death per game, by the enemy Prism (389). Power = killer/victim Focus x health at first sight; weak >= 1.5. Burst: both ready spells (1.5F stun, 1.0F ground) and two basics.

| context | power | n | victim team won | rounds first sight -> death | victim saw killer | dist at first sight | victim steps away/toward/still % | victim branches % | killer branches % | victim spawn steps | nearest ally | nearest altar | kept recall cut | fought back (dmg>0) | dmg to killer | killer health at end | victim 2-turn burst >= killer hp at sight | killer burst >= victim hp | retreat walked in reach with a spell ready | forgone casts >= killer end hp | bag lost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R retreat (last 5) | weak | 144 | 8% | 4 / 9 / 15 | 93% | 4 / 5 / 7 | 35/23/42 | R 61 F 25 B 9 T 2 | F 41 C 20 R 15 | 15 / 31 / 45 | 2 / 4 / 10 | 4 / 8 / 13 | 15% | 71% | 0 / 475 / 881 | 0.51 / 0.77 / 1.00 | 7% | 44% | 34% | 7 | 40 / 160 / 277 |
| R retreat (last 5) | not weak | 95 | 11% | 5 / 12 / 23 | 94% | 5 / 7 / 8 | 29/25/47 | R 45 F 34 T 9 C 6 | F 41 R 31 B 12 | 17 / 26 / 37 | 2 / 4 / 9 | 3 / 7 / 11 | 29% | 69% | 0 / 597 / 1375 | 0.34 / 0.60 / 0.91 | 25% | 34% | 36% | 20 | 139 / 246 / 513 |
| E stop_ender | weak | 61 | 7% | 8 / 17 / 39 | 100% | 7 / 7 / 8 | 32/39/29 | R 39 E 27 B 26 F 6 | T 50 B 28 R 10 | 15 / 24 / 31 | 2 / 3 / 8 | 3 / 3 / 4 | 57% | 77% | 122 / 1354 / 1951 | 0.56 / 0.68 / 0.96 | 13% | 69% | 25% | 6 | 50 / 426 / 554 |
| E stop_ender | not weak | 43 | 0% | 16 / 35 / 98 | 100% | 7 / 8 / 8 | 31/33/36 | B 34 R 30 T 14 F 12 | B 37 T 27 R 27 | 17 / 34 / 47 | 1 / 2 / 4 | 3 / 4 / 5 | 53% | 49% | 0 / 0 / 1580 | 0.43 / 0.85 / 1.00 | 72% | 84% | 42% | 8 | 540 / 595 / 715 |
| other | weak | 16 | 0% | 5 / 5 / 9 | 50% | 7 / 7 / 9 | 15/51/33 | F 36 T 29 B 20 R 16 | F 40 E 20 P 18 | 20 / 31 / 40 | 2 / 3 / 11 | 1 / 9 / 15 | 0% | 0% | 0 / 0 / 0 | 0.87 / 1.00 / 1.00 | 25% | 62% | 0% | 0 | 190 / 298 / 532 |
| other | not weak | 24 | 0% | 5 / 5 / 5 | 29% | 6 / 7 / 7 | 21/38/41 | F 61 R 19 B 9 C 4 | F 57 R 17 P 9 | 18 / 32 / 48 | 2 / 3 / 7 | 2 / 6 / 10 | 33% | 8% | 0 / 0 / 0 | 0.92 / 1.00 / 1.00 | 33% | 58% | 8% | 0 | 359 / 504 / 591 |
| killer tributing | weak | 2 | 0% | 5 / 5 / 5 | 0% | 9 / 9 / 9 | 0/100/0 | B 100 | T 100 | 29 / 29 / 29 | 5 / 5 / 5 | 6 / 6 / 6 | 0% | 0% | 0 / 0 / 0 | 1.00 / 1.00 / 1.00 | 100% | 100% | 0% | 0 | 497 / 497 / 497 |
| killer tributing | not weak | 4 | 0% | 5 / 23 / 23 | 50% | 6 / 7 / 7 | 31/38/31 | B 64 R 36 | B 39 T 32 R 21 | 11 / 18 / 18 | 1 / 7 / 7 | 3 / 4 / 4 | 0% | 0% | 0 / 0 / 0 | 1.00 / 1.00 / 1.00 | 50% | 100% | 50% | 2 | 678 / 758 / 758 |

Every Prism death by the enemy Prism (1109, repeated deaths in one game included)

| context | power | n | victim team won | rounds first sight -> death | victim saw killer | dist at first sight | victim steps away/toward/still % | victim branches % | killer branches % | victim spawn steps | nearest ally | nearest altar | kept recall cut | fought back (dmg>0) | dmg to killer | killer health at end | victim 2-turn burst >= killer hp at sight | killer burst >= victim hp | retreat walked in reach with a spell ready | forgone casts >= killer end hp | bag lost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R retreat (last 5) | weak | 250 | 7% | 5 / 8 / 15 | 95% | 4 / 6 / 7 | 35/22/43 | R 60 F 26 B 5 U 4 | F 45 C 21 R 10 | 16 / 28 / 43 | 2 / 4 / 9 | 5 / 8 / 13 | 12% | 73% | 0 / 317 / 713 | 0.54 / 0.82 / 0.97 | 4% | 44% | 36% | 9 | 18 / 71 / 215 |
| R retreat (last 5) | not weak | 109 | 13% | 5 / 12 / 23 | 89% | 5 / 6 / 7 | 29/24/48 | R 46 F 34 T 9 C 5 | F 41 R 31 B 11 | 16 / 27 / 41 | 2 / 4 / 9 | 3 / 6 / 11 | 29% | 66% | 0 / 541 / 1375 | 0.36 / 0.61 / 0.94 | 26% | 29% | 37% | 24 | 137 / 252 / 535 |
| E stop_ender | weak | 611 | 1% | 5 / 7 / 16 | 100% | 7 / 7 / 8 | 19/53/28 | E 62 R 22 F 7 B 6 | T 65 B 20 R 9 | 10 / 17 / 26 | 2 / 3 / 6 | 3 / 3 / 4 | 46% | 91% | 225 / 688 / 1346 | 0.65 / 0.84 / 0.93 | 2% | 88% | 17% | 8 | 0 / 0 / 70 |
| E stop_ender | not weak | 45 | 0% | 16 / 34 / 98 | 100% | 7 / 8 / 8 | 31/33/36 | B 34 R 30 T 14 F 12 | B 37 T 28 R 27 | 14 / 27 / 47 | 1 / 2 / 3 | 3 / 4 / 5 | 56% | 47% | 0 / 0 / 1580 | 0.43 / 0.71 / 1.00 | 69% | 84% | 40% | 8 | 378 / 586 / 715 |
| other | weak | 38 | 5% | 0 / 5 / 5 | 47% | 6 / 7 / 9 | 9/49/43 | F 43 B 17 T 16 R 10 | F 44 E 11 P 11 | 18 / 31 / 40 | 2 / 3 / 4 | 1 / 6 / 12 | 0% | 5% | 0 / 0 / 0 | 0.82 / 1.00 / 1.00 | 11% | 79% | 0% | 0 | 14 / 58 / 284 |
| other | not weak | 24 | 0% | 5 / 5 / 5 | 29% | 6 / 7 / 7 | 21/38/41 | F 61 R 19 B 9 C 4 | F 57 R 17 P 9 | 18 / 32 / 48 | 2 / 3 / 7 | 2 / 6 / 10 | 33% | 8% | 0 / 0 / 0 | 0.92 / 1.00 / 1.00 | 33% | 58% | 8% | 0 | 359 / 504 / 591 |
| killer tributing | weak | 26 | 15% | 0 / 5 / 5 | 62% | 4 / 5 / 8 | 28/30/42 | B 34 R 31 T 22 F 12 | B 51 R 35 T 13 | 19 / 21 / 29 | 1 / 3 / 5 | 3 / 3 / 5 | 38% | 23% | 0 / 0 / 0 | 0.55 / 0.88 / 1.00 | 23% | 100% | 8% | 2 | 0 / 64 / 497 |
| killer tributing | not weak | 6 | 0% | 5 / 5 / 23 | 33% | 6 / 7 / 8 | 27/47/27 | B 55 R 30 F 15 | B 36 T 33 R 24 | 11 / 16 / 18 | 1 / 6 / 7 | 3 / 3 / 4 | 33% | 0% | 0 / 0 / 0 | 0.94 / 1.00 / 1.00 | 33% | 100% | 33% | 2 | 178 / 678 / 758 |

## Q3 the dominant Prism (Focus >= 2x the enemy Prism's, both alive)

1077 dominant Prism-games, 136607 dominant rounds. "win": the dominant Prism's bag plus its team's score reaches 1,000 (keeps_gems lets go, it banks); "mid": before that.

| phase | rounds | share | branch % (D lines) | sees the weak Prism |
|---|---|---|---|---|
| mid | 88499 | 65% | F 62 T 13 P 6 B 6 C 3 U 3 R 3 K 2 | 17% |
| win | 48108 | 35% | T 78 B 15 R 3 W 3 K 0 U 0 . 0 H 0 | 19% |

Rounds the dominant Prism sees the weak one, by distance: who hits whom that round (events), and what the dominant one does when it does not hit:

| phase | distance | rounds seen | dominant hits weak | weak hits dominant | no-hit branch % |
|---|---|---|---|---|---|
| mid | d<=4 | 1034 | 28% | 35% | C 35 F 31 R 18 P 5 T 5 U 2 |
| mid | d5-6 | 4865 | 4% | 5% | F 40 C 14 U 12 R 11 T 11 B 5 |
| mid | d7-8 | 6548 | 0% | 0% | F 43 T 19 U 9 R 8 P 7 B 6 |
| mid | d>8 | 2479 | 0% | 0% | F 58 T 15 P 7 B 6 R 5 C 4 |
| win | d<=4 | 2227 | 9% | 37% | T 65 R 21 B 12 W 2 U 0 C 0 |
| win | d5-6 | 2951 | 4% | 2% | T 77 B 13 W 5 R 4 . 0 G 0 |
| win | d7-8 | 3049 | 0% | 0% | T 61 B 19 W 11 R 7 . 1 U 1 |
| win | d>8 | 790 | 0% | 0% | T 79 B 15 R 4 K 1 H 0 W 0 |

Seen, neither chasing (C) nor hitting: the chase gate (`preyable`, fight.cc:747) as the replay reads it (own_ground by walking steps; hurt = health < 0.453 max):

| phase | rounds | weak healthy on its ground, no bag | ... with a bag (intercept_steps decides) | preyable (our ground, hurt or <=3) | beyond 8 | by its spawn |
|---|---|---|---|---|---|---|
| mid | 13139 | 28% | 43% | 11% | 18% | 1% |
| win | 8676 | 37% | 37% | 16% | 9% | 0% |

Engagement episodes (dominant sees weak and chases or hits it; ends at the first round it does neither): 1236, 257 end in the dominant Prism's kill.

| end | episodes | kills | length q | branch at end % | 2+ other enemies within 6 | dominant hurt | weak on its own ground | weak healthy | weak carries gems |
|---|---|---|---|---|---|---|---|---|---|
| gate | 781 | 84 | 1 / 1 / 2 | F 58 T 19 U 7 B 7 | 24% | 2% | 97% | 66% | 57% |
| weak_died | 172 | 141 | 1 / 1 / 3 |  | 0% | 0% | 0% | 100% | 0% |
| lost_sight | 158 | 18 | 1 / 1 / 2 | C 61 F 25 U 5 R 3 | 28% | 1% | 93% | 61% | 66% |
| retreat | 121 | 14 | 1 / 1 / 1 | R 100 | 29% | 26% | 96% | 55% | 54% |
| strong_died | 2 | 0 | 1 / 1 / 1 |  | 0% | 0% | 0% | 100% | 0% |
| not_dominant | 2 | 0 | 2 / 2 / 2 |  | 0% | 0% | 0% | 100% | 0% |

Belief about the weak Prism (kr-beliefs side, dump every 10 rounds, 6820 samples in dominant rounds): visible 17%, tracked with <=9 possible tiles 3%, <=49 4%, more 1%, untracked 75% (`track_horizon` = 3 rounds after the last sight). Seen in the last 10 rounds: 27% of dominant rounds.

Sustained dominance (ratio held 10 rounds in a row; 719 games), after its onset:

| weak Prism | games | dominant team wins |
|---|---|---|
| weak killed by the dominant Prism | 258 | 96% |
| weak died otherwise | 55 | 89% |
| weak never died | 406 | 57% |

## Q4 dominant-team losses

Onset as the brief defines it (first round Focus >= 2x, both alive): 894 games, the dominant team wins 554 (62%). Onset at the weak Prism's own tribute (its bag left, Focus fell): 339.

| class (first that applies) | losses | with a sustained onset | onset round | rounds onset -> end | our score at end | dominant bag at end | score + its bag >= 1000 | score + team bags >= 1000 | dominant branches after onset % |
|---|---|---|---|---|---|---|---|---|---|
| 1 the weak Prism's winning tribute made the onset | 108 | 0 | 505 / 605 / 814 | 0 / 0 / 0 | 182 / 280 / 413 | 471 / 594 / 700 | 24 | 34 | . 33 T 27 F 21 B 6 P 4 |
| 2 dominant Prism killed later | 56 | 42 | 86 / 171 / 419 | 380 / 594 / 761 | 210 / 359 / 614 | 0 / 26 / 122 | 2 | 1 | F 67 R 7 P 6 T 5 B 3 |
| 3 winning tribute stunned or locked | 10 | 10 | 684 / 912 / 1192 | 332 / 342 / 349 | 351 / 377 / 441 | 770 / 792 / 856 | 10 | 10 | T 52 F 21 B 17 R 3 W 2 |
| 4 out-tributed while holding its bag | 114 | 96 | 303 / 600 / 721 | 14 / 42 / 176 | 217 / 329 / 411 | 405 / 554 / 642 | 12 | 39 | F 70 P 7 T 6 B 4 R 4 |
| 6 out-raced after banking | 52 | 44 | 363 / 445 / 742 | 34 / 54 / 180 | 904 / 965 / 983 | 0 / 0 / 0 | 0 | 34 | F 33 U 30 T 19 B 7 P 4 |

Class 2 killers (first death after onset): Prism 30, Vesper Vale 14, Cassi 6, camp 2, Issac 2, Ryth 2; bag lost 168 / 258 / 607; rounds after onset 81 / 211 / 374.

## The end of the race (every game)

Losers with a Prism, game ended by the win (906), at the winner's last tribute:

| loser | games |
|---|---|
| score + carried bags >= 1000 | 191 |
| score + Prism bag >= 1000 | 59 |
| Prism in a tribute channel | 117 |
| Prism channelling a winning bag | 39 |
| Prism's winning bag stunned or locked at least once | 33 |

Prism tributes: 1164 completed (0.63 a Prism-game), bag 347 / 519 / 677; 7453 channels started, length 41 / 55 / 84 turns; cancels: stun 2639, manual 2363, lock 1078, death 8.
Winners whose Prism held a winning bag (623): rounds from that to the end 17 / 70 / 168; its channel stunned or locked at least once in 337. Winning tributes by: Prism 494, Vesper Vale 159, Issac 107, Vendetta 69.

## Prism duels: who stepped into cast reach (4) and who hit first (every Prism death by the enemy Prism)

| victim | context | deaths | victim stepped in | killer stepped in | both | victim hit first | killer hit first |
|---|---|---|---|---|---|---|---|
| weak victim | stop_ender in window | 617 | 92% | 1% | 2% | 85% | 15% |
| weak victim | no stop_ender | 277 | 20% | 39% | 21% | 37% | 63% |
| not weak | stop_ender in window | 39 | 49% | 0% | 0% | 15% | 85% |
| not weak | no stop_ender | 176 | 22% | 46% | 21% | 28% | 72% |
