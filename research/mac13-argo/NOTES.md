# ARGO: macro refactor of charybdis (2026-11-13)

Reference: `bots/variants/chy-ref` (frozen charybdis 525). Every A/B: candidate vs chy-ref, `--fuel 200000`, own drafts.
Suites: `maps/suites/mac13/dev` (5,120 maps), `maps/suites/mac13/hold` (2,560), `maps/suites/mac13/ana` (2,560, seeds
140200-140209, analysis only: the mirror study, never an A/B read).

## Log

- 02:00 mirror chy-ref vs chy-ref copy on `ana` (5,120 games, all replays kept) for the loss scoreboard.
- 02:04 mirror done: 50.0% of 5,120 (identical bots; 3 min wall). A/Bs are very cheap; implementation is the bottleneck.
- 02:10 prior-programme digest (subagent) read. Key priors: games ~850 rounds, 97% end on 1000 gems; Prism duel decides
  (first Prism death loses ~88%); Prism hoard worth ~21 points; supply is labour-bound (own groups up and unworked
  ~54%, both teams capture ~36% of production); walking ~50% of alive time, recall/spawn cycle ~27%; mid captures
  separate winners; ocean's +8 came from routing gems into the Prism (carry/funnel/hold). Soft coordination terms,
  packs, rallies, escorts and one-knob scans were all level or lost.
- 02:08 scoreboard study delegated (analyst subagent): research/mac13-argo/scoreboard.md when done.
- Overseer addendum: use large two-direction probes on central behaviours to locate levers (10+ points on 3-5k games),
  then build a real design on the lever. Fixed 10k blocks for 1-3 point effects.
- 02:13 probe suite `maps/suites/mac13/probe` (seeds 140210-140219, 2,560 maps) for lever probes only. A subagent builds
  12 large one-knob probes (pb-*: bank floor x3 / x1/3, crews bigger / smaller, enemy-ground discount off / x2.6,
  rate horizon x0.4 / x2.5, camp risk bold / shy x2, life value x0.5 / x2). Purpose: locate levers and their
  asymmetry, not candidates.
- 02:25 own quick reads on the mirror (scripts/endcarry.py, scripts/race.py; 2,560 distinct games, team A won 48.2%,
  98 games reached r2000): the loser ends with a median 87 carried gems (winner 14); 22% of losers hold a 400+ bag at
  the end, 15% are channelling a tribute when the game ends. In 11.6% of games the LOSER reached 1000 wealth
  (tributed + carried) first (by a median 29 rounds) and still lost: a conversion race lost. The winner takes a
  median 56 rounds (IQR 22-132) from 1000 wealth to its win: the final tribute is long (ceil(bag/10) turns) and
  restarted after cancels. Upper bound for conversion alone ~+3-6 points; not the whole 10.
- 02:22 scoreboard.md (analyst). Breaks: median b0 r403; 72% gradual and farm-built, 20% jumps (69% an L Prism death),
  8% bank (L ends richer, W tributes first). Before the break W and L behave the same (all |dz| < 0.25): the mirror's
  outcome is noise compounded. Whole-game margin +635 = fight +432 (78% of kill gems are Prism bags) + farm +200.
  Walking is 54-56% of champion-rounds in every phase; camp work falls 28% -> 15% after r400. 82% of up group-rounds
  go untouched (monolith 96%, golem 85%, wolf 89%, elk 76%, gem clusters 71%). Willow: 19 capture gems / 1000 alive
  rounds, 7.8 camp dmg a round (Prism 42, Vesper 38), walks 67%. Cassi/Issac/Willow buy almost nothing by r600; W
  ends with 893 unspent gold (457 at r600). After 1000 wealth the winner takes a median 56 rounds to convert, its
  Prism's ~950-gem tribute cancelled ~5 times (stun 6.6k, manual 4.2k, lock 3.2k in 2.5k games), 71 channel rounds
  lost per team. Levers this suggests: (1) labour efficiency (walking, Willow/pair output), (2) endgame conversion,
  (3) gold spend.
- 02:20 12 probes built (audited; note pb-fight-bold is net SHYER and pb-fight-shy net BOLDER: life_value also prices
  kills and carriers) and launched on `probe` (5,120 games each): logs/pb-*.log.
- 02:26 PROBES (probe suite, 5,120 games each, vs chy-ref): bank-big 46.2, bank-small 48.5, campbold 48.7,
  campshy 47.6, crew-less 50.6, crew-more 50.5, far 49.8, near 50.2, fight-bold(net shyer) 50.3, fight-shy(net
  bolder) 50.6, ground-free 45.5, ground-home 49.0 (all +-1.4). Nothing swings 10: the bot is flat to big knob moves
  in both directions (bank floor x3 and dropping the enemy-ground discount cost ~4; the rest within ~2). Target
  choice (horizon x0.4 / x2.5) and crew size don't matter. A 60% bot needs a capability chy-ref lacks, not re-tuning.
