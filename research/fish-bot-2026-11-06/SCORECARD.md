# Fish fidelity scorecard (round 1, agent B, 2026-11-06)

`tools/fish/scorecard/` computes the same ~110 behavioural statistics on Intercontinental Fish's ladder replays and on local
games where a chosen bot plays Fish's role, then ranks the metrics by how far each bot is from Fish. Definitions follow
[FISH_MODEL.md](../fish-2026-11-05/FISH_MODEL.md). Every metric's code is in `metrics.py`, and its label and FISH_MODEL
figure are in `metric_defs.py`.

Full tables:
- [scorecard-control.md](scorecard-control.md): Fish against frozen astraeus.
- [scorecard-fish-r1.md](scorecard-fish-r1.md): Fish against round-1 `bots/fish` and astraeus.
- `.json` siblings of both.

## How to run

```
source /home/ubuntu/venv/bin/activate
py tools/fish/scorecard/run.py fish --name fish-r2          # play, decode, score, compare: ~7 min
#   -> replays/fish-scorecard/fish-r2/scorecard.{md,json}
py tools/fish/scorecard/run.py BOT --name N --opponent variants/astraeus-37e1eb6 --control control-ast37 --out PREFIX
py tools/fish/scorecard/compare.py --candidate N --control control-ast37 --out PREFIX   # re-compare existing datasets
```

- `run.py` first plays BOT against `--opponent` on the 128 ladder maps (`maps/*.map26a`), both sides, 256 games. It uses
  the fast runner and the shared slot pool, with no `--threads`.
- It then runs `build.py local N`, `metrics.py N` and `compare.py`.
- **A changed bot needs a new `--name`.** Datasets, batches and `metrics.json` are reused when they exist; `metrics.py
  --force` recomputes the metrics.
- **Runtime of one run** (fish-r1, 2026-11-06, box busy): games 73 s, decode about 5.5 min (actor perspectives about
  50 s a side, observer caches 80 s, rows 40 s), metrics 20 s, compare 2 s. Total 417 s.
- The Fish column is computed once: `build.py fish` (observer caches, 1 min) and `metrics.py fish` (about 2 min).
- Disk: about 3 MB a game, all under `replays/fish-scorecard/` (gitignored).

### Pipeline

| Step | Tool | Output |
| --- | --- | --- |
| manifest | `build.py local N --batch DIR [--bot-index 0 \| --bot NAME]` | `N/{A,B}/manifest.json`: one part per side of the bot in Fish's role |
| actor perspectives | `tools/fish/extract.mjs`, unchanged | `N/{A,B}/actor/` |
| observer caches | `tools/fish/team_decode.mjs`, unchanged; `scorecard/obs.mjs` | `team/`, `obs/` |
| rows | `engage_rows.one`, `combat_data.main`, `combat_tiles.main`, unchanged | `engage-rows-v1`, `combat-v2`, `tiles-v1` |
| metrics | `metrics.py N` | `N/metrics.json`: per-game counters |
| table | `compare.py` | md and json |

`obs.mjs` is `farm3_decode.mjs`'s per-round snapshot plus three things: emblem formations, deaths during the camp phase,
and end-of-game engine statistics.

**How local replays differ from ladder downloads.**
- A local batch has no `group.json` and no team names. The side comes from `results.json`'s `order`, and the file
  suffix gives it too (`-12`: bot 1 is team A).
- A mirror match writes byte-identical replays for both sides. Every cache is keyed by replay hash, so a batch is split
  into side parts A and B, each with its own caches.
- The Fish column reuses the cohorts' existing actor caches, team caches and row files (`replays/fish-{seventh,fifth,sixth}`,
  `fish-team`, `fish-engage/team-seventh`, `fish-engage/*-rows-v1`, `fish-combat/*`). All of them were built by the same
  unchanged code.

### Reading the table

- **gap** is the distance from Fish on an effect-size scale. Proportions use Cohen's h = |2 asin √a − 2 asin √b|; levels
  (counts, gold, rounds) use |ln ratio|. 0.2 is small, 0.5 medium, 0.8 large.
- **ratio** = candidate gap / control gap. Below 1 means the candidate is closer to Fish than astraeus is.
- **Fidelity** = 100 × the mean over the 106 core metrics of (1 − min(gap, 0.8)/0.8). Per-champion metrics are listed
  but not counted.
- `*` marks a difference beyond 2 bootstrap standard errors of the Fish−bot difference (games resampled); `~` one
  within that.
