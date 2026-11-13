# s1: does charybdis's farm choice predict what it gets?

A measurement study with no bot change kept. `bots/variants/s1-trace` is chy-ref plus debug-only `FC` lines
([fc-trace.patch](fc-trace.patch)). Its release code matches chy-ref's: the same function sizes, and one body with
two exception blocks swapped in order. The lines were played in a debug mirror against chy-ref on
`maps/suites/mac13/study` (2,048 games, 50.0%, 0 failures, fuel 200k), then matched to the replays. The replays are
deleted. The per-choice rows (514k, 251 per team-game) are kept in `replays/mac13-kronos-s1-choices.jsonl.gz`.

- `fc_outcomes.py BATCH`: reads the FC lines from the replay zips' stdout, plus the extracted events and positions,
  and writes one row per choice.
- `report.py [rows]`: writes [tables.md](tables.md), every table below and more.
- `clear_help.py [rows]`: measures how much of a solo clear other champions dealt.

**Definitions.** An FC line is printed in `farm_turn` where `memory.farm_group = best` commits a choice. It is
printed for a new group, a new mode, farm resuming after rounds away, or the group going to respawning. It gives
the priced value `v`, the numerator `w` and the rounds `R` with their parts: trip `t` (bank detour `bk` and respawn
wait included), clear `c`, hold `k` and heal trips `H`. It also gives the part `p`, the weight `x` (home side ×
exposure × stickiness × plan), `per_gold` and the top two other evaluated groups (lower bounds, because of the
prunes).

A *choice* is a run of lines on one group. It ends at one of these:
- the group's first payout: ours (we got a share), ally or enemy;
- the champion's death;
- a line on another group (switched);
- the game end.

Priced numbers:
- "gem rate priced" = Σ p·gems / Σ (R − bk − H).
- "real" = Σ our share gems / Σ rounds from the choice to its end. It is taken over all choices, failures included.
- "team-attr" credits p × the team's payout of the group, in the choice or within 8 rounds after it (a crew member
  leaving a cleared group to its claimer).

Gems, not value units, are the main unit: Vesper's `per_gold` reaches 47 under the gold-farmer weight. The `tg`
unit is per traced team-game.

## Findings

