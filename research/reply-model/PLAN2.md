# Reply model, phase 2: a cheap learned danger as ocean's one danger

2026-11-08. Written as research and a plan; it has since been run (see Status). Phase 1 is
EXPERIMENTS.md "Reply model: learned danger and pressure" (variants `oc-reply`, `rlg`, `rd-base`). This phase adds
the offline scripts `compress.py`, `fold.py`, `lethal.py` and `fuel_bench.cc` in this directory. Their outputs are in
`replays/combatlab/reply/compress/` (`run1-5.log`, `fold.log`, `lethal2.log`, the candidates' pickles).

Every number below was measured on the phase-1 data unless marked *(estimate)* or *(inference)*. File:line references
are to `bots/ocean/src/` at 7fc160d6d.

## Status (2026-11-08)

The plan was run from step 0 on `variants/dg-base` (ocean at 7fc160d6d), with the work in `variants/dg-dev`. It
stopped after step 2 by §7's rules. Numbers are in EXPERIMENTS.md, "Reply model phase 2: one danger".

| Step | Status | Numbers |
|---|---|---|
| 0 | **Done** | C++ = Python: logit diff ≤ 6.9e-7, p diff ≤ 4.7e-6 on 20k rows. Calibration: k full 0.939, min5 0.918, flat 0.326, unseen 0.316. Per-opponent p_kill calibration not done |
| 1 | **Failed: OOF** | Fuel per fight turn +0.2-0.3k, within §4. But lab OOF went 0.65% → 0.925% (full by fuel) and 0.875% (min5), against a +3% bar. Dev A/B of the shadow alone: 48.8% / 49.3% of 10,240, game OOF +42%. A burn arm of the same mean cost left OOF unchanged (0.67%). So the cost that hurts is the part that grows with query count, landing in the heaviest turns |
| 2 | **Level: dropped** | The counters fell: tiles want_home would leave 16.8 → 15.1%, strike-then-leave 23.8 → 22.9%, A-B-A flips 10.2 → 9.9%. A/B 49.7% dev (10,240), 50.0% held out (20,480), 49.9% varied (10,240), game OOF +16-20% |
| 3-10 | **Skipped** | §7: min5 also failed OOF, so keep flat danger and do only step 2. Step 2 was level |

## 0. Summary

- **The danger is mostly a hit probability.** Given a hit, the damage is close to the Reach blow: median damage/blow
  is 1.00 (IQR 0.90-1.00), and the correlation is 0.86 on held-out rows. So danger = min(blow, our health) x k x p(hit).
  The work is in p.
- **Cheap form: a logistic GAM.** p is a sum of lookup tables: 1-D tables, plus five 2-D ones. It uses only features
  that are free at a query (d, blow, stuns) or fixed per enemy for the turn. Its scores:

  | | Lean | This GAM |
  |---|---|---|
  | Within-decision ordering | 0.839 | 0.842 / 0.835 (per enemy / per alternative) |
  | Damage R² | 0.381 | 0.389 |
  | Hit log loss | | 0.482 (full model 0.424, flat 0.642) |

  - It needs none of the Reach::sources work.
  - The per-enemy terms fold into one logit z_e per enemy per turn. A query is then three lookups, a sigmoid table
    and a multiply: **148 wasm instructions measured**, against the lean trees' 374 and the full model's 3,647, both
    before their features. Folding makes the query cost about 1/40 of the full model's and about 1/8 of the lean
    model's *(estimate, counting features)*.
- **Lethal stays worst-case for now, but can become a calibrated probability.** P(killed) uses the same p and
  worst-case damage per hit: P(sum over the enemies that hit of blow_i ≥ health). Its log loss is 0.030, against
  0.076 for a constant rate.
  - At a 0.2 threshold it flags 16% fewer turns than ocean's worst-case test, with 0.866 recall against 0.891.
  - Ocean's worst-case test is not wildly conservative: half of what it flags (precision 0.49) really dies.
- **Unification:** one `Danger` cache in Safety, per Safety generation. It holds:
  - per enemy: z_e and the folded tables;
  - per (enemy, tile): the Blow, p and E, kept in Reach's memo;
  - per tile: an aggregate with expected damage E, worst W, P(any hit) and P(killed).

  Every consumer reads the field its semantics need from that one cache. A fuel mode is chosen once per turn. It is
  never chosen per query, which rlg's per-query gate did, mixing units inside one search.
- **The inconsistencies that matter most are not in plan_strikes' expected danger.** They are between plan_strikes
  and want_home:
  - the step guard's test is narrower than want_home's;
  - fuel shortcuts drop the guard;
  - heal and shield values are priced worst-case inside the same score as the expected danger.

  The migration order puts the infrastructure and these alignment fixes before the model swap. Each step is testable
  on its own.

## 1. Danger inventory

### 1.1 Primitives (model/safety.h, model/safety.cc)

| Primitive | Where | What it computes | Semantics |
|---|---|---|---|
| `Strike` / `compute_strike` | safety.h:51, safety.cc:892 | Max damage of an enemy's next turn at each Chebyshev distance 0-6. Walls, sight and items ignored. | Upper bound |
| `threat_strike` | safety.cc:1082 | Strike widened to two turns when it acts twice before us | Upper bound |
| `Reach::at` | safety.cc:1790 | Strike placed on the map (walks, dashes, sight, wards, Varg splash). Memo of 64 tiles per build. | Max damage, any-hit |
| `Safety::blow` | safety.cc:2344 | Reach::at for a visible enemy; a teleport from its destination | Max |
| `unseen_blow` | safety.cc:2407 | An unseen enemy's Strike at the nearest possible tile within its radius | Max |
| `damage_bound`, `worst_damage`, `damage_ceiling` | safety.cc:2580, 2707, 2629 | Σ blows + camps' full Strength; ceiling counts unseen at their most | Worst case |
| `bound()` | safety.cc:2588 | damage_bound, doubled for enemies acting twice; hits, stuns, and `threat` | Worst case + probability |
| `threatened` / `threat_at` | safety.cc:2716, 2609 | True if a camp or visible enemy hits (probability 1). Unseen: 1 − Π(1 − chance × 0.234) ≥ recall_risk 0.207 | Any-hit + probability |
| `tally` / `touched` | safety.cc:2649, 2644 | bound's damage, summed lazily | Worst case |
| `camp_damage(worst/next)` | safety.cc:2685 | Awake members in reach. worst: full Strength; else × weight (0.5 for unknown) | Worst / expected |
| `enemy_area`, `avoid`, `avoid_within` | safety.cc:2749-2788 | Boards of credible threats' reach | Boolean |
| `lethal` | safety.cc:3168 | worst_damage ≥ health + shield (spawn heals first) | Worst case |
| `may_reach_within`, `unseen_may_hit_within`, `unseen_approach` | safety.cc:2445, 2484, 2518 | Could strike p after n turns of walking | Boolean worst case |
| Fight sim: `simulate` / `trade` | safety.cc:680 / 737 | Alternating sides, focus on the weakest, casts on cooldown, stuns skip the strongest. Every hit lands. Horizon 17 own turns (safety.cc:516). | Deterministic multi-turn |
| `fight_key` / `fight_of` / `new_fight` | safety.cc:2790-2960 | The roster of enemies whose blow hits p, plus allies within 4; memo of 32 | Deterministic |
| `stand_reach/walks/roster/trade` | safety.cc:3049-3128 | Fight at p with walkers joining after their walk, plus camps | Deterministic |
| `chase_trade` | safety.cc:2967 | The chase fight, with delayed allies, late joiners and a bag boost | Deterministic |
| `turns_to_kill_idle` | safety.cc:3130 | Sim with us idle, enemies walking in; camps at *expected* damage | Deterministic |
| `engagement_near`, `partner_bound` | safety.cc:1044, 870 | A fight may open near p; Cassi/Issac kill cap | Boolean |
| `hit_given_reach` 0.234, `recall_risk` 0.207 | params.h:233-234 | The flat hit rate | |

### 1.2 Consumers

Combat, turn order and pathing were read directly. The economy rows come from a delegated sweep, spot-checked at
bank.cc:148, farm.cc:979 and capture.cc:412.

**Strike search (combat/plan.cc)**
- 2044-2058: strikers = visible enemies within max_reach + grid_r.
- 2207-2226: each foe's share is 0.234 × Strike.at(d) × the HoR factor. It orders pricing and sets the bound.
- 2228-2236: the exact price is **0.234 × Reach blow**, at most `max_exact_queries` = 6 a search (196). It is
  subtracted per candidate leaf, skipping removed enemies.
- 2244-2254: unseen threats at 0.234 × unseen blow, for tiles 2+ away.
- 2257: `lethal(p)` for tiles at grid_r only. Nearer tiles rely on the step guard.
- 2266-2293: tiles left unpriced by the query cap keep **0.234 × Strike.at(d)**, an open-ground upper bound.
- 693-695: the shield's value is duration × **damage_bound** (worst case), in the same score as the expected danger.
- 1118: the heal value is 8 × **damage_bound(a.pos)** (worst case).
- 1942: strike_free gates the shield by damage_bound > 0.

**The step guard (combat/guard.cc:502-687)**
- It walls off the tiles within 1-2 where `new_fight(fight_key(q))` is lost, or falls with `linked || lethal(q)`.
- It gives up on fuel at 519-527 ("step-guard-entry"), 604-606 and 640-645. Then no guard is set at all.
- Related: `step_guard_cover` (479); `work_guard` and `keep_out` (737, 759) take last round's damage; `step_safely`
  (11-27) routes around `avoid()`; `pack_zone` (269).

**want_home (combat/fight.cc:447-466)**
- `drawn_home` (390):
  - `recall_line` (334) is 0.315 if a visible enemy is within reach + 8, or `may_reach_within(p, 8)`; else 0.109;
  - the pack zone.
- `camp_trapped` (290) and `mono_trapped` (economy/crew.cc:328): camp fire over the exit walk.
- Willow's `exposure_here` (support.cc:72).
- `stand_lost_at` (401-435): stand_reach/walks/roster/trade with pursuit_steps 2, `lethal()` for falls, and
  `hold.keeps_us`.

**hold_outlasts (fight.cc:355)**
- last round's damage × window ≥ health, or `lethal`, or `turns_to_kill_idle`.

**Chase (fight.cc:653-814)**
- `prey` orders targets by turns per gem.
- For each target: `chase_trade` with delayed allies, `late()` joiners and a bag boost; `comeback::accept_lost`.

**Retreat (fight.cc)**
- `retreat_step` (178-270):
  - first the avoid board;
  - then its neighbours ranked by home, then **worst-case tally damage** (Σ blows + camps), stuns, bush and steps;
  - plus HomeWalk.
- `flee_camps` (87); `escape_walk` (1219, lethal at 1232).
- `sole_escape_threat` (1201) and `dash_retreat_casts` (1260).

**Self abilities (combat/self_abilities.cc)**
- `threats_near` / `danger()` (59-120): worst-case blows and camp hits, used for dash landings.
- `escape_landings` (187); `shield_wanted` (197).
- `shield_if_needed` (627): cast if any blow hits.
- `HealGate` (530-568):
  - the rate is camp fire + **0.234 × blows**, the only expected-value use outside plan;
  - its fallback is health ≤ all blows.

**Abilities (combat/abilities.cc)**
- `stun_worth` (103-124): Strike.at(d) is the value of a stun.
- `enemy_cast` (332); escape casts (361-391); `engagement_near` holds a cast (470).

**Support (combat/support.cc)**
- `exposure_at` (28-44): `bound()`'s doubled damage, threat and stuns, camp reach. It drives Willow's and Prism's
  stations, guard and retreat.
- `recovered_for_work` (151): health ≤ damage_bound.

**fixc (combat/fixc.cc:33-73)**
- The bush threat (Strike with ready slots against the basic one), and `fixc_commit`'s pursuit sum of
  strike_with(e, 0).

**Turn order (model/turn_order.cc)**
- `contact_priority` (171-190): the band level is 16 × **Σ Strike.at(d)** / health, open ground, no Reach.
- `plain_priority` (196): tie_hit; the unseen distance by bisection.
- `offer_channel` (445-470): threats_at blows that cancel.
- `may_escape` / `offer_escape` (491-540): worst-case sums against health.

**Pathing (model/pathing.cc)**
- The guard is applied as walls: 727, 809, 893, 964, 1194, 1409, 1888.
- `route()` (991-1010) turns avoid into walls, except our own region. There are no graded danger costs.
- `fight_near` (1217-1241) withholds the travel dash.

**Banking (economy/bank.cc)**
- `tribute_safe` (144-150): last round's damage × window, and `turns_to_kill_idle`. It gates every tribute start and
  keep (`tribute_ok` 791-799, `continue_tribute` 1345, `carry_bag` 1453, `take_hop` 900).
- `may_chain` (1268): may_reach_within(2).
- `recall_to_bank`, `recall_outruns`, `recall_to_farm` (1276-1303) and `continue_recall` (1393-1415): threatened,
  may_reach_within.
- `ring_quiet` and `watched` (875-920), `strike_eta` and `safer_altar` (1100-1142).

**Farm (economy/farm.cc)**
- `recall_line` → spare_health and trip budgets (642-646).
- `recall_out` (978-981): threatened plus recall_outruns.
- `struggling` (1017-1027): a fixed 0.315 line.
- pack_zone walls (845-875, 2286-2410).

**Capture (economy/capture.cc)**
- `any_threat()` gates (412, 446, 497); it is map-wide.
- `capture_recall` (598): threatened.

**Other economy**
- shop.cc: `wants_shop` (699) is off if threatened; `note_upkeep` (84-95) splits damage between camps and champions
  for emblem values.
- home.cc: `home_room` / `home_fires` (15-136).
- siege.cc: the kite exposure (755-785).
- crew.cc: crew budgets.

### 1.3 Five semantics

Ocean's danger estimates fall into five classes. Each consumer above belongs to one:
1. **Expected next-turn damage:**
   - plan_strikes' tile danger (0.234 × blow);
   - HealGate's rate;
   - camp_damage(worst = false).
2. **Worst-case next-turn damage:**
   - damage_bound, tally (retreat), shield_at and the heal value in plan;
   - escape bids, self_abilities `danger()`.
3. **Any-hit or probability booleans:** threatened (recall, shop, capture, banking), bound().threat (support),
   shield_if_needed.
4. **Worst-case lethal:**
   - lethal (plan, guard, stand_lost_at, hold_outlasts, escape_walk);
   - may_escape.
5. **Deterministic multi-turn:**
   - the fight sims (step guard, want_home's stand, chase, turns_to_kill_idle → tribute_safe, hold_outlasts);
   - reachability (may_reach_within → recall_line, may_chain, recall_outruns).

### 1.4 Inconsistencies found (they drive oscillation or mispricing)

1. **Guard ≠ want_home.**
   - The step guard (guard.cc:502) walls a tile only if `fight_of(fight_key(q))` is lost, or falls and lethal.
     want_home also leaves for walkers within pursuit_steps (stand_walks), camps (camp_trapped), the recall line and
     the pack zone (drawn_home).
   - So plan_strikes can choose an unguarded tile that want_home leaves next turn (strike in, retreat out). The guard
     also covers radius 1-2 only. plan's own lethal check is at grid_r only (2257).
2. **The guard disappears under fuel pressure.** With the shortcuts at guard.cc:521/605/644, plan_strikes prices
   tiles with no guard at all, exactly in the heavy turns where fights are on.
3. **Mixed units in one score.** plan subtracts expected danger (0.234 × blow) but adds the shield at duration ×
   worst-case damage (693-695) and the heal at 8 × worst case (1118). In plan's own danger units, a shield is valued
   up to 1/0.234 ≈ 4.3× the danger it removes *(inference: those weights may have been tuned to compensate)*.
4. **Mixed units in rlg.** The `oc-reply`/`rlg` wiring gates per query (`fuel() < min_fuel` inside the pricing loop),
   so tiles priced before and after the gate crosses 40k get learned and flat danger in one search.
   - The learned danger averages ~55 against the flat 41 (§2.3), so a crossing biases the choice towards the tiles
     priced flat.
5. **One enemy, different chances.**
   - plan prices a visible enemy at a 0.234 chance.
   - threatened() treats the same blow as certain: any visible hit cancels a recall or shop.
   - contact_priority uses the open-ground Strike, not Reach.
6. **Camps.** turns_to_kill_idle prices camps at expected (weighted) damage; lethal and threatened at worst.
7. **Recall line.** recall_line moves farm and crew budgets, but struggling (farm.cc:1024), the siege kite
   (siege.cc:654) and Prism's usable health (support.cc:524) use the fixed 0.315.

### 1.5 Which consumers matter most

Evidence from the lab, and *(inference)* from where the decisions sit:
- **want_home / stand_lost_at** has the largest stakes per decision. Combat lab exp 2, 30-round flips:
  - retreat → stay costs 0.93;
  - stay → retreat costs 0.19 on average, but a learnable subset gains 0.04-0.05 a stay decision.

  It is a multi-turn deterministic simulation, so a one-turn danger model can feed it but not replace it.
- **tribute_safe / continue_tribute and the recall keeps** gate scoring directly. Worst case is right for losing a
  bag. threatened() is any-hit, where an expected value or probability is right: a cancelled recall only costs
  turns.
- **plan_strikes**: the most frequent fight decision. Exp 1 found ocean's tile choice "as good as these features
  allow", and the phase-1 swap was level (49.9% over 30,720 games). Its accuracy gain alone does not pay.
- **The step guard**: it shapes every fight step, and §1.4 items 1-2 put it at the centre of the oscillation.
- **retreat_step**: frequent. A worst-case ranking makes it treat a 0.1-chance blow like a certain one.
- **heal and shield**: Willow, Varg, Heart of Ruin and Prism maps.

## 2. Compression results (question 1)

### 2.1 Method

- **Data:** the phase-1 danger rows with blow > 0, the only rows any consumer prices. 0.6% of blow-0 rows see a hit,
  mean 1.6 damage, so Reach's support is sound.
  - Train: 1.2M of the 1.94M train rows (oo, oa and ao configurations).
  - Held out: all 319,252 rows of the held-out frames (split by game).
  - Ordering: 54,841 counterfactual rows (`alt-va-*`, --alt 5).
- **Metrics,** as phase 1's (`train.py`):
  - hit log loss;
  - damage R², overall and per configuration (oa and ao are opponents astraeus plays);
  - mean prediction against the true 56.0;
  - within-decision ordering on the alternatives, per enemy and summed per alternative (`train.pairwise`).
- **Cost tiers of features:**
  - **A:** free at a query (d, blow, blow_stuns, strike_at) or fixed per enemy for the turn (types, hp, cooldowns,
    e_turns, channel, the alternative targets' features). A per-enemy feature costs once per enemy per turn.
  - **B:** per tile, shared by the enemies (health near p on both sides, p_bush, e_ttd).
  - **C:** needs `Reach::sources` at the tile, a second pass like Reach::at (n_src*, src_here).
- **Fuel:** `fuel_bench.cc` compiles each evaluator with the bot's flags (wasi-sdk-33, -O3, simd128). It counts
  executed instructions with wabt's tracing interpreter over 64 held-out rows, excluding operators wasmtime meters
  at 0. Fuel is ~1 a wasm instruction (AGENTS.md).
  - This measures the evaluator only.
  - Feature costs are estimated from the code and its own comments. Mark them *(estimate)* until a bot bench
    confirms them (§6, step 1).

### 2.2 Results (held out)

| Candidate | Features (tier) | Hit log loss | Damage R² (oo/oa/ao) | Mean | Order / enemy | Order / alt | Eval instr. / query (measured) |
|---|---|---|---|---|---|---|---|
| ocean 0.234 × blow | blow | 0.642 | 0.212 (.213/.206/.217) | 41.4 | 0.775 | 0.780 | ~5 |
| refit 0.325 × blow | blow | 0.642 | 0.248 | 57.5 | 0.775 | 0.780 | ~5 |
| refit, capped at our health | blow, my_hp | 0.624 | 0.241 | 49.4 | 0.775 | 0.780 | ~8 |
| full m1 (4 × 60 trees × 16) | 48 (A-C) | **0.424** | **0.442** (.443/.436/.447) | 54.9 | **0.845** | **0.839** | 3,647 + features |
| lean 12 × 32 | 28 (A-C) | | 0.381 (.380/.378/.385) | 56.4 | 0.839 | 0.833 | 374 + features |
| table blow × t[e_turns, d, e_type] | 3 (A) | 0.520 | 0.329 | 57.5 | 0.813 | 0.811 | 48 |
| GAM 1-D, lean's A features | 20 (A) | 0.502 | 0.324 | 48.6 | 0.837 | 0.829 | |
| GAM 1-D, lean's 28 | 28 (A-C) | 0.476 | 0.347 | 48.6 | 0.836 | 0.827 | |
| GAM 1-D, all 48 | 48 | 0.475 | 0.346 | 48.5 | 0.840 | 0.832 | |
| GAM, lean's A + 5 pairs | 20 (A) | 0.482 | 0.346 | 49.3 | 0.842 | 0.835 | |
| **GAM, lean's A + 5 pairs, capped** (rec.) | 20 (A) | **0.482** | **0.389** (.388/.387/.393) | 54.0 | **0.842** | **0.835** | **148** folded |
| same, blow in 16 bins | 20 (A) | 0.483 | 0.386 | 53.7 | 0.843 | 0.836 | 148 |
| same + a GAM for damage given a hit | 20 (A) | 0.482 | 0.390 | 55.3 | 0.830 | 0.823 | |
| GAM, lean's 28 + pairs, capped, damage GAM | 28 (A-C) | 0.469 | 0.403 | 55.2 | 0.836 | 0.825 | |
| **min5 GAM capped**: d, blow, stuns, e_turns, e_type + 3 pairs (fallback) | 5 (A) | 0.520 | 0.331 | 54.8 | 0.839 | 0.835 | ~148, per-enemy ~0 |
| min7 (+ my_hp, e_dash_ready) | 7 (A) | 0.510 | 0.348 | 54.7 | 0.840 | 0.834 | |
| per-enemy terms only (no d, blow, stuns in p) | 17 (A) | 0.538 | 0.323 | 49.3 | 0.774 | 0.776 | 1 multiply |
| 8 free trees × 8 leaves, capped | 20 (A) | 0.481 | 0.368 | 53.9 | 0.829 | 0.826 | ~170 *(estimate, 24 splits)* |

- The five pairs are (d, e_type), (d, e_dash_ready), (blow, e_turns), (e_turns, e_type) and (blow, my_hp).
- "Capped": the multiplier is min(blow, our health + shield). The constant k is the least-squares multiple of the
  multiplier given a hit: 0.903 capped, 0.785 uncapped.
- The mean of the GAMs is low (48-55 against 56). It costs a little R², and a single rescale fixes it for consumers
  that need calibrated sums (§3.6).

Other evaluators measured: a 1-D GAM of 17 features evaluated in full each query, 1,448 (expf alone is 86); the folded
16-bin 3-feature form, 96.

### 2.3 What the results say

1. **Ordering comes from the per-tile terms (d, blow, stuns, with e_type and e_turns), not the per-enemy context.**
   - min5 orders alternatives as well as the lean and full models: 0.839/0.835 against 0.839/0.833 and 0.845/0.839.
   - The per-enemy-only model orders no better than ocean's flat term (0.774).
   - Tier C (Reach::sources, the costliest part of the lean features) adds ~0.01-0.02 R² and nothing to ordering. Drop
     it.
2. **The per-enemy context buys calibration across enemies.**
   - R² rises from 0.33 to 0.39 and log loss falls from 0.52 to 0.48.
   - Summed danger over a turn's enemies, the full model reaches R² 0.449 against the flat 0.217 (`lethal2.log`).
3. **Capping the multiplier at our health is the cheapest gain:** +0.04 R² at no cost, because no hit takes more than
   we have.
4. **The rest of the gap to the full model is interactions** on the hit logit: log loss 0.48 against 0.42.
   - Small free trees (8 × 8) do not close it (0.481).
   - A 16-48-cell 2-D table per pair is as far as a table form goes cheaply.
   - *(inference)* The remaining gap is spread over many weak interactions. It is not worth a per-query tree.
5. **Binning blow into 16-32 quantile bins loses nothing** (R² 0.386-0.387, ordering unchanged), so tables of 16-32
   entries suffice.

### 2.4 Lethal and summed danger (`lethal.py`, `fold.py`)

- **Data:** 287,740 held-out decisions, each of our turns with its visible enemies whose blow > 0. 90.1% have one such
  enemy, 9.0% two and 0.9% three or more.
- **Killed:** damage taken ≥ our health + shield in 1.45% of decisions.
- Caveat: the rows hold no camps and no unseen enemies, and a victim felled by the first enemy keeps only that row.

| Lethal test | Flags | Recall | Precision |
|---|---|---|---|
| worst case Σ blow ≥ health (ocean's `lethal` without camps) | 2.64% | 0.891 | 0.488 |
| expected sum ≥ health (full model) | 0.34% | 0.173 | 0.741 |
| P(killed) with damage = E[dmg given hit], ≥ 0.10 | 1.52% | 0.597 | 0.568 |
| **P(killed) with damage = blow, p = folded GAM, ≥ 0.10** | 2.49% | 0.888 | 0.515 |
| same, ≥ 0.20 | 2.22% | 0.866 | 0.565 |
| same, ≥ 0.35 | 1.86% | 0.794 | 0.619 |
| same with the full model's p, ≥ 0.20 | 2.03% | 0.857 | 0.610 |

- **Pblow(killed):** P(Σ over hitting enemies of blow_i ≥ health), the hits independent with probability p_i.
  - Log loss 0.0297 with the folded GAM, 0.0286 with the full model; a constant rate gives 0.0756.
  - It is calibrated: 0.25-0.5 predicted 0.39, observed 0.46; 0.5+ predicted 0.70, observed 0.74.
- **Expected value has no place in lethal tests:** it misses 83% of kills.
- **Worst-case damage with a learned hit probability is the right lethal form.** It is the same p as the expected
  damage, so the two cannot disagree on who is dangerous.
- The 11% of kills that Σ blow misses lie beyond Reach's one-turn bound. *(inference)* They are a second turn's hits,
  splash, or damage that hp/shield reads miss. A probability cannot recover them; only the multi-turn layer (§3.5)
  can.

### 2.5 Recommendation

1. **Primary: the capped GAM on lean's A features with five pairs**, folded per enemy.
   - Its accuracy is lean's or better, except log loss against the full model.
   - It costs 148 instructions a query beyond the Reach blow every consumer already computes, plus ~1.5k a visible
     enemy a turn for z_e and its tables *(estimate: the 1,448 unfolded evaluation measured, plus ~300 for the
     tables)*.
2. **Fallback (same units): min5**, the same query cost with no per-enemy pass. It is the turn mode when fuel is short
   (§4).
3. **Not recommended:**
   - the lean or full trees (4-40× the per-query cost, and tier C features);
   - per-query tree ensembles of any size.
   - Quantizing the trees saves little, because the cost is in the splits, not in the floats.

## 3. Unified danger architecture (question 2)

### 3.1 The object

A `Danger` section inside `Safety`, so it lives and dies with the beliefs. Its cache is keyed by
`Safety::generation()`, so a refresh or invalidate drops it with everything else. Sketch:

```cpp
struct Hit {               // one enemy at one tile, before our next turn
    Blow blow;             // Reach::at (visible) or unseen_blow
    float p = 0;           // P(it hits us there)
    float expected = 0;    // min(blow, health) * k * p
};
struct TileDanger {        // every credible threat and camp at p
    float expected = 0;    // Σ Hit::expected + camp_damage(p, false)
    float worst = 0;       // damage_bound(p): Σ blows + camps at full Strength
    float p_any = 0;       // 1 - Π(1 - p_e) (camps in reach: 1)
    float p_kill = 0;      // P(camps + Σ_{hitting} blow_e >= health + shield)
    bool stuns = false;
    std::uint16_t hitters = 0;  // bit e: blow hits (fight_key's enemy bits)
};
class Safety {
    Hit hit(const ChampionBelief& e, vec2 p);     // memoised beside Reach::Memo (same 64-entry slot)
    const TileDanger& danger(vec2 p);              // memoised, 32 tiles; lazy fields
    float expected_bound(const ChampionBelief& e, int d);  // >= hit(e, q).expected for any q at distance d
    Mode mode();                                   // fixed at first use this generation (§4)
};
```

- **Per enemy, at its first `hit()` this generation:**
  - gather the ~17 per-enemy features, as `reply.cc`'s `fixed_danger` does;
  - sum their tables into z_e;
  - fold the pairs with a per-tile feature into per-enemy tables: td[d] (d, e_type and d, e_dash_ready),
    tb[bin(blow)] (blow, blow × e_turns, blow × my_hp) and ts[stuns];
  - fill `expected_bound(e, d)` for d = 0-6:
    `k × min(Strike.at(d), hp) × σ(z_e + td[d] + max over bins b ≤ bin(Strike.at(d)) of tb[b] + max ts)`.

  Strike bounds Reach (the REACH-BOUND debug check, safety.cc:2349), so this stays admissible for plan's
  branch-and-bound.
- **Unseen threats:** `p = chance × p_unseen(e)`, where chance = |possible ∩ reach| / |possible| as today.
  p_unseen is the model at d = the unseen blow's distance. That is an untrained extrapolation until §5.1's unseen rows
  exist, so until then p_unseen = hit_given_reach rescaled to the new calibration.
- **Camps** stay deterministic: an awake member in reach with no nearer champion hits. They enter `expected` at
  weighted strength and `worst` and `p_kill` at full strength. *(The data has no camp rows: §5.5.)*
- **The model's constants** are a generated header, `danger_model.h`: tables, bin edges, k and the sigmoid table.
  Generate it with an export like `lean.py export`, and check it with a `check_lean.py`-style identity test on
  20k rows.

### 3.2 What each consumer reads

| Consumer | Today | Reads | Why |
|---|---|---|---|
| plan_strikes exact price (plan.cc:2230) | 0.234 × blow | `hit(e, p).expected` | Expected value is what a score trades against hits |
| plan_strikes share and unpriced tiles (2220, 2281) | 0.234 × Strike.at | `expected_bound(e, d)` | Must stay an upper bound for the branch-and-bound |
| plan unseen (2244-2254) | 0.234 × unseen blow | `hit(e, p).expected` (unseen) | Same units |
| plan shield and heal value (693, 1118) | duration or 8 × damage_bound | duration / 8 × `danger(p).expected` | Units as the danger it offsets (§1.4.3) |
| plan lethal (2257), guard lethal (guard.cc:672-675), stand_lost_at falls (fight.cc:407) | worst ≥ health | Phase A: `worst ≥ health`, unchanged. Phase B: `p_kill ≥ τ` | §3.4 |
| retreat_step ranking (fight.cc:178) | tally worst | Clear (worst == 0) first as now, then `expected`, then `p_kill` | A 10% blow is not a certain one |
| HealGate rate (self_abilities.cc:561) | camps + 0.234 × blows | `danger(p).expected` | Already expected |
| shield_if_needed (627) | any hit | `danger(here).expected × duration ≥ shield value / margin` | One unit; keep any-hit at first |
| threatened, recall and tribute keeps, shop (safety.cc:2716) | any visible hit | Phase A unchanged. Later `p_any ≥ recall_risk'` | A recall cancel costs turns, not a life: probability belongs here |
| contact_priority (turn_order.cc:171) | Σ Strike.at / health | Σ `expected_bound(e, d)` / health | Same p, no Reach needed |
| may_escape / offer_escape (turn_order.cc:491-540) | worst sums | `worst` (unchanged) or `p_kill` | Worst case |
| support exposure (support.cc:28) | bound().doubled, threat | `worst` (doubled) and `p_any` | Same fields |
| Fight sims (guard, stand, chase, turns_to_kill_idle) | deterministic | The roster `hitters` from the same cache. Hit rates stay 1 in phase A | §3.5 |
| tribute_safe, hold_outlasts | turns_to_kill_idle, worst | Unchanged (worst case) | A bag is lost for good |
| recall_line, may_chain, recall_outruns | may_reach_within | Unchanged (multi-turn reachability) | No one-turn model applies |

### 3.3 How consistency is guaranteed

1. **One cache, one generation.**
   - Every danger number of a turn comes from `Safety::hit` or `Safety::danger`, memoised under
     `Safety::generation()`.
   - Two consumers asking about the same (enemy, tile) in one generation get the same bits.
   - `refresh()` after a kill bumps the generation, as today, so a later consumer sees the new beliefs, as Reach and
     the fight memo already do.
2. **One mode a turn.**
   - The fuel mode (§4) is decided at the cache's first use and stored in it. No consumer reads `fuel()` to choose
     units. rlg's per-query gate is removed.
   - A consumer that cannot afford a query skips its decision as today: a shortcut. It never substitutes a different
     danger.
3. **The same fallback units.**
   - Every mode is the same model at coarser resolution: full → min5 → a calibrated per-enemy constant. Each is
     unbiased in mean, so a mode change between turns shifts no threshold systematically.
4. **One verdict for "would we leave this tile".**
   - The step guard is redefined as `stand_lost_at(q)` with the same roster rules want_home uses: walkers, camps,
     holds, and the recall line's drawn_home where it differs.
   - Both read the fight memo (`fight_of`, keyed by roster).
   - A tile plan_strikes may end on is then exactly a tile want_home keeps us on, given the same beliefs.
   - Where the guard runs out of fuel, the remaining tiles of radius 1-2 are marked *unknown*. plan_strikes prices an
     unknown tile only if `p_kill < τ_guard` from the cache (cheap); otherwise it drops it. It does not fall back to
     "no guard at all".
5. **Hysteresis for want_home.**
   - The danger cache records the tile plan_strikes chose and the stand verdict it assumed (in Memory, one entry).
   - Next turn, if want_home flips that verdict with *no belief change* about the hitters (same roster key, no new
     damage taken), the flip is logged in debug.
   - This is a consistency metric, not a behaviour change. Its rate is the target of steps 2-3 in §6.

### 3.4 Worst case and expected value

| Keep worst case | Use expected value |
|---|---|
| lethal guards (plan, step guard, escape walk): a death costs `life_value` 277 plus the bag and 60 rounds | Tile pricing in the strike search (danger against hits) |
| tribute_safe, hold_outlasts (a bag lost for good) | retreat_step's ranking among unguarded steps |
| Cassi/Issac "falls" checks (both bodies die) | heal and shield valuation |
| escape bids (turn_order may_escape) | contact priority bands |
| Fight sims' rosters (who could join) | threatened() for recall/shop (as a probability, p_any) |

- Phase B replaces `worst ≥ health` with `p_kill ≥ τ`, which is still a tail test with worst-case damage per hit.
- Held out, τ = 0.2 keeps 97% of worst case's recall (0.866 against 0.891) with 16% fewer flags.
- A flag is a lost tile or a forced retreat, so fewer false flags mean more good strikes. τ is tuned by A/B, starting
  at 0.1.

### 3.5 Multi-turn danger and the fight simulation

- The model is one turn. The sims reason over 17 own turns, assuming every hit lands.
- **Phase A (this plan) feeds them only the shared roster** (`TileDanger::hitters`, the same Reach blows). Their
  rosters then match plan's priced enemies exactly. They already do through `fight_key`; the new part is the guard
  using stand rules (§3.3.4).
- **Phase C (later, needs §5.2's data): a learned stand value P(lose | stand at p, H rounds).**
  - Inputs: the sim's own outputs (turns_to_kill both ways, self_falls, walkers, camps), plus the one-turn p_e of each
    hitter and our bag.
  - Labels: the combat lab's forced-stay rollouts.
  - This is exp 2's learnable stay → retreat flip (+0.04-0.05 a stay decision held out), made a shared function that
    the guard and want_home both call.
  - Do not discount the sim's damage by p: the sim's verdict is used as a worst-case filter, and expected-damage sims
    would say "won" on most lost fights.

### 3.6 Re-fitting ocean's other terms

The learned danger averages ~54 on the priced rows; the flat term averages 41. A swap raises plan's danger about 30% on
average. That is why phase 1's "lean × 0.75" arm (a rescale by hand) was as good as rlg.

1. **Unit match first.** Scale the learned expected damage by c = mean(flat) / mean(learned) on plan's priced tiles.
   - c is measured by the lab dump (≈0.76 here: 41.4 / 54.0).
   - Only the ordering changes: A/B that alone.
2. **Fix the mixed units (§1.4.3)** in the same units.
   - Shield and heal valued by expected damage, each with one scalar weight (initially 1 / hit_given_reach × c, which
     reproduces today's values on average).
   - A/B separately.
3. **Joint refit in the lab.**
   - SPSA (tune.py-style, on the lab reward, paired, val10k frames) over 4-6 scalars: danger scale c, shield weight,
     heal weight, the progress step `S.step`, camp weight in camp_at, and τ for p_kill.
   - Start from step 2's values. Then the A/B.
   - Combat lab exp 1 found no single reweighting of the score's parts moves held-out gain beyond ±0.005 under the
     *flat* danger. Under a sharper danger the optimum may move; the SPSA tests that cheaply before any A/B.
4. **Consumers with thresholds** (recall_risk, τ, HealGate) are re-tuned once each, by A/B on a fresh suite, never
   jointly with the score scalars.

## 4. Fuel budget and fallbacks

**Per query:**
- The new work is 148 instructions (measured), plus whatever Reach::at costs where the consumer did not already need
  the blow.
- Every consumer in §3.2 but contact_priority already computes the blow. contact_priority reads `expected_bound`,
  which needs no Reach.

**Per enemy per turn:**
- ~1.5k *(estimate)* for features and folding, only for visible enemies that some consumer asks about.
- 0 on turns with no visible enemy within max_reach + 2 of us (most farm turns).

**Per tile aggregate:** `TileDanger` sums ≤ 3 enemies.
- p_kill by enumeration costs ≤ 2³ subsets (~150 *(estimate)*). It is computed only when a lethal or p_kill field is
  read, and only once `worst ≥ health`, the only case where p_kill > 0. 97% of decisions never need it.

**Per fight turn** *(estimate)*: queries come from plan's exact prices (≤ 6 a search, ~1.1 tiles typical, × 1-2
enemies), retreat's ≤ 8 neighbours and the heal gate.

| Turn | Per-enemy passes | Queries | New fuel |
|---|---|---|---|
| Typical fight turn (1-2 enemies) | 1.5-3k | 10-20 × 148 = 1.5-3k | **3-6k** |
| Heavy turn (3 enemies, a search and a retreat pricing) | 4.5k | 40 × 148 = 6k | **~10k** |
| Without visible enemies | 0 | 0 | 0 |

- For comparison:
  - ocean's lab fight turns average 68.1k, p90 87.8k, 0.57% out of fuel (`lab/base-bb`);
  - rlg (lean, ungated) averaged 68.3k, +0.2k a turn, but rose to 0.92% out of fuel;
  - rlg gated at 40k: 0.60%.
- *(inference)* Lean's ungated OOF rise is too large for its query cost alone: at ~1k a query and ~2-6 queries, it is
  ≤ 6k on few turns. Part of it may be behaviour, with fights chosen nearer enemies making later sims and guards
  dearer. §6 step 1's shadow arm settles this before any wiring.

**Modes**, chosen once per turn at the cache's first use, from `fuel()` against
`fight_cost_estimate() + query_cost_estimate()` (safety.h:433-437), as the step guard already budgets:

| Mode | When | Cost | Accuracy (held out) |
|---|---|---|---|
| full | fuel ≥ need + 15k | as above | log loss 0.482, R² 0.389, order 0.842 |
| min5 | need ≤ fuel < need + 15k | 148 a query, no per-enemy pass | 0.520, 0.331, 0.839 |
| flat-calibrated | below that, or a turn resumed after running out | 1 multiply: k × min(blow, hp) × p̄ | 0.624, 0.241, 0.775 |

- All three are unbiased in mean (§3.3.3), and each has its own `expected_bound`. A turn never mixes them.
- The 15k margin is a first guess, tuned by the OOF census (§6 step 1).
- Cost is cut further by (first, no accuracy change):
  - building z_e lazily, per enemy actually queried;
  - keeping z_e across turns while its quantized inputs are unchanged (cooldowns and health bins);
  - sharing the per-enemy feature gathering with `reply.cc`'s `fixed_danger` code, whose loops already exist.

## 5. Training and labelling changes

1. **Unseen threats.**
   - Today's rows are visible enemies within 8 only (`reply::dump`).
   - Add a row per credible unseen threat at the end tile:
     - features: chance, |possible|, staleness in rounds, distance from the possible set, its Strike at that
       distance, e_turns, type;
     - label: the same hitlog damage.
   - This replaces p_unseen's placeholder, the flat rate, and calibrates threatened() and recall keeps. Small:
     ~10-20k frames of the same bank2 split.
2. **Multi-turn stand labels (phase C).**
   - Rerun exp 2's `--flip` design with `--hitlog`, forcing *stay* at want_home decisions and at step-guard rejections.
   - Labels over 5 and 10 rounds: died, damage taken, bag lost, enemies felled.
   - Features: the sim's outputs and the one-turn p of each hitter.
   - ~20k frames, both opponents.
3. **Retreat paths.**
   - A lab hook to ban or force retreat_step's option k, like the strike search's ban list.
   - Label each option with damage taken over the next 2 turns, and whether a pursuer kept contact. This judges
     expected-value ranking against worst case directly. ~10k frames.
4. **On-policy refresh.**
   - Once step 3 (plan_strikes) of §6 changes behaviour, regenerate one round of train rows with the candidate bot,
     DAgger-style.
   - Check held-out R² and ordering on rows from the *old* policy too. They should not drop by more than noise
     (~0.005 on 319k rows *(estimate)*).
5. **Camps.**
   - Confirm from the hitlog that camp hits are as deterministic as `camp_damage` assumes: nearest champion, ties by
     turn order. If they are, camps need no model.
   - One `build.py` pass over existing rollouts, counting camp damage per turn against `camp_damage(p, true, true)`.
     No new games.
6. **Fit hygiene.**
   - Store the exported tables' training commit and the val metrics in the header comment.
   - Keep the astraeus configurations (oa, ao) in held-out reporting. The candidate's R² was .388/.387/.393, so it
     generalises to an opponent it trained on partly, but ladder opponents are not in the data. Fish stays out of the
     lab.

## 6. Validation sequence and migration order

Each step is a separate variant of the then-current ocean (`./copybot`), A/B'd against its own frozen base.
- With a step's knob off, `bench.py` replays must be byte-identical at 100M (default 16 and wide 52).
- A/Bs follow AGENTS.md:
  - fast runner, own drafts (`--no-test-draft` with directory bots);
  - 10,240-game dev screens on a fresh ladder-mix suite, 20,480 held out on another fresh suite;
  - a `--mix varied` 10k for robustness;
  - each SPRT its own `--sprt-seed`.

| Step | Change | Test | Pass |
|---|---|---|---|
| 0 | Offline: export `danger_model.h`, check C++ = Python on 20k rows (max abs diff < 1e-4), p_kill calibration per opponent | `compress.py`, `fold.py`, a `check_lean.py` copy | Identity |
| 1 | `Danger` cache in Safety, **shadow mode**: computes every field consumers would read, then discards it | bench 100M identical; `--fuel 0` OOF census (`tools/fuel/census`) on the 28 heavy maps; lab shadow arm (val10k, real fuel) | Fuel per fight turn within §4's estimate; OOF ≤ +3% relative. This splits lean's OOF rise into cost and behaviour |
| 2 | Consistency fixes, flat danger kept: the guard as stand rules (§3.3.4), *unknown* tiles instead of a dropped guard, one mode a turn | Debug counters: strike-then-leave rate, want_home A-B-A flips, chosen-tile-guard-rejected; lab paired; A/B 10k + 20k | Counters fall; A/B ≥ 50 held out. This is the step the user's oscillation concern is about, tested before any new model |
| 3 | plan_strikes: learned expected damage, unit-matched (§3.6.1), with `expected_bound` for shares and unpriced tiles | Lab paired (marks 10 and 30); A/B 10k + 20k | ≥ 50 held out, OOF ≤ base + 3% |
| 4 | Shield and heal valued in the same units (§3.6.2) | Lab; A/B with a Willow/Varg/HoR map subset reported | ≥ 50 |
| 5 | retreat_step ranked by expected damage among unguarded steps | Lab retreat options (§5.3); A/B | ≥ 50 |
| 6 | Lab SPSA of the score scalars (§3.6.3), then A/B of the result | tune.py-style, paired lab reward; A/B 20k + fresh 20k | Gain held out |
| 7 | p_kill ≥ τ in plan, guard and stand falls (phase B) | A/B for τ ∈ {0.1, 0.2} | ≥ 50, with the panel non-negative |
| 8 | threatened → p_any for recall, shop and capture keeps (needs §5.1) | A/B | ≥ 50 |
| 9 | contact_priority on `expected_bound` | A/B | ≥ 50 |
| 10 | Phase C: the learned stand value in guard and want_home (needs §5.2) | Lab flips, then A/B | Gain held out |

- Steps 2, 4 and 5 are independent and could screen in parallel, each with its own seed. Steps 3 and 6 depend on 1.
  Steps 7-9 depend on 3.
- A step that is level (within noise) at no fuel cost is kept only if it removes a code path. Otherwise it is dropped.

## 7. Risks, and what to drop

- **Accuracy may not turn into wins again.** Phase 1's 0.845 vs 0.775 ordering was level over 30k games.
  - This plan's bet is consistency (steps 2, 4), and cost low enough to use danger everywhere, not accuracy. If step 2's
    counters fall but its A/B is level, the oscillation is not costing games. Stop after step 3, keeping only the
    cheaper and more consistent code.
- **Fuel.** If step 1's shadow shows > +3% OOF, use min5 as the only mode: no per-enemy pass, 148 a query.
  - It loses log loss (0.52) and R² (0.33) but not ordering.
  - If even that shows, the plan keeps flat danger and does only step 2.
- **Off-policy data.** The model learned from ocean and astraeus as they are. Distribution shift after step 3 is
  handled by §5.4's refresh. Ladder opponents unlike either are untested; ladder scrims are the only check.
- **The unseen extrapolation** (§3.1) stays the flat rate until §5.1. Steps 7-8 wait for it.
- **Branch-and-bound admissibility.** `expected_bound` must stay ≥ every exact price. A debug check like REACH-BOUND
  goes in with step 3.
- **Drop first:**
  - the pressure model (neutral to negative in phase 1, +17% OOF);
  - tier C features and every tree ensemble;
  - the k regressor (it hurts ordering by 0.012);
  - p_any (step 8) if level;
  - phase C if its labels cost more than ~20k frames of lab time.

## Appendix: reproducing

```
python3 tools/pooled.py 4 -- python3 research/reply-model/compress.py cache      # rows to replays/combatlab/reply/compress/
python3 tools/pooled.py 8 -- python3 research/reply-model/compress.py run         # baselines + candidates (prefix filters: r3, r5, ...)
python3 tools/pooled.py 4 -- python3 research/reply-model/fold.py                 # folding check, blow bins, lethal with folded p
python3 tools/pooled.py 2 -- python3 research/reply-model/lethal.py               # summed danger and lethal with the full model
# fuel_bench.cc: header comment gives the wasm build and the instruction count
```
