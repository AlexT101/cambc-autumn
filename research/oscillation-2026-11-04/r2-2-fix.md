# Round 2, fixer 2: every executed advance is asked, and a refusal never idles or sidesteps

Branch `osc/r2-2-every-advance` (worktree `/home/ubuntu/wt/osc-r2-2-every-advance`), base 8c0f3d49. Bot copies
`bots/variants/oscr22-*`.

## Plan

The work veto (`Pathing::set_veto`, armed by `guard_work`) asks `leaves_at(q)` of the tile a work step lands on.
Three things break "a step we take is one want_home will not undo":

1. **Moves it never sees.** The strike search's executed walk (plan.cc, `pathing.try_move` after
   `set_guard(nullptr)`) runs before `guard_work` arms the veto; the chase step (`chase`, fight.cc) runs under the
   strike guard with no veto.
2. **Refusals that idle.** `step_field` skips its search when `veto_reserve()` doesn't fit (static-descend); the
   descent's closer tiles are then refused and the turn stands still.
3. **Refusals that sidestep.** A refused tile joins the routing walls (`merged_guard`) and the route is searched
   again round it. The way round is longer than the way through: its first step is sideways, and the next turn
   (veto memo gone) walks back. This is the bank runaway on leaky-diagonals and the X / C2 churn.

Design (one model of what a refusal means: the tile is where want_home would send us back from, so the walk
neither goes there nor round it; it takes an equally short way if there is one, else holds):

