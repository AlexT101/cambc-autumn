# Family A: retreat/advance flip-flops: findings (phase 1)

Groups: A1 standlost (14.2k episodes, 230k turns), A2 outmatched (1.6k, 22k), A3 retreat stuck/ping-pong (1.7k,
35k), A4 Willow (0.8k, 11k). Line numbers are `bots/astraeus/src` unless stated.

## Method

- `bots/variants/astraeus-trace-A`: the trace bot plus `debug_block` prints, each written so that it only reports
  values the original code computes anyway, in the same short-circuit order:
  - `SA`: `want_home`'s stand inputs and outputs. Fields: pursued, paying_soon, own_ground, bag, lethal, linked, t.lost,
    self_falls. Then per seen enemy: position, visible, age, hp, `fight_reach` R, Chebyshev d, `approach` w
    (`*` = counted as a walker, `-9` = beyond the horizon).
  - `RC`: `continue_recall`'s keep test, term by term, plus the enemy that failed `recall_outruns`.
  - `PK`: the pocket keep.
  - `OM`: pack members when outmatched.
  - `KO`/`WG`: `keep_out` bits and the work-guard tiles.
  - `WL`: Willow's `threat_at` terms.
- Sample: 87 games covering 42 A1, 16 A2, 18 A3 and 13 A4 episodes (the longest on distinct maps, plus random ones
  weighted by length), rerun with fastrunner. 82 of the 87 episodes reproduce exactly in their window. Some games drift
  outside it on fuel-gated turns (the ~8-fuel debug cost); those were checked per episode.
- The original replays' stdout is truncated to its last 1 MiB, so their first rounds have no D lines.
- Ground truth came from `extract.mjs`. Terrain reachability came from a BFS over walls, holes and altars: king steps
  plus one 2-step dash for dash champions, with camp tiles treated as walkable (a lower bound).
- Prevalence figures below come from this sample, so they are rough (±10 points). The long-tail episodes (>200 turns)
  are 26% of A1's turns; the rest is many short episodes.

## Sub-issues, by turns wasted

### 1. Mutual dances: the enemy oscillates in antiphase (A1 ≈ 29%, A2 ≈ 95% of real R turns, some of A4; ≈ 80k turns)

**Examples**
- `replays/batch-20261104-021721-ab-osc-trace-v68-fresh-gen-s1/435-gen-topo-tree-600206416-12.repl26a`, team A, h4
  Marcella, r1600-1933 (A2). Coupled 4-cycle.
  - Enemy Marcella (v68, 4500-5000 hp) walks (21,27)→(22,28)→(23,29), tries a move to (25,30) that is `blocked`, then
    walks back.
  - Ours walks (27,27)→(28,28)→(29,29) as it comes and back as it leaves.
- `replays/batch-20261104-021623-ab-osc-trace-v65-gen/315-gen-long-thin-600104708-12.repl26a`, team A, h1 Cassi,
  r611-752 (A2). Enemy e7 alternates (40,27)↔(41,28) as ours alternates (47,23)↔(46,24).
- `replays/batch-20261104-021623-ab-osc-trace-v65-ladder/072-00vault-21.repl26a`, team B, h6 Prism, r431-1850 (A1,
  706 R turns). Enemy e0 alternates (12,20)↔(11,20) in antiphase.
- `replays/batch-20261104-021838-ab-osc-trace-v61-gen/328-gen-mega-groups-600108208-21.repl26a`, team B, h3 Cassi,
  r814-1982 (A1). Enemy Marcella alternates (19,23)↔(20,24); parity (sub-issue 3) is mixed in.
- Also: 186-gen-dungeon (A2, HoR), 033-gen-arena-600102622 (A2, Cassi), 355-gen-topo-capital (A1 and A2, Issac).

**Board**
- A healthy champion farming, banking or sieging next to an enemy (often a big-health one) that is itself in a loop.
- In the A2 cases the enemy moved between our two turns in 323 of 329 R turns.

**Mechanism**
- Every test is a snapshot of where the enemy stands this turn, with no memory of where it was last turn:
  - `in_pack_zone`: guard.cc:155, members with age ≤ 1 at their current position.
  - `stand()`: safety.cc:2768.
- The work guard's `keep_out` only considers enemies within `pack_radius + 1` of our tile (`work_around`, guard.cc:641
  onwards). An enemy one step further out that steps in on its own turn is never predicted, so F/B steps forward.
