# Draft17 preference protocol

The user authorized using recent Fish/Mite draft data to test a nudge toward their choices, plus a separate **overall pick-rate** ablation. The coordinator approved the fixed design below before training or evaluation outcomes existed. This document's filename is historical; it now describes the concrete amendment. Queue release still requires the sealed implementation's independent review.

## Evidence and limits

The frozen ranked-game window is **2026-11-08 22:51:42 through 2026-11-10 22:51:42 UTC**, end exclusive. Selected daily archive columns were copied from big-arm and analysed locally. No database load, numpy analysis, game execution or build ran on big-arm.

| Team | Drafts | Maps | Observed map/side cells | Repeats per cell | Cells with different compositions |
|---|---:|---:|---:|---:|---:|
| Fish | 710 | 128 | 237 | 1–8 | 0 |
| Mite | 731 | 128 | 246 | 1–7 | 32 |

Recent archive coverage is restricted: November 8 has 479,108 archived games, November 9 has 2,992, and the November 10 snapshot has 2,936. These are capture-sample counts, not the full ladder population. Both teams nevertheless cover all 128 ladder maps. The archive exposes engine label `3.0.0`, not the local executable's `5.0.1`, and contains no bot revision IDs. Mite's within-cell variation could reflect responses to opponents, revisions, or other conditions; these columns cannot diagnose which. Neither team's samples establish equivalence to r2/r5 or the latest live bot.

Each row preserves match ID, team/opponent ID, UTC time, map name/hash, side, ordered picks, engine and source day. Deduplication keys are match/side; conflicting duplicates fail. Cassi & Issac is one draft slot even though it creates two units. Every composition has 3–5 unique contiguous slots. All 128 archive map hashes were verified against the local map bytes before joining existing feature rows. Source columns and extracted inputs have recorded SHA256 hashes.

A useful diagnostic is Fish's Willow inclusion: approximately **93% at five picks, zero at three or four**. The flat ablation deliberately discards this conditioning. This is a behavior observation, not evidence that forcing Willow improves Ocean. Preserve separate team raw counts, overall balanced rates and pick-count breakdowns; do not select a champion ban or force a pick from them.

## Outcome-free preference estimation

Keep the one 800k game collection, historical opponent composition prior, sampler, bodies and training seeds unchanged. This intervention alters **our own pick preference**, not the modeled opponent distribution.

Weight Fish and Mite equally. Within each team, weight each map equally, each observed side equally, and repeat observations of that cell equally. Scale total effective weight to twice the smaller team's map count, here 256 team/map units. Do not silently take only the latest observation or let frequently captured cells dominate. The full frozen window is used without a recency hyperparameter.

The flat direction is one champion inclusion vector pooled over **all pick counts**. Smooth each weighted inclusion with Jeffreys half-success/half-failure, `(weighted_count + .5)/(256 + 1)`, then take finite log-odds. Use precisely the same vector for all three draft sizes, with zero map coefficients.

The conditional direction adds three pick-count intercept offsets and shared slopes on the first 25 F92 features to the flat logits. Fit independent weighted binomial regressions for each champion, penalizing all offsets/slopes by `ridge/2 * squared_norm`. Choose ridge from the fixed set **16, 64, 256** using five map-grouped archive folds (`FNV1a(map_hash) mod 5`), minimizing weighted inclusion log-loss. Recompute the flat prior and weights using only training maps in each archive fold. Rounded ties at 12 decimal places choose stronger regularization. The archive targets contain picks, not game outcomes.

Fit these directions in the final refit's own standardized, clipped F92 coordinates. Missing feature values map to zero exactly as in the existing model. Verify the first 25 feature names against the unchanged F25 configuration. This avoids an inexact conversion between feature normalizations at export. The training-pool mean/standard deviation are outcome-free and common, rather than fold-local.

Center champion coefficients columnwise, which removes only a constant shared by all compositions of the same size. Normalize each direction so the RMS score contrast between two independent uniformly sampled p-champion compositions, averaged over the training maps and their pick counts, is one. Compute this analytically: contrast variance is `2*p*(12-p)/11` times the population variance of the 12 champion scores. No games or outcomes enter normalization.

## Genuine out-of-map scalar calibration

Run five F92 fits using the existing map-key folds. Every side, opponent and repeat of a map stays in its fold. A fold fit sees only the other four folds and uses **fixed sealed draft10 penalties and soft-target weight**, with no whole-data fitted warm start or globally outcome-selected hyperparameters. The unchanged final F92 control still performs its original one-pass penalty search. Thus the calibration predictor and final control can differ in penalties; this transfer mismatch is explicit and is tested by independent selection/confirmation, rather than hidden through fold leakage.

For each of the two fixed directions, fit **one nonnegative scalar lambda**. The target is the actual game win, even if the fixed predictor's fitting target mixes a wealth margin. The signed score perturbation includes only Ocean/self-controlled sides: plus our team on A, minus our team on B, both for Ocean mirror, neither for an opponent-controlled side. Opponent champion values remain fixed during calibration.

Minimize the sum, over training maps, of mean held-out logistic loss plus `lambda²/2`. Thus duplicating games within a map cannot change regularization. Solve the convex one-dimensional derivative directly: return zero when the derivative at zero is nonnegative, otherwise bracket and bisect. There is no grid of behavior strengths and no candidate-gate outcome in this fit.

Add the calibrated direction only to F92 champion intercepts and the first 25 map coefficients. Leave synergy, counters, other features and draft machinery unchanged. Zero lambda aliases control; identical exported headers share one candidate/run. Native key/team parity and the 10M first-turn checks are mandatory before games. Five extra fits add no additional collection games.

## Fixed selection and independent confirmation

[README.md](README.md) gives exact seeds, replacements, noise blocks and resource bounds. Selection uses 1,024 fresh maps, noise blocks 1–64 and 200k fuel: at most 131,072 fresh games for the three approaches plus frozen 506. It makes two one-sided comparisons to control, with Bonferroni family alpha .05 (`z=1.96`). Retain control unless a nudge's lower bound is positive; choose the largest eligible mean, with flat winning an exact tie.

The frozen selection then receives independent 200k confirmation on another 1,024 maps and noise blocks 65–192: at most 196,608 fresh games for selected/control/506. Require positive lower bounds against 506 and against control if a nudge was selected. Control alone retains conservative z=1.96. Report opponent and pick-count breakdowns descriptively; do not choose a new variant from them.

Within each map, average all noise realizations, both sides and both opponents before estimating uncertainty. Use map-level sample SD (`ddof=1`), not noise-repeat sample size. There are no interim decisions. The 128 ladder maps are diagnostic only and are played once for all distinct arms at 200k; confirmation reuses those deterministic cells.

A separate coordinator decision is required after a positive 200k confirmation before any 100k run. It binds the selected source and uses the original untouched 2412900–03 panel (with reserved replacements), noise blocks 193–320. Selection games are never counted in either confirmation. No automatic merge, live test, repin or new training round follows. Tune8 remains behind draft17's completed review.

Sealed inputs are under `~/tmp-offload/localq/rounds/draft17/inputs/preferences/`; the original local extraction and archive-column hashes are under `~/tmp-offload/draft17-preference-study/`.
