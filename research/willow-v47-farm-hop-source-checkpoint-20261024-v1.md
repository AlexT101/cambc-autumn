# v47 ordinary farm-hop port checkpoint

2026-10-24. Cambridge Battlecode rules/local instructions read. Source-only preparation for the authorized v47 baseline / hop / escape / combination isolation; no build, game, tests, scripts/helpers, SDK/tool change, canonical edit, EXPERIMENTS edit, release or submission. Existing variants remain preserved. Connected-camp escape and any later recall overlay are not included.

Frozen parent: `provenance/willow-astraeus-clock-recovery-20261024-v1/workspace/bots/service-base-f7`, 29-file source aggregate verified before/after copying: `f475b8521cada611754076822402a266c43be8de76ce0f2b504b268ff3335824`.

New child: `bots/variants/willow-v47-farm-hop-work`, src only, no `.cambc`.
Manifest: `research/willow-v47-farm-hop-source-v1-manifest.sha256`, 29 entries; source aggregate `63f5deb00dbf445d3e60261f78b359d4931939751d0eb00f843750a8ecaa7f8f`.
Patch: `research/willow-v47-farm-hop-source-v1.patch`, SHA256 `2e633f7502be683f6ce04278a1057f23c25cd55d7378a1ef9b1dd47ece830d8c`.

Port source: immutable `research/willow-ordinary-farm-hop-v34-source-v2.patch`, independently rehashed to `ac73f6d1012698ebb2446fdc4e4e562c301452c5d872dc8ec6044a858a3c58a1`. Read its v2 checkpoint and the immutable v1 review's hazards before porting. The full patch applied without conflicts or new gameplay logic. After removing path/index headers and hunk locations, every port patch hunk/context body is byte-identical to v2. Both deltas change only bot.cpp, bot.h, safety.cpp and safety.h: 181 insertions, 6 deletions. The latter three complete files also compare byte-identical to the existing v2 child. Other 25 source files match frozen v47; no whitespace diagnostics, patch rejects or backup files remain.

Exact retained v2 functionality: already-selected independently affordable ordinary farm objective only; prepared field and <=49 local candidates; ready-dash normal alternative; full cycle/respawn waiting and 10-gold replacement cost; altar reservation and current funding; conservative three future source camp phases R+1..R+3 and first landing phase R+4; zero-residual live-melee timing correction; expanded credible-enemy horizon without the v1 universal untracked-enemy veto; quote/topology/guard/occupancy revalidation; one failed-use refresh/fallback; terminal crystal ownership for new and existing altar channels; separate farm purchase intent confined to normal shopping. Original v2 limitations, knowledge assumptions and cost bounds remain; the port does not improve or certify them.

No other v48 changes imported: original v47 outmatched/want_home/continue_recall behavior and capture_taken signature remain; planner shield pricing, Pathing altar distance and World midturn enemy handling match v47. No deadline-bound optimization, sighting arbitration, boss arm or support-policy change is present. Params and all draft files match parent byte-for-byte, including `test_draft=false` and the production Willow draft setting.

This is the corrected v2 arm, not the rejected v1 implementation. The old v1 review did not certify v2, and independent review of the pinned port remains required before runtime. No compilation, activation, economic improvement, fuel result or safe-channel fixture is claimed. A later hop+escape child must be an explicitly reviewed combination rather than a silent edit to this pinned source.
