# Idea A: altar control (id `altar`, seeds 510000-510999)

The user's ideas 4 (safe altar) and 5 ("game is cooked": camp the altar nearer the opponent and fight their
tributers; on a kill their bag is ours). Bush play (idea 3) feeds the stand choice.

## Evidence (2026-11-05)

**Ladder archive** (replays/ladder-archive, 546k games; top-30 vs top-30 59k):
- 97% of games end by a side reaching 1000 (top-30: 56.6k of 59.1k), so almost every loss is "the
  opponent raced to 1000". What matters is the state on the way.
- Comebacks are rare. With the leader at 700+ and 300+ ahead, the trailer wins 3.0% overall: 5.4% on
  one-altar maps and 2.2% on multi-altar maps. Altar contests already happen on one-altar maps.
- Ours (Pantheon, 8,195 games): one-altar maps 1,779, lost 317. We were cooked (opponent 700+, 300+ ahead)
  in 203 of them and won 14 (6.9%). On multi-altar maps: cooked 693, won 46.
- Post-patch (11-04 on, 455 games): one-altar maps lost 43 of 100, cooked 31, won 1. Multi-altar maps
  lost 143 of 355.
- One-altar maps: 31 of the 127 ladder maps (24%), and 22.6% of a fresh ladder-mix suite (510001-510040).

**Ladder replays** (big-arm, 123 distinct post-patch games: ours plus top-12):
- Altar choice: their tributes go to the altar nearest their own spawn in 76% of cases (top teams 73%, and
  another 27% within 5 steps of it). Guarding the enemy's spawn-nearest altar catches most of their tributes.
- Cooked one-altar losses (opponent 600+, 200+ ahead): 80 enemy tribute starts (4,151 gems, mean 52;
  channels up to 54 turns), 70 completed. 3 were cancelled by locks, 1 by a stun, 1 by death. At 38 starts
  none of our champions was within 8 tiles of the altar, and at 20 more only one. Their final banking is
  uncontested.
- Bags lost to champion kills, one-altar maps. In our losses: ours 265 a game (76 within 4 of the altar),
  theirs 32. In our wins: theirs 151, ours 46. Carrier kills decide one-altar games.

**Self-play** (ocean vs ocean, 588 one-altar maps of fresh-510001..510010, one side each):
- The games are lopsided. The loser's median final score is 343. After 700/300, ~79 rounds remain and the
  trailer wins 4.2%. After 600/200, ~132 rounds remain (8.1%); after 500/150, ~198 (11.3%).
- The loser loses 393 gems a game in bags to champion kills (220 within 4 of the altar), the winner 117.
- Locks: ~6 placed per side a game. Lock cancels: loser 0.41 a game, winner 1.09.

## Design

**A1, guard the one altar when cooked.**
- Trigger (team state, readable by every body): enemy tributed ≥ `enemy_min` and enemy − ours ≥ `gap`.
  It turns off when the gap falls below `gap / 2`.
- Who guards: the top `guards` living bodies of a static fighter ranking (base health × Strength, by
  champion type, ties by index). Cassi & Issac go last, since a linked death hands over both bags. The rest
  farm and bank as now, and bring their bags to the guarded altar.
- The stand: tiles within `stand_radius` of the altar's tribute tiles, open, out of camp reach. Bush tiles
  rank first (a bush tile cannot be seen from outside, and attacking from it does not reveal us), then tiles
  nearer our spawn. Each guard takes a distinct tile by rank.
- Turn: in `decide`, after the bag branch (a guard with a bag banks right there), before `chase`:
  - a visible enemy within `leash` of the altar → `chase` (its fight sim decides);
  - else walk to the stand and hold it.
  - The strike search, retreat, recall and shopping run as before.
  - The guard drops its farm claim.
- Lock mode, `lock_mode`:
  - `keep` (0): keep our lock on the guarded altar, even off our side. An enemy tribute attempt then spends
    5 attacks breaking it in front of the guards.
  - `bait` (1): no new lock on the guarded altar while guarding. An enemy tributing there is left to channel
    and be killed (a kill takes the bag; a lock only sends it away). It is locked only when its channel ends
    within `bait_lock_turns` or the tribute wins.
- **A2**: the guarded altar on multi-altar maps is the one nearest the enemy spawn (`multi` knob). Thresholds
  as A1.
- **A3** (later, if time): a winning bag's altar by walk plus channel against reach from enemies' possible
  sets.
- **A4**: on one-altar maps an unsafe carrier waits at the altar indefinitely (carry_bag). Not a fix
  target yet; to measure.

