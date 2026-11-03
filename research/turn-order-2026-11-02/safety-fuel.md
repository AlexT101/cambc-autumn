# Cheaper Safety under the worst-case enemy order (`ast-safety`)

Goal: astraeus's Safety under the worst-case enemy order (`bots/variants/ast-pwc`, CHANGES 294's model) at about
REF's fuel, wins level or better. REF is `variants/astraeus-294`. Midway the user tightened the brief: the worst
case is **joint over enemies**. At most m enemies act before our next slot (m = enemy slots ahead of it) in one
order chosen for all, so a tile's bound is each enemy's base blow plus the m largest second-turn increments.

**Outcome.** The joint model is in `bots/variants/ast-safety`, with every fuel fix below, and those fixes are
replay-identical. It did not get cheap.
- REF's fuel would need either a looser bound or a cheaper Reach. Per tile, the joint bound needs every
  contested enemy's widened blow; pwc needed only those of its fixed `first_next` set.
- Out-of-fuel turns: 2.12x REF's on both suite sets (pwc: 1.20-1.22x).
- Wins against REF: 46.6% and 46.9% of 10,240 each (pwc: 50.4% and 51.2%).
- At 100M fuel it plays level: s1, the same decisions, won 49.0% of 2,048.

The loss is fuel, not the model. Not merged anywhere; details and numbers below.

Copies (all `bots/variants/`):
- `ast-safety`: the work.
- `ast-safety-s1`: the joint model before the fuel fixes.
- `ast-safety-s4`, `ast-safety-s5`, `ast-safety-s6`: frozen A/B snapshots (s6 = `ast-safety` now).
- `ast-safety-prof-{pwc,ref,s1}`: census builds of ast-pwc, astraeus-294 and the current ast-safety.

Scripts (`scripts/`):
- `sfuel_instrument.py`: census scopes, plus cumulative `CSUM` lines every 100 rounds.
- `csum.py`: per-component fuel per turn, bot against bot.
- `cen_within.py`: the components inside turns that hold a given one.
- `split_sides.py`: lays out one bot's side of a batch for `census.py`.
- `branches.py`: decide-branch frequencies.
- `same_replays.py`: game-by-game replay identity.
- `joint_overcount.py`: the over-count audit.

## 1. Where pwc's fuel goes (pwc vs REF, 100M fuel, census)

2,048 games, 9.9M turns a side:
- **Fuel per turn:** +1,015 (+2.0%).
- **Turns over 85k:** +3.5%.
- **Turns over 100k:** +7% (2.53% of turns vs 2.36%).
- **At the real budget,** that becomes +22% out-of-fuel turns. A turn just over the line often stays over for
  several turns: a stand-off is expensive every turn, and a turn that runs out leaves the champion where it was.

The growth is diffuse. The pieces:
- `enemy_order` recomputes: 0.41 a turn at ~900 fuel each, 369 fuel a turn (none in REF). They were charged to
  `recall_line`, `damage_ceiling` and `strike_foe`, the first callers after each `World` update.
- `doubles()` called `turns_before_ours`, so `enemy_order`, for each enemy inside `bound`/`damage_bound` sums
  (`damage_ceiling` self +102 a turn).
- More two-turn Reach builds and lookups: `first_next` widens nearer enemies than the stale ranks did. These go
  to `recall_line` (+228), `lethal` (+139), `stand`, `step_guard` and `retreat`.

## 2. The joint worst case: where the old code over-counted

The rules give one order for all enemies. At our next slot at most m enemies can act before us, where
m = `enemies_before(our next slot)`. Enemies surely before it (`latest` slot before ours) take their places first.
Any order of the others is possible.

### Consumers audited (pwc's handling → `ast-safety`)

