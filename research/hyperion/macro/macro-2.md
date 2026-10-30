# Macro rebuild (macro-2), running notes

Goal: astraeus macro that beats astraeus-ef8f0b8 60%+ (unlimited fuel, own drafts). Notes are my memory for
the session: designs, rationale, replay observations, results.

## Baseline facts (m4-self mirror replays, 326 distinct ladder+gen games, 2026-10-30)

Analysis scripts: `scripts/` in scratch.tar.gz (stats.py, time.py, legs.py, cap2.py, contact.py, lone.py).

- Games: mean 1048 rounds, 6% reach 2000. Winner has fewer deaths in 67% of games, more in 13%.
- Champion time (alive or dead, all rounds): walking empty 35%, walking with a bag 20%, attacking camps 17%,
  standing still off capture tiles 8%, standing on capture tiles 7%, dead 5%, champion fights 2-5%, tribute 2%,
  on spawn 2%. Debug trace of decide() branches (3 ladder maps): farm 54%, bank (carry_bag) 22%, retreat 6%,
  hold 3.5%, tribute 3%, capture recall 2%, chase 2%.
- Walking legs: tribute->camp 12% of walking, camp->camp 12%, spawn->camp 17% (home visits ~11 per champion
  per game, nearly all by recall; most are healthy recalls carrying a bag and shopping).
- Captures: 1.015 holders per capture (solo farming). Median tribute 15 gems (mean 25), ~33 tributes/team/game.
- Map gem capacity (camp types, respawn+7 cycle) ~5250 gems/game for both teams; captured 1784 (34%).
  Utilisation by class: gem-cluster-dense groups on own side 47-67%; monster-heavy (gems/khp < 10) groups
  13-43%; Monoliths 7% (904 gems/game capacity on maps that have them, 63 taken). The untapped gems are
  expensive ones (camp damage) and contested ones. (NB: the extractor's map JSON `groups[].gems/gold/respawn`
  are misaligned between groups; compute from `types`.)
- Solo vs bots/idle (whole map, no enemy): 874 rounds to 1000 on average.
- Contacts (a champion with an enemy within 6), P(die within 10 rounds) by (us incl. self, them) within 6:
  1v1 4.4%, 1v2 12.1%, 1v3 24%, 2v1 2.9%, 2v2 6.5%, 3v1 2.2%, 3v2 4.8%. Local numbers matter a lot.
- Deaths by champions: 45% with no ally within 6 (nearest ally median 12 tiles), mostly walking (not camp work),
  mostly empty-handed, mid (48%) or own side (35%).

## Prior evidence (EXPERIMENTS "eris" and others) that shapes the design

- eris (2026-10-25) tried duos (31-48.7%: fewer parallel jobs, two walks a group, and the partner often did
  not fight), team carrier hunts (49.5%: carriers flee, 7% killed), power-play fronts, ambushes, denial,
  heal cost in job choice (42.2%), relocating instead of pack retreat, survival tweaks: all level or lost.
  Gains only from Monolith bursts (+4.4 on Monolith maps) and crystal travel, decided once from the map.
- Lesson there: anything that takes champions off farming costs about what it gains. So coordination must
  be cheap: self-selected, only where it pays, no walking purely to regroup.

## Design v1: team operations over shared comms (2026-10-30)

Two tiers. Cheap groups stay solo (the existing farm). Expensive or contested targets become team
operations: one shared op record in comms (kind, target, member mask). Any champion may call one, others
self-select into it by value and set their bit, and it ends when its target is done or stale.
- Burst op: a monster-heavy group (or Monolith) whose solo clear is unaffordable or slow, cleared by 2-4
  self-selected members with siege-style roles (tank in front takes the nearest-champion hits, ranged
  behind, the hurt step out). It harvests the untapped expensive gems and keeps champions together.
- Hunt op: an enemy engaging one of ours (or alone near us) draws nearby healthy allies that can arrive in
  time. It turns 1v1 contacts into 2v1s.
Comms v2: drop the bag slot and the camp slot's second sighting; add the op record.

## Results, round 1 (2026-10-30 ~11:40)

