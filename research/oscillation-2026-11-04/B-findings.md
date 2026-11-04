# B: stuck / stationary champions: findings (phase 1)

**Scope.** The B groups in `replays/osc/all/groups/`:
- B1, farm walk fails: 23,238 episodes, 291,695 turns.
- B2, bank walk fails: 3,968 episodes, 99,576 turns.
- B3, farm idle with no walk: 12,657 episodes, 374,369 turns.
- B4, siege/kite: 4,731 episodes, 294,512 turns.

B1 and B3 overlap: the same spans are often flagged as both kinds.

**Method.**
- I ran a ground-truth classifier over all 5,485 B replays: `extract.mjs` boards, flood fills from the champion under each obstacle set, and the occupancy of respawning camps.
- I reran 93 games exactly with an instrumented copy, `bots/variants/astraeus-trace-B`, which is astraeus-trace plus the following:
  - **`WF` line.** Printed on every failed outer `step_route`, `descend_with` or `step_towards_funded`. It gives the goal tiles reachable within the search cap under each obstacle set:
    - `st`: static walls;
    - `ds`: dash walls;
    - `lc`: static walls plus live camps, with `lcU` the same uncapped;
    - `bl`: `blocked()`;
    - `-al` / `-en`: `blocked()` without allies / without enemies;
    - `full`: with the avoid and guard boards, with `fullU` the same uncapped.

    It also gives the dash slot and the neighbour codes.
  - **`X` line.** The exact `return` line taken in `farm_turn`, `siege`, `kite` and `carry_bag`, plus kite/siege state flags.
  - **`NB` line.** Printed when farm prices nothing (`best < 0`). It gives `short_by`, the share, and per group: steps, state, respawn wait, taken, claimed, kited and affordable.
- Variant line numbers are shifted. Every file:line below is in `bots/astraeus/src`.
- Episodes that did not reproduce under the instrumented build are listed at the end. `tb_x` writes outside `debug_block` shift fuel slightly.

Sub-issues are ordered by turns wasted. Confidence is "confirmed" only where a trace shows the input that flips.

---

## 1. Shared-gems maps: the whole team stands on two kite stations all game (B4, 224k turns)

**Prevalence.**
- 1,089 B4 episodes, 51 games, 224,014 turns: 76% of B4.
- On `gen-shared-gems-600101605` it runs to about 10-18k turns a game: all five champions for about 2,000 rounds.

**Examples.**
- `replays/batch-*-v69-gen/373-gen-shared-gems-600101605-12.repl26a`, team A, all of h0-h4 (Cassi, Issac, ...), r~20-2000. Score 0-0; the tiebreak decides.
- `.../315-gen-shared-gems-600201608-12.repl26a` (v69-fresh-gen-s1), team A. h0, h2 and h3 are "placed" for about 1,450 turns each. The only caster, Cassi h1, flips R/G on `home:standlost`. The group was hit only at r464-472. Score 0-0.

**Board.** The map's single gem group (112 gems, kited) is asleep. Our Issac stands on station (17,17) and an enemy on (26,17). The other three champions stand short of the group, off any station, and never act on it. Monster damage is 0 for every champion all game.

**Mechanism (confirmed by trace).**
- `decide()` sends every turn to `kite()` on a shared-gems map (`bot.cc:375`, `world.map().shared_gems ? kite(...) : siege(...)`), so `farm()` never runs.
- In `kite()` (`economy/siege.cc:594`), a champion without spells gets as stations a square of `station_range` = `ability_range` (4) round each striker (`siege.cc:680`), minus `threat`, the strikers' reach of 4 (`kg`, `kgoals 2`). Only two tiles survive: (17,17) and (26,17).
- The champion on (17,17) returns at `siege.cc:743-749` (`placed`: no hit on an asleep group, return true).
- The others return true at the final `return true` (`siege.cc:782`) every turn:
  - they are inside `vision_radius + station_range`, so the far-walk block (`:754`) is skipped;
  - `step_towards(goals, &threat, cap)` fails because the goals are occupied (ally and enemy);
  - the fallback walks only `!safe_here`.
- Nothing measures progress. No branch hands the turn back unless `ground_stations && !moved && !hit_safe && safe_here && !placed` (`:781`), and these champions have no ground stations.

