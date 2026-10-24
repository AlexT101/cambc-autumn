# Mite Big World B replay: compact native/economy audit

This is a compact review of the saved historical replay, not a rerun. The ZIP SHA-256 is `1ae89813d8134d1f3ddc416457e325d01205f9d8bdaabf56edf916a77043736e`; extracted inner `replay.repl26a` SHA-256 is `2339d497b20811479e313fb03708ba8b89f90eb14789bd235b5f1f17197c500a`. The replay declares engine `v1_0_3` (cambc 3.0.5, WASM SHA-256 `029ecd290dc400e75418178ec386d72cbd7d9f2fc2a2e451bf594ca23566df48`) and resolves to [`maps/01big-world.map26a`](/Users/yufan/Desktop/Development/CambridgeBattlecode2026/willow-upstream-development/maps/01big-world.map26a) (SHA-256 `f1ecb726472858efb1d75d00b0d7668be18d83a010b2abf9a1f8c38aab456aa5`). The historical replay's local Release/debug mode is unknown.

Side B lost at round 906, with final gem score 1009–614 (A–B). Its draft was Vesper Vale, Vendetta, Ryth, Tavi, Marcella. Native audit found 51 play rollovers and 0 play bot errors for B; A had 343 rollovers and 0 errors. Draft/other phases had zero rollovers and errors. These are native replay status events, not semantic-event estimates.

Across the replay there were 36 B captures and 46 A captures. B recorded 22 completed tributes totaling 614 gems and 328 tribute gold; B's ending team gem score is the replay's cumulative total and should not be confused with any one champion's submitted gems.

Marcella (B actor 9) finished with 140 gems collected and 140 submitted, 1468 gold earned / 1370 spent / 98 unspent, 21876.9 monster damage, zero deaths, and 6 completed tributes totaling 140 gems and 328 tribute gold. Her capture shares were 140 gems and 1140 gold across 8 capture-share records. Item names come from the extraction's official `enums.json`; full per-champion data is in [`economy-summary.json`](economy-summary.json).

The native audit used the pinned compact v1_0_3 timeline reader. Receipt: [`native-status.json`](native-status.json), SHA-256 `ce61bde85d19e8ff754c69b7ebe8182fece8afeaed7f00773740ce73cd7df5e6`. Economy receipt: [`economy-summary.json`](economy-summary.json), SHA-256 `f4eb821ea7a5ceeb1d0520c9331c755b2b7b426db9986619f8185099ef10c9e0`. No actor-window trace was produced.