- v1 = comms v2 (op record; bag slot and second sighting dropped) + hunt op (a704d73e..439a047c):
  **48.6% of 9356** (47.6-49.6), dev suites, unlimited fuel. Hunts were rare (the call needs visible
  superiority; typical lone contacts are 1v1 with the nearest ally ~12 away). The loss is probably comms v2
  itself (less enemy sighting data), not the hunts; untested alone.
- Burst op (73ab9a55): smoke 45.6% of 652 (ladder+gen); solo farm speed 2% slower. Calls mostly end
  "unmanned": joiners' momentary solo values are 2-50x their burst share. When crews form they do clear
  Golems with tank rotation. Same failure family as eris's bursts and duos.
- Reading: the farm compares jobs by rate with a horizon penalty, which prefers short cheap jobs; removing the
  horizon lost 45% before (long cycles really are riskier), so I will not fight the valuation head-on.

## Trip economy (from the mirror replays)

- Recalls ~11 per champion-game. Healthy (80%+) champions with no bag recalling and shopping: ~2.8 per
  champion-game; with mid health ~1.4 more. ~30 rounds each => ~12% of champion time on shopping trips.
- Bag recalls (recall home then walk to an altar) are a median 6 (healthy) to 15 (hurt) steps slower than
  walking straight to the nearest altar (BFS on the map).
- Camp damage: 85% ends in our capture, 11% in an enemy capture, 4% never; 17.6% is taken while not attacking
  camps (walking or holding inside awake reach). Narrated solo games show passing hits waking a group and the
  champion then holding a cluster inside its reach (split: 420 hp for 20 gold).
