## Fish

529 games (2026-11-06); Home emblem on 0.3% of recalls.

**1. Counts** (open at game end left out)

| class | recalls | % | per game |
| --- | ---: | ---: | ---: |
| started | 2085172 | 100.0 | 3941.7 |
| **real** (completed + kept then interrupted) | 23643 | 1.1 | 44.7 |
| &nbsp; completed | 20448 | 1.0 | 38.7 |
| &nbsp; kept, then damage | 2119 | 0.1 | 4.0 |
| &nbsp; kept, then stun | 822 | 0.0 | 1.6 |
| &nbsp; kept, then death | 254 | 0.0 | 0.5 |
| **feint** (cancelled by hand at its first own turn) | 1706368 | 81.8 | 3225.6 |
| abandoned (kept a turn or more, then cancelled by hand) | 58689 | 2.8 | 110.9 |
| **undecided** (interrupted before its first own turn) | 296472 | 14.2 | 560.4 |
| &nbsp; damage | 282969 | 13.6 | 534.9 |
| &nbsp; stun | 10761 | 0.5 | 20.3 |
| &nbsp; death | 2742 | 0.1 | 5.2 |
| &nbsp; of which no round-end window (interrupted the round it started) | 33435 | 1.6 | 63.2 |

Undecided recalls followed within 2 rounds by a recall the champion kept: 3.0% (of 291213 followed by any recall).
Decided recalls with first-window hp<50%: 10.8% real; undecided ones with that health: 29496.
Decided recalls with first-window hp<100%: 2.8% real; undecided ones with that health: 224217.

**2. Rules, every window** (precision: real / (real + feint + abandoned), undecided left out)

| rule | flagged | precision % | recall % | undecided among flagged % | precision % if undecided = real |
| --- | ---: | ---: | ---: | ---: | ---: |
| (a) any window | 2051737 | 1.3 | 100.0 | 12.8 | 14.0 |
| (b) first window | 2051737 | 1.3 | 100.0 | 12.8 | 14.0 |
| (c) 2nd+ window (current) | 81504 | 28.0 | 96.5 | 0.0 | 28.0 |
| (d) first window, hp<25% | 24885 | 17.9 | 14.7 | 21.7 | 35.7 |
| (d) first window, hp<33% | 43338 | 17.8 | 25.2 | 22.8 | 36.5 |
| (d) first window, hp<50% | 129149 | 10.8 | 45.6 | 22.8 | 31.2 |
| (d) first window, hp<66% | 270588 | 6.5 | 57.1 | 23.1 | 28.1 |
| (d) first window, hp<75% | 404569 | 4.6 | 61.3 | 22.0 | 25.5 |
| (d) first window, hp<100% | 910438 | 2.8 | 81.7 | 24.6 | 26.7 |
| (e) 2nd+ window, hp<25% | 4138 | 81.5 | 14.3 | 0.0 | 81.5 |
| (e) 2nd+ window, hp<33% | 6925 | 83.5 | 24.5 | 0.0 | 83.5 |
| (e) 2nd+ window, hp<50% | 13773 | 76.0 | 44.3 | 0.0 | 76.0 |
| (e) 2nd+ window, hp<66% | 20107 | 65.1 | 55.4 | 0.0 | 65.1 |
| (e) 2nd+ window, hp<75% | 24781 | 56.7 | 59.4 | 0.0 | 56.7 |
| (e) 2nd+ window, hp<100% | 45694 | 40.8 | 78.8 | 0.0 | 40.8 |
| (f) (c) or (d) hp<25% | 102220 | 23.7 | 96.9 | 5.3 | 27.7 |
| (f) (c) or (d) hp<33% | 117857 | 21.2 | 97.0 | 8.4 | 27.8 |
| (f) (c) or (d) hp<50% | 196764 | 13.8 | 97.4 | 15.0 | 26.7 |
| (f) (c) or (d) hp<66% | 331817 | 8.6 | 97.8 | 18.8 | 25.8 |
| (f) (c) or (d) hp<75% | 461106 | 6.2 | 98.1 | 19.3 | 24.3 |
| (f) (c) or (d) hp<100% | 945929 | 3.2 | 99.1 | 23.7 | 26.2 |

**2s. Rules, only windows an enemy saw** (seen by an enemy champion in that round or the next)

| rule | flagged | precision % | recall % | undecided among flagged % | precision % if undecided = real |
| --- | ---: | ---: | ---: | ---: | ---: |
| (a) any window | 713166 | 1.8 | 48.2 | 11.5 | 13.1 |
| (b) first window | 711090 | 1.7 | 45.0 | 11.5 | 13.0 |
| (c) 2nd+ window (current) | 35980 | 27.3 | 41.6 | 0.0 | 27.3 |
| (d) first window, hp<25% | 17732 | 12.2 | 7.4 | 19.1 | 28.9 |
| (d) first window, hp<33% | 29056 | 12.1 | 12.1 | 18.8 | 28.7 |
| (d) first window, hp<50% | 71953 | 8.9 | 22.3 | 18.1 | 25.4 |
| (d) first window, hp<66% | 144280 | 5.9 | 29.5 | 17.4 | 22.3 |
| (d) first window, hp<75% | 206171 | 4.4 | 31.7 | 16.6 | 20.3 |
| (d) first window, hp<100% | 415289 | 2.7 | 39.1 | 16.8 | 19.0 |
| (e) 2nd+ window, hp<25% | 2170 | 71.6 | 6.6 | 0.0 | 71.6 |
| (e) 2nd+ window, hp<33% | 3447 | 74.5 | 10.9 | 0.0 | 74.5 |
| (e) 2nd+ window, hp<50% | 6995 | 69.7 | 20.6 | 0.0 | 69.7 |
| (e) 2nd+ window, hp<66% | 10829 | 59.7 | 27.4 | 0.0 | 59.7 |
| (e) 2nd+ window, hp<75% | 13212 | 52.4 | 29.3 | 0.0 | 52.4 |
| (e) 2nd+ window, hp<100% | 22391 | 38.1 | 36.1 | 0.0 | 38.1 |
| (f) (c) or (d) hp<25% | 51665 | 21.0 | 42.8 | 6.5 | 26.1 |
| (f) (c) or (d) hp<33% | 61784 | 18.3 | 43.5 | 8.9 | 25.5 |
| (f) (c) or (d) hp<50% | 101363 | 12.0 | 44.8 | 12.8 | 23.3 |
| (f) (c) or (d) hp<66% | 170057 | 7.5 | 45.7 | 14.8 | 21.1 |
| (f) (c) or (d) hp<75% | 229648 | 5.6 | 46.0 | 14.9 | 19.7 |
| (f) (c) or (d) hp<100% | 430138 | 3.1 | 47.3 | 16.2 | 18.8 |

