# Parent vs v33 ordinary-throughput replay audit

Saved exact-parent Big World replay: `provenance/willow-phased-solo-boss-4d08241-v1/outputs/latest-parent-B-vs-v33-big-world.repl26a`; bundle SHA-256 `15a703f86fd6cbf7ca9b14fddc9136f2100bc5afce87520905b274c82cbe670c`; inner `replay.repl26a` payload SHA-256 `0022ca3c4d26d95df367ba021ef4d2b435f2eaccb9e3c76708ba5821619f14dc`. Side A is frozen v33; side B is exact latest parent. Final result: A wins round 780, gems 1110–474 (A–B). This is event-summary-only; no new engine decode or actor-window trace was run.

Movement distance sums each move event as Chebyshev tile-steps (gameplay range metric) and Manhattan tile-steps; it excludes recall/teleport displacement. Recall/teleport counts are event counts. End bag is champion `gems` in final metadata; collected/submitted are separate lifetime stats. Physical team (A/B) is explicit; group coordinates below are map tile coordinates from the extracted map.

## Prism and Vesper

| Side / actor | Moves | Chebyshev tiles | Manhattan tiles | Recall start/cancel/end | Teleport start/end | Tribute start/end | Tribute start/end gems | Tribute gold | Capture-share records (gems/gold) | End bag (collected/submitted) |
|---|---:|---:|---:|---|---|---|---|---:|---|---|
| A (frozen v33), Prism#0 | 457 | 457 | 764 | 727/720/7 | 0/0 | 1/1 | 131/131 | 0 | 7 (131/980) | 0 (131/131) |
| A (frozen v33), Vesper Vale#1 | 435 | 435 | 723 | 675/666/8 | 0/0 | 10/10 | 592/592 | 0 | 11 (331/3034) | 0 (592/592) |
| B (exact latest parent), Prism#5 | 440 | 440 | 735 | 702/694/8 | 0/0 | 0/0 | 0/0 | 0 | 11 (261/1690) | 0 (261/0) |
| B (exact latest parent), Vesper Vale#6 | 435 | 435 | 801 | 727/718/8 | 0/0 | 3/3 | 31/31 | 0 | 5 (31/542) | 0 (31/31) |

## Capture shares by group

| Group | Map-side / mirror | Member tile coordinates | A captures (gems/gold) | B captures (gems/gold) |
|---:|---|---|---|---|
| 0 | 0 / 1 | (28,22), (27,21), (27,22) | 5 (35/208) | — |
| 1 | 1 / 0 | (71,77), (72,78), (72,77) | — | 5 (35/200) |
| 2 | 0 / 3 | (53,28), (52,27), (52,28) | 7 (147/0) | — |
| 3 | 1 / 2 | (46,71), (47,72), (47,71) | — | 9 (189/0) |
| 4 | 0 / 5 | (63,42), (64,42), (64,43), (65,43) | — | 3 (45/300) |
| 5 | 1 / 4 | (36,57), (35,57), (35,56), (34,56) | 3 (45/406) | 1 (15/100) |
| 6 | 0 / 7 | (61,10), (60,11), (61,11), (60,10), (59,10), (59,11) | 8 (328/2650) | — |
| 7 | 1 / 6 | (38,89), (39,88), (38,88), (39,89), (40,89), (40,88) | — | 6 (246/1768) |
| 8 | 1 / 9 | (17,36), (18,36), (17,35), (18,35), (18,37), (17,37) | 4 (148/1163) | — |
| 9 | 0 / 8 | (82,63), (81,63), (82,64), (81,64), (81,62), (82,62) | — | 2 (74/380) |
| 10 | 0 / 11 | (40,34), (40,33) | 3 (0/128) | — |
| 11 | 1 / 10 | (59,65), (59,66) | — | 3 (0/120) |
| 13 | 1 / 12 | (85,84), (86,84) | — | 3 (42/0) |
| 18 | 0 / 19 | (73,24), (74,24) | 4 (16/240) | — |
| 19 | 1 / 18 | (26,75), (25,75) | — | 5 (20/403) |
| 20 | 0 / 21 | (7,1), (6,1) | 1 (4/72) | — |
| 22 | 0 / 23 | (88,3), (89,3), (87,3) | 7 (105/1073) | — |
| 23 | 1 / 22 | (11,96), (10,96), (12,96) | — | 6 (90/875) |

Full structured results: [`summary.json`](summary.json).
