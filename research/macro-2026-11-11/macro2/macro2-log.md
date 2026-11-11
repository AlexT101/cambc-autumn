# macro2 log (lead's running notes)

Brief: `macro2-brief.md`. Worktree `/home/ubuntu/wt/macro2`, branch `macro2-20261111`.
Ref: `bots/variants/ocean-ref-b7c87cf` (== bots/ocean at start). Target 60%+ over 10k+ games at --fuel 200000.
Runner script: `/home/ubuntu/wt/macro2-logs/abrun.sh NAME CAND SUITES [ab.py args]` (logs in `/home/ubuntu/wt/macro2-logs/`).
Suites: `/home/ubuntu/wt/macro2-maps/s-200001..s-200030` (ladder-v2, 256 maps each). Reserve 200031+ for confirmation.

## 0. Theory model (from rules only, written before reading macro code)

Score = tributed gems. 1000 wins outright; else most tributed at r2000.
Gem sources: capture shares (camps) and kills (all victim's carried gems). Gems only count when tributed.

Camp value per hp (gems/hp): wolf .003, elk .006, golem .007, monolith .010, **gem cluster .058**.
Gold per hp: gold cluster .167, wolf .030, elk .038, golem .032, monolith .015.
A group pays the sum of members; respawn timer = longest member respawn, starting at payout.
Capture hold 6 rounds (4 with Capture emblem); one champion suffices; extra allies only split the share.

1. **Throughput ceiling.** Per group, max rate = R / (respawn + kill + hold + travel/dead time).
   The map's supply rate is fixed. Once team capacity exceeds the supply it can reach safely,
   extra champion-turns earn ~nothing by farming: their value moves to *contesting* (taking
   enemy-side/central camps, denying captures with a body, killing).
   In a symmetric game a camp taken from the enemy's supply counts double in the difference.
2. **Phases.** Early: stats low, gold compounds (shards = 30g -> +growth). Clusters and wolves
   are the efficient early targets; gold early is worth more than gold late (compounding,
   fewer rounds left to use it). Mid: elk/golem/monolith become efficient with stats and
   multiple champions (kill time ~ hp / sum of dps; a camp hits only the nearest champion, so
   n champions on a big camp cut kill time by n while one tanks). Late: only gems tributed by
   r2000 matter; carried gems are a liability; lead -> deny/defend, behind -> must contest.
3. **Kills.** A kill = victim's carried gems + 100 gold + ~60 rounds of the victim's turns
   (and its camps uncontested). Deaths cost the same. Lanchester: local numbers decide
   fights (strength ~ n^2), so being *able to converge* when enemies are near is worth a lot,
   while being spread when no enemy is near maximises farming.
4. **Coordination principle.** Not packs or summons (both failed: walking waste, busy allies).
   Instead: allies should choose farm targets so that the team's farming *area* is compact
   relative to the enemy (mutual support within a few turns), and the team's territory is
   pushed forward (enemy-side camps taken when enemies are elsewhere/dead). Every target's
   value should include risk = P(enemy contest/kill) which depends on enemy reach vs ally reach.
5. **Windows.** Enemy deaths open 60-round windows: the whole team should exploit them
   (steal enemy-side camps, monolith, siege). Our deaths close windows: retreat/defend.
6. **Carried gems are bounty.** Tribute cadence trades travel turns against risk; in contested
   zones tribute sooner. Tribute channel ceil(g/10) turns; altar locks deny.

Questions to answer with data: game length distribution; share of champion-turns walking /
farming / holding / fighting / dead / idle; how much camp supply goes uncaptured; which camps
(own/central/enemy side) are taken; what loses mirror games (deaths? supply? steals?).

## Log
- 01:41 started `macro2-base` (copy of ref vs ref, s-200001,2, --keep-replays 0) for pipeline sanity + replays.

## 1. Baseline facts (mirror, 1024 games s-200001/2, 512 analysed)
- macro2-base (copy of ref) vs ref: exactly 512/1024 (deterministic mirror). ~10 min per 1024 games on the shared box.
- Mean 865 rounds, 9/512 reach r2000 -> it is a race to 1000 gems. Rounds quantiles 10/25/50/75/90%: 500/591/776/1045/1398.
- Loser/winner final gems median 0.48 (only 10% within 7%): games are snowballs.
- Winner k5.7/d2.5, loser k2.3/d5.8; loser dead 9.2% of time vs 4.3%; gems lost in bags 140 vs 34.
- Time: walking 53% (move_bag 27 + move 26), camp 18, recall 6, hold 5, dead 4-9, fight 3, tribute 2-3.
  Walk-outs from spawn/recall ~22% of alive time (~48 recalls per team-game, ~18 turns walk-out each).
- Captures by side (gems/game): winner own 715 mid 155 enemy 130; loser own 635 mid 76 enemy 72.
- Supply: idle (up & asleep) gem-cycles 2400/game of 4676 theoretical. Monoliths ~90% idle (on 29% of maps),
  golems ~60% idle (34% of maps). 67% of maps have 5 picks.

## 2. Survey digests (code + priors), key points
Code (ocean): `decide` = fixed-priority fallthrough chain (no cross-branch scoring). Farm = per-champion argmax of
rate(worth, trip+clear+capture+heal trips) with static side weights (home_ground, middle exposure x1.36), stickiness.
No per-group enemy-danger term; unseen enemies dropped after track_horizon=3 rounds; no shared enemy info in comms;
enemy respawn windows computed but unused; claims are the only intent channel; crews via implicit proposals (crew.cc).
Banking: min_bank 25 threshold + chain rule. Shop trips by wants_shop rule. ~16 free comms bits.
Priors: rigid coordination (packs, hunts, summons, duos, distress, rallies, cohesion leans) lost every time (-1..-30).
Wins: crew economics priced in farm (CH256, +11), time-at-work (recall lines, recall as travel, +9), min_bank 25 (+3.7),
turn order (+2-3), value holders. Enemy sightings in comms lost (-2..-3.5: "allies give way to enemies they can't see").
Static side pricing beats dynamic denial/zone terms (several level results). Kills: +1 net kill at r300 -> 85% win;
first kill 77%. 81% of self-play deaths are ganks from fog; 88% follow a retreat; 63% of champion deaths in/near a retreat.
Fish (weaker live opp) packs at camps (joins clears, escorts captures, median ally 2 tiles), takes monoliths 75% vs our 26%.
- Solo vs idle (s-200003, one side, 256 maps): ref reaches 1000 at r644 mean (trib@300 284, @600 766; gold@300 1823).
  Mirror games last 865 rounds: interaction (and sharing the map) costs ~25% of the rate.
- Economy curve (mirror, winner vs loser): str x1.39 vs 1.36 at r200, x2.36 vs 2.16 at r600. Carried gems are 40-50%
  of collected mid-game (r300 winner carries 150, tributed 185). Gaps at r200 are small (trib 103 vs 92).
- Monolith games (151/512): only 71 ever hit a monolith (first hit median r579), 66 captured one (first capture
  median r690); team with more monolith captures wins 49/54; first capturer 44/66. Golem maps (175): 6.2 golem
  captures/game, first median r317; more golem caps wins 97/126. Monolith groups: 174 single, 88 of size 9.
  Back-of-envelope: a 5-champion monolith grind at r300 (~360 dps) ~= 0.32 gems/champ-turn incl. heal trips (mirror
  average 0.23, solo 0.31) + 300 gold; better later. Lever limited to 29% of maps (~+2 overall alone).

## 3. Candidate directions (02:30)
C1 heavy jobs (monolith/golem team clears earlier, tank rotation, team-throughput pricing).
C2 enemy picture (persistent/shared beliefs) + farm risk & opportunity pricing, enemy-death windows.
C3 bag/tribute economy under threat (carried gems 40-50% of collected; bags fed to kills).
C4 hold escorts / implicit support at captures (Fish: 1.1 idle allies within 5 at payouts vs our 0.7).
Waiting on study1 (decisive events, death contexts, waste) to rank.

## 4. study1 findings (analyst on 512 mirror games; scripts in /home/ubuntu/wt/macro2-an/study1/)
- Predictors: gold EARNED at r150 is the best single predictor (cvAUC .699; kills .632; value .670). Non-kill (farm)
  gold lead at r150 >=300 -> 78% win, <=-150 -> 23%. Gold lead >=400 at r300 -> 91%. Lead permanent median r380 (value).
  First kill -> 68% (median first kill r208). Net kills +1 at r150 -> 75%.
- Fights: 28.5 engagements/game, 24% with a kill. Numbers advantage barely converts: margin +1: adv kills 13.4% vs disadv
  9.9%; +3: 20% vs 11.5%; numbers-advantaged engagements fail to kill 85%. Initiator gets more kills 66%.
  Deaths: 37% outnumbered, 21% alone, 26% retreating; 54% while walking, 31% in a fight it joined/started.
- Recalls: 56/team-game (!), 49% at >=90% HP, 50% with bag 0; 65% end in a purchase (median 120 gold).
  Cost (channel + walk-out to next hit) ~34 champion-rounds each -> ~1570 champion-rounds/team-game.
  Vesper recalls 24/game, Issac 18, Prism 16, Cassi 14 (melee tanks 4-7).
- Abandoned approaches (walk >=5 toward an up group then leave): 202/team-game; strict (no enemy seen, nobody hit it,
  leg not ending at a camp) 61/team-game, ~1054 rounds. U-turn excess 197 rounds/team-game.
- Idle off spawn 4.9% (47% near respawning camps, 23% at altars).
- Crews: per champion-round at the clear, gems drop with hitters (Elk 1.61 solo -> 0.52 with 5; Wolf .60 -> .33;
  clusters 1.79 -> 0.78 with 2). Crew join walk-in ~960 rounds/team-game, 102 joins. Golem mean 2.8 hitters,
  Monolith 3.9 (clear 38 rounds, 4234 dmg taken).
- study1 final: deaths: healthy (median 85% HP), empty-bag (58%) walkers (59%) in MID (67%) who SAW the killer (80%),
  burst within ~2 rounds. Pooled HP share decides engagements (0.6-0.8: 19% kill/5.7% loss; 0.8+: 38%/4%).
  Value per champion-round (clear+walk-in+hold): Monolith .85 gems/1.2 gold, Golem .53/1.9, Elk .40/1.9,
  Clusters .37/1.0, Wolf .22/1.4. Monolith first hit r567, 53% untouched. Pass-bys of asleep up groups at hp>=70%,
  bag<20, no enemy: 109/team-game (wolves 52, clusters 30). Own side safe (enemy takes 1-3%); mid split 43/43.
  94% of earned gold is capture gold.
- Priors that bite: pack zone for empty-handed 48.1% (deaths up), relocating instead of retreat level, predictive
  ambushes 50.1%, monolith sieges when rate beats team's 48.3% (started r320, never cleared), eris any-side monoliths
  54.4% on monolith maps, duos/packs lost, join-your-mate's-fight -2.

## 5. Decision 02:15: first two implementation tracks (economy, the teacher's domain)
- T1 `macro2-heavy`: heavy-camp programme (golem + monolith) with team-throughput valuation (breaks the circularity:
  crew value counts only allies already near, so nobody goes), staged crews, tank discipline.
- T2 `macro2-plan`: chain lookahead in farm (each first job valued with its best follow-up from its end place/time),
  respawn-timed second jobs, pass-bys as chains. Screen in solo.py first (fast, deterministic), then mirror A/B.
- 02:25 launched implementers T1 (macro2-heavy) and T2 (macro2-plan); briefs in research/macro-2026-11-11/briefs/.
  T3 brief written (team engagement verdicts, macro2-fight): queued until a slot frees. Fight transcripts confirm
  superior local groups dissolve (1v3 where our Vendetta dashes in alone while Varg farms then retreats).
  Sample of 335 narrated fights: 273 no kill; bigger side kills in ~13% of uneven fights.
- Confirmation suites generated: s-200031..s-200060 (held out; don't screen on them).
- 02:37 T2 macro2-plan done (solo jobs only get chain lookahead; crews/shares untouched; chain_first 6, chain_next 8).
  Its 5 local games: 3 bad losses incl. 00interlock with 11-13 deaths (noise?). Started A/B `macro2-plan`
  (s-200001..20, --sprt --sprt-seed 1) and solo `solo-plan` (s-200003). Launched T3 implementer (macro2-fight).
- solo-plan (T2) vs ref solo: round to 1000 +2.1% [+0.6,+4.0] (SLOWER), trib@600 -17.5, 110 maps faster/146 slower.
  Lesson: the one-job greedy is not the farming bottleneck in solo; lookahead chains don't help (maybe hurt via the
  no-follow-up bias). Solo farming looks near a local optimum -> the mirror is decided by interaction.
- A/B macro2-plan (T2) vs ref: 45.6% of 1306 (CI 43.0-48.3), SPRT H0 (seed 1). OOF 158 vs 44 at 2x fuel. DEAD.
  Mechanism: no solo gain and in the mirror worse; chain-picked solo jobs pull champions off crews/contested work.
- 03:04 T1 macro2-heavy done (heavy_plan in crew.cc: team-throughput prefix search over arriving allies, Golem ops
  reuse Monolith staging; heavy_clear_rounds = siege_rounds 76). Local: monolith map wins big, golem map erratic
  with many champion deaths. Started A/B `macro2-heavy` (20 suites, --sprt --sprt-seed 2).
- A/B macro2-heavy (T1): 48.6% of 869 (CI 45.3-51.9), SPRT H0 (seed 2). By class (1084 games incl. post-stop):
  Golem maps 45.3% (n375), Monolith maps 47.1% (n280), neither 50.7% (n521). Mechanism fires (golem first capture
  r222 vs r331; M caps .24 vs .16, O caps 1.30 vs 1.09) but elk/wolf/cluster captures fall and earned gold is lower
  (r300 1544 vs 1572). DEAD: repeats priors (heavy jobs cost the rest of the farm).
- Interim lesson (03:15): two economy refactors (T2 chains, T1 heavy) both lose. Ocean's farm sits at a robust local
  optimum for farming in isolation; the leverage is interaction (fights, contests, deaths). T3 (fights) running.
- 03:15 FINDING: Cassi & Issac drafted in 96% of team-games; pair dies 1.46/game (both bodies each time) vs Vesper
  .42, Prism .69: ~37% of all deaths; 41% of FIRST kills are a C&I body (Cassi 103, Issac 91 of 472); Prism is the
  top first killer (143). Pair apart: median 9 tiles; at death partner >8 tiles away 46%. Launched T4
  (macro2-pair): pair stake = both lives + both bags in own risk decisions; enemy pair = double-value prey.

### 03:19 T3 (macro2-fight) delivered; A/B launched (SPRT seed 3, s-200001..020)
- Design: a joint verdict per skirmish per round (`combat/skirmish.cc`). Members are us plus allies in the fight square or in strike reach. `Safety::skirmish_fight` simulates every member walking in. ENGAGE if we win on net kills even when they strike first (focus = the first enemy to fall, visible and off the spawn edge). DISENGAGE if we lose on net kills even when we strike first. NONE otherwise.
- Posted over comms (~10 bits: parity, verdict/focus, member mask). ENGAGE followers skip the recall, the pack zone and shopping, chase the focus, and the step guard checks lethal tiles only. DISENGAGE followers go home when any threat reaches their tile.
- Known: the sim's weakest-member bias pushes verdicts towards D; there is no hysteresis.
- A/B macro2-fight (T3): 50.0% of 3338 (CI 48.3-51.7), SPRT H0 (seed 3). OOF 300 vs 147.
  Mechanism (3462 games): deaths 4.27 vs 4.60 a game, recalls 45.2 both, capture gems 897 vs 896, earned r150 714 vs 719,
  r300 1637 vs 1649. Fewer deaths but no economy gain: DISENGAGE retreats likely cost what the saved deaths are worth.
  NEUTRAL. Follow-up asked of T3's implementer: macro2-fight2 (engage-only, hysteresis without new constants, fuel skip).
- 03:40 T4 macro2-pair delivered. Offence: kill_bag = 2 lives + both bags for a linked enemy body, in the strike
  search, casts, prey and turn-order bids. Defence: healthy C&I off its own ground gets the pack zone at hurt_retreat_ratio,
  with linked pooled health = min. Farm: a pair body prices an enemy-reachable unsupported group x pair_hold_share (0.55).
  A/B `macro2-pair` launched (20 suites, --sprt --sprt-seed 4).
- A/B macro2-pair (T4): 46.5% of 634 (CI 42.7-50.4), SPRT H0 (seed 4). Mechanism: deaths 3.86 vs 3.79 (no saving),
  capture gems 894 vs 909, earned r300 1605 vs 1618, fewer elk/wolf/cluster caps. The off-ground pack zone and the farm
  discount cost farm time and saved no lives. DEAD.
- 03:45 Time budgets (macro_stats). Solo: walk 52% (move_bag 27, move 25), camp 25%, recall 7.3%, hold 5.9%;
  walk-outs from spawn/recall 22% of alive time, 43 recalls/team-game. Mirror winner/loser: camp 18/16.7%, dead
  4.3/9.2%, fight 2.9%. Captures/round 0.062 (mirror winner) vs 0.089 (solo).
  Tribute gems 1055 vs 524: the loser captures 783 vs 1000 and loses 139.5 gems in bags vs 34.
- Theory (labour-bound economy): recall channel + walk-out ~= 22-33 champion-rounds; per champion a recall every
  ~75 rounds -> ~29% of solo time. Shop trips are 50% of recalls. wants_shop prices "buy now" against "never buy"
  (full-horizon gain x 0.75), not against "buy later with more gold". EOQ: trip when the holding loss accumulated
  since the last buy equals the trip cost. A rough estimate puts the batch at ~290 gold against the median 120.
  -> T5 `macro2-shop` launched (brief briefs/T5-shop.md).
- 03:40 (clock check: real time; earlier "03:40/03:45" labels were ~5 min early) Debug mirror D-line branch
  shares (512 games, s-200001, batch macro2-dbg): F 58.7%, B 7.8%, dead/none 6.9%, h 6.2%, R 6.1% (263 runs/game,
  mean 2.2 turns; F->R 170, R->F 160 a game: flapping), P 3.6%, K 2.0%, C 1.9% (83 runs), Q 1.6%, T 1.5%, U 1.5%,
  S (dedicated shop trip) ~0% (1 run/game!). Shop recalls come from the farm's recall option (F->K 40/game, priced
  by farm_recall = heal + FULL-horizon emblem gain) and capture recalls (P->Q 37/game). T5 brief extended to those
  values. Retreat anatomy analyst launched on this batch.
