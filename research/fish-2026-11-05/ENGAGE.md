# Fish: engaging, avoiding, pursuing and retreating at the strategic scale (2026-11-05)

This report covers how Intercontinental Fish behaves around enemies at distance 4 and beyond, how it leaves
fights, and its game-level approach. In-contact micro (positioning within range, spells, targets) is in
[COMBAT.md](COMBAT.md) and [TACTICS.md](TACTICS.md); farm targeting is in [FARM-CHOICE.md](FARM-CHOICE.md).

Fish has **no strategic engage mode**. It farms, and enemies bend its farming in proportion to how close
and how threatening they are:
- Its route is bent away from danger and toward weak enemies. Steps continue the current heading in
  70.5% of held-out range turns (never-close baseline 56.5%), and no override beats that. On the 95% of
  those turns where closing was legal and the step was not given up for an attack or cast, it is
  70.9% against 54.4% (audit below).
- It stops hitting a camp as an enemy closes in: 96% with none in sight, 84% at distance 8, 44% at 4,
  18% within 3.
- It walks away from contact mainly when wounded, and goes homeward. Half of the homeward share is
  map geometry (every legal step away is homeward); where it is not, 89% of its first steps away are
  homeward against 43% for a random legal step away.
- It does not pursue beyond sight, does not hunt remembered enemies, and does not rally to fights its
  allies cannot see.

No bot source changed.

## Data, split, causal inputs

- **Cohorts.** Fit: `model`, `confirm`, `third`, `fourth` (309 games). Held out: `fifth` + `sixth` (147 games,
  31 match groups), as in TACTICS/TEAM. The **seventh** cohort (265 games, 56 groups) was untouched until
  this study's freeze and was scored once (last section): every rule except the after-kill one replicates.
  - Every constant below was chosen on the fit cohorts.
  - The held-out cohorts had been decoded and used by earlier studies, but not for these labels. While
    exploring I printed held-out scores for a few depth-3 trees; no constant was chosen from them.
- **Rows** (`engage_rows.py`, `replays/fish-engage/<cohort>-rows-v1.jsonl.gz`) hold every Fish turn in
  sequence per actor. Each `x` comes from the actor's own start perspective, plus:
  - its own memory of each enemy's last sighting (tile, hp, round; kept 40 rounds);
  - enemies first seen later in the same turn;
  - enemy liveness: readable for unseen champions (rules `vision.unseen_units`); taken from the
    observer cache's camp-phase snapshot;
  - static walk distances to both spawns and from the nearest enemy.

  Each `y` is the turn's actions and end state. Later turns of the same actor are used only as labels.
- **Distances** are Chebyshev unless said otherwise. **Danger** and **D(c, d)** (one-turn damage reach) are
  COMBAT.md's. Side **EHP ratio** = (own + visible allies within 8) EHP / visible enemies' EHP within 8.
- **Hindsight route goal**: the end tile of the actor's next camp-hit turn within 40 rounds. Tables that
  stratify on it are descriptive, not predictors. It is used to separate travel from deviations.
- Counts are correlated turns, not independent trials. The JSONs carry per-cohort games and groups.
- **Audit: forced vs free (2026-11-06)**, `engage_audit.py` →
  [rule-audit-engage.json](rule-audit-engage.json), all seven cohorts. Each rule's opportunities are
  split by legality from the actor's turn-start view:
  - **forced**: only one outcome was legal. That covers no legal step of the needed kind (terrain,
    visible champions, visible live camps, the enemy spawn, a walk plus a ready dash in either order),
    stunned or teleporting. It also covers a same-turn outcome that forbids the step: a ranged basic
    attack without a walk, or an excludes-walking cast.
  - **free**: the alternative was legal.

  Each section gives the old number and then the free-row number with the same baseline. The old
  numbers reproduce exactly.

## 1. Enemies at range 4-8: no switch, a bent route

**Opportunities** (`engage_range.py`):
- a free turn: alive, unstunned, off spawn, no tribute or teleport channel, completing alive;
- the nearest visible enemy at 4-8, none nearer;
- no camp hit this turn, not standing on an empty group.

Fit 218,239 turns; held 66,407. Label: the actor's own end tile is closer to / as far from / farther from
that enemy's start tile.

| Held out, by | close | hold | open |
| --- | ---: | ---: | ---: |
| enemy at 4 (12,863) | 37.6% | 20.0% | 42.4% |
| enemy at 8 (9,912) | 50.8% | 22.5% | 26.6% |
| own hp < 0.5 (7,509) | **16.4%** | 39.0% | 44.7% |
| own hp >= 0.5 (58,898) | 47.0% | 19.4% | 33.6% |
| enemy hp < 0.4 (5,489) | **67.6%** | 15.6% | 16.8% |
| 1 / 2 / 3+ enemies in sight | 47.9 / 40.2 / 33.9% | | |

