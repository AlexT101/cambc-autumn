# Mite's wards, and what ocean could take from them (2026-11-08)

Mite's warding was rebuilt from replays, set beside ocean's in the same games, and the two differences that could
matter were built as arms on oc-base25. Scripts are in [miteward-tools/](miteward-tools/). The decoded dumps were
deleted after the decision; the manifests and run logs stay in `~/tmp-offload/miteward/`. Rejected: every arm H0.

## Data

- **r1 era**: Mite's 450 own-view games of 11-07 05:00-14:59 UTC (`replays/fish-scorecard/mite-1107/`, from the
  [Mite study](../mite-2026-11-08/README.md)). They hold 1.83M alive turns and 72,289 wards.
- **r2 era**: every capture.db Mite game from 11-08 01:12 UTC on (r2's pin), 1,274 replays and 1,047 distinct. They were
  decoded with `tools/fish/extract.mjs` (`r2_manifest.py`) and hold 4.27M alive turns and 166,657 wards. 933 of them are
  our scrims (v84-v86, ocean 65.8% against r2). Their ocean side was decoded too (`ocean_manifest.py`): 3.89M turns and
  98,835 wards.
- **Vision check** (`validate.py`). Python's shadowcast (`tools/replay/narrative/vision.py`) places every enemy a
  champion sees at turn start in its own sight or its ward's (43,533 sightings, 0 unexplained). 30% of those sightings
  are its ward's alone.
- r1 and r2 ward behaviour is the same to the decimal: 3.95 vs 3.90 wards per 100 alive turns, 59% vs 61% on bushes,
  28% placed on the recharge round, 9.0% vs 9.6% of hits ward-enabled. Mite's update did not touch wards, so the
  tables below pool the eras or show r2.

## What Mite does

One ward function for every champion: the type changes the rate by under 1 point and the bush share by under 10. It is
a scouting habit, not a combat tool.

1. **Cadence.** Mite places 6% of the turns its ward is ready, and 28% on the round it recharges (the trigger was
   already true while the ward was down). After that the rate is 5-9% a turn, and under 2% once the ward has been
   ready for 100+ rounds. 28% of gaps are exactly 10 rounds.
2. **Trigger and tile: unseen bushes first, camps second, open ground last** (`classes.py`, ready turns, r1;
   availability is measured at the tile the ward goes down from):

   | in ward reach (within 2) | ready turns | placed | where |
   |---|---:|---:|---|
   | a bush of another cluster with tiles nobody sees | 77k | 52-57% | 95-98% on that bush |
   | a bush of another cluster, all of it seen | 66k | 6-13% | 56-65% bush, 20-35% open |
   | no bush, a camp tile (live or cleared) | 292k | 4-6% | 60-66% on the camp tile |
   | nothing | 754k | 1.9% | 94% open |

   - **Bushes** are the main trigger. The more unseen bush tiles a ward would show, the likelier it goes down: 19% at 1
     tile, 59% at 6-10, 74-78% at 11+ (no enemy in sight). It is less likely with enemies in sight (64% with none, 50% / 36%
     / 20% with 1 / 2 / 3+) and with the old ward close (within 2: 29%; farther than 8: 60-68%).
   - **Tile.** Within a cluster it takes the tile that adds the most unseen bush tiles 80% of the time, Fish's rule
     (`fish_hit`). A conditional logit over the legal tiles (`tile.py`) puts bush at +5.0, a camp tile at +2.9, own
     cluster at -3.9 and new tiles at +0.6 a 10. Where the champion goes next adds nothing.
   - **Camp wards**: 12% of all wards, on a camp tile of a live group being fought (Mite wards the camp it is hitting) or
     of a cleared or respawning one. 78% of them add no tile to what the champion sees at placement. They are for later:
     the ward keeps the group's state and capture readable after the champion leaves (rules vision.unseen_units).
   - **Lost sight**: on the turn after every enemy left its sight, the open-ground rate triples (6.3% vs 1.8%) and a
     ward is 54% toward the nearest last-seen enemy, against 32% for a random legal tile.
3. **What it skips.** Big bags (100+ gems: 25% on an unseen bush, against 53%), tiles beside an altar (23%; a tribute
   channel refuses wards), and fights (3% of ready contact turns, against 7% with no enemy). Deaths and respawns change
   nothing.
4. **Timing within the turn**: 75% after its move, 22% with no move, 3% before it. Ocean's are the same (83 / 13 / 4).

## Ocean beside it

Same r2 games, both sides decoded:

| | Mite | ocean |
|---|---:|---:|
| wards a game (team) | 159 | 106 |
| per ready turn: no enemy / enemy in sight / contact | 7.2 / 3.8 / 2.9% | 3.4 / 3.0 / 2.8% |
| per ready turn with an unseen bush in reach | 59% | 28% |
| per ready turn with a camp tile and no bush in reach | 4.3% | 1.7% |
| on a bush / on a camp tile | 61% / 12% | 72% / 0.7% |
| hits on a champion that only the hitter's ward saw | 15.1 a game (9.6%) | 15.1 a game (9.3%) |
| kills whose last hit only a ward saw | 0.79 a game | 0.65 a game |
| hits from an attacker the victim did not see at its last turn end | 8.4% (team: 4.6%) | 14.5% (team: 7.9%) |
| kills from such an unseen attacker | 13.0% | 19.8% |
| hits from a bush | 16.7 a game | 26.0 a game |
| hits on a champion in a bush | 13.9 a game (58% ward-only) | 11.4 a game (57%) |

- **Ward-enabled damage is level.** Mite's extra 53 wards a game add no ward-only hits. Its surplus is scouting with
  no enemy near and camp watching, the information side.
- **Surprise runs our way.** Ocean's hits come from an attacker the victim did not see nearly twice as often (14.5% vs
  8.4%), and ocean kills 6.3 a game to Mite's 5.2. Ocean's bush play beats Mite's scouting. Mite's wards do not stop it:
  hits from a bush are 26 a game for us, 17 for Mite.
