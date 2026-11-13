# s2 tables

40983 chance turns over 1024 traced team-games (40.0 a team-game).
Turns without an end line (ran out of fuel, or stale): 0 (0%).

**Episodes** (per target per 10 rounds): 11.18 a team-game; converted 2.62 (23%), by our Prism 2.10.
Killers of converted episodes: Prism 2.10, Vesper Vale 0.19, Cassi 0.07, their side 0.04, Marcella 0.04, Issac 0.04, Ryth 0.03, Heart of Ruin 0.03, Willow 0.02, Ren 0.01, Tavi 0.01, Stellar 0.01, Vendetta 0.00, Varg 0.00

### By distance, stun and enemy Prism (onset)

| key | per team-game | converted | by our Prism | missed per team-game |
|---|---|---|---|---|
| d 6, stun ready, no enemy Prism within 8 | 3.35 | 23% | 18% | 2.58 |
| d 6, stun ready, enemy Prism within 8 | 2.81 | 11% | 9% | 2.50 |
| d 6, stun down, no enemy Prism within 8 | 1.09 | 16% | 13% | 0.92 |
| d 6, stun down, enemy Prism within 8 | 0.75 | 7% | 6% | 0.70 |
| d 5, stun ready, no enemy Prism within 8 | 0.64 | 51% | 41% | 0.31 |
| d 5, stun ready, enemy Prism within 8 | 0.36 | 28% | 24% | 0.26 |
| d 5, stun down, no enemy Prism within 8 | 0.35 | 29% | 24% | 0.25 |
| d 5, stun down, enemy Prism within 8 | 0.31 | 15% | 12% | 0.26 |
| d 4, stun down, no enemy Prism within 8 | 0.28 | 34% | 21% | 0.19 |
| d 4, stun ready, no enemy Prism within 8 | 0.26 | 74% | 63% | 0.07 |
| d <=3, stun down, no enemy Prism within 8 | 0.24 | 48% | 33% | 0.13 |
| d 4, stun down, enemy Prism within 8 | 0.23 | 18% | 11% | 0.19 |
| d <=3, stun ready, no enemy Prism within 8 | 0.19 | 77% | 70% | 0.04 |
| d <=3, stun down, enemy Prism within 8 | 0.16 | 29% | 19% | 0.11 |
| d 4, stun ready, enemy Prism within 8 | 0.10 | 59% | 50% | 0.04 |
| d <=3, stun ready, enemy Prism within 8 | 0.06 | 64% | 49% | 0.02 |
| all | 11.18 | 23% | 19% | 8.56 |

### By our branch at the onset (decide exit)

| key | per team-game | converted | by our Prism | missed per team-game |
|---|---|---|---|---|
| farm | 3.70 | 20% | 16% | 2.96 |
| tribute kept | 2.15 | 41% | 32% | 1.27 |
| want_home retreat | 2.11 | 9% | 7% | 1.93 |
| carry_bag | 1.04 | 38% | 32% | 0.64 |
| chase | 1.01 | 31% | 23% | 0.70 |
| stop game-ender | 0.45 | 5% | 5% | 0.43 |
| hold capture | 0.37 | 15% | 14% | 0.32 |
| altar guard | 0.20 | 12% | 10% | 0.17 |
| recall kept | 0.05 | 2% | 2% | 0.05 |
| Prism-Willow support | 0.04 | 9% | 7% | 0.04 |
| contest | 0.04 | 13% | 13% | 0.03 |
| siege/kite | 0.02 | 24% | 20% | 0.02 |
| support retreat | 0.01 | 0% | 0% | 0.01 |
| shop trip | 0.00 | 0% | 0% | 0.00 |
| all | 11.18 | 23% | 19% | 8.56 |

### By the chase gate at the onset (prey() asked at decide start)

