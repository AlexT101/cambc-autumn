# quill: farming-macro refactor of astraeus (2026-10-31)

Goal: astraeus with better farming macro beating the frozen baseline
`bots/variants/astraeus-base-d0a8a94-quill` (primary checkout) 60%+ over 10k+ games at unlimited fuel
(`--fuel 1000000000`), own drafts. Dev suites: ladder, gen, maps/fresh-9600..9639. Confirmation (held out):
maps/fresh-9640..9659. A/B names `quill-*`; variants in the worktree's `bots/variants/quill-*`.

Off-limits: champion-vs-champion combat micro, the draft, emblem and shop choices.

## Log

### Ladder study (2026-10-29/30 ranked games among the top 8; scripts in the session scratchpad)
Data: 2241 distinct ranked games of 2026-10-29/30 among IF, us ("prism best girl"), Mite, Ad Astra, newer team, print
dont int, NEETCoders, hello (extract.mjs into the session scratchpad; team names joined from group.json).
Ratings at 10-30: IF 2564, us 2437, Mite 2423, Ad Astra 2403, ... Our record: IF 108-117, Mite 121-104, AA 128-67.

- **We already out-farm every top team early.** Paired in the same games (us/them), captured gems at r300 / r600:
  IF 224/192, 506/448; Mite 246/178, 523/433; AA 253/141, 572/349; NEET 256/139, 550/313. Gold earned at r600
  level with IF (3221/3196), ahead of the rest. Against IF we win 44%: in our losses IF out-captures us
  (r600 534 vs 430) and out-kills us (kill gems 172 vs 101, our deaths 16.8 vs 9.3); in our wins the reverse. The
  farm gap there is downstream of fights, both ways. So the ladder holds no team whose farming we can copy; the
  teacher (70% on macro) is beyond it.
- Time shares (champion-rounds, all games): ours camp 16.5, hold 6.3, walk empty 35.0 (highest of all teams; Mite
  29.2, AA 29.6), walk with bag 16.8 (lowest), recall 1.9 (Mite 5.8, newer 5.6: they recall home more and walk less),
  dead 13.5 (Mite 9.5, AA 8.7, newer 8.8).
- Elk-group clears: ours 35 rounds first hit to clear, 17 rounds with hits, 3.2 hitters, 1.42 visits, 35 camp damage
  taken per gem; Ad Astra 21 rounds, 15 with hits, 2.5 hitters, 1.17 visits, 23 per gem (melee tank in front,
  partner behind). The gap is the dead time inside clears (visits, late joiners), not the hitting.
- Walk-outs: rounds from a recall landing to the next camp hit: ours 21.7 (AA 16.5); capture -> next hit 12.1 (AA 9.0).
- Cohesion (allies within 5, off spawn): ours 1.5, IF 1.5, others 0.85-1.1.

### Solo baseline (quill-solo-base, 326 maps x 2 sides vs bots/idle, unlimited fuel)
Round to 1000: 836.9 mean; collected @300 341, @600 734; gold @600 3356. Time: camp 23.0, hold 8.5, walk 31.2,
walk with bag 21.3, recall 8.6, tribute 3.1, on spawn 2.8. walk_audit: 51% walking; 12.6 recalls per champion-game
(7.5 at hp >= 80%), recall + walk-out ~1446 champion-rounds a game (39%); idle off spawn 7.1% (55% of it beside a
respawning group); 34% of to-camp legs skip a nearer available group by ~9 steps; 48% of to-camp legs head to a group
an ally works or heads to; groups sit up 18 rounds (own side) before their first hit; camp damage 23.8k a game
(23 per gem). Captured 29% of the supply bound (own 48%, mid 29%, enemy 10%).

### Diagnosis that set round 1: strong groups are solo jobs
Ladder 00ambush (IF beat us 1012-698 with 3 deaths each): 100x100, Elk groups 45-64 steps from spawn. IF walked all
six bodies to Elk1 (5040 hp), cleared it in ~15 rounds with damage spread, stepped 6 tiles to Elk2: 157 gems by r200.
Ours trickled in alone (Issac: 37 steps, 480 of 5040 hp dealt, 600 taken, recall at 27%, 37 steps back, repeat): 51 by
r200. Same pattern unopposed. Cause in code: farm's rate ignores the home trips a job's damage forces
(cycle = trip + clear + capture), health is only a hard filter (`spare_health`), and unaffordable groups are chipped
as `risky` fallbacks; crews form only by accident since each champion values a strong group alone or by the share of
claims it already sees. Physics: team damage ~ hp x strikers' strength / crew output, so a crew of k takes 1/k in
total and 1/k^2 each; extra damage costs recall + walk back out.

