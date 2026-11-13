# Brief C13: why the farm's choice changes mid-walk, and pricing it (implementer, licence to research and iterate)

You are an implementation agent for the CASTOR macro programme on the Cambridge Battlecode bot `charybdis` (C++).
Work only in the worktree `/home/ubuntu/wt/mac13-castor` (branch `mac13-castor-20261113`; never push, never touch
`main` or `/home/ubuntu/cambc-autumn` except to read). Read `AGENTS.md` first and follow it (it says to read
`cambc-rules.yaml`: do). C++ API: `docs/api/cpp.md`, `sdk/cpp/cambc.h`. Don't change drafts or emblem choices. Never
edit `bots/variants/chy-ref`, `bots/charybdis` or another implementer's `bots/variants/c*` directory (`c12-end` is
another implementer's).

## Setup
`./copybot variants/c11-int variants/c13-dither` (never copy `.cambc/`); edit only `bots/variants/c13-dither/src`.
c11-int is the programme's best: chy-ref plus `prism_premium` (economy/capture.cc: a gem in a keeping Prism's bag
is worth 1 + premium), a Willow medic, a stun screen and the Prism's shop and farm-recall timing (economy/shop.cc).
Against chy-ref (2x fuel) it reads train 54.8% (53.8-55.7) and dev 55.3% of 10,240 games each, and hold 53.8% of 5,120.

## Why (measured)
Debug solo traces (c6 on c7, Prism vs `bots/idle` on `maps/suites/mac13/study`) show the Prism walks 48% of its
rounds. In 23% of walk segments (44% of walk rounds) it passes a nearer group with monsters up; half of those are
groups another ally claims, which is correct. The other finding is stated by the previous implementer: in 88% of
walk segments, the group finally hit was not the Prism's `farm_group` at departure. Its choice changes about 2.4
times a walk. A walk toward a target dropped later is wasted unless the new target is on the way. The farm
(`economy/farm.cc` `farm_turn`; `rate()` in `economy/camps.cc`) re-picks every turn by
`worth / (rounds x (1 + rounds / H))`.
A re-pick is right only when the inputs changed: a group seen, an ally's claim, a respawn. If values flicker for
the same world (ties, an ally's claim flipping back and forth, the claim exclusion between allies choosing in turn
order, rounding, the prune bounds, the opening plan's weight expiring), the champion zigzags.

## The task
1. Find the causes, from traces. Use debug A/Bs or solo runs (`--debug`, `debug_block({ printf(...); })` only;
   the existing `D <round> <id> <branch> <farm_group> <claim>` lines; `tools/replay/turn_budget.py`, copy at
   `research/mac13-castor/scripts/turn_budget.py`). For each switch of farm_group, record what changed: a new
   sighting, an ally claim, our own claim being taken, a respawn, the plan's weight, or nothing visible.
   Quantify the shares, for every body as well as the Prism, in the mirror against chy-ref, not only in solo.
2. Fix the mispricing behind the largest avoidable share with a rule you can state from the rules or the bot's
   mechanics. Examples, if the traces point there:
   - A claim tie-break both allies read the same way, so two allies stop swapping groups.
   - Pricing a switch by the walk that would be wasted.
   - Keeping a choice while nothing it depends on has changed.
   Don't add a hand-tuned hysteresis margin. The farm's prune bounds must stay valid upper bounds (an earlier
   implementer, C8, broke them and blew the fuel). Watch the out-of-fuel counts in the summaries.

## Measuring
- Win rate: `source ~/venv/bin/activate && cd /home/ubuntu/wt/mac13-castor && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/c13-dither variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mac13/train --name mac13-castor-c13-trainN`
  (10,240 games, ~8 minutes, noise ~1 point). The fix helps if it beats c11-int's 54.8 on train by more than noise.
  Iterate on `train` only (never `dev`, `hold`, `conf`, `x1`).
- Farm speed: `py tools/solo.py variants/c13-dither variants/c11-int --name mac13-castor-c13-soloN --suites maps/suites/mac13/study --one-side --fuel 200000` (same env prefix).
- tmux sessions `mac13-castor-c13-*`. No foreground sleep. Keep at most one A/B of your own in flight at a time.
  Don't end your run while a run you started is in flight. Report every reading; keep each tested variant as a
  directory or a saved diff.

## Before you return
1. A **read-only** auditor subagent (told explicitly not to edit anything) checks
   `diff -ruN bots/variants/c11-int/src bots/variants/c13-dither/src` against this brief and the rules. Fix what it
   finds.
2. Smoke: `... py tools/ab.py variants/c13-dither variants/chy-ref --no-test-draft --fuel 200000 --name mac13-castor-c13-smoke`
   (256 ladder games): no failed games, no `DRAFT-UNFINISHED` / `PLAN-CHECK`, OOF near chy-ref's.
3. Save `research/mac13-castor/patches/c13-dither.diff` (against c11-int, `-ruN`). Don't commit. Kill your tmux
   sessions.

Return via SubagentHandback, no later than 09:15 UTC (check `date -u`), with these: the measured causes and their
shares, the fix and its rule, every reading, and your doubts. If no fix is ready by then, return the cause analysis
alone.