**3. Real recalls against rule (c)**: 23643 real; (c) misses 828 (3.5%: kept at the first own turn, interrupted before the second round end); reads 22815 (96.5%) one window late.

| X | missed, caught by (d) | late, caught a window earlier by (d) | extra feints flagged by (d) | extra undecided flagged by (d) |
| --- | ---: | ---: | ---: | ---: |
| 25% | 84 / 828 | 3400 / 22815 | 15231 | 5401 |
| 33% | 121 / 828 | 5839 / 22815 | 26365 | 9867 |
| 50% | 219 / 828 | 10556 / 22815 | 85545 | 29496 |
| 66% | 319 / 828 | 13177 / 22815 | 187499 | 62495 |
| 75% | 373 / 828 | 14122 / 22815 | 290410 | 88819 |
| 100% | 618 / 828 | 18704 / 22815 | 639590 | 224217 |

**First-window gems and distance** (decided recalls: % real)

| | 0 gems | 1-9 | 10+ | on spawn | 1-5 tiles | 6+ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| real % (n) | 1.3 (1103751) | 1.3 (147065) | 1.4 (537884) | 100.0 (3) | 0.3 (257692) | 1.5 (1531005) |

## Mite

520 games (2026-11-06); Home emblem on 4.5% of recalls.

**1. Counts** (open at game end left out)

| class | recalls | % | per game |
| --- | ---: | ---: | ---: |
| started | 1934911 | 100.0 | 3721.0 |
| **real** (completed + kept then interrupted) | 23204 | 1.2 | 44.6 |
| &nbsp; completed | 22443 | 1.2 | 43.2 |
| &nbsp; kept, then damage | 486 | 0.0 | 0.9 |
| &nbsp; kept, then stun | 140 | 0.0 | 0.3 |
| &nbsp; kept, then death | 135 | 0.0 | 0.3 |
| **feint** (cancelled by hand at its first own turn) | 1618470 | 83.6 | 3112.4 |
| abandoned (kept a turn or more, then cancelled by hand) | 580 | 0.0 | 1.1 |
| **undecided** (interrupted before its first own turn) | 292657 | 15.1 | 562.8 |
| &nbsp; damage | 279499 | 14.4 | 537.5 |
| &nbsp; stun | 10189 | 0.5 | 19.6 |
| &nbsp; death | 2969 | 0.2 | 5.7 |
| &nbsp; of which no round-end window (interrupted the round it started) | 32084 | 1.7 | 61.7 |

Undecided recalls followed within 2 rounds by a recall the champion kept: 1.3% (of 285228 followed by any recall).
Decided recalls with first-window hp<50%: 11.2% real; undecided ones with that health: 31520.
Decided recalls with first-window hp<100%: 2.9% real; undecided ones with that health: 231425.

**2. Rules, every window** (precision: real / (real + feint + abandoned), undecided left out)

| rule | flagged | precision % | recall % | undecided among flagged % | precision % if undecided = real |
| --- | ---: | ---: | ---: | ---: | ---: |
| (a) any window | 1902827 | 1.4 | 100.0 | 13.7 | 14.9 |
| (b) first window | 1902827 | 1.4 | 100.0 | 13.7 | 14.9 |
| (c) 2nd+ window (current) | 25338 | 91.3 | 99.5 | 0.2 | 91.4 |
| (d) first window, hp<25% | 22570 | 18.4 | 15.2 | 15.0 | 30.7 |
| (d) first window, hp<33% | 44739 | 18.0 | 28.2 | 18.5 | 33.2 |
| (d) first window, hp<50% | 131177 | 11.2 | 48.2 | 24.0 | 32.6 |
| (d) first window, hp<66% | 248761 | 8.2 | 64.0 | 26.9 | 32.9 |
| (d) first window, hp<75% | 375052 | 5.8 | 69.0 | 25.8 | 30.1 |
| (d) first window, hp<100% | 923471 | 2.9 | 87.8 | 25.1 | 27.3 |
| (e) 2nd+ window, hp<25% | 3610 | 97.3 | 15.1 | 0.0 | 97.3 |
| (e) 2nd+ window, hp<33% | 6662 | 97.9 | 28.1 | 0.0 | 97.9 |
| (e) 2nd+ window, hp<50% | 11436 | 97.4 | 48.0 | 0.0 | 97.4 |
| (e) 2nd+ window, hp<66% | 15294 | 96.7 | 63.7 | 0.1 | 96.7 |
| (e) 2nd+ window, hp<75% | 16611 | 95.9 | 68.6 | 0.1 | 95.9 |
| (e) 2nd+ window, hp<100% | 21519 | 94.3 | 87.3 | 0.2 | 94.3 |
| (f) (c) or (d) hp<25% | 44298 | 56.6 | 99.6 | 7.8 | 59.9 |
| (f) (c) or (d) hp<33% | 63415 | 42.0 | 99.6 | 13.2 | 49.6 |
| (f) (c) or (d) hp<50% | 145079 | 20.4 | 99.8 | 21.8 | 37.7 |
| (f) (c) or (d) hp<66% | 258805 | 12.1 | 99.9 | 25.9 | 34.8 |
| (f) (c) or (d) hp<75% | 383779 | 8.1 | 99.9 | 25.2 | 31.3 |
| (f) (c) or (d) hp<100% | 927290 | 3.3 | 100.0 | 25.0 | 27.5 |

