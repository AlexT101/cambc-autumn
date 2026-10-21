# hyperion: world model (workstream E)

How hecate dies compared with what its danger estimates said, and what to change in those estimates. Code refs are
`bots/hyperion/src` at main 4674914. Data: 480 v32 ladder rows (360 distinct games, 68% won), the 582 local hecate vs
hecate-v7 games, and 6 traced local games (`debug_fights`, `debug_beliefs`). Numbers are ladder first, local second.
Ladder replays carry no stdout, so there hecate's estimate was rebuilt from true positions, Strength/Focus,
cooldowns and turn order: `compute_strike` plus `threat_strike`'s widening ("the bound"). Scripts and tables are in
`replays/orch/research/` (`edata_*`). "Trapped" and "exit" use Chebyshev distance, not `Reach`, so they are
pessimistic.

Reviewed (E-critic). These were checked against the tables and code: the verdict counts, the point-of-no-return
split and its gems, the death rates by health, the `possible` misses, the Trade split, and the `threat_strike`,
`camp_trapped` and `next_turn_round` claims. One correction: category F is "any damage above the bound", not only the
two-turn chain (see proposal 2).

## Findings

**Scale.** 6.28 deaths a game on the ladder against 4.64 locally. 2536 champion kills handed over 40,097 gems
(~84 a game). Only 8% (5%) of our deaths were traded within 3 rounds. Killers: Stellar 31%, Heart of Ruin 19%, Ren
11%, Marcella 11%. 01boss_battle (sealed altar) is left out.

**We see the killer coming and stay in its reach.** The killer was at Chebyshev 2-4 at the start of its killing turn
in 82% of kills, and walking distance equals Chebyshev in ~97% of them. It was visible at our last turn in 82% (88%);
only 11-12% were ambushes. Death rate per turn inside a visible enemy's bound: 13.1% (15.3%) below 35% health, 0.4%
(0.1%) above.

**The bound is the right size per enemy.** One tile outside the modelled reach, an enemy hits 0-2% of the time;
inside, 28-60%. When it hits, real damage over the bound has median 0.90 (p90 1.19). With the visible bound at 1-2x
our health we die before our next turn 29% (45%) of the time, and at 2x+ 52% (72%).

**Champion kills by the bound's verdict at our last turn** (local 76/11/7/6%):

| verdict | kills | share | gems |
|---|---|---|---|
| A: the visible bound was already lethal | 1816 | 72% | 29.3k |
| B: lethal only once unseen enemies count | 377 | 15% | 8.1k |
| C: a cooldown ready only on the enemy's second turn | 172 | 7% | 1.1k |
| F: any other damage above the bound | 166 | 7% | 1.5k |

**The death was decided a turn earlier.** At our last turn every exit was already lethal in 77% of A kills. The point
of no return (the last turn a step or ready dash reached a tile the bound called survivable) was the final turn in
39% of kills and the turn before in 54%, and that 54% lost 24k of the 40k gems. At that turn 71% were already below
35% health (so `want_home`'s `low` had fired), and the end tile they chose passed the bound in 90%. Under the rules
everyone walks one tile a turn, ranged reach is 3-4 plus dashes, and damage cancels a recall. So a chaser within
reach + 1 cannot be outwalked. `retreat_step` (bot.cpp:251) ranks homeward steps by one window of `damage_bound`.

**`threat_strike` (safety.cpp:637) misses rule cases on two-turn enemies.** It reads one slot mask at
`next_turn_round` for both turns (C), and takes max(walk then strike, strike + one basic) instead of chaining the two
turns. The cases where that undercounts:
- Stellar casting its unit spell on one turn and its ground spell on the next (one cast a turn, rules `turn.cast`).
  That is 3.4 Focus + 2 Strength, against a modelled 2 Focus + 2 Strength (+49% at base stats).
- Heart of Ruin's landing + attack, then an attack, from 3-4 tiles.
- Vesper's dash + attack, then attack + reset + attack: 3x Strength from 5 tiles, against a modelled 1x.

On the ladder C's killers are Stellar 67, Heart of Ruin 48 and Marcella 25. F's are Heart of Ruin 75, Ren 43 and
Stellar 41, and F also holds damage that is not a chain, such as Ren's reflection when we hit it. Every C and F kill
had a survivable tile in reach at our last turn.

**`possible` is not always a superset.** 8.4% of unseen enemies' true tiles were outside it, and 7.8% (524 of 561
misses) came right after a comms sighting, usually one tile out with no turns added. In sets of 9 tiles or fewer (the
ground-cast targets) the miss rate is 18.6%. `note_sighting` fixes the enemy at `{seen_round, -1}`, and
`turns_between` counts the enemy's turns from `slot()` ranks. Ranks need priorities, which are readable only in
sight. The dumps also had our own slot wrong 36.3% of the time, which may be dump timing.

**Camps.** The bound already called the camp lethal at our last turn in 421 of 479 camp deaths (3.6k gems lost).
`camp_trapped` (bot.cpp:1920) returns false while sieging.

## Proposals, ranked by expected value over cost