- Scoreboard follow-up (roles, walking): Prism walks 60% (walk_bag 53), hits 19% but 42.5 camp dmg/alive round
  (224 per hitting round, 2x others); Willow 10.4, Cassi 16, Issac 13, Marcella 10.5 vs Vesper/Vendetta/Varg ~31.
  Cassi/Issac/Willow earn <200 gold by r600. Walk legs: median 4-5 steps to the chosen group; long legs (21+) pass a
  nearer idle group 34-52% of the time; 13-20% of walk rounds end in waiting by a camp. Payout -> next hit median 17.
- Lead -> win (mirror): lead 25-99 at r400 wins 63%, 100-199 79%. So a steady ~+10% farm edge is worth ~60%.
- 02:30 endgame study (scripts/bigtrib.py, excess.py). At the round a winner first reaches 1000 wealth its team has
  tributed T=345 (IQR 221-630) and its Prism carries 562; the Prism's game-ending tribute is ~660 gems (= the need,
  no excess hoard). Winning-bag tributes (team rich) by the eventual winner: 13,360 starts in 2,521 games, 12%
  complete, median 954 gems / 67 turns, cancelled after a median 6 rounds (stun 45%, self 23%, lock 20%; stunners
  Prism, Ryth, Cassi). Completion by enemies within 8 at the start: 0 -> 41%, 1 -> 12%, 2 -> 6%, 3+ -> 3%; 59% of
  starts have an enemy within 8. Only 21% are at an altar nearer our own spawn (22% complete there vs 12%).
  Medium tributes (non-rich, ~346 gems) complete 54%.
  DESIGN 1 "closer": a coherent endgame plan — pick the altar by expected completion, clear the area before the
  long channel, allies converge to guard/intercept, no self-cancel unless the bag is at risk.
- 02:34 Prism walking (scripts/prismwalk.py): mostly camp legs (51% / 7.4 rounds); 69% of its captures are groups it
  cleared itself, collections of allies' clears are short (4-round legs, ally waits ~2). Healthy shop trips (recall
  at >=90% hp, 90% buy) ~3.2 in r1-400 at a median 19 rounds recall-start -> next hit, ~60-75 of its first 400
  rounds; median 150 gold a trip. Altar waiting small. No single walking waste dominates.
- 02:36 Cassi & Issac (scripts/pair.py): apart 11+ tiles 43% of both-alive rounds (0-2: 19%); their camp damage a
  round 37.8 when within 2 vs 21-28 apart. Pair deaths ~3.9 a game (W 1.2, L 2.8; only 6% to camps), each costing both
  bodies (120 body-rounds), both bags and the kill gold; 53% of these kills have 3+ enemies within 8. The pair is
  the team's most-killed unit (Prism: L 1.59). DESIGN 2 "twin": the pair operates as one unit (shared target,
  Issac in front / Cassi behind within 2, retreat and recall together, combined output and min-health risk).
- 02:36 role probes launched on `probe`: pb-gold-hi (gold price x3), pb-gold-lo (x0.33), pb-wait (max_wait 2->12),
  pb-recall-lo (recall lines x0.5), pb-recall-hi (x1.6). willow-farm and pair-hold after their smokes.
- 02:39 role probes (probe suite, 5,120 each): gold-hi 47.7, gold-lo 46.9, wait 47.6, recall-lo 50.4, recall-hi 48.0.
  Same plateau: the tuned constants sit at their optimum; re-allocation knobs only lose.
- 02:40 denial (scripts/deny.py): the defender's stun-cancels of a winning tribute cost the stunner its life within 15
  rounds 66% of the time; the channeller is almost never killed (76 of 13,360 channels); damage during channels is
  small (39% take any, median 176). Conversion flips ~11.6% of games; reaching 1000 wealth first decides 89%.
- 02:41 pb-pair-hold (pair no longer hands captures on) 49.0, pb-willow-farm (Willow farms, no support pair) 47.7
  (probe, 5,120 each). Also flat. Twenty probes, none above 50.6: the plateau is real. Two designs in build: closer
  (endgame) and twin (Cassi & Issac as one unit).
- 02:42 intel (scripts/intel.py): 80% of champion kills have the victim seeing its killer in the 3 rounds before;
  only 10-12% were seen by a teammate alone. Shared enemy sightings can't be a big lever.
- 02:43 early kills (scripts/early.py, r<300): 3,649 kills; victims Issac 863, Cassi 707 (pair 43%), Prism 453;
  killers Prism 45%. First-kill victims: pair 45%; the first victim's team wins 38%. Local numbers at death mostly
  even or -1. Supports twin.
