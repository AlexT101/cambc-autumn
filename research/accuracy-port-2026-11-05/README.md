# Initial accuracy port from astraeus_wip

Candidate: `work/astraeus-accuracy-port`, based on astraeus at
`0f7830e1353b69133aeba1d4ad73a57602446332`. Tested in isolation, then accepted
for main as CHANGES 410 at the user's request.

## Scope

- CHANGES 376: support formation and priority-heal positions may use dead camp tiles;
  live camp occupancy still blocks them. No new formation pathfinding.
- CHANGES 387, selected parts: Willow's camp-finish veto respects reset readiness;
  clear and crew estimates respect shield cooldown after travel; a departing capture
  holder is not counted as covering the group. The passing-camp shield check uses
  the minimum Chebyshev distance to a member's attack range, a conservative travel
  bound, instead of adding wip's stand fields. The main loop uses its existing
  `reach`. No weighted upkeep or Prospector-income changes.
- CHANGES 385 with CHANGES 390's lock-timing corrections: reset and hit a surviving
  lock, attack after melee arrival, and submit immediately after the final ranged
  hit. Current banking/hop callers price these actions. No new altar route fields,
  handoff calculations, or winning-race changes.
- CHANGES 396: forecasts select the learned emblem that shopping selects, using
  the hypothetical inventory when supplied. Existing price/quote caches remain.
- CHANGES 372, deadline only: use the planned capture share with remainder and
  Prospector, capped by crew size for a crew proposal, for the last tribute's time.
  Existing farm pruning and caches remain.

No new fuel gates. Mid-turn camp-kill refresh, broad geometry/simulation changes,
Capture-history tracking, Collectors valuation, and shop-cache invalidation are deferred.

## Comparison

Baseline is a frozen source copy of astraeus at the base commit. Both directories
have `test_draft = false`. `inputs.json` records the map-generator hashes: the
primary checkout's current generator supports the ladder mix and was used read-only.

```sh
node /home/ubuntu/cambc-autumn/tools/mapgen/mapgen.mjs suite \
  --mix ladder --seed 247001-247040 --jobs 16 \
  --out '/tmp/astraeus-accuracy-port/maps/accuracy-247/{seed}'

CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner \
FASTRUNNER_MODE=native CAMBC_SLOTS=40 \
py tools/ab.py astraeus variants/astraeus-pre-accuracy --no-test-draft \
  --suites /tmp/astraeus-accuracy-port/maps/accuracy-247-merged \
  --name accuracy-port-247
```

The 40 suites contain 256 maps each; the merged directory contains symlinks and
combined metadata. 10,240 maps, both sides: 20,480 games. Default real fuel budget.
Both standalone `cambc build` commands passed; `git diff --check` passed.

## Results

20,480/20,480 games finished, no failed matches. Candidate won 10,215 and lost
10,265: **49.88%**, 95% Wilson CI **49.19-50.56%**. Run wall time 288.7 seconds.

| Metric | Candidate | Baseline | Change |
|---|---:|---:|---:|
| Out-of-fuel turns | 145,848 | 146,230 | -0.26% |
| Farm partial evaluations | 2,487,699 | 2,457,358 | +1.23% |

| Camp groups | Games | Candidate win % | OOF candidate / baseline | Farm partial candidate / baseline |
|---|---:|---:|---:|---:|
| <12 | 3,722 | 49.92 | 30,542 / 30,138 | 176,977 / 174,666 |
| 12-23 | 9,710 | 49.79 | 63,684 / 64,054 | 864,239 / 846,317 |
| 24-47 | 6,822 | 50.13 | 47,474 / 47,609 | 1,343,406 / 1,332,649 |
| 48+ | 226 | 45.13 | 4,148 / 4,429 | 103,077 / 103,726 |

Level overall, with essentially unchanged aggregate run-outs and 1.23% more farm
partial evaluations. The 48+ group bucket has only 226 games; its 45.13% result is
too small a sample to establish a regression. These are observed game counts,
not a replay-identical instruction-cost measurement. Four candidate team stdout
files and five baseline files reached the engine's 1 MiB cap, so log counts may
understate those games' totals. The independently counted OOF totals match ab.py.

The bundle was accepted for main after this A/B. The complete source
was unchanged during the run and matches the frozen candidate used by ab.py.

`summary.json` / `summary.md` are ab.py's results. `fuel-and-groups.json` is the
additional replay analysis, reproduced by:

```sh
python3 research/accuracy-port-2026-11-05/summarize.py \
  replays/batch-20261105-151229-ab-accuracy-port-247-accuracy-247-merged \
  maps/accuracy-247-merged research/accuracy-port-2026-11-05/fuel-and-groups.json
```
