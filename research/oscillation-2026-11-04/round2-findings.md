# Oscillation hunt, round 2: findings (main 8c0f3d49, 2026-11-04)

What remains after round 1's fixes (CHANGES 337) and fuel campaign 6 (CHANGES 338-357), why it remains, and two
fixer workstreams.

## Method and data

- **Trace build.** `bots/variants/osc2r-trace` is astraeus 8c0f3d49 plus fuel-campaign-6's `trace.patch`, with
  `test_draft` off. It played v69, v68 and v66, each side on its own draft (`--no-test-draft`), on ladder (172),
  `maps/gen` (512), `fresh-gen-s1` (512) and a new suite `maps/fresh-4104` (seed 4104, 256 maps, 512 games). That
  is 1708 games per baseline.
  - Batches: `replays/batch-20261104-1225{23,06,11}-ab-osc2r-v6{9,8,6}-*`.
  - Logs: `replays/osc2r-v6x.log`.
- **Detector.** Every game ran through `osc_detect --bridge-oof`.
  - Output: `replays/osc/round2` (all 5124 games) and `round2-v6x` (per baseline).
  - Round 1's batches were re-run bridged so the two rounds compare like for like: `replays/osc/round1-v6x-bridged`
    and `osc-int-bridged` (d6e74b6f, 1024 games).
- **Debug build.** `bots/variants/osc2r-dbg` is the trace build with three extra prints:
  - `SL`: stand_lost_at's inputs per enemy (reach R, terrain distance d, walk w, turns before ours t).
  - `LA`: leaves_at's verdict.
  - `VT`: work_veto's verdict.
  - It replayed 240 games: the 100 heaviest A1/A2 games plus 140 random ones (`sample2.txt`).
  - The debug runs drift from the originals, because a debug block's fuel goes into `veto_cost_` and so into the
    reserves. They are analysed as games in their own right; they are deterministic and can be re-run.
  - Kept in `replays/osc/round2-examples/`: the example replays, a debug rerun of mega-groups (`dbg-mega1`), and the
    analysis scripts:
    - `group2.py`, `sum2.py`, `drill.py`: groups and wasted turns.
    - `stl.py`: step-then-leave census.
    - `why_stl4.py`: cause per event.
    - `sc.py`: shortcut and idle census.
    - `show.py`: print the D/SL/LA/VT lines around a round. It expects a `samp/<name>/` layout.
- **Wasted turn.** A turn inside a detector episode is wasted if it does not hit or cast and either:
  - undoes the last move (ends where it ended two turns ago, after moving away), or
  - stands idle in a move branch.

  Every episode turn gets exactly one group, using round 1's groups (FINDINGS-A/B/C) in priority order.

## Before/after: the detector (bridged, osc_compare, 1196 common games per baseline)

| kind | vs v69 | vs v68 | vs v66 |
|---|---|---|---|
| all episodes | **-10.9%** (CI -14.4 to -7.1) | -8.3% | -12.5% |
| stuck_idle | -54% | -58% | -45% |
| stuck_fail | -58% | -59% | -53% |
| pingpong | -40% | -35% | -38% |
| jitter | -39% | -37% | -40% |
| retreatchurn | -12% | -9% | -19% |
| branchflip | -15% | -12% | -20% |
| claimflip | +9% | +12% | +11% |
| out-of-fuel turns | +181% | +194% | +161% |

- **337's headline is smaller than it looked.** Unbridged, 337 read -22%. Bridged, round 1 → 337 → main reads
  -12.2% → -10.5% on the 1024 gen + gen-s1 games. Most of the unbridged figure was out-of-fuel turns splitting
  episodes.
- **The fuel campaign held level overall,** but stuck_fail rose from 20.8k (337) to 24.1k (main).
- **Out-of-fuel turns are still about 2.7x round 1's.**

### Win rates of the trace build

Own drafts, 1708 games each.

| baseline | win rate | 95% CI | OOF turns (ours) | OOF turns (theirs) |
|---|---|---|---|---|
| v69 | 52.2% | 49.9-54.6 | 28.0k | 10.0k |
| v68 | 51.9% | 49.5-54.2 | 28.8k | 8.4k |
| v66 | 73.2% | 71.0-75.2 | 18.2k | 7.9k |

