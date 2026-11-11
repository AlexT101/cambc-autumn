# How real Fish wins the early fights (2026-11-11)

Brief: the [overruns](../overruns/README.md) read found that real Fish puts 2.6 attackers on its first target and
kills it 38% of the time where the Flp4 body and our own packs manage 2.1 and 16%. Find the mechanism in the real
replays, then take it to ocean's offence or to a Fish body that fights like the real one; check first how
faithfully the bodies defend.

**Answer: the mechanism is found, nothing is built that passes, no ocean candidate was gated.**

- Fish's edge is not micro. Focus, stuns, burst within a round, pack compactness, what the target can
  see, Strength and items, and each body's hit rate by distance to the nearest enemy are the same for real Fish,
  the Flp4 body and ocean.
- It is **who fights and where**. Fish's whole pack turns on the target: its Cassi, Issac, Vendetta and Willow hit
  champions where the body's (ocean's) keep hitting the camp. And Fish brings the pack to our half twice as often
  as the body, from round 30, before any kill.
- **The bodies do not defend like the real teams either.** In the fights we start outnumbered (the most common
  kind, 1.7 a game) the body's first target dies twice as often and the fight lasts 40% longer. Over all
  engagements to round 250 we net -0.21 kills a game against real Fish and +0.48 against Flp4 (Mite -0.02, Mt3q
  +0.68). A local read of any offence change is flattered by about 0.7 kills a game.
- Two body variants that chase on sight (`Flp4h`, `Flp4f`) moved none of the targets on 1,024 games each. The gap
  sits in ocean's strike planner (the pair's and Willow's caution) and in farm routing, not in the chase test. That
  is not a build for the time left.

## Data and tools

