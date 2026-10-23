# Fish Gold Rush: source hypotheses from Vesper's known view

2026-10-24 UTC. The strongest current-source hypothesis is a **pack-retreat / empty-bag farm reentry mismatch, amplified by a five-tile ally cutoff**. The visible geometry fits both oscillations precisely. This is a testable explanation for canonical Astraeus, not proof that Astraeus ran in the public match, and not evidence of opponent adaptation.

Read the Cambridge Battlecode rules. This is file-only analysis of all fifteen exported turns, existing exporter semantics, and `bots/baselines/astraeus-cb61eaa/src/`. No engine, build, helper, script, new window or gameplay change. `bots/astraeus/src/bot.cpp` and `params.h` compare byte-identical to that baseline at review time. Existing v3 evidence and hashes remain untouched.

## Evidence pins and limits

Match `58a8288d-a729-4106-81ed-6dfbf76c190c`, our A/Vesper1, rounds10–24; our draft `[5,1,11]`, Fish `[1,11,2]`. JSON: `replays/incoming-loss-followup-20261024-v3/metadata/public-source-unverified-goldrush-10-24-v1/actor-windows-v1/goldrush-actor1-r10-24.json`, SHA `f21674a4f514062d66c0a97cbec30339d29530c2d3d180cf0271ff4323e00b48`. Receipt SHA `e2e4aba6fa9e3da139fd62227bea2ddd90ff0efcdc7a72f798880bde65623355`. Replay SHA `47970b1c959f77498dafd325b8bc2a272252ac39f35fc9045e3febd2e4a7a29b`; map SHA `6e564fdf09fdf67a4182a909d6985737b488742e64f2c3e164204e78bc64c898`. Source/submission/build identity remains unknown.

Frozen source aggregate `369742e3f54259c675c0d4b508a02c0c4517eef6e1cb3ef6f42fa776194180ea`. Reviewed file SHAs: bot.cpp `3bef17ba3c88fe30d147fd9d2ce99881a05515f2940e6f4b251d4b9b3d8803d5`; params.h `cae05ef905e7564822190fac5563833c81cce906ec46e03e4c5687427bb7475e`; safety.cpp `07f6c2ca8e2f165fcb5e02c0998f818fc4a3ebb2ad33180f7fbda43d3df9c123`; self_abilities.cpp `a3f3c6e52a15644433b20a07db801e4063d9bc9254077d3d2eb4597b27dda2ec`.

Positions below are physical A coordinates, distance is Chebyshev. Native movement readiness, per-enemy acted flags/priority, failed attempts, shared claims and C++ beliefs are absent. Initial attack-ready=false occurs while recall is active; it cannot establish post-cancel attack illegality. A camp row marked `static_map_only` does not establish death, cleared group, holder or safe capture.

## What Vesper knows across the opening

Vesper stays1000HP,55Strength,100Focus,0gems,0gold with no items/buffs throughout. All visible allies/enemies likewise remain at their initial full HP and without items/buffs. Every own turn cancels a timer4 recall, acts, then restarts recall. Astraeus explicitly starts recall at ordinary turn end (`bot.cpp:4995`, call5068), so that pattern alone is not a defect.

