# River audit: does running a state make its target strictly better? (2026-10-27)

The rule (the user): running a state must strictly improve its target. If every turn walks to the best target under one evaluation, and each step strictly raises that target's value, then the best value only ever rises while the world stands still. Then no state can step back and forth. Each break of the rule below is a way a cycle can happen.

## Method

[instrument.py](instrument.py) makes an audit copy of river with debug-only traces (refunded):
- the goals of each turn's movement call;
- farm's per-group scores on the turns its target changes;
- want_home's terms on turns we leave.

The batch was 40 ladder games, one side each, against astraeus at the default fuel (replays/aud3; all numbers below are from it). The three scripts here read it:
- [audit.py](audit.py): each state's moves, and every A→B→A cycle;
- [farm_switches.py](farm_switches.py): why farm's target changed;
- [retreat_swaps.py](retreat_swaps.py): why retreat undid an advance.

A cycle is a champion back on its tile two turns later, having moved both turns, counted at its first turn.

## The walks are fine; the targets are not

Judged by the static walking distance to that turn's own goal tiles, the moves come closer:

| state | moves | closer | no closer |
|---|---|---|---|
| farm | 54.1k | 95.7% | 1.3% (2.9% moved outside the pathfinder) |
| bank | 25.3k | 94.1% | 2.3% |
| capture | 5.6k | 91.5% | 7.3% |
| siege | 1.9k | 96.8% | 2.6% |

But after a move with goals, the next turn's goals often differ: farm 18.1%, bank 16.6%, chase 45.7% (a moving enemy, expected). Of 6,129 cycle starts:

| cycles | kind |
|---|---|
| 2,323 | farm: the goal tiles changed (a new target) |
| 896 | bank: the goal tiles changed |
| ~1,330 | a state swap with retreat (farm, bank, siege, capture, chase) |
| ~500 | farm swapping with chase, support or capture |
| ~470 | the same goals, one move no closer (260 of them capture's; not traced) |

## Farm

There were 10,211 target switches; 2,580 of them were stepped straight back from. Each break below cites its code.

1. **Fight turns use another rule.** After strike's search, farm scores nothing (`evaluated = struck && ... ? 0 : n_groups`, farm.htb:1163). It walks to the engaged group or our ownership claim instead (farm.htb:1419). So turns with a fight and turns without alternate between two targets. 2,066 switches start from a turn that didn't score the old target; 666 were stepped back from.

2. **Overrides after the comparison.**
   - The crew pick wins whenever its share beats the best (farm.htb:1413): 1,878 switches, 553 stepped back.
   - Help replaces the pick unconditionally (farm.htb:1415): 384, 100.

   Crew status hangs on `claims::theirs` (the strictly nearest ally; ties to nobody). An ally's single step can flip it, and so can ours: stepping up to an ally's group can make it ours, after which it's scored as a solo clear.

3. **Crew arrival maths.** A claimed group whose crew would finish it before we arrive is skipped (`health_left <= 0`): 1,012 switches, 152 stepped back. This one depends on time, not on our steps.

4. **The risky flag** (`damage > spare_health && !ally_engaged`, farm.htb:1386): 532 switches, 174 stepped back. Its partner terms count allies within `partner_radius` of *us*, not of the group (farm.htb:1069 and 1343). So one step can drop a partner and make the group risky. The recall line inside `spare_health` (farm.htb:857) depends on our tile too, but it caused only 8 switches.

5. **Value and walk measure different things.** The value counts steps to the group's centre (farm.htb:1246). The walk goes to its attack tiles, by a route that treats every unit on the map as a wall (pathing.htb:941). A blocked corridor then means a detour, and the detour reverses once the unit moves. In one traced game (00ambush), 25 of 211 cycles came from this.

6. **Passing hits step toward another group.** `plan_camp_attack` may move toward `aims.farm_group`, the engaged group fixed at turn start (farm.htb:887), before the pick is made. Vendetta at 00ambush rounds 228–239 alternated this way for 12 rounds under an awake group, losing 1500 → 540 HP. That was 20 of 211 cycles in the traced game.

7. **Chain or bank.** With a bag, farm gives the turn to bank when its best is no better than `from_altar_value` (farm.htb:1406). Both values depend on our tile: 760 switches, 264 stepped back.

The largest bucket, "another group beat the target while its value rose" (2,880 switches, 768 stepped back), isn't a break by itself. One evaluation can't send us back that way. Its step-backs trace to the new target having been scored differently on the previous tile: not scored (861), skipped by the crew maths (368), or skipped by the respawn wait (231). So they come back to breaks 1–3.

## Bank

- About a quarter of its goal-change cycles are farm's flips inside a chain capture (above).
- The rest alternate between altars: two different 8-tile sets, or one altar's tiles against all altars'. `covered()` (bank.htb:407) counts an altar as farther when an enemy *visible this turn* could strike it, and our steps change what we see.
- `may_chain` (bank.htb:612) tests whether an enemy could reach the tile we stand on now, so stepping toward the chain target can switch us to banking.

## Retreat swaps

There were 753 swaps where a state stepped forward and retreat stepped straight back. About 330 come from the pack zone, about 330 from the fight forecast losing once an enemy is seen, and about 60 from low health or camp traps.

For farm, bank, capture, chase and contest, 569 of the 598 forward moves passed the Advance check: from A, neither the pack zone nor the forecast said B would send us home. At B we see more, and enemies have moved. Back at A, what we saw at B no longer keeps B out, so we step in again.

siege, ender, spent and support never set an Advance (steps.htb:346): 155 swaps went unchecked, 127 of them siege's.

## Fixes, by cycles removed (proposed, none made)

1. **One rule for farm's target.** Make the walked target always the best under one evaluation:
   - crew and help scored as values in the same comparison, not overrides;
   - fight turns either score too (making it cheap enough) or don't walk to a farm target.
2. **Score a group the same whoever owns it.** Count the allies working on it whatever the ownership labels say. Then stepping close to an ally's group doesn't switch it from crew to solo.
3. **Position-independent risk terms.** A partner counts by its distance to the group, not to us.
4. **One distance for value and walk.** Score the walk to the attack tiles the walk targets. Follow that static field, with units blocking only next to us.
5. **Passing hits only along the walk to the pick**: run `plan_camp_attack` after the pick, and move only toward the pick.
6. **Remembered enemies for `covered`, `may_chain`, the pack zone and the fight forecast**, as the tracker holds them, not only the ones visible this turn. Then what we saw at B still keeps us out of B back at A.
7. **The Advance check for siege, ender, spent and support.**
