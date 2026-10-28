# Audit: model/world.cc, model/world.h

## Changed

**Cleanup** (commit `e74bcc88`). Bench replays are byte-identical (8/8). Fuel over the bench is +12k in total, about 0.0005% (2211802776 -> 2211814735).
- `engine::capture_timer` now uses `engine::capturer`, so the capture-state read and decode exist once.
- Added `engine::buffs(h, code)`, a non-throwing buff reader. `read_stuns` uses it instead of its own copy of the raw call.
- The three `find_bush_clusters` loops are now one private `grow_clusters(left, floor)` (always_inline). `find_all_bush_clusters` no longer recomputes `~clustered_ & bushes` on every iteration; the result is the same set.
- `add_group_hop`: the double `if (h == hops.size())` is now nested, with a comment saying why it returns.
- `StaticMap::build` computes `plan_check` once.
- The `make_landing_dash_foot` FuelMeter was labelled `"dash_foot"`; it is now `"landing_dash_foot"`.
- Comments: `seen_channel`, `respawn_earliest`, `no_board()` (why `kept` exists), and the meaning of `fuel_floor` 0. Removed stray double blank lines.
- **Reverted for fuel:** I merged `make_foot`, `make_dash_foot` and `make_landing_dash_foot` into one `from_spawn` helper. It cost about 32 fuel on almost every turn (+0.06%), probably because it changed inlining around `foot()`. I also tried a shared `open_square` for `Altar::tribute_tiles` and `lock_tiles`; it did not help, so it was reverted too.

**Fixes** (commit `accb226e`). Bench replays are byte-identical, because none of these paths change a decision in these 4 games.
- `update_champion`, on a respawn and on an unseen recall arrival: `b.scale = 1` became `b.scale = b.dealt`. `scale` is `damage_scale * dealt`. At full health `damage_scale` is 1, but Skirmish and Collectors emblems are kept through death and recall. So enemies with those emblems were under-rated, through `hit_strength` and `hit_focus` in safety.cc, until they were seen again.
- On a respawn, `shield` and `shield_turns` are now cleared. Champions respawn without buffs.
- `update_camp`, out of view: when a hold pays out, `held_since = -1` is now cleared along with `holder`. Every other path keeps the rule that `held_since >= 0` only while there is a holder. Before, a group that went respawning, then alive, then cleared with no holder kept a stale `held_since`. `pays_too_late` and `capture.cc` read `held_since` without checking `holder`.

## Considered, not changed
- Rewriting the `central_tile` template as a plain vector function was fuel-neutral. I left it out of the final diff, since it only tidies code used once at start-up.
- Sharing `fixed_step` and `fixed_steps`' mirror decoding: a shared helper would read `index_code` before the early return for a missing mirror group. Left as is.
- `landing_dash_walls` marks every member of a harmful group, harmless ones included. This is correct: a dash landing that hits any member wakes the whole group.
- `update_altars` keeps stale lock beliefs for altars out of view. The SDK lists only visible locks, so nothing better is knowable.

## Suggestions
1. **Camp wake inferred from a health drop is not exact** (world.cc `update_camp` `read_members`, `now - health_round[i] < camp_sleep_time`). If the member was asleep at `health_round`, any drop since means it woke at or after that round. The phase after waking counts as occupied, so it is surely awake through `health_round + 2`: the exact test is `<=`. If the member was already awake, damage does not keep it awake (camps.sleep), so even a 1-round gap can end asleep, and "awake" is wrong. Branch on `member_asleep(i)` from before the read. This only matters when no striker's own state is readable, such as a member killed while the strikers are out of view. Severity low-medium, effort small.
2. **Unseen awake groups go "unknown" late** (`update_camps` and `update_camp`, `round - c.state_round > camp_sleep_time`). A group seen awake may already have had 1 unoccupied phase, so it can sleep 1 round after it was last seen. The current rule keeps "awake" for 3 rounds. This is a judgement call (avoiding a camp vs farming it), but it could be exact if we kept the round each member was last seen with a champion in its range. Low-medium.
3. **The respawn window assumes the previous full update was last round** (`update_champion`, `respawn_earliest = round - 1 + respawn_time`). After a turn lost to fuel, the death could be earlier. Use the previous `updated_round_`. Only the belief dump reads `respawn_earliest` and `respawn_latest`, so either use them (for example, to predict when an enemy returns) or drop them. Low.
4. **Simultaneous enemy tributes** (`update_scores`): with 2 or more candidates whose channel ended, no bag is emptied unless one unseen bag equals the whole delta. If the candidates' bags sum to the delta, empty them all. Low.
5. **An unseen enemy's shield never expires** (`read_shield` runs only while visible). Most readers check `visible`, but `combat_priority.h` adds `enemy.shield` directly. Either age it by `shield_turns` or zero it when the enemy leaves sight. Low.
6. **Fuel trap worth recording:** moving the `make_*foot` bodies into a shared helper cost about 32 fuel a turn for no visible reason (inlining around `foot()` and its callers). Small "pure" refactors near hot accessors need the bench.
7. **`CampGroup::strength` and `threat()` are whole-group sums and unions.** Callers that treat `strength` as "damage to us" overcount when only some members reach us. Worth checking in camp-safety callers (outside this file).
