# Oscillation hunt, round 2: fixer addendum

Follow `FIX-BRIEF.md` (principles, plan → implement → read-only auditor → test, deliverable) with these changes:

- **Findings:** `round2-findings.md` (this directory) defines both workstreams, with mechanisms, examples and
  scopes. Read it first, then the round 1 notes it cites.
- **Base:** main at **8c0f3d49** (the round 1 fixes plus fuel campaign 6). The frozen baseline is
  `bots/variants/astraeus-8c0f3d4`; never edit it.
- **Worktrees:** `/home/ubuntu/wt/osc-r2-1-arrival-round` (branch `osc/r2-1-arrival-round`) and
  `/home/ubuntu/wt/osc-r2-2-every-advance` (branch `osc/r2-2-every-advance`). Notes go in `r2-<N>-fix.md` in this
  directory of the primary checkout. Bot copies: `bots/variants/oscr2<N>-...`.
- **Trace patch:** `research/hyperion/fuel-campaign-6/trace.patch` (the round 1 patch no longer applies). Fit
  failed hunks by hand.
- **Detector:** always `--bridge-oof`, and `--bot <your trace dir name>`. Compare with `tools/replay/osc_compare.py`
  against the investigator's run of main on the same maps and opponent: `replays/osc/round2-v69` (from
  `replays/batch-20261104-122523-ab-osc2r-v69-{ladder,gen,fresh-gen-s1,fresh-4104}`). Play your traced build
  against `baselines/v69` with `--suites ladder,gen,fresh,maps/fresh-4104`, each bot on its own draft
  (`--no-test-draft`).
- **A/B verdict:** 10,240 games on `maps/osc-r2-10k` (fresh-91021..91040, unused):
  `py tools/ab.py variants/oscr2<N>-<sha7> variants/astraeus-8c0f3d4 --no-test-draft --suites maps/osc-r2-10k --name oscr2<N>-<tag>`.
  `maps/osc-r2-20k` is the orchestrator's.
- **Fuel:** report out-of-fuel turns. Main already pays about 2.8× the old baseline's out-of-fuel turns, so keep
  added work bounded and shared, and don't undo the fuel campaign's savings. Still no new fuel gates.
- **Lessons from earlier rounds:**
  - A next-round threat window applied to every Safety consumer lost 0.3-0.8 points; keep yours to the
    deciders that disagree.
  - Refusing post-strike steps lost about 0.6 points; never refuse a hit.
  - The two workstreams run in parallel: stay inside the scope `round2-findings.md` gives you.
