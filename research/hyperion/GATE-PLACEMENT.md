# Fuel gate placement plan (2026-11-05, astraeus 57194754)

The gates are where they were first put, not where a cut costs least. This plan moves the cuts: each gate keeps
back what the work after it really costs, a cut keeps the work already done instead of throwing it away, and the
heavy work that no gate reaches is made cheaper or bounded. It follows [FUEL-GATES.md](FUEL-GATES.md)'s rules (no new
fuel gates; repeated work gets measured limits with deterministic fallbacks), but changes existing reserves and
fallbacks.

Evidence: EXPERIMENTS "Fuel gates census" (2026-11-05). That section covers the census on current astraeus, 550
games, and the step-guard-entry A/B: 50.8%, OOF +7.9%. Census numbers below are from `wa200`, with `cen75` in brackets.

## What the census says

| Gate | Problem | Measure |
|---|---|---|
| step-guard-entry, -sim, -look | It fails open (no guard), and when it cuts it throws away work already done | Needs ~37k; a placing costs 1.6k p50, 13k p90, 21k p99; half its turns end decide with 21k+ unused. Without `fight_cost_estimate()` in the entry, about 60% of the placings it newly lets through are cut at a sim instead, with no guard and their cover work wasted (the A/B's OOF rise) |
| Walk checks: farm-no-route, static-descend, siege-route-fuel, walk_on's approach | They keep back too little: they price the search alone | 14-62% of the turns where they fire run out anyway. Turns where one of them was the last check passed spend p90 27-37k after it, against 13-18k needed. The work after them is travel plans, crossings, the step guard and the turn end |
| prey-cut-short | It keeps back too much | It fires with 36k [41k] left; 93-95% of those turns could have paid for another candidate (4.4k median) |
| farm-partial-evaluation, turn-order, comms-stale-vision | Sized about right | A cut loop's decide spends 15k p50 / 38k p99 against ~35k kept back |
| (no gate) | 47% [66%] of OOF turns pass no fuel check | They are mostly fight turns: the strike search 43k (28k self), `stand_lost_at` 23-25k, `new_fight` 14-16k. In wa200 78% of the remaining OOF turns have no enemy within 6: the farm loop's last pass, in which one group's first-time facts cost more than the margin left, and the farm walk |

Considered and dropped: a cheap economy on fight turns, triggered by game state. On fight OOF turns that pass no
check, the farm is present 36% of the time at 10-15k, against the strike search at 70-78% and 43k. That is too little to free.

## Work items, in order

Each item is its own commit and A/B. Do one at a time unless it says otherwise.

### A. The step guard: a cut keeps a cautious guard (most cuts, and it fails open)

> **Done, 2026-11-05: level, nothing shipped** (EXPERIMENTS "GATE-PLACEMENT item A"). A1(i)/(ii) 49.9%/49.9%,
> A2(i)/(ii) 50.0%/49.8% with OOF +6-13%. Variant (ii) tested lethality by the Strike bound, not `Safety::lethal`.
> On fuel-short turns no guard, a cautious guard and the exact guard play alike. A3 is dropped. Start at B.

**A1. Fail closed at the sim cut.** Change only the fallback. When `simulate` returns false in
[guard.cc](../../bots/astraeus/src/combat/guard.cc) (step-guard-sim), return a guard built from what is already
known instead of `nullptr` or the partial board. Every tile still unsettled and more exposed than ours by its bound
(`exposed`) is guarded. Two variants, each a 10k A/B against astraeus:
- (i) every unsettled exposed tile;
- (ii) only those where `safety.lethal(q)` holds, plus every unsettled one when linked (Cassi and Issac).

Do the same at step-guard-look, which cuts after the bounds and before the exact looks: guard the bound-exposed
tiles. The entry check stays as it is, so this measures the fallback alone. It fires about 86k times in 10k games;
most of the lift should come in A2, where the sim cut fires 282k times.

Risk: walks stalling against a wall of guarded tiles. Run `tools/replay/osc_detect.py --bridge-oof`, then
`osc_compare.py`, on traced games against astraeus (as in fuel campaign 6's audit round) and watch `stuck_fail` and
`stuck_idle`.

**A2. A two-stage entry: price the first sim before the costly part.**
- **Stage 1** is the cheap part: `GuardFoes`, the bound exposures and the union key. Its check keeps back
  `act_reserve + costliest_bound`. Here `costliest_bound` is a decaying maximum of stage 1's own cost, measured like
  `costliest` is now but without the sims in it.
- **Stage 2** decides what is needed. If the union fight is already known (`known_fight_of`) or settled, no sim
  is needed and the placing goes on. Otherwise the existing sim check prices it (`fight_cost_estimate() + act_reserve`).
  When that check fails, take A1's fallback straight away, before the exact looks.

This is `astraeus-sge`'s entry, which removed the double count, plus the fallback that its A/B showed was missing.
Fewer placings are refused, a placing short of fuel still guards, and the only cost lost to a cut is stage 1. A/B
it against A1's winner, and record the counts of entry, sim and look cuts (`replays/fuel/fc5/shortcuts.py`).

**A3, once A1 and A2 ship.** `step_guard_costliest()` also chooses how `route()` searches
([pathing.cc:712](../../bots/astraeus/src/model/pathing.cc#L712)). Check that `costliest_bound` gives the same
choices, or keep the old measure for `route()` alone, so that A2 doesn't change routing.

### B. Walk checks price the walk they guard

> **Done, 2026-11-05: level, nothing shipped** (EXPERIMENTS "item B1", "item B2"). B1 (`travel_cost_estimate`
> only) 50.0%, OOF -4.0%; B2 (full search or none) 50.0%, OOF -0.9%; 20k games each. Both make gates cut more often
> for no win: a lower OOF count alone does not justify more degraded turns.

**B1.** Today the walk checks keep back `search_cost_estimate(cap) + end_reserve`. Give them the terms farm's loop
already reserves for the same walk ([farm.cc:1080-1097](../../bots/astraeus/src/economy/farm.cc#L1080)):
- `travel_cost_estimate` while the dash is ready;
- the deferred step guard's stage-1 price (A2) while it has foes in reach.

Apply it at farm.cc's `search` and `funded` ([1929](../../bots/astraeus/src/economy/farm.cc#L1929),
[2022](../../bots/astraeus/src/economy/farm.cc#L2022)), step_field's static descent
([pathing.cc:1716](../../bots/astraeus/src/model/pathing.cc#L1716)) and `prepare_approach`
([pathing.cc:388](../../bots/astraeus/src/model/pathing.cc#L388)). Share one helper with `loop_reserve`. Their
fallbacks already step, so a cut costs path quality, not the step.

Precedent: CHANGES 348 kept back the veto's measured ask at these same sites, for OOF −6.8% at level win rate.
Campaign 6's broader variant, which kept back the veto's whole turn, lost slightly, so price only the terms above.

**B2.** Replace the fuel-proportional depths (step_field's cap from the fuel left, and `step_towards_funded`'s cap)
with a binary choice: the full cap, or the fallback. Same state and same fuel threshold then give the same route.
Judge it on traceability and win rate. It may cost a little OOF.

### C. Prey keeps back the chase, not more

**C1, a measurement.** Add debug lines for the index of the chosen candidate, each candidate's `chase_trade` cost,
and the cost of the chase's walk after it. Run them on the census maps.

**C2.** Set prey's reserve from C1: the candidate's sim (`fight_cost_estimate()`) plus the measured chase walk at
p95, instead of `search_cost_estimate(16) + end_reserve`. Also move the check after the duplicate-fight skip
(`lost`), so a repeat costs nothing. prey → step-guard-entry is the most common gate pair in a turn (9,203 turns on
cen75); item A found the guard's cut costs nothing at the real budget, so C2 needs no guard work first.

### D. The farm loop's last pass: cheaper, not cut sooner (exact, can run alongside A-C)

> **D1, 2026-11-05: level, not shipped** (EXPERIMENTS "item D1"). Exact; OOF -1.4% over 10k games, noise-sized.
> The rest of the cold pass (`min_camp_damage`'s simulation, `crew_work`) reads health and allies, not terrain: D2
> has nothing static left worth moving.

The farm loop's `room()` was the last check passed on 17.8% [14.2%] of OOF turns. The next pass is one group's
first-time facts (`min_camp_damage`, `clear_fire_sort`, `stand_reach_build`, `crew_work`). Campaign 6 found that
cutting the loop sooner loses farm quality (a1 48.7%). So build the parts that depend only on terrain in the turn-end
queue:
- **D1.** The static `StandReach` tables (camps.cc `stand_reach`) for the nearest groups not yet built. Campaign 6
  measured them at 10-13k on 3% of OOF turns and noted this would be exact.
- **D2.** Anything else in a cold pass that reads only terrain and the draft plan. Find it with the census's
  `farm.loop` sub-scopes.

Fuel-only: replays on every `bench.py` set and on cen75 must be byte-identical at 100M. Then one 10k A/B for OOF.

### E. The work no gate reaches: the fight turn's front half

This is the largest share of OOF turns and the hardest. Make it cheaper first, then bound it.
- **E1, a profile.** Profile the strike search's own cost, the 28k it spends outside its sub-scopes, with
  `tools/fuel/siteprof.py` on cen75 fight turns, both sides playing the census copy.
- **E2, exact cuts.** Make the cuts E1 finds, fuel-only and byte-identical at 100M, as campaign 6's walk-only search
  (CHANGES 352) was.
- **E3, a work limit.** A deterministic per-turn limit on the strike search's exact queries, scaled by foes yet to act,
  instead of the flat `max_exact_queries = 10` ([plan.cc:195](../../bots/astraeus/src/combat/plan.cc#L195)). Tiles past
  the limit keep their Strike bound, a cautious price. This changes play at every fuel level, so run two A/Bs. One at the
  real budget, and one at 10M fuel a turn with `tools/fuel/cap_variant.py`, so that the quality lost (the 10M result)
  and the fuel gained (the real-budget result) are seen apart.
- `stand_lost_at` and `new_fight` have no gate-level fix (campaign 6's "sides" round). Their lever is a cheaper
  `simulate`, which is outside this plan.

### F. Clean-up and docs

- **F1.** `ward_bushes` reads only bush clusters the queue has found and never grows them itself
  ([bot.cc:67](../../bots/astraeus/src/bot.cc#L67)). This removes ward-no-bushes-clusters. A/B it: ward timing changes.
- **F2.** Measured constants in place of the gates' running estimators where the census shows a stable cost
  (FUEL-AUDIT finding C). Do this only for gates that remain after A-E.
- **F3.** Refresh FUEL-GATES.md: the work veto is gone (CHANGES 359), campaigns 5-6 and this census are missing, and
  its table should take each shipped item's numbers.

## Protocol for every item

- **Ship rule:** a change that makes gates cut more often, or adds a degraded path, ships only on a win-rate gain.
  At a level win rate, ship only changes that remove cuts or are fuel-only and exact; a lower OOF count alone is
  not a reason (items A and B).

- **A/B:** against the frozen `variants/astraeus-6c8746a`, or the last shipped item, with `--no-test-draft` (both play
  their own drafts). Use fresh suites, generated while no other batch runs, at most 30k maps a mapgen command. Run 10k
  games, and 20k on fresh suites to ship. Judge by win rate. Report OOF (`oof_bot.py`) and the gate cut counts
  (`replays/fuel/fc5/shortcuts.py`).
- **Fuel-only items** (D, E2): byte-identical replays at 100M on the `bench.py` sets and on cen75.
- **Items that change play:** at 100M they must be identical wherever only the fallback moved (A1, A2, B1, C2). This
  checks that the gate is the only thing that changed.
- **After each shipped item:** rerun the census so the next item starts from current numbers. Build a census copy with
  `instrument.py --fine --trace --lenient` (the farm loop's pattern is fixed), pass absolute `--games` paths to
  bench.py, then run `tail.py`, `census.py` and `gates.py` from `tools/fuel/census/`.
- **Record** each result in EXPERIMENTS.md and each shipped change in CHANGES.md.