- A/B macro2-fight2 (T3b: engage-only, hysteresis, fuel precheck): 49.6% of 2138 (CI 47.5-51.7), SPRT H0 (seed 5).
  OOF 159 vs 86. Team engagement verdicts are neutral in both forms: DIRECTION CLOSED. Lesson: ocean's local fight
  judgement is not where games are lost; binding allies to a joint verdict neither converts kills nor saves time.
- 03:55 Bag-weighted deaths (dbg batch, 256 distinct games; side-swapped pairs are byte-identical): 100+ bag deaths
  0.38/game carry 92.7 of 190.8 gems lost/game; nearly all are Prism (bags to 1019); 80% on the losing team.
  ocean's Prism keeps every gem (retaining_gems) until its bag wins. Tributes of 400+ gems (87% Prism): 1.88
  starts/game, 19% complete (stun 325, lock 161, manual 260 cancels); a completion wins 96%. Prior repo work: Prism
  banking / earlier Prism retreats / health buying all level or lost (EXPERIMENTS 2026-11-10). Not pursued for now.
  Draft rates per team: C&I .96, Prism .78, Vesper .71, Willow .62, HoR .35.
- 04:00 Retreat anatomy (analyst; scripts scratchpad/retreat): 131 R runs/team-game; 45% are healthy (>=0.8),
  unhit, nearest enemy >=5: 85% of those take no damage in 10 rounds, the enemy chases 10%, ~206 champion-rounds per
  team-game lost (flinch total 374 = 8.6% of live turns). Mutual flinches: 58% of runs; 21 same-group standoffs a game,
  capture split evenly. 83% of deaths are during or right after a retreat (fatal runs: HP .70, hit first 42%, chased
  47%). Flinch rate by enemy distance: 8% at 1, 41% at 3, 74% at 5, 88% at 6, 91-97% at 7+.
  Diagnosis: both sides' stand tests read equal fights as lost (conservative initiative), so both flinch.
  -> T6 `macro2-stand` launched: the stand test gives the initiative to the side not walking in, for healthy unhit
  non-carriers (brief briefs/T6-stand.md).
