# Astraeus cb61eaa source freeze

Frozen Git commit: `cb61eaa5276b527c0de85db9b3bcfa0fdadd4a50`.
`bots/astraeus/src` Git tree: `378a2ea31787e642630d179146ef33e43ca1bb9a`.

Baseline: `bots/baselines/astraeus-cb61eaa/src`.
Untouched source control: `bots/variants/willow-astraeus-cb61-work/src`.
Each contains all 29 files exported directly from the frozen Git tree. The tree has no separate bot configuration file: compiled `params.h`, draft configuration and all other source configuration are among the 29 files. Neither directory contains `.cambc`.

Before, baseline, control, independent after-baseline and independent after-control manifests all have aggregate SHA-256 `369742e3f54259c675c0d4b508a02c0c4517eef6e1cb3ef6f42fa776194180ea`.
Recipe: `(cd <botdir> && shasum -a 256 src/* | shasum -a 256)`.
The corresponding 29-row relative manifests are `before-relative.sha256`, `baseline-relative.sha256`, `control-relative.sha256`, `after-baseline-relative.sha256` and `after-control-relative.sha256`. The full before/after sources are saved here under `source-before`, `source-after-baseline` and `source-after-control`, each with its own `src/` directory.

`upstream-delta.patch` records the complete Astraeus change from e72724a to cb61eaa, inspected before export: bot.cpp, bot.h, comms.cpp, self_abilities.cpp, world.cpp and world.h. The upstream changes include Willow support/fuel work, heal visibility/readiness corrections and removal of unused state. The new freeze retains them exactly. The older e72724a baseline was neither overwritten nor modified.

This is a source identity record only. No build, engine, match, canonical source edit, commit, push or merge was performed. Earlier e72724a runtime observations are not claims about this source.