**Rule (approximate):**

```text
close this turn iff the previous step, continued, would close
```

| | Fit | **Held out** | Baseline (never close), held |
| --- | ---: | ---: | ---: |
| Momentum | 156,725/218,239 (71.8%) | **46,841/66,407 (70.5%)** | 56.5% |
| Audit: free rows (closing legal, no step-forbidding attack or cast) | 145,887/203,781 (71.6%), base 57.5% | **44,722/63,078 (70.9%)** | 54.4% |
| Audit: turn-level (camp-hit turns kept), free | 169,024/235,442 (71.8%), base 61.1% | **51,806/72,792 (71.2%)** | 58.4% |

- Fifth 70.5%, sixth 70.6%.
- **Audit.** 3,329 held rows (5.0%) were forced:
  - 2,119 had no legal closing step. Never-close is right on all of them, and momentum on 78.6%.
  - 1,210 cast an excludes-walking spell or made a ranged attack without walking. Momentum gets 37.3%
    of these.

  The forced rows lowered the margin, so on free rows momentum's lead grows from 14.1 to 16.5 points
  (seventh: 70.8% vs 54.5%).
  - The old selection dropped camp-hit turns, a same-turn outcome. Restated from the turn start (keep
    them, label them not closing): 71.2% against 58.4% on free rows. 11.7% of these turns hit a camp
    instead of stepping.
  - Corridors with a single legal closing step (7,398 held) score the same: 70.5% vs 60.2%.
  - Verdict: a real choice.
- Fit-grid overrides do not add anything: "close on prey (enemy hp <= 0.3-0.4, own hp > 0.5, ratio >= 1.5)"
  and "never close below 0.3 hp" reach 71.0% held. Fish is usually already heading toward the prey, so
  momentum has the answer.
- Exploratory ceiling: a gradient-boosted model over 36 causal features gets 68.9% held (62.7% without the
  momentum features). Per-turn step direction at range has no sharp rule.

### 1a. Route geometry: hurt Fish detours, healthy Fish walks on

Moving, non-dash range turns with a known route goal are split by whether any route-progress step keeps
the distance to the enemy:
- **forced**: every progress step closes on it;
- **free**: some progress step does not.

(Hindsight goal: a descriptive table.) Held out:

| | n | progress on route | close |
| --- | ---: | ---: | ---: |
| forced, own hp >= 0.5 | 9,456 | **66.9%** | 70.9% |
| forced, own hp < 0.5 | 896 | **21.5%** (stands 40.6%) | 23.2% |
| forced, enemy hp < 0.4 | 1,048 | 74.5% | 80.5% |
| forced, enemy at 4 → 8 | | 51.6% → 71.8% | |
| free, own hp >= 0.5 | 25,232 | 51.9% | 37.0% |
| free, own hp < 0.5 | 3,803 | 34.6% | **12.7%** |
| free, enemy hp < 0.4 | 2,389 | 37.6% | **60.2%** (detours toward it) |
| no enemy in sight (moving turns) | 361,383 (`model`+`confirm`) | 76% | |

```text
forced route: progress iff own hp/max > 0.5        held 7,035/10,352 (68.0%), always-progress 62.9%; fit 65.1% (61.8%)
audit, legal trade rows (a legal progress step exists, every one closes, no step-forbidding attack/cast):
                                                   held 7,471/10,509 (71.1%), always-progress 65.9%; fit 68.2% (64.5%); seventh 69.8% (65.8%)
```

- **Audit.** The forced/free split above counted every neighbour as a progress step, legal or not.
  - Of the 10,352 held "forced" rows, 464 (4.5%) had no legal progress step at all and 141 (1.4%) gave
    the step up to a ranged attack or an excludes-walking cast. Those 605 are forced: always-progress
    misses all of them, which is why the old baseline read low.
  - With legality, the trade class is 9,747 of the old rows plus 762 old "free" rows whose only safe
    progress steps were blocked.
  - On legal trade rows, progress: own hp >= 0.5 70.3% (9,571), < 0.5 **21.4%** (938). The old figures
    were 66.9% and 21.5%.
  - Verdict: a real choice. The hurt/healthy asymmetry is unchanged, and the margin over
    always-progress is 5.2 points (was 5.1).

- Progress on the route falls smoothly with proximity: held 68.2% at distance 8, 63.4% at 7, 58.7% at 6,
  53.7% at 5, 51.2% at 4.
- **Weak enemies attract**: Fish leaves its route to close on an enemy below 40% health (60% close against
  31% otherwise).
- **Wounds repel**: below half health Fish rarely closes even when the route asks for it.

