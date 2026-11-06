# Fish fidelity scorecard

| column | dataset | games (sides in Fish's role) |
| --- | --- | ---: |
| Fish (ladder) | `fish` (seventh, fifth, sixth) | 412 |
| candidate | `combat-r2` (A, B) | 256 |
| control | `control-ast37` (A, B) | 256 |

- **Fidelity, candidate: 71.2** over 106 core metrics (100 = Fish on every one).
- **Fidelity, control: 70.1** over 106 core metrics (100 = Fish on every one).
- Candidate closer to Fish than the control on 44 of 106 core metrics.

## The 15 core metrics furthest from Fish (candidate)

| # | metric | section | Fish | candidate | control | gap |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `win` win rate | outcome | 86.2% | 10.2%* | 50.0%* | 1.73 |
| 2 | `camp_deaths` deaths to camps per game | 9-10 combat | 1.17 | 0.223* | 0.312* | 1.66 |
| 3 | `kills` champion kills per game (bodies) | 9-10 combat | 8.6 | 2.06* | 6.57* | 1.43 |
| 4 | `keep_rate` recall kept at timer 1 (the last chance to cancel) | 8 economy | 45.0% | 91.7%* | 93.8%* | 1.09 |
| 5 | `ward_bush` ward placements on a bush | 12 wards and bushes | 83.3% | 100.0%* | 73.4%* | 0.84 |
| 6 | `deaths` deaths per game (bodies; Cassi and Issac die together) | 9-10 combat | 5.15 | 11.4* | 9.16* | 0.79 |
| 7 | `campcont:d4` keeps hitting camps, nearest enemy d4 | 9-10 combat | 43.2% | 10.0%* | 51.3%* | 0.79 |
| 8 | `camp_death_share` share of deaths dealt by camps | 9-10 combat | 22.8% | 2.0%* | 3.4%* | 0.71 |
| 9 | `solo_clear:Golem` Fish-only Golem clears done solo | 7.1/7.5 farming | 2.3% | 21.7%* | 22.1%* | 0.67 |
| 10 | `gems600` tributed gems by round 600 | outcome | 576 | 300* | 399* | 0.65 |
| 11 | `bush_tie:none` steps onto a bush among equal-progress steps, no enemy | 12 wards and bushes | 74.8% | 93.1%* | 49.8%* | 0.52 |
| 12 | `cassi_stun_on_cd` Cassi stuns when her damage spell is on cooldown | 9-10 combat | 99.3% | 89.3%* | 45.7%* | 0.50 |
| 13 | `gold600` team gold earned by round 600 | outcome | 4,354 | 2,649* | 3,287* | 0.50 |
| 14 | `shards` shards bought per champion-game | 8 economy | 36.5 | 22.5* | 29.9* | 0.48 |
| 15 | `spent` gold spent per champion-game (engine statistics) | 8 economy | 1,110 | 687* | 917* | 0.48 |

## All metrics

`ref`: FISH_MODEL.md's own figure, where it gives one (its definitions can differ slightly). `*`: beyond 2 bootstrap SE of Fish; `~`: within. gap: effect size against Fish.

### 6 turn budget

| metric | ref | Fish | n | candidate | gap | control | gap | ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `budget:dead` share of turns: dead | 8.5% | 6.5% | 1910811 | 13.5%* | 0.24 | 10.5%* | 0.15 | 1.64 |
| `budget:home` share of turns: on own spawn | 3.1% | 3.1% | 1910811 | 2.3%* | 0.05 | 2.6%~ | 0.03 | 1.62 |
| `budget:tribute` share of turns: tribute channel or attempt | 2.8% | 3.0% | 1910811 | 1.7%* | 0.08 | 2.6%* | 0.03 | 3.24 |
| `budget:fight` share of turns: an action on an enemy champion | 3.0% | 2.7% | 1910811 | 2.1%* | 0.04 | 3.2%* | 0.03 | 1.26 |
| `budget:clear` share of turns: hitting a camp | 20.9% | 21.9% | 1910811 | 18.3%* | 0.09 | 16.7%* | 0.13 | 0.68 |
| `budget:capture` share of turns: on an empty group (capture) | 4.7% | 5.6% | 1910811 | 6.0%~ | 0.02 | 6.4%~ | 0.04 | 0.58 |
| `budget:recall` share of turns: keeping a recall channel | 6.7% | 6.4% | 1910811 | 5.1%* | 0.06 | 5.4%* | 0.04 | 1.37 |
| `budget:wait` share of turns: within 2 of a respawning group | 7.9% | 8.7% | 1910811 | 8.8%~ | 0.00 | 9.1%~ | 0.01 | 0.31 |
| `budget:approach` share of turns: walking within 3 of a living camp | 7.0% | 7.4% | 1910811 | 7.1%~ | 0.01 | 7.4%~ | 0.00 | 4.45 |
| `budget:travel` share of turns: other walking | 34.6% | 34.3% | 1910811 | 32.9%~ | 0.03 | 33.9%~ | 0.01 | 3.15 |
| `budget:idle` share of turns: idle | 0.8% | 0.6% | 1910811 | 2.2%* | 0.14 | 2.2%* | 0.15 | 0.97 |

### 6 turn budget by champion

| metric | ref | Fish | n | candidate | gap | control | gap | ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `budget:dead:Marcella` Marcella: dead |  | 5.3% | 213198 | 10.6%* | 0.20 | 8.9%* | 0.14 | 1.39 |
| `budget:home:Marcella` Marcella: on own spawn |  | 2.7% | 213198 | 2.7%~ | 0.00 | 2.8%~ | 0.01 | 0.25 |
| `budget:tribute:Marcella` Marcella: tribute channel or attempt | 5.7% | 6.6% | 213198 | 2.8%* | 0.18 | 3.7%* | 0.13 | 1.40 |
| `budget:fight:Marcella` Marcella: an action on an enemy champion |  | 4.2% | 213198 | 3.2%* | 0.05 | 5.9%* | 0.08 | 0.68 |
| `budget:clear:Marcella` Marcella: hitting a camp | 12.0% | 12.5% | 213198 | 12.9%~ | 0.01 | 12.0%~ | 0.02 | 0.66 |
| `budget:capture:Marcella` Marcella: on an empty group (capture) |  | 6.7% | 213198 | 5.1%* | 0.07 | 5.4%* | 0.06 | 1.22 |
| `budget:recall:Marcella` Marcella: keeping a recall channel |  | 7.6% | 213198 | 6.3%* | 0.05 | 6.8%* | 0.03 | 1.67 |
| `budget:wait:Marcella` Marcella: within 2 of a respawning group |  | 11.4% | 213198 | 10.3%~ | 0.04 | 10.3%~ | 0.03 | 1.07 |
| `budget:approach:Marcella` Marcella: walking within 3 of a living camp |  | 8.1% | 213198 | 7.3%~ | 0.03 | 9.0%~ | 0.03 | 0.91 |
| `budget:travel:Marcella` Marcella: other walking |  | 34.6% | 213198 | 37.6%~ | 0.06 | 34.4%~ | 0.00 | 18.67 |
| `budget:idle:Marcella` Marcella: idle |  | 0.3% | 213198 | 1.2%* | 0.12 | 0.7%* | 0.06 | 1.89 |
| `budget:dead:Vesper` Vesper: dead |  | 4.2% | 181679 | 6.7%* | 0.11 | 3.9%~ | 0.01 | 7.97 |
| `budget:home:Vesper` Vesper: on own spawn | 5.7% | 5.6% | 181679 | 2.5%* | 0.16 | 3.2%* | 0.12 | 1.33 |
| `budget:tribute:Vesper` Vesper: tribute channel or attempt | 7.0% | 6.5% | 181679 | 4.0%* | 0.11 | 4.1%* | 0.11 | 1.05 |
| `budget:fight:Vesper` Vesper: an action on an enemy champion |  | 3.0% | 181679 | 2.7%~ | 0.02 | 4.9%* | 0.10 | 0.20 |
| `budget:clear:Vesper` Vesper: hitting a camp |  | 21.8% | 181679 | 22.8%~ | 0.02 | 16.3%* | 0.14 | 0.16 |
| `budget:capture:Vesper` Vesper: on an empty group (capture) |  | 7.5% | 181679 | 11.4%~ | 0.13 | 9.3%~ | 0.06 | 2.08 |
| `budget:recall:Vesper` Vesper: keeping a recall channel |  | 6.6% | 181679 | 7.2%~ | 0.02 | 6.0%~ | 0.03 | 0.82 |
| `budget:wait:Vesper` Vesper: within 2 of a respawning group |  | 8.9% | 181679 | 9.7%~ | 0.03 | 9.9%~ | 0.03 | 0.83 |
| `budget:approach:Vesper` Vesper: walking within 3 of a living camp |  | 5.2% | 181679 | 6.0%~ | 0.04 | 6.6%* | 0.06 | 0.60 |
| `budget:travel:Vesper` Vesper: other walking |  | 29.4% | 181679 | 23.8%* | 0.13 | 32.3%~ | 0.06 | 2.00 |
| `budget:idle:Vesper` Vesper: idle |  | 1.2% | 181679 | 3.2%* | 0.14 | 3.6%* | 0.16 | 0.89 |
| `budget:dead:Vendetta` Vendetta: dead |  | 4.6% | 280104 | 9.1%* | 0.18 | 5.9%~ | 0.06 | 3.03 |
| `budget:home:Vendetta` Vendetta: on own spawn |  | 2.2% | 280104 | 2.3%~ | 0.01 | 2.2%~ | 0.00 | 5.76 |
| `budget:tribute:Vendetta` Vendetta: tribute channel or attempt |  | 4.4% | 280104 | 2.3%* | 0.12 | 3.4%* | 0.05 | 2.27 |
| `budget:fight:Vendetta` Vendetta: an action on an enemy champion |  | 2.6% | 280104 | 1.5%* | 0.08 | 1.8%* | 0.05 | 1.44 |
| `budget:clear:Vendetta` Vendetta: hitting a camp |  | 21.7% | 280104 | 19.0%* | 0.06 | 18.1%* | 0.09 | 0.73 |
| `budget:capture:Vendetta` Vendetta: on an empty group (capture) |  | 7.2% | 280104 | 6.9%~ | 0.01 | 6.2%* | 0.04 | 0.28 |
| `budget:recall:Vendetta` Vendetta: keeping a recall channel |  | 7.1% | 280104 | 6.7%~ | 0.02 | 6.0%* | 0.04 | 0.38 |
| `budget:wait:Vendetta` Vendetta: within 2 of a respawning group |  | 8.3% | 280104 | 8.7%~ | 0.01 | 7.1%~ | 0.05 | 0.27 |
| `budget:approach:Vendetta` Vendetta: walking within 3 of a living camp |  | 8.0% | 280104 | 7.6%~ | 0.02 | 6.6%* | 0.06 | 0.30 |
| `budget:travel:Vendetta` Vendetta: other walking |  | 33.1% | 280104 | 33.3%~ | 0.00 | 40.4%* | 0.15 | 0.03 |
| `budget:idle:Vendetta` Vendetta: idle |  | 0.7% | 280104 | 2.6%* | 0.15 | 2.4%* | 0.14 | 1.09 |
| `budget:dead:HoR` HoR: dead |  | 5.2% | 324354 | 11.0%* | 0.22 | 8.6%* | 0.13 | 1.61 |
| `budget:home:HoR` HoR: on own spawn |  | 3.5% | 324354 | 1.9%* | 0.10 | 1.6%* | 0.13 | 0.78 |
| `budget:tribute:HoR` HoR: tribute channel or attempt |  | 2.6% | 324354 | 1.8%* | 0.05 | 2.5%~ | 0.01 | 10.70 |
| `budget:fight:HoR` HoR: an action on an enemy champion |  | 3.3% | 324354 | 2.9%~ | 0.02 | 7.0%* | 0.17 | 0.14 |
| `budget:clear:HoR` HoR: hitting a camp |  | 23.4% | 324354 | 20.8%* | 0.06 | 16.7%* | 0.17 | 0.37 |
| `budget:capture:HoR` HoR: on an empty group (capture) |  | 6.2% | 324354 | 6.8%~ | 0.02 | 5.4%* | 0.03 | 0.70 |
| `budget:recall:HoR` HoR: keeping a recall channel |  | 6.4% | 324354 | 5.7%* | 0.03 | 5.7%* | 0.03 | 1.04 |
| `budget:wait:HoR` HoR: within 2 of a respawning group |  | 8.0% | 324354 | 8.7%~ | 0.02 | 6.9%~ | 0.04 | 0.55 |
| `budget:approach:HoR` HoR: walking within 3 of a living camp |  | 7.4% | 324354 | 7.3%~ | 0.00 | 6.9%~ | 0.02 | 0.16 |
| `budget:travel:HoR` HoR: other walking |  | 33.3% | 324354 | 30.8%~ | 0.05 | 36.3%~ | 0.06 | 0.87 |
| `budget:idle:HoR` HoR: idle |  | 0.7% | 324354 | 2.4%* | 0.15 | 2.5%* | 0.15 | 0.96 |
| `budget:dead:Cassi` Cassi: dead |  | 9.2% | 342127 | 20.3%* | 0.32 | 15.6%* | 0.20 | 1.63 |
| `budget:home:Cassi` Cassi: on own spawn |  | 3.1% | 342127 | 2.4%~ | 0.05 | 2.5%~ | 0.04 | 1.24 |
| `budget:tribute:Cassi` Cassi: tribute channel or attempt |  | 1.4% | 342127 | 0.6%* | 0.09 | 1.2%~ | 0.02 | 4.88 |
| `budget:fight:Cassi` Cassi: an action on an enemy champion |  | 2.3% | 342127 | 2.3%~ | 0.00 | 2.3%~ | 0.00 | 0.06 |
| `budget:clear:Cassi` Cassi: hitting a camp |  | 23.2% | 342127 | 16.3%* | 0.17 | 16.8%* | 0.16 | 1.08 |
| `budget:capture:Cassi` Cassi: on an empty group (capture) |  | 3.9% | 342127 | 3.9%~ | 0.00 | 4.0%~ | 0.00 | 0.19 |
| `budget:recall:Cassi` Cassi: keeping a recall channel |  | 5.0% | 342127 | 3.0%* | 0.11 | 4.0%* | 0.05 | 2.18 |
| `budget:wait:Cassi` Cassi: within 2 of a respawning group |  | 8.8% | 342127 | 8.4%~ | 0.01 | 8.6%~ | 0.01 | 1.77 |
| `budget:approach:Cassi` Cassi: walking within 3 of a living camp |  | 6.7% | 342127 | 7.0%~ | 0.01 | 7.0%~ | 0.01 | 1.04 |
| `budget:travel:Cassi` Cassi: other walking |  | 36.1% | 342127 | 33.5%~ | 0.06 | 35.5%~ | 0.01 | 4.51 |
| `budget:idle:Cassi` Cassi: idle |  | 0.2% | 342127 | 2.4%* | 0.21 | 2.5%* | 0.22 | 0.97 |
| `budget:dead:Issac` Issac: dead |  | 9.2% | 342127 | 20.3%* | 0.32 | 15.6%* | 0.20 | 1.63 |
| `budget:home:Issac` Issac: on own spawn |  | 3.4% | 342127 | 2.0%* | 0.09 | 2.2%* | 0.07 | 1.21 |
| `budget:tribute:Issac` Issac: tribute channel or attempt |  | 1.1% | 342127 | 0.7%* | 0.04 | 1.5%* | 0.03 | 1.20 |
| `budget:fight:Issac` Issac: an action on an enemy champion |  | 2.1% | 342127 | 1.1%* | 0.08 | 1.8%* | 0.02 | 3.42 |
| `budget:clear:Issac` Issac: hitting a camp |  | 23.4% | 342127 | 19.3%* | 0.10 | 18.4%* | 0.12 | 0.81 |
| `budget:capture:Issac` Issac: on an empty group (capture) |  | 4.6% | 342127 | 5.0%~ | 0.02 | 5.6%* | 0.04 | 0.40 |
| `budget:recall:Issac` Issac: keeping a recall channel |  | 6.7% | 342127 | 4.6%* | 0.09 | 6.1%* | 0.02 | 3.76 |
| `budget:wait:Issac` Issac: within 2 of a respawning group |  | 7.3% | 342127 | 7.6%~ | 0.01 | 8.3%~ | 0.04 | 0.34 |
| `budget:approach:Issac` Issac: walking within 3 of a living camp |  | 8.3% | 342127 | 7.6%~ | 0.02 | 8.0%~ | 0.01 | 2.85 |
| `budget:travel:Issac` Issac: other walking |  | 33.4% | 342127 | 29.3%* | 0.09 | 30.6%~ | 0.06 | 1.47 |
| `budget:idle:Issac` Issac: idle |  | 0.5% | 342127 | 2.3%* | 0.16 | 1.8%* | 0.13 | 1.25 |
| `budget:dead:Willow` Willow: dead |  | 4.6% | 183121 | 9.0%* | 0.17 | 9.5%* | 0.19 | 0.90 |
| `budget:home:Willow` Willow: on own spawn |  | 1.8% | 183121 | 2.2%~ | 0.03 | 3.4%~ | 0.10 | 0.29 |
| `budget:tribute:Willow` Willow: tribute channel or attempt |  | 0.7% | 183121 | 1.0%* | 0.03 | 1.8%* | 0.10 | 0.31 |
| `budget:fight:Willow` Willow: an action on an enemy champion |  | 1.4% | 183121 | 1.1%~ | 0.02 | 1.2%~ | 0.02 | 1.41 |
| `budget:clear:Willow` Willow: hitting a camp |  | 27.9% | 183121 | 20.2%* | 0.18 | 20.4%* | 0.18 | 1.03 |
| `budget:capture:Willow` Willow: on an empty group (capture) |  | 2.4% | 183121 | 6.0%* | 0.18 | 4.3%* | 0.11 | 1.73 |
| `budget:recall:Willow` Willow: keeping a recall channel |  | 5.9% | 183121 | 3.8%* | 0.10 | 3.7%* | 0.10 | 0.94 |
| `budget:wait:Willow` Willow: within 2 of a respawning group |  | 8.2% | 183121 | 8.6%~ | 0.01 | 10.0%~ | 0.06 | 0.20 |
| `budget:approach:Willow` Willow: walking within 3 of a living camp |  | 7.5% | 183121 | 7.0%~ | 0.02 | 7.4%~ | 0.00 | 6.31 |
| `budget:travel:Willow` Willow: other walking | 39.9% | 39.1% | 183121 | 40.1%~ | 0.02 | 35.6%~ | 0.07 | 0.27 |
| `budget:idle:Willow` Willow: idle |  | 0.5% | 183121 | 1.1%~ | 0.08 | 2.7%* | 0.19 | 0.39 |
| `budget:dead:Prism` Prism: dead |  | 5.2% | 11298 | 8.9%~ | 0.15 | 8.3%~ | 0.12 | 1.17 |
| `budget:home:Prism` Prism: on own spawn |  | 1.2% | 11298 | 1.2%~ | 0.00 | 3.0%* | 0.13 | 0.04 |
| `budget:tribute:Prism` Prism: tribute channel or attempt |  | 4.6% | 11298 | 11.6%~ | 0.26 | 3.8%~ | 0.04 | 6.69 |
| `budget:fight:Prism` Prism: an action on an enemy champion |  | 2.7% | 11298 | 2.2%~ | 0.03 | 2.2%~ | 0.03 | 1.08 |
| `budget:clear:Prism` Prism: hitting a camp |  | 6.7% | 11298 | 4.6%* | 0.09 | 17.2%* | 0.33 | 0.28 |
| `budget:capture:Prism` Prism: on an empty group (capture) |  | 18.2% | 11298 | 15.2%~ | 0.08 | 7.8%* | 0.31 | 0.25 |
| `budget:recall:Prism` Prism: keeping a recall channel |  | 2.2% | 11298 | 1.8%~ | 0.03 | 4.9%* | 0.14 | 0.23 |
| `budget:wait:Prism` Prism: within 2 of a respawning group |  | 17.5% | 11298 | 16.8%~ | 0.02 | 10.9%* | 0.19 | 0.10 |
| `budget:approach:Prism` Prism: walking within 3 of a living camp |  | 1.7% | 11298 | 1.0%~ | 0.06 | 7.1%* | 0.28 | 0.22 |
| `budget:travel:Prism` Prism: other walking |  | 38.7% | 11298 | 35.1%~ | 0.07 | 32.4%~ | 0.13 | 0.56 |
| `budget:idle:Prism` Prism: idle |  | 1.4% | 11298 | 1.7%~ | 0.02 | 2.3%* | 0.07 | 0.30 |
| `budget:dead:Ren` Ren: dead |  | 8.2% | 29342 | n/a |  | 12.3%~ | 0.13 |  |
| `budget:home:Ren` Ren: on own spawn |  | 1.5% | 29342 | n/a |  | 2.0%~ | 0.04 |  |
| `budget:tribute:Ren` Ren: tribute channel or attempt |  | 0.6% | 29342 | n/a |  | 1.8%* | 0.11 |  |
| `budget:fight:Ren` Ren: an action on an enemy champion |  | 2.4% | 29342 | n/a |  | 5.3%* | 0.15 |  |
| `budget:clear:Ren` Ren: hitting a camp |  | 11.3% | 29342 | n/a |  | 14.4%* | 0.09 |  |
| `budget:capture:Ren` Ren: on an empty group (capture) |  | 6.0% | 29342 | n/a |  | 5.5%~ | 0.02 |  |
| `budget:recall:Ren` Ren: keeping a recall channel |  | 5.0% | 29342 | n/a |  | 5.7%~ | 0.03 |  |
| `budget:wait:Ren` Ren: within 2 of a respawning group |  | 9.0% | 29342 | n/a |  | 8.3%~ | 0.03 |  |
| `budget:approach:Ren` Ren: walking within 3 of a living camp |  | 7.1% | 29342 | n/a |  | 7.2%~ | 0.00 |  |
| `budget:travel:Ren` Ren: other walking |  | 48.0% | 29342 | n/a |  | 34.8%* | 0.27 |  |
| `budget:idle:Ren` Ren: idle |  | 0.8% | 29342 | n/a |  | 2.8%* | 0.15 |  |

### 7.1 grouping and space

| metric | ref | Fish | n | candidate | gap | control | gap | ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `nearest_ally` nearest alive off-spawn ally, median Chebyshev tiles | 2 | 3 | 1720223 | 4 | 0.29 | 4 | 0.29 | 1.00 |
| `ally_within4` nearest ally within 4 (off-spawn turns with another ally off spawn) | 67.0% | 65.7% | 1720223 | 54.4%* | 0.23 | 55.4%* | 0.21 | 1.09 |
| `centroid_spread` mean Chebyshev distance of off-spawn bodies to the team centroid (rounds with 2+) |  | 8.02 | 342346 | 9.03* | 0.12 | 8.69~ | 0.08 | 1.49 |
| `pair_dist` mean pairwise Chebyshev distance of off-spawn bodies |  | 12.1 | 342346 | 14.1* | 0.15 | 13.5* | 0.10 | 1.41 |
| `team_within8` every off-spawn body within 8 of the centroid |  | 31.8% | 342346 | 31.0%~ | 0.02 | 31.4%~ | 0.01 | 2.19 |
| `side_own` off-spawn turns on own half (walk-distance territory) | 69.0% | 67.4% | 1727537 | 75.4%* | 0.18 | 72.3%* | 0.11 | 1.68 |
| `side_mid` off-spawn turns in the middle | 22.0% | 23.2% | 1727537 | 19.8%* | 0.08 | 19.6%* | 0.09 | 0.95 |
| `side_enemy` off-spawn turns on the enemy half | 9.0% | 9.4% | 1727537 | 4.8%* | 0.18 | 8.1%~ | 0.05 | 4.02 |
| `pay_own` payouts on own side | 77.0% | 79.9% | 22432 | 83.2%* | 0.08 | 78.8%~ | 0.03 | 3.15 |
| `pay_middle` payouts in the middle | 16.0% | 12.3% | 22432 | 10.3%~ | 0.06 | 11.7%~ | 0.02 | 3.63 |
| `pay_enemy` payouts on the enemy side | 7.0% | 7.8% | 22432 | 6.5%~ | 0.05 | 9.4%~ | 0.06 | 0.85 |

### 7.1/7.5 farming

| metric | ref | Fish | n | candidate | gap | control | gap | ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `pay1k` payouts per 1,000 rounds per champion-game, median |  | 9.9 | 2262 | 9.1 | 0.08 | 10.9 | 0.10 | 0.88 |
| `pay1k_mean` payouts per 1,000 rounds per champion-game, mean |  | 13 | 2262 | 11* | 0.17 | 12.3~ | 0.05 | 3.17 |
| `pay_single` payouts with a single recipient | 92.0% | 93.6% | 22432 | 98.2%* | 0.24 | 96.3%* | 0.12 | 1.98 |
| `pay_groups` distinct payout groups per champion-game |  | 5.41 | 2262 | 4.78* | 0.12 | 5.49~ | 0.02 | 8.12 |
| `solo_clear:Wolf` Fish-only Wolf-led clears done solo |  | 30.0% | 5983 | 35.7%* | 0.12 | 40.3%* | 0.22 | 0.56 |
| `solo_clear:Elk` Fish-only Elk-led clears done solo | 8.2% | 9.7% | 4228 | 21.3%* | 0.32 | 28.4%* | 0.49 | 0.66 |
| `solo_clear:Golem` Fish-only Golem clears done solo | 1.4% | 2.3% | 310 | 21.7%* | 0.67 | 22.1%* | 0.68 | 0.98 |
| `solo_clear:Monolith` Fish-only Monolith clears done solo | 6.0% | 5.4% | 92 | n/a |  | n/a |  |  |
| `wake_alone` waker of a fully asleep group has no other body within 4 of the group |  | 60.9% | 29713 | 69.9%* | 0.19 | 68.2%* | 0.15 | 1.25 |
| `wake_alone:Elk` waker alone: Elk groups | 51.0% | 54.1% | 7175 | 63.2%* | 0.18 | 63.4%* | 0.19 | 0.98 |
| `wake_alone:Golem` waker alone: Golem groups | 53.0% | 63.3% | 1334 | 70.1%~ | 0.14 | 69.4%~ | 0.13 | 1.11 |
| `wake_alone:Wolf` waker alone: Wolf groups | 55.0% | 61.2% | 9416 | 70.0%* | 0.18 | 70.3%* | 0.19 | 0.96 |

### 7.1 farming by champion

| metric | ref | Fish | n | candidate | gap | control | gap | ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `pay1k:Marcella` Marcella: payouts per 1,000 rounds, median | 16.7 | 18.6 | 248 | 12.1 | 0.43 | 12.6 | 0.39 | 1.10 |
| `pay_groups:Marcella` Marcella: distinct payout groups per game |  | 6.47 | 248 | 4.96* | 0.27 | 5.76~ | 0.12 | 2.28 |
| `pay1k:Vesper` Vesper: payouts per 1,000 rounds, median | 22 | 23.3 | 198 | 18.9 | 0.21 | 16.1 | 0.37 | 0.57 |
| `pay_groups:Vesper` Vesper: distinct payout groups per game |  | 7.98 | 198 | 7.25~ | 0.10 | 7.09~ | 0.12 | 0.81 |
| `pay1k:Vendetta` Vendetta: payouts per 1,000 rounds, median | 17.6 | 18.1 | 337 | 12 | 0.41 | 13.3 | 0.31 | 1.33 |
| `pay_groups:Vendetta` Vendetta: distinct payout groups per game |  | 7.41 | 337 | 5.86* | 0.24 | 6.63* | 0.11 | 2.12 |
| `pay1k:HoR` HoR: payouts per 1,000 rounds, median | 10.4 | 11 | 383 | 10.9 | 0.01 | 10 | 0.10 | 0.10 |
| `pay_groups:HoR` HoR: distinct payout groups per game |  | 5.99 | 383 | 5.6~ | 0.07 | 5.72~ | 0.05 | 1.43 |
| `pay1k:Cassi` Cassi: payouts per 1,000 rounds, median | 5.8 | 6.1 | 406 | 4.3 | 0.35 | 6.1 | 0.00 |  |
| `pay_groups:Cassi` Cassi: distinct payout groups per game |  | 4.27 | 406 | 3.03* | 0.34 | 3.95~ | 0.08 | 4.39 |
| `pay1k:Issac` Issac: payouts per 1,000 rounds, median | 4.8 | 4.8 | 406 | 6.5 | 0.30 | 8.7 | 0.59 | 0.51 |
| `pay_groups:Issac` Issac: distinct payout groups per game |  | 3.71 | 406 | 4.02~ | 0.08 | 5.05* | 0.31 | 0.26 |
| `pay1k:Willow` Willow: payouts per 1,000 rounds, median | 3.1 | 2.8 | 241 | 7.3 | 0.96 | 9.7 | 1.24 | 0.77 |
| `pay_groups:Willow` Willow: distinct payout groups per game |  | 2.71 | 241 | 4.33* | 0.47 | 5.15* | 0.64 | 0.73 |
| `pay1k:Prism` Prism: payouts per 1,000 rounds, median |  | 49.5 | 18 | 17.4 | 1.05 | 15.3 | 1.17 | 0.89 |
| `pay_groups:Prism` Prism: distinct payout groups per game |  | 10.3 | 18 | 6.5~ | 0.46 | 6.12* | 0.52 | 0.88 |
| `pay1k:Ren` Ren: payouts per 1,000 rounds, median |  | 5.4 | 19 | n/a |  | 8.1 | 0.41 |  |
| `pay_groups:Ren` Ren: distinct payout groups per game |  | 7.16 | 19 | n/a |  | 6.08~ | 0.16 |  |

### 8 economy

| metric | ref | Fish | n | candidate | gap | control | gap | ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `spent` gold spent per champion-game (engine statistics) |  | 1,110 | 2262 | 687* | 0.48 | 917* | 0.19 | 2.52 |
| `shards` shards bought per champion-game |  | 36.5 | 2262 | 22.5* | 0.48 | 29.9* | 0.20 | 2.43 |
| `has_emblem` champion-games with an emblem |  | 78.4% | 2262 | 74.7%* | 0.09 | 85.7%* | 0.19 | 0.46 |
| `first_emblem` round of the first emblem, median (champions with one; 10-round bins) |  | 200 | 1774 | 220 | 0.10 | 200 | 0.00 |  |
| `trib_bag` gems carried at a tribute start, median |  | 26 | 10420 | 18 | 0.37 | 21 | 0.21 | 1.72 |
| `tribute_start` tribute starts per free off-spawn turn |  | 0.6% | 1664748 | 0.5%* | 0.02 | 0.6%~ | 0.00 | 12.19 |
| `recall_start` recall started on free turns ending off spawn with no channel running (prepared recall) | 100.0% | 100.0% | 1495719 | 99.9%* | 0.05 | 99.5%* | 0.13 | 0.37 |
| `recall_survive` a recall started on a free turn still running after the next turn | 3.8% | 4.6% | 1272849 | 1.4%* | 0.19 | 1.9%* | 0.16 | 1.25 |
| `keep_rate` recall kept at timer 1 (the last chance to cancel) |  | 45.0% | 36468 | 91.7%* | 1.09 | 93.8%* | 1.17 | 0.93 |
| `keep_rule` timer-1 keep rule agreement (capturing: h<=0.40; payout round: h<=0.63; else h<=0.63 or gold>=30) | 90.6% | 90.0% | 36468 | 99.3%* | 0.48 | 50.1%* | 0.92 | 0.52 |
| `home_gate` home gate (h<=0.63 or gold>=30) holds at a completed recall | 98.6% | 98.3% | 16406 | 99.4%* | 0.10 | 63.9%* | 1.03 | 0.10 |
| `home_reason_hurt` completed recalls with h<=0.63 | 51.5% | 49.2% | 16406 | 53.1%* | 0.08 | 41.6%* | 0.15 | 0.51 |

### 8 economy by champion

| metric | ref | Fish | n | candidate | gap | control | gap | ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `spent:Marcella` Marcella: gold spent per game | 2,318 | 2,609 | 248 | 1,191* | 0.78 | 1,264* | 0.72 | 1.08 |
| `shards:Marcella` Marcella: shards per game | 77 | 86.2 | 248 | 39.1* | 0.79 | 41.1* | 0.74 | 1.07 |
| `first_emblem:Marcella` Marcella: first emblem round, median | 88 | 80 | 246 | 140 | 0.56 | 140 | 0.56 | 1.00 |
| `trib_bag:Marcella` Marcella: tributed bag, median | 33 | 32 | 2365 | 23 | 0.33 | 24 | 0.29 | 1.15 |
| `spent:Vesper` Vesper: gold spent per game | 3,866 | 3,662 | 198 | 2,430* | 0.41 | 2,881* | 0.24 | 1.71 |
| `shards:Vesper` Vesper: shards per game | 128 | 121 | 198 | 80.4* | 0.41 | 95* | 0.24 | 1.68 |
| `first_emblem:Vesper` Vesper: first emblem round, median | 82 | 80 | 196 | 90 | 0.12 | 70 | 0.13 | 0.88 |
| `trib_bag:Vesper` Vesper: tributed bag, median | 57 | 36 | 1392 | 23 | 0.45 | 31 | 0.15 | 3.00 |
| `spent:Vendetta` Vendetta: gold spent per game | 1,475 | 1,530 | 337 | 875* | 0.56 | 1,359~ | 0.12 | 4.74 |
| `shards:Vendetta` Vendetta: shards per game | 49 | 50.4 | 337 | 28.7* | 0.56 | 44.6~ | 0.12 | 4.59 |
| `first_emblem:Vendetta` Vendetta: first emblem round, median | 140 | 130 | 332 | 190 | 0.38 | 160 | 0.21 | 1.83 |
| `trib_bag:Vendetta` Vendetta: tributed bag, median | 36 | 32 | 2116 | 19 | 0.52 | 23 | 0.33 | 1.58 |
| `spent:HoR` HoR: gold spent per game | 790 | 829 | 383 | 635* | 0.27 | 691~ | 0.18 | 1.46 |
| `shards:HoR` HoR: shards per game | 26 | 27.2 | 383 | 20.8* | 0.27 | 22.3~ | 0.20 | 1.37 |
| `first_emblem:HoR` HoR: first emblem round, median | 245 | 220 | 353 | 200 | 0.10 | 230 | 0.04 | 2.14 |
| `trib_bag:HoR` HoR: tributed bag, median | 28 | 25 | 1762 | 17 | 0.39 | 23 | 0.08 | 4.63 |
| `spent:Cassi` Cassi: gold spent per game | 325 | 354 | 406 | 183* | 0.66 | 304~ | 0.15 | 4.30 |
| `shards:Cassi` Cassi: shards per game | 10.5 | 11.5 | 406 | 5.89* | 0.67 | 9.73~ | 0.17 | 4.03 |
| `first_emblem:Cassi` Cassi: first emblem round, median | 418 | 360 | 280 | 460 | 0.25 | 410 | 0.13 | 1.88 |
| `trib_bag:Cassi` Cassi: tributed bag, median | 20 | 18 | 1234 | 14 | 0.25 | 14 | 0.25 | 1.00 |
| `spent:Issac` Issac: gold spent per game | 260 | 247 | 406 | 267~ | 0.08 | 462* | 0.62 | 0.12 |
| `shards:Issac` Issac: shards per game | 8.3 | 7.94 | 406 | 8.66~ | 0.09 | 14.8* | 0.62 | 0.14 |
| `first_emblem:Issac` Issac: first emblem round, median | 414 | 400 | 250 | 310 | 0.25 | 290 | 0.32 | 0.79 |
| `trib_bag:Issac` Issac: tributed bag, median | 17 | 17 | 1041 | 12 | 0.35 | 14 | 0.19 | 1.79 |
| `spent:Willow` Willow: gold spent per game | 135 | 151 | 241 | 344* | 0.82 | 388* | 0.94 | 0.87 |
| `shards:Willow` Willow: shards per game | 4.3 | 4.86 | 241 | 11.2* | 0.83 | 12.5* | 0.95 | 0.88 |
| `first_emblem:Willow` Willow: first emblem round, median | 453 | 380 | 90 | 270 | 0.34 | 280 | 0.31 | 1.12 |
| `trib_bag:Willow` Willow: tributed bag, median | 14 | 14 | 369 | 14 | 0.00 | 21 | 0.41 | 0.00 |
| `spent:Prism` Prism: gold spent per game |  | 148 | 18 | 328~ | 0.79 | 1,067* | 1.97 | 0.40 |
| `shards:Prism` Prism: shards per game |  | 4.72 | 18 | 10.7~ | 0.82 | 35.1* | 2.00 | 0.41 |
| `first_emblem:Prism` Prism: first emblem round, median |  | n/a | 5 | n/a |  | 190 |  |  |
| `trib_bag:Prism` Prism: tributed bag, median |  | 245 | 30 | 880 | 1.28 | 448 | 0.60 | 2.12 |
| `spent:Ren` Ren: gold spent per game |  | 1,007 | 19 | n/a |  | 752~ | 0.29 |  |
| `shards:Ren` Ren: shards per game |  | 32.8 | 19 | n/a |  | 24.5~ | 0.29 |  |
| `first_emblem:Ren` Ren: first emblem round, median |  | 270 | 16 | n/a |  | 230 | 0.16 |  |
| `trib_bag:Ren` Ren: tributed bag, median |  | 8 | 62 | n/a |  | 18 | 0.81 |  |

### 5 priority

| metric | ref | Fish | n | candidate | gap | control | gap | ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `prio_rank_ok` alive turns whose priority has Fish's rank residue ((-p) mod (N+1) = base-health rank) | 100.0% | 99.9% | 1779637 | 100.0%* | 0.02 | 16.2%* | 2.26 | 0.01 |
| `prio_mode_agree` priority mode agrees with the selector (dead / late / contact / quiet), alive unstunned |  | 98.3% | 1779637 | 98.7%* | 0.03 | 1.1%* | 2.67 | 0.01 |
| `prio_quiet_exact` quiet-predicted turns with the exact quiet value -rank-(N+1)*band |  | 98.7% | 1659118 | 98.7%~ | 0.00 | 0.0%* | 2.91 | 0.00 |
| `prio_dead_ok` dead turns with the dead level (L = -1) | 100.0% | 100.0% | 123049 | 100.0%~ | 0.00 | 0.0%* | 3.14 | 0.00 |
| `prio_write_repeat` priority writes that repeat the current value | 0.0% | 0.0% | 202251 | 0.0%~ | 0.00 | 0.0%~ | 0.00 |  |
| `prio_mode:quiet` alive turns in priority mode quiet |  | 92.3% | 1779637 | 91.0%* | 0.05 | 0.0%* | 2.58 | 0.02 |
| `prio_mode:late` alive turns in priority mode late |  | 2.3% | 1779637 | 3.6%* | 0.08 | 0.0%* | 0.30 | 0.26 |
| `prio_mode:contact` alive turns in priority mode contact |  | 4.8% | 1779637 | 5.3%~ | 0.02 | 16.2%* | 0.38 | 0.06 |
| `prio_mode:early` alive turns in priority mode early |  | 0.5% | 1779637 | 0.0%* | 0.14 | 0.0%* | 0.14 | 0.98 |
| `prio_mode:other` alive turns in priority mode other |  | 0.0% | 1779637 | 0.0%~ | 0.00 | 83.8%* | 2.31 | 0.00 |
| `prio_mode:unset` alive turns in priority mode unset |  | 0.1% | 1779637 | 0.0%* | 0.02 | 0.0%* | 0.03 | 0.93 |

### 9-10 combat

| metric | ref | Fish | n | candidate | gap | control | gap | ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `kills` champion kills per game (bodies) |  | 8.6 | 412 | 2.06* | 1.43 | 6.57* | 0.27 | 5.30 |
| `deaths` deaths per game (bodies; Cassi and Issac die together) |  | 5.15 | 412 | 11.4* | 0.79 | 9.16* | 0.58 | 1.38 |
| `camp_deaths` deaths to camps per game |  | 1.17 | 412 | 0.223* | 1.66 | 0.312* | 1.32 | 1.26 |
| `camp_death_share` share of deaths dealt by camps |  | 22.8% | 2123 | 2.0%* | 0.71 | 3.4%* | 0.62 | 1.15 |
| `enemy_in_sight` alive turns with an enemy champion in sight at turn start |  | 22.6% | 1786770 | 33.5%* | 0.24 | 31.9%* | 0.21 | 1.16 |
| `contact_hit` free turns with an enemy within 3 that hit an enemy champion |  | 53.8% | 70792 | 41.0%* | 0.26 | 51.7%* | 0.04 | 6.13 |
| `engage_rule` positioning rule agreement (10.1: kill available, or h>0.49 and danger<=0.28) | 73.6% | 73.9% | 44497 | 68.5%* | 0.12 | 67.7%* | 0.14 | 0.87 |
| `engage_rule:m2` positioning rule, melee at 2 | 73.5% | 73.8% | 15583 | 68.8%* | 0.11 | 66.6%* | 0.16 | 0.70 |
| `engage_rule:m1` positioning rule, melee adjacent | 74.2% | 74.6% | 15035 | 69.7%* | 0.11 | 69.1%* | 0.12 | 0.89 |
| `engage_rule:r` positioning rule, ranged within 3 | 72.9% | 73.3% | 13879 | 67.4%* | 0.13 | 67.3%* | 0.13 | 0.99 |
| `engage_rate:m2` engages: melee at 2 (ends adjacent or spell-hits) |  | 58.6% | 15583 | 38.5%* | 0.40 | 50.2%* | 0.17 | 2.41 |
| `engage_rate:m1` engages: melee adjacent (stays adjacent) |  | 69.7% | 15035 | 58.8%* | 0.23 | 63.9%* | 0.12 | 1.85 |
| `engage_rate:r` engages: ranged within 3 (does not back off) |  | 62.1% | 13879 | 48.8%* | 0.27 | 60.8%~ | 0.03 | 9.93 |
| `kill_override` engages when a kill is available from an engage tile | 98.7% | 98.4% | 2094 | 95.5%* | 0.17 | 94.8%* | 0.21 | 0.83 |
| `chase_rule` chase rule agreement (10.3) | 73.4% | 73.9% | 14931 | 75.3%~ | 0.03 | 65.0%* | 0.19 | 0.17 |
| `chase_rate` chases last turn's target, now nearest and out of basic range | 61.2% | 61.4% | 14931 | 46.9%* | 0.29 | 52.9%* | 0.17 | 1.68 |
| `basic_minehp` basic attack target = min EHP (2+ enemy champions in range) | 93.6% | 94.0% | 5126 | 84.0%* | 0.33 | 79.3%* | 0.45 | 0.73 |
| `basic_champ_first` basic attacks hit a champion when one is in range | 99.9% | 99.9% | 45517 | 100.0%* | 0.02 | 99.9%~ | 0.01 | 2.06 |
| `reset_use` melee reset after a surviving basic, cast unused | 94.6% | 98.3% | 4922 | 99.9%* | 0.20 | 99.8%* | 0.18 | 1.12 |
| `spell_when_still` exclusive damage spell cast when standing, ready, cast unused | 95.4% | 95.0% | 5840 | 97.9%* | 0.16 | 98.3%* | 0.19 | 0.85 |
| `stand_to_cast` stands still when its exclusive damage spell is ready with an enemy within 4 |  | 56.3% | 10580 | 45.7%* | 0.21 | 61.0%* | 0.10 | 2.23 |
| `hor_shield_rule` HoR shield iff a visible unstunned enemy threatens it | 93.1% | 93.1% | 33339 | 90.8%* | 0.09 | 88.6%* | 0.16 | 0.55 |
| `cassi_stun_on_cd` Cassi stuns when her damage spell is on cooldown | 98.9% | 99.3% | 1124 | 89.3%* | 0.50 | 45.7%* | 1.49 | 0.34 |
| `momentum` range 4-8: closes iff the previous step continued would close (9) | 70.8% | 70.9% | 197977 | 70.7%~ | 0.01 | 67.6%* | 0.07 | 0.07 |
| `range_close` range 4-8 free turns that close on the nearest enemy | 45.5% | 43.5% | 197977 | 33.4%* | 0.21 | 41.6%* | 0.04 | 5.38 |
| `campcont_rule` keeps hitting camps iff nearest enemy > 4 (agreement, enemy in sight) | 80.8% | 79.8% | 31933 | 91.0%* | 0.33 | 80.9%~ | 0.03 | 11.22 |
| `campcont:none` keeps hitting camps, nearest enemy none | 96.0% | 96.1% | 301879 | 97.7%* | 0.09 | 97.2%* | 0.06 | 1.51 |
| `campcont:far` keeps hitting camps, nearest enemy far | 89.1% | 87.7% | 8658 | 97.4%* | 0.39 | 96.5%* | 0.34 | 1.14 |
| `campcont:d8` keeps hitting camps, nearest enemy d8 | 85.3% | 82.7% | 5687 | 94.1%* | 0.37 | 85.6%* | 0.08 | 4.67 |
| `campcont:d7` keeps hitting camps, nearest enemy d7 | 85.5% | 83.7% | 5704 | 91.0%* | 0.22 | 86.0%* | 0.06 | 3.52 |
| `campcont:d6` keeps hitting camps, nearest enemy d6 | 79.1% | 75.5% | 4934 | 87.6%* | 0.32 | 81.3%* | 0.14 | 2.22 |
| `campcont:d5` keeps hitting camps, nearest enemy d5 | 67.6% | 67.0% | 3631 | 78.2%* | 0.25 | 63.6%~ | 0.07 | 3.51 |
| `campcont:d4` keeps hitting camps, nearest enemy d4 | 44.8% | 43.2% | 1874 | 10.0%* | 0.79 | 51.3%* | 0.16 | 4.85 |
| `campcont:d1-3` keeps hitting camps, nearest enemy d1-3 | 18.2% | 18.3% | 1445 | 10.8%* | 0.21 | 30.6%* | 0.29 | 0.75 |

### 12 wards and bushes

| metric | ref | Fish | n | candidate | gap | control | gap | ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ward_rate:contact` ward placed, ward ready, enemy within 5 | 8.0% | 8.8% | 87800 | 1.1%* | 0.39 | 3.2%* | 0.24 | 1.61 |
| `ward_rate:enemy` ward placed, ward ready, enemy visible farther | 5.0% | 5.4% | 158032 | 0.6%* | 0.32 | 3.5%* | 0.09 | 3.38 |
| `ward_rate:none` ward placed, ward ready, no enemy visible | 2.9% | 3.0% | 1009741 | 0.4%* | 0.21 | 3.8%* | 0.04 | 4.85 |
| `ward_per_turn` ward placements per alive turn |  | 2.7% | 1779637 | 0.5%* | 0.19 | 2.7%~ | 0.00 | 111.90 |
| `ward_bush` ward placements on a bush | 78.8% | 83.3% | 48502 | 100.0%* | 0.84 | 73.4%* | 0.24 | 3.49 |
| `ward_d2` ward placements at distance 2 from the placer | 88.7% | 85.7% | 48502 | 95.6%* | 0.35 | 90.8%* | 0.16 | 2.23 |
| `bush_tie:contact` steps onto a bush among equal-progress steps, enemy within 5 | 73.1% | 83.6% | 7216 | 73.2%* | 0.25 | 52.0%* | 0.70 | 0.37 |
| `bush_tie:enemy` steps onto a bush among equal-progress steps, enemy visible farther | 78.3% | 88.9% | 7639 | 87.8%~ | 0.03 | 48.0%* | 0.93 | 0.04 |
| `bush_tie:none` steps onto a bush among equal-progress steps, no enemy | 71.1% | 74.8% | 31404 | 93.1%* | 0.52 | 49.8%* | 0.52 | 0.99 |

### outcome

| metric | ref | Fish | n | candidate | gap | control | gap | ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `win` win rate | 77.2% | 86.2% | 412 | 10.2%* | 1.73 | 50.0%* | 0.81 | 2.14 |
| `final_round` round the game ends, mean |  | 860 | 412 | 872~ | 0.01 | 929* | 0.08 | 0.18 |
| `reach_2000` games reaching round 2000 | 2.0% | 2.9% | 412 | 2.3%~ | 0.04 | 2.3%~ | 0.04 | 1.00 |
| `gems300` tributed gems by round 300 |  | 185 | 412 | 115* | 0.47 | 150* | 0.21 | 2.22 |
| `gems600` tributed gems by round 600 |  | 576 | 412 | 300* | 0.65 | 399* | 0.37 | 1.77 |
| `gold300` team gold earned by round 300 |  | 1,942 | 412 | 1,258* | 0.43 | 1,473* | 0.28 | 1.57 |
| `gold600` team gold earned by round 600 |  | 4,354 | 412 | 2,649* | 0.50 | 3,287* | 0.28 | 1.77 |

### 9-10 combat by champion

| metric | ref | Fish | n | candidate | gap | control | gap | ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `contact_hit:Marcella` Marcella: contact turns hitting | 52.8% | 53.2% | 13071 | 40.6%* | 0.25 | 48.5%* | 0.09 | 2.68 |
| `enemy_in_sight:Marcella` Marcella: enemy in sight | 38.5% | 30.5% | 201805 | 40.8%* | 0.21 | 43.0%* | 0.26 | 0.83 |
| `contact_hit:Vesper` Vesper: contact turns hitting | 67.4% | 69.9% | 5487 | 55.8%* | 0.29 | 64.5%* | 0.12 | 2.53 |
| `enemy_in_sight:Vesper` Vesper: enemy in sight | 24.6% | 21.5% | 173963 | 33.0%* | 0.26 | 37.4%* | 0.35 | 0.74 |
| `contact_hit:Vendetta` Vendetta: contact turns hitting |  | 49.7% | 12652 | 30.8%* | 0.39 | 44.9%~ | 0.10 | 4.00 |
| `enemy_in_sight:Vendetta` Vendetta: enemy in sight |  | 23.6% | 267069 | 34.5%* | 0.24 | 21.5%~ | 0.05 | 4.65 |
| `contact_hit:HoR` HoR: contact turns hitting |  | 56.9% | 16125 | 48.9%* | 0.16 | 61.4%* | 0.09 | 1.75 |
| `enemy_in_sight:HoR` HoR: enemy in sight |  | 23.8% | 307452 | 35.1%* | 0.25 | 37.8%* | 0.30 | 0.82 |
| `contact_hit:Cassi` Cassi: contact turns hitting |  | 57.9% | 6122 | 47.0%* | 0.22 | 50.9%* | 0.14 | 1.57 |
| `enemy_in_sight:Cassi` Cassi: enemy in sight |  | 20.0% | 310670 | 31.0%* | 0.25 | 27.1%* | 0.17 | 1.51 |
| `contact_hit:Issac` Issac: contact turns hitting |  | 45.4% | 12771 | 29.6%* | 0.33 | 37.8%* | 0.15 | 2.13 |
| `enemy_in_sight:Issac` Issac: enemy in sight |  | 22.2% | 310619 | 33.2%* | 0.25 | 29.8%* | 0.17 | 1.42 |
| `contact_hit:Willow` Willow: contact turns hitting | 48.3% | 54.4% | 2944 | 36.7%* | 0.36 | 36.0%* | 0.37 | 0.96 |
| `enemy_in_sight:Willow` Willow: enemy in sight | 23.0% | 16.1% | 174519 | 25.9%* | 0.24 | 33.3%* | 0.41 | 0.60 |
| `contact_hit:Prism` Prism: contact turns hitting |  | 61.1% | 296 | 62.6%~ | 0.03 | 59.1%~ | 0.04 | 0.69 |
| `enemy_in_sight:Prism` Prism: enemy in sight |  | 21.3% | 10703 | 29.1%~ | 0.18 | 27.9%~ | 0.15 | 1.16 |
| `contact_hit:Ren` Ren: contact turns hitting |  | 52.1% | 1049 | n/a |  | 56.1%~ | 0.08 |  |
| `enemy_in_sight:Ren` Ren: enemy in sight |  | 22.4% | 26933 | n/a |  | 36.5%* | 0.31 |  |