1. **Completion is not priced, and it is the largest error.** Only 22% of priced choices pay the chooser
   (54.7/tg, 892 gems/tg, about 90% of the team's collected gems). 70% are switched away. On average a choice
   realises 0.43-0.63 of its priced gem rate (0.9-1.1 team-attributed). The ranking holds: realised rate rises
   with every priced-value decile (0.010 to 0.677 gems/round). But the bottom half realises only 7-35% of its
   price, because 7-17% of those choices are paid.

   Champion time per team-game:
   - 2,006 rounds/tg (53% of choice time) go to choices later abandoned, against 1,271 to paid ones.
   - 109 switches/tg come before arrival, with nothing happening to the group (pure re-pricing). They cost 1,001
     rounds/tg, median 5 rounds each.
   - 23 flip-flops/tg (A, then B, then back to A within 20 rounds) cost 213 rounds/tg.
   - At most 1,509 of the 2,006 rounds were not spent closing on the next choice.

   The switch rate is ~70% whatever the chosen value's margin over the runner-up (<1.05x or >2x alike). So the
   stickiness 1.2 (`farm.cc:9`, applied at `farm.cc:1832`) is not what fails: the prices move turn to turn.
   The rate is `rate()` in `camps.cc:183` (worth / (rounds·(1 + rounds/horizon))), with no term for P(paid).

2. **The side weight points the wrong way in the middle band.** Bucketed by d_us/(d_us + d_them):

   | side fraction | 0.2 | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 | 0.8 |
   |---|---|---|---|---|---|---|---|
   | choices/tg | 32 | 37 | 48 | 68 | 25 | 10 | 5 |
   | mean weight x | 1.04 | 1.12 | 1.30 | 1.31 | 1.03 | 0.67 | 0.38 |
   | paid % | 30 | 29 | 24 | 16 | 9 | 4 | 2 |
   | enemy took it % | 0 | 0 | 2 | 8 | 12 | 13 | 12 |
   | real/priced gem rate | 0.78 | 0.75 | 0.65 | 0.44 | 0.34 | 0.25 | 0.12 |

   The middle band carries the highest weight (`mid_exposure` 1.36, `params.h:204`, via `exposure_of`
   `farm.cc:1296`) and yields 0.44 of its unweighted price. Weighted, it is overpriced about 2.2x relative to own
   ground. Enemy-side groups get `home_ground` (`camps.cc:665`, `home_power` 1.89), which is too gentle:
   - Enemy side: 54.7 choices/tg, 9% paid, 552 rounds/tg sunk for 83 gems/tg (0.15 gems a round).
   - Own side: 28% paid, 648 gems/tg over 1,475 rounds sunk.

   The weight may be meant partly as denial, which this study does not measure.

3. **Solo pricing ignores help, and help takes the capture.** 23.2/tg solo (S/K) choices on live groups were
   cleared by the team after our arrival (`clear_help.py`):

   | | choices/tg | others' share of the damage | clear priced | clear real | paid |
   |---|---|---|---|---|---|
   | alone | 14.5 | 0 | 10.0 | 8.4 | 93% |
   | helped | 8.7 | 58% | 25.3 | 10.3 | 43% |

   The solo clear (`min_camp_damage`, `farm.cc:2107`; value `farm.cc:2177`) prices our output alone. Both the
   faster clear and the lost share are left out. Kite clears (K, `spell_clear_rounds`, `farm.cc:2108`/`2169`) are
   priced at 23.4 rounds against 7.9 real (1.6/tg).

4. **The crew modes price a different thing from what they get.**
   - **Joining (J), 84/tg:** priced at the damage part (`part = strength·rounds/health`, `farm.cc:2071`) and with
     almost no hold (`hold = carry ? cap_rounds : 0`, value `farm.cc:2091`). Only 18% are paid. Those take 21 gems
     against 10 priced, because the split goes by holders, and hold 6.2 rounds against 1.5 priced. The personal
     real/priced is 0.63 and the team-attributed 1.08. It is calibrated for the team, not for the champion's time.
   - **Proposing (C), 11.6/tg:** 5% paid and 88% switched. The real/priced is 0.28 (team-attributed 0.74).
   - **Monolith:** 2.7/tg, priced at 1.43 gems/round and realised at 0.47, with 79% switched.

5. **Walk and hold carry small, opposite biases. Distance and phase compound finding 1.** On paid solo choices the
   priced total is 30.0 rounds against 25.4 real (median ratio 0.83).
   - The walk is priced to the group centre (`farm.cc:1893`). That overstates the walk to attack range by 3.3
     rounds (melee) and 3.9 (ranged); at 0-5 steps it is 3.5 priced against 1.1 real.
   - The hold, `capture_rounds` (`capture.cc:9`, capture_time + 1), is short by 1.3 rounds (5.4 against 6.6).
   - By priced steps from 0-5 to 36+: paid falls from 41% to 10%, real/priced from 0.65 to 0.47 and
     team-attributed from 1.09 to 0.78.
   - Late in the game (round 1001+) real/priced is 0.43, against 0.53-0.67 earlier.

6. **Prism is the one champion whose price holds, and Willow and Cassi/Issac are the furthest off.**

   | champion | choices/tg | paid | real/priced (team-attributed) | rounds sunk/tg |
   |---|---|---|---|---|
   | Prism | 36 | 40% | 1.09 (1.28) | |
   | Willow | 27 | 2% | 0.04 (0.58) | 419 |
   | Cassi | 44 | 13% | 0.33 (~1.0) | 503 |
   | Issac | 47 | 14% | 0.40 (~1.0) | 473 |

   Prism's carry modes G/L/Q are priced at about 1.0 (+385 gems/tg). Willow's farm choices are almost never hers.
   Cassi and Issac's are paid to the team.

## Caveats

- Most choices end in a switch, so "real" mixes the price error with the choice not being pursued. The
  parts tables (walk, clear, hold) use paid choices only, which favours fast ones.
- Arrival means within attack range of a camp tile (on a tile for a cleared group). Progress towards the next
  choice uses Chebyshev distance, so the abandoned-walk waste is an upper bound.
- The farm commits choices in branches this trace does not see (`pick_up` and others). A choice spanning a
  bank, fight or shop counts that time against it.
- Mirror only: chy-ref against itself, on the study suite.

## Tables

The main ones are below; [tables.md](tables.md) has all of them (by champion, by phase, by state, the parts, and
solo and crew by group type).

| mode | choices/tg | paid % | switched % | priced R (med) | real rounds paid (med) | gem rate priced | real | real/priced | team-attr | rounds sunk/tg |
|---|---|---|---|---|---|---|---|---|---|---|
| solo S | 127.4 | 24 | 64 | 37 | 22 | 0.369 | 0.193 | 0.52 | 0.93 | 1264 |
| solo-kite K | 11.5 | 19 | 72 | 59 | 24 | 0.237 | 0.222 | 0.94 | 1.39 | 111 |
| crew-join J | 84.0 | 18 | 72 | 22 | 20 | 0.404 | 0.255 | 0.63 | 1.08 | 908 |
| crew-propose C | 11.6 | 5 | 88 | 52 | 34 | 0.417 | 0.118 | 0.28 | 0.74 | 151 |
| Prism G/L/Q | 4.8 | 52-93 | 6-46 | 5-12 | 5-11 | | | 0.87-1.21 | | 8 |

| group | choices/tg | paid % | real/priced | team-attr | rounds sunk/tg | gems/tg |
|---|---|---|---|---|---|---|
| cluster | 77.1 | 29 | 0.52 | 0.81 | 642 | 227 |
| wolf | 100.7 | 20 | 0.70 | 1.24 | 1018 | 255 |
| elk | 52.7 | 17 | 0.67 | 1.16 | 648 | 286 |
| golem | 6.9 | 14 | 0.63 | 1.02 | 93 | 58 |
| monolith | 2.7 | 5 | 0.32 | 0.99 | 41 | 23 |

| outcome (all choices) | choices/tg | rounds/tg | % of time | median rounds |
|---|---|---|---|---|
| ours | 54.7 | 1271 | 33 | 20 |
| ally | 6.7 | 152 | 4 | 18 |
| enemy | 11.4 | 181 | 5 | 10 |
| switched | 170.3 | 2006 | 53 | 8 |
| died | 4.9 | 100 | 3 | 14 |
| game end | 3.0 | 92 | 2 | 15 |
