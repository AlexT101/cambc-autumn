# DIONE: macro refactor of charybdis (2026-11-13)

Reference `bots/variants/chy-ref` (= bots/charybdis at 0f6fa9879). Every A/B: candidate vs `variants/chy-ref`,
`--no-test-draft --fuel 200000`, fast runner, own drafts. Suites: `maps/suites/mac13/dev` (5,120 maps, 10,240 games),
`maps/suites/mac13/hold` (2,560 maps), `maps/suites/mac13/study` (1,024 maps, seeds 142200-142203, study only).

## Log

### 02:00 setup and reading
- Read AGENTS.md, cambc-rules.yaml, BRIEF.md, prior programmes (macro-orchestrators-2026-11-11, CALYPSO, ICARUS,
  JANUS, macro1-6). Prior lessons: the Prism war decides; the hoard is worth more as Focus than score; anything taking
  farm time lost; valuation tweaks level. The teacher shows the mirror is not at equilibrium.

### 02:05-02:25 mirror study (`mac13-dione-mirror`, debug, chy-mirror = copy of chy-ref, study suite, 2,048 games)
504 distinct games extracted to `replays/.analysis-dione`. macro_stats (winner / loser team-games):
- time: walking ~52% (move_bag 27%, move 24-25%), camp 17-19%, hold 4-5%, recall 5.5%, dead 4.1% / 11.0%.
- walks out of spawn 11.6-14.4% (mean 18 rounds) + out of recall 9.2% (mean 18): the home cycle is ~27% of alive time.
  ~40-43 recalls a team-game.
- camp damage taken 16.4k / 14.7k a team-game, champion damage 11.8k / 17.5k.
- deaths 2.2 / 6.3, gems lost at death 34 / 229, kills 6.2 / 2.1; capture gems 1060 / 895; gold earned 5302 / 4136.
- holders per capture: 1 in 98%.

### 02:25-03:35 analysis (scripts in /tmp/dione/*.py on replays/.analysis-dione)
- Completed recalls 42/team-game: 16 at full health with no gold (travel / capture recalls), ~9.5 below half health.
- Capture rates (gems per 100 alive rounds): Prism 69, Vesper 27, Marcella 30, Vendetta 25, Issac 13.5, Cassi 11.5,
  Willow 1.7. Gold earned by r600: Prism 1588, Vesper 1666, Issac 184, Cassi 135, Willow 31.
- Own-half gem capacity ~1,860 a team-game (cycles x gems, upper bound), captured by the owner 756 (41%).
- Prism-kills-Prism: killer could one-shot (1.5 F >= victim hp) in 93%; killer max HP higher in 68% (median ratio
  1.26). Killer's unspent gold median 412 vs victim 25.
- **Non-Prism deaths to a big enemy Prism (F >= 0.9 victim hp): ~1.6 a team-game; in 68% the victim itself closed the
  distance over its last 8 turns (597 of 1,583 with the Prism standing still), 80% had seen it within 5 rounds.**
- Ending a round within 4 of an enemy Prism with a ready spell and 1.5 F >= 0.6 our max HP: ~1 a team-game, death
  within 3 rounds 41% (small Prisms: 5.6%). By branch at entry: E (stop game-ender) 1.8/game 55% die, F 1.07/game 35%,
  R 1.07/game 55%, U 0.42 15%, B 0.29 35%. With 1 / 2 / 3 / 4+ of our bodies within 5 of that Prism: 51 / 38 / 33 / 24%.
- Example: d78757e3622c6b63, one shared altar: two Prisms (699-856 vs 847-1059 gems, max HP 1255 vs 2679) stood ~6
  apart at the altar for 100+ rounds; ours was one-shot (their F 1704 > our 1255 HP; our stun 1971 < their 2679 HP).
- Priors re-read: BOREAS's burst lethality for every champion (b-lethalall) read +0.8 (OOF doubled); b-outnum cut our
  first Prism deaths 16% at no win change. ATLAS's remainder after 517 (fixes 3, 5, press) ~+1.3 at 2x fuel only.

