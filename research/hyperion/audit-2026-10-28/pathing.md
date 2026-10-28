# Audit: pathing (`bots/astraeus/src/model/pathing.cc`, `pathing.h`)

## Changed

Commit `astraeus audit (pathing): cleanup`. Bench (4 maps, test drafts, 100M fuel): **8/8 replays
byte-identical**, total fuel +0.00% (2,211,802,776 -> 2,211,863,952; mean 50161 -> 50162).

- `route()` lost its `through` parameter: every caller passed `{-1, -1}`, so the tile-freeing branch was dead.
- `steppable(p, walls, avoid)`: the one "free neighbour" test (in bounds, off walls, avoid and guard)
  that `closer_neighbours`, `make_way` and `step_closer` each spelled out. `always_inline`: a
  non-inlined version cost +0.04% fuel.
- `grow_centre(slot, group)`: one capped try at a centre field, doubling the cap on failure, shared by
  `make_centre` and `warm_centres` (which repeated it with fuel checks).
- Comments: dropped a map-name reference (walk_cap), a cross-file experiment remark ("dash_across saw
  no gain and stayed") and an obvious one. Reworded draw_all_camps, centre_to_spawn, and kept_steps'
  invariant ("removing/adding a tile" was ambiguous about walls vs walkable). Reworded the danger-region
  note: it claimed every neighbour is in danger, which is false at the edge. The real reason is that
  walling the danger we stand in leaves no way out. It also now says `outside` is the fill's wall board.
  Reworded the step_towards_funded budget note and gave step_towards_funded a header comment.

## Considered, not changed

- `step_towards_funded`'s repeated `cambc::round_number() != round` checks: route() already throws
  StaleTurn on a stale round, so most are redundant. They return false rather than throw, though, and
  changing that changes the out-of-fuel resume path, which the bench doesn't exercise.
- Merging the uncapped branch of `warm_centres` into `make_centre`: their fuel checks differ
  (`fuel_floor` vs `bounded_floor`), so a merged helper needs two floors and reads worse.
- `approach_steps` falling to `walk_cap()` when a made centre field doesn't reach us (see S5):
  behaviour change with no clear win, left as a suggestion.

## Suggestions

S1. **make_way backs off from allies that will never move** (pathing.cc:662-700). Medium severity, small effort.
If our only way is through an adjacent ally and we carry fewer gems (or the same number and a lower
champion_type), we step to the free neighbour farthest from that ally. Nothing checks that the ally is
trying to pass us. Some allies never move: one channelling (tribute at an altar, recall), one holding a
capture tile, one parked in a corridor. Against them we back off, replan next turn, walk back and back
off again. The ally is adjacent and so visible, and its state is readable: when it is channelling or
cannot move, or still stands where it stood last turn, don't back off and treat its tile as a wall.
Also, only adjacent allies are considered. With an ally two tiles down a 1-wide corridor the route
ends exhausted and make_way does nothing.

S2. **Unguarded wide re-search in step_towards(Field)** (pathing.cc:752). Medium severity (fuel), trivial effort.
After a failed capped search (`here + 16`), it may run a second search capped at `here + 96`, with no
fuel check at all. On a 100x100 map that costs about 4000 + 169 x (here + 116) fuel, e.g. ~45k at
here=150, on top of the first search. Both searches matter for correctness, so bound the work rather
than gating it. Either reuse the first search's result (route_exhausted_ already short-circuits a dry
search), or make the first search the wide one when the kept route is unusable, so only one search runs.

S3. **The static-descend fuel gate fires before the kept route is consulted** (pathing.cc:745). Low-medium, small effort.
`step_towards(Field)` skips step_towards when `search_cost_estimate(here + 16) + end_reserve` isn't
available. But route() usually reuses `kept_route_` and runs no search at all (kept_steps). Move the
check into route(), just before `compute_to_with_expansion_count`. The gate would then trip only when a
search has to run, and the descend fallback stays for that case. This narrows an existing gate rather
than adding one.

S4. **Teleport targets skip dead members of live groups** (pathing.cc:820). Low, needs a probe.
`teleport_targets` re-admits camp tiles only for groups that are not `alive`. A member killed in a
group with other members still alive leaves an empty tile. The rules say "not a live camp", and also
"A dead camp's tile (its group cleared or respawning) is a valid target", which reads as group-level
but is ambiguous. `sdk_has_camp` already tells a seen empty tile apart. If a probe shows such tiles are
legal targets, drop the group-state test for seen tiles.

S5. **approach_steps treats an unreachable centre field as walk_cap** (pathing.cc:184). Low, small effort.
A centre field is stored only when complete (a capped field is returned only if whole). So `at(me) ==
unreachable` means no static walk leads from us to the centre. For range 0 (capture), every camp tile
connects cardinally to the centre over tiles walkable on static terrain. The approach search must
therefore fail, and we can return null without running a walk_cap-layer search. For range > 0 (ranged
attacks across holes) the search can still succeed, so the shortcut is exact only for range 0.

S6. **prepare_approach underbudgets for unfarmed groups** (pathing.cc:209). Low.
The added cost covers the centre field. For a group that is not farmed (a Monolith or no reward),
`approach_steps(.., true)` may build `from_ally_spawn()` instead, a full field, and its cost is not
counted.

S7. **Attack tiles exclude other cleared groups' camp tiles** (pathing.cc:328). Low.
`attack_tiles` intersects with `standable`, which drops every camp tile on the map and re-adds only this
group's dead members. A tile of a neighbouring cleared or respawning group is a legal place to stand and
attack from. Excluding live_camps() (camps believed alive) instead of camp_tiles would be exact. It
costs work on each call, so cache it keyed by live_flips().

S8. **Attack tiles ignore our ward** (pathing.cc:301). Low, design.
`member_attack_tiles` requires sight from the attacker's own tile. The rules let a ward's vision count
for attacks, so if our ward sees the member, every open tile within range is an attack tile. This
matters most for camps in bushes. It doesn't fit the cache. Instead, each turn the ward sees the member,
add `square(member, range) & open`.

S9. **Routes don't treat believed-alive unseen camps as walls** (pathing.cc:426). Low.
`occupied_into` uses `camps_into`, which holds only visible camps. A camp on a bush tile stays unseen
until we enter its cluster, so a route through it bumps: one wasted try and a fresh search each round.
OR-ing `live_camps() & ~vision` into the walls would be exact under our beliefs. It is cheap (two board
ops) but changes routes.

S10. **Inside danger the whole connected danger region is freed** (pathing.cc:512). Design question.
While we stand in danger the route ignores danger entirely, so it may walk deeper in towards the goal.
Alternatives: route to the nearest safe tile first when the path to the goal stays in danger, or free
only the tiles within one step of the region's edge. A judgement call, not a bug.

S11. **step_closer's aim is redundant at its callers** (farm.cc:476, siege.cc:572). Trivial.
Both pass the target as the aim. The aim only breaks ties, on Manhattan distance to the same target,
so it does no harm.
