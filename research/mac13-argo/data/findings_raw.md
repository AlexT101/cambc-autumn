# Scoreboard findings (2560 distinct games)

## Outcome
end types: {'1000': 2462, 'r2000': 98}; identity failures (wealth != cap+kill-lost): 0 games; mirror drafts: 2560/2560
end round median 773.5 (IQR 598-1046); W tributed median 1024.0, L tributed median 334.0 (IQR 195-574)

### Collected (tributed + carried) / tributed / capture / kill gems at round X (games still running at X; final value otherwise)
| round | live | collected W/L | tributed W/L | capture W/L | kill gems W/L | lost to camps W/L | W-L collected (live) | W ahead (live) |
|---|---|---|---|---|---|---|---|---|
| 100 | 2560 | 97 / 90 | 12 / 11 | 96 / 91 | 1 / 1 | 0 / 0 | +6 | 44% |
| 200 | 2560 | 225 / 199 | 50 / 47 | 221 / 204 | 8 / 3 | 0 / 1 | +27 | 58% |
| 300 | 2551 | 381 / 309 | 113 / 97 | 367 / 325 | 20 / 6 | 1 / 1 | +71 | 66% |
| 400 | 2496 | 555 / 415 | 204 / 157 | 522 / 450 | 42 / 9 | 1 / 2 | +134 | 71% |
| 500 | 2274 | 724 / 501 | 342 / 219 | 666 / 564 | 75 / 15 | 2 / 3 | +202 | 75% |
| 600 | 1912 | 865 / 557 | 507 / 280 | 777 / 653 | 112 / 20 | 3 / 4 | +276 | 77% |
| 800 | 1187 | 1057 / 604 | 781 / 351 | 913 / 758 | 179 / 31 | 4 / 6 | +442 | 81% |
| 1000 | 718 | 1157 / 621 | 938 / 385 | 982 / 807 | 214 / 35 | 4 / 7 | +591 | 83% |

## A. The break
b0 = last round W's collected lead was <= 0 (lead > 0 for good after it). median 403.0, IQR 188-641, p10 83, p90 893. As a share of game length: median 0.52.
strict (last round lead < 0): median 387.5; W never behind (strict) in 8.0%.
b100 = last round lead <= 100: median 541.5, IQR 346-748.
"bank" wins (W ended with collected <= L: won by tributing, not by wealth): 204 (8.0%).
L's largest lead: median 51.0 gems, at median r209.0; L led by 50+ at some point in 52%, 100+ in 28%.
b0 histogram (per 100 rounds): 0-99: 319, 100-199: 360, 200-299: 302, 300-399: 291, 400-499: 287, 500-599: 266, 600-699: 219, 700-799: 166, 800-899: 107, 900-999: 66, 1000-+: 177

| sizec | n | b0 median | b0 IQR | b100 median | end median | b0/end |
|---|---|---|---|---|---|---|
| L(3000+) | 1058 | 464 | 258-684 | 591 | 753 | 0.65 |
| M(1600-3000) | 797 | 383 | 180-612 | 519 | 751 | 0.52 |
| S(<1600) | 705 | 293 | 133-574 | 442 | 826 | 0.34 |

| npick | n | b0 median | b0 IQR | b100 median | end median | b0/end |
|---|---|---|---|---|---|---|
| 5 | 1675 | 423 | 216-645 | 547 | 751 | 0.58 |
| 4 | 471 | 371 | 156-643 | 511 | 789 | 0.46 |
| 3 | 414 | 342 | 157-606 | 518 | 858 | 0.38 |

| kind | n | b0 median | b0 IQR | b100 median | end median | b0/end |
|---|---|---|---|---|---|---|
| generated | 1920 | 422 | 202-654 | 560 | 780 | 0.55 |
| mutation | 640 | 326 | 152-589 | 484 | 746 | 0.43 |

## B. What builds the margin (W minus L, gems; mean [95% bootstrap CI], median)
farm = capture gems; fight = (kill gems taken - own bags lost to champions), W minus L (= 2x the kill-gem gap); camp = L's bags lost to camps minus W's. They sum to the change in the collected-gem lead. bank = W minus L carried (untributed) at the window end.
| component | pre (1..b0) | surge (b0..b100) | first 100 after b0 | post (b100..end) | r1-300 | r1-600 | whole game |
|---|---|---|---|---|---|---|---|
| wealth | -48.5 [-54.3, -43.2]; med -12 | 85.9 [83.3, 88.5]; med +86 | 319.1 [301.4, 338.2]; med +134 | 621.8 [597.3, 648.6]; med +411 | 71.3 [64.1, 77.8]; med +27 | 307.5 [291.3, 324.4]; med +137 | 635.1 [612.2, 661.8]; med +456 |
| farm | -20.1 [-24.0, -16.4]; med -10 | 60.4 [58.1, 62.7]; med +63 | 76.1 [72.4, 79.5]; med +62 | 177.2 [164.9, 188.4]; med +67 | 42.3 [37.4, 46.7]; med +17 | 124.2 [115.3, 132.6]; med +67 | 200.5 [187.2, 213.2]; med +119 |
| fight | -27.1 [-33.9, -20.5]; med +0 | 24.7 [21.5, 27.9]; med +0 | 240.4 [221.7, 260.3]; med +0 | 441.6 [413.4, 473.8]; med +100 | 28.4 [24.3, 33.2]; med +0 | 182.7 [168.8, 197.4]; med +16 | 432.3 [404.6, 464.0]; med +142 |
| camp | -1.2 | +0.9 | +2.7 | +3.0 | +0.7 | +0.6 | +2.4 |
| bank | -64.7 | -53.7 | +149.8 | -54.2 | +55.4 | +80.5 | -54.2 |
| cap_own | -12.2 | +28.9 | +35.7 | +56.3 | +18.1 | +45.3 | +64.9 |
| cap_mid | -5.0 | +18.3 | +23.2 | +73.0 | +14.4 | +46.7 | +81.1 |
| cap_enemy | -2.9 | +13.2 | +17.2 | +47.9 | +9.8 | +32.2 | +54.4 |
| cap_wolf | -0.0 | +0.2 | +0.2 | +1.0 | +0.1 | +0.2 | +1.1 |
| cap_wolf_cl | -4.5 | +13.6 | +13.7 | +33.7 | +9.9 | +27.0 | +38.9 |
| cap_elk | -3.2 | +20.7 | +22.6 | +53.0 | +15.3 | +43.4 | +64.6 |
| cap_golem | -0.9 | +7.1 | +8.5 | +19.6 | +4.3 | +17.5 | +23.8 |
| cap_gem_cl | -6.6 | +14.4 | +17.8 | +35.9 | +11.2 | +26.3 | +39.6 |
| cap_gold_cl | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 |
| cap_mixed_cl | -0.3 | +1.4 | +1.6 | +1.7 | +1.4 | +2.3 | +2.4 |
| cap_monolith | -4.5 | +3.1 | +11.7 | +32.4 | +0.1 | +7.4 | +30.1 |
| n | 2560 | 1840 | 2560 | 2560 | 2560 | 2560 | 2560 |

