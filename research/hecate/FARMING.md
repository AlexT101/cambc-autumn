# hecate: one farming model (workstream B)

The verdict on three farming designs (rate, plan, minimal) and the one to build. Code refs are to
`bots/hecate/src/bot.cpp` at main 6ac5983; economy data in `replays/orch/research/bdata_agg*.txt`.

**Verdict: build it, in two stages.** Today one decision is priced in up to four places that disagree, and `farm`
picks through four tiers and an override. Each stage deletes more than it adds, can be judged alone, and keeps every
constant with a recorded win. Of the three designs only the minimal one is clearly simpler than today's code, so it
is the base.

## The three designs, scored

| | rate (one rate, bag hazard λ) | plan (committed Job, replan triggers) | minimal (shared prices, one value) |
|---|---|---|---|
| Simplicity | Good, until stage 2 adds an online hazard with a seen/unseen split | Worse: 6 triggers; stage 1 nets ≈ +55 lines | Best: duplicates merged, then the tiers |
| Rule derivation | Good, but κ and λ are fitted | Good: trigger 2 is the one-turn delay of shared memory | Good: rules or in-game counters |
| Strength | Risky: bag size can't be judged locally (chain 80: gen 53.5, ladder 42.9) | Risky: stickiness 1.0 lost −5 | Near-level by design; the tier merge is consensus (COORDINATION 3) |
| Fuel | Level | Saves on held turns, from a loop at its floor | Level if cache keys stay stable (below) |
| Build risk | High; stage 2 unjudgeable locally | High: stored state that can go stale | Low: one kind of change per stage |

Grafted in: from rate, the shop credit in the trip home and the argument that the early prune stays exact (added
prices only lower a value); from plan, the two-turn claim confirmation, held back as stage 3; from all three, crew
output from each claimer's arrival.

## Today's problems in brief

- **The trip home is priced four ways.** `farm`'s `homeward` is min(walk, recall + spawn→altar) with no heal or hurt
  turn; `recall_to_bank`, `capture_recall` (plus its emblem branch and guards) and `wants_shop` each add heal and hurt
  their own way. So farm values a chain by one trip home and the executor takes another.
- **Two heal prices.** The global `heal_rounds` divides by usable health (max × 0.65), farm's lambda by max health.
- **Four tiers and an override pick the group:** best, risky, shared, plus the partner path (`rally_radius` 12), all
  overridden by `help_group` (`struggling`, `help_radius` 8). A crew counts every claimer as already hitting, however
  far away (COORDINATION 3).
- **One taker is assumed in three places** (`ally_holding`, `step_onto_cleared`, `pick_up`), while `holding_capture`
  and `capture_taken` use `holders(G)`.
- **Fixed constants for gold and the end:** gold is worth `gold_worth` × `clear_share` 0.15, shop trips stop at
  `endgame_shop_rounds` 100, and the endgame is split across `endgame()` and `closing()`. We actually spend 16.3% of
  champion-rounds clearing (bdata main-gen), so in-game counters can stand in for 0.15.

## The model

One value per group, built from shared prices:
- **Q1 `heal_rounds(damage, out)`** = damage / (max × (1 − recall line)) × (recall + out); `out` is the group's
  cached `to_spawn`, or upkeep's mean spawn steps with no group.
- **Q2 `home_value(gold_in)`** = `heal_rounds(missing)` + `emblem_gain_rounds(next)` when gold + `gold_in` ≥
  `next.cost`; 0 once the bag wins.
- **Q3 `home_trip(walk, overlap, gold_in)`** = min(walk, max(0, channel − overlap) + hurt + spawn→altar − Q2), and
  which way won. `overlap` is the part of the recall that runs during the capture's remaining rounds.
- **Q4 `gems_share` bounded by time:** gems left = min(short_by, 1000 − enemy score, `ally_rate` × `bag_rounds_left`),
  split over allies alive. Emblem gains and gold's worth fall to 0 near the end by themselves.
