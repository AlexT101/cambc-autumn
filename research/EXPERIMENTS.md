# Experiments

What has been tried on our bots, so it isn't repeated. Win rates are against the bot's own previous version on all maps
from both sides at the real fuel budget, unless noted. Until 2026-10-20 "all maps" was ladder + the old `maps/gen` (132)
+ `maps/gen-central` (46), 390 games; `all` added two fresh-seed suites (746 games), `full` one more (1102). Since then
it is ladder + the unified `maps/gen` (256 maps, 554 games; noise about ±2.1 points). Noise is about ±2.5 points on 390
games; "level" means within noise. Don't retry a lost or level idea as is: it needs a new mechanism or ladder evidence. Results on older bots are
hints, not rules. Git history has the branches, commits and per-suite numbers behind each line.

## General

- Gains on the committed suites shrink on fresh seeds (crews +22/320 -> +8/320; a 54.6% hecate bundle was 47.8% on a
  fresh suite): confirm on suites with a fresh seed.
- Local games are deterministic: rerunning the same maps gives the same results.
- Self-play hides ladder behaviour. Our bots start a recall at every turn end and cancel it the next turn, so locally
  enemies look like they are recalling in ~90% of rounds (5-8% on the ladder): any value for cancelling an enemy
  recall is inflated locally, and an ally's `channel == recall` does not mean it is going home.
- Bug fixes, drafts and map-type strategies have paid off. Retuning tactics or pricing against our own bots rarely
  has; whole-model ports (morgana's farm pricing into nemesis 43.0%, a pack zone decided by the fight sim 46.9%) lost.
- Who wins: in the mirror the side that dies first loses 70%, and +1 net kill at round 300 takes the win rate from 56%
  to 85%. A fight's swing is predicted by HP fraction, lifetime gold and the initiative; head count adds nothing once
  those are in. contest is the only ladder map that reaches round 2000: 31% of its games tie on gems, then gold
  decides.
- Fuel-only changes (byte-identical at 100M) still reroute real-budget games: savings scored 47.5% and a control
  burning 2k fuel a turn 48.4% (full). Neither direction helps; judge them by fuel and out-of-fuel turns, not win
  rate.

## aphelios and morgana (2026-10-15/16)

- One champion per camp: 38-45% (deaths with no ally within 6 doubled). Waiting at respawning groups: 45%. Won:
  discounting enemy-ground groups by min(1, 2·d_enemy/(d_ally+d_enemy)) with ×1.2 stickiness.
- ~20 tactical tweaks level or worse: retreat variants, fighting back when doomed, ally assist, a strike-first fight
  sim alone, pushing when ahead, gold in camp value, Focus on Ren/Tavi, Durability as second emblem (−15), a farm-race
  draft rule, steering around the pack zone (−15/240). Won: crews, draft order (Varg 3rd), a stun valuation bug,
  lock/tribute bugs.
- One-price farm valuation: ~52% vs morgana-v5, 100% on Monolith-only maps. Needed: the first claimer owns a group; a
  respawning group's attack tiles exclude its camp tiles; no face-clearing when camp DPS × exit hits exceeds health at
  the recall line. Lost: discounting reward by enemies that could reach (−3 to −20), two-job lookahead (−24), a
  constant gold share (−4 to −8), pooled crew health (−3). Capping waits at a quarter of a respawn: small maps 25% ->
  50%.
- Picking up cleared groups in sight plus team-total banking: 52.8% (gold-only captures 529 -> 1849 per 264 games).

## nemesis (2026-10-17/18)

- Won (from rival): max_wait 5; home_retreat ratio 2 in our own half; finishing_camp over all awake groups, plus
  camp_trapped; a sticky siege target with 2 Monolith holders; shop recall and chain_bag_limit 80; camp tie-break by
  turn order; retreat by the least exposed homeward step (about +5).
- Lost or level: other drafts (37-50%) and Fish builds (−3); pack bonus or spread penalty in farm value; Monolith
  sieges on normal maps (39.6%); stickiness 1.0 (−5); shopping at 300 gold (−7); casting before walking (46.2%); camp
  damage in the fight sim (47.7%); a periodic ward rule (48.7%); ranking jobs by worth − ρ·cycle (27-34%); EOQ bag
  limit, capture-recall heal value, tank assignment, stun value max(80, next-turn damage), Smith targeting; Treasure
  as second emblem, Stellar ground-skip fix, tank priority, pursuit sim, attack-tile adjacency, symmetric fight
  arrivals, exact enemy-turn threat model, camp clear sim, gold-as-score on Monolith-only maps; a crowd rule and
  farm-zone avoidance with an empty bag (−3.5 vs rival).
- The whole team as one PVP pack (brawler): 2-8% vs nemesis. It earns ~150 gold a game against 540-940, and a pure
  pack can't out-score five farmers.

## hecate (2026-10-18 on)

Shipped changes are in [hecate/CHANGES.md](hyperion/CHANGES.md).

### Strategy and economy

- Level or lost: true first striker in the fight sim, shopping ×2 emblems, third-party camp damage in the fight sim,
  rally assist, caster poke from our own ground, Cassi/Issac target priority, kite cap 40, altar control (6 variants),
  central-group kiting, Focus builds (−4), other drafts (no Cassi 39.5%), Monolith and cluster sieges on normal maps
  (5-40%), Monolith sieges on any map when their rate beats the team's (48.3%: started ~r320, never cleared in time).
- Ladder-motivated, lost locally: gold valued 3× in farm choice (46.9%), the top teams' draft (Ren, Stellar, Cassi,
  Ryth, Varg) with Focus Ren (42.3%), Cassi gold weight 10 instead of 4 (49.2%), gold front-loaded by gems left
  (47.2%, 45.6%), a 100+ carrier going home from any visible threat (48.7%). These target gaps seen against
  Intercontinental Fish ([FISH.md](FISH.md)) that our own bots don't exploit: judge them on the ladder.
- Big bags: an escort (a 150+ carrier waits for 2 allies; empty-handed allies within 18 guard it) was level locally
  (51.3%) and halved big bags lost on Monolith-only maps, but lost on the ladder (scrims vs the top 5 on the same
  maps: 28-47 -> 26-49 and 24-51; stampede 0-1080 once escorts left the shared block). Reverted. A 150+ bag treated
  like Cassi/Issac (a fight where the carrier falls counts as lost) lost bags faster to a carrier hunter: lone
  retreating carriers get run down. Untried: keep the carrier with allies and flee towards them.
- Kept: carriers on their own ground are chased when the bag can be stopped (`intercept_steps`): full 51.1%, bags
  taken +29%, bags lost −21% (any carrier: 49.7%). Stopping a visible game-ending bag (`stop_game_ender`): level in
  self-play, 57.5% vs 55.6% against nemesis-v2. Contesting any gem capture: 50.5%.
- Kept: farm clears with spells from out of the camps' reach (`spell_clear`) and first picks up a cleared group in
  sight (one taker per group): 51.0%. Without the pickup 48.5% (clear-to-hold latency 5.1 vs 4.1 rounds).
- Kept: passing hits skip damaging groups that aren't our choice unless an ally clears them or (melee) they are awake
  (level). Dropped: the pack zone for empty-handed farming too (48.1%; deaths up).
