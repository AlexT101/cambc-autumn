# Astraeus e72724a source freeze and build preflight

- Frozen commit `e72724a010e11b599e61e224b0b992963ae84e0d`; commit tree `395d3848d06445825abafe25fe878ddc73ab3978`.
- `bots/astraeus/src` tree `73aae31e8459f19c7c1da2ca9b83e572bffa0b0e`, identical to `315910d6db2ed18ab793ca4b2f87b21c2c1eb472:bots/astraeus/src`.
- Baseline and candidate each contain 29 source files, byte-identical to Git. Aggregate SHA256 `57f6908fcac310582d5b02606d8742c76c10a57f3a871c6a09792af115289369` using the frozen Khaos v33 manifest recipe.
- Frozen Khaos v33 aggregate `a00fff454c1e48520968c9ba2d4c1ecdae0212ce019724dc06a6e959ddc3412e`; matching source files `29/29`. The v44 source identity record rows match their expected values and Khaos v33: `True`.
- Full `source-before` and independent `source-after-baseline`/`source-after-candidate` snapshots and manifests are preserved here.
- Prepared, not executed: `nice -n 19 env CMAKE_BUILD_PARALLEL_LEVEL=1 /Users/yufan/Desktop/Development/CambridgeBattlecode2026/current-autumn/tools/runtime/cambc-3.0.5/cambc build /Users/yufan/Desktop/Development/CambridgeBattlecode2026/willow-upstream-development/bots/variants/willow-astraeus-e727-work --release > /Users/yufan/Desktop/Development/CambridgeBattlecode2026/willow-upstream-development/provenance/astraeus-e72724a-freeze-20261024-v1/candidate-build.stdout.log 2> /Users/yufan/Desktop/Development/CambridgeBattlecode2026/willow-upstream-development/provenance/astraeus-e72724a-freeze-20261024-v1/candidate-build.stderr.log`.
- Exact CLI, SDK inventory, CMakeLists and engine pins are in `preflight.json`. No build, match, checkout, or gameplay edit occurred.
