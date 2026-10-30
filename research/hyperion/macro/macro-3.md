# Macro redesign notes (macro-3, 2026-10-30)

Running log: hypotheses, measurements, designs, results. Baseline = `bots/variants/astraeus-ef8f0b8` (primary
checkout), own drafts, unlimited fuel. A/B names `m3-*`.

## Tools
- `tools/replay/turn_budget.py <batch dirs> [--by-bot]`: turn budget per class, branch x class, earnings, clears,
  supply, deaths, what decides games. Batches build non-release, so `D round id branch farm_group claim` lines are in
  every A/B replay's stdout.
- `py tools/solo.py CAND REF --suites ladder,gen --one-side --fuel 100000000`: farm speed against bots/idle, ~1 min.

## Measurements (start)
### Mirror (m3-mirror, 582 distinct games, 50.0%)
- Walking ~53% of champion time on both sides; camp hits 17%, hold 5%, tribute 3%, recall 4%, idle off spawn 6%.
- r1-300 the sides spend time identically; the difference is deaths (2.7 vs 4.2%).
- Gems per side: W captured 1000 tributed 1012, kills +75 lost 32; L 786/637, kills +32 lost 75.
- Prism hoarding (`retaining_gems`: keeps the whole bag for Focus until a winning bag or closing): Prism is 57% of the
  loser's gems lost at death; 106 of 143 deaths with 100+ gems are Prisms; 1384- and 1367-gem Prism deaths seen.
- Leader wins: tributed lead r200/400/600 57/64/71%; tributed+carried 64/70/77; more kills 85%; more mid captures 87%.
- Clears: shared Elk clears cost 60-85% more champion-turns/gem than solo and 40% more camp damage (theory: fewer).
- Own-side groups sit up and unworked: wolf 63%, elk 48%, golem 58%, gem cluster 39%, Monolith 91%; mid 75%.
- Deaths: 93/86% follow a retreat branch R in the last 4 rounds, only ~1/3 were closing on spawn.
- Stalls: 02the-pack (no tribute either side), gen-shared-gems-600201600 (all on G 2000 rounds), HoR waiting at an
  altar its own team locked (gen-gem-centre-600205105 r731).
- Median game 972 rounds.
### Solo (m3-solo-base, 326 maps one side, vs idle)
- Mean round to 1000: 878 (15 never). Collected @300 301, @600 683; gold @600 3338.
- So the mirror winner (~970) farms nearly as fast as an unopposed team: farm speed itself is the big lever.
- Solo turn budget: walking ~53% (bag->altar 13, empty->camp 25), camp 22%, hold 5%, tribute 4%, recall 3% + hold
  recall 4%, idle off spawn 8% (14% after r800).

### Solo walk audit (walk_audit.py, 326 solo games; full: walk.md in scratch.tar.gz)
Per game 3818 champion-rounds, 2022 walking in 197 legs (mean 10, 45% of walking in legs of 20+).
Savings upper bounds (champion-rounds/game, overlapping):
1. Walk-then-wait at respawning groups: 203 idle rounds beside a respawning group (arrive ~8 early); 49 to-camp
   legs/game head to a group still respawning (69% with an ally on it too).
2. Recall/shop loop: 10.9 recalls per champion-game, 69% on a capture tile (Q: hold+recall), 77% shop; 4.9 per
   champion-game at hp >= 80%. After arrival 22 rounds (17.5 tiles) to the next camp hit; only 11.5% go back to the
   same group. ~344 gross, ~150 net.
3. Shared crews: 48% of camp-hit rounds shared; Elk 0.87-0.91 turns/gem shared vs 0.62 solo: ~154.
4. Detours: 41% of legs to an available group skip a nearer available one by ~9 steps (half of them worth as much): ~150.
5. Small bags: 57% of tributes under 20 gems; trip overhead 6.8 rounds: ~60 of 110. Altar choice near optimal.
6. Stalls (idle runs 50+): ~45. 7. Bag recalls home then walk to altar: ~35.
Supply: we capture 28% of on-cooldown supply (own side 45.5%, mid 29%, far 11%); far-quartile groups wait 416 rounds.
Opening: first capture r20, first tribute r53 (median), 154 captured by r200.

## Experiments
- b1 (6be0d4ab): Prism retain cap 150 (bank.cc retaining_gems; capture.cc sole holder and Q ride) + make_way past a
  line of allies (pathing.cc label_past_allies; fixes a 1270-round corridor jam at gen-gem-centre-600205105, not a
  lock bug). A/B m3-b1 running.