- 2026-10-19 vs hecate-v6 (1a80ff8).
  - Kept: a spellcaster draft (Stellar, Ryth, Prism, Ren, Cassi, Varg, ...) on shared-gem maps, 63.3% on 120
    shared-gem games (two fresh-seed sets of 30 maps plus the suites' own); the same order on Monolith-only maps lost
    (45.1% of 122), so it is gated on `shared_gems` alone.
  - Level: life_value 600 and 1000 (both 50.0%); away pack ratio 3.0 (50.5%); a chase catch test (beyond range + 1
    only a carrier, a hurt enemy or with a dash ready) plus a kill-per-turn floor at the farm step value (50.3%); a
    game-ending bag tracked out of sight met at its nearest altar with a lock, plus locks on any altar from enemy
    score 700 (50.8%); following a teammate's rally while the enemy is unseen (50.0%, ladder 11/34); a Monster emblem
    priced in best_emblem (49.5%).
  - Lost: home retreat ratio 3.0 with away 3.0 (46.7%); live Monolith sieges on mixed maps when nearer our spawn,
    40-round limit (48.2%); Monster, Home and Treasure priced together (44.6%); farm value halved for groups within 3
    of a believed enemy's reach (41.5%).
- Ladder, 2026-10-19, scrims vs the top 5 on the same maps (75 games each, ±5.5): version 25 31-44; plus fuel round 3
  alone (v28) 30-45; plus the stunned-turn skip too (v27) 26-49; plus the gate removals and the shared-gem draft (v26)
  24-51. The stunned-turn skip was byte-identical in the local fuel A/Bs and only shows against real opponents;
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
- Locks, measured: they cancelled 19 tributes each way in 390 games, and a lock costs a carrier ~3 attacks or a
  detour, so the ceiling is small. Locks only on enemy-side and middle altars: 47.6% (our own-side locks matter).
- Bug-fix bundles, all kept and level: fight sim (Ren's reflection after our own turn, stuns only on fighters in
  reach, `turns_to_kill_idle` joins enemies like `pursuit`, `recall_outruns` uses `threat_strike`); a teammate's
  sighting fixes the enemy at the sighted tile, comms group fields 8 bits; emblem pricing; `siege_candidate` skips
  live Monoliths off Monolith-only maps; kite/contest timing on `enemy_hold_left`; waiting at an unsafe altar capped
  at the walk to the next; a stunned turn skips acting.
  - Wrong and reverted: the crew value with capture rounds (48.0%; the claimer holds, the crew moves on); `passing`
    instead of `affordable` for hits after a walk (49.5%).

### Fights and planning

- Strike planner (`plan.cpp`: every legal attack/reset/cast/walk/dash sequence priced in enemy health points): 52.2%
  vs hecate-v2, 53.4-54.0% vs main. Lost on the way: ranged carriers holding fire to keep walking (47.9%); an early
  `prey()` for the intent (32k fuel, nothing measurable). A farming step priced at a full turn of output cost Ryth's
  and Ren's stuns 9-17% of their hits; at output × gems per camp HP × gem_value they recover.
- Retreat planner (`plan_turn`, branch plan3, unmerged): level at 100M (49.7%) and at the real budget (49.8%), but
  2.5x main's out-of-fuel turns. Each priced tile needs a `Safety::blow` per enemy (~500 per uncached Reach query) on
  up to 49 tiles. Also lost: the chase as a goal planned before acting (43.0-46.2%); a stun valued by the turn it
  denies instead of a flat 80 (48.5%).
- Wall- and sight-aware danger model (`Reach`): changed few decisions (want_home 3.5k of 1.4M evaluations, step_guard
  6.2k of 1.3M, prey 6.3k of 1.2M) and was level at 100M (48.2%); its first version lost to fuel (41.3%). Merged after
  its fuel rounds at 49.1%.
- Loss analysis (mirror, 390 games): winners die 2.0 times a game against 4.1. 86% of deaths carry no gems; 79% are on
  our own ground, but the risk per champion-round is 3.4/1000 on enemy ground vs 0.7 on ours; 88% follow a retreat
  within 4 turns. Retreat triggers before a death: pack zone 200, low health 186, lost fight 128, pursuit 115, none
  85, lethal 55. Time in rounds 1-300: walking to camps 33%, attacking camps 25%, walking to altars 8%. Weak families
  against other bots: huge, large-open, islands, Monolith-only, maze, rows.
- Single-map flips between versions (corners, interlock) follow fuel trajectories, not regressions.
- Strike search phase 1 (2026-10-21, orch/int-strike-p1 dbab204, not merged): plan_strikes' fixed menu replaced by one
  search over every legal walk/attack/reset/dash/cast sequence, camps as targets with wake pricing, bound-ordered Reach
  pricing (research/hyperion/strike-notes.md). Against main: 38.5% of 582 (ladder 30.0, gen 39.6), out-of-fuel turns 16282
  against 946 (all but 0.1% in decide). At 100M fuel still 40.5% (ladder 44.3, gen 40.0): deaths 6.0 against 4.5 a game
  (+34%), captures -4%, tributed -7%. The exhaustive and old-menu checks never fired, but 113 dashes were refused with
  no fuel shortage. Lost; with unlimited fuel it still dies more, so the search or its leaf score misjudges danger.
  Round 2 (orch/int-strike-p1 2277faf on main 0bfc997): dash paths blocked by visible enemy champions
  (probe-dash-enemy), a move must lead to a strike, wakes priced per camp phase, no landing wakes sleepers, fuel cuts.
  52.6% of 582 (ladder 54.3, gen 52.3), but out-of-fuel turns 3441 in 398 games against 1191 in 308 (99.5% in decide;
  elk-arena, contest, hooks, shared-gems, diamond, lanes worst). At 100M 55.2% (ladder 55.7, gen 55.1). Kept and
  merged (main e2242aa) on the keep rule: it wins at the real budget with its out-of-fuel turns included. STRIKE-SEARCH's
  out-of-fuel rule is owed by a fuel-only follow-up (decide), pending.
- Strike search phase 3a (2026-10-21, orch/int-strike-p3a): an enemy Varg's basic attack reaches a tile through a
  unit beside it (our other visible champions, live camp members), with Strike +1 for Varg's basic attacks. 51.0% of
  1094 vs main (ladder 50.0, gen 50.6, fresh gen-s1 51.6), out-of-fuel turns 6551 vs 6471; at 100M 51.4% (ladder
  54.3, gen 49.8, fresh 52.5). Level; kept and merged on the keep rule (follows the rules, plays level).
- Strike search phase 2 (2026-10-21, orch/strike-p2 ported as b76c8b4 on main f6fd561): heal and shield as search
  options. A leaf with its cast unused is offered per end tile with the best heal (min(amount, missing health,
  cooldown x damage_bound at the ally)) and with a shield priced once the tile's foes are priced; decide and act()
  skip their own heal and shield on turns the search planned an exactly priced tile (decide's post-plan shield stays
  for the goal's camp hit). 50.0% of 1094 vs main (ladder 44.3 of 70, gen 52.0, fresh gen-s1 48.8), out-of-fuel turns
  7041 vs 6256 (+12.5%); at 100M 51.1% (ladder 54.3, gen 51.6, fresh 50.2). Level; kept and merged on the keep rule.
  hecate drafts Heart of Ruin first, so only its shield path is live in this A/B (Willow and Varg only in test drafts).
- Strike search phase 3b (2026-10-21, orch/strike-p3b as 1753982 on main a850d48): removal. A leaf's killed foes
  (with a Cassi/Issac partner, seen or not) and stunned foes (stunnable, one turn before ours) leave its end tile's
  danger; each end tile keeps the best leaf per removed set, less those beaten by a superset. 48.9% of 1094 vs main
  (ladder 51.4 of 70, gen 47.9, fresh gen-s1 49.6), out-of-fuel turns 8663 vs 8071 (+7.3%); at 100M 51.0% (ladder
  48.6, gen 51.2, fresh 51.2). Level; kept and merged on the keep rule (follows the rules, plays level).
- Strike search phase 4a (2026-10-21, orch/int-strike-p4a 058f55b on main 971c68b, not merged): retreat turns planned
  by the search under plan3's retreat score (dash_away, flee_camps, retreat_step deleted), unseen threats priced near
  the start and walk tiles. 40.8% of 1094 vs main (ladder 31.4 of 70, gen 41.8, fresh gen-s1 41.0), out-of-fuel turns
  24816 in 897 games vs 10570 in 759 (+135%, 98% in decide); at 100M 52.6% (ladder 55.7, gen 53.5, fresh 51.2).
  Dropped: the play is sound and the 12-point loss is fuel, so the retreat search's cost (builder: mean 21.6k, max
  83.5k) must come down before it is retried.

### Fuel

- Savings rounds, byte-identical at 100M: round 1 −11% a turn; round 2 (bush clusters grown in the warm-up, measured
  worst costs in the estimates); exact fight simulation (fighters made once a turn, quiet turns reused; trade 4.7k ->
  4.0k a call); Reach (ways kept per recipe, static windows once per tile, lazy builds); WASM-aware (−4.2%); host-op
  (sight() skips bush and wall work when none is near); round 3 −17.7% (farm caches keyed by camp versions,
  want_home's quiet-turn exit, enemy_seen early outs, sight masks built lazily).
  - Tried and slower or no gain: raw bitboard reads instead of `is_set`, WASM bitmask searches, a stalemate early-out
    in `simulate`, damage-bound settling before simulating, a per-side cast plan (+37%), a farm straight-line
    prefilter, field steps read from WASM memory, per-group camp-damage boxes, Reach as per-enemy host boards, no
    warm_reach at all (more out-of-fuel turns), the tile table's camp columns summed over only the members within
    reach + 3 of its centre (wave 1: +0.36% as a pass a generation, +0.12% listed in find_members and inlined, on
    the bench and on 7 camp-heavy maps: 0-6 awake members a turn, never more).
- What runs out: fight turns. `step_guard`'s exact tile looks (Reach queries on new tiles, ~850-1200 each) and its
  simulations, then `want_home` and `prey` simulations, the planner, and farm on cold 100x100 starts (centre warm-up
  takes 19-54 rounds there). An out-of-fuel turn resumes next round on stale beliefs and can chain; the cascade
  breaker (StaleTurn at decision checkpoints) keeps them single.
- Gate removals: every gate at once raised out-of-fuel turns from 8 to 100-200 per 16 bench games, and removing only
  the fight-simulation gates from 83/67 to 150/176: a "skip when short" gate adds work exactly when fuel is short.
  Kept removals: turn order without a threat build, a capped chase route, altar fields on demand, fight memo 32. Round
  3 added `step_guard`'s 20k reserve and per-tile check and skipped the turn end, comms send and prepare below 1500.
- Fuel-gate removal 1a on hecate-v5 ([hecate/FUEL-GATES.md](hyperion/FUEL-GATES.md)): enemy-cast, camp-cast,
  route-retry, crow-flies-kite and travel-dash gates gone; `approach` no longer sizes its search by fuel.
  Byte-identical at 100M; head-to-head vs hecate-v5 on all maps 49.7%, out-of-fuel turns 187 vs 169 in 390 games. The
  costlier gates (turn-order, farm-no-route, farm-kept-target, static-descend) raised out-of-fuel turns 48/36 ->
  121/112 per 16 bench games on hecate-v4: they wait until step_guard and farm fit. The first turn has no room for
  extra work: it ends with 1.3-9k left on lanes, swirl, corners, pilgrimage and ambush (world setup 46-75k, decision
  64-116k).
- Measuring out-of-fuel turns: the 16-game bench (`tools/fuel/bench.py --fuel 0`) swings by about ±20 and has no
  shared-gem maps. Over all maps, hecate-v5 runs out ~170 times in 390 games (14% of games), a third of them on two
  shared-gem maps (gen-shared-gems-640105705 alone ~50), then contest and stampede. Count them on the full suite.
- Fight-path round on hecate 110e338, byte-identical at 100M (46 bench games: the default maps vs rival and nemesis,
  heavy maps vs rival): turns over 100k −23/−36/−23%, p999 −6/−7/−6.5%, all turns −1.1/−2.1/−1.2%.
  - Reach::at boxes from span tables, its sight shift out of line and per-way bounds (−14% a query); step_guard bounds
    only foes that can reach a step, asks Reach only of foes in bound reach, reads open tiles packed and memoised
    fights in place; kits kept across turns; threat_strike's widening memoised; camp_damage memo; ward sight cast
    again only when the wards change, read packed; live camps by a per-tile member index; big camp groups skip far
    champions; pack boxes worked out only for outmatching subsets.
  - Tried and slower or no gain: act or hurt inlined into simulate, a loop for plain sides in act (−1%), cast split
    out of attack (+13% a simulation), a cast-only fast path when sums are exact (its checks cost more than it saves),
    ward checks by distance to each ward (+7% a query), a second recipe kept in Reach (recipes rarely flip back), the
    far-champion filter on small groups, a cross-turn simulation memo (2-10% hit rate).
  - On the turns over 95k at 100M the fight cost is simulations ~30k (a 5v5 fight 8-12k), Reach ~25k and step_guard's
    own loop ~9k.
- World and economy round on hecate 110e338, byte-identical at 100M (46 bench games vs rival and nemesis): −3.2% a
  turn (−2.2% on heavy maps), p99 −1.4%, turns over 100k −5%, round 1 without the warm-up −8% (lanes ~208k -> ~180k).
  - Wins: `always_inline` on farm's lambdas, whose captured locals otherwise live in memory (−0.8% alone);
    `[[gnu::flatten]]` on farm, update_camp(s), track, observe, comms receive, route, plan_strikes and the warm-up;
    camp updates in a member function; liveness read only out of view; first-use caches in static arrays, not vectors;
    scratch boards for warm-up temporaries.
  - Slower: flatten on decide (+0.7%), update_champion or continue_recall; refixing a seen enemy by moving its one
    tile; camp member visibility from the tile list; a Chebyshev bound before farm's steps; by-value captures; dash
    widening by dilation and walks by capped fields (+0.4-1.5%).
  - Fuel is ~1 per WASM instruction, loads included.
- Fight-path round 2 on hecate 72cc39c, byte-identical at 100M (same 46 games, measured before the last commit): turns
  over 100k −20/−24/−23%, p999 −5.6/−4.2/−4.8%, max −7.5/−6.4/−7.1%, all turns −1.1/−1.4/−1.2%.
  - Simulation: sentinels for idle, no shield and worthless slots, hurt()'s common case inline, an exact-sum fast turn
    for sides whose Strength and cast damage are small sixteenths (casts add to the cached basic attacks), the weakest
    kept across shields and heals that cannot change it (−14% a simulation on recorded fights).
  - Hidden writes: vec2 and std::pair zero their members, so step_guard, prey, retreat_step and pack_boxes cleared
    hundreds of bytes a call, and Reach::at its sight windows; constructing the Reach pool wrote ~50KB at each game's
    first fight and the strike memos ~6KB on round 1 (now zeroed static storage).
  - dist() in 32-bit (the SDK's is 64-bit: −0.2% on every turn).
  - Memos per ready slots: strikes and Reach ways (cooldowns flip recipes back and forth; the single-entry memos
    missed most turns).
  - Also awake_members works out turn order only near a member's reach, fight keys read joining allies once a turn,
    best_ground clears only cells it reads, the pack zone is drawn as squares and prey tests coverage from its boxes.
  - Tried and slower or no gain in games (judge with whole games: ±0.1% swings from codegen alone): shields in the
    fast turn (−1.8% on big recorded fights, +1.4% on small), side-level shield expiry, a cache of built fight sides
    (a Side copy is memory.copy at a fuel a byte), a bulk side fill (−35% in a microbenchmark, slower in games),
    step_guard's bound from per-foe offsets or row/column tables, pack boxes by a pruned subset search (recursion), an
    early stop in Reach::at when the rest is dominated, packed bits instead of is_set for near_enemy_spawn (the host
    test is cheaper), lethal settled by strike bounds first (the Reach builds only move elsewhere).
  - Top turns (shared-gem maps, ~270k) are still step_guard's 6v6 simulations (~10k each, ~11 a turn), Reach (~35k)
    and fight setup (~1.5k a simulation).
- World, economy and SDK-call round 2 on hecate 85a648a, byte-identical at 100M (46 bench games): −11.2% a turn on the
  default maps vs rival, −13.1% heavy, −11.0% vs nemesis; p99 −5.5/−6.4/−5.4%, p999 −3.6/−5.2/−4.0%, turns over 100k
  284/90/278 -> 220/69/213; round 1 without the warm-up mean 143k -> 139k (max 180k -> 175k).
  - Real budget: shortcuts on the default maps 1665 -> 1018 and vs nemesis 1700 -> 1062, out-of-fuel turns 1/2/0 ->
    0/3/0 (noise).
  - Found with a line profiler that counts every WASM op per source line and function (assembly instrumented, counters
    dumped inside debug_block). Simple host calls cost only ~3-5 fuel; the waste was the WASM around them.
  - Wins: hecate's own host reads test the result inline (`ok()`) instead of calling the SDK's out-of-line `check()`
    (−1.2%), with raw helpers for tile tests, field steps, bitboard clear/set/square/empty/count/positions, occupancy
    and scores, outputs in static storage rather than stack slots (−0.4% each batch); `World::me()` through a kept
    pointer and `enemy_seen()` cached until a champion update (−2.1%); loops over visible enemies return at once when
    none is seen (game_ender −0.6%, five more −0.7%); our handle read once at start-up and round_now into static
    storage (−0.9%); read_priorities and update_champion in locals, out of reach of aliasing stores (−1.4%, −0.3%);
    World::fix inlined so update_champion passes no struct through memory (−0.4%: vec2 and Moment are passed by
    pointer to a stack copy when not inlined); group_at/altar_at and the spawn fields inline in the header (−0.35%,
    −0.1%); dist() and central tiles in 32 bits; slot() from kept team sizes; update_camps reuses last turn's visible
    groups while the camp tiles in view are the same (one IsEqual host call; −0.3% to −1%); route's neighbour scan raw
    and bounds-free off the edge (−0.4%); no ward attempt on a stunned turn (every one threw error 63, ~3.9k).
  - Slower or no gain: `always_inline` on the SDK's check() through a pre-declaration (+2%: inlined throw paths bloat
    every wrapper); an ally_seen() cache (allies are usually in view, +0.2%); farm's loop index without modulo and its
    claim test as one mask (0%); a precomputed crew list (costs more than the claimed groups it serves); CampGroup
    tile/threat accessors inline (round 1 +640, no gain); moving the teleport branch out of update_champion (identical
    fuel); Moment comparisons field by field (+0.02%); vector resize instead of reserve+push_back for camp health
    (round 1 +840).
  - farm's loop (~280 ops a group, ~10 groups a turn) is now ~17% of WASM ops and at its floor for local changes.
- Fight-path round 3 on hecate bbd10a9 (merged with the world round 2), byte-identical at 100M (46 bench games):
  before the merge −0.81/−0.95/−0.85% a turn, p999 −5.3/−4.5/−4.5%, turns over 100k 210/67/200 -> 168/56/160; after it
  (raw SDK helpers in the fight path, step_guard's visible key) a further −0.26/−0.26/−0.27%, p99 −0.5/−0.7/−0.6%,
  turns over 100k 125/44/121 -> 123/39/117.
  - Mostly "known case inline, work out of line": struck(), reach_of(), terrain(), the threat build, gone(), foe
    counts, camp members, cost estimates and fighter slots each test their ready state inline and call a noinline
    builder, so callers keep their locals in registers.
  - Also Reach::at settles a near way outside bushes from its box and tests wards once a query; enemy ward sight
    refreshed from one raw occupancy read and compared in place; step_guard asks each foe's Reach directly and
    simulates an unknown fight without a second memo search; the Reach cost estimate counts a pending mask built once
    a refresh; fight sides filled in one pass with tallies in locals; simulate's debug tallies compile-time; static
    windows place rows by constexpr shifts.
  - Real budget (games diverge, so noisy): out-of-fuel turns 1/5/3 -> 0/0/1 before the merge, 0/0/0 with both rounds;
    step-guard shortcuts 117/421/186 -> 114/175/108 before the merge, 87/327/78 with both.
  - Slower or no gain: per-round static caches in small inlined helpers (+0.1-0.5%: codegen around them grows), a
    turns_before_ours cache (+0.1%).
  - Leads: the general simulation path for Varg shields (~5k a heavy turn), Reach::at's fixed cost (~10k a heavy
    turn), step_guard's own loop (~8.5k) and pack_boxes (~3k).
- Fight-path round 4 on hecate 98706e5, byte-identical at 100M (46 bench games): −1.53/−2.40/−1.59% a turn (default vs
  rival, heavy, vs nemesis), p99 −2.1/−2.6/−2.1%, p999 −2.1/−2.3/−1.9%, max −1.5/−1.8/−1.6%, turns over 100k
  123/39/117 -> 112/31/101.
  - Wins: Safety lists its enemies once a turn as masks (alive and visible; alive, unseen and tracked), and every
    enemy loop in Safety and in step_guard, prey, killable_now, visible_threat and shield_if_needed walks the mask
    instead of testing each belief (−0.6/−0.8/−0.65%, then −0.24/−0.39/−0.27%: a loop over the 152-byte beliefs costs
    ~25 ops an enemy); camp members written into pre-sized storage rather than push_back (−0.26/−0.43%);
    strike()/threat_strike() return their memo by reference (−0.09%); kite's bitboard calls through the raw helpers
    (heavy −0.24%); distance thresholds whose distance is unused tested as a square by unsigned offsets (`in_square`:
    camp members' reach −0.1/−0.18%, blow() −0.1%, fighting_allies' ally squares p999 −0.5 to −0.95%, in_pack_zone and
    step_guard's filters −0.06%).
  - Slower or no gain: most_damage cached per turn (+0.02%: called about once a turn), Reach::at's memo hit inline
    with the miss out of line (+0.12-0.15%: the memo rarely hits, and callers grow), hoisted member and health
    pointers in find_members (−0.01%), a square pre-test before find_members' distance (tail +0.3%).
  - Leads unchanged: the general simulation path for shields, Reach::at, step_guard's bound loop (dist ~800 a heavy
    turn), static_window misses (~640 each, ~6 a heavy turn); World-level enemy masks would let the loops in
    abilities.cpp and self_abilities.cpp (no Safety there) and the age-based loops (in_pack_zone, pack_boxes,
    recall_outruns) skip beliefs too.
- World and economy round 3 on hecate c3c874c (not merged: it raises p99 and leaves heavy maps flat, against the aim
  of cutting the tail), byte-identical at 100M (46 bench games): −1.16% a turn on the default maps vs rival, −1.27% vs
  nemesis, 0.0% heavy; p99 +0.2-0.3%, p999 +0.1-0.2%, turns over 100k unchanged; real budget (an earlier setting)
  unchanged: out-of-fuel 0/0/1 as before, shortcuts 751/913/874 -> 762/914/883 (noise).
  - Measured: a simple host call costs 3 + its arguments (sdk_champion 8, round 7, cooldown 9), so caching
    `my_record()` cannot beat the round read its invalidation needs; a field search costs chunks × (16 + layers) + ~30
    over the whole map (100x100: 169 chunks, 2.9k for 1 layer), whatever region it touches, and `route` was 7% of all
    fuel (3.8k a call, 0.6 a turn; inclusive meters: farm 8.7k a turn with its walk, world update 7.1k).
  - Win: `route` keeps its last field, walls and goals and, for the same goals, reuses it while every tile its walls
    changed at is at least our best neighbour's layer (newly blocked) or has no neighbour below it (newly freed, not a
    goal); the layers below the one that reached us are complete, so the neighbours and steps are exact. Checks that
    fail back off (up to 3 calls), guarded searches are neither checked nor kept, at most 4 changed tiles (2: -0.1%,
    6-12: +0.05-0.3%). Hits ~40% of unguarded calls; each check costs 3 board operations and reads (~700 with the
    freed tiles' neighbours), which leaves heavy maps (100x100, crowded) slightly dearer.
  - Not done: farm's loop has no cheap exact pre-rejection (its ~180 ops a group are spread over 25 lines); a cheaper
    reuse check (field values in WASM memory, a host min over a mask) would make heavy maps gain too.
- What fuel costs main (b05d209 vs hecate-v8, 1094 games, both sides; 2026-10-21): real budget 65.7% (ladder 72.9 of
  70, gen 63.9, fresh gen-s1 66.6), out-of-fuel turns 9614 in 714 games vs 2240 in 511; at 100M (both bots) 62.0%
  (ladder 70.0, gen 62.1, fresh 60.7). Main does 3.7 points better at the real budget, so lifting the limit helps v8
  more than main: main's 4x more out-of-fuel turns do not show as lost games against v8. Main alone at 100M against v8
  at the real budget would isolate main's own loss; ab.py's `--fuel` sets both sides.
- bounded-decide (2026-10-21; orch/bounded-decide, kept and merged): fight horizon 24 -> 2 * cooldown + 1 = 17 own turns,
  and exact early ends (our fighter must outlive the rest of the horizon given every attack and ready cast of theirs;
  or we cannot fell any of theirs and their basic attacks alone, less a stunned turn of their strongest per stun,
  beat our health and every heal). Asked at the start and as either side loses a member; a debug check replays
  each fight to the horizon (0 mismatches in 16k fights). Measured on 01elk-arena, 00contest, 00fragment both
  sides at 100M vs main: kills peak right after cast turns (own turns 9 and 17); the 8% of fights undecided at 24
  cost 20% of simulation fuel (16.9k vs 6.1k). 5.8% of fight verdicts change against 24, all lost -> not lost
  (fights first lost on their turns 18-24). Per fight 7.06k -> 6.26k; same games, both bots metered: decide
  25.4k -> 23.7k a turn (-6.7%), decide >= 100k turns 380 -> 349, pursuit 611 -> 441. Real budget, same 6 games:
  out-of-fuel turns 186 vs main 198 (noise). Tried and dropped: damage reaching us only after every weaker ally
  falls (no heals or shields) plus a re-check every cooldown, identical but +0.1% fuel. Fighters were not cut:
  fight keys already hold only enemies whose blow reaches the tile, pursuit only those within `pursuit_steps`.
  A/B vs main b05d209: 49.8% of 1094 (ladder 50.0, gen 49.4, fresh gen-s1 50.2), out-of-fuel turns 10543 vs 11337
  (-7%); at 100M 50.6% (ladder 52.9, gen 49.4, fresh 51.6). Level with fewer out-of-fuel turns: kept.

### Ports from koi (2026-10-20)

Against hecate 3e8dfa0 (`bots/baselines/hecate-v7`), both sides; fresh suites are `replays/koi-maps/` (seeds 7101-7112).

| variant | ladder + gen + central (390) | fresh gen (1848) | central, standard + fresh (552) | all |
|---|---|---|---|---|
| port: farm horizon on the farm side only, wide search, holders as carriers | 52.3 | 52.9 | 48.6 | 52.1 (2698) |
| cycbank: plain farm values, the horizon only on the chain side of the bank test | 50.5 | | 50.5 | 49.8 (850) |
| cycboth (kept): the horizon on the bank-then-farm value too | 55.4 | 51.9 | 49.8 | 51.9 (2698) |

- The port against the older bots (390 each, hecate-v7 in brackets): aphelios 90.8 (91.8), morgana 76.7 (74.9), rival
  74.4 (70.5), nemesis 63.6 (65.1); against koi 48.7.
- The gain is the group choice (nearer, faster cycles), not earlier banking: the koi version's undiscounted bank side
  made carriers bank early, which was level to negative on its own and cost central-altar maps.

### Week 2 patch (2026-10-20)

- Camp reach per monster type from the camp designs, instead of 3 for all: 54.3% vs hecate-v7 (398 games). Kept.
- Gem limits rescaled by stampede's block (big_gems 55, chain_bag_limit 30, brake_bag 11): 52.8% on top (398), 52.3%
  on a fresh suite (264). Kept. With gem_value 40 as well: 50.8%. With life_value 400 as well: identical games (no
  effect).

### Heart of Ruin (2026-10-20)

Against hecate 1251236 (`bots/variants/hor-pre`, frozen pre-change), ladder + gen (554 games) both sides. HoR draft:
heart_of_ruin, stellar, cassi_and_issac, ryth, varg (normal draft with Ren swapped for HoR).

| match | new | pre |
|---|---|---|
| HoR draft vs pre HoR draft | 70.8 (ladder 64.3, gen 71.3) | |
| normal draft vs pre normal draft | 49.8 | |
| normal draft vs pre HoR draft | 54.7 | 52.0 |
| normal draft vs new HoR draft | 37.7 | 34.7 |

- The dash landing (planner, enemy casts, camp casts), the passive in our damage, and the shield gated on the plan
  when a landing is ready (CHANGES 25). An earlier build with ungated shield reads for allies too gave 68.2 / 50.9 /
  53.2 / 37.7 on the same rows.
- Enemy modelling (landing reach, damage and stun, passive, active shields): +2.7 and +3.0 points against the two HoR
  drafts, level in the mirror.
- The new HoR draft beats our normal draft 62.3% (554): a draft change to try next, with ladder evidence.
- Fuel: about +2% a turn from the early turns on (the shield bookkeeping per champion update, the passive in strikes
  and outputs; moving it around shifted the bench by +-100 a turn from layout alone); real budget 0 out-of-fuel turns.

### Gates, crystals, big groups and gem limits (2026-10-20)

Each against the bot before it (frozen in bots/variants), ladder + gen both sides (554). The first three were measured
on hecate 1251236 and rebased onto d70138d (Heart of Ruin) afterwards.

| change | ladder | gen | all |
|---|---|---|---|
| no big-group sieges off shared-gem maps, holders by tribute length (CHANGES 26) | 57.1 | 54.5 | 54.7 |
| siege the group that gates every altar (27) | 57.1 (boss-battle 2/2) | 49.6 | 50.2 |
| crystal hops to altars no walk reaches, crystal bought every life | 45.2 | 52.5 | 52.0 |
| the same, recall out priced, crystal bought on demand (28) | 47.6 | 52.5 | 52.2 |

- No generated map has a gate or a hop (`GATE`/`HOPS` debug line), so the gen columns of 27 and 28 are fuel noise:
  find_gate and find_hops shift round-1 fuel and reroute games. Only boss-battle has a gate; collision and islands
  hops.
- corridors locally vs rival: 812-1026 and 741-1048 before 26, 1012-484 and 1032-122 after (identical to big_gems
  150).
- boss-battle vs the pre-gate bot: 1002-0 and 640-109; mirror games before it ended 0-0 on gold. The siege is slow
  (champions walk into the Monolith's reach 5 to hit it; the key member fell around round 1100).
- Hops without the recall in their price: carriers hopped into collision's vault whenever it was nearer than the mid
  altar and then sat out 5 recall turns and the walk back.
- Dash crossings (one-tile hole/altar lines a dash jumps), counted for a later change: walks from spawn to groups
  shorten by 51% on fracture, 60% on concentrated-wealth, 58% on gold-rush and 11% on islands (+34 groups reachable),
  under 6% elsewhere on the ladder; 17 of 256 generated maps gain more than 5%.
- Dash crossings (CHANGES 29) vs the pre-dash bot: 52.0% (ladder 20/42, gen 268/512). The first version (3d837e6) was
  21-21 on ladder and 105-99 after 208 gen games, with dashers stuck on big-world (Ren still 1004 of 1060 turns) and
  islands (0 camp attacks): approach goals on crossable holes, crossings into camp tiles, recalls out of what looked
  like a crystal pocket, and fields walking along chains of crossable tiles.
- Gem limits after 26: brake_bag 30 50.9% (554), chain_bag_limit 80 52.7% (ladder 42.9, gen 53.5), both at life_value
  / gem_value ladder 22-20. Not adopted; item 24's values stay.
- corridors: lost mirror games show farm targets flipping every turn (32% of farm turns A-B-A on corridors, 1-2%
  elsewhere), crews joining and leaving a group together because claims reach teammates a turn late. Counting only
  allies earlier in index in crew_strength cut corridors flips to 5.5% but lost 44.5% on gen; counting them only once
  in a crew 40.5% ladder, 44.9% gen; seniority for contested claims made corridors flips worse. All dropped.
- A crystal shortcut over open ground (a crystal landing more than twice the channel's turns nearer on foot, for
  corridors' lanes) was left unfinished and dropped: ladder opponents used 9 crystals in 9 corridors games.

### 7515f8e against submission 31: per map, and boss-battle (2026-10-20)

- 53.2% (554; ladder 22/42, gen 273/512). The maps items 26-29 aimed at all won 2/2: corridors 1028-124 and 1007-210,
  collision, fracture, islands, eight (and their gen mutations: collision 4/4, corridors, fracture 2/2).
  `results.json` match `winner` is the 0-based bot index; reading 1 as bot 1 inverts every per-map table.
- 0/2 maps: contest from d70138d on (every commit since lost both; hecate died 41 and 35 times to 5 and 12; the gen
  monolith-only and shared-gems maps went 3/4 each, so it does not carry over). elk-arena, expanse and interlock flip
  between commits: noise at two games a map.
- boss-battle per commit against v31: d70138d and 96f90c7 0/2, ff50c99 and a599469 2/2, 7515f8e 1/2 (0-0 won on gold,
  90-334 lost). In the loss the key Monolith fell at round 1059 and its tile, the only tribute tile, stayed in reach
  of the other Monolith (200 a turn) until 1303: tributes of 53-158 cancelled after a turn, bags of 87, 53, 385, 105
  and 125 lost there. Bags held back while the gate stood reached 400-875 (40-88 turn channels), cancelled by tribute
  safety, stuns and locks; one holder took the pair's 400. v31 banked 19-49 gem bags at the altar we opened.
- Ladder boss-battle (13 games, v30/v31): 2-11. 8 ended 0-0 and we lost all 8 on lifetime gold. Teams that opened it
  killed both Monoliths in a burst, captured and held the tile: :3 dealt 39.8k in rounds 1200-1250, captured 400 and
  banked 1987 in one channel (won round 1531); OneTap killed both twice and banked 190, 320, 49 and 200.
- Live camps lengthen or cut a walk to an altar on 14 of 277 maps (ladder + gen): only boss-battle cuts it; spiral (30
  groups, +28 steps each) and cross (10, +15) are the only real detours, the rest under 10 steps.

### Draft search after the Heart of Ruin nerf (2026-10-20)

Details in [hecate/DRAFT.md](hyperion/DRAFT.md). Each pick scored on maps of its pick count (ladder + gen), screened on
45% of them and confirmed on the rest. Kept: Heart of Ruin, Marcella, Vesper, Ryth, Stellar, ...: 69.3% vs the old
draft on a fresh-seed suite (512 games; 3/4/5-pick 71.1/63.1/73.8).

- Heart of Ruin is the core: replacing it in HoR/Stellar/Cassi lost 12-48% (80 games each). Marcella (62.5% in
  Stellar's slot) and Ryth were the best additions; Prism, Tavi and Willow lost in every slot of a trio.
- Trios: HoR/Marcella/Cassi and HoR/Marcella/Vesper level (50.0%, 178), both ~61% against the field; the old trio
  Ren/Stellar/Cassi lost 69.7-72.5% to them, and HoR/Stellar/Ren (a common ladder trio) 64-73% to the top three.
- 4th: Ryth (53-60% over Vesper or Cassi); Vendetta, Willow, Varg, Stellar and Ren lost as 4th (42-49% screen).
- 5th: Stellar 57.9% and Willow 52.8% over Cassi (216), level with each other (49.2%, 118); Varg 47.7%, Ren and
  Vendetta lost (42%, 39%).

### Camp awake state from striking members (2026-10-20)

- Monsters sleep one by one (`probe-sleep-range`), but `World` read a group's state from its first visible live
  member, often a cluster. Now the group is awake while any striking member reads awake and asleep only when every
  live striker is seen asleep. Against hecate-v6 (main ffc6b76 without it), real budget: 295/582 = 50.7% (ladder
  36/70, gen 259/512); out-of-fuel turns 1155 against 1152. Level; kept as a logical fix.
- Per-member sleep. `CampBelief::asleep` keeps the strikers read asleep while their group is awake; only damage
  wakes them, so one seen awake again clears the rest. Safety's camp members, `awake_over`, the dash and shield
  hazards, passing and capture-hold "free" hits, `landing_wakes` and `wake_risk` read members, not the group; an asleep
  member counts as a threat only while another champion is within 4 of the group. A blind quiet streak that starts by
  the round a member was woken needs 3 rounds. A traced packs game read a partly awake group on 44 turns.
  Against hecate-v7 (main 5a33e52): 291/582 = 50.0% (ladder 30/70, gen 261/512; flips vs the v7 mirror 5-10 and
  49-44); out-of-fuel turns 1125 against 1224. Level; kept.
- Waking sleeping groups onto enemies (`wake_camps`, never shipped): a damage or stun spell on a group whose asleep
  strikers then reach only enemies, valued by `hit_worth` on reach - distance (+1 once the enemy has acted) phases,
  or the rounds left in a tribute or capture hold. At turn end it fired in 17 of 582 games (25 wakes, almost all
  boss-battle's centre elks), 296/582 = 50.9% against the bot without it; a pre-walk version for walk-excluding
  spells (all of our draft's) when the wake beats `keep_walk_value` never fired, 285/582. Basic-attack wakes (on a
  harmless member, the only way out of reach) never fired. Too rare to measure. A visible enemy held in an asleep
  striker's reach is common locally, but those are mostly self-play recalls (above): ladder games showed 109 capture
  or tribute rounds in 70 games, the enemy usually 4-8 tiles from us. Not merged; its place is the strike search's wake
  pricing (`STRIKE-SEARCH.md`).

### Quality wave 1 (2026-10-21)

- Four behaviour-identical cleanups (world, safety, bot.cpp, comms/turn order/pathing) landed one at a time, each
  16/16 identical on the fuel bench; together total fuel -0.54% (p99 80391 -> 79827).
- Bundle of fixes and removals on top (main 07c414f): a shield read in its last round; diagonal crossing ties by row
  parity; a camp stirred only by champions yet to act, within 5; camp members cut to reach 0 dropped; submit_here
  judges an avoided altar; siege_load counts a cleared group as dead; offer_channel skips stun-immune tributes;
  live max health; step_closer keeps off the guard and the farm zone; warm_up's member fuel check left to
  prepare_member; `killable_now` and `fight`'s exclude removed; the delayed tribute stun removed. 282/582 = 48.5%
  (ladder 30/70, gen 252/512), out-of-fuel turns 1078 against 1147. Level; kept as fixes and level removals.

## koi: Fish's play on hecate (2026-10-19/20)

Against `baselines/hecate-v1`, 1010-1630 games (ladder, gen, central and fresh seeds 7101-7106); details in
[koi/LOG-attempt1.md](koi/LOG-attempt1.md) and [koi/LOG.md](koi/LOG.md).

- Level (52-54%, the same as hecate + latsize alone at 53.3%): Cassi and other damage-free stuns on any monster
  hitting an ally; a peel stun valued at the hurt ally's life; clusters first; spells from range only while an ally
  tanks; enemy-race and late-race banking; Fish's commit (no retreat at hp after burst 300+ and local ratio 1.5+);
  chasing any carrier; Fish's turn priority; the 150-gold shopping recall bag and all; lazy chaining to 5 gems a step;
  waiting in bushes; cycle horizons 70-140; openers when a melee crewmate arrives; elk crews by pick pairs (−1.2); a
  Monster emblem first on big-group maps; Fish's caster draft on Monolith-only and shared-gem maps; the late-race line
  at 850.
- Fish's build table: −5 to −6 alone (no Jungle: 16-50% more camp damage, more heal trips; caster-only −2); with
  Fish's camp-aggro priority (healthy empty-handed bodies act first) and 30% recall line −2.5; with its old-version
  table (Durability second, no Home) about −2. koi ships it for Fish-likeness, with a melee pre-hold step (a body
  steps onto a freed camp tile while the group still fights; level, freed-tile share 41% -> 52%) and Fish's engage as
  an advance (go for the weakest enemy within 6 where hp after burst is 300+ and local health 1.5x theirs; level,
  kills 2.4 -> 2.9 a game): 50.4% over 1986 games, nemesis 59.0, rival 66.7, morgana 74.9, aphelios 89.5.
- Lost: the fitted engage rule as the retreat/advance rule (33-35% on 390); crews by pick pairs (−4 to −10); solo
  range openers (−4.6); respawning groups worth 1.3x (−6); casters chipping Monoliths on mixed maps (never finished in
  time; those maps 33/78 -> 21/78); gold-free heal trips (−6).
- Who wins koi-vs-hecate: the first champion death (first to die wins 41%; no death in a third of games, koi 58%).
  Steals are about 28 gems a game each way: the games are farm races on each side's own groups.
- Found: a body could stand for 90 rounds in a dead-end pocket whose way out a live camp blocked (static fields ignore
  camps); a wider search fixes it (`Pathing::step_towards`), level overall.
- Attempt 3 (from the Fish-vs-hecate scrims; `tools/koi/killcard.py`): Fish converts engagements with less damage per
  kill (2.2k against 3.3k), mostly through its killers' Focus and health; bush and unseen kills are not distinctive.
  Level alone: Fish's targeting (kill, else lowest health; stuns on the biggest threat), a chasing caster stopping at
  nuke range in a bush (+2 on 390), retreating casters casting any ready spell, the step-in after an enemy acts, rush
  tributes late in a tight race. An enemy capture holder counted as a carrier: +1.7 on 1010. Funnelling captures to
  Stellar: −4 to −5. hecate's upkeep builds instead of Fish's table: +2. The final koi (those fight changes with
  hecate's builds): 54.0% over 1986 games (53.4% over 2698), nemesis 63.3, rival 73.6, morgana 74.9, aphelios 92.6
  against hecate-v1's 61.5, 69.0, 74.9, 90.3. Code: [koi/koi.patch](koi/koi.patch) against hecate 110e338.
- w2-small bundle (2026-10-21): the periodic ward deleted (off-bush wards every 20 rounds; WARDS.md proposal 1), the
  rally deleted (COORDINATION 2; nothing read it), and `possible` counting an unseen enemy's turn this round at once
  (WORLD-MODEL 3, a superset fix). 50.3% vs main (582, ladder 50.0, gen 50.4), out-of-fuel turns 983 vs 1116:
  level, kept.
- w2-chain (2026-10-21; WORLD-MODEL 2): an enemy with two turns before ours chained in threat_strike as the max over
  the first turn's slot S1 (or none) of A_S1(d) + B_rest(max(0, d - m)), m = 3 after a dash else 1, replacing
  max(walked, twice); Reach's ways tagged by turn and slot to match (Stellar at 3 tiles 200 -> 298). Strike bounded
  Reach on every tile asked (no REACH>STRIKE in 582 debug games). 47.1% vs main (582, ladder 52.9, gen 46.3),
  out-of-fuel turns 1219 vs 1016: worse, dropped.
- w2-altar (2026-10-21; COORDINATION 1): an altar is usable for a bag when a tribute tile is walkable from spawn with
  live camps as walls and the believed-awake camps' fire there over tribute_turns(bag) stays below the carrier's
  health; bankable_bag replaces my_gems() where a bag decides to bank, and while none is usable for the team's largest
  bag the groups sealing the altars are siege candidates (replacing CHANGES 27's gate). chase gives the turn back when
  it can neither step nor hit. 49.0% vs main (582, ladder 51.4 with boss-battle 2/2, gen 48.6): level, kept.
  Out-of-fuel turns 2145 vs 1004: +208 on rounds 1-2 (the first access build), ~800 on two maps
  (gen-clusters-only-720708305, gen-huge-shared-720707817) where a carrier stood still with a bankable bag 10 steps from
  an altar for 500 rounds and the farmer behind it spent 60-80k a turn in farm's step_towards/make_way retries. The
  stuck carrier is on main too (a 1481-round 'B' run on gen-dense-camps-720708102).
- q2 bundle (2026-10-21; quality wave 2 fixes): stale-turn guards in main.cpp and comms send, farm always evaluates
  (mini-farm fallback deleted), act errors still post claim/bag/health, one heal_rounds price for heal trips, Safety's
  camp hits scaled by our emblems, asleep groups stirred only within a yet-to-act champion's strike reach. 54.5% vs
  main (582, ladder 50.0, gen 55.1), fresh seed 9421 59.4% (512): kept. Out-of-fuel turns 1136 vs 914 (fresh 945 vs
  731), not broken down.
- q3 bundle (2026-10-21; quality wave 3 fixes, on main d372b00 after the wave's behaviour-identical changes landed
  16/16 identical): altar_access floods each camp death's pockets into `ours` at once instead of deferring them while
  an altar is open, and access_fire reads every open tribute tile instead of the first 64. 50.6% vs main (1094, ladder
  48.6, gen 51.4, fresh gen-s1 50.2): level, kept as fixes. Out-of-fuel turns 6276 vs 6106 (ladder+gen 3265 vs 3072,
  against the q2 bundle's 1136: strike search's decide).
- farm-s1 (2026-10-21; FARMING.md stage 1, shared prices): one heal_rounds, one HomeTrip price for every trip home
  (farm's bank trips, recall_to_bank, capture_recall, wants_shop: heal plus the next emblem once the gold completes
  it, no recall that arrives too late to tribute, nothing once closing), gems_share capped by the tribute rate and our
  pace over bag_rounds_left, gold priced by the emblem's saving (about 2x the old per_gold), closing absorbs endgame(),
  holders() for cleared groups; deletes gold_worth, endgame, emblem_gain_rounds and 3 params. upkeep_cost's clearing
  share counts from (camp_turns+1)/(turns+1): at 0 gold was worthless and stampede idled. 50.0% vs main (1094, ladder
  47.1, gen 51.0, fresh gen-s1 49.4): level, kept as the base for stage 2. Out-of-fuel turns 7156 vs 6606 (+8%, all
  decide, spread over maps); 100M bench mean fuel +0.4%, p99 +2.1%. Suspect: prices() keys on the float share, which
  moves every round once the time cap binds, rebuilding farm's group facts.
- strike-fuel (2026-10-21; landed as cc38946, f56b8c9 on main 55f8f6d): strike search fuel with the same choices
  (centre/touch scatter with hashed dedup, memos for wake, landing groups and first-mid, a per-tile viewer row cache,
  our record read once, landings read only foes within their radius). bench 16/16 identical at 100M on main 55f8f6d
  (fuel -0.08%). Worst maps at 100M (12 games): search fuel per call mean 11.75k -> 11.2k, p99 42.5k -> 39.3k, max
  204k -> 133k. Measurement A/B vs 55f8f6d: 51.5% of 1094 (ladder 54.3, gen 52.5, fresh gen-s1 50.0), level as
  expected; out-of-fuel turns 6139 vs 6545 (-6%; ladder 589 vs 633, gen 2699 vs 2728, fresh 2851 vs 3184). The rest
  is the search's tail: searches start with 40-60k left after step_guard; a capped branch gave no real-budget gain
  and was dropped (strike-notes.md).
- strike-fuel-2 (2026-10-21; landed as a850d48 on main afae02d): find_centres takes each point's 3x3 as a row mask
  less the centres already added (same order) and clears the whole near table when over 8 points would each clear
  around them. bench 16/16 identical at 100M on main 1264821 (total fuel -0.002%, p99 86736 -> 86620); big Ryth and
  Stellar searches' centres 8.2k -> 7.6k. Measurement A/B vs afae02d: 50.2% of 1094 (ladder 48.6, gen 50.0, fresh
  gen-s1 50.6), level; out-of-fuel turns 6900 vs 6865 (ladder 589 vs 609, gen 2898 vs 2917, fresh 3413 vs 3339):
  no real-budget gain. Profile (12 worst-map games at 100M): Heart of Ruin searches over 25k average 41k (read 10k,
  grow 20k, price 10k), but ~70k (p90 115k) is spent before the search: world 10k, decide start 12k, want_home 9.5k,
  step_guard 37k (fights 17k at ~10.7k a new fight, Reach exposure 9.5k, fight keys 1.8k). Tried, no gain, dropped:
  per-turn landing classes (regroups 3.6k -> 4.1k: the cost is each cell's first land_foes/land_touch), a heap for
  the price loop's selection (its cost is the strike-share order, ~500 an iteration, plus Reach queries at ~500-700
  on tiles step_guard never asked about). Left: step_guard's fight simulations and the read's per-foe loop (2.9k mean,
  4-6k on big searches; 1-2.7k of it attack_viewers on uncached tiles).
- w2-trapped (2026-10-21; WORLD-MODEL 1): Safety::trapped(p, h), every exit next turn (stay, step, a landing if our
  dash stays ready) taking the visible enemies' strike at p before our next turn plus their next strike at the exit,
  closer by their moves, plus camps, >= h (Chebyshev only); a want_home trigger, and step_guard guards trapped tiles.
  Screened well offline (fires on 3.0% / 1.2% of healthy in-sight turn-ends, catches 74% / 71% of point-of-no-return
  turns). 46.7% vs main (582, ladder 48.6, gen 46.5): worse, dropped. Out-of-fuel turns 1926 vs 1201 (350 vs 293
  games, spread over maps, not one blowup): step_guard asks it about up to 24 tiles a turn, ~3-4k each when trapped.
- w2-ward-early (2026-10-21; WARDS.md proposal 2): place_ward between comms receive and decide, then observe, so a
  ward's sight reaches this turn's strike and casts; the turn-end call kept. 49.5% vs main (582, ladder 55.7, gen
  48.6): level, dropped for fuel. Out-of-fuel turns 1487 vs 1154, all in decide (gen-huge-shared 158 vs 27): at turn
  start ward_bushes grows bush clusters down to small_cost_estimate + end_reserve, so decide starts nearly empty
  (ward-no-bushes-clusters shortcuts 1997 in REF, near 0 in CAND). Retry only with clusters already found (warm-up's
  find_all_bush_clusters) or the search moved after decide. Correction (gaps-ward-early-2's trace): this version placed
  no ward at turn start at all (all 39,946 calls refused: start_recall leaves us channelling into the next turn); turn
  start held at most 4.2k fuel, and the shortcuts were 1,122 vs 1,997, not near 0.
- gaps-ward-early-2 (2026-10-21; GAPS 2): the ward placed in decide right after continue_recall cancels the recall,
  from bush clusters already found only (bush_clusters_found; the turn-end call grows them); after a ward, observe,
  rebuild Safety (refresh() keeps the seen/unseen lists and cached strikes, so newly revealed enemies would stay
  modelled from turn-start beliefs) and invalidate Pathing's occupancy. 13 turn-start wards on 00ambush (main 0).
  50.7% vs main (1094, ladder 50.0, gen 48.0, fresh 53.5); out-of-fuel turns 10112 vs 10123. Level and sound: kept.
- gaps-stat-by-use (2026-10-21; GAPS.md, landed as 278a531): main stat from our counted basic attacks and casts
  (count_use at act()'s end) instead of the per-cooldown formula, which stays until both counts are non-zero; a begun
  emblem is finished in the stat it was begun in. Travel dashes count as landing casts, so Heart of Ruin flips to
  Focus. 56.4% vs main (1094, ladder 65.7, gen 54.7, fresh gen-s1 56.8): kept. Out-of-fuel turns 9427 vs 8471 (+11%;
  ladder 794 vs 752, gen 3860 vs 3602, fresh 4773 vs 4117), not broken down. Untried: count a landing only when it
  hits something (needs a hook at the cast site, strike-search owned).
- farm-s2 (2026-10-21; FARMING.md stage 2, one group value; branch orch/farm-s2 849239c, integrated as
  orch/int-farm-s2 6920ca8 on main 73c9b6e): crews from arrivals (fall_time), claimers dropped when they would leave at
  their recall line, a visible unclaimed partner with no radius, a heal price (camp_risk x damage, free on a recall
  home) in every cycle, one lexicographic (feasible, value) pick; deleted the risky, shared and help tiers,
  rally_radius and help_radius. 45.1% vs main (1094, ladder 54.3, gen 42.6, fresh gen-s1 46.3): worse, dropped.
  Without the heal term in the ranking (orch/int-farm-s2-noheal 543caed): 46.2% (ladder 60.0, gen 44.5, fresh 45.9),
  so the heal price is not the cause. Out-of-fuel turns 10842 vs 10523. Losses spread over most gen kinds (no blowup).
  ab_compare on gen: clears +3%, capture gems -6.7%, gold -10.6%, melee camp damage -19%, capture resets +12%: melee
  champions stop working big monster groups (the old help/shared joins), taking small groups instead. Ladder went the
  other way (tributed +15%).
- gaps-ward-churn (2026-10-21; GAPS 3, WARDS.md proposal 3; landed as c04907d): ward_bushes replaces our ward only
  by a cluster scoring strictly more than the warded one, a score being its tiles within ability_range of here plus
  within ability_range of the work tile (claimed group's centre, else the waited-at altar). On 6 games vs main afae02d:
  wards placed -20%, median bush ward life 21 -> 33 rounds, A-B-A swaps 252 vs 283 (claim and wait_altar alternate, so
  camp-altar-camp still swaps; a persistent work tile would be farm_group, farming-owned). 50.6% vs main 695b6aa (1094,
  ladder 51.4, gen 50.0, fresh gen-s1 51.2); out-of-fuel turns 10638 vs 10472. Level and sound: kept.
- final-clearing (2026-10-21; GAPS camp deaths; branch orch/final-clearing 93ac027, integrated as orch/int-final-clearing
  4b907ac on main 9f89878): most camp deaths with no enemy within 5 (ladder 107 of 146, gen 714 of 898; mostly Elk and
  Golem, half from full health) crossed the recall line, then took 3.6-4.9 more camp hits walking along the edge of the
  camp's reach: an Elk or Golem hits every tile in reach alike, so flee_camps' one-step damage tied and "closest to
  home" circled the camp. flee_camps now adds camp damage x the hits left before leaving every awake camp's reach
  (Safety::camp_area minus standable, walls ignored as in camp_exit_rounds; one search from here, one board test per
  step). 4 games 00elkring/00lanes vs 695b6aa: camp deaths 1 vs 7. 49.9% vs main (1094, ladder 47.1, gen 50.4, fresh
  gen-s1 49.8); out-of-fuel turns 11202 vs 11361. Level and a rule fix: kept. Not fixed: retreat_step walks back into
  an Elk's reach when the way home passes it (recall_outruns ignores camps; lanes), idle turns under a Golem
  (dense-camps).
- final-keepwalk (2026-10-21; GAPS derived thresholds; branch orch/final-keepwalk 06e74a6, integrated as
  orch/int-final-keepwalk 6db8557 on main 4cfb395): the step search priced a carrier's walk at carried_step_value 210
  (keep_walk_value 250 less a cast's 40), so a carrier cast a walk-blocking spell only above 250 and Stellar's nuke (140)
  never did; Intent::keep_walk was set but unread. A carrier's step is now farm_step_value (a step home banks a turn
  sooner, freeing a turn of farming); cast_at_enemies takes the forgone walk's worth (threshold min_value + walk) in
  place of a bool, and retreat and the game-ender intercept pass escape_step_value 210, so those paths keep 250 and
  free stun. Works against the earlier "ranged carriers hold fire to keep walking" loss (47.9%). 52.1% vs main (1094,
  ladder 51.4, gen 52.1, fresh gen-s1 52.1); out-of-fuel turns 11027 vs 11206. Kept.
- fight-fuel (2026-10-21; orch/fight-fuel 4e55a0a, not landed): fight simulation fuel. Profile at 100M, six worst
  maps vs main (decide >= 100k turns, 1103): decide 122k = step_guard 43k (new_fight 3.8 sims ~10k each, exposure 10k, Reach builds
  5k), want_home 27k (pursuit 7.8k), search 22.6k, prey 12k. A sim is ~26 half-turns at ~370 fuel each (~6 fighters;
  ends: won 46%, lost 32%, horizon 22%); fill and make_slot ~1.4k of it. Measured and dropped: a cross-turn fight
  memo by a hash of both sides (0.01 hits a big turn: cooldowns and health move every turn), keeping Reach::at answers
  across turns while its inputs and the enemy wards hold (no fuel change), quiet stretches through shields (no
  change). Kept on the branch: simulate() ends once their side cannot take us over the rest of the horizon (12-18% of
  sims). Identical at 100M (bench 16/16, worst maps 12/12, debug checks of early ends and memo hits clean) but level:
  worst maps -0.26% fuel, bench +0.08%; real budget bench OOF 95 vs 89, six worst-map games 404 vs 301 (noisy, not
  better). The per-turn fight memo and per-turn Reach builds already dedupe within a turn; the cost is the sims'
  per-half-turn work, which needs a cheaper act() rather than fewer duplicate calls.
- Final check (2026-10-21; main 4afef8c = ab47731's code, after keepwalk and quality). Against hecate-v8 (the
  session's first baseline): 63.4% of 1094 (95% CI 60.5-66.2; ladder 65.7 of 70, gen 62.3, fresh gen-s2 64.3);
  out-of-fuel turns 9223 in 743 games vs 1853 in 522. On gen-s1 alone 65.2% of 512 (61.0-69.2), out-of-fuel turns
  4786 vs 837. Against nemesis, both on their own drafts: 93.0% of 1606 (91.6-94.1; ladder 92.9, gen 94.1, gen-s1
  92.2, gen-s2 92.6); out-of-fuel turns 11516 in 1153 games vs 0. v8 stays (under the 80% bar).
- removals (2026-10-21; TODO candidates; branch orch/removals 3328bae on main a1efff2): two removals in
  cast_at_enemies (abilities.cpp enemy_cast). The free stun: an excludes-walking stun hitting every visible enemy
  able to reach us next turn needed only min_value 40, not min_value + walk; only retreat and the game-ender
  intercept pass a walk (escape_step_value 210), so it fired only there. Ground and landing casts at tracked unseen
  enemies: a target spread over `possible` when on at most max_unseen_tiles 9 tiles, which also kept areas and
  landings off an unseen Ren whose retaliation would kill us. The strike search's own unseen ground casts (plan.cpp
  add_unseen) stay. 49.2% vs main (1606, 95% CI 46.8-51.6; ladder 47.1, gen 46.7, fresh gen-s1 49.6, gen-s2 51.6);
  out-of-fuel turns 16157 vs 15948. Level: kept.
- wave 0 (2026-10-21; integration branch claude/dazzling-mccarthy-4kawix f25159f on main 55e0bdc): removals (above);
  the strike search's add_unseen now keeps only the tiles of an unseen enemy whose retaliation would kill us, as
  banned centres, so it no longer plans ground casts at unseen enemies that cast_at_enemies never makes (CHANGES 53);
  Phase markers (`debug_phases`, off by default). One run vs main, ladder + gen, debug builds, CAND with
  `debug_phases` on (`ab.py --phases`, ~0.8% more fuel to CAND only): 48.6% of 582 (95% CI 44.6-52.7; ladder 52.9 of
  70, gen 48.0 of 512); out-of-fuel turns 6198 in 418 games vs 5542 in 413 (+12%; how much of that is the phases'
  fuel is not separated). Level: kept. Where CAND's turns ran out: FUEL-GATES.md, "Out-of-fuel paths".
- wave 1 (2026-10-21; combat merge, [COMBAT-MERGE.md](hyperion/COMBAT-MERGE.md); integration branch
  claude/dazzling-mccarthy-4kawix 36cf487, tag w1, on w0 2b7ea7e): one tile table under one unseen rule, the fight
  memo across invalidate with pursuit/idle memos and reobserve, turn start and camp exit-rounds pricing, search pricing
  through the table with one shield_cap, one unseen-Ren ban for cast_at_enemies and the search (CHANGES 54). One run vs
  w0, ladder + gen, debug builds: 48.5% of 582 (95% CI 44.4-52.5; ladder 50.0 of 70, gen 48.2 of 512); out-of-fuel
  turns 5088 vs 5736 (-11%). Level (above ~47%): kept.
  - Diagnosis: 16 swing maps replayed as w0 mirrors; all 32 games first differ on a CAND move. The main source is
    W1-A's unseen rule in damage_bound: tile(p).worst() takes an unseen enemy from its field capped at unseen_radius
    instead of a full hit anywhere in full reach, an estimate rather than a bound that often reads 0 (TABLE-MISMATCH
    bound 39297 lines in 430 games, all downward). Its users shift: shield_cap drops Heart of Ruin shields a mirror
    cast (5 maps, 3 lost), a recall start became a walk, retreat tiles change. W2-E restores the bound. W1-C's exit
    rounds likely cut camp deaths 15% (443 vs 519), though gems lost to camps rose (881 vs 700). W1-B, W1-D and W1-F
    showed only fuel-shifted divergences. Champion deaths +3%, kills -2.9%, tributed gems -2%.
  - Fuel: W1-B alone was 16/16 identical at 100M but +1.05% a turn, a fixed ~+380 (likely the per-construction
    note_view() and memo bookkeeping, unmeasured) with savings up to 9k on memo hits. Real-budget bench vs w0: out-of-fuel
    turns 132 vs 149 (within its ±20), mean fuel +0.8%. The tile table's camp pre-filter was reverted (Fuel, above).
- wave 2 (2026-10-21; combat merge, [COMBAT-MERGE.md](hyperion/COMBAT-MERGE.md); integration branch
  claude/dazzling-mccarthy-4kawix a9db454, tag w2-merged, on w1 36cf487): one fight engine (engage, FightKey memo,
  dominance) and a lazy guarded() in place of step_guard (W2-A..D), damage_bound an upper bound again (W2-E), fuel-only
  F1/F2 (CHANGES 55). Logic A/B at 100M fuel vs w1 (replays/ab/w2-100M/summary.md): 52.4% of 582 (95% CI 48.3-56.4;
  ladder 47.1 of 70, gen 53.1 of 512). At the real budget it ran out of fuel more than w1: fuel fix below.
- wave 2 fuel fix (2026-10-21; branch w2/fuelfix on w2-merged a9db454; brief W2 fuel fix plus the W2 review's
  findings). Real-budget A/Bs below are ladder + gen (582), both bots with `--phases`.
  - Byte-identical at 100M against a9db454 (16/16, 0 FIGHT-EXIT, PREFILTER and DOMINANCE mismatches): the SIMS line,
    E5 (dead cost estimates), E4 (play_quiet), E1 (a Strength bound before outlives/overwhelmed), E2 (a sim ends once
    the rest of our side must outlive them), B6 (a sim reads the round at its fuel check and abandons a resumed
    turn): total fuel -0.47%, p99 -3.3%. L4, F1 (cut fights memoised for their own key only), F2 (the search asks
    guarded() of its pick alone, reopening tiles priced short against a banned pick) and P1A (a clean stand fight
    settles a pursuit in recall(); pursuers_standing() deleted) were each 16/16 identical at 100M too.
  - Logic: L1 prey's key adds the prey's escorts and keeps only the allies near both tiles; L2 the search's dist-3
    lethal ban; L3 want_home takes a cut fight as no answer; L4 stale checks after guarded()'s verdict and on the
    search's entry. A stale check before the search acts was dropped: resumed turns paid grow and price, then planned
    again, and cascades (an out-of-fuel turn after the same champion's in the round before) rose to 265 of 456.
  - The 16-game bench cannot judge out-of-fuel turns: an instrumented but otherwise identical w2-merged gave 244
    against 178, and 00contest alone swung 74 -> 336. Paired runs decide: on 32 games (bench maps + 8 ladder maps)
    the L1 tip and the fuel-only commits ran out 952 vs 918 times in the same games.
  - L1 as specified (the prey tile's row) built Reach for every threat near the prey: chase/prey/engage/tile went
    14 -> 68 on 32 bench games. Escorts are now the visible foes whose Strike reaches the prey's tile (strike_sum).
  - Dropped: P2 (prey "no worse than here", escorts included): settled 876 of ~7.8k prey asks at 100M, 37 of them
    fights the sim lost, and +0.09% fuel in identical games. P1B: once P1A settles clean stands, only 601 of 1390
    remaining stand+pursuers asks are clean (0.43). E3: falls-only sims 2 of 16.5k.
  - Results vs w2-merged: tip f14a8a5 (L1-L4, F1, F2, P1A) 50.0% (ladder 45.7, gen 50.6), out-of-fuel turns 7109 vs
    8137; + P4 (prey with neither walk nor attack left targets an enemy in reach, no fight) 51.0% (54.3, 50.6), 6339
    vs 7762; + B2 (prey starts at most one new fight a call) 62ffe96 50.9% (50.0, 51.0), 6349 vs 8278. 62ffe96 vs
    w1: 49.7% (51.4, 49.4), 5354 vs 4982 (+7.5%); P4 alone vs w1 49.1%, 5477 vs 4910. Kept: 62ffe96.
  - B1+B3 (three new fights a turn for prey and guarded(), past which guarded() bans exposed tiles; max_guard_asks
    6 -> 3) on 62ffe96: 50.7% vs w2-merged (5871 vs 7952), 49.8% vs w1 (5070 vs 4609, +10%). Pooled over both its
    out-of-fuel ratio to REF is 0.871 against 62ffe96's 0.883: level, and it restricts play. Dropped.
  - Still above w1: against it 62ffe96 runs out more in chase/prey (+380 turns), farm's guarded() walks (+200) and
    want_home (+70), and less in siege (-270); the search is level. Real-budget bench (default 8 maps / 8 more ladder
    maps): w1 132 / 236, w2-merged 178 / 587, 62ffe96 176 / 347; mean 35352, p99 85854 (w2-merged 35743, 86258).
  - Review fixes on 62ffe96 (a340ad9, 8859669): L3 dropped, as want_home branched on Trade::cut, which only a short fuel
    sets (a fuel gate; a cut reads lost again for every reader). P4's trigger moved from prey into chase: a tribute channel
    also clears walk and attack, so continue_tribute's prey skipped its fight and cancelled the tribute for any enemy in
    reach. In P4's state chase now takes the turn only with a hit, so carry_bag's dash away and act()'s contest/siege/farm
    go on. Real-budget bench (8 maps, `--phases`; oof_phases.py): 188 out-of-fuel turns (62ffe96 181, w2-merged 183, w1
    136), 18739 memo sims (16945, 17846, 12938), mean 35860 (35352). Within the bench's +-20: ambush, expanse and lanes
    are identical, and the diverged games move both ways (01hooks-b 10 -> 36, 01hooks-a 19 -> 10, 00contest-a 88 -> 72).
    Out-of-fuel turns under chase/prey 24 -> 16. Not A/B'd.
- raw-bindings port (2026-10-21; branch rawbind on w4-int 0856156): 3b2edbd's raw reads re-implemented on waves 1-4
  (CHANGES 58), plus camp_cast's camp reads (one record, raw stun) and Pathing's ally swap. Checked on a subset, not
  the full bench: bench.py at 100M vs hecate, both sides, 00interlock and gen-classic-720700000 on the own draft
  (Heart of Ruin, Marcella, Vesper, Ryth) and gen-city-720706900, gen-caves-720700400 on a forced
  varg,willow,ren,tavi,cassi draft. Replays 8/8 byte-identical, team stdout identical but for SRCH fuel figures.
  Total fuel -1.30% (own draft) and -1.82% (forced), -1.51% together; p99 -1.5% and -1.8%; 29949 of 29957 turns
  cheaper. The games ran dashes and landings (DASH/LANDING lines), Willow heals and Varg/Heart of Ruin shields (MEND h/s)
  and the strike search; cast_valued never fired in them.
  - Merged into INT (604ca30, tag w34) on w34-merged 55adef3: the same subset 4/4 and 4/4 identical against
    w34-merged; total fuel -1.26% (own draft) and -1.73% (forced), -1.47% together; p99 -1.5% and -1.8%; 27852 of
    27859 turns cheaper.