- 02:55 Prism deaths to champions (scripts/pdeath.py): 3,729; killer Prism 76%. Victim/killer Focus median 0.23: 2,132
  of 2,826 Prism-on-Prism kills have the victim under 0.7x, and 1,551 of those come while the killer channels a
  winning tribute (the victim, bag 0, came to stun-cancel it: the denial sacrifice, a consequence of losing). The
  duel-deciding kills are the near-even ones (>=0.7x): 694 (27% of games), victim bag median 354, the killer
  struck first in 72%. So the near-even duel is decided by first strike (who ends a turn in the other's reach).
- 02:58 confirmation suite maps/suites/mac13/conf (seeds 140300-140319, 5,120 maps) generated; for final confirmation only.
- 03:05 DESIGN 3 idea "late stop" (denial economy): today a defender stuns an enemy's winning channel as soon as it
  can (median 9 turns into a ~67-turn channel) and dies 66% of the time; the enemy restarts at once, so each body
  buys ~9 rounds. Stunning near the channel's end (with turn-order margin) costs the enemy ~60 rounds per stun.
  Exclusive stuns (Prism, Ryth, Tavi, Ren) need the stunner already in range at turn start, which lets the
  channeller react; Cassi's stun, Heart of Ruin's dash landing and Marcella's reset-stun can approach and stun in
  one turn. scripts/abmetrics.py: per-bot macro metrics for an extracted A/B.
- 03:24 RESULTS dev (10,240): twin 42.2% [41.3, 43.2] (a real loss); closer ~49 (running). Overseer note: think in
  packages (offence, defence, economy shifting together as one plan, each part with a reason), build, then ablate.
  Screens on `probe`, finalists on dev/hold, final on `conf`.
- 03:28 twin (dev 42.2%) and closer (dev 49.0%) metrics (scripts/abmetrics.py on 1,000 kept games each):
  twin: pair deaths 1.40 vs 1.86, deaths 4.18 vs 4.70, kills 4.54 vs 4.00 — but capture gems @300 364 vs 394 (-8%),
  @600 749 vs 804; Cassi idle 22.6% vs 12.5%, pair camp dmg 20.2 vs 28.0 a round. A body-swing of ~1 a game is worth
  far less than 8% of captures. closer: stun cancels 0.89 vs 2.18 a game, completion 12.6% vs 9.7%, but captures
  -3% (allies guarding) and first-to-1000 wins 85.5% vs 88.4%. LESSON: farm throughput is king (8% captures ~ 8
  points); any coordination must cost ~no farm time.
- wait_camp (scripts/waits.py, 400 games): Cassi 50, Vesper 45, Willow 41, Prism 39, Issac 39 rounds a game, mostly
  at clusters/wolves/elks, runs of 1-4 rounds.
- 03:30 closer agent's final version (after a fuel cut) smoke 51.6%; its dev run (pre-cut build) 49.0%. Behaviour:
  starts with no enemy within 8: 32% vs 19%; own cancels followed by a kill 74% vs 36%. Not a win as built.
- 03:31 one Vendetta's first 160 rounds (gen-classic-14020901006): hits ~60, walks ~50, holds/idle ~25, channels
  ~20. Camp fire takes it 700->160 hp in 8 rounds on one group, then a recall + 13-15 round walk back out: health is
  only restored on spawn (or by Willow/shields), so camp damage converts straight into heal trips (~20 rounds each).
- 03:35 heal trips (scripts/healtrips.py, recalls started under 60% hp, r1-600): share of alive time ~ Issac 21% (11%
  with a Willow on the team), Vendetta 18% (12.5%), Ren 16%, Varg 14% (11%), Ryth 12%, HoR 12%, Vesper 10% (8.5%),
  Prism 7%; a trip costs a median 22-25 rounds recall-start -> next hit. Willow heals ~1,450 hp / 100 rounds (~28%
  of her cast capacity) while the team takes ~2,500 camp damage / 100 rounds. Health is the binding farm input for
  melee bodies. closer (final build) re-run on probe.
- 03:38 building: twin2 (pair cohesion only under threat; farm exactly as chy-ref when safe) and sustain (Willow
  attaches to the ally whose heal buys the most farm time; farmers price the coming heal into spare health and the
  no-threat recall). Both aim at farm time, the binding resource.
- 03:42 allocation slack (scripts/swaps.py): pairwise target swaps between allies would save only 3.2% of leg walking: walking is geography, not bad assignment.
- 03:43 closer final on probe ~48.4% (dead end; the plan delays starts and the escorts cost farm). Even Prism duels (scripts/duel.py, 694): the killer closed to stun range first 230, the victim 153, both 189 — no simple 'never approach' rule.
- 03:52 conversion war: when the eventual winner first reaches 1000 wealth the loser holds a median 744 (46% >= 800, 35% >= 900): the race is close and the conversion phase decides many games. Supports D3 late stop (max delay per stun) as the defender's half of the war.
- 04:16 sustain (Willow attaches where a heal buys most farm time; farmers price the coming heal) probe 50.0% of
  5,120 [48.6, 51.4]. Metrics (1,000 kept games): Willow heals 1,644 vs 1,431 /100 rounds (+15%), deaths 6.60 vs 7.35,
  kills 6.97 vs 6.20, Prism deaths 0.83 vs 1.00, but captures level (@600 548 vs 558) and slower conversion (198 vs 172
  rounds). Fewer deaths without more farm buys nothing: flat.
- 04:16 twin2 (pair cohesion only under threat, chy-ref farm when safe) probe 48.0% of 5,120 [46.6, 49.4]. Its
  smoke showed pair deaths level with chy-ref after audit fixes: the threat mode costs a little camp damage and buys
  nothing. Pair line closed.
- 04:16 D3 latestop briefed (closer agent): stop a game-ending channel late (one spare turn before its deadline) from a
  safe staging tile; stagger multiple stoppers.
- 04:21 sustain post-audit build probe 49.5% of 5,120 [48.1, 50.9]: flat. Sustain line closed (healing up, heal
  trips level: the heal does not reach the bodies whose trips cost most).
- Prism dominance (scripts/dominance.py, mirror, both-alive rounds every 5): Focus ratio 0.8-1.25 is 50% of rounds and the
  Prisms are a median ~30 apart; within 6 tiles the kill/death odds in the next 60 rounds are 7.0/7.0% at 0.8-1.25,
  12.7/4.8% at 1.25-2, 40.8/1.4% at 2x+ (endgame sacrifices). The 1.25-2 band (13% of rounds) rarely meets (15% within 8).
  Probe batch 2 (pb2-*: Prism hunt / avoid, funnel max / off, deny off / wide, comeback off / wide, hold bold / shy)
  in build.
- 04:45 PROBE BATCH 2 (probe suite, 5,120 each, vs chy-ref): hunt 48.7, avoid 43.8 [42.5, 45.2], funnel-max 48.9,
  funnel-off 43.3 [42.0, 44.7], deny-off 48.6, deny-wide 47.5, comeback-off 49.5, comeback-wide 49.1,
  hold-bold 49.8, hold-shy 48.8. Two big negatives: removing the carry macro (-6.7, its known worth) and keeping our
  Prism away from enemy Prisms of 0.8x+ Focus (-6.2: presence on the contested map is worth a lot; hunting, the
  opposite, is level). Walking to stop a game ender is worth only ~1.4. Every knob sits at its optimum again.
- Tribute completion by starting bag (scripts/tribbins.py, mirror, all tributes): 1-29 96%, 30-59 90%, 60-99 79%,
  100-199 65%, 200-299 39%, 300-499 32%, 500-799 21%, 800+ 5% (8,900 starts = 3.5 a game; 17% done even with no enemy
  within 8 at the start). The endgame's huge channels almost never finish: conversion is the slow step after 1000.
- 04:47 DESIGN 4 'window' briefed (brief-window.txt): long channels start only where the stop window (rounds until any enemy stopper, dead ones by respawn, could stop it) fits the channel; once the team is rich the Prism banks chunks when a window fits; fallbacks keep the race. latestop still building.
- 04:48 500+ bag starts (scripts/bigstarts.py, mirror): 14,137, 98% Prism; the eventual winner's 12,153 (4.7 a game)
  complete 11%; those whose bag alone wins: 9,695, 6% done. Stops: stun 5,957, manual 4,044, lock 2,597. The winner's
  conversion is a churn of ~4 failed restarts: supports window.
- 05:01 latestop (first build, frozen as variants/latestop-a) probe 49.9% of 5,120 [48.6, 51.3]: flat. Stops of
  300+ channels (scripts/lateness.py, 650 kept games): latestop 2.37 a game with a median 65 turns left (<=10 left: 6%)
  vs chy-ref 2.65, 69 left (3%). Most stops still land early: they come through the fight's stun_worth casts and the
  fallbacks, not the staged path. And pb2-deny-off says walking to stop is worth ~1.4 in all. Denial timing is no lever.
- 05:20 Gold (scripts/goldheld.py): little is hoarded except by the Prism (mean 247 at r600); by r600 Cassi earns
  168, Issac 191, Willow 35 against Vesper 1,771 and Prism 1,588. Monoliths (scripts/monolith.py): 28% of maps, ~2 a
  map, 1.24 captures a game at a median r775 (~230 gems each); the first capturer wins 74%. Off Monolith-only maps
  chy-ref's siege only takes one reactively (seal/join/burst/home). Probe batch 3 queued: pb3-siege-any (every
  Monolith a siege candidate behind the existing priced gate), pb3-siege-loose (gate x1.5), pb3-prelock (spare locks
  placed on the enemy-side altar). Fresh probe suite maps/suites/mac13/probe2 (seeds 140220-140229, 2,560) made.