| key | per team-game | converted | by our Prism | missed per team-game |
|---|---|---|---|---|
| refused: healthy (>=45%) off our ground, no bag/hold | 4.55 | 20% | 18% | 3.62 |
| refused: fight sim lost | 1.64 | 13% | 10% | 1.43 |
| refused: escapes (chase verdict) | 1.14 | 16% | 14% | 0.95 |
| chosen | 1.09 | 47% | 39% | 0.58 |
| chosen (we pressed it) | 0.77 | 41% | 25% | 0.45 |
| prey() not run | 0.68 | 20% | 17% | 0.54 |
| refused: pack covers it | 0.43 | 7% | 6% | 0.40 |
| refused: fight already lost (same fight) | 0.31 | 10% | 8% | 0.28 |
| chosen (team pressed it) | 0.28 | 62% | 38% | 0.11 |
| another target chosen first | 0.25 | 34% | 28% | 0.16 |
| refused: near its spawn / out of sight | 0.04 | 25% | 25% | 0.03 |
| chosen (comeback, fight lost) | 0.00 | 20% | 20% | 0.00 |
| all | 11.18 | 23% | 19% | 8.56 |

### Primary cause

Onset branch first (channels, retreats, the bag), then whether a chase ran, then the gate verdict.

| key | per team-game | converted | by our Prism | missed per team-game |
|---|---|---|---|---|
| tribute channel kept | 2.15 | 41% | 32% | 1.27 |
| gate refused: healthy (>=45%) off our ground, no bag/hold | 2.11 | 12% | 11% | 1.85 |
| want_home / retreat | 1.98 | 9% | 7% | 1.81 |
| chased, no kill | 1.03 | 30% | 22% | 0.72 |
| gate refused: escapes (chase verdict) | 0.72 | 11% | 9% | 0.64 |
| gate refused: fight sim lost | 0.71 | 11% | 9% | 0.63 |
| carry_bag: gate refuses too | 0.60 | 25% | 21% | 0.45 |
| we were stunned | 0.57 | 27% | 23% | 0.42 |
| gate would chase, other branch (farm) | 0.40 | 64% | 48% | 0.15 |
| carry_bag: gate would chase, carry_bag did not ask | 0.23 | 65% | 52% | 0.08 |
| gate refused: prey() not run | 0.19 | 25% | 21% | 0.15 |
| gate refused: pack covers it | 0.18 | 9% | 9% | 0.16 |
| gate refused: fight already lost (same fight) | 0.10 | 7% | 5% | 0.09 |
| gate would chase, other branch (hold capture) | 0.06 | 39% | 38% | 0.04 |
| gate refused: another target chosen first | 0.05 | 43% | 41% | 0.03 |
| recall kept | 0.05 | 2% | 2% | 0.05 |
| gate refused: near its spawn / out of sight | 0.02 | 24% | 24% | 0.02 |
| gate would chase, other branch (altar guard) | 0.01 | 31% | 23% | 0.01 |
| gate would chase, other branch (stop game-ender) | 0.01 | 17% | 17% | 0.00 |
| gate would chase, other branch (Prism-Willow support) | 0.00 | 0% | 0% | 0.00 |
| gate would chase, other branch (siege/kite) | 0.00 | 67% | 67% | 0.00 |
| all | 11.18 | 23% | 19% | 8.56 |

### Our channel at onset (a recall is restarted every turn end and usually cancelled)

| key | per team-game | converted | by our Prism | missed per team-game |
|---|---|---|---|---|
| recall (feint or kept) | 7.03 | 18% | 15% | 5.75 |
| tribute | 2.29 | 41% | 31% | 1.36 |
| none | 1.85 | 22% | 18% | 1.45 |
| all | 11.18 | 23% | 19% | 8.56 |

### Target turns before our next turn (engine order)

| key | per team-game | converted | by our Prism | missed per team-game |
|---|---|---|---|---|
| 1 | 5.94 | 23% | 18% | 4.57 |
| 2 | 2.90 | 20% | 16% | 2.31 |
| 0 | 2.34 | 28% | 23% | 1.68 |
| all | 11.18 | 23% | 19% | 8.56 |

