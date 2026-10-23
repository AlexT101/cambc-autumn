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
