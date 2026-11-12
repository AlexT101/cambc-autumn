# v118 against Fish r8: the 147 losses, their causes, and what to change (independent study B, 2026-11-12)

v118 ("Charybdis 520 + psafe-a + emblem lab 6", `bots/baselines/v118`) played 345 live games against Intercontinental
Fish's pinned r8 bot and won 198 (57.4%, Wilson 95% 52-62). 340 of the 345 replays are distinct (5 byte-identical
rematches: 3 wins, 2 losses); the distinct record is 195-145.

This study is replay-first: every loss is classified from its timeline, every count is run over the wins too, and
what the bot decided comes from traced re-runs of the uploaded source that reproduce the live game.

Everything here is uncommitted. Scripts are in this directory; generated data is under `replays/v118b/` (gitignored).

## Short version

1. **Our win condition is one thing: the Prism's hoard reaching the win and being tributed.** A champion of ours held
   a winning bag (our score + its bag at 1,000 or more) in 214 games: we won 193 of them (90%). Of the 131 games where
   that never happened we won 5 (4%).
2. **The losses are that hoard dying or never forming.**

   | class (decisive mechanism, defined in section 2) | losses | share |
   |---|---|---|
   | HOARD-KILL: a 100+ gem bag killed before any winning bag existed (Prism in 45 of 49; Fish's Vesper the killer in 39) | 49 | 33% |
   | FINISH-FAIL: we held the winning bag and did not convert it (carrier killed with it 13, ran out of time 8) | 21 | 14% |
   | FARM-EARLY: out-farmed, 100+ gems of wealth behind by r300 | 25 | 17% |
   | FARM-DEAD: out-farmed, with a third of a champion's game more dead time than Fish | 22 | 15% |
   | FARM-LATE: out-farmed otherwise | 14 | 10% |
   | ATTRITION: many small bags lost, net | 12 | 8% |
   | RACE: we ended with a winning total, unbanked, never in one bag | 2 | 1% |
   | HOARD-CAMP: a 100+ bag lost to a camp | 2 | 1% |

   A 100+ bag lost to a champion happened in 76 of the 147 losses and 9 of the 198 wins: we win 11% (6-19) of the
   games where it happens and 73% of the others.
3. **Why the hoard dies** (trace-verified, section 3.1). Fish r8 funnels its gold into one Vesper (median Strength
   385 and 4,200 max health at r600; 465 and 6,200 when she kills our hoard; Greed emblems in 68% of games). Our Prism
   has a median 2,260 max health at r600. When she attacks the Prism, its death rate follows one physical quantity,
   the basic attacks she needs for its health: 2-9% at 6+ hits, 31-57% at 2-6, 81% under 2. The bot's retreat test
   and stand model look one enemy turn ahead and two walking steps out: on the last turn before the fatal retreat
   they said "stay" in 45 of 57 reproduced cases, with the eventual killer absent from the fight roster in 50. Once
   the retreat starts it is on foot, a median 21 tiles from home, against a dash and range 3: 60 of the 77 big-bag
   Prism deaths end a retreat streak (median 6 rounds).
4. **Why the finish fails** (section 3.2). A winning bag's channel is a turn per 10 gems. Bags under 500 when first
   winning converted 124 of 127 (98%); 500-700 86%; 700+ 73%. Fish answers a long channel with altar locks (120
   cancels of a winning channel in 35 games), stuns (79) and kills.
5. **Why the farm losses happen** (section 3.3). In the 47 FARM-EARLY/-DEAD losses we lose 3.1 champions by r300
   (0.73 in wins), 74% of them in our own half and 58% outnumbered. Over r1-150 we are outnumbered in 24.9% of our
   contact rounds against Fish's 10.8% (paired, +14.1 points, CI 10.8-17.6): Fish moves as a pack, we farm apart.
6. **v118 has no opponent detector.** `opp_detect` exists only in `bots/variants/c520-mx`; it is not in
   `bots/baselines/v118`, `bots/charybdis` or `bots/ocean`. Nothing in v118's play depends on reading Fish as Fish or
   as unknown, so none of the r2 to r8 drop comes from the changed priority encoding.

**Ranked action items** (by estimated gain weighted by the evidence behind it; detail and risks in section 4):

| # | change | losses it touches | estimated upside against Fish r8 | built and checked |
|---|---|---|---|---|
| 1 | The team's finish: no single long channel (allies bank in parallel once the Prism's channel passes ~50 turn ends; answer the cancelling lock) | 21 FINISH-FAIL, 18 of them with 500+ gem bags | +1.5 to +3 points, inferred | only the blunt form (the Prism banks at the cap): `v118fb-cap50` -0.24 ±0.48 locally, `cap35` -3.92 ±0.72 |
| 2 | An out-scaled Prism turns its gold into Health: Health goal of 6 enemy basic hits and a shop trip for it (`shop.cc`). It dies holding a median 255 unspent gold | 62 hoard losses (49 + 13) | +0.5 to +2 points as built, inferred | `v118fb-phs`: -0.21 ±0.50 locally (level); on Fish's recorded inputs the Prism's health at its live death rises in 13 of 37 games. The goal without the trip (`v118fb-php`) changes nothing |
| 3 | Early cohesion: do not farm apart while Fish's pack is unseen or near (first 150-300 rounds) | 47 FARM-EARLY/-DEAD, part of 14 FARM-LATE | +1 to +3 points, inferred | not built; the farm's choice was not traced |
| 4 | Just-in-time banking: the hoard's race paced by the Prism's own collection rate (`race_left_now`) | 8 time-outs + 2 RACE | +0.5 to +1.5 points, inferred | `v118fb-jit`: -0.09 ±0.53 locally (level) |
| 5 | Stop hoarding when out-scaled (`keeps_gems`) | the same 62 | doubtful as built | `v118fb-hk6` -1.11 ±0.63, `hk4` -0.37 ±0.60 locally; on Fish's recorded inputs the bag is still carried at the live death round in 31 of 33 |
| 6 | Kill or zone Fish's Vesper before r300-450 | she died by r300 in 39 games: we won 76% (62-87) against 52% | unknown: correlation | not built |
| D1 | Draft: our own Vesper against Fish (52% with, 66% without; stratified -13 ±11) | 212 games with her | unknown, confounded by map | a lead for the draft lab, not run |