- **Where ocean differs in code** (oc-base25 `bot.cc`):
  - The drafted site ward is placed once in range and kept while that work lasts.
  - `ward_bushes` moves the ward only to a cluster scoring strictly more ability-range tiles (near us and our work)
    than the warded one, so a ward watching a good cluster stays as we walk on.
  - The reveal ward (CHANGES 421) is a rare turn-start ward after a fight or a hurt.
  - Nothing wards a camp tile.
  - Mite has no draft plan and re-wards on the move instead.

## Arms

On `variants/oc-mw-dev`: oc-base25 plus `params::mw` knobs, all off. bench 100M is identical (16/16 default, 52/52 wide
test-draft, 52/52 wide own-draft).
- **fresh** (`fN`): `ward_bushes` takes any cluster scoring at least N over the warded one, once our ward is more than
  `fresh_keep` (2) from us. This is Mite's "move the ward to the newest unseen bush". The planned site ward still
  goes first.
- **camp** (`c1`, `c2`): with no bush in ward reach and no planned ward, a camp tile within 2 of a group our ward does
  not see. c1 takes cleared or respawning groups only (our claim first). c2 adds live ones.
- Not built:
  - the lost-sight ward overlaps s1's reveal-ward-without-gate arm (rw2, `~/tmp-offload/handoff/parked/s1.md`);
  - fewer wards in fights is not a gap (2.9% vs 2.8%).

## Results

Against oc-base25, own drafts, on `mw-scr-1110` (`--mix ladder-v2`), each arm its own SPRT `--sprt 0.50,0.5025`
(seeds 11101-11104). The disk-full crash stopped all four at ~24k games; each resumed on its unplayed maps with its
earlier pairs in the SPRT.

| Arm | Result |
|---|---|
| f1 (fresh=1) | 50.07% (49.85-50.29) of 199,518 games; H0 at 199,445 (LLR -2.96) |
| f4 (fresh=4) | 49.69% (49.13-50.25) of 30,985 games; H0 (LLR -2.96) |
| c1 (camp, cleared groups) | 49.75% (49.40-50.11) of 75,026 games; H0 at 75,021 (LLR -2.95) |
| c2 (camp, all groups) | 49.84% (49.53-50.15) of 98,827 games; H0 at 98,812 (LLR -2.96) |
| s1's rw2 (lost-sight ward, `s1-scr-710`) | 49.7% (49.2-50.2) of 44,679 games; H0 |

c1 and c2 also raise out-of-fuel turns by ~36% (the camp scan); f1 and f4 are level. Nothing ships; the held-out,
varied and panel suites stay unused.

## Conclusion

The data said it before the games did: Mite's extra wards buy information, not damage. Ward-enabled hits were level
(15.1 a game each), and ocean already surprises more (14.5% of hits vs 8.4%). Copying the extra wards moved nothing.

Lesson for "copy the opponent" work: before building, measure whether the behaviour converts into an outcome
(here, hits and kills) in the opponent's games. A visible difference in what they do is not a gap if the result it
should produce is already level or in our favour.
