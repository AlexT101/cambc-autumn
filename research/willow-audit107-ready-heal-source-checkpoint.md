# Upstream107 + Willow ready-heal integration checkpoint

2026-10-23. Root authorized a new source-only child `bots/variants/willow-audit107-ready-heal-work/src` of frozen ee1b404, integrating the exact upstream eaee598→b7bfcb7 revert of CHANGES108. The current source preserves db5b support, repaired de1c transit,06b266 independent ready-heal and ee1b optional buff97 handling. No Monolith crew, itemization or other new gameplay policy is included. No builds, engines, extraction, scripts, git merge/index/commit, canonical/release edits or EXPERIMENTS changes.

## Exact source and artifact pins

| Artifact | Pin |
| --- | --- |
| Upstream revert commit | `b7bfcb7ee9b08e852578fb34fbb36d1c351f7d37` |
| Upstream Git source tree `bots/hyperion/src` | `132a65c233fca01bbfa5ac4c2fcd081deb0715c4` |
| Frozen `bots/baselines/hyperion-upstream-b7bfcb7/src` aggregate | `d6bac05921106e332ee4648b5034e748c65aff111cef3f5110d503bedcf1834a` |
| Common eaee598 commit | `eaee5986e7df268757a492eabc130518200f8f0a` |
| Common eaee598 source tree | `4a129f3a0a1772b68e028f44587da2905ba585c0` |
| Frozen ee1b parent aggregate | `ee1b404d8e50bc188c092739142d6a1f5bcf078756f643588d2693ccf94c7b10` |
| **Integrated child aggregate** | **`a00fff454c1e48520968c9ba2d4c1ecdae0212ce019724dc06a6e959ddc3412e`** |
| Full ee1b→child patch `research/willow-audit107-ready-heal-from-ee1b-source.patch` | `caa817c3b91edbbfe7049bbe8b8dc6fc54052e415bc584705fdd4db4bd708828` |
| Full b7bfcb7→child patch `research/willow-audit107-ready-heal-from-b7bfcb7-source.patch` | `3d35f62d24d9fbd4c0e8edf274d709691ba0370e6d06227a581b495c4a16b3a5` |
| Child29-file manifest `research/willow-audit107-ready-heal-source-manifest.sha256` | `a00fff454c1e48520968c9ba2d4c1ecdae0212ce019724dc06a6e959ddc3412e` |
| Baseline28-file manifest `research/hyperion-upstream-b7bfcb7-source-manifest.sha256` | `d6bac05921106e332ee4648b5034e748c65aff111cef3f5110d503bedcf1834a` |

Aggregate convention: `shasum -a 256 src/* | shasum -a 256` from each bot directory; manifests contain the exact first-command output. New baseline was exported with `git archive` directly from the pinned upstream commit, source only, and is frozen. Both new bot folders contain only `src`, no `.cambc`. ee1b aggregate rechecked unchanged.

## Merge boundary and signatures

Copied ee1b source to the separate child, then ran `git merge-file --diff3` against frozen eaee and frozen b7bf for each of the six upstream-changed files. Five merged cleanly. One conflict in `bot.cpp:decide` was resolved by keeping the entire existing Willow economy/escape ownership, exact mate eligibility and independent ready-heal block, with the restored upstream `want_home(world,safety,...)` call.

All definition/call sites were searched after conflict resolution, not only marked hunks. `holding_capture`, `paying_soon` and `outmatched` again take only World; `want_home` and `continue_tribute` no longer take Pathing. Four added support callers required manual `holding_capture(world,pathing)`→`holding_capture(world)` updates: Willow economy/capture4461, bank-heal admission4673, Prism recovery protected hold4847 and decide protected-work5100. The new ready-heal helper consumes the same originally computed protected-work output, so no independent hold predicate or duplicate shop/eligibility query was added. All other signature changes arrived through the upstream merge. No const-cast, compatibility overload or retained108 hold rule exists.

## Preserved/reverted semantics

- **Exact upstream108 revert:** removes bank-deadline coupling from holding capture while retaining107 `pays_too_late`; restores prior allied capture dating after unseen gaps; restores unseen threat fields around walls, prior known-priority escape judgments, geometric unit-only kite stations and conservative live-camp dash blocking; removes Search's108 ward-view grid extension. These are upstream choices, applied without selective retention.
- **Upstream107 remains:** actual acted/respawn dating and unseen tribute/recall fixes; living-member `awake_over`; submit-after-lock safety; unseen Ren retaliation veto in search/dash; current self shield in priority protection; stun-only recall cancellation bid; turn-order exception catch. Visible ally positive-duration stun/teleport arrival logic also remains, so ee1b's rc97 repair is still relevant.
- **ee1b rc97 repair remains:** the same buff import returns `optional<bool>`,97 is unknown, successful positive/zero/absent stun retains its interpretation, all other errors still throw. Unknown or positive delays the ally one turn, preserving original teleport/immune/self/enemy precedence. No eager snapshot or extra SDK query.
- **db5b support remains:** native5 P/V/M/Willow/HoR; latest native3/4; Treasure/Bruiser completion model plus optional Willow Jungle Health; endpoint roster-presence gating, recovery/formation controller/mailbox, actual restored-health value, strict nine-station safety/member index, bank-heal step and mutable World refresh. Destination-aware broadphase still uses pending teleport destination and latest foe/Strike timing; no old Safety wholesale copy was introduced. Underlying unseen fields now intentionally follow b7bf's restored wall-aware model.
- **Repaired transit remains:** exact de1c stall-only homeward exception, fresh successful asleep read mask/epoch, zero/unknown-health rejection, eight-ray bounded camp reserve, no tank/future-heal credit, original comparator/retries and at-most-one successful walk. No change beyond the surrounding upstream hold signature.
- **06b266 ready-heal remains:** unchanged eligibility/protection outputs, eligible-stunned Prism preservation, real current healability including ward-visible targets, strict stations, gain>3B plus conservative current member-finish veto, one attempted move, fresh observation/real heal and ephemeral ownership. Removing Search's ward-grid extension does not remove this helper's real visible-record current-heal test or alter its terrain-certified candidate sight.

## Exact scope and validation limits

From ee1b exactly six files change: bot.cpp, plan.cpp, safety.cpp/h, turn_order.cpp and world.cpp, **39 insertions/106 deletions**. This equals the exact upstream35/102 plus four necessary added-support caller replacements. From b7bf exactly the established12 support files differ: bot.cpp/h, comms.cpp/h, draft.cpp, draft_selection.h, plan.cpp, safety.cpp/h, support_mailbox.h and world.cpp/h; **1163 insertions/21 deletions**. `turn_order.cpp` is byte-identical to b7bf; ordinary upstream abilities/self-abilities files remain unmodified.

Read the actual complete parent delta, direct new-main safety/plan intersections and all support/heal/hold seams. No unresolved conflict markers or old-arity calls remain. Both complete diffs pass whitespace checking without diagnostics. Source verification is not compile/runtime qualification. Old ee1b results remain attached to their frozen source; their mechanism or outcomes do not automatically qualify this integration. Root/Astra actual review must precede Luna compile/native panels, with protected capture/bank/escape, strict station/teleport behavior, ready-heal and sleep-transit paths retained as primary seams.
