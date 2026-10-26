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
  `wants_crystal` is set every spawn visit rebuys one before shards; bank hops do not check the landing.
- Stampede: Prism spell-kites a 7480-hp group alone at one AoE a cooldown (~750 rounds to clear).

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

## Fuel

Where fuel goes: [FUEL-PROFILE.md](hyperion/FUEL-PROFILE.md) (59% of out-of-fuel turns ran out in the strike search,
18% in farm; 44% are replays that run out again).

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
  No real-budget OOF gain claimed; no Hyperion changes. Details, artifacts, and untested structural
  ideas: [FUEL-IDEAS-2026-10-23.md](hyperion/FUEL-IDEAS-2026-10-23.md).
