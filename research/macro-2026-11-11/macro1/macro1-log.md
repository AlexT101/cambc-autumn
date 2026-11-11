# macro1 log (lead's running notes)

Brief: research/macro-2026-11-11/macro1-brief.md. Worktree /home/ubuntu/wt/macro1, branch macro1-20261111.
Env: `source research/macro-2026-11-11/env.sh` (venv, fastrunner native, CAMBC_SLOTS=86, cd worktree).
A/B: `py tools/ab.py variants/macro1-X variants/ocean-ref-b7c87cf --no-test-draft --fuel 200000 --suites ... --name macro1-X`
Maps: /home/ubuntu/wt/macro1-maps/s-100001 .. s-100040 (ladder-v2, 256 maps each, 512 games/suite).

## Timeline
- 01:40 start. Read brief, AGENTS.md, rules. Generated 40 suites (seeds 100001-100040).
- 01:45 macro1-base = copy of ref. Evidence run `macro1-evid`: base vs ref, --debug, keep all replays, suites s-100001..4 (2048 games). Purpose: self-play loser analysis.
- Spawned 2 read-only surveys: research history (macro ideas tried) and ocean architecture map.

## Evidence 1: mirror (macro1-evid, 1023 distinct games, debug builds, --fuel 200000). 2048 games in 2m12s (box is fast).
Extract: /home/ubuntu/wt/macro1-maps/ana/evid (replays/.analysis symlinks there). turn_budget.py fixed to import from worktree.
- Turn budget W/L: dead 4.7/10.5, camp 18.1/16.6, hold 4.7/4.1, bag->altar 16.7/15.5, empty->camp 17.9/17.2, bag->camp 6.3/6.0,
  idle-off 5.4/4.0 (r801+ 10.1/6.2), recall 4.3/3.8, tribute 3.4/1.7, fight 3.8/3.7.
- Earnings W/L: captured 1006/792, tributed 1066/521, taken by kills 191/57, lost at death to champs 57/185, gold 5892/4463.
- Deaths W/L 2.6/6.4; branch R (retreat) in last 4 rounds 85/80%; 75-80% with 2+ enemies within 8; biggest cell 3+ allies & 3+ enemies (L 16 per 10 games).
- Prism = 67% of loser's gems lost at death (retaining for Focus); deaths with 100+ gems: L 0.40/game = 66% of gems lost.
- Predictors: more kills wins 88.7%, fewer gems lost 88.7%, more captured 80.8%, more mid captures 77%, not dying first 62%.
- Supply: ~58% of own-side gem-weighted group-rounds asleep (available, unworked); mid 70% asleep.
- Clears by side W: own Wolf 18.3 Elk 8.7, mid ~5.5 total, enemy ~7; L fewer mid/enemy.
Priors (survey): every pack/summon/hunt/escort/cohesion lean lost (walking cost > fight gains); crew economics +11 (61% vs old), value holders +2.3,
  min_bank 25 +3.7, giving way less +2, threat-aware recall line +3, Fish turn order +2.9, escape planner +1.7. Comms: -6 without; enemy sightings in comms -2 (x3).
Architecture (survey): per-champion greedy rate score (farm.cc farm_turn ~1850 lines), claims not reservations, crews for strong groups,
  danger barely in farm value (reactive want_home/pack-zone), enemy memory 3 rounds, fights local (allies within 4/7).
- Solo vs idle (s-100005 one side): ocean reaches 1000 at r651 mean (mirror winner median ~770).
- Gold is spent promptly (held 17-80 mean); str grows 47->63 by r300, 103 by r700 (W).
- Hazard (died within 10 rounds per 1000 champion-rounds, mirror pooled): e0 3.7, e1 22, e2+ 50; e2+ & ally<=4 44 vs ally>12 90;
  ally<=4 is already 62% of champion-rounds (team is cohesive already); own zone 10, mid 23, enemy 32; low hp & e2+ 165.
  => deaths are mostly in multi-enemy brawls where allies ARE near; lone-farmer ganks are a minority in the mirror.

