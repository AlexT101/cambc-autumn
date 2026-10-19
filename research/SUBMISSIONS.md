# Ladder submissions

The public API returns a null submission id and version, so `replays/mine` games are split by time (UTC) and our draft. Unranked scrims just after a submission can still show the old draft, because opponents can challenge an older version, so filter by draft too.

| # | Time (UTC) | Bot | Draft |
|---|---|---|---|
| 1 | 2026-10-14 17:38 | aphelios ~v8 | cassi, stellar, ryth |
| 2 | 2026-10-15 04:24 | aphelios v10, random draft off | cassi, stellar, ryth |
| 3 | 2026-10-15 12:43 | morgana e2010e4 | cassi, stellar, varg |
| 4 | 2026-10-15 20:06 | morgana 7477dbe | cassi, stellar, varg |
| 5 | 2026-10-15 23:35 | morgana ec43299 | cassi, stellar, varg |
| 6 | 2026-10-16 19:51 | morgana 96e33f5 (one-price farm) | cassi, stellar, varg |
| 7 | 2026-10-16 21:10 | morgana 4708870 (#6 with fuel savings) | cassi, stellar, varg |
| 8 | 2026-10-16 21:18 | rival ffc64b2 | cassi, varg, stellar, ryth, tavi |
| 9 | 2026-10-17 12:59 | nemesis e647cbd | as #8 |
| 10 | 2026-10-17 14:22 | nemesis 6d98e92 (camp tie-break by turn order) | as #8 |
| 11 | 2026-10-18 03:58 | nemesis ea54740 (fuel overhaul, bush wards) | as #8 |
| 12 | unrecorded | see the platform's submissions page | |
| 13 | 2026-10-18 06:10 | nemesis 2dba924 (least exposed retreat step) | as #8 |
| 14-17 | unrecorded | see the platform's submissions page | |
| 18 | 2026-10-18 15:05 | hecate fddba49 | as #8 |
| 19 | 2026-10-18 18:58 | hecate fddba49 + Fish draft, Focus Ren with reflect in camp estimates, v17 farm port, Cassi gold farmer, Cassi/Issac weaker-body targeting (uncommitted at submission) | ren, stellar, cassi, ryth, varg |
| 20 | 2026-10-18 19:34 | #19 + siege walks funded by fuel not distance (swirl stall), tribute safety over 6 turns, chip hits on harmless camps during spell cooldowns (uncommitted at submission) | as #19 |
| 21 | 2026-10-18 20:28 | #20 + big-bag escort: a 150+ carrier waits for 2 allies before banking, empty-handed allies within 18 come and guard it | as #19 |
| 22 | 2026-10-18 21:34 | #21 with no escort on shared-gem maps (v21 lost both stampede scrims v20 had won) | as #19 |
| — | 2026-10-18 ~22:10 | version 20 made active again (ladder scrims: v20 28-47, v21 26-49, v22 24-51 on the same maps) | as #19 |
| 24 | 2026-10-19 ~03:15 | hecate ed3b2ac: cleanup, bug fixes 2.1-2.6, v17 port replaced by farm-native spell clears and pickups (54.4% vs version 20 locally) | as #19 |
| 25 | 2026-10-19 11:47 | hecate d21e894 (overnight session: strike planner, Reach danger model, carrier chasing, siege fixes, measured emblems and banking, fuel work; 58.0% vs version 24 locally) | as #19 |
| 26 | 2026-10-19 18:32 | hecate 8e9aed7 (fuel round 3 and gate removals, spellcaster draft on shared-gem maps: 63.3% there vs hecate-v6 locally) | as #19; on shared-gem maps (stampede) stellar, ryth, prism, ren, cassi |
| 27 | 2026-10-19 19:26 | hecate 4ba1865 (version 25 plus fuel round 3 and the stunned-turn change only, the hecate-v5 baseline), to isolate the fuel work on the ladder after v26 scrimmed 46-89 vs v25's 50-85 on the same nine teams. Scrims vs the top 5 on the same maps (seed 20261019): v25 31-44, v26 24-51, v27 26-49; Fish 3-12 / 0-15 / 1-14 | as #19 |
| 28 | 2026-10-19 19:35 | hecate 6e3d387 (version 25 plus fuel round 3 and its out-of-fuel gates, without the two stunned-turn commits). Scrims vs the top 5, same maps: 30-45 (v25 31-44, v27 26-49, v26 24-51); 8 games differ from v27, 6 of them wins | as #19 |
| 29 | 2026-10-19 19:42 | hecate d72c1c2 (version 26 with the stunned-turn skip reverted: a stunned turn runs the whole turn, only the refused recall is skipped). Scrims vs the top 5, same maps: 29-46 (v28 30-45, v25 31-44, v26 24-51); 9 games differ from v28, 4-5 | as #26 |

Add a row with each new submission.
