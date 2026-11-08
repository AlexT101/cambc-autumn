# Context knobs: a knob as a function of the map and the game state (ocean = oc-base25, 2026-11-08)

The idea (user): instead of one static value per knob, X = f(map features, game state), or a gate that turns an arm on
only where a learned predicate says it helps. This note has the shared infrastructure, the data analysis for the
invade-deny weight and mid_gold, the policies it supports, and their tests.

## Infrastructure (`bots/variants/oc-ctx-dev`, deleted; on oc-base26 with g2's weights: `context-knobs-g2.patch`)

- `model/context.h`: `x = clamp(constant + sum_i w_i f_i, lo, hi)`; `ctx::knob<W>(constant, lo, hi[, state])` and
  `ctx::gate<W>(...)`. The constant is the knob's global value (the SPSA retune's), so the terms are offsets and compose
  with it. Weights are `constexpr`: all zero, a knob is its constant at compile time.
- Map features, set once in `condition_on_map` (draft.cc) from the draft's PlanFacts: indicators `one_site`,
  `short_spawn` (spawn walk <= 40), `long_spawn` (> 73), `multi_short`, `multi_long`, and standardised logs
  `z_area`, `z_spawn`, `z_gems`, `z_altars` (mean/SD over the ladder-mix suites used below).
- PlanFacts gains `sites` (4 bits: altar tiles within Chebyshev 3 merged, the live gate's one-site definition,
  `lock-tools/sites.mjs`); DraftPlan version 11 -> 12. Computed in the draft (`measure_facts`); champions read it,
  or measure it on their first turn only when the draft memory is missing (the existing facts fallback).
- State features (`score_gap` per 100 tributed, `round_frac`, `alive_gap`) are read only by a knob with a nonzero
  state weight (a callable, `if constexpr`).
- Knobs wired: `params::ctxk::mid_gold_w` (shop.cc prices, clamp 1.0-2.0) and the invade-deny weight
  `params::ctxk::deny_x0` + `deny_w` (farm.cc facts block, s2's B2 port, clamp 0-1).
- Tools: `~/tmp-offload/ctxknob/bin/` (`rows.py` per-game rows from ab runs, `feat.py` features, `tab.py` win% by
  feature bins, `transfer.py` fit on one dataset and test the fitted score on another, `fitx.py` the X = f(z) fit,
  `evalpol.py` policy values from played games, `panel.py` panel deltas paired by map and side).

## Data

Every source is an A/B of an arm against its base on the same maps (both sides), so map main effects cancel: any
dependence of the cand's win rate on a map feature is the arm's effect varying with the map.

| knob | runs | games |
|---|---|---|
| deny | s2 deny50 / deny25 vs oc-base25 on scr10k at 100k and 200k fuel | 4 x 20,000 |
| deny | audit-p3 oc-invade-d50 vs oc-base1 (2026-11-05) | 307,200 |
| mid_gold | gp-dec / gp-conf / gp-conf2 / gp-dev / gp-dev2: x1.25, x1.5, x2.0 vs 1.0 on oc-base23 | 409,600 |
| mid_gold | gp2-mirror: x1.5, x1.75 vs 1.25 on oc-base25 | 102,400 |
| mid_gold | gp2-panel: x1.5-td, x1.75-td and oc-base25-td vs astraeus-td, proteus-td, and arm-td vs oc-base25-td | 245,760 |

## mid_gold: a real context effect

Higher mid_gold wins on one-site maps and on short multi-site maps, and loses on longer multi-site ones, in every
source (win % of the arm vs its base; ± 95%):

| arm (vs), games | one-site (32%) | multi, walk <= 40 (22%) | multi 41-73 (22%) | multi > 73 (24%) |
|---|---|---|---|---|
| x1.25 (1.0), oc-base23, 225k | 50.52 ±0.37 | 50.41 ±0.43 | 50.52 ±0.44 | 49.86 ±0.43 |
| x1.5 (1.0), oc-base23, 194k | 50.65 ±0.39 | 50.21 ±0.47 | 50.22 ±0.47 | 49.05 ±0.46 |
| x2.0 (1.0), oc-base23, 20k | 50.90 ±1.21 | 50.46 ±1.46 | 49.44 ±1.47 | 48.58 ±1.40 |
| x1.5 (1.25), oc-base25 mirror, 51k | 50.96 ±0.77 | 50.28 ±0.92 | 49.41 ±0.92 | 49.07 ±0.89 |
| x1.75 (1.25), oc-base25 mirror, 51k | 50.64 ±0.77 | 51.12 ±0.92 | 49.36 ±0.92 | 48.55 ±0.89 |
| x1.5-td panel delta (pts) | +0.37 ±0.65 | +0.30 ±0.78 | -0.09 ±0.84 | -0.81 ±0.82 |
| x1.75-td panel delta (pts) | +0.84 ±0.68 | +0.53 ±0.81 | -0.65 ±0.87 | -0.78 ±0.85 |

- **Transfer:** a ridge fit of the x1.5-vs-1.0 games (b23) on 13 map features predicts the x1.5-vs-1.25 games (b25,
  other maps) with slope +1.19 ±0.37 (z 3.2); the x1.25 fit predicts both b25 arms with +1.02 ±0.35 (z 2.9). A slope
  near 1 on unseen maps and another base means the context effect is real, not fitted noise.
- **Panel too:** the same split holds against astraeus-td and proteus-td, so unlike v84's min_bank (CHANGES 461/462,
  mirror only) this is not a self-play artefact.