- Live: v115's 260 scrims against Fish r2 and 260 against Mite r6. Local: `oc-dfuel-506` against `spar-dvn1-Flp4`
  and `-Mt3q` on the 128 ladder maps (256 games each, the overruns pickles), and on `maps/gen` + `maps/gen-s1`
  (1,024 each, packgive's `ext2-base`).
- Engagements as in the overruns README: champion-on-champion damage with gaps of at most 6 rounds, bodies within
  8 of the first target the round before the first hit, rounds up to 250. T1 = they hit first with more bodies;
  T2 = we hit first with fewer; T3 = we hit first with more.
- [tools/](tools/): `eng.py` (one row an engagement, both directions: every body's distances, actions and damage),
  `cmp.py` (the fidelity table below, any set of row files), `summ.py`, `window.py` (the largest damage on the
  target in a round-long window; the decoder's `turn` field is not the slot, so windows are rounds), `hitrate.py` (hit, farm and step rates by distance to the nearest enemy), `half.py` (bodies by map
  half), `tr.py` (compact round-by-round trace), `body.sh` (plays and decodes a body variant),
  `patch_fishchase.py`; `q_*.py` are the one-off reads behind the tables (tightness, champion types, compactness,
  sight, early half, defence). Rows and decoded games: `~/tmp-offload/fishfight/`.

## What real Fish does

T1, they hit first with more bodies. "Body" columns are ocean code playing Fish's picks and emblems.

| | live Fish | Flp4, ladder | Flp4, gen | ocean against Fish (T3) |
|---|---|---|---|---|
| engagements | 136 | 141 | 397 | 190 |
| first target died | 38% ±8 | 16% ±6 | 22% ±4 | 16% |
| net kills for the attacker, each | +0.43 ±0.13 | -0.04 ±0.12 | +0.13 ±0.07 | +0.13 |
| attacker's losses, each | 0.10 | 0.26 | 0.17 | 0.15 |
| its bodies within 4 of the target the round before | 1.65 | 1.10 | 1.16 | 0.83 |
| engagements with 2+ within 4 | 52% | 18% | 25% | 18% |
| its bodies within 8 that hit a camp in the first three rounds | 11% | 23% | 20% | 27% |
| damage on the first target | 650 | 457 | 493 | 459 |

**1. The pack is on top of the target when the first hit lands.** Same compactness (mean pairwise distance of the
pack's bodies 3.75 for Fish and Flp4, largest clump within 3: 3.3 and 3.2), same first-hit distance (3.0, 2.9), but
1.65 Fish bodies stand within 4 of the target against 1.10. The kill rate follows that count for everyone:

| attackers within 4 the round before | 0 | 1 | 2 | 3+ |
|---|---|---|---|---|
| live Fish: target died (n) | 9% (11) | 30% (54) | 43% (46) | 56% (25) |
| ocean against Fish (n) | 11% (73) | 15% (82) | 34% (29) | 17% (6) |
| Flp4 body, ladder (n) | 14% (21) | 18% (94) | 11% (18) | 12% (8) |

With 3+ within 4 Fish nets +0.92 kills an engagement. About half of the 38% against 16% is this count, half is a
higher rate at each count.

**2. Everybody in the pack fights; nobody keeps the camp.** By Fish champion, in T1 (share of its engagements
within 8, share of those that hit a champion, damage an engagement, share hitting a camp in the first three
rounds):

| | live Fish | Flp4 body, ladder (gen) |
|---|---|---|
| Cassi | in 74%, hits 71%, 213 damage, camp 14%, within 4: 49% | in 62%, hits 52% (62%), 127 (164), camp 35% (28%), within 4: 27% (33%) |
| Issac | hits 56%, 93, camp 9% | hits 40% (49%), 65 (72), camp 24% (16%) |
| Vendetta | hits 64%, 106, camp 4% | hits 54% (66%), 85 (105), camp 23% (16%) |
| Willow | in 49%, hits 56%, 44, camp 14% | in 34% (30%), hits 29% (40%), 23 (21), camp 35% (28%) |
| Vesper | 548 damage when present | 204 (234) when present |
| Heart of Ruin, Marcella | 147, 161 | 185, 148: the same |

- Fish's Cassi stands 4 behind her melee and casts every cooldown; the damage gap is hers first (+86 an
  engagement), then Vesper's, Issac's, Vendetta's and Willow's. The body's front line already matches.
- With Willow in the pack Fish loses 0.06 bodies an engagement (0.14 without); when she hits, the target dies 49%.
  The body's Willow is with the pack less and hits half as often; ocean's holds no fight by design.
- The kills are not bursts: the largest damage the target takes in one round is 265 (35% of its health) against
  214-230 for the bodies, and only 18% of engagements have a round worth half its health. Fish's target is hit in
  4.2 separate rounds against 3.7 and dies 8.5 rounds in on average (12 for the body). Fish's melee stay
  on it: adjacent and healthy they step away 25% of the time against the body's 34%, and close from distance 2
  47% against 38%.
- Who is hit: our Cassi or Issac in 48% of Fish's T1 (28 pair deaths of 65; our Cassi dies in 16 of 26). Fish's
  pair is our first target in 21% of T3 and dies 7 times in 40.

**3. The pack comes to us.** Share of rounds 30 to 100, before any champion kill in the game, with three or more
bodies nearer the other side's spawn than their own:

| | live Fish | Flp4 | live Mite | Mt3q | ocean against Fish / Flp4 |
|---|---|---|---|---|---|
| 3+ bodies on the other half | 17.1% | 8.5% | 8.5% | 5.6% | 5.7% / 7.1% |
| body-rounds on the other half, rounds 30-250 | 22.6% | 12.5% | 14.4% | 10.6% | 11.5% / 14.3% |

72% of Fish's T1 are on our half (the body 58%), and we start 0.86 outnumbered fights a game on our own half
against Fish, 0.38 against the body. The kill rate itself does not depend on the half (38% and 37%).

**What it is not** (live Fish against the Flp4 body, same definitions): stun on the target in the first two rounds
29% and 28%; first hit a cast 56% and 51%; the target is the lowest-health defender 61% and 59%; the pack's bodies
seen by the target 63% and 60-66%; attackers' Strength 45.4 and 45.3, items 1.14 and 1.17, health 89% and 90%; the
target's own flight (2.4 tiles in four rounds, both). `hitrate.py`: a healthy melee body with an enemy at distance
1 / 2 / 3 hits a champion 84 / 42 / 9% of the time for Fish and 83 / 37 / 11% for the body; ranged at 3 / 4: 50 / 24%
and 47 / 24%.

Stated as something a bot can do: travel as one group including the pair and Willow, take the group to the
enemy's side of the map, and when an enemy comes within sight every member drops the camp and closes, the ranged
ones to 4 and the melee to contact, and stays on the first target.

## How the bodies defend

T2, we hit first with fewer bodies (2.2 against 4.2), the commonest engagement:

| | live Fish | Flp4, ladder | live Mite | Mt3q, ladder |
|---|---|---|---|---|
| engagements (a game) | 439 (1.69) | 373 (1.46) | 338 (1.30) | 338 (1.32) |
| net kills for us, each | -0.03 ±0.07 | +0.18 ±0.08 | +0.02 ±0.08 | +0.20 ±0.08 |
| our kills / our losses, each | 0.21 / 0.24 | 0.35 / 0.17 | 0.22 / 0.20 | 0.35 / 0.15 |
| their first target died | 8% ±2 | 15% ±4 | 11% ±3 | 14% ±4 |
| our damage / theirs | 836 / 508 | 1,153 / 670 | 798 / 599 | 916 / 633 |
| duration, rounds | 10.7 | 14.9 | 11.0 | 13.0 |
| on their half | 58% | 77% | 72% | 80% |

- The first six rounds are the same (the target at 69% and 67% of its health). The body's extra deaths come late:
  it stays in a fight for 15 rounds and its Heart of Ruin and Issac die in it (18 of 96 and 14 of 71 against 9 of
  101 and 6 of 104 for real Fish).
- Against real Fish a poke from behind is worth nothing in kills, whoever starts it: Prism +0.05, Vesper -0.08,
  Cassi -0.05, Issac -0.22 an engagement; against the body +0.27, +0.02, +0.16, +0.26.
- So the brief's caution holds: **no local read of an offence change can be trusted.** The bodies give up twice
  the kills and take none back.

## The body variants tried

Both are `spar-dvn1-Flp4` with one change, played by `oc-dfuel-506` on the ladder maps (256 games) and on gen +
gen-s1 (1,024 games), release builds, `tools/body.sh`:

- `Flp4h`: fishfid's `patch_hunt.py`, prey is any visible enemy whose simulated fight is won, whatever its health
  or half.
- `Flp4f`: `Flp4h` plus Fish's fitted chase rule (FISH_MODEL 10.3): prey is any visible enemy when our side's
  health in sight is over 1.24 times theirs and our own is over 44%
  ([tools/patch_fishchase.py](tools/patch_fishchase.py)).

Fidelity table (`cmp.py`); the targets are the live column:

| | live Fish | Flp4 lad | Flp4h lad | Flp4f lad | Flp4 gen | Flp4h gen | Flp4f gen |
|---|---|---|---|---|---|---|---|
| ocean win % | 69.2 | 83.2 | 82.8 | 86.7 | 74.2 | 77.4 | 79.6 |
| T1: first target died | 38% ±8 | 16% ±6 | 28% ±7 | 19% ±7 | 22% ±4 | 23% ±4 | 21% ±4 |
| T1: net kills for them, each | +0.43 | -0.04 | +0.16 | +0.05 | +0.13 | +0.15 | +0.12 |
| T1: their attackers | 2.62 | 2.14 | 2.43 | 2.24 | 2.22 | 2.20 | 2.20 |
| T1: their bodies within 4 | 1.65 | 1.10 | 1.22 | 1.15 | 1.16 | 1.20 | 1.13 |
| T1: their bodies hitting a camp | 11% | 23% | 20% | 15% | 20% | 19% | 9% |
| T2: net kills for us, each | -0.03 | +0.18 | +0.12 | +0.21 | +0.13 | +0.08 | +0.08 |
| T2: their first target died | 8% | 15% | 12% | 17% | 10% | 12% | 13% |
| T2: duration, rounds | 10.7 | 14.9 | 15.0 | 17.9 | 15.4 | 16.4 | 18.4 |
| net kills for us a game, all engagements | -0.21 | +0.48 | +0.31 | +0.75 | +0.26 | +0.11 | +0.26 |
| rounds with 4+ of them on one of ours, a game | 0.38 | 0.19 | 0.21 | 0.18 | 0.10 | 0.12 | 0.11 |
| rounds with 4+ of ours on one of them | 0.16 | 0.47 | 0.35 | 0.42 | 0.25 | 0.24 | 0.31 |

- `Flp4h` reads better on the ladder maps (28% against 16%) and no different on four times the games. Pooled, the
  first target dies 24% against 20%, inside the noise; the body gets no stronger. Not adopted.
- `Flp4f` does drop the camp (9%, Fish's 11%) and still puts no more attackers on the target: after the strike
  search, a chase only walks, and the search is what declines the hit. It makes the body worse at everything else
  (longer fights, more of its own deaths). Rejected.
- Neither was checked on the four cells (stampede, guardians, crater, adgato_gemcombat5): they do not pass the
  aggregate targets, and 8 games would not rescue them.

## Results against oc-dfuel-506

| gate | result |
|---|---|
| none | no ocean candidate built, no fgate games played |

## Verdict

- The 38% is the whole Fish team arriving together and all of it fighting, on our half. It is a team shape (one
  group that includes the pair and the healer, routed towards the enemy), not a fight rule that can be patched in.
- **Ocean's offence: not built.** Copying it means farming as one group, which every cohesion arm has lost
  (fc1/fc2, squads, packs, rally), and its test would be against bodies that give up twice the kills real Fish
  does. Any local win would be the mirror flattering us.
- **A fight-faithful Fish body: not reached.** The chase test is not the lever. What a body needs, in order of
  size: (1) the pair's and Willow's caution in the strike planner and guard removed for the body (`linked` and
  `heals()` in `combat/plan.cc`, `guard.cc`, `fight.cc`, `safety.cc`), so Cassi casts from 4 and Willow hits;
  (2) farm routing that takes the group to the enemy's half (3+ bodies there 17% of rounds 30-100, now 8.5%);
  (3) leaving a fight it is losing after about ten rounds. Each is a change inside ocean's planner or farm choice
  with its own fidelity loop; `cmp.py` gives the targets in one table for whoever takes it up.
- For the final: nothing here changes v115. The pack-margin arms stay as packgive left them; this read adds that
  the fights they avoid are lost on any ground (38% on our half, 37% on theirs), so a rule tied to our own half
  misses a quarter of them.

## Files

- Body variants (gitignored): `bots/variants/spar-dvn1-Flp4h` (already there), `spar-dvn1-Flp4f`.
- Working data: `~/tmp-offload/fishfight` (`live.pkl`, `local.pkl`: engagement rows of the overruns samples;
  `rows-*`, `games-*`, `ext-*`: the body variants and the gen baseline; `logs/`).
