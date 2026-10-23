# Remembered-camp farm routing: independent source review

2026-10-24 UTC. **No source blocker found for the bounded build and source-known Band activation check.** The implementation matches the narrow policy nominated by `willow-band-hor-routing-mask-causal-review-20261024-v2.md`. This is not evidence of changed replay behavior, useful arrival, fuel cleanliness or competitive gain. Read the Cambridge Battlecode rules, causal review, complete three-file diff, caller/helper/cache context and both provenance REVIEW.md files. No engine, build, match, source edit or EXPERIMENTS edit.

Independently verified candidate aggregates:

- cb61eaa parent `369742e3f54259c675c0d4b508a02c0c4517eef6e1cb3ef6f42fa776194180ea`; `bots/variants/willow-astraeus-remembered-camp-route-work` candidate `2a475721c8985cfcbd189e683ffac90ac05cdbf06280289899d21d9be851204e`.
- Isolated old4db witness candidate `bots/variants/willow-hyperion4db-remembered-camp-route-work`: `0620e6589ba0c1ff908d94538c525b517ed5d8ee3a443e9fe26a9ccc5449a724`; frozen control is `bots/baselines/hyperion-4db-remembered-camp-route-control`.

Both candidates/controls match their complete before/after snapshots. cb61 patch SHA `596ef70d0639ed990a0bd25bfdc729d3c304b2c3e9a58ddf39b129ed71674af2`; old4db patch SHA `1ef4d7200a9a62d16e98e41514f615fb214f5f3af8eec33b2152d365a88bf771`. Their respective Pathing implementations are byte-identical before the patch and again afterward. Only bot.cpp/pathing.cpp/pathing.h change; no Gold arm is included. References below use the cb61 candidate's `src/`.

## Current visibility and the obstacle invariant

`Pathing::farm_occupied_into` (`pathing.cpp:371–382`) first reconstructs the original complete native occupancy board, then reads current native actor vision, complements it, intersects it with the existing believed-live camp mask and unions that result. Camp-only truth is exactly **N OR (B AND NOT V)**. The helper does not trust cached `blocked_` or `world.visible`.

- A live camp leaving vision remains blocked through B even though N no longer reports it.
- A currently visible empty tile clears the belief contribution immediately, including a same-turn kill while World still remembers life.
- Native occupied camps remain blocked even when belief says dead/cleared, including respawn.
- Partial visibility works member by member; a visible empty member opens without dropping unseen living siblings.
- An unseen camp cleared by someone else stays conservatively blocked until knowledge/visibility changes. No age expiry is invented.

The native occupancy/vision reads contain no intervening game action or observation update. Stale-turn checks bracket construction; a fuel rollover prevents the completed old-turn mask from being used. Vision includes own ward/revealed tiles through existing `vision_into` (`util.h:304`). The preexisting helper retains static walking terrain, ally/enemy occupancy, teleport reservations and bump records. Therefore “visible emptiness opens” applies to the added camp component; another legitimate unit/guard/bump can still block that tile.

## Scope, retries and cache behavior

Default `RoutePolicy::visible` keeps the original blocked-cache/native occupancy branch. Only selected farm walking sites opt into `farm`: spell-clear approach, pickup, cleared/attack/adjacent routes, walk-on's prior-target/centre/crow fallbacks, and walking after a dash route. Dash generation/execution, combat search, escape, global `occupied_into/blocked/try_move`, target selection, goal masks, caps and tie ordering are unchanged. Direct adjacent `step_onto_cleared` remains its existing native-confirmed action, not a routed fallback.

The policy propagates through all three hidden-blocker retry searches (`566–578`), Field live/wider searches and descent (`658–679`), crow fallback, and `make_way`'s substitute-step wall filtering (`581–622`). `make_way` reads the immediately preceding failed field, which already used the chosen policy; it does not silently launch a new visible-only search. Native refusal remains distinct from successful movement. A fresh retry keeps bumps and current visibility.

Farm walls enter `route` before through clearing, avoid/guard application and final self clearing (`446–469`). Existing precedence remains: through clears its tile before avoid/guard can reblock it, while self is freed last. Guard storage is not modified by the overlay. Greedy fallback candidate checks use the same farm wall helper, then their original avoid/guard and native-action checks.

The existing `kept_steps` cache receives the completed final wall board; neither a separate policy key nor unconditional clearing is necessary for correctness when those actual boards are compared. A change from farm to visible semantics can invalidate reuse through the changed-wall test. Failed searches still preserve the earlier kept field as before. This does not imply byte-identical later non-farm play: changed farm movement/cache history can naturally affect subsequent decisions.

`live_camps` and approach-field version/flips protocols are unchanged. A live farm wall can open a visibly killed tile immediately while an older approach field still labels a longer route until the ordinary belief update. The patch does not claim to rebuild that field on every native visibility change. This preserved distinction is a runtime control, not grounds to add a second broad cache rewrite now.

## Cost and build boundary

Each farm wall construction adds a native vision read and three board operations, plus fresh occupancy instead of a potentially cheap cached copy and stale checks. Two reusable overlay scratch boards and one fallback wall board allocate on first use, not per group or subsequent call. Existing `live_camps` initialization/update can still allocate/update its own storage. There is no new map-wide tile loop, extra route search, cap increase or fuel gate, but multiple farm route/fallback calls can each pay the added native/board work. Existing cost estimates do not separately prove that overhead fits default fuel; measure it.

The first source-known witness should use the pinned old4db control/candidate and exact Band side/rosters: retain selected source31/goals, keep Wolf100 `(13,33)` blocked at21, and show subsequent departure and useful work. Fewer reversals with waiting is not a pass. Follow with visible-kill/ward reveal/partial-member/respawn controls and hidden-blocker/make-way/guard/self/through controls. Distinguish the new policy's current visible-empty wall from a stale approach field that is still conservative.

Default-fuel activation, errors/rollovers, production, deaths and bags must be assessed before wider paired qualification. The old4db witness validates that lineage only; cb61 requires its own runtime evidence. Source review supports proceeding to the bounded build without another source change.
