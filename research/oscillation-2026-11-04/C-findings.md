# Family C: target switches and goal flip-flops without a retreat: findings (phase 1)

Groups: C1 farm ping-pong with no reason (4,194 episodes, 40.6k turns), C2 bank ping-pong/wander (7,968, 136.9k), C3
claim flip (66,838 episodes), C4 prey/chase flip (4,122, 57.2k). Line numbers are `bots/astraeus/src` unless stated.
Replays are under `replays/`; each example gives its batch directory.

## Method

- `bots/variants/astraeus-trace-C` is the trace bot plus `debug_block` prints:
  - `SR`/`SRP`: each `step_route` call. It prints the call site, the route length, the first-step options, a 5x5 wall
    mask (goal, avoid, guard, blocked), and the kept-route path.
  - `WD`: a 25x25 wall dump for chosen rounds.
  - `MW`: `make_way`. `DS`: `descend_with`. `TM`: `try_move`. `SS`: `step_safely`.
  - `CB`/`CBF`/`BG`/`TH`/`FBAG`: `carry_bag`, `bank_gems`, `take_hop` and chain-farm.
  - `PY`/`PC`/`PF`/`PP`: prey candidates. `PC` gives each `preyable` sub-test: distance, `near_enemy_spawn`,
    `own_ground`, `pair_gems`, `intercept_steps`, `pack_covers`, held. `PF` gives the fight verdict and `late`.
  - `FV`/`FJ`/`FG`/`FX`: farm. These are the final pick, the join candidates, each priced group's value terms, and
    which `continue` dropped a group (by source line).
- Reruns use fastrunner and swap the trace seat for the variant. A window counts only if the rerun's D lines match the
  original up to the window's end. The ~8-fuel debug cost moves fuel-gated turns, so about half of the reruns diverge
  earlier. Valid windows: C1 28/40, C2 27/56, C4 39/80, C3 30/60 plus 2 targeted.
- Ground truth for enemy, camp and ally positions comes from `extract.mjs`.
- Prevalence figures scale sample fractions up to the group's turns, so they are rough (about ±10 points).
  Whole-population statistics over the D lines of all 7,688 trace games are marked "(all games)".

## Sub-issues, by turns wasted

### 1. Farm target flips through groups that vanish from pricing (C3; ≈ 60k returns, ≈ 100k turns in stints ≤ 3)

**Examples**
- `batch-20261104-021721-ab-osc-trace-v68-gen/100-gen-classic-600100016-21`, team B, h5 Prism, r438-441. The choices
  are g0 (0.467), then g14 (0.938), then g0 (0.502).
  - r438: g14 is dropped by `health_left <= 0`, the claimed-group test (farm.cc:1601, variant 1606): the allies'
    crew finishes it before we would arrive.
  - r439: it is priced solo, 17 worth, trip 10, clear 2.
  - r440: dropped by `idle > params::max_wait` (farm.cc:1531), because it is now respawning.
- `batch-20261104-021547-ab-osc-trace-v67-fresh-gen-s1/240-gen-huge-shared-600205203-21`, team B, h4 Cassi,
  r138-141. The choices are g3 (0.86), then g7 (1.99), then g3 (0.75).
  - Enemy Vendetta (id0) stands on g7's centre (16,40), capturing it. Its gems are 15 cleared plus 90 gold.
  - r138: g7 is dropped by the `rated_below` prune (farm.cc:~1398).
  - r139: g7 is cleared and not `ally_holding` (the holder is an enemy). It prices at clear 0 for 1.99, and the
    route to it fails (`r-`).
  - r140: the capture has landed. g7 is respawning and dropped by `idle > max_wait`.
- `batch-20261104-021838-ab-osc-trace-v61-fresh-gen-s1/006-gen-altar-poor-600201000-21`, team B, h3 Cassi, r393-397,
  S→J→S.
  - We join g15 (2.67 vs 2.11 alone) while its crew needs 1.1 rounds and our trip is 4.
  - Two turns later it is not priced (`shared -1`), then 0.25 with 0.1 rounds left: the crew finished first.

