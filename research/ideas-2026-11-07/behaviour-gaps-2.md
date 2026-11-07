# Behaviour gaps, round 2: gem flow, camps, fights, draft and altars (ocean, 2026-11-07)

Round 1 ([behaviour-gaps.md](behaviour-gaps.md)) measured each champion type; this round measures the team: how gems
move, which camps are taken and how, how fights start and end, the draft, and altar locks. Same data and the same
true-version mapping: 18,599 distinct ladder games, our side all v82 (4,466 sides; the 11-06 21:00 to 11-07 14:39
capture), Fish 3,450, Mite 4,328, top (17 teams rated 2290+) 17,654. v82 predates CHANGES 457/458 (Willow follows,
min_bank 25), so the gem-a-tribute and first-tribute gaps below are partly closed in oc-base19.

## Method

- `features2.py` (per game, side and phase: ≤250, 251-700, 701+) and `events2.py` (per capture, engagement, gem
  recall and lock) in `/home/ubuntu/tmp-offload/gaps2/bin/`; tables `rep2.txt` (every measure by phase),
  `rank2.txt` (the candidate gaps), `dive.txt`, `dive2.txt`, `draft2.txt`.
- **Engagement**: champion damage between the teams, split by 8 quiet rounds. Its initiator dealt the first damage;
  numbers and health are counted within 8 tiles of the first hit.
- **Gap** d = (ours − Fish) / pooled SD. **Association** z: logit of the win on the standardised measure, the
  tributed lead at the window's start and the rating gap; signed so z > 0 means moving our value toward Fish's goes
  with winning. `z ours` fits our games, `z pool` Fish, Mite and top together. Associations, not effects.

## Findings

Ranked by |d|, behaviours only (kill counts and engagement outcomes are results, listed after):

| measure | ours | Fish | Mite | top | d | z ours | z pool |
|---|---|---|---|---|---|---|---|
| idle allies within 5 at Elk/Golem payouts (≤700) | 0.89 | 1.52 | 1.00 | 0.99 | −1.03 | −1.8 | −0.4 |
| share of the game's Monolith captures (Monolith maps, 600+ rounds) | 0.57 | 0.90 | 0.65 | 0.50 | −0.88 | +9.3 | +32.9 |
| idle allies within 5 at any payout (≤700) | 0.70 | 1.10 | 0.72 | 0.70 | −0.85 | +1.5 | +3.8 |
| locks placed by round 250 | 1.53 | 0.81 | 0.00 | 0.27 | +0.71 | −3.5 | −3.0 |
| Monolith captures a game (Monolith maps, 600+ rounds) | 0.63 | 1.27 | 0.56 | 0.57 | −0.56 | +2.7 | +24.0 |
| share of engagements we start (≤700) | 0.62 | 0.51 | 0.48 | 0.50 | +0.54 | −7.4 | −20.4 |
| locks a game | 4.54 | 2.90 | 0.10 | 1.81 | +0.49 | +10.3 | −2.9 |
| Elk/Golem share of captures (≤250) | 0.19 | 0.29 | 0.20 | 0.19 | −0.44 | +0.6 | +7.2 |
| gem recalls followed by a capture, not a tribute | 0.38 | 0.44 | 0.39 | 0.43 | −0.31 | +2.4 | +3.4 |
| gem-cluster share of captures (≤250) | 0.22 | 0.14 | 0.18 | 0.18 | +0.28 | −5.9 | +2.9 |
| gold-cluster captures per 100 rounds (701+) | 1.72 | 0.83 | 1.15 | 0.98 | +0.24 | −3.2 | −4.0 |
| teleports per 100 team rounds (251-700) | 0.06 | 0.33 | 0.65 | 0.43 | −0.33 | −3.9 | +5.7 |

