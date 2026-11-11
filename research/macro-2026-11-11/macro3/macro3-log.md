# macro3 log (lead's running notes)

Brief: research/macro-2026-11-11/macro3-brief.md. Worktree /home/ubuntu/wt/macro3, branch macro3-20261111.
Reference: bots/variants/ocean-ref-b7c87cf (never edit). Candidates: bots/variants/macro3-*.
Every A/B: `--no-test-draft --fuel 200000` vs variants/ocean-ref-b7c87cf only. Target 60%+ over 10k+.

Prefix:
```
source /home/ubuntu/venv/bin/activate && export PATH=$HOME/.cargo/bin:$PATH CAMBC_SLOTS=86 CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
```

## Maps
- /home/ubuntu/wt/macro3-maps/s-300001 .. s-300040: ladder-v2, 256 maps each. Plan: 300001-300020 screening (10k games),
  300021-300040 confirmation. Later seeds 300041+ for fresh confirms.

## Timeline
- 2026-11-11 start: read brief, AGENTS.md, rules. Launched two read-only surveys (prior macro research; ocean macro
  architecture). Generating map suites.

## Survey digests (2026-11-11, from two read-only agents)
Prior macro history (most on astraeus, ocean's ancestor):
- Master pattern: gains came from keeping champions working (fewer retreats/heal trips, min_bank 25 +3.7, max_wait 0,
  threat-aware recall line, recall-to-farm, quill crew economics +9 mostly via fewer deaths). Everything moving bodies
  toward each other or toward fights LOST (duos, packs, leashes 18-46%, burst ops 45.6%, hunt ops -1.5..-5, cohesion
  leans 46-49, movement-coupled pack -0.8, engage-on-numbers -1.9). Reason: off-farm time costs what it gains.
- Burst op failure reason: valuation mismatch (instant solo rate vs long-run rate) -> calls unmanned. Untested fix.
- Enemy sightings in comms lost every time (allies give way to enemies they can't see; fuel).
- Contest/steal/deny: level. Locks: local gains reversed live. Comms off -6; camp record ~7 pts; claims ~3.5.
- Mirror: side dying first loses ~70%; +1 net kill at r300: 56%->85%. 88% of deaths follow a retreat; 63% of kills
  during/within 3 rounds of a retreat, 28% of those start at 95%+ health. Winners 2.5 deaths vs 5.4.
- Turn budget (astraeus mirror): walking empty 31-35%, with bag 18-20%, camp hits 17%, hold 5-7%, recall 4-7%, dead 3.5-7.6%.
  Spawn/recall walks out 18.7% of alive time. Camps abundant (4.0 of 6.7 gems/round up at any time): champion time binds.
- Fish (ladder) packs: nearest ally median 2 tiles, 1.54 mates within 5 vs our 1.14; packing emerges from JOINING
  (later decider follows earlier one's group 89-91%), team-union camp memory; Golems are team clears; equal hazard at
  equal numbers but more bodies at contact. Copying Fish wholesale: 23.6%.
Architecture (ocean):
- decide() is a fixed priority ladder (bot.cc:366-519). farm_turn (farm.cc:639, ~1850 lines): value = rate(worth,
  trip+clear+capture+trips_home), rate = w/(r(1+r/horizon)), horizon 100*max(1,side/50). worth = home_ground weight
  (static spawn-distance ratio ^1.89) * exposure (mid band x1.36) * (gems + per_gold*gold) - toll. Enemy champions
  barely enter the per-group value (binary vetoes only). Claims first-come; crews by proposal/timeout (crew.cc).
- No enemy intent model: no prediction of enemy farm target/route/tribute; out-of-sight enemy captures not inferred.
- want_home thresholds; pack zone (guard.cc) reactive; chase pre-empts farm if fight not lost.
- Comms (comms.cc lay_out): claims per ally, one bag slot, one camp-respawn record, ally positions (only with healer),
  ~12 bits free. Priority low 16 bits: claim, support mailbox, chase bit; enemy can read it.

## Study of 1024 debug mirror games (study-309901/2; interim numbers from replay-study agent)
- Exactly 50.0% (deterministic mirror). Median game 761 rounds; 2.3% reach r2000; loser median 527 gems at end.
- Winner vs loser: deaths 2.2 vs 6.0, kills 6.0 vs 2.2, gems lost 43 vs 151, capture gems 1023 vs 804.
- Death anatomy: 74-84% of victims were in retreat (R) in their last 3 turns; healthy at fight start (hp 0.80-0.85);
  "even/ahead group fight lost" 33-45% of deaths (our numbers >= theirs within 8 at fight start), caught alone 2+ ~10-13%,
  1v1 7-10%, bag carry ~10-12%, outnumbered group 9-10%, stopping an enemy ender 20% of LOSER deaths (late desperation).
  76% of deaths have an ally within 8 (nearest ally median 2-4 at death). 30-38% one-round kills (burst focus fire).
  Mid zone 70-78% of deaths. First death: victim hp share within 8 = 0.47; enemies<=8 2.68 vs allies 1.91;
  first-death killer was FARMING in 55% (opportunistic kills by bodies at work).
- P(win | lost first champion) = 0.33; lost first two 0.24.
- Contacts ~77/game. P(contacted champ dies in 15r) by numbers within 6: 1v1 7.0%, 2v1 6.3%, 4v1 5.5%, 1v2 9.3%,
  1v3 14.8%, 1v4 33.7%: numbers barely protect. Local HP share is the strong predictor (AUC 0.69 vs numbers 0.58):
  share>=0.7: P(me die) 3.4% vs P(enemy loses one) 22.4%; 0.55-0.7: 5.5/11.2; 0.45-0.55: 8.1/7.3; <0.3: 25.8/3.1.
- Retreat (R) episodes 70-85 per game, median 2-3 turns, start at hp 0.8 with hp share ~0.51-0.56.
- Unspent gold small (median 15-30): shopping cadence is not a lever.
- Time: walking 54% (empty 28, bag 26), camp 17-18, hold 7-8, recall 4-5, dead 4 vs 9.6.

## Final study report highlights (replay-study agent)
- Pattern H (group fight lost at even/better numbers) 33-45% of deaths: victim had 1.5-1.7 allies within 4, yet in
  60-62% of these deaths the nearby allies dealt ZERO damage; victim side's damage ratio 0.35-0.49; only 7-21% traded.
  The enemy focuses one body (1.6-1.8 attackers) while ours farm on or retreat one by one.
- Retreat paths go to spawn (fight.cc retreat / dash_retreat_casts use pathing.to_ally_spawn()), not to teammates.
  Retreats making no progress home die 17.6% vs 3.8%.
- Cassi&Issac most-killed pick (bodies >8 apart 52% of alive time). Bag deaths carry 92-117 gems.
- Half of the loser's deaths come while already a champion down (cascades). Economy at r150 nearly equal; deaths
  trigger the divergence.
- First killers mostly farming (F) - fights start as farm collisions in the middle.

## Plan (v1)
- Track 2 (launched): macro3-window = "numbers windows": enemy bodies on the field at a group by job end (alive +
  dead whose respawn + walk from spawn beats the job) over our alive bodies = f_g; home_ground^(f_g) farm weight;
  preyable lifts the own-ground rule when f<1 at the target. Exactly inert with full teams.
- Track 1 (next, after mechanism follow-up): team engagement (commit/disengage together, allies join a focused
  teammate's fight, retreat toward allies).
- Helper follow-up (H deaths): allies within 6 helped only 29-30%; non-helpers out of reach & not closing 31-35%,
  retreating themselves 28-37%, hitting a camp 13-16%; only 6-7% of non-helpers were ever in their attack range;
  distance to victim grew 3.0->4.3. Killing team: 78-79% helped, chase 20% of turns, 33-35% closed by 2+, enemy in
  range 58-62%, half fought through damage. Median 2 rounds first hit -> death. Mechanism: attackers hit the edge body
  of a loose farming group; ours keep farming/retreat individually; theirs converge (prey/team_pressed pull them in on
  a hurt fleeing target, nothing pulls ours toward healthy attackers).
- Prior (EXPERIMENTS ~7965, 1710-1730, 6527): power-play windows 50.7% (old bot), peeling 49.8-49.9, covering a
  fleeing mate 49.3-49.9, retreat toward a healthy ally 49.5, join mate's fight -2 (inside duos). Track 2 = a power-play
  variant with respawn+walk timing; expect level, test anyway (cheap).
- Visits/churn follow-up: farm_group changes 29 per champion in r<=600 (4.8/100 rounds), 74-77% without a share of
  the old target; A->B->A flicker 9-10% of changes. Abandoned legs (segment never worked before target changed)
  = 19-20% of ALL champion rounds (strict 17-18%); legs to "nothing" visits 11-12% (half are pass-throughs over
  respawning tiles). Real nothing-visits: 89% dealt damage, 60% woke the group, only 10% cleared it; ended by retreat
  29-33%, re-target to a group ~6 tiles away 20%. W and L equal on all of this: shared inefficiency, i.e. a pure
  farming-throughput lever (not what decides mirror games, but an absolute edge vs the ref).
- Switch causes (121,859 farm_group switches without own capture): ally claimed/stood at A 37% (20.5% of abandoned
  walking; median 2 tiles from A when it switched, B then 12 away!), valuation drift 22% (28% of walking, dA 15),
  enemy within 8 of A or self 20.5% (27% of walking), retreat interrupt 6.4% (11.5%), stale belief 6% (7%),
  A hit by other 4%. 22% of walking legs target a group truly unavailable at leg start, but mostly respawning a few
  rounds after arrival (median +3) - intended. Arrivals at respawning groups: 68% captured by a teammate (team knew,
  body didn't: one shared camp slot).
- 02:22 macro3-window ready (f = (theirs*our_team)/(their_team*ours) so full teams read exactly 1; theirs at g counts
  dead enemies whose max(respawn_earliest, now)+enemy_steps(g) <= arrival+fastest clear+capture; weight
  home^(m*f); preyable lifted when f<1 at target by kill turn). Started A/B macro3-window on set A (10,240 games).
- Launched Track 3 agent: macro3-commit = diagnose churn with debug traces, fix top mechanisms (ally-claim conflicts
  resolved when first visible, drift terms).

## Results
| candidate | games | suites | win% | 95% CI | notes |
|---|---|---|---|---|---|
| macro3-window | 10,240 | A (300001-020) | 50.7 | 49.7-51.7 | level, as the old power-play windows (50.7). ~6 min per 10k A/B. |
| macro3-collapse | 10,240 | A | 50.3 | 49.4-51.3 | level; deaths 4.15 vs 4.08, kills 4.08 vs 4.15 (2 suites): fights unchanged. OOF 932 vs 430. |
| p-stick (1.2->1.5) | 10,240 | A | 49.5 | 48.5-50.4 | probe |
| p-homepow0 | 10,240 | A | 48.1 | 47.1-49.1 | probe: own-ground bias matters |
| p-homepow2 | 10,240 | A | 48.6 | 47.6-49.5 | probe: tuned optimum |
| p-bank40 | 10,240 | A | 50.4 | 49.4-51.4 | probe |
| p-bank15 | 10,240 | A | 47.6 | 46.6-48.6 | probe |
| p-recall07 | 10,240 | A | 49.6 | 48.6-50.5 | probe |
| p-retreat15 (bolder) | 10,240 | A | 49.8 | 48.8-50.7 | probe |
| p-horizon2 | 10,240 | A | 49.4 | 48.4-50.4 | probe |
| macro3-linked | 10,240 | A | 50.0 | 49.0-50.9 | level: kill/protect life value x bodies removed (C&I = 2) |
| macro3-commit | 10,240 | A | 50.0 | 49.0-50.9 | level: claim_beaten (churn -8% in traces). OOF 457 vs 408 |
| macro3-window (set B) | 10,240 | B (300021-040) | 50.0 | 49.0-50.9 | window pooled A+B 50.35 of 20,480: noise |
| macro3-hold | 10,240 | A | 50.3 | 49.3-51.2 | level: stand_lost_at exit skipped at camp when even (Lanchester parity), can strike, not hurt; held 1.8% of at-camp stand-off turns |
| macro3-intent | 10,240 | A | 47.1 | 46.1-48.0 | LOST: enemy-intent contest discount on group values |
| macro3-pause (claim kept on stand retreats) | 10,240 | A | 49.2 | 48.3-50.2 | level/slightly negative; minimal job-ward retreat steps cost ~2% captures in paired batches |
| macro3-flow (unseen-claimer work estimate) | 10,240 | A | 49.7 | 48.7-50.7 | level; agent's 52.9% of 1000 was selection noise; no throughput change in any of its farm-targeting variants |
| macro3-deter (mutual deterrence belief) | 10,240 | A | 50.1 | 49.2-51.1 | level: first-strike-only lost stands are ~4% of lost verdicts; ref backs off 70% when we stay; staying is EV-neutral |
| macro3-hold (set B) | 10,240 | B | 49.9 | 48.9-50.9 | pooled A+B 50.1 of 20,480 |
| macro3-collapse (set B) | 10,240 | B | 50.9 | 49.9-51.9 | pooled A+B 50.6 of 20,480 (CI ~49.9-51.3); OOF 893 vs 437 at 2x fuel |
| macro3-deter (set B) | 10,240 | B | 49.8 | 48.8-50.7 | pooled 49.95 |
| macro3-deny (zero-sum denial term) | 10,240 | A | 50.4 | 49.4-51.3 | level; raises a group in 22% of farm decisions, picks a raised group 6%; vs intent's 47.1 the sign flip recovers but adds nothing |
| macro3-collapse (set C, fresh 300041-060) | 10,240 | C | 50.3 | 49.3-51.3 | pooled A+B+C 50.5 of 30,720 (CI ~49.9-51.1) |
| macro3-window (set C) | 10,240 | C | 50.4 | 49.4-51.4 | pooled A+B+C 50.4 of 30,720 (CI ~49.8-50.9) |
| macro3-stack (window + collapse) | 30,720 | A, B, C | 50.1 | ~49.5-50.7 | 50.5 / 50.5 / 49.3: no better than collapse alone |
| macro3-team (team-marginal join value) | 10,240 | A | 42.0 | 41.1-43.0 | LOST: fewer joins, -4-5% captures |
| macro3-join (share + team bonus: more joining) | 10,240 | A | 49.1 | 48.1-50.1 | level/slightly negative: +18% join decisions, captures -1-1.5%; join valuation at a local optimum |
| **macro3-eoq** (EOQ bank floor) | 30,720 | A, B, C | **52.6** | 52.1-53.2 | 52.5 / 52.9 / 52.5; OOF 493 vs 430 (set A). First significant gain |
| macro3-eoq-hi (floor max(25, Q*)) | 10,240 | A | 51.8 | 50.8-52.8 | raising the floor gives most of the gain |
| macro3-eoq-lo (floor min(25, Q*)) | 10,240 | A | 50.3 | 49.3-51.2 | lowering it near altars adds a little; full eoq 52.5 on A |
| macro3-eoq3 (chain limit = the same floor) | 10,240 | A | 52.4 | 51.4-53.4 | same as eoq (52.5 on A) |
| **macro3-eoq2** (online Gamma hazard, team carriers) | 30,720 | A, B, C | **53.1** | 52.5-53.7 | 53.4 / 53.1 / 52.8; OOF 504 vs 528 (set C). Best |
| macro3-eoq4 (per-champion shrunk hazard) | 10,240 | A | 52.5 | 51.6-53.5 | below eoq2 (53.4 on A) |
| macro3-eoqc (eoq2 + collapse) | 10,240 | A | 53.0 | 52.0-53.9 | no gain over eoq2 |
| macro3-eoq2 (varied stress maps, seeds 300061-070) | 5,120 | varied | 53.4 | 52.0-54.8 | robust on stress maps |
- Probes: every macro knob is at its optimum (level or -1..-2.4 both ways). Structure, not tuning.
- C&I drafted by 96.5% of teams in the mirror; C&I deaths = 35% of kill events (1.43/team-game, each 2 bodies + 2 bags).
  life_value is a flat constant per kill (fight.cc:809, abilities.h:21, turn_order). Launched macro3-linked: life value
  x bodies removed (2 for a linked body with partner alive).
- C&I anatomy: struck body Cassi 54%/Issac 46%; pair distance at fight start spread evenly (<=2 22%, >15 23%);
  pair hazard with an enemy within 8 does NOT depend on pair distance (6.4/8.5/7.7 per 1000 pair-rounds for
  <=3/4-8/>8) vs 3.15 per other body: the pick is simply two exposed bodies. Pair cohesion is not a lever.
  Killers of C&I: Prism 41%, Vesper 29%.

## 03:10 Stand-off study (contested camps, 28,087 episodes, r<=600; replay agent)
- Episode: our champ within 3 of group G, enemy within 8. 22% contested (both within 3). Our side leaves 26-32% of
  the time almost regardless of local HP share (own 30/25/32%, mid 30/23/26% for share <0.45/0.45-0.55/>0.55).
- Held vs left (other side left vs held): capture 68% vs 4%, deaths ~0.01 both, gem delta +14.9 vs -18.2 over 30r.
- Share>0.55: held capture 62% (deaths 0.015), left 13% (0.036, enemy then takes it 37%). Share<0.45: fighting is
  costly (x dies 12.9%); holding 36% capture, deaths 0.027. Leaving never had the fewest deaths in its band.
- Alone vs one enemy, staying: dies 4.7% vs 4.6% with company (baseline 3.7%).
- Caveat: observational ("held" selects calm). Fair basis held+fought+died vs left at share>0.55: capture 38% vs 13%.
- Lever: yield less. A camp we stand on at HP share >= ~0.5 should not be abandoned for enemy presence.
- 03:08 launched macro3-intent agent (enemy-whereabouts belief; discount groups by expected contest before walking).
- 03:15 macro3-commit report: switch reasons (20 debug games): ally 39.8% (36.5% of wasted leg rounds), captured 17.6%,
  enemy 11% (22%), drift 11% (18%), stale 10% (12%). Mechanisms: respawn wait crossing max_wait as we walk away
  (16.8%+18.1%), ally claim appearing (16.9%), crew share pruned (9.4%). Fix: claim_beaten (an ally claiming our group
  that starts work strictly sooner by the same work_arrival estimate takes it; we price crew share). Churn 29.2 -> 26.8
  per champ-game, wasted walking 26.6 -> 26.3%. Small. A/B started (set A).
- 03:16 launched macro3-hold agent: keep working a camp while locally at least even (Lanchester parity), from the
  stand-off study.

## 03:21 First deaths and fog (replay agent)
- First death round p25/50/75 94/197/369; 82% mid zone. Victims Cassi 21%, Issac 17%, Prism 13%, HoR 13%.
  Killers Prism 42%, Vesper 35%; 2.0 attackers per death. Victim activity: retreating 38-41%, at camp 33% (mid 80%),
  walking 18-20% (to mid 56%, enemy-side 35%), bag 7-8%.
- Fog is NOT the cause: a killer was seen the round before the first hit in 87-89% of deaths (median 4 tiles); no
  killer seen in -10..-1 only 5-7%. Unseen-enemy reach sets cover 81% of all rounds (useless). "Known danger" (visible
  within 8 or recently seen + in reach) is on in 25% of rounds and precedes 95% of deaths (median 8-9 rounds on).
- So deaths are decisions under visible danger, ~8 tiles away 10 rounds before. Fog symmetric for winners/losers.
- 03:52 macro3-hold report: of 1362 traced stand-offs, exits: want_home stand_lost_at 252, farm retarget 199 (NOT
  enemy-driven: same per-turn rate with no enemy near), chase 55, pack zone 42, low HP 34. Safety::stand_trade gives
  the enemy the first strike whenever one already reaches our tile, so 79% of at-camp stand-exits were even or better
  by Lanchester (343 of 596 C&I). Fix held only 1.8% of at-camp stand-off turns: level (50.3).
  Reading: the study's "leaving" is mostly farm retargeting (ally takes hold/crew), not fear.
- 03:55 launched ablation agent (one subsystem off per variant) + farm-throughput handicap probes (skip 5%/10% of farm
  turns) to measure where the leverage is.
- 04:03 macro3-intent ready: enemy whereabouts (visible/unseen pos+round/dead respawn) -> earliest arrival per group;
  intent by Luce choice over our own farm valuation from the enemy's position; renewal-reward discount factor on the
  rate (expected worth/rounds with arrivals; fight term with Lanchester odds and life value). Fires: pick changes in
  5.5% of farm decisions. Release smoke 21/64 (warning).
- 04:03 ablations built (13 one-subsystem-off + hc-farm5/10 throughput handicaps); queued sequentially on set A.

## 04:15 Leverage measurements (set A, 10,240 each)
- macro3-intent (enemy-intent contest discount): 47.1% (46.1-48.0): LOST. Avoiding contestable groups costs.
- hc-farm5 (skip 1/20 plain farm() turns): 42.7% (41.7-43.6); hc-farm10: 36.2% (35.3-37.2). ~1.4 points per 1% of
  farm turns, about linear. => throughput is the dominant lever: ~7% more farm efficiency ~ 60%. Wasted walking
  is ~20-25% of champion time in both bots.
- ab-standexit (want_home's stand_lost_at exit off): 37.2%: the fight-model retreat is worth ~13 points.
- 04:15 launched macro3-flow agent: farm throughput refactor (respawn pricing, claim conflicts, valuation
  stability, long-run rate), measured by paired capture throughput vs macro3-base on the same maps.
- Ablation map (one subsystem off, 10,240 each, set A; win% of the ablated bot):
  stand exit 37.2 | strike search when not holding 40.6 | chase 44.4 | recall-to-farm 46.2 | capture handoff 47.8 |
  contest_capture 48.9 | game-ender stop 49.1 | pack-zone exit 49.2 | siege/kite 49.4 | local support 49.6 |
  fixc commit 49.9 | altar guard 49.9 | wake ring 50.0.
  Reading: value sits in fight verdicts (stand exit, strikes, chase) and farm throughput (recall-to-farm, handoff).
  The pack-zone exit, support, siege, fixc, altar guard, wake ring are each worth ~0-1.
- 04:30 launched macro3-logi agent (logistics time: tribute/recall/shop/heal trips, walk-outs), and a retreat cost/precision study.

## 04:18 Retreat cost/precision (replay agent, 49,996 episodes, 98/game)
- Retreat itself median 2 turns, walks away 2 tiles; but back-to-work median 16 rounds (mean 22.5), new work tile
  5 tiles from the start. Retreat-start..back-to-work = 20% of alive rounds; matched non-retreats get back to work
  ~12 rounds sooner (rough extra cost ~6% of alive time). Retreats from a camp: 24.2 vs 3.7 rounds to resume.
- 63% of retreats are false alarms (no damage, no enemy within 3, no death). 43% start at local HP share > 0.55;
  of those only ~26% see danger. Matched "stayed": captures ~2x, deaths no higher (selection bias caveat).
- Lever: the cost of a retreat is the abandoned job (re-target after), not the retreat steps. Candidate idea:
  "retreat as a pause" (minimal retreat to the nearest tile where the stand is not lost, keep the job, resume).
- 05:03 macro3-logi report: no gain; variant left identical to base. Time budget (100 debug games): hit camps 17.2%,
  walk out from spawn 17.4% (57% after bank-bag recalls, ~20 tiles shortest, paths near-shortest), walk between
  camps 13.8% + 12.5% with bag, walk to altar 7.7%, retreat 5.9%, support 6.0%, hold 3.9%, idle in farm 4.2%,
  recall 4.4%, tribute 1.9%, dead 6.4% of all turns. Tried: emblem-stop worth (level), no capture recall under
  min_bank (level), round-trip-priced recalls (early gain, not replicated, more deaths). No capture recalls at all:
  tributed r600 -40 (riding home on a hold is valuable). Logistics are near optimum.
- 05:04 launched macro3-pause agent: stand-verdict retreats keep the claim, retreat minimally to the nearest tile
  where the stand is not lost, resume.
- 05:53 macro3-pause report: stand verdict starts 79% of retreats; 67% start while walking to a job, 12% while
  working; farm_group survives 82% (only the claim drops). 82% retreat again within 20 rounds (median gap 2):
  ping-pong at the edge of the lost-stand area. Job-ward minimal retreat and anti-ping-pong guard each cost ~2% of
  captures by r600 (paired, CI excludes 0); claim-only level. Reading: spawn-ward retreat + ping-pong is useful;
  the retreat cost is that the job lies behind a threat. Levers left: verdict precision, or re-choosing the job.
- 05:58 launched macro3-deter agent: mutual deterrence. A stand lost only by handing the enemy the first strike is, from the enemy's mirror view, lost for them; an online Beta belief of the opponent's back-off rate decides by expected value whether to keep working instead of retreating.
- 06:25 macro3-flow report: wasted walking 19.9% of alive rounds, 12.3% net of progress toward the next target. No
  farm-targeting change raised capture throughput (paired 200-1000 games each): plan-order insertion (keep A if
  rate(A then T) beats T) level; claim_beaten arrival-order ceding -1.7% captures; joining off -2.4% captures (joins
  valuable); unseen-claimer work estimate level (49.7 at 10k). Farming is at a local optimum under its structure.

## 06:35 Bag deaths and gem swings (replay agent)
- 11.1 deaths/game; 16% carry >= 25 gems but hold 84% of gems lost. Per team-game: winners lose 49 gems at death and
  gain 162 from kills; losers lose 166, gain 45. Swing counted to r300/r500: AUC 0.66/0.72; 50+ ahead ~77% wins.
- Big bags (>= 50, 0.76/game, mean 190): Prism 274 of 389 (it retains the bag for Focus), carried a median 175
  rounds, 3 captures chained. Per carrying round Prism is not riskier than average (0.79 vs 0.86 per 1000).
- Bag >= 25 deaths: retreating 72% (after the first hit), walking to an altar 16%, tribute channel 5% (mean bag 272).
  Killers visible >= 5 rounds before in 69%.
- Prior (EXPERIMENTS 610, 4748, 8055, 13259): Prism retain cap 150 46.7%, banking under threat 42.8-49.5: the hoard
  is Prism's damage. Not re-tried.
- 06:40 launched macro3-deny agent: zero-sum valuation (remove intent's contest discount; add denial term = P(enemy takes g) x enemy's loss vs its next-best), built on macro3-intent's model.
- 07:00 macro3-deter report: stand-lost verdicts 184 turns/game; "lost only to the enemy's first strike" 11.7/game,
  strict mirror 7.5/game (~4%); retreat starts in deterrence situations 5.3/game. Ref backs off 81% when we retreat,
  70% when we stay (it strikes 26%). Staying saves ~3 rounds/episode at +4 points of death risk: break-even.
  Most ping-pong stands are lost even with us striking first. Premise true but tiny.
- 07:05 launched macro3-team agent: team-marginal join valuation (a join's team gain is the claimer's time saved x its rate; our share is a transfer), ops/crew-required groups unchanged.
- 07:25 generated set C (ladder-v2 seeds 300041-300060). Launched merge agent: macro3-stack = window + collapse.
- 07:45 launched macro3-eoq agent: map-adaptive bank floor Q* = sqrt(2KD/h) (trip cost, income rate, bag hazard x2 swing) in place of min_bank 25.
- 07:50 macro3-team report: CLEAR NEGATIVE. Joins 78/game (84% on fighting groups); joiner lands hits 56-67%;
  team-marginal pricing (claimer time saved x our rate, share treated as transfer) cut joins to ~50/game, captures
  -3.7% r300 / -5.1% r600 (held out, CI excludes 0), win 42.5% of 200. Joint clears concentrate the team on big
  groups; spreading out moves us to smaller groups and more walking. Joins add more than the time model credits.
  Follow-up asked: macro3-join (share + team bonus, i.e. MORE joining).
- 08:02 macro3-eoq (bank floor Q* = D*sqrt(2T/h): T = marginal trip rounds from here (to altar or recall+altar,
  one tribute turn, back), D = own gem income per turn alive (income_rates prior), h = 0.86e-3 bag hazard x 2 swing;
  clamp 10..min(gems_short, 10*bag_rounds_left)). Floors 10-72 by champion income and trip.
  Set A: 52.5% (51.5-53.4) of 10,240. First significant positive. Confirming on B and C.
- 08:28 FINAL: bots/ocean = macro3-eoq2 (committed). 53.1% of 30,720 (A/B/C), 53.4% of 5,120 varied maps.
  Write-up: research/macro-2026-11-11/macro3.md; EXPERIMENTS.md entry added.
- 08:25 launched impl agent: macro3-eoq5 = eoq2 with chain_bag_limit (26) replaced by an EOQ-consistent rule.
- 08:37 eoq5 built (chain_bag_limit replaced by a holding cost h*swing*bag in farm's banking chain test; uncommitted variant). Set-A A/B started in tmux m3eoq5; result not in at hand-back.
