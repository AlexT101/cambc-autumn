# Camp-group features for the draft and the context knobs (ocean = oc-base25, 2026-11-08; no arm)

A teammate proposed three features:
1. the number of camp groups holding gem clusters, and "exactly one gem-cluster group";
2. the same for gold clusters;
3. a "high-value compact cluster": one big group, a ball rather than a line, that can be watched whole from one tile,
   and is quick to kill for its reward (no Monolith or Golem).

**Result: no arm.**
- Over draft7's F92 model (ocean's draft), the best feature improves map-grouped CV log loss by 0.7 (1e-4). F92's own
  gain over the 25 features was 38.
- Cross-fitted, it changes ocean's team on 9-15% of maps, for +0.02 to +0.03 win-% points. The SPRT H1 bar is +0.25.
- No feature carries a usable per-map signal for mid_gold or invade deny.
- mapgen over-represents gem-only balls: 49% of ladder-mix maps have one, against 28% of the ladder's.

Tools are in `campfeat-tools/`, large files in `/home/ubuntu/tmp-offload/campfeat/`.

## Definitions (`campfeat-tools/campfeat.mjs`)

Counts are per side: team A's groups (mapgen `sideGroups`) plus shared ones.

| feature | definition |
|---|---|
| `gem_groups`, `gold_groups` | groups with at least one gem (gold) cluster (log1p) |
| `one_gem_group`, `one_gold_group` | that count is exactly 1 |
| light compact group | no Golem or Monolith, and one ground tile sees every member tile (symmetric shadowcast, radius 8; walls and bushes opaque) |
| `hv_rate` | best light compact group with value >= 10 by value / ((HP + 1000) / 1000); value = gems + gold/10; the 1000 HP stands for the walk and the 6-round hold |
| `hv_compact` | a light compact group of 3+ members with value >= 40 and `hv_rate` >= 12 |
| `hv_val`, `hv_share` | the best light compact group's value (log1p), and its share of the side's total value |

Compactness rarely binds: 98.5% of ladder groups can be watched whole from one tile. The exceptions are the line maps
(00the-line, 04lines, 01yellow-brick-road, 02gift-wrapping). So the third feature is mostly "a light group worth a lot
per kill time".

## Draft model

Data: draft7's lab (999,979 games, 25,257 maps). Penalties are F92's (w 320, dev 1024, b 64, syn 320).

**Screen (`screen.py`).** F92's fitted logits are a fixed offset. On top of them, champion x new-feature weights are
fitted per pick count, shrunk toward a pooled fit, with the same 5 map-grouped folds as model.mjs. The SE is paired by
map. Differences are in CV log loss (1e-4); negative is better.

| set | over F92 | over F25 (control) |
|---|---|---|
| all 8 | -0.35 ± 0.46 | **-6.77 ± 0.76** |
| counts (1+2) | +0.62 ± 0.30 | -4.14 ± 0.61 |
| gem pair / gold pair | +0.26 / +0.39 | |
| hv4 (all of 3) | -0.56 ± 0.34 | |
| `hv_compact` | **-0.67 ± 0.22** | -1.89 ± 0.33 |
| `hv_rate` | **-0.70 ± 0.24** | -1.92 ± 0.38 |
| `hv_val` / `hv_share` | +0.30 / +0.35 | |
| `gem_groups` / `one_gem_group` | +0.07 / +0.04 | |
| `gold_groups` / `one_gold_group` | +0.42 / -0.02 | |
| control: F92's monoliths, golems, camps_side, walls, shared_groups, one_altar | | -5.81 ± 0.62 |

- Over the 25-feature model, the screen finds the features (-6.8). Over F92 they add nothing: F92 already holds that
  information. As a linear and quadratic fit, F92's base features explain R² 0.83 of `gem_groups` and 0.86 of
  `gold_groups`, but only 0.2-0.35 of the booleans and `hv_compact`.
- Only `hv_compact` and `hv_rate` are about 3 SE better, and only by 0.7.
- **Caveat:** the offset is F92 fitted in-sample, not a full refit. The F25 control shows the screen has power. A full
  refit at 1-2 CPU slots would take about 8 h, and the value step below caps what it could find.

**Picks and value (`select.py`, through the counter agent's pysim port of oc-base25's draft).**
- `bases` reproduces `counter2/sim/base25.txt` to 6 digits.
- New weights are fitted on each map half (`hash(key#half)`). Each map's team is chosen with F92 plus the other
  half's weights, and valued with F92 plus its own half's, against F92's own team. Values are 25 x logit, in win-%
  points.

| set | teams changed | cross value | in-sample ("self") | 126 ladder maps |
|---|---|---|---|---|
| `hv_compact` | 11.8% | +0.019 ± 0.001 | +0.047 | +0.018 |
| `hv_rate` | 9.4% | +0.021 ± 0.002 | +0.052 | +0.016 |
| `hv_compact` + `hv_rate` | 14.9% | **+0.026 ± 0.002** | +0.085 | +0.011 |
| hv4 | 17.9% | +0.003 | +0.124 | +0.022 |
| counts | 10.7% | -0.053 | +0.076 | -0.098 |
| all 8 | 21.9% | -0.030 | +0.216 | -0.006 |

