# Marcella delayed-tribute scalar fixtures

Eight focused arithmetic cases are derived from the approved v2 design and pinned f475 source. They cover the delayed marginal passive term, the already-item-adjusted `per_gold` input (Treasure once), current carried gems excluded, nonpositive `per_gold`, winning/share/ownership/route exclusions, race-horizon rejection, and the optimistic prune upper-bound relation.

Run `python3 verify_fixtures.py` from the repository root. Source review passed. The verifier checks these expected values using a small Python transcription of the reviewed source algebra. It does **not** compile, extract, or invoke production C++; it gives no native API, memory/claim, actor decision, runtime fuel or game-plan coverage. In particular, an unavailable altar or spawn route is represented as an unavailable fact and zero bonus, never as zero travel time.

No production-source harness is included here, so source integration remains outside this fixture's coverage.
