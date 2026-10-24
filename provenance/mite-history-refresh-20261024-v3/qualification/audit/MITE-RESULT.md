# Mite Big World B replay: compact native/economy audit

This is a compact review of the saved historical replay, not a rerun. The ZIP SHA-256 is `1ae89813d8134d1f3ddc416457e325d01205f9d8bdaabf56edf916a77043736e`; extracted inner `replay.repl26a` SHA-256 is `2339d497b20811479e313fb03708ba8b89f90eb14789bd235b5f1f17197c500a`. The replay declares engine `v1_0_3` (cambc 3.0.5, WASM SHA-256 `029ecd290dc400e75418178ec386d72cbd7d9f2fc2a2e451bf594ca23566df48`) and resolves to `maps/01big-world.map26a` (SHA-256 `f1ecb726472858efb1d75d00b0d7668be18d83a010b2abf9a1f8c38aab456aa5`). The historical replay's local Release/debug mode is unknown.

Side B lost at round 906, with final gem score 1009–614 (A–B). Its draft was Vesper Vale, Vendetta, Ryth, Tavi, Marcella. Native audit found 51 B play rollovers / 0 play errors; A had 343 / 0. Draft and other phases had zero rollovers/errors. The team capture-share gem totals were A 1049 and B 692; final banked score was A–B 1009–614, with end bags 40–78.

There were 46 A capture events and 36 B capture events. B completed 22 tributes for 614 gems and 328 tribute gold; A completed 14 tributes. A finished 20 teleports to B's 0. No attack/cast events targeted either mixed Monolith group 16 (camp ID 57) or group 17 (camp ID 56) on either side; the only champion death was B Ryth actor 7, killed by camp 41. These facts describe this replay, not boss-mechanic feasibility.

Marcella (B actor 9) finished with 140 gems collected and 140 submitted, 1468 gold earned / 1370 spent / 98 unspent, 21876.9 monster damage, zero deaths, and 6 completed tributes totaling 140 gems and 328 tribute gold. Her capture shares were 140 gems and 1140 gold across 8 capture-share records. Her official-enum-decoded items and all team members are in `economy-summary.json`.

Native audit: `native-status.json`, SHA-256 `ce61bde85d19e8ff754c69b7ebe8182fece8afeaed7f00773740ce73cd7df5e6`. Economy receipt: `economy-summary.json`. No actor-window trace was produced.
