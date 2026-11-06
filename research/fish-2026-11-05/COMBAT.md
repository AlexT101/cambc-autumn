# Fish: combat against enemy champions (2026-11-05)

What Intercontinental Fish does when it can see enemy champions: when it steps into or stays in
contact and when it backs off, kill-securing, chasing, and which spell it casts. Six rules hold
on the held-out cohorts. Three are near-deterministic spell rules (above 92%). Two are
threshold rules for positioning and chasing (about 72%, against 57-58% baselines). The sixth is
the kill override: given a kill, Fish takes it (98%). No bot source changed. Earlier results
(targeting, recall, holders) are not repeated here.

## Data, split and features

- **Discovery** (the thresholds were fit here): `model` 124 games, `confirm` 96, `third` 43.
- **Held out**: `fourth` 46 and `fifth` 94. These are later games from match groups disjoint from discovery.
- All games use engine `v3_0_0`. Fish's submission version is unknown.
- The held-out cohorts had been decoded by earlier work, and I printed exploratory tree scores
  on them while choosing which features to try. They are not an untouched test. The frozen
  thresholds come from `combat_fit.py` on discovery only. The user said not to worry much about
  overfitting.
- Turns are correlated, so the counts below are agreement over turns, not independent trials.
  Every metric's game count is in `combat-results.json`.

New caches, in `replays/fish-combat/`:

- `<cohort>-combat-v2.jsonl.gz` (`combat_data.py`): one row per **contact turn**. A contact
  turn is a completed Fish turn, alive and not stunned, whose start perspective shows a living
  enemy champion. Rows: 162,404 / 145,355 / 44,460 / 70,164 / 92,727.
- `<cohort>-tiles-v1.jsonl.gz` (`combat_tiles.py`): **end-tile choices**. These are contact
  turns with an enemy within 5. They exclude dash, teleport and tribute turns, and turns starting
  in a tribute or teleport channel. Rows: 64,246 / 65,074 / 20,245 / 25,790 / 36,625.
- The `*-combat-v1` files are an aborted run (a dead-at-end crash): ignore them.

Every feature comes from the actor's own start perspective (`g.read({team, champion})` via
the existing caches). Labels come from the turn's actions, its end perspective and the actor's
next turns. Definitions (`combat_common.py`):

- **One-turn damage reach** `D(c, d)` is the most damage champion `c` can deal in one turn to a
  unit at Chebyshev distance `d`. The options are:
  - a basic attack within range, plus one walk for melee (a ranged walk spends the attack);
  - doubled by an attack reset if the reset is ready;
  - a dash adding 2 to reach;
  - a ready damage spell within 4: unit ×Focus, ground +1 radius, Heart of Ruin's dash 1.5×Focus plus a basic attack.

  One cast per turn. Heart of Ruin's passive is applied. It ignores terrain, blockers and items.
- **Danger(tile)** is the sum of `D(e, dist(tile, e))` over visible enemies not stunned for
  their next turn, divided by own effective HP (health + shield).
- **Kill** means some enemy attackable from the tile has `D(me, ·) >= HP + shield`.

## 1. Positioning: stay in or enter contact only when healthy and the tile is not too dangerous

Three contexts, each a real choice: an alternative tile exists, and the actor is off its spawn.

| Context | Engage means | Decline means |
| --- | --- | --- |
| **m2**: melee, nearest enemy at 2 | ends adjacent to an enemy, or hits a champion with a spell | stays out |
| **m1**: melee, adjacent (it attacks either way) | stays adjacent | steps away (hit-and-run) |
| **r**: ranged, nearest enemy within 3 | does not increase the distance (stands; can shoot without a reset) | backs off |

```text
engage iff kill available from an engage tile
        or (own_hp / max_hp > 0.49 and min danger over engage tiles <= 0.28)
```

`0.49 / 0.28` is the discovery grid optimum. Variants:

- Without the kill override: `0.45 / 0.28`.
- With health adjusted for gems (`×0.65` when carrying, as in Fish's priority encoding): `0.41 / 0.28`.
  It scores the same, so the carried bag adds nothing here.

Results (`combat-fit.json`, `combat-results.json`). The baseline is each context's discovery
majority: m2 declines, m1 and r engage.

| | Discovery | Held out | Held-out baseline |
| --- | ---: | ---: | ---: |
| All three contexts | 28,766/40,309 (71.4%) | **12,881/17,708 (72.7%)** | 10,009 (56.5%) |
| m2: melee approach | 10,728/14,844 | **4,100/5,617 (73.0%)** | 2,515 (44.8%) |
| m1: melee hit-and-run | 9,729/13,641 | **3,981/5,470 (72.8%)** | 3,620 (66.2%) |
| r: ranged stand or back off | 8,309/11,824 | **4,800/6,621 (72.5%)** | 3,874 (58.5%) |
| Same rule, no kill override | 28,443/40,309 | 12,677/17,708 (71.6%) | |
| Gradient-boosted ceiling, 20 turn-start features | 82.5% | 76.6% | |

On held-out turns where a kill is available from an engage tile, Fish engages in
**738/750 (98.4%)**; discovery 1,221/1,231. Across all reachable opportunities in discovery
the engage rate is only 32% for melee one step out and 51% for ranged in range.

The two thresholds recur across separately fitted depth-2 trees:

- melee approach: hp > 0.53 and danger ≤ 0.24;
- hit-and-run: leave if hp ≤ 0.44;
- ranged: back off if hp ≤ 0.52 or danger > 0.27.

The equivalent single-number form, effective health after the threatened hits
`ehpf × (1 − danger) > 0.45`, scores the same (70.9-71.0% on held-out without the kill override).

Health effect, descriptive (discovery). Melee adjacent to an enemy always attacks, but steps
away afterwards in:

| Own health | Steps away |
| --- | ---: |
| 100% | 18% |
| 70% | 31% |
| 50% | 42% |
| 30% | 67% |
| 0-10% | 76-78% |

Where it fails:

- The errors are mostly the rule predicting engagement where Fish declines: 2,944 such
  held-out errors, against 1,883 the other way.
- Healthy, low-danger refusals are common. In `d3e831065afbc6a8`, r55 actor 3, Marcella at 78%
  health and danger 0.05 steps away. In r56 actor 6, Issac at 67% and danger 0.07 does not step in.
- The ceiling says about 4 points remain in my features. The rest is probably destination or
  farming goals, unseen allies, and turn order.
- **Refuted**: a single numbers or power threshold. Using allies' plus own effective HP or
  HP×Strength against visible enemies within 4/6/8/all, the best gets 64.5% (held out 59.8-64.7%).
- Fish's allies agree in the same round only a little more than chance (47.7% against 39.4%),
  so there is no strong team-wide fight/flee mode.

## 2. Spells on champions follow the movement decision

**Exclusive damage spells** (Cassi slot 0, Marcella slot 1, Prism slot 0): when ready, with a
visible enemy champion within 4.

- **Cast iff standing still** and the turn's cast is unused: **4,151/4,252 (97.6%)** held out;
  never-cast baseline 48.6%. Discovery 97.9%.
- Counting a cast in either slot as the prediction: 3,838/4,252 (90.3%).
- When it walks it cannot cast; that part is mechanical. The informative part is that standing
  still with a target in range means casting: 2,185 of the 2,286 held-out standing turns.
- So the damage-cast question reduces to the positioning rule above. This is why the earlier
  turn-start damage-cast tree (77%, missing half the casts) was weak.
- Failures: `4b0912db07f842d7` r588 and r995 actor 4 (Marcella) stand and do not cast.

**Cassi's stun** (slot 1, not exclusive): ready, with an eligible enemy within 4 (not Marcella,
not already stunned).

- **Stun unless she stands still with her damage spell ready**: **914/966 (94.6%)** held out;
  always-stun 80.9%. Discovery 1,885/2,004.
- She stuns on 1,256/1,260 discovery turns when she walks, and on 295/309 when she stands with
  damage on cooldown. Standing with both ready, she casts damage 77% of the time.
- Failures: 49 held-out stuns while standing with damage ready, e.g. `c25a98d6ca2ab58e` r330
  and r620 actor 9.

**Heart of Ruin's shield**: off spawn, ready.

- **Shield iff a visible unstunned enemy has `D > 0` against it**: **12,418/13,449 (92.3%)**
  held out; never-shield 85.0%.
- With threat: 1,228 casts of 1,469. Without threat: 790 casts of 11,980. Camp damage is not
  modelled, which probably explains those 790.
- Failures: `617803df21349794` r959 actor 4, threat 464 at 4 tiles, no shield;
  `c25a98d6ca2ab58e` r249 actor 8 shields with no enemy reach.

**Attack resets** (Vendetta, Issac, Marcella): after a basic attack on a champion that the hit
does not kill, with the reset ready.

- **Reset and attack again**: **1,823/1,852 (98.4%)** held out when the turn's cast is unused;
  2,270/2,299 count the other slot's cast as the alternative. Discovery 98.7%.