All three follow from the rules (one step a turn, dash 2, cooldown 8, one cast a turn, recall cancelled by damage,
healing on spawn). None of them depends on map features or names a situation. They feed STRIKE-SEARCH: its leaf
danger is `Safety::blow`, so better bounds improve it, and `trapped` is a tile filter its phase 4a can call. Proposals
1 and 2 touch `compute_strike`/`Reach`, as phase 3a (Varg's splash reach) does, so don't build them at the same time.

### 1. Leave one turn before the point of no return: `Safety::trapped` (M)

- **Screen first (offline, about an hour).** Over the 480 ladder games (`edata_common.py` has the Strike model),
  count how often our turn-ends are trapped at 35%+ health with an enemy in sight, and how many point-of-no-return
  turns (k=1 above) are trapped. Build only if trapped fires on 10% or fewer of those healthy turns and catches 40% or
  more of the k=1 turns. If it fires too often, weight window 2 by the measured in-reach hit rate (28-60%) and screen
  again. Don't add a constant.
- **Change.** `trapped(p, h)` is true when every exit q of p (the 8 steps, plus our landings if our dash is ready next
  turn) has `W1(p) + W2(q) + camps(p) + camps(q) >= h`:
  - W1 is today's bound at p: the sum of `blow`.
  - W2 sums, for each visible enemy, `strike(e, its turn after our next)` at `max(0, d(e, q) - m_e)`. m_e is its
    farthest move before our next turn: 1 a turn, plus 2 if a dash is ready.
  - An exit on our spawn needs only W1 below h.
  - Chebyshev distance, no Reach queries. That is a few hundred ops a tile, and it runs only when an enemy is in
    sight.

  Once proposal 2 lands, W1/W2 use its slot split.
- **Use.**
  - (a) `want_home` when `trapped(here)`.
  - (b) `step_guard` and `retreat_step` rank trapped tiles after every untrapped one, before `damage_bound`.

  Phase 4a of STRIKE-SEARCH later takes `trapped` as a leaf filter in place of `retreat_step`.
- **Not in this build.** Folding camps into it and deleting `camp_trapped`, which came from the rival, won, and
  excludes sieges on purpose. First count how many of the 421 camp deaths were sieging.
- **EXPERIMENTS.** Retreat variants, home ratio 3.0 (46.7%) and "a 100+ carrier home from any visible threat"
  (48.7%) were all triggered by proxies. Plan3's retreat planner was level at 100M even before it lost on fuel, and it
  priced one window. What is new here is the second window, computed without Reach. Plan3 is also a warning: picking
  better tiles alone did not help.
- **A/B.** (a)+(b) against a frozen baseline. Expect gems lost on death and deaths below 35% near enemies to fall,
  kills not clearly down, and out-of-fuel turns not up.

### 2. Chain the enemy's two turns from the slots actually ready (M)

- **Change.** When `turns_before_ours >= 2`, the widened strike at distance d is
  `max over S1 ⊆ ready(t1) of A_S1(d) + B_S2(max(0, d - m_S1))`:
  - S2 = `ready(t1 + 1) \ S1`;
  - A and B are `compute_strike` with those masks;
  - m_S1 is turn 1's farthest move (1, or 3 with a dash in S1).

  `Reach::build_ways` places the same two turns, so Strike stays an upper bound on Reach. The memo key gains the
  second mask (4 -> 16 entries a champion). Keep `Strike::max_reach` at 6 in this build. Vesper's 7 (walk + dash, then
  walk + reset + attack) also moves the pack zone, so it is a separate change.
- **Replaces.** The `max(walked, twice)` rule in `threat_strike`, `Reach::at`'s `twice_ && basic` term, and
  `most_damage`'s "+ one basic".
- **Evidence.** C is 172 kills, and F's chain share is unknown (F is 166). Together they are 13% of kills but only
  6.6% of gems, which is why this ranks below proposal 1. Stellar alone, the top killer, is undercounted by about
  half on two-turn rounds.
- **EXPERIMENTS.** The "exact enemy-turn threat model" was level or lost on nemesis, but it replaced the bound with
  an expectation. This keeps the bound and fills rule gaps. CHANGES 5 (the widening, deaths -29%) is the precedent.
- **A/B.** Expect fewer C and F deaths and fewer deaths overall, kills about level, and out-of-fuel turns not up.

### 3. `possible` as a true superset after a comms sighting (S)

- **Check first (debug_block, the 6 traced games).** Compare `slot(me, round)` with the bound the visible `acted`
  flags give (teams alternate, so the visible champions that have acted bound our rank). This settles whether the
  36% is real or just dump timing.
- **Change.** In `turns_between`, when the enemy's order against the moment can't be read (it is unseen, or its rank
  comes from a priority that wasn't read), count the turn, so `possible` grows too much rather than missing a tile.
  If the check shows our slot is wrong, raise our rank to the acted-flag bound.
- **Built (orch/w2-small).** Check over 8 local games against hecate-v8: our slot broke the acted-flag bound on
  0.14% of turns, so the 36% was dump timing. The modelled order of a visible enemy against ours was wrong 15% of
  the time, nearly all from enemy ranks. Every priority was read on almost no turns, so an unseen enemy's turn this
  round always counts, and `possible` is dated after it.
- **Evidence.** 524 of the 561 misses come right after comms fixes. Whether this cuts category B (15% of kills) is
  unproven, but small ground-cast targets miss 18.6% of the time either way.
- **A/B.** `audit_beliefs.py` misses near 0, then an A/B for win rate at least level.

## Not proposed

- Allies in `Trade` by arrival. When the sim says we win, we fall first 18.2% of the time and they fall first 18.3%,
  but that counts only engaged fights with a death. Across all such fights the foe died 15.6% against our 4.4%. Its
  error grows with each ally counted (balance 0.81 to 2.09 for 1-4 allies). It is a screen for STRIKE-SEARCH phase 5,
  not a stand-alone change.
- `hit_given_reach` 0.25 stands in for two measured rates: visible enemies in reach hit 28-60% a window, unseen ones
  12-19%. Revisit after proposal 3.
- Bush scouting (ambushes 11-12%), recall or bag as danger states, carrier rules or escorts (lost).
