# Carrier punishment: Fish, top teams and ours, from ladder replays (2026-11-08)

How a team P punishes enemy gem carriers C: whether it sees them, hits them, chases them, leaves camps for them, stuns
their tributes, and what a kill is worth. P is the punishing side; every game gives two P sides.

**Headline: Fish is not a carrier hunter.** Its engage rate does not rise with the bag and falls for 200+. It stuns
tributers no more often than anyone else in reach. Big carriers draw it off camps *less* often than small ones. Our v82
already hits, stuns and locks carriers more than Fish does. Fish's edge in kills (12.6 a game against our 10.1) comes from
general fights against small bags, not from carriers. What does trigger engages, for every team, is **numbers and
distance**, and to a lesser degree **low HP**.

## Data and method

- **Games.** 29,367 distinct games (dedupe on game id) from `tmp-offload/willow/analysis`, which is biased to Willow
  comps, and `tmp-offload/gaps/analysis` (11-05: all Fish and Mite games, plus 500 a team for the 2290+ teams; capture
  11-06 21:00 to 11-07 14:39).
  - Ladder means ranked plus unranked. Scrims (our v78-v82 bundles against Fish and Mite) are reported separately.
- **Groups.** Fish, Mite, top (bigbag.py's 14 names), rest, and ours by era from the UUIDv7 time (willow.md's table).
  - Ladder sides: proteus 935, v76/77 174, v82 4,373.
  - v80/v81 ladder have 2 and 31 sides, so they are omitted.
  - v83/v84 were submitted after the data ends.
- **Sighting.** C's id is in some P champion's `sees` at its turn start in round r, with C's bag at the start of r
  (end of r-1) at least X.
  - An episode is consecutive sighting rounds, with gaps of up to 3 allowed.
  - Episodes that start with C within 1 of its own spawn are dropped.
- **Hit.** Any `attack` or `cast` by P with C in `dmg` or `stun`, from the episode start to the outcome (or last
  sighting + 3).
- **Outcome.** The first of these in [start, last sighting + 3]:
  - C's death: killed by P, or by a camp;
  - `tribute_end`;
  - `recall_end`;
  - otherwise "escaped".
- **Numbers** = P champions alive within 8 of C minus C's allies within 8, Chebyshev. d0 = distance to C from the
  nearest P champion that saw it.
- **Caveats.**
  - Counts are correlated rounds, not independent trials.
  - Opponent mixes differ: Fish mostly meets top teams. See the matchup table.
  - A Cassi/Issac partner kill is credited to the killer, with the partner's bag.
  - `manual` tribute cancels are the carrier's own.
- **Scripts** are in `/home/ubuntu/tmp-offload/cpun/bin/`: `rows.py` (rows → `rows.pkl`), `report.py` (→ `report.txt`,
  all tables) and `extra.py` (→ `extra.txt`).

Prior findings (research/fish-2026-11-05):
- TACTICS §2: Fish has no channel-interrupt priority. With a stun ready within 4, it stuns tributers at 18.6%, against
  18.8% for anyone. It lets recallers go more often.
- TACTICS §3 and MICRO §1: unit damage spells target argmax (gems+8)/(HP+shield); basic attacks target min HP+shield and
  ignore gems and channels.
- MICRO: kills are taken whether or not the enemy is in camp fire (84%).
- CONTINUATION: Prism's tribute start follows self + team score + allied tributing ≥ 1000, not a fixed bag.

This study confirms all of these at team level on 10x more games.

## 1. Episodes against carriers (ladder)

Bag ≥ 100. Columns:
- **eps/side**: episodes per P side.
- **hit 5**: hit by P within 5 rounds of the first sighting.
- **atk**: distinct P attackers, mean, when hit.
- **kill**: killed by P; **kill 20**: killed within 20 rounds.

| P | eps/side | hit in ep | hit 5 | hit 5, d0 ≤ 4 | 1st hit (med rounds) | atk | kill | kill 20 | tributed | recalled | escaped | gems/kill |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Fish | 1.27 | 34% | 10% | 48% | 8 | 1.6 | 9% | 5% | 15% | 20% | 55% | 242 |
| Mite | 2.37 | 34% | 10% | 46% | 9 | 1.7 | 7% | 4% | 11% | 20% | 61% | 291 |
| top | 1.84 | 33% | 13% | 49% | 7 | 1.7 | 6% | 3% | 21% | 17% | 55% | 274 |
| rest | 1.63 | 30% | 12% | 47% | 6 | 1.6 | 4% | 3% | 21% | 15% | 59% | 271 |
| us proteus | 1.73 | 37% | 17% | 63% | 5 | 1.7 | 7% | 4% | 17% | 18% | 57% | 258 |
| us v76/77 | 2.41 | 43% | 19% | 53% | 5 | 1.7 | 7% | 5% | 20% | 22% | 50% | 322 |
| **us v82** | 2.35 | 42% | **18%** | 58% | 6 | 1.8 | 9% | 5% | 12% | 18% | 61% | 251 |
| us v82 scrim | 3.36 | 50% | 19% | 61% | 6 | 2.0 | 6% | 4% | 19% | 19% | 55% | 341 |

