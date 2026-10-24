# Latest-base Big World boss pair

The two preauthorized normal-draft Release 100k games used physical side B for the candidate and its exact latest-base parent, physical side A for frozen v33, and `maps/01big-world.map26a`. Both drafts were identical: Prism, Vesper Vale, Marcella, Willow, Heart of Ruin. No opponent editing or additional games were used.

| B bot | Result | B gems | B-side native play rollovers | B-side bot errors |
|---|---:|---:|---:|---:|
| Exact parent `astraeus-4d08241` | A wins, r780 | 474 | 3 | 0 |
| Candidate `willow-phased-solo-boss-4d08241-work` | A wins, r975 | 748 | 3 | 0 |

A was v33 in both games and had 4 play rollovers and 0 errors in each. Draft and other-phase rollovers/errors were 0 on both sides. Native status was decoded from each replay with the pinned v1_0_3 engine; details and raw replay/map hashes are in `audit-parent/status.json` and `audit-candidate/status.json`. These are single-game diagnostics, not a win-rate comparison.

The extracted map has two mixed Monolith groups: group 16, Monolith camp 57 at (48,48), and group 17, Monolith camp 56 at (51,51). Both replays contain zero attack/cast events against either Monolith camp ID and no camp-death, group-clear, capture, or capture-hold events for either group. Thus neither game observed boss damage, clear, or capture conversion. Across all Marcella round snapshots, the minimum Chebyshev distance to any member tile in either group was 13 for the candidate (r474, (64,65), group17 tile (51,52)) and 7 for the parent (r191, (59,58), group17 tile (52,51)). The Euclidean-nearest Monolith points were respectively 16.1 at r485 and 10.6 at r191. Neither approached the mixed-boss groups late. No living-priority or native actor-order claim is inferred from these semantic event records.

Candidate Marcella survived to r975 and had 4,200/4,200 HP, 500 Strength, 315 Focus at r900, then 3,544.8/4,200 HP, 500 Strength, 315 Focus at r950 and r975. At r975 she was at (49,79), still distance 28 from camp 56, and in a recall channel. Her r900 inventory was item/count pairs `[17:1,19:1,25:1,36:4,37:15,41:2]`; r950/r975 had `[17:1,19:1,25:1,36:4,37:15,41:2]`. Enum decoding: Durability Emblem of Health, Treasure Emblem of Strength, Jungle Emblem of Strength, Bruiser Shard of Strength, Bruiser Emblem of Strength, Bruiser Emblem of Health. At r780 candidate Marcella was 2,805.4/3,700 HP, 365 Strength, 240 Focus, also channeling recall. The exact parent ended at r780 with Marcella alive at 3,047.2/3,400 HP, 250 Strength, 330 Focus, in a recall channel; inventory `[17:1,19:1,27:1,36:3,37:6,39:1,41:2]` (Durability Emblem of Health, Treasure Emblem of Strength, Jungle Emblem of Focus, Bruiser Shard/Emblem of Strength, Bruiser Emblem of Focus, Bruiser Emblem of Health).

The candidate had materially stronger late stats and the game ran 195 rounds longer, but it never reached either boss group in this replay. Since the parent match ended at r780, before the later candidate window, the pair does not establish that the mechanic is infeasible or that more time alone would trigger it. Overall group-clear/capture counts are not used as boss conversion evidence.

The frozen source/build inputs and paired outputs are pinned in `preflight.json`; extraction logs and files are under `extracted/`. Native-status audit inputs, logs, and duty receipts are preserved alongside each audit. Runtime work used the shared clock-recovery workspace and left SDK bytes/mtimes unchanged.