### Round 1: crew economics (quill-crew, coder report summarised)
- Every job's cycle += extra_trips x (recall_turns + spawn->group steps), extra_trips = ceil((D_me - budget)/usable)
  with the bold budget (`/camp_risk`); `risky`/`beyond_spare` removed.
- D_me from crew damage shared by water-filling over members' tank scores ((hp - line*max)/camp_taken, x1.5 melee):
  camps hit whoever tanks, so damage levels the scores. (Strict "tank takes all" never formed crews.)
- Expected crew: me + claimers + available allies (visible, unclaimed or on harmless groups, near the group or me;
  everyone on round 1) -> proposals; joiners count available allies too. Bail-out after 4 rounds in reach with no ally,
  30-round ban. Crew value x1.5 while claimed (stickiness), x0.8 for a rival op while another is under way, no expected
  allies with a visible enemy within 10.
- Solo ladder smoke (70 maps one side): round to 1000 -2.3% [-5.7, +1.6], collected @300 +17 [+3, +32].
- **A/B quill-crew1: 57.4% of 10892 (56.5-58.3)**, dev suites (ladder 54.3, gen 54.3, fresh 52.1-63.7). Committed as
  bots/astraeus (9329e6b5).
- Formation (quill-form, separate coder): tank/focus/side tiles/arrival wait in camp fights; solo smoke level
  (-0.5%), camp damage per gem -5%, 79% of crew camp hits on the declared tank. A/B running; merge quill-cf and
  quill-crew06 (crew_trip_risk 0.6) A/Bs running.

### Round 1 results (all vs astraeus-base-d0a8a94, 10892 games, dev suites, unlimited fuel)
| variant | win % (95% CI) | note |
|---|---|---|
| quill-crew (trip risk 0.35) | 57.4 (56.5-58.3) | committed 9329e6b5 |
| quill-form (formation alone) | 47.9 (47.0-48.9) | tank/focus/side tiles/arrival wait: lost |
| quill-cf (crew + formation) | 54.4 (53.5-55.4) | formation costs ~3 on top of crew |
| quill-crew06 (trip risk 0.6) | **58.6 (57.6-59.5)** | committed b6ba5106 |
| quill-crew08 / crew10 | 58.7 / 57.9 | trip risk flat 0.6-1.0: keep 0.6 |
| quill-look (lookahead on crew 0.35) | not A/B'd | solo smoke +0.5..+1.4% slower, choice changed on ~5% of turns: dropped |
Crew A/B replays (ladder+gen+2 fresh, 1676 games): captured @600 587 vs 552, deaths 4.78 vs 5.24, camp deaths 0.41
vs 0.54; clears per type about as efficient as the base's but 7-10% more elk/golem clears. Weak classes: shared-gems
(108 games, 31-33%), diagonals, gold-centre, arena ~47-50; strong: golem-heavy 73, dense-camps 74, gem-flood 78.
Formation reading: it moved 79% of crew camp hits onto the tank and cut camp damage per gem 5%, but the positioning
(steps toward strikers, waits) costs more than the health it saves; heal trips are mostly shared with bank/shop trips.

### Round 3 (on crew06): Monolith ops (quill-mono) and mid-game availability (quill-avail)
- quill-mono: Monoliths on mixed maps as crew-only strong-group ops (whole team expected, side weight squared, skip
  with a visible enemy within 10, gather outside reach until 60% of crew output is near or 12 rounds, stickiness 2.0,
  siege no longer joins on ally claims). Solo smoke -0.8% [-1.8, 0.0] (only Monolith maps differ; faster on 8 of 9).
- quill-avail: availability by kind with arrival ETAs (spawn, heading home, tributing, on other strong groups if the
  op share beats their job x1.8, ...), staggered-arrival pricing, rendezvous waits <= 4 at spawn/altar. Solo smoke
  -2.2% [-4.2, -0.3], gold @600 +149; but crew share mid-game did not rise (more strong-group work instead).
