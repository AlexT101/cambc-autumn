# Fish: team coordination through turn order, and how it fights at camps (2026-11-05)

This report covers how Intercontinental Fish uses turn-order priority, and what it does once it is
at a camp. Camp-target selection is out of scope; see [FARM-CHOICE.md](FARM-CHOICE.md).

Fish's priority has one structure, `priority = -rank - (N+1) * L`, in every mode, including the
large ±500..800 values. A selector from Fish's own view reproduces the mode of 93.6% of held-out
turns with an enemy visible (always-quiet baseline 64.6%). The selector has four rules:

- dead;
- contested camp, which acts late;
- enemy in reach, which takes the round-boundary seat;
- quiet.

What each mode does:

- **Quiet** order is a camp-aggro tank order. Healthy, gemless champions act first, so they take
  the camps' tie hits; within a health band, the highest base health goes first.
- **Late** is used at camps an enemy contests. It hands the camps' tie hits to the enemy.
- **Contact** gives the most threatened champion back-to-back turns across the round boundary:
  last when the enemy starts the round, first when Fish starts.

At camps, Fish:

- does not kite or step out to let camps sleep: after a camp hit it stays in range 96% of the time,
  and the order only shares tie hits;
- wakes groups alone, Golems and Monoliths included (no crew wait);
- has Willow stay with whichever ally she is already beside.

No bot source changed.

## Data, split, definitions

- **Cohorts**: all six pinned cohorts, 456 games, engine `v3_0_0`. Discovery is `model`, `confirm`,
  `third` and `fourth` (309 games). Held out are `fifth` and `sixth` (147 games; 31 match groups,
  disjoint from discovery).
  - The selector's only fitted constant is the contest margin `k`, chosen on discovery. The level
    structure was found on `model` only.
  - The held-out games had been decoded before for other studies.
  - During exploration I printed held-out scores once: a gradient-boosting screen for late and
    early, AUC 0.986 for both. No rule or constant was chosen on held-out data. The contest and
    reach features were designed on `model`, `confirm`, `third` and `fourth`.
- **Turns are correlated**: counts are agreement over turns, not independent trials.
- **Observer data** (`replays/fish-team/`, `team_decode.mjs`): per round,
  - the camp-phase snapshot: every champion's position, health, shield, gems, current and next
    priority, channel and stun; the awake monsters;
  - every camp attack with its resolved target and health before and after;
  - the real turn order;
  - every champion turn's actions, with targets and health before and after.

  These data are used for labels and diagnostics only.
- **Fish's own view** (the earlier actor caches) supplies every rule input. It is the state just
  before the turn's priority write, or the turn end when there is none.
  - A visible enemy or ally is one in that champion's personal or ward vision.
- **Unit**: every completed Fish turn after the champion's first priority write (`team_rows.py`;
  1,142 earlier rows on the start priority 0 are excluded). The label is the priority in effect
  next round.
  - Fish writes **only on change**: 0 of 76,654 `model` writes repeat the current value. The
    priority in effect is therefore always the last value Fish chose.
- The **camp target rule** holds on the observer data:
  - "nearest living champion within range, ties to the earlier actor this round":
    **386,596/386,649** discovery and **165,139/165,181** held-out camp attacks;
  - ties alone: 88,055/88,075 and 41,632/41,647;
  - 316 and 389 attacks whose target died earlier in the same phase are left out.

## 1. Priority: one encoding, four modes

### 1a. The level encoding (exact)

```text
N    = Fish bodies, dead included (Cassi and Issac separate)
rank = 2 + position when the team is sorted by base max health, descending
       (ties by type index; exception: Heart of Ruin before Varg)
priority = -rank - (N+1) * L          (L an integer "level"; higher priority acts first)
```

