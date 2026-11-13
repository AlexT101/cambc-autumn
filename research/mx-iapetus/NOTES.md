# IAPETUS: macro refactor of charybdis (2026-11-13, 14:20-22:30 UTC)

## Status
- Time: 19:30 UTC. Final: `ia-final` (= `bots/charybdis`), held out 53.2 [52.8-53.7] over 51,000 at 2x fuel. Run ended early by instruction; no subagents or runs open.

Reference `bots/variants/chy-ref` (charybdis 529). Every A/B: `tools/ab.py variants/CAND variants/chy-ref
--no-test-draft --fuel 200000`, fast runner, release builds unless noted. Suites: `maps/suites/mx/dev` (5,100 maps),
`maps/suites/mx/hold` (5,100), mine (seeds 61451000-61459999, ladder-v4): `maps/suites/mxi/study` (61451000-002,
1,020 maps, study only, never decisions), `maps/suites/mxi/conf` (61451100-114, 5,100 maps), `train`
(61451200-214, implementers only), `fin` (61451300-314, the normal-fuel read), `x1` (61451400-414), `x2`
(61451500-514, fresh for the final confirmation; never read before it).

## Log
- 14:20 Read brief, rules, AGENTS, priors (2026-11-11 programme, mac13 NOTES, overseer candidates). Priors that
  matter: CASTOR's wins (consistent Prism gem premium, shop/farm-recall timing, Willow medic) are in chy-ref; coordination
  modes (pack, rally, escort, summon) and farm restrictions lost; solo farm reaches 1000 at ~r667, about the mirror's
  winning-bag round (the enemy barely slows our farm); economic lead of 10-25% at r300 converts ~62%; time: walk ~50%,
  hit ~18% (Prism solo), recall cycle ~23-27%; mid supply used 33%, enemy half ~0; three of five bodies capture
  almost nothing.
- 14:23 Debug mirror chy-mirror vs chy-ref on study (`mx-iapetus-mirror`): 50.0% of 2,040 (2.9 min wall). Extracted to
  `replays/.an-mirror`, narratives in `/tmp/mxi/narr`. Macro report (winner vs loser): walk 55.6/60.6%, work 29.1/25.9,
  dead 4.2/12.4, control 53.7/46.3, own-half captures lost 8/19%, contested cycles won 61/39%. Breaks: farm 53% (median
  r230), fight 37% (r426), bank 9%. Gem flow: kills 273 vs 50 gems a game (fights move more than farm: 446 vs 220).
- Capacity (both teams together): pure cluster groups' gems taken 60%, their gold 40%; wolf+cluster groups 34%;
  elk/golem groups 38%; Monoliths 9%. The cheapest gems (gem clusters, 17 HP a gem, never attack) go half unused.
- One game read end to end (gen-ladder-6145100200014, 4-pick C&I/Prism/Varg, 0 kills): both teams farm only their own
  6 groups as a blob; the Prism recalls home ~9 times by r441 (most at 100% hp: shop/transport); the race ends with
  both Prisms hoarding ~920 and B starting its 63-turn channel 13 rounds before A, which then aborts at 997 wealth.
- **Endgame races** (`/tmp/mxi/{endgame,lag,race,stuncancel}.py`): both teams reach 1000 wealth in 31% of games and the
  first there wins only 55%; winner's lag 1000-wealth -> win median 59, p75 132, p90 458. Winners' 100+ gem tributes
  are cancelled ~6 a game (stun 3,088, own 1,692, lock 1,226 over 1,020 games), ~88 channel rounds a game (median 0:
  heavy tail). At big-tribute starts the nearest enemy is 4-7 tiles away in ~60%. Stunners: Ryth, Prism, Cassi.
  `tribute_safe` checks only kill-within-11-turns: stuns (which cancel) and channels longer than 11 turns are not
  judged. -> line A (`ia-finish`): stop-ETA model (respawn timers, reach, last sightings) gating long channels, and
  the team opening the window by killing the stoppers.
