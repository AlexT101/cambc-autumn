# Macro refactor notes (branch macro-1, from ef8f0b84)

Goal: astraeus with better macro (targets, farming, banking, retreat, coordination, comms) beating the frozen
baseline `bots/variants/astraeus-ef8f0b8` 60%+ on the dev suites (ladder, gen, fresh, maps/fresh-6003..6018), confirmed
on held-out maps/fresh-6067..6074. All A/Bs at --fuel 100000000, run names `m1-*`.

## Starting point (2026-10-30)

Architecture today (code map by an Explore agent):
- Per-champion greedy farm choice: rate = worth / (r (1 + r/horizon)), cycle = trip + clear + capture; claims posted
  through one shared claim slot (and the priority payload for visible allies). No joint assignment; duplicate claims
  in the same round both stand. Crew joining only if it beats own best; `help` override for struggling allies.
- Health cost not in the rate (a hard filter). Enemy discount static (`home_ground`).
- Retreat always to spawn, claim dropped.
- Banking: chain while bag < 45 and no credible enemy within 3, else to the nearest altar.

Past evidence (EXPERIMENTS): champion time walking 31% + walking a bag 20%, camp hits 18.5%, holding 9.4%; ~42% of
own gems asleep at any moment; eris (duos, team hunts, power-play, denial) all level: "anything that takes champions
off farming costs about what it gains".

## Summary (end of the 2026-10-30 session)

What moved the win rate was not a new coordination mechanism but how the team spends champion time: every
change that kept champions working (shorter cycles, no standing at respawns, later recalls, bolder camp and retreat
thresholds) gained, and every cautious one lost. The structural pieces (claim board, ownership, need bits, lock
control, stall breakers) are each level to +2 but remove real failure modes and carry the comms the team now shares.
- Claim board: per-body slot of (claim, ETA bucket, need) every turn instead of one overwritten claim slot;
  ownership (senior claimant unless 2+ ETA buckets earlier) turns duplicate claimers into crews valued by their
  share; the need bit lets an unseen ally ask for a partner. +1.8 (51.8% dev).
- Altar locks worn to one hit (the enemy cannot replace its own lock), final hit + tribute in one turn: level.
- Stall breakers: level (mostly mirrored freezes), stalled champion-rounds -61%.
- Time-at-work package (e926bbeb): cycle horizon 25 (was 100), max_wait 0 (was 5), recall line 0.25 (0.35),
  camp_risk 0.25 (0.35), retreat ratios 3.5/3.0 (2.5/2.0): 58.8% dev (58.7 probe + 58.9 rest), held-out ~60.
Open: the knobs plateau near 59; next levers are structural versions of the same idea (heal trips merged with shop
and bank visits, respawn-timed crews, fewer long walks), and the remaining symmetric contests.

## Log

### Replay study of the baseline mirror (582 games, m1-mirror0; scripts in scratch.tar.gz, replay-study/)
- Time: walk empty 33%, walk with gems 18%, camp hits 17%, hold 5%, recall 7%, dead 5.5% (loser 7.6, winner 3.5),
  idle 6%. Recall loop (channel + walk out of spawn) ~25%. Productive 22%.
- Group state, gem-weighted: up and unworked 44% (own half and mid alike). Team harvests 49% of its half-map supply
  (winner 55, loser 43; mid 55 vs 20). Enemy half: 4%.
- Solo vs bots/idle (m1-solo0): 1000 gems at round 878 on average, barely faster than the mirror's median game (958):
  the bot's own farming speed, not the opponent, is the limit. Solo time budget is the same as the mirror's. 19 shop
  recalls a game at high hp, 18 heal recalls.
- Multi-champion clears 40%; duplicate claims in 56% of team-rounds (one shared claim slot overwritten; `taken` false
  for whoever thinks it claimed first). Pairs arriving together are efficient but camp respawns; crew joins mid-clear
  cost +19 champion-rounds per Elk; interrupted clears (Elk 13%, Golem 24%) run at 1/3 the gems per champion-round.
