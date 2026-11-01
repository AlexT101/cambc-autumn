# astraeus fuel-guard audit (2026-10-31)

A logic-only read of `bots/astraeus/src` at 959b65e7: nothing was run. Every place where the fuel left (or a cost
measured from earlier fuel use) changes what the bot does, with the logic before and after it fires, the risks and
fixes. [FUEL-GATES.md](FUEL-GATES.md) is the removal plan and has the measured out-of-fuel (OOF) effect of removing
each gate. This file covers decision quality: what each fallback does wrong and how to make it fail safely.

"Fail open" means the fallback allows more than the full computation would. "Fail closed" means it allows less.

## Summary

| # | Gate (tag) | Where | Fails | Worst consequence | Fix first |
|---|---|---|---|---|---|
| 1 | step-guard-entry / -sim / -look | combat/guard.cc:391, 466, 505 (returns 493, 520, 532) | **open** | steps onto lethal or losing tiles; A-B-A loops | fall back to the cover or `lethal` rule, not to no guard |
| 2 | fight-cut | model/safety.cc:630, 681 | closed | a won fight reads as lost, so it retreats; A-B-A | remove (rare), or return unknown and don't memoise it |
| 3 | farm-partial-evaluation | economy/farm.cc:888, 1017, 1038 (tag 1172) | changes the choice | flips farm target; starves the guard of fuel | reserve the guard's cost; hysteresis |
| 4 | farm-kept-target | farm.cc:466 | changes the choice | rewrites claim and crew to last turn's group | keep the choice, walk a cached field |
| 5 | crow-flies-farm | farm.cc:473 | path | greedy steps into dead ends; undoes progress | use the cached `from_centre(g)` |
| 6 | farm-no-route | farm.cc:1220, 1256 | path | in range without sight; falls into 4 and 5 | remove (the search is bounded) |
| 7 | farm-no-attack-tiles, spell-clear-no-tiles, siege-no-tiles, **kite (untagged)** | farm.cc:93, 1231; siege.cc:205, 506; pathing.cc:374 | changes policy | siege steps back to staging, kite gives up, spell clear becomes tanking | cached or approximate attack tiles |
| 8 | prey-cut-short | combat/fight.cc:423 | closed | missed kills; chase/farm alternation | try last turn's prey first |
| 9 | siege-route-fuel | model/pathing.cc:854-880 | no move | stalls when contesting captures or intercepting tributes | fixed cap, static-field fallback |
| 10 | static-descend | pathing.cc:892 | path | stalls behind units, no make_way | remove |
| 11 | turn-order | model/turn_order.cc:447 | stale | an old turn's escape or kill priority applies | bound the offers; else plain priority |
| 12 | ward-no-bushes-fuel / -clusters | bot.cc:64, 71 | skip | bush ward delayed | drop the first check |
| 13 | comms-stale-vision | main.cc:274, comms.cc:187 | stale | respawns seen after moving go out a turn late | always observe |
| 14 | `late_floor` turn end (untagged) | main.cc:267-277 | skip | no comms send, no `cleared_by_us` | keep (crash guard) |
| 15 | estimators and measured selectors (untagged) | util.h:54, 520, 551; safety.cc:2441; farm.cc:279 | n/a | gates depend on earlier turns' costs | see the estimators section |

## Cross-cutting findings

**A. Inconsistent failure direction causes two-turn loops.** The step guard fails open and the fight sim fails closed,
so a single fuel-short turn can either step in (no guard) or step out (a fight read as lost). The next full-fuel turn
reverses it. Every gate that changes a decision, rather than only the path, can produce an A-B-A cycle. The general
fix is that a fuel-short turn should repeat the last committed decision (stored in memory) rather than switch to a
different, cheaper policy.