- 05:27 latestop agent's final analysis: of its 208 stun cancels 202 came from the stop path itself, 170 after
  staging was dropped because the staging tile turned unsafe (a non-channeller stun or lethal damage reaches it
  sometime in a ~60-turn channel). Late stops need waiting that tolerates risk: the denial line stays closed.
- 05:27 window (smoke build, frozen variants/window-a) on the FRESH probe2 suite: 45.6% of 5,120 [44.3, 47.0], a real
  loss; out-of-fuel turns 455 vs 310. Ablations requested (window-start: start rule only; window-chunk: rich-team
  chunking only). Probe batch 3 (siege-any, siege-loose, prelock) sent to the closer agent.
- 05:35 window-a metrics (1,000 kept games): captures level (@600 762 vs 765), deaths 4.59 vs 5.15, kills 5.01 vs 4.45,
  but first-to-1000-wealth won 76.6% vs 87.7% and convert rounds (wins) 215 vs 138; rich-tribute completion level
  (12.0 vs 12.4%). Waiting for windows slowed conversion ~77 rounds and bought no completions: conversion SPEED is a
  lever (negative direction ~-4.4). Next: the opposite direction (eager conversion) as a probe pair.
- 05:35 conversion phases (scripts/convert.py, mirror winners): assembly (wealth >= 1000 but no single bag wins) median
  10 / mean 22 rounds; finishing (a bag wins) median 29 / mean 124 (Q3 100): a long tail of cancel-and-restart, the
  holder channelling 71% of those rounds. Restart model: a channel of L turns under a per-turn stop hazard h takes
  ((1-h)^-L - 1)/h rounds to land, exponential in L: at h=0.05 one 65-turn bag ~540 rounds, two 33-turn chunks ~176,
  four 16-turn ~101. Chunking the endgame bag is the lever window aimed at but gated on windows.