- **quill-mono-1: 59.2% of 10892 (58.3-60.1)**: committed (folded into the quill commit that also carries sg).
- quill-avail-1: 58.4% (57.4-59.3): level with crew06; solo speed gain didn't carry. Not merged.
- quill-rho-1 (worth*H/(H+T) - rho*T, team-measured rho, capped at the best old rate): **54.1%**, solo smoke +1.7%
  slower. The average-reward criterion lost: long jobs are riskier against an opponent than their rate says; the
  ratio with its horizon is the better proxy here. Dropped.

### Where mono still loses (2188 extracted games of ladder, gen, fresh-9600..9602)
In wins: deaths 2.9 vs 6.7, captured @600 634 vs 521. In losses: deaths 7.4 vs 3.4, captured 525 vs 584. Fights
decide losses; the farm edge is +7% on average (587 vs 548 @600). Death circumstances are the same for both bots
(53% with no ally within 4, 36-39% outnumbered, 81% fighting, 47% on own side), so no macro-shaped death pattern.
Ladder maps lost both sides: dunes, eight, expanse, gem-fields, gemfight, great-wall, interlock, pilgrimage,
stampede, vault, tangle, uncharted-lands.

### shared-gems fix (quill-sg)
Cause (coder's study of the 108 A/B games): kite() sets every kiter's claim on the big group, so farm prices a crew
that isn't there (kiters' output counted, a kiter as tank, trips instead of the spare-health filter): champions that
kite() can't place (melee vs elk reach, no spells) work the group nearly alone for hundreds of rounds (camp damage
6961 vs 4521 by r400, deaths 13.95 vs 9.84 a game). Fix: kite()'s groups (`shared_gems && big_group`) get the base's
farm pricing. On those maps it now plays like the base; elsewhere byte-identical.
- **quill-sg-1: 59.4% of 10892 (58.5-60.4)**: committed as bots/astraeus.
- Solo (ladder+gen, 652 games) mono vs base: round to 1000 -3.2% [-4.1, -2.2], collected @300 +19, @600 +15. So
  of crew economics' +9 points only a small part is raw farm speed; the rest is interaction (deaths 4.8 vs 5.3 a game;
  when we die first we still win 44%, the base only 32%).

### Round 4: carrier (quill-carry) and crew-scaled side weight (quill-side)
- quill-carry (on mono): crew captures consolidated onto the biggest bag (Prism first), carrier chain limit 90 near a
  fit ally. Tributes 27 -> 24 a game, mean bag 37 -> 42, but walking with a bag up and tributed @600 -76 in solo.
  **A/B 59.2%**, level with mono: dropped.
- quill-side: side weight 1-(1-w)/k for crews of k (visible/arriving members only). Fires rarely (16 flips in 14
  games); mid/enemy-side captures are rare for both bots (14 games: own 276, mid 17, enemy 7).
- Replay (interlock, a ladder map lost both sides): Marcella + HoR as a pair on Elk2.mid' (2 elks, 5040 hp) took 1920
  damage over 20 rounds, the enemy arrived, HoR died to camp + enemy, Marcella fled at 7%. Crew ops on contested
  strong groups by small crews get third-partied.
- quill-side-1: 59.1% (58.2-60.0), level with sg: not merged.

### Confirmation (held-out maps/fresh-9640..9659, 10240 games, unlimited fuel)
**bots/astraeus at the quill branch tip (= quill-crew06 + Monolith ops + shared-gems fix): 60.6% (59.7-61.6)**, every suite
58.6-62.7%, 0 failed matches. Dev (ladder, gen, fresh-9600..9619): 59.4% of 10892. Goal met; stopped.

### Open ideas
- Formation parts alone on the final candidate (built, not A/B'd): `bots/variants/quill-ffocus` (crew focus fire
  only) and `quill-ftile` (non-tank side tiles only). The whole formation lost ~3 points; one part may still pay.
- Contested strong groups: small crews on mid/enemy-side strong groups get third-partied (interlock). Price the
  exposure window (clear rounds x enemy presence) so contested ops want bigger, faster crews.
- Monolith-only maps (102 dev games, 50%) still use siege(); crew ops there are untested.
- Crew economics fuel: prunes are bypassed for strong groups and crew planning runs every farm turn; needs a fuel
  pass (bench.py, real budget) before any submission.
- What didn't carry: lookahead (solo neutral), average-reward criterion (54.1%), mid-game availability (level),
  carrier consolidation (level), crew-scaled side weight (level), trip risk 0.8/1.0 (flat).
