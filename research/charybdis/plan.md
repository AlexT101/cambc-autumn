# charybdis merge plan

Base: `bots/charybdis` = `variants/charybdis-base` = macro1-hold6, 56.8% of 40,960 normal-fuel games against
ocean-main-b7c87cf. This plan covers what to take into it from macro5, macro4, macro6, macro3 and macro2 and from the
leftover variants, and in what order. It is the final plan the merge agents follow.

## Revision (after the independent audit, plan-audit.md)

The coordinator's amendment numbers don't match the audit's own list. I followed the content: everything requested,
except the audit's K2 gate (its amendment 7), which the user's merge rule replaces.

- **Merge rule (the user's).** A KEEP change or group is merged only if it raises the win rate (operational test
  under "Merge rule and gates" below). Otherwise it moves to the end of the CONSIDER queue. The one exception is a
  clear mechanical bug fix with no trade-off, which may be merged at a level win rate. The audit's "adopt K2 unless
  significantly negative" is not adopted.
- **K2 is split.** K2a is M2-d alone, the only clear mechanical bug fix, merged unless it loses. K2b is M2-a, M2-b and
  M2-c, which must show a gain. Its expected +0.5 needs about 40k games to resolve, so the gate size is raised.
- **K3 spec fixes:**
  - the unheld single-tile group the Prism claims (this folds in M4-b4's single-tile part);
  - a `timer >= 2` floor on the Prism's pick, matching the ally side;
  - a stale `kept_group` pin ignored on full groups;
  - a check that the walk goal (all its tiles occupied) advances, with `G.adjacent()` as the fallback;
  - the `enemy_may_see` gate kept.
- **K3 evidence corrected.** `q-nohand` is no longer cited: it ablates the step-off mechanism the base already has,
  on a version from before the single-tile rule. `hand`'s +0.8 / +0.5 covers five changes and isolates none of them.
  K3 is a different rule from macro4's for multi-tile groups. The debug batch now also counts arrivals, payouts and
  the payout delay.
- **Port command.** `patch -p1` from the bot root, or `-p2` from inside `src/`.
- **C1 spec.** It now also prices 'L' on a held group (late form, `hub_net` gate). The +1.6 measured the value and
  the gate together. `q-r0` is described correctly. The rho clamp is named as a hand-set constant.
- **C3.**
  - The merge note is fixed: every macro6 farm.cc hunk applies cleanly, and the danger is that they stack silently
    on `gold_part` (farm.cc:959-960, 1937).
  - Counter-evidence added: prismhold2 (-2.4) and aoe (-3.2).
  - 'G' and 'L' must carry the same bonus.
  - The J branch's `hold` rounds are documented.
- **C1 with C3.** One Focus premium for every Prism pick if both are kept.
- **M5-f moves from DROP to CONSIDER** (low, conditional on a trace), with the branches the base's guard really leaves
  uncovered and a memoised port spec.
- **Smaller notes:**
  - B4 is narrower than first stated. 'G' keeps `enemy_may_see`, and both `leave_for_prism` branches pin.
  - M5-a's attribution is marked as inferred, and hold5 is cited.
  - M5-e's split is marked as coming from traces.
  - M5-c gains a fuzz-1 hunk to check by hand, and its case is stronger on the base.
  - M3-a: the Prism dominates the carrier record.
  - L-2 cites hold7.
  - The audit's "missed changes" are named in their entries.
- **Audit disputes:** none remain. On re-checking the code (`leave_for_prism` lines 456-507, `bot.cc:486`
  `strike_guard`, farm.cc `gold_part`, macro4's `q-nohand` patch), I agree with every point adopted.

## Method

Each bot was diffed against `variants/ocean-main-b7c87cf/src` and against the base, and each step of each programme
against the one before it, from the worktrees' `bots/variants/macroN-*` and `patches/`.
- The behaviour below is read from the code. The evidence is from the logs.
- Unless a row says otherwise, every orchestrator A/B was 10,240 games at **2x fuel** (`--fuel 200000`, release,
  `--no-test-draft`) against ocean-ref-b7c87cf, which is identical to ocean-main-b7c87cf. Only the six final bots
  have normal-fuel numbers (results.md).
- macro3's and macro2's diffs apply to a scratch copy of the base one after the other (`patch -p1` from the bot
  root), and the stack builds in release. The audit confirmed this independently.

## Summary

The four bots ranked just below the base all pull the base's own lever: put the team's capture gems on the Prism, for
its Focus. In each case the base already does the core of it, in a stronger form:
- its `sole_capture_holder` works with enemies in sight, under a threat test;
- its 'G' and 'L' picks take over allies' holds;
- allies leave groups for the Prism (`left_for_prism`);
- dilution guards cover work steps, fight steps with an enemy in sight, retreat steps and Willow.

Most of the Prism-carry pieces from the other bots therefore duplicate the base and are dropped. One gap is real. The
base's Prism can join an ally's hold only on a free tile, so a single-tile group, or one with every tile held, is
never handed to it. macro4 handles that case. Everything else worth taking is independent of the lever: macro3's
bank floor and macro2's four small rule-derived fixes.

**KEEP** (merge queue order):
1. **K1 = M3-a.** EOQ bank floor with an online carrier hazard (macro3). Must show a gain.
2. **K2a = M2-d.** No lethal camp flight (macro2). A mechanical bug fix: may merge at a level win rate.
3. **K2b = M2-c, M2-a, M2-b.** Hold cast, Willow heal order, two casts on a double turn (macro2). Must show a gain.
4. **K3 = M4-b1.** Hand-over of full and single-tile holds: macro4's idea, rebuilt inside the base's
   `leave_for_prism` and 'L' pick. Must show a gain.

**CONSIDER** (queue order; a KEEP that fails its gate joins the end):
1. **C1 = M4-a3 + M4-b2.** Team-marginal value (macro4's rho and `hub_net`) for the base's 'G' and 'L' picks, empty
   and held, and as a gate on its claimed leave.
2. **C2 = M4-a2.** The Prism collects an ally's clear while it is still in progress.
3. **C3 = M6-bc.** Focus-priced farm values (macro6's `carried_bonus`), replacing the base's `gold_part`.
4. **C4 = M5-c.** Prism stun-lock safety (macro5's prismsafe).
5. **C5 = L-3.** macro3-eoq5: the chain limit replaced by the bank floor's holding cost.
6. **C6 = M5-f.** Route tie-break off the Prism's hold. Only if a trace shows transit splits remain.
7. **C7 = L-1.** macro6-mono: the Focus price extended to the Monolith. Only if C3 is kept.

**DROP:**
- M5-a holder Focus premium; M5-b Prism pick-up of held groups; M5-d hold-sole's threat-gated yield; M5-e the
  capture-recall step-off;
- M4-a1 Q collection of held groups as a separate mechanism; M4-b3 `hub_awaited`; M4-b4 the `hub_claim` farm filter,
  except its single-tile part, which is folded into K3;
- M6-a the carry holder premium and the Prism 'T' takeover;
- L-2 macro5-hold-sole3;
- the debug-only trace lines (macro6 YIELD/PHOLD/TAKEOVER/KEEPB, macro4 HUB).

### Merge rule and gates

- **The user's rule.** A KEEP change or group is merged only if it raises the win rate. If it doesn't, it moves to
  the end of the CONSIDER queue. A clear mechanical bug fix with no trade-off may be merged at a level win rate.
  - Only **M2-d** qualifies as such a fix.
  - M2-b corrects a model gap, but it adds caution, so it has a trade-off.
  - M2-c spends a cooldown.
  - M2-a reorders heals.
  - K3 delays an ally's payout and leaves a group empty while the Prism walks.
- **Operational test** (my reading of "raises the win rate"): an A/B against the previous step, frozen, at normal fuel,
  `--no-test-draft`, on fresh ladder-v2 suites. The 95% CI must lie above 50%. 20,480 games give about ±0.7.
  - Start with 20,480 games.
  - If the result is positive but its CI still includes 50%, extend to 40,960 on further fresh suites (about ±0.5)
    before deciding.
  - A bug fix merges unless its CI lies below 50%.
  - s-700001..080 were used for the 40k ranking, so they are not held out.
- **Fuel.** Every bot lost ground from 2x to normal fuel: macro5 -0.8, macro4 -0.4, macro6 -0.5, macro3 -0.8,
  macro2 -0.1, and the base -1.5 (58.3 to 56.8). The suites differ, so part of that is suite noise. Still, the base's
  per-ally threat test and `prism_eta` fields are its new fuel costs. Run a fuel census of charybdis at 100k
  (`tools/fuel/`, out-of-fuel counts against ocean's) beside the merges. Fuel-only cuts need no gate.

## What the base already does (referenced below)

- **B1 Sole Prism holder in sight of enemies.** `economy/capture.cc` `sole_capture_holder`, `prism_hold_threatened`
  and `use_hold_safety`; `Safety::turns_to_harm_idle`, a fight simulation that does not read `threat_strike`. A fit
  Prism on a cleared gem group holds alone even with an enemy in sight, unless the enemy contests the tiles or could
  take it below the hurt line before the payout. The `enemy_may_see` gate is gone *for the hold itself*.
  `sole_capture_holder` has no Monolith or `holders` test.
- **B2 Prism takeover picks.** `farm_turn`'s carry loop, `prism_carries`, `prism_takeover`, `holders_stay` and
  `carry_reach() = 2 x capture_time`.
  - 'G' joins an ally's counting gem hold that the Prism reaches before the payout, on a calm free tile
    (`carry_goal`).
  - 'L' takes a group an ally has left to the Prism.
  - Both need a *visible* holder, and both bail on `enemy_seen` and on `enemy_may_see` at any member
    (`prism_carries`). Both get `taking_over`'s ranged-hit skip and drop out of recall-to-farm.
  - `prism_takeover` fails when no calm free tile exists, so a full group is never picked.
- **B3 `left_for_prism` / `leave_for_prism`.**
  - **Claimed:** allies leave a gem group the Prism claims within `carry_reach` when the Prism would miss their
    hold's payout (for an unheld group, when its walk is at least `capture_rounds - 1 +` ours).
  - **Near:** they leave a freshly cleared group for an unclaimed Prism due before the lapse, via `prism_eta`, unless
    the Prism is dominant (`prism_dominant`).
  - In **both** branches, a held group the Prism is due on before the payout keeps the ally on and pins it
    (`kept_group`, capture.cc:496 and 507, read at 463). A hold with under 2 rounds to pay is never left.
  - It is read by `holding_capture_now`, `yield_capture(after_farm)`, `step_onto_cleared`, `pick_up`,
    `take_capture_handoff`, `join_marcella_capture`, `capture_taken`, the farm and 'T' loops, and `decide`'s claim
    drop.
- **B4 Dilution guards.**
  - `prism_hold_tiles` (capture.cc:870) needs the Prism visible to us, standing on a cleared gem group, and named by
    `sole_capture_holder` from our view.
  - Those tiles are in the work guard (`guard_work`'s avoid, which reaches `decide`'s branches from `banks_bag` on)
    and in the fight step guard (`held_step_guard`, *only with an enemy in sight*).
  - They are also in `retreat_step`'s tie-break and homeward descend, and in Willow's guard and formation
    (`willow_held_guard`, `reguard_willow`, support.cc `on_held`).
  - `yield_capture` steps an ally off a sole Prism's hold even under threat or when hit, then runs the strike search
    (`yielded_in_sight`), and walks out of a big group.
- **B5 Recall exits.** `capture_recall` gives up the keep when a sole Prism holds the group or is coming
  (`prism_coming`). `continue_recall` cancels a recall for `yields_to_prism`.
- **B6 Farm pricing for a Prism keeping its gems.** `keeps_gems`: gold at half its worth (`gold_part`, farm.cc:959-960,
  and the crystal toll at 1937).
- **B7 Claim hygiene.** `drop_carry_claim` on off-way branches and in `carry_bag`. A non-Prism drops its claim on a
  group it left.

## Per-change entries

### macro5 (hold-sole2, 56.2% normal / 57.0% of 39,936 at 2x)

Steps: prismhold = M5-a + M5-b; prismsafe = M5-c; hold-safe = both; hold-sole = M5-d; hold-sole2 = M5-e + M5-f.

#### M5-a: a Prism holder's Focus premium (DROP)
- **Source:** `economy/capture.cc`: `focus_holder`, `focus_gold_per_gem`, `holder_value`'s `focus` term,
  `multiplies(world, a, G)` (signature changed at every caller, farm.cc `pick_up` included), and
  `sole_capture_holder` refactored onto `focus_holder`.
- **Behaviour:** `holder_value` adds `0.3 x (1.5 / 8 x 30) = 1.6875` gems per gem for a Prism whose bag stays short of
  the win with time to bank, so a gem on the Prism is worth ~2.7. `multiplies` is then true for such a Prism on pure
  gem groups. As a result, `value_holder` and `outvalues_holders` name the Prism the holder when it is on or beside
  the tiles, for single-holder, non-Monolith groups. `yield_capture` then steps the others off once it stands on a
  tile and the hold counts, with no threat present. There is no health gate (macro6's version has one).
- **Evidence:** prismhold, which is M5-a with M5-b: 54.6 / 53.8 / 54.7 on three blocks, 54.4 pooled over 29,696.
  Premium x0.5 gave 52.7 and x2 gave 55.0, so the premium acts as a switch.
- **Overlap:** the base's **B1** makes a fit Prism on the tiles the sole holder on every group `value_holder` covers,
  and on more.
  - Inferred, not measured: in ocean, prismhold's gain probably came from holds `sole_capture_holder` refused because
    an unseen enemy might see the Prism. The base removed that gate. macro5 measured only that 28% of
    Prism-damaged captures paid the Prism nothing.
  - What remains:
    - takeovers while an enemy is seen or may see the group. macro1's hold5 relaxed exactly that for 'G' and 'L', and
      was level (57.81 against 57.62 of 40,960).
    - the Prism whose hold B1's threat test refuses. There an unthreatened co-holder would step off, reversing hold2's
      tuned verdict. Variants of that test (hold3, hold4, hold5) were level.
    - `pick_up`'s claimer race on single-tile groups, which K3 handles.
  - **M6-a** computes the same number.
- **Classification:** DROP. The base covers the mechanism, and the residue is level-tested or conflicts with B1.

#### M5-b: Prism pick-up of allies' counting holds (DROP)
- **Source:** `economy/farm.cc` `pick_up`, rewritten around a `pick` lambda.
- **Behaviour:** on the round a gem group is seen cleared, a Prism outside a crew, siege or Monolith operation takes
  over any ally's counting hold within `pick_up_radius` (7) that it outvalues (M5-a) and reaches a round before the
  payout. It runs before the farm loop.
- **Evidence:** part of prismhold, with no separate test.
- **Overlap:** the base's **B2 'G'** does the same from the farm loop, up to 12 steps away. `outvalues_holders` needs
  a free tile too, so neither handles full groups (K3).
- **Classification:** DROP, covered by B2. It also needs M5-a.

#### M5-c: Prism stun-lock safety, "prismsafe" (CONSIDER, C4)
- **Source:**
  - New `combat/stun_lock.cc`, 270 lines: `make_locker`, `lockers`, `stun_reaches`, `locker_at`, `stun_locker`,
    `sole_stun_locker`, `stun_locked_steps`, `stun_lock_around`, `stun_lock_exit`, `trace_stun_lock`.
  - `combat/fight.cc`: `retreat_step`, `want_home`, and `retreat`'s cast branch.
  - `combat/guard.cc`: `lock_out` in `work_guard` and `work_cover`.
  - `economy/bank.cc` `continue_recall`: the recall-home keep is refused while locked. This hunk is separate from
    M5-e's in the same function.
  - Declarations in bot_parts.h; `unity.cpp`.
- **Behaviour:** Prism only. An enemy counts as a "locker" if it has a stun ready on its next turn, that turn falls
  before ours, and the stun plus its following turn's casts and attacks (with the stun slot spent) would kill us, once
  the other threats' blows and two camp phases are added. Lockers can be seen, tracked, or remembered for one ability
  cooldown (growing a step a turn, plus dashes). Spawn tiles are excluded.
  - Inside a lethal lock, `want_home` sends the Prism away, unless `HoldAt::keeps_us`.
  - `retreat_step` tries locked steps after every other step except the `last` ones.
  - With no walk out, the retreat casts at the sole visible locker (`cast_at_enemies_for_escape`).
  - The Prism's work steps avoid locked tiles unless a hold there outlasts the lock.
  - A recall home is not kept while locked, since a stun cancels it.
- **Evidence:**
  - Alone on ocean: 50.7 (49.7-51.7). It fires about 1.5 turns a game, and Prism deaths did not move.
  - On prismhold: +0.5, +0.7 and +0.4 on three blocks, +0.5 over 29,696 games. Not significant.
  - Out-of-fuel turns rose by +20-50 per 10k games.
  - macro4's independent stun-window threat model (gallq, g1) was also level and cost fuel.
- **Overlap:** none in the base. Its case may be stronger on the base than on ocean, since B1 keeps the Prism holding
  in sight of enemies, which is where a lock applies. It also interacts with **B1**: allies decide whether to yield
  from B1's harm test, while the Prism decides whether to leave from this lock test, and the two can disagree,
  leaving a group emptied for nobody.
- **Classification:** CONSIDER. It is mechanical and rule-derived, but the evidence is within noise, it costs fuel,
  and it interacts with B1.
- **Merge notes:**
  - Three `retreat_step` hunks fail on the base and need a hand merge:
    - Combine the early returns as `if (!locked && !safety.avoid_within(...)) { base's beside_held descend, else
      step_towards; return; }`.
    - Likewise `if (!locked && !walk_dash && !test(avoid, here)) { base's held descend; step_towards }`.
    - Add `Option::locked` next to the base's `Option::held`.
    - Rename macro5's deferred index array, `held`, which clashes with the base's `const bitboard* held` (for
      example to `locked_order`).
    - The sort keys combine: the base's `held` key, and macro5's partition of locked options ahead of `last`.
  - `work_guard`'s hunk applies only with fuzz 1, on the line after the base's `in.avoid` edit. Check it by hand.
  - The rest apply. `lock_out` is Prism-only and the base's held tiles are non-Prism-only, so they never meet.
  - Its `retreat()` hunk sits next to K2a's `flee_camps` call: merge by hand.
  - Check out-of-fuel turns at 100k.

#### M5-d: hold-sole's threat-gated yield (DROP)
- **Source:** `economy/capture.cc` `yield_holder` and `yield_steps`, with `yield_capture` rebuilt on them;
  `prism_keeps_hold` and `prism_stays`.
- **Behaviour:** when hit or threatened, a co-holder steps off a Prism's hold only if all of these hold:
  - the Prism keeps it (fit, `focus_holder`, no real recall or teleport) and the hold counts;
  - no strike is possible;
  - a tile is free;
  - the Prism has acted this round, or nothing threatens its tile.

  The step must be no more exposed than staying (`Safety::bound`, least exposed first).
- **Evidence:** hold-sole 54.9 against hold-safe 55.1 on dev: level. It fired in about 4% of the shared payouts.
- **Overlap:** the base's **B4** `yield_capture` already steps a co-holder off a sole Prism's hold under threat and
  when hit, priced by the step guard placed just before, and then runs the strike search. Its gate is B1's verdict.
- **Classification:** DROP. It was level, and the base has its own yield under threat.

#### M5-e: hold-sole2's capture-recall co-holder step-off (DROP)
- **Source:** `economy/bank.cc` `continue_recall`.
- **Behaviour:** a co-holder whose capture recall would keep it on a hold that a `focus_holder` Prism keeps skips the
  `capture_recall` keep when a step-off tile exists. It cancels the recall and steps off.
- **Evidence:** M5-e and M5-f together gave +2.2 over hold-safe, at 2x, across four blocks. They have no separate win
  rates. The smoke traces of shared payouts credit 48% of the shares to recall co-holders and 36% to transit: a
  cause split, not a win-rate split.
- **Overlap:** the base's **B5** covers it.
  - For a co-holder, `capture_recall` returns false when a sole Prism holds or `prism_coming`, `continue_recall`
    cancels the recall, and `yield_capture` steps off. When `holding_capture` is false, `yields_to_prism` cancels it.
  - What remains is a Prism B1 calls threatened, where staying is deliberate, and bank or shop recalls under
    `want_home`. hold7 covered those and was level.
  - hold6's trace leaves 13 shared payouts in 48 games.
- **Classification:** DROP, covered by B5.

#### M5-f: hold-sole2's route tie-break (CONSIDER, C6: low, conditional)
- **Source:** `model/pathing.cc` `closer_neighbours`, and `route()`'s first steps; macro5's own `prism_hold_tiles`.
  That function shares the base's name but has a different signature and test (a counting hold with one holder).
- **Behaviour:** among equally short steps, those onto a hold the Prism keeps alone go last. Not under a bush threat.
- **Evidence:** the transit share of hold-sole2's +2.2 (see M5-e). No win rate of its own.
- **Overlap:** **B4** covers less than the first plan said. With no enemy in sight, these branches walk without the
  held-tile guard:
  - `local_support` and `willow_independent_heal_step` (bot.cc:428/431, before any `guard_steps`);
  - `join_marcella_capture` and `take_capture_handoff` (bot.cc:466/471);
  - `guard_turn` and `chase_with_guard`, which take `strike_guard`, the step guard saved at bot.cc:486 before
    `guard_work`;
  - in `retreat`, every move except `retreat_step`'s: `flee_camps`, `escape_walk` and the dash retreats.

  A tie-break also costs no detour, which the base's hard guard can.
- **Classification:** CONSIDER, low. The leak is small (13 shared payouts in 48 games). Build it only if a debug
  trace of shared payouts by branch shows transit splits through those branches.
- **Merge notes:** port macro5's two pathing.cc hunks, but on the base's `prism_hold_tiles`, memoised per round and
  observation. Pathing calls it mid-search, and the base's version calls `sole_capture_holder` each time. Drop
  macro5's own `prism_hold_tiles`.

### macro4 (handfc, 55.9% normal / 56.3% of 39,936 at 2x)

Steps:
- hub1 53.2 → hub2 54.8 (dev+cf; team-view Q value together with the `hub_net` hand-over gate, allies' premium still
  on; +1.6) → hubQ 55.8 (allies' premium removed; hubA 50.9).
- q-gate 55.8, with ocean's sole-holder gate restored.
- hand 56.6 dev / 56.0 cf+fr, a five-part bundle (+0.8 / +0.5).
- hand2 level; handfc = hand without its ablation scaffolding.
- Ablations: q-nohand 51.1 (no step-off for the Prism at all); q-r0 53.4 (`Hub::on()` true without a premium and the
  late-hold `hub_net` gate removed, so it measures the premium in the value plus the gate); take 54.2 (the takeover
  generalised to any champion).

#### M4-a1: Prism 'Q' collection of allies' held captures, as a mechanism (DROP)
- **Source:** `economy/farm.cc` 'Q' block after the 'T' loop (`collect`, `known_at`); `memo.collected`; the
  `chosen.mode != 'Q'` recall-out exclusion; `economy/hub.cc` `hub_payout`.
- **Behaviour:** a Prism under no held channel, above the hurt line and with rho > 0 prices three kinds of group:
  - an ally's claimed or held cleared gem group, including holders we can't see, read from their posted tiles, and
    with no reach cap;
  - its last collection;
  - any cleared group allies stand on.

  Each must not be the enemy's, not a Monolith, short of the win, and with time to bank. On a multi-tile group it
  joins before the ally's payout. Otherwise it holds afresh where the ally hands over. The hand step's "unheld Q on
  our own claim once the ally leaves it" is the base's 'L'.
- **Evidence:** hubQ and q-gate 55.8; hand 56.6 / 56.0.
- **Overlap:** for multi-tile groups this is **B2 'G'**. Taking a fresh hold from an ally that leaves is 'L' with
  **B3**. Its value goes to C1, its alive-group case to C2, and its full-group hand-over to K3.
- **Classification:** DROP as a parallel mechanism. Two pickers and two hand-over predicates would fight over the same
  holds. Unseen holders and the missing cap go with it.

#### M4-a2: the Prism collects an ally's clear in progress (CONSIDER, C2)
- **Source:** the same 'Q' block, `c.state == CampState::alive` branch, and `collect_joins` (memory.crew).
- **Behaviour:** the group must be alive and claimed by an ally, and worked: damaged last round, or a claimer within
  attack reach. The clear takes `health / claimers' output` rounds. A Prism arriving before the clear ends joins as
  crew, only if `affordable(g)`. One arriving after takes the hold. It is gated by `hold_threatened`
  (`enemy_may_see || hold_reached`).
- **Evidence:** part of hand's five-part bundle. No separate test.
- **Overlap:** the base's Prism can join an ally's claimed alive group as crew ('J'), valued at its share. The base
  then lands the whole capture through **B1**, 'G' or K3.
- **Classification:** CONSIDER. Its effect can't be separated from the rest of hand, and it overlaps 'J'. Test it with
  C3's J pricing, or after it.
- **Merge notes:** port it as an 'L'-like branch for alive groups in the base's carry loop, valued with C1's worth,
  within `carry_reach`. Make sure 'J' and this branch don't both claim the same group in one turn.

#### M4-a3: team-marginal value with the rho premium (CONSIDER, C1, with M4-b2)
- **Source:** `economy/hub.cc`: `camp_gem_density`, `gem_damage_rate`, `hub_premium` (`params::hub_rho_most = 2`),
  `hub_factor`, `champion_gem_rate` and `hub_net`. The 'Q' worth itself is in farm.cc.
- **Behaviour:** one carried gem adds `1.5 x (1.5 + 1) / 8` damage a round, converted to gems at the map's gems per
  camp health point and integrated over the rounds it stays carried, discounted by the farm horizon:
  `rho = d h ln(1 + H/h)`, clamped to [0, 2]. It is about 1 early and about 0.1 late. A collection's worth is then the
  team's marginal gain: `gems x (hub_factor - 1) + holder gain + freed ally rounds x work rate`, over the Prism's
  rounds. The ally would have scored the gems itself.
- **Evidence:**
  - hub1 to hub2, +1.6 over 19,456 games at 2x, changed the value and the hand-over gate together, with the allies'
    premium still on.
  - rho x0.5 gave 55.0 and x2 gave 54.4, against 55.8.
  - q-r0's 53.4 is the premium in the value plus the gates (see the steps above), not the premium alone.
- **Overlap:** the base's 'G' and 'L' value the whole capture, `rate(gems + per_gold x gold, rounds)`. hub1 had the
  same shape, though the base counts gems once where hub1 counted them `(1 + rho)` times. Early, while rho is near 1,
  the two roughly agree; late, the base over-values carries.
- **Classification:** CONSIDER. The evidence is strong but comes from another framework. It could undo part of
  macro1-carry's gain. `hub_rho_most = 2` is a hand-set clamp that binds on gem-dense maps.
- **Merge spec:** port only the six hub.cc functions (drop `Hub`, `team_hub` and the hand-over). In `farm_turn`'s
  carry loop, with `cycle_rate` = `best_value` before the takeover loops:
  - **'G'** (joining before the payout): `gems x (hub_factor(rho, timer, timer) - 1) + holder gain
    + (timer - walk) x cycle_rate`, over `timer` rounds.
  - **'L' on an empty group** left to us: `(1 + rho) x gems + per_gold x gold`, over `walk + capture_rounds`.
  - **'L' on a held group.** This covers the base's claimed leave (the Prism misses the payout) and K3's full groups.
    Use macro4's late form: `gems x (hub_factor(rho, timer, max(timer, walk + capture_rounds)) - 1) + gain`, with no
    freed rounds. Take the pick only if `hub_net > 0`.
  - **M4-b2:** put the same `hub_net > 0` test on the ally side, in `leave_for_prism`'s claimed branch (and K3's
    `full` returns), so both sides agree.
  - B2's gates stay.

#### M4-b1: hand-over of full and single-tile holds (KEEP, K3, rebuilt in the base)
- **Source in macro4:** `economy/hub.cc` `hub_hands_over` (its `single` branch, from the hand step,
  patches/hand-on-qgate.diff) and `hub_hands_at`; its caller in `yield_capture`.
- **Behaviour in macro4:** an ally on a counting hold that the Prism claims (and is not yet on) steps off at once if
  the group is a single tile and the Prism is due before the ally's payout. The Prism's hold restarts on arrival
  whichever way it goes, so the ally's remaining rounds there buy nothing. On a full *multi-tile* group it leaves only
  when the Prism stands beside it, or at the last turn before the payout. It does this only when the premium pays and
  no enemy may see or reach the tile.
- **Evidence:**
  - Nothing isolates this rule. It is one of five changes in `hand`, which gained +0.8 on dev and +0.5 on cf+fr at 2x
    over q-gate. The other four:
    - unheld Q on our own claim;
    - joining an alive clear if affordable;
    - the `at_once` `hub_net` gate;
    - freed rounds counted from the end of the clear.
  - In hand's smoke, Q arrivals went from 39% to 47%, and Q gems paid to the Prism from 38 to 63 a game.
  - (`q-nohand` is not evidence for this rule. It ablates every step-off for the Prism, on q-gate, which predates the
    single-tile rule.)
- **Overlap: a real gap in the base.**
  - On the Prism's side, `prism_takeover` fails when `prism_carries` finds no calm free tile. So 'G' and 'L' never
    pick a full group, and the ally's claimed branch never fires on one.
  - On the ally's side, both `leave_for_prism` branches keep the ally on, and pin it (`kept_group`), when the Prism is
    due before the payout. That assumes a join that can't happen on a full group.
  - An unheld single-tile group the Prism claims is still taken by a nearer ally. The rule is `walk - slack <
    capture_rounds - 1 + our walk`, which assumes a join. This is M4-b4's single-tile case.
- **Classification:** KEEP. It closes a structural gap in the base's own mechanism. The base already hands over a
  group the Prism reaches *after* the payout, at a longer delay. No new constant.

  For multi-tile groups it differs from macro4's rule: it leaves as soon as the Prism is due, not when the Prism stands
  beside the group. The remaining holders keep the count, and the Prism then joins by 'G' at the original payout.
- **Merge spec:**
  - (a) **Ally side,** `economy/capture.cc` `leave_for_prism`:
    - Let `full = held && free_tiles(G.tiles()).is_empty()`. Our own tile is not free.
    - Top `Leave::no` test (line 463): when `full`, ignore the `kept_group` pin, which may be from an earlier round.
      Keep the `payout - round < 2` and `lapsed` tests.
    - Claimed branch, after the `carry_reach` checks and before the payout comparison: return `Leave::claimed` when
      `full`. Also return it when `!held && G.members.size() == 1` (the single-tile case above).
    - Near branch: where `held && eta + slack < rounds` now keeps us and sets `kept_group`, return `Leave::near` when
      `full`, without setting the pin.
    - The lapse logic stays. A Prism that never comes hands the group back after `capture_time`.
  - (b) **Prism side,** `farm_turn`'s carry loop:
    - For a held gem group where `prism_takeover` fails only for want of a free tile, price an 'L' pick.
    - Require `fresh_ally_capture(world, G) >= 2`, the ally side's floor.
    - Require every ally on it to be a non-Prism that is visible, not tribute-channelling and not `held_back`.
    - Use a `prism_carries` variant whose goal is `G.tiles()` less camp-hit tiles, keeping occupied tiles. Every
      other gate stays: `enemy_seen`, `enemy_may_see` at any member, health, the win, time to bank.
    - Value it at `walk + capture_rounds(world)` rounds, as 'L' already is (C1 reprices it if kept).
    - Post the claim. The ally's claimed branch then fires, and the existing 'L' path for an unheld claim continues
      it (`g == memory.claim && memo.carry_group == g`).
    - **Walk goal:** every goal tile is occupied when the pick is made. Check that
      `step_towards(off_zone(carry_goal), ...)` advances. If it doesn't, aim at `G.adjacent()` until a tile frees.
  - (c) Nothing else changes. When `left_for_prism` is true, `holding_capture_now` returns false and `continue_recall`
    takes the `yields_to_prism` branch, so a capture recall is already cancelled. The farm walks the ally off. B4's
    guards keep it off afterwards.
  - **Debug batch before the A/B.** Count per game:
    - the new `full` and single-tile returns;
    - the Prism's arrivals and payouts on handed groups;
    - the payout delay, `walk + capture_rounds - timer`.

    K3(b) is the base's first pick that delays an ally's payout while valuing the whole capture. On a single tile
    with the Prism due before the payout, the delay is under `capture_time`, which is less than the base's claimed
    leave already accepts, but measure it. If the rule fires less than about once a game, expect a level result.
    Under the merge rule it then goes to CONSIDER.

#### M4-b2: the last-turn hand-over, gated on the premium (CONSIDER, part of C1)
- **Source:** `hub_hands_over`'s `timer > 1` path, and `hub_hands_at` → `hub_gain` → `hub_net`.
- **Behaviour:** a Prism due only after the payout gets the hold at the ally's last turn, and only if
  `gems x (hub_factor - 1) - theirs x champion_gem_rate > 0`.
- **Overlap:** the base's claimed leave does this unconditionally, at once, within `carry_reach`.
- **Classification:** CONSIDER, as C1's gate on `leave_for_prism`'s claimed branch. Leaving at the last turn rather
  than at once would also keep the ally's hold as a fallback if the Prism re-picks.

#### M4-b3: `hub_awaited` in `capture_recall` (DROP)
Covered by **B5**: `prism_coming`, plus the `left_for_prism` path through `holding_capture_now` and
`yields_to_prism`. K3(c) extends that path to full groups.

#### M4-b4: allies' farm skips a cleared group the Prism claims, `hub_claim` (single tile folded into K3; rest DROP)
The single-tile part is K3(a)'s `!held && G.members.size() == 1` return. For multi-tile groups the base's claimed
branch already decides, with a timing rule, when a much nearer ally should take the group, and the Prism can join
it there by 'G'. That part is DROP.

### macro6 (carry3, 55.3% normal / 55.8% of 51,200 at 2x)

Steps:
- carry 54.1 (53.9 held out) → carry2 55.2 (55.0 held out), J priced → carry3 56.0 / 56.2 / 55.2 / 55.0 / 56.5,
  S/K/C priced.
- K probes: x0.5 54.2, x2 55.6, x4 54.9.
- carry5 (audit fixes and a health gate): 55.3, worse. carry4 (Focus-aware kill value): level.

#### M6-a: carry, the holder premium and the Prism's 'T' takeover (DROP)
- **Source:** `economy/capture.cc`:
  - `keeps_bag` (with a health gate) and `carried_bonus`;
  - `holder_value`'s `gems x (1 + carried_bonus)` and `multiplies(world, ...)`;
  - `keeps_bag` in `sole_capture_holder`, redundant with `fit_on`'s identical health line;
  - `takes_over` true for a Prism;
  - `may_take_over` gated on `keeps_bag` and allowing `sole->is_self` for every champion.
- **Behaviour:** at the holder price of 0.3 the premium is exactly M5-a's, +1.6875 gems a gem, but health-gated. The
  Prism takes over allies' gem holds by the 'T' path (under `capture_time` steps, `takeover_worth`).
- **Evidence:** carry +4.1.
- **Overlap:** the holder premium is covered by **B1**, as for M5-a. The 'T' takeover duplicates **B2 'G'**, which
  reaches further.
- **Classification:** DROP, with the `may_take_over` change.

#### M6-bc: carry2 and carry3, Focus-priced farm values (CONSIDER, C3)
- **Source:** `economy/farm.cc` `farm_turn`:
  - `keeper`, `keeper_price = prices().per_gold`, `keep_most`, `keep_bonus` and `bound_tribute`;
  - the J branch: `plain`, `carry`, `carry_most`, the moved kite-hit check, and the health gate on `carry`;
  - S/K/C worth `plain + carried`;
  - every prune bound: `unweighed_beaten`, `most_tribute`, `p.tribute_gold`, `join_bound`, `beaten_near`, and the
    claimed bound.
- **Behaviour:** for a Prism keeping its bag, each gem of a non-Monolith group short of the win is worth
  `1 + per_gold x 5.625` in its solo, kited, crew and risky values. On a join, the Focus is added whole, not as a
  share. A joining Prism takes the whole hold, and `carry` is zeroed if the clear's expected damage would leave it
  below the hurt line. When `carry > 0`, the J rate's rounds gain `hold = cap_rounds`, so the plain share is also
  discounted by the hold.
- **Evidence:** carry2 +1.1 and carry3 +1.0, incremental at 2x, on two sets each.
- **Counter-evidence:** pricing the Prism toward its own clears lost twice:
  - macro5's prismhold2 (Focus premium in the Prism's own farm and kill values): 52.2 against 54.6, -2.4;
  - macro4's aoe (a clear model that re-steers the Prism toward clearing): -3.2.

  The base's lever is reallocation ("reallocate, don't redirect").
- **Overlap:** the base's **B6** `gold_part = 0.5` is a cruder version of the same pricing. For a solo pick, the base's
  gold weight relative to a gem is `0.5 per_gold` and macro6's is `per_gold / (1 + 5.625 per_gold)`, equal at
  `per_gold ≈ 0.18`. They really differ in two places:
  - **J**, where the base prices the Prism's join at a share although B1, 'G' and K3 hand it the whole capture;
  - the fixed comparators the absolute scale moves against: 'T', 'G', 'L' and the shared join.

  Removing `gold_part` doubles gold's weight in 'G', 'L', 'T' and the shared join for a keeping Prism. Unless 'G' and
  'L' get the same bonus, the swap tilts the Prism from carrying allies' captures to its own clears. macro6 saw that
  shift: Prism solo captures went from 65 to 105.
- **Classification:** CONSIDER, tested as a swap for `gold_part`, with 'G' and 'L' carrying the same `carried_bonus`.
- **Merge notes:**
  - All 17 of macro6's farm.cc hunks apply to the base textually, with offsets. Only capture.cc's
    `sole_capture_holder` hunk fails, and it goes with M6-a. The danger is a silent clean apply that **stacks on
    `gold_part`**: remove it by hand at farm.cc:959-960 and in the crystal toll at 1937. Keep the base's `keeps` and
    `taking_over`.
  - Port `keeps_bag` and `carried_bonus` into capture.cc, but not their use in `holder_value` (M6-a).
  - Add `gems x carried_bonus` to the 'G' and 'L' worth in the carry loop.

### macro3 (eoq2, 52.3% normal / 53.1% of 30,720 at 2x)

#### M3-a: EOQ bank floor with an online carrier hazard (KEEP, K1)
- **Source:**
  - `economy/bank.cc`: `CarrierRecord carriers`, `note_carriers`, `carrier_hazard`, `bank_floor`, and `bankable_bag`
    using `bank_floor` in place of `params::min_bank`.
  - `economy/shop.cc` `gem_income_rate`.
  - `params.h`: removes `min_bank = 25`; adds `carrier_hazard = 0.86e-3`, measured on 10,240 games, and
    `bag_swing = 2`, by the rules.
  - `bot.cc` `play_turn`: `note_carriers(world)` before `note_upkeep`.
  - bot_parts.h declarations.
- **Behaviour:** a non-winning, non-closing bag is banked only once it holds
  `Q* = D x sqrt(2T / (hazard x bag_swing))` gems, clamped to
  `[10, max(10, min(gems_short, 10 x bag_rounds_left))]`, where 10 is the gems a tribute turn takes. Here:
  - D is the champion's own gem income a turn alive;
  - T is the way to an altar (a walk, or a recall then the walk), plus one tribute turn, plus the way back;
  - the hazard is a Gamma posterior over the team's carrier deaths per carrying round (prior: one death at the
    measured rate).

  High-income champions far from an altar carry 40-70 gems; anyone beside an altar banks 10 or more. The Prism is
  unaffected while it keeps its gems: `banks_bag` needs `!retaining_gems`, and a Prism that no longer keeps them is
  winning or closing, which bypasses the floor. `note_carriers` does count the keeping Prism's carrying rounds and
  deaths, which dominate the posterior on the base. That was equally true on ocean, and macro3's per-champion hazard
  (eoq4) was worse, so it is no reason to change K1.
- **Evidence:**
  - eoq2: 53.4 / 53.1 / 52.8 on sets A, B and C (30,720 games); 53.4 on 5,120 varied maps.
  - Decomposition on set A: only raising the floor gave 51.8, only lowering it 50.3, both (fixed hazard) 52.5, online
    hazard 53.4.
  - Normal fuel: 52.3 (51.8-52.8) of 40,960. Out-of-fuel turns level at 2x.
- **Overlap:** none. On the base, allies hand more captures to the Prism, so their D, and with it their floor, falls.
  That is the consistent direction.
- **Classification:** KEEP. It is independent, replaces a hand-set constant with a derived quantity, held up on three
  sets plus varied maps, and costs little fuel (memoised per round, tile, bag and observation). It must show a gain.
  Expect about +1.5 to +2, resolvable at 20k.
- **Merge notes:** from the bot root,
  `diff -ruN ocean-main-b7c87cf/src macro3-eoq2/src | patch -p1` applies cleanly, and the result builds.

### macro2 (lstep, 50.7% normal / 50.81% of 71,680 at 2x)

Four rule-derived fixes, each level alone at 10-25k games on ocean. combo (a+b+c) scored 50.53 of 51,200, and lstep
(combo + d) 50.76 of 51,200, both at 2x. At normal fuel the package scored 50.7 of 40,960 (CI 50.2-51.2). All four
are independent of the Prism lever.

From the bot root, `diff -ruN ocean-main-b7c87cf/src macro2-lstep/src | patch -p1` applies to the base, on top of K1
too, with fuzz on support.cc and offsets in capture.cc and fight.cc, and the stack builds in release. To split K2a from
K2b, take fight.cc's `flee_camps` and `retreat` hunks alone for K2a.

#### M2-d: no lethal camp flight, "lstep" (KEEP, K2a: a mechanical bug fix)
- **Source:** `combat/fight.cc` `flee_camps`, with its signature gaining `bool& deferred`; the caller in `retreat`.
- **Behaviour:** `flee_camps` now prefers a step `Safety::lethal` does not flag over any lethal one, whatever the
  camp damage. If the best exit is lethal because of enemies, not the camps alone, and some `retreat_step` step is
  non-lethal with a damage bound under our health, it defers to `retreat_step`.
- **Evidence:** +118 wins paired over 51,200 games against combo, 50.53 to 50.76. Found in a replay where a 228-gem
  Prism fled a 20-damage wolf into a one-cast kill.
- **Overlap:** none. The base edits `retreat_step`, which this only calls.
- **Classification:** KEEP, under the bug-fix exception. The old code took a step it could see was lethal while a
  safe one existed. There is no trade-off: it gives up only camp damage that the deferred step's bound shows we
  survive. It merges at a level win rate, and is rejected only if significantly negative.

#### M2-c: the hold cast (KEEP, K2b: must show a gain)
- **Source:** `economy/capture.cc` `hold_capture`.
- **Behaviour:** a holder with no camp its basic attack reaches casts at the nearest alive group within cast reach.
  The group must not be the held one, and must have no sleeping strikers (strength 0, or awake with none asleep), so
  the cast wakes nothing. An excludes-walking cast costs a holder no walk, and a ready slot left uncast loses the
  round. Ocean's `hold_capture` already casts at a camp its basic reaches. This extends that behaviour to cast range.
- **Evidence:** 50.0 of 10,240. Level, and in combo. It fired about once in 3 games on ocean.
- **Overlap:** none. It should fire more on the base, whose Prism holds far more (B1). macro2's duelr showed that
  keeping the Prism's spells off camps costs about 11 points.
- **Classification:** KEEP, but not a pure bug fix. It spends a cooldown (`cast_at_camp` has no enemy check) that an
  arriving enemy might have met. It must show a gain.

#### M2-a: Willow's heal order, "medic1" (KEEP, K2b: must show a gain)
- **Source:**
  - `combat/self_abilities.cc` and `.h`: `heal_value`, `HealMate`, `heal_mate`, `heal_before`; `HealTarget::value`
    and `urgent`; `HealGate::urgent`; `heal_target`, and `heal_ally`'s candidate sort.
  - `combat/support.cc` `heal_station`, and the support formation step choice.
- **Behaviour:** heal candidates are ranked by:
  - urgency first (every blow before our next turn could fell them; the support mate first among the urgent);
  - then the mate while it waits in recovery. This replaces the formation's old exact-tie rule, "the mate first if it
    requests support".
  - then farm rounds saved (`gain / usable health x heal_trip`);
  - then the lowest health fraction.

  The old order was most restored first. Willow only.
- **Evidence:** 50.2 of 24,496 (held out 49.3-50.9). Level, and in combo.
- **Overlap:** none. Its formation hunk sits in the loop where the base added `on_held`. It merges cleanly, and the
  two do not interact: `on_held` filters tiles and `heal_before` ranks heals.
- **Classification:** KEEP, but a re-prioritisation, not a bug fix. It must show a gain.

#### M2-b: two casts on a double turn, "duelm" (KEEP, K2b: must show a gain)
- **Source:** `model/safety.cc`: `add_two_casts`, called from `moved_strike` and the two-turn `threat_strike`; the
  `most_damage` memo takes the larger of strike plus basic and both casts; `Reach::build_ways` adds the two-cast
  entries when `twice`. Comments in safety.h.
- **Behaviour:** an enemy with two turns before our next (turn-order parity, every other round) may cast one slot on
  each turn. The rules allow one cast a turn. Safety's threats, its reach and its damage ceiling now include that sum.
- **Evidence:** 50.0 of 10,240, 50.0 of 15,360 held out. Level, and in combo. Its parent duel lost (39.1) because of
  the stun reserve (duelr 39.3).
- **Overlap:** none. It leaves B1's `turns_to_harm_idle` alone, since that function runs the fight simulation. It
  does change `threatened`, `any_threat` and `avoid`, which `capture_recall`, `yield_capture`, retreat and
  `want_home` read.
- **Classification:** KEEP. It corrects a model gap against a rule, but adds caution, so it is not a no-trade-off bug
  fix. It must show a gain.

### Leftovers

#### L-1: macro6-mono, the carry price extended to the Monolith (CONSIDER, C7, only after C3)
- **Source:** `/home/ubuntu/wt/macro6-work/mono/mono.diff`.
  - capture.cc: `holds_whole`, and an `outvalues_holders` Monolith branch.
  - farm.cc: `keep_bonus(int g)` drops the `!G.has_monolith` exclusion, and zeroes the bonus on a cleared group with
    no free tile that we are not on.
- **Evidence:** 80 debug games, near-identical to carry3. It rarely fires: a Prism bag plus a Monolith usually wins,
  and the win exemption then removes the bonus.
- **Overlap:** the `outvalues_holders` part needs M6-a, which is dropped. **B1** already gives a fit Prism on a
  Monolith tile the whole hold. The "no free tile, no Focus" rule contradicts **K3**.
- **Classification:** CONSIDER. Port only the farm.cc Monolith part, without the free-tile rule, and only if C3 is
  kept.

#### L-2: macro5-hold-sole3, more dilution-leak fixes (DROP)
- **Source:** the scratchpad `hold-sole/hold-sole3.diff`.
  - `prism_hold`, `paid_hold_tiles`, and `prism_stays(payout)`.
  - Payout-round transit detours in pathing: `route`, `closer_neighbours`, `step_closer`, dash landings and
    `paid_wait_`.
  - `continue_recall` stepping any recall co-holder off at the payout, whatever the recall is for.
- **Evidence:** 51.8% of 512 against sole2. Noise.
- **Overlap:** its recall rework is the base's hold7, which was level. Its transit rule is a softer variant of M5-f
  (C6).
- **Classification:** DROP.

#### L-3: macro3-eoq5, the chain limit replaced by a holding cost (CONSIDER, C5, after K1)
- **Source:**
  - `economy/bank.cc` `may_chain` drops the `bag_at_stake >= chain_bag_limit` test.
  - `economy/farm.cc`, banking instance: `hold = bag_swing x carrier_hazard() x bag_at_stake`, in gems a round like
    `best_value`'s rate, lowers best_value against `from_altar_value` in the threshold and in the bank decision.
  - `params::chain_bag_limit = 26` removed.
- **Evidence:** 53.1 at 2x against eoq2's 53.4 on the same set. Level.
- **Classification:** CONSIDER. It is K1's consistent next step and removes the last hand-set bag constant. No gain
  shown.

## KEEP merge queue

Each step is gated against the previous step, frozen, under the merge rule above. A step that fails moves to the end
of the CONSIDER queue, and the next step goes on without it.

| Step | Changes | Port | Gate |
|---|---|---|---|
| K1 | M3-a, bank floor | `patch -p1` of macro3-eoq2's diff, clean | Must gain. 20,480 games; expect +1.5 to +2. |
| K2a | M2-d, lethal camp flight | macro2-lstep's two fight.cc hunks (`flee_camps`, `retreat`) | Bug fix: merge unless significantly negative. 20,480 games. |
| K2b | M2-c, M2-a, M2-b | the rest of macro2-lstep's diff, clean on K1 and K2a | Must gain. Expect about +0.5, so plan on 40,960 games. If it fails as a group, all three move to CONSIDER. Under 40k, a single-piece ablation can't be read. |
| K3 | M4-b1, rebuilt | spec in M4-b1, ~40 lines in `leave_for_prism` and the carry loop | Debug batch first (firing, arrivals, payouts, delay). Then must gain, 20,480 games, extended to 40,960 if positive but unresolved. |

Why this order: K1, K2a and K2b are independent of each other and of the carry lever, and apply without conflict, so
each A/B measures one thing. K2a goes first, alone, because it merges under a different rule. K3 changes the base's
core mechanism. It goes last so that it is measured on the final economy, and so that a loss there doesn't hide the
earlier results.

## CONSIDER queue

Start these only once the KEEP queue is done. Each one is tested alone on the latest charybdis, and must show a gain
to merge.

1. **C1: M4-a3 + M4-b2.** Team-marginal value for 'G', 'L' on empty groups and 'L' on held groups (claimed leaves and
   K3's), with the `hub_net` gate on both the Prism's pick and the ally's leave. It has the strongest outside
   evidence (+1.6, value and gate together). Its risk is undoing part of macro1-carry's gain. If it loses, try the
   gate (M4-b2) alone.
2. **C2: M4-a2.** The Prism collects an ally's clear in progress. Use C1's value if C1 was kept, else the base's. Run
   it with C3's J piece, or after it.
3. **C3: M6-bc.** Swap `gold_part` for `carried_bonus` pricing on S/K/C, on J (Focus whole) and on 'G' and 'L'. Run it
   as a swap, never stacked on `gold_part`.
4. **C4: M5-c.** Prism stun-lock safety. It is independent of C1-C3, so it can run in parallel on its own copy. Check
   out-of-fuel turns at 100k.
5. **C5: L-3.** The chain limit replaced by a holding cost. Independent and cheap.
6. **C6: M5-f.** The route tie-break. Only if a shared-payout-by-branch debug trace shows transit splits in the
   unguarded branches.
7. **C7: L-1.** The Monolith carry price, farm part only, without the free-tile rule, and only if C3 was kept.
   **Dropped by user decision: fired too rarely to pass (80 debug games, 70 identical to carry3); untested.**
8. Then any KEEP step that failed its gate, in queue order.
9. **C8: K2b = M2-c + M2-a + M2-b** (failed phase 1, merge-log.md). **Restructured by user decision (phase 2):**
   M2-b (two casts on a double turn) is **dropped by user decision: adds caution; level in K2b and alone on
   macro2**. M2-c (hold cast) and M2-a (Willow heal order) are tested together as one candidate, moved to the end of
   the queue as **C10**, after C9. The original entry follows.
   Original entry: K2b failed phase 1. It was level at normal fuel on K2a over 40,960
   games: 51.4 against base where K2a had 51.65, and 58.5 against ocean where K2a had 58.4. Out-of-fuel turns rose
   about 2%. If retried, test the pieces separately: M2-b is the one with a fuel cost. Note that `camp_cast`'s
   `engagement_near` already limits M2-c's spent stun to enemies 7-8 tiles off.
10. **C9: K3 = M4-b1** (failed phase 1, merge-log.md). The built candidate is kept as `bots/variants/chy-K3`. It was
    level on K2a over 40,960 games: 51.63 against base where K2a had 51.65, and 58.33 against ocean where K2a had
    58.37. It fired about 0.26 Prism hand-overs a game, with about 7 gems a payout. Its spec still stands, with the
    audit fixes. It may matter more with C1, whose `hub_net` gate reprices exactly these 'L' picks, so retest it
    after C1 if C1 is kept.

11. **C10: M2-c + M2-a** (user decision, phase 2): the hold cast and Willow's heal order from K2b, tested together as
    one candidate on the latest charybdis, after C9. M2-b is dropped.

**One premium rule (C1 with C3).** C1's rho (from damage) and C3's `carried_bonus` (from the shard price) are two
derivations of one quantity, a carried gem's Focus. If both are kept, every Prism pick type (S, K, C, J, G and L) must
use the same premium, or the picks are compared in different units. Test whichever comes second only on top of the
first, under the first's premium. C2 uses the same premium too.
