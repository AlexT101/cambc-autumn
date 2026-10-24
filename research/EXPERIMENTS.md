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
  Out-of-fuel turns level. Dropped. If retried: a fight-survival term for Health in the emblem model, judged against
  v37 or on the ladder, not a stat fixed per champion.
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
  locally to measure; a logic call, not a measured one.

## Draft (2026-10-20, after the Heart of Ruin nerf)

Hecate vs hecate with only the draft changed, each pick on maps of its pick count ([hyperion/DRAFT.md](hyperion/DRAFT.md)).
These predate Khaos's Prism-specific play (CHANGES 82), whose draft starts with Prism.

- Heart of Ruin was the core (replacing it lost 12-48%); Marcella and Ryth were the best additions; Prism, Tavi and
  Willow lost in every slot of a trio. HoR/Stellar/Ren (a common ladder trio) lost 64-73% to the top three trios.
- 4th: Ryth 53-60% over Vesper or Cassi; Vendetta, Willow, Varg, Stellar and Ren lost as 4th. 5th: Stellar 57.9% and
  Willow 52.8% over Cassi, level with each other; Varg 47.7%, Ren and Vendetta lost.

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

## Fuel

Where fuel goes: [FUEL-PROFILE.md](hyperion/FUEL-PROFILE.md) (59% of out-of-fuel turns ran out in the strike search,
18% in farm; 44% are replays that run out again).

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

### Willow continuation on current main, 2026-10-23

Continue from unchanged `8be8eaa11fdfe6b63668be6235bf9364be2ce05c` (Hyperion source Git tree
`4e37607def220c27c5dc21c0159dd160581a4e35`), preserving CHANGES92–104 and106;105 remains reverted.
The old Willow/v41 source is exactly preserved upstream as `bots/baselines/v41` (Git tree
`b783f32ed1c1069eddbb1a80e5e9cb04e3626d25`, aggregate
`a2794129e115abb70faaa5a7e3c66b9728898b0e52c5542fa7885091eaec0bb6`). It is not the current main bot.
Fresh Pantheon history at16:40UTC uses P/V/M/Ryth-or-Vendetta/HoR, consistent with main's native
five-pick roster, without proving the uploaded source revision. CLI draft IDs use `champion_draft`
(Cassi/Issac one pick), not the native expanded `champion_type` enum.

Old-parent side experiments completed in the separate `willow-prism-development` checkout. They
remain frozen diagnostics and must not be relabelled as qualification against this new main:

- Willow affordable-prefix shopping `303aa2ac…` versus a279: published80 finishes40–40, native
  rollovers607/521; gen1023/512 finishes258–254, rollovers2374/2226. Zero runner/native/caught errors
  in both panels. Actual purchase/service trajectories differ, but no clear competitive gain is
  established. A lazy unused-quote variant `dcd00dda…` passes8/8 high-fuel replay-payload identity
  against303, costs+0.00842%, then scores39–41 and rollovers623/532 versus a279 at native fuel.
  Do not carry that optimization as a gain. The new Treasure/Bruiser model requires new evaluation.
- Vesper post-basic capture dash `4eea39fb…` versus a279: a same-puppet Cat pair matches through280;
  the child dashes onto the cleared group281 and receives the same reward287 versus289, followed by
  the same item purchase two rounds earlier. This verifies the mechanism, not general win rate.
  Its native published80 scores37–43, rollovers491/542, zero runner/native/caught errors. Preserve
  it for diagnosis rather than automatically adding it to the main Willow port. The first ec3
  source failed compilation on a private `engine` reader;4eea uses the proper raw SDK read.

The authorized next experiment is a coherent Willow support/controller port onto8be8eaa, with
five-pick P/V/M/Willow/HoR and unchanged main three/four-pick drafts. Retain all newer item, banking,
retreat, pathing and threat behavior. In particular the old credible-enemy broad phase must match
the new known teleport destination origin; copying old Safety would introduce a false negative.
Port only the reviewed support/recovery/mailbox, strict station/index, bank heal and compatible
optional Jungle Health logic. Exclude dropped global wake/gold-holder policy, the unused farm-heal
chooser, prefix shopping, lazy quote variant, Vesper capture dash and reverted travel teleports.
Source review and new baseline qualification are still pending. No new numbered bot or submission.

The coherent port is preserved as `1670a7e8ea2c11424ec9b6759dc0fa6af14115cc2842eb60f63a310b6c6b534b`
(`bots/variants/willow-upstream-coordinated-work`). Root's actual-delta review found no wholesale
replacement of newer main algorithms. Before runtime, root and Astra requested one bounded roster
presence specialization: skip Prism's added protected-work/shop quote when Willow was not drafted,
using type presence only so a dead or hidden partner still receives normal recovery cleanup. The
separate child `bots/variants/willow-upstream-presence-work` is
`db5b37d5e5c609c2c616d3a39c0f1eb7f5adebf401dcd1be8848e0eede237ab8`; its one-condition parent delta
is `b23a1a36f7140b0d8f342ed3f7592da03150cb2eacba4593af4ee3a5f15fa10c`. Root read this exact
delta and independently rehashed the child. This removes unnecessary no-partner work, not all
support overhead, and does not claim three/four-pick replay identity. Both original and child
source/checkpoint/full patches are preserved; canonical main and the new frozen baseline stay
`d8d3cc1da72aaf62eb65fc5de8402b9c3a98a8aade1fabeb5cd9841b3ff01e2c`.

Preservation has one explicit behavioral qualification: CHANGES97's generic retreat body remains,
but Willow's owned forced-escape path returns before it. That path can choose no move without a
stationary finishing attack. In the older303 Starfish loss, actor3's r724 reversal avoids a visible
enemy Prism's threat; the r725-727 aftermath instead nominates a missing camp finish. At r725 the
exported Wolf33/G14 has105 HP against Willow's70 Strength and ready-looking reset, but native
readiness, visibility and same-group wake consequences still need an exact pre-return probe.
The separate one-round diagnostic spec is preserved in the old worktree; no finishing policy or
claimed safe escape is inferred from the replay summary, and it is not bundled into this port.

Runtime preflight pins CLI3.0.5, engine1.0.3 and the40 published maps. A minimal opt-in runner
update passes exact `--cli` and `--release` through both build and run-batch while retaining the
runner's default behavior. Root reviewed the actual diff. First80 native games await final Astra
review; no build or result is claimed here. One already-downloaded current Procless loss is also
being extracted for separate own-view diagnosis; its uploaded source revision is unverified.

### Willow presence package against8be8eaa: first native80

Root and Astra passed the actual full port plus presence condition before runtime. Candidate
`db5b37d5…` versus frozen `d8d3cc1d…` completed the40 published maps, both sides, Release/default100k,
native drafts, CLI3.0.5/engine1.0.3, one nice19 worker: **43–37**, runner failures0, native bot-error
turns0/0, native fuel rollovers512/317. By pick count: three6–6/12 with20/18 rollovers; four7–9/16
with60/57; five30–22/52 with432/242. Only the five-pick candidate drafts Willow. This is a small
initial panel, not qualification or an isolated controller effect.

The separate stdout audit finds one candidate caught code5 (`invalid_argument`) at round696 in
`061-01elk-arena-12.repl26a`, candidate physicalA; reference0. The line has no actor identifier.
That stdout also has a rollover at695, but no causal or Willow attribution is established. Keep
this follow-up distinct from the zero native Bot Error counts. The replay archive is
`cfb585cc255a84315b0edd642136030fc532f3478078104ac61772880330a582`.

Within52 five-pick games, candidate/reference engine-stat per-game means: healing9676.75/0,
gold6923.52/6024.71, deaths4.79/7.10, collected gems1031.96/874.33 and scored836.06/692.21.
Correctly attributed event means: captures53.56/52.62, clears55.10/52.85 and tributes25.52/25.21.
These describe the paired games with different rosters, not independent causal estimates or
promised healing value. Increased native fuel cost is concentrated in five-pick play.

Root caught an event-summary attribution error: `t` is the actor's turn index, not its team.
The corrected v3 uses explicit capture team, actor `a`, death victim `v`, and clearing/waking `by`
looked up in the replay's champion roster. Event-kind totals match extractor counts, no supported
events remain unattributed, and derived deaths match engine deaths in every pick-count stratum.
Earlier bad summaries are preserved under `pre-…` filenames; do not reuse their recall/tribute/
death/clear totals. Canonical corrected JSON SHA:
`aac4f53620484fa0e875f2c9c31ab7b023fad7cde804ff4b9de9f3ff047cc948`.
Results SHA `52d982dcc9f2ea08715a9bdd4a9540ed66944e1f82829b30f9afed7c573b25fb`;
final panel pins SHA `0fdb2f2e3a5dd6681f99abf2220ea4d0ed1134fd753a5eac7aded8495b1e1d99`.
All files are under `replays/willow-upstream-presence-vs-8be8eaa/batch-run-01-release-published40/`.
Root authorized the unchanged sources on fixed gen1023/512 and gen-s1 seed1024/512 next, serially,
to complete1104. No fresh holdout, release number or submission is yet authorized by these results.

### Separate public loss: Pantheon versus procless, Lost World

The fresh CLI match-show response confirms PantheonA lost to proclessB on00lost_world in match
`32a2bf5f-cab7-4574-b183-f3920cf50942`; uploaded source/version remains absent. Raw/extracted evidence
is in the old worktree's `replays/public-procless-lost-world-20261023/`, including the separately
saved `match-cli-response.json` and metadata supplement. The original summary's first-tribute
labels were reversed only in Markdown: correctedA32/B174 matches the original structured JSON
and raw events; the original Markdown is preserved. Native statuses verify A18/B1 rollovers,
including AHoR4's363–375 interruption, with no native bot errors. No routine cause is identified.

Astra's eight-turn own-view review of APrism0 r286–293 narrows the218-gem death without treating
global hindsight as bot knowledge. At289, staying19,11 is already in visible Ryth's AoE reach;
the reversal19,12 additionally enters visible Marcella's direct spell reach. Holes and live camps
form a real pocket, so neither a safe recall nor a complete escape is established. At291 the
successful407-damage exclusive AoE, then35 basic, cannot kill/stun1700HP Marcella and legally
precludes walking. The useful question is the pre-cast choice; calling the absent later walk a
bug would be wrong. No ally is visibly available in these frames, and neither roster has Willow.
This motivates a bounded prospective escape/cast review, not an attributed current-source repair.
Detailed evidence and limits: `research/public-procless-lost-world-loss-review.md`.

### Willow presence package: fixed seed1023 and loss follow-up

The unchanged `db5b37d5…` candidate versus `d8d3cc1d…` completed the exact frozen seed1023
256-map pool, both sides, Release/default100k/native drafts: **263–249/512**, runner failures0,
native bot errors0/0 and caught action errors0/0. Three-pick81–79/160, four77–73/150 and
five105–97/202. Native fuel rollovers are2209/1532, so the modest result does not establish a
cost-free gain. Published plus this panel totals306–286/592; five-pick135–119/254. Seed1024 is
running serially with the same frozen sources and exact previous map hashes; no fresh holdout,
numbered release or submission has been made. The authoritative artifacts are under
`replays/willow-upstream-presence-vs-8be8eaa/batch-run-02-release-gen1023/`; results SHA is
`10fac11df1e916d2cbb13997506aed59d2b088f263b32bc2168955826ecbce74`. The pick-size helper is
limited to win/runner-error strata, not event attribution.

The published-panel loss review nominates two Elkring Willow sequences for actor-own export:
`012-00elkring-21`, actor8/B rounds665–673, and `011-00elkring-12`, actor3/A rounds305–313.
The former loses a385-gem bag after cancelling a long tribute and taking stationary/reversing
escape steps; the latter repeats the stay/reversal shape after banking without a bag. Neither
Willow has a native fuel rollover. Global rows do not establish an available safe escape, so
no comparator change is inferred yet. See `research/willow-upstream-published-loss-window-review.md`.
The older Starfish stationary-finish diagnostic remains source-only and blocked on independent
instrumentation review; it is not part of the tested candidate.

The second fixed generated pool, seed1024, completed **262–250/512**, with three91–85/176,
four81–83/164 and five90–82/172. Native rollovers1970/1331; runner failures and native bot errors
remain0/0. Its caught-action audit is candidate0/reference1: reference physicalA code5 at1782 in
`174-gen-donut-102405600-21.repl26a`. Results SHA:
`6480c68b7c548ec45bd6ca255ee42e33aedf9a69084d7956e98903e29d25f659`.

Combined published40 plus both frozen generated pools: **568–536/1104**, five-pick **225–201/426**.
Native rollovers4691/3180; caught code5 lines1/1; no runner failures or native bot errors. The
generated-only pick split attributes3070/1769 rollovers to five-pick games, versus293/288 in
three-pick and816/806 in four-pick. This is a roster-level cost difference, not a measured Willow
routine attribution. Root rehashed the unchanged candidate as `db5b37d5…` and verified remote main
still8be8eaa. The modest coherent result warrants an untouched256-map/both-sides holdout using
unused seed2026102318, after the two small actor-own exports. No numbered release yet.

The support cost review identifies a conditional per-enemy broadphase saving and a small duplicate
mate-view calculation, but no measured savings. Existing station/Reach caches already avoid many
apparent repeats; preserve refreshes and threat timing. See `research/willow-upstream-support-cost-review.md`.
The separate old Starfish v4 diagnostic now passes bounded source correction review and awaits
compiler validation; it still has no runtime evidence and is absent from the tested source.

### Khaos_v32 qualification and next Willow arm

Untouched seed2026102318 completes **257–255/512**, with three87–93/180, four76–80/156 and
five94–82/176. Runner failures, native bot errors and caught action errors are all0/0. Native
rollovers2044/1445, including1526/712 in five-pick games. Results SHA
`7fd621aed78de24f23ae2505a3b5365edc4ae119a1928d1f98181a551e27b097`; post-run pins are in
`replays/willow-upstream-presence-vs-8be8eaa/batch-run-04-release-fresh-2026102318/`.

Across all1616 games, the candidate is **825–791**, with **319–283/602** in five-pick games.
Native rollovers total6735/4625; caught errors1/1; no runner failures or native bot errors.
The overall holdout is essentially level, while the active five-pick roster has a modest positive
result on each of the four panels. This supports keeping the coherent Willow package as a
qualified alternate release, not claiming a large or universal gain. Fuel cost remains an explicit
weakness. Root authorized packaging the exact unchanged `db5b37d5…` as complete local Khaos_v32;
server submission and canonical integration are not yet claimed. Remote main remains8be8eaa.

Actor-own Elkring review now supplies a concrete next experiment: A309–313 stalls or reverses at
a visibly sleeping Elk boundary because the owned escape ranks any camp-free tile above a
sleeping-camp tile before considering home progress. A narrow stalled-escape transit fallback
will retain the normal comparator and safety elsewhere, require successful fresh asleep reads,
strict home progress, no modeled enemy hit/stun, and actual HP covering a bounded local camp-wake
bailout. Include non-progressing reversals so entry is not immediately undone. The B-side hidden
Elk does not establish the same opportunity and must remain unknown. No safe recall or continued
37-turn tribute is proved. The source-only experiment starts from db5b separately; no change to
the qualified release. Design/evidence: `research/willow-elkring-own-view-diagnosis.md`.

Release completed: Khaos_v32's29-file source clone and canonical `bots/hyperion/src` both rehash to
`db5b37d5…`. Its Release raw/injected WASM are byte-identical to the qualified candidate. The CLI
bundle has29 verified source members,222393 bytes, SHA
`46f92918e1745b9e12994b4ae58a326d4d7e2fea20ce089cf32c1d182630df5c`.
The authenticated `--team me` history resolves Pantheon (`547efb5b-57e5-4355-8501-3b331f506d62`)
across different opponents. One CLI submit succeeded as **server version43**, with note
`Khaos_v32 - Willow support on latest Hyperion`. Its reported222393 upload bytes match local bundle
size; remote payload identity is not claimed. Exact response and pre/post submission provenance
are in `provenance/Khaos_v32-release/`.

### v32 live exploration and Willow cost follow-up

One authorized five-game live unranked group against policy wonk finished **2–3**: losses on
Monolith, Swirl and Hooks; wins on Quadrants and Boss Battle. Group
`c3943bec-ee4d-4a9a-a468-71e269d08154` and its exact CLI request/responses are preserved in
`provenance/Khaos_v32-release/live-ur-policy-wonk/`. Download ZIP SHA is
`8c74d86cda5dbba99651dc7c80284b17ac7c01539710200d1bc7e799fe662f9f`.
These are live exploratory games, not frozen-source benchmark results: the CLI does not expose
the submitted source/version for either participant. v43 was the intended current submission.
Our five-pick draft includes Willow on Monolith, Quadrants and Boss Battle; four-pick Swirl/Hooks
do not include her. Replay extraction and actor-own-view diagnosis are next; no loss mechanism
or draft advantage is inferred from this small outcome split.

The four existing qualification panels' offline audit localizes five-pick rollovers by normalized
roster slot. Candidate/reference totals are5028/2723 over602 games; slot3 contributes2209/350,
or1859 of the2305 excess. Published extraction verifies slot3 as Willow versus Vendetta; the
generated panels remain explicitly slot-labeled pending champion decoding. These are interrupted
turn counts, not fuel totals or routine-level attribution. No new engine runs were used.
See `research/willow-upstream-five-pick-rollover-slots-20261023.md` and its pinned JSON.

The sleeping-camp transit child is source-only pending review. Root/Astra found that current
zero-health beliefs are not sufficient dead-member certificates because the existing health
reader conflates hidden/missing results. The repaired child rejects such members in alive
groups while still accepting freshly cleared groups. No production release changed.

### Sleeping-camp transit: focused mechanism and upstream refresh

Repaired source `de1c99aae1085f767a510c465e015cca50fbf979c0319f6037d70d554bd3d001`
compiled and completed two Release/default100k Elkring games against frozen8be8eaa. As A it
lost737–1034 at970; as B it lost319–1375 at760. Candidate/reference native rollovers1/0,
native bot errors0/0, caught action errors0/0. The candidate's sole rollover belongs to HoR,
not Willow. These two games are an activation check, not a performance estimate.

Separate debug games show two admitted transitions and successful moves at305–306 on A:
2,25→2,24→2,23. B has no transit activation. This confirms entry and continuation are executable;
debug is not a fuel-exact witness for Release. The previous A loss was583–1089 and B319–1375,
but a changed single deterministic outcome does not establish a competitive gain. Artifacts and
mode-separated audits: `replays/willow-upstream-sleep-transit-focused/`; final pins SHA
`aab7fd10e7a341ee144161ae3ed0ff7bda35795eadb6e23a9d20b383d8f4e1ad`.

Remote main then advanced to `eaee5986e7df268757a492eabc130518200f8f0a`, fetched without
changing canonical or frozen sources. Its audit107/108 includes threat-distance/timing, unavailable
allies, ward visibility, capture deadlines and other fixes. Next qualification will integrate the
qualified support package and reviewed transit onto that source first. The original v32 stays
frozen; the new integration is an unnumbered experiment until submittable.

A second authorized live group was queued once against Intercontinental Fish, group
`a8a24ba0-7d50-4761-aaf3-0ab5eb8b2533`, on the same five maps with reversed sides. Exact CLI
request/response and quota preflight are in `provenance/Khaos_v32-release/live-ur-intercontinental-fish/`.
Its opponent and submitted-source versions remain unpinned; this is separate exploratory evidence.

### Mate-view reuse: exact behavior, no measured saving

Source-only child `bafc493445ca013c6f6e11984631d9262d0b537f0f6af070e44df0ca1d872418`
reuses the mate's already-computed heal-view value. Against the same fixed hecate on eight maps,
both sides, parent db5b and child each completed 16 Release games with explicit 100M fuel. All 16
replay payload hashes match exactly; no game errors. Recorded fuel rises 3,044,894,192→3,044,906,613
(+12,421, +0.000408%); after-round-1 mean 37,178→37,179 and p99 90,403→90,403. No Willow-only
attribution is made. This does not demonstrate useful savings, so it is preserved but excluded
from the latest-main integration. Artifacts: `replays/willow-heal-view-reuse-100m/`; final pins SHA
`32cc083a5e0d1886704b3fc71549f240a1241dff4c8e91b6151f68fdeaee1da8`.
Root review caught a retry-indentation regression in the benchmark's new opt-in CLI/Release
options. Luna repaired it and verified the failed-match retry with a subprocess-free mock.
The completed benchmark had no failed games, so its results are unaffected; the pins retain the
script hashes from execution and after repair. No benchmark rerun was needed.

