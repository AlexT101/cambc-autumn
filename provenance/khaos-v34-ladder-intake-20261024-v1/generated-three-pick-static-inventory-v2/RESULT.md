# Generated three-pick static inventory and outcome-blind sample

All eligible maps come from pinned `gen` and `gen-s1` indexes, are re-decoded natively as three-pick maps, and are deduplicated by full map bytes. No game outcomes were read. Features describe public initial geometry; they do not predict capture shares, guaranteed clears, or champion decisions. LOS uses a documented deterministic approximation rather than the engine shadowcaster.

Eligible index entries: 168; unique native three-pick maps: 168; duplicate bytes removed: 0.
Selection ramp cutoffs: low ≤ 0, middle ≤ 7, openness median 2.25.
Selection exceptions: 0; exact ramp bands are 56/56/56. Cutoff values are 0 and 7, with 99 and 15 tied maps respectively split by SHA.
Selected maps with any altar accessible on terrain-only paths but none with camps blocked: 0.
Selected nearest-three asymmetries intersecting a cutoff tie: 1; mirror comparison is in RESULT.json.

|Cell|Suite|Preset|Map|SHA256|mean harmless gems|open|harmless jobs A/B|conservative gems A/B|
|---|---|---|---|---|---:|---:|---|---|
|low/below-median|gen|rows|gen-rows-102301101.map26a|033274acd018eae830b0181d0b743ebe1f3e65ce53dd58a7318196e4acc17e30|0|1.99|1/1|0/0|
|low/below-median|gen-s1|donut|gen-donut-102405614.map26a|0574bda0885ef9b32f78d3000c5565db2e37d62f1405bd0a15e83063b3ce3319|0|1.37|1/1|0/0|
|low/above-or-equal-median|gen|serpentine|gen-serpentine-102307009.map26a|00a717afa55166b7937d7328d5c46b6d856f1215eef88091ad8700ba890a6b97|0|2.6|0/0|0/0|
|low/above-or-equal-median|gen-s1|diamond|gen-diamond-102405516.map26a|14b85bd1f1c6033a2f9fbae8855dd60cafc49dd5523d79a889f339a220cd7b56|0|2.81|2/2|0/0|
|middle/below-median|gen|city|gen-city-102306900.map26a|919646ac8421d0d4bcff6a5b12c2301f134619788c368ce0859df24d7dac0d09|7|1.81|1/1|7/7|
|middle/below-median|gen-s1|blob|gen-blob-102406206.map26a|068a4b65bf7d5ca9e007ba3a19af3d0a0bd8232f5d23b29628ef9a0c74361af5|3.5|1.17|0/1|0/7|
|middle/above-or-equal-median|gen|archipelago|gen-archipelago-102306018.map26a|0c4948375fd2c8586e1a776a29eb47fed7426f422b14deb07bf6571af807090f|7|2.67|3/3|7/7|
|middle/above-or-equal-median|gen-s1|donut|gen-donut-102405617.map26a|49df08e75a8a7db08c43b662075777d2bc9e6a19ebe63f2700defdcda50d4e8f|7|4.5|2/2|7/7|
|high/below-median|gen|labyrinth|gen-labyrinth-102306303.map26a|1c352dbf152b8820bda199a038ffb69b8c1d527203feca8d091e66059e21acb4|14|1.1|1/1|0/0|
|high/below-median|gen-s1|spiral|gen-spiral-102406404.map26a|008f151d0745a1eed5e40a8d2f684b31c8e1a998663e8b25cf4512b11a155ae5|35|1.9|3/3|35/35|
|high/above-or-equal-median|gen|star|gen-star-102305406.map26a|203641a40ba4086741aa0ec0fe62b4f4193148a746353b516ed36cf159194118|28|3.7|3/3|28/28|
|high/above-or-equal-median|gen-s1|classic|gen-classic-102400016.map26a|0036fdfd314928f150bef4eb958eabfbd7d44aeb53371c11f3b4935164e569af|14|3.07|2/2|14/14|

## Limits

Terrain station reach is an 8-neighbour BFS with enemy spawn and camp tiles blocked. Complete Grid groups are considered from each spawn regardless of team label; groups with any monolith are excluded as non-ordinary. Cluster HP is 120 per rules. A group counts as independently accessible only when every member has a reachable range-3 firing station. Conservative harmless supply requires both route and endpoint to avoid tiles within static damaging-camp ranges. This omits camp sleep, combat, shared timing, ally allocation and actual team control. Station visibility is approximate and pinned in `RESULT.json`.
