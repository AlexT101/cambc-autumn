# Draft lab against live drafts: does v87's draft (F92) pick badly against Fish and Mite? (2026-11-08)

**Answer: no. F92 already ranks our teams correctly against Fish's and Mite's real picks, so no arm was built.**
Base `variants/oc-base25` (v87). Tools in [draftlive-tools/](draftlive-tools/); big files in `~/tmp-offload/draftlive/`.

## The opponents' drafts don't react to ours

In big-arm's archive (`react.py`, `react2.py`), Fish on 11-07 played the same team on all 226 of its map-sides
over 617 games, against every opponent. Mite's few changes on 11-07 track its version changes during the day,
not its opponents' picks. So both pick a fixed team per (map, side), and spar's forced live drafts stay right when our
draft changes. Our draft is F92's best team in champion id order (no team lock in oc-base25: `required` and
`banned` are 0). `score.mjs` reproduces all 512 live cells.

## Lab L1

- **Setup** (`dlive.py`): 80 teams per ladder map, as draft-lab vehicles built from oc-base25:
  - vehicle 0 = F92's best (the base);
  - vehicles 1-39 = F92's next best;
  - vehicles 40-79 = random teams.
- **Opponent:** spar-oc29-F/M (Fish's and Mite's live picks per map and side), both sides, 128 maps.
- **Size:** 40,960 games plus 512 controls (plain oc-base25), fast runner, debug builds, real budget.
- **Checks:**
  - every game drafted its table;
  - the opponents' picks equal the live ones in all games;
  - vehicle 0 replays the plain bot game for game (512/512).

The base wins **68.8%** against spar-oc29, which is spar's calibrated level.

| question | result |
|---|---|
| F92 score's within-cell slope (logistic, cell fixed effects) | **1.09-1.11** (1 = as calibrated as on its own lab) |
| win-points per F92 logit, linear, by subgroup | all 20.4, Fish 20.0, Mite 20.9, 3/4/5 picks 19.7/18.9/21.1, one altar 19.9, multi 20.7 (each ±0.3-0.8) |
| F92's best team minus F92's ranks 2-40, realized | **+10.1 ±2.4** pts |
| random teams | 30% wins against 57% for the top 40 |
| CV log loss (8 map folds) over the F92 score alone, champion mains | -8.6e-4 (Willow +0.17, Vesper +0.12 … Ryth -0.09, Prism -0.10 logit) |
| + counters against the live picks | +2 to +8e-4 (worse than mains alone) |
| + champion × 8 map features | +27 to +40e-4 (worse) |
| cross-fitted choice from the corrected models: realized gain over the base team | -1.4 to +2.1 ±2.9 pts across six models; none clear of noise |

- **No systematic mis-pick.** F92's ranking is equally sharp against Fish and Mite, for every pick count and on
  one-altar and multi-altar maps. Corrections that the cross-validation would keep are only champion offsets of
  ≤ 0.17 logit.
- **The positive selection rows are the optimizer's curse.** They come from the counter models, which lose in CV.
- **Can't be gated anyway.**
  - A per-ladder-map table would change nothing on fresh suites or the panel, so it can't reach the 99% local bar.
  - The general corrections have no CV support, and their predicted value (≤ 0.17 logit on a few champions) is far
    below what spar resolves (±3).
- **Archive cross-check** (`arch.py`, other teams' games against Fish and Mite, team-day and (opponent, map) fixed
  effects): Prism +0.66 and Marcella -0.79 against the average champion. Other teams' bodies drive this; for
  our body against the spar, Prism reads -0.10 and Marcella -0.05.
- **What it rules out:** v87's live losses to Fish and Mite are not its draft's choice among our teams. That agrees
  with spar.md: the remaining gap is behaviour (carry gold allocation, fights), not picks.
- **L2** (the same lists against spar-o29gs) was stopped at 208 games, as unneeded.
