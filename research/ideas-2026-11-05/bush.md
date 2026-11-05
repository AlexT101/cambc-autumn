# Idea C: object permanence and bush play (id `bush`, seeds 512000-512999)

Dev copy: `bots/variants/oc-bush-dev` (from oc-base1). Knobs: `params::bush::`.

## Evidence

Ladder sample: every ranked game captured on big-arm from 2026-11-04 23:00 to 2026-11-05 03:00, post balance patch
(1025 games, top ~25 teams; `replays/bush-ladder/`). Self-play sample: 512 games of astraeus-294 against a comms
variant (`replays/batch-20261102-204716-ab-comms-meas-*`). Scripts: the scratchpad's `bush/*.py` (vanish, matched,
follow, ambush, ambush_team, wards, trade, reveal). Vision is the replay's own `sees` (turn start, champion and ward).

**Vanishes are rare.** An engaged enemy (damage either way in the last 2 rounds, a pursuer within 6) leaves the
whole team's sight about 18.7k times in 1025 games. 7.0k of those end in a bush: ~3.4 per team per game, 2.4 with
the pursuer within 3. The vanisher stays in that cluster 2.4 rounds on average.

**Hiding works against ladder bots, through sight more than through lost tracking.** Matched on pursuer distance
before and after the step and on the retreater's health, kills within 4 rounds:

| retreater's health | hidden in bush | visible in the open | visible in a bush | hidden in the open |
|---|---|---|---|---|
| < 25% | 13.2% | 27.8% | 24.2% | 17.4% |
| 25-50% | 4.1% | 9.1% | 7.1% | 4.2% |

But pursuers do not visibly lose track. Their distance to the hider 1-2 rounds later is only 0.1-0.3 tiles more
than to a visible retreater at the same start distance, and the in-range share is the same within a few points.
Ladder bots keep walking the same way. The gain is that a unit attack needs sight (and a ranged walk spends the
attack).

**Attacking from a hidden bush trades far better.** Ranged pokes (distance 2+) at a champion, and what the shooter
takes over the next 2 rounds:

| shooter's tile | ladder: hit back | ladder: damage taken | self-play: hit back | self-play: damage taken |
|---|---|---|---|---|
| open | 27.9% | 84.7 | 25.5% | 63.9 |
| bush, seen | 25.7% | 71.4 | 21.9% | 52.7 |
| bush, hidden | 9.7% | 23.7 | 14.9% | 40.5 |

