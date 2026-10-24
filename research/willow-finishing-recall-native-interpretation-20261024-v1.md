# Finishing recall: native mechanism and remaining loss

2026-10-24. **The narrow correction works at the intended decision and preserves the carry; the remaining loss does not invalidate that mechanism or establish an always-bank policy.** One fully reactive game, no strength claim. This review reads existing extracted files and source only. Willow-first manipulation batches are excluded.

Evidence root: `provenance/willow-finishing-recall-bigworld-20261024-v1/`. Candidate source `781fe3641afc4333d8c8a1b42f1344b4ba19edf9d96ae092e9e62069b9083d68`, exact latest parent `f599a31faa0251321beb97a726918286e266218ceb3e183b8271e41c5c84718c`, frozen v33 opponent `a00fff454c1e48520968c9ba2d4c1ecdae0212ce019724dc06a6e959ddc3412e`. Physical B candidate against A v33, Big World, same normal ordered five-pick drafts. Bundle SHA `bcddd6777bd59929e8033bef869b8e73b8d9819de89d3c4b99fe5b8a9afa5f8f`; inner replay SHA `369f73638437e6ed4313cdb19d18798c85a3da425863f602842b0d1ad558b8f0`. Do not confuse the extraction directory/bundle prefix with the inner payload.

## Confirmed local improvement

`logs/compare.stdout.log` (SHA `f3e8f4b3caf1e934b24f4eaa2455e778926e66d9f51f653a586a21af3c8b3c2c`) finds no earlier accepted-input divergence: first difference is Prism5 at738, input27683, step163689, parent cancel-channel versus candidate end-turn. Candidate recall completes739, carrying246, from raw `(35,56)` to `(21,88)`. Its round-end HP rises528→2440, Focus609→681 and gold680→20 after arrival/shopping. The parent trace already established the pack-suppression cause; the new reactive execution now also establishes that the existing interception check permits the keep.

Candidate B still loses1014–588 at877, versus parent1110–474 at780. Native B remains3 rollovers/0 errors; Prism has none, survives with287 gems and takes/deals no champion damage. A has4 rollovers/0 errors. These are per-actor native-status findings (`native-audit.json`, SHA `ca3f99dd0eb9d5c30b3d6e83964f86370deaff8f2726790e84bdd6b41ded3fdd`), not `meta.faults` interpretation. The first divergence is the reviewed policy action rather than an earlier fuel-induced fork. Later differences are reactive consequences; the longer game and increased team score are not independent strength measurements.

## Remaining score gap, and what retained Focus actually did

Candidate ordinary captures total925 versus A1030. A also takes21 gems in the unchanged pre-fork HoR9 death at709. B ends carrying316 and A37. Therefore `1014−588 = 105 + 2×21 + (316−37) = 426`: ordinary acquisition deficit, transfer swing, and unbanked difference. Even instantly submitting every B ending bag yields904, still96 short of winning; banking alone cannot turn this same terminal allocation into a victory. Earlier banking could change subsequent farming and the entire trajectory, so this is accounting, not a counterfactual proof that banking never helps.

Prism's personal bag remains287 after its41-gem g7 payout777, but it remains useful to teammates. Existing events record **Prism clears g23 at786 → Vesper captures15 at794**, and **Prism clears g7 at845 → Vesper captures41 at852**. Thus “no further personal capture/no tribute” is not idle work. At780–877 Prism retains782.5 Focus, including430.5 from287 carried gems, and supplies camp damage. Removing that bag would remove that damage contribution; it cannot be treated as a free287 score gain with identical later captures. Whole-match monster damage is53,817.9, but that alone is not the causal value of retention.

Selected round-end observer context (raw physical coordinates throughout):

| Round | A/B submitted | B carried, Prism / others | Prism position / HP |
| --- | --- | --- | --- |
| 738 | 654 /419 | 246 /55 | `(35,56)` /528 |
| 739 | 654 /419 | 246 /55 | `(21,88)` /2440 |
| 780 | 684 /474 | 287 /0 | `(18,91)` /2800 |
| 820 | 770 /474 | 287 /15 | `(45,87)` /2800 |
| 850 | 832 /532 | 287 /29 | `(34,95)` /2756.8 |
| 876 | 993 /588 | 287 /29 | `(14,96)` /2567.8 |

These are global end-of-round observations, not proof of each actor's simultaneous private bag knowledge, altar accessibility or enemy visibility. At876 a fresh287-gem tribute alone takes29 turn ends; the subsequently observed finish one round later cannot be prevented by merely deciding to bank at that late snapshot.

## Source interpretation and its boundary

Frozen parent `bot.cpp:700–703` intentionally retains a gem-Focus champion's nonzero bag unless it is already winning or `closing`. `decide:4878` clears banking while retaining, and `4986–4989` only enters the carry/bank dispatcher when the bag is usable **and not retained**. `can_tribute_safely:3302–3306` likewise declines for a retained bag. `bankable_bag:640–643` separately checks altar access/camp exposure. Zero submissions therefore fits explicit policy; it is not evidence of a failed tribute or a stuck recall.

Team-bank awareness exists: `gems_short:436–442` counts own bag and visible allied ongoing tributes; `race_left:672–680` also subtracts other living allies' visible bags or last comms posts. Posts are rounded up in fours and have no full age field (`comms.h:29–35`), so they are beliefs, not an omniscient live team sum. `closing:689–697` compares bank travel/channel time with the round limit and **our team's** projected completion; `World::ally_rate` (`world.cpp:1905–1909`) uses our submitted-score history since roughly half the current match.

A concrete source limitation is that this retention horizon does not use the opponent's submitted score or payout pace, although both submitted scores are readable. `game_ender:3424–3446` addresses an interceptable visible winning enemy carrier, not a general deadline imposed by the opponent's economy. This can leave a retained bag valuable for farming beyond the match's actual remaining life. It is a plausible later policy experiment, **not yet a demonstrated avoidable banking error here**: we lack an actor-known early banking opportunity, feasible safe route/channel, and the competing value of its lost farming service. Neither invisible opponent intent nor hindsight from the final score supplies those facts. Do not add an opponent-score threshold or force tribute from this one result.

## Small next comparison and recommendation

Keep the recall fix as a justified correction candidate, with its source/fixture/native mechanism evidence intact. Next, two small paired cells are enough to check nearby behavioral consequences without rerunning this deterministic witness: **Big World A** and **Gold Rush B**, candidate versus the same exact f599 parent, both against frozen v33 with normal drafts. Reuse a control only when source/binary/map/side identity matches; old f7/cb61 outcomes are not controls for this child. This is a proposal for parent scheduling, not authorization or a run performed here.

Inspect whether changes begin in the intended held-capture/pack-suppression context, whether actual interception checks still reject unsafe channels, whether a winning top-up is left to canonical behavior, and whether saved carries produce useful farming or later score without creating new turnover. A non-activating cell can check drift/fuel consequences but cannot prove the exception useful. No rigid small-panel win-rate gate is appropriate: fixtures cover decision boundaries, this game validates a real corrected action, and broader competitive value remains separate.

No additional actor window is nominated now. The existing events already refute both “saved carry has no use” and “banking alone would win.” If a later retention experiment becomes the priority, choose an earlier source-known decision with a feasible altar route and enough channel time; ask specifically for retention/closing horizon and accessible opportunity, rather than extracting a terminal snapshot merely because its bag is large.
