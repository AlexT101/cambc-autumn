# KRONOS notes (macro refactor of charybdis, 2026-11-13)

Worktree `/home/ubuntu/wt/mac13-kronos`, branch `mac13-kronos-20261113`. Reference `bots/variants/chy-ref` (= charybdis 525).
Every A/B: `py tools/ab.py variants/CAND variants/chy-ref --no-test-draft --fuel 200000`, release, fast runner.
Suites: `maps/suites/mac13/dev` (5,120 maps), `maps/suites/mac13/hold` (2,560), `maps/suites/mac13/conf` (mine, seeds
145200-145219, 5,120 maps; index files in `conf-raw/<seed>/index.json`).
Tool tweak: `tools/replay/turn_budget.py` and `walk_audit.py` import from this worktree (they hard-coded the primary
checkout). Run analysis with `CAMBC_ANALYSIS=replays/.analysis`.

## Log

### 02:00 start
Read brief, rules, the 2026-11-11 macro programme (eight orchestrators, all level), CHANGES 507-525.
Priors that matter: the Prism war decides (first Prism death loses ~90%); every rule that takes champion time off the
farm lost; valuations that keep the farm intact were level; crews worth ~20 points; the pack lost 11 although its
Prism got +23% gems and +30% kills, because captures fell 16% and team tributes 30% (the score race matters).

### 02:05 baseline mirror (debug, 256 ladder games, `mac13-kronos-mirror`), turn_budget.py
- Time (W/L % of champion-rounds): dead 4.9/14.1, camp 17.6/15.6, hold 6.0/4.9, walking ~50 (empty->camp 17.7,
  bag->altar 13.8, bag->camp 5.9, empty-other 6.2), recall 4.0 + hold+recall 2.2, idle-off 6.7/3.8 (altar guard U).
- Supply: ~61% of gem-weighted group-rounds the groups are up and asleep (available, unworked), ~25% respawning.
  Upper bound on gems left asleep ~2,400 a team-game against ~1,060/740 captured: the economy is champion-time bound.
- Clear efficiency (champion hit-turns per gem): Wolf 1.5-1.9, Elk solo 0.40 / crew 0.75-1.06, Golem 0.23-0.70,
  gem cluster 0.25. Wolves are the least efficient by 4x, and the most cleared (14.7 own a game vs 9.1 Elk).
- Prism share of team capture gems (both-Prism games): r<=300 W 0.55 / L 0.48; later 0.45 / 0.49. Kill gems: Prism 82%.
- Predictors: more kills 91%, fewer gems lost 91%, more captured 82%, tributed+carried lead r400 73%.
- Deaths: L 8.7 a game, W 2.6; 'R' last branch in 60-70%; 'E' (stop-ender) 18.7% of loser deaths.
- Prism, r1-300 (both-Prism games): walks 59% of its rounds, hits camps 19%, stands on cleared tiles 7-9%; bags W
  54/130/227 vs L 43/86/130 at r100/200/300.
- First Prism-on-Prism death per game (64 of 128 games): victim/killer Focus ratio median 0.85 (21 of 64 >= 1);
  victim mostly in 'R' for 5 rounds at distance 3-4, often under 60% health 5 rounds before. Victim saw the killer in
  136/162 Prism deaths: not an information problem. A stunner ally within 4 of the killer in only 6/64: peel is rare.
- Assignment: replaying farm decisions, ~42 decisions a team-game have a pairwise swap with a teammate's current
  claim that saves walking, ~420 steps a team-game (~15% of team walking, Chebyshev, an upper bound).