### Target type

| key | per team-game | converted | by our Prism | missed per team-game |
|---|---|---|---|---|
| Willow | 2.47 | 13% | 10% | 2.16 |
| Cassi | 2.43 | 28% | 24% | 1.75 |
| Issac | 2.17 | 27% | 22% | 1.59 |
| Vesper Vale | 1.26 | 19% | 15% | 1.02 |
| Ryth | 1.00 | 27% | 20% | 0.73 |
| Heart of Ruin | 0.48 | 25% | 16% | 0.36 |
| Marcella | 0.35 | 35% | 28% | 0.23 |
| Tavi | 0.28 | 32% | 27% | 0.19 |
| Ren | 0.26 | 34% | 28% | 0.17 |
| Vendetta | 0.19 | 27% | 25% | 0.13 |
| Varg | 0.17 | 20% | 16% | 0.14 |
| Stellar | 0.10 | 24% | 19% | 0.08 |
| all | 11.18 | 23% | 19% | 8.56 |

### Target channel at onset

| key | per team-game | converted | by our Prism | missed per team-game |
|---|---|---|---|---|
| recall | 9.38 | 22% | 18% | 7.32 |
| none | 1.62 | 33% | 22% | 1.08 |
| tribute | 0.18 | 10% | 10% | 0.17 |
| all | 11.18 | 23% | 19% | 8.56 |

### Target on its own side (own_ground false = their side)

| key | per team-game | converted | by our Prism | missed per team-game |
|---|---|---|---|---|
| their side | 8.70 | 23% | 19% | 6.73 |
| our side | 2.48 | 26% | 20% | 1.83 |
| all | 11.18 | 23% | 19% | 8.56 |

### Target in bush / we in bush

| key | per team-game | converted | by our Prism | missed per team-game |
|---|---|---|---|---|
| target bush 0, us bush 0 | 10.33 | 22% | 18% | 8.01 |
| target bush 0, us bush 1 | 0.63 | 38% | 30% | 0.40 |
| target bush 1, us bush 0 | 0.16 | 24% | 20% | 0.12 |
| target bush 1, us bush 1 | 0.05 | 35% | 29% | 0.03 |
| all | 11.18 | 23% | 19% | 8.56 |

### Our bag at onset

| key | per team-game | converted | by our Prism | missed per team-game |
|---|---|---|---|---|
| 150+ | 8.59 | 26% | 22% | 6.39 |
| 50-149 | 1.67 | 15% | 10% | 1.43 |
| 1-49 | 0.51 | 19% | 8% | 0.41 |
| 0 | 0.41 | 18% | 11% | 0.34 |
| all | 11.18 | 23% | 19% | 8.56 |

### Target health share at onset

| key | per team-game | converted | by our Prism | missed per team-game |
|---|---|---|---|---|
| 90%+ | 5.97 | 24% | 21% | 4.54 |
| 80%+ | 1.03 | 21% | 17% | 0.82 |
| 60%+ | 0.90 | 18% | 14% | 0.75 |
| 50%+ | 0.72 | 20% | 14% | 0.58 |
| 70%+ | 0.71 | 18% | 14% | 0.58 |
| 40%+ | 0.71 | 21% | 13% | 0.56 |
| 30%+ | 0.55 | 25% | 18% | 0.41 |
| 20%+ | 0.33 | 39% | 21% | 0.20 |
| 10%+ | 0.17 | 51% | 22% | 0.09 |
| 0%+ | 0.08 | 62% | 23% | 0.03 |
| all | 11.18 | 23% | 19% | 8.56 |

### Burst margin (our stun+ground raw / target effective hp)

| key | per team-game | converted | by our Prism | missed per team-game |
|---|---|---|---|---|
| 2.5+ | 4.66 | 36% | 30% | 3.00 |
| 1.6-2.5 | 2.82 | 17% | 13% | 2.34 |
| 1.2-1.6 | 2.32 | 13% | 9% | 2.01 |
| <1.2 | 1.38 | 13% | 9% | 1.20 |
| all | 11.18 | 23% | 19% | 8.56 |

