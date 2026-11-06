# Fish: combat micro in contact, as a team (2026-11-05)

This report covers what Intercontinental Fish does once its champions and the enemy's are in contact.
It looks at whom the team hits and in what order, the stuns and ground spells not decoded before,
spacing, bushes and wards, fights beside awake camps, and who takes kills.

Headline: **Fish has no team-level targeting.** Each champion applies its own target rule at the
moment it acts. Allies converge only because earlier hits make the same enemy the lowest-health
one. Spacing has less structure than first reported, once the game rules are separated out:

- a ranged champion that walks away from a melee enemy within 2 ends out of its reach (90%,
  against 38% for a random tile). Whether it walks at all is close to a coin flip (55%, against 45%);
- retreating champions walk to the lowest-danger tile;
- melee champions do **not** choose the tile beside the weakest enemy. That held only on turns
  where they then hit it, and melee range forces those;
- every champion prefers bushes everywhere, not just in fights.

The rules were fitted on four cohorts, checked on two held-out cohorts, then frozen and scored
once on the untouched **seventh cohort**, where every rule held. No bot source changed.

**Audit: forced vs free rows (2026-11-06).** Each rule was re-scored on the rows where
cambc-rules.yaml leaves the alternative legal. Rules that condition on a same-turn outcome were
restated from turn-start state. The script is `tools/fish/micro_audit.py`, the output
[rule-audit-micro.json](rule-audit-micro.json); all seven cohorts are pooled, and seventh is also
reported alone. Corrections are marked "Audit" in place, with the old numbers kept beside them.

- **Pure rule, dropped:**
  - "no ward input within 10 rounds of the previous one" is the ward recharge;
  - "melee ends beside the weakest enemy" is the basic-target rule, seen through the end tile.
- **Partly rule:**
  - Prism's and Ren's "cast iff still": 38% and 65% of the rows are forced;
  - Marcella's re-hit: 91% forced;
  - ranged end distance: a random tile is already 84% safe;
  - kill securing: the "share of deaths" number.
- **Real choices:**
  - the target rules (2+ candidates, so free by construction);
  - the ranged kiting tile given a walk, and the declines;
  - bush pathing and the ward rate.

## Data, split and evaluation

- **Fit:** `model`, `confirm`, `third` and `fourth` (253 games with contact rows, 45 groups).
- **Held out:** `fifth` and `sixth` (111 games, 31 groups). Other studies had decoded these, but
  not for these labels.
- **Seventh:** 265 games (201 with multi-candidate basic attacks, 56 groups), 21:40-23:40 UTC on
  November 5.
  - Hashes of every `micro_*` script and dependency were frozen in
    [micro-seventh-freeze.json](micro-seventh-freeze.json) (00:10 UTC November 6).
  - The freeze came before any seventh-cohort micro row was built.
  - The hashes still matched when seventh was scored.
- **Inputs are causal.**
  - Target rules read each attack's or cast's own before-state. That is the actor's view at the
    moment it acts, so it already includes what earlier allies did to visible enemies.
  - The alternative rules add one observer-derived input each (micro_rows `ctx`): which enemies
    earlier Fish actors hit or stunned this round, the actor's own previous targets, and who hurt
    Fish since the actor's last turn. These inputs precede the decision and an ally could post
    them in the 8 shared bytes, but Fish may not actually read them.
- **Labels** come from a new observer decode, `micro_decode.mjs`. It records every action's full
  effect on every champion and camp: damage including AoE, splash and HoR's landing, kills and
  stuns.
- **Tile rules are conditional on the turn's class**, which is an outcome. "In the best set" is
  compared with a uniformly random candidate of the same class.
- **Danger** is COMBAT.md's: the sum of the visible, unstunned enemies' one-turn reach, divided by
  own HP + shield.
- **Spawn caveat.** micro_rows drops turns on spawn using `misc_rows.spawn_tiles`, the ring that
  MISC's correction widened by one tile, rather than `breadth.spawn`. That wrongly drops 2,467 of
  491,518 contact turns (0.5%), 513 of 148,714 in seventh. The rules were not re-scored for it.
- Counts are correlated turns, not independent trials. "Meaningful" means two or more candidates
  and, for an alternative rule, a pick different from the baseline.