### 1b. Danger-weighted steps

Among the route-progress steps (one king step, no dash, enemy 3-8, legal by terrain and visible units)
whose danger differs, the step taken has the minimum danger:

| | Fit | **Held out** | Random progress step, held |
| --- | ---: | ---: | ---: |
| All | 73.7% of 6,852 | **68.9% of 2,046** | 51.7% |
| Own hp < 0.5 | 84.6% of 721 | **87.8% of 237** | 49.2% |
| Audit, also blocking live camp tiles and the enemy spawn: all | 73.7% of 6,722 | **69.2% of 1,993** | 51.8% |
| Audit: own hp < 0.5 | 84.8% of 703 | **88.4% of 232** | 49.2% |
| Enemy at 5 / 6+ | 78.1% / 80.5% | 77.5% / 82.9% | 55.1% / 62.0% |

So the route is chosen with a danger cost (stronger when hurt), much as COMBAT's escape-dash landing is.
**Audit.** The step legality left camp tiles and the enemy spawn walkable.
- Blocking them drops 53 of 2,046 held rows (2.6%), which were left with fewer than two legal steps
  or no danger spread.
- The rate is unchanged: 69.2% (seventh 67.7% vs 51.3%).
- The rule is conditional on a single walked progress step. That is a parameter-given-act table, not
  a whether-to-step rule.
- Verdict: a real choice.
Counterexamples (held, hurt, not min-danger): `9984ed3c103d0602` r76 actor 2 (HoR);
`4dc0723fddb46297` r439-440 actor 8 (Issac).

### 1c. Farming under observation: a distance curve

Opportunity: last turn hit a camp and an awake camp still has the actor in range. Label: hits a camp again.

| Nearest enemy (held) | none | > 8 | 8 | 7 | 6 | 5 | 4 | 1-3 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| keeps hitting | 96.1% of 105,226 | 87.7% | 84.0% | 84.0% | 77.4% | 66.3% | 43.7% | 17.7% |

```text
keeps hitting iff nearest enemy > 4      held 8,213/10,191 (80.6%), always-hit 76.3%; fit 79.3% (75.5%)
keeps hitting iff no enemy D reaches it  held 8,068/10,191 (79.2%)
audit, free rows (a live visible camp in reach) held 8,172/9,996 (81.8%), always-hit 77.7%; fit 81.1% (77.5%); seventh 80.8% (77.5%)
```

**Audit.** Reach means:
- ranged: within 3, or 4 with a ready reset after a walk;
- melee: within 1 after an optional walk or dash;
- damaging spells: 4 (unit) or 5 (ground);
- Heart of Ruin's dash: 3.

Results:
- 195 held rows (1.9%) had no visible live camp in reach, and 5.6% of them hit one anyway: camps out
  of the start view, AoE and splash are outside this model.
- On free rows with an enemy in sight, by distance: 1-3 18.2%, 4 44.8%, 5 67.6%, 6 79.1%, 7 85.5%,
  8 85.3%, beyond 8 89.1%. The old curve is 18 / 44 / 66 / 77 / 84 / 84 / 88.
- Verdict: a real choice. The only change: the curve was measured with a few unreachable camps in it.

With an enemy D reaching the tile: 32.1% (healthy), 14.5% (hurt). Without: 81.3% (healthy), 50.7% (hurt).
This joins TEAM.md 3a ("no kiting at camps"): enemies make Fish stop hitting. TEAM 3a's "stays in camp
range 96%" is mostly forced, though: 76% of its rows could not leave range that turn or were ranged
attacks in place. Where stepping out was legal, Fish stays 87%, and at the range edge only 55%. See
TEAM.md's audit. Counterexample:
`9d1c0f3589a0e5d1` r136-139 actor 0 (Marcella keeps hitting with an enemy at 4).

### 1d. The "early" priority mode is a function of the end tile

Fish writes priority after moving. TEAM.md's unresolved early mode (L = -2..-5), split by the end-of-turn
distance to the nearest enemy (held):

| End distance | 1-2 | 3 | **4** | 5 | 6 | 7+ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| early | 0.1% | 3.8% | **14.8%** | 2.4% | 0.4% | 0.1% |
| contact | 99.6% | 67.1% | 26.4% | 15.3% | 11.1% | 6-9% |

Among quiet/early turns ending 3-5 from an enemy (held):

| D > 0 at the end tile | early |
| --- | ---: |
| neither side's | 1.2% of 16,796 |
| only Fish's | 24.2% of 3,939 |
| only the enemy's | 16.5% of 3,221 |
| **both** | **42.2%** of 2,207 |

- Fit: 1.3 / 27.5 / 17.0 / 46.5%.
- So early marks an end tile just outside basic reach but inside a dash or spell reach. It is not an
  intent to engage.
