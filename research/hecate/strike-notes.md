# Strike search: handoff notes

Phase 1 (search core) is on main (52.6% vs main, kept), and so are phase 3a and phase 2 (heal and shield as
options; 50.0% of 1094 vs main, 51.1% at 100M, out-of-fuel turns 7041 vs 6256). Spec: [STRIKE-SEARCH.md](STRIKE-SEARCH.md).

## Phase 3a (on main): Varg's splash in Reach and Strike

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

## Phase 2: heal and shield (on main)

- A leaf whose cast is unused goes to `best` with the best heal from the start tile or the end tile (`heal_from`,
  worth min(amount, missing, cooldown x `damage_bound(mate)`)), and to `kept` (shielders): pricing adds `shield_at(c)`.
- `Planned::searched`: decide skips its post-plan heal, act() its end-of-turn heal/shield unless the goal walked or
  hit after. decide's post-plan `shield_if_needed` stays (the search cannot see the goal's hit on a farmed camp).
- 6 games vs main: 0 EXH/DOM; OOF 46 vs 41. Search mean 11.0k vs 10.3k.

## Phase 3b: removal (orch/strike-p3b)

- **Rule.** A leaf's removed set (bits by enemy index) drops enemies from its end tile's danger: a killed foe and its
  Cassi/Issac partner (`Unit::drop_kill`, the partner by `linked_partner`, seen or not, so unseen threats from
  `threats_at` drop too); a stunned foe only if `turns_before_ours == 1` and it was stunnable (not Marcella, not
  already stunned: `x.stunnable`, read only when the turn can stun) (`drop_stun`). `stun_worth` stays 80.
- **Collapse.** `best`/`kept`/`exh`/`exh_kept` are `Front`s per tile: the best leaf per removed set, less any another
  beats with a superset removed (`Front::admit`); 8 entries, when full the lowest goes (an option lost, never one
  overvalued). With no removal it behaves exactly as before.
- **Pricing.** Per tile, `gather` lists both fronts' candidates; each Reach blow (and unseen threat) is added to the
  candidates not removing that enemy (HoR factor per leaf); a foe every candidate removes is never queried. The tile
  takes the best candidate (`Tile::entry`); `t.danger` = the largest candidate danger (keeps SRCH-DOM sound).
- **Checks.** SRCH-EXH compares fronts by mutual cover (each entry matched by one removing a superset, within 0.5);
  skipped when a front is full. SRCH lines add `rm` (chosen removed set), `sets` (largest front), `leaves`.
- **6 games** (hecate's draft, this branch vs main's hecate; 00packs, gen-shared-gems-720701900,
  gen-huge-shared-720707800, both sides): no crash, 0 EXH/DOM. REFUSED 9 vs 5, every one on a turn that ran out
  of fuel (as before). The removal decided 56 of 3213 searches (`rm` non-zero); fronts held 2 sets 4 times.
- **Fuel: not settled.** OOF (oof.py) 179 vs 38: shared gems 175 vs 36 (143 in one game, an early 4v4 brawl
  r37-176 where all four of ours search each turn), 00packs 4 vs 2, huge 0/0 (no fights). Search per call mean
  13.1k vs 10.5k; on searches of the same shape (nodes, offers, tiles, queries, foes) read +0.4k, grow +0.2k,
  price +0.55k over main, of which p2's notes claim +0.2k/+0.1k/+0.3k. So 3b costs ~0.5k a call; the rest of the
  OOF gap looks like game divergence, but 6 games cannot say. The A/B's oof.py (vs p2 and vs main) decides.
- Not done: the shield's `damage_bound` (and heal worth) ignore removal, so a kept shield is overvalued next to a
  leaf that removes the foes it would block; camps woken onto a stunned enemy (fixed wake targets).

## Debug checks (debug_block, `debug_search`)

- `SRCH-EXH` (exhaustive enumerator, per tile and slot), `SRCH-DOM` (old menu must not beat the choice),
  `SRCH-REFUSED` (an action refused other than by a hidden unit), `REACH-BOUND` (3a: Reach beyond Strike).
- Debug code never touches Safety, Pathing or sight caches: the game stays byte-identical to release.
- Summariser: strip NULs from `team-*.stdout`, regex `^SRCH`; skip lines with wrapped phase counters (OOF).

## Fuel (main)

- Searches start with ~40-60k left (after step_guard down to `act_reserve` 20k + estimate); OOF turns are those
  whose search costs 25-50k. Tail: Heart of Ruin trees (30-56 nodes, ~1.5k a node), ground centres with many unseen
  tiles, pricing at the query cap. Caps on nodes/queries changed games but not OOF: the tail needs cheaper nodes.
- A search that runs out of fuel resumes next round with a stale plan: the source of every REFUSED seen so far.
- WASM: raw bitboard reads cost more than host ops plus `positions_into` for 7x7; cache Window rows as `uint16`.

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
- `Tables` live in a union so their initialisers never run (~50k of turn 1); `Front::n` is valid by the has bits.
- Not done: the probe that no second cast follows a Vendetta refresh; the Strike-equals-Reach shortcut.

## Next

Phase 2's out-of-fuel rise (+12.5% on the A/B) is unlocated. If 3b's OOF rises, meter `gather`/`admit` in a
debug_block first. Phase 4a takes retreat turns, and with them the last reset_may_kill/landing_ready use.