## 1. Focus fire and sequencing: none beyond min-EHP

```text
basic attack target  = argmin (hp + shield, id) over visible enemies in basic range    (known rule)
unit damage target   = argmax (gems + 8) / (hp + shield)                               (known rule)
Cassi stun target    = argmax Strength, excluding Marcella and positive-timer stuns    (known rule)
no term for: an ally's target this round, a stunned enemy, own last target, the last attacker,
             an enemy yet to act this round
```

Basic attacks with 2 or more candidates. In the alternative rows, "alternative" is how often Fish
picks the alternative where it differs from min-EHP; the min-EHP column scores the same rows:

| Rule | Fit | Held out | **Seventh** |
| --- | ---: | ---: | ---: |
| min (hp + shield, id), all multi-candidate rows | 5,845/6,254 (93.5%) | 1,961/2,077 (94.4%) | **2,836/3,029 (93.6%)** |
| Alternative: target an ally hit earlier this round | 101/312 (32.4%); min-EHP 66.7% | 19/79; 73.4% | **30/110 (27.3%); 70.9%** |
| Alternative: own previous-turn target | 103/676 (15.2%); 84.5% | 30/193; 82.9% | 46/300 (15.3%); 84.3% |
| Alternative: retaliate on the last enemy that hurt me | 66/1,382 (4.8%) | 19/410 (4.6%) | 28/677 (4.1%) |
| Unstunned enemies first (all mixed rows) | 173/483 (35.8%); min-EHP 89.9% | 44/142; 92.2% | 105/253 (41.5%); 93.7% |

**Convergence happens anyway.** Take basic attacks where an earlier Fish hitter's target is among 2
or more candidates. The later hitter joins that target in:

| | Fit | Held out | **Seventh** |
| --- | ---: | ---: | ---: |
| Joins, actual | 1,168/1,380 (84.6%) | 378/440 (85.9%) | **502/596 (84.2%)** |
| Joins, as min-EHP predicts | 79.0% | 82.5% | 81.7% |
| Joins, random candidate | 52.2% | 51.9% | 52.5% |
| When min-EHP points elsewhere: joins | 95/290 (32.8%) | 18/77 (23.4%) | **28/109 (25.7%)** |
| — random candidate | 46.8% | 46.5% | 46.7% |

- When min-EHP points elsewhere, Fish joins *less* often than a random pick would.
- A scratch grid on fit found almost nothing more. It tried a focus bonus on the ally's target
  (×0.5-0.9, −50..−300 EHP, −0.5..−5 × the damage allies dealt) and an own-target bonus. The best,
  −150 EHP, gains 14/6,254. It was not saved.
- Some joins still go against min-EHP (113 of the 409 fit errors). They concentrate where the two
  EHPs are within 1.5× of each other (75/133 join, against 21/148 beyond 1.5×). No simple bonus
  reproduces them.
- Examples:
  - `5e2578c38cc2fe3b` r44 actors 4 and 2: Issac and HoR hit Willow's target, Vesper (820 and 775
    EHP), over Marcella (508) and Issac (502).
  - `8419760728c945c9` r88-89 actor 2: HoR hits HoR (880 with shield) over Ryth (440) twice.

**Stun, then hit?** Later Fish basics this round, with an enemy stunned earlier this round among 2
or more candidates, hit the stunned enemy at the rate min-EHP predicts:

| | Fit | Held out | Seventh |
| --- | ---: | ---: | ---: |
| Hits the stunned enemy | 152/207 | 43/62 | 63/94 |
| — min-EHP prediction | 148 | 43 | 63 |
| — random | 115 | 33.5 | 49.7 |

**Spells and allies.**

- Unit damage spells, alternative "an ally's target first", where it differs: 5/98, 5/37, 3/41.
  The ratio rule itself holds at 92.2% / 91.7% / **91.1% (595/653)**.
- Cassi stun, the same alternative: 5/40, 2/11, 3/20. Max Strength holds at 91.3% / 86.0% /
  **90.5% (171/189)**.
