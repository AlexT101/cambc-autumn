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