## Missed episodes (8.56 a team-game)

### Missed: primary cause x target turns before our next

| key | per team-game | converted | by our Prism | missed per team-game |
|---|---|---|---|---|
| want_home / retreat | 1 | 1.11 | 0% | 0% | 1.11 |
| gate refused: healthy (>=45%) off our ground, no bag/hold | 1 | 0.95 | 0% | 0% | 0.95 |
| tribute channel kept | 1 | 0.81 | 0% | 0% | 0.81 |
| gate refused: healthy (>=45%) off our ground, no bag/hold | 2 | 0.59 | 0% | 0% | 0.59 |
| want_home / retreat | 2 | 0.37 | 0% | 0% | 0.37 |
| want_home / retreat | 0 | 0.33 | 0% | 0% | 0.33 |
| gate refused: fight sim lost | 1 | 0.32 | 0% | 0% | 0.32 |
| chased, no kill | 1 | 0.31 | 0% | 0% | 0.31 |
| gate refused: healthy (>=45%) off our ground, no bag/hold | 0 | 0.31 | 0% | 0% | 0.31 |
| gate refused: escapes (chase verdict) | 1 | 0.30 | 0% | 0% | 0.30 |
| chased, no kill | 2 | 0.27 | 0% | 0% | 0.27 |
| tribute channel kept | 0 | 0.24 | 0% | 0% | 0.24 |
| gate refused: escapes (chase verdict) | 2 | 0.24 | 0% | 0% | 0.24 |
| carry_bag: gate refuses too | 1 | 0.22 | 0% | 0% | 0.22 |
| tribute channel kept | 2 | 0.21 | 0% | 0% | 0.21 |
| we were stunned | 0 | 0.21 | 0% | 0% | 0.21 |
| gate refused: fight sim lost | 2 | 0.19 | 0% | 0% | 0.19 |
| we were stunned | 1 | 0.18 | 0% | 0% | 0.18 |
| carry_bag: gate refuses too | 2 | 0.15 | 0% | 0% | 0.15 |
| chased, no kill | 0 | 0.14 | 0% | 0% | 0.14 |
| gate refused: fight sim lost | 0 | 0.12 | 0% | 0% | 0.12 |
| gate refused: escapes (chase verdict) | 0 | 0.10 | 0% | 0% | 0.10 |
| gate refused: pack covers it | 1 | 0.08 | 0% | 0% | 0.08 |
| carry_bag: gate refuses too | 0 | 0.07 | 0% | 0% | 0.07 |
| gate refused: prey() not run | 1 | 0.06 | 0% | 0% | 0.06 |
| gate refused: pack covers it | 2 | 0.06 | 0% | 0% | 0.06 |
| gate refused: fight already lost (same fight) | 1 | 0.06 | 0% | 0% | 0.06 |
| gate would chase, other branch (farm) | 2 | 0.06 | 0% | 0% | 0.06 |
| gate would chase, other branch (farm) | 1 | 0.05 | 0% | 0% | 0.05 |
| gate refused: prey() not run | 2 | 0.05 | 0% | 0% | 0.05 |
| all | 8.56 | 0% | 0% | 8.56 |

### Missed: what the target did before our next turn (onset)