- Deaths: loser 5.0 a game vs winner 2.0. Fight outcomes follow the hp ratio at the first hit (K/D 0.13 -> 7.9) and
  max hp (items, i.e. gold), much more than numbers (+-2 champions: 0.83 -> 1.21). 48% of deaths start below 75% hp.
  Support is rare: 0.17 joiners per fight; an ally 7-15 tiles away never joins in 62% of side-fights. After a death
  K/D is 0.59 for 60 rounds.

### Step 1: claim board (1e7af34a)
Comms rebuilt as one mixed-radix number: a slot per ally body (claim, ETA bucket, need bit), written every turn, then
camp record, bag, sightings as room allows (sightings mostly gone on 4-5 bodies). Ownership: senior claimant owns a
group unless another is 2+ ETA buckets earlier. Farm: a group an ally owns is valued only as crew; need bit asks for a
partner (unseen allies now answer help).
- Coder's small A/Bs (396 games): spec version (crews only on need) 42.4%; crews allowed on any owned group 58.1%;
  crew limited to one partner 46.5%; new layout with old farm rule 52.0%. Restricting crews loses: being together
  pays against the opponent even when it costs farming time.
- Full dev A/B (m1-board, 9356 games): 51.8% (50.8-52.8). Ladder 58.6 of 140. The small-sample 58% was noise. Time
  budget and overlap metrics barely moved (two allies walking to one group 22.6% vs 22.7%): crews still join.

### Probes (single knobs on the board version, probe suite = ladder, gen, gen-s1, fresh-6003..6008, 4236 games)
Diagnostics of where the slack is, not candidates:
| probe | win % |
|---|---|
| board (dev suites) | 51.8 |
| home_power 1 (dev) / 0 (dev) | 51.5 / 49.2 |
| recall line 0.25 / 0.15 / 0.50 | 53.0 / 51.7 / 42.5 |
| camp_risk 1.0 (cautious) / 0.2 (bolder) | 42.5 / 50.7 |
| recall 0.25 + camp_risk 0.25 | 53.1 |
| chain_bag_limit 90 / 20 | 51.6 / 51.0 |
| farm stickiness 2.0 | 51.2 |
| no shop trips | 50.2 |
| no turn-end recall feint (only on R/S/B/P turns) | 48.9 |
Reading: caution costs heavily (time out of the field), boldness gains little: the risk posture is near its optimum.
Solo: home_power 1 / 0 reach 1000 only 2.2% / 2.8% sooner: supply is not binding, champion capacity is.
Bank limits, stickiness, shop trips: flat.

### Step 2: altar locks (f1166194)
Replays: on 1-altar maps the loser is fully locked out 57% of rounds; locks stood for hundreds of rounds because only a
banking carrier ever hits one. Rule trick: one lock per team per altar, so an enemy lock worn to 1 hit can't be
replaced. Built: any champion with a spare attack wears enemy locks on altars we use down to 1 hit; the final hit and
the tribute in one turn; hold the final hit while a visible enemy carrying a lock could relock during the channel
(at most 8 rounds); lock enemy-side altars too. Dev A/B (m1-locks): 52.2% (board 51.8): level.

### Step 3: stalls (608c09c1)
37 of 838 maps had our champions frozen 200+ rounds (whole-team freezes in siege/kite G, contest standoffs P, farm F).
Fixes: sieges/kites with no progress for 40 turns give the group up 300 rounds; a siege with no way goes to farm;
contest standoffs end after 30 quiet rounds (chase if we win, extra bodies leave if the rest still match); a bag no
altar can take counts the whole game as left; skip respawns an enemy stands on; step off a respawning tile; skip
groups wholly in a pack zone after 20 rounds; sealed altars treated as locked; corridor jams drop the target after 8.
Stalled champion-rounds -61%; A/B level (52.1 -> 52.2 on 1750): the freezes were mostly mirrored.