**2s. Rules, only windows an enemy saw** (seen by an enemy champion in that round or the next)

| rule | flagged | precision % | recall % | undecided among flagged % | precision % if undecided = real |
| --- | ---: | ---: | ---: | ---: | ---: |
| (a) any window | 602202 | 1.7 | 38.9 | 12.5 | 14.0 |
| (b) first window | 600950 | 1.5 | 33.8 | 12.5 | 13.8 |
| (c) 2nd+ window (current) | 9108 | 85.0 | 33.2 | 0.5 | 85.0 |
| (d) first window, hp<25% | 16926 | 11.2 | 6.9 | 15.7 | 25.1 |
| (d) first window, hp<33% | 29083 | 10.7 | 11.3 | 16.1 | 25.1 |
| (d) first window, hp<50% | 72691 | 8.0 | 20.7 | 17.2 | 23.8 |
| (d) first window, hp<66% | 129715 | 5.9 | 26.9 | 18.5 | 23.3 |
| (d) first window, hp<75% | 182015 | 4.4 | 28.0 | 17.9 | 21.5 |
| (d) first window, hp<100% | 372006 | 2.4 | 31.8 | 17.5 | 19.5 |
| (e) 2nd+ window, hp<25% | 1545 | 95.7 | 6.4 | 0.0 | 95.7 |
| (e) 2nd+ window, hp<33% | 2560 | 96.1 | 10.6 | 0.0 | 96.1 |
| (e) 2nd+ window, hp<50% | 4704 | 95.1 | 19.3 | 0.1 | 95.1 |
| (e) 2nd+ window, hp<66% | 6230 | 93.7 | 25.1 | 0.1 | 93.7 |
| (e) 2nd+ window, hp<75% | 6645 | 92.1 | 26.3 | 0.2 | 92.2 |
| (e) 2nd+ window, hp<100% | 8049 | 88.8 | 30.7 | 0.4 | 88.8 |
| (f) (c) or (d) hp<25% | 24670 | 36.4 | 34.4 | 10.9 | 43.3 |
| (f) (c) or (d) hp<33% | 35975 | 26.2 | 35.3 | 13.2 | 35.9 |
| (f) (c) or (d) hp<50% | 77686 | 13.2 | 37.0 | 16.2 | 27.3 |
| (f) (c) or (d) hp<66% | 133369 | 8.1 | 38.1 | 18.0 | 24.7 |
| (f) (c) or (d) hp<75% | 185318 | 5.8 | 38.3 | 17.6 | 22.4 |
| (f) (c) or (d) hp<100% | 374145 | 2.9 | 38.7 | 17.4 | 19.8 |

**3. Real recalls against rule (c)**: 23204 real; (c) misses 105 (0.5%: kept at the first own turn, interrupted before the second round end); reads 23099 (99.5%) one window late.

| X | missed, caught by (d) | late, caught a window earlier by (d) | extra feints flagged by (d) | extra undecided flagged by (d) |
| --- | ---: | ---: | ---: | ---: |
| 25% | 13 / 105 | 3514 / 23099 | 15556 | 3391 |
| 33% | 23 / 105 | 6519 / 23099 | 29759 | 8296 |
| 50% | 57 / 105 | 11134 / 23099 | 88168 | 31520 |
| 66% | 78 / 105 | 14784 / 23099 | 166523 | 66874 |
| 75% | 87 / 105 | 15926 / 23099 | 261502 | 96863 |
| 100% | 99 / 105 | 20267 / 23099 | 670462 | 231425 |

**First-window gems and distance** (decided recalls: % real)

| | 0 gems | 1-9 | 10+ | on spawn | 1-5 tiles | 6+ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| real % (n) | 1.4 (1002889) | 1.5 (143976) | 1.5 (495389) | - (0) | 0.1 (238194) | 1.6 (1404060) |

## ocean (scrims v78-v81)

1049 games (2026-11-06); Home emblem on 10.0% of recalls.

**1. Counts** (open at game end left out)

| class | recalls | % | per game |
| --- | ---: | ---: | ---: |
| started | 4067541 | 100.0 | 3877.5 |
| **real** (completed + kept then interrupted) | 51303 | 1.3 | 48.9 |
| &nbsp; completed | 50356 | 1.2 | 48.0 |
| &nbsp; kept, then damage | 683 | 0.0 | 0.7 |
| &nbsp; kept, then stun | 98 | 0.0 | 0.1 |
| &nbsp; kept, then death | 160 | 0.0 | 0.2 |
| &nbsp; kept, then other | 6 | 0.0 | 0.0 |
| **feint** (cancelled by hand at its first own turn) | 3432648 | 84.4 | 3272.3 |
| abandoned (kept a turn or more, then cancelled by hand) | 9341 | 0.2 | 8.9 |
| **undecided** (interrupted before its first own turn) | 574249 | 14.1 | 547.4 |
| &nbsp; damage | 556188 | 13.7 | 530.2 |
| &nbsp; stun | 12056 | 0.3 | 11.5 |
| &nbsp; death | 6001 | 0.1 | 5.7 |
| &nbsp; other | 4 | 0.0 | 0.0 |
| &nbsp; of which no round-end window (interrupted the round it started) | 57327 | 1.4 | 54.6 |