- **Sequencing.** A stun on an enemy yet to act this round removes that enemy's turn in this round.
  Cassi does not prefer such enemies. With mixed candidates, the yet-to-act enemy is stunned in:

  | | Fit | Held out | Seventh |
  | --- | ---: | ---: | ---: |
  | Actual | 59/104 | 11/31 | 23/57 |
  | Max Strength predicts | 63 | 13 | 22 |
  | Random | 52.0 | 15.0 | 28.1 |

**Holding an attack for a teammate's kill: no.** See section 6. Melee attacks 99.6% of the time
with an enemy in range (DECISIONS.md), and exclusive damage spells are cast whenever Fish stands
still (COMBAT.md).

- **Audit:** half of COMBAT's "still" rule is forced, because a walk forbids the cast. On free rows
  (stood, the cast unused) it is "always cast", at 95.4%.

## 2. Stuns and ground spells for the remaining kits

**Fish never drafts Ryth, Tavi or Stellar** (0 of 456 earlier games, and none in seventh's rows).
Their stuns and ground spells cannot be decoded from Fish. Prism (17 earlier games), Ren (13) and
Varg (4) are rare. Stuns landed by source, fit:

| Source | Stuns landed |
| --- | ---: |
| Cassi slot 1 | 2,991 |
| HoR dash | 1,815, from 1,559 casts |
| Marcella reset-stun | 1,245 |
| Ren | 112 |
| Prism | 44 |

```text
Marcella reset-stun: the reset (slot 0) follows a surviving basic (COMBAT's reset rule); the stunning
                     second basic hits the same target as the first
Prism:  standing still, enemy within 4: slot 0 (unit damage+stun) if ready, else slot 1 (ground)
        (walking forbids both: they are exclusive)
        ground centre = the tile within 4 with the most visible enemies within 1 (camps ignored)
        unit stun target ≈ max (gems+8)/EHP, Marcella included (the damage is the point)
Ren:    stun (slot 0) ready, enemy within 4, standing still: cast (walking forbids it)
```

| Rule | Fit | Held out | **Seventh** |
| --- | ---: | ---: | ---: |
| Marcella's stunning basic = her first basic's target (2+ candidates) | 138/138 | 62/62 | **69/69** |
| — every reset-stun on a champion | 1,615/1,615 | 544/546 | 884/885 |
| — min EHP, for comparison | 94.2% | 93.5% | 92.8% |
| Prism slot rule (baseline: never cast) | 275/343 (80.2%; 50.1%) | 161/183 (88.0%; 44.3%) | **96/116 (82.8%; 35.3%)** |
| Prism ground centre maximises enemies hit | 139/143 | 89/91 | **63/64** |
| — when 2 or more enemies can be hit | 17/17 | 19/20 | 6/6 |
| Ren stun iff standing still (baseline: never) | 360/374 (96.3%; 68.5%) | 187/193 (96.9%; 74.1%) | **424/434 (97.7%; 60.8%)** |

**Audit, Prism and Ren.** Both of Prism's spells and Ren's stun are exclusive, so a walk rules
them out: "walking: no cast" is the rule. The table pools all cohorts; seventh alone is in
brackets.

| | Prism | Ren |
| --- | ---: | ---: |
| Old "cast iff still" | 490/496 98.8% (92/97) | 990/1,001 98.9% (430/434) |
| Forced rows (walked, or the turn's cast spent) | 188 (38%) | 652 (65%) |
| Free rows (stood): casts (baseline: never) | 302/308 98.1%; 1.9% (70/75) | 338/349 96.8%; 3.2% (170/174) |
| Turn level from turn-start state: always cast (baseline: never) | 60.9%; 39.1% | 33.8%; 66.2% |
| Both ready, stood and cast: slot 0 | 60/65 (92.3%) | |

- Given that it stands, Fish always casts, which is a real but obvious choice.
- The decision that matters is whether to stand. Ren stands on only a third of its opportunities.
  That is the spacing question (section 3), not a spell rule.
- Prism's slot order is a real choice.

- **Audit, Marcella's re-hit.** Of the 3,029 reset-stuns (all cohorts), 2,761 (91%) have only one
  enemy champion in her reach at the second basic, so the re-hit is forced there.
  - The 268 with 2 or more are the table's first row (269 there, from a slightly different join).
    All 268 re-hit; min EHP alone predicts 93.7%.
  - In the 17 where min EHP points elsewhere, all 17 re-hit the first target (5/5 in seventh).
  - Verdict: mostly rule, plus a real but small-sample persistence.
- **Marcella** switches nothing for the stun: max Strength would get only 47% / 42% / 45%. One reset
  in five (414 of 2,029 in fit) spends its second basic on a camp.
- **Prism's area.**
  - Its ground spell mostly hits one enemy: 115 of 143 fit casts.
  - A camp is in the 3x3 on only 15 of 144 fit casts, so the spell is not a farming tool in contact.
  - With both slots ready it casts the unit stun: 57 of 58 fit cases when at most one enemy fits in a
    3x3.
- **Prism's unit stun is a finisher as often as a stun.** Fit outcomes: kill 60, stun 44, wasted on
  stun-immune Marcella 23. Held out: 6, 50, 8. Seventh: 15, 20, 15.
- **Unit-stun targets are too few to settle.** Prism and Ren, 2+ candidates, all cohorts:
  - Prism: (gems+8)/EHP 24/30, min EHP 22/30, max Strength 16/30.
  - Ren: (gems+8)/EHP 35/48, min EHP 32/48, max Strength 31/48.
- Unlike Cassi's pure stun, these damage stuns do not skip Marcella: 5 / 9 / 12 of Ren's.
- Counterexamples: Prism `880de20cafbfcff6` r62 actor 6 (centre hits fewer than possible); Ren
  `65ba43301b83bf2f` r906 actor 10.

## 3. Spacing in contact

The population is completed, unstunned turns off spawn with an enemy within 5, walking without
dash, teleport or tribute. Candidates are the start tile and its walkable neighbours.

```text
ranged, a melee enemy within 2, walks:   end >= 3 from every melee enemy
ranged, walks and stays within 3 of one:  maximise distance (capped at 3) to the nearest melee enemy
any decline (walks to a farther tile):    the lowest-danger farther tile
melee, walks and ends adjacent:           no tile rule (audit: "beside the weakest" was its hit)
tie-break among same-distance tiles:      bush (section 4)
```

| Hypothesis: end tile in the best set (random) | Fit | Held out | **Seventh** |
| --- | ---: | ---: | ---: |
| Ranged, melee within 2: ends >= 3 from all melee | 1,841/2,051 89.8% (38.5%) | 525/595 88.2% (36.5%) | **950/1,041 91.3% (38.4%)** |
| Ranged, stays in range: farthest from melee (cap 3) | 3,674/4,362 84.2% (45.0%) | 1,020/1,238 82.4% (43.6%) | **1,795/2,083 86.2% (45.6%)** |
| — the same tiles by min danger | 82.1% | 78.6% | 81.2% |
| Ranged decline: min danger | 631/684 92.2% (60.4%) | 134/151 88.7% (62.9%) | **307/349 88.0% (59.2%)** |
| Melee decline: min danger | 2,671/3,094 86.3% (58.1%) | 581/706 82.3% (57.7%) | **1,279/1,491 85.8% (58.9%)** |
| Melee engage: adjacent to the weakest | 1,471/2,076 70.9% (49.8%) | 452/583 77.5% (49.3%) | **750/987 76.0% (49.2%)** |
| — min danger among adjacent tiles | 62.7% (43.9%) | 62.7% (45.2%) | 62.2% (45.1%) |
| — most enemies adjacent | 44.9% (38.6%) | 52.5% (38.6%) | 53.0% (39.1%) |
| Any walk: min danger over all candidates | 67.1% (51.8%) | 59.7% (51.4%) | 61.5% (52.1%) |

**Audit, spacing.**

- **Melee engage is not a tile choice.** The 3,646 engage rows (all cohorts) split by whether the
  actor hits the weakest reachable enemy after its last step.
  - If it does (1,822 rows), melee range puts the end tile next to that enemy: 1,821/1,822 end
    beside it, against 45.0% random.
  - If it does not (1,824 rows), Fish ends beside the weakest in 46.7% of them, below random's
    54.2%.
  - So the "adjacent to the weakest" row (70.9% / 77.5% / 76.0%) is the basic-target rule seen
    through the end tile. It is dropped, and so are its sub-rows.
- **Ranged, melee within 2.** "Given that it walks" conditions on the turn's outcome.
  - From turn-start state: a ranged champion with a melee enemy within 2 and a tile 3 or more
    from every melee enemy ends 3 or more away in 3,442/6,293 turns (54.7%). Staying within 2 is
    45.3%. Seventh alone: 984/1,784 (55.2%).
  - The tile rule given a walk (89.8% against 38.5%) stands, since the walk could legally end on
    any neighbour.
  - Whether to walk is COMBAT's ranged line. A ranged walk spends the basic attack, so this is the
    choice between shooting and kiting.
- **Ranged distance at turn end** (the bullet below) is mostly geometry.
  - Over 77,677 ranged contact turns with a melee enemy visible, 89.1% end 3 or more from every
    melee enemy. A random candidate tile scores 84.0%.
  - A fifth of them (15,578) are forced: a basic attack without a reset rules out walking. Those
    score 73.3%, against 67.6% random.
  - On free rows it is 93.0%, against 88.1%: a small real preference.
- The declines and "stays in range: farthest" also condition on a walk, but they compare tiles
  within that class, so they remain free tile choices.

- **Turn classes.** The rules work within a class: kite, back off, step in. Over all candidates,
  min danger is weak, because destinations dominate the step (COMBAT's 31-38% logit). Choosing the
  class is COMBAT's positioning rule (about 72%).
- **Ranged champions keep out of melee reach.** At turn end in contact, the share at distance 3 or
  more from the nearest melee enemy (fit): Cassi 91%, Willow 89%, Prism 88%, Vesper 84%.
  - Audit: a random candidate tile already gives 84%, so this is mostly geometry (see above).
  - Cassi's mode is 4-5 tiles (25% and 29%), her spell range rather than her basic range.
  - Against ranged enemies she is within 3 only 8% of the time.
- **With a melee enemy within 2, ranged champions often stand and shoot.** Fit counts:

  | | Turns | Stand and hit | Walk |
  | --- | ---: | ---: | ---: |
  | Cassi | 2,588 | 833 | 1,755 |
  | Vesper | 1,723 | 1,000 | 703 |

  Whether to stand or step is COMBAT's ranged health/danger line. The table above is where they
  step to.
- **Varg** has 10 rows in all: no splash-tile rule can be tested.
- Counterexamples:
  - ranged: `610a60f9343bc486` r401 actor 0 (Vesper); `f712c0309f4a38b3` r714 actor 6 (Cassi);
  - melee engage: `72e3972091749179` r200 actor 10; `d956fc1080aa56d0` r454 actor 2;
  - decline: `fe5675fd7c40fa51` r101 actor 2.

## 4. Bushes and wards

```text
pathing: among tiles making the same progress, step onto a bush (in every context)
wards:   about 2-3x more often in contact; the tile is the bush-vision one (MISC), not pushed
         towards the enemy
ambush:  no evidence; hit rates from bushes are only slightly higher
```

**Bush pathing.** Take walking turns where the tiles that make the same progress towards where the
actor stands three turns later (a destination proxy) include both bush and open tiles. The share
ending on a bush (expected share in brackets):

| Context | Fit | Held out | Seventh |
| --- | ---: | ---: | ---: |
| Enemy within 5 | 9,054/12,343 73.4% (44.1%) | 3,602/4,831 74.6% (42.9%) | 5,441/7,447 73.1% (44.0%) |
| Enemy visible, farther | 70.4% (43.7%) | 78.6% (43.2%) | 78.3% (44.0%) |
| No enemy visible | 72.6% (44.8%) | 71.0% (43.6%) | 71.1% (45.2%) |

The same tie-break holds in contact for tiles at the same distance to the nearest enemy:
70.9% / 71.7% / 72.2%, against 44.7% / 43.2% / 44.4% random. This is a pathing habit, not a
fight tactic. Wall-adjacent tiles get only 59-63% (48% random).

**Hits from bushes.** With an enemy in basic range at turn start, off spawn, the hit rate:

| | Fit | Held out | Seventh |
| --- | ---: | ---: | ---: |
| On a bush, unseen by the in-range enemies | 3,036/3,909 (77.7%) | 83.5% | 84.7% |
| On a bush, seen | 81.7% | 86.5% | 87.1% |
| Open | 77.6% | 80.1% | 80.0% |

There is no ambush pattern beyond being on bushes more.

**Wards.** Placement rate with the ward ready (10+ rounds since the actor's last ward input):

| Context | Fit | Held out | Seventh |
| --- | ---: | ---: | ---: |
| Contact | 7,666/110,766 (6.9%) | 3,006/30,637 (9.8%) | 4,726/59,125 (8.0%) |
| Enemy visible | 4.9% | 6.0% | 5.0% |
| None | 3.0% | 3.0% | 2.9% |

- In contact the ward tile is on a bush in 63% / 69% / 69% of placements.
- The ward is more often farther from the nearest enemy than the actor is (3,916 farther, 2,507
  nearer, 1,243 equal of 7,666 in fit). It scouts bushes, not the enemy.

## 5. Fights beside awake camps

Below, "enemy in reach" means Fish's one-turn reach is above 0 against it; "in fire" means inside
an awake visible camp's range. The hit rate on enemies in reach (self / enemy):

| | Fit | Held out | Seventh |
| --- | ---: | ---: | ---: |
| clear / clear | 40.1% | 48.7% | 48.3% |
| clear / enemy in fire | 29.4% | 34.6% | 35.7% |
| in fire / clear | 31.8% | 37.0% | 35.7% |
| both in fire | 38.9% | 51.0% | 44.1% |

- Fish does not use camp aggro against enemies: it hits enemies in camp fire *less* often.
- Kills are taken regardless:

  | Killable, killed | Fit | Held out | Seventh |
  | --- | ---: | ---: | ---: |
  | Enemy in fire | 84.3% | 83.5% | 85.6% |
  | Enemy clear | 84.1% | 84.5% | 89.1% |

- 10-14% of Fish's kills are on an enemy in camp fire. Taking such a kill keeps the bag from being
  destroyed by the camp, but it is not prioritised.
- Already covered elsewhere and not redone: contested captures (TACTICS: Fish fights the holder
  rather than stepping on), stuns on tributes (base rate), lock placement (MISC: pre-banking), and
  the late priority mode handing tie hits to the enemy (TEAM).
- Last hits on camps carry no reward (captures pay the holders). Only Vendetta's passive rewards
  them, so last-hitting was not studied.

## 6. Kill securing

```text
the first Fish actor in turn order with the enemy in its one-turn kill reach kills it 84-89% of
the time (audit; 98.5-99.2% was the share of the deaths)
no actor holds a hit for a teammate; there is no preference for who takes the kill
```

| | Fit | Held out | **Seventh** |
| --- | ---: | ---: | ---: |
| Enemies in some Fish actor's kill reach | 2,893 | 1,545 | 2,335 |
| — die this round | 2,469 (85.3%) | 1,311 (84.9%) | 2,102 (90.0%) |
| — killer is the first capable actor (of the deaths) | 2,438 (98.7%) | 1,301 (99.2%) | **2,070 (98.5%)** |
| — Audit: the first capable actor kills it (of all killable) | 2,438/2,893 (84.3%) | 1,301/1,545 (84.2%) | **2,070/2,335 (88.7%)** |
| First capable actor does not hit that enemy | 373 | 214 | 228 |
| — kills another instead | 76 | 38 | 66 |
| — hits another | 57 | 28 | 34 |
| — no hit; a later ally kills it ("holding") | **20 (0.7%)** | 7 (0.5%) | 20 (0.9%) |
| — no hit; it survives | 220 | 141 | 108 |

- **Audit.** The "of the deaths" share is close to structural.
  - The first capable actor acts first, so when a capable actor kills the enemy, it is usually
    that one.
  - From turn-start state, the first capable actor kills the enemy in 84-89% of cases.
  - The real finding is the holding row: 0.5-0.9%. No actor declines a kill for a teammate.
- The surviving no-hit cases fit the reach approximation (terrain and items ignored) and COMBAT's
  2% non-engage on kills.
- Kills by type, fit: Marcella 933, Vendetta 600, Vesper 466, HoR 410, Cassi 261, Issac 184,
  Prism 109.
- 567 of 3,034 fit kills (19%) come from an actor without the kill in its turn-start reach: hits
  earlier in the round and approximate reach.

## What did not pan out

- **Focus bonuses.** Any focus bonus, own-target persistence, retaliation or stunned-target term on
  basics (section 1).
- **Stun choices.** Yet-to-act stun targets, and ally-target stuns.
- **Ground stuns of the other kits.** Ryth, Tavi and Stellar never appear on Fish.
- **Varg splash tiles.** Too few rows.
- **Melee tile shapes.** "Most enemies adjacent" barely beats random; "fewest adjacent" is below
  random.
- **Fighting by the camps.** Camp-fire avoidance as a tile rule is weak (56-63% against 48-49%
  random), and Fish does not exploit camp aggro.
- **Ambushes.** No ambush beyond the general bush habit; wards are not aimed at enemies.
- **Audit drops.**
  - The ward recharge, a game rule.
  - The melee "beside the weakest" tile, which is the target rule.
  - Ranged end distance as a headline, since most tiles are already safe.

## Compared with astraeus

- **Targets.**
  - astraeus prices every hit by `hit_worth_of` (`combat/abilities.cc`): kill distance with the bag
    at `gem_value × gems`, plus recall/stun worths, inside a per-champion strike search
    (`combat/plan.cc`).
  - Fish uses fixed rules per slot (min EHP; (gems+8)/EHP; max Strength).
  - Neither assigns targets across the team. astraeus's only cross-turn link is its own kill bid
    (`model/follow.h`), which Fish has no counterpart for. proteus's shared slot ledger is closer to
    team assignment than anything Fish does.
- **Stuns.**
  - astraeus's `stun_worth` values the turn the target loses (that turn's strike at our nearest
    body), tribute cancels and recalls.
  - Fish's Cassi takes max Strength and ignores whether the enemy has acted.
  - Fish's Prism and Ren damage stuns ignore Marcella's immunity.
- **Spacing.**
  - astraeus scores a plan's end tile by the damage expected there (`plan.h`), and retreats by
    `retreat_step` (damage risked, then stun-free, then home).
  - That is Fish's min-danger decline. Fish's ranged "stay 3 or more from melee" falls out of the
    same danger, since melee reach is walk + hit.
  - Whether astraeus's ranged champions also step in beside the weakest enemy, or keep at 4-5
    tiles as Cassi does, was not checked.
- **Bushes.**
  - astraeus places wards for bush vision (`ward_bushes`).
  - A path preference for bush tiles (73% against 44%) was not found in astraeus's pathing in this
    pass, so it is unverified. It would hide Fish's champions from enemies outside the bush.

None of this says Fish's choices are better; they are descriptions to test by A/B.

## Reproduce

```sh
export PYTHONPATH=tools/fish R=research/fish-2026-11-05
node tools/fish/micro_decode.mjs replays/fish-micro/obs --jobs 5 $R/manifest.json $R/confirmation-manifest.json \
  $R/third-manifest.json $R/fourth-manifest.json $R/fifth-manifest.json $R/sixth-manifest.json $R/seventh-manifest.json
for c in model confirm third fourth fifth sixth seventh; do python3 tools/fish/micro_rows.py $c --jobs 6; done
python3 tools/fish/micro_focus.py    $R/micro-focus.json    --splits fit held seventh   # sections 1, 6
python3 tools/fish/micro_spells.py   $R/micro-spells.json   --splits fit held seventh   # section 2
python3 tools/fish/micro_space.py    $R/micro-space.json    --splits fit held seventh   # sections 3-5 tiles
python3 tools/fish/micro_camps.py    $R/micro-camps.json    --splits fit held seventh   # section 5
python3 tools/fish/micro_bushward.py $R/micro-bushward.json --splits fit held seventh --jobs 6   # section 4
python3 tools/fish/micro_audit.py    $R/rule-audit-micro.json --jobs 6   # forced vs free (needs micro-focus.json)
```

- Every script refuses to overwrite its output. `micro_decode.mjs` skips existing games only with
  `--resume`.
- Rows: `replays/fish-micro/<cohort>-micro-v1.jsonl.gz`. Observer decode:
  `replays/fish-micro/obs/<SHA16>.json.gz`.
- The JSONs hold counts per split, game and group coverage, and up to 12 counterexamples per split
  (game SHA16, round, actor).