### 03:35 launched
- implementer: `chy-atlas` = chy-ref + ATLAS remaining-after-517 (fixes 3, 5, press, floors). A base component.
- read-only study agent: systematic macro mistakes in early-decided mirror games.

### 02:40 walking waste (/tmp/dione/walkwaste2.py, 40 games, legs of 4+ consecutive moves vs BFS shortest path)
- Overall walked turns exceed the BFS path between leg ends by 31%.
- Farm legs with no enemy within 9 and one target: 0% waste (paths are optimal). Farm legs with an enemy within 9
  and the target changing mid-leg: 19.6% of all walking turns, 48% waste = 9.4% of all walking. All enemy-near legs
  together (F, B, R, Prism, Willow) carry ~25% of all walking as excess steps: champions dither near enemies (walk to
  a target the guard then blocks, switch, come back). farm.cc's group choice has no dynamic enemy term (only crews
  and Monoliths look at enemies), so the target near the enemy stays best and the step guard stalls the walk.
- Prism casts per 100 alive rounds: at camps 3.0 (stun slot) + 3.25 (ground), at champions 1.85; cap 12.5 a slot.
- Monoliths: 125 of 504 games; nobody even hits one in 72 of them; first hit median r540; 94 captures, median
  55 rounds first hit to capture, 5.2k damage taken, 4 attackers, 256 gems.
- Willow heals 14.9 HP a round vs ~52 capacity.
- P(death within 10 rounds) of a non-Prism by Chebyshev distance to the enemy Prism, when its burst 2.5 F >= our
  health (150 games, /tmp/dione/risk.py): alone d3 .66, d4 .49, d5 .37, d6 .10, d7 .08, d8+ ~.05; with 2+ allies
  within 5: d4 .28, d5 .18, d6 .11. Against a small Prism: d<=5 ~.05-.07, far .01. The AoE reach (5) is a kill zone;
  ~65 champion-rounds a game are spent in it.

### 02:47 study agent report (15 games studied, patterns quantified over 504; scripts in /tmp/dione-study/)
1. Weaker Prism within reach of a stronger one (biggest). Prism kills are CC (1.5F + stun) then AoE (1F) = 2.5F with
   no reply, often on the killer's double turn. Death within 2 rounds at d4 35%, d3 40%, d2 60%, d5 8%, d6 1% (enemy
   spell ready, 2.5F >= our hp). Before r400, rounds within 5 of a Prism that can kill ours while ours cannot kill
   back: losers 504, winners 134 (154 games). 75% of first-Prism-death victims ended the round before within 4 of the
   killer; victims were farming/retreating near it. 1,105 non-lethal pokes on a Prism that can kill back (85% by the
   eventual loser; poker dies 22-38% within 2 rounds); 665 in R, 314 in E. retreat() pins the Prism with a cast when
   escape_walk finds no safe step, but the mistake is getting to 4 at all.
2. Prism capture race: Prism capture-gem lead at r300 predicts wins more steeply than allies' (+160: 79%, -160: 21%).
   ~30 gems/team by r300 go to an ally capturing while the Prism stands within 4.
3. Stop-ender "whatever the risk": our Prism in E within 5 of a stronger ready Prism: 1,154 rounds, 32% die in 2
   rounds, 0% kill it; 38 of 246 first Prism deaths in E. The ender cancels on its own when threatened.
4. Cassi & Issac: 1.55 pair deaths a team-game, 57% with the partner 6+ away, 55% by a Prism.
5. Retreat/farm oscillation (minor).

### 02:50 candidates in flight
- `chy-atlas` (ATLAS fixes 3, 5, merge fixes, press, fuel floors; + 3 port fixes: bag focus kept under the floor, the
  press's fall test as 520/525's, no recount of our own actions in press_damage). Smokes 50.8 / 49.2 of 256. Dev A/B
  `mac13-dione-atlas` running.
- `dz1` (implementer): kill-zone macro on chy-atlas: one-sided killer zones (burst incl. the stun's handed-back turn
  >= our health; reach 4 unit stun / 5 with ground spell / +1 on a double turn) priced in farm choice (factor on
  worth, hysteresis), goal walks, retreat, strike plans ending in a zone, bank altar choice, and stop-ender waiting at
  the zone edge until it can arrive and act in one turn.
