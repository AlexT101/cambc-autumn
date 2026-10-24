# Terminal no-work conversion source experiment v1

2026-10-23. Exclusive ignored `bots/variants/willow-no-work-conversion-work`, cloned `src/` only from canonical 4db. Only `src/bot.cpp` changes. No other gameplay arm is bundled. No build, runtime, tooling scripts, canonical edits, cleanup, deletion, or root documentation edits.

Parent aggregate: `4db4eecbda37e23dbce0b162d2cf7441a3d32a554d6534cf196e3ffbedcdf2fd`.
Candidate aggregate: `28d1311c92a6ed25c30a51e78de9445f92581d9a9401353d9be9e42c4a1d2e1d`.
Aggregate convention inside a bot: `shasum -a 256 src/* | shasum -a 256`.
Exact parent delta: `candidate-v1-vs-4db.patch`, SHA `9a1cb198707bbfb97d9e7598d995dfd611c2a74e6cfe0846273ddfda4421fc2c`.

Full before and after snapshots: `parent-4db-src/` and `candidate-src-v1/`, each with 29 source files and a per-file SHA256 manifest. The candidate snapshot matches the variant byte for byte; the exact delta passes the whitespace check. Actual frozen source review requested from Astra. No runtime qualification or gain is claimed.

## Contract implementation

The policy contract is `research/willow-retained-no-work-conversion-contract.md`. `farm` retains its original Boolean return and adds an optional ephemeral `FarmOutcome` output, initialized to ordinary. Existing callers use the default null pointer. Only the ordinary decide caller requests it, and only for Prism.

Two scalar flags are recorded while the original loop runs. `deadline_rejected` is set only inside an actual existing `too_late` result, for positive finite modeled worth, a finite nonnegative clear estimate, and a finite known altar approach. `unresolved_work` vetoes positive work skipped for excessive respawn wait, claimed work with nonpositive total or remaining health, or unavailable/nonfinite forecast values. Nonfinite worth also vetoes. There is no new group scan, field construction or forecast; the original pruning and short circuits are retained. Competitive pruning is not called a deadline rejection. Its existing best/shared candidate would itself prevent terminal no-choice unless the pruned proposal has no positive rate.

Only the final no-choice branch after all original affordable, risky, shared and help choices may emit the terminal result. It requires actual `k == evaluated == n_groups`, the deadline witness and no unresolved work, ordinary F, Prism, the already-computed positive bankable bag and retained status (`!banks_bag`), no siege target or siege memory, and no combat search. A single existing-import self record then requires alive state, all move/basic/cast permissions, no recall/tribute/teleport channel, and the same position as the turn's starting belief. `world.throw_if_stale()` follows that read before emitting the result. The existing final stale check remains in place. A certified scan has positive k because it has a deadline witness, so the parent's zero-iteration route fallback cannot occur after certification.

Successful early work, held capture, contesting, productive selected waits, every selected route and every partial-evaluation fallback retain their existing paths. Higher-priority decisions still return before this ordinary caller. Global `sieged` is deliberately not an admission test: `siege()` sets it even when declining, which would wrongly exclude all ordinary nonshared-map farm calls. Actual siege work already returns before farm; `memory.siege` and `siege_group()` remain explicit exclusions.

The ordinary caller consumes the result once, clears farm group/claim/crew together, announces decision B and invokes existing `bank_gems` with explicit `BankReason::no_work_deadline`. Only that invocation bypasses retention. Ordinary banking callers retain their existing guard and behavior. It does not call carry_bag or recursively farm. The standard banking flag is set for this turn; normal decide clears it next turn if retention still applies. No permanent conversion latch, artificial closing/winning status, global threshold or fuel gate is added.

`bank_gems` retains altar choice, locks, avoidance, pack routing and movement guards. Its five existing submission call sites share a local wrapper that propagates the explicit conversion option to `submit_here`. For this option, `tribute_ok` is mandatory even at the starting tile and after an unsuccessful move; a stale check follows that safety computation before the submission preparation actions. Ordinary submission callers retain the original conditional safety check. No risk permission or safety threshold is relaxed.

## Bounds and uncertainties

The scalar certificate adds no extra loop or evaluator. A possible terminal activation adds one self-record read and one freshness check, then uses the existing bank route; the new mandatory tribute checks and their safety work are intentional costs. There is no claimed fuel saving, bounded total route cost, exit guarantee or monotone progress guarantee.

Treating nonpositive claimed remaining work as unresolved is conservative even when the current crew forecast predicts an ally will finish before arrival. The excessive-wait veto can also make activation rare when any positive group is waiting to become eligible. Report those boundaries rather than silently broadening them. A completed loop is the original policy's complete traversal, not omniscient knowledge: hidden information, future respawns, teammate work and the race estimate can change next turn.

This is a general policy consistency experiment, not a proven Rows repair. Runtime work must measure actual activation, safe submissions, route progress or blockage, next-turn work resumption/reversals, converted capital, forgone work and native fuel/errors before any adoption claim. Existing recalled stubs and the independent-ready-heal movement price are unchanged.
