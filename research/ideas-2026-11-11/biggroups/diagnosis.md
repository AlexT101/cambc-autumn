# Big camp groups we don't take: diagnosis (2026-11-11)

Data: the 520 pinned v115 scrims (260 Fish r2, 260 Mite r6; all 128 ladder maps, both sides), decoded by the
badmaps agent (`~/tmp-offload/badmaps/ext`). Scripts and pickles: `~/tmp-offload/biggroups/an/`
(`grp.py`, `crew.py`, `agg.py`, `bymap.py`, `attrib.py`, `tl.py`). Local comparison: badmaps' 512 games of
oc-dfuel-506 against spar-dvn1-Flp4 / -Mt3q on the ladder maps (`extl`), and a 12-game debug trace
(`replays/ab/bg-trace1`).

## What is true

1. **Fish and Mite clear Golem groups with gem clusters attached early, with nearly the whole team; we do not.**
   - 35 ladder maps have such a group (a Golem plus 1-12 gem clusters: 43-120 gems, 160 gold, 5.1-6.4k health).
   - Captures of them by r200, a game on those maps: Fish 0.43, Mite 0.47, us 0.06-0.11. Gems from them by r300:
     Fish 54, Mite 59, us 19-20.
   - Their early clears (woken by r200): crews of 4-5 (mean 4.2 Fish, 4.0 Mite; ours 3.0), first wake r45-130,
     about 22 rounds on a clean one (geodes: wake r58-67, clear r80-91, two tanks share 1.9k damage, no trip home).
     The holder is their gold carry (Mite: Vesper 31 of 51; Fish: Marcella or Vendetta).
   - Ours first fall around r400-500, when shards make a solo or two-body clear affordable, or never.
   - geodes: Mite and Fish take one of the two 92-gem Golem groups 5-6 times from r86-97 in all 4 games; we take
     ours 0 times. Those captures are 486-587 of their ~1,040 gems, more than the whole margin (we score 400-570).
2. **Monoliths: they capture first more often** (52 of 164 games on the 40 Monolith maps, against our 34), and one
   capture decides rows (2 Monoliths + 10 clusters, 470 gems, r790-930), gold_rush and famine.
3. **Herds:** stampede's shared block (6 Elk + 10 gem + 4 gold clusters, 16k health) pays them 1,266 gems a game
   and us 44; our kite wakes it at r46 and every ~52 rounds after and clears nothing.

## Why we don't

- **Crew pricing counts only allies already near.** A proposer expects allies in sight within 11 tiles that are
  free or on a harmless group (`crew_available`). Our bodies farm spread out, so a Golem is priced with one or two
  bodies, which means trips home, and loses to any solo camp. Nobody starts, so nobody joins. Trace (geodes, local):
  the first pick of a Golem group is r199 with "expected 1"; no crew of three forms before r450.
- **The draft's opening plan cannot take them either.** geodes' own Golem group is one of its 7 candidates, but its
  model puts every hit on one tank, so any Golem (and most Elk) clear "fails" and the plan lists only wolves and
  clusters (plan value 60 by r100 against 140 for the Golem group alone).
- Fish and Mite pay almost nothing to gather because they move packed all game; we would pay walks.

## The local bodies do not do it

Flp4 and Mt3q are our own code under their drafts: early Golem+gem captures by r150 are 0.02-0.03 a game against the
real teams' 0.14-0.15, and they clear half as many in all (0.34-0.37 a game against 0.68-0.69). A local gate cannot
see the race for these groups; it can only measure whether a team clear pays for itself.

## How much of our losses it explains (the correction to the early read)

- **Less than it looks in aggregate.** On the 35 Golem+gem maps we win 62% (140 games) against 67% elsewhere. In
  games where they took one by r200 and we did not, we still win 61% (Fish) and 73% (Mite), no worse than games
  where neither did (56%, 61%). Their early clear is not, on average, what beats us.
- **It is decisive on maps where big groups hold most of the gems.** By the share of a map's gem supply
  (gems / respawn) in Golem, Monolith and 7k+ herd groups:

  | share | maps | games | we win |
  |---|---|---|---|
  | 0 | 53 | 216 | 65.3% |
  | 0-0.2 | 8 | 32 | 62.5% |
  | 0.2-0.4 | 28 | 112 | 70.5% |
  | 0.4-0.6 | 26 | 104 | 67.3% |
  | 0.6+ | 13 | 56 | 53.6% |

  The 0.6+ maps are 10% of the ladder; level with the rest they would be worth about +1.3 points overall.
- **The tail maps named are four different failures**, not one:
  - geodes, waves, fields (partly), horseshoes, quadrants: the early team clear of a Golem group (above);
  - rows, gold_rush, famine, fields (partly): a Monolith capture at r400-930 that we contest and lose or never try
    (rows: we deal half or more of the damage in all 4 games and they capture all 4);
  - stampede: the kite on a shared big group;
  - the_pack: a 48-wolf herd.

## Earlier work that bears on a fix

- The teammate's `macro2-heavy` (worktree `~/wt/macro2`, on 506) already prices Golem and Monolith groups as team
  clears at the team's yield per champion-round, with staging. It fires (first Golem capture r222 against r331) and
  **lost its mirror screen: 48.6% of 869, Golem maps 45.3% of 375**; `macro2-mono` (Monoliths only) 48.0% of 1,482.
  Small captures and earned gold fall: the gathering costs more than the group pays, on average.
- EXPERIMENTS: packing arms (pair-pack, pos-crew, open-pack) moved Elk/Golem gold but not wins; `fe-yard`
  (backyard priced like the front) lost 2.6 points.
- So a general "take big groups" change has lost twice. What is left untested is the narrow case the replays point
  at: a group rich enough that one clear is worth several small captures (geodes: 92 gems for the champion-rounds of
  about two 15-gem captures), taken when gathering is cheap.

## Local results (2026-11-11)

Team clears of Golem groups lose on every map class, a held-out one included; the table and the mechanism are in
[EXPERIMENTS.md](../../EXPERIMENTS.md) under "Big camp groups". `split.py` prints the paired tables from the runs
`replays/ab/bg-{f1,r2,s2}-<bot>-<body>`; `mech.py` the capture, gold and death differences from decoded replays.