| Consumer | pwc | Joint? | ast-safety |
|---|---|---|---|
| `threat_strike` widening, Reach `twice` (via `turns_before_ours`) | widened the fixed `first_next` set (≤ m, nearest first) | count yes, worst-for-tile no: a far candidate whose increment beats a near one's at p was never widened | per tile: base + top-`room` increments among the contested (`Safety::pick`); `blow()` gives each enemy its share |
| next-round strike of an enemy outside `first_next` | still struck once (`strike(e, next_turn_round)`), whether or not it can act before us | **no**: every acted enemy got a next-round turn | none before ours (`threat_strike` returns none at 0 turns); it fights from its first turn after ours (`sits_out`: in `lost_mask_`, `arrives_at` 1 in the fight sim, as a stunned enemy) |
| `Bound::doubled`, `damage_bound`/`damage_ceiling(double_unacted)` (retreat, HomeWalk, `recovered_for_work`, support exposure, `mend_step`) | doubled each visible unacted enemy with `turns_before_ours < 2` | **no**: every unacted enemy got a second turn | doubling removed; `blow()` already holds this round's turn plus the joint next-round share |
| `may_escape`, `offer_escape` (turn_order.cc) | blows doubled the same way per enemy | **no** | Safety's joint blows; "unavoidable" = each enemy's base blow (this round's turn) |
| `GuardFoes::exposure` (guard.cc `step_guard`) | its own per-foe Reach sum | as `threat_strike` | contested foes through `Safety::blow` |
| booleans and per-enemy questions (`threatened`, `may_be_hit`, `approach`, `fight_key`, `threats_at`) | per enemy | per-enemy maxima are feasible alone | each enemy's max (`first_next` = mandatory or any candidate while room ≥ 1) |
| `drop_stun`, `abilities.cc` stun proofs (`turns_before_ours == 1` / `!= 1`) | per enemy | per enemy question | unchanged (an enemy's own max) |
| `offer_heal`, `danger` (turn_order.cc) | every enemy gets this round's and next round's turn | **no** | **not changed** (bids, not proofs; left) |
| fight sim (`stand`/`fight_of`) | every enemy may strike first | **no** | **not changed** beyond `sits_out` |

### How often it bit

`scripts/joint_overcount.py` over ast-pwc-dx's SB traces: 2,048 games, 245,351 reads of our turn with 2+ live
enemies within 4.

| Over-count | All 2+ | n=2 seen | n=3 seen | n=4+ seen |
|---|---|---|---|---|
| reads | 245,351 | 135,461 | 41,425 | 14,326 |
| pwc `blow()` sums: next-round turns before ours > m | 43,858 (17.9%) | 16.7% | 26.3% | 39.1% |
| REF (last-read ranks), same | 38,536 (15.7%) | 15.0% | 21.9% | 32.2% |
| `doubled` sums (retreat, HomeWalk, ...): visible enemies > m | **110,187 (44.9%)** | 44.4% | 64.5% | 79.4% |
| widened (second-turn) enemies > m | 0 | | | |

- `first_next` kept the widened count within m. Its two failures:
  - its set, chosen once a turn by distance, need not be the worst set at a given tile;
  - every non-chosen enemy still got a next-round turn: 47,061 excess turns over the 43,858 reads.
- The `doubled` consumers broke the bound in nearly half of all fights and in four of five fights with 4+ enemies:
  193,679 excess turns.
- **Caveat on m.** m is taken from our pre-bid slot. Our own bid can move it at turn end. In 15.7% of reads, more
  of the listed enemies really acted before our next turn than that m. The joint model uses the same pre-bid slot,
  as pwc did.

## 3. Changes in `ast-safety`

The model (decision-changing; the guarantee is kept and tightened to the joint worst case):
- `enemy_order`:
  - `first_next` = mandatory | candidates while room ≥ 1 (each enemy's own worst, for per-enemy questions);
  - `contested` = the candidates when they outnumber `room`;
  - `room` = m − mandatory.
- `turns_before_ours` (top, from `first_next`) and `base_turns_before_ours` (this round only).
- `threat_strike`: no strike at 0 turns. `base_strike`.
- `Safety::blow(e, p)`: `lowered(e, p) ? base_blow : top_blow`. `lowered` = contested and not in `pick(p)`, the
  `room` largest gains at p, where a hit or stun gained ranks above any damage. Unseen threats use the same choice
  (`unseen_blow`, `unseen_at`).
- `sits_out`: a visible enemy with no turn before ours fights from its first turn after ours. It is used in
  `make_slot`, `build_threats` (`lost_mask_`), `fight_reach` and `approach`.
- `double_unacted` doubling removed. `may_escape` and `offer_escape` use the joint blows; `GuardFoes` routes
  contested foes through `Safety::blow`.

Fuel fixes. Each is fuel-only: replays are byte-identical to s1 at 100M fuel, 512 of 512 games, suite fresh-85941
(`same_replays.py`).
- **A. Lazy contested set.** `Safety` no longer computes `enemy_order` when it lists enemies; the contested set is
  worked out on first need.
- **B. `enemy_order` reuse.** It is kept per (round, observations) and computed leaner:
  - bit iteration over settled enemies;
  - closed-form enemy slots instead of `team_slot` / `enemies_before` calls.
- **C. Per-Safety caches.** Each enemy's `turns_before_ours`, `base_turns_before_ours`, `sits_out` and
  sitting-out `fight_reach` (beliefs are fixed for the turn).
- **D. `pick` shortcut.** When no more candidates hit p than the room, it skips the base blows.
- **E. One Reach query for both blows.** `Reach::single_at` returns the first-turn (base) blow from the same query
  as the widened one, so a contested enemy needs one lookup, not two. A one-turn build differs only where an ally
  blocks a first-turn dash that a later dash finds open: `single_exact()` falls back to the base Reach there.
- **F. `pick` memo.** Results are kept by tile (as Reach's), not for the last tile only.

## 4. Results

Fastrunner native, `--no-test-draft`, 512 games a suite with both sides. Out-of-fuel (OOF) turns as `ab.py` counts
them.

| Run | Suites | CAND win % | 95% CI | OOF CAND / REF |
|---|---|---|---|---|
| ast-pwc vs astraeus-294 (`sfx-pwc-A`) | 85900-85919 | 50.4 | 49.5-51.4 | 119,355 / 97,545 (1.22x) |
| ast-safety s1 (joint, no fuel fixes) (`sfx-safety-A`) | 85900-85919 | 45.6 | 44.6-46.6 | 236,256 / 95,127 (2.48x) |
| ast-safety s1 at 100M fuel (`sfx-safety-100M`) | 4 suites | 49.0 of 2,048 | 46.8-51.1 | n/a |
| ast-safety s4 (A-D) (`sfx-s4-dev`) | 85940-85959 | 44.5 | 43.6-45.5 | 238,454 / 95,586 (2.49x) |
| ast-safety s5 (A-E) (`sfx-s5-A`) | 85900-85919 | 46.5 | 45.6-47.5 | 211,049 / 95,864 (2.20x) |
| **ast-safety s6 (A-F, final)** (`sfx-s6-A`) | 85900-85919 | **46.6** | 45.7-47.6 | 205,298 / 96,722 (2.12x) |
| **ast-safety s6, confirm** (`sfx-s6-B`) | 85920-85939 | **46.9** | 45.9-47.8 | 205,883 / 96,916 (2.12x) |
| ast-pwc vs astraeus-294, confirm (`sfx-pwc-B`) | 85920-85939 | 51.2 | 50.2-52.2 | 119,958 / 100,297 (1.20x) |

`tools/fuel/bench.py run --set wide --jobs 94` (52 games against hyperion, 100M fuel; `replays/fuel/sfx-*.json`):

| Bot | Mean fuel/turn | p99 | Turns over 100k | vs REF |
|---|---|---|---|---|
| astraeus-294 (REF) | 54,000 | 114,504 | 2.22% | |
| ast-pwc | 54,799 | 116,117 | 2.41% | mean +1.5%, p99 +1.4% |
| ast-safety s6 | 55,991 | 119,712 | 2.74% | mean +3.7%, p99 +4.5%, over 100k +23% |

The excess sits in champion-games with many out-of-fuel turns (`tools/fuel/oof_bot.py`, `sfx-s5-A`):

| OOF turns per champion-game | s5 | REF |
|---|---|---|
| <10 | 82,505 | 59,625 |
| 10-49 | 104,959 | 30,546 |
| >=50 | 23,585 | 5,692 |

About 80% of the excess comes from champions that run out at least 10 times in a game.

100M-fuel census, ast-safety vs ast-pwc on fresh-85940 (2.4M turns a side):

| | s1 | s4 (A-D) | s5 (A-E) | s6 (A-F, final) |
|---|---|---|---|---|
| fuel/turn over pwc | +1,358 | +848 | +739 | +710 |
| turns over 100k, % (pwc 2.79) | 3.66 | 3.57 | 3.50 | 3.46 |

What's left in s5 against pwc, per turn:
- `pick`: 776 inclusive, 499 self. This is the contested enemies' widened Reach lookups: pwc only looked up
  `first_next`'s.
- Spread through the consumers that call `blow()`: `lethal` +181, `want_home`/`channels` +181, `step_guard` +155,
  `chase` +145, `damage_ceiling` +137, `retreat` +134, `bound` +115.
- `fight_any`/`fight_key` +170: more enemies in `lost_mask_` (sitting out).

On real-budget out-of-fuel turns (census, fresh-85942) the excess sits in fights with 3+ visible enemies:
- **Share of OOF turns with 3+ visible enemies:** 63% for s4, 43% for pwc.
- **Retreat in those turns:** s4 retreats in 0.6 of them, at 30k fuel a turn; pwc in 0.1.
- **Overall retreat rate:** at 100M fuel, both bots retreat equally often (55.98 vs 55.84 per 1,000 turns).
  Retreat turns are dearer in s4, so they run out of fuel more often.

## 5. What's left and why

- **The joint bound costs fuel by nature.** To know which m enemies are worst at a tile, every contested enemy's
  widened blow is needed there. pwc fixed its set once a turn and widened only those. "Fewer enemies widened" holds
  for the sums, but not for the work of choosing them.
  - Fixes A-F (replay-identical) cut it. Out-of-fuel turns fell 11% (2.48x → 2.20x REF), and wins went from
    45.6 to 46.5.
- **Cheaper, still worst case, but looser** (decision-changing; not tried):
  - Pick the m by Strike-table increments (distance only) against the one-turn Reach base, and charge the chosen
    their Strike widened blow. This upper-bounds the joint worst case, at about pwc's lookups per tile. It is more
    pessimistic behind walls.
  - Branch-and-bound on `pick`: upper bound each gain by the Strike widened blow minus the Reach base, and look up
    exact widened blows only while a candidate could still make the top m. Exact up to ties. It needs the one-turn
    base lookup for every candidate, so the saving is unclear.
- **Not joint yet:**
  - `offer_heal` and `danger`: every enemy takes both turns.
  - The fight sim: every enemy may strike first.
  - The unseen this-round term.
  - Our own slot is the pre-bid one (§2 caveat).
- **The amplifier.** At the real budget, out-of-fuel turns grow about 3x faster than turns over 100k at 100M fuel
  (pwc +7% → +22%; s5 about +35%, estimated through pwc, → +120%). Getting near REF needs turns over 100k within 1-2% of REF's at 100M
  fuel. Even pwc's model is not there.
