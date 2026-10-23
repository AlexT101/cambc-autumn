# hyperion: strike search

On turns with an enemy in reach, `plan_strikes` (plan.cpp) chooses our moves and hits by searching every action
sequence the rules allow (cambc-rules.yaml `turn`, `abilities`), scored against what the enemies can still do
afterwards. Farming is out of scope: camps enter only as targets on fight turns. Shipped as CHANGES 37 (core), 38
(Varg's splash), 42 (heal and shield), 43 (removal), 56 (`strike_after`), 58 (guarded tiles passable), 68
(commutation pruning), 76 (node cap), 85 and 87 (audit fixes).

## As built

- **Pipeline:** `Search::read` -> `grow` (DFS) -> pricing -> execution. `strike_after` runs it again from where the
  goal left us while a hit is possible.
- **Grid.** Moves end within 3 of the start: a 7x7 bitboard in a `uint64` (bit (y+3)*7+x+3). `free_` (walk/land),
  `pass_` (dash path: not wall, visible camp, visible enemy or enemy spawn), `landings(c)` less `land_bad`.
- **Legality** per unit as grids: `Unit::legal` (basic attack, range + sight), `cast_legal` (range 4). Sight is
  `attack_viewers()` (safety.cpp), exact except viewers in a bush beyond a step (conservative).
- **DFS over symbolic moves.** Walks and plain dashes are not expanded per tile: later actions AND their legality into
  the move's requirement (`req_w`, `req_d`, `req_e`), and `settle()` resolves end tiles. Hitting landings (Heart of
  Ruin) are expanded once per set of foes and camp groups hit (`lset`). Ground casts from the start only. At most 24
  nodes (binds on 0.45% of searches).
- **Covered:** walk, attack, reset, dash, unit and ground casts, Cassi's stun anywhere, melee W A R A, ranged W R A, a
  move only when a strike follows it (`Node::owed`), attack + cast in both orders, Marcella's armed stun, Vendetta's
  refresh, Varg's splash both ways, heal and shield as options. Camps are targets only for Vendetta (kill), Varg
  (splash onto a foe) and Heart of Ruin's landing.
- **Wakes** (`wake`, `find_wakers`, memo `wake_at`): woken strikers hit the nearest of us, visible allies and held
  enemies; 2 hits when a step cannot leave the reach. Bans: a sleeping Monolith member; an ally recalling, tributing
  or on a cleared camp; a lethal woken hit. No landing may wake a sleeper or hit only camps (`land_bad`).
- **Leaf score** = hits - cast 40 / dash 2 x step + a heal or priced shield if the cast is unused + step if the walk is
  unused; then + progress - camps - 0.25 x Reach blow (Heart of Ruin scaled by its new `damage_scale`) - unseen
  threats beyond 1. Ren's retaliation is summed over the plan (`Node::hurt`).
- **Removal.** A leaf's removed set drops a killed foe (and its Cassi/Issac partner, seen or not) from its end tile's
  danger, and a stunned foe only if it has exactly one turn before ours and is stunnable. `best`/`kept` are `Front`s
  per tile: the best leaf per removed set, less any beaten by one removing a superset; 8 entries.
- **Pricing:** tiles by upper bound, foes by Strike share, cut once a tile cannot win; `max_exact_queries` 10. Strike
  must stay an upper bound on Reach (`Safety::blow` returns nothing outside Strike's reach), so every Reach rule
  change goes into `compute_strike` too. Distance-3 winners must pass `Safety::lethal`.
- **Execution:** `Search::concrete`. A walk or dash refused by a hidden unit takes the best leaf with the same prefix
  avoiding that tile, else `strike_enemy`.
- **Debug checks** (`debug_search`, in `debug_block`, game byte-identical): `SRCH-EXH` (exhaustive enumerator),
  `SRCH-DOM` (the old menu must not beat the choice), `SRCH-REFUSED` (an action refused other than by a hidden unit),
  `REACH-BOUND` (Reach beyond Strike). Summarise `team-*.stdout` with NULs stripped, regex `^SRCH`.

## Gotchas

- Window (9x9, safety.cpp) and Grid (7x7, plan.cpp) layouts differ; `to_grid` converts row by row.
- `hit_unit` mutates `h` before it can fail: callers restore `h = saved`.
- Cassi and Issac: `Unit::link`; all damage through `lose()`; `moot()` for one blow on both bodies.
- `Tables` live in a union so their initialisers never run (~50k of turn 1); `Front::n` is valid by the has bits.
- Not done: the probe that no second cast follows a Vendetta refresh; the shield's `damage_bound` (and heal worth)
  ignores removal; camps woken onto a stunned enemy.

## Open phases

- **4a, retreat.** `want_home` still decides to retreat; the search plans the turn with every enemy in reach at full
  damage, plus life + bag where that could kill us, and home progress around `Safety::avoid()`. `retreat()` keeps
  tributing first when safe and keeps setting `claim` and `banking`; `dash_away`, `flee_camps` and `retreat_step` go
  on these turns. Lost 40.8% at the real budget but 52.6% at 100M: the retreat search (mean 21.6k, max 83.5k) must
  get cheaper first. Branch `orch/strike-p4a-wt` bdb5902 holds an untested partial fix.
- **4b, chase** (on 4a, `orch/strike-p4b` 6997211, untested). `prey()` still picks the target; the search plans the
  turn with `prey`'s attack tiles as the goal field and the normal step value. `dash_to_attack` and the fixed step,
  attack, reset, cast order go.
- **5, one danger model.** Folding `want_home`, `step_guard` and `prey` into the search (TODO 3; the overlaps are in
  [FUEL-PROFILE.md](FUEL-PROFILE.md)) must carry everything they decide: the low-health retreat and its
  `finishing_camp`/`holding_capture` exceptions; the pack zone; `camp_trapped` with siege limits; pursuit beyond reach;
  Cassi and Issac's linked death; `paying_soon` and `own_ground`; enemies seen beyond strike reach. Fights at leaves
  need health in the fight memo key. A step guard folded into the search showed no gain in three runs (EXPERIMENTS
  Fights).

## Not in this plan

Farming tactics through the search; one currency for our health and enemy health; a cast's cooldown priced by next
turn's strike; allies finishing a foe before its next turn; stunning awake camps that hit us; valuing camps woken onto
enemies.