- `ref` is FISH_MODEL's own figure. It is a check on the Fish column: it matches within a few points almost everywhere.
  Departures are by definition: `bush_tie` uses a 3-turn goal; `ward_d2` counts from the placer's tile; the waker
  proxies differ.

### Metrics

| Group | Metrics (ids) |
| --- | --- |
| §6 turn budget | `budget:{dead,home,tribute,fight,clear,capture,recall,wait,approach,travel,idle}`, overall and per champion (farm3_describe's activity classes) |
| §7.1 grouping | `nearest_ally` (median), `ally_within4`, `centroid_spread`, `pair_dist`, `team_within8`, `side_{own,mid,enemy}` (off-spawn turns), `pay_{own,middle,enemy}` (payout location) |
| §7.1/7.5 farming | `pay1k` (payouts per 1,000 rounds per champion-game: median, mean, per champion), `pay_single`, `pay_groups`, `solo_clear:{Wolf,Elk,Golem,Monolith}`, `wake_alone` (+ per camp type) |
| §8 economy | `spent`, `shards`, `has_emblem`, `first_emblem` (per champion too), `trib_bag` (median bag at a tribute start, per champion), `tribute_start`, `recall_start`, `recall_survive`, `keep_rate`, `keep_rule` (timer-1 rule), `home_gate`, `home_reason_hurt` |
| §5 priority | `prio_rank_ok` (base-health rank residue), `prio_mode_agree` (selector §5.3), `prio_quiet_exact`, `prio_dead_ok`, `prio_write_repeat`, `prio_mode:{quiet,late,contact,early,other,unset}` |
| §9-10 combat | `kills`, `deaths`, `camp_deaths`, `camp_death_share`, `enemy_in_sight`, `contact_hit`, `engage_rule` (+m2/m1/r), `engage_rate:{m2,m1,r}`, `kill_override`, `chase_rule`, `chase_rate`, `basic_minehp`, `basic_champ_first`, `reset_use`, `spell_when_still`, `stand_to_cast`, `hor_shield_rule`, `cassi_stun_on_cd`, `momentum`, `range_close`, `campcont_rule`, `campcont:{none,far,d8..d4,d1-3}` |
| §12 wards and bushes | `ward_rate:{contact,enemy,none}` (ward ready), `ward_per_turn`, `ward_bush`, `ward_d2`, `bush_tie:{contact,enemy,none}` |
| outcome | `win`, `final_round`, `reach_2000`, `gems300`, `gems600`, `gold300`, `gold600` |

The rule-agreement metrics score each bot by its agreement with Fish's frozen rule on the same kind of opportunity. A bot
that follows the rule scores Fish's rate (for example 73.9% for positioning), not 100%. They compare like with like and
are the most useful.

## Fish against astraeus (the control)

- Fish: seventh + fifth + sixth cohorts, 412 games.
- Control: `bots/variants/astraeus-37e1eb6` in Fish's role in an astraeus-37e1eb6 mirror, 256 sides of 128 distinct
  games.
- **Control fidelity: 70.1.**

The 15 largest core gaps (all beyond 2 SE):

| # | metric | Fish | astraeus | gap |
| ---: | --- | ---: | ---: | ---: |
| 1 | `prio_dead_ok` dead turns at the dead level | 100.0% | 0.0% | 3.14 |
| 2 | `prio_quiet_exact` exact quiet priority value | 98.7% | 0.0% | 2.91 |
| 3 | `prio_mode_agree` priority mode follows the §5.3 selector | 98.3% | 1.1% | 2.67 |
| 4 | `prio_mode:quiet` turns in quiet mode | 92.3% | 0.0% | 2.58 |
| 5 | `prio_mode:other` priorities outside Fish's encoding | 0.0% | 83.8% | 2.31 |
| 6 | `prio_rank_ok` base-health rank residue | 99.9% | 16.2% | 2.26 |
| 7 | `cassi_stun_on_cd` Cassi stuns while her damage spell cools down | 99.3% | 45.7% | 1.49 |
| 8 | `camp_deaths` deaths to camps per game | 1.17 | 0.31 | 1.32 |
| 9 | `keep_rate` recall still kept at timer 1 | 45.0% | 93.8% | 1.17 |
| 10 | `home_gate` h ≤ 0.63 or gold ≥ 30 at a completed recall | 98.3% | 63.9% | 1.03 |
| 11 | `bush_tie:enemy` bush step among equal-progress steps, enemy farther | 88.9% | 48.0% | 0.93 |
| 12 | `keep_rule` timer-1 keep rule | 90.0% | 50.1% | 0.92 |
| 13 | `win` win rate (different opponents) | 86.2% | 50.0% | 0.81 |
| 14 | `bush_tie:contact` bush step, enemy within 5 | 83.6% | 52.0% | 0.70 |
| 15 | `solo_clear:Golem` Golem clears done solo | 2.3% | 22.1% | 0.68 |

Next, ranked 16-35:

| metric | Fish | astraeus | gap |
| --- | ---: | ---: | ---: |
| `camp_death_share` | 22.8% | 3.4% | 0.62 |
| `deaths` / game | 5.15 | 9.16 | 0.58 |
| `bush_tie:none` | 74.8% | 49.8% | 0.52 |
| `solo_clear:Elk` | 9.7% | 28.4% | 0.49 |
| `basic_minehp` | 94.0% | 79.3% | 0.45 |
| `prio_mode:contact` | 4.8% | 16.2% | 0.38 |
| `gems600` | 576 | 399 | 0.37 |
| `campcont:far` (enemy > 8) | 87.7% | 96.5% | 0.34 |
| `campcont:d1-3` | 18.3% | 30.6% | 0.29 |
| `nearest_ally` median | 3 | 4 | 0.29 |
| `gold600` | 4,354 | 3,287 | 0.28 |
| `kills` / game | 8.6 | 6.57 | 0.27 |
| `ward_rate:contact` | 8.8% | 3.2% | 0.24 |
| `ward_bush` | 83.3% | 73.4% | 0.24 |
| `solo_clear:Wolf` | 30.0% | 40.3% | 0.22 |
| `ally_within4` | 65.7% | 55.4% | 0.21 |
| `wake_alone:Wolf` | 61.2% | 70.3% | 0.19 |

Largest per-champion gaps (not in the fidelity number):

| Champion | Fish | astraeus |
| --- | --- | --- |
| Willow | 2.8 payouts / 1k rounds; 4.9 shards; 2.7 payout groups | 9.7; 12.5; 5.2 |
| Marcella | 86 shards; first emblem round 80; 18.6 payouts / 1k rounds | 41; 140; 12.6 |
| Issac | 4.8 payouts / 1k rounds; 7.9 shards | 8.7; 14.8 |
| Vesper | 23.3 payouts / 1k rounds | 16.1 |

**Close already** (gap < 0.1):
- Most of the turn budget.
- Payout location; payouts per champion-game overall; distinct groups.
- Momentum (70.9% against 67.6%) and `range_close`.
- Contact hit rate; ranged engage rate; `basic_champ_first`; `campcont_rule`; `stand_to_cast`.
- Tribute rate; first-emblem median; ward placements per turn.

**What this says `bots/fish` must move, in order:**
1. **The priority encoding** (§5). astraeus's priorities are not Fish's at all.
2. **Recall handling** (§8). Fish cancels at timer 1 most of the time (keeps 45%): it holds prepared recalls several
   turns while waiting, then gates the last keep on h ≤ 0.63 or gold ≥ 30. astraeus keeps 94% of the channels that reach
   timer 1, and goes home outside the gate a third of the time.
3. **Cassi's stun** on her damage cooldown, and **min-EHP basic targets** (79% against 94%).
4. **Gold concentration on the carries** (per-champion shards and payouts): Marcella and Vesper collect, while Willow,
   Issac and Cassi clear and leave.
5. **Big camps as team clears.** Golems and Elks are solo 2-10% for Fish against 22-28%. Fish also wakes groups
   alone less often: 61% against 68%.
6. **Bush pathing** (a 74-89% tie-break against astraeus's 48-52%) and **wards in contact** (8.8% against 3.2%,
   78-83% on bushes).
7. **Camp exposure and camp hitting near enemies.** Fish dies to camps 1.2 times a game (23% of its deaths) against
   0.3, and its opponents may cause part of that. It stops hitting camps sooner once an enemy is in sight: it keeps
   hitting 18% of the time with the enemy within 3 (astraeus 31%), and 88% with the enemy beyond 8 (97%).
8. **Grouping**: nearest ally median 3 against 4, within 4 in 66% against 55%. This is the user's "Fish groups closer";
   the gap is real but moderate.

## Round-1 `bots/fish` (candidate)

Agent A's bot, frozen mid-round as `replays/frozen/b96d6792f9d9/fish` (2026-11-06 02:38), against astraeus-37e1eb6:
**25.8% wins** (66/256), **fidelity 75.2** against astraeus's 70.1. It is closer than astraeus on 46 of 106 core metrics.

- **Fixed** (gap now ≤ 0.1):
  - priority: dead level 100%, quiet exact 99.6%, mode agreement 99.4%, rank residue 100%;
  - home gate 99.4%.
- **Overshoots Fish**: keep rule 99.4% against Fish's 90.0%. Fish's rule is fitted, and it keeps less exactly.
- **Still astraeus-like** (ratio about 1):
  - recall `keep_rate` 93.4% against Fish's 45%;
  - Cassi's stun on cooldown 49.9%;
  - bush tie-break about 50%;
  - `basic_minehp` 79.4%;
  - solo Elk clears 24%, Golems 13%;
  - grouping: nearest ally 4, within 4 in 53.6%;
  - camp deaths 0.25.
- **Worse than astraeus**:
  - win rate 25.8%;
  - kills 4.6 / deaths 11.1 a game, against 6.6 / 9.2;
  - gold by round 600: 2,766 against 3,287, with fewer shards;
  - kill override 90.6% against 94.8%;
  - ranged engage rate 53.2% against 60.8%.

These are round-1 changes: the draft, shop, priority and recall gate. The combat chunk is not in yet.

## Caveats and known limits

- **Opponents differ.** Fish's games are against top ladder teams. The local columns play astraeus-37e1eb6.
  - Outcome metrics are not comparable across columns: win, gems and gold by round, kills and deaths, and probably camp
    deaths.
  - Neither is anything driven by enemy behaviour: enemy-in-sight share, contact frequency, `side_*`.
  - Use them to compare candidate with control, not with Fish.
- **Rosters differ.** Per-champion and kit-specific metrics only count bodies that exist. astraeus drafts Ryth, Prism and
  Willow often, and Vesper and Vendetta less.
  - `cassi_stun_on_cd` and `hor_shield_rule` sample only games with Cassi or HoR.
  - Pooled metrics such as `pay1k` and `trib_bag` mix rosters. Read the per-champion lines when drafts differ.
- **The mirror control has 128 distinct games.** Both sides of each count, as parts A and B.
- **Approximations.** Each is applied identically to both sources.
  - `keep_rule`'s payout-round branch is a proxy: the previous turn stood on the same group while it was empty.
  - `camp_deaths` counts deaths during the camp phase.
  - `bush_tie`'s goal is the tile three turns later, with ally and enemy tiles excluded and camps not excluded.
  - `ward_rate`'s readiness comes from the actor's own placements (10-round recharge).
  - The waker is the first Fish camp hit on a fully asleep group, from `team_decode`. Ground spells that are not aimed at
    a camp tile are missed.
  - Contact level j and the early mode are not checked; contact and early only count as modes.
  - The `engage_rule`, chase, reset, spell and shield metrics run `combat_rules.py`. That code is COMBAT.md's version,
    checked on the sixth cohort; the MICRO-era refinements are not in it.
- **An independent read-only audit** (subagent, 2026-11-06) found ten problems, and nine are fixed. They concerned the
  recall and tribute denominators, `campcont_rule` rows with no enemy, the keep rule's payout branch, priority 0 read
  as unset, the waker test, the bush split, the priority view on turns without a write, cluster members in the contested
  test, and ward tracking.
  - After the fixes the Fish column matches FISH_MODEL: keep rule 90.0% (ref 90.6), recall survival 4.6% (3.8),
    `campcont_rule` 79.8% (80.8), dead level 100%.
  - Not applied: momentum still extrapolates any previous move, where the original uses a single king step. Fish reads
    70.9% against the ref's 70.8%.
- **Not covered yet**:
  - camp choice (the §7.2 logit) and holder rank and entry (§7.4);
  - tribute-trigger rule agreement (§8.3) and the walk-or-recall rule;
  - unit-spell targets, dash landings and spacing end tiles (§10.7-10.8);
  - first capable actor kills (§10.9);
  - Willow's heal rule, locks and teleports.
  - The existing tools (`farm3_evaluate.py`, `micro_*`, `tactic_*`) compute these. Wiring them in means building their
    rows (`micro_rows` needs `micro_decode` observer caches) for a local part, the way `build.py` does for the engage and
    combat rows.
