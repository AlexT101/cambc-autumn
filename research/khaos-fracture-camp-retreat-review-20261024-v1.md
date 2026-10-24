# Fracture: failed camp conversion and a bounded retreat diagnostic

2026-10-24. Read-only review of normal-draft match `6431a334-0746-4bac-b46d-847637121163`, our physical B versus Claudus Maximus A. No new runtime or source change. Willow-first ladder manipulation is excluded. Metadata timing does not identify the uploaded binary; Fracture has not been source-reproduced. The earlier matched map/opponent/side sample was also a loss. This is not evidence that release 48 introduced the mechanism below.

## What the score gap means

B captured 493 and banked 317; Prism5 retained all 176 remaining gems and survived. A captured 1,130, banked 1,025, and retained 105. Thus the 708 score gap is `637 capture gap + 176 B carry - 105 A carry`; there were no B gem death drops. The A ending bags are Tavi3 61 and Marcella4 44, correcting the compact report's attribution of all 105 to Marcella. Native audit found no errors or rollovers on either side.

A's 1,130 includes the 200-gem Monolith group21 payout to Vendetta2 at r773. Ordinary capture income is therefore A930 versus B493, a 437 gap. This does not justify restarting the boss experiment: repeated ordinary conversion already explains much of the deficit.

| Group and public layout | Observed conversion |
| --- | --- |
| g11, 22 gems, own right edge | Prism5 captures r113/254/379/489/572/674/743/849: 176 total. A productive loop, not evidence of being stuck. |
| g12/g13 mirror pair, 30 gems each | A g12 six payouts (180); B g13 r52/623/807 (90). B has a 571-round first-to-second payout gap. |
| g15, 59 gems | A r430/541/654/800 (236); mirror g14 never pays. |
| g22/g23 mirror pair, 44 gems each | A g22 five payouts (220). B attempts g23 unsuccessfully near r469–480; A Vendetta gets g23 at575, B Vesper only at762. |

Banking Prism's 176 would not by itself win: all B captured gems total493. The better nomination is lost work/uptime during a concrete ordinary-camp attempt.

## Exact failed attempt, raw physical coordinates

Own Vesper6 is ranged, maxHP1200, carrying zero gems. Camps33 at(34,41) and37 at(35,41) are the two range4 Elks of group23; its other members are camps35/66/68. Group23 is worth44 gems/200 base gold. Vesper attacks camp33 for135 at r469–471, twice at472 using Attack reset, and once at473. No team healing or immediate supporting worker accompanies the following escape sequence.

| Round | HP after that round's camp phase | Accepted Vesper actions relevant here |
| --- | ---: | --- |
| 472 | 612 | Basic, reset slot0, basic; remains(34,43). |
| 473 | 528 | Basic camp33; remains(34,43). |
| 474 | 444 | Move(34,43)→(35,43). |
| 475 | 360 | Move→(36,43). |
| 476 | 276 | Move→(37,43). |
| 477 | 192 | Dash slot1→(39,42), then ordinary move→(38,42). |
| 478 | 108 | Move(38,42)→(39,42). |
| 479 | 66 | Move(39,42)→(38,42). |
| 480 | 0 | Camp33 hits42, then37 hits the remaining24 and kills Vesper. |

Both Elks deal42 each phase through478. Only camp37 reaches(39,42), dealing42 at479; both reach(38,42). Exact terminal event is step97771. These are camp attacks, not hidden enemy champion damage. Recall starts after each activation and camp damage cancels the timer4 stub next phase; that cadence is not itself a retreat bug.

The apparent escape tile is a pocket. At(39,42), north(39,41), northeast(40,41), east(40,42), southeast(40,43), and south(39,43) are holes. Westward exits remain in the Elks' ranges. Consequently the r479 reversal does **not** establish that a safe one-step continuation existed. At r477 the other B actors are Prism5(59,43), Marcella7(27,63), Willow8(23,38), HoR9(17,61). Willow is 15 tiles from the Vesper endpoint and sees Vendetta2 in the end-round state; no free immediate heal can be credited. Vesper's end-round `sees` arrays are empty throughout472–479, but these are not native actor-start observations or private fog beliefs.

## Source hypothesis, not an observed branch

Frozen f475 `provenance/willow-astraeus-clock-recovery-20261024-v1/workspace/bots/service-base-f7/src/bot.cpp:2823` and released-source `bots/Khaos_v34/src/bot.cpp:2827` both implement `camp_exit_rounds` by finding a standable, camp-safe tile on geometric rings. They do not verify a connected walking path to it. `camp_trapped` (f475:2838; v48:2842) prices that count with `dps*(1.5*rounds+1)`. Holes can therefore make its claimed walking-exit estimate optimistic even though its multiplier is conservative on an open board.

Both sources' `flee_camps` at bot.cpp:303 similarly scores proximity to a safe tile, then immediate damage/home distance. In v48 `retreat` at4233 calls `dash_away` then `flee_camps`, falling back to `retreat_step` if flee makes no move (4266–4268). `self_abilities.cpp:397` ranks dash landings by local threat count and home-field distance, not a funded onward escape path. `retreat_step` at341 can choose a homeward in-range step when no zero-damage longer step is available. `Safety::damage_bound` at safety.cpp:2019 does include camp damage, so “camps omitted from safety entirely” is not the hypothesis.

