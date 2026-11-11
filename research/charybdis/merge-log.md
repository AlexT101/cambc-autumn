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
