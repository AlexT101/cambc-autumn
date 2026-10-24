# A67 Treasure exposure from published80 controls

Existing extracts only; a67 is selected from manifest order using pinned workspace paths. The games use 3–5 picks, so per-role denominators vary. No new game run, build, or extraction was performed.

Native per-round `earned` comes from the engine snapshot `earnedGold` field. The extractor separately reports event-derived gold as a soft check; that derived value is not used here. First completion is the first end-of-round snapshot with a Treasure Emblem. Post-completion income is terminal native earned minus earned at the end of that round, excluding the whole completion round.

The fixed-schedule estimate is `0.2 / (1 + base passive + 0.2) × post-completion native earned` (Vesper base passive 0.33; others 0; Marcella’s tribute-generated gold is eligible). It is a floor-counterfactual approximation, not causal ROI or proof of benefit: it assumes the observed purchase schedule and behavior, and ignores costs and schedule changes. Partial means at least one Treasure shard appeared, but no Treasure emblem appeared, across the recorded snapshots.

| Role | Completed | Partial | No Treasure | First completion round, median [min–max] | Post-completion native earned, median [min–max] | Implied fixed-schedule bonus, median [min–max] | No Durability item at terminal | No Jungle item at terminal | Neither item |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Heart of Ruin | 74 | 5 | 1 | 210.5 [42–958] (n=74) | 1032 [0–3648] (n=74) | 172 [0–608] (n=74) | 44/80 | 31/80 | 11/80 |
| Marcella | 64 | 3 | 1 | 166 [30–1072] (n=64) | 1814 [48–9432] (n=64) | 302.333 [8–1572] (n=64) | 10/68 | 13/68 | 5/68 |
| Prism | 0 | 0 | 80 | — | — | — | 24/80 | 14/80 | 7/80 |
| Vesper Vale | 76 | 1 | 3 | 161 [24–1084] (n=76) | 1400 [0–4437] (n=76) | 183.007 [0–580] (n=76) | 11/80 | 11/80 | 5/80 |
| Willow | 39 | 3 | 10 | 379 [79–1121] (n=39) | 288 [0–1428] (n=39) | 48 [0–238] (n=39) | 38/52 | 19/52 | 16/52 |

At terminal, across 360 a67 champions: 127 had no Durability-family item, 88 had no Jungle-family item, and 44 had neither. Counts excluding emblems only: 155 had no Durability emblem and 98 had no Jungle emblem.

The Willow champion appeared in 52 of the 80 a67 rosters. At terminal, 38/52 had no Durability-family item, 19/52 had no Jungle-family item, and 16/52 had neither; 42/52 had no Durability emblem and 23/52 had no Jungle emblem.

Detailed per-game/per-champion records, input hashes, and replay SHA256 pins are in `report.json`.
