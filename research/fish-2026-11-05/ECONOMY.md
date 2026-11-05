# Fish's economic mode switches: home trips, recall completion, tributes

November 5, 2026. Research only: no bot, earlier artifact, cache or manifest changed. Camp-group
targeting was deliberately left alone.

**Data.** All six decoded cohorts (456 games, engine `v3_0_0`). Rules were read off the four
oldest cohorts, **FIT** = model + confirm + third + fourth (309 games), and are reported unchanged
on whole held-out cohorts, **HELD** = fifth + sixth (147 games, 31 match groups). All features are
the actor's own cached perspective at the decision turn's start (its view, plus its own earlier
sightings for camp respawn memory); later frames only label. Counts are turns or episodes, which
are correlated within a game: they are not independent trials. Spawn tiles are `breadth.spawn`
(exclusive cached maxima). Health is `hp / maxHp` without shield.

**Recall semantics used throughout.** Fish starts a recall at the end of almost every turn off spawn
(the "prepared recall", CONTINUATION.md). A start is never a label here, nor is keeping it a few
turns. A channel that starts a turn at timer 4 has just been prepared; at **timer 1** the turn is
the last chance to cancel: keeping it then is the decision to arrive (the next turn starts on
spawn unless damage or a stun interrupts). Home labels are only **completed arrivals**: a recall
kept through timer 1 whose next turn starts on spawn, or a walk that ends a turn on spawn.

## 1. Home-trip gate: health <= 0.63 or gold >= 30 (necessary, near-exact)

**Rule.** At the last keep (timer 1) of every completed recall home:

```text
hp / maxHp <= 0.63   or   gold >= 30   (one shard)
```

| Completed recall arrivals | FIT | HELD |
| --- | ---: | ---: |
| Gate holds at the timer-1 turn | 11,714/12,008 (97.55%) | **5,563/5,643 (98.58%)** |
| Baseline: health <= 0.63 alone | 6,381/12,008 | 2,906/5,643 |
| Baseline: gold >= 30 alone | 7,929/12,008 | 3,798/5,643 |

The gold half is "can buy one shard", not "can complete an emblem": of HELD healthy shop recalls,
758/2,652 (28.6%) carry less than `30 x (5 - shards bought mod 5)` (shards counted from the
actor's own shop turns). Thresholds are flat optima: health 0.62-0.63 and gold 30 are best in the
FIT sweep (gold 25 or 35 lose 20-70 turns). Gem-weighted health (the priority encoding's x0.65 when
carrying) fits worse (23,598 vs 23,991 FIT timer-1 decisions).

Converse at decision time, after the actor's own capture payout, healthy (hp > 0.63), no enemy seen
before the endpoint (the next of farm, home, tribute):

| P(next endpoint is home) | FIT | HELD |
| --- | ---: | ---: |
| gold < 30 | 53/955 (5.5%) | **36/622 (5.8%)** |
| gold >= 30 | 3,598/8,336 (43.2%) | **1,885/4,267 (44.2%)** |

So gold >= 30 or a wound is the gate; it is not sufficient (section 3).

Violations: 374 of 17,651 completed recalls, concentrated on Cassi (96) and Issac (91); 165 carry
gems, 77 stand on a just-paid group tile. A partner-follows rule does not explain the Cassi/Issac
cases (16 of 187 have the partner arriving within 2 rounds). Some are recalls used as a shortcut
to an altar: `a01c1f9f1c54417d` (04atoll) r684 actor 0 (Marcella, full health, 7 gold, 38 gems)
walks toward spawn and recalls 36 steps out, then walks from spawn to the altar (altar walk 46
from the recall tile, 31 from spawn); Cassi does the same at r683.

## 2. Timer-1 keep rule: when a prepared recall is allowed to complete

```text
at a turn starting with the recall channel at timer 1 (alive, unstunned, off spawn):
  standing on an empty group (capturing):                  keep iff hp/maxHp <= 0.40
  on a respawning group's tile in its payout round
    (its respawn timer still reads the full 40/50/60/80/150): keep iff hp/maxHp <= 0.63
  otherwise:                                                keep iff hp/maxHp <= 0.63 or gold >= 30
```

| All timer-1 decisions | FIT | HELD |
| --- | ---: | ---: |
| Rule | 23,991/26,888 (89.23%) | **11,044/12,192 (90.58%)** |
| Always cancel | 14,777 (54.96%) | 6,493 (53.26%) |
| Health only (0.40 capturing, else 0.63) | 20,356 (75.71%) | 9,127 (74.86%) |

By branch (HELD): capturing 3,959/4,043; payout round 2,003/2,765; paid tile, later rounds
1,118/1,155; elsewhere 3,964/4,229. The payout-round branch is the weak one: there Fish has just
received its share and its real choice (farm/home/tribute) is made that turn (section 3).
In the later rounds of a paid tile, healthy actors with gold >= 30 keep in 99% (for example own
respawn reading 47-49 or 57-59: 1,623/1,630 FIT); at exactly the full value they cancel 74%
(50: 2,800/3,594; 60: 1,167/1,750).

Reading: the recall is Fish's idle action. A completed recall needs four turns with nothing to do
and, at timer 1, the gate of section 1; while capturing, only a wound below 40% sends it home.
Capturing actors keep the channel across the countdown (19,802 FIT channels kept at timer 4 on an
empty group and cancelled later). This replaces DECISIONS.md's timer-1 tree (78.44%) with three
named conditions.

Counterexamples (HELD): `cfc1265d7551c7d5` actor 6 (Marcella) keeps at r488, r663, r729, r882,
r995, r1014 with the gate false; `bd2f59dff6a7ad93` r233 actor 5 (Marcella) cancels with it true;
FIT: `f983f4e8efc50a51` actor 1 (Vendetta) r202, r385, r529, r564. All kept in
`econ-home.json`.

## 3. After a payout: farm, home or tribute (approximate forecast)

Episodes: the turn after the actor's own capture share (gems or gold rose on the tile it ended its
last turn on), off spawn. Label: the first of a camp hit or another empty group occupied (farm), a
completed arrival (home), a successful tribute start (trib) within 60 rounds. Episodes whose
endpoint follows an enemy sighting, death or timeout are dropped (FIT 10,368 kept of 15,823; HELD 5,326 of 7,527).

