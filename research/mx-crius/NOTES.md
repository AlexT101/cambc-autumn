# CRIUS: macro refactor of charybdis (2026-11-13)

## Status (final, programme ended early by the user at ~17:25 UTC)
- Best candidate: none beat chy-ref; bots/charybdis = chy-ref (CHANGES 529), unchanged. No held-out or 100k read run.
- Lines (train suite, 10,200 games each, 2x fuel, vs chy-ref): A a-collect best 49.8 [48.9, 50.8]; B b-crew best
  50.5 [49.5, 51.4]; C c-balance best 50.4 [49.5, 51.4]; D d-stakes best 50.3 [49.3, 51.3]: all level. E e-denial
  lost (45.7-47.1), unfinished. F f-thru unfinished (one solo read, 4% slower). Patches for all in `patches/`.
- Nothing running; all mx-crius tmux sessions and runs killed; replay batches and extracts deleted.

## Setup
- A/B: `research/mx-crius/ab.sh TAG CAND SUITE [args]` = ab.py variants/CAND vs variants/chy-ref, --no-test-draft,
  --fuel 200000 (FUEL=normal drops it), fast runner native, name mx-crius-TAG, log in logs/TAG.log.
- Suites (`maps/suites/mx/`, ladder-v4, 340 maps a seed): dev (61440000-14), hold (61440100-14) given;
  mine: study 61441000-04 (1,700 maps; traces and smokes only, never decisions), train 61441400-14 (implementers'
  own loops), x1 61441100-14, x2 61441200-14, x3 61441600-14 (confirmation), scr 61441500-14 (screens), fin 61441300-14 (the normal-fuel final read).
  `research/mx-crius/gen.sh NAME A B` makes one.

