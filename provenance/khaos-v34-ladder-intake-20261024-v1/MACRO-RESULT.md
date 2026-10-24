# Khaos v34 post-submit replay macro audit

This report covers only two root-selected, ordinary five-pick ranked losses. The ladder metadata places both after the 2026-10-24 10:17:24Z Khaos_v34 submission event, but replay records do not carry a submission/version ID. Treat these as provisional post-submit samples, not proven server-version-48 runs.

The latest ranked metadata sample is 30 finished games, 12–18. Its 15 provisional post-submit rows are 5–10; the preceding 15 are 7–8. Across the merged, deduplicated ranked history, there are 125 non-Willow-first finished rows (69–56), with 110 pre-cutoff (64–46) and 15 provisional post-cutoff (5–10). Willow-first (ordered first pick 7) is excluded. The 15 post-submit rows by opponent are Prism best girl 1–4, Claudus Maximus 0–5, and Mite 4–1. The one exact pre/post matched map/opponent/side cell is Fracture vs Claudus Maximus, our side B, one game each; both are losses. These small samples are descriptive.

## Gem Fields, our side A vs prism best girl

Normal drafts were our `[Prism, Vesper Vale, Marcella, Willow, Heart of Ruin]` vs `[Prism, Marcella, Ryth, Heart of Ruin, Vesper Vale]`. We lost 429–1077 at round 543. No native Bot errors or fuel rollovers were found on either side.

The game has a large Prism-side economy and fight gap. Our Prism (actor 0) collected 126, submitted 0, ended with 35, died once, and dealt 1,779.9 champion damage. The opponent Prism (actor 5) collected and submitted 505, recorded 3 kills, and dealt 5,272.2 champion damage. At round 330 our Prism died carrying 91 gems; the same death event credits all 91 to opponent Prism. This accounts for the opponent's 91-gem collection above its 986 capture-share gems. Our remaining 35-gem bag reconciles its 126 collected minus 91 lost.

Capture events allocate 555 gems / 530 gold to our team and 986 gems / 1,539 gold to the opponent. Completed tributes were 429 and 1,077 gems respectively. A decisive early allocation was the opponent's group 5 capture at round 31: 71 gems and 90 gold credited to opponent Prism. Its group 11 capture at round 99 added 36 gems and 90 gold to the same Prism; it shopped at round 104. Our Prism captured no gold and bought no items in this match. The public event stream shows the early neutral-income split; it does not establish what either bot knew or why it chose its route.

Our Prism started 465 recalls, canceled 462 (447 manual), and completed 2. Our Willow (actor 3) started 418, canceled 417 (410 manual), and completed 1. Starting recall each turn and canceling the previous end-turn recall stub is routine bot cadence; these counts alone do not indicate abnormal retreat or re-engagement.

The authorized own-view windows for Prism actor 0 and Vesper actor 1, rounds 1–9, show only enemy identities and no visible enemy locations. Prism takes a 60-damage hit from Elk camp 8/group 4 at round 7; it has no gold, items, or camp attacks in this window. Vesper routes into group 4 and attacks gem camps 47 and 49; the Elk hits it for 60 at rounds 5, 6, 8, and 9. It clears camp 47 at round 6 and camp 49 at round 9, and Willow heals it for 240 at round 9. The output files are `own-view-windows-v1/gem-fields-prism0-r1-9.json` and `own-view-windows-v1/gem-fields-vesper1-r1-9.json`. Their public source attribution remains unverified.

## Fracture, our side B vs Claudus Maximus

Normal drafts were our `[Prism, Vesper Vale, Marcella, Willow, Heart of Ruin]` vs `[Vesper Vale, Heart of Ruin, Vendetta, Tavi, Marcella]`. We lost 317–1025 at round 886. The native audit found no Bot errors or fuel rollovers on either side.

Our B team collected 493 gems, tributed 317, and finished with 176 unbanked in Prism (actor 5), who survived the match with no champion damage dealt. There were no death drops for B. The opponent A team captured 1,130 gems, tributed 1,025, and ended with 105 carried by Marcella. The 708 score gap reconciles to A's 637-gem capture-share advantage plus our 176-gem end bag minus A's 105-gem end bag. Our Willow (actor 8) died at rounds 180 and 587, both to opponent Vesper (actor 0); Vesper finished with two kills and 1,540 champion damage. Our Vesper (actor 6) and Heart of Ruin (actor 9) then died at rounds 839 and 844 to opponent Marcella (actor 4), with no gem transfer in either death. Those late kills may affect future farm uptime, but do not explain an additional score transfer in this replay. The available events do not show the actors' private threat assessments.

Our Prism started 841 recalls, canceled 835 (767 manual), and completed 5. Our Willow started 726, canceled 722 (636 manual, 85 due to damage, 1 due to death), and completed 3. Starting recall each turn and canceling the previous end-turn recall stub is routine bot cadence; these counts alone do not indicate abnormal retreat or re-engagement.

## Pins and limits

The downloaded bundles and inner replay payloads, extracted event/round/meta files, map JSONs, and native-status audit are pinned in `MACRO-RESULT.json`. The local release-artifact inventory is in `release-artifact-inventory.json`. The replay event extractor and native status audit use the pinned v1_0_3 engine. `meta.faults` was not used as an error/rollover classification; the native step-kind audit reports those separately.

The Khaos_v34 local source is pinned at aggregate `781fe3641afc4333d8c8a1b42f1344b4ba19edf9d96ae092e9e62069b9083d68`; its submission metadata records server version 48. The frozen f7 parent is `f475b8521cada611754076822402a266c43be8de76ce0f2b504b268ff3335824`. The total source difference includes the later-base port changes as well as finishing-recall work. These two ladder matches are not a controlled source comparison and cannot attribute their outcomes to any one change.
