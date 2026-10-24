# Mite ranked refresh: one follow-up nomination

2026-10-24. Metadata-only review of the successful 08:29 UTC refresh reported by root. No downloads, scripts, replay extraction or runtime work. Source/submission identity remains unknown.

Evidence: `provenance/mite-history-refresh-20261024-v3/ranked-first30.json`, SHA256 `00250e19e320964e4728a9b64f9686d22b741eb2f9302a65c6837e00823040ec`; prior intake `provenance/mite-ladder-history-intake-20261024-v1/{REPORT.md,raw/ranked-first50.json}`. The refresh is a latest-30 slice, not continuous coverage since the prior intake.

Verified **19–11 across 30 rows**, six five-game groups created 07:30:17.522–08:20:16.009 UTC; Mite plays A in20 and B in10. No match IDs overlap the prior50. Mite retains precisely the same three ordered drafts observed previously:

| Ordered Mite draft | Refresh | Prior50 |
|---|---:|---:|
| `[1,2,0,10,6]` |13–8 (21)|26–11 (37)|
| `[11,1,6,2]` |4–0 (4)|5–2 (7)|
| `[6,2,10]` |2–3 (5)|5–1 (6)|

The five-pick is Vesper/Vendetta/Ryth/Tavi/Marcella. Repeated drafts do not establish unchanged code; lower aggregate win fraction does not establish a regression.

| Group UTC | Opponent | Mite side | Record |
|---|---|---:|---:|
|08:20|Trzy Kwaterki|B|3–2|
|08:10|:3|B|3–2|
|08:00|new team(4)|A|3–2|
|07:50|print dont int|A|4–1|
|07:40|Zarzorki|A|4–1|
|07:30|Claudus Maximus|A|2–3|

The four returning opponents have no newly observed ordered draft in this slice: Trzy's five-pick `[6,2,0,1,11]`, new team(4)'s three/four/five prefixes of `[11,6,1,0,2]`, print dont int's four/five prefixes of `[1,11,2,0,6]`, and Zarzorki's three/four/five prefixes of `[11,1,6,0,2]`. `:3` and Claudus were absent from the prior50: `:3` now shows `[11,2,1,6]`, `[11,5,0,1,6]`, `[11,5,2,1,6]`; Claudus `[1,2,11]` and `[1,11,2,10,6]`. These are changes in sampled opponents/maps and draft mix, not proof of new submissions or adaptation.

There are four exact repeated opponent-ID/map-ID/physical-side/both-ordered-draft cells. All preserve the prior result: Starvation B versus Trzy is a win (`7d8d103a…`→`22cd2ea8…`); Ambush A versus new team(4) remains a loss (`6fc00ed3…`→`f3a426db…`); The Farm A against that opponent remains a loss (`3f7fd02c…`→`c4c5aa90…`); Corridors A versus print dont int remains a win (`48390a5f…`→`1c34c2bc…`). This provides no outcome-flip cell to prioritize over the existing mechanism question.

## Sole nominated loss

**`67f9d74a-673e-4b9a-936a-688c75632a0b`**, Big World, created08:10:13.262 UTC, finished08:11:34.098, gems result. Mite B loses with `[1,2,0,10,6]`; `:3` A wins with `[11,5,2,1,6]`. Group `e8e18c45-22eb-4630-9e11-8e1c4e9f36e9`; opponent UUID `bbe481a7-4575-4826-9a3e-f81c28205de8`; map UUID `0ad985c2-fd81-4d09-9986-5363d454b54f`; engine1.0.3.

This has the same map ID and Mite ordered draft as the earlier boss-loss witness `cf39cebf-e598-4540-afaa-b470321fe98a`, but reverses Mite's physical side and changes opponent and enemy draft. The prior winner was new team(4) B with `[11,6,1,0,2]`. It is therefore a useful **mechanism comparison**, not a paired estimate of source strength.

After current comms tests, a compact first pass should ask whether a Monolith payout again materially contributes to the winning economy, or whether ordinary farm/tribute conversion or PvP denial explains this loss instead. Retain both teams' capture/tribute trajectory and Marcella's ordinary versus boss income; only nominate an actor-known window if a concrete decision emerges. The earlier evidence is in `research/mite-observable-counter-review-20261024-v1.md`: enemy Marcella's two-visit Monolith cycle converted228 gems, with known sleeping adjacent hazard. Do not assume that cycle occurs in the new game or reuse its actor ID/coordinates without checking sides. No other fresh replay is nominated, and no new download/extraction is initiated here.
