# Edge-economy draft screen results

All 14 new games completed and all six planned comparisons reuse the exact same-side cells named in the plan. Rows stay separated by arm, map and physical side; results are not pooled into one win rate. Score is submitted gems. Draft picks and actual actor bodies come from the native statistics roster. Native status comes from replay timeline audits.

| Arm | Map | Candidate side | Candidate score | v33 score | Result | Rounds | Draft picks / bodies | Candidate play rollover/error | Control score (candidate–opponent) |
|---|---|---:|---:|---:|---|---:|---:|---:|---|
| support-p | 00contest | A | 0 | 1000 | L | 1553 | 5 / 5 | 8/0 | 0–1000 (f475 baseline Prism/Vesper) |
| support-p | 00contest | B | 1000 | 0 | W | 1435 | 5 / 5 | 11/0 | 1000–200 (f475 baseline Prism/Vesper) |
| support-s | 00contest | A | 400 | 600 | L | 2000 | 5 / 5 | 13/0 | 0–1000 (f475 baseline Prism/Vesper) |
| support-s | 00contest | B | 0 | 1000 | L | 1678 | 5 / 5 | 16/0 | 1000–200 (f475 baseline Prism/Vesper) |
| support-c | 00contest | A | 400 | 800 | L | 2000 | 5 / 6 | 15/0 | 0–1000 (f475 baseline Prism/Vesper) |
| support-c | 00contest | B | 1000 | 0 | W | 1886 | 5 / 6 | 18/0 | 1000–200 (f475 baseline Prism/Vesper) |
| support-p | 01boss-battle | A | 0 | 1199 | L | 1551 | 5 / 5 | 2/0 | 0–1199 (f475 baseline Prism/Vesper) |
| support-p | 01boss-battle | B | 1015 | 0 | W | 655 | 5 / 5 | 1/0 | 1015–0 (f475 baseline Prism/Vesper) |
| support-s | 01boss-battle | A | 1006 | 788 | W | 1587 | 5 / 5 | 4/0 | 0–1199 (f475 baseline Prism/Vesper) |
| support-s | 01boss-battle | B | 1169 | 23 | W | 1414 | 5 / 5 | 3/0 | 1015–0 (f475 baseline Prism/Vesper) |
| support-c | 01boss-battle | A | 0 | 1194 | L | 1651 | 5 / 6 | 5/0 | 0–1199 (f475 baseline Prism/Vesper) |
| support-c | 01boss-battle | B | 0 | 702 | L | 2000 | 5 / 6 | 4/0 | 1015–0 (f475 baseline Prism/Vesper) |
| default-Prism-Vesper | 00gem-fields | A | 1040 | 592 | W | 537 | 5 / 5 | 0/0 | 658–1211 (Prism-Vendetta) |
| default-Prism-Vesper | 00gem-fields | B | 126 | 1004 | L | 427 | 5 / 5 | 3/0 | 1023–701 (Prism-Vendetta) |
| default-Prism-Vesper | 00quadrants | A | 1012 | 625 | W | 521 | 5 / 5 | 0/0 | 1014–601 (Prism-Vendetta) |
| default-Prism-Vesper | 00quadrants | B | 432 | 1015 | L | 429 | 5 / 5 | 0/0 | 516–1024 (Prism-Vendetta) |
| Prism-Vendetta | 00gem-fields | A | 658 | 1211 | L | 574 | 5 / 5 | 1/0 | 1040–592 (default-Prism-Vesper) |
| Prism-Vendetta | 00gem-fields | B | 1023 | 701 | W | 553 | 5 / 5 | 0/0 | 126–1004 (default-Prism-Vesper) |
| Prism-Vendetta | 00quadrants | A | 1014 | 601 | W | 464 | 5 / 5 | 0/0 | 1012–625 (default-Prism-Vesper) |
| Prism-Vendetta | 00quadrants | B | 516 | 1024 | L | 522 | 5 / 5 | 0/0 | 432–1015 (default-Prism-Vesper) |

Contest and Boss Battle comparisons use the exact existing f475 Prism/Vesper control on the same map and physical side. Gem Fields and Quadrants compare Prism/Vesper with Prism/Vendetta on the same map and side. Control records are named and hash-pinned in `RESULT.json` and `PLAN.json`.

## Prism-Vendetta

- 00gem-fields: 1 wins in 2 sides; A-side 0, B-side 1.
- 00quadrants: 1 wins in 2 sides; A-side 1, B-side 0.

## default-Prism-Vesper

- 00gem-fields: 1 wins in 2 sides; A-side 1, B-side 0.
- 00quadrants: 1 wins in 2 sides; A-side 1, B-side 0.

## support-c

- 00contest: 1 wins in 2 sides; A-side 0, B-side 1.
- 01boss-battle: 0 wins in 2 sides; A-side 0, B-side 0.

## support-p

- 00contest: 1 wins in 2 sides; A-side 0, B-side 1.
- 01boss-battle: 1 wins in 2 sides; A-side 0, B-side 1.

## support-s

- 00contest: 0 wins in 2 sides; A-side 0, B-side 0.
- 01boss-battle: 2 wins in 2 sides; A-side 1, B-side 1.

## Verification

- `cambc run-batch`: 14 replay bundles saved, zero failed; stdout SHA-256 `7b48b67fd6cbef82e84645396f4791e7d42ac07cb40413ed6e57c44dae45579b`.
- All 20 rows have a native turn-status audit, including reused controls. Audits count play, draft, and other rollover and bot-error events by physical side. All 14 new-game rows had zero bot-error events.
- All rows show native draft. The Cassi arm drafts five picks and produces six candidate bodies (Cassi and Issac); all other candidate recipes here produce five bodies.
- The screen is diagnostic evidence from a small set of map/side cells. It does not establish a selector threshold.
