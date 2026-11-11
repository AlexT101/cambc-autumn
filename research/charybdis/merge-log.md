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