**Fix directions.**
- (a) When no ally casts and the group is asleep, let `kite()` return false so farm or siege runs; the asleep group needs no kiting.
- (b) A progress budget: if no hit lands on the kited group for N rounds, drop the kite plan for that champion.
- (c) Widen non-caster stations to `range + reach` ring tiles, or let non-casters attack (wake) once allies are in place.

**Risks.** Waking an Elk-type kited group without casters could cost HP. The point of kite on these maps was to avoid exactly that. The fix needs a solo/AB run on shared-gems maps, where the current behaviour scores 0.

## 2. A dasher on a dash-only island with an enemy within 10 (B1 78k, B2 50k, B3 65k; about 193k turns)

**Prevalence.**
- 4,504 episodes, 468 games.
- Median length 13 rounds, but 98.5k turns are in episodes of 200 rounds or more.
- Map families: atoll 69k, moated-altars 39k, dash-lattice 37k, topo-split 19k, 02the-pond 17k, archipelago 3.5k.
- Dashers only: Heart of Ruin 65k, Issac 62k, Vesper Vale 43k, Vendetta 18k, Ren 6k.

**Examples.**
- `replays/.../128-02the-pond-21.repl26a`, team B: h7 HoR at (18,19) r29-2000 and h5 Issac at (18,21). Frozen for 1,972 rounds; final 15-21.
- `.../063-gen-atoll-600101926-12.repl26a`, team A, h4 Ren (22,39), r1112+ (B1).
- `.../051-gen-atoll-600101912-12.repl26a`, team A, h2 Issac (9,16), r1238+.
- `.../155-gen-dash-lattice-600107600-12.repl26a`, team A, h5 HoR (52,30), r685, 59 turns, carrying 17 gems (B2).
- `.../420-gen-topo-split-600106500-21.repl26a`, team B, h5 Issac (25,21), r784.

**Board.** On the pond, the travel plan dashed onto the island at r21. The champion waited out the cooldown (r22-28, `r+` with no move). From r29 every walk fails. The enemy that keeps us there is itself stuck at (13,13), so neither side moves again.

**Mechanism (confirmed by trace).**
- `WF` on these episodes reads `st 0 ds N dash -1/0`: no goal tile is reachable on foot, some are reachable with dash walls, and no dash slot is offered.
- `Pathing::travel_dash()` (`model/pathing.cc:1121`) returns no slot whenever `enemy_within(world_, my_pos(), travel_dash_clearance)`, with `travel_dash_clearance = vision_radius + dash_range` = 10 (`pathing.cc:24`).
- `step_route` / `descend_with` and `walk_on` therefore search with walking only, and fail every turn.
- `make_way` and the dasher fallback `walk_on` (`farm.cc:1978`) cannot help: there is no foot exit.
- The rule is Chebyshev distance to any visible enemy. It does not ask whether that enemy can reach us, and on islands it usually cannot.

**Fix directions.**
- (a) When the static walk from here reaches no goal (`st == 0`), allow the travel dash regardless of clearance, or with a smaller clearance. On an island, the dash is the only move.
- (b) Measure clearance by the enemy's walk or dash reach to our landing, not by Chebyshev distance.
- (c) Exempt enemies that are themselves walled off.

**Risks.** The clearance exists so that a dash does not land us beside an enemy or spend the escape dash. Rule (a) can still land next to a waiting enemy on an atoll, so it should keep the landing-safety checks: the post-dash enemy check at `pathing.cc:1412-1422` already exists.

## 3. Live camps block the capped search, or seal the goal (B1, B2 and B3; about 40-90k turns)

**Prevalence.**
- The classifier's `live_camps_block` class: B1 17.4k turns (466 episodes, 160 games), B2 7.5k, B3 14.8k.
- Most of the idle part of `open_path_but_fail` (B1 34k, B2 12k, B3 16k) is also this. The static classifier ignores live camps and the search cap, and the trace shows `lc 0` in most of those samples.
- Of 5,687 failed `r` searches in the reruns with `st > 0, lc 0`:
  - 2,328 (41%) have `lcU > 0`: a detour exists beyond the cap;
  - 3,359 (59%) have `lcU 0`: every goal is sealed behind live camps.