- **Q5 gold in gems** = `gems_share(short, next.saved / next.cost)`. `saved` comes from `upkeep_cost`, which already
  holds the measured clearing share (`camp_turns / turns`) and heal trips. Replaces `gold_worth` × `clear_share`.
- **Q6 `takers(g)` = `holders(G)`** wherever a cleared group counts the allies on it.
- **Q7 `crew(g)`:** up to 4 (output, eta). For a claimed group, its claimers, with eta the group's centre field at the
  claimer's tile (`GroupFacts::centre`), 0 when unseen (today's assumption). For an unclaimed group, the best
  visible unclaimed ally (replaces the partner path). Health left = H − Σ outᵢ · max(0, t − etaᵢ), solved
  piecewise; our part is our share of the damage.
  - **Rescue:** if without us the claimers would cross their recall line before the group falls, the team gets
    nothing from it, so part = 1 provided we arrive before that breach. Replaces `struggling` and `help_radius`.
- **Group value** = rate(worth × part, trip + wait + clear + capture if we hold + heal_rounds(our damage share)), with
  worth = home² × min(gems, short) + Q5 × gold. The clearing method (basic, spells, with the crew) is the feasible
  one of highest value. The pick is lexicographic on (feasible, value), feasible = soften × damage share ≤
  `spare_health`: one comparison instead of the tiers. The infeasible best is still taken when nothing is feasible,
  as risky is today.

## Mapping from today's decision points