### Probes, round 2 (on 608c09c1 = board + locks + stalls, dev 51.8%)
| probe (probe suite) | win % |
|---|---|
| crew value x1.5 | 52.3 |
| help 16 / partner 20 | 51.9 |
| cycle horizon x3 / x0.5 / x0.25 | 49.1 / 53.5 / 53.3 |
| horizon x0.5 + recall 0.25 + camp_risk 0.25 | 55.4 |
| max_wait 2 / 10 | 54.6 / 50.5 |
| retreat ratios 3.5 / 3.0 (bolder) | 52.5 |
| pursuit_steps 1 | 51.6 |
| gold_price_scale 3 | 51.1 |
| no chase / chase off own ground too | 49.4 / 47.5 |
Common thread: champion time spent working beats safety margins and waiting. Shorter cycle horizon (near, quick
jobs; fewer long walks to big groups), no standing at respawns (max_wait 2), a later recall line, and slightly
bolder camp and retreat thresholds each help; caution (earlier recalls, costlier camp risk, waiting longer) loses.
Chasing as now is right (both directions lose).

### Step 4: tank formation (not kept)
86% of formation hits on the tank, but camp damage per gem and heal trips unchanged: every awake monster hits
someone each phase, so moving hits saves nothing; 52.2% of 2188.

### Step 5: c1 = 608c09c1 + horizon 50 + recall 0.25 + camp_risk 0.25 + max_wait 2 + retreat ratios 3.5/3.0
- c1 dev: 57.6% of 9356 (56.6-58.6). Its games (ladder, gen, gen-s1; 964 extracted): captured +58 gems a team-game
  (mid +27, own +27), tributed 842 vs 770, idle 4.2% vs 5.8% of champion time, camp hits 17.2 vs 16.4%; deaths up a
  little (camps 1.01 vs 0.67, champions 4.79 vs 4.51), kills 4.21 vs 4.47. The gain is farming throughput.
- Combos on c1 (probe suite, c1 there ~57.5): max_wait 0 58.7; + horizon 35 58.9; + horizon 25 (c3a) 58.7;
  + ratios 4.5/4.0 58.2; + recall 0.2 56.5; horizon 35 + camp_risk 0.2 57.8; c3a + stickiness 1.0 ~58.1,
  + heal_trip_fraction 0.4 ~58.2, + chain_bag_limit 60 ~57.1 (partial). The knobs plateau at ~58.8.
- c3a (e926bbeb): probe suite 58.7% of 4236, rest of dev (fresh-6009..6018) 58.5% of ~2000+ so far.
- c3a held-out (fresh-6067..6074): 59.7% of 4096 (58.2-61.2); default fuel 59.8%.

### Step 6: home trips (95500f74)
A healthy champion (75%+ health) takes a shopping trip only with two emblems' gold: one home visit heals and shops.
Probe suite 59.3% (c3a 58.7). Final candidate:
- dev 59.2% of 9356 (58.2-60.2): probe suite 2511/4236, fresh-6009..6018 3030/5120.
- held-out 59.7% of 4096 (58.2-61.2); default fuel 59.3% of 4096 (57.8-60.8), out-of-fuel turns 11028 vs 9849.
- Last round on 95500f74 (dev, 9356 each): horizon 35 59.2, heal_trip_fraction 0.4 59.3, hurt_health_fraction 0.4
  59.2, recall line 0.30 59.6: all level with it (59.2). The knob space is flat here; kept 95500f74.

### Open ideas
- Structural versions of the time-at-work finding: plan home trips (heal + shop + bank by recall) as one visit;
  respawn-timed crews (a crew commits only when its arrival meets the respawn; pairs camping respawns cost ~40
  champion-rounds an Elk); fewer interrupted clears (13% of Elk, 24% of Golem clears at a third the gems a round).
- Camp deaths rose with the bolder thresholds (1.01 vs 0.67 a game): a camp-lethality check on the bolder recall
  line could keep the time and drop the deaths.
- Fight support through the board (an engaged flag; 62% of side-fights have an idle ally 7-15 tiles away) is
  untested; replays say numbers move K/D far less than the hp ratio, so expect little.
- Monolith team bursts (eris: +4.4 on Monolith maps, 24% of games).
- Symmetric contest standoffs (gift-wrapping 4v4, 1v1 on the-line/stalactites) still freeze.