## Evidence 2: replay study taxonomy (scripts /home/ubuntu/wt/macro1-maps/study/)
- THE BANK: Prism holds 71-81% of carried gem-rounds; loser 150+ bags carried median 447 rounds, die median 3 steps from an altar.
  Loser Prism 200+ bag episodes: 42% death, 43% never banked, 16% banked (winner 90% banked). 200+ tributes: 4.3/game, 23% complete;
  ~35k channel turns on cancelled tributes. 37% of games end on one winning 200+ tribute. 100+ bag deaths = 6% of deaths, 62% of gems lost (435/518 Prism).
  bankable rule: bank.cc retaining_gems(): Prism keeps ALL gems unless winning_bag or closing.
- Death taxonomy (loser): team fight at even+ numbers 36%, desperation at game-ending enemy bag (E) 16%, outnumbered 2+ 16%, lone not farming 10%,
  chase overextension 7%, lone farmer 6%, carrier at altar 5% (22.5% of gems), camp 4%.
- Coordination: at fight start ~1.7/2.8/3.4 per side within 4/8/12 of 4.9 alive; only 0.3 arrive in next 5 rounds. More bodies wins 64%, initiator 68%.
  Allies 5-8 tiles from a dying teammate: 13% fought, 47% farming. Down bodies -> hazard 2.5-3x (no posture change).
- Waste: farm target changes 5.5/100 turns, ~30 A-B-A flips/game; abandoned approaches ~16-18% of alive turns (upper bound): retarget 6%, enemy took it 4-5%, enemy seen/retreat 5%.

## Plan v1 (02:10)
1. macro1-bank: Prism banks in completable pieces (cap retention at the tribute window) [+ probe: no retention at all]. Defense of our bank.
2. Next: enemy-bank denial (their mega-bag is the prize) and fight arrival/commitment.

## Result 1 (02:21): Prism bank discipline LOSES big
- macro1-bank (Prism retains only while tribute fits 11-turn window, i.e. <=110 gems): 36.9% of 10240 [35.9-37.8] (s-100001..20)
- macro1-bank0 (Prism never retains): 32.7% of 10240 [31.8-33.6]
- Lesson: Prism's carried-gem Focus (+1.5/gem, spells scale with Focus) is the dominant force. The hoard is the team's weapon.
- Prism in both drafts in 816/1023 mirror games (80%). Bigger Prism bag by 50+ at r200 -> 75% win (r300+ 78%).
- Prism gets only 35% of its team's captured gems (33% as sole holder); Prism lands 57% (W) of kill-gem transfers.
=> New direction: PRISM CARRY. Grow our Prism's bag faster (funnel gems), protect it, kill theirs.
- bank0 mechanism (1024 games extracted, fight_metrics): kill share at equal numbers 0.42 vs ref 0.58; deaths 5.0 vs 3.6; kills 3.3 vs 4.8;
  capture gems 809 vs 947. Prism's Focus decides fights AND speeds clears.
