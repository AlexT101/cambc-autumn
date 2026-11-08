# Engage on local numbers: does Fish's rule explain our losses? (2026-11-08)

Analysis only; no bot changed. Question: does a Fish-style "engage on local numbers" rule explain a measurable share
of ocean's losses to Intercontinental Fish and the other top teams, and if so, which arm would copy it?

**Answer: no.** In every local state we start fights about twice as often as Fish, against the same opponent in the
same games. There is no state, whether cut by numbers, local health, own health, stun readiness or distance, where
Fish engages and we don't. That direction is worth −0.003 net kills a game (CI −0.014..+0.008), about 0.0 points. Fish's
own engage rate *falls* as its local numbers rise, as everyone's does. The gap against Fish is in how our engagements
go, not in which ones we start. The only positive selection term runs the other way: we engage where Fish holds back.
Holding back at a local EHP ratio below 0.8 is worth at most +0.26 points against Fish, and it costs against the other
top teams. That is below the +0.3 bar and has the wrong sign on the wider panel, so **no arm is specified**.

## Data

- **Scrims, v83-v86 against Fish**: 815 games with both sides decoded (1,090 finished; the rest are
  unreadable or have no contact rows). This is the closest live data to ocean (v86 = oc-base23; oc-base25 adds only the
  mid-game gold price). Both teams play the same maps and each other, so the opponent mix is matched. We win 60.4% of
  these (v85/v86: 64.2%).
  - Also v78-v82 against Fish (1,013), and v83-v86 against Mite (878).
- **Ladder** (the gaps/willow decodes, 11-05 and 11-06 21:00 to 11-07 14:39): Fish 3,303 sides (1,037 against the 14
  top teams), our v82 4,238 (1,172 against top), top 14,606, Mite 4,186.
- **Decoding.** Scrim replays not already decoded were staged and run through `tools/replay/extract.mjs` (2,777 games, 8
  threads). The ladder reused `tmp-offload/{gaps,willow}/analysis`.
- **Files.** Everything is in `~/tmp-offload/engage/`:
  - `bin/stage.py`, `bin/rows.py` (rows), `bin/analyse.py` (`report.txt`), `bin/restraint.py`, `bin/byhp.py`
    (`byhp.txt`);
  - row files `rows-ladder.npz` and `rows-scrim.npz`: 5.56M contact rows in 25,431 games.

## Method

- **Contact row.** One row per (game, team P, round r, anchor a):
  - P champion a is alive at the start of r;
  - an enemy that some P champion sees at its turn start in r is within 6 of a;
  - no champion damage from either team fell within 8 of a in rounds r−8..r−1 (a quiet contact).
- **Anchors.** Taken greedily, nearest to an enemy first. P champions within 4 of a chosen anchor are covered, so one
  fight front gives one row.
- **Engagement.** The first champion damage or stun within 8 of a, in round r, after those 8 quiet rounds.
  - `pe`: P struck first. `ee`: the enemy struck first.
  - The decision rows are those with `ee = 0`, where the enemy had not already started the fight that round.
  - The hazard P(engage | state) is per decision row. Section 6 of `report.txt` repeats the analysis per episode (the
    first quiet contact; struck first within 3 rounds), with the same ordering.
- **State** at a:
  - allies and enemies alive within 4, 6 and 8;
  - local EHP (health + shield) within 6, both sides;
  - own health fraction, and the health fraction of the nearest enemy;
  - ready abilities and ready stuns within 6, both sides;
  - gems carried within 8, both sides;
  - distance to each spawn;
  - d0, the distance to the nearest seen enemy.
- **Outcome.** Over rounds r..r+19, among champions within 8 of a at r:
  - kills won minus kills lost (camp deaths kept apart; a Cassi/Issac linked death counted once);
  - gem swing: enemy bags minus own bags at death.