- On our next turn the enemy is in range: `home:outmatched` (fight.cc:379) or a lost stand, and we retreat. The enemy
  then steps back (its own flip), and the cycle repeats.
- Confirmed for A2 by OM/KO lines: `KO` is absent (`keep_out` returned 0 at `work_around`) on 297 of the 329.
- The opponents are older versions of our own bot, so both sides deter each other. Collision and topo-tree show the
  enemy carrying 400+ gems in its own 2-cycle.

**Confidence**: confirmed by trace; how often this happens against ladder opponents is unknown.

**Fix directions**
- Hysteresis: after a `home:*` retreat, keep the triggering enemies' positions from the last 2-3 rounds as a keep-out
  zone for the work guard (a few vec2s in Memory). Or require the zone to be clear by one extra step before
  re-entering.
- Or treat an enemy's last two positions as both occupied, which matches its 2-cycle.
- Risk: farming less near enemies that really leave; stuck rather than ping-ponging when the work's only route goes
  through the zone.

### 2. Pursuit-horizon cliff: a stand lost only to walkers, unguarded and without hysteresis (A1 ≈ 25-30%; ≈ 60k turns)

**Examples**
- `replays/batch-20261104-021623-ab-osc-trace-v65-ladder/122-02stalactites-21.repl26a`, team B, h8 Willow, r144-2000,
  77 gems, B↔R between (20,9) and (19,10), 927 R turns.
  - Three enemies sit still on camp tiles (14..15,16..17) for 1,800 rounds.
  - At (19,10) they read w1/w2/w2 and the stand is lost; at (20,9) all are 3 or more past reach.
- `replays/batch-20261104-021838-ab-osc-trace-v61-ladder/070-00the-line-21.repl26a`, team B, h7 Prism, r477-1939,
  78 gems, F↔R (24,22)/(23,23).
  - Two stationary enemies on camp tiles (27,16) and (26,16).
  - At (24,22): e0 w1 and e3 w2, lost. At (23,23): e0 w2 only, not lost.
- `replays/batch-20261104-021547-ab-osc-trace-v67-fresh-gen-s1/160-gen-dash-lattice-600207618-21.repl26a`, team B, h5
  Issac, r902-1954, 49 gems, B↔R (39,29)/(40,30). Enemy e0 is still at (36,23): d6 w2 versus d7 w3.
- `replays/batch-20261104-021759-ab-osc-trace-v66-ladder/139-03fan-12.repl26a`, team A, h5 HoR, r680-725. The enemy
  waits at an altar.
- **Terrain-blind variant**: `replays/batch-20261104-021505-ab-osc-trace-v69-ladder/128-02the-pond-21.repl26a`, team B,
  h4 Cassi, r407-1464, 48 gems, B↔R (5,12)/(6,11), 528 R turns.
  - At (6,11): Issac (12,12) R4 d6 w2* and HoR (13,13) R5 d7 w2*, lost. At (5,12): w3, not lost.
  - Both enemies sit on a 44-tile island in the pond (rounds 400-1470, with 21 and 49 gems). BFS: no route to us,
    with or without a dash.
  - The only bank route to the altar (3,7) passes (6,11), next to a wolf camp.
- **Spawn-edge variant**: `replays/batch-20261104-021505-ab-osc-trace-v69-ladder/008-00collision-21.repl26a`, team B,
  h7 Marcella, r800-852, 25 gems.
  - On spawn tile (5,38) `want_home` returns false at once (fight.cc:369). Bank steps off to (6,38), where the stand is
    lost to Marcella (13,31) at w2*, so it steps back on.
  - The enemy, carrying 428 gems, alternates (14,30)↔(13,31).
- **Joiners variant** (an enemy in reach plus walkers): see sub-issue 3's last paragraph.

**Mechanism**
- `want_home` calls `stand(here, pursued ? pursuit_steps : 0, …, joined = pursuit_steps)` (fight.cc:399, params.h:128,
  `pursuit_steps = 2`).
- `stand` (safety.cc:2768-2800) counts every visible enemy whose `approach()` is 1-2 as a walker joining the fight.
- `approach()` (safety.cc:2238-2242) is Chebyshev distance past reach: `max(1, dist(p, acts_from(e)) - reach)`. It
  ignores terrain, which causes the pond and moated cases.
