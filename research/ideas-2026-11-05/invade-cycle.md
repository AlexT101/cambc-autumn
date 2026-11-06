# Mirror pull, third pass: a learned cycle-constraint gate (ocean, 2026-11-05)

The user's hypothesis: sunburst has many camps but few high-value ones, so it is cycle-constrained. Once the team has
cleared its high-value groups, it waits out their respawn on low-value camps, and the mirror pull spends that slack
on the enemy's high-value groups. The user wants the gate learned, not guessed.

Earlier passes are in EXPERIMENTS "Mirror pull" and "Mirror pull, second pass", and in invade.md. The pull is +9-10
on sunburst families and -1 to -2 on fresh ladder-mix suites. The second pass's map model failed because its labels
were noise: 8 games a map, reliability 0.11.

## Plan

1. **Rebase.** `bots/variants/oc-mp-dev` is oc-base3 (= bots/ocean) plus oc-late-dev's knobs (`params::late`; the
   patch applied cleanly). With the knobs off, bench.py at 100M replays 16/16 (default) and 52/52 (wide)
   byte-identical to oc-base3. Fuel +0.03% / +0.02%: the pull's locals. `oc-mp-u1` is c = 1.
2. **Labels.**
   - A *family* is a base map plus mild mutations: 1-2 of walls/bushes/holes +-1-2, with picks unchanged
     (`mkfam.py`; mutation seeds 527000000+ for the pilot and 527100000+ for the full pool).
   - A game's label is c = 1's win minus oc-base3's on the same map, side and opponent. Base against oc-base3 is
     self-play, so it counts 0.5.
   - Opponents: oc-base3, astraeus-now-1105, panel-proteus and oc-inv2-crew, both sides. A family member is 8
     games, and a family's label is the mean over its members.
   - Reliability is estimated by split-half over members, with Spearman-Brown.
3. **Pool.** It reuses sungrad (10 arms), sunfam2, sunlike and the 128 ladder maps, and adds fresh ladder-mix seeds
   527000-527009 and `--mix varied` seeds 527100-527104 (made in scratch; only the maps used moved to
   `maps/suites/mp3/`).
4. **Features** (`feat.mjs`) come from the map alone, with groups as the bot's StaticMap holds them:
   - worth = gems + gold / 5; health and strength from the camp table;
   - walks in king steps, with walls, holes, altars and the enemy spawn blocking.

   They fall into three sets:
   - **The older set** (mapfeat2): size, densities, home walks, worth by side, reach, rates and tortuosity.
   - **Cycle-constraint**, at high-value floors 20 and 30 gem-eq:
     - camp and high-value counts and shares;
     - high- and low-value output per period, a period being respawn + whole-team clear + hold;
     - body demand: body-rounds of damage and hold per period, over the bodies;
     - the nearest-neighbour high-value tour against the mean respawn;
     - slack;
     - the best yield per body-round on our low-value camps, our high-value groups and theirs (from ours);
     - the distance from our high-value groups to theirs, against our home walk;
     - their worth share in high-value groups near ours.
   - **A two-team farm simulation**, `picks` bodies a side and no fights, over 300 and 800 rounds: idle and walk
     shares, the share of rounds with our high-value groups all down, and the income change when side A scores
     walks with the pull.