- When the cast went elsewhere, it was Vendetta's or Issac's dash to reach, or Marcella's damage spell.
- Ranged resets (Vesper, Willow) are mostly walk, reset, attack. They are not modelled.
- Failures: `08ae1d96d715f304` r710 actor 5 and r660 actor 8.

Dashes are used both ways. Within 5 of an enemy, discovery counts:

| | Engage (hits that turn) | Escape (ends farther, no hit) |
| --- | ---: | ---: |
| Vendetta | 1,111 | 633 |
| Heart of Ruin | 1,985 | 625 |
| Issac | 831 | 594 |

No dash rule was fitted.

## 3. Chasing: follow a fleeing target if it is weak, or if Fish is healthy and not outnumbered

Opportunity: last round's turn hit enemy E, and E is now the nearest visible enemy but out of
basic range (more than 1 for melee, more than 3 for ranged). Chased means hitting E this turn,
or stepping closer without hitting anyone else.

```text
chase iff E_hp / E_max <= 0.37
       or ((own + visible allies within 8) EHP / visible enemies' EHP > 1.24
           and gem_health > 0.44)
```

- Result: **4,005/5,532 (72.4%)** held out, against always-chase 58.3%. Discovery 9,434/13,117
  (71.9%, base 54.4%). The thresholds come from a discovery depth-3 tree, simplified.
- Errors: 876 predicted chases that do not happen, 651 chases missed. For example,
  `d3e831065afbc6a8` r51/r53 actor 3: Marcella chases an 86%-health target at an EHP ratio of 1.18.

**How far**: chases are short. A streak is consecutive rounds following or hitting the same
target that fled. Held-out streaks:

| Streak length | Streaks |
| --- | ---: |
| 1 turn | 1,180 |
| 2 turns | 496 |
| 3 turns | 222 |
| 4 turns | 167 |
| 5 or more | 205 |

Total 2,270. The longer ones nearly all end on a turn that hits the target.

The first sighting is not a separate decision. Episodes with no contact for 5+ rounds and an
enemy within 5 split almost only on whether a hit is possible now (depth-3 tree 76.3% held out over 494
episodes, against 60.1% never-engage).

## What did not pan out (do not redo)

- **Priority as a combat label.** In contact Fish writes large priorities, ±(500..800) plus
  small offsets, with the sign alternating by round. It does so about 90% of the time with an
  enemy within 2, against 2% with none visible. But in that mode it hits only about 60% of
  reachable turns, against about 12% in the ordinary small-negative mode. It is a co-output, not
  a decision label, and it is not decoded here.
- **Exact-tile choice.** A conditional logit over the 9 tiles gets only 31-38%, against 19-33%
  for "stay". Non-combat goals dominate the exact step.

## Compared with astraeus

- **Health line.** Fish's 0.49 matches astraeus `hurt_health_fraction = 0.47`, below which
  astraeus retreats from smaller packs.
  - Astraeus decides by a fight simulation (`stand_lost_at`) and health×damage pack ratios
    (`hurt_retreat_ratio` 3.85, `home_retreat_ratio` 2.61).
  - Fish is reproduced by a per-tile danger cap (≤ 0.28 of own EHP) plus a kill override. Pack
    ratios alone do not explain Fish (≤ 64.7%).
- **HoR shield.** Astraeus `shield_if_needed` (self_abilities.cc) shields when a seen enemy's
  blow reaches us, or an awake camp reaches us. That is the same rule.
- **Chasing.** Astraeus `chase_health = 0.4` chases (dash_to_attack) an enemy below 40% and
  below our own fraction. Fish's 0.37 target line is close. Fish also chases healthier targets
  when its side has more than 1.24× the visible EHP.
- **Resets and exclusive damage.** Fish resets whenever the cast is free. Astraeus withholds the
  reset only when Varg's shield is wanted. Fish casts exclusive damage whenever standing.
  Astraeus prices casts (`chip_value`) per strike search; whether it ever stands still without
  casting was not checked.

## Caveats

- Reach and danger are Chebyshev and ignore terrain, hidden units, items (Durability, Skirmish)
  and camp damage.
- Danger uses only enemies visible at turn start.
- Thresholds are fitted split points, not recovered source constants.
- The spell rules are conditional on that turn's walking (an outcome of the same turn), except
  the HoR shield rule.
- Prism, Stellar and Tavi have few or no rows.

## Reproduce

