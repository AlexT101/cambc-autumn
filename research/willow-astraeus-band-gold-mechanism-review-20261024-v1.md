# Astraeus Band route and Gold terminal: seven-game mechanism review

2026-10-24 UTC. Read-only review of the seven existing native extractions and the exact reused old-4db Band control; no new execution, decoding, helper implementation, or gameplay edits. Cambridge Battlecode rules apply. **Band has demonstrated useful work after the route correction and is ready for a broader paired check. Gold has demonstrated an earlier completed capture on A and a disrupted but abandoned capture on B; inspect that abandonment before promoting or adding hold policy.** Neither conclusion is a strength claim from this small sample.

## Evidence and identity

Run root: `replays/willow-astraeus-mechanism-band-gold-20261024-v1/`. `run-preflight-receipt.json` and `seven-game-preflight.json` pin the sources/builds/maps; `analysis-v1/index.json` resolves the replay-hash directories. Each contains `meta.json`, `events.jsonl.gz`, and `rounds.json.gz`. All seven report validation OK with zero hard/soft notes. This is extraction validation, not absence of fuel faults.

Both sides use ordered Prism, Vesper, Heart of Ruin drafts (`[5,1,11]`); A actors are 0/1/2 and B actors 3/4/5. Opponent is v33 `a00fff454c1e48520968c9ba2d4c1ecdae0212ce019724dc06a6e959ddc3412e`. Public Fish source remains unknown and its different roster is not a source-known fixture for these games.

| Cell / replay SHA prefix | Candidate side | Result / rounds | Final gems A,B |
|---|---|---|---|
| cb61 base Band / `6b0d97f5d5441295` | A | loss / 939 | 236,1013 |
| cb61 Band patch / `6446e7117719efaa` | A | loss / 928 | 429,1013 |
| old4db Band patch / `9e0fadaa08e00abc` | A | loss / 928 | 429,1013 |
| cb61 base Gold / `9671f4818af50bae` | A | loss / 2000 | 704,913 |
| cb61 base Gold / `4177b44bd51c2c56` | B | win / 1707 | 280,1007 |
| cb61 Gold v2 / `c6337390a621c6c2` | A | win / 1439 | 1001,176 |
| cb61 Gold v2 / `9acf1504d69f20e9` | B | loss / 1830 | 1001,363 |

Source aggregates: cb61 base `369742e3f54259c675c0d4b508a02c0c4517eef6e1cb3ef6f42fa776194180ea`; cb61 Band `2a475721c8985cfcbd189e683ffac90ac05cdbf06280289899d21d9be851204e`; old4db Band `0620e6589ba0c1ff908d94538c525b517ed5d8ee3a443e9fe26a9ccc5449a724`; Gold v2 `692b6ffe52ea70f9aef3e82609b7133548be295d0eff4cd238a7a5a43ea38fe2`. Full replay SHA and metrics are in `analysis-v1/mechanism-summary.json` (SHA256 `2751737428535e736dbc59148770602f184f697aab3b3eabca871af07afda579`). Normalized action comparison and reciprocal-move nominations: `analysis-v1/gold-paired-event-comparison.json` (SHA256 `bb8d168023a94c8e440d6f71db9536dbfa4d3dbca1bfee89e05be8dfb48eec4f`). Absolute step ordinal is excluded when comparing paired actions.

## Band: route change leads to farming and banked gems

First cb61 route divergence is HoR2 r13/t0 from `(8,30)`: base walks to `(9,30)`, patch to `(7,30)`. The patch takes the detour before entering the old pocket: r14 `(6,29)`, r15 `(6,28)`, r18 `(8,25)`, r19 `(9,24)`, r20 dash `(11,24)` then walk `(12,24)`. Base instead oscillates around `(11,31)↔(11,32)` after r19, with interrupted recalls. Merely crossing the spawn boundary is not the successful mechanism; all arms did that earlier.

The patch routes while the blocking wolf remains alive: native camp100 at `(13,33)` has 1295 HP at r19 and 1130 at r22; Vesper1 clears it only at r41. Its expanded extractor group is **62**, distinct from group numbering in earlier C++ evidence. HoR2 begins actual camp damage at r37 (camp4), then works other camps. Its first attributed group clear is g30 r130, capture r136 gives 28 gems, and tribute r141 banks those 28. This is productive route recovery, not just a different idle location.