- `rank` is `(-priority) mod (N+1)`, read as `N+1` when the remainder is 0. So the test is not
  that L comes out an integer, which it always does. The test is that this remainder is the same
  for each champion in every mode and never equals 1.
  - It holds for **2,507/2,507** champion-games over all six cohorts, residue 1 never.
  - The base-health order predicts the rank in **2,499/2,507**. The 8 misses are Heart of Ruin
    and Varg, both on 1,000 base health, in 4 games (`16855528a5758df6`, `bf8f956a51c181d9`,
    `9476046b55d2763f`, `8d56024bb6b53842`): Heart of Ruin comes first although
    its type index is higher.
  - [priority-ranks.json](priority-ranks.json)'s tables are this order (Marcella 1200 > Vesper or
    Heart of Ruin 1000 > Vendetta or Issac 900 > Prism or Willow 700 > Cassi 600).
- The levels fall into five modes ([team-priority.json](team-priority.json); turn counts):

| Mode | L | Discovery turns | Held-out turns |
| --- | --- | ---: | ---: |
| dead | −1 | 143,660 (all dead turns) | 46,609 (all) |
| quiet | band (0..3) | 1,259,213 | 571,438 |
| late | band + 5 | 46,599 | 13,216 |
| contact | 99 + j when the enemy starts next round, −101 − j when Fish does | 104,988 | 34,689 |
| early (alive) | −5..−1 | 9,956 | 3,201 |
| other | — | 698 | 251 |

`band = max(0, floor(4 * (1 - min(1, (hp+shield)/maxhp) * (0.65 if gems))))`, as in
[README.md](README.md).

What the modes mean for turn order (higher acts first):

- **When Fish starts the round**: contact (higher j first), then early, then quiet (band 0
  first), then late.
- **When the enemy starts**: early, then quiet, then late, then contact (higher j **last**).
- Dead champions always write L = −1. Their turn is empty, but the value persists into their
  respawn turn.
- The "penalty 5" of README.md is the late mode. The "large ±500..800" values of COMBAT.md are
  the contact mode: (N+1)·(100+j) ± (N+1) − rank. With N = 5 that is 600 ± 6j + 6 − rank.

### 1b. Contact sign: who starts next round (exact)

`contact+` (act first) iff Fish starts the round in which the write applies; otherwise
`contact-` (act last):

- **104,925/104,988** discovery and **34,659/34,689 (99.91%)** held-out contact turns.
- The 30 held-out misses include `f6b2a92e79976f11` r283 actor 5 (−695) and `b2a8402f3bcb821f`
  r474 actor 10 (702).

**What it buys: back-to-back turns.** Take a round where the enemy starts and the next, where Fish
starts. If a Fish champion is `contact-` in the first and `contact+` in the second, the last actor
of the first round is the first actor of the second: **6,320/10,017** discovery and
**2,928/4,551 (64.3%)** held-out round pairs. Without such a champion the rate is
2,487/69,150 and **1,128/31,692 (3.6%)**.

- Only the camp phase separates the two turns; no enemy acts between them.
- Misses are mostly several contact champions whose j order differs between the two rounds, e.g.
  `a01c1f9f1c54417d` r160 (five contact champions).
- Since j grows with threat, the seat goes to the most threatened champion.

### 1c. Contact level j: threat in sixteenths of effective health (approximate)

```text
j ≈ min(16, floor(16 * T / (hp + shield)))
T = sum over visible enemies of D(e, distance), the one-turn damage reach of combat_common.py
```

- Exact in **66,436/104,988** discovery and **20,295/34,689 (58.5%)** held-out contact turns;
  within 1 in 79,974 and **25,282 (72.9%)**.
- The baseline "j = 0" gets 54,279 and 15,770 (45.5%).
- The cap at 16 is real: 4,375 discovery turns sit exactly at j = 16.
- Fish's threat model differs from D: terrain, items and perhaps camps. So this is a fitted
  description, not the source formula. With gems, dividing by 0.65 as in the band scores worse
  (60.0% exact in discovery).

### 1d. When each mode is chosen: the selector

