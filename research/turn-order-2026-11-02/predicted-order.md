# Predicted enemy order (`ast-pred`) against worst case (`ast-pwc`)

The question: does a predicted enemy order do better than the worst case, keeping the worst case wherever a proof
needs it? Direction is in [TODO.md](../hyperion/TODO.md) "Turn order and ally coordination": assume enemies order
adversarially, and never fall back to an enemy keeping its order.

**Answer: no.** Every variant is level with REF and with the others. The predictor is better calibrated than either
fixed rule, but no consumer turns that into wins, and the predicted kill bids cost about +15% out-of-fuel turns.
The adversarial sparring bot punishes none of the models, REF's persistence included.

## Bots

All are on BASE (`bots/astraeus` = e9c37971 + CHANGES 293, 294) and judged against REF (`bots/variants/astraeus-294`,
the same source). Every bot has `test_draft` off, so all runs use `--no-test-draft`.

| Bot | What it is |
|---|---|
| `ast-pwc` | `ast-wc`'s worst-case model ported onto BASE (`model/enemy_order.{h,cc}` and the edits in `turn_order.cc`, `safety.cc`, `plan.cc`, `fight.cc`), plus the `double_unacted` fix. |
| `ast-pwc-nofix` | `ast-pwc` without the `double_unacted` fix. |
| `ast-pwc-dx` | `ast-pwc` with `SB` and `KB` trace lines (debug_block) for the diagnosis. |
| `ast-pred` | `ast-pwc` with predicted values: kill bids and `drop_stun` (below). Proofs stay worst case. |
| `ast-pred-kill`, `ast-pred-stun` | `ast-pred` with only the kill bids or only `drop_stun`. |
| `ast-pred-t15` | `ast-pred` with the kill bid's confidence at 0.85 instead of 0.75. |
| `ast-pred-noop` | `ast-pred-kill` that computes the predicted kill bid but never offers it. It isolates the fuel. |
| `ast-pred-learn` | **Relaxation, flagged.** `ast-pred` with one more predictor feature: the enemy team's priority-change rate in contact, learned online in the match. It learns that a static opponent is static. |
| `ast-adv2` | The sparring adversary, on BASE. Its priority is constant (raw 0 by index, payload 0) except at a band bid (kill, escape, heal, channel). A reader sees a static order until the decisive turn. Comms are out of the payload. |

**The `double_unacted` fix** (`safety.cc`, `doubles()`): `damage_bound`, `bound().doubled` and `damage_ceiling`
double a visible enemy yet to act only when `turns_before_ours(e) < 2`. Otherwise its blow is already widened to two
turns by `threat_strike`.

## 1. Why worst case was level

The tracer was `ast-pwc-dx` against REF: 2048 games on fresh-85540..85543 (50.2%), extracted to
`replays/pred-dx-ex`. The script is `scripts/dx_analyze.py`.
- `KB` gives each kill-bid candidate under the old persistence rule and under the worst case.
- `SB` gives Safety's `turns_before_ours` for every live enemy within 4 at the start of `act()`: old (last-read
  ranks) and worst case. The truth comes from the replay: the enemy's real turns before our next turn, and whether
  it hit us.

**Candidate 1, "the bids were already worst case", holds completely for kill bids.**
- `World::enemy_priorities_change` was on in 806,810 of 808,496 traced turns with an enemy within 4 (99.8%).
  astraeus's payload changes its priority, so the flag flips at the first sighting.
- Of 13,063 kill-bid candidates, 12 had the flag off and 3 flipped (2 targets died anyway).
- So `ast-wc`'s `enemy_next_rank` change does nothing against astraeus-family opponents. Its whole effect against
  REF comes through Safety (and the rare fork).

**Candidate 2, "Safety's pessimism cost as much as it saved", holds.** Worst case changes about a third of Safety's
reads within 4. It halves the dangerous error (counting too few enemy turns), but claims at least as many second
turns that never come. Rates are of reads (2048 games, 1.15M reads):

| enemy | reads | right: old / worst | too few: old / worst | too many: old / worst |
|---|---|---|---|---|
| visible, yet to act | 488,755 | 63.3% / 63.1% | 28.2% / 14.5% | 8.5% / 22.4% |
| visible, acted (settled) | 489,809 | 73.3% / 60.4% | 10.2% / 8.0% | 16.5% / 31.6% |
| unseen, yet to act | 119,384 | 57.4% / 43.7% | 23.0% / 6.0% | 19.6% / 50.3% |
| unseen, acted | 47,609 | 59.0% / 39.9% | 18.9% / 4.7% | 22.1% / 55.4% |

