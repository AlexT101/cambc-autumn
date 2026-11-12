# Stacking today's small gains on charybdis (combo, 2026-11-12)

The user asked: "try combining positive variants like 50.1 changes together to see if they have amplified effect". Base and
REF: `variants/charybdis-cb9f86d` (= bots/charybdis, CHANGES 517). Results are also in [EXPERIMENTS.md](../../EXPERIMENTS.md),
under "Stacking today's small gains".

**Answer: the gains do not amplify. They add, or they fail to hold up on fresh maps.** Comms and psafe-a stack
additively (+0.27 at 100k). gp-race and the ally-position consumers were worth about nothing on maps they had not
been picked on, so adding them only adds noise, and at 100k gp-race also adds out-of-fuel turns.

## Parts

| tag | change | source | its read when picked |
|---|---|---|---|
| cm | comms slots, cm2-k3 (crew count from claim slots, told cell centres) | `../chyport/chy18-cm2k3.patch` | +0.30 at 100k on chy-draft18 |
| gp | gp-race: gold priced against the gem race in standings (tributed + carried) | `../gemprice/patches/gp-race.patch` | +0.20 at 200k on chy18-cm2k3 |
| ck | ally-position consumers C + K: an unseen free ally counts for crew availability, and an unseen claimer counts in the crew, by its told tile | `../allypos/chy18-apc2.patch` | +0.09 at 200k on chy18-cm2k3 |
| ps | psafe-a: a Prism holding the winning bag heals at home before the channel when the enemy cannot win first (added at the coordinator's request) | `../prismsafe/psafe-a.patch` | +0.17 at 200k, ~+0.25 at 100k |

Left out: the chynudge draft nudge (per-opponent; the user said "probably remove this"), and G of allypos (the
siege and Monolith gathers), which changed 0.4% of games.

Porting: cm's `main.cc` hunk lands on 516's `sight_pos()` test. That `moved` only decides the turn-end vision
refresh, which is 516's own meaning, so the port is exact. gp and ps share `bank.cc`, `bot_parts.h` and `params.h`
but touch different functions. ps refuses the tribute in `can_tribute_safely` and reads its own `World::enemy_rate`;
gp prices gold through `gems_share` and the mid-game hump. All the patches applied without conflicts.

Variants, each `variants/charybdis-cb9f86d` plus the parts named. Patches against cb9f86d are in this directory:

| variant | parts |
|---|---|
| `cbx-cm` | cm |
| `cbx-gp` | gp |
| `cbx-cmgp` | cm + gp |
| `cbx-cmck` | cm + ck (ck needs cm's slots) |
| `cbx-cmgpck` | cm + gp + ck |
| `cbx-ps` | ps (= `psafe-a`, frozen) |
| `cbx-cmps` | cm + ps |
| `cbx-allps` | cm + gp + ck + ps |

## Held-out maps

The parts were picked on reads from pool batches 0-15 (gp and ck, at 200k), 32-50 (cm, at 100k), and 0-9 and 16-19
(ps). A stack picked from those reads is biased on those maps, so:
- The 200k screen ran on batches 16-31, which no cm, gp or ck arm had played. Batches 16-19 overlap ps's 200k read,
  but ps was not in the 200k screen.
- The 100k read ran on batches 51-62. Batches 51-52 had never been played, and batches 53-62 are new maps grown for
  this test (mapgen seeds 2425000-2425099, `--mix ladder-v2`, 25,245 maps added; the pool now holds 163,234 maps,
  so batches 0-62 are whole). No gate had played any of these maps.

## Results

`tools/fgate.py CAND variants/charybdis-cb9f86d --first-batch J --max-batches N --ci 0`, unmetered Flp4 and Mt3q
bodies, both sides, fastrunner. The 200k rows ran at `--fuel 200000`. In the table, "OOF" is out-of-fuel turns a game
(REF in brackets).

Results against charybdis-cb9f86d:

| arm | fuel, batches | win% (95% CI) | games | Fish | Mite | OOF | verdict |
|---|---|---|---|---|---|---|---|
| cbx-cm | 200k, 16-31 | 50.22 (50.01-50.43) | 327,680 | +0.27 ±0.28 | +0.16 ±0.31 | 0.052 (0.053) | ZONE |
| cbx-gp | 200k, 16-31 | 50.12 (49.90-50.34) | 327,680 | +0.13 ±0.29 | +0.12 ±0.32 | 0.055 (0.053) | ZONE |
| cbx-cmgp | 200k, 16-31 | 50.16 (49.94-50.39) | 327,680 | +0.15 ±0.30 | +0.18 ±0.33 | 0.056 (0.053) | ZONE |
| cbx-cmck | 200k, 16-31 | 50.21 (49.99-50.42) | 327,680 | +0.23 ±0.28 | +0.19 ±0.32 | 0.053 (0.053) | ZONE |
| cbx-cmgpck | 200k, 16-31 | 50.25 (50.03-50.47) | 327,680 | +0.19 ±0.30 | +0.30 ±0.33 | 0.056 (0.053) | ZONE |
| cbx-cm | 100k, 51-62 | 50.08 (49.82-50.33) | 245,760 | +0.07 ±0.35 | +0.09 ±0.38 | 6.43 (6.43) | level (low LLR +2.98, high -8.01) |
| cbx-gp | 100k, 51-62 | 49.94 (49.67-50.22) | 245,760 | -0.19 ±0.37 | +0.07 ±0.40 | 7.05 (6.43) | level, no gain |
| cbx-cmgp | 100k, 51-62 | 50.17 (49.89-50.45) | 245,760 | +0.06 ±0.38 | +0.28 ±0.41 | 7.03 (6.43) | ZONE-low (low +3.63) |
| cbx-cmck | 100k, 51-62 | 49.92 (49.65-50.18) | 245,760 | -0.02 ±0.36 | -0.14 ±0.39 | 6.50 (6.43) | level, no gain |
| cbx-cmgpck | 100k, 51-62 | 49.94 (49.66-50.22) | 245,760 | -0.22 ±0.38 | +0.10 ±0.41 | 7.10 (6.43) | level, no gain |
| cbx-ps | 100k, 51-62 | 50.17 (49.99-50.36) | 245,760 | +0.07 ±0.25 | +0.28 ±0.26 | 6.52 (6.43) | ZONE (low +8.72, high -13.09) |
| **cbx-cmps** | 100k, 51-62 | **50.27 (50.01-50.53)** | 245,760 | +0.38 ±0.35 | +0.16 ±0.38 | 6.53 (6.43) | **ZONE** (low +5.68, high -5.04) |
| cbx-allps | 100k, 51-62 | 50.16 (49.88-50.43) | 245,760 | +0.10 ±0.38 | +0.21 ±0.40 | 7.16 (6.43) | ZONE-low (low +3.53) |

No failed games and no early losses in any run.

### Additivity, paired on the same maps (`additive.py`; points, 95% CI)

| contrast | 200k (40,960 maps) | 100k (30,720 maps) |
|---|---|---|
| cm + gp + ck, observed | +0.25 ±0.22 | -0.06 ±0.28 |
| ... minus the sum of its parts (all − gp − (cm+ck)) | -0.08 ±0.29 | +0.08 ±0.37 |
| ... minus the best single (all − cm) | +0.03 ±0.22 | -0.14 ±0.28 |
| gp given cm (cm+gp − cm) | -0.06 ±0.22 | +0.09 ±0.28 |
| ck given cm (cm+ck − cm) | -0.01 ±0.18 | -0.16 ±0.24 |
| ck given cm+gp | +0.08 ±0.19 | -0.23 ±0.24 |
| cm × gp interaction | -0.18 ±0.29 | +0.15 ±0.36 |
| ps given cm (cm+ps − cm) | | +0.19 ±0.18 |
| ps given cm+gp+ck | | +0.21 ±0.19 |
| cm × ps interaction | | +0.02 ±0.25 |
| cm+ps − ps (cm on top of ps) | | +0.10 ±0.25 |

- **No amplification.** Every interaction is within noise of zero, with no consistent sign across the two budgets.
  When the parts hold up, they add: ps contributes +0.19 to +0.21 whatever it is stacked on, its own +0.17 alone.
- **The 50.1 parts shrank on held-out maps.** gp: +0.20 where it was picked; on held-out maps +0.12 alone and -0.06
  given cm at 200k, then -0.06 and +0.09 at 100k. ck: +0.09 where picked, then -0.01 and -0.16 given cm. That is the
  regression to the mean expected of arms picked on their reads. cm on 517 read +0.22 at 200k and +0.08 at 100k,
  against +0.30 at 100k on chy-draft18. 517's lethal-model fixes may already cover some of what the crew count
  bought, or this may be noise: the two reads overlap.
- **gp costs fuel at 100k.** Every arm with gp runs about 0.6 more out-of-fuel turns a game, about 10% (gp 7.05,
  cm+gp 7.03, all 7.10, all+ps 7.16, against 6.43). Without gp, the arms are within 0.1. At 200k, out-of-fuel turns
  are too rare to show it. Its pricing reads (`gems_share`, `prices`) are cached per bag key; the new per-turn work
  is `note_standing`, and `standing()` decodes the comms bags. Whether the extra turns come from that compute or from
  play that runs closer to the budget was not measured (`bench.py` would tell). gp's earlier gate ran only at 200k,
  so this cost was never visible there.

## Recommendation

- **Stack: cbx-cmps (comms + psafe-a)**, 50.27 (50.01-50.53) at 100k on 30,720 held-out maps. That is a ZONE (low
  SPRT at H1, high at H0): confidently above 50, below 50.5. Its out-of-fuel turns are level (+0.10). Both parts have
  a stated mechanism, and they add without interacting. Taking it is a judgement call under the zone rule, with the
  usual live pairing before charybdis moves.
- **Leave out ck.** It never read positive on held-out maps (-0.01 at 200k, -0.16 at 100k, given cm).
- **Leave out gp-race for now.** About +0.0 on held-out maps, with ~10% more out-of-fuel turns at 100k. If the
  pricing idea is wanted, find and cut its fuel cost first, then re-read it at 100k on maps it has not played.
- Batches 51-62 have now been played by these arms. Pool batches 63 and later do not exist yet. Grow more maps, on
  seeds clear of 2425000-2425099, for any further held-out read.

## Files

- `p1.sh` (200k screen and map growth), `p2.sh` (100k: cm, all), `p3.sh` (100k: ps arms), `p4.sh` (100k: gp, cm+gp,
  cm+ck). Logs and mapgen output are in `~/tmp-offload/combo/`.
- `additive.py REF BATCHES [--fuel N] [--arms a,b,..]`: the paired contrasts. `reads/` holds its outputs and
  `../chyport/report.py`'s pooled read for each arm.
- Gate logs: `~/tmp-offload/diverse/gate-logs/fgate-cbx-*--charybdis-cb9f86d*-batch.json`. Runs:
  `replays/ab/fbe501-cbx-*-{Flp4,Mt3q}-m2560b0{16..31}-fuel200000` and `-m2560b0{51..62}`.
