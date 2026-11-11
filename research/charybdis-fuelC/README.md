# Charybdis fuel C — 2026-11-11

Worked alone in `/home/ubuntu/wt/charybdis-fuelC`, branch `charybdis-fuelC-20261111`,
from `1178688e9` (`origin/charybdis-20261111`). The user requested closure
before further ideas. **The 10% exhaustion target was not reached.** The user subsequently
approved keeping these exact optimizations after reviewing the inconclusive real-budget
results, and authorized pushing this branch.

The final source is `bots/charybdis`, frozen as `variants/chary-fuelC-final`;
`variants/chary-fuelC-combo` is the identical source used for final measurements.
The reference is `variants/chary-fuelC-base`, frozen before this pass. Earlier
Charybdis fuel passes are preserved. Source fingerprints are in `results/source-hashes.json`.

## Changes kept

- An idle holder's incoming damage ceiling can prove survival before simulation.
  Otherwise simulate only enemy turns and the holder's shield expiry; the holder
  never attacks or casts. Enemy casts, arrivals, Ren reflection and deaths retain
  the original arithmetic and order.
- Quiet basic-attack intervals involving Ren apply nonlethal damage and reflection
  directly. Shields, casts, stuns and deaths return to the existing simulator.
- Capture threat caches use a separate Safety generation. A refresh that finds no
  death or new camp stun preserves the fixed beliefs and retained camp model used
  by the idle simulation. Observations, reconstruction and invalidation still
  invalidate it. Other Safety consumers retain their original generation.
- Ren's harmless groups bypass geometry and sorting. Once a mixed group's strikers
  are gone, the remaining cluster clears are summed directly. A positive float
  residual retains the old extra attack. The next-death search stops at one turn,
  its minimum possible answer.
- Dash ranking skips landing-harm checks when the complete score cannot enter the
  three retained landings. Equal scores preserve the original board order.

No draft, strategic constant, fuel gate or reserve changed.

## Results

All games use cambc 5.0.1 and the native fast runner, jobs/threads 86, sharing the
machine-wide slot pool. Bench games are debug builds, so shortcuts are recorded.
Both arms use their own drafts except the explicitly matched test/coverage drafts.

| Test | Games | Exhausted turns REF → CAND | Shortcuts REF → CAND |
|---|---:|---:|---:|
| Development screen | 1,024 | 7,018 → 6,452 (-8.06%) | 285,754 → 277,519 (-2.88%) |
| Reserved fresh confirmation | 4,096 | 27,399 → 26,438 (**-3.51%**) | 1,106,126 → 1,090,337 (**-1.43%**) |
| Standard release A/B | 1,280 | 7,340 → 7,379 (+0.53%) | compiled out |

Fresh confirmation 95% intervals: exhaustion **-7.08% to +0.22%**, shortcuts
**-3.12% to +0.13%**. Both include zero. Per-turn changes are -3.43% and -1.35%.
Mean play fuel changes -0.12%; after-round-one means are 47,083 → 47,027.
The release win rate is 50.31% (95% 47.6–53.0). There are no failed games,
broken/capped drafts or losses by round five in the final bench or release A/B.
These results do not establish a reliable real-budget improvement.

OOF counts come from the runner's complete `Out of fuel: A ... B ...` lines.
Bench inference and stdout recovery markers miss consecutive exhausted turns.
Shortcuts count events, excluding `out-of-fuel` and malformed `SLOT` labels.
The 10,000-resample paired bootstrap resamples maps with both sides together;
it does not treat the two sides as independent observations. Full paired counts,
CIs and label totals are in `results/confirm.json`.

Nine reference stdout streams and six candidate streams reach the 1 MiB cap.
Their union is ten paired games; recorded shortcuts are therefore censored there.
The complete runner OOF counts are unaffected. `stdout-sensitivity.json` records
the shortcut comparison with these pairs omitted; `stdout-audit.json` lists them.

The screen uses fresh ladder-v2 seeds 3711100–3711101 (512 maps). Confirmation
uses reserved seeds 3711102–3711109 (2,048 maps), not used for candidate selection.
Each seed generates 256 maps. Manifests are under `tools/`. Standard release uses
128 ladder + 256 gen + 256 gen-s1 maps, both sides.

## Identity and conditional checks

**232/232 replays byte-identical at 100M**, with no exceptions or diagnostic
changes: 52 wide own-draft, 52 wide test-draft, 128 forced-composition coverage.
All 13 champion bodies occur in coverage (Cassi and Issac share a draft pick).
Ren is in every forced composition; the other picks cycle through every kit.
Coverage includes 40/64/100-square stress maps with 112/208/352-member groups,
plus ordinary ladder/generated maps and 32 screen maps. This exercises harmless
and mixed clears, reflection, shields, heals, stuns, dashes and Prism holds.

The actual-source native oracle compares **1,000,000 idle fights, 1,000,000 team
fights and 1,000,000 camp clears**, with zero mismatches. It includes shield expiry,
arrival delays, reflection, linked enemies, camp hits and positive float residuals;
team fights also compare the bounded simulator's loss/self-fall verdicts.
It is compiled with contraction disabled and undefined-behaviour sanitization.
Final identity summaries and oracle output are in `results/`.

