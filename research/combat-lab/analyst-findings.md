# Combat lab analyst findings: where ocean's combat choices lose (2026-11-08)

The question: in which combat situations does ocean (`variants/oc-cl2-base`, as the lab copy `variants/lab-cl2`)
choose worse than an alternative the lab can force, by how much, and which code makes the choice. The scripts,
runner options and their checks are in [lab2-notes.md](lab2-notes.md).

## Verdict

**No pattern beats ocean once the result has to replicate.** That holds over about 10,700 forks in four runs, two
opponents and both map-hash halves.

- No one-turn action (walk, dash, attack, cast, end; held 1 or 3 turns) beats ocean's own by more than the noise.
- No verdict flip forced for 3 or 8 turns beats ocean's own either. The flips tested were retreat to stand, stand
  to retreat, chase to no chase, and chase where ocean declined.
- Whatever local regret ocean has is at most about 0.05 to 0.08 bodies per fork at 10 rounds, and none at 30.
- Ocean's retreat and chase verdicts are right against every flip the lab can force, and often by a wide margin.

The one surviving lead is **declining to chase**. Forcing a chase where ocean did not gains +0.05 to +0.06 bodies,
but only against astraeus, and only on one map half. It is level in the mirror and on the other half.

Below are the ranked items, with the lab's limits and what it would need to go further.

## Method

| run | opponent | arms | games (both sides) | forks | marks |
|---|---|---|---|---|---|
| A | ocean (mirror) | `none` + every legal one-turn action, holds 1 and 3 (~25 arms a fork) | 416 | 3229 | 10/30/60 |
| B | astraeus (`variants/an-astraeus`) | same as A | 115 (partial, stopped) | 900 | 10/30/60 |
| C | ocean (mirror) | `none`, `home:{0,1}:{3,8}`, `chase:{0,1}:{3,8}` | 404 (partial) | 4736 | 10/30/60 |
| C2 | astraeus | same as C | 157 (partial) | 1836 | 10/30/60 |

**Maps and sampling.**
- Every run used `maps/suites/merged/cl2-dev` (ladder-v2), with a distinct map list per run.
- Triggers: A and B used `near:6, close:3, branch:RCA, kill:5, death:5`, with gap 10 and at most 8 forks a game. C
  and C2 used `near:6, close:4, branch:RC`, with gap 8 and at most 12 forks a game.
- Commands: `<run>/command.txt` under the scratchpad (`an/`).
- **Partial runs.** A was stopped at 413 of 800 games and B at 113. C and C2 are read from the rows built at 404 and
  157 games, out of 800 and 600.

**Noise replicates.** Every arm was played four times:
- rep 0, the real continuation;
- a +10k per-turn fuel jitter;
- skipped turns of the 1st and 2nd farthest lab champions (in the next round, so the decision is untouched).

The placebo, forcing ocean's own action, reproduces ocean's play exactly (217 of 241 forks). It measures nothing, so
the replicates are the noise floor.

**Combat reward.** It is the decider's team minus the enemy's, as changes since the fork:
- **C** = kills − deaths (Cassi and Issac 0.5 each) + 0.5 · Δhealth share + bags. Bags are min(gems carried at the
  fork, 80) / 80 per dead champion: theirs plus, ours minus. Capped, because carriers with 500-1900 gems made raw bag
  scores heavy-tailed.
- **CL** = C over the champions within 12 of the decider at the fork.
- **KD** = CL without the health term (bodies and bags only). KD is the headline, because health share credits
  healing at home.
- **Economy is kept apart:** E = Δ(tribute + carried gems), and W = Δwealth.

**Estimators.**
- **Per fork:** naive regret (best arm on rep 0 minus `none`); cross-fit regret (best arm picked on one rep and scored
  on the others); and a null regret (the same max over replicate differences of `none` alone).
- **Class gain** is the a priori quantity: a class's mean over its arms and reps, minus `none`'s mean over reps.
  Forks where the class contains ocean's own action are excluded.