Kill rate by threshold (hit in 5 in brackets):

| P | 30+ | 50+ | 100+ | 200+ |
|---|---:|---:|---:|---:|
| Fish | 13% (14%) | 12% (13%) | 9% (10%) | 8% (9%) |
| Mite | 8% (13%) | 7% (12%) | 7% (10%) | 6% (9%) |
| top | 7% (14%) | 7% (14%) | 6% (13%) | 5% (11%) |
| us proteus | 8% (16%) | 8% (16%) | 7% (17%) | 7% (18%) |
| us v82 | 10% (18%) | 10% (18%) | 9% (18%) | 7% (15%) |
| Fish scrim (vs us) | 10% (11%) | 9% (10%) | 9% (8%) | 9% (9%) |

- Everyone kills big carriers less often than small ones.
- Fish kills the most per episode at 30-50 bags, but at 100+ it equals v82 (9%).
- At 100+, Fish and Mite hit carriers within 5 rounds the least of all groups (10%).

Matchups, bag ≥ 50, hit / killed by P (n):

| P \ carrier | Fish | Mite | top | us v82 | rest |
|---|---:|---:|---:|---:|---:|
| Fish | | 36% / 9% (1,825) | 37% / 10% (5,636) | 28% / 6% (717) | 36% / 19% (2,591) |
| top | 27% / 3% (7,713) | 33% / 6% (8,873) | 34% / 7% (58,570) | 27% / 4% (7,736) | 39% / 10% (26,886) |
| us v82 | 35% / 5% (851) | 47% / 10% (9,354) | 42% / 11% (5,540) | | 36% / 9% (8,676) |
| us v82 scrim | 40% / 4% (1,455) | 53% / 10% (1,066) | | | |
| Fish scrim | | | | 31% / 8% (1,033) | |

Fish's carriers are the hardest to kill for everyone (top 3%, us 4-5%). Fish's 19% against "rest" is easy prey.

## 2. Gems denied per side-game (ladder)

| P | kills | kills of 100+ bags | gems taken by kills | enemy bags lost to camps | enemy tributed | taken / (taken + enemy tributed) |
|---|---:|---:|---:|---:|---:|---:|
| Fish | 12.6 | 0.12 | 107 | 5 | 411 | 20.6% |
| Mite | 9.2 | 0.18 | 105 | 5 | 584 | 15.3% |
| top | 7.9 | 0.12 | 99 | 5 | 749 | 11.7% |
| rest | 6.6 | 0.08 | 69 | 12 | 796 | 8.0% |
| us proteus | 7.9 | 0.13 | 105 | 6 | 590 | 15.1% |
| us v82 | 10.1 | 0.22 | 137 | 7 | 461 | 23.0% |
| us v82 scrim | 8.0 | 0.21 | 165 | 22 | 702 | 19.0% |

Fish takes fewer gems per game than v82 and kills fewer 100+ carriers (0.12 against 0.22). Its extra kills are on small
bags.

## 3. Chase

P champions that see C at the first sighting, 3 ≤ d0 ≤ 8, not on or fighting a camp. The columns are the change in
distance to C after 1, 3 and 5 rounds; the share that closed 2 or more tiles by round 3; and hits on C within 5 rounds.

| P | bag | n | Δd k=1 | Δd k=3 | Δd k=5 | closed ≥2 by 3 | hit in 5 |
|---|---|---:|---:|---:|---:|---:|---:|
| Fish | 0-9 | 58,062 | -0.47 | -0.40 | +0.04 | 38% | 12% |
| Fish | 10-49 | 12,716 | -0.59 | -0.60 | -0.26 | 41% | 17% |
| Fish | 50-99 | 2,703 | -0.48 | -0.41 | +0.09 | 37% | 17% |
| Fish | 100-199 | 1,029 | -0.31 | -0.19 | +0.40 | 31% | 14% |
| Fish | 200+ | 801 | -0.10 | +0.34 | +0.57 | 22% | 7% |
| top | 30-99 | 65,162 | -0.47 | -0.44 | -0.04 | 40% | 16% |
| top | 200+ | 7,355 | -0.24 | +0.04 | +0.59 | 29% | 10% |
| us v82 | 30-99 | 12,108 | -0.44 | -0.14 | +0.23 | 36% | 20% |
| us v82 | 100-199 | 2,615 | -0.40 | -0.07 | +0.32 | 33% | 21% |
| us v82 | 200+ | 2,298 | -0.15 | +0.17 | +0.62 | 27% | 16% |

