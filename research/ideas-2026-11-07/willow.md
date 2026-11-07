# Willow: how top teams play it, how ocean does, and the arms (ocean, 2026-11-07)

## Data

- **Archive** (big-arm `.oarena/archive/<day>/data`, copied to `/home/ubuntu/tmp-offload/willow/archive/`): per-unit
  summaries of every platform game. 2026-11-05 is complete (373,215 games, engine 3.0.0); 11-04, 11-06 (from 20:30)
  and 11-07 (to 06:20) hold only the live capture's slice.
- **Replays**, decoded with `tools/replay/extract.mjs`, 16,467 distinct games with a Willow, in
  `/home/ubuntu/tmp-offload/willow/analysis/`:
  - 11-05: every Fish Willow game (2,360); up to 1,200 of each other top-20 team's; all 615 of ours; and 6,000
    random others. From the day's replay zips.
  - capture.db, 11-06/07: 1,699 of ours and 213 of Fish's.
  - ladder-scrim bundles (v78, v80, v81, v82 against Fish and Mite).
- **Scripts**: `/home/ubuntu/tmp-offload/willow/scripts/`. `features.py` writes per-round features of each Willow;
  `report.py` writes the tables (`report.txt`); `unitstats.py` reads the archive's unit stats.

**Version eras** (ours, from `cambc submissions list --json` and the scrim log; the platform labels groups by
the newest submission even while another is pinned):

| Era | Window (UTC) | Notes |
|---|---|---|
| proteus (v72-v75) | to 11-05 22:11, and 11-06 01:29-04:51 | v75 "troll bot" was live from 11-04 15:32, not v76/v77 |
| v76/v77 | 11-05 22:11 - 11-06 ~01:29 | ocean ad32d648; v77's fixed draft (varg, tavi, ren, prism, stellar) has no Willow |
| v78 | 11-06 04:51-11:08 | **v79's one group was played by v78** (byte-identical replays) |
| v80 | 11:08-16:11 | |
| v81 | 16:11-20:51 | |
| v82 | 20:51 on | live and pinned |

The capture holds replays of ours only from 11-06 ~16:00. The v78-v81 rows are therefore scrims against Fish and
Mite, not ladder games. v82 has both: scrims, and 1,039 ladder sides.

## Findings

All figures are per Willow side. "Carry" is the ally (not Willow) with the biggest carried bag, in rounds where it
holds 10 or more. Distances are Chebyshev.

**1. Fish's Willow is an escort, not a farmer.** From the 11-05 unit stats:

| team | Willow camp gems | tributes | gold earned | share of team camp gems | share of monster dmg | healing |
|---|---|---|---|---|---|---|
| Fish | 28 | 1.4 | 177 | 2.8% | 11.2% | 11.5k |
| ours (proteus, 11-05) | 122 | 5.2 | 533 | 12.7% | 14.1% | 9.0k |
| ours (v82, 11-07) | 106 | 4.9 | 301 | | | 9.5k |
| Vvvvv | 104 | 6.4 | 426 | 13.1% | 9.1% | 10.3k |
| other top teams | 21-52 | 0.6-2.1 | 114-310 | 2.2-6.0% | 7.7-17.3% | 8.1-12.8k |

Fish's Willow does its share of camp damage but leaves the captures to the others. Ours takes about four times the
gems and banks five bags a game, as a farmer.

**2. Fish's Willow keeps close to a teammate, not to the carry.** Its median distance to the carry is no smaller
than ours. Fish, mid-game (rounds 251-1000): 11-13 tiles, within 4 of the carry 20-25% of rounds. Ours (v78-v82):
8-10 tiles, 25-35%. What differs is the nearest ally and the count of allies in heal range:

| | nearest ally (median) | allies within 4 | allies within 4, "quiet" (no enemy within 10) |
|---|---|---|---|
| Fish | 2 | 1.4-2.0 | 1.49 |
| top teams | 2-3 | 1.1-1.5 | 1.06 |
| ours, v82 (ladder) | 3 | 1.2-1.3 | 0.93 |
| ours, proteus | 3-4 | 1.0-1.2 | 0.84 |

The gap is in quiet rounds: ours drifts off to farm, Fish's stays beside someone. In fights (an enemy within 6)
all teams converge: within 4 of the carry 35-45%, 1.6-2.0 allies in range.

**3. By situation.** Fish's Willow barely changes position between ahead, even and behind (dCarry 12, n4
1.6-1.75). Its bag grows when behind (7.4 gems against 3.2 when ahead). Ours, in v78-v82, keeps nearer the carry
when ahead (dCarry 7, within 4 33-40%) than when behind (11, 26-28%). Cooked rounds are rare (Fish 2%, ours
v82 ladder 4%, scrims 8-10%).