**Examples, cap too small** (a detour exists beyond `cap`):
- `.../328-gen-three-lane-600202503-21`, team B, h11 and h10, from r13-16, cap 46-49: 359 and 304 failing turns.
- `.../301-gen-labyrinth-600103814-12`, team A, h2 Cassi (11,19), r30 and r753: 245 turns.
- `.../349-gen-topo-backdoor-600206710-12`, team A, h2.
- `.../376-gen-topo-necks-600207000-21`, team B, h9.

**Examples, sealed** (`lcU 0`):
- `.../140-03fan-21`, team B, h8 and h6, from r1: 801 and 607 turns.
- `.../479-mut-corridors-600101814-12`, team A, h1 Cassi (24,0), goal (16,21): every corridor crosses the camp band at y=19-20.
- `.../033-gen-archipelago-600202025-12`, team A, h0 and h3.
- `.../388-gen-topo-odd-spawn-600207104-21`, h8 (bank).
- `.../217-gen-fortress-600102200-12`, h4 Marcella (bank).

**Mechanism (confirmed by trace).**
- Farm prices `best` by `best_steps`, which are static centre-field steps that ignore live camps. It then walks with `cap = best_steps + max_detour` (`farm.cc:1901`), and live camps are walls.
- When the detour round live camps exceeds `max_detour` (16), or no detour exists, both `step_towards` calls fail (`farm.cc:1974-1976`).
- A non-dasher has no fallback (`farm.cc:1978` is `dasher` only) and stands still. Next turn it re-picks the same `best`, because pricing never sees the live-camp walk.
- Dashers also fail in `walk_on` (`r-r-d-` tags), since its fields carry the same live-camp walls.
- Nothing caches the failure into the pricing.

**Fix directions.**
- (a) On a failed capped walk, retry once uncapped. Or remember `{group, here}` as unreachable for N rounds, so pricing (`steps_known`) takes the live-camp walk or skips the group.
- (b) When sealed, price the blocking camp as the target (it is often harmless), or treat the sealed group as unreachable.

**Risks.**
- An uncapped search costs fuel. It should be bounded, or happen once per failed group, not every turn.
- Skipping a sealed group can make allies drift to worse groups when the seal is about to be cleared by someone else.

## 4. Allies hold the only way (B1 43k, B2 8.5k, B3 20k; about 72k turns)

**Prevalence.** `allies_block`: B1 3,781 episodes in 688 games; B2 511 in 250; B3 763 in 299.

**Examples.**
- `.../376-gen-topo-necks-600207000-21`, h10 Willow (35,29) r1810: `bl 0 -al 35`.
- `.../380-gen-topo-necks-600207008-21`, h7 Marcella (8,37) r974: `bl 0 -al 9`.
- `.../409-gen-topo-necks-600107008-12`, h3 Issac r152, bank: `-al 1`, `r-r-d-r-r-`.
- `.../351-gen-topo-backdoor-600206713-12`:
  - h0 Vendetta (12,78) carries 71 gems in siege. Ally Prism h3 at (13,76) in a 1-wide corridor blocks it: 1,088 + 1,127 turns.
  - Prism itself fails with `st 6, lc 0`: live camps, so this is sub-issue 3.
- `.../190-gen-topo-shortcut-600106901`, h8 Prism, holding 329 gems in F.

**Board.** Neck maps: a 1-wide corridor with an ally standing in it, usually an ally that is itself waiting (at its goal, or stuck as in sub-issue 3).

**Mechanism (confirmed by trace).**
- `step_route` calls `make_way` only when `route()` returns unreachable (`pathing.cc:1482-1504`).
- `make_way` (`pathing.cc:1507-1554`) has three limits:
  - it skips an ally standing on its own goals (`opened = true; continue`);
  - it asks the ally with fewer gems to back off;
  - the blocker itself never yields: the ally has to run make_way on its own turn.
- An ally that is itself stuck or waiting therefore never moves.
- `Pathing::step_towards_funded`, used by siege, kite-cleared and siege-cleared, has no `make_way` at all (`pathing.cc:1559-1600`).
- Siege-engaged champions also never hand the turn to farm on a failed step (`siege.cc:333` applies only `!engaged`), so they repeat the failure every turn (`siege.cc:340`).