**Mechanism.** The only hysteresis is `stickiness = 1.2` (farm.cc:9). It is applied at farm.cc:1432 as a weight on the
current `farm_group`'s worth, plus `crew_hold` for a claimed join (farm.cc:976), which applies only when `op`. It
protects the old target against a slightly better new one. It does nothing when a candidate is priced on one turn
and skipped on the next, which is what happens here. The skip tests have no memory:
- `max_wait` (farm.cc:1531): a group respawns once someone captures it.
- The claimed-crew `health_left` test (farm.cc:~1601).
- The `rated_below` prune (farm.cc:~1398) and the 1606-style `continue`s.

So a group that is about to be captured by someone else gets one turn as the best target, which is worth a lot
because it is already cleared, and then it disappears. The champion steps toward it and back. With 30-round windows
(all games), the outcomes of A→B→A returns are:
- 142,640 A→B→A returns in F/B.
- 46k of them did work on B: a camp hit on B, or a capture or hold during the stint. That is legitimate.
- 96k did no work on B. Their B stints last 1 turn 35.5k times, 2 turns 15.6k, 3 turns 10.0k, 4-5 turns 12k, and 6 or
  more 23k.
- Only 4.6k returns were near-ties (the B group was the runner-up within 20%), so this is not mainly a hysteresis-margin
  problem.
- By mode, the no-work returns split into J>S 21.3k, S>J 20.0k, S>S 15.6k, J>J 12.7k, S>H 4.4k, H>S 3.3k and S/C 4.8k.

**Confidence.** Confirmed by trace (FX/FG) in 2 S>S reruns; the 006 J-flip comes from FJ/FV. That the 1-3 turn
stints mostly come from this mechanism is likely: in every S>S/J>S window I read, B had been cleared or claimed by
someone else.

**Fix directions**
- Price a cleared-but-held group as taken: an enemy standing on a cleared group's centre is capturing it. Treat it
  like `ally_holding`, or contest it explicitly via `contest_capture`.
- Have the join test require `trip < remaining crew rounds`. Today the join bound uses `max(sqrt(trip*(horizon+trip)),
  1-trip)` (farm.cc:~1596), which lets a 4-step trip join a 1-round remainder.
- Keep a short memory of groups dropped by `max_wait` or `health_left` (an "about to go" flag), so a single turn's
  re-pricing does not switch.

**Risks.** Real contests of enemy captures, which are valuable kills, could be skipped; route them through the fight
code instead. Late joins sometimes still help clear a high-HP group.

### 2. Route / descend alternation and vision-dependent walls (C1 ≈ 50%, ≈ 19k turns; some of C2 wander)

**Examples**
- `batch-20261104-021505-ab-osc-trace-v69-fresh-gen-s1/155-gen-dash-lattice-600207615-12` (also v66), team A, h0
  Vendetta, r779-1060.
  - The static dash field descends via a crossing. The live route, with travel dash off because an enemy is within 10,
    has no way through.
  - `walk_down` (pathing.cc:1605-1650) alternates between descending on the field and the wide route, and each undoes
    the other.
- `batch-20261104-021547-ab-osc-trace-v67-fresh-gen-s1/251-gen-labyrinth-600203801-12`, team A, h1, r156-157. Wall
  dump, 1-wide corridors:
  - At (63,93) a unit 'u' stands in the corridor at (62,88). The route goes round the east loop: 14 steps, first step
    (64,94).
  - From (64,94) that tile is unseen (','), so it is not a wall. The route is 6 steps back via (63,93).
  - The two tiles alternate.
- `batch-20261104-021505-ab-osc-trace-v69-fresh-gen-s1/444-gen-tunnels-600204300-21`, team B, h8, r417-418: the same
  inconsistent route lengths. Its dump window started after a recall, so it is not wall-dumped.
- Seen in the sample but not confirmed: 350-topo-backdoor, 164/165 dash-lattice, 112-close-spawns, 264-leaky,
  443-tunnels.