Undecided recalls followed within 2 rounds by a recall the champion kept: 1.2% (of 562179 followed by any recall).
Decided recalls with first-window hp<50%: 8.0% real; undecided ones with that health: 72584.
Decided recalls with first-window hp<100%: 3.3% real; undecided ones with that health: 455083.

**2. Rules, every window** (precision: real / (real + feint + abandoned), undecided left out)

| rule | flagged | precision % | recall % | undecided among flagged % | precision % if undecided = real |
| --- | ---: | ---: | ---: | ---: | ---: |
| (a) any window | 4010214 | 1.5 | 100.0 | 12.9 | 14.2 |
| (b) first window | 4010214 | 1.5 | 100.0 | 12.9 | 14.2 |
| (c) 2nd+ window (current) | 60550 | 84.5 | 99.8 | 0.0 | 84.5 |
| (d) first window, hp<25% | 56695 | 15.1 | 12.6 | 24.7 | 36.1 |
| (d) first window, hp<33% | 104931 | 12.0 | 18.3 | 25.6 | 34.6 |
| (d) first window, hp<50% | 264346 | 8.0 | 29.7 | 27.5 | 33.2 |
| (d) first window, hp<66% | 501424 | 5.9 | 41.0 | 28.3 | 32.5 |
| (d) first window, hp<75% | 685050 | 5.1 | 48.0 | 28.9 | 32.5 |
| (d) first window, hp<100% | 1579417 | 3.3 | 71.4 | 28.8 | 31.1 |
| (e) 2nd+ window, hp<25% | 7424 | 86.5 | 12.5 | 0.0 | 86.5 |
| (e) 2nd+ window, hp<33% | 11006 | 84.7 | 18.2 | 0.0 | 84.7 |
| (e) 2nd+ window, hp<50% | 17864 | 85.0 | 29.6 | 0.0 | 85.0 |
| (e) 2nd+ window, hp<66% | 24642 | 84.9 | 40.8 | 0.0 | 84.9 |
| (e) 2nd+ window, hp<75% | 28799 | 85.1 | 47.8 | 0.0 | 85.1 |
| (e) 2nd+ window, hp<100% | 42998 | 84.9 | 71.2 | 0.0 | 84.9 |
| (f) (c) or (d) hp<25% | 109802 | 53.5 | 99.8 | 12.8 | 59.4 |
| (f) (c) or (d) hp<33% | 154448 | 40.2 | 99.8 | 17.4 | 50.6 |
| (f) (c) or (d) hp<50% | 307011 | 21.9 | 99.9 | 23.6 | 40.3 |
| (f) (c) or (d) hp<66% | 537315 | 13.0 | 99.9 | 26.5 | 36.0 |
| (f) (c) or (d) hp<75% | 716782 | 9.9 | 100.0 | 27.6 | 34.7 |
| (f) (c) or (d) hp<100% | 1596931 | 4.5 | 100.0 | 28.5 | 31.7 |

**2s. Rules, only windows an enemy saw** (seen by an enemy champion in that round or the next)

| rule | flagged | precision % | recall % | undecided among flagged % | precision % if undecided = real |
| --- | ---: | ---: | ---: | ---: | ---: |
| (a) any window | 1382629 | 1.2 | 29.2 | 10.9 | 12.0 |
| (b) first window | 1380036 | 1.0 | 24.7 | 10.9 | 11.9 |
| (c) 2nd+ window (current) | 18796 | 73.3 | 26.9 | 0.0 | 73.3 |
| (d) first window, hp<25% | 29828 | 7.2 | 3.5 | 16.8 | 22.7 |
| (d) first window, hp<33% | 55683 | 6.0 | 5.5 | 16.4 | 21.5 |
| (d) first window, hp<50% | 140696 | 4.0 | 9.1 | 17.2 | 20.5 |
| (d) first window, hp<66% | 256237 | 3.0 | 12.1 | 17.9 | 20.3 |
| (d) first window, hp<75% | 343525 | 2.5 | 13.9 | 18.0 | 20.1 |
| (d) first window, hp<100% | 711868 | 1.7 | 19.3 | 18.0 | 19.4 |
| (e) 2nd+ window, hp<25% | 2334 | 76.6 | 3.5 | 0.0 | 76.6 |
| (e) 2nd+ window, hp<33% | 3804 | 74.1 | 5.5 | 0.0 | 74.1 |
| (e) 2nd+ window, hp<50% | 6441 | 73.4 | 9.2 | 0.0 | 73.4 |
| (e) 2nd+ window, hp<66% | 8820 | 72.7 | 12.5 | 0.0 | 72.7 |
| (e) 2nd+ window, hp<75% | 10172 | 72.9 | 14.5 | 0.0 | 72.9 |
| (e) 2nd+ window, hp<100% | 14479 | 73.2 | 20.7 | 0.0 | 73.2 |
| (f) (c) or (d) hp<25% | 46635 | 33.8 | 27.4 | 10.7 | 40.9 |
| (f) (c) or (d) hp<33% | 71175 | 22.9 | 27.7 | 12.9 | 32.8 |
| (f) (c) or (d) hp<50% | 153817 | 11.1 | 28.0 | 15.7 | 25.1 |
| (f) (c) or (d) hp<66% | 267226 | 6.5 | 28.2 | 17.2 | 22.6 |
| (f) (c) or (d) hp<75% | 353343 | 5.0 | 28.4 | 17.5 | 21.6 |
| (f) (c) or (d) hp<100% | 718044 | 2.5 | 28.8 | 17.8 | 19.9 |

