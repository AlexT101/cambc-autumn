# Connected camp escape: narrow source design

2026-10-24; source-only proposal. This repairs an actual geometric assumption in frozen f475 and Khaos_v34; it does not establish that the Fracture replay executed the nominated branches. No implementation or runtime requested here.

## Scope and invariant

Share one lazy **walking escape result** between `camp_trapped` and `flee_camps`, and consult it for camp-driven dash endpoints. Keep ordinary farm quotes, economic prices, enemy combat policy, recall cadence, and healthy non-exposed turns unchanged. The result answers “how many legal walking steps, under this current observation, reach a tile outside the existing camp hazard model?” It is not proof against future hidden enemies, ally movement, camp wakes, or changing aggro.

The current source's `camp_exit_rounds` (f475 bot.cpp:2823; Khaos_v34:2827) searches geometric rings; `flee_camps` at303 uses the same proximity idea through `any_within(exits,...)`. Holes and overlapping camp ranges invalidate both the claimed walking distance and the `max_camp_reach+1` upper bound. The high-health early return based on that upper bound must not survive unconditionally.

## Minimal computation

1. Preserve the existing zero camp-damage return, siege exception, already-triggered low-health/pack retreat short circuits, and the lower-bound test that already compels retreat at a one-step exit cost. No field is needed merely to conclude retreat is necessary; build only when choosing its route.
2. Cheap normal case: find a directly verified walking sequence to a safe tile, testing every intermediate tile on the **walking** blocker board. Eight compass rays up to the former small radius are a bounded useful first attempt, not a completeness test. A found path gives an upper bound D: if current health exceeds the existing `dps*(1.5*D+1)` expression, admission can keep working without a native field. If D also equals the geometric lower bound, it is the exact connected distance and can settle either side of that comparison. Otherwise a failed health comparison or failed ray must fall through to the exact query, not declare “trapped” or “unreachable.” Keep the selected path as a cheap retreat option where appropriate.
3. Hard case: use the existing native reverse walking-search primitive, `distance_field::compute_to_with_expansion_count`, from all camp-safe goals to the current tile. `Pathing::route` at pathing.cpp:448–478 already does this and retains exact labels below the reached origin layer. This is preferable to building an uncapped whole-map `Field` on every exposed turn. A small internal read-only route-result seam can return distance plus its known descending neighbors; avoid a second independent search in `flee_camps`. No new fuel-dependent admission gate or silent return to geometric distance.
4. Search walls are the actual walking graph: terrain `map.blocked_for_us`, current visible/live camp tiles, current observed units, teleport reservations and bumped tiles, with self freed. `Pathing::blocked/occupied_into` (pathing.cpp:348–369) supplies this; `Pathing::static_walls` and `foot` do **not**, since they deliberately remove crossable holes/altars for dashers (31–39). Include any currently effective movement guard consistently with the caller. Diagonal walking checks only the destination tile, matching the SDK field and rules18; do not impose a new corner-cut rule.
5. Goals are walkable, currently unoccupied tiles outside the **same existing Safety camp area** used by retreat, rather than raw all-monster ranges or an invented omniscient sleep model. `Safety::camp_area` derives from `awake_members`; members already reflect known sleep, possible wakes, allied aggro and damage modifiers (safety.cpp:1642–1738,2111). This keeps the repair about connected terrain. Verify consistency with `camp_damage<=0` rather than introducing a second notion of “safe.” No unseen camp is declared dead merely because its tile is absent from a native visibility mask.

Do not use the capped `make_field(...,max_layers)` wrapper as a distance answer: util.h:443 discards a globally incomplete field even when the queried origin has a valid label. The route primitive retains the reached distance. A complete finite map search can distinguish unreachable; a truncated local search cannot. If an optional bounded local implementation is preferred, it must explicitly return “unknown beyond bound,” then use the native route query; it must not map truncation to a free/short exit. One native search on difficult topology is the simpler first implementation.

