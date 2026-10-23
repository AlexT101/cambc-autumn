# Latest Hyperion integration source checkpoint

2026-10-23. Resolves the active root-owned merge into canonical `bots/hyperion/src`. Upstream is `fbda80314d703877c3929e2dec8211c61f5d1e79`, source Git tree `c7f483145a44c24bf9763041d72aed52f81d7a16`. Root's pre-merge HEAD was `b4fba6b827c7dbb5c443dfe412de5590b4cf09c8`. This agent edited source only and created these source-review artifacts; no staging, commit, push, compiler, engine, scripts or runtime. Root retains index/research-merge/commit ownership.

| Artifact | SHA-256 |
|---|---|
| **Canonical29-file aggregate / manifest** | **`337f42a54beb5890109e56b755237d8ea0d07abb240d095778f01e2098ab7b39`** |
| `src/bot.cpp` | `6a41ad3340c53df490eb6bf23b78533a44aa2c7e796aa853d3dc0a757daaa52a` |
| `src/main.cpp` | `3b4d3839133bcf1a4291ca3a2f2a6e820ad4e38cc9479e4e9d6bc70b1e1db9c7` |
| `src/world.cpp` | `7afdfd0f033d520fd7a13523ceb1e7c7e9973b56bc69f294525945347a9c2c92` |
| Full fbda803→canonical patch | `7fa73a788370279ae0f11d86da726a1897d435c5241fea954d583b9a7ef0401b` |
| Full a00fff→canonical patch | `3c93ed64963490495624ec1a17862d7756f94297528c8ad0597989ed8ac5c4b1` |

Files: `research/willow-latest-fbda803-source-manifest.sha256`, `research/willow-latest-fbda803-from-upstream-source.patch`, `research/willow-latest-fbda803-from-a00fff-source.patch`. Aggregate recipe from `bots/hyperion`: `shasum -a 256 src/* | shasum -a 256`; manifest is the first command's exact output. Whitespace check is clean, no source conflict markers remain. Git's source conflict remains unmerged in the index until root stages the resolved working file.

## Exact reconstruction

Frozen `willow-audit-live-ally-work` ee1b404 is the reviewed a00fff support/transit/ready-heal/optional97 source with upstream108 reapplied. It was copied into a temporary source directory and the exact `git diff 7a5d178..fbda803 -- bots/hyperion/src` was applied with stripped source paths. `diff -rq` found no difference between that independent reconstruction and canonical; both aggregate to337f42a5. No extra gameplay integration logic was needed beyond qualified108 context.

Canonical differs from ee1b in exactly3 files,19 insertions/3 deletions: upstream prey's per-invocation lost-fight memo (`bot.cpp`), Debug-only resumed-turn OOF logging (`main.cpp`), and stamp-based `groups_near` deduplication preserving encounter order (`world.cpp`). This exactly includes commits9462644/b492152/c05267b. Canonical vs a00fff is7 files,125 insertions/42 deletions (all108 plus those3 changes). Canonical vs latest upstream retains the same12-file qualified custom scope,1163 insertions/21 deletions.

## Merge and semantic seams

Only source conflict was `decide` in `bot.cpp`. Resolution preserves its complete Willow economy/escape ownership, local support/retreat and independent ready-heal blocks, while adopting `want_home(world,pathing,safety,...)`. Four custom `holding_capture` callers now pass Pathing: Willow economy capture protection, bank-heal step guard, Prism recovery capture exception, and inserted local-support protected-work calculation. No old holding/want_home/paying_soon/continue_tribute signature remains. Upstream's complete holding-capture deadline, want_home/outmatched/paying_soon/continue_tribute signature chain is present.

All107/108 changes are retained by the reconstruction identity, including ward/LOS/capture/threat/ally timing fixes. Optional api97 unknown pending-stun handling and conservative arrival delay remain exact ee1b; custom teleport-destination-aware credible broadphase, member index/asleep certificates, actual-health support, mailbox publication after the turn-order catch and bank-heal behavior are preserved. Native draft remains qualified a00fff. No forecast formation, deadline staging, local Monolith crew, four-pick replacement or other experimental arm entered canonical.

Root/Astra actual review precedes runtime. This checkpoint establishes source composition and identity only, not qualification of the latest upstream combination. Existing a00fff and all experimental/frozen sources remain unchanged.