- The largest flip is a visible enemy yet to act, counted 1 by last read and 2 by worst case (149,402 reads, 31%).
  The second turn was real in exactly half (74,201). The enemy hit us before our next turn in 36% of the real ones
  and 23% of the false ones.
- The worst flips are settled enemies: visible and acted, counted 0 by last read and 1 by worst case (91,090 reads).
  The rules allow it, since unsettled teammates above it may drop below it. It happened 16% of the time.
- Outcomes, from the original `ast-wc` A/B (10,240 games, `replays/pred-wcfinal-ex`, `tools/replay/fight_metrics.py`):
  - ast-wc died 5.34 times a game against the baseline's 5.40 (-1.1%), and killed 4.87 against 4.82.
  - It also captured 62.72 times a game against 63.09, and earned 881.5 capture gems against 887.9 (-0.7%).
  - Fewer deaths, paid for in farm time: level.

**Candidate 3, `double_unacted` counting a two-turn blow twice:** real, and fixed in every variant here. It is not
what made worst case level. With and without the fix, `ast-pwc` played 50.53% and 50.57% on the same 10,240 games
(paired -0.04, -0.52..+0.44; 628 games differ). Out-of-fuel turns were 119,456 with the fix and 116,895 without.
The fix does not cut fuel.

**Candidate 4, "our test opponents never exploit a persistence assumption":** true, and the stronger adversary
doesn't either (section 4). REF's Safety still reads last-read ranks, and `ast-adv2` is built to look static. Yet
REF scores the same against it as `ast-pwc` (paired -0.21, -1.39..+0.96). Bidding late cannot exploit a stale
read. That takes a move search that walks into a two-turn ambush; it is not built (Next).

## 2. The enemy-order predictor (offline)

**Data.** `scripts/order_data.py` writes one row per (round r, observing team, enemy e within 4 of an observer at
round start). The observer o is the team's nearest champion.
- o's view: enemies that acted before o have set their final next priority; the others still show last round's.
  From that view come e's last-read rank next round, its worst-case `earliest` / `latest`, and whether it is settled.
- Features: health, distances, counts within 4, ranks, and the enemy team's online change rates up to r-1.
- Target: whether e acts before o next round, at o's real next slot.

Sources:
- ladder: 9510 replays in `replays/meas-ladder-ex`, 10.2M rows;
- self-play: 4268 games of `ast-measure` against `astraeus-e9c3797` in `replays/meas-ex`, 3.1M rows.