A depth-4 tree (min leaf 40) on causal features gets **HELD 3,336/5,326 (62.64%)** vs majority
"home" 2,147 (40.31%); FIT 63.02%. Per held group 51.5-79.1% (31 groups). Its top splits:
nearest altar walk <= 8 and payout gems > 6 → tribute; payout gold > 74 (an Elk/Golem-sized share)
→ home unless far (home walk > 22 still home); small payouts → farm unless the next ready camp is
> 5 away and home <= 14. These are fitted splits, not source constants. Confusion and examples
are in `econ-payout.json`. ROUTES.md's post-payout forecast (different episode and label
definitions) was 55.52%.

## 4. Walk or recall home: walk iff the walk is at most 5 steps

For completed arrivals passing the gate (deliberate trips), the walking distance (king steps,
walls/holes/altars/enemy spawn blocking) from the decision tile (the walk's first tile, or the
recall's timer-4 tile):

```text
walk iff home_walk <= 5, else recall
```

| | FIT | HELD |
| --- | ---: | ---: |
| Rule | 11,682/12,364 (94.48%) | **5,439/5,658 (96.13%)** |
| Always recall | 10,253 (82.93%) | 4,812 (85.05%) |

The threshold sweep peaks at 5 in both (HELD: 4 → 5,281, 5 → 5,439, 6 → 5,374). FIT by distance:
5 steps 478 walk / 105 recall, 6 steps 153 / 309. A recall takes 5 turn ends, so Fish walks when
walking is no slower. Ungated walk-ins (3,175, 1,520 from an adjacent tile, 71 that then shop) are
mostly incidental passes over spawn and are excluded. Counterexamples: `4dc0723fddb46297` r35
actor 6, r204 actor 5 (recall from <= 5); `81e3a65896b028a3` r350 actor 0 (walk from > 5).

## 5. Why recalls complete: retreat or shopping; travel is rare

Completed recalls by the timer-1 state (HELD, 5,643): **retreat** (hp <= 0.63) 2,906 (738 with an
enemy in sight), **shop** (healthy, gold >= 30) 2,657, other 80 (1.4%). Home is a shortcut to the
next camp group Fish hits after leaving spawn (4 turns of channel left + walk from spawn, less than
the walk from the timer-4 tile) in 17/56 "other" recalls with a next camp, and to an altar in 9/37
"other" recalls carrying gems. Shortcuts occur at similar rates in shop trips (1,106/2,483), so a
pure travel recall is at most ~1% of completed recalls; the 04atoll altar shortcuts above are the
clearest instances. Prepared recalls that complete are rare: elsewhere than on a camp, 7,773 FIT
timer-4 channels arrive against 965,310 cancelled at timer 4 and 11,285 kept then cancelled.

## 6. Prism: banks only a winning bag (exact necessary condition, small sample)

```text
Prism starts a tribute only if  own bag + team score + bags of all allies in sight >= 1000
```

| Prism tribute starts | FIT | HELD |
| --- | ---: | ---: |
| This rule | 61/61 (11 games) | **8/8 (4 games)** |
| Old rule (allies already tributing) | 57/61 | 5/8 |
| Bag + score only | 55/61 | 2/8 |

Smallest margin 2 (`d3e831065afbc6a8` r931 actor 4: bag 444 + score 537 + 21 in sight = 1002).
This fixes CONTINUATION.md's counterexample `2f0390ba522dd27e` r691 actor 4 (668 + 305 + 42
carried by a recalling Marcella = 1015). Whether unseen allies' bags count (through shared
memory) cannot be told. The gate is not sufficient: adjacent to an altar with it true and no enemy
in sight, Prism starts in 10/22 FIT and 0/2 HELD frames. After its own payouts Prism goes on to
tribute in 6/219 FIT and 2/68 HELD episodes: it carries its gems (+1.5 Focus each) otherwise.

## 7. Other champions: no fixed gem threshold; the altar's distance decides