This makes **terrain-connected exit cost versus local exposure reduction** a defensible, inherited source hypothesis for r474–477. A failed local improvement followed by homeward fallback could also explain the later reversal. Actual caller, camp knowledge, blocked/guard tiles, weighted camp estimates, and private enemy beliefs remain unknown; the public match has not established either function's execution. Do not change recall policy, force holding, or prohibit reversing based on this sequence.

## One bounded next step

Root authorized, and Luna has been asked to schedule, existing-exporter own-view **Vesper6 physical B r472–480 inclusive** (9 rounds). Required observations: native champion type/action readiness, visible/known camp33/37 HP/awake state, local terrain/occupancy, visible enemies, and available allies. Coordinates above are raw; B own-frame is `(60-x,70-y)` and must remain separate.

If that view supports known camp exposure and feasible earlier exits, the minimal subsequent trusted source diagnostic is the **r474 retreat decision and r477 dash→walk decision**, not another whole-game farm scan. Log only already-computed caller/reason, `camp_trapped` dps/ring result, chosen dash/home distance, `flee_camps` current/best cost and walk_out, attempted endpoint/refusal, and whether `retreat_step` fallback executes. Candidate path connectivity can then be checked from the actual known blocked board. A private enemy exclusion, stale/unseen camp discrepancy, or lack of a survivable route from the earlier health state would falsify a simple avoidable-routing interpretation. No such trace is requested or implemented yet.

The saved artifacts establish wasted camp work followed by camp-only death, not how many additional captures a repair would produce or that this single death caused the637 total capture deficit.

## Evidence pins

All replay artifacts below are under `provenance/khaos-v34-ladder-intake-20261024-v1/`:

- `extracted/e173d5a45b8562cb/meta.json`: SHA256 `eec006856e1dfcc373beb8331b971bec5564a589be50bb142ce86dab8aec6af0`.
- `extracted/e173d5a45b8562cb/events.jsonl.gz`: `d2d968f853b4591577fc97ec833629e10fe4ef27e5595be323419c9633537ecd`.
- `extracted/e173d5a45b8562cb/rounds.json.gz`: `3ea65bcc75f698aa684d9f19ff9fbeed33be9ed9a1f6b3f66ffa8acffafc5a56` (round r is array index r−1).
- `extracted/maps/8f17d2cbf1d64f77.json`: `73ca7fc6b7f0332ce7e81805b43ed02e7fea1237cefdb522461e429836ebab7b`.
- `MACRO-RESULT.json` pins the source bundle/native audit; `MACRO-RESULT.md` provides the cohort context, subject to the end-bag attribution correction above.

Source identities: frozen f475 aggregate `f475b8521cada611754076822402a266c43be8de76ce0f2b504b268ff3335824`; locally released Khaos_v34 aggregate `781fe3641afc4333d8c8a1b42f1344b4ba19edf9d96ae092e9e62069b9083d68`. Neither identity is inferred from this Fracture outcome.

## Bounded own-view follow-up

The authorized existing-exporter window is now available at `provenance/khaos-v34-ladder-intake-20261024-v1/fracture-vesper6-r472-480/own-view.json`, SHA256 `90e38fcfc4408b33a6d193ac29662ac6f03d73be862efa8112a262e7f9763fbb`. It confirms actor6 is physical-B Vesper Vale with Attack reset/Dash, Strength135, Focus100, maxHP1200. User context says the active server was v47; the artifact still explicitly lacks exact binary/source attribution.

At every living actor start472–479, **no other champion is visible**, and both Elks33/37 are explicitly own-view-known and awake. Camp33 HP is645 at472,375 at473,240 from474 onward; camp37 stays2400. Thus the two camp threats were not merely static-layout hindsight, and no visible ally tank/heal or visible enemy forced the local route. Private remembered enemy positions/comms remain unavailable. Static-only cluster records must not be relabelled live/cleared from this export alone.

Native start cooldowns are `[reset,dash]`:472 `[0,4]`,473 `[7,3]`,474 `[6,2]`,475 `[5,1]`,476 `[4,0]`,477 `[3,0]`,478 `[2,7]`,479 `[1,6]`. The dash was already ready476, but is only used477. The holes defining the pocket are public terrain and present in the local own-view terrain, with nearby entries marked currently visible. Local camp coordinates are own-frame `(26,29)` and `(25,29)`, corresponding to raw `(34,41)` and `(35,41)`; all movement tables above remain raw.

This strengthens the connected-escape diagnosis to **known camp and known terrain**, while leaving the actual admitting branch and chosen-path rejection unresolved. It does not establish a safe late one-step exit, guaranteed survival from474, or that the remaining low-HP Elk should have been attacked instead of retreating. A source prototype is justified by the independently verified geometric invariant; a private branch claim still needs exact reproduction/trace. The source-only design is `research/willow-connected-camp-escape-design-20261024-v1.md`.
