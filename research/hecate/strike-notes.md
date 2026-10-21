# Strike search: handoff notes

Phase 1 (search core) is on main (52.6% vs main, kept). Phase 2 (heal and shield as options) is on
`orch/strike-p2`, ported onto phase 1 as reworked. Spec: [STRIKE-SEARCH.md](STRIKE-SEARCH.md).

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

## Search (plan.cpp)

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
- **Leaf score** = hits - cast 40 / dash 2*step + (phase 2, below: a heal or a priced shield) if the cast is unused + step if the walk is
  unused; then + progress - camps - 0.25 x Reach blow (HoR scaled by new damage_scale) - unseen threats beyond 1.
- **Pricing:** tiles by bound, foes by Strike share, cut once a tile cannot win; `max_exact_queries` 10.
  Distance-3 winners must pass `Safety::lethal`.
- **Execution:** `Search::concrete`; a walk/dash refused by a hidden unit takes the best leaf with the same prefix
  avoiding that tile (it becomes `chosen`), else `strike_enemy`. `Pathing::try_move` has a `refused` out-param.

## Phase 2: heal and shield

- A leaf whose cast is unused is offered per end tile twice:
  - `best[c]`: plus the best heal castable from the start tile or from c (`heal_from`, `tables.heal_at/heal_who`
    from `read_mates`). Heal worth per mate = min(amount, missing health, `ability_cooldown` x
    `damage_bound(mate)`), only if `worth_healing` (heal_ally's threshold, shared).
  - `tables.kept[c]` (shielders): pricing adds `shield_at(c)` = shield_worth's min(amount, duration x
    `damage_bound(c)`) once the tile's foes are priced; the bound uses the whole amount until then.
- Pricing keeps both candidates per tile (`raw_of/leaf_of`; danger `d0/d1` per candidate, as the HoR factor is per
  leaf). `Tile::keep` says which won, `Tile::shield` whether to cast it. `concrete(c, keep, shields)` puts a heal
  first (from the start) or last, a shield last (`Op::heal`, `Op::shield`).
