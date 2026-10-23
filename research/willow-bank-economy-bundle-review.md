# Willow bank/economy bundle actual source review — 2026-10-23

**Approved for the planned broad native1104 comparison against frozen130. No actionable source blocker found. This is not release approval or a claim of combined improvement.** Read the Cambridge Battlecode rules, actual parent/bundle and donor diffs, the bundle checkpoint/full patch, and the existing bank-heal, station-cost and dense-draft contracts. No build, engine, extraction, script or gameplay edit was performed; only this review note was added. Root owns EXPERIMENTS and test scheduling.

Independently verified bundle aggregate `a2794129e115abb70faaa5a7e3c66b9728898b0e52c5542fa7885091eaec0bb6`, using the established `shasum -a 256 src/* | shasum -a 256` convention. Independently rehashed all three donors:

| Component | Exact donor aggregate |
| --- | --- |
| Station-member index v2 | `12f3a622d3907f31f32dd34e80e9436df75f84c59f2282c32fe6846b3b2840a9` |
| Actual one-step bank heal | `fab7c7b13e8271a933a6b7d250f4e3627f5112fc1a6d85c9d98f78b1982b7e7f` |
| Dense native fifth-slot Vendetta | `2dd4084d601fc89138afa7df45372d45260ad8d23313e3e6f56e249f1bb26a69` |

Recursive comparison against frozen130 `130a17af668a432a8a5582ec0736b1ef13c22e05245bc5742e472f3d02a620a5` finds exactly `bot.cpp`, `world.cpp`, `world.h`, `draft.cpp`, and `draft_selection.h`. Direct comparisons establish world files byte-identical to index-v2 and draft files byte-identical to dense. Bundle-versus-index `bot.cpp` contains only the reviewed bank-heal additions/plumbing; bundle-versus-bank `bot.cpp` contains only the reviewed index path. The full parent diff agrees. Whitespace check emits no errors. This independently corroborates Sol's donor-reconstruction evidence without requiring another reconstruction or build. No bb836 formation, post-dash, economic pricing, farm routing, P67 diagnostics or new fuel gate is included.

## Interaction review

The only direct gameplay/index intersection is `willow_bank_heal_step` calling `willow_step_guard`. Index-v2 keeps only static contributing member identities and integer depth, preserving original group/member order and `groups_near` cache effects. Evaluation still rereads current clear/respawn state, member health and sleep before adding camp risk/damage. Enemy additions precede camp additions and float order remains unchanged. Raw fallback calls remain on the original path. The bank helper therefore receives the same strict origin/candidate exposure contract; it does not inherit stale camp safety from the static index.

Each span is consumed synchronously inside one exposure evaluation before another station query can grow the pool. The bank helper stores station values, not index spans. Its later `see_again` may rebuild stations and grow the static pool without invalidating an outstanding span. The chosen banking field lives in separate Pathing-owned storage and survives those refreshes. Map ownership, bounded lazy pages, geometric growth, pending-entry publication and existing stale/action boundaries remain the reviewed v2 implementation.

Banking still prioritizes immediate tribute, locked/avoided altar selection, pack routing, hop/crystal, dash and lock handling before the actual-heal step. Forced/retreat, winning/closing and held/contested capture exclusions remain. The helper requires no worthwhile current heal, current readiness/gain, safe legal adjacent range/LOS, and finite nonincreasing distance in the same chosen field. Successful movement refreshes and attempts a fresh heal; failed movement refreshes before ordinary banking. No ownership or Memory write was added.

The draft arm changes only native five's last champion when `3ull*members > 10ull*groups`. Three/four, first four of five, test-draft precedence, fallback and draft memory retain donor semantics. Counting remains the existing bounded map-layout query inside cached selection. The bank helper can target any eligible ally and does not assume a fifth-slot HoR, so Vendetta introduces no source-level index or identity mismatch. It does change real team economy, movement, healing opportunities and opponent interactions, which require combined games.

Root's separate donor evidence—index544–560/1104, bank39–41/80, dense43–37/80—does not add into a bundle estimate. Prior formation-containing combinations regressed despite useful isolated arms. Index cost savings may change native rollover timing, and dense rosters may change bank-heal frequency; neither is established here. Keep this source frozen for the requested native comparison, inspect errors/rollovers and switched/unchanged roster strata, and require the agreed untouched confirmation before any later promotion decision. This review authorizes the native1104 stage only.