- **Search's no-hit move asked once** (bot.cc `search_strikes`, plan.cc executor). Before the search, the work veto
  is armed over the step guard (`guard_work`'s veto, the step guard kept). The search plans as before (nothing is
  vetoed yet, so `guard()` is the step guard). The executor asks the veto of the end tile only, and only for a plan
  with no hit (no attack, spell or landing dash): a hit is never refused (a28721f3's lesson). A refused plan is
  replaced by the best plan from our own tile (no move), else none; the work then walks under the same veto.
  Not while holding a capture (no `guard_work` follows).
- **Chase step asked** (fight.cc `chase`, called with the work's veto from bot.cc and bank.cc). The step is
  vetoed unless a hit can follow it this turn (target visible, attack unspent, melee or a ready reset, and the
  target within range + 1). A refused chase falls through to the work, as an unreachable target does.
- **The veto's memo survives re-arming** (pathing): `drop_veto` no longer clears it; it is keyed by the veto
  function and `World::observations` (as before), cleared at `begin_turn`. So the search's ask, the chase's and
  the work's share one memo: no tile is asked twice in a turn from the same view.
- **A refusal is final, not walled** (pathing): routes are searched against the guard without the refused tiles
  (`route()`, and the cover no longer ORs them), so a route's first steps are the equally short ones; the refused
  ones fail by the memo. `step_route` / `step_towards_funded` no longer search again because a veto refused a step
  (only a hidden blocker re-plans). A walk whose every shortest first step is refused holds (`held_` set), and
  `step_field` then skips its wider search. Equally short alternatives are still taken.
- **Short-fuel walks search bounded** (pathing `step_field`): instead of skipping the search when
  `search_cost_estimate(cap) + end_reserve + veto_reserve()` doesn't fit, it searches with the cap the fuel above
  that reserve pays for, as `step_towards_funded` does, if that cap still reaches our field distance; only below
  it does static-descend stand. Bounded work, no new gate.

Callers affected: every walk under the work veto (farm, bank, siege/kite, contest, shop walk, walk_on), the chase
(decide and carry_bag), the strike search. Not touched: leaves_at, drawn_home, stand_lost_at, safety.*, guard.cc.

Fuel: one leaves_at per no-hit search move and per vetoed chase step (shared memo: no repeats); fewer re-searches
after refusals; bounded searches on short-fuel turns (within the reserves).

## What shipped on the branch (final tree = e718eaf8; head 6cbfb5c0)

The plan above was implemented in c951ce30 (v1), then revised in e718eaf8 (v2) after its numbers and the audit:

- **Kept from v1:**
  - The search's no-hit plan is asked once, of its end tile. A hit is never refused.
  - The chase step is asked unless a hit follows it.
  - The memo is shared across re-arming, keyed by the veto fn.
  - step_field's search is bounded by the fuel left, not skipped.
- **Dropped from v1: the blanket hold.**
  - In v1, a walk whose shortest first steps were all refused stood still. That raised stuck_fail by 47% on the detector and gained nothing overall (all -0.1%).
  - Refusals now wall the route and re-search round it, as on main.
- **Kept as an opt-in hold:** `Pathing::hold_refusals(true)`, with `held()` reporting it. Only the bag's altar walk uses it (`walk_to_altar`, bank.cc).
  - A held walk short of altar `at` waits for that altar the way carry_bag already waits at one it stands at.
  - It waits as many rounds as the walk to the nearest other unlocked altar takes, then avoids that altar for as long. `wait_for_altar` is shared with that path.
  - This is the bank runaway's fix: a step aside and back, instead of a re-target.
- **Audit fixes:**
  - route()'s one-step cover shortcut is skipped while holding.
  - know_failure uses the same guard as route().
  - A refused search plan falls back to the best plan that hits or stays, rather than only our own tile's plan.
  - A landing dash counts as a hit only where it lands on someone.
  - There is no ask once a plan is under way (done > 0), so a plan is never stranded on a tile it only passed.
  - throw_if_stale runs right after the ask.
- **Tried and reverted (fb959efd, reverted in 6cbfb5c0):** the chase holding on refusal. Detector all went from -4.3% to -1.2%, and fuel did not move.

## Auditor (read-only, on c951ce30) and responses

1. **Cover shortcut keeps a refused step.** Fixed: skipped while holding. Without a hold, the cover again ORs the vetoed tiles, as on main.
2. **Stranded mid-plan.** Fixed: the ask is skipped when done > 0.
3. **Fallback too coarse.** Fixed: it takes the best hitting or staying plan.
4. **Landing dash that hits nobody.** Fixed: checked against land_hits.
5. **know_failure guard mismatch.** Fixed.
6. **Memo kept after the work's camp hits.** Not fixed. It is low severity, and forget_vetoes after the search covers our own strikes.
7. **Unconditional throw_if_stale.** Fixed.
8. **Missed callers that still sidestep.** By design in v2: re-searching round refusals is main's behaviour. v1 showed that holding everywhere idles.
9. **Chase asks up to 8 first steps.** This turned out to be the fuel cost; see below.

## Results (A/B: 10,240 games, maps/osc-r2-10k, vs variants/astraeus-8c0f3d4, --no-test-draft)

| variant | win % (CI) | out-of-fuel turns, CAND vs REF | detector all vs round2-v69 (CI) |
|---|---|---|---|
| v1 c951ce3 (blanket hold) | 50.0 (49.1-51.0) | 156,346 vs 155,795 (+0.4%) | -0.1% (-3.4 to +3.3); stuck_fail +47% |
| no-hold (v1 minus the hold) | 50.7 (49.7-51.6) | 173,454 vs 157,144 (+10.4%) | -4.0% (-7.0 to -1.3) |
| **v2 e718eaf (final)** | **50.0 (49.0-50.9)** | **172,286 vs 158,556 (+8.7%)** | **-4.3% (-7.2 to -1.5)** |
| v2 without the bounded search | 50.3 (49.3-51.3) | 170,695 vs 158,027 (+8.0%) | — |
| v2 without the chase ask | 49.6 (48.6-50.6) | 156,917 vs 156,582 (+0.2%) | +0.7% (-2.5 to +3.9) |
| v2 without the search ask | 50.2 (49.2-51.2) | 167,375 vs 159,206 (+5.1%) | — |
| v3 fb959ef (chase holds) | 50.0 (49.0-50.9) | 171,519 vs 156,362 (+9.7%) | -1.2% (-4.3 to +1.7) |

v2's detector, kind by kind, against round2-v69:

| kind | change |
|---|---|
| retreatchurn | -8.7% |
| branchflip | -7.2% |
| goalflip | -2.8% |
| pingpong | -12.0% |
| jitter | -17.8% |
| wander | -2.2% |
| stuck_idle | -1.8% |
| stuck_fail | +12.4% |
| out-of-fuel turns | +9.2% |

The detector gain comes almost entirely from the chase ask: without it the total is +0.7%. That ask is also the fuel cost: +8.5 points of out-of-fuel turns, because it asks up to 8 first steps at 2-16k fuel each, with only one ask reserved.

Step-then-leave census (1,708 detector games): base 105.7k, v2 97.8k (-7.5%).

| advance led by | base | v2 |
|---|---|---|
| chase (`C//srch/r`) | 11.8k | 6.5k |
| search no-hit move (`F//srch/m`) | 5.8k | 4.4k |

Veto turns rose from 44.3k to 57.2k, because more moves are asked. Idle veto turns rose from 14.7k to 19.2k.

Static-descend idle turns were 14.5k on the base and 15.7k on v2. The bounded search did not reduce them. Most are frontier holds whose descent is refused, and a search would only add a sidestep. The ablation that drops the bounded search reads the same, within noise.

Episodes. These are reruns of the original games with the v2 trace. They diverge from the original by about round 22, so they are indicative only.

| example | base | v2 |
|---|---|---|
| leaky-diagonals h4 bank runaway | 873 turns, half out of fuel | gone: 237 B turns, 9 out-of-fuel turns, no position repeated more than 3 times |
| wild h3 | flips 440 times (41,20)↔(41,19) | gone: most-repeated move 6 |
| gem-drought h0, arena h6 | — | chase asks (44 and 126 turns) and search refusals (16 on arena); no long flip found |

## Open

- The chase ask's fuel: +8.7% out-of-fuel turns over 8c0f3d4.
  - A per-ask fuel check, or one reserved ask per first step, in step_route under the chase would bound it.
  - So would a cheaper leaves_at, which is fixer 1's area.
  - Without the fuel fix, v2 is a wash on win rate: 50.0%.
- stuck_fail is up 12%: refusals on walks with no fallback (bitboard step_towards in capture or siege).
- The static-descend idles are not reduced. They look like correct holds, not a fuel artefact.
- The memo is kept after the work's own camp hits (audit point 6).