surge (b0..b100): largest W component per game: farm 77%, fight 22%, camp 1%
first 100 after b0: largest W component per game: farm 62%, fight 37%, camp 1%
whole game: largest W component per game: fight 49%, farm 49%, camp 2%
first 100 rounds after b0: lead gain mean +319.1; farm +76.1, fight +240.4, camp +2.7; games where |fight| > |farm|: 38%

L death within 10 rounds of b0: 38% of games; with a bag >= 50: 23%, >= 100: 17%
L Prism died within 10 rounds of b0: 20% (Prism drafted in 87% of games)

## C. Subsets that isolate farming from the Prism duel
| subset | n | b0 med | pre: farm/fight/camp | b0+100: farm/fight/camp | whole: farm/fight/camp/bank |
|---|---|---|---|---|---|
| all | 2560 | 403 | -20 / -27 / -1 | +76 / +240 / +3 | +200 / +432 / +2 / -54 |
| Prism drafted, no Prism death before b0 | 2011 | 359 | -25 / -8 / -0 | +76 / +253 / +2 | +180 / +506 / +4 / -65 |
| Prism drafted, a Prism died before b0 | 216 | 692 | +22 / -238 / -13 | +67 / +434 / +12 | +242 / +324 / -7 / +12 |
| no Prism drafted | 333 | 531 | -19 / -4 / -0 | +81 / +36 / +1 | +299 / +60 / +1 / -29 |
| no kill before r300 | 1136 | 508 | -22 / -25 / -1 | +65 / +251 / +2 | +87 / +415 / +1 / -106 |

## D. W vs L behaviour, standardised (paired: mean W-L / sd of W-L; P(W>L) excludes ties)
### Rounds 1-150 (before most breaks) (2560 games)
| feature | W | L | W-L | dz | P(W>L) | n |
|---|---|---|---|---|---|---|
| gold_earned | 707 | 666 | +41.2 | +0.20 | 57% | 2560 |
| cap_per_100alive | 19.6 | 18.4 | +1.18 | +0.16 | 57% | 2560 |
| gold_spent | 602 | 568 | +33.3 | +0.16 | 57% | 2560 |
| kills | 0.305 | 0.194 | +0.111 | +0.16 | 62% | 2560 |
| deaths | 0.234 | 0.354 | -0.119 | -0.15 | 39% | 2560 |
| lab_dead | 0.0184 | 0.0266 | -0.00812 | -0.12 | 41% | 2560 |
| raids | 0.699 | 0.6 | +0.0996 | +0.11 | 59% | 2560 |
| own_lost | 0.6 | 0.699 | -0.0996 | -0.11 | 41% | 2560 |
| campdmg_per_alive | 20 | 19.7 | +0.322 | +0.11 | 53% | 2560 |
| steals | 0.215 | 0.152 | +0.0637 | +0.10 | 60% | 2560 |
| lab_work | 0.326 | 0.321 | +0.00432 | +0.09 | 54% | 2560 |
| lab_hold | 0.045 | 0.0438 | +0.0012 | +0.09 | 54% | 2560 |
| lab_recall | 0.0447 | 0.0437 | +0.000986 | +0.08 | 53% | 2560 |
| lab_camp | 0.278 | 0.275 | +0.00305 | +0.07 | 54% | 2560 |
| lab_fight | 0.026 | 0.0257 | +0.000364 | +0.07 | 54% | 2560 |
| gold_bank | 105 | 97.6 | +7.85 | +0.07 | 52% | 2560 |
| lab_walk_bag | 0.19 | 0.187 | +0.00265 | +0.04 | 52% | 2560 |
| lab_walk_all | 0.541 | 0.539 | +0.00185 | +0.04 | 51% | 2560 |
| lab_lost | 0.00118 | 0.00112 | +6e-05 | +0.03 | 53% | 2560 |
| idle_own | 0.76 | 0.761 | -0.00168 | -0.03 | 49% | 2546 |
| idle_enemy | 0.761 | 0.76 | +0.00168 | +0.03 | 51% | 2546 |
| camp_deaths | 0.0406 | 0.0484 | -0.00781 | -0.03 | 46% | 2560 |
| lab_wait_camp | 0.0169 | 0.0166 | +0.000362 | +0.03 | 51% | 2560 |
| lab_spawn | 0.0122 | 0.0122 | +6.38e-05 | +0.02 | 50% | 2560 |
| clus | 0.765 | 0.766 | -0.00114 | -0.02 | 48% | 2560 |
| idlev_own_per100 | 150 | 150 | -0.685 | -0.02 | 46% | 2560 |
| idlev_enemy_per100 | 150 | 150 | +0.685 | +0.02 | 54% | 2560 |
| lab_tribute | 0.0029 | 0.00283 | +6.72e-05 | +0.01 | 52% | 2560 |
| lab_walk | 0.351 | 0.352 | -0.000795 | -0.01 | 50% | 2560 |
| lab_idle | 0.014 | 0.0139 | +0.000108 | +0.01 | 52% | 2560 |
| nn | 4.49 | 4.5 | -0.00813 | -0.01 | 50% | 2560 |
| lab_wait_altar | 0.000296 | 0.000295 | +1.48e-06 | +0.00 | 53% | 2560 |
| idlev_mid_per100 | 69 | 69 | +0 | +0.00 | -% | 2560 |
| idle_mid | 0.828 | 0.828 | +0 | +0.00 | -% | 1383 |

