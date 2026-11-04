# Stream 1: terrain-aware enemy reach (fix notes)

Branch `osc/1-terrain-reach` (worktree `/home/ubuntu/wt/osc-1-terrain-reach`), from astraeus 088bf3f4.

## Plan

### Confirmed mechanism (source, 088bf3f4)

- `Safety::approach(e, p)` (safety.cc ~2238) is `max(1, dist(p, acts_from(e)) - reach)` once e's one-turn
  `Reach` misses p: straight-line. Every multi-turn reach reads it: `stand()` walkers/joiners (want_home's
  pursuit horizon), `late()` (chase fights), `turns_to_kill_idle()` (hold_outlasts), and through the same
  pattern `recall_outruns` (bank.cc ~1066) and `paying_soon` (fight.cc ~273), which also price unseen
  enemies seen last round as `dist(p, e.pos) - reach`.
- `Pathing::travel_dash()` (pathing.cc ~1121) refuses the travel dash for any visible enemy within
  Chebyshev 10 (`vision_radius + dash_range`); `travel()`/`take()` repeat the test on live tiles after a
  bump or a landing.
- `recall_line` (fight.cc ~326) raises the line for any visible enemy within `max_reach + threat_radius`;
  `may_chain` and `engagement_near` use straight-line enemy reach the same way.
