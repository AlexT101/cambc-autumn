# Parent Prism own-view: r735–744

This is the single authorized own-view window for actor 5 Prism on physical side B (exact latest parent; opponent is frozen v33 on A). Replay bundle/file SHA-256 15a703f86fd6cbf7ca9b14fddc9136f2100bc5afce87520905b274c82cbe670c; inner replay payload SHA-256 0022ca3c4d26d95df367ba021ef4d2b435f2eaccb9e3c76708ba5821619f14dc; map SHA-256 f1ecb726472858efb1d75d00b0d7668be18d83a010b2abf9a1f8c38aab456aa5. Source aggregates: parent f599a31faa0251321beb97a726918286e266218ceb3e183b8271e41c5c84718c, v33 a00fff454c1e48520968c9ba2d4c1ecdae0212ce019724dc06a6e959ddc3412e. Exporter uses pinned v1_0_3 own-view compatibility engine. Full ten-round observations and ordered actor actions: actor-window.json.

## At the r738 cancellation
At the start of Prism's turn, the own-view observation places Prism at raw [35, 56] / own-normalized [64, 43], HP 528/1480, carrying 246 gems, in recall channel timer 1. Cooldowns are [0, 3]; cast-ready is True, attack-ready is False.

- Visible Vesper Vale actor 1 (side A): raw [32, 50], own-normalized [67, 49]; Chebyshev distance 6; HP 2713.59765625/2800, strength 400, abilities ['Attack reset', 'Dash'], cooldowns [0, 5], channel type 1 timer 4.
- Visible Willow actor 3 (side A): raw [35, 50], own-normalized [64, 49]; Chebyshev distance 6; HP 700/700, strength 67, abilities ['Heal', 'Attack reset'], cooldowns [6, 0], channel type 1 timer 4.

Ordered actions on this actor turn are cancel-channel at step 163689, then recall at step 163690. Both visible enemies are themselves in recall channels at timer 4 in this snapshot. The observation supplies no active enemy action or attack event at the cancellation point; this does not prove they could not become threatening later. In particular, the own-view record shows positions and channels rather than a private threat forecast.

The next rounds preserve that pattern: r739 again cancels and recalls while both enemies remain visibly in recall; at r740 Prism cancels, casts CC at Vesper raw (32,52), recalls, and sets priority. At r741 Vesper is visible at (32,52) with no channel and Prism uses AoE at (35,52). Those later facts do not alter what Prism knew at the r738 cancellation. This summary does not extend past r744 or infer unseen frames.

The full exporter receipt is actor-own-view-window/v3; actor-view output SHA-256 6f3d56e744e9185f84eb60725a5e0c9b0a898520b3018442f00efe44c7e8b12d. Duty wrapper ran at 10% approximate active fraction; there was no build or game run in this audit.
