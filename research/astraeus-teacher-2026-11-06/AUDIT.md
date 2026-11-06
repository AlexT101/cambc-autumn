# Teacher audit implementation campaign

Starting teacher: `1e9f7a8b3`, frozen source `a299d95209c9`.
Opponent: unchanged normal-fuel astraeus. Initial source/SDK fingerprint
`60d2c6a7c8ab`; the rebuild noted below has identical bot source.
Teacher gets unlimited fuel; both use their own drafts. Each measurement is
20,000 games (10,000 maps, both sides), through `tools/teacher_ab.py` and the
native fast runner. No teacher-versus-teacher matches are used.

One implementation agent works at a time, without running builds, tests or
benchmarks. The parent waits while it works, reviews its diff, then builds and
benchmarks. Strategy/model changes require a fresh-map confirmation before committing.
The user subsequently authorized keeping pure improvements and engine-correct
calculations even without a measured win-rate gain; correctness fixes still get
the requested 20,000-game benchmark, with noisy or negative results reported.
`audit_compare.py` compares outcomes by map and side; uncertainty clusters the
two sides of each map. A higher win rate against astraeus must also exceed the
accepted teacher's rate on the same games.

## Suites

- Screening: seeds 863001–863040, `maps/teacher-audit-20261106`, sample seed
  863000. Unchanged teacher: **10,609/20,000 = 53.045%**, zero failed matches
  and zero teacher out-of-fuel turns.
- Visibility confirmation: seeds 864001–864040, with previously measured and
  duplicate layouts removed by SHA-256 before sampling. See
  `audit-confirmation-maps.json`. Sample seed 864000, directory
  `maps/teacher-audit-confirm-unique-20261106`.
- Heart of Ruin confirmation: seeds 865001–865040, sample 865000, directory
  `maps/teacher-hor-confirm-unique-20261106`. Previously tested and duplicate
  layouts removed before sampling; `audit-hor-confirmation-maps.json`.

The first sandboxed baseline attempt could not access the native cache and
shared worker slots; it produced no successful games and is excluded. The
completed baseline is `teacher-audit-base-20k-r2`.

During retreat testing, an unrelated `sdk/cpp/cambc_local.h` addition changed
the runner's source/SDK fingerprint and caused a fresh Astraeus build
(`0d6866e6bfd3`). Neither bot includes that header, and the opponent source is
unchanged, but the compiled WASM differs in exception-control layout. Its
normal fuel budget makes binary identity relevant. The initial comparison
against the old executable is invalid (`audit-retreat-confounded.json`).
Rerun the accepted HoR teacher against the exact new opponent executable as
`teacher-audit-hor-ref-rebuilt-20k`; `audit_compare.py` now rejects different
opponent WASM hashes. The earlier HoR comparison still passes that check.
The replacement baseline again won 10,664 games (53.320%), with identical
aggregate opponent fuel-exhaustion counts. All later comparisons require the
executable hash, regardless of this particular rebuild's unchanged aggregate.

## Candidates

1. **Exact terrain visibility and ward coverage.** Reviewed changes replace
   bush approximations in combat/support with cluster-correct shadowcasts and
   rank legal reveal-ward locations by actual visible suspect tiles. Preserve
   selected-cluster policy, uncertainty about enemy wards, and strategic weights.
   Screening: **53.265%**, +0.220 points; 491 gained games, 447 lost;
   paired 95% interval −0.075 to +0.515 points. No errors or teacher fuel
   exhaustion. Source `e139f4ac96de`.
   Fresh confirmation: **53.425% versus 53.340%**, +0.085 points;
   462 gained games, 445 lost; paired 95% interval −0.205 to +0.375 points.
   Zero errors or teacher fuel exhaustion. **Keep** under the requested
   measured-win-rate rule: both suites improve, but neither establishes a
   statistically clear gain. Results: `audit-visibility.json` and
   `audit-visibility-confirmation.json`.