### Live policy wonk loss diagnosis

Actor-own review rules out a proposed Monolith recall/heal veto: Willow heals Prism at666,
then recalls with her heal on cooldown and only full-health Prism visible. Prism's later206-gem
death is a separate visible lethal-spell/nonlethal-exclusive-cast decision, needing branch/risk
confirmation after the new upstream integration. Opponent Willow's Monolith heal position is
inside camp range with closer allies tanking; it demonstrates a useful service geometry, not
guaranteed future tank protection. A safe-ring ally rendezvous and independent one-step ready
heals merit bounded design before relaxing camp exposure. See
`research/willow-policy-wonk-monolith-own-view-diagnosis.md`.

Swirl/Hooks begin with higher realized capture income for us, but later deaths and fewer
productive cycles dominate. Our paid capture gems75/154 trail the opponent's1080/1034; simply
banking the remaining bags cannot close those gaps. Own-view HoR sequences distinguish actual
stuns from idle turns and newly revealed opponents from hindsight. Swirl has real allied follow-up;
Hooks' re-entry after retreat merits a branch/routing witness. No generic no-follow-up penalty or
forced unsafe capture is inferred. See `research/policy-wonk-four-pick-loss-review.md`.

### Latest-main integration: first native panel

The source-only integration `c71fc5730dc64f0463faea9c2edd6ef3a849332b86e5264ae4720c223b482d83`
combines the qualified support package and reviewed sleeping-camp transit with upstream
`eaee5986e7df268757a492eabc130518200f8f0a`. Against its frozen source aggregate
`a97aeefdf861fa71e26bf9908e7cb26eeb326b95cf3ef50b58cd62b810aed925`, the same published40
map panel (both sides, Release/default100k, native drafts) finishes **37–43**. Pick strata are
3-pick6–6, 4-pick8–8, and 5-pick23–29. Native rollovers are587/366, with zero native bot
errors and zero runner failures. Caught action-error lines are17/17, all code97
(`api_not_in_vision`); these are not actor-attributed. Both source aggregates remain pinned.
This small panel warrants diagnosis and the first fixed generated512, not release or rejection.
Results: `replays/willow-audit-transit-vs-eaee598/batch-run-01-release-published40/`.

Root review found double-escaped raw regexes in the new turn-order-marker audit. Its initial
zero-marker result is invalid pending a repaired positive-case check and offline rescan;
match outcomes and the independent native/caught-action audits are unaffected. Preserve the
initial report and provenance rather than silently replacing them. No match rerun is needed.
The repaired parser now has positive/negative checks, and the offline rescan confirms zero
turn-order markers on both sides. Astra also caught actor IDs being mislabeled as champion
types in the initial optional fuel breakdown. Luna rebuilt that mapping from each replay's
actual champion rows; team totals, map pick counts and wins are unchanged. Invalid originals
remain beside `summary-corrected.md`, `pick-strata-corrected.json` and
`setup-after-batch-run-01-corrected.json` (SHA `4ae344d6…`). Use those corrected artifacts.

### Live Fish exploration and Monolith comparison

The authorized Fish group finished **4–1**: Monolith391–1054 lost; Swirl1065–333,
Quadrants1012–854, Boss Battle1146–0, and Hooks1001–66 won. Live sources remain unverified.
All five extractions pass hard validation; native rollovers31/0 and native bot errors0/0.
Our five available stdout files have no caught action-error markers; opponent stdout is absent.
See `replays/Khaos_v32-live-UR/intercontinental-fish/analysis-final/` and its summary/pins.

Fish's Monolith draft is Vesper/Vendetta/HoR/Cassi&Issac/Ryth: five picks, six bodies, no healer.
Both Monolith captures supply512 gems; outside those objectives our captured gems674 exceed
Fish's553. Our Prism never dies and retains261 gems at the finish; banking that bag alone
would still not win. This differs from policy wonk's visible lethal-burst loss. Three short
actor-own windows are approved to check a possible Willow heal opportunity, Prism's late
known-information choices, and Fish's second Monolith clear. No draft exception or forced
late bank is inferred from final scores. Preliminary evidence is recorded in
`research/willow-fish-monolith-loss-review.md`, with own-view conclusions explicitly pending.

### Independent Willow ready heal: reviewed source, runtime pending

Separate child `bots/variants/willow-audit-ready-heal-work/src` has aggregate
`06b266efc20e36955c22ea9db743e1a71ea9ab9eb82463825f8284f0af33f68f` on frozen c71fc.
Root and Astra read the actual109-line bot.cpp addition and caller seams with no source blocker.
It reuses existing economy and mate-eligibility outputs, preserving the eligible-Prism path.
On an ordinary quiet turn without an eligible mate, Willow can take one strictly safe step to
heal another visible ally. Present gain must exceed three camp basics; immediate resource
finishes and capture/bank/shop/escape remain protected. A useful ally healable on the current
tile declines the step, including visibility supplied by Willow's ward. Successful movement
refreshes observations, uses the real healing action and owns the remainder of the turn.
No new claim, promised heal, formation timer or fuel gate is added. Runtime is still pending;
the published/gen integration panels use c71fc and say nothing about this child.
See `research/willow-audit-ready-heal-source-checkpoint.md` and its source-review note.

The approved Fish own view strengthens the r415 opportunity: Willow has a ready heal and sees
Marcella missing224 HP, with no visible enemy or Prism. Actual Strength70 gives a three-basic
price210. Reaching healing range delays entering the small cleared camp by two turns, not one;
the exact source admission remains to be checked at runtime. Fish's later Monolith clear instead
shows Vesper's465-Strength sustained attacks with a closer visible HoR tank. It supports reviewing
objective crew coordination, not forcing a late Prism bank or assuming unseen enemy knowledge.

### New live-ally stun query: bounded visibility repair

Source inspection finds that `World::observe` skips same-round allies already read, while
upstream's new fighter construction uses that cached `visible` bit to make a live buff query.
Walking out of sight can therefore make the query throw97 even after observation. This is a
provable source mismatch; the saved17/17 exceptions have not all been attributed to it.
Source-only child `bots/variants/willow-audit-live-ally-work/src`, aggregate
`ee1b404d8e50bc188c092739142d6a1f5bcf078756f643588d2693ccf94c7b10`, adds a9-line safety.cpp
repair to ready-heal06b266. The same single buff import returns unknown on97 before reading
its output buffer, while other error codes propagate. Unknown or positive pending stun delays
the ally one turn; known absent/expired stun preserves immediate eligibility. Teleport and
stun-immune paths remain unchanged. No eager World scan, extra SDK call or fuel gate is added.
Root/Astra actual reviews pass; focused build/runtime is next after the active frozen gen panel.

### Audit-era follow-up results and upstream108 revert

Frozen c71fc versus a97ae completes fixed gen1023 **263–249/512**, strata3p79–81,
4p76–74, 5p108–94. Native rollovers2214/1346, native bot errors0/0, runner errors0;
caught97 lines30/20 and turn-order markers0/0. The published+gen592 aggregate is300–292,
including5p131–123. This qualifies neither a different source nor the still-unrun second gen
panel. Results SHA `f17139cfc0b4c71af5b49b5ecd9f2567e974e44d84462e3ea4b616afcb8f90eb`;
artifacts and setup-after are under `replays/willow-audit-transit-vs-eaee598/`.

The ee1b ready-heal/visibility bundle compiles and completes four Release/default-fuel focused
games: Monolith versus c71fc1–1, LostWorld versus a97ae1–1. Candidate native rollovers1+6,
reference0+8; no runner/native bot errors. No candidate caught errors; LostWorld reference has
two97 lines. Two separate Debug Monolith games complete1–1 with a positive new helper event:
Willow actor8/B at199 cancels a recall, steps34,21→35,22 and heals visible HoR240 HP.
Debug and Release own-view windows both confirm the action and resulting1000 HP; their replay
payload SHA is identical `93903c1226015f2b0ff03ffefb8b2eee9d5411a77b46688c2c9b5258200b3948`.
This payload equality supports behavior for that pair, not Debug/Release fuel equality. Root
rejected an earlier claim that structural timeline parity alone proved state parity; the repaired
record separates that limited check from actual payload and bounded own-view equality. Use
`replays/willow-audit-live-ally-focused/focused-summary-corrected-v2.json` and its sidecars.

The same ee1b source then completes the published80 versus a97ae **39–41**, native
rollovers653/376, native bot errors0/0, runner errors0. Candidate caught errors0 versus23
reference97 lines in12 matches; turn-order markers0/0. This supports the narrow visibility
repair and leaves broad competitive qualification open. Results SHA
`992e1ef365c9c740981383ad409c009c7c8f2b0c1cef6c8549ea13f39573b9dc`;
full pins are in `replays/willow-audit-live-ally-vs-eaee598/setup-after.json`.

Before generated follow-up, origin/main advances to `b7bfcb7`, reverting CHANGES108 while
Alex investigates a ladder deficit. CHANGES107 and its live-ally stun query remain. Freeze all
completed sources/results; integrate that exact revert into a separate source child retaining
our support/transit/ready-heal/visibility repair, and compare against a newly frozen main.
Canonical v32 and server43 remain unchanged. The separate local Monolith crew design is not
part of this integration; its timing must account for allies that already acted so the tank does
not abandon merely because the ranged partner spent its current attack.

### Main107 integration: source approved, qualification running

New frozen child `bots/variants/willow-audit107-ready-heal-work/src`, aggregate
`a00fff454c1e48520968c9ba2d4c1ecdae0212ce019724dc06a6e959ddc3412e`, applies the exact
eaee598-to-b7bfcb7 upstream revert to ee1b, with four added support call sites adapted to the
restored hold signature. Root and Astra read the actual complete parent delta and decide/safety
seams; no integration blocker remains. Support, transit, independent ready healing and the
optional97 buff-query repair are preserved. No Monolith or item policy is included.
The comparator is frozen b7bfcb7 source, aggregate
`d6bac05921106e332ee4648b5034e748c65aff111cef3f5110d503bedcf1834a`.
Luna is authorized to run the published80 and both fixed512 generated panels serially at
Release/default fuel, one worker. Prior source results do not transfer to this candidate.

The separate local Monolith experiment is authorized from the same frozen parent, following
`research/willow-local-monolith-crew-design.md` (SHA
`61f2c432b9b744cc760e95d254b3fca04a7fa49b9dd97bc11c601ad1bc0babcf`). It compares a
nearby certified crew against ordinary farming, preserves the existing sealing/Monolith-only
path, uses bounded fresh member records and current-health exit reserves, and accounts for
acted allies using first-attack delays rather than deleting their sustained damage. This is an
opportunistic local basic-attack arm, not remote assembly or a claim that the historical losses
would reverse. Implementation and qualification are still pending. Willow service analysis
continues separately; no map-specific draft exception follows from the two live losses.

New107 candidate a00fff completes published80 **40–40**, native rollovers531/302,
native bot errors0/0 and runner errors0. Caught action errors are candidate0/reference10
code97 lines; turn-order markers0/0. Fixed gen1023 then completes **265–247/512**,
strata3p80–80,4p80–70,5p105–97. Native rollovers2522/1638 (5p1991/1117), native bot
errors0/0, runner errors0 and turn-order markers0/0. Results SHA
`2d484f69c891edd8799afff172ff9e3dbc413ace3684cce689f12c8417007543`; all artifacts are in
`replays/willow-audit107-ready-heal-vs-b7bfcb7/`. The second fixed generated panel is running.

Gen1023 caught errors are candidate2 code5 versus reference44 code97. Candidate witnesses are
game038/gen-blob-102306208 physicalB r701 (replay archive
`ed2024b3307baf0d8d2e64fed6154d282e30fe3b6e76c9bd994f665aab84abac`) and
game475/mut-elk-arena-102303400 physicalA r1008. Both say invalid metadata/alignment/overlap/
argument, without an actor or API call site. This error category occurred in earlier db5b and
8be8eaa panels too; that does not prove these instances have the same cause. Preserve exact
Release evidence and run two bounded Debug reproductions after qualification/recipient views.
Do not equate caught exceptions with native Bot Error statuses or silently suppress code5.

Willow follow-up review confirms that healing already ranks all visible allies. The fixed Prism
relationship restricts formation/recovery, not all-ally heal selection. A recipient's short
rendezvous may avoid moving Willow, but must pay actual lost melee/exclusive-cast work and be
survivable without an unreceived heal. Two recipient-own windows are pending; no mailbox
extension or recipient policy is authorized yet. See
`research/willow-nonprism-support-rendezvous-review.md`.

Fixed gen1024 completes **264–248/512**, strata3p85–91,4p88–76,5p91–81.
Native rollovers2230/1466, native bot errors0/0, runner errors0 and turn-order markers0/0.
Candidate caught errors0; reference32 code97 plus3 code5. Results SHA
`b0d77ae7ec8a0924715adea0b0c975b4e54624a2124dfcf26cb156df140187ab`.
The completed1104 comparison is **569–535**, native rollovers5283/3406, candidate caught
errors2 code5 versus reference86 code97 and3 code5. This is modest support, with a continuing
fuel cost. Root checked the actual gen1024 audit to correct a compressed agent prose report;
the underlying audit has the right32/3 counts. Published results SHA is
`c4459a1be8554c55056d943db6a83f2cc4d85241c0cfa8507291dc1476323f7f`.

Two recipient views are now exported under the live Fish/policy-wonk actor-window folders,
with source identity explicitly unverified. Their pins are in
`replays/Khaos_v32-live-UR/recipient-followup-actor-window-pins.json`. Two unchanged-source
Debug code5 reproductions are authorized next. After those, compare frozen a00fff directly
against deployed db5b on unused generated seed2026102341 (256 maps, both sides), retaining
Release/default-fuel qualification and exact provenance. No v33 preparation/upload yet.

The isolated four-pick P/V/M/W arm is authorized for source preparation from a00fff, with
gameplay and all other draft sizes unchanged. Use native drafts: test-draft mode overrides
the lineup and cannot test this comparison. No map/counterpick selector is authorized.

### Willow follow-up: recipient evidence and bounded side work

The two unchanged-source Debug reproductions do not reproduce candidate code5, but they also
do not reproduce the Release trajectories. Blob diverges on the first decoded action; Elk has
252 identical event rows before diverging at round10. Both reference wins are diagnostics,
not new competitive observations or a code5 fix. Preserve the original Release witnesses.
The comparison record is `debug-code5-diagnostic/release-debug-comparison.json` beneath the
main107 replay folder, SHA `712da25d2c80e7e8001bebde481fd08ad180e2a13bcbb2bda77b3dcaa9ca9cfc`.
Fresh512 against deployed db5b is now running on the pinned unused seed2026102341.

Recipient-own views do not justify a new addressed mailbox or non-Prism formation policy.
Fish Marcella415 can see ready Willow, but a return step costs the next turn's basic or
exclusive spell; current health and remaining camp work do not establish added useful
activity from the224 heal. Policy-wonk Marcella794 already receives the actual360 heal;
moving her for a hypothetical safe-ring Willow would not repair a missed service in that
history. Retain the separate Willow-side ready-heal change. Final recipient review SHA is
`c712fac099685e143ed30933c63d0025ac95027ab32005a028f82beac32d48fd`.

Root and Astra approve the isolated native four-pick source, aggregate
`157f5f79cddb45424ff2c25ce707e705d315c324267c5587a3f7b711f06ab06b`, for subsequent
comparison against exact a00fff. Only the fourth native four-pick choice becomes Willow;
first three picks, gameplay and three-/five-pick choices remain unchanged. The full source
patch SHA is `2a2d11dc1dbe98504da248dfcbd1a5eceede55c4acdbc3b32f14de66e26366f3`.
No runtime result yet. Map geometry can later explain service access and lost frontline
value; no named-map or enemy-Tavi selector follows from the two live losses. Current draft
order is cached on its first call, so reacting to later revealed enemy picks would require
an explicit draft change. Simultaneous picks remain unknown.

The separate Monolith crew source was held after actual review of bbd869. The four repairs
address outside-group damage on cleared capture tiles, current vision before trusting raw
group clearance, contributors with an explicit conflicting claim, and empty-handed winning
capture travel/tribute pricing. Corrected source56f17fe is now under final review; it remains
uncompiled and separate from both the release candidate and four-pick Willow study.

Fresh seed2026102341 completes **251–261/512 against deployed db5b**, native rollovers
2403/2286, native bot errors0/0, caught action errors0/0, runner errors0 and turn-order
markers0/0. Map-index draft-size strata are3p77–85/162,4p80–78/158,5p94–98/192;
their rollovers are523/536,289/304,1591/1446 respectively. These are map-size strata,
not champion-event attribution. Results SHA
`45dec6c0f08024723f093d88c92a5a3861ebdfdd6467f3bddaf37bb05d36d76d`, native audit SHA
`8d1ec74f0f05c09209a7749400bab952f6a0b56208b4905d4dac2e7a3d16ec16` in
`replays/willow-audit107-vs-db5b-heldout-2026102341/batch-run-01-release-seed2026102341/`.
The preserved invalid first setup draft omitted the `src/` prefix from the aggregate recipe;
it was corrected before launch without changing source/maps. See the adjacent correction
note and authoritative pre-run setup SHA
`6c0ceb8b8eb746036cf360464a77d1e7ac672467c2fab3cc03c1f40da3ef4620`.

Root accepts a00fff for Khaos_v33 preparation as a logical repair with near-level direct
results, not demonstrated win-rate superiority. The1104 upstream comparison and512 deployed
comparison have different opponents and must remain separate. Preserve the two unresolved
Releasecode5 witnesses; their failed Debug reproduction does not close them. The fresh batch
has117 additional rollovers, concentrated in five-pick play. Only source-identical clone/build/
bundle preparation is authorized now; no four-pick or Monolith experiment enters this release.

Root and Astra also approve Monolith56f17fe for later bounded runtime. Separate repair review
SHA `0dcf42eeb01a9083b8d4edfed7a81012a2321018a403d0bc1d008e91960b1f1b`; no source
blocker remains, but activation, fuel and actual outcomes remain unmeasured. Four-pick Willow
is the next main experiment.

The published80 actual-roster audit initially mislabeled candidate drafts on physicalB by
using a bot index as a physical-team index. Root caught the impossible half-Willow result
against the fixed source selector. Preserve the superseded report and correction note;
authoritative `actual-draft-strata-v3.json` SHA
`b5eb07c91e0ceb32ed2c7667977f4a621a01c06139504ba09b3ac59372aca1b7` validates both
physical mappings against result order for all80 replays. Actual candidate lineups are
3pP/V/HoR in12 games,4pP/V/M/HoR in16, and5pP/V/M/W/HoR in all52. Published wins by
size are6–6,5–11,29–23; the total40–40 never changed. Native rollovers by size are26/32,
42/44,463/226. Thus all1104 five-pick cells total225–201/426, combining actual published
draft size with generated map-index size; this is not an actor-level service measurement.

The native four-pick comparison is authorized after v33 package preparation: exact157f5
versus a00fff, published16 then generated150+164 four-pick cells,330 games total, both sides,
Release/default100k, one worker. Verify actual candidateP/V/M/W and referenceP/V/M/HoR
through physical-team mapping. No map selector, item/micro change or Monolith policy is
included. The API's503/429 responses to read-only team-history refreshes do not interrupt
local work; submission will be a separate single attempt once the package check completes.

### Khaos_v33 / server44 submitted

Root submitted the unchanged qualified a00fff source once at2026-10-23T15:59:25-0400, note
`Khaos_v33 - Willow ready healing and retreat repairs`. The CLI confirmed server44 and225939
uploaded bytes. Local ZIP SHA is `787423a8a652e3e75cb1724d4bad529ef4f2a998600f3b924248ebf7e4093bf2`;
receipt SHA `86dac718004151395933bf56b7927759d21b77b803712ccf85a2436a123b890b` is in
`provenance/Khaos_v33-release/submit-response.txt`. Remote payload was not downloaded, so
matching byte count is not a remote hash claim. This is the same authenticated session and
Pantheon deployment target confirmed forv32; fresh read-only history verification returned
503/429, so no fresh team-identity verification is asserted.

