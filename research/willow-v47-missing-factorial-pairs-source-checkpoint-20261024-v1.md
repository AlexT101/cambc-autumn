# v47 missing factorial pairs: exact-union source checkpoint

2026-10-24. Explicitly authorized source-only completion of hop+mixed and escape+mixed. Cambridge Battlecode rules read. No adaptation, new policy, build, game, scripts/helpers/tests, SDK/tool changes, canonical edit, EXPERIMENTS change, release or submission.

Frozen reviewed inputs independently rehashed unchanged before composition:

- Hop `bots/variants/willow-v47-farm-hop-work`: `63f5deb00dbf445d3e60261f78b359d4931939751d0eb00f843750a8ecaa7f8f`.
- Escape `bots/variants/willow-v47-connected-escape-work`: `4b5a71e6535bb7b0ccfec3ad26fa6a1c5cef066807576792384e9966efdc0343`.
- Mixed approach `bots/variants/willow-v47-mixed-camp-approach-work`: `afd057fa1051e21d0c09cea4ae7cb594afe5b4de7e796cf46ae43ab06ae3871e`.

All descend from frozen service-base-f7/f475 `f475b8521cada611754076822402a266c43be8de76ce0f2b504b268ff3335824`. Existing single, pair and triple variants remain unchanged.

| Child under bots/variants | 29-file source aggregate | Delta versus f475 |
| --- | --- | --- |
| willow-v47-hop-mixed-approach-work | `7e5dc37a4b897a38f2cd2cffedfed6f8c68562698919b929210fe2b538d1fb88` | 5 files,188 insertions/8 deletions |
| willow-v47-escape-mixed-approach-work | `e8d10ca2f5680692faa541d9b725849f0927580c61bd6f6e2d7711e3e0e603fc` | 6 files,220 insertions/51 deletions |

Manifests: `research/willow-v47-hop-mixed-approach-source-v1-manifest.sha256` and `research/willow-v47-escape-mixed-approach-source-v1-manifest.sha256`; each has29 entries and SHA256 equal to its aggregate above.

Full-file exact-union proof for each pair: clone the respective hop/escape parent, then copy only mixed approach's abilities.cpp. That file compares byte-identical to the reviewed mixed parent, and recursive comparison against the hop/escape input reports abilities.cpp as the only differing file. Therefore the other28 source files match the selected parent exactly. The changed-file sets are disjoint, requiring no hunk adaptation or new integration logic. Default draft/params and all unrelated files remain f475. Src-only copies contain no `.cambc`, backups or rejects; no whitespace diagnostics.

Hop+mixed patches:

- Versus f475: `research/willow-v47-hop-mixed-approach-source-v1.patch`, SHA256 `599b8e5a1e15d9b52c8cb904f61ea52e558c97a83b2765db102b2b1699cfde51`.
- Versus hop: `research/willow-v47-hop-mixed-approach-vs-hop-source-v1.patch`, SHA256 `4ddabc5bc40a5b1f0d510a48072bc05fccf5bb8011b78dbb3ec3364bd9401f37`.
- Versus mixed: `research/willow-v47-hop-mixed-approach-vs-mixed-source-v1.patch`, SHA256 `56337db4b1f7b4764b12ec369ce765122068e72c259e08eff2d8f7955cb7aaff`.

Escape+mixed patches:

- Versus f475: `research/willow-v47-escape-mixed-approach-source-v1.patch`, SHA256 `0e4048deaae2a583c221610e57af476eeeeebf0d5c28a0e36e9b11e336550144`.
- Versus escape: `research/willow-v47-escape-mixed-approach-vs-escape-source-v1.patch`, SHA256 `de44860fccb625051a0a39d131719bd8da6fb81ce410591f5f538f4f8ff380f1`.
- Versus mixed: `research/willow-v47-escape-mixed-approach-vs-mixed-source-v1.patch`, SHA256 `ebcc4eea0a9a3b700896e1bab561ed68897354c9fca431e1c7c9ddc69b3009ba`.

Both preserve all reviewed arm limitations and original interaction semantics. A successful mixed approach cast returns before ordinary movement/hop; the original r7 damaging-exposure refusal is retained. Hop+mixed contains no escape change; escape+mixed contains no hop change. Neither contains generalist support, fixed-roster substitutions, recall, deadline-bound, communications, boss or other v48 overlays. This is exact source composition, not a runtime result or a requirement that either single arm first win. Luna owns the missing factorial runtime cells.
