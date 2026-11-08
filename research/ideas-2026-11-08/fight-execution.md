# Fight execution against Fish: where the +0.72 kills a game comes from (2026-11-08)

Analysis only; no bot changed. engage-numbers.md found that at matched local states Fish's engagements against us net
+0.72 kills a game more than ours against it (CI +0.21..+1.26), in v83-v86 scrims. This splits that term.

**Answer.**
- **Most of the gap is turn order, and CHANGES 464 has already closed it.**
  - In v83-85 the gap is +0.96 kills a game (CI +0.45..+1.62). In v86 (oc-base23 = oc-base22 + Fish's contact order) it
    is +0.07 (−0.96..+1.00).
  - The parts that fall with v86 are the ones turn order explains:
    - killing bursts that use a double turn (one champion acting at the end of one round and the start of the next);
    - kills in the turn a stun bought;
    - our champions caught walking home.
  - At v86 our double-turn kills exceed Fish's (0.46 against 0.21 a game).
- **Focus targeting, first-hit type, wasted stuns and resets explain nothing.**
- **What remains in current ocean is champion execution: Cassi and Marcella leave their exclusive damage spell unused
  far more often than Fish's.** Our Cassi walks off instead of casting; our Marcella takes reset + basic over the
  spell.
  - At Fish's cast rates, v86 would gain at most +0.29 kills a game (CI +0.18..+0.62), ≤ +1.0 points.
  - One arm is specified for it below: `params::excl_spell_gain`.

## Data and method

- **Rows.** engage-numbers' rows were recomputed for the 815 v83-v86 scrims against Fish (`~/tmp-offload/engage2/bin/fx.py`).
  The rows, engagements and kills match `rows-scrim.npz` exactly.
  - The extraction adds per-engagement features (first hit, its target against the candidates in the hitter's reach,
    focus and burst, stuns, resets, double turns) and every local champion death in r..r+19, with its timing, stun
    status, recall/retreat status and types.
  - 260k rows, 16,707 engagements, 8,399 deaths.
- **Turn order** was rebuilt per round: team seats alternate, A starting odd rounds, and within a team the order is by
  the previous round's priority, then id. It matched all 7.04M actions in the events (0 mismatches). From it:
  - each stun's lost turn and the turn it bought;
  - each victim's last real turn before death;
  - double turns.
- **Recalls.** Both bots start a recall and cancel it the next turn almost every turn (thousands a game). A recall
  counts only once the channel has outlived one of its owner's own turns.
- **Accounting** (`bin/split.py`): the execution term of engage-numbers.
  - Fish's engagements are reweighted to our engagement counts per state cell (36 cells).
  - Outcome splits (deaths by category) sum exactly to the total.
  - Engagement-type splits are Oaxaca twofold: Fish's mix at our returns, plus within-type.
  - Joint game bootstrap, 300 draws.
  - Per-version runs fix the cell mask from all 815 games (`OKFIX=1`), so the subsets compare.
- **Champion and spell detail:**
  - `bin/champs.py`: kills per engagement with the type present locally;
  - `bin/mar.py`: Marcella's turns in contact;
  - `bin/excl.py`: every turn of an exclusive damage caster (Cassi, Prism, Marcella, Stellar, Ren) with the slot
    ready and an enemy within 4.
- Points use engage-numbers' +3.3 points per net kill a game. That figure is correlational, so every point figure is an
  upper bound.
- Everything is in `~/tmp-offload/engage2/`: `fx.npz`, `split-*.txt`, `splitf-*.txt` (fixed mask), `champs.txt`,
  `examples-*.txt`.

## The splits (v83-v86 pooled; total +0.718)

Shares are of +0.718 and are not additive across splits: each split is its own partition. "v86" is the same split on
the 219 v86 games with the fixed mask.

| split | component | kills/game (95% CI) | share | v86 |
|---|---|---:|---:|---:|
| 1. first hit | Fish's mix of first-hit kinds (basic, stun, spell, HoR dash-stun, dash-in) at our returns | +0.012 (−0.046..+0.069) | 2% | |
| | first hit is a stun | +0.002 (−0.037..+0.037) | 0% | |
| 2. focus | first-hit target min EHP / nearest / max Strength | +0.017 / +0.021 / +0.013 (each CI spans 0) | 2-3% | |
| | carrier | −0.113 (−0.184..−0.045) | −16% | |
| | all round-0 hitters on one target | −0.026 (−0.058..+0.008) | −4% | |
| 3. burst and timing | kills in r..r+1 | +0.266 (+0.136..+0.424) | 37% | −0.01 |
| | killing burst includes a **double turn** | **+0.558 (+0.328..+0.766)** | **78%** | −0.25 (−0.81..+0.23) |
| | victim took ≥ 100% of its max health since its last real turn | +0.251 (+0.066..+0.453) | 35% | +0.04 |
| | kill **in the turn a stun bought** | +0.248 (+0.141..+0.361) | 34% | +0.01 (−0.20..+0.22) |
| | kill while the stun was still pending (it bought nothing) | −0.165 (−0.277..−0.058) | −23% | −0.09 |
| | damage dealt in r..r+1 (mediator; Fish deals less) | −0.154 (−0.251..−0.065) | −21% | |
| 4. cooldowns | wasted (overlapping) stuns | 0 (neither bot casts one) | 0% | |
| | damage into stunned targets | +0.005 (−0.015..+0.027) | 1% | |
| | missed resets (Fish misses more; the sign is confounded) | +0.051 (+0.019..+0.092) | 7% | |
| | exclusive damage spells left unused (counterfactual, not a partition; see Arm) | ≤ +0.45 (+0.24..+0.69) | ≤ 63% | ≤ +0.29 (+0.18..+0.62) |
| 5. disengage | victim **walking home** (≥ 2 tiles closer to spawn in 3 rounds) | +0.540 (+0.309..+0.730) | 75% | +0.08 (−0.34..+0.47) |
| | victim recalling / recall cut by damage | −0.189 / −0.339 | −73% | −0.20 / −0.33 |
| | all non-fighting deaths together | +0.012 | 2% | |
| | victim fighting | +0.706 (+0.281..+1.132) | 98% | +0.51 (−0.29..+1.26) |
| 6. champions | Fish's first-hitter types at our returns | −0.341 (−0.577..−0.135) | −47% | |
| | **Marcella**: same-type kills per engagement (2.56 a game × +0.114 (+0.083..+0.149)) | +0.29 (+0.21..+0.38) | 40% | +0.15 (−0.01..+0.29) |
| | Vesper Vale, Willow (same type) | +0.27 / +0.14 | | +0.08 / +0.16 |
| side | kills won / deaths lost | +0.681 / +0.037 | 95% / 5% | |

By version, with the fixed mask:

| version | games | execution |
|---|---:|---:|
| v83 | 255 | +0.84 |
| v84 | 214 | +1.34 |
| v85 (oc-base22) | 127 | +0.54 |
| **v86 (oc-base23, + CHANGES 464)** | 219 | **+0.07 (−0.96..+1.00)** |

Against v83-85:
- the total moves −0.89 (−2.08..+0.21; 95% of draws below 0);
- double-turn kills −1.10 (−1.69..−0.58);
- stun-bought kills −0.32 (−0.57..−0.10);
- walking-home deaths −0.62 (−1.10..−0.15).

Our engagements' own net per engagement hardly moves (+0.06 a game in every version). What fell is the net of Fish's
engagements against us: our threatened champion now holds the seat on each side of the round boundary.

### 1-2. First hit and focus: nothing

- **There is rarely a target choice at the first hit.** In 92-94% of engagements on both sides, the hitter has only one
  enemy champion in its reach.
- **Where there are two or more**, both bots pick the min-EHP target at similar rates.
- **Both concentrate fire.** Each puts ≥ 90% of r..r+2's damage on one target in 87% (ours) and 95% (Fish's) of
  engagements, at no value (composition −0.010).