| key | per team-game | converted | by our Prism | missed per team-game |
|---|---|---|---|---|
| move,recall_start | 5.09 | 0% | 0% | 5.09 |
| nothing | 1.88 | 0% | 0% | 1.88 |
| cast_Dash,move,recall_start | 0.20 | 0% | 0% | 0.20 |
| atk,recall_start | 0.19 | 0% | 0% | 0.19 |
| recall_start | 0.19 | 0% | 0% | 0.19 |
| cast_Heal,move,recall_start | 0.14 | 0% | 0% | 0.14 |
| atk,move,recall_start | 0.12 | 0% | 0% | 0.12 |
| cast_AoE damage,recall_start | 0.07 | 0% | 0% | 0.07 |
| cast_CC,move,recall_start | 0.07 | 0% | 0% | 0.07 |
| atk,cast_Attack reset,move,recall_start | 0.07 | 0% | 0% | 0.07 |
| cast_Shield,move,recall_start | 0.07 | 0% | 0% | 0.07 |
| move | 0.04 | 0% | 0% | 0.04 |
| cast_AoE damage,move,recall_start | 0.03 | 0% | 0% | 0.03 |
| cast_Heal | 0.03 | 0% | 0% | 0.03 |
| atk,cast_Dash,move,recall_start | 0.03 | 0% | 0% | 0.03 |
| all | 8.56 | 0% | 0% | 8.56 |

### Missed: distance at our next turn (onset d -> next d)

| key | per team-game | converted | by our Prism | missed per team-game |
|---|---|---|---|---|
| 6 -> 6 | 2.81 | 0% | 0% | 2.81 |
| 6 -> 7 | 2.46 | 0% | 0% | 2.46 |
| 6 -> 5 | 0.72 | 0% | 0% | 0.72 |
| 6 -> 8 | 0.49 | 0% | 0% | 0.49 |
| 5 -> 5 | 0.43 | 0% | 0% | 0.43 |
| 5 -> 6 | 0.36 | 0% | 0% | 0.36 |
| 4 -> 4 | 0.19 | 0% | 0% | 0.19 |
| 4 -> 5 | 0.17 | 0% | 0% | 0.17 |
| 5 -> 4 | 0.13 | 0% | 0% | 0.13 |
| 5 -> 7 | 0.10 | 0% | 0% | 0.10 |
| 6 -> 9 | 0.09 | 0% | 0% | 0.09 |
| 3 -> 4 | 0.08 | 0% | 0% | 0.08 |
| 3 -> 3 | 0.08 | 0% | 0% | 0.08 |
| 4 -> 6 | 0.06 | 0% | 0% | 0.06 |
| 6 -> None | 0.06 | 0% | 0% | 0.06 |
| 4 -> 3 | 0.05 | 0% | 0% | 0.05 |
| 6 -> 4 | 0.05 | 0% | 0% | 0.05 |
| 3 -> 5 | 0.03 | 0% | 0% | 0.03 |
| 5 -> 8 | 0.03 | 0% | 0% | 0.03 |
| 1 -> 1 | 0.02 | 0% | 0% | 0.02 |
| all | 8.56 | 0% | 0% | 8.56 |

### Missed: did our Prism damage it in the 8 rounds

| key | per team-game | converted | by our Prism | missed per team-game |
|---|---|---|---|---|
| no hit | 7.30 | 0% | 0% | 7.30 |
| hit | 0.91 | 0% | 0% | 0.91 |
| stun hit, hit | 0.22 | 0% | 0% | 0.22 |
| stun hit, no hit | 0.12 | 0% | 0% | 0.12 |
| all | 8.56 | 0% | 0% | 8.56 |

### Missed: healed / shielded by its side in the 8 rounds

| key | per team-game | converted | by our Prism | missed per team-game |
|---|---|---|---|---|
| healed 0, shield 0 | 6.88 | 0% | 0% | 6.88 |
| healed 1, shield 0 | 1.31 | 0% | 0% | 1.31 |
| healed 0, shield 1 | 0.30 | 0% | 0% | 0.30 |
| healed 1, shield 1 | 0.06 | 0% | 0% | 0.06 |
| all | 8.56 | 0% | 0% | 8.56 |

### Missed: we died within 8 rounds

| key | per team-game | converted | by our Prism | missed per team-game |
|---|---|---|---|---|
| 0 | 8.05 | 0% | 0% | 8.05 |
| 1 | 0.51 | 0% | 0% | 0.51 |
| all | 8.56 | 0% | 0% | 8.56 |

### Gate verdict x distance (onset)