| HoR2 whole-match production | Monster damage | Earned gold | Collected / submitted gems |
|---|---:|---:|---:|
| cb61 base | 0 | 0 | 0 / 0 |
| old4db unpatched reused control | 0 | 0 | 0 / 0 |
| cb61 Band patch | 12,416.8 | 664 | 200 / 200 |
| old4db Band patch | 12,416.8 | 664 | 200 / 200 |

Reused old4db control replay SHA `cdbd5b2619aa504fcaf8ede78ac48ca8d0a85cdda4dad436a75f28c25b879ac7`, in `replays/willow-hyperion4db-vs-v33-a00fff-full1104-native-audit-v1/cdbd5b2619aa504f/`, lost at965 with189/1000. The two patched lineages share the early route and these totals, but their events are not identical (recall/action ordering diverges at r53). The patch loses eleven rounds earlier than cb61 base despite greater production; duration is not a success proxy. Prior source review found no new blocker. Next: broader fixed-map, side-paired validation of the same narrow overlay, retaining both production and runtime/fuel checks.

## Gold A: ordinary damaging endpoint changes, then a real payout

First candidate action difference is HoR2 r14/t3, starting `(15,13)`: base walks `(16,12)` and dashes `(18,14)`; v2 walks `(16,14)` and dashes `(18,15)`. Both deal150 dash plus30 basic damage to enemy HoR5. The v2 dash additionally kills camp5 for120 damage and ends on the already-cleared g8 Gold tile. Enemy HoR5 had cleared that tile's camp15 at r14/t0.

V2 starts g8 hold at r15, remains on `(18,15)` through r19, and receives20 gold at r20 before leaving. Candidate's first completed capture is r20 versus base r31. This validates useful occupancy and uninterrupted payout. It does **not** identify the extra no-strike `economic_moves()` terminal: `Search::offer` adds occupancy credit to ordinary damaging leaves too, and this first divergent combo does damage. Release builds omit `GOLDTERM`, so no hidden terminal activation is proved.

Exact pre-action eligibility check: `analysis-v1/maps/32d3738f8ee828ea.json` defines g8 as **only camp15 at `(18,15)`**, gold20/gems0. At r14/t0/s1611, enemy HoR5 kills that camp and emits `group_clear g8`, before our r14/t3/s1647 walk and s1648 dash. Camp5 killed by our dash belongs to **g2**, at `(17,16)`; it does not create the g8 clearance. Our turn-start position `(15,13)` is Chebyshev distance3 from g8. Neither endpoint nor any tile in the enclosing x15–18/y13–15 rectangle is a wall or bush, so the radius8 shadowcasting rules make g8 visible from that start position. Thus native clearance and static sight satisfy the necessary eligibility conditions before the search. This geometric visibility check is not a logged `World` read: `read_economics` still requires the current state round, consistent occupants/holder and a positive quote, whose actual evaluated values are absent from the release evidence.

## Gold B: useful disruption, but continuation remains unresolved

Candidate accepted actions match through r24. Own HoR5 clears g2 at r24. At r25/t3 base Vesper4 attacks enemy HoR2 from `(18,19)` for55; v2 dashes to g2 tile `(16,17)` and makes the same55-damage attack. At the time of the dash, enemy Vesper1 had already dashed/walked away `(17,15)→(15,13)→(14,12)` at t2. Own HoR5 is nearby `(18,15)`, though damaged; own Prism3 is remote near `(10,19)`. The immediate choice is plausible: preserve the hit and occupy a cleared camp while a nearby enemy withdraws. It also spends an eight-turn dash cycle; Vesper cannot assume that exit option is available throughout the six-round capture.

| Opening g2 sequence | Base B | Gold v2 B |
|---|---|---|
| First hold | enemy at26 | ours at26 |
| Our continuity | no opening hold | hold26–29; within-group move28 preserves progress |
| Departure | — | r30 `(17,18)→(18,19)`, progress lost |
| First payout | enemy HoR2 r31,100 gold | enemy Vesper1 r39,133 gold |

The v2 opening delays the enemy payout eight rounds, but yields **zero own opening payout**. Recipient and item scaling differ, so these are not equal100-gold payouts merely shifted in time. First own capture elsewhere occurs r49 versus base r153. Do not attribute the B match loss to the local dash or treat interrupted occupancy as a realized capture.