```sh
for c in model confirm third fourth fifth; do
  python3 tools/fish/combat_data.py $c
  python3 tools/fish/combat_tiles.py $c
done   # to new --out dirs
OMP_NUM_THREADS=2 python3 tools/fish/combat_fit.py /tmp/combat-fit.json   # discovery-only thresholds, GBM ceiling
python3 tools/fish/combat_eval.py /tmp/combat-results.json   # every rule, both splits, errors gzip beside
```

Rules: `tools/fish/combat_rules.py`. Every failure is in `combat-results.errors.jsonl.gz`, with
game, round, actor, step and features. Twelve per metric and split are in `combat-results.json`.

## Sixth-cohort check (added by the coordinating session)

The sixth cohort ([sixth-manifest.json](sixth-manifest.json), 53 games / 11 groups, 21:10–21:40
UTC) had been decoded for destination scoring but never used for combat features or rules. The
combat scripts and `combat-fit.json` were hashed in [combat-sixth-freeze.json](combat-sixth-freeze.json)
first; the only later edit appends `sixth` to `combat_common.COHORTS`. `combat_data.py sixth`,
`combat_tiles.py sixth`, then `combat_eval.py` wrote [combat-results-sixth.json](combat-results-sixth.json)
(+ errors). Held-out results, accuracy (baseline):

| Rule | Fourth | Fifth | **Sixth** |
| --- | ---: | ---: | ---: |
| Positioning, health/danger + kill override | 71.8% (56.5%) | 73.3% (56.5%) | **4,481/5,824 76.9% (60.4%)** |
| — m2 (melee, enemy at 2) | 72.2% (46.9%) | 73.4% (43.6%) | 1,604/2,108 76.1% (34.4%) |
| — m1 (melee, adjacent) | 71.5% (66.1%) | 73.5% (66.2%) | 1,642/2,103 78.1% (76.6%) |
| — r (ranged) | 71.8% (56.8%) | 73.0% (59.7%) | 1,235/1,613 76.6% (73.3%) |
| Kill available → engage | 98.0% | 98.6% | 316/326 96.9% (63.8%) |
| Damage spell iff standing still | 97.9% (50.8%) | 97.4% (47.2%) | 1,204/1,238 97.2% (42.1%) |
| Cassi stun unless still with damage ready | 94.3% (83.8%) | 94.8% (78.9%) | 243/260 93.5% (73.1%) |
| Heart of Ruin shield iff threatened | 92.6% (85.6%) | 92.1% (84.6%) | 3,828/4,152 92.2% (82.6%) |
| Reset after a surviving basic, cast unused | 98.6% | 98.4% | 614/627 97.9% (2.1%) |
| Chase | 70.9% (56.6%) | 73.3% (59.3%) | 1,543/2,006 76.9% (66.2%) |

Every rule holds. On the sixth cohort the positioning rule's edge over the per-context majority
is mostly in m2; for m1 and ranged contexts the majority answer is nearly as good (78.1% vs
76.6%, 76.6% vs 73.3%). Counts here are per cohort; the running totals `combat_eval.py` prints
are cumulative.

## Seventh-cohort check (coordinating session, 2026-11-06)

[seventh-manifest.json](seventh-manifest.json): 265 games / 56 groups, 21:40–23:40 UTC
November 5, pinned by `pin_cohort.py` with `combat-fit.json` and `combat_rules.py` hashed in
[seventh-freeze.json](seventh-freeze.json) before decoding (all hashes matched at scoring).
[seventh-audit.json](seventh-audit.json): 3,271,252 inputs / 1,240,049 completed turns, exact.
The only code edit was appending `seventh` to `combat_common.COHORTS`. Results in
[combat-results-seventh.json](combat-results-seventh.json) (+ errors), accuracy (baseline):

| Rule | Seventh |
| --- | ---: |
| Positioning, health/danger + kill override | 20,292/27,589 73.6% (57.2%) |
| — m2 / m1 / r | 73.5% (42.1%) / 74.2% (69.5%) / 72.9% (61.0%) |
| Kill available → engage | 1,259/1,275 98.7% (63.4%) |
| Damage spell iff standing still | 6,572/6,766 97.1% (48.7%) |
| Cassi stun unless still with damage ready | 1,336/1,413 94.6% (78.9%) |
| Heart of Ruin shield iff threatened | 21,357/23,135 92.3% (84.7%) |
| Reset after a surviving basic, cast unused | 3,012/3,065 98.3% (1.7%) |
| Chase | 6,951/9,465 73.4% (61.2%) |

Every rule holds at its fourth/fifth level, on five times the sixth cohort's games.

## Audit: forced vs free decisions (2026-11-06)