- 05:44 pb3-siege-any (every Monolith a siege candidate behind the priced gate; smoke: Monolith captures 82 vs 45)
  probe2 47.1% of 5,120 [45.7, 48.5]; pb3-siege-loose (gate x1.5) 43.8% [42.5, 45.2]. Monolith sieges off Monolith-only maps
  cost: the gate is right, and a looser one costs more. The window agent's final build: smoke 49.6%, fuel 30 vs 15
  out-of-fuel turns; it made no ablations. Probe batch 4 (chunk300, chunk150, eager, eager-rich) in build.
- 05:47 THE STUCK LEADER. Two long mirror games: a Prism holding a 1,048-gem winning bag (a 105-turn channel) restarts
  ~60 times over r569-r1738, stunned each time by an enemy Prism with bag 0 that dies and respawns ~every 80 rounds;
  in another the bag grows 632 -> 2,830 (kills add to it) and every channel (up to 283 turns) is stunned or locked
  over r525-r1626. Finishing (a bag wins -> win) exceeds 200 rounds in 15.2% of games and 400 in 8.6%; those hold 73% /
  58% of all finishing rounds. A bag past ~500 cannot be converted against a defender that keeps coming: the Prism
  should never carry a bag its channel cannot finish. pb4-chunk probes test exactly that.
- 05:48 Inside the first stuck game: the stuck leader (T1) won anyway. Its Prism killed T0's Prism (bag 466) at r553
  and held 1,048 from then on, while its Cassi/Issac trickled 14-43-gem tributes (score 240 -> 973) and T0's team
  went into denial (2 captures after r569, score frozen at 327, its Prism dying with bag 0 every ~80 rounds). Stuck
  regimes are mostly slow wins, not flips: chunking may speed wins without moving the win rate. The decisive event
  is the Prism duel that hands one side the other's bag. pb5-avoid125 / avoid160 (avoid only clearly stronger enemy
  Prisms) queued.
- 05:52 pb3-prelock (spare locks on the enemy-side altar, bug-fixed) probe2 49.3% of 5,120 [47.9, 50.7]: flat.
- 05:57 pb5-avoid125 (avoid only enemy Prisms >= 1.25x) probe2 48.5% [47.2, 49.9]: flat. Engagement is at its optimum.
- Defender while the winner finishes (scripts/defender.py, 1,000 mirror games with 50+ finishing rounds): the loser's
  capture gems fall 136 -> 65 a 100 rounds and its deaths rise 1.0 -> 3.2 a 100 rounds: the whole team throws itself at
  the channel (every body holding a hard stop walks in, stop_game_ender), while deny-off (no walking stops at all) cost
  only 1.4. DESIGN 5 "one stopper": the team sends only the body whose stop lands first (a backup only when it cannot
  land in time); the others keep farming.
- 06:02 pb5-avoid160 probe2 49.6% [48.3, 51.0]: flat. onestop briefed (closer agent).
- 06:11 PROBE BATCH 4 (probe2, 5,120 each): pb4-chunk300 (Prism banks bags >= 300 once team wealth >= 700) 40.0%
  [38.7, 41.4]; pb4-chunk150 (>= 150 from 600) 36.0% [34.7, 37.3]. The biggest levers found all day, both strongly
  negative: the late hoard's Focus is worth far more than conversion speed. The stuck leader is stuck but wins;
  its huge bag is what kills the stoppers. (pb4-eager-rich equals pb4-eager: closing() already banks every bag
  once the team is rich.)