**Fuel:** stands are computed once per game (tens of tiles). There is a field per stand tile, cached like
wake_ring's, so ~2.5k once and then a field read a turn. `chase` costs what it costs now. Expect no change in
out-of-fuel turns.

**Subvariant grid (dev: one-altar maps of fresh-510001..510010, then full ladder-mix suites):**
- trigger (`enemy_min`/`gap`): 500/150, 600/200, 700/300;
- `guards`: 2, 3, all;
- `lock_mode`: keep, bait;
- `stand_radius` 2 vs 3; `leash` 6 vs 8.

**Expected gain:** applies to the ~23% one-altar maps. Self-play: the trailer is cooked in ~97% of
one-altar games and wins 4-11% from there. A guard that lifts that by 10-20 points gives +1-2 points a
one-altar game, so +0.3-0.5 overall; more if an earlier trigger works. Ladder ceiling, from the archive:
~2.5% of our games are cooked one-altar losses.

## Results

All against oc-base1 on the one-altar dev subset (588 maps, 1,176 games); EXPERIMENTS "Altar control (ocean,
2026-11-05)" has the tables.
- **A1 as designed is level.** g1-g5 read 49.1-50.8: plain guard, bold 1-2, bait locks, an earlier trigger.
  - The leader waits out the guards: 89% of its post-cook tributes start with none of our bodies within 3.
  - Bold guards die more (5.3 deaths a game against 3.6) without taking more bags: a cooked mirror side is
    the weaker side.
- **Sweep, d2.**
  - Always on: 1 guard 44.0%, 2 guards 32.1%. A permanent guard costs farming.
  - Trigger 300/100 with 2 guards: 50.3%. Late trigger 700/300: 50.3%. Radius 3, leash 8: 50.9%.
- **Course change: escort.** In self-play one-altar games a team holds a winning bag for 30+ rounds in 70% of
  team-sides (median bag 535). 89 of 1,176 games are lost from there.
  - Winning tributes over 30 turns: 3,200 starts, 285 completed; cancels were 1,171 manual, 848 stun, 662 lock.
  - Short ones (8 turns or fewer): 452 of 634 completed.
  - So the guard is tried as an escort: hold the one altar while a body of ours carries a winning bag
    (`escort`). This is the user's idea 4 on maps with no other altar.
  - Ladder caveat: there such a hold was lost once in 45 team-games. Ladder teams punish it less than our
    mirror does.
- **e3 = escort + cooked guard** (`on`, `escort`, the rest default) is the one that kept a reading.
  - Full ladder-mix chunks c1-c3 (15,360 games): 50.1%. Confirm on unused seeds (20,480 games): 50.5%
    (49.8-51.2). `--mix varied`: 51.1% of 2,560.
  - On one-altar maps alone (unbiased self-play): 51.2% of 7,976 (50.1-52.3). Multi-altar maps, where it is
    inert, read 50.0-50.2.
  - Panel on fresh one-altar maps (altar-one-p3): e3 − base +2.7 proteus, +1.5 demeter, +1.3 ocean-td,
    −0.1 astraeus, +1.9 v67 (mean +1.5).
  - Panel check (panel-check-514510): +0.1, +0.3, 0.0, +0.3, +0.3. It passes the rule.
  - Fuel per turn is unchanged (bench). A/B out-of-fuel turns are +2-5%, from the different play.
  - On multi-altar maps e3's replays are byte-identical to oc-base1's at 100M fuel (790 of 790). At the real
    budget about half diverge through fuel, which is noise (82 winners flipped, 46 against 36).
  - **Dedicated one-altar confirm** (the 10,250 one-altar maps of fresh-510200..510379): **51.1% of 20,500
    (50.4-51.8). Kept**, at ~+0.25 overall.
  - Sweep within e3 (8,088 one-altar games each): escort_at 800 49.6 and 900 50.3 (k0 51.3); guards 2/4 50.8/51.6;
    leash 4/9 51.3/51.6. Only an earlier escort is clearly worse; the defaults stay.
- **Cut, each after a sweep:** the cooked guard alone (g1-g5, h1-h6); escort alone (e1, e2, e4); escort_keep
  (e5, e6); A2's multi-altar guard (a1-a3); A3's safe altar (s1-s3, margins 4-12, slack 10-25). A3's
  redirect fired in 27 of 300 games and left winning-tribute outcomes unchanged (1,933 against 1,931 won).
- A4, the indefinite wait at the one altar, was not changed. The escort covers that carrier.
- Side finding: a Prism hoard (685-853 gems, 79-86-turn channels) restarted and cancelled ~15 times in one game
  (d1-g1 040). Not this idea's lever.
