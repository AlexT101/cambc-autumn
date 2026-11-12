# v118 against Fish r8: why we lose, from 345 live games and their traces (2026-11-12)

v118 ("Charybdis 520 + psafe-a + emblem lab 6", frozen at `bots/baselines/v118`) played 345 games against the pinned
Intercontinental Fish r8 bot and won 198 (57.4%). Five cells were played twice with identical games, so the distinct
sample is 340 games, 195 won. This note says how the 147 losses happened, what our bot decided before them (from
re-runs of the real code that reproduce the live games), which fixes were tested here, and what is left to try.

Every number is from `replays/pulls/v118-fish-2026-11-12.json`, the bundles it lists and the scripts in this folder.
"Verified" names the evidence: **replay** (counted from the live replays), **trace** (our decision as logged by a
re-run that matches the live game), **A/B** (fgate, 20k+ games), **fork** (live positions played on against the r8
body). "Inferred" is said where it applies.

## 1. Summary

1. **Half of the losses are one event: a hoard is killed.** In 77 of 147 losses (52%, CI 44-60) we lost a bag of 100
   or more gems to an enemy champion; that happened in 10 of 198 wins. We win 11% of the games where it happens
   (10 of 87) and 73% of the others. The bag is Prism's in 66 of the 77, the killer is Fish's Vesper in 57, the median
   bag is 280 gems at round 604, and in 43 of the 77 we led in wealth (tributed plus carried) just before it.
   Verified: replay.
2. **Prism dies retreating, from an enemy it had watched for a median of 28 rounds.** In 55 of 68 traced hoard deaths
   Prism was in a run of `want_home` turns (median 6 turns) that began with the killer mostly 3-6 tiles away. Before
   that it went on working. The retreat's recall was refused on 549 of 551 such turns. Verified: trace.
3. **Seven fixes for it were tested here and all lose.** Keeping the retreat recall (-1.7 to -3.6 points), fleeing
   earlier (-2.3 to -3.5), banking once hunted (-10 to -15), capping the hoard at 350 or 500 gems (-2.8 to -8.6),
   each on 20k-41k fresh games and again from the live positions themselves (section 5). The hoard is our win engine
   against the bodies at every size, so no caution of this kind passes a local gate; the bodies kill a hoard far less
   often than Fish does. Verified: A/B and fork.
4. **Fish's edge is its gold funnel.** Fish's Vesper holds 72% of Fish's gold at round 100 (her passive adds 33% to
   it), two to three times our richest champion's, in our wins too. At round 600 she has 393 Strength and 5,553 health on
   average (466 and 6,782 in our losses; 699 and 12,549 at their end) against Prism's 2,200-2,400 health.
   Verified: replay.
5. The other losses: 35 overrun (24%: 10+ deaths or under 300 gems captured, deaths starting at round 94 on our own
   half against four enemies), 16 out-raced with a hoard still in the bag (11%), 16 out-farmed with few deaths
   (11%), 3 hoards lost to a camp (2%).

Ranked action items are in section 6. In short: nothing found here is a cheap play-level fix for the main loss
channel, and several plausible ones are now ruled out with numbers. The two changes worth building are a camp-fire
margin for bag carriers (small, well-defined, tested level, 3-4 thrown games in 345) and a test bed that contains the
mechanism (the live-fork run added here, and a Fish body judged on hoard kills); the strategic lever is the gold
funnel, which is a design change, not a patch.

## 2. Data and reproduction

| step | result |
|---|---|
| bundles | 345 of 345 on disk; `manifest.py` builds the harness manifest from the pulled rows (the scrim log held 85) |
| maps | `05chiseled_brick` and `05rocket` are not under `maps/`; cut out of our replays into `replays/v118/ws/maps/` (the cut rule reproduces 118 of 118 known maps byte for byte, and the re-runs below are exact on these four games) |
| source | `tools/replay/harness/versions.py` now also registers a live upload frozen in `bots/baselines/v<N>` (v118 is not in gates.jsonl yet); the scheduler's build workspace `lab-emb6-c520-ps-1794478617` has the same source |
| release re-runs against the puppet | **345 of 345 exact**: every input, every round hash, the result, and our fuel on every turn |
| traced re-runs, `tracebot.py` (lines D, TT, EB, WH, CR, CX) | 345 run, **287 exact**, 252,019 of 280,275 rounds trusted (89.9%) |
| traced re-runs with the stand and chase verdicts too (ST, CT) | 245 exact, 229,190 rounds trusted (81.8%) |

