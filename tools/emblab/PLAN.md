# Emblem lab round 2: plan (revised after a read-only audit, 2026-10-29)

Goal: a learner that improves astraeus's emblem choices quickly from very many games, free to choose any emblem,
conditioned on champion, pick count, map features and game state. Round 1 (CHANGES 232, EXPERIMENTS "Emblem lab main
run") gave +2.0 points from a static table; the fit could not use map features (overfit) or game state.

## What round 1 established

- Batches now run at ~82 games/s (40k in ~8 min; the other agent's runner work), an A/B of ~1,100 games in ~45 s.
- Reach of the k-th new emblem, of 1.376M champion-games: k0 98.3%, k1 92.0%, k2 82.1%, k3 71.6%, k4 61.7%,
  k5 52.7%, k6 44.8%, k7 38.1%, k8+ 32.3% (some champions reach k ~ 100; Power and Bruiser repeat). Only k < 8 was
  ever forced.
- Uniform forcing over 39 arms wastes most forced decisions on clearly bad arms (Focus on non-casters: -3 to -7 points
  at k0) and degrades the game states later decisions are learned in.
- The whole-game intention-to-treat fit is unbiased but noisy: one game outcome spread over ~16 forced decisions, with
  no conditioning on state.

## 1. Games (vehicles and assignment)

- **Base policy:** astraeus 8fad72c (learned table + gold 1.5x). "Not forced" means the base's own choice (table arm
  or current logic), so every round measures departures from the current best bot.
- **Ordinals 0..11** forced (k >= 12 stays with the base), each with probability p_k (start: 0.35 at k0, 0.5 after).
- **Proposal over arms, never eliminating any:** for each (pick count, type, ordinal) cell, a forced arm is drawn from
  q = (1 - eps) * top-two Thompson over the current fit's bootstrap draws + eps * uniform over all 39 arms, eps = 0.3,
  and every arm's q floored at 0.4%. The base's own arm is excluded (it is the control). q is written into the
  table and the game record, so every estimate can use the known propensity.
- **Drafts:** as round 1 (explore without Stellar / ladder prior / night1 teams); coordinate with the draft-lab work
  before changing.
- **Logs (debug_block, free locally):** per decision, besides today's EMB fields: both teams' submitted gems
  (`global_submitted_gems`), own team's carried gems, allies alive, enemy champions seen alive, round, gold, stats,
  the base's choice and the current logic's choice and value, and the current logic's value of every arm (analysis
  only: 39 pinned evaluations are too dear to ship).
- **Maps:** everything but the held-out suites; generate two or three more held-out fresh suites for 10k-game A/Bs.

## 2. Fit: per decision, under sequential randomisation

Each forced arm is drawn before the game, independently of everything, so at the moment decision k is reached its
assignment is independent of the state then (round, score, items) and of whether k was reached. Hence, among
reached decisions, the effect of the arm *conditional on the state at k* is unbiased; the round-1 bias came from
summing per-decision terms over a game whose number of reached decisions depends on how it goes.

- **Rows:** reached decisions. **Outcome:** the decision's team wins.
- **Baseline (nuisance) terms,** pre-treatment for decision k: draft and map terms (as fit.mjs, per pick count), state
  at k (score difference and sum, round, gold, k, allies alive), and the table assignments of the team's and enemy's
  other ordinals (ITT; independent of the arm at k). These soak up most outcome variance, so the arm effects are far
  sharper than in the whole-game fit (CUPED-style variance reduction).
- **Effect terms,** arm a against the base's choice: per (type, kb, family, stat) as now with k up to 11 (kb = k for
  k < 6, then 6-8, 9-11); arm-family x map features through a low-rank map embedding (r = 2-3 learned map factors
  instead of 14 x 19 free terms, which overfit); arm x state (score difference, round, gold, the base choice's family,
  current logic's value of the arm where cheap to compute in the bot).
- **Fitting:** penalised logistic regression (the existing L-BFGS on worker threads), CV and bootstrap by map. A
  gradient-boosted model (install LightGBM in the venv) on the same rows as a check on what the linear model misses.
- **Policy evaluation before any A/B:** doubly robust off-policy estimate of a candidate policy's win rate from the
  randomised decisions with their propensities. Choose thresholds and feature sets by this, then A/B the best.

## 3. Deploy

- `best_emblem` scores the arms with the fitted linear model over features the bot can compute cheaply at the
  decision (type, pick count, k, map features from the draft step, score, round, gold, base choice) and takes the
  argmax if its margin over the base clears a threshold chosen by off-policy evaluation. Cost: ~39 x 30 multiplies
  per new emblem.
- A/B on held-out suites, 10k games (~7 min, ~±1 point).

## 4. Loop

play 160k games (~35 min) -> fit (~10 min) -> off-policy check -> 10k A/B -> the winner becomes the next base.

## Revisions after the audit (supersede the sections above where they differ)

- **Variance reduction is small where it matters.** Decisions come early (median round 97 at k0, 260 at k1, 398 at
  k2); the last gem checkpoint before a decision explains 0.4% of win variance at k0, 7% at k1, 13% at k2, 26% at k7.
  State covariates stay, but they are not the lever.
- **No whole-policy off-policy evaluation.** A team reaches ~28 decisions below k12, so importance weights collapse
  (median probability of playing the base throughout ~1e-8). Judge policies by A/B (10k games ~7 min); use
  off-policy estimates only for single-decision changes.
- **Proposal drawn in the vehicle at decision time,** from a seeded RNG in the table: q(a|s) = eps * uniform over
  arms whose passive is not owned + (1 - eps) * softmax((v[a] - v[base] + fitted correction) / tau), q logged per
  decision. v is free there (debug_block pauses fuel). No arm is ever below eps / 39. ~10% of games keep low-p uniform
  forcing as an unbiased check. Owned-passive fallbacks (7% of forced draws at k1, 43% at k7) disappear because only
  eligible arms are drawn. Lower p at late k.
- **Fit per ordinal,** with smoothing across k (no k3+ pool deployed onto k3..7), a type x ordinal term for the
  base's own value, arm x (v gap, the current logic's pick family, round); select arms on CV folds and score on
  held-out folds (the full-fit argmax read off bootstraps has a winner's curse); report gains on the probability scale.
- **Deployable state:** the current logic's own pick costs nothing. All 39 arm values need one pass of value() over
  every arm (est. ~3x a current_emblem call): measure with tools/fuel/bench.py before relying on it. Map features
  exist only in the draft step; passing them needs space in draft memory (unchecked).
- **Vehicle patches** must follow 8fad72c's shop.cc (scale gold once, log the base's choice and the current logic's
  separately, ordinals 12).

## Order of work

1. From existing data, no new games: a table keyed also by the current logic's pick
   (learned_arm[picks][type][k][its family]), fitted per decision (the pick is pre-treatment, the arm random), per
   ordinal. Also fixes the k3+ copies (5-pick Ryth buys Bruiser-Health at k3..7, never sampled). A/B against 8fad72c.
2. Round-2 vehicles and lab as revised above; first batch, then the per-decision fit.
3. A params lab: each team-game's params.h constants drawn from the trainer table (one draw per game, a clean
   design), fitted as a response surface per pick count. Gold price alone moved ~1 point.
4. Greed and shop timing (Greed's 35 stats per 750 gold beat 5 Power emblems' 30 for the ~10% past k14).

## Open questions

- Is the score at decision time informative enough, or should the logs carry a win-probability estimate?
- Does forcing at k0 (98% reach, the biggest lever) cost too much game quality even with the Thompson proposal?
- Should drafts be learned in the same games (one lab), given the draft lab's ongoing changes?
