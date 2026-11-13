# NYX: macro refactor of charybdis (2026-11-13), running log

Worktree `/home/ubuntu/wt/mac13-nyx`, branch `mac13-nyx-20261113`. Reference `bots/variants/chy-ref` (frozen charybdis).
Every A/B: candidate vs `variants/chy-ref`, `--no-test-draft --fuel 200000`, fast runner, suites `maps/suites/mac13/dev`
(5,120 maps = 10,240 games), `maps/suites/mac13/hold` (2,560 maps), own fresh seeds 146200-146999 for more.

## Log

- 01:59 Read BRIEF, rules, prior macro programmes (research/macro-orchestrators-2026-11-11.md and the eight NOTES).
  Priors that matter: the mirror read flat to ~40 knobs and ~50 designs; Prism duel decides; crews worth ~20 points;
  supply not binding (own groups up and unworked 54%, mid 71.5%), labour-bound (walking ~45-50%).
- 02:00 Debug mirror on the 128 ladder maps (`mac13-nyx-basedbg`, 256 games, 128 distinct), extracted to
  `replays/.analysis/basedbg`. macro_stats: mean 898 rounds; winner/loser deaths 2.7/9.0, kills 9.0/2.7, gems tributed
  @300 104/99 (level), @600 494/244: decided r300-600, by fights and bags. Walking ~49% of alive time.
- 02:25 Found in history (astraeus aa9eb2290, research/hyperion/MACRO-NOTES.md): enemy sightings in comms LOST (removing
  them won 55.3%: they fed Safety and made champions give way); camp/respawn records are the most valuable comms
  content (removing them -7 points); "boldness on strong groups pays; coordination must make bold chips cheaper, not
  rarer". Lead: the team's shared picture of *camps* (not enemies) is where information pays.
- 02:30 Study agent launched on the mirror replays (information gaps at deaths, fight participation, home cycle,
  divergence timeline, stale camp knowledge: walks to groups that are already dead, up-and-unworked groups near idle
  allies). Scripts in `research/mac13-nyx/study/`.