Vesper4 stays at680.4HP throughout r24–31. It cancels recall with3 turns left at both r28 and r30, moves, then restarts. At r30 before its t2 movement, own Prism3 has moved farther away and enemy Prism0 attacks a camp; there is no intervening hit on Vesper or new enemy movement at that round's earlier turns. Enemy Prism was already in Vesper's recorded visible set by r27. At the prior round boundary, enemy HoR2 is `(17,14)`, enemy Vesper1 `(17,13)`, enemy Prism0 `(20,13)`, compared with Vesper4 `(17,18)`; nearest distance4. Own HoR5 is `(22,17)`, distance5, moving outward on its subsequent turns. These known-position candidates support pursuit/weakening support more than a sudden unseen attacker. They do not prove the precise predecision SDK view, current belief, or safety branch. Cooldowns and turn order continue changing despite constant HP.

The source makes a simple “pack veto sent it home” claim premature. In canonical `bot.cpp:2810–2820`, `paying_soon` protects a recognized held capture if nearest recent enemy distance exceeds3 and believed payout is within2 rounds. A correct g2 hold and payout31 should satisfy that geometric test at r30. `want_home` can still return true for lethal/camp/stand evaluation; alternatively the hold/payout belief or branch may differ. `continue_recall` (`4151–4176`) can cancel for safety/timing, but cancellation itself does not require leaving. `hold_capture` (`4243`) does not walk. The release events cannot choose among these explanations.

Smallest next diagnostic, if authorized: Gold-v2 B actor4 **r29–30**, plus the r25 quoted endpoint record only if needed. Capture actual evaluated `holding_capture`, group id/state/holder/occupants/held_since/payout, `paying_soon` nearest enemy and result, ordered `want_home` reason, `lethal/pursued/linked/stand` results when reached, recall keep/cancel reason, and actual dispatch to retreat/hold/search/other move. Preserve short-circuit behavior; never compute all predicates just to log them. Confirm actor-known camp tiles and native current occupancy against World belief. A recognized hold, paying_soon=true and leave=false falsifies the home-retreat account; a wrong hold/payout directs attention to belief continuity; correct beliefs plus a reached safety loss supports continuation-risk pricing.

Gold v2 `plan.cpp:421` currently credits eligible occupancy as gold times capture/denial value according to surviving endpoint enemy occupants. `bot.cpp:4954` quotes via `rate(per_gold, capture_rounds())`; it does not estimate survival of all six holding rounds. Existing `rate`/farm cycles (`bot.cpp:879,2360`) already provide time discount, and `Safety::approach` (`safety.cpp:1951`) offers a bounded current-enemy reach estimate. Reuse those concepts only after identifying the departure: discount prospective capture by hold/exit cost and retain separately justified denial value. The carrier-altar `intercept_steps` helper is a different problem and must not be transplanted as a camp-arrival oracle. Prefer a bounded valuation correction over forced engagement, permanent holding, or a new blanket capture veto.

## Source-known zero-bag reversal for the existing v5 diagnostic

Use the **canonical cb61 Gold B control**, actor4, r41–42, with r40/43 as context. Positions are r40 `(25,17)`, r41 `(24,18)`, r42 `(25,17)`, r43 `(24,18)`. HP1000 and bag0 throughout; each move is followed only by recall start and next-turn manual cancellation, with no intervening accepted productive action by Vesper. Recorded visible enemy IDs are0/1 at all four boundaries. Dash cooldown goes2→1→0→0 and reset1→0→0→0, so this is an observed reversal, not proof of identical decision inputs. It is a cleaner baseline fixture than v2 A r38–39, which begins with a dash before the reciprocal walk.

This satisfies the source-known nomination gate in `research/fish-goldrush-diagnostic-spec-20261024-v5.md`. Apply its two-turn branch specification only after a bounded actor-known view confirms the local enemy/camp/support state; the current summaries nominate the fixture but do not prove a farm→retreat branch. The public Fish r22→23 remains a separate unknown-source observation.

## Minimal initial logging handoff

Luna owns any later diagnostic implementation; this is a specification, not a request to run or modify gameplay now. Use two separately pinned diagnostic copies and exact selectors: **base B Vesper4 r41–43**, and **Gold-v2 B Vesper4 r29–30**. Retain replay/source/build identity in the receipt. Do not initially add the full v5 roster or geometry dump.