**Mechanism.** The route BFS walls are `occupied_into` (pathing.cc:604): allies, *visible* enemies and units, camps,
bumped tiles, plus avoid and guards. They depend on what this tile sees, and so does `travel_dash` (pathing.cc:1121,
`enemy_within(.., travel_dash_clearance)`). The fallback chain is descend on the static field, then `step_field`,
then the wide route. It mixes a static distance with a live one. When the two disagree about which side is shorter,
each step reverses the last.

**Confidence.** Confirmed by trace and wall dump for the labyrinth and dash-lattice cases; likely for the remaining
C1 descend/route mixes.

**Fix directions**
- Remember units seen in a corridor for a few rounds as soft walls; the kept route (`kept_routes_`, pathing.cc:1023)
  could also keep its blocker.
- When the route fails and we descend, mark the descend and don't reverse it with a wide route on the next turn
  unless the walls changed.
- Commit to a detour for N turns.

**Risks.** Stale walls cause longer detours. Remembered blockers that have moved cost steps.

### 3. Prey preyable flips at the enemy's own-ground or spawn line (C4 ≈ 35%, ≈ 20k turns; C2 BC part)

**Examples**
- `batch-20261104-021838-ab-osc-trace-v61-fresh-gen-s1/101-gen-chambers-600203619-12`, team A, h1 Vendetta, r579-583.
  Prey e8 (492/1000 hp) steps (6,26)/(6,27), where `own 1` and it is preyable, then (6,28), where `own 0` and it is
  not. Our branch goes C, C, F, C.
- `batch-20261104-021759-ab-osc-trace-v66-gen/271-gen-hedges-600102914-12`, team A, h0 Vendetta, r547-550. e5 at full
  hp alternates (24,25), `own 1`, and (25,24), `own 0`. Our branch goes C, F, C, F, and we step back and forth with
  it.
- `batch-20261104-021623-ab-osc-trace-v65-fresh-gen-s1/304-gen-random-600201402-21`, team B, h4 Vesper Vale,
  r432-435. e2 (700/700) at d 8 toggles `near_enemy_spawn` (fight.cc:494) as it steps (13,7)↔(12,6). Our branch goes
  C, F, C, F.
- Also seen: 350-monolith-only h8 Issac, 481-mut-cuts h2 Issac, 181-dungeon h5 HoR, 013-archipelago, 285-huge.
- Over all samples, this is the largest single reason a chase ends or switches: 30 of ~100 C-exits, plus 4 at the
  spawn line.

**Mechanism.** `preyable` (fight.cc:493-508) returns false for a healthy enemy with no bag out of range on its own
side: `!own_ground(world, e.pos) && e.health >= hurt_health_fraction*max && held == 0 && (pair_gems == 0 ||
intercept_steps == unreachable)`, at fight.cc:504. It also returns false on `near_enemy_spawn` (fight.cc:494). Both
are tested fresh each turn on the enemy's current tile. An enemy walking or kiting along the line flips our branch
every step. `pressed` (fight.cc:514-525) keeps the engagement only when we struck or chased last turn *and* it is
still preyable afterwards (the `PP pressed` lines are followed by `preyable 0`).

**Confidence.** Confirmed by trace (PC sub-tests) in 3 maps.

**Fix directions**
- Hysteresis on the line: a prey chased last turn stays preyable while it is within 1-2 tiles of our side or of the
  spawn edge, or while it is not moving away.
- Alternatively, when it crosses, give up for K turns and don't re-chase, to avoid the F/C cycle either way.

**Risks.** The rule protects against being drawn into enemy ground or spawn (ambushes, respawning enemies). A margin
has to stay small; A/B it.

### 4. Guard horizon: re-centred guards walling the goal (C1 ≈ 15%, but the longest episodes: ≈ 8-10k turns)

**Examples**
- `batch-20261104-021623-ab-osc-trace-v65-ladder/121-02stalactites-12`, team A, h4 Willow, r298-1829, 1,532 turns.
  Willow's stations guard covers the 3 tiles toward group 7. The route is 4 steps for a goal 3 away, and it
  alternates.