- `probe-idle` (measurement): farm branch idles 1 turn in 20, to read how farm time converts to wins.

### 02:53 result: chy-atlas dev **50.1% of 10,240 (49.1-51.0)**, OOF 959 vs 693. Level: ATLAS's +1.3 at 2x (on
charybdis 515) does not reproduce on 525. Kept only as dz1's base (no harm, no gain). A dev A/B takes ~3 min wall.

### 03:01 probe-idle (farm branch idles 1 turn in 20 = ~3% of all turns): **42.4% of 10,240 (41.4-43.3)**
Farm time converts to wins at ~2.5 points per 1% of champion turns. The mirror is far from flat in efficiency: any
real time saving is strongly leveraged. Farm-turn classes (30 debug games, /tmp/dione/prog.py): progress toward the
target 60%, hitting camps 29%, at target (<=3) without hitting 4.2%, stalled 4.0%, stepping away 2.3%, no target
0.6%. With walking ~56% of champion-rounds and ~31% of walked steps excess over BFS (most of it enemy-near), excess
steps are ~17% of champion time: the largest recoverable block. Dead time 7.6%; C&I pair deaths (1.55 a team-game)
cost 120 body-rounds each.
- 03:05 launched `tp1` (implementer, on chy-ref): farm trips priced on a per-turn flood that avoids the step guard's
  enemy-reach tiles (never shorter than static steps, so prune bounds hold), a commitment rule on guarded trips, and
  the goal walk following the priced route. Unchanged with no threats listed.
- Waiting at the farm target without hitting (4.2% of farm turns): 77% at a respawning group (respawn waits).

### 03:25 suites (overseer note): iterate on `maps/suites/mac13/screen` (seeds 142210-142229, 5,120 maps); keep
`dev` and `hold` for keep/drop reads; `conf` (142230-142249) generating for the final confirmation.
- dz1-s1 (dz1's pre-audit snapshot) on dev: **49.8% of 10,240 (48.8-50.8)**, OOF 1118 vs 689. Level.
- dz1-s1 replays (998 dev games, /tmp/dione/abstats.py, timeshare.py): our deaths 7.6 vs 9.5 a game (-20%), dead
  rounds 441 vs 555, rounds in a burst-capable Prism's zone 17.6 vs 24.9 (Prism 2.8 vs 4.8), lost gems 141 vs 159,
  gold earned 6921 vs 6770 — but capture gems 896 vs 902, Prism capture gems 323 vs 332, and wins 49.0%. Time shares
  (cand vs ref): dead 6.7 vs 8.4, still (off camp tiles, not hitting/fighting/tributing) 8.8 vs 7.6, walk 34.6 vs
  34.8, walk_bag 25.7 vs 25.4, camp 14.1 vs 14.0. The time saved from death went into standing still, not farm:
  avoidance without a productive alternative buys nothing.
- tp1-s1 (pre-audit) on dev: **48.9% of 10,240 (47.9-49.9)**, OOF 724 vs 635.

### 03:50 tp1 final: screen **50.0% of 10,240 (49.0-50.9)**, OOF 799 vs 546. Level; dropped.
Implementer's diagnosis (debug batch): farm-near-enemy waste fell only 1.6 points. Pure-farm legs near enemies
already walk shortest paths; the excess sits in legs mixing farm with other branches: farm+retreat 6.4% of all
walking, farm+retreat+other 2.5%, farm+chase+retreat 1.9%. The pattern: farm walks toward an enemy, want_home /
retreat sends the champion back, farm sends it in again. Target pricing can't fix it; the fix belongs where farm's
goal walks and the retreat trigger disagree.
- Farm/retreat ping-pong in the mirror (200 games, D lines, /tmp/dione/osc.py): 59 F->R->F cycles a team-game
  (retreat run median 1 turn, farm resumes median 2 turns), 45 R->F->R with a short (<=10) farm interlude, ~108 farm
  turns a team-game inside those interludes.
- dz1 final (implementer report): bodies end ~60% fewer turns within 4-5 of a burst-ready enemy Prism than chy-atlas
  and die near one ~70-75% less (d<=5 deaths in 3 rounds 1.41 vs 4.94 a team-game; our Prism as victim at d<=4 0.53
  vs 2.20). OOF 35 vs 17 in 256 games. Smoke 52.0% of 256. Running screen + dev.
- **dz1 final: screen 50.2% of 10,240 (49.2-51.1), OOF 1104 vs 585; dev 49.8% of 10,240 (48.9-50.8), OOF 1239 vs
  634.** Level despite ~70% fewer deaths near burst-ready Prisms. Deaths avoided by avoidance are not converted.
- 04:05 probe battery launched (one-constant copies of chy-ref on screen): mid_exposure 1.8 / 2.4, home_power 1.2,
  max_wait 6, recall line x0.79, gold price x1.5, chain_bag_limit 40, pick_up_radius 12. Purpose: find macro
  dimensions with slope (the constants were fitted on ocean-era bots, before the carry economy).
- Gold: capacity ~18k a game (both teams), taken 33%; harmless pure-gold groups capacity ~1.6k, taken 37%.

### 04:20 probe battery (one-constant copies of chy-ref, screen, 10,240 games each)
mid18 50.1, mid24 **48.6** (47.6-49.5), home12 50.1 (OOF 1031 vs 578), wait6 **49.0** (48.0-50.0), rhf25 50.4,
gold15 49.4, chain40 49.3, pick12 50.5. Flat: the constants sit on a plateau (as earlier programmes found). A map,
not a direction. Dirs `bots/variants/pb-*`.

### 04:25 where games are decided (dz1 dev replays, 1,000 games; mirror 504)
- Median game r1080 (quartiles 798-1524); the winner reaches 1000 tributed while the loser has ~340 + ~160 carried.
- **First Prism death decides: the killer's team wins 89%** (mirror: 246 of 504 games have one; median r440, killer
  Prism's bag median 340 vs victim's 171; 163 of 246 by the Prism, 33 by Vesper; victim the weaker Focus 71%).