**Fix directions.**
- (a) Let `step_towards_funded` try `make_way` too.
- (b) A waiting champion that stands in a 1-wide neck on an ally's route (comms: the ally's next step or goal) steps aside.
- (c) An engaged siege whose funded step fails k turns running falls back to farm (like the `!engaged` exit).

**Risks.** Make-way swaps can turn into ping-pong (family A). A waiting champion that steps off its station loses its stand.

## 5. Our own champions keep a respawning camp from returning (about 23k turns, all of B)

**Rule.** A group returns only when all its camp tiles are empty at round start.

**Prevalence.**
- Episodes near an ally on a respawning camp whose timer has reached 0: B1 17.0k turns, B2 4.6k, B3 1.8k.
- By map: 00vault 9.9k, gen-labyrinth-600103814 4.3k, topo-backdoor-600206710 2.2k, 01boss-battle 1.7k, 02stalactites 1.5k.

**Examples.**
- `replays/batch-*-v61-ladder/072-00vault-21.repl26a`, team B, r100-1849:
  - Vault group 0 (camp tiles x=12..18) has timer 0.
  - Our Cassi h4 at (18,14) and Issac h5 at (18,15, 4 gems) stand on its camp tiles. Their exits (19,14)/(19,15) are held by allies Prism h6 (118 gems) and Marcella h7, and (11,15)/(11,16) by enemies.
  - Prism's goal is that group's adjacent tiles (here is in goals), so it waits forever. Cassi and Issac have `bl 0, -al 2`, and make_way skips allies on their goals.
  - Prism waits 1,750 turns with 118 gems unbanked; Issac's B2 lasts 1,539 turns.
- `.../121-02stalactites-12.repl26a`, team A, r299-~1800:
  - Group 8 has timer 0, and h1 and h3 wait on its goal tiles (mode J, inG 1, f exit at the farm stay).
  - h4 ping-pongs (14,20)↔(14,21) every turn: both are group 8 camp tiles, on its walk to group 7's attack tile (17,21) (`r+` each turn). So the camp never returns, and h0 and h2 (210 and 246 gems) sit in W.
  - The h4 ping-pong is family A's; its effect here is B.
- `.../302-gen-labyrinth-600103814-21.repl26a`, h10 HoR r175, 1,065 turns.

**Mechanism (confirmed by trace on vault; the stalactites board and trace show the occupant).**
- Pathing knows the rule:
  - `approach` drops a respawning group's tiles from the goals (`pathing.cc:403`);
  - `drop(tiles, ...)` at `:501`;
  - `Pathing::leave_respawning` exists (`pathing.cc:1468`).
- But farm calls `leave_respawning` only when `best < 0` (`farm.cc:1841`).
- A champion with a `best` that stands on, or walks through, another group's respawning camp tiles is never told that it holds that group back.
- Waiters at the group's goal tiles do not ask the occupant to leave, and make_way skips allies on goals.

**Fix directions.**
- (a) In farm's final walk, or before staying, add "if I stand on a respawning camp whose respawn round has passed and an ally or I wait on it, step off" (`leave_respawning` with the zone).
- (b) Mark respawning-and-due camp tiles as an avoid board in the walk, so routes do not idle on them.
- (c) The waiter publishes its group in comms, and an occupant that sees it yields.

**Risks.** Stepping off a camp tile on a 1-wide corridor may fight the route (sub-issue 4). An avoid board on camp tiles can seal routes on corridor maps where the camp tiles are the only floor.

## 6. B3 "farm prices nothing" (`best < 0`) (243k turns): mostly intended waits

**Mechanism (confirmed by trace).** Every rerun B3 `no_goal` sample exits at `farm.cc:1836-1842`: `best < 0`, then `leave_respawning`, which is a no-op off a respawning tile, then return true. The cause was decomposed with ground truth plus `NB`.