The29-file release clone and canonical Hyperion exactly match tested a00fff. Release rawWASM
`f1e94a1e5c5c45c9907ef1e237c88e079157aa153fdbf116516627c31e85ebb7` and injectedWASM
`4fcd9435b5f77abcc42576baa1533dbc8b681bd720632adae160df9792bf1792` match the qualified
candidate byte-for-byte and the completed fresh batch's artifact pins. All29 archived source
members match the clone. Current branch merges b7bfcb7 with source-exact reconciliation;
CHANGES entries109/110 distinguish Willow work from upstream107 and reverted108.

### Native four-pick Willow:136–194/330, diagnose rather than deploy

Frozen157f5 versus exact a00fff changes only P/V/M/HoR to P/V/M/W on four-pick maps.
Published16 is8–8, gen1023's150 is70–80, gen1024's164 is58–106: **136–194/330**.
Native rollovers are36/47,475/312,436/422 (947/781 combined). Every panel has zero runner,
native bot, caught action and turn-order errors. Actual replay rosters validate all660
physical-team rows against result order, with the intended candidate/reference lineups.
Panel summary SHA `01dd35ea68ffe5ba8e33aca7053d621ca81b883d2f7b21aa7f2fc3ff957571b3`
is in `replays/willow-four-pick-157f5-vs-a00fff/panel-summary.json`. No fresh confirmation
or numbered release is warranted for this universal HoR replacement. Five-pick Willow
alongside HoR remains in v33. Preserve this source as the diagnosed experimental arm.

Hooks2–0 and Rows0–2 nominate contrasting mechanisms, not a named-map selector. In both
Rows games there is no champion combat or death. Candidate team collection roughly matches
the reference, but Prism's578/566 bags complete conversion after the opponent wins. Prism
already began its long tribute before its own public-score-plus-bag first met1000; this is
not refusal to bank an already-winning bag. A15-turn post-capture standing interval in
RowsA deserves an own-view check, but even removing those15 turns would not by itself erase
the25-turn scheduled-finish gap. Do not replace the completion estimate with total capture
rate that assumes this carrier keeps farming while it travels/channels.

All four diagnostic games' first two Willow heals go to Marcella. HooksB's r32 heal360 is
followed by Willow's stationary basic and Marcella's continuing work/clear37/capture43.
This supports current multi-recipient service; it does not establish a missing permanent
Marcella pairing. Source review leaves any dynamic workmate or draft selector as a future
hypothesis. Luna is exporting only RowsA Prism1155–1161 and HooksB Willow30–37, then running
the already-approved Monolith56f17 Debug/Release paired diagnostic, four games total.

### Narrow follow-up: own views and Monolith non-activation

The two actor-own exports are complete. Rows Prism0/A1155–1161 confirms940/1000HP,
578gems, no visible Willow or enemy, and no rejected move; its repeated fresh recall is
the ordinary end-turn fallback, not evidence of an intended completed recall. The move
to20,4 succeeds1159. The proposed retained-bag deadline omission is **not present**:
farm's `too_late` separately reads the altar distance even while retaining gems. A bounded
branch witness remains necessary to distinguish remembered work, partial evaluation and
other no-work branches. No gameplay fix follows from this view alone. Hooks Willow7/B32
knows Marcella480/1200HP and heals360 while preserving her55basic; reset is cooling down.
This validates useful existing service, but not a counterfactual prevented death or recall.
Final own-view review SHA is
`c86ae40aabaa32b124749a9313c6dbb10fcd22438aa3e03ec6059a32267728f8`.

Monolith56f17 versus a00fff completed one physical-order pair each in Debug and Release,
default100k fuel. Both pairs are1–1 at1112rounds per game, with zero native rollovers,
runner errors, native bot errors, caught action errors and turn-order issues. All five
Debug nominations reject admission; none selects crew work. Extracted events show no
Monolith-group0/1 activity in any of the four games. This is **non-activation**, not
qualification or evidence of improved boss control. Debug outcomes do not establish
Release branch parity. Detailed artifact:
`replays/willow-local-monolith-crew-vs-a00fff/diagnostic-summary.json`, SHA
`48cd59bd1fe62ef721f473aea4174ad36880e2e150a0fafbb7b7c3a3abe343de`.

Source review identifies a conditional startup barrier: two necessary contributors that
retain different explicit farm claims cannot certify or publish the boss claim. Unclaimed
workers, a solo-capable anchor, an existing boss claim or a damaged boss can still admit.
The full-clear current-health reserve and fixed-station member coverage can independently
reject work. A bounded diagnostic will identify the actual rejection before any policy
change; removing the claim filter alone is not an established remedy.

### Rows branch witness and next Willow formation experiment

Bounded Debug traces now reproduce the original four-pick Release RowsA extracted actions.
The detailed reason run matches all30132 chronological event rows. At1158 Prism has evaluated
all9 groups without a ranked option: group0 exceeds the wait limit;1/3/5/8 fail the solo
deadline;4/7 fail crew remaining-health eligibility;6 is the excluded mixed Monolith. Group2
is known respawning until1171, with a visible ally claim,12 travel steps and1 arrival wait.
Its shared clear estimate is4.607rounds and value0.406786, but `too_late` rejects it. At1159,
arrival wait becomes0, the deadline admits it and Prism walks toward it. Retention remains
true in both turns. This establishes the no-ranked-work/deadline seam; it does not establish
that arbitrary early tribute, retaining a stale farm target, or weakening the deadline wins.
The interpretation/proposal remains separate from Willow. Evidence and corrected diagnostic
parent pins are in `replays/willow-four-pick-debug-trace/rows-A-reason/`; the initially wrong
setup-parent hash is preserved with its correction note. These are extracted-event matches,
not an assertion that Debug and Release spend identical fuel.

Root and Astra approve the isolated forecast-formation source
`0e989629893b451a0c164cac5757cf8b41eb1b2be36ef2766d1afc26a8bdfb59`
for runtime. Only an already-selected, zero-current-gain Willow formation move may change:
it can establish next-phase heal access to a currently visible, already-acted worker taking
conditional camp damage. Current output/heals, strict station safety, original formation
expiry, claims and draft stay unchanged. The forecast supplies value only; it never lends
HP or assumes a future heal. Shield-capable recipients are excluded because cached ally
shield0 does not prove absence. Source is94 insertions/1 deletion inbot.cpp from exacta00fff;
patch SHA `b2ae65a1587925ac5cdf40c552add256b2b555052870f9700f895573ea146ef7`.
Independent actual review SHA
`60185755509ea12bb75fd8a349110b1bb5cb9193f5d89f2dc64caa2f90e77486`.
Debug native five-pick activation comes first; no activation means no broad competitive
claim. With useful activation, the next panel is published80 at Release/default fuel.

New upstream7a5d178 reapplies108 throughcafb6f5. Its Hyperion source tree is exactly the
previous eaee598 tree, so this is a known source revision restored, not newly discovered
gameplay. Our existing frozen ee1b ready-heal bundle is the corresponding integration;
its earlier published80 result39–41 versus a97ae remains valid for that exact source.
Keep the forecast experiment on a00fff until its isolated observation is complete.
Upstream100M diagnostics motivate fuel work but do not replace normal-budget qualification.

### Latest Hyperion base and bounded experiment findings

The user requested the latest Hyperion again. Upstream is now `fbda80314d703877c3929e2dec8211c61f5d1e79`.
Canonical source aggregate `337f42a54beb5890109e56b755237d8ea0d07abb240d095778f01e2098ab7b39`
reconstructs exactly from the frozen ee1b audit108 integration plus the three new upstream
C++ changes: repeated lost chase evaluations are reused, nearby camp groups use stamp
deduplication, and resumed-turn out-of-fuel printing is Debug-only. These changes are19
insertions/3 deletions across3 files relative to ee1b. Source identity and preserved Willow
integration seams are documented in `willow-latest-fbda803-source-checkpoint.md`.
The frozen new upstream comparator is `bots/baselines/hyperion-upstream-fbda803`, aggregate
`15dcd64d35c179a726c02d3e775b1e3f263f9a4c33b5a8c745e7b13f66dd802d`.
No performance result for an earlier source transfers to this integration. Native replay
rollovers remain the fuel measure; absence of the removed Release print is not evidence
that no turn exhausted fuel.

The old-base forecast formation arm completed52 Debug games on native five-pick published
maps. There were zero raw or parsed forecast activations in104 stdout streams; the largest
stream was717548 bytes, below the1MiB capture limit. This is non-activation, so the planned
Release80 was not run. The descriptive27–25 result is not competitive qualification.
Final summary SHA `2f4f9f6782d9405de4ee8abc44cd7d107ab06622f6f8f99f8d2049baa59c328e`
is in `replays/willow-forecast-formation-vs-a00fff/`; preserve the completed observation.

The Monolith certificate's bounded rejection trace also found no admitted work. In the
observed nomination only Willow entered the worker list. Her candidate stations could
not cover every camp member: most failed the Monolith at(1,1), and the two stations that
reached it failed the Gem Cluster at(0,2). Anchor, exposure and health-reserve checks were
not reached. All34226 extracted chronological events matched the prior Debug game;
that does not establish Release fuel parity or feasibility after relaxing the first check.
Final predicate summary SHA `3af9fae110eaee15a02236d0cd751fe235e9b3b8a983ecbf62dbc6fcd6304457`
is in `replays/willow-local-monolith-reject-trace/cert-reason-v2/`. No further Monolith
runtime is scheduled from this arm.

Both remaining experiments have source-only children on the new canonical base:
deadline staging `42980a43ac4312378b31a609d8f64f2e306dfd25fa8674798d9ed572739a3c27`
and forecast formation `647a10e00c51290b2ba4a38b4cdc93a5f6c258c331d40cb3b1a23610ddbfeb1d`.
Their complete policy hunk bodies match the previously reviewed isolated changes exactly;
see `willow-fbda803-experiment-rebase-source-checkpoint.md`. Neither is canonical or a
numbered release. New development and testing proceeds from this latest base. The forecast
arm needs a rejection diagnosis before any policy relaxation; the staging arm needs an
actual own-view activation witness and normal-budget comparison.

### Latest integration published80:41–39, normal-budget audits complete

Integrated337f42a5 versus frozen fbda803 source15dcd64 completed all80 published games
at Release/default100k, one worker. Wins41–39, runner errors0. Native play rollovers are
559/344; native Bot Error statuses and other draft/play status errors are0/0. The caught
action audit finds candidate0 and reference16, all reference code97 visibility failures.
Turn-order markers/issues are0 across80 validated games. These measures remain separate.

Actual physical rosters were independently mapped to bot indices for every replay. Three-
and four-pick teams share P/V/HoR and P/V/M/HoR respectively; five-pick candidate uses
P/V/M/W/HoR in all52 games, while reference uses Ryth in28 and Vendetta in24 in that slot.
Map-size strata are8–4/12,9–7/16 and24–28/52 respectively. This small comparison neither
establishes overall improvement nor isolates Willow's effect. The extra candidate fuel
rollovers remain material; no numbered release follows this panel alone.

Artifacts: `replays/willow-fbda803-integrated-vs-fbda803/`, setup-after SHA
`84880c52b624be4bd8c72f62623e5d0e5cfc160cc24026981beb8441d1551fa9`;
batch `batch-run-01-release-published40/summary.md` SHA
`16325e4798d6612eb4e6db8559c527d6512d6e340850c1e0563fdba8f32987ba`.
Source/build/map/replay/audit pins are recorded together. Both Release builds succeeded.
The canonical integration is saved in merge commit d4cf962; server44 remains unchanged.

Next Willow diagnostic uses the unchanged latest forecast647a on one Elk Arena pair,
with Debug-only counters at existing computations. Source review suggests an interaction
between current heal-worth thresholds, idle priorities and the completed-turn requirement;
it also identifies the static spawn-tile output veto. Neither has yet been measured as the
cause of nonactivation. A separate source-only value variant may combine unacted workers
and freshly certified empty-group exemption while preserving all safety and current-output
protections. These are proposed conditional positioning improvements, not promised heals.

### Forecast funnel witness and value-only follow-up

The unchanged latest forecast647a was copied into Debug diagnostic92578884, with counters
at existing computations, then played one Elk Arena pair against integrated337f. All34
helper trace rows parse:22 stop at the static camp-spawn veto;12 have no surviving current
workable claim, with all12 rejected before working/damage/worth evaluation. No alternative
station is selected. This supports investigating those gates but does not establish that
the22 vetoed neighborhoods were actually empty or that unacted workers would qualify.
Each replay has one malformed/interleaved outer-funnel row; outer-funnel denominators
explicitly use only complete rows. Neither stdout reached the1MiB cap.

This Debug pair is1–1, with120/124 native rollovers, no native Bot Error or turn-order
markers. Willow's printed OOF phase is decide in20/25 instances; this is Debug evidence,
not a Release phase measurement. Summary SHA
`2750336924d8533d6d3dfce690495417976927a31152c5ed3058839bb2273fd6` and setup-after SHA
`2d27825d910d912540e276e03afb0b3c7159b01546ef174bd03b2fe0bcc3c4cd` are under
`replays/willow-forecast-funnel-vs-integrated-parent/`. Counter locals can affect Debug
code generation/fuel; only output is wholly inside debug_block. No payload parity claim.

The separate reviewed value variant is source0bac63b7. It admits not-yet-acted visible
workers for conditional positioning value, and exempts freshly certified cleared or
respawning groups from the static output veto. Live harmless camps still veto movement.
No future healing or allied tanking enters a safety budget. The successful-state epoch
was extended to recognized respawning code3: state_round alone could be fresh after
unknown code0. The prior sleeping-escape consumer still rejects nonalive respawning
groups, so that admission is unchanged. Actual source review SHA
`d2cfd22bf61879fdb4d9125ca1c1e7106a8afe9076d4077580b3e52262cb5a48`.
See `willow-fbda803-forecast-value-source-checkpoint.md` for both exact deltas and manifest.
The variant is approved for separate runtime, not canonical integration or submission.

The uninstrumented value variant's subsequent Elk Arena Debug pair is1–1, with no runner,
native Bot Error or turn-order markers. There are no changed-move WFF markers; maximum
stdout725303 bytes is below the capture cap. Native rollovers125/141 are Debug-only.
This two-game nonactivation does not qualify or reject the wider policy. Artifacts are in
`replays/willow-forecast-value-vs-integrated-parent/batch-run-02-debug-elk-arena/`.
Further forecast qualification is deferred while investigating the user's Fish regression.

### Current Fish losses and requested4c4eacc comparator

CLI-retrieved finished group342a1765-2345-4f3a-890e-79e83f6802a8 is1–4: Hooks wins;
Gemfight, Shortcut, Expanse and Big World lose. All five put Pantheon on physical A.
The five-pick losses are Expanse658–1004/r820 and Big World536–1012/r964. Actual Fish
composition is Vesper/Vendetta/HoR/Varg/Cassi&Issac, six bodies. The earlier saved4–1
Fish group had Cassi fourth and Ryth fifth; current Fish puts Varg fourth and Cassi fifth.
Map mix also differs. The CLI exposes no executed submission ID, so these public replays
are not attributed to local337f or another exact source merely from the draft.

Our team has zero deaths in both current five-pick losses. Expanse captures777 gems;
658submitted+119held accounts for them, still short of Fish1004. Big World captures994;
536submitted+458held accounts for them. Banking alone would remain six short at that finish.
Big World Willow earns no gold, makes825 walks/87 basics and seven heals2259, repeatedly
capturing a14-gem/zero-gold harmless group. Vesper earns212gold/spends0 and deals5648 camp
damage, versus Fish Vesper41177. Fish's Vendetta and Varg earn2015/1515gold. The supported
lead is allocation and growth, not a missed emergency heal or a blanket forced-bank fix.
Willow's344–350 actor view has full HP, no local ally/camp and successful departure steps;
the repeated recall/cancel events are consistent with the normal end-turn stub.

Corrected extraction, raw intake and native audit are preserved in
`replays/Khaos-v-current-fish-history/group-342a1765/` and
`provenance/fish-regression-history/`. Final group summary Markdown SHA
`3038d6fa4a08070fc1b38339918842193a282afcd27fba8219f3f51307366f13`, JSON SHA
`6c786a2cf2a20223e65d4e5a812f4254c28d2a7172ac0d043372dc5606bb9587`.
Pantheon has18 native rollovers and no native Bot Error statuses; public opponent-side
status rows are absent, so Fish native errors are unavailable, not zero. An invalid first
extraction and failed binary turn-order-audit attempt remain labeled separately.

The user's suggested comparator is Alex4c4eaccefe61f63c5c7adc2ab06105e0ad36b8ec.
Frozen `bots/baselines/hyperion-upstream-4c4eacc` is its root Hyperion source,28 files,
aggregate7f773ba81b8acc1b3d8912ca48ef98be007b4820ca83f5b7b89ff15b75c3f36f.
It is not the unrelated v40 baseline added by that commit. Every source file matches Git.
Its ordinary farm/gold/shop formulas match current337f, apart from capture-signature
wiring; this is not full behavioral equivalence. Its fourth pick is Ryth/Vendetta by existing
camp density instead of Willow, followed by HoR fifth. The saved public results do not prove an executed4c4
submission or the reported historical win rate. Controls will compare the exact old bot,
current gameplay with that old draft, and unchanged current Willow against the same frozen
policy with Fish's roster; this emulator is explicitly not Fish's private gameplay.

Drafts reveal completed simultaneous picks only. Current Willow pick4 sees three opponent
picks; even a delayed fifth-slot choice cannot see Fish's final Cassi. A source-only
counterdraft experiment can respond to the already revealed Vesper/Vendetta/HoR prefix
at our existing fourth slot, preserving fifth-slot HoR and the nonmatching order. It must
not claim to detect an unknown full Fish roster or freeze its observation on pick1.
Detailed evidence/timing is in `willow-current-fish-economic-diagnosis.md` and
`willow-counterdraft-observation-timing.md`. No new deployment or UR queue was made.

### Frozen Fish-roster controls and initial paired experiment

The roster emulator is frozen at10e5eeaa, parent fbda803 source15dcd64. Only its native
five-pick draft changes, to Vesper/Vendetta/HoR/Varg/Cassi&Issac; three/four-pick and test
draft behavior are untouched. It reproduces the observed composition, not Fish's private
gameplay. Local Expanse and Big World decode to the exact public replay map hashes
51ebf62356056f62 and c890c7d4607bc45c respectively.

Current old-draft control b8108db1 changes only the cached role expression in draft.cpp:
teacher Ryth/Vendetta fourth, HoR fifth. The separate conditional2797a671 observes the
exact already revealed enemy Vesper/Vendetta/HoR prefix at three completed own picks,
then latches the teacher fourth choice. Actual Willow/Ryth/Vendetta fourth is reconciled
before selecting fifth, retaining HoR. Missing, late or nonmatching information keeps
the ordinary Willow order. Both full source diffs and aggregates pass independent review
in `willow-fish-draft-controls-source-review.md`, SHA
`c8698a50f4dffacf91ef07756869da707d3bddeb8f6095c1689d4295fc4ade10`.
Neither child changes canonical337f or has been submitted.

The authorized initial comparison is twelve Release/default100k games: exact4c4 source
7f773ba8, unchanged current337f, and current old-draft controlb8108, each against the same
emulator on Expanse/BigWorld both physical sides. Conditional2797 is not part of this
panel. One nice19 worker, build/runtime threads1; no additional live UR. Pre-game manifest
`provenance/fish-roster-emulator-preflight/setup-before-games.json` SHA
`5177a5aaf8b6e2a3c5a0e497dc9c93f540cb8fee06b4a5b79bd332ce0130703f` binds all four
sources, actual Release raw/injected WASMs, CLI/engine and map identities. This small
mechanism comparison is not broad qualification or identification of the live submitted
source. Full outcome and actual roster/native-status audits will follow completion.

### Full roster control panel: the blanket fallback does not hold

All156 games completed: exact4c4 wins31/52, current Willow337f wins32/52, current
teacher-draft controlb810 wins25/52. Native play rollovers are357/378,850/389,413/434
(candidate/emulator). Runner failures, native Bot Errors and turn-order markers are zero;
all candidate caught action errors are zero. The emulator catches code97 in16/15/21
rounds respectively. Preserve those failures as a reference-policy limitation; do not
repair the frozen opponent halfway through the comparison or call these actual Fish wins.

