# Experiments

What has been tried on our bots, so it isn't repeated. Win rates are against the bot's own previous version on all maps
(ladder + `maps/gen` + `maps/gen-central`, 390 games) from both sides at the real fuel budget, unless noted; `all` adds
two fresh-seed suites (746 games), `full` one more (1102). Noise is about ±2.5 points on 390 games; "level" means within
noise. Don't retry a lost or level idea as is: it needs a new mechanism or ladder evidence. Results on older bots are
hints, not rules. Git history has the branches, commits and per-suite numbers behind each line.

## General

- Gains on the committed suites shrink on fresh seeds (crews +22/320 -> +8/320; a 54.6% hecate bundle was 47.8% on a
  fresh suite): confirm on suites with a fresh seed.
- Local games are deterministic: rerunning the same maps gives the same results.
- Self-play hides ladder behaviour. Our bots start a recall at every turn end and cancel it the next turn, so locally
  enemies look like they are recalling in ~90% of rounds (5-8% on the ladder): any value for cancelling an enemy recall
  is inflated locally, and an ally's `channel == recall` does not mean it is going home.
- Bug fixes, drafts and map-type strategies have paid off. Retuning tactics or pricing against our own bots rarely has;
  whole-model ports (morgana's farm pricing into nemesis 43.0%, a pack zone decided by the fight sim 46.9%) lost.
- Who wins: in the mirror the side that dies first loses 70%, and +1 net kill at round 300 takes the win rate from 56%
  to 85%. A fight's swing is predicted by HP fraction, lifetime gold and the initiative; head count adds nothing once
  those are in. contest is the only ladder map that reaches round 2000: 31% of its games tie on gems, then gold decides.
- Fuel-only changes (byte-identical at 100M) still reroute real-budget games: savings scored 47.5% and a control burning
  2k fuel a turn 48.4% (full). Neither direction helps; judge them by fuel and out-of-fuel turns, not win rate.

## aphelios and morgana (2026-10-15/16)

- One champion per camp: 38-45% (deaths with no ally within 6 doubled). Waiting at respawning groups: 45%. Won:
  discounting enemy-ground groups by min(1, 2·d_enemy/(d_ally+d_enemy)) with ×1.2 stickiness.
- ~20 tactical tweaks level or worse: retreat variants, fighting back when doomed, ally assist, a strike-first fight sim
  alone, pushing when ahead, gold in camp value, Focus on Ren/Tavi, Durability as second emblem (−15), a farm-race draft
  rule, steering around the pack zone (−15/240). Won: crews, draft order (Varg 3rd), a stun valuation bug, lock/tribute
  bugs.
- One-price farm valuation: ~52% vs morgana-v5, 100% on Monolith-only maps. Needed: the first claimer owns a group; a
  respawning group's attack tiles exclude its camp tiles; no face-clearing when camp DPS × exit hits exceeds health at
  the recall line. Lost: discounting reward by enemies that could reach (−3 to −20), two-job lookahead (−24), a
  constant gold share (−4 to −8), pooled crew health (−3). Capping waits at a quarter of a respawn: small maps 25% -> 50%.
- Picking up cleared groups in sight plus team-total banking: 52.8% (gold-only captures 529 -> 1849 per 264 games).

## nemesis (2026-10-17/18)

- Won (from rival): max_wait 5; home_retreat ratio 2 in our own half; finishing_camp over all awake groups, plus
  camp_trapped; a sticky siege target with 2 Monolith holders; shop recall and chain_bag_limit 80; camp tie-break by
  turn order; retreat by the least exposed homeward step (about +5).
- Lost or level: other drafts (37-50%) and Fish builds (−3); pack bonus or spread penalty in farm value; Monolith sieges
  on normal maps (39.6%); stickiness 1.0 (−5); shopping at 300 gold (−7); casting before walking (46.2%); camp damage in
  the fight sim (47.7%); a periodic ward rule (48.7%); ranking jobs by worth − ρ·cycle (27-34%); EOQ bag limit,
  capture-recall heal value, tank assignment, stun value max(80, next-turn damage), Smith targeting; Treasure as second
  emblem, Stellar ground-skip fix, tank priority, pursuit sim, attack-tile adjacency, symmetric fight arrivals, exact
  enemy-turn threat model, camp clear sim, gold-as-score on Monolith-only maps; a crowd rule and farm-zone avoidance
  with an empty bag (−3.5 vs rival).
- The whole team as one PVP pack (brawler): 2-8% vs nemesis. It earns ~150 gold a game against 540-940, and a pure pack
  can't out-score five farmers.

## hecate (2026-10-18 on)

Shipped changes are in [hecate/CHANGES.md](hecate/CHANGES.md).

### Strategy and economy

- Level or lost: true first striker in the fight sim, shopping ×2 emblems, third-party camp damage in the fight sim,
  rally assist, caster poke from our own ground, Cassi/Issac target priority, kite cap 40, altar control (6 variants),
  central-group kiting, Focus builds (−4), other drafts (no Cassi 39.5%), Monolith and cluster sieges on normal maps
  (5-40%), Monolith sieges on any map when their rate beats the team's (48.3%: started ~r320, never cleared in time).
- Ladder-motivated, lost locally: gold valued 3× in farm choice (46.9%), the top teams' draft (Ren, Stellar, Cassi,
  Ryth, Varg) with Focus Ren (42.3%), Cassi gold weight 10 instead of 4 (49.2%), gold front-loaded by gems left (47.2%,
  45.6%), a 100+ carrier going home from any visible threat (48.7%). These target gaps seen against Intercontinental Fish
  ([FISH.md](FISH.md)) that our own bots don't exploit: judge them on the ladder.
