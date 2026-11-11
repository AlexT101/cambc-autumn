# charybdis phase-1 merge log

Every A/B: release builds, normal fuel (no `--fuel`), `--no-test-draft`, fast runner, on the fixed phase-1 suite set
`/home/ubuntu/wt/charybdis-maps/s-710001..710040` (40 ladder-v2 suites of 256 maps, both sides: 20,480 games).
Extensions, when a step needs more games, are `s-710041..710080`. CIs are ab.py's 95% intervals.
Accept rule (merge1-brief.md): win rate against charybdis-base above the last accepted state's (50% for the first step),
and against ocean-main-b7c87cf not below the last accepted state's. K2a (a mechanical bug fix) is accepted unless
significantly negative.

## Reference: charybdis-base on these suites

charybdis-base vs ocean-main-b7c87cf: **56.9%** of 20,480 (CI 56.3-57.6). OOF turns CAND 121,404, REF 111,497.

## K1 = M3-a, EOQ bank floor with an online carrier hazard (macro3-eoq2)

- **Merged:** `diff -ruN ocean-main-b7c87cf/src macro3-eoq2/src` applied with `patch -p2` from the bot root, offsets
  only, no fuzz:
  - economy/bank.cc: `CarrierRecord carriers`, `note_carriers`, `carrier_hazard`, `bank_floor`; `bankable_bag` uses
    `bank_floor` in place of `params::min_bank`;
  - economy/shop.cc: `gem_income_rate`;
  - params.h: `min_bank` removed; `carrier_hazard = 0.86e-3`, `bag_swing = 2` added;
  - bot.cc `play_turn`: `note_carriers(world)` before `note_upkeep`;
  - bot_parts.h: declarations.
- **Audit:** no bugs. Hunks identical to the source; the hook lands at the same place in the base's `play_turn`;
  `bankable_bag` has no base-only callers; the Prism's `banks_bag` is unchanged (`retaining_gems` bypasses the floor
  except on a winning or closing bag, which bypass it anyway); farm.cc's `bank_floor` is a member, no shadowing
  problem. Inherited risks (no fix): the keeping Prism dominates the hazard posterior; any bag above 0 counts as
  carrying while the prior was measured at 25+; Cassi/Issac's shared death counts twice; the floor moves with position.
- **A/Bs (20,480 each):**
  - vs ocean-main: **57.9%** (CI 57.2-58.6); OOF CAND 125,278, REF 109,620.
  - vs charybdis-base: **51.1%** (CI 50.4-51.7).
- **Decision: accepted.** Above 50% against base, and 57.9 >= 56.9 against ocean.

## K2a = M2-d, no lethal camp flight (macro2-lstep)

- **Merged:** macro2-lstep's two combat/fight.cc hunks alone (`flee_camps` gains `bool& deferred`, prefers a
  non-lethal step, and defers to `retreat_step` when only lethal exits are left and a surviving retreat step exists;
  its caller in `retreat`, with the debug-only `LSTEP` trace). `patch -p2`, offsets only. Built on K1.
- **Audit:** no bugs. Hunks identical to the source; none of macro2's other pieces leaked in. The base's own
  `retreat_step` changes (held-tile descend branches) are unreachable after a deferral, since a deferral needs camp
  damage at `here`, which puts `here` in `avoid`; only the base's `held` sort key remains, which reorders equal-damage
  steps and cannot put a lethal step first. Inherited risk (no fix): the prediction of `retreat_step`'s step can
  miss on the bush bonus, walk-dash options or a failed `try_move`, as in macro2.
- **A/Bs (20,480 each):**
  - vs ocean-main: **58.2%** (CI 57.5-58.8); OOF CAND 126,328, REF 110,118.
  - vs charybdis-base: **51.4%** (CI 50.7-52.1).
- **Decision: accepted.** A bug fix, and it also passes the gain rule (51.4 > 51.1 against base, 58.2 >= 57.9 against
  ocean); the steps are within noise of each other.

## K2b = M2-c hold cast, M2-a Willow heal order, M2-b two casts on a double turn (macro2-lstep)

