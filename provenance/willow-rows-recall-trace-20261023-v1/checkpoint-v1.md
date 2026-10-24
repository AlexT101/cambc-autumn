# Rows recall diagnostic source v1

Source-only diagnostic, 2026-10-23. Exclusive ignored child `bots/variants/willow-rows-recall-trace-work` is cloned from frozen fd99, with no upstream integration or item arms stacked. Only `src/bot.cpp` differs. No build, replay extraction, runtime, scripts or gameplay repair was performed.

Parent aggregate: `fd99d1072c9c57b7d536e4c2602da56cffcfca3c41ac758aff10a552a7583f2f`.
Candidate aggregate: `166fab1a6f40dfba15cf4d22b00da75c936fd606c9ca0e8e42d6fe084e75d995`.
Aggregate convention inside each bot: `shasum -a 256 src/* | shasum -a 256`.
Exact parent patch: `candidate-v1-vs-fd99.patch`, SHA `3939f7e0d77b47d170044dbd716fe610cb9243722e53e3854de5da355886f76d`.

The before and after source snapshots each contain all 29 files: `parent-fd99-src/` and `candidate-src-v1/`, with per-file SHA256 manifests. The candidate snapshot matches the child byte for byte. The exact parent patch passes the whitespace check. Source review was requested from Astra; no runtime qualification is implied by these static checks.

## Target and output

New output begins `ROWS <round> <current decision>`. Its gate uses only cached `world.map().team_a`, `world.me().index == 0` and rounds 1167 through 1168 inclusive. It adds no actor, round, position, visibility, health, fuel or other native reads. All new output is inside the `rows_trace` helper's `debug_block`. Existing parent debug output is retained unchanged.

The target is actor 0/team A in exact fd99 Rows replay `041-00rows-12.repl26a`, SHA `bb485f891944ae3ed739b91812c576d30ac48e4c0f87e5cd4b376bdb75042a16`, saved extract `bb485f891944ae3e`. The gate deliberately uses no map-name or hidden state lookup; it would also print for the same actor/window on another map.

## Recorded facts

- `altar-usable`, `bankable`, `winning`, `race`, `closing` and `retaining` print existing invocation results and already-computed terms. `race short` is after subtracting eligible teammate bags; `closing left` is the existing bag horizon. Altar fire loss is evaluated only when the existing open-tile condition permits it. No call is made solely to fill a trace field.
- `recall-enter/home/keep/cancel`, `recall-bank` and `recall-shop` identify the existing recall branch and its static walking comparison when reached. Bank-or-shop is distinguished by the preceding bank and shop records. `recall-start completed` means the existing recall API returned without throwing; it does not invent a separate success query.
- `farm-enter/context/return` identifies pickup, early attack, held capture, bank preference, stale turn and other existing early paths. `farm-scan` records `k`, intended `evaluated`, total groups, original partial flag, fight-search flag and each candidate record. `k == evaluated == 0` is not a full group evaluation. `k == evaluated == total` means the loop completed; individual competitive pruning remains visible and does not certify every group through all filters.
- Per-group `farm-skip/prune/deadline/own/shared` distinguishes terminal structural/reach/wait/viability/deadline exclusions from competitive pruning and surviving own/shared health/rate estimates. No forecast or deadline calculation is repeated for logging. `farm-no-choice` is printed only after affordable, help and risky selection have all failed.
- `farm-selected` gives final group, steps, crew, spell and cached camp state. Respawn wait comes from the corresponding existing per-group estimate. `farm-route` logs the actual selected route functions' returned Booleans, including cached previous-target reuse, centre descent and crow-flies fallback. `farm-routing search` is the existing fuel decision, not a new gate. `farm-route-final` reports the original `walked` variable; if a later dasher fallback runs, its own records are authoritative rather than that earlier Boolean.
- `bank-zone`, `bank-route`, and `safe-step` expose the selected altar field and actual step results when banking or ordinary shopping uses them. A route function returning true is its existing success contract, not a new measured position delta. `carry-wait` identifies the existing altar wait branch. `decide-done` and `turn-done` preserve final decision and group/claim/crew/banking identity.

All existing model and route calls retain their count, operands, and short-circuit structure; temporary scalars only retain their existing results. No new scans, forecasts, fields, actions, claims, fuel gates or imports were added. The diagnostic does not interpret an absent log as a false value: the original short circuit may simply not have reached that computation. If the final decision is an unrelated higher-priority path, this narrow trace may nominate a further focused witness rather than explain its internal behavior.

## Required runtime qualification

Debug code generation and debug-block overhead can perturb fuel and decisions, including before the output window. Before asserting a Rows branch, qualify the diagnostic against frozen fd99 with native action and state agreement through the target window, using the same replay inputs. A build or high-fuel agreement alone is insufficient evidence of default-budget branch identity. No claim of such agreement or of a source hypothesis being true has been made here.

Validated retained no-choice with closing false would support the proposed no-work retention gap. A bank/shop selection followed by unsuccessful live steps would support the static-versus-live route hypothesis. A selected camp with an acceptable known wait or a held capture would support productive waiting. These are interpretation criteria, not observed outcomes.
