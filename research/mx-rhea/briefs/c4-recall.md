# C4 `recall`: a recall's target is a commitment allies see

Worktree /home/ubuntu/wt/mx-rhea (branch mx-rhea-20261113). Read AGENTS.md and cambc-rules.yaml first.
Do not commit, push, touch other worktrees, `bots/charybdis`, or `bots/variants/chy-ref` (frozen
reference). Do not change draft/ or emblem choices. Another implementer works in variants/c3-threat:
leave it alone.

## The mistake (measured on 1,020 mirror games of chy-ref, debug D/RF lines)
farm() chooses to reach group X by way of spawn (RFCHOOSE, economy/farm.cc ~2480, `memory.recall_farm`,
kept by `continue_recall` in economy/bank.cc ~1493-1552). On landing, bot.cc ~620-633 clears
`memory.recall_farm` and farm() chooses from scratch. A third of recall-to-farm trips (4.5 per
team-game of ~13) land and then go to another group; in half of those, the champion was healthy and
walking straight from the recall's start to the group it finally chose would have been ~20 rounds
sooner. Nothing stops two allies from recalling for the same small group. Example: game 0824205
team A: at r53 the Prism (56 gems in its bag, at the mid 56-gem cluster g0) recalled for the 7-gem
g1 near spawn; Cassi recalled for the same g1 at r54 and cleared it; the Prism landed r58, switched
back to g0 and walked 48 rounds to where it started.

## The design (find out first, then build)
1. Find out why the target changes on landing, using the mirror's debug replays in
   /home/ubuntu/wt/mx-rhea/replays/ana-mirror (extracted; `research/mx-rhea/scripts/tt_recall.py`
   and `tt_follow.py` show the cases): ally took/claimed X, X's respawn estimate moved, the claim
   did not cover a recall, stickiness lost on landing, or the via_recall price being optimistic.
   Report the split.
2. Then fix the causes you find, tied to the mechanism, e.g.:
   - a recall's target is our posted claim from RFCHOOSE until we land and reach it, so allies'
     farm()/crew treat it as claimed exactly as they treat a walking ally's claim (it may already be;
     check comms `claim()` and what the claim holds while recalling);
   - before choosing a recall for X, check X is not claimed by an ally that gets there no later
     (the same test farm applies to walking claims);
   - on landing, X keeps farm's stickiness (memory.farm_group) instead of a fresh choice;
   - if the via_recall price is systematically optimistic (e.g. it ignores the channel's
     interruption or the post-landing walk the analysis shows), correct the price, not a fudge factor.
   No magic numbers; no new tuned constants.

Add debug_block trace lines where the new logic decides.

## Process
- `./copybot variants/chy-ref variants/c4-recall` (copybot leaves out .cambc/), edit only there.
- Comment only counterintuitive behaviour, concisely.
- When the code builds, spawn ONE read-only auditor subagent (general-purpose) with the diff and
  this brief: correctness, stale memory (deaths, respawn, cancelled recalls), comms payload limits
  (8 shared bytes; don't break existing fields), fuel. Fix its findings.
- Build release, then smoke from the worktree:
  `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-rhea && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/c4-recall variants/chy-ref --no-test-draft --fuel 200000 --name mx-rhea-c4-smoke`
  (256 games): 0 failures, no DRAFT-UNFINISHED / PLAN-CHECK, OOF not up materially.
- Then one debug trace run on `maps/suites/mx-rhea/study` (check `py tools/ab.py -h` for --debug and
  a game cap; ~100-200 games) and count recall landings that retarget, per side.
- Save the final diff (against chy-ref) to research/mx-rhea/patches/c4-recall.diff. Delete the
  replay batches your smokes and traces made under replays/ when done.
- Stop and report: the cause split from step 1, the design as built (file:line), auditor findings
  and fixes, smoke (win%, failures, OOF both sides), trace counts. Do not run larger A/Bs.