So ladder bots answer a hidden shooter about a third as often as a visible one. Our lineage answers it better, so
self-play understates any gain here. About 4.6% of all ladder champion damage comes from shooters hidden in bushes
(self-play: ~4%), spread over every team (3-9% of each team's damage dealt, 2-8% taken). It is ordinary play, not
one team's trick.

**Ladder bots ward bushes heavily.** There are 8.7 wards on the map on average, 43% of them in bushes, each
replaced every ~28 rounds (ours: 33). A champion standing in a bush within 5 of an enemy shares that cluster with
an enemy ward 62.5% of the time (28% away from enemies). Safety's rule that an unseen bush tile counts as seen when
we have not seen the enemy's ward is therefore about right on the ladder, and is not the bug it first looks like.

**Reveal-ward chances.** An engaged enemy (damage either way in the last 2 rounds) can sit unseen in a bush within
4 of us, in a cluster with a tile within ward range 2 that is not our own. Per team per game, that happens in 5.2
champion-rounds on the ladder and 4.1 in self-play. In 70-75% of them the hidden enemy had hit us that round or the
round before. Our ward was ready in only 36-42% of them.

## What ocean already does (and so what is left)

- `possible` sets give full object permanence. Safety's Reach models each visible enemy's walk or dash and its
  sight from where it lands (bush tiles are seen only from their own cluster or a ward). So Safety already credits
  bush cover, exactly inside our own cluster, and pessimistically for clusters we are outside: there an unknown
  enemy ward is assumed to see the tile. retreat_step and the strike search read those tallies, so "flee to bushes"
  is largely in place where it is real.
- Enemy wards count only while in sight this round (`Wards::refresh`): one seen last round is forgotten.
- Wards go down at turn end (bush ward) or at turn start (only the draft's planned ward). Nothing wards in order to
  reveal an enemy for this turn's strikes.
- There is no inference from being hit by an unseen enemy.

## Design (knobs, all off = oc-base1 byte-identical)

- **K1 `reveal_ward` (C2, C6, C1's prior).** At turn start, before the strike search, with the ward ready, one ward
  goes into an unseen bush cluster (not our own) with a tile within 2. The cluster must hold a credible part of an
  unseen tracked enemy's `possible`, near us: at least `reveal_mass` of it, within that enemy's one-turn reach + 1
  of us. The enemy must also be lost prey (engaged last turn) or (mode 2) a threat. Clusters are scored by the
  `possible` mass they hold, doubled for an enemy last seen in or beside the cluster (C1's vanish prior). Then
  `see_again`, so the strikes, chase and Safety see what it reveals the same turn (wards.vision). Fuel: a few
  bitboard ANDs and counts per candidate when the ward is ready and an unseen enemy is near (~0.3-2k); nothing
  otherwise. `see_again` only on a placement.
- **K2 `blind` (C4, C5: the enemy has no object permanence).** In `Reach::at(p)`, for a bush tile p that the enemy
  cannot see now (it stands outside p's cluster, and neither its known ward nor the unknown-ward rule sees p), the
  sight ways' damage (walk or dash in, then attack) is scaled by `blind`. 1 is off, 0 means it never walks in on a
  hunch. This makes standing and shooting from inside a bush, and retreating within one, cheaper in Safety. It is
  an exploit: the panel judges it.
- **K3 `chase_share` (C3).** `lost_prey` keeps prey while at least this share of its `possible` lies in our sight
  square (now 1.0), and chase then walks to the part inside. Fuel: one count.
- **K4 `ward_memory` (C4 support).** An enemy ward seen in the last N rounds still counts as that enemy's ward, so
  its vision is exact rather than the unknown-ward pessimism. Wards last ~28 rounds on the ladder.

## Grid and order

1. Screen each knob alone against oc-base1 (`--sprt 0.50,0.51`, ladder-mix suites from 512000 on, own drafts,
   real fuel): reveal_ward {1, 2} with reveal_mass 0.25; blind {0.5, 0}; chase_share {0.5}; ward_memory {10, 25}.
2. Sweep the constants of anything level or better (reveal_mass {0.1, 0.25, 0.5}, the prior, blind {0.25, 0.75},
   ward_memory). Sweep before cutting.
3. Full factorial over the confirmed winners (at most 4 knobs), confirm at 20k+ games on unused seeds plus
   `--mix varied`, then the PANEL.md panel.

## Expected gain

- reveal_ward: 1.5-2 events per team per game, each a hidden attacker made hittable this turn. Perhaps +0.5 to
  +1.5 points, on maps with bush clusters near fights and camps (most ladder maps, e.g. 04sunburst's altar ring and
  side clusters).
- blind: unclear in self-play, since our lineage punishes hidden shooters more than ladder bots do. Positive
  against the ladder if the hit-back gap is causal. It risks losing to panel members with object permanence.
- chase_share and ward_memory: small, under 0.5.

## Results

All rows are in EXPERIMENTS.md, "Idea C: object permanence and bush play (ocean, 2026-11-05)". So far:
- Every knob alone is level against oc-base1 (49.7-50.6 on 7-10k games): reveal_ward 1/2 (with reveal_mass 0.1-0.25,
  reveal_reserve 8), blind 0/0.5, chase_share 0.5, ward_memory 5/10/15/25, farm_bush 1/2.
- reveal_ward works mechanically (a hit after the ward in the same turn: 0.43 a game against 0.06) but is rare, and
  mode 2 cost +6-7% out-of-fuel turns. Turn-start cluster growth is now capped at 15k a turn (the `c` variants).
- At 10M fuel rw2c reads 51.1 (50.1-52.0); at the real budget every mode-2 variant is 50.2-50.6 with +5-6% OOF. A
  trace put the leftover cost in the per-enemy loop that runs every turn (~140 fuel, +0.25% over identical games),
  even after the cooldown gate (`d`) and a static reach bound (`e`). Mode 3 runs the loop only after a fight last
  turn or a health loss since our last turn (+0.09%, +1.6-2.0% OOF) and is still level: 50.4 on s1, 50.2 on s2
  (pooled 50.3 of 20,480, 49.6-51.0). reveal_ward is cut after sweeping modes 1-3, reveal_mass 0.05-0.25 and
  reveal_reserve 8.
- Outcome: no confirmed winner. Every knob is cut after its sweep; blind 0 is neutral on the panel too.
- farm_bush leans negative on the bushiest maps (48.8-49.3 ±1.3 at bush density >= 4%): cut.
- ward_memory is level at every setting: cut.
- Added during the run: `reveal_reserve` (keep the turn-end bush ward back near enemies) and `farm_bush` (idea 3's
  positioning: farm a camp from a bush stand).
- Why so little: ocean already has object permanence and a sight-exact Safety. Hidden-bush killing blows are 3.5% of
  kills in self-play (6.7% on the ladder), so the whole area is a small slice of the game.