### Pre-break window 1..b0, games with b0 >= 100 (2037 games)
| feature | W | L | W-L | dz | P(W>L) | n |
|---|---|---|---|---|---|---|
| cap_per_100alive | 21.7 | 22.9 | -1.18 | -0.29 | 24% | 2037 |
| campdmg_per_alive | 23.1 | 22.7 | +0.424 | +0.13 | 57% | 2037 |
| gold_bank | 277 | 324 | -46.2 | -0.12 | 45% | 2037 |
| lab_walk_bag | 0.259 | 0.267 | -0.0074 | -0.12 | 44% | 2037 |
| lab_tribute | 0.00743 | 0.0082 | -0.000773 | -0.10 | 45% | 2037 |
| lab_walk | 0.301 | 0.296 | +0.00545 | +0.09 | 54% | 2037 |
| lab_fight | 0.0257 | 0.0254 | +0.000279 | +0.07 | 53% | 2037 |
| gold_spent | 2.66e+03 | 2.63e+03 | +38.1 | +0.07 | 52% | 2037 |
| lab_walk_all | 0.561 | 0.563 | -0.00195 | -0.05 | 46% | 2037 |
| idle_own | 0.743 | 0.745 | -0.00215 | -0.04 | 48% | 2027 |
| idle_enemy | 0.745 | 0.743 | +0.00215 | +0.04 | 52% | 2027 |
| lab_dead | 0.0362 | 0.0343 | +0.00185 | +0.04 | 53% | 2037 |
| lab_lost | 0.00118 | 0.00114 | +4.66e-05 | +0.04 | 53% | 2037 |
| lab_wait_camp | 0.0221 | 0.0225 | -0.000404 | -0.03 | 48% | 2037 |
| clus | 0.726 | 0.725 | +0.00131 | +0.03 | 51% | 2037 |
| lab_camp | 0.23 | 0.23 | +0.000814 | +0.03 | 51% | 2037 |
| deaths | 1.45 | 1.41 | +0.0368 | +0.02 | 52% | 2037 |
| nn | 5.19 | 5.21 | -0.0183 | -0.02 | 49% | 2037 |
| kills | 1.26 | 1.29 | -0.0309 | -0.02 | 49% | 2037 |
| steals | 0.602 | 0.622 | -0.0201 | -0.02 | 48% | 2037 |
| gold_earned | 2.94e+03 | 2.95e+03 | -8.1 | -0.01 | 47% | 2037 |
| lab_wait_altar | 0.00145 | 0.00131 | +0.000143 | +0.01 | 52% | 2037 |
| lab_idle | 0.0126 | 0.0125 | +0.000101 | +0.01 | 52% | 2037 |
| camp_deaths | 0.156 | 0.15 | +0.00589 | +0.01 | 52% | 2037 |
| lab_recall | 0.0456 | 0.0457 | -9.01e-05 | -0.01 | 49% | 2037 |
| lab_spawn | 0.0119 | 0.012 | -3.24e-05 | -0.01 | 48% | 2037 |
| idlev_own_per100 | 126 | 127 | -0.25 | -0.01 | 48% | 2037 |
| idlev_enemy_per100 | 127 | 126 | +0.25 | +0.01 | 52% | 2037 |
| lab_hold | 0.0443 | 0.0443 | +1.68e-05 | +0.00 | 53% | 2037 |
| lab_work | 0.282 | 0.282 | +5.81e-05 | +0.00 | 51% | 2037 |
| raids | 2.91 | 2.91 | +0.00245 | +0.00 | 48% | 2037 |
| own_lost | 2.91 | 2.91 | -0.00245 | -0.00 | 52% | 2037 |
| idlev_mid_per100 | 58.8 | 58.8 | +0 | +0.00 | -% | 2037 |
| idle_mid | 0.794 | 0.794 | +0 | +0.00 | -% | 1059 |