- `batch-20261104-021838-ab-osc-trace-v61-ladder/072-00vault-21`, team B, h8 Heart of Ruin, r1647-1796. We descend
  into (12,21). The guard `###` is to the south, and the 12-step kept route leads back to (13,21).
- Also seen: 310-gen-round, 104-gen-classic, 006-altar-poor h5, 330-mega-groups, 150-03reef.

**Mechanism.** `guard_steps` (combat/guard.cc:600) covers radius 1, or the dash range when a dash is ready.
Willow's stations guard and `guard_work` (guard.cc:753) are re-centred on our tile every turn, and `route_around`
ORs them into the walls. The guarded tiles move with us: one step changes which tiles toward the goal are walled, so
the BFS's best first step reverses.

**Confidence.** Confirmed by trace (SR masks).

**Fix directions**
- Make guard tiles a cost rather than a wall for goal tiles.
- Or exclude the goal-adjacent ring.
- Or keep the guard centred on the turn-start tile for a few turns while working the same goal.

**Risks.** The guard is what keeps champions out of camp or enemy reach. Softening it near goals may take hits it now
avoids; A/B against camp damage taken.

### 5. may_chain / chain-farm flips while carrying (C2 ≈ 25-30%, ≈ 35k turns, mostly C2 "pingpong B")

**Examples**
- `batch-20261104-021759-ab-osc-trace-v66-fresh-gen-s1/480-mut-corridors-600201801-21`, team B, h6 Cassi, r277-282,
  carrying 21 gems.
  - r277-278: chain-farm picks g17 (0.29 vs from-altar 0.22), so `banking 0` and the walk heads to g17.
  - r279: `may_chain` is false, so `banking 1`, `bank_gems` runs and walks toward the altar.
  - r280: back to g17.
- `batch-20261104-021838-ab-osc-trace-v61-ladder/161-03ultrastarvation-12`, h2 Marcella, r414 and after.
- `batch-20261104-021721-ab-osc-trace-v68-fresh-gen-s1/511-mut-the-pack-600201800-12`, team A, h0 Ryth, r415 and
  after.
- Also seen: 072-caves, 170-far-altars, 100-classic, 230-gem-centre, 026-galaxy.

**Mechanism.** `carry_bag` (economy/bank.cc:1202-1254) sets `memory.banking = close || walked || !may_chain(..) ||
!farm(..)` at bank.cc:1248. `may_chain` (bank.cc:1043-1045) is `!credible_enemy_may_hit_within(here,
pursuit_steps)`. An enemy at the edge of that horizon, or one that goes in and out of sight, flips whether we chain
to a group or walk to an altar, and the two goals lie in different directions.

**Confidence.** Confirmed by trace (CB/CBF/FBAG) for corridors and ultrastarvation.

**Fix directions**
- Hysteresis on `may_chain`: once a chain is abandoned for safety, bank until the bag is submitted, or for N turns.
  Or require the threat to persist before abandoning a chain that is under way.

**Risks.** Chaining under a real, newly seen threat loses the bag. The asymmetric version (abandon quickly, resume
slowly) is the safer one.

### 6. make_way swaps with a stationary ally (C1 ≈ 20% of the sample, ≈ 3-6k turns: the "constant-distance sidestep")

**Examples**
- `batch-20261104-021623-ab-osc-trace-v65-fresh-gen-s1/385-gen-topo-odd-spawn-600207101-12`, team A, h0 Vesper Vale,
  r814-823: `MW me 17,7 ally 18,7 away 16,7`. The next turn `walk_on`'s descend steps back next to the ally.
- `batch-20261104-021505-ab-osc-trace-v69-fresh-gen-s1/432-gen-topo-tree-600206406-21`, team B, h6 Vesper Vale,
  r306-312.
- Also seen: 043-atoll, 419-topo-split, 376-topo-necks, 293-labyrinth.

**Mechanism.** `make_way` (model/pathing.cc:1507-1557) runs when the route fails because of an ally. The champion
with fewer gems, or the later name, steps to the tile farthest from the ally. The next turn the goal is unchanged,
the ally hasn't moved (it is working or capturing), and `walk_on`/`descend_with` walks straight back.

