# Bag-carrier prey against Fish r8 (2026-11-13): abandoned before building

**The idea.** A kill hands the killer the victim's carried gems. Fish r8 banks late, so its non-Vesper bodies carry
big bags for long stretches while its Vesper farms elsewhere. The plan was to make such a carrier a pursuit target
when Vesper is far and 2+ of ours are near, with a longer pursuit that the farm yields to.

**Verdict: abandoned before building.** The situation the arm targets is rare, and we already take it. Fish banks
0.20 such bags a game live and 0.15 locally, and we already kill about as many. Converting a third of the banked
ones would be under 0.1 kills a game, well under what the 50.5% bar needs. The frequent version of the situation is a Fish pack, where the arm's own
condition doesn't fire.

## Data

- **Live:** 161 Fish r8 games of v117/v118 (`~/tmp-offload/fishr8/live`).
- **Local, the body's fidelity:** v118 against `fr8-g25` on the 168 ranked maps, 336 games (fishr8's extract).
- **Local trace:** `variants/bag-carrier-prey-trace` is chy-525 plus a debug-only trace (`trace-chy525.patch`). It
  played `fr8-g25` on fresh ladder-v4 maps (b015 p7, 640 games, 200k fuel, debug). The trace logs each of our turns
  that sees a non-Vesper Fish carrier of 50+ gems: our branch, and what `prey()` decided about the carrier.

A **spell** is a run of rounds a Fish champion other than Vesper carries 50+ gems. "Opp" is the ideation's
condition: one of ours sees the carrier, Fish's Vesper is more than 8 from it, and 2+ of ours are within 6.
"Isolated" is opp with no other Fish (besides Vesper and a linked twin) within 8 of the carrier.

### 1. The body carries like live Fish

| | live r8 | v118 vs fr8-g25 | chy-525 vs fr8-g25 (fresh) |
|---|---|---|---|
| spells a game | 3.07 | 2.91 | 3.46 |
| carrier rounds a game | 339 | 255 | 269 |
| bag gems a game | 331 | 302 | 321 |
| ended by Fish's tribute | 71% | 78% | 78% |
| ended by our kill | 15% (47 gems a game) | 13% | 12% |
| opp spells a game | 1.06 | 0.88 | 0.87 |
| opp spells we kill | 32% | 32% | 32% |

The body's carriers hold about 75-80% of live's carrier rounds and bags. A local A/B could read this arm.

### 2. The opp rounds are mostly fights with Fish's pack

- **Live:** an opp round has 1.6 other Fish within 6 of the carrier on average. We hit the carrier in 83% of opp
  spells, a median of 826 damage, so we are already fighting them.
- **Local trace:** 34.8 opp unit-turns a game. Other Fish within 8 of the carrier: none in 14%, three or more in
  about 47%.

What our unit did in those turns (local, chy-525):

| verdict | share | carrier killed by us within 15 rounds |
|---|---|---|
| prey not run: retreat 25%, farm 8%, altar guard 6%, our own bank or tribute 8%, Willow 3% | 56% | 15% |
| fight lost (`chase_trade`) | 17% | 12% |
| chased (prey, pressed or team-pressed) | 9.5% | 25-30% |
| preyable in `chase_aim`, and we struck where we stood | 5.6% | 33% |
| escapes (the chase verdict) | 3.3% | 8% |
| pack covers it, healthy and not interceptable, near its spawn, out of vision | 7% | 3-14% |

The fights we turn down are mostly against the pack. That is where the old hunts lost: the team hunt of carriers
(49.5%), the comms hunt op (48.6%) and the widened hunt (46.4%).

### 3. Isolated carriers are rare, and we already take them

| | live r8 | local chy-525 |
|---|---|---|
| isolated episodes a game | 0.73 | 0.47 |
| distinct spells with one, ended by our kill, a game | 0.17 | 0.13 |
| distinct spells with one, ended by Fish's tribute, a game (the arm's whole target) | 0.20 | 0.15 |
| their bags when first seen isolated, gems a game (an upper bound) | ≤ 45 | ≤ 21 |
| tributed spells with a "we outnumber them" episode (ours within 6 > Fish within 8), a game | 0.28 | 0.23 |

- Live, spells we saw isolated give 0.17 of our 0.45 carrier kills a game. We kill about as many of them as Fish
  banks.
- Local isolated turns (4.9 a game): we chase in 15% of them. The pursuits the arm could add are these turns,
  about 1.2 a unit-game:
  - retreats while healthy and not carrying;
  - fights called lost, 65% of them Cassi or Issac, where the 600-health Cassi falls first and the death takes
    both bags;
  - escapes;
  - farm turns.

**Ceiling.** Turning a third of the tributed isolated bags into kills is about 0.07 kills a game live and 0.05
locally. With the looser "we outnumber them" trigger it is about 0.09 and 0.08: under 10 gems a game each way. That is under half a point against Fish, before what the pursuers stop farming.
fgate's unit also averages in the Mite body, so the read would be smaller still. The standard's dilution rule
(frequency × gain before screening) says not to screen it.

## What would have to change for this to pay

The banked gems this arm can't reach are carried inside Fish's pack, or while Vesper is near. Taking those is the
general problem of beating Fish's pack, not a pursuit rule. A revival needs a reason our fight model is wrong
against that pack, measured from live positions (`fishr8/fr_forkarms.py`), since the body fights unlike real Fish.

## Files

- `spells.py`: Fish's non-Vesper bag spells and how each ends, live or local (`SPELLS_OUT`).
- `opprounds.py`: what our near units did in live opp rounds.
- `isolated.py`: episodes under four conditions (A-D) and their outcomes.
- `tracejoin.py`, `retreats.py`, `retreats_iso.py`: the trace's verdicts joined with replay truth.
- `trace-chy525.patch`: the debug-only trace against `variants/chy-525`.
- Working data: `~/tmp-offload/bag-carrier-prey/`. The trace run is
  `replays/batch-20261113-005821-ab-bcp-trace-fr8g25-b015p7-p7`.
