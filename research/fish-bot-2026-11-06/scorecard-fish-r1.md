# Fish fidelity scorecard

| column | dataset | games (sides in Fish's role) |
| --- | --- | ---: |
| Fish (ladder) | `fish` (seventh, fifth, sixth) | 412 |
| candidate | `fish-r1` (A, B) | 256 |
| control | `control-ast37` (A, B) | 256 |

- **Fidelity, candidate: 75.2** over 106 core metrics (100 = Fish on every one).
- **Fidelity, control: 70.1** over 106 core metrics (100 = Fish on every one).
- Candidate closer to Fish than the control on 46 of 106 core metrics.

## The 15 core metrics furthest from Fish (candidate)

| # | metric | section | Fish | candidate | control | gap |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `camp_deaths` deaths to camps per game | 9-10 combat | 1.17 | 0.254* | 0.312* | 1.53 |
| 2 | `cassi_stun_on_cd` Cassi stuns when her damage spell is on cooldown | 9-10 combat | 99.3% | 49.9%* | 45.7%* | 1.40 |
| 3 | `win` win rate | outcome | 86.2% | 25.8%* | 50.0%* | 1.31 |
| 4 | `keep_rate` recall kept at timer 1 (the last chance to cancel) | 8 economy | 45.0% | 93.4%* | 93.8%* | 1.15 |
| 5 | `bush_tie:enemy` steps onto a bush among equal-progress steps, enemy visible farther | 12 wards and bushes | 88.9% | 46.6%* | 48.0%* | 0.96 |
| 6 | `deaths` deaths per game (bodies; Cassi and Issac die together) | 9-10 combat | 5.15 | 11.1* | 9.16* | 0.76 |
| 7 | `bush_tie:contact` steps onto a bush among equal-progress steps, enemy within 5 | 12 wards and bushes | 83.6% | 50.5%* | 52.0%* | 0.73 |
| 8 | `camp_death_share` share of deaths dealt by camps | 9-10 combat | 22.8% | 2.3%* | 3.4%* | 0.69 |
| 9 | `kills` champion kills per game (bodies) | 9-10 combat | 8.6 | 4.64* | 6.57* | 0.62 |
| 10 | `bush_tie:none` steps onto a bush among equal-progress steps, no enemy | 12 wards and bushes | 74.8% | 49.1%* | 49.8%* | 0.54 |
| 11 | `keep_rule` timer-1 keep rule agreement (capturing: h<=0.40; payout round: h<=0.63; else h<=0.63 or gold>=30) | 8 economy | 90.0% | 99.4%* | 50.1%* | 0.48 |
| 12 | `gold600` team gold earned by round 600 | outcome | 4,354 | 2,766* | 3,287* | 0.45 |
| 13 | `gems600` tributed gems by round 600 | outcome | 576 | 368* | 399* | 0.45 |
| 14 | `solo_clear:Golem` Fish-only Golem clears done solo | 7.1/7.5 farming | 2.3% | 13.3%~ | 22.1%* | 0.45 |
| 15 | `basic_minehp` basic attack target = min EHP (2+ enemy champions in range) | 9-10 combat | 94.0% | 79.4%* | 79.3%* | 0.45 |

## All metrics

`ref`: FISH_MODEL.md's own figure, where it gives one (its definitions can differ slightly). `*`: beyond 2 bootstrap SE of Fish; `~`: within. gap: effect size against Fish.

### 6 turn budget

| metric | ref | Fish | n | candidate | gap | control | gap | ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `budget:dead` share of turns: dead | 8.5% | 6.5% | 1910811 | 12.5%* | 0.21 | 10.5%* | 0.15 | 1.43 |
| `budget:home` share of turns: on own spawn | 3.1% | 3.1% | 1910811 | 2.1%* | 0.07 | 2.6%~ | 0.03 | 2.02 |
| `budget:tribute` share of turns: tribute channel or attempt | 2.8% | 3.0% | 1910811 | 2.0%* | 0.06 | 2.6%* | 0.03 | 2.45 |
| `budget:fight` share of turns: an action on an enemy champion | 3.0% | 2.7% | 1910811 | 3.1%* | 0.03 | 3.2%* | 0.03 | 0.87 |
| `budget:clear` share of turns: hitting a camp | 20.9% | 21.9% | 1910811 | 17.8%* | 0.10 | 16.7%* | 0.13 | 0.79 |
| `budget:capture` share of turns: on an empty group (capture) | 4.7% | 5.6% | 1910811 | 6.1%~ | 0.02 | 6.4%~ | 0.04 | 0.62 |
| `budget:recall` share of turns: keeping a recall channel | 6.7% | 6.4% | 1910811 | 5.4%* | 0.04 | 5.4%* | 0.04 | 1.02 |
| `budget:wait` share of turns: within 2 of a respawning group | 7.9% | 8.7% | 1910811 | 8.7%~ | 0.00 | 9.1%~ | 0.01 | 0.01 |
| `budget:approach` share of turns: walking within 3 of a living camp | 7.0% | 7.4% | 1910811 | 7.5%~ | 0.01 | 7.4%~ | 0.00 | 2.94 |
| `budget:travel` share of turns: other walking | 34.6% | 34.3% | 1910811 | 32.8%~ | 0.03 | 33.9%~ | 0.01 | 3.22 |
| `budget:idle` share of turns: idle | 0.8% | 0.6% | 1910811 | 2.0%* | 0.13 | 2.2%* | 0.15 | 0.89 |

### 6 turn budget by champion

| metric | ref | Fish | n | candidate | gap | control | gap | ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `budget:dead:Marcella` Marcella: dead |  | 5.3% | 213198 | 10.4%* | 0.19 | 8.9%* | 0.14 | 1.35 |
| `budget:home:Marcella` Marcella: on own spawn |  | 2.7% | 213198 | 2.7%~ | 0.00 | 2.8%~ | 0.01 | 0.36 |
| `budget:tribute:Marcella` Marcella: tribute channel or attempt | 5.7% | 6.6% | 213198 | 3.1%* | 0.17 | 3.7%* | 0.13 | 1.28 |
| `budget:fight:Marcella` Marcella: an action on an enemy champion |  | 4.2% | 213198 | 4.1%~ | 0.01 | 5.9%* | 0.08 | 0.09 |
| `budget:clear:Marcella` Marcella: hitting a camp | 12.0% | 12.5% | 213198 | 11.6%~ | 0.03 | 12.0%~ | 0.02 | 1.60 |
| `budget:capture:Marcella` Marcella: on an empty group (capture) |  | 6.7% | 213198 | 5.7%~ | 0.04 | 5.4%* | 0.06 | 0.71 |
| `budget:recall:Marcella` Marcella: keeping a recall channel |  | 7.6% | 213198 | 6.8%* | 0.03 | 6.8%* | 0.03 | 1.05 |
| `budget:wait:Marcella` Marcella: within 2 of a respawning group |  | 11.4% | 213198 | 10.1%~ | 0.04 | 10.3%~ | 0.03 | 1.18 |
| `budget:approach:Marcella` Marcella: walking within 3 of a living camp |  | 8.1% | 213198 | 9.3%~ | 0.04 | 9.0%~ | 0.03 | 1.23 |
| `budget:travel:Marcella` Marcella: other walking |  | 34.6% | 213198 | 35.6%~ | 0.02 | 34.4%~ | 0.00 | 6.19 |
| `budget:idle:Marcella` Marcella: idle |  | 0.3% | 213198 | 0.6%* | 0.06 | 0.7%* | 0.06 | 0.91 |
| `budget:dead:Vesper` Vesper: dead |  | 4.2% | 181679 | 8.1%* | 0.16 | 3.9%~ | 0.01 | 11.85 |
| `budget:home:Vesper` Vesper: on own spawn | 5.7% | 5.6% | 181679 | 2.3%* | 0.17 | 3.2%* | 0.12 | 1.45 |
| `budget:tribute:Vesper` Vesper: tribute channel or attempt | 7.0% | 6.5% | 181679 | 3.6%* | 0.13 | 4.1%* | 0.11 | 1.24 |
| `budget:fight:Vesper` Vesper: an action on an enemy champion |  | 3.0% | 181679 | 4.0%* | 0.06 | 4.9%* | 0.10 | 0.57 |
| `budget:clear:Vesper` Vesper: hitting a camp |  | 21.8% | 181679 | 18.5%* | 0.08 | 16.3%* | 0.14 | 0.58 |
| `budget:capture:Vesper` Vesper: on an empty group (capture) |  | 7.5% | 181679 | 7.7%~ | 0.01 | 9.3%~ | 0.06 | 0.08 |
| `budget:recall:Vesper` Vesper: keeping a recall channel |  | 6.6% | 181679 | 6.8%~ | 0.01 | 6.0%~ | 0.03 | 0.23 |
| `budget:wait:Vesper` Vesper: within 2 of a respawning group |  | 8.9% | 181679 | 9.9%~ | 0.03 | 9.9%~ | 0.03 | 0.98 |
| `budget:approach:Vesper` Vesper: walking within 3 of a living camp |  | 5.2% | 181679 | 6.9%* | 0.07 | 6.6%* | 0.06 | 1.19 |
| `budget:travel:Vesper` Vesper: other walking |  | 29.4% | 181679 | 29.4%~ | 0.00 | 32.3%~ | 0.06 | 0.01 |
| `budget:idle:Vesper` Vesper: idle |  | 1.2% | 181679 | 2.9%* | 0.12 | 3.6%* | 0.16 | 0.78 |
| `budget:dead:Vendetta` Vendetta: dead |  | 4.6% | 280104 | 9.9%* | 0.21 | 5.9%~ | 0.06 | 3.51 |
| `budget:home:Vendetta` Vendetta: on own spawn |  | 2.2% | 280104 | 2.1%~ | 0.01 | 2.2%~ | 0.00 | 3.15 |
| `budget:tribute:Vendetta` Vendetta: tribute channel or attempt |  | 4.4% | 280104 | 2.9%* | 0.09 | 3.4%* | 0.05 | 1.61 |
| `budget:fight:Vendetta` Vendetta: an action on an enemy champion |  | 2.6% | 280104 | 3.0%~ | 0.02 | 1.8%* | 0.05 | 0.46 |
| `budget:clear:Vendetta` Vendetta: hitting a camp |  | 21.7% | 280104 | 17.8%* | 0.10 | 18.1%* | 0.09 | 1.10 |
| `budget:capture:Vendetta` Vendetta: on an empty group (capture) |  | 7.2% | 280104 | 6.6%~ | 0.02 | 6.2%* | 0.04 | 0.56 |
| `budget:recall:Vendetta` Vendetta: keeping a recall channel |  | 7.1% | 280104 | 6.7%~ | 0.01 | 6.0%* | 0.04 | 0.32 |
| `budget:wait:Vendetta` Vendetta: within 2 of a respawning group |  | 8.3% | 280104 | 8.1%~ | 0.01 | 7.1%~ | 0.05 | 0.20 |
| `budget:approach:Vendetta` Vendetta: walking within 3 of a living camp |  | 8.0% | 280104 | 7.7%~ | 0.01 | 6.6%* | 0.06 | 0.20 |
| `budget:travel:Vendetta` Vendetta: other walking |  | 33.1% | 280104 | 33.1%~ | 0.00 | 40.4%* | 0.15 | 0.00 |
| `budget:idle:Vendetta` Vendetta: idle |  | 0.7% | 280104 | 2.2%* | 0.12 | 2.4%* | 0.14 | 0.89 |
| `budget:dead:HoR` HoR: dead |  | 5.2% | 324354 | 11.7%* | 0.24 | 8.6%* | 0.13 | 1.77 |
| `budget:home:HoR` HoR: on own spawn |  | 3.5% | 324354 | 1.7%* | 0.12 | 1.6%* | 0.13 | 0.92 |
| `budget:tribute:HoR` HoR: tribute channel or attempt |  | 2.6% | 324354 | 2.1%* | 0.03 | 2.5%~ | 0.01 | 5.85 |
| `budget:fight:HoR` HoR: an action on an enemy champion |  | 3.3% | 324354 | 5.1%* | 0.09 | 7.0%* | 0.17 | 0.54 |
| `budget:clear:HoR` HoR: hitting a camp |  | 23.4% | 324354 | 18.7%* | 0.12 | 16.7%* | 0.17 | 0.69 |
| `budget:capture:HoR` HoR: on an empty group (capture) |  | 6.2% | 324354 | 6.5%~ | 0.01 | 5.4%* | 0.03 | 0.30 |
| `budget:recall:HoR` HoR: keeping a recall channel |  | 6.4% | 324354 | 6.0%~ | 0.02 | 5.7%* | 0.03 | 0.61 |
| `budget:wait:HoR` HoR: within 2 of a respawning group |  | 8.0% | 324354 | 8.1%~ | 0.00 | 6.9%~ | 0.04 | 0.09 |
| `budget:approach:HoR` HoR: walking within 3 of a living camp |  | 7.4% | 324354 | 7.4%~ | 0.00 | 6.9%~ | 0.02 | 0.12 |
| `budget:travel:HoR` HoR: other walking |  | 33.3% | 324354 | 30.5%~ | 0.06 | 36.3%~ | 0.06 | 0.96 |
| `budget:idle:HoR` HoR: idle |  | 0.7% | 324354 | 2.2%* | 0.13 | 2.5%* | 0.15 | 0.86 |
| `budget:dead:Cassi` Cassi: dead |  | 9.2% | 342127 | 17.5%* | 0.25 | 15.6%* | 0.20 | 1.26 |
| `budget:home:Cassi` Cassi: on own spawn |  | 3.1% | 342127 | 2.2%* | 0.06 | 2.5%~ | 0.04 | 1.60 |
| `budget:tribute:Cassi` Cassi: tribute channel or attempt |  | 1.4% | 342127 | 0.9%* | 0.05 | 1.2%~ | 0.02 | 2.81 |
| `budget:fight:Cassi` Cassi: an action on an enemy champion |  | 2.3% | 342127 | 2.4%~ | 0.01 | 2.3%~ | 0.00 | 2.75 |
| `budget:clear:Cassi` Cassi: hitting a camp |  | 23.2% | 342127 | 16.6%* | 0.17 | 16.8%* | 0.16 | 1.03 |
| `budget:capture:Cassi` Cassi: on an empty group (capture) |  | 3.9% | 342127 | 4.6%~ | 0.03 | 4.0%~ | 0.00 | 9.56 |
| `budget:recall:Cassi` Cassi: keeping a recall channel |  | 5.0% | 342127 | 3.3%* | 0.09 | 4.0%* | 0.05 | 1.82 |
| `budget:wait:Cassi` Cassi: within 2 of a respawning group |  | 8.8% | 342127 | 8.4%~ | 0.01 | 8.6%~ | 0.01 | 1.70 |
| `budget:approach:Cassi` Cassi: walking within 3 of a living camp |  | 6.7% | 342127 | 6.8%~ | 0.01 | 7.0%~ | 0.01 | 0.51 |
| `budget:travel:Cassi` Cassi: other walking |  | 36.1% | 342127 | 34.5%~ | 0.04 | 35.5%~ | 0.01 | 2.85 |
| `budget:idle:Cassi` Cassi: idle |  | 0.2% | 342127 | 2.9%* | 0.24 | 2.5%* | 0.22 | 1.12 |
| `budget:dead:Issac` Issac: dead |  | 9.2% | 342127 | 17.5%* | 0.25 | 15.6%* | 0.20 | 1.26 |
| `budget:home:Issac` Issac: on own spawn |  | 3.4% | 342127 | 1.9%* | 0.09 | 2.2%* | 0.07 | 1.31 |
| `budget:tribute:Issac` Issac: tribute channel or attempt |  | 1.1% | 342127 | 1.2%~ | 0.01 | 1.5%* | 0.03 | 0.22 |
| `budget:fight:Issac` Issac: an action on an enemy champion |  | 2.1% | 342127 | 2.1%~ | 0.00 | 1.8%* | 0.02 | 0.04 |
| `budget:clear:Issac` Issac: hitting a camp |  | 23.4% | 342127 | 19.8%* | 0.09 | 18.4%* | 0.12 | 0.71 |
| `budget:capture:Issac` Issac: on an empty group (capture) |  | 4.6% | 342127 | 5.8%~ | 0.05 | 5.6%* | 0.04 | 1.17 |
| `budget:recall:Issac` Issac: keeping a recall channel |  | 6.7% | 342127 | 5.3%* | 0.06 | 6.1%* | 0.02 | 2.37 |
| `budget:wait:Issac` Issac: within 2 of a respawning group |  | 7.3% | 342127 | 7.9%~ | 0.02 | 8.3%~ | 0.04 | 0.62 |
| `budget:approach:Issac` Issac: walking within 3 of a living camp |  | 8.3% | 342127 | 7.7%~ | 0.02 | 8.0%~ | 0.01 | 2.50 |
| `budget:travel:Issac` Issac: other walking |  | 33.4% | 342127 | 29.2%* | 0.09 | 30.6%~ | 0.06 | 1.53 |
| `budget:idle:Issac` Issac: idle |  | 0.5% | 342127 | 1.6%* | 0.11 | 1.8%* | 0.13 | 0.86 |
| `budget:dead:Willow` Willow: dead |  | 4.6% | 183121 | 6.5%* | 0.08 | 9.5%* | 0.19 | 0.41 |
| `budget:home:Willow` Willow: on own spawn |  | 1.8% | 183121 | 2.0%~ | 0.01 | 3.4%~ | 0.10 | 0.14 |
| `budget:tribute:Willow` Willow: tribute channel or attempt |  | 0.7% | 183121 | 1.6%* | 0.08 | 1.8%* | 0.10 | 0.82 |
| `budget:fight:Willow` Willow: an action on an enemy champion |  | 1.4% | 183121 | 1.1%~ | 0.02 | 1.2%~ | 0.02 | 1.31 |
| `budget:clear:Willow` Willow: hitting a camp |  | 27.9% | 183121 | 22.8%* | 0.12 | 20.4%* | 0.18 | 0.67 |
| `budget:capture:Willow` Willow: on an empty group (capture) |  | 2.4% | 183121 | 6.3%* | 0.20 | 4.3%* | 0.11 | 1.87 |
| `budget:recall:Willow` Willow: keeping a recall channel |  | 5.9% | 183121 | 4.0%* | 0.09 | 3.7%* | 0.10 | 0.84 |
| `budget:wait:Willow` Willow: within 2 of a respawning group |  | 8.2% | 183121 | 8.7%~ | 0.02 | 10.0%~ | 0.06 | 0.30 |
| `budget:approach:Willow` Willow: walking within 3 of a living camp |  | 7.5% | 183121 | 6.9%~ | 0.02 | 7.4%~ | 0.00 | 6.81 |
| `budget:travel:Willow` Willow: other walking | 39.9% | 39.1% | 183121 | 38.9%~ | 0.00 | 35.6%~ | 0.07 | 0.07 |
| `budget:idle:Willow` Willow: idle |  | 0.5% | 183121 | 1.1%* | 0.08 | 2.7%* | 0.19 | 0.39 |
| `budget:dead:Prism` Prism: dead |  | 5.2% | 11298 | 12.5%~ | 0.26 | 8.3%~ | 0.12 | 2.10 |
| `budget:home:Prism` Prism: on own spawn |  | 1.2% | 11298 | 1.1%~ | 0.01 | 3.0%* | 0.13 | 0.05 |
| `budget:tribute:Prism` Prism: tribute channel or attempt |  | 4.6% | 11298 | 3.2%~ | 0.07 | 3.8%~ | 0.04 | 1.82 |
| `budget:fight:Prism` Prism: an action on an enemy champion |  | 2.7% | 11298 | 2.5%~ | 0.01 | 2.2%~ | 0.03 | 0.30 |
| `budget:clear:Prism` Prism: hitting a camp |  | 6.7% | 11298 | 5.7%~ | 0.04 | 17.2%* | 0.33 | 0.13 |
| `budget:capture:Prism` Prism: on an empty group (capture) |  | 18.2% | 11298 | 15.1%~ | 0.08 | 7.8%* | 0.31 | 0.26 |
| `budget:recall:Prism` Prism: keeping a recall channel |  | 2.2% | 11298 | 2.0%~ | 0.02 | 4.9%* | 0.14 | 0.11 |
| `budget:wait:Prism` Prism: within 2 of a respawning group |  | 17.5% | 11298 | 15.2%~ | 0.06 | 10.9%* | 0.19 | 0.32 |
| `budget:approach:Prism` Prism: walking within 3 of a living camp |  | 1.7% | 11298 | 2.9%~ | 0.08 | 7.1%* | 0.28 | 0.29 |
| `budget:travel:Prism` Prism: other walking |  | 38.7% | 11298 | 38.0%~ | 0.01 | 32.4%~ | 0.13 | 0.10 |
| `budget:idle:Prism` Prism: idle |  | 1.4% | 11298 | 1.7%~ | 0.02 | 2.3%* | 0.07 | 0.34 |
| `budget:dead:Ren` Ren: dead |  | 8.2% | 29342 | 8.7%~ | 0.02 | 12.3%~ | 0.13 | 0.13 |
| `budget:home:Ren` Ren: on own spawn |  | 1.5% | 29342 | 1.9%~ | 0.03 | 2.0%~ | 0.04 | 0.85 |
| `budget:tribute:Ren` Ren: tribute channel or attempt |  | 0.6% | 29342 | 0.7%~ | 0.01 | 1.8%* | 0.11 | 0.12 |
| `budget:fight:Ren` Ren: an action on an enemy champion |  | 2.4% | 29342 | 6.1%* | 0.19 | 5.3%* | 0.15 | 1.23 |
| `budget:clear:Ren` Ren: hitting a camp |  | 11.3% | 29342 | 11.8%~ | 0.02 | 14.4%* | 0.09 | 0.18 |
| `budget:capture:Ren` Ren: on an empty group (capture) |  | 6.0% | 29342 | 4.7%~ | 0.06 | 5.5%~ | 0.02 | 2.89 |
| `budget:recall:Ren` Ren: keeping a recall channel |  | 5.0% | 29342 | 5.4%~ | 0.02 | 5.7%~ | 0.03 | 0.55 |
| `budget:wait:Ren` Ren: within 2 of a respawning group |  | 9.0% | 29342 | 9.9%~ | 0.03 | 8.3%~ | 0.03 | 1.26 |
| `budget:approach:Ren` Ren: walking within 3 of a living camp |  | 7.1% | 29342 | 6.5%~ | 0.03 | 7.2%~ | 0.00 | 25.68 |
| `budget:travel:Ren` Ren: other walking |  | 48.0% | 29342 | 41.3%~ | 0.14 | 34.8%* | 0.27 | 0.50 |
| `budget:idle:Ren` Ren: idle |  | 0.8% | 29342 | 3.0%* | 0.17 | 2.8%* | 0.15 | 1.08 |

### 7.1 grouping and space

| metric | ref | Fish | n | candidate | gap | control | gap | ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `nearest_ally` nearest alive off-spawn ally, median Chebyshev tiles | 2 | 3 | 1720223 | 4 | 0.29 | 4 | 0.29 | 1.00 |
| `ally_within4` nearest ally within 4 (off-spawn turns with another ally off spawn) | 67.0% | 65.7% | 1720223 | 53.6%* | 0.25 | 55.4%* | 0.21 | 1.16 |
| `centroid_spread` mean Chebyshev distance of off-spawn bodies to the team centroid (rounds with 2+) |  | 8.02 | 342346 | 8.98* | 0.11 | 8.69~ | 0.08 | 1.41 |
| `pair_dist` mean pairwise Chebyshev distance of off-spawn bodies |  | 12.1 | 342346 | 14* | 0.14 | 13.5* | 0.10 | 1.34 |
| `team_within8` every off-spawn body within 8 of the centroid |  | 31.8% | 342346 | 29.8%~ | 0.04 | 31.4%~ | 0.01 | 5.41 |
| `side_own` off-spawn turns on own half (walk-distance territory) | 69.0% | 67.4% | 1727537 | 71.5%* | 0.09 | 72.3%* | 0.11 | 0.83 |
| `side_mid` off-spawn turns in the middle | 22.0% | 23.2% | 1727537 | 20.4%~ | 0.07 | 19.6%* | 0.09 | 0.77 |
| `side_enemy` off-spawn turns on the enemy half | 9.0% | 9.4% | 1727537 | 8.1%~ | 0.05 | 8.1%~ | 0.05 | 1.00 |
| `pay_own` payouts on own side | 77.0% | 79.9% | 22432 | 79.9%~ | 0.00 | 78.8%~ | 0.03 | 0.03 |
| `pay_middle` payouts in the middle | 16.0% | 12.3% | 22432 | 11.5%~ | 0.02 | 11.7%~ | 0.02 | 1.39 |
| `pay_enemy` payouts on the enemy side | 7.0% | 7.8% | 22432 | 8.6%~ | 0.03 | 9.4%~ | 0.06 | 0.51 |

### 7.1/7.5 farming

| metric | ref | Fish | n | candidate | gap | control | gap | ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `pay1k` payouts per 1,000 rounds per champion-game, median |  | 9.9 | 2262 | 9.3 | 0.06 | 10.9 | 0.10 | 0.65 |
| `pay1k_mean` payouts per 1,000 rounds per champion-game, mean |  | 13 | 2262 | 10.8* | 0.19 | 12.3~ | 0.05 | 3.53 |
| `pay_single` payouts with a single recipient | 92.0% | 93.6% | 22432 | 97.8%* | 0.21 | 96.3%* | 0.12 | 1.73 |
| `pay_groups` distinct payout groups per champion-game |  | 5.41 | 2262 | 5.08~ | 0.06 | 5.49~ | 0.02 | 4.15 |
| `solo_clear:Wolf` Fish-only Wolf-led clears done solo |  | 30.0% | 5983 | 39.5%* | 0.20 | 40.3%* | 0.22 | 0.93 |
| `solo_clear:Elk` Fish-only Elk-led clears done solo | 8.2% | 9.7% | 4228 | 24.0%* | 0.39 | 28.4%* | 0.49 | 0.79 |
| `solo_clear:Golem` Fish-only Golem clears done solo | 1.4% | 2.3% | 310 | 13.3%~ | 0.45 | 22.1%* | 0.68 | 0.66 |
| `solo_clear:Monolith` Fish-only Monolith clears done solo | 6.0% | 5.4% | 92 | n/a |  | n/a |  |  |
| `wake_alone` waker of a fully asleep group has no other body within 4 of the group |  | 60.9% | 29713 | 68.9%* | 0.17 | 68.2%* | 0.15 | 1.10 |
| `wake_alone:Elk` waker alone: Elk groups | 51.0% | 54.1% | 7175 | 62.4%* | 0.17 | 63.4%* | 0.19 | 0.89 |
| `wake_alone:Golem` waker alone: Golem groups | 53.0% | 63.3% | 1334 | 64.5%~ | 0.03 | 69.4%~ | 0.13 | 0.19 |
| `wake_alone:Wolf` waker alone: Wolf groups | 55.0% | 61.2% | 9416 | 70.8%* | 0.20 | 70.3%* | 0.19 | 1.06 |

### 7.1 farming by champion

| metric | ref | Fish | n | candidate | gap | control | gap | ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `pay1k:Marcella` Marcella: payouts per 1,000 rounds, median | 16.7 | 18.6 | 248 | 11.5 | 0.48 | 12.6 | 0.39 | 1.23 |
| `pay_groups:Marcella` Marcella: distinct payout groups per game |  | 6.47 | 248 | 5.05* | 0.25 | 5.76~ | 0.12 | 2.13 |
| `pay1k:Vesper` Vesper: payouts per 1,000 rounds, median | 22 | 23.3 | 198 | 15.3 | 0.42 | 16.1 | 0.37 | 1.14 |
| `pay_groups:Vesper` Vesper: distinct payout groups per game |  | 7.98 | 198 | 6.93* | 0.14 | 7.09~ | 0.12 | 1.19 |
| `pay1k:Vendetta` Vendetta: payouts per 1,000 rounds, median | 17.6 | 18.1 | 337 | 11.9 | 0.42 | 13.3 | 0.31 | 1.36 |
| `pay_groups:Vendetta` Vendetta: distinct payout groups per game |  | 7.41 | 337 | 6.08* | 0.20 | 6.63* | 0.11 | 1.77 |
| `pay1k:HoR` HoR: payouts per 1,000 rounds, median | 10.4 | 11 | 383 | 10.1 | 0.09 | 10 | 0.10 | 0.90 |
| `pay_groups:HoR` HoR: distinct payout groups per game |  | 5.99 | 383 | 5.57~ | 0.07 | 5.72~ | 0.05 | 1.56 |
| `pay1k:Cassi` Cassi: payouts per 1,000 rounds, median | 5.8 | 6.1 | 406 | 5 | 0.20 | 6.1 | 0.00 |  |
| `pay_groups:Cassi` Cassi: distinct payout groups per game |  | 4.27 | 406 | 3.47* | 0.21 | 3.95~ | 0.08 | 2.66 |
| `pay1k:Issac` Issac: payouts per 1,000 rounds, median | 4.8 | 4.8 | 406 | 7.5 | 0.45 | 8.7 | 0.59 | 0.75 |
| `pay_groups:Issac` Issac: distinct payout groups per game |  | 3.71 | 406 | 4.43* | 0.18 | 5.05* | 0.31 | 0.58 |
| `pay1k:Willow` Willow: payouts per 1,000 rounds, median | 3.1 | 2.8 | 241 | 8.6 | 1.12 | 9.7 | 1.24 | 0.90 |
| `pay_groups:Willow` Willow: distinct payout groups per game |  | 2.71 | 241 | 5.01* | 0.61 | 5.15* | 0.64 | 0.96 |
| `pay1k:Prism` Prism: payouts per 1,000 rounds, median |  | 49.5 | 18 | 15.1 | 1.19 | 15.3 | 1.17 | 1.01 |
| `pay_groups:Prism` Prism: distinct payout groups per game |  | 10.3 | 18 | 7.71~ | 0.29 | 6.12* | 0.52 | 0.56 |
| `pay1k:Ren` Ren: payouts per 1,000 rounds, median |  | 5.4 | 19 | n/a |  | 8.1 | 0.41 |  |
| `pay_groups:Ren` Ren: distinct payout groups per game |  | 7.16 | 19 | n/a |  | 6.08~ | 0.16 |  |

### 8 economy

| metric | ref | Fish | n | candidate | gap | control | gap | ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `spent` gold spent per champion-game (engine statistics) |  | 1,110 | 2262 | 763* | 0.37 | 917* | 0.19 | 1.96 |
| `shards` shards bought per champion-game |  | 36.5 | 2262 | 25.1* | 0.38 | 29.9* | 0.20 | 1.89 |
| `has_emblem` champion-games with an emblem |  | 78.4% | 2262 | 82.8%* | 0.11 | 85.7%* | 0.19 | 0.57 |
| `first_emblem` round of the first emblem, median (champions with one; 10-round bins) |  | 200 | 1774 | 210 | 0.05 | 200 | 0.00 |  |
| `trib_bag` gems carried at a tribute start, median |  | 26 | 10420 | 21 | 0.21 | 21 | 0.21 | 1.00 |
| `tribute_start` tribute starts per free off-spawn turn |  | 0.6% | 1664748 | 0.6%~ | 0.01 | 0.6%~ | 0.00 | 3.91 |
| `recall_start` recall started on free turns ending off spawn with no channel running (prepared recall) | 100.0% | 100.0% | 1495719 | 99.7%* | 0.10 | 99.5%* | 0.13 | 0.74 |
| `recall_survive` a recall started on a free turn still running after the next turn | 3.8% | 4.6% | 1272849 | 1.4%* | 0.20 | 1.9%* | 0.16 | 1.28 |
| `keep_rate` recall kept at timer 1 (the last chance to cancel) |  | 45.0% | 36468 | 93.4%* | 1.15 | 93.8%* | 1.17 | 0.99 |
| `keep_rule` timer-1 keep rule agreement (capturing: h<=0.40; payout round: h<=0.63; else h<=0.63 or gold>=30) | 90.6% | 90.0% | 36468 | 99.4%* | 0.48 | 50.1%* | 0.92 | 0.52 |
| `home_gate` home gate (h<=0.63 or gold>=30) holds at a completed recall | 98.6% | 98.3% | 16406 | 99.4%* | 0.10 | 63.9%* | 1.03 | 0.10 |
| `home_reason_hurt` completed recalls with h<=0.63 | 51.5% | 49.2% | 16406 | 55.2%* | 0.12 | 41.6%* | 0.15 | 0.78 |

### 8 economy by champion

| metric | ref | Fish | n | candidate | gap | control | gap | ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `spent:Marcella` Marcella: gold spent per game | 2,318 | 2,609 | 248 | 1,197* | 0.78 | 1,264* | 0.72 | 1.08 |
| `shards:Marcella` Marcella: shards per game | 77 | 86.2 | 248 | 39.3* | 0.79 | 41.1* | 0.74 | 1.06 |
| `first_emblem:Marcella` Marcella: first emblem round, median | 88 | 80 | 246 | 130 | 0.49 | 140 | 0.56 | 0.87 |
| `trib_bag:Marcella` Marcella: tributed bag, median | 33 | 32 | 2365 | 26 | 0.21 | 24 | 0.29 | 0.72 |
| `spent:Vesper` Vesper: gold spent per game | 3,866 | 3,662 | 198 | 2,353* | 0.44 | 2,881* | 0.24 | 1.84 |
| `shards:Vesper` Vesper: shards per game | 128 | 121 | 198 | 77.9* | 0.44 | 95* | 0.24 | 1.82 |
| `first_emblem:Vesper` Vesper: first emblem round, median | 82 | 80 | 196 | 80 | 0.00 | 70 | 0.13 | 0.00 |
| `trib_bag:Vesper` Vesper: tributed bag, median | 57 | 36 | 1392 | 27 | 0.29 | 31 | 0.15 | 1.92 |
| `spent:Vendetta` Vendetta: gold spent per game | 1,475 | 1,530 | 337 | 1,039* | 0.39 | 1,359~ | 0.12 | 3.28 |
| `shards:Vendetta` Vendetta: shards per game | 49 | 50.4 | 337 | 34.2* | 0.39 | 44.6~ | 0.12 | 3.16 |
| `first_emblem:Vendetta` Vendetta: first emblem round, median | 140 | 130 | 332 | 180 | 0.33 | 160 | 0.21 | 1.57 |
| `trib_bag:Vendetta` Vendetta: tributed bag, median | 36 | 32 | 2116 | 23 | 0.33 | 23 | 0.33 | 1.00 |
| `spent:HoR` HoR: gold spent per game | 790 | 829 | 383 | 711* | 0.15 | 691~ | 0.18 | 0.84 |
| `shards:HoR` HoR: shards per game | 26 | 27.2 | 383 | 23.3* | 0.15 | 22.3~ | 0.20 | 0.78 |
| `first_emblem:HoR` HoR: first emblem round, median | 245 | 220 | 353 | 190 | 0.15 | 230 | 0.04 | 3.30 |
| `trib_bag:HoR` HoR: tributed bag, median | 28 | 25 | 1762 | 23 | 0.08 | 23 | 0.08 | 1.00 |
| `spent:Cassi` Cassi: gold spent per game | 325 | 354 | 406 | 240* | 0.39 | 304~ | 0.15 | 2.52 |
| `shards:Cassi` Cassi: shards per game | 10.5 | 11.5 | 406 | 7.75* | 0.39 | 9.73~ | 0.17 | 2.38 |
| `first_emblem:Cassi` Cassi: first emblem round, median | 418 | 360 | 280 | 410 | 0.13 | 410 | 0.13 | 1.00 |
| `trib_bag:Cassi` Cassi: tributed bag, median | 20 | 18 | 1234 | 14 | 0.25 | 14 | 0.25 | 1.00 |
| `spent:Issac` Issac: gold spent per game | 260 | 247 | 406 | 370* | 0.40 | 462* | 0.62 | 0.65 |
| `shards:Issac` Issac: shards per game | 8.3 | 7.94 | 406 | 12* | 0.42 | 14.8* | 0.62 | 0.67 |
| `first_emblem:Issac` Issac: first emblem round, median | 414 | 400 | 250 | 310 | 0.25 | 290 | 0.32 | 0.79 |
| `trib_bag:Issac` Issac: tributed bag, median | 17 | 17 | 1041 | 14 | 0.19 | 14 | 0.19 | 1.00 |
| `spent:Willow` Willow: gold spent per game | 135 | 151 | 241 | 401* | 0.97 | 388* | 0.94 | 1.03 |
| `shards:Willow` Willow: shards per game | 4.3 | 4.86 | 241 | 13* | 0.99 | 12.5* | 0.95 | 1.04 |
| `first_emblem:Willow` Willow: first emblem round, median | 453 | 380 | 90 | 270 | 0.34 | 280 | 0.31 | 1.12 |
| `trib_bag:Willow` Willow: tributed bag, median | 14 | 14 | 369 | 17 | 0.19 | 21 | 0.41 | 0.48 |
| `spent:Prism` Prism: gold spent per game |  | 148 | 18 | 134~ | 0.10 | 1,067* | 1.97 | 0.05 |
| `shards:Prism` Prism: shards per game |  | 4.72 | 18 | 4.29~ | 0.10 | 35.1* | 2.00 | 0.05 |
| `first_emblem:Prism` Prism: first emblem round, median |  | n/a | 5 | n/a |  | 190 |  |  |
| `trib_bag:Prism` Prism: tributed bag, median |  | 245 | 30 | 778 | 1.16 | 448 | 0.60 | 1.91 |
| `spent:Ren` Ren: gold spent per game |  | 1,007 | 19 | n/a |  | 752~ | 0.29 |  |
| `shards:Ren` Ren: shards per game |  | 32.8 | 19 | n/a |  | 24.5~ | 0.29 |  |
| `first_emblem:Ren` Ren: first emblem round, median |  | 270 | 16 | n/a |  | 230 | 0.16 |  |
| `trib_bag:Ren` Ren: tributed bag, median |  | 8 | 62 | 8 | 0.00 | 18 | 0.81 | 0.00 |

### 5 priority

| metric | ref | Fish | n | candidate | gap | control | gap | ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `prio_rank_ok` alive turns whose priority has Fish's rank residue ((-p) mod (N+1) = base-health rank) | 100.0% | 99.9% | 1779637 | 100.0%* | 0.02 | 16.2%* | 2.26 | 0.01 |
| `prio_mode_agree` priority mode agrees with the selector (dead / late / contact / quiet), alive unstunned |  | 98.3% | 1779637 | 99.4%* | 0.11 | 1.1%* | 2.67 | 0.04 |
| `prio_quiet_exact` quiet-predicted turns with the exact quiet value -rank-(N+1)*band |  | 98.7% | 1659118 | 99.6%* | 0.10 | 0.0%* | 2.91 | 0.04 |
| `prio_dead_ok` dead turns with the dead level (L = -1) | 100.0% | 100.0% | 123049 | 100.0%~ | 0.00 | 0.0%* | 3.14 | 0.00 |
| `prio_write_repeat` priority writes that repeat the current value | 0.0% | 0.0% | 202251 | 0.0%~ | 0.00 | 0.0%~ | 0.00 |  |
| `prio_mode:quiet` alive turns in priority mode quiet |  | 92.3% | 1779637 | 89.8%* | 0.09 | 0.0%* | 2.58 | 0.03 |
| `prio_mode:late` alive turns in priority mode late |  | 2.3% | 1779637 | 2.9%~ | 0.04 | 0.0%* | 0.30 | 0.12 |
| `prio_mode:contact` alive turns in priority mode contact |  | 4.8% | 1779637 | 7.3%* | 0.10 | 16.2%* | 0.38 | 0.27 |
| `prio_mode:early` alive turns in priority mode early |  | 0.5% | 1779637 | 0.0%* | 0.14 | 0.0%* | 0.14 | 1.00 |
| `prio_mode:other` alive turns in priority mode other |  | 0.0% | 1779637 | 0.0%~ | 0.00 | 83.8%* | 2.31 | 0.00 |
| `prio_mode:unset` alive turns in priority mode unset |  | 0.1% | 1779637 | 0.0%* | 0.02 | 0.0%* | 0.03 | 0.83 |

### 9-10 combat

| metric | ref | Fish | n | candidate | gap | control | gap | ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `kills` champion kills per game (bodies) |  | 8.6 | 412 | 4.64* | 0.62 | 6.57* | 0.27 | 2.29 |
| `deaths` deaths per game (bodies; Cassi and Issac die together) |  | 5.15 | 412 | 11.1* | 0.76 | 9.16* | 0.58 | 1.33 |
| `camp_deaths` deaths to camps per game |  | 1.17 | 412 | 0.254* | 1.53 | 0.312* | 1.32 | 1.16 |
| `camp_death_share` share of deaths dealt by camps |  | 22.8% | 2123 | 2.3%* | 0.69 | 3.4%* | 0.62 | 1.11 |
| `enemy_in_sight` alive turns with an enemy champion in sight at turn start |  | 22.6% | 1786770 | 33.5%* | 0.24 | 31.9%* | 0.21 | 1.16 |
| `contact_hit` free turns with an enemy within 3 that hit an enemy champion |  | 53.8% | 70792 | 49.0%* | 0.10 | 51.7%* | 0.04 | 2.29 |
| `engage_rule` positioning rule agreement (10.1: kill available, or h>0.49 and danger<=0.28) | 73.6% | 73.9% | 44497 | 66.8%* | 0.16 | 67.7%* | 0.14 | 1.14 |
| `engage_rule:m2` positioning rule, melee at 2 | 73.5% | 73.8% | 15583 | 66.7%* | 0.16 | 66.6%* | 0.16 | 0.99 |
| `engage_rule:m1` positioning rule, melee adjacent | 74.2% | 74.6% | 15035 | 68.5%* | 0.13 | 69.1%* | 0.12 | 1.11 |
| `engage_rule:r` positioning rule, ranged within 3 | 72.9% | 73.3% | 13879 | 65.1%* | 0.18 | 67.3%* | 0.13 | 1.36 |
| `engage_rate:m2` engages: melee at 2 (ends adjacent or spell-hits) |  | 58.6% | 15583 | 47.5%* | 0.22 | 50.2%* | 0.17 | 1.33 |
| `engage_rate:m1` engages: melee adjacent (stays adjacent) |  | 69.7% | 15035 | 61.7%* | 0.17 | 63.9%* | 0.12 | 1.38 |
| `engage_rate:r` engages: ranged within 3 (does not back off) |  | 62.1% | 13879 | 53.2%* | 0.18 | 60.8%~ | 0.03 | 6.66 |
| `kill_override` engages when a kill is available from an engage tile | 98.7% | 98.4% | 2094 | 90.6%* | 0.37 | 94.8%* | 0.21 | 1.76 |
| `chase_rule` chase rule agreement (10.3) | 73.4% | 73.9% | 14931 | 67.3%* | 0.15 | 65.0%* | 0.19 | 0.76 |
| `chase_rate` chases last turn's target, now nearest and out of basic range | 61.2% | 61.4% | 14931 | 52.7%* | 0.18 | 52.9%* | 0.17 | 1.02 |
| `basic_minehp` basic attack target = min EHP (2+ enemy champions in range) | 93.6% | 94.0% | 5126 | 79.4%* | 0.45 | 79.3%* | 0.45 | 1.00 |
| `basic_champ_first` basic attacks hit a champion when one is in range | 99.9% | 99.9% | 45517 | 99.9%~ | 0.02 | 99.9%~ | 0.01 | 1.32 |
| `reset_use` melee reset after a surviving basic, cast unused | 94.6% | 98.3% | 4922 | 99.9%* | 0.20 | 99.8%* | 0.18 | 1.07 |
| `spell_when_still` exclusive damage spell cast when standing, ready, cast unused | 95.4% | 95.0% | 5840 | 98.0%* | 0.17 | 98.3%* | 0.19 | 0.88 |
| `stand_to_cast` stands still when its exclusive damage spell is ready with an enemy within 4 |  | 56.3% | 10580 | 54.2%~ | 0.04 | 61.0%* | 0.10 | 0.44 |
| `hor_shield_rule` HoR shield iff a visible unstunned enemy threatens it | 93.1% | 93.1% | 33339 | 88.2%* | 0.17 | 88.6%* | 0.16 | 1.09 |
| `cassi_stun_on_cd` Cassi stuns when her damage spell is on cooldown | 98.9% | 99.3% | 1124 | 49.9%* | 1.40 | 45.7%* | 1.49 | 0.94 |
| `momentum` range 4-8: closes iff the previous step continued would close (9) | 70.8% | 70.9% | 197977 | 68.7%* | 0.05 | 67.6%* | 0.07 | 0.67 |
| `range_close` range 4-8 free turns that close on the nearest enemy | 45.5% | 43.5% | 197977 | 40.9%* | 0.05 | 41.6%* | 0.04 | 1.32 |
| `campcont_rule` keeps hitting camps iff nearest enemy > 4 (agreement, enemy in sight) | 80.8% | 79.8% | 31933 | 81.7%* | 0.05 | 80.9%~ | 0.03 | 1.72 |
| `campcont:none` keeps hitting camps, nearest enemy none | 96.0% | 96.1% | 301879 | 97.7%* | 0.09 | 97.2%* | 0.06 | 1.53 |
| `campcont:far` keeps hitting camps, nearest enemy far | 89.1% | 87.7% | 8658 | 96.6%* | 0.35 | 96.5%* | 0.34 | 1.02 |
| `campcont:d8` keeps hitting camps, nearest enemy d8 | 85.3% | 82.7% | 5687 | 86.8%* | 0.11 | 85.6%* | 0.08 | 1.45 |
| `campcont:d7` keeps hitting camps, nearest enemy d7 | 85.5% | 83.7% | 5704 | 85.0%~ | 0.04 | 86.0%* | 0.06 | 0.56 |
| `campcont:d6` keeps hitting camps, nearest enemy d6 | 79.1% | 75.5% | 4934 | 82.0%* | 0.16 | 81.3%* | 0.14 | 1.13 |
| `campcont:d5` keeps hitting camps, nearest enemy d5 | 67.6% | 67.0% | 3631 | 64.1%~ | 0.06 | 63.6%~ | 0.07 | 0.86 |
| `campcont:d4` keeps hitting camps, nearest enemy d4 | 44.8% | 43.2% | 1874 | 52.4%* | 0.18 | 51.3%* | 0.16 | 1.13 |
| `campcont:d1-3` keeps hitting camps, nearest enemy d1-3 | 18.2% | 18.3% | 1445 | 30.2%* | 0.28 | 30.6%* | 0.29 | 0.98 |

### 12 wards and bushes

| metric | ref | Fish | n | candidate | gap | control | gap | ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ward_rate:contact` ward placed, ward ready, enemy within 5 | 8.0% | 8.8% | 87800 | 3.2%* | 0.24 | 3.2%* | 0.24 | 0.99 |
| `ward_rate:enemy` ward placed, ward ready, enemy visible farther | 5.0% | 5.4% | 158032 | 3.3%* | 0.11 | 3.5%* | 0.09 | 1.13 |
| `ward_rate:none` ward placed, ward ready, no enemy visible | 2.9% | 3.0% | 1009741 | 3.7%* | 0.04 | 3.8%* | 0.04 | 0.87 |
| `ward_per_turn` ward placements per alive turn |  | 2.7% | 1779637 | 2.6%~ | 0.00 | 2.7%~ | 0.00 | 2.79 |
| `ward_bush` ward placements on a bush | 78.8% | 83.3% | 48502 | 73.4%* | 0.24 | 73.4%* | 0.24 | 1.01 |
| `ward_d2` ward placements at distance 2 from the placer | 88.7% | 85.7% | 48502 | 89.4%* | 0.11 | 90.8%* | 0.16 | 0.70 |
| `bush_tie:contact` steps onto a bush among equal-progress steps, enemy within 5 | 73.1% | 83.6% | 7216 | 50.5%* | 0.73 | 52.0%* | 0.70 | 1.04 |
| `bush_tie:enemy` steps onto a bush among equal-progress steps, enemy visible farther | 78.3% | 88.9% | 7639 | 46.6%* | 0.96 | 48.0%* | 0.93 | 1.03 |
| `bush_tie:none` steps onto a bush among equal-progress steps, no enemy | 71.1% | 74.8% | 31404 | 49.1%* | 0.54 | 49.8%* | 0.52 | 1.02 |

### outcome

| metric | ref | Fish | n | candidate | gap | control | gap | ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `win` win rate | 77.2% | 86.2% | 412 | 25.8%* | 1.31 | 50.0%* | 0.81 | 1.63 |
| `final_round` round the game ends, mean |  | 860 | 412 | 926* | 0.07 | 929* | 0.08 | 0.96 |
| `reach_2000` games reaching round 2000 | 2.0% | 2.9% | 412 | 2.7%~ | 0.01 | 2.3%~ | 0.04 | 0.30 |
| `gems300` tributed gems by round 300 |  | 185 | 412 | 151* | 0.20 | 150* | 0.21 | 0.94 |
| `gems600` tributed gems by round 600 |  | 576 | 412 | 368* | 0.45 | 399* | 0.37 | 1.22 |
| `gold300` team gold earned by round 300 |  | 1,942 | 412 | 1,297* | 0.40 | 1,473* | 0.28 | 1.46 |
| `gold600` team gold earned by round 600 |  | 4,354 | 412 | 2,766* | 0.45 | 3,287* | 0.28 | 1.61 |

### 9-10 combat by champion

| metric | ref | Fish | n | candidate | gap | control | gap | ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `contact_hit:Marcella` Marcella: contact turns hitting | 52.8% | 53.2% | 13071 | 43.1%* | 0.20 | 48.5%* | 0.09 | 2.14 |
| `enemy_in_sight:Marcella` Marcella: enemy in sight | 38.5% | 30.5% | 201805 | 43.8%* | 0.28 | 43.0%* | 0.26 | 1.06 |
| `contact_hit:Vesper` Vesper: contact turns hitting | 67.4% | 69.9% | 5487 | 60.4%* | 0.20 | 64.5%* | 0.12 | 1.72 |
| `enemy_in_sight:Vesper` Vesper: enemy in sight | 24.6% | 21.5% | 173963 | 32.7%* | 0.25 | 37.4%* | 0.35 | 0.72 |
| `contact_hit:Vendetta` Vendetta: contact turns hitting |  | 49.7% | 12652 | 45.2%* | 0.09 | 44.9%~ | 0.10 | 0.93 |
| `enemy_in_sight:Vendetta` Vendetta: enemy in sight |  | 23.6% | 267069 | 34.4%* | 0.24 | 21.5%~ | 0.05 | 4.61 |
| `contact_hit:HoR` HoR: contact turns hitting |  | 56.9% | 16125 | 56.2%~ | 0.01 | 61.4%* | 0.09 | 0.14 |
| `enemy_in_sight:HoR` HoR: enemy in sight |  | 23.8% | 307452 | 35.8%* | 0.26 | 37.8%* | 0.30 | 0.87 |
| `contact_hit:Cassi` Cassi: contact turns hitting |  | 57.9% | 6122 | 51.2%* | 0.13 | 50.9%* | 0.14 | 0.96 |
| `enemy_in_sight:Cassi` Cassi: enemy in sight |  | 20.0% | 310670 | 29.9%* | 0.23 | 27.1%* | 0.17 | 1.37 |
| `contact_hit:Issac` Issac: contact turns hitting |  | 45.4% | 12771 | 41.3%* | 0.08 | 37.8%* | 0.15 | 0.55 |
| `enemy_in_sight:Issac` Issac: enemy in sight |  | 22.2% | 310619 | 32.5%* | 0.23 | 29.8%* | 0.17 | 1.33 |
| `contact_hit:Willow` Willow: contact turns hitting | 48.3% | 54.4% | 2944 | 36.8%* | 0.36 | 36.0%* | 0.37 | 0.96 |
| `enemy_in_sight:Willow` Willow: enemy in sight | 23.0% | 16.1% | 174519 | 25.7%* | 0.24 | 33.3%* | 0.41 | 0.59 |
| `contact_hit:Prism` Prism: contact turns hitting |  | 61.1% | 296 | 55.1%~ | 0.12 | 59.1%~ | 0.04 | 2.91 |
| `enemy_in_sight:Prism` Prism: enemy in sight |  | 21.3% | 10703 | 29.3%~ | 0.18 | 27.9%~ | 0.15 | 1.20 |
| `contact_hit:Ren` Ren: contact turns hitting |  | 52.1% | 1049 | 56.0%~ | 0.08 | 56.1%~ | 0.08 | 0.96 |
| `enemy_in_sight:Ren` Ren: enemy in sight |  | 22.4% | 26933 | 36.5%~ | 0.31 | 36.5%* | 0.31 | 1.00 |