- Its 74% "closing" rate (start distance 5-6 → end 4) is mechanical: early written after a step *out*
  from 2-3 is 99% "opening".
- What separates early from quiet inside that band is still unknown (probably Fish's own threat model,
  with terrain).
- **Audit.** This is an output encoding, not a decision with alternatives. Priority is a free action of
  any value, applied from the next round, and Fish writes it from its end tile. No legality split
  applies, and nothing here is a choice rule.

## 2. Walking retreat: wounded Fish goes home, healthy Fish makes space

**Opportunities** (`engage_retreat.py`): free contact turns, an enemy within 3 at the start, three
consecutive own turns available, adjacent melee excluded (it always strikes, COMBAT.md). Fit 56,461; held
19,904.

**Label `retreat`**: after 3 own turns the actor's tile is >= 2 farther from the nearest enemy's start
tile, with no champion hit and no recall arrival.

| Held out | hp <= 0.54 | hp > 0.54 |
| --- | ---: | ---: |
| all | 42.8% of 4,427 | 14.7% of 15,477 |
| outnumbered by 2+ (enemies > allies + 1) | 45.1% | 23.2% |
| enemies = allies + 1 | 48.9% | 17.2% |
| enemies <= allies | 35.8% | 11.0% |
| carrying gems / not | 46.6% / 41.0% | 18.4% / 13.2% |
| ally died in last 10 rounds / not | 46.8% / 42.2% | 19.0% / 14.7% |
| on a running capture | 30.4% (46) | **7.2%** (447) |
| COMBAT "unacceptable" / acceptable | 45.6% / 28.2% | 28.9% / 13.3% |
| under ECONOMY's home gate (hp <= 0.63) / above | 36.9-43.5% / 12.1-16.8% (by home walk) | |

```text
walking retreat iff hp/max <= 0.36 and side EHP ratio <= 1.3   (fit-grid optimum)
```

| | Fit | **Held out** | never-retreat, held |
| --- | ---: | ---: | ---: |
| Rule | 43,003/56,461 (76.2%) | **15,892/19,904 (79.8%)** | 78.8% |
| COMBAT's unacceptable as the trigger | 70.6% | 73.8% | 78.8% |
| Audit: free rows (a 3-step walk/dash path to a tile >= 2 farther exists, turn-start occupancy) | 41,345/54,668 (75.6%), never 74.0% | **15,603/19,558 (79.8%)** | 78.5% |

- Fifth 77.6% (base 76.6%), sixth 84.1% (83.2%).
- **Refuted as a threshold decision.** Walking retreat is a graded tendency driven by own health. Each of
  these adds a few points to it: outnumbering, carrying, a recent ally death. A running capture suppresses
  it (TACTICS.md section 4).
- No rule beats never-retreat by more than one point.
- **Audit.** 346 held rows (1.7%) had no path to a tile 2 farther away within three steps (one more
  for a ready dash), with turn-start occupancy. They still retreat 3.5% of the time, because occupancy
  changes. On free rows the rule is 79.8% against 78.5%, so the margin is 1.2 points (was 1.0). Seventh
  free: 78.5% against 77.2%. Ranged hits and walking retreat are exclusive by rule, but the label is a
  3-turn turn-level choice (hit, stay or leave), so that does not force it. Verdict: a real choice, and
  a weak rule as before.

**Where to** (held: 2,243 episodes, the first retreat turn of each actor-run; fit 7,077):

| Over the 3 turns | Held | Fit |
| --- | ---: | ---: |
| home walk shorter | **86.4%** | 88.8% |
| home nearer (Chebyshev) | 76.3% | 80.7% |
| placebo: 3 steps straight away from the enemy brings home nearer | 58.3% | 56.8% |
| toward the nearest visible ally (ally >= 3 away; 758) | 56.7% (away 33.5%) | 54.9% (33.8%) |
| altar nearer / farther | 34.8% / 54.1% | 34.7% / 55.2% |
| ends on a bush (started on one) | 15.0% (16.8%) | 12.8% (14.0%) |

So walking retreats are homeward, not merely away. Bushes are not sought, and altars are avoided.

**Audit: how much of "homeward" is geometry.** At the first retreat turn, the actor's legal steps away
from the enemy (Chebyshev farther) are classified by whether they shorten the walk home:

| Held episodes (2,243) | share | first step away and homeward | home walk shorter over 3 turns |
| --- | ---: | ---: | ---: |
| every legal away step is homeward (forced) | 39.1% (877) | 87.7% | 98.9% |
| no legal away step is homeward (forced) | 9.6% (216) | 0 | 33.3% |
| no legal away step | 1.5% (33) | | 84.8% |
| **mixed (free)** | **49.8% (1,117)** | **74.6%** (of first steps away, 89.2%); random legal away step 43.4% | **86.9%** |