- **Accounting** (counterfactual-free). Cells are allies − enemies within 6 (≤−2..≥+3) × d0 (≤3, 4-6) × local EHP
  ratio (<0.8, 0.8-1.25, >1.25), 36 cells. For our side:
  - selection = Σ f_us(s) · (p_Fish(s) − p_us(s)) · (o_us(s | engage) − o_us(s | not)), where f is decision rows per
    game. It is split into the cells where Fish engages more and those where it engages less.
  - execution = Σ f_us(s) · p_us(s) · (o_Fish(s | engage) − o_us(s | engage)).
  - CIs come from a joint game bootstrap (a scrim game holds both sides' rows), 300 draws.
  - Placebo: the same accounting between two random halves of one team's games. It gives the noise floor of any sum
    that keeps only the "cells that gain".
- **Kills to points.** In v83-v86 scrims against Fish, win ~ (our kills − their kills) gives +3.3 points per net kill a
  game (linear; logit average marginal effect 4.8). This is correlational: the stronger side also gets the kills. Point
  figures below use 3.3 and are upper bounds.

## 1. Who engages: rates per contact

| set | sides | decision rows/side | P(engage)/row | engagements started/side | enemy struck first/row |
|---|---:|---:|---:|---:|---:|
| us v83-86 scrim vs Fish | 815 | 155 | 8.9% | 13.8 | 3.8% |
| Fish scrim vs us v83-86 | 815 | 164 | 4.1% | 6.7 | 7.9% |
| us v83-86 scrim vs Mite | 878 | 132 | 9.7% | 12.9 | 4.5% |
| us v82 ladder | 4,238 | 135 | 8.9% | 12.0 | 4.6% |
| Fish ladder | 3,303 | 130 | 6.9% | 9.0 | 5.6% |
| Fish ladder vs top | 1,037 | 147 | 6.3% | 9.2 | 6.1% |
| top ladder | 14,606 | 184 | 7.2% | 13.3 | 6.6% |
| Mite ladder | 4,186 | 128 | 7.1% | 9.1 | 7.1% |

Behaviour-gaps-2 found we start 62% of engagements; here, against Fish, we start twice as many as Fish does.

## 2. P(engage | local state)

By allies − enemies within 6: P(engage) per row / net kills in 20 rounds when engaging / when not.

| set | ≤−2 | −1 | 0 | +1 | +2 | ≥+3 |
|---|---:|---:|---:|---:|---:|---:|
| Fish scrim vs us v83-86 | 10.3% / +0.28 / +0.07 | 6.7% / +0.17 / +0.06 | 4.1% / +0.17 / +0.01 | 4.5% / +0.15 / −0.01 | 4.0% / +0.17 / +0.00 | 3.5% / +0.16 / +0.01 |
| us v83-86 scrim vs Fish | 17.7% / −0.02 / −0.04 | 12.0% / +0.08 / −0.02 | 7.8% / +0.07 / −0.02 | 9.3% / +0.02 / −0.04 | 9.4% / +0.02 / −0.05 | 8.9% / +0.05 / −0.04 |
| Fish ladder vs top | 12.2% / +0.43 / +0.10 | 9.5% / +0.31 / +0.10 | 6.2% / +0.25 / +0.05 | 6.7% / +0.20 / +0.04 | 6.6% / +0.29 / +0.06 | 5.6% / +0.35 / +0.07 |
| us v82 ladder | 13.4% / +0.39 / +0.11 | 11.7% / +0.32 / +0.09 | 8.2% / +0.25 / +0.06 | 9.5% / +0.25 / +0.06 | 10.0% / +0.24 / +0.07 | 9.1% / +0.25 / +0.07 |

- **Fish's rate does not rise with numbers.** It is highest when outnumbered, and falls from 10-12% at ≤−2 to 3.5-5.6%
  at ≥+3. Every group shows the same shape.
  - Outnumbered contacts are mostly ones the enemy walked into, and the first hit then is often defensive.
  - Within 8 (the ±8 table in `report.txt`) the curve is flat for everyone.
- **Logistic fit** (decision rows; coefficients per unit):

  | set | allies − enemies r6 | log2 EHP ratio r6 | d0 | own hp frac | stun ready us − them | own gems (log2) |
  |---|---:|---:|---:|---:|---:|---:|
  | Fish scrim vs us | −0.215 | +0.067 | −1.229 | +0.467 | +0.364 | −0.026 |
  | us v83-86 scrim vs Fish | −0.228 | +0.107 | −0.918 | +0.221 | +0.260 | +0.035 |
  | Fish ladder | −0.186 | +0.139 | −1.004 | +0.651 | +0.431 | −0.026 |
  | us v82 ladder | −0.244 | +0.070 | −0.869 | +0.401 | +0.321 | +0.060 |
  | top ladder | −0.242 | +0.251 | −1.005 | +0.316 | +0.261 | +0.003 |

  Fish's distinctive terms are own health, stun readiness, a steeper distance term (it strikes from close in) and lower
  aggression with a bag. Numbers are not among them: no team's numbers term is positive once EHP is in the model.
  - This matches FISH_MODEL §9-10. There, a numbers threshold fits Fish's engages at 64.5%, against 72% for its
    danger rule (h > 0.49 and danger ≤ 0.28, plus the kill override).
- The carrier-punish study (§6) saw hit rates doubling with numbers. It counted the numbers around the *target* at its
  first sighting, and every hit within 3 rounds, defensive ones included. Per decision round around the actor, the
  effect is not there.

## 3. Accounting

v83-v86 scrims against Fish, net kills a game (bootstrap 95% CI):

| term | kills/game | points (≤, ×3.3) |
|---|---:|---:|
| Selection, cells where **Fish engages more** | −0.003 (−0.014..+0.008) | 0.0 |
| Selection, cells where Fish engages less | −0.571 (−0.700..−0.463) | −1.9 |
| Selection, all (moving every cell to Fish's rate) | −0.574 (−0.704..−0.464) | −1.9 |
| Only the cells that gain | +0.157 (+0.110..+0.221) | placebo +0.076 ± 0.033 |
| Execution (our engagements going as Fish's) | **+0.718 (+0.214..+1.261)** | +2.4 |

- **Numbers are not a gap.** Fish engages more than we do in none of the 36 cells by more than noise.
- **Copying Fish's rates would cost us.** Cut by own health × d0 × stun readiness (`byhp.txt`), "Fish engages more" is
  +0.000 against Fish and +0.004 against top. We engage 1.5-2.5x Fish's rate in every healthy cell, and on observed
  outcomes those extra engagements pay (Δ kills, engaging against not, +0.07 to +0.22).
- **The real gap is execution.** At the same local state, Fish's engagements against us net +0.72 kills a game more
  than ours against it (behaviour-gaps-2 §5's finding, at state level).
  - Against the top teams on the ladder, our engagements go as well as Fish's: execution −0.28 (−0.62..+0.10).
  - The execution gap is specific to the Fish matchup.
- **The ladder confirms it.**
  - v82 against Fish ladder: Fish-more cells +0.035 (+0.012..+0.081), about 0.1 points; Fish-less cells −0.667.
  - Against top only: +0.002 and −0.824.

## 4. The reverse direction: we engage, Fish holds back, and we lose

The only cells that gain are those where our engage effect is negative and Fish engages less. All of them have a local
EHP ratio below about 1 (`restraint.py`). The table gives the value of moving our rate to Fish's there:

| set | region | our engagements/game | at Fish's rate | kills/game (CI) |
|---|---|---:|---:|---:|
| us v83-86 vs Fish (scrim) | EHP ratio < 0.8 | 4.0 | 2.4 | **+0.080 (+0.029..+0.140)** |
| us v83-86 vs Fish (scrim) | EHP ratio < 1.0 | 5.4 | 3.1 | +0.084 (+0.014..+0.147) |
| us v78-82 vs Fish (scrim) | EHP ratio < 0.8 | 4.3 | 2.8 | +0.167 (+0.120..+0.204) |
| us v82 vs top (ladder) | EHP ratio < 0.8 | 2.5 | 1.7 | **−0.060 (−0.086..−0.037)** |
| us v82, all ladder | EHP ratio < 0.8 | 2.4 | 1.7 | −0.016 (−0.047..+0.024) |

- Against current Fish, the restraint is worth ≤ +0.26 points (0.080 × 3.3, an upper bound). It has shrunk since v78-82
  (+0.55).
- Against the other top teams it costs: −0.06 kills, about −0.2 points.
- Against our ladder mix it is level.
- This is the opposite of Fish's rule, and it does not hold outside one opponent.

## 5. Decision

The bar was a simple rule covering ≥ +0.3 points. Results:
- **Numbers (any k) and health ratio (any h)**: the table in §4 of `report.txt`. For every k ∈ {0, 1, 2} and h ∈ {0,
  0.8, 1, 1.25, 1.5}, Fish engages *less* than we do where the rule fires. Adopting "engage iff allies ≥ enemies + k
  and EHP ratio ≥ h" at Fish's rates removes 0.8-5.8 engagements a game and costs 0.16-0.62 kills.
- **Restraint below an EHP ratio of 0.8**: ≤ +0.26 points against Fish, negative against the top teams.

**No arm.** Fish's edge in fights is in how its engagements go: who it hits, its stun and kill timing, and its comp of
bruisers. It is not in when it starts them. That is consistent with behaviour-gaps-2 §5 (its edge holds at every number
advantage) and with the carrier-punish arms (lv50, ic100x, sr50, lv100), all ≤ +0.15.

Where the effort should go instead: the execution term, +0.72 kills a game against Fish at matched states. To split
it, decompose engagement outcomes against Fish by first-hit type (spell or basic attack, stun or not), focus target
and the turn of the kill, using the rows here (`rows-scrim.npz` has the anchor type, cooldowns and damage dealt and
taken in 10 rounds).

If anyone wants the restraint anyway: ocean's engage gate is `prey()` / `preyable()` in `combat/fight.cc`, which runs
`safety.chase_trade` on the local fight. A knob would demand a local EHP ratio ≥ x (x ∈ {0.6, 0.7, 0.8, 0.9}) before
`prey()` returns a target that is not already engaged. That costs ~100 fuel a turn: a sum over at most 10 champion
beliefs. The data predicts level or negative on the panel, so it is not worth a screen.
