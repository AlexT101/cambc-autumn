# Three-pick order, fixed-roster proxy, and income results

Completed 44/44 new games; `run-batch` exited 0 and saved all 44 replay/statistics pairs.

Native statistics show 0 games with bot faults, 0 with diagnostic codes, 0 body-count mismatches, 0 candidate draft-sequence mismatches, and 0 roster mismatches against the intended proxy or reused control.

## Order and fixed-roster proxy results

| Candidate draft order | Opponent fixed-roster proxy | Candidate wins/games | Candidate A | Candidate B | Fragment | Packs |
|---|---|---:|---:|---:|---:|---:|
| M/V/HoR | Marcella/Vendetta/Tavi fixed-roster proxy | 4/4 | 2 | 2 | 2 | 2 |
| M/V/HoR | Vesper Vale/Heart of Ruin/Vendetta fixed-roster proxy | 4/4 | 2 | 2 | 2 | 2 |
| P/V/HoR | Marcella/Vendetta/Tavi fixed-roster proxy | 2/4 | 1 | 1 | 1 | 1 |
| P/V/HoR | Vesper Vale/Heart of Ruin/Vendetta fixed-roster proxy | 3/4 | 2 | 1 | 2 | 1 |
| V/HoR/M | Marcella/Vendetta/Tavi fixed-roster proxy | 3/4 | 2 | 1 | 1 | 2 |
| V/HoR/M | Vesper Vale/Heart of Ruin/Vendetta fixed-roster proxy | 3/4 | 2 | 1 | 1 | 2 |
| V/HoR/P | Marcella/Vendetta/Tavi fixed-roster proxy | 3/4 | 2 | 1 | 1 | 2 |
| V/HoR/P | Vesper Vale/Heart of Ruin/Vendetta fixed-roster proxy | 3/4 | 2 | 1 | 1 | 2 |

## M3 delayed-income comparison

M3+income vs v33: **5/12** (candidate A 3/6; candidate B 2/6). Exact reused M3-v33 controls: **6/12** (candidate A 3/6; candidate B 3/6).

Matched-cell outcomes changed: gain=1, loss=2, same=9.
The income arm uses the exact reused M3-v33 controls from the fixed-three screen, matched by map and candidate physical side. These fixed-roster proxies use f475 gameplay with roster overrides; they are not replicas of real competition opponents.

Per-game draft, outcome, and output hashes plus the exact reused control hashes are in `RESULT.json`.

## Native phase status audit

The pinned replay auditor scanned all 44 new games. Native `Turn rollover` counts (fuel-turn yields) and `Bot error` counts are shown separately; no result is inferred from statistics diagnostics.

| Group | Games | Candidate play rollover/error | Candidate draft rollover/error | Candidate other rollover/error | Opponent play rollover/error | Opponent draft rollover/error | Opponent other rollover/error |
|---|---:|---:|---:|---:|---:|---:|---:|
| income-M3-vs-v33 | 12 | 10/0 | 0/0 | 0/0 | 11/0 | 0/0 | 0/0 |
| order-M-V-HoR-vs-proxy-mvt-three | 4 | 5/0 | 0/0 | 0/0 | 2/0 | 0/0 | 0/0 |
| order-M-V-HoR-vs-proxy-vhv-three | 4 | 4/0 | 0/0 | 0/0 | 9/0 | 0/0 | 0/0 |
| order-P-V-HoR-vs-proxy-mvt-three | 4 | 3/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| order-P-V-HoR-vs-proxy-vhv-three | 4 | 4/0 | 0/0 | 0/0 | 4/0 | 0/0 | 0/0 |
| order-V-HoR-M-vs-proxy-mvt-three | 4 | 3/0 | 0/0 | 0/0 | 1/0 | 0/0 | 0/0 |
| order-V-HoR-M-vs-proxy-vhv-three | 4 | 10/0 | 0/0 | 0/0 | 4/0 | 0/0 | 0/0 |
| order-V-HoR-P-vs-proxy-mvt-three | 4 | 5/0 | 0/0 | 0/0 | 5/0 | 0/0 | 0/0 |
| order-V-HoR-P-vs-proxy-vhv-three | 4 | 3/0 | 0/0 | 0/0 | 7/0 | 0/0 | 0/0 |

All 44 native replays were read using the pinned v1_0_3 compact timeline; total native bot-error steps: 0. Detailed reports and input hashes are in `native-audit/` and `NATIVE-PHASE-AUDIT.json`.
