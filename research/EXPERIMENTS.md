# Experiments

What has been tried, so it isn't repeated: lessons, and the ideas that lost, were level and dropped, or are held.
Kept changes are in [hyperion/CHANGES.md](hyperion/CHANGES.md), not here. The untrimmed file (every measurement and
the per-round fuel details) is `git show 1d5ddf0:research/EXPERIMENTS.md`.

Win rates are against the bot's previous version, all maps from both sides at the real fuel budget, unless noted.
`tools/ab.py` runs 1094 games: ladder (70) + `maps/gen` (512) + fresh `maps/gen-s1` (512); results before 2026-10-21
used 390-582 games. Noise is about ±2.1 points on 582 games; "level" means within noise. Don't retry a lost or level
idea as is: it needs a new mechanism or ladder evidence. Results on older bots are hints, not rules.

## Lessons

- Gains on the committed suites shrink on fresh seeds (crews +22/320 -> +8/320; a 54.6% hecate bundle was 47.8% on a
  fresh suite): confirm on a fresh seed.
- Self-play hides ladder behaviour. Our bots start a recall at every turn end and cancel it the next turn, so locally
  enemies look like they are recalling in ~90% of rounds (5-8% on the ladder): any value for cancelling an enemy
  recall is inflated locally, and an ally's `channel == recall` does not mean it is going home. Changes level or
  better locally have lost on the ladder (the big-bag escort, the stunned-turn skip, the shared-gem caster draft).
- Bug fixes, drafts and map-type strategies have paid off. Retuning tactics or pricing against our own bots rarely
  has; whole-model ports (morgana's farm pricing into nemesis 43.0%, a pack zone decided by the fight sim 46.9%,
  farming stage 2 45.1%) lost.
- Who wins: in the mirror the side that dies first loses 70%, and +1 net kill at round 300 takes the win rate from 56%
  to 85%. A fight's swing is predicted by HP fraction, lifetime gold and the initiative; head count adds nothing once
  those are in. contest is the only ladder map that reaches round 2000: 31% of its games tie on gems, then gold
  decides.
- Loss analysis (mirror, 390 games): winners die 2.0 times a game against 4.1. 86% of deaths carry no gems; 79% are on
  our own ground, but the risk per champion-round is 3.4/1000 on enemy ground vs 0.7 on ours; 88% follow a retreat
  within 4 turns. Weak families against other bots: huge, large-open, islands, Monolith-only, maze, rows.
- Single-map flips between versions follow fuel trajectories, not regressions; two games a map is noise.
  `results.json` match `winner` is the 0-based bot index; reading 1 as bot 1 inverts every per-map table.


## Phase 1-2 fuel: why the level bundles add up to a loss (2026-11-04, astraeus_wip)

Every bundle of phases 1a, 1b and 2 was level on its own 10k games, but together they lose, and only at the real fuel
budget. 40,448 games each on `maps/p1-total` (fresh-81001..81079, 20,224 maps, used by no bundle's A/B), own drafts,
fast runner. The heads: 57194754 (before 1a), 5de95d33 (1b with its audit fix), 0570a63d (phase 2).

| A/B | Real budget: win % (CI), OOF cand / ref | 10M fuel a turn |
|---|---|---|
| 5de95d33 vs 57194754 | 48.8 (48.3-49.3), 519.5k / 344.2k | 49.9 (49.4-50.4) |
| 0570a63d vs 5de95d33 | 47.2 (46.8-47.7), 1067.5k / 544.7k | 50.3 (49.8-50.8) |
| 0570a63d vs 57194754 | 46.0 (45.6-46.5), 1034.1k / 350.6k | 50.6 (50.1-51.1) |

Drop-one bisect at the real budget: the head with one commit reverted (bot code only, conflicts resolved by hand so
later commits stay) against the head. Above 50% means the head does better without it.

| Dropped | Against | Win % (CI) | OOF cand / ref |
|---|---|---|---|
| B6 camp stands (0570a63d) | 0570a63d | 51.0 (50.5-51.5) | 980.4k / 1107.7k |
| B1 unseen and ally walls (75212575) | 0570a63d | 50.4 (50.0-50.9) | 899.6k / 1093.7k |
| B2 HoR, camps after our fall (32d0a232) | 0570a63d | 50.4 (49.9-50.9) | 1007.4k / 1099.3k |
| B5 shop cache keys (5b33d792) | 0570a63d | 50.4 (49.9-50.9) | 1014.6k / 1110.5k |
| B3 allies' real distance (6159e094) | 0570a63d | 50.1 (49.7-50.6) | 1028.6k / 1103.8k |
| B4 stun tribute delay (81a281de) | 0570a63d | 50.0 (49.5-50.5) | 1105.4k / 1105.7k |
| 1b-1 crews (28fa24b1) | 5de95d33 | 50.5 (50.0-51.0) | 494.4k / 530.9k |
| 1b-6 sight, fight sim heals (9910ecd6) | 5de95d33 | 50.4 (49.9-50.9) | 496.3k / 531.4k |
| 1b-2 combat values (b1f3990f) | 5de95d33 | 50.1 (49.6-50.6) | 517.9k / 524.7k |
| 1b-4 economy (f679bdf4) | 5de95d33 | 50.1 (49.6-50.6) | 514.4k / 533.3k |
| 1b-5 pathing, Willow (3b28299d) | 5de95d33 | 50.0 (49.5-50.5) | 486.4k / 532.7k |
| 1b-3 camps (385287f9) | 5de95d33 | 49.9 (49.4-50.4) | 534.6k / 534.1k |
| C dead camp tiles (55280955) | 5de95d33 | 50.0 (49.5-50.5) | 534.0k / 534.2k |
| B lock hits (365ece65) | 5de95d33 | 49.9 (49.4-50.4) | 531.5k / 532.3k |
| 1b audit fix (5de95d33) | 5de95d33 | 49.9 (49.5-50.4) | 529.4k / 532.4k |
| 1a-2 tribute race (b1f348a9; takes B's lock hits with it) | 5de95d33 | 50.1 (49.6-50.6) | 502.9k / 534.0k |
| 1a-1 walking races (cfcedb21; helpers kept) | 5de95d33 | 50.0 (49.5-50.4) | 526.1k / 532.2k |
| 1a-3 camp ties, heal reach (0d881691; takes A and C's heal_reaches with it) | 5de95d33 | 50.0 (49.5-50.5) | 533.4k / 533.3k |
| 1a-4 holders, siege health (b10c57e8; 1b-3's siege kept) | 5de95d33 | 49.8 (49.3-50.2) | 535.7k / 535.0k |
| 1a-5 shield casts (fa8c6e4a; takes the 1a fix's shield credit) | 5de95d33 | 50.1 (49.6-50.5) | 533.2k / 536.1k |
| 1a-6 draft camp heal (3a17d920) | 5de95d33 | 50.0 (49.5-50.5) | 533.1k / 532.9k |

No one commit carries the loss: each one that adds fuel costs up to a point and the drops roughly sum to it, so the
cost compounds through out-of-fuel turns. Phase 1a costs little (1a-2's walks are its one fuel item, -6% OOF when
dropped). Dropping the 1a audit fix (b4b10061) doesn't build (1b-1 uses its walk field). The changes live in
`bots/astraeus_wip`; astraeus is back at 57194754.

## Phase 2: assumptions replaced by calculations in the fight sim, the unseen model and the shop (2026-11-04, astraeus 5de95d33; CHANGES 379-)

Six bundles, each against the one before it (the first against 5de95d33, phase 1b's audit fix). 10,240 games each
(20 fresh suites merged into one directory), own drafts, fast runner. Shipped unless the CI's top is below 50%.

| Bundle | Against | Maps | Win % (CI) | OOF cand / ref |
|---|---|---|---|---|
| 1: unseen enemies' and allies' walks round walls (CHANGES 379) | 5de95d33 | fresh-149001..149020 | 49.2 (48.2-50.2) | 176.8k / 138.9k |
| 2 with stuns on the damage's target: HoR by its health, camps after our fall, stuns (lost) | 1 | fresh-149021..149040 | 48.6 (47.6-49.6) | 212.4k / 190.2k |
| 2 without the stuns (CHANGES 380) | 1 | fresh-149141..149160 | 49.9 (48.9-50.8) | 214.2k / 190.3k |
| 3: allies' strikes in kill bids by real distance (CHANGES 381) | 2 | fresh-149041..149060 | 50.5 (49.5-51.5) | 230.0k / 213.0k |
| 4: a stun on a tributing enemy by the rounds it delays (CHANGES 382) | 3 | fresh-149061..149080 | 50.1 (49.1-51.0) | 218.5k / 218.4k |
| 5: shop caches keyed by income and horizon (CHANGES 383) | 4 | fresh-149081..149100 | 49.8 (48.8-50.8) | 259.5k / 235.2k |
| 6 with the least-fire stand: camp stands on tiles that see the member (lost) | 5 | fresh-149101..149120 | 48.5 (47.5-49.4) | 319.3k / 254.7k |
| 6 with the stand nearest the old tile (CHANGES 384) | 5 | fresh-149161..149180 | 50.3 (49.3-51.3) | 300.3k / 263.9k |

## Phase 1b: assumptions replaced by calculations (2026-11-04, astraeus b4b10061; CHANGES 369-)

Six bundles, as phase 1a's, each against the bundle before it (the first against b4b10061, phase 1a's fix).
10,240 games each (20 fresh suites merged into one directory), own drafts, fast runner. Shipped unless the CI's top
is below 50%.

Bundle 1 first read each body's own walk (`walk_to`): 49.8 (48.8-50.7) against 3a17d920, OOF 105.2k / 96.7k; on the
team's walking-only field before the fix's other parts, 49.6 (48.7-50.6), 105.8k / 97.7k.

Then three follow-ups: CHANGES 375 (fuel only: `heal_reaches` on support's helpers, bench replays identical 16/16
and 52/52 wide), and C and B below, each against the one before; then the audit's fix (CHANGES 378).

| Bundle | Against | Maps | Win % (CI) | OOF cand / ref |
|---|---|---|---|---|
| 1: crews and pick-ups by the walk (CHANGES 369) | b4b10061 | fresh-148001..148020 | 49.6 (48.7-50.6) | 106.5k / 97.4k |
| 2: combat values from the ready strike (CHANGES 370) | 1 | fresh-148021..148040 | 49.7 (48.8-50.7) | 107.0k / 103.5k |
| 3: camps by the hits that land (CHANGES 371) | 2 | fresh-148041..148060 | 50.0 (49.1-51.0) | 101.9k / 102.0k |
| 4: tribute deadline by share, Capture and Collectors values (CHANGES 372) | 3 | fresh-148061..148080 | 49.9 (48.9-50.9) | 117.8k / 112.8k |
| 5: paths forget our camp kills, Willow walks to her heal tiles (CHANGES 373) | 4 | fresh-148081..148100 | 49.4 (48.5-50.4) | 131.4k / 120.8k |
| 6: sight-aware watchers, unseen approach, heal reach in the sim (CHANGES 374) | 5 | fresh-148101..148120 | 50.1 (49.1-51.0) | 132.7k / 122.5k |
| C: heal positions on dead camp tiles (CHANGES 376) | 375 | fresh-148141..148160 | 50.0 (49.0-51.0) | 144.2k / 144.5k |
| B: our lock's hits left in the carrier's tribute (CHANGES 377) | C | fresh-148161..148180 | 50.2 (49.3-51.2) | 140.1k / 140.2k |
| fix: two_blows' tie, Capture credit with an ally owner (CHANGES 378) | B | fresh-149121..149140 | 50.0 (49.0-51.0) | 141.4k / 141.5k |

## Phase 1a: assumptions replaced by simple calculations (2026-11-04, astraeus 57194754; CHANGES 362-)

Six small bundles, mostly straight-line distances replaced by walks, each against the bundle before it (the first
against 57194754). 10,240 games each (20 fresh suites merged into one directory), own drafts, fast runner. Shipped
unless the CI's top is below 50%.

| Bundle | Against | Maps | Win % (CI) | OOF cand / ref |
|---|---|---|---|---|
| 1: walks for capture races, claims, sides (CHANGES 362) | 57194754 | fresh-147001..147020 | 49.9 (49.0-50.9) | 89.7k / 88.7k |
| 2: the tribute race by walks and locks (CHANGES 363) | 1 | fresh-147021..147040 | 50.1 (49.1-51.1) | 100.4k / 94.5k |
| 3: camp-hit ties by turn order, heal reach (CHANGES 364) | 2 | fresh-147041..147060 | 50.3 (49.3-51.2), 10,238 games | 97.5k / 96.5k |
| 4: remainder shares, siege capacity in effective health (CHANGES 365) | 3 | fresh-147061..147080 | 50.1 (49.2-51.1) | 100.0k / 99.8k |
| 5: shield absorption by whole casts (CHANGES 366) | 4 | fresh-147081..147100 | 50.5 (49.6-51.5) | 93.2k / 91.5k |
| 6: the draft's camp-heal cost by the drafted walk (CHANGES 367) | 5 | fresh-147101..147120 | 50.0 (49.0-51.0) | 91.6k / 91.7k |
| fix: one team walk for capture races, the live shield (CHANGES 368) | 6 | fresh-148121..148140 | 50.3 (49.3-51.3) | 95.6k / 95.1k |

Every bundle is level and none moved out-of-fuel turns by more than ~6%; all six shipped as the calculations. The
fix after them: `capture_taken` compared each body's walk on its own dash graph (Issac's crosses what Cassi's cannot),
so the two could disagree on who is nearer; it now reads one walking-only field for the team.

## Unseen enemies where they may be, not where last seen (2026-11-04, astraeus 7b4f4ad; step 1 is CHANGES 361)

Step 1: every test that read an out-of-sight enemy at its last tile (`e.pos`, `age(round) <= 1`) reads `possible`,
counted only while Safety counts it (`credible_unseen`):
- the pack zone, with an unseen member's box around its possible tiles off its spawn;
- `may_draw_home`, `pack_covers`, `preyable`, `chase_aim`, `ring_quiet`, `enemy_may_see`, `fight_near`, the turn
  order's `enemy_dist`;
- the stand: `stand_reach`, `late`, `turns_to_kill_idle` (by `unseen_approach`), and stand_lost_at's early return
  (`unseen_may_hit_within(p, pursuit_steps)`).

Left on the last sighting: prey and chase aim (aiming at it), the sealed-pocket prey, `walk_allies_in`, the
retreat tie-break and the in-sight tests.

Step 2 is E1 (ablation B above): the step guard adds the tiles an unseen threat hits and ours does not, each judged
by `stand_lost_from` with no hold. E1's `unseen = ... || unseen_may_hit_within(p, 0)` is already in step 1:
`stand_reach` lists the unseen that hit p.

Fuel:
- pack members prefiltered by a near test;
- `credible_unseen` and `possible_on_spawn` memoised;
- the turn order's unseen distance bucketed;
- the exposed tiles from the threats' `area` boards;
- `unseen_approach` from a per-enemy capped Chebyshev field once an enemy is asked about near a second tile
  (bench 52/52 identical).

10,240 games each (20k for the last row), own drafts, fast runner:

| Candidate | Against | Maps | Win % (CI) | OOF cand / ref |
|---|---|---|---|---|
| step 1, first cut | 7b4f4ad | fresh-99501..99520 | 49.5 (48.5-50.4) | 94.5k / 73.5k |
| step 1+2, first cut | 7b4f4ad | fresh-99521..99540 | 49.4 (48.4-50.3) | 151.3k / 74.1k |
| step 1, fuel work | 7b4f4ad | fresh-99501..99520 | 49.9 (48.9-50.8) | 87.1k / 75.5k |
| step 1+2, fuel work | 7b4f4ad | fresh-99521..99540 | 49.4 (48.4-50.3) | 138.6k / 74.4k |
| step 1, final (s1c) | 7b4f4ad | fresh-99561..99580 | 49.7 (48.7-50.6) | 85.2k / 72.3k |
| step 1+2, final (s12c) | 7b4f4ad | fresh-99541..99560 | 50.4 (49.5-51.4) | 134.0k / 74.3k |
| step 1+2, final | step 1, final | fresh-99581..99599 + 99521..99540 | 49.9 (49.2-50.6), 19,966 games | 271.7k / 173.8k |

Everything is level. Step 1 costs ~+18% out-of-fuel turns, and step 2 a further ~+56%.

Diagnosis on fresh-99521..99540, against 7b4f4ad:

| Variant | OOF cand / ref |
|---|---|
| step 2 worked out but not applied | 136.0k / 74.2k |
| step 2 with the cover left as step 1's | 132.8k / 74.7k |
| the cover widened but no stands | 89.1k / 75.4k |

So step 2's cost is its own stands, not the behaviour it changes nor the wider cover making routes search twice.
Profiled at 100M on the census maps:
- the stands run in ~1.3% of step-guard calls (1,312 of 101k), 3.2 tiles a call;
- they average 24k a call: trade 3.7k, reach 1.8k, roster 0.6k, lethal 0.4k a tile;
- 36% of the tiles and 42% of the calls lose;
- the spikes land in turns already heavy with fights.

An exact memo of stand_trade's camp/walker path saved 4%, so the fights are mostly distinct; it was dropped. A
union-first pass (one stand over every exposed tile's roster) would save at most ~15% at that loss rate.

Step 1+2 (30ae22ec) against step 1 shipped (33e5cd33), fresh-99701..99857 (40,192 maps, 80,384 games): 49.6%
(49.2-49.9), out-of-fuel turns 1,051k against 676k (+55%). Step 2 is level or slightly worse.

Step 1 shipped for the single model (CHANGES 361), level at +18% out-of-fuel turns. Step 2 not shipped: no gain for
the fuel (branch worktree-agent-aeacfa16ac18552d4, commit 30ae22ec).

## Oscillation hunt (2026-11-04, astraeus, CHANGES 337)

Traced ~7,700 games; detectors and findings in `research/oscillation-2026-11-04/`. Fix A/Bs at 10,240 games on
fresh-88001..88020, own drafts (each stream alone, then merged):

| Change | Against | Win % (CI) | OOF cand / ref |
|---|---|---|---|
| 1 terrain reach (d62d050) | 088bf3f4 | 50.3 (49.4-51.3) | 66.4k / 56.2k |
| 2 one verdict + veto (e509b4e) | stream 1 | 50.3 (49.3-51.2) | 207.8k / 66.4k |
| 3 farm pricing by the walk (25e10cc) | 088bf3f4 | 50.5 (49.5-51.4); 49.9 on seeds 3391-3410 | 60.0k / 57.7k |
| 4 kite plan, siege yields (9886f82) | 088bf3f4 | 50.2 (49.2-51.2) | 58.5k / 56.5k |
| 4 siege low at the stand (5012bf1) | 9886f82 | 50.0 (49.0-50.9); Monolith suites 48.9 of 2,682 | 60.5k / 57.5k |
| 1+3+4 merged | 088bf3f4 | 50.1 (49.1-51.0) | 72.4k / 56.1k |
| all four, 20,480 games (fresh-88001..88040) | 088bf3f4 | 50.6 (49.9-51.3) | 458.7k / 111.3k |

Lost and reverted: a two-round threat window for turn-order parity (-0.3 to -0.8: every Safety consumer turned
pessimistic); terrain distance for joining allies without their dash (-0.5); re-searching farm's pick during
pricing (+15k OOF, -0.8); a wide farm search cap, static + 96 (-1); pricing the fire taken walking into a siege
stand (45.9% of 2,682 on Monolith maps). Removing wasted turns did not move the win rate against our own previous
version.


## Oscillation hunt, round 2 (2026-11-04, astraeus, CHANGES 358)

Investigator: `research/oscillation-2026-11-04/round2-findings.md` (5,124 traced games of 8c0f3d49 against v69,
v68, v66). Detected with `--bridge-oof`, round 1's -22% reads about -12%: out-of-fuel turns had split episodes.
Wasted turns on common games fell 764k to 555k (-27%) from round 1.

| Change | Against | Games | Win % (CI) | OOF cand / ref |
|---|---|---|---|---|
| W2 every advance asked (e718eaf), kept | 8c0f3d49 | 20,480 | 50.0 (49.4-50.7) | 336.3k / 311.2k |
| W1 + W2 merged | 8c0f3d49 | 20,480 | 49.2 (48.5-49.8) | 367.0k / 311.8k |
| W1 final, pack zone at arrival, one shared verdict (1dc5cbf) | 8c0f3d49 | 10,240 | 50.2 (49.2-51.1) | 169.5k / 156.4k |
| W1 full: veto judges the arrival round's window, enemies advanced (c62e260) | 8c0f3d49 | 10,240 | 48.4 (47.4-49.4) | 365.0k / 157.5k |
| W1 full at --fuel 400000 | 8c0f3d49 | 10,240 | 48.0 | 0 / 0 |

W1's full model removed the turn-order step-then-leave cycles (detector -17%, retreat churn -36%) and lost about 2
points even with no fuel limit, as did every variant that changed the stand's verdict (47.8-49.7): those steps mostly
pay (camp hits, bank or farm tempo, capture resets while the enemy has no turn before ours). Refusing them is wrong;
pricing what the step earns before the enemy's double turn is the open direction. W2's ablations: the chase ask
carries most of the episode gain and most of the fuel; a blanket hold when every first step is refused raised
stuck_fail 47% for nothing.


## One safety model: unseen enemies in the stand and guard, want_home's parts in the guards (2026-11-04, astraeus e73fe3ca)

Six changes, one candidate: the stand and the step guard count unseen enemies from `possible` (the guard judges such
tiles by `stand_lost_from` without holds); `paying_soon` and `recall_outruns` use `may_reach_within` (`walk_in`
removed; a stunned enemy counts a turn later); Willow's leave test is `exposure_here().enemy`; `keep_out` asks
`drawn_home_at`; a strike-search plan that hits nothing never ends where `drawn_home_at` leaves; `keep_out` runs
the stand on tiles off our own ground that have walkers and no hit.

| Comparison | Maps | Games | Win % (CI) | OOF cand / ref |
|---|---|---|---|---|
| all six vs e73fe3ca, own drafts | fresh-99401..99440 | 20,480 | 49.5 (48.8-50.2) | 280.0k / 141.7k |

Level or slightly worse, at about 2x the out-of-fuel turns. No oscillation detector run.

Ablations (`bots/variants/astraeus-abl{A,B,C}`, the later changes switched off), each against e73fe3ca on
fresh-99401..99420 (10,240 games; the full candidate's games on the same suites for the last row):

| Variant | Win % (CI) | OOF cand / ref |
|---|---|---|
| A: `paying_soon`/`recall_outruns` on `may_reach_within`, Willow's test, `keep_out` by `drawn_home_at` | 49.8 (48.8-50.8) | 72.1k / 70.9k |
| B: A + the unseen stand and step guard | 50.4 (49.5-51.4) | 121.3k / 71.6k |
| C: B + no unhit search end where `drawn_home_at` leaves | 50.2 (49.3-51.2) | 121.7k / 71.5k |
| all six: C + the own-ground stand in `keep_out` | 49.4 (48.5-50.4) | 140.5k / 71.8k |

All within noise of each other. The unseen stand and guard carry most of the fuel (+70%), the own-ground stand the
rest; A costs nothing.

The unseen double count (safety.cc only): an unseen enemy
whose turn this round comes after ours has that turn's walk or dash in `possible` already (World::track), and
`threat_strike` counted it again. The fix strikes from `possible` without that turn's walk, dash travel or
walk-then-stun, a second turn before ours still full. On A (`bots/variants/astraeus-ablA-dc`) against A,
fresh-99421..99440, 10,240 games: 50.1% (49.1-51.1), OOF 71.1k / 71.3k. Level, free.

Shipped: A and the double count (CHANGES 360). B, C and the own-ground stand are left out for their fuel.

## Oscillation work, final check and the veto ablation (2026-11-04, astraeus 19f22154)

| Comparison | Maps | Games | Win % (CI) | OOF cand / ref |
|---|---|---|---|---|
| 19f22154 vs 088bf3f4 (before the oscillation work) | fresh-99121..99237 | 59,900 | 50.2 (49.8-50.6) | 976.3k / 329.2k |
| 19f22154 with the work veto off (`arm_veto` stores nothing) vs 19f22154 | fresh-99238..99277 | 20,480 | 49.8 (49.1-50.5) | 149.4k / 325.1k |

The veto off, traced, against v69 (1,708 games, osc_compare `--bridge-oof` vs 19f22154's trace): episode turns +6.9%
(+4.2 to +9.5): retreat churn +16.5%, branch flips +18.8%, pingpong +12%, jitter +12%; stuck_fail -18.7%,
stuck_idle -10.8%; win vs v69 48.1% against 52.1% (1,708 games each, CIs overlap). The veto (337, its asks 358) holds
~7% of the episode reduction for 2.2x the out-of-fuel turns and no measurable win rate.

The removal (CHANGES 359), 20,480 games each, own drafts:

| Candidate | Against | Maps | Win % (CI) | OOF cand / ref |
|---|---|---|---|---|
| veto removed | 19f22154 | fresh-99278..99317 | 49.6 (49.0-50.3) | 142.0k / 328.0k |
| veto removed | 088bf3f4 | fresh-99278..99317 | 50.6 (49.9-51.2) | 143.3k / 111.2k |
| veto and believed enemies removed (359) | 19f22154 | fresh-99318..99357 | 49.8 (49.1-50.5) | 142.1k / 336.2k |
| the same | 088bf3f4 | fresh-99318..99357 | 50.0 (49.3-50.7) | 142.2k / 115.7k |
| the same | veto removed | fresh-99318..99357 | 49.6 (48.9-50.3) | 144.3k / 147.1k |

The veto removal replays byte-identically at 100M to 19f22154 with the veto never armed (bench `--set wide`, 52/52).

## Older bots (aphelios, morgana, nemesis; 2026-10-15/18)

- Lost or level: one champion per camp (38-45%); waiting at respawning groups (45%); ~20 tactical tweaks (retreat
  variants, fighting back when doomed, ally assist, pushing when ahead, gold in camp value, Durability second emblem
  −15, steering round the pack zone −15/240); farm pricing variants (reward discounted by enemies that could reach −3
  to −20, two-job lookahead −24, a constant gold share −4 to −8, pooled crew health −3); other drafts (37-50%) and Fish
  builds (−3); pack bonus or spread penalty in farm value; Monolith sieges on normal maps (39.6%); stickiness 1.0 (−5);
  shopping at 300 gold (−7); casting before walking (46.2%); camp damage in the fight sim (47.7%); a periodic ward
  rule (48.7%); ranking jobs by worth − ρ·cycle (27-34%); EOQ bag limit, tank assignment, Smith targeting, exact
  enemy-turn threat model, gold as score on Monolith-only maps.
- The whole team as one PVP pack (brawler): 2-8% vs nemesis. It earns ~150 gold a game against 540-940; a pure pack
  can't out-score five farmers.

## Strategy and economy

- Audit judgment calls dropped or replaced (2026-10-22, CHANGES 86): a comms capture reminder (re-posting pending
  captures in a cycle, 1652507) never sends stale data but changes the shared slot most rounds, which delays
  teammates' new captures, and teammates who saw a hold already infer the respawn; dropped untested. A carrier
  stranded by its avoided altar standing still (e22f389) idled 10-25 rounds even when banking was safe; replaced.
- Level or lost: true first striker in the fight sim, shopping ×2 emblems, third-party camp damage in the fight sim,
  rally assist, caster poke from our own ground, Cassi/Issac target priority, kite cap 40, altar control (6 variants),
  central-group kiting, Focus builds (−4), Monolith and cluster sieges on normal maps (5-40%), Monolith sieges on any
  map when their rate beats the team's (48.3%: started ~r320, never cleared in time), the pack zone for empty-handed
  farming too (48.1%; deaths up).
- Ladder-motivated (from the Intercontinental Fish analysis), lost locally (judge on the ladder): gold valued 3× in farm choice (46.9%), the
  top teams' draft with Focus Ren (42.3%), Cassi gold weight 10 (49.2%), gold front-loaded by gems left (47.2%,
  45.6%), a 100+ carrier going home from any visible threat (48.7%).
- 2026-10-19, level: life_value 600 and 1000; away pack ratio 3.0; a chase catch test plus a kill-per-turn floor; a
  game-ending bag met at its nearest altar with a lock, plus locks from enemy score 700; following a teammate's rally
  while the enemy is unseen (ladder 11/34); a Monster emblem in best_emblem. Lost: home and away retreat ratio 3.0
  (46.7%); live Monolith sieges on mixed maps when nearer our spawn (48.2%); Monster, Home and Treasure priced
  together (44.6%); farm value halved near a believed enemy's reach (41.5%).
- Big bags: an escort (a 150+ carrier waits for 2 allies) was level locally and halved big bags lost on Monolith-only
  maps, but lost on the ladder (scrims vs the top 5: 28-47 -> 26-49 and 24-51; stampede 0-1080 once escorts left the
  shared block). Treating a 150+ bag like Cassi/Issac (a fight where the carrier falls counts as lost) lost bags faster
  to a carrier hunter. Untried: keep the carrier with allies and flee towards them. Chasing any carrier, not only
  interceptable ones: 49.7%.
- Shared-gem maps: a spellcaster draft (Stellar, Ryth, Prism, Ren, Cassi, Varg) won 63.3% locally on 120 games but was
  level on the ladder (29-46 vs 30-45) and reverted; on Monolith-only maps it lost (45.1%).
- Emblems dropped: a model over five families with Health or main stat (Monolith-only 9/38); Home as second (50.4%) or
  first (48.9%) emblem.
- Locks cancelled 19 tributes each way in 390 games and cost a carrier ~3 attacks or a detour: a small ceiling. Locks
  only on enemy-side and middle altars: 47.6% (our own-side locks matter).
- Wrong and reverted: the crew value with capture rounds (48.0%; the claimer holds, the crew moves on); `passing`
  instead of `affordable` for hits after a walk (49.5%).
- Gem limits (CHANGES 24): gem_value 40 on top 50.8%; life_value 400 changed no game; brake_bag 30 50.9% and
  chain_bag_limit 80 52.7% (ladder 18-24, not confirmed on a fresh suite) after CHANGES 26.
- boss-battle (CHANGES 27, reverted): sieging the gate Monolith's key member opened the altar around round 1100, but its
  tile stayed in the other Monolith's reach and bags held back meanwhile (400-875) could not be banked. Ladder teams
  that score there kill both Monoliths in a burst and hold the tile (one banked 1987 in one channel). Ladder record
  there 2-11, all 8 0-0 games lost on gold.
- corridors farm targets flipped every turn (32% of farm turns A-B-A), crews joining and leaving together because
  claims reach teammates a turn late. Counting only earlier allies in crew_strength (44.5% gen), counting them once
  (40.5% ladder, 44.9% gen) and claim seniority all lost.
- A crystal shortcut over open ground (for corridors' lanes) was dropped: ladder opponents used 9 crystals in 9
  corridors games. Camps reachable only by crystal (ambush, big-world, fracture: 7-21 gems) are not farmed.
- Farming stage 2 (on CHANGES 40; crews from arrivals, one lexicographic pick, the risky/shared/help tiers deleted): 45.1%
  (gen 42.6), 46.2% without its heal term. Melee champions stopped working big monster groups and took small ones
  (melee camp damage −19%, capture gems −6.7%); the ladder went the other way (tributed +15%).
- Waking sleeping groups onto enemies (`wake_camps`): fired in 17 of 582 games, too rare to measure; its place is the
  strike search's wake pricing.

- Banking small bags only for nearby enemies (`strat/farm`, 2026-10-23). Ladder mechanism (624 games vs the top 20):
  `may_chain` refuses to keep farming whenever `safety.any_threat()`, which counts any visible or tracked enemy
  map-wide. In losses (r200-600) we hit camps on 16.6% of alive rounds against their 21.0%, bank smaller bags (mean
  per-game non-Prism median 17.6 vs 35.2 gems) and spend 30.5% of alive time on bank trips against 21.5%; in 44% of
  3,120 traced trip starts the enemy was unseen or 6+ tiles away (f5b32366-2 r344: an 8-gem Vesper went home for a
  Heart of Ruin 22 tiles off). Groups idle equally on both sides, so the gap is champion time. `may_chain` using
  `enemy_within(here, pursuit_steps)`: 50.5%; plus `chain_bag_limit` 30 -> 60: 51.2%; plus bags of 30-59 on the old
  map-wide rule (1e7864d): 51.4%. Out-of-fuel turns level. Locally the freed time barely became captures and bigger
  bags died more (gems lost on death 19.9 -> 24.7 a game in v1). Held as ladder-motivated (1e7864d).
  Follow-up (`strat/farm2`): in 1e7864d's A/B games bank trips fell 13% but walking to an altar with a bag did not
  (chained bags start home from farther out); all walking fell 1.6% of champion time. Rounds carrying a bag rose
  26.5% (30-59 bags +85%, from `chain_bag_limit` 60), deaths with 10+ gems 939 vs 729, net tributed -6 a game.
  Chaining unless a credible enemy is within `pursuit_steps` plus our walk to an altar (a0fbff0): 48.9%, out-of-fuel
  turns +5.5%. Dropped. If tried on the ladder, use v1's limit of 30: the 30-59 bags cause most of the extra loss.
  On astraeus (2026-10-24, `bots/variants/b12-chain45` against c2f1350b): `may_chain` refuses only for
  `credible_enemy_may_hit_within(here, pursuit_steps)` (any_threat's credibility, bounded by reach + 3), and
  `chain_bag_limit` 30 -> 45 (CHANGES 119's carrier pursuit check covers bags from `brake_bag` 11). 51.4% of 1104
  (48.5-54.4; ladder 53.8, gen 55.1, gen-s1 47.5), out-of-fuel turns 2367 vs 2446; fresh suite (seed 7511) 49.2% of
  512 (44.9-53.5). Against hyperion 54.7% of 1104 where REF reads 53.1% (gen 56.4 vs 47.9, gen-s1 53.7 vs 57.4: the
  same split). In its A/B games, CAND vs REF a game (ladder / gen / gen-s1): tributes 22.4/29.7/29.9 vs 25.4/32.7/33.4,
  non-Prism mean bag 26.7/21.9/21.1 vs 24.1/19.0/18.8, alive turns carrying a bag 43/41/42% vs 38/37/38%, turns
  walking a bag toward an altar or tributing level (16.6/16.4/16.8% vs 15.6/15.9/16.5%), gems lost on death
  193/80/97 vs 147/76/79, gems tributed 746/807/764 vs 707/760/789. Level; kept by the user's call on the ladder
  argument (CHANGES 133).
- Worst ladder maps against the top 20 (`strat/maps`, 2026-10-23; 624 games, 57% overall). Adjusted for opponent
  strength: 00interlock 21%, 00swirl 23%, 00rushbait_v2 25%, 00stampede 27%, 00corners 28%, 00great_wall 30%. In
  general, losses come from groups about equally far from both spawns: the opponents take 405 gems a game there in our
  losses against our 189 (wins: 117 against 313); home groups are level. No single decision rule behind it.
  Shared-gem maps (2 ladder, 12 in gen + gen-s1): `kite()` stations only ground casters at groups whose strikers reach
  4, so on 00stampede in r1-700 Prism kites 92% of its turns and the other four 0% (they farm gold); the opponents
  took the first clear of the 160-gem group in 18 of 22 games, usually after our Prism did most of the damage
  (1fd519dc-2: 11,880 vs 4,200). Non-kiters standing guard outside the group (ba53bab): 49.5%, class maps 9/28 (the
  guards idled, gold fell to 1/3-1/20 of theirs). On shared-gem maps a champion without a station falling through to
  `siege()` over big groups under `siege_ready` (13a6c1b): 50.1%, class 14/28. Held as ladder-motivated (13a6c1b):
  self-play cannot show it, as both sides kite slowly.
- Middle groups (0.42-0.58 of the spawn-to-spawn walk) are lost late, to strength, not to a contest rule (2026-10-23,
  624 games). In losses we take 249 middle gems a game against 506 (band 0.45-0.55); before r300 it is level (56 vs
  67), after r500 208 vs 451. Their lifetime gold over ours grows 1.13x (r100) to 1.49x (r800) and max health 1.10x to
  1.55x; their captures paid ~1.09-1.17x base gold (Treasure, now CHANGES 101). Before r400 our split of camp damage
  (home ~65%, middle 28%) is the same in wins and losses, and both teams use ~2.5 champions and ~29 camp damage per
  gem at middle groups worth 40+. `contest_capture` gates correctly (1,157 of 1,338 farm-instead turns were 5-8 tiles
  off with 1-5 hold rounds left). The remaining lever, skipping middle groups stronger enemies could reach, repeats
  ideas that lost (farm value halved near an enemy's reach 41.5%; reward discounted by reachable enemies -3 to -20).
- Teleport crystals for travel (`strat/gaps`, 2026-10-23). Ladder (624 games): opponents started 2,539 teleports in
  191 games (12 of 18 teams, ~4 a game, median 35 steps saved), mostly on 18 maps (00road_of_riches, 00great_wall,
  01starvation, ...); we teleported 56 times, only to altars no walk reaches. On those maps we win 86.1% against teams
  that never teleport and 51.5% against teams that do (elsewhere 65.2% vs 49.4%): ~19 points, also within ranks 11-20.
  Always carrying a crystal and using it while farming, banking or going home to shop where a landing beats the walk
  by 6+ steps, no enemy in sight of either end, no awake camp at the landing (37bbf44): 50.5% (ladder 50.0, gen 49.2,
  gen-s1 52.0), out-of-fuel turns level; against v37 61.5% where its base scored 61.1%. ~4.6 uses a ladder game, on the
  same maps; games with 10+ uses went 59.8% (82) against 49.3% with none, but they are under 10% of the suite. Steering
  long walks to crystal sources (d64dfe1, 74f43a8): 50.0%, 49.5%, out-of-fuel turns +35-90%. 37bbf44 shipped as
  CHANGES 105 after winning on its map class (55.7%), then reverted until it is refined. Other gaps found: opponents ward more (~30 a champion a game vs 19; 27% off bushes, ours never).
- Health in builds (`strat/builds3`, 2026-10-23; top teams' 624 ladder games against the current bot's 592 games vs
  v37). Top teams put far more emblems into Health (share to r1000: Ryth 52% vs our 28%, Vendetta 41/22, Heart of
  Ruin 46/26, Marcella 38/22, Vesper 26/13); their first Bruiser is Health far more often (Ryth 274/320 vs 55/143);
  top Prisms open Durability-Health (68/85), ours Monster-Focus (327/592). `best_emblem` values Health only through
  fewer heal trips (`upkeep_cost`), never fights survived. Treasure in Health on Ryth, Vendetta, Marcella and Heart of
  Ruin (8e53ec9): 49.0% (gold earned -5-10%, deaths unchanged); first Bruiser in Health on those (5f91ee8): 50.2%.
  Out-of-fuel turns level. Dropped (that suite rarely drafted Vendetta; on Vendetta alone, with our 3-pick draft, it
  won: [Vendetta](#vendetta-2026-10-24-astraeus-on-its-3-pick-draft-marcella-vendetta-hor)). If retried: a
  fight-survival term for Health in the emblem model, judged against v37 or on the ladder, not a stat fixed per
  champion.
  Retried for Prism as that term (`b3-fight`, 2026-10-24): `upkeep_cost` adds deaths a turn x (respawn + walk out +
  2 x mean bag x `rounds_per_gem`) x P(now)/P(build), P = output x max health / damage taken at the mean bag's Focus
  (ladder fights: log-odds ~2 per unit log ratio of either, so at even odds deaths fall in proportion to P); deaths
  counted from 1 per 1000 alive turns. Prism bought Health (ladder suite r1000: 2404 vs 1570 max health, deaths 1.00
  vs 1.26 a game) but against 5d43ecf: 50.4% of 1104 (47.4-53.3; ladder 53.8, gen 51.2, gen-s1 49.0), out-of-fuel
  turns 2693 vs 2486. On top of CHANGES 123's shop fix (`b3-shopfight` against `b3-shop`): 50.8% of 1104 (47.9-53.8;
  ladder 56.2, gen 51.2, gen-s1 49.6). Dropped; not extended to the other champions. Self-play may hide it (both
  sides share the build), so a ladder read is the remaining test.
- Every champion's shop trip on CHANGES 123's whole-purchase price, as Prism's (`b4-shop`, 2026-10-24): `wants_shop`
  without the non-Prism gates (next emblem affordable or begun, `home_trip().short_gold == 0`). Against acbcbcb:
  50.1% of 1104 (47.1-53.0; ladder 47.5, gen 50.6, gen-s1 50.0), out-of-fuel turns 2259 vs 2344. Gold held did not
  fall (mean while alive, ladder suite: Marcella 82 vs 82, Heart of Ruin 36/38, Vesper 35/39; gen 72/71, 32/33,
  37/40): the trip's price (`affordable_prefix` gain against recall + walk back), not the gate, keeps Marcella's gold.
  Dropped.
- Vesper keeps a shared gold hold (`b4-vhold`, 2026-10-24): top teams' Vesper earns 42% of team gold, ours 29%.
  `holding_capture` left a shared hold to the lowest id; it now ranks a Vesper (not tributing, teleporting or
  landing a recall) first on a group that pays gold, so her +33% covers the whole share. Our draft picks Vesper
  second, so it only changes Vesper against Prism when `prism_capture_holder` declines (traced: 17 turns in 3 games).
  Against acbcbcb: 48.9% of 1104 (46.0-51.9; ladder 47.5, gen 49.0, gen-s1 49.0), out-of-fuel turns 2325 vs 2408.
  Dropped. The id order is not why our Vesper earns less.
- Why our Vesper earns less (2026-10-24, the 320 v47 ladder games' events and traces; no build). Not a claim bug:
  - We take more base capture gold than the top teams (4,993 a game against 4,481) and as much by r200 (714 vs 705).
    The gap is how it is split. Our Vesper's share of base capture gold is 24% whatever the group: big (150+ gold),
    mid or small, gold-heavy or gem-heavy. Prism takes 28%, the most. Their Vesper takes 28% overall and 32% of big
    groups. Their Prism (in 79 of the 320 games) takes 6%.
  - Claims are first come: each champion takes its own best group, and farm values gold with its own bonuses
    (CHANGES 104). Nothing gives a contested gold-rich group to Vesper for her +33%. Moving 16 points of base gold
    to her would be about +260 gold a game (~4%). Vesper first on a shared hold (above) lost.
  - Banking is the bigger difference in champion time. Our Vesper, Marcella and Heart of Ruin tribute 7-8 times per
    1,000 rounds at 23-28 gems each; the top teams' do it 3-5 times at 35-48. Our Vesper spends 19.5% of her turns
    banking (Prism 2.3%) and 55% farming. This is the known small-bag finding ("Banking small bags only for nearby
    enemies" above, held/dropped), not Vesper-specific.
- Middle kills on large maps (2026-10-24, v47 traces against the top 6: 203 enemy deaths in the middle, not to camps,
  in large-map losses). Not a dead-enemy bug: Safety (`safety.cpp`, enemies with `!alive` skipped) and the pack zone
  (`alive && age <= 1`) drop a dead enemy at once. Farm choice has no live contest term at all, only the static
  `home_ground` discount, and `respawn_earliest` is written but never read.
  - In the 40 rounds after such a death our survivors' farm target is a middle group on 65% of turns (wins 67%,
    small maps 66-83%). What differs is retreat: `d=R` 9.4% vs 5.3%, `outmatched` 4.6% vs 1.8%.
  - Middle capture gems per death, us vs them: within 8 tiles of the kill, 7.7 vs 3.7 in the first 30 rounds and
    5.0 vs 11.0 in rounds 31-60. Elsewhere in the middle, 4.9 vs 12.1 over the first 60 rounds, all while the victim
    is still dead. We take the fight's own group. Their other four then out-capture our survivors, who target the middle
    as often as in wins, so this is fight strength (finding #1 of the large-map report, the pack zone), not targeting.
  - Enemy-ground discount scaled by who can arrive (`b6-dead`, against 95d47b0). `farm` kept the discount
    `1 - home` only for the share of enemies that can stand on the group by our payout. A dead enemy arrives at
    `respawn_earliest` plus `enemy_steps(g)`, and our payout is steps + wait + fastest clear + capture. No constants.
    It fires as meant: a debug trace of 4 large-map games picked a lifted group on 98 of 2,033 farm turns with an enemy
    dead, lifts 1.01-1.35. 49.9% of 1104 (47.0-52.9; ladder 46.2, gen 52.1, gen-s1 48.2). Large maps (area
    2500+): 51.0% of 698. Out-of-fuel turns 2458 vs 2372. Dropped: level as a strategy change.
- Not a bug: on a leave turn `decide` casts `shield_if_needed` before `retreat`, but skips it when `strike_possible`
  and `reset_may_kill || landing_ready`; Heart of Ruin's dash lands, so with it ready and an enemy within 5 (every
  step-to-kill dash) the shield already waits, and Varg has no dash (its reset kill is `reset_may_kill`).
- From the teammate's v40 (`origin/codex/willow-prism`), ported together (`port/v40-bits` 15d87ae, 2026-10-23): a
  Prism refusing a camp attack whose wakes would hit an ally holding a capture, recalling or tributing, or kill one;
  a healthy Vesper on a cleared gold-only group with no enemy seen holding it so her +33% applies. Against eba051e:
  49.7% of 1104; against v37 on own drafts 68.1% (main 67.3%); out-of-fuel turns level. Rare: in 6 local games the
  wake check vetoed 28 attacks (all for a recalling or tributing ally), the Vesper hold fired in 1. Not merged.
  The wake check alone (`port/wake-check` 8ac57a2) against e5a5d13, own drafts: 51.4% of 1104 (ladder 55.0, gen
  48.6, gen-s1 53.5), out-of-fuel turns level; on a fresh suite (seed 2718, 512 games) 48.4%. Dropped.
- The teammate's Willow code (v40 0500905, v41 ff250ad: ~1,140 lines of bot code) is not ported: our draft never
  picks Willow (1 of the 30 test compositions does), its evidence is level (v41 808-808 against v40), and it raised
  out-of-fuel turns ~50% with Willow drafted. Port it only alongside a draft that uses Willow. v41's dense-map 5-pick
  draft (Vendetta for Heart of Ruin) runs against CHANGES 102's evidence.
- Step then teleport (`fu/step-teleport` 1cf1047, 2026-10-23): `crystal_across` also takes landings 4 away by stepping
  to a safe neighbour first. In 18 traced games on the teleport maps a one-step-away landing qualified on 269 turns
  when none did from the current tile, but 71 were crossed next round anyway, 74 within 2-12 rounds, and when both
  qualified stepping was usually 1 step better. Teleport class suite: 48.6% of 512 (44.3-53.0). Dropped.
- Teleporting enemies (untested gaps, 26946fc): only `world.cpp` widens a teleporting enemy's `possible` to tiles
  within 3; nothing reads its known landing (`teleports_into`, used only by pathing). Safety and the fight search treat
  a channelling enemy as able to act from its tile; `prey`/`intercept_steps` ignore `channel_end_round`; stun
  targeting values cancelling a tribute but not a teleport; `World::grow` spreads `possible` though the channel pins it.
  Fixed on `strat/teleport2` (cafa84c, on teleport base 8dbc020): a seen teleport lands at its reserved tile at its
  turn start in `channel_end_round` and acts that turn, in safety, the fight search, `prey`/`intercept_steps`, stun
  value and tracking. Locally rare (visible enemy teleports per team-game: 1.2 on the teleport class suite, 0.47
  ladder, 0.09 gen), so the A/B is level: with the crystal rule below, 50.5% of 1104 against 8dbc020, class suite
  50.6% of 512. Merged alone, without an A/B, as CHANGES 106 (7581f1c).
- Crystals only on maps with shortcuts (`strat/teleport2-buy` 1355c53): the draft samples the map and champions buy
  no crystal with fewer than 4 shortcut tiles unless an altar hop needs one. Its estimate of unused crystal gold
  (32 → 25.5 per team-game ladder, 36 → 24 gen) assumed crystals are lost at death, from 5.5 buys per team-game on
  maps with no shortcut use; `probe-death-items` shows they are kept, so those buys follow crystals spent some other
  way (altar hops, uncounted uses) and the waste figure is unreliable. 49.1% of 1104 against 8dbc020. Dropped.
- Audit judgment calls not kept (2026-10-23, against 586586c): an unseen enemy keeping its last-seen health after an
  assumed recall instead of full (`p2/recall-health` f5ae7f4): 48.4% of 1104, dropped. Held: dropping our own winning
  tribute to stop an enemy tribute that lands first, unless a visible ally acting in time can stun it or lock its
  altar (`p2/intercept-first-main` 99248f8): 50.5% of 1104 (47.6-53.5), but both teams near 1000 at once is too rare
  locally to measure; a logic call, not a measured one. Ported to astraeus as CHANGES 126 (49.4% of 1104).
- Recall out to farm (2026-10-24, `bots/hermes`, uncommitted, astraeus at 90e2e0d): empty-handed, farm prices a
  group's arrival as min(walk, `recall_turns` + 1 if hurt + steps from spawn), the from-altar leg likewise, and
  `continue_recall` keeps the turn-end recall while that still lands sooner (`recall_to_farm`: unthreatened,
  `recall_outruns`, not just waiting out a respawn). Ladder maps only, own drafts against astraeus: 47.5% of 80
  (36.9-58.3); 32 maps split, won both 3 (great-wall, monolith, elk-arena), lost both 5 (gem-fields, gemfight,
  pilgrimage, rushbait-v2, swirl). 519 kept trips, 94% landed; the 29 cut short cost 48 standing turns. Not judged:
  needs the full `ab.py` run.

## Draft (2026-10-24, astraeus against top-10 team proxies)

Details and the per-team table in [hyperion/DRAFT.md](hyperion/DRAFT.md#astraeus-draft-search-2026-10-24).

- 3 picks: Marcella Vendetta HoR over Prism Vesper HoR, +16.5 ±6.5 on all maps, +17.3 on a fresh suite (CHANGES 134).
- 4 picks: no single swap beat Prism Vesper Marcella HoR; Ryth for HoR -8.7 ±6.7 on all maps.
- 5 picks: Tavi or Ryth for Prism level on all maps and on the fresh suite; every other single swap level or worse.
- Counter picks: no matchup difference beyond noise, so no rule.

## Comms packing (2026-10-25, astraeus)

`bots/variants/ast-comms-sight2` against astraeus 2289c90a (`bots/variants/ast-head-2289c90`), one A/B of all of:
shared-memory records sized from the map and team sizes (mixed radix; the respawn round mod the group's respawn + 17);
priorities renumbered to a 12-bit order-preserving rank code with 7 - ally index below it and a 16-bit payload (raw 0
stays 0 and every other priority keeps its sign: bots read unseen champions as priority 0, and hecate played differently
until this held); each ally's claim and the Prism/Willow support intents in that payload; a second enemy sighting
sharing the camp slot, a capture winning it.
- 49.9% of 1104 (47.0-52.9; ladder 47.5, gen 49.6, gen-s1 50.6). Out-of-fuel turns 2831 vs 2699.
- The packing and renumbering alone play identically: 104 bench games (wide set, own and test drafts) the same but for
  the replays' `prio`; +160 fuel a turn (median).
- Claims read from priorities matched the ally's own in all 12260 reads on 00contest; the slot's differed in 5.5%.
  Received second sightings matched the enemy's true position in 99.8-100%; 00contest gets ~75% more sightings.
- Neither version found a valid support message when asking on four Prism/Willow maps: support is barely exercised.
- `probe-fuel-ops`: a 64-bit division or remainder costs ~3.5 fuel more than a multiply.

## Patch 2.0.0 (2026-10-25, astraeus)

b33ae780 (CHANGES 148: 2.0.0 stats, emblem values, enemy Skirmish/Collectors, engine capture timers) against
e45ab0bd's astraeus (1.x tables), both on engine 2.0.0 with own drafts: 53.5% of 652 (49.7-57.3; ladder 52.1 of 140,
gen 53.9 of 512). Out-of-fuel turns 2423 vs 2399. No failed matches.

## Edge-case maps (2026-10-25, astraeus)

astraeus 71e3e19 against v44, own drafts, on the regenerated suites (gen 1029, gen-s1 1030): 56.3% of 1104 (53.4-59.2;
ladder 53.8, gen 58.4, gen-s1 54.7). By class (`tools/ab_classes.py`):

| Class | Games | Win % | To round 2000 |
|---|---|---|---|
| access teleport | 68 | 50.0 | 13% |
| access dash | 64 | 60.9 | 27% |
| gated | 20 | 55.0 | 0% |
| spawn 4x3 | 38 | 36.8 | 0% |
| camp_mode rich | 34 | 35.3 | 6% |
| camp_mode jackpot | 26 | 69.2 | 81% |
| camp_mode poor | 72 | 59.7 | 53% |
| gem-drought | 8 | 62.5 | 100% |

- The weak classes with no edge-case cause: the 4x3 losses are spread over hole-heavy maps (islands, great-wall,
  archipelago) and the "rich" losses are fight maps (arena, farmland, three-lane). Not pursued.
- Tiebreaks are fine: in 107 games to round 2000, our carried gems at the end would have flipped one result.
- The cause was stalls (`tools/replay/stalls.py`). The fixes are CHANGES 145-147.
- Mirror A/Bs hide stall fixes: both bots stall in the same places, so the fixed side wins one game and the other side
  usually the other. Each fix read level against 71e3e19 while its stalls were gone; against v44 the class rates
  moved (teleport 50.0 -> 64.7).
- A rare path's A/B reads ~50% because most games are untouched: in a mirror A/B a map whose two games end on the
  same round played identically. Count the maps that differ and read those (CHANGES 171: 11 of 326; 172: 7).

Tried and dropped:
- A contest anchored to its group's tiles on every hold, not only contested ones: 49.4% of 1104, standard class 47.2%.
- Farm hops into the enemy's walk region: fed kills on archipelago-103002013, -103002025, -102902027.

Open (not fixed):
- 1v1 contest standoffs: one champion of each team on a cleared group's tiles, neither attacking, for ~900 rounds
  (gen-far-spawns-102904903, 01yellow-brick-road's gold row). Symmetric against our own bots.
- Farm starved of fuel on big mazes (gen-huge-shared-102905203, 93x93): the target's field is estimated at 51k, so
  the farm loop breaks before it every turn and the approach search fails each turn. Both bots.
- Farm hops: a walker in a pocket cannot retreat (damage cancels the recall), so a pocket camp fight or a region the
  enemy reaches by crystal costs deaths (01shortcut's hole ring at r94, gen-archipelago-102902015); a champion whose
  only options need a crystal has no gold while an ally claims the gold camps (gen-archipelago-103002007); once
  `wants_crystal` is set every spawn visit rebuys one before shards. Bank hops now check the source and landing
  (CHANGES 172).
- Stampede: Prism spell-kites a 7480-hp group alone at one AoE a cooldown (~750 rounds to clear).

### DRAFT-COMPUTE #2 and #3 (2026-10-26, astraeus)

- #2 chokepoints, stopped: dead-end pockets reachable on foot die at the base rate (x1.04 against the rest); the
  excess is off-foot islands, x21.8, 12% of deaths ([chokepoints.md](hyperion/draft-compute/chokepoints.md)).
- #3 maze portals, not built: 1 of 582 maps has a full field over ~40k. 61% of routing SHORTCUT lines came from 4
  games on 2 maps whose walks exceed the approach search's width + height cap; the cap fix (CHANGES 158) read 50.3% of
  1164 and 50.0% of 96 winding maps, stalled champion-games 17 -> 8 ([portals.md](hyperion/draft-compute/portals.md)).

### DRAFT-COMPUTE session total (2026-10-26, astraeus, CHANGES 155-163)

- main ef5ca17 against the session's start f3f47ea, own drafts: 52.1% of 1164 (49.2-54.9; ladder 49.3, gen 50.0,
  gen-s1 54.9), and 53.6% of 280 on 140 unused ladder mutations (`mapgen mutate random`, seeds 26101-26250);
  pooled 52.4% of 1444. Out-of-fuel turns 4406 vs 5612 and 1663 vs 2086 (-21%).
- At ca1139b (before 162-163) the same A/B read 53.4% of 1164 (ladder 45.0% of 140) and 55.4% of 280 mutations: the
  ladder dip did not hold on its mutations.
- Kept: plan v4-v7 (header 160 -> 80 bits), the ward plan (159, the only drafted section that won alone), the farm
  order (157), the walk cap (158), comms urgency (162), first-turn fuel (156, 160, 161, 163). Not kept: drafted group
  distances (#1), chokepoints (#2), maze portals (#3), the opening schedule (#5).
- Round 1 over the session (wide bench): mandatory work 244k -> ~174k mean (100M), round-1 turns that run out at the
  real budget 59 -> 18 of 241.

### DRAFT-COMPUTE #5, the opening schedule (2026-10-26, astraeus)

- Not merged (f96ea98a on `worktree-agent-a40911bd838aaa775`): simulated annealing in the draft over each body's first
  jobs against our greedy farm rule reacting, sent as group indices (median ~8-22 bytes, ~2k decode in round 1).
- Bonus in the farm, ending at the first deviation: 49.7% and 51.1% against 80db5f7/801ed7d, 53.2% against m160,
  49.0% of 512 on an unused suite (seed 7171): level. Strict (scheduled entry as the farm's target): 45.4%, then
  46.9% after calibration; -3.4% gems captured by round 300.
- Calibration (real job sequences replayed through the model, rounds 1-300): before first contact 88% of gems and a
  9-10 round median timing error, the model's greedy 102%; over 300 rounds 77% and 23 rounds. A mirrored enemy hides
  denial (both sides score the same by construction); a fixed enemy timetable lost 17% once the enemy reacts.
- Why: the search finds plans the model overrates (+26% predicted over its greedy, -1.5% in a near-identical Python
  model). Residuals are fights after contact, re-timing a fixed list around respawns and holds, and risk-based
  banking ([schedule.md](hyperion/draft-compute/schedule.md)).

### DRAFT-COMPUTE #4, the ward plan (2026-10-26, astraeus)

- Kept (CHANGES 159): one drafted ward tile per camp group and altar, scored by shadow casts at radius 6 over the
  enemy-standable tiles the site's champion cannot see; greedy bush wards as the fallback. 52.1% of 1164 against
  80db5f7 (49.2-54.9), 52.5% of 512 on an unused suite (seed 61026). Wards 18.0 -> 28.2 a champion a game, surprise
  deaths 0.109 -> 0.082 a champion a game. Out-of-fuel turns +7% on the unused suite (2090 vs 1952), level on the main
  A/B: not traced ([wards.md](hyperion/draft-compute/wards.md)).
- Rejected before building: a team-wide coverage plan (ward sight is personal: 34 of our 80 bush-ambush deaths were
  under a teammate's ward); variable-width or Rice-coded entries (a lookup would need a decode pass).

### Ward sight and comms urgency (2026-10-26, astraeus)

- Kept, level (CHANGES 162): comms post the enemy most urgent for a teammate that may not see it, and replace a less
  urgent sighting a teammate posted this round. 49.4% of 1164 against `astraeus-m160` (46.5-52.3), own drafts;
  victims who knew their killer at their last turn 36% -> 41%, within noise. Urgencies in `send()` with a shadow cast
  per enemy read 48.7% and ran out of fuel at the turn end (send has ~1.5k to spare); listing allies eagerly at the
  turn start rerouted boss-battle via an earlier round-1 run-out ([ward-sight.md](hyperion/draft-compute/ward-sight.md)).
- Ward sight already reaches every decision (Safety, `want_home`, `tribute_safe`, `track()`'s absence evidence,
  comms). The measured gap was which enemy comms posts: in 113 of 173 teammate turns that saw a later killer, both
  slots were already taken. Ceiling ~2% of deaths.
- A ward placed in the same turn just before a tribute start revealed a new enemy 35 times in 1164 games: judging a
  tribute after the ward is not worth a change.
- The ward plan's +7% out-of-fuel turns on its unused suite (above) is most likely A/B-to-A/B spread: the same REF
  (`astraeus-m160`) read 4087, 4458 and 5716 out-of-fuel turns across three A/Bs of near-identical candidates. Only a
  new phase or a paired replay shows a real cost.

## Map suites regenerated with designed scenarios (2026-10-25, gen seed 1029, gen-s1 seed 1030)

`maps/gen` and `maps/gen-s1` were rebuilt by the reworked mapgen (tools/README.md):
- Designed scenarios (atoll, gatekeeper, fortress, ...), dash- and crystal-only objectives, economy extremes, and
  seeded random ladder mutations.
- Results before this date are on the 1027/1028 suites and don't compare directly.

Same bots on old and new suites (gen + gen-s1, 1024 games each):

| Pair | Old suites | New suites |
|---|---|---|
| main d5425b6 vs v44, own drafts | 49.1% (46.1-52.2) | 52.1% (49.0-55.1) |
| main vs v44, main on test drafts | 30.6% | 35.2% |
| main vs hecate, test drafts | 81.1% (78.5-83.3) | not run |

- `ab.py` with a bot directory leaves its `params.h` alone: v44 has `test_draft = false`, so without `--no-test-draft`
  main plays test drafts against v44's own (the 30.6% row).
- On 26 games of the hardest new maps (atolls, gates, vaults, 5x2 spawns), main beat hecate 20-6 with no failed
  matches.
- Atoll games ran to round 2000, one side tributing 0 of 118 gems collected: our bots don't take a treasure island
  reachable only by dash or crystal.

## astraeus against our bots on fresh maps (2026-10-25, gen seed 1027, gen-s1 seed 1028)

astraeus 288d98db (CHANGES 140) against hyperion cfd1a3a1, hecate, v49 and v44: ladder (80), the newly generated
`maps/gen` and `maps/gen-s1` (512 each), both sides, 1104 games each. "Old 3-pick" is `bots/variants/astraeus-olddraft3`,
astraeus with Prism Vesper HoR on 3-pick maps (before CHANGES 134); 4- and 5-pick games came out identical in every pair.
"hecate own" is hecate with `test_draft` off.

| vs | astraeus | 3-pick (378) | old 3-pick | 3-pick (378) | 4-pick (358) | 5-pick (366) |
|---|---|---|---|---|---|---|
| hyperion | 55.4% (52.5-58.3) | 62.4 | 52.8% | 54.8 | 49.7 | 53.6 |
| hecate own | 89.8% (87.8-91.4) | 90.5 | 86.2% | 80.2 | 89.1 | 89.6 |
| v49 | 53.3% (50.3-56.2) | 59.3 | 50.9% | 52.4 | 48.3 | 51.9 |
| v44 | 57.6% (54.7-60.5) | 60.8 | 55.3% | 54.0 | 53.4 | 58.2 |

- Marcella Vendetta HoR beats Prism Vesper HoR by 7-10 points on 3-pick maps against all four, short of the +16.5
  against top-10 proxies.
- On 4-pick maps astraeus is level with hyperion and v49: its lead over them is 3-pick maps.
- v49 still wins the ladder maps: astraeus 37.5% of 80 (27.7-48.5), old 3-pick 40.0%; mostly 4- and 5-pick maps.
- Against hecate on its test drafts astraeus wins 93.1%; hecate's own draft does better.
- Out-of-fuel turns: astraeus more than each bot but v44 (vs hyperion 2733 against 1749; hecate own 3278 against 1009).
- 2026-10-26, astraeus 89d756a0 (CHANGES 172) against hyperion b33ae780, own drafts, on the 2.0.0 suites (gen 1201,
  gen-s1 1202), 1164 games: 58.7% (55.8-61.5); ladder 43.6% of 140 (35.6-51.8), gen 60.7%, gen-s1 60.7% (different
  games, the same 311-201). Out-of-fuel turns 4564 against 2259. The lead is still all on generated maps.
  astraeus 25d45679 in the same setup: 56.1% (53.2-58.9); ladder 44.3%, gen 55.3%, gen-s1 60.2%; out-of-fuel turns
  3905 against 2144. The 36 astraeus commits since then add ~2.6 points against hyperion, all of it on gen.

## eris: macro strategies for a sparring partner (2026-10-25)

eris, a copy of astraeus 5a0dbb98, against frozen copies of astraeus and hyperion at 5a0dbb98, own drafts, 1104
games each (ladder 80, gen 512, gen-s1 512). Goal: 60% against astraeus, astraeus's own hyperion score + 10 against
hyperion. Baselines: 50.0% (identical code) and 58.3%. The bot and the `spar/*` branches were not kept; the shas below
are their commits, unreachable once garbage-collected. Win % below is against astraeus unless noted.

- Where astraeus-vs-hyperion games are decided (1104 replays): 94.5% end at 1000 gems; the leader at r300 wins 62%,
  at r600 70%. The team with more kill gems wins 88%, more middle captures 78%, more enemy-side captures 80%. 58% of
  deaths are in the middle. Champion time: walking 31% + walking with a bag 20%, hitting camps 18.5%, holding 9.4%,
  idle 7%, dead 5%. Both teams spend 2.4% of their time on enemy ground, and ~42% of each side's own gems sit asleep
  at any moment.
- Kept in eris as map-class gains (the rule: confirmed on a fresh suite, nothing lost elsewhere):
  - **Monolith bursts** (bb9c237e): the team stages at one anchor, followers trust an ally's burst call,
    a siege leaves only past a farther healthy ally, and a burst starts only if a recall plus the walk back fits inside
    it. Monolith maps (136 maps, 272 games) 54.4% (mirror 50; Monoliths 0.71 a game vs 0.06), fresh Monolith suite
    56.6%; all suites 51.5%, vs hyperion 59.0%. Found: Heart of Ruin never joined a siege (the `low` check wanted six
    hits of health).
  - **Crystal travel** (e8e415f3): hyperion 37bbf44's crystal hops plus a crystal right after a step,
    gated in the draft (`scan_crystal`) to maps with 5+ tiles where a landing is 10+ steps nearer spawn or an altar;
    other maps play exactly as astraeus. 50.7%, vs hyperion 59.1%; ~55% on maps where a crystal saves 15+ steps a
    cycle. Supply binds: one carried crystal, rebought only on spawn.
  - Merged (02da5722): 51.0%, vs hyperion 60.1% (gen 63.5); fresh Monolith suite 57.0%. On Monolith maps that also
    pass the crystal gate the merge read 47.7% against 53.5-55.8% for each alone (86 games); no mechanism found
    (no crystal use during a burst), within noise.
- Level or lost (best version shown; none reached 52%):
  - **Contesting enemy capture holds** (750280ce, 4 versions, best 50.6%): `contest_capture` without the
    vision + 2 limit, groups an enemy is still clearing, tiles out of melee holders' reach. Fired ~2 times a game; equal
    fights read as lost in ~70% of checks. Arriving while the enemy was still clearing gave 10 kills and 0 deaths in
    16 traced games; arriving at holds mostly gave them the capture. Enemy camp damage in the fight sim: 49.9%.
  - **Team hunt of enemy carriers** (3e17bc88, 5 versions, best 49.5%, vs hyperion 57.7%): bags shared in comms,
    hunt claims with a caller plus two. ~26 hunts a game, ~7% killed the carrier, camp damage and gold -7%. Kill rate
    4.5% with no ally near, 16% with two; carriers retreat at a 2.5 ratio once a pair shows. Tributing carriers die
    1-3% of the time. A bag record in the camp slot (d1f3dfbe) stops pushing out the second sighting on ~85% of maps.
  - **Power-play windows** (9cfaae1f, 5 versions, best 50.7%): farm front line moved by live numbers, chases with
    the numbers. Both bots already push when ahead (middle and enemy time 32% -> 45-53%); a dead enemy is back before
    an enemy-side clear and capture finish.
  - **Duos** (749ccb4d, 5 versions, 31-48.7%): worse the more of the team is paired. Fewer parallel jobs and two
    walks a group (ladder 634 vs 836 gems a game); eris died more while locally ahead (2v1: 49 deaths vs 31); in half
    of those an ally within 4 hit nothing. "Join your mate's fight": -2 more.
  - **Predictive ambushes at enemy farm targets** (bf018b44, 5 versions, best 50.1%): astraeus's claim leaks in
    its priority's low byte (90% match the group it stands on; hyperion's do not match). Loose versions fired ~33 times
    a game with 5% kills; tight ones killed without losses but fired ~3 times. Waiting in bushes: level.
  - **Zero-sum denial in farm value** (85189549, 3 versions, best 50.5%): worth + q x gems, q the chance the enemy
    takes the group. Our middle share rose 0.50 -> 0.59 but astraeus's captures did not fall (its farmers take idle
    home groups); our own captures fell and deaths rose. Middle share follows strength; side weighting looks
    rate-optimal both ways.
  - **Initiative-aware fight verdicts** (9d149c4d, 6 versions, best 51.7%, vs hyperion 56.3%): `stand`,
    `prey` and `step_guard` play the fight with us first when our blow reaches. Fights we open convert 32% (13% when
    enemy-first) but are ~3 a game; we strike first in 23% of in-reach verdicts. A won first-strike verdict overriding
    the pack zone doubled deaths. Stacked with steal and ambush: 51.8%, out-of-fuel turns +60%.
  - **Champion-time audit** (b868d12e, 4 versions, best 50.6%; debug `AUD` trace per champion-turn): ~4,480
    champion-turns a game: empty walking 27%, camp hits 17%, ~40 recalls a game (27 during holds; 10.6 of those only
    for the emblem value). One champion takes 98% of shared clears' camp hits. Bank trip in job value: level; heal cost
    for camp damage in job choice: 42.2%; no heal value in hold recalls: 47.5%; Willow tending: 49.1%.
  - **Relocating instead of a pack-zone retreat** (1a876612, 5 versions, best 50.5%): retreat and farm flip at
    the zone edge (32 stalls, 122 turns a game). Avoiding the pack's groups cut stalls but camp hits stayed ~765 a
    game; sideways steps let packs close in (deaths up).
  - **Survival** (bdacc438, 4 versions, best 49.2%): 4.1 deaths a game; carriers
    0.60 (Prism's kept bag is 70% of gems lost), healthy deaths to bursts, chases or lost stands 2.4. Prism banking past
    the bag that doubles its Focus: 47.4%. Recalls kept only when no seen enemy arrives first: 48.9%. The pack zone
    remembering unseen members 3 rounds: 49.2%, deaths 3.98 vs 4.19 but rounds away from the work cost as much.
  - **Monolith round 2**: any-side Monoliths 54.4% (= v5), our side only 52.6%, skip a shared
    central one 52.9% (Monolith suite). Bursting Golems or Elks with more champions never cost less health a gem
    (Golem 1163 hp a clear alone, 1397 with two).
  - **Bursting a map's big shared group** (2d84340c, stopped early): 36.6% (v1) and 42.7% (v2, kite maps left
    alone) on 82 class games, 41.9% on 160 fresh. Lost.
  - Stopped before an A/B: fleeing toward an ally's claimed group when chased (12053161, WIP).
- What the level results share: against a near-mirror, anything that takes champions off farming costs about what it
  gains, and every fight model reads equal fights as lost. Gains came only from map classes with value both bots
  leave (Monoliths, shortcuts), decided once from the map. The largest known lever, composition (the 3-pick draft:
  +7-10 against every bot), was not tried. eris ends at 51.0% / 60.1% against targets of 60% / 68%.

## Ladder-analysis ideas (2026-10-25, astraeus)

From [ladder-analysis-2026-10-24.md](ladder-analysis-2026-10-24.md). Each against astraeus 3f8e75e
(`bots/variants/ast-ref-3f8e75e`), own drafts, 1104 games (ladder 80, gen seed 1027, gen-s1 seed 1028) unless noted.
"Fresh Monolith maps": the 130 Monolith maps of fresh suites seeds 4417 and 6151 (260 games). Branches
`exp/prism-treasure`, `exp/monolith`, `exp/kill-progress`.

- **Prism Treasure first** (`best_emblem`'s Prism branch falls through to the Treasure rule): 49.5% (46.5-52.4); 4- and
  5-pick maps (Prism is not in the 3-pick draft) 49.2% of 722. Prism spent 1142 gold a game against 970 but banked 83
  gems against 102 (others 721 against 730): Monster-Focus's camp damage was worth more than the gold. Dropped; river
  read 49.2% for the same opening.
- **Heart of Ruin out of fuel in fights**: not fixed. Ladder games after ~15h UTC (CHANGES 131-133 live) 2.35
  out-of-fuel fight turns per HoR game against 1.99 before; locally 1164 in 500 games (other champions 12-88), 58% right
  after a dash landing. Metered (`debug_fuel` plus meters in decide): on a spilled turn the world update costs ~27k,
  `want_home` ~47k and the strike search ~49k (medians; up to 337k over several turns). This is TODO "Next" 2-3
  (shield-kit fight sims, one danger model), not a separate bug.
- **M1, a burst on a low Monolith** (9fce3fd4): off Monolith-only maps a live Monolith whose known health the team
  clears within `burst_rounds` (20) is sieged; and `siege_heal_trip` no longer recalls once the group is cleared (a
  smoke game lost a game-winning 200-gem capture to it: all three of ours recalled at 54-62% after the clear).
  50.5% (47.6-53.5), Monolith maps 53.0% of 270; fresh Monolith maps 51.2% of 260 (45.1-57.2). Monolith captures 208
  against 121, but REF took 22 we did most of the damage on: burst members left one by one at low health.
- **M2, solo chipping kept above the burst line** (1c67e1d3, on M1): one champion chips an own-side or middle
  Monolith alone while a visit beats the farming rate (`chip_pays`, from about r420), never below the burst line;
  bursts wait for 60% of the team's output with no solo fallback (dropped after `siege_max_wait`); under the line a
  sieger heal-trips only past a healthier ally on it; an ally's Monolith claim is joined only with an enemy believed in
  reach. 49.5% (46.5-52.4), Monolith maps 49.3% of 270. Against M1, the sniper it was built for, on fresh Monolith maps:
  43.8% of 260. M2 captured 273 Monoliths to M1's 246, but M1 took 47 that M2 had mostly damaged (M2 took 13); of the 34
  traced, 15 were left under 2000 hp (mostly after team visits), 15 at 2000-8000, 4 above. An equal enemy's burst line
  is our own, so a floor at ours is theirs to burst.
  - M2b (dbac289b), chip only while our output is at least the enemy's: 43.5% of 260 against M1.
  - M2b without chipping (the waits and holds alone): 47.3% of 260 against M1. Chipping costs ~4 more on its own: a
    champion off farming for visits worth ~2-4k each. Lost; M1 stays the Monolith candidate.
- **Kill progress in hit value** (cb990dc2): a hit is worth the fall in `kill_distance(health) = 0.4 health +
  (0.6 full + life + bag) sqrt(health / full)` (path-independent, so the strike search's order assumption holds; a
  kill from full health is worth full + life + bag as before, chip damage ~0.8x at full health and ~1.3x at 20%).
  52.4% (49.4-55.3; ladder 62.5, gen 50.4, gen-s1 52.7); fresh suite seed 4417 49.0% of 512; pooled 51.3% of 1616.
  Ladder maps and their mutations (`mut-*`) 56.8% of 278, other generated maps 50.1% of 1338. Deaths a game 4.77
  against REF's 5.29 (camp deaths 0.45 each). Out-of-fuel turns +9% (2814 against 2577).

## Magic numbers and special cases (2026-10-25, astraeus)

CHANGES 142. Each batch against astraeus 9328116 (`bots/variants/ast-ref-9328116`), own drafts, 1104 games (ladder 80,
gen 512, gen-s1 512); kept batches in CHANGES.

| Batch | Win % | 95% CI | OOF cand / ref |
|---|---|---|---|
| Corrections (gold share, camp factor, kill tests, no healthy pack ratio) | 49.5 | 46.5-52.4 | 2858 / 2918 |
| Arrival tests, together | 48.4 | 45.4-51.3 | 2857 / 2859 |
| - paying_soon by arrival | 51.1 | 48.1-54.0 | 2858 / 2887 |
| - holds by reach, travel dash by reach | 47.7 | 44.8-50.7 | 2793 / 2885 |
| - holds by reach, travel dash clearance kept at 10 | 50.9 | 48.0-53.8 | 2793 / 2716 |
| Special cases generalised | 49.8 | 46.9-52.8 | 2980 / 2979 |
| Values (stun = output, camp floor = cast_cost) | 50.3 | 47.3-53.2 | 2740 / 2871 |
| Monolith holders, gold-rate handoff | 49.8 | 46.9-52.8 | 2888 / 2768 |
| All kept, + fresh suite seed 7319 (1616) | 49.9 | 47.4-52.3 | 4325 / 4048 |

- Lost: the travel dash's clearance (10, kept as `vision_radius + dash_range`) as each enemy's strike reach + the dash
  (`engagement_near(here, 0, dash_range)`): it dashed past closer enemies; -3 with the holds, which alone are level.
- Fuel: identical-game fuel against the reference is +0.2% (~100 a turn) in the 10 bench games still played identically;
  each batch alone was within 0.04% but the gold-rate one, whose per-turn Treasure read (+0.20%) now happens only in
  the handoff. Out-of-fuel turns +7% in the all-kept A/B, level in each batch's.
- Left as tuned: `min_landing_value` 250 (stands in for the landing's unpriced exposure: the strike search's dash cost
  would make it ~45), `brake_bag` 11 (tuned for gem rewards, not tribute length), `big_gems` 55 (golem + elk + wolf),
  the `width + height` endgame walk bounds (no Pathing at their 9 callers), `escape_step_value`, `rounds_per_gem`,
  `cycle_horizon`, the siege and Monolith params, `life_value`/`gem_value` (the priority code assumes their residues).

## Magic numbers, phase 2: rule-derived fixes (2026-10-26, astraeus)

Each against astraeus 25d45679 (`bots/variants/astraeus-25d4567`; CHANGES 152 plays identically), own drafts, 1164
games (ladder 140, gen 512, gen-s1 512).

| Change | Win % | 95% CI | OOF cand / ref |
|---|---|---|---|
| All three below together | 44.5 | 41.7-47.4 | 3912 / 3914 |
| `cycle_horizon` deleted (a cycle's rate is worth / rounds) | 45.4 | 42.5-48.2 | 4062 / 3934 |
| Willow's heal step charges the basics it gives up | 50.0 | 47.1-52.9 | 3882 / 3889 |
| `camp_exit_rounds` by walk (`reachable_tiles` over `Pathing::blocked`) | 51.2 | 48.3-54.1 | 3974 / 3924 |

- The horizon's loss is the bundle's: horizons of 70-140 were level (koi), none is not. It stays.
- Heal step: 50.0% on every suite, with identical out-of-fuel counts on gen and gen-s1: it rarely fires (Willow is
  drafted on 5-pick maps only, and the step needs no strike possible and an ally a step out of heal range). Kept
  (CHANGES 153).
- Exit by walk: the old rings counted a safe tile behind a wall as one step out. Level; kept (CHANGES 154). The `1.5x`
  escape-damage factor was left (exact camp phases would roughly halve the margin: a risk bet, its own A/B).

## Phase 1: rules-derived models and farm-loop fuel (2026-10-27, astraeus)

CHANGES 178-182. Each against astraeus 0c13a93b (`bots/variants/astraeus-0c13a93`), own drafts, 1164 games (ladder
140, gen 512, gen-s1 512); the W1, W2 and W3 rows are cumulative within their stream. From rules checks of the threat,
farm and fuel code (bugs, modelling gaps, magic numbers); the deferred items are in TODO.

| A/B | Change | Win % | 95% CI | OOF cand / ref |
|---|---|---|---|---|
| w1-fuel-13 | stale tail leaves the farm loop; centres warmed nearest the farm choice (kept, 178) | 50.3 | 47.4-53.1 | 4523 / 4531 |
| w1-fuel-135 | + FSEED turns in nearest order with the stop | 49.8 | 47.0-52.7 | 4550 / 4524 |
| w1-fuel | + pruning before stale facts | 49.8 | 47.0-52.7 | 4572 / 4526 |
| w2-dur | Durability in bounds, pack ratio, unseen hits, Ren retaliation (kept, 179) | 50.4 | 47.6-53.3 | 4720 / 4673 |
| w2-camp | + camp phases by the rules (kept, 179) | 49.7 | 46.9-52.6 | 4802 / 4630 |
| w2-arrive | + allies walk into fights (kept, 180) | 50.3 | 47.4-53.1 | 5106 / 4562 |
| w3-monster | camp estimates with Monster and Collectors (kept, 181) | 50.1 | 47.2-53.0 | 5012 / 4889 |
| w3-capture | + skip enemy holds paying before we arrive, + score backfill | 46.6 | 43.8-49.5 | 5067 / 5017 |
| w3-mb1 | Monster + the hold skip | 47.5 | 44.7-50.4 | 4887 / 4970 |
| w3-b6 | Monster + the score backfill (kept, 181) | 49.2 | 46.4-52.1 | 4990 / 4869 |
| w4-probefix | capture state any tile, recall landing (kept, 182) | 50.3 | 47.4-53.1 | 4747 / 4811 |
| p1-merged | 178-182 together | 51.0 | 48.2-53.9 | 5335 / 4781 |
| p1-narrow | + a one-turn walk joins at once (kept, 180) | 50.7 | 47.8-53.6 | 4982 / 4516 |
| p1-confirm-1301 | p1-narrow on fresh suite 1301 (512 games) | 52.5 | 48.2-56.8 | 1810 / 1666 |

- Fuel, all exact at 100M (wide 52/52, heavy 16/16) but dropped for real-budget reasons: drafted spawn steps before
  the centre field (F4: heavy +1%; gen-gem-centre's queue never warms centres, so the farm loop rebuilds `from_here`,
  ~34k, every turn); building `to_any_altar` and the spawn-centre field early in the queue, and warming centres by
  drafted steps (centre fields later, rounds 3-30 worse); pruning before stale facts (rounds 2-100 overshoot -12-35%
  at 100M, but pruned groups stay stale and are retested: rounds 61+ out-of-fuel 3340 vs 3249); FSEED turns in
  nearest order (no out-of-fuel gain). Saved on `orch/p1-w1-fuel-full` and `orch/p1-w1-fuel-135`. Rounds 1-10
  out-of-fuel turns: kept 825 vs 837, with pruning 803 vs 838.
- Lost: the farm skipping an enemy-held cleared group whose payout comes before we arrive (MB1, valued as respawning
  from payout + respawn through `wait`): Monster + it 47.5% against Monster + the backfill 49.2%, ladder 42.9.
  Pricing it instead of skipping is in TODO.
- Arrival: delayed allies leave the fight sim's plain path; w2-arrive alone added 8% out-of-fuel turns over w2-camp,
  and p1-merged ran x1.116 the REF's (rounds 1-10 877 vs 846, 61+ 3874 vs 3382). Delaying only walks of 2+ turns
  (p1-narrow) brought it to x1.103 (61+ 3525 vs 3138) at a level win rate; the confirm run is x1.086.

## Phase 2: emblems from the rules and measured income (2026-10-27, astraeus)

CHANGES 183-184. The plan priced each emblem's rule in the bot's units from per-gem rates measured on 652 own-draft
games (Treasure +0.4-0.5 gold a gem, Hunter about half that, Prospector 0.07-0.13 gems a gem, Capture 2 rounds a
hold). First a forced first emblem in place of Treasure (Prism unchanged), then the model.

Forced first emblem, both bots on test drafts, against astraeus d0244de2 with test drafts (`emb-ref`), ladder + gen,
652 games (CI about ±3.8):

| A/B | First emblem | Win % | ladder | gen |
|---|---|---|---|---|
| emb-td-capture | Capture | 55.2 | 47.1 | 57.4 |
| emb-td-prosp | Prospector | 53.7 | 50.0 | 54.7 |
| emb-td-monster | Monster, main stat | 53.2 | 51.4 | 53.7 |
| emb-td-none | none (the model's pick) | 51.1 | 50.0 | 51.4 |
| emb-td-hunter | Hunter | 49.7 | 50.0 | 49.6 |
| emb-td-skirm | Skirmish | 46.6 | 46.4 | 46.7 |
| emb-td-cp | Capture then Prospector | 49.8 | 48.6 | 50.2 |
| emb-td-cm | Capture first + Monster a candidate for all, against emb-td-capture | 49.7 | 49.3 | 49.8 |

Own drafts, against d0244de (`bots/variants/astraeus-d0244de`) unless noted, ladder + gen + gen-s1, 1164 games:

| A/B | Change | Win % | 95% CI | ladder / gen / gen-s1 | OOF cand / ref |
|---|---|---|---|---|---|
| emb-own-capture | Capture first | 53.3 | 50.4-56.1 | 47.9 / 54.9 / 53.1 | 5056 / 4968 |
| emb-own-prosp | Prospector first (W1/W2 step 0) | 54.4 | 51.5-57.2 | 51.4 / 55.7 / 53.9 | 4629 / 4847 |
| p2w1-a | income counters + passive terms, nothing forced | 59.5 | 56.6-62.2 | 49.3 / 60.9 / 60.7 | 4969 / 4628 |
| p2w1-b | + passives' gold at the best stat emblem's saving (kept, 183) | 61.1 | 58.2-63.8 | 47.9 / 63.7 / 62.1 | 4660 / 4619 |
| p2w1-b-vs-prosp | p2w1-b against emb-prosp-own | 56.9 | 54.0-59.7 | 53.6 / 56.8 / 57.8 | 4871 / 4305 |
| p2w2-prism | Prism prices passives from static map rates, against emb-prosp-own | 49.6 | 46.7-52.4 | 54.3 / 46.3 / 51.6 | 4947 / 5005 |
| p2w2-prism-vs-d0244de | the same against d0244de | 55.2 | 52.4-58.1 | 51.4 / 55.9 / 55.7 | 4970 / 4972 |
| p2w2-sinks | + Collectors (3+ families) and Greed, against p2w2-prism | 51.8 | 48.9-54.7 | | 5556 / 5257 |
| p2-merged-vs-w1 | Prism under W1's live rates, against p2w1-b (kept, 184) | 50.8 | 47.9-53.6 | 56.4 / 48.0 / 52.0 | 4661 / 4613 |
| p2-merged-vs-d0244de | 183 + 184 | 62.4 | 59.6-65.1 | 57.1 / 61.5 / 64.6 | 4789 / 4773 |
| p2-merged-fresh1302 | 183 + 184 on fresh suite 1302 (512 games) | 64.3 | 60.0-68.3 | | 2288 / 1877 |

- Treasure first is worth about nothing at +10% (emb-td-none 51.1): every forced variant earned 5-8% less gold and
  still won or drew. Skirmish (no fight term) is the worst first emblem; Hunter matches Treasure.
- Capture and Prospector depend on the map as their rules predict. By the REF side's captures per gem (terciles):
  Capture first 46.5 / 51.6 / 67.4, Prospector first 48.8 / 51.6 / 60.6. Ladder maps have big groups (~12 captures
  per champion-game against ~16 on gen), where Capture first lost (47.1, 47.9).
- Forced passives do not add up (emb-td-cp 49.8, below either alone): the second delays the stat emblems. The model
  buys them back to back (Prospector then Capture or Treasure) and wins.
- Monster offered to everyone late was level (emb-td-cm 49.7), like 2026-10-19's Monster in best_emblem.
- p2w1-a priced a passive's gold at whichever candidate led the loop, often another passive; the best stat emblem's
  saving gave +1.6 overall but ladder 49.3 -> 47.9 (140 games, within noise). Rounds 1-10 out-of-fuel 948 vs 873.
- Dropped: Collectors and Greed as candidates (p2w2-sinks): level, out-of-fuel turns +6%, Greed never bought,
  Collectors ~0.34 a champion-game in place of Bruiser (patch on `orch/p2-w2-prism` ae692b50). Static Prism priors:
  replaced by the live rates, not dropped on a result.
- Merged, terciles by captures per gem 48.2 / 65.5 / 73.5; by cluster-group share level (61.6 / 63.9 / 61.6). The
  ladder rose to 56.4-57.1 with Prism's passives (W1 alone 47.9), so no ladder fix was tried. Fresh 1302's extra
  out-of-fuel turns are rounds 61+ (1625 vs 1248) on two maps: gen-arena-130202620 209 vs 86, mut-stampede 213 vs
  118; the main run was level (4789 vs 4773; rounds 1-10 951 vs 865, 61+ 3326 vs 3476).

## Phase 3: drafts after patch 2.0.0 (2026-10-27, astraeus 3ff5e55)

Details and tables in [hyperion/DRAFT.md](hyperion/DRAFT.md#phase-3-draft-search-2026-10-27-astraeus-3ff5e55).
Single swaps of each draft against the source bot playing the post-patch top-10 drafts (`tools/variants/ds_run.py`),
paired, ~7.7k games; fresh suite `maps/fresh-1303`. No draft changed.

- 3 picks: all 7 swaps lost on 160 jobs (-4.4 to -24.4, 5 beyond 2 SE); Marcella Vendetta HoR stays.
- 4 picks: all 7 lost on 160 jobs; the three closest (Cassi, Willow, Tavi for Vesper) lost on all 356 (-3.1 to -6.5).
- 5 picks: Vendetta for Vesper +3.7 ±4.7 pooled over 704 (base 486 +4.3, fresh 218 +2.3, fresh top 5 -1.2), head to
  head 50.3% of 704: under the +2 SE bar. Vendetta for Willow +3.1 on the base pool, -9.6 fresh.

## Draft lab: drafts from map features (2026-10-28, astraeus bb73f75; CHANGES 198)

Self-play with per-map forced drafts (`tools/draftlab`, lab `night1`): 88308 games in 12 hours (30 batches, 0 errors,
0 draft mismatches), about equal per pick count, half the games with one team on a top-20 ladder composition
(`prior.json`, patch 2.0.0). Batches 0-2 uniform exploration; then 70% Thompson sampling, 15% paired probes, 15%
exploration. `maps/fall-holdout` never played. Not stopped early at 08:14: the best team per map matched the 2 h
older model on 86/77/73% of maps (3/4/5 picks, bar 90%) and the search's cv still fell 0.0026.

- **Model:** per pick count, champion intercepts + champion x 19 map features + pair synergy + counters, penalised
  toward a pooled fit, penalties by 5-fold cross-validation over maps. Final cv log loss 0.6326; without map terms
  0.6485, intercepts only 0.6513, coin 0.693. The map terms' gain grew all night (0.011 at 9k games, 0.016 at 88k;
  on exploration games alone still rising at 18k). Counters were penalised to ~1e-4 (no measurable counter effect in
  our play); synergy is worth 0.0003. Pairing the gem margin into the target (alpha) did not help.
- **Strongest features** (spread of champion value per sd): gems per side, cluster share, Golem/Monolith share,
  altar contest ratio, big-camp share (1-3 points); holes, bushes, choke, openness and dash shortcuts weakest (0.4-0.7).
- **Model-best teams** vary by map: on 5 picks 10 of 12 champions are in some map's best team (Marcella 87%, HoR 78%,
  Vesper 65%, Willow 61% of maps); Stellar almost never at any pick count. On 3 and 4 picks our fixed drafts are the
  model's best single team; on 5 picks Vesp Cass Marc Will HoR would be (+3.3 predicted).
- **Predicted** (the model's own estimate against the ladder prior, posterior draws): per-map drafts +7.2 / +8.3 /
  +11.3 points over the fixed drafts on 3/4/5 picks.
- **Measured** (CHANGES 198, against bb73f75, own drafts): 56.8% of 868 on maps the lab never played (fall-holdout
  55.3% of 356, fresh seed 52826 57.8% of 512), 57.9% of 1164 on the standard suites (in-sample). Positive on every
  pick count; about half the predicted gain.
- **C++ port:** 0 differences in features and team against the JS on 248 maps in game and 760 offline; fuel 1.6M
  median, 5.6M max; the draft analysis spilled past draft round 0 on 2 of 356 holdout team-games. The port's first
  version cost 14-19M on 100x100 maps (the first draft turn would have run out before picking); the audit fixed it.
- **Ladder cross-check** (`model.mjs ladder`, 11570 games between two top-20 teams, team effects and Elo): champion
  values barely correlate with self-play (3/4/5 picks -0.08 / 0.29 / 0.03). Prism is our self-play's best champion
  (+10 to +14) but below average on the ladder (5 picks -6.9 +-5.4); Willow (+11.3 +-4.5) and Ryth (+5.2 +-3.4) are
  clearly good on the ladder at 5 picks and weak in our play. Reading: self-play measures how well our bot plays a
  champion; Willow and Ryth are where our play most trails the field. Against real teams the gain may be smaller.
- Data: `replays/draftlab/night1` (games.jsonl 260 MB; a compressed copy is backed up off-repo).

## Durability gaps and emblem shopping (2026-10-27, astraeus 929b142)

CHANGES 185-186, cumulative bundles, own drafts, against 929b142 (`bots/variants/astraeus-929b142`), 1164 games:

| A/B | Change | Win % | 95% CI | ladder / gen / gen-s1 | OOF cand / ref |
|---|---|---|---|---|---|
| todo-b1 | Ren's retaliation x our taken, live_self's factors, siege others by camp_output (kept, 185) | 50.3 | 47.4-53.1 | 50.0 / 50.4 / 50.2 | 4806 / 4811 |
| todo-b2 | + shopping trips count completed passives, Prism offered Treasure (kept, 186) | 49.6 | 46.7-52.4 | 49.3 / 46.5 / 52.7 | 4962 / 4737 |

- Both level, logical, kept; not bisected. todo-b2's out-of-fuel turns are +5% (gen 1967 vs 1738) though the
  prefix's own cost is unchanged: play (more or different trips).

## Assumption audit, batches 1-2 (2026-10-27, astraeus c6cb8e7)

Against c6cb8e7 (`bots/variants/astraeus-c6cb8e7`), own drafts. Kept: CHANGES 191-196.

| A/B | Change | Win % | 95% CI | Games | OOF cand / ref |
|---|---|---|---|---|---|
| batch1-own | 191-193 + river's camp area/stun term (B) + recall_outruns under camp fire (C) | 47.3 | 44.5-50.2 | 1164 | 5443 / 3529 |
| batch1-B-alone | B alone | 47.8 | 44.9-50.6 | 1164 | 5573 / 3571 |
| batch1-noB | 191-193 + C | 48.6 | 45.8-51.5 | 1164 | 3635 / 3667 |
| b1-noC-ladder | 191-193 | 46.4 | 38.4-54.7 | 140 (ladder) | 736 / 737 |
| b1b2-noC-ladder | 191-193 + all of batch 2 | 38.6 | 30.9-46.8 | 140 (ladder) | 1037 / 649 |
| b1noC-p6-p7-4a-ladder | 191-196 (kept) | 53.6 | 45.3-61.6 | 140 (ladder) | 802 / 727 |

- Dropped, B: river's closed form (area x (cover - 1) folded into the clear's strength, stuns as cancelled
  attacks, with the fastest-clear and `beyond_spare` bounds following it). Its every-turn out-of-fuel blowups late in
  games (02the-pack, mut-the-pack, gen-dense-camps) cost the batch; not retried cheaper.
- Reverted, C: `recall_outruns` false whenever `camp_damage(here, worst)` > 0 counts unknown-wake groups and ignores
  nearer champions, so it may cancel recalls no camp would hit. A narrower test (members known awake that pick us)
  is untested.
- Unidentified regression: batch 2's P3a (shared-clear fire by stand tile), P3b/P4 (fire handed to teammates in
  steps, lethal camp tiles in retreat) and P5 (Heart of Ruin's scaling in Trade), together: -8 points and +40%
  out-of-fuel turns on the ladder. Not split. See TODO.

## Vendetta (2026-10-24, astraeus on its 3-pick draft Marcella Vendetta HoR)

Against astraeus 72de514 (`bots/variants/vend-ref`), own drafts, the 3-pick maps only (other pick counts play
identically): ladder 6, `maps/gen` 84, `maps/gen-s1` 92 maps, both sides (364 games); fresh suite seed 9137, its 85
3-pick maps (170). Pieces: **A** a camp kill gives Vendetta one more hit in `min_camp_damage` (`kill_carry`, every
clear estimate); **B** an unseen Vendetta ally's arrival assumes a ready dash then the cooldown, not a dash every turn
(`earliest_work_delay`); **C1** Treasure in Health on Vendetta; **C2** a Monster emblem in Strength among Vendetta's
emblems, with camp kill tests counting its +10%; **D** with the reset cooling, a camp hit that kills goes first.

- All five: 45.6% of 364 (40.6-50.7; gen 49.4, gen-s1 42.9). Vendetta bought 0.87 Monster emblems a game, earned 4%
  less gold and banked 12 fewer gems.
- B alone 49.5% of 364. A+B+C1+D (no Monster): 48.4% of the 364, fresh 53.5% (50.0% of 534).
- **C1 alone: 53.8% of 364 (48.7-58.9), fresh 54.1% of 170**; 53.9% of 534. Shipped with B (level, a model
  correction; not played together) as CHANGES 137.
- Each on top of CHANGES 137 (065f2631, `bots/variants/vm-ref`), fresh suites seeds 5171 and 6203, their 3-pick
  maps (312 games): A 49.0%, D 49.4% (both level); **C2 54.5% (48.9-59.9)**, confirmed on the 364 above: 54.1%
  (49.0-59.2); 54.3% of 676, out-of-fuel turns level. Shipped as CHANGES 138. The bundle's readings against C1 (C2 "-3", A or D "-5") were
  differences between candidates on the same games, within noise; only the single-piece runs above attribute.
  The bundle's 45.6% stays unexplained (the parts sum to ~55): A and D together, maybe with C2, is untested on
  CHANGES 137; both were dropped.
- Why A and D are level: on the unmodified side (364 games), of camp kills made with the reset cooling and the cast
  free, 66% cleared the group (nothing left to hit), 22% left the rest out of melee reach (the reset waits a turn),
  11% reset at once and 0.5% missed an adjacent member. So refreshes are rarely wasted, A's extra hits mostly happen
  (a turn late), and D's kill first adds a hit only in the few multi-member groups where one is in reach.

## v50's all-map changes, CHANGES 135 and 136 (2026-10-24 audit)

v50 (065f2631) differs from v49 (80e21f33, `bots/baselines/v49`) on 4- and 5-pick maps only by CHANGES 135 (a kill
opens its tile in the strike search) and 136 (a spent stun is not pending; Marcella's tribute gold). Audited after v50
went 11-19 against Intercontinental Fish on the ladder (v49 51-54; p ~0.25, likely an older Fish).

- Code review against the rules: no bug. 135 opens only tiles of units killed in that branch, never the enemy spawn,
  both bodies of a linked pair; Node +16 bytes, no fuel gate. 136: every former `has_stun` reader that meant "will lose
  its next turn" now reads `stun_pending`; only `my_stunned` keeps `has_stun`, correctly. The stun reading is
  engine-confirmed (`probe-stunread`, tools/probes/README.md). Marcella's gold uses gem-equivalents per gold, no bonus.
- v50 code (72de514d) against v49, own drafts (identical on 4/5 picks), the 4- and 5-pick maps of ladder, gen and
  gen-s1: 52.4% of 736 (48.8-56.0; 4-pick 48.9 of 356, 5-pick 55.8 of 380), out-of-fuel turns 2258 vs 2019 (a few
  gen maps; ladder 255 vs 248).

## river: astraeus in htb with position comms (2026-10-24/25)

`bots/river` is astraeus's engine (world, safety, pathing, strike search, decisions) in htb, its decide() split into
per-champion states, with comms replaced by a Huffman-coded ring of moves (exact: 0 wrong of ~300k checks) and
claims worked out from positions (Khaos's closest-ally rule) instead of posted.

- The port is faithful: river with astraeus's own comms (`bots/river_ac`) plays byte-identical games to astraeus at
  unlimited fuel; on ladder maps it scores 49.3% (720 games, 9 fuel budgets 94k-106k, CI 46-53).
- River as specified (ring + support + bags + positions + claims, no capture timers or sightings): 39.4% (720 games,
  CI 36-43), out-of-fuel turns 1.28x astraeus's. The ring and claims cost ~10 points on ladder maps.
- Ladder maps only, 240 games (fuel 97k/100k/103k; budgets share outcomes, about 160 independent games, so ±8 a test
  and ±11 between two tests): astraeus with no comms 47.9%; river ring only 42.9-43.8%; + support 46.2, + bags 44.6,
  + capture timers 37.9 (27-bit records crowd moves out), + positions and claims 40.0, + tail sightings 41.7;
  posting the recall landing early (to cut last-moment recall cancels from 21% to 8.5%) 34.6. On all suites (1662
  games, ab.py): river 39.5%, without claims 38.4%, astraeus without comms 44.5%, river with sightings in the move
  stream 28.5%.
- Astraeus's comms are worth ~2 points on ladder maps (~5.5 over all suites); its sightings alone are not (53.6%
  without them, ladder suite).
- Pitfalls: a refused move or dash reads to astraeus as a hidden blocker (pathing and the strike search then try every
  alternative and run out of fuel), so river reports walking or dashing unavailable when the record would not fit; a
  4000-fuel margin before moves made late retreat moves fail the same way; astraeus's per-turn priorities break any
  comms rule that assumes a fixed turn order (river tracks each ally's read point by its latest record, plus a 4-bit
  "still here"); per group and ally, claims cost ~100 fuel in WASM (6-14k a turn), per-tile nearest-group lists ~2-3k;
  a vector of one entry per tile cost a fuel a byte to fill (84k once); copying .htb bots under `bots/variants/` makes
  the editor extension write ~600 MB of context headers per copy.

## river: local router and dash prices (2026-10-26)

`bots/pathlab` benchmarks route searches at release fuel (20 random queries a map, goals 10-30 away, an enemy reach
and the 2 nearest camp groups awake). A WASM tile test costs ~27 fuel and a vector push ~54, so per-tile searches are
expensive; word-parallel masks are not.

- Fuel per call (median, 4 maps):
  - the comms session's 11x11 Dijkstra: 76-102k;
  - helios's chunked bitmask A* (Cambridge-Battlecode-Fall), whole map: 30-58k; windowed to radius 8: 21-27k;
  - an exact search over (tile, dash cooldown, camp sleep progress): 31-45k for walkers, 78-146k for dashers;
  - a backward Dijkstra over the 7x7 window around us in one u64 (helios's local-window trick), the rim seeded at
    2 x host steps: 6.7-7.1k, 7.3-7.7k with dash edges.
- The 7x7 search as river's router (`Pathing::local_search`, removed again; kept outside the tree). Costs in half turns:
  - enemy reach +3, beside it +1;
  - awake camps charge only on "hot" reach: tiles we can reach before the camp would sleep, chained through its
    reach and the tile beside it from within 2 of us;
  - inside an awake camp's reach, a second search prices leaving it to sleep.
- Travel dashes priced 3 (dash for a gain of 2) unless the dash may be needed before it is ready again:
  - a crossing ahead uses a keep price the draft tunes;
  - a credible enemy within 8 uses at least 9.
  - The draft simulates 16 trips with the real cooldown (`tune_dash`, 1.8-6.8M fuel). It chose 7 on 00pilgrimage
    (1151 turns against 1203 eager) and eager on the 7 other maps tried. For travel alone, dashing at a gain of 2
    takes ~20% fewer turns than never.
- A/B against river-base (the comms session's 24-expansion weighted A*). 70 ladder maps, both sides, 9 fuel budgets
  88k-112k, 140 games each; the mean over budgets:

  | Candidate | Win % | Out-of-fuel turns (cand / base) |
  |---|---|---|
  | the 7x7 router and the dash prices | 41.9 | about half |
  | the 7x7 router | 43.6 | about half |
  | the 7x7 router with the old flat camp weights (reach 2, beside 1), no leave search | 41.6 | |
  | camps never trigger the router (3 budgets) | ~43.6 | |
  | travel dashes not compared with the walk (3 budgets) | ~43.3 | |
  | light weights (enemy reach +1, nothing beside it; hot camps at half their damage, 1-5; no leave search) | 57.1 | 118k / 283k |
  | **no weighted routing: host routes, host-steps travel dashes** | **57.5** | 64k / 265k |
  | no weighted routing, plus the dash prices and the draft's tuner | 56.7 | 68k / 280k |

  Steering by enemies' and camps' reach makes river passive: the capped A* follows the weights loosely and loses
  ~7 points to unweighted routes, the exact search follows them fully and loses ~14. Safety, the guard and the
  callers' avoid boards already keep river out of danger. Light weights do no better than none at twice the
  out-of-fuel turns, and the dash prices add nothing to unweighted routes. River now routes unweighted and dashes
  for a gain of 2 steps, as before.

## river: camp member targeting (2026-10-27)

- Camp hits rank members by Strength over current health, read from the engine when ranking. This now applies to the
  reset's second hit too, which used to take the weakest member.
- `prefer_partial` is removed: a ranged farmer about to wake its own group hit a damaged harmless cluster first, but
  the group wakes once farming starts anyway.
- Vendetta's two-hit kill (the kill readies the reset) is a tiebreak, no longer a +1e6 override.
- A member is left alone when an ally that has not yet acted this round could take it:
  - its hit is no stronger than ours and kills it, from where it stands;
  - and the member is its own top pick by the same score.
  - Without the top-pick condition, the weaker ally hit the member only 19 of 40 times on 00pilgrimage; with it, 22 of
    27 on three maps.
- A/B against river without these changes, 70 ladder maps, both sides, 140 games each (about ±8 at 95%):

  | Fuel | Win % | Out-of-fuel turns (cand / base) |
  |---|---|---|
  | 100k | 55.0 (46.7-63.0) | 11,950 / 12,582 |
  | 100M (unlimited) | 52.1 (43.9-60.2) | 0 / 0 |

  Both lean positive and neither is significant. Kept: the change does what was asked and nothing regressed.
- Vendetta pairing: with the reset ready and a member one hit kills, the basic attack goes to the best other member
  of its group and the reset's hit takes the kill (it readies the reset again). Traced: 39 of 39 pairs ended on the
  kill.
- A/B against the same base without any of these camp changes. River-vendetta forces Vendetta first; split by
  whether the candidate drafted Vendetta:

  | Bots | 100k | Unlimited | Out-of-fuel turns at 100k (cand / base) |
  |---|---|---|---|
  | river | 57.1 | 52.1 | 12,311 / 12,383 |
  | river-vendetta | 56.4 | 48.6 | 10,157 / 10,685 |
  | river-vendetta, rebuilt on the 2026-10-27 afternoon base | 57.9 | 48.6 | 4,577 / 4,330 |
  | games with Vendetta (both rows above) | 54.9 of 164 | 48.8 | |
  | games without Vendetta (river) | 59.5 of 116 | 52.6 | |

## river: camp attack planner (2026-10-27)

`plan_camp_attack` (farm.htb): the turn's first camp hit and the tile it is struck from. The options are here, a step
(melee freely; a ranged step spends the attack, which the reset buys back), a dash, or a dash then a step. Each
option scores the damage it prevents (research/river/CAMP-SCORE.md). Area casts and Heart of Ruin's landing are
ranked by the same score.

- A/B against the base without any camp changes (river-vendetta, 70 ladder maps, both sides, 140 games each):

  | Version | 100k | Unlimited | Out-of-fuel turns at 100k (cand / base) |
  |---|---|---|---|
  | full fight model (kill order, V(h) - V(h')), dashes searched everywhere | 47.9 | 47.9 | 8,521 / 4,277 |
  | same, dashes only when no hit is possible without one | 50.7 | 52.1 | 6,185 / 4,193 |
  | linear score: min(d, h) s / h per member hit; stun and a safer tile s / rounds | 46.4 | 51.4 | 5,754 / 4,480 |

- Isolated: each version against a passive bot (drafts, never acts), 70 ladder maps, same sides, ~55 clears a game.
  At unlimited fuel, planner against no camp changes, paired by map (95% CI):

  | Measure | No camp changes | Planner | Difference |
  |---|---|---|---|
  | camp damage taken per 1000 camp hp removed | 166.9 | 165.6 | -1.3 [-14.7, +12.2] |
  | rounds per clear | 20.0 | 20.0 | 0.0 [-1.7, +1.6] |
  | damage taken per clear | 341.5 | 331.4 | -10.1 [-39.6, +19.4] |
  | round the game ended | 961.6 | 952.7 | -8.9 [-58, +41] |

  The planner does not clear camps better. Its single-target choice is the old Strength-per-health ranking. It moved
  on 1-9% of attacking turns, each sparing at most one camp phase.
- Fuel: about 7.6M per game for the in-range attack against 2.6M before (one team, 6 maps, 100M fuel), ~1.5% of turn
  fuel. Lossless trims left the 52 bench replays byte-identical and saved 0.2%: early exit, `allowed` once per group,
  lazy threats, on-demand phase damage, landings checked on need. On the bench the share of turns over 100k is
  1.70% against 1.65% without the planner.

## river: dash-aware live routes (2026-10-27)

A dasher pocketed behind a hole line froze for good: Vesper Vale on 00ambush from round ~80, in every build. The
static approach field (dash-aware, but blind to sight lines) put it on an attack tile. The live route
(`Pathing::route`, the host's walking search) had no way into the sealed room. `dash_towards` skips goals within 2.

- While the dash is ready, `route` drops this champion's crossings (`map().crossable` less its static walls) from
  its walls. A first step onto a crossing is a dash (`dash_over`) to the landing nearest the goals along the route,
  at least 2 steps on, never onto the avoid zone, a waking landing or a suicidal one.
- A/B against the same build without it (river-vendetta, 70 ladder maps, both sides, 140 games each):

  | Fuel | Win % | Out-of-fuel turns (cand / base) |
  |---|---|---|
  | 100k | 50.7 (42.5-58.9) | 4,535 / 4,761 |
  | 100M (unlimited) | 55.7 (47.4-63.7) | 0 / 0 |

  Kept: it fixes the freeze and costs nothing.

## river: farm/capture split and the user's batch (2026-10-27)

These changes landed together:

- **States:** a "capture" state before farm; the old "capture" (Prism yield, Vesper Vale handoff) is renamed
  "handoff".
- **Ownership:** a cleared group's holder places go to a Prism keeping it, then to allies on it by gems carried,
  then to the nearest by centre steps; ties to the lower index. Holding uses the same rule.
- **Farm:** no longer picks up or walks onto cleared groups.
- **Planner:** tiles need a sight line to the target (member attack tiles); the tiebreak is 0.001 x our hit per
  member hit.
- **Routes:** jump a crossing only if walking is 2+ steps longer.
- **Hole-line dash** (`dash_across`): removed from farm and bank, then deleted.

A/B (river-vendetta, 70 ladder maps, both sides, 140 games each):

| Candidate | Reference | 100k | Unlimited | Out-of-fuel turns at 100k (cand / ref) |
|---|---|---|---|---|
| the batch | the build before it (dash-aware routes) | 40.0 (32.3-48.3) | 46.4 | 4,901 / 4,964 |
| the batch, capture changes reverted | the batch | 57.1 | 55.0 | 4,629 / 4,899 |
| the batch, capture changes reverted | the build before it | 41.4 (33.6-49.7) | 50.7 | 4,445 / 4,832 |

The capture rule costs about 5-7 points. The rest costs about 9 at 100k but nothing at unlimited fuel, without more
out-of-fuel turns. Kept anyway: `bots/river` holds every requested change (the user's rule: river is the newest
version, not necessarily the best).

Later on 2026-10-27, also in `bots/river`:

- **Safe recall line** (`recall_unreachable`, `recall_line` in retreat.htb). Go home at 10% health instead of 35%
  when no enemy can come within its attack or damage/stun spell reach in the recall's turns + 1. Dashers get 2
  more tiles. Unseen enemies count from their `possible` board, dead ones from their spawn if they may respawn in
  time, and untracked live ones always count. Farm's camp budget uses the same line. Against the batch above:
  52.1 at 100k (4,803 / 4,699 out-of-fuel turns), 47.1 unlimited: neutral.
- **Camp-hit dodge** (`dodge_camp_hits` in turn_order.htb). When next phase's camp hits would take us below the
  recall line, and we tie with an ally for a monster and act before it, rank ourselves lowest. Then the ally acts
  first and takes the hit. Only when each such ally stays above 35% after the extra hits. It fired 0-3 times a
  game in three games: too rare to measure.
- **Spare-walk camp steps** (`camp_spare_step` in farm.htb, after attacking from where we stand).
  - If next phase's camp hits would take us below the recall line, step to the neighbour with the fewest hits
    that still has a live member in attack range with a sight line.
  - Otherwise, melee, step greedily to minimise the max Chebyshev distance to the group's live members. Never
    onto a tile newly below the line or deeper into enemy reach.
  - The planner charges 1000 for any tile whose next-phase hits take us below the line, so a ranged champion
    steps (paying the reset) or dashes to a safe tile in range.
  - Traced: the danger step fired once in three games, centring 12-41 times a game.
  - With the dodge, against the safe-recall build: 57.9 (49.6-65.7) at 100k (4,813 / 4,757 out-of-fuel turns),
    50.7 unlimited.

- **Vendetta kill plan** (`camp_targets_at`, with the reset ready). Steps in order:
  1. If a member dies to one hit, the first hit goes to the best other member of its group (normal score; on equal
     scores a member that is not a one-hit kill first), and the reset's hit kills the one-hit member.
  2. Else, the best member two hits kill is hit twice.
  3. Else, normal order.

  The reset's hit takes kills first, which ready it again. Traced: one-hit pairs killed on the reset 22 of 26
  turns, two-hit plans 34 of 43; the rest never cast the reset.
- **Recall window:** 4 rounds plus a turn for turn order, not 5 plus one. A recall starts at every turn end and is
  kept at the next turn start, one turn end in.

- **Priced dash routes** (pathing.htb). While the dash is ready, `route()` picks its first move with
  `local_search`, the 7x7 bit-parallel Dijkstra from 2026-10-26 without danger weights.
  - A step costs 2 and a dash the price: 3, the draft's keep price with a crossing within 8, at least 9 with an
    enemy within 8.
  - The window's rim is seeded at 2 per host walking step.
  - Walk-only host routes remain otherwise, with the whole-map crossing route only when walking can't reach the
    goals.
  - `tune_dash` is back in the draft. On 00ambush it chose 3, using about 2M fuel.
- **Step tiebreak:** equally short steps prefer a bush, then a diagonal, then the smaller Manhattan distance to
  the aim, then compass order (routes and static-field descent).
- **Wards:** a candidate bush cluster scores only tiles no other allied ward already sees (radius-6 shadowcast, a
  ward in a bush seeing its own cluster).
- **Ward comms** (comms.htb, after the reports). Allied wards sit in bushes, unseen from outside, so the first
  version knew almost none: 60% of placements went into a cluster a teammate had warded.
  - One entry: absent, or an ally's ward tile flagged new or not.
  - A new ward is written at once and put new until the owner's next tick finds it still in the word; then once
    more, not new.
  - Others yield to a new entry; each ward is refreshed on two rounds in every 2 x team size.
  - 20 ladder games vs astraeus: every teammate learned every ward, delay median 1, 90th 2 (before the new flag:
    median 3, 90th 8, as refreshes overwrote unread announcements). Placements 1354 -> 738; into an ally's
    cluster 60% -> 47%, mostly far parts of big clusters.
  - Position accuracy 99.955-99.970% (99.960 without); written but unread, the bench is identical (52/52,
    +0.8% fuel).

None of these has an A/B yet (the ward comms A/B was stopped at the user's request).

### river: states merged (2026-10-27)

At the user's request:
- **capture**, from capture, hold and handoff. It has one score by case:
  - leave a group a Prism holds, or Vesper Vale relieving Heart of Ruin: 10;
  - stay on ours or one we contest: 8, after strike;
  - walk to ours: 1.
- **retreat**, from retreat, shop and the recall half of channel. Listed first:
  - keep the recall: max;
  - else it is dropped and we walk: fighting at 12, an errand at 5.

`run_states` now lets a score below a state's max wait until the list reaches it. There it is scored again and runs if it still reaches that level.

Intended changes:
- The recall is kept for danger, shopping and a siege heal only while it lands before walking would. Walking counts dashes (`recall_beats_walk`, `dash_route::paced`).
- Siege heals walk home when walking is faster.
- `capture_ours` puts Heart of Ruin last among allies on the tiles, so Vesper's relief works under the gems rule. The relief drops its id check.

Results:
- With those changes reverted, games are byte-identical to the old build: 20/20 at unlimited fuel, bench 52/52. Fuel is +0.75%, ~64 a turn in the state code.
- A/B vs the old build (`variants/river-premerge`): 51.4% (100k), 45.0% (unlimited), 140 games each. Both are within noise.
- Then: no recall is kept on a tile any awake camp member reaches, stunned included (`keep_recall`; before, only the danger reason checked, and only unstunned members). No A/B.
- Then the user's recall rules (`retreat_move`, `recall_spot`, `recall_threat`, `note_exposure` in retreat.htb; old code commented out):
  - no escape dash: the way home is pathfound;
  - within 8 steps of spawn, walk, unless an enemy last seen is nearer it;
  - base case (no enemy in sight, none that must reach a recall): walk to the nearest tile off every awake camp's reach and recall there;
  - else recall only where no enemy could cut it short, or in a bush where the enemy could believe us on at least min(cluster size, 8) bush tiles (exposure memory). Getting there, step away by their walk, then out of their sight, then nearer home;
  - enemies reckoned with: seen within 10 + the recall's stage rounds.

  A/B vs the same build without them (`variants/river-prerecall`), 140 games:

  | Build | 100k | Unlimited |
  | --- | --- | --- |
  | First version (any enemy that *might* reach counted as pressing: ~3x more flee turns than recalls) | 29.3% | 33.6% |
  | Seen / must / may split, rules alone | 42.1% | 42.9% |
  | With the tracker change, fresh baseline | 31.4% | 35.7% |

  Out-of-fuel turns at 100k: 35.6k vs 18.2k.
- Tracker without the 10-round horizon (`possible` grows forever; threats, casts, strikes and turn order still weigh only enemies fixed within 10 rounds via `tracked_recently`):
  - identical games (20/20 at unlimited fuel, bench 52/52);
  - +10% fuel a turn (p50 +15%).
- Leave-one-out on 35 ladder maps (70 games, about ±12). Each row is current river with one change undone, against current river (above 50%: the change hurts):

  | Undone | 100k | Unlimited |
  | --- | --- | --- |
  | A: no escape dash (dash back) | 52.9% | 45.7% |
  | B: walk home within 8 steps (old walk-vs-recall rule back) | 51.4% | 48.6% |
  | C: base case (old enemy checks back) | 48.6% | 47.1% |
  | D: `retreat_move` (old flee_camps / retreat_step back) | 58.6% | 60.0% |
  | E: tracker without horizon (horizon back) | 70.0% | 50.0% |

  E costs only fuel, but about 20 points at 100k. D costs about 10 at both budgets. A, B and C are neutral.
- Best build is not current river: `variants/river-prerecall` (river before the recall rules) beats it by ~15-20 points.
- Fixed on the way: wards from comms in a cluster not yet found made `other_wards_vision` cast from an opaque tile (engine error 5, ~250 a game on 01big-world). Together with the other session's router and comms fixes, 0 error lines on the 8 maps that had them.

**Best build measured so far:** `bots/variants/river-vendetta-c2now`, 57.9% at 100k against the base without any
camp changes. It has camp targeting by Strength per health, ally finishing, and the Vendetta pairing; no planner, no
capture split. It still freezes in hole-line pockets (no dash-aware routes); that fix was measured only on the
planner build (+5 at unlimited fuel).

## river: slot comms, Treasure, shard orders, camp targeting (2026-10-25)

All on the 40 ladder maps, both sides, 9 fuel budgets 88k-112k (720 games, about ±3.6 at 95%); head to head against
`rv-nobit` (river with the comms below, no sightings, astraeus's shop and targeting) unless stated.

- Comms with no marker bit, fixed turn order (priorities never set): one Huffman slot per ally (stay 1 bit, diagonal
  4, cardinal 5, the rest 10), rewritten every round by a tick (read, apply in posting order, write) and before each
  move. 99.999% of 426k checks exact on 80 games, none unknown. What it took: the tick runs from `aph::fuel()` whenever
  the budget rises (a resumed turn may never reach the turn's start), every write is preceded by a raw fuel check and
  a round check (a turn that runs out inside a host call gets its answer, then resumes next round), spawn arrivals are
  moves from the first spawn tile free of communicated positions, and main ends no turn with under 1000 fuel (a turn
  that runs out inside end_turn loses the next turn, `probe-endturn-fuel`). vs astraeus 43.5% (old marker-bit slots
  42.6%, ring 39.4%).
- Enemy sightings in what the slots leave (writer index, then per enemy its index and ring/tile offset from the
  writer, Huffman by ring): 99.94% of records decode exactly. Applied, they lose: 45.8%, nearest only 46.2%, and with
  a one-shift writer and enemies read once a turn 42.8%; written and decoded but not applied, 49.0% though out-of-fuel
  lines rose 63% (a bit-at-a-time writer). So the loss is the play, not the fuel: refreshed sightings keep enemies
  tracked, and astraeus's safety treats tracked unseen enemies as threats. Left off (`send_sightings`).
- Treasure under "maximise the integral of non-Treasure emblems" (`treasure.py`, our earned gold with Treasure's bonus
  removed): it loses for every champion we play (our base gold over a ~986-round game: Prism 1110, Vesper 1356, Heart
  of Ruin 860, Marcella 1409, Willow 355); it pays only above ~1650 base gold (Vesper ~2150: bonuses add, 20 of 133),
  as Fish's Vesper (2809). A second Treasure adds no gold. In play, no Treasure loses: 46.7% head to head, 32.6% against
  astraeus (where `rv-nobit` scores 42.6%): the objective ignores that a Treasure emblem's 5 shards still count.
- Shard orders: Fish's for Vesper (Bruiser-Str, Durability-Hea, Power-Str) and Heart of Ruin (Jungle-Foc, Bruiser-Hea)
  without Treasure 41.4% (no Treasure alone 46.7%); Treasure then Power in the main stat only 25.6% (no Jungle or
  Durability: camps' hits and heal trips): astraeus's upkeep model picks better for our play. A Treasure returned with
  no saving (`saved` 0) breaks gold valuation: a variant doing so scored 35.1%; priced right, Fish's orders with
  Treasure first 40.4%. Prism opening with Treasure-Focus (it opens Monster) 49.2%.
- Camp targeting: the reset's hit by damage removed per hit (was: lowest health) 49.7%; plus walking to tiles in range of
  members that hit back when one is within two steps 51.5% (Willow's clusters killed before the last dealer 70% -> 9%),
  aimed at the first target by that order rather than any 51.5%. With the camp estimate below, 46.1% and 46.9% (rerun on
  budgets 89k-113k: 44.7%); the estimate with the reset's new order but no tile change 47.2%: the reset order and the
  estimate each hold alone and lose together. Dropped both targeting changes; Vendetta keeps its kill-first rule.
- The camp estimate with Vendetta's kill-first targeting (F1): 53.3% against `rv-nobit`, but against astraeus 41.9% and
  39.7% (budgets 89k-113k) where `rv-nobit` scores 43.5% and 41.8%: river-vs-river gains need not carry over. On the F1
  base, Vendetta's targeting (both drafting Vendetta) 48.3%, with its reset aimed by damage too 47.1%: the 54.9% above
  (generic reset change, older base) does not hold here. Claims' per-tile
  lists worked out with spare fuel at the turn's end (for the next turn's lookups) 46.2% against that: the turn-end
  warm-ups that fuel would have gone to are worth more. River spends ~1.8k more a turn than astraeus (49.2k vs 47.4k,
  claims 2.4k of it): working out new tiles' lists, not the strictly-nearest checks (memoising those per group and turn
  left it at 2.45k). Forgetting unseen enemies after 5 rounds instead of 10 (`track_horizon`): 49.2%.
- Against astraeus (720 games each; `rv-nobit` 42.6% over 1440): dealer-first tiles with the reset's damage order 36.4%,
  the exposure-aware tiles with it 40.3%, sightings applied 36.7%, the camp estimate 40.8% (1440). What wins head to
  head against river's astraeus-like play loses to astraeus. River ships as `rv-nobit` (the camp estimate, the tiles
  and the reset order are test switches, off; Vendetta's kill-first first hit stays, outside our draft).
- 720 games here are about ±3.3 at 95% stratified by map and side (the population is these 40 maps); clustered by map
  (to generalise to new maps), ±5-6. Only 6-8 of the 80 map-sides give one result at every budget.
- Vendetta, both teams drafting it: its two hits a turn aimed to end on a kill (refunding the reset) 54.9%; the clear
  estimate counting a member two hits kill as one turn on top, 48.9% (dropped). Vendetta for Willow on 5-pick maps
  (both with the logic) 50.7%.
- Camp-clear estimate (min_camp_damage) against 5004 solo clears: rounds 0.90x, damage 0.92x overall, but Prism 0.53x /
  0.58x (area spells and stuns uncounted), Heart of Ruin ~0.82x, Vesper damage 1.23x and Willow 1.12x (clusters first).
  Area hits counted on the members a 3x3 covers and stuns as cancelled attacks: 53.1%, rerun on budgets 89k-113k 52.2%.

### river synced to astraeus 5a0dbb98 (CHANGES up to 141, 2026-10-25)

The 24 astraeus commits after 4d082411 (river's base) ported commit by commit into `bots/river_ac` (astraeus's
comms and turn order) and `bots/river` (all but comms and turn order; astraeus's priority payload is left out, river
never sets priorities). After each, `river_ac` played byte-identically to astraeus at that commit at 100M fuel
(2 maps, both sides); at the end on 12 maps (24 games). The htb port's renames: plan.cpp's `walked` is `seg_walked`,
`dilate(` is `grid_dilate(`, `Unit` is `SearchUnit`; abilities.cpp's `camp_stunned` is `camp_stunned_now`;
turn_order.cpp's `none` band is `no_band`; draft_selection.h is gone with CHANGES 134.

### river comms: Huffman vs arithmetic coding (2026-10-25)

Slot contents of 40 ladder games (171k), fitted on half the games and scored on the other half, every symbol at
most 10 bits (6 allies always fit). Bits a slot: Huffman as it was (stay 1, diagonal 4, cardinal 5, rest 10) 3.363;
optimal length-limited Huffman 3.295, with the ally's previous symbol as context 2.334, previous two 2.251;
arithmetic coding in rANS form 4.66 (a state's worth of start-up cost per word: no use for 15-bit messages); exact
arithmetic coding (range 2^63, frequencies out of 1024, exact in 64-bit integers) 3.219, 2.228, 2.126; compact tables
(9 common frequencies and one shared rare one per context) with contexts reset every 64 rounds (a reader that misses
a round resyncs) 2.180. Kept: the last. Moves 99.991-99.993% exact on 40 and 12 games (the misses are the
low-fuel lag both codes share), sightings 10998/10998 exact; byte-identical games at 100M fuel (sightings off, the
decoded slots are the same). Fuel: +880 a turn against the old Huffman (decoding ~100 a slot against ~20 for a table
lookup; release builds the same); head to head 49.3% of 720, out-of-fuel lines +3%.

## river: order-proof comms and the turn order back (2026-10-26, cambc 4.0.0)

The repo's SDK moved to cambc 4.0.0 (patch 2.0.0); with the 3.0.5 CLI astraeus crashed every turn
(`camp_group_capture_state`), so the venv was upgraded and the baselines re-measured. Ladder maps, both sides, 9 fuel
budgets 88k-112k (720 games), against astraeus:

- river with the order-proof comms below and astraeus's turn order restored (`turn_order.htb`): 46.7% (CI 43-50).
  The same comms with the order fixed: 35.6%; the old fixed-order Huffman comms (`rv-port`): 34.3%. Free turn order is
  worth ~11 points; the comms alone are within noise. Sightings applied: 43.2% (-3.5, as on 3.0.5).
- Order changes: astraeus re-prioritises an ally in 9.5% of ally-rounds; the team order changes in 22% of rounds.

Comms designs, measured by an offline simulator over the extracted 80 traced games (each ally reads, then writes,
in the game's real turn order; exact arithmetic-coding costs; `scratchpad sim/sim.py`), then validated in play:

| design | bits/slot | decoding exact (sim) | notes |
| --- | --- | --- | --- |
| positions mod a square window covering the last two written positions (no turn info; sizes 1, 5, 9) | 4.62 | 100% | no overflow; per-axis moduli 5.0-5.7, all sizes 4.93 (naming the size costs more than it saves) |
| moves + counter mod 3 + double when a teammate missed a slot (shipped 2026-10-26 morning) | 4.20 | 100% | in play 99.907% exact on 80 games: overflows lag |
| moves + turn bit + window when missed, hold fallback (now) | 3.6 | 99.999% | in play 99.973%, 17.7 slot bits a word (counter 20.4) |

- Floors: the move given the two before costs 2.04 bits held out (river's compact table 2.09; champion type -0.01,
  teammate's move or game phase worse: sparse); a turn bit is 1 bit (the bit pattern of a word is not compressible
  with a fixed table: 4.9 bits/5 slots at best); the "a teammate missed my slot" signal ~0.3. Announcing priorities
  instead of turn bits: 163 distinct values, 0.97 bits/slot, and a missed announcement desyncs everyone.
- Coding moves from where the ally was two turns ago (every slot readable after a missed one) costs 3.35 bits a move
  against 2.04, and a reader that misses one slot then reads the next lacks the position between. Coding with the
  history lagged a slot (so a reader that missed one can still parse) costs 2.41.
- What made the turn bit safe: a slot that would leave under 9 bits becomes a hold (bit + "nothing new"), so a write
  never fails and no bit goes stale (a stale bit reads as a fresh slot every other round and every teammate stops
  parsing); readers apply any new slot to what they hold, and the writer keeps each teammate's view of its position
  and move history (a missed stay after stays changes nothing), covering only teammates whose view differs, with
  windows (act-independent) instead of doubles. Dead writers that need to cover send one absolute slot.
- Remaining misses (0.027% of checks): holds when several teammates cover in the same round (64%), moves on turns
  that ran out of fuel (24%; the pre-move write now needs 100 fuel in release builds, 250 in debug).
- In play: river with these comms 49.4% against astraeus (720 games, CI 46-53; the counter comms 46.7%), comms
  ~350 fuel a turn dearer than the counter version (debug build).
- Sightings in what the slots leave: ring frequencies, seen rate (0.31) and modes fitted to 248k sightings; the
  block carries the writer's round parity (dating by inferred order was wrong for 0.4% of records). 99.998% exact.

## river: the spec's own parts (Khaos claims, State score, stateless) and report comms (2026-10-26/27)

The river spec replaces parts of astraeus: claims exactly as Khaos's harvest, Khaos's State (run/score), no memory
between turns (the router is in "river: local router and dash prices" above). Ladder maps, both sides, against
astraeus; 720 games at 9 fuel budgets (88k-112k) unless "240" (100k, 94k, 106k). All with the router off.

- Claims exactly as Khaos (claim_subset with tie_self off: an ally owns a group when strictly nearest by walking steps,
  from Pathing's static centre fields; it claims its nearest owned group; no reach cap): 47.2% (CI 44-51), against 49.4%
  for the old Chebyshev-within-8 claims; out-of-fuel lines 32.5k against 20.9k. The all-pairs loop costs ~5k a turn
  (~21k on 00lanes, 42 groups) even with no field reads: WASM fuel counts every stack operation, ~40 a (group, ally)
  pair (a synthetic 42x5 loop of compares: 8.7k). Nearest-first lists per tile with a full-scan fallback cost 63k there
  (allies owning nothing scan everything): reverted.
- State as Khaos (max_score, score(), the best runs, an unended run passes the turn on): score() may return 0 only where
  run() would end and change nothing. The dead state's run also clears `banking` for a living ally without a bag;
  skipping it by score left banking stale with memory: k1 + score 34.6% (240) against k1 45.0%. Dead now always runs.
- Stateless (astraeus's Memory -> per-turn `Aims`, derived from facts): 33.8% (240; k1 45.0%), and at 10M fuel 43.8%
  against 57.5% (80): logic, not fuel. The same tree carrying every Aims field over from last turn: 45.8% (240). Per field
  carried over: claim+crew 38.8%, claim+crew+farm_group 41.2%, banking 32.9%, farm_group 34.6%, siege 35.4%. So the loss
  is mostly the farm's commitment to its target ("unless we claimed it first", the stickiness, the walk on to it).
  Fact-based stand-ins that recovered nothing: farm_group = the group we are clearing (an awake member in attack range,
  or our capture), claim = it else our Khaos claim, the nearest of the groups within the stickiness of the best, the walk
  prepared towards the claim. Also no gain: astraeus's altar wait timer, siege staging timer, Prism/Willow recovery and
  formation caps, ward, crystal and capture handoff (each restored alone, 240 games). The first cuts were worse: damage
  as what threats could deal and farm_group seeded with the Khaos claim gave 23.1% (the claim skipped farm's
  affordability check; tributes were refused whenever an unseen enemy might reach an altar). Damage is now observed:
  World::self_damage is the health lost since the end of our turn before. Landed as is (the user chose strictly
  stateless); the gap stays open.
- Reading bitboard tiles from the board's storage (word (y>>3)*chunk_stride + (x>>3), bit ((y&7)<<3)|(x&7)) matches
  sdk_Bitboard_Test on every call of 3 full games, ~27 fuel cheaper (util.htb test()). distance_field buffers do NOT match
  sdk_DistanceField_Get in play: the host keeps fields its own way.
- Report comms (landed): after every slot, a report per ally: absent (sees nobody), relative to its last report (an enemy
  in both by its move, given its move before) or fresh (ring, sector about the spawn-to-spawn axis, tile in the sector);
  forms 53/10/1 of 64 (a 1024-way form did not fit after the slots' 9-bit reserve: writes failed and positions drifted),
  flags 975/69 (on given on/off in the last report), fresh 258 of 1024. A writer short of room drops teammates' reports,
  the last first. Relative only when every teammate has the last report: each wrote after reading it (its slot is newer
  than ours), and the report is still in the word. A reader decodes a report only when its slot is new, otherwise puts
  it again as read; one it cannot read it writes absent and holds as nothing. 80 ladder games: positions 99.883% exact,
  reports 99.855% (some misses are trace lines interleaved in team stdout), 7 report parse failures (one game, detected
  and recovered), word 26.1 bits (slots 17.4). The first design (a report inside each slot) had positions at 93.4%: a
  misparsed report corrupted every later slot. Applying the reports in the world stays off (it cost 3-7 points before).

## river: fuel (2026-10-27)

Profiled with debug-only meters (debug_block output is refunded, so one instrumented game replaces an A/B for fuel):
every state, the comms tick and posts, every Pathing entry point. Six ladder maps, one side, 100k: ~13k turns. Every
change below plays identical games at 10M fuel to the version before it.

- Report comms (landed with reports on) cost ~6k a turn more than slots alone: decoding a new report ~1.5k (a
  576-byte Fields zero-fill and copy each, float log2 per field, linear symbol searches), re-encoding every report at
  each write, about two writes a turn. Fixed: no zero-fill or copy, bits measured by the coder, binary searches,
  ring-tile tables for fresh tiles, an identical write skipped. Then `send_reports = false` (nothing reads the reports;
  the section leaves the word): the comms tick 8.5k -> 3.9k a turn, posts 2.6k -> 0.9k, out-of-fuel turns 239 -> ~100
  in the six games. The report code stays behind the switch (99.86% exact when on).
- Claims (exact Khaos, all allies): 6k a turn, 20k on 00lanes (42 groups). Field reads were not the cost: ~40-80 fuel a
  (group, ally) pair of plain WASM (fuel counts every stack operation). Landed: each centre field exported once
  (export_linear_buffer, ~0.26 fuel a tile), a row of steps to every group per tile (built on an ally's first visit:
  walls are static), and the strictly-nearest test in WASM SIMD, 8 groups at a time. Median 20.4k -> 3.9k (00lanes),
  6.1k -> 1.9k, 6.6k -> 2.0k; 0 disagreements with the old code over ~15k side-by-side computations.
- Pathing per route() call: building the walls 0.5-1k, the kept-route check 0.2-0.5k, the host search 0.5-3.9k (when
  run, ~50% of calls), the first steps 0.8k (8 field reads). Field reads are only 19-34 a turn: exporting fields to
  memory would save <1k. A static-field shortcut (exact: answer from a cached field of the static walls and camps when
  no other wall can lie on a shortest way, d_static(t) + Chebyshev(me, t) > ours; 0 differences in 4,150 checks) hit
  11-47% of calls but its fixed costs (camp board, board compares, building fields) raised route() 2.5k -> 3.6k a
  turn: reverted. A first-steps memo found no repeated (tile, field) within a turn.
- Left: decide is ~37k a turn, farm's evaluation ~7k (astraeus's logic), the world update ~8k, the claims ~3.7k.
- Comms split by unit (each ally's slot its own arithmetic-coded segment ending on a whole bit; a writer recodes only
  its own and splices it in): identical games at 10M, but the word grew 17.8 -> 21.2 bits (a segment's end costs
  ~1-2 bits; the mode's context on the slot before had to go), SMALLER 25 -> 378, ally positions 99.98% -> 99.73%. Fuel:
  posts -230 each, the tick unchanged, ~100 a turn in all: re-encoding the slots after ours was never the cost.
  Reverted. The tick (3.9k) is decoding each teammate's slot (~435 a slot: turn bit 47, mode 98, move 167, placing
  and history 99, spread over small steps) plus the alive check (31), what each teammate has of us (~0.9k) and our
  write (~0.9k).
- Route lengths when the host searches (6 maps): 12% are 1-2 steps, 25% up to 4, 50% up to 10, 15% 30 or more. A
  search costs ~800 plus ~40 a layer, below any per-tile WASM search, so short routes leave nothing to win.
- The world update (9.2k a turn; camps 3.3k, champions 2.8k, turn ranks 1.9k on 37% of turns, priorities 0.6k,
  altars 0.4k). Host reads are 5-20 fuel flat while our own code is ~2-3 fuel an instruction, so the cost is our
  logic. Landed, identical games at 10M: util's test()/tile_set() back to the raw host call (16 fuel against 54 for
  the direct read with its bounds check; ~100 tests a turn): the turn -1.6k. A group in view settled without reading
  its members when it reads as last round did: respawning before its read return round, or alive and asleep with a
  member read asleep then that still is (damage or a stun wakes every asleep member, which cannot sleep again within
  a round); 67% of in-view updates, 0 differences from the full reading in 155k: camps 2.9k -> 2.2k. Update 9.2k ->
  8.1k, turn 59.5k -> 57.2k. Tried and dropped: the awake/asleep camp boards in place of per-member reads (exact, but
  ~0.7k dearer: four tile tests a member cost more than the two host reads they replace).
- Out-of-fuel turns mostly end turns that arrive nearly empty: main runs out on purpose under end_turn_fuel (logged
  in the phase before, `warm tables` or `comms finish`), and the resumed turn then has ~83-91k (tick ~3.4k, stale tail
  ~2.7k), so a champion whose turns cost ~90k runs out every round. The camp-combat change (2026-10-27) took the six
  games from 100 to ~1100 (00contest: one champion's farm ran out for 64 rounds straight); the count is chaotic, 30
  to 345 on one map between builds that differ only in debug output.

## river: dash routes (2026-10-27)

bots/river/dash_route.htb. An exact search over (tile, dash cooldown 0-7): each turn one walk and, with the dash ready,
one dash of up to 2 king steps in either order; dash paths cross holes, altars, allies and unseen enemies, not walls,
camps, visible enemies or the enemy spawn; ready again 8 turns on. Checked against an independent forward search in
Python (50/50 boards). Scored: every route() call of a dasher on the 40 ladder maps, both sides (26k-45k queries a
run), each policy following its own moves turn by turn from the query's state; mean turns to the goal.

| policy (one run, optimum 7.59 turns, 23.5k queries) | excess turns | never arrive |
|---|---|---|
| walking only | +4.8 | 247 |
| route() of 2026-10-27 (7x7 priced search, crossings only when walking can't reach), emulated | +2.4 to +2.7 | 39 |
| greedy on the walking field | +1.3 | 77 |
| greedy on the field with crossings open | +0.24 | 5 |
| paced (that field in turns, dashes every 8) | +0.22 | 5 |
| routed: the crossing on the route traced, wait for the dash there or walk round | +0.066 | 5 |
| decision tree (depth 4, relative features, 300k labelled moves) | +0.065 | 5 |

The loss is almost all at crossings (open ground: ~0.08). The emulated route() walks round hole lines a dash crosses
(00road-of-riches -55 turns a query on walking alone). Trees on absolute turns lost to the formula (constant leaves
misrank ends one step apart); on relative features one ties it in rollouts (per decision 0.0113 against 0.0134,
cross-validated by map).

Landed: the routed policy on host fields (Router), Pathing::step_towards' first resort for dashers (dash_route::step;
off with dash_route::enabled); equally near tiles by step_tiebreak (bush, diagonal, aim). One field with crossings open (the walking one only for a route that crosses), kept
while goals and walls are; ends ranked on one read each. In rollouts +0.13 turns (12 never). Fuel a call: field
~1.1k, a turn's choice 2.8k (cooling) to 6.8k (dash ready, crossing). In play, 40 maps one side: out-of-fuel turns
941 and 1241 in two runs against 1176 with it off (parity: map medians 18 and 16; the counts swing between runs); moves: walk 36.5k, wait 7.7k (cooldown at a crossing, or a dash enemies forbid),
dash then walk 1.5k, dash 0.36k, walk then dash 0.22k, none found (route() decides) 10.1k. No win-rate A/B yet.
A/B, router on vs off (same river, own drafts), 40 ladder maps both sides at 91k-106k (6 budgets): 247/480 =
51.5% (95% CI 47-56); the 13 maps with hole lines 77/156 = 49.4%, the others 52.5%. Out-of-fuel lines 36.4k against
39.3k. Shorter dasher routes do not show in the win rate at this size; kept on (neutral).
Then (user's requests, same day): (1) speed-up dashes never skip a bush (pathing.htb skips_bush: a 2-step dash with a
bush among the tiles an equally short walk could pass), in the router, route()'s dash, dash_over and travel_dash; dash
casts skipping a bush 540 -> 197 a 40 games (the rest are fight, escape and landing-damage dashes, left as they were).
(2) Vendetta: with the dash cooling, a unit killable now (a hit, or two with the reset) from here or a step away is
killed first if from there a dash can then leave the reach of every camp awake after it (each live striker's square,
the killed one left out; a group's static threat board counts the killed one and blocks every escape); 567 kills a
40 games, every one readying the dash. Check ~270 fuel (median) when nothing is near. (3) The router's ends searched
with early stops (a move gains at most its length on fc; landings tried along the best step first; landing paths
tested directly instead of a landing board): a dash-ready choice 11.5k -> 5.7k, rollouts +0.15 (from +0.13).
Out-of-fuel turns with all on: 975 against 1176 off.
Pitfalls hit: `long` is 32 bits in WASM; paced() as a loop cost ~1k a call (closed form now); 7x7 bit windows read
in WASM cost more than the host's board ops.

## river: target audit (2026-10-27)

The user's rule: running a state must strictly improve its target. Full report, with the tracing copy and its
scripts: [river/audit/AUDIT.md](river/audit/AUDIT.md). In 40 ladder games against astraeus:
- 94-97% of farm, bank and siege moves (and 91.5% of capture's) come closer to their own goals.
- 6,129 back-and-forth cycles come from the targets: farm's changed 2,323 times, bank's 896, and about 1,330 were
  swaps with retreat.
- Farm switched targets 10,211 times (2,580 stepped back from). Causes:
  - fight turns pick by another rule;
  - crew and help override the value pick;
  - crew status hangs on who is strictly nearest;
  - partner terms are measured from us, not the group;
  - the value counts steps to the centre, while the walk targets attack tiles and treats all units as walls;
  - passing hits move toward the engaged group.
- Bank's altar choice and `may_chain` read only enemies visible this turn.
- Advance doesn't stop half the retreat swaps: what we see at B isn't kept at A. siege, ender, spent and support
  have no Advance. Fixes are proposed there; none made.

## Draft (2026-10-20, after the Heart of Ruin nerf)

Hecate vs hecate with only the draft changed, each pick on maps of its pick count ([hyperion/DRAFT.md](hyperion/DRAFT.md)).
These predate Khaos's Prism-specific play (CHANGES 82), whose draft starts with Prism.

- Heart of Ruin was the core (replacing it lost 12-48%); Marcella and Ryth were the best additions; Prism, Tavi and
  Willow lost in every slot of a trio. HoR/Stellar/Ren (a common ladder trio) lost 64-73% to the top three trios.
- 4th: Ryth 53-60% over Vesper or Cassi; Vendetta, Willow, Varg, Stellar and Ren lost as 4th. 5th: Stellar 57.9% and
  Willow 52.8% over Cassi, level with each other; Varg 47.7%, Ren and Vendetta lost.

## Draft: ladder win-rate model (2026-10-24)

- `tools/winrate` on 36302 ranked games of the top 30 teams from 2026-10-22: P(A wins) = sigmoid(S_A - S_B + Elo
  term), S summing each pick's intercept plus weights on 10 map features. Cross-validated log loss 0.6800 against
  Elo alone 0.6842 (held-out maps 0.6829 vs 0.6843). Champion effects are about ±0.05 logit; Ren is -0.125.
- astraeus drafting the model's top picks per map (`bots/variants/astraeus-wr`; Heart of Ruin on only 6 of 40 maps,
  Tavi, Cassi and Varg in): 37.5% of 80 against astraeus (40 ladder maps, CI 27.7-48.5), lost, where the model
  predicted +4.9 points. 7/12 on maps where it kept Heart of Ruin, 23/68 where it dropped it. The ladder values
  measure other teams' play of each champion; astraeus plays its own composition better.
- The whole ladder (764168 games from 2026-10-22, `tools/winrate/fetch.py`) does not help predict the top 30's
  games: trained on those games alone 0.6754 (57.1%), every game at full weight 0.6815, games below 2000 Elo
  down-weighted by a Gaussian in Elo no better at any width (h = 100: 0.6757). Champion values differ by skill
  (Prism +0.02 at the top, -0.03 ladder-wide; Ren -0.13 and -0.02), and pairings stay close everywhere (median Elo
  gap 3 ladder-wide, 21 for the top 30), so there are no lopsided games to learn from either.
- The ceiling is low: Elo alone, if exact, calls 54.6% of top-30 games, and knowing each 5-game group's winner
  calls only 70.2% (58% of groups are 3-2).

## koi: Fish's play on hecate (2026-10-19/20)

Against hecate-v1, 1010-2698 games. Three ports were kept (CHANGES 21).

- Level: damage-free stuns on any monster hitting an ally; a peel stun; clusters first; spells from range only while an
  ally tanks; enemy-race and late-race banking; Fish's commit and engage rules; Fish's turn priority; the 150-gold
  shopping recall; lazy chaining; waiting in bushes; cycle horizons 70-140; a Monster emblem first on big-group maps;
  Fish's caster draft on Monolith-only and shared-gem maps; Fish's targeting; a chasing caster stopping at nuke range
  in a bush.
- Lost: Fish's build table (−5 to −6: no Jungle means 16-50% more camp damage); the fitted engage rule as the
  retreat/advance rule (33-35%); crews by pick pairs (−4 to −10); solo range openers (−4.6); respawning groups worth
  1.3x (−6); casters chipping Monoliths on mixed maps; gold-free heal trips (−6); funnelling captures to Stellar (−4 to
  −5).
- koi vs hecate games are farm races on each side's own groups (steals ~28 gems a game each way); the first champion
  death decides. Fish converts engagements with less damage per kill (2.2k against 3.3k), through its killers' Focus
  and health.

## v36-v37: the teammate's Khaos builds (2026-10-22)

Ported from bots/v37 on top of CHANGES 90, against e14e7c3, each on its own draft (1094 games). Prism's camp stun on
another harmless group was kept (CHANGES 91).

- Lost: mixed-camp farm targeting (v36, "teacher" behaviour: farming a group whose members in reach both strike and
  do not, hit the lowest-health one first, usually the harmless cluster; Vendetta excepted when its reset can finish
  the weak one). With CHANGES 91 and Durability priority 47.2% (ladder 40.0, gen 48.6, gen-s1 46.7), against 50.7%
  without it; the monsters that strike live longer.
- Held, no measurable effect: Durability in the turn-order danger ratio (v36: ours scaled 0.9 against an enemy with
  a Durability emblem, theirs 0.9 against ours). With CHANGES 91 50.7% (555-539), the same total as 91 alone; it
  only moves a champion across a tenth of the ratio.

## Camp fire by reach: the clear plan, pricing and standing (2026-10-26, astraeus)

Against 00a638e, own drafts, ladder + gen + gen-s1 (1164 games).
- The exact clear plan (branch `claude/stoic-planck-o73876`, c8c6d9b: fire classes, a kill-order DP for up to 4
  strikers, stand goals, the draft's leads priced by it): 49.5% (46.6-52.4), ladder 42.1% of 140 (19 maps lost from
  both sides, 8 won), out-of-fuel turns 6011 vs 4108. Its wide bench against hecate on test drafts had read level.
- A simple version: price by reach (CHANGES 173) and stand by it. Before the first hit, walk to the attack tiles left
  after dropping each striker's reach, strongest first, while any remain; wake a sleeping farm group only from those;
  in the fight, a one-tile step to a cheaper tile (ranged only when the saving over the rounds left beats the round
  the step costs). A striker that would otherwise hit an ally who dies in fewer hits (health and shield over the hit
  after Durability) pulls us into its reach. 48.4% (45.5-51.2), ladder 41.4%, out-of-fuel turns +54%, after two fuel
  fixes: a member-pair loop over cluster fields (31k a call on 00vault) and the wake gate recomputed per member in
  range (90k a turn).
- Split: pricing only 51.3% (48.4-54.2; ladder 55.7), out-of-fuel +34%; standing only 49.1% (46.3-52.0; ladder 47.9),
  out-of-fuel level. Standing loses alone and more with the cheaper price. Kept: pricing, made cheap (CHANGES 173):
  50.5% of 1164, 50.4% of 512 on fresh 41026.
- `--fuel 10000000` with `debug_fuel` on stopped our bot's output at round 265 on 00vault (8 gems): measure fuel at
  the real budget or with bench.py.

## v61's features ported into astraeus (2026-10-27)

All of v61's (`bots/baselines/v61`) features astraeus lacked, in one bundle (af3ad8e, on deb288a): the retreat rework
(Prism's safe step off a lethal tile unless a cast kills or stuns in time the sole threat; Heart of Ruin below the
recall line keeps its ready dash, only a lethal landing first); hard-coded emblems ahead of the income model (off 3
picks Hunter for Vendetta and Heart of Ruin, Prospector for Marcella with clusters on our walk, else Treasure;
Prism's Prospector on cluster maps; on 3 picks Monster for everyone, Prospector on cluster maps, Tavi's Prospector
then Hunter); never Vesper, Vendetta in her slot; the 3-pick Tavi-map draft and Tavi's and Stellar's 3-pick roles;
`turn_rank_valid`. Against `bots/variants/astraeus-deb288a`, own drafts (`--no-test-draft`), ladder + gen + gen-s1
in six mixed batches of ~98 maps, 4 threads:

| | CAND win % | Games | 95% CI |
|---|---|---|---|
| all | 47.3 | 1164 | 44.4-50.1 |
| ladder | 50.7 | 140 | 42.5-58.9 |
| gen | 47.1 | 512 | 42.8-51.4 |
| gen-s1 | 46.5 | 512 | 42.2-50.8 |
| 3 / 4 / 5 picks (gen suites) | 46.6 / 46.6 / 47.0 | 296 / 324 / 404 | |

Batches in order: 43.4, 45.9, 48.5, 51.0, 50.5, 44.2. Out-of-fuel turns 4579 (CAND) against 3640. Lost as a bundle,
on every pick count; the parts were not A/B'd apart (the emblem rules and the Vesper swap had each already tested
level or lost: "Phase 3: drafts after patch 2.0.0", CHANGES 183-184).

Reruns on the same six batches, against deb288a:
- Vesper back and no Treasure fallback in the emblem rules (9d24efd): 45.4% of 784 after four batches (42.9, 45.4,
  46.4, 46.9), cancelled.
- Split (`research/hyperion/v61-split/`), each part with v61's drafts (Vendetta for Vesper): retreat 52.9% of 1164
  (50.0-55.8; batches 57.1, 56.1, 52.6, 54.6, 47.9, 48.9), kept as CHANGES 197; the emblem rules 47.3% of 588 after
  three batches (45.9, 51.0, 44.9; out-of-fuel turns 862 vs 598 in batch 3), cancelled; the 3-pick package (Tavi-map draft and Tavi's roles), on 3-pick maps only (ladder 12, gen 69,
  gen-s1 79, fresh suites seeds 1301 and 1302 78 each): 45.3% of 632 (41.4-49.2; batches 45.0, 48.8, 44.2, 42.9).
  272 maps split 1-1 (the package changes nothing there); of the 44 that went one way, CAND lost both games on 37:
  where it acts (presumably the Tavi maps) it loses about 5 in 6. Lost. Merged to main anyway with
  the rest of the port (bb73f75, branch claude/astraeus-v61-full), which was not A/B'd as a whole on main's base.

## Audit fixes (2026-10-28, astraeus)

The behaviour fixes of the 2026-10-28 code audit ([audit-2026-10-28](hyperion/audit-2026-10-28/README.md)), eleven as
one bundle (`audit/fixes-2026-10-28` 64bd853) against `bots/variants/astraeus-55a8c79` (main after CHANGES 202), own
drafts (`--no-test-draft`), ladder + gen + gen-s1:

| | CAND win % | Games | 95% CI |
|---|---|---|---|
| all | 49.7 | 1164 | 46.8-52.5 |
| ladder | 45.7 | 140 | 37.7-54.0 |
| gen | 49.4 | 512 | 45.1-53.7 |
| gen-s1 | 51.0 | 512 | 46.7-55.3 |

Out-of-fuel turns 4722 (CAND) against 4470. Level; ten kept as CHANGES 203. The eleventh, bot.cc's damage taken on
our spawn counted from full health, was dropped on review: `memory.damage` is read as a lasting drain
(`tribute_safe`, the altar retreat in bank.cc, upkeep pricing), but the spawn's turn-end heal undoes it, so it would
retreat from or refuse tributes at altars beside our spawn under harmless pokes (DIRECTIONS.md). Not re-run without it.

## Tribute stops (2026-10-28, astraeus; CHANGES 206)

DIRECTIONS fight 1, 4, 5, 11 and champions 1 as one bundle (7f1fc09, frozen in `bots/variants/astraeus-7f1fc09`)
against `bots/variants/astraeus-7884d8d` (main before it), own drafts (`--no-test-draft`), ladder + gen + gen-s1 split
into 6 mixed batches of ~194 games (`replays/ab/tribute-stops/`):

| | CAND win % | Games | 95% CI |
|---|---|---|---|
| all | 49.9 | 1164 | 47.0-52.8 |
| ladder | 50.7 | 140 | 42.5-58.9 |
| gen | 49.4 | 512 | 45.1-53.7 |
| gen-s1 | 50.2 | 512 | 45.9-54.5 |

Batches ran 51.0, 50.5, 50.0, 51.0, 48.4, 48.4. Out-of-fuel turns 4674 (CAND) against 4631. Level; kept (logic
fixes). Fixes 1 and 4 push opposite ways (more chasing vs less), so their debug counters ran in the candidate:
STOP-RANGE (fix 4 drops a stop that attack range alone made) 467 lines in 86 of 1164 games, ENDER-WALK (fix 1 keeps
a walking carrier that lands before our win) 220 lines in 5 games, nearly all from one game. Both are too rare to
move the rate.

## Kill worth, Prism's sight (2026-10-28, astraeus; CHANGES 207)

Three fixes (031c248, frozen in `bots/variants/astraeus-031c248`) against `bots/variants/astraeus-509d9fb` (main
before them, with CHANGES 206), own drafts (`--no-test-draft`), ladder + gen + gen-s1 (`replays/ab/killval-sight/`):
a kill is worth the tribute it cancels and a stun counts only on a survivor (DIRECTIONS plan 2); `attack_target` and
`best_hit` value hits by the strike search's `hit_worth` (params 1); Prism's recovery window is what Willow sees.

| | CAND win % | Games | 95% CI |
|---|---|---|---|
| all | 51.3 | 1164 | 48.4-54.2 |
| ladder | 48.6 | 140 | 40.4-56.8 |
| gen | 50.8 | 512 | 46.5-55.1 |
| gen-s1 | 52.5 | 512 | 48.2-56.8 |

Out-of-fuel turns 4777 (CAND) against 4487, +6.5%, within the spread one REF shows across runs. Level; kept.

- With a fourth fix, `main_stat` counting heals at their full 3x and landings in its prior (64ac1dd, branch
  `exp/main-stat-heals`): 49.2% of 959 when the run stopped (ladder 53.6% of 140, gen 48.2% of 512, gen-s1 49% of
  307; `replays/ab/killval-sight-heal/`, its gen-s1 games slowed by a laptop on battery). Within noise of the run
  without it, but no support either: not kept, untested alone. Willow's prior still picks Strength (15 against 27).

## Escapes and the mend turn (2026-10-28, astraeus)

DIRECTIONS abilities 1, fight 1, turn_order 1, bot 1 and bot 2, plus Prism's window counting Willow's ward (support 1),
as one bundle (`bots/variants/astraeus-step12`, the working tree on f61af92) against `bots/variants/astraeus-f61af92`,
own drafts (`--no-test-draft`), ladder + gen + gen-s1 (`replays/ab/escape-mend/`):
- an escape stun certifies on an enemy yet to act this round whose only turn before ours that is;
- Prism's escape-walk rule for every champion with a walk-excluding cast at enemies (no ground cast certified, so Ryth
  always walks), and after it a cast that allows walking (Cassi's stun);
- Ren keeps its escape dash as Heart of Ruin does, with only a killing cast (unit or landing) before a dash that clears;
- `offer_escape` bids only when what lands whatever the order (expected camp damage, this round's strikes) leaves us alive;
- the mend turn steps on spawn towards the next goal when no more exposed, as `home_trip` prices it, and mends under
  camp fire only while it misses more than the camps take a round.

| | CAND win % | Games | 95% CI |
|---|---|---|---|
| all | 55.1 | 1164 | 52.2-57.9 |
| ladder | 50.7 | 140 | 42.5-58.9 |
| gen | 53.5 | 512 | 49.2-57.8 |
| gen-s1 | 57.8 | 512 | 53.5-62.0 |

Out-of-fuel turns 4934 (CAND) against 4678, +5.5%, within the spread one REF shows across runs. A gain; kept as
CHANGES 208 (logic fixes) without a fresh-suite confirmation, and not split.

## Walk-only leaves, camp fire, escape stun, heal-step camps (2026-10-28, astraeus; CHANGES 209)

DIRECTIONS plan 1, safety 3, fight 8 and support 2 as one bundle (`bots/variants/astraeus-bundle4`, the working tree
on 95c4f5a) against `bots/variants/astraeus-085f676` (main before it), own drafts (`--no-test-draft`), ladder + gen +
gen-s1 (`replays/ab/bundle4/`):

| | CAND win % | Games | 95% CI |
|---|---|---|---|
| all | 50.2 | 1164 | 47.3-53.0 |
| ladder | 52.1 | 140 | 43.9-60.2 |
| gen | 48.0 | 512 | 43.7-52.4 |
| gen-s1 | 51.8 | 512 | 47.4-56.1 |

Out-of-fuel turns 4949 (CAND) against 4788, +3.4% (ladder 1020 vs 871, gen 1966 vs 2246, gen-s1 1963 vs 1671). Level;
kept (logic fixes). Not split: plan 1 and safety 3 fire far more often than fight 8 (Ryth escapes) and support 2
(Willow's heal step, 5-pick maps), so a split would start with those two. No firing counts were taken.
- The safety part (safety 3) was reverted after this run, over its pessimism about allies (DIRECTIONS safety 3). Main
  keeps plan 1, fight 8 and support 2, which were not A/B'd without it.

## Cheap exact fixes (2026-10-28, astraeus)

Nine small DIRECTIONS fixes as one bundle (`bots/variants/astraeus-cheapfix`, the working tree on b34f219) against
`bots/variants/astraeus-b34f219`, own drafts (`--no-test-draft`), ladder + gen + gen-s1 (`replays/ab/cheap-exact/`):
self_abilities 1 (Varg holds the reset for the shield by `shield_if_needed`'s own test), fight 5 (`sure_kill` counts
our shield against Ren's retaliation), bot_parts 1 (camp targets ranked while scanning, the best 16 kept), combat_priority
1 (our cooldowns a tick lower, as of our next turn), bank 2 (`bankable_bag`'s pocket test at the recall landing), camps 5
(`breach` charges `fire * turns` less the killed member's last phase), abilities 8 (`cast_at_enemies` always checks for
a stale turn), siege 4 (kite's reset on any spent attack), world 5 (an unseen shield expires at its owner's turn start).

| | CAND win % | Games | 95% CI |
|---|---|---|---|
| all | 49.7 | 1164 | 46.9-52.6 |
| ladder | 48.6 | 140 | 40.4-56.8 |
| gen | 50.4 | 512 | 46.1-54.7 |
| gen-s1 | 49.4 | 512 | 45.1-53.7 |

Out-of-fuel turns 4903 (CAND) against 4733, +3.6%, within the spread one REF shows across runs. Level; kept as CHANGES
210 without self_abilities 1, dropped after the run (DIRECTIONS self_abilities 1: it can now give up a reset to shield
against a camp it never woke). Not split; most of the fixes fire rarely, and no firing counts were taken.
- camps 5 is not DIRECTIONS' `turns - 1`: `breach` runs after a failed step, so we stand there until our turn after the
  kill, and the group fires every phase but the last member's.
- self_abilities 2 (`dash_to_attack` skipping a Ren whose retaliation would kill us) was dropped before the run: it
  needs us above half health, and 0.2x Ren's Focus never reaches that. A dash-then-refuse more likely comes from Heart
  of Ruin's landing drawing a second retaliation, which nothing sums.

## One turn-order model for every champion (2026-10-28, astraeus)

The turn order's "teacher" split removed (DIRECTIONS combat_priority 1-5, turn_order 1 and 3, idle_priority 1-3), as
one change (`bots/variants/astraeus-turnorder`, the working tree on 3f3aaac) against `bots/variants/astraeus-3f3aaac`,
own drafts (`--no-test-draft`), ladder and two fresh suites no A/B had used (`maps/fresh-82801`, `maps/fresh-82802`,
mapgen seeds 82801-82802; `replays/ab/turnorder/`):
- every champion bids for the kill and protect bands; Prism, Vesper, Ryth, Vendetta, Marcella and Heart of Ruin
  skipped `bid()` since CHANGES 82;
- `offer_channel` bids only when acting earlier can deny a cancel: not against a visible enemy's turn yet to come this
  round, an enemy we cannot act before even so, or a camp hit on a recall; a recall or teleport no longer prices the
  bag;
- `offer_heal` counts the ally's shield and damage taken, what lands before the heal whatever we bid (this round's
  turns of enemies yet to act, next round's of those acting first even so), and caps the heal after those hits;
- the plain scale's danger from Safety's `strike()` with live health, stuns and damage factors (combat_priority.h's
  copy and World's turn-start enemy snapshot deleted), full health on our spawn;
- the idle order by who loses least absorbing a camp's tie hit (`Safety::tie_hit`, the strongest hit had we acted
  first in every tie): those it leaves alive by hits in hand, then those it kills by fewest gems; no role table.
A read-only audit (same setup as the 2026-10-28 audit) found nine fixes, applied before the run.

| | CAND win % | Games | 95% CI |
|---|---|---|---|
| all | 50.8 | 1164 | 47.9-53.6 |
| ladder | 54.3 | 140 | 46.0-62.3 |
| fresh-82801 | 53.5 | 512 | 49.2-57.8 |
| fresh-82802 | 47.1 | 512 | 42.8-51.4 |

Out-of-fuel turns 10916 (CAND) against 12077: ladder 1001 vs 1024, fresh-82801 5806 vs 6993, fresh-82802 4109 vs
4060. A third fresh suite (`maps/fresh-82803`, seed 82803; `replays/ab/turnorder-82803/`): 52.0% of 512 (47.6-56.3),
out-of-fuel turns 2225 vs 2362. Pooled, the three fresh suites 50.9% of 1536, with ladder 51.1% of 1676 (48.7-53.5).
Level. b7-bands (every champion bidding the kill band alone) read 49.3% with +5% out-of-fuel turns; here they fell
9% (13141 vs 14439), mostly on fresh-82801. No firing counts were taken. Left out: the ally's camp hit before the heal and a
stun on the healer (offer_heal), both rare (only Willow heals).

## The goal after the strike search (2026-10-28, astraeus)

What the goal branches do after the strike search, measured and then bounded (`bots/variants/astraeus-batch1`, the
working tree on be29e4b) against `bots/variants/astraeus-be29e4b`, own drafts (`--no-test-draft`), ladder and the three
fresh suites (`replays/ab/batch1/`). `GOALX` debug lines (bot.cc `probe_search`/`probe_goal`) log every searched turn:
the branch, the move after the search against the intent's field, and any cast taken with the search's cast left.
- **Measured on main** (ladder, 48219 searched turns in 140 games): the goal's casts were rare (dashes 187, camp
  resets 113, enemy casts 2). The off-intent moves were the frequent case: chase walked off the farm field after
  15.7k searches, nearly all towards its prey. And the intent had no goal field at all in 36% of searches (17.4k):
  `walk_target` treated start_recall's every-turn recall as a channel, so neither act()'s turn-start `approach` nor
  `prepare_next_turn`'s ever ran off spawn. The ranged return ended 3419 turns, 416 of them Vesper's with a dash left.
- **Changed:** (1) `walk_target` ignores our recall: tribute and teleport still block, and the turn-start approach
  moved into decide() after the channel checks. (2) After a search that saw every enemy (`searched`: none of its own
  moves revealed one), chase only walks: no `dash_to_attack` and no hits of its own, since the search priced and
  passed on those and `strike_after` hits from where the walk ends. With no walk left it gives way to the other
  branches. (3) The ranged return is gone: with the walk spent, the goal keeps camp work and travel dashes, which
  the search does not price (it plays a dash only before a strike). Kite skips its walk section, and wants_shop is
  only tried with a walk. (4) Audit fix: `World::turn_start` for every "walked this turn" test (`cast_walked`, the
  search's `walked_first`, `strike_after`, siege, bank, decide's guard re-place). `see_again` moved `me().pos`, so
  an exclusive spell could be tried after a walk.
- **Rejected:** chase's prey given to the search as its intent (distance into attack range as progress). The intent
  matched chase 97% of the time, but `prey()` before the search ran its fight sims on a full budget, and the search
  then overran it: out-of-fuel turns 1851 vs 1027 on the ladder (+80%). A step is worth about 5 enemy health
  (`farm_step_value`), so the intent's direction only breaks ties between strikes. This agrees with the earlier
  "early `prey()` for the intent" result.

| | CAND win % | Games | 95% CI |
|---|---|---|---|
| all | 49.0 | 1676 | 46.6-51.4 |
| ladder | 57.1 | 140 | 48.9-65.0 |
| fresh-82801 | 47.1 | 512 | 42.8-51.4 |
| fresh-82802 | 49.0 | 512 | 44.7-53.3 |
| fresh-82803 | 48.6 | 512 | 44.3-53.0 |

Out-of-fuel turns 18081 (CAND) against 16334, +10.7%: ladder 1127 vs 1240, fresh-82801 6897 vs 5200, fresh-82802 7559
vs 7720, fresh-82803 2498 vs 2174. Level, with more out-of-fuel turns. Firing counts over the A/B (467k searched
turns):
- Searches without a goal field fell from 36% to 0.4%. Farm's crow-flies fallback fell 8179 -> 1859, but
  farm-kept-target rose 1194 -> 2314 and farm-no-route 2669 -> 3892, and `prey()` was cut short less (46562 -> 27751).
- Chase came after 90.6k searches, 51k of them walking off the farm field (the rejected intent's case).
- The goal took the search's cast 2.5k times, all unpriced kinds: travel dashes 1235, camp resets 1291.
Left open: the extra fuel. Most likely it is the turn-start approach, which has no fuel floor, now running on
every turn, with fresh-82801 taking most of it. Also open: Vesper may now `dash_across` right after a fight attack.
`dash_across` has no enemy-distance check (melee dashers already could). Farm's travel dashes after a search went
from 72 to 77 a ladder run.

### Follow-up: the goal-field fix alone, bounded (2026-10-29)

Part (1) alone on be29e4b, plus a bound on its cost (`bots/variants/astraeus-goalfield`; part (1) by itself is
`astraeus-gf1`). The full batch is saved as `research/hyperion/batch1-full.patch`, and parts (2)-(4) on top of this
change as `batch1-parts23.patch` (applies and builds). Same REF, drafts and suites as above.
- **Where the fuel went.** The extra out-of-fuel turns above were one map. gen-shared-gems-8280101604 (fresh-82801)
  gave +1575 of fresh-82801's +1697: both bots, REF included, run out on thousands of turns there, and the total
  swings by ~1.5k with the game's course. The same map went 2506 vs 3581 in this A/B and 820 -> 2518 on the bench;
  without it the bench totals are level. The fix does cost fuel, and all of it is approach searches:
  - 18 of 52 wide-bench games at 100M play byte-identically to main. In them, a turn costs +1254 (median +752) and
    turns over 100k go 165 -> 186. On fresh-82801's 154 identical games it is +1328 a turn, with turns over 100k
    2518 -> 2908.
  - A `debug_fuel` trace of 00expanse (identical replay): the `approach` meter goes 414 -> 1262 a turn. Nothing
    else changes.
  - Metered at the real budget (wide): the turn-start `approach` goes 222 -> 575 a turn (17.7k -> 48.9k searches,
    ~3k each, p99 ~11k). `prepare_next_turn`'s approach goes 18 -> 397 a turn, all spare fuel in the turn-end queue.
    A strike search costs the same with the field (16.1k vs 16.0k a run).
  - Why it re-searches: in 651 of 860 turn-start searches on the shared-gems map, the turn end before had the same
    field ready. `approach_ready` dropped a field when any camp tile anywhere on the map changed.
- **Bounded:** `Pathing::same_labels` keeps a field when at most 8 camp tiles changed and none of them can change a
  label:
  - none within range of the target group's members (its goals);
  - no new camp on a labelled tile;
  - no dead camp on or next to one.

  A verification build searched afresh after every keep: 17,939 keeps, 3.75M labels compared, 0 wrong. It cuts
  turn-start searches 48.9k -> 32.0k and turn-end ones 29.6k -> 25.7k. Turn-start approach fuel goes 575 -> 397 a
  turn (main 222). What still needs a search is a real label change: a member of the target dying (114 a turn),
  leaving the field (95), a camp change on or next to its labels (134), no field yet (38).
- **Audit fixes** (read-only auditor): the strike search's goal gain is `max(0, steps here - steps there)`. Tiles past
  ours are labelled or not depending on where the cached field was searched from, and so (rarely) on the turn end's
  fuel. The turn-start approach moved below the stun and game-ender returns. Neither end searches during a recall
  that lands next turn. Declined: skipping the farm field while carrying a bag. `banks_bag` can flip within the turn,
  and the Willow and farm readers would then read a cache-dependent field.

Bench, own drafts, against main as opponent (real budget: out-of-fuel turns and mean fuel a turn):

| | main | part (1) | bounded |
|---|---|---|---|
| wide, real budget | 939, 49.1k | 1027, 51.5k | 1175, 51.5k (gen-chambers-102206117 +247; without it 167 -> 156) |
| fresh-82801, real budget | 2492, 47.4k | 2060, 48.7k | 4099, 48.8k (shared-gems +1698; without it 1672 -> 1581) |
| wide, 100M: mean, turns > 100k | 49.4k, 2860 | 51.0k, 3061 | 50.9k, 3340 |
| fresh-82801, 100M: mean, turns > 100k | 47.8k, 19331 | | 49.0k, 19572 |

| | bounded win % | Games | 95% CI | OOF CAND | OOF REF | part (1) win % | OOF CAND | OOF REF |
|---|---|---|---|---|---|---|---|---|
| all | 47.3 | 1676 | 44.9-49.6 | 16019 | 16269 | 47.6 (45.2-49.9) | 14139 | 13918 |
| ladder | 45.7 | 140 | 37.7-54.0 | 1034 | 924 | 52.1 | 1184 | 1331 |
| fresh-82801 | 48.0 | 512 | 43.7-52.4 | 4413 | 5336 | 48.0 | 2387 | 2298 |
| fresh-82802 | 47.5 | 512 | 43.2-51.8 | 7975 | 7611 | 46.9 | 8006 | 7798 |
| fresh-82803 | 46.7 | 512 | 42.4-51.0 | 2597 | 2398 | 46.5 | 2562 | 2491 |

Lost: the fix, bounded or not, reads 47.3-47.6% with out-of-fuel turns level (`replays/ab/goalfield/`,
`replays/ab/goalfield-part1/`). The loss is the fix's own: the bound and audit fixes change nothing (47.3 against
47.6). Batch 1's parts (2)-(3) brought it back to 49.0.

At 100M fuel the same candidate is level: 49.8% of 1676 (47.4-52.2; ladder 55.7, fresh 50.2/48.6/49.0;
`replays/ab/goalfield-100M/`). So the loss runs through fuel, but not through out-of-fuel turns. The fuel gates fire
more often: on the wide real-budget bench, against main, prey-cut-short 2259 -> 3054, ward-no-bushes-fuel
1642 -> 2549, turn-order 981 -> 1388 and step-guard-entry 3372 -> 3733. The extra ~1.3k a turn in approach work,
part of it in the queue ahead of the warm-ups, leaves less for the turn's other gated steps. The goal field in
nearly every search gains nothing at 100M either. It is worth having only once the gates are gone, or once the
approach costs about what it did on main: a field repaired across camp changes, or one searched only for the
readers that use it.

### Follow-up: parts (2)-(3) without the fix (2026-10-29)

`batch1-parts23.patch` on be29e4b (it does not touch the goal field), plus `same_labels` from above, plus
`dash_across` taking its dash from `travel_dash_ready`: no travel dash across a wall with an enemy within
`travel_dash_clearance` (the batch 1 auditor's Vesper finding; it covers every dasher and the bag's walk to an
altar too). Frozen at `bots/variants/astraeus-parts23v`; same REF, drafts and suites. Not audited, and
`same_labels` not bench-checked byte-identical.

| | Win % | Games | 95% CI |
|---|---|---|---|
| all | 50.4 | 1676 | 48.0-52.8 |
| ladder | 49.3 | 140 | 41.1-57.5 |
| fresh-82801 | 53.1 | 512 | 48.8-57.4 |
| fresh-82802 | 49.6 | 512 | 45.3-53.9 |
| fresh-82803 | 48.8 | 512 | 44.5-53.2 |

Level, out-of-fuel turns 17282 vs 16041 (`replays/ab/parts23v/`). The three changes were not separated.

## CHANGES 199-228 against 3938c0f (2026-10-29, astraeus)

Main (m7) read only 50.8% against `bots/variants/astraeus-3938c0f`, though the chained A/Bs since (each against its
predecessor) sum to about +9 points, +5.1 of it CHANGES 208's. Frozen checkpoints against the same REF, own drafts
(`--no-test-draft`), ladder + gen + gen-s1, 1164 games each (`replays/ab/bisect-ladder-*`, `bisect-gen-*`,
`prefuel-vs-3938c0f`, `main-vs-3938c0f`):

| CAND | Adds | Ladder | gen | gen-s1 | All | OOF CAND / REF (gen + gen-s1) |
|---|---|---|---|---|---|---|
| f61af92 | 199-207 | 49.3 | 49.4 | 51.6 | 50.3 | 3711 / 3875 |
| 085f676 | 208 | 52.1 | 50.0 | 54.1 | 52.1 | 3878 / 3881 |
| be29e4b | 209-212 | 47.9 | 52.0 | 50.0 | 50.6 | 4008 / 3833 |
| 8ec2c4d | 213 | 49.3 | 51.2 | 50.0 | 50.4 | 3747 / 3723 |
| m7 | 214-228 | 42.1 | 50.4 | 53.5 | 50.8 | 2968 / 3615 |

No step is outside noise (about ±2 points between two runs). CHANGES 208's 55.1% against f61af92 shows as +1.8 here,
undone by 209-212; the rest are level, as their own A/Bs read. A chain of level A/Bs carries ±5 points of summed noise
and a kept outlier is inflated, so a chained sum is no estimate of the total: check it against a fixed old REF.
- CHANGES 209's walk-only leaves (the one part of that bundle never A/B'd as main has it) reverted on main (3f5c24e,
  `bots/variants/astraeus-nowalkleaf`), against the same REF: 50.8% (ladder 43.6, gen 50.4, gen-s1 53.1), the same as
  main. Neutral (`replays/ab/nowalkleaf-vs-3938c0f/`).

## No forced emblems (2026-10-29, astraeus)

bb73f75's emblem rules (v61's, never A/B'd on this base) removed: every `forced(...)` return in `best_emblem` (Prism's
Prospector on cluster maps; off 3 picks Hunter for Vendetta and Heart of Ruin and Prospector for Marcella; on 3 picks
Prospector on cluster maps and Tavi's Prospector then Hunter). 3-pick Monster stays a `best_stat` candidate for all.
`bots/variants/astraeus-noforce` against `bots/variants/astraeus-c6423d3`, own drafts, ladder + gen + gen-s1, 1164
games (`replays/ab/noforce/`): **52.8%** (50.0-55.7; ladder 52.1, gen 53.7, gen-s1 52.1), 3 / 4 / 5 picks 52.0 / 52.8
/ 53.7. Out-of-fuel turns 3257 / 3173. Confirmed on the fresh suite `maps/fresh-102901` (seed 102901, 512 games,
`replays/ab/noforce-fresh102901/`): 53.3% (49.0-57.6), 3 / 4 / 5 picks 51.2 / 49.3 / 57.8, out-of-fuel turns 1303 /
1182. Together 53.0% of 1676; kept as CHANGES 231.

## Emblem lab pilot (2026-10-29, tools/emblab)

12000 self-play games of astraeus 1c0d627 vehicles (`replays/emblab/pilot/`): drafts random or from the night1
ladder prior; each champion's first 8 new emblems each forced to a uniformly random (family, stat) with probability
0.4; gold priced 1.5x in farm choices; half the maps' vehicle pairs identical but for one flipped decision. 13.8
games/s on 94 slots; every forced arm bought; out-of-fuel turns 2.49 a team-game.

- **Pairs lose.** Paired games were identical up to the flip (2858/2860) and agreed on the winner 75.7% of the time
  (independent same-map games 50.6%), but a pair informs one decision and an independent game ~16: per game, pairs
  carried 0.24x the information on wins (1.02x on the wealth margin). The main run plays none.
- **Wins beat the margin as a target** here: a random arm instead of the model's at the first decision is -2.6 win
  points (z 6.8 on wins, 1.9 on margin).
- **A random emblem is a cost, not a lever, pooled:** forced at the first decision -2.6 points, the second -1.7, the
  third -0.7; pooled over champions, families differ by ~0.4 points, so any gain is in champion x emblem x stat.

## Emblem lab main run and the learned table (2026-10-29, tools/emblab)

172k games (pilot + 4 batches of 40k, 1c0d627 vehicles, no pairs, Stellar out of random drafts). Fit
(`fit.mjs`, intention-to-treat on the table's assignments, per pick count), CV log loss on wins: draft 0.6549, draft
per pick count 0.6515, + emblem terms 0.6465, + per pick count 0.6429, + family x map 0.6432; wins alone beat any
margin mix. Pick count moves champion strength (Prism +10.9 win points at 3 picks, +1.2 at 5; Willow -12.2 / +0.2)
and what the old chooser's own pick is worth (first emblem 3.5 / 2.8 / 2.0 points over an average arm at 3 / 4 / 5);
the per-size arm terms shrink to nothing. Learned arms beat the old choice by 0.5-1.5 points from the second emblem
on (Jungle-Health second, mostly at 5 picks; Health and Durability / Home / Tribute / Monster later), never reliably
at the first. For comparison the draft lab's own model on night1's 60k games: 0.6298 (pairs off 0.6303); our draft
terms there 0.6327.

A/Bs against 1c0d627, own drafts, ~2,544 games each (training-map suites / held-out fall-holdout, fresh-2918,
fresh-2934): table + 1.5x gold 52.0% (53.0 / 51.2); table vs 1.5x alone 52.0% (51.2 / 52.7); table + 1.0x 50.8%;
1.5x alone 49.6%. Kept as CHANGES 232.

## Emblem lab round 2 (2026-10-29/30, tools/emblab, PLAN.md)

800k games from 8fad72c on ~30k fresh maps (gen 4001, gen-s1 4002, fresh-4003..4120), each team's k-th new emblem
(k < 12) drawn in the game at 0.35 / 0.5 from eps-uniform + a softmax over the current logic's values, propensities
logged (recomputed from the logs to 0.02%). Per-decision fit (dfit.mjs, 16M forced rows): CV log loss baseline
0.54913, static arm terms 0.54866, + state 0.54857, + map 0.54817 (map terms help with 30k maps). Held-out
calibration of predicted arm gains ~1.0, but following the fit's argmax against the base: -0.1 +- 0.1 win points per
decision (winner's curse over ~39 arms). Doubly robust cross-fitted selection of one choice per (pick count, type,
ordinal), over all 44M reached decisions: z 0 -0.32, z 1 -0.13, z 2 +0.08 +- 0.03, z 3 +0.01 per decision; keyed also
by the current logic's pick family, worse at every z (cells too thin). A/Bs against 8fad72c on unused fresh suites:
z 2 from 18 batches 51.4% of 12,288 (fresh-4041..4044, 5001..5020) and 51.8% of 10,240 (5021..5040); z 3 51.0% of
12,288; z 2 from all 20 batches 53.0% (5021..5040) and 52.3% (5041..5060), kept as CHANGES 233; against the old
chooser 1c0d627, 55.0% of 10,240 (5061..5080).

Hierarchical empirical-Bayes pooling of the doubly robust cell means (all > type > (type, ordinal bucket) > (pick
count, type, bucket) > cell; choice = best posterior mean - 1 sd if positive): nested cross-fitted +0.21 +- 0.04 per
decision against the base (+0.13 to 0.16 over the shipped selection), moving 74% of decisions; pick count and single
ordinal carry almost no heterogeneity (sd 0.02-0.04 points against 0.65 across types). State, map, teammate and
previous-emblem splits, surrogate (next-checkpoint) outcomes and bagging did not help. A/B of the pooled table
(359 cells) against CHANGES 233: 50.6% of 10,240 (fresh-5081..5100) and 49.4% of 10,240 (5101..5120), 50.0% together:
per-decision gains did not add up once three quarters of decisions changed. Not kept.

## Draft lab draft2 and counter-aware drafting (2026-10-30, astraeus 26d273e; CHANGES 234)

590,711 self-play games (3/4/5 picks 194,937 / 194,881 / 200,893; 25 batches, ~0.10 s a game) from 26d273e (the
round-2 emblem table built in) on ~50k maps regenerated 2026-10-30 (gen, gen-s1, fresh-6003..6176; fresh-6177..6196
held out). Mix explore 0.5 / Thompson 0.35 / probe 0.15, half the games with one team from the ladder prior, Stellar
out of random drafts; night1's games started the fit at weight 0.25 for batch 0, then 0.

- **Model:** final cv log loss 0.6217; without map terms 0.6435 (map terms worth 0.022, night1 0.016), without pairs
  0.6229, without synergy 0.6228, without counters 0.6219, intercepts only 0.6476. Penalties b 64, w 1280, syn 320,
  ctr 5120. Counters at most ~0.012 logit; synergy up to ~0.37 logit (Vend+Pris -9.2 points on 3 picks).
- **Teams:** Vendetta, Marcella, Prism and HoR dominate; on fresh-6178 the counters model and the no-counter refit
  pick the same round-0 team on 242 of 256 maps.
- **A/Bs** (own drafts, fresh-6177..6196, 10,240 games each): no-counter refit against 26d273e 51.9% (50.9-52.9),
  kept; counters (fixed) against 26d273e 50.0%, against the no-counter refit 48.4%. Counters at the prior only (no
  re-rank) 48.7% of 2,048 against the no-counter refit. Re-ranking changes the team on ~11% of maps (near ties), and a
  change restarts the draft analysis's leads on 100k-fuel draft turns; counters this small buy nothing to pay for it.
- **Bug found on the way:** the first counter build lost 40.7% to the no-counter one. Re-ranking all 792 teams on a
  later draft turn cost 60-90k fuel (debug), and on 5-pick maps the turn ran out before picking, so the rest of the
  draft was random (the engine: "ran out of fuel without picking"). A cheaper walk (still ~41%) did not fix it;
  cached round-0 team scores with an exact stopping bound (picks x the largest row sum of |ctr|) did (18-40k).
  Re-sorting the remaining picks each round had also restarted the leads on most maps; kept champions now keep
  their order.
- Data: `replays/draftlab/draft2` (games.jsonl 1.8 GB), `replays/draftlab/draft2-noctr` (links + refit).

## Macro overhaul: four parallel branches and a merge (2026-10-30, astraeus ef8f0b8)

Four agents each rebuilt astraeus's macro (targets, farming, banking, retreat, coordination, comms) independently
from ef8f0b84, aiming at 60% against `bots/variants/astraeus-ef8f0b8` at unlimited fuel, each on its own dev and
held-out fresh suites; a fifth (macro-5) merged them. The branches were local and deleted after the merge (tips in
[hyperion/macro/](hyperion/macro/README.md), with each branch's log, replay measurements and open ideas); the
frozen copies below keep the final bots on this box (git-ignored). Main shipped macro-4's bot with `max_wait` 3 (CHANGES 235-241).

**Normal-fuel comparisons**, 10,240 games each, own drafts, 0 failed matches. Against ef8f0b8 on fresh-7021..7040, the
others on fresh-7001..7020 (all regenerated, unused before; git-ignored, rebuild with `mapgen.mjs suite --seed N`):

| Bot | vs astraeus-ef8f0b8 | vs hyperion-ef8f0b8 | vs astraeus-54254fb | Frozen copy |
|---|---|---|---|---|
| ef8f0b8 (before) | - | 79.5% | 59.9% | `variants/astraeus-ef8f0b8` |
| macro-1 (95500f7) | 59.5% (58.6-60.5) | 83.1% | 66.9% | `variants/astraeus-95500f7` |
| macro-2 (d8821f9) | 52.7% (51.7-53.7) | 79.9% | 60.9% | `variants/astraeus-d8821f9` |
| macro-3 (77e54381) | 50.0% held-out at unlimited fuel; not compared | | | branch only |
| macro-4 (67cad24 = bot 83804615) | 59.9% (58.9-60.8) | 83.3% (82.5-84.0) | 66.4% (65.5-67.3) | `variants/astraeus-67cad24` |
| macro-5 merge (532f164b) | 59.6% (58.7-60.6) | 83.8% (83.0-84.5) | 67.4% (66.5-68.3) | `variants/astraeus-532f164` |

Out-of-fuel turns against ef8f0b8: macro-1 27.4k vs 26.9k, macro-2 32.3k vs 26.4k, macro-4 26.9k vs 27.5k. macro-4
against hyperion 23.4k vs 16.6k, against 54254fb 26.6k vs 36.5k. The branches' unlimited-fuel held-out readings (macro-1 59.7, macro-2 53.8,
macro-4 58.4) held at the real budget within about a point.

**What the branches agree on** (each found it separately in mirror replays and A/Bs):
- Champions walk ~51-55% of their time, and a solo team (against `bots/idle`) reaches 1000 gems at ~875-880 rounds,
  barely faster than the mirror's winner: the bot's own farming speed binds, not supply (camps sit up and unworked).
- Every gain came from champions spending more time working: giving way less (pack zone, retreat ratios,
  pursuit), later recalls (threat-aware or lower lines), recall as travel (recall out to farm, hermes's prototype, ported by macro-2
  and macro-4), no standing at respawns (max_wait). Caution loses: earlier recalls, costlier camp risk, longer waits.
- Coordination toward fights lost or was level everywhere: hunts (macro-2, twice), burst ops (macro-2), distress
  and assist (macro-3), tank formation (macro-1), team ops for strong groups (macro-4), as eris's duos and hunts.
  Shared information pays a lot (macro-3: dropping the capture record -6; macro-4: no comms -6), but adding more of
  it did not, and enemy sightings in comms hurt (macro-4, -2: allies give way to enemies they cannot see).
- Sharp optima, don't retest blind: recall-or-walk banking (walk-only banking 36.6%, slack in the comparison 35.3%),
  Prism's hoard (cap 150 46.7%), camp_risk 0.35 on macro-4's base, retreat ratios past 3.0/3.5 (macro-1, macro-4;
  on macro-3's base home_retreat_ratio 1.5 and 3.0 both lost, unexplained).
- Solo screens (`solo.py`) understate anything that changes exposure (macro-2's E2: -2.4% solo, -13 points in play).

## Macro refactor, macro-1 (2026-10-30, astraeus from ef8f0b8; notes in hyperion/macro/macro-1.md)

All against the frozen `bots/variants/astraeus-ef8f0b8`, own drafts, unlimited fuel (`--fuel 100000000`). Dev suites:
ladder, gen, gen-s1, fresh-6003..6018 (9356 games); probe suite: ladder, gen, gen-s1, fresh-6003..6008 (4236).
Design log and replay findings: [hyperion/macro/macro-1.md](hyperion/macro/macro-1.md).
- Claim board in comms (a slot per body: claim, ETA bucket, need bit; ownership by seniority unless 2+ buckets
  earlier; crews on any owned group): 51.8% of 9356. Crews only on a need bit: 42.4% of 396 (idle is worse);
  crews limited to one partner 46.5% of 396.
- Altar locks (enemy locks worn to 1 hit in passing; final hit and tribute in one turn; relock check; enemy-side
  locks): 52.2% of 9356 on top of the board. Stall breakers (sieges/kites without progress, contest standoffs, sealed
  altars, held respawns, corridor jams): 51.8% of 9356 with both (stalled champion-rounds -61%, mostly mirrored).
- Shared-clear tank formation (tank by absorb tier, supports on tiles the tank covers, tank first in turn order):
  52.2% of 2188; 86% of formation hits land on the tank but damage and heal trips per clear unchanged (every awake
  monster hits someone). Not kept (m1/tank.patch in hyperion/macro/scratch.tar.gz).
- Single-knob probes on the board version (probe suite unless noted): home_power 1 / 0 51.5 / 49.2 (dev); recall
  line 0.25 / 0.15 / 0.5: 53.0 / 51.7 / 42.5; camp_risk 1.0 / 0.2: 42.5 / 50.7; chain_bag_limit 90 / 20: 51.6 /
  51.0; stickiness 2.0: 51.2; no shop trips 50.2; no turn-end recall feint 48.9. On the lock+stall version (51.8 dev):
  crew value x1.5 52.3; help/partner radius 16/20 51.9; cycle horizon x3 / x0.5 / x0.25: 49.1 / 53.5 / 53.3;
  horizon x0.5 with recall 0.25 and camp_risk 0.25: 55.4; max_wait 2 / 10: 54.6 / 50.5; retreat ratios 3.5/3.0:
  52.5; pursuit_steps 1: 51.6; gold_price_scale 3: 51.1; no chase 49.4; chase off own ground too 47.5.
- Time-at-work package on the lock+stall version: horizon 50 + recall 0.25 + camp_risk 0.25 + max_wait 2 + retreat
  ratios 3.5/3.0 (c1): 57.6% of 9356 (56.6-58.6); captured +58 gems a team-game, idle 4.2% vs 5.8%, deaths slightly
  up. Then max_wait 0 58.7, horizon 35 58.9, horizon 25 (e926bbeb) 58.7 on the probe suite and 58.9% of 5120 on
  fresh-6009..6018 (dev 58.8%); held-out fresh-6067..6074 59.7% of 4096 (58.2-61.2), at the default fuel 59.8%.
  Further knobs flat or worse: ratios 4.5/4.0, recall 0.2, camp_risk 0.2, stickiness 1.0, chain_bag_limit 60,
  heal_trip_fraction 0.4.
- A healthy champion (75%+ health) goes home to shop only with two emblems' gold (95500f74): 59.3% of 4236 on the
  probe suite against 58.7 without it.
  Full dev 59.2% of 9356 (58.2-60.2); held-out 59.7% of 4096 (58.2-61.2); default fuel 59.3% (57.8-60.8),
  out-of-fuel turns 11028 vs 9849. On top of it, all level (dev): horizon 35 59.2, heal_trip_fraction 0.4 59.3,
  hurt_health_fraction 0.4 59.2, recall line 0.30 59.6.

## Macro rebuild, macro-2 (2026-10-30, astraeus ef8f0b8; notes in hyperion/macro/macro-2.md)

Each against `bots/variants/astraeus-ef8f0b8`, own drafts, unlimited fuel (`--fuel 100000000`). "Dev" = ladder, gen,
gen-s1 and fresh-6019..6034 (9356 games); "subset" = ladder, gen, gen-s1, fresh-6019..6024 (4236 games; C1 there
reads 53.4%). Mirror-replay facts behind the designs are in macro-2.md (champion time: walking 55%, camp
attacks 17%; contacts: 1v2 12% death within 10 rounds against 2.9% for 2v1).

| Variant | Win % | Games | 95% CI | What |
|---|---|---|---|---|
| comms v2 + hunt op | 48.6 | 9356 | 47.6-49.6 | shared op record; allies converge on an enemy engaging one of ours |
| comms v2 alone | 50.1 | 9356 | 49.1-51.1 | op record in place of the bag slot and second sighting: free |
| burst op (smoke) | 45.6 | 652 | 41.8-49.4 | self-selected team clears of monster-heavy groups; calls mostly unmanned |
| E1 no shopping-only trips | 47.3 | 9356 | 46.3-48.3 | shop trips pay |
| E2 bank by walking, never by recall | 36.6 | 9356 | 35.7-37.6 | recalls 31 vs 50 a team-game, collected gems -6.5%, gold -7%; solo only -2.4% |
| buddy cohesion | 49.4 | 9356 | 48.4-50.5 | farm values a group by its distance to working allies, by exposure; retreat toward support |
| rfarm: recall out to farm | 50.7 | 9356 | 49.7-51.7 | hermes's idea, priced like HomeTrip (heal and emblem value) |
| Y1 = rfarm + no home pack zone when healthy | 52.5 | 9356 | 51.5-53.5 | collected +2.8%, deaths level |
| Y2 = rfarm + healthy never "pursued" in want_home's stand | 50.4 | 9356 | 49.4-51.4 | |
| Y3 = rfarm + recall line 0.35 -> 0.25 | 52.1 | 9356 | 51.1-53.1 | |
| C1 = rfarm + Y1 + Y3 + buddy | 54.1 | 9356 | 53.1-55.2 | collected +2.7%, gold +2.3%, but deaths 5.3 vs 4.5 (own side +0.65) |
| C2 = C1 + hurt fraction 0.4, brake_bag 20 | 53.6 | 9356 | 52.6-54.6 | |
| D1 = C1 + low line 0.10 with no enemy near | ~51.2 | 3718 | stopped | below 0.25 hurts even with no enemy seen |
| D2 = D1 + hunt with calls widened to unseen allies | ~46.4 | 2209 | stopped | the hunt loses again |
| P1 = C1 + home_power 1 | 54.4 / 54.0 | 4236 / 9356 | 52.9-55.9 / 53.0-55.0 | subset / dev: no gain over C1 |
| P2 = C1 + max_wait 10 | ~51.8 | 2371 | stopped | |
| P3 = C1 + chain_bag_limit 90 | ~53.0 | 4171 | stopped | level with C1 |
| P4 = C1 + no chase walks | ~46.9 | 2018 | stopped | chasing prey is worth ~7 points |
| P5 = C1 + recall line 0.20 | ~53.5 | 1942 | stopped | level with C1 |
| P6 = C1 + prey off our ground below 75% health (was 50%) | ~50.4 | 1489 | stopped | |
| Q1 = C1 + healthy home pack zone back, radius = each member's strike reach + 1 | 52.9 | 4236 | 51.4-54.4 | subset; level |
| D3 = C1 + low line 0.35 with an enemy near, 0.25 otherwise | ~52.6 | 3321 | stopped | |
| R2 = C1 + recall-to-bank / capture recall taken up to min(8, bag/8) rounds slower than walking | ~35.3 | 1542 | stopped | with E2: the recall-or-walk choice is a sharp optimum at the exact time comparison |
| **C1 held out** (fresh-6075..6082) | **53.8** | 4096 | 52.3-55.4 | |
| C1 held out, default fuel | 53.3 | 4096 | 51.7-54.8 | out-of-fuel turns 12,438 vs 10,265 |

- Coordination toward fights lost every time (hunt twice, bursts, as eris's duos and hunts did): converging pulls
  champions off farming into fights the mirror brings to you anyway. What won keeps champions productive: not
  yielding home ground when healthy, staying out to a lower health line, recall as travel.
- Solo farming (`tools/solo.py`) understates anything that changes exposure: E2 read -2.4% there and -13 points in
  the A/B. Walking carriers meet enemies and yield.

## Macro redesign, macro-3 (2026-10-30, astraeus ef8f0b8; notes in hyperion/macro/macro-3.md)

Against `bots/variants/astraeus-ef8f0b8`, own drafts, unlimited fuel (`--fuel 100000000`). Dev suites: ladder, gen,
gen-s1, fresh-6035..6050 (9356 games); smaller runs use a subset (n given). Measurement tools:
`tools/replay/turn_budget.py`, `tools/replay/walk_audit.py` (brought to main).
- Measured (mirror, 582 games): walking 53% of champion time on both sides, also unopposed (solo, 878 rounds to 1000
  gems; the mirror winner takes ~970). r1-300 both sides spend time alike; deaths differ. Most deaths start healthy
  (median 82% HP): farming walk-ins 31%, healthy retreats caught 27%; an ally within 8 in 64%.
- Prism retain cap 150: 46.7% of 9356 (lost; Prism's hoard is power). Allies jammed in a corridor line give way
  (make_way past several allies): 50.2% of 9356, kept (fixes a 1270-round stall).
- Farm lab on solo (solo.py vs bots/idle, 326 maps): wait0, noshop, noQ, bigbag, walk x1.5, stickiness, horizon,
  help radius, crew x0.8/x1.25 all within +-1%; no crews +11.1% slower (crews are worth a lot); no home discount -3.0%.
- Distress beacon + assist branch: replacing the camp/second-sighting comms slot lost 44.6% of 2750; the comms
  change alone (assist off) 43.4% of 1469: the shared capture record is worth ~6 points. With the slot shared three
  ways (capture > distress > second sighting): 50.6% of 3212, deaths -8%, kept.
- On that: home_power 1 49.6%, 0 49.3%, wait0 + crew x0.8 50.1% (2188 each); pack_ally_radius 8 49.9% (6.6k), 12
  50.8% (2188); fight_ally_radius 8 46.8% (1744); home_retreat_ratio 1.5 47.4% (6k). All level or lost.
- Unseen camps reveal nothing, not even liveness (probe-camp-unseen): the YAML said otherwise, fixed.
- Prism as the team's carrier (farm values Prism crewing or taking over allies' captures at the full reward; allies
  step off): our Prism's bag 248 vs 110 at r600 and Prism deaths 0.70 vs 1.24 (140 ladder games), but 50.7% of 9356
  (pc1); with carrier distress drawing help from farther, 48.8% of 3212 (pc1 read the same on those suites). Marcella
  as carrier (no Prism): smoke 15/38 vs 21/38, her gold fell; dropped.
- On the carrier: assist_steps 8 50.5% of 3212, 20 48.0% of 1062; retreat toward a nearer healthy ally from the first
  retreat turn 49.5% of 3056; no turn-end recall feint (recall only when continue_recall would keep it) 48.4% of
  1935. All level.
- What the level results share: in the mirror every macro knob and most additions sit on a flat optimum; the only
  large moves were losses from breaking something (shared capture record -6, Prism cap -3, counting farther allies
  in fight sims -3, more aggressive retreat ratio -2.6). Claim churn (~7.6% of champion time on trips dropped
  before the first hit) is the largest measured waste not yet attacked (needs claim arbitration, not stickiness).
- Claim arbitration by arrival (both claim g: the one arriving sooner by g's centre field keeps it): 50.4% of 3212.
  gold_price_scale 1.0 / 2.5: 51.5% / 50.6% of 3212. Final branch (77e54381) held-out fresh-6083..6090: 50.0% of
  4096 [48.5-51.6] at unlimited fuel; 49.7% [48.2-51.3] at the default fuel, out-of-fuel turns +44%.

## Macro overhaul, macro-4 (2026-10-30, astraeus from ef8f0b8; notes in hyperion/macro/macro-4.md)

All against `bots/variants/astraeus-ef8f0b8`, own drafts, unlimited fuel; "dev" is ladder + gen + gen-s1 +
fresh-6051..6066 (9356 games), "subset" ladder + gen + gen-s1 + fresh-6051..6054 (3212).

- **Self-play picture:** champions walk 51% of their time (empty 32%, with a bag 19%), damage camps 18%; ~60
  walks a team-game out of spawn (heal, bank-via-spawn and shop trips). Camps are abundant (groups up and asleep
  hold ~60% of the map's gems a round); champion time and health bind. Chosen groups are a median 11 tiles off,
  the nearest live one 9: travel is geometry, not choice.
- **Kept:** threat-aware recall line (0.18 with no credible enemy near, else 0.35) 53.3% dev; comms without
  enemy sightings + a claim field per ally 55.0-55.3% dev; walking-distance escape from camp fire 55.9%;
  recall out to farm (hermes's prototype, the stop's heal credited) 56.3%; pack zone radius 5 and retreat
  ratios 3.0/3.5 58.3%.
- **Comms ablations** (subset, on the recall line; it read 54.0%): no comms 47.9; no sightings 55.7 (they feed
  Safety's pack zone and threats, so champions give way to enemies a teammate saw); no claims 50.5; no
  capture records 47.2. More camp info (two capture slots + a group-health slot): 54.0% dev, nothing.
- **Wards** (subset): none 47.5% (on 55.5); no planned wards -1; no bush wards -3.
- **Lost or level:** strong groups as team operations (real solo budget, nearest-champion crew damage,
  assemble before waking): 48.1% dev, strict 38.4%: bold chips of strong groups are what pays (camps never
  regenerate). camp_risk 0.25 / 0.20: 51.8 / 51.1 (0.35 is a peak). Cohesion bonus near allies' claims
  52.4-52.6. Chasing healthy enemies off our half 50.2 (subset, -4). Monolith bursts at 35/50 rounds -4/-5.
  max_wait 15 -5. Uniform recall 0.15 48.9, 0.20 51.2, 0.25 ~53.5-53.9 (subset/1164).
- **Giving way less** (the last gains): pack radius 5 + retreat ratios 3.0/3.5 58.3%; then pursuit 2, hurt 0.35,
  brake bag 25: 59.4% dev (58.4-60.4). Past the peak: ratios 4.0/4.5 58.5, pursuit 1 57.9, radius 4/3 57.4/57.6,
  per-member radius 57.9. Old comms (with sightings) on the final bot 57.9: sightings still hurt.
  Level: safe line 0.14 59.6, ward following the champion 59.2, ally radius 8 58.0.
- **Final (83804615) on held-out fresh-6091..6098 (4096 games): 58.4% (56.9-59.9) at unlimited fuel, 59.2%
  (57.7-60.7) at the default budget.**

## Macro merge, macro-5 (2026-10-30, astraeus = macro-4's bot + max_wait 0; notes in hyperion/macro/macro-5-merge.md)

Normal fuel, own drafts. Dev = ladder + gen + gen-s1 + fresh-6100..6115 (9356 games); held-out fresh-6116..6123
(4096). Base: macro-4's bot (83804615, `variants/astraeus-67cad24`), chosen over macro-1's (level at normal fuel)
for its many separately measured pieces and smaller code; overlapping knobs (recall line, camp_risk, pack zone,
recall out to farm) kept at macro-4's values, retreat ratios identical on both.
- **Against the base, dev:** max_wait 0 (macro-1's; recall out to farm keeps 5) **52.3%** (51.3-53.3), broad (16 of
  19 suites over 50); with cycle horizon 25 too 52.4; horizon 25 alone 50.5; two-emblem home trips (macro-1) 50.1;
  make_way past a line of allies (macro-3) 49.9; macro-1's claim board in place of macro-4's comms 49.0, with 15%
  more out-of-fuel turns. Only max_wait 0 kept.
- **Comms layout:** on the merged bot (base + horizon 25 + max_wait 0), macro-4's layout 61.3% (60.3-62.3) vs
  ef8f0b8 against the board's 60.3% (59.3-61.2); board vs macro-4's head to head 49.3% (48.3-50.3), out-of-fuel
  turns 28,495 vs 24,426. macro-4's kept (it also drops ~400 lines). The board brings sightings back, which
  macro-4 measured at -2.
- **Final 532f164b, held-out:** 58.3% (56.8-59.9) vs ef8f0b8; 50.0% (48.4-51.5) vs the base (dev and held-out
  pooled about +1.6 over the base).
- **Final comparisons, 10,240 games each, normal fuel, own drafts:**
  | vs | maps | win % | 95% CI | out-of-fuel turns cand / ref |
  |---|---|---|---|---|
  | astraeus-ef8f0b8 | fresh-7021..7040 | **59.6** | 58.7-60.6 | 26,994 / 27,357 |
  | hyperion-ef8f0b8 | fresh-7001..7020 | **83.8** | 83.0-84.5 | 24,378 / 16,341 |
  | astraeus-54254fb | fresh-7001..7020 | **67.4** | 66.5-68.3 | 27,772 / 36,703 |
  Against macro-4's own (59.9 / 83.3 / 66.4) and macro-1's (59.5 / 83.1 / 66.9): level to +1.
- Not tried (level or lost on their branches, or overlapping a kept setting): macro-1's altar locks, stall
  breakers, camp_risk 0.25, flat recall 0.25; macro-2's hold-own-side, low lines, cohesion, hunt and burst ops;
  macro-3's distress/assist and Prism carrier.
- **Shipped instead:** macro-4's bot with `max_wait` 3 (CHANGES 241 on main; macro-5's own CHANGES 241 is the
  max_wait 0 version and stays on its branch). Against macro-4's bot (`variants/astraeus-67cad24`) on
  fresh-7041..7060 (unused before), normal fuel, own drafts: **51.2% of 10,240 (50.2-52.2)**, out-of-fuel turns
  26,669 vs 27,360. Frozen as `bots/variants/astraeus-b378e30`.
## fuchsia's camp targeting in demeter (2026-10-28, demeter = astraeus)

fuchsia (an older bot, not in this repository) farms with a greedy loop: the group hittable soonest, the nearest tile in range and
sight of a live member, the weakest member in reach, and a wait beside the camp while it respawns. Against
`bots/idle` it is far slower than astraeus (`tools/solo.py`, 90 maps both sides, 500k fuel, both on their own
drafts): round to 1000 +49% [+40, +59], tributed @600 458 vs 629, 31 games never at 1000 vs 3. Its parts, ported into
demeter behind switches (`bots/variants/demeter-fuchsia-port`, a variant per combination), each against astraeus
against idle at 500k fuel; round to 1000, negative faster:
- Weakest member first (T): 1164 games +0.2% [-0.3, +0.6], tributed @600 -6.1 [-11.2, -1.5].
- One stand tile plus the respawn wait beside the camp (SrWb): 1164 games +0.4% [-0.1, +1.0].
- All of them (TSWb): 1164 games +1.2% [+0.7, +1.8], tributed @600 -9.7. Lost.
- Respawn wait alone (W) -0.4% [-1.7, +0.8], the stand tile alone (S, Sr) +0.1 to +0.2%, 180 games each: level.
  Stand tiles weighed by exposure (E): +2.0% and 7184 out-of-fuel turns at 500k. Lost.
No vs-astraeus A/B was run: nothing helped farming. demeter was left equal to astraeus.

## Fish's draft in demeter, and the ladder farm gap (2026-10-29, demeter = astraeus 1c0d6277)

demeter forced to Intercontinental Fish's drafts (`bots/variants/demeter-fishdraft`: 3 picks HoR, Marcella, Vesper; 4
Cassi+Issac, HoR, Vendetta, Vesper; 5 adds Marcella) against demeter on its own drafts, each against `bots/idle`
(`solo.py`, ladder + gen, 326 maps both sides): round to 1000 +3.1% [+1.9, +4.3] (slower), collected @150/300/600
−4.1/−11.5/−28.8, tributed @150 +12.4 (earlier banking), gold @600 −96. Lost: the ladder farm gap is not the draft.
Against idle, demeter collects 132 gems by r150 on the ladder maps where, on the ladder, we capture 78 and the top
teams 110. The gap comes from contests and crews on Elk/Golem and big middle groups, not small-group farming:
[demeter-farm-2026-10-29.md](demeter-farm-2026-10-29.md).

## Gold-first farm changes (2026-10-30, demeter = astraeus 1c0d6277)

For the gold priority: more gold earned, never fewer wins. Each change against `bots/variants/demeter-base` (=
demeter), own drafts (`--no-test-draft`), ladder + gen + gen-s1, 1164 games (`replays/ab/<name>/`); gold and gems are
`tools/ab_farm.py`'s CAND - REF per team-game, 95% CI. Designs and analyses in `replays/wf3-scratch/`, `replays/wf4/`,
`replays/wf5/`.
- **Gold lean** in farm choice (`bots/variants/demeter-gold-weight`, c2): a gold is worth p·min(1.5, 1 + 2p) gems,
  p = `prices().per_gold`, for capture shares, Marcella's tribute gold and the crystal toll; the shop is unchanged
  (`dmw-gold-weight-ab`): **50.9%** (48.0-53.7; ladder 47.9, gen 51.8, gen-s1 50.8), gold @300 +38.1 [+14.8, +59.9],
  @600 +46.8 [-10.0, +102.2], capture gold @300 +39.7 [+21.8, +56.6], tributed @600 -9.2 [-21.2, +2.1], out-of-fuel
  turns 3166 / 3186. Ladder gold @300 -40.4 [-133.1, +51.3]; 4-pick drafts without Cassi 45.9% (196 games),
  tributed @600 -29.3 [-59, -2]. Against idle (`dmw-gold-weight-solo`, 582 maps, 500k fuel): gold @300 +39.1, @600
  +95.3, collected @300 -8.8 (3-pick Cassi drafts -33.3). Kept. Fresh suite (`mapgen suite --seed 103001`,
  `dmt-gold-weight-confirm`, 512 games): **52.1%** (47.8-56.4), gold @300 +39.3 [+11.1, +65.3], @600 +61.5 [-8.2,
  +130.7], capture gold @300 +33.5 [+12.8, +54.8], tributed @600 -6.8 [-23.7, +10.1], out-of-fuel turns 1774 / 1697.
  Confirmed; not yet merged into demeter.
  - r2, p + min(2p², 0.125) and no lean for Cassi or Tavi on its gold maps (`demeter-gold-weight-r2`,
    `dmt-gold-weight-r2-ab`): 48.5% (45.7-51.4), gold @300 +33.3 [+10.7, +54.6], @600 +55.9 [+0.4, +111.9], tributed
    @600 -4.9 [-17.9, +7.7]; 3-pick Cassi drafts 38.3% (94 games) against c2's 52.1%. Against idle it keeps c2's gold
    for fewer gems (collected @300 -5.6; 3-pick Cassi -27.4). Lost to c2.
- **Pay-aware holder** (`demeter-pay-aware-holder`): of two or more allies on a one-holder group, the one the capture
  pays most (gold bonuses, Marcella's 2 gold a gem) holds and the rest yield; a free champion steps onto an ally's
  counting hold that would pay it more (`dmt-pay-aware-holder-ab`): **48.0%** (45.2-50.9; ladder 45.0, gen 47.7,
  gen-s1 49.2), gold @300 +34.3 [+15.0, +55.7], @600 +40.3 [-10.5, +95.1], capture gold @300 +9.0 [-6.3, +25.1] (the
  gain is mostly Marcella's tribute gold), tributed @600 -0.6 [-12.0, +11.1]; 2.5 joins and 2.5 yields a game. Lost:
  under its 48.5% bar, with no dose-response between firing and losses.
- **One owner per small harmless group** (`demeter-harmless-one-owner`: no strength, no Monolith, health ≤ 480; a
  banking champion drops such a claim): against idle (`dmt-harmless-one-owner-solo`, 1164 games) gold @300 +19.4
  [+9.1, +30.0], @600 +57.4 [+37.6, +78.3], round to 1000 -1.1%; against demeter (`dmt-harmless-one-owner-ab`) 50.1%
  (47.2-53.0; ladder 42.9), gold @300 +9.1 [-11.8, +29.0], @600 +3.9 [-50.8, +54.9], deaths r1-600 +0.157 [+0.006,
  +0.316] a game. Co-claims r1-300 -74%; deaths after a switch to a group 12+ tiles away +0.143 [+0.039, +0.249]
  (ladder +0.371). Lost: a crew keeps bodies together, which a solo against idle cannot see.
- **Respawn wait cap** (`params::max_wait` 5 -> 2, `dmt-respawn-wait-cap-ab`): 51.6% (48.8-54.5), gold @300 +7.4
  [-12.3, +27.3], @600 -5.8 [-61.6, +48.7], tributed @600 +5.7 [-5.7, +16.5]. Idle beside respawning groups r1-300
  -39% (7.27 -> 4.42 rounds a body), spent on walking (band-diversion rounds +1.19 a body); camp damage +0.7%. Lost.
- **Siege kite call** (`demeter-siege-kite`): on a big shared group's first life, a Prism or Stellar kiting it calls
  2 teammates to a ring just outside the strikers' reach once the clear is due within their walk + 20 rounds. On 83
  shared-gems maps (`dmt-siege-kite-shared`, 166 games): 53.0% (45.4-60.5); the stampede family 25/34, life 0 to us
  in 29 of 32, tributed @600 +103.3 [+77.8, +127.7], gold @600 +94.8 [-135.7, +332.3]; far gen maps 26/60. Calling
  only for groups over 40 steps away (`-r2`, `dmt-siege-kite-r2-shared`): 53.0%, the same stampede games. Standard
  A/B (`dmt-siege-kite-ab`): 49.9% (47.0-52.8), gold @300 -0.1 [-20.1, +20.1], @600 +1.0 [-48.8, +52.3]. Held: wins
  on one self-play map family, no gold.
- Dropped before an A/B (`replays/wf4/PLAN.md`, `replays/wf5/hold-payout/design.md`): keeping a counting hold to the
  payout when no enemy can kill the holder first (5-11% of kept holders died within 12 rounds, against 2% of leavers;
  a melee veto removes the deaths and 73% of the gold; about +0.6 gold @300); stepping onto contested holds (about
  +2.5 gold); crew calls, partner sums, finish crews, lone big groups and a bag floor (below detection or a wrong
  premise); position comms (46.0% ±6.0 over 261 games, out-of-fuel turns +40-60%).

## demeter onto astraeus 8d97ef19, with a leave-one-out ablation (2026-10-30)

demeter (astraeus 1c0d6277 + the gold lean, c2) moved to astraeus 8d97ef19 (CHANGES 232-241) + c2:
`bots/variants/demeter-merged`, now `bots/demeter`. 1164 games each (ladder 140, gen 512 and gen-s1 512, seeds 6001
and 6002), own drafts; gold and gems by `tools/ab_farm.py`, CAND - REF per team-game (`replays/ab/dmm-*`,
`replays/dmm/`).
- Merged against old demeter (`demeter-gold-weight`): **62.0%** (59.2-64.8), gold @300 +76.4 [+54.9, +98.7], @600
  +214.6 [+158.9, +270.5], capture gold @300 +92.4, tributed @600 +40.0 [+27.1, +52.9]; out-of-fuel turns 3100 / 2634.
- Each piece removed from the merged bot (CAND) against it; a negative gold delta means the piece earns gold:

| Removed | Win % | Gold @300 | Gold @600 | Tributed @600 |
|---|---|---|---|---|
| macro-4 (CHANGES 235-240; ef8f0b8 + c2 + `max_wait` 3) | 41.2 (38.4-44.1) | -54.1 [-74.7, -32.8] | -138.4 | -36.4 |
| learned emblem table (232-233; `best_emblem` always the old chooser) | 46.8 (44.0-49.7) | +27.9 [+6.8, +48.9] | +48.2 | -5.4 |
| draft2 model (234; `draft/` from 1c0d627) | 47.3 (44.5-50.2) | +2.9 | -17.5 | -12.7 |
| `max_wait` 3 (241; back to 5) | 49.3 (46.4-52.2) | -8.4 | -6.9 | +3.9 |
| c2 (= astraeus 8d97ef1) | 51.0 (48.2-53.9) | -37.9 [-59.7, -16.0] | -104.6 [-157.0, -50.3] | -0.2 |
| `gold_price_scale` 1.5 (232; 1.0, c2 kept) | 51.5 (48.7-54.4) | -34.7 [-55.7, -13.6] | -94.1 [-146.7, -42.7] | +2.6 |

  Everything kept. c2 and the 1.5x gold price each earn about 35 gold @300 at a level win rate, and they stack. The
  learned emblems win games but cost about 28 gold @300.
- Allies read without the end-of-turn pre-recall (`ally_channel`: a recall not yet `kept_recall` is no channel) at
  `prospector_gold_holder`, the Marcella/Stellar holds, `ally_stops` and the plan's ally waker
  (`demeter-merged-chanfix`, `dmm-chanfix`): 50.0% in every suite; 7 of 582 side-swapped pairs diverged at all, no
  winner changed. Those checks almost never decide anything. Dropped.
- Pay-aware holder (see "Gold-first farm changes"; lost there at 48.0%) ported to the merged bot
  (`demeter-merged-pah`, `dmm-pah`): 50.7% (47.8-53.6), gold @300 +23.6 [+2.3, +44.2], @600 +57.6 [+4.5, +113.9],
  capture gold @300 -2.3, tributed @600 +2.4. Fresh suites `fresh-8101..8104` (seeds unused before, 2048 games,
  `dmm-pah-confirm`): **51.2%** (49.0-53.3), gold @300 +12.9 [-2.8, +27.1], @600 +79.3 [+40.2, +116.6], end +168.4
  [+41.4, +288.4], tributed @600 +0.1; out-of-fuel turns 5220 / 5462. Kept: in `bots/demeter`. Its gold is the
  holders' pay (Marcella's tribute gold, gold bonuses); capture gold is level.
- One owner per small harmless group (lost there on ladder deaths), ported (`demeter-merged-hoo`, `dmm-hoo`): 52.1%
  (49.3-55.0; ladder 52.1, gen 55.5, gen-s1 48.8), gold @300 -0.1 [-20.8, +20.1], @600 +38.9 [-18.2, +94.2],
  out-of-fuel turns 3364 / 3205.

## Map families (2026-10-30, mapgen 2316775d; all suites regenerated)

`maps/gen`, `gen-s1` and `fresh-6003` to `fresh-6040` (10,240 maps) were regenerated by the generator with the
topology, scenarios and quirks families, ladder-rate quirks in every preset and varied suite mixes (tools/README.md);
the older suites were deleted. Current astraeus (8d97ef19's bot, macro-4 + max_wait 3) on them plus the ladder,
own drafts, 20,620 games each, 0 failed matches:

| Against | Win % | 95% CI | Out-of-fuel turns (cand / ref) |
|---|---|---|---|
| hyperion | 82.3 | 81.8-82.8 | 91.1k / 47.8k |
| astraeus-ef8f0b8 | 59.2 | 58.5-59.8 | 94.7k / 90.5k |
| astraeus-3938c0f | 66.3 | 65.7-67.0 | 98.8k / 133.4k |

- **The macro gain holds on the new families.** By family the spread is under 3 points against ef8f0b8 (designed 58.2,
  topology 60.9) and 3938c0f (quirks 64.8, topology 67.6). Against hyperion the weakest families are quirks (79.3) and
  mutations (75.8).
- **Weakest presets** (at least 60 games):
  - fuel-stress (~100x100, ~240 stored camps): 34.8% against ef8f0b8, 48.9% against 3938c0f (92 games each);
  - cluster-carpets: 45.9% against ef8f0b8;
  - hole-maze: 48.3% against ef8f0b8;
  - monolith-only: 49.4% against ef8f0b8, 60.4% against hyperion;
  - mega-groups: 68.5% against hyperion.

## Map-fuzzer fixes (2026-10-30, astraeus b378e30; CHANGES 242-243)

The first `tools/fuzz` run (`replays/fuzz/first`, astraeus against `bots/idle`, hyperion as reference). Fixes judged
first on the run's 52 distinct worst maps against idle, both sides, then in the mirror. Own drafts, normal fuel.
- **Against idle, the 52 worst maps (CHANGES 242 + 243):** tributed gems 20,608 -> 33,345; 16 sides that never
  reached 1000 now do; out-of-fuel turns 1,359 -> 1,393. Solo (`tools/solo.py`, fresh-6031..6034, 2048 paired
  games): round to 1000 -0.5% (-0.9 to -0.1), games never reaching it 94 vs 99, out-of-fuel turns 9,466 vs 10,114.
- **Mirror against b378e30:** 50.8% of 5120 (49.4-52.1) on fresh-6031..6040, out-of-fuel turns 21,123 vs 20,938;
  50.0% of 2048 (47.8-52.1) on fresh-9001..9004 (generated for this), 9,429 vs 9,018. Level; kept as fixes.
- **Merged to main** with the exact fuel commits (b0224880, f4c52674, 97ec3a5f, a6e0b4bb): wide bench against the fixes
  alone 52/52 replays identical, total fuel -0.52%. a6e0b4bb against b378e30 on fresh-9501..9520 (unused before), own
  drafts: 50.8% of 10,240 (49.8-51.8), out-of-fuel turns 42,742 vs 42,776.
- **Diagnosed, not fixed** (each needs a policy choice):
  - Touching spawns (rushbait-v2 mutations, fuzz L00): idle enemies on the adjacent spawn keep our spawn and the
    tiles beside it in reach. Their reach alternates with round parity (team A starts odd rounds), so a hurt
    Prism steps toward spawn on one turn and out on the next (`retreat_step`: a zero-damage step away beats a
    damaging step home), and `continue_recall` cancels every recall (`recall_outruns`: an enemy is always within
    the channel's approach). It never heals; hyperion strands three champions the same way and scores with the
    fourth. Vesper Vale on spawn runs out of fuel every other turn in the strike search (four enemies always in
    sight). Options: price a step onto our spawn by one round of damage against health (the spawn heals at turn
    end), or let a recall stand when no enemy has moved for many rounds.
  - Dash and walk disagree (m-starvation-100582 side A, 513 gems against hyperion's 1002): Heart of Ruin's
    `dash_across` follows the approach field, which prices every hole line as dashable, and lands across a hole
    row; the walk after it (`step_towards` on the attack tiles, holes as walls) heads back round the row, and the
    next dash crosses again: an 8-round loop from round ~150 to 2000. Options: the walk descends the same approach
    field while the dash cools down, or the field prices one crossing per cooldown.
  - Altars sealed by a big group (the-pack mutations 09/10: one altar inside a ring of ~30 wolves; galaxy L07,
    L05): bags of ~1000 never tributed; hyperion scores 0 there too. Needs a siege plan for sealing groups that
    only spells (range 4 against the wolves' 3) can clear safely.

## Emblem lab round 3 and map-keyed emblems (2026-10-31, tools/emblab, PLAN-draft3.md; nothing shipped)

799,842 games from 4b6a932 (round 2's table built in, so the base is CHANGES 233) on the draft3 pool (ladder,
fall-custom, fresh-9100..9280), drafts 40% random / 30% top-10 ladder / 30% the shipped draft model's team, arms
drawn as round 2. 20.1M forced and 44.9M reached decisions; proposals recomputed to 0.02%.

- **Fit:** penalty search from round 2's penalties, one round of the two (`--rounds`): no group moved CV by more
  than 0.00003, so round 2's penalties stand. CV log loss baseline 0.54689, static 0.54649, state 0.54640, full (map
  terms) 0.54601: the emblem and map signal is as large as round 2's (0.00096 then, 0.00088 now). Held-out
  calibration 0.98-0.99; following the model's argmax loses 0.1-0.2 points per decision (winner's curse).
- **Static selection, doubly robust, against the base:** class 0 z 0 -0.46 +- 0.06, z 1 -0.21, z 2 -0.04 +- 0.03
  (moves 29%), z 3 0.00 +- 0.01 (2%); keyed by current family worse at every z. The same with a static outcome
  model. Round 2's z 2 had been +0.08: what it took is now the base, and nothing left beats it by more than noise.
- **Map-keyed (`dfit.mjs --mapdr`, mapdr.mjs):** 1,800 configs (granularity cell / type x ordinal bucket / type;
  no split, each of the 25 features at 7 quantile cuts, or k-means k 2-6; z 0-3), the config chosen inside the
  cross-fitting (per outer fold on the other four). Nested: all configs -0.063 +- 0.034 (moves 38%; a different
  config chosen in every fold), static configs only -0.023 +- 0.011. The best single config (type x bucket,
  gems_side split, z 2) was +0.081 +- 0.027 single-level, which is best of 1,800 and does not survive nesting.
- **Prospector on cluster maps** (hypothesis stated before the run): always taking a Prospector arm loses to the
  base in every `cluster_share` bin, but less on cluster-heavy maps (focus -1.02 +- 0.15 in the lowest eighth,
  -0.38 +- 0.15 in the highest; strength and health flatter). The direction holds; the size never beats the base.
- **Not run:** the A/Bs (no candidate). Round 2's table stays; draft3 trains under it.

## Draft lab draft3 (2026-10-31, astraeus f33d8e63; CHANGES 261)

476,881 self-play games (3/4/5 picks 158,400 / 158,378 / 160,103; 12 batches in 7 h, sharing the box with other
agents' A/Bs at 0.03-0.09 s a game, against draft2's 0.015) on the draft3 pool (ladder, fall-custom, fresh-9100..9280),
from scratch (no prior games: emblem round 3's games were left out, their forced emblems would skew champion values),
counters off from the start (`ctr` 1e9), all 25 features. The disk filled during batch 11 (other agents' A/B
replays, 89 GB that day): 288 games lost, the run stopped at its deadline before the last 8k-game batch.

- **Model:** cv log loss 0.6271 (without map terms 0.6480, without synergy 0.6280, intercepts 0.6509); penalties b 256,
  w 1280, syn 320 (the search moved only b, from 64). Without `sight_gap` and `narrow` (`draft3-cheap`, own search):
  0.6272, the same penalties.
- **Fuel** (`firstturn.py --sample`, 2,875 maps, 5,750 team-drafts): all 25 features ran fall-custom `giant`
  (256x256) out before the pick and a dash-lattice (fresh-9136) to 9.17M, over the 8.5M bar; analysis unfinished
  after round 0 on 7.6%. 23 features: 0 out of fuel; median 1.52M, p99 4.05M; giant 9.89M (since deleted: past the
  published 100x100), the worst legal map 6.70M; unfinished 5.3%.
- **Parity:** 0 differences (`native.mjs` all 66,987 pool and holdout maps with `--src` the candidate's draft dir;
  without `--src` it compares against bots/astraeus's header and reports every changed team; `parity.py` 200 maps).
- **A/B** against 3c492dbe, own drafts: 51.3% of 10,240 (fresh-9300..9319, 50.3-52.3), confirmed 52.0% of 10,240
  (fresh-9400..9419, 51.0-53.0). The feature A/B (all 25 against 23) was not run: the full header fails on fuel.
- **What `narrow` and `sight_gap` change** (all 25 against `draft3-cheap`, moved from TODO): CV 0.6271 against
  0.6272, ~0.0001 of the map terms' 0.021. Teams differ on 3,492 of 46,407 pool maps (7.5%; 3/4/5 picks 5.8 / 7.0 /
  9.2%), 93% by one champion, 8 of the 171 published maps; mostly mazes (labyrinth 32%, tunnels 27%, dash-lattice
  22%, topo-necks and -backdoor 19%, leaky-diagonals 18%, hole-maze 16%). At ~2 points a swapped map that is ~0.15
  points overall, below what an A/B sees unless the ladder gains maze maps. `narrow` favours dashers whose dash is
  movement (win points per +1 sd, 3/4/5 picks: Vesper +1.5/+1.1/+1.2, Ren +1.1/+0.8/+1.4, Vendetta +0.6/+0.3/+0.8)
  against Marcella -1.3/-0.8/-0.7, Cassi -1.0/-0.3/-0.7, Prism -0.9/-0.8/-0.5, Heart of Ruin -0.6/-0.1/-0.5;
  `sight_gap` is weaker (at most +-0.8: Ren, Vesper, Ryth up; Prism, Stellar down). The full model adds Vesper on 773
  maps and Ren on 269, dropping Marcella (437) and Cassi (396), and Ryth (329) for Prism (368); Vendetta nets -60.
  Self-play associations; `dash_gain` already covers dash shortcuts between the spawns, so `narrow` adds only the
  corridor part.

## Draft lab draft4 (2026-11-03, astraeus b65b0d87; CHANGES 297)

1,347,324 self-play games (3/4/5 picks 444,752 / 444,670 / 457,902) in 15 batches of up to 100k over 1.5 h on the
fast runner (native), sharing the box with another agent's A/Bs: 69 min playing (~19.6k games a minute), 17 min
waiting between batches (fixed since, b65b0d87), init 5 min, the final search 10 min. Pool fresh-77000..77195 (50,176
maps no lab or A/B had played) plus the ladder and fall-custom; opponent prior the top 10 other teams' ranked drafts
since 2026-10-31 (3/4/5 picks 3,740 / 4,720 / 12,908 team-games); our teams under the team lock (CHANGES 296);
sources explore, current (draft3-cheap's teams), Thompson and probe; counters off; all 25 features. 0 errors; draft
mismatches 16-39 a 100k batch.

- **Model:** cv log loss 0.6098 (without map terms 0.6322, without synergy 0.6114, intercepts 0.6370); the final search
  kept b 64, w 1280, syn 320. Not comparable with draft3's 0.6271 (other games and maps). `draft4-cheap` (a link lab
  on draft4's games, the 23 features of draft3-cheap) fitted at those penalties without its own search.
- **Teams:** against draft3-cheap the best team is the same on 55.7 / 48.1 / 44.6% of draft4's pool maps (3/4/5 picks).
- **Fuel** (`firstturn.py`, the 25-feature header): draft4's sample (2,879 maps, 5,758 team-drafts) 0 out of fuel,
  median 2.83M, max 7.26M; draft3's ten heaviest maps and fresh-9136: the dash-lattice 913607608 9.16M, over the 8.5M
  bar (it was 9.17M on draft3's). The 23-feature header measures what 261's does.
- **Parity:** `native.mjs --src` 0 differences on 854 maps (ladder, gen, fresh-9320, fresh-93000).
- **A/B** (own drafts, 20,480 games each on fresh-9320..9339 and fresh-93000..93019): draft4-cheap against b65b0d8
  51.6% (50.9-52.3); all 25 features against draft4-cheap 50.0% (49.3-50.7). The confirm on fresh-93020..93059 was
  stopped before any game finished (a user decision), so those suites are unplayed.

## Crew economics, quill (2026-10-31, astraeus from d0a8a94; notes in hyperion/macro/quill.md; CHANGES 256-258)

Against `variants/astraeus-base-d0a8a94-quill`, own drafts, unlimited fuel, 10,892 dev games (ladder, gen,
fresh-9600..9619) unless noted. Ladder study first: we already out-capture every top team by r600 (IF 506 vs 448);
on 00ambush the gap to IF was strong far groups taken as a six-body crew (157 gems by r200) against our solo chips
with long home trips (51).
- **Crew economics (quill-crew, 57.4%)**: job cycles include the home trips their camp damage forces; crew damage
  shared by water-filling over tank scores; proposals with an expected crew of available allies (whole team on
  round 1), bail-out after 4 rounds alone; `risky` fallback removed. Trip risk 0.6 (crew06): 58.6%; 0.8 / 1.0: 58.7
  / 57.9. Only ~3% faster unopposed (solo r1000 -3.2%): most of the gain is interaction (deaths 4.8 vs 5.3 a game).
- Monoliths on mixed maps as crew-only operations (quill-mono): 59.2%. kite()'s big group on shared-gems maps keeps
  the base's pricing (quill-sg; those maps were 33%): **59.4%; held out on fresh-9640..9659: 60.6% of 10,240
  (59.7-61.6)**, every suite 58.6-62.7%. Shipped as CHANGES 256-258.
- Level or lost: camp-fight formation (tank tiles, focus, side tiles, arrival wait) 47.9% alone, 54.4% on crew;
  one-step lookahead (solo neutral); worth·H/(H+T) − ρ·T with measured income rate 54.1%; mid-game availability
  by opportunity cost 58.4%; crew carrier consolidating captures 59.2%; side weight shrinking with crew size 59.1%.
- **Real budget, ported onto main (CHANGES 256-258)**, own drafts, fresh-9860..9899 (unused before), 20,480 games
  each, every suite above 50%: 61.4% (60.8-62.1) against f33d8e6 (= d0a8a94), 74.9% against 3938c0f, 87.4% against
  hyperion. Out-of-fuel turns 118.6k against f33d8e6's 84.7k: the crew planning and the dropped claimed-group bound
  (TODO). Unported quill on fresh-9840..9859: 58.4%, 73.4%, 86.3% of 10,240.

### quill's fuel (2026-10-31; CHANGES 260)

Two workers (fuel-campaign-2 NOTES "quill: run-out forensics", "quill: crew-value bound"). Forensics (stand_reach in
byte lanes, crew_tank debug-only, share_damage reading our record once), exact: against 259, 49.7% of 1164
(46.8-52.5), out-of-fuel turns 4843 vs 7113 (-32%). Kept.
Crew-value bounds (crew-valid farm-loop prunes, plan_crew only when it may beat the best), exact: against 260,
52.6% of 1164 (49.7-55.4), out-of-fuel turns 4782 vs 5774 (-17%). Kept (CHANGES 262).

## Middle band, smooth band and denial pricing (2026-10-31, astraeus 258-262; CHANGES 264)

Why the middle of the map pays more, three ways, own drafts, real budget, 20,478 games each on fresh-9900..9939
against 258 (the same games, so pairs are exact):

| Variant | Win % | 95% CI | Suites at 50%+ | Out-of-fuel turns (cand / ref) |
|---|---|---|---|---|
| Hard band x1.2 on [0.35, 0.6) (orbit's, `mid-on-main` e67a64bd) | 51.1 | 50.4-51.8 | 30/40 | 133,140 / 128,005 |
| Smooth edges, 0.05 either side (`smooth-mid` d1fbdd9) | 50.9 | 50.2-51.6 | 34/40 | 134,426 / 126,836 |
| Denial pricing, 1 + (1 - home_side) x scarcity (`denial-pricing` 1a87277) | 50.3 | 49.6-51.0 | 23/40 | 131,312 / 124,609 |

- Smooth against hard: -42 games (z = -0.51), level: the gain is the plateau, not the edges.
- Denial against hard: -168 games (z = -1.80). Scarcity = 1 - supply / demand per map (supply: non-Monolith groups'
  reward over respawn + capture time; demand: both teams' champions at `rounds_per_gem` 2.3): 0 on 00expanse and
  00gem-fields, 0.6 on 00galaxy and 00anvil. Its weight rises towards the enemy spawn and is 1 on camp-rich maps,
  the opposite shape to the band's, so the band's gain is likely not denial: perhaps `home_ground` discounts the
  middle too early.
- Smooth band on 262 + 261's drafts (fresh-9940..9979): 51.4% of 20,480 (50.7-52.1). Shipped (CHANGES 264).

## Farming macro, round 2: five branches (2026-10-31, astraeus d0a8a94; CHANGES 252)

Five independent orchestrators each refactored astraeus's farming macro in a worktree (combat micro, draft and shop
off-limits), judged at unlimited fuel (`--fuel 1000000000`) against frozen d0a8a94, own drafts, ~10k-game A/Bs on
their own dev suites and confirmed on held-out ones. Each agent's log is on its branch
(`research/hyperion/macro/<name>.md`); the branches are local.

| Agent (branch) | Best candidate | Dev | Held out |
|---|---|---|---|
| orbit (`worktree-agent-ac06503eddc99d45d`, 43e48835) | tank-aware clear pricing, siege fix, middle band x1.2 | 51.6% of 10,892 | 51.7% of 10,240 |
| harvest (`worktree-agent-ac8c9f185c34a6588`, e2b00fe4) | held fixes 1a/1b/2 (TODO), middle band x1.25 | 51.7% of 10,892 | 52.7% of 10,240 |
| ember (`worktree-agent-a91b5e8105bc0dc3c`, a88e9b37) | value-holder captures (funnel) | 52.8% of 10,892 | 52.8% of 10,240 |
| tide (`worktree-agent-a858d1a3462425136`, 984d837e) | ember's funnel + orbit's c1 + Willow medic + feint fixes | 54.5% of 10,892 | 53.9% of 10,240 |
| quill (`worktree-agent-a7197ae9101a36242`, e1f76f8d) | crew economics (trip-aware job costs, shared damage, operations, Monolith crews) | 59.4% of 10,892 | 60.6% of 10,240 |

- **Shared lesson (orbit, harvest, ember, tide):** every change that moved where or when champions farm lost or read
  level: squads and leashes (18-35%), deathballs (28-35%), packs (31-46%), raiding pairs (39-44%), escorts, one waiter
  per respawn (48.4%), earlier Monolith bursts (31-47%), gold weighted x2.5-4 (47-49%). Only free value won: who holds
  a capture (ember: gold earned +397 a game on gen, Marcella's share of tributed gems 29 -> 35%, deaths -0.8, kills
  +0.8; hold rounds unchanged).
- **quill's finding:** the ladder has no team that out-farms us (we capture more by r600 than every top-8 team); the gap
  is strong groups far from spawn chipped solo through long home trips, since farm's job rate never priced the trips a
  job's damage forces. Pricing them, and taking strong groups as crews, is what moved the mirror: deaths 5.3 -> 4.8.
  Camp-fight formation (tank tiles, focus fire) read 47.9% alone and 54.4% on crews: repositioning cost more than the
  health it saved.
- **Dropped from the merge:** the Willow medic (12 params; 50.4% alone, +0.9 on the funnel, within noise), the middle
  band (4 params; ~+0.5-1 alone; x1.5 lost), the held fixes (TODO).
- **quill shipped (CHANGES 256-258):** see "Crew economics, quill" above; 61.4% of 20,480 against d0a8a94's bot at the
  real budget.
- **Merged (CHANGES 252):** ember's funnel with its error-97 fix, orbit's siege cover fix, tide's feint fixes; 52.3% of
  20,108 against 251 at the real budget. `params::takeover_steps` was inert (the payout timer bounds the walk) and is
  gone.
- **Camp damage by the nearest-champion rule** (orbit's tank-aware pricing without the middle band, `merge/funnel`
  6b0fe83, on top of 252): 53.0% of 20,108 against 251 on the same games, paired against 252 +147 games (+0.73
  points; 3,246 flipped to wins, 3,099 to losses; McNemar z = 1.85); out-of-fuel turns 92,887 against 252's 64,181,
  worst bench turn ~500k. Head-to-head against 252 on fresh-9800..9839 (unused before): 50.3% of 20,478
  (49.6-51.0), level, out-of-fuel turns 86,095 against 63,284. Held (TODO).
- **On 258 (real budget, fresh-9900..9939, 20,478 games each, against 258):** middle band x1.2 (orbit's, branch
  `mid-on-main` e67a64bd) 51.1% (50.4-51.8), 30 of 40 suites at 50%+, out-of-fuel turns 133,140 against 128,005;
  not shipped (4 tuned params). Held fixes 1a/1b/2 50.1% (TODO item 4). Combat feint fixes 50.0% (CHANGES 259).

## Corridor yield (2026-10-31, astraeus 088243bd; CHANGES 253)

A whole-team deadlock in a one-tile spawn exit (gen-topo-shortcut-600106907, m3 57-1025) traced to make_way not
freeing an ally with allies queued behind it. make_way through a line of allies: 50.2% of 1164 (47.3-53.0) against
main, out-of-fuel turns level (2967 vs 2918), stalled champions 158 vs 173. Kept for the bug, not for a gain. Lost:
dashers trying the wide walking route before descending their field after a failed farm route (the deadlock game
53-1025: they stop taking hole crossings). Stall counts in mirror A/Bs are dominated by legitimate holds
(gen-shared-gems-600101605, every champion all game); remaining jams to look at: gen-topo-backdoor-600206713,
gen-topo-island-600106600, gen-topo-necks-600107008.
- Siege fire tiles on other groups' dead camp tiles (CHANGES 254; gen-topo-backdoor-600206713, a ranged sieger's only
  tiles in range were the last corridor group's, so it stood in the corridor mouth and blocked the melee): 50.2% of
  1164 (47.3-53.0) against cy-base, out-of-fuel turns 3013 vs 3015, stalled champions 154 (78.0k rounds) vs 157
  (78.6k). Kept for the bug; the game itself 0-114 -> 1101-114.
- Dashers sieging a seal only their dash walk reaches (CHANGES 255; gen-topo-island-600106600, gold clusters sealing
  the pocket past a hole line, both dashers holding winning bags all game): 50.4% of 1164 (47.6-53.3) against
  cy-base with 254, out-of-fuel turns 3023 vs 3000, stalled champions 147 (70.9k rounds) vs 152 (70.9k); 10 games
  differ from 254 alone, 3 losses to wins, none back. Kept.
- Seen, not fixed (gen-topo-necks-600107008, main = orch2-m5 against fb0, 161-953): Prism (west to farm) and Varg
  (east to bank) one tile apart in a 1-wide neck for 1700 rounds. Neither is beside the other, so make_way frees
  nobody, and a non-dasher has no field descent after a failed farm route (`!walked && dasher`). The corridor-yield
  bot does not reach that layout on this map (562-1034, no stall), but the gap case is still open.

## Ranged retreat steps and shots (2026-11-01, astraeus 268; was CHANGES 272, not shipped: dropped from the 2026-11-02 RC)

From v66's ladder replays (research/v66-replays): in the retreat branch our ranged champions stepped where enemies
still reached them and so fired 43% of turns against the top teams' 65%. Own drafts, real budget, against 268
(`bots/variants/astraeus-base`, 5880baa1). RS traces (debug_block in `retreat()`, read with replay outcomes) on fresh-30100:

| Variant | Games | Win % | 95% CI | Out-of-fuel (cand / ref) |
|---|---|---|---|---|
| v1: fire unless a step lowers the damage bound, the walk home survives or camps reach us | 2,048 (30100-03) | 47.0 | 44.9-49.2 | 7,876 / 7,574 |
| v2: fire only when no step leaves a standing blow (the dropped retreat change's rule) | 7,168 (30100-13) | 49.3 | 48.2-50.5 | 33,101 / 28,232 (first build, see below) |
| the retreat change as merged (quote kept per tile) | 10,240 (30114-33) | 49.5 | 48.5-50.5 | 37,296 / 37,151 |
| the same | 3,072 (30134-39) | 50.1 | 48.3-51.8 | 10,971 / 10,955 |
| standing blows ranked before the bound (ranged) | 10,240 (30114-33, paired) | 49.6 | 48.6-50.5 | 37,455 / 37,195 |

- v1's traces: in "no step lowers the bound" states the old step took 67 damage before our next turn, firing 88 (+84
  dealt); deaths within 6 rounds 28% vs 45%, ranged deaths per game 2.5 -> 3.8 on the ladder maps, Vesper's doubled.
  Worst-case reach overstates pursuit in self-play: a step that forces the pursuer to move often ends the exchange.
- Split by whether the step tile stays in an enemy's basic range from where it stands: out of it, stepping took 49
  against 78 firing; inside it, 135 against 117 (+93 dealt). Hence the standing-reach rule.
- v2's first build added the `standing` flag inside `Reach::at` and rebuilt the ranked steps at each decision point:
  ranged `retreat()` p50/p90 17.3k/40.1k fuel against 11.8k/20.8k, out-of-fuel turns +17%. A separate template
  instance for standing queries and one ranked quote per tile and spent actions: 13.4k/24.1k, level.
- Mechanism (2,042 games of the shipped A/B): ranged attack rate with an enemy within 3 55% vs 51%, ranged damage +4%,
  ranged deaths +5% (Prism +15%, Willow +6%). Level overall: the extra shots are paid back in deaths.
- Not tried: judging the sure-kill test without the victim's own blows (the kill removes them); a teleporting enemy's
  arrival blow as standing.

## Dash-aware travel in Pathing (2026-11-02, astraeus 23905ab6; branch `astraeus/dash-pathing`)

River's router on astraeus (`olympus/astraeus-river-merge`) claimed 53.4% of 1,164 games but 15,803 out-of-fuel turns
against 0. Rebuilt from the rules inside astraeus instead: `model/dash_turns.h` prices travel by the turn (open ground:
a dash is any two steps of a walk; a hole/altar line: walk to its launch, wait for the cooldown if need be, cross),
and `Pathing::travel`/`plan` choose walk, walk round, wait, dash, dash then walk or walk then dash by turns to the
goals. Dashers' live routes open StaticMap::crossable; the walking route is searched only when crossing would wait for
the dash, capped by the turns crossing takes. dash_across, both dash_towards and travel_dash are gone; travel dashes
also go in sieges, captures and walks home. Enemy within vision + 2: no travel dash (as before).
All own drafts, real budget, against frozen 23905ab6, fresh-31400..31419 unless noted:
| Variant | Win % | 95% CI | Games | OOF cand / ref |
|---|---|---|---|---|
| ties keep the dash (dash only when strictly sooner) | 49.8 | 48.8-50.7 | 10240 | 46113 / 38926 |
| ties take the dash | 52.9 | 52.0-53.9 | 10240 | 54363 / 40294 |
| ties take the dash, no crossings (open-ground dashes only) | 51.9 | 51.0-52.9 | 10240 | 42576 / 39109 |
| ties take the dash, cheaper crossing trace and plan (a2562092..HEAD) | 52.1 | 51.2-53.1 | 10240 | 49668 / 39131 |
| the same, fresh-31420..31439 (unused before) | **52.2** | 51.2-53.1 | 10240 | 48090 / 37535 |
- Holding the dash for the fight until it saves a turn loses ~3 points to dashing whenever it costs nothing: a dash
  cast now is back soonest. Crossings add ~1 point and most of the extra out-of-fuel turns.
- Out-of-fuel turns +28%; mean fuel per turn only +2% (48.5k vs 47.6k), so it is a tail. Per call: travel's crossing
  trace ~0.6-1.1k (once 1.2-2.3k: one trace per goal board, resumable, horizon by cooldown), a dash plan ~6.5k
  (blocked board 0.9k, window masks 2k, one label read per end 2.8k), a walking route round a crossing ~6k.
- Bugs the smoke games found: waiting never chosen with no step (fallback cascades); a stall when a tie held the dash
  at a launch with the walk spent; waiting forever when the crossing landing was vetoed (waits now only while cooling).
  A read-only audit found a revealed enemy after a bump still allowing a travel dash, the step guard worked out for
  nothing at launch tiles, and dash+walk ends past the guard's radius: fixed.
- Dropped deliberately: the old travel dash's rule against landing deeper in awake camps' reach (walking routes have no
  such rule; callers pass `avoid`). Untested on its own.
- The enemy clearance (no travel dash with a visible enemy within vision + 2), on 3f3fa6d3, fresh-31400..31419:
  none 50.3% (49.3-51.3, OOF 52100 / 38911); within 8 (strike reach + a dash) 52.5% (51.5-53.4, 51572 / 39570), level
  with 10; near an enemy only landings no nearer it 50.1% (49.1-51.1, 81271 / 38295: probably repeated planning when
  every landing is excluded, not chased). A dash spent near an enemy, even away from it, costs ~2 points: kept at 10.
- Fuel-only c00b84de (walk rounds proved failing without a search: foot() parts us from the goals, or the kept failed
  walk round's labels bound us past the cap; dash plan reads its window boards in place and shares blocked() with the
  route): 80/80 bench replays identical at 100M, mean -0.07% (topo, dash-lattice -0.3 to -2%). Real budget,
  fresh-31400..31419: 52.8% (51.8-53.7), OOF 50886 / 40348 (+26%, was +27%): the tail is not there.
- Open: the out-of-fuel tail (+26%) is still unattributed; the logic-level candidates (walk rounds, repeated planning,
  the dash plan, dash-only pockets) are done or proved small. Next: the fuel census (tools/fuel/census) on the OOF
  turns, against the reference.

## Batch 1: woken camps, dash-first threats, Heart of Ruin landings (2026-11-02, astraeus 8880ba3f; CHANGES 275)

Three branches against `bots/variants/astraeus-8880ba3`, own drafts, real budget, each on fresh-70001..70020 (10,240
games); the merge on fresh-70101..70120. Nothing won clearly, so only the rules fix with no cost shipped.
| Variant | Win % | 95% CI | OOF cand / ref |
|---|---|---|---|
| `b1/woken-camps`: our hits' wakes recorded (`World::note_hit`) and read by Safety, Varg's splash wakes priced (`wake_cost`), one shield test | 50.1 | 49.1-51.0 | 57,042 / 54,552 (+4.6%) |
| `b1/dash-threats` 1+2: dash-first two-turn threats, dash-path rules, per-enemy pack radius | 50.0 | 49.0-50.9 | 57,675 / 55,278 (+4%) |
| item 1 (dash-first threats and dash-path rules) | 50.4 | 49.4-51.3 | 55,710 / 54,819 (+1.6%) |
| item 2 (pack radius `threat_strike(...).reach + 1`) | 49.4 | 48.5-50.4 | 56,841 / 55,434 (+2.5%) |
| `b1/hor-landings` c62bf5c9: HoR landings near sleeping camps priced (`WokenFire`), not banned | 50.1 | 49.1-51.0 | 61,041 / 55,032 (+11%) |
| 87243ef4: landing classes only by groups a landing can wake | 49.9 | 49.0-50.9 | 58,804 / 55,100 (+6.7%) |
| **merge: dash-path rules only (CHANGES 275)** | **49.8** | 48.8-50.7 | 52,148 / 51,529 (+1.2%) |
- Dropped as level with more out-of-fuel turns: woken-camps (its record alone is untested; the extra fuel is
  unprofiled, likely members re-found after each wake and `sdk_has_camp` in `note_hit`), dash-first threats (more
  caution against dashers; `offer_heal` would keep the old two-turn model), hor-landings (extra landing classes crowd
  the strike search's 24 nodes; it also took a woken hit on an ally as free, assuming the ally steps out first).
- If woken-camps and hor-landings are retried, they must share one camp-fire price (both derive from plan.cc's
  `wake()`), and agree on allies: woken-camps charges a hit on an ally, hor-landings did not.
- Untried alone: the woken-camps record; Varg's shared shield test (DIRECTIONS self_abilities 1; a retreat step
  after the hold can also leave the shield's reach); `reset_and_attack_camp`'s missing Monolith check and picking the
  member whose 3x3 holds the most killable members (camps 1); a landing beside Ren then an attack in
  `landing_suicidal`, `attack_target` and `step_to_kill` (self_abilities 2; the branch summed both retaliations in
  `dash_to_attack`). Still open: a landing leaving a capture we hold (abilities 1).

## Batch 3: melee clearing, prey choice, healthy deaths (2026-11-02, astraeus 702704b6; CHANGES 276-278)

Three branches against `bots/variants/astraeus-702704b`, own drafts, real budget, each on fresh-70301..70320 (10,240
games); the merge on fresh-71301..71320. All level; only rule-consistent fixes with no assumed numbers shipped.
| Variant | Win % | 95% CI | OOF cand / ref |
|---|---|---|---|
| `b3/melee-clearing` a6d079ed: spell clears by true spell reach (ground 5) for every champion, siege at that reach | 50.0 | 49.0-50.9 | 53,793 / 53,536 |
| `b3/prey-choice` 9530f89d: prey self-delay by our strike, side_damage with unacted allies, Cassi/Issac kill worth the partner's health | 49.9 | 48.9-50.9 | 54,038 / 54,312 |
| + race home in place of the own-ground chase filter | 48.3 | 47.3-49.2 | 55,940 / 54,912 |
| + race home only removing targets, filter kept | 49.7 | 48.8-50.7 | 54,804 / 53,821 |
| `b3/healthy-deaths` 8b0d030b: retreat steps by `safety.bound`, a stunning step costs twice its blows | 50.1 | 49.1-51.1 | 54,598 / 54,539 |
| `b3/fled-guard` f206aab8: work guard keeps a fled stand by enemy identity and distance (~23 turns a game) | 49.4 | 48.5-50.4 | +5% |
| **merge: CHANGES 276-278** | **49.9** | 48.9-50.9 | 57,292 / 57,127 (+0.3%) |
- Melee clearing, solo against idle (ladder, both sides): rounds to 1000 -0.8% [-2.3, +0.6], gems collected by 600
  -11 [-24, +1], gold by 600 -40 [-99, +11]. Dropped: it lets melee champions kite whenever farm's price says so, a
  trade-off resting on that price. Ryth's "camp damage collapse" (TODO) was an artifact of comparing against all
  champions: against Marcella (same base stats, melee) Ryth is level or ahead on 4 of the 6 maps and trails on oasis
  and gold-rush, where Marcella's 2x Focus spell adds damage and Ryth dies more. Against idle Ryth deals 24.9 camp
  damage a round to Marcella's 29.8 with the same turn split (61% walk, 18% hit, 12% idle); low stretches are fights.
- Prey choice, merged with fixes: the partner's health in `kill_bag` was dropped (it raises the chip value of every
  hit on that body, not only the kill); the self-delay keeps baseline when we cannot walk (the branch fell back to
  basic range, ignoring casts) and counts a ready heal or shield as allies' test does; `side_damage` no longer counts
  an ally's ready spell in both its turns. Kills, deaths and gems a game for the branch: 4.06/4.42/836 against
  3.98/4.49/833.
- Chases (2,048 games): ~41 chase episodes a game a team, 11.5% end in a kill, 2.4% in the chaser's death; out-of-reach
  chases rarely close, close starts convert 20-37%. The race home discriminates best but as a filter it costs farm time
  (race 1) or as many kills as the time it saves (race 2). Chase against farm is break-even at the margin.
- Healthy deaths (183 traced baseline mirror games on fresh-70201, 2,274 kills): by the decision the turn before the
  first hit, farming 50%, already retreating 25%, low health 14%. Retreat deaths: median health 100% at the first hit,
  median 22 steps from home, the attacker first seen a median 8 rounds before, 5-6 steps outside its reach, between
  victim and spawn 0.23 a death. The gap (distance - reach) per victim turn over 560 retreat deaths: homeward steps
  hold it (+0.01 a turn), flips back to farming lose it (-0.67 a turn, -717 total), turns lost to stuns (every 8
  rounds, mostly HoR and Vendetta) -495, each enemy dash -0.8 to -1.2. A same-speed pursuer with a dash or stun every
  8 rounds always catches a champion >20 steps from home. Flips are not deadlier once conditioned (death within 15
  rounds 5.7-10% after a flip, 15-25% continuing to retreat: selection); the trigger enemy's last step barely predicts
  contact (13.7% vs 8.5%). In 36% of farming deaths our side had more health within 8 tiles. Only 0.34% of retreat
  steps changed with the stun pricing; its doubling is an assumed bound, so only "a stun reach is not clear, and
  ranks after a stun-free step at equal damage" shipped (276). The fled-guard v1 (exact positions) fired 2.2 turns
  a game, a no-op.
- Left from the closed TODO and DIRECTIONS items: the fled-guard was the stand memo for 269's work guard missing
  stands lost only to pursuers (~19% of step-then-retreat turns); pricing only the tile the step takes (a lazy veto in
  `try_move`) is untried. Healthy deaths, untried: a yield only from a pack walking toward us (or the stand sim with
  arriving allies); fewer long walks home past dash or stun pursuers (farm placement); fight entry when our side
  outweighs theirs. CHANGES 201's shared-gem kiting is still unverified on a second fresh shared-gem set (the first
  gave 59.2% of 120). A Cassi/Issac kill could add the partner's health to the kill alone, if at all. Against idle,
  Ryth and Prism cast walk-excluding spells at enemies on their own spawn (~1% of turns, a wasted walk; batch 4: from
  `stun_worth`, left).

## Batch 2: spawn heal, camp deaths, pathing yield (2026-11-02, astraeus 8880ba3f; CHANGES 279-281)

Three branches against `bots/variants/astraeus-8880ba3`, own drafts, real budget, each on fresh-70201..70220 (10,240
games); the merge onto main 103c9bac (after batches 1 and 3) against `astraeus-103c9ba` on fresh-71201..71220.
| Variant | Win % | 95% CI | OOF cand / ref |
|---|---|---|---|
| `b2/spawn-heal` aa8285fe: HomeWalk first in retreat_step, recall stands when no walk home survives, lethal on spawn | 50.2 | 49.2-51.2 | 54,203 / 53,995 |
| `b2/camp-deaths` ccd453c2: `camp_trapped` prices the walk out as uncovered | 46.5 | 45.5-47.4 | +5% |
| `b2/camp-deaths` 1faabb52: cover lapses only if one turn's move can't bring the tank nearer than us | 49.1 | 48.1-50.1 | +8% |
| `b2/camp-deaths` 78b2a75f: sealed crystal pockets in farm pricing | 50.1 | 49.1-51.1 | 53,838 / 53,911 |
| `b2/pathing-yield` gap1: gap deadlock fix on 274's pathing, "no way" memo across turns | 49.8 | 48.8-50.8 | +5.3% |
| `b2/pathing-yield` gap3: gap1 bounded, its no-line answers kept | 50.1 | 49.2-51.1 | +6.4% |
| `b2/pathing-yield` nogap1: make_way walls channelling and holding allies | 49.8 | - | +9.4% |
| `b2/pathing-yield` 2078d6d2: range-0 approach exit only | 50.0 | 49.1-51.0 | 54,060 / 54,033 |
| **merge: CHANGES 279-281** | **50.2** | 49.3-51.2 | 55,939 / 55,441 (+0.9%) |
- Spawn heal: the held 1a+1b cherry-picked as they were lost against idle on L00 (gems by 600 -45, deaths 77 against
  55): 1a ranked the home step first even at full health, so Issac stepped on and off touching spawns all game. The
  shipped form ranks it first only if the spawn leaves us healthier than now, and replaces `max_walk` 4 by
  `recall_turns() + 1`. Solo against idle: 60 L00 maps 1000 gems 5.2% sooner [2.6, 8.1], gems by 600 +32.5 [+11, +53],
  gold +233, never reaching 1000 27 against 33, OOF 787 against 624; 598 ladder and fresh maps level (-0.1%
  [-0.2, +0.1]), OOF 6,636 against 7,063. The merge marks every surviving homeward step (the branch took the first in
  compass order) so 276's damage-then-stun-free order decides among them; a8ebfa3f's early exit at full health is
  exact (a bound is never negative). Fix 2 (dash cooldown) stays out (CHANGES 274).
- Camp deaths (3,072 games of b1-wc2, fresh-70001..06): ~0.49 a game a side, ~10% of ~4.95 deaths; Golem 37%, Elk
  32%, Monolith 24%, Wolf 7%. The group was woken by an ally 43%, the victim 41%, an enemy 16%. 46% came after an ally
  had tanked the group and walked off, or two equally near melee champions' turn-order tie flipped each round
  (gen-open-field 631fe513); 11.5% had no walk out at the first hit (mostly self-woken after a crystal hop:
  mut-ambush-field c2941925, Marcella in a walled Golem pocket, a recall each hit cancels); 63% still had an
  affordable walk out. "Recalling" at death means nothing (the turn-end recall feint: 85%). TODO's "off-foot islands
  hold 12% of deaths" counted champion kills only (`offfoot.py` drops camp kills). TODO Bugs "retreat_step into an
  Elk's reach" is not real: retreat_step, flee_camps and avoid include awake and maybe-awake members and
  continue_recall drops on camp damage; 1% of camp deaths came walking homeward into an awake group. Cover pricing
  in `camp_trapped` cut camp deaths (-0.061, -0.010 a game) but lost (the covered crew left early, gems -2.2%): the
  tank's tenure belongs in the clear plan / `share_damage`. The sealed pocket change: camp deaths -0.020 (noise).
- Pathing yield: on gen-dash-lattice-966507608 the whole team stands still all game in both bots (a pre-existing
  mirror standoff), champion 0's turns at 98-99k fuel in the baseline; the gap fix's memo miss ~8.5k, hit ~1.6k.
  Walling allies that won't move jammed whole teams (mut-fan-7020901848, both gen-topo-backdoor maps: 5 champions
  still 1,200+ rounds at an altar); waiting instead still jammed. Latent bug: `route_reached_` is overwritten by
  every search. The belief showed a Marcella tributing for 1,300 rounds with 0 gems. The gap fix found no oscillation
  on gen-gem-drought-600105818 or the necks map. Walls for allies that won't move: a channel or hold frees its tile
  within a few turns, while a wall makes callers re-plan every turn and suppresses the back-off; "parked" has no
  definition anywhere.
- After 279: `HomeWalk`'s damage bound covers only next turn's enemy moves for every step (a pursuer closing during
  the walk is not counted), and the doubled bound is pessimistic. It costs ~1k fuel a tile, so a few L00 maps run out
  more (L00-c1-10 side A out-of-fuel turns 52 against 10); side A of the L00 family stays poor (fuel-cut loops).

## Batch 4: farm exposure, fight fuel, chase value (2026-11-02, astraeus 702704b6; nothing shipped)

Three branches against `bots/variants/astraeus-702704b`, own drafts, real budget, each on fresh-70401..70420 (10,238
games). None won, so nothing merged and no merge A/B; docs only, on ad74b7b4.
| Variant | Win % | 95% CI | OOF cand / ref |
|---|---|---|---|
| `b4/farm-exposure` daa6589c: `home_race` walk-race weight replaces `home_ground` and the middle band | 49.6 | 48.6-50.6 | 53,057 / 53,673 |
| `b4/fight-fuel` 1c5bb7c4 (guard1): step guard without fuel gates (2-sim limit, unsimulated tiles guarded iff `safety.lethal`) + fled-tile memory | 50.3 | 49.3-51.3 | 114,080 / 57,022 (2x) |
| `b4/fight-fuel` c1c75224 (fled1): fled-tile memory alone, gates kept | 50.2 | 49.2-51.2 | 55,434 / 55,033 |
| `b4/fight-fuel` 38124211: strike search with no query cap, on guard1 (vs frozen guard1) | 49.8 | 48.9-50.8 | 116,870 / 118,015 |
| `b4/chase-value` v1: chase pay per round against farm's raw `job_rate` | 49.9 | 48.9-50.9 | 58,204 / 55,638 (+4.6%) |
| `b4/chase-value` 1acc69a0 (v2): displaced rate scaled to realized income | 49.0 | 48.0-50.0 | 61,890 / 54,677 (+13%) |
- Farm exposure, the hazard (3,072 mirror games): champion deaths per 1000 champion-rounds by where the victim stood
  8 rounds before. The walk home does not predict deaths (at share 0.5-0.6, risk falls 2.4 -> 0.8 from 10-20 to 60+
  steps home); the step margin D = d_enemy - d_ally does, nearly independent of map size: D <= -10 ~5, -5 ~3.2,
  0 ~1.9, +5 ~1.0, +10 ~0.6, +20 ~0.25, >= +30 ~0.05 (a factor e per 8-10 steps, about a sight radius). ~95% of
  champion-rounds face >= 4 dash/stun abilities, so the roster's effect can't be read. The candidate weighed
  (1 - P_c)(1 + P_e) with P_e = sigmoid(-D/8), P_c = sigmoid(-(D/8 + 1)) (peak 1.127 at D ~ +5) and deleted five
  tuned constants, but its sigmoid, scale and form are unmeasured choices, and by spawn walk it lost on small (<30:
  48.7%) and very large maps (80+: 48.3%, unreachable 47.7%), won 30-50 (51.7%; each ~+-2): on large maps it crushes
  deep enemy-side groups (0.30 -> 0.05 at D < -24) where the data levels off (~2.7x the front's risk). Gems +3.4
  +- 8.9, champion deaths -0.12 +- 0.14. Dropped: level and a trade-off by map size.
- Fight fuel (baseline): OOF ~5.3 a game a bot, mostly farm; the strike search ran out on ~8% of first OOF turns,
  `strike_after` ~4% (~0.6 fight OOF turns a game). The step guard gives up for fuel ~38 times a game a bot (33,476
  entry, 5,039 look, 454 sim shortcuts in 1,024 games). A-B-A position cycles are 2.55% of champion turns, 8.6% of
  them next to a step-guard shortcut (~4.5x the chance, ~7 extra cycles a game). Ungated (164k placings at 100M):
  94% need no fight sim (~120 fuel); a sim costs 12-20k (one 12k, two 34k, three 46k on average); a 2-new-sim limit
  binds on 0.62%; the entry gate fired before the cheap first pass. In strike searches whose pricing costs >= 20k,
  the step guard worked out inside the price loop took 32.4k of 43.6k on average, reach queries 3.2k; uncapped, a
  search asks <= 41 queries (27k; p99 10.4k). So the cost behind fight turns is the step guard's fight sims, not
  the query cap. guard1 cut cycles 2.79% -> 2.63% (streak-4+ turns -14%) for 2x OOF; fled1 2.74% -> 2.59% (-11%),
  the cheapest loop fix found, but it assumes want_home's verdict holds while the enemies seen stand still and we
  are no healthier (ignores cooldowns, arriving allies, turn order): dropped under the level rule.
  `tools/fuel/census/instrument.py` no longer matches astraeus (3 patterns in bot.cc, fight.cc; run with
  `--lenient`).
- Chase value: a chase's pay per round (kill gold + 2x target bag + held group's gems + 60 rounds of income, over
  the turns to catch, or capped by its walk home when uncatchable) against the displaced farm job's rate. Farm's
  `best_value` is nominal (~1.1 gems a round) against ~0.29 realized income a turn (~4x), so v1 declined 40% of
  chases (chase turns 62 vs 104): kills 4.15 vs 4.53, deaths 5.08 vs 4.67, kill share at equal numbers
  0.50 -> 0.474: fewer chases cede fights. v2 (chase turns 87 vs 104) lost more. Spawn casts (~0.1 a game) all come
  from the strike search's `stun_worth`; a stun on spawn does take a turn, so left.
- Untried: a farm weight read off the measured hazard (no sigmoid); a 10-20k-game sweep of the middle band's height
  and bounds; denial only on the enemy's half, or weighted by the enemy's score; the strike search's step guard priced
  once per tile outside its price loop. Both loop fixes wait on cheaper fight sims.

## Batch 5: channel beliefs, shop, Monolith wakes, camp tanks, claim churn (2026-11-02, astraeus 103c9bac; CHANGES 282-287)

Five branches against `bots/variants/astraeus-103c9ba` (camp-tank against `astraeus-702704b`), own drafts, real
budget, each on fresh-70601..70620 (10,240 games); the merge onto main 3fa17f96 against `astraeus-ad74b7b` on
fresh-71501..71520. All level; only the rule-exact parts shipped.
| Variant | Win % | 95% CI | OOF cand / ref |
|---|---|---|---|
| `b5/channel-beliefs` 310fb1d1: our stun ends the channel, tributes that win together (unseen counted), several landed tributes, respawn window | 49.9 | 48.9-50.8 | 54,616 / 53,903 (+1.3%) |
| `b5/shop` b5shop-1: Focus-scaled heals and shields in `main_stat`/`upkeep_cost` (shop 2) + Ryth's Power Health + count_use | 49.0 | 48.0-50.0 | 54,881 / 52,705 (+4%) |
| b5shop-2: same, shields credited only when drained (06dfe65d) | 49.4 | 48.5-50.4 | 53,935 / 54,043 |
| b5shop-3 9410be0b: Power Health + count_use only | 50.2 | 49.2-51.2 | 54,285 / 54,442 |
| `b5/monolith` cea77213: a sleeping Monolith priced in `Search::wake`, not banned (plan 2) | 50.0 | 49.0-51.0 | 54,336 / 54,380 |
| `b5/monolith` 0955d7cf alone: a camp stun on a sleeping monster worth nothing | 50.2 | 49.2-51.1 | 54,884 / 54,573 |
| `b5/monolith` both (b5-monolith-both) | 50.1 | 49.2-51.1 | 54,865 / 54,629 |
| `b5/camp-tank-dropped` c6c361e5 (b5-seq1): camp tie order by spare hits | 49.9 | 48.9-50.9 | +8% |
| `b5/camp-tank-dropped` bacdfcc3 (b5-seq2): + a champion trapped next turn ranks with those leaving | 50.0 | 49.0-50.9 | +14% |
| `b5/claim-churn` first_to_work (b5cc-ab1): a co-claimed group belongs to the claimer that starts work first | 50.0 | 49.0-50.9 | 63,860 / 53,981 (+18%) |
| **merge: CHANGES 282-287** | **50.2** | 49.2-51.1 | 56,472 / 57,262 (-1.4%) |
- Channel beliefs (debug_block in `World::update` against replay truth, 32 self-play games, ~2.3M samples): a visible
  champion's channel is a fresh engine flag, except within our own turn after our stun (282). Unseen enemy tributes
  are right 82% of the time, wrong runs 0-20 rounds, bounded by the channel's end round (closes DIRECTIONS abilities 5:
  no gate needed). An enemy recall seen starting that ends out of sight is assumed complete: false 5,523 against
  true 447 in self-play (the turn-end recall feint), left as is (on the ladder recalls are mostly real; DIRECTIONS
  bot 6, abilities 4). Batch 2's Marcella tributing 1,300 rounds with 0 gems did not reproduce in 32 games:
  likely batch 2's modified build. Merged with a fix: 283 counts only visible other tributes (the branch counted
  believed unseen ones, an assumption 18% wrong); it fired in 2 of 32 games.
- Shop: crediting every shield cast in full moved Heart of Ruin to Focus (S/F/H shards 5/53/42 -> 6/75/19; HoR games
  45.7%) and Varg toward Focus (82/5/14 -> 59/32/10; 43.6%). Shields credited only when drained (health lost after a
  turn ended shielded) put Varg back on Strength and HoR level but 70% Focus via landings; Willow on Focus looked worse
  (47.3%, n=490; heals credited in full even when they overheal). Focus pays only when the shield or heal is
  saturated: a retry needs Willow's overheal measured and only landing HoR dashes counted (travel dashes count now).
  Greed (shop 1) not attempted: it needs a timing-aware comparison (bonus only at 750; a begun Greed blocks
  `home_trip` and `wants_shop` until saved).
- Monolith (baseline self-play, 214 Monolith maps): per team a game ~0.88 Monolith captures (~200 gems), ~2.2 wakes,
  ~1.4 of them ending asleep with health left. Of 534 asleep endings the waking team dealt 4.9k and took 3.4k on
  average; 149 include one of ours killed by the group; 107 dealt < 500. Partial clears are mostly not wasted (~0.1
  groups a game our damage then enemy capture; ~1.2k of ~20k damage a game never captured). The priced wake: captures
  0.866/0.868, gems 200.2/200.1, wakes 2.29/2.17, wake-and-leave 1.59/1.44 a game: dropped (a trade-off, captures
  unchanged). The stun change fixed a Cassi stunning a sleeping Monolith every 46 rounds (gen-monolith-only-7060201500,
  600 taken each time, no damage done) but delays a stun that opens a siege by a turn (the attack that wakes the
  group comes after the cast): dropped as a trade-off. Found: ~1/3 of `MONO ENGAGE` lines are one member waking a
  Monolith with no crew staged, since `mono_engage` counts the engager toward `mono_gather_share` (0.6), so the
  stronger of two passes alone; and with reach 5 the nearest melee body takes 200 a phase for ~5 phases walking out:
  1,100-1,200 health can't tank a Monolith (needs `share_damage` / `camp_trapped` modelling).
- Camp tanks: per-round tie prediction is nearly exact (`find_members` uses round + 1, parity, alternation, next
  priority via `World::slot`); only our own rank is inexact (`set_turn_order` sets priority after the turn's
  decisions). The flip comes from our own order: `idle_priority` puts the champion with most hits in hand first, so
  two tied champions trade hits and run low together (631fe513: Vendetta and HoR beside a Golem swap every round or
  two). The real failure is mutual cover: each prices its walk out as covered by the other, both leave, hits keep
  landing on one. b5-seq1: camp deaths 0.508 against 0.467 a game (Golem/Monolith tank-left up), gems 945.9 against
  939.9. b5-seq2: camp deaths 0.511/0.473, gems 951.7/938.7, tributed 832.8/822.9, all deaths 4.78/4.95. Dropped:
  level, more out-of-fuel turns. Lesson: rank is set after the decisions it should price, so moving who takes a tie
  moves hits onto champions whose turn priced them safe: price rank and decisions together; exit fields under a
  tie hit need a cache or bound.
- Claim churn (512 traced mirror games, mapgen seed 76991): turns between two working turns claiming a group other
  than the one finally worked are 33% of alive time, 19.7-19.9% net of steps that still closed on the next work;
  retreats 5.0% and bank trips 2.4% of that. Re-pricing flips are the largest claim cause, ~7.4% net (2.3% flips to
  an ally's group as crew, ~2.6% the group captured while walking to it); ally co-claims ~3.2% (a sooner ally joining
  later ~0.7%, ally out of sight 40% of it; joining as crew then leaving ~1.3%); enemy holding 0.5%, deaths 0.6%.
  first_to_work cut its target 0.80% -> 0.48% but arriving first then re-pricing grew as much (net 19.84% against
  19.68%), and cost a centre field per claimed group a turn: dropped. Arrival arbitration is now level twice
  (macro-3 m3-v-arb and this).

## Batch 6: farm flips, fight and guard fuel, Monolith engage, travel time (2026-11-02, astraeus 3fa17f96; CHANGES 288)

Batch 6's branches against `bots/variants/astraeus-ad74b7b` on fresh-70701..70720 (travel-time against the
farm-flips bot `astraeus-9bba28d`), b5/sim-fuel against `astraeus-103c9ba` on fresh-70601..70620; own drafts, real
budget, 10,240 games each. The merge (farm-flips + the two fuel-only branches) onto main cd600d73 against
`astraeus-cd600d7` on fresh-71601..71620.
| Variant | Win % | 95% CI | OOF cand / ref |
|---|---|---|---|
| `b6/farm-flips` 9bba28dc: farm's `max_wait` test by travel turns (CHANGES 288) | **52.1** | 51.1-53.0 | 58,272 / 57,793 (+0.8%) |
| `b5/sim-fuel` 80bdad00: fuel-only, fight sims -2.6% | 50.1 | 49.1-51.1 | 54,776 / 54,521 |
| `b6/guard-fuel` f6bdc6b2: fuel-only, step guard's non-sim work | 50.3 | 49.3-51.3 | 58,053 / 58,205 |
| `b6/mono-engage` f30692cf: `mono_crew_ready` phase sim replaces `mono_gather_share` | 50.2 | 49.2-51.1 | 57,048 / 57,528 |
| `b6/travel-time` f2b586de: every walk-vs-rounds race in turns (vs farm-flips) | 49.8 | 48.8-50.8 | 63,814 / 57,675 (+10.6%) |
| **merge: 288 + sim-fuel + guard-fuel** | **52.9** | 51.9-53.8 | 56,857 / 53,460 (+6.4%) |
- Merge: 5,412 of 10,240 wins, 16 of 20 suites above 50%. Out-of-fuel turns +6.4% against farm-flips' +0.8% alone
  (the fuel-only parts only lower fuel at 100M); not chased, as A/B out-of-fuel counts swing by thousands on
  shared-gem maps: check with `tools/fuel/oof_bot.py` before more farm work.
- Farm flips (512 traced mirror games, 81,420 flips before any work on the previous group): mostly new information
  (group captured while walking 15.7% of invested rounds, another branch ran in between 15.2%, ally claim changed
  9.5%, other state ~16%, help calls 6.3%); fuel minor (a pick the fuel-cut loop never reached: 2.6% of flips). The
  largest mechanical cause: `max_wait` measured in walk steps, so a dash raised the measured wait by 2 and dropped
  the group being neared (10.1% of flips, 5.1% of invested time). With 288: unworked flips -11.6%, dash-driven wait
  flips 8,262 -> ~1,300, churn net 19.82% -> 19.44%. Against idle (fresh-70701..04): tributed @600 +5.1 [+2.0, +8.4],
  gold +28 [+13, +44], round to 1000 -0.5%. Left: groups entering as their wait falls under `max_wait` (~9% of
  invested time; the cutoff's own boundary; a longer `max_wait` lost before); FarmRecall's recall-out wait still in
  steps; the farm trip price still `max(steps, respawn)`; `travel_turns` follows the dash's enemy clearance (an
  enemy coming within it switches the measure back to walking).
- Fight sim profile (fight set, 30 games at 100M): a sim averages 4.5k (p90 9.1k, p99 15.6k): `act` 61% (~400 a
  call), early-end checks 13%, `play_quiet` 8% (39% of calls moved nothing). Sims are ~3.2% of fight-set fuel;
  `new_fight` ~6.0k a call. A step-guard placing past its entry gate: 1 sim 9.8k (5.5k of it sims), 2: 27.4k (13.8k),
  3: 37.6k, 4+: 63.3k; ~half of each placing's growth per sim is non-sim work. No memo gain (74 repeats in 63k
  hashed sims). Sim-only changes can't reach Fuel 2's -0.3% total bar (sim-fuel: -0.09% fight set). Dropped there:
  v128 fighter copies, cached `walk_allies_in` reach, inlined quiet act, primed quiet state / F4 event skip (+0.5 to
  +1.8%).
- Guard fuel: exact `Reach` looks are the largest non-sim cost left (~6.6k in a 2-sim placing; `Reach::at` ~4.7k,
  a miss ~620 fuel, nothing obviously wasteful; all misses ~0.66% of fight-set fuel). `step_guard_cover` is the largest
  non-sim pool (~17.6k calls x ~1.4k, mostly the `GuardFoes` constructor); sharing it with `step_guard` needs a Safety
  epoch in the cache key (`refresh()` after our attacks doesn't bump `world.observations`).
- Monolith engage: wakes 2.41/2.42, wake-and-leave 1.61/1.62, captures 0.932/0.926, deaths to Monoliths
  0.677/0.674 a team a game: the engage gate does not drive wake-and-leave or Monolith deaths. Lone wakes come from
  other paths (attacks in passing, help, siege on Monolith-only maps); `MONO ENGAGE` lines mark `siege_group` being
  set, not a wake. The lever: a lone 1,000-1,200 health body can't tank a reach-5, 200-damage Monolith, unmodelled in
  farm choice and crew pricing (`share_damage`, `min_camp_damage`). Dropped: level.
- Travel time: FarmRecall, HomeTrip, `contest_capture` and siege's kite tests in turns (prices left in steps):
  level, OOF +10.6% (+3.8% without fresh-70703), cause not found. Dropped. Converting farm's trip price to turns
  means changing every pruning bound: a separate project.

## Batch 7: trip price in turns, the batch 6 merge's out-of-fuel rise (2026-11-02, astraeus a1563030; nothing shipped)

| Variant | Win % | 95% CI | OOF cand / ref |
|---|---|---|---|
| `b7/trip-turns` 8a10eee4: farm's trip arrival in travel turns (vs the farm-flips bot `astraeus-9bba28d`, fresh-70801..70820) | 50.4 | 49.4-51.3 | 62,397 / 56,119 (+11.2%) |
- Trip turns: farm_turn's `arrive` = `turns(steps)` on plain walks, wait = max(0, respawn - arrive) (and the
  `max_wait` test), trip = arrive + wait, the recall race and bank's `recall_to_farm` in turns; pruning bounds kept
  valid via `turns(near)` (`PreUpper::cool`, exact for s 0..399, c 0..8). OOF +11.2% (fresh-70803 alone 5,653 vs
  2,861; without it +6.5%). Untraced lesson: for a dasher `turns(near)` ~ 0.8 x near, which lowers every pre-facts
  bound, so fewer groups are pruned before their facts, fields and clear estimates are read; b6/travel-time showed
  the same (+10.6%). A retry must make that extra work cheap or bounded first. Dropped: level. Claim churn,
  untested: a commitment cost in farm's comparison; an ETA in the per-ally claim field.
- Batch 6 merge's OOF +6.4% (56,857 vs 53,460) is not a real cost: three stalled games give ~74% of it
  (gen-tunnels-7160704309 side 12, fresh-71607 #453, +1,456; gen-topo-split-7160506505 side 12, fresh-71605 #447,
  +657; gen-labyrinth-7160303800 side 21, fresh-71603 #266, +386). There, from round 300 to 2000, CAND's champions
  sit in the bank branch ~900-1,400 turns each and run out almost every turn (bank-branch streak-starting OOF 1,825
  CAND vs 640 REF). Chaotic: ~170 fuel of meters a turn turned #453 into a 1026-102 win. The rest +1.7% (+898 +- 509,
  within ~2 SE), matching farm-flips' +0.8%. `travel_turns` ~200-270 fuel a call for dashers, ~40-80 (max ~1.4k) a
  turn, ~37 a call otherwise: not a fuel regression. `tools/fuel/census/batch_oof.py` now skips `D SLOT` lines.
- `b8/bank-stall` 280b400c (vs `astraeus-3bfe479`, fresh-70901..70920): 50.0% (49.1-51.0) of 10,240, OOF 60,146 /
  60,924 (-1.3%). Diagnosis of the stalled games: a standoff at a choke, not new in batch 6 (with another build the same
  stall moved to REF). tunnels-7160704309: every altar and farm target lies beyond a one-tile column at x=28 that both
  teams' five champions block from round ~300. topo-split-7160506505: carriers wait 1,000+ rounds for the enemy-held
  x=64-66 corridor to altar (65,78) while altar (27,78) is open. `bank_gems` always walks to the nearest altar, the step
  guard refuses the step every turn, and nothing redirects the carrier; a stuck turn spends ~70k in `carry_bag` (chase
  20-36k; `step_safely`'s failed guarded search ~23k plus the wide retry 7-19k, or the chained farm loop ~60k), plus
  `continue_recall` ~15k and world update ~9k, so every turn runs out. Fix tried: a carrier held short of its altar for
  the walk to the next altar avoids it (`note_held`, reusing `carry_bag`'s watched-altar `avoid_altar`). topo-split OOF
  941 -> 275 but a new flip at the corridor mouth: `may_chain` judges only the current tile, so one step north out of
  enemy reach chains a farm and walks back (the fuzzer's bank/chain carry flip); tunnels unchanged (no other altar);
  labyrinth OOF up. Dropped: level, and it doesn't end the stalls. Open: `may_chain` judging where the chained walk goes; failed route
  searches and chase evaluations recomputed every turn of a standoff.
- `b8/chain-dest` 8fac98b8 (vs `astraeus-3bfe479`, fresh-71701..71720): `may_chain` judges enemy reach along the
  chained job's whole walk, not just the current tile. topo-split-7160506505 corridor-mouth loops 3,877 / 1,960 ->
  17 / 5 (sides A / B), but OOF there roughly tripled. 50.5% (49.6-51.5) of 10,240, OOF 82,237 / 55,729 (+47.6%, every
  suite). `b8/chain-dest-cheap` 01430750 (no dilated board: per-tile tests on enemies within reach of the route, same
  decisions) on the same suites: 50.3% (49.3-51.3), OOF 84,814 / 55,501 (+53%), so the test is not the cost; likely
  carriers that now bank land in the stalled bank branch (above). Both dropped. Next: make that branch's stuck turns
  cheap first, then retry. Untried (TODO's carry flip): once `may_chain` refuses with a bag, keep `memory.banking` until the
  bag is tributed or lost, or no credible enemy has been in reach for a while (the release rule is a policy choice: ask
  the user).

## Session merge: what shipped from batches 1-7 (2026-11-02, astraeus, squashed onto 8880ba3f)

Every run: astraeus against `astraeus-8880ba3` (the bot before batch 1), own drafts, fresh-72001..72020 (unused before),
10,240 games. The last two pair game by game with the first's maps.

| Variant | Win % | 95% CI | OOF cand / ref |
|---|---|---|---|
| CHANGES 275-288 as merged by batches 1-7 | 51.6 | 50.6-52.5 | 52,158 / 50,420 (+3.4%) |
| ... without 279's recall keep | 51.4 | 50.5-52.4 | 52,310 / 50,466 (+3.7%) |
| ... also without 280 and 283, and 275 narrowed (shipped) | 52.0 | 51.1-53.0 | 52,693 / 50,273 (+4.8%) |

- 279's recall keep (`walk_home_fails`, from `held/spawn-heal-dash-cooldown` 1b) dropped: when no walk home survived, an
  unthreatened recall stood even if `recall_outruns` said an enemy would reach us before it completed, so it mostly
  wasted channel turns before the enemy cancelled it, and it took home as the only escape (allies, a pursuer giving
  up). Back to the old rule: keep only a recall that outruns every recently seen enemy. 51.4% against 51.6%, within
  noise (the first run's per-game results were deleted, so not paired). Its share of 279's L00 gain against idle was
  not measured separately.
- 280 (sealed crystal pockets: a walker's clear priced with 0 trips, worth 0 alone if it costs our health) dropped: it
  trusted `min_camp_damage`'s solo estimate, ignored heals, and crew pricing stayed unaware of the pocket. 50.1% alone
  in batch 2, rarely fires.
- 283 (a visible tributer flagged when the other visible tributes need its bag to win) dropped: no timing check (a bag
  landing much later still flagged it), 2 games in 32. 49.9% bundled in batch 5.
- 275 narrowed: an ally bars an enemy dash path only if its next turn comes after the enemy's last chance to dash (the
  enemy's turn, or its second with two turns before ours); one that acts first may step aside. The first version took
  every visible ally as a wall, which understates threats when they move. Landing on an ally's tile is unchanged.
- The three together against the recall-only run, paired: 5,329 wins against 5,267 (+62, +0.6 points); 1,640 games
  changed (851 to wins, 789 to losses), z 1.5. Kept: level to slightly better, and each removes an assumption.
- The gap between batch 6's 52.9% (against the batch 5 bot) and 51.6% here was within noise of the merges' level
  reads (batches 1 and 3 read 49.8% and 49.9%); not resolved.

## Combat round: retreats, chases, opening hits, draft wards (2026-11-02, astraeus f9074463; CHANGES 289)

From the v66 ladder replays against the top 4 (research/v66-replays). Every A/B is 10,240 games against the frozen
`bots/variants/astraeus-f907446`, own drafts, real budget, fastrunner; "v66" is the same bot against
`baselines/v66` paired game by game with the base's run (`base-f907-vs-v66-81001-81120`: 56.5% of 61,440). The v65
pairing (base 80.6%) is too lopsided to show anything. Fresh suites from seed 81001 (unused before).

| Variant | Suites | Win % | 95% CI | OOF cand / ref | v66 paired |
|---|---|---|---|---|---|
| chase v1: prey's own-ground filter waived for an enemy engaged last turn | 81021-40 | 48.8 | 47.8-49.7 | 53,312 / 53,353 | (v65 +0.01) |
| chase v2: an engaged enemy that left sight stays prey while its tiles stay within sight | 81021-40 | 51.9 | 50.9-52.8 | 54,161 / 52,913 | +0.76 (-0.19..+1.71) |
| chase v3: v2 + the search's walk aims at the engaged enemy | 81021-40 | 52.4 | 51.5-53.4 | 55,104 / 53,125 | +2.18 (+1.12..+3.23) |
| chase v4: v3 + aim at an unseen one too, radius-9 bound | 81021-40 | 52.5 | 51.6-53.5 | 55,009 / 53,029 | +1.94 (v3 -0.23) |
| chase v3, held out | 81081-100 | 52.4 | 51.4-53.3 | 63,919 / 62,970 | +2.27 (+1.21..+3.32) |
| **chase v3 + engaged-cast fix (CHANGES 289)**, held out | 81081-100 | **52.2** | 51.2-53.1 | 64,298 / 63,510 | **+2.13** (+1.07..+3.19) |
| t5-zone dbaced70: search end tiles out of the pack zone and raised recall line; keep_out at the guard radius | 81041-60 | 50.2 | 49.2-51.1 | 61,281 / 54,463 | (v65 -0.10) |
| t5-stand 919c8d94: an opening champion hit (moved, no enemy reached the start tile, kills nothing) refused where want_home's stand sends us back | 81041-60 | 50.1 | 49.1-51.1 | 63,522 / 55,074 | +0.82 (-0.09..+1.73) |
| t5-pair: zone + stand | 81041-60 | 50.3 | 49.4-51.3 | 69,354 / 55,361 | +0.52 |
| t5-stand-hit: stand + end-tile danger at the measured 0.38 hit chance | 81041-60 | 49.6 | 48.6-50.6 | 63,554 / 54,453 | +0.37 |
| draft ward2 5e3777ca: a second planned ward tile per site for a second ally | 81101-20 | 50.0 | 49.0-50.9 | 59,308 / 58,164 | +1.12 (+0.03..+2.22) |
| ward2 + approach-weighted ward score | 81101-20 | 49.8 | 48.8-50.7 | - | +0.78 (ward2 -0.34) |

- Ladder measurements (scripts in the session scratchpad, not kept): our pursued retreats die 29% against ~13%;
  retreat-branch retreats start on stand_lost (49%, median health .90), outmatched (29%, .92), stand_falls (7%),
  low (8%). A haven (healthy ally nearer than home, reachable first, joint HPxStr ahead) exists in 22-31% of our
  retreats and 31-40% of theirs, and the direction taken changes deaths on neither side: haven-seeking retreats
  are not worth building. Short homeward retreats drag the attacker onto our half as theirs do, but we kill it 8%
  of the time (they 22%). The README's 21-39% pursuer deaths count proximity, not chases: chase-branch pursuers die
  5%. Committed pursuers kill 31% (they 53%); step geometry is the same (direct 0.63 / 0.66, cut-offs 0.07 / 0.06):
  interception is not worth building. 43% of allies in not-lost fight sims deal nothing within 5 rounds (farm 39%,
  bank 16%); removing them flips 24% of not-lost verdicts but those flips precede a death only 7% of the time.
- Chase stops (ladder 541 games / self-play 40): target out of sight 25% / 25%, own-ground filter 21% / 19%,
  retreat 19% / 10%, chase fight lost 15% / 14%, the search's walk spent 8% / 13%. Belief chases: 4.6 a game, 1-4
  turns, the target seen again within 3 rounds 71%. Stuns on us while chasing rose (117 -> 147 stops).
- Leave decision (`want_home`, fight.cc; branch `worktree-agent-a5ba063e3f853e90d`, fresh-81001..81020):

  | Variant | Win % | 95% CI | OOF cand / ref | v66 paired |
  |---|---|---|---|---|
  | V1 9fe46acf: want_home's stand plays us first when our blow this turn reaches an enemy of the fight (our first turn hits only enemies we reach) | 50.0 | 49.1-51.0 | 56.7k / 54.6k | (v65 +0.30) |
  | V2 5cdcaebe: V1 + in contact (a visible enemy strikes us now) the stand, not the pack zone, decides | 50.2 | 49.3-51.2 | 56.7k / 54.2k | +0.23 (-0.73..+1.20) |
  | V3 5bc9eefe: V2 + retreat race against observed followers: stay if the walk home falls, buys no turn and standing deals more | 46.6 | 45.7-47.6 | 108.9k / 54.9k | -3.24 |
  | V3d 098230ba: V3, fuel fixed, a stay fights in place (no farm/bank/chase after the search) | 47.9 | 46.9-48.9 | 65.6k / 54.2k | -1.78 |
  | V3e 3bbf100c: V3d + a follower pursued over both of our last two turns | 48.3 | 47.3-49.2 | 62.7k / 54.5k | -1.44 |
  | V4 c0c08f77: V2 + rosters without Willow and allies low (<0.35), recalling or mending | 49.9 | 48.9-50.9 | 55.8k / 53.9k | +0.19 |

  V1/V2 flip ~8.5 leave verdicts a game to stay (mostly 1v1, 2v2, 2v3), ~1.4 the other way, but deaths and kills
  barely move (V2 vs v65: deaths 3.46 vs 3.51, kills 3.93 vs 3.86). The pack-zone override no longer doubles deaths
  (eris did): 273's fall-first rule now guards the stand. The race's stays die as the lost stand predicts, but
  real walks the race calls doomed survive far more often (pursuers quit, terrain, allies arrive): the homeward
  drag is worth more than the model credits. Melee walk and attack are independent, so a melee retreater trades
  the same blows as one that stands; only ranged retreaters lose a shot, ~0.5 stay episodes a game. want_home
  returning false hands the turn to farm or bank, not a fight: any "stay" needs a fight-in-place branch (V3d).
  Race fuel: ~16 distance-field reads a step (median 20k a call); crow-flies walks and one strike build cut it to
  ~9k, still +15-21% OOF.
- Opening gate on 289 (branch `worktree-agent-a0fdb8d0c2f593d62`): ca78811f is 919c8d94 on 57131355; 94656606 adds
  the re-pick: a refused end tile is guarded and the next-ranked plan taken (pruned tiles reopen from their bound),
  at most 3 stand checks a turn, `end_veto` up to 4 tiles a round. The gate fires on ~2.4% of searches; the re-pick
  then takes a stay without a hit 81%, a hit from a tile whose stand holds 6%, a walk 3%, the check cap 9%.

  | Variant | Suites | Win % | 95% CI | OOF cand / ref | v66 paired |
  |---|---|---|---|---|---|
  | gate a3cf9039 (on 0c45902e), against chase v3 | 81061-80 | 51.1 | 50.1-52.0 | 66,368 / 59,759 | +0.31 over chase v3 |
  | gate + re-pick 030f223b, against chase v3 | 81061-80 | 50.9 | 49.9-51.9 | 76,139 / 61,279 | +0.62 over chase v3 |
  | gate ca78811f, against 289 | 81061-80 | 50.8 | 49.8-51.8 | 65,893 / 59,846 | +0.23 over 289 |
  | **gate + re-pick 94656606, against 289 (30,720 games)** | 81141-200 | **50.2** | 49.6-50.7 | 225,282 / 178,846 | **+0.53** (+0.00..+1.05, z 1.97) |
  | leave V1+V2 on 289 (e78ed3d9) | 81121-40 | 49.8 | 48.8-50.7 | 61,514 / 58,581 | +0.47 (-0.47..+1.40) |

  On fresh-81061/81062 against v66: deaths a game 4.79 (289) / 4.71 (gate) / 4.49 (gate + re-pick), kills 5.60 /
  5.59 / 5.69, kill share at equal numbers .563 / .572 / .591. Fewer deaths, kills held, but within half a point of
  win rate, and +26% OOF from stand sims on 2-3 adjacent refused tiles a turn. Not kept for now: cut the repeated
  stands' fuel first (one stand result a tile a turn; replays byte-identical) and retest. 289 against v66 on
  81141-81200: 58.4% of 30,720. Zone and the 0.38 price made the search more passive.
- Draft memory: 747-984 bytes free on the bench maps (82 on gen-dense-camps-120105502) cannot hold per-tile data;
  the combat gaps are decisions, not static data. Left: wall-aware clear stands (farm pricing), and fuel-only
  round-1 cuts (group centres for `static_camps` ~10-15k on 100-group maps; dashers' crossable tiles 6-16k).

## Chases and leaves on the ladder (2026-11-02, astraeus 57131355; CHANGES 290)

Chase episodes in v66's 412 ladder games against the top 4 (scripts and definitions in
`research/v66-replays/scripts/chase/`): a pursuer that hit its target in the last 3 rounds, within 3, while the
target steps homeward, followed until a kill, the target's spawn, the pursuer's death, lost contact or the target
turning. ~10k episodes a side.

- Lethality: their chases end in a kill 27%, ours 11% (targets under 35%: 53% / 33%). A healthy pursuer (>= 60%) on
  a hurt target (< 50%) kills 49% / 27% and drops it 28% / 42%. Not the own-half filter alone: on the pursuer's own
  half, targets at 35-50% die 36% / 17% and at 50-75% 21% / 7%.
- Execution is level: melee pursuers hit at the same rate from each distance (adjacent 0.75 / 0.73, two off 0.42 /
  0.38); dashes and stuns a round are level. They spend more rounds in contact (adjacent rounds 11.9k / 9.0k) and
  bring more helpers (0.60 / 0.39 allies hitting the target an episode). Ranged pursuers in reach (1-3) fire 48-59% of
  rounds against our 32-40% and walk 26-39% against ~50%: v66 README finding 2 again, from the chasing side.
- Trading while fleeing: fleeing, they deal 0.95 of what the pursuer deals; we 0.69 (ranged fleers 0.96 / 0.44).
- Our pursuer's decisions (v66 traces, healthy pursuer, target < 75%): in dropped chases 29% of turns are retreats
  (stand_lost 1533, outmatched 704, low 308) and ~50% farm or bank turns.
- Leaving vs staying, as observed: a healthy pursuer that left a hurter target on the stand or the pack zone died
  within 20 rounds 23% (the target 8%); one that stayed 8% (the target 40%), at every head count within 8. **This is
  confounded**: the stand counts health, strength and arrivals the head count misses, and overriding it lost (below).
- Turn order: a pursuer acting after its target in the round kills ~3x as often within each target-health band, both
  sides; doubles are level (0.19-0.21 a round boundary). Alternating turns make the order within a round irrelevant
  to a chase's geometry, and the danger priority puts endangered champions first, so this is selection: not built.

A/Bs, 10,240 games each against `bots/variants/astraeus-5713135`, own drafts, fastrunner; v66 paired against
`base-5713135-vs-v66` on the same games (base 58.7% on 82001-20, 57.6% on 82021-40). `pressed`: a visible enemy we
struck or chased last turn, off its spawn's edge, with a smaller health share than ours.

| Variant | Suites | Win % | 95% CI | OOF cand / ref | v66 paired |
|---|---|---|---|---|---|
| press1: want_home skips the stand and the pack zone while pressing (unless lethal); prey takes the pressed enemy | 82001-20 | 45.6 | 44.7-46.6 | 56,324 / 64,435 | -3.15 (-4.26..-2.05) |
| pA: only the stand skipped | 82001-20 | 47.9 | 46.9-48.8 | 56,941 / 60,856 | - |
| press2: press1 + the pressed enemy followed past the own-half filter | 82001-20 | 44.2 | 43.2-45.1 | 57,480 / 63,100 | - |
| **pB: only prey's part (CHANGES 290)** | 82001-20 | **50.6** | 49.7-51.6 | 60,374 / 61,060 | **+0.99** (+0.00..+1.97) |
| pB, held out | 82021-40 | 50.4 | 49.4-51.3 | 56,416 / 56,859 | **+1.39** (+0.41..+2.36) |

- The stand verdict and the pack zone are right to pull a healthy champion out of a fight it presses (-2 points
  each), even against v66; the own-half filter too (press2 -1.4 on press1, as chase v1). The fewer out-of-fuel turns
  are the skipped stand sims and earlier deaths. Don't retry "stay while healthier" without a new mechanism.
- Left: their pursuit's edge is persistence and helpers, not steps. Followed up below.

Why pB (CHANGES 290) works, from a debug copy that logs the chase play-out on every pressed-chase turn (`debug_block`,
no fuel), 1,024 games on fresh-82001/82002, joined to the replays. The shortcut fires ~84 times a game, target a
median 5 tiles off; the play-out reads lost on 20% of them. It is right that these chases go worse (target dead
within 20 rounds 12% against 30% when not lost; our chaser 6.9% against 3.6%), but the base, which drops the chase
for farm in the same situations (logged in a base-behaving copy), gets the same 12% and 6.9%: walking off is no
safer. The play-out asks whether we win at the target's tile (2.1 enemies there against 1.2 in want_home's stand at
ours; every lost verdict has our fall first; we are a turn late in 88%; removing the delay or the late joiners alone
flips 11% / 16%), not whether chasing beats the alternative. The base picks the same target 84% of the time, drops
the chase 13%, switches target 3%; a lost turn is followed by a not-lost one only 11% of the time (no flicker).
Kills 5.01 / 4.67 and deaths 5.98 / 6.33 a game against the base (control copy 4.58 / 4.62, 5.91 / 5.84).

Leads, against `bots/variants/astraeus-290` (290 against v66: 59.7% on 82001-20, 59.0% on 82021-40):

| Variant | Suites | Win % | 95% CI | OOF cand / ref | v66 paired |
|---|---|---|---|---|---|
| **L1a: a teammate's pressed fight (`team_pressed`) taken as ours, and aimed at (CHANGES 291)** | 82001-20 | **50.0** | 49.0-51.0 | 61,567 / 61,226 | +0.51 (-0.27..+1.29) |
| L1a, held out | 82021-40 | 50.0 | 49.0-50.9 | 57,049 / 58,118 | +0.64 (-0.13..+1.42) |
| L1b: only the strike search's aim at it | 82001-20 | 49.9 | 48.9-50.8 | 61,528 / 60,857 | -0.50 (-1.06..+0.07) |
| rs: "Ranged retreat steps and shots" (v2, was 272) ported onto 290 (`bots/variants/astraeus-rs`) | 82001-20 | 49.8 | 48.9-50.8 | 61,886 / 60,768 | -0.15 (-0.76..+0.47) |
| rs, held out | 82021-40 | 49.8 | 48.9-50.8 | 56,215 / 56,337 | -0.16 (-0.78..+0.46) |

- Helpers (lead 1): each nearby ally joins about as often as theirs on the ladder (0.28-0.31 against 0.31-0.40 per
  ally within 8); they have 3+ allies near 27% of chases, we 14%, and alone their pursuer still kills 41% against our
  22% (healthy pursuer, hurt target). L1a is level and changes 46% of games.
- Ranged firing (lead 2): our ranged champions with an enemy within 3 fire 43% of turns; 74% of walk-without-fire
  turns are retreat turns (fire 11% there, 71% on farm and strike turns, chase turns 2% of these). The ported change
  is level a third time, now also against v66: dropped. The rest of the ranged gap is when to leave, not how.

## Positions at first contact (2026-11-02, v66 ladder replays; nothing built)

Is the chase and retreat gap positional? First contacts (an enemy within 8 after 5+ rounds with none; ~20k ours,
~26k theirs) in v66's ladder games against the top 4, scripts in `research/v66-replays/scripts/chase/`
(`contact_pos.py`, `cp_sum.py`, `joiners.py`). Death within 20 rounds: us 9.2%, them 5.1%.

- Escape geometry is not it. At contact both sides have the same distributions of steps home, cut-off margin (the
  enemy's steps to our spawn minus ours; cut off 13% / 15%), open tiles within 2, homeward branches, path detour,
  half and bushes; none of them predicts death much (cut off by 3+: 10.3% / 6.0%, not cut off: 10.3% / 5.4%), and
  in every bin we die about twice as often. astraeus weighs no escape route when choosing where to go (farm prices
  a group's static side; the guards price fights with the enemies seen now), but this says such a term would not
  close the gap.
- Support distance is. In contacts that become fights (a hit within 10 rounds): allies within 8 at contact 1.58 /
  2.12, within 12 2.05 / 2.59; second-nearest ally a median 9 / 6 tiles. Enemy joiners in the next 5 rounds 1.12 /
  0.83, from 9-12 tiles, about 55% in the team's sight at contact on both sides. Five rounds in we are outnumbered
  29% / 11% and ahead by 2+ 19% / 39%. Numbers then predict death on both sides (down 2+: 31% / 26%; up 2+: 11% /
  6%); our fight deaths reweighted to their numbers fall from 18.4% to ~15.0%: ~40% of the gap to their 10.5%.
- The rest is in the fight. We strike first more (23% / 16% of contacts) and die after it twice as often (13.4% /
  6.9%). Our deaths climb with enemy joiners (none 13.3%, 2+ 24.7%), theirs barely (9.8%, 11.8%). When the first
  joiner arrives both sides are near full health (in contact 3%), head home within 2 rounds 7-8%, and take the same
  damage over the next 5 rounds (0.12 of max health), yet over 15 rounds we die 16.7% / 9.5% and kill 0.28 / 0.51
  enemies: the fights diverge later (v66 README: 26% of our damage lands on champions that die, 49% of theirs).
- Leads: support distance in farm choice (cohesion bonuses lost in self-play before; the ladder now prices it at
  ~40% of the fight-death gap, so judge any retry against v66 too); engagements that count who can arrive on both
  sides (the opening gate with re-pick, "Combat round", is the nearest built piece: +0.53 against v66, +26% OOF).

## Cohesion, four parallel attempts (2026-11-02, astraeus 291; CHANGES 292)

Four independent agents, each on its own copy of 291 and its own 20 fresh suites (83001-83080), aimed at the support
gap in "Positions at first contact". 291 against v66: 59.4 / 59.1 / 59.8 / 59.4% on 83001-20 / 83021-40 / 83041-60 /
83061-80.

Movement tie-breaks (agent C, dev 83041-60, held out 83001-20):

| Variant | Win % | 95% CI | OOF cand / ref | v66 paired |
|---|---|---|---|---|
| p1: pull tie-breaks (radius 20, claims half weight) + retreat tie | 51.6 | 50.7-52.6 | 68,291 / 57,795 | +0.75 (-0.53..+2.03) |
| p2: p1, octagonal distance, near 3, dash-landing ties | 51.3 | 50.4-52.3 | 85,625 / 59,215 | |
| **p4: p1, radius 30, claims as visible allies (CHANGES 292)** | **51.9** | 51.0-52.9 | 69,620 / 59,231 | +0.85 (-0.44..+2.13) |
| **p4 held out** | **51.3** | 50.4-52.3 | 73,085 / 62,628 | +0.73 (-0.57..+2.03) |
| p5: p1 + melee steps within attack range toward the team while clearing | 50.6 | 49.6-51.6 | 68,560 / 58,484 | |
| p6: p4 + farm near-tie lean (up to +3% for groups within 12 of allies) | 51.1 | 50.2-52.1 | 73,907 / 59,161 | |
| p7: p4 + strike planner end tiles lean toward the team | 51.0 | 50.0-52.0 | 71,494 / 59,571 | |

- p4 against v66 (1,024 games): allies within 8 at contact 1.56 -> 1.67, second-nearest ally 9 -> 8, death within 20
  rounds of contact 11.1 -> 10.5%, deaths a game 5.44 -> 5.08, v66's 6.99 -> 7.25, gems 870 / 881.
- Anything that moved a choice that was not an exact tie (p5-p7) read like the old cohesion bonuses: lower.
- Out-of-fuel turns rise ~17-24% (solo too). The pull costs ~1% of a turn; farm and carry turns near allies cost
  more. Making those cheaper is the follow-up.

Engagements that count posted fights (agent B, dev 83021-40, held out 83041-60): each champion posts the enemy it
is fighting in its priority payload (bit 11 flag, bits 12-14 enemy index; not while retreating or mending);
`Safety::Wide` counts posting teammates within 8 (not 4) in `fighting_allies`.

| Variant | Win % | 95% CI | OOF cand / ref | v66 paired |
|---|---|---|---|---|
| c1: posts + a lost want_home stand re-run with posting mates + wide prey sims + joined chases off own ground | 50.2 | 49.2-51.2 | 66,079 / 62,947 | |
| c2: c1 + join any teammate's contact | 49.8 | 48.8-50.7 | 68,755 / 63,727 | |
| c3: c1 without the off-own-ground bypass | 50.4 | 49.5-51.4 | 63,854 / 59,066 | +1.21 (+0.25..+2.17) |
| c4: c3 + retreat toward posting mates + pack zone counts them within 8 | 49.9 | 48.9-50.8 | 66,302 / 61,574 | |
| c5: c3 + focus (a posted enemy within a striker's range +1 worth 0.33 life_value more) | 50.7 | 49.8-51.7 | 63,527 / 58,472 | |
| c6: c5 + opening gate (ca78811f) passing when posting mates make the stand hold | 51.3 | 50.4-52.3 | 74,616 / 59,510 | +0.58 (-0.45..+1.61) |
| c6 held out | 51.8 | 50.8-52.7 | 69,745 / 57,153 | +0.01 (-1.01..+1.02) |

- c6 against 291 (2,048 games): deaths 6.43 / 6.92, kills 6.35 / 5.91, damage on champions that die 29.7 / 27.1%,
  gems 825 / 812; spacing unchanged (allies within 8 at contact 1.66 / 1.65): better fights, not cohesion.
- Self-play: fights with no ally within 8 die 15.1%, with three 8.5%; 81% of deaths are ganks from fog (the victim had
  seen every attacker 16-23% of the time); cohesion before round 300 barely predicts the mirror's winner (50-53%);
  focus fire was already 76% same-target within 4. Joining at range (c2) and retreating toward fights (c4) lose, as
  before.

Support in farm choice (agent A, dev 83001-20, held out 83041-60): a group's weight becomes exposure x
supported, supported = 1 + risk x (0.15 support - 0.15 (1 - support)); risk 1 within 20 walking steps of the enemy
spawn, 0 at 40; support the summed nearness (full within 6, none past 12, capped at 1) of each ally's claim centre,
else recent position.

| Variant | Win % | 95% CI | OOF cand / ref | v66 paired |
|---|---|---|---|---|
| s1: penalty 0.2 on unsupported risky groups, risk by home_side share | 49.6 | 48.7-50.6 | 65,263 / 57,554 | |
| s2: penalty 0.4 | 47.7 | 46.7-48.7 | 63,215 / 58,187 | |
| s3: bonus 0.15 + penalty 0.15, share risk | 50.4 | 49.5-51.4 | 66,545 / 58,157 | |
| s4: bonus 0.3 + penalty 0.3 | 48.7 | 47.7-49.7 | 67,603 / 59,061 | |
| s5: 0.15 / 0.15, risk by absolute steps from the enemy spawn | 51.3 | 50.3-52.2 | 66,283 / 60,080 | +0.57 (-0.66..+1.79) |
| s5 held out | 50.7 | 49.7-51.6 | 61,774 / 56,440 | -0.02 (-1.23..+1.19) |

- s5 (3,070 held-out games): allies within 8 at contact 1.60 / 1.55, deaths 6.15 / 6.45, kills 5.05 / 4.75, gems
  949 / 944; solo 0.5% slower to 1000 gems. Penalties alone push champions out of the middle (26.8 -> 24.8% of
  time) instead of into it together, as buddy cohesion did; bigger weights pull them across the map; home_side's
  share mislabels large maps (s1-s4 45.5-49.0% there). Fights with 0 / 1 / 2+ allies within 8 kill us 15.8 / 12.7 /
  10.1% in self-play. The fight sims count allies within 4 only, so an ally 6-10 away changes no decision.
  `coh-a-s6` = s5 with a per-group pruning cap: bench replays identical, -0.7% fuel.

On top of 292 (fresh-84001..84020, against astraeus-292; 292 against v66 there: 61.2%):

| Variant | Win % | 95% CI | OOF cand / ref | v66 paired |
|---|---|---|---|---|
| 292 + B's c6 (`ast292-c6`) | 50.0 | 49.0-50.9 | 92,318 / 75,772 | |
| 292 + B's c5 (`ast292-c5`) | 49.7 | 48.8-50.7 | 80,626 / 75,045 | +0.30 (-0.64..+1.25) |
| 292 + A's s6 (`ast292-a6`) | 50.1 | 49.1-51.0 | 83,649 / 75,998 | |

- B's fight posts and A's farm lean add nothing on 292 (all three cut deaths after contact) and cost fuel: dropped.

Cohesion weight in farm choice and team calls (agent D, dev 83061-80): worth x cohesion(g) = 1 - k risk (1 -
support), support from the nearest ally anchor (visible tile or claimed centre; 1 within 6, 0 at 14).

| Variant | Win % | 95% CI | OOF cand / ref | v66 paired |
|---|---|---|---|---|
| pull: -0.04 a step past 6 from the nearest anchor, floor 0.6, every group | 47.5 | 46.6-48.5 | 60,354 / 55,843 | |
| risk: front groups only (home_side share 0.6 -> 0.75), floor 0.7 | 48.5 | 47.6-49.5 | 57,987 / 54,104 | |
| risk2: risk, off before round 150 and while banking | 49.4 | 48.4-50.3 | 58,289 / 54,882 | -1.96 (-3.11..-0.81) |
| risk3: risk2 stronger (floor 0.55, zone to 0.8) | 46.1 | 45.1-47.1 | 58,784 / 57,683 | |
| sup: risk2 + `Safety::stand` counts visible healthy allies at 5-7 (joining after their walk) | 47.4 | 46.4-48.3 | 60,682 / 55,251 | |
| rally: sup + a rally bit when we stand only thanks to them; team_pressed takes a rallier's enemy | 46.9 | 45.9-47.9 | 70,280 / 55,774 | |
| int: risk2 + a second chaser cuts off the target's way home | 48.7 | 47.7-49.7 | 58,989 / 56,073 | |

- pull against 291 (2,048 games): allies within 8 1.56 / 1.42 over all rounds, crews 56 / 50% of camp-attack
  rounds, deaths 6.18 / 6.59, kills 5.25 / 4.83, tributed gems 810 / 832, and 291 farms the map we leave. The win
  rate falls as cohesion rises: each step buys ~+0.4 kills and -0.4 deaths and costs at least as much in gems and
  ground. Against v66 clearly negative.
- Self-play reproduces the ladder gap (allies within 8 at contact 1.58 locally, 1.60 on the ladder, top teams
  2.11; over all rounds 1.21 / 1.85, moving too; shared holds 3 / 15% of captures), yet locally an ally within 8
  lowers our death rate per round in no band. Striking first kills 19 / 21 / 21% at 1v1 / 2v1 / 3v1 locally; top
  teams 29 / 30 / 30% on the ladder. On the ladder our death rate at contact stays ~18% whatever the ally count;
  theirs falls 16 -> 5%. Lost stands are ~98 retreat turns a game; 32% have a healthy ally at 5-8 the verdict does
  not count, but counting or calling them (sup, rally) did not bring them.
- Read: support pays only if fights turn numbers into kills; our per-fight execution is the lever, not distance.

astraeus 292 (CHANGES 290-292) against 289 (57131355, `bots/variants/astraeus-5713135`) on fresh-84001..84020:
53.0% (52.0-53.9) of 10,240, out-of-fuel turns 66,132 / 57,968; on fresh-84021..84040 51.7% (50.8-52.7) of 10,238,
66,675 / 57,684; together 52.4% (51.7-53.0) of 20,478.

All four: free tie-breaks (C) are the only cohesion that paid. Leans that change choices (A, D, and C's own p5-p7)
buy kills and cost the same in farming; fight-side posts (B) improve fights alone but overlap 292. Combined with 292 (`bots/variants/ast292-c5`, `-c6`):
pending.

## Fights and planning

- Strike planner variants lost: ranged carriers holding fire to keep walking (47.9%); an early `prey()` for the intent
  (32k fuel, nothing measurable). A farming step priced at a full turn of output cost Ryth's and Ren's stuns 9-17% of
  their hits.
- Retreat planner (`plan_turn`, branch plan3): level at 100M and at the real budget, but 2.5x the out-of-fuel turns
  (a `Safety::blow` per enemy on up to 49 tiles). Also lost: the chase planned as a goal before acting (43.0-46.2%); a
  stun valued by the turn it denies instead of a flat 80 (48.5%).
- Reach changed few decisions (want_home 3.5k of 1.4M evaluations) and was level in play; its first version lost to
  fuel (41.3%).
- Strike search phase 1's first round lost 38.5% (40.5% even at 100M: deaths +34%) to illegal dashes, moves with no
  strike after them and fuel; the round that shipped fixed those.
- Strike phase 4a (retreat turns planned by the search, `orch/int-strike-p4a` 058f55b): 40.8%, but 52.6% at 100M with
  out-of-fuel turns +135%. The play is sound; the retreat search's cost (mean 21.6k, max 83.5k) must come down first.
- Step guard folded into the strike search (825ea36, then 8250a4f): no gain in three runs, all slightly down; with test
  drafts the guard, built after the search, hit its fuel gate twice as often.
- Enemy two-turn chain in threat_strike (w2-chain): 47.1%. `Safety::trapped` as a want_home trigger and guard
  (w2-trapped): 46.7%, out-of-fuel turns +60% (up to 24 tiles a turn at ~3-4k).
- Audit phases 2-3 (2026-10-22, CHANGES 87): Varg's attacks skipping any target whose splash touches a sleeping
  camp was a ban where the search prices wakes; held for a priced version (wake cost on champion hits, waking camp
  targets ranked last), untested. The two-turn chain was not retried (w2-chain above).
- Remembering enemy wards out of sight (kept until we see the tile without one), on top of CHANGES 90's per-owner
  sight: 49.6%, out-of-fuel turns level. Remembered wards were stale 90% of the time in a traced game against hecate
  (3439 wrong, 394 right; wards in sight 909/909 right). Known limit, accepted: an enemy's fresh ward placed in its
  own turn (sight counts at once) is not modelled, so `Reach` is bolder than reality beside our bush clusters.
- An ally's stun read with its stats when first seen in a round, kept on the belief (branch `astraeus`, 34ea5de,
  2026-10-23). Safety used to read it live, and after our move hid a believed-visible ally (vision is personal) the read
  threw and lost the rest of the turn. Against main, ladder + gen only: 50.0% of 592 (ladder 48.8 of 80, gen 50.2),
  out-of-fuel turns 2339 vs 2481. Level; a correctness fix, kept (CHANGES 111).
- Astraeus Willow cleanup, behaviour-preserving part (2026-10-23): heal targeting shared (`heal_ready`, `heal_target`),
  a recall flag in place of decision letters, Willow's sleep certificate replaced by camp beliefs plus
  `World::camps_current`, the plan's Willow guard exception dropped, the turn-end support re-read only after a ward.
  `bench.py` wide set, own drafts (astraeus drafts Willow on 5-pick maps) against the frozen
  `bots/baselines/astraeus-8d240cc`: 52/52 replays identical, fuel -0.1%. Swapping Willow's post-move `see_again` for
  `see_revealed` is not behaviour-preserving (its camp, ally and Safety reads follow the full re-observe): left for the
  A/B'd steps.
- Astraeus Willow step guard on hyperion's deferred guard (2026-10-23): stations memoised per World observation and
  tile, legality read at use, the guard a `GuardFn` through `guard_steps`; `support_vision` and `willow_step_guard`
  gone. Same bench: 52/52 identical, fuel -0.16% (p99 -1.1%). Dropping `credible_enemy_may_hit_within` cost +1.2% fuel
  (p99 +3.7%): it spares `threats_at`'s per-tile searches for unseen enemies, and `avoid_within` is no exact substitute
  (camps; a teleport's current tile, not its landing).
- Astraeus Willow exposure on Safety (2026-10-23): enemy damage, doubled-unacted damage, hit and stun from one new
  `Safety::bound(p)` pass (damage_bound's terms; unseen enemies at their full blow when any possible tile is in reach,
  where `threats_at` priced the nearest), awake camps as `camp_damage(p, true, true)`; Willow keeps counting sleeping
  members as exposure and its exit burden. A/B against `bots/baselines/astraeus-8d240cc` on all 211 five-pick maps
  (ladder, gen, gen-s1; 422 games): 49.3% (CI 44.5-54.0), out-of-fuel turns 2738 vs 3482. Level; kept. A first
  version with four Safety calls a tile (`damage_bound` twice, `may_be_hit` twice: each prices every visible enemy's
  Reach) was 51.2% but doubled out-of-fuel turns (6744 vs 3528); without the stations' enemy pre-check, fuel +2.1%
  (p99 +7.8%) at 100M. 3- and 4-pick maps never run this code.
- Astraeus Willow's turn on hyperion's (2026-10-23): `willow_economy_or_escape` gone. Its economy is hyperion's path
  with the search off while Willow holds a capture, carries a bag to bank or goes to shop (`support_work`): heal first,
  then `hold_capture` / `carry_bag` / the shop step (`strike_after` still takes a hit in reach). Its escape is a
  `want_home` rule: any enemy that may hit Willow, seen or not, sends it home, bar on a capture; `retreat` does the
  rest, so Willow's 9-tile escape ordering and the sleeping-camp bailout are gone (asleep monsters never hit; only
  Willow's exposure counted them). The post-goal call is gone: in 62 traced games it took 486 turns and never moved
  Willow (mostly a farm step onto a capture relabelled as a hold); after the change, turns ending exposed with a step
  left were all capture holds. `support_recall` gone (a support retreat is a plain retreat turn). A/B against the
  frozen c16939d on the 211 five-pick maps (422 games): 50.7% (CI 46.0-55.5), out-of-fuel turns 1769 vs 2635. Kept.
- Astraeus: the search's heal worth what it restores capped at `ability_cooldown * damage_bound` again (hyperion's
  `read_mates`; v44 valued the full restore, so an unthreatened ally took the cast from Willow's attack reset).
  Five-pick A/B against d308076: 51.4% (CI 46.7-56.2), out-of-fuel turns 1719 vs 1705. Kept.
- Astraeus: `see_revealed` for `see_again` after Willow's walks (both heal steps, `local_support`); a refused step
  still re-reads in full, as `revealed()` skips a tile we have not left. Five-pick A/B against 5917401: 50.0% (CI
  45.3-54.7), out-of-fuel turns 1784 vs 1746 (noise: the same bot read 1705 and 1746 in two runs). `bench.py` wide:
  49/52 replays identical, fuel -0.02%: these walks are too rare to matter for fuel. Kept as hyperion's pattern.
- Astraeus: Willow's danger weighed as `threatened()` weighs it (a visible enemy in reach, or unseen ones whose
  chance of a hit reaches `recall_risk`), enemies only: `Safety::bound` gains `threat` in its one pass, read by the
  `want_home` rule and by the exposure's `enemy` (so the stations' guard and the support formation's `safe()`
  agree with the rule). Camps stay out: Willow farms, and its exposure counts camp members itself. Five-pick A/B
  against 0c703ea: 50.7% (CI 46.0-55.5), out-of-fuel turns 2002 vs 1859, all of the rise on gen-shared-gems
  (374 vs 144 in its two games; the rest 1628 vs 1715). `bench.py` wide: identical games +0.00% fuel (the weighting
  costs nothing), all games +0.9% from changed play, 33/52 identical. Kept. As the reference of the next A/B the
  same bot ran 83 out-of-fuel turns on gen-shared-gems: the rise was a fuel trajectory.
- Astraeus with `retreat-sideways` merged (cfd1a3a; `retreat_step` ported into its bot.cpp): five-pick A/B against
  960cdfe, 51.7% (CI 46.9-56.4), out-of-fuel turns 1839 vs 1781.
- Astraeus (315910d) on all suites, both sides, each bot on its own draft (2026-10-23; 1104 games each; 5-pick maps
  422 of them, the only ones `willow_draft` changes):
  - Willow draft vs hyperion (main c71be8c): 50.1% (CI 47.1-53.0; 5-pick 49.8, 3/4-pick 50.3), out-of-fuel turns
    3288 vs 2503.
  - Hyperion's draft (`willow_draft = false`) vs hyperion: 49.9% (47.0-52.9; 5-pick 49.8, 3/4-pick 50.0), 2712 vs 2632.
  - Willow draft vs v44: 52.8% (49.9-55.7; ladder 65.0 of 80; 5-pick 53.6), 3133 vs 5334.
  - Hyperion's draft vs v44: 52.4% (49.5-55.4; ladder 58.8 of 80; 5-pick 53.6), 2744 vs 4971.
  Willow in the Ryth/Vendetta slot is level with hyperion's pick but costs ~30% more out-of-fuel turns; the reshaped
  Willow layer beats v44's slightly and uses far less fuel. (Equal 5-pick totals in both pairs are coincidence: the
  drafts differ and only ~10 of those 422 games matched.)
- Willow for Marcella on 4-pick maps (2026-10-24; astraeus at c2f1350 copied to `bots/variants/astraeus-willow4`,
  drafting Prism/Vesper/Willow/HoR; `replays/suites/4pick`, the 178 4-pick maps of ladder, gen and gen-s1, both
  sides, own drafts): vs hyperion 40.2% of 356 (CI 35.2-45.3), out-of-fuel turns 654 vs 510; unchanged astraeus vs
  hyperion on the same games 54.5% (49.3-59.6), 610 vs 520. Willow costs ~14 points as the 4th pick: lost. Asked
  because the ladder's 5v5 maps (the only ones v47 drafts Willow on) read +11.5 ± 7.2 points over 3v3, which a
  5th champion and the maps themselves explain as well as Willow.
- Bag deadline at the enemy's win (2026-10-24; astraeus at 80e21f3 copied to `bots/variants/astraeus-enemyrace`):
  `World::enemy_rate` (as `ally_rate`, over the later half of the game) and `bag_rounds_left` also capped by
  (1000 - enemy score) / enemy rate, so `closing` banks a bag before the enemy is due to win. Motivated by v47's
  low-contact ladder losses, where Prism's held bag was 73% of the tribute gap. All suites, both sides, own drafts,
  against unchanged astraeus: 51.1% of 1104 (CI 48.1-54.0; ladder 55.0 of 80, gen 50.6, gen-s1 51.0), out-of-fuel
  turns 2395 vs 2446. Level, and not ported: the new cap binds only when `race_left` (the rounds until score plus
  every bag reaches the win at our rate) comes after the enemy's projected win, i.e. when we are projected to lose
  the race, where banking gives up Prism's Focus and carriers' chases (`carry_bag` chases only while not `closing`)
  for nothing. Projected to win, `race_left` already sets an earlier deadline. If our pace is underestimated
  (`ally_rate` counts tributes, not Prism's growing bag), the fix is a collection-rate `race_left`, not an enemy cap.
- Stuns priced in the strike search's end-tile danger (2026-10-24; astraeus at 80e21f3 copied to
  `bots/variants/astraeus-stunprice`): a blow that stuns adds a turn of our output (`output()`'s formula; 0 for
  Marcella) to its damage at `plan.cpp`'s four danger sites. Motivated by v47's Tavi games: half of Tavi's stuns on
  us land from range 4, and 79% of victims saw it ready.
  Against `bots/variants/astraeus-stundraft` (astraeus drafting Tavi for Vesper: Prism and Tavi at every pick count),
  all suites, both sides, own drafts: 60.1% of 1104 (CI 57.2-63.0); unchanged astraeus against it 59.9% (57.0-62.7).
  974 of the 1104 games changed, but stuns on us stayed 22.4 a game (Tavi's 7.23 vs 7.28), deaths 4.1 vs 4.1: the
  term moves end tiles without keeping us out of stun range. Not ported.
- Astraeus fuel, behaviour-preserving (2026-10-24, against the frozen `bots/baselines/astraeus-e72724a`):
  - Prism's recovery takes its cheap exits (`!ready`, `worth_healing`) before the mate's exposure and the formation view.
  - Tiles in `local_support`'s loop are judged safe after its other filters.
  - The independent heal step judges its own tile after its target and camp-finish filters.
  - Willow's guard is an empty board when no enemy may hit within a step: no 9-tile build for camps alone.
  - After Willow's walk and at the turn's end, `exposure_here` prices our tile alone, not a fresh 9-tile build.
  - `stations()` is keyed only once built, so a throw part-way through leaves nothing to reuse.
  - Only Prism and Willow read the support mailbox; its endpoints are found once.
  - Write-only state removed.

  `bench.py` wide set, own drafts: 52/52 replays identical, fuel -1.54% (mean -1.6%, p99 -0.8%), turns over 100k
  1233 -> 1164. Only 5-pick maps run this code.
- Astraeus Willow-layer logic fixes (2026-10-24, 4217ceb, against the fuel cuts above, `bots/variants/astraeus-de55b3c`):
  - Willow casts the heal it stepped for when the step reveals a threat (it gave the rest of the turn up unhealed).
  - `immediate_camp_finish` skips dead members (health 0 read as a finish).
  - `heal_ready` judges an ally by what stops its coming turn's heal (stun, kept recall, tribute, teleport,
    cooldown); a routine recall started at a turn end no longer stops Prism's recovery.
  - Willow's heal and formation views add our tile and our ward's sight, as the search's `viewers()` does.
  - Prism's recovery always prices the walk out by the spawn field, never Chebyshev while the field was cold.

  Five-pick A/B (211 maps, both sides): 53.6% of 422 (CI 48.8-58.3; ladder 60.4 of 48, gen 51.0, gen-s1 54.7),
  out-of-fuel turns 2729 vs 2854. Fresh five-pick suite (`mapgen suite --seed 1031`, 89 maps): 46.6% of 178 (CI
  39.4-54.0), 523 vs 630. Pooled 51.5% of 600: level. Kept: each is a rules-derived correction with no trade-off.
- Astraeus: Prism waiting in place for Willow's heal takes its free basic attack (95f9a84, against cb61eaa): a visible
  enemy in range, else a camp whose whole group has no strength; casts stay with the search. Five-pick A/B plus the
  fresh seed-1031 five-pick suite: 49.5% of 600 (CI 45.5-53.5), out-of-fuel turns 3421 vs 3441. `bench.py` wide:
  52/52 replays identical; the branch ran on 31 turns and never found a target (the safe tile already keeps enemies
  and striking camps out of range). Kept, level: it costs nothing and rarely fires.
- Astraeus bug fixes from TODO "Bugs, ranked" (2026-10-24, each against the one before, starting at v47; full A/B,
  1104 games, each bot on its own draft):
  - A fully shield-absorbed spell or landing priced with Durability (`min(raw * taken, shield)`; TODO #6): 50.1%
    (CI 47.1-53.0; ladder 51.2, gen 50.4, gen-s1 49.6), out-of-fuel turns 2475 vs 2473. Kept (CHANGES 113).
  - Dashers' farm altar distances from their own field, not the draft's walking steps (TODO #2): 51.6% (CI 48.7-54.6;
    ladder 55.0, gen 51.0, gen-s1 51.8), out-of-fuel turns 2569 in 536 games vs 2497 in 494. Kept (CHANGES 114).
  - `capture_taken` skips allies bound elsewhere (tributing, a kept recall, claiming another group) unless on the
    group's tiles (TODO #4): 50.1% (CI 47.1-53.0; ladder 51.2, gen 50.0, gen-s1 50.0), out-of-fuel turns 2896 vs
    2706 (that REF read 2569 in the run before). Kept (CHANGES 115).
  - An enemy we killed mid-turn marked dead by `observe()` instead of becoming an unseen threat (TODO #1, first
    item): 50.0% (CI 47.1-52.9; ladder 50.0, gen 49.8, gen-s1 50.2), out-of-fuel turns 2783 vs 2789. Kept (CHANGES
    116). #1's other items need restructuring and were left.
- Astraeus batch-1 fixes from replay evidence (2026-10-24, each against `bots/variants/b1a-ref` = 4d08241; full
  A/B, 1104 games, each bot on its own draft):
  - A capture hold under `recall_health_fraction` stays only while last round's damage (`Memory::damage`) times the
    rounds to payout + 1 is below our health (camps behind walls and bush attackers hit unseen), and the approach to a
    respawning group leaves its camp tiles out of the goals (an occupied group returns late): 50.8% (CI 47.9-53.8;
    ladder 47.5, gen 50.0, gen-s1 52.1), out-of-fuel turns 2823 vs 2804. Kept (CHANGES 117).
  - `retreat` takes a sure kill one step off (melee, whose walk keeps the attack) or a dash off, from a tile where
    `only_threat` finds nothing but the victim reaching us (MATCH_GROUP_REVIEW Finding 2: a low Heart of Ruin walked
    away from a 23-health Ryth two tiles off): 50.2% (CI 47.2-53.1; ladder 50.0, gen 50.0, gen-s1 50.4), out-of-fuel
    turns 2810 vs 2802. It fired 8 times in 80 ladder games. Kept (CHANGES 118). Not done: `retreat_step` still
    counts an enemy just killed as a threat, and a leave turn's shield takes Heart of Ruin's and Varg's one cast first.
  - A carrier (`bag_at_stake >= brake_bag`) healthy on our own ground gets `want_home`'s pursuit check
    (`stand(here, pursuit_steps)`), as off it: a kill takes the whole bag, so the exemption's "no reason to come for
    us" fails for a bag. Against 116: 51.1% (CI 48.1-54.0; ladder 56.2, gen 48.8, gen-s1 52.5), out-of-fuel turns
    2632 vs 2718. Gems lost on death 105.3k vs 111.3k (deaths with 11+ gems 1240 vs 1353, with 50+ 556 vs 582);
    tributed 857k vs 845k. Prism, stronger with a bag, still fights: its kills 1224 vs 1159, tributes 175.8k vs
    167.6k, champion damage -2%. Again against 118 (same function as 117): 51.4% (CI 48.4-54.3; ladder 55.0, gen
    51.2, gen-s1 51.0), out-of-fuel turns 2733 vs 2745. Kept (CHANGES 119).
- Joining an enemy Monolith siege on mixed maps (b1 ideas #3; ladder: 13-27 when the opponent took a Monolith, 43-20
  when nobody did; 2026-10-24, from 4d08241). Our bots never siege there, so it was judged against a proxy sieger
  (REF with `siege_candidate`/`siege_ready` passing live Monoliths on every map) on the 134 mixed-Monolith maps of
  `maps/`, `maps/gen`, `maps/gen-s1` (`replays/suites/b1b-monomix`). The proxy took 391 Monoliths in 268 games
  against REF's 11; REF won 76 of the 177 games where only it captured one. An awake, visible Monolith with a visible
  enemy in its reach (or already our siege claim, or an ally's) is a siege candidate at its current health, with
  the health-pool check skipped while an enemy is in its reach (the nearest champion takes the hits). Vs the sieger:
  REF 55.2%, candidate 58.6% (paired 17 flips to wins, 8 to losses); fresh mixed-Monolith suite (seeds 7311/7312, 136
  maps): REF 50.0%, candidate 54.4% (27 vs 15; both suites p ~0.014). Our Monolith captures 11 -> 33 (2.4k -> 7.2k
  gems), the sieger's 391 -> 373; 28 of ours were kills we finished, and contested resets fell 10 -> 1: the gain is
  finishing the kill and taking the tile, not contesting it. Deaths level. Full suites vs REF 49.9% (CI 47.0-52.9;
  ladder 50.0, gen 50.0, gen-s1 49.8), out-of-fuel turns 2779 vs 2743; vs hyperion 50.5% (ladder 51.2, gen 51.0,
  gen-s1 49.8). Kept (CHANGES 120); judge on the ladder by Monolith gems on mixed-Monolith maps.
- Stun-cycling long enemy tributes (b1 ideas #4), trace check only (v47 harness, 320 ladder games, trusted rounds):
  898 enemy channels of 70+ gems (2.8 a game; 175 Marcella's, stun-immune). A stunner of ours (Prism, Heart of Ruin,
  Marcella; v47 drafts no other) could reach stun range with the stun ready before completion in 315 (0.98 a game;
  cooldown never decided it, as these channels last 7+ turns), and 219 of those completed (0.68 a game). Unescorted,
  seen by us and within 8 steps: 64 (0.20 a game); 90 of the 219 had 1-3 escorts. 18 of our 55 stun or lock cancels
  were tributed later anyway. Below the ~1 a game bar for a build; not built.
- Untried: count a Heart of Ruin landing as a cast only when it hits something.
- `tribute_safe` refusing a channel a ready visible stun can cancel (REPLAY-FOLLOW-UPS R1-11; branch `fu/tribute-stun`,
  2026-10-23): a stun ready on any enemy turn before the channel ends 49.8%, only one that lands on the enemy's next
  turn (3d8b89e) 50.1%; out-of-fuel turns level. It fired ~10 times in two local games, mostly mid-channel where
  `continue_tribute` keeps the channel anyway. Dropped. Lock cancels (115 on the ladder) untried.
- Kill value (REPLAY-ANALYSIS C2: big nukes on healthy enemies beat sure kills; branch `fu/kill-value`, 2026-10-23):
  a kill worth at least the victim's max health (0528bd4) 49.9%, slightly fewer kills and more deaths (the floor
  raises every late kill against danger, not only against the competing hit); a killing blow worth
  `max(health, damage) + life_value + bag`, so a sure kill never loses to the same blow elsewhere (51c4fa7) 50.3%.
  Out-of-fuel turns level. Dropped; 51c4fa7 still counts a non-lethal hit before a kill on the same enemy.
- Chased retreats (REPLAY-ANALYSIS A2: 81% of deaths on retreat turns) are lost fights, not a worse retreat
  (2026-10-23, 624 ladder games, both teams): low and pressed (<35% health, enemy within 4, off spawn) we died within
  20 rounds in 39% of episodes, the opponents in 46%; lone healthy contacts 10.6% vs 15.6%. Walking home did best of
  the movement classes for both teams; moving toward allies did worse. Long retreats dying is mostly selection.
  Don't retune where or when we retreat on A2's evidence.
- `retreat_step` taking a sideways step over a free homeward one only when it leaves every reach (`fu/retreat`
  e617c90; sideways steps with damage > 0 were followed by death 688 times in 6,277 chased turns, 376 expected at
  the direct-step rate, an association): 50.3%, out-of-fuel turns level. Dropped.
- `retreat_step` taking a step that lengthens the walk home when it leaves every reach (`damage_bound` 0) and no
  step that keeps or shortens it does; one still in reach stays excluded (branch `retreat-sideways`, bbef5e4,
  2026-10-23). In a Willow trace 519 retreat turns ended in reach with no such homeward step. Against main: 49.7% of
  1104 (CI 46.8-52.7; ladder 48.8, gen 49.4, gen-s1 50.2), out-of-fuel turns 3813 vs 3956. Level; kept (CHANGES
  112).
- Tracking unseen enemies past 10 rounds (REPLAY-ANALYSIS A4; `fu/tracking`, 2026-10-23). The untracked killers were
  last seen a median 31 rounds before the kill (quartiles 19-88; 28 of 148 within 15). By 10 rounds an unseen
  enemy's possible tiles (median ~300 for Marcella, ~650 for Vesper) are past what `credible_weight` counts, so the
  cutoff rarely decides (098927ae-3: 294-369 tiles when dropped). Never dropping: 48.5%, out-of-fuel turns +18%
  (50.5% at unlimited fuel). Kept past 10 rounds only while the set is <= 338 tiles (1a1a48c): 50.2%. Dropped.
- Altar locks (REPLAY-ANALYSIS D2; `fu/locks`, 2026-10-23). Ladder: we placed 2,811, mostly in passing on our own and
  middle altars; 118 cancelled 121 enemy tributes (20.3k gems), and enemies spent 8,722 basic attacks removing 1,712,
  so most of the value is that tax. Enemy locks cancelled 112 of ours, mostly short channels that banked a median 31.5
  rounds later (17 carriers died, 3.4k gems). Only 32 of 115 cancels had the locker seen carrying a lock within 3 of
  the altar, so defending has almost no ceiling. A lock-carrier with nothing better walking into lock range of a
  visible enemy tribute it can reach in time (`lock_tribute`, before `chase`): 50.2%; bags of 50+ only (46115ba):
  50.0%. Out-of-fuel turns level. Dropped: a cancel only delays the bag.
- Prism's earnings gap is not its turn logic (2026-10-23, 624 ladder games, freezes of 50+ rounds left out): ours 239
  gems per 1,000 alive rounds, the 85 enemy Prisms 324. Kill gems are 64 of the 85 (20 vs 84): 42% of theirs came from
  35 kills of our Prism and its kept bag (retention), and 42% from one game (03898b90-1). Capture gems 220 vs 240 (not
  significant); where both sides had a Prism ours did 15% more camp damage and 16% more captures but earned 14.5 gems
  a capture against 19.4 (Monolith captures 23 vs 37 per 1k explain 14 of the 31 points; the rest is group choice).
  Its idle time (14.7% vs 8.2%) is mostly holds, kite stations and respawn waits, by design. No change made.
- v38 replay analysis (830 top-20 ladder games, 2026-10-23; deleted 2026-10-26, `git show
  c6bd5030:research/hyperion/REPLAY-ANALYSIS.md` and `REPLAY-FOLLOW-UPS.md`). Fixed: CHANGES 92-98, 100, 118; dropped
  above. Verdicts were well calibrated (`stand_ok` followed by death on 0.023% of turns); the misses were the
  cooldown gap (CHANGES 95), unseen wards and untracked killers. Leads never followed up, from v38 and not rechecked on
  astraeus:
  - A Marcella walk-then-cast the threat build rated unreachable, not the cooldown gap (2612381c-4 r561; her walk
    tiles were bushes).
  - A walker ping-ponging between tiles the farm rates 60 and 61 steps (03898b90-2, 00great_wall, r298-358).
  - Free captures cleared in passing and never held: `home_ground` zeroed a group 3 tiles away, which farm read as 94
    steps (00f80df5-4, 00reverse_spiral; 298 groups, 7.1k gems).
  - Standoffs: on strike-search turns farm skips its evaluation (CHANGES 81), so two champions froze 741 rounds
    (bfabbed2-1); and endgame idling near spawn with no group to finish (`farm best=-1`).
  - Heart of Ruin shielding at full health over a sure kill: `shield_at`'s `damage_bound` counts the enemy the kill
    removes (7 turns). A landing kill on an adjacent 308-health Issac never offered (0f946dfa-3 r732-735).
  - Camp casts hold for visible enemies within range, not tracked unseen ones (83 of 251 nukes spent just before a
    kill window had the enemy unseen within 6).
  - Chasing with a bag: `prey` takes any chase whose 1v1 sim wins, blind to the bag and to other enemies (2.8% of
    carrying chases followed by the carrier's death within 15 rounds).
  - `place_lock` cancelled an unseen ally's tribute 3 times (it reads `ally.channel`).
- v47's 4-pick ladder deficit against v44 (-14.2 points stratified by opponent) does not reproduce (2026-10-24; all
  178 four-pick maps of `maps/`, `maps/gen`, `maps/gen-s1`, both sides, 356 games each). v44 is built on hyperion
  62825eb, so it already has CHANGES 107; the diff is 108-112 and the Willow work.
  - v47 vs v44: 48.3% (CI 43.2-53.5). Champion hits per game (Marcella's spell 9.5 vs 9.6, Heart of Ruin's basic
    attacks 36.0 vs 36.1), kills, deaths and holds all within 5%.
  - Against a third bot (hyperion, with v47's draft): v47 48.6%, v44 49.7%. With hyperion forced to the Claudus
    Maximus draft (Heart of Ruin, Tavi, Vendetta, Vesper Vale): v47 61.5%, v44 60.4%. Forced to the ladder's most common draft (Heart of Ruin, Marcella, Ryth, Vesper Vale):
    v47 58.4%, v44 61.5%. Across the three: v47 about 1 point behind, within noise. (`draft_order` ignores
    `draft_preference` on 4- and 5-pick maps, so a `make_variant.py` opponent there drafts as hyperion unless that
    branch is disabled.)
  - Reverts on v47, against v47: 108's unseen-threat field back to walking distance 48.3%; 112's `retreat_step` 49.7%.
    Neither moves the readouts.
  - On the ladder the deficit is mostly confounding. Stratified by opponent, map and side: -5.9 (CI -10.1..-1.7).
    Restricted to games after 03Z, when the opponents' bots were closer in time: +0.6 (CI -9.0..+10.2). v44's own
    results flip within one opponent, map and side over the night (Sponge, rushbait_v2, b: `wllwlwwww`), so opponents
    changed bots. The "same in the overlap window" figure is Claudus Maximus alone. v44 played it there only on
    gemfight and hooks, where v47 also wins; v47's losses to it are on rushbait_v2, reverse_spiral, rows and shortcut.
    The engagement drop also goes away per opponent: against the Ryth draft, Marcella's spell hits go 17.1 -> 18.3
    and Heart of Ruin's attacks 72 -> 71. Against Sponge they are 22.5 -> 21.8 and 85 -> 92. It comes from the
    opponent mix and from Claudus Maximus. Prism tributing nothing (13% of v44's games, 43% of v47's) tracks losses,
    not a cause: locally both are at about 47%. No change made.
- Astraeus 24507a0 (CHANGES 113-120 together) against v47 (2026-10-24): 54.3% of 1104 (CI 51.3-57.2; ladder 57.5,
  gen 51.4, gen-s1 56.6), out-of-fuel turns 2617 vs 2464; fresh suites `--seed 1101` 49.6% of 512 and `--seed 1102`
  50.4% of 512 (together 50.0% of 1024). Each change was kept on the committed suites, so 54.3% is selection; the fresh
  50.0% is the estimate: level in self-play. Most of the eight are correctness fixes, and two (119, 120) target
  ladder behaviour our bots lack.
- Astraeus acbcbcb (CHANGES 113-123) on the same two fresh suites (1024 games): against v47 49.1% (CI 46.1-52.2),
  out-of-fuel turns 2290 vs 2089; against hyperion 53.0% (50.0-56.1), where v47 reads 51.3% (48.2-54.3). Level
  against v47, +1.7 against a third bot (within noise).
- Astraeus 8c2fd5b (CHANGES 113-131) on the unused fresh suite `replays/suites/b4-fresh` (seed 7411, 512 games):
  against v47 50.6% (CI 46.3-54.9), out-of-fuel turns 1072 vs 993; against hyperion 53.5% (49.2-57.8), where v47
  reads 49.0% (44.7-53.3). Pooled with the 1101/1102 runs against hyperion (1536 games): 53.2% vs v47's 50.5%.
- Batch 2 fights (2026-10-24, against d3cc38f, 1104 games unless noted):
  - Enemies who walk into a fight join the verdict (CHANGES 122). In want_home, prey and step_guard: 50.2% (47.2-53.1),
    out-of-fuel turns 2813 vs 2596. Without step_guard (kept): 50.9% (48.0-53.8; gen-s1 52.0), 2573 vs 2778; fresh
    seed 7321 52.1% of 512; against hyperion 53.4%. A debug trace showed verdicts flipping at arrivals 1-3 as
    intended (no implementation error). The guard's earliest-arrival pricing makes every step tile with a nearby
    enemy look worse than it is, which may be why it lost.
  - Vesper attacks, then dashes clear in `retreat()` instead of dash + walk (`dash_clears(..., exposed)`): 48.9%
    (46.0-51.9), 2495 vs 2557. Bundled with 121: 49.3%, 3/4-pick maps 48.9% of 724. Dropped: the walk it gives
    up is a tile of distance the pursuer must close next turn, so it is a trade-off, not a free attack.
  - Willow takes no chase (CHANGES 121): 49.5% of 380 five-pick games. Kept as a consistency fix.
  - Enemies in bushes posted first in the shared sighting slot (CHANGES 124): 49.7% (46.8-52.7), 2573 vs 2564. Kept
    as level; local bots stand in bushes little, so judge it on the ladder by blind damage taken.
- Recently seen unseen enemies join a fight's verdict late (`b5-late`, 2026-10-24, against 03cf613): CHANGES 122's
  `Safety::late` and `stand()`'s joiners (the latter only once a visible enemy hits us) also took credible unseen
  enemies (weight > 0, last seen at most 2 rounds ago, off their spawn), arriving after the walk from their nearest
  possible tile to reach (1 if a possible tile is already in reach but outside the key). 49.3% of 1104 (46.3-52.2;
  ladder 51.2, gen 49.0, gen-s1 49.2), out-of-fuel turns 2309 vs 2201. A debug trace (3 games) had it firing as
  meant: 34 stand verdicts with an unseen joiner, 12 flipped from won to lost. Dropped. A likely cause (not
  tested): the nearest possible tile puts a 1-2 round stale enemy 1-2 tiles closer than it probably is.
- Double turns from turn order (`b7-bands`, 2026-10-24, against 2b34c2f). By the rules a champion gets two actions
  with no enemy between only by acting after an enemy in round R and before it in R+1, and acting before an enemy
  next round never hands it a double: astraeus already prices this in `offer_kills` (full value when the enemy has
  acted, via `can_act_before`), idle low and in-contact high in the teacher scale. But the teacher six (our whole
  draft) skip the bands since CHANGES 82, so it never ran for them. Letting every champion bid the kill band (kills
  and channel cancels needing us first; heal, escape and channel bids still non-teacher only): 49.3% of 1104
  (46.3-52.2; ladder 47.5, gen 49.8, gen-s1 49.0), out-of-fuel turns 2268 vs 2166. Fired ~7 times a game (Prism
  mostly). Dropped. herbert's secret LAST/FIRST bands add nothing over this: priorities are readable in sight.
- A stun we cast read mid-turn (`b8-stun-cast`, 2026-10-24, against 2b34c2f; TODO bug 1): `World::read_stuns` after
  our stunning cast, Safety rebuilt if a target's `stun_pending` changed. 50.5% of 1104 (47.6-53.5; ladder 53.8, gen
  50.8, gen-s1 49.8), out-of-fuel turns 2438 vs 2305. Kept, level (CHANGES 128).
- An enemy revealed by a refused step while we stay on the tile vision was read from (`b8-bump`, same REF; TODO bug
  1): `see_revealed` checks for it after a bump. 49.6% of 1104 (46.7-52.6; ladder 50.0, gen 49.2, gen-s1 50.0),
  out-of-fuel turns 2377 vs 2428. Kept, level (CHANGES 129).
- Stale camp stuns and thrown errors (`b10-fix`, 2026-10-24, against 298cff1; batch 5 bug hunt findings 3 and 5): a
  camp's stun buff counts only at timer > 0 (timer 0 is spent; `probe-campstun`); no tribute start while stunned, no
  lock retry at an altar our team locks out of sight, no second recall start in a round. 50.5% of 1104 (47.5-53.4;
  ladder 52.5, gen 51.8, gen-s1 48.8), out-of-fuel turns 2389 vs 2544. Kept, level (CHANGES 130). Not fixed: an
  exclusive cast after a walk in a strike plan (2 errors) comes from a resumed out-of-fuel tail that walked in the new
  round; an enemy respawning before our next turn is still no threat (finding 4, 17 hits in 563 games: needs a belief
  at its spawn through Safety, not small).
- No action in a turn's resumed out-of-fuel tail (`b11-stale-act`, 2026-10-24, against e2deee3): every action host
  call checks the round first (`throw_if_stale`), so the tail that ran out of fuel no longer walks, attacks, casts or
  starts a recall in the next round ahead of the fresh turn (61 such actions in 47 of 230 out-of-fuel turns in 80 ladder
  games before; the source of the rc 113 and rc 126 errors). 49.5% of 1104 (46.5-52.4; ladder 48.8, gen 49.8, gen-s1
  49.2), out-of-fuel turns 2502 vs 2537; 100M bench 52/52 identical. Kept, level (CHANGES 132).

- Phase 1 correctness bundle (2026-10-24, astraeus c0de6b4 as `bots/variants/p1-ref`; ladder + gen 592 games
  unless noted). The bundle (`p1a-fix`): stun checks by `stun_pending` instead of `has_stun`; our own hits re-read
  (enemy kills via `see_kills`, woken camp groups via a members-only `update_camp`, channels a stun cancels cleared in
  `read_stuns`, our own fighter from live health and shield); endgame tributes (Marcella's attack, reset, attack on a
  tributing carrier, attacks aimed at the carrier, no walk-spending action before closing in; `place_lock` compares
  landing times; `enemy_tribute_wins` sums visible tributes landing no later; tribute while holding a capture);
  Marcella's 2 gold per tributed gem in farm worth; a Heart of Ruin dash counted as a damaging cast (`main_stat`) only
  when it lands on something; retaliation checks against health plus shield over Durability. 44.6% of 592 (40.6-48.6),
  out-of-fuel turns 1507 vs 1105. Split:
  - Own-hit re-reads (`p1a-state`): 47.3% (43.3-51.3), out-of-fuel 1570 vs 1079: a Safety refresh, our fighter rebuilt
    and camps re-read from two tiles on nearly every farming turn. Lean version (`p1a-state2`: one `is_alive` per
    visible enemy, `see_again` only after a kill; camps re-read only after a camp hit, from our tile; no self rebuild):
    49.3% (45.3-53.3), out-of-fuel 1247 vs 1146.
  - Heart of Ruin cast count (`p1a-hor`): 48.5% (44.5-52.5), out-of-fuel 1019 vs 1055.
  - The rest with CHANGES 135 (`p1-rest`): 49.5% (45.5-53.5), out-of-fuel 1313 vs 1175; plus the Heart of Ruin count
    on gen-s1 (`p1-rest-hor`): 49.8% of 512, 1462 vs 1303.
  - All of it (`p1-final`): 46.5% of 1104 (43.5-49.4; ladder 43.8, gen 45.3, gen-s1 48.0), out-of-fuel 2849 vs 2464.
    The small deficits add up. Kept: CHANGES 135 alone; then the stun checks and Marcella's gold (user's call). The
    own-hit re-reads, endgame, retaliation and Heart of Ruin parts are held in `bots/variants/p1-final`.

## Hold rule and the work guard (2026-11-01, astraeus 5880baa1; CHANGES 269)

Own drafts, real budget, against `variants/astraeus-base` (5880baa1). Mid-size runs: ladder + fresh-30200/30201
(1,164 games); fuel smokes on the ladder (140).
| Variant | Win % | Games | Out-of-fuel turns (cand / ref) |
|---|---|---|---|
| hold rule alone (want_home exemptions, no work guard) | 50.6 | 1,164 | 4,837 / 4,213 |
| hold rule + work guard (zone, recall line, hold tiles) | 52.9 | 1,164 | 6,970 / 4,657 |
| that + the stand's pursuers in the guard | 51.2 | 1,164 | 10,646 / 4,527 |
| shipped (keep_out cached, cover exact; before the audit fixes) | 50.8 | 10,240 (fresh-30210..30229) | 43,287 / 37,594 |
| shipped, audit fixes (lethal blocks a hold; full GuardState) | **51.5** | 15,360 (fresh-30210..30239) | 65,458 / 56,085 |
- Pursuers in the guard: each tile's stand needs a fight simulation. Per-tile exact stands cost a median 12.6k a
  guard (p90 33k); a bound roster by distance (no Reach, no threat build) and one union fight first, then per-tile
  with dominance, still p90 ~8k and the out-of-fuel turns x2.3. A cover of every tile beside us made routes work
  the guard out every turn (no saving). Dropped for no measured gain; the stand-lost-to-pursuers flips remain.
- Flips (A-B-A tiles) are unchanged by the guard (2.92 vs 2.93 per 100 champion-rounds): half the step-then-leave
  turns in a debug trace were enemies moving between our turns, which no same-world check removes.
- Hold metrics (2,048 games): walked-off resets 1.17 vs 2.40 a game; pressured holds paid 81% vs 71%; deaths level.

## Stack 269-272 (2026-11-01, astraeus; CHANGES 269-271 and the dropped retreat change)

The hold rule (269), Willow's heal gate (270), C&I `partner_bound` (271) and the ranged retreat's shots (272 then; dropped from the
2026-11-02 RC, so the shipped 272 is the stack's fuel cuts) merged, with the audit fixes (CHANGES "269-271 together"). Own drafts, real budget, fresh suites unused before; the paired
columns compare two A/Bs game by game on the same maps and sides.
| Pairing | Suites | Games | Win % | 95% CI | Out-of-fuel turns (cand / ref) |
|---|---|---|---|---|---|
| stack vs `astraeus-hold` (269 alone) | fresh-30700..30719 | 10,240 | 49.8 | 48.9-50.8 | 47,041 / 45,468 |
| stack vs `astraeus-base` (5880baa1) | fresh-30720..30739 | 10,240 | 50.9 | 50.0-51.9 | 44,839 / 37,974 |
| stack without the retreat change vs hold (ablation) | fresh-30700..30719 | 10,240 | 49.9 | 48.9-50.8 | 46,892 / 45,396 |
| stack vs v61 / base vs v61 | fresh-30740..30749 | 5,120 each | 85.1 / 84.4 | paired +0.7 (-0.4 to +1.8) | 20,185 / 23,652; 16,057 / 25,009 |
| stack vs v65 / base vs v65 | fresh-30740..30749 | 5,120 each | 77.8 / 77.0 | paired +0.8 (-0.5 to +2.0) | 23,699 / 29,860; 19,642 / 29,747 |
| stack vs hecate / base vs hecate (copy, test_draft off) | fresh-30740..30749 | 5,120 each | 98.2 / 97.9 | paired +0.3 (-0.1 to +0.7) | 22,051 / 13,417; 18,052 / 13,894 |
- Against hold, by our draft (stack): with Willow 49.4% of 1,833 (270's own A/B: 52.8% of 1,741), without 49.9%; C&I
  on either side 49.6% of 5,086; ranged champions 0/1/2/3+ 50.0/50.1/49.3/48.3%. Per champion-game, stack / hold:
  Willow deaths 1.89 / 1.75, healing 29.0k / 28.3k; Prism deaths 0.71 / 0.67; Vesper 1.19 / 1.13; Issac damage taken
  2,184 / 2,404.
- The ranged deaths pointed at the retreat change, but without it the stack is the same against hold (paired -0.02 points, -0.63 to
  +0.59) and its Willow games 49.8%: no single change drags; 270's Willow gain did not show on these suites.
- The stack's out-of-fuel turns: +3.5% over hold, +18% over base (269's +17%); against the older bots +21-26% over
  base's.

## Fight play-out with reach, and our fall before theirs (2026-11-01, astraeus; CHANGES 273)

From the v66 calibration (research/v66-replays/README.md 4e). Positions joined to the level-2 sims
(`scripts/simreach/collect_pos.py`, on branch `held/reach-playout`): of the fighter-rounds the sim has striking, 36% are out of the fighter's
one-turn strike reach of every opposing member at the round's start and hit 5% of the time; within basic range
65-70%, within walk/dash reach 33-39% (`hitstate.py`). Walkers past their reach at the start join within 5 rounds
40-45% (gap 1), 30% (2), 20% (3) (`arrive.py`).
- **Reach play-out** (branch `held/reach-playout`, cb2328dd): per pair, the turn each fighter can first strike each
  opposing member (its walk past its strike reach, a step a turn, or the other walking into its own reach, plus the
  steps by which that reach exceeds this one's); each strikes the weakest it reaches, so Cassi & Issac fall through
  the body reached; our own fighter strikes an enemy from the turn that enemy can strike it, so the fight stays a
  function of its roster (memo, step_guard covers). The per-tile version calibrated no better.
- **Calibration** (Python port, stand sims r<=260, all; `evalreach.py stand all ...`; this section's `scripts/simreach/` files are on
  branch `held/reach-playout`), ladder / self-play:

  | Verdict | lost | AUC (side loses more, 10r) | AUC (our death, 10r) | not lost | death 10r after | their first-death share |
  |---|---|---|---|---|---|---|
  | base (v66) | .343 / .343 | .637 / .638 | .668 / .657 | 5,082 / 4,483 | 5.5% / 3.4% | .584 / .710 |
  | + our fall first loses | .382 / .380 | same | same | 4,777 / 4,230 | 4.5% / 2.6% | .618 / .739 |
  | reach | .362 / .359 | .646 / .642 | .680 / .662 | 4,936 / 4,372 | 5.0% / 3.3% | .598 / .715 |
  | reach + fall first | .425 / .413 | .646 / .642 | .680 / .662 | 4,448 / 4,007 | 3.8% / 2.2% | .643 / .760 |

  Against Cassi & Issac reach does most (ladder AUC our death .641 -> .657). One-step joins counted at once, or reach
  on one side only, calibrate the same or worse.
- **A/Bs** against `variants/astraeus-stack` (66e2c518), own drafts, real budget:

  | Candidate | Suites | Games | Win % | Out-of-fuel turns (cand / ref) |
  |---|---|---|---|---|
  | reach + fall first | fresh-31100..31103 | 2,048 | 51.4 | 10,883 / 9,838 |
  | reach + fall first | fresh-31106..31107 | 1,024 | 51.3 | 5,237 / 4,610 |
  | reach + fall first | fresh-31108..31115 | 4,096 | 51.6 | 20,365 / 16,666 |
  | reach + fall first (cheaper placing) | fresh-31116..31119 | 2,048 | 50.8 | 8,975 / 7,554 |
  | reach alone | fresh-31104..31107 | 2,048 | 48.6 | 10,426 / 9,164 |
  | fall first alone | fresh-31104..31105 | 1,024 | 51.8 | 4,781 / 4,742 |
  | fall first alone | fresh-31108..31115 | 4,096 | 50.6 | 17,094 / 16,515 |
  | fall first alone | fresh-31116..31119 | 2,048 | 51.3 | 7,649 / 7,737 |
  | **fall first + guard fix (shipped)** | fresh-31120..31139 | 10,238 | **51.0** (50.0-52.0) | 42,686 / 42,232 |

  Same suites (6,144 games): reach + fall first 51.4%, fall first alone 50.8%: +0.5, within noise. Reach adds
  +15-22% out-of-fuel turns, spread over maps (+19% without the 2% heaviest).
- **Where reach's fuel goes:** on identical fights (a debug copy playing both models and discarding one,
  replays identical), the reach model costs ~+560 a fight in new_fight, ~+0.2% of turn fuel and +4% of 100k+ turns:
  placing (100-150 a pair; 1v1 ~140) and partial turns (10-22% dearer sims in 4+ fighter fights, as fewer fighters
  hit and fights last longer). The rest of the out-of-fuel increase follows the games' states (standoffs such as
  gen-atoll-3111201951, 204 against 2). A pair cache and a lone-fighter fast path saved nothing measurable.
- Mechanism (reach + fall first, fresh-31100..31103, `tools/replay/fight_metrics.py`, `hold_metrics.py`): deaths
  4.59 against 5.01 a game, kills 4.58 against 4.18, kill share at equal numbers 51.8%; tributed gems 837 against
  820, captures 60.6 against 59.9; hold walk-offs 1.14 against 1.16.
- Next for reach: make it cheap where it changes nothing (most fights are uniform once arrivals pass), or keep only
  its arrivals for allies (who joins) and the C&I targeting; and the strike search's `hit_given_reach` (0.25 against
  0.38 measured next-round hits in reach).

## Release candidate 269-273 (2026-11-02, astraeus 80721f68)

The stack 269-271, the fuel cuts (272) and the fall-first rule (273), without the ranged retreat change (dropped). Own
drafts, real budget, fresh suites unused before (fresh-31200..31279 generated for this; 31270-31279 left unused).
`variants/astraeus-base` is 5880baa1's bot, `variants/astraeus-stack` 66e2c518's (with the retreat change).

| Run | Suites | Games | RC win % | 95% CI | Out-of-fuel turns RC / ref |
|---|---|---|---|---|---|
| RC vs base | fresh-31200..31239 | 20,480 | **52.4** | 51.7-53.0 | 90,454 / 75,719 (+19.5%) |
| RC vs stack | fresh-31240..31259 | 10,240 | 50.2 | 49.2-51.2 | 45,881 / 44,692 (+2.7%) |
| RC vs v65 | fresh-31260..31269 | 5,120 | 78.3 | 77.2-79.4 | 21,344 / 28,728 |
| base vs v65 | fresh-31260..31269 | 5,120 | 75.9 | 74.7-77.1 | 17,596 / 30,792 |
| RC vs base, ladder | maps/ | 140 | 55.7 | 47.4-63.7 | 750 / 708 |
| RC vs base, ladder mutations | 509 mutations of the ladder maps (seeds 31300-31307) | 1,018 | 52.8 | 49.7-55.8 | 5,546 / 4,837 |

- RC vs base: 37 of 40 suites at 50%+ (lowest 47.5%). Against v65, paired on the same games: RC - base **+2.38 points
  (+1.12 to +3.65)**, flips 606 / 484 (McNemar z = 3.70).
- Out-of-fuel turns against base are broad (3,954 maps up, 2,397 down; +25.4k / -9.9k), heaviest on
  gen-fortress-3122302206 (+2,137), gen-turtle-3122608606 (+1,737) and gen-wild-3123506218 (+1,179). The stack 269-272
  already ran +18% against base (EXPERIMENTS "Stack 269-272"); the RC is +2.7% over the stack.
- Mechanism, fresh-31200..31203 (2,048 games, `fight_metrics.py`, `hold_metrics.py`), RC against base: deaths 4.91
  against 5.19 a game (to champions 4.44 / 4.70), kills 4.70 against 4.44, kill share at equal numbers 51.1%; tributed
  gems 837 against 824, captures 64.7 against 63.8, captured gems 899 against 882; hold walk-offs 1.15 against 2.19,
  pressured holds paid 81% against 69%; A-B-A flips 2.98 per 100 champion-rounds in both; out-of-fuel turns 8,731
  against 7,918.

## Fuel

Where fuel goes: the latest profiles below (after CHANGES 107-108 and 109-110, and CHANGES 99's). Every out-of-fuel
turn runs out inside `decide`, mostly on fight maps (8-10 champion brawls; Heart of Ruin, then Ren, Varg, Ryth). Who
computes danger, and where the models overlap: [DANGER-MODELS.md](hyperion/DANGER-MODELS.md).

- Stack fuel (2026-11-01, CHANGES 272; the stack 269-272 against 5880baa1's bot). Census copies (instrument.py
  `--fine` plus scopes on the new functions, and a per-game total of every scope; fight and oof sets at 100M against a
  stack copy): stack 46.1k a turn against 44.2k on the fight set (heavy turns 91.6k against 90.6k, 12% more of them),
  54.9k against 53.2k on oof. Pure new code on the fight set, a turn: keep_out ~380 (in_pack_zone per tile), guard
  bookkeeping ~170, retreat quotes +~130, holds' turns_to_kill_idle ~70, HealGate (Willow) up to 20-40k on a heavy
  turn, standing_damage ~20, partner_bound ~6; keep_out set a tile in under 1% of calls, and the work guard's
  step_guard returned null in 0.23 of 0.24 calls a turn. Play, not code: the step guard is placed as often (no
  duplicate placings in either bot) but costs ~17% more a placing; stands, lethal checks and the strike search cost
  more a call. At the real budget the fight set's first out-of-fuel turns rose 253 -> 350, keep_out present in 15% of
  them (ran out inside it in ~7%). Kept (CHANGES 272): keep_out's batched pack test with a superset check
  (keep_out ~380 -> ~170 a turn), HealGate's per-ally damage memo; also standing_at's memo, which went with the
  dropped retreat change. Matched census (same games):
  -229 a turn, -1.1k a heavy turn on the fight set. 100M: 234/234 identical, total -0.05 to -0.46% by set. Real
  budget benches (stack -> cut): fight 395 -> 382, oof 977 -> 937, wide 421 -> 686 (gen-chambers-102206117 a and b
  diverged into runaways, +227). A/B own drafts, fresh-30900..30919: 50.4% of 10,240 (49.4-51.3), out-of-fuel turns
  41,631 against 44,058 (-5.5%). Dropped after a read-only audit: HealGate answering `gain >= least_` from bounds
  (gain >= amount, or >= amount x 7/8 when no ally misses a full heal) without the damage loop; skipping the loop can
  skip the round's first Reach build, which freezes ally positions and enemy wards for the round (behaviour change).
  Open: the remaining ~1k a turn is the hold rule's contact; cheaper step-guard placings and stands are general fuel
  work.
- Fuel campaign 3, merge round 4, the last (2026-11-01, against `astraeus-fc3-m3` at 100M and fc3b in the A/B; notes
  and the campaign summary in hyperion/fuel-campaign-3/NOTES.md, `MAIN/replays/fuel/fc3/m4-*.json`). **Kept, all of
  fc3-camps and fc3-sim (CHANGES 268)**: min_camp_damage's clear order kept when no comparison with a moved member
  flips; access_fire kept on its inputs, with per-tile reach masks; play_quiet in locals and a one-fighter act. 100M:
  all replays identical; total -0.17 / -0.24 / -0.36 / -0.07 / -0.10 / -0.02% (wide / oof / mg / q / big / fs),
  fight set -0.20%, camp-heavy set -2.93% (p99 -6.4%). Real-budget benches (m3 -> m4, runaway games swing them): OOF
  517 -> 452, 716 -> 1031, 237 -> 539, 1800 -> 2530, 122 -> 151, fs 1627 -> 1653, fs2 4487 -> 4472, camp-heavy 1482 ->
  694, fight 401 -> 385; games under 150 OOF fell on oof, mg and q. A/B (fresh-11000..11019, own drafts, real budget,
  10,240 games): camps alone (m4c) 50.7% (49.8-51.7), OOF 37,799 against 56,233; + sim (m4) 50.8% (49.8-51.7), OOF
  37,908 against 55,825 (level with m4c: kept). m4 rounds 1 / 2-10 / 11-60 / 61-300 / 300+ 5,316 / 4,047 / 6,267 /
  7,533 / 14,745; runs <10 / 10-49 / 50+ 27,302 / 8,940 / 1,666. **Campaign**: mirror 54,610 -> 37,908 (-30.6%;
  target -50%). Confirmation on unused suites fresh-11100..11109 (5,120 games): 50.6% (49.2-52.0), OOF 18,475
  against fc3b's 25,796 (-28.4%; round 1 2,595 / 5,014). Fuel a play turn in the A/B (real budget): mean 50,004 ->
  48,022, p90 86,250 -> 85,950.
- Fuel campaign 3, merge round 3 (2026-11-01, against `astraeus-fc3-m2f` at 100M and fc3b in the A/B; notes in
  hyperion/fuel-campaign-3/NOTES.md "Merge round 3", `MAIN/replays/fuel/fc3/m3-*.json`). **Kept, all of fc3-audit
  (CHANGES 267)**: emblem reads keyed on max health / Strength / Focus (Prism's gems), kept recall from read state,
  camp stun read first, camp-tile view by tile. 100M: all replays identical; total -1.11 / -1.46 / -1.56 / -0.91 /
  -0.65 / -0.53% (wide / oof / mg / q / big / fs), round 1 +0.1-0.2%. Real-budget benches (m2f -> m3): OOF 567 -> 517,
  665 -> 716, 233 -> 237, 1840 -> 1800, 105 -> 122, fs 1673 -> 1627, fs2 4522 -> 4487. A/B (fresh-11000..11019, own
  drafts, real budget, 10,240 games): 50.5% (49.5-51.4), OOF 38,820 against 56,943 (mirror 54,610, m2f 40,457);
  rounds 1 / 2-10 / 11-60 / 61-300 / 300+ 5,301 / 4,013 / 6,108 / 7,717 / 15,681; runs <10 / 10-49 / 50+ 27,003 /
  9,987 / 1,830 (one topology runaway, gen-topo-shortcut-1100206938-b, 557). **Dropped, fc3-fight (0a4c638b)**: the
  strike search pricing maybe-guarded tiles before resolving the deferred guard. Identical on six sets and a 30-game
  fight set but not exact: when the guard was owed but left unresolved (the tile bound-stopped) and the 10-query cap
  then binds, the capped fallback excludes guarded tiles the old code priced. Gain -0.05% on the fight set, ~0
  elsewhere: not A/B'd.
- Fuel campaign 3, merge round 2 (2026-11-01, against `astraeus-fc3-m1` at 100M and fc3b in the A/B; notes in
  hyperion/fuel-campaign-3/NOTES.md "Merge round 2", `MAIN/replays/fuel/fc3/m2-*.json`, `m2f-*.json`). **Kept, all of
  fc3-scale and fc3-loops (CHANGES 266)**: farm pre-facts and banking upper bounds in f32x4 lanes, stop tables,
  static_camps lanes, kite's station cache, fp2 reusing fp1's failure. 100M: all replays identical; total -0.53 /
  -0.95 / -1.02 / -1.98 / -1.28 / -18.4% (wide / oof / mg / q / big / fuel-stress fs). Real-budget benches (m1 ->
  m2f): OOF 1273 -> 567, 860 -> 665, 348 -> 233, 3747 -> 1840, 127 -> 105, fs 2367 -> 1673, fs2 (80 games) 6314 ->
  4522. A/B (fresh-11000..11019, own drafts, real budget, 10,240 games): m2f 50.5% (49.5-51.4), OOF 40,457 against
  56,707 (mirror 54,610, m1 43,359); rounds 1 / 2-10 / 11-60 / 61-300 / 300+ 5,223 / 4,157 / 6,500 / 7,945 / 16,632;
  runs <10 / 10-49 / 50+ 28,412 / 10,511 / 1,534. Without fp2's reuse (2affa588), m2: 50.4% (49.5-51.4), OOF 41,943
  against 57,280, runs of 50+ 2,468: the reuse is -1,486 (the reference's own swing between runs ~600), kept.
- Fuel campaign 3, merge round 1 (2026-11-01, against frozen `astraeus-fc3b` = 4a7c25f6; notes in
  hyperion/fuel-campaign-3/NOTES.md, `MAIN/replays/fuel/fc3/m1-*.json`, `m1r-*` none). **Kept, fc3-farm (CHANGES
  265)**: crew-rate bounds for strong and claimed groups, `camp_in_reach` by dilation, first-turn `recall_line` foe
  skip. 100M: all 204 replays identical; total -2.96 / -4.51 / -3.92 / -8.25 / -3.76% (wide / oof / mg / q / big),
  over 100k 5694 -> 3989, 20818 -> 16036, 9415 -> 7318, 43157 -> 30046, 6866 -> 4463; round 1 mean -15 to -31%.
  Real-budget benches: OOF 595 -> 1273, 894 -> 860, 386 -> 348, 2678 -> 3747, 151 -> 127 (wide and q's rises are
  three games in two-turn loops: 01boss-battle-b, gen-topo-island-986606600-b, gen-topo-shortcut-989706930-a);
  round-1 turns at the 200k cap 43 -> 21, 104 -> 72, 49 -> 36, 85 -> 63, 41 -> 34; farm-partial-evaluation -16 to
  -24%. A/B (fresh-11000..11019, own drafts, real budget, 10,240 games): 50.5% (49.6-51.5), OOF 43,359 against
  55,116 (mirror 54,610); rounds 1 / 2-10 / 11-60 / 61-300 / 300+ 5,668 / 3,849 / 6,886 / 9,034 / 17,922 against
  10,457 / 5,949 / 7,793 / 9,831 / 21,086; runs <10 / 10-49 / 50+ 28,681 / 12,323 / 2,355 against 36,771 / 13,783 /
  4,562. **Dropped, fc3-routes (afea1852)**: lower-bound fields over terrain and live camps, made in the turn-end
  queue, to skip failed route searches past their cap. Exact in decisions; 100M +0.04 to +0.15% on four sets, -0.30%
  on q (worker's numbers). On top of fc3-farm, same A/B: 50.6% (49.6-51.5), OOF 44,403 against 55,238 (+2.4% over
  fc3-farm alone; runs of 50+ 2,963 against fc3-farm's 2,355). Also level in the worker's own 8k A/B (45,408 / 45,163).
- Draft turn: split maps and fall-custom giant (CHANGES 244-245; 2026-10-31, against the split-maps commit
  0ad3e86): release `firstturn.py` on the 73 maps that ran out, the 200 heaviest split maps, 200 random maps and
  giant, 880 team-drafts: out of fuel before the pick 68 -> 0. Start-up plus model draft on split maps: before, the
  200 heaviest median 8.9M, max 10.0M of those that finished; with 244 median 5.5M, max 8.25M; with 245 median
  4.3M, max 7.0M. Others median 2.3M -> 1.7M; giant out of fuel -> 8.25M. Lost:
  relaxing each tile's 8 neighbours from a precomputed mask by bit iteration (+0.2M on 9178: the unrolled test is
  cheaper), a branchless neighbour test, offsets spelled out in clearance's BFS (both dearer), and stopping Dial
  once S and the altars are known (exact, but ~10% of a split map's field lies beyond). Fuel was counted offline
  with a wasmtime harness (the bot's compiler and flags), within 0.1% of in-game marks.

- Fuel round 1 (CHANGES 214; 2026-10-29, against frozen 8ec2c4d, `replays/fuel/orch/m1-*.json`): fights that settle
  on our fall end there, `track` shares a lineage's growth whatever its dating, `fix` skips rewriting unchanged
  boards. 100M, wide set (test drafts): 52/52 identical, mean 50923 -> 50894, p90 86081 -> 86068, p99 106866 ->
  106316, over 100k 3615 -> 3551, round 1 197299 -> 197310, rounds 2-10 mean 90143 -> 89092 and p90 99365 -> 94461;
  total -0.06% (28k turns cheaper, 231k dearer by a median 16). OOF set (own drafts, vs 8ec2c4d): 32/32 identical, mean
  62520 -> 62376, p90 88486 -> 88340, p99 147280 -> 145736, over 100k 11851 -> 11109, round 1 212725 -> 212750,
  rounds 2-10 p90 104026 -> 95318; total -0.23%. Real budget: wide OOF 1247 -> 1047, shortcuts 18883 -> 16627
  (step-guard-entry 4770 -> 4020, prey-cut-short 2465 -> 1887); OOF set OOF 8339 -> 9522 (1719 -> 1996 without the
  shared-gems pair; every game diverged, several ran longer), shortcuts 46248 -> 48787. A/B (1676, ladder +
  fresh-82801/2/3, own drafts): 49.8%, out-of-fuel turns 15809 vs 19568, without the gen-shared-gems-8280101604 /
  8280201605 pair 8342 vs 8760. Kept.
- Fuel round 1, routes past a deferred step guard (CHANGES 215; 2026-10-29, `replays/fuel/orch/m1b-*.json`): with
  CHANGES 214, against frozen 8ec2c4d at 100M. Wide: 52/52 identical, mean 50923 -> 50865, p90 86081 -> 86056, p99
  106866 -> 106166, over 100k 3615 -> 3531, round 1 197299 -> 197296, rounds 2-10 p90 99365 -> 94434; total -0.11%
  (-0.06% over 214). OOF set: 32/32 identical, mean 62520 -> 62134, p90 88486 -> 88307, p99 147280 -> 135669, over
  100k 11851 -> 10646, rounds 2-10 p90 104026 -> 95256; total -0.62% (-0.39% over 214). Real budget: wide OOF 1247 ->
  1191, shortcuts 18883 -> 15816 (step-guard-entry 4770 -> 3564); OOF set OOF 8339 -> 9472 (1719 -> 1749 without the
  shared-gems pair), shortcuts 46248 -> 45055. A/B against astraeus-m1 (214 alone; 1676, own drafts): 50.6%,
  out-of-fuel turns 18590 vs 18754, 8104 vs 7970 without the pair. The 100M tail gain did not show as fewer OOF
  turns. The same m1 build read 8342 (without the pair) in its own A/B against 8ec2c4d, so a different opponent moves
  these counts by ~5%.
- Fuel round 2 (CHANGES 216-217; 2026-10-29, `replays/fuel/orch/m2a-*.json`, `m2-*.json`): exact end-of-turn cuts
  (`may_escape`'s camps only once an enemy hits, comms slot urgency in `send`, the ward's bush test first) and
  step_guard's first union without per-tile keys (216, frozen m2a); a turn after one that ran out finishes its
  decision late (217, frozen m2). 100M against frozen 8ec2c4d, m2a: wide 52/52 identical, mean 50923 -> 50705, p90
  86081 -> 86033, p99 106866 -> 106020, over 100k 3615 -> 3481, round 1 197299 -> 197269, rounds 2-10 mean 90143 ->
  89081 and p90 99365 -> 94440; total -0.43% (-0.31% over m1b). OOF set: 32/32 identical, mean 62520 -> 61839, p90
  88486 -> 88223, p99 147280 -> 135655, over 100k 11851 -> 10492, round 1 212725 -> 212734, rounds 2-10 p90 104026 ->
  95035; total -1.09% (-0.47% over m1b). m2 at 100M: identical to m2a on both sets, +0.05% fuel. Real budget (base /
  m1b / m2a / m2): wide OOF 1247 / 1191 / 970 / 666, shortcuts 18883 / 15816 / 14237 / 12688; OOF set OOF 8339 /
  9472 / 13784 / 2423 (shared-gems maps 7138 / 8331 / 12611 / 1245, the rest 1201 / 1141 / 1173 / 1178), shortcuts
  46248 / 45055 / 44853 / 35376. The shared-gems counts are bimodal: 216 is exact, and m2a's 13784 there is the
  livelocks running longer after real-budget divergence. A/B m2 against m1b (1676, ladder + fresh-82801/2/3, own
  drafts): 49.6% (47.3-52.0);
  out-of-fuel turns 7815 vs 9192, 6777 vs 7609 without the gen-shared-gems maps; by round 1 / 2-10 / 11-60 / 61-300 /
  300+: 607 / 516 / 1040 / 1626 / 4026 vs 594 / 676 / 1339 / 1904 / 4679; in champion-games of 50+ run-outs 587 vs
  1434. A late turn's OOF line names its last phase (queue 1941 vs 81), not where it ran out; 78 late tails ran out
  again (10 before). Kept.
- Fuel round 3 (CHANGES 218; 2026-10-29, `replays/fuel/orch/m3-*.json`, frozen m3): `find_members` boxes per group
  on first use and a wake check bounded by the box; Reach builds read camps only within the tile sets' radius (no
  spot pool, bounds per query); `camp_exit_rounds` without its per-tile camp test; `in_pack_zone` by the members
  near the tile; step_guard's bound pass by per-foe cell masks; route() keeps the step guard's cover for the round.
  100M against frozen 8ec2c4d (m2 in brackets): wide 52/52 identical, mean 50923 -> 50594 (50731), p90 86081 ->
  86002 (86045), p99 106866 -> 104910 (106049), over 100k 3615 -> 3300 (3484), round 1 197299 -> 197227 (197295),
  rounds 2-10 mean 90143 -> 89085 (89079) and p90 99365 -> 94450 (94469); total -0.64% (-0.27% over m2). OOF set
  32/32 identical, mean 62520 -> 61071 (61866), p90 88486 -> 87720 (88243), p99 147280 -> 133461 (135680), max
  430932 -> 393305, over 100k 11851 -> 9061 (10500), round 1 212725 -> 212700 (212760), rounds 2-10 mean 90857 ->
  89894 (89913) and p90 104026 -> 95053 (95060); total -2.31% (-1.28% over m2). Real budget (base / m2 / m3): OOF
  set OOF 8339 / 2423 / 1948 (shared-gems maps 7138 / 1245 / 1006, the rest 1201 / 1178 / 942), shortcuts 46248 /
  35376 / 31944 (step-guard-entry 16703 / 13585 / 12224); wide OOF 1247 / 666 / 751, shortcuts 18883 / 12688 /
  14324 (small samples whose games diverge). A/B m3 against m2 (1676, ladder + fresh-82801/2/3, own drafts): 50.3%
  (47.9-52.7); out-of-fuel turns 6775 vs 7511, 5945 vs 6597 without the gen-shared-gems maps; by round 1 / 2-10 /
  11-60 / 61-300 / 300+: 602 / 510 / 925 / 1342 / 3396 vs 607 / 517 / 1015 / 1615 / 3757; in champion-games of 50+
  run-outs 493 vs 386. Kept.
- Fuel round 4 (CHANGES 219-220; 2026-10-29, `replays/fuel/orch/m4-*.json`, frozen m4): round-1 world construction
  (camp members copied from the layout words whole, per-type sums from a table, groups in one resize, camp healths in
  one pass, crossings sharing their shifts, `square_dilate` without its copies); the fight sim's plain path takes
  arrivals and the quiet path takes Ren, and `their_cap` sums casts and Ren only when the basic attacks fall short.
  100M against frozen 8ec2c4d (m3 in brackets): wide 52/52 identical, mean 50923 -> 50530 (50594), p90 86081 -> 85995
  (86002), p99 106866 -> 104450 (104910), over 100k 3615 -> 3220 (3300), round 1 mean 197299 -> 195763 (197227), p90
  211094 -> 203033 (210961), max 282913 -> 268295 (282831), rounds 2-10 mean 90143 -> 89062 (89085) and p90 99365 ->
  94360 (94450); total -0.77% (-0.13% over m3). OOF set 32/32 identical, mean 62520 -> 60973 (61071), p90 88486 ->
  87678 (87720), p99 147280 -> 132459 (133461), over 100k 11851 -> 8827 (9061), round 1 mean 212725 -> 209980
  (212700), p90 253016 -> 246106 (253022), max 423294 -> 412168 (423218), rounds 2-10 mean 90857 -> 89832 (89893) and
  p90 104026 -> 94837 (95053); total -2.47% (-0.16% over m3). Against m3 run the same way: OOF set on test drafts (Ren,
  Heart of Ruin, Varg, Ryth) 32/32 identical, -0.14%, p99 116788 -> 115992, over 100k 5066 -> 4920, round 1 mean
  213523 -> 210354; many-group set (farmland, labyrinth, pillars, close-spawns, dense-camps, three-lane from
  fresh-82801..3; own drafts) 12/12 identical, round 1 mean 330501 -> 311088, p90 371423 -> 355183, max 417225 ->
  400985, play -0.13%. Real budget (base / m3 / m4): OOF set OOF 8339 / 1948 / 1732 (shared-gems maps 7138 / 1006 /
  802, the rest 1201 / 942 / 930), shortcuts 46248 / 31944 / 30430 (step-guard-entry 16703 / 12224 / 12205); wide
  OOF 1247 / 751 / 710, shortcuts 18883 / 14324 / 14239. A/B m4 against m3 (1676, ladder + fresh-82801/2/3, own
  drafts): 50.7% (48.3-53.1); out-of-fuel turns 6703 vs 6805, 5597 vs 5859 without the gen-shared-gems maps; by round
  1 / 2-10 / 11-60 / 61-300 / 300+: 483 / 447 / 849 / 1323 / 3601 vs 603 / 510 / 826 / 1433 / 3433; in
  champion-games of 50+ run-outs 670 vs 531. Kept.
- Fuel round 5 (CHANGES 221-222; 2026-10-29, `replays/fuel/orch/m5-*.json`, frozen m5 = 221-222, m5a = 221):
  `rank_turns` re-ranks only a stale team, allies compared above the payload bits (221); an idle strike search
  (no enemy within reach of a hit, landing or unit cast, nothing else to offer) skips read/grow/price and returns
  whether `read()` takes any enemy (222). 100M, m5 against m4 (against 8ec2c4d in brackets): wide 52/52 identical,
  mean 50530 -> 50073 (50923), p90 85995 -> 85923 (86081), p99 104450 -> 102412 (106866), over 100k 3220 -> 2959
  (3615), round 1 mean 195763 -> 195687; total -0.90% (-1.67%). OOF set 32/32 identical, mean 60973 -> 60209
  (62520), p90 87678 -> 87533 (88486), p99 132459 -> 130872 (147280), over 100k 8827 -> 8261 (11851); total -1.25%
  (-3.69%). OOF set on test drafts 32/32 identical, -1.11%, p99 115992 -> 114288, over 100k 4920 -> 4606. Real
  budget (base / m4 / m5): OOF set OOF 8339 / 1732 / 1700 (shared-gems maps 7138 / 802 / 785, the rest 1201 / 930 /
  915), shortcuts 46248 / 30430 / 31253 (step-guard-entry 16703 / 12205 / 13328, prey-cut-short 5663 / 6306 / 5530);
  wide OOF 1247 / 710 / 744, shortcuts 18883 / 14239 / 12545. A/B m5 against m4 (1676, ladder + fresh-82801/2/3, own
  drafts): 50.0% (47.6-52.4); out-of-fuel turns 7053 vs 6657 (+5.9%), 5881 vs 5726 without the gen-shared-gems maps;
  by round 1 / 2-10 / 11-60 / 61-300 / 300+: 473 / 420 / 816 / 1410 / 3934 vs 482 / 445 / 865 / 1342 / 3523; in
  champion-games of 50+ run-outs 832 vs 527. The rise is spread over maps (02the-pack +99, the three shared-gems
  maps +251, gen-serpentine-8280104501 +61; 01elk-arena -34). 222: exact at 100M, but more real-budget OOF turns:
  reverted (the worker's own real-budget OOF set run of 222 had 1732 -> 2134; m5's above, 1700). A/B
  m5a (221 alone) against m4, the same way: 50.4% (48.0-52.7); out-of-fuel turns 6453 vs 6658, 5543 vs 5718
  without the gen-shared-gems maps; by round 473 / 422 / 811 / 1315 / 3432 vs 483 / 448 / 867 / 1291 / 3569; 50+
  run-outs 486 vs 427. 221 kept; main is m5a.
- Fuel round 6 (final) (CHANGES 223-226; 2026-10-29, `replays/fuel/orch/m6-*.json`, reference `m5a-*.json` rerun
  fresh, frozen m6): `make_centre` one uncapped field search (223); a failed route search's labels reused (224);
  `read_geometry`'s dash blockers only on a dashing turn and the unseen-threat pass without visible Reach builds
  (225); the farm loop's banking stop in an out-of-line instance (226); plus `probe-padding` (tools only). Each was
  exact at 100M in its worker's runs (223: maze set 12/12, labyrinth first-approach turns -20..-25k; 224: maze over
  100k -2.4%; 225: over 100k -1..-1.3%; 226: many-group over 100k -4.7%, wide/OOF total +0.01-0.02%). 100M, m6
  against m5a (against base 8ec2c4d in brackets): wide 52/52 identical, mean 50238 -> 50220 (50923), p90 85970 ->
  85955 (86081), p99 104276 -> 103911 (106866), over 100k 3198 -> 3145 (3615), round 1 mean 195687 -> 195566
  (197299); total -0.04% (-1.38%). OOF set 32/32 identical, mean 60533 -> 60491 (62520), p90 87667 -> 87638
  (88486), p99 132391 -> 131618 (147280), over 100k 8811 -> 8687 (11851), round 1 mean 209736 -> 209446 (212725);
  total -0.07% (-3.24%). A/B m6 against m5a (1676, ladder + fresh-82801/2/3,
  own drafts, real budget): 50.3% (47.9-52.7); out-of-fuel turns 6069 vs 6366 (-4.7%), 5393 vs 5693 without the
  gen-shared-gems maps; by round 1 / 2-10 / 11-60 / 61-300 / 300+: 475 / 365 / 802 / 1273 / 3154 vs 473 / 428 /
  810 / 1374 / 3281; in champion-games of 50+ run-outs 256 vs 302. Unlike 222, these exact cuts did not raise
  real-budget run-outs. All kept; main is m6.
  Campaign headline (CHANGES 214-226, against a fixed opponent): m6 and 8ec2c4d each against hecate, test drafts on
  both sides, 1676 games (`orch-base-vs-hecate`, `orch-m6-vs-hecate`): out-of-fuel turns 11101 -> 7325 (-34%;
  hecate 2848 / 2695), win 89.9% -> 90.2%; by round 1 / 2-10 / 11-60 / 61-300 / 300+: 528 / 680 / 952 / 1486 / 7455
  -> 390 / 307 / 685 / 1175 / 4768; in champion-games of 50+ run-outs 2129 -> 591. Real-budget bench, 8ec2c4d -> m6:
  wide out-of-fuel 1247 -> 692 and shortcuts 18883 -> 12782; OOF set 8339 -> 1845 and 46248 -> 31934. Exact cuts
  must still pass the A/B (222).
- Fuel round 7 (CHANGES 227-228; 2026-10-29, `replays/fuel/orch/m7-*.json`, frozen m7): `rank_turns` copies passes
  0/1 into 2/3 when every key equals its next (227); a camp settled last round reuses its in-view member mask while
  `camp_view_` and its version hold, and `CampBelief` is no longer zeroed before its initialisers (228). 100M, m7
  against m6: wide 52/52 identical, mean 50220 -> 50043, p90 85955 -> 85931, p99 103911 -> 103647, over 100k 3145 ->
  3121, round 1 mean 195566 -> 195584; total -0.35%. OOF set 32/32 identical, mean 60491 -> 60209, p90 87638 ->
  87603, p99 131618 -> 131315, over 100k 8687 -> 8557, round 1 mean 209446 -> 209466; total -0.47%.
  A/B m7 against m6 (1676, ladder + fresh-82801/2/3, own drafts, real budget, `orch-m7`): 50.1% (47.7-52.5);
  out-of-fuel turns 6098 vs 6157 (-1.0%), 5224 vs 5254 without the gen-shared-gems maps; by round 1 / 2-10 / 11-60 /
  61-300 / 300+: 478 / 360 / 813 / 1258 / 3189 vs 475 / 369 / 826 / 1314 / 3173; in champion-games of 50+ run-outs
  337 vs 334. Both kept; main is m7.
  The campaign headline above (round 6) was measured on m6, not m7.
- Fuel phase 2 (2026-10-29, on m7; CHANGES 229-230; findings and dropped attempts in
  `hyperion/fuel-campaign/OPEN-ITEMS.md`). Five investigations:
  - Sims and the step guard (`tools/fuel/simprof`): heavy turns run ~2.3 distinct fights (stand's own 37% of sim fuel,
    guard U1 18%, chase 31%, guard tiles 10%); identical sims within a turn are 0.6-0.9% and same-roster fights diverge
    at half-turn 0, so shared prefixes and per-side tapes don't pay. Two exact early exits for U1 ("we wipe them before
    they fell us"; re-running checks as the horizon shrinks) were identical but +0.27% / +0.05%. Left: F4's event mask
    in non-plain `act` (the only lever over 1k a heavy turn), a resumable fight memo (<1%).
  - Why 222 raised OOF turns: idle-skip turns almost never ran out (62 of 148k); the extra run-outs were all in streaks
    (champion-games of 10+: +784, CI +281..+1341) on non-idle turns. Not freed fuel feeding gates (a variant hiding it
    from every `fuel_ok` changed nothing) nor `step_guard_costliest`'s decay. Measured: the `read()` restructure made
    every real search +365 dearer, +667 after an idle turn (cold per-tile caches), so the cut moved cost onto fight turns,
    the only ones that run out. Judge exact cuts also by the turns they make dearer. A rebuilt skip (idle test inside the
    original `read()`, +140 overhead) is identical at 100M but not A/B'd.
  - Farm loop: a clearing-aware stop (classes per map, cached full-health flags) cut heads 71 -> 42 a call and many-group
    fuel -1.3% but cost wide +0.5% / OOF +0.25% from the flattened `farm_turn`'s codegen (+0.54% with the stop present
    but never run); real many-group OOF 109 -> 183 (12 games). Banking bounds cut bodies 83 -> 13 but cost as much as the
    cached bodies. The cost is the ~10 near bodies a call (~1.6k each).
  - Round 1 on ~100-group maps: no exact cut closes ~110k; 230 lets the decision finish in round 2.
  - Small leads: 229 kept; windowed tracking dilation made exact (padding in source words caused the old mismatches)
    but +1.1% (the kernel ~400 a call + 180 a chunk a step); kite's `know_failure` fires 1-4 times a game.
  A/B checks, own drafts, ladder + gen + gen-s1 (1164): m7 against 3938c0f (CHANGES 198) 50.8% (47.9-53.6), out-of-fuel
  turns 3576 vs 4635; 8ec2c4d (before the campaign) against 3938c0f 50.4% (47.6-53.3), 4721 vs 4627. So against a fixed
  reference the campaign cut out-of-fuel turns ~24% at a level win rate. Ladder alone read 42.1% (m7) vs 49.3%
  (8ec2c4d), 140 games each (~1.2 SE): unconfirmed; check on a fresh ladder-mutation suite.
- Farm loop, a per-group suffix stop on recall-out turns (2026-10-30, astraeus 3e849d5, dropped). The lead: recall-out
  farm turns cost 25.2k against 14.7k otherwise, blamed on `FarmMemo::Most::spawn_near` (one group near spawn keeps
  the suffix bound near the recall channel). Measured (debug copy, wide set, non-banking loops with the stop): the
  tightest exact suffix bound of that form (suffix max of each group's own bound: its own worth, distance from here and
  via-recall trip) would cut 1.9 of 17.2 iterations a recall-out turn (0.5 of 7.8 that reach the facts), ~850 fuel of
  a ~12.4k loop; plain turns 1.7 of 14.2. Most cut iterations are ones the group's own rated prune already drops
  for about what the bound costs. Segments a turn, recall-out vs plain (both reach the loop): farm_recall 1247 vs 6,
  loop 12357 vs 10575, after the loop 7024 vs 4734, total 24.4k vs 20.2k, so most of the lead's 10.4k gap is the
  comparison set (plain includes early returns). Implemented lazily (refine the aggregate stop down past positions
  whose own bound fails, no n-group pass): 52/52 identical, total +0.09% (+0.06% with `rate` inlined). Dropped.
- Small "pure" refactors near hot accessors need the bench (2026-10-28 audit, world.cc): moving the `make_*foot`
  bodies into a shared helper cost about 32 fuel a turn for no visible reason (inlining around `foot()` and its
  callers).
- bot.cc split into files and folders (CHANGES 200; 2026-10-28, against 3938c0f, `replays/fuel/split/`): wide set,
  test drafts, 52/52 identical replays at 100M and at the real budget, total fuel equal to the unit, no turn cheaper
  or dearer. Release object, compared function by function (`llvm-objdump -d -r`, calls and addresses as symbols):
  same 1199 functions and 493185 instructions; only two exit-time global destructors swapped numbers. Two release
  builds of the *same* source are not identical: one `try_table` in `bank_gems` / `farm_turn`'s throw_if_stale path
  is placed differently from build to build, same instructions, so judge codegen by function, not by wasm bytes.
- Fuel audits 1-3, the accepted items (CHANGES 187-189; 2026-10-27, astraeus against dfaf546). Release builds
  (`cambc build/run --release`, as the ladder), turn-end queue on, 100M, against a hecate copy: wide set (52, test
  drafts), heavy set (the farm audit's 12 maps with 22-106 groups plus 00ambush, 00lanes, 01hooks, 00contest; own
  drafts, 32) and the fight audit's 12 fight maps (own drafts, 24). All identical, every step. 187-189 against dfaf546:

  | Set | Rounds | Mean | p90 | p99 | Turns over 100k |
  |---|---|---|---|---|---|
  | heavy | 2+ | 61.6k -> 61.3k (-0.5%) | 88.5k -> 88.3k | 129.2k -> 123.0k | 5197 -> 4330 |
  | heavy | 1 | 284.7k -> 269.6k (-5.3%) | 378.9k -> 362.9k | 442.4k -> 410.9k | over 200k 125 -> 117 |
  | heavy | 2-10 | 106.4k -> 98.5k (-7.5%) | 144.3k -> 126.7k | 238.0k -> 190.4k | 536 -> 390 |
  | heavy | 61+ | 59.4k -> 59.2k (-0.3%) | 87.9k -> 87.8k | 122.8k -> 118.7k | 3852 -> 3430 |
  | wide | 2+ | 51.5k -> 51.5k (+0.1%) | 86.1k -> 86.1k | 114.6k -> 114.8k | 5651 -> 5577 |
  | wide | 1 | 198.9k -> 197.1k (-0.9%) | 215.5k -> 208.3k | 257.8k -> 250.7k | over 200k 65 -> 51 |
  | wide | 2-10 | 90.9k -> 90.0k (-0.9%) | 103.9k -> 99.6k | 165.9k -> 161.1k | 252 -> 210 |
  | wide | 61+ | 50.0k -> 50.1k (+0.2%) | 85.6k -> 85.6k | 114.0k -> 113.9k | 5126 -> 5093 |

  Real budget, fuel2-tip2 (own drafts, 1164): 50.9% (48.0-53.7), out-of-fuel turns 3836 vs 4822 (round 1 277 vs 448,
  rounds 2-10 325 vs 483, 61+ 2849 vs 3460). The first run (fuel2-tip, 50.9%, 3900 vs 4842) had the queue's step warm-up
  priced at 60 a group for two kinds: 53 queue run-outs vs 31, 30 in rounds 2-10; a check a kind at 250 a group fixed it.
  Lost or not kept:
  - F2a, `walk_allies_in`'s walks in a table kept for the Safety's life (per ally, then per ally and enemy): identical
    but +0.03% on the fight set and +0.02-0.07% elsewhere, dearer on almost every turn. Dropped.
  - 187's check skipped for groups whose steps are already read: rounds 61+ dearer (wide +0.43% against +0.25%).
  - 188 with every step lazy: round 1 -13k but round 2 +2.4k (group hops read every group's ally steps on round 2).
  The farm audit's P1+P4 alone, as the review measured it (`replays/ab/review-p14-vs-base`): 52.2% of 1164, 4680 vs
  4975.
  The unity build (CHANGES 190) on top: identical on all three sets, rounds 2+ mean -0.28% / -0.27% / -0.25%
  (wide / heavy / fight), round 1 -0.1 to -0.2%; the arch audit had -0.37% total with the queue off.
- Gate firings and CHANGES 174-177 (2026-10-26, astraeus against 9beb148; `replays/fuel/gates/`, wide bench and a
  heavy set of 8 maps with 28-100 groups, test drafts). Per champion-turn in the cs-price2 A/B (1164 games):
  farm-partial-evaluation fired alone on 37k of its 54k turns (its own reserve: `ample` ~97k on 100x100 never
  passes, then ~25-30k a group), step-guard alone on 18k (a sticky `costliest`); turn-order, ward and comms mostly
  ride with them. Merged, 100M: wide 52/52 and heavy 16/16 identical, mean +0.4% and -1.2% (heavy p50 -2.3%). Real
  budget: heavy out-of-fuel play turns 1579 -> 294, farm-partial-evaluation 25.7k -> 20.9k, step-guard 2310 ->
  1156; wide 985 -> 1164, but without the two gen-chambers maps 297 -> 306 (gen-chambers-102206117 507 -> 673; 456
  with 176 alone). Lost: prey gating only new sims (+39% out-of-fuel, all gen-chambers); the farm bound only from 24
  groups (no worst-case gain).
  Full A/Bs against 9beb148, own drafts, 1164 games: 174-177 50.6% (47.7-53.5; ladder 51.4, gen 51.4, gen-s1
  49.6), out-of-fuel turns 5446 vs 4710 (+16%, all in `decide`, on fight maps: treasure-box, arena, elk-arena,
  open-field; dense-camps 127 -> 98); without 176's prey part 49.1%, 5189 vs 4944 (+5%); without 176 (kept)
  50.8% (47.9-53.6; ladder 54.3, gen 52.0, gen-s1 48.6), 4370 vs 4578 (-4.5%). The step-guard and prey gates
  brake fight turns: firing less, the fight code runs out. 177 took comms-stale-vision 36.4k -> 6.6k.
- Warm-up readers and the end-of-turn queue (CHANGES 166-168; 2026-10-26, wide bench, test drafts, 100M,
  `replays/fuel/wq/`). The check: a copy skipping `prepare_next_turn`, `warm_reach`, the warm-up and the table queue
  (later the one queue) against the bot. Before 2/52 identical; spawn-field readers 23/52, centre fields 24/52, group
  hops 24/52, ward clusters 52/52. The divergences were found by diffing the debug stdout of the two runs (fuel
  fields masked; NUL padding stripped), not the replays. Dropped: group hops made at once on first ask, in round 1
  (round 1 +12.5k mean, 00ambush +90k), then on the second turn (01islands 124-156k); the turn-start ward growing its
  clusters (gen-city 35-95k). 166 alone against f9d2e26b: 52.3% of 1164 but out-of-fuel turns 4717 vs 4186, rounds
  2-10 793 vs 278; fixed by 168 to 513 vs 281. Still open: rounds 61+ 3241 vs 3076 in 166-168 against f9d2e26b,
  untraced. A pre-existing `engine error 5` in prepare/queue at gen-labyrinth-102106300 r756 (side b) is caught and
  changes nothing; untraced.
- Plan v4 and the first-turn cuts (CHANGES 155-156; 2026-10-26, wide bench, test drafts, 100M, against f3f47ea;
  `replays/fuel/m155-*.json`): v4 alone 52/52 identical, round 1 -1.3k a champion (-0.2%), play turns level; v4 plus
  the six cuts 52/52 identical, round 1 mean 539.2k -> 519.3k (-3.7%, p90 -2.5%), play turns 48,501 -> 48,408 (-0.2%;
  total -0.23%). The cuts: profiled mandatory round-1 work 244.0k -> 221.0k (`StaticMap::build` -11.5k, of it
  crossings -6.8k; `init_beliefs` -3.1k; siege's `altar_access` -7.6k); at the real budget, round-1 turns that ran
  out 61 -> 53 of 241 (in `decide` 59 -> 50). Lost or dropped: `[[clang::minsize]]` on `StaticMap::build` and
  `init_beliefs` (dearer: camp beliefs 11.6k -> 21.6k on boss-battle, camp groups +8k); camp members by `resize` and
  direct writes (+6k on gen-hourglass-102205812) and the healths by `resize` and a raw loop (no change): the cost is
  libc++'s per-vector machinery, hence fixed arrays; a first live-camps build branching inside the steady-state loop
  (~5 fuel a play turn, so moved out of line). `FuelMeter` (~170) inflates inner-loop profiles (~30k on a 40-group farm
  loop); laps of raw `fuel()` reads (~15) do not. Biggest round-1 costs left, with ideas:
  [first-turn.md](hyperion/draft-compute/first-turn.md).
- First-turn cuts, pass 2 (CHANGES 160; 2026-10-26, wide bench, test drafts, 100M, against df3b03e;
  `replays/fuel/m160-*.json`): 52/52 identical; round 1 mean 523.6k -> 516.8k (-1.3%), play turns level (total
  -0.04%); profiled mandatory round-1 work 212.0k -> 193.4k; at the real budget, round-1 run-outs 48 -> 28 of 241.
  Three plan bits (`tributes_walked`, `dash_spawn_steps`, `dash_altar_steps`), attack tiles indexed to the group
  asked, enemy steps decoded on first ask, live camps' first build skipping version-0 beliefs. Lost or not done: a
  "no dash-crossable tile" bit (4 of 111 dasher instances, ~-0.2k); camp tiles set in the board's words instead of a
  host set per member (+1.2k, reverted); the farm order built in `decide` (it would move into round 2's 100k turn);
  allies' `possible`/`undashed` boards left unallocated (~1.1k, but ~60 readers to audit for a null board); faster
  decode code (~90-150 a value is the op count); a struct-of-arrays camp layout and exact cuts to `min_camp_damage` /
  `spell_clear_rounds` (float rounding and `std::sort` tie order feed the damage), untried. Inlined, the
  `tributes_walked` path cost ~11 a play turn, so the rebuild is out of line.
- First-turn cuts, pass 3 (CHANGES 161; 2026-10-26, wide bench, test drafts, 100M, against `astraeus-m160`;
  `replays/fuel/m161-merge.json`): 52/52 identical; round 1 mean 516.8k -> 513.8k (-0.6%), play turns level (total
  -0.04%); profiled mandatory round-1 work 193.4k -> 188.5k; at the real budget, round-1 run-outs 28 -> 21 of 241.
  Pooled camp arrays, storage-less ally boards (copies now don't compile), the threat board skipped with no ally
  within the group's threat radius, first ranks without `rank_turns`. Lost or not done: `ally_engaged` as a
  member-by-ally distance loop (+1.3k round 1, +0.44% play turns: the cached board wins over turns); the fastest
  clear on first need (round 1 -0.8k, play turns +0.05%); `safe_targets` by a word scan (`count_in_square`) in place
  of `any_within`'s host ops (+0.65k, +17k on boss-battle); earlier farm-loop pruning (it reorders equal-valued
  groups, so not exact); camp damage and a struct-of-arrays camp layout, untried.
- Round 1's farm loop and the draft (CHANGES 163, plan v7; 2026-10-26, wide bench, test drafts, 100M, against
  `astraeus-merge162`; `replays/fuel/r1farm-*.json`): 52/52 identical; round 1 mean 513.9k -> 500.2k (-2.7%), play
  turns +0.01%; 24/24 identical on 12 unbenched gen-s1 maps; a copy visiting every group in reverse order on round 1
  also 52/52. Profiled: mandatory round-1 work 188.5k -> 173.6k, farm loop 46.2k -> 28.1k; real-budget round-1
  run-outs in `decide` 21 -> 18 of 241. The draft cannot carry round 1's farm result exactly: it depends on
  `per_gold` (`prices` over a World, 0.09-1.46 by type and map), on allies' claims posted at their turn end (lost if
  they run out) and on allies' first moves (crew work, `struggling`, `ally_engaged`); per-group facts are 3-6 KB.
  So the draft sends guesses (leads) and the loop's prunes were made exact in any order (rated bound from the
  Chebyshev distance, ties by the usual order). Lost: the rated bound after the steps on every turn (+0.7% play
  turns); the first-turn prunes behind runtime flags in one loop (+0.4%: ~19 fuel a group); dash steps read through
  the plan per lookup (~350 each); leads without the rated bound (little: the plain bound already prunes 57%).
- First-turn cuts, pass 5 (CHANGES 170; 2026-10-26, three branches from f9d2e26b stacked on main; wide bench, test
  drafts, 100M; `replays/fuel/p5/`): 52/52 identical after every step and against 9ab21632; 24/24 on 12 gen-s1 maps;
  profiled mandatory round-1 work 184.8k -> 160.7k (over 200k 82 -> 40); real-budget round-1 run-outs 16 -> 2 of
  241. Since the turn-end queue (CHANGES 167) round 1's total is bounded, so judge first-turn cuts by each turn's work
  before the queue: a cut that moves work into the queue can push it onto round 2 (`home_ground`'s lazy read made
  round 2 +3.6k until the queue decoded every group on round 1; `near_bushes` built in the warm-up cost rounds 2-5
  +90-170). Lost or dropped: Ren's `reflected_clear` from summed health (-0.10k); a tighter Ren clear bound (healthiest
  attacker first; fuzzed sound, gap to the true clear 18.6% -> 10.7%, but +0.02k: Ren's plain prunes already decide);
  an all-zero enemy-steps fast path (2 of 26 maps, +0.08k); `ChampionBelief() {}` (-0.77k); two `find_crossings`
  savings (-0.45k, dashers only); `farm_attack_tiles`' fuel floor skipped for drafted tiles (not exact:
  `ready_check_` is keyed by slot, round and position only). Pass 4's one dearer instance (gen-dense-camps-102108100
  b, Ren, +5.5k) is the pre-facts check run on 35 groups to skip 18, not a cache effect.
- Bush clusters by run labelling (2026-10-26, astraeus, wide bench, test drafts, 100M; `bots/variants/astraeus-clusters`):
  the old `grow_cluster` cost ~6.4k a cluster on 00ambush (host flood ~4.3k, the Growth's two boards ~600, indexing
  ~950), and ~12k on a cluster with a diagonal-only link (huge-shared, 17 of 77). Replaced by one union-find pass over
  the bush runs of the exported row-major board (~25 a 64 tiles + ~200 a run, resumable by 8-word batches), then each
  cluster built on demand from its ring of runs (~400 + ~150 a run; found order unchanged). 52/52 identical; round 1
  mean -14.4k (-2.6%), p90 -33k, p99/max unchanged (bushless gen-classic); per champion ambush -58k, monolith-heavy
  -62k, caves -56k, huge-shared -53k, close-spawns -49k, pilgrimage -37k; small maps +0.7k to +1.1k (hooks,
  dense-camps, monolith). WASM really is ~1 fuel an instruction, but a run takes ~150 instructions, and the
  auto-vectorised byte-mask loop cost ~200 a run until vectorisation was disabled. Lost or dropped: rows scanned one
  by one (empty rows ~90 each), a finalise pass instead of rings, binary-search lookup (~180 a cluster vs a per-word
  index). A hybrid (a lean host flood on maps up to ~100 chunks, labelling otherwise) modelled ~5k cheaper on hooks
  but nothing on big maps; not run.
  Shipped bounded (CHANGES 151): a batch labels only as many words as the fuel covers at 32 runs a word, and a
  cluster the fuel can't cover whole (sizes kept per union-find root) is built in resumable batches. A copy forced
  to the smallest batches, pausing after each, stayed 52/52 identical. The bounds cost ~2k a champion on the mean
  (size tracking ~7k on monolith-heavy): final round 1 -2.3% (p90 -3.6%) against the plan v3 commit; ambush -57k,
  monolith-heavy -54k, caves -51k, huge-shared -49k, close-spawns -45k, pilgrimage -33k; hooks +3k.
- Fuel-only changes (byte-identical at 100M) still reroute real-budget games (savings 47.5%, a control burning 2k a turn
  48.4%): judge them by fuel and out-of-fuel turns, not win rate. Out-of-fuel totals swing by hundreds on three or four
  long fights (gen-chambers, gen-hourglass); count them on the full suite.
- Fight sims can't be made much cheaper exactly (2026-10-23, wide bench, test drafts, 100M; `fu/fuel-sims` dbefc20):
  66.3k sims at ~4.7k, ~11 half-turns each. ~60% is the event turns (casts, stuns, deaths, shield expiry, arrivals; ~6
  a sim at 370-490), 17% the existing early-end checks, 10% basic-attack stretches; setup ~840. Exact early exits (a
  quick loss over the enemy's turns, a mirrored quick win) ended 9.1k of 81.8k checks early but each check costs ~570
  against ~1.6k saved: +0.30% fuel (+0.20% checked only at the start). Dropped. Bigger targets: the fixed costs around
  sims (step_guard ~11k, update_camps ~8.3k, Reach and threat builds) and the number of sims asked a turn.
- Those fixed costs have no exact cut worth an A/B either (2026-10-23, same bench; mean turn 36.1k, 2,631 turns over
  100k, 578 out-of-fuel at the real budget). Re-profiled on turns over 100k (own cost a turn; each meter ~100, so
  small items read high): sims 15.9k (2.0 a turn), `Reach::at` 7.5k (20.7 calls), world update 7.2k, `Search::read`
  6.2k, `stand` 5.9k, in-view groups in `update_camps` 5.7k (~10 at ~570), `grow` 5.4k, Reach builds 5.0k (3),
  step_guard's own work ~8k. step_guard's tile loop as per-foe bitmasks: identical replays, fuel -0.00% (its earlier
  3.8k a call was meter overhead). Skipping `update_camp`'s board test before a member's health read is not exact:
  the engine reports a dead member on a seen tile as not in vision, which the test reads as dead; the exact version
  saves <= ~27 per visible member. What remains is per-call engine charges or already cached.
- The search's unseen-threat pricing (`plan.cpp`, `threats_at` per priced tile 2-3 steps out) skipped when no credible
  unseen enemy can reach the grid, one `any_within` per enemy a search (2026-10-23, main c71be8c, wide bench, own
  drafts, 100M): identical replays, fuel -0.003% (dearer in 15,092 turns, cheaper in 716). Dropped; `flee_camps`'
  nine `damage_bound`s (one remembered `any_within` per unseen enemy a tile) would save less.
- Out-of-fuel streaks (2026-10-24, batch 5 bug hunt; v47 harness with fuel-free probes in a RELEASE_CODE copy): a
  resumed turn finishes its tail, then a fresh turn reruns the same path in an unchanged world. 9bce3341-2's 197-turn
  Vesper streak (and its rematch 0688310e-2) was a failing route search out of a hole island, fixed by CHANGES 131.
  4bd1a9ef-3's HoR r37-48 runs out in `plan_strikes` (~50k left at its start, after `want_home` ~18-28k), and
  33ddfdef-1's early streaks are several champions in the opening farm turns: neither is a repeat of one bounded step.
- Gate removals: every one so far was level at 100M but multiplied out-of-fuel turns, since a "skip when short" gate
  adds work exactly when fuel is short. Held branches: `fuel/no-gates-1` (23319 vs 6776), `-1b` (4.2x), `-1c` (5.1x;
  the culprit is pick_up's farm-loop gate, the ward gate a distant second); the turn-order gate (bb414db, +13%); step
  guard on `stand_of` with limits instead of gates (`fuel/guard-fold`, 861 -> 2931); the farm loop ungated with a limit
  of 12 estimates (`fuel/farm-ungate`, 2193 vs 416 on 6 heavy maps). With the farm-loop gate removed, out-of-fuel turns
  went 483 -> 1109, almost all on fight maps, 44% of cuts inside the farm loop.
- The stale-plan drop (CHANGES 59) costs turns in long fights: the resumed search used to finish and spend the attack
  and cast, so its replay was cheap; now every replay is a full turn that runs out again.
- Extra out-of-fuel turns need not show as lost games: main beat hecate 65.7% at the real budget but 62.0% with 100M
  for both (2026-10-21), as lifting the limit helped hecate more. ab.py's `--fuel` sets both sides.
- Heavy-turn profile after CHANGES 109-110 (2026-10-23; 6-map test-draft screen: 00ambush, 00contest, 00lanes,
  gen-bench chambers-102206117, hourglass-102205812, dense-camps-102108100; decide >= 85k, round 1 left out; meters
  ~100-170 each): step_guard 27k (1.2 calls, sims 10k), want_home 21k (stand 10k), prey 19k (sims 8k), search 19k,
  world update 15k (`update_camps` 7k), sims 22.5k in all (6.3 at ~3.6k), `Reach::at` 7k (20), Reach builds 5.4k (3;
  1.56k of each is the tile sets). A first touch pays for shared builds: `damage_ceiling` reads 6k as the first to
  build the visible Reaches and `find_members` (3.7k).
- Measured and dropped on that screen: keeping builds across a mid-turn kill (work after `invalidate()` ~100 a heavy
  turn); turn memos for `lethal` and `approach` (0.1 and 0 repeated tiles a heavy turn); Reach tile sets reused across
  turns with camps in the window, keyed by live members (exact, -25 a heavy turn: the key's own static window and camp
  reads are most of a rebuild); earlier stale checks (a resumed turn wastes a median 3.4k, mostly the throw); dropping
  `prepare_walk` (not exact: the approach field is searched out to our tile).
- Codegen: the ladder builds only src/ with its own flags, so flags can't ship. Locally -flto −1.6% (with the wasm EH
  options at link), inline-threshold=1000 −0.8%, -Os +6.9%. Hot loops are fully inlined with no spills; the cost is
  wasm's stack-machine instruction count (40% local.get/set). wasi-sdk-33's llvm-objdump.exe works on the module.
- Host imports (cambc 3.0.4): the runner links a few undeclared imports (`champion_movement_mask`,
  `bc_Bitboard_DrawManhattan`, `champion_respawn_timer` unprobed); none saves fuel. `fuel_pause`/`fuel_resume` link
  only in debug builds. Imports charge for their work.
- `debug_block` is not free (engine 1.0.3, cambc 3.0.5, 2026-10-22). 100 empty blocks cost 1418 fuel against 619 for
  the plain loop: about +8 a block, because the SDK refunds 2 (`fuel_adjust(2)`) but the guard costs 10. With the
  refund raised to 10 the blocks are neutral in isolation, yet v38's debug build still differs from release on almost
  every turn (draft −9, champion turns +40 to +170), because codegen (inlining) differs. With the stock SDK, v38's
  debug build differed from release in fuel on 2644 of 2652 turns of one ladder game; that game happened to stay
  identical. No constant refund makes a debug build fuel-exact, so the replay harness traces with fuel
  virtualised from a release-code recorder ([tools/replay/harness](../tools/replay/harness/README.md)).
- Measured costs: a simple host call is 3 + its arguments; a field search is chunks × (16 + layers) + ~30 over the
  whole map whatever it touches (100x100: 2.9k for one layer); a WASM loop often costs more than the host calls it
  replaces. Touching a farm group costs ~150-270 even when `best_value` rejects it (~90% of groups); a non-plain act()
  (shield kits, mostly Heart of Ruin's scaling) is 44% of simulation fuel, and sims reaching the horizon are 16% of
  sims but 37% of their fuel.

- CHANGES 107-108's ladder deficit (2026-10-23) is fuel, not logic. 107+108 against 90d285e: ladder 36.2% at the real
  budget (reproduced exactly), but 57.5% of the same 80 games with 100M for both (13 of the 14 maps lost from both
  sides win at least one back); on two fresh suites of ladder mutations (`mapgen mutate`, one per ladder map, seeds
  4242 and 9191) 53.8% and 50.0% (107 alone 50.0%, 108 against 107 53.8%). Its lost ladder games capture less
  (resets +31%, tributed -11%) and die more (+13%); out-of-fuel turns there +21% (585 vs 483, spread over 31 of 56
  games), on the fresh suites +4-6%.
- Where 107-108's fuel goes (bench, 6 ladder maps vs hecate, 100M): 107 +2.9% a turn, 108 +0.5%. Almost all of 107 is
  ad70701's recall end no longer moving an unseen champion to its spawn (+2.8%; the tribute half and the `acted`
  dating cost nothing measurable; b74c16c reroutes 10 of 12 games at +0.6%, d833089 2 at +0.03%). It hits allies too: ours start a recall every turn end, so an ally out of sight used
  to turn `inferred` after 5 turns and `work_arrival` gave it no delay; now it stays anchored at its sighting, so
  `crew_work` stops writing claimed groups off as cleared by the crew and farm prices them in full. The ally half
  alone is +2.4% on identical replays, all in `farm`; the enemy half costs nothing but changes 5 of 12 games. It is
  mean cost on farm turns, not the fight turns that run out: 108 with the ally half reverted still had 592 vs 465
  out-of-fuel turns on the ladder (42.5%). 108's costs are behavioural: `ward_sees` (search legality, +0.5%, p99
  +2.4%) and the Chebyshev unseen threats (+0.2%). The others (kite, hold deadline, bush camps, hold dating) leave
  every bench replay identical at <= +0.06%; `can_act_before` reroutes 6 of 12 games at +0.1%.

- Tail profile after 107-108 (2026-10-23, test drafts, 100M; turns whose `decide` used >= 95k on 4 long-fight maps,
  inclusive meters): step_guard 29.5k (25%), strike search 23.6k (read 8.5k, grow 6.4k, price 7.8k), chase/prey
  22.5k, want_home 22.3k (`stand` sim 10.2k, `lethal` 6.6k); world update 16.8k before decide (`update_camps` 8.1k,
  ~420 a group in view). Fight sims 22% (3.6 a turn at ~7.3k). Real-budget OOFs stop in the strike search 33%, farm
  24%, `strike_after` 16%. A resumed turn spends a median 11.1k of its fresh budget before its own turn starts.
  Exact cuts kept (16/16 identical, total -0.10%, p99 -0.5%, over-100k 606 -> 587): prey skips a (fight key, delayed)
  pair it already lost (8.8% of prey sims); `groups_near` dedupes by a stamp (a miss 1.2-3.6k -> 1.0-2.0k on
  gen-chambers); the release build drops the out-of-fuel printf (~2.5k a resumed turn; local builds still print it).
  No gain: a per-turn sim memo by exact inputs (only prey's repeats, 1.9% of sims); four cached radii in
  `groups_near` (-0.01%); noinline around `run()`/`act` for cheaper unwinds. Reusing the first search's read in
  `strike_after` doesn't pay: it searched 31 times in a gen-chambers game (420k fuel, ~0.01%), once with the state
  unchanged since the first search (the only exact reuse), 0-3 times on ambush, hooks and hourglass; it holds 16% of
  OOF stops only because it runs last on heavy turns. Open: one `sdk_camp` read per member in `read_camps`
  (needs a probe that it reports dead where `has_camp` is false); farm's three `is_stale()` returns let act() go
  on with heal, shield, ward and recall on a stale turn; throwing there instead (`fuel/stale-farm-throws` c4be796,
  identical at 100M) was 50.4% of 240 (ladder and two fresh ladder-mutation suites) with out-of-fuel turns 2129 vs
  2134 in the same games, though the 8-map real-budget bench read 242 -> 187. Not merged.

Tried and no gain (not merged):

- Farm loop: a bound carried across turns (+0.5%; keeping last turn's target would disagree on up to ~29%); best-first
  by bound (+3.8%); spatial buckets (+0.23%; a version only on 64+ group maps −0.02%, not worth ~190 lines); an exact
  prefilter (−0.07%).
- Farm loop order by drafted walking distance (06654719, DRAFT-COMPUTE #1; 2026-10-26): groups by walking steps from
  last turn's choice, one draft field per group, sent as a plan section. 51.4% of 1164 against 801ed7da, but 49.2% of
  356 head to head against the same order by Chebyshev distance (CHANGES 157, kept) on fresh many-group suites, for
  1-6M draft fuel, up to 128 plan bytes and a 4-19k decode per anchor
  ([distances.md](hyperion/draft-compute/distances.md)).
- Fights: exact bounds at a sim's start (+0.05%; the settled sims were the cheap ones); a horizon of 9 (6.7% of sims are
  lost after half-turn 19); shield kits on the plain path (+0.02%); requiet after a death (+0.03%); cross-turn fight
  memos (0.01-10% hit rates); a per-side cast plan (+37%); act or hurt inlined; cast split out of attack (+13% a sim);
  a cache of built fight sides (memcpy costs a fuel a byte). Prey: the bound key first is not exact, and the fight sim
  is not monotone (2 of ~660 settlements wrong).
- step_guard: no exact cut left (Reach memo 0 collisions, repeated keys 2%).
- Reach: a way-0 fast path (−0.04%, relies on unprobed shadow_cast origin behaviour); a Strike == Reach shortcut
  (+0.19%); grouping spots per camp group (+0.48%); tile-set reuse (level: sets cost ~40-90 a build, build_ways and
  at() are the cost).
- Strike search: shifted viewer grids (−0.02%); a best-first frontier under the node cap (~500 a node, out-of-fuel turns
  +27%); per-turn landing classes; a heap for the price loop; keeping each landing grouping for the whole search
  (f4a8d31, ~4k on the biggest search, too much machinery).
- World: a per-group visible-member mask (+2.5%); route field reuse (World round 3, c3c874c: −1.2% on default maps but
  p99 up and heavy maps flat).
- Codegen-level: raw bitboard reads instead of `is_set`; `always_inline` on the SDK's check() (+2%); flatten on decide
  (+0.7%); per-round static caches in small inlined helpers (+0.1-0.5%); memoising turns_to_kill_idle (+0.01%).

- Draft plan v3 (CHANGES 150; 2026-10-26, wide bench, test drafts, 100M, against 25d4567): 52/52 replays identical,
  play turns +0.0%, round 1 +2.6% (+14k a champion). Bit-at-a-time reads cost +45k: a Rice code read bit by bit and a
  member's square scanned tile by tile cost ~100s of fuel each. 64-bit windows with ctz/popcount brought it to +26k, and
  an up-front flag bitmap (no work for unflagged members) with no altar bound brought it to +14k. The altar bound
  (nearest altar per group) cost ~30 fuel an altar per group (25k on 00lanes, 18 altars) to save 3-30 bytes. A decoded
  value still costs ~100 fuel, and a flagged member's index ~900.
  Sending range-3 bush bits only, with range 1 cut from them, kept 52/52 identical and left round 1 at +2.1% (+11k).
  It saved only 0-5 bytes a map (13 over the 26 maps): few camps have an open bush within 1.
- Fuel ideas screen (2026-10-23, a5749c4, isolated copies; 6 maps / 12 games, test drafts, 100M,
  normal local -O3 builds): all three candidates kept 12/12 replays byte-identical; none improved p99.
  Baseline mean/p99/turns >100k: 41977/114160/1555. Stop generating rejected children after the existing
  24-node search cap: 41982/114245/1561 (up to 23777 saved on one turn, but only 63 cheaper vs 9272
  dearer). Direct raw-chunk rectangle tests for any_within: 42180/114209/1563 (+0.48% total fuel).
  Singleton unseen threats as direct Chebyshev distance instead of a field: 41981/114160/1555.
  No real-budget OOF gain claimed; no Hyperion changes (`git show 4e3ab133:research/hyperion/FUEL-IDEAS-2026-10-23.md`).
- Untried fuel ideas (all exact): vectorise the strike search's price loop across candidates (`-msimd128`, per-lane
  order kept); a hits-only `Reach` path for `approach` and `fight_key`, never stored as a full blow; reuse a Reach
  build's eligibility per (from, range, sight) and apply each damage recipe to it; copy only a fighter's mutable state
  into each sim, and undo only the touched health slots in `Search::grow`; unwind `grow` at the 24-node cap through
  its return value instead of polling each branch; certificates that a fight's result holds over a bounded health
  region, built on spare turns.

## Cast value over the cooldown (2026-11-01, astraeus, CHANGES 270)

From the v66 ladder analysis (research/v66-replays/README.md section 5: Willow heals late; HoR and Varg shields up
for fewer champion hits than the top teams'). Kept: Willow's heal by its value over the cooldown (CHANGES 270). In
the A/B extracts, both sides' per-champion-game numbers come from `research/v66-replays/scripts/extract`-style
scripts (willow.py, shield.py, abil.py) keyed on bot names, plus shield absorption (decreases of the shield buff
other than its expiry).
- **Shield before contact (dropped).** `shield_if_needed` as a value rule: damage a round from awake camps in reach,
  a camp we hit and each visible enemy from the turn it can strike us (`Safety::approach`, its strike at its attack
  range), as if we stay; cast when the shield cast now absorbs over its 5 turns at least what it would held until
  every source within the cooldown strikes (so a shield is cast before contact when the approaching blows would fill
  it). Pilot, own drafts, fresh-30338..30339, with the heal change: 49.6% of 1,024. HoR shield casts 52.1 -> 59.3 a
  game, Varg 30.8 -> 35.1, but absorbed damage level (HoR 4,691 -> 4,648 a game, Varg 3,344 -> 3,403) and shield up
  at champion hits level (40.4% -> 40.8%): the extra casts were at 5-9 tiles from the nearest enemy and absorbed 18-20%
  of their amount (casts within 2 tiles absorb 60%), and casts within 2 tiles fell 7,612 -> 7,108 as the cooldown was
  spent before contact. Approaching enemies seldom arrive within 5 rounds, and the bot has no model of the chance they
  do; with `hit_given_reach` as that chance no pre-contact cast could fill a shield. Shield logic left as it was.
- Where HoR's ready shield goes unused at a champion hit (base, own drafts, 1,024 games: 15 a HoR-game): 42% the turn
  after a dash (the strike search chose the landing over the kept shield, `shield_at` = min(amount, 5 x
  damage_bound)), 16% stunned, 3% out of fuel, 13% hits by an enemy it did not see.
- The heal gate first used `Safety::damage_bound` at the ally's tile for the fall test, which counts camps as they
  would hit us (find_members lowers each member's reach by the champions nearer it, the ally included) and
  `grid_r + range` as the planner gate's radius; replaced after the audit by the ally's own camp fire (nearest
  champion) and the heal range plus a walk. The heal-only pilot before those fixes: 50.9% of 1,024 (fresh-30336..37).

## Cassi and Issac pair valuation (2026-11-01, astraeus 1920ec92; CHANGES 271)

- Damage on the healthier body counted only below its partner (10), so hits on Issac were worth 0 wherever Cassi
  stood. The partner now bounds it only while one of us can reach it with a basic attack in a turn, and damage short
  of the bound counts its chip. Level: own drafts 49.7% of 10,240 (fresh-30000..30019), test drafts 49.8% of 10,240
  (fresh-30020..30039); out-of-fuel turns +0.7% / +1.4%.
- The mechanism works locally (melee hits on a lone Issac with a lower, out-of-reach Cassi 72% -> 86%, damage on Issac
  +15%) but converts to no kills: pair kills 1.72 a game for both, 1.0 through Cassi and 0.7 through Issac either way,
  and C&I games 49.3% (base 50.3%, 3,580 games). Our own C&I is the local opponent; ladder Issacs chase as a melee
  frontline, which self-play does not reproduce, so the ladder is the real test.
- Ranged champions still hit a lone Issac only 41% of turns: their misses are retreat steps (v66-replays finding 2),
  not valuation.
- Not tried: unlinking the fight simulator's bodies when one is beyond our reach (safety.cc `link_bodies`).


## demeter reset: gold leans, Fish's packing, the Cassi & Issac draft and pair yield (2026-11-02, astraeus 9abbbdea)

Every A/B is against `variants/astraeus-9abbbde` (astraeus HEAD, CHANGES 274) unless it names pair-yield, on
fastrunner native at 500k fuel per turn (no out-of-fuel turns, so fuel does not confound), 3244 games (ladder, gen, gen-s1, fresh-8101..8104; both on own
drafts), early stop at |z| >= 3 after 300 games. Gold is ab_farm on the ladder + gen + gen-s1 games (1196), CAND - REF
with a 95% CI. Notes and job list: replays/dmm/RESUME.md, jobs3.txt; the Fish study: [fish-farm-2026-11-02.md](fish-farm-2026-11-02.md).

Kept: **pair-yield** ([demeter-pair-yield-2026-11-02.diff](demeter-pair-yield-2026-11-02.diff), applies to astraeus
9abbbdea). It has three parts:
- The draft takes the model's best team that includes Cassi & Issac, on every pick (`map_features.cc` `model_team`).
- Cassi no longer farms gold alone (`gold_farmer`, `farms_gold`): she farms with the crew.
- While its partner lives, Cassi's or Issac's hold counts half in the holder choice (`capture.cc` `hold_shy`,
  `params::pair_hold_share`), so another ally on the group takes the capture.

Fish drafts the pair in 134 of 135 games and deals 80% of its camp damage in crews of 3+, and its pair holds ~1.7
captures by r300 against our ~4.7. The pair shares one chain limit, so each body banks ~15 gems a trip, at 1.2-1.3
bank rounds a gem against 0.7-1.0 for the other types. Yielded gems (~17 a game) go to Prism, Heart of Ruin, Vendetta,
Varg and Willow. The pair's bank rounds fall by 3-4 each and its hitting rounds rise by 3. Captures with the pair in the
crew barely move (7.57 to 7.75 a game), and gems lost are level (fish-farm-2026-11-02.md, Round 4).

| Run | Win % | Gold @300 | Gold @600 | Capture gold @300 | Elk/Golem @300 | Tributed @600 | Camp deaths |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 500k, early stop at z +4.29 (2901 games; farm 604) | 54.0 [52.2, 55.8] | +52 [+16, +91] | +131 [+37, +233] | +52 [+27, +79] | +39 [+21, +57] | +35 [+16, +55] | +0.2 |
| 500k, fresh-8105..8108 (unused), 2048 | 53.6 [51.4, 55.8] | +8 [-10, +25] | -8 [-52, +36] | +15 [+3, +27] | +23 [+13, +32] | +25 [+15, +34] | +0.3 |
| 100k (ladder fuel), 3244 | 54.1 [52.4, 55.8] | +29 [+7, +51] | +77 [+16, +133] | +34 [+18, +50] | +37 [+24, +48] | +26 [+12, +40] | +0.3 |
| 100k, fresh-8109..8112 (unused), 2048 | 52.8 [50.6, 54.9] | +17 [-1, +36] | +36 [-11, +84] | +22 [+9, +35] | +25 [+16, +35] | +27 [+17, +37] | +0.3 |

Gems and capture gold confirm on every set; total gold @300 on the default suites, and only just (+17 [-1, +36]) on
fresh-8109..8112 (pair-pack reads the same way on fresh-8105..8108). At 100k every suite is up: ladder 58.1 (172), gen 55.3, gen-s1 55.1, fresh-8101..8104 52.3-53.9. Out-of-fuel turns are
equal to astraeus's (14066 vs 14277); on fresh-8109..8112 the raw count is 13192 vs 11425, but per body-round it is
1.28 vs 1.25 a 1k (1.48 vs 1.46 when astraeus also drafts the pair): the excess is the extra body. Against another opponent (bots/hyperion, 100k, 3244 each) pair-yield wins 91.1%
[90.0, 92.0] (ladder 84.9) and astraeus 90.4% [89.4, 91.4] (ladder 79.1): consistent, but near the ceiling. A share of
0.25 instead of 0.5 reads the same: early stop 53.8% [51.8, 55.8] of
2398, gold @300 +51.

Kept on top of it, gold first: **pair-yield + the c2 lean** (py-c2,
[demeter-pair-yield-gold-2026-11-02.diff](demeter-pair-yield-gold-2026-11-02.diff), the whole change from astraeus 9abbbdea:
pair-yield plus farm's `gold_gems = p * min(gold_lean_cap, 1 + gold_lean * p)` at lean 2.0, cap 1.5). Against
pair-yield directly:

| Run | Win % | Gold @300 | Gold @600 | Gold, end | Capture gold @300 | Tributed @600 |
| --- | --- | --- | --- | --- | --- | --- |
| 500k, default suites, 3244 (farm 1196) | 50.1 [48.4, 51.8] | +36 [+12, +60] | +59 [+3, +117] | +29 ns | +32 [+17, +47] | -12 [-26, +2] |
| 500k, fresh-8105..8108 (unused), 2048 | 51.0 [48.9, 53.2] | +53 [+35, +70] | +112 [+67, +155] | +183 [+50, +317] | +50 [+39, +62] | -7 [-17, +2] |
| 500k, fresh-8109..8112 (unused), 2048 | 49.8 [47.6, 51.9] | | | | | |
| 100k, default suites, 3244 (farm 1196) | 49.8 [48.0, 51.5] | +38 [+14, +64] | +85 [+21, +151] | +170 [-6, +355] | +36 [+19, +53] | -2 [-17, +11] |

Pooled 50.2% of 10584: wins level with pair-yield, and the gold gain holds on every set (camp deaths level). Against
astraeus py-c2 reads 53.5% [51.7, 55.2] at 500k and 52.5% [50.7, 54.2] at 100k, pair-yield 54.0 and 54.1: each within
noise, both lower, so the lean may cost up to a point against astraeus. On astraeus alone c2 read 49.0% (tributed
-14); on pair-yield the gem cost is smaller (-2 to -12). The half-strength c1 read 49.2% of 7340 against pair-yield
(below), within noise of c2's 50.3% of the same games. pair-yield is the pick for wins; py-c2 for demeter, gold first.

Re-verified on the newer astraeus f9074463 (CHANGES 275-288; both patches apply unchanged): pair-yield early stop
53.9% [52.0, 55.9] of 2498 (capture gold @300 +42 [+17, +68], Elk/Golem +31, tributed +27 [+5, +48], total gold @300 +28
ns; farm 543); py-c2 early stop 53.4% [51.3, 55.4] of 2312 (gold @300 +54 [+18, +95], @600 +121 [+24, +226], capture
+66 [+40, +94], tributed -4 ns; farm 522); py-c2 against pair-yield 48.9% [47.2, 50.6] (default suites; gold @300 +43
[+18, +68], @600 +83 [+17, +145], capture +41 [+24, +58], tributed -10 [-25, +4]) and 49.8% [47.6, 52.0] (fresh-8105..8108). Every direct py-c2 against pair-yield read together: 49.8% of 15876 (~[49.0, 50.6]).
Through astraeus py-c2 reads 0.5-1.6 below pair-yield each time (three pairs), so a cost of up to a point is not ruled out.

`bots/demeter` is now astraeus e9c37971 (CHANGES 292) plus pair-yield: 54.0% [52.3, 55.7] of 3244 against astraeus
e9c37971 at 100k fuel (ladder 57.6, every suite above 50). Out-of-fuel turns 19966 vs 20401, all in `decide` and
`queue` on both sides, none at a demeter-only site; both are ~40% above 9abbbdea's (~14.1k), from CHANGES 275-292.
Once astraeus took pair-yield (CHANGES 294, on 293), it differed from demeter only by 293: astraeus 38aa25ce against
demeter, ladder maps only, own drafts, 100k: 52.3% of 172 [44.9, 59.7], out-of-fuel turns 1906 vs 1784
(`replays/ab/ast294-vs-demeter-ladder/`). `bots/demeter` was then recopied from astraeus 38aa25ce.

Without the yield (**pair-pack**, [demeter-pair-pack-2026-11-02.diff](demeter-pair-pack-2026-11-02.diff)):

| Run | Win % | Gold @300 | Capture gold @300 | Elk/Golem @300 | Tributed @600 | Camp deaths |
| --- | --- | --- | --- | --- | --- | --- |
| 500k, 3244 games | 52.1 [50.4, 53.8] | +31 [+7, +54] | +33 [+16, +49] | +27 [+16, +39] | +36 [+23, +49] | +0.3 |
| 500k, fresh-8105..8108 (unused), 2048 | 51.4 [49.2, 53.5] | +8 [-10, +25] | +16 [+4, +29] | +16 [+6, +26] | +25 [+16, +34] | +0.4 |
| 100k (ladder fuel), 3244 | 50.6 [48.9, 52.3] | +27 [+3, +50] | +31 [+14, +48] | +24 [+12, +36] | +31 [+17, +45] | +0.3 |

Its parts: cassi-pack alone 51.8% [50.0, 53.5] (confirm 51.6% [49.4, 53.7] on fresh-8105..8108), gold level; the pair
draft alone 49.2% [47.4, 50.9], capture gold +37 [+22, +52], deaths to camps +0.3. The forced pair only pays with packing.
By draft (1196 games, cells of 100-300): no pick count or opponent draft where the forced pair reads consistently worse.

Dropped (against astraeus unless noted):
- Gold lean (`gold_gems = p * min(cap, 1 + lean * p)`), every form but the mildest (c1, below) cost wins: c4 47.0% [45.3, 48.7] (gold @300 +34,
  tributed -26); c4 only while not behind in gems 48.8% (gold +16 ns); behind by up to 50 47.5%; on cassi-pack 49.0%
  (gold +8 ns, tributed -12); c2 49.0% [47.3, 50.7] (gold @300 +37, @600 +101, tributed -14). At 100k fuel c4 + one-owner 48.4%, c4 alone 47.1% (early stop z -3.21), one-owner alone
  48.6% (gold +3). The lean trades gem pace for gold.
- Fish packing heuristics, level and no gold: crew-follow 50.6%, pos-crew (ally positions over comms) 50.5% (Elk/Golem
  +16 [+6, +27], total level), open-pack (ally claims on fighting groups 2.0x for 40 rounds) 50.4%, crew-defend 49.8%,
  marcella-hold 50.3%, no gold farmer at all (also Tavi) = cassi-pack (no Tavi gold-farmer games in these suites). A 1.5x
  pull or comms positions barely move packing (lone Elks with crews of 4+: 18-20% vs 17%; Fish 53%).
- On pair-yield, each an early stop level with it: carrier-holds 53.3% [51.3, 55.2] (2413 games), gold @300 +38;
  output-yield (holder value less 0.05 x camp output, the strongest farmer yields) 53.1% [51.1, 55.0], gold +41.
  takeover (only the pair takes over a capture one of it holds) 53.8% [51.9, 55.6], gold +34.
  prism-hold (a healthy Prism +0.5 a gem to hold) 53.6% [51.7, 55.6], gold +45, tributed +17.
- On pair-pack: carrier-holds (an ally already carrying gems gets +0.5 a gem to hold) 51.7% [49.9, 53.4]; pos-crew 50.4% (Elk/Golem +38 but end gold -174); pair-cover (the pair stops counting a recalling or
  doomed ally as cover) 51.9%, camp deaths +0.2 vs +0.3, gold the same: no gain.
- Bank or chain (`from_altar_value` weighed at `chain_bias`, on pair-pack): 0.85 49.3% (camp damage +1.4k but tributed
  +20 vs +36, gold lost +7); 0.7 48.6%; 1.15 51.4% (camp damage +0.9k, gold @300 +7: banking sooner farms less). Bigger bags farm
  more and score less, smaller ones farm less; astraeus's 1.0 is the best.
- hasten (a Capture-emblem owner steps into an ally's hold under way, capping it at capture_emblem_time) 50.0%
  [48.3, 51.7]: gold identical to astraeus through r300 (+0.0, tributed +1); the emblem is rare, so it barely fires.
- contest-gold (contest an enemy hold on gold groups too, not only gem groups) 49.9% [48.2, 51.6]: gold @300 +9 [-14, +34],
  tributed -3.
- More c4 lean, each worse: in shop gold pricing too 46.8% [44.7, 48.9] (early stop of 2199), in capture takeover pricing
  too 47.1% [45.4, 48.8], only before gold_lean_until 47.3% [45.6, 49.0].
- pass-gold (ranged hits in passing on gold clusters too) 49.0% [47.3, 50.8]: gold @300 +6 [-16, +29], tributed -3.
- Pair safety, each against pair-yield directly. pair-yield's pair dies to camps 2.7x as often as astraeus's (170 vs 64
  hit-body deaths in 600 pair games each, f100-confirm): mostly Golems (68 vs 18) and Monoliths (49 vs 8), and fast
  (from >= 0.6 health to dead within 5 rounds 41% vs 22%); Issac is hit in 103 of 170. A death of either takes both
  bodies and both bags. pair-line (the pair's recall line 0.35 even with no enemy near, not 0.18) 49.4% [47.7, 51.2]:
  pair camp deaths 20.7 vs 24.7 per 100 games, gold level. pair-nofinish (no staying below the line to finish a camp)
  49.8%, deaths and gold unchanged. pair-notank (halve the pair's crew tank score) is a no-op: `crew_tank` only feeds a
  debug_block; camps hit the nearest champion. The extra deaths are the price of packing.
- The c1 lean (`gold_lean` 1.0, cap 1.25; the mildest): on astraeus 49.7% [48.0, 51.4] with gold @300 +29 [+8, +53],
  @600 +58 [+2, +117], tributed -2: level and a gold gain. On pair-yield (py-c1) against pair-yield directly: 50.7% of
  3244 (default suites), 47.8% of 2048 (fresh-8105..8108), 48.2% of 2048 (fresh-8109..8112): 49.2% of 7340 (~[48.0,
  50.3]), 48.0% on the unused sets alone; gold @300 +24 [+1, +47], @600 +60 [-1, +119], end +17 ns, tributed +1.5.
  Against astraeus py-c1 read 51.6% (default) and 53.6% (fresh-8105..8108; pair-yield 54.0 and 53.6). About a point of
  wins for the gold: dropped (c2, twice the lean, is kept above).

## Turn order and ally coordination (2026-11-02, astraeus e9c37971)

Against frozen `variants/astraeus-e9c3797`, own drafts, fastrunner, 10,240 games a row (20 fresh suites of 512) unless
noted. Notes, traces and scripts: [turn-order-2026-11-02/](turn-order-2026-11-02/README.md).

| Change | Win % | 95% CI | OOF cand / ref | Verdict |
|---|---|---|---|---|
| Idle allies nearer an enemy act later (`ast-idle-nearlate`, `plain_priority` only) | 51.5 / 52.3 (6,828, unused) / 52.3 | ~52.0 of 27,308 | level | **kept: CHANGES 293** |
| Idle allies nearer an enemy act earlier (`ast-idle-nearearly`) | 44.4 | 43.4-45.4 | 72,968 / 74,109 | lost |
| Dead allies ranked below idle ones (`ast-deadlast`) | 48.2 | 47.2-49.2 | 73,678 / 73,653 | lost |
| Ally seat commitment v1 (top-seat planning + soft holds) | 46.6 | 45.6-47.6 | 81,883 / 77,739 | lost |
| Ally seat commitment v2 (no soft holds, move priced at the release seat) | 49.45 of 20,480 | ~48.8-50.1 | +2.6-6% | level, held as a base |
| Worst-case enemy order (`ast-wc`: no persistence fallback, permutation bound, Safety) | 49.6 | 48.7-50.6 | +14% | level, held |

- **Act late when nothing needs you early.** An idle champion near an enemy that acts earlier only hands the enemy the
  reply: in rounds with a dead ally, deadlast's idle-near allies acted 1.4 enemy turns sooner, took 38% more damage and
  died 35% more, dealing no more. Ordering idle allies by nearness swings 7 points. The baseline's dead-above-idle rank
  gets part of this. Seat v1 lost the same way: each of its two parts moved low-need allies earlier, ~2 points each.
- **Ally commitment is real but rare.** 3.0% of bids assuming acting first acted after their enemy (0.28 a game), 89%
  pushed down by a later teammate's kill bid; outcomes were no worse. v2 cut hard breaks from 1.9% to 0.25%.
- **Safety's next-round count is wrong in 32.6% of reads within 4**: 49% of its underestimates from our own slot
  moving after the move, 31% from an unsettled enemy moving up.
- **Round-boundary doubles** in contact land kills at 2.9% against 1.3% for a single turn, but only 14.5% go to one
  champion (no ladder team over 13%). Unbuilt.
- **Small:** forks 0.25 a game; an ally holding our only hitting tile 0.8% of strike turns.
- **Kill conversion is not order:** astraeus kills 30% of enemies under 25% health in reach, Fish and PBG 45%; enemy
  acting first is no more common in escapes than kills.
- Worst case costs fuel mostly through `double_unacted` doubling a blow already widened to two turns (more often now).
  The adversarial sparring bot (`ast-adv`, static between bids) is as strong as astraeus but punishes neither.

Follow-up on astraeus 294 (against `variants/astraeus-294`, 10,240 games a row unless noted):

| Change | Win % | Verdict |
|---|---|---|
| Worst case ported, `double_unacted` fixed (`ast-pwc`) | 50.5 / 49.8; 50.4 / 51.2 | level, +21% out-of-fuel turns; held |
| Predicted enemy order for kill bids and `drop_stun` (`ast-pred`) | 50.3 / 49.7 | level, +37% out-of-fuel; dropped |
| Learning a static opponent online (`ast-pred-learn`, against the user's rule) | 49.8 / 49.3 | dropped |
| Joint worst case per tile (`ast-safety`: base blows + the m largest second turns) | 46.6 / 46.9 | level at 100M fuel, 2.1x out-of-fuel turns; held for a cheaper form |
| Strike pledges in the payload (`ast-comms` v1) | 50.8 / 50.8 | the gain is keeping our own bid; readers +0.00 |
| Keep our own kill bid, no message (`ast-follow` v1, + no bid while channelling v2) | 50.3 / 50.2 | level; base of CHANGES 295 |
| Kill-now value on all partial damage (`ast-kill1`) | 49.7 (-0.92 paired) | lost: fewer engagements; don't retry |
| Kill-now value on kills only (`ast-kill1b`) | 50.5 / 50.3 | level |
| Bids at the real distance (`ast-kill2`, = v2 + reach) | 50.5 / 50.5; 50.4 of 40,448 | **kept: CHANGES 295** |

- Enemy order: a predictor beats both fixed rules on calibration (ladder Brier 0.086 against last-read 0.101 and
  worst case 0.476) but makes the same calls at 0.5. The worst-case kill bids were already in force against astraeus
  opponents (the fallback is off in 99.8% of turns); worst case in Safety halves undercounts and adds as many
  overcounts. Old damage sums gave every unacted enemy a second turn: more than the order allows in 45% of reads with
  2+ enemies (`safety-fuel.md`).
- Kill conversion is not a choice problem: kills on offer are taken 97.4% of the time. Near an enemy under 25%,
  33% of our champion-turns can't reach it and 20% retreat on Safety's call; ~2% would kill with another choice.

## Camp aggro: waking camps onto enemies (2026-11-02/03, astraeus 294 variants)

Camps attack at the next round's start, before any champion moves, hitting the nearest champion in reach (ties to the
earlier seat). An enemy that has already acted, or is channelling, is held in place for that first hit: damaging or
stunning any member of a sleeping group whose strikers reach it, from outside their reach, puts the camp on it.
Variants and diffs: [aggro-2026-11-03/](aggro-2026-11-03/README.md). All against `variants/astraeus-38aa25c` (CHANGES
294), both bots on their own drafts (`--no-test-draft`), fastrunner native, on alext (whose `maps/gen` differs from
the local, recovered one).

- `aggro-s`/`s6`: at the turn's end (bot.cc `aggro_camp`), an unused basic attack or a damage/stun cast when every
  woken striker's nearest champion is a held enemy, never us or an ally (seen, or seen within 5 rounds near).
- `aggro-x2`..`x8`: the strike search credits a woken hit on a held enemy with `hit_worth` (combat/plan.cc `wake`) and
  may basic-attack or ground-cast such groups; x3-x8 make the same decisions as x3 at falling cost.

Fixed samples, 52,394 games each (ladder, `maps/gen`, `maps/gen-s1`, `maps/fresh-92001`..`92100`):

| Variant | Win % | 95% CI | Out-of-fuel turns vs REF |
|---|---|---|---|
| aggro-s (turn end) | 50.05 | 49.6-50.5 | +20.3% |
| aggro-s6 (s, cheaper) | 50.05 | 49.6-50.5 | +10.3% |
| aggro-x8 (search credit) | 49.68 | 49.3-50.1 | +9.1% |
| aggro-x8-nomono (sleeping Monoliths stay banned) | 49.77 | 49.3-50.2 | +9.6% |
| aggro-x2-safe-nomono (no credited wake with an unseen ally maybe near) | 49.56 | 49.1-50.0 | +10.9% |
| aggro-x6-null (the search code, weight 0: the base's decisions) | 49.77 | 49.3-50.2 | +8.6% |
| aggro-x8s6 (x8 + s6's turn-end hook) | 49.95 | 49.5-50.4 | +18.7% |
| aggro-x8-w05 / -w3 (aggro_weight 0.5 / 3) | 49.73 / 49.67 | 49.3-50.2 / 49.2-50.1 | +9.9% / +8.1% |
| aggro-s6-min10 (= s6 game for game: no striker is under 20) | 50.05 | 49.6-50.5 | +10.3% |
| aggro-s6-min40 (no lone-Wolf wakes; 272 games differ from s6) | 50.04 | 49.6-50.5 | +10.0% |
| aggro-s6-selfin (may stand in a woken reach) | 50.07 | 49.6-50.5 | +10.6% |
| aggro-s6-mem0 / -mem12 (ally memory 0 / 12 rounds) | 50.04 / 49.97 | 49.6-50.5 / 49.5-50.4 | +10.3% / +10.2% |
| aggro-s6-nospell / -spell30 (basic attacks only / casts worth 30) | 49.94 / 50.09 | 49.5-50.4 / 49.7-50.5 | +9.5% / +10.4% |
| aggro-s6-nomono | 50.07 | 49.6-50.5 | +10.2% |
| aggro-s6-unheld (wakes onto enemies yet to act too; 4054 games differ, 1332 winners flip, 666 each way) | 50.05 | 49.6-50.5 | +10.3% |

Screens before (SPRT 0.50 vs 0.52 stopping low on ladder, gen, gen-s1, fresh-9100..9115; then 0.50 vs 0.51 on
gen..fresh-92040): x2-nomono 50.2 of 2731, s 48.9 of 1193, x2-safe 49.8 of 2592, x2-safe-nomono 50.0 of 2002, x3
50.1 of 2018, s6 50.4 of 4143; x6 49.3 of 3378, s6 49.9 of 8143, x6-nomono 49.6 of 3158, x6-w2 49.4 of 3919, all H0.
The local 1196-game reads (x2-nomono 52.3, s 52.1) were noise.

- **Nothing reaches significance; the wake is real but small.** In x8's games (1196, ladder/gen/gen-s1, `ab_farm.py`)
  REF dies to camps 1.2 times a game against CAND's 1.1 (-0.1, CI [-0.2, +0.0]); gold, captures and camp damage are
  level. A held enemy is in a sleeping striker's reach in ~21% of the strike searches that read camps.
- **The out-of-fuel increase is the code's cost, not different games.** x6-null plays the base's decisions (bench:
  52/52 replays identical at 100M fuel) yet has +8.6% out-of-fuel turns. Paired on identical bench searches it costs
  +1528 fuel a search, all in `read` (`srch_pair.py`); searches run ~1 turn in 12, so +0.2% of all fuel. The excess is
  broad (CAND more on 6959 maps, fewer on 3938; the top 200 maps hold half; `oof_maps.py`), mostly `decide`: turns
  near the cap anywhere tip over. Its price in games is at most a few tenths (x6-null 49.77, CI 49.3-50.2).
- **Where the fuel went** (x7/x8 meters, `aggro-x8-meter-on-x8.diff`, `agm.py`): with no held enemy in reach,
  `aggro_possible` still costs a median ~0.9k, a groups_near query at our tile the base never makes for a plain
  attacker; with one (21%), read_members +2.1k (touches flips on), the group checks and find_wakers ~3.7k (x7: 5.4k),
  read_camps' member loop ~2k. Cheaper forms: x7 (cached group verdicts) +27 a search; x8 (static per-group reach boxes,
  held enemies and find_wakers' champion list once a search) -49 a search; x9 (boxes instead of groups_near) +454,
  since groups_near's per-tile cache persists across turns and x8's query was warming later reads; x10 (a static
  dilated camp board before groups_near) +38. All exact (bench replays identical).
- The turn-end hook (aggro-s) cost fuel the same way: s6's cheaper hook halved its out-of-fuel increase (+20% to
  +10%) with identical replays, and neither moved the win rate.

Held: nothing kept. If revisited, luring awake camps (an awake monster stays awake while any champion is in its range,
and hits the nearest) is a different mechanism from waking sleeping ones.

Fuel alone reshuffles games: aggro-s and s6 decide identically at unlimited fuel, yet 26k of their 52k games differ in
length under the real budget. A change touching a few percent of games reads as noise beside that.

### The ostrich on alext (2026-11-03, demeter = astraeus 294 + the ostrich)

`bots/demeter` (copied as `variants/demeter-ost`) against `variants/astraeus-38aa25c`, own drafts, fastrunner native:
**51.04% of 52,394** (ladder, gen, gen-s1, fresh-92001..92100; CI 50.6-51.5; fresh suites 51.09% of 51,198), out-of-fuel
turns 501,069 vs 495,973 (+1.0%). Confirmed on unused seeds, fresh-91001..91020 and fresh-94001..94080: **51.38% of
51,200** (CI 50.9-51.8), out-of-fuel +1.6%. `ost-low` (also the early seats in danger bucket 4+ unengaged): 50.72% of
52,394 (CI 50.3-51.2). The local 51.0% of 7340 was right. Not yet ported to astraeus, which has since taken CHANGES
295-296.

## Fuel campaign 4, round 1 (2026-11-03, astraeus fc99b847)

Baseline `astraeus-fc4b` = fc99b847; merged bot `astraeus-fc4-m1` (CHANGES 298-301 plus a fuel-only cut in
`Pathing::plan`). Notes, review and per-worker numbers: hyperion/fuel-campaign-4/NOTES.md ("Worst-case census", "Fuel
gates", "Merge round 1"); benches `MAIN/replays/fuel/fc4/m1-*.json`. 100M: replays identical on all eight bench sets
(wide, oof, mg, q, big, fs, fight, tgt), total fuel -0.08% (q) to +0.01%.

A/B, real budget, own drafts, fast runner, fresh-11000..11019, 10,240 games each (per bot; OOF = out-of-fuel turns,
fuel = a play turn's fuel, `fuelstats.py`):

| run | win % (95% CI) | OOF cand / ref | r1 | 2-10 | 11-60 | 61-300 | 300+ | runs <10 / 10-49 / 50+ | fuel mean / p90 / p99 |
|---|---|---|---|---|---|---|---|---|---|
| mirror (fc4b) | 50 | 97,011 | 10,705 | 10,093 | 14,126 | 23,262 | 38,825 | 62,977 / 29,172 / 4,862 | 50,621 / 86,450 / 92,950 |
| fc4-census (298 alone) | 49.3 (48.4-50.3) | 66,944 / 95,767 | 7,742 | 6,424 | 10,088 | 14,485 | 28,205 | 44,226 / 20,793 / 1,925 | |
| fc4-gates (299-301) | 50.6 | 96,244 / 97,543 | | | | | | | |
| **m1 (298-301)** | **49.6 (48.7-50.6)** | **66,239 / 95,128** | 7,746 | 6,455 | 9,997 | 14,321 | 27,720 | 43,960 / 20,456 / 1,823 | 50,589 / 86,350 / 92,950 |

m1 is -30.4% against the reference in the same games (target -30%), level with the census branch alone (-30.1%): the
gates' lower comms and ward reserves don't eat the fuel the farm loop now leaves. Turns at or over 100k 0.29% -> 0.23%.
Shortcuts without out-of-fuel 4.11M -> 3.86M (-6.0%): farm-partial-evaluation 2,321,472 -> 2,703,675 (+16.5%),
comms-stale-vision 500,462 -> 55,850 (-88.8%), step-guard-entry 476,124 -> 428,583, turn-order 383,022 -> 261,417
(-31.7%), farm-no-route 77,555 -> 67,774, ward-no-bushes-clusters 69,176 -> 48,791 (-29.5%), static-descend 28,966 ->
21,637, step-guard-look 61,960 -> 75,665, crow-flies-farm 73,653 -> 78,516. Confirmations: 298 alone 50.0% of 10,240
on fresh-10100..10119 (OOF -30.8%); 299-301 alone 50.5% of 5,120 on fresh-11100..11109 (OOF -1.2%).

## Fuel campaign 4, round 2 (2026-11-03, astraeus m1)

Base `astraeus-fc4-m1` (round 1); `astraeus-fc4-m2f` = m1 + CHANGES 302 (the farm loop's CrewAllies table and the
no-crew plan_crew skip, fuel only), `astraeus-fc4-m2` = m2f + CHANGES 303 (walk_allies_in delays an ally one
walk-turn out of reach; a behaviour lift). Review, bench tables and the cumulative position: hyperion/fuel-campaign-4
/NOTES.md ("Farm loop", "Rules and assumptions", "Merge round 2"); benches `MAIN/replays/fuel/fc4/m2{,f}-*.json`.
100M: m2f's replays identical to m1's on all eight sets, total fuel q -3.90%, big -1.91%, wide -1.85%, oof -1.09%,
mg -0.99%, tgt -0.64%, fight -0.03%, fs +0.03%; m2's diverge where the lift fires (oof 18/48 and mg 13/24
identical; oof and mg p99 and turns over 100k up in the diverged games).

A/B, real budget, own drafts, fast runner, fresh-11000..11019, 10,240 games each (OOF per bot):

| run | win % (95% CI) | OOF cand / ref | r1 | 2-10 | 11-60 | 61-300 | 300+ | runs <10 / 10-49 / 50+ | fuel mean / p90 / p99 |
|---|---|---|---|---|---|---|---|---|---|
| m2f vs m1 | 50.5 (49.5-51.4) | 64,368 / 69,041 (-6.8%) | 7,130 | 6,154 | 9,607 | 13,422 | 28,055 | 41,173 / 20,484 / 2,711 | 50,023 / 86,150 / 92,550 |
| m2 vs m1 | 50.1 (49.1-51.1) | 65,003 / 68,685 (-5.4%) | 7,129 | 6,161 | 9,461 | 13,234 | 29,018 | 41,115 / 19,704 / 4,184 | 50,031 / 86,250 / 92,550 |
| m2 vs m2f | 49.7 (48.7-50.7) | 64,195 / 64,396 | 7,130 | 6,154 | 9,442 | 12,917 | 28,552 | 41,149 / 19,233 / 3,813 | |
| m2f vs fc4b | 50.7 (49.8-51.7) | 66,392 / 97,007 (-31.6%) | 7,128 | 6,146 | 9,709 | 13,571 | 29,838 | 41,100 / 19,808 / 5,484 | 50,063 / 86,250 / 92,550 |
| **m2 vs fc4b** | **50.3 (49.3-51.3)** | **66,082 / 95,949 (-31.1%)** | 7,127 | 6,142 | 9,541 | 13,324 | 29,948 | 41,081 / 19,680 / 5,321 | 50,070 / 86,250 / 92,550 |

farm-partial-evaluation -24.6% against m1 (2.03M / 2.69M a bot), shortcuts without out-of-fuel -19.5% (m2f) and
-18.6% (m2); against fc4b, m2's shortcuts are 3.13M / 4.11M (-23.9%). The walk lift is level on win rate and OOF in
three A/Bs (and pooled 50.07% of 20,480 against m1 in the worker's), so it is kept. Against fc4b, m2's total OOF is
m1's (66,082 against 66,239): every bucket to round 300 is 5-8% lower, but two new turn-end-queue runaways
(gen-fortress-1101902231, gen-dash-lattice-1100707609; also in m2f's run) add ~3.5k in runs of 50+.

## Fuel campaign 4, round 3 (2026-11-03, astraeus m2)

Base `astraeus-fc4-m2` (round 2); `astraeus-fc4-m3` = m2 + CHANGES 304 (make_way / label_through skip label walks
that cannot find a label; fuel only) + 305 (the opening farm loop reserves the walk's attack-tile decode; behaviour
at the real budget only). Review, worker tables, dropped variants and the cumulative position:
hyperion/fuel-campaign-4/NOTES.md ("Worst-case tail", "Merge round 3a"); benches `MAIN/replays/fuel/fc4/m3-*.json`.
100M: m3's replays identical to m2's on all eight sets, total fuel -0.05% (fs) to -0.42% (fight), round 1 +0.1-0.5%.

A/B, real budget, own drafts, fast runner, 10,240 games each (OOF per bot):

| run | suites | win % (95% CI) | OOF cand / ref | r1 | 2-10 | 11-60 | 61-300 | 300+ | runs <10 / 10-49 / 50+ |
|---|---|---|---|---|---|---|---|---|---|
| A vs m2 | fresh-11000..11019 | 50.2 (49.3-51.2) | 62,263 / 64,097 | 7,132 | 6,183 | 9,451 | 12,837 | 26,660 | 41,038 / 19,847 / 1,378 |
| A+C vs m2 | fresh-11000..11019 | 49.5 (48.5-50.5) | 59,553 / 64,634 (-7.9%) | 4,038 | 6,568 | 9,531 | 13,218 | 26,198 | 38,150 / 19,430 / 1,973 |
| A+C vs m2 | fresh-11240..11259 | 50.4 (49.4-51.3) | 60,013 / 64,248 (-6.6%) | 3,586 | 5,971 | 9,203 | 13,580 | 27,673 | 36,563 / 21,996 / 1,454 |
| **m3 vs fc4b** | fresh-11000..11019 | **50.3 (49.3-51.2)** | **59,134 / 93,635 (-36.8%)** | 4,028 | 6,561 | 9,461 | 12,925 | 26,159 | 38,476 / 18,284 / 2,374 |

m3 against fc4b: fuel a play turn 49,911 / 86,150 / 92,450 (mean / p90 / p99) against 50,666 / 86,450 / 92,950,
turns at/over 100k 0.22% against 0.29%; shortcuts 3.16M against 4.18M (-24.3%). Against the same baseline m2 had
OOF 66,082: m3 is -10.5%, round 1 7,127 -> 4,028 (305) and runs of 50+ 5,321 -> 2,374 (304: the
gen-fortress-1101902231 and gen-dash-lattice-1100707609 runaways were make_way walking a crowd of allies every
decide). Dropped (worker): 305's reserve on every turn (farm-partial-evaluation +16%), for the first 10 rounds
(+5.7%), without the ample bound (level, dearer at 100M), and a 3-slot failed-route cache (level with A).

## Fuel campaign 4, round 3b (2026-11-03, astraeus m3)

Base `astraeus-fc4-m3` (round 3a). `astraeus-fc4-m4` adds CHANGES 306 and 307. 306 is fuel only: walk_down skips a
repeated failed descent, and camp_cast reads out-of-reach members only for sole_finish. 307 is behaviour at the real
budget only: on a quiet turn, the turn-order gate keeps a 6k reserve. The review, worker tables and cumulative
position are in hyperion/fuel-campaign-4/NOTES.md ("Exact repeated work", "Turn-order gate", "Merge round 3b",
"Campaign summary"). Benches are `MAIN/replays/fuel/fc4/m4-*.json`. At 100M, m4's replays are identical to m3's on
all eight sets, with total fuel +0.00% to -0.09% and turns over 100k down on every set.

A/B, real budget, own drafts, fast runner, 10,240 games each (OOF per bot):

| run | suites | win % (95% CI) | OOF cand / ref | r1 | 2-10 | 11-60 | 61-300 | 300+ | runs <10 / 10-49 / 50+ |
|---|---|---|---|---|---|---|---|---|---|
| m4 vs m3 | fresh-11000..11019 | 50.3 (49.4-51.3) | 58,042 / 59,882 (-3.1%) | 4,036 | 6,582 | 9,278 | 12,999 | 25,147 | 38,032 / 18,786 / 1,224 |
| m4 vs m3 | fresh-10000..10019 | 50.0 (49.1-51.0) | 60,742 / 62,640 (-3.0%) | 3,862 | 6,350 | 9,185 | 13,484 | 27,861 | 37,392 / 20,276 / 3,074 |
| **m4 vs fc4b** | fresh-11000..11019 | **50.0 (49.0-50.9)** | **57,482 / 93,462 (-38.5%)** | 4,026 | 6,561 | 9,161 | 12,568 | 25,166 | 38,048 / 17,384 / 2,050 |

Against m3, turn-order firings fell 199k -> 117k and 213k -> 124k (-41%, -42%). comms-stale-vision rose 44k -> 53k
and 47k -> 56k (+20%, +20%). Fuel a play turn is level (mean 49,928 / 49,944). Against fc4b, m4's fuel a play turn
is 49,904 / 86,150 / 92,350 (mean / p90 / p99), against 50,666 / 86,450 / 92,950. Turns at/over 100k are 0.22%
against 0.29%, and shortcuts 3.07M against 4.18M (-26.5%). The fresh-10000..10019 suites are new to campaign 4. The
worker's +250 runs of 50+ didn't recur: 1,224 / 1,358 and 3,074 / 3,175. Dropped: the per-tile step guard
(fc4-guard; OOF +6-8% in 10,240), and the turn-order reserve at 5k (comms-stale-vision +33%).

## Fuel campaign 5, round 1 (2026-11-03, astraeus fc5b)

Baseline `astraeus-fc5b` (main 1fe4a9f2's astraeus, = fc4's m4). The merged bot is `astraeus-fc5-m1`: CHANGES 308-310,
all fuel only. 308 floors the farm loop's own-group prunes at a crew share's value. 309 skips non-help groups once a
help call is set. 310 has the strike search's step guard reuse its cover's first pass. Review, worker numbers and
the dropped farm variants (banking floor, seeded order) are in hyperion/fuel-campaign-5/NOTES.md ("Farm loop",
"Fight-side round 2", "Merge round 1"). Benches are `MAIN/replays/fuel/fc5/m1-*.json`. At 100M all 234 replays are
identical. Total fuel moved -1.06% to -2.18% by set, -0.44% on fight and +0.59% on fs (codegen). Turns over 100k fell
on seven sets.

A/B, real budget, own drafts, fast runner, fresh-11000..11019, 10,240 games each (OOF per bot):

| run | win % (95% CI) | OOF cand / ref | r1 | 2-10 | 11-60 | 61-300 | 300+ | runs <10 / 10-49 / 50+ | fuel mean / p90 / p99 |
|---|---|---|---|---|---|---|---|---|---|
| mirror (fc5b) | 50 | 58,518 | | | | | | | 49,924 / 86,150 / 92,450 |
| 308 alone | 50.5 (49.5-51.4) | 59,690 / 59,616 | | | | | | | 49,336 / 86,150 / 92,250 |
| 308+309 | 50.5 (49.5-51.5) | 59,359 / 59,441 | 4,029 | 6,201 | 9,293 | 13,359 | 26,477 | 37,929 / 18,927 / 2,503 | 49,204 / 86,050 / 92,250 |
| 310 alone | 49.8 (48.8-50.7) | 59,268 / 58,954 | 4,062 | 6,589 | 9,170 | 12,920 | 26,527 | | |
| **m1 (308-310)** | **50.1 (49.1-51.0)** | **60,117 / 60,007** | 4,020 | 6,228 | 9,191 | 13,472 | 27,206 | 37,685 / 18,516 / 3,916 | 49,179 / 86,050 / 92,250 |

OOF is level. Shortcuts without out-of-fuel fell 3.05M -> 2.60M (-14.8%):
- farm-partial-evaluation -20.0% (2.06M -> 1.65M);
- ward-no-bushes-clusters -20.3%;
- crow-flies-farm -8.6%;
- step-guard-sim -10.5%;
- step-guard-look -4.5%.

Fuel a play turn: mean -1.5%, p50 -2.5%. The cheaper farm loop doesn't turn into fewer OOF turns. A cut loop
keeps its reserve, so the turns it now finishes were mostly within budget already, and 45% of OOF is in rounds 300+.

Runs of 50+ rose by 1.1k. Of that, 711 OOF turns are one deterministic runaway: gen-rivers-1100302130 (order 21),
where a banking champion's every decide overruns from round 579. 308 alone reproduces it and fc5b doesn't. 308 is
inert while banking, so 308 only diverges the game into that state; the stack is not found yet.

## Fuel campaign 5, round 2 (2026-11-03, astraeus fc5-m1)

The merged bot is `astraeus-fc5-m2`: m1 plus CHANGES 311-313, all fuel only. 311 finds the strike search's landing
classes by one partition. 312 has label_through test for a labelled tile in its reach before walking a line of
allies. 313 keeps three spare failed route searches. fc5-budget's turn-order reserve (12k with an enemy within 6) was
reverted on its branch: -1.2% OOF on fresh-110xx but +0.0% on an unused suite, and turn-order firings +25%. Review,
worker numbers and dropped attempts: hyperion/fuel-campaign-5/NOTES.md ("Fight unit costs", "Economy-side OOF",
"Fight-turn budget", "Merge round 2"). At 100M all 234 replays are identical to fc5b's and m1's. Against m1, total
fuel moved -0.12% (q) to +0.10% (big), from 313's lookups.

A/B, real budget, own drafts, fast runner, fresh-11000..11019, 10,240 games each (OOF per bot):

| run | win % (95% CI) | OOF cand / ref | r1 | 2-10 | 11-60 | 61-300 | 300+ | runs <10 / 10-49 / 50+ | fuel mean / p90 / p99 |
|---|---|---|---|---|---|---|---|---|---|
| 311 vs m1 | 50.1 (49.1-51.1) | 56,103 / 57,961 | | 6,243 / 6,239 | 8,782 / 8,900 | 12,783 / 13,072 | 24,277 / 25,732 | | |
| 312 vs m1 | 49.9 | 56,876 / 56,429 | | | | | | 2,200 / 1,747 (50+) | |
| 312+313 vs m1 | 49.7 | 57,669 / 58,940 | 4,178 / 4,019 | 6,289 / 6,228 | 8,897 / 9,007 | 13,259 / 13,054 | 25,046 / 26,632 | 2,395 / 4,318 (50+) | |
| fc5-budget reserve 12k vs m1 (reverted) | 49.8 | 57,013 / 57,702 | | | | | 25,090 / 25,812 | | |
| **m2 vs fc5b** | **50.7 (49.8-51.7)** | **57,920 / 59,731** | 4,178 / 4,035 | 6,268 / 6,564 | 9,030 / 9,277 | 13,113 / 13,134 | 25,331 / 26,721 | 37,358 / 17,678 / 2,884 vs 37,965 / 18,900 / 2,866 | 49,229 / 86,050 / 92,250 vs 49,918 / 86,150 / 92,450 |

On fresh-10100..10119, 312 read -1.8% and 312+313 -0.9% against m1.

- m2's out-of-fuel turns are -3.0% against fc5b (without shared-gems maps 55,133 / 56,737, -2.8%), the campaign's
  first drop beyond the ~1k run noise. It falls in every bucket from round 2 on: rounds 300+ -5.2%, 2-10 -4.5%.
  Round 1 is +143 (+3.5%). The 312+313 A/B read the same +159. At 100M, m2's round-1 mean is +0.2-0.6% over m1's on
  seven sets, likely 313's lookups.
- Shortcuts without out-of-fuel: 2.60M against 3.04M (-14.5%), as m1. farm-partial-evaluation 1,653,290 / 2,059,860;
  step-guard-sim 4,703 / 5,734; static-descend 16,951 / 18,981.
- Runs of 50+ are level: 2,884 / 2,866. m1 had read 3,916 / 2,820.
- Still far from the campaign target of 40,960. Every unit of the fight tail is near its floor (fc5-fight2), and
  85% of near-enemy OOF turns pass no fuel check after `act()` starts (fc5-budget). What is left needs the work
  itself bounded.

## Fuel campaign 5, round 3 and summary (2026-11-03, astraeus fc5-m2)

The merged bot is `astraeus-fc5-m3`: m2 plus CHANGES 314-320, all fuel only. 314-317 are exact early exits in
Safety's sums: retreat's untouched tests, retreat_step's ranking, Willow's threat test and only_threat. 318 moves
313's spare lookup out of line, and 319 memoises label_through's line walks. 320 has farm's takeover pass ask its
walk-independent tests before building a group's walk field. Also merged: the tool-speed branch (fast runner PGO
builds and the like, tooling only, no bot change). Review, worker numbers and dropped attempts:
hyperion/fuel-campaign-5/NOTES.md ("Unread work on near turns", "Early exits", "Pathing follow-ups", "Economy early
exits", "Merge round 3"). At 100M all 234 replays are identical to fc5b's and m2's. Against m2, total fuel fell
0.08-1.00% on every set, and turns over 100k fell on six of eight.

A/B, real budget, own drafts, fast runner, 10,240 games each (OOF per bot, cand / ref):

| run | suites | win % (95% CI) | OOF cand / ref | r1 | 2-10 | 11-60 | 61-300 | 300+ | runs <10 / 10-49 / 50+ |
|---|---|---|---|---|---|---|---|---|---|
| 314 vs m1 | fresh-110xx | 49.8 (48.9-50.8) | 54,809 / 57,749 (-5.1%) | | 6,221 / 6,242 | 8,551 / 9,018 | 12,162 / 12,945 | 23,857 / 25,526 | |
| 315-317 vs m2+314 | fresh-110xx | 50.1 | 53,758 / 54,074 (-0.6%) | | 6,247 / 6,265 | 8,392 / 8,506 | 11,817 / 11,921 | 23,125 / 23,205 | |
| 318 vs m2 | fresh-110xx | 50.1 (49.2-51.1) | 56,568 / 55,792 (+1.4%) | 4,145 / 4,176 | | | | | 1,643 / 1,258 (50+) |
| 319 vs m2 | fresh-110xx | 50.6 (49.6-51.5) | 56,098 / 56,515 (-0.7%) | 4,128 / 4,177 | | | | 23,992 / 24,501 | |
| 320 (first commit) vs m2 | fresh-110xx | 50.2 (49.2-51.2) | 52,130 / 56,111 (-7.1%) | 4,175 / 4,177 | 5,960 / 6,288 | 7,378 / 8,860 | 11,668 / 12,913 | 22,949 / 23,873 | |
| m3 without 319 vs fc5b | fresh-110xx | 50.5 (49.5-51.4) | 50,874 / 59,181 (-14.0%) | 4,136 / 4,035 | 5,951 / 6,581 | 7,196 / 9,436 | 10,997 / 12,806 | 22,594 / 26,323 | 33,358 / 15,911 / 1,605 vs 37,837 / 19,447 / 1,897 |
| **m3 vs fc5b** | fresh-110xx | **50.4 (49.4-51.4)** | **50,627 / 58,754 (-13.8%)** | 4,132 / 4,035 | 5,872 / 6,575 | 7,205 / 9,426 | 11,100 / 12,822 | 22,318 / 25,896 | 33,406 / 15,301 / 1,920 vs 37,701 / 19,017 / 2,036 |
| **m3 vs fc5b** | fresh-520xx (new) | **50.2 (49.2-51.2)** | **51,067 / 57,039 (-10.5%)** | 3,596 / 3,541 | 5,536 / 6,049 | 7,006 / 8,963 | 10,256 / 12,407 | 24,673 / 26,079 | 32,164 / 16,237 / 2,666 vs 36,304 / 18,977 / 1,759 |

- m3 has 13.8% fewer out-of-fuel turns than fc5b, and 10.5% fewer on suites no campaign A/B had used. Without
  shared-gems maps: 48,663 / 56,495 and 48,869 / 54,631. Most of the drop is 320 (-7.1% alone, rounds 11-60 -17%)
  and 314 (-5.1%, rounds 300+ -6.5%). Each removes one heavy piece of work on turns that were just over budget: a
  ~15k field build and a retreat's blow pricing.
- Fuel a play turn, m3 / fc5b: mean 49,139 / 49,907, p50 47,150 / 48,350, p90 86,050 / 86,150, p99 91,850 /
  92,450, at/over 100k 0.21% / 0.22%. On fresh-520xx: 48,947 / 49,651, p90 86,050 / 86,150, p99 91,850 / 92,350.
- Shortcuts without out-of-fuel: 2.56M against 3.04M (-15.7%). farm-partial-evaluation 1,655,573 / 2,055,215,
  farm-no-route 32,706 / 48,950 (-33%), comms-stale-vision 44,463 / 53,474, turn-order 99,219 / 114,539,
  ward-no-bushes-clusters 40,757 / 51,324, step-guard-entry 420,003 / 437,357. On fresh-520xx: 2.53M against 2.98M (-15.1%).
- Round 1 is +97 (+2.4%) and +55 (+1.6%) on the two suites, as in m2 (+143).
- Runs of 50+ are level on fresh-110xx (1,920 / 2,036) but up on fresh-520xx (2,666 / 1,759): runaway games move
  from suite to suite (round 1's rivers-1100302130 kind). Not traced.
- 319 kept: m3 without it reads 50,874 / 59,181, level with m3. At 100M it costs oof and mg p99 +0.7% / +1.0% (one
  map's store cost) but cuts q's turns over 100k by 779 (net -640 over oof, mg, q, big and fs).
- The campaign target was -30% (40,960 against the mirror's 58,518). m3 reaches 50.6k: -13.8% against its
  same-run reference, -13.5% against the mirror.

Campaign 5 against fc5b (fresh-11000..11019, 10,240 games each):

| bot | win % | OOF | r1 / 2-10 / 11-60 / 61-300 / 300+ | runs <10 / 10-49 / 50+ | fuel mean / p90 / p99 | >= 100k | shortcuts (no OOF) |
|---|---|---|---|---|---|---|---|
| fc5b mirror | 50 | 58,518 | | | 49,924 / 86,150 / 92,450 | 0.22% | 3.05M |
| m1 (308-310) | 50.1 | 60,117 / 60,007 (+0.2%) | 4,020 / 6,228 / 9,191 / 13,472 / 27,206 | 37,685 / 18,516 / 3,916 | 49,179 / 86,050 / 92,250 | 0.23% | 2.60M (-14.8%) |
| m2 (+311-313) | 50.7 | 57,920 / 59,731 (-3.0%) | 4,178 / 6,268 / 9,030 / 13,113 / 25,331 | 37,358 / 17,678 / 2,884 | 49,229 / 86,050 / 92,250 | 0.22% | 2.60M (-14.5%) |
| **m3 (+314-320)** | **50.4** | **50,627 / 58,754 (-13.8%)** | 4,132 / 5,872 / 7,205 / 11,100 / 22,318 | 33,406 / 15,301 / 1,920 | 49,139 / 86,050 / 91,850 | 0.21% | 2.56M (-15.7%) |

## Fuel campaign 6, round 1 (2026-11-04, astraeus fc6-m1)

Baseline `astraeus-d6e74b6` (d6e74b6f, CHANGES 337; the campaign's goal is to undo 337's out-of-fuel cost). The merged
bot is `fc6-m1`: CHANGES 338-342, from two workers (hyperion/fuel-campaign-6/NOTES.md `## veto`, `## econ`). 338-341
are fuel only; 342 (farm's loop reserves the veto's measured cost) changes play only at the real budget. Benches are
`MAIN/replays/fuel/fc6/m1-*.json`. At 100M all 322 replays on the nine sets (wide oof mg q big fs fight tgt osc) and the
16-game default bench are identical. Total fuel -0.24% (fs) to -0.80% (osc); mean -0.2 to -0.8%; p99 -0.2 to -1.4%;
turns over 100k 136,541 -> 133,867 (-2.0%); round-1 mean -1.0 to -2.7%, p99 -1.3 to -5.4%. Round 2's mean rose
+0.5 to +1.6% on every set: 340 moves ~2k of round 1's caches there (round 1 + 2 together unchanged on econ's own
bench). Real-budget benches, summed over the nine sets: OOF 34,374 -> 30,504; round-1 turns at the 200k cap 756 -> 633;
shortcuts without OOF 343,854 -> 352,632.

A/B, real budget, own drafts, fast runner, 10,240 games each (OOF per bot, `batch_oof.py` skipping shared-gems maps for
the buckets):

| run | win % (95% CI) | OOF cand / ref | r1 | 2-10 | 11-60 | 61-300 | 300+ | runs <10 / 10-49 / 50+ | fuel mean / p90 / p99 / >=100k |
|---|---|---|---|---|---|---|---|---|---|
| veto tip (338-339), fresh-66101..66120 | 50.2 (49.3-51.2) | 198,559 / 224,498 | | | | | | | 52,516 / - / - / 0.50% vs 52,876 / 0.55% |
| econ tip (340-342), fresh-66101..66120 | 50.4 (49.4-51.3) | 205,538 / 222,406 | 13,303 / 17,320 | | | | | | 52,882 / - / 96,150 / 0.52% vs 52,866 / 96,550 / 0.54% |
| **m1, fresh-66201..66220** | **49.1 (48.2-50.1)** | **196,967 / 237,559** | 11,829 / 16,922 | 11,880 / 15,726 | 18,183 / 20,763 | 46,032 / 55,059 | 103,947 / 122,736 | 19,676 / 76,413 / 95,782 vs 18,801 / 90,125 / 122,280 | 52,495 / 86,650 / 96,050 / 0.50% vs 52,853 / 86,750 / 96,650 / 0.57% |
| m1, unused suites (mapgen seeds 66701..66720) | 49.7 (48.7-50.6) | 202,235 / 246,397 | | | | | | | 52,625 / 86,650 / 96,150 / 0.51% vs 52,922 / 86,750 / 96,750 / 0.59% |

- Win rate over both m1 runs: 49.4% (48.7-50.1) of 20,480. Level, at the low edge; the workers' tips read 50.2 and
  50.4 on other suites.
- Out-of-fuel turns -17.1% and -17.9%, every round bucket down: round 1 -30%, runaway games (50+) -22%. Round 2
  alone is level (4,364 / 4,456), so 340's shift into round 2 doesn't run turns out. Still far from the campaign's
  -50% target (d6e74b6f against 088bf3f4 was 458,674 / 111,324 in 20k games).
- Shortcuts without OOF 4.13M / 4.02M (+2.9%): farm-partial-evaluation 2.70M / 2.44M (+10.8%, 342 stops the loop
  earlier to keep the veto's reserve); turn-order 307k / 378k (-19%), comms-stale-vision 107k / 144k (-26%),
  farm-no-route 52k / 76k (-32%), prey-cut-short 141k / 148k, step-guard-entry 582k / 594k.

## Fuel campaign 6, round 2 (2026-11-04, astraeus fc6-m2)

Baseline `fc6-m1` (CHANGES 338-342). The merged bot is `fc6-m2`: CHANGES 343-345, from the runaway worker
(hyperion/fuel-campaign-6/NOTES.md `## runaway`); its code equals the worker's A/B tip (rw-d), so that A/B is the
round's. 343-344 are fuel only; 345 (farm reserves the veto's unmeasured first ask) changes play only at the real budget.
Benches are `MAIN/replays/fuel/fc6/m2-*.json`. At 100M all 322 replays on the nine sets and the 16-game default bench
are identical to m1's. Total fuel +0.00% (fs) to +0.03% (big), q -0.19%, osc -0.04%; most turns are ~10-20 fuel
dearer (the field ids). Mean, p99 and turns over 100k level (133,867 -> 133,953); round-1 mean +17 to +96 fuel a set;
round-2 mean level (+0.02% at most). Real-budget benches, summed over the nine sets: OOF 30,504 -> 30,775 (noise);
round-1 turns at the 200k cap 633 -> 490.

A/B, real budget, own drafts, fast runner, 10,240 games (OOF per bot, `batch_oof.py` skipping shared-gems maps for the
buckets):

| run | win % (95% CI) | OOF cand / ref | r1 | 2-10 | 11-60 | 61-300 | 300+ | runs <10 / 10-49 / 50+ | fuel mean / p90 / p99 / >=100k |
|---|---|---|---|---|---|---|---|---|---|
| rw-a (343-344) vs fc6-m1, fresh-66301..66320 | 49.9 | 204,352 / 204,991 | 11,808 / 11,797 | | | | | | |
| **rw-d = m2 vs fc6-m1, fresh-66301..66320** | **49.9 (49.0-50.9)** | **200,640 / 203,481** | 7,479 / 11,798 | 12,714 / 11,716 | 18,809 / 18,453 | 47,993 / 48,072 | 109,048 / 108,880 | 18,950 / 75,199 / 101,894 vs 19,767 / 76,626 / 102,526 | 52,433 / 86,650 / 96,150 / 0.51% vs 52,481 / 86,650 / 96,050 / 0.51% |

- Level. Out-of-fuel turns -1.4%, nearly all of it 345's round 1 (-37%); about 1k of it reappears in rounds 2-10
  (+8.5%). 343-344 alone are level on OOF: the corridor jams they cut (label_through 13.2k -> 7.3k a turn, route
  38k -> 33.6k on topo-shortcut-6621506918) are too few to show in 10k games.
- Bank-branch (B) OOF turns 10,979 / 8,666, first-in-streak in 300+ 4,705 / 1,795, mostly one map
  (gen-arena-6631702600, 2,412 first-in-streak for m2, not in m1's top 25): a diverged game's bank runaway.
- Shortcuts without OOF 4.48M / 4.44M (farm-partial-evaluation 2.77M / 2.74M).
- The stand worker (NOTES `## stand`) shipped nothing: settle bounds that end the fight sim early (our side falls
  weakest first; their least damage fells us before ours fells their weakest) gave identical replays at 100M, but every
  form cost more than it saved: AB +0.62% / +0.71% total on fight / osc, ABC +1.40% / +1.55%, t=0 only +0.12% /
  +0.15%, gated off want_home's tile +0.03% / +0.03%. A check costs 225-1.2k and fires too rarely against the 1.3-3k
  sim it settles. Last form: `hyperion/fuel-campaign-6/stand-settled-s5.diff`.

## Fuel campaign 6, round 3 (2026-11-04, astraeus fc6-m3)

Baseline `fc6-m2` (CHANGES 338-345). The merged bot is `fc6-m3`: CHANGES 346-349, from two workers
(hyperion/fuel-campaign-6/NOTES.md `## share`, `## tail`); its code equals the two workers' tips together. 346-347 are
fuel only; 348-349 (the walk sites' and prey's reserves keep back the work veto's ask) change play only at the real
budget. Benches are `MAIN/replays/fuel/fc6/m3-*.json`. At 100M all 322 replays on the nine sets and the 16-game default
bench are identical to m2's. Total fuel -0.06% (fs) to -0.47% (fight), osc -0.45%, oof -0.33%; mean -0.1 to -0.5%;
p99 -0.1 to -1.0% (fight, osc -0.9%); turns over 100k 133,953 -> 132,016 (-1.4%); round-1 mean -0.1 to -0.4%; round-2
mean -0.0 to -0.2%. Dearer: fight's max turn 368,355 -> 382,179 (347: where our tile leaves too, both stands run).
Real-budget benches, summed over the nine sets: OOF 30,775 -> 25,666 (-16.6%; osc 13,260 -> 10,416, fight 3,160 ->
2,323, tgt 2,428 -> 1,998); round-1 turns at the 200k cap 490 -> 481; shortcuts without OOF 354k -> 361k
(prey-cut-short 24.4k -> 35.1k, static-descend 8.7k -> 13.9k, farm-no-route 7.1k -> 10.6k).

A/B, real budget, own drafts, fast runner (OOF per bot, `batch_oof.py` skipping shared-gems maps for the buckets):

| run | win % (95% CI) | OOF cand / ref | r1 | 2-10 | 11-60 | 61-300 | 300+ | runs <10 / 10-49 / 50+ | fuel mean / p90 / p99 / >=100k |
|---|---|---|---|---|---|---|---|---|---|
| sh-a (346) vs fc6-m2, fresh-67201..67220, 10,240 | 50.2 (49.2-51.2) | 182,662 / 192,005 | 7,514 / 7,514 | 12,651 / 12,651 | 16,843 / 17,427 | 42,247 / 44,802 | 99,503 / 105,618 | - / - / 89,080 vs - / - / 96,294 | 52,326 / - / 95,850 / 0.47% vs 52,377 / - / 95,950 / 0.49% |
| tail-b (347-348) vs 347 alone, fresh-67101..67120, 10,240 | 50.3 (49.3-51.2) | 186,121 / 199,598 | | | | | | | |
| tail-c (347-349) vs 347-348, fresh-67101..67120, 10,240 | 50.0 (49.0-50.9) | 174,098 / 189,695 | | | | | | | |
| tail-d (347-349) vs fc6-m2, fresh-67101..67120, 10,240 | 50.4 (49.4-51.3) | 174,323 / 201,647 | 6,512 / 6,954 | 11,345 / 12,123 | 16,785 / 18,940 | 39,245 / 47,016 | 95,862 / 111,290 | 19,235 / 68,065 / 82,449 vs 18,928 / 72,978 / 104,417 | 52,264 / 86,550 / 95,650 / 0.46% vs 52,344 / 86,650 / 96,050 / 0.51% |
| **m3 vs d6e74b6f, fresh-67301..67340 (unused), 20,480** | **49.9 (49.2-50.6)** | **329,711 / 484,858** | 14,391 / 33,900 | 24,383 / 31,571 | 31,924 / 41,130 | 75,034 / 112,131 | 175,352 / 253,716 | 40,115 / 131,237 / 149,732 vs 38,387 / 177,157 / 256,904 | 52,383 / 86,650 / 95,650 / 0.44% vs 52,850 / 86,750 / 96,750 / 0.59% |

- **The campaign so far (338-349) at scale: out-of-fuel turns -32.0%** against d6e74b6f (target -50%; 337 against its
  parent was 458,674 / 111,324). Win rate level: 10,220-10,260, suites 43.8 / 50.4 / 54.7 (min / median / max).
  Round 1 -58% (all farm branch: F 13,702 / 33,210 first-in-streak), games with 50+ out-of-fuel turns -42%, 300+
  -31%, 61-300 -33%, 2-10 and 11-60 -22%. Fuel a play turn p50 51,650 / 52,150.
- First-in-streak OOF 272,777 / 397,936; phase decide 87% / 82%, queue 13% / 18%; ending before the turn's branch line
  (`?`) 85% / 81%: the no-check fight work (tail's open lead) is now most of what is left.
- Worst maps differ: m3's top two are gen-topo-capital-6732207401 (2,565 first-in-streak, ref 700) and
  gen-cluster-carpets-6730308807 (1,815, not in the ref's top 25): diverged games' runaways.
- Shortcuts without OOF 8.65M / 8.16M (+6.0%): farm-partial-evaluation 5.50M / 4.95M (+11%), prey-cut-short
  470k / 315k (+49%, 349), static-descend 241k / 145k (+66%, 348), farm-no-route 182k / 156k (+17%), crow-flies-farm
  42.8k / 28.6k; turn-order 533k / 767k (-30%), comms-stale-vision 185k / 293k (-37%), step-guard-entry 1.18M / 1.21M.
- Dropped this round (numbers in NOTES): tail's farm-loop cold-pass reserve (a1 48.7%, a2 48.3%, a3 49.8% with OOF
  -0.7%) and the walk sites keeping back the veto's whole turn (49.6%, OOF -1.9% against the tip); share's cross-turn
  Reach and distance memos (~460 and ~250 a heavy turn at most, not built).

## Fuel campaign 6, round 4 (2026-11-04, astraeus fc6-m4b)

Baseline `fc6-m3` (CHANGES 346-349). Two workers (hyperion/fuel-campaign-6/NOTES.md `## big`, `## fight`). Shipped:
CHANGES 350-351 (big, fuel only), frozen as `fc6-m4b`. Not shipped: fight's a28721f3 (the post-strike work veto
refuses a step more exposed than our tile without the stand; `fc6-m4` = 350-351 plus it): its 20k run against
d6e74b6f lost (49.0%, CI below 50) and it brought back the wasted turns CHANGES 337 removed (table below).

Benches are `MAIN/replays/fuel/fc6/m4b-*.json` and `m4-*.json`. At 100M all 322 m4b replays on the nine sets, the
16-game default bench and the big worker's 16-map topology set (32 games) are identical to m3's. Total fuel -0.05% (q),
others within 0.001%; turns over 100k 132,022 -> 132,016; round-1 mean q 316,405 -> 285,754 (-9.7%), other sets within
0.05%; round-2 mean level on every set. Real-budget benches, summed over the nine sets: OOF 25,666 -> 25,195 (q 3,728
-> 3,241, others within 8); shortcuts without OOF 361.2k -> 359.7k. m4 (with the fight change) diverges at 100M
wherever it fires: real-budget OOF 22,744 (osc 10,416 -> 8,852, fight 2,323 -> 1,927, tgt 1,998 -> 1,671, oof 3,383 ->
3,013), shortcuts without OOF 375.2k (step-guard-entry 68.8k -> 78.7k).

A/B, real budget, own drafts, fast runner (OOF per bot, `batch_oof.py` skipping shared-gems maps for the buckets, all
OOF turns):

| run | win % (95% CI) | OOF cand / ref | r1 | 2-10 | 11-60 | 61-300 | 300+ | games <10 / 10-49 / 50+ | fuel mean / p50 / p90 / p99 / >=100k |
|---|---|---|---|---|---|---|---|---|---|
| big-b3 (350-351) vs fc6-m3, fresh-67501..67520, 10,240 | 49.9 (48.9-50.9) | 158,146 / 157,878 | 7,030 / 7,112 | | | | | | 52,398 / 51,650 / 86,650 / 95,450 / 0.43% vs 52,393 / 51,650 / 86,650 / 95,450 / 0.43% |
| fight-p1 (a28721f3) vs fc6-m3, fresh-67401..67420, 10,240 | 49.6 (48.6-50.5) | 155,180 / 173,477 | | | | | | | >=100k 0.42% vs 0.46% |
| m4 vs d6e74b6f, fresh-67601..67640, 20,480 | 49.0 (48.3-49.7) | 289,789 / 484,818 | 14,211 / 34,484 | 23,679 / 31,201 | 27,159 / 38,844 | 64,661 / 112,048 | 151,591 / 253,975 | 40,162 / 129,807 / 111,332 vs 38,064 / 180,713 / 251,775 | 52,568 / 51,850 / 86,650 / 95,350 / 0.40% vs 52,988 / 52,250 / 86,750 / 96,750 / 0.59% |
| m4 vs m4b, fresh-67601..67640, 20,480 | 49.7 (49.0-50.4) | 296,617 / 334,579 | | | | | | | |
| **m4b vs d6e74b6f, fresh-67601..67640 (unused), 20,480** | **49.5 (48.8-50.2)** | **311,551 / 462,889** | 14,208 / 34,485 | 23,770 / 31,191 | 29,644 / 37,997 | 70,871 / 106,369 | 163,710 / 239,568 | 39,643 / 131,921 / 130,639 vs 38,238 / 181,247 / 230,125 | 52,412 / 51,650 / 86,650 / 95,450 / 0.42% vs 52,859 / 52,150 / 86,750 / 96,650 / 0.56% |

- **The campaign so far (338-351) at scale: out-of-fuel turns -32.7%** against d6e74b6f (round 3's m3: -32.0% on other
  suites). 350-351 cut round 1 on topology maps, ~2% of the fresh suites: at scale they are level, as their worker's
  A/B. Win rate level: 10,131-10,349, suites 45.1 / 49.3 / 52.5 (min / median / max). Round 1 -59%, games with 50+
  out-of-fuel turns -43%, 300+ -32%, 61-300 -33%. First-in-streak 257,092 / 379,859; phase decide 87% / 82%; ending
  before the turn's branch line (`?`) 86% / 81%. Shortcuts without OOF 8.45M / 8.00M (+5.6%): farm-partial-evaluation
  5.44M / 4.91M, prey-cut-short 427k / 284k, static-descend 237k / 142k; turn-order 517k / 747k, comms-stale-vision
  181k / 288k, step-guard-entry 1.11M / 1.15M.
- The reference's OOF differs between the two 20k runs on the same maps (462,889 / 484,818): games diverge, so compare
  OOF only within a run.
- **The fight change's gameplay check** (`tools/replay/osc_detect.py`, traced copies of fc6-m3, fc6-m4b and fc6-m4:
  the d6e74b6f trace hooks, `osc-int-trace`'s diff, against `baselines/v69`, `CAMBC_LOG_LIMIT=16000000`). Episode
  turns by kind; m4b is fuel only, so its column is the noise floor:

  | kind | d6e74b6f, gen + gen-s1 (1,024) | m3 | m4b | m4 | m4 vs m4b | m3, fresh-67601..67604 (2,048) | m4b | m4 | m4 vs m4b |
  |---|---|---|---|---|---|---|---|---|---|
  | claimflip | 421,825 | 437,613 | 436,657 | 439,271 | +0.6% | 874,349 | 874,455 | 884,697 | +1.2% |
  | retreatchurn | 293,502 | 320,930 | 321,861 | 320,486 | -0.4% | 595,995 | 595,110 | 622,420 | +4.6% |
  | goalflip | 216,186 | 225,056 | 224,859 | 226,779 | +0.9% | 416,804 | 416,782 | 428,518 | +2.8% |
  | branchflip | 134,129 | 139,162 | 138,785 | 137,390 | -1.0% | 254,499 | 254,085 | 261,593 | +3.0% |
  | wander | 47,815 | 49,562 | 49,576 | 50,427 | +1.7% | 87,532 | 87,524 | 96,628 | +10.4% |
  | stuck_idle | 35,414 | 38,879 | 39,465 | 39,408 | -0.1% | 75,665 | 75,759 | 72,324 | -4.5% |
  | stuck_fail | 20,540 | 19,941 | 23,199 | 23,330 | +0.6% | 35,923 | 35,765 | 44,473 | +24.3% |
  | pingpong | 21,492 | 19,795 | 19,867 | 21,424 | +7.8% | 36,617 | 36,724 | 41,807 | +13.8% |
  | jitter | 19,905 | 16,123 | 16,241 | 16,890 | +4.0% | 31,159 | 31,435 | 35,477 | +12.9% |
  | preyflip | 3,969 | 3,930 | 3,821 | 3,575 | -6.4% | 6,268 | 6,378 | 6,664 | +4.5% |
  | all | 1,214,777 | 1,270,991 | 1,274,331 | 1,278,980 | +0.4% | 2,414,811 | 2,414,017 | 2,494,601 | +3.3% |

  m4b's total moves 0.3% at most and its kinds 2% at most on 2,048 games (gen + gen-s1's stuck_fail +16% is a few
  games: small kinds are noisy on 1,024). On 2,048 m4 raises every kind but stuck_idle, most the ones 337 cut
  (pingpong, jitter, stuck_fail, wander), with `veto` the leading reason more often (pingpong episodes tagged veto 1,571 -> 4,226
  on gen + gen-s1). A refused step keeps the champion on a tile it then leaves or walks back to: the refusals the stand
  would not have made are wasted turns. Traced at the real budget (debug builds), so fuel-gated choices differ from
  the untraced bots'.
- The traced m3 shows more episode turns than d6e74b6f on gen + gen-s1 (+4.6%; retreatchurn +9%): the campaign's
  real-budget changes (reserves that skip searches) have play effects of their own. Not checked further.
- **This table is unbridged** (`osc_detect.py` without `--bridge-oof`, added in round 5): it split a champion's run at
  every OOF turn, so bots with fewer OOF turns read as more episodes (d6e74b6f -> m3 +4.6% is +0.7% bridged). Round 5
  re-judged the fight change bridged.

## Fuel campaign 6, round 5 (2026-11-04, astraeus fc6-m5b)

Baseline `fc6-m4b` (CHANGES 350-351). Two workers (hyperion/fuel-campaign-6/NOTES.md `## exact`, `## audit`). Shipped:
CHANGES 352 (exact's walk-only strike search, fuel only) and 353 (audit's fix to 345's opening livelock, real budget
only), frozen as `fc6-m5b`; also the audit's tools (`osc_detect.py --bridge-oof`, `tools/replay/osc_compare.py`,
`hyperion/fuel-campaign-6/trace.patch`). Not shipped: exact's bf8df313 (lazy stand walkers, fuel only) and round 4's
a28721f3 (the post-strike veto refusal), both below level at 20k. `fc6-m5` is the full merge (exact's two commits plus
the fix), `fc6-m5f` is fc6-m5 plus a28721f3.

Workers' A/Bs against fc6-m4b (10,240 games each): exact (both commits, fresh-67801..67820) 49.6% (48.6-50.5), OOF
159,429 / 160,537 (-0.7%); audit's fix (fresh-67701..67720) 49.9% (48.9-50.9), OOF 153,565 / 153,359, round 1 7,853 /
6,954. Exact is byte-identical at 100M on the nine sets plus 75 census maps (150 games); the fix on 4,096 traced games.

**Identity.** At 100M all 322 fc6-m5b replays on the nine sets and the 16-game default bench are identical to fc6-m3's
(= m4b's). Total fuel fight -0.21%, osc -0.21%, oof -0.13%, others -0.06 to +0.00%; p90 osc 95,077 -> 94,757, others
within 0.2%; p99 within 0.4%; max level; turns over 100k 132,016 -> 131,239; round 1 and round 2 means level (within
0.01%). The fix as the worker wrote it (the first ask added at the reserve's return) made every set dearer at 100M
(fs +0.45% total, turns over 100k 25,313 -> 25,938): farm_turn is flattened. Added inside the per-group reserve
(same sum), fs is +0.00% against exact alone. Real-budget benches summed over the nine sets (indicative): OOF 25,195
-> 26,056, shortcuts without OOF 359.7k -> 362.5k. Also identical at 100M: fc6-m5 (full merge), and exact alone against
m4b on 4,096 games of the 20k suites (fresh-67921..67928, every outcome the same).

**The audit's attribution** (traced copies against `baselines/v69`, fresh-67701..67720, 10,240 games, bridged
detector, `all+oof` = episode turns plus OOF turns): main (m4b) vs d6e74b6f +1.4% (+0.2..+2.5) with OOF -33.5%;
reverting each reserve from main: 342+345 -1.43% (-2.39..-0.49), 345 alone -0.73% (-1.38..-0.09: the livelock), 342
alone -0.70% (-1.60..+0.17), 348 +0.37% (-0.53..+1.30), 349 +0.19% (-0.56..+0.96). At 100M d6e74b6f, main and every
revert give identical episode counts. main + fix vs main -0.63% (-1.14..-0.11); vs d6e74b6f +0.8% (-0.3..+1.8). The
detector without `--bridge-oof` splits a champion's run at every OOF turn (the D line is missing), so a bot with fewer
OOF turns showed more episodes: round 4's d6e74b6f -> m3 +4.6% is +0.7% bridged.

**The fight re-judgement** (a28721f3). Traced copies (trace.patch) of fc6-m5 and fc6-m5f against `baselines/v69` on
the same 10,240 games (fresh-67901..67920, own drafts, real budget, `CAMBC_LOG_LIMIT=16000000`), `osc_detect.py
--bridge-oof`, `osc_compare.py` (CI: bootstrap over games, paired by map and side):

| kind | m5 | m5f | m5f vs m5 (95% CI) |
|---|---|---|---|
| claimflip | 4,732,561 | 4,743,641 | +0.2% (-0.5..+1.1) |
| retreatchurn | 3,912,687 | 3,892,733 | -0.5% (-2.2..+1.2) |
| goalflip | 2,379,699 | 2,379,584 | -0.0% (-1.2..+1.2) |
| branchflip | 1,486,315 | 1,481,296 | -0.3% (-1.9..+1.3) |
| wander | 520,257 | 544,302 | **+4.6% (+2.0..+7.3)** |
| stuck_idle | 310,090 | 301,997 | -2.6% (-8.6..+3.3) |
| stuck_fail | 212,712 | 218,550 | +2.7% (-5.5..+11.6) |
| pingpong | 204,456 | 214,315 | +4.8% (-1.5..+10.8) |
| jitter | 176,953 | 175,976 | -0.6% (-8.2..+6.9) |
| preyflip | 37,648 | 39,605 | +5.2% (-1.4..+12.7) |
| all | 13,973,378 | 13,991,999 | +0.13% (-0.81..+1.12) |
| OOF turns | 160,540 | 148,583 | -7.4% |
| **all+oof** | 14,133,918 | 14,140,582 | **+0.05% (-0.91..+1.02)** |

Episodes with a `veto` reason: pingpong 2,087 -> 3,679, wander 2,966 -> 4,847, stuck_fail 1,415 -> 2,035, jitter
1,714 -> 2,312, all kinds 120,427 -> 147,391. Bridged, the change's wasted turns are level in total (its extra
refusals, wander most, are paid for by fewer OOF turns), so it passed the gameplay check; round 4's +3.3% was mostly
the unbridged detector. It failed on win rate: against d6e74b6f at 20k, m5f 48.5% (47.8-49.2), and on the
shipped base (353 alone plus a28721f3) 49.1% (48.4-49.8), -0.58 points paired against 353 alone (-1.33..+0.18).
Not shipped (third reading at about -0.6).

**20k A/Bs against d6e74b6f** (own drafts, real budget, fast runner, the same 20,480 games for every row:
fresh-67921..67940 and fresh-66001..66020, unused before this round; fresh-66021..66040 stay reserved for the final
run). OOF per bot; buckets from `batch_oof.py` (shared-gems maps skipped); paired = per-game win difference against
fc6-m4b's run of the same games. The rows after m5b were chosen on these games, so they read optimistic:

| run | win % (95% CI) | suites min / med / max | paired vs m4b | OOF cand / ref | r1 | 2-10 | 11-60 | 61-300 | 300+ | games <10 / 10-49 / 50+ | fuel mean / p50 / p90 / p99 / >=100k |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fc6-m4b (control) | 49.7 (49.1-50.4) | 45.7 / 49.8 / 53.1 | | 326,728 / 485,601 | 13,897 / 33,934 | 23,207 / 30,765 | 31,431 / 40,827 | 73,765 / 110,626 | 175,964 / 257,691 | 39,857 / 129,550 / 148,857 vs 38,294 / 176,575 / 258,974 | 52,381 / 51,650 / 86,650 / 95,550 / 0.44% vs 52,826 / 52,150 / 86,750 / 96,750 / 0.59% |
| fc6-m5 (352 + bf8df313 + 353) | 48.9 (48.2-49.5) | 45.1 / 48.9 / 51.8 | -0.88 (-1.59..-0.16) | 330,557 / 486,096 | 15,670 / 33,934 | 21,987 / 30,725 | 31,852 / 40,969 | 76,435 / 113,044 | 175,743 / 255,350 | 40,082 / 132,732 / 148,873 vs 38,077 / 176,991 / 258,954 | 52,350 / 51,650 / 86,650 / 95,550 / 0.44% vs 52,850 / 52,150 / 86,750 / 96,750 / 0.59% |
| fc6-m5f (m5 + a28721f3) | 48.5 (47.8-49.2) | 45.5 / 48.5 / 52.3 | -1.21 (-2.02..-0.39); vs m5 -0.33 (-1.08..+0.42) | 307,094 / 510,979 | 15,683 / 33,934 | 21,922 / 30,733 | 28,611 / 41,441 | 68,826 / 119,346 | 164,399 / 273,282 | 40,454 / 129,987 / 129,000 vs 37,703 / 176,088 / 284,945 | 52,508 / 51,750 / 86,650 / 95,450 / 0.42% vs 52,985 / 52,250 / 86,750 / 96,850 / 0.61% |
| exact (352 + bf8df313) | 48.9 (48.2-49.5) | 44.1 / 49.0 / 51.8 | -0.87 (-1.57..-0.18) | 328,978 / 486,186 | | | | | | | |
| 352 alone | 49.9 (49.3-50.6) | 45.1 / 50.2 / 55.1 | +0.21 (-0.22..+0.63) | 322,170 / 487,825 | | | | | | | |
| bf8df313 alone | 49.0 (48.3-49.7) | 44.9 / 48.9 / 53.7 | -0.73 (-1.42..-0.04) | 331,402 / 486,967 | | | | | | | |
| 353 alone | 49.7 (49.0-50.3) | 45.5 / 49.6 / 53.5 | -0.07 (-0.33..+0.19) | 328,199 / 486,262 | | | | | | | |
| 353 + a28721f3 | 49.1 (48.4-49.8) | 45.1 / 49.0 / 53.9 | -0.65 (-1.43..+0.13) | 307,218 / 521,124 | | | | | | | |
| **fc6-m5b (352-353)** | **49.9 (49.2-50.6)** | 45.7 / 49.7 / 54.5 | +0.17 (-0.32..+0.65) | **322,838 / 487,656** | 15,958 / 33,933 | 22,045 / 30,751 | 31,184 / 40,881 | 72,958 / 111,487 | 171,965 / 258,067 | 39,675 / 129,911 / 144,524 vs 38,116 / 177,466 / 259,537 | 52,389 / 51,650 / 86,650 / 95,550 / 0.43% vs 52,833 / 52,150 / 86,750 / 96,750 / 0.59% |

- **The campaign so far (338-353) at scale: out-of-fuel turns -33.8%** against d6e74b6f (m4b on the same games
  -32.7%). Win rate level: 10,220-10,260. Round 1 -53%, games with 50+ OOF turns -44%, 300+ -33%, 61-300 -35%.
  First-in-streak 267,625 / 399,550. Shortcuts without OOF 8.50M / 8.11M: farm-partial-evaluation 5.35M / 4.87M,
  prey-cut-short 469k / 319k, static-descend 247k / 151k; turn-order 528k / 773k, comms-stale-vision 183k / 295k,
  step-guard-entry 1.17M / 1.23M.
- **bf8df313 is fuel only and still lost:** identical at 100M, but at the real budget it changed the winner of 5,203
  of 20,480 games against m4b's run (352 alone: 1,958) and raised OOF 1.4%. Its saving on the census turns
  (stand_lost_at's walks) did not show at scale. Not looked into further.
- 353 moves round 1 (13,897 -> 15,958 on m4b's games): the opening's first group is weighed without the first-ask
  reserve. It is level on win rate and total OOF, and removes the livelock.
- Real-budget games diverge even for fuel-only changes (exact vs m4b: 37% of games ended in the same round with the
  same winner), so the reference's OOF moves between runs of the same games (485,601 .. 521,124): compare OOF
  within a run, and win rates paired by game.

## Fuel campaign 6, round 6 (2026-11-04, astraeus fc6-m6)

Baseline `fc6-m5b` (CHANGES 352-353). Two workers (hyperion/fuel-campaign-6/NOTES.md `## init`, `## sides`). Shipped:
CHANGES 354-357 (init's four round-1 world-init cuts, all fuel only), frozen as `fc6-m6`. The sides worker shipped
nothing.

**Identity.** At 100M all 322 fc6-m6 replays on the nine sets and the 16-game default bench are identical to
fc6-m5b's (the worker also checked fsx: 20 fuel-stress and 8 huge maps, `replays/fuel/fc6/fsxset.txt`). Total fuel
fs -0.04%, others -0.00 to -0.01%; turns over 100k 131,239 -> 131,238; dearer turns are a few fuel each (codegen
outside init). Round 1 mean / p90 / max, round 2 mean (m5b -> m6, 100M):

| set | round 1 mean | p90 | max | round 2 mean |
|---|---|---|---|---|
| wide | 230,722 -> 229,264 | 293,373 -> 291,929 | 516,327 -> 512,730 | 110,766 -> 110,786 |
| oof | 251,258 -> 248,480 | 370,096 -> 361,216 | 452,654 -> 448,987 | 122,258 -> 122,203 |
| mg | 249,277 -> 246,859 | 330,809 -> 323,031 | 443,947 -> 436,169 | 122,041 -> 122,079 |
| q | 285,759 -> 283,534 | 430,224 -> 424,796 | 597,905 -> 587,306 | 147,668 -> 147,645 |
| big | 284,098 -> 281,330 | 383,215 -> 377,867 | 476,145 -> 472,502 | 160,048 -> 160,048 |
| fs | 607,449 -> 578,852 | 676,939 -> 644,275 | 742,515 -> 709,952 | 280,010 -> 280,010 |
| fight | 199,389 -> 198,717 | 213,237 -> 212,772 | 315,420 -> 310,589 | 91,312 -> 91,248 |
| tgt | 249,705 -> 248,186 | 297,667 -> 295,041 | 355,497 -> 352,871 | 114,946 -> 114,934 |
| osc | 205,798 -> 205,315 | 238,324 -> 236,377 | 319,989 -> 317,363 | 97,001 -> 97,035 |
| fsx (worker) | 504,993 -> 485,474 | 667,351 -> 636,331 | 799,727 -> 772,406 | 230,916 -> 230,916 |

Real budget, round-1 turns at the 200k cap (worker's benches): wide 31 -> 19 of 245, q 121 -> 113, mg 34 -> 32, others
level; fs 140 of 140 and fsx 290 of 318 still cap (a fs body's world init is ~201k after the cuts, ~229k before).

**A/B** (worker, `fc6init-a` = 354-357 vs fc6-m5b, fresh-68101..68120, 10,240 games): **49.5% (48.6-50.5)**. OOF
160,548 / 157,701 (+1.8%); batch_oof round 1 7,274 / 7,751 (-6%), 2-10 10,387 / 10,524, 11-60 15,395 / 15,440, 61-300
36,737 / 36,173, 300+ 85,857 / 82,871. The late excess is one game: gen-leaky-diagonals-6811007814 with init-a as A
runs 2000 rounds at ~1.4 OOF a round from round ~450 (2,165 OOF; m5b as A wins in 534 with 15), bodies overrunning
in step-guard / static-descend; without it OOF is +0.5%. The state is reachable from m5b's code (identical at 100M).
Fuel a turn mean 52,293 / 52,306, p90 86,550, p99 95,350. fsx both sides (56 games): OOF 3,039 / 3,098.

**Dropped** (init; numbers on fs): `camps.assign(n, prototype)` (+1.6k: memory.copy), writing camp_tiles' words
directly (+8.6k) or via a linear buffer (+3k), the new crossings form on every map (small maps regressed), reading
every camp type's stats before the member loop (fs -12k, small maps +2k), lazy altar steps (fs total +0.046%: the
per-call check costs more than round 1 saves), the spawn field for draft ally steps (changes play).

**Sides (null result).** The fight sides each stand builds (`new_fight`) and the blows behind them, measured on the
75 census maps against d6e74b6f. On OOF turns a `new_fight` is mostly the sim (8.5k) over setup (~4.1k: `make_slot`
~2k, almost all the turn's first use of each fighter). No sim repeats within a turn (0.03% of 435k sims by full
content key); across turns 6.5% repeat (5.6% of sim fuel), but a content key costs ~400-500 a sim against ~300-700
saved. `blow` repeats are already answered by `Reach::at`'s memo; the stand path allocates nothing. Dropped:
`walk_allies_in` reading the fight's enemies once (identical, -0.00 to -0.01%, more turns dearer than cheaper). Open:
the sim itself, and how many stands reach one (0.91 an OOF turn, a decision-level change).

## Fuel campaign 6 summary (2026-11-04, astraeus d6e74b6f -> fc6-m6)

Goal: undo the out-of-fuel cost of CHANGES 337 (d6e74b6f, the oscillation fixes; 458,674 / 111,324 OOF turns against
its parent in 20k games) without changing its play; target OOF -50% against d6e74b6f at scale. Six rounds, 14 workers
(hyperion/fuel-campaign-6/BRIEF.md, NOTES.md). **Result: OOF -34.6% at 20k, win rate level (50.1%), and at 100M fuel
every bench replay (322 on nine sets plus the 16-game default bench) is still byte-identical to d6e74b6f's**: the
campaign's play changes act only when fuel is short. The -50% target was not reached.

**Shipped, by round** (effects as measured in each round; the 20k rows are against d6e74b6f on suites unused before):

| round | CHANGES | what | measured |
|---|---|---|---|
| 1 (fc6-m1) | 338-341 (fuel only), 342 | the work veto's stand reads recall, hold, lethal and pursuit only where its verdict does; lethal skips strikes out of reach; label_through keeps 16 walks; farm's loop keeps back the veto's measured ask | vs d6e74b6f, 2 x 10k: 49.1% and 49.7%, OOF -17.1% / -17.9% (round 1 -30%) |
| 2 (fc6-m2) | 343-344 (fuel only), 345 | label_through's walks survive failed searches; wider failed searches drop spares first; farm keeps back the veto's unmeasured first ask | vs m1, 10k: 49.9%, OOF -1.4% (round 1 -37%) |
| 3 (fc6-m3) | 346-347 (fuel only), 348-349 | enemy_reach's lookup checks the last slot first; the veto reads our tile's leave only for a tile it would veto; the walk's searches and prey keep back the veto's ask | vs d6e74b6f, 20k: 49.9%, OOF -32.0% (338-349) |
| 4 (fc6-m4b) | 350-351 (fuel only) | hops share pockets and remember barren ones; whole floods use a distance field on big maps | q round-1 mean -9.7%, its dearest turn 1.15M -> 598k; vs d6e74b6f, 20k: 49.5%, OOF -32.7% |
| 5 (fc6-m5b) | 352 (fuel only), 353 | walk-only strike search when no strike reaches a foe; 345's first-ask reserve only for a group to walk to (fixes an opening livelock) | vs d6e74b6f, 20k: 49.9%, OOF -33.8% |
| 6 (fc6-m6) | 354-357 (fuel only) | round-1 world init: plan decode in locals, the engine's group count, crossings test only nearby camp tiles, groups and beliefs written whole | fs round-1 mean -4.7%; vs m5b, 10k: 49.5%, OOF +1.8% (one runaway game; +0.5% without it) |

**Final A/B: fc6-m6 against d6e74b6f** (own drafts, real budget, fast runner, 20,480 games on 40 suites no A/B had used:
fresh-66021..66040, fresh-68201..68220; batch `replays/batch-20261104-121709-ab-fc6-final-vs-base-*`; OOF buckets from
`batch_oof.py`, shared-gems maps skipped, all OOF turns):

| | fc6-m6 | d6e74b6f | change |
|---|---|---|---|
| win % (95% CI) | **50.1 (49.4-50.8)**, 10,259-10,221 | | suites min / median / max 45.9 / 49.6 / 56.4 |
| OOF turns (ab.py) | **311,440** (in 17,574 games) | 475,970 (in 19,041) | **-34.6%** |
| OOF, batch_oof (first-in-streak) | 305,793 (261,775) | 468,284 (395,215) | -34.7% (-33.8%) |
| round 1 | 15,526 | 34,482 | -55.0% |
| rounds 2-10 | 22,767 | 31,480 | -27.7% |
| rounds 11-60 | 30,019 | 39,759 | -24.5% |
| rounds 61-300 | 70,686 | 108,518 | -34.9% |
| rounds 300+ | 166,795 | 254,045 | -34.3% |
| in games with <10 / 10-49 / 50+ OOF | 40,004 / 131,432 / 134,357 | 38,562 / 179,171 / 250,551 | +3.7% / -26.6% / -46.4% |
| fuel a turn mean / p50 / p90 / p99 | 52,382 / 51,550 / 86,650 / 95,350 | 52,823 / 52,050 / 86,750 / 96,650 | -0.8% / -1.0% / -0.1% / -1.3% |
| turns at/over 100k | 0.42% | 0.58% | -28% |
| shortcuts without OOF | 8.40M | 8.05M | +4.4% |
| farm-partial-evaluation | 5.39M | 4.91M | +9.9% |
| step-guard-entry | 1.11M | 1.17M | -4.9% |
| turn-order | 513k | 752k | -31.8% |
| prey-cut-short | 427k | 289k | +47.6% |
| static-descend | 231k | 149k | +54.7% |
| farm-no-route | 181k | 157k | +15.8% |
| comms-stale-vision | 181k | 290k | -37.8% |
| step-guard-look | 176k | 174k | +1.4% |
| ward-no-bushes-clusters | 95k | 81k | +17.8% |
| crow-flies-farm | 46k | 35k | +30.1% |

Phase of OOF turns: decide 74% / 69%, queue 26% / 31%; first-in-streak ending before the turn's branch line (`?`) 84%
/ 80%. Round 1 is all farm branch (F 14,911 / 33,796 first-in-streak). Worst maps (first-in-streak): mut-the-pack-
6603901838 2,380 / 2,879, gen-huge-shared-6602505201 1,623 / 1,077, gen-mega-groups-6602308215 1,186 / 1,441. The
shortcut rises are the real-budget reserves at work (342/345/353 stop farm's loop early, 348 the walk's searches, 349
prey); turn-order and comms-stale-vision fall with the turns no longer run out.

**Benches, d6e74b6f (base-*) -> fc6-m6 (m6-*)**, 100M (every replay identical; play turns after round 1; total includes
round 1):

| set | mean | p90 | p99 | max | turns over 100k | round 1 mean | round 1 p90 | round 1 max | round 2 mean | total |
|---|---|---|---|---|---|---|---|---|---|---|
| wide | 55,705 -> 55,307 | 87,114 -> 87,062 | 116,247 -> 115,459 | 324,363 -> 316,789 | 6,261 -> 5,994 | 234,707 -> 229,264 | 306,870 -> 291,929 | 532,995 -> 512,730 | 109,800 -> 110,786 | -0.72% |
| oof | 59,388 -> 58,747 | 91,002 -> 90,046 | 157,764 -> 155,402 | 805,066 -> 803,803 | 18,573 -> 17,654 | 256,278 -> 248,480 | 387,185 -> 361,216 | 466,404 -> 448,987 | 121,122 -> 122,203 | -1.09% |
| mg | 61,021 -> 60,580 | 88,888 -> 88,609 | 145,781 -> 144,937 | 475,804 -> 471,444 | 4,987 -> 4,798 | 255,664 -> 246,859 | 335,513 -> 323,031 | 463,856 -> 436,169 | 120,759 -> 122,079 | -0.74% |
| q | 63,570 -> 62,979 | 96,584 -> 96,055 | 176,419 -> 173,431 | 595,398 -> 598,768 | 24,062 -> 23,675 | 323,875 -> 283,534 | 480,001 -> 424,796 | 1,167,811 -> 587,306 | 146,786 -> 147,645 | -0.99% |
| big | 62,431 -> 62,099 | 88,031 -> 87,961 | 127,313 -> 126,230 | 360,546 -> 349,742 | 5,722 -> 5,552 | 292,859 -> 281,330 | 387,546 -> 377,867 | 496,310 -> 472,502 | 158,963 -> 160,048 | -0.55% |
| fs | 96,987 -> 96,712 | 138,759 -> 138,270 | 210,588 -> 209,810 | 844,323 -> 844,052 | 25,617 -> 25,309 | 618,575 -> 578,852 | 697,448 -> 644,275 | 764,853 -> 709,952 | 278,565 -> 280,010 | -0.34% |
| fight | 54,098 -> 53,323 | 87,828 -> 87,517 | 143,805 -> 140,341 | 369,209 -> 382,234 | 10,828 -> 9,999 | 201,626 -> 198,717 | 224,393 -> 212,772 | 337,341 -> 310,589 | 90,388 -> 91,248 | -1.43% |
| tgt | 62,738 -> 62,329 | 92,779 -> 92,104 | 144,830 -> 143,096 | 424,499 -> 424,472 | 4,472 -> 4,308 | 256,937 -> 248,186 | 313,158 -> 295,041 | 366,790 -> 352,871 | 113,058 -> 114,934 | -0.67% |
| osc | 61,148 -> 60,237 | 96,323 -> 94,756 | 160,821 -> 157,192 | 448,995 -> 441,446 | 36,022 -> 33,949 | 208,719 -> 205,315 | 246,910 -> 236,377 | 330,779 -> 317,363 | 96,301 -> 97,035 | -1.49% |

Turns over 100k summed over the nine sets: 136,544 -> 131,238 (-3.9%); total fuel -1.02%. q's round-1 max is
350-351's hops; fs's round 1 is 354-357's init (a fs body still cannot finish round 1 inside 200k). Dearer: round 2's
mean on every set (+0.6 to +1.7%: 340 moves round 1's caches there) and fight's max turn (347: both stands run where
our tile leaves too).

Real budget (`--fuel 0`; games diverge, so per-set OOF is indicative: tgt rose):

| set | OOF | shortcuts (without OOF) | round-1 turns at 200k cap |
|---|---|---|---|
| wide | 1,425 -> 1,150 | 19,610 -> 21,115 | 71 -> 19 of 245 |
| oof | 4,739 -> 3,607 | 46,203 -> 52,057 | 110 -> 88 of 276 |
| mg | 1,121 -> 740 | 12,654 -> 13,861 | 54 -> 32 of 124 |
| q | 4,609 -> 3,982 | 56,485 -> 55,170 | 158 -> 113 of 264 |
| big | 478 -> 357 | 23,963 -> 25,179 | 104 -> 91 of 164 |
| fs | 2,199 -> 1,597 | 57,079 -> 56,365 | 140 -> 140 of 140 |
| fight | 3,604 -> 2,493 | 25,644 -> 27,254 | 21 -> 11 of 162 |
| tgt | 1,486 -> 2,307 | 9,184 -> 13,775 | 42 -> 26 of 84 |
| osc | 14,713 -> 9,846 | 93,032 -> 94,917 | 56 -> 24 of 282 |

Default 16-game bench (8 maps against hyperion), d6e74b6f -> fc6-m6. 100M (16/16 identical): total 5.012G -> 4.969G
(-0.86%), mean 54,008 -> 53,543, p90 86,872 -> 86,829, p99 111,469 -> 110,406, max 253,254 -> 252,040, turns over 100k
1,816 -> 1,719, round-1 mean 239,602 -> 235,824 (p90 308,707 -> 299,856, max 350,651 -> 330,840), round-2 mean 112,704
-> 113,185. `--fuel 0`: OOF 323 -> 189, shortcuts without OOF 6,959 -> 6,361, round-1 turns at the 200k cap 21 -> 7 of
88, p99 94,981 -> 92,822.

**Dropped, and why** (numbers in the rounds above and NOTES):
- **The post-strike work veto refusal** (round 4's a28721f3: refuse a step more exposed than our tile without running
  the stand), three readings: with 350-351 against d6e74b6f 49.0% (48.3-49.7) at 20k with OOF -11% against 350-351
  alone; fc6-m5f 48.5% (47.8-49.2); 353 plus it 49.1% (48.4-49.8), -0.58 points paired. Bridged, its wasted turns are
  level (the extra refusals, wander +4.6%, are paid by fewer OOF turns); it lost on win rate every time.
- **Lazy stand walkers** (round 5's bf8df313, fuel only, identical at 100M): -0.73 points paired (-1.42..-0.04) and OOF
  +1.4% at the real budget; its census saving did not show at scale.
- **Settle bounds** in the fight sim (round 2, stand): identical at 100M, but every form cost more than it saved
  (+0.03% to +1.55% total on fight / osc): a check costs 225-1.2k and fires too rarely against the 1.3-3k sim it ends.
- **Reserves that lost** (round 3, tail): farm's loop keeping a cold-pass reserve (48.7%, 48.3%, 49.8% with OOF only
  -0.7%), and the walk sites keeping back the veto's whole turn (49.6%, OOF -1.9%).
- Smaller: cross-turn Reach and distance memos (share; ~250-460 a heavy turn at most), a cross-turn fight-sim memo
  (sides; a content key costs ~400-500 a sim against ~300-700 saved), an exact walk_allies_in table (+0.03 to +0.24%),
  lazy altar steps (init; fs total +0.046%), per-turn veto-count caps (bind on 0.8-2.6% of turns).

**Open leads** (from NOTES):
- The no-check fight work is most of what is left: 84% of first-in-streak OOF turns end before the branch line, in
  want_home's stand, the strike search and the post-strike veto. On OOF turns a `new_fight` is mostly its sim (8.5k);
  only a cheaper sim or fewer stands reaching one (0.91 an OOF turn, a decision-level change) moves it.
- Runaways (games with 50+ OOF still hold 44%): standoffs repeating the same failed searches (make_way/step_field) or
  fight_of each turn; a per-turn failure memo keyed on goals/walls/me would be exact. gen-leaky-diagonals-6811007814's
  overrun in step-guard / static-descend is one such state, reachable from m5b's code.
- Round 1 is now 5% of OOF, all farm: a fs body still needs ~201k for world init (static_camps ~105 a member,
  init_beliefs ~93 a group), so only an indexed plan at 200+ groups or fewer instructions a member lets it act.
- 342's measured loop reserve: dropping it reads -0.7% wasted turns (CI crosses 0) for +5.8% OOF; a tighter reserve
  (skip landings already in the veto's boards) is the lead. Static StandReach tables built mid-game could move into
  the turn-end queue (3% of OOF turns hold one, ~10-13k); the walk_on veto after a strike (~13k a tile).

## Teleport crystal shortcuts (2026-11-03, astraeus 296 variants)

A crystal (10 gold, carry 1, bought on spawn or dead) hops to a free tile within Chebyshev 3 after a 3-turn channel,
walls ignored. astraeus buys one only for pockets no walk reaches (StaticMap::hops). Variants against
`variants/astraeus-10b2313` (CHANGES 296), own drafts, fastrunner native on alext, 52,394 games each (ladder, gen,
gen-s1, fresh-92001..92100); diffs in [crystal-2026-11-03/](crystal-2026-11-03/).

| Variant | Win % | 95% CI |
|---|---|---|
| v1: hop on any walk when it beats walking by 4 turns (lookahead 3, safe start); buy first on spawn | 46.84 | 46.4-47.3 |
| buyonly (v1's buying, no hops) | 47.03 | 46.6-47.5 |
| nobuy (v1's hops with crystals bought only as before) | 49.99 | 49.6-50.4 |
| v2: buy last (after shards) | 48.67 | 48.2-49.1 |
| v2-buyonly | 48.55 | 48.1-49.0 |
| v3: v2, buying only when a static plan (BFS from spawn, then landings by channel time, steps of 3) saves 8 steps to the farm choice | 49.81 | 49.4-50.2 |
| v3-b4 (saves 4) | 49.64 | 49.2-50.1 |
| v5: v3 plus routing: with a crystal, walk to the plan's best hop source for the farm choice or any altar, and hop | 49.69 | 49.3-50.1 |
| v4: v3's plan, buying when the rounds saved times the farm value a round beat 1.5x the gold's price (and 4 steps) | 49.71 | 49.3-50.2 |

- **The buying is the cost.** v1's hops added nothing over its buying (v2 48.67 vs v2-buyonly 48.55); bought first,
  the 10 gold held back emblems (-3.2). Gated by a plan of the real saving (v3) it is level, not a gain.
- **v3 across a panel** (gauntlet.py, 11,436 games an opponent, paired by map and side): vs v67 -0.7 [-1.4, +0.0],
  v66 +0.5, v65 -0.2, demeter +0.6; mean +0.08 points.
- **Univardisty of Shingtonwash** (fetch_replays, 98 games): ~4 hops a game, all on wall maps, from the same few sources
  next to their spawn. In their 01concentrated_wealth game (`cambc matches download ce8e0389...`) they bought 42
  crystals in 1192 rounds and hopped 42 times over the NW wall at (13,22) to (17,25), the way out of their spawn to
  the altar (23,24) and the centre group. Our walk there through the NE gap is ~26-32 steps against a hop's ~24:
  ~8-10 steps a trip, which they buy every trip (their gold allows it; ours is short: most of v5's buy attempts on
  that map failed for gold). team_crystals.py's static BFS overstated that walk (87).
- v5's routing works (traced on 01concentrated_wealth: routes built for every group whose hop saves 8, carriers walk
  to the sources) but rarely has a crystal to use. The first v5 build never built its routes (warm_crystal_plan
  returned before the routing step once the levels were done); fixed before its A/B.
- v4's value test (`saved * memory.farm_rate >= 1.5 * prices().per_gold * 10`): the trace put that ratio between 0.5
  and 37 (median ~2.6) over buy checks; level with v3 (49.71). v4 ran with the fresh suites merged
  (`maps/fresh-92all`), the same maps.

Held: nothing kept. Crystals pay for UW, whose economy has gold to spare; ours spends it on emblems first.

## Main against v66 and v67 (2026-11-03, astraeus 1fe4a9f2)

Main after fuel campaign 4 (frozen as `bots/variants/astraeus-1fe4a9f2`) against `bots/baselines/v66` and `v67`, own
drafts, real budget, fast runner, on 40 new suites `maps/fresh-96001..96040` (`mapgen suite --seed 96001-96040`,
10,240 maps, both sides: 20,480 games each). Logs in `replays/ab-main-vs/`.

| Opponent | Win % | 95% CI | W-L | Suites (min / median / max) | OOF main / opponent |
|---|---|---|---|---|---|
| v66 | **68.0** | 67.3-68.6 | 13,919-6,561 | 63.9 / 68.0 / 73.4 | 90,153 / 112,636 |
| v67 | **61.7** | 61.0-62.3 | 12,629-7,851 | 58.2 / 61.5 / 67.0 | 91,960 / 127,250 |

All 40 suites above 50% in both; no failed matches.

## The ostrich and SPSA-tuned constants (2026-11-03, astraeus 6265c2cb; CHANGES 321)

Shipped: diana's ostrich (turn order: an enemy in reach moves us to the danger band's early seats only once we or an
enemy near us lost health within `ostrich_rounds`) and the 51 constants of diana's SPSA run `replays/tune/d1` at its
final iteration (1312), ported to astraeus as `constexpr` values (exact float32s). The port is exact: on fc99b84 it
replays identically to `bots/variants/diana-d1-final` at 100M (24/24 games), with 0.4% less fuel (constexpr instead of
the tuner's patchable block).

**The tuning run.** `tools/tune/tune.py` (SPSA, 4 sign pairs, 3,072 games an iteration, 4.02M games in all,
05:57-14:51 UTC) against a fixed panel: astraeus fc99b84, demeter, hyperion, v66, v67, crystal-v3, own drafts, on
`maps`, `maps/gen`, `maps/gen-s1` and `maps/fresh-92001..92100`. Mean candidate win rate against the panel by
iteration: 63.3% (1-100), 64.3% (100-300), 65.1% (300-600), 65.7% (600-900), 65.7% (900-1312). The biggest moves:
`hurt_health_fraction` .35 -> .470, `camp_risk` .35 -> .416, `crew_trip_risk` .6 -> .769, `siege_pool_share`
.6 -> .484, `burst_rounds` 20 -> 15, `help_radius` 8 -> 6, `tribute_window` 6 -> 8, `max_wait` 3 -> 2.

**Held-out tests.** Real budget, fast runner, 40 suites `maps/fresh-53000..53039` (new for these A/Bs, never in the
tuning pool), 20,480 games each. Logs in the `ostrich` worktree's `replays/ab/`.

| A/B | Win % | 95% CI | Suites (min / median / max) | OOF candidate / reference |
|---|---|---|---|---|
| tuned (`astraeus-ost`) vs pre-tune main (`astraeus-main`), own drafts | **54.6** | 53.9-55.3 | 45.9 / 54.8 / 58.8 (39 of 40 above 50) | 107,985 / 104,616 (+3.2%) |
| tuned vs the ladder test drafter | **69.7** | 69.1-70.3 | 65.2 / 69.7 / 74.6 | 91,374 / 92,802 |
| pre-tune vs the ladder test drafter | **66.5** | 65.8-67.1 | 59.0 / 66.4 / 70.9 | 86,907 / 90,493 |

The test drafter (`bots/variants/testdrafter`) is pre-tune main with `test_draft` on and the refreshed test-draft table
(CHANGES 322: the 10 most common compositions per pick count of the top 10 other teams' ranked games, 10-31..11-03).
It is not in the tuning panel and plays compositions the panel never drafts (Vesper, Vendetta, Heart of Ruin, Ryth,
Prism, Varg, Ren with and without Cassi & Issac). Its candidates draft for themselves (Cassi & Issac in every game):
mixing own and test drafts in one A/B is deliberate here, ladder compositions against our real draft.

Against the test drafter, by its composition (`choose()` picks one by map and side, uniformly; each row is ~600-860
games, about ±5 points a row; drafts read from the replays' draft phase):

| Test drafter composition | Games | Tuned % | Pre-tune % | Change |
|---|---|---|---|---|
| HoR Vend Marc | 641 | 67.4 | 61.8 | +5.6 |
| Marc Varg HoR | 593 | 76.1 | 71.2 | +4.9 |
| HoR Marc C&I | 600 | 67.7 | 64.2 | +3.5 |
| Vesper Marc C&I | 637 | 65.9 | 63.3 | +2.7 |
| HoR Vesper Ryth | 628 | 75.0 | 73.2 | +1.8 |
| Vesper C&I HoR | 608 | 66.4 | 64.8 | +1.6 |
| Ryth Marc HoR | 565 | 71.2 | 70.8 | +0.4 |
| Prism Marc HoR | 642 | 71.0 | 71.2 | -0.2 |
| Vesper Marc HoR | 616 | 67.7 | 68.0 | -0.3 |
| Vesper HoR Vend | 608 | 68.9 | 69.2 | -0.3 |
| **all 3-pick** | 6138 | **69.7** | **67.7** | **+2.0** |
| Vesper Vend HoR C&I | 622 | 66.4 | 55.9 | +10.5 |
| Vesper C&I HoR Marc | 615 | 64.4 | 58.0 | +6.3 |
| HoR Marc Willow C&I | 626 | 71.6 | 65.7 | +5.9 |
| Marc Vend HoR C&I | 591 | 61.9 | 56.5 | +5.4 |
| HoR Ryth Willow Marc | 636 | 78.9 | 73.7 | +5.2 |
| Willow HoR Vend Marc | 614 | 75.2 | 71.0 | +4.2 |
| Ryth Vend Marc HoR | 647 | 72.6 | 70.6 | +2.0 |
| Prism Marc HoR Vend | 603 | 71.0 | 69.2 | +1.8 |
| Vesper HoR Vend Marc | 622 | 69.1 | 67.4 | +1.8 |
| HoR Vesper Ryth Marc | 600 | 69.5 | 69.5 | +0.0 |
| **all 4-pick** | 6176 | **70.1** | **65.8** | **+4.3** |
| Willow HoR Vend Ryth Marc | 802 | 73.4 | 66.5 | +7.0 |
| Vesper Vend HoR Marc C&I | 794 | 63.1 | 56.5 | +6.5 |
| Marc Vend HoR C&I Willow | 804 | 67.5 | 62.3 | +5.2 |
| Vesper Vend HoR Tavi Marc | 843 | 72.6 | 68.1 | +4.5 |
| HoR Ren Vesper Ryth Marc | 858 | 71.9 | 67.8 | +4.1 |
| HoR Marc Vesper C&I Willow | 793 | 61.8 | 58.5 | +3.3 |
| Vesper Vend HoR Ryth Marc | 815 | 68.1 | 65.5 | +2.6 |
| HoR Ren Vesper C&I Vend | 856 | 66.8 | 65.2 | +1.6 |
| Vesper Vend HoR Varg Marc | 809 | 72.2 | 71.8 | +0.4 |
| Ryth Vend Marc Varg HoR | 792 | 75.8 | 77.4 | -1.6 |
| **all 5-pick** | 8166 | **69.3** | **66.0** | **+3.4** |

**Overfitting.** The fear was that SPSA learned the six panel bots and the tuning maps. Evidence against it:
- the gain holds on maps the tuner never saw (54.6% against pre-tune, 39 of 40 suites above 50%);
- it holds against an opponent outside the panel playing other drafts: +3.2 points (69.7 against 66.5, ±0.9), on every
  pick count (+2.0 / +4.3 / +3.4), in 25 of 30 compositions; the five that dip lose 0.0-1.6 points, all within noise,
  and four of them were already our easiest matchups (68-77%);
- the largest gains are where pre-tune was weakest: Cassi & Issac compositions (Vesper Vend HoR C&I 55.9 -> 66.4,
  Vesper Vend HoR Marc C&I 56.5 -> 63.1, Vesper C&I HoR Marc 58.0 -> 64.4).
Not yet covered: an exploiter search for constant sets that beat the tuned ones (`tools/tune/league.py`, run `x1`, the
tuned bot frozen): results in a follow-up entry. Cost: out-of-fuel turns +3-5%.

## Exploiter search against the tuned constants; main against v66 and v67 (2026-11-03, astraeus 8a2e8afb)

**Exploiter search** (`tools/tune/league.py`, run `replays/tune/x1`, from d1): the tuned constants (d1's iteration
1312, = CHANGES 321) held fixed (`a` 0, no main games); optuna TPE exploiters over the same 51 constants and ranges
(about 0.5x to 2x each default), 32 trials a round, each on 24 maps from both sides (48 games) against the tuned bot,
d1's map pool, own drafts (Cassi & Issac mirror), diana's base (fc99b84 + the ostrich). The first round was seeded
with the default constants and d1's iterations 100, 300, 454 (d1a), 700 and 1000. A round's best trial with 56%+ was
replayed on 500 more maps (1,000 games) and would have joined the league at 54%+.
- 26 rounds, 832 trials, 15 minutes. Round bests on their 48 games: 54-67% (the best of 32 noisy trials). All 25
  confirmations failed: 42.4-50.7% of 1,000, mean ~46%. None of the seeds came close either.
- A weak adversary (TPE on 51 dimensions with 48-game trials) that probes only the Cassi & Issac mirror, so this rules
  out broad weaknesses of the tuned constants, not narrow ones.
- Tooling: after a fast-runner rebuild changes native cache keys, a tune or league run started before its base bot has
  played once under the new runner patches only the old key's library and compiles every candidate (~15 s each; a
  round took 3 min instead of ~35 s). Restarting the run after the base has played fixes it.

**Main against v66 and v67.** Main at 8a2e8afb (fuel campaign 5, the ostrich and the tuned constants; frozen as
`bots/variants/astraeus-8a2e8afb`) against `bots/baselines/v66` and `v67`, own drafts, real budget, fast runner, on
40 new suites `maps/fresh-97001..97040` (10,240 maps, both sides: 20,480 games each). Logs in
`replays/ab-main-8a2e8afb-vs-v66.log` / `-v67.log`.

| Opponent | Win % | 95% CI | W-L | Suites (min / median / max) | OOF main / opponent |
|---|---|---|---|---|---|
| v66 | **71.4** | 70.8-72.0 | 14,627-5,853 | 68.9 / 71.3 / 74.8 | 76,644 / 115,281 |
| v67 | **66.0** | 65.3-66.6 | 13,513-6,967 | 59.6 / 66.1 / 72.3 | 76,988 / 122,799 |

All 40 suites above 50% in both; no failed matches. Against main at 1fe4a9f2 ("Main against v66 and v67", other
suites): +3.4 points against v66 (68.0), +4.3 against v67 (61.7), and ~15% fewer out-of-fuel turns (90,153 / 91,960).

## Last-minute bug fixes (2026-11-03, astraeus 1b46dab0; CHANGES 323-325)

Three stall and gem-loss fixes from three agents' replay audits, merged and judged together against
`bots/variants/astraeus-1b46dab` (= v68), own drafts, fast runner, on 40 unused suites `maps/fresh-98301..98340`
(20,480 games). A baseline mirror on the same games gave 107,693 out-of-fuel turns a side; "differ" is a game whose
winner or length differs from the mirror's.

| Variant | Win % | 95% CI | OOF CAND / REF | Games differ (maps) | Winners changed (for / against) |
|---|---|---|---|---|---|
| A1 + A2 + B + C | 50.1 | 49.4-50.7 | 109,544 / 108,743 | 4,769 (3,469) | 921 / 909 |
| **A1 + A2 + C (kept)** | **50.0** | 49.3-50.7 | 109,707 / 109,265 | 4,710 (3,438) | 904 / 900 |

- Out-of-fuel, kept version: in the 15,770 games that played as the mirror, CAND +0.5% (56,881 against ~56,630),
  nearly all in the turn-end `queue` phase (15,917 against 15,708): CHANGES 323's lower estimate lets the warm-up
  start fields it sometimes cannot finish; those games still played the same. In the 4,710 that differ CAND and REF
  rose alike (+3.4% / +3.2%): different games, not the code.
- Bug maps against v68 (both sides): champion-rounds stood still 100+ rounds 12,012 -> 6,221 (all-game stalls on
  topo-shortcut-600206905, topo-backdoor-600206700 and topo-necks-600107006 gone; what is left is the shared-gem
  standoff below). Agents' own A/Bs: A1 alone 49.9% of 10,240 (+2.1% OOF), A1 + A2 50.0% (fresh-98001..98020),
  C 50.0% (fresh-98201..98220, OOF flat).
- Dropped, B: `kite()` returning false when every station is held by a unit in sight (shared-gem standoff,
  gen-shared-gems-600101605: a guard on the one station a big group leaves, the rest walking at it all game, 0-0).
  Its own A/B was 50.0% of 10,240 (fresh-98101..98120), but on its own map the yielding champions farmed, died to
  camps 10 times with 0 gems, and v68 then scored 227 / 341: the 0-0 split (team B wins ties) became two losses.
  Farm cannot earn there either; the standoff needs a fix where farm and kite choose the group, not a yield.

## Healing on our own spawn (2026-11-03, astraeus cd577b10; CHANGES 328)

Judged against `bots/variants/astraeus-15a050a` (round 2 with the first passes since reverted), own drafts, fast runner. Suites:
- `maps/fresh-99501..99540` (40 unused suites, merged as `maps/fresh-995all`);
- the 86 ladder maps (`maps/fresh-ladder86`);
- `near5`: 6,380 maps whose nearest striking camp is within 5 (Chebyshev, team A's spawn box), picked from 100 new
  suites `fresh-97201..97300` (seeds unused before; 1.2% of maps are within 3, 7% within 4);
- `near4`: within 4, from those suites and fresh-995xx (2,492 maps).

| Version | All | fresh-995all | near (suite) | OOF CAND / REF |
|---|---|---|---|---|
| pre-audit + audit fixes (d8003561) | 50.5 (20,652) | 50.5 | | 125,986 / 110,097 |
| + crew stands kept ours, lazy gap (097929ad) | 50.8 (33,240) | 50.9 | near5 50.6 | 190,323 / 172,103 |
| + post-fight walk holds spawn stands (fd300b73) | 50.8 (33,240) | 51.0 | near5 50.5 | 192,281 / 172,788 |
| + per-tile fire cached (6cd9fe93) | 50.7 (25,464) | 51.0 | near4 49.4 | 152,809 / 139,556 |
| **kept: + spawn board from the camp area (cd577b10)** | **51.1 (33,412)**, CI 50.5-51.6 | 51.0 | near5 51.3 | 191,128 / 176,191 |

- **By distance** of the nearest striking camp (all three suites of the kept version): 1: 54.8% (186 games),
  2: 51.1% (352), 3: 50.6% (334), 4: 51.2% (4,146), 5: 51.1% (12,880), farther: 51.0% (15,514). Monolith maps within
  3: 60.3% (78).
- **Economy vs `bots/idle`** on the 436 maps within 3 (872 games, rounds to 1000 tributed gems): the first audited
  version was +1.0% slower (CI -0.4..+2.4), the kept one -0.8% (-2.0..+0.5). Near-spawn groups are a small share of
  the economy even there: on gen-topo-duel-9720207204 the champions stood on the spawn column next to the central
  group 87 turns in ~3.7k, against 65 for the base.
- **Ablations** on near4 (fd300b73; 4,984 games each, all 48.1-51.2): full 49.6, recall kept as before 49.8, no
  `mend_hit` 49.7, no siege walk home 49.5. None of the parts moves the near maps at this resolution.
- **What the audit and testing changed:**
  - **Crew pricing.** Pricing crews at the crew's shortest range repriced every clear, not only spawn stands. On
    mut-the-pond-9950901819 it sent the team to a farther wolf group (322-1034 as team A). Crews now keep our stands
    and only take the least sturdy member's survivable.
  - **The post-fight walk.** In farm's `struck` branch (after a fight search, most turns with an enemy in sight),
    `walk_on` walked champions off their spawn stand every other turn. It took 110 of ~220 farm turns on
    gen-topo-duel-9720207204, and the stand logic was reached 13 times.
- **Fuel, open.** Out-of-fuel turns are +8.5% in the kept A/B (+25% in round 1 in fd300b73's).
  - On the fuel bench (wide set, 100M): mean 52,064 -> 52,616 (+1.1%), round 1 213k -> 219k, >100k turns +10%.
  - A census on 24 near4 maps at the real budget had OOF play turns level (176 / 172). The OOF turns spent more in
    `farm.loop` (18.4k vs 13.0k OOF-first) and `camp_trapped`.
  - Round 1 on 00lanes: same call counts. `stand_reach` builds cost ~500 more each, and the rest of
    `min_camp_damage` ~570 more a call, not yet attributed.
- **Not integrated:** the draft's heal price (draft.cc, recall + walk), kite on shared-gem maps, Willow's heal value,
  and groups with more than 32 strikers (`reaching` keeps 32 bits).

## Fuel merge: CHANGES 331-333 (2026-11-03, astraeus 3d4d9c52 + 331-333)

bench.py, test drafts vs hyperion, fast runner. wide is `--set wide` (52 games); heavy is 02the-pack, 00packs, 26
the-pack mutations (fresh-730xx) and 25 out-of-fuel-heavy maps, 19 fresh and 6 ladder (78 games). Replays identical at 100M: wide
52/52, heavy 78/78. Total fuel at 100M -0.03% (wide) and -0.07% (heavy); heavy p99 129,334 to 129,060, max 387,492
to 383,934, turns over 100k 9,512 to 9,466 (wide 5,515 to 5,491). Real budget, base / cand: wide OOF 615 / 622,
farm-partial-evaluation 9,284 / 8,926, step-guard-entry 2,811 / 2,683, p99 93,505 / 93,410; heavy OOF 999 / 1,034,
farm-partial-evaluation 15,997 / 15,295, p99 95,433 / 95,509. Out-of-fuel turns on samples this size swing by tens:
judge them on a full A/B. `tools/fuel/census/maps.txt` named maps/fresh-828xx, which no longer exist; it now lists the
25 heavy maps above.

## Audit fixes to 325-330 (2026-11-03, astraeus 04e87c4f; CHANGES 334)

Four rare-case fixes, A/B'd as a check that nothing regresses. Against `bots/baselines/v69`, own drafts on both sides,
fast runner, `maps/fresh-96101..96140` (unused before; fresh-96103 has 255 maps) plus `maps/fresh-ladder86`:
**50.0% of 20,650** (49.3-50.7); per suite 49.0-51.2; ladder 48.3% (40.9-55.7) of 172. Out-of-fuel turns 121,102
against 121,293. No failed matches. In 12 instrumented debug games (03homonoliths, 02the-pack, 00monolith,
01boss-battle, 02guardians, 00elkring, both sides), only the siege stall fired: 22 exits with the wait already
started, all on 02guardians, where the old exit would have restarted the wait. The live walk home, the
no-free-spawn-tile case and the ranged hot tile never came up there.

## v69 against v68: farming and pathing (2026-11-03, astraeus 0c332d65; CHANGES 335-336)

Why v69 did slightly worse than v68 on the ladder: the farming, banking and pathing side. All runs use the fast runner,
own drafts on both sides, and `--no-test-draft`.
- **Ladder.** Corrected extracts of 258 ranked games (sides fixed, extractor 42d84240): v68 59% of 69, v69 63% of 189,
  against different mixes of opponents. v69 captured more (63.5 groups a game against 53.6) and earned more (3,862
  gems by round 600 against 2,884). It took more camp damage (23.3k against 17.2k; 366 a capture against 321) and
  recalled more (51 against 42). Opponents changed between the sets: in several same-map pairs the enemy diverges
  first (rounds 3-4). Where we diverge first (lost_world, the_pond, 01broken_curve, 02fields), v69's opening economy
  was equal or better, and the games were lost in later fights. boss_battle losses are Monolith sieges against
  Vesper (siege area).
- **Local, v69 against v68 head to head** (ladder + fresh-43001..43004, 2,220 games): 52.0% (49.9-54.1); ladder
  49.4% of 172. `ab_farm` farming was equal or slightly better for v69. Camp damage was 23.0k against 22.5k a game,
  recalls 57.6 against 60.7. Flips per 1k alive rounds were 28.1 against 28.3. Oscillation episodes (3+ quiet flips)
  were 2,159 against 2,172.
- **Against ladder compositions** (`variants/v68-td`, test drafts; 5,292 games each): v69 65.6% (64.4-66.9), v68
  65.2% (63.9-66.5); ladder 65.1% against 62.8% of 172. No local sign of a farming or pathing regression in v69.
- **Found and fixed** (in v68 too): the static-descent and wide-route two-turn cycle (CHANGES 335), and a walk
  standing on a respawning group's tile (336), each level on 20,652 games. Together (55805d38) against `bots/baselines/v69`
  (fresh-43021..43040 + ladder, 10,412 games): 49.5% (48.5-50.5); ladder 52.3% of 172; out-of-fuel turns 63,155
  against 64,723.
- **Open, not fixed:**
  - **Ward bumps.** `ward_bushes` (bot.cc) retries the same first 3 tiles of a bush cluster every turn. An ally's
    unseen ward is a hidden blocker, so every try fails. That is ~49 blocked placements a game a side; 42% repeat
    a tile within 2 rounds. It costs fuel and leaves the ward unplaced. Allied ward tiles are not remembered across
    turns.
  - **gen-topo-gatehouse (a 1x10 corridor spawn).** The team jams in single file; v68 jams too. 1,188 quiet spawn
    flips in one game.
  - **An ally holding the only tribute tile.** A banker routed to it waits, and the static descent can walk it back
    (02guardians, mut-fan). `make_way` yields only between two movers.
  - **Ladder 63fd3ae8 game 1** (00rushbait_v2): Issac (480/900) dashed across a hole line to hit an Elk alone at
    round 256. He left at round 259 with 360 hp, walked 5 tiles still in the Elk's reach, and died at round 264
    (Cassi with him). With the walk out priced (`camp_trapped`), round 258 sat on the one-hit margin. Farm's trip
    budget (`trip_spare`, health above the recall line) does not include the walk out of a pocket under fire. Not
    reproduced locally.

## Siege and risk review of v68 against v69 on the ladder; the camp exit's shelter (2026-11-03, astraeus 0c332d65)

**Ladder.** 195 games (v68: 49, v69: 146, many of v69's scrims), re-extracted after a fix to `tools/replay/extract.mjs`.
It read the teams from the group's sides, so in a scrim group whose sides were chosen (`tools/scrim_ladder.py --sides`)
a match on the other sides credited our play to the opponent. Ranked groups were not affected: none of the 54,725
ranked matches on disk has its sides swapped. Now it reads each match's own sides (`EXTRACTOR_VERSION` 2).

On the three opponents both versions met (NEETCoders, Trzy Kwaterki, subscribe to caterpillow), v68 won 63.3% of 30 and
v69 69.0% of 29. Per game:

| | v68 | v69 |
|---|---|---|
| Our deaths | 6.07 | 6.83 |
| Deaths to camps | 0.10 | 0.55 |
| Deaths at an altar | 0.10 | 1.10 |
| Camp damage taken | 15.5k | 22.3k |

All are small samples. 22 of the 32 altar deaths come from one game (047ecefb-4, 03showdown): there Marcella killed
NEETCoders' Prism and took its 1061 gems (r570). She held them for 340 rounds, starting a 107-turn tribute 14 times.
Each start was cancelled under fire, the longest after 64 turns, and she died with the bag at r908, which lost the game
at 874 to 1023. This is the designed rule: `tribute_safe` judges again each turn, over at most `tribute_window` turns.
The 00anvil deaths to the Monolith come from capturing and tributing inside its reach; v68 has them too.

**A death traced exactly.** The harness puppet (`decode_all.mjs`, `gen_puppet.mjs` for the opponent's team) replays
63fd3ae8-1 (00rushbait_v2, v69 against Trzy Kwaterki) exactly in a release build: 1038 to 247, and the same positions.
A debug build matched as far as r260.

1. At r256 Issac (480 hp) dashed across the x=14 hole line and attacked Elk 16 at (16,14) alone (branch `B`, farm group 16).
2. At r258, with 360 hp, `camp_trapped` read a walk out of 4 steps. The Elk's reach had been cut to 2 because Vendetta,
   at (13,11), was 3 from it and acts first (`find_members`): Vendetta "sheltered" every tile 3 or more from the Elk.
3. Vendetta left at r259. The walk out was 6 steps, all in reach, and Issac died at r264 at (20,16).

So the shelter is right for the next camp phase only. The exit walk (`camp_exit_field`, `exit_hits`) priced it for the
whole walk.

**The fix lost.** Each member's own range was carried in `CampHit::range`, with `Safety::camp_range_area()` and
`camp_fire()` for the walk. A/B against astraeus 0c332d65 (frozen as `variants/astraeus-0c332d6`): own drafts, fast
runner, `maps/fresh-7101..7120` (unused before, 256 maps each) plus the 86 ladder maps. Diffs are in
`research/shelter-2026-11-03/`.

| Variant | Win rate of 10,412 | Ladder (172 games) |
|---|---|---|
| shelter1: both the trap test and `flee_camps` use the unsheltered walk | 47.0% (46.0-48.0) | 43.6% |
| shelter2: only `camp_trapped` uses it; `flee_camps` steps as before | 46.6% (45.7-47.6) | 45.9% |

Every suite was below 51%. Leaving the camps earlier costs more than these deaths, so the trap test's optimism is
load-bearing. Both variants were reverted. A fix would have to tell a shelter that stays (a tank on the group) from one
passing by, and nothing here does that cleanly.

## proteus ported into astraeus: dropped (2026-11-04, astraeus aa594c49 + bots/proteus 75d6d885)

Proteus is astraeus d04b171e with enemy turn windows (`turn_window.cc`), a seat ledger in the shared bytes, and seats
assigned by the chance each need is met over the feasible enemy orders (`turn_order.cc`). Every run: own drafts,
fast runner, 40,448 games on maps no A/B had used.
- **proteus against astraeus aa594c49** (fresh-61001..61079): 50.0% (49.5-50.5); out-of-fuel turns 374k against 232k.
- **Ported onto aa594c49** (fresh-62001..62079): 50.3% (49.8-50.8); out-of-fuel turns 361k against 224k.
- **With fixes** (fresh-63001..63079): 49.7% (49.2-50.2); 332k against 227k. The fixes: a 1 KB subset table filled and
  copied for every candidate need, replaced by a direct sum; an escape blow over two turns counted in both the
  unavoidable part and the seat-dependent part; a dead enemy's turn after ours counted as an unseen one's.
- **Revised** (fresh-64001..64079): 50.2% (49.7-50.6); 330k against 229k. Dead enemies' slots are unknown again
  (they set priorities: `probe-dead-priority`), an escape blow over two turns splits into its one-turn strike now and
  the rest, and the ledger and order model are made only when a need is priced (fuel only: 52/52 replays identical,
  -0.9% fuel).
- **Where the fuel goes** (census, 100 games at the real budget): the ledger and model ~0.8k a turn before the lazy
  change; the rest, ~1.2k a turn in `channels`, `s.lethal` and `want_home`, is the windows' premise itself: an unseen
  enemy may act after us while any enemy turn after ours is unaccounted for, which widens the threats.

Level in every run with about 45% more out-of-fuel turns, so the port was dropped.