- **Carrier.** Fish's first hits go to the carrier more often, and at our returns that would *cost* us (−0.11).
- **Kinds.** Fish's first hits are damage spells a little more often (38% against 30%), at the same returns.

### 3. Burst and turn order: already in ocean since v86

- **Fish converts with less damage.** Its engagements deal less in r..r+1 (362 against 396) and take more (139
  against 71), but kill more.
- **The difference was where the blows fell in the turn order.** Kills whose killing burst includes a hitter acting
  twice with no enemy turn between carry 78% of the gap.
- **The decoded examples (v83-85) are all one pattern.** A low or retreating champion of ours dies to a Fish hitter
  that held the last seat of one round and the first of the next.
  - `01a1b8f6` r255-256: Fish's Issac hits our Cassi in seat 9 of r255, twice, then kills her in seat 0 of r256.
    She had cast in seat 0 of r255 and had no turn in between.
  - `01a1b841` r224-226: Fish's Vesper hits our Ren in seat 0 of r224. Ren walks, then dashes away in seat 0 of r225.
    Fish's Vesper, again in seat 0, finishes him in r226.
  - `01a1b7c5` r1307: Fish's Vendetta deals 645 in seat 0 to our walking Stellar, which had moved in seats 5 and 4 of
    the two rounds before.