- 02:33 spawned macro1-carry (Prism takes over allies' gem holds it can reach before payout; allies hold for a claiming Prism; Prism per_gold/2).

## Result 2 (02:40): macro1-safe level
- macro1-safe (farm destination refused if arrival would be in pack zone/under recall line; race lost to nearer outnumbering enemies): 49.6% of 10240 [48.6-50.5]; OOF 543 vs 489.
- Prism deaths (mirror, Prism-both games): loser Prism dies 1.30/game (148 gems lost/game), winner's 0.26. 57% of loser-Prism deaths are KILLED BY THE ENEMY PRISM;
  66% with 3+ enemies within 8. => Prism-vs-Prism duel is the core dynamic: bigger Prism kills smaller, takes its bag, snowballs.
- Prism-kills-Prism (682 events): killer bag bigger 82% (by 50+ 70%); killer Focus 1067 vs victim 391. Snowball.
- 02:46 spawned macro1-duel (memory of enemy Prism power/whereabouts 12 rounds; avoid a dominant enemy Prism (stun >= half our hp);
  our dominant Prism hunts a dominated one).

## Result 3 (02:55): macro1-carry WINS
- macro1-carry: 54.3% of 10240 [53.3-55.3] (s-100001..20); OOF 491 vs 500. (Prism 'G' takeover of ally-held gem captures it reaches before payout;
  allies cancel capture recalls to yield to a claiming Prism; retaining Prism per_gold x0.5.)
- carry games (1024 extracted): Prism cap share 36.2% vs ref 29.0%; bag200 105 vs 71; bag400 239 vs 158; Prism-games win 55.8%;
  Prism kill-gem share 59% vs 42%; Prism deaths/pgame 0.66 vs 0.91.
- 03:00 spawned macro1-carry2 (= carry + kill routing to Prism: turn-order kill bid counts bag twice for retaining Prism; non-Prism zeroes bag value of a kill Prism surely takes later this round).
- 03:01 confirm carry on s-100021..40 (macro1-carry-c).
- macro1-carry confirm (s-100021..40): 55.7% of 10240 [54.7-56.6]. Combined 55.0% of 20480.

## Result 4 (03:13): macro1-duel LOSES
- macro1-duel: 45.3% of 10240 [44.3-46.2]. Avoid rule (stun >= half our hp -> farm bars within 6+age, flee within 6) fires on squishies vs any mid Prism
  (hundreds of bars/flees per game) => cedes map. Consistent with prior "giving way loses". Hunt half untested alone.
- carry games: first Prism death decides: ours first (218/830) win 15%; theirs first (281) 86%; none (331) 57%.
  Bag lead at r150: ahead 429 (67% win), behind 132 (28%). Our first-dying Prism had the bigger bag 50% of the time (theirs 16%);
  enemy Prism within 6 at 72-82% of first Prism deaths; killer: Prism 47-67%, Vesper 12-19%.
- 03:15 spawned macro1-carry3 (Prism claims ally-held gem captures beyond payout window, walk <= 2*capture_time; ally leaves them for the carry).

## Result 5 (03:27): macro1-carry2 level vs carry
- macro1-carry2 (kill routing): 54.4% of 10240 (carry 54.3% same suites). Rule 1 fires ~1 per 2 games, rule 2 never. Dropped.
- 03:28 spawned read-only study of our Prism's first deaths (study2/).
- macro1-hunt (carry + duel's hunt only): 54.4% of 10240 = level vs carry. Duel's loss was all avoidance. Dropped.
- carry endgame (Prism-both games): wins: our Prism peak>=300 in 87%, tribute starts 4.7/game, completes 1.1, cancels 3.5.
  losses (367/830): peak>=300 in 54%, peak>=500 23% (big Prism still lost: died or never banked).

## Evidence 3 (03:42): how our Prism dies first (study2/, 218 games)
- duel initiative lost 24%, duel out-raced 18%, stunned by other champion then focused 26%, camp 11%, channelling 8% (median bag 492), Vesper 9%.
- Both Prisms end 22% of free turns inside the ready enemy Prism's reach, NOT scaled by bag (21.7% bigger vs 23.0%).
  Measured P(enemy Prism spell hits ours before our next turn | d at end of our turn): 1 enemy-Prism turn first: d<=4 35%, d5 21%, d6 0;
  2 turns first (double turn): 58/37/7%. Spells not ready: 0.
- 30% of decisive hits from unseen attackers (19% bushes).
- Our Prism tributes of 300+: 2364 starts, median channel 49, 17% complete (theirs 25%).
- Prism maxHP/gold/focus at r300: ours 1174/586/425 vs ref 1029/448/328 (carry did not starve Prism of gold).
- 03:45 spawned macro1-guard (carry + our Prism end-tile exposure priced by measured P(hit|d,k) x (life+bag); step guard; big-tribute start/cancel discipline vs enemy Prism).

## Result 6 (04:05): carry3 small gain, guard level
- macro1-carry3 (Prism claims ally-held/left gem groups up to 2*capture_time walk; allies leave them; stale claims dropped):
  55.1% of 10240 [54.2-56.1] (s-100001..20; carry 54.3), 56.2% of 10240 [55.2-57.1] (s-100021..40; carry 55.7). Pooled 55.65% of 20480. New base.
- macro1-guard (carry + end-tile exposure vs enemy Prism, step guard, long-tribute start/cancel vs enemy Prism): 54.2% of 10240 [53.2-55.1]
  = level with carry; OOF 1100 vs 542. End-tile rule almost never fires (exception: enemy spell < half our hp+shield). Dropped.

## Evidence 4 (04:10): the endgame (ana/carry, 830 Prism-both games)
- Games end at 1000 tributed in 97%. Wins: our Prism tributes 496 of the score. Losses: our Prism tributes 54, ends holding 183
  (34% hold 200+), lost 154 at deaths; those big-bag losses are simply behind (score+bag would win only 11%).
- Big (200+) tributes by cause: ours (2938) done 18%, manual cancel 35%, stun 30%, lock 17%; theirs done 25%.
  Enemy within 8 at start: 0 -> 55% done, 1 -> 14%, 2+ -> 4-5%. 75% of our big starts have an enemy within 8.
  Home altar (much nearer own spawn) 51-61% done; mid altars 13-20%; most maps have no home altar.
- Their completed 200+ tributes (509; 426 in games they won): no ally of ours within 5 of the altar during the whole channel
  in 68% (none within 10 in 32%); mean channel 29 rounds. Locks: ~4 placed per side per game, ~1.1 held (own-side altar).
- Failed big tributes are cheap: our Prism dies within 15 rounds of a cancelled 200+ tribute only 2-3% of the time; games with
  cancels still won 72-91%. Tribute start discipline is not a lever (consistent with guard level). Dropped.
- Win rate by map family (carry3 s-1..20): uniform 50-61%; no class to target.
- First Prism death by phase (carry): ours <150 (bag 29) -> 27% win; theirs <150 -> 75%. Killers of our Prism: Prism 103/218.
- Life value (mirror, 1023 games): first death, bag<50, r<300: victim team wins 27.9% if Prism, 41.1% other; all low-bag deaths
  27.3/38.1% (r<300), 13.9/31.3% (r300+). Prism life (sans bag) ~2x another champion's; ocean prices all lives at life_value 276.6.
- 04:15 spawned macro1-deny (sentinel with lock at the threat's altar while enemy score + remembered enemy bag >= 1000),
  macro1-plife (Prism life value x2 everywhere a life is priced), and a read-only farm-churn study (study3/).

## Evidence 5 (04:25): farm target churn (study3/, 500 debug mirror games, 4.26M alive turns)
- Open switches (A not resolved) waste 4.96% of alive turns (8.2% counting non-farm-branch moves): ally newly claims A 1.27
  (ally nearer 63%, ~3-round lag), leave solo A to join ally's B 1.17, drift 0.75, co-claim 0.65, enemy in sight 0.48, symmetric swap 0.45.
  Walked to A then ally resolved it 0.76; then enemy engaged/took it 2.46.
- Causes: flat stickiness 1.2 (farm.cc) with no commitment; claims first-come with no distance tie-break; attack_in_range /
  prefer_partial overwrite memory.claim with a passing hit (posted claim stops naming the target); join-vs-solo re-weighed each turn.
- Joint re-assignment (Hungarian) of the same targets: upper bound 1.2% of turns. Truly idle negligible (0.2-0.3%).
- Proposed: durable claims settled by team walk distance (1.5-2.5%), trip-aware hysteresis/commitment (0.7-1.2%), join decided at pick (0.7-1.0%).

## Result 7 (04:30): plife level
- macro1-plife (carry3 + Prism life priced 2x at every life-pricing site, both sides): 55.6% of 10240 [54.6-56.5] (s1-20; carry3 55.1),
  56.1% [55.1-57.0] (s21-40; carry3 56.2). Pooled 55.85 vs 55.65: level. Dropped (combat pricing of Prism life is not the lever).
- 04:33 spawned macro1-claims (posted claim = real target, distance tie-break on conflicts, trip-aware hysteresis/commitment, join decided at pick).
- Fresh suites s-100041..60 generated for confirmations.

## Evidence 6 (04:40): Prism duels are decided by Focus, not initiative (ana/carry3, 1024 games of carry3 vs ref)
- carry3 Prism-both games 830, win 55.9%. Capture gems: our Prism 448 (ref Prism 319), our others 502 (ref 594). Tributed: our Prism 335.
- Engagements (first Prism spell on the other Prism after 20 quiet rounds; who dies within 15 rounds), by hitter/target Focus ratio:
  <0.5: hitter dies 52%, wins 4% (647); 0.5-0.8: 19/14 (442); 0.8-1.25: 9/20 (543); 1.25-2: 6/30 (308); >2: 4/53 (273).
  Ours initiated at <0.5 221 times (0.27/game): died 48%. Theirs 426 times: died 54%.
- Our Prism's first deaths (204): bag bigger than the enemy Prism's in 58%, killer Prism 55%.
=> design macro1-yield: our Prism dominated 2x in Focus by a seen enemy Prism never initiates and never ends a turn in its reach.

## Result 8 (04:55): deny level
- macro1-deny (sentinel holding a lock at the remembered winning carrier's nearest altar; comms spare claim code): 55.2% of 10240 [54.2-56.1]
  (s1-20; carry3 55.1). Threat turns on late (enemy score 930-998), sentinels mostly die at crowded altars or arrive late. Dropped.
- 04:52 spawned macro1-yield (our Prism only: vs a seen enemy Prism with >= 2x its Focus, no initiation, never end a turn in its reach (5,+1 on double turn), flee out of it).

## Evidence 7 (05:05): carry3 vs ref, fight metrics and turn budget (1024 games; debug A/B s-100003/4 55.1%)
- fight_metrics (ana/carry3): captures 54.3 vs 54.0 a game, capture gems 924 vs 894, deaths 4.24 vs 4.82, kills 4.59 vs 4.00,
  kill share at equal numbers 0.524. The edge is fights (bigger Prism), not farm volume.
- turn_budget --by-bot: walking ~50% of every champion's rounds (bag->altar 16%, empty->camp 18%), camp 17%, dead 7.2 vs 8.2.
  Prism: dead 5.1 vs 7.3, tribute channel 6.7 vs 4.2, hold 8.7 vs 7.7. Late (r801+) idle-off 9.4 vs 7.7.

## Result 9 (05:35): claims loses, yield level
- macro1-claims (posted claim = real target; distance tie-break; commitment replacing flat stickiness 1.2; joins decided at pick):
  52.3% of 10240 [51.3-53.3] (s1-20; carry3 55.1) = -2.8. Churn fell 16-29% in 48-game traces. Loses: see diagnosis below.
- macro1-yield (our Prism vs >=2x-Focus seen enemy Prism: no initiation, end tiles out of reach, flee): 55.0% of 10240 [54.1-56.0] = level.
  Fired in 8 of 60 traced games (255 dominated turns). Dropped.
- claims per-suite: lower than carry3 on 16 of 20 suites. Captures 54.1 vs ref 53.7 (s1-2), capture gems 909 (carry3 924).
  Hypothesis: commitment/join bar remove adaptive switching; claim-info fixes (1,2) are not the problem.
- 05:40 spawned macro1-claimslite (claims parts 1+2 only: posted claim = target, distance tie-break; flat stickiness kept)
  and macro1-funnel (allies leave cleared gem groups for a nearby non-dominant Prism without its claim, lapse after capture_time; no co-hold dilution).
- carry3 fresh confirm s-100041..60: 55.9% of 10240 [54.9-56.8]. carry3 pooled 55.73% of 30720 (s1-60).
- macro1-claimslite (claims parts 1+2 only; fired ~3-4x a game each, churn unchanged): 54.2% of 10240 [53.2-55.1] (carry3 55.1) = -0.9. Dropped: churn is mostly adaptive; claims following passing hits help.

## Evidence 8 (05:55): dominance and the race (ana/carry3, Prism-both games)
- Win by our/their Prism Focus ratio: r100 <0.8 31%, 0.8-1.25 51%, >1.25 66% (403 games); r300 17/47/70%.
- Dominant at r300 but lost (149 of 489): our deaths 6.56 vs 4.07, their allies tributed 759 vs ours 397, our Prism only 90.
- Losses are economic deficits: when the enemy reaches 600, our score 355 + Prism bag 221 (wins: 575 + 347); banking earlier would not win them.
- 05:58 spawned macro1-reaper (our Prism: any enemy its ready burst kills is preyable anywhere off spawn; fight sim/escape gates unchanged).
- macro1-plife fresh s-41..60: 55.9% of 10240 [54.9-56.8] (carry3 55.9). plife pooled 55.87% of 30720 vs carry3 55.73%: level, not adopted.

## Result 10 (06:40): funnel wins, reaper level
- macro1-funnel (carry3 + allies leave fresh cleared gem groups for a nearby non-dominant Prism without its claim, lapse after
  capture_time; sole Prism holder: allies' steps kept off its tiles, yield steps relaxed): 56.8% of 10240 [55.8-57.8] (s1-20; carry3 55.1) = +1.7.
  OOF 615 vs 475 (fields per left group). Traces: Prism capture gems 456 -> 489 a game, shared payouts 1.20 -> 0.57.
- macro1-reaper (our Prism: an enemy its ready burst kills is preyable on its own ground): 55.3% [54.4-56.3] = level. Dropped.
- macro1-funnel confirm: s21-40 55.5% [54.6-56.5] (carry3 56.2), s41-60 57.0% [56.0-57.9] (carry3 55.9).
  funnel pooled 56.43% of 30720 vs carry3 55.73% (same maps): +0.7. New best.
- 06:35 spawned macro1-funnel2 (leave only when our Prism's ETA, incl. its current task, is within capture_time; fuel-bounded fields).
- macro1-funnel2 (funnel + leave only when our Prism's ETA incl. its current task is within capture_time; leaves 4.3 -> 0.32 a game):
  56.4% [55.4-57.4] (s1-20), 57.0% [56.1-58.0] (s21-40), 57.0% [56.0-57.9] (s41-60). Pooled 56.80% of 30720 vs funnel 56.43, carry3 55.73.
  New best (more consistent across suites; OOF back to ref level). Implementer's read: much of funnel's value is change 2 (no dilution)
  and allies leaving the area, not timed handoffs.
- funnel2 held-out s-100061..80 (fresh): 57.2% of 10240 [56.2-58.1]; varied mix s-100081..85: 55.6% of 2560 [53.7-57.5].
  funnel2 ladder-v2 pooled: 56.9% of 40960 (s1-80).
- Enemy Prism captures 348 gems a game, 280 of them with none of ours within 8: contesting them is not feasible.

## Result 11 (07:40): the funnel gain is the no-dilution hold
- macro1-hold (carry3 + funnel's change 2 only: sole Prism holder not shared, holds unless an enemy is in sight): 56.2% [55.2-57.1] (s1-20),
  56.8% [55.9-57.8] (s21-40); carry3 55.1/56.2, funnel2 56.4/57.0. Change 2 is most of the gain; change 1 (leaving groups) ~+0.2.
- Ally deaths with our Prism dead: 22% of ally deaths in losses vs 4% in wins; distance to our Prism otherwise similar W/L.
- funnel2 on the 128 ladder maps (both sides): 55.9% of 256 [49.7-61.8] (gen suite missing in worktree).

## Result 12 (08:10): hold2 wins on every suite set; bots/ocean = hold2
- macro1-hold2 (funnel2; the sole Prism holder keeps its hold with an enemy in sight unless a seen enemy contests the tiles
  or could take it below hurt_health_fraction within the remaining hold rounds + 1, via Safety::turns_to_harm_idle; allies'
  fight steps and in-sight step-offs keep off its tiles). Traces (48 debug games): Prism-ally shared payouts 21 -> 14, 0 Prism
  deaths within 10 rounds of 238 kept holds.
- 57.8% [56.9-58.8] (s1-20), 57.4% [56.5-58.4] (s21-40), 58.2% [57.2-59.1] (s41-60), 57.6% [56.6-58.5] (s61-80);
  funnel2 56.4 / 57.0 / 57.0 / 57.2. Pooled 57.76% of 40960 [57.3-58.2] vs funnel2 56.9. Varied s-81..85: 56.2% of 2560
  [54.3-58.1] (funnel2 55.6). OOF at ref level (487-620 vs 461-603). Adopted: bots/ocean = macro1-hold2.
- 08:06 spawned macro1-hold3 (hold2 with a kill-only threat test); 08:08 generated fresh held-out suites s-100086..105.
- Fresh held-out s-100086..105 (ladder-v2, generated after hold2 was adopted): hold2 57.0% of 10240 [56.1-58.0], funnel2 56.2%
  [55.3-57.2] on the same maps: +0.8, as on s1-80. hold2 over all 100 suites: 57.6% of 51,200.
- 08:09 spawned macro1-hold4 (hold2's threat test for every sole holder, not just the Prism).
- macro1-hold3 (hold2 with a kill-only threat test, as hold_outlasts): 57.9% [56.9-58.8] (s1-20), 57.7% [56.7-58.6] (s21-40),
  58.0% [57.0-58.9] (s41-60), 57.3% [56.3-58.2] (fresh s86-105); hold2 57.8 / 57.4 / 58.2 / 57.0. Pooled 57.69% vs 57.62% of
  40960 on the same maps: level. Kept hold2 (the kill-only test also lets fit_on revoke a hurt Prism's verdict mid-hold).
- macro1-hold4 (hold2's threat test for Tavi and Marcella sole holds too): 57.8% [56.9-58.8] (s1-20; hold2 5921 wins, hold4
  5920). Fires in ~1% of games under our draft (no 3-pick Marcella+Stellar; Tavi rarely a sole gem holder in sight): no-op.
- 08:21 spawned macro1-hold5 (the threat test for our Prism's other capture decisions: claims, carry picks, capture recall).
- macro1-hold5 (hold2's threat test also for our Prism's 'G' takeover and 'L' carry picks, which bailed on any enemy in sight):
  57.8% (s1-20), 57.8% (s21-40), 58.2% [57.3-59.2] (s41-60), 57.4% [56.4-58.3] (fresh s86-105). Pooled 57.81% vs hold2 57.62%
  of 40960 on the same maps (+0.19): level. Kept hold2.
- 08:40 spawned macro1-hold6 (close hold2's remaining dilution leaks: out-of-sight leak, retreat steps onto the Prism's tiles).

## Result 13 (09:04): hold6 wins on every suite set; bots/ocean = hold6
- macro1-hold6 (hold2 + its remaining dilution leaks closed: Willow had no work guard so her farm/follow steps ignored the
  Prism's held tiles; Willow's support formation kept her standing on the hold; a damaged ally out of sight never stepped
  off; retreat prefers a step off the hold as a tie-break after its safety keys). Traces (48 games): Prism-ally shared
  payouts 23 -> 13, gems to allies 341 -> 230.
- 57.9% [57.0-58.9] (s1-20), 58.2% [57.2-59.1] (s21-40), 58.9% [58.0-59.9] (s41-60), 58.1% [57.2-59.1] (s61-80),
  57.5% [56.6-58.5] (fresh s86-105); hold2 57.8 / 57.4 / 58.2 / 57.6 / 57.0. Pooled s1-80 58.29% of 40960 [57.8-58.8]
  (hold2 57.76); all 100 suites 58.14% of 51200 [57.7-58.6]. Varied s81-85: 56.2% of 2560 [54.2-58.1] (hold2 56.2).
  OOF at ref level (479-661 vs 451-604). Adopted: bots/ocean = macro1-hold6.
- macro1-hold7 (hold6 + an ally doesn't start a recall on a sole Prism hold's tiles): 57.9% (s1-20), 58.1% (s21-40);
  hold6 5934 / 5956 wins, hold7 5931 / 5952: level (the recall leak is a few gems a game). Kept hold6.
- Final: bots/ocean = macro1-hold6, 58.3% of 40,960 (s1-80) [57.8-58.8], 58.1% of 51,200 over all 100 suites.
