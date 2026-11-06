# Fish farming, and the structure of its camp targeting (farm3)

November 5-6, 2026. Research only: no bot, earlier script, cache, manifest or result changed. New
scripts are `tools/fish/farm3_*`, new caches `replays/fish-farm3/`, new results `farm3-*.json` here.

**Result.** Fish's camp destinations are chosen from **team-shared camp memory**, not each
champion's own sightings. Rebuild every candidate group's state from the newest sighting by *any*
Fish champion whose turn came before the decision. Then farm2's own features and logit, refitted,
get **65.82%** of held-out destinations against **63.63%** for the same model on own memory (+1.5
to +2.9 points by match-group bootstrap). The gain is +2.8 points after spawn, the weak half.

- Observer truth for camp states gives the same gain (65.69%). Truth applied only where no
  teammate had a newer sighting gives none (63.34%).
- So what Fish knows about camps is what its team has seen. The channel is presumably its 8 bytes
  of shared team memory, which replays do not record.
- None of this is rule-forced. Only 1-3% of destination rows have one feasible candidate. On free
  rows farm3 gets 67.83% / 62.57% (fifth / sixth) and 63.53% on the seventh cohort, against wait
  baselines of 52.25% / 44.66% / 48.73% (section 6).
- Every other structural idea tested fails (section 4): closed-form rate scores, per-map circuits,
  team assignment or claims, deciding at payout, and score-lead or enemy-liveness terms. Openings
  are deterministic per map but stay unexplained (57% at best).

**Untouched seventh cohort** ([seventh-manifest.json](seventh-manifest.json): 265 games, 56 match
groups, 21:40-23:40 UTC November 5). [farm3-seventh-freeze.json](farm3-seventh-freeze.json) hashed
the fits and every script, 2026-11-06 00:13 UTC, before any seventh play was read. Its features were
built with the unchanged pipeline into `replays/fish-farm3/seventh/`; all hashes matched at scoring.
Scored once ([farm3-seventh.json](farm3-seventh.json), fit on FIT only):

| Model | All (12,179) | Payout (4,974) | Spawn (7,205) |
| --- | ---: | ---: | ---: |
| **farm3: team-union memory** | **7,686 (63.11%)** | **3,538 (71.13%)** | **4,148 (57.57%)** |
| farm2 features, own memory, same fit | 7,391 (60.69%) | 3,431 (68.98%) | 3,960 (54.96%) |
| frozen `farm2-fit.json` (five cohorts) | 7,406 (60.81%) | 3,460 (69.56%) | 3,946 (54.77%) |
| frozen `farm2-fit-A.json` | 7,375 (60.56%) | 3,436 (69.08%) | 3,939 (54.67%) |
| wait baseline | 5,934 (48.72%) | 2,939 (59.09%) | 2,995 (41.57%) |

- farm3 minus farm2, match-group bootstrap: **+2.0 to +2.9 points** (spawn +2.1 to +3.1).
- farm3 matches or beats farm2 in **54 of 56 groups**, and strictly beats it in 50.
- Ranked games: 1,477/2,276 against 1,417; unranked: 6,209/9,903 against 5,974.
- Refitted on all six cohorts ([farm3-seventh-all.json](farm3-seventh-all.json)): 63.33% against
  60.62% (+2.2 to +3.2).

## Data and split

- **Cohorts**: the six decoded cohorts (456 games, engine `v3_0_0`).
  - **FIT** = model + confirm + third + fourth (309 games): all fitting and constant choices.
  - **HELD** = fifth + sixth (147 games, 31 match groups): reported unchanged.
  - The held-out games were inspected by earlier studies, and I looked at random held-out misses
    while choosing hypotheses. The seventh cohort is the only untouched test.
- **Episodes and labels** are farm2's (FARM-CHOICE.md):
  - post-payout and spawn-exit starts with no visible enemy;
  - the label is the first camp hit, or occupation of another empty group, within 40 rounds;
  - the denominator is every non-opening episode labelled `hit`, 5,928 held out. Unscoreable
    labels count as errors.