## Retreat and dash coherence

The connected result replaces geometric progress in `flee_camps`; its current immediate `damage_bound` and enemy-aware constraints still matter. Use connected remaining distance to break otherwise safe progress ties and avoid repeatedly selecting the lowest-damage dead-end tile. If no funded route is presently known, retain emergency escape behavior but report that outcome distinctly; do not turn an unknown route into a promise of survival or a compulsory stay.

For a camp-driven `dash_away`, score the **final endpoint of this activation**, including an available ordinary walk, not the dash landing in isolation. The legal dash graph is still `dash_landings_from` (pathing.cpp:674); the subsequent walk must use the walking graph. At most the existing bounded dash landing set and eight walking neighbors are relevant. A shortest-route reverse search that reaches the starting tile already labels all closer tiles, so useful connected-progress endpoints can often be compared without a second field. If a candidate needs an unlabelled distance, its distance is unknown, not unreachable; either retain the ordinary connected walking escape or resolve that particular need. Do not reuse an imaginary future dash every walking step.

After a successful dash, the ordinary movement must honor that selected escape continuation or re-evaluate fresh blockers; it must not independently undo the dash's camp-exposure gain via a generic home-field fallback. Conversely, camp escape must not override a necessary escape from a visible enemy. If an intervening action changes camps, readiness, or observed threats, invalidate the corresponding result before relying on it. Action legality/freshness remains with the existing `try_move`/dash APIs.

The current `dps*(1.5*D+1)` health expression remains a heuristic: variable damage along a connected path and future aggro can exceed current-tile DPS. This narrow repair makes D real; it does not convert that expression into a survival certificate. Recording a path's existing damage estimates would be a later measured extension only if needed, not a prerequisite to testing the connectivity correction.

## Cache, transient occupancy and cost

Use a single lazy scratch result per champion observation/decision, not per group. Reuse between health admission, flee selection, and dash continuation only while goals/hazards, walking walls, and relevant guard remain unchanged. Existing `Pathing::kept_steps` (pathing.cpp:495–524) already checks goal/wall changes and proves some cached labels reusable; do not assume its home-route singleton stays valid after another route query overwrites it. A dedicated one-slot escape result or scoped copy/ownership is sufficient.

Own movement changes the query origin, not inherently every distance label, but can reveal blockers or change Safety observations. Reuse only finite completed labels with unchanged inputs; otherwise replan. Other champions/reservations are temporary current blockers, never permanent camp topology. A hidden blocker refusal invalidates/replans through the existing bump handling; there is no assumption that a failed move spent the walk. A later freed ally tile can reopen a route. No persistent “unreachable group” label is warranted.

The fast ray checks themselves have nonzero board-access cost; native queries have setup and layer costs documented in util.h:414–419. This proposal therefore makes no fuel improvement claim. Cost remains outside ordinary per-group farm enumeration and is paid only while exposed, with the cheap verified-path case and within-decision reuse first. Avoid the Starvation failure mode of a new cold field inside every candidate price. Preserve measured behavior/cost separately when the isolated prototype is eventually tested.

## Small meaningful checks, after the Fracture own-view

- Open camp area: connected distance equals the former geometric answer; no native fallback when a cheap path settles the decision.
- Hole-separated safe tile: the near safe coordinate is not a short walking escape; the query finds the connected detour and retreat does not oscillate into a blind pocket solely to reduce instantaneous damage.
- Overlapping camp ranges: no `maxReach+1` upper-bound assumption; the union-safe exit can be farther away.
- Temporary blocking ally / newly revealed blocker: current route changes, then recovers when the tile frees; no stale permanent rejection.
- Ready dash plus remaining walk: compare legal terminal endpoints, never price holes as ordinary walking or undo the selected dash escape accidentally.

The authorized Fracture Vesper6 r472–480 export remains the first evidence check. A source-known reproduction/branch witness is still needed before claiming this repair addresses that match.