Every trace statistic below uses a game only through the round before its first difference from the live game.

**Harness finding.** `live_trace_bot.py`'s CS and CC lines (`cal_stand`, `cal_chase`) change v118's play: with them
3 of 6 test games left the live game (the first at round 42, a different farm claim with 86k fuel left), with only
the D line 6 of 6 were exact, and with its lines some turns' fuel is off by 31-36. `tracebot.py` drops CS, CC and HG and
prints the verdicts from values the bot already holds; those ST and CT sites still cost about 11 fuel a call beyond
any refund (1 of 6 test games diverged), so they run as a second pass. `live_trace_bot.py` also fails on v118 as it
stands (the chase_trade call site changed).

## 3. Taxonomy of the 147 losses

`taxonomy.py`. One class a game, first match, evaluated on our side of wins and losses alike:

| class | rule | losses | wins | our win rate when it holds |
|---|---|---|---|---|
| hoard-killed | we lost a bag of 100+ gems to an enemy champion | 77 (52%, 44-60) | 10 (5%) | 10/87, 11% (6-20) |
| hoard-camp | a bag of 100+ lost to a camp | 3 (2%) | 1 | 1/4 |
| unbanked | none of those, and 300+ gems still carried at the end | 16 (11%, 7-17) | 6 (3%) | 6/22, 27% (13-48) |
| overrun | none of those, and 10+ deaths or under 300 gems captured | 35 (24%, 18-31) | 2 (1%) | 2/37, 5% (1-18) |
| outfarmed | the rest | 16 (11%, 7-17) | 179 (90%) | 179/195, 92% |

The thresholds are descriptive. With a 50-gem bag the first class holds 100 losses and 33 wins (25% won); with 200
gems, 59 losses and 4 wins (6% won).

Gem flow (it adds up exactly per game: wealth = captured + bags taken - bags lost to champions - bags lost to camps).
The final deficit, Fish minus us, mean per loss: farm 234, fight 452 (twice the net bags lost), camp 10. In our wins
the same split is farm 378, fight 194 in our favour.

| class (losses) | farm | fight | our deaths v theirs | our capture gems v theirs | carried at the end | median rounds |
|---|---|---|---|---|---|---|
| hoard-killed | 75 | 784 | 8.6 v 6.2 | 871 v 946 | 132 | 804 |
| unbanked | 155 | 32 | 4.8 v 2.8 | 914 v 1070 | 563 | 712 |
| overrun | 672 | 131 | 16.1 v 5.5 | 326 v 998 | 9 | 974 |
| outfarmed | 190 | 76 | 4.8 v 2.8 | 841 v 1030 | 68 | 820 |

**Wins against losses on the same clocks** (means, us minus Fish):

| | r100 | r200 | r300 | r400 | r600 |
|---|---|---|---|---|---|
| capture gems, wins / losses | +26 / +6 | +77 / +9 | +160 / +10 | +219 / -7 | +300 / -64 |
| lifetime gold, wins / losses | -140 / -216 | -210 / -447 | -152 / -723 | -117 / -1022 | +81 / -1778 |
| deaths, wins / losses | +0.1 / +0.4 | -0.3 / +0.6 | -0.9 / +0.7 | -1.3 / +0.9 | -2.8 / +1.8 |
| bags lost to champions, wins / losses | +2 / +4 | +1 / +10 | -17 / +17 | -26 / +32 | -55 / +112 |

- We are behind in gold at round 100 in wins and losses. In wins we out-capture Fish in gems from the start; in
  losses the gem capture is level to round 400 and the gap comes afterwards from bags.
- By the death difference at round 150: one or more fewer deaths than Fish, 76% won (60/79); level, 60% (102/170);
  one more, 46% (26/57); two or more, 26% (10/39).
- By game length: 600 rounds or fewer 84% (74/88), 601-800 57% (67/117), over 800 41% (57/140).
- Our deaths in losses after round 400: 6.8 a game, 3.9 of them Vesper's, 4.7 on our own half. In wins our Prism
  makes 2.3 kills a game after round 400.

