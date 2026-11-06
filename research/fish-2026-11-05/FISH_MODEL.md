# Intercontinental Fish: a behaviour model from its ladder replays

What the Cambridge Battlecode ladder team **Intercontinental Fish** (here "Fish") does, as
reverse-engineered from its public ladder replays (the organisers allow this). This document stands
alone: every term, formula, threshold and table needed is inline. Source reports are listed only for
provenance, in the appendix.

It is a set of measured regularities, not Fish's source code. Rules here are **imitation rules**: they
reproduce Fish's choices at the stated rates. Fitted split points are called **fitted thresholds**. They
are not Fish's constants, and nothing here says that copying Fish would improve another bot.

---

## 1. Scope, data and conventions

### 1.1 Data

All games are cambc 5.0.0 ladder replays (replay engine `v3_0_0`), dated 2026-11-04 23:10 UTC to
2026-11-05 23:40 UTC. Fish's submission version is not in the metadata, so we cannot tell whether one
submission played every game. Each cohort below is a separately pinned set of whole match groups, with
duplicate bytes, match ids and groups removed against every earlier cohort.

| Cohort | Games | Match groups | Created | Role in this document |
| --- | ---: | ---: | --- | --- |
| `model` | 124 | 25 | Nov 5 | discovery (original 109 train / 15 test split) |
| `confirm` | 96 | unknown | Nov 4 evening (US Eastern) | discovery / first confirmation |
| `third` | 43 | 9 | Nov 5 | discovery / confirmation of the decision trees |
| `fourth` | 46 | 10 | Nov 5 | discovery / confirmation of the route models |
| `fifth` | 94 | 20 | Nov 5, 18:50-21:10 UTC | **held out** for most later studies |
| `sixth` | 53 | 11 | Nov 5, 21:10-21:40 UTC | **held out** for most later studies |
| `seventh` | 265 | 56 | Nov 5, 21:40-23:40 UTC | **untouched**: rules frozen by hash, then scored once |

Total: 721 games. The seventh cohort holds 3,271,252 inputs and 1,240,049 completed champion turns,
accounted for exactly against the raw timeline. Fish won 352 of the first 456 games (the six cohorts
before the seventh), and only 9 of those 456 reached round 2000.

The usual split in the later studies:
- **FIT** = model + confirm + third + fourth (309 games).
- **HELD** = fifth + sixth (147 games, 31 match groups).
- **Seventh** = the untouched test.

HELD had been decoded by earlier studies, though not for the labels each later study scored. Only the
seventh cohort is a clean, untouched test.

### 1.2 Inputs and labels

- Every rule's inputs come from the acting champion's own view at decision time: the game's own WASM
  replay decoder, read from that champion's perspective (its sight plus its own ward's), and its own
  earlier sightings. No opponent gold, hidden positions or future events are used.
- Exception, flagged where used: team-shared camp memory (section 7.2), built from teammates' earlier
  views.
- Labels may use later frames (the next camp hit, an arrival home), but labels never feed a predictor.
- Counts are turns or episodes within games. They are correlated, not independent trials. Match-group
  bootstrap intervals are given where a report computed them.

### 1.3 Confidence tags

Every claim carries one tag:

| Tag | Meaning |
| --- | --- |
| **[7]** | Frozen before decoding, then scored once on the untouched seventh cohort |
| **[H]** | Fitted on earlier cohorts, scored unchanged on held-out cohorts (named; HELD unless stated) |
| **[X]** | Exact or near-exact (≥ 97%) on a large sample, without a held-out split |
| **[D]** | Descriptive frequency on a large sample, not a predictive rule |

"Free rows" means opportunities where the game rules left the alternative legal. Every rule here was
re-checked on free rows (the forced-vs-free audit of 2026-11-06), and the free-row numbers are the ones
given. Rules that the game itself forces were dropped.

### 1.4 Game facts needed to read the rules

From `cambc-rules.yaml`, the engine-verified rules:

- **Turn order.** Team A starts odd rounds, team B even rounds. The teams alternate one champion at a
  time. Within a team, higher priority acts first (ties by id). A new priority applies **from the next
  round**. Writing priority is free and takes any int32.
- **Actions.** A turn has one walk (king step), one basic attack and one successful cast.
  - Melee range is 1; walking and attacking are independent.
  - Ranged range is 3; **a ranged champion's walk or basic attack spends both**.
  - **Exclusive spells** cannot be cast after walking, and forbid walking after the cast.
  - An attack reset restores a spent basic attack (never the walk). A ranged champion can walk, reset,
    then attack.
  - Dashes move up to 2 king steps.
  - Wards, shopping, consumables and priority are free actions.
- **Recall.** A recall channel lasts 5 turn ends, then moves the champion to its spawn. It is cancelled
  by any damage or a stun, and can be cancelled voluntarily. While channelling, the champion can only
  cancel.
- **Spawn.** A champion on its own spawn heals to full at its turn end. Shopping is possible only on
  the own spawn or while dead.
- **Camps.** A camp attacks the nearest champion in its range; ties go to the champion acting first in
  that round's turn order. A champion killed by a camp loses its carried gems. Camps sleep after 2 camp
  phases with no champion in range.
- **Captures.** Standing on an emptied group's camp tile, with no enemy on any of its tiles, pays at
  round R+6 for a hold from R (R+4 with a Capture emblem). Those on the tiles at payout split the gems
  and gold.
- **Kills.** The killer gets 100 gold (150 with Hunter) plus the victim's carried gems. Killing either
  Cassi or Issac kills both.
- **Tribute.** A tribute channel starts within 1 of an altar and scores the carried gems. It takes
  `max(1, ceil(gems/10))` turn ends, and a stun cancels it.
- **Locks.** A lock is placed within 2 of an altar and blocks the other team's tributes there.
- **Teleport crystal.** Lands within 3 after a 3-turn channel.
- **Shards.** A shard costs 30 gold; five identical shards form an emblem.
- **Wards.** Placed within 2, with one ward per champion and a 10-round recharge. Placing onto an
  unseen allied ward fails silently.
- **Memory.** Each team shares only 8 bytes of memory between its champions.
- **Kits used below:**
  - Marcella is immune to stuns.
  - Prism gains +1.5 Focus per carried gem.
  - Heart of Ruin's ("HoR") dash stuns and damages enemies within 1 of its landing.
  - Unit and ground abilities have range 4; a ground spell hits a 3x3 area.

---

## 2. Glossary and shared definitions

- **Distance**: Chebyshev, unless "walk" is said. **Walk** means king-step BFS with walls, holes,
  altars and the enemy spawn blocking. Camps block only where stated.
- **EHP** (effective health): `hp + shield`.
- **Health fraction** `h = hp / max_hp`. **Gem health**: `h × 0.65` if carrying any gems, else `h`.
- **Band**: `max(0, floor(4 × (1 − min(1, EHP/max_hp) × (0.65 if gems > 0 else 1))))`, which takes
  values 0..3.
  - Without gems the boundaries are 75%, 50% and 25%; with gems, 10/13 and 5/13. Equality falls into
    the lower-health band.
  - The 0.65 is any value in (0.649350649, 0.65]; the data cannot tell them apart.
- **One-turn damage reach `D(c, d)`**: the most damage champion `c` can deal in one turn to a unit at
  distance `d`. Take the best of these options:
  - a basic attack (Strength) if `d` ≤ range, with one walk allowed for melee (so melee reaches 2,
    ranged 3);
  - doubled if an attack reset is ready;
  - a ready dash adds 2 to reach;
  - a ready damage spell within 4: a unit spell does multiplier × Focus; a ground spell reaches one
    tile farther; HoR's dash does 1.5 × Focus plus a basic.

  One cast per turn. HoR's passive is applied. `D` ignores terrain, blockers, items and camps.
- **Danger(tile)** = `Σ over visible enemies e not stunned for their next turn of D(e, dist(tile, e))`,
  divided by own EHP. It is measured on the turn-start view.
- **Kill available** (from a tile): some enemy attackable from it has `D(me, ·) ≥ its EHP`.
- **Acceptable** (a tile): a kill is available there, or (`h > 0.49` and danger ≤ 0.28).
  - These are fitted thresholds (section 9.1).
- **Side EHP ratio**: (own + visible allies within 8) EHP / visible enemies' EHP within 8.
- **Contact turn**: a completed turn, alive and unstunned, whose start view shows a living enemy
  champion.
- **Group**: a camp group (cardinally connected monsters). Its state is one of:
  - unknown (0);
  - alive (1);
  - empty (2): all members dead, awaiting capture;
  - respawning (3).
- **Payout episode / spawn episode**: a farm decision taken on the turn after the actor received a
  capture share, or on its first actionable turn leaving spawn.
- **Prepared recall**: a recall Fish starts at the end of a turn and normally cancels the next turn
  (section 8.1). **Timer** `t`: the turn ends left in the channel; 4 at the first turn start after the
  start, 1 at the last chance to cancel.
- **Holder rank** (capture holders and entrants):
  `Marcella > Vesper Vale > Vendetta > Heart of Ruin > Cassi > Issac > Willow`. Prism, Ren and Varg
  are unranked.

---

## 3. Draft and emblems

### 3.1 Picks [X]

From the four oldest cohorts (309 games, before the fifth):