| cause | turns | share | games | verdict |
|---|---|---|---|---|
| All gem groups respawning; each is skipped because its wait on arrival exceeds `params::max_wait` = 2 (`farm.cc:1531`) | 74.2k | 31% | 275 | Mostly intended. It walks once the wait drops. The cost is position: it idles wherever it is, not near the group or the enemy's approach. |
| A tributing ally's bag already wins: `gems_short()` (`bank.cc:139`) subtracts visible allies' tribute-channel gems, so `short_by <= 0` and every worth `min(gems, short_by) <= 0` | 58.2k | 24% | 597 | **False positive** in 636 of 657 games: the tribute lands, median 27 rounds later. **Real** in 19 lost games (3.0k turns), where the tributer is stunned or locked again and again. Example: `.../batch-*-v68-ladder/170-adgato-gemcombat4-21.repl26a`, team B. h8 Issac channels from r529 on the altar with a growing bag (1,353 gems, b = 136 turns), and stun or lock cancels it again and again. The other four idle about 850 rounds with `short -1231`. Our score stays at 878 from about r870, and the game is lost 878-1026 at r1458. |
| Endgame: every group too late to clear and bank before r2000 (r0 >= 1850) | 46.8k | 19% | 387 | Intended (`too_late`). |
| Few (2 or fewer) or several alive gem groups, none priced | 56.4k | 24% | 745 | Mixed. Seen in `NB`: groups claimed by allies, where `health_left <= 0` so the share is skipped (`farm.cc:1601`); groups unreachable on foot with no crystal (`steps 65535`); and `U` (unaffordable). Example: `.../014-gen-archipelago-600102000-21`, team B, h8 HoR on its spawn island r1-56: 8 alive gem groups at Chebyshev 21-32, all `steps 65535`. The only island group, g1 (gold), was being taken by an ally. It moves at r57, when g1 is back. |
| Monolith-only map, non-crew (Willow): every group is `U` | 7.3k | 3% | 29 | Intended by design (a Monolith is a crew's only). Whether Willow should trail the crew to heal is a strategy question. |

**Fix directions.**
- (a) Pending-win: count a tributer's bag only while its channel is progressing. For example, drop it after one cancel, or after the channel has been restarted more than k times. Alternatively keep farming at a reduced weight rather than pricing everything at 0.
- (b) All-respawning: pre-position on the soonest-due group, pricing the wait, instead of skipping groups with `idle > max_wait`.

**Risks.**
- (a) sends allies away from a tribute they might be defending.
- (b) changes pricing that `max_wait` was tuned for (CHANGES history), and needs an A/B.

## 7. Siege (non-shared B4): engaged, funded walk fails or alternates (about 70k turns)

**Prevalence.** Non-shared B4 is 70.5k turns: stuck_idle 38.5k, wander 17k, jitter 7.5k, ping-pong 7k. By map: gen-monolith-only 16.5k (62 games), topo-backdoor 10.8k, mut-contest 6.1k, arena 5.5k, topo-shortcut 5.2k, 00contest 3.6k.

**Stuck (confirmed on topo-backdoor-600206713).**
- Engaged siege (`sf 0x1e`, staged 0.5), and `step_towards_funded` fails every turn.
- The cause is the corridor and ally block of sub-issue 4, with no `make_way` in the funded walk.
- An engaged champion never returns false (`siege.cc:333`), so the exit at `siege.cc:340` repeats for 1,000+ turns.

**Wander / alternation (trace, likely).**
- Example: `.../051-gen-arena-600202624-12`, team A, h0 Vesper Vale (3,374 HP), r716-805. Engaged on the Monolith, all staged (`sf 6`, sst 0.92-1.00).
- On odd turns `f+` steps toward a caster station 2-3 tiles away. On even turns an `m+` `try_move` runs before siege (with `srch:nohit` from the strike search), after which siege's funded step fails (`m+f-`).
- So it cycles (13,12)→(14,13)→(13,12) and never reaches the station or casts.
- Other examples, wander in G with `s` exit 340 and `f+`: `gen-arena-600102601` h1 Vesper; `mut-contest-600201818` h7 Issac; `01the-farm` h1 Issac; `gen-dungeon-7713102428` h4 Willow; `02guardians` h3 Marcella.
- This is a two-decider alternation. It belongs with family A, which should identify the `m+` source: strike-search step or guard step.
- Also seen: `tanked` (an ally nearer the Monolith takes its hits) toggles the goal set between the ability-range ring and the range ring (`siege.cc:296-310`), which gives jitter.

**Fix directions.**
- (c) of sub-issue 4.
- Let the pre-siege move respect the siege station (don't step off a station the siege will walk back to).
- Hysteresis on `tanked`.

## 8. Smaller walk-failure causes

- **Avoid zone (pack_zone) seals every goal.**
  - Example: `.../036-00interlock-21`, h5 Cassi r422: `bl 10, full 0, av 132`. The zone (`farm.cc`: `zone = bag_at_stake > 0 ? pack_zone : nullptr`) comes from her partner's bag. `off_zone(goals)` leaves goals, but the route cannot cross the zone.
  - Likely; a few k turns.
  - Fix: when every goal is unreachable outside the zone, retry inside it, or bank first.
- **Enemies hold the way.** Example: `.../184-gen-dungeon-600202414-21`, h7 Prism with 337 gems in F, `-en 45`. About 2.6k (B1) + 1.4k (B3) turns.
- **Bank goal reachable only by dash for a non-dasher** (`nearest_goal_off_foot`, B2 5.9k).
  - Examples: `.../155-gen-dash-lattice-600207615-12` h1 Cassi (`d-`, `gd -2`, `av 121`); `.../001-00ambush-12` h4 Marcella (`st 0 ds 32`).
  - The altar goal set includes tiles reachable only with dash walls; `descend_with` fails every turn.
  - Likely; not traced further.
- **Large bags left in farm.** Prism with 118, 329, 337 or 427 gems stays in F (00vault, topo-shortcut-600106901, dungeon-600202414, atoll-600101913) instead of banking. Not investigated: `banks_bag` / `bankable_bag` should be checked by whoever takes the bank family.

## False positives (phase 2 can skip these)

- **Busy ranged champions** (B1 `open_path_but_fail/busy` 22.7k, `goal_is_here/busy` 25.1k turns): they hit a camp or a champion almost every turn. The ranged attack after the strike search spends the walk (`kite`/farm comment: "With the walk spent ... none of it moves us"). The walk "fails" because `my_can_move()` is false. That is working as designed.
- **Melee at its goal after a `srch:nohit` strike search** (`goal_is_here`, `d-`, `inG 1`; for example oasis Issac and diagonals Vendetta). `walk_on`'s descend fails because the champion is already on the goal, and it attacks or waits there. It counts as a walk failure only by tag.
- **Waiting on our goal for a short respawn** (`goal_is_here` idle, timer 40 or less, about 21.5k turns): intended camping on the group. The exception is timer 0 with an ally on the camp, which is sub-issue 5.
- **Pending winning tribute** (sub-issue 6): 636 of 657 games are won within about 27 rounds.
- **Endgame too-late idle** (r >= 1850, about 47k turns).
- **Monolith-only non-crew Willow** (about 7k turns): by design.

## Not reproduced under the trace build (fuel drift)

These were not used for mechanisms:
- mut-lost-world-600101808 Willow
- topo-web Vesper
- topo-capital-600107400 Vesper
- atoll-600201911 Marcella
- hole-maze-600107500 Cassi
- hole-maze-600107510 Issac
- hole-maze-7713107508 Vesper
- mut-contest-600101800 Issac

In topo-backdoor the episode shifted (r305) but reproduced in substance.

## Tools and data

- Variant: `bots/variants/astraeus-trace-B/`. The `WF`/`X`/`NB` lines are in `debug_block` except the `tb_x` exit-line writes. Touch `src/unity.cpp` after an edit: the build cache can miss it.
- Scratch (session-local): `/tmp/claude-1000/-home-ubuntu-cambc-autumn/62251b19-0166-4ed1-9aaa-ba9841b0ddec/scratchpad/`:
  - `py/classify.py`: ground truth;
  - `cls.jsonl`, `bep.json`: per-episode classes;
  - `rerun.py`: one game with the variant;
  - `board.py`: ASCII board at a round;
  - `py/show.py`: D/X/WF/NB at an episode;
  - `pend.json`, `ng.json`, `resp.json`: the sub-issue 5/6 tallies.