Tributed bags per type (all cohorts, median [10%-90%]): Marcella 33 [12-97], Vendetta 36 [8-111],
Heart of Ruin 28 [8-77], Cassi 20 [7-56], Issac 17 [7-46], Vesper Vale 57 [12-487], Willow 14
[7-44]. Starts at 2 gems exist for most types. After a payout, with gems, no enemy, non-Prism:

```text
tribute next iff  altar_walk <= ready + 2  and  gems >= 8 x (altar_walk - 2)
```

`altar_walk`: steps to a tile beside the nearest altar; `ready`: min over other camp groups of
max(walk to beside it, remembered respawn wait), from the actor's own sightings (unseen groups
assumed alive).

| Post-payout, with gems | FIT | HELD |
| --- | ---: | ---: |
| Rule | 7,304/8,731 (83.66%) | **3,586/4,275 (83.88%)** |
| Never tribute | 6,705 (76.80%) | 3,250 (76.02%) |
| Best distance-only rule (altar_walk <= 5) | 7,173 | 3,546 |
| Rule, altar within 12 (meaningful subset) | 2,437/3,367 (72.38%) | 1,242/1,712 (72.55%), never 52.86% |

It finds 490/1,025 HELD tribute endpoints (154 false alarms): many tributes follow a later
decision. Distance carries most of the signal; the gem term adds one point over distance alone.
Race state matters only as a trend (all cohorts): where the rule says tribute, the rate rises from
69% (enemy score < 200) to 81% (>= 800); where it says not, tributes go from 10% before round 400
to 27% after round 800. A winning bag (own + score
+ allies in sight >= 1000) is tributed in 24/29 HELD episodes where the rule agrees and 16/39 where
it does not. Counterexamples (HELD): `bd2f59dff6a7ad93` r291 actor 5 (Marcella, 106 gems, altar 6,
camp ready 3, tributes), `cfc1265d7551c7d5` r749 actor 6 (Marcella, 31 gems, altar 28, tributes).

**Tribute while capturing: almost never.** Starting a turn within 1 of an altar with gems while on
an empty group, Fish starts a tribute in 4/170 FIT and 4/27 HELD frames, against 1,017/5,568 and
462/2,190 off a capture; 41 of 10,633 tribute starts are on an empty group.

**Altar choice.** On maps with 2+ altars, of tributes reached by a walk, the altar nearest by walk
at the walk's start is the one used in 4,743/4,976 FIT and **2,192/2,294 HELD (95.55%)**. No
meaningful-choice baseline was built (second-altar distances are not in the rows).

**Channels.** Of tribute starts, FIT 6,403/7,143 complete, 143 are cancelled by Fish, 319 are
interrupted (stun or a lock: not distinguished), 6 die; HELD 3,180/3,490 complete, 50 cancelled.

## Compared with astraeus (`bots/astraeus/src/economy/`)

- Shop trips: `shop.cc wants_shop` needs gold >= 30 and, except Prism, >= 150 or a begun emblem,
  then prices the trip. Fish's only gold condition is >= 30 (28.6% of its healthy shop recalls are
  below emblem completion).
- Retreat: our recall lines are `recall_health_fraction` 0.325 (threatened) and
  `safe_recall_health_fraction` 0.144. Fish completes a recall at <= 0.63 (<= 0.40 while capturing).
- Walk or recall: our `home.cc walk_home_limit` walks up to channel + 1 = 6 steps; Fish up to 5.
- Prism: our `bank.cc winning_bag` (`gems_short`) counts allies in sight only while they channel a
  tribute; Fish counts every ally bag in sight.
- Fish does not hold its capture for a tribute (or vice versa) and ties shopping to idleness: it
  goes home when it has had nothing to do for four turns and can buy a shard or is wounded.

## Not resolved

- Sufficiency of the home gate when not on a just-paid tile: post-payout healthy actors with gold
  >= 30 go home 44% of the time; the camp-readiness and via-home detour features tried here give
  only the approximate tree of section 3.
- Prism's start/decline when the gate is true; other types' adjacent-altar declines (lock memory is
  not in the actor caches).
- Cassi/Issac completed recalls without the gate (187 of 17,651).

## Reproduce

New scripts (refuse to overwrite): `tools/fish/econ_rows.py` (per-turn rows with spawn, altar and
camp-readiness memory), `econ_common.py`, `econ_episodes.py` (payout, t1, t4, arrival, trib, adj
episodes), `econ_home.py`, `econ_tribute.py`, `econ_payout.py`.

```sh
python3 tools/fish/econ_rows.py replays/fish-econ/rows-v3.jsonl.gz --jobs 6
python3 tools/fish/econ_episodes.py replays/fish-econ/episodes-v1.jsonl.gz
R=research/fish-2026-11-05
python3 tools/fish/econ_home.py $R/econ-home.json
python3 tools/fish/econ_tribute.py $R/econ-tribute.json
python3 tools/fish/econ_payout.py $R/econ-payout.json
```

Results: [econ-home.json](econ-home.json), [econ-tribute.json](econ-tribute.json),
[econ-payout.json](econ-payout.json), each with denominators per role, baselines and counterexamples.
