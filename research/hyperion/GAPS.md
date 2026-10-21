# hyperion: gaps against hecate-v8

Where main stands against `baselines/hecate-v8` and what to change, from the cumulative-1 A/B (main 108eb9a, 1094
games: ladder 70, gen 512, fresh gen-s1 512, both sides). Since then farm-s1, strike-fuel and strike-p2 landed, each
level (EXPERIMENTS.md), so the picture stands. Scripts and outputs: `replays/orch/research/` (`gaps_breakdown.py`,
`gl_*.py`, `champ_*.py`, `gc_*.py`, `ward_churn.py`, `wf_trace.py`, `gw_idle.py`).

## Where main stands

- **56.1%** (614-480, 95% CI 53.2-59.0): ladder 57.1, gen 56.6, fresh 55.5; team A 58.1, team B 54.1.
- Map pairs: 146 won on both sides, 79 lost on both, 322 split (the composition decides those).
- Weak presets are enclosed or sparse: fortress 1/8, lanes 2/8, caves and maze 4/12, sparse-camps 6/16, cells and
  tunnels 10/24. Ladder maps lost 0/2: 00contest, 00expanse, 00pilgrimage, 00reverse-spiral, 01corridors.
- Out-of-fuel turns 6077 against 1839 (3.3x), Heart of Ruin 58% of ours (3.65 a game against 0.97). Strike-p2 added
  another 12.5% since.

## Where it loses

1. **Composition tables measure matchups, not piloting.** Heart of Ruin, Ren, Stellar is 7/39 for main and 11/39 for
   v8 with the same picks; paired by champion on the same maps, Stellar and Ren play level (Stellar deaths 1.7 vs 1.7,
   gems 134 vs 126) and main's lift over v8 with Stellar, Ren and Heart of Ruin (+10 to +13 points) is its average.
   Judge piloting on lost-both and won-both pairs.
2. **The first champion death decides** (as EXPERIMENTS' General notes): main wins 41.2% when it dies first, 67.5%
   when v8 does. Main's first deaths are in worse fights: outnumbered 41% (v8 34%), its own team struck first 44%
   (v8 38%), two or more attackers 64% (v8 58%). Lone champions picked off in tunnels and labyrinths.
3. **Economy on lost-both pairs:** level gems at round 150 (65 vs 68), apart by 300 (143 vs 164); captures 62 vs 71 a
   game; v8 steals 56 gems a game in main's losses against 36. Monoliths: main did more damage (1189k vs 1093k) but
   captured fewer (40 vs 58); big groups woken and left to sleep again (archipelago, 00contest).
4. **Clearing deaths** to camps, ~1.2 a game each, 80% with no enemy within 5; Stellar the top victim.
5. **Shard choice.** `main_stat` (bot.cpp) builds Stellar on Strength 70%, Prism 69%, Heart of Ruin 77%; every ladder
   team, our own Pantheon submission included, builds Stellar and Prism 76-90% Focus. Its test assumes a basic attack
   every round; main's champions basic-attack on 18-21% of alive turns and cast at ~30% of the cooldown maximum.
   Measured damage per shard (single target): Stellar Focus/Strength 1.37, Prism 1.55, Marcella 0.99, Tavi 0.49.
   Prism is an exact tie (8 x 2.5 against 8 x 2.5) that goes to Strength; Heart of Ruin's landing is left out of the
   sum although `raw_output` counts `lands()`.
6. **Stellar's nuke** is cast on 25.5% of turns where it is ready with a seen enemy within 4 (Cassi with the same slot
   54.6%, ladder Stellars 58-70%); 89% of the misses are walks. `keep_walk_value` 250 (abilities.cpp) applies while
   carrying, and the nuke does 140 at base Focus, so the Strength build can never clear it.
7. **Wards churn.** Every ward is now on a bush, but 97% of bush wards end replaced by another bush ward (v8 57%), 59%
   within 20 rounds, and 32% ping-pong back to the previous cluster (camp to altar and back).

Ruled out as deciders: bag losses (~3 gems a death), denied tributes (0.3-0.5 a game each), out-of-fuel turns by
themselves (55.9% with none, 53.2% with 5-14; 2% of deaths follow our own out-of-fuel turn within 4 rounds), and idle
turns: all are on our own spawn, and the gap is one idle turn per extra death (slope 1.0 over 1094 games), the
respawn turn.

## Proposals, ranked

### Build now (outside the owned areas)

