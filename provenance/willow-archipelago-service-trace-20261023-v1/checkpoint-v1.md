# Archipelago post-clear local-service diagnostic source v1

2026-10-23. Exclusive ignored source-only child `bots/variants/willow-archipelago-service-trace-work` of frozen canonical 4db. Only `src/bot.cpp` changes, with 70 additions and seven replacements/removals. Instrumentation is confined to the cached local-support decision seam and its caller/result. No policy redesign, build, runtime, extraction, tooling scripts, canonical or root-document edits, cleanup or deletion.

Parent aggregate: `4db4eecbda37e23dbce0b162d2cf7441a3d32a554d6534cf196e3ffbedcdf2fd`.
Candidate aggregate: `06ea3ac24e3494622eabb0e6ec58b81979791eee9f7d70a445199c5cb2b14267`.
Aggregate convention inside a bot: `shasum -a 256 src/* | shasum -a 256`.
Exact delta: `candidate-v1-vs-4db.patch`, SHA `c73d4466fa9c25f8a30bda705abfd709715ea0fbd9f4c32a80488f0eefca7d7d`.

All 29 parent and candidate source files are saved in `parent-4db-src/` and `candidate-src-v1/`, with per-file SHA256 manifests. The candidate snapshot matches the variant byte for byte. Only bot.cpp differs, and the exact delta passes the whitespace check. Band routing diagnostic `46ab555f9637c1d5d86bcb7da1fa55bbf541515b023966d1e45ee8d2dc44e414` remains separate and unchanged.

## Exact target

Source nomination: `research/willow-archipelago-post-clear-service-review.md`. Target replay is `gen-gen-archipelago-102306013-candidate-B.repl26a`, SHA `c8ecfd7d658337605092e5007386ba18d378952bf91d78822c92fcb0181d5849`, saved extract `c8ecfd7d65833760`. Actor8 is physical-B Willow (own index3 in this five-pick game). The cached gate uses physical team B, cached champion handle8, and rounds139–146 inclusive, with no native actor or round lookup and no map-name lookup.

All new output begins `ARCH <round> <current decision>` and is inside debug_block. Existing parent debug output is retained unchanged. Absence of a log means its original control path may not have run; no helper is invoked merely to fill a missing trace field.

## Values and boundaries

- `local-call` records already-computed leave, protected-work, effective protect, Willow-protected, strikes and formation state. `local-result` records the actual returned Boolean, support ownership, mate eligibility, retreat flag and resulting farm/claim/crew/formation state. `decide-done` distinguishes ordinary F or other decisions from support ownership and includes cached own HP belief without reading health again.
- `local-enter` uses the existing `here` and `health` locals, so HP there is the original native value already obtained by the function. It also logs existing flags, identity, formation counters and mate cached index/visibility/position-observation round/stats round/channel. A mate unavailable refusal is named without redoing any test or visible-record query.
- `mate-channel` records the original observed-channel result. On a recall-channel mate, this is the already-computed kept-recall result; on tribute or teleport it names that exclusion and does not imply a recall query was performed. `support-seen` is the function's existing current observation marker. `healer-ready` records existing support_ready output and offered amount; for this Willow target it is Willow's heal readiness, not a new Prism ability query.
- Existing heal-target iteration records only candidates already reaching its live-record read. HP and max HP are copied by the original code before kept_recall can reuse scratch storage. The original kept-recall call and worth_healing predicate are each evaluated once; their results are retained in scalars for logging. Accepted target count and the actual selected station's best gain identify qualified useful demand without another ally scan.
- `work-source` is the existing received mate claim/source group index, not a native group handle. Its optional cached-belief line records state, observation round, awake belief, last damage, respawn round, holder/held-since and member count. HP0 and HP-round0 refer only to the first member; no total remaining HP is invented or summed. These are beliefs, not fresh visibility or guaranteed remaining work.
- `station-input` records the original readiness, active-clear, expiry, optional cooldown-work-route presence and formation state. `station` records the existing found flag, source position, actual selected station, best gain/gap and already-computed risk safety. No candidate-station logs, extra field reads, Safety forecast or station scan are added.
- The stationary-output branch is named where its existing successful action resets formation. On the ordinary support-completion path, existing heal results, actual enemy attack result and actual camp attack group identify productive output. The original calls remain single and in their original order.
- `formation-reset` records the exact original productive and route_progress Booleans and the counter values immediately before resetting. The progress-kind label identifies the original expression family: no movement, existing work field, or matching source-group centre. It does not re-read a field or repeat a distance/model function. With progress false, that label does not assert a successful matching-work certificate. `formation-after` records the counters after the unchanged reset condition. Caller results cover early returns that do not reach this seam.

No extra native import, visibility/health query, ally/group scan, model, route or field query is added. No helper is duplicated or called twice for tracing. Existing attack, heal, support, channel, safety and formation decisions retain their inputs, order, short circuits and results. The source records branch facts; accepted output and physical movement must still be joined to the validated native action stream.

## Qualification and interpretation

No original-game decision has been attributed yet. This package has not been built or run. Ordinary debug code generation and debug-block guard cost can diverge before the gated window. Validate the original action/state/import/fuel prefix, including preceding cooldown/action context, before treating these logs as actor-known evidence.

A validated F decision would move the question to ordinary economic work. Validated support ownership with matching unfinished work and real progress can justify zero-current-heal formation. Zero useful gain alone is insufficient: only its combination with unjustified remaining work and a demonstrably available forgone ordinary action would nominate a policy change. Global mate HP/positions, absent recall events or end snapshots do not substitute for the captured local knowledge. Pure Focus and Health/Focus arms remain separate hypotheses.
