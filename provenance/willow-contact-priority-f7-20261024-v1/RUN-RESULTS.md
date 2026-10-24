# Willow contact-priority runtime diagnostic

2026-10-24. Isolated candidate source remained pinned at aggregate `8e535de8da12fde3b5d2c0b03edb275790539b2a867f86cf985ed554ec44c2e7`; exact f7 parent source at `f475b8521cada611754076822402a266c43be8de76ce0f2b504b268ff3335824`; frozen v33 at `a00fff454c1e48520968c9ba2d4c1ecdae0212ce019724dc06a6e959ddc3412e`. No canonical bot or `research/EXPERIMENTS.md` was changed.

The candidate built in Release with 100,000 fuel per turn, normal drafts, one job, `nice 19`, and an approximately 10% active duty cycle. Build and run-batch used the shared clock-recovery workspace. The rebuilt parent and v33 raw/injected WASM hashes match the earlier pinned builds exactly. Candidate raw/injected WASM hashes are `769e16407eb3faafbbe1e02f67624c89905e6b7cef4c9cc3dbe8c40d7d2bd05c` and `6252772fd899f706fed9e91e87076024132518ebb4026901158c1840876d8631`.

| Arm | Map and side | Outcome | Round |
|---|---|---:|---:|
| Candidate vs v33 | Elkring, candidate B | Candidate win | 786 |
| Exact f7 parent vs v33 | Elkring, parent B | Parent win | 786 |
| Candidate vs v33 | Pilgrimage, candidate A | Candidate win | 1,358 |
| Exact f7 parent vs v33 | Pilgrimage, parent A | Parent win | 1,358 |
| Candidate vs v33 | Gold Rush, candidate A | v33 win | 2,000 |

The four requested selected-map games had identical paired outcomes. More specifically, the decoded, uncompressed event and round-state payloads are byte-identical between candidate and parent on both maps. The Gold Rush candidate-A payload is also byte-identical to the existing f7-base-A vs v33 control. That old control has exact parent/v33 source pins and matching raw/injected compiler outputs; it was not rerun. Gold Rush did not draft Willow, so it is only a general replay/build negative control.

The compact native status audit found no bot errors. In the selected maps, candidate play rollovers/errors were `0/0`, parent `0/0`, and v33 `6/0` (all six were on Pilgrimage). In Gold Rush, candidate had `1/0` and v33 `15/0`. Draft and other-phase rollover/error counts were zero. These are native engine status counts, not extracted or inferred error metrics.

The candidate replay payloads show no living Willow at priority 13 in either selected game, including while recalling. Thus the change did not activate in this panel; the identical action payloads confirm the panel says nothing about the policy's effect. The checked repository replay harness replays games and traces bots; it does not inject arbitrary native state. No copied contact-predicate test was substituted. The independent scheduling fixture at `fixtures/projected_order_fixture.py` simulates the engine's alternating-team order by sorting actual roster turns and advancing the ABBA cursor; it covers both 5v6 and 6v5 rosters, either starting side, stable dead champion IDs, and priority ties. It does not validate contact, stun, unknown-enemy, or camp timing admission boundaries.

The Gold Rush arm and selected-game outcomes are diagnostics only. No promotion or performance conclusion follows from this small panel.

Receipts and inputs are retained beside this report: build/run duty logs in `runtime/`, native reports and receipts in `native/`, source pins in `CHECKPOINT.md`, candidate and parent comparison in `payload-comparison.json`, full outputs in `outputs/`, and extracted replay payloads in `payloads/extracted/`. The initial run-batch manifest path mistakes and their logs remain preserved in `runtime/`; those attempts launched no matches. The successful batch completed all four matches with zero failed games.