Every actual draft and physical-side mapping was decoded. The28 teacher-Ryth cells yield
13/18/15 wins for4c4/current Willow/current teacher. The24 teacher-Vendetta cells yield
18/14/10. Current Willow beats the current teacher in both strata: paired current-only
versus teacher-only wins are5–2 and9–5. Thus neither the blanket prefix fallback nor
retaining current Vendetta solely under the existing density rule is supported by this
panel. Big World remains a specific nomination, not a validated named-map exception.

The same-roster4c4/current-teacher comparison instead localizes a question to Vendetta
cells: ten4c4-only wins versus two current-only; the Ryth cells have three versus five.
A frozen native fbda803 control on the same52 cells is the next isolation step, separating
upstream107/108 changes from shared changes in the Willow integration. This is evaluation
of existing source controls, not new held-out evidence for a selector fitted to this panel.

Panel summary JSON SHA `93e438a8171d307f692b10f5674559720e5f672fa832790f91ae7d2cc73f19f7`,
Markdown SHA `374b9a15c14a55fbf36fb41ac3292881a57270434e9bde54f975dd496e626351`, under
`replays/fish-roster-emulator-panel-20261023/`. Final source/build/map/audit/replay pins:
`provenance/fish-roster-emulator-preflight/setup-after-extension.json`, SHA
`d7ea862bd77f3a8c775ed8f5a862a0170637b0430eaf9c187ace766405c31173`.

Latest upstream a5749c4 was merged in e17a156; it adds the frozen v44 baseline and research
notes, with no Hyperion gameplay delta. Its baseline source is byte-identical to our
released Khaos_v33/a00fff. A separate source-matched four-game calibration against the
same emulator loses all four Expanse/BigWorld sides, with10/5 native rollovers and no runner,
native, caught or turn-order errors. This arm is separate from the156-game panel. The
newer development source's1–3 on those same cells does not establish general improvement.
Canonical remains337f; no new numbered release or live UR was made.

The paired BigWorld mechanism review also narrows the explanation. At round400 own camp
damage is nearly equal between Willow and teacher controls, but capture ownership differs
substantially. Vendetta's first shared group6 clear/payout is63/69 versus107/115; later
Vesper receives much more gold and gems despite similar output. Willow does deliver2120
real early healing, all to Marcella, and becomes injured herself. Prism's injury window
has no recorded current/one-step Willow heal geometry. Missing allied own-view/branch
information prevents claiming a missed legal heal. See the allocation and paired-control
reviews; no speculative future healing was added to safety or farm values.

### Native upstream control and optional97 isolation

Frozen native fbda803 completes the same52 roster-emulator cells at30–22. Its native play
rollovers are331/377 (candidate/emulator), caught code97 rounds8/18, with no runner failures,
native Bot Errors or turn-order markers. The24 teacher-Vendetta cells yield13 wins and
the28 teacher-Ryth cells17. Thus the old4c4→fbda change loses five wins in the former
stratum while gaining four in the latter; fbda→current teacher loses another three/two.
The near-equal whole-panel4c4/fbda totals do not exclude an upstream layout interaction.
These are paired diagnostics on an already examined panel, not held-out selector evidence.
The full52 comparison is in `replays/fish-roster-emulator-panel-20261023/08-fbda803-vs-roster-emulator-full52/`;
comparison JSON SHA `719e1d592944cd4be5cabc428dbe6beca2722d54bbb72d3fca0481a23fa79554`.

Source-reviewed97 ablations complete a2×2: upstream with the safe optional handler37c3,
and current teacher with the old throwing handler e9a9. Only the two safety.cpp hunks
change in each child. The eight initial default100k games, Elk Arena and Boss Battle
both sides, give37c3 four wins and e9a9 four losses. Both new arms have zero runner/native
Bot Errors, caught action errors and turn-order markers. Restoring exceptions is an
experimental factor, not a release proposal. Complete source pins and review are in
`fish-optional97-factorial-source-checkpoint.md` and its source review.

On Boss specifically, upstream throw and upstream optional both win2–0 with2/2 candidate
rollovers; current teacher optional and current teacher throw both lose0–2 with8/16.
No caught error is reported in these cells. The same-handler37c3/b810 event streams first
differ in round1, but the first mismatch compares different actors, so that ordinal event
comparison does not identify a specific wrong decision or equivalent input state.

Four authorized Release100M diagnostic games compare37c3 and b810 on Boss A/B, raising
both candidate and emulator budgets. The complete unwrapped replay payload is identical
between codebases on each side; candidate wins both in893/1759 rounds. There are no native
rollovers, native/caught errors or turn-order markers. This supports a budget-mediated
integration effect in those cells, not a default-budget qualification. Candidate fuel is
186,693,253→189,520,692 on A and307,336,356→312,787,256 on B: current teacher uses1.51%/1.77%
more than upstream optional, across identical gameplay. Every candidate champion's total
is higher, with median-profile differences506–711 fuel. The responsible helper is not yet
identified. The protocol-preserving absent-pair comms optimization is the next small
source candidate, not a claimed complete explanation of the Fish regression.

Two additional100M games accidentally used e9a9 instead of b810. They remain preserved
and explicitly excluded in `04-current-teacher-throw97-highfuel/EXCLUDED-ARM.md`; the correct
b810 pair is folder05. A preliminary verbal B-loss report confused winner bot index with
physical side. Reconciliation of raw winner indices confirms the corrected high-fuel2–0
and all earlier31/32/25/30-of52 totals; no wider-table correction was needed.
Evidence is in `replays/fish-optional97-factorial-vs-emulator/winner-fuel-reconciliation.json`,
SHA `fb564d02c0b8dfda8c3c7a404297c493f177f45a7e6bd5477f71185ccc9869ee`, and
`fish-factorial-causal-fuel-review.md`. Canonical337f and the submitted release remain unchanged.

Separate known-information four-pick review does not establish a combat bug from two
nominated deaths. Shortcut Prism cannot leave adjacent ready Vendetta's melee threat with
one walk after the altar lock; his stun buys a turn, and the later stun marker is expired.
Gemfight HoR's round51 step increases enemy separation. Earlier route choices remain
questions, not proven missed escapes. See `willow-current-fish-four-pick-losses.md`.
The upstream unseen-recall crew hypothesis likewise needs its narrow positive-delay claim
gate to occur; its formula can increase our projected reward share. No observation-metadata
reversal or harmless-camp finishing policy was added without a witnessed decision error.

### Local source recovery interruption

A helper accidentally deleted the local bots directory during variant preparation. Development
paused immediately; no new match or submission occurred. Tracked canonical337f was restored
fromHEAD87cbbfe and rehashed. Thirty-four documented source trees were reconstructed from
release ZIPs, immutable Git sources, exact patches and original task tool records, then
independently checked. Replays, maps, research, original source/build pins and release receipts
were outside the deleted directory and remain intact. The fixed emulator10e5 and diagnostic9257
also match their original file and aggregate hashes. Their previously unsaved full patches are
now preserved as `fish-roster-emulator-recovered-source.patch` and
`willow-forecast-funnel-recovered-source.patch`.

The newly rebuilt Khaos_v33 raw and injected WASMs exactly match its original release pins.
Other reference binaries must likewise be checked before reuse. One pre-existing ignored
directory, `bots/variants/ladder_manip`, has unknown contents and no recovered source; the user
has been asked about it. This is not a claim of exhaustive filesystem recovery. See
`BOTS-RECOVERY-20261023.md`, `bots-recovery-source-audit.md`, and the immutable source inventory
`recovery/incident-20261023-bots-recovery/recovery-index-v2.json`.

### Cached support endpoints: initial fuel-only check

The user closed the unknown `ladder_manip` recovery question with “ignore it”; its contents
remain unknown. All four required benchmark executables were reproduced with exact original
raw and injected hashes before runtime work resumed.

Candidate a67dc0a3 changes only comms.cpp from canonical337f: cache immutable ally indices,
skip irrelevant support-mailbox work when the Prism/Willow pair is absent, and keep the
ordinary successful-read epoch separate from the support epoch. Current liveness and respawn
checks remain per-turn. Astra source review found no behavioral blocker. The teacher-draft
child is7c7819f3; its other28 files matcha67. Neither is a numbered release or canonical edit.

Six Release games at100M fuel, Boss Battle both sides, check both present/absent pair cases.
Teacher child uses the existing b810 high-fuel parent pair; canonical337f and cacheda67 each
play a new pair against unchanged emulator10e5. All four complete unwrapped replay comparisons
are byte-identical; opponent fuel totals also match exactly. All six new games have zero
runner/native/caught/turn-order errors and zero native rollovers. Candidate play fuel changes:

| Roster | Side A parent → child | Side B parent → child |
| --- | ---: | ---: |
| Teacher |189,520,692 →188,178,741 (−0.708%) |312,787,256 →310,147,402 (−0.844%) |
| Willow |247,547,851 →246,838,444 (−0.287%) |362,646,513 →361,578,858 (−0.294%) |

Typical per-turn savings are301 without the pair and118 with it; first-turn initialization
costs differ. This recovers only part of the measured integration overhead. High fuel tests
behavioral equivalence, not default-budget strength. Evidence and actual actor mapping:
`replays/fish-comms-cached-diagnostic-20261023/initial-six-reconciliation-v1.{json,md}`.
The four new default100k Boss checks give cached teacher1–1 (old teacher0–2) and cached
Willow2–0 (original Willow also2–0). The Willow match lengths change983/953→983/1494;
these two games do not establish a strength gain. Native play rollovers are13/16 for the
teacher/emulator pair and12/11 for cached Willow/emulator. Native Bot Errors and turn-order
markers are zero. The teacher matches contain one caught code5 per team, on different games;
the cached Willow matches contain none. An initial verbal summary incorrectly reported zero
rollovers/errors and a wrong cached-A roster; replay-derived correction is preserved in
`replays/fish-comms-cached-default100k-20261023/correction-record-v1.{json,md}`.

The repository `tools/fuel/bench.py` default eight-map set then runs both controls against
unchanged10e5, each side, Release100M, one job:32 games,16 matched pairs. All16 complete
replay payloads, winners and drafts are identical. Total play fuel falls3,305,958,229→
3,292,319,906 (−0.41%);83,785 paired turns are cheaper and50 dearer. Excluding round1 gives
83,763 turns and−0.4169%. The higher first-turn initialization cost is retained in the
all-play comparison. These are fuel-equivalence tests, not strength qualification.
An attributed stdout scan finds zero candidate caught action errors in either arm; the fixed
emulator has the same six code97 markers in each. The scan records bundle, physical side,
bot identity, round and original marker text in `stdout-marker-scan-v1.{json,md}`.

The reviewed one-file comms change is retained in canonical, nowa67dc0a3; frozen337f remains
intact for the BigWorld decision trace. Checkpoint, source review, source/build pins and exact
commands are under `research/cached-endpoints-bench32-checkpoint-v2-20261023/` and
`willow-comms-cached-endpoints-source-review.md`. Runtime evidence is under
`replays/fish-comms-cached-fuelbench32-20261023/`. No numbered version or submission was made.

### Current development source against the submitted v33

Native-draft Release/default100k, all40 published maps on both sides, one worker: a67 versus
frozen released a00fff finishes40–40/80. Both source aggregates and all four raw/injected WASM
hashes match their frozen records before/after the run. Actual replay rosters partition the
results into3-pick7–5,4-pick10–6 and5-pick23–29 for a67. This does not isolate the Willow pick:
both five-pick policies include Willow, and the code differs beyond support. The aggregate
is level and the five-pick result supplies no basis for immediate release or a fitted selector.

Runner failures, native Bot Errors and turn-order markers are zero. Native play rollovers are
622/523 (a67/v33). One candidate caught code5 occurs on Starfish A at round822; the reference
has none, and neither has code97. The code5 cause remains unresolved, not silently excluded.
The candidate's increased rollover count is for different games/decisions; it does not
contradict the byte-identical fuel-only saving measured against its immediate337f parent.

Artifacts: `replays/willow-comms-cached-vs-khaos-v33-a00fff-80published-20261023/batch-run-01-release-published40/`.
Attribution summary SHA `19108cab018de43f2b47c218dbff9b3351e5b7c91e061c73e9e889497f0aae87`;
postflight pins SHA `04adfb96518b69d1fd2ebde6339580e95b3fb9acccabe72e3032e81765c29f11`.
No release follows from this level panel alone.

### BigWorld decision witness and sustainable crew experiment

The frozen337f BigWorld A loss against emulator10e5 reproduces exactly in Release. The
instrumented recorder retains the full action/state sequence but differs in two fuel readings:
Willow at round4 by+40 and Heart of Ruin at470 by+896. The subsequent branch trace matches all
205 actor/round wrapper segments for rounds35–75, all four rollover points and all native
actions/state through that window. Its first action/state differences occur at279/280, after
recorder stdout ends during267. This supports bounded decision observations, not a claim of
strict fuel identity or full-game traced equivalence.

Prism selects group12 at41 while Willow retains4; their remembered positions are stale and
invisible. Willow sees the pair again at46 and provides the previously verified heal to
Marcella. Willow selects help6 at47 and Prism explicitly changes12→6 at50. Prism then takes
early passing attacks on the same assigned group while losing health, before retreating60.
Thus the earlier hypothesis of passing attacks silently redirecting him from12 is rejected.

Source review identifies a narrower inconsistency: struggling-ally help can override the
helper's own grouped health rejection, and Boolean allied occupancy can promote otherwise
unaffordable work. The existing forecast values were not logged, so this does not prove that
every group6 commitment fails the model. An isolated sustainable-crew candidate from current
a67 now aligns those admission paths and re-evaluates damaged ranged crew work. It preserves
harmless attacks, melee passing, actual healing, spell kiting and risky fallback. Source review
and default-budget paired tests precede any canonical change.

Compact trace evidence, complete instrumentation diff/header, source/build pins and fidelity
limits: `willow-bigworld-witness-checkpoint-20261023/PROVENANCE.md`. The validated diagnosis and
bounded implementation contract are in `willow-bigworld-validated-crew-diagnosis.md`.

### Sustainable crew: mixed default-budget result and Boss fuel diagnostic

Reviewed candidate69010aea from a67 aligns early ranged passing, ranked affordability and
struggling-ally help. It preserves ordinary melee/harmless passing, existing grouped estimates,
spell kiting and risky-own fallback. Source review caught and corrected an overly broad early
scope and a stale-world check placed before the new lazy certificate. Canonical staysa67.

Four published maps, both sides, fixed10e5 emulator, native drafts, Release/100000: candidate
and parent each win4/8. Candidate gains Gemfight B and loses Boss B. Gemfight is four-pick,
without Willow; the three five-pick maps therefore finish2/6 versus3/6. The opponent emulates
Fish's roster only on five-pick maps and retains native upstream picks otherwise. No private
Fish policy is reproduced. Fourteen new games plus two source/build/map-matched reused Boss
controls complete with zero runner failures, native Bot Errors, caught action errors or
turn-order markers. Native play rollovers are35/38 for candidate/emulator and33/26 for
parent/emulator. This small panel neither qualifies a release nor establishes aggregate strength.

The verified BigWorld comparisons show an economic cost despite less incoming camp damage.
At common round904 on A, candidate banked+carried capital is765 versus958; incoming camp damage
is22,380 versus28,746 and completed recalls32 versus35. At common round946 on B, capital is782
versus891, incoming damage17,858 versus25,978, recalls33 versus37, and deaths1 versus4. Fewer
injuries alone do not establish an improvement. First action differences involve healthy actors:
A Prism takes a different step at43; B Vesper walks at39 where the parent attacks, resets and
attacks again. Those events do not identify the rejected alternatives or exact decision branch.

Boss A first differs at round1: candidate Prism has native rollover status6 and no action,
while parent Prism acts and moves. The candidate later wins only329–301 at2000; parent wins
at983. Boss B first differs through two acted routes at3; candidate loses at1070 while parent
wins at1494. Whole-game rollover totals cannot explain these specific divergence points.

Two separate candidate Boss games at100M, reusing matched a67 high-fuel controls, both win:
767/1099 rounds versus parent1204/1812. Actions and whole champion/gem snapshots match through
A36/B37; first differences are Prism's route at37 and Vesper's dash/move at38. On these matched
180/185-own-turn prefixes, candidate fuel is3.782%/3.722% lower. At100M both A-side Prisms act
and take the same first move; their first turns cost570,851/575,995, so neither high-fuel turn
fits the ordinary first-turn budget. This separates a budget-sensitive opening from later
policy differences; it does not prove the entire default-budget loss is caused by one rollover.
Both high-fuel games have zero native rollovers, Bot Errors and turn-order markers. High fuel
is diagnostic only, not release qualification.

Artifacts: `replays/willow-sustainable-crew-fish-panel-20261023-v2/` and
`replays/willow-sustainable-crew-boss-100m-fuel-diagnostic-20261023-v1/`. Use the former's
`postflight-v2.json` for explicit native-side versus canonical-arm winner indices, and
`bigworld-paired-summary-v2.txt`. The initial BigWorld summary paired the wrong Boss parent
paths; it is preserved as invalid and excluded. All35 extraction soft notes concern derived
earned gold or champion-damage counters; reported snapshot capital, native results and incoming
camp damage do not depend on those fields. Incoming event damage was checked against native
monsterDamageTaken. Binary CAMSTAT files named `.stats.json` are not JSON.

A new source-only fallback experimentfd99d107 retains current-HP-bounded risky shared work
only after affordable choices, preserves incumbent crew identity through an unevaluated route
fallback, and clears rejected work consistently. It reuses existing calculations and does not
restore the Boolean ally-occupancy waiver. This addresses static consistency gaps, not a proved
cause of the observed first divergences. Source review passes. Neither experiment is a
numbered release or a canonical gameplay change.

The fd99 follow-up wins5/8 against the same fixed10e5, compared with4/8 for6901 and a67.
It wins BigWorld A, both Boss sides, Expanse B and Gemfight B. Five-pick cells are4/6 versus
2/6 and3/6 respectively; four-pick Gemfight is1/2 versus2/2 and1/2. This small mixed panel
does not justify fitting a map/draft selector. Native play rollovers are41/41 for fd99/emulator;
runner failures, native Bot Errors, caught action errors and turn-order markers are zero.
Eight extractions succeed with12 soft derived-stat notes (9 earnedGold,3 championDamageTaken).

The initially reported4/8 count was wrong: Gemfight B is a candidate win. Native final
winner/scores and run-log TEAM A/B lines agree on5/8. Use `RESULTS-v2.md` and
`postflight-v2.json` under `replays/willow-sustainable-crew-fallback-fish-panel-20261023-v1/`;
v1 prose is superseded. Native physical-team indices and canonical bot indices are explicit.
BigWorld A at the common904-round endpoint still has less own capital than a67 (749 versus958),
despite eventually winning1014–874 at1085. This is not evidence of universally faster farming
or proof of an unlogged branch. Boss A wins377–0 only at2000 and Boss B0–1013 at1975, both
slower than a67's wins.

The direct published40-map panel subsequently finishes35–45/80 for fd99 against frozena67,
with physical-side wins17/40 on A and18/40 on B. Both use native drafts, Release and explicit
100000 fuel, one low-priority worker. Native play rollovers are589/572; runner failures,
native Bot Errors, caught action markers and turn-order markers are zero. Extraction succeeds
80/80, with133 soft derived earnedGold notes and no hard failures. Native outcomes and rosters
do not depend on those derived counters. The runner's stdout was not persisted; this limit is
recorded, and each outcome comes from the saved native replay with explicit physical mapping.
Source and raw/injected WASM pins match the frozen artifacts. See
`replays/willow-sustainable-crew-fallback-vs-a67-published80-20261023-v1/RESULTS-v1.md` and
`postflight-v1.json`. The initial chat-only side split20/15 was incorrect; the authoritative
native table has17/18. Native draft-round partitions are3-pick5/12,4-pick4/16 and5-pick26/52;
this describes the panel and is not a fitted draft selector. This weaker panel does not qualify
a release. The next diagnosis
separates useful short ranged contributions from committing to an unaffordable full clear;
neither that hypothesis nor the value of another refinement is proved by aggregate wins.

### Willow shopping and role-dependent Treasure research

