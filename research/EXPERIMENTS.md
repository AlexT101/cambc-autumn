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

## Fuel

Where fuel goes: [FUEL-PROFILE.md](hyperion/FUEL-PROFILE.md) (59% of out-of-fuel turns ran out in the strike search,
18% in farm; 44% are replays that run out again).

- Fuel-only changes (byte-identical at 100M) still reroute real-budget games (savings 47.5%, a control burning 2k a turn
  48.4%): judge them by fuel and out-of-fuel turns, not win rate. Out-of-fuel totals swing by hundreds on three or four
  long fights (gen-chambers, gen-hourglass); count them on the full suite.
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

## Willow / Prism and Vesper economy (2026-10-23, in progress)

Continues from upstream `15949893c123578c47a8c7bea530f25c7a641336` in the isolated
`willow-prism-development` checkout. Canonical `bots/hyperion/src` is unchanged. Frozen baseline
`bots/baselines/hyperion-upstream-1594989` source aggregate is
`eb4829b9aca06271e2c754435c400a5f21b2534745cd0373de29a2c8b707b02c`.
Aggregates here use `shasum -a 256 src/* | shasum -a 256` from the bot directory.

- Vesper's passive applies to her received gold, including her capture share; camp last-hit is not ownership of
  the payout. Treasure adds 20 percentage points to her 33% passive (153% total), once across emblem stats.
  Its five-shard stats compete with Power's six-shard stats and other emblem effects. Source details and frozen
  experimental arms: [willow-vesper-source-checkpoints.md](willow-vesper-source-checkpoints.md).
- Gold-value-only arm `3fedfa68dbfc7c9b882f7cf28b75db945765cb178e152e7cb9d297975efece8e` prices the actual
  bonus once in farm and incoming-shopping estimates, preserving the original passing-camp predicate. Release
  eight-game diagnostic against frozen upstream: **5–3**, native fuel-rollover statuses **11 vs 4**, bot errors
  **0 vs 0**. This is mechanism screening, not evidence of a competitive gain.
- Forced Willow diagnostic source `f64390194580c826727f61f5bed7b5a0a87a8e049dd0d54e53effc4b5f778569`
  uses Prism/Willow/Heart of Ruin for three picks, and replaces Ryth/Vendetta with Willow for five picks.
  Initial eight games were **Debug**, 5–3; preserve them as diagnostics. Explicit **Release** rerun: **7–1**,
  native fuel-rollover statuses **11 vs 14**, bot errors **0 vs 0**. No four-pick map in these samples.
- Both Release runs use the same four maps with exchanged sides: packs, road-of-riches, lanes, broken-curve.
  CLI 3.0.5, engine 1.0.3, default fuel, one match/build worker, nice 19. Runner now has explicit `--release`
  for both build and run-batch. Exact pins are in `replays/willow-prism-upstream-forced/pins.json`; results and
  native status counts are in each batch's `diagnostic-summary.json`.
- Gold/Treasure/capture bundle `bots/willow-vesper-cache-fixtures-v1`, source
  `f71154064f1b2073ffa17391be4519d33f1a0af17710cf19e60f1942b3fcda9b`, adds Treasure Strength first after
  existing partial purchases, and yields safe gold-only captures only to an eligible Vesper already present.
  A Vesper-only shard inventory stamp invalidates cached next-family/remaining-cost quotes after purchases;
  turn-start numeric World stats are unchanged. Host fixtures exercise production helper arithmetic, cache
  key transitions and holder predicate exclusions. They do not establish native capture actions. Release eight-game
  diagnostic against gold-value-only: **4–4**, native rollovers **6 vs 4**, no bot errors. Descriptive team totals
  over those eight games: capture-share gold **41,213 vs 30,693**, submitted gems **6,963 vs 5,228**, deaths
  **22 vs 39**. Vesper earned gold **21,070 vs 10,089**; her engine Treasure bonus counter summed to **2,546**.
  Both sides play the same match durations, but the bundle changes several policies: these totals do not isolate
  Treasure's causal effect. One Treasure Strength completed per Vesper; first completion ranged from round 29
  (packs) to 317 (lanes). Road's two bonus counters were only 42 and 8. Next: assess timing and broader maps.
  Per-game result, shop conversion events and economic pins: `replays/willow-vesper-cache-fixtures-v1/`.
- Willow support source checkpoint `523a2e3f92e072699e661b19cad11470f172e10ddf444d615ad6802559878411`
  remains untested natively. Design: [willow-prism-coordination-theory.md](willow-prism-coordination-theory.md).
  Local formation and recovery must retain actual-health safety, finite waiting and capture/banking priorities;
  short-lived request/availability messages are not promised healing. Own-view replay windows are being audited
  for target eligibility and pre-action alignment; global end-of-round proximity is not proof of a missed heal.
  Independent review fixed counters that were committed after post-move observation, allowing fuel suspension to
  lose a support decision, and stopped changing camp claims from renewing the idle budget. The reviewed mailbox
  fixture child `76d937cba19b7d230d27b18902c58829cf171c43dd09039c84e4d0cbcabcfb8d` factors the same protocol
  into production-used pure helpers; pending host fixtures and a ten-game Release check including four-pick hooks.
  Corrected Broken-curve diagnostic: round 12 HoR has 880/1000 HP, below the existing 216-HP useful-heal threshold
  for a 360-HP heal. Its timer-4 recall is a provisional stub, not a kept recall. This is not a missed-heal example.
- Willow mailbox host fixtures passed on the production helper. Same-roster Release ten-game diagnostic
  (`replays/willow-prism-support-fixtures-v1/batch-run-02-release-pinned-cli`): **4–6**, native extracted fuel
  rollovers **10 vs 24**, no bot errors; 3/4/5-pick branches all verified. Candidate/reference: submitted score
  **5,852 vs 7,782**, Willow deaths **18 vs 15**, Prism deaths **12 vs 10**, useful healing **75,056.8 vs 67,335.5**.
  More healing did not establish better play. Road lost both sides with no Prism deaths; Packs A lost 60–1000
  with five deaths each on Willow and Prism. Review those decisions before another support patch. A prior attempt
  resolved the old PATH CLI and failed all builds before any games; preserved separately as `batch-run-01-release`.
  Runner and A/B now accept explicit `--cli` and fingerprint the actual executable before building.
- The unchanged Vesper bundle (`f7115406…`) versus frozen upstream completed the full 40-map published ladder,
  both physical sides: **41–39**, zero match errors. Native replay audit: play fuel rollovers **256 vs 232**,
  no bot errors and no draft rollovers. All 80 replays extracted with one worker. Batch, native audit and exact
  pins: `replays/willow-vesper-cache-fixtures-v1/batch-run-02-release-full-ladder/`. This is a near-even published-map
  result, not yet a demonstrated general gain. Next is the existing 256-map `maps/gen` seed-1023 pool, both sides,
  unchanged source and Release/default-fuel runtime.
- That unchanged Vesper bundle completed all **512** seed-1023 generated-map games: **271–241**, zero run errors.
  Native replay audit reports **1,205 vs 1,121** play fuel rollovers, zero bot errors, zero draft/other statuses.
  Published plus this generated pool totals **312–280** over 592 games; the
  seed-1024 pool and fresh held-out confirmation remain. Preserve this batch as
  `replays/willow-vesper-cache-fixtures-v1/batch-run-03-release-gen256-seed1023/`.
- The unchanged bundle completed the second 256-map pool (`maps/gen-s1`, seed 1024), both sides: **260–252**,
  zero run errors. The complete 1,104-game qualification totals **572–532 (51.8%)**. Native audit found **1,200 vs
  1,148** play fuel rollovers in this pool, no bot errors and no draft/other statuses. Across all 1,104 games,
  play rollovers are **2,661 vs 2,501**; match-path changes also affect these totals, so they do not isolate added
  instruction cost. Fresh confirmation is authorized on the complete
  generated seed-2026102307 suite, with unchanged sources and no map/result-based selection, after the queued
  Willow diagnostic checks. This small aggregate lead is not yet a confirmed improvement.
- Own-view support follow-up: Road A rounds 26–29 show Willow taking no actions while heal cooldown ticks
  7 to 4 after her round-25 heal. Visible Prism is missing 180 HP, below the current 216 useful-heal threshold.
  Packs A round 122 shows Willow moving toward visible HoR, then resetting and attacking before the subsequent
  burst; the replay does not prove which internal support-controller gate declined ownership. The next child
  will require productive cooldown formation and enforce Willow's local safety independently of pair availability
  and formation timeout, including safe-current to unsafe-neighbor moves. Captures, banking and necessary
  shopping must select economic actions inside that safety rule, rather than fall through to generic offense.
- Reviewed support successor `bots/variants/willow-prism-productive-safety-work` is frozen at
  **`c5dfe2044d884d8dfe1dd4211835b0face525f7c0edd06857b715c2a253a78f7`**. It changes only `bot.cpp` and `plan.cpp`
  from `76d937…`. Cooldown formation needs actual stationary damage or descent along an already-built matching
  ordinary route. Independent Willow standoff and the ordinary walk guard cover known enemy exposure; strict
  camp-range exclusion remains local to formation/recovery, while ordinary affordable camp work remains intact.
  Protected captures retain original stationary camp output, and P/B/S/R ownership keeps the original recall
  stub/continuation economics. Explicit winning/last-chance immediate tributes retain their old priority.
  Banking safety was checked: its idle simulation uses only the stationary recipient, with no imaginary allied
  healing. Existing crystal-hop selection is unchanged; the new guard is not a universal teleport safety claim.
  Next is the same forced-roster ten-game Release panel against `f6439019…`; source review is not outcome evidence.
- The `c5dfe…` ten-game panel completed **4–6**, submitted score **6,290 vs 7,834**, Willow deaths **23 vs 14**,
  effective healing **60,369 vs 71,183**, and native rollovers **75 vs 17**, with no bot errors. All actual rosters
  and replay validations passed. Against the prior support arm's separate same-panel run, candidate Willow deaths
  rose 18 to 23 while candidate all-champion deaths fell 61 to 53. Its 75 rollovers are Willow 45, HoR 24, Prism 6;
  the prior arm's 10 were all HoR. Willow's new rollovers concentrate in Lanes (21) and Road (23), but both
  Broken Curve losses have zero rollovers, so fuel is not a complete explanation. Exact productive-only
  (`7dbdc49aa16737e0edae9a14d1f5a8c26ce2197575bb613bf4b5b076cd249a5a`) and standoff-only
  (`6ea9549525855978170369434a775dd298225a3e13a8986af4074447340cf899`) source ablations are frozen for diagnostics.
  The standoff arm intentionally preserves the tested behavior, including a confirmed macro scope expansion:
  any positive Willow bag now directly routes to an altar, bypassing original `carry_bag` safe small-bag chaining.
  Both old and new support controllers already excluded such bags from formation; the new difference is forced
  economic routing and action-tail ownership, not a newly added formation exclusion. Repair and optimize before
  widening support qualification. See `replays/willow-prism-productive-safety-v1/batch-run-01-release-pinned-cli/`.
- Literal ablations completed the same forced-roster ten-game Release panel. Cooldown-only `7dbdc49a…`:
  **4–6**, submitted score **5,335 vs 7,887**, native rollovers **10 vs 7**, Willow deaths **15 vs 10**, Prism
  deaths **8 vs 15**, effective healing **69,086 vs 60,899**. Standoff-only `6ea95495…`: **6–4**, submitted
  score **7,191 vs 7,106**, rollovers **42 vs 9**, Willow deaths **24 vs 18**, Prism deaths **3 vs 9**, effective
  healing **55,734 vs 63,572**. Both have zero bot/match errors and validated 3/4/5-pick rosters. These narrow
  diagnostics expose tradeoffs and interaction; they neither select a general draft nor establish competitive
  improvement. Pins and summaries are in `replays/willow-prism-{cooldown,standoff}-only/`. The healing verifier
  now allows the actual accumulated per-event rounding bound (0.05 per tenths-rounded event plus epsilon),
  rather than a fixed 0.1 across all casts; only summaries were rerun, not games.
- The local enemy prefilter `98945ff9ae0f35a8b749b0f00ed9088678af3eee7cab41600e2e4c6162a2f02b` passed source
  review: a whole-window Strike reach bound can skip the nine enemy queries only when none can hit, retaining
  all camp calculations. High-budget exact-replay and real-budget rollover checks are pending. Small-bag scope
  restoration `9ca5cbf7c2ca38f1101db8c9df6593a0aedf4d4c9c5a060c1d851c37462a2662` releases safe, nonclosing,
  chainable carriers away from an altar to original guarded `carry_bag`. An initial source-only gate on unused
  movement (`b247…`) was rejected in review because the post-decision recheck overwrote successful farming after
  a ranged walk/basic. Corrected release preserves completed farm state. Mechanical combined source
  `8b9c0291f1f3a73886d17c99ce1a1d373b9b50fb43f232665e776b2e564ac754` remains untested.
