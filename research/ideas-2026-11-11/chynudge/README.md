# Per-opponent draft nudges on charybdis (chy-draft18), 2026-11-11

Question (user): "so have we tried nudging more? and what is the best version now? ... consider a/b against
charybdis with our changes in". Is there a draft nudge, for Fish and for Mite separately, that makes `chy-draft18`
better against that opponent?

Answer: **no.** No nudge reaches 50.5 against its own opponent's body, none is established above 50, and every
stronger nudge loses. Nothing ships; no candidate was frozen.

## What this morning covered on ocean, and what it did not

([draftnudge/README.md](../draftnudge/README.md), ocean 506, both bodies.)

- **Covered.** One kind of nudge: ocean's champion values plus lam x the log-odds that Fish (or Mite) *itself holds*
  the champion, flat or conditional on the map. Strengths that change 15, 30 and 50% of maps' teams ("light" = 15%,
  "strong" = 50%), and the far end: drafting their likeliest team (99% of maps), never Prism, never Willow. Each arm
  was read against both bodies, so the per-opponent numbers exist: against the Fish body every Fish-direction arm
  read +0.20 to +0.28 (±0.20 to ±0.37) at all three strengths; against the Mite body every arm read -0.01 to -0.65.
- **Not covered.** (1) Any direction made from *outcomes* against that opponent, rather than from the opponent's
  own picks. (2) Strengths between 50% and the full copy (bracketed by -0.2 and -17, so not open). (3) charybdis,
  whose draft values Prism more. (4) 100k fuel, live games.

## What was tested here

Twelve arms, each `chy-draft18` with only `draft_model.h` changed (`nudge.py`):

- **TF, TM: this morning's direction on charybdis.** The flat log-odds that Fish / Mite holds the champion, at a
  light strength (17-19% of maps change) and a strong one (56-57%).
- **RF, RM: a direction fitted from outcomes** (`load.py`, `fit.py`, `cv2.py`). draft18's lab holds 299,907 games
  of charybdis against the Fish body and 299,520 against the Mite body, with varied teams on both sides. On each
  body's games, with draft18's own logit as a fixed offset, a ridge logistic fits what our team is worth *beyond the
  model*: a term per champion and per champion x the first 25 map features. No new lab games and no refit of the
  model itself. Strength 1 is the fitted size (32% of maps change), then 2 (54%) and 4 (77-80%).
- **RB: the same fit on the Fish and Mite games together**, which a draft could use without knowing the opponent;
  strengths 1 and 2, against both bodies.

The fitted residual is real in the lab's games and mostly opponent-specific (held-out log loss change in 1e-4, five
map folds, penalty 4096):

| games of | fitted on the same body | fitted on the other two bots | fitted on all three |
|---|---:|---:|---:|
| Fish body | -30.8 | -3.5 | -20.0 |
| Mite body | -21.0 | -6.6 | -16.4 |
| ocean 506 | -13.7 | +15.3 | +0.9 |

The Fish and Mite map weights correlate 0.24. Flat champion offsets against Fish: Prism -0.08, Cassi & Issac -0.04,
Ren / Heart of Ruin / Vendetta +0.03 (logit); against Mite: Heart of Ruin +0.06. A champion term alone is worth
-2.2 (Fish) and -0.4 (Mite); our champion x their champion adds -3.6 and -2.0; a per-pick-count term adds nothing.