| key | per team-game | converted | by our Prism | missed per team-game |
|---|---|---|---|---|
| refused: healthy (>=45%) off our ground, no bag/hold | d 6 | 3.74 | 16% | 14% | 3.12 |
| refused: fight sim lost | d 6 | 1.20 | 10% | 8% | 1.08 |
| refused: escapes (chase verdict) | d 6 | 1.11 | 16% | 14% | 0.93 |
| refused: healthy (>=45%) off our ground, no bag/hold | d 5 | 0.60 | 34% | 30% | 0.39 |
| chosen | d 6 | 0.49 | 31% | 21% | 0.34 |
| prey() not run | d 6 | 0.46 | 13% | 11% | 0.40 |
| chosen | d 5 | 0.31 | 51% | 44% | 0.15 |
| refused: pack covers it | d 6 | 0.29 | 5% | 5% | 0.28 |
| refused: fight sim lost | d 5 | 0.26 | 17% | 12% | 0.21 |
| refused: fight already lost (same fight) | d 6 | 0.25 | 6% | 5% | 0.23 |
| chosen (we pressed it) | d 4 | 0.24 | 38% | 18% | 0.15 |
| refused: healthy (>=45%) off our ground, no bag/hold | d 4 | 0.21 | 52% | 47% | 0.10 |
| chosen (we pressed it) | d 6 | 0.19 | 34% | 25% | 0.13 |
| chosen (we pressed it) | d 3 | 0.19 | 46% | 31% | 0.10 |
| another target chosen first | d 6 | 0.17 | 30% | 23% | 0.12 |
| chosen | d 4 | 0.14 | 70% | 62% | 0.04 |
| prey() not run | d 5 | 0.14 | 28% | 23% | 0.10 |
| refused: fight sim lost | d 4 | 0.11 | 20% | 18% | 0.09 |
| chosen | d 3 | 0.11 | 67% | 62% | 0.04 |
| chosen (we pressed it) | d 5 | 0.09 | 48% | 28% | 0.04 |
| chosen (team pressed it) | d 5 | 0.08 | 56% | 37% | 0.04 |
| chosen (team pressed it) | d 6 | 0.07 | 51% | 21% | 0.04 |
| refused: pack covers it | d 5 | 0.06 | 14% | 9% | 0.05 |
| chosen (team pressed it) | d 4 | 0.05 | 61% | 35% | 0.02 |
| prey() not run | d 4 | 0.05 | 45% | 36% | 0.03 |
| chosen (team pressed it) | d 3 | 0.05 | 83% | 56% | 0.01 |
| refused: fight already lost (same fight) | d 5 | 0.05 | 16% | 14% | 0.04 |
| refused: fight sim lost | d 3 | 0.05 | 31% | 22% | 0.03 |
| another target chosen first | d 5 | 0.04 | 41% | 35% | 0.03 |
| chosen (we pressed it) | d 2 | 0.04 | 56% | 34% | 0.02 |
| all | 11.18 | 23% | 19% | 8.56 |

### Exit x gate (onset)