**Breakdowns** (95% Wilson intervals; a map has two games, so a single map says nothing):

| cut | games | won |
|---|---|---|
| set: v1 core / v1 ext / p170 new | 80 / 180 / 85 | 55% (44-65) / 55% (48-62) / 65% (54-74) |
| side a / b | 173 / 172 | 58% (51-65) / 56% (49-64) |
| picks 5 / 4 / 3 | 220 / 69 / 56 | 57% (51-64) / 57% (45-68) / 59% (46-71) |
| our draft has Prism / has not | 287 / 58 | 58% (52-63) / 55% (42-67) |
| our draft has Vesper / has not | 212 / 133 | 52% (45-59) / 66% (58-74) |
| Fish's draft has Vesper / has not | 260 / 85 | 56% (50-62) / 62% (52-72) |
| altars 1 / 2-4 / 5+ | 91 / 226 / 28 | 59% / 57% / 57% |
| longest side up to 40 / 41-60 / 61+ | 98 / 105 / 142 | 60% / 53% / 58% |

- Loss classes by draft: with our Prism, 74 of 121 losses are hoard-killed and 18 overrun; without it, 17 of 26 are
  overrun and 3 hoard-killed. Prism changes how we lose, not how often.
- Fish's commonest drafts: Vesper/Vendetta/HoR/C&I/Willow 55% of 66 (21 of 30 losses hoard-killed),
  Vesper/Varg/HoR/C&I/Willow 66% of 62, Vesper/HoR/C&I 57% of 46, Vesper/Tavi/HoR/C&I/Willow 46% of 28. Our commonest:
  Ryth/Vesper/C&I/Prism/Willow 52% of 56 (23 of 27 losses hoard-killed). No pair of cells here separates at 95%.
- Maps: of 170 maps, each played from both sides, we lost both games on 42 and won both on 67; independent games
  would give 31 and 56. So part of the result is fixed by the map and the two drafts on it, which this data cannot
  split.
- Round limit: 8 games, 3 won. The five losses: `03one_gem` (24-248, overrun), `01boss_battle` (379-947 with 4,086
  gems carried), `05clouds` (136-548 with 1,438 carried), `02guardians` (107-318, a 1,475-gem Prism bag killed at
  round 1909), `05cassette` (548-953). Three of the five are hoards that never scored.

## 4. Root causes from the trace

### 4.1 Hoard-killed (77 losses)

`hoard_trace.py`, `encounters.py`, `death_trace.py`. Of 93 own deaths with 100+ gems in losses, 83 are traced through
the death (68 of them Prism's).

**The bag was being kept, as the rule says.** `keeps_gems` (economy/bank.cc) holds Prism's gems until its bag wins or
the race closes. At the death the bag was winning in 10 of 68, a banking branch had run in the last 12 turns in 15,
and the median bag was 422 gems short of the win.

**Prism knew, late.** On its last turn `want_home` (combat/fight.cc) said yes in 56 of 68. The final unbroken run of
yes turns is a median of 6 (quartiles 2, 6, 10). At that run's first turn:
- the killer stood 3-6 tiles away in 34 of the 47 cases where our belief has a position (ranged reach 3, a dash 2 more);
- it had been in sight for a median of 28 rounds (quartiles 9, 28, 45) while Prism farmed, held or walked on;
- the first hit had already landed in 18 of 55, and came within 3 rounds in 13 more;
- our health was a median 80%. The reasons: a pack zone 26, a lost stand 22, low health 7.

The stand is judged against enemies that can strike within `params::pursuit_steps` (2) turns of walking, so the
verdict turns when the killer is already inside the distance it closes.

**The retreat is a walk.** On the turns that wanted home with a recall running, `continue_recall` refused it 549 of
551 times: `safety.threatened(here)` 286, `recall_outruns` false 255, the walk no slower 8; kept 2. Fish's Vesper walks as fast as Prism,
hits from 3 and dashes 2; our believed Strength for her at these deaths is a median 450 against Prism's 2,000 health.

**This is how we die in general.** Of all 1,581 traced deaths to champions, 76-98% (by phase and result) come on a
turn that already wanted home, after a median run of 4-7 such turns; about half wanted home before the first hit.
The pattern is the same in our wins; losses have 5.6 times as many late deaths.

**Encounters** (Prism with 100+ gems, an enemy in sight within 9 that kills Prism before Prism kills it, by health
over Strength against its health over our spell and attack output): 720 episodes in 287 Prism games.
- In wins, 305 episodes and 2 deaths. In losses, 415 episodes and 91 deaths (22%), 31,669 gems.
- By the enemy's turns to kill us: under 2, 38% died; 2-4, 25%; 4-7, 17%; 7 or more, 5%.
- `want_home` said yes on the first turn of 22% of episodes.

**One game in full** (`fb2e2eae-4`, 04comb, exact re-run): we lead by 481 wealth at round 500. From round 557 Prism
(585 gems, score 307) walks to the only altar to bank. Fish's Vesper (12,200 health, Strength 640, both as we believe
them) arrives there to tribute. Rounds 561-590: Prism alternates a retreat step (the stand is lost at 7 tiles) and a
bank step (at 8 tiles no roster forms) between two tiles, 22 rounds, while Vesper channels 301 gems in its sight. The
recall is refused 18 times as not outrunning her. Rounds 591-592 Prism hits her for 2,451 (20% of her health). Rounds
593-598 it walks away at her pace, 5 tiles ahead, recall refused as threatened. Round 599 she dashes and hits for 796;
round 600 she acts first and kills. Fish wins at round 653.