- Broken Curve has a repeated no-fuel-exhaustion escape plateau: Willow retreats to own-frame (10,10), then
  takes 42 elk damage per round without moving until dying (A rounds 275–281 and 369–375; mirrored B 273–279).
  Own-view windows confirm 238→196→154→112→70→28 HP, no visible enemy, no buff/stun, unspent movement flag,
  and repeated recall starts. Public walls block the direct home direction, while bush (10,9) ties current
  immediate exposure and Chebyshev home distance. The current-first comparator therefore stays. `can_move` and
  hidden blockers are not exposed by the replay API; the remedy is a better attempted route, not a claim of
  guaranteed movement. The new child `7569eb3c51f0994b6bce612907b7993b388718f8174caa83c6a78d0630479fc3`
  uses the existing cached home path field only after previous escape priorities tie, plus a stale-world check
  after ranking in case lazy field construction suspends. All risk priorities and station legality remain intact.
  This source-reviewed six-line change atop `8b9…` is pending native tests. Own-view files are under the c5dfe
  batch's `actor-windows/`; static camp-tile exclusion is a separate future limitation, unnecessary for this route.
- Prefilter `98945…` passed the Release high-budget benchmark against frozen forced-roster `f6439019…`:
  all **16/16 replay payloads byte-identical** to c5dfe on the default eight mixed maps, both sides, 100M fuel.
  Total fuel **3,146,740,841 → 3,051,226,848 (−3.04%)**, mean post-round-one turn **37,473 → 36,327**.
  Corrected real-budget Lanes/Road pairs went **2–2**, native rollovers **14 vs 8**, zero bot errors; the frozen
  c5dfe candidate had 59 rollovers on the matching four map/side/opponent games. Sources and map hashes match.
  An initial file named `default4-100k-release` accidentally retained bench.py's 100M default; its zero-rollover
  result is **not** a real-budget result and is excluded. The preserved `default4-100k-corrected-release` report
  explicitly records `fuel: 0` and no CLI fuel override. Reports and replay payloads are under `replays/fuel/`.
- Combined escape-route repair `7569eb3c…` completed ten Release/default-fuel games against frozen forced
  baseline: **4–6**, native rollovers **17 vs 10**, zero bot/match errors and zero draft/other statuses. The c5dfe
  same-panel run was 4–6 with 75 vs 17 rollovers. Detailed actor/economic extraction is pending; changed match
  trajectories mean this is not a pure instruction-cost comparison. Batch: `replays/willow-prism-escape-route/`.
- Full-ladder loss review separates candidate mechanisms from inherited behavior. Quadrants 035 has later
  Vesper Jungle/Power completion (373/475 versus reference 267/329) and less camp damage, but Vesper submits
  slightly more gems; delayed mitigation/output is plausible, not a complete explanation of the team loss.
  Boss Battle 053 has Vesper dying with 2,402 gems after acquiring that bag at round 1076. Corrected actor-view
  windows show a concrete recovery alternative at round 1099: 1,299/3,000 HP on (24,2), with public spawn tile
  (24,1) adjacent and unoccupied; she instead walks to (24,3). At round 1102 she walks toward visible Marcella
  and uses a nonlethal reset/attack despite Marcella's available 1,701-damage spell exceeding her current HP.
  The inherited 35% return threshold does not force recovery at 43.3%; the exact selected planner branch is not
  traced. This is a lead for adjacent-spawn recovery, not evidence against Treasure. Quadrants' exported post-shop
  windows are bank routes: both candidate and reference take 11 rounds from shopping to starting tribute;
  different channel durations match their different bag sizes. Rows 042's low personal Vesper receipts were **not** demonstrated lost
  team rewards: all 14 groups she finished were eventually captured by her team, 12 paid to allies, and the
  suspicious round-802 departure was a valid handoff to Marcella. Candidate Prism ends with 479 retained gems;
  team submitted-plus-carried is 972 versus reference 1,031. Final bags locate unscored resources but do not
  establish when an earlier safe tribute should have started. Keep Prism retention unchanged in these arms.

Pending Treasure timing hypothesis (Astra review; not implemented): keep the frozen unconditional bundle for
broader testing first. A later arm can start Treasure only when all five shards can be completed now, comparing
its immediate upkeep saving `sT` against the ordinary chooser's `sE`. Over the existing estimated useful-work
horizon `H`, require delayed bonus-funded upgrades to repay `max(0,sE-sT)*H`. Forecast base capture income only
from consecutive actor-observed start-gold minus previous-end-gold, divided by the pre-Treasure 1.33 multiplier;
exclude unobserved gaps and own-turn kill gold. At additional rate `q=0.20*base_income`, credit each of at most
five follow-up shards only after `shop_return_delay + 30*j/q`, using its real marginal upkeep saving and applying
emblem passives at completion. Both sides of the comparison are rounds saved. Do not charge the full 150 as
lost capital, recurse through `prices()`, or also credit future income in `Prices::per_gold`. This timing and income
forecast is a testable approximation, not evidence for excluding any named map.

- Fresh seed-2026102307 confirmation completed all **512** games: **261–251**, zero match errors. Across
  qualification and confirmation, the unchanged gold/Treasure bundle is **833–783 / 1,616 (51.55%)**.
  The compact native audit reports **873 vs 795** play rollovers, zero bot errors and zero draft/other statuses;
  aggregate native rollovers across all 1,616 games are **3,534 vs 3,296**. This is a modest positive result for
  the bundle, not an isolated Treasure effect or a precise win-rate estimate. Exact source, CLI, engine, maps,
  results and audit pins are in `replays/willow-vesper-cache-fixtures-v1/batch-run-05-release-heldout-seed-2026102307/`.
  The exact `f7115406…` source was released as **Khaos_v29 / server version 39** to Pantheon; Willow remains
  experimental. Canonical `bots/hyperion/src` now matches this qualified release. The numbered copy's raw and
  injected Release WASM both match the qualified candidate. Provenance: `provenance/Khaos_v29-release/`.
- Compact auditing was checked against full snapshots on four frozen c5dfe replays: **777,463 states** with no
  phase/kind/actor/team mismatch, including **61 native rollovers** and zero bot errors. The report's phase
  counters use step phases; its zero `finished` count does not establish terminal-header coverage. That reporting
  distinction is being corrected. The full auditor remains available. Reports are `timeline-v103-parity*.json`
  under `replays/willow-prism-productive-safety-v1/batch-run-01-release-pinned-cli/`.
- Detailed combined-Willow extraction gives **7,802 vs 7,744** submitted score, Willow deaths **23 vs 22**,
  Prism deaths **8 vs 16**, and effective healing **65,914 vs 63,837**. The mirrored Broken Curve plateau is
  repaired in the observed action sequence: Willow moves (9,10)→(10,9)→(11,8) on rounds 273–274 and completes
  recall at 279. The other side diverged earlier, so it is not a matched proof. Hooks B remains an investigation
  target, with repeated stationary turns under an elk despite nearby Prism farming.
- Own-view exporter audit found two defects in the v2 camp/terrain evidence: the vision helper received map data
  without bitboard `chunkStride`, and canonical-half map camp indexes were mixed with expanded snapshot camp
  IDs. Preserve those exports, but exclude their visibility flags and camp coordinates/state from actor-known
  reasoning until corrected v3 exports are available. Champion observations and action sequences are unaffected.
  No new camp policy is justified by the invalid fields.
- Corrected v3 windows use bitboard metadata and expanded camp IDs. A residual `alive:false` output field is
  invalid (the camp snapshot exposes no such field); the exporter now omits it, and the preserved v3 files have
  a sidecar warning. Positive known health and awake state are usable. Hooks B rounds 132–135 show Willow
  stationary at raw (16,22), losing 60 HP per camp phase. Raw (17,22) is a visible empty bush, farther from the
  visible awake elk at (14,20), while Prism occupies (17,23). Equal immediate exposure and equal static home
  distance make the existing current-first tie stay in place. Proposed narrow repair: after existing escape
  priorities tie, prefer lower sum of `strength * (reach + 1 - distance)` over the same awake/due-respawn
  damaging camp members already evaluated. This adds no threat queries or fields and does not borrow ally
  tanking. A separate `open_for_us` legality cleanup permits dead-camp transit during owned escape only; it is
  not the demonstrated cause of Hooks. Broken Curve shows known sleeping elks and no visible Prism, so do not
  predict Prism's later waking attack from global replay knowledge.
- Released Vesper source is committed as `b7a0c15` with provenance follow-up `ebde6c9`, draft PR #4. Two live
  five-game groups were queued through the CLI after server-v39 submission: Fish (`de021eba-2c48-4504-941e-d44520ce22e6`)
  on our A side and `:3` (`3f84cdf1-9f7a-44d0-a462-40cad108f6c0`) on our B side, on Expanse, Quadrants, Swirl,
  Boss Battle and Hooks. Fish finished **3–2** (wins Quadrants/Boss Battle/Hooks). These are live exploration,
  not fixed-submission benchmark results; confirm any exposed submission IDs before assigning exact source.
- The `:3` group finished **1–4**, so these two live groups total **4–6**. Both use engine 1.0.3; replay metadata
  does not expose a submission/version ID. Corrected physical-side audit gives **18 vs 688** native play rollovers,
  zero bot errors, zero draft/other statuses. Initial adapter reports inverted the sides; retain them as invalid and
  use `native-status-corrected-side-compact.json`, `analysis-fish-our-A/` and `analysis-cat-our-B/` only.
  Replay/action review shows Fish Swirl's initial Prism/Vendetta deaths at rounds 26/30 precede Vesper's first
  Treasure shard at 118, so that early collapse is not caused by the Treasure purchase. Cat Swirl has a low-HP
  Vesper attack/retreat lead at 169–170; public own-view windows are queued with source attribution explicitly
  unverified. Expanse's Vesper has zero deaths and banks all collected gems in both games; investigate throughput
  and allocation rather than infer a bag-loss problem from the final score.
- Reviewed clearance child `0eefb348590dfd66cd7d9eca13d13a909986a8365d44fd8d047db2be6c597642` completed the
  same ten-game Release/default-fuel panel against frozen forced Willow: **4–6**, score **6,482 vs 8,246**,
  Willow deaths **31 vs 20**, Prism deaths **14 vs 11**, useful healing **65,398 vs 73,082**, native rollovers
  **21 vs 8**, no bot errors. These are not aggregate improvements over the earlier route child. Hooks B's first
  Willow move difference is round 121: old (17,18)→(17,19), new→(18,19), both noncamp destinations. The old
  round-136 camp death is avoided; the new first death is round 201. An initial runtime note that actor 7 was
  already dead at 128–138 was an indexing mistake, superseded by Astra's actor-native extraction review.
  Review the changed failure mechanisms instead of discarding a logical fix on ten games.
- Gold integration is mechanical and separately frozen: forced control `08402461d2c240951a8e870b3971cd5611a95ba4c9f74e9ce76aa907990f85d1`,
  support route `7ac9ecba9d2d74cc7f9ca2e09494c475278ebcff17ad7e5f16ce2adfca33c5ef`, and clearance
  `5a669542453612ade136aa7aa80b85081c6bd226ef89e2a69d17333d5250ce3f`. The clearance-versus-control
  published-40 A/B80 finished **42–38**, with the same forced roster on both sides and the qualified gold bundle on
  both. Native play rollovers were **585 vs 215**, with zero bot/match errors and zero draft/other statuses.
  This tests support behavior; it does not establish that adding Willow improves the native draft. Results SHA
  `bbeb8c99e339a85a7e81afadd2eef594a3cd567970c1365f581441a7f87f58a0`, native audit SHA
  `8a65fad33a80420555f3759cd7fd163b0e10d73ed196b005e3f3fa4731a85076`; see
  `replays/willow-prism-gold-clearance/batch-run-01-release-published40/`. Willow rollovers concentrate on
  Yellow Brick (40/31, sides A/B) and Starfish (43/28), motivating exact cost work before broader qualification.
- The older clearance ten-game result metadata was accidentally relabelled with live-UR bot names while the UR
  adapter was being corrected. The original pre-mutation results byte hash is unavailable. The bad metadata,
  old audit and pins are preserved as dated snapshots; only the two bot labels were repaired from the original
  setup, manifest and run log. All remaining parsed results fields and replay payloads are unchanged. Corrected
  results SHA `15b171d7d3c269a0256f380aac85d1b542ad656ca5ed387214dd0e12cd2284a0` and the fresh
  `native-status-corrected-labels-compact.json` are bound by the active pins and `label-correction-note.md`.
  The alias-backed earlier own-view export remains labelled untrusted for source attribution. The gold A/B80
  was unaffected. Correctly pinned Hooks B actor-7 rounds 190–199 are in `actor-window-reviewed/` of the
  clearance batch; source identity comes from the repaired provenance, not invented aliases.
