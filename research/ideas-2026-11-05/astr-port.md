# astraeus changes ported to ocean (ocean, 2026-11-06)

Goal: find what astraeus has that ocean lacks and port whatever helps into ocean. Base `bots/variants/oc-retest-clean`
(= `bots/ocean`: oc-tuned4 plus CHANGES 419-421). Dev copy `bots/variants/oc-astport-dev`, knobs
`params::astport::`, all off by default.

## Inventory

ocean branched from astraeus at 5b66bde0 (CHANGES 401). astraeus commits since (`git log 5b66bde0..HEAD --
bots/astraeus`, as of 37e1eb64):

| commit | CHANGES | what | class |
|---|---|---|---|
| 3076ffa9 | (fuel campaign) | squash of 32 worktree commits: pre-loop cuts, PreLanes bounds, crew tables, turn-end queue warm-ups, live_camps by dirty group, exact walk windows | (i) via CHANGES 415, except its logic parts d737bcf6, 4a16bebf, 9dba3ed8, 1310d649 + refit: (v) |
| a790c441 | (fuel) | farm loop: ocean's s2 and s4 fuel steps | (ii) ocean's 406 |
| 7950979e | (fuel) | altar access without floods, the unseen-enemy box, ocean's s5 | (i) via 415 / (ii) 406 |
| 9cb65c88 | 409 | ocean's 402-404 in astraeus, plus beaten_near's banking bound for the recall out | (ii), except the beaten_near fix: (v) |
| 4d1a2465 | 410 | selected astraeus_wip accuracy fixes (376, 385/390, 387, 396, 372's deadline) | (iii), less what 411 removed |
| 29cd0921 | 411 | removes 410's lock-break reset and share-based tribute deadline | (iii): only what remains of 410 is ported |
| 4f17957d | 412 | the draft's usable health reads `recall_health_fraction` | (iii) |
| 37e1eb64 | 417 (astraeus) | ocean's 405, 413, 414 in astraeus | (ii); ocean has since retuned (418) and replaced 414 (420) |

A hunk-by-hunk scan of `git diff 5b66bde0 HEAD -- bots/astraeus/src` against ocean's source (every added line looked
up in ocean's file) finds nothing else: the remaining differences are ocean's own equivalents (the 406 memos for
gems_short/race_left/gems_share, which astraeus keys by BagKey; ocean's PreLanes layout with `exposure_most`;
`champion_wealth`, which 420 removed) and the constants, where ocean keeps its own (405, then 418). No
astraeus-only fuel-only change (iv) is left: 415 took them all.

### (iii) astraeus-only, decision-changing

Each is a knob. astraeus measured 410 as one bundle (with the parts 411 removed): **49.88% (49.19-50.56)** of 20,480
against 0f7830e1, OOF -0.26%, farm partial evaluations +1.2%. 411 was not A/B tested.

| knob | from | what |
|---|---|---|
| `shield_ready` | 410 (wip 387) | camp damage priced with the shield's cooldown after the trip: `recovered_for_work`, farm's `affordable`, `crew_share` (by arrival) and the alone clear (not under way: ready after the reach) |
| `reset_finish` | 410 (wip 387) | Willow's `immediate_camp_finish` counts two basics only with the attack reset ready |
| `dead_camp_tiles` | 410 (wip 376) | `local_support` and `heal_reaches` may use dead camp tiles (`open_for_us`, minus live members) |
| `leaving_holders` | 410 (wip 387) | `capture_taken`: an ally on the tiles that is held back or recalls out before payout does not count ahead of us |
| `lock_arrival` | 410 + 411 (wip 385/390) | banking: a melee champion hits the lock on the step it arrives and then tributes; a ranged hit that breaks the lock is followed by the tribute; `lock_turns` counts the arrival hit (melee, or already there) |
| `shop_forecast` | 410 (wip 396) | `best_emblem` gives the learned emblem in forecasts too (prices, affordable_prefix, hypothetical items), not only inside buy_shards |
| `draft_reserve` | 412 | the draft's usable health uses `recall_health_fraction` (ocean 0.298) instead of `draft_recall_health_fraction` (ocean 0.227) |

astraeus's 412: 50.02% (49.04-51.00) of 10,000 against 29cd0921: level, kept as one fewer constant.

### (v) left out of 415 because they change decisions

| knob | commit | what | astraeus measured |
|---|---|---|---|
| `price_keep` | d737bcf6 | `prices` keeps best_emblem's choice until the gem share moves by a tenth; gain and per_gold follow the share | with the exact pre-loop cuts 51.0 (50.3-51.7) of 20,480 vs a67cb2ca; on top of them 50.7 -> 51.1 on the same maps (within noise) |
| `spawn_field_first` | 4a16bebf | the spawn field is made right after the first World::update | level: +0.5, -0.1, -0.2 paired over 3 x 10,240 |
| `loop_reserve` | 9dba3ed8, 1310d649, a650e7e1 refit | after the first turn the farm loop keeps back a reserve fitted by class (banking x dash ready) per chunk and layer instead of the walk's estimates | rsv2 51.1 / 51.3 against 5b66bde, farm partial evaluations -21%, OOF -3% against the stack; the refit 50.2 (49.7-50.8) of 30,720 |
| `beaten_near_via` | 9cb65c88 | beaten_near's banking bound prices the recall out without the walk's trip home | only inside 409's port bundle (55.0) |

## Method

Each knob alone against oc-retest-clean, own drafts, real fuel, fast runner:
- dev: SPRT 0.50/0.51 on fresh-536000..536039 (`ap-dev`; 535xxx was taken by the measuring agent);
- ≥50.3: a full 20,480 on the dev suite, then confirm on unused 536100..536139 (`ap-conf`);
- winners combined, confirmed on 536200..536239 (`ap-combo`), `--mix varied` 536300..536309 (`ap-varied`), and the
  panel (panel-check-514510, astraeus-now-1106 as its astraeus). A third set, 536400..536439 (`ap-conf2`), was added
  when the first two confirms disagreed.

Exactness: bench.py at 100M against oc-retest-clean (default 16, wide 52, pool 128), knobs off byte-identical.

## Results

Full tables: EXPERIMENTS "astraeus changes ported to ocean (ocean, 2026-11-06)".

- Knobs off: bench.py at 100M identical to oc-retest-clean (16/16, 52/52, 128/128).
- Every knob but `loop_reserve` stopped on H0 at the dev SPRT, 49.1-50.2%. reset_finish, dead_camp_tiles,
  leaving_holders, draft_reserve and beaten_near_via change few games (H0 within 1.5-2.5k games); lock_arrival (50.1),
  shop_forecast (49.7) and price_keep (49.7) change most games and still read level or below.
- `loop_reserve`: 51.1 (SPRT H1), 51.0 over the full dev suite; on unused seeds 50.7 (50.0-51.4), 50.1 (49.4-50.7) and
  50.0 (49.3-50.7), ~50.3 pooled over 61,440; varied 50.0 (48.6-51.3); panel mean +0.34, no member down
  significantly; OOF -2.4%, farm-loop cuts -25% on the real-budget bench. Its scale sweep (0.8-1.3) is flat over
  0.8-1.0 and loses from 1.15 up.
- Frozen: `bots/variants/oc-astport` = oc-astport-dev with `loop_reserve` on (scale 1.0).

## Draft CHANGES entry (not shipped; number at ship time, 424 or the next free)

## 424: the farm loop keeps back what the rest of the turn spends, by class (ocean, 2026-11-06)

astraeus's state-sized reserve (9dba3ed8, 1310d649 and the a650e7e1 refit), which CHANGES 415 left out as a logic
change. After the first turn, farm_turn's loop stops evaluating groups when fuel falls below end_reserve plus a
reserve fitted on astraeus's cut loops at the real budget by class (banking x dash ready): 24.7k / 20.4k / 21.4k /
16.4k plus per search chunk and per chunk and layer of the walk to the choice, in place of the walk's own estimates
(`walk_reserve` + `search_cost_estimate` + travel). The first turn keeps the old terms. bench.py at 100M identical to
oc-retest-clean (16/16 default, 52/52 wide, 128/128 pool). Real budget, wide bench: OOF turns 662 -> 576, farm partial
evaluations 9,552 -> 7,131. Own drafts, real fuel, against oc-retest-clean, 20,480 games each: 51.0 (50.3-51.7) on
fresh-536000..536039, **50.7 (50.0-51.4)** on unused 536100..536139, 50.1 and 50.0 on unused 536200..536239 and
536400..536439 (~50.3 pooled over 61,440), out-of-fuel turns -2.4%; 50.0 of 5,120 on `--mix varied`; panel mean
+0.34 with no member down significantly. Scaled 0.8-0.9 it is level, 1.15-1.3 loses. The other astraeus changes
ocean lacked (410's parts, 412, d737bcf6, 4a16bebf, 9cb65c88's beaten_near fix) were level or lost. Frozen as
`bots/variants/oc-astport`. Evidence: EXPERIMENTS "astraeus changes ported to ocean (ocean, 2026-11-06)".
