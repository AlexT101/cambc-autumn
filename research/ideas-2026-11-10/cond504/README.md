# Current506 conditional exploiters: more local evidence

Rebased before any heavy work on 2026-11-10 to frozen Ocean 506, including the shipped 505/506 fuel savings. Seeds, sample sizes, statistical rules, review barriers and job IDs are unchanged. The `cond504` directory name is retained for queue compatibility.

The user asked to continue local testing after the earlier inconclusive conditional-arm results: “well you can just run more games lol”. This is a new506 experiment, preserving the old16d6f78 results separately. Queue order is both existing ward gates, Mite channel, its coordinator review, Fish carry-follow, its coordinator review, then the requested draft and tuning labs. Jobs are exclusive. No builds, map generation or games happen during preparation.

## Exact ports

`variants/oc506-chanM` and `variants/oc506-bagfF` contain only their original `ca-chan-M` / `ca-bagf-F` minus `ocean-16d6f78` changes, applied cleanly to frozen `variants/oc-dfuel-506` (commit183a1295c). All506 fuel, draft, emblem and wakecold changes remain. Each adds the same five classifier files, World observation/priority hooks, unity include and negative test stubs; its policy changes only turn_order.cc or support.cc. No main bot file is edited.

- **Mite channel:** on an ending channel, after the existing camp-damage and stun-immunity guards, inferred Mite posterior≥.8 offers the protect turn-order bid without requiring a visible cancel threat. This is not literally every turn of every channel, nor a guarantee of the first final slot.
- **Fish carry-follow:** Willow's existing follow target score gains `min(known bag,120)/40` when inferred Fish posterior≥.8. Existing eligibility, ally-location and movement logic remains.
- Both stubs remain−1; runtime classification is active. Each champion has its own observations. Classifier overhead and mistaken activation can affect the other opponent, so that half is **not an identity control**. Current Mite differs from its live pin; these tests use fixed local bodies, not a claim to reproduce its latest behavior.

## Prospective sample and inference

Both candidate and base play release/native engine5.0.1 at200k, both sides, own drafts, against fixed local Flp4/Mt3q bodies. One shared new1,024-map ladder-v2 pool starts with seeds2414000–03; reserved2414004–07 are used only if exact-content duplicate replacement is needed, before any outcomes. Duplicates are excluded within the pool and against the ladder, old standard gate pool, old conditional-arm pool and draft10 training pool; this explicit scope is not universal historical novelty. Noise blocks1004–2003 are disjoint from the old conditional runs38–404 and tuning's1001–1003. Every block revisits one128-map slice with a new opponent parameter variation:1,000 blocks do **not** mean128,000 distinct maps.

The reference's matching506 cells are shared between these two tests. Reusing cached cells never adds them twice to a test's units. Existing unrelated506 reference cells are reusable only with the exact same map/side/body/source/fuel/release identity. The128 ladder maps are diagnostic; fresh maps decide.

The policy targets one identifiable opponent, so the standing narrow-change rule applies. Each primary paired unit averages the two sides on one map against that target opponent; Fish and Mite are not pooled to dilute the effect.

- Target **gain** SPRT:50.0% versus50.25%, LLR boundaries±ln19. Its first lower crossing is absorbing for that prespecified test. Upper crossing is a positive local screen, not an automatic merge or normal-fuel admission.
- Separate target **harm** SPRT:49.75% versus50.0%. A first lower crossing rejects under that test. A lower reversal after its upper crossing becomes a conservative **regression review**, not a newly calibrated rejection.
- Remembered gain-H0 and harm-H1 crossings together stop as **SMALL/UNRESOLVED judgement review**. These are first-cross histories, not a current confidence interval, proof of positive gain or automatic rejection. Low-H1 alone never counts as gain.
- The other opponent has its own49.75%/50.0% harm read. A lower crossing triggers **off-target harm review** and takes precedence over a target gain. Continued monitoring is a safety review alarm, not an independent fresh significance claim. Even when the target passes, the coordinator must inspect this half's uncertainty and effect before a shipping decision.
- The broad50.5%/50.75% target statistic is diagnostic only. There is no precision-only or eight-block stop. At1,000 blocks without a terminal decision, report **UNRESOLVED**; no automatic repeat or extension.

Interval estimates are descriptive on repeated noise/map units. Target/off-target results, both likelihood ratios, first crossings, source/body seals and per-block paired coverage are retained. A positive target alone never establishes safety on the other opponent. Any further normal100k test requires coordinator review of the200k evidence. No automatic repin, merge, live submission or lab refill follows.

## Scheduled validation

Each job verifies approved-base policy and committed Ocean before its first heavy phase. A changed base holds for review; a genuinely started experiment stays frozen. Fish's job also requires the explicit Mite review token.

Release builds and32 release smoke cells (the16 matching baseline cells are cached between arms) (candidate/base×two bodies×four maps×both sides) check complete cells, zero errors/handoff failures and unchanged ordered drafts. Four fixture maps were chosen prospectively from the current model's Willow-containing teams, to exercise the Fish policy, not by outcomes. A separate debug trace copy adds bounded activation stamps, retaining both negative stubs. Twenty-four debug games record posterior observations and actual target-policy activation against both bodies and frozen Ocean. Ocean activation is observed without requiring it. Debug logging changes fuel/codegen; these tiny fixtures establish mechanism, not strength or a classifier accuracy rate. Any unexpected off-target activation remains visible in the record. The strength gate uses the uninstrumented release candidate.

`run.py ARM --check` verifies input/source/tool seals and reports preflight without heavy work. Queue jobs use `run.py chanM` and `run.py bagfF`. `smoke.py` owns scheduled mechanism checks, `gate.py` owns complete paired-cell audits and targeted accumulation, and `stats.py` / `test_stats.py` define and check the decision boundaries. Artifacts live in `~/tmp-offload/cond504`; review tokens remain exclusively coordinator-owned.


## Mandatory direct Ocean mirror (user amendment)

Both jobs also play the release candidate directly against frozen506 at200k after the targeted gate, even if that gate stops early. This fixed mirror sample contains8,192 new distinct ladder-v2 maps, both sides:16,384 games per candidate, in eight sequential1,024-map chunks. Seeds2415000–31 supply the initial pool;2415032–35 are reserved solely for duplicate replacement before mirror outcomes. The pool excludes exact bytes in the stated historical roots and the main conditional pool. Both arms share maps, but each arm counts every map/side only once. Frozen Ocean has no noise variants; repeated deterministic cells add no evidence and are never scheduled.

Mirror results are **absolute direct head-to-head wins**, separate from the performance delta against Fish/Mite replicas. The paired score averages both sides on a map. Report the mean, normal95% map-paired interval, pair counts and a conservative bounded empirical-Bernstein95% interval, which remains nondegenerate if every pair splits1–1. Intervals describe the sampled generator distribution; neither crossing50% nor nonsignificance proves safety. A negative normal interval flags harm for review. There are no interim result-based stops, automatic extensions, merges or100k follow-ups. Exact cell/source audits and error, early-loss, handoff and capped-draft counts are retained. Execution validity failures hold the job.

The primary gate's review marker explicitly says mirror pending and complete=false. Only after the mandatory mirror result exists does the wrapper write complete=true with both result hashes; manual review tokens remain coordinator-owned. All target, off-target and mirror evidence must be reviewed together before another fuel budget or shipping. The debug smoke adds eight Ocean games recording real classifier posteriors and policy activation without forced stubs; these are mechanism fixtures, not mirror-strength evidence.