- 06:14 pb4-eager (winning channels start at any risk, before other branches, no heal trip first) probe2  49.9 | 48.5-51.2 : flat. pb6-keep (the Prism ignores the team race in closing(): keeps until its own bag wins) in build.
- 06:16 FLIPS (scripts/flips.py, flipdeath.py; mirror): the first team to 1000 wealth loses 302 of 2,522 games. In 51%
  of those its Prism dies after t0 (vs 2% of held games), with a median bag of 533, to the enemy Prism (119/155). Only
  33 of those 155 deaths come while channelling; the victim's Focus is a median 0.92x the killer's (Q1 0.57): even
  duels, taken while ahead. DESIGN 6 "lead safe" (variance): once our team is rich our Prism avoids enemy Prisms of
  0.7x+ Focus (pb2-avoid's zone, gated); the trailing side does the opposite (hunt while the enemy is rich).
- 06:19 pb6-keep (the Prism keeps until its own bag wins, ignoring the team race) probe2 41.1% [39.8, 42.5]. With the
  chunk probes this brackets chy-ref's switch (the Prism banks once the team as a whole is rich) as a sharp optimum:
  earlier costs 10-14, later 9. Bank timing is decisive and already right.
- 06:28 pb7-leadsafe (pb2-avoid's zone at 0.7x, only while our team is rich) probe2 49.9% [48.5, 51.3]; pb7-leadsafe-hunt
  (plus a 0.8x hunt while the enemy is rich and we are not) 50.0% [48.7, 51.4]. Flat: once rich the Prism is banking
  (closing), and the zone only shapes farm walks. The flip deaths come on the way to or at the altar.
- 06:36 Replications on probe2 of the best first-batch probes: crew-less 50.1 (probe 50.6), fight-shy (net bolder) 50.4
  [49.0, 51.7] (probe 50.6; pooled 50.5 of 10,240, +-1.0), crew-more 49.4. Noise around 50.
- 06:47 onestop (only the designated first stopper goes for a game-ending channel, a backup when it cannot land in time;
  the rest play on) probe2 50.1% of 5,120 [48.8, 51.5]: flat. Behaviour check running.
- 07:07 onestop behaviour (929 kept probe2 games, scripts/onestop_check.py): while the opponent finishes 50+ rounds,
  capture gems 73.4 vs 72.0 a 100 rounds and deaths 2.90 vs 2.89: unchanged. The defender's farm collapse is not the
  stop path; it is the whole game state (a dominant enemy Prism, threats pushing bodies home). The design changed
  little in play. pb8-banksafe (bank walk / altar / start avoid 0.7x enemy Prisms with a 100+ bag, plus pb7) and
  pkg-end (onestop + pb4-eager) on probe2; onestop-a and fight-shy on dev.
- 07:09 pb8-banksafe probe2 49.7% [48.3, 51.1]: flat.
- 07:18 pkg-end (onestop + pb4-eager) probe2  49.9 | 48.5-51.2 : flat. Finalist so far: onestop-a (most coherent design, ~50). Its hold run launched. pb9-race07 / race14 (race_left x0.7 / x1.4) queued to find the bank switch's slope.
- 07:20 DEV (10,240 each): onestop-a 50.2% [49.2, 51.2]; pb-fight-shy (life_value x2, net bolder) 50.2% [49.2, 51.2].
- 07:32 pb9-race07 (race_left x0.7: carriers close earlier) probe2 49.9% [48.6, 51.3]; pb9-race14 (x1.4) 50.2% [48.8, 51.6]:
  flat near the switch, so the cliff (chunk / keep) is only at large shifts. onestop-a HOLD 50.0% of 5,120 [48.6, 51.3];
  conf launched.
- 07:45 Fresh probe suite maps/suites/mac13/probe3 (seeds 140230-140239, 2,560, ladder-v2): probe2 carried ~20 screens.
  Built (agent, audited, smoked): pb10-shop-lo / pb10-shop-hi (shop_gain_scale x0.5 / x2: a healthy Prism shop trip
  costs ~19 rounds, ~3 in r1-400, the one economy lever not yet probed) and pkg-knobs (onestop-a + fight-shy +
  recall-lo + crew-less + race14: the five ~50.2-50.6 reads stacked, in case small real gains add). All three on probe3.
- 07:46 CONF (final confirmation, 10,240): onestop-a 50.0% [49.0, 50.9]. The finalist equals chy-ref on
  every suite (probe2 50.1, dev 50.2, hold 50.0, conf 50.0): a coherent stop design with no measurable effect.
- 07:47 pb11-siege-tight (siege gate x1/1.5) and pb11-siege-seal (off Monolith-only maps Monoliths only for seal): the untested direction of pb3's siege probes. Briefed (brief-probes6.txt).
- 07:51 PROBE3 (5,120 each): pb10-shop-lo (shop_gain_scale x0.5) 51.6% [50.2, 52.9]; pb10-shop-hi (x2) 49.5%
  [48.1, 50.9]; pkg-knobs 50.1% [48.7, 51.5] (the small reads do not add). The shop trip has a slope: fewer trips
  win. shop-lo on dev (10,240) launched; follow-ups briefed to find the shape (x0.25, none, Prism-only, others-only).
- 07:56 pb11-siege-tight / pb11-siege-seal built (smokes 49.2 / 49.6; tight also gives a bursting Monolith the 50.7-round limit, as loose did by construction); both on probe3. DESIGN 'defer' briefed (brief-defer.txt): a shop trip's purchase is valued only over the rounds until the next natural home visit (measured per champion), not over all remaining farm.
- 08:04 pb10-shop-lo on DEV (10,240): 49.9% [48.9, 50.9]. Its probe3 51.6 was noise (the first CI above 50 of
  ~50 screens is what chance gives). pb11-siege-tight probe3 49.9% [48.5, 51.3], pb11-siege-seal 50.0% [48.6, 51.4]:
  sieging less is level, sieging more lost 3-6: the reactive siege sits at the edge of its optimum. Shop follow-ups
  (built and audited: shop-q x0.25, shop-none, shop-lo-prism, shop-lo-others; smokes 48.4 / 52.0 / 51.6 / 50.0) on
  probe2 to map the shape anyway. Note from the audit: capture.cc's Prism capture-recall prices its own shop+heal
  trip unscaled, outside wants_shop.
- 08:10 Shop follow-ups (probe2, 5,120 each): shop-q (x0.25) 49.8, shop-none (no healthy shop trips at all)
  49.2 [47.8, 50.5], shop-lo-prism 50.6 [49.2, 52.0], shop-lo-others 49.5. Shopping trips are worth under a point in
  all: buying on the other visits home (heals, deaths, bank trips by way of spawn) covers nearly all of it. The shop
  line is closed; defer (already building) finishes it on its principled form.
- 08:26 defer built (agent, audited; smoke 53.5% of 256): shop purchases valued over min(1, H/rounds), H the
  measured interval to the next natural home visit (prior 60 rounds, measured 59-64 in r1-400, 73 in r401-800; deaths
  count as visits since the dead shop). Finding: wants_shop causes only 0.67 trips a champion-game (0.13 under
  defer); most healthy recall-and-buy trips are farm_recall / home_trip trips through spawn, which price the next
  emblem over all remaining farm the same way. defer on probe3 + dev; defer-all (the same horizon there) briefed.
- 08:33 defer: probe3 50.6% [49.2, 52.0]; DEV 50.9% of 10,240 [49.9, 51.9] (best dev read of the programme,
  still inside noise). Hold and conf launched.
- 08:34 defer-all built (agent, audited; smoke 51.2% of 256): defer's horizon also on home_trip's emblem term,
  farm_recall's purchase term and the Prism capture-recall shop ride (that ride censored like wants_shop's).
  Healthy Prism shop trips in r1-400 2.69 -> 1.05 (all champions 1.26 -> 0.80); all Prism completed recalls 7.8 ->
  4.9 a game; gold per trip 150 -> 180. On probe3 and dev.
- 08:39 defer HOLD 49.6% of 5,120 [48.2, 50.9]; CONF 50.0% of 10,240 [49.1, 51.0]. Over all 30,720 games
  (probe3, dev, hold, conf) about 50.3: level. dev's 50.9 was noise.
- 08:40 defer-all probe3 45.0% [43.6, 46.3]; DEV 45.0% of 10,240 [44.1, 46.0]: a real loss of 5. Halving the
  Prism's recalls through spawn (7.8 -> 4.9 a game) costs 5 points, so those combined heal+shop+route trips are
  worth a lot, while pure shop trips (wants_shop, 0.67 a champion-game) are worth under a point. Kept
  replays/batch-*defer-all-p3* for a look. Bracket briefed: pb12-via-hi / via-lo (the purchase term of those trips x2 /
  x0.5, no horizon).
- 08:42 pb12-via-hi / via-lo built (smokes 52.3 / 48.8); both on probe3, via-hi also straight on dev given the time left.
- 08:44 pb12-via-x4 (factor 4) built, smoke 50.8; on probe3.
- 08:48 THE VIA LEVER (purchase term of trips home by way of spawn: home_trip emblem, farm_recall, Prism
  capture ride), probe3 5,120 each: x0.5 52.1% [50.7, 53.4]; x2 49.0 (dev 48.6 of 10,240 [47.6, 49.6]); x4 47.0
  [45.6, 48.3]; defer-all (horizon factor, ~0.1-0.3 early) 45.0. A peak below 1 and a cliff further down: fewer
  detours through spawn win until the Prism stops visiting home for heals/shards it needs. via-lo on dev, hold and
  conf at once (the window closes at 10:00); via-03 / via-07 briefed to place the peak.
- 08:49 defer-all metrics (1,000 kept probe3 games, abmetrics.py + shoptrips.py): deaths 7.93 vs 6.98 a game,
  Prism deaths 0.98 vs 0.81, captures 891 vs 921, Prism completed recalls 5.4 vs 7.9 a game. The trips through spawn
  heal as well as shop: priced without the purchase, bodies stay out hurt and die. So the purchase term is partly
  standing in for a heal value the heal term under-prices; a moderate cut (x0.5) trims detours, a deep one loses lives.
- 08:50 pb12-via-03 / via-07 built (smokes 48.8 / 52.0); on probe3.
- 08:52 pb12-via-lo CONFIRMATION: dev 50.2% of 10,240 [49.3, 51.2]; hold 50.8% of 5,120 [49.5, 52.2]; conf
  51.4% of 10,240 [50.5, 52.4]. Held out (dev + hold + conf, 25,600): 50.8% [50.2, 51.4]; with probe3 (30,720) 51.0%.
  The curve on probe3: x0.3 50.4, x0.5 52.1, x0.7 50.7, x1 (chy-ref) 50, x2 49.0, x4 47.0, defer-all 45.0. A broad
  peak near 0.5 worth under a point; probe3's 52.1 was partly luck. via-lo is the finalist (the first candidate whose
  held-out interval clears 50). A further fresh suite maps/suites/mac13/fin (seeds 140240-140249) is generating.