- Those Hooks turns separate capture holding at rounds 190–192 from subsequent retreat pauses. At 194 and
  199 Willow cancels recall without moving or restarting it; at 197 it retains the channel with visible pursuers.
  Own-view actions do not expose the selected branch or caught C++ exceptions. A narrow controller trace is
  needed before another movement patch. In particular, the banking recall branch lacks the chase-horizon
  check used by the preceding retreat branch, but its selection in this episode remains unproven.
- Source-only tile prefilter `67cfd58af9c4fee360fd5291d5702211a00e90342f45d619e4746c5307b0859b` adds a
  radius-zero conservative enemy-reach check per local station after the existing whole-neighborhood check.
  It retains camp work and skips exact enemy exposure only on a negative bound. Cost and byte identity were
  tested on the default eight mixed maps, both sides, pinned Release/100M against `08402461…`: all **16/16
  replay payloads are byte-identical**, but candidate-team play fuel rises **3,087,031,811 → 3,098,048,915
  (+0.36%)**; mean 36,744→36,876, p99 85,687→87,127, maximum 186,483 unchanged. Turns cheaper/dearer:
  1,184/15,032. Existing bench output does not identify champions, so there is no Willow-only attribution.
  The extra tile scans do not pay on this panel. Keep the parent, exclude this child from integration, and do
  not spend a default-budget rerun on it. Reports: `replays/fuel/willow-gold-prefilter-{parent,child}-100m.json`.
- Existing Hooks B ZIP stdout provides a stronger explanation for the no-action turns: `team-b.stdout` logs
  `act error: engine error 5: Invalid metadata, alignment, overlap or argument.` at rounds 122–124, 194 and 199.
  It lacks champion IDs, but Willow actor 7 has only recall cancellation (or no actions) at those rounds while
  the other candidate actors act. Treat actor attribution as strong evidence, not explicit log identity. There
  are no corresponding catch lines at 191–193 or 197–198. Native zero-error status does not include caught
  C++ exceptions. The failing import remains unknown; an isolated exact-source one-game harness trace is being
  adapted before repairing the argument fault. Live SDK state reads do not support the earlier stale-recall
  guard hypothesis.
- The complete stdout audit found **1,335 caught act-error lines across 51/80** gold-clearance games
  (1,296 code 5; 39 code 97), versus zero in the control. The old ten-game clearance panel has **242 across
  6/10** (239 code 5; 3 code 97), also versus zero. There are 1,334 unique match-round instances in the
  80-game candidate because one round logs twice. These remain side-attributed, not actor-attributed.
  See `research/caught-act-errors-clearance-audit-2026-10-23.md` for per-archive hashes and rounds.
- Source audit identifies a concrete invalid-call path: `willow_step_guard` evaluates every in-bounds station,
  including walls; visible ranged threat evaluation calls `Reach::at` and `sight`, which shadowcasts from that
  station. `tools/probes/README.md` documents opaque-origin shadowcast as engine error 5. Adjacent walls and
  visible reachable threats occur in the reviewed Hooks episodes. Child
  **`d3e145906ab84b49e17a481ce51be8d3431bad5634e47b68d9c17bdf0b8e0844`** excludes only actual walls from
  station exposure, preserving all nonwall legal and illegal station calculations. Walls are unselectable by
  escape and formation, and cached-exposure callers otherwise query actual champion positions. This repair
  is source-reviewed and entering the same published-40 A/B80 against `08402461…`; no new draft/item policy.
- The isolated original Hooks replay against a generated opponent puppet reproduces all 27,767 inputs and
  973 round hashes with exact final result using uninstrumented Release `0eef…`. Its recorder does **not**:
  the first difference is round 70, actor 5 missing a priority action. No recorder `@r`/`@x` point explains it.
  Thus no internal trace after round 70 is evidence for the original trajectory. Preserve the failed parity
  result under `replays/willow-prism-escape-clearance/current-source-trace/`; diagnose tooling separately.
  The wall repair is justified by the concrete API-contract violation, not by an unvalidated controller trace.
- The wall-only child `d3e14590…` completed the same published-40 A/B80 **46–34**, with zero match/native bot
  errors; play rollovers **559 vs 226**. Caught act errors fell to **34 across 17 candidate matches, all code 97**;
  **zero code 5** remains, versus 1,296 previously. The reference still has zero caught errors. This is a small
  outcome panel but directly verifies removal of the invalid-call class. Results SHA
  `d43ed4036077048c678e75896d809cbbda8244d20c9be0506a1767585da645ac`, native audit SHA
  `c7de5eb872ec0b08fea19eaf66bbda10f39189d5c81dbf2dedf3d02d5f767f85`; batch
  `replays/willow-prism-gold-wall-guard/batch-run-01-release-published40/`.
- The residual code-97 source has a separate concrete witness. Old clearance Broken Curve is **3v3**, with
  candidate Willow **A1/B4**, not A3/B7. At round 24 she cancels recall then replaces the ward that revealed her
  Prism teammate's bush. Correctly pinned explicit-step own views confirm Prism visible before and after
  cancellation, then identity-only after ward placement (A steps 3420/3421; B 3409/3410). `World::observe()`
  skips allies already read this round, leaving `mate->visible` stale; `local_support` then calls unguarded
  `kept_recall` on the now-hidden mate. Child **`73532ab70622df98fc487c9dd6fef8e8f5b276247d2040c44124fbe58f4290aa`**
  adds a live `visible_record` eligibility check and takes the existing abandon/reset path. It is source-only
  pending qualification; no global visibility-cache or item policy change. Window hashes:
  A `e744667eda8c8f13e8d55d0115b2af6bd39af958eb920c517e8c5391a8a5ebd4`,
  B `d92a534f2c1e588592e5868894b8bd243bdb3496c07abc1ab988a3006e829634`.
- Harness metadata audit found the recorder actually compiled against repository-root CMake/SDK with
  `CAMBC_DEBUG=ON`, despite a separately patched workspace existing. The intended `RELEASE_CODE` override
  and patched SDK were therefore not used. A corrected workspace-context rebuild is pending; this explains a
  concrete setup defect but does not yet prove the cause of the first divergence.
- Rebuilding the recorder in the intended workspace context resolves that parity failure. Corrected recorder
  and the bounded tracer both match the original **27,767 inputs and all 973 round hashes**, including finish;
  no trace import mismatches were reported. Exact actor-7 trace confirms failed ShadowCast origin **(14,18),
  radius 4 at r194**, and **(19,20), radius 4 at r199**, each rc 5 immediately followed by the caught act error.
  Both turns had cancelled recall; r197 instead returns **`bank_keep`**. The latter is now a confirmed branch,
  not yet proof that its alternative is safer. See `current-source-trace/trace-summary.json` and its comparison
  pins. The original wrongly built recorder remains excluded. Combined wall/live-mate source `73532…` is
  now running the same published-40 A/B80 against the frozen same-roster gold control.
- Deferred item arm **`9c49af2227edbd30873f91197d2ec342814e9087e50de4779fd4fbbf6fcdd647`**, cloned from
  `73532…`, adds Willow Jungle Health to the existing upkeep-value comparison before a Jungle emblem is owned
  and completes its begun partials after ordinary begun-partial precedence. Existing choices, prices, healing
  model and draft stay unchanged; no purchase is forced. Source-only and unmeasured, excluded from the current
  correctness batch. See `research/willow-prism-jungle-health-source-checkpoint.md`.
- Combined correctness child `73532…` completed published-40 A/B80 **46–34**, zero run/native bot errors.
  Native play rollovers **636 vs 238**; the wall-only panel had 559 vs 226, so removal of caught aborts does not
  itself establish a cost saving. Caught act errors are now **2 code-97 lines** (candidate A, Elk Arena r811 and
  Hooks r20), versus zero control. These residual calls are not yet localized. Batch and full pins:
  `replays/willow-prism-gold-live-mate/batch-run-01-release-published40/`. The next diagnostic compares the
  unchanged candidate against **actual released Khaos_v29/native draft `f711…`**, on all 40 published maps,
  both sides, before spending generated-map qualification on a roster that may not repay its substitution.
  The 46–34 same-roster result is support-controller evidence, not proof of draft value.
- Actual-roster comparison `73532…` versus frozen released `f711…` finished **42–38 / 80**, zero run/native bot
  errors, native rollovers **589 vs 275**. Correct pick-count splits: **3 picks 6–6, 4 picks 8–8, 5 picks 28–24**.
  `matches[].winner` is already a bot index; an initial summary incorrectly remapped it through physical side.
  Preserve that excluded summary and use `diagnostic-summary-v2.json` / `pins-v3.json` under
  `replays/willow-prism-gold-live-mate-vs-khaos-v29/batch-run-01-release-published40/`. Corrected group totals
  are checked against all 80 rows and headline wins. Both-side stdout audit reports candidate **4 code-97
  lines / 3 matches**, reference **1 / 1**. The auditor now reports reference errors rather than wrongly treating
  a previously observed zero as an invariant. This is a modest positive draft-inclusive panel, pending breadth.
- Exact-cost child **`e975d51efbf96d6a4ab07cd61cd773758743eb806d71f61872efba2538dd3247`** adds a separate
  Willow-neighborhood broadphase that omits only unseen enemies with nonpositive credibility, matching both
  exact threat paths. Existing conservative API remains unchanged. Against `08402461…`, Release/100M default
  eight mixed maps both sides gives **16/16 byte-identical payloads**, total fuel **3,122,886,496 → 3,118,137,631
  (−0.15%)**, mean after-round-one **36,227 → 36,171**, maximum unchanged. This is a small measured saving.
  Default-budget Starfish/Yellow Brick both sides gives **1–3**, candidate/control native rollovers **206/47**,
  zero native/caught errors. The parent was 2–2 on those exact pairs: Yellow Brick A flips to a loss; all other
  winners stay. Different default-budget trajectories are expected; four games do not establish general quality.
- Source-only incremental exact-cost arm **`6f7d98432d001e8919ce9c26988c35e60aecdb25cd02f126dbcfd0e5017213de`**
  reuses station `open_for_us` for risk admission as well as legality, atop `e975…`. It retains all dynamically
  blocked open-tile exposures and skips only static tiles our champions cannot occupy. Consumer proof has
  passed design review; actual source review/16-game cost check pending. The existing e975 high-budget results
  can serve as the frozen comparison, avoiding an unnecessary repeated parent run.
- Open-stations `6f7d…` passed actual source review and the pinned Release/100M comparison: **16/16 byte-identical
  payloads**, total fuel **3,118,137,631 → 3,107,438,021 (−0.34%)**, 16,083 turns cheaper and 10 dearer. The exact
  `e975…` parent report was reused after checking maps, opponent, mode, fuel, CLI and engine pins. Reports and
  hashes are in `replays/fuel/gold-live-mate-vs-open-stations-high100m/summary.json`. No extra default-budget
  four-game run was added. For the earlier credible-guard default four, the matching parent had **192** native
  rollovers versus the child's 206; this does not change the small-sample interpretation above.
- Focused Hooks A tracing localizes the remaining r20 code-97 call: **Marcella actor 2** executes
  `preferred_capture_holder`, querying **Vesper handle 1** with `sdk_champion` while cached alive/visible are true,
  **standing on the camp is false**, and cached channel is recall. The helper computes `kept_recall` before rejecting
  the ineligible occupant. The original candidate has zero native rollovers. This unguarded path also exists in
  released `f711…`; it is not a Willow-only regression. The isolated Release reproduction matches every extracted
  event, but its payload hash differs, so this is **event-sequence parity**, not a claim of complete replay or
  fuel/internal-state identity. Evidence and both hashes are in
  `replays/willow-prism-gold-live-mate/hooks-a-r20-trace/diagnosis.json`. A separate child will reject cheap
  ineligibility before SDK reads and guard any remaining remote recall query against stale visibility.
- Frozen final correctness candidate **`5ef147c704dbaa7a5143f346c9cd4a3156bb3d1305557069042ed5d77dac01d2`**
  (`bots/variants/willow-prism-gold-holder-visibility-work`) adds that fix atop `6f7d…`. Only `bot.cpp` changes:
  reject cheap ineligibility, require fresh `visible_record` for remaining remote candidates, then evaluate the
  unchanged recall condition. Self avoids the redundant live visibility read. Independent source review passes;
  generic recall, gem-holder preference, pressure rules and item policy remain unchanged. The support mailbox
  header is byte-identical to the production helper that already passed its fixtures. This bundle now enters
  published 80 + gen 512 + gen-s1 512, then a fresh 512-game holdout against released **native-roster `f711…`**,
  own compiled drafts, Release/default fuel, CLI 3.0.5/engine 1.0.3, one low-priority worker. Deferred Jungle Health
  and Willow bank-recall horizon changes are excluded. No outcome result for this final source is claimed yet.
