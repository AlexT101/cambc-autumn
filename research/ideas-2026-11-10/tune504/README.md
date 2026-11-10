# One506 economy/crew/shop tune: proposed protocol

Rebased before any heavy work on 2026-11-10 to frozen Ocean 506, including the shipped 505/506 fuel savings. Seeds, sample sizes, statistical rules, review barriers and job IDs are unchanged. The `tune504` directory name is retained for queue compatibility.

**Root approved protocol and implementation; independent code review passed.** No training init, builds, map generation, benchmark or games have run for this proposal. Queue order is both full504 ward gates, then the entire draft17 lab/evaluation, then one exclusive tune8 job. Draft17 completion alone does not start tuning: explicit `draft17-reviewdone` and a base-policy/source check are required. If an approved draft/ward result changes main, hold and obtain a concrete source review/reseal; never silently retarget frozen506.

The sourcewide rescan selects27 continuous price/health/crew parameters, including 8 useful sites absent from params.h. See [inventory and exclusions](INVENTORY.md), [exact ranges](PARAMETERS.md), and machine-readable `parameters.json`/`protocol.json`. Production defaults remain exact in the tuning vehicle before training. Learned models, threat calibration, priority encodings, engine facts and fuel/search budgets are unchanged.

## Why this differs from tune1

Tune1 already trained on10,240 fresh ladder-v2 maps: it was not a ladder-only training mistake. Its19 knobs mixed combat values, retreat/escape geometry, Safety probability and economy; its9-opponent panel included6 Fish/Mite noise bodies and3 other opponents.700 iterations produced806,400 games. Final fresh gate was−0.188±0.250pp (Fish−0.239±0.337; Mite−0.137±0.363), despite ladder+0.539±0.250. NARROWED did not establish a gain or formal rejection. That bundled result cannot identify which constant hurt.

This proposal changes the policy family and fills actual source-local omissions; uses only the current Fish/Mite local body families, equal weight; narrows ranges around defaults; and reduces the gem proxy from25% to 10% with no gold proxy. Win weight .9 keeps the optimization close to the shipping objective while a small tributed-gem margin supplies information in common-result pairs. It is not claimed that this objective change alone fixes tune1. All endpoints are prospectively selected, not chosen after looking at a validation result.

## Training and endpoint

- 100k release fuel, native shared pool; own draft unchanged. Training is selection among perturbed policies, not a fixed-candidate strength claim.200k training could misrank policies whose useful work competes for production fuel. No tune.py fuel changes.
- 40 reserved ladder-v2 mapgen seeds2413000–2413039,10,240 training maps. Generate and hash only after scheduled preflight. Compare content to the standard validation pool and remove collisions before any games, replacing prospectively from reserved later train seeds if needed; seal the exact resulting training list. Record scope, not universal novelty.
- Equal Fish Flp4/Mite Mt3q, noise 1001–1003 (six opponents), outside final gate's noise1–1000. Fixed sources captured before games; no local opponent refits or pin changes. Deliberate ladder-composition opponent bodies versus our own draft.
- 600 iterations ×24 maps ×6 opponents ×8 candidates =691,200 scored games maximum. Each iteration samples maps and a common random side for all±perturbations. Training-map reuse is expected SPSA selection, not claimed new evidence. Four independent sign vectors; inflight1 avoids stale-gradient updates and nested batch overlap. No convergence chasing, time-based extension, automatic next run or checkpoint tournament.
- Scaled-coordinate gains a=.20,A=100,alpha=.602,c=.10,gamma=.101. All 27 floats use explicit ranges; no half-to-double fallback. Export the arithmetic mean of iterates 301–600 (one prespecified endpoint), rounded once to float32 into ordinary source constants. The baseline is frozen506, not the training vehicle.

## Validation and review

Default vehicle must pass both 16-game and52-game100M replay-identity benchmarks against plain506 before training. Measure the vehicle's fuel overhead; identity does not prove identical100k behavior. If identity or material overhead fails, stop for review rather than silently remove knobs. After training, require all 600 iterations with1,152 non-null scores each, no source/config/map drift, and endpoint bounds. Any run error invalidates automatic export; early draft losses remain losses and are reported, not deleted. Exported plain constants must match an applied-value vehicle on the same two 100M identity sets.

The one exported candidate first gets a **200k** fixed-candidate gate against frozen506: standard Flp4/Mt3q, both sides, standard fixed1,024 ladder-v2 maps with noise blocks 1–1000,128 ladder diagnostic maps. `--ci0 --zone-stop --ahead0 --max-seeds1000 --jobs4`. Complete paired cells and zero execution errors required; retain and report draft early-loss counts using established rules. Repeated noise/map units are not distinct unseen maps. Standard three-way sequential boundaries apply; ZONE is a judgment review, not a demonstrated positive95%interval or rejection. At ordinary cap, report UNRESOLVED with no extension.

Report Fish/Mite and map-class splits as supporting interpretation, with post-hoc selection caveat. Any 100k candidate confirmation requires a separate root decision after 200k supports gain. Reserved2413900–2413903 are **not** an automatically scheduled confirmation. No auto merge, live submission, repin or follow-on tune.

The queue wrapper should hash/seal all inputs, refuse existing started/cache identities, log phase events, and stop on failed invariants. Builds and identity checks are scheduled phases within this exclusive job, never parallel prep work outside the queue. The reviewed source transformation and launcher are included here; admission uses `run.py` and the sealed manifest under `localq/rounds/tune8`.

## Preparation checks

Eight lightweight tests pass: exact default source reconstruction, all-range export limited to declared sites, writable map-conditioned aliases and fixed learned headers, drift/invalid-value refusal, committed-main plus policy checks, hold-before-start and frozen-after-start behavior, exactly 600 actual SPSA controller iterations using a fake runner, and an incomplete fake batch failing before its first gradient update. No native games or builds were run by these tests.

Independent review found an unpooled metadata parsing phase in the existing tuner; the isolated wrapper now acquires actual shared capacity and limits parser workers to that allocation, releasing it in `finally`. Identity metadata parsing also reserves one slot. Before training, vehicle overhead above 1% on either release 100M identity set requires review. All build, benchmark and training phases remain scheduled work.


Resource default: only the final candidate gate phase uses `tools/gate_compile_ahead.py`,16 process-isolated compile workers/eightfutureblocks in the shared86 pool. Existing noise bodies are frozen/built under the normal cache locks; no warm/scored games or statistical changes. Its context stops dispatch and drains compiles as soon as the actual gate phase ends, even though the lab wrapper PID can live longer. `CAMBC_COMPILE_AHEAD=0` disables the optimization. Training/fit phases do not spawn this helper.
