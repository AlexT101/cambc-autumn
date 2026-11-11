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