- `Planned::searched`: a plan was carried out and its tile was exactly priced (a capped, unpriced tile had no
  shield priced, so the turn's end decides). Then decide skips its post-plan heal, and act() its end-of-turn
  `heal_ally`/`shield_if_needed` unless the goal walked or attacked afterwards (`searched_at`, `searched_hit`).
  decide's post-plan `shield_if_needed` stays: a cast the plan left unused had its shield priced at 0 (no seen
  blow or awake camp on the end tile). The search cannot see the goal's coming hit on a sleeping farmed camp
  (shield_if_needed's `in_reach && hitting`), so without this, farm's camp reset (Varg) or dash (Heart of Ruin)
  would take the cast first.
  Turns the search does not plan (no strike, heal on spawn `mend`, retreat `leave`) cast them first as before,
  with the reset_may_kill/landing_ready gate; `want_home` now runs before them (beliefs are fixed for the turn).

## Debug checks (debug_block, `debug_search`)

- `SRCH-EXH`: the exhaustive enumerator agrees with the search per end tile and per slot (spent/kept); heal only
  from start or end tile in both (exact for Willow, who has no dash).
- `SRCH-DOM`: the old menu (larger candidate's danger, shield left out) never beats the choice.
- `SRCH-REFUSED`: a thrown or refused action other than a hidden unit. `SRCH` lines carry `cast h|s|-`, `mates N`.
- Debug code never touches Safety, Pathing or sight caches: the game stays byte-identical to release.
- Summariser: strip NULs from `team-*.stdout`, regex `^SRCH`. Not committed (~30 lines).

## Phase 2 port: checks (6 games, real budget)

- Variant willow,varg,heart_of_ruin,marcella,vesper from this branch vs the same from main: 00packs, 01big-world,
  gen-huge-shared-720707800, both sides. No crashes, 0 EXH, 0 DOM. 5 REFUSED (main's copy: 3), every one a stale
  plan resumed after an out-of-fuel turn. Casts chosen: shield 115, heal 14 of ~1700 searches.
- Search fuel per call (lines that did not run out): mean 11.0k vs main's 10.3k (read +0.2k, grow +0.1k, price
  +0.3k, act +0.1k). p99 39-50k vs 29-44k.
- Out-of-fuel turns (oof.py): 46 vs main's 41 (00packs 27 vs 29, 01big-world 19 vs 12, shared 0 vs 0; the shared
  map had no search turns). Of the 46, 8 ran out inside a search (main: 10); the rest were farm, bank and goal
  work after small searches in diverged games. Within noise on 4 games; judge on a full A/B.

## Fuel

- Phase 1 round 2, 6 real-budget games vs main: 0 OOF each side. Search per call mean 9k, p90 12.5k, p99 27k, max
  44k. Heaviest: HoR fights with 2 foes (40 nodes, ~60k grow at 100M; ~36k not located). Next step: meter grow's
  per-node work (Node and health copies, dash and walk set-up).
- A search that runs out of fuel resumes next round and carries out its stale plan (a REFUSED source).
- **Fuel follow-up (orch/strike-fuel, same choices).** At 100M on the six worst A/B maps vs hecate-v8, main has
  no more over-100k turns than hecate-v8 (2.9% vs 3.1%): the real-budget OOF rise is not turn demand. SRCH lines
  now print `left` (fuel at the search's start): searches start with ~40-60k left, after step_guard's fights
  spend down to `act_reserve` (20k) plus an estimate, and the OOF turns are those whose search costs 25-50k.
  The tail matters, not the mean. Tail sources: Heart of Ruin trees (30-56 nodes, ~1.5k a node outside settle),
  ground centres with many unseen tiles (find_centres and the per-node centre loop), pricing at the query cap.
  Saved: per call mean 11.75k -> 11.2k, p99 42.5k -> 39.3k, max 204k -> 133k (12 games at 100M, identical).
- **Caps tried and dropped:** at most 3 landing groups a node (never bound: groups rarely exceed 3), at most 4
  centre kinds, 16 nodes and 6 Reach queries a search. The last changed 8 of 12 games at 100M and cut calls over
  50k from 44 to 26, but real-budget OOF did not fall (16 bench games 82 vs main 82; 6 worst-map games 58 vs 51
  for the same-choice branch). Bounding the tail needs cheaper nodes, not fewer.
- WASM costs: raw bitboard reads (`chunk_window`-style) cost more than host ops plus `positions_into` for a 7x7
  window; 128-bit Window shifts per row are dear (cache rows as `uint16`).

## Gotchas

- Window (9x9, safety.cpp) vs Grid (7x7, plan.cpp) layouts differ; `to_grid` converts row by row.
- `hit_unit` mutates `h` before it can fail: callers restore `h = saved`.
- Cassi and Issac: `Unit::link`; all damage through `lose()`; `moot()` for one blow on both bodies.
- `Tables` live in a union so their initialisers never run at start-up (they cost ~50k of turn 1).
- A search that runs out of fuel resumes next round with a stale plan: all REFUSED seen so far.
- The shield's `damage_bound` ignores camps the leaf itself wakes (their hit is in the wake cost only).
- Heal targets only allies visible at turn start. Neither heal nor shield pays `cast_cost`.
- Not done: the probe that no second cast follows a Vendetta refresh; the Strike-equals-Reach shortcut;
  stunned/capture-holding enemies as fixed wake targets.

## Next

Phase 2 A/B (hecate drafts HoR first, so the shield path is live; Willow and Varg only in variants). The open
fuel step: meter grow's per-node work in Heart of Ruin fights. Phase 3a (Varg's splash, above): its A/B. Phase 4a takes retreat turns, and with them the last reset_may_kill/landing_ready use.
