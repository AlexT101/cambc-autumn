# Khaos_v33 / server44

Submitted once on2026-10-23 at15:59:25-0400, with note `Khaos_v33 - Willow ready healing and retreat repairs`. The CLI receipt confirms server44 and225939 uploaded bytes. No remote payload was retrieved; the byte count does not establish a remote hash.

The29-file source-only clone, canonical Hyperion and tested candidate all have aggregate `a00fff454c1e48520968c9ba2d4c1ecdae0212ce019724dc06a6e959ddc3412e`. Raw and injected Release WASM are byte-identical to the qualified candidate. The CLI ZIP contains exactly those29 source files; local SHA-256 is `787423a8a652e3e75cb1724d4bad529ef4f2a998600f3b924248ebf7e4093bf2`.

Against frozen current upstream b7bfcb7, qualification was569–535 over1104 games. A separate fresh512 comparison against deployedv32 was251–261. These support a near-level logical repair, not established win-rate superiority. The fresh comparison had no caught action errors, native bot errors or runner failures. Two rare candidate code5 errors in the upstream comparison remain unresolved; Debug reproduction diverged from Release and did not reproduce them. Fuel rollovers remain a limitation.

`release.json` records the full qualification, build, bundle and submission pins. `release.pre-submission.json` preserves preparation metadata; `submit-response.txt` is the exact receipt. The same Pantheon session target was used asv32; read-only history refreshes returned503/429, so no immediate fresh team verification is claimed.

This release includes upstream107, the upstream108 revert, Willow support/Prism recovery, independent ready healing and bounded retreat repair. Four-pick Willow and the local Monolith crew are separate experiments.