### First 100 rounds after b0 (2276 games)
| feature | W | L | W-L | dz | P(W>L) | n |
|---|---|---|---|---|---|---|
| deaths | 0.185 | 1.28 | -1.1 | -0.83 | 6% | 2276 |
| lab_dead | 0.038 | 0.179 | -0.141 | -0.80 | 12% | 2276 |
| kills | 1.23 | 0.172 | +1.06 | +0.80 | 94% | 2276 |
| lab_work | 0.267 | 0.193 | +0.074 | +0.71 | 77% | 2276 |
| cap_per_100alive | 33.8 | 18.8 | +15 | +0.60 | 82% | 2276 |
| lab_tribute | 0.0493 | 0.0136 | +0.0357 | +0.55 | 80% | 2276 |
| raids | 0.989 | 0.384 | +0.605 | +0.51 | 86% | 2276 |
| own_lost | 0.384 | 0.989 | -0.605 | -0.51 | 14% | 2276 |
| lab_hold | 0.0407 | 0.0296 | +0.0111 | +0.47 | 72% | 2276 |
| lab_recall | 0.0423 | 0.0346 | +0.00778 | +0.35 | 66% | 2276 |
| steals | 0.339 | 0.1 | +0.239 | +0.34 | 80% | 2276 |
| lab_camp | 0.177 | 0.149 | +0.0273 | +0.33 | 64% | 2276 |
| lab_wait_altar | 0.0208 | 0.00199 | +0.0188 | +0.27 | 77% | 2276 |
| lab_walk_bag | 0.285 | 0.25 | +0.0351 | +0.27 | 64% | 2276 |
| lab_fight | 0.0309 | 0.0289 | +0.00199 | +0.26 | 71% | 2276 |
| lab_walk_all | 0.546 | 0.518 | +0.0279 | +0.23 | 59% | 2276 |
| lab_wait_camp | 0.0301 | 0.0192 | +0.0109 | +0.22 | 64% | 2276 |
| clus | 0.705 | 0.729 | -0.0247 | -0.21 | 42% | 2276 |
| camp_deaths | 0.0136 | 0.0492 | -0.0356 | -0.14 | 18% | 2276 |
| idlev_own_per100 | 121 | 127 | -6.84 | -0.13 | 40% | 2276 |
| idlev_enemy_per100 | 127 | 121 | +6.84 | +0.13 | 60% | 2276 |
| lab_lost | 0.00147 | 0.00116 | +0.000313 | +0.12 | 60% | 2276 |
| nn | 5.58 | 5.84 | -0.258 | -0.11 | 47% | 2276 |
| idle_own | 0.771 | 0.781 | -0.0104 | -0.08 | 47% | 2264 |
| idle_enemy | 0.781 | 0.771 | +0.0104 | +0.08 | 53% | 2264 |
| lab_walk | 0.26 | 0.268 | -0.00725 | -0.06 | 48% | 2276 |
| campdmg_per_alive | 21.8 | 21.6 | +0.223 | +0.02 | 56% | 2276 |
| lab_idle | 0.0124 | 0.0131 | -0.000702 | -0.02 | 52% | 2276 |
| lab_spawn | 0.0118 | 0.0118 | +7.83e-05 | +0.01 | 51% | 2276 |
| idlev_mid_per100 | 53 | 53 | +0 | +0.00 | -% | 2276 |
| idle_mid | 0.722 | 0.722 | +0 | +0.00 | -% | 1234 |

## C (detail). Subsets
no Prism death before b0: n=2011; W ahead at r300 in 68% (lead mean +85, median +35); b0 median 359; L's Prism died (ever) in 55% / W's Prism ever died 2%
  r1-300 W-L: wealth +84.8, farm +49.5, fight +34.8, camp +0.5, cap_own +20.6, cap_mid +16.6, cap_enemy +12.2, cap_wolf +0.0, cap_wolf_cl +11.6, cap_elk +17.5, cap_golem +5.0, cap_gem_cl +14.0, cap_gold_cl +0.0, cap_mixed_cl +1.3, cap_monolith +0.1
no kill before r300: n=1134; W ahead at r300 in 58% (lead mean +20, median +8); b0 median 509; L's Prism died (ever) in 34% / W's Prism ever died 4%
  r1-300 W-L: wealth +20.2, farm +20.0, fight +0.0, camp +0.2, cap_own +8.9, cap_mid +5.4, cap_enemy +5.7, cap_wolf +0.0, cap_wolf_cl +3.7, cap_elk +8.9, cap_golem +1.9, cap_gem_cl +3.5, cap_gold_cl +0.0, cap_mixed_cl +1.6, cap_monolith +0.4
### No kill before r300: rounds 1-300 (1134 games)
| feature | W | L | W-L | dz | P(W>L) | n |
|---|---|---|---|---|---|---|
| cap_per_100alive | 23.8 | 22.5 | +1.26 | +0.27 | 61% | 1134 |
| gold_earned | 1.86e+03 | 1.79e+03 | +62.6 | +0.20 | 59% | 1134 |
| campdmg_per_alive | 25.1 | 24.6 | +0.568 | +0.20 | 57% | 1134 |
| gold_spent | 1.66e+03 | 1.62e+03 | +45.1 | +0.14 | 55% | 1134 |
| raids | 1.36 | 1.22 | +0.141 | +0.11 | 57% | 1134 |
| own_lost | 1.22 | 1.36 | -0.141 | -0.11 | 43% | 1134 |
| gold_bank | 196 | 178 | +17.5 | +0.08 | 53% | 1134 |
| steals | 0.251 | 0.198 | +0.0538 | +0.08 | 57% | 1134 |
| lab_work | 0.335 | 0.333 | +0.00212 | +0.06 | 54% | 1134 |
| lab_hold | 0.0471 | 0.0463 | +0.000784 | +0.06 | 52% | 1134 |
| lab_wait_altar | 0.0004 | 0.000321 | +7.98e-05 | +0.06 | 57% | 1134 |
| lab_spawn | 0.0147 | 0.015 | -0.000268 | -0.05 | 49% | 1134 |
| lab_tribute | 0.00513 | 0.00494 | +0.000196 | +0.05 | 53% | 1134 |
| lab_camp | 0.283 | 0.282 | +0.00114 | +0.04 | 53% | 1134 |
| idlev_own_per100 | 148 | 149 | -1.64 | -0.04 | 46% | 1134 |
| idlev_enemy_per100 | 149 | 148 | +1.64 | +0.04 | 54% | 1134 |
| lab_walk_all | 0.546 | 0.547 | -0.00126 | -0.04 | 49% | 1134 |
| lab_lost | 0.000521 | 0.000492 | +2.95e-05 | +0.03 | 50% | 1134 |
| idle_own | 0.737 | 0.739 | -0.00144 | -0.03 | 49% | 1131 |
| idle_enemy | 0.739 | 0.737 | +0.00144 | +0.03 | 51% | 1131 |
| lab_walk_bag | 0.274 | 0.276 | -0.00184 | -0.03 | 48% | 1134 |
| lab_recall | 0.0559 | 0.0561 | -0.000215 | -0.02 | 48% | 1134 |
| lab_idle | 0.0118 | 0.0122 | -0.000395 | -0.02 | 50% | 1134 |
| deaths | 0.097 | 0.104 | -0.00705 | -0.02 | 46% | 1134 |
| camp_deaths | 0.097 | 0.104 | -0.00705 | -0.02 | 46% | 1134 |
| lab_wait_camp | 0.0213 | 0.0211 | +0.000198 | +0.02 | 51% | 1134 |
| lab_dead | 0.00494 | 0.00521 | -0.00027 | -0.01 | 48% | 1134 |
| clus | 0.701 | 0.702 | -0.000591 | -0.01 | 50% | 1134 |
| nn | 5.41 | 5.4 | +0.0104 | +0.01 | 51% | 1134 |
| lab_fight | 0.00937 | 0.00938 | -1.81e-05 | -0.01 | 51% | 1134 |
| lab_walk | 0.272 | 0.271 | +0.000574 | +0.01 | 51% | 1134 |
| idlev_mid_per100 | 57.4 | 57.4 | +0 | +0.00 | -% | 1134 |
| kills | 0 | 0 | +0 | +0.00 | -% | 1134 |
| idle_mid | 0.828 | 0.828 | +0 | +0.00 | -% | 524 |