- The Hooks trace equivalence is additionally checked at the extracted state layer: **23,049/23,049 events** match
  across the whole match, and normalized extracted round-end states match through rounds **1–20**. This still
  does not establish full payload, fuel, or full-match internal-state identity; the saved diagnosis states those
  limits explicitly.
- Final-source `5ef147c…` published panel finished **44–36 / 80**, zero run/native bot errors and **zero caught act
  errors on both sides**. Native play rollovers remain higher: **505 vs 235**. Results SHA
  `f38b5678cc8b2e0f855286df7e982488020fac20e39b370bb17db347b5f5d1c0`; batch
  `replays/willow-prism-gold-holder-visibility/batch-run-01-release-published40/`. The preceding `73532…` panel
  was 42–38, but this outcome difference combines the guard and optimizations, not an isolated causal estimate.
  Generated-map qualification continues with the final source frozen.
- Prepared next exact-cost experiment **`d6bc4851693d0fa9a604e183d07215c73b53971281b207925bc8cf4124547528`**,
  `bots/variants/willow-prism-record-reuse-work`, from `5ef147c…`. A lazy loop-local movement read replaces repeated
  reads in the read-only support station scan. `kept_recall_from_state` allows existing fresh ally records and the
  heal loop to avoid redundant champion-detail queries; channel time remains conditional on recalling, with the
  same exception scopes. The channel-time helper does not overwrite champion-record storage. Independent source
  review passes, but no build, replay identity or fuel measurement has run. This arm is excluded from qualification.
- `5ef147c…` broad qualification finished **495–609 / 1,104 (44.84%)**: published 44–36, seed1023 **228–284**,
  seed1024 **223–289**. Native play rollovers **4,455 vs 3,103**, zero native bot errors; caught act errors **2 code5
  candidate**, versus **49 code97 and 1 code5 reference**. Candidate residuals are seed1024 open-field102407102 A
  r896 and shared-gems102401905 A r82; the latter replay also has reference code5 at r741. These rare argument
  faults are not yet localized and must not be described as eliminated. Per-batch setup/results/audits/hashes are
  under `replays/willow-prism-gold-holder-visibility/`. Its initial 1104 summary mislabeled the combined generated
  pick split as seed1024; a corrected v2 is being saved, preserving the original. Raw match results are unaffected.
- Generated roster splits across both seeds: **3 picks 114–222 / 336** (1023 54–106; 1024 60–116), **4 picks
  154–160 / 314**, **5 picks 183–191 / 374**. The three-pick substitution explains most of this matchup's deficit;
  this does not isolate Vesper's gold bonus from its mobility, independent farming or controller interactions.
  No heldout suite was generated or consumed for `5ef…`. Keep it as a diagnostic parent and improve the roster
  and demonstrated escape issue rather than releasing it or treating the threshold as an automatic discard.
- Exact-source own views from `038-00reverse-spiral-21.repl26a` (archive SHA
  `fc80f05b87a4bf5a8aa1feb242202d0b0daa30bcfe24fd255d26fe511fad98a8`) show Willow7 at r185–187 sees an awake
  Elk14 and Marcella's committed recall timers 3/2/1. Willow keeps basic-attacking while taking 60 camp damage
  each phase; healing is unavailable or correctly withheld from the committed recall. At r189 she has 218 HP
  and steps from (28,23) to (29,22), deeper into the known Elk's range. Existing home distance outranks the cached
  camp-exit burden at equal immediate risk. The late northward escape is a different case: Vesper is visibly
  approaching from r902 and threatens that exit by r904, so forcing north would ignore known danger. See the
  two pinned `actor-windows-reverse-spiral/` exports. Earlier farm admission needs a minimal caller trace before
  changing incumbent/ally-engaged exceptions; no blanket camp ban or healing-item fix follows from this episode.
- Reviewed child **`4100a9a2294c29147bf0a5b95156b45efb7f00e60cdf724aaf68aa532e553b5e`**
  (`bots/variants/willow-prism-camp-exit-roster-work`) restores native **three-pick Prism/Vesper/HoR**, keeping
  current four/five-pick Willow rosters, and promotes already-computed camp-exit burden before home-distance ties.
  All higher safe/lethal/stun/imminent/damage/economic priorities remain unchanged. Burden is geometric, not a
  guaranteed obstacle-aware exit, so routing outcomes still need validation. Only `draft_selection.h` and `bot.cpp`
  change; no new evaluations, fuel gates, items or recall policies. Missing-Willow support handling passes review.
  This child now runs the same 1,104-game qualification against native `f711…`; fresh holdout remains pending.
  Legacy support summaries assume Willow in three-pick drafts and must not be reused unchanged for this child.

- The parent qualification summary correction is saved as
  `replays/willow-prism-gold-holder-visibility/qualification-summary-1104-v2.json`, SHA
  `639f06a2912d535006ee27f2ec7039fadef23f8550ff1e7eb29ab29e2aebf1a7`. It renames the combined generated
  roster split, adds per-seed splits and records both-side caught errors. The original summary and all raw
  batches remain unchanged; this is a reporting/provenance correction, not a new result.
- `4100a9…` published panel finished **40–40 / 80**, native rollovers **511 vs 232**, zero run/native bot errors,
  zero candidate caught act errors and two reference code97 lines. Generated qualification continues. The
  Reverse Spiral B extract at
  `replays/willow-prism-camp-exit-roster/batch-run-01-release-published40/analysis-reverse-spiral/225f0d926e7b3763/`
  matches the parent event sequence through step 28010. The first changed move is Willow7 at r188/step28019:
  (27,24) to (27,25), instead of (28,23). She exits the Elk's range at r189 with **218 HP** and recalls safely;
  the parent dies at r193. This directly validates the targeted escape improvement, not a match-level win:
  both lose, candidate submitted score changes 203 to 216 while the opponent changes 1027 to 1059.
  Whole-match Willow deaths change 4 to 3 and effective healing 5,116.5 to 8,532.7, but Prism deaths rise 2 to 3.
  A later new Willow death at r345 follows Prism waking another group at r339; its cause remains unassigned
  pending both actors' own-view windows. Ordinary farm actions lack the combat planner's allied wake-liability
  check, but that source gap alone does not establish the cause of this episode.

- `4100a9…` generated seed1023 finished **256–256 / 512**, native rollovers **1,828 vs 1,135**, zero run/native
  errors, zero candidate caught act errors and **21 reference code97 lines**. By picks: three **78–82** with
  rollovers129/146; four **79–71**, 297/123; five **99–103**, 1,402/866. Results SHA
  `4117d5d9cbf5174dd8a964804821334cccd03e5b910d6bfd82270c9c19a87c50`; the adjacent
  `outcomes-by-picks-presets.json` counts winner directly as bot index. Second generated seed remains in progress.
- Willow7 own views r338–344 confirm that she knows the newly awakened group10 and sees enemy Vesper at
  (25,8), but keeps moving within camp reach and eventually waits at (26,5). At r343–344 she starts with no
  active channel; repeated recalls are the expected end-turn stub, not evidence that `continue_recall` held her.
  A two-step exit can trade camp exposure for enemy exposure, and another group's wolves are not currently
  observed. A safe override is not yet established; a bounded exact trace will distinguish comparator choice,
  legality and earlier branches. The first requested Prism export accidentally targeted actor5 (Vesper) by
  confusing turn slot5 with champion ID. Its own metadata exposes the mismatch; it is excluded as Prism evidence.
  The corrected actor4 export is pending. No causal claim about Prism's knowledge follows from Willow's vision.
- Prepared optional source-only item child **`f996fe7ca43a92b1dbf20dbefca9f4bec0078b7577fbd40b5969d923bdbaa9d6`**,
  `bots/variants/willow-prism-camp-exit-health-work`. Its four added lines exactly port the reviewed Jungle Health
  option onto `4100a9…`: finish a begun Willow partial, and consider one Jungle Health emblem through existing
  upkeep valuation. It does not force a purchase or value future healing. Source reviewed; no build, activation
  measurement or outcome test yet, and excluded from the current qualification.

- `4100a9…` full qualification finished **545–559 / 1,104 (49.37%)**, with seed1024 **249–263**. Native play
  rollovers **4,032 vs 2,979**, zero native/run errors. Candidate caught faults: one code5 in
  `387-gen-shared-gems-102401905-12.repl26a`, A/r82, archive SHA
  `b285c48ed5347cb97e4a2c6ba29f069a6a07a30377b07cdb616e08829b45a173`; reference has 41 code97 and one code5
  line. Generated splits combined: three **164–172**, four **160–154**, five **181–193**. This is near-level
  behavior with a demonstrated escape fix, not a proven win-rate improvement. Preserve it for further improvement;
  no fresh holdout or Willow release has occurred. Full pins are in
  `replays/willow-prism-camp-exit-roster/qualification-summary-1104.json` and its batch references.
- Corrected `reverse-spiral-prism4-r339.json` confirms Prism personally sees Willow at (28,5), recalling with
  timer4, and group10 asleep. He stuns enemy Vesper then basic-attacks the Golem for35. The group's Wolf at
  (27,3) uniquely prefers Willow (distance2 versus3 to Prism), so the new wake creates known20 allied damage
  at the observed positions; Willow takes20 in the next phase. This does not depend on the Golem's tie order.
  `Search::read_camps` admits camp basics only for Vendetta/Varg, so Prism's basic uses the ordinary attack path.
  A source-only Prism-basic protected-wake child is being prepared; the exact caller trace remains in progress.
  Protecting even recall stubs matches existing planner policy but may delay healthy coordinated farm starts,
  an explicit tradeoff to measure. The separate Willow evacuation issue is still under investigation.

- The bounded exact-source trace is complete in
  `replays/willow-prism-escape-clearance/current-source-trace/trace-camp-exit-prefix-report.json`, SHA
  `8af966d0ab4aaf8e8d90df780940dcf928a889b0973f5ae5871a9b211dd6adb8`. Release baseline and recorder each
  reproduce the original 33,736 inputs, 1,197 round hashes and result. The instrumented trace matches all 1,379
  compared call-count/hash segments and 3,608 candidate action events through r344. Its first later wrapper
  mismatch is r779; later trace output is excluded. Native Prism4's r339 basic is confirmed as
  `attack_camp_target`, group10/member0. Willow7 takes `bank_trip` at r339–340, forced escape at r341–344,
  then cannot improve its comparator at r343–344. Southward stations are legal but score 250 imminent damage
  versus 140 staying; lower camp-exit burden (140 versus 280) never reaches the tie-break. This establishes a
  greedy escape limitation, not a proven safe second step: nearby hidden camp occupancy remains unknown.
  The diagnostic's initial native-ID versus side-local-index filter mistake was corrected only in instrumentation;
  failed traces are retained and no frozen gameplay source changed.
- Independently reviewed Prism-basic wake child **`36903909dfbfcad463ee1ccb583dba8ec018ad1dd8daa1f28fa74afc9a3875ce`**
  (`bots/variants/willow-prism-protected-wake-work`) changes only `bot.cpp` from `4100a9…`. An action-local,
  bounded snapshot rejects newly woken raw hits onto visible recalling/tributing/capture-holding allies or a
  visible ally who cannot survive the total new hit. It credits a freshly verified killing basic only for the
  actual target; surviving groupmates still count. Harmless groups pass, and fresh awake/dead members add no
  wake harm. The initial unbuilt `dae1e510…` shortcut using cached awake/recent damage was removed because
  damage does not reset an already-awake member's sleep counter. Only the final reviewed source is authorized
  for an 80-game published same-roster comparison against frozen `4100a9…`, with both-side native and caught
  error audits. Fuel cost, recall-stub conservatism and outcome remain unmeasured at this checkpoint.

- Independently reviewed owned-escape child **`61528d3eb8afabab166695d65d20f41595fd5425c9904ea7ae11f055dfc73aba`**
  (`bots/variants/willow-prism-escape-cost-work`) is a separate three-hunk change from frozen `4100a9…`.
  It keeps safe/nonlethal/stun precedence, then compares enemy imminent damage plus existing camp-exit burden,
  before all original immediate-risk and routing ties. A raw camp-imminent accumulator uses the identical
  existing camp scan predicate and units; there are no extra SDK/path/threat queries or fuel gates. In the
  exact r341/342 witness this ranks the southward station 250 against 280 staying. It estimates repeated camp
  damage geometrically, not a certified safe route; later enemy pursuit or obstacles can defeat the estimate.
  Bank admission is deliberately unchanged: the confirmed escape already starts at r341 with 540 HP, while
  r339/340 are ordinary bank routing rather than immediate safe tribute. An 80-game same-roster diagnostic
  against `4100a9…` is authorized after the wake-guard panel and audits.