- dz1: our Prism died first in 205 games, theirs in 259 (wins 10% / 89%), but the 536 games with no Prism death went
  only 47%: avoidance turned would-be Prism deaths in games we were behind into slow losses (a selection effect), so
  saving the Prism does not recover the lead. dz1 dev also: deaths 7.7 vs 10.1, dead 6.6% vs 8.6%, capgems 884 vs 878,
  gold earned 7291 vs 7073, still 9.1 vs 7.9.
- Kill gems: 142 a team-game, Prism takes 101; allies landing kills with our Prism within 4: ~11 gems. No lever.
- Final winning tributes: bimodal (201 under 5 turns, 195 of 30+ turns, Prism 236 of 496); the loser is 12+ tiles from
  the altar in most. Late denial is no lever (the loser is far behind by then).
- Groups sit alive and untouched at full health much of the game: gem clusters 28%, gem+wolf 41%, elk+gem 36%,
  Monolith groups 82%. Capacity is not saturated: the economy is walk-bound (every type walks 55-60% of alive time).
- Per-type time: C&I hit camps 19-20% but capture little (the carry hands captures to Prism); Prism tributes 8.6% of
  its time, walks 57%.

### 04:35 coh1 launched (overseer: make the decision layers agree)
Implementer brief `/tmp/dione-briefs/coh1.md` (copied to research/mac13-dione/briefs/coh1.md): one give-way verdict
(want_home's enemy predicates as a per-tile function) shared by farm target choice (infeasible targets dropped for the
next best in the same turn), repelled-target memory keyed on the threat, retreat hysteresis keyed on facts once a
target was entered with a plan, goal walks avoiding give-way tiles. Diagnose which want_home predicates drive the 59
F->R->F cycles first. Snapshot `coh1-s1` when it first builds.
- 04:50 dzab launched (ablation agent): dz1 split into Prism-only, allies-only, no-pricing, no-ender; screens.
- No-Prism-death games (mirror, 258) end fast (median r656) and are a farm race: the winner leads captures +33 at r400
  (P 0.72), Prism Focus no different (P 0.48). Prism-death games: Prism Focus lead decides (P 0.83 at r600).