- That is why the static grid was level: x1.5/x1.75 gain on half the maps and lose on the other half.

Mechanism. mid_gold raises gold's price in farm choice in the mid game: we take gold groups and buy shards sooner.
On one site, banking means holding the one altar, so fights at it decide the game and shard power wins them; short
walks bring fights early on any map. Live scrims point the same way: on one-site maps our losses are more lopsided in
gold (our/opp median 0.47, against 0.72 on multi-site maps), our median gold trails the opponents' (3,559 vs 3,886;
level on multi-site maps), and we win only 40% of one-site games past round 1200 (61% on multi-site maps). On long
multi-site maps the race is gem throughput across several altars, and gold weight costs gems.

## Invade deny: weak context effect, no map-class split

- No one-site/multi-site split: old d50 multi 50.14 / one 49.96; new d50 49.59 / 49.07; d25 50.30 / 50.26.
- Spawn walk: deny loses where spawns are close, in both independent sources:

| arm | walk <= 39 | 39-73 | > 73 |
|---|---|---|---|
| d50 on oc-base1, 307k | 49.50 ±0.31 | 50.45 ±0.31 | 50.30 ±0.31 |
| d50 on oc-base25, 40k | 49.19 ±0.85 | 48.94 ±0.85 | 50.14 ±0.85 |
| d25 on oc-base25, 40k | 49.83 ±0.85 | 50.53 ±0.85 | 50.52 ±0.85 |

- Transfer is weaker: the old fit predicts the new games with slope +0.31 ±0.24, and the new fit predicts the old
  games with +0.30 ±0.12. So the true effect is about a third of what was fitted.
- Mechanism: close spawns put their half's groups beside their spawn, where they heal and respawn at once and come
  out quickly, while our own groups are left for them to take back. With distant spawns their half is far from their
  heal, so taking it costs them gems at little risk.

## Policies and predictions (written before the games)

Valued split-half (map hash) on played games against static 1.25:
- one-site or multi-short at 1.75: gp2-mirror +0.33 / +0.58 per half (+0.45 ±0.27 overall).
- one-site only at 1.75: +0.16 / +0.24.
- The ridge X = f(z) fits were unstable between halves and no better on the held-out half, so the hand structure
  (fitted cells) goes forward.