- **The draft is a fixed function of the map.**
  - Every map with 2 or more games used one pick order: 14/14 maps (3 picks), 18/18 (4 picks) and
    57/57 (5 picks).
  - Every game used its map's order (309/309).
  - All 65 maps seen from both sides share the order between sides.
  - Round 0 cannot see the enemy's picks, and later rounds show no reaction to them.
- **Never drafted:** Ryth, Tavi and Stellar, in 0 of 456 games and none in the seventh cohort.
  Varg appears once in 309 games, Ren 8 times and Prism 11 times.

Pick orders (round 0 first; games; Fish wins):

| Picks | Order | Games | Won |
| --- | --- | ---: | ---: |
| 3 | Vesper Vale, Heart of Ruin, Cassi & Issac | 21 | 17 |
| 3 | Vesper Vale, Marcella, Cassi & Issac | 17 | 10 |
| 3 | Marcella, Prism, Cassi & Issac | 3 | 3 |
| 3 | Marcella, Heart of Ruin, Cassi & Issac | 3 | 2 |
| 4 | Marcella, Vendetta, Heart of Ruin, Cassi & Issac | 53 | 35 |
| 4 | Vesper Vale, Vendetta, Heart of Ruin, Cassi & Issac | 3 | 3 |
| 4 | Marcella, Prism, Heart of Ruin, Cassi & Issac | 3 | 3 |
| 5 | Marcella, Vendetta, Heart of Ruin, Cassi & Issac, Willow | 105 | 83 |
| 5 | Vesper Vale, Vendetta, Heart of Ruin, Cassi & Issac, Willow | 87 | 62 |
| 5 | Vesper Vale, Vendetta, Heart of Ruin, Cassi & Issac, Ren | 7 | 5 |
| 5 | Marcella, Prism, Heart of Ruin, Cassi & Issac, Willow | 5 | 4 |
| 5 | Vesper Vale, Vendetta, Marcella, Ren, Heart of Ruin | 1 | 1 |
| 5 | Vesper Vale, Vendetta, Heart of Ruin, Varg, Cassi & Issac | 1 | 0 |

- Round 0 is Marcella or Vesper Vale. It is a tendency, not a recovered rule: Marcella on 36 of 41
  checked maps with more gem than gold clusters; Vesper on 25 of 37 others.
- Prism, always in round 1 after Marcella, appears only on the `adgato_gemcombat` maps.
- The one-off Ren and Varg orders are on maps seen once.

### 3.2 Shopping and emblem builds [X]

Emblems are named `Family-Stat`: the family and the stat of the five identical shards (S Strength,
F Focus, H Health). Purchases match the engine's statistics in 1,706/1,706 champion-games. Nothing is
ever sold. The buying rule is in section 8.4. Build orders per champion (5-pick games, the largest
sample; 3- and 4-pick games match):