- The old 86.4% "home walk shorter" is half geometry: 50.2% of episodes had no first-step choice.
- On the free half, Fish picks the homeward step 89% of the time when it steps away, against 43% for a
  random legal away step (seventh 91% vs 44%).
- Verdict: partly rule (geometry). The remaining homeward preference is a real choice, and stronger
  than the old straight-away placebo comparison suggested.

**How it ends** (first within 40 turns, held):

| | all | hp < 0.3 | hp 0.3-0.6 | hp >= 0.6 |
| --- | ---: | ---: | ---: | ---: |
| re-engages (hits a champion) | 35.0% | 15.8% | 28.7% | 43.3% |
| reaches spawn | 30.9% | **55.9%** | 46.9% | 15.6% |
| farms | 20.5% | 4.0% | 16.3% | 26.9% |
| dies | 6.6% | 23.4% | 6.4% | 2.7% |
| tributes | 5.0% | 0 | 0.4% | 8.9% |

- Median turns to the end: re-engage 6, farm 7, home 9.
- When it resumes farming, it is the same group as its last camp hit in only **27.6%** of 457 held
  episodes (fit 28.6%). The median first camp hit is 5 tiles from where the retreat began.
- Two kinds of retreat:
  - **Wounded** (hp <= 0.63, ECONOMY's home gate): ends home 48.9%, dies 12.2%.
  - **Healthy**: spacing, which re-engages 42.8% and farms 26.5%.

Counterexample: `0fa9afb90c5f8200` r324-328 actor 5. Vesper at 43% with 71 gems is outside the rule's
0.36, yet walks 5 tiles home, heals, and leaves. This is ECONOMY's walk-home iff <= 5 steps.

## 3. No pursuit beyond sight, no hunting

`engage_lost.py`. **Lost sight**: no enemy in any own context this turn, while one seen last turn is
alive. L is its last-seen tile; the placebo is L mirrored through the actor. Fractions are of turns over
the next 5 (held, 10,043 episodes):

| | close on L | open from L | close on placebo | reaches L | re-sighted | camp hit |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| all lost enemies | 28.6% | 30.2% | 21.8% | 5.9% | 32.0% | 34.3% |
| a **target** (hit within 2 rounds; 673) | **18.2%** | **38.1%** | 13.2% | 33.4% | 29.3% | 29.1% |
| target lost at >= 3 (393) | 23.3% | 31.5% | 16.2% | 19.0% | | |
| weak target (< 40% hp; 332) | 17.8% | 39.6% | 10.5% | 39.9% | 16.0% | |

Fit is the same (target 17.1% close vs 39.0% open).

**Audit.** 633 of the 3,397 held target turns (18.6%) were forced:
- 305 had no legal step closing on L;
- 328 spent the turn on a ranged attack or an excludes-walking cast after re-sighting.

On free turns: close on L 22.2%, open 42.5%, placebo 15.3% (seventh 20.7 / 44.4 / 15.7%). Verdict: a
real choice, and the conclusion stands.

```text
no pursuit: after losing sight of its target, Fish opens from the last-seen tile about twice as often as it closes on it
```

- The small excess over the placebo is momentum, not search.
- "Reaches L" counts targets lost at distance 1-2, which are mostly on the tile already.
- COMBAT.md's chases end when sight ends.

**Hunting.** Free, non-farming turns with no enemy in sight, and memory of an alive enemy seen 2-10 rounds
ago at >= 9 (held 19,910):

| | Closes on its last-seen tile | Placebo |
| --- | ---: | ---: |
| all | **41.5%** | 41.4% |
| remembered carrier | 41.6% (7,203) | 41.6% |
| remembered weak enemy | 44.9% (1,547) | 38.7% (fit 52.1% vs 33.1%) |
| audit: both a closing step on L and one on the placebo legal (18,145; 8.9% dropped) | 45.1% | 44.2% (fit 46.7% vs 42.9%; seventh 45.1% vs 44.5%) |

- Fish does not hunt by memory. The weak-enemy excess is the only trace of attraction beyond sight.
- Counterexamples that do follow a lost target 3 turns (held): `cfc1265d7551c7d5` r1125 actor 9 (Cassi),
  r824 actor 11 (Willow); `bd2f59dff6a7ad93` r88 actor 5 (Marcella).

## 4. Regrouping: allies do not converge on unseen fights

Pairs: a Fish actor A hits an enemy champion (fight) or has seen none for 10 rounds (quiet control). An
ally B is 9-30 away, does not see A, and is free. Measured: B's distance change to A's tile over B's next
5 turns, and B arriving within 6 (held):

| B's view | A at 10-14: fight / quiet | 15-19 | 20-24 | arrive within 6 (10-14): fight / quiet |
| --- | ---: | ---: | ---: | ---: |
| blind (no enemy in sight or memory) | -0.27 / -0.20 | -0.62 / -0.40 | -0.77 / -0.51 | 8.5% / 12.0% |
| remembers an enemy | +0.12 / -0.43 | -0.53 / -0.66 | -1.06 / -0.86 | |
| sees an enemy | -0.55 / -0.03 | -0.35 / -0.35 | -0.09 / -0.48 | 11.9% / 6.0% |

- **No rally through shared memory.** A blind ally's drift toward an ally's fight is within 0.1-0.3 tiles
  in 5 turns of the quiet control, and its arrival rate is lower.
- Allies that see enemies near the fight converge a little at 5-14.
- Waiting for allies before a fight was not found either:
  - range closing rises only modestly with visible allies (1 enemy: 41% close with 0 allies, 49% with
    3+; `model` exploration);
  - TEAM.md 3b found no crew wait at camps.

## 5. After a fight

**After a Fish kill** (observer kill labels: a Fish hit that leaves the victim at <= 0 hp; 1,234 held). The
first of these within 40 turns:

| Held | fight on | farm | home | tribute | death |
| --- | ---: | ---: | ---: | ---: | ---: |
| all | 35.3% | 24.6% | 20.8% | 16.7% | 1.1% |
| another enemy in sight (749) | **53.0%** | 17.8% | 16.2% | 10.4% | 1.6% |
| none in sight (485) | 7.8% | 35.1% | 28.0% | **26.4%** | 0.2% |
| bag after the kill 0-9 / 10-29 / 30+ | 36.8 / 36.8 / 31.2% | 31.6 / 21.4 / 14.6% | 23.4 / 17.5 / 19.0% | **4.9 / 21.8 / 33.5%** | |
| own hp < 0.4 (95) | 33.7% | 11.6% | **46.3%** | 0 | 7.4% |

```text
fights on iff another enemy is in sight          held 844/1,234 (68.4%), never 64.8%; fit 60.9% (61.2%)
```

- The rule is weak (it is below baseline on fit).
- **Audit.** Nothing forces either endpoint: fighting on needs an enemy in sight later, and the rule
  conditions on turn-start sight. Verdict: a real choice, but the rule does not replicate (seventh 64.7%
  against never 69.4%).
- With no one left in sight, the bag decides between farming and banking (cf. ECONOMY.md 7).
- Kill gold (100) passes the home gate (gold >= 30), yet only 21-28% go home.

**After an ally dies**: within contact, a death in the last 10 rounds adds 4-5 points to walking retreat at
equal health (section 2). There is no team-wide flight.

## 6. General approach

Fish wins 352 of 456 games, and only 9 reach round 2000 (6 won). All rows, by phase and score state
(all six cohorts, `profiles` in the JSON; fit and held are alike):

| | enemy in sight | champion hit | camp hit | contact turns with a hit | range turns closing |
| --- | ---: | ---: | ---: | ---: | ---: |
| rounds 0-249 | 20% | 2.6% | 28.6% | 52.6% | 41.4% |
| rounds 500-749 | 27% | 3.0% | 18.8% | 51.9% | 41.7% |
| rounds 1000-1249 | 32% | 3.5% | 10.6% | 49.0% | 39.1% |
| rounds 1500+ | 36-37% | 3.1-3.2% | 7-8% | 37-42% | 28-32% |
| leading by > 200 | 32% | 3.5% | 19.7% | 51.6% | 40.3% |
| behind by >= 200 | 42% | 4.0% | 17.4% | 45.8% | 39.1% |
| opponent >= 800 | 40% | 3.7% | 14.9% | 44.5% | 39.9% |

- **One policy all game.** Fish farms first. Fights are incidental to farming and grow as camps thin out
  and the teams meet more.
- Being behind, or the opponent nearing 1000, does not raise its aggression: contact hit rate and range
  closing drop slightly. It keeps farming and banking (tribute starts rise when leading: 0.80% of turns at
  lead > 200, against 0.42% behind).
- Long games (1500+ rounds) are the defensive tail: fewer camps, less closing, fewer contact hits.
- **By champion** (all cohorts):

  | | enemy in sight | champion hit | range closing | contact hit |
  | --- | ---: | ---: | ---: | ---: |
  | Marcella | 38.5% | 5.7% | 45.2% | 52.8% |
  | Heart of Ruin | 28.6% | 3.7% | 42.2% | 54.0% |
  | Vesper | 24.6% | 3.4% | 45.7% | **67.4%** |
  | Vendetta | 28.9% | 3.0% | 41.0% | 44.6% |
  | Cassi | 24.3% | 2.7% | 40.1% | 54.0% |
  | Issac | 27.3% | 2.3% | 39.3% | 42.4% |
  | Willow | 23.0% | **1.4%** | **31.5%** | 48.3% |

  Marcella is the front-liner, Vesper the most willing ranged hitter, and Willow keeps out.

## Negative results (do not redo)

- **A discrete engage/avoid decision at range.** No hp/danger/ratio/prey threshold beats momentum (70.5%).
  Trees over 36 causal features stay at 59-61% for the 3-way step. Deviation trees (approach/hold/away among
  off-route steps) get 59% vs 37% majority, and their top split is momentum.
- **The early mode as an engage intent.** It is end-tile geometry (section 1d).
- **COMBAT's acceptability as a walking-retreat trigger.** It scores below never-retreat (73.8% vs 78.8%).
- **Memory pursuit, hunting, shared-memory rallies** (sections 3-4).
- **Bush ambush or bush retreat.** Retreats end on bushes no more than they start on them.

## Compared with astraeus

- **Range behaviour.**
  - astraeus decides fights by simulation (`stand_lost_at`, `combat/fight.cc`). It retreats from packs that
    outmatch it by health × damage (`hurt_retreat_ratio` 3.85 when hurt below
    `hurt_health_fraction` 0.47 or carrying `brake_bag` 22; `home_retreat_ratio` 2.61 on own ground). Its
    `guard_work` keeps farm steps off tiles `want_home` would flee.
  - Fish has no pack zone. It bends the farm route by a danger cost (min-danger step 69% vs 52% random,
    88% when hurt) and stops hitting camps once an enemy is within 4.
- **Prey.**
  - astraeus chases via `preyable`: in vision, not near the enemy spawn, and out of range on its own
    ground only if hurt or carrying.
  - Fish's attraction to enemies below 40% health is the same idea, applied as a route detour at 4-8
    tiles. It also never goes beyond sight.
  - astraeus's `Safety` tracks unseen enemies (`credible_unseen`) for danger, not for pursuit. Fish shows
    no memory pursuit either.
- **Retreat destination.**
  - astraeus `retreat_step` ranks steps by risked damage, then steps home: homeward unless a sideways
    step is clear.
  - Fish's walking retreat is homeward too. It has an 86% shorter home walk, against a 58% straight-away
    placebo. Half of that is geometry: where it had a choice, 89% of its first steps away are homeward,
    against 43% for a random legal step away.
    Its escape dashes instead minimise danger (TACTICS.md).
- **Regrouping.** astraeus gathers Monolith crews (`mono_gather_share`) and Willow pairs (`support.cc`).
  Fish rallies to nothing it cannot see.
- **After a kill.** No equivalent branch in astraeus; it re-decides each turn. Fish's split (fight on if
  another enemy is visible, else the bag decides) is the same in effect.
