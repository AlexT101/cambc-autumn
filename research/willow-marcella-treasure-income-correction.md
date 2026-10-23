# Marcella Treasure income: replay correction

2026-10-23. Read-only existing exact-a67 replay evidence. This corrects the earlier assumption that Treasure excludes Marcella's tribute-generated gold. No engine, new extraction, probe, script or gameplay edit. Root has requested a dedicated probe after the active runtime worker finishes; YAML is unchanged pending that verification.

## Independent native snapshot witnesses

Both sources are already extracted under `replays/willow-sustainable-crew-fish-panel-20261023-v2/extract16/`; actor2 is physical-A Marcella. `rounds.json.gz` contains engine snapshot balance and lifetime earned gold, distinct from the extractor's derived event-accounting soft checks.

| Exact replay directory | Treasure completion | Tribute round/gems | Previous→current earned | Previous→current balance | Observed increase |
|---|---|---|---|---|---:|
| `937e49df38e49207` BigWorld |227, Strength|328 /41|472→570|12→110|98|
| `b3fc46242dae948d` Boss |78, Focus|698 /732|3528→5284|278→2034|1756|

The bags become zero. Existing events show no capture, kill or shopping income for Marcella on either tribute round. The increments match the floor-visible effect of41×2×1.2=98.4 and732×2×1.2=1756.8; the unmodified alternatives82 and1464 do not match. These two direct snapshot differences do not depend on reconstructing native earnedGold from events.

Whole-game accounting independently agrees:

- BigWorld: native earned3095, submitted313, zero kills. Capture events pay2350 gold:130 before Treasure and2220 after. Fifteen gems are tributed before Treasure,298 after. `2350 +15×2 +298×2.4 =3095.2`, consistent with native floor3095. Without the tribute bonus the total would2976. The recorded-schedule Treasure increment is370 capture gold plus119.2 tribute gold,489.2 total; this is not a no-Treasure gameplay counterfactual.
- Boss: native earned5774, submitted751. Captures pay3372; five explicit kill rewards pay120 each; all tributes occur after Treasure. `3372 +600 +751×2.4 =5774.4`, consistent with native floor5774. Marcella's tribute contribution is1802.4, not1502. Removing it as an allegedly ineligible source would understate Treasure's return.

The SDK calls Treasure's passive20% more gold gained and gives Marcella's base tribute rate2. `cambc-rules.yaml` lists capture/kill bonus application but does not explicitly exclude tribute-generated gold. Existing `probe-capture` scenario6 tests Treasure on Vesper/Vendetta, not Marcella; scenario8 includes an idle Marcella. No direct existing probe confirmation was found in those cases. The pending probe should distinguish balance from lifetime earned, hold all other income/spending fixed, and compare the same tribute quantity before/after Treasure.

## Consequence for allocation and future item tests

Do not remove Treasure from Marcella on the argument that her large earnedGold is mostly ineligible tribute income. Native earnedGold still needs decomposition to understand role and timing, but in these replays both capture/kill income and her tribute-generated income benefit. Her early completion78 in Boss precedes the large698 tribute; BigWorld completion227 precedes298 of313 submitted gems.

For other champions, no uniform lower-Treasure policy follows. Vesper's33% makes him a valuable holder where capture timing and safety are preserved; Marcella has a separate reason to convert gems. Neither role bonus justifies delaying a capture, starving another worker's effective upgrade, or routing every worker to the same reward. The isolated Willow first-protection arm tests a concrete delayed-protection opportunity cost; it does not impose a team-wide gold-emblem ban.

## Minimal healing-value measurement

At an already evaluated heal candidate retain scalar pre-cast HP/maxHP, current nominal heal, actual gain estimate, target, current cast readiness and selected path. Compute marginal capacity `min(deficit, H+delta)-min(deficit,H)` and both current/proposed worth_healing outcomes. Record actual cast success separately; an offered heal is not delivered HP. Include basic/reset opportunities and the item's actual purchase round/cost.

Cover generic `heal_ally`, local-support and independent-step target selection, and the combat planner's heal action. Logging only `heal_ally` misses other successful heal paths. Reuse each path's existing live/observed values, label belief versus live provenance, and never add native reads to fill missing fields. A centralized low-level cast wrapper can record success but cannot invent the selected recipient's pre-cast deficit; thread scalar diagnostic data from selection if a future diagnostic is authorized. No instrumentation is implemented here.

Full-cap360 events only bound unknown extra demand; they do not prove it. Subcap events normally show no capacity benefit on that recorded cast. Raising Focus also raises the60% ordinary heal threshold, so record potentially suppressed low-gain casts, with the below-half-health exception. The relevant result is additional absorbed healing and subsequent productive recipient turns versus farming/reset/survival cost, not nominal offered healing or a damage-equivalent coefficient.
