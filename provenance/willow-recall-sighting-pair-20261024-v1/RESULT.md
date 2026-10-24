# Combined recall and sighting audit

This audit covers existing native game outputs only; it adds no games. Source is the reviewed combined child aggregate `29ac1251ddc63c1b3e824d9c1d6182df57890e62b3757d5e362fe15be3a91e60`. Toolchain, engine, map, and WASM pins are in [RESULT.json](RESULT.json).

The first Big World run was misordered. Its original manifest placed the candidate first, so the actual assignment was candidate A vs frozen v33 B, despite the old output filename. That game finished A 1000–757 in round 953. It is preserved as an A-side diagnostic. The corrected, root-reviewed row ran frozen v33 A vs candidate B and finished A 1014–588 in round 877. The Pilgrimage row correctly ran candidate A vs v33 B and finished A 1030–210 in round 1358. These are single-game outcomes, not strength estimates.

All drafts were the same five picks on each side: Prism, Vesper Vale, Marcella, Willow, Heart of Ruin. The saved-control comparisons are bound to original candidate and rerun reference replay paths, exact physical sides, and maps in `RESULT.json` and the six `comparison-*.json` receipts:

- Misordered Big World candidate A vs parent A and recall-only A: first difference at event r11, s2309, actor 2, candidate `Recall` vs reference `Cast ability`; both comparisons had 35,585 input events, 12 matching round hashes, and ended 1000–757 r953. Payloads were not exact.
- Corrected Big World candidate B vs parent B and recall-only B: first difference at r11, s2339, actor 7, candidate `Recall` vs reference `Cast ability` on camp 53. Candidate/recall had 32,792 input events; parent had 28,990. There were 12 matching round hashes. Candidate vs recall ended at the same 1014–588 r877 result, but the payloads were not exact; candidate vs parent ended 1014–588 r877 vs 1110–474 r780.
- Pilgrimage candidate A vs parent A: first difference at r1183, s236380, actor 0, candidate `Move` vs reference `Recall`; inputs 51,804 vs 51,803 and 1,184 matching round hashes. Both ended 1030–210 r1358, but payloads were not exact. Candidate A vs sighting-only A was byte-for-byte payload exact: 51,804 inputs, 1,359 matching round hashes, same 1030–210 r1358 result.

Round snapshot status counts use turn code 6 for fuel rollover and 7 for error. Misordered Big World: candidate A 3 rollovers/0 errors; v33 B 8/0. Corrected Big World: v33 A 4/0; candidate B 3/0. Pilgrimage: candidate A 0/0; v33 B 6/0. Actor counts are in the JSON receipt. The `meta.faults` field is not used as an error count.

At the corrected Big World first divergence, decoded events show the same actor-7 camp attack at s2338, then candidate `recall_start` at s2339 while the references cast on camp 53. No nearby champion contact appears in decoded events/state. Round-snapshot status codes match through this point, including the common HoR rollover at event r11. The snapshot cannot establish within-round ordering, and mailbox payloads are not serialized, so this does not prove or rule out a remote shared sighting. Do not characterize this as confirmed sighting-policy activation.

Candidate Prism fate: misordered Big World A collected/submitted 510/510 with bag 0 and no deaths; corrected Big World B collected 287, submitted 0, ended with bag 287, and had no deaths; Pilgrimage A collected/submitted 141/141 with bag 0 and no deaths.

The initial failed misoriented comparison attempt remains as the zero-byte `comparison-misoriented-bigworld-A-vs-parent-A.json`; its path error is preserved in the earlier run logs. The completed side-corrected comparisons are separate files and do not overwrite it.