- m3-b1 total 46.7% [45.7-47.7] of 9356 (dev suites, 3.3 min wall). Split: m3-jam (jam fix only) 50.2% [49.2-51.2],
  kept (logic fix); m3-cap (Prism cap 150 only) 46.7% [45.6-47.7], reverted (b88c9bc1). Prism's hoard is worth a lot
  in the mirror (matches eris's 47.4% for banking past the Focus-doubling bag). Don't cap Prism.
- Farm lab on solo (ad5a839f; variants bots/variants/lab-*, REF m3-b1): every farm knob is flat (+-1%): wait0 -0.8,
  noshop +0.3, noQ +0.9, bigbag -0.5, walk x1.5 0.0, stickiness/horizon/help radius ~0. Crews are a big win: nocrew
  +11.1% slower (noshared +5.6, nohelp +1.3). nohome (no enemy-side discount) -3.0% (risk not judged). combo3
  (wait0 + crew x0.8) -1.2% on fresh solo maps. Conclusion: within this architecture the solo farm is at a flat
  optimum; the walking is structural. The mirror is decided by deaths/kills and fights, so coordination it is.

### Mirror loss study (a9b34082, ~25 games read, 2207 deaths counted)
1. Chased retreat never escapes: 48% of victims in R 6 of last 8 rounds, killer in C in 66%; half no closer to spawn.
2. Fresh third champion: first fatal fight won 50-21 by the side with more champions within 8; 46% of multi-round
   kills landed by a late joiner.
3. Allies keep farming while a teammate dies slowly within reach: 15% of deaths (mostly ally in F, then R, B).
4. Cascades: re-entry where an ally just died (18% of losers' deaths vs 8% winners').
5. E branch (stop game-ender) solo charges: 9% of deaths, 87% by losers.
6. Chasing deep onto enemy ground (less often).

## a1: distress beacon + assist branch Y + retreat toward help (a7d68371)
- comms: camp/second-sighting slot -> distress record (ally, exact tile, round%4, severity 0-3 from rounds we last).
  Posted at turn end when a visible enemy can hit our tile before our next turn, or retreating with bound hits.
- assist (Y): after hold/carry_bag, before shop/chase/contest/siege/farm, not if the search attacked: health >= 60%,
  bag < brake_bag, walk 2..cap steps (cap 12/10/7/5 by severity), step_safely toward the tile.
- fallen filter: 20 rounds after a victim dies at its distress tile, farm skips groups within 8 while an enemy was
  seen within 8 of it in the last 20 rounds.
- retreat toward the nearest healthy ally (seen within 3 rounds, nearer than spawn, <= 12 steps) on the 3rd straight
  retreat turn without spawn progress.
- m3-a1: 44.6% of 2750 (stopped early). By side (463 games): fights better (deaths 5.0 vs 5.2, kills 5.2 vs 5.0,
  net bag gems +8, deaths on own ground 54 vs 61%), economy worse (captured 802 vs 861, gold 5347 vs 5702, camp time
  13.5 vs 14.3%, idle 50+ stretches twice as many). Suspect: the dropped capture/respawn record (allies stop
  learning of out-of-sight captures). m3-a1c (assist_steps 0, fallen_rounds 0: only the comms change) A/B running;
  agent restoring the camp record with distress multiplexed in the slot (capture > distress > second sighting).
- m3-a1c (a1's comms, assist/fallen off): 43.4% of 1469 (stopped). So dropping the capture/respawn record (and the
  second sighting) costs ~6 points: shared camp knowledge is worth a lot. Lesson: comms matter for the economy;
  more camp-state sharing could pay.
- a2: camp record restored, slot three-way (capture > distress > second sighting; low-bit tags), assist as a1.
  A/B m3-a2 on ladder,gen,fresh,fresh-6035..6038 (3212 games) running. Machine load ~150 from other sessions: A/Bs
  now take ~40-60 min for 3k games (3.3 min for 9.4k when idle).
- m3-a2: 50.6% of 3212 [48.9-52.3]. By side: deaths 3.4 vs 3.7 a game (-8%), first death r380 vs 360, economy
  level (captured 879 vs 883). Committed 225a82c3 as the coordination base.
- Probe (probe-camp-unseen): unseen camps reveal nothing, not even liveness; the YAML said otherwise: fixed
  (a87a5ff6). Camp-belief audit (a6c2384a): 19% of out-of-sight group states stale, 77% of near ones from enemy
  activity nobody saw; wasted walks ~72 champion-rounds/team-game (1.6%), comms could fix 0.1-0.4%: not a lever.
  9323 of 29359 farm trips are dropped before the group comes into view (churn).
- On a2: home_power 1 49.6%, home_power 0 49.3%, combo3 (wait0 + crew x0.8) 50.1% (2188 games each): all level.

### Death recipes (aadaea20, 3984 champion kills in 582 mirror games)
Median HP at the first enemy hit 82%; only 26% start below 50%. Recipes: healthy and farming (F) 31% (72% walking,
35% blind); healthy, already retreating (R) and caught 27% (94% had seen the attacker; outnumbered only 37%);
healthy other (E/B/C) 17%; low from an earlier fight 12%; low from camps 8%. An ally within 8 in 64% of deaths,
within 12 in 77%, but walking (F/R). Killers outnumber at the first hit in only 33%.
=> The pack-zone retreat counts only visible allies within pack_ally_radius 5: each champion retreats alone from
   a pack its nearby allies could have matched, and is caught. Testing pack_ally_radius 8 and 12 (m3-v-p8/p12).
- On a2, fight/retreat knobs: pack_ally_radius 8 49.9% (9.4k, partial 6.6k), 12 50.8% (2188); fight_ally_radius 8 +
  pack 8 (t8) 46.8% (1744): counting farther allies in the fight sims makes us take fights we lose; home_retreat_ratio
  1.5 47.4% (6k): more aggression loses (3.0 lost before, 46.7%). The stand/retreat thresholds sit at a sharp optimum.
- Final winning tributes (mirror): median 35 gems, 4 turns; only 22% of games end on a 10+ turn channel; the loser
  ends at a median 690. Games are won by gradual accumulation, not a last big tribute.
- Monolith maps are ~10-12% of dev maps: Monolith bursts are a class gain at most.

## Prism as the team's carrier (pc1, af390d10)
Insight from the cap loss: the bigger our Prism's bag relative to theirs, the better (Focus). So route the team's
gems into Prism: farm values Prism crewing an ally's group, and taking over an ally's cleared hold, at the full
reward when it would hold alone (carrier_holds_alone); allies step off (yield_capture) and skip the capture recall
for a hold Prism takes. Smoke (140 ladder games): our Prism's bag 248 vs 110 at r600, Prism deaths 0.70 vs 1.24.
- m3-pc1: 50.7% of 9356 [49.7-51.7]. Committed 77e54381 with pc2's parts.
- Marcella as carrier when no Prism (gold +2/gem tributed): smoke 15/38 vs 21/38, Marcella gold fell; dropped.
- pc2 = pc1 + carrier distress (help from up to 2x farther, at 40% health) + take_capture_handoff skips carrier holds.
- Assist radius on pc1: assist_steps 20 48.0% of 1062 (stopped), 8 50.5% of 1025 (running).
- Other measurements: shared-clear camp damage lands on melee tanks (Vendetta/Marcella/HoR 69%, Prism 4%): fine.
  Claim churn (a6c2384a): trips dropped before the first hit waste ~7.6% of champion time (yielding to an ally's
  claim ~2-3%, plain flips ~2%); stickiness knobs were flat in solo, so it needs claim arbitration (ETA), untried.
- pc2 (HEAD 77e54381) 48.8% of 3212; pc1 on the same suites read the same. Retreat-help from turn 1 49.9% of 3212.
  gold_price_scale 1.0 51.5%, 2.5 50.6% (3212 each): level.
- Final candidate = HEAD (m3-final). Held-out fresh-6083..6090, unlimited fuel: 50.0% of 4096 [48.5-51.6].
- Claim arbitration by arrival (m3-v-arb, a249ba7e: when we and an ally both claim g, the one arriving sooner keeps
  it, by g's centre field and the ally's known position): A/B running.
- m3-v-arb: 50.4% of 3212 [48.6-52.1]: level; not merged (variant kept in bots/variants/m3-v-arb).
- Held-out at the default fuel (info): 49.7% of 4096 [48.2-51.3]; out-of-fuel turns 16633 vs REF 11548 (+44%:
  assist's capped fields every retreat/assist turn and the carrier checks are not yet made cheap).

## Where this leaves macro (end of session)
Nothing reached 60%. The final branch is level with the baseline (dev 48.8-50.7, held-out 50.0). The measured
wastes are real (walking 53%, claim churn 7.6%, waits 5%) but every fix converts the saved time into other low-yield
time; the mirror sits on a flat optimum for local changes. Open: claim arbitration with an ETA in comms; Prism
formation (allies farm near the carrier, needs prune-consistent bonuses); Monolith/golem team bursts on map classes;
the fuel cost of assist.
