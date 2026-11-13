# Prism walking (2558 games with a Prism or Vesper, 0 errors)

## (a) Walk legs by purpose: % of the champion's walk rounds / mean leg length
| champion | phase | walk % of alive | camp | hold | tribute/altar | spawn/recall | fight | wait_camp | died | regroup | other |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Prism | r1-400 | 61% | 51% / 7.4 | 14% / 3.9 | 1% / 15.2 | 6% / 3.2 | 13% / 5.5 | 14% / 14.1 | 0% / 1.9 | 0% / 15.6 | 1% / 13.3 |
| Prism | r401-800 | 59% | 35% / 8.0 | 11% / 3.4 | 6% / 12.2 | 5% / 3.8 | 19% / 7.3 | 19% / 13.9 | 0% / 3.7 | 1% / 25.1 | 3% / 10.1 |
| Vesper Vale | r1-400 | 49% | 50% / 7.0 | 7% / 1.8 | 8% / 11.4 | 8% / 3.1 | 10% / 5.6 | 14% / 10.2 | 0% / 3.0 | 1% / 13.9 | 3% / 9.6 |
| Vesper Vale | r401-800 | 56% | 34% / 6.7 | 6% / 1.9 | 13% / 9.8 | 7% / 3.6 | 16% / 7.4 | 17% / 10.1 | 0% / 6.3 | 2% / 21.4 | 5% / 10.5 |

## (b) Captures the Prism shared, by who dealt most of the cycle's monster damage
- r1-400: prism most 34280 (69%, Prism gems 27.4/capture, Prism damage share 75%); ally most 14303 (29%, Prism gems 21.4/capture, Prism damage share 16%); enemy most 1437 (3%, Prism gems 33.9/capture, Prism damage share 12%)
- r401-800: prism most 21854 (79%, Prism gems 27.7/capture, Prism damage share 86%); ally most 4773 (17%, Prism gems 21.3/capture, Prism damage share 14%); enemy most 1097 (4%, Prism gems 34.2/capture, Prism damage share 11%)

Collections (ally did most of the damage): the Prism's walk leg into the tiles, the gap from the clear to its arrival, and the clearing ally's rounds on or within 2 of the tiles in that gap
| phase | collections | Prism walk leg median / mean | Chebyshev dist at clear median | clear -> Prism arrival median / mean | clear -> payout median | clearing ally waiting rounds median / mean | ally waited 3+ rounds |
|---|---|---|---|---|---|---|---|
| r1-400 | 14303 | 4 / 6.5 | 2.0 | 3 / 4.3 | 7 | 2.0 / 2.2 | 36% |
| r401-800 | 4773 | 4 / 7.3 | 3 | 3 / 5.9 | 7 | 2.0 / 2.4 | 40% |

## (c) Completed recalls: shop trips (recall started at >= 90% health)
| champion | phase | completed recalls per champion-game | started at >= 90% hp | of those, bought something on spawn | gold per buying trip median / mean | rounds on spawn after arrival median | recall start -> next camp hit median / mean |
|---|---|---|---|---|---|---|---|
| Prism | r1-400 | 5.06 | 64% | 90% | 150 / 172 | 2 | 19.0 / 24.1 |
| Prism | r401-800 | 2.18 | 61% | 89% | 180 / 253 | 2 | 19.0 / 27.3 |
| Vesper Vale | r1-400 | 7.24 | 55% | 91% | 150 / 158 | 1 | 16.0 / 21.3 |
| Vesper Vale | r401-800 | 4.87 | 63% | 88% | 150 / 195 | 1 | 17.0 / 23.1 |

## (d) Prism alive rounds within 2 of an altar, not channelling a tribute
- r1-400: 3.3% of Prism alive rounds (12.8 rounds per Prism-game), mean bag 149; by class: walk_bag 53%, camp 16%, fight 12%, hold 6%, walk 5%, recall 4%
- r401-800: 5.9% of Prism alive rounds (15.6 rounds per Prism-game), mean bag 456; by class: walk_bag 49%, fight 16%, camp 9%, wait_altar 9%, wait_camp 8%, walk 4%
