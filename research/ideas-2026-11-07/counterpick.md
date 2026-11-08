# Counter-picking in ocean's draft (2026-11-07)

**Result: counters exist only in aggregate, and they are too small to draft on. No arm was built.** Held out, the
counter terms improve log loss by 1-9 (1e-4). No single pair is significant once the bot-against-bot matchup is
controlled. With the shrinkage CV picks, the largest pair is 0.036 logit. Ocean's draft with these counters is
predicted to gain at most +0.08 win-% points (5 picks), far below what a 40k-game A/B can see (±0.5).
The lightly penalised estimates would claim +6 points, but valued under the shrunk ones they lose 3: the
optimiser's curse, as with draft2's counters (-1.6).

Scripts and data are in `/home/ubuntu/tmp-offload/counter/` (`scripts/`, `sim/`; the archive columns in `archive/`,
one row per game in `games.pkl`).

## What a counter can use (rules)

- One pick per round, both teams each round. A pick is hidden until both have picked that round, so in round r we
  see their picks of rounds 0 to r-1. The first pick is blind, and the last sees all but one of theirs.
- The draft bot does not know who the opponent is. Their identity shows only through their earlier picks.
- In our ladder games, their earlier picks pin down their team:

| picks | modal team right, given 0 / 1 / 2 / 3 / 4 of their picks | distinct teams |
|---|---|---|
| 3 | 22 / 60 / 83% | 33 |
| 4 | 29 / 58 / 86 / 94% | 51 |
| 5 | 27 / 56 / 71 / 80 / 91% | 85 |

  So the information is there. The question is whether counters are worth acting on.
- ocean (`variants/oc-base21`) already has the plumbing, behind `draft_model::counters`, which is off. With
  counters on, round 0 scores against the prior's pick shares `q`. Each later round re-ranks teams that hold our
  picks against the revealed ones (`map_features.cc model_team`). The pick order puts the most counter-sensitive pick
  last.

## Data

- **Source:** big-arm's per-day archive, 2026-11-04 to 11-07 (engine 3.0.0 throughout but 92 games of 11-04).
  - 764,145 games among 808 teams, ranked and unranked.
  - Dropped: 1,384 games ending in a fault and 15 unrated, leaving **762,746**.
  - 11-05 and 11-06 are complete days. 11-04 and 11-07 hold only the top teams' games.
- **Top subset `r2000`** (both ratings ≥ 2000): 142,985 games, 1,740 team pairs.
- **Our games:** 10,229.

## Model

Logistic, P(A wins). Every term is antisymmetric (A's indicator minus B's):
- side;
- rating difference / 400;
- team-day effects (strength per submission period);
- champion x pick count;
- champion x map;
- same-team pair synergies;
- the counters: for pair (c < d), [c in A, d in B] - [d in A, c in B]. This is model.mjs's convention, so
  ctr[pair(c, d)] is our c's edge against their d.
- **Robustness term:** a team-pair effect (unordered pair). It absorbs the bot-against-bot matchups that fixed
  compositions would otherwise lend to the pair terms.
- **Penalties:** L2 on the summed loss (team 1, champion 10, map 30, synergy 30, team pair 3); the counter penalty
  is searched.
- **Cross-validation:**
  - map-grouped: 5 folds of maps;
  - team-grouped: 5 folds of teams; the test set is every game with a held-out team, and these fits have no team
    effects, so a held-out team's strength comes from its rating. With team-day effects in, the rating's
    weight drifted between fits (2.1 against 0.7 logit per 400), and the team-grouped loss was meaningless.

## Results

**Held-out log-loss change from adding counters** (1e-4; negative is better). Each row is at its best penalty, on
the summed loss.

| games | controls | map-grouped CV | team-grouped CV |
|---|---|---|---|
| r2000 | team-day | -24.5 (λ 1000) | -3.3 (λ 1000; 4 of 5 folds better) |
| r2000 | team-day + team pair | **-8.8** (λ 1000; folds -3.0 to -15.6) | -3.3 |
| all | team-day | -12.7 (λ 3000) | -0.8 (λ 10000; 4 of 5 folds) |
| lab, draft6-ctr (draft6.md) | lab design | -3.7 | |
| lab, draft7-f92-ctr (F92, ctr searched: 1280) | lab design | -4.4 (0.55288 vs 0.55332) | |

