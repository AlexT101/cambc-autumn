# Audit of the charybdis merge plan

Auditor's read of `plan.md` against the code and the logs. I diffed every bot against `variants/ocean-main-b7c87cf/src`
myself, read the base's whole diff, and dry-ran each bot's diff on a scratch copy of `charybdis-base`. I also read the
macro1-6 logs and macro4's `hand-on-qgate.diff`, and diffed macro4's `q-nohand` and `q-r0` ablations against `q-gate`.
I applied macro3's and macro2's diffs to a scratch copy, one after the other, and built the result with `cambc build --release`.
It builds. I ran no games.

Citations are `file:function` in `bots/variants/charybdis-base/src` unless a bot is named. Line numbers are the base's.

## Headline

The plan is sound in outline. Its base-coverage claims mostly hold in the code, and K1 and K2 apply and build as stated.
I found seven substantive problems:

1. **K3 is missing the unheld single-tile case (M4-b4).** For a cleared single-tile group the Prism has claimed, the
   base's claimed branch lets a nearer ally take it. K3(a) would then make that ally step off at once. The result is a
   wasted walk, and the Prism holds afresh anyway.
2. **K3's evidence is misattributed.** `q-nohand` ablates `q-gate`, which predates the single-tile rule. It also removes
   every step-off for the Prism, the base's B1/B3 yields included. `hand`'s +0.8 / +0.5 covers five changes, not three.
3. **M5-f's "only uncovered paths" list is incomplete.** Several branches walk without the base's held-tile guard.
4. **M6-bc's merge note is wrong.** All 17 of macro6's farm.cc hunks apply to the base textually. The danger is that
   they silently stack on `gold_part`, not that they conflict. The two conflicts the note names are macro4's.
5. **M6-bc's counter-evidence is missing.** macro5's prismhold2 (-2.4) and macro4's aoe (-3.2) both priced the Prism
   toward its own clears and lost.
6. **C1 and C3 price the same premium two ways.** C1 uses macro4's rho, from damage. C3 uses macro6's `carried_bonus`,
   from the shard price. Both are a carried gem's Focus.
7. **K2's gate is underpowered.** The group's expected +0.5 cannot be resolved in 20k games, so the planned ablations
   cannot be read either.

## What the base already does (B1-B7)

**AGREE, with three precisions the DROP rationales depend on:**
- **The held-tile guard is narrower than the plan implies.**
  - `prism_hold_tiles` (capture.cc:870) needs the Prism visible to us, standing on a cleared gem group, and named by
    `sole_capture_holder` from our own view.
  - The step guard adds those tiles only with an enemy in sight (guard.cc:708 `guard_steps`).
  - The work guard adds them only in `decide`'s branches after bot.cc:499 (`guard_work`).
- **The base's 'G' still bails on `enemy_seen` and on `enemy_may_see` at any member** (capture.cc:813 `prism_carries`).
  B1 dropped that gate only for the hold itself. `enemy_may_see` is true for an enemy in sight within 8, a tracked one
  possibly within 8, or an untracked one seen within `track_horizon` (3) rounds.
- **Both of `leave_for_prism`'s branches pin the ally** (`kept_group`, capture.cc:455) when the Prism is due before
  the payout, not only the near branch.

## Per-entry verdicts

### macro5

- **M5-a, holder Focus premium: DROP. AGREE.**
  - Coverage holds. `value_holder` and `outvalues_holders` return nothing for `holders(G) != 1` or a Monolith
    (macro5-hold-sole2 capture.cc). B1 has neither restriction, so it covers more groups. `fit_on` carries the same
    health line as macro6's `keeps_bag`.
  - The premium's residue:
    - takeovers while an enemy is seen or may see the group, through `pick_up`, `step_onto_cleared` and the
      `value_holder` yield. 'G' refuses these. macro1's hold5 relaxed the enemy-in-sight bail for 'G' and 'L' and was
      level (57.81 vs 57.62 of 40,960).
    - `pick_up`'s claimer race on single-tile groups. That race is the K3 gap below.
  - Correct the rationale's wording. "prismhold's gain came from holds `sole_capture_holder` refused because an unseen
    enemy might see the Prism" is an inference, not a measurement. macro5 measured only that 28% of Prism-damaged
    captures paid it nothing.