### Wasted turns by group

3588 games common to both rounds. Group letters as in round 1.

| group | what | r1 | r2 | change |
|---|---|---|---|---|
| A1 | stand lost: retreat churn | 196k | 156k | -20% |
| A2 | pack zone (`outmatched`) | 20k | 19k | -5% |
| A3 | low / camp-trap / fled | 25k | 20k | -20% |
| A4 | Willow | 10.7k | 12k | +12% |
| B1 | fight stuck failing | 120k | 39k | **-68%** |
| B2 | bank stuck | 25k | 10k | -60% |
| B3 | farm idle | 110k | 90k | -18% |
| B4 | G (gather) stuck | 86k | 20k | **-77%** |
| C1 | F jitter | 28k | 33k | +18% |
| C2 | bank/walk churn | 29k | 31k | +7% |
| C3 | claim flips | 76k | 85k | +12% |
| C4 | prey flips | 30k | 33k | +10% |
| X | contest with veto (new) | 29 | 1.3k | new |
| **all** | | **764k** | **555k** | **-27%** |

All 5124 round-2 games: 764k wasted turns.

| group | wasted turns |
|---|---|
| A1 | 220k |
| C3 | 123k |
| B3 | 105k |
| B1 | 51k |
| C4 | 46k |
| C2 | 46k |
| C1 | 46k |
| B4 | 30k |
| A3 | 29k |
| A2 | 27k |
| B2 | 17k |
| A4 | 16.5k |

**A1 is now the largest group by far, and A1+A2 come from one mechanism (below).**

### False positives, and what was set aside

- Ranged champions attacking from the same tile and casts are counted as busy, not wasted.
- Respawn waits and other short waits: W-branch turns are counted only inside stuck episodes.
- B3 holds two kinds of turn that are not plausibly fixable as oscillation:
  - **Structural.** On topo-island-600206600 (~19k turns in both rounds), champions sit on spawn islands joined
    by hole bridges while the groups they could farm respawn or cannot be reached.
  - **Late game.** 29k of B3's 74k no-claim turns come at round 1850 or later.
- Capture→recall sequences and pending winning tributes fall under X and A3 and are small: X is 1.3k, A3 is
  mostly hp:low.

## Sub-issue 1: the veto and the stand judge q for the wrong round (A1, A2; most of the remaining waste)

**The pattern.** On a non-R turn the champion steps from p to q. On its next turn, standing on q, want_home says
leave (`home:standlost` or `home:outmatched`) and it retreats to p. Often the next turn advances to q again.

**How often it happens.**
- 212k step-then-leave events in round 2's 3588 common games, down from 251k in round 1.
- Full 2-cycles (p → q → p → q) fell from 34k to 16.9k.
- Parity over all 5124 games: ~170k events leave in a "wide" round against ~130k in a narrow one. Among F-branch
  cycles the split is 10.8k wide to 4.6k narrow.

**What decided each event.** The debug sample, classified by which enemy flipped the verdict between the veto's
read at t and want_home's at t+1 (`why_stl4.py`):

| cause | random 140 games: events | random: cycles | heaviest 100: events | heaviest: cycles |
|---|---|---|---|---|
| window / reach changed (turn order) | 11.4% | **27.8%** | 10.2% | **33.4%** |
| enemy moved (one step closer) | 20.0% | 23.0% | 16.2% | 23.6% |
| pack zone (`home:outmatched`) | 13.6% | 13.2% | 16.1% | 10.1% |
| vision / new enemy | 5.8% | 7.6% | 4.3% | 3.2% |
| strike-search move, never asked | 16.8% | 8.3% | 18.3% | 10.2% |
| chase step, never asked | 12.0% | 7.6% | 14.1% | 6.4% |
| Willow (no veto at all) | 3.8% | 6.0% | 10.5% | 8.6% |
| home:low / camptrap | 7.9% | 0.4% | 4.6% | 0.2% |
| asked, but no SL logged (memo or early return) | 4.8% | 2.8% | 1.3% | 0.8% |

The random sample has 7203 events and 570 cycles; the heaviest-100 sample has 32.9k events and 4.2k cycles.

### Mechanism

The work veto, `work_veto` (combat/guard.cc:722), is armed by `guard_work` (guard.cc:785) and asks
`leaves_at(q)` (combat/fight.cc:468). leaves_at is `drawn_home || stand_lost_at`:

- `drawn_home` (fight.cc:422) includes the pack-zone test `in_pack_zone` (guard.cc:166).
- `stand_lost_at` (fight.cc:433) runs the stand: `stand_reach` (model/safety.cc:2798) and `trade`
  (safety.cc:2870).

All of these price q **with this turn's turn-order window and the enemies where they stand now**. Next turn,
want_home (fight.cc:478) prices the same q again, this time with that round's window and the enemies after their
moves. The two reads disagree in a fixed direction, three ways:

1. **Window (turn-order parity).**
   - `turns_before_ours` (safety.cc:949) gives an enemy 2 turns before our next one when our team starts the
     round (team A on odd rounds, team B on even), and 0-1 otherwise. `threat_strike` (safety.cc:993) widens that
     enemy's reach when it has 2 turns.
   - The veto runs in round t but is answering a question about round t+1, and t+1 has the other parity.
   - So in a narrow round the veto passes a q that the next, wide round finds lost. The champion steps in, steps
     out, and repeats every two rounds, even with **stationary enemies**.
   - Example: mega-groups-410408202-12 vs v66, team A, h0, 500 hp, rounds 405-445, cycling between (54,5) and
     (55,5).
     - Round 406 (even, narrow): the veto prices (55,5) with e2 at (62,6) and e3 at (61,6): R4, t1, w3/w2, walk
       mask 0x8. Not lost; the step is taken.
     - Round 407 (odd, wide): want_home at (55,5) sees R5, t2, w2/w1, walk mask 0xc. Lost; it retreats to (54,5).
     - Neither enemy moved. Debug rerun: `round2-examples/dbg-mega1`.
   - Example: 00the-line-2 vs v68, team B, h5, rounds 437-439. A stationary e0 at (8,16) reads R5 d6 w1 t1 at
     q=(13,22) in the odd round, then R6 w0 t2 in the even one. The `hit` flag goes on and the trade is lost. The
     same happens to h6 at q=(2,19) in rounds 1531-1535, again with e0 not moving (R5 w1 t0 → R6 w0 t2).
2. **Horizon cliff (enemies one step closer).**
   - The stand counts as walkers only enemies whose walk is at most `pursuit_steps` (= 2, params.h:128). Its
     `approach` (safety.cc:2241) is measured from the enemy's position now.
   - An enemy at w3 that takes one step before our next turn becomes a w2 walker. An enemy at w1 becomes a w0
     hitter, which flips the trade's first-strike semantics ("with nobody in reach yet, we strike first").
   - Example: leaky-diagonals-600207807-1 vs v68, team A, h4, banking 131 gems, rounds 594-597.
     - At (46,43), round 594: walk mask 0x15 (e0, e2, e4). Not lost.
     - Next turn: e3 moved from (52,50) to (51,49), so its walk fell 3 → 2 and it joined the walkers (mask 0x1d).
       e4's window also went t0 → t2. Lost; it goes back to (45,42). This repeats every two rounds.
3. **Pack zone.**
   - `in_pack_zone` (guard.cc:166) tests `dist(q, e.pos) <= pack_radius` (guard.cc:51) using current positions,
     with no window.
   - Example: gen-classic-410400004-2 vs v66, h8, round 223. The veto passes (15,63) with drawn0 and leaves0
     (e1 at (10,63), e5 at (15,57)). In round 224, `home:outmatched` sends it back to (16,64). Round 225 steps
     in again.

Vision changes make up the rest (5-8%): an enemy that is believed but not visible from p, and is visible from q.

### Confidence

**High** that the cause is one model judging one tile for two different rounds:
- The parity skew and the stationary-enemy cycles are reproduced in debug runs, with numbers.
- Window plus walk-in plus pack zone explains 45% of events and 64% of cycles in the random sample, and 56% of
  cycles in the heaviest games.

## Sub-issue 2: moves the veto never sees, and refusals that become idle turns