### No Prism death before b0: pre-break window, b0 >= 100 (1574 games)
| feature | W | L | W-L | dz | P(W>L) | n |
|---|---|---|---|---|---|---|
| cap_per_100alive | 23.7 | 25.1 | -1.42 | -0.36 | 21% | 1574 |
| gold_bank | 279 | 337 | -58 | -0.16 | 44% | 1574 |
| lab_walk_bag | 0.269 | 0.277 | -0.008 | -0.13 | 44% | 1574 |
| campdmg_per_alive | 23.9 | 23.5 | +0.337 | +0.12 | 56% | 1574 |
| gold_earned | 2.6e+03 | 2.65e+03 | -49.6 | -0.11 | 45% | 1574 |
| lab_walk | 0.292 | 0.286 | +0.006 | +0.09 | 54% | 1574 |
| deaths | 1.06 | 0.961 | +0.0953 | +0.08 | 53% | 1574 |
| lab_tribute | 0.00719 | 0.00764 | -0.00045 | -0.07 | 47% | 1574 |
| kills | 0.886 | 0.97 | -0.0832 | -0.07 | 47% | 1574 |
| lab_dead | 0.0311 | 0.0278 | +0.00326 | +0.07 | 55% | 1574 |
| lab_fight | 0.0223 | 0.0221 | +0.000238 | +0.07 | 52% | 1574 |
| lab_wait_camp | 0.0215 | 0.0222 | -0.000658 | -0.06 | 47% | 1574 |
| lab_recall | 0.0448 | 0.0452 | -0.000474 | -0.05 | 47% | 1574 |
| lab_walk_all | 0.562 | 0.564 | -0.00199 | -0.05 | 46% | 1574 |
| clus | 0.731 | 0.729 | +0.00216 | +0.04 | 51% | 1574 |
| lab_wait_altar | 0.000955 | 0.000825 | +0.000129 | +0.04 | 53% | 1574 |
| camp_deaths | 0.087 | 0.075 | +0.0121 | +0.03 | 55% | 1574 |
| steals | 0.517 | 0.547 | -0.0299 | -0.03 | 48% | 1574 |
| idle_own | 0.744 | 0.746 | -0.00118 | -0.02 | 48% | 1566 |
| idle_enemy | 0.746 | 0.744 | +0.00118 | +0.02 | 52% | 1566 |
| raids | 2.4 | 2.44 | -0.0394 | -0.02 | 47% | 1574 |
| own_lost | 2.44 | 2.4 | +0.0394 | +0.02 | 53% | 1574 |
| lab_spawn | 0.0116 | 0.0118 | -0.000105 | -0.02 | 47% | 1574 |
| gold_spent | 2.32e+03 | 2.31e+03 | +8.4 | +0.02 | 51% | 1574 |
| lab_lost | 0.00106 | 0.00105 | +1.96e-05 | +0.02 | 53% | 1574 |
| lab_work | 0.293 | 0.293 | -0.000529 | -0.01 | 51% | 1574 |
| lab_idle | 0.0126 | 0.0125 | +0.000113 | +0.01 | 52% | 1574 |
| lab_hold | 0.0465 | 0.0466 | -8.97e-05 | -0.01 | 52% | 1574 |
| nn | 5.1 | 5.1 | -0.00346 | -0.00 | 49% | 1574 |
| idlev_own_per100 | 132 | 133 | -0.181 | -0.00 | 48% | 1574 |
| idlev_enemy_per100 | 133 | 132 | +0.181 | +0.00 | 52% | 1574 |
| lab_camp | 0.239 | 0.239 | +1.09e-05 | +0.00 | 50% | 1574 |
| idlev_mid_per100 | 61.2 | 61.2 | +0 | +0.00 | -% | 1574 |
| idle_mid | 0.804 | 0.804 | +0 | +0.00 | -% | 813 |

