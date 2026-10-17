# nemesis baseline for the optimality report's metrics

2026-10-17. Bot: bots/nemesis at e647cbd, frozen as bots/baselines/nemesis-v1 (draft Cassi & Issac, Varg, Stellar,
Ryth, Tavi). Every number below comes from the generalised scripts in `scripts/` (selection options in
`scripts/gamesel.py`), with the same definitions for nemesis and the ladder teams. No win-rate testing here.

## Sources

Local batches (`py run_batched.py nemesis <opponent> [--gen|--central]`, both sides, default options), all extracted
into replays/.analysis. The gen and central suites are the new ones (seeds 3107 and 3108); every match completed.

| batch | opponent | maps | games | nemesis wins |
|---|---|---|---|---|
| replays/batch-20261017-091937-928141 | rival | maps/gen (132) | 264 | 58.0% |
| replays/batch-20261017-092038-365160 | rival | maps/gen-central (46) | 92 | 59.8% |
| replays/batch-20261017-092118-221354 | morgana | maps/gen | 264 | 69.3% |
| replays/batch-20261017-092216-917498 | morgana | maps/gen-central | 92 | 66.3% |
| replays/batch-20261017-092239-309635 | aphelios | maps/gen | 264 | 84.8% |
| replays/batch-20261017-092342-732047 | aphelios | maps/gen-central | 92 | 88.0% |
| replays/batch-20261017-093624-653243 | rival | maps/ (17 ladder maps) | 34 | 50.0% |
| replays/batch-20261017-093638-790228 | morgana | maps/ | 34 | 61.8% |
| replays/batch-20261017-093649-017773 | aphelios | maps/ | 34 | 70.6% |

Columns used below:

- **nem v rival**: the first two batches (356 games, nemesis's side). The opponent's own numbers from the same games
  are in the script outputs (rival is within noise of nemesis on almost every metric).
- **nem all**: the six gen/central batches (1,068 games).
- **nem ladder maps**: the last three batches (102 games on the 17 maps in `maps/`, the current ladder pool).
- **procless / Fish / Mite**: their ladder games in replays/.analysis since 2026-10-16 (316 / 260 / 343 games,
  `--no-copies`). Rows marked *current pool* use only games since 20261016-113842 (113 / 113 / 137 games), when
  the ladder switched to the map versions in `maps/`: before that, corners, expanse, interlock and lanes had
  pure gem-cluster groups that the current versions lack, so economy rows mix map versions otherwise.

There are no ladder games of nemesis yet (submitted 12:59Z; the newest downloaded ladder group is from 05:50Z), and
only 14 games of rival on the ladder (PTN Hyperion since 20261016-211800), too few to tabulate; they are in the
script outputs as a sanity check (they are close to local rival on Ryth walking, tanking shares and ward rates).

Reproduce (from any working directory; deathaudit and turnreach2 write a .pkl there):

```
cd research/optimality/scripts
for s in spellhold2 spellwaste3 h2h_econ campshare wards deathaudit chase turnreach2 freedouble bushhits; do
  py $s.py --src replays/batch-20261017-091937-928141 replays/batch-20261017-092038-365160 --team nemesis rival --limit 1000000
  py $s.py --team procless "Intercontinental Fish" Mite --no-copies --limit 1000000   # + --since 20261016-113842: current pool
done
```

## Caveats

- **Opponents.** Local opponents are our own bots. They pre-start a recall at every turn end (memory
  local-recall-prestart-skew), so locally the enemy looks "recalling" ~90% of rounds against 5-8% on the ladder.
  Anything that reacts to enemy channels (stun and cast valuation near enemies, recall-cancel bonuses) is skewed,
  which touches the enemy-within-6 spell rows and the champion-attack reset row. They also share nemesis's
  nearest-enemy-first priority rule, which makes priority races symmetric: locally a third of all hits are on
  double moves (ladder 11-22%) and nemesis gives away as many double moves as it takes. Treat the double-move and
  deaths rows as opponent-dependent; compare nemesis against itself across versions, not against the ladder.
- **Maps.** Gen/central maps have more gem clusters than the ladder pool, so absolute economy numbers differ by map
  set; use the ladder-maps column against the *current pool* references.
- **One-turn reach.** The report gives 2.1% (all hits we take) and 3.5% (hits before our deaths) from beyond one-turn
  reach on a double move, with a definition it did not record. turnreach2.py now uses the attacker's one-turn reach
  for the action it used (melee attack 2, Varg 3, ranged 3, Tavi/Willow/Vesper 4, +2 after a dash; unit spell 4,
  ground spell 5): on the same ladder data that gives 2.6% and 4.8% for PTN Hyperion (2.4% / 3.8% on the report's
  first 600 games).
- Every generalised script reproduces the report's numbers under its default arguments. One ladder game
  (d6d4d6a52a006dab) was first extracted from a local copy, so its meta.json names the teams A and B; the scripts now
  take names from index.json, which credits PTN Hyperion with one more death (2,639 vs 2,638) and Mite/PTN with 3/2
  more chase streaks than the report.

## 1. Spells held while farming (spellhold2.py; REPORT 11.1)

Farming turns (attacking a camp this round or last, live monster within 4) with the damage spell ready, first 300
rounds. walk = share of those turns on which the champion walked (an excludes-walking spell is then illegal);
cast = share that cast the spell.

No enemy within 6 (a champion fight follows within 8 rounds 2-5% of the time; casting is right):

| champion / slot | nem v rival walk / cast (n) | nem ladder maps | procless | Fish | Mite |
|---|---|---|---|---|---|
| Cassi s0 | .03 / .91 (4361) | .04 / .91 | .04 / .94 | .08 / .90 | .05 / .94 |
| Ryth s0 | **.51 / .44** (4177) | **.55 / .43** | .08 / .70 | .13 / .81 | .42 / .57 |
| Stellar s0 | .09 / .66 (6059) | .08 / .68 | .06 / .92 | .04 / .91 | .04 / .76 |
| Stellar s1 | .07 / .72 (5346) | .05 / .68 | .03 / .93 | .05 / .86 | .04 / .73 |
| Tavi s1 | **.30 / .67** (1917) | .32 / .64 | .03 / .86 | .04 / .93 | .06 / .94 |
| Ren s0 (not drafted) | - | - | .08 / .70 | .13 / .83 | .40 / .59 |

Standing still nemesis casts Ryth 89%, Tavi 95%, Cassi 94%, but Stellar only 72% (s0) and 78% (s1)
against 90-98% for procless and Fish standing still: Stellar's loss is not walking but the cast filters (`wake_risk`, value floor).

Enemy within 6 (a fight follows within 8 rounds 48-75% of the time for nemesis):

| champion / slot | nem v rival walk / cast (n) | nem ladder maps | procless | Fish | Mite |
|---|---|---|---|---|---|
| Cassi s0 | .11 / .11 (665) | .11 / .21 | .07 / .92 (121) | .08 / .92 (99) | .07 / .92 |
| Ryth s0 | .23 / .43 (228) | .24 / .46 | .22 / .30 | .34 / .41 | .25 / .74 |
| Stellar s0 | .14 / .13 (570) | .09 / .15 | .12 / .85 | .09 / .80 | .13 / .60 |
| Stellar s1 | .11 / .29 (368) | .08 / .23 | .03 / .91 | .08 / .85 | .03 / .85 |
| Tavi s1 | .13 / .22 (342) | .16 / .26 | (19) | .23 / .14 | .08 / .92 |

All farming turns with a spell ready (spellwaste3.py): nemesis casts 64% (rival 65%), procless 80%, Fish 84%, Mite 72%.

## 2. Attack reset on ready turns (campshare.py; REPORT 11.3)

Turns on which a reset champion acted with the reset ready and attacked (or reset); share that cast the reset.

| | nem v rival | nem all | nem ladder maps | procless | Fish | Mite |
|---|---|---|---|---|---|---|
| camp-attack turns | **.71** (22,796) | .72 | .72 | .88 | .86 | .86 |
| Issac / Ryth / Tavi / Varg on camps | .77 / .65 / .72 / .67 | .77 / .67 / .74 / .69 | .76 / .68 / .77 / .68 | .86 / .91 / .85 / .89 | .89 / .86 / .75 / .84 | .88 / .86 / .62 / .92 |
| champion-attack turns | .82 | .82 | .80 | .90 | .79 | .82 |

## 3. Camp damage sharing in mixed melee+ranged clears (campshare.py; REPORT 10)

Groups cleared by one team with melee and ranged participants. Shares of the camp damage taken (by melee, by the
participant with the highest max health) against the melee share of damage dealt.

| | nem v rival | nem ladder maps | procless | Fish | Mite |
|---|---|---|---|---|---|
| mixed clears | 3,719 | 1,119 | 2,717 | 3,667 | 4,555 |
| camp damage taken by melee | .71 | .71 | .82 | .80 | .89 |
| camp damage dealt by melee | .45 | .47 | .52 | .51 | .53 |
| taken by the max-HP participant | **.44** | .46 | .62 | .51 | .54 |
| participants hit | 2.07 | 2.14 | 1.99 | 2.17 | 1.98 |

## 4. Economy, first 300 rounds (h2h_econ.py; REPORT 13.8)

Per 100 pick-rounds (one pick = one champion; Cassi and Issac count as one). References: current pool.

| | nem v rival (gen) | nem all (gen) | nem ladder maps | procless | Fish | Mite |
|---|---|---|---|---|---|---|
| camp damage dealt | 2,933 | 2,946 | 2,551 | 2,506 | 2,269 | 2,447 |
| of which spells | 1,044 | 1,037 | 881 | 937 | 967 | 896 |
| camp damage taken | 503 | 507 | 587 | 705 | 464 | 520 |
| gems captured | 56.5 | 56.0 | 32.9 | 35.1 | 30.2 | 34.2 |
| from wolf-only groups | 19.2 | 18.9 | 18.8 | 22.8 | 17.7 | 19.9 |
| from elk-only groups | 3.9 | 4.0 | 4.5 | 5.6 | 4.4 | 4.8 |
| from gem-cluster-only groups | 18.8 | 18.5 | 0 | 0 | 0 | 0 |
| gold captured | 142 | 143 | 147 | 156 | 146 | 152 |
| gems tributed | 50.8 | 50.6 | 28.5 | 28.2 | 25.8 | 27.3 |
| champion-rounds carrying gems | 26.3 | 26.0 | 23.8 | 32.1 | 33.2 | 28.4 |
| carried gem-rounds | 1,425 | 1,419 | **1,050** | 1,392 | 1,567 | 1,154 |
| recalls completed | 1.25 | 1.25 | 1.17 | 1.56 | 1.05 | 1.23 |
| deaths (any cause) | 0.12 | 0.13 | 0.16 | 0.13 | 0.11 | 0.16 |
| carried gems lost | 0.91 | 1.19 | 1.15 | 1.80 | 0.71 | 1.76 |

Whole game:

| | nem v rival | nem all | nem ladder maps | procless | Fish | Mite |
|---|---|---|---|---|---|---|
| tributes per game | 17.0 | 17.5 | 18.7 | 18.2 | 14.2 | 18.4 |
| bag at tribute, median / mean | 44 / 54.4 | 44 / 54.9 | 36 / 48.8 | 36 / 46.3 | 46 / 61.7 | 36 / 45.1 |
| games on maps with a Monolith | 84 | 252 | 18 | 24 | 19 | 26 |
| Monolith-group captures / game there | 1.04 | 1.05 | 1.50 | 0.46 | 1.63 | 0.04 |
| Monolith-group gems / game there | 207 | 210 | 300 | 92 | 326 | 8 |
| damage to Monolith groups / game there | 19.5k | 20.4k | 27.9k | 10.0k | 37.5k | 0.8k |

Against rival in the same games nemesis captures and banks ~2-4% more, carries 27% more gem-rounds, takes 53% more
Monolith captures, and loses 24% fewer carried gems.

## 5. Deaths (deathaudit.py; REPORT 2.5)

Deaths to enemy champions. escapable = a guaranteed escape (conservative 8-turn BFS) existed at the round the victim
first saw a future attacker.

| | nem v rival | nem all | nem ladder maps | procless | Fish | Mite |
|---|---|---|---|---|---|---|
| deaths per game | 2.58 | 2.45 | 5.03 | 4.16 | 4.24 | 4.84 |
| escapable at first sighting | .82 | .82 | .76 | .76 | .70 | .80 |
| no escape at sighting | .16 | .16 | .18 | .22 | .21 | .16 |
| never saw the killer | .01 | .01 | .04 | .02 | .08 | .03 |
| last escapable round to death, median | 2 | 3 | 2 | 4 | 2 | 3 |
| mean bag at death | 7.0 | 7.5 | 7.6 | 11.4 | 12.2 | 14.1 |

Current pool: procless 4.72 / .80, Fish 4.19 / .74, Mite 4.38 / .79 (deaths per game / escapable). rival dies 3.26
per game against nemesis (.82 escapable).

## 6. Chase streaks (chase.py; REPORT 3)

>= 3 consecutive own turns approaching the same visible enemy from outside one-turn basic reach. Hit = damage during
the streak or the 3 rounds after.

| | nem v rival | nem ladder maps | procless | Fish | Mite |
|---|---|---|---|---|---|
| streaks per game | 11.0 | 13.9 | 14.3 | 23.3 | 23.2 |
| target kept its distance | .19 | .17 | .30 | .28 | .32 |
| hit, fleeing target | .28 | .24 | .27 | .26 | .18 |
| hit, anchored target | .41 | .40 | .41 | .47 | .36 |
| melee: hit fleeing / anchored | .20 / .34 | .15 / .31 | .30 / .40 | .25 / .41 | .17 / .33 |
| ranged: hit fleeing / anchored | .36 / .54 | .36 / .57 | .21 / .45 | .28 / .55 | .21 / .42 |

## 7. Wards (wards.py, bushhits.py; REPORT 4, 9)

| | nem v rival | nem ladder maps | procless | Fish | Mite |
|---|---|---|---|---|---|
| wards per 100 alive champion-rounds | **8.11** | 8.18 | 1.65 | 1.55 | 2.66 |
| on a bush tile | **.47** | .47 | 1.00 | 1.00 | 1.00 |
| a bush ward replaced by an off-bush ward | **.50** | .57 | 0 | 0 | 0 |
| own hits on bush-standing victims enabled by own ward in the cluster | .51 | .64 | .64 | .74 | .60 |

On the ladder maps every nemesis champion type places 7.6-8.8 wards per 100 rounds, 42-51% on bushes.

## 8. Turn order and double moves (turnreach2.py, freedouble.py; REPORT 1, 2.2)

Slot model: 0 mismatches over 2,860,000 local action events (and 13.8M ladder ones).

| | nem v rival | nem ladder maps | procless | Fish | Mite |
|---|---|---|---|---|---|
| own hits | 17,021 | 7,634 | 30,551 | 32,012 | 33,255 |
| on a double move | .370 | .341 | .113 | .221 | .147 |
| on a mirror double move | .319 | .284 | .094 | .100 | .089 |
| on a manufactured double move | **.051** | .057 | .019 | **.121** | .058 |
| victim dies within 2 rounds: one-turn hits / manufactured | .204 / .289 | .188 / .249 | .099 / .074 | .225 / .233 | .183 / .224 |
| hits taken on enemy double moves | .372 | .344 | .159 | .169 | .136 |
| hits taken from beyond one-turn reach | .094 | .090 | .055 | .058 | .048 |
| same, before a death (within 2 rounds) | .146 | .113 | .089 | .083 | .069 |
| free double move taken (enemy within 5 acted first) | .529 | .533 | .246 | .341 | .181 |
| double move given away (we acted first) | .559 | .496 | .226 | .237 | .351 |

Nearly all beyond-reach hits taken are on double moves (.093 of .094 for nemesis). On the ladder PTN Hyperion
(morgana/rival era) took .512 and gave away .151; locally the same rule meets itself and the advantage cancels.

## Notable

- Ryth walks on half its ready farming turns (51-55%) and Tavi on 30%, against 3-14% for procless and Fish: the
  report's 11.1 loss is still in nemesis (it inherited farm() from morgana via rival), and Tavi now has it too.
  Mite has the same Ryth/Ren habit (40-42%).
- With an enemy within 6, procless, Fish and Mite still cast Cassi (92%) and Stellar (80-91%); nemesis casts them
  11-29% of the time. The report called hold_range defensible; the top teams disagree for their ranged spells.
- Tanking: nemesis's highest-HP participant takes 44% of camp damage (top 51-62%), melee 71% (top 80-89%).
- Wards: 8.1 per 100 rounds, 47% on bushes, and half of the bush wards are replaced by an off-bush one; the top teams
  ward 1.5-2.7 per 100, all on bushes, and never replace a bush ward with an off-bush one.
- Economy on ladder maps is already at procless's level per pick-round (camp damage, gems, tributes), but nemesis
  carries a third less (carried gem-rounds 1,050 vs 1,392-1,567) and recalls less than procless.
- Monolith sieges: on maps with one, nemesis takes 1.0-1.5 Monolith captures per game, close to Fish (1.6) and far above
  procless and Mite.