- **Patterns** are found on map-hash half 0 and measured on half 1 and on the other opponent's run. CIs are 95%
  bootstraps over games.
- **Scripts:** `fork_regret.py`, then `fork_patterns.py`, `fork_branch_table.py`, `fork_rules.py`,
  `fork_verdicts.py` and `fork_examples.py`, all in `tools/combatlab/`.

## Noise floor

Per fork, in KD bodies, run A (B is the same within 0.01-0.02):

| mark | naive regret | cross-fit regret | null (replicate noise) | net, at most |
|---|---|---|---|---|
| 10 | 0.19 | 0.15 | 0.10 | ~0.05-0.08 |
| 30 | 0.60-0.66 | 0.37 | 0.48 | 0 |
| 60 | 0.92 | — | 0.92 | 0 |

- CL reads the same: mark 10 naive 0.26 against a null of 0.13; mark 30, 0.70 against 0.54.
- The null understates the noise: two different actions diverge more than two replicates do. The "net" column is
  therefore an upper bound on ocean's local regret.
- Every top pattern found on half 0 regressed to ≤0 on half 1, at marks 10 and 30, on both CL and KD. That is the
  signature of selection on noise.

## How often the situations come up

Run A, both teams: ~880 rounds and 16.5 deaths a game. The branch turns (champion-turns) per game were:
- F (farm or move) 5393;
- R (retreat) 658;
- C (chase) 389;
- B (bank) 677.

Per side that is about 330 retreat turns and 195 chase turns a game. Of the forks the triggers sampled (which
over-weight contact):
- R is 31%, C 20% and F 18%.
- 84% of R forks have an enemy within 8.
- The forced chase differs from ocean's own play in 60% of non-R/C forks.
- Hits on the fork turn itself are rare: most fork actions are walks before contact.

## Ranked items

Ranked by frequency × |gain|, and by whether the gain replicates. **None is a positive pattern that replicates.**
Items 1-4 are things the lab confirms ocean gets right, so changing them is ruled out. Item 5 is the one open lead,
and item 6 is what the lab can't resolve.

### 1. Retreat with an enemy within 8: ocean is right to go (big, replicates everywhere)

**Situation.** Branch R, with an enemy within 8 (`want_home` true). This is ~280 turns a side a game.

**Forced stand** (`home=0`), KD gain over ocean's own play, four cells (C h0 / C h1 / C2 h0 / C2 h1):

| arm | mark 10 | mark 30 |
|---|---|---|
| stand 3 turns | −0.155 / −0.138 / −0.105 / −0.084 | −0.162 / −0.137 / −0.179 / −0.099 |
| stand 8 turns | −0.32 / −0.30 / −0.26 / −0.19 | −0.39 / −0.33 / −0.41 / −0.23 |

- All of these CIs exclude 0.
- At hp < 0.5 the stand is worse: −0.28 / −0.21 / −0.17 / −0.14 (3 turns, mark 10).
- At hp ≥ 0.5 it still loses: −0.11 / −0.11 / −0.08 / −0.06.
- Retreats with no enemy within 8 (from a camp) lose most of all to a stand: −0.40 to −0.49 (3 turns).
- **Economy** loses as well: E −4 to −13 gems at mark 10, and −3 to −20 at mark 30.
- **Regret:** none; the better action is ocean's.

**Examples** (the forced stand loses in every rep):
- `gen-classic-140000401021#a` r340: Cassi (20,32) 605/665 retreats from a Vesper at 6 with four allies around. Under
  the stand, Cassi and Issac die at r345. CL 0.34 for ocean against −1.03.
- `gen-classic-140000901021#b` r314: Cassi (16,2) 747/795 with a Marcella at 4. The stand loses Cassi and Issac by
  r322. CL −0.20 against −1.16.
- `gen-ladder-140001500020#b` r142: Vendetta (26,16) 1288/1400 with a Vesper at 5 and 3 enemies near. The stand dies
  at r147. CL 0.00 against −0.73, and 0.76 against −0.87 at mark 30.