- The protected-wake child `36903909…` completed its 80-game published same-roster panel **42–38**, zero runner,
  native play/draft and caught act errors on both sides. Native play rollovers are **652 vs 575**, so this is not
  evidence of a free safety improvement. Results SHA `31effe9638bfbea7364f4b412af8d37b48e02f31b74fd56594a70f1ff6644b93`;
  batch `replays/willow-prism-protected-wake/batch-run-01-release-published40/`. Root found that the first pins
  file's post-run aggregate was calculated with path-prefixed filenames rather than the canonical bot-directory
  command; authoritative `pins-corrected-v2.json` now verifies canonical `36903909…`/`4100a9…`, with the original
  retained and its noncanonical values labeled. Its opponent is `4100a9…`, unlike the older
  r339 witness against released `f711…`. The new Reverse Spiral r339 attacks a different camp/group; matching
  map/round alone does not establish the same causal episode or demonstrate that the original hit was prevented.

- Escape-cost `61528d3…` finished its same-roster published panel **32–48 / 80**, native play rollovers
  **642 vs 579**, zero runner/native/caught errors on both sides. Results SHA
  `b37bedb527450232d9d9d06b8e7edcaf5180c33c043de1d6366d9f3ec2ac559c`; pins in
  `replays/willow-prism-escape-cost/batch-run-01-release-published40/pins.json`. Its setup provenance was
  reconstructed after launch and is explicitly labeled accordingly; canonical source hashes were verified
  after completion. The diagnostic loss signal calls for mechanism analysis before qualification, not a
  claim that the hypothesis is disproved. A controlled Reverse Spiral B run against the original frozen
  `f711…` opponent is authorized to compare first differences with the existing `4100a9…` witness.
- Source-only integration **`130a17af668a432a8a5582ec0736b1ef13c22e05245bc5742e472f3d02a620a5`** combines
  reviewed protected wake, escape cost and the optional Jungle Health candidate. Independent composition review
  confirms exact patch composition; it remains unbuilt and deferred while the escape regression is diagnosed.
  Exact-cost helper child **`2467c6e1c3c23f71d5075967e318b3891fff919a3286b3a1befd43b4ea3e9ba4`** from `36903909…`
  ports the reviewed record reuse and lazily constructs the wake batch only for damaging groups. Source review
  passes, but no replay identity or fuel-saving result is claimed. Its source-only port onto the combined bundle
  is in progress; no broad test or release is authorized merely by these composition checks.

- Controlled escape-cost Reverse Spiral B against the original frozen `f711…` opponent completed with exact
  matching first **7,936 emitted events**. Its first changed action is Willow7 at r341: old `(28,5)→(27,5)`,
  new `(28,5)→(27,6)`. Own-view exports confirm the same initial state and known information. New Willow then
  steps to `(27,7)` at r342 and leaves camp exposure; Vesper retreats rather than pursuing her. Across r342–350,
  old Willow/Prism take 540/180 camp damage, new 20/380: pair damage falls **720→400**. Prism survives at160 HP
  and recalls at r350; Willow survives the old r345 death and banks seven gems at r362. Thus this is a direct
  local escape success, not evidence of pursuit underpricing. Later whole-match score still falls **216→120**,
  Willow deaths3→2/healing8,532.7→7,396/submitted43→42, Prism deaths3→2; those are downstream outcomes.
  Pins and actor windows are in `replays/willow-prism-escape-cost/khaos-reverse-spiral-diagnostic/`; replay SHA
  `ce21cf484d4d747cc20a3b2ae0ee024e2db5005340e028bd17247c8df547bd3f`. Native rollovers candidate/reference1/2,
  zero native/caught errors. Initial synthetic bot-order metadata was corrected with original reader outputs
  preserved; no match rerun occurred. A concrete loss from the 32–48 panel still needs its own paired diagnosis.
- Reviewed helper port **`96d462db4680bed48696209d0c2e45adf1d8689506eec43643ca4d009161be8c`** exactly applies
  the `36903909…→2467c6e1…` cost delta onto `130a17…`; source checkpoint is
  `research/willow-prism-coordinated-reuse-source-checkpoint.md`. It remains unbuilt and excluded.
- Exact-cost qualification of **`2467c6e1…` vs `36903909…`** completed on 16 native-draft games against frozen
  `f6439019…`, Release with an explicit **100,000,000 fuel override**, not the normal game budget. All16 replay
  payload hashes match. Recorded play-turn fuel rises **3,197,974,157→3,198,296,241**, +322,084 (**+0.0101%**);
  after round1 the rise is322,376. This bundle has no demonstrated fuel saving and is not adopted; no default
  budget follow-up is justified. Raw reports and pre-run pins are under `replays/fuel/willow-wake-reuse-*`;
  authoritative corrected comparison `willow-wake-reuse-high100m-comparison-v2.json` (original preserved).
  The helper port's exact source composition is not an independent runtime test. The corrected comparison
  explicitly distinguishes the 100M diagnostic quantum from the platform's 100k default; actual run controls
  were pinned correctly.

- Monolith was selected for a controlled regression diagnosis: `61528d3…` lost both sides with zero native
  rollovers/errors. One native-draft `4100a9…` mirror on the same 50×50/five-pick map gives physical B a
  **1006–574** win, versus B's **681–1325** loss under `61528d3…`. Opponent A is the same `4100a9…` in both;
  an initial report incorrectly said it differed, corrected in
  `replays/willow-prism-escape-cost/monolith-parent-mirror/diagnostic-summary-v2.json` and `pins-after-v2.json`.
  Mirror archive SHA `0217f88f74ee6366fa6dfa0754920a22a77e76327d42279b5d8a2ea758cf58b2`; paired candidate
  archive `817a1ccc3772fa73ca916168b0b3021a69518bcee64f9fb5bb0b3f59afc7c3b6`. The native-input comparator
  finds first recorded mismatch at input33901/r910, B HoR9 moving `(30,20)→(30,21)` versus `(29,19)`;
  round-state hashes first differ at r911. Willow's r912 heal targets the same Marcella with the same deficit
  at different positions. No concrete escape-comparator failure is established. Fuel differs earlier (Willow
  +38 at r1); zero rollovers does not exclude existing fuel-gated decisions or unrecorded communication/private
  state differences. This outcome flip must not be recast as an observed bad Willow heal or pursuit death.
- Authorized full native-draft/default-100k qualification of **`130a17…` vs released `f711…`**, published80 plus
  gen1023/512 and gen-s1 seed1024/512, one worker. This tests the coherent wake/escape/Jungle-Health bundle,
  explicitly excluding the no-saving helper delta. The isolated escape 32–48 diagnostic remains a concern;
  the controlled local escape benefit and lack of a demonstrated policy failure motivate broader combined
  testing, not a release claim or threshold exception. Verify actual Jungle Health purchase activation before
  attributing any benefit to that optional choice. No fresh holdout, unranked batch or release is yet authorized.

- Combined `130a17…` completed the published-map segment **51–29 / 80** against released `f711…`, with candidate
  wins split 25 on A and 26 on B. Native play rollovers are **469 vs 216**, zero runner/native/draft errors;
  caught act errors are candidate0/reference2 (both code97, Gold Rush r1522/r753). Results SHA
  `15a61157911d8c03b732bcf369f43ff8a086aa68b25acb7e587bb6adafcbd970`; source/runtime pins and both audits
  are in `replays/willow-prism-coordinated/batch-run-01-release-published40/`. This is a promising first segment,
  not a completed qualification or isolated attribution to any component. Gen1023 and gen-s1/1024 continue
  serially under the existing authorization. No source change is made during qualification.
- Separate source-only cost child **`9530a5fd9e91f36587ac9d93fbafca347d0b9c35b157bc23a17ba641ebeae262`**
  (`bots/variants/willow-prism-coordinated-risk-cost-work`) specializes `support_exposure_raw` so only Willow's
  station-cache calls accumulate `camp_imminent`. Independent review verified that only that cache's escape
  comparator reads the field; other risk fields, SDK calls, invalidation and stale/error paths are unchanged.
  Review passes, but the child remains unbuilt/unmeasured and excluded from `130a17…` qualification. No fuel
  saving or runtime identity is claimed. Checkpoint: `research/willow-prism-coordinated-risk-cost-source-checkpoint.md`.
- Upstream fetched through `5910608` (HTB tooling fixes). Its delta from `1594989` does not change Hyperion
  gameplay source; the frozen qualification inputs remain applicable. No merge or rebase was performed.
- Separate pure-`130a17…` cost child **`348440a42334ef8ae90ee4a0733b016dd5e32ba6f47fefecc2053f44f562d499`**
  (`bots/variants/willow-prism-coordinated-lazy-wake-work`) leaves the two fixed wake-record arrays uninitialized
  until their groups are used. Group/Target are trivially default-constructible plain records in ordinary
  `std::array` storage, avoiding inactive-union lifetime issues. Each new group receives exact original values,
  and every matching target index receives its original sentinel before fallible group queries. Independent
  actual-source review passed: partial-error vetoes, duplicate targets, hidden-health conservatism, bounds,
  SDK order and floating accumulation order remain. Only bot.cpp differs. No build/runtime test or saving is
  claimed; the added per-group index scan can offset savings. This remains outside active qualification,
  pending a later 100M replay-identity/fuel experiment. Checkpoint:
  `research/willow-prism-coordinated-lazy-wake-source-checkpoint.md`.
- Combined `130a17…` finished gen1023 **256–256 / 512**, native play rollovers **1889 vs1158**, zero
  runner/native/draft errors. Caught act errors: candidate0, reference24 code97 across17 matches (A8/B16 lines).
  Results SHA `2ec467dc16be525195b8086c0a51858c9430b27f2d67250fce7c3d6c22eecac7`; full audit rows/source pins
  in `replays/willow-prism-coordinated/batch-run-02-release-gen1023/`. Published plus this suite totals307–285,
  with zero candidate caught errors. Seed1024 continues unchanged; no release inference yet.
- A single current-source loss, published `072-01shortcut-21.repl26a`, was extracted for paired actor views:
  archive SHA `e4c3016684200c68de478a106203ed53a41411491c586d20914efc53bd1f5afa`, candidateB Prism4/Willow7,
  zero native rollovers on both sides. Own-view windows r95–104 are in the published batch's `actor-windows/`.
  Prism's r100–102 deficits60/120/180 are below the existing216 useful-heal threshold; Willow is in a kept
  recall then. At r103 Prism is missing240 and Willow heals him after arriving at spawn. This interval does
  not substantiate the recall-stub missed-recovery hypothesis. Earlier r95–97 Willow stands at raw(14,12)
  with400/340/280HP beside full-health Prism(15,13), under the visible awake Elk(12,14). Her shorter distance
  draws its60-damage hits; at r98 she moves(15,12) then recalls. Whether earlier tank-allocation positioning
  improves combined output/recovery cost remains a hypothesis under review, not an attributed cause of loss.
- Combined `130a17…` completed seed1024 **261–251 /512**, native play rollovers **1863 vs1555**, zero
  runner/native/draft errors. Candidate retains one caught code5 (`invalid_argument`) on shared-gems102401905
  A/r82, archive `51d6524ed2c74cbaacf9032c1d27d9da9d6f03c00ec186257c55f52796c21b19`; this is the same map,
  side and round as the earlier `4100a9…` and `5ef147…` residual, not actor/call attribution. Reference has18
  code97 lines. Full qualification is **568–536/1104**, native play rollovers4221 vs2929, candidate caught1
  code5 versus reference44 code97. No claim of zero candidate action errors is made.
- Pick-count split is pinned in `replays/willow-prism-coordinated/qualification-splits-by-picks.json`, SHA
  `7e043407fd724657fef1b2e46c3c0da1cd78c93ba3c168e0cb94d81bf4588c91`: published3/4/5 wins-losses5–7/11–5/35–17;
  seed1023 79–81/74–76/103–99; seed1024 92–84/85–79/84–88. Thus generated-only3/4/5 totals171–165/159–155/187–187.
  Three sampled candidate-side Jungle-preset replays (two4p, one5p) show no Willow Jungle Health shard purchase;
  this limited activation check cannot establish that the optional item never buys, nor attribute the gain to it.
- Authorized a fresh512-game confirmation on unused seed2026102308 with unchanged `130a17…`/`f711…`, native
  drafts/default100k/Release/one worker. The known single residual argument fault is carried explicitly while
  planning bounded localization; it is not automatically treated as a new regression or ignored. New fault
  clusters require review. No new experimental cost/draft/micro source is included in this confirmation.