The canonical a67 shop chooses main stats from basic attacks and damaging casts, excluding
Willow's healing; its upkeep model prices her own clearing and recovery, not allied healing
or support availability. Health/mitigation alternatives exist, but fresh Focus is absent.
This is a support-value gap, not proof that Focus-first or Health-first wins. Healing must
not be added to raw_output, which also drives camp damage and crew affordability.

Willow gains50HP,3Strength or5Focus per30-gold shard; Focus adds up to15HP to each actual
heal and helps only when the old heal cap binds. Her worth-healing threshold also grows
with heal size. Exact a67 BigWorld/Boss A examples show meaningful farming and healing:
239/329 basic attacks,20/53 heals,6695.8/17162 actual healing, and zero Willow deaths.
Both retain120Focus. BigWorld finishes TreasureStrength but only four JungleStrength
shards, so she never receives completed Jungle protection. These native totals and exported
actions do not expose all above-cap recipient deficits or establish a counterfactual benefit.

Treasure grants its five shards' stats plus20% base capture/kill gold. Vesper's additive
bonus changes1.33→1.53, others1.00→1.20; the extra absolute payout is identical per base
gold. Actual future recipient income and the delayed alternative emblem matter, so no blanket
removal from non-Vesper roles is justified. Our initial claim that Marcella's tribute passive
was excluded is contradicted by two exact-a67 replays: BigWorld A rounds327→328 have a41-gem
tribute and98 additional displayed gold, with completed Treasure and no capture/kill/shop in
that round (82×1.2=98.4 before floor). Full Boss A accounting also matches2.4 gold per tributed
gem. A dedicated engine probe then confirms the rate: without Treasure,4 gems pay8 gold;
after Treasure,15 gems pay36 gold, with no other income during either tribute. The rule
reference and probe index are corrected. The earlier user statement was corrected immediately
when the replay evidence appeared. Successful source/evidence is preserved in
`tools/probes/probe-marcella-treasure/` and the full v2 replay/provenance folder. The invalid
first attempt lacked the Marcella draft case and is preserved separately. The successful
probe's one derived earnedGold warning omits all44 tribute gold; the existing validator
currently sums capture/kill income but no tribute income. Native snapshot deltas are decisive.
Historical CHANGES101 found broad/fresh Treasure-first gains; generic forced Health and
additional speculative Treasure-return pricing did not improve their historical baselines.

The replay extractor is now corrected separately: v2 adds each tribute completion's native
lifetime-earned-gold delta to `tribute_end.earnedGold`, and validation includes it. It does
not infer historical bonuses from final inventory. The probe reconstructs 388 earned gold
including the 8/36 tribute payments; exact a67 BigWorld and Boss reconstruct Marcella's
3095/5774 and remove only her omitted-income warnings. Their native outcomes, round states
and event sequences match old extractions except for the added field. Fragment, with no
Marcella, has 55 tribute events with zero earned income and no validation notes. Other Boss
warnings remain. Existing extractions are preserved; new outputs and source snapshots,
patch, hashes and reports are under `provenance/willow-marcella-tribute-earned-gold-20261023-v1/`.
The extractor version bump prevents reuse of older cache entries lacking the new field.

Two separate source-only a67 experiments are being prepared: allow one existing-model-selected
Jungle/Durability before Treasure for Willow, preserving begun items; and, after economy plus
protection, substitute one newly selected BruiserStrength with BruiserFocus. The latter keeps
the same150gold and50HP, trades12Strength for20Focus, and quotes the actual chosen stats
without inventing healing-as-DPS savings. Historical same-shop337f games show some Bruiser
activation, but each new arm still requires actual purchase evidence and runtime validation.
Research: `willow-support-items-and-treasure-review.md`. Canonical remainsa67.

Six Release/100k item smoke games then exercise the two frozen arms against fd99 on
BigWorld A, Expanse A and Corners B. First-protection starts Jungle Strength at BigWorld
round 494 (three shards, completion 792) and Corners round 52 (two shards, completion 494).
Expanse has no qualifying protection purchase before Treasure. The Focus arm buys no Willow
Bruiser Focus in BigWorld/Expanse; Corners buys four shards at 836 and completes at 1001.
Absence of a purchase does not prove a policy no-op because quotes can affect prior decisions.
Other champions' normal Focus purchases are not evidence of Willow-specific policy activation.

Corners' four Focus shards give Willow 140 Focus versus 120 for the same-stage Strength
item; the completed Bruiser gives 145 versus 125. Fourteen subsequent heals restore 5613 HP;
ten exceed the corresponding Strength-item cap, using 600 HP of extra capacity on that
recorded trajectory. This conditional cap utilization does not establish a counterfactual
healing or win gain, and does not price the sacrificed attack damage. An earlier calculation
incorrectly granted every non-Focus emblem a Focus shard; only Bruiser gives those cross-stat
shards. That calculation is preserved and superseded. Effects begin at shard purchase.

Both arms win one of their three selected diagnostic cells. First-protection/fd99 native
rollovers total 22/17; Focus/fd99 total 9/19. Runner failures, native Bot Errors, caught action
errors and turn-order markers are zero. All six extracts succeed with 12 tribute-income
earnedGold soft notes under the old extractor. Native fault counters and capped fuel values
are not used as substitutes for the native rollover audit. Authoritative corrected report:
`replays/willow-support-item-smoke-20261023-v1/audit-v2/RESULTS-v3.md`, with preserved earlier
attempts, source/build pins and physical-side rosters. This panel establishes purchases and
recorded effects, not a release qualification.

A direct Health sibling of the first-protection arm is now source-reviewed: `3b815902`.
Only when `2ae444fa` would select fresh Jungle Strength in its first-protection override,
it returns the actual-valued Jungle Health choice. Begun items, Durability, Treasure timing
rules and all other roles remain unchanged. Completion exchanges 15 Strength for 250 HP at
the same cost and camp mitigation; the extra HP above the 35% recall reserve is 162.5.
Neither healing capacity nor its worthwhile-heal threshold changes. This arm is needed
because the protection smoke games selected Jungle Strength; later Health purchases do
not test the first protective stat. Quotes may affect decisions before any purchase, so
absence of a qualifying purchase is not evidence of an identical policy trajectory.
See `willow-health-selection-and-first-protection-review.md`,
`willow-first-jungle-health-comparison.md` and the actual-source review. Full source
snapshots and exact parent/cumulative patches are preserved in
`provenance/willow-first-jungle-health-20261023-v1/`. Runtime qualification is pending.

### Upstream c71be8c integration prepared separately

Origin/main advanced froma5749c4 toc71be8c with end-of-turn terrain-table preparation and
deferred generic step guards. An isolated a67 child,4db4eecb, incorporates those eight source
files while preserving eager Willow station guards, their refresh behavior and protection
during plan execution. Its actual-source review passes; no canonical merge or runtime claim
follows from that. Full parent/upstream/integration snapshots and exact deltas are preserved in
`provenance/willow-upstream-c71be8c-20261023-v1/`.

Upstream reports complete replay identity on its own28 high-fuel screen games and fewer
real-budget rollovers on1104 games, but those artifacts were unavailable locally and those
results do not validate this combined Willow source. Our qualification requires16 paired
Release100M games against frozen a67 with the fixed10e5 opponent, then separate default-budget
checks. The queue intentionally spends spare fuel, so total fuel alone is not its objective;
heavy-turn costs, rollover behavior and preserved actions matter. First cold initialization
allocates13200 payload bytes at100×100 after a6000 per-tile allowance plus10000 end reserve.
This is a source-review concern about the reserve, not a proven rollover. See
`willow-upstream-c71be8c-source-review.md`.

The isolated integration completes all16 high-fuel pairs with byte-identical complete native
replay payloads. Across83763 own turns after round1, total fuel rises from3271380744 to3898892321
(+19.18%), while turns above100000 fall624→492 and the maximum falls231256→221411. The queue
spends spare fuel preparing later work; these counts do not establish real-budget behavior.
Round1's summed fuel delta is+443892 and is not a claim that each first turn fits200000.
Native rollovers and Bot Errors are zero at100M; candidate caught errors are zero, and the
emulator's six code97 markers match the controls. All16 extracts succeed with19 earnedGold
soft notes. Two complete Ambush attempts were duplicated after the adapter failed while
forming a log filename; their payload/fuel hashes match the successful reruns and they are
counted once. Both attempts and successful runtime logs are preserved. See
`replays/willow-upstream-c71be8c-integrated-fuelbench16-20261023-v2/RESULTS-v3.md` and
`postflight-v2.json`. The v3 prose clarifies that round 1 was not tested under its real 200k cap.

The subsequent default-100k diagnostic has eight unique cells: BigWorld, Boss, Expanse
and Gemfight on both physical sides against fixed 10e5. Both integration and a67 win 4/8;
candidate play rollovers are 39 versus the a67 controls' 33. Candidate caught/native bot
errors and turn-order markers are zero. The fixed opponent has 29 rollovers and one caught
code97. Only BigWorld A preserves the entire default-budget input/state/result sequence;
the other trajectories diverge. Boss A first differs at round 1 (End turn versus rollover),
which does not identify the cold queue as the cause. This small panel is not a strength gain.

The initial adapter passed candidate as physical A for every tag. Its four nominal B
attempts are byte-identical A duplicates and excluded. Four missing B cells were then run
with reversed arguments in a separate directory; all attempts and logs remain. The corrected
ledger, native audits, per-cell rosters, controls and checksums are authoritative at
`replays/willow-upstream-c71be8c-integrated-default100k-8-20261023-v1/corrected-v2/RESULTS-v2.md`.
Do not use the original eight-cell mapping. Development now integrates origin/main c71be8c
to exact reviewed source 4db4eecb; broader qualification is still required before release.
Willow item and crew experiments are not included in that canonical source.

### Bounded stationary crew contribution prepared separately

An isolated fd99 child,10310292, adds an early stationary attack option for ordinary ranged
farming when the full-clear affordability gate rejects already-active shared work. It requires
fresh visible camp work and a visible ally in actual basic reach, preserves nonincumbent claims,
and charges all static camp strikers in reach without ally, kill, healing or sleep discounts.
Current HP must retain the existing35% reserve after that phase, and current-tile modeled enemy
hits/stuns reject the extra option. Sixteen group memos, one phase sum and at most one threat
evaluation bound the added work. Later moving attacks, ranking and routing retain fd99 behavior.
This is a one-phase policy hypothesis, not a full-clear or escape guarantee, and does not claim
to recover the sleeping-camp BigWorld B39 example. Actual-source review passes with no blocker;
see `willow-stationary-crew-source-review.md`. No runtime, canonical change or release claim.
Snapshots and exact deltas are preserved in
`provenance/willow-stationary-crew-20261023-v1/`.
### Upstream supplementary fuel screen (reported)

- Fuel ideas screen (2026-10-23, a5749c4, isolated copies; 6 maps / 12 games, test drafts, 100M,
  normal local -O3 builds): all three candidates kept 12/12 replays byte-identical; none improved p99.
  Baseline mean/p99/turns >100k: 41977/114160/1555. Stop generating rejected children after the existing
  24-node search cap: 41982/114245/1561 (up to 23777 saved on one turn, but only 63 cheaper vs 9272
  dearer). Direct raw-chunk rectangle tests for any_within: 42180/114209/1563 (+0.48% total fuel).
  Singleton unseen threats as direct Chebyshev distance instead of a field: 41981/114160/1555.
  No real-budget OOF gain claimed; no Hyperion changes. Details, artifacts, and untested structural
  ideas: [FUEL-IDEAS-2026-10-23.md](hyperion/FUEL-IDEAS-2026-10-23.md).

### Willow first-Jungle Health: bounded purchase diagnostic

The isolated `3b815902` Health sibling completed three Release/default-100k games against
fixed `fd99`, with matching `2ae444fa` first-protection controls. Both arms win BigWorld A
and lose Corners B and Expanse A. This selected three-cell diagnostic is not a strength test.
Expanse's complete native payload is identical to its control and has no qualifying Health
purchase. On BigWorld, the first action difference is Willow's round102 move, before the
first Health purchase at506; no logged branch identifies why the pricing change first
altered the route. Later differences cannot be attributed solely to acquired HP.

On Corners, Health buys two Jungle shards at52, two more at355, and completes at384.
Through the common round950 horizon it delivers7737 healing/25casts, completes12 recalls
and dies twice, versus12285.5/37casts,8recalls and one death for2ae. On BigWorld through
round1001, the corresponding healing is3058.8/10casts versus6478/20casts, recalls10versus11,
and deaths0for both. These diverged histories establish neither a survival benefit nor that
Health is intrinsically worse; item quotes also affect farm and shopping decisions.
Health/native opponent rollovers are9/25; native BotError, caught act-error, turn-order
markers and runner failures are zero. The authoritative common-horizon report is
`replays/willow-first-jungle-health-smoke-20261023-v1/RESULTS-v2.md` with filtered audit
`audit/health-vs-2ae-v2.json`. Its superseded v1 mixed full-game event totals with common-round
state snapshots and remains preserved. All sources, builds, actual sides and replay hashes
are pinned in the run's postflight; the arm remains isolated.

### Stationary crew: direct-parent smoke, opponent mismatch

Eight Release/default-100k cells for `10310292` ran against parent `fd99`, although the
planned opponent was the fixed `10e5` roster emulator. Preserve these as direct-parent
diagnostics only; they cannot be compared with fd99's earlier emulator results. No reruns
or emulator qualification are implied. The correct physical A/B orders and eight unique
outputs are preserved under `replays/willow-stationary-crew-smoke-20261023-v1/`.
Candidate wins4/8: BigWorld A, Boss A, Expanse B and Gemfight B. Both bots have31 native
play rollovers, with zero native BotError, caught act-error, turn-order markers and runner
failures. Gemfight has four picks and no Willow; the other maps have five picks. The added
stationary tier is not instrumented, so outcomes do not establish activation. Extractor v2
reports one remaining derived-earnedGold soft note on Boss A; outcomes and native round
states do not depend on that derived total. No canonical promotion or release claim.

### Focus policy port to current upstream

Isolated `ae18438d` ports the exact five-line one-BruiserFocus policy from `1657a09c` onto
canonical `4db4eecb`. Its full best_emblem function matches the older arm; begun partials,
Treasure and first completed protection still precede one fresh Bruiser Strength-to-Focus
exchange. The actual Focus value and price are returned. Full 29-file source snapshots,
manifests and exact patch are under `provenance/willow-one-bruiser-focus-c71-20261023-v1/`.
No Health/protection-first policy, demand gate or invented healing-to-DPS utility is bundled.
Runtime is pending and canonical remains unchanged. Check qualifying purchases before
a broad comparison; native five-pick results must be reported alongside the whole panel.
See `willow-demand-informed-focus-next-step.md`: current heal demand alone does not measure
extra Focus benefit, and a higher heal cap also changes the existing cast threshold.

### Treasure exposure by role in saved a67 controls

A single sequential analysis of the existing fd99-vs-a67 published80 extracts selects only
the a67 side by the original manifest order (40 physical A,40 B). It uses native cumulative
earnedGold snapshots, not the event-derived earnedGold validator. Income after the first
completed Treasure excludes its entire completion round. The estimate attributable to
Treasure is `0.2/(1+passive+0.2)` times that later observed income: Vesper's denominator is
1.53, others1.2, including Marcella's tribute income. This holds the observed farming and
purchase schedule fixed, ignores displaced-item benefits, and is not causal ROI.

Treasure completion counts and median estimated later bonuses: Vesper76/80 and183gold,
HoR74/80 and172, Marcella64/68 and302.3, Willow39/52 and48; Prism0/80. Median completion
rounds are161,210.5,166 and379 respectively. Of Willow's39 completions,15 earn under30gold
of estimated bonus thereafter. Eight completed Treasure but never completed Jungle or
Durability by game end;21/52 Willow appearances end without either protective emblem.
These observations motivate targeted Willow timing experiments, not removing Treasure
from all non-Vesper champions. The passive alone does not make Treasure uniquely efficient
on Vesper. Full per-game records, source/replay/manifest pins and the Luna analysis script
are in `research/willow-a67-treasure-exposure-20261023-v1/`.

### Retained Prism no-work conversion: isolated source candidate

`28d1311c` implements the bounded contract as a separate `4db4eecb` child. Only bot.cpp
changes. An ephemeral farm outcome requires retained positive bankable Prism gems, an
actually complete normal scan, no selected work tier, a positive evaluated deadline
rejection, no unresolved positive wait/work, and a fresh live record with movement/basic/
cast unspent. Early work returns and selected jobs retain their behavior. The ordinary
farm caller clears the abandoned claim and invokes existing banking once with an explicit
retention override; every submission site now requires tribute_ok for this invocation,
including the original tile after failed movement. Ordinary banking callers are unchanged.

No new scan or fuel gate is introduced. The terminal branch adds a self-record read and
freshness checks; actual conversion has its normal routing cost. No persistent latch or
global closing change is made. The source review passes, but conservative wait/claimed-work
vetoes may suppress activation, and next-turn work selection may reverse the route. Runtime
must establish actual activation, conversion, fuel costs and reversals. This is not an
attribution or verified fix for the older Rows replay. Full snapshots, manifest, exact patch
and checkpoint are in `provenance/willow-no-work-conversion-20261023-v1/`; see
`willow-no-work-conversion-source-review.md`. Canonical remains4db; runtime is pending.

### Current integration versus released v33: full native-draft outcomes

Release/default100k `4db4eecb` versus frozen released `a00fff45`, both physical sides on
40 published +256 gen(seed1023)+256 gen-s1(seed1024) maps:524–580/1104(47.46%). Published
maps40–40, gen231–281, gen-s1253–259. Both draft sources are identical and test_draft=false.
This does not demonstrate an improvement over release; the generated-map deficit requires
diagnosis. Willow item, stationary-crew and no-work-conversion arms are not included.

All1104 unique native CLI games completed and source/raw/injected/CLI/engine pins remain
unchanged. The first13 completed outputs resolved beside the manifest rather than the run
cwd; they were preserved and reused. One subsequently started game was interrupted without
a completed output. The remaining1091 ran once with absolute output paths. Both attempts,
the interrupted attempt, logs and combined authoritative outcome ledger are preserved in
`replays/willow-hyperion4db-vs-v33-a00fff-full1104-run01/`; the first13 replays remain in the
preflight provenance directory. No completed cell was rerun for the path correction.

The completed full-state native audit covers all1104 games: candidate4318 play rollovers
(A2239/B2079), reference5170(A2566/B2604), and zero native BotError for either bot. Draft
and other-phase rollover/error counts are zero. Separate stdout audits find one candidate
caught code98(api_not_found), Labyrinth102406310 physical B round448, and none for v33;
the action/import cause is not yet identified. Turn-order markers are zero for both bots
across1104 audited games, with no audit issues. There are no runner failures. Lower aggregate
rollovers do not explain or offset the strength deficit.

Detailed reports and the combined `audit-summary.json` are under
`replays/willow-hyperion4db-vs-v33-a00fff-full1104-native-audit-v1/`; the combined summary
SHA256 is `3e3e2f011984c196185109a4114ccd8c31d617573e102bf771587d95dfccebb4`.
Final source/build/CLI/engine pins match pre-run values. An initially started extraction
pass was stopped after77 complete records because it did not supply this full-phase audit.
Its outputs/logs remain in the same directory for loss analysis, without a finalized extract
index. No release follows from these outcomes.

### Combined Health and Focus item hypothesis

Isolated `279ddbf4` combines exact3b first-protection/JungleHealth behavior with the exact1657
one-BruiserFocus preference on canonical4db. Only best_emblem changes(+14/−1). Removing the
Focus block leaves that full chooser byte-identical to3b; the Focus block matches1657.
Existing partials, protection closure, Treasure priority and the completed-Focus inventory
witness remain intact. The Health/Focus substitutions return their actual values; the
inherited forced-Treasure proxy is unchanged. Source review passes; runtime is pending.
This tests provider survival and healing together, alongside isolated Focus, without a
new scalar healing utility. Full29-file snapshots/manifest/patch/checkpoint are in
`provenance/willow-health-plus-focus-c71-20261023-v1/`; see
`willow-health-plus-focus-c71-source-review.md`. No canonical promotion or gain claim.

### Generated-map loss nominations and bounded Band route witness

