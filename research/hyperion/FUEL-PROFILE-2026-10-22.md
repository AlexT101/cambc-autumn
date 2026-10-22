# hyperion: where the fuel goes (2026-10-22)

Measured on main bbf6f05 (CHANGES 1-59). The map for the fuel-cut batch: which code to make cheaper, which danger
models overlap, and which gates still fire.

## Method

- `tools/fuel/bench.py run hyperion --set wide --test-draft`: 26 maps (12 ladder, 12 `maps/gen`, 2 `maps/gen-s1`), both
  sides, against hecate. Both bots draft ladder top-10 compositions seeded by map and side. 52 games, about 5 minutes
  with 8 jobs.
- Profile: two throwaway copies (`bots/variants/prof-hyperion`, `prof2-hyperion`, not committed). Each has about 85
  scoped meters plus a record of every fight simulation, and prints one compact line per turn.
  - Every meter read and write is inside `debug_block`, so both copies played 52/52 replays identical to main.
  - Meter overhead was about 750 fuel a turn in the first pass and 1.4k in the second (about 28-42 fuel per meter).
  - Shares below are taken against the baseline's per-turn fuel, so they read a few percent high.
- The second pass's output hit the 1 MiB stdout cap in 10 games. It covers 301k of the 315k turns: the first
  1277-1843 rounds of those games, and all of the other 42.
- **"Over 90k"** means play turns, after round 1, that used more than 90k at 100M fuel: 6209 turns, 2.0%.
- **incl** counts a phase's whole call tree. **excl** subtracts the meters opened inside it. The excl column sums to
  100% of fuel.

## Baseline

| wide set, test drafts | mean | p50 | p90 | p99 | max | turns > 100k | out-of-fuel at 100k |
|---|---|---|---|---|---|---|---|
| hyperion bbf6f05 | 35.3k | 32.5k | 55.6k | 106.8k | 452k | 4147 (1.32%) | 1611 |
| hecate (same games) | 31.4k | 28.9k | 51.7k | 95.6k | 395k | 2543 (0.81%) | 279 |

- **JSON files:** `replays/fuel/wide-base-100M.json` and `wide-base-real.json`, in the primary checkout too. Turns
  are counted from round 2, since round 1 has 200k and warms up on whatever fuel is left.
- **Real budget:** mean 35.9k, p99 93.3k.
- **Out-of-fuel turns by map:**
  - gen-chambers-102206117: 682
  - gen-chambers-102106111: 256
  - gen-hourglass-102205812: 254
  - 00contest: 235
  - 00fragment: 43
  - 01hooks: 34
  - gen-dense-camps: 34
  - 00corners: 20
  - gen-huge-shared: 18
  - every other map: 9 or fewer
- **Streaks:** two thirds of the out-of-fuel turns are follow-ons. The 1621 turns form 853 streaks of consecutive
  rounds for the same body: 529 single turns, 143 pairs, and 181 runs of 3-14 turns, which hold 1092 of the turns.
  CHANGES 59 replays a stale round from the start, and the replay runs out again.
- **Turns over 100k at 100M by map:**
  - gen-chambers-102106111: 1232
  - gen-chambers-102206117: 996
  - gen-hourglass-102205812: 779
  - 00contest: 489
  - gen-dense-camps: 168
  - 00corners: 100
  - 00swirl: 80
  - 01hooks: 64
  - every other map: 50 or fewer

## Top level

| phase | all turns: incl % | all: excl % | all: mean a turn | over 90k: incl % | over 90k: excl % | over 90k: mean a turn |
|---|---|---|---|---|---|---|
| world update | 22.5 | 1.4 | 7.9k | 12.2 | 0.4 | 14.2k |
| comms receive + send | 4.1 | 4.1 | 1.5k | 1.0 | 1.0 | 1.2k |
| decide (incl. turn order) | 72.8 | 6.4 | 25.7k | 86.1 | 3.5 | 100.5k |
| warm_reach | 1.2 | 1.2 | 0.4k | 1.2 | 1.2 | 1.4k |
| turn end, prepare, warm-up | 0.4 | 0.4 | 0.1k | 0.1 | 0.1 | 0.1k |

