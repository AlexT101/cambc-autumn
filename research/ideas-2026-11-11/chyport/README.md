# Comms slots on charybdis, and charybdis against the bodies (2026-11-11)

Questions: does ocean's comms change (CHANGES 507-ocean, `comms/cm2-k3.patch`) carry over to charybdis, and is
charybdis ahead of ocean against the Fish and Mite bodies, not only in the mirror?

Answers: charybdis is ahead of ocean 506 against the bodies by 4.7 points, on both. The comms change is worth
about +0.3 points on charybdis, confidently between 50 and 50.5 (ZONE), with out-of-fuel turns level.

## The port

`cm2-k3.patch` applies to `variants/chy-draft18` unchanged (one hunk offset), and the six files it touches end
equal to `variants/oc-comms-507`'s where charybdis had not changed them. One consumer is charybdis's own:
`recent_tile` (`economy/capture.cc`), which tells an ally whether to leave a cleared gem group for a Prism it
cannot see, reads `comms::told_ally` and takes the tile to be within 2 steps. With slots the told tile is a cell
centre (cell side median 6), there on about 77% of turns in every game, where `comms_ally`'s record came once
every few rounds and only while a healer lived. Two variants, both on `chy-draft18`:

| variant | patch | `recent_tile` |
|---|---|---|
| `variants/chy18-cm2k3` | `chy18-cm2k3.patch` | reads the slot's cell, with the slack from the cell: `comms::told_error()`, half a cell side |
| `variants/chy18-cm2k3n` | `chy18-cm2k3n.patch` | does not read slot cells (seen tiles only), so the leave gets no told tile at all |

## Results

`tools/fgate.py`, 100k fuel, fresh `--mix ladder-v2` maps nobody had played, both sides, unmetered Flp4 / Mt3q
bodies. Pool batches 32-34, then 38-50 of the pool grown for this (mapgen seeds 2417384-2417543; the pool now
holds 137,989 maps, 53 whole batches, 51 and 52 unplayed). `report.py CAND REF 32-34,38-50` pools the two
segments.

Results against chy-draft18:

| read | win% (95% CI) | games | Fish | Mite | OOF turns a game (base) | outcome |
|---|---|---|---|---|---|---|
| chy18-cm2k3, batches 32-34 | 50.60 (50.09-51.11) | 61,440 | +0.44 ±0.69 | +0.76 ±0.75 | 6.05 (6.09) | undecided |
| chy18-cm2k3, batches 38-50 | 50.23 (49.99-50.48) | 266,240 | +0.36 ±0.34 | +0.11 ±0.37 | 6.12 (6.15) | NARROWED (ZONE crossed) |
| **chy18-cm2k3, all 16** | **50.30 (50.08-50.53)** | 327,680 | +0.37 ±0.30 | +0.24 ±0.33 | 6.11 (6.14) | LLR low +8.2, high -6.2: ZONE |
| chy18-cm2k3n, batches 32-34 | 50.76 (50.25-51.27) | 61,440 | +0.50 ±0.69 | +1.02 ±0.76 | 6.07 (6.09) | undecided |
| chy18-cm2k3n, batches 38-50 | 50.19 (49.94-50.44) | 266,240 | +0.32 ±0.34 | +0.06 ±0.36 | 6.13 (6.15) | NARROWED (ZONE crossed) |
| chy18-cm2k3n, all 16 | 50.30 (50.08-50.52) | 327,680 | +0.35 ±0.30 | +0.24 ±0.33 | 6.12 (6.14) | LLR low +8.2, high -6.3: ZONE |
| chy18-cm2k3 against chy18-cm2k3n, all 16 | 50.01 (49.93-50.08) | 327,680 | +0.02 ±0.11 | -0.01 ±0.12 | 6.11 (6.12) | 1.4% of games differ |
| chy18-cm2k3 head to head, own drafts | 49.87 (49.18-50.55) | 20,480 | - | - | 5.48 (5.47) | level |
| chy18-cm2k3n head to head, own drafts | 50.07 (49.38-50.75) | 20,480 | - | - | 5.47 (5.47) | level |

- Both arms: a gain confidently above 50 and confidently below 50.5, the same size as on ocean (+0.16 ±0.14)
  within noise. Fish and Mite both read positive. One-site maps +0.62 ±0.40, multi-site +0.18 ±0.27.
- Out-of-fuel turns are level or slightly lower than chy-draft18's, against both bodies (Fish 6.97 against 7.02,
  Mite 5.25 against 5.25).
- The two arms share their games but for 1.4%: feeding slot cells to the Prism leave changes nothing measurable.
  The gain is the crew count, as on ocean.
- Head to head (suite `~/tmp-offload/chyport/h2h`, mapgen seeds 2417544-2417583, 10,240 maps) is level at ±0.7:
  it cannot see +0.3 and shows no mirror loss.
- The first three batches read +0.6 and +0.8; the thirteen after them +0.2. All sixteen are in the pooled row.

Verdict: zone gain, the same as on ocean; a judgement call. If taken, `chy18-cm2k3` (the leave stays fed, with an
honest slack) and `chy18-cm2k3n` are equal on the evidence.

Results against oc-dfuel-506 (`chy-draft18`, the same gate, batches 32-33):

| read | win% (95% CI) | games | Fish | Mite | OOF turns a game (base) | outcome |
|---|---|---|---|---|---|---|
| chy-draft18 | 54.75 (53.99-55.50) | 40,960 | +4.59 ±1.01 | +4.90 ±1.09 | 6.17 (5.90) | LIVE BAR H1 |

- Against the bodies charybdis wins 81.3% where ocean 506 wins 76.5%: Fish 83.4 against 79.0, Mite 78.9 against
  73.9. One-site maps +3.14 ±1.34, multi-site +5.37 ±0.91.
- The mirror's 60.3% overstates it, as mirrors do, but the gain against the bodies is large and on both.
- Charybdis runs 0.27 more out-of-fuel turns a game than ocean 506 (Fish 7.06 against 6.72, Mite 5.29 against 5.08).

Verdict: charybdis is the stronger bot against the bodies; `chy-draft18` is the base to build on.

Runs: `replays/ab/fbe501-{chy18-cm2k3,chy18-cm2k3n,chy-draft18,dfuel-506}-{Flp4,Mt3q}-m2560b0NN`,
`replays/ab/chyport-h2h-{b,n}`; gate logs `~/tmp-offload/diverse/gate-logs/fgate-chy*-b3{2,8}-batch.json`; scripts
and logs `~/tmp-offload/chyport/`.