**Fits.** `scripts/order_fit.py` (ladder) and `scripts/order_botfit.py` (the in-bot model, ladder and self-play
weighted equally). They are logistic regressions in numpy (`/tmp/claude-1000/venv`; the repo's Python has no numpy).
- Separate weights for "last read says before" and "after".
- Features: ranks the enemy must climb, ranks ahead, enemy ranks before the slot / team size, an ally within 2,
  allies and its teammates within 4, its health, our lowest health within 4, it ranks first now, its team starts
  next round, we rank first.
- The online variant adds the team's priority-change rate per settled in-contact turn (prior 0.3 over 20).
- Test split: a quarter of games by hash.

A settled enemy needs no model: last read is right 98.9% (ladder) and 98.2% (self-play). The rules bound the rest.
For **unsettled enemies** (test games):

| data | rows | acts before | last read: Brier / log loss / too few | worst case: Brier / log loss | in-bot model: Brier / log loss | + online |
|---|---|---|---|---|---|---|
| ladder | 1,367,628 | 30.7% | 0.101 / 0.70 / 6.3% | 0.476 / 3.29 | 0.089 / 0.31 | 0.086 / 0.30 |
| self-play (astraeus) | 417,167 | 44.5% | 0.198 / 1.37 / 10.7% | 0.397 / 2.74 | 0.144 / 0.44 | 0.143 / 0.44 |

- **Last read is mostly right.**
  - On the ladder, an unsettled enemy that last read puts after us comes before 8.7% of the time. When last read
    says before, it is before 86%.
  - The worst case's "before" for an unsettled enemy is right 39% of the time on the ladder and 53% in self-play.
- **astraeus reorders more than the ladder.** Last read errs twice as often against it. Near-static teams (print
  dont int, NEETCoders, Sponge, Claudus Maximus) make last read exact or nearly (Brier 0.000-0.05).
- **The model's gain is calibration, not decisions.** At p = 0.5 it makes the same calls as last read: the same
  accuracy (89.9% ladder, 80.2% self-play), the same error split. Its Brier is 12% (ladder) and 27% (self-play)
  lower.
- **The online feature adds little:** Brier 0.0887 to 0.0859 on the ladder, 0.1437 to 0.1425 in self-play.
- **One static model cannot fit both fields.**
  - The combined in-bot model over-predicts jumps on the ladder: p 0.20-0.30 sees 16% before.
  - It under-predicts them against astraeus: p 0.10-0.20 sees 25% before.
  - Fitted on the ladder alone it is calibrated there, within 1-2 points per bin, and under-predicts astraeus jumps
    by 2x.
- **Where it matters, the enemy is most adversarial.** Take a kill-like situation: last read says after us, the
  enemy below 30% health, within 2.
  - It comes first 17.6% of the time on the ladder and 40.1% against astraeus, whose escape bid jumps it to the top.
    The model says 22% for both.
  - At p ≤ 0.10 it is safe in both fields (0.4% ladder, 1.6% astraeus), but that covers only 20% of the
    situations. At p ≤ 0.25 (ast-pred's gate) it covers 57-60%, and astraeus comes first 28.6% of the time.

## 3. Decision rule

- **Proofs stay worst case** (the `ast-pwc` model): Safety's `turns_before_ours` / `next_turn_round`
  (threat_strike widening, Reach, escape proofs, `controls`, `offer_escape`, `offer_channel`), channel ends, and
  camp tie hits.
- **Values use the predictor** (`p_before_next` in `enemy_order.cc`): 0 or 1 where the rules decide, 0.98 / 0.02 for
  a settled enemy, the logistic model otherwise.
  - **Kill bids** (`offer_kills`): when the worst-case slot blocks the bid, bid anyway if:
    - we act first by the read order;
    - P(target before our slot) ≤ 0.25 (`predicted_first` 0.75; `ast-pred-t15` uses 0.15);
    - side damage at the read slot kills.

    Wrong costs only an early seat: no proof depends on the bid.
  - **`drop_stun`** (`plan.cc`): a stun counts as removing the enemy's only turn before ours when Safety's second turn
    comes from `first_next` and the predictor gives it under 0.5.

## 4. Results

Fastrunner native, `--no-test-draft`, 20 fresh suites from this range. Set A is fresh-85500..85519 and set B is
fresh-85520..85539 (unused before), 10,240 games each. Paired differences use the same map and side
(`scripts/paired.py RUN_A RUN_B`). Run names are under `replays/ab/`.

| CAND | vs REF, A | vs REF, B | paired vs `ast-pwc` (A; B) | OOF CAND / REF (A) | vs `ast-adv2` (A) |
|---|---|---|---|---|---|
| `ast-pwc` | 50.5 (49.6-51.5) | 49.8 (48.8-50.7) | - | 119,456 / 98,400 (+21%) | 59.0 |
| `ast-pwc-nofix` | 50.6 | | +0.04 (-0.44..+0.52) | 116,895 / 99,659 (+17%) | |
| `ast-pred` | 50.3 (49.4-51.3) | 49.7 (48.7-50.7) | -0.20 (-0.96..+0.56); -0.07 | 137,971 / 100,484 (+37%) | 58.9 |
| `ast-pred-kill` | 50.7 | | +0.18 (-0.47..+0.82) | 136,021 / 99,106 (+37%) | |
| `ast-pred-stun` | 50.2 | | -0.35 (-0.97..+0.27) | 119,309 / 100,117 (+19%) | |
| `ast-pred-t15` | 50.2 | | -0.37 (-1.10..+0.36) | 134,305 / 99,579 (+35%) | |
| `ast-pred-noop` | 50.5 | | -0.02 | 134,846 / 98,055 (+38%) | |
| `ast-pred-learn` (relaxation) | 49.8 (48.8-50.8) | 49.3 (48.3-50.2) | -0.74 (-1.67..+0.18); -0.49 | 137,785 / 99,071 (+39%) | 59.2 |
| REF (`astraeus-294`) | | | | | 59.3 (58.3-60.2) |

Across A and B (20,480 games): `ast-pwc` 50.15%, `ast-pred` 50.01%, `ast-pred-learn` 49.53%. `ast-pred-learn` against
`ast-pwc` is -0.62 paired (-1.28..+0.05).

**Against the sparring bot**, paired on the same 10,240 games:

| | `ast-pwc` | `ast-pred` | `ast-pred-learn` |
|---|---|---|---|
| vs REF | -0.21 (-1.39..+0.96) | -0.40 (-1.57..+0.77) | -0.08 (-1.26..+1.10) |

`ast-pred-learn` against `ast-pred` is +0.32 (-0.50..+1.14). Nothing is punished.
- `ast-adv2` is 9 points weaker than REF: REF wins 59.3%. It loses the idle near-late order (CHANGES 293) and the
  danger buckets.
- Its static order does fool the learner: its in-contact change rate reads near 0. But a fooled kill bid only
  wastes a seat.

**Fuel.** The predicted kill bid costs out-of-fuel turns, not decisions.
- `ast-pred-noop` computes the bid and never offers it: +15k out-of-fuel turns over `ast-pwc` (+13%), with the same
  wins (paired -0.02).
- Against astraeus the worst-case slot blocks nearly every unsettled target. So the predicted path runs a second
  `side_damage` (allies' `two_turns`, `strike_with` per spell subset) at the turn end, on the turns already near
  the limit.
- `bench.py` against hyperion shows +0.18% total fuel, but over-100k turns up 2% (1538 to 1569): the cost lands in
  fight turns.
- `ast-pwc` itself is +21% (+17% without the fix), as `ast-wc` was: Safety's wider threats, not the model's own work
  (worst-case.md "Fuel").

## Conclusions

- **Worst case is level because, against astraeus-family opponents, the kill bids were already worst case.** The
  persistence fallback switches off at the first payload change. What remains is Safety:
  - it halves the dangerous undercounts;
  - it doubles the false second turns, mostly on settled enemies, where the rules allow a jump that happens 16% of
    the time;
  - deaths fall about 1% and farm falls about 0.7%.
- **A predictor is better calibrated but is no better at decisions.** Last read is right 80-90% of the time for
  unsettled enemies. The model mostly adds calibrated probabilities around last read's calls, and no consumer here
  converts them.
- **The one place a prediction could relax a value is where the enemy is most adversarial.** A low-health enemy in
  our reach bids to escape: astraeus jumps 40% of the time, the ladder 18%. Predicted kill bids there are level and
  cost fuel.
- **Recommendation: no relaxation.** Keep worst case for every order question, as the user directs. `ast-pwc` is the
  rule-compliant form on BASE, level (50.15% of 20,480), and +21% out-of-fuel turns. Its fuel, not its play, is what
  holds it back, as worst-case.md found.
  - `ast-pred`'s value relaxations are safe against an adversarial orderer. Wrong, they cost only an early seat or
    a misvalued stun, and the proofs are untouched. They gain nothing and cost fuel, so they are not worth shipping.
  - `ast-pred-learn`'s online feature is the relaxation the user's rule forbids. It gains nothing either (-0.62
    against `ast-pwc` over 20,480 paired games). Drop it.

## Next

- **Cheapen `ast-pwc`'s Safety** before shipping it. Choose `first_next` by threat to our tile, not distance (the
  settled 0→1 flips are 91k reads, wrong 84%). Or bound the settled enemies' jump by what their unsettled
  teammates gain from dropping. Both need care to stay rule-derived.
- **An ambush adversary** to test persistence for real: a move-search term in `ast-adv2` for tiles from which its
  next two turns kill a target whose stale read says one (worst-case.md). Until it exists, "never punished" means
  only that bid timing alone cannot exploit a stale read.
- **Cheaper kill-bid damage**: memoise `two_turns` per ally and distance in `Strikes`, if a predicted or forked
  bid is ever kept.

## Scripts

- Dataset: `python3 scripts/order_data.py replays/meas-ladder-ex L.pkl`, and the same for `replays/meas-ex` into
  S.pkl.
- Fits: `venv/bin/python scripts/order_fit.py L.pkl [S.pkl]` (ladder fit, per team) and
  `venv/bin/python scripts/order_botfit.py L.pkl S.pkl` (the in-bot weights).
- Diagnosis: `python3 scripts/dx_analyze.py replays/pred-dx-ex`, from the repo root.
- Paired comparisons: `python3 scripts/paired.py RUN_A RUN_B`, from the repo root.
