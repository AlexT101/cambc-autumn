# Native replay extraction cross-checks

The corrected inventory expands canonical map storage through `Grid.allCamps()` and `Grid.groups()`. Three existing replay map extracts confirm total camp counts, per-type counts, and ordinary group reward sums. These extracts describe full native maps, matching the v2 whole-map rows.

| Map | Extract camps/groups | V2 camps/groups | Extract ordinary rewards | V2 ordinary rewards |
|---|---:|---:|---:|---:|
| 00gem-fields | 50 / 18 | 50 / 18 | 364 gems, 600 gold | 364 gems, 600 gold |
| 01fracture | 86 / 28 | 86 / 28 | 444 gems, 2720 gold | 444 gems, 2720 gold |
| 01big-world | 92 / 24 | 92 / 24 | 376 gems, 2160 gold | 376 gems, 2160 gold |

Source extracts:
- `provenance/khaos-v34-ladder-intake-20261024-v1/extracted/maps/d22495f1f242da29.json` (SHA-256 `e923dd93f1db74eeaf0cd96b42cb968e5dc4f369fd0e81efdfa5bba16394d5e7`)
- `provenance/khaos-v34-ladder-intake-20261024-v1/extracted/maps/8f17d2cbf1d64f77.json` (SHA-256 `73ca7fc6b7f0332ce7e81805b43ed02e7fea1237cefdb522461e429836ebab7b`)
- `provenance/willow-finishing-recall-bigworld-20261024-v1/extracted/maps/c890c7d4607bc45c.json` (SHA-256 `9f21864a9e2e03469fb7d03b496960402ffbdfa6d09fd8f2da11e124472af4e8`)
