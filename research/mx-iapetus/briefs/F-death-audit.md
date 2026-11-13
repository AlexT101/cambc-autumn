# Line F: death audit (`ia-audit`)

You are an implementer for IAPETUS (orchestrator of the macro refactor of charybdis). Work in the worktree
`/home/ubuntu/wt/mx-iapetus` (branch `mx-iapetus-20261113`). Read `AGENTS.md` and `cambc-rules.yaml` first.
Do not commit, push, or touch `/home/ubuntu/cambc-autumn` (read-only) or other worktrees.

## Base and why
Start from the current best, `bots/variants/ia-prism-v1`:
`./copybot variants/ia-prism-v1 variants/ia-audit`. A/B against `variants/chy-ref`; compare with the base's own train read.

The biggest gain so far came from a death audit. Line D traced the branch our big-bag Prism was in before each death
and found most deaths in `stop_game_ender` runs. Our bodies charged an enemy's long winning tribute 30-150 rounds early,
and 63% of those runs died within 25 rounds. Timing the stop for the channel's last stop (`stop_due`) gained about
2.5 points on its own, and 3.3 points held out on top of line B. Your job is to repeat that method for **every body's deaths**
(and for the kills we fail to make) on the current base.

## Task
1. Run debug games of the base against chy-ref (`--debug`, 2x fuel; the study suite `maps/suites/mxi/study` has 1,020
   maps, or the ladder's 256). Trace in `debug_block` the decision branch (`decision`, `Branch::*`), the target,
   hp, bag and the enemies in sight on each of the last ~10 turns before every death of ours. The base may already
   carry D's `PB` trace; extend it. Output goes to `team-?.stdout` in each replay zip. Extract at most about 1,000
   games, with `--threads 8`, one extraction at a time.
2. Classify deaths by the branch that led into them (the decision on the turn the fatal exchange became unavoidable,
   not just the last one), bag lost, and whether the risk was visible to the bot when it committed. Rank the classes
   by gems and lives lost a game. Do the same, briefly, for the enemy's deaths: which of our decisions win kills.
3. Pick the class with the largest avoidable loss whose cause is a misjudged rule (timing, a wrong value, a missing
   term), not plain caution. Line A, line D's v2 and earlier programmes all found that blanket caution loses. Fix the
   rule, tied to the mechanism, with no magic numbers. Then repeat for the next class while reads allow.

## Process
- A/B (train suite only; IAPETUS judges on other suites):
  `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-iapetus && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/ia-audit variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mxi/train --name mx-iapetus-F-r<N>`
  in a tmux session named `mx-iapetus-F-r<N>` (no `--threads`). A 10,200-game read takes about 2-4 minutes. Wait with a
  background until-loop, never a foreground sleep. Kill only by tmux session name. Up to 8 train reads, one at a
  time. Delete replay batches you've studied.
- For each read find out why it moved (deaths by class, gems lost, kills, OOF). Keep each version you A/B as
  `bots/variants/ia-audit-v<N>`.
- Log each step with times to `research/mx-iapetus/logs/F-audit.log`.
- Before returning: spawn a read-only auditor subagent on your diff and fix what it finds; make sure the bot builds;
  play the smoke `py tools/ab.py variants/ia-audit variants/chy-ref --no-test-draft --fuel 200000` (256 ladder games, no
  failed games, no DRAFT-UNFINISHED / PLAN-CHECK).
- Off limits: `draft/`, emblem choice, `bots/variants/chy-ref`, the base variant, `bots/charybdis`.
- Report: the death table (classes, gems, lives), what you fixed and why, every read with CI and OOF, why each moved,
  the best version's path, and what you'd try next.