- **Score state.** astraeus has `game_ender` and winning-bag logic; Fish shows no comeback aggression.

None of this says Fish's choices are better; A/B before porting anything.

## Seventh-cohort test (untouched; scored once)

The seventh cohort: [seventh-manifest.json](seventh-manifest.json), 265 games, 56 groups, 21:40-23:40 UTC
November 5.

**Freeze first.** [engage-seventh-freeze.json](engage-seventh-freeze.json) (2026-11-06T00:15:14Z) holds the
SHA-256 of every `engage_*` script and of the fit/held results. It was written before any seventh play was
read.

**Procedure.**
- Seventh had no observer caches. `team_decode.mjs` (unchanged) wrote them to
  `replays/fish-engage/team-seventh`.
- Rows, range and retreat files were built with the frozen scripts.
- `engage_eval.py`'s `--team-cache` replaces the observer path for the fit cohorts too, so its first run
  stopped before writing anything. It was rerun unchanged (hash verified) with `--team-cache
  replays/fish-engage/team-merged`: symlinks to `replays/fish-team` plus `team-seventh`. Scored once.

Results: [engage-results-seventh.json](engage-results-seventh.json) and
[engage-lost-seventh.json](engage-lost-seventh.json).

| Rule (frozen) | Held (fifth+sixth) | **Seventh** | Seventh baseline |
| --- | ---: | ---: | ---: |
| Range: close iff momentum closes | 70.5% | **92,837/131,570 (70.6%)** | never close 56.5% |
| Forced route: progress iff hp > 0.5 | 68.0% | **13,144/19,640 (66.9%)** | always progress 63.2% |
| — forced, hp >= 0.5 / < 0.5: progress | 66.9% / 21.5% | 66.4% / 27.1% | |
| — free, enemy hp < 0.4 / ok: close | 60.2% / 31.4% | 58.6% / 31.8% | |
| Danger: chosen step min-danger (random) | 68.9% (51.7%) | **67.6% (51.3%)** of 4,133 | |
| — own hp < 0.5 | 87.8% (49.2%) | **85.8% (50.4%)** of 457 | |
| Camp: keeps hitting iff nearest enemy > 4 | 80.6% | **17,262/21,742 (79.4%)** | always 76.0% |
| — curve none / 8 / 6 / 5 / 4 / 1-3 | 96 / 84 / 77 / 66 / 44 / 18% | 96 / 82 / 75 / 67 / 43 / 19% | |
| Early at end tile: neither / both sides' D > 0 | 1.2% / 42.2% | **1.1% / 40.7%** | |
| Retreat iff hp <= 0.36 and ratio <= 1.3 | 79.8% (78.8%) | **25,467/32,408 (78.6%)** | never 77.4% |
| — COMBAT unacceptable as trigger | 73.8% | 72.4% | 77.4% |
| Retreat: home walk shorter (straight-away placebo) | 86.4% (58.3%) | **88.9% (57.2%)** of 3,720 | |
| — toward nearest ally / away | 56.7 / 33.5% | 59.2 / 29.4% | |
| — ends re-engage / home / farm / death / tribute | 35 / 31 / 20 / 7 / 5% | 33 / 30 / 24 / 7 / 4% | |
| — resumed farm on the same group | 27.6% | 29.5% of 895 | |
| Lost target, next 5 turns: close / open last-seen tile | 18.2 / 38.1% | **17.2 / 40.7%** (918) | placebo 13.8% |
| Hunt: close on remembered enemy (placebo) | 41.5% (41.4%) | **42.3% (42.4%)** of 42,269 | |
| — remembered weak enemy | 44.9% (38.7%) | 46.7% (36.1%) of 2,875 | |
| Blind ally, 5-turn change toward an unseen fight, 10-14 / 15-19 / 20-24 (quiet control) | -0.27 / -0.62 / -0.77 (-0.20 / -0.40 / -0.51) | -0.28 / -0.46 / -0.62 (-0.04 / -0.26 / -0.52) | |
| After a kill: fights on iff another enemy in sight | 68.4% (64.8%) | **1,292/1,997 (64.7%)** | never 69.4% |
| — fight on with / without another enemy in sight | 53.0 / 7.8% | 46.1 / 7.2% | |