### Inside world update

| step | all: excl % | all: mean a turn | max | over 90k: excl % |
|---|---|---|---|---|
| `update_camps` (per visible member: `test` + `camp_health` + `camp_awake`) | 8.7 | 3.1k | 17.7k | 6.8 (8.0k a turn) |
| `update_champions` (self) | 5.9 | 2.1k | | 2.8 |
| `grow` (unseen enemies' possible sets) | 4.5 | 1.6k | 30.7k | 0.7 |
| `read_priorities` | 1.5 | 0.5k | | 0.6 |
| `rank_turns`, `update_altars`, `update_scores`, `read_vision`, `observe` | 2.7 | | | 1.4 |

`update_camps` costs 8.2k a turn on gen-chambers-102106111, 7.6k on dense-camps, 5.9k on gen-chambers-102206117 and
5.2k on gen-hourglass-102205812. On other maps it is 1-4k.

### Inside decide

| step | all: incl % | all: excl % | when it runs: mean | when it runs: p90 | max | over 90k: incl % | over 90k: excl % |
|---|---|---|---|---|---|---|---|
| `farm` | 25.2 | 0.1 | 15.3k | 24.3k | 123k | 6.1 | 0.0 |
| `farm`: evaluation loop | 12.8 | 11.4 | 8.6k | 14.8k | 67k | 4.1 | 2.6 |
| `farm`: walk after it | 7.8 | 2.7 | 5.5k | 10.5k | 66k | 1.5 | 0.4 |
| `farm`: prelude, then `prices` and `home_trip` | 5.2 | 3.5 + 2.1 + 1.0 | 3.2k | 5.3k | 45k | 0.8 | 0.9 |
| `route` (all callers) | 4.9 | 4.9 | 3.1k | 5.7k | 59k | 0.7 | 0.7 |
| `continue_recall` (73% of turns; holds want_home) | 10.4 | 1.2 | 5.0k | 9.7k | 82k | 10.3 | 0.2 |
| `want_home` | 8.9 | 2.6 | 3.4k | 7.6k | 81k | 21.3 | 3.2 |
| `want_home`: `lethal(here)` | 2.2 | 1.8 | 1.0k | 2.8k | 23k | 4.2 | 2.3 |
| `want_home`: the fight at here | 1.3 | 0.3 | 2.2k | 8.5k | 30k | 6.2 | 0.9 |
| `want_home`: `pursuit` | 1.2 | 0.0 | 5.9k | 13.2k | 29k | 6.1 | 0.1 |
| `step_guard` (1.13 calls a turn when heavy) | 3.0 | 1.0 | 5.7k | 17.5k | 142k | 18.7 | 4.2 |
| `step_guard`: exact tile looks (Reach::at) | 0.8 | 0.1 | 4.0k | 8.9k | 55k | 5.3 | 1.0 |
| `step_guard`: settling fights (sims) | 1.0 | 0.1 | 7.3k | 15.1k | 101k | 8.2 | 0.4 |
| `plan_strikes` (the strike search) | 2.7 | 2.7 | 13.1k | 22.2k | 325k | 15.8 | 15.8 |
| `plan_strikes`: read / grow / price / act | | | 5.9 / 3.2 / 3.7 / 0.5k | | 33 / 302 / 33 / 5k | 5.9 / 5.2 / 4.6 / 0.4 | |
| `strike_after` | 0.6 | 0.6 | 0.2k | | 32k | 0.6 | 0.5 |
| `chase` + `prey` | 3.2 | 1.3 | 5.1k (prey) | 15.2k | 78k | 10.8 | 4.0 |
| `siege` (on 55% of turns) | 4.6 | 0.6 | 3.0k | 6.5k | 33k | 1.3 | 0.1 |
| `siege`: `siege_candidate` (`altars_sealed`, `access_fire`) | 4.0 | 4.0 | 2.6k | 5.4k | 33k | 1.3 | 1.3 |
| `carry_bag` (holds chase and farm) | 8.0 | 2.3 | 15.1k | 28.2k | 83k | 5.0 | 0.5 |
| `retreat` | 2.0 | 1.3 | 12.4k | 20.6k | 74k | 0.6 | 0.5 |
| `set_turn_order` | 3.1 | 3.0 | 1.1k | 2.4k | 30k | 3.1 | 3.0 |
| `wants_shop` | 1.4 | 1.4 | 0.7k | | 18k | 0.3 | 0.2 |
| `find_members` (Safety's camp hits) | 2.4 | 2.4 | 0.9k | 2.0k | 61k | 2.7 | 2.7 |
| heal and shield, wards, camp and enemy casts | 3.5 | 3.5 | | | 46k | 0.8 | 0.8 |

### Spread over many callers (the totals are also inside the rows above)

| item | all: % | over 90k: % | count | cost each |
|---|---|---|---|---|
| fight simulations | 3.4 | 20.1 | 0.23 a turn; 3.09 a turn when heavy (p99 7, max 11) | 5.1k mean, 10.9k p90, 25.5k max; ~400 a half-turn |
| Reach builds | 1.3 | 4.5 | 2.9 a heavy turn (max 13) | 1.6-1.8k |
| Reach::at misses | 1.1 | 5.0 | 13 a heavy turn | ~490 |
| `fight_key` / `fight_key_with` | 1.2 | 4.7 incl | 1.9 a heavy turn | |
| `lethal` (all callers) | 2.2 | 4.6 | 1.5 a heavy turn | |
| Side `fill` (making fighters) | 0.5 | 2.1 | 5.6 a heavy turn | ~450 |
| threat build | 0.8 | 1.0 | 1 a heavy turn | 1.2k |
| `threatened` | 1.4 | 0.2 | | |

### How the simulations end

Over all turns: 72.7k sims, 12.9 half-turns each.

| end | share | fuel each | half-turns |
|---|---|---|---|
| they all fall (`t`) | 42.8% | 4.6k | 12.2 |
| `outlives` exit (`o`) | 25.3% | 3.4k | 5.9 |
| we all fall (`u`) | 20.5% | 5.5k | 15.8 |
| horizon (`h`) | 8.7% (15.9% on heavy turns) | 11.7k (14.4k) | 30.7 (33.6) |
| `overwhelmed` exit (`w`) | 2.7% | 4.9k | 10.1 |

- Horizon-length fights are about 20% of simulation fuel, and about 30% on heavy turns. The exit bounds are checked
  only at the start and when a member falls, so a fight that nobody wins plays all 34 half-turns.
- By side size (allies v enemies):
  - 1v1: 17.5% of sim fuel, 3.3k each;
  - 2v2: 11.6%;
  - 1v2: 11.0%;
  - 2v1: 9.3%;
  - 2v3: 8.2%, 8.8k each;
  - 3v3: 6.4%, 9.9k each;
  - 4v4: 14.3k each.
- Fuel per half-turn grows with fighters: 282 at 1v1, 395 at 2v2, 501 at 3v3, 634 at 4v4.
- By caller: 54k are `fight()` / `new_fight` sims (5.0k each) and 17.6k are `pursuit` sims (5.6k each, 9.8k on heavy
  turns). Only 0.8k are `turns_to_kill_idle` sims.

## The worst turns

- **By champion**, turns over 100k:
  - Heart of Ruin: 1424
  - Ren: 723
  - Varg: 567
  - Ryth: 477
  - Issac: 278
  - Stellar: 260
  - Marcella: 173
  - Willow, Vesper Vale, Vendetta and Prism: 0-26 each
- **By map:** gen-chambers (both seeds), gen-hourglass-102205812 and 00contest hold 81% of the heavy turns. These are
  8-10 champion brawls. On 62% of heavy turns the largest simulation has 5-7 fighters, and on 86% it has 4-8.
- **The strike search makes the very worst turns.** All 25 turns over 260k are Heart of Ruin, Ren or Ryth.
  - 21 of them are Heart of Ruin, with `plan_strikes` taking 110-325k. The 429k turn spent 302k growing the search
    tree (`plan_grow`).
  - 194 of the 244 turns where the search costs more than 50k are Heart of Ruin. Its p99 search is 79k; every other
    champion's is 28-46k.
  - Ren's and Ryth's worst turns are simulations: 7-11 sims for 97-125k.
- **No single cap brings most of the over-100k turns under 100k.** Turns fixed, of 4147:

| change | turns fixed |
|---|---|
| search capped at 30k | 115 |
| search capped at 20k | 326 |
| at most 3 sims a turn | 151 |
| `step_guard` capped at 15k | 936 |
| no `pursuit` | 864 |
| `prey` capped at 5k | 957 |
| every sim half the cost | 1395 |
| search at 30k, sims halved and step_guard at 15k | 2570 (62%) |

## Danger models

Each model below answers some form of three questions: who can hit tile p and how hard, whether we lose a fight here,
and whether we die here. The costs are from the profile above.

| model | file:line | computes | inputs | cost | callers |
|---|---|---|---|---|---|
| `Strike` / `strike()` | safety.cpp:651, 734 | A distance table (0-6) of the most damage or stun on its next turn. Ignores walls and sight. | facts, Strength, Focus, cooldowns | memo hit ~tens | everything below. turn_order.cpp:102 keeps a second, separate cache |
| `threat_strike()` | safety.cpp:766 | Strike widened to two turns when the enemy has two turns before ours | `turns_before_ours` | cheap | Safety foes, `threats_near`, `shield_wanted` |
| `Reach` | safety.cpp:1222, 1384 | Exact 9x9 placement: walk, dash, sight, Varg splash; a 64-entry memo per build | static windows, `live_camp`, recipe cache | 1.7k a build, ~490 a missed tile | `blow`, step_guard's exposure, plan's exact queries, `visible_threat`, `approach`, `shield_if_needed` |
| `Threat` / `threats()` | safety.cpp:1690 | A capped distance field per unseen credible enemy | `possible`, walls | 1.2k a build | `fight_key*`, `worst_damage`, `threatened`, `enemy_area`, `threats_at` |
| `damage_bound` / `damage_ceiling` / `worst_damage` | safety.cpp:1844, 1852, 1885 | Sum of camp hits and blows. The three treat unseen enemies differently. | `each_threat` | per enemy | `lethal`, flee and retreat steps (8-9 tiles), plan `shield_at` and `read_mates`, turn_order |
| `lethal(p)` | safety.cpp:2096 | One-turn kill: ceiling, then bound, then worst (up to 3 passes) | the above | 2.2% of all fuel | `want_home`, step_guard (per guarded tile), plan (end tiles at distance 3) |
| `threats_at` | safety.cpp:1799 | Per-enemy blow at p. For unseen enemies it uses the field when the threats are built, else a Chebyshev bisection, so the answer depends on what ran earlier in the turn. | | | plan (dist >= 2; drops the visible blows it computed), turn_order `offer_channel` / `offer_escape` |
| `threatened(p)` | safety.cpp:1894 | Chance of damage before our turn (recall risk) | forces the threat build | 1.4% | up to 5 times a turn at `my_position()`, not memoised |
| camp hits: `find_members`, `camp_damage`, `camp_area` | safety.cpp:1497, 1873, 1909 | Awake members' hits, cut by nearer champions; the memo holds the last tile only | camp beliefs | 2.4% | want_home `camp_trapped` ring scan, `flee_camps`, plan (`camp_at` re-implements it at plan.cpp:1573), `note_upkeep` |
| fight sim: `fight` / `new_fight` / `simulate` | safety.cpp:1985, 1996, 479 | Sides alternate for 17 turns; they strike first. **No camp damage** (`us.camp` stays 0). Memo of 32 keyed by (enemies hitting p, allies within 4). | fighters made once a turn | 5.0k a sim | want_home (bot.cpp:2210, up to twice), step_guard (2350/2359), prey (2476, up to 8) |
| `pursuit` | safety.cpp:2054 | We strike first; enemies within 3 steps arrive; weighted camp hits. Not memoised. | `approach` (Reach) | 5.6k (9.8k heavy) | want_home only |
| `turns_to_kill_idle` | safety.cpp:2075 | We never act; enemies walk in; camps hit | `approach` | 1.6k, rare | `tribute_safe`, up to 2-3 times a turn at the same tile |
| pack zone: `outmatched` / `pack_covers` | bot.cpp:2015-2168 | Subsets of enemies seen this round, scored by health x output, with a box within 7 of them | no Strike, Reach or sim | once a round | want_home, prey, routing zones |
| `want_home` | bot.cpp:2197 | low health, then `outmatched`, `camp_trapped`, `lethal`, `visible_threat` + fight, then pursuit | all of the above | 21% of heavy-turn fuel | decide, `continue_recall`, `continue_tribute` |
| `step_guard` | bot.cpp:2242 | Tiles a step or dash could end on that want_home would flee. A Strike bound, then a Reach exposure, then a union fight, then fights with the fewest enemies first, with a local dominance cache. | Strike, Reach, fight keys, sims, `lethal` | 19% of heavy-turn fuel | decide (twice when the search moved us) |
| `prey` | bot.cpp:2434 | The best kill whose fight at the enemy's tile is won | `pack_covers`, fight sims | 10% of heavy-turn fuel | chase, `carry_bag`, `continue_tribute` |
| strike search end tiles | plan.cpp:1554-1724 | 0.25 x Strike share, then exact `blow` (capped at 10 queries), unseen enemies via `threats_at`, `lethal` at dist 3, `damage_bound` for shields, guarded tiles dropped, killed and stunned enemies removed. `wake` / `find_wakers` repeat find_members' nearest-champion logic. | Strike, Reach, Threat, guard | 16% of heavy-turn fuel | decide, `strike_after` |
| self_abilities `threats_near` / `danger()` / `shield_wanted` / `shield_if_needed` | self_abilities.cpp:54, 76, 142, 417 | An integer depth score per dash landing. The shield's own visible test and its own camp loop. | threat_strike, Reach | small | dashes, shields |
| abilities `enemy_cast` / `camp_cast` / `keep` | abilities.cpp:206, 362, 432 | One-turn Strike reach, not widened; a third model of camp reach | | small | casts |
| turn_order `offer_escape` / `side_damage` | turn_order.cpp:162, 109 | `damage_bound(p, true)` worked out by hand a third time, with different unseen distances | Strike, `threats_at` | 3% | once a turn |

### Overlaps to fold

1. **"Who hits p, how hard" has four representations.**
   - The four are Strike tables, Reach placement, Threat fields, and the `enemy_area` squares, which are a superset of
     Reach.
   - Unseen enemies get seven treatments: `each_threat`'s d=0, `threats_at` bisection, the field, `most_damage`,
     `threatened`'s fraction, `avoid_within`, and the casts.
   - The Strike-then-Reach gate is written three times: `Safety::blow`, step_guard's `bound`, and plan's share.
2. **The same tile is priced in several passes per turn.**
   - For an end tile, plan runs exact blows, then `threats_at` (repeating the visible blows), then `damage_bound` for
     the shield (repeating them again), then `lethal`.
   - turn_order computes `damage_ceiling` twice, then `damage_bound`, then `threats_at`, all at `self.pos`.
   - `want_home` runs `lethal(here)`, `fight_key(here)` twice, `visible_threat`, then pursuit's `approach` for each
     enemy.
   - step_guard's tiles around here and the search's end tiles are mostly the same tiles, judged by different models:
     a fight sim against a Strike share plus Reach.
3. **"Do we lose or die here" has about seven models.**
   - The models are fight (no camps), pursuit (we strike first, arrivals, camps), the idle sim, `lethal`, the pack
     zone, `tribute_safe` and `offer_escape`.
   - want_home mixes one-turn `lethal` with a multi-turn fight. step_guard uses `lethal(q)` to decide whether a fight
     where we fall counts.
4. **The fight memo is shared only by exact key.**
   - want_home and step_guard share keys. prey keys at the enemy's tile and rarely hits.
   - pursuit and the idle sim have no memo.
   - step_guard's dominance cache (`covers`) is local to one call, and step_guard runs 1.13 times a turn when heavy.
5. **Camp danger has about nine models:**
   - `find_members` and `camp_damage`;
   - plan's `camp_at`;
   - plan's `wake` and `find_wakers`;
   - `threats_near` (full reach, no cut);
   - `shield_if_needed`'s own camp loop;
   - `min_camp_damage` / `finishing_camp`;
   - `camp_cast keep`, `wake_risk`, `landing_wakes`;
   - `CampGroup::threat()`;
   - `access_fire` (bot.cpp:498).
6. **Estimates that only feed gates** can go with the gates:
   - `fight_cost_estimate` (it calls `list_reachable`, which itself spends fuel);
   - `query_cost_estimate`, `build_cost_estimate` and `estimate_build`;
   - `count_champions` and `costliest_*`;
   - step_guard's static `costliest`;
   - `search_cost_estimate` in prey.
7. **`fight_key` forces the full threat build.** That includes a distance field for every unseen credible enemy, even
   when only visible enemies can reach the tile.

## Fuel shortcuts at the real budget (wide set, 308.7k turns)

| tag | fires | per 1k turns | where it fires |
|---|---|---|---|
| step-guard (3 sites) | 5690 | 18.4 | chambers x2, hourglass-s1, contest |
| prey-cut-short | 5207 | 16.9 | same |
| home-no-pursuit | 4817 | 15.6 | chambers, hourglass-s1, boss-battle, city |
| farm-partial-evaluation | 4458 | 14.4 | everywhere, ambush 206 |
| comms-stale-vision | 2787 | 9.0 | everywhere |
| ward-no-bushes-fuel | 2568 | 8.3 | fight maps |
| turn-order | 1427 | 4.6 | |
| farm-no-route | 385 | 1.2 | |
| static-descend | 254 | 0.8 | |
| siege-route-fuel | 96 | 0.3 | |
| farm-kept-target | 95 | 0.3 | **also 21 at 100M**: it is a no-approach fallback, not only a fuel gate |
| crow-flies-farm | 72 | 0.2 | open-field 22 |
| ward-no-bushes-clusters | 30 | 0.1 | |
| farm-no-attack-tiles | 5 | | |
| siege-no-tiles, spell-clear-no-tiles, fight-cut | 1 each | | almost dead |
| home-no-fight-sim | 0 | | **dead** on this set |
| out-of-fuel | 1611 | 5.2 | every one in `decide` |

The untagged gates (step_guard's `act_reserve`, the `late_floor` skips in main.cpp, warm_reach's floor, and the
`prepare_walk` floor) are not counted here.

## Ranked cuts

The percentages below are of all play fuel unless marked heavy, which means turns over 90k. The estimates assume the
cut code costs half of what it does today, unless a line says otherwise.

1. **The strike search on Heart of Ruin.** Up to 325k on one turn (302k growing the tree), and 15.8% of heavy-turn
   fuel.
   - Bound the landing/node growth, or merge equal landings earlier. This takes the worst turns from 300-450k to
     about 150k, and cuts heavy-turn fuel by 5-8%.
   - Part of it may be byte-identical (dedupe); a hard bound is a behaviour change and needs an A/B.
2. **The fight simulation's cost.** 20% of heavy-turn fuel; halving it would fix 34% of over-100k turns.
   - (a) A cheaper `act()`: ~400 a half-turn, rising to 634 at 4v4 (TODO 2).
   - (b) Check the `outlives` / `overwhelmed` exits every few half-turns, not only when a member falls. Horizon fights
     are 20-30% of sim fuel. EXPERIMENTS records an older "stalemate early-out" as no gain, but that was before the
     exact exits of CHANGES 48. Re-measure it.
   - Estimate: -8 to -10% heavy-turn fuel. Byte-identical is possible: the exits are exact, and the
     FIGHT-EXIT-MISMATCH check covers them.
3. **The farm evaluation loop.** 11.4% of all fuel on its own, 8.6k a farm turn, and 10k a turn on gen-classic. Plus
   the prelude, `prices` and `home_trip` (6.6%) and the walk (2.7% plus route's 4.9%).
   - It visits every group each farm turn. Sub-profile the per-group reads (centre field `at()`, `allies_on` tests,
     `drafted_spawn_steps`), then hoist, cache or bound them.
   - Estimate: -5 to -8% of mean fuel. Byte-identical is possible if the visit order and ties are kept.
4. **The world update.**
   - `update_camps` is 8.7% (3k a turn, 8k on camp-dense maps): three host calls per visible member each turn.
     Re-measure the two occupancy boards against per-member reads on dense maps, and skip members whose reads cannot
     have changed.
   - `update_champions` and `grow` are 10.4%. `read_priorities` is 0.5k every turn.
   - Estimate: -3 to -6% mean. Byte-identical is possible.
5. **`step_guard` and the search's end tiles judge the same tiles twice.** 19% plus 16% of heavy-turn fuel.
   - Byte-identical: keep the settled keys and exposures across its two calls a turn, and widen the Reach memo, which
     has 64 entries keyed by the low 3 bits.
   - Then fold the guard into the search's end-tile pricing, or the reverse. That is the "one danger model" batch and
     a behaviour change that needs an A/B.
   - Estimate: -5% heavy-turn fuel byte-identical, -10 to -15% folded.
6. **`want_home`'s pursuit.** 6.1% of heavy-turn fuel, and removing it would fix 864 over-100k turns.
   - Skip it when `fight(here)` was won and the conditions in EXPERIMENTS Fuel (2) hold: no camps at here, nobody
     still walking in, and no linked body falls.
   - Making `fight()` count camps (`us.camp`) would let pursuit and fight share one model.
   - Behaviour change, needs an A/B. Estimate -4% heavy.
7. **`siege_candidate` on every farm turn.** 4.0% of all fuel, 2.6k a call on 55% of turns. `altars_sealed` reaches
   `access_fire`, which tests every open tribute tile against every stirring group, memoised for one round only.
   - Memoise it on (access version, stirring groups' camp versions), or cut it short when nothing is near an altar.
   - Byte-identical. Estimate -3% mean.
8. **The stale-turn replay (CHANGES 59).** 67% of out-of-fuel turns are follow-ons, in streaks of 2-14 rounds.
   - Replay only the cheap path, or carry out the plan after a resume when the beliefs are unchanged.
   - A behaviour change that needs an A/B. It is the biggest lever on out-of-fuel turns (about -50%) until items 1-6
     land.

## Smaller items

- `set_turn_order` costs 3% everywhere. Its four danger passes at `self.pos` can share one.
- `find_members` costs 2.4%, max 61k.
- `lethal` costs 2.2%. It runs on 82% of turns as want_home's first test.
- `threatened` costs 1.4%. It runs up to 5 times a turn and is not memoised.
- `wants_shop` costs 1.4%.
- Comms cost 4.1% in all.
