# charybdis: merge of the 2026-11-11 macro programme

## 40k-game A/Bs, normal fuel (each best attempt vs bots/ocean on main = variants/ocean-main-b7c87cf)
Suites /home/ubuntu/wt/charybdis-maps/s-700001..700080 (ladder-v2, fresh), both sides, release, own drafts, 2026-11-11 09:42-09:56 UTC.

| Bot (source branch) | Win % | Games | 95% CI | 2x-fuel result (orchestrator) |
|---|---|---|---|---|
| macro1-hold6 (macro1-20261111) | 56.8 | 40960 | 56.3-57.3 | 58.3 of 40960 |
| macro5-hold-sole2 (macro5-20261111) | 56.2 | 40960 | 55.7-56.7 | 57.0 of 39936 |
| macro4-handfc (macro4-20261111) | 55.9 | 40960 | 55.5-56.4 | 56.3 of 39936 |
| macro6-carry3 (macro6-20261111) | 55.3 | 40960 | 54.9-55.8 | 55.8 of 51200 |
| macro3-eoq2 (macro3-20261111) | 52.3 | 40960 | 51.8-52.8 | 53.1 of 30720 |
| macro2-lstep (macro2-20261111) | 50.7 | 40960 | 50.2-51.2 | 50.8 of 71680 |

Base: macro1-hold6 (highest; macro5 within a point but no simpler). bots/charybdis = macro1-hold6; frozen as bots/variants/charybdis-base (gitignored).

## Phase 1 merges (normal fuel, `--no-test-draft`, release; suites s-710001..710040, ladder-v2, 20,480 games each unless noted)
Details in merge-log.md.

| Step | Changes | vs ocean-main | vs charybdis-base | Decision |
|---|---|---|---|---|
| (ref) charybdis-base | - | 56.9 (56.3-57.6) | - | - |
| K1 | M3-a bank floor | 57.9 (57.2-58.6) | 51.1 (50.4-51.7) | accepted |
| K2a | M2-d no lethal camp flight | 58.2 (57.5-58.8) | 51.4 (50.7-52.1) | accepted (bug fix) |
| K2a (40,960, s-710001..080) | (accepted state, both halves) | 58.37 | 51.65 | reference for K2b, K3 |
| K2b (40,960, s-710001..080) | M2-c, M2-a, M2-b | 58.5 (58.0-58.9) | 51.4 (50.9-51.9) | rejected: to CONSIDER |
| K3 (40,960, s-710001..080) | M4-b1 hand-over (rebuilt) | 58.3 (57.9-58.8) | 51.6 (51.1-52.1) | rejected: level with K2a, to CONSIDER |

Phase-1 state: K1 + K2a (commit 3c9b6c294), frozen as bots/variants/charybdis-p1: 58.37 vs ocean-main, 51.65 vs charybdis-base (40,960 each).

## Phase 2 merges (normal fuel, `--no-test-draft`, release; suites s-720001..720080, ladder-v2, 40,960 games each)
Details in merge-log.md. "vs p1" is the candidate against charybdis-p1 directly.

| Step | Changes | vs ocean-main | vs charybdis-base | vs charybdis-p1 | Decision |
|---|---|---|---|---|---|
| (ref) charybdis-p1 | K1 + K2a | 58.61 (58.1-59.1) | 52.21 (51.7-52.7) | - | - |
| C1 | M4-a3 + M4-b2 team-marginal value + gate | 57.69 (57.2-58.2) | 51.35 (50.9-51.8) | 49.31 (48.8-49.8) | rejected: loses |
| C1b | M4-b2 gate alone | 58.73 (58.3-59.2) | 52.35 (51.9-52.8) | 50.06 (49.6-50.5) | rejected: level, fires 0.26/game |
| C3 | M6-bc carried_bonus pricing, swap for gold_part | 59.0 (58.5-59.4) | 52.3 (51.8-52.7) | 50.3 (49.8-50.8) | extended |
| C3 (81,920, s-720001..160) | same; p1 there: 58.68 / 51.96 | 59.06 | 52.14 | 50.31 (49.97-50.65) | rejected: level; fuel-optimization candidate |
| C6 | M5-f route tie-break | - | - | - | not built: trace shows 0.014 transit splits/game |