- So one step toward a stationary enemy moves it from w3 (ignored) to w2 (counted), and the fight flips to lost.
- The work guard deliberately does not price "stands lost only to pursuers" (guard.cc:620-627). The step guard prices
  `fight_key(q)` fights (safety.cc:2542), which hold only enemies whose blow hits q, and no `late()` walkers.
- So F/B/G/X step onto the tile and `want_home` sends us back from it next turn. `retreat_step` (fight.cc:178) moves
  one tile homeward, which is enough to drop the walker, and nothing remembers the decision.
- `pursued` is forced for carriers (`bag_at_stake ≥ brake_bag = 22`, fight.cc:395-397), which is why most long ones
  carry 25-80 gems. They never bank: the bank route keeps aiming at the altar the walkers watch.
- EXPERIMENTS (CHANGES 269, "Hold rule and the work guard") tried pursuers in the guard: about 2.3x the out-of-fuel
  turns and no measured gain. "Pricing only the tile the step takes (a lazy veto in `try_move`)" is listed as untried.

**Confidence**: confirmed by trace (SA lines on both tiles of each cycle). Terrain variant: confirmed by BFS plus
ground truth.

**Prevalence**
- About 33% of the long-tail A1 turns and about 17% of the rest.
- Terrain: 1 of 16 long episodes (1,058 turns).
- Spawn edge: about 4% of short episodes.
- Enemies were stationary in 4,778 of 9,395 counted-enemy samples, 4,738 of them on camp tiles.

**Fix directions**
- (a) A lazy veto in `try_move`: one `stand()` with the pursuit horizon for the tile the work step actually takes, at
  about one fight simulation a turn near enemies, not eight. Retry the next-best step once.
- (b) Memory: a tile where `want_home` said "lost to walkers" is guarded for N rounds while those walkers stay within
  1 of where they were.
- (c) Terrain-aware `approach()` for w > 0: the enemy's walking or dash distance from a flat-price `distance_field`
  per visible enemy, cached per turn. This also fixes `recall_outruns` (sub-issue 4) and `late()` (safety.cc:2604).
- (d) Stationary enemies (same tile for k rounds, visible, not in a bush) count as walkers only once they move.
- (e) For carriers: when the bank's only route is vetoed, try another altar, or wait or recall, rather than walking
  into the veto.
- Risks:
  - (a) and (b) can leave the champion idle when the vetoed tile is on the only path. That still beats ping-pong only
    with (e).
  - (c) costs fuel per visible enemy.
  - (d) walks into ambushes (dash champions waiting at their reach edge).

### 3. Turn-order parity: an enemy's reach alternates each round (A1 ≈ 17%, part of A4; ≈ 35-40k turns)

**Examples**
- `replays/batch-20261104-021505-ab-osc-trace-v69-gen/336-gen-moated-altars-600108109-21.repl26a`, team B, h8
  Marcella, r744-1924, 75 gems, B↔R (32,40)/(31,39), 590 R turns.
  - Enemy Prism e2 (25,36) is stationary across the moat.
  - At (31,39) it reads R6 d6 w0, lost. Next round at (32,40) it reads R5 d7.
- 328-gen-mega-groups-600108208-21 (above): Marcella reads R5 at d5 in even rounds and R4 in odd rounds, with the same
  cooldowns (0,0).
- `replays/batch-20261104-021721-ab-osc-trace-v68-gen/284-gen-huge-600101300-21.repl26a`, team B, h9 Prism, r435-470.
- `replays/batch-20261104-021721-ab-osc-trace-v68-gen/304-gen-lakes-600100500-21.repl26a`, team B, h5 Cassi,
  r346-364.
- A4: `replays/batch-20261104-021721-ab-osc-trace-v68-ladder/009-00contest-12.repl26a`, team A, h4 Willow, r439-453.
  - Vesper (14,34) is stationary. At (8,29) `threat_at` reads `T6 vis R6 d6 hit1`, giving `home:willow`.
  - From (7,28) the next round it reads R5, so the stations guard lets F step back.

**Mechanism**
- `threat_strike()` (safety.cc:990-996) widens a strike by a walk when `turns_before_ours(e) ≥ 2` (safety.cc:948-955).
  That happens when the enemy acts after us this round and before us next round.
