# Optional make-way ally read robustness source v1

2026-10-23. Exclusive ignored source-only child `bots/variants/willow-make-way-missing-ally-work` of canonical 4db. Only the ally lookup/priority-read block in `Pathing::make_way`, `src/pathing.cpp`, changes: 11 additions and three replaced lines. No tracing, Focus, Health, conversion or routing-policy arm is stacked.

Parent aggregate: `4db4eecbda37e23dbce0b162d2cf7441a3d32a554d6534cf196e3ffbedcdf2fd`.
Candidate aggregate: `03aaf746068a29d94f4e6d5245f89d97ca9bae123bb518fa32ab07a0a509797c`.
Aggregate convention inside each bot: `shasum -a 256 src/* | shasum -a 256`.
Exact parent delta: `candidate-v1-vs-4db.patch`, SHA `ccd669ca834a1ca89e87e64d3e2a8c3ec662c949b6ff4655b794bb920aa8a5f5`.

Full before and after snapshots contain all 29 source files, under `parent-4db-src/` and `candidate-src-v1/`, with per-file SHA256 manifests. The candidate snapshot matches the variant byte for byte. Only pathing.cpp differs and the exact patch passes the whitespace check. No build, runtime, tooling script, canonical/root-document edit, cleanup or deletion was performed.

## Exact error boundary

The contract is `research/willow-make-way-missing-ally-source-review.md`. The original ally-at-tile lookup, self/ally gem-count reads, and existing short-circuit gem/type comparison are retained verbatim inside a narrow try block. The successful path adds no query, occupancy pass, field, forecast, route, visibility preflight, import or fuel gate. Guard construction, route work and movement remain outside the catch.

The catch handles only `cambc::error` with the exception's copied `api_not_found`98 or `api_not_in_vision`97 code. Other errors are immediately rethrown. On those two expected errors only, `world_.throw_if_stale()` runs after the SDK has already constructed the exception and captured its engine diagnostic. No round import is inserted between the failed raw call and SDK error construction.

If stale, `StaleTurn` propagates from the catch body to the existing runner. If still current, existing `invalidate()` marks local occupancy and position caches stale, then make_way returns false. It does not keep iterating the sampled ally board, choose an unknown ally, fabricate priority, mark a hidden move bump, or rebuild a route here. The already-reached `route_exhausted_ = false` remains as before; unknown ally identity is not proof that a wider route is impossible.

The source contract fits this exact code and required no broader refactor. Exception layout can still alter compiled fuel or import scheduling; source review does not prove successful-path fuel equivalence. Future checks should cover successful and priority-tie imports/actions, current-round missing/hidden ally returning false with invalidation, expected errors after rollover propagating StaleTurn, and unexpected errors propagating normally. No such tests were run in this task.

This addresses a feasible local robustness seam. It does not establish that make_way caused the exact Labyrinth102406310 B round448 error98, nor claim to fix that incident, successful stale reads, or other rollover races. Preserve and diagnose the original incident separately.
