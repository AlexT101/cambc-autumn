# Draft model features: one-altar and misspecification (ocean, 2026-11-06)

Question: is exactly one altar special to the draft model? The deployed model (`replays/draftlab/draft5`, 1,088,482
self-play games, fitted 2026-11-05T03:14) sees altars only as `altars` (log1p), `altar_ratio` and `altar_centre`.
Offline only, no new games: every number is 5-fold cross-validated log loss over maps (the lab's folds, `hash(key) % 5`),
scored on wins, as `model.mjs fit --search` scores it. Changes are in units of 1e-4 with the fold-to-fold SE; "map SE"
clusters the paired difference by map. For scale, the map terms are worth 233 (no-map model 0.6221 against 0.5988).

Tools: `draftfeat-tools/` (`mx.mjs` is a scratch copy of model.mjs with candidate features and `cvx`, which cross-validates
several feature sets on the same games and folds and dumps per-map losses and per-fold logits; `prep.py`, `gbm.py`,
`score.py`, `side.py`, `compare.py`, `cross.mjs`; `cvN-compare.txt` are the tables). Large outputs:
`/home/ubuntu/tmp-offload/draftfeat/`. Candidate lab: `replays/draftlab/draft5-feat` (links draft5's games, maps and
priors; own config and model.json). Candidate bot: `bots/variants/oc-draftfeat` (copy of `variants/oc-base4`).

## 1. The deployed fit, reproduced

`model.mjs fitbench --lab replays/draftlab/draft5 --cv --warm --threads 32`: **0.59876**, as model.json's `cv.model`.
The 5-fold CV took 19.2 s on 32 threads from a warm start (60 Newton steps); 1:42 wall in all, most of it reading the
games and the warm full fit. On the loaded box later (load 65-100) one feature set took 64-130 s, 92 features ~7 min.

## 2. Altar candidates

Note first: no pool map has 0 altars (min 1), so `zero_altar` is constant and changes nothing. A pick-count interaction
is already in the model: each pick count has its own fit (shrunk toward the pooled one).

| Added to the 25 | CV change | fold SE | folds better | one-altar maps | reweighted to ladder-mix altars |
|---|---|---|---|---|---|
| one_altar | **-0.42** | 0.16 | 4/5 | -6.6 ±3.3 | -1.5 ±0.8 |
| one_altar, two_altar | -0.59 | 0.23 | 4/5 | -6.7 ±3.3 | -1.3 ±0.8 |
| one_altar, two_altar, altars 3-4 (bins) | -0.61 | 0.24 | 4/5 | -6.5 ±3.3 | -1.3 ±0.8 |
| odd_altar (a self-mirrored altar) | -0.72 | 0.26 | 4/5 | -7.3 ±2.2 | -2.3 ±0.6 |
| log1p(altars)^2 | -0.45 | 0.10 | 5/5 | -4.7 ±0.9 | -1.2 ±0.2 |
| one_altar x each of the 24 others (separate slopes on one-altar maps) | -2.22 | 0.58 | 5/5 | -38.6 ±10.0 | -8.9 ±2.3 |
| zero_altar | 0 | - | - | - | - |

So **one altar is special, but only a little**: a consistent gain about 2.6 SE from zero, ~20x smaller than what
follows. One-altar maps are 4.9% of the lab's pool (it is `--mix varied`, fresh-160000..160099) but 25% of the ladder
and 23% of a ladder-mix suite (the 2,047 maps of fresh `df-991101..991108`), hence the reweighted column.

Per-champion effect of one_altar in the final model (draft5-feat, below), win-percentage points against the average
champion on a one-altar map compared with another (25 x logit):

| Picks | favoured | disfavoured |
|---|---|---|
| 3 | Prism +2.7, Heart of Ruin +2.2, Marcella +1.3, Willow +1.0 | Vendetta -3.9, Vesper -1.5, Cassi -0.7 |
| 4 | Prism +2.9, Heart of Ruin +1.9, Marcella +0.9, Willow +0.7 | Vendetta -3.5, Vesper -1.3, Ryth -1.2 |
| 5 | Tavi +2.8, Stellar +1.5, Ryth +0.9, Willow +0.9 | Varg -3.0, Vendetta -2.5, Vesper -1.9 |

The one_altar-only fit gives about the same picture (Vendetta -3.9/-3.9/-2.6, Prism and Heart of Ruin +2 on 3-4 picks).

## 3. Misspecification check

**Score tests** (`score.py`): for each candidate g(map) x champion, the score statistic on the base model's out-of-fold
residuals, g projected off [1, z]. chi2(12) is ~12 under the null; one_altar scored 174 (rank 107 of 343). The top ones
were mapgen metrics the model never had: **monoliths 2188** (Prism -26 z, Heart of Ruin +19, Marcella +18), **golems
1613**, camps_side 1027, walls 888, shared_groups 640, and economy curvature (gems_side x big_share 1547, gems_side x
gold_side 1440, gems_side^2 1305).

**GBM** (`gbm.py plain`, sklearn HistGradientBoosting; lightgbm/xgboost are not in the venv): map features (the 25
transformed, raw altar count), pick count, side, our and their champions as multi-hot vectors and their difference;
trained on rows plus side-swapped copies, early-stopped on 12% of the training folds' maps, same 5 map folds.
**CV 0.59131 against the logistic's 0.59876: -74.5** (folds -68, -77, -80, -71, -74). The logistic is clearly
misspecified. Its split gains: champion-difference splits (Cassi, Prism, Vesper) under each other and under
gems_side, cluster_share, gold_side, big_share, area; pick count with Prism, Cassi, Stellar, Tavi.

Not the cause: the logistic is calibrated (out-of-fold slope 0.99-1.00 per pick count); mirrored champions leave no
residual; a map-dependent side advantage gains nothing (-0.16, `side.py`).

**Candidates from it, refitted as in section 2** (all 5/5 folds better):

| Set | Features | CV change | fold SE | one-altar maps | ladder-mix weighted |
|---|---|---|---|---|---|
| monoliths, golems (log1p) | 27 | -7.7 | 0.57 | -6.7 | -7.7 |
| + camps_side (log1p), walls, shared_groups (log1p) = raw5 | 30 | -16.0 | 0.33 | -3.0 | -14.0 |
| raw5 + one_altar | 31 | -16.7 | 0.48 | -13.0 | -16.3 |
| all 25 squares (alone) | 50 | -14.6 | 0.87 | -15.9 | -15.5 |
| raw5 + one_altar + 16 products/squares (score-test top) | 47 | -35.1 | 0.61 | -18.4 | -31.5 |
| + all 25 squares | 68 | -39.9 | 0.58 | -23.6 | -37.1 |
| + 24 more products (score test on the 47's residuals) = **F92** | 92 | -48.1 | 0.27 | -47.5 | -48.0 |
| **F92, w penalty 320** (1280 deployed) | 92 | **-53.4** | 0.35 | -47.7 ±8.8 | -52.4 ±2.6 |
| F92, w 80 | 92 | -54.0 | 0.58 | -44.1 | -52.3 |
| F92, w 5120 | 92 | -39.1 | 0.42 | -44.5 | -40.4 |
| F92 (w 1280), counters on (ctr 320) | 92 | -50.7 | - | - | - |
| 25 base, counters on (ctr 1280 / 320 / 80) | 25 | -2.9 / -2.7 / -2.6 | 0.20 | -0.6 | -2.9 |

syn 80 and b 16 change nothing; 24 further products, and cubes of the 12 features with the most residual-GBM gain
(the cheap champion x feature shapes left to try for the residual -16), went numerically degenerate (NaN) and were
dropped. The products
were chosen by score tests on out-of-fold residuals of the same games, a mild selection bias: their chi2 were 200-500,
against ~35 for the largest of 300 null draws. **Counters**, never searched since draft3 (ctr pinned at 1e9), are back
to a measurable -2.9; the bot ships without them (draft2's counters lost an A/B), so F92 keeps them off.

What is left after F92 (`gbm.py resid`: a Newton-step GBM on F92's per-fold logits, w 1280): **-16.1** more
(0.59395 to 0.59234); map features x champion difference alone -14.2, compositions alone (no map) -2.1, about what
counters give. So the rest is higher-order champion x map structure, not side or calibration.

## 4. The F92 model (draft5-feat)

`model.mjs fit --lab replays/draftlab/draft5-feat` (w 320, the rest draft5's; counters ~2e-6, so no `--counters`).
The 67 new features in FEATURES order: monoliths, golems, camps_side, walls, shared_groups, one_altar, sq_ of all 25
base features, then 36 products pr_a__b (`draftfeat-tools/new67.json`).

- **Deployed team changes** (`model.mjs teams`, no lock as in draft5): **83 of 126 ladder maps** (66%; 3 picks 12/19,
  4 picks 21/26, 5 picks 50/81; 23 of the 32 one-altar maps) and **1,271 of 2,047 fresh ladder-mix maps** (62%; 334 of 477
  one-altar). Champion shares on the ladder: Cassi 92 to 84%, Willow 32 to 26%, Vendetta 30 to 26%, Ryth 30 to 35%,
  Ren 14 to 21%, Stellar 4 to 8%, Tavi 2 to 6%; Prism, Marcella, Heart of Ruin, Vesper about level.
- **`model.mjs gain`** (per-map team against the ladder prior's top 40, each model under its own posterior), ladder,
  3/4/5 picks: current 70.6 / 71.8 / 70.7%, F92 70.5 / 74.6 / 72.6%. Each model rates its own picks, so
  `cross.mjs` scores both models' teams under both models:

| Scored under | ladder 3 / 4 / 5 picks (new - old, points) | one-altar ladder maps | fresh 3 / 4 / 5 | one-altar fresh |
|---|---|---|---|---|
| F92 | +3.4 / +3.0 / +2.1 | +4.3 / +2.8 / +2.3 | +1.6 / +1.8 / +1.8 | +2.3 / +2.2 / +2.3 |
| draft5 | -2.0 / -2.8 / -1.4 | -2.0 / -1.8 / -1.6 | -1.6 / -2.0 / -1.8 | -2.1 / -2.4 / -2.4 |

F92 is the better fit by 53 (5/5 folds, on one-altar and ladder-mix weights alike), so its view should be the nearer.
These are predictions against the ladder prior in self-play of the lab's bot (`variants/ocean-base`, 3b3a57a0), not
ocean's current play: only an A/B says what the switch is worth.

## 5. Candidate bot: `bots/variants/oc-draftfeat` (not A/B'd; `test_draft` off)

`variants/oc-base4` (READY when copied) with the F92 `draft_model.h` (`model.mjs cpp --lab replays/draftlab/draft5-feat`)
and `map_features.{h,cc}` measuring the 67 new features: the raw five from compute()'s existing passes (walls counted in
the SIMD tile pass, shared groups in the groups loop, monoliths/golems/camps_side from its `types[]`), one_altar from the
altar count, and sq_/pr_ parsed from `names` at compile time; a derived feature asks for its components' want bits.

- **Parity** (`native.mjs --src bots/variants/oc-draftfeat/src/draft`): the 128 ladder maps and fresh df-991101 (384
  maps): 0 key, 0 team, 0 C++ failures; every base and raw feature and one_altar exact. 182 sq_/pr_ values differ by at
  most 2 ulp (3.8e-16 relative): libm against V8 `log` in the last bit, which README's exactness note already allows;
  before, logs were taken only inside `model_team`, so native.mjs never compared them. ocean's own source against draft5
  still matches exactly (128 maps).
- **First draft turn fuel** (`firstturn.py`, release, `--rounds 0`; start-up + model draft, of the 10M first turn):
  ladder 128 maps median 2.52M, max 5.88M (oc-base4 2.46M, 5.83M); 530 heavy and random draft5 pool maps median
  3.53M, max 6.88M (oc-base4 3.48M, 6.82M). No team-draft ran out; analysis unfinished after round 0 on 204 of 1,060
  (oc-base4 202). The 67 features cost ~55k.
- Tool changes (additive): `tools/draftlab/derived.mjs` (new), model.mjs FEATURES appended (92) and `raw()` computing
  derived values for old maps.jsonl rows, features.mjs `mapRow` writing them, native.mjs comparing a bot's names as a
  prefix of FEATURES (so 25-feature bots still check).

## 6. A/B: no gain (2026-11-06)

`bots/variants/oc-draftfeat2` = `variants/oc-retest-clean` (= bots/ocean, v78) with F92's `draft_model.h` and
`map_features.{h,cc}`; JS parity on the 128 ladder maps 0 team mismatches (2-ulp sq_/pr_ differences only); first draft
turn as in section 5 (ladder median 2.52M against 2.46M, max 5.88M; 530 heavy maps max 6.88M; none out of fuel).
Both on own drafts, fast runner, 2x fuel (`--fuel 200000`). Suites `df-e` (545000-545039), `df-c` (545100-545139,
unused), `df-v` (545200-545209, `--mix varied`); `/home/ubuntu/tmp-offload/draftfeat/` (`ab.sh`, `split.py`).

| Run | oc-draftfeat2 | 95% CI | one-altar maps | multi-altar maps |
|---|---|---|---|---|
| df-e, SPRT 0.50/0.51 (`--sprt-seed 5451`) | 49.4% of 4,927 | 48.0-50.8 | | H0 accepted (LLR -3.07) |
| df-e, all 20,480 | **49.9%** | 49.2-50.6 | 49.7% of 4,694 (48.5-51.0) | 50.0% of 15,786 |
| df-v (`--mix varied`), 5,120 | 50.6% | 49.3-52.0 | 51.3% of 694 | 50.5% |
| ladder 128, head-to-head, 256 | 49.6% | 43.5-55.7 | 51.6% of 64 | 49.0% |
| ladder 128 against astraeus-now-1106, 256 | 54.7% (oc-retest-clean 50.0%) | 48.6-60.7 | 48.4% (45.3%) | 56.8% (51.6%) |

Not run, since it did not win at 2x: the real budget, the df-c confirm, the panel and the draft6 plan.

**Why** (`realeval.mjs`: each model's prediction of these 20,480 games, side term included). On the 12,576 games
where the teams differ the candidate scored 49.9%; F92 predicted 53.7%, draft5 46.5%, and both are worse than a coin
there (log loss 0.6962 and 0.6996 against 0.6931); on one-altar maps F92 predicted 54.6% for 49.6%. Each model believes
its own best team beats the other's by ~3.5 points, and in ocean's games the two are level: choosing the argmax
inflates each model's own estimate (the optimizer's curse), and the lab's games are another bot's
(`variants/ocean-base`) than v78. F92 does predict the real games better overall (0.6950 against 0.6971), but a
better fit on random teams does not separate the near-best teams. The `gain` and cross-evaluation figures of section
4 are such self-assessed choices and overstate what a switch is worth.

## Conclusions

- One altar is special but small: -0.42 ±0.16 alone, -0.7 on top of the raw five; a few points per champion
  (Vendetta and Vesper worse; Prism, Heart of Ruin, Marcella and, at 5 picks, Tavi and Stellar better). In play its
  maps read 49.7% (48.5-51.0): nothing to change for it.
- The model is misspecified (GBM -74.5; F92 -53.4 ±0.35), but the better fit did not draft better: F92's teams are
  level with draft5's in ocean's games (49.9% of 20,480 at 2x fuel; 50.6% varied). Keep draft5 in ocean.
- A draft6 lab for these features alone is not worth its compute. If a lab is rerun anyway (ocean v78 as the player,
  ladder-mix pool), include F92's features (cheap: ~55k fuel) and judge it by head-to-head games between the
  candidate teams, since CV loss over random teams does not predict draft gains.
