# D: spawncamp (ocean, 2026-11-05)

User's idea (7): "consider camps attackable via standing on top of spawn tiles. this gives us a full heal every
turn. if we can tank a hit from camp (standing in a convenient spot) then we can endure forever and eventually take
it. ofc we have to consider the time asw. [...] reduce testing down to the subset of maps with camps nearby such as
03homonoliths, ofc generated maps asw etc."

## Evidence

- Rules: a turn ended on our own spawn heals to full (rounds.turn_end); enemies cannot enter it; camps never
  regenerate (camps.sleep), so damage on a group is banked; each monster hits the nearest champion in its reach.
- Already in the bot (CHANGES 328): `StandReach` homes, `home_free` / `min_camp_damage` price spawn-stand hits as
  free, `home_stands` in farm and the siege, `mend_hit`. Farm excludes Monoliths (farm.cc `!has_monolith`), and the
  siege takes a Monolith only when the team clears it within `siege_rounds` (64) on Monolith-only maps, or in a
  `burst_rounds` (15) burst elsewhere.
- **Prevalence** (team A's spawn; rough line of sight; `scratchpad/df/prevalence.mjs`):

  | | ladder (128) | ladder-mix 514000-514039 (10,240) |
  |---|---|---|
  | striker within 1 of a spawn tile | 0.8% | 0.2% |
  | striker within 3 (ranged basic) | 4.7% | 4.6% |
  | striker at exactly 4 (unit spells only) | 7.8% | 3.9% |
  | a whole group within 3 | 3.1% | 3.6% |
  | the stand choice changes the fire (min < max over stands) | 0.8% | 0.1% |
  | a Monolith within 3 | 0.8% (03homonoliths) | 0.16% |

  Choosing the stand that minimises fire almost never matters (StandReach already keeps the least-fire stand).
- **How ocean plays the near maps** (oc-base1 = ocean self-play on the 16 ladder near maps; `scratchpad/df/dnear.py`):
  - plaza (Golem at 3, fire 120): cleared every ~80-200 rounds from spawn and around it. Three stands hold ~3
    ranged bodies, about 0.3 gems a body-round, near the normal farm rate (`rounds_per_gem` 2.3): rate pricing
    already weighs the time.
  - treasure-box: its wolves lie between the two spawns, so contested captures are expected.
  - quadrants, yin-yang, membrane: first captures at r12-80, 5-21 captures a game.
  - **03homonoliths**: three Monoliths (60,000 health, 600 gems, fire 600 on the nearest body) touch our 3x3 spawn,
    and all nine tiles are within 3 of one. The group is not touched until r1055, then cleared in ~100 rounds by a
    heavily sharded team (a Vesper hit 539). First home capture r1127-1212, game over r1401 (1200-300). Before
    that the team farms gold clusters. Ladder top teams (both ratings > 2150, 742 games) do the same: median
    tributed 0 at r1400, median end r1487.
- **The gap:** the siege's 64-round gate prices a home siege like a field siege. From our spawn it costs no health,
  and the progress is banked. 4 bodies at base output (~145 a round) clear 60k in ~410 rounds, i.e. the first 600
  gems ~700 rounds earlier than now.

## Design (knobs `params::spawncamp::`)

- `home_siege(world, g)`: g is a Monolith group whose live strikers all have a spawn stand whose fire the sturdiest
  of us outlasts (`home_free(g, team's shortest range, max home_survivable) >= live strength`).
- Siege candidate: off Monolith-only maps such a group counts like a burst or join (`home_siege_any`).
- `siege_ready`: for such a target the limit is `max(limit, home_siege_rounds)` and the team's power is scaled by
  min(1, spawn stands of its live members / bodies alive). The stand count is `home_reach`'s popcount, at the
  shortest range.
- The rest is the existing siege: home stands first (`home_stands`), the low and leave logic, and committing at
  `siege_commit_slack`.
- Knobs: `home_siege_rounds` (0 = off; grid 128, 256, 512, 4000), `home_siege_any` (true).
- **Fuel:** `home_siege` runs per Monolith group per siege call. A static per-group prefilter (a member within 3
  of our spawn's box) returns at once for far Monoliths. Near ones pay `siege_load`, a team loop and `home_free`
  (StandReach is built once a group and range).
- **Expected:** a large gain on home-Monolith maps (03homonoliths is 1/128 of the ladder) and nothing elsewhere.
  The code path only changes where a Monolith is home-free, so other maps' games should be identical.

## Other gaps (E ~5885), judged

- Stand choice: matters on 0.1-0.8% of maps (table above); dropped.
- Spells at range 4 from spawn (3.9-7.8% of maps): a cast every 8 turns (~170-200 damage) for a body that would
  otherwise farm. Small; not pursued unless D1 suggests that home damage is underpriced generally.
- The draft's heal price ignores spawn stands: only matters on the ~4.6% of near maps, through the draft's
  learned model; not pursued.
- Groups with more than 32 strikers: none within 3 of a spawn in the 10,240 maps.

## Results (EXPERIMENTS "spawncamp (ocean, 2026-11-05)")

- **Kept: L512m**, `home_siege_rounds` 512, `home_siege_any` false (`bots/variants/oc-spawncamp-L512m`).
- df-mono: 80.6% of 124. Monolith-only maps 86/90 (L512 with any: 87/90); 03homonoliths won in ~660 rounds.
- Monolith-only is kept because on mixed maps home sieging keeps the Monolith awake while bodies walk through its
  reach (4.1 deaths a game). Level there either way: any on 18/34 and 56/120, off 14/34 and 59/120.
- L 128-4000 make no difference.
- Confirm 50.2% of 20,480; varied 50.1% of 5,118 (the change is local: +0.27 ladder points expected).
- Panel level on full suites; on df-mono 85.2% average against oc-base1's 57.6%.
- Fuel: 52/52 identical at 100M; OOF level at the real budget.

## Round 2 (ocean = oc-fuel4, 2026-11-05)

The user: "surely considering end of turn healing on spawn camps is useful? again start conservatively (see map
homolith). like maybe in the scoring as a coeff". Dev copy `bots/variants/oc-spawn2-dev` (`params::spawn2::`, all
off: bench.py at 100M identical to oc-fuel4, default 16/16 and wide 52/52, total fuel +0.02-0.03% from codegen).
Against `bots/variants/oc-fuel4`, own drafts, fast runner, real fuel. Numbers: EXPERIMENTS "spawncamp round 2
(ocean, 2026-11-05)".

