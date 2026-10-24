# Band HoR routing diagnostic source v1

2026-10-23. Exclusive ignored source-only child `bots/variants/willow-band-hor-routing-trace-work` of frozen canonical 4db. Only `src/bot.cpp` and `src/pathing.cpp` change, with 99 additions and 19 replacements/removals. No gameplay policy, ranking, route order, guard rule or movement action is changed intentionally. No build, replay extraction, runtime, helper scripts, canonical edits, root documentation edits, cleanup or deletion.

Parent aggregate: `4db4eecbda37e23dbce0b162d2cf7441a3d32a554d6534cf196e3ffbedcdf2fd`.
Candidate aggregate: `46ab555f9637c1d5d86bcb7da1fa55bbf541515b023966d1e45ee8d2dc44e414`.
Aggregate convention inside each bot: `shasum -a 256 src/* | shasum -a 256`.
Exact delta: `candidate-v1-vs-4db.patch`, SHA `03c88aa944de107fd3c65495aef680065520781e4b02c300c67664f2a51bb7ee`.

Full parent and candidate snapshots each contain all 29 source files, under `parent-4db-src/` and `candidate-src-v1/`, with per-file SHA256 manifests. The candidate snapshot matches the variant byte for byte. Only the two stated files differ from the parent. The exact patch passes the whitespace check. No source review or runtime qualification is implied by these static checks.

## Target and interpretation

Source nomination: `research/willow-4db-v33-generated-loss-nominations.md`. Target replay is `gen-gen-band-102305906-candidate-A.repl26a`, SHA `cdbd5b2619aa504fcaf8ede78ac48ca8d0a85cdda4dad436a75f28c25b879ac7`, extract `cdbd5b2619aa504f`. Public map `gen-band-102305906` is 84 by 84. The diagnostic asks whether actor2's reversals around rounds17–22 follow changing selected economic work or different routes/fallbacks toward the same work. It does not assume that adjacent group62 was affordable or that a legal productive dash existed.

Every new output is inside a debug_block, gated solely on cached physical team A, own index2, and rounds17 through22 inclusive. The gate adds no round, actor or visibility imports. It intentionally does not inspect the map name. Existing parent debug output remains unchanged.

- `BAND <round> <decision> farm-enter/decide-done` records the actual farm/claim/crew tuple. Early pickup, early work, held capture, approach cast and attack-goal returns are named where the original path runs.
- `selected` records only the final group after own/risky/shared/help choice, its static centre, already-computed steps, claim/crew/spell, k/evaluated and total group count. No economic candidate loop is logged. `no-choice` distinguishes an empty result and includes the existing evaluation counts.
- `route` records the actual selected farm route function and returned Boolean. `approach-unavailable` and `previous-route-fallback` expose the original warm-field and incumbent fallback paths. Selected cleared/spell/dash/live attack/adjacent routes are distinguished. These wrappers retain the original short-circuit call order and do not call a model or route again to obtain a trace field.
- The optional group62 line reads only its cached World state, state round, awake/asleep belief, last damaged round, first member HP and HP observation round. The public group has one member. There is no fresh visibility or camp-info query, and no assumption that cached belief is native current truth.
- `BANDPATH` logs the existing route search's current coordinate, field distance, best neighbouring field distance, first-step count, cap, and exhaustion/layer result when already computed. The descent summary uses its existing sorted neighbour array, including the first proposed step and that step's already-read value; it does not read another field tile. If a later neighbour is tried, its actual attempted coordinate appears in the move log, but its field value is not newly queried.
- Field-following logs its existing current field value, optional aim, avoid presence, static-descent fuel branch and failed-descent/search status. A guard refusal is recorded only inside the existing successful guard predicate: the trace never forces guard materialization or repeats guard evaluation. Move logs preserve the existing single native move call and its returned Boolean or caught error.

No new native visibility query, field read, Safety forecast, group scan, model call, native action, import or fuel gate is introduced. The only new output uses debug-block machinery already present in the parent. Route success retains each function's existing contract; it is not a separately measured position change. Absent logs can mean the original short circuit did not reach that operation. Higher-priority nonfarm decisions are visible in decide-done, but their internal goal policies are outside this narrow trace.

## Qualification required before diagnosis

This is intended for the existing fuel-exact harness/recorder workflow. Ordinary debug code generation can diverge from Release at round1, before the gated output window; debug-block guard overhead can also change later fuel decisions. Do not treat replay similarity, an acted end-round status, or an ordinary debug rerun as causal proof.

Validate the action/state/import/fuel prefix, including opening rollover scheduling, through the target window before using these logs as the frozen4db branch witness. The trace source has not been built or run. There is no observed finding yet of changed economics, fixed-goal oscillation, guard failure or safe camp refusal, and no gameplay repair is proposed by this source package.
