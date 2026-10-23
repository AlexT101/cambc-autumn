# Current Willow support cost review

2026-10-23, read-only source review of frozen candidate `db5b37d5e5c609c2c616d3a39c0f1eb7f5adebf401dcd1be8848e0eede237ab8` against latest-main baseline `d8d3cc1da72aaf62eb65fc5de8402b9c3a98a8aade1fabeb5cd9841b3ff01e2c`. No implementation, script, build, extraction or runtime work. Read `research/hyperion/FUEL-GATES.md`; neither proposal adds a fuel gate, path search, map-wide board or less-safe fallback.

Published five-pick rollovers (432 versus242) and generated-panel totals (2209 versus1532, as reported by root) establish a cost concern, **not** attribution to Willow or her nine stations. The candidate's 12-file delta also includes changed draft, Prism recovery, comms and item behavior. Existing branch/actor frequency and fuel measurements must precede a claim about the cause of the excess.

## What is already saved

- `bot.cpp:4323–4356`: `willow_step_guard` memoizes all nine station records by round, `support_vision` and actual origin. Repeated `willow_economy_or_escape`, local-support and bank-heal calls in that epoch consume the records; they do not normally recompute nine threat/camp passes. The wrapper scans at most nine cached records to find a requested tile. That tiny lookup is not a convincing major target.
- `see_again` (`bot.cpp:2678`) increments the vision epoch, invalidates Pathing and reconstructs Safety before rebuilding an installed Willow guard. This is required after successful movement and hidden-blocker failure. The later fresh station pass is not a redundant cache miss merely because it occurs in the same round.
- `safety.cpp:1711–1809,1897–1916`: enemy list, liveness, Strike/credibility, Reach and Reach's per-tile blows are already cached. A nine-tile loop does **not** imply nine enemy-liveness SDK calls or nine full Reach builds per enemy. `Reach::at` itself memoizes blows (`1498`).
- The member index (`world.cpp:392`) already limits camp scans to actual static members that reach the tile, retaining group/member accumulation order. Its unconditional `groups_near` call intentionally preserves the previous scratch/cache effects. Simply deleting that call is not an innocuous exact port: it changes the shared radius cache and later work/fuel behavior. Do not reopen it without a separate measured cache contract.
- The final fresh support-intent observation at `bot.cpp:5095` does not rebuild another nine stations: `act` clears the guard at5050 before this observation. Its current-position exposure falls back to the raw path. Omitting that observe would weaken the actual-ready publication boundary and is not recommended.
- `my_can_move` inside the local-support loop is a fresh raw self-record SDK read (`util.h:79–93`), but at most eight cheap reads are involved and the guard builder already hoists its own copy. Hoisting this alone is unlikely to explain hundreds of rollovers.

## 1. Conditional material opportunity: per-enemy nine-station broadphase mask

Current path:

1. `bot.cpp:4335` calls `Safety::credible_enemy_may_hit_within(here,1)` once.
2. If **any** credible enemy might hit any neighboring station, all open stations call `support_exposure_raw(..., include_enemies=true, ...)`.
3. `Safety::threats_at` (`safety.cpp:1932`) then iterates every live credible enemy for each station. In its unbuilt branch, an unseen enemy uses `any_within` and a distance bisection even when that particular enemy is far from the entire neighborhood. The existing boolean broadphase only avoids the whole enemy pass when everybody is far away.

A bounded mask of **which enemies** may hit the current-plus-eight square could retain the existing exact station computation for retained enemies and omit provably zero contributions from the others. This is most promising when one nearby threat makes the boolean true while several other credible unseen enemies are far away. For five enemies it trades a complete, at-most-five-enemy broadphase for skipping up to nine repeated far-enemy queries. It can cost more when all enemies are nearby or visible; no savings are established yet.

Minimum semantic boundary:

