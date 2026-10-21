# Strike search: handoff notes

Spec: [STRIKE-SEARCH.md](STRIKE-SEARCH.md). Phase 1 (search core) is on main (52.6% vs main before it, hecate-v9).

## Phase 3a (branch `orch/strike-p3a`): Varg's splash in Reach and Strike

- **Rule** (cambc-rules.yaml `champions.varg`, `probe-varg-splash`): a basic attack also hits other enemy
  champions and camps within 1 of its target. An enemy Varg therefore reaches p through any unit beside p.
- **Reach** (safety.cpp): `units_` = our visible champions other than us (`occupied`) plus live camp members in the
  9x9 window. `splash_targets(from, range)` (per build, lazily, per tile set): the units a basic attack can hit from
  `tiles_[from]`, with the target's sight (bush clusters, enemy wards) as for p. In `at()`, a sight way with no
  direct attack tile still hits p when `splash_targets & box(p, 1)` is non-empty (one AND per way). Varg's sight
  ways are all basic attacks (reset and shield add no spell way). `w.bound` grows by 1 only when `units_` is
  non-empty, so `reach()` and `enemy_area()` grow only near units.
- **Strike** (`compute_strike`): basic-attack entries (basic, reset, dash then attack) reach `range + 1` for Varg;
  `threat_strike`'s second-attack widening too. Unconditional, as Strike must bound Reach; this is what widens
  `want_home`, `step_guard`, `prey`, unseen Varg threats (`unseen_weight` uses the reach) and our own Varg's Strike.
- **Debug check** `REACH-BOUND round e<idx> ...` (in `Safety::blow`, debug_block, once a round): Reach's reach,
  damage or stun beyond Strike's. 0 seen.
- **6 games** (Varg drafted 2nd by both sides: cand = this branch, ref = hecate-v9 with `test_draft` off; 00packs,
  gen-shared-gems-720701900, gen-huge-shared-720707800, both sides): no crash, 0 REACH-BOUND/EXH/DOM.
  - SRCH-REFUSED: cand 8, ref 6, all attacks (op 1) or dashes (op 3), on both sides, so not from this change. Most
    are on turns whose SRCH line shows `fuel 0` and a wrapped phase counter (likely fuel running out mid-search;
    unconfirmed). Worth a look in the fuel work: these Varg drafts make it visible.
  - Out-of-fuel turns (oof.py): cand 46, ref 39; shared gems 37 vs 36, 00packs 9 vs 3 (one Heart of Ruin chain
    of resumed turns at r468-470/805/901-903). Turns over 95k on 00packs 22 vs 13. After this the per-query
    splash loop moved into the per-build `splash_targets` cache (an AND per query); not re-measured (game cap).
    The A/B's oof.py decides. Strength not judged; the A/B should include Varg-heavy test drafts (test_draft has Varg in 8 of its 30 compositions).

## Search (plan.cpp), as of phase 1 round 2

- `plan_strikes` = `Search::read` -> `grow` (DFS) -> pricing -> execution.
- **Grid.** Moves end within 3 of the start: 7x7 bitboard in a `uint64` (bit (y+3)*7+x+3). `free_` (walk/land),
  `pass_` (dash path: not wall, visible camp or visible enemy; `probe-dash-enemy`), `landings(c)` less `land_bad`.
- **Legality** per unit as grids: `Unit::legal` (basic attack, range + sight), `cast_legal` (range 4). Sight is
  `attack_viewers()` (safety.cpp), exact except viewers in a bush beyond a step (conservative).
- **DFS over symbolic moves.** W and plain D are not expanded per tile: later actions AND their legality into the
  move's requirement (`req_w`, `req_d`, `req_e`), and `settle()` resolves end tiles. Hitting landings (Heart of
  Ruin) are expanded once per set of foes and camp groups hit (`lset`). Ground casts from the start only.
- **Covered:** W, A, R, D, S (unit and ground), Cassi's stun anywhere, melee W A R A, ranged W R A, a move only when
  a strike follows it (`Node::owed`), attack + cast both orders, Marcella's armed stun, Vendetta's refresh, Varg
  splash both ways, camps as targets only for Vendetta (kill) and Varg (splash onto a foe).
- **Wakes** (`wake`, `find_wakers`, memo `wake_at`): woken strikers hit the nearest of us, visible allies, held
  enemies; 2 hits when a step cannot leave the reach. Bans: sleeping Monolith member; ally recalling/tributing/on a
  cleared camp; a lethal woken hit. No landing may wake a sleeper or hit only camps (`land_bad`).
- **Leaf score** = hits - cast 40 / dash 2*step + shield_worth(start) if the cast is unused + step if the walk is
  unused; then + progress - camps - 0.25 x Reach blow (HoR scaled by new damage_scale) - unseen threats beyond 1.
- **Pricing:** tiles by bound, foes by Strike share, cut once a tile cannot win; `max_exact_queries` 10.
  Distance-3 winners must pass `Safety::lethal`.
- **Execution:** `Search::concrete`; a walk/dash refused by a hidden unit takes the best leaf with the same prefix
  avoiding that tile, else `strike_enemy`. `Pathing::try_move` has a `refused` out-param.

## Debug checks (debug_block, `debug_search` in plan.cpp)

- `SRCH-EXH`: exhaustive enumeration per end tile must equal the search. `SRCH-DOM`: the old menu (`menu_shape()`)
  must not beat the choice. `SRCH-REFUSED`: an action that threw or was refused other than by a hidden unit.
  Debug code never touches Safety, Pathing or sight caches (byte-identical to release).
- `SRCH r handle fuel .. nodes .. read .. grow .. price .. act ..` per call (read `team-*.stdout`, strip NULs).

## Fuel

- Phase 1 round 2, 6 real-budget games vs main: 0 OOF each side. Search per call mean 9k, p90 12.5k, p99 27k, max
  44k. Heaviest: HoR fights with 2 foes (40 nodes, ~60k grow at 100M; ~36k not located). Next step: meter grow's
  per-node work (Node and health copies, dash and walk set-up).
- A search that runs out of fuel resumes next round and carries out its stale plan (a REFUSED source).

## Gotchas

- Window (9x9, safety.cpp) vs Grid (7x7, plan.cpp) layouts differ; `to_grid` converts row by row.
- `hit_unit` mutates `h` before it can fail: callers restore `h = saved`.
- Cassi and Issac: `Unit::link` pairs the bodies; all damage goes through `lose()`; `moot()` drops a body's own value
  when its partner dies later in the same blow.
- `land_hits` marks landings within the radius of a foe or live camp member; others stay symbolic.
- Not done: the probe that no second cast follows a Vendetta refresh; the Strike-equals-Reach shortcut (now also
  needs no units beside p for a Varg); stunned/capture-holding enemies as fixed wake targets.

## Next

Phase 3a A/B (ladder + gen, both sides, vs hecate-v9) with oof.py; then 2 (heal and shield as leaf options) and 3b
(killed and stunned foes leave the end tile's danger).