## Log
- 14:21 Read BRIEF, AGENTS, rules, CASTOR/overseer/macro-orchestrator priors, CHANGES 526-529.
  Priors: the gains so far came from pricing consistency (CASTOR's Prism premium used everywhere), Prism shop
  timing, Willow medic, wards by value. Restricting farm (pack/escort/convoy) lost 5-13. Economic leads convert
  (CASTOR: +20-25% economy by r300 ~ 60%). ~22% of games without our Prism read level in every programme.
- 14:24 Debug mirror chy-mirror vs chy-ref on study: 50.0% of 3,400 (2.1 min). Extracted to `replays/an-mirror`.
- 14:30 **Turning points** (`scripts/turning.py`, `swing2.py`; 1,700 lost games, loser's view). Swing round = last round
  the loser's tributed+carried was level or ahead: quartiles r151 / r352 / r572 (25% before r150). Final gap: kill
  transfers -472, captures -206, camp losses ~0. Loser's Prism died first 49%, no Prism death 35%, no Prism 12%.
  In the 25 rounds after the swing: no loser death in 58% (gap grows by captures, -57 gems), a loser death in 42%
  (half the Prism). Biggest victim had no ally within 8 in 26%; outnumbered by 2+ in 37%.
- Cohesion (mean distance to nearest ally) does not predict the result at r100-500 within gem-lead bins
  (`cohesion.py`); the gem lead does (r100 lead>25: 66-76%).
- Kills (`killnum.py`, 17,421): victim outnumbered by 2+ within 6 in 40%; in 58% of those an ally stood 7-14 away.
  **Fights are instant** (`fightlen.py`): rounds from the victim's first champion damage to death, quartiles 0/1/3,
  p90 7; allies 7-14 away close by 0.1 tiles on average. Convergence after contact cannot work; pre-contact
  position and who strikes first decide.
- Time budget (macro_stats): walk ~49%, camp 18% (W) / 17% (L), dead 4.7% / 13.5%; recalls 46 a team-game.
  Recalls (`recalls.py`): Vesper ~13.6 a game, 59% at >90% HP, 84% shop; Prism 7.7 (68% >90%, 90% shop, 158 gold);
  Issac 7.9 (37% >90%, heal trips). A recall cycle (5 + ~15 rounds to the next hit) ~24% of team time.
- Per type (`champtypes.py`): Prism earns 2,273 gold, carries 176 unspent on average; Cassi/Issac ~230 each, Willow 51
  (frozen near base stats: Cassi max HP 653 at r300). C&I pair deaths 1.95 a team-game (`pairdeath.py`), 59% by the
  enemy Prism (feeding it ~200 gold a game), bodies 6+ apart in 52%.
- Supply (`supply.py`): Elk groups (32 gems) sit up and asleep at full HP 41% of rounds to r600, Golem (62) 54%,
  Monolith 92%, wolves 54%, gem clusters 33%.
- **Crews are inefficient** (`crews.py`, `crews2.py`, `crewlag.py`): Elk/Golem clears with 2-3 strikers are slower and
  take more total camp damage than solo ones in every phase (mid Elk: solo 13.3 r / 469, duo 17.6 / 643, trio
  18.3 / 748). Second striker's lag quartiles 0/2/5 (p90 14); 19% of damage before it arrives. Only the Monolith
  stages before waking (`mono_engage`). -> line B.
- **Prism share** (`collector.py`): the Prism takes 54.4% of captured gems; allies make 21.5 captures a team-game
  without it (396 gems), 5.9 of them (111 gems) with the Prism within 8 tiles 6 rounds before payout. -> line A.
- Endgame: the loser ends with tributed+carried >= 1000 in 20% of losses, richer than the winner in 8%.
- 14:45 Launched A `a-collect` (brief `briefs/a-collector.md`): Prism collects allies' holds (relay hand-over before
  payout), allies price groups the Prism can collect with its premium. 14:57 launched B `b-crew`
  (`briefs/b-crews.md`): staged starts, tanking, departures and crew pricing on Elk/Golem groups.
- 14:45 Solo baseline (chy-ref vs idle, study, 2x): 1000 at r620; collected @150/300/600 223 / 525 / 934. The mirror's
  team wealth runs at ~75% of that (172 / 388 at r150 / 300, `collected.py`). Solo time: walk 50%, camp 25%, recall
  7.7%, hold 6%; the spawn cycle (recall + walk out from spawn) ~29%; banking ~11%.
- **Yield by group kind** (`yield.py`: each champion-round attributed to the next group it damages; its share of the
  capture is the return). Solo: Wolf groups take 40% of champion time at 0.20 gems + 1.20 gold a round; Elk 30% at
  0.36 + 1.68; Golem 4% at 0.56 + 1.96; gem clusters 16.5% at 0.40; gold clusters 6.4% at 1.93 gold. Elk/Golem
  dominate Wolves on both gems and gold. Mirror: same order. Sent to B.
- Branches (D lines, mirror): farm 75% r1-150, 65% r151-400, 48% r401+; retreat 4-6%; chase 1.5%.
- Deaths: victim's last turn retreat 50%, stopping an enemy winning tribute (E) 28% (victim's team wins 5% of those:
  lost endgames), farm 14%. Victim saw the killer the round before in 78%; for 10+ rounds in 33%, 4+ in 55%, first
  seen ~7 tiles away at 90%+ HP in two thirds (`sightrun.py`). Over the last 10 turns (non-E): retreat 40%, farm 36%.
  Deaths are long standoffs and chases with warning, not ambushes.
- Cassi/Issac bank ~2.8 times a team-game each, ~28 gems, ~20-round trips (`tributes.py`); the Prism's channel
  completes 13% of starts in the mirror.
- research/fish-farm-2026-11-02.md (top ladder team Fish): packs (crews 4+ on 53% of lone Elks vs our 16%), dies half
  as often, 21% of its deaths outnumbered vs our 56%; "the farm's rate never makes a crew better than an equal camp
  alone; packing pays only through what the rate leaves out (camps not lost, deaths, local strength)".
- Contact onsets (`contact.py`): death within 10 rounds 4.4%; by allies-enemies within 10, -4 13.9% ... 0 3.6% ... +3
  1.5%; holds within each half (own: 18.2% -> 1.7%; enemy half: 7.7% -> 0.9%). The local balance gradient is robust.
- Gold (`goldfit.py`, logistic on differences at r200/300/400): per 100, wealth 0.53-0.75, Prism gold 0.12-0.17, others'
  gold 0.09-0.10: a gold ~0.2-0.3 gems, more on the Prism. No case for routing gold to allies.
- Back-and-forth walking (`uturn.py`, legs of 8+ steps ending under half their steps from the start): Cassi/Issac 27-28%
  of steps in the mirror vs 9-17% solo; Prism 14% vs 10%; Willow ~50% (follows). Enemy-induced U-turns cost C&I ~7%
  of their time. A narrative (study game 1841) shows the relay already happening (allies clear Gems, Prism arrives
  to capture) and a 49-step Cassi walk ending 3 tiles from its start.
