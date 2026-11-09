# Escape planner fuel, second pass (2026-11-09)

The task: cut the build cost of `model/escape.cc` again, keeping its plans identical. The gate values
(`params::escape::min_fuel`, `slack_fuel`) were left alone. The candidate is `bots/variants/fo-lean`, which equals this
branch's `bots/ocean`.

## Profile of the shipped build (oc-esc-478)

There were two measurements:
- **Phase checkpoints.** `fuel()` was read between phases in a debug build, using
  [phasepatch](#tools). They cover `bench.py run --set wide --test-draft` against oc-cl2-seat5m at 100M fuel:
  52 games and 13,705 builds.
- **A per-site profile.** `tools/fuel/fuelprof` was run over 16 games at 100M fuel against oc-cl2-seat5m.

| phase | 478 | fo-lean (before its last read change) |
| --- | ---: | ---: |
| pursuers (beliefs, classes, unseen exports) | 1.90k | 1.9-2.3k* |
| terrain (window rows of the static and camp boards) | 1.12k | 0.95k |
| hit layers | 4.60k | 4.34k |
| our dash and the goals | 1.16k | 1.16k |
| backward pass | 1.40k | 1.26k |
| **build** | **10.17k** | 9.97k |

\* Shifts in code generation move fuel between phases from build to build.

What the profile showed:
- **The grows are not the cost.** I had expected the hit layers to be dominated by dilations, at about 40 wasm ops
  each. Cutting a third of them (below) saved only ~6% of the phase. One pursuer class costs ~2.1-2.4k of hit layers,
  however few grows it does. The rest is loop, lambda and spill overhead around them.
- **About 20% of escape.cc's fuel has no source line.** It is compiler-generated: spills, constants and
  prologues.
- **The top line was the scalar row extraction from the packed boards.** That is `row()`/`rows_of`: about 2k a
  build for seven boards times 15 rows, plus the per-row `RowAt` table.
- **Queries cost ~6%.** `value`, `after_dash` and `after_walk` are called from `escape_landings` and
  `retreat_step`.

## Changes (all exact)

1. **Hit layers reuse their grows.**
   - `grow(walked)` is computed once a turn. It serves both the pursuer's dash landings and the next turn's walk.
   - A melee pursuer's strike, `grow(moved)`, is also its next turn's walk.
   - A ranged pursuer's shot from where it stood is the first step of `widen`, which the walk reuses.
   - Dash-spent tiles are tracked as `moved` = walked | dashed. Its dash landings hold `walked` from its first dash
     turn on, so after that turn the old "shoot after a dash from an undashed tile" term is already in `moved`.
   - `grow(empty)` is no longer computed before a pursuer's dash turn.
   - `grow_by` is split into `widen(h, r)`, which carries on from a set already within 1. With one mask at the end,
     a masked or an unmasked start gives the same rows.
2. **Backward pass.** grow distributes over a union, so the dash-kept rows take one grow of
   (walk ∪ dash landings) instead of two.
3. **Terrain.**
   - The static boards are now `passable`, `~walls` and bushes. Each spawn is read only on the window rows that its
     bounding box meets, and is usually not read at all.
   - Before, the code read seven full boards: walk and dash for both teams, bushes, spawn and camps. Now it reads four
     full boards (camps, passable, unwalled, bushes) in one row loop that shares the index arithmetic. That loop
     replaces the per-row `RowAt` table with one `Span`.
   - `blocked_for_us` = impassable | enemy_spawn (world.cc), so walk_us = passable & ~enemy_spawn, and likewise for
     the rest.
4. **`escape_landings`' `rank_of`** reads one value when the slack goal is off, which is the same value twice.

## Identity

- **Plan dumps** (`dumppatch.py`). Each ESC debug line carries a hash of hit_[0..5], walk_, path_, slack_goal_,
  origin_ and the full pass, and each slack pass prints its own hash. Over the same 52 bench games at 100M, fo-lean
  and 478 print identical ESC/ESCS lines: 13,705 builds and 7,080 slack passes, 20,785 lines, no mismatch.
- **`bench.py compare`** of the plain builds (base.json against lean.json): **identical replays 52/52**.
- **A read-only audit** of the diff against HEAD found no input where any value differs. It relied on these
  assumptions:
  - reach and burst are at least 1, which they are;
  - the static boards are fixed once exported;
  - widen's chains cover every offset monotonically.

  It also noted a pre-existing limit, unchanged: `widen`'s doubling under-reaches for r >= 8, which is unused (reach
  is at most ~6).

## Cost

The ESC debug lines measure each build from the 52 bench games at 100M fuel. Both bots make the same builds.

| | mean | p50 | p90 | p99 | max |
| --- | ---: | ---: | ---: | ---: | ---: |
| 478 | 10,193 | 9,713 | 14,032 | 17,625 | 21,261 |
| fo-lean | 9,622 | 9,177 | 13,521 | 17,220 | 21,795 |