- 15:10 Farm-window study (read-only subagent, 540 farm-break windows, scripts in `scripts/study/`): gap 107 capture gems a
  game, 56% mid groups (70.5 vs 10.2), 37% own home. **Giving way at contested mid groups ~45%**: winner takes 78% of
  contested mid cycles, 84% at equal headcount with equal stats; the loser's nearby bodies retreat in 23% of the next 10
  turns vs 14% and drop the target 1.34 vs 0.37 a game; give-way retreats followed by an enemy capture nearby 35 vs 6.9
  gems a game; Prism retreat turns 5.07 vs 2.49. Knock-on: home elk/golem crews don't form (~25-30%). Deaths ~14%.
  Banking/recalls/Willow not drivers. Suspect: the binary `falls` rule in `stand_lost_at` (Prism, C&I, big carriers
  leave stands the team wins). -> line B (`ia-contest`): price the give-way, commit to contested work the team holds.
- 15:40 Train reads (10,200 each, CI 95%): A-r1 (informed stop-ETA + 60-round wait) 49.7 [48.8-50.7], OOF 1120/951;
  A-r2 49.2 [48.2-50.2], OOF 1464/968. Mechanism (A-r1): big starts, completion (18.6 vs 18.9%), stun/lock cancels and
  bag deaths all unchanged: the window almost never exists (0.8% of winning-bag rounds), and waiting doesn't open one.
  B-r1 (priced give-way incl. kills) 47.5 [46.5-48.5], OOF 1370/885: retreat turns barely change, deaths 8.5 vs 7.0 a
  game (debug), Prism bag gems lost 105 vs 82; kills counted as what holding wins never come in the mirror (the loser
  leaves after killing our body). B-r2 47.1 [46.2-48.1]. Boldness at stands loses, as caution did: the study's
  correlation looks like survivor bias (the stronger side stays because it is stronger).
- 15:48 B-r3 (v3: no farm skip, stake = gems only) train 50.9 [49.9-51.8], OOF 941/849: the farm skip and the gold
  stake were what cost B 3 points.
- 15:50 **Kill-gem study** (`scripts/kills.py`, `prism.py`, `prism2.py`, mirror, 1,020 games): 50+ gem kills move 246
  gems a game from the loser vs 37 from the winner; the loser's **Prism alone loses 180 a game** (winner's 20), 128 of
  it in 300+ bags (0.21 a game vs 0.02). Prisms never tribute before their last bag (mean carried bag 392 W / 201 L).
  Loser-Prism 300+ deaths (211): 150 of 180 gems within 8 of an altar; bag+wealth < 1000 in 164 (not the winning
  bag); approaching the altar in 129; >=1 ally dead in 122; no ally within 4 in 100; enemy within 4 of that altar 15
  rounds earlier in 135; full hp 15 rounds earlier in 137. Pattern: a big Prism bag walks to an altar the enemy holds,
  often after the team lost a fight.

## Candidates
### B `ia-contest` (contest judgement; brief `briefs/B-contest.md`, log `logs/B-contest.log`, patch `patches/B-contest-final.diff`)
- Change (final): Prism, C&I, life-worth carriers and lethal tiles leave a team-won stand only when their fall
  (health + life + bag at gem value, Prism premium) exceeds the contested group's gem stake to both sides; the previous
  farm choice is kept when the team is invested and the stand reads won (not when banking or a winning capture).
- Train: r1 47.5 [46.5-48.5], r2 47.1 [46.2-48.1] (both with a farm skip of contested groups whose stand reads lost,
  and gold in the stake), r3 50.9 [49.9-51.8] (no skip, gems-only stake), r4 50.3 [49.4-51.3] (+crew expectation).
  Smoke 49.2 of 256, no failures.
- Learning: the skip read "everyone within 12, striking first" called 56% of contested stands lost and gave groups
  away: -3.5 points. Pricing + commit moves contest wins +3 points and ~20 captured gems a game but retreat counts
  barely move (priced stays ~5 a game): the give-way is mostly elsewhere (support/Prism recovery, retreat() dropping
  the claim).
- Judged (2x fuel, vs chy-ref): dev 50.6 [49.6-51.6] (OOF 979/836); held out hold 50.7 [49.8-51.7], conf 51.2
  [50.3-52.2], x1 51.4 [50.4-52.3]: **pooled held-out 51.1 [50.6-51.7] over 30,600** (OOF 2711/2544). Small but real;
  now `bots/charybdis` (best so far).

### A `ia-finish` (finish window; brief `briefs/A-finish.md`, log `logs/A-finish.log`, patch `patches/A-finish-final.diff`) — dropped
- Change: `model/stop_eta` (per enemy, the turn ends before a stun or lock could reach a channel at a tile: reach,
  cooldowns, dashes, respawns, unseen last tiles intersected with `possible`, informed by sight and wards); long
  winning channels not started where shut when another altar is open; running ones kept while their window holds;
  `finish_altar` choice; kill value for visible stoppers.