| key | per team-game | converted | by our Prism | missed per team-game |
|---|---|---|---|---|
| farm | refused: healthy (>=45%) off our ground, no bag/hold | 1.71 | 13% | 12% | 1.48 |
| tribute kept | refused: healthy (>=45%) off our ground, no bag/hold | 1.14 | 41% | 34% | 0.67 |
| want_home retreat | refused: healthy (>=45%) off our ground, no bag/hold | 0.71 | 7% | 7% | 0.65 |
| want_home retreat | refused: fight sim lost | 0.64 | 10% | 9% | 0.58 |
| farm | refused: escapes (chase verdict) | 0.60 | 12% | 10% | 0.53 |
| farm | refused: fight sim lost | 0.56 | 12% | 10% | 0.49 |
| carry_bag | refused: healthy (>=45%) off our ground, no bag/hold | 0.39 | 33% | 30% | 0.26 |
| tribute kept | chosen | 0.37 | 49% | 35% | 0.19 |
| chase | chosen | 0.29 | 30% | 24% | 0.20 |
| chase | chosen (we pressed it) | 0.29 | 39% | 25% | 0.18 |
| tribute kept | refused: escapes (chase verdict) | 0.27 | 31% | 27% | 0.19 |
| farm | chosen (we pressed it) | 0.24 | 56% | 33% | 0.11 |
| stop game-ender | refused: healthy (>=45%) off our ground, no bag/hold | 0.23 | 5% | 5% | 0.22 |
| want_home retreat | refused: pack covers it | 0.23 | 6% | 5% | 0.21 |
| farm | prey() not run | 0.17 | 22% | 18% | 0.14 |
| carry_bag | chosen | 0.17 | 61% | 53% | 0.07 |
| farm | chosen | 0.17 | 68% | 64% | 0.06 |
| hold capture | refused: healthy (>=45%) off our ground, no bag/hold | 0.17 | 9% | 9% | 0.15 |
| chase | prey() not run | 0.17 | 20% | 19% | 0.13 |
| want_home retreat | refused: fight already lost (same fight) | 0.16 | 8% | 7% | 0.15 |
| want_home retreat | chosen (we pressed it) | 0.16 | 15% | 9% | 0.13 |
| tribute kept | refused: fight sim lost | 0.14 | 27% | 22% | 0.10 |
| want_home retreat | prey() not run | 0.13 | 4% | 4% | 0.13 |
| stop game-ender | refused: pack covers it | 0.12 | 5% | 5% | 0.12 |
| carry_bag | refused: fight sim lost | 0.12 | 20% | 18% | 0.10 |
| chase | refused: healthy (>=45%) off our ground, no bag/hold | 0.10 | 17% | 16% | 0.08 |
| carry_bag | refused: escapes (chase verdict) | 0.08 | 19% | 16% | 0.07 |
| carry_bag | prey() not run | 0.08 | 25% | 20% | 0.06 |
| tribute kept | chosen (team pressed it) | 0.08 | 69% | 32% | 0.02 |
| chase | another target chosen first | 0.07 | 29% | 25% | 0.05 |
| all | 11.18 | 23% | 19% | 8.56 |

## Chance turns (not deduplicated)

| exit | real prey verdict | shadow verdict | per team-game |
|---|---|---|---|
| farm | refused: healthy (>=45%) off our ground, no bag/hold | refused: healthy (>=45%) off our ground, no bag/hold | 4.94 |
| tribute kept | prey() not run | refused: healthy (>=45%) off our ground, no bag/hold | 3.39 |
| want_home retreat | prey() not run | refused: healthy (>=45%) off our ground, no bag/hold | 2.72 |
| want_home retreat | prey() not run | refused: fight sim lost | 2.55 |
| carry_bag | prey() not run | refused: healthy (>=45%) off our ground, no bag/hold | 1.87 |
| farm | refused: fight sim lost | refused: fight sim lost | 1.72 |
| farm | refused: escapes (chase verdict) | refused: escapes (chase verdict) | 1.71 |
| tribute kept | prey() not run | chosen | 1.18 |
| chase | chosen (we pressed it) | chosen (we pressed it) | 0.99 |
| farm | prey() not run | chosen (we pressed it) | 0.96 |
| want_home retreat | prey() not run | refused: pack covers it | 0.91 |
| farm | prey() not run | refused: healthy (>=45%) off our ground, no bag/hold | 0.90 |
| hold capture | prey() not run | refused: healthy (>=45%) off our ground, no bag/hold | 0.88 |
| chase | chosen | chosen | 0.84 |
| carry_bag | prey() not run | chosen | 0.77 |
| farm | prey() not run | prey() not run | 0.74 |
| stop game-ender | prey() not run | refused: healthy (>=45%) off our ground, no bag/hold | 0.73 |
| want_home retreat | prey() not run | refused: fight already lost (same fight) | 0.67 |
| tribute kept | prey() not run | refused: escapes (chase verdict) | 0.62 |
| want_home retreat | prey() not run | prey() not run | 0.60 |
| chase | prey() not run | prey() not run | 0.60 |
| tribute kept | prey() not run | chosen (team pressed it) | 0.56 |
| farm | prey() not run | chosen | 0.50 |
| carry_bag | prey() not run | refused: fight sim lost | 0.42 |
| carry_bag | prey() not run | chosen (team pressed it) | 0.38 |