- **Overall, the build is 5.6% cheaper (-570 a build).** By class count: 1 class 7.6k → 6.9k, 2 classes 9.5k → 9.0k,
  3 classes 11.6k → 11.1k.
- **Slack pass:** 1,110 → 1,040.
- **Per-site profile of the same 16 games:** whole-bot fuel fell 5,408M → 5,405M, all of it in the planner (about
  -5.5% of the planner's own fuel).
- **Code layout matters at this scale.** Some intermediate versions measured nothing or slightly worse in the
  profile than their debug-bench reading suggested:
  - the first hit-layer rewrite alone read +2% in one profile run, although 13 of its 16 games failed in that run;
  - making `widen` always_inline changed nothing.

## A/B

Final test: `py tools/ab.py variants/fo-lean variants/oc-cl2-seat5m --no-test-draft --suites maps/suites/merged/esc2-dev
--name fo-final-lean`, 40,960 games.

| CAND | win % | 95% CI | games |
| --- | ---: | --- | ---: |
| fo-lean (`replays/ab/fo-final-lean`) | **51.3** | 50.8-51.8 | 40,960 |
| oc-esc-478 = shipped ocean (`replays/ab/esc2-dev-478`, the orchestrator's run) | 51.4 | 50.9-51.8 | 40,960 |

**Win rate: level**, as expected. A 5.6% cheaper build is ~570 fuel on the turns that plan, and the headroom arms
(EXPERIMENTS "Escape planner fuel") put the whole plan's cost at ≤ ~0.9 points.

**Out-of-fuel turns.**
- **This batch played on stock cambc**, so it has no `Out of fuel:` lines and the A/B summary reads `?`. The
  launcher's env line read `CAMBC_SLOT_WEIGHT=12CAMBC_BIN=...`: a missing space, so `CAMBC_BIN` was never set.
  Stock and the fast runner play the same games, so the win rate stands. The merge's held-out run has the counts
  (CHANGES 480).
- **The proxy.** Turns are counted from the replays' `team-?.fuel`, as entries of exactly 100,000. Each batch saved
  1,000 replays, and the two batches share 988 games. On 478's batch the proxy reads 3% under the runner's count:
  11,027 against 11,350 for CAND.

| 988 shared games | OOF CAND | OOF REF | CAND - REF |
| --- | ---: | ---: | ---: |
| oc-esc-478 | 11,027 | 10,121 | +906 |
| fo-lean | 10,572 | 9,773 | +799 |

- **CAND's OOF fell by 4.1%.** The reference's fell too (3.4%), because the games diverge: 920 of the 988 have the
  same winner.
- **The lift is small.** The excess over the reference, which the planner adds, shrank by ~12%. At normal fuel the
  cheaper build mostly lets turns near the gate or the end of the budget finish. That shows up as fewer lost turns,
  not as a measurable win-rate change.

## Rejected or not done

- **Deeper hit-layer work.** Merging the strikes of pursuer classes that share a reach, as one dilation of their
  union, is exact. It was not done: the bush-hidden strikes it would share are ~3% of the planner.
- **A per-tile flag-byte grid of the static boards** (one SIMD load a window row for every board). Building it costs
  ~W×H×boards ops once a game, ~100k+, more than a turn. Building it lazily per row puts ~10k on the first build in a
  new area.
- **Padding the static boards to a byte-aligned stride**, so every row has the same shift. It needs a ~15k
  repack once a game, which lands on a gated build turn, for maybe a few hundred fuel a build.
- **Folding camps into the static boards on each camp flip.** It would remove one board read (~150 a build) for
  ~1.5k of host calls a flip.
- **A lazy slack goal.** It would save ~0.3k on the ~48% of builds that never ask for the slack pass, and add a
  reload on the rest: ~60 a build net.
- **Reusing the first build after a dash** (the second build at the landing, which the 50k gate skips 83% of the
  time: sibling notes in `fuel-gate.md`). Not exact: the window moves by up to 2, so its edge rows need new pursuer
  reach, and `see_again` changes the beliefs.
- **The rest of a retreat turn** (decide before `retreat()` ~20k, `retreat_step`'s pricing ~13k) is outside the
  planner and was out of scope.

## Tools

Scratch scripts used here, not kept in the repo:
- `dumppatch.py` patches a frozen copy to print plan hashes in debug.
- `phasepatch.py` prints phase checkpoints.
- `esc.py` summarises ESC lines and compares two bench game dirs line by line.
- The fuelprof runs used `CXXFLAGS=-g` builds with 16 games played by `tools/fastengine/runner-prof` at
  `FASTRUNNER_BOT_FUEL=<bot>:100000000`. Warm the native cache with one game first: 16 cold starts at once lost games.
