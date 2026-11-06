# Map-conditioned constants: diagnostic and design (ocean, 2026-11-05)

The idea: constants as functions of map features known at draft time, θ(map) = θ0 + Σ_j W_j z_j(map), trained by
SPSA. Nobody had tried it. This note asks whether the existing data shows a prize, using no new games.

**Verdict.** The prize is not shown, and the SPSA logs could not show one either way. The two large held-out A/B sets
show no map dependence worth having: the gain from tuning differs in size between maps, never in sign, and most of
that difference is the same one every unrelated A/B shows. Don't run a contextual SPSA yet. First make `tune.py` log
per-game scores (a 10-line patch, below, to apply once oc4 ends); one oc-sized run with that log is enough to make the
decision. A design for the contextual tune follows, for use if that decision says go.

Scripts: `research/ideas-2026-11-05/mapcond-tools/` (`run.sh` reruns everything in about 5 minutes with 2 BLAS
threads and plays no games). The data went to the session scratchpad (`MAPCOND_DIR`).

## 1. Data availability

| | oc2 | oc3 |
|---|---|---|
| run | `replays/tune/oc2`, 61 constants, 1,288 iterations | `replays/tune/oc3`, 67 constants, 1,381 iterations |
| an iteration | 64 maps x 3 opponents, 4 sign pairs (8 candidates), 192 games per candidate | 64 maps x 5 opponents, 320 games per candidate |
| pool | the 128 ladder maps | ladder x8 (1,024 entries) + fresh-517000..517019 (5,120) |
| per-game scores | **not kept** | **not kept** |
| per-iteration | each candidate's mean score and win rate, and x after the update (`history.jsonl`) | same |

- **Per-game results are gone.** `Batch.finish` deletes `work/itK` unless `TUNE_KEEP` is set, and `history.jsonl`
  keeps only the per-candidate means. The docstring says "each iteration's scored games in games/", but the code never
  writes them.
- **Everything else is recoverable exactly.** `plan()` seeds its RNG with `seed * 1000003 + k` and draws the sign
  vectors, then the maps (`rng.sample` over the sorted pool), then the sides, all before x is used. Replaying it
  (`recon.py`) and recomputing every update x_{k+1} = clip(x_k + a_k ĝ) from the logged means matches
  `history.jsonl` to 1e-16 on all 78,507 (oc2) and 92,460 (oc3) coordinates. So the Δ vectors, c_k (ints use
  max(c_k, 1/(hi-lo))), maps and sides are certain, provided the pool is unchanged. It is: no pool map is newer than
  its run's `config.json`, and neither config was edited mid-run. Each map is matched to its opponents through the
  `opps` order.
- What we have is therefore 4 paired score differences per iteration, each over 192 or 320 games, together with the
  iteration's 64 maps.
- **A second source with per-game results:** the held-out A/Bs of the two tunes (`replays/batch-*/results.json`:
  map, order, winner), 20,480 to 40,960 games per comparison on maps the tuner never used. These only test the one
  direction each tune moved, but they test it map by map.