**3. Real recalls against rule (c)**: 51303 real; (c) misses 121 (0.2%: kept at the first own turn, interrupted before the second round end); reads 51182 (99.8%) one window late.

| X | missed, caught by (d) | late, caught a window earlier by (d) | extra feints flagged by (d) | extra undecided flagged by (d) |
| --- | ---: | ---: | ---: | ---: |
| 25% | 27 / 121 | 6435 / 51182 | 35213 | 14012 |
| 33% | 37 / 121 | 9333 / 51182 | 66973 | 26888 |
| 50% | 57 / 121 | 15194 / 51182 | 173820 | 72584 |
| 66% | 84 / 121 | 20947 / 51182 | 334546 | 142135 |
| 75% | 97 / 121 | 24533 / 51182 | 458382 | 197753 |
| 100% | 113 / 121 | 36532 / 51182 | 1081186 | 455083 |

**First-window gems and distance** (decided recalls: % real)

| | 0 gems | 1-9 | 10+ | on spawn | 1-5 tiles | 6+ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| real % (n) | 1.6 (2108460) | 1.3 (303803) | 1.2 (1081029) | - (0) | 0.9 (514096) | 1.6 (2979196) |

## astraeus (self-play)

300 games (2026-11-06); Home emblem on 8.7% of recalls.

**1. Counts** (open at game end left out)

| class | recalls | % | per game |
| --- | ---: | ---: | ---: |
| started | 2317802 | 100.0 | 7726.0 |
| **real** (completed + kept then interrupted) | 28801 | 1.2 | 96.0 |
| &nbsp; completed | 28266 | 1.2 | 94.2 |
| &nbsp; kept, then damage | 396 | 0.0 | 1.3 |
| &nbsp; kept, then stun | 71 | 0.0 | 0.2 |
| &nbsp; kept, then death | 68 | 0.0 | 0.2 |
| **feint** (cancelled by hand at its first own turn) | 1972097 | 85.1 | 6573.7 |
| abandoned (kept a turn or more, then cancelled by hand) | 4775 | 0.2 | 15.9 |
| **undecided** (interrupted before its first own turn) | 312129 | 13.5 | 1040.4 |
| &nbsp; damage | 296695 | 12.8 | 989.0 |
| &nbsp; stun | 12119 | 0.5 | 40.4 |
| &nbsp; death | 3315 | 0.1 | 11.1 |
| &nbsp; of which no round-end window (interrupted the round it started) | 36491 | 1.6 | 121.6 |

Undecided recalls followed within 2 rounds by a recall the champion kept: 1.1% (of 305944 followed by any recall).
Decided recalls with first-window hp<50%: 6.6% real; undecided ones with that health: 37865.
Decided recalls with first-window hp<100%: 2.8% real; undecided ones with that health: 242241.

**2. Rules, every window** (precision: real / (real + feint + abandoned), undecided left out)

| rule | flagged | precision % | recall % | undecided among flagged % | precision % if undecided = real |
| --- | ---: | ---: | ---: | ---: | ---: |
| (a) any window | 2281311 | 1.4 | 100.0 | 12.1 | 13.3 |
| (b) first window | 2281311 | 1.4 | 100.0 | 12.1 | 13.3 |
| (c) 2nd+ window (current) | 33534 | 85.7 | 99.8 | 0.0 | 85.7 |
| (d) first window, hp<25% | 38078 | 12.0 | 12.9 | 18.6 | 28.4 |
| (d) first window, hp<33% | 68785 | 10.0 | 19.1 | 20.1 | 28.1 |
| (d) first window, hp<50% | 169356 | 6.6 | 30.0 | 22.4 | 27.5 |
| (d) first window, hp<66% | 314619 | 4.9 | 40.8 | 23.5 | 27.2 |
| (d) first window, hp<75% | 427271 | 4.2 | 47.3 | 23.9 | 27.1 |
| (d) first window, hp<100% | 958419 | 2.8 | 70.6 | 25.3 | 27.4 |
| (e) 2nd+ window, hp<25% | 4364 | 84.9 | 12.9 | 0.0 | 84.9 |
| (e) 2nd+ window, hp<33% | 6543 | 83.4 | 19.0 | 0.0 | 83.4 |
| (e) 2nd+ window, hp<50% | 10341 | 83.1 | 29.8 | 0.0 | 83.1 |
| (e) 2nd+ window, hp<66% | 14049 | 83.3 | 40.7 | 0.0 | 83.3 |
| (e) 2nd+ window, hp<75% | 16288 | 83.4 | 47.2 | 0.0 | 83.4 |
| (e) 2nd+ window, hp<100% | 23964 | 84.6 | 70.4 | 0.0 | 84.6 |
| (f) (c) or (d) hp<25% | 67228 | 47.8 | 99.8 | 10.6 | 53.3 |
| (f) (c) or (d) hp<33% | 95749 | 35.1 | 99.9 | 14.4 | 44.5 |
| (f) (c) or (d) hp<50% | 192530 | 18.6 | 99.9 | 19.7 | 34.6 |
| (f) (c) or (d) hp<66% | 334090 | 11.1 | 99.9 | 22.1 | 30.7 |
| (f) (c) or (d) hp<75% | 444504 | 8.4 | 99.9 | 23.0 | 29.5 |
| (f) (c) or (d) hp<100% | 967974 | 4.0 | 100.0 | 25.0 | 28.0 |

**3. Real recalls against rule (c)**: 28801 real; (c) misses 54 (0.2%: kept at the first own turn, interrupted before the second round end); reads 28747 (99.8%) one window late.

