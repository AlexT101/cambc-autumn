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