| Champion | Emblems in order of formation (games with that emblem at that position) | No emblem |
| --- | --- | ---: |
| Cassi | Power-F (#1 in 131/146) > Durability-F (#2 in 55) > Bruiser-H (#3 in 34) | 59/205 |
| Issac | Prospector-H (#1 in 107/116) > Bruiser-H (#2 in 48) > Durability-H (#3 in 32) > Power-S (#4 in 21) | 89/205 |
| Heart of Ruin | Prospector-F (#1 in 126/189) > Capture-H (#2 in 109) > Jungle-F (#3 in 105) > Monster-F (#4 in 60) > Hunter-H (#5 in 40) > Bruiser-H (#6 in 42) | 17/206 |
| Vendetta | Capture-H (#1 in 185/197) > Jungle-S (#2 in 175) > Monster-S (#3 in 127) > Hunter-H (#4 in 88) > Durability-H (#5 in 81) > Collectors-S (#6 in 64) > Bruiser-S (#7 in 52) > Prospector-H (#8 in 37), then repeated Bruiser-S | 4/201 |
| Willow | Prospector-H (#1 in 68/68) > Power-S > Home-H > Durability-H | 129/197 |
| Marcella | Prospector-F (#1 in 72/110; else Capture-F or Hunter-F) > Treasure-F/H > Capture-F > Jungle-F > Monster-F > Bruiser-H > Durability-H > Bruiser-F > Skirmish-H > Collectors-H, then repeated Bruisers | 1/111 |
| Vesper Vale | Capture-S (#1 in 71/96; else Prospector-S, 23) > Treasure-S > Jungle-S > Monster-S > Hunter-H > Durability-H > Collectors-S > Bruiser-S > Bruiser-H (#10 in 54), then repeated Bruisers | 0/96 |
| Prism | Prospector-H; then Greed-H shards accumulate (a Greed emblem needs 25 shards) | 3/5 |
| Ren | Prospector-H (#1 in 4/5) > Bruiser-H | 3/8 |

Gold concentrates on the carries:

| 5-pick, mean per game | Shards | Gold spent | Median round of the first emblem |
| --- | ---: | ---: | ---: |
| Vesper | 128 | 3,866 | 82 |
| Marcella | 77 | 2,318 | 88 |
| Vendetta | 49 | 1,475 | 140 |
| Heart of Ruin | 26 | 790 | 245 |
| Cassi | 10.5 | 325 | 418 |
| Issac | 8.3 | 260 | 414 |
| Willow | 4.3 | 135 | 453 |

---

## 4. Opening [X]

- **Deterministic per map, side and champion.**
  - Across games with the same map, side and champion, the first camp group attacked is the same in
    **1,918/1,969 pairs (97.4%)**. One game, on `04keyhole`, differs in every champion, perhaps another
    submission.
  - Grouping by (map, Fish side, roster) gives 259 game pairs. Every actor's inputs are identical
    through round 1 in 236 pairs, round 10 in 220, round 20 in 179, round 50 in 142 and round 100 in 66.
    The median first divergence is round 53.
  - 168 of 243 divergences come at or after the first enemy sighting.
  - The first group and the round of the first hit match for every actor in 186/259 pairs (72%).
  - This holds across opponents: only 3 of the 259 pairs share a known opponent draft.
  - So one replay of a map and side gives Fish's first ~20 rounds (moves, ward tiles, first camps).
- **Packs.** In 109 of the 191 configurations with two or more opening hitters, all of them go to the
  same group.
- **Round-1 divergences** look like a dropped priority write, sometimes with its ward attempt. The
  champion's priority then stays 0 for round 2.

The opening plan itself is not recovered (section 13).

---

## 5. Turn order: the priority encoding

### 5.1 The encoding [X]

```text
N    = number of Fish champion bodies, dead included (Cassi and Issac count separately)
rank = 2 + position in the team sorted by base max health, descending
       (ties by champion type index; exception: Heart of Ruin before Varg)
       e.g. Marcella 1200 > Vesper or HoR 1000 > Vendetta or Issac 900 > Prism or Willow 700 > Cassi 600
priority = -rank - (N+1) * L          L is an integer "level"
```

- `rank = (−priority) mod (N+1)`, read as N+1 when the remainder is 0. It is the same for a champion
  in every mode in **2,507/2,507** champion-games (six cohorts), and never 1.
- The base-health order predicts rank in 2,499/2,507. The 8 misses are HoR and Varg, both on 1,000
  base health, where HoR comes first.
- In the 6-body roster (Marcella, HoR, Vendetta, Cassi, Issac, Willow) the ranks are 2, 3, 4, 7, 5
  and 6.
- Fish writes **only on change**: 0 of 76,654 `model` writes repeat the current value.

### 5.2 The modes

| Mode | L | Meaning | Held-out turns |
| --- | --- | --- | ---: |
| dead | −1 | dead champions | 46,609 (all dead turns) |
| quiet | band (0..3) | default | 571,438 |
| late | band + 5 | at a contested camp | 13,216 |
| contact | 99 + j if the enemy starts next round; −101 − j if Fish does | enemy in reach | 34,689 |
| early | −5..−1 (alive) | see below | 3,201 |
| other | — | unexplained | 251 |

Resulting order, with higher acting first:
- **Fish starts the round:** contact (higher j first), then early, then quiet (band 0 first), then
  late.
- **Enemy starts the round:** early, then quiet, then late, then contact (higher j last).

With N = 5 the contact values are `±(600 + 6j + 6) − rank`, the "±500..800" values seen in fights.

**Contact level j** (approximate; Fish's own threat model differs):

```text
j ≈ min(16, floor(16 * T / EHP)),  T = Σ over visible enemies of D(e, distance)
```

- [H] Exact in 20,295/34,689 (58.5%) held-out contact turns, within 1 in 72.9%. Baseline j = 0:
  45.5%.
- The cap is real: 4,375 discovery turns sit at exactly 16.

**Contact sign** [H]: `contact+` (act first) iff Fish starts the round in which the write applies.
This holds in **34,659/34,689 (99.91%)** of held-out contact turns.

- **What it buys: back-to-back turns** [H]. Take an enemy-start round followed by a Fish-start round.
  If a Fish champion is `contact−` then `contact+`, the last actor of the first round is also the
  first actor of the next.
  - This happens in **2,928/4,551 (64.3%)** of held-out round pairs, against 3.6% (1,128/31,692)
    without such a champion.
  - Since j grows with threat, the most threatened champion gets the pair.

**Early mode** [7] (an output, not a choice). It marks an end tile just outside basic reach but inside
dash or spell reach.
- Among quiet or early turns ending 3-5 from an enemy, early is chosen:
  - when both sides' `D > 0` reaches the end tile: 42.2% held, 40.7% seventh;
  - when neither side's does: 1.2% held, 1.1% seventh.
- By end distance (held): 14.8% at 4, 3.8% at 3, 2.4% at 5, ≤ 0.4% elsewhere.
- What separates early from quiet inside that band is unknown.

### 5.3 The mode selector [H]

From the champion's own view just before its priority write:

```text
if dead:                   L = -1
elif contested_camp:       L = band + 5                            (late)
elif enemy_in_reach:       L = 99 + j  or  -101 - j  (sign as above) (contact)
else:                      L = band                                (quiet)

enemy_in_reach: a visible enemy e is within reach(e) of self or of a visible ally,
                or within reach(self) of self; reach = 3 ranged, 2 melee
contested_camp: a visible awake ranged monster (not a cluster) has self in its range, and a
                visible enemy is within range + 1 of an awake member of that monster's group
                (the +1 is the only fitted constant: 91.7% / 93.4% / 91.8% for k = 0 / 1 / 2)
early is never predicted
```

| Held out | Mode correct | Baseline: always quiet |
| --- | ---: | ---: |
| Alive, enemy visible | **131,740/140,817 (93.6%)** (fifth 93.3%, sixth 94.1%) | 64.6% |
| — the same without the late rule | 87.3% | |
| — exact priority value | 117,767 (83.6%) | |
| All turns | **658,828/669,404 (98.4%)** | 92.3% (dead → −1) |
| — exact priority value | 642,197 (95.9%) | |

- Where the mode is right, quiet and late values are exact in 566,609/569,678 and 9,561/9,595
  held-out turns.
- Held-out errors: early never predicted (2,895); quiet predicted where late was actual (2,246);
  contact predicted where late was actual (1,112); contact predicted where quiet was actual (1,170).
- **Late is contagious.** A champion that sees a late ally is late in 7,990/14,091 held-out turns,
  against 4,963/126,726 when it sees none. Late episodes are often team-wide. Fish may share a late
  flag through the 8 bytes, or read allies' visible priorities; neither is established.
- **Priority is not a combat flag.** Negative writes occur on 7,824 training turns with a direct
  attack or cast on an enemy champion.

### 5.4 What the order does at camps [H]

**Ties between Fish champions** for a camp hit (25,907 held-out). Fish's actual order is compared with
id order and with its own order reversed:

| Who takes the tied hit | Fish order | id order | reverse |
| --- | ---: | ---: | ---: |
| highest health fraction | **73.0%** | 65.1% | 46.7% |
| a gemless champion, mixed-carrier ties (8,006) | **70.4%** | 30.0% | 33.7% |
| most hits in hand (EHP / camp strength) | 71.4% | 71.9% | 29.5% |

- So the quiet order shields carriers and the relatively hurt. A camp kill destroys the carried bag.
- It does not give the hit to the most absolute EHP.
- In lethal ties, the champion the hit would kill was spared in 39/39 discovery and 45/45 held-out
  ties. Id order would have spared it in 26 and 35.

**Ties between Fish and an enemy.** The share of tied hits Fish takes, by the first tied Fish
champion's mode:

| Mode | Fish starts the round | Enemy starts the round |
| --- | --- | --- |
| quiet | 61% (discovery) | 45% |
| late | 24% (held 29%) | 13% (held 15%) |
| contact | 100/107 (held 42/45) | 3/79 (held 0/45) |

The late mode cuts Fish's share of contested-camp hits by half to two thirds.

**Who stands in range** [H]. Camp hits taken, as a share of the hitting monster's in-range turns:
HoR 46%, Issac 41%, Vendetta 42%, Marcella 49%, Vesper 35%, Cassi 14%, Willow 9%. Melee bodies stand
at distance 1 and take the hits; Cassi and Willow stand at 3-4 and are rarely hit.

---

## 6. Where the turns go [D]

Each Fish champion turn gets the first activity that applies. Shares of 2,236,792 turns over the six
cohorts:

| Activity | Share |
| --- | ---: |
| dead | 8.5% |
| on own spawn (home) | 3.1% |
| tribute channel or attempt | 2.8% |
| an action on an enemy champion | 3.0% |
| hitting a camp | 20.9% |
| standing on an empty group (capture) | 4.7% |
| keeping a recall channel | 6.7% |
| beside (≤ 2) a respawning group | 7.9% |
| walking near (≤ 3) a living camp | 7.0% |
| other walking (travel) | 34.6% |
| idle | 0.8% |

- **By champion.** Marcella clears least (12.0%) and tributes most (5.7%). Vesper tributes 7.0% and
  is at home 5.7%. Willow travels most (39.9%).
- **By phase.** Clearing falls from 30% of turns (rounds 1-100) to 9% after round 1000. Death rises
  from 3% to 17%, and travel from 34% to 42%.
- **By score lead.** The share of farming does not change with the lead; the differences follow
  deaths and game phase.
- **One policy all game** [D]. By phase and score:

  | | Enemy in sight | Hitting a camp | Range turns closing |
  | --- | ---: | ---: | ---: |
  | rounds 0-249 | 20% | 28.6% | 41.4% |
  | rounds 1500+ | 36-37% | 7-8% | 28-32% |
  | behind by ≥ 200 | 42% | 17.4% | 39.1% |

  - The contact hit rate drops slightly from 52.6% to 45.8% when behind.
  - Tribute starts rise when leading: 0.80% of turns at a lead above 200, 0.42% when behind.
  - There is no comeback aggression.
- **By champion, all cohorts:**

  | | Enemy in sight | Hits a champion | Range turns closing | Contact turns hitting |
  | --- | ---: | ---: | ---: | ---: |
  | Marcella | 38.5% | 5.7% | 45.2% | 52.8% |
  | Vesper | 24.6% | 3.4% | 45.7% | 67.4% |
  | Willow | 23.0% | 1.4% | 31.5% | 48.3% |

---

## 7. Farming

### 7.1 Spread, circuits and holders [D]

- **Payouts.** 92% of Fish payouts have one recipient (20,319 of 22,042).
  - Median payouts per 1,000 rounds per champion-game: Vesper 22, Vendetta 17.6, Marcella 16.7,
    HoR 10.4, Cassi 5.8, Issac 4.8, Willow 3.1.
  - So the high-rank holders collect, and Cassi, Issac and Willow mostly clear and leave.
- **Circuits.** A champion's payouts cycle among a few nearby groups.
  - The top two groups hold 45-65% of its payouts. A-B-A returns are 11-19%. Distinct groups per game:
    2.7 (Willow) to 7.9 (Vesper).
  - Games do not repeat beyond the opening: two games with the same map, side and champion share
    their first three payout groups in only 22% of pairs.
- **No zones.** Two champions of a game overlap in 67% of their payout groups.
- **Position.** Off spawn, 69% of turns are on Fish's half, 22% in the middle and 9% on the enemy half.
  - Payouts: 77% own side, 16% middle, 7% enemy side (mostly clusters and wolves).
  - The nearest ally is a median 2 tiles away, and within 4 in 67% of turns.
- **Big camps are team clears.**
  - Golems: 345 clears, 5 solo. Monoliths: 116 clears, 7 solo, Vesper 5 of them at Strength 200-545.
  - Elk groups: 457 of 5,598 solo, by Vesper 204, Vendetta 177 and Marcella 53.
- **Steals are incidental.** About 1% of payouts each way.

### 7.2 Camp choice: the team-memory logit [7]

This model predicts Fish's next camp group after a payout or a spawn exit.

**Episodes and label.**
- Start: a payout or spawn-exit turn with no visible enemy; openings are excluded.
- Label: the first camp-directed hit, or occupation of a different empty group, within 40 rounds.
- Censoring: an enemy sighting, a tribute, death, a return home or a timeout censors the episode.
- Candidates: groups with a static walk below 999, excluding the group just paid out.
- About 8% of labels are brief hits followed by another group.
- Fish heads straight for its pick: steps after the first lie on a shortest path to the label 90% of
  the time. Post-spawn misses are different choices, not mid-route changes of mind: only 33-43 of 948
  misses walk toward the prediction and then end at the label.

**Team-union memory** (the structural finding). Each candidate group's state is the newest sighting by
**any Fish champion whose turn came earlier**, not only the actor's own memory.

```text
for each candidate group g at a decision (actor a, round t):
    own      = a's own remembered state of g
    sighting = newest group-state sighting of g in any OTHER Fish champion's earlier turn
               (turn start, before an action, or turn end) this game
    if sighting exists and (sighting.round > own.round or g unknown to a):
        state(g)   = sighting.state          # 0 unknown, 1 alive, 2 empty, 3 respawning
        age(g)     = t - sighting.round
        respawn(g) = max(0, sighting.respawn_countdown - age(g))   if respawning
        if the state changed: live hp = full if alive/unknown, else 0; awake = 0
```

The channel is presumably the 8 shared bytes, which replays do not record (they read zero). It is
mostly respawn timers that are shared:

| Camp states used (refitted, scored on HELD) | Accuracy |
| --- | ---: |
| own memory only | 63.63% |
| **team-union memory** | **65.82%** |
| observer truth for all groups | 65.69% |
| truth only where no teammate has a newer sighting | 63.34% (no gain) |
| team memory, respawning-state sightings only | 65.52% |
| team memory, other states only | 64.20% |
| team memory, sightings at least 40 rounds old | 63.78% (gain gone) |

So Fish knows what its team saw, and no more. The shared summary cannot be every sighting (8 bytes); 142
held-out hits of the own-memory model become misses under the union.

**Features of candidate `c`.**
- `walk`: static king-step walk to a tile adjacent to the group (for alive or unknown groups) or onto a
  camp tile (for empty or respawning ones), with visible living camps also blocking.
- `respawn`: remembered rounds until it respawns (0 if not respawning). `wait = max(walk, respawn)`.
- `S`: own Strength. Fighter hp: wolf 1350, elk 2400, golem 5000, monolith 20000 (clusters 120).
  Fighter Strength: 20, 60, 120, 200.
- Unknown groups count as alive.

| Feature | Definition |
| --- | --- |
| `wait`, `logwait` | `wait/10`; `ln(1+wait)` |
| `respawn_part` | `max(0, respawn − walk)/10` |
| `alive_fight` | alive: total fighter hp / S / 100 |
| `alive_dps` | alive: total fighter Strength / 100 |
| `monolith`, `golem` | alive and contains one |
| `clusters_only` | no fighters |
| `unknown`, `empty`, `respawning` | state indicators |
| `gold`, `gems` | group reward / 100, / 10 |
| `allies_near` | visible allies within 3 of a camp tile |
| `ally_recent` | the actor saw an ally on the group within the last 10 rounds |
| `visited`, `route`, `last` | the actor farmed it before; it has seen this origin → group transition; it is the last group farmed |
| `terr`, `terr_neg` | `T = (min distance to own spawn) − (min distance to enemy spawn)`; `max(0, T)/10`, `max(0, −T)/10` |
| `ally_closer` | a visible off-spawn ally is closer to the group than the actor |
| `logworth` | `ln(1 + worth)`, `worth = 3·gems + gold` |
| `logR` | `ln R`, `R = max(1, wait + kill + cap)`. `kill` = remembered live hp / (S + Strength of visible off-spawn allies within 4 of the group); full hp if respawning, 0 if empty. `cap` = 0 if empty, else 7 |
| `lograte` | `logworth − ln R − ln(1 + R/Hz)`, `Hz = 100 · max(1, max(map W, H)/50)` |
| `logshare`, `enemy_near` | static walks from our spawn `us` and the enemy's `them`: `ln max(0.05, min(1, 2·them/(us+them)))`; `them ≤ us` |
| `empty_age` | empty: `min(age, 100)/10` |
| `resp_expired`, `resp_expired_age` | respawning and its countdown has run out; `min(max(age − original countdown, 0), 200)/50` |
| `alive_age` | alive: `min(age, 200)/50` (age = rounds since the sighting) |
| `hp_fight` | alive: remembered live hp / S / 100 |
| `damaged`, `awake`, `part_frac` | alive and below full hp; alive with an awake member; `1 − live/full hp` |
| `crew_frac`, `crew_any`, `crew_kill` | visible allies within 4: Strength / S; any; kill rounds saved / 10 |
| `n_types`, `has_elk`, `wolves`, `gold_only` | members / 5; alive with an elk; alive with a wolf; no gem reward |

**Score** = `Σ w_k · f_k(c)`. The pick is the argmax, ties to the lower group id. There are separate
weights after a payout and after a spawn, fitted on FIT (L2 0.1):

| Feature | Payout | Spawn |
| --- | ---: | ---: |
| `logworth` | +4.156 | +0.995 |
| `logR` | −3.617 | +0.519 |
| `lograte` | −1.400 | +0.988 |
| `logwait` | −2.610 | −2.103 |
| `wait` | +0.050 | +0.109 |
| `respawn_part` | −1.027 | −1.655 |
| `empty` | −3.733 | −3.378 |
| `empty_age` | +0.278 | +0.344 |
| `respawning` | +0.720 | +0.769 |
| `resp_expired` | −0.040 | −0.057 |
| `resp_expired_age` | −0.256 | −0.410 |
| `alive_age` | −0.294 | −0.538 |
| `unknown` | −0.960 | −1.136 |
| `damaged` | +0.374 | +0.644 |
| `awake` | +0.702 | +0.228 |
| `part_frac` | −1.658 | −1.009 |
| `hp_fight` | −0.081 | −0.395 |
| `alive_fight` | −0.447 | −0.020 |
| `alive_dps` | +0.461 | +0.359 |
| `monolith` | −2.183 | −0.182 |
| `golem` | −0.558 | −0.006 |
| `has_elk` | +0.502 | +0.671 |
| `wolves` | −0.016 | +0.158 |
| `clusters_only` | +0.226 | +1.181 |
| `gold_only` | −0.391 | −0.713 |
| `gold` | −0.553 | −0.306 |
| `gems` | +0.009 | −0.000 |
| `n_types` | −0.469 | −0.005 |
| `logshare` | +2.446 | +0.009 |
| `enemy_near` | −0.816 | −1.248 |
| `terr` | −0.254 | −1.225 |
| `terr_neg` | −0.113 | +0.274 |
| `visited` | +0.379 | +0.590 |
| `route` | +0.656 | +0.592 |
| `last` | 0.000 | +0.314 |
| `ally_recent` | −0.568 | −0.600 |
| `ally_closer` | +0.457 | +0.453 |
| `allies_near` | −0.114 | +0.050 |
| `crew_frac` | −0.156 | −0.119 |
| `crew_any` | −0.302 | −0.218 |
| `crew_kill` | +0.006 | +0.019 |

These are surrogate weights. Correlated features (`logworth`/`logR`/`lograte`, `wait`/`logwait`,
`alive_fight`/`alive_dps`) must be read together.

What the weights say:
- **After a payout**, Fish prices log worth (gems at about 3 gold) against log total time (wait +
  clear + capture) and strongly prefers its own half (`logshare`).
- **After a spawn**, time beyond the wait barely counts. What matters is worth, wait and memory: it
  avoids remembered-empty, unknown and enemy-near groups, and prefers respawning ones whose timer runs
  out about when it arrives.
- It prefers awake, partly cleared groups, joining a fight under way.
- It avoids groups an ally was just seen on, and lone Monoliths after a payout.

**Results** (all labelled rows; a median of 15 feasible candidates per row):

| Cohort | Team-memory logit | Own-memory logit, same fit | Wait baseline (`argmin wait`) |
| --- | ---: | ---: | ---: |
| **Seventh [7], all** | **7,686/12,179 (63.11%)**; free rows 63.53% | 60.69% | 48.72% |
| — after a payout | 3,538/4,974 (71.13%) | 68.98% | 59.09% |
| — after a spawn | 4,148/7,205 (57.57%) | 54.96% | 41.57% |
| HELD [H] | 3,902/5,928 (65.82%) | 63.63% | 49.66% |

- Seventh gain over own memory: +2.0 to +2.9 points by match-group bootstrap. It matches or beats own
  memory in 54/56 groups.
- Payout choice is good (71%); post-spawn choice is the weak half (58%).
- Misses are mostly near ties: the label is the model's second choice in 664 of 1,578 HELD post-spawn
  misses.

### 7.3 Camp attack target [H]

At a basic attack with visible living camps in basic range and no enemy champion in basic range:

```text
prev = group of this actor's most recent basic attack on a camp (its own memory, kept across death)
candidates = camps in basic range; if prev has one in range: candidates = those in prev
target = argmin (camp hp, y, x, camp id)
```

The `confirm` cohort, scored with a frozen rule. 81% of camp attacks have only one target and are not
counted:

| Rows with 2 or more candidates | Rule | min (hp, id) | Uniform random |
| --- | ---: | ---: | ---: |
| all | **19,440/20,646 (94.16%)** | 78.28% | 42.3% |
| several groups in range | 4,408/4,937 (89.28%) | 40.90% | 31.4% |
| tied lowest hp (the `(y, x)` tie-break decides) | 3,260/3,671 (88.80%) | 35.63% | |

- **Group retention**: with several groups available and the previous one still among them, Fish
  stays on it in 4,170/4,286 (97.29%).
- **A new group**, when the previous is gone, is chosen correctly in only 289/651 (44.39%).
- Fish also hits altar tiles with basic attacks (about 540 per cohort), removing enemy locks.

### 7.4 Capture holders and entry

- **The highest-ranked holder stays** (exploratory replication on `confirm`). Holder rank is the
  section 2 order.
  - Opportunities: on an empty group, with another visible ally on its tiles, no enemy visible.
    Predict "stay" when self ranks highest among the visible holders.
  - Result: 1,519/1,535 (98.96%), against 64.84% stay overall.
  - Marcella stays in 321/322.
  - The model was frozen after other `confirm` metrics were seen, but before holder rows were built.
- **A lone holder stays** [H, third]: 6,341/6,400 (99.08%) with no other visible holder.
- **Lower-ranked holders** [H, third: 801/1,065 (75.21%) vs always-leave 59.91%]:

  ```text
  self_timer, best_timer = recall timers of self and of the highest-ranked visible holder (0 if none)
  if best_timer > 3:  leave iff h > 0.406          (fitted)
  else:               leave iff self_timer > 3 and free exits > 3
  ```

  - "Free exits" are adjacent tiles off the group, unblocked by terrain or visible units.
  - Both recalling with timers 1-3 → stay: 143/148 (96.6%).
  - Example asymmetry (discovery): Issac leaves Cassi in 62/94 pairings; Cassi leaves Issac in 0/46.
- **Incoming entry** [H, fifth]: enter iff self outranks the best visible current holder. The fitted
  tree adds one exception: decline at capture timer ≤ 1 with own gold ≤ 12.
  - Rows: off the group, a free adjacent camp tile, a visible allied holder, no visible enemy.

    | Outcome | Rule | Rank alone | Never enter |
    | --- | ---: | ---: | ---: |
    | enters by turn end | 3,033/3,638 (83.37%) | 82.68% | 72.07% |
    | entry held through an observed payout | 3,256/3,628 (89.75%) | 88.62% | 79.93% |

  - It does not separate replacing an incumbent from sharing its payout.
- **Tribute while capturing: almost never** [H]. Within 1 of an altar with gems, on an empty group,
  Fish starts a tribute in 4/27 HELD frames, against 462/2,190 off a capture.

### 7.5 Waking and camp micro

- **Wakes alone, whatever the group** [H]. The waker is the first Fish damage to a fully asleep group.
  "Alone" means no other Fish champion is within 4. Rates: Monolith 146/232 (63%), Golem 203/382
  (53%), Elk 51%, Wolf 55%.
  - There is no crew wait; allies arrive before the clear.
  - Wakers are often squishy: Cassi 1,837, Issac 1,481, Willow 789 held-out wakes.
- **Staying in camp range** [H, 7]. Opportunity: a champion hit by a camp whose group is still awake
  next phase, on rows where it could leave that turn.
  - It stays in **87.3%** of 16,245 held-out rows (seventh 87.6% of 31,435): melee 92.2%, ranged
    47.9%.
  - On the range edge (one step leaves): 55.3% (seventh 54.9%).
  - One inside the edge: 91.0%. Two inside: 97.2%.
  - So Fish does not walk two or more tiles to escape camp fire. At the edge it steps out about half
    the time, and ranged champions that do not attack leave about half the time.
  - Camp kills are rare: 8 held-out champions dead by the next camp phase.

---

## 8. Economy

### 8.1 Prepared recall [X]

- **Fish starts a recall after its other actions on almost every turn off spawn.** All 504,415
  sampled eligible `model` turn ends do so (alive, unstunned, off spawn, no channel).
- **It usually cancels it next turn.** The channel survives to the next turn in 16,651 of 434,104
  next-turn choices (3.8%).
- Elsewhere than on a camp, 7,773 FIT timer-4 channels go on to arrive, against 965,310 cancelled at
  timer 4 and 11,285 kept, then cancelled.
- A recall start is therefore not a retreat. Completing one needs four turns with nothing better to do
  and the gate below.

### 8.2 Going home [H]

**The home gate** (necessary, near-exact). At the last keep (timer 1) of a completed recall home:

```text
h <= 0.63  or  gold >= 30            (fitted thresholds; 30 = one shard)
```

- It holds in **5,563/5,643 (98.58%)** HELD completed recalls (FIT 97.55%). Health alone covers
  2,906 and gold alone 3,798.
- Health 0.62-0.63 and gold 30 are flat optima. The gem-weighted health fits worse.
- The gate is not sufficient. After its own payout, healthy, with no enemy seen: next endpoint is
  home in 36/622 (5.8%) with gold < 30, and in 1,885/4,267 (44.2%) with gold ≥ 30.
- Of HELD completed recalls: retreat (h ≤ 0.63) 2,906, shop (healthy, gold ≥ 30) 2,657, other 80
  (1.4%).
- Recalls used as travel shortcuts are at most about 1%. Example: on `04atoll`, Marcella recalls 36
  steps out to reach the altar via spawn.

**The timer-1 keep rule:**

```text
at a turn starting with the recall channel at timer 1 (alive, unstunned, off spawn):
  standing on an empty group (capturing):                    keep iff h <= 0.40
  on a respawning group's tile in its payout round
    (its respawn countdown still reads the full 40/50/60/80/150):  keep iff h <= 0.63
  otherwise:                                                  keep iff h <= 0.63 or gold >= 30
```

- **11,044/12,192 (90.58%)** HELD, against 53.26% always-cancel and 74.86% for health alone. FIT
  89.23%.
- By branch: capturing 3,959/4,043; payout round 2,003/2,765 (the weak branch); later rounds on a paid
  tile 1,118/1,155; elsewhere 3,964/4,229.
- Of the 1,653 keeps on `third`, 1,640 arrive; 11 are interrupted.

**Walk or recall** (free rows). Fish takes the faster way home: it walks when the walk is at most 5
steps, and recalls otherwise.
- **5,197/5,414 (95.99%)** HELD with a camp-aware walk, against 84.37% always-recall.
- By band: ≤ 4 steps walks 97.8%, 5 steps 86.7%, ≥ 6 steps recalls 96.4%.

**Hurt arrivals wait the turn out on spawn** [H, 7].
- A recall arrival short of full health stays on spawn that turn in **4,224/4,224** HELD and
  **7,398/7,398** seventh. Full-health arrivals stay in only 47.0% (seventh 45.6%).
- Hit on the spawn since its last turn and short of full: stays in 99.5% (seventh 99.3%).
- Respawn turn at full health: stays 38.5%.

**Enemies near the spawn** [D, six cohorts].
- Leave rate from spawn by the nearest visible enemy's distance to Fish's spawn, 1 to 8: 24, 23, 26,
  34, 39, 48, 46, 65%. With no visible enemy: 45%.
- After a respawn there is no extra caution beyond this.
- Fish rarely camps the enemy spawn: 100 of 17,392 held-out basics hit an enemy on its own spawn.

### 8.3 Tribute [H]

**Non-Prism champions: altar distance decides, not a fixed bag.** After a payout, carrying gems, with
no enemy:

```text
tribute next iff  altar_walk <= ready + 2  and  gems >= 8 * (altar_walk - 2)
altar_walk = walk to a tile beside the nearest altar
ready      = min over other groups of max(walk, remembered respawn wait); unseen groups assumed alive
```

- **3,586/4,275 (83.88%)** HELD, against 76.02% never-tribute. With an altar within 12: 72.55%
  against 52.86%.
- Distance carries most of it: `altar_walk ≤ 5` alone gets 3,546.
- Race state is only a trend. Where the rule says tribute, the rate rises from 69% (enemy score
  < 200) to 81% (≥ 800). Where it says not, tributes go from 10% before round 400 to 27% after
  round 800.
- Tributed bags, median [10%-90%] (all cohorts): Marcella 33 [12-97], Vendetta 36 [8-111], HoR 28
  [8-77], Cassi 20 [7-56], Issac 17 [7-46], Vesper 57 [12-487], Willow 14 [7-44].

**Prism banks only a winning bag** (exact on a small sample):

```text
Prism starts a tribute only if  own bag + team score + bags of all allies in sight >= 1000
```

- 61/61 FIT starts (11 games) and **8/8 HELD (4 games)**. The smallest margin is 2.
- Whether unseen allies' bags count cannot be told.
- The condition is not sufficient: with it true beside an altar, Prism starts in 10/22 FIT frames.
- Prism otherwise carries its gems (+1.5 Focus each): it tributes after 2 of 68 HELD payouts.

**Altar choice.** On maps with 2 or more altars, the tributed altar is the nearest by walk at the
walk's start in 2,192/2,294 (95.55%) HELD walks (no baseline was built).

**Channels** (HELD). Of 3,490 tribute starts, 3,180 complete and 50 are cancelled by Fish; the rest are
interrupted.

**Payout-time forecast** (approximate) [H]. A fitted depth-4 tree forecasts the next of farm, home and
tribute after a payout: **62.64%** of 5,326 HELD episodes, against majority "home" 40.31%. Its top
splits:
- nearest altar walk ≤ 8 and payout gems > 6 → tribute;
- payout gold > 74 (an Elk- or Golem-sized share) → home;
- small payouts → farm.

### 8.4 Shopping [X]

```text
at the very start of a turn that begins on Fish's own spawn, or while dead:
    buy a teleport crystal (on crystal maps only; condition unknown)
    buy an altar lock if this is a lock map (below), none is carried, and (gold - 10*crystals) mod 30 >= 10
    buy floor((gold - 10*consumables) / 30) shards, in the build order of section 3.2
```

- Alive, starting on spawn with gold ≥ 30: shops in 13,228/13,232. Dead with gold ≥ 30: 834/834.
  Never off spawn: 1,715,297/1,715,297 turns.
- The shard count matches in 10,340/10,340. The lock rule matches in 2,825/2,827.
- Gold is never kept back to finish an emblem: 28.6% of HELD healthy shop recalls carry less than
  the emblem's remaining cost.
- Shopping happens before any walk, attack or cast in 13,389/13,389 shop turns.

### 8.5 Altar locks

- **Which maps** [X; H on new maps]. Purchases are all-or-nothing per map: 116/116 maps.
  - `gap` = (enemy spawn's walk) − (own spawn's walk) to beside the altar nearest Fish's spawn, with
    walls, holes and altars blocking and camps not.
  - **Locks iff gap ≤ 4**: 112/115 maps (always-lock 76/116), and 7/7 maps first seen in the fifth
    cohort.
  - Misses: two maps at gap 5 that lock, and one single-altar map that never does.
  - On 202/210 lock games the first lock is bought at the first shop with ≥ 10 gold left over. Eight
    games start later, for unknown reasons.
- **Where** [D]. Of 1,506 placements, 82% are from distance 2 and 66% at Fish's nearest altar.
  - 48% are followed by the placer's own tribute there within 3 turns; 500 are placed with no gems.
  - Only 93 come while an enemy is visibly tributing there: locks are pre-banking and territorial.

### 8.6 Teleport crystals [X]

- Bought on 17 of 116 maps, never on the other 99.
  - On 8 maps, at every shop turn without one (e.g. `00pilgrimage` 214/214).
  - On 9, sporadically.
- **881 of 883 teleports go exactly 3 tiles**, the maximum.
  - For 744 (84%), the walk between the tiles is ≥ 40 steps or impossible.
  - 255 distinct (map, from, to) hops cover all 883. E.g. `02tangle` (12,26)→(9,29) is used 50 times.
- They are per-map wall-crossing shortcuts: only 113 of 738 are taken with an enemy visible.

---

## 9. Behaviour around enemies at range (distance 4-8)

There is **no strategic engage mode**. Fish farms, and enemies bend its farming in proportion to their
closeness and threat.

**Momentum** [7]. On free turns (alive, off spawn, nearest visible enemy at 4-8, no camp hit, not on an
empty group):

```text
close on that enemy this turn  iff  the previous step, continued, would close
```

- **70.8%** of 124,995 seventh free rows, against never-close 54.5%. HELD 70.9% against 54.4%.
- Fit-grid overrides do not add anything: closing on prey (enemy h ≤ 0.3-0.4) and never closing
  below h 0.3 both reach 71.0%.
- Descriptive (HELD):
  - closing falls from 47.0% at h ≥ 0.5 to 16.4% at h < 0.5;
  - it is 67.6% when the enemy has h < 0.4;
  - it falls from 47.9% with one enemy in sight to 33.9% with three or more.

**The route bends by health** [7]. The hindsight farm goal is the end tile of the actor's next
camp-hit turn within 40 rounds; it is used only to label, never as an input. "Trade rows": a legal
progress step toward it exists, but every such step closes on the enemy.

```text
progress iff h > 0.5      seventh 69.8% vs always-progress 65.8%; HELD 71.1% vs 65.9%
```

- Progress rates: h ≥ 0.5 70.3% (seventh 69.5%); h < 0.5 21.4% (seventh 26.4%).
- Where a non-closing progress step exists, Fish detours toward an enemy below 40% health: it closes
  58.6% against 31.8% otherwise (seventh).
- Route progress falls smoothly with proximity: 68.2% at 8 down to 51.2% at 4 (HELD).

**Danger-weighted steps** [7]. Among legal route-progress steps whose danger differs (enemy at 3-8),
the step taken is a minimum-danger one in **67.7%** of seventh rows, against 51.3% for a random step.
- When hurt (h < 0.5): 85.5% against 50.4%. HELD: 69.2% (51.8%), hurt 88.4% (49.2%).

**Camp hitting falls with enemy distance** [7]. Opportunity: last turn hit a camp, an awake camp is
still in reach.

| Nearest enemy | none | > 8 | 8 | 7 | 6 | 5 | 4 | 1-3 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| keeps hitting (HELD free rows) | 96% | 89.1% | 85.3% | 85.5% | 79.1% | 67.6% | 44.8% | 18.2% |

- `keeps hitting iff nearest enemy > 4`: seventh 80.8% against always-hit 77.5%.
- With an enemy's `D` reaching the tile: 32.1% (healthy), 14.5% (hurt).

**No pursuit beyond sight** [7]. After losing sight of a target hit within 2 rounds, over the next 5
turns (free turns):
- Fish closes on the last-seen tile 20.7%, opens away 44.4%, against a mirrored placebo's 15.7%.
- HELD: 22.2 / 42.5 / 15.3%.

**No hunting** [7]. With no enemy in sight, but memory of a live enemy seen 2-10 rounds ago at 9 or
more tiles, Fish closes on its last-seen tile 45.1% against placebo 44.5%.
- The only trace of attraction beyond sight is a remembered weak enemy: 46.7% vs 36.1%.

**No rally** [7]. A blind ally 10-24 tiles from a teammate's fight drifts toward it no more than in
quiet control periods. The excess is 0.1-0.25 tiles in 5 turns at 10-19, none at 20 or more.

**Walking retreat is a graded tendency, homeward** [7].
- Rates (HELD; an enemy within 3 at the start; retreat = ≥ 2 farther after 3 own turns with no hit):

  | | h ≤ 0.54 | h > 0.54 |
  | --- | ---: | ---: |
  | all | 42.8% | 14.7% |
  | outnumbered by 2 or more | 45.1% | 23.2% |
  | on a running capture | 30.4% | 7.2% |

  Carrying, a recent ally death and outnumbering each add a few points.
- The best threshold, `retreat iff h ≤ 0.36 and side EHP ratio ≤ 1.3` (fitted), barely beats
  never-retreat: seventh free 78.5% vs 77.2%.
- **Direction.** Where the first step away has both homeward and non-homeward options, Fish's step
  away is homeward **91%** of the time, against 44% for a random legal step away (seventh; HELD 89% vs
  43%).
  - Retreats move toward the nearest visible ally 59% vs away 29%.
  - They do not seek bushes, and they move away from altars (54% farther).
- **How retreats end** (seventh): re-engage 33%, reach spawn 30%, farm 24%, die 7%, tribute 4%.
  - Below h 0.3, 56% reach spawn (HELD).
  - When it resumes farming, it is the same group in only 29.5%.

**After a kill** [D; the predictive version fails on seventh]. Within 40 turns:
- it fights on in 46-53% of cases if another enemy is in sight, and in 7-8% if none is;
- with no one left in sight, the bag decides: tribute follows 4.9% of kills with a bag of 0-9 gems
  and 33.5% with 30 or more (HELD);
- kill gold (100) passes the home gate's gold ≥ 30 (section 8.2), yet only 21-28% go home.

---

## 10. Combat in contact

### 10.1 Positioning [7]

Three contexts, each a real choice (an alternative tile exists, off spawn):

| Context | Engage means | Decline means |
| --- | --- | --- |
| m2: melee, nearest enemy at 2 | ends adjacent, or hits a champion with a spell | stays out |
| m1: melee, adjacent | stays adjacent | steps away after attacking |
| r: ranged, nearest enemy within 3 | does not increase the distance | backs off |

```text
engage iff kill available from an engage tile
        or (h > 0.49 and min danger over engage tiles <= 0.28)        (fitted thresholds)
```

| | Seventh | Baseline (per-context majority) | HELD |
| --- | ---: | ---: | ---: |
| all | **20,292/27,589 (73.6%)** | 57.2% | 72.7% (56.5%) |
| m2 | 7,224/9,826 (73.5%) | 42.1% | 73.0% |
| m1 | 6,942/9,354 (74.2%) | 69.5% | 72.8% |
| r | 6,126/8,409 (72.9%) | 61.0% | 72.5% |

- Errors are mostly predicted engagements that Fish declines: healthy, low-danger refusals.
- The gem-adjusted health (`0.41 / 0.28`) scores the same.
- A gradient-boosted ceiling over 20 turn-start features reaches 76.6% HELD.
- Melee adjacent to an enemy always attacks, then steps away (discovery) in: 18% at full health, 31%
  at 70%, 42% at 50%, 67% at 30%, 76-78% at 0-10%.
- Allies agree on fight or flee in the same round only slightly more than chance (47.7% vs 39.4%).

### 10.2 The kill override [7]

When a kill is available from an engage tile, Fish engages in **1,259/1,275 (98.7%)** of seventh
turns, against a 63.4% baseline.

It extends to dashes [H]. When the nearest enemy is beyond walk-and-hit reach but inside dash reach
(melee at 3-4, Vesper 4-5, HoR 2-3), and some landing gives a kill, Fish dashes in:
- **111/126 (88.1%)**, against never-dash 11.9%.
- Without a kill it dashes in on only 26% of healthy, low-danger opportunities. No threshold explains
  that decision.

### 10.3 Chase [7]

Opportunity: last turn hit enemy E; E is now the nearest visible enemy but out of basic range.

```text
chase iff E.h <= 0.37
       or (side EHP ratio (own + allies within 8 / enemies) > 1.24 and own gem health > 0.44)
       (fitted thresholds)
```

- **6,951/9,465 (73.4%)** seventh, against always-chase 61.2%. HELD 72.4% vs 58.3%.
- Chases are short. Of 2,270 HELD streaks: 1 turn 1,180, 2 turns 496, 3 turns 222, 4 turns 167,
  5 or more 205. Chases end when sight ends (section 9).

### 10.4 Basic and spell targets [7]

```text
basic attack target   = argmin (EHP, id)          over visible enemies in basic range
unit damage spell     = argmax (gems + 8) / EHP   over visible enemies within 4, lower id on ties
                        (Cassi slot 0, Marcella slot 1; 8 is a fitted offset)
Cassi's stun (slot 1) = argmax (Strength, then lower id) over visible enemies within 4,
                        excluding Marcella (stun-immune) and enemies with a positive stun timer
```

| Rows with 2 or more candidates | Seventh | HELD | Baseline |
| --- | ---: | ---: | ---: |
| basic: min EHP | **2,836/3,029 (93.6%)** | 94.4% | — |
| unit damage: `(gems+8)/EHP` | **595/653 (91.1%)** | 423/462 (91.6%) | min EHP 78.3% (HELD) |
| — where another enemy carries more gems than the min-EHP one | | 111/134 (82.8%) | min EHP 37.3% |
| Cassi stun: max Strength | **171/189 (90.5%)** | 86.0% | lowest raw hp: 127/253 on `confirm` multi-enemy rows, where the rule gets 242/253 |

- Fish attacks a champion over a camp when both are in range: 1,649/1,650 (original holdout).
- **Basics ignore gems and channels** [H]: `(gems+8)/EHP` gets 80.0%, carriers-first 76.5% and
  channellers-first 67.7%, against min EHP 94.4%.
- **Marcella's reset-stun re-hit**: with 2 or more enemies in reach at the second basic, the stunning
  basic hits the first basic's target in 268/268 (all cohorts). That includes 17/17 where min EHP
  points elsewhere (5/5 seventh).
- **Prism's ground spell** centre is the tile within 4 with the most visible enemies within 1, camps
  ignored: 63/64 seventh, 89/91 HELD.
- **Unknown:** the unit-stun targets of Prism and Ren (too few rows; section 13).

### 10.5 Casting: when spells go out

- **Exclusive damage spells** (Cassi slot 0, Marcella slot 1, Prism) [7]. Standing still, with the
  spell ready and the turn's cast unused, Fish casts in **95.4%** of 11,819 free rows (seventh 94.7%),
  against 4.6% for never.
  - The real decision is standing versus walking. From turn-start state, "cast iff the start tile is
    acceptable" predicts the cast in **69.3%** (seventh 70.2%) against never-cast 49.5%.
- **Prism** [7]. Standing, it casts in 302/308 (seventh 70/75).
  - With both slots ready it casts slot 0 (the unit damage-plus-stun) in 60/65.
  - From turn start it casts in 60.9% of opportunities.
  - Its unit stun ends as often in a kill as a stun (seventh: kill 15, stun 20, wasted on Marcella
    15).
- **Ren's stun** [7]. Standing, it casts in 338/349 (seventh 170/174). It stands on only 33.8% of
  opportunities.
  - Prism's and Ren's damage stuns do not skip stun-immune Marcella.
- **Cassi** [7]. With damage on cooldown she stuns in **2,354/2,379 (98.9%)**.
  - With both spells ready she casts something in 97.4% (damage 822, stun 1,384, none 58).
  - Her damage-or-stun choice is not recovered: always-stun 61.1%, damage-iff-acceptable 57.2%.
- **Heart of Ruin's shield** [7, free rows with no dash cast]:

  ```text
  shield iff a visible unstunned enemy has D > 0 against HoR
  ```

  - 20,357/21,864 (93.1%) seventh, against never 83.8%. All cohorts: 93.2% vs 83.7%.
  - Threatened: shields 95.2% (6,793/7,134). Unthreatened: no shield 93.0%. Camp damage, not
    modelled, probably explains the rest.
- **Willow's heal** [H, all cohorts free rows]:

  ```text
  heal iff any visible ally within 4 is injured
  ```

  - 94.9% of free rows (seventh 94.9%), against never-heal 76.6%. Injured allies are healed in 86.2%
    of free turns.
  - She heals on 59/65 turns where the largest injury is ≤ 20 hp.
  - **Target** (original holdout, given a heal): max `min(missing hp, 3 × Focus) / ally max_hp`,
    312/348 (89.7%). Lowest health fraction gets 311/348, so the two cannot be told apart.
- **Melee with an enemy within 1** attacks in 2,368/2,377 (99.6%; `third`).

### 10.6 Attack resets [7]

After a basic attack on a champion that survives, with the reset ready and the turn's cast still
unused, Fish resets and attacks again:
- **94.6%** seventh (3,012/3,184); all cohorts 94.0% (9,892/10,527).
- In 482 of the misses the cast went to another spell instead: Vendetta's or Issac's dash to reach,
  or Marcella's damage spell.
- Ranged resets (Vesper, Willow) are mostly walk, reset, attack, and are not modelled.

### 10.7 Dashes and landings [H]

Landings are scored only where the key differs among legal landings:

| Rule | HELD | Random legal landing |
| --- | ---: | ---: |
| HoR engage dash lands where the most visible enemies are within 1 | **882/896 (98.4%)** | 15.9% |
| Escape dash lands on a minimum-danger tile | **1,158/1,196 (96.8%)** | 46.6% (79.0% among farther tiles) |
| — farthest from the nearest enemy | 88.8% | 24.2% |
| — nearer home than before | 70.7% | 37.6% |

- Escapes minimise danger first; home is secondary.
- The exact tile is not recovered: lexicographic orders reach 35-47%.
- About 75% of dashes (77,809 of 93,357) happen with no enemy within 6, as travel.
- Order within the turn: melee dashes are dash, walk, attack; HoR's are walk, dash, attack.
- **Escape timing is not a threshold.** No (h, danger) rule beats never-escape (92.5%). Escape rates
  rise from about 3% at full health to 20-30% below 20%.

### 10.8 Spacing [7]

Population: completed contact turns off spawn, enemy within 5, walking without a dash.

```text
ranged, a melee enemy within 2, walks:     ends >= 3 from every melee enemy
ranged, walks and stays within 3 of one:   maximises distance (capped at 3) to the nearest melee enemy
any decline (walks to a farther tile):     the lowest-danger farther tile
```

| End tile in the rule's set | Seventh | Random candidate |
| --- | ---: | ---: |
| ranged kite from melee within 2 | **950/1,041 (91.3%)** | 38.4% |
| ranged stays in range, farthest from melee | 1,795/2,083 (86.2%) | 45.6% |
| ranged decline, min danger | 307/349 (88.0%) | 59.2% |
| melee decline, min danger | 1,279/1,491 (85.8%) | 58.9% |

- Whether to kite at all is close to a coin flip. A ranged champion with a melee enemy within 2 and an
  escape tile ends ≥ 3 away in 55.2% of seventh turns (always-stay 44.8%).
- At turn end, ranged champions end 3 or more from every melee enemy in 93.0% of free rows, against
  88.1% for a random tile.
- Cassi's modal distance is 4-5 tiles (25%, 29%), her spell range.
- Melee champions follow no end-tile rule beyond their target.

### 10.9 Kill securing and no focus fire [7]

```text
each champion applies its own target rule at the moment it acts; nothing team-level
```

- **The first capable actor kills** (the first Fish actor whose kill reach covers the enemy):
  **2,070/2,335 (88.7%)** seventh, 84.2% HELD.
- **Nobody holds a kill for a teammate.** "No hit, then a later ally kills it": 20 of 2,335 (0.9%)
  seventh, 0.5-0.7% elsewhere.
- **Convergence is a by-product.** A later hitter joins an earlier Fish hitter's target in 84.2% of
  seventh rows, against 81.7% predicted by min EHP and 52.5% for a random candidate. Where min EHP
  points elsewhere, it joins only 25.7%, against a random 46.7%.
- Kills of enemies in camp fire are taken at the usual rate (85.6% vs 89.1% clear). Fish hits enemies
  in camp fire less often (35.7% vs 48.3%), so it does not exploit camp aggro.

### 10.10 Enemy channels: no interruption priority [H]

Hit rate on a reachable visible enemy:

| Enemy state | Hit rate |
| --- | ---: |
| not channelling | 56.0% |
| recalling, started this round (timer 4) | 40.2% |
| recalling, kept a turn or more | 36.9% |
| tributing | 48.5% |

- Fish lets adjacent or in-range recallers go more often. Where the positioning rule says engage, it
  does so against a recalling nearest enemy in 67.3% (m1) and 67.4% (r) of turns, against 86.9% and
  84.7% when the enemy is not recalling.
- Tributers are stunned at the base rate: 16/86 (18.6%) against 18.8%.

### 10.11 Captures under threat [H]

- **A running capture holds against danger.** On a hold where Fish's tile is unacceptable, it stays
  in 197/264 (74.6%); the positioning rule's decline prediction (section 10.1) scores 27.3%.
  - At capture timer 1-4 it stays in 80% (714/891, all cohorts); at 5 or none, 51%.
- **Contests.** Fish hits an enemy standing on the group in 79% of turns where that enemy is in reach.
  It stays iff acceptable at h 0.45: 79.5% vs always-stay 76.7%.
- **An enemy-held group beside Fish.** It hits the holder (488/922) far more often than it steps onto a
  free tile (182/841).

---

## 11. Team coordination

**Coordinated or shared:**
- **Camp knowledge** (section 7.2). Destinations follow the newest state any earlier teammate saw,
  mostly respawn timers. This is presumably carried in the 8 shared bytes.
- **Turn order** (section 5). One encoding. The quiet order hands camp tie hits to healthy, gemless
  champions; the late mode hands contested camp hits to the enemy; contact gives the most threatened
  champion back-to-back turns.
- **Late mode spreads across the team** (7,990/14,091 vs 4,963/126,726).

**Not coordinated:**
- **Joining, never partitioning.**
  - A visible ally closer to a group makes Fish more likely to go there (`ally_closer` > 0).
  - Same-round co-deciders: when the later one's own top choice is the earlier one's group, it goes
    there in 89-91%.
  - Allies' commitments more than 8 tiles away add nothing (+0.1 point).
- **No team targeting, no kill holding** (section 10.9).
- **No rally to unseen fights, no crew wait** (sections 7.5, 9).
- **No team-wide fight or flee mode** (47.7% vs 39.4%).
- **No zones** (67% payout-group overlap between champions).
- **Hidden ally knowledge beyond camp states**: observer-truth ally positions add at most 0.4 points
  to destinations.
- **Willow** has no fixed escort; she most often ends nearest Cassi.

---

## 12. Wards and bushes

- **Bush pathing** [7]. Among steps making the same progress toward where the actor stands three
  turns later, Fish steps onto a bush:
  - 73.1% in contact (random 44.0%);
  - 78.3% with an enemy visible farther away;
  - 71.1% with no enemy (45.2%).

  The same tie-break holds in contact among tiles at equal distance to the enemy (72.2% vs 44.4%).
  It is a habit, not an ambush.
- **Hits from bushes** [7]: 84.7% unseen on a bush, 87.1% seen on a bush, 80.0% in the open.
- **Ward rate** [7]. With the ward ready, Fish places one on:
  - 8.0% of contact turns (4,726/59,125);
  - 5.0% of turns with an enemy visible;
  - 2.9% of turns with none.
- **Ward tiles.** In contact the tile is on a bush in 69% (seventh). Wards land farther from the
  nearest enemy than the actor more often than nearer (3,916 vs 2,507, FIT). They scout bushes, not
  the enemy.
- **Geometry** [D]. Of 42,469 placements, 88.73% are at distance 2 and 78.80% on a bush.
- **Allied-ward collisions** [X]. 32,015 of 32,417 failed ward inputs (98.76%) target a teammate's
  current ward tile: Fish does not track allied wards. After such a failure it places elsewhere on
  2,489 turns and gives up on 27,187.

---

## 13. Refuted hypotheses (do not retry)

Destinations and farming:
- **astraeus's closed-form `rate()` = worth / (R(1+R/H))**: 40.72% HELD, against the logit's 63.63%
  and wait 49.66%. With grid-searched constants: 50.49%.
- **Per-map circuits** (lookup by map, side, champion, reason and previous group): 51.6% vs 65.7% on
  the same rows.
- **Claims or partition.** Opening greedy value-split 19.0%. Remote commitments +0.1 point.
  Sequential exclusion: none (89-91% join).
- **Deciding the next trip at payout**: payout-time rank picks the post-spawn destination in 24.0%,
  spawn-time rank in 57.3%.
- **Score lead or enemy liveness terms**: 63.48% vs 63.63%.
- **Return to the last off-spawn position after spawn**: 17%.
- **Opening = nearest camp**: 42.3%. Reward-rate: 47.6%. Best opening rule tried: 56.7%.
- **A reward-rate grid score for new camps**, `(gold + 0.25·gems) / (4 + wait + hp term)`: 39.08% vs wait 46.20%.
- **Restrict to visited groups / follow the most frequent transition**: 42.58% / 42.06% vs wait
  47.68%.
- **"Follow the leader", decide at recall start, remembered ally positions** as destination features:
  no gain.
- **Observer truth on groups no teammate saw more recently**: 63.34% (no gain), so Fish infers no
  hidden camp state.
- **A crew requirement before waking big groups**: Monoliths are woken alone 63% of the time.
- **"Never leave a capture without a visible replacement"**: 59 departures of 6,400.

Economy:
- **A fixed gem threshold for tribute.** Marcella starts at 4 gems and declines at up to 208.
- **Prism's gate counting only allies already tributing**: 57/61 FIT, 5/8 HELD.
- **Timer-4 recall arrival classifier**: 98.76% vs baseline 98.75%; finds 21 of 1,848 arrivals.
- **Gem-weighted health in the home gate**: fits worse (23,598 vs 23,991).
- **Cassi/Issac partner-follow** as the explanation of recalls without the gate: 16/187.

Combat and tactics:
- **"Positive priority in combat, negative otherwise"**: 7,824 negative writes on attack turns.
- **A numbers or power threshold for engaging**: best 64.5%, vs the danger rule's 72%.
- **A discrete engage/avoid decision at range**: no threshold beats momentum. Trees over 36 features
  reach 59-61%.
- **An unacceptable tile (section 2) as the walking-retreat trigger**: 73.8% vs never-retreat 78.8%.
- **A threshold for the engage dash or escape dash decision**: grid 78.5% vs majority 78.4%; escape
  92.5% = baseline.
- **Interrupting channels.** Channellers first: 23.2% vs min EHP 92.8%. Recallers are hit less, not
  more.
- **Gems weighing basic attacks**: 80.0% vs 94.4%.
- **Focus-fire, own-target, retaliation and unstunned-first terms on basics**:
  - an ally's target 27.3% where it differs;
  - own previous target 15.3%;
  - retaliation 4.1%;
  - unstunned first 41.5%;
  - the best focus bonus gains 14/6,254.
- **Cassi stunning enemies yet to act**: 23/57 vs random 28.1.
- **Exact step choice as a 9-tile logit**: 31-38% vs "stay" 19-33%.
- **After-kill rule "fights on iff another enemy in sight"**: seventh 64.7% vs never 69.4%.
- **Early priority mode as an engage intent**: it is end-tile geometry.
- **Pursuit by memory, hunting, shared-memory rallies, bush ambush or bush retreat**: see the
  numbers in sections 9 and 12.
- **Camp-fire avoidance as a tile rule**: 56-63% vs 48-49% random.
- **Shared or draft memory readable from replays**: both read zero all game, for every team.

---

## 14. Open questions

- **What Fish writes to its 8 shared bytes.** The camp summary (group and round of clears or respawn
  timers?) and possibly the late flag.
- **The opening's joint plan.** It is deterministic per map and often a pack, but no rule reaches 57%.
- **Post-spawn destination choice**: 58% on seventh.
- **Stand-and-cast versus walk**: 69% from turn start. Ren stands on only a third of opportunities.
- **Cassi's damage-or-stun choice** when both are ready.
- **Prism and Ren unit-stun targets.**
  - Prism `(gems+8)/EHP` 24/30, min EHP 22/30.
  - Ren `(gems+8)/EHP` 35/48, min EHP 32/48.
- **What triggers the early priority mode** inside its band, and what seeds the late mode beyond the
  contest rule.
- **Healthy "spacing" retreats**: what makes a healthy champion back off (14.7% at h > 0.54).
- **Home-gate sufficiency.** Why only 44% of healthy post-payout champions with gold ≥ 30 go home,
  and why kill gold rarely sends Fish home (21-28%).
- **Incoming capture entry**: replacing the incumbent versus sharing its payout.
- **Prism's declines with a winning bag**, and other types' adjacent-altar declines (lock memory is
  not in the data).
- **Crystal maps and crystal use timing**; the late first lock in 8 games.
- **Candidate rules seen only in-sample** (not confirmed on held-out data):
  - Lock placement: place iff some altar within 2 has no lock of either team. 3,510/4,035 (86.99%)
    vs never-place 63.47%, across five cohorts. Fish's own lock memory is the likely missing input.
  - Ward tile: the tile within 2 that adds the most bush tiles unseen by the actor's sight and current
    ward. Chosen in 80-86% of turns with a positive score, against 10-12% for a random tile (`model`
    and `fifth`, 40 games each). The tie-break is unknown.
  - Ward cadence: no trigger found. 21.5% of ward gaps are exactly 10 rounds.
- **Submission versions**: whether one Fish build played every game is unknown.

---

## Appendix: provenance

All in `research/fish-2026-11-05/`. Numbers were checked against the named JSONs.

| Section | Source report | Main JSON |
| --- | --- | --- |
| 1 Data | README, CONTINUATION, DECISIONS, ROUTES, CHOICE, FARM-CHOICE, FARM3 | `*-manifest.json`, `seventh-audit.json` |
| 3 Draft, emblems | DRAFTS-EMBLEMS; MICRO (never-drafted) | `drafts-emblems.json` |
| 4 Opening | FARM3 §4, MISC §5 | `farm3-explore.json`, `misc-opening.json` |
| 5 Priority | TEAM §1-2, README §1, ENGAGE §1d | `team-modes.json`, `team-priority.json`, `team-aggro.json`, `priority-ranks.json` |
| 6 Turn shares | FARM3 §1a, ENGAGE §6 | `farm3-describe.json`, `engage-results.json` |
| 7.1-7.2 Camp choice | FARM3, FARM-CHOICE, CHOICE | `farm3-fit.json`, `farm3-seventh.json`, `farm3-explore*.json`, `rule-audit-farm.json` |
| 7.3 Camp target | CONTINUATION §1, FARM3 §6 | `breadth-confirmation.json`, `rule-audit-farm.json` |
| 7.4 Holders, entry | CONTINUATION §3, DECISIONS §2, ROUTES §2, CHOICE, ECONOMY §7 | `holders-replication.json`, `decisions-confirmation.json`, `incoming-payout-fifth.json` |
| 7.5 Waking, camp range | TEAM §3 and audit | `team-campfight.json`, `rule-audit-engage.json` |
| 8 Economy | ECONOMY, CONTINUATION §4-5, MISC §1-3, TACTICS §5 | `econ-home.json`, `econ-tribute.json`, `econ-payout.json`, `misc-*.json`, `rule-audit-engage.json` |
| 9 Range behaviour | ENGAGE | `engage-results-seventh.json`, `engage-lost-seventh.json`, `rule-audit-engage.json` |
| 10 Combat | COMBAT, TACTICS, MICRO, DECISIONS §4 | `combat-results-seventh.json`, `rule-audit-micro.json`, `micro-*.json`, `tactic-*.json` |
| 11 Team | TEAM, FARM3 §3-4, CHOICE, MICRO, ENGAGE §4 | as above |
| 12 Wards, bushes | MICRO §4, MISC §4 | `micro-bushward.json`, `misc-wards.json` |
| 13-14 | all reports' negative results and HANDOFF's open list | |