Bot predicted target turns (may act after us + before ours next) vs engine order: 0->0: 927, 0->1: 494, 1->0: 7346, 1->1: 16323, 1->2: 2510, 2->1: 4608, 2->2: 8775
### Sizing: onset turns that did not act on the target, against acting turns in the same stratum

Acting turns (chase, cast or step in at onset) by stratum: d3 66%, d3 stun 88%, d3 stun eP 66%, d4 43%, d4 eP 34%, d4 stun 82%, d4 stun eP 65%, d5 35%, d5 eP 26%, d5 stun 51%, d5 stun eP 32%, d6 18%, d6 eP 11%, d6 stun 24%, d6 stun eP 13%.

| cause (onset turn did not act) | per team-game | converted | acting-rate conversion | added kills per team-game (upper bound) |
|---|---|---|---|---|
| want_home / retreat | 1.52 | 6% | 20% | +0.21 |
| gate refused: healthy (>=45%) off our ground, no bag/hold | 1.10 | 7% | 20% | +0.14 |
| gate refused: escapes (chase verdict) | 0.43 | 8% | 20% | +0.05 |
| gate refused: fight sim lost | 0.39 | 7% | 21% | +0.05 |
| we were stunned | 0.57 | 26% | 32% | +0.03 |
| carry_bag: gate refuses too | 0.29 | 15% | 19% | +0.01 |
| gate refused: prey() not run | 0.07 | 19% | 27% | +0.01 |
| gate refused: pack covers it | 0.06 | 12% | 17% | +0.00 |
| gate would chase, other branch (farm) | 0.11 | 49% | 50% | +0.00 |
| carry_bag: gate would chase, carry_bag did not ask | 0.06 | 35% | 29% | -0.00 |
| tribute channel kept | 2.15 | 41% | 30% | -0.23 |
| all | 6.93 | 20% | 25% | +0.31 |
### Lethal windows (burst > effective hp), first turn per target per 10 rounds

| window | onset branch / what we did | per team-game | converted |
|---|---|---|---|
| **d<=4, stun ready, ground back by our next turn** | all | 1.28 | 82% |
| | tribute kept, no act | 0.48 | 77% |
| | carry_bag, no act | 0.21 | 97% |
| | farm, stun | 0.17 | 91% |
| | carry_bag, stun | 0.15 | 99% |
| | want_home retreat, stun | 0.06 | 70% |
| | farm, no act | 0.04 | 82% |
| **d5, stun ready, ground back by our next turn** | all | 1.99 | 54% |
| | tribute kept, no act | 0.74 | 66% |
| | farm, ground | 0.47 | 65% |
| | want_home retreat, ground | 0.10 | 36% |
| | carry_bag, ground | 0.10 | 81% |
| | farm, no act | 0.09 | 20% |
| | carry_bag, no act | 0.09 | 54% |
| **d6, stun ready** | all | 7.30 | 17% |
| | tribute kept, no act | 1.56 | 33% |
| | farm, no act | 1.22 | 6% |
| | farm, step in | 0.94 | 17% |
| | want_home retreat, no act | 0.83 | 5% |
| | chase, step in | 0.52 | 29% |
| | carry_bag, no act | 0.42 | 20% |

### enemy_turn_before_ours_next for the target vs the engine order (chance turns)

| bot says | engine: acts before our next turn | engine: does not |
|---|---|---|
| acts | 22757 | 11954 |
| does not act | 3004 | 3268 |

`enemy_may_act_after_us` (this round) matched the engine on every chance turn.