- Train (10,200 each): r1 49.7 [48.8-50.7], r2 49.2 [48.2-50.2] (wait in place), r3 49.9, r4 49.9, r5 50.1, r6 50.1
  [49.1-51.0] (OOF 994/955). Smoke 50.8, clean.
- Learning: true windows exist in 0.8% of winning-bag rounds (23 of 275 games, omniscient). Waiting works per attempt
  (r2: big starts -37%, stun cancels -48%, completion +6 points) but costs tempo and bags (lag p90 +166, bag deaths up).
  Every tribute start an enemy sees completes 2-4% (unseen 12-20%), and 1,879 of 2,383 seen starts are within 6 of an
  enemy ward: **wards watching altars** decide the finish. Gems go in bag deaths, not cancels.
- 16:45 **Ward study** (`scripts/wards.py`, mirror): big tributes with no enemy body within 8 and no enemy ward within 6
  complete 69-78%; under an enemy ward 11-12%; with a body near 11-13%. Winners start ~7 big tributes a game (66% under
  an enemy ward), losers ~1.7. Winner's wards cover 56% of altars over the last 150 rounds, loser's 47.5%. Comms carry
  no enemy sightings: a ward's view of an enemy tribute reaches only its owner. -> line E (`briefs/E-altar-watch.md`):
  relay enemy tributes, respond with stoppers, watch altars with wards in the race phase. Queued behind C.

### C `ia-territory` (live territory in farm choice; brief `briefs/C-territory.md`, log `logs/C-territory.log`, patch `patches/C-territory-final.diff`) — dropped
- Change: `may_contest` (lower bound on each enemy's arrival at a group: respawn, sight, `possible_box`, last
  sighting, recall, dashes); while an enemy is dead, a group's static weight h rises to h + (1-h)·(share of enemy
  bodies that cannot contest before our finish); prunes kept valid.
- Train: r1 49.6 [48.6-50.6], r2 (strict) 49.9 [48.9-50.9], r3 (+ force discount) 50.3 [49.3-51.3] (OOF up 38%),
  r4 (final) 49.7 [48.8-50.7]. Smoke clean.
- Learning: provably free discounted groups exist in 0.1% of farm turns (respawn + walk back beats our walk + clear +
  capture). Even an oracle frees few: only 18-24% of enemy-half groups go unapproached, and what the bot can know barely
  predicts which. Enemy-half groups are small or respawning. Forces at contested groups are nearly always matched.
  The lever left is better enemy knowledge (sightings through comms), justified on safety/fights, not farm weights.

### D `ia-prism` (the Prism's bag; brief `briefs/D-prism-bag.md`, log `logs/D-prism.log`, patch `patches/D-prism-v1.diff`)
- Finding (D's study): of the loser's 300+ Prism deaths, the largest share (81/211, 50.7k gems) come in branch E
  (`stop_game_ender`): the enemy's hoarding Prism starts its long winning tribute, our big-bag Prism runs in to stun
  it and is killed. Over 1000 games, 5,208 such runs by all bodies, 63% died within 25 rounds; the enemy channel had
  30-150 rounds left at the run's start.
- v1 (`stop_due`): stop a winning tribute only when the rounds to its last stop are within our steps + an ability
  cooldown; remember an unseen deferred ender; no stun value on a winning channel that is not due; our own tribute or
  recall cancelled only when due. On top of B.
- Train 53.6 [52.6-54.5] (OOF 1071/1185). **Held out: dev 53.0, hold 53.3, conf 53.4, x1 53.5: pooled 53.3
  [52.8-53.8] over 40,800** (OOF 3949/4099). New best, now `bots/charybdis`.
- 17:20 D ablation `ia-stopdue` (chy-ref + stop_due only) train 52.5 [51.6-53.5] (OOF 999/1178): stop_due alone
  ~+2.5, B adds ~+1 (within one read's noise; consistent with B's 51.1 held out). Mechanism (v1, 1000 debug replays):
  enemy deaths 8.5 -> 10.3 a game, ours flat; E runs 5.2 -> 3.9; bodies dead within 25 rounds of an E start 3.3 ->
  1.9; our Prism deaths 0.90 -> 0.70. The enemy's early runs at our long tributes now die to us.
- E-r1 (relay + known-tribute enders on D v1) train 52.7 [51.7-53.6] vs base 53.6 (reproduced): diagnosing.

### E `ia-watch` (altar relay, response, watch; brief `briefs/E-altar-watch.md`, log `logs/E-watch.log`, patch `patches/E-watch-final.diff`, on D v1) — dropped
- Change: a tribute record in comms (enemy, altar, tile, end mod 64, bag class; fits 76% of ladder maps) folded into
  beliefs so `game_ender`/`place_lock`/`stop_due` see unseen channels; path-timed `stop_due`; race-phase wards watch
  unwatched altars; killers also respond.
- Train vs base 53.6: r1 52.7 (end period 32 bug), r2 53.5, r3 53.7 (+watch), r4 53.6, r5 53.5, r6 53.5. Smoke clean.
- Learning: our stops replace the enemy's own cancels; it restarts and as many land (paired: landed 90 vs 93 of ~600
  win-alone attempts), while our deaths inside those channels rise (260 -> 406 in 256 games). Stopping buys only delay;
  holding the altar (lock + kill threat) would be needed to convert it.
