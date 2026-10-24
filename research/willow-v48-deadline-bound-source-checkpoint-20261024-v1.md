# v48 walking-deadline bound source checkpoint

2026-10-24. Cambridge Battlecode rules and `research/khaos-v48-isolated-control-first-fork-review-20261024-v1.md` read. Root explicitly authorized this independent prospective source preparation while the Starvation diagnostic remains pending. No build, game, helper/script implementation, canonical edit, EXPERIMENTS edit, release or submission.

Parent `bots/Khaos_v34`, 29-file source aggregate verified before and after: `781fe3641afc4333d8c8a1b42f1344b4ba19edf9d96ae092e9e62069b9083d68`.

Child `bots/variants/willow-v48-deadline-bound-work`, src only, no `.cambc`. Manifest `research/willow-v48-deadline-bound-source-v1-manifest.sha256`, 29 entries, source aggregate `46c5b5580f63e14d47c4cb3887ea7f626af6abed4a42eebfb0d635ec22d7703d`.

Patch `research/willow-v48-deadline-bound-source-v1.patch`, SHA256 `587a57e6e3b344e92cfec28c0bbaee6eac8385af2387da3dca0704e2984d265e`. Only `src/bot.cpp` changes, 9 insertions and 1 deletion; other 28 files match parent. No whitespace diagnostics. Params/default production draft remain byte-identical (`test_draft=false`). Farm-hop and Gem Fields policy remain held.

The only changed code is farm's `too_late` lambda. If its exact `known.to_altar` is unset and the existing `draft_spawn_graph` is false, it reads the optional drafted walking distance. A present finite value may prove false only when the original full deadline sum, with that walking distance substituted, is <=left. The sum retains integer addition followed by float conversion, then adds clear_rounds, matching the original arithmetic order. The bound is never assigned to `known.to_altar` or a Pathing cache.

Source edge review:

- Exact-cache present: original predicate, no new draft read.
- Walking-graph actor/no crossables: existing bool skips the shortcut; original exact path.
- No draft plan, walking unreachable or bound exceeding deadline: original exact centre_to_altar lookup and predicate, including the original exact-unreachable means no deadline behavior.
- Equality at deadline: false, matching the original strict > predicate. Zero finite walking distance is valid.
- A finite walking route bounds either static dash graph because both retain walking edges and use the identical centre and tribute goals. This is a proof for the existing static estimate, not actual future movement, cooldowns, occupancy or altar safety.
- Early false leaves the exact cache unset, so later bag/chained-cycle valuation still obtains the corrected exact graph distance. Repeated early calls may repeat only the optional scalar read/arithmetic. No new native import, field, board, global search, fuel gate or policy memory is introduced.

This is a prospective repair to decision work/coverage. Avoiding cold field construction or changing code generation can change downstream existing fuel cutoffs and actions; byte-identical fuel-only behavior is not claimed. The pending trusted Starvation trace must still establish whether this cost path explains its first fork. Compilation, runtime activation, fuel benefit and competitive value are untested here.