- `mut-ultrastarvation-140001317038#b` r171: Vesper (31,36) 520/1000 next to a Ren and Hor. The stand dies at r178.

**Code:** `want_home` (oc-cl2-base `src/combat/fight.cc:447-465`; `drawn_home` 390, `stand_lost_at` 401). Leave it
alone. Forcing a recall earlier on farm turns (`home=1x3` in F) is level: −0.007 / −0.006 / −0.040 / +0.031.

**Caveat.** The forced stand applies to the decider only, while its allies keep ocean's policy and retreat, so the
decider often stands alone. The result is "retreat is right given that allies retreat", not "a team stand loses".
See *What the lab needs*, item 3.

### 2. Chase continuation: ocean is right to keep chasing

**Situation.** Branch C. This is ~195 turns a side a game.

KD gain at mark 10 (C h0 / C h1 / C2 h0 / C2 h1):

| forced flip | gain |
|---|---|
| no chase, 3 turns (`chase=0x3`) | −0.023 / −0.034 / −0.054 / −0.038 |
| home, 3 turns (`home=1x3`) | −0.076 / −0.046 / −0.045 / −0.062 |
| home, 8 turns (`home=1x8`) | −0.083 / −0.066 / −0.079 / −0.102 |
| no chase, 8 turns (`chase=0x8`) | −0.033 / −0.044 / −0.058 / −0.061 |

- `chase=0x3` is significant in one cell and `home=1x3` in three. `home=1x8` and `chase=0x8` are significant in all four.
- At mark 30, `home=1x8` reads −0.066 / −0.101 / −0.135 / −0.076.
- In contact frames of run A, ocean's stay-and-hit takes the kill, and walking away loses it:
  - `gen-lakes-140001006001#a` r1045: Hor against a Prism at 282 hp. CL 1.33 against 0.05.
  - `gen-vaults-140003715001#a` r435: Hor. CL 2.79 against 0.71.

**Code:** `prey`/`chase` (`fight.cc:653-808`) are confirmed.

### 3. One-turn steps in a retreat or at contact: nothing beats ocean's

**Situation.** Runs A and B, every legal action class, compared with ocean's at mark 10 (KD).

**Significant classes** (`+` = beats ocean, `−` = loses to it):

| situation | run A | run B |
|---|---|---|
| R | 0 + / 36 − of 43 classes | 0 + / 8 − |
| C | 2 + / 14 − | 0 + / 5 − |
| F | 0 + / 10 − | 0 + / 10 − |
| enemy at ≤2 | 0 + / 13 − | 0 + / 8 − |
| enemy at 3-4 | 0 + / 22 − | 0 + / 5 − |

- At contact every deviation is worse, by 0.1-0.5 bodies. So the lab is sensitive enough to see a wrong step, and
  ocean's are not wrong.
- The two positive C cells (dash toward the enemy, toward home) did not replicate in B.

**Concrete rules**, scored with no outcome selection (mark 10 KD, A / B):

| rule | A | B |
|---|---|---|
| `chase_dash`: chasing with dash ready, dash to the landing nearest the target | +0.015 [−0.032, +0.061] | +0.020 |
| `chase_dash_any`: mean over all dash-toward landings | +0.011 | −0.015 |
| `retreat_dash`: dash on the first retreat turn | −0.036 | −0.054 |
| `attack_low`: hit the lowest enemy | level or worse | level or worse |
| `stun_near`: stun the nearest | level or worse | level or worse |

- `chase_dash` also costs 12-17 gems of economy at mark 60.
- One `chase_dash` win was a cascade. In `gen-shared-gems-140000314002#b` r1273, an allied Ren recalled home and the
  health-share term moved.

**Code:**
- `chase` (`fight.cc:790`) dashes only when the target is beyond range+1, through `dash_to_attack`
  (`self_abilities.cc:382`, chase_health 0.4); the planner prices a dash at `dash_range * step` (`plan.cc:1211`,
  dash nodes 1748-1763, aim gain 2101-2104). All three are confirmed: dashing more in a chase doesn't pay.
