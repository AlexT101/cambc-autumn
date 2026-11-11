# Fish/Mite draft nudge on ocean 506 (2026-11-11)

Question (user): does nudging ocean's draft toward what Fish or Mite pick make it stronger; map-conditional, and as
an ablation the flat pick rate. Answer: **no, for either team**. Light nudges are level, strong ones lose, and
drafting like them loses 15-17 points with our bot.

## Pick rates (% of teams holding the champion, all pick counts, the 128 ladder maps; Fish/Mite ranked games 11-09..11)

| | ocean 506 | Fish | Mite | other top 10 |
|---|---:|---:|---:|---:|
| Prism | 75 | 6 | 22 | 27 |
| Willow | 64 | 60 (5 picks only: 94) | 23 | 24 |
| Ryth | 24 | 0 | 0 | 35 |
| Ren / Varg | 16 / 13 | 3 / 1 | 0 / 0 | 10 / 29 |
| Vesper Vale | 68 | 44 | 76 | 69 |
| Cassi & Issac | 94 | 99 | 100 | 68 |
| Marcella | 21 | 64 | 23 | 54 |
| Tavi | 12 | 0 | 71 | 6 |
| Vendetta | 25 | 79 | 42 | 42 |
| Heart of Ruin | 30 | 91 | 89 | 83 |

Fish's draft is a fixed function of the map (250 map/side cells, one comp each, unchanged since 11-06). Mite's
moved (modal comp changed on 106 of 254 cells between 11-06..08 and 11-09..11; it now takes Willow on 35% of 5-pick maps).
By pick count: `picture.py`.

## Method

- **Directions** (`nudge.py fit`): per team, the log-odds that it holds each champion. `f` flat: one number per
  champion over all maps and pick counts. `c` conditional: ridge logistic on pick count and the model's first 25 map
  features (held-out champion overlap of its likeliest team: Fish 93%, Mite 87%; pick count alone 89%, 80%).
- **Arms**: draft10's champion values plus lam x direction, lam set so 15 / 30 / 50% of fresh maps change team.
  Each arm is oc-dfuel-506 with only `draft_model.h` changed (`bots/variants/dn-<arm>`); C++/JS teams match on 512
  maps, and 5,880 sampled replays drafted the planned team.
- **Games**: 200k fuel, release, fast runner, plain `ab.py` batches (up to 24.5k games) against the fixed compiled bodies
  `spar-dvn{1,2,3}-Flp4` / `-Mt3q`, both sides, on 18,385 fresh ladder-v2 maps (seeds 7111000-23 screen, 7111100-47
  held out). An arm plays only the maps where its team differs from the base's; the base's games on the same maps
  are the counterfactual. Checked: on 444 games with an unchanged team, winner and rounds were identical.
  416,904 games, no errors, capped drafts or early losses.

## Results against oc-dfuel-506 (18,385 fresh maps; base 78.7% against the bodies: Fish 81.1, Mite 76.4)

Win% is 50 + the arm's change over all maps (unchanged maps count as 0); CI over maps.

| arm | maps changed | paired games | win% (95% CI) | vs Fish body | vs Mite body | held-out maps only |
|---|---:|---:|---|---:|---:|---|
| Fish flat 15 | 14.8% | 10,920 | 50.07 (49.92-50.22) | +0.23 ±0.20 | -0.09 ±0.22 | 50.06 (49.87-50.24) |
| Fish flat 30 | 29.9% | 21,964 | 50.01 (49.79-50.23) | +0.22 ±0.29 | -0.20 ±0.32 | 49.99 (49.72-50.25) |
| Fish flat 50 | 50.3% | 36,984 | 49.91 (49.63-50.19) | +0.28 ±0.37 | -0.46 ±0.41 | 49.84 (49.50-50.17) |
| Fish cond 15 | 14.6% | 10,764 | 50.09 (49.93-50.24) | +0.27 ±0.20 | -0.10 ±0.22 | 50.03 (49.85-50.22) |
| Fish cond 30 | 29.7% | 21,828 | 49.97 (49.75-50.19) | +0.24 ±0.29 | -0.30 ±0.32 | 49.92 (49.66-50.19) |
| Fish cond 50 | 49.8% | 36,628 | 49.80 (49.52-50.08) | +0.20 ±0.37 | -0.60 ±0.41 | 49.65 (49.30-49.99) |
| Mite flat 15 | 15.3% | 11,252 | 50.06 (49.91-50.21) | +0.20 ±0.20 | -0.08 ±0.23 | 50.14 (49.96-50.33) |
| Mite flat 30 | 30.0% | 22,036 | 49.94 (49.73-50.16) | +0.13 ±0.28 | -0.24 ±0.32 | 50.03 (49.77-50.29) |
| Mite flat 50 | 49.9% | 36,692 | 49.82 (49.54-50.10) | +0.08 ±0.37 | -0.44 ±0.41 | 49.78 (49.44-50.12) |
| Mite cond 15 | 15.3% | 11,276 | 50.11 (49.96-50.27) | +0.24 ±0.20 | -0.01 ±0.23 | 50.19 (50.00-50.38) |
| Mite cond 30 | 29.9% | 21,992 | 49.94 (49.73-50.15) | +0.21 ±0.28 | -0.33 ±0.31 | 49.97 (49.71-50.23) |
| Mite cond 50 | 50.2% | 36,928 | 49.73 (49.45-50.01) | +0.11 ±0.37 | -0.65 ±0.41 | 49.70 (49.36-50.04) |