| X | missed, caught by (d) | late, caught a window earlier by (d) | extra feints flagged by (d) | extra undecided flagged by (d) |
| --- | ---: | ---: | ---: | ---: |
| 25% | 8 / 54 | 3719 / 28747 | 26586 | 7100 |
| 33% | 11 / 54 | 5480 / 28747 | 48393 | 13811 |
| 50% | 20 / 54 | 8608 / 28747 | 121111 | 37865 |
| 66% | 28 / 54 | 11717 / 28747 | 226653 | 73875 |
| 75% | 34 / 54 | 13592 / 28747 | 308713 | 102223 |
| 100% | 48 / 54 | 20296 / 28747 | 692151 | 242241 |

**First-window gems and distance** (decided recalls: % real)

| | 0 gems | 1-9 | 10+ | on spawn | 1-5 tiles | 6+ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| real % (n) | 1.6 (1143568) | 1.2 (186734) | 1.1 (675371) | - (0) | 0.9 (267346) | 1.5 (1738327) |

## Fish (ladder 10-30)

231 games (2026-10-30); Home emblem on 0.5% of recalls.

**1. Counts** (open at game end left out)

| class | recalls | % | per game |
| --- | ---: | ---: | ---: |
| started | 774997 | 100.0 | 3355.0 |
| **real** (completed + kept then interrupted) | 9726 | 1.3 | 42.1 |
| &nbsp; completed | 9459 | 1.2 | 40.9 |
| &nbsp; kept, then damage | 164 | 0.0 | 0.7 |
| &nbsp; kept, then stun | 45 | 0.0 | 0.2 |
| &nbsp; kept, then death | 58 | 0.0 | 0.3 |
| **feint** (cancelled by hand at its first own turn) | 651981 | 84.1 | 2822.4 |
| abandoned (kept a turn or more, then cancelled by hand) | 517 | 0.1 | 2.2 |
| **undecided** (interrupted before its first own turn) | 112773 | 14.6 | 488.2 |
| &nbsp; damage | 108814 | 14.0 | 471.1 |
| &nbsp; stun | 2823 | 0.4 | 12.2 |
| &nbsp; death | 1123 | 0.1 | 4.9 |
| &nbsp; other | 13 | 0.0 | 0.1 |
| &nbsp; of which no round-end window (interrupted the round it started) | 10450 | 1.3 | 45.2 |

Undecided recalls followed within 2 rounds by a recall the champion kept: 1.6% (of 110797 followed by any recall).
Decided recalls with first-window hp<50%: 12.1% real; undecided ones with that health: 12904.
Decided recalls with first-window hp<100%: 3.0% real; undecided ones with that health: 88498.

**2. Rules, every window** (precision: real / (real + feint + abandoned), undecided left out)

| rule | flagged | precision % | recall % | undecided among flagged % | precision % if undecided = real |
| --- | ---: | ---: | ---: | ---: | ---: |
| (a) any window | 764547 | 1.5 | 100.0 | 13.4 | 14.7 |
| (b) first window | 764547 | 1.5 | 100.0 | 13.4 | 14.7 |
| (c) 2nd+ window (current) | 10236 | 94.9 | 99.9 | 0.0 | 94.9 |
| (d) first window, hp<25% | 8760 | 23.7 | 15.9 | 25.2 | 42.9 |
| (d) first window, hp<33% | 15901 | 23.4 | 28.3 | 26.1 | 43.4 |
| (d) first window, hp<50% | 53397 | 12.1 | 50.5 | 24.2 | 33.4 |
| (d) first window, hp<66% | 107770 | 7.3 | 61.0 | 24.8 | 30.3 |
| (d) first window, hp<75% | 156687 | 5.3 | 65.2 | 24.0 | 28.0 |
| (d) first window, hp<100% | 361953 | 3.0 | 84.8 | 24.5 | 26.7 |
| (e) 2nd+ window, hp<25% | 1683 | 91.2 | 15.8 | 0.0 | 91.2 |
| (e) 2nd+ window, hp<33% | 2952 | 92.5 | 28.1 | 0.0 | 92.5 |
| (e) 2nd+ window, hp<50% | 5267 | 92.7 | 50.2 | 0.0 | 92.7 |
| (e) 2nd+ window, hp<66% | 6374 | 92.9 | 60.9 | 0.0 | 92.9 |
| (e) 2nd+ window, hp<75% | 6790 | 93.2 | 65.1 | 0.0 | 93.2 |
| (e) 2nd+ window, hp<100% | 8727 | 94.3 | 84.6 | 0.0 | 94.3 |
| (f) (c) or (d) hp<25% | 17298 | 64.4 | 99.9 | 12.7 | 68.9 |
| (f) (c) or (d) hp<33% | 23162 | 51.1 | 100.0 | 17.9 | 59.9 |
| (f) (c) or (d) hp<50% | 58341 | 21.4 | 100.0 | 22.1 | 38.8 |
| (f) (c) or (d) hp<66% | 111625 | 11.5 | 100.0 | 24.0 | 32.7 |
| (f) (c) or (d) hp<75% | 160126 | 7.9 | 100.0 | 23.5 | 29.5 |
| (f) (c) or (d) hp<100% | 363448 | 3.5 | 100.0 | 24.3 | 27.0 |

**2s. Rules, only windows an enemy saw** (seen by an enemy champion in that round or the next)