**B. Priority inversion: economy work spends the fuel that safety needs.** `guard_steps` (bot.cc:336) only defers the
guard. It is placed when the first step needs it, which is after farm's evaluation loop. That loop reserves fuel for
its own walk and route (`loop_reserve`, farm.cc:692) but not for the guard. So the farm loop, which degrades
gracefully, runs to its floor, and then the guard, which fails open, gets cut. This is the TODO's Marcella case (farm
turns ~85k; 443 of ~900 turns cut). Fix: when a guard is deferred and `GuardFoes::reaching != 0`, add its expected
price (`fight_cost_estimate() + act_reserve + step_guard_costliest()`) to `loop_reserve`. Alternatively, place the
guard before the farm loop on those turns. Both change an existing gate's threshold; neither adds a gate.

**C. The estimators carry history across turns.** `step_guard_costliest` (static), `costliest_unseen` (static),
`costliest_field` and `max_field_layers` (static, also grown by the turn-end queue's fills) set later gates'
thresholds. So "the queue never changes play" holds at 100M fuel but not at the real budget: a field the queue builds
raises `full_field_cost_estimate()`, so farm's loop breaks earlier on later turns. `step_guard_costliest` is also
sticky: it only decays when a placing completes or nothing reaches us, never when the entry gate fires. Once
`step-guard-entry` starts firing next to enemies it tends to keep firing.

**D. Missing hysteresis memories.** The fixes below reuse four small memories: a fled tile (TODO item 1), the last
prey target, a margin to keep the farm choice, and the last siege goals.

## Per gate

### 1. Step guard: step-guard-entry, -sim, -look (combat/guard.cc)

- **Fires when:**
  - Entry (:391): fuel < `fight_cost_estimate() + act_reserve` (20k) + `step_guard_costliest()`.
  - Sim (:466): fuel < `fight_cost_estimate() + 20k` before any fight that isn't memoised.
  - Look (:505): fuel < floor + 1000 × foes before each exact exposure.
- **Before:** the guard holds every tile within a step (or a ready dash) that is more exposed than ours and whose
  fight is lost, or where we fall when linked or `lethal`. Routes, descents and `try_move` refuse those tiles.
- **After:**
  - Entry, look, and a cut on the union fight (:493, :520) return `nullptr`: no guard, so every tile is open.
  - A cut in the final loop (:532) returns a partial guard. That loop is sorted fewest enemies first, so the
    unsettled tiles left open are the ones with the most enemies, i.e. the most dangerous.
- **Risks:**
  - Steps onto lethal or losing tiles, then `want_home` flees next turn. This is the Marcella two-round cycle.
  - Teleport-pending foes and the dash radius (2) widen the exposure, so a dasher can be sent two tiles into a fight.
  - Stickiness (C) makes the gate fire on whole stretches of turns near enemies.
- **Mitigations, cheapest first:**
  1. **Fail closed with what is already known** (your "tiles in enemy range" idea, made relative to our tile).
     `step_guard_cover` (guard.cc:351) is the cheap pass `route()` already uses. It compares Strike windows only and
     builds no Reach and runs no fights. It returns the tiles more exposed than ours. On an entry cut, return the cover
     instead of `nullptr`. Steps that are less or equally exposed (retreat, sideways) stay open, so this never traps us.
     On a look or sim cut, guard the tiles not yet settled (`exposed[i..m)`) by the FUEL-GATES rule "guarded iff
     `safety.lethal(q)`". `lethal` is a sum over threats once they are built, and they are built by then. Where only
     the bound is known, use "bound mask not within `here_mask`". Cost: about one cover pass. Risk: more timid on cut
     turns (won't press into fights it would win), and farm walks near enemies may stall. A stall is better than a
     lethal step, and it ends when fuel allows the full guard.
  2. **Fled-tile memory** (TODO item 1): when `want_home` leaves tile T, keep T guarded while the enemies seen then
     stay where they were. A few hundred fuel. This breaks the A-B-A loop whatever the fuel.
  3. **Fix the inversion** (B), so the guard is cut less often in the first place.
  4. **Remove the gate** (FUEL-GATES): a measured simulation-count limit with fallback 1. This needs cheaper sims. A
     cross-turn fight memo keyed on the full fighter state (positions, health, cooldowns) would make most farm-turn
     sims free, since enemies holding still give the same keys turn after turn.
  5. Make the estimator decay on entry cuts too, or remove it once 4 lands.

### 2. fight-cut (model/safety.cc)

- **Fires when:** in `simulate`, every 8 plies, fuel < `end_reserve` (10k). This applies to every `new_fight`,
  `chase_trade` and `stand`.
- **Before:** the simulated outcome. **After:** `lost = self_falls = true`, stored in the fight memo as known for the
  rest of the turn. In the step guard, `settle()` then spreads "lost" to every larger fight it covers.
- **Risks:** fails closed, so `want_home` retreats from a won fight, the guard blocks tiles, and chases are refused.
  The next full turn advances again, giving an A-B-A loop, the mirror of gate 1. It runs at the very end of the
  budget, so it hits the fight-heaviest turns.
- **Mitigations:** `simulate` is bounded (2 × `fight_horizon` plies), so its worst case is known. FUEL-GATES measured
  removal as level and the gate as rare: remove it. If something must stay, return `lost_known = falls_known = false`
  without memoising, so callers use their own fallback (`lethal(p)`) rather than a fabricated loss.

### 3. farm-partial-evaluation (economy/farm.cc)

- **Fires when:** before each group, fuel < max(`ample`, 15k + `loop_reserve`) (:888). `loop_reserve` is the approach
  plus the route to the current best. Also when a from-here static field (:1017) or a hop field (:1038, 2× a full
  field) is unaffordable.
- **Before:** every group is weighed and the best value wins. **After:** the best of the groups weighed so far. The
  order starts at last turn's choice and goes by nearness to it. If no group was weighed, it walks on to last turn's
  choice (:1185).
- **Risks:**
  - Alternation: a cut turn picks a near group and a full turn a far one, each walking a different way. Teammates
    see the claim flip, which churns their crew choices.
  - Bias: the `break`s at :1017 and :1038 mean groups with no cached steps (no centre field, no drafted steps, behind
    a hop) are never weighed on short turns.
  - It spends the fuel the guard needs (B).
- **Mitigations:**
  1. Reserve the deferred guard's cost in `loop_reserve` (B).
  2. Hysteresis: after a cut loop, keep `memory.farm_group` unless a weighed group beats it by a margin. Its value is
     known because it is weighed first.
  3. Keep the last complete evaluation's values, so a cut loop compares against stale but complete data, not a subset.
  4. Make the loop cheap (TODO 1). Build the first centre fields in the 200k first turn.

### 4. farm-kept-target (farm.cc:466)

- **Fires when:** in `walk_on(g)`, `prepare_approach(g)` refuses (fuel < 10k + the approach's cost, plus a centre field
  if missing) and last turn's group's approach is ready.
- **Before:** walk g's approach field. **After:** `memory.farm_group = memory.claim = previous`, `memory.crew = false`,
  and walk the previous group's field.
- **Risks:** this changes the decision, not just the path. The claim posted to teammates reverts, crew status is
  dropped even if we were crew, and next turn may pick g again, so the claim alternates. The previous group may have
  gone bad (enemy holding, taken by an ally). It also fires at 100M as a no-approach fallback.
- **Mitigation:** keep g and degrade only the path. Descend g's cached centre field (`pathing.from_centre(g)`: no
  search, usually built by the queue's `warm_centres`). Use the previous group's field only if nothing for g is cached,
  and even then without rewriting `claim` or `crew`.

### 5. crow-flies-farm (farm.cc:473)

- **Fires when:** `walk_on` has no approach for g, no ready previous, and the approach was skipped for fuel. The code
  is `skipped ? nullptr : pathing.centre_field(g)`. `centre_field` builds the field if it is missing, so a skipped
  approach also skips a centre field that is **already cached**.
- **Before:** descend a field. **After:** `step_closer`, a greedy Chebyshev step among the steppable neighbours.
- **Risks:** as you said: behind a concave wall or a pocket it walks into the dead end, or it alternates with full
  turns that take the real path around, undoing their progress. Live camps are avoided only through `zone`.
- **Mitigations:**
  1. A one-line fix: `skipped ? pathing.from_centre(g) : pathing.centre_field(g)`. It is free and exact, and after the
     warm-up every farmed group has a centre field, so crow flies becomes almost unreachable.
  2. If still nothing is cached, store last turn's tile and exclude it from `step_closer`. This breaks two-cycles,
     though it can stall in a pocket.
  3. The same `step_closer` fallback is at siege.cc:595 (kite, when `approach()` finds no way within `walk_cap`; not
     fuel). Prefer the centre field there too.

### 6. farm-no-route (farm.cc:1220, 1256)

- **Fires when:** fuel < `search_cost_estimate(best_steps + max_detour)` + 10k.
- **Before:** a live route to the sight-checked attack tiles, or to the camp tiles for a cleared group, with
  make_way and hidden-blocker retries. **After:** `walk_on(best)`, which descends the approach field. Its goals are
  range squares, not sight-checked. On a miss it chains into gates 4 and 5.
- **Risks:** stops in range without line of sight (bush or wall), so no attack; stalls behind units; and through
  `walk_on` it can switch target (4).
- **Mitigation:** the search is bounded by a small cap near the target. Remove the gate. At least fix 4, so this
  never changes the target.

### 7. Attack-tile gates: farm-no-attack-tiles, spell-clear-no-tiles, siege-no-tiles, kite stations

All four share `Pathing::prepare_member` (pathing.cc:370): it refuses if fuel < floor + 10k or bush-cluster growth
can't finish above that floor. Drafted attack tiles skip it, so these bite on undrafted groups and ranges.

- **farm-no-attack-tiles (farm.cc:1231):** walks `walk_on(best)` instead of to attack tiles. The risks are as 6.
- **spell-clear-no-tiles (farm.cc:93):** `spell_clear` returns false, so it uses the plain approach: basic attacks
  inside the monsters' reach. That is a fuel-dependent switch from spell clearing to tanking camp hits, and an A-B-A
  between the spell tile and the attack tile.
- **siege-no-tiles (siege.cc:205):** `tiles()` gives an empty board, so the fallback goal is the staging ring outside
  the group's reach (:234). An **engaged** attacker (melee, ranged or caster) steps back to staging on a cut turn and
  returns next turn, losing every other turn's attacks. Engaged sieges have many champions in sight, which are the
  turns most likely to be cut.
- **kite stations (siege.cc:506), untagged:** a failed `prepare_member` turns off ground and unit stations. `near`
  then becomes the squares at ability range (4) around attackers, minus their reach. That is empty for reach ≥ 4
  (elk, golem, monolith), so `kite` returns false and the turn falls through to farm. It is invisible to `oof.py`
  because it isn't tagged.
- **Mitigations:**
  1. Never fall back to "no tiles". Use the cached slots for the members that have them. For a missing member, use a
     conservative approximation: `shadow_cast` over the Chebyshev square with bush tiles dropped (a flat-price host
     call). Bush clusters are the costly part, and dropping bushes keeps the approximation a subset (every tile in it
     sees the member).
  2. Siege and kite: reuse last turn's goals for the same (group, range) when the tiles can't be built.
  3. Tag the kite fallback with `note_shortcut("kite-no-stations")`. A tag counts the fallback; it isn't a new gate.

### 8. prey-cut-short (combat/fight.cc:423)

- **Fires when:** before each candidate (8 at most, best value first), fuel < `fight_cost_estimate()` +
  `search_cost_estimate(2 × vision_radius)` + 10k.
- **Before:** chase the best candidate whose fight isn't lost. **After:** stop. If no candidate passed, there is no
  chase and the turn goes on to contest, siege or farm.
- **Risks:** fails closed (passive), so it's milder than gate 1. It misses kills, and chase and farm can alternate
  (a step toward the prey, then next turn back toward the farm group).
- **Mitigations:** store last turn's prey and evaluate it first while it's still a candidate. That costs one sim and
  makes the chase sticky. Then a measured count limit (FUEL-GATES) after cheaper sims and a cross-turn chase memo.

### 9. siege-route-fuel / `step_towards_funded` (model/pathing.cc:854-880)

- **Fires when:** fuel − floor < fixed + one chunk, so no search at all. Otherwise the cap is however many layers the
  fuel left pays for. Before each move it also checks fuel − floor < `last_reserve` (2k).
- **Before:** the shortest route, at any depth. **After:** either the same route (BFS within a cap is exact when it
  finds one) or **no move**. The choice of route doesn't depend on fuel; whether to move does.
- **Callers:** siege (capture walk, staging and attack tiles), kite (contesting a held capture, :475 and :481), and
  fight.cc:632, the walk to attack or stun a **tributing enemy**.
- **Risks:** stalls exactly where timing matters: an enemy hold completes, or a tribute channel finishes.
- **Mitigation:** the FUEL-GATES plan: a fixed cap of 2 × static steps + `max_detour` (uncapped at most one full
  field). On failure, descend a cached static field (`to_group` for camp tiles). For fight.cc:632 the goals lie within
  vision, so a 2 × `vision_radius` cap is enough.

### 10. static-descend (pathing.cc:892)

- **Fires when:** in `step_towards(Field)`, fuel < `search_cost_estimate(here + max_detour)` + 10k.
- **Before:** a live route within `max_detour` of the static distance, a wider retry, and make_way past allies.
  **After:** a greedy descent of the field only.
- **Risks:** stalls when every closer neighbour holds a unit. Two short-fuel allies in a corridor can deadlock
  because neither runs make_way. Low.
- **Mitigation:** the cost is bounded by the cap, so remove it (FUEL-GATES: +3 / +33 / +15% OOF, so pair it with B).

### 11. turn-order (model/turn_order.cc:447)

- **Fires when:** alive and fuel < 10k in `set_turn_order` (after `act`).
- **Before:** bids (kills, heals, channel end, escape) set next round's priority, else the plain priority.
  **After:** keep last turn's rank if one is valid, else the plain priority with no bids.
- **Risks:** a rank from an earlier turn's emergency (an escape or a kill bid) applies to a different situation next
  round. A missed escape bid lets enemies act between our champions before we move.
- **Mitigation:** bound the offers that cost (FUEL-GATES lists `offer_escape`'s `threats_at` at 9-14.5k,
  `offer_kills`, `offer_heal`, `may_escape`); most are Reach reads the turn's Safety has already built. Until then,
  fall back to the plain priority rather than the last rank, because a stale emergency rank is worse than none.

### 12. ward-no-bushes-fuel / -clusters (bot.cc:64, 71)

- **Fires when:** fuel < 15k at the turn-end bush ward, or cluster growth can't finish above 15k.
- **Before:** ward the best bush cluster. **After:** no bush ward. The cooldown is unspent, so it retries next turn.
- **Risks:** low. The ward is delayed, on exactly the busy turns when enemies may be hiding in bushes.
- **Mitigation:** `find_bush_clusters` is floor-bounded and resumable (work carries over, and the queue pre-grows
  clusters within `ward_range() + 1`), so the first `fuel_ok` adds nothing. Drop it, in FUEL-GATES' combined A/B.

### 13. comms-stale-vision (main.cc:274, comms.cc:187)

- **Fires when:** we moved and fuel < 10k before `comms::send`.
- **Before:** `observe()` after moving, so the posted respawns include the new tile's view. **After:** posts from the
  turn start's vision.
- **Risks:** low. A respawn seen only from the new tile reaches teammates a turn late.
- **Mitigation:** observe plus send costs at most ~6.3k, so always observe (FUEL-GATES: −7 to +26% OOF).

### 14. `late_floor` turn end (main.cc:267-277), untagged

- **Fires when:** fuel < 1.5k after `decide`. It skips `note_turn_end`, `comms::send` and the queue.
- **Risks:**
  - The turn's claim, bag and sightings aren't posted, so teammates read stale claims (duplicate farming) and a
    stale partner bag.
  - A missing `cleared_by_us` shifts `hold_start` (world.cc:2366) by a round, so our own capture's payout is
    misjudged.
- **Mitigation:** keep it (end_turn must not run out). If it fires often, send comms before `note_turn_end`, since
  the comms bits matter more. Tagging it would let `oof.py` count it.

## Estimators and measured selectors (untagged)

- `step_guard_costliest()` (util.h:54): the entry gate's margin, and `route()`'s choice of how to search
  (pathing.cc:539). That choice is documented as exact. It is sticky (C).
- `Safety::fight_cost_estimate` (safety.cc:2441) uses `costliest_fight_` (per Safety, so per turn and reset by
  `see_again`) and `query_cost_estimate` → `build_cost_estimate`, which uses `costliest_unseen()` (static, for the
  game).
- `full_field_cost_estimate` / `field_cost_estimate` (util.h:551-558): from `costliest_field()` and
  `max_field_layers()`, grown by any `make_field`, the queue's included.
- **`farm_dash_kind` (farm.cc:279):** `150 × n_groups < full_field_cost_estimate()` is frozen at the first call of
  each instance. The non-opening instance first runs on turn 2, after turn 1's queue fills have moved
  `costliest_field`. So how much the first queue built decides, for the whole game, whether a dasher's farm loop reads
  the draft's dash steps or a from-here field. Mitigation: decide from map size (`search_cost_estimate(W + H)`), and
  check that the two sources give the same steps. If they do, only the cost differs.

Once the gates they serve are gone, delete them (FUEL-GATES' clean-up). `route()`'s use of
`step_guard_costliest` can stay.

## Fixed caps: deterministic fallbacks, not fuel gates

These don't read fuel, so the same state always plays the same. Their cost can still use up fuel that the gates above
then lack.

- plan.cc:192 `max_exact_queries = 10`: tiles past it keep their Strike price, and ring tiles at `grid_r` go
  unchecked for `lethal` (excluded as alternatives, :2098). This is ~45k with four foes yet to act (TODO item 3).
- plan.cc:194 `max_nodes = 24`; `max_unseen` 24; `max_units` 14.
- guard.cc: the foe list fills up (`all_listed` false), so it computes `fight_key` per tile, which is exact but
  dearer. `settled` has 26 entries.
- fight.cc: 8 prey candidates; enemies past the eighth are ignored.
- pathing.cc: `walk_cap` doubling, the wider retry at 6 × `max_detour`, and siege.cc:595's crow-flies on an
  approach failure (see 5).

## Fuel reads that don't change play

`TurnEndQueue` (main.cc:124-226), `prepare_next_turn` (bot.cc:403), `Pathing::warm_up` / `warm_centres` /
`grow_centre`, `StaticMap::warm_up` / `warm_drafted_steps` / `warm_enemy_steps` / `grow_cluster`'s floor, the draft
bot, and debug output (`log_fight`, `dump_beliefs`, `FuelMeter`). They are exact at 100M (FUEL-GATES), but finding C
applies: at the real budget their fills move the estimators that other gates read.

## Suggested order

1. Free or strictly safer fixes, each its own A/B:
   - crow flies via `from_centre` (5);
   - the step guard failing closed with cover and `lethal` (1.1);
   - farm-kept-target keeping the choice (4);
   - remove fight-cut (2);
   - tag the kite fallback (7.3).
2. The inversion (B): reserve the deferred guard's cost in farm's loop.
3. Memories: fled tile (1.2), last prey (8), farm margin (3.2), last siege goals (7.2).
4. FUEL-GATES' removals once sims are cheaper (cross-turn fight memo), counting with `oof.py`.
