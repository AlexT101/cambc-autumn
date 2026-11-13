# C3 `threat`: the retreat's verdict reaches target choice

Worktree /home/ubuntu/wt/mx-rhea (branch mx-rhea-20261113). Read AGENTS.md and cambc-rules.yaml first.
Do not commit, push, touch other worktrees, `bots/charybdis`, or `bots/variants/chy-ref` (frozen
reference). Do not change draft/ or emblem choices.

## The mistake (measured on 1,020 mirror games of chy-ref, debug D lines)
farm() picks a camp group with an enemy nearby. Next turn the enemy moves, `want_home()`
(combat/fight.cc ~618; `stand_lost_at`, `drawn_home`) fires and `retreat()` steps us back (branch R).
The turn after, from the backed-off tile the stand looks safe again and farm() picks the same group.
Neither choice remembers the other: the champion rocks on the group's edge. Pursuits with 2+
farm->retreat flips: 10-12 per team-game, ~31 rounds each, 0.077 gems/round against 0.296 for
pursuits without flips; the enemy captures the group 2-3 times per team-game; losers die in them
twice as often as winners (1.30 vs 0.57 per team-game). Example: game 6baaaf14 team A Prism at the
14-gem mid cluster r37-87, ~12 flips, HP 1220->447, 17 gems.

## The design
The retreat's verdict is about the stand at the group, not about the tile we backed off to, so
target choice must ask the same question about the same place:
1. When decide() takes the retreat (want_home true, branch R) while our farm target is group g
   (and we are near enough to g that the verdict concerns its stand), remember g as `threatened` in
   Memory (one group per champion is enough; keep the turn it was set).
2. While g is threatened, farm() may choose g only if the same retreat test that sent us home
   (the stand_lost_at / drawn_home logic, or the closest reusable piece of it) evaluated at the tile
   we would work g from, with the current beliefs and our current health, says we would hold there.
   Otherwise g is skipped this turn and farm() picks the best other group (or what it does when no
   group is available). Reuse HoldAt / the existing evaluators; do not invent a new threat score or
   margins.
3. Clear the mark when that test passes at g, when g's state changes (captured / respawned), when
   we die or recall, or when our health rises (a heal changes the verdict).
Everything else (want_home itself, retreat(), the step guard) stays as it is. Mind fuel: the test
runs for one group per turn at most; check that it doesn't add OOF turns.

Add a debug_block trace line when a threatened group is skipped and when the mark clears.

## Process
- `./copybot variants/chy-ref variants/c3-threat` (copybot leaves out .cambc/), edit only there.
- Comment only counterintuitive behaviour, concisely.
- When the code builds, spawn ONE read-only auditor subagent (general-purpose) with the diff and
  this brief: correctness bugs, stale-memory bugs (ids, deaths, respawn), fuel risk, whether the
  stand test is evaluated at the right tile. Fix its findings.
- Build release, then smoke from the worktree:
  `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-rhea && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/c3-threat variants/chy-ref --no-test-draft --fuel 200000 --name mx-rhea-c3-smoke`
  (256 games): 0 failures, no DRAFT-UNFINISHED / PLAN-CHECK, OOF not up materially.
- Then one debug trace run on 40 maps of `maps/suites/mx-rhea/study` (`--debug --suites
  maps/suites/mx-rhea/study --max-games 80` or the equivalent ab.py flag; check `py tools/ab.py -h`)
  and count how often the skip fires and clears per game, and how many flip pursuits remain (a flip
  = farm target g, then R, then farm target g again within a few turns), compared with chy-ref's
  side of the same games.
- Save the final diff (against chy-ref) to research/mx-rhea/patches/c3-threat.diff.
- Stop and report: the design as built (file:line), the auditor's findings and fixes, smoke result
  (win%, failures, OOF both sides), the trace counts. Do not run larger A/Bs.
