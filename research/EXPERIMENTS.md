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