| rule | flagged | precision % | recall % | undecided among flagged % | precision % if undecided = real |
| --- | ---: | ---: | ---: | ---: | ---: |
| (a) any window | 269494 | 1.9 | 45.0 | 12.9 | 14.5 |
| (b) first window | 269107 | 1.7 | 41.1 | 12.9 | 14.4 |
| (c) 2nd+ window (current) | 4524 | 90.0 | 41.9 | 0.0 | 90.0 |
| (d) first window, hp<25% | 5809 | 15.3 | 7.3 | 20.1 | 32.3 |
| (d) first window, hp<33% | 9612 | 15.6 | 12.3 | 20.2 | 32.6 |
| (d) first window, hp<50% | 25889 | 10.5 | 22.6 | 19.4 | 27.9 |
| (d) first window, hp<66% | 51456 | 6.6 | 28.1 | 19.3 | 24.6 |
| (d) first window, hp<75% | 73363 | 4.8 | 29.6 | 18.8 | 22.8 |
| (d) first window, hp<100% | 160713 | 2.7 | 36.7 | 18.4 | 20.6 |
| (e) 2nd+ window, hp<25% | 784 | 83.5 | 6.7 | 0.0 | 83.5 |
| (e) 2nd+ window, hp<33% | 1316 | 85.4 | 11.6 | 0.0 | 85.4 |
| (e) 2nd+ window, hp<50% | 2455 | 86.5 | 21.8 | 0.0 | 86.5 |
| (e) 2nd+ window, hp<66% | 3086 | 87.2 | 27.7 | 0.0 | 87.2 |
| (e) 2nd+ window, hp<75% | 3240 | 87.6 | 29.2 | 0.0 | 87.6 |
| (e) 2nd+ window, hp<100% | 4026 | 89.2 | 36.9 | 0.0 | 89.2 |
| (f) (c) or (d) hp<25% | 9581 | 49.4 | 42.7 | 12.2 | 55.5 |
| (f) (c) or (d) hp<33% | 12881 | 38.4 | 43.2 | 15.1 | 47.7 |
| (f) (c) or (d) hp<50% | 28113 | 18.6 | 44.1 | 17.9 | 33.1 |
| (f) (c) or (d) hp<66% | 53117 | 10.0 | 44.5 | 18.7 | 26.8 |
| (f) (c) or (d) hp<75% | 74885 | 7.1 | 44.6 | 18.5 | 24.3 |
| (f) (c) or (d) hp<100% | 161538 | 3.3 | 44.8 | 18.3 | 21.0 |

**3. Real recalls against rule (c)**: 9726 real; (c) misses 7 (0.1%: kept at the first own turn, interrupted before the second round end); reads 9719 (99.9%) one window late.

| X | missed, caught by (d) | late, caught a window earlier by (d) | extra feints flagged by (d) | extra undecided flagged by (d) |
| --- | ---: | ---: | ---: | ---: |
| 25% | 1 / 7 | 1550 / 9719 | 4857 | 2204 |
| 33% | 3 / 7 | 2753 / 9719 | 8779 | 4144 |
| 50% | 6 / 7 | 4907 / 9719 | 35195 | 12904 |
| 66% | 7 / 7 | 5928 / 9719 | 74637 | 26745 |
| 75% | 7 / 7 | 6335 / 9719 | 112320 | 37563 |
| 100% | 7 / 7 | 8244 / 9719 | 264707 | 88498 |

**First-window gems and distance** (decided recalls: % real)

| | 0 gems | 1-9 | 10+ | on spawn | 1-5 tiles | 6+ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| real % (n) | 1.4 (455716) | 1.7 (46061) | 1.6 (160447) | 100.0 (5) | 0.2 (92076) | 1.7 (570143) |

## Mite (ladder 10-30)

227 games (2026-10-30); Home emblem on 0.0% of recalls.

**1. Counts** (open at game end left out)

| class | recalls | % | per game |
| --- | ---: | ---: | ---: |
| started | 820825 | 100.0 | 3616.0 |
| **real** (completed + kept then interrupted) | 9573 | 1.2 | 42.2 |
| &nbsp; completed | 9393 | 1.1 | 41.4 |
| &nbsp; kept, then damage | 142 | 0.0 | 0.6 |
| &nbsp; kept, then stun | 23 | 0.0 | 0.1 |
| &nbsp; kept, then death | 15 | 0.0 | 0.1 |
| **feint** (cancelled by hand at its first own turn) | 683933 | 83.3 | 3012.9 |
| abandoned (kept a turn or more, then cancelled by hand) | 480 | 0.1 | 2.1 |
| **undecided** (interrupted before its first own turn) | 126839 | 15.5 | 558.8 |
| &nbsp; damage | 122724 | 15.0 | 540.6 |
| &nbsp; stun | 3198 | 0.4 | 14.1 |
| &nbsp; death | 907 | 0.1 | 4.0 |
| &nbsp; other | 10 | 0.0 | 0.0 |
| &nbsp; of which no round-end window (interrupted the round it started) | 16328 | 2.0 | 71.9 |

Undecided recalls followed within 2 rounds by a recall the champion kept: 0.8% (of 124376 followed by any recall).
Decided recalls with first-window hp<50%: 10.3% real; undecided ones with that health: 11816.
Decided recalls with first-window hp<100%: 2.8% real; undecided ones with that health: 97901.

**2. Rules, every window** (precision: real / (real + feint + abandoned), undecided left out)