| arm | policy | games changed | prediction |
|---|---|---|---|
| `oc-ctx-g2` | mid_gold + 0.5 (1.25 -> 1.75) on one-site maps and multi-site maps with a walk <= 40 | ~52% of maps | mirror +0.25 (+0.1 to +0.45): one-site +0.5-0.8, multi-short +0.3-0.6, others exactly 0; panel +0.2-0.4 pooled |
| `oc-ctx-d1` | deny 0.25 where the walk is over 40, else 0 | ~66% of maps | mirror +0.15 (0 to +0.35), no one/multi difference |

State dependence (behind means more risk) is not measurable from these A/Bs: they hold only the outcome per game.
ocean's comeback already raises denial when behind (deny_scale), and mid_gold is already a hump on the score. The
state terms are in the infrastructure, at zero.

## Results

Own drafts, real budget, fast runner; screen `merged/ctx-scr-1060` (+ resume suites after the 09:50 disk-full crash),
held out `ctx-held-1061`, varied `ctx-varied-1062`, panel `ctx-panel-1063` (seeds 1060000-1063059, `--mix ladder`).
SPRT seeds 10601/10602 (screen), 11601 (held out), 12601 (varied), 13601 (panel).

**d1 (deny by spawn walk): dropped.** Screen ran out its suite at 102,400 games, 50.04% (pair CI 49.79-50.29), LLR
-1.36, undecided; no split (one-site 50.00, multi 50.06). At best +0.25, and the transfer slope (0.3) said it would
not hold. Global deny25/deny50 belong to s2.

**g2 (mid_gold 1.75 on one-site and short multi-site maps): screen H1, held out flat: dropped.** Screen on oc-base25;
the rest on oc-base26 with only g2's diff (`oc-ctx-g2-26`).

| Test | Result |
|---|---|
| Screen (oc-base25) | 50.34% (50.08-50.60) of 72,130 games; H1 (LLR 2.96) |
| Held out (oc-base26) | 50.12% (49.78-50.47) of 81,920 games; undecided, suite exhausted (LLR -0.01) |
| Varied | 50.01% (49.04-50.98) of 10,240; undecided (LLR +0.29 at 0.4975,0.50) |
| Panel, pooled (astraeus-td, proteus-td) | +0.63 pts (astraeus +0.87 ±0.46, proteus +0.59 ±0.41); H1 at 0.50,0.5025 (LLR 8.55) |
| td mirror (panel suite) | 50.43% (49.87-50.99) of 30,720 |

Split by cell (win %, ±1.96 se), against the predictions:

| Cell (share of held-out games) | Screen | Held out | td mirror | Predicted |
|---|---|---|---|---|
| one-site, walk <= 40 (12%) | 51.29 ±1.03 | 50.91 ±0.98 | 51.50 ±1.57 | |
| one-site, walk > 40 (20%) | 50.43 ±0.82 | 50.04 ±0.78 | 51.12 ±1.27 | |
| one-site, all (32%) | 50.77 ±0.64 | 50.38 ±0.61 | 51.27 ±0.99 | +0.5-0.8 |
| multi, walk <= 40 (22%) | 50.33 ±0.77 | 50.19 ±0.73 | 50.40 ±1.17 | +0.3-0.6 |
| multi, walk > 40 (46%, unchanged) | 50.04 ±0.54 | 49.92 ±0.50 | 49.84 ±0.83 | 0 |

The context effect is real and points where the fits said (one-site, short walks), and the panel likes it more than
the mirror (the opposite of v84's mirror flattery). But the all-maps size is diluted: the held out's changed cells
average about +0.3, which is +0.16 on all maps; pooled with the td mirror and varied, +0.19 (about ±0.28) on oc-base26.
That is below the +0.25 bar, and deciding it would take ~300k more games for a likely marginal H1. No narrower cell
clears the bar either: one-site with a short walk, the strongest (+0.9 to +1.5), is 12% of games, a ceiling near +0.15.
The one-site gain matches Mite's one-site strength, so it may be worth folding into a larger one-site package. g2
would compose with a global mid_gold change (it is mid_gold + 0.5, clamped to 2.0). The live gate (`live-ctx-g2-26`) was
already prepared by the scheduler, so it stays queued; a clear live gain would reopen it.