| Rounds | Our Vesper / actual work | Visible ally support | Visible Fish formation and readiness |
|---|---|---|---|
|10–12|`(12,9)` basics/reset10, basic11, move to `(13,10)`12|Prism `(10,8)→(11,7)→(12,7)`; HoR `(10,12)→(9,12)→(10,13)`. Both slots0 throughout.|All enemies identity-only; no enemy position inference.|
|13–14|`(13,10)`, one basic each|Prism `(13,7)→(14,7)`, HoR `(9,12)→(10,13)`; all within4, both slots0.|Vesper `(16,16)` reset5→4/dash0; HoR `(15,18)` shield0/dash6→4; Vendetta `(16,17)` both0. Three bodies within a two-tile square.|
|15–17|Same tile, basics; own dash2→1→0|Prism `(15,7)→(16,7)→(17,7)` stays within4, both0. HoR `(7,14)→(8,14)→(7,14)` is6/5/6 away; dash7/6/5.|Vesper still `(16,16)`, reset3/2/1, dash0. HoR `(15,18)`, dash4/2/2. Vendetta `(16,17)→(16,17)→(15,17)`, both0.|
|18–19|Same tile, basic/reset/basic18, basic19|Prism `(18,7)→(19,7)` distance5→6; HoR `(8,14)→(7,14)` distance5→6, dash4→3.|Vesper `(16,16)→(15,17)`, both0. Vendetta `(14,18)→(13,18)`, both0. HoR identity-only: do not place it from omniscience.|
|20|`(13,10)→(13,11)`|Prism `(20,8)` distance7, both0. HoR `(8,13)` distance5, shield0/dash2.|Vesper `(14,17)`, Vendetta `(13,18)`, both0; HoR identity-only.|
|21|`(13,11)→(12,10)`|Prism identity-only. HoR `(7,14)` distance6, shield0/dash1.|Same visible Vesper/Vendetta positions, both0; HoR identity-only.|
|22|`(12,10)→(13,11)`|Prism identity-only. HoR `(7,15)` distance5, both0.|Vesper `(14,17)`, HoR `(12,17)`, Vendetta `(13,18)`, all slots0; three bodies again within two tiles.|
|23|`(13,11)→(12,10)`|Prism identity-only. HoR `(7,16)` distance6, both0.|Same visible enemy positions and readiness as22.|
|24|Dash `(12,10)→(10,8)`, walk `(9,8)`|Prism `(20,11)` distance8, both0; HoR identity-only.|Vesper `(14,17)` reset7/dash0; HoR `(13,15)` shield0/dash7; Vendetta `(13,18)` both0. HoR is now only5 away at turn start.|

Thus the enemy formation is observably compact when all three are visible; the same is not true of our team at20–24. This establishes local force separation, not why either teammate chose its route. Our HoR shield is self-only. Its dash is unavailable21, then ready22–23 but still6/5 tiles from Vesper and much farther from Fish. Prism's ready CC cannot hit enemies remotely from `(20,8)`20, and its position is not known21–23. Neither ally is certified able to provide immediate cover or safely follow. A different earlier assignment/rendezvous is plausible, but mandatory grouping would abandon other work whose value this perspective does not reveal.

Group1's observed HP reductions accompany basics13–19; exact attack targets are not exported. Camp4 `(13,14)` remains visibly120HP20–23. At21/23 it is within basic range3, but three55-damage basics would be needed absent other damage, and the first ranged basic spends that turn's walk. At24 it becomes static-only. There is no witnessed completed group1 capture to defend or contest in this interval.

## Ranked source hypotheses

### 1. Pack threshold and reentry: strongest geometric match

`pack_boxes` (`bot.cpp:2641`) includes visible allies within `pack_ally_radius=5`, plus self, and enemies seen this round or last outside their spawn exclusion. A subset is dangerous when its summed health times summed average output exceeds our side's product times a ratio. `Strike::max_reach=6` makes the pack radius7 (`bot.cpp:2607`). On own ground the healthy ratio is2; on enemy ground it is100 (`params.h:50–55`). `want_home` calls `outmatched` before the detailed fight test (`bot.cpp:2855`). Full HP does not exempt a champion from the own-ground ratio.

The Vesper/Vendetta pair at `(14,17)`/`(13,18)` is distances6/7 from `(13,11)` and7/8 from `(12,10)`: one tile crosses the intersection of both radius7 squares. At20/22 our HoR is within5; at21/23 it is at6. Prism contributes to neither retreat-turn pack sum. This explains why the unchanged1000HP is not the deciding variable.

Conditional arithmetic under the exact current-source own-ground classification: `raw_output` amortizes spells over8 turns (`bot.cpp:848`), yielding Vesper61.875, Vendetta78.75, HoR48.75 at these stats. Solo Vesper's threshold is `2×1000×61.875=123750`; the Fish pair scores `2000×140.625=281250`, so it outmatches solo Vesper. Adding our full-HP HoR raises our threshold to `2×2000×110.625=442500`, above every enemy pair. All three enemies score568125, but their common radius7 box excludes `(12,10)` because Vendetta is8 away. This predicts the observed approach/retreat pattern if `own_ground`, enemy inclusion and beliefs match. Native spawn-distance fields and those actual internal predicates have not been evaluated here; do not silently assume them. On enemy ground at ratio100 this explanation would fail.

