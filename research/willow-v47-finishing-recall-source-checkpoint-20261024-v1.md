# v47 finishing-recall isolation source checkpoint

2026-10-24. Cambridge Battlecode rules read. Source-only regression isolation; no build, runtime, submission, tooling/helper implementation, canonical change or EXPERIMENTS edit. Farm-hop remains held.

Parent: frozen own archived v47 `bots/astraeus`, 29-file source aggregate verified before and after copying: `f475b8521cada611754076822402a266c43be8de76ce0f2b504b268ff3335824`.

Child: `bots/variants/willow-v47-finishing-recall-work`, src only, no `.cambc`. Its 29-entry manifest is `research/willow-v47-finishing-recall-source-v1-manifest.sha256`; aggregate `64d9c8fd9d587d898139983138341b8346681fc2c32a0804c359ae25613c9cb5`.

Patch: `research/willow-v47-finishing-recall-source-v1.patch`, SHA256 `10982649c28e0e8d47de8b8868fcdec4c5662f444e295e9c7ba5f0c029aeebdf`.

Only `src/bot.cpp` changes: 22 insertions, 4 deletions. Removing diff headers and hunk locations gives byte-identical contents to the reviewed `research/willow-finishing-recall-4d08241-source-v1.patch`. The three hunks add the already-evaluated suppressed-pack scalar, initialize/thread it through want_home, and preserve an existing recall in the narrow non-winning held-capture/early-landing case using the original threat/tribute/outrun checks. Normal home=true behavior, game-ender precedence and cached-false fallback remain unchanged.

No shield pricing, dash-aware altar distance, bound-elsewhere capture-allocation or midturn killed-enemy update is included. All other 28 source files match v47 byte-for-byte. Params and draft sources are unchanged; default production draft remains selected (`test_draft=false`). No whitespace diagnostics, patch rejects, backup files or `.cambc` directories remain. These are source checks, not compilation or behavior results.