2. **Admissible exposure cutoffs.** Scalar and SIMD prechecks consistently used
   `exposure_most`; the redundant SIMD rescaling was removed. Scoring constants
   and formulas were unchanged. **Reject and revert:** 10,633/20,000 = 53.165%
   versus accepted visibility's 53.265%, −0.100 points (paired 95% interval
   −0.803 to +0.603). 2,535 gained games and 2,555 lost. Zero match errors or
   teacher fuel exhaustion. Evidence: `audit-farm-bounds.json`; rejected source
   delta: `audit-farm-bounds-rejected.patch`. This is not proof of a regression,
   but it fails the requested measured-improvement rule.

3. **Heart of Ruin combat frontier.** Dominance now also requires no stronger
   surviving HoR retaliation, using the same multiplier as final scoring.
   Dynamic frontiers and candidate lists retain all nondominated choices;
   constructed vector storage lives outside the raw table union. Screening:
   **10,664/20,000 = 53.320% versus 53.265%**, +0.055 points; 23 gained and
   12 lost; paired 95% interval −0.005 to +0.115. Zero errors or teacher fuel
   exhaustion. Source `19b387bbb05f`. Fresh confirmation: **53.025% versus
   53.065%**, −0.040 points; 13 gained and 21 lost; paired 95% interval
   −0.097 to +0.017. Zero errors or teacher fuel exhaustion. **Keep under the
   user's updated correctness rule:** the old dominance test could discard a
   plan that scores better after the existing HoR damage adjustment. The small
   screening gain did not confirm; no WR improvement is established. Evidence:
   `audit-hor-frontier*.json` and `audit-hor-frontier-rejected.patch`.
   The patch filename records its initial rejection; the identical tested code
   was restored after the user's instruction.

4. **Retreat continuation and full exit search, initial bundle.** Exact
   descending-path camp damage and HomeWalk survival, full exit fields, and
   revised unreachable handling. Source `80219ba686f3`. Valid matched-executable
   result: **10,616/20,000 = 53.080% versus 53.320%**, −0.240 points;
   161 gained, 209 lost; paired 95% interval −0.432 to −0.048. Zero match
   errors or teacher fuel exhaustion. `audit-retreat.json`; source delta
   `audit-retreat-full.patch`. The full bundle is not kept.

5. **Exact retreat continuation alone.** Keep ExitHits and HomeWalk dynamic
   programming; retain the prior exit-field depth and finite no-exit estimate
   for this isolated trial. Source `f82b799a9bb2`. **Keep:** 10,664/20,000 =
   **53.320% versus 53.320%**, exactly level; 153 gained, 153 lost; paired
   95% interval −0.171 to +0.171. Zero errors or teacher fuel exhaustion.
   The calculation examines every descending shortest-path continuation under
   the same damage estimates, without changing their prices. Kept under the
   correctness exception. `audit-retreat-dp.json`; the direct full-bundle
   comparison is `audit-retreat-full-vs-dp.json`.

6. **Full exit fields with unchanged no-exit estimate.** Remove the search-depth
   cap and refresh field caches when their inputs change. Preserve the prior
   finite risk estimate only for genuinely unreachable exits. Source
   `ba534f6be509`. **Keep:** 10,664/20,000 = **53.320%**, with all 20,000 winners
   identical to the continuation-only version. Zero errors or teacher fuel
   exhaustion. `audit-full-exit.json`. The full-bundle regression is isolated
   to its changed no-exit policy; the search cap itself can be removed.

## Remaining audit work

Each item needs a separate reviewed implementation and measured decision;
larger items should be split into independently meaningful changes.

3. Remove camp-threat truncation and account for action results where tractable.
4. Examine remaining dash-route assumptions; shortest walking continuations
   and full exit searches are implemented above.
5. Replace camp-clear approximations with reachable action schedules and
   evaluate crew subsets where future ally behavior can be held fixed.
6. Improve the fight evaluator's action simulation before adding response search.
7. Replan remaining legal actions after a newly revealed blocker.

Income priors, strategic prices and draft models remain heuristics unless an
experiment specifically justifies changing them. More fuel does not reveal
unknown future actions or income.