- Source-only dense-pack draft child **`2dd4084d601fc89138afa7df45372d45260ad8d23313e3e6f56e249f1bb26a69`**
  (`bots/variants/willow-prism-dense-vendetta-work`) changes only fifth pick HoR→Vendetta when the released
  strict `3ull*members > 10ull*groups` boundary holds. Willow and all first-four roles stay; three/four-pick
  paths make no new camp query. The cached five-pick initializer reuses bounded `native_draft_counts()`.
  Independent actual-source review passed, but this remains unbuilt/unmeasured, separate from confirmation.
  Count density is a coarse existing hypothesis, not a proven counter to a team or guarantee of cheap resets.
  Checkpoints: `research/willow-map-counterdraft-review.md`, `research/willow-prism-dense-vendetta-source-checkpoint.md`.

- Coordinated `130a17…` completed fresh seed2026102308 **259–253/512**, giving **827–789/1616 (51.18%)**
  against released `f711…`. Fresh native play rollovers are1708 vs950, zero runner/native/draft errors;
  caught errors are candidate1 code98 versus reference44 code97 plus1 code98. Both code98 occurrences are
  physicalA/r6 on mirrored gen-city202610230806914 games after r5 rollovers, with `No visible entity of this
  kind occupies the tile`; this is shared evidence, not an engine-cause attribution. The earlier candidate
  shared-gemsA/r82 code5 remains unresolved. Across1616, native rollovers5929 vs3879 and caught lines2 vs89;
  neither a zero-error nor fuel-saving claim is made. Fresh3/4/5-pick results81–73/84–86/94–94. Results SHA
  `a21c86ab8ea698567306a91a543af48d4332a93b00c1a03b7b41f8cd6de976ac`; summary SHA
  `f4041f7e75fced8a63de2133c8df26ef73e7ee90658dfe8d9f854318aed32be9`, under
  `replays/willow-prism-coordinated/batch-run-04-release-heldout-2026102308/` with both audits and pins.
- Fresh setup provenance correction: the original setup used bare filenames in its source aggregate,
  rather than the canonical bot-root `src/*` recipe. Sources were unchanged and independently rechecked
  as130/f711. Original setup SHA `c4942110ace7076f34a788efd5f0d40b440795498ad208a932f20bd4a0a67688`
  is retained. Correction sidecar SHA `3873108b2b9a28ac6705bba8aeda547ecb10903ab7aedc498284ab5f27717cb6`
  was written **after process/build launch and at least26 printed match completions**, not before the run.
  Final pins preserve this timing limitation rather than recasting it as a pre-run canonical pin.
- Independent review supports releasing exact130 as a modest coherent bundle, with the greater fuel burden
  and rare caught faults explicit. The fresh result is near parity, published maps supply much of the margin,
  and no isolated Willow/item benefit or statistical significance is asserted. Bounded residual-fault
  localization is next; numbered release and submission receipt are not yet created.
- Review of the pinned1104 pick splits concentrates the extra rollover count in5p:3257 vs1815 (+1442),
  compared with3p325 vs320 and4p639 vs794. These are event totals, not normalized per-turn fuel rates or
  isolated attribution to Willow. Five-pick coordination cost is a priority for measurement; do not add fuel
  gates or infer that all extra cost comes from the support controller.
- Isolated post-dash child **`fbb2190cc0468d4647183fd8e4c8e716d96649e9d1a58bf528c7303fd155f9d2`**
  passed independent actual-source review including the final three stale-state repairs. Both successful
  escape-dash callers refresh Safety; on a camp-safe landing, the remaining walk compares staying against
  at most8 legal homeward neighbors by damage, existing dash-depth, home distance and enemy gap. Full ties
  stay; refused moves never use an unranked fallback. No-dash and camp-positive legacy paths remain. This
  comes from a public Cat Swirl own-view hypothesis with unverified source, not proof that staying saves
  the observed Vesper. No build/runtime/fuel claim; child remains separate from130 qualification.
- Bounded localization of shared-gemsA/r82 code5 reproduced the original130 match exactly against a replay
  puppet:50,782 inputs and1,433 round hashes. Recorder vsRelease first diverges at r761; trace vsrecorder first
  diverges at r635, placing the target safely inside both validated prefixes. At r82 actor1 (A Vesper) receives
  code5 from `bc_DistanceField_Get(-1,-1)`; five preceding move imports return code21 and the following priority
  call sets13. This identifies the import/arguments, not its high-level caller or a proven stale-state cause.
  Evidence: `replays/willow-prism-coordinated/code5-shared-gems/repro/code5-localization-evidence.json`, with
  exact target stdout preserved under that case's `evidence/`. No global trace-equivalence claim or source
  repair is made. The qualified130 source remains frozen for release preparation.
- Follow-up saved actor state shows Vesper alive at r80 with190HP at(16,28), dead/off-map at r81 with respawn60,
  and still dead at r82 with respawn59. The trace reports a prior-turn fuel resume into r82. This ties the
  off-map query to a resumed dead actor, while leaving the high-level caller unresolved. Updated evidence
  is retained in the case JSON; no global Field::at behavior change was made.
- **Released exact130 as Khaos_v30 / server40.** Only qualified source was copied to the numbered directory
  and canonical Hyperion. Raw WASM `cc23c57b34cd32853849ecd97aba4113efbaaf13e5282811f0d94f3acae3c9cc`
  and injected WASM `728b61f9810aabbc43edfbc90e81adef92b029e986471c026fb4540a8a79abcd` match the candidate
  byte-for-byte. CLI bundle contains30 source-only entries,220406bytes, SHA
  `d15c8410d7ebc9c2c19ffa0f1b5d366911988f9c102806278a2f3b3358b32b5f`; its members match the source files.
  The upload reported the same byte count, but its remote payload was not retrieved. Pantheon was confirmed
  before submission. Receipt SHA `12204b152855cf41f8c84e7f758914ce9ba44ae419581e7031e3abde00a4bfd2` in
  `provenance/Khaos_v30-release/submit-response.txt`. All known faults/fuel limits and the fresh setup
  correction remain explicit in release provenance. The mailbox fixture now includes canonical Hyperion's
  identical helper and passes; it no longer depends on an ignored experiment directory.
- Offline actor attribution on562 generated5p games finds Willow1517 rollovers versus315 for reference
  fourth-slot Ryth/Vendetta; same fifth-slot HoR1685 vs1435. Both sides share the same603733 round-exposure
  proxy per slot, which is not an exact per-champion invocation count. Published-map events remain unattributed
  by slot in this report. Full four-suite5p counts4494 vs2440; source/function causality is not established.
  Report: `research/willow-five-pick-fuel-diagnosis.md`; reusable offline helper and pinned JSON retained.
- Source-only Willow station scratch child `33d608469b59419b7cc0a1275da543936844b467f64206ebd426c59da21141a2`
  reuses one normally constructed threat-output array across the existing nine station calls when the
  neighborhood enemy broad phase is positive. Independent actual-source review passed: complete returned
  prefixes, lifetimes, fallback local storage, SDK/accumulation order and strict guards are preserved.
  A Release/100M diagnostic panel of eight maps/both sides against frozen f711 produced **16/16 identical
  replay payloads, winners and drafts** versus parent130. Total play fuel4184007689→4183581223 (−426466,
  −0.01019%); Willow924670554→924544872 (−125682, −0.01359%). This tiny saving does not warrant integrating
  the child; no default100k qualification or release claim. Pins/raw results in
  `replays/fuel/willow-station-scratch-100M/`. Next investigate one Willow-heavy five-pick game before designing
  further caching, rather than presuming this scratch initialization caused the observed rollovers.
- After server40 submission, queued two live exploration groups through CLI only: Fish
  `7c79bf17-8938-4dab-adfc-75776d6a0351` and :3 `99f66b35-e905-49b5-9d09-aba06fc1e4fe`. Maps in order:
  Swirl, Boss Battle, Shortcut, Monolith, Expanse; Pantheon sidesA/B/A/B/A against Fish andB/A/B/A/B against:3.
  Receipts are in v30 provenance. Neither opponent nor own submission identity is exposed/pinned by this
  endpoint; queue-after40 is not source verification. These ten games are exploratory loss evidence, separate
  from frozen local benchmarks. No outcome or source attribution is inferred before results arrive.

- The post-dash child `fbb219…` completed the native-draft published40/both-sides diagnostic against frozen
  v30/130: **43–37/80**, candidate A24/B19, zero runner/native/draft errors and zero caught-act lines on both
  sides. Native play rollovers621 vs572. Results SHA
  `8ea9ec260323baad813d8a851679a40bd2725ab7ba66009270b41d0b5f801634`, with setup/pins/audits under
  `replays/willow-prism-post-dash-v30/`. Release/default100k, one worker. This is a small selection panel,
  not broad qualification or proof that the old live Vesper would survive its counterfactual.
- Dense fifth-pick child `2dd408…` completed the same80-game setup against130: **43–37**, A21/B22,
  native play rollovers582 vs609, zero runner/native/draft/caught-act errors. Actual replay roster metadata
  verifies the strict density switch on12 five-pick maps: Vendetta13–11/24. Sparse five-pick HoR maps15–13/28;
  unchanged three-pick6–6/12 and four-pick9–7/16. The latter controls cannot establish a draft gain; all bins
  reconcile to the total. Results SHA `1744d672f0b050e197bf5480f988437cdd174e9225c67e178e0c66d289d584fe`;
  roster audit SHA `481a2d2718477485f7094ce57376a3c494b8c0f09933955bba8bd555ddf27f09`, under
  `replays/willow-prism-dense-vendetta-v30/batch-run-01-release-published40/`. No integration/release yet.
- The ten live v30 exploration games completed **3–7**: Fish2–3 (Swirl/Boss wins), :3 1–4 (Swirl win).
  Intake/pins are in `replays/Khaos_v30-live-UR/` and `research/khaos-v30-live-ur-intake.md`. These are live
  opponents with unexposed submission IDs, not frozen benchmark results. Four-pick Fish has five bodies
  through Cassi/Issac; five-pick Fish has six. All selected maps include Willow; Expanse is five-pick.
- Fish Shortcut `b7f1c586-dd5b-418b-ae25-7dee92ef0d06` was reproduced with exact130 Release against its
  opponent replay puppet: all26,486 inputs,1,123 round hashes and the353–1176 final result match. Raw/injected
  WASM match the qualified release. Compare SHA `ba8ba51d77fd89ff75d8713c1d8a731656b62cd1561a63365efe62416c8059d7`;
  before/after pins and audits are retained in that match's `puppet-repro/`. Native public and reproduction
  audits show zero rollovers/bot errors; local caught-act audit is also zero. The extractor's conflicting
  `faults:[1,0]` field is unresolved and is not treated as an established action fault. Exact behavior is
  reproduced by130; the server's uploaded source/version remains unexposed.
- Own-view review of that loss finds no missed eligible heal in Willow's first death sequence: no Prism or
  Marcella in view, full-health Vesper only, and no self-heal. Holes block the apparent direct south escape.
  The opening's four nonproductive support turns precede a valid240HP Marcella heal. A proposed adjacent
  basic-attack alternative was withdrawn: Elk reach is4, so the required x16 tile is exposed. No opening
  formation change is justified by that witness. Reviewing r256–262 before the chase next, using own-view
  observations rather than hidden enemy state. Note: `research/khaos-v30-fish-shortcut-review.md`.

- Fish Shortcut r256–262 resolves the camp-admission question: Willow sees the Elks asleep through259,
  does not attack them, then sees Vendetta and the newly awakened Elks at260 and reverses immediately.
  Enemy teleport/wake events explain the pressure after entry, but were not prior Willow policy inputs.
  No known-awake admission or missed-heal repair is justified by this episode. Existing farm code already
  considers allied claims; a general escort/coordination improvement needs evidence of productive support,
  rather than blindly following stale standing claims.
- Fresh :3 Monolith `03804be4-132e-412d-82f1-29ff3466bb5f` loses532–1002. Decoded actual A roster is
  P0/V1/M2/W3/HoR4; B HoR5/P6/Vendetta7/V8/M9. Willow survives, heals4042HP, captures85 gems and submits81.
  Native audit shows A0/B69 rollovers and zero Bot errors; A stdout is empty but B stdout is absent, so a
  two-sided caught-act clearance is unavailable. Public source identity is unverified. Extract
  `replays/.analysis/40b5263ca37f9876/`; event summary SHA
  `f5f2f4f06d27bf2e322370e85687d4482114df0303dd881f848460d0acc7932b`, combined view pins SHA
  `5f8e9e35f74b59d7a5d28675f308599b80023f2e16f99444772abba7f706d2cf` under the match's `analysis/`.
  These corrected sidecars point to00monolith; the original map-filename/null-hash pins remain preserved.