1. **The strike search's executed move.**
   - The move is `pathing.try_move(a.tile, &refused)` at combat/plan.cc:2214. It runs before `guard_work` arms the
     veto, so `vetoed()` (pathing.cc:1154) has no `veto_fn_` and passes everything.
   - These are 17-18% of events. Example: gen-gem-drought-600105820-1 vs v69, h0, rounds 1434-1437.
     - In the F branch, `srch:nohit` moves from (22,16) to (21,16) with no LA logged.
     - Next turn, at (21,16), e3 at (16,18) reads R5 d5 w0 t2. Lost; back to (22,16). The cycle has period 2.
   - Even if asked in round 1434 (narrow), the veto would probably have passed it (t1, R4). This class pays off
     only together with sub-issue 1.
2. **The chase step.**
   - prey/chase moves with `pathing.step_towards(goals, zone, ...)` (fight.cc:825). That is unguarded, and no
     veto is armed in branch C.
   - These are 12-14% of events. Example: gen-arena-410402606-2 vs v69, h6 at 280 hp, round 535. The chase goes
     from (19,9) to (18,10). In round 536, e1 and e2 step in (e2: R5 t2 w1), the stand is lost, and it goes back.
3. **Static-descend turns that stand still** (new since CHANGES 348).
   - In 1196 v69 games, `static-descend` fired 12.4k times, 80% of them on idle turns (9.9k). In round 1 it fired
     1.9k times, 43% idle (0.8k).
   - CHANGES 348 made `step_field` (model/pathing.cc:1764) keep back `veto_reserve()`, the veto's dearest recent
     ask, before its search. When the fuel is short it skips the search and falls back to `descend_with`. The
     closer neighbours are then mostly refused by the veto. In a 300-game sample, 2178 of ~3.4k idle shortcut
     turns are F `d-` with a veto.
   - This is the "fuel reserve turned into an idle turn" pattern the brief asked about.
   - Other shortcut fires grew too, idle share in brackets:

     | shortcut | round 1 | round 2 |
     |---|---|---|
     | turn-order | 14.5k (5% idle) | 32.5k (14% idle) |
     | prey-cut-short | 14.5k (12%) | 24.9k (19%) |
     | step-guard-entry | 3.96k idle | 7.24k idle |
4. **A vetoed goal becomes a sidestep.**
   - When the veto refuses the bank's tile or the tiles in front of it, the route goes around the refused tiles,
     and that sideways step undoes itself next turn.
   - wild-410406240-21 vs v66, h3, 35 gems: (41,20)↔(41,19), with a veto every turn.
   - 267-gen-leaky-diagonals-600207807-12 vs v68, h4, 2500 hp, 131 gems. 873 of its turns are B, alternating
     (46,42)↔(45,42) for hundreds of rounds, every other turn out of fuel (`r-d-r-r+` with `veto`). This is the
     runaway in fuel-campaign-6's NOTES; it is this game's top champion (A1/C2).
   - The X group (contest with veto, 1.3k) and the 27k veto-still F turns inside episodes belong to the same family.

**Confidence.**
- Medium-high for points 1-2: these moves are never asked, by construction.
- High for point 3: the counts and the code path agree, and CHANGES 348 itself recorded static-descend going from
  74k to 134k.
- Medium for point 4: two clear examples; the overall count is unclear.

## Other groups (not chosen this round)

- **C3, claim flips** (123k, up 12%). 54k of these turns are failing walks during flips (`r-r-d-`).
  - Top: topo-backdoor-410406720, a corridor jam with G/F stalls; atoll-600201900.
  - Round 1's claim-hysteresis direction still applies; it is outside the stand model.
- **B3, farm idle** (105k).
  - New: shared-gems 126 → 8k turns. 312-gen-shared-gems-600201600-21 vs v66, h9, idles at spawn (4,63) from round
    169 with claim −1: the kite plan has no station and farm prices nothing.
  - 02the-pack-12 went from 0 to 2076 turns.
  - Structural: topo-island (19k).
- **A4, Willow** (16.5k, up 12%). `guard_work` skips Willow (guard.cc:786), and want_home's Willow test
  (fight.cc:492) is not in leaves_at, so Willow has no veto. Willow is 10.5% of events in the heaviest games.

## Two workstreams (ranked by expected value)

### W1: leaves_at judges q for the round we arrive

**Highest expected value.**

**Scope.**
- combat/fight.cc: `leaves_at`, `stand_lost_at`, `drawn_home`.
- model/safety.{h,cc}: `turns_before_ours`, `threat_strike`, `stand_reach`, `approach`, `trade`, as needed.
- combat/guard.cc: `in_pack_zone` / `pack_members_of`, `work_veto`, `keep_out`.