- Chases are short for every team: the closing is spent by round 3 and is gone by round 5.
- Fish closes hardest on 10-49 bags and least on 200+, where it opens distance. Huge bags travel with escorts
  (numbers, §6).
- Travel in 5 rounds is 3.0-3.4 tiles for everyone, whatever the bag.

## 4. Leaving camps

The P champion is on a group tile, or hit a camp in the two prior rounds, and sees C within 8 at the first sighting.
"Left" means it is 2 or more from the group within 5 rounds; "toward" means also closer to C than at the start.

| P | 0-9 | 10-29 | 30-49 | 50-99 | 100-199 | 200+ |
|---|---:|---:|---:|---:|---:|---:|
| Fish left / toward | 65 / 39% | 72 / 44% | 72 / 44% | 71 / 44% | 63 / **28%** | 63 / **29%** |
| top | 61 / 36% | 63 / 38% | 63 / 37% | 64 / 38% | 61 / 34% | 67 / 37% |
| us proteus | 66 / 41% | 67 / 41% | 67 / 39% | 64 / 42% | 76 / 40% | 72 / 39% |
| us v82 | 68 / 39% | 73 / 45% | 73 / 45% | 73 / 43% | 75 / 42% | 81 / 43% |

- Fish leaves camps for 10-99 carriers slightly more often than for empty enemies (+5 points). It leaves for 100+
  carriers *less* often.
- v82 already leaves more often than Fish at every bag (81% at 200+). Hits on C from camp are 9-16% for Fish and 14-21%
  for v82.

## 5. Tributes: stuns, locks, kills

Enemy tribute channels seen by P during the channel. The stun column counts stuns by P; all stuns came from P.

| P | bag | n | done | stun | death | lock | carrier cancel / other |
|---|---|---:|---:|---:|---:|---:|---:|
| Fish | all | 21,097 | 89% | 2.0% | 0.6% | 2.7% | 6.3% |
| Fish | 30-99 | 6,724 | 86% | 2.4% | 0.7% | 3.3% | 7.4% |
| Fish | 100+ | 1,521 | 50% | 6.1% | 1.9% | 8.5% | 33.5% |
| Mite | 100+ | 4,310 | 32% | 16.3% | 0.7% | 7.1% | 43.6% |
| top | 100+ | 17,816 | 49% | 17.2% | 1.1% | 6.9% | 25.6% |
| us proteus | 100+ | 676 | 50% | 15.7% | 0.9% | 10.5% | 22.8% |
| us v82 | all | 32,961 | 81% | 5.7% | 0.6% | 4.5% | 8.5% |
| us v82 | 100+ | 4,428 | **33%** | **20.0%** | 1.5% | **18.9%** | 26.1% |

- Big-bag channels are mostly broken by the carrier itself: 494 of Fish's 1,521 100+ cases are `manual` cancels.
- Fish stuns big tributes a third as often as everyone else. v82 stuns and locks the most.

**Stun opportunities.** A P stun champion is alive, unstunned and has its stun ready at the start of the round, and sees
an enemy within 4. The table gives the share of such rounds in which it stunned that enemy.

| P | tributing | tributing, d ≤ 2 | not channelling | not channelling, d ≤ 2 | recalling | tributing 30+ |
|---|---:|---:|---:|---:|---:|---:|
| Fish | 22.7% (1,179) | 43.5% | 22.0% (113,523) | 40.2% | 16.1% | 21.7% |
| Mite | 32.9% (3,498) | 68.1% | 27.0% | 52.8% | 23.8% | 31.4% |
| top | 22.7% (21,230) | 48.7% | 20.0% | 38.5% | 17.6% | 22.7% |
| us v82 | 35.5% (2,874) | 74.0% | 28.6% | 55.1% | 26.4% | 36.2% |