```text
if dead:                       L = -1
elif contested camp (k = 1):   L = band + 5                 (late)
elif enemy in reach:           L = 99 + j or -101 - j       (contact, sign by 1b)
else:                          L = band                     (quiet)

enemy in reach:  some visible enemy e is within reach(e) of self or of a visible ally,
                 or within reach(self) of self; reach = 3 for ranged, 2 for melee
                 (a melee walk plus attack; a ranged walk spends the attack).
contested camp:  some visible awake monster with a range (not a cluster) has self within its
                 range, and a visible enemy is within range + 1 of an awake member of that
                 monster's group.
```

`k` is the only fitted constant (discovery mode accuracy: k = 0 91.7%, **k = 1 93.4%**,
k = 2 91.8%). The early mode is never predicted. Results ([team-modes.json](team-modes.json)):

| | Discovery | Held out |
| --- | ---: | ---: |
| Alive with an enemy visible: mode correct | 404,254/432,977 (93.4%) | **131,740/140,817 (93.6%)** |
| — baseline: always quiet | 273,776 (63.2%) | 90,959 (64.6%) |
| — same selector without the late rule | 372,463 (86.0%) | 122,880 (87.3%) |
| — exact priority value | 367,615 (84.9%) | **117,767 (83.6%)** |
| All turns: mode correct | 1,533,351/1,565,114 (98.0%) | **658,828/669,404 (98.4%)** |
| — baseline: always quiet (dead → L = −1) | 1,402,873 (89.6%) | 618,047 (92.3%) |
| — exact priority value | 1,495,240 (95.5%) | **642,197 (95.9%)** |

- Per held-out cohort (enemy visible): fifth **88,668/95,038 (93.3%)**, sixth
  **43,072/45,779 (94.1%)**.
- Exact-value misses are mostly j (1c). Where the mode is right, quiet and late values are exact
  in 566,609/569,678 and 9,561/9,595 held-out turns; the rest are rank swaps and band reads.

Held-out errors, enemy visible:

- The early mode, never predicted: 2,788 + 74 + 33.
- Quiet predicted, late actual: 2,246. Contact predicted, late actual: 1,112.
- Contact predicted, quiet actual: 1,170.
- Examples: `cfc1265d7551c7d5` r165 actor 9 (early, nearest enemy 4); r219 actor 10 (late, no
  contested camp in view); r225 actor 9 (quiet with an enemy in reach);
  `825fcee16f386346` r224 actor 0 (contact at a contested camp).
- Reach-rule misses with no enemy visible at the decision (1,411 and 819 turns) suggest Fish
  sometimes decides from an earlier sighting in the turn.

**Late is contagious, not only triggered.** With an enemy visible, a champion is late in 32,161
of 54,424 discovery turns when it sees a late ally, against 13,753 of 378,553 when it sees none.
The pattern repeats held out: 7,990/14,091 against 4,963/126,726. Late episodes are team-wide
(e.g. `ee053a1ab7e44f67` r43-67, all five champions). Fish may share the flag through the 8-byte
shared memory, which replays do not record, or read allies' visible priorities. The contest rule
captures most of it from each champion's own view.

**Early (L −5..−1 alive) is unresolved.** It concentrates one step outside reach: 5,912 of
35,118 discovery turns with the nearest visible enemy at 4. In a `model`+`confirm` exploration it was more
frequent when that enemy had a spell or dash threat (28.7% against 11.2%), and its level −2..−5 does not follow the
band. No rule tried separates it.

## 2. What the order does at camps

From [team-aggro.json](team-aggro.json): every camp attack on the observer data, with the
camp-phase positions.

**Ties between Fish champions** are attacks whose nearest set holds two or more Fish champions
and no enemy. Fish's real order is compared with two counterfactuals for the same tied set: id
order (every priority 0) and the reverse of Fish's order.

