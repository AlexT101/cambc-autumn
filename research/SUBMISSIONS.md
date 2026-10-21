# Ladder submissions

The public API returns a null submission id and version, so `replays/mine` games are split by time (UTC) and our draft. Unranked scrims just after a submission can still show the old draft, because opponents can challenge an older version, so filter by draft too.

| # | Time (UTC) | Bot | Draft |
|---|---|---|---|
| 1 | 2026-10-14 17:38 | aphelios ~v8 | cassi, stellar, ryth |
| 2 | 2026-10-15 04:24 | aphelios v10 | cassi, stellar, ryth |
| 3 | 2026-10-15 12:43 | morgana e2010e4 | cassi, stellar, varg |
| 4 | 2026-10-15 20:06 | morgana 7477dbe | cassi, stellar, varg |
| 5 | 2026-10-15 23:35 | morgana ec43299 | cassi, stellar, varg |
| 6 | 2026-10-16 19:51 | morgana 96e33f5 | cassi, stellar, varg |
| 7 | 2026-10-16 21:10 | morgana 4708870 | cassi, stellar, varg |
| 8 | 2026-10-16 21:18 | rival ffc64b2 | cassi, varg, stellar, ryth, tavi |
| 9 | 2026-10-17 12:59 | nemesis e647cbd | as #8 |
| 10 | 2026-10-17 14:22 | nemesis 6d98e92 | as #8 |
| 11 | 2026-10-18 03:58 | nemesis ea54740 | as #8 |
| 12 | unrecorded | | |
| 13 | 2026-10-18 06:10 | nemesis 2dba924 | as #8 |
| 14-17 | unrecorded | | |
| 18 | 2026-10-18 15:05 | hecate fddba49 | as #8 |
| 19 | 2026-10-18 18:58 | hecate fddba49 + uncommitted changes | ren, stellar, cassi, ryth, varg |
| 20 | 2026-10-18 19:34 | #19 + uncommitted changes | as #19 |
| 21 | 2026-10-18 20:28 | #20 + big-bag escort | as #19 |
| 22 | 2026-10-18 21:34 | #21 with no escort on shared-gem maps | as #19 |
| — | 2026-10-18 ~22:10 | version 20 made active again | as #19 |
| 24 | 2026-10-19 ~03:15 | hecate ed3b2ac | as #19 |
| 25 | 2026-10-19 11:47 | hecate d21e894 | as #19 |
| 26 | 2026-10-19 18:32 | hecate 8e9aed7 | as #19; on shared-gem maps (stampede) stellar, ryth, prism, ren, cassi |
| 27 | 2026-10-19 19:26 | hecate 4ba1865 | as #19 |
| 28 | 2026-10-19 19:35 | hecate 6e3d387 | as #19 |
| 29 | 2026-10-19 19:42 | hecate d72c1c2 | as #26 |
| 30 | 2026-10-19 19:49 | hecate 65d5605 | as #19 |
| 31 | 2026-10-20 16:28 | hecate 284eb73 (SDK 3.0.1 / week 2 patch: new stats, Heart of Ruin and golem out-of-bounds fixes, camp reach per monster type 54.3% vs hecate-v7, gem limits rescaled 52.8% on top) | as #19 |
| 32 | 2026-10-20 22:29 | hecate cb5b461 (SDK 3.0.2 / Heart of Ruin nerf, Heart of Ruin played and modelled, dash crossings, crystal hops, holders by tribute length; new draft from research/hyperion/DRAFT.md) | heart_of_ruin, marcella, vesper_vale, ryth, stellar |

Add a row with each new submission.