**1. Monoliths are Fish's.** 40 of the 128 ladder maps have a Monolith (38 of them with other gems too). In games of
600-1000 rounds on them Fish takes one in 75% of games (1.18 a game), we in 26% (0.52), Mite 24%, top 28%. Fish
takes 90% of its games' Monolith captures, we 57%. When we take fewer than the opponent we win 46% (241 sides),
more 94% (286). How Fish does it differs from how we do (`mono3.py`, 719 of our Monolith captures, 1,364 of Fish's):

| | median clear (rounds) | bodies dealing damage | damage taken by the team | own share of the damage |
|---|---|---|---|---|
| ours | 49 | 4-6 (mode 4) | 7.9k | 0.93 |
| Fish | 114 | 2-4 (mode 4, 30% two or three) | 13.6k | 0.98 |
| Mite | 55 | 5-6 | 6.8k | 0.93 |
| top | 76 | 2-4 | 9.8k | 0.93 |

Fish grinds a Monolith slowly with part of the team (Vesper Vale, Vendetta, Heart of Ruin, Marcella) and keeps
farming with the rest; nobody steals it (2% of its captures had less than half of their damage from Fish).

**2. Fish escorts its captures.** At a payout Fish has 1.1 idle allies within 5 tiles (ours 0.70, Mite and top
0.70-0.72); at Elk and Golem 1.5 (ours 0.9). The escorts are Cassi (0.32 a capture), Issac (0.29), Heart of Ruin
(0.25) and Willow (0.20). Fish takes more Elk and Golem early (29% of captures ≤250 against our 19%) and half our
gem clusters (2.6 a game ≤250 against 5.0). Captures are still held by one champion (1.09 holders against 1.05).

**3. Round 1's loser, early spacing, explained.** Fish's pack forms at camps, not on the move: its allies come to
the camp being cleared and wait out the capture beside it. It pays for it: its capture gems ≤250 are 85 per 100
rounds against our 94 (−9%), and Mite and top, which space like us, farm 85 and 66. Round 1's `fu250` made bodies
walk to each other instead, and early camp gems fell by a third to a half. A pack arm has to come from the camp
choice (several bodies on the bigger camps), not from following.

**4. We lock early and often.** 4.5 locks a game (1.5 by round 250) against Fish's 2.9 (0.8), top's 1.8 (0.3),
Mite's 0.1. Two thirds are destroyed either way, after a median 65 rounds; 7-8% cancel a tribute. ocean places a
carried lock on any altar on its own side it passes (bank.cc place_lock). The associations point the other way
(z −3.5 early, pool −3.0): no arm.

**5. Fights.** We start 62% of engagements (Fish 51%, top 50%), 61% of them with a spell (Fish 52%). Fish's edge is
not selection: at every number advantage at the start, from −2 to +2, its initiations net +0.8 to +1.0 kills
(ours +0.4 to +0.56) and the engagements started on it +0.24 to +0.43 (ours −0.07 to +0.12). Our own outcome does
not depend on the numbers we start at (+0.43 at −2, +0.42 at +2). Focus fire (damage concentration per target, 0.64
to 0.74) and the health at which a body disengages (0.65-0.70) are level. Kills per death are the result, not a
knob; starting more goes with winning in every fit. No arm.

**6. Gem flow.** The time a gem sits in a bag (Little's law) is level early (48 rounds against 54) and ours is
longer later (97 against 70, then 135 against 75); the share of gems lost at death after round 700 is 15.6% against
7.8%. Most of both is our Prism, which hoards for Focus (215 gems carried on average after round 700, 11.8 lost per
100 rounds; Fish drafts it in 3% of games). The other types each lose 0.2-1.3 more gems per 100 rounds than
Fish's after round 700 (Marcella 2.9 against 1.6), round 1's late-death gap. Carry-to-tribute walks (12.6 against 11.4 tiles), the rounds from
the last gain to the tribute (21-28), tributes started with an enemy within 8 (33% against 32%) and tribute
cancels (2-7%) are level. Our first tribute came at round 110 against Fish's 159, the min_bank gap that CHANGES 458
closed.

**7. Draft.** Pick rates (share of sides), ours against Fish: Cassi & Issac 95/99, Prism 75/3, Vesper Vale 61/46,
Heart of Ruin 47/93, Willow 46/57, Marcella 41/62, Vendetta 25/83, Ren 19/4. Among the top teams a Prism pick goes
with winning (z +8.0 given the rating gap; ours +0.4), Heart of Ruin and Vesper Vale do not (−3.5, −3.7).

**8. Smaller.** Re-take of a respawned camp (38-70 rounds), clear times and contested captures are level. Late we
take twice Fish's gold clusters (1.7 against 0.8 per 100 rounds) but fewer goes with losing. Every top team
teleports 5-10x as often as we do (pool z +4 to +6), never from spawn and mostly in fights: 66% of Fish's crystals
(Vesper Vale, Vendetta, Heart of Ruin) are followed by a hit on a champion within 40 rounds, ours 37%. A fight
crystal is a combat feature with no single knob; round 1's crystal hop (to altars) lost.

## Arms
