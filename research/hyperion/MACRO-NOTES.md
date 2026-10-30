# Macro overhaul notes (macro-4, from astraeus ef8f0b8, 2026-10-30)

Running log: models, designs, observations, results. Baseline: `bots/variants/astraeus-ef8f0b8` (own drafts),
A/Bs at `--fuel 100000000`. Dev suites: ladder, gen, fresh(gen-s1), fresh-6051..6066 (~9.4k games, ~4 min wall
when the box is free). Held out: fresh-6091..6098.

## Tools

- `tools/replay/macro_stats.py DIR` (extract.mjs `--out DIR` first): per team, winners vs losers: time shares by
  activity, walk segments by what starts/ends them, clears by helpers, captures, deaths, kills, idle groups.

## Self-play picture (m4-self: 512 unique games of gen + fresh-6051; ladder alike)

Time share of champion-rounds (winner team):
- walking empty 31.7%, walking with a bag 19.2%, damaging camps 17.8%, recall channel 6.9%, standing still 6.8%,
  holding a capture 4.8%, dead 3.6% (losers 7.4%), fights 3.1%, tributing 2.7%.
- Walks by what starts them (share of alive time, count a team-game, mean rounds): from a camp 14% (81, 7.6), from a
  tribute 11.5% (35, 14.6), from a hold 10.6% (40, 11.7), from spawn 9.9% (30, 14.7), from a recall landing 8.8%
  (29.5, 13.4), from a fight 6.9%. Spawn + recall walks out: 18.7% of alive time (~60 trips a team-game).
- Group to group: median 21 rounds from the last hit on one group to the first on the next; the chosen group is a
  median 11 tiles off, the nearest live group 9: target choice is mostly near; travel is the map's geometry.
- Camps are abundant: groups up and asleep hold ~4.0 of the map's 6.7 gems/round (sum gems/respawn) at any time.
  The bottleneck is champion time and health, not camps.
- Captures: 99% have one holder. Clears with >=2 champions dealing 10%+: ~55% of striker clears.
- Winners vs losers: deaths 2.5 vs 5.4, kills 4.7 vs 2.0, gems lost 31 vs 71, captured gems 994 vs 789,
  gold earned 5824 vs 4387.
- Champion kills: victim had 0 allies within 6 in 43% of them; (victim side - killer side) within 6: even 38%,
  -1 23%, +1 20%: numbers alone don't decide.
- Monolith maps (123 of 512): no capture in 75; the first capturer wins 37 of 48; median first capture r928.
- Mean Strength 50 / 63 / 88 and max health 960 / 1111 / 1475 at rounds 100 / 300 / 600.

## Model: solo vs pair clears

Solo cycle: travel T + clear C + capture 6 + heal share R*S*C/M (S camp strength, M max health, R ~19 rounds a heal
trip). A pair that both hold: per champion better than solo only if T + 6 < R*S*C/(2M), i.e. only for groups too
costly to clear alone. Pairs pay through fights (local superiority) and safety, not farm throughput.

## Parameter scans (sensitivity, not for shipping as is)

ladder+gen+fresh (1164 games) unless noted, against astraeus-ef8f0b8, unlimited fuel:
- recall_health_fraction 0.35 -> 0.25: 53.9%; 0.20: 51.2% (3212); 0.15: 48.9% (3212); 0.25 + hurt 0.35: 53.5% (3212).
- chain_bag_limit 90: 49.7; camp_risk 0.6 (more cautious): 49.4; home_power 0.5: 50.1; help/partner radius
  16/20: 49.2; gold_price_scale 3: 49.1; recall 0.25 + camp_risk 0.6: 49.5 (3212).
- Reading: the health line matters (heal trips are costly), the rest is flat.
- Recalls: 51 a team-game; 57% start at 60%+ health and 65% carry gems (bank trips by way of spawn), so
  only ~1/3 are heal trips.

## P1: threat-aware recall line (c543a733)

