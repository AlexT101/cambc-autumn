# Fight-model calibration from natural play (2026-11-09)

Question: does ocean's fight model (oc-cl2-base: `Safety::stand_trade` in `stand_lost_at`, `Safety::chase_trade` in
`prey`) call fights lost that are won when they happen, or the reverse? If so, recalibrating it would be a whole-behaviour
change. **Answer: no. At both decision boundaries the model is calibrated, and outcomes are continuous across them.
No correction was built and no A/B was run.**

## Method

- `bots/variants/cal-dbg` (and its identical copy `cal-dbg2`): oc-cl2-base plus `debug_block` traces, and the noisiest
  existing traces muted (SLOT, SRCH, CREW, FIXC-BUSHT, CHASE-AVAIL) to stay under the 1 MiB stdout cap.
  - `CS`: every stand verdict that reaches `stand_trade`.
  - `CC`: every `chase_trade` candidate in `prey`.
  - Each line holds the inputs, the prediction (lost, self_falls, turns to kill, the sim's damage over 1 and 5 turns
    for each side), and the roster: each member's arrival turn, health, and whether it is visible.
  - The margin `m` is log2 of the factor on our side's health and max health at which the verdict flips. It is
    found by bisection on copies of the same sides (`Safety::cal_stand` / `cal_chase`, in safety.cc). `m > 0`: lost,
    and we would need 2^m our health to win; `m < 0`: won, and still won down to 2^m. It is capped at ±3.
  - The recomputed verdict matched the live one on all 3.2M lines. It runs inside debug blocks, so it is fuel-free;
    the fighter-cache bits are restored afterwards.
- Games: 2,048 debug games, cal-dbg vs cal-dbg2, so both sides log and the opponent is oc-cl2-base's behaviour.
  - `ab.py --debug --no-test-draft`, fast runner.
  - Maps: maps/gen (512 games), 256 cl2-dev maps (512), 256 more cl2-dev maps (512), 256 gen-s1 maps (512).
  - 1,966 games kept and extracted: 2.09M stand verdicts and 1.11M chase candidates.
  - Batches `replays/batch-2026110[8]-23*-ab-cal-run{1,2}-*` (pinned with `.keep`).
- Outcomes from the replays (`cal-tools/collect.py`), over the next 10 (and 20) rounds from our turn:
  - our champion's death;
  - deaths among the roster's enemies and among its allies, counted by pick (Cassi & Issac as one);
  - **bodies** = their dead minus ours;
  - whose side lost a champion first;
  - damage exchanged;
  - the turn's decision (`D` line);
  - the game's result.
- Confidence intervals are 95%, from a Poisson bootstrap over games: consecutive verdicts in one fight are correlated.

### Selection bias, and how it is limited

The verdict decides the action (stand lost → leave 98.5%; won → stay 99.9%), so a fight called lost and then fought is
rare and selected: trapped champions, channels and fixc commits. These are only 1% of lost verdicts, and their bodies
are −0.14 to −0.74. Two estimates avoid that selection:
1. **Calibration curve:** P(our side loses a champion first | someone dies within 10) against the margin. For a
   calibrated verdict this crosses 50% at m = 0.
2. **Regression discontinuity at m = 0:** local-linear fits on each side within a bandwidth of 0.1, 0.25 or 0.5,
   giving the jump won − lost.
   - Rows just either side of the boundary differ only by a few percent of simulated health, but take opposite actions.
   - So the jump is the causal effect, at the boundary, of this turn's verdict (stay or chase instead of leave or not
     chase), including everything that follows.
   - If the model were pessimistic, the won side would do better than the lost side (a positive jump), and moving the
     boundary toward standing or chasing would pay.

What remains:
- The estimate is local to the boundary.
- It is intent-to-treat: the next turn re-judges.
- It covers only verdicts that reach the sim. drawn_home, camp_trapped and the pack zone decide first.
- The step guard's and the strike search's fights are not logged.

## Results

### Stand verdicts (2.09M)