## Labour by phase (share of champion-rounds, W / L)
| phase | walk | walk_bag | camp | hold | tribute | recall | fight | wait_camp | wait_altar | spawn | idle | lost | dead | camp dmg / alive rd |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| p1 (n=2560) | 35.1 / 35.2 | 19.0 / 18.7 | 27.8 / 27.5 | 4.5 / 4.4 | 0.3 / 0.3 | 4.5 / 4.4 | 2.6 / 2.6 | 1.7 / 1.7 | 0.0 / 0.0 | 1.2 / 1.2 | 1.4 / 1.4 | 0.1 / 0.1 | 1.8 / 2.7 | 20.0 / 19.7 |
| p2 (n=2560) | 25.0 / 25.5 | 31.4 / 30.2 | 21.1 / 19.9 | 4.6 / 4.2 | 1.4 / 0.9 | 5.2 / 4.9 | 2.6 / 2.6 | 2.6 / 2.4 | 0.1 / 0.1 | 1.3 / 1.3 | 1.0 / 1.0 | 0.1 / 0.1 | 3.8 / 7.1 | 25.3 / 23.5 |
| p3 (n=2418) | 26.3 / 26.6 | 29.5 / 29.1 | 15.5 / 13.7 | 4.0 / 3.4 | 5.3 / 1.6 | 3.7 / 3.4 | 2.8 / 2.7 | 3.6 / 2.4 | 1.7 / 0.5 | 1.2 / 1.3 | 1.2 / 1.2 | 0.1 / 0.1 | 5.1 / 14.1 | 25.3 / 24.3 |

## Supply left up and unworked (share of up group-rounds with no camp hit and no capture hold, by zone relative to the team)
| window | own idle W/L | mid idle W/L | enemy idle W/L | raids (enemy-half captures) W/L | raid gems W/L | steals (captured a group the other team cleared) W/L |
|---|---|---|---|---|---|---|
| p1 (n=2560) | 82 / 82 | 89 / 89 | 82 / 82 | 0.7 / 0.6 | 10 / 8 | 0.2 / 0.2 |
| p2 (n=2560) | 81 / 81 | 85 / 85 | 81 / 81 | 2.0 / 1.4 | 37 / 22 | 0.5 / 0.3 |
| p3 (n=2418) | 86 / 86 | 86 / 86 | 86 / 86 | 2.8 / 1.7 | 56 / 31 | 0.6 / 0.4 |
| pre (n=2464) | 82 / 82 | 88 / 88 | 82 / 82 | 2.7 / 2.7 | 40 / 43 | 0.6 / 0.6 |
| game (n=2560) | 85 / 85 | 87 / 87 | 85 / 85 | 6.8 / 4.4 | 126 / 72 | 1.6 / 1.0 |

### Group classes: supply and use (whole game, both teams)
| class | games with it | groups | up share | up: untouched (monsters alive) | up: cleared, unheld | captures per 1000 group-rounds | capture gems/game W / L | share of all capture gems |
|---|---|---|---|---|---|---|---|---|
| wolf | 511 | 1478 | 82% | 89% | 1% | 4.7 | 6 / 5 | 1% |
| wolf_cl | 2216 | 19849 | 68% | 81% | 2% | 6.5 | 285 / 247 | 28% |
| elk | 1968 | 9514 | 59% | 76% | 2% | 7.0 | 359 / 294 | 34% |
| golem | 855 | 1909 | 68% | 85% | 1% | 4.3 | 88 / 64 | 8% |
| gem_cl | 1490 | 9045 | 48% | 71% | 11% | 10.6 | 245 / 205 | 23% |
| gold_cl | 1364 | 8488 | 66% | 82% | 10% | 6.8 | 0 / 0 | 0% |
| mixed_cl | 178 | 437 | 43% | 61% | 7% | 11.7 | 21 / 18 | 2% |
| monolith | 717 | 1427 | 91% | 96% | 0% | 0.7 | 55 / 25 | 4% |

## Cohesion by phase (W / L)
| window | n | nearest ally (field bodies) W / L | W-L | largest cluster share % W / L | W-L (pt) |
|---|---|---|---|---|---|
| p1 | 2560 | 4.49 / 4.50 | -0.01 [-0.05, 0.03] | 76.5 / 76.6 | -0.11 [-0.35, 0.10] |
| p2 | 2560 | 5.62 / 5.59 | 0.03 [-0.01, 0.08] | 69.9 / 70.7 | -0.84 [-1.09, -0.58] |
| p3 | 2418 | 5.65 / 5.81 | -0.16 [-0.22, -0.10] | 70.4 / 71.7 | -1.26 [-1.55, -0.94] |
| pre | 2464 | 5.08 / 5.11 | -0.02 [-0.06, 0.00] | 73.4 / 73.2 | 0.16 [-0.04, 0.37] |

## Gold (team totals, W / L, games running at X)
| round | n | earned | spent | unspent | capture gold |
|---|---|---|---|---|---|
| r150 | 2560 | 707 / 666 | 602 / 568 | 105 / 98 | 670 / 639 |
| r300 | 2551 | 1707 / 1535 | 1521 / 1386 | 186 / 149 | 1594 / 1466 |
| r600 | 1912 | 3996 / 3375 | 3538 / 3109 | 457 / 266 | 3610 / 3194 |
| end | 2560 | 5952 / 4566 | 5059 / 4269 | 893 / 297 | 4927 / 4226 |

