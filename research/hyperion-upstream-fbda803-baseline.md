# Hyperion upstream fbda803 baseline

This is an immutable source-only snapshot of `bots/hyperion/src` from `fbda80314d703877c3929e2dec8211c61f5d1e79`. All 28 files were byte-checked against that Git tree. It has no `.cambc` or compiled artifacts. Source aggregate: `15dcd64d35c179a726c02d3e775b1e3f263f9a4c33b5a8c745e7b13f66dd802d`; per-file hashes are in `bots/baselines/hyperion-upstream-fbda803/source-manifest.sha256`.

Compared with the frozen `eaee5986e7df268757a492eabc130518200f8f0a` baseline (aggregate `a97aeefdf861fa71e26bf9908e7cb26eeb326b95cf3ef50b58cd62b810aed925`), exactly three source files differ; all other 25 are byte-identical:

- `src/bot.cpp`: `prey()` now remembers failed `(key, delayed)` fight evaluations and skips repeated `chase_trade` work for the same pair within the current search.
- `src/main.cpp`: the out-of-fuel resume diagnostic and OOF marker are inside `debug_block`, avoiding the release-mode printing cost; the shortcut accounting remains.
- `src/world.cpp`: `StaticMap::groups_near()` replaces a linear duplicate search through the output list with a generation-mark vector indexed by group.

This records source-level changes only. It makes no runtime performance claim. No gameplay qualification was run.