- Capture gems by map side, winner vs loser a game (mirror): own half 762 vs 719, middle 137 vs 76, enemy half 128 vs
  89, Monolith 32 vs 12. **The middle and the enemy half are the differentiator (+100), own half nearly level.** In
  r0-300 the winner's Prism takes 42 gems off its own half vs the loser's 22. Middle groups sit untouched 64% of the
  game. Stolen captures (cleared by one team, captured by the other) are rare: 1.2 a team-game.

### 04:45 dzab (dz1 ablations, screen, 10,240 each; dz1 itself 50.2)
prism-only 50.0 (49.0-50.9), allies-only (our Prism without zones) 51.0 (50.0-51.9), noprice (no farm/bank zone
use) 51.1 (50.2-52.1), noender 50.4. All within noise of dz1; the Prism's own avoidance and the pricing read slightly
negative. OOF ~2x chy-ref. Dev reads of allies and noprice running (`mac13-dione-zab*-dev`; a first attempt was
killed by the ablation agent's cleanup glob).
- dzab dev: allies-only **50.1%** (49.1-51.1), noprice **50.5%** (49.6-51.5) of 10,240. Level: the dz1 line is closed.
- Deaths by branch over the last 4 turns (mirror, D lines): our Prism's deaths 49% in retreat, 37% in the
  stop-game-ender; C&I's 38% farming, 34% retreating. Tribute cancels cost ~42 turns a team-game (stun 23, lock 10).

### 04:55 farm trips (mirror, /tmp/dione/trips5.py; a trip = a run of F turns on one farm_group)
Non-Prism farm turns: own capture 28%, ally took it 22% (the carry), enemy took 5%, ended in retreat 11%, hit then
switched 9%, **walked toward a target then abandoned it without hitting 14-17% (~47 trips a team-game)**; those walks
made ~31% progress toward the next target: ~200 wasted turns a team-game (+~40 for the Prism), ~5% of team turns.
Of the 47: a mate targeted the same group in 22.5 (10.6 the mate on it and in sight when we started, 7 joined later,
4.9 unseen at start); no mate 24 (respawning throughout ~20, asleep alive ~16, overlapping); an ally nearer at the
switch in ~30. Two failures: duplicate targeting, and target instability without new information.
- 04:58 launched `fc1` (implementer, brief research/mac13-dione/briefs/fc1.md): diagnose switch causes, then
  team-consistent assignment (crew sizing in the choice, symmetric tie-breaks on claims/ETA) and consistent pricing
  (stable beliefs until an observation, no drift-driven switches). coh1's early debug run (`coh1-v1`, 2,048) read 43.3%:
  the implementer is iterating.

### 06:25 coh1 report (final `bots/variants/coh1`, diff patches/coh1.diff): level
- Final = shared give-way verdict (`gives_way(p)`, memoised), steer_off (next step off give-way tiles when an equally
  short one is clear), a step plan that may override want_home's zone/lost-stand answer. Dev **50.0% of 10,240**
  (OOF 1,301 vs 620) as `coh1-f1`; the full design with target exclusion + repel marks (`coh1-f2`) dev 49.3%.
  Study reads (2,048 each): v1 (exclusion + steer + plan) 43.3; without exclusion 51.1; steer only 49.6; exclusion only
  for repelled 49.1; audit fixes applied to the full design 45.5.
- **Diagnosis (2,048 debug mirror games): `stand_lost_at` drives 83% of F->R->F cycles** (zone 9%, Willow 5%, recall
  line 2%). At those retreats our champion had walked in 3x as often as the enemy walked up. 41% of S retreats right
  after a step priced clear had the same enemy distance and health: **the verdict flips with turn order** (S retreats
  breaking a farm run are 2.3x as common in rounds we act first; how many enemy turns precede ours alternates).
- Cycles fell only 20% (61.9 -> 49.6); farm share unchanged; OOF doubled.
- Lesson (with dz1, tp1): **excluding contested targets loses (43-46%)**; the near-enemy "waste" is the price of
  contesting ground, and ceding it costs more than the walking saved.
- 06:27 launched `pi-safe` / `pi-near` (probe-idle's 1-in-20 idle gated on no enemy within 10 / an enemy within 10) to
  split the -7.6 of probe-idle into safe farm time vs near-enemy turns.

### 06:40 fc1 report (final `bots/variants/fc1`, patches/fc1.diff): level
- fc1-s1 (pre-audit) screen **50.0% of 10,240** (OOF 515 vs 569). Final: study 51.8% of 2,048; screen run pending.
- Diagnosis of switch causes (turns a team-game, non-Prism): respawning target came due elsewhere 46 (mates on it) +
  31 (unclaimed); a mate's claim left the new group 31; old group's respawn wait grew (new timer read) 27; help calls
  24; joining a mate's claim ~48; drift with no new information 15; other claim moves ~40. **Almost all switches
  follow new information**; drift is small.
- What lost: ETA-then-index claim ownership 32.8 / 43.8 / 44.6 (unseen mates' positions stale 18+ rounds; claims
  flicker to -1 on retreat/shop/death; mirrored yielding); walking to a pending respawn early 42.8-48.1 (still time
  7.6% -> 13.4%: arriving early idles). What remains in fc1 (a fill-in for doomed picks) rarely fires.
- Dash use in safe space is already near cooldown (ready-but-walked 4-8% of moving turns); near enemies the dash is
  held 38-45% (reserve). Not a lever.

### 06:40 idle split (pi-safe / pi-near, screen 10,240 each)
- **pi-safe (idle 1 in 20 farm turns only with no enemy visible within 10): 43.3% (42.4-44.3).**
- **pi-near (only with an enemy within 10): 49.8% (48.8-50.8).**
- Safe-space farm turns carry nearly all of probe-idle's -7.6: about -1.8 points per 1% of farm turns idled there.
  Near-enemy farm turns are worth far less (about a quarter of the farm turns are near enemies, so an equal value
  would have cost ~-2.3). This explains dz1/coh1/tp1: they changed near-enemy turns, which are worth little.

### 06:50 home cycle (mirror, /tmp/dione/home2.py, 200 games)
~42 completed recalls a team-game: from farm at full health 13.3 (travel), 50-90% health 8.5, <50% 4.6; from holds
5.5; from retreat 4.0; respawns 5.2. Median 15-19 rounds from arrival to the first camp hit or capture share:
~1,000 rounds a team-game (~20% of team turns) plus the channels, all in safe space.
- 06:52 launched `hc1` (brief briefs/hc1.md): diagnose why farm-branch recalls happen, then cut avoidable ones
  (harmless groups for hurt champions, heal trips that pay, Willow field heals) with derived pricing.
- 06:55 launched `rk1` (brief briefs/rk1.md): port ocean 507 comms slots (told tiles), claims that persist through
  retreat/shop/recall, shared respawn knowledge; the information-driven switches.
- Both report by 08:15. Decision reads after that: dev, hold, conf.
- fc1 final screen **50.1% of 10,240** (49.1-51.0), OOF 518 vs 577. Level; closed.

### 07:40 hc1 report (patches/hc1.diff): level
- hc1 final screen **49.95% of 10,240** (48.98-50.92); hc1-s1 49.92.
- Recall causes (per team-game, 400 debug games): travel (farm priced spawn as sooner) 18.9, capture recalls
  (banking rides) 16.8, heals below the recall line 2.3, camp_fled 1.8, shop 1.5, bank 0.7. The targeted cause (hurt
  champion skipping harmless work) is ~1.8; the large buckets are trips the bot already prices as the fastest route.
  Home->productive rounds unchanged (1,028).
- rk1-s1 (port of ocean 507 told tiles + persistent claims) screen **50.7% (49.8-51.7)**; rk1-h1 48.7; rk1-h2 50.4.
  rk1-s1 dev read running.
- 07:42 launched `pz1` (brief briefs/pz1.md): a dominant (one-sided safe) Prism prices gems with a denial share q
  (the enemy's otherwise share by walk geometry), so it farms the middle and enemy half where its gems come out of the
  enemy's share and its presence zones enemy bodies. Deadline 08:55.
- rk1-s1 dev **50.8% of 10,240 (49.8-51.8)**, OOF 611 vs 691; with screen 50.7: ~+0.75 over 20k. Hold read running.
- rk1-s1 hold **49.6% of 5,120 (48.2-51.0)**. Pooled over screen+dev+hold 25,600 games ~50.5%: level.

### 07:50 rk1 report (final `bots/variants/rk1` = rk1-s2, patches/rk1.diff)
- rk1 = ocean 507's comms slots (told tiles; an unseen claimer counts in its group's crew by its told tile), applied
  cleanly to chy-ref, plus the 8-round claim refresh held for two turns. Screen **50.8% (49.9-51.8)**, OOF 553 vs 573.
- Held claims (intent kept through retreat/shop): 48.7 raw, 50.4 with audit fixes; switched walks barely move (the
  walks move to other groups), deaths +3-10%. Dropped.
- Respawn sharing: the camp records already carry it (84 posts / 391 reads a team-game); nothing missing.
- Running rk1 on conf (10,240) and dev (10,240).
- rk1 (final) conf **49.4% of 10,240 (48.4-50.4)**, OOF 625 vs 700; dev **50.3% (49.3-51.2)**. Pooled with screen 50.8: ~50.2 over 30,720. Level.
- dzab-noprice hold **49.4% of 5,120**, conf **50.4% of 10,240** (OOF 1,147 vs 659). Pooled over screen+dev+hold+conf
  (35,840) ~50.5%: level. rk1 pooled (rk1 + rk1-s1, one line apart, 56,320 games) ~50.3%: level.
- pz1-s1 screen 50.1, pz1-s2 screen 50.1: level (report pending).

## 08:17 cr1 (capture recall consults carry_bag's chain decision) — level/negative
- Measure (debug study, behaviour-identical trace): 18.2 capture recalls per team-game; 77% have a post-payout bag below
  the EOQ floor (7.2k of them gold-only rides), 4% would chain; only ~19% are rides carry_bag would bank.
- Gate in capture_recall refusing rides below floor / when may_chain holds (exceptions: winning bag, want_home).
  Screen **49.4% of 10,240** (48.4-50.3); smoke 48.4. The rides below the floor are not wasted: the ride doubles as the
  shop/heal trip and moves the champion safely, so farm's "capture rides home" pricing is the better model. Dropped.
- pz1-s3 screen 50.2 of 10,240. pz1 s1/s2/s3 all 50.1-50.2: level.

## 08:21 pz1 (dominant Prism values enemy-side gems at 1+q, denial share) — level
- Dominance (seen all enemy Prisms, Focus >= 2x, top-two enemy strikes < our health) holds only 45 farm turns a game,
  in 36% of games, median first round 310: too rare and late to move the race. Prism capture split barely moved
  (middle 55.0 vs 52.7). Screens: s1 50.1, s2 50.1, s3 (measured split q) 50.2, all 10,240; study 48.6. Dropped.
- First Prism death (study): cand's died first in 27.3% (cand wins 12.1%), ref's in 26.6% (cand wins 82.0%).
- 08:18 launched rk1np = rk1 + dzab-noprice (both ~+0.5 alone, disjoint files) to test whether they stack.

## 08:35 rk1np = rk1 + dzab-noprice (which is dz1 with kz_price off) — best pooled, still level
| suite | games | win % | 95% CI | OOF cand / ref |
|---|---|---|---|---|
| screen | 10,240 | 51.0 | 50.0-52.0 | 1,067 / 598 |
| dev | 10,240 | 50.7 | 49.7-51.6 | 1,203 / 633 |
| hold | 5,120 | 50.0 | 48.6-51.3 | 553 / 315 |
| conf | 10,240 | 50.3 | 49.3-51.3 | 1,189 / 614 |
- Pooled 35,840: ~50.57% (~50.05-51.1). Stacks a little over either part (rk1 pooled ~50.3, noprice ~50.5) but no more.
  OOF ~1.9x the reference's (the kill-zone model's fuel); at 2x fuel it is not a loss here, but on 1x it would need the
  model's fuel cut first. The patch is `patches/rk1np.diff`.
- 08:34 launched rk1npz = rk1np + pz1-s3 (farm.cc three-way merge).
- 08:41 rk1npz (rk1np + pz1-s3) screen **50.9% of 10,240** (49.9-51.9; OOF 1,102/591) vs rk1np 51.0: pz1 adds
  nothing. Not taken to decision suites.
- 08:36 launched rk1np-f: exact (behaviour-identical) fuel cuts in the kill-zone model to bring OOF back down.

## 09:15 rk1np-f (exact fuel cuts in kill_zone) — no fuel to cut
- Profile (self-play, 8 screen maps, 1M fuel): rk1np vs rk1 heavy (100k+) turns 2,682 vs 1,525, but total fuel only
  +2.8%. The extra is spread over fight sims (trade, chase_trade, update_champion, plan_strikes...): rk1np is simply
  in more fight turns. The kill zone itself costs ~4% of a heavy turn; dz1's `press()` + `press_taken` ~12%.
- Two exact cuts kept (bench identity 128/128 at 100M; fuel +0.004%: nothing). Screen 51.0% of 10,240, OOF 1,034/615.
  The extra OOF needs a behaviour change (gate press / its eager press_taken), not a fuel-exact patch. Not pursued.
- 09:16 fresh suite `maps/suites/mac13/fin` (seeds 142250-142269, 5,120 maps): rk1np and rk1 both read on it.
- 09:20 fin (fresh, 10,240 games): rk1np **50.9** (49.9-51.8; OOF 1,366/682), rk1 **51.0** (50.1-52.0; OOF 742/657),
  dzab-noprice **50.2** (49.3-51.2; OOF 1,265/629).

## 09:25 Final pooled reads vs chy-ref (2x fuel, all 10k blocks except hold's 5,120)
| candidate | screen | dev | hold | conf | fin | pooled (46,080) |
|---|---|---|---|---|---|---|
| rk1np (rk1 + dz1/noprice) | 51.0 | 50.7 | 50.0 | 50.3 | 50.9 | **~50.64% (~50.2-51.1)** |
| dzab-noprice (dz1, kz_price off) | 51.1 | 50.5 | 49.4 | 50.4 | 50.2 | ~50.42% |
| rk1 (comms told-tile slots) | 50.8 | 50.3 | 49.6 (s1) | 49.4 | 51.0 | ~50.29% |
- The two parts add (0.42 + 0.29 against 0.64 measured). rk1np copied to `bots/charybdis` on this branch.
  The goal (60%) is not met: every macro redesign this session read within ~1 point of the reference.
- 09:30 var (fresh `--mix varied` stress suite, seeds 142270-142289, 10,240 games): rk1np **51.2** (50.3-52.2;
  OOF 1,565/1,121), rk1 **50.2** (49.2-51.2). rk1np holds up on stress maps; with var its pooled read over 56,320
  games is ~50.7%.

## 09:36 Ablation: rk1np-nopress (dz1's disarm press never weighed; one param) — press kept
| suite | rk1np-nopress | rk1np | OOF nopress / rk1np |
|---|---|---|---|
| fin | 50.9 | 50.9 | 981 / 1,366 |
| var | 50.5 | 51.2 | 1,318 / 1,565 |
| dev | 49.8 | 50.7 | 950 / 1,203 |
- nopress 50.4% vs rk1np 50.9% over the same 30,720 games: the press is worth ~+0.5 (noise-level) and is where
  roughly a third of rk1np's extra OOF turns come from. Kept in charybdis; on 1x fuel its gate wants a look.
- conf: nopress 50.3 (OOF 937/576) vs rk1np 50.3. Over 40,960 shared games nopress ~50.4 vs rk1np ~50.8.