**1. Main stat by counted use (M; bot.cpp, bot.h).** Count, per champion over the game, the basic attacks made and the
damaging casts per slot (damage kind or `lands()`, as `raw_output` counts). `main_stat` picks Focus when Focus growth
x Σ(multiplier x casts) beats Strength growth x attacks, and keeps today's test until both counts are non-zero. Count
at the end of `act()` from our own state (a slot's cooldown restarted this turn; the attack spent without a ranged
walk, a reset adding one), so no owned file changes. The stat can now change mid-game, so a begun emblem is finished
first in whatever stat it was begun. Shared-gem and Ren rules stay. Rests on the measured attack and cast rates and damage
per shard (item 5), no new constant. Past record: "Focus builds (−4)" (2026-10-18) and Fish's build table lost; both
were fixed per champion, before the week-2 stat patch and Heart of Ruin, and this decides from each game's own rates.
In the real draft it moves Heart of Ruin (borderline either way) and Stellar on 5-pick maps; the test-draft A/B
weighs every champion. Watch: shards bought per stat by champion, champion damage per alive turn.

**2. Ward at turn start, second shot (S-M; bot.cpp).** The w2-ward-early A/B tested nearly nothing: at turn start we
are still channelling the recall `start_recall` began at the last turn end, so `place_ward`'s `channelling()` guard
refused all 39,946 traced turn-start calls (6 games). Place it in `decide` right after `continue_recall` has
cancelled the recall (ward and recall share one channel, so this is the earliest legal point), then observe and
refresh Safety before the strike. In that call read only bush clusters already found, else leave the ward to the
turn-end call, which stays. Drop the main.cpp hook. Rests on `wards.vision` (probe-ward-sight) and `channelling`.
Check with `wf_trace.py` that turn-start placements are non-zero before the A/B. EXPERIMENTS' entry blames cluster
growth starving decide; the trace shows at most 4.2k at turn start and the shortcut count 1,122 against 1,997, not
"near 0": correct it with the result.

**3. Replace a ward only when the new cluster watches more (S-M; bot.cpp `ward_bushes`).** WARDS.md proposal 3: score
a cluster by its tiles within 4 of here plus within 4 of our work tile (the claimed group's centre or
`memory.wait_altar`), score our current ward's cluster the same way (0 off a bush), and place only when the best
candidate scores higher. Rests on `wards.rate` and `wards.lifetime` (one ward, never expires, so a placement is worth
V(new) − V(old)) and the churn in item 7. Reads the farm claim, changes nothing in it. Watch ping-pong count and bush
ward life. Touches the same function as 2: build both from main and let the second to land rebase.

### For the strike search owner

4. **Engagements while outnumbered** (item 2): main's first deaths start from worse fights than v8's; chase and the
   search's leaf score decide whether to engage. Measure on lost-both pairs, not composition tables.
5. **`keep_walk_value` while carrying** (item 6): a fixed 250 that no base-Focus spell clears. TODO.md already lists
   replacing `keep_walk`'s logic by a plain threshold; derive it from the walk's value instead (the step's
   `intent.step_value`). Re-measure after 1, which raises Stellar's Focus.
6. **Heart of Ruin's fuel** (fuel-only, byte-identical): 53 of its out-of-fuel turns in 2 traced games are in
   `plan_strikes`, 39 in `chase`; strike-fuel-2 measured ~70k spent before the search on big HoR turns (step_guard
   37k). 20.2% of its turns with the dash ready and an enemy within 3 run out (v8 3.5%).

### For the farming owner

7. **Big groups and Monoliths finished by the one who started them:** waking a group and letting it sleep again
   (archipelago: 4 wakes, 12.4k of 15.8k damage, v8 took it), Monoliths out-damaged but not captured (40 vs 58), the
   last hit lost on 00contest. Captures on lost-both pairs 62 vs 71.
8. **Clearing deaths** with no enemy near (~1.2 a game, Stellar most).
9. **Fuel in siege/farm** (Ren 46, Heart of Ruin 19 traced out-of-fuel turns) and `bankable_bag` (11; `access_fire`
   is already memoised per round, so trace `altar_access` rebuilds before any fix). Fuel-only.

### Not proposed

- Draft changes: the composition gaps are matchups (item 1) and DRAFT.md's search already chose the picks.
- Idle turns, bag losses, locks and tribute denial: measured not to decide games (above).
- More wards or off-bush wards: WARDS.md's data gives them no value.

## Review

Checked against the brief:
- **Scenario rules:** none of 1-3 names a map, preset or situation; each follows from a rule (stat growth, one
  channel, one ward) and a rate measured in play.
- **Unverified claims:** the ward-early bug is read from the code (`place_ward` guard, `start_recall` at every turn
  end) and the trace; the idle cause is measured here. The Focus damage ratios are single-target only, which
  undercounts Stellar's ground spell and Heart of Ruin's landing, so they understate Focus.
- **Rejected before:** Focus builds and the ward-early A/B, each with the new reason given; the periodic ward and
  wake_camps are not revived.
- **Owned areas:** 1 counts at the end of `act()` without touching plan.cpp, abilities.cpp or self_abilities.cpp;
  2 sits in `decide` before the search and changes only what is visible to it; 3 is wards only. Items 4-9 are
  recorded, not built.