No local A/B can size the hoard items: by the fishr8 README's own fidelity table the stand-in body `fr8-g25` takes
37 gems a game off our Prism with its Vesper against 99 live, so it under-prices exactly the behaviour they target.
The screens (20,480 games each: one fresh ladder-v3 batch, `fr8-g25` and Mt3q bodies) show local cost, not live
benefit. Items 2 and 4 are level locally and can go into one live batch; items 1 and 3 need building first.

**No candidate here is shown to win.** The study finds where the games go and which decisions are behind it; the
fixes are sized from replay counts, screened for local cost, and for items 2 and 5 checked for whether they change
the Prism's state at the round of its live death.

## 1. Data, tools, reproduction

- **Rows:** `replays/pulls/v118-fish-2026-11-12.json`, 345 games, 69 groups. All 345 bundles were on disk by 16:30 UTC.
- **Extract:** `mkmanifest.py` and `mkgroups.py` unzip the bundles into `replays/v118b/ladder/` and a group-folder
  layout with a synthesized `group.json`, so `tools/replay/extract.mjs` names the teams and checks every result
  against the rows (345 of 345 valid). The cache is `replays/v118b/analysis/`.
- **Per-game features:** `feat.py` (wealth, gold and dead-time curves, captures by half, every death with place,
  bag and killer, tributes, locks, both teams' champions). Its wealth-gap identity (farm + fight + camp) has zero
  residual on all 345 games.
- **Standard tools used:** `analyze.py --reports losses,macro,tempo,fights,audits` (`replays/v118b/reports/all/`),
  `triage.py`, the harness.
- **Two maps were missing locally** (05chiseled_brick, 05rocket). They are cut from the replays (the common prefix
  of two games on the map, after the 14-byte header) into `replays/v118b/ws/maps/` only; the release re-runs on them
  are exact, which proves the bytes. `maps/` is untouched.

**The harness for v118.** `versions.py` registers live versions from the scheduler's `gates.jsonl`; v118 is not in
it (its last record is v117). An uncommitted `_baseline_versions()` in `versions.py` (another session's) maps v118
to `bots/baselines/v118/src` with `replays/v118` as its directory. To keep that directory and the shared file
alone, `h.py` runs any harness script with an extra version `v118b` (same source, `replays/v118b`) injected at run
time: `py research/ideas-2026-11-12/v118-fish-b/h.py batch.py --version v118b ...`. `versions.py` is not edited.

**Reproduction.**

| run | what | games exact | rounds reproduced |
|---|---|---|---|
| release re-run | `bots/baselines/v118` `--release` against each puppet | 345 / 345, per-turn fuel identical in every game | 280,275 / 280,275 |
| `d` | + the bot's own `D` line (branch, farm group, claim) in a fuel-paused window | **345 / 345** | **280,275 / 280,275** |
| `v` | + `DX` (state, scores, want_home's reason) and `CS` (stand verdict and roster) | 216 / 345 | 205,234 (73.2%) |
| `g` | + `DX`, `PX` (lethal bound and idle kill time at the end tile), `HG` (reach) | 252 / 345 | 234,802 (83.8%) |

- The release re-runs prove `bots/baselines/v118` is the upload and the puppets replay Fish exactly.
- Every statement below about **which branch the bot took** uses run `d`, which reproduces all games.
- Statements about **why** (retreat reason, stand verdict, lethal bound) use runs `v` and `g` and only the rounds up
  to each game's first difference from the live game (`ladder_trusted_through`); each such count says how many
  events it covers.
- `tools/replay/harness/live_trace_bot.py` stops on v118 (its `chase_trade` line no longer matches), so
  `mktrace.py` ports its lines. Findings on the method:
  - The trace windows are fuel-neutral only if they leave the bot's caches alone. `my_position()`, `my_gems()` and
    `gems_short()` cache per turn; a trace read that refreshes them saves the bot a later host call and the re-run
    leaves the live game's fuel. With memory-only reads plus one direct `sdk_champion` into a local, a second window
    a turn reproduced 30 of 30 games that the accessor form had split 14 / 16. `mktrace.py`'s windows also put
    `self_fresh` and `gems_fresh` back.
  - What still diverges is the mid-turn `CS` line and `want_home`'s notes (`Safety` queries inside the window) and
    the `HG` / `PX` queries: 63% and 73% of games stay exact. Not chased further.

## 2. Every loss classified

`classify.py`. The final wealth gap (tributed + carried gems, them minus us) splits exactly into

- **farm:** their capture gems minus ours;
- **fight:** twice the net bags lost to champions (a kill moves the bag, a double swing), split into **hoard** (our
  bags of 100+ gems) and **small** (the rest, net of what we took);
- **camp:** bags lost to camps.

Tests, in order: FINISH-FAIL (we held a winning bag, `winbag.py`); RACE (we ended with at least their wealth, or
with a winning total in tributes plus bags); else the largest component names the game, with the farm games split
by when and how (the table in the short version). The per-loss table with every component is
`replays/v118b/loss_table.md` (`classify.py --list` prints it).

**Do the classes separate losses from wins?**

| event | wins (198) | losses (147) | win rate when it happens (95% CI) | otherwise |
|---|---|---|---|---|
| held a winning bag at some point | 193 | 21 | 90% (85-93) of 214 | 4% of 131 |
| a 100+ bag lost to a champion | 9 | 76 | 11% (6-19) of 85 | 73% of 260 |
| our Prism lost a 200+ bag (287 Prism games) | 2 | 57 | 3% of 59 | 84% of the 185 where it reached 200 and lost none; 19% of the 43 where it never reached 200 |
| a 100+ bag lost to a camp | 1 | 4 | 20% (4-62) of 5 | 58% |
| ended holding 300+ unbanked gems | 6 | 22 | 21% (10-40) of 28 | 61% |
| Fish's Vesper died by r300 (260 games with her) | 30 | 9 | 76% (62-87) of 39 | 52% (45-59) of 221 |
| our deaths by r300 | 0.8 a game | 3.6 (FARM-EARLY), 3.1 (FARM-DEAD), 1.0 (HOARD-KILL) | | |

The exact decomposition, means: losses gap 697 = farm 234 + fight 452 + camp 10; wins gap -575 = farm -378 + fight
-194 + camp -2. In the 49 HOARD-KILL losses the farm part has a median of 6 gems: we farm level with Fish and lose the bag.

**The 8 round-limit games** (3 wins, 5 losses):

| game | map | result | class | what happened |
|---|---|---|---|---|
| 0c405783-4 | 01boss_battle (1 altar) | 379-947 | FINISH-FAIL (time) | Prism held the winning bag from r895 for 1,106 rounds and ended with 4,086 gems unbanked: 45 starts of the winning channel, 40 left by us, 3 cancelled by locks, 2 by stuns |
| a8ce501d-1 | 05clouds | 136-548 | FINISH-FAIL (time) | winning bag from r644 (1,011 gems), 1,357 rounds held, 15 enemy locks after it, 30 channel starts; 1,438 unbanked |
| a7c6e95f-5 | 02guardians (1 altar) | 107-318 | FINISH-FAIL (died) | winning bag from r1413, held 496 rounds, killed by Vesper at r1909 with 1,475 gems |
| d4f78bbf-1 | 05cassette | 548-953 | HOARD-KILL | Prism killed by Vesper with 251 (r324) and 246 (r894) |
| 0d22b20b-5 | 03one_gem | 24-248 | FARM-DEAD | out-captured by 208 gems |
| 8b86f0e2-5, a7c6e95f-1, b46d3eff-1 | 03one_gem, 03ultrastarvation x2 | wins | | |

**Breakdowns** (`breakdown.py`, full tables in `replays/v118b/breakdown.md`; Wilson 95%):

| cell | games | win % | loss classes |
|---|---|---|---|
| side a / b | 173 / 172 | 58 (51-65) / 56 (49-64) | no side effect |
| 5 / 4 / 3 picks | 220 / 69 / 56 | 57 (51-64) / 57 (45-68) / 59 (46-71) | HOARD-KILL + FINISH-FAIL 52 / 10 / 8 |
| set v1 core / v1 ext / p170 new | 80 / 180 / 85 | 55 (44-65) / 55 (48-62) / 65 (54-74) | |
| our draft with / without Prism | 287 / 58 | 58 (52-63) / 55 (42-67) | without Prism: FARM-DEAD 13, FARM-LATE 6, FARM-EARLY 5 |
| Fish's first pick Vesper / Marcella | 260 / 83 | 56 (50-62) / 64 (53-73) | |
| Fish Vesper x our Prism | 210 | 55 (48-61) | HOARD-KILL 40 and FINISH-FAIL 17 of 95 losses |
| no Fish Vesper x our Prism | 77 | 66 (55-76) | |
| Fish: Vesper/Vendetta/HoR/C&I/Willow | 66 | 55 (43-66) | HOARD-KILL 19 of 30 losses |
| Fish: Vesper/Varg/HoR/C&I/Willow | 62 | 66 (54-77) | |
| Fish: Vesper/HoR/C&I | 46 | 57 (42-70) | |
| Fish: Vesper/Tavi/HoR/C&I/Willow | 28 | 46 (30-64) | |
| ours: Ryth/Vesper/C&I/Prism/Willow | 56 | 52 (39-64) | HOARD-KILL 18 and FINISH-FAIL 6 of 27 losses |
| maps 1 / 2 / 3+ altars | 91 / 134 / 120 | 59 / 56 / 58 | |
| longer map side <=40 / 41-60 / 61-80 / 81+ | 98 / 105 / 58 / 84 | 60 / 53 / 64 / 55 | 81+: HOARD-KILL 22 and FINISH-FAIL 4 of 38 losses |
| game length <500 / 500-799 / 800-1199 / 1200+ | 36 / 168 / 102 / 39 | 89 / 64 / 39 / 46 | |

- Results repeat by cell, not by game: on the 194 (map, side) cells v117 also played against r8, both versions lost
  66, both won 88, v117 alone won 19 and v118 alone 21. 66 of v118's 85 losses there were v117's too.
- 42 maps were lost on every game played (86 games), 67 won on every game (137). With two games a map, single
  cells prove nothing; the classes above are the unit.

## 3. Root causes at trace level

### 3.1 The hoard is killed (HOARD-KILL 49, and 13 of the 21 FINISH-FAIL)

**Replay facts** (`deathctx.py`, `hunts.py`, `retreats.py`, `retreat_rate.py`; all 345 games).

- Our champions died with 100+ gems to a champion 98 times (33,284 gems; 8 times in wins): the Prism 77 times,
  29,334 gems, median bag 280, median round 578.
- Fish's Vesper killed 58 of those 77. She was the only attacker in the fatal run in 44 of her 58 and dealt 93% of
  its damage. Her Strength then: quartiles 340 / 465 / 640; her max health 4,200 / 6,200 / 9,050; the Prism's max
  health 1,675 / 2,293 / 2,861.
- Medians by round, every game:

  | | r200 | r400 | r600 | r800 | r1000 |
  |---|---|---|---|---|---|
  | Fish Vesper Strength | 135 | 220 | 385 | 455 | 480 |
  | Fish Vesper max health | 1,500 | 3,400 | 4,200 | 5,500 | 7,700 |
  | Fish Vesper earned gold | 912 | 1,908 | 2,967 | 3,423 | 4,201 |
  | our Prism max health | 1,285 | 1,675 | 2,260 | 2,585 | 2,845 |
  | our Prism earned gold | 340 | 860 | 1,215 | 1,380 | 1,500 |

- **The death rate is set by hits-to-kill.** 486 episodes of Vesper damage on our Prism (runs with gaps of at most 2
  rounds), wins and losses; 124 end in the Prism's death:

  | Prism health / Vesper Strength at the start | episodes | Prism died |
  |---|---|---|
  | under 2 | 43 | 81% |
  | 2-3 | 35 | 57% |
  | 3-4 | 40 | 35% |
  | 4-5 | 54 | 39% |
  | 5-6 | 54 | 31% |
  | 6-8 | 69 | 9% |
  | 8-12 | 97 | 9% |
  | 12+ | 93 | 2% |

  The bag does not raise it (17% at 400+ gems, 33% with none): the body does.
- What the Prism can itself know (the largest Strength it has seen on a living enemy, `outscaled.py`): median
  hits-to-kill at r400 / r600 / r800 is 18.8 / 15.0 / 18.5 in wins and 12.7 / 8.4 / 6.0 in losses. "Bag of 100+ and
  under 6 hits" first holds in 29 of 166 Prism wins (17%) and 54 of 121 Prism losses; in the 60 hoard losses with a
  Prism death it holds before the bag is lost in 37, a median 47 rounds before (K = 8: 42, median 112 rounds).
- In the episodes with a 100+ bag where the Prism died (62), the team's damage to Vesper during the episode has a
  median of 0; where it survived (246), 717.
- She is not killable late: 6-12k health. In the 04comb example below she has 12,200.

**Trace facts.**

- *Branch (run `d`, exact, all games).* On the turn before the fatal run's first hit the Prism's branch was
  retreat `R` in 47 of the 77 deaths, farm `F` 14, bank `B` 4, tribute `T` 3, stop-ender `E` 3. 60 of the 77 end a
  streak of consecutive retreat turns: median 6 rounds, 39 of 5+, 14 of 10+; the streak began with the killer at a
  median 5 tiles, the Prism at a median 82% health, home a median 21 tiles away.
- *Retreats are common and usually work* (32,598 retreat streaks with an enemy within 6 at their start, 95 a game;
  5.0% end in death). The failures are the close and the out-scaled ones: 17% from distance 1, 7% from 3, 2% from
  5-6; with Vesper nearest, 8.7% under 2 hits, 2.0% at 6-10. So "78% of all our deaths end a retreat" (1,448 of
  1,834) is the base rate of a bot that retreats often, not a broken retreat.
- *Why it did not leave earlier (run `v`, 57 of the 77 deaths in reproduced rounds).* On the last turn before the
  final retreat streak:
  - `want_home` was asked and said stay in 45 (not asked in 7: a channel);
  - the stand test (`stand_lost_at`, `combat/fight.cc`) formed no fight roster in 38 (the eventual killer unseen in
    18, in sight but outside the roster in 20), judged the stand won in 18 (killer not in the roster in 12, in it
    in 6), and saw our fall in 1.
  - So in 50 of 57 the eventual killer was in no fight the model considered.
  - The first retreat turn's reason: recall line or pack zone (`drawn_home`) 30, stand lost 15.
- *What the model saw at the tile it ended on (run `g`, 60 of the 77).* On the turn before the first hit:
  `Safety::lethal` said not lethal in 49 and lethal in 11; `turns_to_kill_idle` said 1-3 idle turns in 30 and never
  in 15; the killer's modelled strike reached the tile in 32.

**The decision responsible.** The Prism's safety is judged one enemy turn set ahead (`lethal`: worst damage before
our next turn) and, for the stand, over enemies who hit the tile now or walk in within `params::pursuit_steps = 2`.
A fed Vesper needs 4-5 basic attacks for the Prism, which is two to three rounds, she closes with a dash every 8
rounds while both walk one tile a turn, and she starts from outside that horizon. Nothing in `keeps_gems`
(`economy/bank.cc`: `gem_focus && !winning_bag && !closing`), in the shop (the Prism's shards are Health only until
1,200 max health, `economy/shop.cc`) or in the retreat test asks whether an enemy that out-damages and out-paces us
exists. The hoard is kept, and walked around the map, on a body that one enemy can take in a few rounds from 20
tiles of walking away from home. And the body lags its own gold: the Prism buys only on spawn, a hoarding Prism
seldom goes home (`wants_shop` prices the trip by the stat gain and the heal, not by the bag riding on the body), and it dies holding a median 255 unspent
gold (150+ in 39 of 58 hoard deaths), 8 Health shards.

**Named games.**

- **fb2e2eae-4, 04comb (1 altar), side a, lost 307-1019.** We lead by 481 wealth at r500. At r560 the Prism (585
  gems, 1,415 max health) starts its tribute and leaves it; Fish's Vesper (Strength 640, 796 a hit on a champion, 12,200 max health) locks
  the altar at r570 and tributes 301 beside it (r570-591). The Prism's branches r586-599: `R B R B R R R R R R R R R
  R`. It casts at her and stuns her at r591-592, then walks away one tile a turn for six rounds while she follows
  at distance 5 without a dash. At r599, acting first, it casts at her again (the spell excludes walking); she
  dashes and hits for 796, acts first in r600 and hits again: dead with 585 gems from 96% health, no turn in
  between. Trace: `R` with reason 6 (stand lost, 17 turns to our death / never theirs) from r586; the stand was
  known lost, the walk could not get out.
- **caad0bb7-3, 04pinwheel, side a, lost 14-1362.** Prism (556 gems, 2,065 health) farms with Heart of Ruin in
  sight; `CS` at r557: stand won, we never fall, they die in 8 turns. Heart of Ruin dash-stuns it at r560, Vesper
  (not in the roster) arrives: 520 at r561, then 520 + 476 acting first in r562. Dead two rounds after a "won"
  verdict.
- **86326bb9-2, 05slant, side b, lost 237-1015.** `R6 B R6 B R6 B R1 R6 R1 ...` for 15 rounds with a 759-gem bag
  at 20% health: retreat and bank alternate, the bag never reaches an altar; killed by Vesper at r700 at the break.

### 3.2 The winning bag is not converted (FINISH-FAIL 21)

**Replay facts** (`winbag.py`, `channels.py`, `cancels.py`).

- Conversion by the bag's size when it first wins:

  | bag when first winning | games | converted | rounds to the win (median, wins) |
  |---|---|---|---|
  | under 100 | 80 | 96% (90-99) | 9 |
  | 100-300 | 26 | 100% | 13 |
  | 300-500 | 21 | 100% | 35 |
  | 500-700 | 42 | 86% (72-93) | 52 |
  | 700+ | 45 | 73% (59-84) | 89 |

  18 of the 21 failures are bags of 500+. Later is worse too: first winning before r600 converts 95%, after r800 81%.
- We started a winning-bag channel of 100+ gems 552 times in 82 games and completed 64. The others ended: left by
  us 283, cancelled by an enemy lock placed on the altar 115, by a stun 78, by death 2, open at the end 10.
  Counting winning channels of any size, locks cancelled 120 in 35 games and stuns 79.
- The 21 failures: the carrier died with the bag in 13 (Vesper 10, a Monolith camp 2, Fish's Prism 1) (the 21
  held it a median 47 rounds); 8 ran out of time: 2 at the round limit after more than a thousand rounds of
  restarts, 6 as Fish finished first (3 of those 6 are the small-bag cases: a score of 964-995 and a last bag of
  8-41 gems).
- Our own cancels are mostly justified: of the 80 in losses, the carrier would have survived the turns left in 14
  (4 games) even if the enemy had acted the same; it died in that window 20 times anyway.
- Lock cancels: the locker was Vesper 30, Issac 21, Heart of Ruin 20, Cassi 13, Marcella 11; we had hit it in the
  10 rounds before in 109 of 120; the channel had a median 41 turns left.

**Trace facts (run `d`, exact).** The Prism's branches while it holds the winning bag are runs of `T` broken by
`R`, `B`, `W`: 5fe50000-4 (02gift_wrapping, 4 altars), r560-775, `T x36, R x4, B x7, W, T, T, R, T x27, B x6, T
x4, B x7, T x32, R/B x38, T x49`: three lock cancels (one with 7 turns left, r537) and four restarts at the same
altar, 922 gems unbanked when Fish reaches 1,001. d5d4297f-4 (04gap, 100x90): `F` until r892, `B` from r893 (the
round the team's score and bags reach 1,000), 42 rounds of walking, and the 52-turn channel not started when Fish
wins at r979 with our 607 gems unbanked and a wealth lead of 185.

**The decision responsible.** `keeps_gems` holds every gem on one body until `winning_bag`, so the win arrives as
one channel of bag / 10 turn ends (two thirds of that with the Tribute emblem), and the carry macro (`farm.cc` 'G',
'L', 'Q'; `leave_for_prism`) keeps adding to it. `race_left_now` (`bank.cc`) paces the race by `World::ally_rate`,
the tribute rate over the later half of the game, which reads near zero for a hoarding team, so `closing` fires
only when the score and bags already hold the win; the walk and the channel then come on top.

### 3.3 Out-farmed (FARM-EARLY 25, FARM-DEAD 22, FARM-LATE 14)

**Replay facts.**

- Early deaths decide these games. Deaths of ours to champions by r300: 3.6 (FARM-EARLY) and 3.1 (FARM-DEAD) a
  game against Fish's 0.9 and 1.6; in wins 0.8 against 1.8. 146 such deaths in the 47 games: 74% in our own half,
  58% outnumbered within 8, 62% with a stun in the fatal run; Fish's killers are spread (Cassi 24, Vesper 24, Heart
  of Ruin 23, Issac 20).
- Wealth at r300: 106 against 350 (FARM-EARLY), 152 against 108 (FARM-DEAD: level until the deaths), 447 against
  255 in wins. Fish earns more gold early in every class, wins included (r150: 791 against our 678 in wins).
- Cohesion over r1-150, paired by game (`analyze.py --reports macro`): our field champions have no ally within 8
  in 15.8% of rounds against Fish's 8.7% (+7.1 points, CI 6.0-8.2); in contact we are outnumbered 24.9% against
  10.8% (+14.1, CI 10.8-17.6). We win 71% of the 78 games where our outnumbered share is the lower one and 52% of
  the 200 where it is the higher.
- Fights at equal numbers swing 3.8 gems a fight Fish's way; with one more champion we break even (-0.4), Fish
  gains 3.5.
- Where Fish's gems come from in these losses: 393 of its 1,058 capture gems from the middle and 252 from our half
  in FARM-EARLY (wins: 66 and 56 of 670).
- 13 of the 22 FARM-DEAD and 6 of the 14 FARM-LATE losses are games without our Prism (58 such games, 55%).

**Trace facts (run `d`, exact).** The branch on the turn before the fatal run of these 146 early deaths: retreat
53%, farm 34%, chase 5%, hold 3%; the same mix as early deaths in wins (47 / 38 / 4 / 3). The bot does the same
thing in both; in the losses Fish's pack meets it more often and in larger numbers.

**Root cause, as far as this study reaches.** The farm (`economy/farm.cc`, crews by group value) spreads our
champions over the groups; Fish's five move together and take our half or the shared middle one group at a time.
No trace was taken of the farm's choice at these moments (the `CS`/`DX` runs cover the retreat, not the pick), so
the code-level cause is **inferred** from positions, not shown from the decision.

### 3.4 The rest

- **ATTRITION (12):** small bags; 6 of the 12 are within 125 gems of level at the end. No common mechanism found.
- **HOARD-CAMP (2, and 2 of the FINISH-FAIL):** the Prism killed by a Monolith group with 407-974 gems (5fa3b150-2,
  ad01a0b7-5, 1af8e2c8-4, f3e6611d-4). Four games; not studied further.
- **RACE (2):** 1493263b-4 and 02f5a5c6-4, lost 964-1001 and 957-1001 with the winning total split over bags.

## 4. Action items

Play-level items first, ranked by expected win-rate gain against Fish r8 over confidence. "Touches" counts games in
this set. Upside ranges are my estimates; where they rest on a correlation the text says so.

### 1. Finish without one long channel

- **Mechanic.** A tribute channel is one turn end per 10 gems; a lock placed on the altar cancels it whole (10 gold),
  a stun cancels it, and the carrier stands still for all of it. Five champions channel in parallel; one Prism
  channels alone.
- **Evidence.** Winning bags under 500 convert 98%, 500-700 86%, 700+ 73%; 120 lock cancels and 79 stun cancels of
  winning channels; 21 losses with the win in one bag.
- **Change, in order of how well-defined it is.**
  1. Once the Prism's own channel would pass a limit (the measured break is about 50 turn ends), allies stop
     handing it captures (`leave_for_prism`, the 'G' / 'L' / 'Q' carry picks in `farm.cc`, `yield_capture` in
     `capture.cc`) and bank their own gems: the score rises in parallel and the Prism's winning bag stays short.
  2. After a lock cancels a winning channel, the nearest allies break that lock or take the Prism's channel to an
     altar no enemy is within 2 of (`altar_guard.cc`, `bank.cc` `submit_here`); today the Prism restarts the same
     channel at the same altar (5fe50000-4: four times).
- **Touches.** 21 FINISH-FAIL losses (18 with 500+ bags) and the long conversions among the wins.
- **Upside.** If 500+ bags converted like 300-500 ones: up to 18 games; half of that is **+1.5 to +3 points**.
  Inferred.
- **Risk.** A smaller hoard is less Focus in the last third of the game; the local programme found every blunt cap
  costly ("cap at 150: 46.7%").
- **Local screen.** Only the blunt form was cheap to build: the Prism itself stops keeping gems when its channel
  passes the limit. At 50 turn ends (`v118fb-cap50`) 49.76% (-0.24 ±0.48): level within the screen's noise. At 35
  (`v118fb-cap35`) 46.08% (-3.92 ±0.72): a clear loss, so the limit cannot go much under the measured break. The
  parallel-banking form (1) is not built.

### 2. An out-scaled Prism turns its gold into Health

- **Mechanic.** A hoard is safe only on a body the enemy cannot take between two of our turns. With back-to-back
  turns (the rules' alternation lets a champion act last in one round and first in the next), an attack reset and
  a stun on us, an attack-reset carry lands 4 to 6 basic attacks before we act twice. Measured: the Prism's death
  rate under Vesper's attack is 2-9% at 6+ hits and 31-81% below. The Prism's Focus comes from carried gems (1.5 a
  gem), so its gold is free for Health: a 150-gold Bruiser Focus emblem, which it buys 1.8 times a game, is worth
  27 carried gems. Items are bought only on our spawn or while dead.
- **Evidence** (the 58 hoard losses with a Prism death; replay).
  - The Prism dies holding a median **255 unspent gold** (quartiles 116 / 255 / 558; 150+ in 39 of 58, 300+ in 28):
    8 Health shards, +550 health, about one more hit from a 465-Strength Vesper. Its median max health at those
    deaths is 2,293 against 6 x 465 = 2,790.
  - On its own sightings the 6-hit condition held before the death in 37 of the 58, a median 50 rounds before; in
    23 of those 37 it bought nothing between then and its death.
- **Change.** `economy/shop.cc`, two parts.
  1. The Health-first branch for `Passive::gem_focus`: the goal is `max(sturdiest_base_health, 6 x the largest
     Strength seen on a living enemy)` in place of 1,200 (`v118fb-php`).
  2. `wants_shop`: an out-scaled Prism whose gold buys a whole further enemy hit of Health takes the trip whatever
     the stat gain prices it at (`v118fb-phs` = 1 + 2).
  A follow-up worth pricing: Greed in Health for the Prism when out-scaled (40 shards' Health for 750 gold: 3.47
  health a gold against 2.17 for a five-shard emblem); Fish's Vesper buys 1.3 Greed-Strength and 1.1 Greed-Health a
  game, our Prism none.
- **Does it act? Re-runs on Fish's recorded inputs** (`cf_state.py`; the masked v118 source plus the change against
  each hoard loss's puppet; only the Prism's own state is read, since Fish's side stops reacting once the game
  leaves the live one).
  - Part 1 alone: at the round of the live death the Prism's max health is the same in 38 of 43 games, median 2,390
    against 2,390, unspent gold 325 against 326. **The goal alone does nothing**: the gold is not being spent.
  - Parts 1 + 2: max health raised by 300+ in 13 of 37, the same in 19; games with 6+ hits for the live killer's
    Strength 10 -> 16 of 37; unspent gold median 325 -> 151.
- **Touches.** The 62 hoard losses.
- **Upside as built.** It moves about one hoard death in six into the 6+ hit band, where the episode death rate is a
  quarter of what it is below: about 5 of the 62 hoard deaths avoided, of which 35 in 62 end ahead on wealth without
  the bag transfer: 2 to 4 games, **+0.5 to +2 points**. Inferred. A form that shops sooner (the trip at any
  out-scaled 150 gold, Greed-Health) would reach more of the 39 deaths with 150+ gold unspent.
- **Risk.** Shop trips cost farm rounds; less Focus and fewer passives late. Against opponents without a fed carry
  it rarely acts.
- **Local screens.** `v118fb-php` 50.03% (+0.03 ±0.33), 292 games differ; at 8 hits (`v118fb-php8`) 50.02% (+0.02
  ±0.36). `v118fb-phs` 49.80% (-0.21 ±0.50; Fish body +0.29, Mite body -0.70), 707 games differ: level within one
  batch's noise, not a shown gain.

### 3. Early cohesion against a pack

- **Mechanic.** Fights go to numbers and to the first hit (the side with more champions present won 59%, the
  initiator 71%, over 2,400+ fights here). Fish's five arrive together.
- **Evidence.** Section 3.3: outnumbered in contact 24.9% against 10.8% over r1-150; 3.1-3.6 early deaths in the 47
  FARM-EARLY/-DEAD losses.
- **Change.** In `economy/farm.cc`'s crew pick and `combat/guard.cc`'s work guard, while the enemy pack is unseen
  or within reach of a group, price a group by the allies who can reach it before the pack can. No candidate built:
  the farm's choice at these moments was not traced, so the change is not yet tied to a branch.
- **Touches.** 47 losses, plus the 19 Prism-less FARM-DEAD / FARM-LATE ones.
- **Upside.** **+1 to +3 points**, inferred; the earlier "group up early" candidate (LOSSES.md 6) and the
  follow / presence arms in EXPERIMENTS were level locally, so this needs the pack to be modelled by the body
  first.
- **Test.** `fgate` against `fr8-g25` reads it only if the body packs like Fish; check its r1-150 isolation
  against 8.7% before trusting a read.

### 4. Just-in-time banking of the hoard

- **Mechanic.** The hoard scores nothing until a channel of bag / 10 turns after a walk; a race is won by the
  round the channel ends, not the round the gems are collected.
- **Change.** `economy/bank.cc` `race_left_now`: for a Prism, the pace is the larger of the team's tribute rate
  and the Prism's own collection rate (`gem_income_rate()`), so `closing` sends the bag to the altar while the rest
  of the win is still coming in.
- **Touches.** The 8 FINISH-FAIL time-outs and 2 RACE losses (d5d4297f-4 is the clean case: 42 rounds of walk and
  a 52-turn channel started 86 rounds before Fish's win).
- **Upside.** 2 to 5 games, **+0.5 to +1.5 points**, and shorter wins.
- **Risk.** A little Focus at the end.
- **Local screen.** `v118fb-jit`: 49.91% (-0.09 ±0.53), 818 games differ: level. An earlier enemy-clock cap on
  every bag (2026-10-24, 1,104 games) was level too; this is a different lever (our pace, Prism only).

### 5. Stop hoarding when out-scaled (not recommended as built)

- **Mechanic and signal** as item 2. `economy/bank.cc`: `keeps_gems` also requires that no living enemy, at the
  Strength last seen, needs fewer than 6 basic attacks for our max health; the Prism then banks like any carrier
  (the EOQ floor). Built as `v118fb-hk6` and `v118fb-hk4`.
- **Why it ranks low.**
  - The signal comes late. On the Prism's own sightings it holds before the death in 37 of the 58 hoard deaths, a
    median 50 rounds before, and a 300-gem bag needs 30 turn ends plus the walk.
  - Re-run on Fish's recorded inputs (`cf_state.py --run hk6`, the Prism's state only): at the round of the live
    death the Prism still carries 100+ gems in 31 of the 33 games still running (median bag 316 live, 362 in the
    re-run).
  - It loses locally: `hk6` 48.89% (-1.11 ±0.63), `hk4` 49.63% (-0.37 ±0.60) on 20,480 fresh games each.
- **What would be needed.** An earlier signal (at 8 hits it holds a median 112 rounds before the bag is lost in 42 of
  the 60, but also in 30% of the wins), or a positional answer (keep the hoard outside the out-scaling enemy's
  two-turn reach of 6-7 tiles and walk home at first sight), which was not built.

### 6. Set Fish's Vesper back early

- **Evidence.** In the 260 games with her, she died by r300 in 39: we won 76% (62-87) against 52% (45-59); by r450
  in 57: 75% against 50%. We win 72% of the quarter of games where she has under 1,013 gold at r300 and 43% of the
  quarter above 1,949. She makes 60% of our deaths to champions in those games (762 of 1,280), has 5.4 kills and
  0.5 deaths a game in our losses and 1.0 / 1.0 in our wins.
- **Caveat.** Correlation: a side winning early fights kills her and wins anyway. No decision of ours was traced to
  it.
- **Change to consider.** The kill worth (`combat/fight.cc` prey / chase) counts the victim's share of its team's
  gold income, so the carry is the preferred kill while she is still 1,000-2,500 health (before r300-400).
- **Upside.** Unknown. A candidate would be cheap; the local body's Vesper earns less (475 gold at r100 against 569
  live), so a local read under-states it.

### Draft-level (kept apart)

- **D1. Our own Vesper against Fish.** With her 110 of 212 (52%, 45-59); without 88 of 133 (66%, 58-74); stratified
  by pick count and Fish-has-Vesper, -13 points (about ±11). In Prism games against Fish's Vesper the hoard is lost
  in 31% with our Vesper and 18% without. Confounded: the draft is a function of the map.
- **D2.** Ren +23 stratified on 38 games, Marcella +11 on 65, Ryth -9 on 114: all inside the noise of cells this
  small.
- **D3.** Our Prism against Fish's Vesper wins 55% (210 games); without Prism against her 60% (50 games). The
  Prism is still right on these numbers: the hoard is also how we win.
- None of these is a recommendation to change the draft tables by hand: they are leads for the draft lab's next
  fit, which should include an r8-like body.

## 5. Local screens run

All: `tools/fgate.py CAND variants/lab-emb6-c520-ps --pool v3 --first-batch 16 --max-batches 1 --ci 0 --fish-body
fr8-g25`, release builds, fast runner, own drafts both sides, real 100k fuel, 2,560 fresh ladder-v3 maps x 2 sides
x 2 bodies = 10,240 games a bot (20,480 with REF's cached half), plus the 128 ladder maps as a side read. REF is the
unmasked v118. One batch is a screen (±0.6 points), not a ship read; nothing here is called shippable.

| candidate | change | fresh win % (95% CI) | Fish body | Mite body | games that differ |
|---|---|---|---|---|---|
| `v118fb-php` | Prism Health goal 6 x top enemy Strength | 50.03 (49.70-50.36) | +0.06 | +0.00 | 292 |
| `v118fb-php8` | the same at 8 | 50.02 (49.66-50.38) | +0.08 | -0.04 | 370 |
| `v118fb-phs` | php + the shop trip for it | 49.80 (49.30-50.29) | +0.29 | -0.70 | 707 |
| `v118fb-jit` | hoard race paced by the Prism's collection | 49.91 (49.38-50.45) | -0.02 | -0.16 | 818 |
| `v118fb-hk4` | no hoard under 4 hits | 49.63 (49.03-50.23) | -0.35 | -0.39 | 1,035 |
| `v118fb-hk6` | no hoard under 6 hits | 48.89 (48.26-49.51) | -1.09 | -1.13 | 1,167 |
| `v118fb-cap50` | no hoard past a 50-turn channel | 49.76 (49.28-50.23) | -0.33 | -0.16 | 615 |
| `v118fb-cap35` | no hoard past a 35-turn channel | 46.08 (45.36-46.80) | -4.67 | -3.16 | 1,347 |

Batch 16 is the batch another session's gate had just played for the same REF, so REF's half came from the cache;
it is a first look for each candidate here, not a held-out confirmation.

**State checks on Fish's recorded inputs** (`cf_state.py`, `cf_php.py`). The masked v118 source plus a candidate's
edit, played against the puppets of the 70 HOARD-KILL and FINISH-FAIL losses (`runs/php`, `runs/phs`, `runs/hk6`).
These re-runs are the live game until the changed bot first acts differently; after that Fish's side replays its
inputs without reacting, so only the Prism's own state at the round of its live death is read (health, unspent gold,
bag), never the fight's outcome.

| change | games still running at the live death round | Prism max health then, live -> re-run (median) | 6+ hits for the live killer | unspent gold | bag |
|---|---|---|---|---|---|
| php (Health goal) | 43 | 2,390 -> 2,390; the same in 38 | 10 -> 10 | 325 -> 326 | |
| phs (goal + shop trip) | 37 | 2,325 -> 2,390; raised by 300+ in 13, the same in 19 | 10 -> 16 | 325 -> 151 | |
| hk6 (no hoard under 6 hits) | 33 | | | | 316 -> 362; still 100+ in 31 |

Logs: `replays/v118b/logs/fgate-*.log`. The candidates are copies of `variants/lab-emb6-c520-ps` (gitignored);
their diffs are the few lines quoted in section 4 (`diff -r bots/variants/lab-emb6-c520-ps bots/variants/v118fb-NAME`).

## 6. Verified, inferred, not found

**Verified**

| finding | by |
|---|---|
| `bots/baselines/v118` is the upload; puppets replay Fish | 345 / 345 release re-runs exact, fuel identical |
| every class count, every wins-versus-losses table, hits-to-kill, conversion by bag size, cohesion | replay counts over all 345 games |
| the Prism's branch before its deaths; retreat streaks; turn budget | run `d`, 345 / 345 games exact |
| the retreat test said stay and the killer was in no roster (50 of 57) | run `v`, reproduced rounds only (57 of 77 deaths) |
| the lethal bound and reach at the end tile (49 of 60 not lethal) | run `g`, reproduced rounds only (60 of 77) |
| v118 has no opponent detector | source: no `opp_detect` in `bots/baselines/v118/src`, `bots/charybdis`, `bots/ocean` |
| local cost of the candidates | fgate screens, one batch each (a screen) |
| the Health goal alone leaves the Prism's health unchanged at its live deaths (38 of 43); with the shop trip it rises in 13 of 37 | re-runs of the changed source on Fish's recorded inputs (`runs/php`, `runs/phs`), the Prism's own state only |
| the Prism dies holding a median 255 unspent gold | replay, 58 hoard deaths |
| with the no-hoard change the bag is still carried at the live death round (31 of 33) | re-run on Fish's recorded inputs (`runs/hk6`), the Prism's own state only |

**Inferred**

- Every upside range in section 4.
- That more Prism health would lower the death rate as the hits-to-kill table reads (correlation plus arithmetic).
- That the re-runs' state changes carry over to live play (after the first different action the puppet does not react).
- That the farm losses come from the farm's spread (positions, not a traced decision).
- That Vesper's early death causes wins.

**Looked for, not found**

- A side effect (58% / 56%), a pick-count effect (57 / 57 / 59), an altar-count effect (59 / 56 / 58).
- Fuel as a cause: not studied here; the release fuel is identical to live, and LOSSES.md's "not a cause" was not
  retested.
- A broken retreat: retreat streaks fail 5.0% of the time; the deaths are the close and out-scaled tail.
- Wasted winning channels through our own cancels: survivable in 14 of 80 in losses (4 games).
- Turn share lost to retreating: 4.5% of our turns in wins, 8.8% in losses; dead time is the larger difference
  (5.2% against 14.8%).
- Marcella's nuke as a main killer (LOSSES.md 2, v78): she makes 7% of our deaths now; Vesper makes 41% (60% in
  the games she plays).

**Against earlier analyses**

- *fishr8 README, "opp_detect read r8 as unknown":* true of the detector, irrelevant to v118, which has none. The
  share of the r2 to r8 drop it explains for v118 is zero.
- *fishr8 README, Vesper's numbers:* its "Strength 460 and 6.7k health at r600" matches our losses (458 and 6,699);
  over all games with her the means are lower (339 and 4,549 in our wins). "Greed in 72%, median r454": 68% and
  r490-504 here. "62% of our deaths": 60% in her games, 41% over all 345. "Over 800 rounds we win 34-38%": 41% (58
  of 141).
- *fishr8 README section 4, "no counter built; every form of banking or caution lost locally":* confirmed for
  banking (`hk6` -1.11), but two forms are level locally (`php`, `jit`), and the README's own point that the body
  cannot price the fed Vesper applies in both directions: a local loss does not show a live loss.
- *EXPERIMENTS "Keeping a hoarding Prism alive" (11-11): "it dies fighting, not fleeing".* Against r8 it dies
  fleeing: 60 of 77 on a retreat streak, and in the fatal episodes the team's damage to Vesper has a median of 0.
- *EXPERIMENTS "Prism's bag" (11-10): "rarely a one-shot".* Still true: 10 of 77 die from 80%+ health with no turn
  of their own; 45 of 77 have two or more own turns inside the fatal run.
- *LOSSES.md 5, the lock war:* present in a new form. Fish cancels our winning channel with a lock 120 times in 35
  games.
- *Astraeus "bag deadline at the enemy's win" (10-24):* level then on 1,104 games; the RACE and time-out games here
  are not that case (we hold the winning total), which is why item 4 changes our pace, not the enemy's clock.

**The rules file.** Nothing in these replays or re-runs contradicts `cambc-rules.yaml`. Seen and consistent: lock
placement cancels channels at the altar; back-to-back turns across a round boundary; damage does not interrupt a
tribute.

## 7. Files

Scripts (this directory):

| file | what |
|---|---|
| `mkmanifest.py`, `mkgroups.py` | harness manifest and group-folder layout from the rows file |
| `h.py`, `run_harness.sh` | the harness with version `v118b` injected; the chain |
| `mktrace.py` | the trace bots (`--lines d`, `d,dx,cs,tw`, `d,dx,hg,px`) |
| `dlib.py` | trace loaders |
| `feat.py`, `classify.py`, `breakdown.py`, `tl.py`, `ep.py` | features, classes, tables, one game's timeline, a turn-level window with trace lines |
| `deathctx.py`, `hunts.py`, `outscaled.py`, `retreats.py`, `retreat_rate.py` | hoard deaths, Vesper-on-Prism episodes, the out-scaled signal, retreat streaks |
| `winbag.py`, `channels.py`, `cancels.py` | winning bags, long channels, cancels |
| `cf_state.py`, `cf_php.py` | the Prism's state at its live death round in re-runs of a changed bot on Fish's recorded inputs |
| `verdicts.py`, `lethal.py` | the retreat reason, stand verdict and lethal bound before hoard deaths |

Data (`replays/v118b/`): `analysis/` (extract), `feat.json`, `classes.json`, `loss_table.md`, `breakdown.md`,
`deathctx.json`, `hunts.json`, `outscaled.json`, `retreats.json`, `retreat_rate.json`, `winbag.json`,
`channels.json`, `cancels.json`, `reports/all/`, `runs/batch` (release re-runs), `runs/d`, `runs/v`, `runs/g`
(traces), `runs/php`, `runs/phs`, `runs/hk6` and `cf-*` (the state checks), `trace-bot-d`, `tb-v`, `tb-g` (the trace bots' sources), `tb-php`, `tb-phs`, `tb-hk6` (the state-check bots), `ws/`
(the harness workspace, 2.7 GB of puppets), `logs/`. The trace-method experiments (the single-line variants) were
deleted; `mktrace.py --lines ...` rebuilds any of them.

Candidates: `bots/variants/v118fb-{php,php8,phs,jit,hk4,hk6,cap50,cap35}` (copies of `variants/lab-emb6-c520-ps`).

Not done: `research/EXPERIMENTS.md` is not updated (the screens are recorded here only); no commit, push or upload.