The lab's final refit, with its ablation CVs, was stopped after 2.8 h on 8 shared slots. So its counters were not simulated. Its CV gain is the ladder's size.

- About two thirds of the map-grouped gain is team matchups: the team-pair term takes -24.5 to -8.8.
- On new teams, the counters are worth 0 to 3 (1e-4).
- At the chosen penalty the counters are tiny: |ctr| ≤ 0.036. The largest are:
  - Vend > HoR +0.036; Pris > Tavi -0.036;
  - Ryth > Vesp, Marc > Varg and Vesp > Pris -0.028;
  - Ryth > Pris +0.025; C&I > Tavi +0.024.

**Pairs** (r2000, light penalty λ 10, Wald z, Benjamini-Hochberg over the 66):

| controls | q < 0.05 | |z| > 2 (model SE) |
|---|---|---|
| team-day (team-pair-clustered SE) | 6 | 6 |
| team-day + team pair | **0** (best: Vend > HoR +0.12, q 0.055) | 3 (chance: 3.3) |

- Without the matchup term, the six are Vend > HoR +0.12, C&I > Ren -0.16, Will > HoR +0.11, Vesp > HoR +0.09,
  Ryth > Ren -0.14 and Ren > Varg +0.17.
- None survives the matchup control. No pair is real on its own.
- "X > HoR" terms are relative to X's main effect, because nearly every team holds HoR.

**Our own games by true version** (the eras of willow.md, then v83 from 11-07 19:05):
- **Method:** fit on everyone else's games (λ 1000, rating for strength), score ours.
- **Result:**
  - ocean v78-v84: **+16.8 ± 8.1** (1e-4) better with counters, 6,219 games;
  - all ours: +7.7 ± 6.4, 10,229 games;
  - proteus eras: -6 to -7.
  - Opponent-clustered SEs throughout.
- So the ladder's counters do transfer to ocean's games, at about 2 SE.
- **Pairs fitted on our games alone** (era x map and opponent effects): ±0.15 SEs. The largest z is 3.75
  (Stel > Pris -0.87, 278 games, proteus's Stellar). Too noisy to act on.

## Actionable: what the draft would do with them

`sim/sim_main.cc` runs oc-base21's `model_team` natively, round by round, as `model_draft` does:
- re-rank on revealed picks;
- kept champions keep their order;
- opponents are the 16 test compositions per pick count, in their pick order, weighted, on the 128 ladder maps.

Teams are compared with counters off. The gain is the lab model's base value (b + w.z + synergies) plus the counter
terms of the "truth" vector.

| counters drafted with | valued with | team changed 3 / 4 / 5 picks | predicted gain, win-% points 3 / 4 / 5 |
|---|---|---|---|
| ladder, CV penalty (λ 1000) | same | 0.3 / 6.8 / 12.8% | +0.00 / +0.01 / **+0.08** |
| ladder, light (λ 10, |ctr| ≤ 0.18) | same | 35 / 68 / 88% | +0.65 / +3.3 / +6.0 |
| ladder, light (λ 10) | ladder λ 1000 | 35 / 68 / 88% | **-0.50 / -2.1 / -3.2** |

- The shrunk counters move few teams and gain nothing measurable.
- Unshrunk counters move most teams and lose once valued honestly.

## Decision

The authorised plan builds arms "if counters are real". They are real only as a small aggregate held-out gain. No
pair is significant, and the predicted draft value is ≤ 0.1 point. A ladder-composition A/B of 40,960 games resolves
about ±0.5, so an arm cannot win a test it is predicted to tie. No arm, no games, no merge.

**What would change this:**
- A patch that makes one champion a hard counter, so that one pair is worth ≥ 0.15 logit and survives the
  team-pair control.
- A per-opponent model: the earlier picks identify the opponent bot, which predicts their team 56-94% of the time.
  The bot-against-bot matchup term above is large. Exploiting it means modelling opponents, not champion pairs.

## Team-specific counters (2026-11-08)

**Result: there is no team-specific counter to draft on, ours or an opponent's. No arm.** The previous fit shared each
counter across all teams. That could hide counters that belong to one team's playstyle, and the team-pair term
absorbs only overall bot-against-bot results. So the counters were refitted per team.
- In-sample, team-specific counter variance is real (permutation p < 0.05).
- All of it is team-by-map style. Drafts are fixed per map, so a counter term can stand in for "team T does well on
  map m". With a team x champion x map term in the model, the counter variance's best estimate is zero.
- Held out on new maps, team-specific counters make log loss worse.
- Cross-fitted, ocean-specific counters are worth -0.07 ± 0.38 win-% points in ocean's draft (+0.08 ± 0.08 at the
  tighter prior that map CV supports). Opponent-aware drafting is worth -0.9 to +0.01.