**Confidence.** Confirmed by trace (MW then DS).

**Fix directions**
- Remember the yield: don't re-enter the ally's adjacent tile while that ally still stands there.
- Or pick a different goal tile of the same group.

**Risks.** Minor; groups with one approach tile may need a wait instead.

### 7. Yield-capture step off / step on (C1 ≈ 409 episodes, 2.7k turns)

**Examples**
- `batch-20261104-021547-ab-osc-trace-v67-ladder/156-03shrines-21`, team B, h6 Cassi, r94-99, a 2-cycle.
  - At (25,9) on a cleared group, `yield_capture` steps off to (26,10): `TM site yieldcap`.
  - Next turn the farm's route walks back to (25,9).
- Also seen: 490-islands h9 Issac, 166-adgato-gemcombat2 h8 HoR, 384-topo-odd-spawn, 187-dungeon, 006-altar-poor h4.

**Mechanism.** `yield_capture` (economy/capture.cc:336-345) only acts when we stand on the cleared group:
`group_at(here)`, at capture.cc:340. Off it, it returns false and the farm's goal tiles still include the group, so
`farm_turn` walks back on.

**Confidence.** Confirmed by trace.

**Fix directions**
- After a yield, drop that group's tiles from the farm's goals while the capture holder is on it (a `memory.yielded =
  {g, until}`).
- Or have yield return true (hold) while adjacent.

**Risks.** None obvious; the yielder idles anyway.

### 8. Chase dropped because the strike search moves first (C4 ≈ 13%, ≈ 7k turns)

**Examples**
- `batch-20261104-021721-ab-osc-trace-v68-fresh-gen-s1/463-gen-wild-600206203-12`, team A, h0 Vesper Vale, r832-835.
  The branch goes F (with `srch:nohit`, search moved), then C toward e5 at d 7, then F with srch, then C.
- Also seen: 412-topo-split h5 Vesper Vale, 496-mut-ribs h10 Marcella, 490-gold-rush, 232-gem-drought h4 Vendetta.

**Mechanism.** The strike search (`plan_strikes`, bot.cc:220-232) is planned with `intent.group =
memory.farm_group`. The chase is only `intent.aim` (`chase_aim`). On turns when it finds no hit it may still take a
move toward the farm intent. The turn then ends without `prey()` being asked (no PY line), so `chase` doesn't run.
The next turn the search does not move and the chase resumes. The alternation follows the search's move parity.

**Confidence.** Likely: the TM site and the missing PY lines are traced, but the search's internal choice is not
logged.

**Fix directions**
- When last turn was a chase and the prey is still seen, give the search the chase's goal as the intent group or
  goal.
- Or skip no-hit search moves when a chase is pending.

**Risks.** The search's no-hit moves are sometimes positioning for next turn's hit.

### 9. Prey lost from sight after our step (C4 ≈ 12%, ≈ 7k turns; C2 BC "chase:unseen")

**Examples**
- `batch-20261104-021759-ab-osc-trace-v66-gen/263-gen-hedges-600102900-12`, team A, h4 Marcella, r592 and after.
- `batch-20261104-021623-ab-osc-trace-v65-gen/124-gen-continent-600102800-21`, team B, h5 Marcella, r641-650:
  5 C→B exits with `seen 0 lost 0`.
- Also seen: 150-03reef h6 Cassi, 142-continent.

**Mechanism.** `prey()` (fight.cc:585-608) sees only `seen_enemies() | lost_prey`. `lost_prey` (fight.cc:~550-570)
keeps an unseen prey only if it was engaged last turn and every tile it could have reached is within our vision. A
prey at range 8 that steps out after our step fails that test. We fall back to bank or farm, step back, see it again,
and chase.

**Confidence.** Confirmed by trace (PY `seen 0 lost 0` with the enemy one tile beyond vision in extract).

**Fix directions**
- Keep the last-seen prey as a goal for one or two turns (a "search last known position") instead of dropping to the
  farm.

**Risks.** Chasing ghosts into fog; bound it to a couple of turns.

### 10. Smaller C1 cases