[rule-audit-micro.json](rule-audit-micro.json) holds these numbers, written by
`python3 tools/fish/micro_audit.py OUT --jobs 6`. It reads COMBAT's own `-combat-v2` rows for all
seven cohorts.

- **Method.**
  - A row is **forced** when cambc-rules.yaml leaves only the predicted outcome legal, given the
    same-turn outcome the rule conditions on.
  - A row is **free** when the alternative was legal.
  - Rules that condition on a same-turn outcome are also restated as a choice from turn-start
    state.
- **Scope.** Numbers pool all cohorts; seventh alone is in brackets. This covers section 2 and
  the seventh-cohort check table above. Its "damage spell", "Cassi stun", "HoR shield" and
  "reset" rows repeat the old metrics and are superseded by the table below.

| Rule | Old (baseline) | Forced rows | Free rows (baseline) | Turn level from turn-start state | Verdict |
| --- | --- | --- | --- | --- | --- |
| Damage spell iff standing still | 21,775/22,314 97.6% (never 49.5%) [97.1%] | 10,495 (47.0%): walked 10,245 (exclusive), cast spent 250 | 11,280/11,819 95.4% = "always cast" (never 4.6%) [94.7%] | always cast 50.5% against never 49.5% [51.3%]; cast iff acceptable at the start tile 15,473/22,314 69.3% [70.2%] | **partly rule** |
| Cassi stun unless still with damage ready | 4,378/4,643 94.3% (always stun 80.5%) [94.6%] | 839 (18.1%): damage cast, so the turn's one cast is spent | 3,539/3,804 93.0%, **below** always stun 98.3% [93.2%; 97.9%] | damage on cooldown: stun 2,354/2,379 (98.9%); both ready: damage 822, stun 1,384, none 58 | **pure rule** for the "unless" |
| Heart of Ruin shield iff threatened | 66,278/71,727 92.4% (never 84.6%) [92.3%] | 4,013 (5.6%): dash cast; the rule scores 78.4% there | 63,132/67,714 93.2% (never 83.7%) [93.1%]: threatened 6,793/7,134 shield, unthreatened 93.0% no shield | — (turn-start inputs) | **real choice** |
| Reset after a surviving basic, cast unused | 9,892/10,045 98.5% (1.5%) [98.3%] | 1,810: a cast before the basic, so a reset is impossible (excluded from the old row, correctly) | — | the cast still unused at the basic: reset 9,892/10,527 94.0% (6.0%) [94.6%]; 482 cast another spell later | **real choice**, inflated by about 4.5 points |
| Positioning, health/danger + kill override | 73.6% [seventh] | none: walking stays legal (stunned turns are excluded) | = old | turn-start inputs | real choice |
| Kill available → engage | 98.7% [seventh] | none | = old | turn-start inputs | real choice |
| Chase | 73.4% [seventh] | none | = old | turn-start inputs and the previous turn | real choice |

- **Damage spells.**
  - When Fish walks, the exclusive cast is illegal, so the "walks → no cast" half (47% of rows)
    scores 100% by rule.
  - What remains is "standing still with the cast unused → cast", a nearly constant 95.4%.
  - From turn-start state the decision is the positioning one: COMBAT's acceptable line predicts
    the cast at 69.3%.
  - So the 97.6% headline is half rule and half "casts when it can". The informative number is
    69%, in line with DECISIONS' 77% cast tree.
- **Cassi's stun.**
  - Its exception, no stun when she stands with damage ready, is the one-cast-per-turn rule.
    On the 269 free rows where she stood with damage ready and did not cast it, she stunned 87%.
  - From turn-start state she casts something on 97% of the turns where both spells are ready.
  - Her damage-or-stun choice is not recovered:

    | Predictor (both ready) | Accuracy |
    | --- | ---: |
    | Damage iff COMBAT-acceptable, else stun | 57.2% |
    | Always stun | 61.1% |
    | Always damage | 36.3% |

  - The real finding is "always cast one spell", not the conditional rule.
- **Heart of Ruin's shield.** The shield shares the turn's cast with the stun-dash. On the 4,013
  dash turns the shield was illegal, and those rows were most of the rule's errors. On free rows
  the rule improves slightly, to 93.2%.
- **Resets.**
  - The old row dropped the turns where another spell was cast after the basic, which is a
    same-turn outcome.
  - Scored from the moment of the basic, with the cast still unused, the rule is 94.0%.
- **Positioning and chasing** use turn-start inputs, and walking stays legal on their rows, so
  they are real choices. The audit does not change them.