| Held out (25,907 tie hits) | Fish's order | id order | reverse |
| --- | ---: | ---: | ---: |
| Hit goes to the highest health fraction | **18,909 (73.0%)** | 16,877 (65.1%) | 12,104 (46.7%) |
| Mixed carriers (8,006): a gemless champion takes it | **5,633 (70.4%)** | 2,398 (30.0%) | 2,699 (33.7%) |
| Hit goes to the most hits in hand (ehp / camp strength) | 18,505 (71.4%) | 18,631 (71.9%) | 7,631 (29.5%) |

Discovery (48,966 tie hits): 33,434 / 29,173 / 19,041 for health fraction. For the 16,686
mixed-carrier ties, 11,916 / 4,861 / 5,356.

- Quiet order protects carriers and the relatively hurt. A camp kill destroys the carried bag
  (rules `combat.camp_kill`).
- It is no better than id order at giving the hit to the most absolute effective health: the
  band is a fraction, and the base-health rank only breaks ties within a band.
- Lethal tie hits are rare: 39 and 45 ties had one champion the hit would kill. Fish's order
  spared that champion in all 39 and all 45; id order would have in 26 and 35.
- Counterexample (carrier tanks): `cfc1265d7551c7d5` r362-364, Marcella (actor 7) carrying, tied
  with Issac (actor 9) for camp 48. Her band still outranks his.

**Ties with an enemy.** These are attacks whose nearest set holds a Fish champion and an enemy.
The share in which Fish is hit, by the first tied Fish champion's mode and who starts the round
(discovery, then held out):

| Mode | Fish starts | Enemy starts |
| --- | ---: | ---: |
| quiet | 255/417 (61%); 167/296 | 204/454 (45%); 130/304 |
| late | 529/2,189 (24%); 206/707 (29%) | 302/2,298 (13%); 113/766 (15%) |
| contact | 100/107; 42/45 | 3/79; 0/45 |

- Late cuts Fish's share of contested-camp hits by about half to two thirds. This is the
  late mode's evident purpose.
- Contact acting first takes the camp hit nearly always, the price of the first-mover seat.

**Who stands nearest.** In held-out camp hits with two or more Fish champions in range (57,840),
the victim is the Fish champion with the most effective health in **31,405 (54.3%)**. Choosing
uniformly among those in range would give 24,359 (42.1%). Discovery: 60,122/111,339 against
44,844.

| Type | Hits taken, held out | In range of the hitting monster, same hits | Hits / in range |
| --- | ---: | ---: | ---: |
| Heart of Ruin | 16,552 | 36,196 | 46% |
| Issac | 15,625 | 38,473 | 41% |
| Vendetta | 8,978 | 21,404 | 42% |
| Marcella | 4,028 | 8,283 | 49% |
| Vesper Vale | 6,991 | 20,168 | 35% |
| Cassi | 3,829 | 28,182 | 14% |
| Willow | 1,514 | 17,101 | 9% |

The melee bodies stand at 1 and take the hits. Cassi and Willow stand in range at 3 or 4 and are
rarely hit: they are farther away and later in the order.

## 3. Camp-fight micro

From [team-campfight.json](team-campfight.json), observer labels.

### 3a. No kiting, no stepping out: Fish stays in range

The opportunity is a Fish champion hit by a camp in round r whose group is still awake at round
r+1's camp phase, and which is alive then. "Stays" means it is within range of an awake member of
that group at r+1's camp phase.

- Excluded: 6,127 and 2,748 cases where the group was cleared; 27 and 8 where the champion died.
- "Hits in hand" = (hp + shield at its turn start) / camp damage it took in phase r.

| Hits in hand | Gemless, held out | Carrier, held out | Discovery (both) |
| --- | ---: | ---: | ---: |
| < 1 | 1,409/1,446 (97%) | 31/50 | 784/872 |
| 1-2 | 895/982 (91%) | 73/101 | 1,074/1,347 |
| 2-4 | 3,043/3,299 (92%) | 408/508 (80%) | 4,106/4,904 |
| 4-8 | 6,780/7,082 | 1,578/1,725 | 14,565/15,701 |
| ≥ 8 | 34,481/35,453 | 19,334/20,068 | 125,045/129,704 |
| **All: stays** | | **68,032/70,714 (96.2%)** | 145,574/152,528 (95.4%) |

