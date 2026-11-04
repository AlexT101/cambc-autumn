# Stream 2: guard ↔ want_home consistency (fix notes)

Branch `osc/2-consistency` (worktree `/home/ubuntu/wt/osc-2-consistency`), on top of stream 1 (d62d050e). A/B
reference: stream 1's build, `variants/osc1-d62d050`.

## Plan

### Confirmed mechanisms (source at d62d050e)

- **Two models of one question.** want_home (combat/fight.cc) leaves a tile when its recall line is above our
  health, it is in a pack's zone, or `stand(p, pursued ? 2 : 0, ..., joined = 2)` is lost; `pursued` reads
  `own_ground(p)`, our health and bag. The work guard (combat/guard.cc) approximates that for the tiles beside us
  by `step_guard` (fight_key fights: enemies whose blow hits q, no walkers, no joiners), `keep_out` (pack zone and
  recall line, neighbours only) and leaves out the stand's pursuers and joiners on purpose (EXPERIMENTS "Hold
  rule and the work guard": a stand per tile cost x2.3 out-of-fuel turns). So a work step lands on tiles want_home
  leaves next turn: lost to walkers (A §2), to joiners (A §3 end), across the own-ground line (A §6).
- **Turn-order parity** (A §3): `threat_strike` and `Reach::build(twice)` widen to two turns when
  `turns_before_ours >= 2`. With teams alternating who starts a round, a pair at the same rank sees 2, 0, 2, 0
  enemy turns before our next: the guard prices q in a 0-round with the one-turn reach, want_home prices it from
  q in the next (2-turn) round.
- **Vision** (A §5): stand counts visible enemies only; stepping out of sight drops the enemy, stepping back
  shows it again.
- **Mutual dance** (A §1): every test reads where enemies stand now; an enemy that steps in on its turn was never
  priced by the guard. No same-world check removes this (EXPERIMENTS: half of the step-then-leave turns).

### The model: one verdict, priced where the step lands, with the reach both rounds use

1. **Window**: a reach is judged over `window_turns(e)`: the enemy's turns before our next, or, when it has none
   (it acted before us this round and acts after us next round), the next window's. That is what we face
   wherever we stand next turn, so a tile reads alike in both rounds and no consumer alternates. Used by
   `threat_strike` and the Reach build (so every Safety consumer: guard, want_home, retreat_step, avoid,
   lethal). Pairs whose window is 1 every round are unchanged.
2. **One verdict** `leaves_at(p)` in fight.cc: the recall line at p, p's pack zone, and the stand at p with
   `pursued` read at p (own ground, health, bag), all behind p's hold. want_home is `leaves_at(here)` plus the
   camp tests (trapped, fled) and Willow's. The work guard (bank, shop, contest, siege, farm) asks
   `leaves_at(q)` of the tile a work step or dash is about to land on: a **lazy veto** in Pathing (try_move,
   an unguarded route's first step, a travel dash's landing). A vetoed tile joins the guard for the rest of
   the turn and the route is searched again around it. One stand per step taken, not per tile beside us;
   stand's walker fights are memoised by (key, arrivals) so repeats are free.
3. **Joiners on terrain**: `walk_allies_in` (our allies joining a fight) by the terrain distance (stream 1's
   model) instead of Chebyshev.
4. **Believed positions**: stand counts an enemy seen last round (out of sight now) as a walker from its last
   tile (walk_in, as recall_outruns and paying_soon already do), and want_home's early return counts it too:
   both the verdict at our tile and the veto at the next read the same enemies.
5. **Enemy motion** (dance; later, measured separately): the veto prices q as next turn will if enemies close
   in.

Out of scope here: farm.cc/pathing routes/make_way/capture.cc (stream 3), siege.cc (stream 4). The Pathing veto
hook is a few lines in try_move/step_route/take.

### Fuel

Window: free (memoised strikes). Veto: one `leaves_at` per attempted work step with an enemy seen: a
fight simulation at most (~5-15k) plus the recall line and pack tests; none when no enemy is seen or lethal.

Points 1 and 3 were built, measured and reverted (below); 5 was not built.

## Changes (commit e509b4e3 on osc/2-consistency)

- **leaves_at(p)** (combat/fight.cc, bot_parts.h) is want_home's verdict at p, camps aside. It is drawn_home
  (p's recall line, unless finishing a camp at p or a hold at p keeps us; p's pack zone) or stand_lost_at.
  stand_lost_at:
  - reads lethal(p) and `pursued` at p (own ground, health, bag);
  - counts a hold we would start at p as under way, since next turn it is;
  - runs `stand` with p's pursuit horizon.

  want_home is spawn → drawn_home → mono/camp trapped → camp_fled → Willow → stand_lost_at, the same order as
  before, through the same helpers.