On matching wide own-draft turns after round one, the bundle saves 21 mean fuel
and 76 on baseline turns of at least 95k; over-100k turns fall 6,323 → 6,307.
Conditional coverage mean falls 46,498 → 46,390 and over-100k turns 14,484 → 14,351.
These small exact savings do not imply a 10% real-budget exhaustion reduction.

## Lessons and rejected work

Read the rules, tool guide, FUEL-GATES, previous Charybdis passes, fuel campaigns
6/7/12/13 and the 2026-11-10 passes before and during implementation. Their warnings
held: added bookkeeping often costs more than recomputation, broad survival bounds
rarely settle extra fights, and a promising small screen can regress on fresh maps.

The initial fuelprof run was not a reliable exhausted-turn census. The sixth pass
explains that its `oof` class mostly contains double-budget first turns, and source
attribution can include impossible functions. Do not interpret the recorded
`prof-release-oof.json` as the cost distribution of actual exhausted turns.

`results/identity.csv` records every completed wide comparison; savings there are
on matching games and exclude round one. Variant names below have prefix
`variants/chary-fuelC-`. Candidates are experiments, not independent replications.

| Candidate / idea | Result and disposition |
|---|---|
| idle | Idle survival bound; exact, small saving; retained. |
| ren | Single-pair quiet reflection loop; only a few fuel saved; superseded. |
| core | Direct turn-window answers and leaner single-target hurt; heavy turns dearer; dropped. |
| farm | Enable Ren harmless-group pre-prunes; 49/52 own identities, dearer; dropped. |
| clusters | Harmless Ren clears with float-residual correction; exact; retained. |
| windows | Finer World order-observation generation; about 297 more fuel on heavy turns; dropped. |
| hold / hold2 | Hold-cache generation, with/without windows; hold2 exact, retained. Its 1,024-game OOF screen was -5.76%. |
| altar | Static altar tiles outside all monster ranges; 51/52 own identities, no useful net saving; dropped. |
| dash | Full-score landing filter; small exact saving relative to its parent; retained alone. |
| duel | Entire Ren duel specialization; too few calls, about 15 heavy fuel saved; dropped. |
| campbound | Static camp-range zero test with ally-fall exception; extra checks made heavy turns dearer; dropped. |
| copy / copy2 | SIMD fighter copies, returning/by-reference; both substantially dearer on heavy turns; dropped. |
| caps / caps2 | Tighter reflection/cast/arrival damage ceilings; exact but dearer; dropped. |
| reflect | Cache reflected_clear; nearly no reuse because its callers mainly run on the opening turn; dropped. |
| idle2 | Enemy-only idle simulation; exact; retained. |
| quiet | General quiet reflection interval; exact; retained. |
| tail | Remaining harmless members and one-turn next-death exit; exact; retained. Screen OOF -4.40%, shortcuts -2.27%. |
| combo | Final retained bundle; results above. |
| gank | Prove a team finishes a lone non-shielder before any ally can fall; oracle/identity pass, heavy turns dearer; dropped. |

Remaining leads: avoid `prism_hold_tiles` at callers whose routes cannot reach the
hold; investigate the escape-plan work inside `dash_away`; inspect camp-free
`altars_sealed` access without rebuilding a static proof board. None is claimed
as a gain. Further work must reduce actual expensive operations rather than add
more generic cache keys or broad simulation bounds. The 10% target remains open.

## Reproduction

Activate `/home/ubuntu/venv/bin/activate`, then set:

```sh
export CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner
export FASTRUNNER_MODE=native
python tools/fuel/bench.py run variants/chary-fuelC-final --opp variants/chary-fuelC-base --set wide --jobs 86 --out replays/fuel/check.json
# Add --test-draft for ladder compositions; --fuel 0 for the real budget.
python tools/fuel/bench.py compare BASE.json CAND.json
python research/charybdis-fuelC/tools/paired.py BASE.json CAND.json BASE-run-batch.log CAND-run-batch.log OUT.json
python tools/pooled.py 1 -- python research/charybdis-fuelC/tools/check_sim.py bots/variants/chary-fuelC-base bots/charybdis
```

Generate fresh maps with `tools/mapgen/mapgen.mjs suite --mix ladder-v2 --seed S
--out DIR`; large groups with `research/hyperion/fuel-campaign-13/stress_maps.mjs`.
For conditional tests, copy both bots and rewrite both test composition tables with
`tools/draftlab/test_comps.py --prior research/charybdis-fuelC/tools/coverage-prior.json
--bot BOT`, then bench with `--test-draft --maps $(cat research/charybdis-fuelC/tools/maps-coverage.txt)`.
Raw JSONs: `replays/fuel/fuelC/`; runner logs/bundles:
`replays/fuel/games/<result-stem>/`; release: `replays/ab/fuelC-combo-standard/`.