- 08:55 via-final: pb12-via-lo with the factor as params::via_gain_scale (commented); byte-identical replays to pb12-via-lo on 256 ladder games. Further fresh suites fin (140240-9) and fin2 (140250-9), 5,120 games each, running.
- 08:57 via-lo on the further fresh suites: fin 50.2% of 5,120 [48.8, 51.5]; fin2 50.0% [48.6, 51.4]. All
  held-out games (dev, hold, conf, fin, fin2: 35,840): 50.6% [50.1, 51.1]. A small gain, about +0.6. More: via-final
  on fresh fin3 / fin4 (140260-79), and via-03 / via-07 on dev for the curve's shape.
- 09:05 via-final fin3 50.1% of 5,120 [48.7, 51.5], fin4 50.4% [49.1, 51.8]. All held-out via-lo/via-final games
  (dev, hold, conf, fin1-4: 46,080): 50.5% [50.1, 51.0]. Curve on dev (10,240 each): x0.3 49.7, x0.5 50.2, x0.7 50.6:
  a broad, shallow optimum between 0.5 and 0.7 around +0.5. Last probe pair briefed: the heal term of the same trips
  x1.5 / x0.67 on via-final.
- 09:08 pb13-heal-hi / heal-lo (heal term of the via trips x1.5 / x0.67 on via-final; wants_shop's heal kept) built, smokes 54.3 / 48.4. Both on dev; heal-hi and via-final also on fresh fin5 (140280-9).
- 09:13 pb13-heal-hi dev 49.9% [49.0, 50.9], fin5 50.9% (via-final on fin5 50.4% [49.1, 51.8]); pb13-heal-lo
  dev 49.9%. The heal term is level both ways: the via factor acts on the purchase only. via-final held out (dev,
  hold, conf, fin1-5: 51,200 games): 50.5% [50.1, 51.0]. Extra reads: via-final on probe, probe2 (never used to choose
  via) and a --mix varied stress suite (140290-9).
- 09:19 via-final on probe 48.8% of 5,120 [47.5, 50.2], probe2 49.7% [48.3, 51.1], varied (stress mix) 50.2%
  [48.8, 51.6]. Every via-lo/via-final read not used to choose it (dev, hold, conf, fin1-5, probe, probe2, varied:
  66,560 games): 50.3% [49.9, 50.7]. The gain is at most a few tenths: the via factor is near level, like the rest.
  via-07 (dev 50.6) on conf, hold and fin for the comparison.
- 09:24 pb12-via-07: conf 49.5% of 10,240 [48.5, 50.5], hold 50.2%, fin 49.4%: level. Last reads: via-final on
  fresh fin6 / fin7 (seeds 140330-49).
- 09:28 via-final fin6 49.9% of 5,120, fin7 50.2%. FINAL READ, every via-lo/via-final game not used to choose
  it (dev, hold, conf, fin1-7, probe, probe2, varied): 76,800 games, 50.3% [49.9, 50.6]. Including probe3 (where it was
  chosen): 81,920, 50.4%.

## Summary (09:30)
- Finalist: bots/variants/via-final (= pb12-via-lo with params::via_gain_scale = 0.5): the purchase term of trips home
  by way of spawn (home_trip's emblem, farm_recall, the Prism capture ride) at half weight. Level with chy-ref
  within a few tenths; the only candidate whose held-out interval cleared 50 at any point (25,600 games: 50.8
  [50.2, 51.4]), and it regressed to 50.3 over 76,800.
- onestop-a (one designated stopper of game-ending channels): probe2 50.1, dev 50.2, hold 50.0, conf 50.0. Level.
- The bot sits on a flat optimum in every macro direction we could move it: ~60 probes / designs, two-direction
  where they were knobs. The large effects are all losses, and all concern the Prism and its trips:
  bank earlier (chunk300 / chunk150: -10 / -14), bank later (keep: -9), funnel off (-7), Prism avoiding enemy Prisms
  (-6), siege more (-3 / -6), slower conversion (window: -4), dropping the enemy-ground discount (-4.5), bigger bank
  floor (-4), fewer trips through spawn (defer-all: -5), more of them (via x4: -3).
- 09:31 pb14-twin-lo / hi (tribute_window 11 -> 6 / 20) built, smokes 50.0 / 50.0; on probe3.
- 09:32 pb14-twin-lo (tribute_window 6) probe3 49.0% [47.7, 50.4]; pb14-twin-hi (20) 49.5% [48.2, 50.9]: level both ways.
- 09:34 pkg-final (via-final + onestop) built (smoke 48.4); on fin5 / fin6, where via-final read 50.4 / 49.9.
- 09:35 pkg-final fin5 50.4% / fin6 49.9%: the same reads as via-final (50.4 / 49.9); onestop adds nothing on top. via-final stays the finalist (simpler).
- 09:37 Null check: chy-mirror (identical source) vs chy-ref on fin and fin2: 50.0% exactly on each (both sides of every map are played, so equal bots read 50.0).
- 10:00 FINISH: all subagents stopped or finished, no mac13-argo tmux sessions or processes remain. bots/charybdis/src now equals bots/variants/via-final/src (charybdis 525 + via_gain_scale 0.5).