| margin m | n | bodies/10r | our champion dies | an enemy dies | P(ours first \| a death) |
|---|---|---|---|---|---|
| ≤ −3 | 278,188 | +0.247 | 1.6% | 28.2% | 11.8% |
| −3..−1.5 | 310,682 | +0.184 | 1.5% | 20.9% | 15.0% |
| −1.5..−1 | 186,514 | +0.124 | 2.0% | 16.1% | 21.9% |
| −1..−0.5 | 239,862 | +0.079 | 2.5% | 12.9% | 29.8% |
| −0.5..−0.25 | 144,970 | +0.040 | 3.2% | 10.6% | 38.6% |
| −0.25..−0.1 | 79,180 | +0.016 | 3.5% | 9.2% | 45.4% |
| **−0.1..0 (won, stay)** | 52,414 | −0.004 | 3.9% | 8.2% | **50.7%** (49.4-52.2) |
| **0..+0.1 (lost, leave)** | 60,802 | −0.010 | 2.5% | 6.2% | **53.8%** (52.7-55.3) |
| +0.1..+0.25 | 79,852 | −0.023 | 2.8% | 6.2% | 58.2% |
| +0.25..+0.5 | 135,014 | −0.040 | 3.3% | 5.6% | 63.3% |
| +0.5..+1 | 195,746 | −0.064 | 4.7% | 5.1% | 69.1% |
| +1..+1.5 | 135,950 | −0.091 | 7.0% | 4.4% | 75.5% |
| +1.5..+3 | 185,984 | −0.169 | 14.6% | 4.1% | 84.4% |

- The curve is monotone and crosses 50% at m ≈ 0.
- Jump won − lost at m = 0, bandwidth 0.25:
  - bodies/10r −0.006 (−0.013..+0.001);
  - bodies/20r −0.013 (−0.024..−0.003);
  - our death +1.8 points and an enemy's death +1.5 points: a fair trade;
  - games won −0.008 (−0.016..+0.004).
- The other bandwidths are the same within noise (0.1: bodies +0.006 ±0.014, won +0.011 ±0.020), and so are the two
  run halves (run1 −0.007, run2 −0.005).
- **Standing more at the boundary would not gain.**

### Chase candidates (1.11M; 69% lost)

| margin m | n | bodies/10r | our champion dies | target side dies | P(ours first \| a death) |
|---|---|---|---|---|---|
| −0.5..−0.25 | 53,028 | +0.051 | 1.6% | 7.8% | 27.6% |
| −0.25..−0.1 | 33,148 | +0.039 | 1.9% | 7.0% | 32.2% |
| **−0.1..0 (won, chase)** | 21,260 | +0.038 | 1.9% | 7.2% | 33.1% |
| **0..+0.1 (lost)** | 26,820 | +0.027 | 1.7% | 6.1% | 37.0% |
| +0.1..+0.25 | 40,832 | +0.035 | 1.4% | 6.3% | 33.6% |
| +0.25..+0.5 | 76,986 | +0.028 | 1.8% | 6.5% | 37.9% |
| +0.5..+1 | 148,834 | +0.023 | 1.9% | 6.3% | 40.8% |
| +1..+1.5 | 148,600 | +0.021 | 2.5% | 6.3% | 42.5% |
| +1.5..+3 | 311,712 | +0.003 | 5.5% | 6.6% | 51.1% |

- The first-death share stays below 50% on the lost side. A declined chase has no fight of its own, so the deaths
  that follow come from other fights.
- The decision-relevant jump is flat. At bandwidth 0.25:
  - bodies +0.010 (+0.001..+0.019);
  - our death +0.3 points;
  - games won −0.017 (−0.035..+0.001).
- At 0.1 and 0.5: bodies −0.007 / +0.004, won −0.029 / +0.008.
- **Chasing more at the boundary gains a hundredth of a body a decision and no games.**

### Subgroups at the boundary (|m| ≤ 0.25; jump won − lost, local-linear, bandwidth 0.25)

| stand subgroup | P(ours first) won / lost side | jump bodies | jump games won |
|---|---|---|---|
| health ≥ 90% | 49.4 / 57.9% | −0.010 (−0.021..−0.001) | −0.018 (−0.035..−0.002) |
| health < 50% | 51.7 / 57.0% | +0.007 (±0.020) | −0.006 (±0.031) |
| alone (no ally in roster) | 25.8 / 31.8% | +0.012 (+0.004..+0.019) | +0.010 (±0.021) |
| 3+ enemies | 43.9 / 52.3% | −0.027 (−0.046..−0.008) | −0.016 (−0.029..+0.001) |
| unseen enemy in roster | 46.5 / 50.7% | +0.019 (+0.005..+0.035) | −0.009 (±0.023) |
| walkers in roster | 47.5 / 55.6% | −0.005 (±0.008) | +0.001 (±0.012) |
| busy ally (leaving, banking, holding) | 51.8 / 60.8% | −0.009 (−0.019..0.000) | −0.006 (±0.011) |
| carrying 10+ gems | 47.4 / 57.6% | −0.000 (±0.011) | +0.015 (−0.001..+0.033) |