Seventh confirms these, with nearly the same margins:
- the momentum rule;
- the hurt/weak-enemy route asymmetries;
- danger-weighted steps;
- the camp distance curve;
- the end-tile account of early;
- homeward retreats;
- no pursuit beyond sight, and no hunting.

The walking-retreat rule again beats never-retreat by about one point only; it stays a tendency. The
after-kill rule **fails** on seventh (below its baseline), though the descriptive split it rests on
(7% vs 46%) holds. Treat it as a description, not a predictor. The blind-ally convergence excess is
0.1-0.25 tiles in 5 turns at 10-19 and none at 20+: no rally.

## Reproduce

```sh
export PYTHONPATH=tools/fish OMP_NUM_THREADS=2; R=research/fish-2026-11-05; E=replays/fish-engage
for c in model confirm third fourth fifth sixth; do python3 tools/fish/engage_rows.py $c --jobs 6; done   # ~3 min/cohort
python3 tools/fish/engage_range.py $E/range-v1.jsonl.gz
python3 tools/fish/engage_retreat.py $E/retreat-v2.jsonl.gz     # v1 lacked tiles; deleted
python3 tools/fish/engage_eval.py $R/engage-results.json          # sections 1, 2, 4, 5, 6 (~10 min)
python3 tools/fish/engage_lost.py $R/engage-lost.json             # section 3
python3 tools/fish/engage_show.py fifth 610a60f9343bc486 0 378 392   # one actor's turns, one line each (--all: whole team)
python3 tools/fish/engage_audit.py $R/rule-audit-engage.json       # forced vs free audit, all 7 cohorts (~2 min, 6 procs)
```

- Seventh: the commands in the freeze file, with `--team-cache replays/fish-engage/team-merged` for
  `engage_eval.py` (`ln -s` every file of `replays/fish-team` and `replays/fish-engage/team-seventh` into it).
- Every script refuses to overwrite its output.
- [engage-seventh-freeze.json](engage-seventh-freeze.json) holds the SHA-256 of the scripts and fit/held
  results, and the seventh commands.
- Counterexamples (SHA16, round, actor) are in each JSON's `errors` / `counterexamples_*` / `examples_held`.
- Held-out momentum misses, e.g. `610a60f9343bc486` r381-390 actor 0: Vesper finishes a 183-gem tribute,
  walks a lane with Varg shadowing at 6-8, then dashes onto Marcella.