- 17:50 D final report. Death classes before 300+ Prism deaths (mirror): E (stopping an ender) 81/211, R (retreat)
  60, T (tribute) 29, B (bank walk) 23. T/B: `closing` banks a 400-950 bag in a 40-95 turn channel; an enemy big-bag
  Prism walks in from 6-8 and one-shots it. R: our Prism spends stun/AoE on camps while an enemy Prism closes with both
  ready. D's rule patches on top of v1 (habit gate 52.2 with OOF x2.7 — caution again; keep-stun-off-camps 53.5;
  duel-first 53.7; audit fixes 53.4/53.3) all level. Final `ia-prism` (v1 + audit fixes: recall cancels on a hard stop,
  out-of-sight ender checks our bag lands first, stop_due decided once a round) held out **53.1 [52.6-53.6] over
  40,800** (paired with v1's 53.3: level). `bots/charybdis` stays v1; the audit fixes go into the final merge.
- 17:55 F launched (`briefs/F-death-audit.md`, all bodies' deaths, on v1); G launched (`briefs/G-prism-duel.md`,
  the threat model behind Prism duels, on v1).
- 18:20 F audit (v1 base, 1000 study replays): our deaths 6.56 a game (bag 229), kills 8.03 (245). The enemy Prism
  (300+ bag in 79%) lands 51% of our deaths. Commit classes (lives/gems a game): R 2.03/64, E 1.08/54, F 1.71/26, B
  0.39/35. G study: our Prism deaths 0.73 a game (128 gems); the per-turn damage bound is right (visible Prism blow
  exceeded in 0.2% of 114k turns); the misses are untracked lurkers (dropped 3 rounds after sighting) and a double turn
  across the round boundary that pick_second gives to the nearest enemy instead of the one whose strike reaches us.
  F-r1 (pick_second by strike gap) 53.1 [52.2-54.1]; G-r1 (track while `possible` is small) 52.5 [51.5-53.5], OOF up:
  both neutral or worse against 53.6. Deconflicted: G owns the Prism-killer model; F the other deaths and kills.

### F `ia-audit` (death audit on D v1; brief `briefs/F-death-audit.md`, log `logs/F-audit.log`, patch `patches/F-audit-final.diff`) — dropped
- Death table (1000 debug study games, per game): our 6.56 lives / 229 bag gems, kills 8.03 / 245. Enemy Prism lands
  51% of our deaths (bag 300+ in 79%). By commit branch: R 2.03 lives/64 gems, E (stop) 1.08/54, F 1.71/26, B
  0.39/35, T 0.07/29. E deaths are 85% in lost games; the stopped tribute was cancelled by our lock 342, our stun
  439, the channeller itself 252. Non-Prism killers 3.13/56 (Vesper last hit in ganks 1.40). Pack-zone retreats end in
  a death 1.8% vs stand retreats 0.5%; 113 stand-retreat starts a game (flip-flopping).
- Changes (rare, mechanism-correct): pick_second by strike gap (v1, 53.1, handed to G); dasher retreat by the foot
  field beside dash-only lines (v2, 53.5); price the stay when the walk gains nothing (v3, 53.6); audit fixes (v4,
  53.5). Firing ~0.2 and ~0.05 a game: neutral, not shipped.
- 18:55 Macro report of D v1 vs chy-ref (1000 release study games, `/tmp/mxi/rep-v1`): dead time 7.4 vs 9.2%,
  conversion 67.5 vs 63.4%, contest_win 51.8 vs 48.2, outnumbered 13.7 vs 15.8%; no loss cluster with a clear excess.
- 18:58 H launched (`briefs/H-stop-execution.md`: who stops and how, on D final), the largest remaining class.

### G `ia-duel` (Prism threat model; brief `briefs/G-prism-duel.md`, log `logs/G-duel.log`, patches `patches/G-duel-v*.diff`)
- Findings: the one-turn damage bound is right (visible enemy Prism blow exceeded in 0.2% of 114k turns). Errors: the
  slot before ours goes to the nearest enemy, not the one whose strike reaches us (64 big-bag deaths read safe); the
  3-round tracking horizon drops lurkers (40 deaths to untracked killers, last seen median 44 rounds earlier, median 4
  tiles away); the escape plan gives a ranged pursuer no walk-and-cast across the round boundary. The duels are
  lopsided: the enemy Prism's stun alone kills us in 175 of 186 big-bag deaths (ours kills it in 39).
- Train: r1 (track while possible small) 52.5, r2 (v2 pick_second by blow) 53.7, r3 (+per-enemy credible tracking)
  53.7, r4 (+escape straddle, audit) 53.3, r5 (v4 without tracking) 53.1 — all level with 53.6.
- Mechanism (v4 vs base, 1000 debug games): Prism deaths 0.73 -> 0.58, bag lost 128 -> 95, 100+ bag deaths 0.278 ->
  0.221, tributed 273 -> 264, working time ~85%: the bag saved shows up as a more cautious Prism, not as wins.
- 19:06 judging v2 (`ia-duel`) and v4 held out (`mx-iapetus-G2-held`, `-G4-held`).
- 19:16 G held out (paired with v1's 53.3 and D final's 53.1 on the same 40,800): **v2 53.6 [53.1-54.1]** (OOF
  4404/4091, +11% vs v1), v4 52.4 [51.9-52.9] (OOF 4986): v4's bag savings cost wins (a more cautious Prism); v2's
  pick_second fix is level-to-slightly-up (+0.3 held out, +0.1 train). Merge implementer building `ia-final` =
  `ia-prism` (D final) + G v2's pick_second.

### H `ia-stop` (stop execution; brief `briefs/H-stop-execution.md`, log `logs/H-stop.log`, patches `patches/H-stop-v*.diff`) — stopped by instruction, neutral
- Train vs ia-prism 53.3: v1 (stun before lock; lock now when the ring is lethal) 53.3, v2 (leave a lock stop to a
  ready ally stunner) 53.5, v3 (lock inside stun reach, both in one turn) 52.9, v4 (lethal-ring stunner defers) 53.4.
- Learning: stun stops (0.75 a game) lose the stopper within 12 rounds 38% of the time, lock stops (0.34) 84%;
  channellers are rarely killable (median health ~3,400), and they restart at the same altar after ~89% of stops. A
  Prism's ground cast reaches 5 against our stun's 4: the stun ring is a death zone, whoever stops.

## Final: `ia-final` = `bots/charybdis`
- `ia-final` = D final (`ia-prism`: B contest pricing + D `stop_due` + D audit fixes) + G v2 `pick_second` ordering
  (only `model/turn_window.cc`). Built release and debug; read-only audit clean (one open logic gap: a stunned enemy
  that already acted still gets a positive blow in `pick_second`; not a regression, unfixed to keep the measured v2);
  smoke 50.4 of 256, 0 failed, no DRAFT-UNFINISHED / PLAN-CHECK. Diff vs chy-ref: `patches/final-vs-chyref.diff`.
- Held out at 2x fuel vs chy-ref: dev 53.5 [52.6-54.5], hold 53.0 [52.0-54.0], conf 53.7 [52.7-54.7], x1 53.1
  [52.1-54.0], fresh x2 52.9 [52.0-53.9]: **pooled 53.2 [52.8-53.7] over 51,000** (OOF 5339 / 5018). Paired: D v1 on
  the four older suites 53.3, on x2 53.4 (OOF 967/947): level with v1 (-0.1 to -0.5, within noise), with D's audit
  fixes in. Committed as `bots/charybdis` per the coordinator; the normal-fuel read is the coordinator's.