- **Rule: always stay.** No hits-in-hand threshold beats it in either split. Staying is least
  common at 1-4 hits in hand, which no threshold can exploit.
- Carriers leave somewhat more (72-80% stay at 1-4 hits in hand), consistent with the gem-bag
  penalty in the band.
- Low-health stayers (under 2 hits in hand) are hit again next phase in **2,102/2,408**
  held-out cases (1,393/1,858 discovery). The quiet band drops them in the order, but at camps
  they are usually the only one nearest, so the order rarely saves them.
- Yet camp kills are rare: 8 held-out champions dead by the next camp phase. Clearing members
  and Willow's heals are plausible reasons, not verified here.
- So Fish does not kite camps with ranged champions or step out to let a group fall asleep.
  Leaving shows up as recall or departure, which DECISIONS.md and ROUTES.md cover.
- Leaving while healthy happens, e.g. `cfc1265d7551c7d5` r7 actor 8 (47 hits in hand) and r102
  actor 10 (11 hits in hand).

### 3b. Waking: alone, whatever the group

A wake is the first Fish damage to a group none of whose members was awake at that round's camp
phase and none woken earlier that round. "Alone" means no other Fish champion is within 4 of any
member at that moment (observer positions).

| Group | Held out: woken alone | Discovery |
| --- | ---: | ---: |
| Monolith | **146/232 (63%)** | 253/385 (66%) |
| Golem | **203/382 (53%)** | 446/801 (56%) |
| Elk | 1,061/2,069 (51%) | 2,699/5,186 (52%) |
| Wolf | 1,422/2,576 (55%) | 3,467/6,093 (57%) |
| Clusters | 1,825/3,130 | 3,471/5,730 |

- A crew requirement before waking strong groups is refuted: big groups are woken alone at least
  as often as wolves.
- The waker is often a ranged squishy. Held-out wakers include Cassi 1,837, Issac 1,481,
  Vendetta 1,201, Heart of Ruin 1,049, Vesper 1,058, Marcella 821 and Willow 789.
- Solo Golem/Monolith wakes: `fe5675fd7c40fa51` r411 actor 0 and r438 actor 1 (Monolith),
  `be6f364d32fd7f32` r62 actor 1 (Golem).
- This measures who is near at the first hit, not later arrivals. Allies often join, and the
  quiet order then hands them the tie hits (section 2).

### 3c. Splitting damage and last hits

- Not re-derived here. CONTINUATION.md's camp-target rule already covers both: keep the previous
  group, then minimum (health, y, x, id), 94% of multi-target choices. Allies applying the same
  rule therefore focus the same monster.
- No separate split or last-hit rule was looked for. Capture holders and handoffs are in
  CONTINUATION.md and ROUTES.md.

### 3d. Willow: stays beside the ally she is already beside