- Big bags: an escort (a 150+ carrier waits for 2 allies; empty-handed allies within 18 guard it) was level locally
  (51.3%) and halved big bags lost on Monolith-only maps, but lost on the ladder (scrims vs the top 5 on the same maps:
  28-47 -> 26-49 and 24-51; stampede 0-1080 once escorts left the shared block). Reverted. A 150+ bag treated like
  Cassi/Issac (a fight where the carrier falls counts as lost) lost bags faster to a carrier hunter: lone retreating
  carriers get run down. Untried: keep the carrier with allies and flee towards them.
- Kept: carriers on their own ground are chased when the bag can be stopped (`intercept_steps`): full 51.1%, bags taken
  +29%, bags lost −21% (any carrier: 49.7%). Stopping a visible game-ending bag (`stop_game_ender`): level in
  self-play, 57.5% vs 55.6% against nemesis-v2. Contesting any gem capture: 50.5%.
- Kept: farm clears with spells from out of the camps' reach (`spell_clear`) and first picks up a cleared group in
  sight (one taker per group): 51.0%. Without the pickup 48.5% (clear-to-hold latency 5.1 vs 4.1 rounds).
- Kept: passing hits skip damaging groups that aren't our choice unless an ally clears them or (melee) they are awake
  (level). Dropped: the pack zone for empty-handed farming too (48.1%; deaths up).
