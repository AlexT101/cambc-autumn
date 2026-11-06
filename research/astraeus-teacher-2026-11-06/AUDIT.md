# Teacher audit implementation campaign

Starting teacher: `1e9f7a8b3`, frozen source `a299d95209c9`.
Opponent throughout: unchanged normal-fuel astraeus, frozen source `60d2c6a7c8ab`.
Teacher gets unlimited fuel; both use their own drafts. Each measurement is
20,000 games (10,000 maps, both sides), through `tools/teacher_ab.py` and the
native fast runner. No teacher-versus-teacher matches are used.

One implementation agent works at a time, without running builds, tests or
benchmarks. The parent waits while it works, reviews its diff, then builds and
benchmarks. Improvements require a fresh-map confirmation before committing.
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

The first sandboxed baseline attempt could not access the native cache and
shared worker slots; it produced no successful games and is excluded. The
completed baseline is `teacher-audit-base-20k-r2`.

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

## Remaining audit work

Each item needs a separate reviewed implementation and measured decision;
larger items should be split into independently meaningful changes.

2. Make farm pruning bounds admissible for the actual exposure function,
   preserving tuned scoring constants.
3. Preserve combat result states that differ in surviving Heart of Ruin health;
   remove camp-threat truncation and account for action results where tractable.
4. Optimize retreat continuation over shortest-path fields instead of taking
   greedy steps; examine remaining bounded exit search and dash-route assumptions.
5. Replace camp-clear approximations with reachable action schedules and
   evaluate crew subsets where future ally behavior can be held fixed.
6. Improve the fight evaluator's action simulation before adding response search.
7. Replan remaining legal actions after a newly revealed blocker.

Income priors, strategic prices and draft models remain heuristics unless an
experiment specifically justifies changing them. More fuel does not reveal
unknown future actions or income.