5. **Model.** Ridge, logistic (on the label's sign) and a depth-2 GBM, under grouped 5-fold CV repeated over 5
   random fold assignments.
   - Groups: every sunburst-derived map is one group, SUN. A ladder map and its mutations in the ladder mix share a
     group. Every other map is its own group.
   - Leave-SUN-out is reported as well.
   - The metrics are held-out r and the mean label of the top-k fraction by held-out prediction, with CIs from a
     group bootstrap.
6. **Gate and A/B.** These run only if a held-out positive subset exists.

## Results

### Label reliability (pilot: 200 families x 16 members x 8 games = 128 games a family)

The pilot families are 50 sungrad maps (5 per arm), 50 ladder maps, 70 fresh ladder-mix maps (527000) and 30 varied
maps (527100). Its 44,590 games ran at about 170k games/h. The split-half is by member, with Spearman-Brown to the
full label:

| Families | 16 games | 32 | 64 | 128 |
|---|---|---|---|---|
| all 199 | 0.31 | 0.49 | **0.68** | 0.80 |
| without SUN (149) | 0.32 | 0.46 | 0.62 | 0.77 |
| SUN only (50) | 0.40 | 0.58 | 0.78 | 0.87 |
| fresh + varied (100) | 0.38 | 0.52 | 0.68 | 0.80 |

The per-game reliability is about 0.03, against about 0.014 in the second pass's sunlike pool: this pool has real
spread. Family means have an sd of 9-12 points; at 128 games the noise sd is about 6. By class: fresh -0.9, ladder
-1.0, sun +3.1, varied +2.1. So the full pool runs at **64 games a family** (8 members), reliability about 0.65.

Two caveats.
- **Map by opponent.** Within one opponent, a family's 32-game label has a split-half reliability of 0.65-0.76. The
  correlation of the same family's labels between two opponents is only 0.03-0.23 (mean 0.12). Most of the
  reliable variation is therefore map x opponent, not map. The part shared across opponents, which is what a map
  gate can use, has an sd of about 7 points.
- **Pseudo-replication.** Mild mutations replay m0's game, same winner and round count, for about 24% of members.
  So the split-half overstates independence a little.

Held-out CV on new families is the arbiter either way.

### Full pool: 1,336 families

The full pool is the pilot plus 1,138 families at 8 members (64 games): 140 sungrad (12 per arm), 20 sunfam2, 120
sunlike, the other 78 ladder maps, 600 fresh ladder-mix maps (527000-527009) and 200 varied maps (527100-527104).
That is 127,330 games at about 140k/h, shared. At 64 games a family the reliability is 0.73 (0.72 without SUN).

c = 1 minus off, by class, in points:

| Class | Families | Mean |
|---|---|---|
| fresh | 670 | -2.30 |
| ladder | 126 | -1.77 |
| sun (sungrad, sunfam2) | 190 | +0.69 |
| sunlike | 120 | -1.28 |
| varied | 230 | -1.92 |

On the full pool alone, by opponent: oc-base3 -2.2, astraeus-now -2.2, proteus -3.2, crew -0.5. The 04sunburst
family itself reads 0.0 over 128 games. The +9.8 of the first pass was against oc-combo2 and a six-opponent set.
Ladder families range from +27 (01fracture, 00lost-world, 00great-wall, 03honeycomb, 04dunes) to -39 (03the-front,
04mesas, 03one-gem, 03ultrastarvation, 00ambush).

**Univariate.** Spearman over all families, fresh+ladder in brackets:
- The strongest are the cross distances: how far the enemy's copy of each of our worthy groups is (Chebyshev,
  worth-weighted, `cw_cross_cheb`): -0.17 (-0.23). The pull pays where their groups are near ours.
- Then symmetry (rotational worse) -0.13 and the distance from our high-value groups to theirs -0.12.
- Then the best high-value yield +0.12, reach of their worth +0.11, altars -0.11 and spawn gap -0.10.
- **The cycle-constraint features are weak.** Body demand, slack, tour against respawn, low-value count per
  high-value group and their dependence on high-value groups near ours are all under 0.07. So are the simulation's
  high-value-down share and pull delta.

**Held-out models.** Grouped 5-fold CV over 980 groups, 5 repeats. Each cell is the mean label of the top k% by
held-out prediction, with a 95% group-bootstrap CI:

| Model | Set | r | top 5% | top 10% | top 20% | top 30% | top 50% |
|---|---|---|---|---|---|---|---|
| ridge (109 features, alpha 300) | all | +0.13 [0.07, 0.18] | +0.3 | -1.2 | -1.3 | -0.3 | -0.4 |
| | fresh | +0.15 | -1.4 | -2.4 | -1.2 | -0.6 | -0.8 |
| logistic (on the sign) | all | +0.17 [0.11, 0.23] | -1.4 | +1.0 | +1.0 | +0.4 | +0.2 |
| | fresh | +0.20 | -0.4 | +1.9 | +1.0 | +0.2 | -0.2 |
| ridge on 6 features chosen in-fold | all | +0.17 | -1.9 | -0.1 | +0.2 | +0.4 | +0.1 |
| | fresh | +0.22 | -1.7 | +0.2 | +0.7 | +0.3 | +0.6 |
| **GBM** (depth 2, 150 trees) | all | **+0.21 [0.15, 0.27]** | +0.0 | -0.0 | +1.2 [-0.5, 2.5] | +1.2 [-0.2, 2.2] | +0.5 |
| | fresh | +0.24 [0.17, 0.32] | +0.9 | +1.4 | **+1.8 [-0.2, 3.5]** | +0.8 | -0.3 |
| | ladder | +0.19 | -4.8 | -3.1 | -1.6 | -1.2 | -0.1 |
| | fresh+ladder | +0.24 | +0.2 | +0.4 | +1.2 [-0.7, 2.9] | +0.6 | -0.4 |
| | leave-SUN-out, on SUN | +0.16 [0.03, 0.29] | +4.2 | +1.7 | +3.2 | +2.2 | +1.3 |
| GBM, 300 trees | fresh | +0.24 | +0.7 | +1.3 | +1.0 | +0.7 | +0.0 |
| GBM on 26 hand-picked features | fresh | +0.22 | +1.8 | +1.7 | +0.6 | +0.4 | -0.1 |

