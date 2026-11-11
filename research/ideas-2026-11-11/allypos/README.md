# Ally positions from comms in existing decisions (2026-11-11)

Question (user): "also when ally comms are merged it adds a lot more dims of things we can do like modifying
existing things to consider ally positions". Which existing decisions on charybdis would play better if they knew
where unseen allies are (the cm2-k3 slots: a told cell centre, cell side median 6, there on ~77% of turns)?

Answer: none of the four tried moves the needle. Each is level against `chy18-cm2k3` at 200k fuel; the best is
under +0.1 points with intervals of ±0.14-0.19 over 327,680 games. No 100k run, since no 200k read showed a gain.

## How the candidates were picked

Every decision that reads ally positions was read (128 `world.allies` loops). Nearly all of them read only allies
in sight. The ones where a told tile could matter are those whose radius is wider than the vision radius (8):
only there is a relevant ally out of sight because it is out of range rather than behind a wall. Those were:

- `crew_available_radius` (11) and `crew_near_radius` (9) in `economy/crew.cc`: which free allies a strong-group
  proposal expects. `read_avail` returned "never" for any ally out of sight.
- The siege staging ring (`economy/siege.cc`, reach + 3 around each live member) and farm's Monolith staging
  (`mono_engage`, reach + 2): the gather counts only allies in sight, but a ring around a Monolith (reach 5) is
  wider than our sight, so an ally across it is unseen and the gather can wait out `siege_max_wait` /
  `mono_max_wait`.
- The crew count (`crew_claimer_bits`, the one consumer that already won in cm2-k3) counts any claimer seen within
  `crew_seen_rounds` (12) without asking where it is now; its told tile says whether it has since left (a heal
  trip or a recall).

Combat radii (`fight_ally_radius` 4, `pack_ally_radius` 6, `pack_radius` 4) are inside vision and finer than a
told cell (±3), so fight and retreat consumers were not built. The fight lever the live data shows (Fish's victims
have more allies close when hit) is about where champions stand before a fight, not a radius test in an existing
decision.

A debug trace of `chy18-apgc` (256 ladder games, mirror against cm2-k3) found the crew-availability branch
reached in 87% of games, the siege-ring branch in 12% and the Monolith-ring branch in 9%.

## Variants (all on `variants/chy18-cm2k3`; `told_tile` in `bot_parts.h`: an unseen ally's slot cell, at most a round old)

| variant | patch | change |
|---|---|---|
| `chy18-apg` | `chy18-apg.patch` | G: siege and Monolith gathers count an unseen claimer whose told tile is at the staging ring |
| `chy18-apc` | `chy18-apc.patch` | C: an unseen free ally (no claim, or a harmless one) is available for a crew by its told tile (`crew_available_radius` of the group, or of us); it adds output only, as an unseen claimer does |
| `chy18-apgc` | `chy18-apgc.patch` | G + C |
| `chy18-apk` | `chy18-apk.patch` | K: an unseen claimer with a told tile counts in the crew by the tile alone, not by a sight within 12 rounds |
| `chy18-apc2` | `chy18-apc2.patch` | C + K |

## Results

`tools/fgate.py CAND variants/chy18-cm2k3 --fuel 200000 --screen --ci 0`, unmetered Flp4 / Mt3q bodies, pool
batches 0-7 (phase 1) and 0-15 (phase 2). `report.py` pools the batches.

Results against chy18-cm2k3 (200k fuel):

| arm | win% (95% CI) | games | Fish | Mite | paired games differ | OOF turns a game (base) | verdict |
|---|---|---|---|---|---|---|---|
| apg (G), b0-7 | 49.98 (49.91-50.04) | 163,840 | -0.09 ±0.09 | +0.04 ±0.09 | 0.4% | 0.047 (0.046) | level, nearly inert |
| apgc (G+C), b0-7 | 50.16 (49.91-50.40) | 163,840 | +0.02 ±0.33 | +0.29 ±0.36 | 6.4% | 0.046 (0.046) | level |
| apc (C), b0-15 | 50.07 (49.90-50.24) | 327,680 | +0.10 ±0.23 | +0.05 ±0.25 | 6.2% | 0.048 (0.047) | level |
| apk (K), b0-15 | 50.06 (49.92-50.21) | 327,680 | +0.06 ±0.20 | +0.07 ±0.21 | 4.4% | 0.047 (0.047) | level |
| apc2 (C+K), b0-15 | 50.09 (49.90-50.28) | 327,680 | +0.21 ±0.25 | -0.03 ±0.28 | 7.4% | 0.047 (0.047) | level |

- G: the gathers rarely wait on an unseen ally. Its branch runs in about one game in ten but changes 0.4% of games.
- C, K and both together each change 4-7% of games, and the changes cancel out: every pooled read is within
  ±0.1 of zero. C's first eight batches read +0.10 (apc) and +0.16 (apgc); its next eight read +0.05.
- Fuel: level everywhere (the tile is decoded only where these branches ask for it).

Verdict: none of them is worth merging. It confirms the comms round's finding: allies relevant to a decision now
are mostly in sight already, and the crew count was the one fact the claim got wrong.

## Where a bigger gain would have to come from

It would not come from patching existing radius tests. It would need new behaviour that uses a picture of the
whole team: where champions stand before fights (staying within reach of each other on the enemy side, which the
live table in `../comms/README.md` points at), or what allies have seen (clears, enemy sightings), which needs
more bits than a tile slot. Both are fight or retreat matters, so the local bodies would over-reward them (see
`../fishfight/`); they would need mechanism metrics and a live read.

## Files

- Patches against `variants/chy18-cm2k3`: `chy18-{apg,apc,apgc,apk,apc2}.patch`.
- `p1.sh`, `p2.sh`: the gate chains; `report.py`: the pooled read (from `../chyport`); `reads/`: its outputs.
- Gate logs `~/tmp-offload/diverse/gate-logs/fgate-chy18-ap*--chy18-cm2k3*-fuel200000-batch.json`; runs
  `replays/ab/fbe501-chy18-{ap*,cm2k3}-{Flp4,Mt3q}-m2560b0NN-fuel200000`.