**Dev maps** (round 1's `prevalence.mjs` on fresh ladder-mix 529000-529079): a striker within 4 of a spawn tile on
8.2% of maps (within 3: 4.5%; at 4 exactly: 3.7%); a whole striking group within 3: 3.3%; a Monolith within 3:
0.2%. Subsets: `df2-dev` (1,702 maps: 529000-529039's near maps plus round 1's df-near3 and df-near4), `df2-dev2`
(802, 529040-529079), `df2-mono` (round 1's df-mono and df-monomix: 78 home-Monolith maps with other gems, 44
Monolith-only).

### 1. A home-stand coefficient in farm's value (cut)

- **Design** (`home_bonus` k, `home_bonus_partial`): a group whose live strikers all fire on spawn stands we
  outlast (`home_free` at our range and `home_survivable` covers its live Strength) is worth (1 + k) of itself, in
  the loop's `exposed` factor, so every value and prune of the group reads it; partial: 1 + k x the covered share.
  A static table marks the groups that can ever take it (a striker within our range of the spawn box); every bound
  scales by that most (PreLanes' bounds through a column, `rated_below`, `claim_most`, `altar_below`, and the stop
  search's `beyond` through a per-run flag), so the prunes stay exact. Maps without such a group skip it all.
  Decisions are identical off near maps (24/24 at 100M).
- **Result:** no k gains. On df2-dev: 0.05 48.5%, 0.1 48.0%, 0.25 48.8%, partial 0.1 48.2%, partial 0.25 49.0%
  (SPRT H0 for most). k = 0.001, which changes 1 of 24 near-map games at 100M, read 49.1%: the loss was the bonus's
  fuel (out-of-fuel turns +2.6%), not its value. With the bonus cached per belief version (`B*c`), on df2-devall's
  5,008 games: 0.001 49.6%, 0.1 48.9%, 0.25 49.1%. The value term adds nothing on top of the fuel. CHANGES 328's
  free home fire and round 1's finding stand: rate pricing already weighs the time, and the walk saved is in the
  trip. Higher k was not tried (no positive reading).

### 2. Home Monolith sieges on mixed maps, fixed (kept: `oc-spawn2`)

- `home_siege_any` (round 1's) alone: on df2-mono 61.1% against oc-fuel4 (= L512m), 67.3% on the 78 mixed maps;
  deaths to camps 1.20 a game.
- **`avoid_home_reach`:** while a home Monolith one of us claims is awake (off Monolith-only maps), the work guard
  (`guard_work`, which bank, shop, siege and farm walks honour) bars its reach off our spawn, unless we already stand
  in it off spawn. Bodies that cannot leave without crossing it stay home and siege or wait. With `home_siege_any`:
  df2-mono 63.5%, mixed maps 71.2% (111/156); deaths to camps 0.28 a game. Mixed home-Monolith games end at ~r830
  instead of ~r1300. Monolith-only maps are unchanged (identical games).
- `home_stands_only` (only bodies on a home stand siege; the rest farm, declining the group): 32.0% (the rest walk
  out through the reach); with the avoid as well 54.5%. Cut.
- The per-turn avoid call first cost ~44 fuel a turn on every map (+0.10% total fuel); a static per-map test (a
  Monolith within ranged reach of our spawn's box, `home_monolith_map`) leaves +0.04%, the codegen floor.
- Kept as plain code (no knobs) on oc-fuel4: `bots/variants/oc-spawn2` (= `oc-spawn2-c1`); shipped into `bots/ocean`
  (2026-11-06) with fuel round 6's K1 as `variants/oc-base4`, CHANGES 416 (EXPERIMENTS "oc-base4: CHANGES 416 and 422
  merged"). Full suite df2-full
  49.8% (49.2-50.5) of 20,480, confirm df2-conf 50.0% (49.3-50.7) of 20,480, varied df2-vary 50.4% (49.1-51.8) of
  5,120; the knobs-off dev reads 50.0% on df2-full (the fuel perturbation alone). The change acts on ~0.2% of maps,
  where it wins ~70%: +0.04 points expected, below what full suites resolve.
- Panel (panel-check-514510; oc-fuel4's rates in brackets): astraeus 55.6 (55.6), proteus 58.6 (59.2), demeter
  62.1 (62.6), ocean-td 79.9 (80.5), v67 74.2 (74.8). No member fails (all within 0.6), but the mean is -0.46,
  so PANEL.md's rule 2 is not met; as in round 1, that is noise for a change this local. On df2-mono the panel
  moves from 82.0 / 69.3 / 69.3 / 72.5 / 74.6 to 79.1 / 79.9 / 86.9 / 85.7 / 88.9 (mean +10.6).

### 3. Spells from spawn at range 4 (cut: level)

`spawn_spells` 1: on mend turns, after the mend step, a damage spell (unit or ground, no landing) at a striking
group in reach whose fire on our tile once woken fits `home_room` (`cast_from_spawn`); 2: also at the end of any
turn on spawn without a walk. Rarely fires (19-21 of 24 near-map games unchanged at 100M). S1: df2-dev 50.6%,
df2-dev2 49.3%, df2-devall 50.2% (5,008); S2: 50.8%, 48.4%. Level.

### 4. The draft's heal price and spawn stands

Not tried: it acts through the draft model on the ~4.6% of near maps, and items 1 and 3 found nothing to buy there.