- **CHANGES 464 gives us the same seats** (contact: first seat when we start the round, last when they do).
  - In v86 the share of our fight damage dealt in double turns is 22.5%, against Fish's 20.6%.
  - Double-turn kills per game: ours +0.46, Fish's +0.21.
  - **We now use the contact order in fights at least as well as Fish.** Nothing to add.

### 4. Cooldowns

- **Stuns.** Neither bot casts an overlapping stun: ocean skips `stun_pending` targets, and Fish skips stunned ones.
- **Damage into stunned targets** is about the same (9% against 11% of damage).
- **Resets** are used after nearly every surviving basic by both (missed in 0.4% of our engagements and 1.3% of
  Fish's).
- **Exclusive damage spells are the cooldown gap.** See the Arm below.

### 5. Disengage: balanced overall; the walking-home part went with v86, and it is the retune agent's area

- **Retreat deaths are split by method.** Fish dies recalling (its recalls get cut by our damage), while we died walking
  home.
- **Across all non-fighting deaths it nets +0.01.** Walking home was +0.54 in v83-85 (+0.69) and is +0.08 in v86
  (CI spans 0). The contact seats let a walker take two steps before Fish acts.
- **Handed over:** generic retreat thresholds belong to the retune agent. No arm here: the v86 residual is not
  measurable.

### 6. Champions: Marcella, and exclusive casts generally

- **Fish's comp is not a better engager at our returns** (composition −0.34). The gap is inside types.
- **Marcella is the largest same-type gap.**
  - Fish's Marcella makes 0.213 kills per engagement she is in, against our Marcella's 0.099. That is +0.29 kills a
    game, 40% of the gap; v86 +0.15.
  - Two causes:
    - **Gold.** Fish's Marcella has Focus 241 against our 156 at round 400, and 430 against 196 at round 800. Her
      Focus-to-health split is the same (~2.5:1), so she simply gets more shards: about 25 to our 14 by round 400.
      This is an economy question, not fight execution, and is noted here only.
    - **Her cast choice:**

| Marcella adjacent, basic landed, damage spell ready | ours | Fish |
|---|---:|---:|
| turns a game (games with her) | 4.26 (225 games) | 1.96 (527 games) |
| casts the spell | 53%: 422 dmg, kill 0.151, dies ≤ 2 rounds 7.1% | 72%: 597 dmg, kill 0.323, dies 3.4% |
| walks off without casting | 46%: kill 0.005, dies 16.5% | 26%: kill 0.000, dies 12.8% |
| with the reset also ready: reset / spell | 80% / 20% (reset: 83 dmg, 0 kills, dies 11.7%) | 52% / 47% |

- **Every exclusive damage caster shows the same choice** (`excl.py`, with the slot ready and an enemy within 4). Fish
  casts more, ours walks:

  | champion, distance | cast rate, ours | cast rate, Fish |
  |---|---:|---:|
  | Cassi, adjacent | 17% | 30% |
  | Cassi, 2-4 | 24% (21 turns a game) | 34% |
  | Marcella, adjacent | 51% | 64% |
  | Marcella, 2-4 | 33% | 38% |
  | Prism, adjacent | 45% | 74% (36 games only) |

  - In v86 it persists:
    - Cassi 22% (CI 18-25) against 34% (31-36) at 2-4, and 17% against 32% adjacent;
    - Marcella 56% against 67% adjacent, and 31% (26-35) against 40% (37-43) at 2-4.
  - Ren is the exception: ours casts more than Fish's.
- **Walking does not visibly buy safety.** Our walk-off turns have a *higher* death rate within 2 rounds than our
  cast turns (Cassi 7.3% against 4.6% at 2-4; Marcella 15.5% against 6.2% adjacent). This is confounded: we walk where
  it is dangerous.
- **v86 examples** (`examples-excl.txt`):
  - `01a1b96b` r1823: our Marcella (spell 220) stands next to a Heart of Ruin at 985/2000. She plays basic, reset,
    basic (80 damage), then walks.
  - `01a1b96d` r944: our Cassi (spell 252) has that Heart of Ruin at 855/1800 two tiles away and steps off.
  - Fish, the same situation: `01a1b99a` r616, its Marcella casts 840 on a Vesper at 501 (kill); `01a1b978` r82,
    basic + spell on a Willow at 100 (kill).

## Arm: `params::excl_spell_gain` (exclusive damage spells over the walk)

**Result (2026-11-08): H0 at 1.5/2.0/3.0, and with the retreat-branch cast at 2.0; casts rose, kills did not.** See
[spell-marcella.md](spell-marcella.md).

- **Size.** This is the only component ≥ +0.3 points left in current ocean. At Fish's cast rates (our turns a game ×
  rate gap × our kills per cast, less our kills per non-cast turn):
  - pooled ≤ +0.45 kills a game (CI +0.24..+0.69);
  - **v86 ≤ +0.29 (+0.18..+0.62), ≤ +1.0 points**: Cassi +0.17, Marcella +0.12.

  The marginal cast falls on a healthier target than the average one, so expect about half of that.