- 02:40 dev and hold suites ready.
- 02:14 Ablations (interventions) on dev, 10,240 games each: `abl-nocamp` (comms camp/respawn record removed)
  **44.5% (43.5-45.5)**: the one shared camp record is worth 5.5 points. `abl-noally` (teammates' tile record off)
  49.8% (48.8-50.7): worth nothing. (The clock: these ran in ~2 min each; the box is quiet.)
- 02:20 Candidate 1 `tcp` (team camp picture) to an implementer: ally record off; as many generic camp-event slots
  as fit; events respawn / member health (chips, kills) / cleared + hold state; post the most useful untold fact;
  readers fold newer facts into CampBelief. Rationale: camp knowledge is the comms content that pays; chips are banked
  progress that teammates can't see today.
- 02:30 Study (research/mac13-nyx/study/, `aggregate.py`): deaths: killer unseen by the victim but seen by an ally in
  16-20%, unseen by all 8-16%. Fights: defending allies within 8 deal champion damage only 10-12% in 3 rounds (attackers'
  43-48%), mostly keep farming; one more early dealer ~10x kills. Recalls: shop 47%, travel 23%, heal 23%, bank 7%.
  First deaths: 46% while already retreating (R), 65% in mid; death 1/3/6 rounds after first hit. Capacity used:
  gem clusters 50%, wolf 28%, elk 39%, golem 22%, Monolith 3%. Stale camps: ~35-40 abandoned walks a game to groups that
  stay dead (~6% of alive rounds); enemy-emptied targets abandoned 4x as often as reached (state learnt on arrival).
- 02:32 Candidate 2 `trs` (retreat into support) to an implementer: a retreat may head for a visible ally where the
  fight model says we don't fall, instead of always our spawn; allies seeing a teammate hit/retreating engage the
  pursuer when the same model says the fight is won. Costs farm time only when someone is already in trouble.
- 02:40 `tcp` pre-audit snapshot: 49.2% of 10,240 (48.3-50.2). `trs` pre-audit 50.1%.
- 02:55 `trs` final (`mac13-nyx-trs`, patches/trs.diff): **49.7% of 10,240 (48.8-50.7)**, level. It fires rarely: ally
  goal on 1.7% of retreat turns (~5 a game), RECV ~4.5 turns a game. Rare rules can't move the mirror; dropped.
- 02:55 Ablation sweep (11 branches nobody measured: wake_ring, guard_turn, fixc, reveal ward, bush ward, all wards,
  mite habit, handoffs, yield, kite, locks) to a builder: looking for subsystems of negative value, as enemy sightings
  in comms once were (+2 when removed).
- 03:02 Ablation sweep on dev (10,240 games each, vs chy-ref): **noward 41.7** (wards worth ~8 points), **yield 41.4**
  (keeping off a sole Prism hold, ~8.6), bushward 46.7 (bush wards ~3.3; so planned/drafted wards at our work site
  ~4-5), mite 47.7 (turn-end tribute habit ~2.3), reveal 49.6, fixc 49.8, guardturn 49.8, handoff 49.7, kite 49.8,
  wakering 49.9, **lock 50.9 (50.0-51.9)** (no altar locks: level to slightly positive). Reading: vision of our work
  sites (planned wards) and camp knowledge (comms camp record, 5.5) are the information that pays.
- 03:05 `tcp` final (`mac13-nyx-tcp-b`, patches/tcp.diff): **49.6% of 10,240 (48.6-50.5)**, level, though live (median
  per game: 31 respawns, 267 cleared states, 1,020 member healths applied by readers). More camp knowledge beyond the
  respawn record changes nothing measurable: the record's 5.5 points are teammates timing own captures' respawns.
- 03:06 Candidate 3 `vis` (value-driven ward policy: one value function over enemy-standable unseen tiles near work and
  here, bush clusters from inside, keep/replace by value margin) to an implementer. Wards are worth 8 points; placed only
  ~1 per 35 rounds per champion against a 10-round cooldown.
- 03:08 Mirror drafts: Cassi & Issac in 123/128 games; their bodies are ~half of all champion deaths (520 each in 128
  games). Candidate 4 `pair` (cohesion under threat: fragile body joins the sturdy one, sturdy one stays in support,
  retreat together; unchanged when safe) to an implementer. Open lead named by earlier programmes (66% of pair deaths
  6+ apart), never built.
- 03:24 Snapshot reads on dev (pre-final, 10,240 each): `vis-a` **51.0% (50.0-52.0)**; `pair-a` 49.7% (48.8-50.7).
- 03:30 Second ablation sweep (ab2-*: Prism shop trips, travel recalls, game-ender stop, Prism recovery, mend step,
  prefer_partial, contest, guard_work, chase, Monolith ops) to a builder. Plan: stack the positive pieces (vis, no
  locks, any ablation that reads positive), confirm on hold and x1, and keep searching for a large lever.
- 03:32 Overseer: dev has carried ~18 reads; iterate on a fresh screening suite and keep dev+hold for keepers; design a
  composite around a shared purpose rather than one subsystem at a time. Generating `maps/suites/mac13/scr` (seeds
  146300-146319, 5,120 maps) for screens; `x1` (146200-146219, 5,120 maps) ready for final confirmation.
- 03:33 Role time use (study reports): the winner's Prism walks 52% of alive rounds (48% carrying), hits camps 12%,
  holds only 8%, yet takes 40% of team capture gems (82% of carried gem-rounds). Willow walks 62%. Asked the study
  agent for the Prism's walk breakdown (to what, whose clears) to size a "Prism pipeline" composite.
- 03:36 Prism study (study/prism_study.py): Prism walks to respawning groups 13-20% of alive rounds; 53% of its captures
  (58% of gems) are clears with allies, 35% alone, 9% ally-only; ~120-210 gems a game of ally-cleared gem groups near
  the Prism go to the ally. Prism capture-gem lead at r300 correlates 0.45 with winning (team 0.33, others -0.04).
- 03:40 **`vis` final (patches/vis.diff): dev 51.0% (snapshot), scr 50.9% of 10,240 (49.9-51.9), hold 51.9% of 5,120
  (50.5-53.3)**: the first candidate above level. Wards placed ~26 -> ~46 per champion per game. `pair` final
  (patches/pair.diff): dev snapshot 49.7%; scr running.
- 03:42 Candidate `vis2` (on vis): ward value weighted by information (tracked enemies' possible-set mass + a base
  weight), and the hold / respawn-wait / altar-wait tile tie-break by the same sight value. Vision is the lever with
  measured weight (no wards -8), and vis shows more of it still pays.
- 03:45 `pair` scr: 49.4% of 10,240: dropped (forced pair retreats ~11 a game cost what joins saved).
- 03:50 Ablation sweep 2 on dev (10,240 each): travel recalls 46.7 (worth 3.3), guard_work 47.2 (2.8), contest 48.5
  (1.5), mend 49.5, partial 50.0, Prism shop-only trips 49.7; ender/recovery/chase/mono rerunning after audit fixes.
  No negative-value subsystem found besides locks (+0.9 when off). Building `vl` = vis + no locks.
- 03:49 Sweep 2 reruns (post-audit): chase 44.4 (worth 5.6), ender 49.0, mono 49.0, Prism recovery off 50.5 (49.6-51.5).
- 03:53 **`vl` = vis + no altar locks: scr 52.3% of 10,240 (51.3-53.3), hold 51.7% of 5,120 (50.3-53.0)**. New base.
- 03:59 `vis2` snapshot (info-weighted ward value + sight tie-break for hold/wait tiles; locks still on): scr 52.2% of
  10,240 (51.2-53.2), hold 51.8% of 5,120 (50.4-53.1). vs vis (50.9 / 51.9): ~+0.8 pooled.

- 04:21 ab_farm on vl vs ref (scr, 1,000-game extract): no economic edge. Gold @300 +3.7 [-24.7, +33.0], capture gold @300 +0.8, camp damage +0.3k. Tributed gems @600 +13 [-4, +30], a trend only. vl's gain is in fights and vision, not farming.
- 04:21 The vis2 agent was still editing vis2 (capture.cc at 04:09) after my snapshot reads, so the scr and hold reads are of an earlier state. I've asked it to freeze and report. v3 builds on the frozen copy.
- 04:30 vis2 frozen (agent report). After my snapshot reads it changed only through fuel (lineage-merged enemy masses, exact pruning) and a hidden-blocker stop. Release smoke 136-120 both times. Out-of-fuel turns 22 vs REF 12; debug 17 vs 14. VSTAND ~28 a game, all on hold tiles (the respawn-wait hook never fires), so the sight tie-break is in practice a hold-only feature. Ward placements +5% over vis.
- 04:31 Two implementers started.
  - (A) `vlx` = vis2 + no locks, then `v3` = vlx + a scouting tie-break on ordinary walks (among equal-length, equal-safety steps, the one whose sight reveals the most information value; walking is ~50% of rounds).
  - (B) `var` on chy-ref: a value-at-risk policy for gem carriers (want_home / keeps_gems / banks_bag priced by the bag, kill gold and dead time at risk against the cost of leaving).
    - Why: the loss study's largest death cluster is Prism killed walking with 200+ gems: excess 65 gems a game, warned 20+ rounds, a recall would have saved 46%.
    - Prism deaths overall: 1.57 a game in losers against 0.09 in winners.
- 04:32 `vl` dev read started, for the keeper reading (dev + hold). `scr2` (seeds 146400-146419) is being generated as the next screening suite.
- 04:27 (the 04:30-04:32 stamps above are ~5 min early) **`vl` dev: 52.0% of 10,240 (51.0-53.0)**. Out-of-fuel turns CAND 747 vs REF 704.
  - vl over dev + scr + hold: 52.0-52.3%, about 52.0% pooled over 25,600 games.
  - `scr2` generated: seeds 146400-146419, 5,120 maps.
- 04:36 **`vlx` (= vis2 + no locks, patches/vlx.diff on vis2): scr2 52.1% of 10,240 (51.1-53.1), hold 53.0% of 5,120 (51.6-54.4), dev 52.1% of 10,240 (51.1-53.0).**
  - Same-suite control: `vl` on scr2 is 51.9% (51.0-52.9). So vis2's information weighting adds about +0.2-0.3 over vl: positive, but within noise.
  - Out-of-fuel turns are up (scr2: 1,012 vs REF 713; vl had 807). A fuel fix to vis2's ward scoring might return a little.
  - A/Bs now take ~3 min per 10k games (the box is quiet). Reads are cheap and implementation is the bottleneck, so a parameter/structure sweep is affordable.
- 04:53 **`v3` (vlx + a scouting tie-break on ordinary walks): scr2 52.4% of 10,240 (51.4-53.4), hold 51.5% of 5,120 (50.1-52.9).**
  - Pooled over the same 15,360 games: v3 52.1% against vlx 52.4%. Flat: the walk tie-break adds nothing measurable.
  - Release smoke 53.9% of 256, 0 failed.
- 04:56 v3 agent report: the walk tie-break hooks into Pathing (step_route, step_towards_funded, descend_with) for farm, bank, shop and guard_altar walks.
  - It changes the step on ~22% of farm turns and 18% of bank turns: 563 changed steps a game, median gain 10 band units, ~5k fuel each.
  - Despite firing that often it is flat, so walk-time scouting has no measurable value in the mirror. Vision's value lies in where wards go and how long they last, not in where walkers look.
  - The agent's cleanup glob also deleted 23 old finished smoke batches; their summaries survive.
- 04:57 Sweep 3 (diagnostic) started, built on vlx: 13 risk/boldness constants, each at a low and a high value (hit_given_reach, mid/max_exposure, recall lines, hurt/home retreat ratios, camp_risk, fight_weight, life_value, credible_weight, crew_trip_risk, carrier_hazard).
  - Goal: find which direction of risk appetite the mirror rewards, then build a principled structural change around it rather than ship tuned constants.
- 05:17 Sweep 3 variants built: 25 of 26, all audited and smoked clean (patches/sweep3.diff).
  - sw-hgr-lo can't be built: a static_assert requires hit_given_reach >= recall_risk.
  - sw-drec-* also moves the draft's champion valuation (draft_recall_health_fraction is read only in draft.cc). It is diagnostic only and not shippable under the no-draft rule.
  - Reads run on scr2 through scripts/queue.sh, two queues.
  - First reads (vlx scr2 = 52.1): camp_risk x0.7 52.3, x1.4 52.1. Flat.
- 05:24 **`var` (value-at-risk retreat/bank policy for carriers, on chy-ref; patches/var.diff): scr2 49.5% of 10,240 (48.5-50.5). Dropped.**
  - Agent diagnosis, from 568k exposed carrier turns over 768 debug games: the risk of death within 5 rounds is driven by local strength ratio (0.56% -> 6.8% across its range) and being hurt (x3-5). Bag size and being the Prism add little once strength is known.
  - The rule fired on ~17% of exposed carrier turns but did not cut big-bag Prism deaths in the smoke. Sending carriers home trades their work time for bags that were mostly not lost. "Boldness pays" again.
  - The study's "a recall would have saved 46%" is hindsight: the same rule fires in many more safe situations than fatal ones.
- 05:24 Sweep 3 so far, scr2 (vlx 52.1): camp lo/hi 52.3/52.1; cred lo/hi 52.3/52.9; drec lo/hi 52.8/51.6 (draft-touching); fight_weight lo/hi 52.8/52.8. All inside +-0.8 of base.
- 05:40 Re-read the 2026-11-11 macro programme summary in research/EXPERIMENTS.md. Its findings:
  - Caution loses in proportion to the work it costs; var fits that pattern.
  - Redirecting the Prism is level; reallocating gems to it is what won.
  - Structural redesigns lose. Tuning is saturated. The team focus call is level, because we already converge.
  - The levers left are: (a) negative-value subsystems, as locks were; (b) information, as wards are.
- 05:40 Started:
  - `hunt`: ally sightings shared through comms for offence only (prey candidates, kept out of Safety).
  - Ablation sweep 3 on vlx: siege, shop trips, TP crystal, Willow-Prism support, fixc_commit, follow strike, open plan, comeback, mid-game gold hump, finish_heal, altar guard.
- 05:47 Sweep 3 on scr2 (vlx 52.1; all 10,240 games). Every constant reads 52.1-53.1 except one:
  - **mid_exposure x0.8: 50.5 (49.5-51.5); x1.25: 53.7 (52.7-54.6).** A monotone 3.2-point spread.
  - sw-midx-hi on hold: 53.7% of 5,120 (52.4-55.1), against vlx 53.0. Pooled over scr2 + hold: 53.7 vs 52.4.
  - mid_exposure is farm's premium on middle-band groups: d_enemy/(d_ally+d_enemy) between 0.25 and 0.68, worth up to x1.36.
  - Reading: in the mirror, taking the contested middle pays more than the tuned premium assumes.
  - The rest (scr2): life lo/hi 52.8/53.0, maxx lo/hi 52.8/53.1, home lo/hi 52.8/52.7, hurt 52.2/52.2, srec-hi 52.1, hgr-hi 52.9, haz lo/hi 52.8/52.3.
  - Next: extend the mid_exposure family (x1.5, x2), read sw-midx-hi on dev, and look for the derivation (denial: a middle group we take is one the enemy doesn't).
- 05:50 **sw-midx-hi (vlx + mid_exposure x1.25 = 1.70): dev 54.1% of 10,240 (53.1-55.0)**; vlx dev was 52.1.
  - Over dev + scr2 + hold (25,600 games): ~53.9 against vlx ~52.4.
  - sw-midx-lo hold: 49.5% of 5,120 (48.1-50.9), against vlx 53.0.
  - Monotone and replicated on three suites. The family mid_exposure x1.5, x2, x3, a wider band and a matching max_exposure has been asked for.
- 05:58 `hunt` built: calls fit in the free comms bits, are answered only in prey, and the audit found no Safety leak. Smoke 56.6% of 256; vlx's own smoke was 57.0. Reading on scr2.
  - Abl3 so far (scr2, vlx 52.1): comeback-off 51.9, crystal-off 52.3, finish_heal-off 51.9, fixc_commit-off 52.2. All level: none of these subsystems carries measurable value in the mirror.
- 06:05 Reads on scr2, against vlx 52.1:
  - mid_exposure family: x0.8 50.5, x1.25 53.7, x1.5 52.4 (mx-150), x1.5 with max_exposure matched 51.1 (mx-150m), x1.5 with a wider band 51.5 (mx-150w); x2 and x3 still running.
  - The peak is near x1.25 (1.70). Not monotone past it, so it is a tuned optimum for the mirror, not a direction to push.
  - `hunt` 51.5 (-0.6): dropped.
  - Abl3: follow-off 51.7, mid_gold-off 52.4, plus the four above. All level.
  - Running `sw-midx-hi` on scr (a fourth suite), with ab_farm for the mechanism.
- 06:15 **`sw-midx-hi` scr: 53.6% of 10,240 (52.6-54.6).**
  - Four suites: scr2 53.7, hold 53.7, dev 54.1, scr 53.6, giving **~53.8% over 35,840 games**. vlx was ~52.3 on the same suites.
  - The mid_exposure curve on scr2: x0.8 50.5, x1.0 52.1, x1.25 53.7, x1.5 52.4, x2 50.4, x3 46.2. A clear interior optimum near x1.25.
  - Abl3 (scr2): openplan-off 52.8, shoptrip-off 52.1. Level.
  - Sweep 4 (13 farm/crew constants around sw-midx-hi) is being built; its reads are queued behind its smokes.
- 06:24 ab_farm on sw-midx-hi vs ref (scr, 1,000-game extract): gold end +241 [+3, +472]; gold @300 +18 [-16, +52]; capture gold @300 +11; tributed @600 +8 [-14, +28].
  - So taking the middle more does not buy a measurable economic edge by r300-600. Its effect is positional: where the teams meet and who holds the contested ground.
- 06:24 Abl3 (scr2): siege-off 51.9 (level); **support-off 50.5** (Willow-Prism support is worth ~1.6).
  - Sweep 4: 24 variants built and audited. gold_farmer_weight was skipped because the draft reads it. Smokes are run by a detached driver; I must check that it has exited when finishing.
  - Sweep 5 started: 18 crew/chase/altar/siege constants around sw-midx-hi.
- 06:39 Sweep 4 so far (scr2; base sw-midx-hi 53.7): chip lo/hi 53.7/53.8; **efficiency_power lo/hi 54.7/52.7** (holders' and farm's gold-efficiency weighting; lower = more even). Reading eff-lo on hold.
  - Box load is ~140-180, so reads are slower. Only a subset of sweep 5 is queued: crew_cap, pack_ally_radius, pursuit_steps lo, crew_tank_line.
  - With ~50 variants in these sweeps, the best one will show about +1.5 from noise alone. A winner counts only if it replicates on another suite.
- 06:47 s4-eff-lo (efficiency_power x0.8) on hold: 54.0% of 5,120 (52.7-55.4), against sw-midx-hi's 53.7. Its +1.0 on scr2 shrinks to +0.3, so it looks partly noise. Reading it on dev.
  - s4 fcp-hi (fight_camp_prior x1.4) on scr2: 53.7, level.
  - Sweep 5 narrowed to 7 variants (load).
- 07:01 Box load is ~220, and a 10k read now takes ~20 min. I stopped the sweep 5 read queue (none of its reads finished) so the remaining time goes to sweep 4 and the final confirmations.
  - Sweep 5's 35 variants are built and 21 are smoked (patches/sweep5.diff), but none is read.
  - s4 fcp-lo 53.3: level.
- 07:09 **s4-eff-lo dev: 54.1%, the same as sw-midx-hi's 54.1. Dropped as noise** (scr2 +1.0, hold +0.3, dev 0).
  - s4 help radius lo/hi: 54.1/53.6. Level.
  - sw-midx-hi is the final candidate. Started its confirmation on x1 (5,120 maps, unused).
  - Started a part-ablation `mo` (chy-ref + the mid premium alone) to show how the parts add up.
- 07:31 **sw-midx-hi x1 (unused suite, 146200-146219): 54.0% of 10,240 (53.0-54.9)**, 0 failed. Out-of-fuel turns CAND 876 vs REF 601 (+0.03 a game).
  - Five suites: scr2 53.7, hold 53.7 (5,120), dev 54.1, scr 53.6, x1 54.0. That is **53.85% pooled over 46,080 games**, ~±0.45 at 95%.
  - s4 hp-hi (home_power x1.25) on scr2: 53.0, level.
- 07:36 **Part-ablation `mo` (chy-ref + the mid premium alone): scr2 50.7% of 10,240 (49.7-51.7).**
  - The premium adds +0.7 on the reference bot but +1.6 on vlx, which has the ward policy and no locks.
  - The parts interact. Contested-ground presence pays when our ward vision makes the middle readable: more wards near work sites means less is unseen around mid groups.
  - Reading mo on hold to check. Also started: `mxe` / `mxl` (the premium only before / only after r300) to learn when it pays.
  - s4 hp-lo (home_power x0.8) 54.1: level.
- 07:49 `mo` hold: 51.6% of 5,120 (50.3-53.0).
  - Pooled with scr2, mo is ~51.0%: the mid premium alone is worth about +1.0 on chy-ref, against about +1.5 on vlx. The parts mostly add, with at most mild synergy, so I'm softening the 07:36 reading.
  - s4 low lo/hi (mid_low_share x0.7 / x1.3): 53.7 / 54.0, level. The band's edges don't matter; the premium's height does.
- 07:52 **`mxe` (premium 1.70 before r300, 1.36 after): scr2 52.4% of 10,240 (51.4-53.4)**, the same as vlx's 52.1.
  - The early premium does nothing. The whole gain comes from r300 on, when games are being decided: holding the contested middle in the mid-game is the lever, not winning the opening race.
  - mxl (the reverse) is running.
- 08:05 The mid premium, finer grid on scr2 (vlx base):
  - 1.36 (x1.0) 52.1; 1.53 (x1.125) 53.7; 1.70 (x1.25) 53.7; **1.87 (x1.375) 54.8 (53.9-55.8)**; 2.04 (x1.5) 52.4; 2.72 (x2) 50.4.
  - **`mxl` (1.36 before r300, 1.70 after): 53.5**, the same as sw-midx-hi. The gain is all in the mid/late game.
  - Testing whether s4-mx137 (1.87) is real or selection noise: reading it on hold and dev now. I stopped the rest of sweep 4 (near, opw, own, rival, stick: unread) to free throughput.
- 08:15 s4-mx137 (premium 1.87): hold 54.5% of 5,120 (53.1-55.9); dev 52.9% of 10,240 (51.9-53.8).
  - Over scr2 + hold + dev it has 53.98%, against sw-midx-hi's 53.83% on the same 25,600 games. Level: the top of the curve is flat from 1.53 to 1.87.
  - x1 and scr reads are running for completeness. Unless they separate the two, sw-midx-hi (1.70, the middle of the flat top) stays the final.
- 08:19 s4-mx137: x1 53.0% of 10,240, scr 52.9%. Over all five suites (46,080 games) it has **53.51%, against sw-midx-hi's 53.85%**. **The final stays sw-midx-hi (mid_exposure 1.70).**
  - Reads are fast again, so the unread sweep-4 constants (own_ground_share, crew_near_radius, crew_rival_factor, open_plan weight, crew_stickiness) are queued on scr2 until ~09:30, as information.
- 08:22 **Final copied into bots/charybdis** (identical to bots/variants/sw-midx-hi/src; patch patches/final-sw-midx-hi.diff against chy-ref).
  - Smoke of bots/charybdis against chy-ref: 137-119 (53.5% of 256), the same games as sw-midx-hi's smoke. 0 failed, 0 broken drafts.
- 08:41 **Part-ablations of the final**, pooled over scr2 + hold (15,360 games each; the final has 53.68% there):

  | arm | what it lacks | win % | the part's worth |
  |---|---|---|---|
  | fa-locks | no-locks (buys locks again) | 52.85 | no-locks +0.8 |
  | fa-novis2 | vis2's information weighting and hold sight step (= vl + premium) | 52.63 | vis2 +1.05 |
  | vlx | the mid premium | 52.40 | premium +1.3 |
  | mo | everything but the premium (= chy-ref + premium) | 51.00 | wards, vis2 and no-locks together +2.7 |

  - Every part is positive in the final, and they roughly add up.
  - Late sweep-4 reads (scr2, base 53.7): own_ground lo/hi 53.6/53.0, open_plan weight lo/hi 52.4/53.1, crew_near lo 53.6, stickiness lo 53.9. All level.
- 08:49 The final pooled over five suites: **53.81% of 46,080 (+-0.46, so 53.35-54.27)**. The commit message's 53.85 was a rounding slip.
  - Last sweep-4 reads (scr2, base 53.7): crew_near lo/hi 53.6/53.6, crew_rival lo/hi 53.2/54.2, stickiness lo/hi 53.9/52.6. All level. Sweep 4 found nothing beyond mid_exposure.
  - Robustness check: generated `v2` (`--mix ladder-v2`, seeds 146500-146519, 5,120 maps), the mix nearer the ladder. Reading the final and vlx on it.
- 08:53 **On `v2` (ladder-v2 mix, fresh): final 53.2% of 10,240 (52.2-54.2), vlx 52.9% (51.9-53.8).**
  - The final still wins there, but the mid premium's share shrinks from ~+1.4 (ladder mix) to ~+0.3.
  - The premium's value depends on map structure: ladder-v2 has gem balls and other group shapes, so the static spawn-distance band captures "contested" less well there.
  - Reading the premium's slope on v2: x0.8 (sw-midx-lo), x1.375 (s4-mx137) and mo.
- 08:59 **Correction to 08:53: I read the two v2 logs the wrong way round.** On `v2` (ladder-v2 mix, 10,240 games each):
  - the final (sw-midx-hi) has **52.9% (51.9-53.8)**;
  - vlx has 53.2% (52.2-54.2).
  - Slope of the premium on v2: x0.8 (sw-midx-lo) 49.2% (48.3-50.2), x1.0 (vlx) 53.2, x1.25 (final) 52.9, x1.375 (s4-mx137) 53.5. mo is running.
  - So on ladder-v2 maps the premium sits on a plateau from x1.0 to x1.375. Lowering it costs 4 points, but raising it neither helps nor hurts.
  - The +1.4 the premium gives on ladder-mix suites does not carry over to ladder-v2. The final's v2 edge (+2.9 over chy-ref) comes from the vision and no-lock parts.
- 09:05 **v2b (fresh ladder-v2, seeds 146600-146619, 10,240 games each): final 53.0% (52.0-53.9), vlx 53.3% (52.4-54.3).** mo on v2: 50.0% (49.0-50.9).
  - So it replicates: on ladder-v2 maps the mid premium is worth nothing (pooled v2+v2b: final 52.95, vlx 53.25 over 20,480 each). On its own, over chy-ref, it is worth nothing either (mo 50.0).
  - On ladder-mix maps it is worth +1.3, and the final gains +1.4 over vlx there. The premium is therefore map-mix dependent but never costs anything at x1.25. The final stays.
  - The final's edge over chy-ref on ladder-v2 (+3.0) comes from vis2 and no-locks.
  - All earlier batches are deleted. With the time left, reading a sweep 5 subset on scr2 as a screen only (crew_cap, pack_ally_radius and crew_tank_line lo/hi, pursuit_steps lo): queues q40 and q41.
- 09:26 Sweep 5 subset on scr2 (base final 53.7, 10,240 games each):
  - Level: aguard lo/hi 53.7/53.8, aleash lo/hi 53.6/53.7, bigg lo 53.6, ccap lo/hi 53.6/53.6, pack lo/hi 53.5/53.6, tank lo/hi 53.7/53.7.
  - Win counts within ~20 games of the base, so most of these constants are close to inert in the mirror.
  - Outlier: purs-lo (pursuit_steps 2 to 1, a shorter horizon for the threat of pursuit, so less caution) 54.6 (53.6-55.6). That is +0.9, inside the selection noise of ~20 variants. Confirming it on hold and dev (q43, q44).
- 09:29 purs-lo does not hold up: hold 53.8% of 5,120 (final 53.7), dev 53.5% of 10,240 (final 54.1). Its scr2 +0.9 was selection noise. bigg hi 53.8 on scr2, also level.
- 09:38 Sweep 5 finished on scr2. All level: cban lo/hi 53.7/53.7, cenemy lo/hi 53.6/53.7, cseen lo/hi 53.9/53.6, cwait lo/hi 53.7/53.8. The crew, altar and pack constants are close to inert in the mirror.
- 09:38 **Clean held-out reads of the shipped bot (bots/charybdis = sw-midx-hi)** on two suites generated after all selection:
  - f1 (ladder mix, seeds 146700-146719): **53.8% of 10,240 (52.9-54.8)**.
  - vr (`--mix varied` stress maps, seeds 146800-146819): **53.4% of 10,240 (52.4-54.3)**.
  - No failed games and no draft failures on either.
  - Out-of-fuel turns: f1 CAND 897 / REF 650; vr CAND 1650 / REF 1289.
  - Ladder mix over six suites: 30,307 of 56,320 games = 53.81%.
  - Reading vlx on f1 and vr for the premium's share (q52, q53).
- 09:40 **The premium's share on the clean suites.** vlx is the final without the premium; mo is chy-ref plus the premium only. 10,240 games each.

  | suite | final | vlx | mo |
  |---|---|---|---|
  | f1 (ladder mix) | 53.8 | 52.9 (52.0-53.9) | 51.0 (50.1-52.0) |
  | vr (varied) | 53.4 | **54.2 (53.3-55.2)** | 49.8 (48.8-50.8) |

  - So the mid premium is worth about +1 on ladder-mix maps (scr2, hold, dev, f1 all agree). It is level to about -0.5 on ladder-v2 (v2, v2b) and about -0.8 on varied maps.
  - Ladder-mix suites, final against vlx: scr2 53.7/52.1, hold 53.7/53.0, dev 54.1/52.1, f1 53.8/52.9.
  - Other mixes, final against vlx: v2 52.9/53.2, v2b 53.0/53.3, vr 53.4/54.2.
  - The shipped bot stays sw-midx-hi, because the brief's suites (dev, hold) are the ladder mix.
  - If ladder-v2 is the better model of the real ladder (AGENTS.md says it is), vlx is the safer choice: it is equal there and ~1 lower on the ladder mix.
  - Both beat chy-ref by 2.9-4.2 on every suite and mix.
  - The premium encodes "the middle band is contested". It holds for ladder-mix layouts but not for gem-ball or varied group shapes, where spawn-distance share is a poor proxy for contest.
- 09:42 **Part-ablations of the final on the other mixes** (10,240 games each):
  - v2 (final 52.9): without vis2 (fa-novis2) 53.4, with locks back (fa-locks) 52.3.
  - vr (final 53.4): without vis2 53.5, with locks back 52.6.
  - No-locks is worth +0.6 to +0.8 on every mix.
  - vis2 is worth +1.05 on the ladder mix but nothing on ladder-v2 or varied maps. Like the premium, it is map-mix dependent.
  - So the 08:59 claim that the v2 edge comes from vis2 and no-locks is half wrong. On ladder-v2 and varied maps, most of the edge over chy-ref (~+3) comes from the base vis change (value-driven wards, present in fa-novis2) plus no-locks.
- 10:00 Finished. No subagents, tmux sessions, drivers or batches remain. The shipped bot is bots/charybdis = variants/sw-midx-hi (commit 010707b4d).
  - Map dirs f1, vr, v2 and v2b are left uncommitted.