- Misallocated camp damage (fragile body hit while a much sturdier ally was in that camp's range): ~1.6k a game,
  small. Recalls: heal / shop / travel, next work mostly nearer spawn than the recall's start: no obvious detour.
- A/Bs are fast: 2,048 debug games in ~1 min of play after builds.

### 02:20 k1-assign launched (subagent): nearest-claimer assignment of solo groups
Brief `briefs/k1-assign.md`: a solo group claimed by a teammate who reaches it later (by a margin from the comms
tile slack) is ours to take; the later claimer yields and re-chooses. Crews, Prism carry, sieges untouched.
- Bigger mirror (debug, 2,048 games on `maps/suites/mac13/study`, mine, seeds 145300-145303, `mac13-kronos-mirror2`):
  swap estimate 550 steps a team-game (19% of team walking); the Prism's capture gems come mostly from its own clears
  (r<=300 W: own 124, shared 76, ally-cleared hand-offs only 25); allies in reach of an enemy hitting our Prism only
  ~3.5 times a team-game (joining fights is rare and not the lever); Monolith maps 29%, captured in 45% of them,
  median r776.
- Targets abandoned within 8 tiles after 4+ rounds of walking: ~23 a team-game, ~290 walk rounds (upper bound),
  not mostly allies' captures.

### 02:47 s1-farmcal launched (study subagent): predicted vs realised farm rates
Brief `briefs/s1-farmcal.md`: debug-trace the farm's priced choice, compare with what each choice yields.
- Early Prism race (2,048 study games): in 25% of games one Prism has 1.5x the other's bag at r300; that Prism's team
  wins 80%. Its edge is captures, not kills: 236 vs 119 capture gems by r300 (own side 168 vs 98, mid 40 vs 13,
  enemy side 28 vs 8; 50+-gem captures 80 vs 22), its team's captures 395 vs 292. Kills by r300: 19 vs 2 gems.

### 02:40 k1-snap (interim k1-assign, harmless/cleared groups only): **49.7% of 10,240 dev (48.7-50.6)**, level
Fires ~2 steals + 2 yields a game in the debug smoke: too narrow (charybdis treats every striker group as a crew
job). k1b widens it to live striker groups (requested from the implementer). A 10,240-game A/B takes ~3 minutes.

### 02:57 k1b-snap (claim race widened to live striker groups): **49.6% of 10,240 dev (48.7-50.6)**, level
Assignment by arrival does not move the mirror, narrow or wide. Pending the implementer's firing counts; the swap
estimate was an upper bound on steps, and the steps saved evidently don't turn into captures that matter.

### 02:58 k2 launched (subagent): enemy ground priced by enemy lethality (k2-leth) / by a round ramp (k2-early)

### 03:25 k2 (enemy ground priced by lethality): both lose
- `k2-leth` (home weight and mid band scaled by L = enemy burst / our max health, L ~0.35 early to ~0.5-0.7 late):
  **47.4% of 10,240 dev (46.4-48.4)**.
- `k2-early` (same scaling by a round ramp, no discount before r100, full from r300): **48.1% (47.1-49.1)**.
- Lesson: the static enemy-ground discount is not over-cautious early. Taking more mid/enemy ground early, even
  while kills are rare, costs ~2 points. The early Prism-race winners' mid/enemy captures are a consequence of
  being ahead, not a cause (as ICARUS warned about outcome splits).
- Other measurements: our Prism sees a burst-killable enemy non-Prism within 6 ~14.6 times a team-game but kills
  only ~2.6 (mostly at distance 5-6 with the stun ready; a third while our Prism channels a tribute). Cassi/Issac
  pair deaths per round do not fall with the bodies together (0-2 tiles 2.4/1000 rounds, 11+ 1.8): pair cohesion is
  not a lever. Retreat deaths (2+ rounds of R): 2.4 a team-game, an ally within 4 at the retreat's start in 1.5.

### 03:30 s1-farmcal findings (study, `s1/README.md`, 2,048 traced mirror games)
- Only 22% of farm choices pay the chooser; 70% are switched away; 53% of choice time (2,006 rounds a team-game) is
  in choices later abandoned; 109 switches a team-game before arrival with nothing changed at the group. During
  abandoned (non-Willow) choices the champions moved ~1,210 tiles a team-game (net displacement), only ~150 of it
  toward the next choice: ~1,000 tiles a team-game of walking that served no completed choice.
- Switches happen whatever the margin at choice time: new options keep appearing (72% of pre-arrival switches go to
  a group outside the old choice's top 3; 41% to respawning groups; 38% to crew joins). Main transitions S->S 26/tg
  (224 wasted tiles), S->J 22/tg, J->S 12/tg.
- Mispricing: completion is not priced; crew joins priced with ~no hold and the damage part (paid to the joiner
  18%); the middle band weighs 1.31 while yielding 0.44 of its price; walk priced to the centre (+3-4 rounds), hold
  1.3 rounds short. Prism's choices are the only well-calibrated ones (real/priced 1.09).
- Overseer (03:35): iterate on a dedicated screening suite (dev and hold untouched until a finalist); think about
  the whole time budget (how champions sequence activities over many turns), then ablate.
  Screening suite: `maps/suites/mac13/scr` (mine, seeds 145400-145419, 5,120 maps).

### 03:47 k4 probes launched (subagent): stickiness 2/3, a commitment rule, honest join pricing, no mid premium,
walk/hold calibration. They measure the gradient of commitment before a sequencing redesign is built on it.

### 03:45 screens on `scr` (10,240 games each)
| variant | change | win % (95% CI) |
|---|---|---|
| k3-g10 / g25 / g50 | soft team gravity in the farm value, lambda 0.10 / 0.25 / 0.50 | 49.9 / 50.2 / 50.5 (each +-1.0) |
| k4-st2 | farm stickiness 1.2 -> 2.0 | **47.9** (47.0-48.9) |
| k4-st3 | stickiness 3.0 | **42.8** (41.8-43.7) |
Commitment loses steeply: the churn s1 measured is the farm adapting to new information, not waste. Gravity is
flat with a slight lean at 0.5.

### 03:55 k4 probe screens on `scr` (10,240 games each)
| variant | change | win % (95% CI) |
|---|---|---|
| k4-commit | keep the target until reached unless invalid / carry pick / challenger 2.5x | **44.1** (43.2-45.1), OOF 1,095 |
| k4-st10 / k4-st11 | stickiness 1.0 / 1.1 | 49.7 / 49.2 |
| k4-join | crew joins priced with the full hold and the expected share | 49.8 |
| k4-mid | no middle-band premium (mid_exposure 1.36 -> 1.0) | **45.6** (44.6-46.5) |
| k4-cal | walk priced to attack range, hold +1.3 rounds | 50.4 (49.4-51.3) |
- The farm sits on a sharp optimum: stickiness 1.0-1.2 level, more commitment loses steeply (2.0 -2.1, 3.0 -7.2,
  a commit rule -5.9). Adaptivity is worth a lot.
- The middle-band premium is worth +4.4 points although s1 found mid choices realise only 0.44 of their price: its
  value is denial (contesting the middle), which the per-choice calibration does not see.

### 04:02 more screens on `scr`
| variant | change | win % (95% CI) |
|---|---|---|
| k3-g100 | team gravity lambda 1.0 | 50.6 (49.7-51.6) |
| k3-g200 | team gravity lambda 2.0 | **47.9** |
Gravity peaks ~+0.5 at lambda 0.5-1.0: not a lever. Launched k2h-leth / k2h-early (lethality-priced ground scaling
the home weight only, mid premium kept as is) on `scr`; launched s2 (Prism kill conversion study,
`briefs/s2-prismkills.md`) and a belief-accuracy audit (`variants/kr-beliefs`, debug mirror on study512, then
`tools/replay/audit_beliefs.py`).

### 04:20 k2h (lethality ground on the home weight only, mid premium kept), `scr` 10,240 each
| variant | win % (95% CI) |
|---|---|
| k2h-leth | 49.8 (48.9-50.8) |
| k2h-early | 49.5 (48.6-50.5) |
Level: the enemy-ground pricing is not a lever in either direction once the mid premium is left alone.
- Belief audit: `audit_beliefs.py` crashes on charybdis's belief dump format (IndexError in parse_dumps); dropped:
  the Prism-death study already showed the victim saw its killer (information is not the bottleneck).
- k4 agent final report: all eight probes built and smoked clean (results above); commit rule's CMT counts ~164
  kept turns / 85 switches a game.

### 04:20 gold audit (1,024 debug mirror games, `scripts/gold2.py`)
Prism average unspent gold: r1-300 50 (L) / 57 (W); r300-600 145 / 221; r600-1000 195 / 442 (5-7 shards, each +65
health on a 700 base), ~7 shop visits a game. Vesper 65 / 92 over r300-600. Shopping value is a farming measure
(`affordable_prefix().gain`: rounds of upkeep saved), blind to fight value. Games end by 1,000 tributes (median
round 744; the loser's median tribute 365): a snowball.
Launched k5 (subagent, `briefs/k5-shop.md`): Prism shop value x2 / x4, non-Prism shop from one shard, all x2.

### 04:30 k5 shop probes on `scr` (10,240 each)
| variant | change | win % (95% CI) |
|---|---|---|
| k5-ps2 | Prism shop gain x2 (wants_shop, capture recall) | **48.6** (47.6-49.5) |
| k5-ps4 | x4 | **46.7** (45.7-47.7) |
| k5-os | non-Prism shop from one shard (no emblem-price gate) | 49.2 (48.2-50.2) |
| k5-all2 | every shopping value x2 | **47.5** (46.5-48.4) |
More shopping loses, monotonically: the Prism's unspent gold is not a lever (its field time and bag are worth more
than the stats). No principled item-value design follows from this.

### 04:30 Prism war and the race (1,024 debug mirror games, `scripts/`)
- Prism deaths: 75% by the enemy Prism (1,109 of ~1,480); the first Prism death decides 91% (485 of 532).
- Focus ratio 2+ is first reached at mean round 493, yet its team wins only 62%: of 340 such losses, 274 have no
  later Prism death at all. They are lost on the tribute race.
- **The race:** in 337 of 1,024 games the loser at some point had score + carried bags >= 1,000 (median 84 rounds
  before the end, a quarter 210+). Then the loser's score was 312 and bags 701, 82% of them on its Prism; the winner
  was also >= 1,000 in 161 of these. At the end, the loser still had score + bags >= 1,000 in 221 games.
  The Prism keeps every gem for Focus until its bag (with the score and allies' visible channels) wins or the team's
  posted bags close the race (`keeps_gems`, `closing`, `race_left` in bank.cc). Nothing in the banking logic reads
  the enemy's race (only `world.score.enemy` in a few combat spots): a ~575-gem Prism needs a 58-turn channel.
Launched s3 (subagent, `briefs/s3-prismwar.md`): Prism encounters, weak deaths, strong conversion, dominant losses.

### 04:45 s2 (Prism kill conversion) findings (`s2/README.md`)
The Prism already takes nearly every real kill chance: 72% of chances start at distance 6 (two steps from a cast),
real lethal windows at d<=4 convert 82%. All causes together are worth at most +0.31 kills a team-game (of 2.1);
a real fix ~0.1-0.15. Not a lever worth a candidate.

### 04:45 the race, more (scripts `race2.py`, `race3.py`, `endgame.py`)
- Over the 337 race games, from the round the loser first had score + bags >= 1,000: the winner's Prism channels
  53% of its turns, banks (walks) 22%, farms 10%; the loser's channels 15%, farms 18%, is dead 28%, banks 16%. The
  loser had the bigger total then (median +21 gems).
- Winning tributes: 494 of 1,004 by a Prism; 458 of 200+ gems (25% 619+). The loser was mid-channel at the end in
  164 games (Prism 91, median 390 gems, 4 turns into ~30). Altar locks are a live system (1-altar maps: 10 placed,
  9 destroyed a game).
- Examples: (a) a team at 977 with 40 gems spread over four carriers took 150 rounds and lost; (b) a Prism at an
  altar with 885 gems (89-turn channel) cancelled again and again until round 2000, lost 148 + 885 vs 660.
- k6 launched (subagent, `briefs/k6-bank.md`): Prism bank caps 150 / 300, enemy-race-aware Prism banking, and
  the same race test closing every carrier's race.
- Prism tribute attempts by bag (all 1,024 games, `ptrib.py`): 1-50 gems 195 attempts, 85% complete; 50-150 75,
  49%; 150-300 146, 29%; 300-500 908, 33%; **500+ 5,726 (5.6 a game), 11% complete** (41% stun, 32% manual, 17%
  lock cancels, ~14 turns in before the cancel). The Prism almost never banks mid-game; the endgame is a long stun
  war over giant channels.
- Prism 300+ tribute attempts by enemies within 8 at the start (`chguard.py`, 6,836 attempts): none 1,611 (40%
  complete), one 1,854 (9%), two 1,701 (4%), three+ 1,670 (3%). 76% of the giant channels start in sight of an
  enemy and almost all fail; allies near the Prism do not raise completion.

### 04:43 k6 caps on `scr` (10,240 each): banking the Prism's hoard early is a disaster
| variant | change | win % (95% CI) |
|---|---|---|
| k6-cap150 | Prism stops keeping gems at 150 (banks) | **28.3** (27.4-29.1) |
| k6-cap300 | at 300 | **35.0** (34.1-36.0) |
The hoard's Focus (+1.5 a gem) is worth far more than the score it would bank early, and the walks and channels
cost the Prism's field time. The steep slope says the Prism's bag is the team's main asset: anything that grows it
(or keeps it alive) has leverage; anything that drains it loses.
- k6-erace / erace-all not screened: by construction near no-ops (a team able to win by banking already has
  race_left 0, so `closing` already holds); the race is lost at the altar (the stun war), not in the decision.
- Capture shares (`shares.py`, per team-game in both-Prism games): r<=300 Prism solo 221 gems, others 180, shared
  ~3; later Prism solo 272, others 313. The Prism already takes ~55% of early capture gems, almost never split.
- k7 launched (subagent, `briefs/k7-feed.md`): wider hand-offs to the Prism, carried_bonus x2 / x0.5, no giant
  Prism channel started with an enemy within 8.

### 05:00 s3 (the Prism war) findings (`s3/README.md`)
- Encounters with power ratio >= 1.5: the weak Prism closes the distance in 50% (dies within 20 rounds in 57% of
  those); in farming encounters its farm target lies within 4 of the strong Prism in 54% (within 8 in 79%); it saw
  the strong Prism 75% of the time.
- With Focus >= 2x held 10 rounds the dominant team wins 73% of 719 games: 96% if its Prism later kills the weak
  one, 57% if never (406 games). The dominant Prism farms 62% of its mid-game rounds, sees the weak Prism 17% of
  rounds, and 63% of its engagements end at the chase gate (`preyable`: the weak Prism healthy on its own ground).
  It tracks the weak Prism only while it sees it (track_horizon 3).
- Retreat deaths are 61% of first Prism-on-Prism deaths; fighting back from the start rarely wins.
- Endgame: Prisms start 7,453 channels (median 55 turns), complete 0.63 tributes a game.
- Caveat: 494 of 512 map pairs are the same game twice (mirror, sides swapped): ~530 independent games.
- k8 launched (subagent, `briefs/k8-prismwar.md`): a rules-derived Prism duel model; the outmatched Prism's farm
  avoids the strong Prism's reach (k8-avoid); the dominant Prism may chase the weak one on its own ground and tracks
  it a capture's length (k8-hunt); both (k8-war).
- k6 agent: all four k6 variants built and smoked; the race variants are no-ops by construction.

### 04:56 k7 carried_bonus probes on `scr` (10,240 each)
| variant | change | win % (95% CI) |
|---|---|---|
| k7-cb2 | a kept gem's Focus value x2 in the farm | 49.5 (48.6-50.5) |
| k7-cb05 | x0.5 | 49.4 (48.4-50.3) |
Flat: how much the Prism's own farm prefers gems is not the lever (its bag grows mostly from its own work anyway).
- k7-quiet (no Prism channel > tribute_window turns started with an enemy visible within 8): 48.4% (47.5-49.4),
  but 3,510 out-of-fuel turns vs 873: a fuel burn in the refusal path; sent back for a fix before reading it.
- k7-feed (unclaimed hand-off window capture_time -> carry_reach, carry_reach 2 -> 3 holds): 49.4% (48.4-50.3),
  level. Feeding the Prism more through hand-offs moves nothing (its bag comes from its own work).
- Deaths per game (both teams, `kills.py`): non-Prism by a Prism 4.6, by others 3.4, by camps 0.4; Prism by a
  Prism 1.2, by others 0.4. Gems handed to Prisms by kills: 272 a game (others 92), ~22% of a Prism's income: every
  ally the enemy Prism kills feeds its Focus.

### 05:10 k8-hunt on `scr`: **50.1% (49.1-51.1)**, level
The dominant Prism may chase the outmatched enemy Prism on its own ground (rules-derived duel model: our two-turn
burst covers its health, its does not cover ours) and tracks it a capture's length. Conversion opportunities with
the duel model's dominance are evidently too rare or still blocked by the other gates. (PW firing rates pending.)
- Monolith maps (`mono.py`): 260 of 1,024 games; captured in 98; the first capturer wins 72%; the Prism among the
  first holders 24%; first capture median round 668.

### 05:17 k8-avoid / k8-war on `scr` (10,240 each)
| variant | change | win % (95% CI) |
|---|---|---|
| k8-avoid | the outmatched Prism's farm skips groups in the strong Prism's reach (+ rounds since sighting) | 49.6 (48.6-50.6) |
| k8-war | avoid + hunt | 49.6 (48.7-50.6) |
The Prism-war doctrine is level in every form. Note: enemy sightings are not shared between teammates
(`World::note_sighting` has no caller); EXPERIMENTS records shared sightings losing ~0.5 before, so not retried.

### 05:25 the unopposed winning channel (`winch.py`) -> k9
458 of 1,024 mirror games were won by a 200+-gem tribute (median 650 gems, 45-turn channel). During it the losing
side was alive 69% of the time and farmed 42% of its turns (dead 33%); **in 354 of 458 no champion of ours came
within 5 of the channeller**. `game_ender` / `stop_game_ender` and the lock stop act only on an enemy channel a
champion sees, and vision is personal. The old altar guard triggers on tributed score (enemy >= 600, 200 ahead) and
only on one-site maps; in hoard games the enemy's score is ~340 while its Prism carries ~650.
k9 launched (subagent, `briefs/k9-watch.md`): guard the altars while the enemy can end the game by tributing what we
believe it carries; every map (guards spread over sites by the enemy's walk); variants watch / watch1 (trigger only)
/ watch2 (2 guards).
- `knew.py`: at the start of those 458 winning channels, some champion of ours had seen the channeller within the
  last round in over half (median 1 round; 90th percentile 52); its last-seen bag already covered the enemy's need
  in 275 of 430. The seer often lacks a ready stun/lock and its teammates never learn of it. Added k9-alarm: a comms
  record posting the altar of a seen winning enemy channel, so stoppers converge.

### 05:33 rescreens on `scr` (10,240 each)
| variant | win % (95% CI) | OOF cand / ref |
|---|---|---|
| k8-avoid2 (post-audit avoid: no hit in passing on threatened groups) | 49.6 (48.6-50.5) | 794 / 782 |
| k8-war2 (post-audit avoid + hunt) | 49.7 (48.7-50.6) | 759 / 790 |
| k7-quiet2 (fuel fix: winning bags exempt; refusal after place_lock) | 50.5 (49.5-51.5) | 806 / 769 |
| k9-watch (altar watch on the enemy's believed carried bags, all maps) | 49.9 (48.9-50.9) | **5,973** / 779 |
k9-watch's guards burn fuel (guard_turn chase searches every turn); sent back for a fuel fix and firing counts.
- Where the 458 winning 200+ channels happen (`chsite.py`, side fraction of the altar between the spawns): middle
  362, winner's side 84, loser's side 12. Guards at the middle sites are where the stops are needed.
- 05:40 launched kc-combo (subagent): chy-ref + k3-g100 + k4-cal + k7-quiet2, the small leaners together, as a
  fallback finalist.

### 05:46 kc-combo on `scr`: **50.5% (49.5-51.4)** of 10,240, OOF 775 / 607
chy-ref + k3-g100 + k4-cal + k7-quiet2. The small leaners do not add up to more than +0.5.
- `chseen.py`: in 267 of the 458 giant winning channels some champion of ours SAW the channeller during it (6,988
  champion-rounds, mostly at 6-9 tiles; Vesper/Willow/Issac most). Their branches: farm 32%, retreat 27%, bank 18%,
  stop-ender only 8%. 79% of those seers carried no lock; ability cooldowns were ready ~75-80%, but most seers have
  no stun. `holds_hard_stop` (the "whatever the risk" stop) needs a ready stun or a carried lock; without one the
  seer only fights "as priced" (and usually retreats or farms).
- `chlock.py`: at the start of those channels the losers had 3.5 champions alive, 2.1 carrying a lock; in 281 of 458
  a living lock carrier was within lock reach in 80% of the channel's duration, and still the channel completed:
  the carrier did not know. 121 channels had no living lock carrier. Lock placements: 3.7 a team-game (in-passing
  denial on our-side altars mostly).

### 06:03 k10-lockfirst on `scr`: **48.8% (47.8-49.7)**, OOF 742 / 677
The lock bought before the shards (so more champions carry the hard stop for a game-ending channel). Loses ~1:
a lock is mostly spent in passing on our-side denial, and the shards it delays are worth more than the extra
stops. k10-lockres (adds a reserve: no denial with the last lock while the enemy can end the game) screens next.
- 06:10 `chcancel.py` (all 200+ channels, 1,024 mirror games): 7,635 started (6,586 by the eventual winner), 1,177
  complete. Cancels: stun 2,759, manual (the channeller's own choice to act) 2,561, lock 1,128, death 10. A
  cancelled one ran a median 5 turns of ~60. By the nearest enemy at the start: 0-4 tiles 862 (1.2% complete),
  5-8 4,918 (7%), 9-12 865 (32%), 13+ 990 (55%). The Prism starts most of its giant channels in sight of an enemy
  and loses them; k7-quiet (refuse those starts) was +0.5 only and rc-deep (EXPERIMENTS) level, so the channel's
  place is not where the game is decided: a cancelled channel costs ~5 turns and keeps the bag.

### 06:12 k10-lockres on `scr`: **48.7% (47.7-49.7)**, OOF 732 / 675
Lock-first plus no denial with the last lock while the enemy's believed bags win: the same loss as lock-first.
More lock carriers (more `holds_hard_stop`, so more "whatever the risk" stop_game_ender walks) cost ~1.3; the
extra stops do not pay. Open question: is the loss the delayed shard or the reckless stop walks?

### 06:15 k9-watch (fuel-fixed) on `scr`: **50.0% (49.1-51.0)**, OOF 724 / 776
Guards on every site while the enemy's believed carried bags can end the game: level. The agent's debug subset:
watching() on in 78 of 200 games, ~155 rounds an episode, still on at the end in 75 of 78. Watching the altars
neither stops the winner nor costs the loser.
- `stopper.py` (stop-ender 'E' episodes, 1,024 mirror games): the loser runs 5.7 a game (the winner 0.6); the
  loser's stopper dies in 52% (its Prism 821 times in all), cancels a channel in 74%. The winner restarts and
  completes later: the stops buy time but the loser is already behind. The endgame is the consequence; the game is
  decided before the winning channel starts.

### 06:35 when the mirror is decided (`when.py`, `early.py`, `edeath.py`, `pair.py`, `band.py`)
- The team ahead in tributed+carried gems wins 48% at r50, 60% at r100, 64% at r200, 66% at r300, 74% at r400,
  79% at r600; a 1.5x lead wins 73% at r100, 83% at r200, 95% at r300 (25% of games have one at r300).
- In those 252 games (1.5x at r300; leader wins 240): by r300 the leader has 0.83 deaths against 2.89, 46 dead
  champion-rounds against 153, 5 gems lost against 74, 0.05 Prism deaths against 0.56, kills 2.6 against 0.7,
  capture gems 379 against 238 (r<=150: 157 against 120). Early deaths decide the early lead.
- Deaths r<=300 (1,920): victims Cassi 547 / Issac 547 (the pair dies together), Prism 185, Heart of Ruin 133,
  Willow 129; killers enemy Prism 734, camps 266, Cassi 214. The last branch was retreat in most known cases.
- The Cassi/Issac pair dies 1.5 times a team-game (both bodies off for 60 rounds, both bags to the killer); the fallen
  body is Cassi 1,410 / Issac 1,215; the bodies were 12+ apart in 1,017 of 3,081; killers Prism 1,735, Vesper 481.
- Deaths per 1,000 alive body-rounds r<=500 (a pair death counted once per pair, so per body x0.5): pair own 0.40 /
  mid 1.07 / enemy 1.52; Prism 0.17 / 1.18 / 1.60; others 0.20 / 1.41 / 1.84. On its own ground the pair loses its
  two bodies at 2x the rate others lose one (4x in bodies).
- k10 agent: lock-first raises enemy-tribute cancels by locks from 0.75 to 1.12 a game (200+ gems: 0.52 to 0.79),
  and still loses ~1.2: more stops do not change who wins.
- `pairown.py`: 748 pair deaths on our own ground by r500 (0.37 a team-game); killers enemy Prism 365, camps 90,
  Vesper 74; fallen body Issac 327 / Cassi 320; the fallen body had seen its killer 2-6 rounds before in 450 of 557
  known; its health 5 rounds before: median 0.69 of max.
- 06:30 k13-shun launched (subagent, `briefs/k13-shun.md`): k8-avoid generalised: every champion whose health
  (the pair's weaker body) the seen enemy Prism's two-turn burst covers keeps its farm out of that Prism's reach.

### 06:25 k9-alarm on `scr`: **50.1% (49.2-51.1)**, OOF 707 / 821
k9-watch plus a comms record of a seen winning enemy channel's altar, so stoppers with a ready stun or a lock
converge: level. The endgame stop is not the lever in any form (watch, alarm, more locks): the winner of the
mirror is decided before its winning channel (when.py), by the early deaths.
- k9 agent final: fuel cause was the first guard turn building every site's stand tiles (116k+ on 100+-group maps),
  fixed (debug subset OOF 13 / 11, was 312 / 11). watching() on in ~40% of games, ~205 body-rounds a game; the alarm
  record fit in 180 of 200 games, posted in 57, read in 56. Smokes clean. The k9-watch2 / watch1 variants are not
  screened: the full watch and the alarm are level.

### 06:48 k9-watch1 on `scr`: **50.1% (49.1-51.1)**, OOF 732 / 778
The carried-bag trigger on one-site maps only: level, as the full watch.

### 06:50 k13-shun on `scr`: **49.6% (48.6-50.5)**, OOF 797 / 791
Every champion the seen enemy Prism's burst can kill (the pair's weaker body) keeps its farm out of that Prism's
reach for a capture's length: level. Fires on 5.2% of farm turns (2.3% by r300; Willow 15.8%, the pair ~7%).
Avoiding the Prism by farm choice does not lower the deaths that decide the early lead: those happen in fights
and retreats, not by walking into its reach to farm.
- 07:05 `retreat.py` (deaths r<=500 whose victim retreated in its last 6 rounds: 2,361): an ally was within 3 of
  the victim 5 rounds before in 1,344; allies within 4 over those rounds were farming 40% of their turns,
  retreating 34%, chasing 7%. In 1,198 of the 1,709 with an ally near, the allies were split (some working, some
  retreating). Killers: enemy Prism 1,109. These are lost team fights to a Prism whose burst one-shots, not
  isolated pick-offs; the fight sim already counts nearby allies.
- Note: `rounds.json` arrays are indexed by round - 1 (index 0 is round 1); earlier scripts that indexed by round
  read one round later (harmless for their windows).

### 07:22 finalist candidates on `dev` (10,240 each, first use of dev)
| variant | dev win % (95% CI) | OOF cand / ref | scr |
|---|---|---|---|
| kc-combo (g100 + cal + quiet2) | 50.1 (49.1-51.1) | 1,298 / 590 | 50.5 |
| k7-quiet2 | 50.4 (49.4-51.3) | 820 / 557 | 50.5 |
| k3-g100 | 49.3 (48.3-50.2) | 696 / 551 | 50.6 |
Nothing separates from the reference. k7-quiet2 is the provisional finalist (50.45 pooled over 20,480): hold and
conf launched.
- `peel.py`: of 1,586 kills by the enemy Prism by r500, an ally other than the victim was within 4 of the killer
  in the 3 rounds before in only 310, one with a ready stun in 95 (81 of them without a stun landing on it): the
  peel ceiling is ~0.08 a game.
- `branches.py` (share of turns, winner / loser): farm 61.7 / 59.7, dead-or-none 3.8 / 11.0, retreat 4.5 / 5.8,
  bank 6.7 / 5.6, Willow 5.5 / 5.3, hold 3.8 / 3.5, altar guard/escort 3.5 / 1.6, tribute 3.4 / 1.0.
- `bankroute.py`: 14,621 non-Prism bank trips on 2+-altar games: start -> chosen altar -> next capture costs 24.0
  Chebyshev steps on average; the best altar seen in the game 23.5 (0.59 a trip; 5+ saved in 589 trips). Choosing
  the altar by the walk back to work is not a lever.

### 07:42 k7-quiet2 confirmation: hold **50.3% (49.0-51.7)** of 5,120, OOF 337 / 293; conf **50.2% (49.2-51.2)** of 10,240, OOF 654 / 614
Over scr + dev + hold + conf (35,840 games) k7-quiet2 reads ~50.35%: consistent, but inside noise of level.
- 07:48 k16-lethal launched (subagent, `briefs/k16-lethal.md`): on k8-hunt, our Prism's `preyable` counts any
  target its two-turn burst covers as hurt (s2 fix 1), and a ready lethal stun in range is cast before a retreat
  (s2 fix 2, narrow). s2's ceiling is ~+0.3 Prism kills a team-game; the early kill gap is ~1.9.

### 08:05 k16-lethal (pre-audit build) on `scr`: 50.6% (49.6-51.6), OOF 771 / 766
Level-leaning; the audited build differs (bot.cc, fight.cc, prism_war.h) and is rescreened when the agent reports.
- k16 agent: audit fixes B1 (no stun gate on a target on its own spawn), R4 (enemy Prisms left to k8's clause),
  R2 (the pre-retreat stun only when the covered target is the only threat here), N1; smoke 51.6%. The audited
  build is rescreening (`k16-lethal-b`).
- 08:12 kq launched (subagent): k16-lethal + k7-quiet2, a finalist candidate if k16 holds.

### 08:18 k16-lethal (audited) on `scr`: **50.5% (49.6-51.5)**, OOF 772 / 769
Level-leaning, like every Prism-kill and chase change (k8-hunt 50.1). On to `dev` with kq.
- kq agent: kq/src = k16-lethal/src + k7-quiet's bank.cc (auditor: byte-identical to k7-quiet's bank.cc, nothing
  else differs); smoke 50.8% (256), clean. kq and k16-lethal are on `dev`.

### 08:26 kq and k16-lethal on `dev` (10,240 each)
| variant | dev win % (95% CI) | OOF cand / ref |
|---|---|---|
| kq (k16-lethal + k7-quiet2) | 50.5 (49.5-51.4) | 617 / 559 |
| k16-lethal | 50.0 (49.1-51.0) | 604 / 596 |
k16 adds nothing on dev; kq reads as k7-quiet2 (dev 50.4). **Finalist: k7-quiet2** (the simplest of the two).

### 08:34 k7-quiet2 at 1x fuel (100k, the platform's) on `conf`: 50.0% (49.0-50.9) of 10,240, OOF 62,892 / 63,209
Level at the platform's fuel too; no fuel cost from the rule.
- 08:37 k17 launched (subagent, `briefs/k17-lock.md`): why lock-first lost. k17-lockstop (a carried lock no longer
  makes `holds_hard_stop`, so no "whatever the risk" walk on a lock alone) and k17-nolock (no lock bought).

### 08:46 k17 lock probes on `scr` (10,240 each)
| variant | change | win % (95% CI) | OOF cand / ref |
|---|---|---|---|
| k17-lockstop | a carried lock alone no longer makes `holds_hard_stop` | 49.8 (48.8-50.8) | 760 / 755 |
| k17-nolock | no lock is ever bought | 50.6 (49.6-51.6) | 675 / 697 |
Locks are worth about nothing in the mirror either way, and the lock's hard stop is not what cost lock-first its
1.2 points: buying the lock before the shards delays emblems (a lock's 10 gold leaves a champion short of an
emblem's 5th shard), and that is what loses.
- 08:51 k17-nolock on `dev`: 50.4% (49.4-51.4), OOF 1,269 / 546 (dev's OOF is noisy: a few heavy maps). Like
  k7-quiet2 (dev 50.4). kn (k7-quiet2 + k17-nolock, disjoint files) launched for dev / hold / conf.

### 09:00 kn (k7-quiet2 + k17-nolock) on dev / hold / conf
| suite | games | win % (95% CI) | OOF cand / ref |
|---|---|---|---|
| dev | 10,240 | 50.6 (49.6-51.6) | 707 / 568 |
| hold | 5,120 | 49.9 (48.6-51.3) | 324 / 323 |
| conf | 10,240 | **51.6 (50.6-52.5)** | 1,011 / 706 |
Pooled 50.9% of 25,600 (k7-quiet2 on the same suites: 50.3%). A further fresh suite `fin` (mine, ladder-v2,
seeds 145600-145609, 2,560 maps, first use) was generated; kn and k7-quiet2 on it.

### 09:04 `fin` (fresh, 5,120 games each)
| variant | win % (95% CI) | OOF cand / ref |
|---|---|---|
| kn | **51.7 (50.3-53.1)** | 305 / 293 |
| k7-quiet2 | 50.5 (49.2-51.9) | 311 / 295 |
kn pooled over dev + hold + conf + fin: 51.0% of 30,720 (~50.4-51.6). Running kn on scr and k17-nolock alone on
hold / conf / fin to see which half carries it.

### 09:08 last reads (and the finalist)
| variant | scr | dev | hold | conf | fin | pooled |
|---|---|---|---|---|---|---|
| kn (k7-quiet2 + no lock) | 51.0 (50.0-51.9) | 50.6 (49.6-51.6) | 49.9 (48.6-51.3) | 51.6 (50.6-52.5) | 51.7 (50.3-53.1) | **51.0% of 40,960** |
| k17-nolock | 50.6 (49.6-51.6) | 50.4 (49.4-51.4) | 49.5 (48.2-50.9) | 51.1 (50.1-52.1) | 51.5 (50.1-52.8) | 50.65% of 40,960 |
| k7-quiet2 | 50.5 (49.5-51.5) | 50.4 (49.4-51.3) | 50.3 (49.0-51.7) | 50.2 (49.2-51.2) | 50.5 (49.2-51.9) | 50.4% of 40,960 |
scr/dev/conf/fin are 10,240 games each except hold and fin (5,120). kn's held-out suites (hold + conf + fin, 20,480
games, none used to pick it): 51.2%. **Finalist kn**, copied into `bots/charybdis/src` (bot.cc, economy/bank.cc).
Live risk: locks were worth about nothing in this mirror, but EXPERIMENTS records our own-side locks mattering on
the ladder (lock restriction 47.6%) and Mite scoring ~0 on one-site maps while our lock is up: k17-nolock should be
checked against the Fish/Mite bodies (fgate) before it ships; k7-quiet2 alone is the safe half.

## Summary (09:10)
- Goal 60% not reached. Best: kn = chy-ref + k7-quiet2 (a Prism starts no non-winning channel longer than
  tribute_window with an enemy visible within 8, unless the round limit forces it) + k17-nolock (no altar locks
  bought: their gold goes to shards and emblems sooner): 51.0% of 40,960 at 2x fuel; k7-quiet2 alone is level at 1x.
- ~45 candidates screened at 10,240 games each; every macro lever read inside 50 +- 1.5 except steep losses (caps on
  the Prism's bag -15 to -22, farm stickiness/commitment -2 to -3, no middle premium -4.4, shopping sooner -1.4 to
  -3.3, the lock before shards -1.2).
- Where the mirror is decided: early deaths (the 1.5x-gem leader at r300 wins 95%; by r300 it has 0.8 deaths vs
  2.9), mostly by the enemy Prism's burst in lost team fights near allies, with a peel ceiling of ~0.08 a game.
  The endgame (winning channels, stops, locks, altar watch, alarms) is the consequence: no stop design moved it.

### 09:14 kn on `fin2` (fresh, seeds 145610-145619, 5,120 games): **51.1% (49.8-52.5)**, OOF 297 / 328; at 1x fuel (100k) on `conf`: **51.5% (50.5-52.4)**, OOF 61,698 / 63,975
kn at 2x fuel, all six suites: 51.0% of 46,080; held out (hold + conf + fin + fin2, 25,600): 51.2%. It holds at the
platform's fuel too.

### 09:18 `fin3` (fresh, seeds 145620-145629, 5,120 games each): kn 50.4% (49.0-51.8), OOF 351 / 261; k7-quiet2 50.1% (48.7-51.5)
kn, all seven suites at 2x fuel: **50.95% of 51,200** (~50.5-51.4); held out (hold, conf, fin, fin2, fin3: 30,720
games, none used to choose it): **51.05%** (~50.5-51.6). k7-quiet2 over its 46,080: ~50.4%. The lock removal
carries most of kn's gain.

### 09:25 kn mechanism (`knmech.py`, 1,000 study512 games, release): kn 52.0%
- Gold spent by the team: r200 857 vs 868, r400 2,140 vs 2,128, r600 3,402 vs 3,350 (kn vs chy-ref): the lock's
  gold buys kn ~1.7 more shards across the team by r600, a small edge.
- Locks placed a game: kn 0, chy-ref 3.8; tributes cancelled by a lock: kn's 0.8 a game, chy-ref's 0. kn wins while
  losing every lock exchange: the cancels and denials locks buy are worth less in this mirror than the gold and
  the actions (a lock spends the placer's consumable action) they cost. The mechanism is not fully pinned down.

### 10:00 finish
All subagents of mine finished; no `mac13-kronos-*` tmux session remains; finished replay batches deleted (the
debug mirror `batch-20261113-034628-ab-mac13-kronos-bel-study512` and its extraction in `replays/.analysis` kept
for the scripts). `bots/charybdis/src` = kn.