Larger moves, screen maps only (6,133 maps; the copies on 1,024):

| arm | maps changed | paired games | win% (95% CI) | vs Fish body | vs Mite body |
|---|---:|---:|---|---:|---:|
| draft Fish's likeliest team | 98.8% | 4,048 | 32.6 (30.6-34.6) | -15.0 ±2.7 | -19.7 ±2.8 |
| draft Mite's likeliest team | 99.2% | 4,064 | 34.6 (32.7-36.6) | -13.3 ±2.6 | -17.4 ±2.7 |
| never Prism | 79.5% | 19,492 | 41.3 (40.6-42.1) | -7.2 ±0.9 | -10.1 ±1.0 |
| never Willow | 61.0% | 14,956 | 46.5 (45.9-47.0) | -4.0 ±0.8 | -3.2 ±0.8 |
| never Prism or Willow | 86.3% | 21,164 | 38.4 (37.6-39.1) | -10.8 ±1.0 | -12.5 ±1.1 |

**Verdict: neither nudge ships.** No arm's interval reaches 50.5; the 15% arms sit at +0.06 to +0.11 with intervals
that include 50, and every 50% arm is below 50. No 100k run (rule: only for a 200k gain) and no frozen candidate.

## What the games say

- **Why a light nudge is free and a strong one is not.** Up to ~30% of maps, the nudge replaces our marginal pick
  (Ryth, Ren, Varg, Tavi out; Heart of Ruin, Marcella, Vendetta, Tavi in). The model prices those swaps at -2.2
  points on the changed maps; measured -0.8 ±0.5 on the held-out maps. Its ranking among near-top teams is mostly
  noise, so their preference is a harmless tie-break, not a better one. Prism and Willow stay (Prism 79% -> 76% at the 50% arms).
- **Prism and Willow are not over-picked for this bot.** Banning Prism costs 8.7 points, Willow 3.6, and their
  whole drafts 15-17 (the model predicted 22-25). The gap to other teams' pick rates is how ocean plays the
  champions: its Heart of Ruin / Vendetta / Marcella teams are much weaker than its Prism / Willow teams, while the
  top teams win with the former.
- **Opponent split.** Every nudge reads about +0.2 against the Fish body and negative against the Mite body
  (-0.1 light, -0.4 to -0.65 at 50%). The draft cannot see the opponent, so this cannot be used.
- **Live scrims, observational** (`live.py`; 8,755 games against Fish, 9,152 against Mite; within a map/side cell,
  version effects removed): our teams one sd closer to their preference won -0.9 ±1.4 points against Fish and
  +0.1 ±1.1 against Mite (conditional scores). No signal, wide intervals.

## Limits and what was not done

- The bodies are ocean's code with Fish's/Mite's drafts, ~10 points easier than the real teams; the draft model was
  fitted against them. A live effect the bodies cannot show is not ruled out; the live read above is observational.
- No 100k-fuel run, no 128-ladder-map side read, no live test, no out-of-fold fit on draft10's 800k lab games.
- Mirror, astraeus and other opponents were not played.
- 17 held-out maps share a draft-lab key with a screen map (dropped from the pooled table).

## Files

`extract.py` (archive -> drafts), `picture.py`, `nudge.py` (directions, strengths, nudged model), `run.py`
(build / play / read / pool), `swaps.py`, `fidelity.py`, `live.py`. Data: `~/tmp-offload/draftnudge/`
(`results/` per-game outcomes, `work/final/` the tables, `work/directions.json`, `work/levels.json`, `labs/`).
Arm bots: `bots/variants/dn-*` (gitignored; safe to delete).