- Probes: E1 no shopping-only trips (wants_shop never true, Prism's capture recall without the shop term);
  E2 bank by walking (no recall_to_bank / capture_recall banking, farm prices the walk).

## Results, round 2 (2026-10-30 ~13:40), all dev suites (9356 games) vs ef8f0b8, unlimited fuel

| Variant | Win % | 95% CI | Note |
|---|---|---|---|
| comms v2 alone (a704d73e) | 50.1 | 49.1-51.1 | free; the hunt costs ~1.5 |
| E1 no shopping-only trips | 47.3 | 46.3-48.3 | shop trips pay |
| E2 bank by walking, no recall | **36.6** | 35.7-37.6 | recalls 30.6 vs 49.5 a team-game, gold -7%, collected -6.5%, submitted -12.6%, deaths 4.6 vs 4.2 |
| buddy cohesion (support factor in farm value + retreat toward support) | 49.4 | 48.4-50.5 | solo neutral |
| rfarm: recall out to farm (hermes port, HomeTrip-priced) | 50.7 | 49.7-51.7 | solo neutral |
| hold-recall on rfarm (heal/shop recall timed to payout) | not run | | fires ~0.4 a game (only gem-less holds qualify) |

- E2's solo check: +2.4% slower to 1000 and -4% gold, against -13 points in the A/B. In real games the walking
  carriers lose much more than in solo: they meet enemies and yield (pack-zone retreats, detours). So the
  time lost to yielding is a big hidden cost, and solo screens understate anything that changes exposure.
- Other agents' A/B summaries on this box (names only, code not read) show pack/retreat variants at 55-58%,
  which points the same way. Probing the retreat triggers on rfarm: Y1 pack zone only when hurt/carrying (not for
  healthy champions on own ground), Y2 healthy champions never "pursued" in want_home's stand, Y3 recall line
  0.35 -> 0.25.

## Round 3 (2026-10-30 ~14:20)

Interim (~7.6k of 9356 games): Y1 52.5%, Y2 50.4%, Y3 52.3% (each includes rfarm, 50.7).
Y1's games (ladder+gen, 620): collected gems 946 vs 920 (+2.8%), submitted +4.3%, recalls 60 vs 50 a team-game,
deaths 4.6 vs 4.5, gems lost at death 53 vs 58. The gain is farm time not given up, not fights.
Debug traces (3 mirror games): 65% of retreat-branch turns had no champion damage to the retreater within
-3..+5 rounds; 29% were by champions at 60%+ health. Most retreats are precautionary.

Building on it:
- C1 = rfarm + Y1 + Y3 + buddy cohesion (staying put makes having an ally near matter more).
- C2 = C1 + hurt_health_fraction 0.5 -> 0.4 and brake_bag 11 -> 20 (carriers and the hurt yield later).
- D1 = C1 + an enemy-aware low line: the low-health retreat at 0.25 only with an enemy near (visible within
  12, last seen within 12 + age in the last 8 rounds, or a tracked possible area within 8); otherwise 0.10.
  Camps are already covered by camp_trapped, so the low line only guards against champions.

## Round 3 results (2026-10-30 ~14:50)

- Final: Y1 52.5% (51.5-53.5), Y2 50.4%, Y3 52.1% of 9356.
- Interim: C1 54.4% (6500 games), C2 54.0%. D1 (low line 0.10 with no enemy near) 51.2% at 3.7k: worse than C1, so
  stopped. Health below ~25% is a real risk even with no enemy seen: unseen enemies arrive, camps keep hitting.
- D2 = D1 + comms v2 + hunt op with calls widened to unseen allies believed near: 46.4% at 2.2k, stopped.
  The hunt has now lost twice (-1.5, then about -5 with more calls). Converging allies on contacts pulls them off
  farming into fights we don't need; in the mirror, fights come to you anyway.
- Pattern so far: what wins keeps champions productive (not yielding home ground, staying out longer, recall as
  travel); what loses pulls them toward fights or off farming (hunts, bursts, duos). Next probes on C1:
  P1 home_power 1, P2 max_wait 10, P3 chain_bag_limit 90, P4 no chase walks (4236-game subset each).

## Round 4 (2026-10-30 ~15:25)

- C1 dev final: 54.1% (53.1-55.2). Committed d8821f97 (bots/astraeus = C1).
- C1 games (ladder+gen): collected 962 vs 937, gold 5228 vs 5110, recalls 56 vs 48 a team-game; deaths
  5.3 vs 4.5 (own side 2.49 vs 1.84, healthy 8 rounds before 2.83 vs 2.22, camp deaths 0.78 vs 0.56).
  It wins by farm time, and pays some of it back in deaths on its own ground.
- Probes on C1 (subset, C1 = 53.4%): P1 home_power 1 54.4% (full dev 54.0%: no gain); P3 chain 90 ~53.0;
  P5 recall 0.20 ~53.5; P6 wider prey ~50.4; P4 no chase ~46.9; P2 wait 10 ~51.8.
- Q1 (healthy home pack zone back, radius = each member's strike reach + 1 instead of 7): 52.9% subset, level.
- D3 (low line 0.35 with an enemy near, 0.25 otherwise; farm pricing at 0.25): running on dev.
- Final checks started for C1: held-out fresh-6075..6082 at unlimited fuel and at default fuel.

## Final (2026-10-30 ~16:05)

- C1 held out (fresh-6075..6082, unlimited fuel): 53.8% of 4096 (52.3-55.4); default fuel 53.3% (51.7-54.8),
  out-of-fuel turns 12,438 vs 10,265 (rfarm turns the Chebyshev prunes off while a recall could win; the loop
  does more work).
- D3 (low line 0.35 near enemies / 0.25 otherwise) ~52.6% at 3.3k: stopped. R2 (recall-to-bank up to bag/8
  rounds slower than walking, uncapped HomeTrip arrival) ~35.3% at 1.5k: stopped. With E2 (no recall banking,
  36.6%) the recall-or-walk banking choice is a sharp optimum at the existing exact comparison.
- Final: C1 on macro-2 (d8821f97). Target 60% not reached.

## Open ideas

- The extra deaths C1 pays on its own ground (healthy, 8 rounds before death): a smarter yield that keeps the farm
  time (Q1's reach-based zone was level; maybe the stand sim with arriving allies, or yield only when a pack is
  walking toward us).
- Chasing is worth ~7 points (P4); loosening prey lost. Better prey choice (who to chase) is likely high leverage.
- Coordination toward fights lost every time here; coordination that saves farm time (who holds a capture, who
  banks, joint clears where solo values are honest long-run rates) is still untested properly: the burst op
  failed on a valuation mismatch (instant solo rate vs long-run rate), not on execution.
- rfarm's fuel: restore exact prunes with a via-spawn lower bound before any ladder use.