| Today | Becomes |
|---|---|
| farm `homeward`/`bank_now`, `recall_to_bank`, both branches of `capture_recall` | `home_trip` (Q3) |
| `wants_shop`'s inequality | shop when Q2 ≥ min(back, recall + hurt) + back |
| global `heal_rounds`, farm's lambda, the spell-vs-basic test | Q1; the method is the higher value |
| `gold_worth`, `clear_share`, `endgame_shop_rounds` in `may_shop` (Tavi's test stays) | Q4, Q5 |
| `endgame()`, `endgame_horizon` | closing = `bag_rounds_left` ≤ walk + tribute + `endgame_margin`; `too_late` at any horizon |
| `ally_holding`, `step_onto_cleared`, `pick_up`'s single taker | `allies_on ≥ takers(g)`; `pick_up`'s nearest-taker tie stays |
| risky / shared / partner / help tiers, `struggling`, `crew_strength` | Q7 + rescue + the lexicographic pick |

**Deleted:** `gold_worth`, `endgame`, `struggling`, `crew_strength`, the partner loop, the joint-clear block, the help
override and 6 tier variables; params `clear_share`, `endgame_shop_rounds`, `endgame_horizon`, `rally_radius`,
`help_radius`. Estimated about −30 lines in stage 1 and −40 in stage 2, to be checked on the diff.

**Kept on purpose:** stickiness ×1.2 (1.0 lost −5), `max_wait` 5 (waiting lost, 45%), `home_power` 2 (won),
`chain_bag_limit` 30 and `brake_bag` 11 (chain 80 lost on the ladder); `contest_capture`, siege and kite (a 50.5%
keep, the don't-remove list); `finishing_camp` and `camp_trapped` (they feed `want_home`, Workstream A's); `camp_risk`
(no A/B on record, but it sets every clear's boldness); `gold_farmer_weight` 4 (gold-only captures matter: the pickup
that took them 529 → 1849 won 52.8%, and nothing backs deleting it).

## Fuel

- **Cache keys.** Farm's `Context` keys its per-group cache and includes `per_gold`. Q5 reads upkeep counters that
  move every turn, so compute it only when short_by, items or stats change, or every group is rebuilt every turn.
  Health-dependent Q2 stays out of the cache too: the cache keeps walk and tribute, and `back` becomes a min and two
  adds per group (~10 ops × ~10 groups).
- **Crew solve** only on claimed groups, plus infeasible ones for the partner as today: one warm centre-field read
  per visible claimer.
- **The prune** stays exact (the heal term only lowers a value); the partner exemption stays as written.
- **No new host calls, no gates.** Expect ±1% of farm's mean; check `tools/fuel/bench.py` (mean, p99, out-of-fuel).

## Handing fight turns to the strike search

`decide`'s order is unchanged: `plan_strikes` runs before every farming branch. `Intent` (`group =
memory.farm_group`, `step_value`, `to_altar`, `anchored`) is unchanged. Farm calls `strike_enemy` only after its walk
and never picks an enemy target. `retreat`, `want_home`, `chase` and the plan are untouched.

## Build plan

**Stage 1: shared prices (S).** Q1–Q6, closing absorbs `endgame`, `takers`.
- Screen (`debug_block`, 6 games): per_gold old against new (expect within ~±30%); recalls with a bag and shop
  trips against main.
- A/B (`tools/ab.py`, ladder + gen, 582) against the commit it branched from. Keep if ≥ 47% and out-of-fuel turns
  not up.

**Stage 2: one group value (M), on stage 1.** Q7 with rescue, the heal term in the cycle, the lexicographic pick,
the tier deletions.
- Screen (6 games): how often the chosen group changes on farm turns; A-B-A steps on corridors, labyrinth and
  spiral (4.3% overall today, ~32% on corridors in mirror losses); camp deaths; gold-only captures.
- A/B against stage 1. Keep if ≥ 47%, with deaths carrying 20+ and camp deaths not up. Confirm any gain on
  `maps/gen-s1`.

**Stage 3, only if stage 2's screen shows more corridor flips: two-turn claim confirmation.** An ally's claim counts
in Q7 once it reads the same on two of our turns in a row. Rule: shared memory reaches a teammate up to a turn late
as turns alternate, the cause EXPERIMENTS gives for corridors' flips. Not a retry: earlier-index (44.5% gen),
count-once (40.5% ladder) and seniority changed who counts; this changes only when a claim counts.

## Not adopted, and why

- **The plan's Job and triggers:** six replan triggers are six special cases, stage 1 nets +55 lines, and the fuel
  saving falls on a loop already at its floor (~17% of WASM ops, EXPERIMENTS).
- **The rate design's bag hazard λ** (in place of `may_chain`, `chain_bag_limit`):
  - only the ladder can judge it (chain 80: gen 53.5, ladder 42.9);
  - self-play hazard is low (12 gems a game lost to champions locally, 32 on the ladder without boss-battle), so an
    online λ grows bags exactly where local A/Bs can't see the cost;
  - its prior is off: we measure 0.96 deaths per 1000 champion-rounds against the 5.7e-4 assumed, and that counts
    all deaths, not carriers';
  - the top teams' larger bags (median 22-29 against our 14-15) stay open, for a model judged on the ladder.
- **κ in place of `camp_risk`, 0.6 and 1.5:** fitted numbers for tuned ones, and it touches `want_home`. Revisit
  after stage 2.
- **Contest as a farm option:** `decide` runs `contest_capture` before kite and siege, so inside `farm` it would
  vanish on shared-gem and Monolith-only maps.
- **One `free_hit` for `passing` and `hold_capture`:** a few lines saved, and close variants lost (`passing` for
  `affordable` after a walk, 49.5%).

## Review (B-judge, adversarial pass)

Checked against the code at 6ac5983, EXPERIMENTS and bdata. **Corrected:** contest stays outside `farm`; Q5 must not
change farm's `Context` every turn; `camp_risk` has no recorded A/B (the minimal design said "each won"); λ's prior;
`gold_farmer_weight` kept (its deletion was unargued); the closing/endgame merge applies the 20-round margin on the
race side too (small, stated). **Left in:** the heal term in the cycle is a clear price, not the lost "capture-recall
heal value" (a trip price); rescue reuses the recall line. **Risks:** the heal term may favour harmless groups and
lengthen cycles (watch walk share, tributes per 100 rounds); arrival crews may add corridor flips (stage 3).
