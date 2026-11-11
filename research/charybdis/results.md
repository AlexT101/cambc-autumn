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
| C2 | M4-a2 Prism collects an ally's clear in progress ('Q') | 59.15 (58.7-59.6) | 52.43 (52.0-52.9) | 50.91 (50.4-51.4) | **accepted** |
| C4 (on C2) | M5-c Prism stun-lock safety | 58.5 (58.0-59.0); paired vs C2 -0.68 (-1.23..-0.12) | 52.4 (51.9-52.9); -0.05 | 50.9 (50.4-51.4); -0.02 | rejected: loses vs ocean, OOF +15% |
| C5 (on C2) | L-3 chain limit as a holding cost | 59.1 (58.7-59.6); -0.01 | 52.6 (52.1-53.1); +0.20 | 50.9 (50.4-51.4); +0.00 | rejected: level |
| C3 ext (s-720161..240) | same; p1 vs ocean there 58.45 | 59.0 (58.5-59.4); paired vs p1 +0.51 | - | 50.4 (50.0-50.9) | - |
| C3 (122,880, s-720001..240) | pooled | paired vs p1 +0.42 (+0.08..+0.75) | - | 50.35 (50.07-50.63) | **clear gain**: re-ported onto the accepted state |
| C7 | L-1 Monolith carry price | - | - | - | dropped by user decision: fired too rarely to pass (80 debug games, 70 identical to carry3); untested |
| C8 M2-b | two casts on a double turn | - | - | - | dropped by user decision: adds caution; level in K2b and alone on macro2 |
| C9 (on C2) | K3 hand-over of full and single-tile holds | 59.1 (58.6-59.6); -0.05 | 52.8 (52.3-53.3); +0.35 | 50.9 (50.4-51.4); +0.02 | rejected: level vs p1 |
| C10 (on C2) | M2-c + M2-a hold cast, Willow heal order | 59.3 (58.8-59.7); +0.10 | 53.1 (52.6-53.5); +0.62 | 51.5 (51.0-52.0); +0.61 | **accepted** |
| C3r (on C2 + C10) | C3 re-ported, 'Q' with the premium | 60.4 (59.9-60.9); vs C10 +1.15 | 53.0 (52.5-53.5); -0.05 | 51.4 (50.9-51.9); -0.16 | extended |
| C3r (81,920, s-720001..160) | C10 there: 59.43 / 53.04 / 51.37 | 60.12; **+0.70 (+0.29..+1.11)** | 53.19; +0.16 | 51.32; -0.05 | **accepted (user decision)** |

## Phase-2 result

Accepted: C2, C10 and C3r on p1. Final state = `bots/charybdis`, frozen as `bots/variants/charybdis-p2`. On
s-720001..160 (81,920 games each): **60.12%** against ocean-main-b7c87cf, **53.19%** against charybdis-base and
**51.32%** against charybdis-p1. p1 itself scored 58.68% against ocean and 51.96% against base on the same suites.

## Fuel pass

Exact fuel cuts on p2 (CHANGES 513), no A/B: bench.py at 100M is 52/52 byte-identical on own and test drafts for
both commits (c9e2de302 mean -1.1%, then 1178688e9 a further -0.4%). Agent A's paired 4,096-game measurement:
out-of-fuel turns -5.4% (CI -8.2..-2.5), SHORTCUT lines -4.0%; agent B's: -1.3% (CI -4.3..+1.6). Details in final.md.