- **Work veto** (Pathing::set_veto, combat/guard.cc work_veto).
  - guard_work arms it after deferring the work guard. try_move, an unguarded route's first step and a travel
    dash's landing ask `leaves_at(tile)`.
  - A refused tile joins the guard: guard() is the merged board, and route()'s cover also holds the vetoed
    tiles. The route is then searched again (step_route/step_towards_funded: only when a step was vetoed).
  - Verdicts are memoised per tile while World::observations stays.
  - The veto is dropped at turn start (Pathing::begin_turn) and by set_guard/defer_guard.
  - It is skipped on homeward steps (step_safely to the ally spawn), and while our own tile already leaves:
    want_home kept us (stays_here), or else leaves_at(here).
  - Willow has no work guard, so it has no veto.
- **Stand in two parts** (Safety::stand_roster, stand_trade, no_worse).
  - Stands with walkers on a fight already on go through fight_of's memo with the walkers late.
  - stand_lost_at keeps the rosters it read this observation (8). A roster no worse than one that held,
    holds; one no better than one lost, is lost.
- **Believed enemies.** Stand counts an enemy seen last round, out of sight now, as a walker from its last tile
  (walk_in). want_home's "nobody in sight" early return counts it too (enemy_believed).
- finishing_camp(world, p).

### Measured and reverted

Each row is 10,240 games on osc-fix-10k vs `variants/osc1-d62d050`.

| variant | CAND win % | 95% CI | OOF CAND | OOF REF |
|---|---|---|---|---|
| everything, first cut (4af7007e) | 48.8 | 47.8-49.7 | 284,506 | 68,250 |
| ... with the veto off | 48.2 | 47.3-49.2 | 92,019 | 69,514 |
| ... with the window off | 49.1 | 48.2-50.1 | 261,166 | 67,602 |
| ... with believed enemies off | 48.8 | 47.8-49.7 | 269,853 | 67,564 |
| ... with terrain joiners off | 49.3 | 48.4-50.3 | 232,758 | 67,218 |
| everything + audit fixes + memos (wip2) | 48.9 | 47.9-49.9 | 361,140 | 67,125 |
| wip2, veto/window/believed/joiners off (refactor only) | 49.7 | 48.8-50.7 | 69,730 | 66,874 |
| wip2, veto only (window/believed/joiners off) | 49.5 | 48.6-50.5 | 263,231 | 67,492 |
| **wip2, window and joiners off = e509b4e3** | **50.3** | **49.3-51.2** | **207,844** | **66,413** |

- **Window** (`window_turns`): when an enemy has no turn before our next, threat_strike and the Reach use the
  next window's 2 turns.
  - It removes the 2,0,2,0 alternation for same-rank pairs. It took retreatchurn to 268k, against 299k
    without it (detector, below).
  - But it makes every Safety consumer as pessimistic in 0-rounds as in 2-rounds: the strike search's end
    tiles, lethal, hold_outlasts, retreat avoid. Across the ablations it cost about 0.3-0.8 points.
  - A sound fix prices only "where must I be at my next turn" by W(t+1): the veto and guard, not the strike
    search. Safety holds one reach model per turn, so this needs a second Reach per enemy. Not done.
- **Terrain joiners** (walk_allies_in by enemy_reach::distance). It used the enemy's terrain and no dash for an
  ally's approach, which errs late, so stands read lost more often. Cost about 0.5. Doing it properly needs
  the ally's own movement profile.

## Auditor (read-only, on 4af7007e) and responses

- **HIGH: the veto survives an abandoned turn** (begin_turn didn't drop it, and guard_safety_ dangled).
  Fixed: begin_turn calls drop_veto().
- **Fuel: passed tiles weren't cached, and a refusal turned off route()'s cover shortcut.** Fixed:
  - a cleared board beside the vetoed one, both per observation;
  - the cover ORs the vetoed tiles, so the shortcut stays.
- **leaves_at(q) ≠ next turn's want_home.** Responses:
  - finishing_camp read at our tile: fixed (finishing_camp(world, p)).
  - A hold not yet started at q read as not paying: fixed. hold_rounds' one-round difference is left (it errs
    cautious).
  - Age-1 enemies drop next turn, and believed walkers adjacent to q are pruned with approach 0: left, both
    cautious or rare.
  - camp_trapped/camp_fled/Willow missing from leaves_at: left. Open, below.
- **Window too pessimistic in 0-rounds:** confirmed by A/B, reverted.
- **The veto only stalls homeward and after the strike search moved us onto a leaving tile.** Fixed: no veto on
  step_safely to the ally spawn, nor while our tile already leaves.
- **Low:**
  - restore_guard's comment: fixed.
  - label_through's memo keyed on guard_: wasted step only, left.
  - take() walk-first asks the veto of the transit tile: left.