- 2026-10-19 vs hecate-v6 (1a80ff8). Kept: a spellcaster draft (Stellar, Ryth, Prism, Ren, Cassi, Varg, ...) on
  shared-gem maps, 63.3% on 120 shared-gem games (two fresh-seed sets of 30 maps plus the suites' own); the same
  order on Monolith-only maps lost (45.1% of 122), so it is gated on `shared_gems` alone. Level: life_value 600 and
  1000 (both 50.0%); away pack ratio 3.0 (50.5%); a chase catch test (beyond range + 1 only a carrier, a hurt enemy or
  with a dash ready) plus a kill-per-turn floor at the farm step value (50.3%); a game-ending bag tracked out of sight
  met at its nearest altar with a lock, plus locks on any altar from enemy score 700 (50.8%); following a teammate's
  rally while the enemy is unseen (50.0%, ladder 11/34); a Monster emblem priced in best_emblem (49.5%). Lost: home
  retreat ratio 3.0 with away 3.0 (46.7%); live Monolith sieges on mixed maps when nearer our spawn, 40-round limit
  (48.2%); Monster, Home and Treasure priced together (44.6%); farm value halved for groups within 3 of a believed
  enemy's reach (41.5%).
- Ladder, 2026-10-19, scrims vs the top 5 on the same maps (75 games each, ±5.5): version 25 31-44; plus fuel round
  3 alone (v28) 30-45; plus the stunned-turn skip too (v27) 26-49; plus the gate removals and the shared-gem draft
  (v26) 24-51. The stunned-turn skip was byte-identical in the local fuel A/Bs and only shows against real opponents;
  reverted (the recall guard stays). Fish went 3-12, 2-13, 1-14, 0-15 across the four. Version 29 (v26 without the
  stun skip) 29-46: level with v28, so the gate removals plus the shared-gem draft are a wash on the ladder; the draft
  went 2-3 on stampede against v28's 3-2 and was reverted too, as a local-only gain.
- Emblems: the next one by measured value (Jungle, Power, Durability priced by the rounds they save) 52.0% full; on
  Monolith-only maps the coming siege priced before any camp has hit us (39/60 on extra Monolith-only maps against 30
  for the fixed order); a begun emblem priced by its remaining shards 51.6%. Dropped: the model over five families and
  Health or main stat (Monolith-only 9/38); Home emblem as second (50.4%) or first (48.9%) emblem.
- Sieges: a heal-trip bug (recall kept, cancelled next turn) fixed: 51.1-51.2%, gen-monolith-only 9/24 -> 17/24; the
  siege role survives the heal-trip turn (50.7%) and fight turns (level). Siege readiness with heal trips: level.
- Banking: `closing()` banks when score + team bags + team rate × (walk + tribute) reach 1000: 50.7%; the same horizon
  bounds farm's chain deadline: 51.3%. In losses most carried gems are fresh captures, not missed banking.
- Locks, measured: they cancelled 19 tributes each way in 390 games, and a lock costs a carrier ~3 attacks or a detour,
  so the ceiling is small. Locks only on enemy-side and middle altars: 47.6% (our own-side locks matter).
- Bug-fix bundles, all kept and level: fight sim (Ren's reflection after our own turn, stuns only on fighters in reach,
  `turns_to_kill_idle` joins enemies like `pursuit`, `recall_outruns` uses `threat_strike`); a teammate's sighting fixes
  the enemy at the sighted tile, comms group fields 8 bits; emblem pricing; `siege_candidate` skips live Monoliths off
  Monolith-only maps; kite/contest timing on `enemy_hold_left`; waiting at an unsafe altar capped at the walk to the
  next; a stunned turn skips acting. Wrong and reverted: the crew value with capture rounds (48.0%; the claimer holds,
  the crew moves on); `passing` instead of `affordable` for hits after a walk (49.5%).

### Fights and planning

- Strike planner (`plan.cpp`: every legal attack/reset/cast/walk/dash sequence priced in enemy health points): 52.2%
  vs hecate-v2, 53.4-54.0% vs main. Lost on the way: ranged carriers holding fire to keep walking (47.9%); an early
  `prey()` for the intent (32k fuel, nothing measurable). A farming step priced at a full turn of output cost Ryth's
  and Ren's stuns 9-17% of their hits; at output × gems per camp HP × gem_value they recover.
- Retreat planner (`plan_turn`, branch plan3, unmerged): level at 100M (49.7%) and at the real budget (49.8%), but
  2.5x main's out-of-fuel turns. Each priced tile needs a `Safety::blow` per enemy (~500 per uncached Reach query) on up
  to 49 tiles. Also lost: the chase as a goal planned before acting (43.0-46.2%); a stun valued by the turn it denies
  instead of a flat 80 (48.5%).
- Wall- and sight-aware danger model (`Reach`): changed few decisions (want_home 3.5k of 1.4M evaluations, step_guard
  6.2k of 1.3M, prey 6.3k of 1.2M) and was level at 100M (48.2%); its first version lost to fuel (41.3%). Merged after
  its fuel rounds at 49.1%.
- Loss analysis (mirror, 390 games): winners die 2.0 times a game against 4.1. 86% of deaths carry no gems; 79% are on
  our own ground, but the risk per champion-round is 3.4/1000 on enemy ground vs 0.7 on ours; 88% follow a retreat
  within 4 turns. Retreat triggers before a death: pack zone 200, low health 186, lost fight 128, pursuit 115, none 85,
  lethal 55. Time in rounds 1-300: walking to camps 33%, attacking camps 25%, walking to altars 8%. Weak families against
  other bots: huge, large-open, islands, Monolith-only, maze, rows.
- Single-map flips between versions (corners, interlock) follow fuel trajectories, not regressions.

### Fuel

- Savings rounds, byte-identical at 100M: round 1 −11% a turn; round 2 (bush clusters grown in the warm-up, measured
  worst costs in the estimates); exact fight simulation (fighters made once a turn, quiet turns reused; trade 4.7k ->
  4.0k a call); Reach (ways kept per recipe, static windows once per tile, lazy builds); WASM-aware (−4.2%); host-op
  (sight() skips bush and wall work when none is near); round 3 −17.7% (farm caches keyed by camp versions, want_home's
  quiet-turn exit, enemy_seen early outs, sight masks built lazily). Tried and slower or no gain: raw bitboard reads
  instead of `is_set`, WASM bitmask searches, a stalemate early-out in `simulate`, damage-bound settling before
  simulating, a per-side cast plan (+37%), a farm straight-line prefilter, field steps read from WASM memory,
  per-group camp-damage boxes, Reach as per-enemy host boards, no warm_reach at all (more out-of-fuel turns).
- What runs out: fight turns. `step_guard`'s exact tile looks (Reach queries on new tiles, ~850-1200 each) and its
  simulations, then `want_home` and `prey` simulations, the planner, and farm on cold 100x100 starts (centre warm-up
  takes 19-54 rounds there). An out-of-fuel turn resumes next round on stale beliefs and can chain; the cascade breaker
  (StaleTurn at decision checkpoints) keeps them single.
- Gate removals: every gate at once raised out-of-fuel turns from 8 to 100-200 per 16 bench games, and removing only the
  fight-simulation gates from 83/67 to 150/176: a "skip when short" gate adds work exactly when fuel is short. Kept
  removals: turn order without a threat build, a capped chase route, altar fields on demand, fight memo 32. Round 3
  added `step_guard`'s 20k reserve and per-tile check and skipped the turn end, comms send and prepare below 1500.
- Fuel-gate removal 1a on hecate-v5 ([hecate/FUEL-GATES.md](hecate/FUEL-GATES.md)): enemy-cast, camp-cast, route-retry,
  crow-flies-kite and travel-dash gates gone; `approach` no longer sizes its search by fuel. Byte-identical at 100M;
  head-to-head vs hecate-v5 on all maps 49.7%, out-of-fuel turns 187 vs 169 in 390 games. The costlier gates
  (turn-order, farm-no-route, farm-kept-target, static-descend) raised out-of-fuel turns 48/36 -> 121/112 per 16 bench
  games on hecate-v4: they wait until step_guard and farm fit. The first turn has no room for extra work: it ends with
  1.3-9k left on lanes, swirl, corners, pilgrimage and ambush (world setup 46-75k, decision 64-116k).
- Measuring out-of-fuel turns: the 16-game bench (`tools/fuel/bench.py --fuel 0`) swings by about ±20 and has no
  shared-gem maps. Over all maps, hecate-v5 runs out ~170 times in 390 games (14% of games), a third of them on two
  shared-gem maps (gen-shared-gems-640105705 alone ~50), then contest and stampede. Count them on the full suite.
- World and economy round on hecate 110e338, byte-identical at 100M (46 bench games vs rival and nemesis): −3.2% a turn
  (−2.2% on heavy maps), p99 −1.4%, turns over 100k −5%, round 1 without the warm-up −8% (lanes ~208k -> ~180k). Wins:
  `always_inline` on farm's lambdas, whose captured locals otherwise live in memory (−0.8% alone); `[[gnu::flatten]]` on
  farm, update_camp(s), track, observe, comms receive, route, plan_strikes and the warm-up; camp updates in a member
  function; liveness read only out of view; first-use caches in static arrays, not vectors; scratch boards for warm-up
  temporaries. Slower: flatten on decide (+0.7%), update_champion or continue_recall; refixing a seen enemy by moving
  its one tile; camp member visibility from the tile list; a Chebyshev bound before farm's steps; by-value captures;
  dash widening by dilation and walks by capped fields (+0.4-1.5%). Fuel is ~1 per WASM instruction, loads included.