**After the death.** The game runs a median 151 more rounds. Fish starts 368 channels of 11+ turns in those 77 games;
we cancel 180 by stun and 42 by lock, and Fish still completes one in 63 games. In 31 of the 77 the stolen bag alone
took Fish's total past 1,000.

### 4.2 Hoards that never score (4 unbanked losses, 3 round-limit losses)

`channels.py`. Our tribute channels by length, live:

| length (turn ends) | channels | completed | cancelled by a lock | by a stun | by hand |
|---|---|---|---|---|---|
| 1-5 | 4,040 | 96% | 66 | 53 | 15 |
| 6-10 | 779 | 91% | 22 | 17 | 21 |
| 11-20 | 216 | 68% | 22 | 6 | 36 |
| 21-40 | 199 | 44% | 44 | 7 | 57 |
| 41-70 | 330 | 24% | 109 | 40 | 94 |
| 71+ | 159 | 4% | 34 | 38 | 76 |

- A constant chance of about 2.7% a turn of being cancelled fits every row (e^-0.027L: 67%, 44%, 23% at 15, 30, 55
  turns). A placed lock cancels every channel at its altar (altar_locks.effect) and costs Fish 10 gold.
- Prism's channels of 21+ turns: 639 started, 155 completed, 180 cancelled by a lock, 79 by a stun, 214 by hand; a
  cancelled one had run a median of 8 turns. Our wins need 2.8 such attempts a game.
- `05clouds`: the bag wins from round 644 to the round limit, 29 channels (15 cancelled by locks, 7 by stuns), the
  longest ran 74 turns, Fish placed 17 locks; we killed Fish 46 times and lost 136-548. `01boss_battle`: winning from
  round 895, 25 channels, the bag grew to 4,086 gems (a channel of 180+ turns). `02gift_wrapping`: winning from round
  541, 11 channels, 6 cancelled by locks, lost at round 775. `04bowls`: winning at round 907, lost at 967.
- **The local body has the same hazard**: against `fr8-g25` (336 calibration games) our 21-40 turn channels complete
  39% and 41-70 turn ones 20%. So this part of the game is in the local gate already.
- The other 12 unbanked losses never held 1,000 gems in all: Prism still kept its bag (9 of them never started a bank
  branch) when Fish reached 1,000. Banking it would not have changed the result; they are races lost on farm.
- Wealth to score: in our wins our wealth first reaches 1,000 a median 39 rounds before the end (quartiles 13, 39,
  76). In 23 losses our wealth reached 1,000 at some point (sampled every 25 rounds) and in 47 it reached 900; in 16
  we got to 1,000 before Fish did, and in 3 more level with it.

### 4.3 Hoards lost to camps (3 losses, and `01boss_battle`)