- 03:58 T5 macro2-shop (EOQ cap: every trip's shop value = min(full-horizon gain, holding loss accumulated since the
  last buy)). Solo s-200003: round to 1000 -0.5% [-1.2, +0.2], gold earned r300 +58 [+30, +85], tributed equal.
  A/B: 49.4% of 2034 (CI 47.2-51.6), SPRT H0 (seed 6); OOF 244 vs 84. NEUTRAL: fewer trips buy farm time but stats
  arrive later; the two cancel (as shop_gain_scale's tuning implies). Shop timing is not a lever. CLOSED.
- 04:18 T6 macro2-stand delivered. KEY MECHANIC FOUND: turns alternate by priority, so each enemy champion gets 2 turns
  before our next every other round and 0 the round after (round parity). Calm stand retreats: in 93/106 wasteful
  cases the striker is an enemy with two turns before ours, which really does strike first: the old they-first
  ordering is exact there. That parity is the R F R flapping. As built (initiative to us only when no roster enemy
  strikes first) it flips 0-9 stand verdicts a team-game. A/B launched (seed 7). Asked for macro2-stand2 (the
  commitment bet): a double-turn enemy outside its first-turn reach counts as walking in (the enemy commits only
  ~10% of the time).
- A/B macro2-stand (T6): 49.9% of 1252 (CI 47.2-52.7), SPRT H0 (seed 7). As expected from its tiny reach. NEUTRAL.
- A/B macro2-stand2 (commitment bet: a double-turn enemy outside its first-turn reach counts as walking in):
  49.3% of 1555 (CI 46.8-51.7), SPRT H0 (seed 8). NEUTRAL. The flapping costs both sides alike; holding ground
  against the double turn gains nothing. STAND DIRECTION CLOSED.
- 04:30 Checks: vision share of alive enemies seen, winner vs loser: .197/.192 (r1-150), .248/.243, .304/.287. Not a
  lever. First kill wins ~68% whatever its round (no early-kill premium). Winning bags convert in a median 19 rounds;
  the first holder wins 95%.
  TODO notes: "every macro gain came from more time working; coordination toward fights lost every time";
  the kill gap is reach and lost stands.
- Willow (62% of teams): heals 15.5 HP/round against a capacity of ~52 (3 x Focus every 8 rounds), so ~30% used;
  camp damage 6.6k vs ~18k for Vesper. The heal is an unused labour resource (a heal trip ~33 champion-rounds).
  -> T7 `macro2-medic` launched (briefs/T7-medic.md): heal value targeting, attend the top camp-damage ally,
  optional farm heal budget.
- 04:42 macro2-mono (T1's heavy programme on Monolith groups only; byte-identical to ref on maps without a Monolith):
  on the 741 Monolith maps of s-200021..030 (`/home/ubuntu/wt/macro2-maps/mono-21-30`, 1482 games): 48.0%
  (CI 45.4-50.5). DEAD: the team-throughput Monolith programme loses on the very maps it targets.
- 04:49 Fresh-eyes researcher (read-only Plan) proposals:
  (1) start Monoliths only in enemy death windows. Monolith clears are contested: 25% are stolen (the stealer
  does 43% of the damage), and the clearer loses 0.69 bodies an episode vs 0.49. Episodes started with an enemy dead
  (n=47): 37 rounds to capture vs 61, deaths 0.33 vs 0.69, stolen 19% vs 23%.
  (2) join enemy Monolith clears late.
  (3) hold back contested respawns: a group returns only at a round start with all its tiles empty; the nearer team
  takes 84-85% of mid respawns; ceiling ~+1-2.
  -> macro2-monowin (macro2-mono + death-window gate on starting a Monolith op) being built.
- T7 macro2-medic delivered: heal targets by value (trip saved per HP) with urgent first; Willow attends the ally
  with the highest camp intake (or a crew's planned tank) from tiles outside camp reach; farm integration skipped (no
  comms room). Locally: healing per round about equal, her camp damage halved. A/B launched (seed 9).
- A/B macro2-medic (T7): 48.8% of 1326 (CI 46.1-51.5), SPRT H0 (seed 9). DEAD. Attending cost Willow's own farming
  (camp damage halved) and healing per round did not rise.
- Per-map-family split of macro2-fight (3462 games): no family stands out beyond noise (|z| < 2), so there is no
  map-conditioned harvest.
- 04:57 macro2-medic1 (T7 part 1 only: Willow's heal targets by trip-time value, urgent first, the waiting mate next;
  positioning = ref): 50.5% of 4016 (CI 49.0-52.1), SPRT H0 at 52 (seed 10). LEVEL, slightly positive; acts only in
  the 62% of team-games with Willow. Kept as a logical component.

## 05:05 Replay watcher (8 mirror games where the loser was level at r150)
Three failures account for every game in the sample, none of them farming efficiency:
- **A. Prism bag duels** (5 of 8 decided by a Prism kill). Focus grows 1.5 per carried gem, so a banker's spells
  become one-shots: stun 1.5xFocus at reach 4, area 1xFocus at reach 5, neither with a walk.
  - Over all 256 games: 45 Prism-on-Prism kills of 100+ bags, and the victim's team lost 41. The victim had seen
    its killer the turn before in 33, the killer carried the bigger bag in 32 and had its stun ready in 31, and the
    victim's stun was cooling down in 28.
  - Rule: never end a turn inside an enemy Prism's one-shot reach unless our burst kills it first, and keep the
    stun in reserve.
- **B. Lockouts.** In 63 one-altar games, the loser was locked out 50+ rounds longer in 44 (the reverse in 5).
  - Ref hits a lock only when a bank walk happens to end in range. Carriers flip B/R near locked altars: 1711
    episodes, which ended in death 99 times for losers against 35 for winners.
  - Rule: breaking a lockout is a team task (5 hits in total, ranged reach 3, melee 1), and carriers wait.
- **C. Piecemeal engagements:** lone fighters, and solo camp pokes that can't clear.
Next: T8 lock siege (briefs/T8-lock.md) now; the Prism duel (A) after monowin.

## 05:13 macro2-monowin: 48.1% of 1482 (Monolith suite), CI 45.6-50.7
mono plus a gate: Monolith operations start only inside enemy death windows. The gate rarely opens (a window is at
most ~60 rounds, while heavy_plan's need runs 61-149), so most games run no Monolith operations. No better than mono
(48.0). The Monolith track is closed: ref's own handling is at least as good.

## 05:18 macro2-medic1 on s-200021..030: 50.1% of 5120, CI 48.8-51.5
With s-200001..020 that makes 9136 games at ~50.3%: level. A/Bs are fast here (5120 games in under a minute of
wall time), so compute is no constraint; the implementers are the bottleneck. From now on every screen runs 10k+.

## 05:22 Lock warfare in ref-vs-ref (512 base games)
- One-altar maps: 117 of 512 games. Median game 935 rounds. Each side is locked out of every altar for a mean of
  532 rounds (loser) or 370 (winner).
- 1499 breaks, about 12.8 a game:
  - First hit to break: median 77 rounds, quartiles 32 and 122.
  - 4.85 hits from 1-2 hitters, so a hit lands about every 15 rounds, only when a bank walk ends in range.
  - The owner relocks a median 39 rounds after a break. In that window the breaker's team tributes about 109 gems.
- 2+ altars: 1745 breaks, median 62 rounds. Lockout means are 88 rounds (loser) and 52 (winner).
- The lever is consecutive hits: a siege landing 5 hits in a few turns saves about 70 rounds of lockout per break.

## 05:40 macro2-lock (T8 siege + carriers wait): 46.8% of 10240, CI 45.9-47.8 (lost)
- Release split on s-200001..002: one-altar 47.0%, 2+ altars 46.3%. A debug rerun on s-200001..002 gave 46.0% of 1024 (one-altar 37.2%, 234 games).
- The mechanism works. Lockout per game, cand vs ref: 346 vs 444 rounds on one-altar maps, 56 vs 76 on 2+.
  Breaks on one-altar maps: 1948 vs 1690, and the owner takes longer to relock (median 41 vs 33 rounds).
- But the breaks don't convert:
  - Gems tributed before the relock average 73 per cand break, against 109 per ref break.
  - 30% of cand breaks yield no tribute at all (13% for ref).
  - On one-altar maps the candidate tributes 683 a game vs 866, and dies 8.1 times vs 6.3.
  - Bank-walk turns drop from 553 to 351.
- Diagnosis: "carriers wait" keeps the bags away from the altar, so when a lock breaks nobody is there to bank. Ref's
  B/R hovering looks wasteful, but it parks the bags beside the altar for the moment it opens.
- Next: macro2-lock2 keeps the siege and drops the carriers wait.

## 05:52 macro2-lock2 (siege without the carriers wait): 47.6% of 10240, CI 46.7-48.6 (lost)
- s-200001..002 by altar count: one-altar 45.3%, 2+ altars 45.9%.
- Identity check (debug, s-200001, lock vs base): of the games where the siege never fired, 290 match ref-vs-ref
  exactly and 9 differ. The siege fired in 213 games and changed 210 of them. So the loss comes from siege episodes,
  and it shows on 2+ altar maps too.
- Diagnosis: recruiting farmers off their farms costs more than the faster breaks gain. A lockout is symmetric, and
  bags keep growing while locked, so nothing is lost unless someone dies.
- Next: macro2-lock3. Only carriers that ref would send to bank anyway break the lock, and they keep hitting every
  turn instead of leaving after one hit.

## 05:55 macro2-duel (T9): 39.1% of 10240, CI 38.2-40.1 (heavy loss)
- Diagnosis of game 185:
  - Safety's one-window model was correct every turn: Focus-scaled burst, area reach 5, and walk+cast 6 on a
    double turn.
  - B died holding a capture in a dead-end pocket. `hold_outlasts` looks only to the payout and never asks whether
    a way out exists after it.
  - B's stun went on a camp while A's Prism was unseen 9 tiles away, never sighted (age 356, track horizon 3).
- Game 249 exposed a real model gap: a double turn allows two casts (stun, then area), 2.5F, where ref counted one
  cast plus a basic.
- Built:
  - (1) a two-cast double-turn burst in safety;
  - (2) a Prism stun reserve that keeps the stun off camps while an enemy Prism could be within 12. Camp stuns went
    from 14-32 a game to 1-4.
- Both together lose 11 points. Splitting into duelm (model only) and duelr (reserve only).

## 06:08 duel split
- macro2-duelm (two-cast double-turn burst model only): 50.0% of 10240, CI 49.0-51.0. Level. A correct rule
  fix, but it doesn't win.
- macro2-duelr (Prism stun reserve only): 39.3% of 10240, CI 38.3-40.2. The whole loss.
- Lesson: the Prism's camp spells drive the economy. Its stun does 1.5xFocus and its Focus grows with the retained bag.
  Camp casts were 26 stuns + 28 area a game at ~0.3 of slot capacity each. Cutting the stuns to 1-4 a game costs 11
  points: far more than any duel it might save.
- Bag duels are rare, while farm damage is every turn. Caution that costs farm output loses in proportion.

## 06:14 macro2-lock3 (carrier-only siege, consecutive hits): 49.9% of 10240, CI 48.9-50.9 (level)
- Only carriers that ref's banking already sends to the altar break the lock. Once in range they hit every turn,
  instead of leaving; no one is recruited off a farm and there is no post-break hold.
- In local games, locks fell within a round of the hits they had left (ref: median 77 rounds).
- Level overall. On s-200001..002: one-altar 45.3% (234 games), 2+ altars 47.1%.
- The lock track is closed. Lock timing is real, but in a mirror it is worth ~0: the bags wait safely and are
  scored either way.

## 06:28 macro2-medic1 held out (s-200031..060): 50.1% of 15360, CI 49.3-50.9
- In all, 24496 games at ~50.2%: level, no regression.

## 06:35 Farm-waste analyst (256 debug mirror games, 512 team-games)
- About 40% of F turns (~1110 per team-game) end without our team capturing the group.
  - Walks abandoned before arrival: 537 (net ~236).
  - Woke the group but left it uncleared: 194.
  - Enemy captured it during our walk or engagement: 116 + 114.
- 57% of F turns are walking.
- The strongest predictor is the group's side: waste is 27% on our side, 59% mid and 82% on the enemy side. The
  bot-observable race (our walk vs the enemy spawn's walk) gives 34% waste when we are 5+ closer and 82% when 5+
  farther.
- Retarget triggers: 88 a team-game with no event and 73 after a scheduled respawn. Both are time-inconsistent
  switches.
- T12 (briefs/T12-commit.md): farm targets change only on new information. Running alongside T11 (camp spells).

## 06:46 macro2-spells (T11): 50.0% of 10240, CI 49.0-50.9 (level)
- Step 1 found ref already casts nearly every ready camp slot it usefully can.
- Uncast ready slots near camps are walks that matter: ranged champions step from 4 to 3 for an extra basic, worth
  more than moving the cast schedule up a turn. The rest are channels, Monolith safety, enemies near, and low-value
  Cassi stuns under cast_cost.
- The only fix was a cast on hold turns with no basic target. It fired about once in 3 games. Level, as expected.

## 07:18 macro2-race (T13): 44.8% of 10240, CI 43.8-45.8 (lost)
- Change: farm value x p_win, with p_win = 1/2 when the enemy's earliest arrival comes before our clear + hold.
  The arrival is from tracked positions, or the spawn walk for enemies out of track.
- For enemies out of track, the spawn walk beats a slow clear even on our own side, so own-side groups got halved,
  picks moved from mid to own, and it lost 5 points.
- Lesson: ref's static `home_ground` (spawn-walk ratio ^1.89) already prices the race. A step race on top over-prices
  contest. The 82% enemy-side waste is the price of contesting, and contesting is worth it.

## 07:23 macro2-commit (T12): 48.6% of 10240, CI 47.7-49.6 (lost)
- Change: keep the farm target unless news arrived (group state, claims, crew, enemy in sight, own health or bag, a
  turn off the farm, or a value drop).
- Root causes of the no-news switches:
  - the `max_wait` gate, which lets a respawning group enter the ranking only when our wait would be 2 rounds or
    fewer;
  - `rate()` is a ratio, so a near small group overtakes a far big one as both arrivals shrink;
  - crew values that move with ally visibility.
  The switches are not pure waste: many are sensible on-the-way detours, and holds rarely lasted (median 2 rounds).
- Lesson: ref's per-turn re-planning plus stickiness 1.2 is better than commitment. A "wasted" walk often still
  steps toward the group reached next.

## 07:36 macro2-duelm held out: 50.0% of 15360 (CI 49.2-50.8). macro2-combo = medic1 + duelm + spells' hold cast
- s-200001..030: 50.6% of 15360, CI 49.8-51.3.
- Held out s-200031..060: 50.5% of 15360, CI 49.7-51.3.
- Pooled: 50.55% of 30720 (CI about 50.0-51.1). The best candidate, but no more than marginally above level.
  Three rule-derived pieces that never fire on most turns.

## 07:42 macro2-combo on fresh s-200061..100 (mapgen ladder-v2, made now): 50.6% of 20480, CI 49.9-51.2
- Pooled over three disjoint sets: 25873 wins of 51200 = **50.53% (95% CI 50.10-50.97)**. Small, but positive.
- Out-of-fuel turns are about level (985 vs 891 on the fresh set; 771/755 and 745/733 earlier).
- T14 (briefs/T14-exits.md: hold exit check plus a kill-bid lethal check, on top of the combo) is being built.

## 08:00 macro2-held (T15, on combo): 49.9% of 10240, CI 48.9-50.9
- The escape plan now counts each ready enemy spell on every turn from its ready turn, at most once. Before, it
  counted the spell only on the first two ready turns, so it was both optimistic and double-counting.
- Out-of-fuel turns rose to 896 vs 511, from a 1.5-2x pass cost.
- Not better than combo (combo was 50.6% on s-200001..030). Dropped: the verdicts change rarely, and the fuel cost
  eats what they gain.

## 08:06 macro2-exits (T14, on combo): 50.3% of 15360 (s-200001..030), CI 49.5-51.1
- Changes: a hold exit check, and kill bids barred from lethal tiles. Neither check fired in the reruns.
- In game 185, `hold_outlasts` already rejects the hold, but `want_home`'s stand tests keep the Prism anyway. In the
  yin-yang game, the step toward the enemy came from `retreat()` off an already-lethal tile, not from `keep_bid`.
- No better than combo (50.6% on the same suites). Dropped.

## 08:26 macro2-healstay (T16, on combo): 50.5% of 15360 (s-200001..030), CI 49.7-51.3
- Change: an ally counts a visible Willow's coming heal in its heal-trip pricing (`heal_rounds_now`, `trip_spare`).
- It rarely changes a recall: 0-4 decisions a game.
- Same as combo on the same suites (7758 vs 7765 wins). Dropped.

## 08:27 macro2-combo on 10 stress suites (`--mix varied`, v-200101..110): 50.6% of 5116, CI 49.3-52.0
- Robust: no loss on the varied stress maps.

## 09:15 macro2-lstep (T17, on combo): 50.76% of 51200 (CI 50.33-51.20), shipped as ocean 508
- Diagnosis of the yin-yang death: `flee_camps` ranked only the steps down the camp-exit field. To escape a
  20-damage wolf, it walked the 228-gem Prism into a one-cast kill while a safe sideways step existed.
- Fix: non-lethal steps rank first, and an enemy-lethal best step defers to `retreat_step` when it has a safe step.
  It fires rarely (1 LSTEP in 3 games).
- Results on combo's three sets:
  - s-200001..030: 50.8% of 15360;
  - held-out + fresh s-200031..060 and s-200061..100: 50.8% of 35840;
  - varied stress suites: 50.6% of 5116.
  - Out-of-fuel turns level.
- Paired with combo: +118 wins of 51200 (n.s.), but logical and never worse. bots/ocean = macro2-lstep (commit
  c3e459e6e).

## 09:21 Cleanup
- Deleted my replays: base, dbg, lockdbg and solo batches, and sample1. The findings are recorded above, and the games
  are deterministic, so they can be re-run.
- Extracts remain outside git in /home/ubuntu/wt/macro2-an. Maps are in /home/ubuntu/wt/macro2-maps
  (s-200001..100, v-200101..110, mono-21-30).

## 09:22 macro2-lstep (= ocean 508) on fresh s-200111..130: 50.5% of 10240, CI 49.6-51.5
- Pooled over four disjoint ladder-v2 sets: 31166 wins of 61440 = **50.73% (95% CI 50.33-51.12)**.
- Out-of-fuel turns level (517 vs 526).

## 09:23 macro2-lstep on fresh s-200131..150: 51.3% of 10240, CI 50.3-52.3
- Pooled over five disjoint ladder-v2 sets: 36418 wins of 71680 = **50.81% (95% CI 50.44-51.17)**.
- Out-of-fuel turns on this set: 908 vs 545, in a similar number of games (367 vs 368), so a few games ran long
  out-of-fuel streaks. Over all sets: 3939 vs 3511.

## 09:29 macro2-lstep on the Monolith suite (mono-21-30, overlaps s-200021..030): 51.1% of 1482, CI 48.5-53.6
- No weakness on Monolith maps.

## Final state
- bots/ocean = macro2-lstep (ocean 507 + 508): 50.81% of 71,680 vs ocean-ref-b7c87cf at 2x fuel.
- Write-up: macro2.md.