### Shard-equivalents (emblem = 5, Greed = 25) and emblems per champion type, W / L
| round | champion | n | shard-eq W / L | emblems W / L |
|---|---|---|---|---|
| r300 | Cassi | 2491 | 1.9 / 1.8 | 0.21 / 0.20 |
| r300 | Issac | 2491 | 2.1 / 2.2 | 0.22 / 0.22 |
| r300 | Prism | 2218 | 20.6 / 17.9 | 3.82 / 3.26 |
| r300 | Vesper Vale | 1607 | 25.0 / 22.8 | 4.66 / 4.21 |
| r300 | Willow | 1590 | 0.3 / 0.4 | 0.02 / 0.02 |
| r300 | Heart of Ruin | 769 | 4.5 / 4.3 | 0.66 / 0.62 |
| r300 | Ryth | 723 | 9.2 / 8.7 | 1.54 / 1.46 |
| r300 | Vendetta | 627 | 13.3 / 12.4 | 2.34 / 2.14 |
| r300 | Varg | 392 | 7.7 / 7.7 | 1.23 / 1.24 |
| r300 | Marcella | 375 | 7.8 / 7.2 | 1.28 / 1.18 |
| r300 | Ren | 326 | 6.8 / 6.6 | 1.08 / 1.03 |
| r300 | Tavi | 258 | 9.3 / 8.3 | 1.49 / 1.28 |
| r300 | Stellar | 82 | 6.0 / 6.1 | 0.90 / 0.93 |
| r600 | Cassi | 1856 | 5.1 / 4.5 | 0.76 / 0.64 |
| r600 | Issac | 1856 | 5.8 / 5.3 | 0.86 / 0.77 |
| r600 | Prism | 1586 | 48.5 / 40.0 | 9.32 / 7.65 |
| r600 | Vesper Vale | 1308 | 57.8 / 51.8 | 11.19 / 9.98 |
| r600 | Willow | 1226 | 0.8 / 0.9 | 0.06 / 0.08 |
| r600 | Heart of Ruin | 600 | 10.3 / 9.8 | 1.74 / 1.65 |
| r600 | Ryth | 512 | 19.4 / 17.6 | 3.56 / 3.19 |
| r600 | Vendetta | 447 | 31.6 / 28.2 | 5.95 / 5.28 |
| r600 | Ren | 262 | 15.2 / 14.6 | 2.69 / 2.58 |
| r600 | Marcella | 255 | 17.3 / 15.1 | 3.13 / 2.70 |
| r600 | Varg | 232 | 18.7 / 18.1 | 3.41 / 3.28 |
| r600 | Tavi | 182 | 22.5 / 19.4 | 4.10 / 3.52 |
| r600 | Stellar | 45 | 16.4 / 14.2 | 2.89 / 2.51 |

## Deaths per game by victim type (W / L)
| victim | games | W: deaths/game / median round / mean bag / by camp / outnumbered (champ kills) / by Prism | L: same |
|---|---|---|---|
| Issac | 2500 | 0.47 / r470 / bag 7 / camp 12% / outn 35% / byPrism 40% | 0.91 / r595 / bag 8 / camp 6% / outn 42% / byPrism 53% |
| Cassi | 2500 | 0.63 / r588 / bag 13 / camp 9% / outn 25% / byPrism 49% | 1.58 / r681 / bag 15 / camp 3% / outn 31% / byPrism 64% |
| Prism | 2227 | 0.15 / r553 / bag 136 / camp 13% / outn 48% / byPrism 46% | 1.59 / r728 / bag 133 / camp 3% / outn 57% / byPrism 76% |
| Vesper Vale | 1607 | 0.29 / r569 / bag 21 / camp 7% / outn 37% / byPrism 52% | 0.99 / r704 / bag 25 / camp 3% / outn 55% / byPrism 59% |
| Willow | 1592 | 0.61 / r640 / bag 2 / camp 9% / outn 25% / byPrism 47% | 1.33 / r664 / bag 3 / camp 5% / outn 39% / byPrism 54% |
| Heart of Ruin | 775 | 0.63 / r606 / bag 8 / camp 4% / outn 44% / byPrism 29% | 1.24 / r627 / bag 11 / camp 3% / outn 49% / byPrism 34% |
| Ryth | 725 | 0.58 / r463 / bag 13 / camp 10% / outn 40% / byPrism 43% | 1.89 / r687 / bag 13 / camp 4% / outn 60% / byPrism 61% |
| Vendetta | 632 | 0.33 / r525 / bag 11 / camp 18% / outn 42% / byPrism 21% | 0.63 / r633 / bag 18 / camp 12% / outn 46% / byPrism 30% |
| Varg | 393 | 0.29 / r553 / bag 11 / camp 13% / outn 32% / byPrism 38% | 0.52 / r574 / bag 18 / camp 10% / outn 39% / byPrism 40% |
| Marcella | 379 | 0.55 / r505 / bag 12 / camp 8% / outn 41% / byPrism 53% | 2.05 / r720 / bag 15 / camp 3% / outn 61% / byPrism 73% |
| Ren | 329 | 0.51 / r589 / bag 10 / camp 7% / outn 48% / byPrism 33% | 1.32 / r698 / bag 14 / camp 1% / outn 54% / byPrism 44% |
| Tavi | 260 | 0.85 / r480 / bag 13 / camp 6% / outn 43% / byPrism 33% | 1.98 / r593 / bag 8 / camp 3% / outn 42% / byPrism 46% |
| Stellar | 82 | 0.44 / r579 / bag 19 / camp 3% / outn 40% / byPrism 58% | 1.49 / r668 / bag 22 / camp 0% / outn 53% / byPrism 57% |

Gems lost at own deaths per game, by phase (W / L): r1-150 2 / 4, 151-400 7 / 38, 401-800 23 / 138, 801+ 9 / 77

## Prism (games with Prism drafted)
| round | n | Focus mean W / L | carried gems mean W / L | carried median W / L |
|---|---|---|---|---|
| r200 | 2227 | 323 / 284 | 138 / 113 | 122 / 100 |
| r300 | 2218 | 496 / 403 | 236 / 177 | 210 / 158 |
| r400 | 2163 | 676 / 507 | 339 / 229 | 310 / 211 |
| r600 | 1586 | 950 / 600 | 485 / 255 | 440 / 209 |

n=2227. Prism never died: W 91%, L 42%. First death round median (when it died): W 457, L 467. First Prism death was L's in 90% of games where one died.
W Prism tributes/game 6.5: completed 1.0 (mean size 553, median 547), cancelled 5.4 (mean bag 1118; stun 5731, manual 3675, lock 2535, death 4); gems scored by Prism / team tributed: 0.52
L Prism tributes/game 1.2: completed 0.2 (mean size 444, median 484), cancelled 0.9 (mean bag 834; manual 1322, stun 526, lock 222, death 29); gems scored by Prism / team tributed: 0.18

W all tributes/game 24.4, completed 17.4, cancelled 6.8
L all tributes/game 12.3, completed 10.1, cancelled 2.0