| chase subgroup | jump bodies | jump games won |
|---|---|---|
| health ≥ 90% | +0.014 (+0.002..+0.027) | −0.010 (±0.026) |
| 2+ allies in roster | +0.021 (−0.004..+0.042) | −0.032 (−0.053..−0.007) |
| busy ally in roster | +0.027 (+0.002..+0.049) | −0.028 (−0.049..−0.003) |
| 3+ enemies | +0.027 (−0.006..+0.052) | −0.045 (−0.078..−0.015) |
| carrying 10+ | +0.025 (+0.010..+0.039) | −0.002 (±0.034) |

No subgroup has a positive jump in games won. Where bodies favour standing or chasing (alone; unseen enemies; team
chases), the games do not follow, and the team-chase cases lose games significantly.
- **The healthy pursuer that leaves on a lost stand is right to leave.** At health ≥ 90%, staying at the boundary
  loses bodies and games.
- That fits the level team arms of G3a and G3b: cover, peel and honest rosters all add chases or stands right at this
  boundary.

### Mechanism checks (the model's parts are biased, but the biases cancel)

Members of the roster that hit within their predicted arrival + 1 rounds, when our champion stays:

| member | arrival 0 | 1 | 2 |
|---|---|---|---|
| enemy, seen | 48% | 32% | 25% |
| enemy, unseen | 19% | 12% | 11% |
| ally | 32% | 20% | 11% |

- The sim has every member striking every turn from its arrival. Realized damage over 5 rounds is 0.3-0.6 of the
  sim's on both sides (engaged stays: theirs 0.66, ours 0.54).
- Near the boundary the ratio of realized to simulated damage balance is 1.05 (engaged stays): enemies deliver
  slightly more of their simulated damage than we do. Unseen enemies are overcounted, allies more than seen enemies,
  and enemies strike first in the sim. These cancel: the death outcome crosses 50% at the boundary.
- Fixing one of them (expected reach for the unseen, discounted allies) would unbalance the rest, in a direction the
  boundary tables say does not pay.
- Paired verdicts on the same contact (our stand and the enemy's, 575k pairs):

  | verdicts | share | ours first / theirs first |
  |---|---|---|
  | both lost | 8.4% | 8.6 / 9.7% |
  | both won | 23.5% | 8.6 / 7.8% |
  | we lost, they won | 31.9% | 15.7 / 3.5% |
  | we won, they lost | 36.2% | 4.0 / 16.1% |

## Verdict

The fight model is well calibrated where it decides. The arms that came out level (retreat rollouts, lead pursuit,
honest rosters, cover, peel, post-action re-judging) were level because the opportunities they opened sit at this
boundary, where taking the fight and declining it are worth the same. The vetoes they hit (chase_trade lost on 41 of 53
cover asks; 88% of peel candidates rejected) are, on this evidence, correct or harmless. A whole-model recalibration
has nothing to correct in either direction, so step 2 was not run.

Files: `cal-tools/collect.py` (replays → rows), `flat.py` (rows → npz), `nana.py` (tables, game bootstrap), `ana.py`
(slower per-row tables, members, pairing). Variants `bots/variants/cal-dbg`, `cal-dbg2` (debug-only instrumentation).

## Against Fish and Mite (2026-11-11)

[fishcal-notes.md](fishcal-notes.md) repeats this study on 2,384 live scrims of v105-v111 (one fight model) against
Fish and Mite, re-run exactly against puppets with these lines traced. Both boundaries are calibrated against both
opponents too: the first-death curve crosses 50% at m = 0, and games won are flat across it. Against Fish the parts
cancel less well (its members deliver less of their simulated damage relative to ours: balance 0.87 against the
mirror's 1.08), and standing at the boundary gains +0.03-0.05 bodies over 10 rounds there, but not over 20 or in games.