- Monolith actor views892–900 reveal a support hypothesis: after walking south, Willow reverses toward a
  far visible Prism at897, although his126HP deficit is below the ordinary216HP heal threshold. Four turns
  of movement do not reach heal range or produce a heal/basic. This is consistent with130's ready/zero-gain
  formation accepting any distance-reducing station toward a visible mate; visibility can extend through
  wards. Review a local, productive formation rule before expanding long-range rendezvous behavior.
  Do not infer that every moved turn was wasted without the ordinary farm alternative or source reproduction.

- Cat Monolith now has an exact130 Release/default100k puppet reproduction:37,646 input records and1,018
  round-start hashes match, including final532–1002. Compare SHA
  `77c31658e7978df54fdb0bdf2ba747808b306de2d5d27cbcea8d96302d8f2731`; source/WASM and adapter provenance
  are in the match's `puppet-repro/pins-after-run.json`. Candidate A has zero native/caught faults or
  rollovers; puppet B reproduces69 native rollovers and has zero local caught faults. The latter does not
  replace the missing original opponent stdout. Exact-source Willow897–900 view SHA
  `d3a2749b710ee60d5a1a1705d9d8e0b45e0857bc808165f1703f8ff9c9e26552`. Her far mate is visible through
  **her own ward** at16,25, not teammate-shared vision. Original server payload remains unexposed.
- The Fish economy review identifies a deficit preceding deaths: through300, captures give183 vs185 gems
  but210 vs1370 base gold (223 vs1625 paid). Our Vesper gets first gold at278; Fish Vesper has803 earned
  and165 Strength by300, versus53/60. Exact130 views39–48 show our solo Vesper taking40 camp damage per
  turn while working on two wolves, leaving49 with320HP and the first wolf still85HP; no visible enemy or
  ally explains the withdrawal. Gold pricing already includes Vesper's bonus; repeating Cassi's weight is
  not an established repair. Source hypotheses to measure are stale cached Upkeep-dependent prices and
  prospective camp recovery omitted from ranked farm cycles. No economy patch is yet justified by a
  branch/value trace. Full accounting and limits: `research/khaos-v30-fish-shortcut-economy-review.md`.
- Pure130 local-formation child **`bb836c1eb21831ffb837c8becfd5e06b3cd57c8d64565e0fbffb8b17bee509f5`**
  changes only `local_support`. Ready Willow with zero current heal gain can choose an otherwise legal
  safe station only within actual heal range/visibility, or via a strictly descending already-ready
  compatible economic route that also closes the mate gap. In-range waiting, real heals, cooldown policy,
  protected work and escape remain. Separate lazy route/progress state avoids changing older formation
  clock resets. No new field build or fuel gate. Source contract/checkpoint saved; runtime qualification
  is pending. This is a gameplay hypothesis, not a cost-only or loss-prevention claim.

- **Correction to per-champion fuel attribution:** the station-scratch report's Willow totals used a fixed
  draft-slot stride over chronological team fuel records, despite changing priorities. On monolith-heavy
  seed102407601 physicalB, that produces exactly the previously quoted83,325,221. Aligning the8,050 play
  fuel entries to8,050 native team-B actor turn-end records (after8 constants and5 draft turns) instead gives
  Willow actor8 **94,894,141**. Withdraw the prior924,670,554→924,544,872 Willow panel totals and0.01359%
  actor-specific saving until corrected across the panel. Team totals4184007689→4183581223,16/16 replay
  identity and the decision not to integrate scratch33 remain supported. This concerns chronological fuel
  attribution, not the separate native rollover event counts. Original reports are retained for correction.
- Source-only station profiler `031b86b5e22d1b0308d5e9e9501993a3b2ab13e5bf0f9acdff6e71cb7346abe4`
  has passed the one-match100M gameplay identity check:55,356 inputs,1,612 round hashes and embedded replay
  payload SHA `3ce208a971acd6e83c136a00f1f00cb92ae9f68b523426268e3deaccd81c6f85` match the saved baseline.
  Its3,259 WSP rows occupy539,480 stdout bytes, below the cap. Correctly aligned Willow fuel rises
  94,894,141→133,348,296 from diagnostic overhead; team fuel362,329,748→400,816,423. Probe/counter/logging
  overhead is not production work, and nested sampled intervals are not additive exact function costs.
  Detailed interval analysis is pending; this is not a default100k qualification or a release candidate.
- Independent actual-source review approved local-formation `bb836c…` for the bounded80-game panel.
  A separate source-only bundle `d22e3d0a60f785604d542f8bfd66acb7ae6a5db4cd02d9432f149f6a17606657`
  combines only that child, reviewed post-dash `fbb219…`, and reviewed dense draft `2dd408…`; five source
  files differ from130. Component identity/source checkpoint retained, combined review/runtime pending.

- Local-formation `bb836…` completed the published80 panel **41–39**, native play rollovers679 vs727,
  zero runner/native/caught-act errors. Its Fish Shortcut puppet control matches all26,486 inputs and
  1,123 round hashes. Cat Monolith first diverges at Willow3/r274 (End turn versus Recall), after275
  matched round-start hashes. The changed puppet outcome is not a competitive win: the recorded opponent
  becomes open-loop after divergence, and the original r897 witness is no longer a matched-state comparison.
  Artifacts: `replays/willow-prism-local-formation-v30/`.
- Combined follow-up `d22e3d…` completed the same published80 panel **34–46**, A16/B18 wins, native play
  rollovers596 vs654 and zero runner/native/caught-act errors. Results SHA
  `d9c351cd583fe89fae53676786ee42047bc0f37c206977c88aa8e53a23f67bda`; pins/audits in
  `replays/willow-prism-followup-bundle-v30/`. Generated panels are paused for interaction diagnosis;
  no changes to released130. Paired roster strata localize the shortfall: switched five-pick maps5–19,
  all other maps29–27. This localizes an interaction, not its causal branch, and does not by itself
  establish a global draft regression or Willow failure.
- Economic trace `8debb…` reproduced Fish Shortcut actions and every round hash when End/rollover are
  normalized, but added logging changes Vesper1/r31 End turn to a native rollover. It is not fuel-exact.
  Withdraw its selected-camp cycle/value attribution: one record can be overwritten by a risky candidate
  before a different final best group is reported. Repair is pending; original artifacts remain under the
  match's `economy-trace/`. Comparable PRICE rows show cached Vesper gold quotes above freshly calculated
  quotes at31/39, so these observations do not support stale underpricing as the cause of low gold income.
- Offline native-chronology correction now covers all16 parent and16 scratch-child100M archives. The
  corrected Willow play-fuel totals are **1,018,849,269→1,018,208,447** (−640,822, −0.062897%). All32 fuel
  length, inner replay/map hash and actor-sum/team-sum checks pass. Original reports remain unchanged;
  correction sidecars are `replays/fuel/willow-station-scratch-100M/actor-fuel-correction-v2.json` and
  `comparison-v2-corrected.json`. The unchanged whole-team saving remains only0.01019%, so scratch33 is
  still excluded. `tools/fuel/attribute_actor_fuel.mjs` now uses actual native actor order rather than
  fixed draft slots. No matches were rerun for this metadata correction.
- Quadrants A/035 localizes the bundle/dense first action divergence to candidate Willow3/r244 after245
  matched round hashes. Bundle moves23,2→24,3, dense23,2→23,3; both close the visible Prism gap and neither
  can heal yet. At246 bundle25,4 can heal both Prism220/700 and Marcella342/1200; dense24,4 can reach only
  Prism. Bundle heals Marcella, consistent with equal360HP gain then lower health fraction. Its own view
  does not establish a higher immediate threat to Prism, and subsequent M damage/P recall does not prove
  the choice wrong. No heal-ranking repair is justified. Both matches have only first-turn Willow
  rollovers on each side. Correct paired246–249 views use actor3/A in both archives; the initially exported
  dense8/B file is preserved as opponent/reference and excluded from the paired interpretation.
- Reviewed pair `898393116e429f7f6eb1121f2b8f1cf0eed712bcd71dff80c51479ba09417d5b` combines only
  bb836 local formation and2dd408 dense draft. Exactly3 files differ from130, exact donor comparisons
  pass; bounded published80 queued. No post-dash or economic changes entered it.
- Economic trace v3 `b7a6baf…` fails native fidelity: r31 End→rollover, r32 substantive attack→rollover,
  only33 round hashes match and65 candidate rollovers. Later39/49/64/67/72 rows are not matched-policy
  evidence. Its pre-logger31 record reports G2 clear42/damage1120/cycle48, bank_now46 and best5.07345
  versus from-altar1.91549, but is not a strict fuel-exact control. The next tracing approach will reuse
  the repository recorder/tracer harness rather than another ordinary printf replay.
- Pure130 station member-index v2 `12f3a622d3907f31f32dd34e80e9436df75f84c59f2282c32fe6846b3b2840a9`
  passed actual source review for bounded100M identity/cost testing only. Static per-tile member refs
  retain groups_near calls, original order/arithmetic and fresh dynamic reads. Lazy8×8 descriptor pages
  avoid eager full-map allocation; geometric pool growth repairs the superseded c582 child’s repeated
  exact-size reserve. No measured savings or default-fuel qualification yet.
- Pair898 published80 finished **37–43**, native play rollovers561 vs676 and zero runner/native/caught
  errors. Strata wins3p6/12,4p7/16,unchanged5p14/28,switched5p10/24. The switched shortfall exists without
  post-dash, but its difference from bundle5/24 does not by itself prove a bad post-dash branch. No pair
  integration; analysis saved in `research/willow-followup-interaction-review.md`.
- Member-index12f3 completed **16/16 exact payload matches** at explicit100M against saved130 runs.
  Team play fuel4,184,007,689→4,156,811,002 (−0.65%); native-chronology Willow
  1,018,849,269→991,551,568 (−2.68%). Heavy MonolithB saves8.42% Willow fuel; the initial sparse Swirl
  cases save only0.42%/0.13%, showing that the first four-game6.2% estimate overstates the broader saving.
  Native100M audits have zero rollovers/errors; caught actions candidate0, v29 reference1 code97 on
  huge-sharedB/r1077. Original4 cases were reused;10 remaining cases completed, and two map-not-found
  setup rows were repaired with only the missing shared-gemsA/B cases. No completed games repeated.
  Combined result SHA `5625e3d51cb2b76b55f28572fb39f02444b0879bcc65fc9cd2077423f5c22ace`; full pins/audits
  in `replays/fuel/willow-station-member-index-v2-100M/`. Pure-index native1104 qualification againstv30
  is now authorized; these100M diagnostics are not native-fuel outcomes.

- Member-index12f3 native qualification against frozen130: published80 **44–36**, native rollovers495
  versus576, then seed1023/512 **251–261**, rollovers2,103 versus2,117. Both batches have zero runner,
  native bot and caught-action errors; source and map pins match their pre-run setup. Combined295–297
  is near even and is not evidence of a win-rate gain. The separate seed1024/512 stage is running.
- The repaired repository harness now reproduces Fish Shortcut source130 at default fuel exactly:
  release and calibrated recorder match all26,486 inputs,1,123 round hashes and the final353–1176 result.
  Its adapted diagnostic tracer also matches the complete replay and all4,491 recorder call segments,
  with no missing, extra, duplicate or different segments. Evidence is in
  `replays/willow-fish-shortcut-econ-harness-v3/runs/fish-shortcut-source130-A/` (`record-validation.json`,
  `trace-validation.json`). This validates these diagnostic rows on this replay; it does not turn trace
  stdout overhead into a production fuel measurement. Fresh-price recomputation is intentionally omitted.
  Vesper31 and39 both rank the incumbentG2 highest, so this witness does not support a best/old-incumbent
  mismatch. Prism64/67/72 selects rankedG2 with71/70/70 planned walking steps and zero estimated damage;
  at67 the walk returns no-step. The higher-valued riskyG4 has27–28 steps but1,980 estimated damage.
  Route failure and safe-versus-risky selection need source diagnosis before changing economy policy.
- Source-only Willow bank-heal child `fab7c7b13e8271a933a6b7d250f4e3627f5112fc1a6d85c9d98f78b1982b7e7f`
  differs from130 only inbot.cpp. It proposes one strictly safe adjacent step for an actual worthy heal
  during ordinary nonurgent banking, using the same selected bank field with finite nonincreasing
  distance. Immediate tribute and existing pack/hop/lock/dash priorities remain; forced escape, winning,
  closing, held/contested capture and an already available current-tile heal exclude it. Equal-distance
  movement intentionally can spend one bank-progress turn for healing. Cat89 is a motivating tradeoff,
  not a proved optimal action. Actual Astra source review and native mechanism/outcome tests are pending;
  no release or canonical source change has been made.

