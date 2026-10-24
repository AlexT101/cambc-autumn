# Recall + sighting clean-union checkpoint

2026-10-24. Source-only isolated unnumbered child: `bots/variants/willow-recall-sighting-4d08241-work`. Cambridge Battlecode rules previously read. Created from frozen finishing-recall src and copied only exact reviewed sighting-arbitration v3 comms.cpp/comms.h. No .cambc, novel policy/tuning, build/game, script/test/tooling change, canonical/EXPERIMENTS edit or release. All parent variants retained; both contributing29-file source manifests independently verified unchanged before copying.

Parent baseline aggregate `f599a31faa0251321beb97a726918286e266218ceb3e183b8271e41c5c84718c`. Recall source aggregate `781fe3641afc4333d8c8a1b42f1344b4ba19edf9d96ae092e9e62069b9083d68`; sighting v3 aggregate `a439a6c2d1d1d2ef1004f3a463b243d1f48d2daa65eada801d83f55c5c17a2df`. Component reviews: `research/willow-finishing-recall-4d08241-source-review-20261024-v1.md` and `research/willow-sighting-arbitration-4d08241-source-review-20261024-v3.md`.

Combined29-file manifest: `research/willow-recall-sighting-4d08241-source-v1-manifest.sha256`, aggregate `29ac1251ddc63c1b3e824d9c1d6182df57890e62b3757d5e362fe15be3a91e60`.
Full baseline delta: `research/willow-recall-sighting-4d08241-source-v1.patch`, SHA256 `83433f94747168e0b64eb7223022944a61a12db8bf9ede147e195c1fa0fe660e`.

Verification is a clean union: baseline differs only in bot.cpp, comms.cpp and comms.h; combined bot.cpp byte-matches the frozen recall child; both combined comms files byte-match sighting v3. Directory comparisons show only comms.cpp/h differ from recall and only bot.cpp differs from sighting. The manifest contains29 files. No whitespace diagnostics from no-index diff check. Private recall scalar plumbing and communications wire/API retain the exact reviewed component implementations; no integration behavior was added.

Root reports component native/fixture evidence separately: recall first divergence at738 kept the channel and completed739, preserving Prism later but still losing588–1014; other parent comparison outcomes stayed unchanged. Sighting v3's13 protocol fixtures passed and the native Pilgrimage A result stayed1030–210 at1358 with no own rollovers/errors. This worker did not run those checks. No combined runtime result or outcome gain is claimed. Root will dispatch independent integration review and Luna owns build/runtime.