**4. Abilities.** The heal has a cooldown of 8, so at most 12.5 casts per 100 rounds.

| | heals /100 alive rounds | restored / 3xFocus | restored / game | on the carry | in a fight | heals r1-100 /100 |
|---|---|---|---|---|---|---|
| Fish | 6.6 | 0.56 | 11.8k | 13.5% | 18% | 7.5 |
| top | 3.9 | 0.74 | 10.8k | 26% | 34% | 4.6 |
| ours v82 | 5.2 | 0.61 | 9.9k | 19% | 28% | 5.8 |
| ours proteus | 4.6 | 0.61 | 9.1k | 17% | 22% | 5.8 |

- Fish heals the most often and the earliest, as top-ups (56% of a full heal). Its Willow stays beside the
  bodies that take camp damage, so it restores the most per game.
- Attack resets: 4.5-5.4 per 100 alive rounds for every team, and every one is followed by a hit.
- Willow deaths a game: Fish 0.76, ours v82 ladder 1.03, ours v78-v82 scrims (against Fish and Mite) 1.7-2.4.

**5. Carried bags.** Bags of 15+ gems, by whether Willow was within 4 for half the bag's rounds, split by enemy
contact (an enemy within 4 of the carrier at some point). Without contact, every team lands 93-97% of bags
whether Willow is near or not. With contact, for 15-39 gem bags:

| | landed, Willow far | landed, Willow near |
|---|---|---|
| Fish | 78.9% (n 4,099) | 85.9% (n 1,994) |
| top | 73.2% (16,529) | 80.8% (6,351) |
| rest | 68.5% (21,378) | 75.2% (6,021) |
| ours v82 ladder | 80.5% (2,473) | 83.5% (853) |
| ours v82 scrims | 74.4% (554) | 70.6% (177) |

For 40+ gem bags with contact, the difference is 0-4 points either way. Proximity is chosen, not assigned, so
these are associations.

**6. Winning.** A logistic fit within each group: win on the share of carry rounds Willow spends within 4,
controlling for the tributed lead at the window's start, the rating gap (archive games) and Willow's deaths.
- Rounds 1-250: positive for Fish (+1.21, se 0.33), top teams (+0.40, se 0.13) and our v82 ladder games (+0.99,
  se 0.41).
- Rounds 250-500: Fish +0.89 (0.36), top +0.30 (0.15); our v82 ladder games -0.99 (0.44).
- Rounds 500-800: nothing for anyone.

Each Willow death costs 0.3-1.3 logits, the steadiest term.

**7. How often we have a Willow.**
- On the ladder, v82 drafts Willow in 40-67% of games (hourly, 11-06/07); proteus did in ~25%.
- Locally, ocean's F92 draft in self-play (768 games, ladder and gen) drafts it in 32% of games: 2% of 3-pick, 29%
  of 4-pick and 51% of 5-pick maps.

## What this suggests for the arms

- **Leave the captures to the others (`shy`).** Fish's Willow takes 2.8% of camp gems and ours 12.7%.
- **Stay beside the group in quiet rounds (`follow = 2`).** Fish's nearest ally is at 2 and ours at 3-4.
  Following the carry (`follow = 1`) is the weaker reading: Fish does not do it, though early proximity
  correlates with winning.
- **Heal more often, earlier, for less (`heal_least_scale`, `step_min_share`).** Fish heals at 56% value, 6.6
  times per 100 rounds.
- Situational gates (`gate`: enemy near, ahead, behind) and ablations of ocean's three Willow steps (heal step,
  bank heal step, formation with Prism) as controls.

## Arms and results

Full detail is in EXPERIMENTS.md, "Willow arms (ocean, 2026-11-07)".
- **Following the group is the gain.** On maps where we draft Willow (2x fuel, 10,374 games each), the leash
  matters most: 3 tiles gives 52.2, 2 gives 53.7, 1 gives 53.2. `shy` adds about 0.6 on top: fg2sj 54.3.
- **Weaker or losing arms.** Following the carry: 51.0-52.8. `shy` alone: level. Following only while ahead: lost.
  Heal thresholds alone: lost. Ablating any of ocean's three Willow steps: level.
- **Winner: `variants/ow-fg2sj`.**
  - Held out at the real budget, all maps: 52.1 (51.6-52.5) of 40,960.
  - `--mix varied`: 51.1 (50.2-52.1) of 10,240.
  - Panel: every member up, by +0.6 to +1.8.
- **It moves our Willow towards Fish's.** Nearest ally 3 -> 2 tiles. Its bag 8.1 -> 3.2. Heals per 100 rounds
  5.3 -> 6.4. Restored per game 10.0k -> 12.3k. Deaths a game 1.21 -> 0.89.