## E. Map classes (preset; mutations pooled)
| preset | n | b0 med | end med | farm | fight | camp | bank | b0+100 farm/fight | dominant | |fight|>|farm| | team A wins | to r2000 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ladder | 1120 | 418 | 767 | +151 | +458 | +1 | -66 | +67 / +253 | fight | 49% | 47% | 3% |
| mut | 640 | 326 | 746 | +256 | +381 | +3 | -59 | +87 / +211 | farm | 45% | 50% | 4% |
| classic | 300 | 415 | 752 | +162 | +512 | +2 | -35 | +74 / +292 | fight | 54% | 48% | 3% |
| tiny | 60 | 248 | 816 | +394 | +465 | +1 | +70 | +82 / +157 | farm | 37% | 32% | 3% |
| monolith | 50 | 505 | 820 | +159 | +595 | +10 | +69 | +75 / +308 | farm | 42% | 56% | 10% |
| huge | 40 | 476 | 642 | +90 | +236 | +1 | -268 | +73 / +141 | fight | 52% | 55% | 0% |
| lakes | 40 | 433 | 826 | +207 | +468 | +10 | +60 | +66 / +330 | farm | 48% | 50% | 8% |
| contested-centre | 40 | 235 | 788 | +324 | +368 | -10 | -49 | +77 / +193 | farm | 45% | 35% | 0% |
| small-brawl | 40 | 426 | 1032 | +306 | +756 | +6 | +280 | +87 / +305 | fight | 60% | 52% | 8% |
| monolith-only | 30 | 886 | 1215 | +555 | +50 | +1 | -60 | +206 / +86 | farm | 13% | 50% | 3% |
| shared-gems | 30 | 402 | 1387 | +724 | +73 | -1 | +38 | +127 / +43 | farm | 3% | 43% | 20% |
| maze | 30 | 440 | 884 | +190 | +425 | +19 | -14 | +47 / +365 | fight | 60% | 60% | 3% |
| rows | 30 | 486 | 784 | +149 | +330 | +3 | -101 | +88 / +190 | farm | 37% | 57% | 0% |
| vaults | 30 | 570 | 822 | +121 | +369 | +1 | -193 | +82 / +275 | farm | 47% | 60% | 0% |
| caves | 20 | 501 | 830 | +229 | +351 | +20 | -102 | +63 / +103 | farm | 35% | 50% | 5% |
| jungle | 20 | 362 | 686 | +106 | +268 | +0 | -275 | +47 / +211 | fight | 45% | 50% | 0% |
| lanes | 20 | 558 | 804 | +141 | +269 | +2 | -117 | +80 / +145 | fight | 50% | 45% | 5% |
| altar-poor | 20 | 438 | 766 | +38 | +500 | +13 | -278 | +38 / +371 | fight | 65% | 45% | 0% |

Mutations: 640 games over 126 bases.

## F. Side asymmetry (team A moves first on odd rounds; identical bots)
team A wins 48.2% [46.2, 50.0] of 2560 distinct games.
- by sizec: L(3000+) 48.5% (n=1058), M(1600-3000) 48.2% (n=797), S(<1600) 47.7% (n=705)
- by npick: 3 48.8% (n=414), 4 48.8% (n=471), 5 47.8% (n=1675)
- by sym: horizontal 44.9% (n=597), rotational 48.8% (n=1483), vertical 50.2% (n=480)
- by kind: generated 47.6% (n=1920), mutation 50.0% (n=640)

## G. Champion types: farming and fighting (per 1000 alive rounds, whole game, both teams pooled)
| champion | games | capture gems | camp dmg / alive rd | kills | deaths | camp deaths | walk | camp | hold | tribute | wait+idle+spawn | dead |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Cassi | 2500 | 106 | 14.8 | 0.30 | 1.45 | 0.07 | 56% | 18% | 3% | 1% | 5% | 12% |
| Issac | 2500 | 122 | 11.7 | 0.18 | 0.91 | 0.08 | 51% | 19% | 4% | 1% | 7% | 12% |
| Prism | 2227 | 637 | 42.0 | 3.95 | 1.11 | 0.04 | 54% | 13% | 6% | 8% | 5% | 6% |
| Vesper Vale | 1607 | 270 | 37.6 | 1.56 | 0.73 | 0.03 | 51% | 21% | 5% | 2% | 8% | 4% |
| Willow | 1592 | 19 | 7.8 | 0.06 | 1.14 | 0.07 | 67% | 13% | 1% | 0% | 10% | 6% |
| Heart of Ruin | 775 | 128 | 12.8 | 0.54 | 1.11 | 0.04 | 55% | 19% | 4% | 1% | 6% | 6% |
| Ryth | 725 | 175 | 20.8 | 0.49 | 1.58 | 0.08 | 51% | 16% | 5% | 1% | 9% | 8% |
| Vendetta | 632 | 235 | 33.4 | 0.51 | 0.59 | 0.08 | 54% | 21% | 5% | 2% | 7% | 3% |
| Varg | 393 | 185 | 30.6 | 0.13 | 0.59 | 0.07 | 60% | 21% | 4% | 1% | 4% | 3% |
| Marcella | 379 | 234 | 9.8 | 1.04 | 1.60 | 0.07 | 56% | 10% | 5% | 2% | 9% | 8% |
| Ren | 329 | 141 | 16.3 | 0.55 | 1.06 | 0.02 | 53% | 21% | 4% | 1% | 7% | 6% |
| Tavi | 260 | 154 | 23.3 | 0.96 | 1.74 | 0.07 | 53% | 17% | 5% | 1% | 7% | 9% |
| Stellar | 82 | 203 | 30.1 | 0.46 | 1.33 | 0.01 | 53% | 18% | 5% | 1% | 9% | 7% |

Games to r2000: 98; W carried at end mean 1200, L 142; tributed W 613, L 310
Gems still carried at the end (both teams): mean 394, games with 300+: 1025
