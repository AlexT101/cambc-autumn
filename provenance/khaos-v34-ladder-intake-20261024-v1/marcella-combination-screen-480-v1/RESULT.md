# Marcella combination screen results

Completed 480/480 games; `run-batch` exit 0; saved 480 replays and 480 statistics files.

Native audit: 0 games with bot faults, 0 with diagnostic codes, 0 candidate body-count deviations from map pick count. Per-game roster and output hashes are in `RESULT.json`.

## Candidate results by arm and opponent

| Arm | Opponent | Wins / games | Candidate A | Candidate B | Mean completed rounds | Candidate rosters |
|---|---|---:|---:|---:|---:|---|
| marcella-hop | f475 | 44 / 80 | 29 / 40 | 15 / 40 | 1085.1 | Prism + Vesper Vale + Marcella + Willow + Heart of Ruin: 52; Prism + Vesper Vale + Marcella + Heart of Ruin: 16; Prism + Vesper Vale + Heart of Ruin: 12 |
| marcella-hop | v33 | 52 / 80 | 26 / 40 | 26 / 40 | 1096.1 | Prism + Vesper Vale + Marcella + Willow + Heart of Ruin: 52; Prism + Vesper Vale + Marcella + Heart of Ruin: 16; Prism + Vesper Vale + Heart of Ruin: 12 |
| marcella-hop-mixed-approach | f475 | 43 / 80 | 26 / 40 | 17 / 40 | 1110.7 | Prism + Vesper Vale + Marcella + Willow + Heart of Ruin: 52; Prism + Vesper Vale + Marcella + Heart of Ruin: 16; Prism + Vesper Vale + Heart of Ruin: 12 |
| marcella-hop-mixed-approach | v33 | 50 / 80 | 24 / 40 | 26 / 40 | 1073.5 | Prism + Vesper Vale + Marcella + Willow + Heart of Ruin: 52; Prism + Vesper Vale + Marcella + Heart of Ruin: 16; Prism + Vesper Vale + Heart of Ruin: 12 |
| marcella-mixed-approach | f475 | 41 / 80 | 24 / 40 | 17 / 40 | 1101.7 | Prism + Vesper Vale + Marcella + Willow + Heart of Ruin: 52; Prism + Vesper Vale + Marcella + Heart of Ruin: 16; Prism + Vesper Vale + Heart of Ruin: 12 |
| marcella-mixed-approach | v33 | 47 / 80 | 23 / 40 | 24 / 40 | 1069.8 | Prism + Vesper Vale + Marcella + Willow + Heart of Ruin: 52; Prism + Vesper Vale + Marcella + Heart of Ruin: 16; Prism + Vesper Vale + Heart of Ruin: 12 |

Candidate-side scores are aggregated by explicit A_source/B_source identity with the tested `candidate-source-aggregation/aggregate.py` helper. The 160 games per arm comprise 40 maps × both sides × two opponents; do not pool across arms or opponents. Candidate roster/body-count audit uses native statistics `roster.champions`, not the plan labels.

## Native phase status audit

Counts are native `Turn rollover` and `Bot error` step kinds from pinned v1_0_3 replay scans. Rollovers (fuel-turn yields) are separate from bot errors. Candidate vs opponent counts by arm and opponent:

| Arm | Opponent | Candidate play rollover/error | Candidate draft rollover/error | Candidate other rollover/error | Opponent play rollover/error | Opponent draft rollover/error | Opponent other rollover/error |
|---|---|---:|---:|---:|---:|---:|---:|
| marcella-hop-mixed-approach / f475 | service-base-f7 | 253/0 | 0/0 | 0/0 | 267/0 | 0/0 | 0/0 |
| marcella-hop-mixed-approach / v33 | v33 | 294/0 | 0/0 | 0/0 | 542/0 | 0/0 | 0/0 |
| marcella-hop / f475 | service-base-f7 | 258/0 | 0/0 | 0/0 | 248/0 | 0/0 | 0/0 |
| marcella-hop / v33 | v33 | 288/0 | 0/0 | 0/0 | 551/0 | 0/0 | 0/0 |
| marcella-mixed-approach / f475 | service-base-f7 | 254/0 | 0/0 | 0/0 | 266/0 | 0/0 | 0/0 |
| marcella-mixed-approach / v33 | v33 | 256/0 | 0/0 | 0/0 | 557/0 | 0/0 | 0/0 |

All six native phase batches scanned 480/480 replays; 0 total native bot-error steps.
The per-game native status reports and inputs are in `native-audit/`; input file hashes and engine/mode pins are collected in `NATIVE-PHASE-AUDIT.json`.