The prediction is real: held-out r is 0.2-0.24 with CIs well above 0, and the rank holds out of the sunburst family
(leave-SUN-out r +0.16). It mostly finds the losing tail, though. The best selected subsets are +1 to +2 points with
CIs that reach 0, they move with the model settings, and on ladder maps every top-k is negative. Gating the best
fifth would make the bot about +0.2 to +0.4 points better than off overall, below what a 20,480-game A/B resolves
(about ±0.7).

The GBM's most important features are ch_/cw_cross_cheb, hv30_yield, hv_e_yield, hv_yield, sim800_walk, walls and
bushes.

### Pre-registered subset test on unused seeds: fails

The final GBM was fit on all 1,336 families. It scored the 10,240 fresh ladder-mix maps of seeds 527500-527539 and
picked the top 20%: 2,048 maps (threshold +0.82, mean prediction +1.78). It also picks 37 of the 128 ladder maps,
04sunburst among them at +1.2. The selected maps are in `maps/suites/mp3/sel-ab`. Each map played c = 1 and off
against the four opponents, both sides: 28,672 games.

| Selected maps | Predicted | Observed c = 1 minus off |
|---|---|---|
| all 2,048 (top 20%) | +1.78 | **+0.75 [-0.29, +1.72]** |
| top 2% of the suite (205) | +3.57 | +0.24 ± 3.35 |
| top 5% (512) | +2.92 | -0.22 ± 2.04 |
| top 5-10% (512) | +1.85 | +0.51 ± 1.91 |
| top 10-20% (1,024) | +1.17 | +1.35 ± 1.42 |

By opponent: oc-base3 +0.4, astraeus-now +1.3, proteus -0.5, crew +1.8. Within the selected maps the prediction does
not rank the label (r -0.02): the maps it rates highest do no better.

A gate at this threshold would leave the pull on for a fifth of maps at about +0.75. That is about +0.15 points
overall against off, and not significant. A 20,480-game A/B (about ±0.7) cannot resolve it, so the keep bar (a
20k win) cannot be met. **No gate was built into the bot and no A/B was run.** variants/oc-mp was not frozen.

## Verdict

- The labels are now reliable (0.73 at 64 games), and map features do predict the pull's per-family effect out of
  sample (r 0.2-0.24).
- What they predict is mostly where the pull loses. Its losses are large where the enemy's copies of our groups are
  far (cross distance), on rotational maps, on large maps and with many altars.
- They do not find a subset where it wins: held-out top-k is +1 to +2 with CIs reaching 0, and on unused seeds it is
  +0.75 with no dose-response.
- The user's cycle-constraint hypothesis did not show up as signal. Every high-value count, share, demand, slack,
  tour-against-respawn and dependence feature, and the farm simulation's bottleneck share, has |Spearman| under
  0.07. The useful features are geometric: how near their copy of our groups is, and the yield of high-value groups.
- Most of the label's reliable variation is map x opponent (between-opponent correlation 0.12), which a map gate
  cannot use.

## Files

- Bots:
  - `bots/variants/oc-mp-dev`: oc-base3 plus `params::late`, knobs off, bench-identical.
  - `bots/variants/oc-mp-u1`: c = 1.
- Maps: `maps/suites/mp3/` (SUITES.md).
- Scripts (session scratchpad `mp3/tools/`):
  - `mkfam.py`: families;
  - `runlab.sh`: label games, all under one slot group;
  - `labels.py`: labels and reliability;
  - `feat.mjs`: features;
  - `fit.py`: CV models;
  - `select.py`: the final GBM and the subset.