**Games.** 200k fuel (standing rule: screen at 200k; the lab's games were at 100k), release, fast runner, `ab.py`
against fgate's run-time bodies `rt-Flp4` / `rt-Mt3q` (unmetered, a noise seed per map), both sides, on 12,269 fresh
ladder-v2 maps (mapgen seeds 7111100-7111147, this morning's held-out set; not in the fgate pool, whose seeds are
2417000-2417383, and never played by charybdis). The user's trick: an arm plays only the maps where its team differs
from chy-draft18's, against the opponent it is meant for, and chy-draft18's games on the same maps and noise are the
counterfactual. Where two arms draft the same team on a map the game is played once. 129,628 games, no errors, early
losses or capped drafts. Checks: 1,792 games on maps with an unchanged team had the same winner and length as
chy-draft18's (128 an arm and opponent); 3,552 kept replays drafted the planned team.

## Results against chy-draft18

chy-draft18 wins 85.7% against the Fish body and 80.0% against the Mite body on the maps it played (the union of the
changed maps, 89% and 85% of all). "Overall" is the change over all maps against that opponent (changed cells x
share; unchanged cells are exactly 0), as a win rate.

| nudge | opponent | cells changed | changed cells, points (95% CI) | maps (games each bot) | overall win% (95% CI) |
|---|---|---:|---|---:|---|
| RF x1 (fitted against Fish) | Fish | 31.7% | +0.67 (-0.40 to +1.73) | 3,894 (7,788) | 50.21 (49.87-50.55) |
| RF x2 | Fish | 54.1% | -0.47 (-1.29 to +0.34) | 6,641 (13,282) | 49.74 (49.30-50.18) |
| RF x4 | Fish | 79.7% | -2.59 (-3.28 to -1.89) | 9,782 (19,564) | 47.94 (47.38-48.49) |
| RB x1 (fitted against both) | Fish | 29.3% | +0.92 (-0.16 to +2.00) | 3,600 (7,200) | 50.27 (49.95-50.59) |
| RB x2 | Fish | 50.3% | +0.07 (-0.76 to +0.90) | 6,176 (12,352) | 50.04 (49.62-50.45) |
| TF light (toward Fish's picks) | Fish | 16.6% | +0.69 (-0.70 to +2.07) | 2,037 (4,074) | 50.11 (49.88-50.34) |
| TF strong | Fish | 56.4% | -0.25 (-1.00 to +0.50) | 6,918 (13,836) | 49.86 (49.44-50.28) |
| RM x1 (fitted against Mite) | Mite | 32.3% | -0.03 (-1.15 to +1.10) | 3,959 (7,918) | 49.99 (49.63-50.36) |
| RM x2 | Mite | 53.5% | -0.64 (-1.52 to +0.24) | 6,566 (13,132) | 49.66 (49.19-50.13) |
| RM x4 | Mite | 76.6% | -1.68 (-2.43 to -0.93) | 9,404 (18,808) | 48.71 (48.13-49.29) |
| RB x1 | Mite | 29.3% | -0.10 (-1.28 to +1.08) | 3,600 (7,200) | 49.97 (49.62-50.32) |
| RB x2 | Mite | 50.3% | -0.40 (-1.31 to +0.50) | 6,176 (12,352) | 49.80 (49.34-50.25) |
| TM light (toward Mite's picks) | Mite | 18.7% | -1.54 (-3.01 to -0.08) | 2,299 (4,598) | 49.71 (49.44-49.98) |
| TM strong | Mite | 57.0% | -1.09 (-1.92 to -0.25) | 6,998 (13,996) | 49.38 (48.90-49.86) |

**Verdict: nothing clears the bar; chy-draft18's draft stays.** Against Fish the three light nudges read +0.1 to
+0.3 with intervals that include 50 (the same size and sign as this morning on ocean); against Mite every arm is
level or negative; nudging more loses, steadily, in every direction.

## Why

- **The fit's own ceiling is under the bar.** On the cells RF x1 and RM x1 change, the fitted model itself claims
  +0.049 logit a cell, in sample: about +0.6 points a cell against Fish and +0.8 against Mite at these win rates,
  so +0.2 to +0.25 overall even if every bit of it is real. The residual is real but spread over near-ties: where a
  different team is clearly better, draft18 already picks it.
- **The stronger arms confirm the fit, not a gain.** For x2 and x4 draft18 alone predicts -1.4 to -3.7 points a
  changed cell and the fitted model 0 to -1.8; measured -0.5 to -2.6. The residual is right that these swaps cost
  less than draft18 says, and they still cost.
- **The games differ from the fit's.** The lab's bodies played ladder and random teams, compiled and metered; the
  gate's bodies play Fish's and Mite's own drafts, unmetered. The residual averages over the first.

## Limits

- 200k fuel only; no 100k run (none earned), no fgate, no held-out repeat (the 6,133 maps of seeds 7111000-23 are
  unused by charybdis), no ladder-map side read, no live games.
- The bodies under-punish fights (fishfight, livedraft READMEs): the +0.03 for Ren, Heart of Ruin and Vendetta
  against the Fish body may be flattered. No arm depends on it.
- A per-opponent draft would also need the opponent at draft time. From the ladder's pick orders (11-09 on, 2,238
  drafts), telling Fish from Mite by their first two picks is right 76% of the time, by four picks 89% / 66%
  (no map conditioning); our last pick could be held until then. Not built, since no arm wins.
- Not tried: our champion x their champion terms folded in against each team's expected draft (worth a tenth of the
  map terms in the lab's games), all 92 features, directions from live games.

## Files

`load.py` (lab games + the model's logit), `fit.py` / `cv2.py` (residual fits and their cross-validation),
`nudge.py` (directions, strengths, nudged link lab), `run.py` (build / play / read), `fidelity.py`.
Data: `~/tmp-offload/chynudge/` (`work/directions.json`, `work/read-main.json`, `work/stages/main.json`,
`results/` per-game outcomes, `labs/` nudged models). Arm bots: `bots/variants/cn-*` (gitignored; safe to delete).
No patch and no frozen candidate: an arm is `node tools/draftlab/model.mjs cpp --lab ~/tmp-offload/chynudge/labs/<arm>`.