| Record | Smallest hook and fields |
|---|---|
| `HOME` | `want_home` returns, canonical `bot.cpp:2849–2868`: round/actor/current native position, called from `continue_recall` or main dispatch, boolean result and first actual terminal reason. Preserve ordered evaluation of `low`, `outmatched`, `camp_trapped`; record only predicates actually reached. For the stand return include the already-computed `lethal`, `pursued`, `linked`, `t.lost`, `t.self_falls`. |
| `RECALL` | Existing decision in `continue_recall`, `4151–4176`: initial channel timer; keep reason or cancellation; whether cached `home` was used later. Do not interpret a cancel event as a retreat. |
| `PATH` | Immediately at actual main dispatch calls (`leave→retreat`, `support_retreat→retreat`, `holding→hold_capture`, or ordinary `farm` near the function end): caller tag, decision start position, `memory.farm_group/claim/banking`, and position after the called action. For an intermediate successful search move, tag that actual call separately so the start/end are not mistaken for the subsequent farm move. Endpoint records use executed positions rather than a fresh path search. Base fixture needs this plus `HOME/RECALL` first; no map-wide masks. |
| `HOLD` (Gold v2 only) | At existing calls to `holding_capture` and `paying_soon` (`1494`, `2810`), with call context: already-read group id/state/holder/held_since/payout; holding result and short-circuit reason; if reached, already-computed nearest recent enemy distance and payout test. Record current native position and World position to detect a post-move belief mismatch. In `continue_recall`, record the returned `capture_recall` result when it was actually called. Do not call these helpers a second time to populate the log. |

If `PATH` shows farm on the outbound turn and home→retreat on the return, inspect the recorded home reason before adding any geometry. If both calls are farm, the original pack-return account is falsified and the next bounded record is selected group/route target at the two existing farm selections. If both are retreat, inspect that local retreat choice instead. For Gold, a correctly recognized payable hold plus `leave=false` directs the investigation to the actual movement caller; a false hold or late believed payout directs it to local camp belief; `leave=true` with correct hold requires its recorded safety reason. Only a missing discriminating value justifies a second logging pass. No force-hold, new veto, or automatic gameplay correction follows from these nominations.

## Decision and runtime boundary

Proceed with broader paired Band validation when the coordinator allocates the single heavy worker. Keep Gold v2 as an experimental candidate and resolve its B capture-continuation decision before revising economics. Prefer the two small diagnostic fixtures above over another broad public scan. Do not combine unrelated grouping or pursuit changes with either patch.

First round-end candidate fuel status6 appears on Gold A at499 in base and108 in v2; on Gold B at22 in both, before the r25 first action divergence. These observations must remain separate from extraction validation and from causal attribution. The seven outcomes are a mechanism check, not evidence for a Gold strength improvement or a clean fuel bill. No further execution or instrumentation is authorized by this report.

## Follow-up: exact actor-view caveat, 2026-10-24

The existing source-known exports `replays/willow-astraeus-route-gold-ownview-v1-20261024/gold-v2-b-v33.json` (SHA256 `58a64db8875ee2d3fd7daac819a5f9c064089a7f964ed6d6696315d7edfd0d5d`) and `base-gold-b-v33.json` (`a908ac67bad8c92f14820b5dcb80aa655240470d1b9a4d40e8eace8d77f8ded1`) now provide first phase-10 observations, rather than reconstructed round-boundary context.

In Gold v2 B, Vesper4 begins both r29 and r30 at `(17,18)` with680.4001HP. Enemy HoR2 is visible at `(16,14)` then `(17,14)` and its **dash cooldown changes1→0**. Own visible HoR5 moves `(21,18)→(22,17)`, distance4→5, with397.36HP; own Prism3 is identity-only in both actor views. Vesper's own dash remains unavailable (4→3); enemy Prism0 and Vesper1 remain visible at `(20,13)` and `(17,13)`. Thus no incoming hit and unchanged self HP do **not** imply unchanged danger. The newly ready enemy dash and weaker nearby support can make departure reasonable. They also mean a geometric `paying_soon` check alone cannot settle the reached safety decision. Actual `want_home`/stand/dispatch tracing remains pending; no hold-policy correction is established.

The baseline export independently confirms r41 `(25,17)→(24,18)`, r42 back to `(25,17)`, r43 back to `(24,18)`, with1000HP/zero bag at every turn start. Exact turn-start reset/dash cooldowns are `[1,2]`, `[0,1]`, `[0,0]`, respectively; do not substitute the earlier round-end arrays for these readiness observations. This remains the separate farm/retreat diagnostic, not proof that the Gold capture abandonment is the same mechanism.