- Team A starts odd rounds and team B even rounds, so for a given pair this holds on alternate rounds.
- In a one-turn round the work guard or Willow's stations guard (guard.cc:600-608) judges the destination with the
  narrow reach and allows it.
- The next round, `want_home` judges the same tile with the widened reach (+1) and leaves. Then the round after is
  narrow again.
- `retreat_step`'s comment (fight.cc:172-177) already notes "an enemy reach that alternates with turn order walks us
  back" for the retreat itself.

**Confidence**: confirmed by trace: R alternates with round parity for a stationary enemy with constant cooldowns.
The R drop between the R turn and the next turn shows in 949 of 6,282 sampled R turns.

**Fix directions**
- The work and stations guards should price a destination with the reach `want_home` will use from it next turn: the
  union of both windows, or `turns_before_ours` evaluated for next round.
- Or `want_home` could keep a "lost last turn at this tile" memory.
- Risk: the guard becomes more conservative every round (less farming at reach edges). Fuel is small: the reach is
  already memoised per round (`strike_memo`).
- **Joiners**: in 2,068 of 2,734 "in reach" R turns there were also enemies 1-2 steps past reach.
  - `stand()` adds them (`joined`, safety.cc:2785-2790); the step guard's `fight_key` fights do not.
  - So a tile where one weak enemy can hit us looks safe to the guard. Example: 315-gen-shared-gems-600201608-12,
    team A, h1 Cassi, r530-2000, G (kite) ↔ R, 728 R turns. Issac 430 hp at d5 = R5, plus three joiners at d6.
  - Same fix family as sub-issue 2 (a). The key is already simulated there, so adding the `late` walkers is cheap.

### 4. Stranded in a pocket: no walk home and the recall cancelled every turn (A3 long tail; 8.1k distinct turns in 18 games, game-deciding)

**Examples**
- `replays/batch-20261104-021623-ab-osc-trace-v65-fresh-gen-s1/055-gen-atoll-600201904-12.repl26a`, team A, h4 HoR,
  r156-1940, 61 hp, on the central island.
  - Entered by teleport crystal at r87-90; the island's hole ring is wider than a dash.
  - Recall starts every turn end and is cancelled ('manual') at the next turn start, 1,785 times.
- `replays/batch-20261104-021505-ab-osc-trace-v69-gen/336-gen-moated-altars-600108109-21.repl26a`, team B, h7 Prism,
  r747-1925, **815 gems**, 14 hp, inside the moat around altar (30,40).
  - All four of our champions are inside the moat. Enemy Cassi, Prism (671 gems) and Marcella stand at the moat edge
    (25,35..37); none has a dash, so they cannot enter.
  - We lost the game.
- `replays/batch-20261104-021547-ab-osc-trace-v67-fresh-gen-s1/160-gen-dash-lattice-600207618-21.repl26a`, team B, h4
  Cassi, r896-2000.
- `replays/batch-20261104-021838-ab-osc-trace-v61-fresh-gen-s1/062-gen-atoll-600201911-21.repl26a`, team B, h5 Cassi,
  r653-1389.
- `replays/batch-20261104-021851-ab-osc-trace-v69-f77131-fresh-77131/414-gen-topo-split-7713106504-21.repl26a`, team
  B, h8 Cassi, r611-1101.
- `replays/batch-20261104-021505-ab-osc-trace-v69-gen/331-gen-moated-altars-600108100-12.repl26a`, team A, h3
  Marcella, r398-664.

**Board**
- The champion is hurt (`home:low`), or healthy but `standlost`/`selffalls` in the moated cases.
- It is on an island, inside a moat, or in a dash-lattice cell. BFS shows no walking route to its own spawn in **all
  45** A3 stuck episodes of 50+ turns.
- Maps: gen-atoll, gen-moated-altars, gen-dash-lattice, gen-topo-split, gen-fortress, gen-continent.
- Enemies watch from across the gap, often stationary.

**Mechanism** (RC/PK lines, every turn of every long example)
- `continue_recall` keeps the recall only if `want_home && !walk_beats_recall && !threatened && !can_tribute_safely
  && recall_outruns` (bank.cc:1159-1162).
