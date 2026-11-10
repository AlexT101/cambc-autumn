# Lane A: the world update (order, laziness, cross-turn reuse): no-go

**Verdict: no-go.** On turns where a gate cut work, the world update costs about 10.2k. At most about 1.1k of it is
not plainly read before the turn's first action. The go bar was about 3k, so I built no candidates and used no
refund-scope runs.

## Method

`bots/variants/fga-meas` is oc-ceil-ref plus raw-fuel probes inside `debug_block` (patch: `laneA-meas.patch`). The
probes cover:
- each part of `World::update`;
- the turn's first action: the first `self_acted()` inside decide, i.e. the first move, attack or cast;
- the end of decide;
- the turn's `SHORTCUT` count.

Setup:
- 64 maps from `merged/fceil-2020`, every 160th file, played on both sides against oc-ceil-ref: 128 games and about
  570k turns.
- Fast runner, own drafts, debug builds. Those are -O3 like release: only `debug_block` is added.
- Tables: `laneA-wm.py` and `laneA-wm2.py` (replays in `replays/fga-meas1`, `fga-meas2`).
- Turns that resumed after running out are dropped, because their start fuel belongs to the round before.

## The world update now, per part (mean fuel a turn, alive turns, round 2 on)

| part | all | any gate cut (6.0%) | `farm-partial-evaluation` (3.2%) |
|---|---|---|---|
| **whole `run("world")`** | **7.1k** (p50 6.5k, p90 11.2k, p99 15.7k) | **10.6k** | **10.2k** |
| vision board | 0.16k | 0.15k | 0.17k |
| priorities, ranks, slots | 1.5k | 2.4k | 2.0k |
| of which `rank_turns` | 0.56k | 1.32k | 1.06k |
| allies | 1.35k | 1.70k | 1.69k |
| visible enemies | 0.33k (0.6 of them) | 1.14k (2.1) | 0.74k (1.3) |
| unseen enemies | 0.83k (4.9) | 1.31k (3.6) | 1.64k (4.4) |
| of which `track()` | 0.33k | 0.92k | 1.17k |
| camps | 2.3k | 3.2k | 3.1k |
| of which the view scan | ~0.95k | ~1.1k | ~1.1k |
| of which settled groups | 0.54k (2.3 groups) | 0.82k (3.4) | 0.76k (3.0) |
| of which updated groups in view | 0.84k (1.1 groups) | 1.31k (1.7) | 1.27k (1.6) |
| of which timer-only groups out of view | 0.01k | 0.01k | 0.01k |
| altars and scores | 0.52k | 0.60k | 0.59k |
| the rest (begin_turn, self_acted, the lambda) | 0.17k | 0.17k | 0.17k |

Spent before the turn's first action, world update included:

| turns | mean | p50 |
|---|---|---|
| all | 18.4k | 14.1k |
| farm-cut | 29.2k | 22.9k |

So on farm-cut turns the world update is about a third of what the turn spends before it acts.

## What is read before the first action

- **Read before acting on essentially every turn that could gain:**
  - Camps feed the farm loop. It weighs groups nearest first, and every updated group is in view, so within 8 tiles.
    Safety reads the stirring camps too.
  - Visible enemies, and ranks and slots, feed Safety, the step guard and camp-fire order, which run before any step.
  - Allies feed crew pricing (`plan_crew`'s expected allies), camp targeting and support.
  - Altars feed `want_home`, which runs before the branch on nearly every live turn.
  - Scores feed `comeback::cooked`, which is decide's first line.
- **Not plainly read before acting:**

  | part | farm-cut turns |
  |---|---|
  | tracking of enemies whose `possible_box` does not come within 14 of us (0.41 enemies a turn) | 0.50k |
  | altars and scores, counted as if unread | 0.59k |
  | timer-only camps out of view | 0.01k |
  | **upper bound** | **1.1k** (0.6k over all turns) |

  Tracking is small because `params::track_horizon` is 3: an enemy unseen for more than 3 rounds is not grown at all.
- **Skipping unchanged entities is already done** wherever the engine can prove it:
  - `camp_settled`: a group in view that is asleep or respawning, read through one witness;
  - timer-gated out-of-view camps (`camps_pending_`);
  - `fix()` keeps a visible enemy's boards when it has not moved;
  - shared track lineages;
  - the `items_key` emblem skip.
- **What is left:**
  - `rank_turns`, about 1.1k on farm-cut turns. A memo of its inputs was tried in CHANGES 495 and cost +165 a turn.
  - The camp view scan, already incremental on the tiles that changed.
  - Per-ally host reads, which are needed because an ally may have acted since our last update.

At the brief's +0.17 to +0.45 a point per 1k a turn, the 1.1k bound on cut turns (0.6k over all turns) is worth at
most about +0.1 to +0.3. That is below what a 20k-game audit can see (±0.9), and every deferral also needs a lazy
accessor at 25+ read sites (`possible` alone has 36 outside world.cc; `camps[` has 137).

## The first turn

The first turn is where the deferrable fuel is large, but it has already been priced small. From
`bots/variants/fga-fprof`, which is fga-meas with `debug_fuel` on (the meters cost fuel, so play differs), over 348
first turns on 64 games:
- The world update costs 63k of the first turn's 200k (p50 61k, max 111k):

  | part | fuel |
  |---|---|
  | `build_static` | 29k (`static_camps` 15k, boards 3.9k, crossings 3.9k) |
  | `init_beliefs` | 9.3k |
  | the first `update` | 13.8k (track 3.1k) |
  | `from_ally_spawn` | 9.0k |

- The first action comes at 146k spent.
- The farm loop is cut on almost every first turn: 710 `farm-partial-evaluation` lines in 698 first turns.

Two candidates looked possible: deferring `from_ally_spawn` to the turn-end queue (9k), and deferring parts of
`build_static` the first turn does not read.
- EXPERIMENTS 11-08 priced a free world update on the first turn only at **+0.36 ±1.08**, for all 63k. A 9-20k
  deferral would be a fraction of that.
- `from_ally_spawn` is made first on purpose (main.cc comment): while it is missing, heal trips use a crow-flies
  bound, and the turn that made it depended on fuel. So deferring it changes play in a way the code was written to
  avoid.

I did not build either.

## Open questions

- Why does `rank_turns` cost about 0.7-0.9k a call for 10 champions? It is SIMD `rank_by` on two sides, two passes
  when next round's order differs, and it re-ranks on about 60-80% of turns. Against oc-ceil-ref the enemy side
  re-ranks whenever an enemy in view changes its payload bits: `shift` is 0 for enemies, because their encoding is
  unknown. An exact cut is possible, but this programme does not want exact cuts, and 495's memo lost.
- Lanes B and C: on farm-cut turns 29k is spent before the first action, and the world update is 10k of it. The other
  19k (want_home, guard, route) is where the order and laziness ideas could pay, but it is outside lane A.

## Files

- Copies: `bots/variants/fga-meas` (probes inside debug_block only: release builds are unchanged) and `bots/variants/fga-fprof` (+ `debug_fuel`).
- `laneA-meas.patch`: fga-meas against oc-ceil-ref.
- `laneA-wm.py`: world parts by turn class (`WM` lines).
- `laneA-wm2.py`: tracking near and far, `rank_turns`, and the first turn (`WM`, `WT` and `WF` lines).
- Replays: `replays/fga-meas1`, `replays/fga-meas2` (128 games each) and `replays/fga-fprof1` (64 games).
