# Hooks HoR43–47: camp exit or avoidable reversal?

2026-10-23. Existing own-view/events and frozen a00fff source only; no engine, export, script or implementation. **A route/branch bug is not established.** The strongest specific hypothesis is a camp-exit decision that trades northern Elk exposure for southern enemy reach. Resolve that one branch before changing pursuit or support policy.

Evidence: `replays/Khaos_v32-live-UR/policy-wonk/actor-windows/hooks-pantheon-hor3-a-r41-49.json`, SHA `673709c43eece23990763e92194b2a126bb6432d5829a65f89cef6d617a3aaae`; events under `analysis/a44be2fd40507089/events.jsonl.gz`. Replay payload `a44be2fd4050708990181a905b2a4e02c42e3ad86bf4e6e941b47e02c5483436`. Public deployed source is unverified; a00fff is a source-contract comparison, not recovered execution.

## Known sequence

| Own turn | Start / HP | Actual movement | Known constraints |
| --- | --- | --- | --- |
|43|18,19 /506|18,18 after basic|Four enemy identities/positions visible; shield5/dash6.|
|44|18,18 /451|18,17|Awake Elk15,13 now visible; shield4/dash5.|
|45|18,17 /396|18,16|Northern Elk1270HP; Vesper17,20 has ready reset/dash.|
|46|18,16 /396|Cancel fresh recall,18,17|Northern Elk1100HP; shield2/dash3. Enemy M15,19, V17,20, Tavi14,20, W17,21.|
|47|18,17 /341|18,18|Northern Elk1010HP; shield1/dash2. Same four enemies visible.|

No allied champion is visible in these own turns. Elk15,17 remains visibly asleep. The eastern wall atx19 blocks immediate eastward alternatives; north18,15 is not a listed wall/hole but remains within the northern Elk's range4. Tile18,16 is distance3 from that awake Elk,18,17 distance4,18,18 distance5: the observed southern steps are an actual exit from that threat radius. This does not certify the best route; native movement and internal camp/route beliefs are absent.

The harmful consequences are explicit. Vesper's55 basic at step5505 follows the46 move and cancels recall. After47's step5605, Vesper55 at5637 and Willow55 at5680 hit HoR. Enemy Marcella then moves adjacent and deals45 twice at5730/5732 before HoR's48 turn, with the second basic stunning him. The48 no-action turn is not idling. Her stun, rather than a guessed final dash motive, explains this immediate lost action. Opponent Willow's next heal is actually48 to Vesper; it was cooldown2 in HoR's46 view and1 in47, not an already-ready heal at46.

## Source-compatible explanation and missing witness

[want_home](/Users/yufan/Desktop/Development/CambridgeBattlecode2026/willow-upstream-development/bots/variants/willow-audit107-ready-heal-work/src/bot.cpp:2824) checks low health, pack danger, camp entrapment and simulated standing.396HP is above the350 low-health threshold;341 is below, subject to finishing/holding exceptions. Neither value alone identifies the branch. [decide](/Users/yufan/Desktop/Development/CambridgeBattlecode2026/willow-upstream-development/bots/variants/willow-audit107-ready-heal-work/src/bot.cpp:5055) retreats on `leave` before ordinary strike/chase/farm selection. HoR's43 attack therefore does not prove pursuit: retreat itself may attack before walking.

[retreat](/Users/yufan/Desktop/Development/CambridgeBattlecode2026/willow-upstream-development/bots/variants/willow-audit107-ready-heal-work/src/bot.cpp:4147) tries [flee_camps](/Users/yufan/Desktop/Development/CambridgeBattlecode2026/willow-upstream-development/bots/variants/willow-audit107-ready-heal-work/src/bot.cpp:298) before homeward retreat. That helper adds estimated remaining camp hits to immediate `damage_bound`, prefers lower cost, and uses home distance for ties. Its exit-distance estimate uses nearby camp-free tiles, not a complete safe path. The northern Elk and wall make a southward exit plausible even while enemies are south. `retreat_step` instead restricts its ranked neighbors to nonincreasing home distance and can fall back to routing. Existing Safety camp reach also depends on visible closer actors, next order and potential wakes; raw60×distance arithmetic is not its executed score.

There are two precise source omissions to test, rather than a generic proposal to add enemy risk that already exists. First, `any_within(exits,p,r)` can count a camp-free tile through the eastern wall without proving a connected walk; for examplex20 lies beyond the northern Elk's radius whilex19 is blocked. Whether that tile is in the actual combined exit mask is part of the missing witness. Second, remaining **camp** phases are accumulated, but enemy risk along the subsequent exit steps is not: a step toward18,18 can enter Willow's current three-tile basic radius and shorten Marcella's later approach even if the first step's bound looks tolerable. Neither omission proves the observed choice wrong:18,18 is a real exit from the northern Elk, and north remains camp-exposed. A repair is warranted only if the exact chosen branch/cost demonstrates that the omitted route or later enemy exposure changed the ranking against a viable alternative.

The smallest missing witness is **one r46 decision snapshot**: source identity, `continue_recall`/`leave` result, final decision branch, whether `flee_camps` succeeded, current camp damage and `walk_out`, and the current/north/south candidate legality, home distance, immediate enemy/camp bound and total exit cost. Include other neighbors only if they beat those nominees or explain failed movement. If fallback routing owns the move, record its rejected options and chosen home-field step instead. This distinguishes an intentional least-bad exit from a ranking/route defect. Only inspect47 if46 leaves the cause unresolved. Do not prescribe a northward move without its legal route and known survival cost; the globally observed allies tanking the northern Elk are hidden to HoR here.

## What Willow changes—and does not

There is no visible allied ready healer in this record. Adding360 hypothetical HP could increase affordable escape time but does not remove walls, enemy reach or camp risk, and it is not actual knowledge. More importantly, the proposed fixed four-pick P/V/M/W arm **replaces this HoR**, so healing the same HoR in the same snapshot silently adds a fifth role. These losses motivate measuring service and frontline availability; they do not prove a Willow rescue or identify a draft cause.

Keep draft testing separate. For this specific failure, the actionable next step is the bounded branch witness above if an exact-source reproduction is later authorized; no new gameplay correction is justified from these artifacts alone.