- Build/use the mask only for this station neighborhood and this Safety/vision epoch. Keep each retained enemy's original order and **the existing built/unbuilt `threats_at` algorithm**. Do not replace its unbuilt nearest-possible-tile calculation with the built field result; these are different paths today.
- Use the existing `foe`/`threat_strike`, `gone` and credibility decisions. For a visible pending teleport, the origin must be `teleport_pending() && in_bounds(tp_dest) ? tp_dest : pos`, exactly as current `blow`/broadphase do (`safety.cpp:1908,1982`). Timing remains entirely in latest-main `threat_strike`. Unknown destinations retain current behavior; this does not establish an unknown-landing safety guarantee.
- For unseen enemies, exclusion requires no possible tile within `strike.reach + 1` of the neighborhood center, using the existing `possible` and positive-credibility test. This conservative Chebyshev bound excludes only enemies that cannot affect **any** of the nine stations; it must also hold for the built Threat field path. Never use last-seen position as a substitute for `possible`.
- Recompute after observe/reconstruction, move, hidden blocker and stale resume. Never carry a mask across a changed origin/vision/Safety lifetime. Preserve all original threat contributions and floating-point accumulation order for retained enemies; skipped enemies must contribute neither damage nor stun nor `hits` at any station.
- No generic API-wide threat filtering or different camp admission is necessary. Exact station records/guard bits and decisions, rather than only aggregate replay outcomes, are the correctness witness.

Smallest useful measurement **before authorizing an implementation**: an exact harness over existing db5b inputs that counts station rebuilds by actor/branch, `built_` mode, nearby-mask population, live/credible unseen population, and existing `threats_at`/`any_within` query counts. Record fuel deltas around the existing complete station build, separating cold and warm index/Reach cases. No new production SDK queries are needed to log already-computed results. If far credible unseen enemies are rare, reject this proposal rather than adding machinery.

## 2. Small, simpler opportunity: reuse the mate's already-computed heal-view mask

In Willow's `local_support`, a worthy ready mate can enter `targets` with `attack_viewers(world,mate->pos,4)` at `bot.cpp:4680`; the function unconditionally calls the identical `attack_viewers` again for `formation_view` at4683. A call-local copy of the first result, used only when that exact mate target was added, would eliminate the duplicate computation. If the mate is absent from targets, keep the existing formation call. Prism's path is unchanged.

The second call's far sight mask is already warm, so this is **not** a claimed eliminated shadowcast/SDK vision query. It still repeats the nine-row bush-window assembly and near-sight work (`safety.cpp:1194–1205`; `sight`1141–1190). This is an allocation-free, narrow common-subexpression reuse with likely modest savings. It may be worthwhile only if actual mate-target frequency is high; do not sell it as a rollover fix.

Proof obligations: same world, mate position, range4 and store behavior; no observe/action between the two computations; copy the `Reach::Window` value, not a pointer into mutable scratch storage. Keep target iteration, worth-healing tests, tie order, mate identity and all missing/invalid/channelled-mate exits unchanged. The intervening work only builds other sight masks and cannot change the already-returned value; `sight`'s terrain mask cache has no eviction. Measure actual duplicate frequency and whole-function cost before deciding that even this small patch is worthwhile.

## Minimum qualification if either is later implemented

1. Attribute current 100k rollovers/fuel to actor and phase on existing panels first; no assumption that team-level excess is Willow station cost.
2. Compare parent/child on identical existing harness inputs at100M with native action/round-hash equality. Check bit-for-bit nine-station risks, legal flags and guard boards for proposal1; target/view/selected station equality for proposal2. Include visible threats, both acted orders, unseen credible/zero-credible sets, known pending teleport near destination/far source and the reverse, not-ready teleport timing, and stale/hidden-blocker/moved refreshes.
3. Report per-station-build and total-turn instruction/fuel changes, median/p95/tail and maximum, split by built/unbuilt Safety, cold/warm caches and Willow/Prism. Count hostcalls removed/added rather than inferring from source. A mask can have a negative net cost in favorable cases yet lose overall.
4. Then compare real-budget native rollovers and errors on the same frozen panel, followed by the normal broad/heldout qualification only if savings are material. Existing fuel gates can change real-budget execution even when high-fuel behavior is identical; no new gate or speculative credit is allowed.

Recommendation: measure proposal1's favorable-case frequency first. Proposal2 is a safe-looking small cleanup if cheap to review, with deliberately limited expectations. No other material exact-behavior optimization was established by this bounded read. The earlier unused-quote optimization is not revisited.
