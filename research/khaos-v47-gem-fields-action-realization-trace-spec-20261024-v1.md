# Gem Fields Prism: selected g4, unrealized approach spell

2026-10-24. Frozen f475 source-only follow-up, bounded to physical-A Prism0 rounds6–7. No new helper, build or run by this reviewer. Exact quote-prefix receipt and corrections are recorded in `khaos-v48-gem-fields-opening-economy-review-20261024-v1.md`. This supersedes the original “g4 rejected for g0” nomination.

## What is established

The trusted225-input/nine-state/45-host-segment prefix selects g4 both turns: claim4/crew0, no shared/help selection, all18 candidates evaluated, spell0. Partner-rescued value is.692690/.734156. Thus crew/economic reweighting is not the demonstrated immediate fix.

At r6 Prism is(18,19),700HP,35Strength/80Focus, both cooldowns0. It sees awake Elk8(21,24),2400HP, and live clusters35(22,23),37(22,24),45(20,24),49(21,23), each120HP; cluster47 is only static-layout known. There is no visible enemy. Cast center(21,23) is within4 and its3×3 covers those five known live targets. Ground abilities can target occupied/wall/unseen tiles and do not require a clear walking path (rules58–61). Focus80 AoE would apply80 to each,400 total before considering other unknown members. This is a legal known-geometry opportunity, not a guaranteed winning line or free action: Prism's ground spell excludes walking.

At r7 Prism stands(17,20),640HP after an Elk hit, both cooldowns0. Elk8 is within4, so unit CC is geometrically reachable; however Prism is also in its range4. Known nearby allies do not guarantee free tanking or healing. No opponent future position is needed for this nomination.

## Source-derived gates to distinguish

All line references use `provenance/willow-astraeus-clock-recovery-20261024-v1/workspace/bots/service-base-f7/src/`.

1. `bot.cpp:2426–2434`: spell-clear branch is off because selected `spell0`; next is `cast_at_camp_on_approach(world,best)`, then `farm_attack_tiles` or `walk_on` fallback. Confirm this exact caller is reached before assuming a cast decision.
2. `abilities.cpp:599–624`: requires Prism, belief-ready slot, native can_cast, unchanged position; alive group; harmful group's belief awake; no live group member in basic range3; and no living damaging camp from any group within its attack range. At6 the visible Elk is distance5, outside the final exposure guard; at7 it is distance4, so that guard is a direct possible rejection. A stale belief/prior gate may reject sooner; do not infer which without a tag.
3. `camp_cast` at393–558 checks actual castability, group/state, visible enemies within6, then imports only currently visible live members and builds the `harmful` list. Unit approach spells require harmful targets; at6 the sole Elk is out of unit range4. The ground call at499–500 supplies `&harmful` for a harmful approach group. `best_ground` at166–214 requires **two harmful hits** when that pointer is present. One-Elk/eight-cluster g4 cannot pass regardless of aggregate damage to clusters. It is a deliberate source gate, not absence of AoE support or a line-of-sight restriction.
4. Ordinary movement then makes both exclusive Prism spells unavailable (`walked/castable`, abilities.cpp:23–27). `cast_at_camp` after the walk atbot.cpp:2464 does not recover the discarded pre-walk opportunity.

## Are the moves wrong-way routing?

Not established. From(18,19), the southern hole row y21 spansx13–19, with holes(19,20),(20,20),(21,20) and farther northeast. The observed westward steps(17,20),(16,20) are consistent with going around the row's western end toward g4's attack stations. Vesper also occupies(18,20) in the start view. Native target-center distance15→14 decreases in the quote. Static layout supports a detour, but no complete shortest-path proof or dynamic route winner has been inferred. Do not change route direction merely because raw Chebyshev distance increases.

## Minimal continuation instrumentation for Luna

Reuse the already trusted f475 recorder/tracer setup and the same actor/round scope; preserve all query order/short circuits. Log results where already computed, not by rerunning native/Safety calls. Revalidate accepted inputs, round hashes and host-call segments throughr7 before interpreting.

- **One farm continuation tag:** entry to approach-cast; returned boolean; actual following path `tiles-ready`, `tiles-null→walk_on`, `already-in-goals`, or normal routing. Record the existing best/range/spell, selected target and actual move endpoint. In `walk_on`, record whether it used the intended group, previous group or centre fallback. No new field read just for logging.
- **One approach rejection tag:** first executed failure among type/readiness/native-cast/walked, group-state, group-awake, basic-range member, or damaging-camp exposure. Record only the relevant already-visited member/group and existing distance/range. Do not evaluate later gates after an early return.
- **If camp_cast is reached:** native ready-slot results already used, visible member count/harmful count, resulting selected slot/value/tile, execute result/error. For the existing `best_ground` loop, accumulate counts and maximum already-computed value/center rejected by `hits<2`; record whether any candidate passed. This proves the one-harmful restriction without evaluating alternate casts.
- **Only if route fallback remains ambiguous:** at the actual route call record existing `search`, cap, null/ready result, route/descent/fallback label, and the already-chosen move. Reuse existing fuel readings at existing checks; no fresh `fuel()` or host state probe. There is no need to dump all board cells or repeat the entire farm scan.

These records distinguish (a) pre-cast unavailable/stale state, (b) two-harmful rejection at6, (c) exposure rejection at7, and (d) normal detour versus retained-target/cost fallback. The smallest likely experiment, **only if confirmed**, is improving the existing Prism approach-cast opportunity test for an already-selected mixed camp, rather than macro role assignments, a blanket “cast every ready spell,” or forcing all allies to join. Preserve exclusive-action cost and enemy/other-group wake checks. This note does not authorize implementation or another policy expansion.