- **M5-b, Prism pick-up: DROP. AGREE.** 'G' covers it, up to 12 steps (`carry_reach`).
- **M5-c, prismsafe: CONSIDER. AGREE.**
  - The merge notes are accurate. Dry-run on the base: `retreat_step` hunks 1, 2 and 4 fail, and the rest apply.
  - Add: guard.cc's `work_guard` hunk applies only with fuzz 1, on the line after the base's `in.avoid` edit. Check it
    by hand.
  - Add: the case may be stronger on the base than on ocean. B1 now keeps the Prism holding in sight of enemies,
    which is where a stun lock applies.
- **M5-d, hold-sole's threat-gated yield: DROP. AGREE.** Level: hold-sole 54.9 against hold-safe 55.1 on dev. The base
  steps off under threat through the step guard (capture.cc:611 `yield_capture`).
- **M5-e, recall step-off: DROP. AGREE.**
  - The code confirms coverage. For a co-holder, capture.cc:919 `capture_recall` returns false when a sole Prism holds
    or `prism_coming`. bank.cc `continue_recall` then cancels the recall. When `holding_capture` is false,
    `yields_to_prism` cancels it.
  - The residue is the Prism that B1 calls threatened, where staying on is deliberate (hold2), and bank or shop
    recalls when `want_home`. hold7 covered those and was level.
  - Evidence wording: the +2.2 is M5-e and M5-f together. The "about half" split comes from shared-payout causes in
    hold-sole's smoke traces, not from win rate.
- **M5-f, route tie-break: DROP. DISAGREE with the rationale; reclassify as CONSIDER, low, conditional.**
  - Branches with no held-tile guard when no enemy is in sight:
    - `local_support` and `willow_independent_heal_step` (bot.cc:428/431, before any `guard_steps`);
    - `join_marcella_capture` and `take_capture_handoff` (bot.cc:466/471);
    - `guard_turn` and `chase_with_guard`, which take `strike_guard`, the step guard saved before `guard_work`
      (bot.cc:486, 516);
    - in `retreat`, every move except `retreat_step`'s: `flee_camps`, `escape_walk` and the dash retreats
      (fight.cc:1380).
  - A tie-break also costs no detour, which the base's hard guard can. That matters in corridors, where passing
    through off the payout round is harmless.
  - The leak is small. hold6 traced 13 shared payouts in 48 games. So build it only if a debug trace of shared
    payouts by branch shows transit splits left.
  - Port it as macro5 wrote it, in pathing.cc `closer_neighbours` and `route()`'s first steps, but on the base's
    `prism_hold_tiles` and memoised per round and observation. Pathing calls it mid-search, and the base's version
    calls `sole_capture_holder` each time.

### macro4

- **M4-a1, Q as a mechanism: DROP. AGREE.** Two features of Q go with it unmentioned: holds by allies we can't see,
  read from their posted tiles (`known_at`), and no 12-step cap. 'G' needs a visible holder within `carry_reach`.