- The retreat keeps its dash in reserve (`keep_dash` in `retreat`, `fight.cc:1322-1384`). Also confirmed.

### 4. Forced chase where ocean does nothing in particular: level in the mirror

**Situation.** Non-R/C forks (mostly F) with an enemy near, forcing `chase=1` for 8 turns.

KD gain, C h0 / C h1:
- mark 10: +0.015 [−0.012, +0.040] / −0.000 [−0.020, +0.018];
- mark 30: +0.026 / −0.059 (significant).

Split by `preyable`'s conditions (`fight.cc:557-575`), mirror only:
- target hp ≥ 0.45: +0.007 / +0.001;
- target near its own home: −0.018 / +0.033;
- target carrying 20+ gems: +0.028 / +0.017;
- allies at least equal in number: +0.001 / +0.008;
- outnumbered: +0.041 / −0.018.

None of these replicates. An earlier read on a third of run C (+0.025 [+0.003, +0.052] over all forks) regressed to
+0.009 / +0.001 as the run grew. The forced chase also costs E −2 gems at mark 10 in C h0.

### 5. Declined chase against astraeus: the one open lead (does not replicate)

**Situation.** As in item 4, against astraeus (run C2).

KD gain, `chase=1x8`, C2 h0 / C2 h1:

| forks | mark 10 | mark 30 |
|---|---|---|
| all non-R/C | +0.008 [−0.022, +0.035] / **+0.062 [+0.027, +0.098]** | −0.018 / **+0.141 [+0.049, +0.236]** |
| F only | −0.001 / **+0.071** | −0.021 / **+0.145** |

- **Not one game:** the half-1 gain is spread over many games (top game 2.8 of 12.7 summed bodies at mark 10). It
  shows on `gen-ladder` (206 forks, +0.038 [+0.004, +0.081] at mark 10) and on `gen-small-brawl`, `gen-lakes` and
  `mut-ribs`.
- **But half 0 is level,** and the mirror is level (item 4).
- **Hurt target** (hp < 0.45; 20-40 forks a cell):
  - mark 10: +0.150 (significant) / −0.013 / −0.019 / +0.170 (significant), over C h0 / C h1 / C2 h0 / C2 h1;
  - mark 30: −0.073 / −0.109 / +0.017 / +0.204.
  - Too few to call.

**Examples** (forced chase gains in every rep; mirror run C):
- `gen-classic-140000401021#a` r343: Tavi (19,29) 900/900 on a farm turn, an enemy Vesper (24,32) 2374/2500 at 5, and
  four allies at hand. Ocean walks away and the Vesper escapes at 803 hp; the chase kills it at r348. CL 0.31
  against 0.98.
- `gen-ladder-140001500093#a` r241: Issac (35,34) 1040/1300 farming with three allies, an enemy Willow at 190/700
  nearby. The chase kills the Willow at r246. CL 0.01 against 1.14, and 1.12 against 2.39 at mark 30.
- `gen-ladder-140001500020#b` r174: Vendetta (17,20) 619/1400 against a Ren (18,16) 520/900 at 4. The chase kills the
  Ren at r181. CL 0.41 against 1.33.
- `gen-huge-140001212000#b` r557: Vesper (13,57) 1068/1600 on a bank turn, against a Vendetta carrying 32 gems. CL
  −0.15 against 1.29 at mark 10, but 0.14 against −1.28 at mark 30: the gain is a 10-round one.
- **Counter-case,** `gen-ladder-140003600018#a` r367: the forced chase's gain (−1.23 for ocean against 0.02) is a
  cascade. Ocean's own retreat line dies at r375, and the chase only avoids that line.

**Hypothesis**, if it is real: `preyable` (`fight.cc:557-575`) drops an enemy that is out of range, off our ground,
at health ≥ `hurt_health_fraction` (0.453), carrying no bag and with no hold. `prey` (`fight.cc:653-774`) also drops
a target whose `chase_trade` is lost.

