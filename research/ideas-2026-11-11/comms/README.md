# Comms: what the 8 bytes carry, what else they could, and what wins (2026-11-11)

Question (user): comms could carry ally positions, and could fit twice the data if claims lagged a round. Which
encodings are worth it, and which uses of the information win games?

Short answer: the team word has room for every ally's position at no cost in bytes (a claim changes in only 8.5% of
turns, so its field is free most of the time). Carrying positions alone changes nothing. One consumer turns them
into a small, repeatable gain: counting a claimer we cannot see, but whose posted tile is at its group, as part of
that group's crew. That is worth about +0.45 points against the Fish and Mite bodies at 200k fuel (122,880 games,
CI +0.20 to +0.72) and about +0.2 at the ladder's 100k (CI -0.07 to +0.47), where its fuel cost eats half of it.
It is real but small: not a needle-mover, and too small for a live test to see.

After a fuel pass the merge candidate is `bots/variants/cm2-k3` (`cm2-k3.patch` on `oc-dfuel-506`): level with base
on out-of-fuel turns, and +0.17 / +0.18 points at 100k on two independent reads (see "Fuel pass").

## What ocean sends today

The 8 team bytes are one 64-bit word laid out per map (`bots/ocean/src/model/comms.cc`):

| field | bits (team of 6, typical) | content | staleness |
|---|---|---|---|
| claims | 6 x bits(groups + 1), often 6 x 4-5 | each ally's claimed group | none: rewritten every turn |
| bag | bits(128 x team) = 10 | one ally's bag, in fours | one poster a round |
| camp | bits(sum of each group's respawn + 17), about 10-12 | one capture and its respawn round | one a round, fits 192/192 traced games |
| ally (CHANGES 465) | bits(cells x 4 x team + 1) | one non-healer's tile in a c x c cell, c = 1/3/5 | one poster a round, only while a healer lives; fits 79% of games |

Each champion's priority adds 16 bits, readable only on a champion in sight: claim + 1 (8 bits), the support mailbox
(3), the chase bit and round (3), 2 spare.

What that leaves a reader knowing about a teammate it cannot see (traces, 96 games against each of the Fish and Mite
bodies, which agree):

- A teammate is in sight in only about 40% of reader-teammate pairs. The unseen ones are far: median 18 tiles, 27%
  within 12, 9% within 8.
- The ally record gives a tile no older than 3 rounds for 16% of unseen pairs. Otherwise the reader assumes the
  claimed group's centre, which is off by a median 7 tiles (15+ tiles 29% of the time).
- An unseen claimer is 6+ tiles from its claimed group's centre 54% of the time and 10+ tiles 42%. The farm values
  count it as working there from now.

## Encodings considered

All three reuse the claim fields, widened to take every spare bit: one slot per ally of (64 - bag - camp) / team
bits, 7 bits in a team of 6 (77% of games). A slot value below groups + 1 is a claim, anything above is a tile code.
They cost no bytes and replace the old ally record. `params::comms_slots` picks one.

| mode | idea | tile frames | unseen claims read wrong | tile no older than 3 rounds | tile error |
|---|---|---|---|---|---|
| today | one ally record a round | - | 0% | 16% of unseen pairs | cell of 1-5 |
| 2: alternate (the user's idea) | claim on even turns, tile on odd | 50% | 4.2% | 96% | cell side median 6: median 2, within 4 93% |
| 1: claim on change | claim when it changes (held two turns so allies on both sides of the turn order read it) and every 8 rounds; tile otherwise | 77% | 0.0% | 96.5% | as mode 2 |
| 3: claim on change, split tile | as mode 1, but a tile frame is x one turn and y the next, at cell side 1-3 | 77% | 0.0% | 81% (84% within 4) | median 1, within 2 91%, 99th pct 5 |

- **The one-round latency idea works but is dominated.** Alternating doubles the capacity as predicted, and the
  price is a claim one round late on half the turns (4% of reads of an unseen ally's claim are wrong). Sending the
  claim only when it changes gets more tile frames and no claim lag, because claims rarely change.
- **Mode 3 applies the same latency trade to the tile instead of the claim**: two turns to deliver a position, in
  exchange for near-tile precision. A reserved code marks a jump (recall, teleport, respawn) so a reader never
  pairs an x from before it with a y from after; without it the 99th percentile error was 23 tiles.
- Fuel: 0.33% more in the debug build; out-of-fuel turns equal to base at both budgets tested with the plumbing alone.

Not built:

- Positions in the priority word: it is readable only on champions in sight, whose position we already have.
- Enemy sightings: lost three times already (allies give way to enemies they cannot see); not repeated.
- Status frames (health, ultimate ready) and a second camp record in the spare tile frames: see "Not reached".

## Uses, and what each did

Consumers are separate knobs on top of the plumbing (`bots/variants/cm2-dev/src/params.h`):

| knob | use | how often it acts (traces) |
|---|---|---|
| (none) | Willow's follow already reads told tiles; coverage rises from 16% to 81-96% | every healer game |
| `told_arrival_rounds` | farm: time an unseen claimer's arrival from its told tile instead of counting it as working now | 13 arrivals a game, about half with a delay (median 0-3 rounds) |
| `told_late` | farm: a claimer told to arrive after us joins the clear on arrival, not from the start | 1.1-1.4 repricings a game |
| `told_crew` | crew: an unseen claimer whose told tile is as near its group as we are counts in the group's crew | flips 22% of games, against 14% without it |
| `told_pull` | pathing tie-break pulls toward an unseen ally's told tile instead of its claim's centre | flips 26% of games |

Results against `oc-dfuel-506` (= ocean 506): fresh `--mix ladder-v2` maps, both sides, each arm and the base
against four fixed Fish bodies (`spar-dvn1..4-Flp4`) and four Mite bodies (`spar-dvn1..4-Mt3qro`), paired by map,
side and body; the unit is a map. Panels A, B, C are 10,240 maps each (40,960 games an arm a panel).

| arm | content | fuel | panels | win % (base) | paired diff, points (95% CI) | games | Fish | Mite | OOF turns a game (base) |
|---|---|---|---|---|---|---|---|---|---|
| cm2-s2 | alternate, plumbing only | 200k | A | 79.40 (79.27) | +0.13 (-0.36..+0.62) | 40,960 | +0.05 ±0.67 | +0.21 ±0.71 | 0.05 (0.05) |
| cm2-s1 | on change, cells, plumbing only | 200k | A | 79.33 (79.27) | +0.06 (-0.30..+0.42) | 40,960 | +0.07 ±0.49 | +0.05 ±0.51 | 0.05 (0.05) |
| cm2-s3 | on change, split, plumbing only | 200k | A | 79.26 (79.27) | -0.00 (-0.36..+0.35) | 40,960 | -0.27 ±0.50 | +0.26 ±0.50 | 0.05 (0.05) |
| cm2-s3a | s3 + arrival | 200k | A | 79.31 (79.27) | +0.04 (-0.34..+0.41) | 40,960 | -0.24 ±0.52 | +0.32 ±0.53 | 0.05 (0.05) |
| cm2-s3p | s3 + pull | 200k | A | 79.27 (79.27) | +0.00 (-0.50..+0.50) | 40,960 | -0.22 ±0.68 | +0.22 ±0.72 | 0.05 (0.05) |
| cm2-s3l | s3a + late | 200k | C | 79.50 (79.39) | +0.11 (-0.26..+0.48) | 40,960 | +0.16 ±0.51 | +0.06 ±0.54 | 0.05 (0.05) |
| cm2-s1c | s1 + arrival, late, crew | 200k | C | 79.62 (79.39) | +0.23 (-0.23..+0.68) | 40,960 | -0.05 ±0.63 | +0.51 ±0.66 | 0.06 (0.05) |
| cm2-s3c | s3a + late + crew | 200k | A+B+C | 79.70 (79.31) | +0.40 (+0.14..+0.66) | 122,880 | +0.28 ±0.36 | +0.52 ±0.38 | 0.05 (0.05) |
| cm2-s3c | | 200k | B+C, held out | 79.73 (79.32) | +0.41 (+0.09..+0.73) | 81,920 | +0.25 ±0.44 | +0.57 ±0.46 | 0.05 (0.05) |
| **cm2-s3k** | s3a + crew | 200k | A+B+C | 79.77 (79.31) | **+0.46 (+0.20..+0.72)** | 122,880 | +0.35 ±0.36 | +0.57 ±0.38 | 0.05 (0.05) |
| cm2-s3c | | 100k | A+B+C | 79.72 (79.46) | +0.26 (-0.02..+0.53) | 122,880 | +0.11 ±0.38 | +0.40 ±0.40 | 6.24 (5.99) |
| **cm2-s3k** | | 100k | A+B+C | 79.66 (79.46) | **+0.20 (-0.07..+0.47)** | 122,880 | -0.02 ±0.38 | +0.41 ±0.40 | 6.22 (5.99) |

s3c was picked as the best of six arms on panel A, so its unbiased read is panels B and C. s3k was built after
that, to split s3c's two consumers; its panel A and B runs came after its panel C one.

Verdicts:

- **Plumbing alone (s1, s2, s3): level**, as the user predicted. That includes Willow's follow, which gets a told
  tile five times as often and gains nothing measurable from it.
- **Alternation (s2): level, and dominated** by claim-on-change on every trace measure.
- **Arrival timing, late claimers, pull (s3a, s3l, s3p): level.** They rarely have anything to act on.
- **Crew count from told tiles (s3k): small gain at 200k, about half of it at 100k.** The late-claimer logic on
  top (s3c) adds nothing, so s3k is the candidate: less code, same result. Cells against split tiles (s1c against
  s3c on panel C) are indistinguishable, so the crew count does not need tile precision.
- The 100k loss comes with 0.23 more out-of-fuel turns a game. The plumbing was built for reach, not fuel, so a
  fuel pass on s3k could plausibly recover the 200k figure; that was not done.

Independent read of s3k at 100k on the reworked `tools/fgate.py` (its own 40,960 fresh maps, unmetered run-time
Fish and Mite bodies, 327,680 games): 50.20% (49.95-50.44), that is +0.20 ±0.25 points; Fish +0.17, Mite +0.22;
ladder maps (side read) 49.63% (48.49-50.77). It agrees with the panels' +0.20 (-0.07..+0.47); the two together
put the 100k gain at about +0.20 ±0.18.

**Verdict on s3k (and s3c): a real gain of about +0.2 points at ladder fuel, +0.46 at 200k. It is in the 50-50.5
zone, below the pass bar, and far below what a live test can see. Not merged.** If it is wanted, take s3k (not s3c)
and give it a fuel pass first.

Why positions alone do so little: the teammates whose position changes a decision in the next few rounds are the
near ones, and those are mostly in sight already. An unseen teammate is a median 18 tiles away, so knowing its tile
to within 2 rather than 7 rarely changes what we do now. The crew count is the exception because it is a yes/no fact
(is my partner at the group or not) that the claim alone gets wrong half the time.

## Fuel pass: `cm2-k3` (2026-11-11)

Where s3k's fuel went, 100k on panel A (40,960 games an arm; base 79.46%, 6.15 out-of-fuel turns a game):

| arm | content | paired diff, points (95% CI) | OOF turns a game |
|---|---|---|---|
| cm2-s3 | plumbing only | -0.31 (-0.75..+0.13) | 6.41 |
| cm2-s3a | + farm arrival | -0.38 (-0.82..+0.06) | 6.39 |
| cm2-s3k | + arrival + crew | +0.00 (-0.47..+0.48) | 6.40 |
| cm2-k1 | s3k with the unused code stripped (52/52 identical replays, -0.23% fuel) | -0.01 (-0.48..+0.47) | 6.35 |
| cm2-k2 | k1 without farm arrival | +0.10 (-0.37..+0.58) | 6.36 |

The plumbing is the whole cost: +1.0-1.3% fuel a turn on identical games (the per-ally decode and x/y history on every
turn), all of the extra out-of-fuel turns, and about 0.3 points at 100k. The crew count costs nothing measurable and
earns about +0.3 to +0.5 on top. Farm arrival does nothing (k2 = k1).

`cm2-k3` = `oc-dfuel-506` + `cm2-k3.patch` (196 lines, 6 files; `mkfinal.py` builds it) removes the reader's
per-turn work instead of trimming it:

- A tile frame is one 2D cell (side median 6), decoded on demand from the word read this turn, only when the crew
  count (or Willow's follow) asks. No history: a tile is known only while the ally's slot holds one (77% of turns).
- A slot holding a tile leaves the claim as last read, so the claim costs one compare an ally.
- The old ally record's poster loop goes; `send` takes our position from `main.cc`; no farm arrival.
- Bench (100M, identical games): 0.15% less fuel than base, against 1.01% more for k2.

It is not behaviour-preserving relative to s3k: cells instead of 1-3 tile precision, no 4-round history, no jump
code, no farm arrival.

Results against `oc-dfuel-506` (`cm2-k3`):

| read | fuel | win % (base) | diff, points (95% CI) | games | Fish | Mite | OOF turns a game (base) |
|---|---|---|---|---|---|---|---|
| panels A+B+C | 100k | 79.64 (79.46) | +0.18 (-0.09..+0.44) | 122,880 | +0.00 ±0.36 | +0.35 ±0.38 | 5.97 (5.99) |
| `fgate.py`, 16 batches, unmetered bodies | 100k | 50.17 (49.93-50.40) | +0.17 ±0.24 | 327,680 | +0.40 ±0.32 | -0.07 ±0.35 | 5.78 (5.77) |
| panels A+B+C | 200k | 79.46 (79.31) | +0.15 (-0.11..+0.42) | 122,880 | +0.10 ±0.36 | +0.21 ±0.38 | 0.05 (0.05) |
| cm2-s3k, panels A+B+C, for comparison | 200k | 79.77 (79.31) | +0.46 (+0.20..+0.72) | 122,880 | +0.35 ±0.36 | +0.57 ±0.38 | 0.05 (0.05) |
| cm2-s3k, `fgate.py`, for comparison | 100k | 50.20 (49.95-50.44) | +0.20 ±0.25 | 327,680 | +0.17 ±0.34 | +0.22 ±0.36 | 5.98 (5.77) |

- **Fuel: level with base** on both reads (s3k was +0.2 turns a game on both).
- **Win rate: +0.17 and +0.18 on two independent reads at 100k**, about +0.17 ±0.18 together; each interval alone
  reaches zero, and the Fish/Mite split swaps between the two reads.
- **The fuel came back but the gain at 100k did not grow**: at 200k k3 is +0.15 where s3k is +0.46, so the coarse,
  history-free tile lost about as much behaviour as the cheaper reader saved in fuel.
- Not built: posting, in a tile frame, the ally's distance to the group it claims instead of a map cell. That is the
  one fact the crew count uses, it is exact to a tile, and it decodes on demand with no history, so it should give
  s3k's behaviour at k3's fuel. Willow's follow would fall back to the claim's centre.

## Do Fish and Mite converge on fights more than we do?

One use that could be large is calling far allies to a fight. Live check on 512 ladder games of v115 (256 against
each), every engagement start (first enemy champion damage after 10 quiet rounds), teammates 10-25 tiles away that
see no enemy (`live_converge.py`):

| team | engagements | far teammates' approach over 8 rounds, before / after | allies within 5 at the start | victim dead within 15 rounds |
|---|---|---|---|---|
| Fish | 6,280 | +0.14 / +1.26 | 1.76 | 15.7% |
| Mite | 5,313 | -0.07 / +1.28 | 1.51 | 19.8% |
| ocean against Fish | 2,461 | -0.10 / +0.89 | 1.37 | 20.9% |
| ocean against Mite | 2,677 | +0.20 / +0.92 | 1.49 | 21.3% |

Their far teammates close about 1.1-1.35 tiles more in the 8 rounds after a fight starts than before it; ours 0.7-1.0.
The gap is a third of a tile over 8 rounds, so neither of them is running a strong "come and help" call that we lack.
Two things do differ: their champions take the first hit 2-2.5 times as often as ours do (we open more of the
fights), and Fish's champion that is hit has more allies already close (1.76 against our 1.37). Both are about where
champions stand before the fight, not about what gets broadcast once it starts.

## Not reached

- **Camp surprises.** 14 times a game a champion comes back to a group it believed alive and finds it cleared, and
  8-9 times finds it captured and respawning (2.5-3 a game each for its own claim). Most captures seen this way are
  the enemy's first sighting, which comms cannot remove, but clears by teammates could be posted in spare tile
  frames. Measured, not built.
- Status frames (health, ultimate ready) for a "help me" or "ult ready, engage" consumer. The live table above says
  the prize is small unless it changes where champions stand before fights.
- A consumer for ganks or grouping: the teammate's macro sessions cover fight verdicts and claim ownership in
  comms (macro2, macro5), so these were left to them.
- The big-arm archive was not used; the live read above is from the local v115 scrim replays only.

## Files

- Merge candidate: `bots/variants/cm2-k3` = `oc-dfuel-506` + `cm2-k3.patch` (`mkfinal.py cm2-k3` rebuilds it;
  `cm2-k1`, `cm2-k2` are the earlier fuel-pass steps).
- Dev copy with every knob off (byte-identical replays to base on `bench.py`'s 52): `bots/variants/cm2-dev`.
- Frozen arms: `bots/variants/cm2-s1`, `-s2`, `-s3` (plumbing, modes 1-3), `-s3a` (+ arrival), `-s3l` (+ late),
  `-s3k` (+ crew), `-s3c` (+ late and crew), `-s3p` (+ pull), `-s1c` (mode 1 + late and crew); `cm2-tr*` are the
  trace builds.
- `mkarm.py` freezes an arm, `batch.py` prepares panels, runs and reports, `trace.py` reads the debug traces,
  `live_converge.py` is the live table.
- Maps: seeds 3611000-3611119 (`--mix ladder-v2`), panels A, B, C of 10,240 maps each, under
  `~/tmp-offload/comms2/`; replays' summaries in `replays/ab/cmb-*`.