The code explicitly permits the reverse step: farm uses `bag_at_stake>0 ? pack_zone : nullptr` (`bot.cpp:1902–1906`). Its comment says empty-handed entry keeps the champion nearby because the zone starts beyond strike reach. Vesper's observed bag is0 throughout. The immediate-threat `step_guard` tests exposure/fight outcomes, not this broad pack policy (`bot.cpp:2891–3077`); it can admit a tile that next turn's pack test rejects. Ally strength is also computed around the current anchor, not every prospective endpoint. These are real source seams even though the public branch is unknown. The desired improvement would be productive staging or another objective when reentry cannot produce work, not weakening retreat or compelling an attack.

### 2. Turn-order-dependent immediate threat: plausible secondary discriminator

Vesper's recorded turn index alternates3 on even rounds and2 on odd rounds, consistent with being the second own actor as team-first order alternates. This does not reveal every enemy's priority/acted state. `turns_before_ours` and `threat_strike` (`safety.cpp:805,837`) can widen a threat when an enemy gets two turns before ours. The pair's positions/cooldowns do not change20–23, but phase/ally visibility do; native timing must be included before calling the states identical.

The pack explanation does not require actual incoming damage. At24 HoR closes to `(13,15)`, and actual dash use is consistent with `dash_away` requiring positive immediate danger (`self_abilities.cpp:397–409`), unlike21/23 when a normal retreat step suffices. This is consistency, not proof of that call site. Record `turns_before_ours`, exact reach/blow, `Safety::stand` outcome and `want_home` reason to distinguish this from hypothesis1. Recall cancellation also fits `recall_outruns` rejecting a four-turn channel while enemies can approach (`bot.cpp:3328,4152`); no recall bug is established.

### 3. Farm choice/coordination or camp wall: lower priority for this particular edge

No observed blocker prevents either direction of `(12,10)↔(13,11)`; both moves repeatedly succeed and the two endpoints are not camp tiles. This weakens a direct live-camp-wall explanation for the oscillating edge. A stale field, changing farm group/claim, rejected attempt before the successful move, or another decision branch could still route away. If the reverse move comes from `retreat` before `farm`, Band's remembered-camp routing overlay cannot address that cause. Conversely, if `want_home=false` and both directions come from farm, inspect approach-field distances, occupancy/guard bits, claims and selected group before touching danger thresholds.

Known alternate work exists, but **a safe alternate capture is not certified**. Gold camp13/group6 `(15,12)` is visible120HP and asleep at21–23; it is distance2 from `(13,11)` and3 from `(12,10)`. It offers a geometrically reachable harmless-camp basic, not immediate payout. It still needs multiple hits, legal readiness, subsequent occupation and hold time, and the export does not certify complete group state or safe arrival/holding. Current farm's passing-hit filter excludes non-selected pure-gold groups for Vesper (`bot.cpp:1769–1776`), though the main objective evaluation can choose gold (`2178` onward). At retreat turns farm may never be reached. Other visible gold tiles farther toward the enemy are not automatically better; group0 includes the20000HP monolith. No current-view safe cleared group can be claimed from static-only rows.

## Smallest decisive diagnostic

No additional public window is critical. For a source-known occurrence on the frozen canonical build, instrument or inspect **two consecutive decisions corresponding to22→23**, retaining the20→21 repetition as confirmation only if needed. Public actions2446–2448 and2547–2549 delimit the observed cancel/move/recall sequences, but substituting a current binary into a source-unknown public replay is not provenance.

At the existing `continue_recall→want_home` seam, capture one compact record: branch/reason (`low`, `outmatched`, `camp_trapped`, detailed `stand`); own-ground spawn distances, bag and pack threshold; included ally/enemy masks/positions and the triggering pack box; `recall_outruns`; enemy acted/next-slot/reach. At the chosen move, capture caller (`retreat`, farm, chase, other), farm group/claim, whether zone/guard applied, endpoint membership and field distances, and any native rejection/reveal before success. Existing final decision `R` versus `F` narrows the question but does not identify the specific retreat predicate.

Prediction: if farm22 admits `(13,11)` without a pack zone, then23 exits through `outmatched` with HoR excluded at distance6, hypothesis1 is supported. If `outmatched=false` and detailed stand loses only because of temporal reach, hypothesis2 wins. If home=false and pathing chooses both directions, inspect hypothesis3. The candidate intervention must preserve safe retreat and demonstrate useful attack/clear/occupation or productive alternate work; merely replacing oscillation with permanent waiting is not success. This analysis authorizes no new execution or patch.