**What to build.** When pricing a tile we would *arrive* on (the veto, and the work guard's keep-out), use the model
want_home will use next turn, and the same model in both places:
- The next round's window per enemy (`turns_before_ours` for round+1, with `threat_strike` widened to match).
- Each enemy advanced by the turns it gets before our next one. Concretely: its approach/walk reduced by those
  turns, so a w3 enemy with one turn left counts as a walker, and a w1 enemy counts as a hitter.
- Pack-zone members advanced the same way.

Two further pieces:
- Make want_home's read of "here" agree with what the veto said: one function, two calls, not two models.
- Optional: put Willow's leave test into leaves_at and give Willow the veto.

Per FIX-BRIEF, this is a monotonic decision by aligning the models, with no memory or hysteresis. The cost is
moderate: per ask, one more window lookup and a shifted walk.

**Must fix.**
- mega-groups-410408202-12 vs v66 h0 (rounds 405-445, (54,5)↔(55,5)).
- 00the-line-2 vs v68 h5 (rounds 437-439) and h6 (rounds 1531-1535).
- leaky-diagonals-600207807-1 vs v68 h4 (rounds 594-600).
- gen-classic-410400004-2 vs v66 h8 (rounds 223-225).

**Expected saving.** Window, walk-in and pack zone are ~45% of step-then-leave events and ~64% of cycles. That is
~95k of 212k events, and roughly 40-50% of A1+A2's 247k wasted turns (5124 games), i.e. ~100k turns.

**Risks.**
- Pricing for the wide round everywhere makes champions more conservative: more stalls in front of the frontier,
  fewer contested altars.
- Stream 2's earlier attempt, a next-round window for *every* consumer, lost 0.3-0.8 points. Keep the change to
  leaves_at and the matching want_home read.
- Expect B1 and veto-still turns to rise unless a vetoed goal leads to a wait or re-target; W2 covers that part.

**Must not touch.** plan.cc, the prey/chase code, model/pathing.cc.

### W2: every executed advance is asked, and a refusal never idles or sidesteps

**Scope.**
- combat/plan.cc: the strike search's executed walk, around line 2214. Ask `leaves_at` on the executed end tile
  only (lazy, a single ask), not per candidate.
- combat/fight.cc: `prey` / `chase` step (around line 825). Its step is asked the same way. This is a different
  function from W1's.
- model/pathing.cc `step_field` (line 1764): instead of skipping the search when `veto_reserve()` doesn't fit,
  search with a cap bounded by the fuel left, as `step_towards_funded` does. This makes the work bounded, not
  gated; no new fuel gate.
- Bank and farm goal choice (economy/): when the goal tile is vetoed, re-target or hold rather than route around
  the refused tiles.
- Use leaves_at only through its existing signature.

**Must fix.**
- gen-gem-drought-600105820-1 vs v69 h0 (rounds 1434-1437).
- gen-arena-410402606-2 vs v69 h6 (rounds 535-538).
- 267-gen-leaky-diagonals-600207807-12 vs v68 h4 (B runaway (46,42)↔(45,42)).
- wild-410406240-21 vs v66 h3 ((41,20)↔(41,19)).
- static-descend idle turns: 9.9k per 1196 v69 games.

**Expected saving.**
- Unasked moves are ~29% of events and ~16% of cycles (~60k events). They are realised fully only once W1's
  model lands.
- Static-descend idle and the bank sidestep: ~40k turns over 5124 games, plus part of C2 and X.
- Total roughly 60-80k turns.

**Risks.**
- The earlier post-strike refusal (a28721f3) lost 0.58 points, because a strike's walk refused after the fact
  forfeits the hit. Ask only no-hit search moves, or price the hit in.
- Fuel: one stand per executed move; it must leave `tools/fuel/bench.py` within budget.
- A bounded search may still run out of fuel on the leaky-diagonals pattern, so check its out-of-fuel turns
  directly.

**Must not touch.** leaves_at internals, `drawn_home`, `stand_lost_at`, model/safety.*, combat/guard.cc. Those
are W1's, so the two can run in parallel and their gains compound.
