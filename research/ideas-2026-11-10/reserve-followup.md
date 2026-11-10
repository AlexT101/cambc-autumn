# Farm-reserve lead: read-only coverage audit, 2026-11-10

The v106 Fish lead is worth retaining as an unresolved live lead. It is not already incorporated in Ocean498, and the precise reserve-only change on current498 has not been tested by the records inspected. Existing older tests do cover a closely related bundle extensively, so repeating that old sweep would duplicate work.

## What v106 actually contains

Scheduler gate record `/home/ubuntu/tmp-offload/handoff/sched/gates.jsonl` identifies v106 as `live-wd-rs8`, built from workspace `build/live-wd-rs8-1794286616`. Its `economy/farm.cc`, `main.cc` and `util.h` match the frozen variant byte-for-byte. Against v105's `live-wd-fsnh`, those are the only changed source files:

- farm.cc subtracts 8000 from `after_loop`, releasing fuel for more farm-loop evaluation. It does not set the reserve to 8k or raise the total budget. `end_reserve` stays 10000. The first-turn opening reserve path is unchanged.
- main.cc/util.h also add `q1`: while turn-end warm-up runs, remember its round and make every later `fuel_ok` fail if that coroutine resumes in another round. This is a queue-recovery guard with global check overhead.

Thus v106 versus v105 changes reserve, q1 and the priority-mask key. v106 versus v107 shares the new mask, but changes reserve, q1 AND camp shielding. The live lead cannot be assigned solely to reserve from either comparison. Source provenance confirms q1 is genuinely in the prepared submission workspace, not merely a later variant edit.

## Existing tests

`research/EXPERIMENTS.md` “Farm-loop reserve sweep on ocean-16d6f78 + q1”, terminal JSONs in `~/tmp-offload/diverse/gate-logs/`, and `research/fuel-2026-11-10-third/results/farm-handoff.md` agree:

| Old arm versus ocean-16d6f78 | Fresh delta, points | Ladder delta | Coverage |
|---|---:|---:|---|
| q1+8k slack (`oc16-rs8`) | +0.150±0.250 | +0.554±0.252 | 317 blocks, 40,576 fresh paired units; NARROWED/ZONE |
| q1+12k slack | +0.208±0.250 | +0.468±0.255 | 322 blocks; NARROWED/ZONE |
| q1+2k /4k /6k | −0.268 /−0.04 /−0.031, each±0.25 | positive | Already screened to narrow width |
| q1+16k /20k /24k | +0.05±0.52 /−0.43±0.56 /−0.12±0.60 | positive | Partial runs stopped by original owner; more OOF |

The 8k arm's Fish split is **fresh+0.014±0.339**, ladder+0.642±0.349. Its fresh Mite split is+0.286±0.362. No old arm cleared the configured fresh+0.5 acceptance threshold. These are accumulated sequential-gate summaries, not independent confirmations or estimates of the live-r2 gain. The larger slack arms subtract more reserve; the old handoff's phrase “larger reserves” should not be interpreted literally.

The separate `oc16-q1` gate used older Flp/Mt3p bodies: fresh−0.082±0.250 at 50 blocks, ladder+0.020±0.244. This does not isolate q1 on the rs8 gate's exact Flp4/Mt3q conditions. `ocean-16d6f78` also differs from live v105 in 11 source files, so old local versus live evidence is not an exact base match.

The third fuel campaign tested `oc-third-queueguard` against frozen497: only main.cc/util.h differ. Its 1024-game real-budget bench had OOF 8671→8772(+1.16%, CI−1.94..+4.68), shortcuts+0.84%, mean fuel+0.28%. The owner dropped it for no OOF/shortcut benefit. This is a real-budget mechanism/cost screen, not a fresh Fish/Mite strength gate; do not reinterpret it as a conclusive strength rejection. The 100M 95/96 identity result retained the documented preparation-sensitive divergence caveat.

## Current coverage and remaining question