Five own camp deaths carried 100+ gems, all Prism's. Traced:
- `ad01a0b7-5` (04courtyard, 446 gems, a lead of 413): Prism farms a Monolith as its nearest target for 8 turns at
  126 a turn, from 1,442 of 4,340 health down to 525, `want_home` no on every turn. The hit then rises to 286;
  `want_home` says yes at 239 health and the next phase kills. `mono_trapped` (economy/crew.cc) leaves only when
  health is at most the camp's damage times the steps to get behind a covering ally, plus one.
- `1af8e2c8-4` (01boss_battle, 974 gems): on the altar-guard branch with no enemy in sight, Prism walks into a
  Monolith's reach at 1,390 of 2,130 health, takes 252 a turn, and `camp_trapped` fires at 634: three steps later it
  is still in reach and dies.
- `f3e6611d-4` (01starfish, 661 gems, a lead of 443): guarding an altar inside an Elk's fire, then Vesper arrives.
- `8184ff41-4` (a win, 111 gems): sieging a Golem from 860 health to 20.

Camp deaths as a whole are not a weakness against Fish: ours 0.23 a game (3,111 gems in all), Fish's 0.57.

### 4.4 Overrun (35 losses) and outfarmed (16)

- Overrun losses have their first own death at a median round 94: on our own half (26 of 33), outnumbered or alone
  against two or more (22 of 33), with a median of four enemies and two of ours within 8, the killer in sight 6+
  rounds before in 41 of 61 early deaths. Killers: Issac, Heart of Ruin, Marcella, Cassi. 17 of the 35 are drafts
  without Prism. 14 maps were lost from both sides this way (`01gold_rush`, `01elk_arena`, `00stampede`, `00ribs`,
  `00galaxy`, `00quarry`, `00swirl`, `02arena`, `05border`, `05nest`, `05poker_chip`, `05runway`, `00contest`,
  `04waves`).
- The decisions before these deaths look like those in our wins (before the first hit: farming 46%, already
  retreating 43%; `want_home` yes 43% against 41% in wins). What differs is how often Fish's pack comes: 1.74 early deaths a game in
  overrun losses against 0.47 in wins. No single decision was isolated; this class is map and draft more than a branch.
- Outfarmed: Fish captures 1,030 gems to our 841 with deaths level (4.8 v 2.8). Four of the 16 ended within 100 gems.

## 5. Fixes tested here