- **Mechanism.** `plan_strikes` (combat/plan.cc) scores each turn's sequence as its hits' worth less the expected
  damage at the end tile. A walk adds the goal's step value (`leaf_value`).
  - An exclusive cast forgoes that step and the chance to end on a safer tile.
  - Its damage short of a kill counts at `hit_worth`: `chip_value` 0.247 of the damage, plus the concave fall in
    `kill_distance`.
  - So against a healthy target, a 200-500 spell loses to the step plus a lower end-tile danger. It also loses to
    Marcella's reset line (two basics, the stun's `stun_worth`, and the walk kept).
  - Fish casts whenever it stands. Its rule is "cast iff standing still", 95% on free rows (COMBAT.md §2).
  - The arm raises the worth of the exclusive spell's damage in that comparison only.
- **Change** (not implemented). In `Search::spell_unit` (combat/plan.cc), when `sp.excl && d > 0` and the slot does not
  stun, multiply the `hit_worth(...)` term by `params::excl_spell_gain`. Do it before the retaliation and
  `cast_cost` are subtracted.
  - That covers Cassi slot 0, Marcella slot 1 and Stellar slot 0.
  - It leaves out the stunning exclusive casts (Prism slot 0, Ren slot 0), which already cast as often as Fish's.
  - It leaves out `enemy_cast`'s retreat and escape paths (`cast_at_enemies(world, escape_step_value)` in fight.cc), so
    retreats keep their walk.
- **Grid:** `excl_spell_gain` ∈ {1.0 (control, identical build), 1.25, 1.5, 2.0, 3.0}.
  - Legality: it only reprices sequences the search already generates legally (the exclusive cast, then no walk; one
    cast a turn). Every value is legal.
- **Fuel.** One compare and one multiply per `spell_unit` call: a few dozen fuel a turn at most, none outside fights.
  At 1.0, `bench.py` replays must stay byte-identical.
- **Prediction.**
  - Cast rates: Cassi's at 2-4 tiles rises from 22% toward 30-34%; Marcella's spell share with both ready rises from
    20% toward ~45%.
  - Outcome: +0.1..+0.2 net kills a game against Fish, about +0.3..+0.6 points.
  - Where it shows: drafts with Cassi & Issac (87% of our games) or Marcella (28%), and mid-to-late game, where
    Marcella's Focus makes the spell 400+.
  - Expect less on the panel.
  - Risk: Cassi (600 health) dies more by standing. Check her death rate within 2 rounds of a cast in the A/B's
    replays.
- **Test.** Screen 1.5 and 2.0 first with `py tools/ab.py` against a frozen `variants/oc-base25`, using `--no-test-draft`
  (both bot directories have `test_draft` off) and distinct `--sprt-seed`s. Confirm on a held-out suite.
  - Check the predicted cast-rate shift with `bin/excl.py`'s logic on the A/B replays. If the rates rise and kills do
    not, look at the games that changed before trying another value.

## Not specified, and why

- **Turn order** (double turns, stun windows): closed by CHANGES 464. v86 matches or beats Fish.
- **Walking-home deaths**: generic retreat, which belongs to the retune agent. The v86 residual is +0.08 (CI −0.34..+0.47).
- **Focus targeting, first-hit kind, stuns, resets**: each ≤ 3% of the gap, or negative.
- **Marcella's Focus**: she gets less gold than Fish's Marcella. That is economy (shop/farm allocation), not fight
  execution.
- **HoR dash-in first hits** (6% of ours, 9% of Fish's; per engagement +0.04 against +0.17) are left to the HoR agent
  (hor-passive.md).