- **Coverage:** join_marcella_capture, yield_capture and take_capture_handoff move before guard_work
  (capture.cc, stream 3's file): left.
- **Stand memo path equals the direct trade:** confirmed. `walking &= ~(key >> 16)` is more pessimistic in a
  way that is wanted.

## Episodes

- **the-line** (A §1/§2, `070-00the-line-21`, h7 Prism r477-1939). Before, F↔R ping-pong (23,24)↔(22,23), 730
  turns each. Rerun with the candidate (scratchpad ep2): h7 holds a capture at (16,16) for 1,286 of 1,479
  lines, and has 12 R lines. The game diverges early, so this shows the cycle is gone, not a like-for-like
  replay.
- **Retreat churn per champion, same games** (detector, osc1-d62d → e509b4e3; longest episode in parentheses):

  | game, champion | osc1-d62d | e509b4e3 |
  |---|---|---|
  | gen-arena-600202601-21 h9 Marcella | 1,258 (361) | 660 (116) |
  | mut-vault-600101805-12 h0 Cassi | 1,230 | 513 |
  | gen-arena-600202600-21 h8 Marcella | 1,018 | 459 |
  | gen-monolith-only-600201508-12 h2 Issac | 981 | 146 |
  | gen-arena-600102601-12 h0 Ryth | 890 | 255 |
  | gen-moated-altars-600208104-12 h1 Cassi | 861 | 239 |
  | gen-arena-600202601-21 h10 Willow | 988 | 964 (no veto) |

## Detector

Turns in episodes; 1,024 games vs baselines/v69 on gen and fresh. `osc2-n` is the refactor only;
`osc2-w` adds the veto, window, believed enemies and joiners.

| kind | before-v69 | osc1-d62d | osc2-n | osc2-w | **e509b4e3** |
|---|---|---|---|---|---|
| retreatchurn | 442,919 | 420,277 | 417,491 | 268,390 | **298,679** (-29%) |
| claimflip | 410,005 | 406,136 | 415,639 | 397,362 | 400,903 |
| goalflip | 251,809 | 243,892 | 247,991 | 204,888 | 211,397 |
| branchflip | 178,457 | 171,895 | 172,830 | 124,293 | 132,293 |
| stuck_idle | 79,162 | 62,129 | 58,323 | 53,396 | 53,883 |
| wander | 60,482 | 52,332 | 51,060 | 43,177 | 46,845 |
| stuck_fail | 58,375 | 42,778 | 39,886 | 33,201 | 30,822 |
| pingpong | 38,584 | 36,852 | 39,260 | 34,268 | 34,571 |
| jitter | 34,225 | 32,335 | 34,402 | 30,046 | 30,424 |
| preyflip | 4,070 | 3,660 | 3,966 | 3,975 | 3,960 |
| **total** | 1,558,088 | 1,472,286 | 1,480,848 | 1,192,996 | **1,243,777** (-15.5%) |
| home:standlost | 178,239 | 161,515 | 160,456 | 104,559 | 111,984 |
| home:selffalls | 14,942 | 13,991 | 15,059 | 6,119 | 6,979 |
| home:outmatched | 37,164 | 36,248 | 35,097 | 25,654 | 29,441 |
| home:low | 49,286 | 44,219 | 42,964 | 29,790 | 30,949 |
| home:willow | 10,937 | 10,058 | 11,287 | 9,776 | 9,476 |

Detector A/B (trace build vs v69): 52.1% (49.1-55.2), OOF 21,014 vs 5,249.

## A/B and fuel

- **e509b4e3 vs osc1-d62d050**, osc-fix-10k, 10,240 games: **50.3%** (49.3-51.2). It does not lose.
  - OOF turns: 207,844 vs 66,413 (×3.1).
  - Its replays match `variants/osc2-c1`'s byte for byte.
- **bench.py** (default maps vs osc1-d62d050), play turns after round 1:
  - mean fuel 50,822 → 53,070 (+4.4%);
  - turns over 100k: 1.53% → 2.27%.
- **Census (OOF-heavy maps):**
  - The veto runs on about 45% of heavy turns. It costs about 16k there, about 1.2 leaves_at a turn.
  - One leaves_at is about: roster 3k, lethal 2.4k, recall line and pack zone 1.4k, and a fight simulation
    6-12k when walkers make the roster new.
  - The roster memo seldom fires: each landing tile's roster is new.
  - The cost is the one stand per step that A §2 fix (a) predicted. No fuel gate was added.

## Open

- **Fuel:** ×3 out-of-fuel turns. What remains is the stand simulation itself (Safety::trade) and lethal(p)
  per landing. Making trade cheaper would serve want_home too.
- **Turn-order parity:** reverted. The fix that fits is a next-window reach for the veto and guard only (a
  second Reach per enemy).
- **Joiners on terrain:** reverted. It needs the ally's own profile (dash included).
- **Willow:** no work guard, so no veto. Its churn is unchanged (support.cc stations guard; leaves_at lacks
  the Willow test).
- **leaves_at has no camp_trapped/camp_fled parts:** those flips stay.
- **Mutual dance** (enemy motion toward q): not built.
- **Capture moves before guard_work** (capture.cc, stream 3): unvetoed.
- **Not started:** C3/C5/C8/C9 (preyable flips, chain vs bank, the strike search's no-hit move, lost_prey),
  bag carriers above brake_bag, and moving the chase models onto the reach model.