All arms are copies of `variants/lab-emb6-c520-ps` (v118 without the live mask) under `bots/variants/v118f-*`,
gated against it by `gate.sh` / `gate2.sh`: fgate at 100k fuel, pool v3 batches 16-17, release builds, own drafts
both sides. **std** is the standard bodies (Flp4, Mt3q); **fr8** puts the Fish r8 body `fr8-g25` in Flp4's place.
Fresh maps decide; the figure is the candidate minus the reference in points, with its 95% half-width and the fresh
games played. **fork** is `livefork_arms.py`: 337 of the 340 distinct live games (the others end before round 330) forked at rounds 300, 450, 600 and 750 with
the engine state of the live game (Fish's Vesper as rich as she was), the candidate and the reference each taking our
side against `fr8-g25` (two noise seeds), 2,054 paired continuations, standard error clustered by game.

| arm | change | std | fr8 | fork | verdict |
|---|---|---|---|---|---|
| rr1 | the retreat keeps its recall whenever nothing can hit our tile this turn (`recall_outruns` dropped) | -3.60 ±0.89 (20,480) | -2.77 ±0.67 (40,960) | - | loses |
| rr2 | the same for carriers of 19+ gems only | -2.55 ±0.80 (20,480) | -1.67 ±0.61 (40,960) | -1.90 ±1.61 | loses |
| hf | a kept hoard goes home when an enemy in sight wins the duel with it and could walk into reach within a recall's length | -2.31 ±0.75 (20,480) | -3.47 ±0.83 (20,480) | -4.04 ±1.56 | loses |
| hb2 | once such an enemy has shown itself, the bag is banked, not kept | -10.31 ±0.90 (20,480) | -12.42 ±0.99 (20,480) | -5.55 ±1.73 | loses |
| hb | hf and hb2 | -12.66 ±0.99 (20,480) | -14.69 ±1.08 (20,480) | -6.77 ±1.96 | loses |
| cap350 | the bag is kept only below 350 gems | -6.05 ±0.74 (20,480) | -8.63 ±0.85 (20,480) | -6.33 ±1.95 | loses |
| cap500 | the bag is kept only below 500 gems | -2.77 ±0.57 (20,480) | -3.41 ±0.64 (20,480) | -1.66 ±1.30 | loses |
| cm | a carrier of 19+ gems keeps two more camp phases of health in hand before `want_home`'s camp tests | -0.29 ±0.45 (40,960) | +0.16 ±0.50 (40,960) | -0.15 ±1.13 | level |

- The std and fr8 reads share the candidate's games against the Mite body (half of each), so they are not two
  independent samples. A gate stopped at REJECT after one batch; rr1, rr2 (fr8) and cm played two.
- The fork read agrees in sign with the fresh-map gates for every losing arm, also on the forks of the live
  hoard-killed losses alone (hf -5.2 ±3.1, hb -7.0 ±4.2, cap350 -6.8 ±3.2, cap500 -1.6 ±2.4, rr2 -4.6 ±3.4).
- From those forks the reference wins 53.7% (±4.2) against the body where the live games gave 51.5%: over all forks
  the body is close to live. From the positions of live losses it wins 27.3% where Fish won every one, and from live
  wins 78.5%.
- **Why the replay said otherwise for the recall.** After a refusal for `recall_outruns`, our champion took no damage
  in the next five rounds in 90% of 10,366 cases, and 676 later deaths (29,281 gems) followed such a case. But an
  enemy came within 5 tiles of the tile we would have stood on in 69% of them. Counting a recall as landing only if
  none did leaves 31%, and 86 distinct deaths (5,229 gems; 13 deaths and 4,372 gems with a 100+ bag). Standing still
  costs more than that recovers: rr1 and rr2 lose everywhere.
- **Puppet counterfactuals** (`puppet_cf.py`: an arm against Fish's recorded inputs) depart from the live game a
  median of 390 rounds before the hoard's death for the hoard arms, so they say nothing about it. For cm they are
  clean on two games (the camp is deterministic and no enemy is near): in `ad01a0b7-5` the arm first differs at round
  511 and Prism walks out with its 446 gems; in `8184ff41-4` at round 172, out with 111.

## 6. Action items, ranked

**Play.**

1. **A bag carrier's camp-fire margin** (the cm arm; `combat/fight.cc` `want_home`, with `economy/crew.cc`
   `mono_trapped` and `combat/fight.cc` `camp_trapped`).
   - Mechanism: a camp's kill destroys the whole bag (combat.camp_kill), and the two tests leave one hit of margin.
   - Touches: 5 deaths in 345 games, all Prism's, 2,599 gems; three losses from leads of 413-470 and the 974-gem bag
     of `01boss_battle`. Upside: at most 4 games in 345, about +1 point against Fish; nothing against opponents who
     never see our hoard near a Monolith.
   - Evidence: trace (4.3); the puppet run reverses two of the deaths; A/B: level on 40,960 fresh games against each
     pair of bodies (-0.29 ±0.45 and +0.16 ±0.50) and from live positions (-0.15 ±1.13). So it costs nothing
     measurable locally, and its gain is too rare to measure locally: the case for it is the four live games.
   - Risk: carriers leave camps two hits earlier, so some clears are abandoned; the std read leans down (-0.29).
     Before shipping: a longer gate (two batches narrow each read to about ±0.5).
   - The 974-gem death is a second fault this arm may not cover: the altar-guard branch (`economy/altar_guard.cc`
     `guard_turn`) stepped a hoard into an awake Monolith's reach with no enemy in sight. Its steps should take the
     camp area as blocked for a carrier; that needs its own arm.
2. **Do not ship hoard caution of the kinds in section 5**, and do not spend live quota on them: recall on a
   reachable tile, earlier flight from a duel-winning enemy, banking once hunted, a cap at 350 or 500. Each loses
   2-15 points on fresh maps and loses from the live positions too. This repeats, on v118 and with the r8 body, what
   EXPERIMENTS already records for ocean 506 (bm-* arms, cap 150, bank at enemy score + bag).
3. **The hoard that wins but cannot score** (`economy/bank.cc` `keeps_gems`, `closing`, `carry_bag`; the shop's
   Tribute emblem).
   - Mechanism: a channel lasts a turn per 10 gems and is cancelled at about 2.7% a turn, live and locally, so a
     60-turn channel completes one time in five and a 150-turn one never. A Tribute emblem cuts a channel by a third
     (economy.emblems): 60 turns become 40, 23% becomes 34%.
   - Touches: 4 unbanked losses and 3 round-limit losses outright, and the 39-round median delay between holding
     1,000 gems and winning in every win (2.8 long channels a win).
   - Not built here. Candidates, each measurable locally because the body has the hazard: Prism buys the Tribute
     emblem when its bag's channel passes a length (the lab already prices the emblem; this ties it to the bag); once
     a bag wins, later captures go to allies who bank them in short channels instead of lengthening the one that
     keeps failing (in `05clouds` and `01boss_battle` the winning bag kept growing for 1,000+ rounds).
   - Upside: a few games in 345 directly; unknown through shorter games (our win rate is 84% in games of 600 rounds
     or fewer and 41% past 800). Risk: gold spent on the emblem instead of Focus or health.
4. **Overrun games** (35 losses): no decision isolated here. The lead from the data is exposure: early deaths come
   on our own half at 2 against 4 with the killers in sight for 6+ rounds. The pack-zone work in EXPERIMENTS
   (2026-11-11, pg-z8) is the open thread; nothing new to add to it.

**Strategy and draft.**

5. **Answer the gold funnel.** Fish converts gold, not gems: one champion with a 33% gold passive takes 72% of the
   team's gold, buys Greed, and by round 600 kills any of ours in two or three turns while ours cannot kill it. Our
   gold goes to Prism (43% of ours at round 100), whose shards are the weakest in the game (65 health, 2.5 Strength).
   When we draft Vesper too (212 games) she has 165-230 gold at round 100 against Fish's 424-494. Candidates, all
   design work to be judged on fresh maps: our Vesper as the holder of gold-rich groups that carry few gems; her
   build following Fish's (Capture, Treasure, then Greed). Inferred from replay counts; nothing here tests it.
6. **Draft.** The data cannot separate draft from map (two games a map, drafts fixed per map). Leads only: we win 52%
   with our own Vesper drafted and 66% without (intervals touch); our commonest five-pick draft loses 23 of its 27
   losses to a hoard kill. A draft refit should use Fish r8's drafts (deterministic per map and side), which the
   fishr8 body already holds.

**Measurement.**

7. **Judge hoard changes from live positions.** `livefork_arms.py` is now set up on v118's 337 r8 games: any arm
   takes our side at rounds 300-750 with Fish's real items. It costs about two minutes for 2,054 paired
   continuations, agreed in sign with the gates on the six losing arms it ran and read level on cm. Its limit is the
   body's play after the fork.
8. **Fit the Fish body to the hoard kill.** Targets from this data: 0.29 Prism deaths with 100+ gems per Prism game
   (93 in 287), 22% of out-killed encounters ending in Prism's death in losses and 13% overall, Vesper's 2.9 kills
   and 0.78 deaths a game, 393 Strength and 5,553 health at round 600. From the positions of live losses the body
   lets our reference win 27%; a faithful one would be near 0. Until a body does this, a counter to the hoard kill
   cannot be seen locally, whatever it is.
9. **Trace harness.** Use `tracebot.py`'s lines for charybdis-line versions: `live_trace_bot.py`'s CS, CC and HG lines
   perturb them, and its patch no longer applies.

## 7. Against earlier analyses

- **opp_detect.** v118 contains no opponent detection: no file or symbol of it exists in `bots/baselines/v118/src`
  (it lives in `variants/c520-mx`). So Fish r8's new priority encoding changes nothing in v118's play, and none of
  the r2 to r8 drop comes from a misread opponent. The r8 fix in `fishr8/oppd-r8.patch` matters only for a future
  arm that uses the detector.
- **v118 against v117 on r8.** CHANGES 524 and the fishr8 README set v118's 57.4% against v117's 49.7% of 165. The
  scrim log now holds 304 v117 games against r8: 171 won (56.3%). On the same 304 cells v118 won 174, and 243 results
  are equal. Emblem lab 6 did not gain against Fish r8.
- **r2 to r8** holds as the fishr8 README says: on 245 shared cells v118 won 186 against r2 and 139 against r8 (23
  flips for, 70 against), and on the 93 cells where Fish's draft is unchanged, 74 and 54.
- **Vesper's share of our deaths** is 42% of deaths to champions over all 345 games and 45% in losses, not 62%.
  Prism loses 124 gems a game to deaths in Prism games, 90 of them to Vesper (the README: 116 and 99). Vesper took
  100+ from Prism in 59 of 287 Prism games (21%) and we won 5% of those, against 74% of the 219 where she took none.
  Her kills of Prism have a median bag of 124 at round 604 (the README: 215 at 612).
- **"Banking or caution has lost in every form tried"** is confirmed and extended: seven more forms, on v118, against
  the r8 body, and from live positions. The fishr8 notes' own two counters, read the same way while this ran (commit
  f1970b23f: Prism banks after Vesper's Greed -2.64 ±0.96, a pre-Greed Vesper focus +0.54 ±0.57), agree.
- **LOSSES.md (v78)** blamed Marcella's nuke, our own initiations and the lock war. Against r8 Marcella is drafted in
  a quarter of the games and makes 0.5 of our 9.6 deaths a loss; the deaths are retreats, not initiations (76-98% on
  a turn that already wanted home); Fish places 2.8 locks a game to our 3.9, and locks matter through cancelled
  channels (4.2), not through blocked altars (no blocked tribute attempt of ours in 345 games).
- **Fuel** is not a cause: our out-of-fuel turns are 7.2 a game in wins and 11.5 in losses, under 0.3% of turns.
- **Rules.** Nothing in these replays or re-runs contradicts `cambc-rules.yaml`.

## 8. Looked for and not found

- A decision that separates overrun losses from wins before the first death.
- A side, pick-count, altar-count or map-size effect: every cut is within its interval of 57%.
- A recall that would have saved hoards at an acceptable cost (section 5).
- A local-versus-live gap in channel cancellation: the body cancels our long channels as often as Fish does.
- A draft effect separable from the map.
- Any change in v118's behaviour by opponent.

## 9. Files

Scripts (run from the repo root, `source ~/venv/bin/activate`):

| file | what |
|---|---|
| `manifest.py` | harness manifest for v118 from the pulled rows; unzips replays and fuel into `replays/v118/ladder/` |
| `features.py` | per-game, per-death and per-capture tables from the live extract (`replays/v118/analysis/`) |
| `taxonomy.py` | the loss classes, the gem-flow split and every breakdown (`--list`, `--tsv`, thresholds) |
| `tracebot.py` | v118's trace bot: release code plus D, TT, EB, WH, CR, CX (and ST, CT) lines; the header documents each |
| `tracelib.py` | loader for the traced re-runs, trusted rounds only |
| `hoard_trace.py` | the victim's last turns before each big-bag death (`--show KEY` prints one) |
| `death_trace.py` | the same summary for every own death, by phase, result and class |
| `encounters.py` | Prism with a bag against an enemy that out-kills it: episodes and what followed |
| `retreat_recall.py` | refused retreat recalls against what happened next, with the frozen-tile test |
| `channels.py` | tribute channels by length and how they ended; `--local EXT` for a local batch's extract |
| `puppet_cf.py` | an arm against Fish's recorded inputs in chosen games |
| `livefork_arms.py` | arms from live positions against the r8 body; `--read` prints the paired table |
| `gate.sh`, `gate2.sh` | the fgate reads of section 5 (logs in `~/tmp-offload/v118-fish/gates/`) |

Data (gitignored): `replays/v118/` holds the manifest, the harness workspace `ws/`, `runs/batch` (release re-runs),
`runs/direct` and `runs/direct-st` (traces), `extract/ladder`, `analysis/` (the tables and `taxonomy.tsv`), `cf/`
(puppet runs) and `livefork*/`. Arms: `bots/variants/v118f-{rr1,rr2,rk,hf,hb,hb2,cap350,cap500,cm}` (gitignored; rk
is rr2 plus hf, built but not gated).

Changed outside this folder: `tools/replay/harness/versions.py` (registers `bots/baselines/v<N>` live uploads).
Nothing was committed from this work; another session's commit 480fd0a61 picked up that change and the first
versions of `manifest.py` and `features.py`. `features.py` has changed since (the wealth-lead fields) and the other
files here are untracked. `research/ideas-2026-11-12/v118-fish-b/` is a different session's.