Scripts and outputs are in `/home/ubuntu/tmp-offload/counter2/` (`scripts/`, `sim/`).

### Model

The model above (side, rating, team-day, champion x pick count, champion x map, synergy, shared counters at λ 1000,
team pair), plus these per-team blocks, each L2-penalised (a Gaussian random effect, sd = 1/√(2λ)):
- `tm`: team strength across all days, so a time split keeps each team's strength.
- `tc[T, c]`: team T's champion c, its style main effect.
- `u[T, c, d]`: T's c against the other side's d, ordered (132 per team). An opponent-side counter ("anyone's c
  against T's d") is the same parameter, -u[T, d, c], so one block covers both sides.
- `tcm[T, c, m]`: T's champion c on map m, i.e. style x map. Since T's team on map m is fixed, this is close to
  "T on map m".

A team is its uuid; ours is split into the proteus and ocean lineages.

Cross-validation:
- 5 map-grouped folds;
- two time splits: fit 11-04 to 11-06 and test 11-07 (3,058 games); fit 11-04 and 11-05 and test 11-06 (73,695).

### 1. Heterogeneity

**Held-out log-loss change** (1e-4, summed over folds; negative is better):

| subset | added | to | map CV (per fold) | test 11-07 | test 11-06 |
|---|---|---|---|---|---|
| r2000 | tc λ30 | base | -39.3 | -205 | -68 |
| r2000 | u λ100 | tc | +10.7 (+8.5 +23.9 +7.1 +14.7 -0.4) | -31.1 | -10.4 |
| r2000 | u λ300 | tc | -0.8 (-1.6 +5.3 -2.4 +1.5 -6.5) | -25.5 | -10.0 |
| r2000 | tcm λ30 | tc | -7.3 | **-376** | **-315** |
| r2000 | u λ100 | tc + tcm | +5.4 (+2.1 +14.3 +3.1 +10.4 -3.0) | -11.6 | -4.7 |
| r2000 | u λ30 | tc + tcm | +33 | +7 | +17 |
| all | tc λ30 | base | -50.0 | -217 | -60 |
| all | u λ100 | tc | +8.2 (+17.8 +10.9 +7.9 +2.7 +1.3) | -46.1 | -1.9 |
| all | u λ300 | tc | -0.7 (+3.7 +0.5 -1.4 -2.9 -3.8) | -34.5 | -6.2 |
| all | tcm λ30 | tc | -4.8 | **-429** | **-319** |
| all | u λ100 | tc + tcm | +4.1 (+13.4 +6.8 +3.6 -1.0 -2.8) | -19.3 | +2.2 |
| all | u λ30 | tc + tcm | +29.7 | -6.2 | +32.4 |

- On new maps, team-specific counters do not transfer: the u rows are level or worse in 4 of 5 map folds.
- On a new day they are worth -5 to -31 on r2000 and -2 to -46 on all games. Once tcm is in, they are worth -5 to -12, inside the noise of the 3k-game
  11-07 test.
- The large held-out term is team style by map: tcm is worth -300 to -380 on a new day.

**Variance components** (r2000, Laplace marginal likelihood):
- **Conditional:** the other terms profiled out.
- **Integrated:** every term's Gaussian prior integrated, REML-like.
- **LR test:** each LR is against variance 0.
- **Permutation null:** u's team labels shuffled among game-sides with the same (own set, opponent set)
  composition. 79% of game-sides are in strata holding more than one team. 18 permutations.

| block | given | prior sd | LR | permutation null |
|---|---|---|---|---|
| tc | base | 0.35 | 2,221 | |
| u | base | 0.125 | 2,399 | |
| u | tc | 0.088 (conditional); 0.18 (integrated) | 325; 1,230 | max 0 (conditional), 31-98 (integrated): p < 1/19 |
| tcm | tc | 0.50 | 20,618 | |
| u | tc + tcm | **0** (the conditional marginal likelihood is highest at λ → ∞) | ≤ 0 | |

So the user's hypothesis holds in-sample: team-specific counters are not noise. They have sd ≈ 0.09-0.18 logit
around the shared ones, and pooling does hide them. But they are explained by style per map (tcm, sd 0.5), and what
is left does not predict new maps. The integrated variance of u given tcm could not be computed: with 57k tcm
columns, the dense log-determinant is too large.

### 2. Ocean-specific counters

- **Fit:** r2000 plus all our games, 144,470 games.
- **Prior:** every team's u at λ 64. This is sd 0.088, the conditional estimate given tc: the loosest prior that
  part 1 supports.
- **Other terms:** tc λ30 and tcm λ30.
- **SEs:** from the inverse Hessian over every term but champion x map and tcm.
- **Result:** posterior means of u[ocean, c, d], our c against their d, as a deviation from the shared counter:

| our > their | u | SE | games |
|---|---|---|---|
| HoR > Marc | +0.094 | 0.073 | 1,344 |
| Ren > Tavi | +0.094 | 0.081 | 501 |
| Marc > Vend | +0.094 | 0.074 | 2,141 |
| Marc > Tavi | -0.090 | 0.078 | 1,187 |
| Marc > HoR | -0.086 | 0.076 | 2,501 |
| Vesp > Marc | +0.086 | 0.072 | 1,413 |
| Tavi > Vesp | +0.084 | 0.081 | 416 |

- Every |z| is below 1.3. Without tcm, the largest is Marc > HoR -0.128 ± 0.076.
- The lighter prior's estimates are shrunk hard: the posterior SE (0.07-0.08) is close to the prior sd (0.088).

### 3. Opponent-specific

**Raw cells** (our set against their set, ocean lineage):
- Mite: 2,785 games, 118 cells; Fish: 1,290 games, 126 cells.
- Between-cell spread (sd of the true win rate, beta-binomial): 0.23 and 0.22, χ² p < 1e-20.
- The cells are maps, though: we played more than one team against the same opponent on the same map in 466 of
  1,206 opponent-map cells. So this spread is mostly map strength.

**Within our own games:** e[O, c], our champion c against opponent O, for the 11 opponents with ≥ 100 games (6,349
games).
- **Controls:** opponent x map, opponent x day, our era, and our champion x map effects.
- **Held out** (1e-4):
  - opponent-map-grouped folds: -29 (prior sd 0.18);
  - random folds: -18.
- **Variance:**
  - conditional marginal likelihood: 0;
  - integrated: sd 0.35, LR 35.
- **The largest, at sd 0.35, all within 2.6 SE:**
  - against Fish: our HoR -0.51 ± 0.20, C&I -0.33 ± 0.24, Vesp -0.33 ± 0.20;
  - against Mite: our Vesp -0.44 ± 0.20, Ren +0.34 ± 0.21, C&I -0.34 ± 0.24;
  - against BBL: our HoR +0.51 ± 0.30.

**From the ladder fit** (u[O, d, c], their d against anyone's c):
- Mite's C&I against Marc +0.21 ± 0.07 and Vesp against Vend +0.16;
- Fish's Vesp against Marc -0.14 ± 0.07 and C&I against HoR +0.13;
- BattleCats' Prism against C&I +0.18 ± 0.07.

This is about what 1,500 cells would give by chance at |z| ≈ 3.

**Identification:** modal opponent given the map and their first 0-4 picks.

| | 0 / 1 / 2 / 3 / 4 of their picks |
|---|---|
| lookup on 11-04..06, scored on 11-07 (419 games), all | 3 / 47 / 72 / 74 / 75% |
| same, Fish | 13 / 53 / 62 / 63 / 67% |
| in-sample (all days), Mite | 77 / 94 / 95 / 95 / 94% |
| in-sample (all days), Fish | 17 / 63 / 69 / 70 / 73% |

Mite and BBL do not appear on 11-07. Mite is identified early and is easy; Fish is the hardest of the top opponents.

### 4. Value in ocean's draft

**The simulator:** a Python port of oc-base25's `model_team` and sim_main's round loop (`sim/pysim.py`).
- It matches the C++ sim on all 2,048 map x composition drafts: counters off, λ 1000 and λ 10.
- oc-base25's draft model is byte-identical to oc-base21's.

**The games valued:** our 4,774 ocean-lineage games on the 88 of the archive's 128 maps that are in `maps/`, each with
its real opponent and that opponent's team in pick order. The other 40 maps are not on disk (30% of our games).

**What ocean drafts with:**
- **shared:** the shared counters;
- **ocean:** shared + u[ocean];
- **ident:** the opponent model: the posterior over the top 12 opponents given the map and the picks revealed so far
  (a leave-one-out lookup over our games), that opponent's teams on the map, and V_O = shared + u[ocean, c, d] -
  u[O, d, c];
- **oracle:** as ident, with the opponent known.

**How it is valued:** the lab model's base + synergy change, plus the counter terms under a "truth" fit, against the
real opponent's u.
- **cross:** draft with one random half of the maps' fit and value with the other half's; mean ± SE over 6 splits.
- **bayes:** draft and value with the full fit. It shows the optimiser's curse.

**Predicted gain, win-% points** (all valued games; Mite and Fish subsets):

| prior on u | valued | shared | ocean | ident | oracle |
|---|---|---|---|---|---|
| λ 64 (sd 0.088) | cross | -0.15 ± 0.11 | **-0.07 ± 0.38** | -0.49 ± 0.44 | -0.90 ± 0.42 |
| | cross, vs Mite | -0.33 | +0.83 ± 0.53 | +0.78 ± 0.70 | +0.23 ± 0.73 |
| | cross, vs Fish | +0.01 | -1.23 ± 0.48 | -2.19 ± 0.68 | -2.70 ± 0.67 |
| | bayes | +0.16 | +2.48 | +4.18 | +4.66 |
| λ 256 (sd 0.044; map CV level) | cross | -0.05 ± 0.06 | **+0.08 ± 0.08** | +0.01 ± 0.11 | -0.07 ± 0.14 |
| | cross, vs Mite | -0.13 | +0.34 ± 0.12 | +0.45 ± 0.17 | +0.37 ± 0.25 |
| | cross, vs Fish | +0.02 | -0.24 ± 0.10 | -0.62 ± 0.21 | -0.77 ± 0.24 |
| | bayes | +0.12 | +0.75 | +1.45 | +1.63 |

- The lab model's base value lost by these team changes is -0.8 (ocean) to -2.5 (oracle) points. The counter terms do
  not pay it back once they are valued on independent data.
- The in-sample "bayes" claims of +2.5 to +4.7 are the optimiser's curse again, as with the light shared counters.

### Decision

The honest predicted gain is under the +0.3 bar at both priors:
- ocean-specific counters: -0.07 ± 0.38 at λ 64, +0.08 ± 0.08 at λ 256;
- opponent-aware ones: -0.9 to +0.01.

So no arm was proposed and no games were played.
- **The one lead:** against Mite, ocean-specific counters are +0.34 ± 0.12 at λ 256 (+0.8 ± 0.5 at λ 64). Against
  Fish, the same draft loses 0.24 ± 0.10 (-1.2 ± 0.5).
- **A Mite-only arm:**
  - Mite is identified early: 94% from its first pick, in-sample.
  - The arm would add about +0.34 x Mite's share of our games, ≈ +0.14 overall.
  - Keeping Mite and dropping Fish is choosing opponents by the outcome, the optimiser's curse at the opponent
    level.
  - +0.3 against one opponent is far below what the paired scrims resolve.
- **What would change this:** a counter that survives the tcm control on held-out maps.
- **Where the information is:** team style per map (tcm) is the large persistent effect, -300 to -380 (1e-4) on a new
  day. It is about the opponent bot on a map, and the draft cannot choose the map. If it is used at all, it is for
  play (e.g. expecting a strong opponent's known plan on a map), not for picks.