- **The reference** is farm2's feature sets and options (`base+hp+rate+home+stale+crew+size`,
  gems at 3 gold, crew Strength), **refitted on FIT**. It scores 63.63% on HELD (fifth 65.88%,
  sixth 59.55%), matching `farm2-fit-A.json`'s fifth and sixth figures within 0.2 points. Every
  alternative is compared with it on the same rows.
- **Observer data** (`farm3_decode.mjs`; one camp-phase snapshot per round, with positions, gold,
  gems, channels, group states, camp health and scores; plus `replays/fish-team`'s actions) are
  used only for section 1's descriptions, for labels and as named diagnostics. They are never
  model inputs.

## 1. Farming in general (descriptive, observer data, all 456 games)

### 1a. Where the turns go

Each Fish champion turn gets one activity, the first that applies (`farm3_describe.py`):

- **dead**;
- **home**: starts on its own spawn;
- **tribute**: a tribute channel or attempt;
- **fight**: an action on an enemy champion;
- **clear**: an action hitting a camp;
- **capture**: starts on an empty group's tile;
- **recall**: keeps a recall channel;
- **wait**: a respawning group's tile within 2;
- **approach**: walks with a living camp within 3;
- **travel**: any other walk;
- **idle**: anything else.

| Champion (turns) | dead | home | trib | fight | clear | capt | recall | wait | appr | travel | idle |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **all (2,236,792)** | 8.5 | 3.1 | 2.8 | 3.0 | **20.9** | 4.7 | 6.7 | 7.9 | 7.0 | **34.6** | 0.8 |
| Cassi (408,045) | 11.6 | 3.2 | 1.1 | 2.6 | 22.5 | 3.3 | 5.2 | 7.8 | 6.0 | 36.7 | 0.3 |
| Issac (408,045) | 11.6 | 3.3 | 1.0 | 2.3 | 22.1 | 4.0 | 6.7 | 7.0 | 8.1 | 33.1 | 0.8 |
| Heart of Ruin (382,209) | 7.2 | 3.3 | 2.4 | 3.6 | 22.4 | 5.5 | 6.6 | 7.4 | 7.4 | 33.5 | 0.9 |
| Vendetta (329,819) | 6.3 | 2.2 | 4.3 | 3.0 | 20.6 | 6.5 | 7.5 | 7.7 | 7.5 | 33.4 | 1.1 |
| Marcella (249,979) | 7.3 | 2.8 | 5.7 | 5.4 | 12.0 | 5.4 | 7.8 | 9.9 | 7.4 | 35.9 | 0.4 |
| Willow (229,909) | 7.2 | 1.9 | 0.5 | 1.6 | 24.5 | 1.8 | 7.2 | 7.7 | 7.0 | 39.9 | 0.9 |
| Vesper (192,649) | 5.2 | 5.7 | 7.0 | 3.4 | 22.2 | 6.5 | 6.9 | 8.6 | 5.5 | 27.8 | 1.3 |

(% of turns. Prism, Ren and Varg have 13,258, 20,163 and 2,716 turns.)

Forced by the rules: all dead turns (8.5%), 13,969 stunned turns (0.6%; counted under whatever
class their position gives) and 3,050 respawn turns (0.1%, no walk, attack or cast). That is 9.3%
of turns. On the other 90.7% the shares are free choices. Recall and tribute channels can always
be cancelled, so those rows are free.

- **About 35% of turns are walking between camps.** A fifth are spent hitting camps, and 8%
  waiting beside a respawning group. Idle turns are under 1%.
- **Holders and clearers.** Capture shares go to whoever stands on the tiles at payout, and 92%
  of Fish payouts have one recipient (20,319 of 22,042).
  - Vesper (22 payouts per 1,000 rounds, median per champion-game), Vendetta (17.6), Marcella
    (16.7) and Heart of Ruin (10.4) collect them.
  - Cassi (5.8), Issac (4.8) and Willow (3.1) mostly clear and leave. This is CONTINUATION.md's
    holder ranking `Marcella > Vesper > Vendetta > HoR > Cassi > Issac > Willow` in action.
- **By game phase.** Clearing falls from 30% of turns (rounds 1-100) to 9% after round 1000.
  Death rises from 3% to 17%, travel from 34% to 42%, and tribute peaks at 3.8% in rounds 601-1000.
- **By score lead** (tributed gems, Fish minus enemy):
  - far behind (< -100): 17% dead and 16% clearing;
  - level: 6% dead, 26% clearing, 6% home (the opening);
  - far ahead (> +100): 7% dead, 19% clearing, 3.9% tribute.
  Farming does not visibly change mode with the lead: the differences follow deaths and game phase.
- **By team gold** (summed carried gold): with under 30 gold, 7% of turns are at home and 4% are
  waiting. With 200+ gold, 2% are at home and 10% waiting. Fish spends gold as it arrives
  (ECONOMY.md's gate is gold >= 30).

### 1b. Sequences and spread

| Champion | Payouts | Repeat same group | A-B-A | Distinct groups a game | Top-2 groups' share | Own side | Enemy side |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Vendetta | 5,654 | 5.9% | 13.2% | 7.0 | 47% | 78% | 6.4% |
| Heart of Ruin | 4,147 | 9.1% | 13.5% | 5.5 | 52% | 72% | 8.2% |
| Marcella | 4,074 | 9.9% | 19.2% | 5.9 | 56% | 79% | 7.7% |
| Vesper | 3,997 | 4.0% | 12.4% | 7.9 | 45% | 78% | 5.1% |
| Cassi | 2,759 | 10.7% | 12.0% | 4.0 | 57% | 77% | 8.0% |
| Issac | 2,302 | 14.5% | 11.2% | 3.6 | 60% | 66% | 9.7% |
| Willow | 767 | 13.1% | 10.8% | 2.7 | 65% | 71% | 7.0% |

Sides are by static walk from the two spawns; the rest are "middle", equally far from both.

- **Local circuits, not scripts.** A champion's captures cycle among a few nearby groups: the top
  two groups hold about half its payouts, with frequent A-B-A returns.
  - Example: `0b1a9e673ab41855` (04mesas), Marcella: 12, 14, 12, 14, 12, 14, 13, 12, ...
- **But games do not repeat.** Two games with the same map, side and champion share their first
  payout group in 59% of pairs and their first three in 22% (2,235 pairs). A per-map lookup
  table predicts destinations worse than the logit (section 4).
- **No zones.** Two champions of a game overlap in 67% of their payout groups (mean over 2,557
  pairs). Marcella and Vendetta overlap 79%, Cassi and Issac 64%.
- **Spread.** Off spawn, 69% of champion turns are on Fish's side, 22% in the middle and 9% on
  the enemy side (1,976,464 turns). The nearest ally is a median 2 tiles away (quartiles 1 and 6),
  and within 4 tiles in 67% of turns.

### 1c. Big camps, enemy-side camps and steals

- **Solo clears.** Solo means one Fish champion and no other champion damaged the group or was
  hit by it, from its respawn to its clear. Fish clears 5,598 Elk groups.
  - 457 are solo: Vesper 204, Vendetta 177, Marcella 53, Heart of Ruin 17, the others 6.
  - The soloist's Strength: Vesper quartiles 212/328/455 (minimum 85); Vendetta 125/185/284 (65);
    Marcella 54/72/92 (40). Median round 574 (quartiles about 400-750).
- **Golems and Monoliths are team clears.**
  - Golems: 345 Fish clears, 5 solo (Vendetta 4 at Strength 275-425, rounds 903-1712; Vesper once
    at 415, r606).
  - Monoliths: 116 Fish clears, 7 solo (Vesper 5 at Strength 200-545, Marcella once at 124,
    Vendetta once at 353).
  - TEAM.md's "woken alone" is about the first hit. Allies arrive before the clear.
- **Captures by side** (22,042 Fish payouts): own 17,048 (77%), middle 3,504 (16%), enemy 1,490
  (7%). Enemy-side captures are mostly gold or gem clusters and wolves (1,080 of 1,490). There are
  289 Elk, 98 Golem and 23 Monolith groups among them.
- **The enemy takes 2,256 groups on Fish's side** (10% of its payouts).
- **Steals**, by who damaged the group in its last clear before the payout:
  - Fish was paid for 257 groups the enemy alone cleared, and for 2,494 both teams worked on;
  - the enemy was paid for 201 groups Fish alone cleared.

  Stealing is incidental: about 1% of payouts each way.

## 2. Compared with astraeus

- **Shared camp memory.** Astraeus keeps camp beliefs per champion (`model/` world beliefs) and
  shares a claim ledger through comms. Fish's destinations behave as if every champion knows the
  newest group state seen by any teammate, including groups a teammate just cleared or re-cleared.
- **Joining, not partitioning.** Fish never splits value among assignees (section 4: the opening's
  `greedy_split` and the commitments test). Co-deciders go to the same group, and the logit's
  `ally_closer` weight is positive. Astraeus's `crew_rate` adds crew Strength to the clear time,
  which Fish's choices agree with (FARM-CHOICE.md's `crew` option). Astraeus's claims exclude allies
  instead; Fish has no exclusion.
- **No closed-form rate.** astraeus's `rate()` (`worth / (R (1 + R/H))` over walk, clear and
  capture time) chooses Fish's destination in 40.7% of held-out episodes, below the wait baseline
  (49.7%). With constants grid-searched on FIT, the best closed form reaches 50.49% (payout 65.1%, spawn 42.1%), 13 points below farm2.
  Fish's choice depends on worth, wait and memory state with weights that differ after payout and
  after spawn, which no single-rate formula reproduces (FARM-CHOICE.md's table).
- **Kiting, crews and waking**: TEAM.md. Fish wakes alone and stays in range. Astraeus gathers
  Monolith crews.

None of this says Fish's choices are better; port only through an A/B.

## 3. The structure: team-union camp memory (`farm3_memory.py`)

```text
for each candidate group g at a decision (actor a, round t, engine step s):
    own      = a's remembered state of g (farm2_data: a's own contexts up to its turn start)
    sighting = newest group-state sighting of g in the contexts (turn start, before actions, turn
               end) of any other Fish champion's turn with engine step < s
    if sighting exists and sighting.round > own.round (or g is unknown to a):
        state(g)   = sighting.state                   # 1 alive, 2 empty, 3 respawning
        age(g)     = t - sighting.round
        respawn(g) = max(0, sighting.respawn - age)   # if respawning
        if the state changed: live hp = full if alive or unknown else 0; awake = 0
score with farm2's features and logit (separate payout/spawn weights), argmax, ties to lower id
```

The weights are refitted on FIT: `farm3-fit.json` holds `farm3` (team memory) and `farm2` (own
memory). These are surrogate weights, not Fish constants. The memory rule is the structural
claim. A newer ally sighting exists for 97-98% of episodes in every cohort (at least one
candidate).

Held out ([farm3-heldout.json](farm3-heldout.json), errors in its sibling `.errors.jsonl.gz`):

| Cohort | Reason | farm3 (team memory) | farm2 (own memory) | Wait |
| --- | --- | ---: | ---: | ---: |
| fifth | all | **2,592/3,819 (67.87%)** | 2,516 (65.88%) | 2,002 (52.42%) |
| fifth | payout / spawn | **76.95% / 62.24%** | 75.31% / 60.03% | 63.27% / 45.69% |
| sixth | all | **1,310/2,109 (62.11%)** | 1,256 (59.55%) | 942 (44.67%) |
| sixth | payout / spawn | 68.55% / **58.99%** | 68.55% / 55.18% | 55.80% / 39.25% |
| **HELD** | all | **3,902/5,928 (65.82%)** | 3,772 (63.63%) | 2,944 (49.66%) |
| HELD | payout / spawn | **74.26% / 61.02%** | 73.14% / 58.21% | 60.87% / 43.27% |

Match-group bootstrap of farm3 minus farm2 (10,000 resamples): fifth +1.2 to +2.8 (spawn +1.1 to
+3.3, 20 groups); sixth +1.4 to +3.6 (spawn +2.5 to +5.2, 11 groups); HELD +1.5 to +2.9 (spawn
+1.9 to +3.7, 31 groups).

**What makes it structural, not just a better feature.** The memory variants below are all
refitted on FIT with the same features ([farm3-explore.json](farm3-explore.json),
[farm3-explore-kinds.json](farm3-explore-kinds.json)):

| Camp states used | HELD | vs own memory |
| --- | ---: | --- |
| own memory (farm2) | 63.63% | — |
| **team-union memory (farm3)** | **65.82%** | +1.5 to +2.9 |
| observer truth, all groups | 65.69% | +1.4 to +2.8 |
| observer truth, respawning groups only | 65.47% | +1.2 to +2.4 |
| observer truth only where no ally sighting is newer | 63.34% | −0.6 to +0.0 |
| team memory, ally sightings at least 10 rounds old | 65.08% | +0.8 to +2.0 |
| team memory, ally sightings at least 40 rounds old | 63.78% | −0.3 to +0.6 |
| team memory, only sightings by an ally standing on the group | 66.03% | +1.8 to +3.0 |
| team memory, only sightings by an ally off the group | 65.86% | +1.6 to +2.9 |
| team memory, only sightings of a respawning state | 65.52% | +1.3 to +2.5 |
| team memory, only sightings of other states (alive, empty, unknown) | 64.20% | −0.2 to +1.3 |

- Team memory matches truth: the information Fish uses beyond its own sight is what teammates saw.
- Truth elsewhere, on groups no teammate saw more recently, adds nothing. So Fish is not
  inferring hidden states, and our reconstruction of its own memory is not simply too poor.
- **What is shared is mostly respawn timers.** Sharing only respawning-state sightings gets most
  of the gain (65.52%). Sharing only the other states gets little (64.20%).
  - It does not matter whether the ally stood on the group or saw it from afar.
  - Sightings 10 or more rounds old still help (65.08%). At 40 or more rounds old the gain is gone,
    the length of a wolf respawn.
  - Read: Fish knows when any teammate saw a group cleared or respawning, and its timer. It skips
    those groups and times its arrival on them.

What it changes (HELD; a scratch diagnostic, not saved): farm3 fixes 272 farm2 misses and breaks 142.

- The largest fixed class: farm2's pick was a group the actor remembered as respawning, with its
  timer run out, which a teammate had since seen re-cleared (63). Or one remembered alive that a
  teammate had seen cleared or empty (36).
- Fish does not walk to camps its team knows are gone.
- Fixed examples:
  - `72e3972091749179` r385 actor 7 (Prism, payout): farm2 g69 (own: alive, seen 29 rounds ago;
    team: respawning, 45 left), farm3 and label g80;
  - `72e3972091749179` r16 actor 10 (Issac, payout): g97 seen empty by an ally a round earlier;
  - `fe5675fd7c40fa51` r415 actor 1 (Vendetta, spawn): the label g10 was remembered respawning 50
    rounds ago; an ally saw it alive this round.

## 4. Structural hypotheses tested (negative results)

All are on HELD with weights or constants from FIT, against farm2 refitted on FIT (63.63%), unless
stated ([farm3-explore.json](farm3-explore.json)).

| Hypothesis | Test | Result |
| --- | --- | --- |
| **Closed-form score** (astraeus `rate()`) | `worth/(R(1+R/H))`, R = max(walk, respawn) + clear + 7 capture, gems ×3 | **40.72%** (payout 55.9%, spawn 32.1%), against farm2 63.63% and wait 49.66%; gems ×10: 36.76% |
| Closed form, 7 constants grid-searched on FIT | gem price, ln R exponent, horizon on/off, home-share power, empty/unknown/recent-ally penalties (1,728 combinations a reason) | **50.49%** (payout 65.1%, spawn 42.1%), −14.8 to −11.6 points against farm2. Best constants: payout gem 3, exponent 1, horizon on, share power 1, empty penalty 2; spawn gem 1, share power 3, empty 2, unknown 0.5, recent ally 0.5 |
| **Per-map circuits** | lookup of the most frequent FIT label for (map, side, champion, reason, previous group) | (map, side, champion, reason, previous group), covering 2,798 held-out episodes: **1,445 (51.6%)** against farm2 1,839 (65.7%) on the same rows. Coarser keys are worse (47.6%, 33.9%) |
| **Team assignment / claims** | allies' committed destinations (their own later labels: an oracle for any shared claim), as logit terms | **65.05%**, +1.4 points (+0.8 to +2.1), all of it from allies deciding in the same round (weight +0.74 payout, +0.84 spawn). Joining, never exclusion |
| — commitments of allies more than 8 tiles away | | **63.71%**, +0.1 (−0.1 to +0.2): no remote claims, in either direction |
| **Sequential exclusion in turn order** | same-round co-deciders, the later actor (B) vs the earlier (A) | When B's own top choice is A's destination, B goes there: **247/270** payout pairs, **292/327** spawn pairs (89-91%, against the 58-73% base rate). When it is not, B still picks A's group in 119/238 spawn pairs. No exclusion; co-located deciders move together |
| **Decided at payout** for the next trip | spawn destinations after a payout then home, same life: frozen CHOICE logit ranked at the payout vs at the spawn exit | 4,840 trips: payout-time rank picks the destination in **1,163 (24.0%)**, spawn-time rank in 2,771 (57.3%). Return to the paid group: 186 (3.8%). Refuted |
| **Score lead / enemy liveness** | enemy and Fish dead fractions (readable by Fish) × enemy side or walk, score lead × enemy side | **63.48%** (−0.3 to −0.0): no effect |
| **Openings** (round 1, deterministic) | 209 map/side configurations, 946 labelled champion openings | nearest 42.3%; individual astraeus rate 47.6%; greedy in id order, crew Strength joins **56.7%**; greedy splitting value 19.0% (34.0% with crew); one pack to the team-best group 55.7% |

- **Openings are deterministic and still unexplained.**
  - Across games with the same map, side and champion, the first group is the same in **1,918 of 1,969** pairs of games (97.4%); the misses include one game (`dba375dec6f4bd8f`, 04keyhole) differing in every champion, perhaps another submission.
  - Yet no rule tried reaches 57%.
  - In 109 of the 191 configurations with two or more opening hitters, every one goes to the
    same group, a pack.
  - Splitting value among assignees (a partition) is the worst rule. Adding assigned allies'
    Strength to the clear time (joining) is the best. Fish's opening is a joint plan we have not
    decoded.
- **Not tested**: dashes and teleports in travel time (dashes save at most a step every 8
  rounds; teleports are rare, MISC.md), and dynamic blockers in walks.

## 5. Retained counterexamples (farm3 misses, HELD)

- **Team memory misleads.** `bd2f59dff6a7ad93` r48 actor 7 (Heart of Ruin, spawn): an ally saw
  g22 alive, so farm3 picks it; Fish goes to g19, as farm2 predicted. 142 such breaks, 68 of them
  with the label's own state changed: 36 where the actor remembered the label respawning and a
  teammate had seen it alive. Either the sharing is partial (not every sighting reaches the team)
  or the label group's appeal is from something else.
- **Re-clear timer**: `f4d928f76c12f807` r192 actor 3 (Cassi, spawn): team memory says g4
  respawning with 11 rounds left (own: expired 66 rounds ago); farm3 prefers it, and Fish goes to
  g3.
- **Unchanged farm2 misses** (FARM-CHOICE.md) remain:
  - the cleared Monolith beside spawn (`9d651ecb658daedc` r547/r855, actor 4);
  - walking past a nearer group (`825fcee16f386346` r630, actor 3);
  - unvisited remembered timers (`f54302b2e536a4bc` r265, actor 4);
  - incidental ranged hits as labels (`72e3972091749179` r307, actor 7).
- **Near ties dominate.** In HELD misses the label is farm2's second choice in 664 of 1,578
  post-spawn misses and 324 of 547 post-payout misses. Label-versus-pick state swaps (alive vs
  respawning) make up 557 of the post-spawn misses.

## 6. Audit: forced vs free decisions (2026-11-06)

`farm3_audit.py` → [rule-audit-farm.json](rule-audit-farm.json). A row is forced when the rules (or
the label's own horizon) leave one outcome.

- **Destinations**: forced when at most one candidate is feasible. Feasible means reachable, not
  the group just paid out, and `max(walk, remembered respawn) <= 40`, the label window: a group
  still respawning past it can be neither hit nor occupied as empty in time.
- **Camp target**: forced when a single visible living camp is in basic range.
- **Activities**: forced turns are dead turns (shop and priority only), the respawn turn (no walk,
  attack or cast), stunned turns and teleport channels.

| Metric (report) | Headline | Forced share | Free rows: model vs baseline | Verdict |
| --- | --- | ---: | --- | --- |
| farm3 destinations, HELD fifth / sixth (FARM3) | 67.87% / 62.11% | 1.0% / 2.8% | **67.83% vs wait 52.25%** / **62.57% vs 44.66%** | holds |
| farm3 destinations, seventh (FARM3) | 63.11% | 2.6% | **63.53% vs wait 48.73%** (farm2 61.08%) | holds |
| farm2-fit-A, fifth / confirm / sixth (FARM-CHOICE) | 65.88 / 62.05 / 59.36% | 1.0 / 2.4 / 2.8% | 65.82 / 62.41 / 59.83% vs wait 52.25 / 51.04 / 44.66% | holds |
| choice-fit.json, fifth (CHOICE) | 61.56% | 1.0% | 61.43% vs wait 52.25% | holds |
| route/fitted, fourth (ROUTES) | 49.07% | 2.8% | 49.70% vs wait 48.27% | weak, as reported |
| camp basic-attack target, confirmation (CONTINUATION) | 94.16% (multi-target) | **80.9% of all camp attacks** | 94.16% vs min (HP, id) 78.28%, uniform 42.3% | holds; the all-attacks 98.87% is mostly forced |
| — several groups in range | 89.28% | — | vs min (HP, id) 40.90%, uniform 31.4% | holds: group retention is the content |
| — tied lowest HP (coordinate tie-break decides) | 88.80% | — | vs min (HP, id) 35.63% | holds: the (y, x) order is real |
| incoming entry (ROUTES), fifth | 83.37% (turn end) | 0% | all rows have a free tile, no stun, channel 0 or 1 (121 none, 3,517 recall, cancellable) | unchanged |
| trip forecast (ROUTES), fifth | 70.04% vs farm 61.02% | 0% (tribute impossible at 0 gems: 2,042 rows, 2-way) | gems >= 1: **63.20% vs always-farm 50.68%**; 0 gems: 84.18% vs 82.37% | holds on 3-way rows; the 0-gem rows add little |
| activities (FARM3 1a) | dead 8.5% of turns | **9.3% forced** | dead 190,854, stunned 13,969, respawn turns 3,050, teleport 0 | descriptive |

The camp-target rule is discovery 94.88% / confirmation 94.16% on free rows, against min (HP, id)
81.07% / 78.28%.

- The 82% / 81% forced share inflates only the all-attacks figure (99.09% / 98.87%), never
  reported as the headline.
- Destinations have a median of 12-15 feasible candidates; under 3% of rows are forced. So no
  destination headline is a rediscovered rule.
- The trip tree's tribute branch never fires at 0 gems (0 of 2,042 predictions; 3 labels). Its
  gain comes from the 4,217 rows where all three trips are possible.

## Caveats

- **Sharing is inferred, not observed.** Shared memory reads zero in replays (CHOICE.md). The
  8-byte buffer cannot carry every sighting: Fish must share a compressed summary, which the union
  overstates (section 5's breaks). The respawn-only result suggests the shared summary is clear/respawn events (a group id and round fits a few bytes per champion), but the encoding is not identified.
- **Not independent of my choices.** HELD was used to choose among tests. Only the seventh cohort
  is an untouched test.
- **Payout episodes** gain less (+1.1) than spawn exits (+2.8): after payout the actor has just
  seen its surroundings itself.
- The farm2 labels, unscoreable rows and the simplified clear time carry over (FARM-CHOICE.md).
- `farm3-heldout.json` was written before `farm3_evaluate.py` gained `--also`, and its recorded
  hash is the earlier file's. The scored code paths are unchanged.

## Reproduction

```sh
export PYTHONPATH=tools/fish OMP_NUM_THREADS=2
M=research/fish-2026-11-05
# observer snapshots (descriptive only) and section 1
node tools/fish/farm3_decode.mjs replays/fish-farm3/obs --jobs 6 $M/manifest.json $M/confirmation-manifest.json \
  $M/third-manifest.json $M/fourth-manifest.json $M/fifth-manifest.json $M/sixth-manifest.json
python3 tools/fish/farm3_describe.py $M/farm3-describe.json
# team-union memory, fit, held-out score
for c in model confirm third fourth fifth sixth; do python3 tools/fish/farm3_memory.py $c; done
python3 tools/fish/farm3_fit.py $M/farm3-fit.json model,confirm,third,fourth
python3 tools/fish/farm3_fit.py $M/farm3-fit-all.json model,confirm,third,fourth,fifth,sixth
python3 tools/fish/farm3_evaluate.py $M/farm3-fit.json $M/farm3-heldout.json fifth,sixth
# section 4
python3 tools/fish/farm3_explore.py $M/farm3-explore.json habit commit pairs payout liveness truth unshared lag opening closed
python3 tools/fish/farm3_explore.py $M/farm3-explore-kinds.json kinds
python3 tools/fish/farm3_audit.py $M/rule-audit-farm.json   # section 6
# seventh cohort, after farm3-seventh-freeze.json
D=replays/fish-farm3/seventh; S=$M/seventh-manifest.json
python3 tools/fish/decision_data.py $S replays/fish-seventh $D/decisions-v2.jsonl.gz
python3 tools/fish/routes_data.py $S replays/fish-seventh $D/decisions-v2.jsonl.gz $D/routes-v3.jsonl.gz
python3 tools/fish/choice_data.py replays/fish-seventh $D/routes-v3.jsonl.gz $D/choice-v1.jsonl.gz
python3 tools/fish/farm2_data.py $D/choice-v1.jsonl.gz replays/fish-seventh $D/farm2-v3.jsonl.gz
python3 tools/fish/farm3_memory.py seventh
python3 tools/fish/farm3_evaluate.py $M/farm3-fit.json $M/farm3-seventh.json seventh --also farm2_frozen=$M/farm2-fit.json
python3 tools/fish/farm3_evaluate.py $M/farm3-fit-all.json $M/farm3-seventh-all.json seventh
```

All scripts refuse to overwrite their outputs. `farm3_lib.cohort_paths` finds any cohort other
than the six under `replays/fish-farm3/NAME/`, so the seventh needed no code change after the
freeze. `farm3_describe.py` also writes per-game payout sequences and per-group sides
(`per_game`) and every solo big-camp clear (`solo_big`) to `farm3-describe.json`.