- Fish has no tributer priority overall, which replicates TACTICS: 22.7% against 22.0%.
- That figure is mostly Marcella (713 of Fish's 1,179; her stun needs an adjacent reset basic): 5% tributing against
  10% not.
- Fish's unit stunners do favour tributers, though n is small:

  | Fish stunner | tributing | not channelling |
  |---|---:|---:|
  | Cassi | 85% (79) | 58% |
  | Heart of Ruin | 40% (356) | 23% |
  | Ren | 88% (17) | 28% |

- Ours: Cassi 76% against 35%, Prism 64% against 47%, Ren 67% against 46%.
- Recallers are stunned less than anyone, for every team.

## 6. Engage triggers

All first sightings of an enemy (any bag, d0 ≤ 8). The label is hit by P within 3 rounds. Each cell is d0 ≤ 3 / d0 4-8.

| P | bag 0-9 | 10-29 | 30-49 | 50-99 | 100-199 | 200+ |
|---|---:|---:|---:|---:|---:|---:|
| Fish | 49 / 7% | 57 / 10% | 52 / 9% | 58 / 9% | 53 / 7% | 42 / 5% |
| top | 54 / 9% | 54 / 8% | 52 / 9% | 54 / 10% | 51 / 9% | 46 / 6% |
| us v82 | 56 / 11% | 59 / 13% | 55 / 12% | 57 / 14% | 61 / 14% | 56 / 10% |

| P | C hp < 0.25 | 0.25-0.5 | 0.5-0.75 | 0.75-1 |
|---|---:|---:|---:|---:|
| Fish | 74 / 13% | 57 / 8% | 55 / 8% | 48 / 8% |
| top | 63 / 8% | 57 / 8% | 57 / 9% | 52 / 8% |
| us v82 | 74 / 15% | 64 / 12% | 60 / 12% | 55 / 12% |

| P | numbers ≤ -2 | -1 | 0 | +1 | +2 | ≥ +3 |
|---|---:|---:|---:|---:|---:|---:|
| Fish | 36 / 3% | 39 / 6% | 50 / 8% | 54 / 10% | 54 / 16% | 64 / 25% |
| top | 39 / 4% | 45 / 6% | 51 / 9% | 59 / 12% | 63 / 21% | 69 / 28% |
| us v82 | 45 / 6% | 50 / 10% | 53 / 12% | 61 / 15% | 60 / 24% | 68 / 30% |

Logistic fit, hit in 3 ~ log2(1+bag) + hp frac + numbers + d0 (se in brackets):

| P | n | base | log2(1+bag) | hp frac | numbers | d0 |
|---|---:|---:|---:|---:|---:|---:|
| Fish | 87,778 | 11% | +0.041 (0.005) | -0.30 (0.07) | +0.227 (0.008) | -0.631 |
| Mite | 128,649 | 12% | -0.040 (0.004) | +0.05 (0.05) | +0.283 (0.007) | -0.629 |
| top | 652,010 | 12% | -0.012 (0.002) | +0.10 (0.03) | +0.282 (0.003) | -0.637 |
| us v82 | 134,663 | 15% | +0.017 (0.003) | +0.05 (0.05) | +0.190 (0.006) | -0.591 |

- **Bag is not a trigger** for anyone. Fish's +0.04 a doubling is +0.3 logit from 0 to 200 gems, against +0.23 for one
  extra champion.
- **The trigger is numbers.** At d0 4-8, Fish's hit rate doubles at each step (≤0 → +1 → +2 → +3: 5% → 10% → 16% → 25%).
  - Bag × numbers at d0 4-8 (extra.txt): Fish 100+ carriers are hit at 4% / 7% / 13% for numbers ≤0 / +1 / ≥+2.
  - v82 is at 9% / 12% / 29%.
- **Fish alone has a real low-HP term.** It hits a < 25% HP enemy at d0 ≤ 3 74% of the time, against 48% at full HP,
  consistent with its kill-first rules. We already match it (74%).
- No sharp threshold anywhere: every curve is smooth in numbers and distance.

Kill within 10 rounds of first sighting (d0 ≤ 8): Fish 10% / 8% / 5% / 5% / 3% / 2% across the six bag buckets; v82
7% / 6% / 5% / 4% / 3% / 2%. Fish's kill edge is entirely on bags under 30.

## 7. Win impact (100+ carriers)

| P | killed by P: n, P win | tributed: n, P win | escaped/recalled: n, P win |
|---|---|---|---|
| Fish | 397, 83% | 652, 38% | 3,236, 54% |
| Mite | 739, 84% | 1,133, 28% | 8,301, 42% |
| top | 2,220, 66% | 7,585, 20% | 25,849, 27% |
| us proteus | 114, 79% | 282, 29% | 1,218, 50% |
| us v82 | 884, 82% | 1,275, 38% | 8,077, 60% |

- A 100+ kill against a 100+ tribute is worth about +45 points of P's win rate for every team. This is correlational:
  the stronger side is the one that gets the kill.
- In games with a sighted 100+ carrier, the first such episode ends in a P kill 11% of the time for Fish and 8% for v82.

## Arms

(to be filled)