The preserved 77 complete extracts nominate two failures for further diagnosis, not a
representative loss-rate estimate. On Band102305906 physical A, Heart of Ruin remains at
full health but deals no damage and earns no gold over 965 rounds. He reverses repeatedly
near a narrow corridor, then stops moving after round514. His only saved end-turn rollover
is round1; persistent fuel exhaustion does not explain the visible standstill. The selected
farm goal, live action allowances and routing branch are absent from these snapshots.
Nearby intact group62 does not itself prove that attacking it was affordable or legal.

On Archipelago102306013 physical B, Willow casts three heals totaling740 versus the
opponent's thirteen totaling4018. All three candidate casts are deficit-limited below the
current cap, so more Focus would not enlarge those exact heals. The replay establishes
less delivered service, not a missed legal heal or a particular hidden routing decision.
See `willow-4db-v33-generated-loss-nominations.md` for pinned frame and actor evidence.

Isolated diagnostic source `46ab555f` adds cached-value logging to canonical4db's bot.cpp
and pathing.cpp for physical A actor2, rounds17–22. It records selected work and actual
route outcomes without a new native/model/field query. Full29-file snapshots, manifests,
patch and checkpoint are in `provenance/willow-band-hor-routing-trace-20261023-v1/`.
It remains unbuilt: source review and a validated recorder/trace prefix are required before
using its output to attribute the frozen game's branches. Canonical remains unchanged.

### Current-upstream Willow item activation diagnostics

Eight new Release/default100k games compare isolated ae184 Focus and279d Health+Focus to
frozen releasedv33 on four preselected map/physical-side cells: Cells102306611 A,
Archipelago102306009 A, and Archipelago102306002 A/B. Controls are the existing4db games;
they were selected for completed Willow Bruiser Strength, not randomly sampled. Ae184 wins
3/4,279d2/4,4db1/4. These are activation/behavior diagnostics, not general strength evidence.

Ae184 starts a Bruiser Focus build in all four cells: first observed item deltas occur at
rounds363,564,694 and668 respectively. The last is a completed emblem appearing within one
inventory update; emblems cannot be bought directly. Source review establishes that the new
override is Willow's only initial Bruiser Focus source: main_stat remains Strength, while
begun-item logic only completes existing shards. The policy therefore activates, although
the snapshots do not expose every evaluated quote or the exact API purchase sequence.

At each pair's common horizon, ae184 Willow healing changes10602.6→12200.4,
6480.6→4971.2,9357→9763 and4156→4338.9 HP. Cells adds one Willow death; healing capacity
alone is not a survival result. Completed recalls are8→7,16→18,9→9 and11→10. The other
hundreds of recall_start events include ordinary automatic stubs and are not completed trips.

Health+Focus starts Focus only on009 A, where both arms have matching extracted event paths.
Its other cells complete Jungle Health instead. On002 B it wins at806 while Willow's native
earned gold falls220 versus control958 at that horizon. This is not itself an economic
failure: candidate team score+held gems is1009 versus control887, and opponent capital is471
versus570. Willow healing rises2596→4667 and recalls fall9→7. On002 A at861 the team's
capital instead falls1011→813 while opposing capital rises653→858. Keep both outcomes to
study allocation and service tradeoffs; do not select a map-specific item policy from them.

Both arms have zero native BotError, caught action error and turn-order markers. Native
candidate/reference play rollovers are2/7 forae184 and3/1 for279d. Eight actual manifests,
physical orders, outputs, tool/map/source/build pins and post-run rehashes are under
`replays/willow-item-activation-eight-cell-20261023-v1/run01/`. The final audit record is
`selected-activation-final-audit-v1.json`(SHA256
`cdb9d59b3fb5fbb3aafe5830bd7224cea357fbb580b1660d50457423d1b11125`);
the corrected common-horizon report isv2. V1 and its helper remain preserved. Inventory
deltas reconcile with native end-round state. No derived earned-gold validator is used.
Canonical remains4db; no release or promotion follows from these selected cases.

### Optional make-way ally lookup: isolated robustness source

Source candidate03aaf746 wraps only make_way's existing ally lookup and yield-priority
reads. Expected missing/hidden-ally errors98/97 check world staleness on the error path:
StaleTurn propagates; a current-turn failure invalidates local caches and declines the yield.
Unexpected errors propagate unchanged. Successful-path imports and short-circuit comparison
are preserved, without new normal-path queries or a fuel gate. Exception layout may still
change compiled fuel. Full29-file snapshots/manifest/patch/checkpoint are in
`provenance/willow-make-way-missing-ally-20261023-v1/`. It is unbuilt and is not an attribution
or verified fix for the Labyrinth caught error. See the corresponding source review.

### Next compound candidate and support witness

Unnumbered source9b405b0d combines only exactae184 Focus and exact03aaf make-way handling
on4db. Both full29-file removal proofs reproduce the independent arms byte for byte.
Its own full paired comparison againstv33 is being prepared; the eight Focus-only games
cannot be reused for this new source. Full snapshots, manifests and patch are in
`provenance/willow-focus-safe-yield-20261023-v1/`. It remains unbuilt and unsubmitted.

Archipelago's post-clear analysis also finds that Willow stays near full-health Prism
through139–145. Her heal only becomes ready139, and nearby injured Marcella has already
committed to recall while capturing. This does not establish missing service from separation.
Existing zero-gain formation can reset its four-turn limit on productive work or movement
toward a matching claim; useful prepositioning must be distinguished from unjustified resets.
Diagnostic06ea3ac2 logs this existing decision seam for WillowB/handle8/r139–146 without
new native/model/route queries. Source-only snapshots/manifests/patch are under
`provenance/willow-archipelago-service-trace-20261023-v1/`; it is unbuilt and unqualified as
a witness. See `willow-archipelago-post-clear-service-review.md`. No formation policy change
is selected from the current snapshots.

### Band routing witness: qualified rounds 17–22

The 46ab diagnostic now has a qualified bounded trace. Original, recorder and trace match
through round22 on 527 inputs, 23 state hashes and six phase-aware rollovers. All66 trace
segments match recorder counts/hashes, with no harness mismatch in that window. The
recorder preserves full-game actions/state and all play-turn fuel; its first draft turn
uses eight additional fuel. It is not wholly fuel-exact.

Actor2 selects group31/claim31, centre(46,42), in every recorded turn. In rounds17–20
the live attack and adjacent searches reach their depth caps without finding a route;
these are bounded search failures, not proof of unreachability. In round20 the cached
approach descends (11,32)63→(11,31)62. Round21's live attack route instead moves back
to(11,32), labelled48 steps from its goals; round22's live search fails and the cached
approach returns to(11,31). The selected group stays fixed, but that does not establish
identical goal/obstacle boards. Visibility-dependent live occupancy versus remembered
camp occupancy is under investigation; the nearby native camp is not proven to be the
selected economic target.

Both recorder and trace stdout hit the default1MiB cap. Recorder history ends near148;
the trace's first later harness mismatch is148, first action mismatch149 and first
state-hash mismatch150. Its later result is not gameplay evidence. No rerun was needed
for the qualified window. The preserved report, validation and post-run pins are in
`replays/willow-band-hor-routing-witness-20261023-v1/phase3-trace/`. Canonical remains4db.

The separate9b compound versus frozenv33 full1104 preflight is ready, with552 maps and
explicitly reversed physical A/B orders. Run-manifest SHA256 is
`cfafbb2c0eac4a1ae24057111980834e3991b4a099f4eda8254fde0b07fc640e`.
It has not built or run. Incoming live-loss analysis has the single heavy worker first.

### Fresh public losses and controls: October 23 evening

The incoming-loss review freezes150 ranked history rows and seven replay identities,
with five new extracts, two actor-own windows and a full native status audit of those
seven. Latest50 are26–24 versus55–45 in the previous100, with changing maps/sides and
unknown submitted executables. One0–5 Claudus group uniquely uses our Willow-first
drafts; its sampled Lanes game has no recorded draft rollover/error. Opponent adaptation
is not established. Both sides' submission IDs remain unavailable through the CLI.
See `incoming-loss-adaptation-review-20261023-v1.md` for exact inventory and limitations.

Farm's Prism806 sees a24HP awake Elk within legal basic range while holding280 gems.
His chosen movement takes lethal126 camp damage. Killing that member and staying
reduces the known next camp-phase bound to84<120HP; a different nearby step also has
a nonlethal known camp bound. This motivates immediate-survival precedence over exit
burden, followed by a separate emergency basic-kill option. It does not establish a
whole escape, safe bank or live source branch. Retention remains economically useful:
Prism supplies66% of team camp damage, with420 Focus from the carried280 gems.

Corners' inspected Willow death is pursuit by an already-visible Vendetta, without a
demonstrated late escape. Monolith loses despite10–0 kills and comparable camp damage;
enemy Vesper captures the256-gem boss twice. BigWorld's win has the same zero-gold Willow
pattern as the earlier loss, while Vesper's output is much higher. These are distinct
decision/allocation questions, not evidence for blanket Willow or Prism-retention removal.
Own native play rollovers total56 across the seven selected games, with no recorded own
BotError; public opponent zero counts are unavailable/redacted, not a clean-runtime result.

After the bounded replay work released the worker,9b's fresh Release build passed and
its reviewed full1104 comparison began. Raw artifact SHA256 is
`735adcd4437ddbee2492a90971659c3e4b7b9089ebd2185e57fa3a432ef1d2fc`;
injected SHA256 is`2edf180d24cff911c9918f23c0dc4722b856f558d4538c9e9c01e64a3c5e94dd`.
Source, reference artifacts and all552 map pins match preflight. Results remain pending.

### Source candidates from the incoming survival review

Primary1a1ee8e changes only flee_camps on canonical4db. It retains the immediate damage
bound from the existing current-plus-eight-position pass. When any evaluated option is
lethal, it tries the saved nonlethal neighbors in existing exit-cost/home order, with
bounded retries and stale checks. It holds only after those steps are unavailable and
staying survives. All-nonlethal cases preserve the original selection/fallback; all-lethal
cases retain the ordinary fallback. This avoids a new general preference for waiting at
an exit-cost local minimum. Native guard/reveal uncertainty remains; surviving one phase
does not prove eventual escape.

Separate child3d18ab0 adds a Prism-only basic when all evaluated movement and staying
are lethal. It certifies a currently visible, killable, already-awake damaging member
and its bounded harmful group, subtracts only its actual charged Safety contribution,
and requires the resulting stay bound below native HP and the selected movement bound.
All other camp/enemy terms stay unchanged. It never treats a ranged basic as compatible
with walking. Source review passes after stale-read corrections; neither arm is built
or runtime-qualified. Farm806 may activate walking alone, not this narrower basic arm.
Full29-file snapshots, patches and contracts are in
`provenance/willow-flee-survival-20261023-v1/`; see its source review.

Band diagnostic28e64f extends frozen46ab with paused raw bitboard chunks, source/native
member mapping and actual route-cache reasons forA/actor2/r20–22. Source review confirms
no extra gameplay observations, reordered predicates or forced lazy guard. Runtime prefix
equivalence must be re-established;46ab's earlier qualification does not transfer. Full
snapshots/patches are in`provenance/willow-band-hor-routing-masks-20261023-v1/`.

The fresh Monolith review reconciles earlier rejected local-crew work. Claudus's Vesper
uses solo attrition with a heal trip, then separately clears harmless members. Our actor's
lower health/output and unknown local admission rule prevent copying that job directly.
The prior single-station crew arm had zero admissions and first failed member coverage;
it is not being rerun unchanged. See`claudus-monolith-allocation-review-20261024-v1.md`.

### Next bounded runtime checks and source attribution

The survival runtime preflight selects six existing 4db games with an actual own Prism
death to a camp, then pairs both source arms against the same frozen v33, map and physical
side. These twelve games are activation/progress diagnostics, not a strength sample.
`provenance/willow-flee-survival-runtime-preflight-20261024-v4/` pins the full manifest,
control replay hashes and normal SDK/toolchain. Its original execution addendum omitted
`--release` on explicit builds; preserved v2 corrects both commands before any runtime.
The run command also explicitly uses Release and 100000 fuel. Runtime remains queued
behind the 9b full comparison and its audits; no source or artifact promotion has occurred.

The separate read-only `willow-4db-v33-upstream-regression-seams-20261024-v1.md` identifies
the actual eleven-file delta from released v33. Willow formation, draft, ordinary farm
affordability and shopping are unchanged. It ranks queue/guard scheduling attribution,
an exact demand-driven ward query, and unseen-threat geometry for later investigation.
The panel's generated-map deficit is not evidence for a map-name selector or a blanket
rollback. Existing failed optimizations and high-fuel equivalence limits remain recorded.

### Incoming loss follow-up through 02:31 UTC

`incoming-loss-followup-20261024-v1.md` freezes the next25 ranked games (15–10) and
separately records295 new UR rows, whose repeated requests are not an independent
strength sample. Four native CLI summaries and replay hashes nominate Fracture versus
:3, Starvation versus procless, and the P/V/HoR Gold Rush mirror versus prism best girl,
with Expanse/procless as a productive-Willow control. Both live submissions remain unknown.
The same-map/side/draft prior Starvation loss and Expanse win recur; adaptation is unproven.

The loss mechanisms differ. Starvation has14524 Willow healing but repeated Prism deaths
and all102 collected gems lost. Gold Rush has enemy Vesper6796 gold versus our292 and a
deathless enemy Prism who retains then banks836 in one winning tribute. Fracture's deathless
Prism holds242, but even full team scored+held474 falls far short of1026. The Expanse win
has independent Willow income1238 and143 gems collected/banked. These summaries reject
blanket more-healing, earlier-banking, or permanent-follow prescriptions; they do not yet
certify actor-known alternatives. Twenty-nine bounded actor turns are queued for local
visibility/readiness review after the current benchmark worker is released.

The first Gold Rush window is amended to Vesper1/A rounds10–24, making the first
three-window pass33 turns. The summary shows our Vesper clearing groups at13 and17,
our HoR receiving one reward at19 and enemy Vesper the other at23. Combat starts18.
This nominates capture ownership and the clear-to-combat transition; it does not prove
that staying or contesting was locally safe. The later154–164 request is preserved.

### Astraeus upstream freeze and pending Focus audit

Fetched upstream e72724a without merging into canonical4db during its child's audit.
The new Astraeus tree is identical to315910d; its29-file source aggregate is
`57f6908fcac310582d5b02606d8742c76c10a57f3a871c6a09792af115289369`.
Frozen source and untouched build control are `bots/baselines/astraeus-e72724a` and
`bots/variants/willow-astraeus-e727-work`; complete before/after receipts are in
`provenance/astraeus-e72724a-freeze-20261024-v1/`. They are not yet built here.