`oc-campsh-498/src/economy/farm.cc` is byte-identical to v105's file: no loop_slack subtraction. Its util.h has no queue_round guard and retains end_reserve10000; the current working Ocean farm file also has the unchanged reserve formula. CHANGES495–497 improve records, queues, tail guards, support, combat and geometry costs; they explicitly do not ship the reserve reduction or q1. Source equality and the third-fuel report agree. Those savings can change how often this reserve binds, so the old sweep cannot be assumed to transfer unchanged.

No reserve arm appears in the current local jobs.txt. This audit made no source, dataset, queue, submission or pin changes and did not contact the prior owner.

## Authorized current-base experiment

Three arms complete the minimum full factorial against the same frozen `oc-campsh-498` reference:

- `oc-rs8-498`: subtract 8000 from `after_loop`; no other source change.
- `oc-q1-498`: the exact q1 helper and queue wrapper from submitted v106, rebased onto 498; no reserve change. The original local-static helper form is retained. The third-fuel guard bench used an equivalent inline-global form, so it is supporting mechanism evidence rather than an identical-source strength gate.
- `oc-rs8q1-498`: exactly the union of those source changes.

This separates reserve, guard, and their interaction on the current base. All use normal 100k play fuel, unchanged 10M draft allowance, release/native 5.0.1, own drafts, fixed Flp4/Mt3q, and the standard paired fresh-map gate. Changed policy is intentional; these are not claimed as fuel-only optimisations. The minimum after-loop estimate before subtraction is 26,400, so subtracting 8,000 cannot underflow. The opening branch keeps its original reserve.

The reference includes all 495–497 fuel changes and 498 shielding. Its source seal is `d0a0755075bf4010dc1ac96e7b209aafd3791ba1a8bc1c3b625d56e55f38a23e`. Per-arm seals live in `reserve-tools/sources.json`; `run_gate.py` refuses changed sources. Artifact `candidate-manifests.json` records every source file and `source-factorial-check.json` verifies exact factorial differences and own drafts.

Queue admission follows all already-admitted behavior work, including ward and livelock gates, ahead of pending training. No live promotion or merge is authorized by these provisional live totals; any promising normal-fuel gain requires appropriate fresh unused-map confirmation on the then-current frozen base. Ward outcome ownership continues independently.

## Preparation checks

All three final release builds pass. Four maps (`00ambush`, `00breadcrumbs`, `00great-wall`, `00lanes`), both sides, against each of Flp4/Mt3q give 64 smoke conditions across the reference and three arms. All have normal fuel metadata, zero game errors, early losses and draft handoff failures. All 64 replays pass extractor hard validation; every arm retains both ordered drafts in all 16 paired cells. These deterministic smoke cells are mechanism checks, not independent strength evidence.

The pure reserve and combined arms change events in all 16 cells, first differing at rounds 3–55. Guard-only changes seven cells, at rounds 13–542, and leaves nine event streams identical. This shows the policies can affect the actual games; it does not distinguish the guard's check overhead from successful queue recovery. Out-of-fuel counts across the 16 candidate-side games are base 98, reserve 86, guard 95, bundle 86. Changed trajectories mean these counts are not a cost benchmark or win-rate result.

Artifacts in `~/tmp-offload/reserve-coverage-2026-11-10/`: `verified-smokes.json`, `smoke-analysis/`, `mechanism-checks.json`, `mechanism-summary.json`, `source-factorial-check.json`, and `patch-reproduction.json`. The two patches reconstruct each sealed arm exactly from frozen 498, including their union. `fgate --no-run` reads zero pre-existing reserve-arm blocks. No old opponent cache/body is renamed or modified.

To reconstruct an absent arm, copy `variants/oc-campsh-498` with `./copybot` to its named variant, then apply `reserve-tools/slack8k.patch`, `reserve-tools/queueguard.patch`, or both with `git apply --directory=bots/variants/ARM`. Never overwrite an existing sealed variant. `python3 research/ideas-2026-11-10/reserve-tools/run_gate.py ARM --jobs 4` verifies the source and runs its normal-fuel gate. The queue command manifest is `queue-commands.json` in the artifact directory.
