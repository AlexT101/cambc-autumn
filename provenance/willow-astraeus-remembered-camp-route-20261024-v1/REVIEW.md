# Farm-only remembered-camp routing on cb61eaa

Specification: `research/willow-band-hor-routing-mask-causal-review-20261024-v2.md`. Read the Cambridge Battlecode rules and inspected the exact Pathing/farm seams before editing. This is source-only implementation, awaiting independent review and source-known activation evidence.

Candidate: `bots/variants/willow-astraeus-remembered-camp-route-work/src`.
Untouched control: `bots/variants/willow-astraeus-cb61-work/src`.
Frozen baseline: `bots/baselines/astraeus-cb61eaa/src`.
Parent Git commit: `cb61eaa5276b527c0de85db9b3bcfa0fdadd4a50`.
Parent 29-file source aggregate: `369742e3f54259c675c0d4b508a02c0c4517eef6e1cb3ef6f42fa776194180ea`.
Candidate 29-file source aggregate: `2a475721c8985cfcbd189e683ffac90ac05cdbf06280289899d21d9be851204e`.
Recipe: `(cd <botdir> && shasum -a 256 src/* | shasum -a 256)`.
Full 29-file snapshots are `before-src` and `after-src`; relative SHA-256 manifests normalize filenames to `src/`. The complete diff is `source.patch`. Only bot.cpp, pathing.cpp and pathing.h change. This candidate contains no gold-terminal changes and no `.cambc`.

## Obstacle policy and current native vision

The explicit `Pathing::RoutePolicy::farm` opts selected farm walking into a conservative camp overlay. Default `RoutePolicy::visible` follows the existing native occupancy implementation. Farm wall construction calls existing `occupied_into(out)` afresh, reads current `vision_into`, and merges `live_camps() & ~native_vision` using reusable boards. In camp terms the invariant is:

`current native camp occupancy OR (believed-live member AND outside current native vision)`.

Fresh full occupancy is intentional even when global `blocked_` is cached: that cache could contain a camp killed by same-turn damage. The helper neither reads `world.visible` nor trusts that cache. No action or observation refresh occurs between native occupancy and vision reads; `world_.throw_if_stale()` brackets construction so a fuel rollover during those reads discards the old turn's result. Current vision includes the actor's owned ward vision and native revealed tiles. Existing ally/enemy occupancy, static walking walls, teleport reservations and bumps are still assembled by the original helper.

The farm overlay is applied before existing through-tile clearing, avoid/guard assembly, self-tile clearing, `kept_steps` validation and distance-field compute. Thus the existing cache receives the final policy walls; no policy key or unconditional cache reset is added. Existing through/self clearing retains its original precedence, including guards being reapplied after through clearing and self being freed last. Default policy keeps the previous cached-blocked/cold-occupancy branch. `occupied_into`, `blocked`, `try_move`, combat search, escape, dash paths/landings, guards, target selection, goal masks, caps and tie ordering are unchanged.

Policy is threaded through bitmap routes, their three hidden-blocker attempts, `make_way` and its substitute endpoint filtering, Field live searches/wider retries, descending-field endpoint filtering and crow-flies endpoint filtering. Farm opts in at attack/adjacent/cleared routes, `pick_up`, spell-clear walking, `walk_on` (including previous-choice/centre/crow fallbacks), and the walking follow-up to a dash route. Native dash generation/execution remains unchanged. Direct adjacent `step_onto_cleared` still checks every member natively dead before native `try_move`; it does not build a route or admit a remembered camp by this policy.

The existing `live_camps` version/flips protocol and approach fields are unchanged. World observations/member-health/state/comms transitions continue to determine their mask. A same-turn visible kill can open the live farm wall immediately without rewriting World; an old static approach field can still encode a longer path until its ordinary belief update. That limitation is separate from the new live wall's current-vision override and remains for runtime checks.

## Source controls and tile clearing

These are source-level truth-table and call-chain checks, not executed fixtures. Let N be current native camp occupancy, B be believed-live membership, and V be current native tile visibility. Additional static/unit/guard/avoid/bump blockers are held equal here.

| Control | N | B | V | Farm camp wall |
| --- | ---: | ---: | ---: | ---: |
| Remembered live camp leaves sight | 0 | 1 | 0 | 1 |
| Visible empty tile with stale live belief, including our same-turn kill | 0 | 1 | 1 | 0 |
| Camp cleared outside sight, not yet observed | 0 | 1 | 0 | 1 until evidence changes |
| That cleared camp is revealed | 0 | 1 | 1 | 0 immediately in live walls |
| Respawn/current occupied camp despite cleared/dead belief | 1 | 0 | 1 | 1 |
| Known dead/unoccupied member | 0 | 0 | 0 or 1 | 0 |

Partial member visibility is handled per tile: visible empty members open, unseen believed-live siblings remain blocked, and any native occupied sibling blocks. No all-or-nothing group visibility test or age expiry is introduced. Once World changes member/group liveness, the original `live_camps` cache rewrites those members and its original mask-change invalidation remains effective.

An ally changing tiles changes the native wall inputs without removing an unseen remembered camp. Hidden-blocker retry rebuilds both current native occupancy and current native vision; existing bumps remain. `make_way`'s yielded step and field/crow fallback candidates use the same farm wall helper, then retain their original avoid/guard tests. Non-farm callers omit the policy and retain the original visible-only wall semantics. No guard is materialized solely for diagnostics; no new logging was added.

## Cost and unresolved evidence

The overlay adds one bounded native vision read and three full-board host operations (complement, intersection, union) per farm wall construction, plus freshness checks. Fresh occupancy can cost more than the previous cached-blocked copy. Two new reusable scratch bitboards are initialized on the first farm overlay; a third is initialized on the first farm fallback wall read. They are not per-group or per-call allocations after initialization. The existing live-camp cache can initialize/update its existing vectors and member bits. There is no new global tile scan, path search, age threshold, map selector, new fuel gate, target ban, cap increase or forced camp fight.

The qualified Band interpretation predicts that remembered Wolf100/source62 at (13,33) stays a farm route obstacle at round21, matching rounds20/22. This source change alone does not certify the next step, departure from the pocket, arrival at useful work or competitive gain. Stale unseen live beliefs can retain obstacles already cleared by another actor, cause longer detours or yield waiting; current visibility only corrects those tiles once seen. Extra native/board work and longer searches can lose fuel. Existing search caps and native failures remain possible.

No build, engine, replay execution, runtime instrumentation, competitive test, canonical source edit, commit, push or merge occurred. Required next evidence remains the same-source old4db Band control/candidate activation with unchanged selected work/goals, useful subsequent progress, observation/partial visibility/respawn controls, retry/make_way/guard/self/through controls and normal-fuel accounting. Earlier traces are evidence for the diagnosis, not results for this candidate. Full paired evaluation and unused-suite confirmation remain subsequent gates.

The same exact source policy was mechanically ported to an isolated old4db witness candidate; see `provenance/willow-hyperion4db-remembered-camp-route-20261024-v1/REVIEW.md`. It supplies the appropriate source lineage for the qualified historical Band activation; cb61 requires its own runtime claims.