Upstream's v44 baseline matches all29 released Khaos_v33 source files. Its reported
1104-game Astraeus result versus that source is52.8%, with a49.9–55.7% interval and
3133/5334 candidate/reference OOF turns. This verifies baseline source identity, not
their build/run manifest or today's live submission. See `astraeus-integration-review-
20261024-v1.md` and its separate identity receipt. Astraeus consolidates Willow danger
and movement scheduling; shopping, camp-escape ordering, farm pathing and mixed-Monolith
admission remain distinct unresolved mechanisms.

The local9b Focus-plus-optional-make-way compound completed all1104 scheduled games
against frozenv33 at518–586, versus its4db parent's524–580 on the same panel. This is
not an overall improvement. The completed full-state audit records4344 candidate play
rollovers (A2247/B2097) versus5186 reference, with zero native BotError in all phases.
Caught-action and turn-order audits are both clean across1104; source,552 maps,
artifacts,CLI,engine and SDK postpins pass. Whole-match rollover totals are not a
paired per-turn fuel comparison. No source is promoted or release submitted.
Exact map/side pairing leaves1094 outcomes unchanged, with2 loss-to-win and8
win-to-loss changes. All10 changed cells are statically verified five-pick maps;
this is map eligibility, not a directly observed roster or purchase-activation audit.

### Incoming own-view decisions and new-base survival review

The next ranked-only intake after02:31:39.616Z contains15 games,12–3, all our physicalA.
All opponent ordered drafts recur in the prior175 rows. Ambush repeats a same-side,
same-draft Claudus loss. This does not establish adaptation or source stability; see
`incoming-loss-followup-20261024-v2.md`.

The three public own-view exports completed33 normal actor turns with pinned inputs
and explicitly unknown live source. Gold Rush Vesper trades at(17,15) while the enemy
occupies gold group2 at(17,18). Reaching(17,16) from his r18 origin requires both dash
and walk, sacrificing a basic; direct dash is out of range. This nominates an economic
movement comparison, not a free capture or proven safe counterplay. Current source's
gold contest omissions and search action constraints are mapped separately.

Starvation shows Prism taking repeated adjacent Vendetta hits, then retreating, with
Willow's ready heal and in-range position failing to coincide in the inspected window.
It nominates support availability, not a proved missed heal. Fracture Willow heals
Marcella then retreats under camp attrition/pursuit. At648 she cancels and restarts a
recall without another recorded successful action, losing channel progress. Hidden-
blocker attempts or observation gains may be absent from that action export, so an
avoidable restart is not established; neither is a saved death. See
`incoming-loss-own-view-review-20261024-v1.md` for every inspected turn.

Independent source review passes for the exact Astraeus survival-first9b1fd50 and
emergency-basic8878fff ports. The helper subtracts the same charged camp contribution
under the new SafetyBound accounting, while upstream111/112 and support paths remain.
They remain unbuilt and need fresh activation; old4db outcomes cannot transfer.

### Survival diagnostics completed; economic search under review

The twelve Release/100k survival diagnostics completed with no runner failures, and
compact native, caught-action, turn-order and post-pin checks passed. Both the primary
survival-first arm and its emergency-basic child went 3–3 on the six selected cells,
matching the reused 4db controls' aggregate result. Their decoded events and round
states match each other on all six cells: there is no observed effect unique to the
emergency-basic addition. This is not proof that a particular internal branch ran.

Compared with the six controls, each arm has13 team camp deaths versus16,61 carried
gems lost to camps versus117, and4220 banked versus3928. Prism camp deaths are4 versus6.
The Caves114, Blob339 and Cells603/61 deaths persist; Archipelago has a new Prism
camp death at172. The late Cells615 death does not recur because the candidates win
at1082, before the control's1860 death. These selected-cell observations support
further diagnosis, not a competitive improvement claim. Full extraction receipts and
paired windows are in `provenance/willow-flee-survival-runtime-preflight-20261024-v4/`,
with `survival-activation-diagnostics-v4.json` the corrected derived report. No control
was rerun or re-extracted.

The first Astraeus economic-terminal implementation offers bounded non-strike movement
to currently observed, cleared gold groups, with a matching cached price quote and
ordinary combat/safety competition. Independent source review requests two changes
before build: avoid temporary full-map bitboards during group qualification, and retain
signed progress toward an unrelated farm objective rather than erasing real detour
cost. See `willow-astraeus-gold-contest-terminal-source-review-20261024-v1.md`.
It remains isolated, unbuilt and unqualified.

The Band mask diagnostic passed original replay-prefix equivalence through round22.
All62 decoded mask records match the qualified trace hashes. Native camp100/group62
at(13,33) is present in the live camp obstacle board at20, absent at21, and present
again at22, while the bot retains the earlier observation. The movement oscillation
coincides with different live-route and cached-approach paths. Causal review is checking
their exact goal and wall semantics before selecting a correction; later trace output
is not qualified by this prefix comparison.

### Latest ranked intake, upstream Willow fixes and ward fuel check

The ranked intake through03:40:12.979Z adds20 games,8–12. Fifteen use the normal
Prism-first draft and go8–7. The five Univardisty games all use anomalous Willow-first
drafts and go0–5; two own drafts exactly repeat earlier same-map/side Claudus anomalies.
Several normal-draft wins and losses also repeat prior map/side/draft comparisons.
This does not establish opponent adaptation. The Gemfight draft prefix has eight
Input/Draft-champion pairs and no recorded draft rollover, BotError or End-turn;
that sequence alone does not identify the submission or prove explicit-versus-automatic
pick provenance. See `incoming-loss-followup-20261024-v3.md` and its preserved inputs.

Fetched cb61eaa, which adds upstream Astraeus Willow visibility/readiness corrections
and cost reductions after e72724a. The exact29-file freeze and untouched control have
aggregate `369742e3f54259c675c0d4b508a02c0c4517eef6e1cb3ef6f42fa776194180ea`.
Upstream reports52/52 cost-only replay equivalence and pooled51.5% of600 for the later
logic changes; these are upstream reports, not our independently reproduced results.
The local source review finds no blocker, while Band pathing and economic-search
mechanisms remain separate. See `willow-astraeus-cb61eaa-source-review-20261024-v1.md`.

The isolated ward-demand v2 optimization completed16/16 own-draft games at100M
diagnostic fuel against the fixed Fish-roster emulator. Every native replay payload
is byte-identical to the paired4db control. Draft and first-round fuel are identical,
but play fuel rises1,286,959 over3,933,913,698 control fuel across83,835 samples;
turns above100k rise564→567 and nearest-rank p99 rises94,378→94,531. This version
does not deliver the intended fuel improvement and is not promoted.

Two tooling issues were reconciled without rerunning games: the preflight initially
compared whole-ZIP hashes to recorded inner-payload hashes (all16 payload pins match),
and the adapter failed serializing tuple-keyed ledger data after saving all16 results.
Source/tool/map/artifact and unique-command reconciliation passes; the failed exit
and a separate future adapter repair are preserved. Authoritative receipts are
`provenance/willow-ward-demand-viewers-20261024-v2/candidate16-postflight-recovered-v2.json`
and `candidate16-fuel-tail-summary-v1.json`. No normal-fuel strength claim follows.

### Upstream Astraeus integrated; isolated mechanism checks

Commit `c5ad40f` merges cb61eaa. Canonical `bots/astraeus` is the exact 29-file
upstream source 369742e3; canonical Hyperion is the exact 28-file upstream source
f2229059. The old4db source and every candidate remain frozen separately. Source
and SDK diffs against cb61eaa are empty. Earlier test results in this log still
belong to their named source snapshots; they are not results for new Astraeus.

The first control build failed before compilation because the host clock was
earlier than source/CMake timestamps, causing repeated Ninja regeneration. Its
logs and unchanged source snapshots are preserved. A fresh isolated workspace
copies identical bytes with current copy timestamps; the system clock and original
source timestamps are unchanged. Five sequential Release builds then succeeded.
The rebuilt frozen v33 matches both its recorded raw and injected WASM hashes.
See `provenance/willow-astraeus-clock-recovery-20261024-v1/build-postflight.json`.

Source reviews pass for the remembered-camp farm-route overlay and corrected
gold-occupancy terminal v2. The route overlay uses current native occupancy plus
remembered living camps outside current native vision; visible empty tiles remove
only that remembered contribution. Gold v2 avoids temporary group bitboards and
retains signed progress toward unrelated objectives. Both remain isolated.

Seven source-known Release games are authorized at explicit 100k fuel, jobs 1:
cb61 control and route candidate on Band 102305906 A; the route candidate on old4db
on the same cell; cb61 control and Gold v2 on Gold Rush, both physical sides.
The existing unpatched4db Band replay is reused only as an eighth comparison
record. These are mechanism checks for useful departure and economic continuation,
not a seven-game strength or release threshold.

All seven games completed once with no runner failures. Every side has zero native
BotError, zero caught-action errors and no turn-order errors. Play fuel rollovers
remain separate from those checks. Source and raw/injected artifact pins are
unchanged. The existing event extractor processed exactly the seven new replays
with one thread in23 seconds, with no hard or soft validation errors; the old4db
control was reused without another decode.

The Band route candidate turns the formerly idle HoR into a productive farmer:
664 earned gold, 200 gems collected and banked, and12,416.79 camp damage, versus
zero for that champion in cb61 control. The first changed move is at13; the
candidate attacks a camp at37, captures group30 at136 and tributes at141. Team
banking rises236→429, though both lose (control939, candidate928). The old4db route
candidate has the same observed output; its reused unpatched control loses at965.
This demonstrates useful departure from the stall, not a competitive win.

On Gold Rush, cb61 control loses A704–913 at2000 and wins B1007–280 at1707.
Gold v2 wins A1001–176 at1439 and loses B363–1001 at1830. The first accepted
action differences are HoR's landing at14 on A and Vesper's dash at25 on B.
The latter begins a gold hold but abandons it before payout. The enemy captures
the group at31 in control (HoR receives100 gold), versus39 in v2 (Vesper receives133
gold); delay and the different recipient bonus must be assessed separately. These
outcomes nominate continuation and commitment
analysis; they do not establish a net strength gain or prove that the extra
no-strike terminal, rather than an ordinary leaf's occupancy credit, was selected.

### Broader route comparison and latest upstream

The remembered-camp route comparison completed 112 matched physical-side cells
per arm against frozen v33: both cb61 control and route candidate finish 57–55.
There are seven wins gained, seven lost, 50 shared wins and 48 shared losses.
Coverage is all 40 published maps plus eight generated families from each of two
existing suites. It deliberately includes the known Band witness and is diagnostic
regression coverage, not independent held-out confirmation. Of 224 comparison
records, 220 are new games and four reuse pinned Band/Gold Rush mechanism runs.
All fresh games completed with zero native BotError, caught-action errors or
turn-order errors. Native play rollovers remain; the fresh-arm totals have unequal
109/111-game denominators and are not a paired fuel-overhead estimate. Selected
Band B and Starvation A losses and Yellow Brick Road A gain are under causal review.
The route fix remains isolated pending that review; a level win count does not
invalidate its demonstrated useful departure from the Band A stall.

Merge `a564c25` incorporates upstream `f7d54e9`. Canonical Astraeus now has aggregate
`f475b8521cada611754076822402a266c43be8de76ce0f2b504b268ff3335824`; Hyperion and SDK
are unchanged. Four added lines let stationary Prism use an available basic attack
while waiting for Willow: an enemy first, otherwise a harmless camp. The frozen
cb61 experiment arms are unchanged. Upstream reports 49.5% of 600 and 52/52 wide
replays identical, with 31 branch entries but no attack target; these are upstream
reports and do not exercise successful attacks. Source review finds no interface
collision. A nonlethal Ren retaliation can still cost HP despite consuming no walk
or cast; that is a narrow future fixture, not an observed regression or a new policy.

The next isolated Willow arm values observed marginal ally healing in the shopper's
existing recovery-round units, alongside lost own farming and recovery cost. It
preserves the first Treasure policy and prices later full and partial purchases
consistently. The current 60% heal-efficiency threshold is replayed, including cases
where more Focus suppresses a previously worthwhile heal. See
`willow-cb61-service-shopper-design-20261024-v2.md`. No new release was submitted.

The three selected route pairs now have bounded actor-view review. Band B's first
changed route avoids a reversal and reaches the same 28-gem payout at145 instead
of153, despite the later loss. On Starvation A, the route variant's Vesper has no
accepted first-turn action and a native fuel rollover, while control moves from
(2,48) to(3,49) with the same known starting state. This precedes the subsequent
formation difference; it does not establish which computation exhausted fuel or
prove the eventual loss's cause. Yellow Brick Road A delegates the remaining wolf
damage to visible allies and moves a round earlier, with the camp still dying that
round; the bounded window does not establish additional production or win causality.
See `willow-route-panel-review-20261024-v1.md`.

Source review finds no safe small cache substitution for the route's fresh occupancy
and vision reads. A separate two-line child replaces SDK `bitboard::set` wrappers
inside the existing live-camp board update with the identical `sdk_Bitboard_Set`
call through the existing inline `set_tile` helper. Inputs, error handling and camp
tracking remain unchanged. Child aggregate `1b4928c91330e2ddfa615cc70cbb52f9879124a5b62f66085e4c93af56eb2f6f`
is preserved with all29 files before/after; no saving is claimed before measurement.

Independent source review passes for the service-aware Willow shopper prototype
`effae506` and its mechanically ported f7 child `730051ef`. Only the upstream four
Prism lines differ between those candidate identities. The first runtime panel pairs
the f7 child with exact f7 baseline `f475b852` against frozen v33 on four previously
selected service cells plus Gold Rush A/B no-Willow controls: twelve new games.
Both sides of that comparison include the same upstream Prism change. Source review
does not establish activation, improved team conversion or fuel equivalence.

The twelve f7 service-panel games completed before the user's compute pause; no
games were repeated. A subsequent low-duty bundle/stdout audit reports base3/6
versus service2/6. Cells102306611 A changes from a base win at875 to a service
loss at891. The other five cells retain winner and duration. Four pairs have
identical inner replay payloads (Archipelago102306009 A, Archipelago102306002 B,
and Gold Rush A/B); Archipelago102306002 A also changes payload while retaining
its loss at830. All twelve stdout audits have zero caught-action and turn-order
markers. These are not native phase-status audits, and aggregate fuel summaries
are not a causal cost comparison once play differs. No purchase activation or
healing benefit is claimed yet. Evidence:
`../provenance/willow-service-lowcpu-audit-20261024-v1/service-panel-light-audit.json`.
Only the two differing pairs are selected for further extraction, with one worker,
low priority and deliberate process duty cycling under the user's CPU constraint.

The source-known Gold Rush base diagnostic faithfully reproduces Vesper's farm /
retreat reversal through round43. However, the first proposed initiative explanation
used an incorrect melee reach formula for ranged Vesper. Her ready dash plus basic
already reaches distance5 in one activation, so the farm destination at distance5
was already within the current scalar strike bound. The proposed4-to5 admission
boundary is retracted; no projected-timing gameplay change is justified by that
argument. Terrain-aware reach, guard short-circuits, fuel admission and fight results
remain to be distinguished using existing computed values. Gold v2's round30 trace
is perturbed by a fuel rollover and cannot identify the original continuation branch.

### Bounded service and wrapper follow-up (2026-10-24)

The service-panel audit now has native and actor-aligned evidence; use
`willow-service-panel-activation-review-20261024-v1.md` and the corrected
`service-panel-light-audit-v2.json`, not the initial per-row winner placeholders.
The six paired cells remain base3/6 versus service2/6. In Cells A, Willow's first
accepted-action difference is the round411 recall approach; both builds have
identical items through round405 and no Focus purchase is observed. Prospective
shop values can affect decisions before a purchase, so this does not establish
non-activation. Archipelago002 A first differs at Willow's round5 ward placement.
These are candidates for decision/fuel attribution, not proof that more healing
or a different item stat would repair the losses. The shopper remains isolated.

The live-camp board-write wrapper child `1b4928c9` completed its four authorized
games under one worker with a 10% active-duty schedule. At 100M fuel its Starvation
A replay payload is identical to the route parent (`8b4e15938a7d553e…6743e7`);
both lose at round1771. Each first champion turn costs54 additional fuel, and
later play differs by only1086 total fuel over8850 turns. The child's normal100k
Starvation A and Band A payloads also equal the preserved parent controls.
All four native, caught-action and turn-order audits pass. This wrapper offers
no demonstrated strength or fuel benefit and is not promoted. Receipts are in
`../provenance/willow-astraeus-livecamp-write-child-runtime-20261024-v1/`.

### Latest Astraeus and Mite investigation (2026-10-24)

Fetched upstream `dc9867a` explicitly labels frozen v47 as live Astraeus f7d54e9.
Its source tree is identical to f7; the intervening changes regenerate map suites
and update tooling. The normal five-pick roster remains Prism, Vesper, Marcella,
Willow, Heart of Ruin, also the effective v44 roster. Local v44 is source-identical
to released Khaos_v33/a00fff. Upstream's latest f7-versus-cb61 report is49.5%/600,
which does not establish a regression or gain. See
`astraeus-v47-upstream-regression-review-20261024-v1.md`.

Fresh authenticated history at05:50:47Z exposes no submission version IDs. The
user subsequently identified the unusual Willow-first batches as ladder
manipulation and instructed us to ignore them. They are excluded from the
regression analysis, and the pooled100-game result is not an Astraeus estimate.
Normal Prism-first drafts in the60 newer rows are17–13. Restricting to normal
five-pick drafts, newest25 are14–11 versus18–8 in the earlier26 of this100-game
window; their schedules differ. This warrants replay inspection, not a
version-attributed rollback. Two exact map/side/both-draft win-to-loss pairs are
selected: Fish Elkring B and :3 Pilgrimage A. Historical generated map names must
not be pooled across the newly changed seeds1025/1026.

Mite's separately frozen latest50 ranked rows are36–14, predominantly drafting
Vesper, Vendetta, Ryth, Tavi and Marcella. Its uploaded revision is likewise
unknown. Six wins/losses were selected across Elkring, Big World, Corridors and
Lanes for economic and actor-visible decision analysis. Both investigations use
existing CLI/replay tooling, one decoder with low active duty, and no browser,
new games or submission. Raw metadata and selection context are preserved in
`../provenance/astraeus-regression-history-intake-20261024-v1/` and
`../provenance/mite-ladder-history-intake-20261024-v1/`.

Ten replay extracts and nine bounded actor/action windows now complete this
investigation. Both normal-draft matched cells first diverge on our accepted
actions, but identical exported observations do not establish identical private
state or uploaded source. Own native rollovers fall2→0 on Elkring and2→1 on
Pilgrimage; both pairs have zero native BotErrors and caught-action errors. These
losses do not show a new whole-game fuel collapse. On Pilgrimage, the shared
88-gem group12 accounts for the dominant economic reversal at common horizon1403:
own capture gems440→88 and opponent176→704. More total Willow healing did not
preserve that objective. Her death770 follows damage from a bush-hidden Vesper;
her inspected turns763–769 contain no visible enemy, so this is not evidence
that she ignored a visible ready attacker. See
`astraeus-normal-five-pick-matched-review-20261024-v1.md`.

Elkring supplies a narrower source experiment. At161 Willow makes the same move
in both games, but the newer game spends reset for55 damage. Current priority
arithmetic then drops her from14 to−41, losing useful even-round escape slots.
The observed Ryth cannot hit immediately from distance3; the concern is pursuit
and subsequent contact. Candidate `willow-contact-priority-f7-work`, aggregate
`8e535de8da12fde3b5d2c0b03edb275790539b2a867f86cf985ed554ec44c2e7`,
adds a recall-only floor13 when it actually improves the projected alternating
schedule against an already-acted, fresh, visible, known-unstunned enemy. Higher
Wish priorities remain unchanged. Conservative camp lifecycle checks avoid
stealing aggro through a priority tie. Independent final source review passes;
the prototype has not yet been built or measured, and its admission in the
public replay's unavailable private state is unknown. A small paired normal-fuel
panel against frozen v33 is assigned to the sole low-duty runtime worker.

Mite's Big World loss retains a gold lead (8494 versus6861 final) and contains
no champion deaths on Mite's side. The opponent's Marcella captures a mixed
Monolith group for228 gems at971 and banks them at1033, following a damaged-boss
sortie, paid recall/heal trip, return, and separate harmless cleanup. Mite does
not take that group in either the matched-map win or loss. Canonical Astraeus
also excludes live non-sealing mixed Monoliths from ordinary farm/siege admission.
This supports an isolated phased-work experiment, not a generic aggression or
counterdraft change. Source planning must use current actor stats, legal spell
and basic schedules, a safe exit, the complete paid healing/return cycle, and
normal alternative farm values. No private Mite source or repeatable counter
win rate is claimed. See `mite-observable-counter-review-20261024-v1.md` and
`mite-phased-boss-source-design-20261024-v1.md`.

The nine actor windows and compact manifests retain exact match, payload and
engine identities under `../provenance/ladder-history-replays-20261024-v1/`.
Use `bigworld-pair-macro-notes-v4.md`: earlier v3 incorrectly called971 the bank
time and overcounted successive camp hits. Raw bundles and compressed extracts
remain preserved separately. No candidate has been promoted or submitted.

### Contact-priority diagnostic panel and phased-work implementation (2026-10-24)

The contact candidate `8e535de8` builds in Release; reconstructed f7 parent and
frozen v33 binaries match their previous raw/injected hashes. Both candidate and
parent beat v33 on Elkring B at786 and Pilgrimage A at1358. Candidate Gold Rush A
loses at2000, matching the existing exact f7 control, which was reused. All three
comparisons have identical inner `replay.repl26a` bytes, as well as identical
extracted event/round JSON. Selected-map candidate/parent native play rollovers
are0/0, while v33 has6 across the two maps; Gold Rush has1 candidate and15 v33.
Native BotErrors are zero. These are small diagnostic results, not evidence of
strength or a release threshold.

No living end-round Willow priority13 is observed in either selected map.
Round-end sampling alone cannot exclude a write followed by death, so a follow-up
native step-header audit and separate raw-payload equality check are retained.
The identical complete replay payloads show no observable policy change in this
panel. The initial Python order fixture checks independent schedule examples,
not production admission; its first equivalent-expression assertion was
identified and corrected. Next is an exact-source helper fixture with declared
mocked dependencies and one bounded gate-rejection trace, rather than a larger
win-rate panel. The broad group-range camp guard can conservatively overreject,
but these results do not yet identify it as the binding condition. Evidence is
in `../provenance/willow-contact-priority-f7-20261024-v1/` and
`willow-contact-priority-nonactivation-diagnostic-20261024-v1.md`.

The separate phased boss implementation is now a Marcella-only one-heal-trip
prototype under source review. A fresh active-job escape certificate may override
the generic35% health heuristic only while that job owns the work/exit action;
ordinary work and enemy danger retain their original retreat policy. This permits
testing the observed4100HP mechanism instead of requiring an artificial5200HP
state. The plan review also fixes the remote HP expiry bound: another actor can
kill and hold later in the observation round, so use `last_live_round +
settings.capture_time + respawn`, without the ordinary cycle helper's extra turn.
Source checks still need to settle cached action state, cleanup, return and cycle
reset behavior before any build or performance claim.

The contact follow-up now compiles and calls the unchanged production helper
bodies against declared mock observations. Its positive case and negative cases
pass; SDK observation acquisition and the outer dispatch remain outside that
fixture. One bounded Elkring trace records channel, schedule and distance
rejections, with no sampled camp rejection. Its full replay payload and native
step-header sequence equal the Release replay, so no observable trace
perturbation was found. The shared runtime source and Release binaries were
restored and match their pins. A final two-game Elkring B comparison against
frozen Hyperion `4c4eacc` is underway: its native draft includes Ryth, unlike
the newer v33 opponent. This tests the motivating pursuer without altering
the opponent or treating it as a model of Mite. See the fixture receipt and
`diagnostic/DIAGNOSTIC-v1.md` under the contact provenance directory.

Phased boss source v3 is independently approved for build and focused mechanism
tests, aggregate `b4a7d993fa954e459b89e21e25fc52834ba6574f29d5ad60528c2fbc861a0f95`.
Review corrected an own-camp threat veto, return cooldown timing, interference
from generic passing attacks, incomplete certificate-cache inputs and cycle
reconciliation. A failed return move now refreshes observation before any
second attempt. Immutable v1/v2/v3 patches and manifests preserve each change.
There is still no runtime evidence of a completed heal-return-capture cycle,
affordable fuel or improved match results. The same sole throttled worker will
build this candidate after the contact pair. See
`willow-phased-solo-boss-f7-source-checkpoint.md` and the final pinned verdict in
`willow-phased-solo-boss-f7-source-review-20261024-v2.md`.

The user reconfirmed that Willow-first batches are ladder manipulation. They
remain excluded from all active regression comparisons; no investigation of
their implementation is needed. Canonical Astraeus and the deployed bot remain
unchanged.

### Contact arm closed; latest upstream intake (2026-10-24, 07:15 UTC)

The final frozen `4c4eacc` Elkring B pair also produces identical candidate and
f7-parent payloads: both win at round 798, with zero native rollovers or bot
errors on either side. Its native Ryth draft therefore adds no observed match
activation or benefit. Both traces include the same priority-write record
targeting 13 with the actor already dead in the immediately following state;
this must not be reported as a live contact-policy activation. The source-bound
positive fixture is useful unit evidence, not a competitive result. Local bots'
frequent end-turn recall stubs also limit these opponents' coverage of the
public non-channeling pursuit situation. The arm is preserved without promotion.
The closed 28-file compact artifact list is
`../provenance/willow-contact-priority-f7-20261024-v1/diagnostic/contact-artifact-manifest.json`.

Phased boss f7 v3 builds successfully in Release with the unchanged shared SDK
and throttled worker. Raw/injected WASM hashes are
`be6f385b31ea75cfe8512e0d430c26a97049d6220c5a09a30438e1447e400dfa` /
`3aede28b85a52f0e489df91e1ad7de326c40ccf2fd0e1bc8a22557af16a37017`.
No boss runtime game has yet run. The receipt is
`../provenance/willow-phased-solo-boss-f7-20261024-v1/build-receipt.json`.

Fetched upstream `4d08241123b88ad0365d4b0ad346cd65a329b699` after the earlier
`dc9867a` inspection. Four small Astraeus fixes change shield/Durability spell
pricing, dash-aware altar distance, capture-holder coordination for allies bound
elsewhere, and mid-turn killed-enemy observations. Upstream reports sequential
1,104-game results of 50.1%, 51.6%, 50.1% and 50.0%; these are Alex's recorded
results, not reruns here. A separate source-only boss port is being prepared
against this latest baseline. Frozen f7 candidates, canonical sources and the
completed comparisons remain intact.

The new upstream replay harness supports v47 and a versioned trace bot. Its
reported exact reruns are not proof that our selected public losses use f7.
One selected Pilgrimage loss may be rerun against its recorded opponent actions
to establish the exact prefix, then traced only within that prefix. This would
explain Willow's post-heal step using actual private beliefs and farm/support
branches. No whole-manifest pipeline or browser rendering is planned.

### Latest-base boss qualification and missing destination (2026-10-24)

The independently reviewed latest-base child `0b777e56` and exact parent
`f599a31f` both build in Release. Two ordinary-100k Big World games put each on
physical B against frozen v33 on A, with identical native five-pick drafts.
Parent loses at 780 with 474 tributed gems; child loses at 975 with 748. Each
game has three B-side and four A-side play rollovers, with zero native bot
errors or draft/other-phase rollovers. Neither game attacks either Monolith,
clears either mixed boss group, or captures one. The extra duration and gems
therefore do not demonstrate the intended boss mechanism.

Across the existing Marcella snapshots, minimum Chebyshev distance to any
member of groups 16/17 is 7 for parent and 13 for child. At 900 the child has
4,200 HP, 500 Strength and 315 Focus, but stays distant. Its actual inventory
has Durability, Treasure and Jungle passives; it does not have Monster. The
local candidate only considers nearby groups and a current/one-step working
station, while ordinary farm excludes Monoliths. This arm needs an economic
destination and approach before its local work can be exercised. Exact
inventories, output identities and native audits are in
`../provenance/willow-phased-solo-boss-4d08241-v1/PAIR-RESULT.md`.

The separate source-bound arithmetic fixture passes on the recorded opponent
Marcella capacity snapshot: 4,100 HP, 290 Strength, 120 Focus and
Monster/Jungle/Durability. Unchanged production sortie/cooldown helpers leave
8,736 boss HP after 28 first-visit activations, then finish in 22 after the paid
return's entry cost. Moving-cast and reserve boundaries pass too. This host C++
fixture mocks observations and does not test native selection, routes, cycle
state, fuel or conversion. It must not replace the real candidate's inventory
in any game claim. See `fixture/FIXTURE-RESULT.md` in that provenance directory.

Static map review found another admission restriction: the two Big World
Monoliths are at (48,48) and (51,51), each with range 5. Every melee station next
to one lies in the other's raw range. The current helper rejects overlapping
positive-strength camps even when the other is asleep, so routing alone would
not admit this map. The next isolated design separates provisional travel from
local work and uses fresh neighboring camp state before entering its hazard.
Long-distance fields can retain a conservative static board; the local corridor
and its safe exit need compatible geometry. No future hidden enemy action is
claimed impossible. The approach and state-aware overlap corrections remain
design work, with no new runtime or promotion yet.

The preserved actor-visible Big World window confirms this is an available-info
case: rounds 850–854 show neighboring camp 56/group 17 at full health and asleep,
while target camp 57/group 16 is awake. The actor can read both. These IDs and
states come from `actor-window-bigworld-boss-v1/big-world-loss-marcella6-r850-859.json`;
its camp positions use the actor's coordinate frame and must not be mixed with
the raw-map coordinates above. The amended design now has a separate isolated
implementation underway; the completed runtime sources stay frozen.

The bounded Mite combat audit finds existing handling for visible spent mobility,
low HP, kill/bag value and stun order. Future enemy neutral-phase damage is not
credited, but the available Mite-own-view windows do not establish a missed kill
by our bot. No generic combat patch follows from that observation alone. The
one-match Pilgrimage v47 harness is being prepared in an isolated checkout;
release reproduction must establish its trusted prefix before private decision
traces can explain the selected public loss.

The selected Pilgrimage loss `62589f4b-d504-4bf7-b641-f3e9de95ce9c`
now reproduces exactly with the isolated v47 Release harness: all 54,155 action
inputs and 1,404 round hashes match, including the round-1403 result and
392–1,035 score. The recorder also reproduces those inputs, hashes and result.
Its original-replay fuel comparison differs only on draft turn zero by 55;
all 7,023 later measurements match. The separate original-versus-Release fuel
comparison and full artifact identities remain for the final receipt. This
establishes behavioral reproduction of this loss, not uploaded-source identity.
A level-2 trace is now limited to Willow's rounds 763–769 and must preserve the
trusted prefix before its private branch records are interpreted.

The completed harness receipt confirms Release fuel equals all 7,028 original
measurements. The recorder's sole difference is draft measurement 8 (+55);
its one rollover is separate from its zero `@x` records. The trace reproduces
that rollover and matches all 7,019 segments, full inputs, round hashes and
result. Original versus rerun replay bytes differ, so these are semantic and
fuel comparisons, not a raw-payload identity claim. The normalized production
source aggregate is the existing f7 pin; the generated diagnostic source has
its own manifest. Corrected receipts preserve the earlier path-dependent hash
and rollover-label mistakes without rerunning any game.

Willow's rounds 763–769 consistently use the ordinary `farm` movement site,
canceling and restarting the normal recall stub. Round 769 also heals Marcella.
This confirms the action branch; the enemy beliefs and message arbitration are
being interpreted separately before proposing a gameplay correction. See
`../provenance/willow-pilgrimage-fuel-harness-v1/RESULT.md` and its compact
preservation manifest.

A metadata-only CLI refresh at approximately 07:59 UTC finds 17–13 in the latest
30 own ranked matches, including 15–11 across 26 five-pick games. All own drafts
start with Prism; no Willow-first batch is counted. Changing schedules and
unavailable submission IDs still prevent attributing these totals to a source
regression. The Mite refresh failed with HTTP 429 and one delayed HTTP 503, so
the prior saved replay sample remains its evidence. No new replay extraction
or simulation was performed for this refresh. Raw responses and command details
are in `../provenance/astraeus-regression-history-refresh-20261024-v2/`.

The trusted trace resolves the Willow goal more specifically: she selected
group 12 as help for Marcella's claimed camp, with shared value 1.753 versus
the best independent group's 0.214 at round 769. No support formation or retreat
branch owns that step. Her older communicated Vesper fix remains dated 762;
Marcella directly observes newer Vesper positions at 765 and 766, but current
HoR sightings occupy the shared slot. At 765 the HoR enemy/position/health
payload repeats the one Marcella received at 764. The source preserves any
fresh current-round sighting, preventing publication of the local contact.

This supports a separate duplicate-sighting arbitration experiment. It does
not prove which unseen-threat cutoff admitted Willow's step, nor that a newer
fix guarantees survival or objective control. The first design allows one
fresh, locally relevant replacement while protecting important information,
using existing moved-observation permission and a bounded publication protocol.
See `willow-pilgrimage-trusted-trace-sighting-design-20261024-v1.md` for exact
trace/source references, available information and protocol tradeoffs.

The separate macro boss approach v2 is source-ready at aggregate
`fbbdabd00d4726d36feb4c6bb87475d2e4fc9a1b118bcf59a4a577da9c3a275f`.
It adds one cached remote economic quote, funded movement-only probing and
fresh local inactive-neighbor checks, without a provisional work certificate
or below-35-percent exception. An immutable Release compile runs while the
independent source review proceeds. No game or benefit is claimed yet; source
and cost bounds are in the dated approach checkpoint.

Approach v2 then compiled and passed the bounded independent source review, but
the one normal-100k Big World B game exposed a severe fuel regression. Frozen
v33 wins at 975, with final A/B gems 1,005/677. Candidate B has 175 native play
rollovers, 172 on Marcella; the earlier parent and boss-only candidate each had
three B-side rollovers. Both sides have zero native bot errors; v33 has four
play rollovers. Neither boss group is approached, attacked, cleared or captured.
Marcella's nearest group-17 tile remains 13 steps away. The inner payload differs
from both earlier games despite sharing the boss-only candidate's end round.
This arm is held for cost diagnosis and optimization, with no admission or
safety weakening and no release. See
`../provenance/willow-phased-boss-approach-4d08241-v1/RUN-RESULT.md`.

The separate sighting-arbitration implementation is frozen at v3 aggregate
`a439a6c2d1d1d2ef1004f3a463b243d1f48d2daa65eada801d83f55c5c17a2df`.
Source review caught a missed-reader generation-alias case; v3 preserves any
nonempty current-parity report for a nonconsecutive reader, rather than allowing
extra normal publications. It also checks current ally vision and confirms the
selected enemy's live native record before packing a replacement. The wire size
and unrelated fields stay unchanged. Final review, compile, protocol fixture
and native behavior checks remain separate from source completion.

The trusted claim follow-up does not justify expanding this patch: Marcella's
766 retreat was not represented by the emitted claim slot, whose owner is not
printed, but she genuinely resumed group-12 farming at 767. Willow's 766 help
field was unset, and help resumed only at 768–769. That transient transport
limitation does not establish stale commitment as the cause of the fatal step.

Independent sighting-v3 review is now complete with no remaining source blocker;
the missed-reader and post-move visibility corrections are included in the
verified pin. A Release build and small production-bound protocol fixture are
next. Boss cost review identifies repeated replacement of the one cached
whole-map exit field as a plausible expensive path when alternate quotes fail;
this is a source-supported hypothesis, not yet a measured profile attribution.
The proposed optimization preserves live prices and eligibility while reusing
immutable static-wall/exit fields. No further boss game has run.

Sighting v3's Release build succeeds with the frozen source aggregate and
unchanged SDK hash and timestamp. Its first host fixture passes its assertions,
but independent review finds that three assertions do not yet establish the
claimed cases: the Vesper mock overstates real reach, missed-reader coverage
never calls the publication path, and the repeated send is independently blocked
by unchanged payload equality. A narrow fixture revision is queued; this is a
test-evidence correction, not a new production-source defect. The first native
comparison uses the entire new-protocol team on Pilgrimage A against frozen v33,
paired with the exact latest parent rather than the older f7 baseline.

The successful 08:29 UTC Mite metadata refresh is 19–11 in 30 ranked games and
13–8 in 21 five-pick games. Its three ordered drafts match the prior sample;
the four exact repeated opponent/map/side/draft cells preserve their earlier
outcomes. These changing schedules and unavailable submission IDs do not prove
adaptation or regression. Only Big World B loss
`67f9d74a-673e-4b9a-936a-688c75632a0b` against :3 is nominated and downloaded for
later decoding. It reverses Mite's side and changes the opponent relative to the
earlier boss-loss witness, so it will be a mechanism comparison. No Willow-first
ladder-manipulation batch is included.

The first latest-parent/sighting-v3 native pair is complete. On Pilgrimage A
against frozen v33, both win 1,030–210 at round 1,358 with matching native drafts.
Both own teams have zero play rollovers and zero native errors; v33 B has six
play rollovers and zero errors in each. Draft/other phase failures are zero.
The inner replay hashes differ, and the first semantic difference is still
being classified. This cell does not demonstrate a match-strength gain. No
additional game is inferred from the passing host assertions or shared result.

The first decoded divergence is Prism0 at round 1,183. Both cancel the recall
stub; the candidate moves from (13,39) to (12,38) and restarts recall, whereas
the parent restarts in place and takes that same step a round later. Subsequent
paths differ, but both start the same 141-gem tribute at 1,311 and complete it
at 1,326. Final Prism economy/combat totals match. Public decoded records do not
expose the private message/guard chain; a source-pinned paired trace would be
needed to distinguish the intended information effect from computation-cost
effects. No claim of replay equivalence, zero effect or realized benefit follows.

The boss cost design separates physical static-field reuse from logical route
admission. A cache hit must preserve the existing `cold_round` switch check and
failed-preparation pointer semantics. The altar field depends on the current
open-goal signature under fixed walls, not the selected exit; a home field must
be keyed by exact exit, since two groups can yield more than two endpoints.
See `willow-phased-boss-route-cache-design-20261024-v1.md`. No optimization or
measured saving is claimed at this checkpoint.

The communications fixture is now independently reviewed through revision 3.
It uses the real Vesper geometry, explicitly seeds an unchanged aliased record
with zero freshness before a missed-reader send, and challenges the replacement
marker with a changed same-enemy native payload. Thirteen scenarios pass. Each
of two test-only guard removals fails its intended assertion; production source
is unchanged. Earlier inadequate fixture revisions and their reviews remain
preserved. This closes the three targeted host-test gaps, not native scheduling
or strength validation.

The newly decoded Mite Big World B loss ends 1,009–614 at round 906. It has no
champion combat damage, no damage to either Monolith, and no boss capture.
Captured gems are 1,049 versus 692; endpoint bags are 40 versus 78. The 357-gem
capture deficit plus 38 extra unbanked gems explains the 395-point loss. The
winning side repeatedly converts ordinary groups that Mite scarcely uses,
including pure gems, and completes 20 teleports versus none for Mite. That is
an observed routing/economic difference, not an isolated teleport effect or
proof of source identity. Mite has 51 native play rollovers, its opponent 343,
and neither has native bot errors. This replay does not repeat the earlier
two-visit boss mechanism.

A separate audit of the existing exact latest-parent Big World B control finds
a different failure. Its actual score is 1,110–474 at round 780; earlier root
shorthand mixed the opponent score with the candidate game. The bundle hash is
`15a703f86fd6cbf7ca9b14fddc9136f2100bc5afce87520905b274c82cbe670c`,
while its inner payload remains the recorded `0022ca3c...`. Captures are only
828 versus 756, but enemy kills transfer 21 gems from HoR and 261 from Prism;
both stolen bags are banked. The final 636-point gap equals the 72-gem capture
gap plus twice the 282 transferred gems. Prism cancels a Home recall with one
turn left at 738 before dying at 744. One bounded actor-known view, Prism5
rounds 735–744, is nominated to establish the information available at that
cancellation before changing recall or banking policy.

That own-view now confirms both visible pursuers were six tiles away at Prism's
738 cancellation. Vesper had a five-turn dash cooldown, and both enemies had
already acted that round; before Prism's next activation they could each act
only once. Neither visible enemy could interrupt the remaining one-turn recall
with those facts, even after cancelling its own recall stub. This is a bound on
the visible pair, not a proof about unseen enemy beliefs or camps. The source
hypothesis is a `paying_soon` relaxation of pursuit in `want_home`, followed by
`capture_recall` refusing departure before payout. A fresh isolated exact-4d
Release reproduction is authorized before a narrow private branch trace;
the older v47/f7 source is not being substituted.

The reviewed altar-cache child `5c47f2fc...` compiles with unchanged SDK bytes
and timestamp. Its one ordinary-100k Big World B game against frozen v33 ends
1,005–662 at 975 with 177 candidate play rollovers (174 Marcella), versus the
approach control's 1,005–677 and 175 (172 Marcella). Both have zero bot errors;
v33 has four play rollovers. No boss is attacked or captured. The payloads
differ, and the cache has no demonstrated rollover benefit. It remains isolated
while the concrete Prism recall failure takes priority; no additional boss
run is authorized by these results.

The isolated `local-parent-bigworld-f599` Release reproduction now matches all
28,990 inputs, 781 round hashes and the round-780 1,110–474 result. Physical-B
fuel matches all 3,913 original measurements, including the nominated Prism
turns. Both original fuel streams are preserved; this local key has no inferred
official submission identity. Recorder and narrow branch-trace validation are
the next separate steps.

The recorder subsequently reproduces all inputs, round hashes and the result;
one physical-B fuel measurement differs by 719 for actor9 at round25. Its
`@r=3`/`@x=1` instrumentation counts are separate from native turn rollovers.
The corrected puppet-A/tracer-B prefix is exact through round738: 27,690 input
records and 739 round-start hashes, with zero wrapper mismatch reports and
738 actor5 yield checks. Seven native rollovers (three B, none Prism5) match.
The successful trace used the one-job batch runner with a recorded 10% duty
cycle. An earlier wrong-side trace and its process-control failure are retained
but excluded; that failed invocation has no valid throttling receipt.

The private branch confirms the proposed cause: round737 has pack=true and
paying_soon=false, so home=true and the existing safe-channel checks keep the
recall. At738 pack remains true but paying_soon becomes true; home becomes
false after the zero-pursuit stand evaluation. Its home-keep safety checks are
skipped. The capture helper then finds an unthreatened square, held_since734,
payout740 and channel1, and rejects arrival739 before payout740. An isolated
gameplay correction is now being implemented: carry the already-evaluated
suppressed-pack fact into a contextual recall keep, preserving interception
checks, cached normal home, game-ending intervention and the existing winning
capture-share classification. No additional combat simulation is proposed.

The reviewed correction is frozen as aggregate `781fe364...`; only bot.cpp
changes. Its source-bound host fixture extracts the actual outmatched,
want_home and continue_recall functions and passes 11 decision cases plus
scalar initialization checks. Five test-only mutations are caught by their
intended cases after two sensitivity checks were corrected. The canonical
capture helper's keep is preserved when arrival is not early; failed new keeps
leave cached home=false. Safety, native reads and capture-share/tribute
accounting are explicit mocks, so this establishes branch behavior rather than
native integration or ally-accounting correctness. Independent source and
fixture reviews find no remaining blocker. One ordinary-100k reactive Big
World candidate-B versus frozen-v33-A game is authorized against the existing
parent control, using the one-job duty-capped batch runner.

That native test reaches the intended decision without earlier action drift:
the first differing input is index27,683, Prism5 at round738/step163689,
parent Cancel channel versus candidate End turn. The 739 round-start hashes
for rounds0–738 match; the next state differs at739 when the candidate recall
completes. Candidate raw/injected WASM are `9aab0533...`/`e7f63a94...`; the
source and SDK pins remain unchanged. Candidate B still loses, 588–1,014 at877,
with the same three play rollovers and zero native errors (v33 A four/zero).
Prism has no rollover or error, survives with287 gems, and has no champion
damage dealt or received. The former261-gem death does not occur.

This validates the targeted behavior without establishing a general win-rate
gain. The remaining426-point gap is105 ordinary-capture difference
(A1030/B925),42 from the existing21-gem HoR transfer, and279 from ending bags
(B316/A37). Prism retaining287 is not itself proof of a missed winning bank:
even all B bags plus score total904. Existing events also show retained Prism
clearing camps that Vesper subsequently captures. Broader source-fix checks
are three serial games: parent/candidate A versus frozen v33 B on Big World,
then candidate A versus v33 B on Pilgrimage using the already-saved parent
control. No additional private trace or live unranked is queued.

The component union is separately frozen as `29ac1251...`: exact recall
bot.cpp plus exact reviewed sighting-v3 comms.cpp/h, with the other26 files
unchanged from f599. Independent integration review finds no source blocker.
Fresher delivered enemy beliefs can legitimately change pack/recall decisions
and their cost, so component checks are not being treated as combined runtime
proof. Two combined games are authorized next, Big World B and Pilgrimage A
against frozen v33 with existing component/parent controls, after the current
recall-extension receipts are complete.

The three recall-extension runs are complete. On Big World A, parent and
recall candidate both win1,000–757 at953 with identical35,585-input replays and
954 matching round hashes; own native status is3 rollovers/0 errors, opponent
8/0. On Pilgrimage A, the recall candidate exactly matches the saved parent's
51,803 inputs and1,359 round hashes, winning1,030–210 at1358 with own0/0 and
opponent6/0. Prism banks510 on Big World and141 on Pilgrimage, survives and
ends empty in both. Source/binary/SDK pins remain unchanged. Thus these two
additional cells show no observable gameplay drift, while the earlier
Big World B witness changes precisely at the intended recall decision.