- **Merged (candidate only):** the rest of macro2-lstep's diff, `patch -p2`, offsets only, no fuzz, on K2a:
  economy/capture.cc `hold_capture` (cast at the nearest alive group within cast reach that wakes nothing);
  combat/self_abilities.cc/.h (`heal_value`, `HealMate`, `heal_mate`, `heal_before`, `HealTarget::value`/`urgent`,
  `HealGate::urgent`); combat/support.cc (`heal_station`, the formation step choice); model/safety.cc/.h
  (`add_two_casts`, `moved_strike`, two-turn `threat_strike`, `most_damage`, `Reach::build_ways`).
- **Audit:** no bugs; every hunk identical to the source.
  - The base's Willow `on_held` filter and `heal_before` ranking coexist (one filters tiles, the other ranks).
  - M2-b leaves B1's verdict alone: `turns_to_harm_idle` models the Prism as never acting, and `add_two_casts`
    raises damage, never reach.
  - The plan is wrong that `cast_at_camp` has no enemy check: `camp_cast` refuses when `engagement_near`
    (a visible enemy within cast reach + 1, or within its strike reach + 1). The remaining exposure is a sole
    Prism holding with an enemy at 7-8 tiles, which may spend its stun on a camp.
- **A/Bs (40,960 each, s-710001..710080, the plan's size for an expected +0.5):**
  - vs ocean-main: **58.5%** (CI 58.0-58.9); halves 58.59 / 58.33. OOF CAND 260,042, REF 220,045.
  - vs charybdis-base: **51.4%** (CI 50.9-51.9); halves 51.27 / 51.52.
  - The accepted state (K2a) on the extension suites s-710041..710080, so both compare on identical maps:
    vs ocean 58.6% (CI 57.9-59.3), vs base 51.9% (CI 51.2-52.6). Over all 40,960: K2a **58.37%** vs ocean,
    **51.65%** vs base.
- **Decision: rejected, to the end of the CONSIDER queue.** Against base it is below K2a, 51.39 against 51.65, and
  lower on both halves. Against ocean it is level, 58.46 against 58.37. It was level at 2x fuel too (macro2: 50.0,
  50.2 and 50.0 on ocean), so this is not a normal-fuel loss and gets no fuel-optimization note. OOF turns rose about
  2% against K2a's (260,042 against 254,823 in the vs-ocean runs). K3, ported on top of K2b, was rebased onto K2a
  before its test: the same diff, applied cleanly.

## K3 = M4-b1, hand-over of full and single-tile holds (rebuilt in the base)

- **Built (candidate only), on K2a:**
  - economy/capture.cc `leave_for_prism`, the ally side:
    - `full` means we stand on a held group whose every tile is taken, our own counted as taken whatever the
      occupancy reads.
    - The `kept_group` pin is ignored when `full`.
    - The claimed branch returns `claimed` when `full`, and on an unheld single-tile group.
    - The near branch returns `near` when `full`, both in the pin case and in the slack window.
  - New `prism_hand_over`, the Prism side: `prism_takeover`'s gates, plus every tile held by visible non-Prism
    allies with no tribute and not held back, and `fresh_ally_capture >= 2`. It calls `prism_carries(..., taken)`,
    whose goal is the group's tiles less camp-hit tiles.
  - economy/farm.cc carry loop: a full held group goes to `prism_hand_over` only (skipping `prism_takeover`, which
    must fail on it). It is priced as 'L' over `walk + capture_rounds`.
  - The walk goes to `G.adjacent()` and waits there while every goal tile is held, since the base's route treats
    ally-occupied tiles as blocked.
  - Debug-only traces: `K3 LEAVE/PICK/ARRIVE/PAYOUT/LOST`. bot.cc calls `k3_watch` inside `debug_block`.
- **Audit:** no release-side bug; the spec is fully implemented. Fixed after the audit:
  - `full` now requires us on the group, with our own tile explicit. The audit could not confirm that ally occupancy
    includes self, and off-tile callers were getting full leaves that later lapsed their record.
  - Debug: the leave trace now prints once per group, cleared episode and kind (it overcounted). `k3_watch` arms
    only on a new pick, resets on leaving or death, reads gems only while alive, and logs the measured payout delay.
  - Fuel: a full group skips `prism_takeover`'s doomed `enemy_may_see` scan.

  Not changed (risks noted): the two sides' gates differ, as for the base's held 'L', so a Prism can wait beside a
  hold that is never left, until the timer is under 2; the waiting tile is not checked for camp damage; a leave that
  frees only a camp-hit tile dissolves the pick.
- **Debug batch** (512 games against ocean-main, debug build on fresh suite dbg-719001, measured on the K2b-based
  build; the K3 diff is identical):
  - Prism hand-over picks 0.26 a game (in 55 of 512 games), with a predicted delay of 4.9 rounds (median 4, at
    most 14).
  - Arrivals and payouts 0.19 a game; 7.1 gems a payout; measured delay against the ally's payout 3.9 rounds
    (median 4, -1 to 11). No hand-over was lost.
  - Ally leaves, per process and episode: claimed-full 0.33 a game (0.20 on single-tile groups), claimed-single
    (unheld) 1.40, near-full under 0.01.
  - That is under the plan's "about once a game", so a level result was expected.
- **A/Bs (40,960 each, s-710001..710080):**
  - vs ocean-main: **58.3%** (CI 57.9-58.8); halves 58.12 / 58.55. OOF CAND 255,255, REF 220,549.
  - vs charybdis-base: **51.6%** (CI 51.1-52.1); halves 51.58 / 51.69.
- **Decision: rejected, to the end of the CONSIDER queue.** It is level with K2a on the same 40,960 games: 51.63
  against 51.65 against base (8 wins fewer) and 58.33 against 58.37 against ocean. More games can't make a 0.02-point
  deficit a gain. It was not measured at 2x, so it gets no fuel note.

## Phase-1 result

Accepted state: K1 + K2a, `bots/charybdis` at commit 3c9b6c294, frozen as `bots/variants/charybdis-p1`.
On s-710001..710080 (40,960 games each): **58.37%** against ocean-main-b7c87cf and **51.65%** against
charybdis-base. charybdis-base itself scored 56.9% against ocean on s-710001..710040.

# Phase 2: the CONSIDER queue (merge2-brief.md)

Every A/B: release builds, normal fuel (no `--fuel`), `--no-test-draft`, fast runner, on the fixed phase-2 suite set
`/home/ubuntu/wt/charybdis-maps/s-720001..720080` (80 ladder-v2 suites of 256 maps, both sides: 40,960 games). Each
candidate plays ocean-main-b7c87cf, charybdis-base and charybdis-p1. CIs are ab.py's 95% intervals; "paired" compares
two runs against the same opponent game by game (same map, same side), with a 95% CI on the difference.
Debug batches: 512 games (debug build) against ocean-main on `dbg-729001`.
Accept rule (first phase-2 change): against p1, 95% CI lower bound above 50%; against ocean-main and base, not below
p1's on these suites.

## Reference: charybdis-p1 on these suites

- vs ocean-main: **58.61%** of 40,960 (CI 58.1-59.1); OOF CAND 247,857, REF 215,490.
- vs charybdis-base: **52.21%** of 40,960 (CI 51.7-52.7).

## C1 = M4-a3 + M4-b2, team-marginal carry value with the `hub_net` gate (macro4-handfc)

- **Merged (candidate only):**
  - new economy/hub.cc: macro4's `camp_gem_density`, `gem_damage_rate`, `hub_premium`, `hub_factor`,
    `champion_gem_rate`, `hub_net` (verbatim); `params::hub_rho_most = 2`; declarations in bot_parts.h; unity.cpp.
  - economy/farm.cc carry loop: `cycle_rate` = `best_value` before the 'T' loop. 'G' worth
    `gems x rho + holder gain + (timer - walk) x cycle_rate` over `timer`; held 'L' (the ally's claimed leave)
    `gems x (hub_factor(rho, timer, max(timer, walk + capture_rounds)) - 1) + gain`, taken only if `hub_net > 0`;
    empty 'L' `(1 + rho) x gems + per_gold x gold`. Holder gain is `takeover_gain`'s: our `holder_value` less the
    best visible holder's, at `prices().per_gold`.
  - economy/capture.cc `leave_for_prism` claimed branch: a held group is left only if `hub_net > 0` (M4-b2).
- **Audit:** one bug, fixed. A held group was priced as empty when any holder's recall landed before the Prism's
  arrival, which also caught capture recalls timed to land on the payout (they score). Now it is priced as empty only
  when every visible holder lands a kept recall before the payout (`channel_end_round < payout`, the base's own test).
  Both gates now use `G.gems`. Noted, not changed: the empty 'L' still uses the base's halved `per_gold`
  (`gold_part`), as the spec says; `hub_premium` is recomputed on the ally side (cheap).
- **Debug batch:** C1 changed the Prism's carry decision in 225 of 512 games, about 2 turns a game. Almost every flip
  refuses a 'G' or 'L' the base took (G 246 and L 244 episodes refused, 54 newly taken). The refusals have negative
  worth: the holder gain. On gold-rich groups a Vesper (+33% gold, high `relative_efficiency`) or Marcella holder's
  `holder_value` exceeds the Prism's by 30-150 gems' worth. The gate alone refused 0.17 Prism picks and 0.03 ally
  leaves a game. Prism 'G'/'L' picks per game fell from 1.21/1.59 (p1, trace copy) to 0.65/0.98.
- **A/Bs (40,960 each):**
  - vs ocean-main: **57.7%** (CI 57.2-58.2); paired against p1's run -0.92 (CI -1.36..-0.47). OOF CAND 250,548.
  - vs charybdis-base: **51.3%** (CI 50.9-51.8); paired -0.86 (CI -1.33..-0.40).
  - vs charybdis-p1: **49.3%** (CI 48.8-49.8).
- **Decision: rejected.** It loses significantly to p1 and falls below p1 against both references. The likely reason
  is that the holder-gain term undoes the base's carry lever. macro4 gained with it, but on ocean, whose Prism
  carried little. The base's gain comes from handing allies' captures to the Prism ("reallocate"), and C1 refuses
  roughly half those carries whenever the holder values gold more. That overlaps with the base: its 'G'/'L' already
  price the Prism's side, and `gold_part` already stands in for the premium. Per the plan, the gate alone was tried
  next (C1b). Next step if revisited: price the holder gain with gems only (drop the gold differential), or take the
  premium only on 'L' empty groups.

## C1b = M4-b2 alone, the `hub_net` gate on held hand-overs

- **Merged (candidate only):** hub.cc, params and declarations as C1. The carry values are the base's. Two gates:
  - farm.cc, a held 'L' the Prism reaches after the payout (`walk >= timer`) whose holders stay: taken only if
    `hub_net(rho, G.gems, timer, max(timer, walk + capture_rounds)) > 0`;
  - capture.cc, `leave_for_prism`'s claimed branch for a held group: the same test from the ally's side.
- **Audit:** one over-block, fixed. The Prism-side gate also caught in-time picks with a recalling co-holder (now
  `walk >= timer` only). The sides otherwise agree; the remaining differences (the ally reads the Prism's posted
  tile, each instance computes `champion_gem_rate` from its own view) matter only at the threshold.
- **Debug batch:** 0.24 Prism refusals and 0.02 ally keeps a game (in 70 and 10 of 512 games). It rarely fires,
  so a level result was expected.
- **A/Bs (40,960 each):**
  - vs ocean-main: **58.7%** (CI 58.3-59.2); paired against p1 +0.13 (CI -0.03..+0.29).
  - vs charybdis-base: **52.3%** (CI 51.9-52.8); paired +0.14 (CI -0.03..+0.30).
  - vs charybdis-p1: **50.1%** (CI 49.6-50.5).
- **Decision: rejected (level).** The lower bound against p1 is under 50%. Reaching above 50% at 81,920 games would
  need about 50.35%, against the 50.06% measured, so it was not extended. It fires about once in four games. It was
  not measured at 2x, so it gets no fuel note.

## C6 = M5-f, route tie-break off the Prism's hold (conditional): not built

- **Trace** (the plan's condition). A debug copy of charybdis (`chy2-C6trace`, debug-only lines in bot.cc) tags each
  `decide()` branch. For a non-Prism champion, it logs every step onto a group the Prism holds alone
  (`prism_hold_tiles` from its view, copied before `decide`). It also logs every turn that ends on such a group the
  round before its payout (a split share). 512 games against ocean-main on dbg-729001:
  - step-ons: `take_capture_handoff` 29, retreat 13, chase 6, farm 1;
  - splits: 22 in 22 games. 15 are champions already on the tiles before the Prism became sole holder (not
    transit). 7 are transit through the unguarded branches the plan lists: 4 by retreat moves, 3 by chase moves.
- **Decision: not built.** Transit splits through those branches happen 0.014 times a game, once in about 70
  games. A tie-break that changes so few games can't show a clear gain at 40k games. The leak is smaller than macro5
  measured on ocean (hold6's 13 shared payouts in 48 games), because the base's guards already cover most of it.

## C3 = M6-bc, Focus-priced farm values replacing `gold_part` (macro6-carry3)

- **Order:** taken before C2, since C2's plan entry says to run it with C3's J piece or after C3.
- **Merged (candidate only), on p1** (a first build on C1 was discarded with C1):
  - economy/farm.cc: macro6's hunks 2-15 (`keep_most`, `keep_bonus`, `bound_tribute`; S/K/C worth `plain + carried`;
    the J branch's `plain`/`carry`/`carry_most`, `hold = cap_rounds`, the health gate, and the moved kite-hit check;
    every prune bound). Hunk 1 (`multiplies`' signature, part of M6-a) and the debug lines are left out.
  - The base's `gold_part` is removed at both places (the `per_gold` halving and the crystal toll), so this is a swap.
  - `keeper` is the base's `keeps` (`keeps_gems`), not macro6's `passive == gem_focus`.
  - The 'G' and 'L' carry worth gains `gems x keep_bonus(G)`, as the plan requires, so every Prism pick type uses one
    premium.
  - economy/capture.cc: `keeps_bag` and `carried_bonus` ported, but not used in `holder_value` or the others (M6-a).
- **Audit:** no bugs.
  - The hunks match macro6's, and no `gold_part` is left.
  - The prune bounds stay valid: `keep_bonus(G)` is 0 or `keep_most`; the join bound's carry term bounds J's.
  - Nothing outside farm.cc relied on the halved gold.
  - Risks noted: 'T' is now harder for a keeping Prism with a Vesper-level gold bonus; J counts the Focus in full even
    where B1 may not make the Prism sole holder; `carried_bonus` ignores `prism_dominant`.
- **Debug batch:** the bonus applies to every keeping-Prism pick. Prism picks a game (p1 trace copy, then C3):
  S 14.54 to 14.26, C 3.03 to 2.71, K 6.75 to 6.92, J 12.65 to 12.83, G 1.21 to 1.13, L 1.59 to 1.47.
- **A/Bs, s-720001..080 (40,960 each):**
  - vs ocean-main: **59.0%** (CI 58.5-59.4); paired against p1 +0.36 (CI -0.22..+0.95). OOF CAND 249,931.
  - vs charybdis-base: **52.3%** (CI 51.8-52.7); paired +0.04 (CI -0.55..+0.64).
  - vs charybdis-p1: **50.3%** (CI 49.8-50.8). Within noise, so it was extended.
- **Extension, s-720081..160 (40,960 more each, p1 measured there too):**
  - vs p1: 50.3% (CI 49.8-50.8);
  - vs ocean: 59.1%, against p1's 58.8%;
  - vs base: 52.0%, against p1's 51.7%.
- **Pooled, 81,920 games:**
  - vs charybdis-p1: **50.31%** (CI 49.97-50.65);
  - vs ocean-main: **59.06%**, paired against p1's 58.68% +0.37 (CI -0.04..+0.78, z 1.77);
  - vs charybdis-base: **52.14%**, paired against p1's 51.96% +0.17 (CI -0.25..+0.60).
  - OOF turns are level against p1 (CAND 241,225, REF 238,119 on the extension).
- **Decision: rejected (level).** The CI lower bound against p1 is 49.97%, not above 50%, even at 81,920 games. The
  direction is positive throughout, so it is the nearest miss so far.
  - **Flag: dropped at normal fuel: candidate for later fuel optimization.** macro6's carry2 and carry3 gains
    (+1.1, +1.0) were measured at 2x fuel.
  - The likelier reason is overlap: the base's `gold_part` is a cruder version of the same pricing, so the swap
    changes the Prism's gem:gold weight only where `per_gold` differs from about 0.18, and on J.
  - Next step: test it with a Focus premium gated on `prism_dominant`. Or combine it with a future change that hands
    the Prism more joins (where the J piece matters most).