- `recall_outruns` (bank.cc:1066-1074) fails because some visible enemy has `approach() ≤ 5`. `approach()` is
  Chebyshev (sub-issue 2): `ap1`-`ap4` for enemies who cannot cross the holes or moat. Atoll HoR: Vendetta (26,17),
  Chebyshev 5, BFS unreachable even with its dash.
- The pocket keep (bank.cc:1176-1180) then fails in two ways, regardless of `want_home`:
  - `PK foot0 fg11 pocket0`: the farm group is inside the same pocket, so `beyond_walk` (farm.cc:101-106) returns
    false ("farm there"). Atoll HoR, dash-lattice Cassi, topo-split Cassi.
  - `pocket1 banking1` with gems > 0 ("bank there"). Moated Prism with 815 gems, atoll Cassi, moated Marcella.
- So the recall is cancelled, `retreat` runs, and `to_ally_spawn` is unreachable. Its walks fail (`d-`, `d-d-`) or
  shuffle, and the champion idles for the rest of the game.
- Nobody damages it, so a kept recall would have landed in 5 turns.

**Confidence**: confirmed by trace (RC and PK lines) for 6 long examples; BFS for all 45.

**Prevalence**: 21 champion spans, 8,118 turns, 18 games (after removing overlapping stuck_fail/stuck_idle episodes).
This is about 40% of A3's turns. Per game it is the costliest sub-issue: the moated game lost an 815-gem bag.

**Fix directions**
- When `want_home` holds and our tile has no walk home (`!on_foot(here)` or `to_ally_spawn` unreachable), keep the
  recall unless `threatened(here)`. Damage cancels it anyway, so nothing is lost by trying.
- A terrain-aware `recall_outruns` (as sub-issue 2 (c)).
- Upstream (economy, not A): don't crystal into, or stay in, a pocket below the recall line without an exit.
- Risk: very low. A recall from a pocket the bot could still farm loses the farm, but only while `want_home` says
  leave.

### 5. Vision toggle: from the other tile the enemy is out of sight (A1 ≈ 10%; ≈ 20k turns)

**Examples**
- `replays/batch-20261104-021623-ab-osc-trace-v65-gen/245-gen-gem-flood-600105900-12.repl26a`, team A, h2 Issac,
  r441-879, F↔R (45,26)/(44,25), 218 R turns.
  - At (44,25) enemy e7 at its altar (40,25) reads R3 d4 w1*, lost.
  - At (45,26): `SA unseen`.
- `replays/batch-20261104-021505-ab-osc-trace-v69-fresh-gen-s1/428-gen-topo-tree-600206400-21.repl26a`, team B, h10
  Prism, r957-973, 202 gems.
- `replays/batch-20261104-021759-ab-osc-trace-v66-gen/212-gen-far-altars-600108707-21.repl26a`, team B, h4 Issac,
  r566-577.
- Also 00collision h7, 176-gen-dungeon h8 (enemies at altars or behind walls/bushes).

**Mechanism**
- `want_home` returns false when nothing is lethal and no enemy is visible: `if (!lethal && !enemy_seen(world))`,
  fight.cc:392. `enemy_seen` counts visible enemies only (world.h:605).
- Stepping behind a wall or bush edge drops the enemy, the work steps back into sight, and the stand is lost again.
- `stand()` itself can price tracked unseen enemies (`seen_enemies()` includes tracked ones, plus the `unseen` flag),
  but the early return skips it.

**Confidence**: confirmed by trace.

**Fix directions**
- Don't take the early return while an enemy seen this round or last (age ≤ 1) would have been counted. Or let the
  work guard keep a tile we left for an enemy we can no longer see.
- Risk: more retreats from enemies that really left; small fuel cost.

### 6. Own-ground line: the `pursued` exemption flips across it (A1 ≈ 10% of short episodes; ≈ 15-20k turns)

**Examples**
- `replays/batch-20261104-021838-ab-osc-trace-v61-ladder/109-02famine-12.repl26a`, team A, h2 Issac, r595-641.
  - At (43,54): `own0`, pursued, lost to e10 at w2.
  - At (42,53): `own1`, healthy, not pursued, so F steps back to (43,54).
- `replays/batch-20261104-021759-ab-osc-trace-v66-fresh-gen-s1/012-gen-altar-poor-600201007-21.repl26a`, team B, h5
  Issac, r464-505: (29,30) `own0` versus (30,29) `own1`.