- ICARUS lesson re-read: Monolith captures doubled but level: Focus past dominance doesn't convert (a 600-gem bag is a
  60-turn channel, the rules allow no partial tribute).
- 15:05 B train: stage1 50.5, stage2 49.4, stage3 49.7 (OOF 1,689 vs 1,328). A train t1 49.2.
- 15:18 **B b-crew done: level** (patch `patches/b-crew.diff`). Staged wake for every strong non-Monolith group
  (`stage_wait`: wait iff F*Sc*trip/usable > k*S, once per sleep, bounded by solo clear time). Train: stage1 50.5
  [49.5, 51.4], +crew pricing 49.4, +tank positioning 49.7 (OOF up), final audited 49.6 [48.6, 50.6] OOF 856/923.
  Solo vs idle level (r1000 -0.3%). Crew clears faster/less damage (early Elk duo 28.4/966 -> 25.1/896, lag 13.1 ->
  10.4; mid Golem duo 21.4/1312 -> 19.9/1176) but no win rate. Learned: the 'crews are inefficient' premise was mostly
  composition (lone Prism clears dominate solo; crews are weaker bodies; contested clears counted as crews). Within
  composition crews beat solo. Most lag from crews formed after the wake (help/join). Early departures rare (5%).
  Lesson: clear efficiency on strong groups is not a lever; shelved.
- 15:20 Launched C `c-balance` (brief `briefs/c-balance.md`, base chy-ref). Early lead (`early.py`, mirror): the
  winner's lead at r100 is captures +7.7 vs kill transfers +2.7 (r150 16.7 / 9.5, r250 42.7 / 29.4); a capture lead
  >15 at r150 sits with the eventual winner 681 vs 340 games. Early is economy, later kills.
- Zero-return jobs (`waste.py`, rounds to r600 attributed to the next group a champion damages): enemy-taken groups
  cost only 4.3% of champion time in the mirror, abandoned ones 8.5% (solo 6.2%). Contested-group theft is not where
  the mirror's 25% economy deficit goes; deaths (dead 4.7% / 13.5% of time W/L), retreats and U-turns are.
- Retreats (`retreats.py`, D-line R runs): ~300 short runs a game (3-4 rounds), 4.5% end in death; death rises with
  enemies within 6 (0: 1.1% ... 3+: 10%) and low HP, mildly with ally distance (4.1% -> 6.5%). Retreat is a flicker,
  not a lever of its own; the local balance before contact (line C) is.
- **Winning bags** (`race.py`, `race2.py`, `finish.py`, `winstart.py`): the team that first holds a one-tribute win
  wins 88%; 19.7% of losses had one at some point (mostly the Prism, median bag 638). Prism winning bags (>=300)
  convert 80% (bag 300-500 91%, 700-900 75%), median 93 rounds from the bag to the end in wins (p90 699). Only 5.9% of
  9,198 winning Prism starts complete (60+ turn channels: stun 55%, lock 22%, own cancel ~17%); 0 enemies within 8 at
  start: 17%. Even with every enemy dead at start only 8% (respawn is 60 rounds). Priors (EXPERIMENTS: caps at
  13/26/50/300/450, escorts, safe altars, unseen starts, cancel fixes C1-C4, Prism banking psm50b -9, bm-lb -2) are
  all level or lose on this: not a new line.
- **The Prism duel is economics** (`prismdeath.py`, `duel.py`): 78% of Prism kills are by the enemy Prism (148 gems a
  kill); a Prism losing a 100+ bag: its team wins 6%. Prism encounters (within 6): with a bag gap of 250+ the richer
  kills within 30 rounds 47%, the poorer 0.9%; near-equal bags 3-4% each way, 93% nothing. HP barely matters. The
  game is the Prism's gem lead; everything goes through team gem rate and Prism share.
- Mirror game length quartiles 559 / 717 / 994 (solo reaches 1000 at r620).
- 15:50 **A a-collect done: level** (patch `patches/a-collect.diff`). chy-ref already had most of the collector
  ('G' takeover, 'L' leave, 'Q', pick_up, sole_capture_holder / yield_capture hand-over, prism_coming). Added:
  takeover with enemies in sight (tile-wise harm test), pick_up to a free tile, hold-for-reachable-Prism instead of
  leaving empty, allies price the Prism's reach. Gems x premium pricing for 'G' lowered the Prism share; reverted.
  Train t1 49.2, t2 49.5, t3 49.8 [48.9, 50.8], t4 (audited) 49.6 [48.6, 50.6]; Prism share 0.536 vs 0.527, collects
  7.15 vs 6.7. Addressable ally captures near the Prism are only ~30 gems a game (out of reach: Prism tributing or
  busy ~17-20, single-tile groups ~10, too late ~11). Shelved.