- **step_safely avoid toggle.**
  - Example: `batch-20261104-021721-ab-osc-trace-v68-ladder/128-02the-pond-21`, team B, h6 Marcella, r1337-2000,
    664 turns.
  - Path: farm `cross()` → `take_hop` (bank.cc:785) → `step_safely` (guard.cc:17, `near =
    avoid_within(here, vision_radius)`). The avoid walls the hop source (22,20) only from (13,24).
  - Confirmed. Rare (2 of 28) but long.
- **travel-dash toggle.**
  - Example: `batch-20261104-021838-ab-osc-trace-v61-fresh-gen-s1/159-gen-dash-lattice-600207618-12`, h2 Issac,
    r600-900. The enemy at (42,26) is visible only from (41,18). pathing.cc:1121 turns the dash off, so the route is
    9 steps walking instead of 4 with the dash.
  - Also seen: 051-00quarry h4 HoR. Confirmed. About 1 in 28 of the sample.

## C2 and C4 summary of the samples

- **C2.** The four parts: wander BC (48k turns), wander B (43.6k), pingpong B (35.4k) and pingpong BC (9.9k). In 27
  valid windows:
  - BC prey visibility or own-ground (§3, §9): 10.
  - Bank versus farm (`may_chain`, §5): 7.
  - Unexplained route: 3.
  - Bank versus strike search: 2.
  - Descend: 2.
  - Avoid: 1.
  - Unconfirmed: 289-gen-jungle h2 Issac r1018-2000, 983 turns, `close = 1`, descend then wide route then dash back.
    Probably §2 (a blocker in the corridor).
- **C4.** The kinds: pingpong CF (14.1k turns), jitter CF (13.4k), preyflip CF (11.4k), preyflip BC (5.4k) and
  preyflip CFR (5.0k). Where ~100 chase exits or prey switches end:
  - own-ground: 30.
  - Strike search moved us: 13.
  - Unseen (`lost_prey` empty): 12.
  - Another branch first: 10.
  - Two-prey re-rank by cost: 6.
  - Spawn line: 4.
  - Fight lost because of `late` joiners: 4.
  - Fight lost: 3.
  - Seed example 024-archipelago team B h4 Vesper Vale r580-627 reproduced the CFCF with prey [1,2]. Its exits are
    own-ground and re-rank (the dungeon 181 pattern: e9's own-ground flips, and e7's fight is lost because of
    `late`).

## False positives

- **C3 capture/recall sequences** (15,985 of 66,838 episodes, 691k turns): the claim changes through Q/K/H as the
  group is captured and we recall or mend. This is normal.
- **C3 "farm churn" with no return** (32,446 episodes): mostly re-targeting after a group is cleared or captured.
  Only the A→B→A returns without work (§1) are real.
- **C3 returns where B was worked** (46k of 142.6k): legitimate.
- **C3 overall.** About 17k real-flipflop episodes are real (≈ 26%). Counting the short no-work churn too gives an
  upper bound near 45%. Of the no-work stints, those of 6 or more turns (23k, 282k turns) are largely plan changes
  after a long walk, not oscillation.
- **C1 camp-attack shuffle** (47 episodes, 321 turns): repositioning among attack tiles while hitting. Fine.
- **C1 "goal-moves"** (269 episodes): the goal group moves (a crew re-plan); mostly fine.
- **C2 strike-search hit versus bank step** (e.g. 479-mut-corridors h2 r1121): the champion strikes, then banks.
  Productive.
- **C4 "preyflip" without ping-pong pairs** (9 of 24 in the first sample, ≈ 30% of preyflip turns): switching between
  two prey that both remain valid as positions change, while closing in. Mostly fine; the cost re-rank (6 cases) is
  borderline.

## What remains

- §2's share of C1's "route r+ alternating distance" category (911 episodes, 8.4k turns) is inferred from 4 traced
  cases; other wall sources may contribute.
- §8: why the strike search's no-hit move is chosen (it is not logged).
- C2 wander B (43.6k turns): about a third of the sampled windows were invalid (fuel drift), so its split between §2
  and §5 is the least certain.
