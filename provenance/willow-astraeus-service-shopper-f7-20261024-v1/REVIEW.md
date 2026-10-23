# Service shopper: mechanical port to f7d54e9

New candidate: `bots/variants/willow-astraeus-service-shopper-f7-work/src`.
Exact upstream parent: `f7d54e9e742c3a09ab597c588149b0f0fe3520df`, all 29 Astraeus source files, aggregate `f475b8521cada611754076822402a266c43be8de76ce0f2b504b268ff3335824`.
Ported candidate: all 29 files, aggregate `730051ef2d15d38f6d84abe3ae250586100c3323c3bb439ca2bfcc516ac1737f`.
Recipe: `(cd <botdir> && shasum -a 256 src/* | shasum -a 256)`.

The original frozen cb61 prototype remains unchanged at `bots/variants/willow-astraeus-service-shopper-work/src`, aggregate `effae506db059367407528fd258c43344276101be09954ad75e9f5c39db59e1c`. Its complete provenance/review stays at `provenance/willow-astraeus-service-shopper-20261024-v1/`. No repair or policy change was folded into this port; independent review of the original service implementation remains pending.

Procedure: inspect exact `git diff cb61eaa..f7d54e9 -- bots/astraeus`, copy the frozen cb61 candidate, and apply that saved upstream diff with ordinary patch tooling. `upstream-delta.patch` preserves the exact Git diff. The entire source delta is four lines in Prism's stationary support branch: take a free basic against an enemy or a wholly harmless camp group while waiting in place for Willow. They are disjoint from the service collector, utility, profile lifecycle and quote hooks. `port-only.patch` records the complete candidate-to-candidate comparison and contains exactly those four added lines in bot.cpp. Every other source byte is the original prototype's byte.

`before-src` was exported directly from the pinned f7 Git tree and compares byte-for-byte equal to the latest canonical Astraeus at handoff. `after-src` preserves the complete new candidate. The 29-row relative manifests normalize filenames to `src/`. `source.patch` is the full service experiment against the new upstream base; as in the original, only bot.cpp, self_abilities.cpp, self_abilities.h and plan.cpp differ from that parent. All source snapshots/manifests are pinned here.

The shared implementation/assumptions, coordinator clarifications, diagnostic seam and source risks are documented in the original prototype's REVIEW.md. The port keeps the same signed full/prefix/Prices utility, last-eight successful-scan profile, missing-data exclusion, shop-visit publication, pending epoch invalidation, planner-heal coverage bias, explicit cache revision, after-Treasure candidate scope and debug_block-only diagnostics. Added ready-field SDK lookups and profile arithmetic retain the same unresolved fuel cost. No runtime activation, no-Willow equivalence, purchase outcome or competitive gain is claimed for either identity.

No `.cambc` was copied. No build, test, engine, canonical/sibling edit, helper script, commit or push occurred. Original and ported candidates are separate identities for subsequent independent source review and, if accepted, separately pinned runtime checks. Any requested service repair should be applied to each identity explicitly without overwriting this frozen port record.
