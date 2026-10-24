# Big World Mite pair: decoded macro comparison

Both existing extractor-v2 replays were read from their saved `meta`, `rounds`, and `events` files. No replay engine pass was run. Team A is Mite in both matches. The loss replay ended at round 1109; the win replay ran to 1151 and is clipped here to the shared round-1109 horizon. Submission versions remain unverified.

The full per-group capture-cycle sequence, round checkpoints, all Marcella capture/tribute/shop events, and replay-input hashes are in [bigworld-pair-macro-v2.json](bigworld-pair-macro-v2.json), SHA-256 `fc81639bbc834290870d32c260a51c247a963e31afbd2227028be509a7cbae90`.

| Replay | Result | Captures by A / B through r1109 | Champion capture-share gems, A | Champion capture-share gems, B |
|---|---:|---:|---|---|
| `cf39cebf-e598-4540-afaa-b470321fe98a` | A 835–1017 B, loss | 48 / 56 | Marcella 254, Ryth 261, Vendetta 204, Vesper 86, Tavi 137 | Marcella 485, HoR 199, Vesper 189, Ryth 131, Vendetta 125 |
| `9c04eaa5-42af-47a1-babb-5bcf4fb0b523` | A 1004–796 B, win | 50 / 48 | Marcella 264, Ryth 258, Vendetta 257, Vesper 131, Tavi 88 | Vesper 362, Marcella 206, HoR 107, Vendetta 124, Ryth 4 |

Capture-share gems sum contribution records from `capture` events; they are not unique carried or submitted gems. Group timelines retain the source capture event, not inferred camp ownership between events.

| Shared checkpoint | Loss A gold earned / spent / bank gold; score / bags | Loss B | Win A | Win B |
|---|---:|---:|---:|---:|
| r400 | 1796 / 1760 / 36; 86 / 87 | 1417 / 1260 / 157; 168 / 61 | 1796 / 1760 / 36; 86 / 87 | 2281 / 2240 / 41; 184 / 19 |
| r600 | 3247 / 3130 / 117; 250 / 84 | 2506 / 2270 / 236; 323 / 43 | 3367 / 3250 / 117; 250 / 99 | 4023 / 3980 / 43; 352 / 30 |
| r800 | 5018 / 4930 / 88; 470 / 62 | 4042 / 3860 / 182; 514 / 28 | 5107 / 5050 / 57; 513 / 45 | 5678 / 5440 / 238; 479 / 74 |
| r1109 | 8494 / 8110 / 384; 835 / 114 | 6861 / 6320 / 541; 1017 / 90 | 8818 / 8470 / 348; 968 / 15 | 8046 / 7240 / 806; 755 / 41 |

Checkpoint format is cumulative earned gold / cumulative negative shop transactions / current champion gold inventory; team score / current carried gems. “Team score” is the native round column, not a reconstruction from tribute events.

The recurring gem loops are actor-resolved in the JSON. On Mite A, group 6 (41 gems) was captured ten times in both games; group 22 (15 gems) thirteen times in both; group 18 (4 gems) ten times in the loss and nine times in the win. B captured group 7 (41 gems) once in the loss and seven times in the win, and group 9 (37 gems) six times in both. Group 2 (21 gems) was captured by B twice in the loss (r302, r1095) and not captured by either side by r1109 in the win. This is the useful check against treating group 10 as a gem loop: group 10 is pure gold (0 gems, 40 gold).

Mite Marcella’s first capture was that pure-gold group 10 at r88 in both games (0 gems, 40 gold). In both games she next captured group 22 at r202 (15 gems) and group 6 at r229 (41 gems), then completed her first tribute at r257: 56 gems submitted, 112 gold earned. On the losing replay, opponent Marcella’s first capture was group 11 at r125 (0 gems), then group 7 at r186 (41 gems); her first tribute completed at r283 with 56 gems and 134 gold. In the winning replay opponent Marcella first captured group 23 at r122 (15 gems), then group 19 at r159 (4 gems), and completed her first tribute at r285 with 34 gems and 81 gold. The full chronological shop and subsequent tribute records are preserved in the JSON.

For the loss replay’s boss group 16 (static group HP begins at 20,480), the first recorded damage was opponent Marcella (actor 6, team B) at r823: 120 damage killed camp 58 and reduced the group HP column to 20,360. Her arrival path begins r815; no earlier group-16 damage event appears in the replay. Group camp 57 produced 28 `camp_attack` events against her for 126 damage each between r824 and r855; the four missing rounds are r826, r834, r842, and r850, so damage did not occur every round. She used a 319-damage basic attack at r825, Damage at r826, and Attack reset at r833, r841, and r849. The own-view export records 572 HP at r858 when she begins recall from [44,56]; recall completes at r863 at base [21,88]. She returned to the group by r940 at full 4,200 HP. During the later clear, camp 57 produced 19 further 126-damage events against her from r942 through r962, with gaps at r949 and r957. Final camp deaths were 57 at r962, 46 at r963, 54 at r964, and 60 at r965; the group clear was r965, capture hold began r966, and B captured at r971 for a 228-gem share. Marcella started recall at r966 and completed it at r971 carrying 228 gems; she started tribute at r1010 and completed it at r1033, submitting 228 gems and earning 548 gold. Thus r971 is both the capture and recall-completion round, not a banked-gem round. Actor 6’s extracted `sees` and `seenBy` round columns are empty across this interval; they do not establish opponent visibility more generally. No group-16 clear/capture event appears in the paired win replay through r1109.

Generated by `summarize_bigworld_pair_v2.py`; the original first-pass outputs are unchanged. Static group values are taken from the extracted map JSON.
