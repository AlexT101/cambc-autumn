# astraeus changes ported to ocean, round 2 (ocean, 2026-11-07)

Base `bots/variants/oc-base11` (= `bots/ocean`, CHANGES 449). Port copy `bots/variants/oc-astport2`, knobs
`params::astport2::`, off by default. Round 1 (`research/ideas-2026-11-05/astr-port.md`) covered astraeus up to
37e1eb64 (CHANGES 417). astraeus is at 8c0343f5e (CHANGES 440), frozen as `bots/variants/astraeus-now-1107`;
commits since 37e1eb64: 5166d1c58 (423), 53874b0b7 (424-428, 430-432, 435, 437), 9e1fad363 (439), 8c0343f5e (440).

## Inventory: astraeus entries 400+ against ocean

| CHANGES | what | in ocean? | here |
|---|---|---|---|
| 400 | lock memory, ally tribute proof, kill_turn emblem | yes (before ocean branched at 5b66bde0) | - |
| 403 | plan-check resign | yes (ocean has it too) | - |
| 409 | ocean's 402-404 in astraeus | ocean's own; its beaten_near fix tested in round 1 (H0) | skipped |
| 410, 411 | wip accuracy fixes | tested in round 1 as 6 knobs, all H0 (49.7-50.2) | skipped |
| 412 | draft reserve = recall_health_fraction | round 1 `draft_reserve`, H0 | skipped |
| 3076ffa9 logic parts | price_keep, spawn_field_first, loop_reserve, beaten_near_via | round 1: H0 but loop_reserve (~50.3 pooled on 3 unused suites); left out of the pool (CHANGES 441) as the alternative to r1's reserve | skipped |
| 417, 423 | ocean's 405, 413-414, 418-422 in astraeus | ocean's own | - |
| 424 | stand check reads; farm's centre fields | reads in (433); centre fields left out by 433 (they change a later approach in ocean) | skipped: <0.1% fuel, not exact in ocean |
| 425, 427, 428 | fuel merges 2, 4, 5 | yes (433) | - |
| 426 | altar walk, kite memo, siege team_power, round-1 | yes but siege()'s team_power once a call (433: diverges in ocean at a real decision) | skipped: same reason |
| 430-432 | fuel merges 6-8 | yes (434) | - |
| 435 | fuel merge 9 | yes (436) | - |
| **437** | fuel merge 10: strike search members unzeroed, grid boards in place on big maps, wakers' and camp threats' champion lists once, farm's clear priced last | **no** | **ported, unconditional (fuel-only)** |
| **439** | our own turn-end recall feint is not a channel for the walk to our farm choice | **no** | **ported, knob `own_feint`** |
| **440** | feinting enemies: camp wakers held in place, unseen unkept recalls do not heal, a new bag sure to bank keeps the recall | **no** | **ported, knob `enemy_feint`** |
| 442-449 (teacher) | astraeus_teacher only; none applied to astraeus | n/a | skipped |

## Port notes

- 437: patches from `fc7-m9`..`fc7-m10`. find_wakers merged by hand: ocean's enemies take ptw's
  `enemy_latest_slot`, kept in the near list. farm.cc's `passing`: astraeus's version returns true for the farm group
  without `affordable`; here it returns `affordable(g)`, so the reorder is exact.
- 439: `channel_held()` is `channelling()` with the knob off; `goal_field` and `strike_possible`'s gain keep the old
  code off; `prepare_next_turn`'s `recall_farm` test only on.
- 440: `held_this_round` in find_wakers, `recall_kept` for enemies, `enemy_feints_` detection and `recall_to_bank`'s new
  bag clause only on. Enemy `recall_kept` is read nowhere else in ocean (every other reader iterates allies).

## Exactness (bench.py, 100M)

- oc-astport2 (knobs off, 437 in) against oc-base11: default 16/16, wide (test drafts) 52/52 identical; total fuel
  -0.00% / +0.00%.
- Knob on, games that differ from oc-base11 (default / wide): both 15/16, 36/52; own_feint 10/16, 29/52; enemy_feint
  7/16, 17/52. Both act on most maps, so SPRT applies (no rare-trigger method needed).

## Results

Tables: EXPERIMENTS "Ocean vs astraeus and astport2 (ocean, 2026-11-07)".
- Every knob screen stopped on H0 at 2x: the bundle read 49.2%, own_feint 50.0% and enemy_feint 49.9%. At the real budget
  the bundle pooled 49.9% over 40,960 held-out games, and 50.1% on varied.
- 437 alone (oc-astport2, knobs off) pooled 50.45% (50.0-50.9) over 40,960 held-out games, with out-of-fuel turns
  -1.3%. Recommended for ocean as a fuel-only change; 439 and 440 are not.