- Prism time (`budget.py`, `legs.py`, r<=600): the Prism moves 55% of its rounds even solo; 34% of its walking is spawn
  -> first camp and 10% camp -> spawn (~19% of Prism time on the spawn cycle, ~5.6 home visits by r600). CASTOR's shop
  EOQ already prices this.
- Fight values are tuned constants in enemy HP (life 276.6 = 15.8 gems, gem 17.5) whoever dies and whenever, while the
  economy prices the same gems by state (Prism premium, rates, per_gold): -> line D.
- 15:55 Launched D `d-stakes` (brief `briefs/d-stakes.md`).
- **The middle decides the economy** (`zones.py`, group zone by its share of the two spawn distances: own <0.4,
  middle 0.4-0.6, enemy >0.6): winner minus loser captured gems per game, own / middle / enemy zone: r150 +3.4 /
  +13.0 / +0.4; r300 +11.5 / +43.7 / +2.2; r600 +18.2 / +110 / +8.2. Winners take ~58% of middle gems (r300 157 vs
  113). Own-half farming is level; the enemy half is barely farmed by anyone.
- Middle cycles (`midcycle.py`, to r600): the team that wakes a middle group captures it 88% (93.5% with no enemy
  within 8 at the wake, 75% with one). Winners wake 52.8% of middle groups but take 59.7% of middle gems; 13.8% of
  middle gems are taken from the waker. Availability -> wake lag quartiles 0 / 12 / 47 rounds.
- Solo supply (`supply.py` on the solo baseline): even with the whole map free, groups sit up and asleep at full health
  60-72% of rounds (Elk 64%, Golem 72%, wolves 72%, gem clusters 52%): the team's farm is champion-time bound, not
  supply bound. Throughput (walk, clear speed) is the economic lever; walking is 55% of the Prism's rounds.
- 16:10 D t1 49.9 [48.9, 50.8].
- Stat growth (`stats.py`, medians): Cassi stays at 600 max HP / 30 Str through r500 and earns 20 gold by r300 (Issac
  40); Willow earns nothing; Prism 775 gold and 237 bag by r300, Vesper 657 gold. Cassi & Issac are in 97% of our
  comps and stay at base stats: they clear for the Prism and take no shares.
- **Early bags decide** (`bagwin.py`, mirror): at r150 a Prism bag lead of 20-50 gems wins 63%, 50-100 72%, 100+ 83%
  (median Prism bag 105 at r150); team wealth +20-50 at r150 wins 65%. A modest, consistent early edge is a 60% bot.
- Priors on middle pricing (macro2-race 44.8, macro3-intent 47.1): both *discounted* contested groups and lost
  ("contesting is worth it"); home_ground (spawn-walk ratio ^1.89) and mid_exposure 1.36 are static tuned weights.
  Untested: a derived *denial / urgency* value (a middle group not taken now goes to the enemy, a race swing of 2W x p),
  replacing the static weights. Candidate line E.