**What it needs before anyone acts on it:**
- the finished C2 run;
- a second astraeus sample on fresh maps;
- a dedicated trigger: an enemy within 8 that is not chased, especially below 0.45 hp.

As it stands it is not evidence.

### 6. Doomed retreats: the lab can't resolve them

**Situation.** Ocean dies within 10 rounds of a retreat decision (the `death:5` trigger, run A).

- **On these forks,** alternatives survive more often than ocean's own diverged reps: 22% against 10%. Walking
  away-and-level for 3 turns survives 44% of the time, against 11%. The best arm survives where ocean's home-ward line
  walks into the enemy.
  - `gen-jungle-140003207001#b` r434: Issac 434/980 dies on ocean's line at r442, but survives with
    `walk:away:levelx3`. CL −0.48 against 0.00, and 0.31 against 1.05 at mark 60.
  - `gen-ladder-140001200111#a` r100: Ryth. CL −0.83 against −0.05 at mark 10, and −3.4 against 1.4 at mark 30.
  - `mut-wilds-140003517066#a` r621: Vendetta. CL −1.16 against 0.09, and −3.0 against −0.15 at mark 30.
  - Even a saving arm can score worse in KD (−4 in `gen-ladder-140001200010#a` fork 7).
- **This is selection on the outcome.** The trigger conditions on ocean's rep 0 dying. Ocean's own reps are
  replicates of that death and stay correlated with it, while the alternatives are less correlated, so the
  comparison favours the alternatives.
- **The pre-decision cell is tiny.** R with hp < 0.5, an enemy within 3 and dash ready (the situation before the
  death is known) has only 8 forks. Every class in R with hp < 0.5 and an enemy within 3 is negative.

**Hypothesis**, if real: `retreat_step` (`fight.cc:178-270`) scores steps by safety toward home, and can pick a
home-ward line through the enemy's reach where a sideways step escapes.

**What it needs:** a danger trigger that fires before the outcome is known (hp < 0.5, an enemy within 3), with
hundreds of forks, and multi-turn retreat paths as arms (see below).

## What the lab can't resolve, and what it needs

1. **Effects below ~0.03 bodies a fork.** A 1000-fork cell has a CI of about ±0.03-0.04 at mark 10 and ±0.06 at
   mark 30, so anything smaller is invisible. The scan's net bound (≤0.05-0.08 at mark 10) leaves room only for
   small, situation-wide effects. Those are A/B territory, not fork territory.
2. **Multi-turn plans.** Arms are one op held 1 or 3 turns, or a verdict held 3 or 8 turns. A planned escape (side
   step, then dash, then home) or a chase with a chosen dash turn can't be expressed. *Needs:* mixed op sequences in
   LabAct (a list of per-round ops), plus a retreat-path arm that takes a waypoint.
3. **Team decisions.** Verdicts are forced on the decider alone, while allies run ocean's policy. That biases against
   any stand or chase that only works as a group: the item 1 caveat, and probably the cascades in items 4 and 5.
   *Needs:* group arms that force the verdict on every lab champion within R of the decider.
4. **Target choice.** `chase:1` lets `prey` pick the target. The lab can't ask "chase *that* one". *Needs:* a
   target-id arm (force `prey()` to return a given enemy).
5. **Rare danger states.** The current triggers sample contact and branch changes. Low-health turns within reach
   (item 6) and declined chases on hurt targets (item 5) are a few dozen forks a run. *Needs:* triggers on those
   predicates evaluated before the decision, e.g. `danger:HP:D` and `unchased:HP:D`.
6. **Second-opponent coverage.** B and C2 are partial: 115 and 157 games. The astraeus-only lead in item 5 needs C2
   finished and a repeat on fresh maps.
7. **Decision-irrelevant noise.** Fuel jitter barely perturbs ocean: 10% of arms diverge by mark 10 at +1500, and
   20-25% at ±10k. Skipping a far champion's turn does better (14% of forks at mark 10). A noise model nearer the
   divergence between actions would tighten the cross-fit bound, e.g. skipping the turn of the nearest enemy outside
   12.