Features, all knowable at draft time, come from mapgen's `metrics()`: `index.json` for fresh suites, and
`mapgen.mjs check --json` for the ladder (one ladder map, adgato-gemcombat5, fails validation and goes through
`met1.mjs`). They are standardised: log area, picks, rotational symmetry (vs mirror), spawn walk distance, camp
density, log gems per side, big_share (the Monolith and Golem share of a side's gems), contested share and altar
count. Buckets: terciles, picks 3/4/5, the three symmetries, altars 1/2/3+, big_share 0/low/high.

## 2. Gradient heterogeneity in the SPSA logs (iteration level)

Model (`spsa_het.py`), fitted jointly by OLS on all pairs:
diff_kp = Σ_i Δ_kpi · 2c_ki · (g_i[epoch] + Σ_j W_ij · z̄_kj) + ε. Here g_i is the gradient in scaled x, with 4
epochs to absorb drift; W_ij is its change per SD of feature j; z̄_k is the iteration's mean feature vector. That makes
549 (oc2) and 603 (oc3) interaction terms. The null comes from 500 permutations of z̄ across iterations.

| | oc2 | oc3 |
|---|---|---|
| SD of an iteration's mean feature (per-map SD 1) | 0.086-0.091 | 0.121-0.129 |
| SE of a main gradient g (per epoch) / of an interaction W | 0.020 / **0.142** | 0.015 / **0.069** |
| RMS of the main gradients, debiased | 0.007-0.012 | 0.000-0.005 |
| interactions with \|t\| > 2: observed (null mean, null 95%) | 26 (25.4, 36) | 32 (27.9, 38) |
| \|t\| > 3 | 2 (1.5, 4) | 3 (1.7, 4) |
| largest \|t\| (null 95%) | 3.07 (3.87) | 3.67 (3.92) |
| omnibus Σt² (null mean, null 95%), permutation p | 574 (552, 629), 0.31 | 644 (606, 685), 0.19 |

Nothing stands out from chance. The top pairs (oc2: `siege_pool_share` x spawn_dist, t 3.1; oc3: `gold_farmer_weight`
x picks, t 3.7, and `mid_exposure` x picks, t 3.3) are what 550-600 tests produce under the null.

**It is a power failure, not a negative.** Every iteration draws 64 maps from the same pool, so iteration means
barely vary (SD 0.09 of a map's), and an interaction is 7-14 times harder to see than a main gradient. The SE of W
(0.07-0.14) is ten times the size of the main gradients themselves. Per-bucket gradients cannot be formed at all,
because no iteration is all small maps or all 3-pick maps. The prize bound these logs give (section 4) is vacuous.

## 3. Map dependence of the two tuned directions (held-out A/Bs, per game)

`ab_het.py` regresses each map's mean result (cand win - 0.5, or a paired difference against a common opponent) on the
9 standardised features, with HC0 SEs (one map = 2 games). It gives a joint Wald test, and its null is 500 shuffles of
features across maps.

| comparison (games) | mean effect | joint Wald χ²(9), perm. p | largest slopes, points per SD (SE) |
|---|---|---|---|
| oc2: oc-tuned vs oc-base1, oct-a (20,480) | +3.16 | 45.5, **0.002** | log_gems -1.9 (0.5), spawn_dist -1.5 (0.5), camp_density +1.3 (0.6), big_share +1.3 (0.5), sym_rot -0.8 (0.4) |
| oc2: (tuned - base1) vs astraeus and proteus, oct-b (40,960) | +2.57 | 21.8, **0.018** | log_gems -1.1 (0.5), sym_rot -1.0 (0.3), big_share +1.0 (0.4), altars -0.8 (0.3) |
| oc2 mid-run vs oc-base1, oct-c (10,240) | +2.18 | 14.9, 0.10 | |
| oc3: oc-tuned3 vs oc-combo2, oc3-confirm (20,480) | +0.57 | 13.9, 0.12 | |
| same, oc3-confirm2 (20,480) | +0.01 | 4.5, 0.88 | |
| same, `--mix varied` (5,120) | +0.12 | 9.4, 0.45 | |
| oc3: (tuned3 - combo2) vs 5 panel bots, pchk + p2 (35,840) | +0.74 | 9.7, 0.43 | |

- **oc2's gain does depend on the map.** It replicates on independent maps and opponents: the slope vectors of oct-a
  and oct-b correlate +0.89, and their difference is χ²(9) 9.3. **It never changes sign.** In every bucket of every
  feature it is +1.5 to +4.7 (oct-a) and +1.6 to +3.7 (oct-b). It is smallest on rotational maps (+2.4 / +1.7
  against +4.7 / +3.4 on horizontal), on maps with 3+ altars and on maps with many camps.
- **Most of that dependence is generic.** The same regression on 11 unrelated A/Bs (`ab_control.py`; the 8 large
  ones are oct-base1 vs astraeus and vs proteus, ocean-d5, v2-conf, v2-conf2, oc3-vs-astr, oc3-vs-panel-astraeus and
  oc4-ast), with slopes divided by each one's mean effect, pools to a common profile. Every edge shows less on
  high-gem maps (-0.41 per SD), long-spawn maps (-0.31) and many-altar maps (-0.16), and more on maps with a high
  big_share (+0.33). oc2's normalised profile correlates **+0.89 (oct-a) and +0.75 (oct-b)** with it. What remains is
  χ²(9) 16.7 and 12.6, before allowing for the controls' own spread (they disagree with each other at χ² 10-41 on
  10 df). The only consistent residual is rotational symmetry (z -2.0, -2.6), which falls to about -1.5 once that
  spread is counted.
- **oc3's direction shows nothing**, and its slope vectors on the two confirm suites correlate only +0.40.

**Cross-validated choice per map.** A rule is fitted on one A/B and scored on an independent one. It plays the tuned
vector on a map only when the training A/B's linear model, or its best one-feature bucket rule, predicts a gain there.

| train -> test | policy minus always-tuned |
|---|---|
| oc2 oct-a -> oct-b (linear / bucket) | +0.05 ± 0.05 / 0.00 (all maps tuned) |
| oc2 oct-b -> oct-a | +0.05 ± 0.04 / 0.00 |
| oc3 confirm -> confirm2 | +0.09 ± 0.14 / +0.10 ± 0.14 |
| oc3 confirm2 -> confirm | +0.01 ± 0.18 / 0.00 ± 0.14 |
| oc3 confirm -> panel (pchk + p2) | -0.06 ± 0.08 / -0.10 ± 0.08 |

## 4. The prize

- **Choosing between the vectors we have, per map: about 0.** The cross-validated rules above are worth +0.05 points
  or less.
- **Conditioning oc2's step length on the map: at most about 0.3 points.** Take a quadratic along the direction,
  with t = 1 (shipped) at the pooled optimum: then f_z(t) = a_z t - h t²/2, h = 2ē, and the extra gain from t_z is
  Var(e_z)/(4ē). The debiased SD across maps of the predicted effect is 1.8 points (oct-a) and 0.7 (oct-b), which
  gives **0.26 and 0.05 points**. Most of that variance is the generic sensitivity above, and a per-map step cannot
  harvest it: if a map just makes every edge smaller, its optimum along the direction does not move.
- **A full contextual tune: these logs can't bound it.** The quadratic model takes h from oc2's own progress: score
  +0.062 over |Δx|² 0.67, so h ≈ 0.19 per scaled unit², with 0.60 win per unit of score. On that model the debiased
  Σ W² of the iteration fits is 0.45 ± 1.09 (oc2) and 0.07 ± 0.30 (oc3), and the 95% upper bounds come to 370 and 77
  points, which is meaningless. A single interaction at its SE would already be worth 3.3 points (oc2) or 0.7 (oc3).
  So the open question is directions the global tune never moved, where the gradient flips sign between kinds of map
  and averages to about zero. Neither data source can see those.
- **What per-game logs would buy.** If each game's paired difference is attributed to its own map, z varies with SD 1
  instead of 0.09-0.12. SE(W) then falls to roughly the full-run SE of a main gradient: **about 0.010 (oc2-sized run)
  or 0.0075 (oc3-sized)**, 14 and 9 times tighter. That detects |W| ≥ 0.04 / 0.03 at a Bonferroni level over 600 tests
  (each worth about 0.25 points by the same model), and pins the omnibus prize to about ±0.5 points (1 SE). One run
  answers the question.

## 5. Recommendation and design

### Stage 0: log per-game scores in tune.py (applied 2026-11-06, after oc4 ended, with the names list added)

In `cmd_run`, after `names = list(cfg["params"])` (the plan's `ck` is the per-name `cn` dict):

```python
        rec_g = {"k": k + 1, "deltas": [[d[n] for n in names] for d in deltas], "cn": [ck[n] for n in names],
                 "games": [[str(Path(m).relative_to(ROOT)), o, s] for m, o, s in batch.games],
                 "scores": {c: [None] * len(batch.games) for c in res}}
        for c, r in res.items():
            for sc, _, gi in r:
                rec_g["scores"][c][gi] = round(sc, 5)
        with (run / "games.jsonl").open("a") as f:
            f.write(json.dumps(rec_g) + "\n")
```

This takes about 40 KB an iteration (about 55 MB for an oc3-sized run) and plays no extra games. Logging `deltas`
and `cn` also keeps the analysis valid if `config.json` is edited mid-run, which would otherwise break the
reconstruction. Fix the docstring's "games/" to match.

### Stage 1: the decision, from the next run's games.jsonl

There are two ways to get the run:
- piggyback on the next SPSA run (oc5 or later); or
- a fixed-θ gradient probe: `a = 0` at ocean's current values, 1.5-2M games, about 5 h. It is cleaner, because
  gradients don't drift.

Fit the per-game version of `spsa_het.py`: d_g = s_p,g - s_m,g on Δ ⊗ [1, z_g], with the map, not the game, as the
cluster, and a permutation null over maps. Go to Stage 2 only if all three hold:
1. the omnibus Σt² is beyond the permutation 99th percentile;
2. pairs beyond Bonferroni (|t| > 3.9) appear and keep their sign in both halves of the run;
3. the debiased prize Σ_i W_iᵀ Σ_z W_i · 0.6 / (2h) is at least 1 point.

### Stage 2: contextual SPSA (only if Stage 1 passes)

- **What to condition.** Only the (constant, feature) pairs Stage 1 keeps: expect a handful of constants and at most
  4 features. Everything else stays global. Features must be computed identically in Python and in the bot, so use
  exact map counts: log(W·H), picks (as a number, or 3/4/5 dummies for a per-bucket form), rotational symmetry, the
  Chebyshev spawn-centre gap, camps per side, log gems per side, big_share and altar count. Avoid mapgen's walk
  metrics (spawn_dist, contested) unless the bot's own distance field reproduces them.
- **Parameterisation.** Linear in standardised z, in natural units, clipped to the constant's range:
  θ_i(z) = clamp(θ0_i + Σ_j B_ij · clamp((z_j - μ_j)/σ_j, ±2.5), lo_i, hi_i). Ints are rounded after. μ and σ are
  fixed in `config.json` from the pool. Clamping z keeps `--mix varied` maps from extrapolating. A per-bucket form is
  the same thing with dummy features.
- **Training needs no extra games.** Candidates are θ(z) ± cΔ, with Δ perturbing θ0 only. Since ∂f/∂B_ij =
  z_j ∂f/∂θ_i, each game's paired difference updates both: ĝ_θ0,i = mean d_g/(2c_iΔ_i) and ĝ_B,ij = mean
  d_g z_gj/(2c_iΔ_i). An iteration therefore costs what it costs now. Use θ0 at the current shipped values, B = 0 at
  the start, a_B = a/2 with ridge shrinkage B ← (1 - λa_k)B (most interactions are null), and θ0 either frozen or on
  its usual gain.
- **tune.py changes.**
  - Compute z per pool map once (a node script with the bot's exact definitions, cached in `run/z.json`) and carry it
    in `games`.
  - Write B (nf+ni) x J, μ, σ, lo and hi into the patched block alongside θ0.
  - Keep the per-game attribution above in the update.
  - Have `status` and `apply` print and emit B.
  - patch.py needs only the bigger block (same magic, new layout version).
- **Bot changes (tunified copy).** tunify.py points params at a second global, `diana_eff.f/i`, instead of
  `diana_tune`. The champion's first turn fills it from `diana_tune` and z, once, before anything reads a tuned
  constant: compute z from SDK map queries ahead of `StaticMap::build` if `build` uses tuned constants. Champions and
  the draft bot are separate instances, so every champion computes z itself. That is O(groups) plus 67·J
  multiply-adds, a few thousand fuel against the first turn's 200k, with no fuel gate.
- **Budget.** Resolving B to SE ≈ 0.01 takes about 2M games, an oc2-sized run of about 6 h on this box. Then a
  held-out A/B against the global constants: 40,960 games (the expected gain is ≤ 1 point, so it needs a ±0.5 CI),
  plus 5,120 games on `--mix varied` and the panel check.
- **Port.**
  - `apply` writes θ0 and B as exact-float32 `constexpr` arrays plus μ and σ in `params.h`.
  - The conditioned constants become `inline float` globals set by an `init_map_constants()` call on the first turn;
    the rest stay `constexpr`.
  - Cost: global loads instead of immediates for those constants, at most the 0.16-0.31% fuel measured between the
    patched block and constexpr in the oc2/oc3 ports.
  - Sanity check: at B = 0 the port must replay identically to the global bot.

## Files

- `mapcond-tools/recon.py`: rebuilds Δ, c_k, maps and sides per iteration from `plan()`'s seed and verifies them
  against the x updates.
- `feats.py` and `met1.mjs`: the feature table.
- `spsa_het.py`: the iteration-level interaction fit and its permutation null.
- `ab_het.py`, `ab_buckets.py` and `ab_control.py`: per-map regressions, bucket tables, cross-validated policies and
  the unrelated-A/B controls.
- `prize.py`: the quadratic prize estimates.
- `run.sh`: all of the above.