- **M4-a2, Q on alive groups: CONSIDER. AGREE.**
- **M4-a3, team-marginal value: CONSIDER, C1. AGREE with the class; amend the spec.**
  - The merge notes price only 'G' and 'L' on an empty group. They must also price 'L' on a **held** group: the
    base's claimed leave, where the Prism misses the payout, and K3's full groups. Use macro4's late form:
    `gems x (hub_factor(rho, timer, max(timer, walk + capture_rounds)) - 1) + gain`, with no freed rounds. Its
    `hub_net > 0` gate (M4-b2) belongs on the same pick.
  - hub1 to hub2's +1.6 changed the value and the hand-over gate together, so pairing them as C1 is right. Say so.
  - `q-r0` is not "rho 0 inside Q". It also made `Hub::on()` true without a premium and removed the `hub_net` gate on
    late holds. Its 53.4 is the premium in the value plus the gate, not the premium alone.
  - The clamp `hub_rho_most = 2` binds on gem-dense maps (macro4's 07:40 review). It is a hand-set number.
- **M4-b1, full and single-tile hand-over: KEEP, K3. AGREE with KEEP; DISAGREE with the evidence and the spec as
  written.** See amendments 1-6.
  - The gap is real. capture.cc:836 `prism_takeover` returns false when `prism_carries` finds no calm free tile. So
    'G' and 'L' never pick a full group, so the ally's claimed branch never fires on one.
  - The evidence is wrong.
    - `q-nohand` ablates `q-gate`, which predates the single-tile rule. It returns false for any Prism holder in
      `yield_capture` ("nobody steps off for Prism"), so it measures the step-off mechanism the base already has.
    - The `hand` step bundles five changes:
      - the single-tile hand-over;
      - unheld Q on our own claim;
      - joining an alive clear if affordable;
      - the `at_once` `hub_net` gate;
      - freed rounds counted from the end of the clear.

      K3's own share of +0.8 / +0.5 is unknown.
  - macro4 leaves a full **multi-tile** group at once only when the Prism stands beside it. K3(a) leaves as soon as
    the Prism is due before the payout. That is fine: the remaining holders keep the count, and the Prism then joins
    by 'G' at the original payout. But it is a different rule from macro4's, not a port of it.
- **M4-b2, last-turn gated hand-over: CONSIDER, with C1. AGREE.**
- **M4-b3, `hub_awaited`: DROP. AGREE.** `prism_coming` and `yields_to_prism` cover it.
- **M4-b4, the `hub_claim` farm filter: DROP. DISAGREE in part.** Its single-tile case is what K3 needs; see
  amendment 1. Without it, the base's claimed branch on an unheld group keeps a nearer ally. That is
  `walk - slack < capture_rounds - 1 + our walk`, which assumes the Prism can join our hold, and it can't on one
  tile.

### macro6

- **M6-a, carry premium and 'T': DROP. AGREE.** Its `may_take_over` change (`!sole || sole->is_self`) applies to every
  champion, not only the Prism. It goes with the drop.
- **M6-bc, Focus-priced farm values: CONSIDER, C3. AGREE with the class; amend the notes.**
  - **The conflicts are wrong.** All 17 farm.cc hunks apply to the base with offsets. Only capture.cc's
    `sole_capture_holder` hunk fails. The "1733 `ally_holding` line" is macro4's `hub_claim` hunk. The crystal-toll
    line is untouched by macro6. The real risk is a silent clean apply that stacks on `gold_part` (farm.cc:959, 1937).
  - **Removing `gold_part` reprices the other picks.** It doubles gold's weight in 'G', 'L', 'T' and the shared join
    for a keeping Prism. 'G' and 'L' get no `carried_bonus`, so the swap tilts the Prism from carrying allies'
    captures to its own clears. macro6 recorded that shift: Prism solo captures 65 to 105.
  - **Counter-evidence to cite:**
    - macro5 prismhold2 (Focus premium in the Prism's own farm and kill values): 52.2 against 54.6, -2.4;
    - macro4 aoe (re-steering the Prism toward clearing): -3.2;
    - macro5's lesson, "reallocate, don't redirect".

    The base's lever is reallocation. Test C3 with 'G' and 'L' carrying the same bonus, or not at all.
  - **Undocumented in the J branch:** with `carry > 0` the rate's rounds gain `cap_rounds` (`hold`), so the plain share
    is also discounted by the hold.
- **C1 against C3:** these are two derivations of one quantity, a carried gem's Focus. If both are kept, use one
  premium for every Prism pick (S, K, C, J, G and L). Otherwise the picks are compared in different units.

### macro3

- **M3-a, EOQ bank floor: KEEP, K1. AGREE.**
  - The code matches the plan: `q = rate x sqrt(2T / (hazard x bag_swing))`, clamped to
    `[10, max(10, min(gems_short, 10 x bag_rounds_left))]`.
  - The Prism is unaffected: `banks_bag` needs `!retaining_gems`, and a non-keeping Prism is winning or closing,
    which bypasses the floor.
  - It applies and builds on the base.
  - Fix the port command. The diff applies with `patch -p1` from the bot root, or `-p2` only from inside `src/`.
  - Note: `note_carriers` counts the keeping Prism's carrying rounds and deaths. On the base those dominate the
    posterior, although the floor never applies to the Prism. That was equally true on ocean, so it is not a reason
    to change K1. macro3's eoq4 (a per-champion hazard) was worse.

### macro2

- **M2-a, M2-b, M2-c, M2-d: KEEP, K2. AGREE.**
  - It applies on top of K1 (fuzz on `support.cc`, `capture.cc` and `fight.cc` offsets) and builds in release. I read
    the merged formation loop: `on_held` filters tiles and `heal_before` ranks heals, and they do not interact.
  - M2-b leaves B1's test alone. `turns_to_harm_idle` runs the fight simulation (`fighter()` and `Fighter` kits), not
    `threat_strike` or `most_damage`. M2-b does change `threatened`, `any_threat` and `avoid`, which `capture_recall`
    and `yield_capture` read.
  - M2-c on the base: `cast_at_camp` (combat/abilities.cc) has no enemy check. But ocean's `hold_capture` already
    casts at any camp its basic reaches, so M2-c extends existing behaviour. It does not open a new risk. It fired
    about once in 3 games on ocean; expect more on the base.
- **The group's gate is underpowered.** 20k paired games give about ±0.7 at 95%. The group's expected gain is about
  +0.5 (+0.7 at normal fuel against ocean), and each piece alone was level at 10-25k. The planned ablation ("M2-b
  first, then M2-a") cannot be read at that size.

### Leftovers

- **L-1, Monolith carry price: CONSIDER, after C3. AGREE.**
- **L-2, hold-sole3: DROP. AGREE.**
  - Its recall rework steps off any recall co-holder standing there at the payout, whatever the recall is for. The
    base's analogue, hold7, was level. Cite it.
  - With M5-f as a CONSIDER, its payout-round transit rule (`paid_hold_tiles`) is the softer variant of the same
    idea. Keep it dropped.
- **L-3, eoq5: CONSIDER. AGREE.** The holding cost `bag_swing x hazard x bag` is in gems per round, the same unit as
  `best_value`'s rate. It also removes the hand-set `chain_bag_limit = 26`.
- **Debug-only traces: DROP. AGREE.**

### Testing notes and the queues

- **The fuel deltas are correct:** -0.8, -0.4, -0.5, -0.8, -0.1, and -1.5 for the base. Gating at normal fuel, the
  out-of-fuel census and fresh ladder-v2 suites are right.
- **The K order is right**, K1 then K2 then K3. The gates need the changes in amendments 7 and 8.

## Missed or unstated changes

None is large. Each should be named in its entry so a porter doesn't drop it unawares.

1. macro4 `hand`: unheld Q on our own claim once the ally leaves it (`g != memory.claim`). The base's 'L' covers it.
   The `at_once` `hub_net` gate goes with C1.
2. macro4 Q: holders we can't see, read from posted tiles, and no reach cap. Both go with M4-a1.
3. macro6 J: `hold = cap_rounds` added to the rate's rounds when the Prism carries. It belongs to M6-bc.
4. macro6 `may_take_over`: `sole->is_self` allowed for every champion. It goes with M6-a.
5. macro2 M2-a: the old exact-tie rule in the formation ("the mate first if it requests support") becomes
   `heal_before`'s "waiting mate" rank. It belongs to M2-a.
6. macro5 M5-c: the home-recall keep in `continue_recall` refuses while locked. It is listed, but it is a separate
   hunk from M5-e in the same function.

There are no params.h changes beyond those listed: macro4's `hub_rho_most`, and macro3's `min_bank`, `carrier_hazard`
and `bag_swing`. `charybdis-base` equals `macro1-hold6`.

## Evidence attribution

The orchestrator numbers quoted are the right ones and are at 2x fuel. Only the six final bots have normal-fuel
numbers. Corrections:
- **K3 / M4-b1:** drop `q-nohand` as evidence. `hand`'s +0.8 / +0.5 is the five-part bundle above, incremental on
  `q-gate` at 2x. Nothing isolates K3.
- **`q-r0`:** the premium in Q's value plus the hand-over's gates, not "rho 0 inside Q".
- **M5-e / M5-f:** +2.2 combined, incremental over hold-safe at 2x. The 48% and 36% split is shared-payout causes in
  hold-sole's smoke traces, not win rate.
- **M4-a3:** +1.6 is hub1 to hub2, value and gate together, at 2x, with the allies' premium still on.
- **M6-bc:** carry2 +1.1 and carry3 +1.0 are incremental at 2x, on two sets each. Matches the plan.
- **M2:** each piece is isolated on ocean at 2x and level. The group is +0.53 (combo) or +0.76 (lstep) at 2x, and +0.7
  at normal fuel. Matches the plan.

## Amendments to the plan

1. **K3(a), unheld single tile.** In `leave_for_prism`'s claimed branch, also return `Leave::claimed` for
   `!held && G.members.size() == 1`, after the `carry_reach` checks. This is M4-b4's case. Without it, a nearer ally
   walks onto a single-tile group the Prism claims, and K3 then steps it off.
2. **K3(b), timer floor.** The Prism's held-group 'L' pick requires `timer >= 2`, the bound the ally side keeps
   (`payout - round < 2` returns `Leave::no`). Otherwise the Prism walks to a hold the ally will not leave.
3. **K3(a), stale pin.** When `full`, ignore a `kept_group` pin set in an earlier round: the top `Leave::no` test in
   `leave_for_prism`.
4. **K3(b), walk goal.** Every tile in the goal is occupied. Check that `step_towards(off_zone(carry_goal))` advances.
   If it doesn't, aim at `G.adjacent()` until a tile frees. Keep `prism_carries`' `enemy_may_see` gate in the variant.
5. **K3 evidence.** Replace the `q-nohand` citation with "`hand`, +0.8 / +0.5 for five changes; none isolates the
   rule".
6. **K3 debug batch.** Besides firing frequency, count the Prism's arrivals and payouts on handed groups, and the
   delay (`walk + capture_rounds - timer`). K3(b) is the base's first pick that delays an ally's payout while valuing
   the whole capture. On a single tile with the Prism due before the payout, the delay is under `capture_time`. That
   is less than the base's existing claimed leave already accepts, so the pricing is consistent with the base, but it
   should be measured.
7. **K2 gate.** Adopt unless significantly negative: these are rule fixes, with M2-d a bug fix. Drop the
   ablation-on-level step, which cannot resolve at 20k.
8. **Port commands.** Read `patch -p1` from the bot root (or `-p2` from `src/`) for K1 and K2.
9. **M5-f.** Reclassify from DROP to CONSIDER, low, conditional. List the real uncovered branches: `local_support`,
   `willow_independent_heal_step`, the handoffs, `guard_turn`, `chase_with_guard`, and `retreat`'s non-`retreat_step`
   moves. Gate it on a shared-payout-by-branch trace. Port it with the base's `prism_hold_tiles`, memoised.
10. **M4-b4.** Change DROP to "single-tile part folded into K3" (amendment 1); the rest is DROP.
11. **C1 spec.** Add 'L' on held groups, late form with `hub_net` gate. State that +1.6 measured value and gate
    together. Correct `q-r0`'s description. Name the rho clamp as a hand-set constant.
12. **C3 notes.**
    - Replace the conflict note: all farm.cc hunks apply; guard against stacking on `gold_part`, removing it at
      farm.cc:959 and 1937.
    - Add prismhold2 (-2.4) and aoe (-3.2) as counter-evidence.
    - Say whether 'G' and 'L' get `carried_bonus`. Recommend testing with them included, so the swap does not tilt
      the Prism from carries to solo clears.
    - Document the J branch's `hold` rounds.
13. **C1 with C3.** Add a rule to the CONSIDER queue: one Focus premium, rho or `carried_bonus`, for every Prism pick
    type if both are kept. Test the second only on top of the first, under the same premium.
14. **M5-c merge notes.** Add the fuzz-1 `work_guard` hunk to check by hand.
15. **M5-a, M5-e and M3-a wording.**
    - M5-a: mark the prismhold attribution as inferred, and cite hold5 for the in-sight residue.
    - M5-e: mark the "about half" as from payout traces.
    - M3-a: note that the Prism dominates the carrier record.