0.18 of max health with no credible enemy near (visible within 12, or Safety's credible hit within 6 steps),
else 0.35; the draft keeps 0.35. m4-p1: **53.3% of 9356 (52.3-54.3)**. Safe line 0.12: 51.8%.

## P2: strong groups as team operations (reverted)

Diagnosis (debug traces, 15 games): 36% of strong-group visits are chips; `spare_health` = real spare / camp_risk
(0.35) budgets 2.86x the health a champion can spend, so champions wake big groups alone and leave; crew shares
count unseen claimers as present and split camp hits by output though the nearest body takes all.
Implemented: real solo budget (camp_risk 1 for solo), nearest-champion crew damage, only seen/arriving partners,
assemble outside reach before waking (wait <= 10), help with a health check.
- With a fallback to the old budget for groups no crew in sight can clear: 48.1% of 9356 (on P1, so -5).
- Strict (no fallback): **38.4%**.
- Lesson: boldness on strong groups pays. Camps never regenerate, so a chip is banked progress, and the
  conservative team leaves half the map's gems (strong groups) to the bold one. Coordination has to make bold
  chips cheaper, not rarer.
- (Suites for these two ran on fresh-6019..6034 by mistake; equivalent fresh maps.)

## Fights and numbers (self-play, narrate.py fights of 145 gen games; conv.py on 512)

- Kills a fight by numbers present (us v them): 1v1 net 0; 2v1 +0.067; 3v1 +0.097; 3v2 +0.026; 4v3 +0.094.
  Numbers help, moderately; ~46 fight starts a team-game.
- At a fight's start, free (not fighting) allies of the side: within 0-2 tiles 0.29, 3-5 0.58, 6-8 0.42,
  9-11 0.33 per fight. ~1.3 allies within 9 tiles stay out of the fight.
- prey() never chases a healthy enemy off our own half unless it holds a capture or carries a bag we can
  intercept (fight.cc ~315): a macro choice ("whether to hunt").
- P1's worst losses are early fight blowouts on fight maps (stalactites: 2v2s lost in r15-99, 4 vs 1019).

## Scans on P1 (all against astraeus-ef8f0b8; P1 itself reads 54.0% on the 3212-game subset
ladder+gen+fresh+6051..6054, 53.3% on the 9356 dev set)

- camp_risk 0.25: 51.8% (9356); 0.20: 51.1% (9356): bolder than 0.35 loses too; 0.35 is a peak.
- P2's crew/assembly parts with the old bold budget (m4-p2b): 51.8% (9356): no gain.
- Monolith bursts at 35 / 50 rounds of team output: 49.5 / 48.7% (3212). Waiting 15 rounds at a respawning
  camp: 49.2%. Chasing healthy enemies off our half (prey's own-ground filter removed): 50.2%.
- Cohesion (farm value x1.15 / x1.30 for groups within 8 of an ally's claim): 52.4 / 52.6% (9356): level.
- **No shared-byte comms at all: 47.9% (3212), i.e. comms are worth ~6 points.** Ablations running.
- First death: 35% before r100, median r164; the team dying first loses ~65% (self-play). P1 dies first
  in 56% of games yet wins 54.5%: it trades safety for economy.
- Carried gold is small (18-86 mean per champion): gold is spent promptly.
- Comms ablations on P1 (3212 subset, P1 = 54.0%): **no enemy sightings 55.7%** (sightings hurt: they feed
  Safety's threats and make champions give way); no claims 50.5% (claims are worth ~3.5); no capture records:
  pending.
- No capture/respawn records: **47.2%** (3212): camp-state info is worth ~7 points, the most valuable comms
  content. P1 refinements (threatened line 0.45 / 0.28, threat radius 3 / 10): 52.6-53.4%, level with P1.
- Plan: comms v2 (m4-cv2): no sightings, a claim field per ally (always current), capture record in its own
  slot. Then v3: more camp knowledge (two capture slots, a group-health slot so chips are known team-wide).
- No sightings on the whole dev set: **55.3% of 9356** (P1 53.3). Comms v2 (no sightings + per-ally claim
  fields + capture slot of its own): **55.0% of 9356**: per-ally claims add nothing over the rotating claim.
- Safe chaining (bag limit 90 instead of 45 while no enemy threatens, on P1): 54.8% (3212; P1 54.0): +0.8, noise.