- Also gen-classic-600200008-21 h3 Cassi.

**Mechanism**
- `pursued` is false on own ground when healthy and the bag is small (fight.cc:395-397, `own_ground` guard.cc:29), so
  `stand` gets approach 0 and the walkers are dropped.
- One step across the line the walkers count again. The work guard ignores walkers (sub-issue 2), so nothing stops the
  step off.

**Confidence**: confirmed by trace (`pur`/`own` fields on both tiles).

**Fix directions**
- Hysteresis on the line: judge `own_ground` with a 1-2 step margin, or with the tile we came from.
- Or the sub-issue 2 (a) veto for the step that leaves own ground.
- Risk: slightly more passive near the midline.

### 7. Retreat ping-pong under real pressure (A3 short episodes; ≈ 15-20k turns, partly legitimate)

**Examples**
- `replays/batch-20261104-021505-ab-osc-trace-v69-ladder/127-02the-pond-12.repl26a`, team A, h2 Marcella, r66-307,
  `R` only, (20,22)↔(21,21) with `m+` single moves.
  - It is wedged between a wolf camp (21-22,21-22) and enemies on the pond island.
  - `RC thr1`: the recall is cancelled as threatened.
- `replays/batch-20261104-021838-ab-osc-trace-v61-ladder/053-00reverse-spiral-12.repl26a`, team A, h4 Ren, r438-444,
  160 hp, 44 gems.
  - The route home fails (`r-d-m+`); `retreat_step` alternates (2,24)↔(3,24) with Prism (6,18) at `ap1`.
- 234-gen-gem-drought h6 HoR, 432-gen-topo-tree h5 Issac, 246-gen-labyrinth h9 Marcella: an enemy at d1-d2 with both
  sides losing hp.

**Mechanism**
- `retreat_step` (fight.cc:178-270) ranks steps by priced damage, and the enemy's reach alternates with parity
  (sub-issue 3), so the "clear" step alternates.
- The route home passes the pursuer or a camp, so `step_towards(home)` fails.
- These are real engagements: most A3 `<20`-turn ping-pongs show hp falling.

**Confidence**: likely (D, RC and SA lines on 6 examples; `retreat_step`'s per-option prices were not logged).

**Fix**: low priority.
- Make `retreat_step` prefer the option it took last turn when the alternatives price equally.
- Or price with both windows (sub-issue 3).
- Separately, entering a sealed camp ring with too little health (`mut-elkring-600101836-12`, h2 Prism with 92 gems,
  `camptrap`) has no exit: camp hits cancel every recall. That belongs to economy (B), not A.

## False positives / mis-grouped (phase 2 can skip or regroup)

- **Episodes that are not R flips**: episodes where R is under 20% of turns are mostly F/B/G ping-pongs that picked up
  one or two `home:*` turns. That is 10% of A1's turns, 29% of A2's and 40% of A4's. They belong with C1, C2 or B4.
  Examples:
  - A2/A1 `…v61-ladder/072-00vault-21` h8 HoR, r102-1645: 1,538 turns, 4 R.
  - A4 `…v65-ladder/121-02stalactites-12` h4 Willow, r297-1830: 1 R.
  - A1 `…v61-gen/374-gen-shared-gems-600101605-21` h5 Cassi, 1,843 turns of G (kite), 3 R.
  - A4 285-gen-monolith, 279-gen-hole-maze, 287-gen-monolith-only, 052-gen-arena: 1 R each.
- **A3 short R-only ping-pongs in active fights** (sub-issue 7): mostly real retreats under pursuit.
- **Mutual dances** (sub-issue 1) are real waste, but they are a property of playing our own lineage. Count them
  separately from the ladder impact.

## Not pinned down / remaining

- What each stationary enemy is doing: frozen on camp tiles (stalactites, the-line) or at altars or the moat edge for
  hundreds of rounds. It looks like the mirror image of our flips or of B3 idling, but baselines print no traces.
- The joiners share of sub-issue 3 overlaps with parity, so their separate prevalence is not measured.
- Willow: only 4 A4 episodes were checked with `WL` lines: contest (parity), topo-necks (dance), starfish and
  lost-world (real nearby threats). Willow's stations guard was not instrumented.
- A3 short `camptrap`/`campfled` episodes (233 + 16 dominant) were not examined.