| rule | flagged | precision % | recall % | undecided among flagged % | precision % if undecided = real |
| --- | ---: | ---: | ---: | ---: | ---: |
| (a) any window | 804497 | 1.4 | 100.0 | 13.7 | 14.9 |
| (b) first window | 804497 | 1.4 | 100.0 | 13.7 | 14.9 |
| (c) 2nd+ window (current) | 10322 | 92.4 | 99.6 | 0.1 | 92.5 |
| (d) first window, hp<25% | 9990 | 16.1 | 13.5 | 19.5 | 32.4 |
| (d) first window, hp<33% | 17091 | 14.8 | 20.1 | 23.8 | 35.1 |
| (d) first window, hp<50% | 45865 | 10.3 | 36.8 | 25.8 | 33.4 |
| (d) first window, hp<66% | 91728 | 7.5 | 52.0 | 27.4 | 32.9 |
| (d) first window, hp<75% | 134684 | 6.0 | 61.1 | 27.3 | 31.7 |
| (d) first window, hp<100% | 390067 | 2.8 | 85.6 | 25.1 | 27.2 |
| (e) 2nd+ window, hp<25% | 1341 | 95.5 | 13.4 | 0.0 | 95.5 |
| (e) 2nd+ window, hp<33% | 2011 | 95.1 | 20.0 | 0.0 | 95.1 |
| (e) 2nd+ window, hp<50% | 3734 | 93.7 | 36.5 | 0.0 | 93.7 |
| (e) 2nd+ window, hp<66% | 5243 | 94.2 | 51.6 | 0.0 | 94.2 |
| (e) 2nd+ window, hp<75% | 6151 | 94.6 | 60.8 | 0.0 | 94.6 |
| (e) 2nd+ window, hp<100% | 8673 | 94.1 | 85.2 | 0.0 | 94.1 |
| (f) (c) or (d) hp<25% | 18971 | 56.1 | 99.7 | 10.3 | 60.6 |
| (f) (c) or (d) hp<33% | 25402 | 44.8 | 99.7 | 16.0 | 53.6 |
| (f) (c) or (d) hp<50% | 52453 | 23.5 | 99.8 | 22.5 | 40.8 |
| (f) (c) or (d) hp<66% | 96807 | 13.4 | 99.9 | 26.0 | 35.9 |
| (f) (c) or (d) hp<75% | 138855 | 9.4 | 100.0 | 26.5 | 33.4 |
| (f) (c) or (d) hp<100% | 391716 | 3.3 | 100.0 | 25.0 | 27.4 |

**2s. Rules, only windows an enemy saw** (seen by an enemy champion in that round or the next)

| rule | flagged | precision % | recall % | undecided among flagged % | precision % if undecided = real |
| --- | ---: | ---: | ---: | ---: | ---: |
| (a) any window | 300285 | 1.4 | 37.4 | 12.1 | 13.3 |
| (b) first window | 299777 | 1.2 | 32.5 | 12.1 | 13.1 |
| (c) 2nd+ window (current) | 3675 | 87.4 | 33.5 | 0.1 | 87.4 |
| (d) first window, hp<25% | 6277 | 10.4 | 5.8 | 15.8 | 24.6 |
| (d) first window, hp<33% | 10007 | 10.4 | 9.0 | 17.3 | 26.0 |
| (d) first window, hp<50% | 25513 | 8.1 | 17.6 | 17.8 | 24.4 |
| (d) first window, hp<66% | 51217 | 5.3 | 23.4 | 18.2 | 22.5 |
| (d) first window, hp<75% | 73369 | 4.0 | 25.3 | 18.0 | 21.3 |
| (d) first window, hp<100% | 182958 | 1.9 | 29.9 | 17.0 | 18.6 |
| (e) 2nd+ window, hp<25% | 554 | 91.2 | 5.3 | 0.0 | 91.2 |
| (e) 2nd+ window, hp<33% | 878 | 91.7 | 8.4 | 0.0 | 91.7 |
| (e) 2nd+ window, hp<50% | 1781 | 90.0 | 16.7 | 0.0 | 90.0 |
| (e) 2nd+ window, hp<66% | 2384 | 90.2 | 22.5 | 0.0 | 90.2 |
| (e) 2nd+ window, hp<75% | 2621 | 90.2 | 24.7 | 0.0 | 90.2 |
| (e) 2nd+ window, hp<100% | 3278 | 88.3 | 30.2 | 0.0 | 88.3 |
| (f) (c) or (d) hp<25% | 9461 | 39.1 | 34.6 | 10.5 | 45.6 |
| (f) (c) or (d) hp<33% | 12899 | 30.1 | 35.0 | 13.5 | 39.5 |
| (f) (c) or (d) hp<50% | 27581 | 15.0 | 36.1 | 16.5 | 29.0 |
| (f) (c) or (d) hp<66% | 52755 | 8.1 | 36.8 | 17.6 | 24.3 |
| (f) (c) or (d) hp<75% | 74716 | 5.7 | 36.9 | 17.7 | 22.4 |
| (f) (c) or (d) hp<100% | 183776 | 2.3 | 37.3 | 16.9 | 18.9 |

**3. Real recalls against rule (c)**: 9573 real; (c) misses 38 (0.4%: kept at the first own turn, interrupted before the second round end); reads 9535 (99.6%) one window late.

| X | missed, caught by (d) | late, caught a window earlier by (d) | extra feints flagged by (d) | extra undecided flagged by (d) |
| --- | ---: | ---: | ---: | ---: |
| 25% | 11 / 38 | 1281 / 9535 | 6689 | 1949 |
| 33% | 14 / 38 | 1913 / 9535 | 11001 | 4065 |
| 50% | 22 / 38 | 3498 / 9535 | 30293 | 11816 |
| 66% | 33 / 38 | 4941 / 9535 | 61286 | 25166 |
| 75% | 34 / 38 | 5818 / 9535 | 91663 | 36836 |
| 100% | 36 / 38 | 8156 / 9535 | 283460 | 97901 |

**First-window gems and distance** (decided recalls: % real)

| | 0 gems | 1-9 | 10+ | on spawn | 1-5 tiles | 6+ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| real % (n) | 1.4 (424086) | 1.4 (66007) | 1.3 (203893) | - (0) | 0.1 (99576) | 1.6 (594410) |