The best is a tenth of the +0.25 bar, so no candidate or A/B was built. The in-sample column is the optimiser's
curse again: up to 8x the cross-fitted value.

## Context knobs (`knobs.py`, read-only on `ctxknob/ana/*.pkl`)

- **Data:** the knob agent's A/B rows, on 90,960 maps: every oc-base25-era map, plus 4,000 sampled from each older run.
- **Model:** per source, a logistic fit of the arm's win on z(feature), with label x cell intercepts (one-site;
  multi-site walk <= 40 / 40-73 / > 73). A slope is signal beyond the agent's cells. Slopes are in win-% points per SD.

| feature | mid_gold b23 | mid_gold b25 mirror | mid_gold b25 panel | deny old | deny b25 |
|---|---|---|---|---|---|
| `gem_groups` | -0.16 ± 0.14 | -0.32 ± 0.16 | +0.10 ± 0.27 | -0.03 ± 0.57 | -0.22 ± 0.18 |
| `one_gold_group` | -0.30 ± 0.14 | +0.11 ± 0.16 | -0.11 ± 0.26 | -1.36 ± 0.57 | +0.25 ± 0.18 |
| `hv_rate` | +0.00 ± 0.14 | -0.22 ± 0.16 | -0.13 ± 0.26 | -0.03 ± 0.56 | +0.11 ± 0.18 |
| `hv_val` | -0.12 ± 0.14 | -0.29 ± 0.16 | -0.14 ± 0.26 | -0.11 ± 0.56 | -0.05 ± 0.18 |
| the other four | \|z\| <= 1.5 | | | | |

- None is consistent across sources: 3 of the 40 tests reach |z| >= 2, about what chance gives.
- At most there is a weak `gem_groups` lean for mid_gold: -0.2 to -0.3 per SD in the mirror sources, but not in the
  panel. It is small next to the one-site/short cells (±0.5 to 1 point). No knob term is worth fitting.

## mapgen against the ladder

The 128 maps in `maps/` are the archive's 128, byte for byte. The archive's names use `_` where the files use `-`, so
none are missing. (counterpick.md's "88 on disk" is a name mismatch.)

| feature | ladder (128) | mapgen ladder mix (25,131 of fresh-5900xx) | test |
|---|---|---|---|
| gem / gold groups per side (mean) | 5.87 / 5.95 | 5.62 / 5.67 | KS p 0.94 / 0.72 |
| `one_gem_group` / `one_gold_group` | 8.6% / 3.1% | 5.8% / 3.9% | binomial p 0.18 / 0.82 |
| `hv_compact` | 30.5% | 38.5% | p 0.07 |
| `hv_rate` median (mean) | 12.0 (13.3) | 15.4 (16.3) | KS p < 0.001 |
| `hv_share` median | 0.16 | 0.19 | p 0.03 |
| maps with a gem-only group of 3+ | **28%** | **51%** | p ~ 1e-7 |
| gem-only groups of 3+ per side | 0.66 | 1.04 | |
| pure-gem groups that are single clusters | 58% | 37% | |

- The counts match. The mismatch is the gem-cluster-only ball, which drives `hv_rate`.
- **Sources** (`tools/mapgen/generate.mjs`):
  - `LADDER_GROUPS`' gem-only make-ups of 3+ cells (`ggg`, `gggg`, `ggggg`, `gggggg`, `big:gems`) in the `ladder`
    preset: 56-60% of its maps have a ball;
  - the `classic` preset's `TEMPLATES.gems` / `elk_gems` blobs: 68%.
  - Mutations of ladder maps match (29%).
  - The ladder's balls also cluster on a few gem-only maps (72% of ladder maps have none). Independent make-up
    draws spread them over more maps.
- **Proposal (not applied).** A `GEM_BALL` factor on those weights, tested in a copy (`mgfix/`, seeds
  1080000-1080007, 2,048 maps each):

| | ladder | mapgen now | GEM_BALL 0.5 |
|---|---|---|---|
| maps with a gem ball | 28% | 49% | 41% |
| balls per side | 0.66 | 0.98 | 0.78 |
| `hv_rate` median | 12.0 | 15.4 | 13.4 |
| gem groups / gems per side | 5.87 / 267 | 5.60 / 253 | 5.55 / 250 |

  It closes about half the gap in the `ladder` preset, from 56% to 43% of its maps. `classic` (61%) needs its
  `gems` template's 3- and 4-cell blobs cut too.
- None of these features matters for the draft or the knobs, so the fix is low priority. It is worth doing only if
  someone builds gem-ball-specific behaviour (splash or area play on clusters), which mapgen suites would over-weight
  by about 1.8x.