The opportunity is a Willow turn on which she walks, with two or more visible allies off spawn
(Willow's own view). The label is the ally she ends strictly nearest; 5,772 held-out ties are
excluded.

| Predictor | Held out (16,538) | Discovery (48,744) |
| --- | ---: | ---: |
| **Ally nearest at her turn start** | **13,845 (83.7%)** | 40,712 (83.5%) |
| Ally missing the most health | 4,419 (26.7%) | 12,220 |
| Lowest health fraction | 4,490 | 12,541 |
| Lowest id | 4,864 (29.4%) | 13,786 |

- She has no fixed escort target. Cassi is the ally she ends nearest most often (6,398/16,538
  held out), then Issac and Heart of Ruin.
- Her heal target given a cast is README.md's model: the most restored fraction, 89.7% on
  multi-target holdout. Whether she casts is in DECISIONS.md (94%).
- She stands in camp range often but is rarely hit (9% of her in-range turns, section 2).

## Compared with astraeus

- **Idle order**: [idle_priority.h](../../bots/astraeus/src/model/idle_priority.h).
  - Same purpose as Fish's quiet mode: the camp tie hit goes to whoever it leaves alive with the
    most hits in hand, gemless before carriers.
  - Astraeus counts absolute hits in hand, `floor((ehp - hit) / hit)`. Fish uses a quarter-band of
    health fraction (×0.65 when carrying), then base max health.
  - So astraeus gives the hit to the champion with the most hits in hand more often than Fish's
    order does (Fish: 71.4%, the same as id order), while Fish protects hurt low-health champions
    by fraction.
  - With no camp hit pending, astraeus orders by enemy distance ("the ostrich": nearer enemies act
    later). Fish has no such term: near enemies take it to contact, early or late.
- **Fight order**: [turn_order.cc](../../bots/astraeus/src/model/turn_order.cc).
  - Astraeus bids for kill, protect and danger bands and checks the enemy's next-round slots
    (`next_slot`, `we_start`).
  - Fish has no bidding. It has one threat-scaled band whose sign flips with who starts the next
    round, so the most threatened champion takes the round-boundary pair of turns. Astraeus has no
    such sign rule.
- **Contested camps**: astraeus has nothing like Fish's late mode, which hands contested camp tie
  hits to the enemy.
- **Crews and kiting**: `economy/crew.cc` (tank score, water-filling damage shares) and
  `farm.cc`.
  - Astraeus gathers a Monolith crew before waking (`mono_gather_share`, `mono_max_wait`) and
    kites big groups (`kited`).
  - Fish does neither (section 3): it wakes alone and stays in range; its order only shares tie
    hits.
- **Willow**: [support.cc](../../bots/astraeus/src/combat/support.cc) pairs Willow with a
  protected mate (Prism or Tavi) and treats tiles a camp can hit as unsafe. Fish's Willow stays
  with whoever she is beside (most often Cassi) and stands in camp range (17,101 held-out
  in-range turns), but is rarely the victim (9%).

None of this says Fish's choices are better; they are descriptions to test by A/B.

## Reproduce

```sh
M=research/fish-2026-11-05
node tools/fish/team_decode.mjs replays/fish-team --jobs 6 $M/manifest.json $M/confirmation-manifest.json \
  $M/third-manifest.json $M/fourth-manifest.json $M/fifth-manifest.json $M/sixth-manifest.json
for c in model confirm third fourth fifth sixth; do
  python3 tools/fish/team_rows.py replays/fish-team-rows/$c-rows-v2.jsonl.gz --cohorts $c
done
python3 tools/fish/team_priority.py $M/team-priority.json   # 1a-1c; reads rows v1 (the same rows without camp columns)
python3 tools/fish/team_modes.py $M/team-modes.json         # 1d
python3 tools/fish/team_aggro.py $M/team-aggro.json         # 2
python3 tools/fish/team_campfight.py $M/team-campfight.json # 3
```

- `team_priority.py` reads `*-rows-v1.jsonl.gz`, built by the same script before the camp columns
  were added; rows v2 has the same rows and columns plus the camp columns.
- Every script refuses to overwrite its output.
- Counterexamples (game SHA16, round, actor) are in each JSON's `examples` and `errors`.
- New scripts: `tools/fish/team_{decode.mjs,common.py,rows.py,priority.py,modes.py,aggro.py,campfight.py}`.

## Audit: forced vs free decisions (2026-11-06)

This checks whether each rule above is a choice or a restatement of cambc-rules.yaml. It uses
`tools/fish/engage_audit.py` → [rule-audit-engage.json](rule-audit-engage.json) (`audit.stepout`,
`audit.willow`). The earlier text is unchanged. Labels are the same observer labels as section 3, and
the old numbers reproduce exactly. Legality comes from the actor's own turn-start view:
- a step onto an in-bounds tile that is not a wall, hole, altar or the enemy spawn, and not held by a
  visible champion or a visible live camp;
- a ready dash, and a walk plus a dash in either order;
- none when stunned or teleporting.

**Priority (section 1).** Priority is a free action, any int32, applied from the next round
(`turn.free`, `team_order`). Nothing restricts its value, so the level encoding and the modes are
output encodings, not choices among constrained alternatives. Confirmed: no legality audit applies.

**3a. "Stays in camp range" is mostly forced.** The opportunity is the actor's own turn in round r,
after the camp hit. It could leave if some tile reachable that turn (or its start tile) is out of
range of every awake member of the hitting groups at r+1:

| Held out (70,714; old stays 96.2%) | n | share | stays |
| --- | ---: | ---: | ---: |
| cannot leave this turn (every reachable tile still in range) | 47,102 | 66.6% | 100% |
| stunned | 125 | 0.2% | 100% |
| ranged, attacked without walking (gave the step up for the hit) | 6,625 | 9.4% | 99.9% |
| cannot stay (no reachable tile in range) | 617 | 0.9% | 0% |
| **free** | **16,245** | **23.0%** | **87.3%** |
| — melee / ranged | 14,475 / 1,770 | | 92.2% / **47.9%** |
| — on the range edge (one step out leaves) | 3,271 | | **55.3%** |
| — one inside the edge / two inside (a walk plus a dash needed) | 2,374 / 10,505 | | 91.0% / 97.2% |

Seventh: free 27,546/31,435 (87.6%), edge 54.9%. Discovery: free 86.2%, edge 55.1%.

- 76.2% of the old headline was forced: 53,852 rows that could not leave, were stunned, or attacked
  in place as ranged.
- Restated as a turn-level choice from the turn start, counting the ranged attackers as free:
  20,806/22,870 stay (91.0%).
- Where one step is enough to leave, Fish leaves about half the time. Ranged champions that do not
  attack leave in 52%.
- So "no stepping out" holds only in the sense that Fish does not walk two or more tiles to get out.
  At the edge it often steps out.
- The hits-in-hand table above is dominated by forced rows and should not be read as a choice curve.
- **Verdict: partly rule.**

**3b. Waking alone.** Waking can always be delayed, and so can waiting for an ally. Nothing forces
either, so it is a real choice. Not re-scored.

**3d. Willow "stays beside the ally she is already beside" is geometry.** For each of her legal steps
(she has no dash), the audit computes which ally would be strictly nearest given the allies' end
positions:

| Held out (16,538) | n | start-nearest = end-nearest | random legal step (placebo) |
| --- | ---: | ---: | ---: |
| Old | 16,538 | 83.7% | **86.8%** |
| Forced: every legal step gives the same end-nearest ally | 12,019 (72.7%) | 96.6% | 96.6% |
| **Free**: her step decides it | **4,519** | **49.6%** | **60.8%** |

Seventh: free 51.1% vs placebo 60.5%; discovery 49.5% vs 60.4%.

- The old 83.7% is below a random legal step's 86.8%.
- Where her step decides, she ends nearest the ally she started beside less often than chance: she
  moves toward another ally.
- **Verdict: pure rule** (one-step geometry). The predictor carries no information about her choice.

| Rule | Old (held) | Forced share | Free rows (held) vs baseline | Verdict |
| --- | ---: | ---: | ---: | --- |
| Priority encoding, modes | exact / see 1d | n/a | n/a | output encoding |
| 3a stays in camp range | 96.2% | 76.2% | 87.3% stays; 55% at the edge | partly rule |
| 3b wakes alone | 51-63% | 0 | same | real choice (descriptive) |
| 3d Willow: start-nearest ally | 83.7% (placebo 86.8%) | 72.7% | 49.6% vs placebo 60.8% | pure rule |