- 16:30 D t2 50.2 [49.2, 51.1].
- 16:35 **D d-stakes done: level** (patch `patches/d-stakes.diff`). `economy/stakes.cc`: life_gems (respawn x side's
  rate x output, Prism premium, gold, kill gold; C&I both) and bag_gems (to the killer's win, x killer Prism premium)
  in every fight valuation incl. turn_order bids. Derived life_gems mean ~75 (Prism 127, Vesper 100, C&I 63, Willow
  46) vs 15.8 implied: the planner's kill worth also pays out max health, which carries the life; life_value is a
  residual. Train: t1 literal 49.9, t2 normalised (life_value x life_gems/75) 50.2, t3 +bids 50.2, t4 audited 50.3
  [49.3, 51.3]; OOF +8%. Kills +10 gems a game, Prism deaths ~level. Shelved.
- 16:40 Launched E `e-denial` (brief `briefs/e-denial.md`), with a note on the opening plan's r<=100 weight.
- C&I kills (`cideath.py`): 1.85 a team-game, 63% by the enemy Prism; 66% of those from 90%+ health 3 rounds before
  (bursts, not attrition): more health from gold would not save them much.
- **First Prism-on-Prism kill** (`firstpk.py`): in 770 of 1,700 games, the killer's team wins 94%. In 25% of them the
  killer was *poorer* (victim bag median 399) and in 18% within 50 gems: 43% of these game-deciding kills (19% of all
  games) are not bag-decided; the victim stood outnumbered (allies - enemies within 6 about -1).
- 16:50 **C c-balance done: level** (patch `patches/c-balance.diff`, `economy/contact_risk.cc`): every farm job priced
  net = min(worth, worth(1-p) - loss + gain), p from enemy spread (fitted 2.3 sqrt(a)), hazard 0.012 x/sqrt(1-x)
  per contact round (x = enemy share of output x health; fitted on 835k contact rounds), death cost with premiums and
  respawn at farm rate; kill gain symmetric. Kept home_ground / mid_exposure. Train t1 50.4, t2 49.0 (downside only:
  gave up work), t3 50.2, t4 50.2, t5 (audited, unseen enemies spread over the map) 49.9 [48.9, 50.8], OOF +40-50%.
  t2-t4 cut deaths 4-10% and Prism deaths up to 18% with no win; nearest-ally distance unmoved. Shelved.
- **Lesson so far (A-D):** the bot sits on an optimised risk/farm frontier: changes that trade farm for safety or
  safety for farm read level (C cut deaths, D gained kill gems, A raised Prism share, B sped crews: all ~50%). A
  gain needs a Pareto move: more farm at equal risk (throughput), or better information.
- 16:55 Launched F `f-thru` (brief `briefs/f-throughput.md`).
- 17:1x E t1 46.9 [46.0, 47.9], t2 47.1 [46.1, 48.1]: denial pricing loses ~3 (first non-level result).
- 17:10 Coordinator (box etiquette): every extract.mjs gets --threads 8, one extraction at a time, sample batches. Relayed to E and F.
- 17:25 **F f-thru stopped (unfinished)**, patch `patches/f-thru.diff`. Traces (200 debug solo maps): solo time walk
  53%, clear 27%, recall 6.6%, hold 4.7%; recall + walk out is 0.5 rounds *shorter* than walking (recalls are travel);
  detours <= 6.6% (attributable ~1.4%), abandoned clears ~2%, overlap-able holds 0.6%, path crossings <= 1.2% in sight:
  no addressable waste above ~2% of champion time. chain1 (two-job lookahead, rate of both): solo +4.0% slower
  [3.4, 4.5], collected @300 -25.8, OOF 808 vs 149 (a chain's rate lies between its jobs', so detours look good; most
  jobs had no follow-up left to us). chain2 (surplus over the best single rate) built, not read.
- 17:25 **E e-denial stopped (unfinished)**, patch `patches/e-denial.diff`: t1 46.9 [46.0, 47.9], t2 47.1
  [46.1, 48.1], t2b 47.1 [46.2, 48.1], t3 45.7 [44.8, 46.7]; control e-ctl 49.1 [48.1, 50.1]. Pricing denial of
  contested groups up loses 3-4 points, as discounting them lost in macro2/macro3: the static middle weight sits at
  the optimum both ways.
- Insight: chy-ref is on an optimised frontier for every single-mechanism change measured today (Prism share, crews,
  contact risk, fight stakes): mechanisms moved (deaths -4-10%, Prism share +1pt, crew clears faster, kill gems +10)
  and win rate did not. Games are decided by the early Prism bag (r150 lead 20-50 -> 63%) and the first Prism-on-Prism
  kill (killer's team 94%; 43% of those not decided by bags, the victim outnumbered by ~1), the economic gap is the
  middle (winners +44 middle gems by r300 vs +11.5 own half), and solo execution has no waste above ~2%.
- E's report: the control (its code with ref's static weight) read 49.1, so its structural edits (sound prunes
  replacing ref's tuned bound) cost ~1 point and the denial term ~2. Denial measured from waker rates is only ~0.18 of a
  middle group's gems (own half ~0.10) against ref's static +0.36, so the middle lost priority: middle wakes 46.6% vs
  53.4%, middle gems @300 100.8 vs 111.4, own-half 239 vs 227; fewer deaths (8.09 vs 8.63) and Prism bags slightly up
  (r150 111 vs 104) yet -3 points. The static 1.36 prices more than denial (what we lose for good by leaving a middle
  group). The saved e-denial diff includes unbuilt, unsmoked auditor fixes. Scratch copy `variants/e-ctl` left in place.