- The one-turn `Reach` (visible enemies' tile sets) is already terrain-aware; unseen enemies' `possible`
  sets are grown over their walls. Only the multi-turn and clearance tests are straight-line.

### The model: one terrain distance

`D(e, p)`, "the Chebyshev distance at which, on open ground, e would reach p as soon as it does here":

    D(e, p) = max(dist(o, p), a + min{ S(q) : dist(q, p) <= a })        (dist(o, p) <= a: D = dist)

- `o`: where e acts from (its tile, or a seen teleport's landing; for an enemy seen last round, its last tile).
- `S`: static king steps from `o` over the tiles open to e (`blocked_for_them`: walls, holes, altars, our
  spawn). For a dasher, the hole and altar tiles a dash jumps (standable on two opposite sides, thinned as
  our own `crossable` is) are open too, at the two steps the dash is. Units and camps are left out: they
  move or die, so this stays a lower bound on the walk.
- `a`: e's act range without moving (basic reach with Varg's splash, unit/ground spells' reach, a landing
  dash's radius).
- On open ground `min S = dist - a`, so `D = dist` exactly: every caller keeps its tuned Chebyshev
  behaviour where nothing is in the way, and only terrain can raise D. An enemy walled off from every tile
  within `a` of p gets D = unreachable.
- Each threshold test `D <= X` is one host `reachable_tiles(o, X - a)` board (cached per enemy, origin and
  step count across turns: static terrain, so a stationary enemy costs nothing after the first turn) and one
  `any_within(board, p, a)`. A board that is the whole clipped square (no terrain within its steps) answers
  without the test; a board that stopped growing ends the search (a sealed island answers in one step).

### Callers (all read the same D)

1. `Safety::approach(e, p, horizon)`: `max(1, D(e, p) - reach)` where Reach misses; exact up to `horizon`.
   Callers pass their horizon: `stand()` (farthest), `late()` (pursuit_steps), `turns_to_kill_idle()`.
2. `Safety::walk_in(e, p, horizon)`: approach for a visible enemy, `D(e from its last tile, p) - reach` for one
   seen last round. `recall_outruns` and `paying_soon` both read it (they had the same code twice).
3. Pocket keep (`continue_recall`): wanting home with no walk home (`!on_foot`, or sealed in a camp ring),
   the recall is kept unless threatened now: retreat has nowhere to walk and damage cancels the recall anyway.
4. `travel_dash`: refused only for a visible enemy with `D <= vision_radius + dash_range` (the same 10 on open
   ground, so "the dash is the fight's" holds wherever a fight can come); the post-bump and post-landing
   checks use the same D from the enemies' live tiles.
5. `recall_line`, `may_chain` (`Safety::may_reach_within`), `engagement_near`: visible enemies by D.
   Unseen ones keep `possible` (already grown over terrain).

Left to stream 2: the pack zone (Chebyshev boxes; outmatched/keep_out), parity windows, joiners in the step
guard, vision toggles, the own-ground line.

### Fuel

Per threshold test ~150 (50x50) to ~400 (100x100) fuel, a new board ~100-250. Most queries hit the open
fast path. Expected: a few hundred to a few thousand fuel on turns with visible enemies near; plus a one-time
crossing build for dasher enemies (~3-8k, warmed in the turn's spare fuel).

## What changed (commits b0be7c90, 36da99bb)

- New `model/enemy_reach.{h,cc}`: `distance()`, `within()` (one test), `profile()/act_range()`, `widest()`,
  `origin()`, `warm_up()`. Boards: host `reachable_tiles(from, s)` over `blocked_for_them` (walkers) or
  `StaticMap::their_dash_walls()` (dashers), 24 LRU slots of up to 16 boards, kept across turns.
- `StaticMap::their_dash_walls()`: `blocked_for_them` minus `crossing_tiles(standable_them, unthinned)`;
  `find_crossings`' crossing part is now `crossing_tiles()` (same operations for our own champions). Warmed
  in main.cc's warm-up after the map's, without blocking the rest of the warm-up.
- `Safety::approach(e, p, horizon)` reads D; `walk_in` (recall_outruns, paying_soon), `may_reach_within`
  (recall_line, may_chain); `stand`/`late`/`turns_to_kill_idle` pass their horizons. `engagement_near`,
  `recall_line`'s visible loop and the crystal-landing `watched` test read D.
- `Pathing::fight_near()`: the travel-dash clearance by D, for enemies seen this round or last (as walk_in's
  callers count them; visible-only toggled with vision, C-findings §10), from `origin()`; the post-bump and
  post-landing checks by D from the engine's live tiles (an unmatched tile at the widest enemy profile).
- `continue_recall`: wanting home, not threatened, no walk home (`!on_foot` or `sealed_in`) and no safe
  tribute: keep the recall (A-findings §4's pocket keep).

## Auditor (read-only subagent) findings and responses

- Checked correct: horizon plumbing in every caller, D's open-ground equality (edges included), the open
  fast path, the "stopped growing => far" exit, act ranges per champion, the crossing refactor, `within()`
  scratch reentrancy.
- **Teleports judged from e.pos** in fight_near/recall_line/engagement_near: fixed (`origin()`/`acts_from`).
- **Thinned crossings drop real dashes** (a diagonal dash across a straight line): fixed, the enemy's
  crossings are unthinned (walking along a 1-wide line beside land is no shortcut). Left: knight-shaped
  dashes round a pond corner, dashes landing on a dead camp's tile (rare; adding them would let S chain
  across 2-wide ponds).
- **Unstarted teleport crystals** are not modelled: left (open issue).
- **Fuel**: threshold tests now one query (`within`); the exact `approach` loop usually ends at its first
  step. keep_out's 8 tiles x recall_line/paying_soon is the worst case: measured by the A/B's out-of-fuel turns.
  The warm-up no longer returns early when the dash walls can't be afforded.
- **walk_allies_in** (allies join by Chebyshev while enemies come by D): left; enemies walled off are no
  longer in those fights at all, which is the case that mattered. Noted for stream 2 (joiners).
- **Our chase** (kill_turn, intercept_steps, preyable) is still straight-line: left, a possible next
  oscillation (island enemies no longer push us home, so we may chase to the shore). Open issue.
- `enemy_area`/`avoid()` are next-turn Reach/Chebyshev squares: left (next-turn, not this stream's).
- Pocket keep: sound; only cost is channelling instead of striking first when an enemy shares the pocket.
- `fight_near(false)` is cached per round and tile: a ward revealing an enemy later the same turn on the same
  tile is missed until the live checks; accepted.

## Third change (1facb439, fixed in 2a6966d9): a withheld travel dash still travels when no walk reaches the goals

The 36da99bb detector batch showed an 823-turn freeze on `gen-dash-lattice-600107601-21` (team B, h5 Vendetta,
r1178-2000 at (45,33), every walk `r-r-d-r-r-` failing). Instrumented rerun: an enemy at (37,33) on open ground,
D = 8 <= 10, so the clearance withholds the dash (correctly by the reach model, as the old rule did), and the cell
has no walk out. "The dash is the fight's" only holds while a walk still reaches the goals; held on a dash-only
cell it keeps us there for good. `travel_dash()` now marks a dash `withheld` (fight_near alone left it out);
`step_route` releases it (`forced`) when the walking route to the goals is unreachable; a forced dash passes the
live post-bump/post-landing checks (the enemy near is already known) and its paths avoid visible enemies' tiles
(the planner otherwise assumes none is on a path's middle tile). Landings stay under the step guard. Rerun: the
Vendetta moves 166 times in the same window (was 0 in 823 turns).

1facb439 cleared the slot but kept `now`/`cool`, so dash-ready planning ran with no slot, and it ran an extra
route search on every withheld turn (OOF 89.6k vs 57.8k at 10k games, 50.0%). 2a6966d9 keeps the withheld
readiness apart (`withheld`, `withheld_now`, `withheld_cool`) and releases it only after the normal route
search came back unreachable, inside step_route's loop, so a reachable walk costs nothing extra.

## Fourth change (d62d050): cheaper threshold test (fuel only)

`reaches()` first tests the tile s steps straight towards p (one `is_set`, which settles it on open ground),
then falls back to `any_within`; step counts are taken lazily. `tools/fuel/bench.py`: 16/16 replays identical
to 2a6966d9, total fuel -0.09%.

## Episodes, before (phase 1 trace) / after (osc1-trace at b0be7c90; same opponent, map and sides)

Per champion window: turns, turns ending on another tile, turns with a failed walk, distinct end tiles.

| example | before | after |
|---|---|---|
| 128-02the-pond-21 (v69) B h5 Issac, h7 HoR r400-1450 | 1 tile each for 1,050 turns (frozen on the island) | 170 / 158 distinct tiles |
| 128-02the-pond-21 B h4 Cassi r400-1450 (B<->R at (5,12)/(6,11)) | 11 tiles, R 801 | 119 tiles, R 46 |
| 055-gen-atoll-600201904-12 (v65) A h4 HoR r156-1940 | R 1,785, moved 0, 1 tile | F577 B574 P101, moved 917 |
| 336-gen-moated-altars-600108109-21 (v69) B h7 Prism, 815 gems | R 1,179, moved 0 | W911 T182 B50 R28; bag banked in part, game won 686-288 (lost before) |
| same game, B h8 Marcella (B<->R (31,39)/(32,40)) | R590 B588, 2 tiles | W849 B147 F93, 98 tiles |
| 160-gen-dash-lattice-600207618-21 (v67) B h5 Issac r902-1954 | B528 R525, 6 tiles, every turn a failed walk | game over by r945 (won 1003-268) |
| same game, B h4 Cassi r896-2000 | R 1,105, 2 tiles | moving, game over by r945 |
| 062-gen-atoll-600201911-21 (v61) B h5 Cassi r653-1389 | R 737, moved 1 | F149 B93, 74 tiles |
| 155-gen-dash-lattice-600107600-12 (v69) A h5 HoR r685-800, 17 gems | B54 R43 | F90 R8, bag banked |
| 063 / 051 gen-atoll (v69) A h4 Ren / h2 Issac | already moving in this rerun's window | moving |

Game results over these 9 games: 6 won after, 3 before (single maps: noise). The moated Prism's new 911-turn
altar wait carries a 1,000-1,700 gem bag whose tribute channel (100+ turns) is never safe: a bank-family issue,
not reach. Before/after D lines: `unzip -p REPLAY team-b.stdout | grep -a "^D [0-9]* 7 "` on
`replays/batch-20261104-021505-ab-osc-trace-v69-gen/336-gen-moated-altars-600108109-21.repl26a` and the rerun in
the scratchpad (not kept); every rerun above reproduces from `tools/fastengine/runner/fastrunner run`.

## Detector, before (phase 1 astraeus-trace vs v69) / after (osc1-trace at d62d050 vs v69)

Same 1,024 games (maps/gen + fresh gen-s1, both sides). Outputs: `replays/osc/before-v69`, `replays/osc/osc1-d62d`
(intermediate: `osc1-b0be`, `osc1-36da`). Turns in episodes:

| kind | before | after | change |
|---|---|---|---|
| stuck_fail | 58,375 | 42,778 | -27% |
| stuck_idle | 79,162 | 62,129 | -22% |
| wander | 60,482 | 52,332 | -13% |
| preyflip | 4,070 | 3,660 | -10% |
| jitter | 34,225 | 32,335 | -6% |
| retreatchurn | 442,919 | 420,277 | -5% |
| branchflip | 178,457 | 171,895 | -4% |
| pingpong | 38,584 | 36,852 | -4% |
| goalflip | 251,809 | 243,892 | -3% |
| claimflip | 410,005 | 406,136 | -1% |

By branch, the reach-driven ones: stuck_fail B 8,035 -> 3,568, R 3,081 -> 1,326, W 1,085 -> 260; stuck_idle
B 5,776 -> 1,676, R 2,048 -> 429; pingpong R 8,721 -> 5,615, B 6,707 -> 5,820; jitter R 7,519 -> 4,609. The
`home:low` reason (recall_outruns refusing a recall) fell from 2,020 stuck_fail / 1,669 stuck_idle turns to
below the table's top four. At 36da99bb the per-family rises (topo-backdoor game 349 Cassi, dash-lattice
games 158 and 166) were single diverged games; 158's Vendetta freeze is what the third change fixed.

Win rate in the detector batch vs v69: before 49.8% of 1,196 (with ladder); after 49.6% of 1,024 (CI 46.6-52.7);
OOF 6,548 vs v69's 5,468.

## A/B (maps/osc-fix-10k vs variants/astraeus-088bf3f, --no-test-draft, 10,240 games each)

| commit | CAND win % | 95% CI | OOF CAND | OOF REF |
|---|---|---|---|---|
| 36da99bb | 49.7 | 48.7-50.6 | 66,234 (6,515 games) | 57,327 (6,225) |
| 1facb439 | 50.0 | 49.0-51.0 | 89,568 (7,464) | 57,814 (6,243) |
| 2a6966d9 | 50.3 | 49.3-51.2 | 69,433 (6,670) | 56,618 (6,237) |
| **d62d050** | **50.3** | **49.4-51.3** | 66,417 (6,673) | 56,223 (6,244) |

One suite only (osc-fix-10k), so there is no per-suite split. Summaries: `replays/ab/osc1-<commit>/summary.md`.

## Fuel

- `tools/fuel/bench.py`, d62d050 vs 088bf3f (16 ladder games; replays differ, as play changed): mean turn
  51,880 -> 52,828 (+1.8%), p50 +2.5%, p99 98,904 -> 101,589 (+2.7%), turns over 100k 820 -> 929.
- Out-of-fuel turns at 10k games: +18% (66.4k vs 56.2k), in 'decide' (49k vs 40k) and 'queue' (20k vs 16k).
  By family (2a6966d9): arena +1,092, the-pack +630, continent +622, shared-gems +530, topo-duel +496;
  dash-lattice -217.
- Metered (debug-only counter around every distance/within call) on gen-arena maps: 0.8-1.9M fuel per game
  for the whole team, at most ~8k in one turn. So the reach queries themselves are a small part of the rise;
  the rest is the changed play (fewer frozen champions, so more moving, routing and fighting turns).

## API for stream 2 (`model/enemy_reach.h`, namespace `aph::enemy_reach`)

- `far` (1<<14): no walk gets within act range.
- `Profile{act, dasher}`; `act_range(facts)`, `profile(facts)`, `widest(world)` (the widest profile of any enemy:
  for an unknown enemy on a live tile).
- `distance(world, profile|belief, from, p, limit)`: D(e,p) = max(dist, act + min S(q) over q within act of p),
  S = king steps over `blocked_for_them` (walkers) or `their_dash_walls()` (dashers). Exact if <= limit, else
  > limit. Chebyshev on open ground.
- `within(world, profile|belief, from, p, x)`: D <= x, one board test.
- `origin(belief)`: tp_dest when a teleport is pending, else pos. Use as `from`.
- `warm_up(world, fuel_floor)`: builds their_dash_walls early. It doesn't block.
- On Safety: `approach(e, p, horizon)` (turns until e can strike p; 0 = now), `walk_in(e, p, horizon)`
  (visible: approach; unseen: from its last tile), `may_reach_within(p, turns)` (visible by `within`, unseen by
  `possible`). `Pathing::fight_near(live)` is the travel-dash clearance on the same model.
- Boards are cached across turns per (origin, dasher) in 24 LRU slots, so callers need no cache of their own.

## Open issues

- `walk_allies_in` (joiners) is still Chebyshev: stream 2's.
- Our own chase (kill_turn, intercept_steps, preyable) is still straight-line. A shore can show a prey we cannot
  reach while it can't reach us: a possible new oscillation, not seen in the detector.
- Teleport crystals not yet started, knight-shaped dashes and dashes landing on dead camps aren't modelled.
- enemy_area / avoid boards for next-turn squares are still square dilations.
- The pack zone (guard ↔ want_home): stream 2.
- The dash clearance now counts only enemies seen within a round (age <= 1), as walk_in does; it was any live
  tile before. Stricter, so that a vision toggle can't flip it.
- The moated Prism's altar wait with a 1,000+ gem bag whose tribute is never safe: a bank-family issue.
- Fuel: +18% OOF turns. Most of it is changed play, not the queries.