- Member-index12f3 completed native1104: **544–560 (49.28%)** against130. Seed1024 contributed249–263,
  native rollovers1,915 versus1,919 and no runner/native bot errors. Both sides have two caught-action
  errors on this seed (codes5 and98): candidate5 on Classic/r854, reference5 on Monolith/r608, code98 on
  Hourglass/r496 for both. Total native rollovers across1104 are4,513 versus4,612 (−2.15%). Seed1024
  pick-count results are86–90/176 at3,80–84/164 at4,83–89/172 at5. Sources/maps remain pinned. This is
  a near-even cost candidate, not a measured win-rate improvement; fresh confirmation is deferred until
  the separate bank-heal panel decides whether to qualify a coherent combination.
- Astra actual-source review approved bank-heal fab7c7 for bounded runtime, with no actionable blocker.
  `research/willow-bank-heal-review.md` records current-heal/LOS semantics, strict safety, field lifetime,
  stale/hidden-block refresh and caller priorities. Its costs include delayed banking, consumed cast and
  reduced HoR missing-health damage after a heal. Cat mechanism and published80 tests are authorized;
  healing volume alone will not count as success.

- Bank-heal fab7c7 Cat Monolith mechanism check reaches the motivating state with an exact baseline
  prefix. First action divergence is Willow3/r89:130 moves32,41→33,42; child moves32,41→32,42 and heals
  visible HoR4 at28,46. Own views confirm HoR510/1000 before the cast and870/1000 next turn, with Willow
  heal cooldown7. No candidate native rollover/bot error or caught action error. The post-divergence
  puppet result1001–252 is descriptive only, not a competitive win or causal estimate. Pins/audits/views
  are in `replays/willow-bank-heal-step-cat-monolith/`; the separate frozen130 published80 comparison is
  running. The original baseline r90 state is not a matched-state counterfactual after the r89 change;
  the field-nonincreasing rejection remains source-checked rather than separately runtime-isolated.

- Bank-heal fab7c7 published80 completed **39–41**, native rollovers629 versus638, zero runner/native
  bot/caught-action errors. Source and parent pins remain unchanged. This near-even small panel supports
  further evaluation of the bounded actual-heal tradeoff, not a win-rate gain claim. Results/audits are
  in `replays/willow-prism-bank-heal-step-v30/batch-run-01-release-published40/`.
- A new source-only combination is authorized: pure-index12f3 + bank-heal fab7c7 + dense fifth-slot
  Vendetta2dd408, against130. It retains Willow, tests restoring dense-pack clearing beside her, and uses
  the static station index to reduce support cost. The earlier bb836 formation and post-dash arms are
  explicitly excluded; P67 route diagnostics and economy-price changes are also excluded. Each component
  has separate source review and a measured panel, but the combination has no measured outcome yet.
  Actual combined-source review, native1104 and an untouched confirmation suite remain required before
  any numbered release. Canonical hyperion and server40 remain130.

- Combined bank/economy source `a2794129e115abb70faaa5a7e3c66b9728898b0e52c5542fa7885091eaec0bb6`
  passed actual Astra source review. Exact donor-removal and full-patch reconstructions confirm the five
  changed files contain only index12f3, bank-heal fab7c7 and dense fifth-slot2dd408. Its published80
  panel is **40–40**, native rollovers500 versus545, zero runner/native bot errors. Candidate has one
  caught code5 (Boss Battle match054, physicalB, r589), reference zero. Archive SHA
  `dca5c3fd0801c93145c190de9b96bb855d34695dd443477f4d54b7e3459ad4c8`. The error's high-level cause is
  not established by its code; it must not be silently equated with the earlier off-map field witness.
  Results SHA `25e57a1cbff0d3017aa861fa60fee2b5f7d501392628584848ff86f6e938620b`. Generated1023/1024
  stages are authorized after the bounded P67 diagnostic. Fresh confirmation seed2026102314 is declared
  before these results but not yet generated or authorized to run.
- P67 route diagnostic source `d4a1ebf46479a6064386826334723f3f302fcc40a23639e338b29df3165a22a8` and
  helper `trace_prism_route_one.py` SHA `5f3d8ba18bfbb983d8ef9edbc23d7c232042ba2d1e218b938a3d5b61040e6244`
  passed source/tool review for one calibrated trace. Review repaired staged-source hash comparison
  against generated wrappers, exact generated-artifact pin checking, repeated stale farm rows and
  unread-neighbour labels. Diagnostic only; no gameplay edit. Full recorder/replay/call-stream equality
  remains required before interpreting any route-cause row.

- P67 route trace required a diagnostic-only const-method repair before compilation; the failed build
  and original source are retained. Corrected source `b9b731801b5b022d24ddd0c40be96f9251e00c26f7555a7a031c06cd9007f001`
  then matches all26,486 inputs,1,123 hashes and4,491 recorder call segments. Exact evidence:
  `replays/willow-prism-route-diagnosis-v1-constfix/trace-validation.json`. There is one FARM row and two
  ROUTE rows. P67 has movement, funded search, zone present, no guard, and spell mode but is too far for
  `spell_clear`. Both ordinary attack and group-adjacent routes have cap86, layers0, unreachable origin,
  zero first steps and exhausted search; neither `make_way` nor a native move succeeds. This excludes
  a finite-cap/fuel/hidden-blocked-move explanation and identifies no usable route roots. Whether raw
  geometry, zone removal or occupancy removes them still needs the four-count follow-up, now reviewed
  and queued after bundle1024. No risky-camp promotion or gameplay route change is authorized yet.
- Combined a279 seed1023/512 is **254–258**, native rollovers2,101 versus2,138, no runner/native/caught
  errors. Pick splits are78–82 at3,79–71 at4,97–105 at5. Two initial CLI setup attempts failed argument
  validation before any build/game; actual setup-v3 and all prior logs are preserved. Completed games
  were not repeated. The512 seed1024 stage is running on its separately pinned existing map manifest.
- A separate source-only next Willow arm is authorized from frozen a279: choose an actual safe heal
  among an already committed ordinary live-camp farm route's equal-best first steps when Prism cannot
  serve as the support partner. Preserve higher-priority attacks/protected work and current support
  ownership; no detour, new route search/field, per-camp board or fuel gate. When reset is ready, reject
  candidate tiles with any static camp spawn in basic range3 using at most49 direct map-grid reads,
  conservatively preserving potential post-walk camp attacks without kill prediction. This is a new
  untested source hypothesis, excluded from a279 and all running tests. Astra theory is recorded in
  `research/willow-actual-heal-admission-theory.md`; actual implementation review remains required.

- Combined a279 completed native1104 at **555–549 (50.27%)** against frozen130. Seed1024 contributed
  261–251, native rollovers1,757 versus1,802, zero runner/native bot errors and caught errors2 versus1
  (candidate code5 Classic/r854 and code98 Hourglass/r496; reference code98 Hourglass/r496). Total
  rollovers are4,358 versus4,485 (−2.83%), caught errors3 versus1. This is near-even outcome evidence
  with lower measured rollover cost, not proof of a win-rate improvement. The previously declared fresh
  seed2026102314 is now authorized for256 unused generated maps/both sides512 games after source and
  unused-seed checks. No numbered release or canonical update is authorized before that confirmation.
- P67 four-stage root-removal diagnostic is exact across the full saved replay and all4,491 recorder
  call segments. Raw attack goals28 and adjacent goals10 both become0 immediately after `off_zone`;
  unblocked and final roots remain0. Replay SHA
  `c05c31800144d24ce252d89e46c8ba5e6e331484ad5c5f332389c5f115a18f57`, validation in
  `replays/willow-prism-route-diagnosis-v1-root-removal/trace-validation.json`. This localizes the empty
  route input to zone filtering rather than search cap, occupancy or hidden movement failure. It does
  not prove the zone itself is inappropriate. A source-based feasibility repair is under review;
  no safety mask removal or unconditional promotion of the risky alternative is authorized.
- Next Willow child `bcb9c7b6935e7ed4bed39eb9abd7e540842cdb1acf3fe303a2ec5ca1ee2b639b` is source-complete
  and awaiting actual Astra review. Only bot.cpp/pathing.cpp/pathing.h differ from frozen a279. Its
  separate synchronous first-step chooser preserves the original pathing method and ranks safe actual
  heals among the selected route's equal-best steps. Source and donor reconstruction checks passed;
  no builds or game evidence yet. It remains excluded from a279's fresh confirmation.

- Astra's actual review approved exact bcb9 for bounded runtime, with no actionable source blocker
  (`research/willow-farm-heal-choice-review.md`). A separate published80 comparison against its exact
  a279 parent is authorized after heldout completion; no broad suite or release is authorized for this
  child. Mechanism evidence must distinguish an admitted choice, actual movement and actual healing.
- Cheap stdout context for a279's code5 cases shows preceding turns resumed into the error round:
  Boss Battle B/r589 follows r588 completion at589; Classic A/r854 follows r853 completion at854. The
  generic invalid-metadata/alignment/overlap/argument message does not identify the failing import or
  establish that either is the older resumed-dead-actor field query. Their cause remains unresolved.

- Frozen a279 untouched seed2026102314 confirmation completed **253–259/512**, giving exactly
  **808–808/1,616** across broad and fresh panels. Heldout native play rollovers1,662 versus1,764;
  combined6,020 versus6,249 (−3.66%). Runner/native bot/draft errors remain zero. Heldout caught markers
  are candidate2 (Classic code5/r683, Random code98/r919) versus reference0; combined candidate5
  (three code5, two code98) versus reference1 (code98). Fresh pick splits:3p77–79,4p84–84,5p92–96.
  Map index SHA `9105735b0d731fbda2a1351ed684ba148ee292fea04211145c8d0952553ee962`; results SHA
  `75d929649ec2ead75c4835ec4d976f559ce33c8c0832f5180ddfd1b222ebb64a`. Root approved promotion as
  an incremental logical/cost release under the repository's near-even keep rule, not a win-rate gain.
  Source-only Khaos_v31 packaging is queued; server submission and canonical update are not yet done.
- Cached Cat Monolith early-capital review finds comparable early base captures but different recipients:
  through100 base gold530 versus490, paid530 versus579; through200 base1,150 versus1,210, paid1,169
  versus1,458. Vesper gets one payout79 versus six totaling818 through200. Two nominated later own-view
  windows are Vesper/Prism53–56 (gem-bearing capture allocation) and Vesper82–85 (cleared group then
  off-tile healing recall, payout106). These do not establish an erroneous handoff/recall; Willow is
  distant and cannot supply an immediate heal. See `research/khaos-v30-cat-monolith-early-capital-review.md`.

- Release manifest assembly independently summed all four native audits and corrected the earlier prose
  aggregate6,025/6,304 to6,020/6,249. Per-batch audit values were unchanged; the earlier prose understated
  the candidate's cost relative to the reference. Root rechecked the four saved audit files and corrected
  the percentage above. This is a metadata/arithmetic correction, not a rerun or changed qualification.
- New Willow bcb9 isolated published80 against a279 completed40–40, rollovers516 versus529, zero runner,
  native or caught action errors. Boss Battle Willow15 moved and healed Vendetta360, but actual own-view
  review excludes this as a chooser witness: visible live Prism's recall timer4 is not a kept recall, so
  the new helper's viable-Prism gate rejects it. Preserve the descriptive view without causal attribution.
  Further qualification waits for a genuine admission-frequency/mechanism check; no policy rollback is
  justified by this small even panel alone.

- **Released exact a279 as Khaos_v31 / server41.** Root CLI submission succeeded with222187bytes,
  receipt `provenance/Khaos_v31-release/submit-response.txt`. Canonical Hyperion now matches a279. Raw
  WASM `926b82ad01addb4d7e297bc610bef6ee696f286ea3764f354b16f3c02bcced32` and injected
  `1c57fb1878b4c6eb03cf475bc116c521097b575a8134621a4e00a46866d2be91` match the frozen candidate.
  CLI bundle SHA `696249dfa82302b0f011e17449f7962dfa534628265b7d324902dffbb8b201cc`; local members
  match all30 source files. The remote uploaded ZIP was not retrieved. Fresh public team/history lookup
  returned429; the upload used the existing authenticated CLI session previously verified for Pantheon.
  Prepared-manifest review corrected a copied old reference code97 count and preserved correction
  records. The gen1023 redundant batch field and gen1024 redundant bots field are stale; actual commands,
  outputs, source hashes and results consistently identify a279 against frozen130. No games were rerun.
  The separate bcb9 ordinary-farm chooser is not included in this release.

Small diagnostic samples select follow-up analysis and broader tests; they do not establish a release threshold
on their own. Release status and actual server version belong in the numbered release provenance.
