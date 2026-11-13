# Line H: how we stop a winning tribute (`ia-stop`)

You are an implementer for IAPETUS (orchestrator of the macro refactor of charybdis). Work in the worktree
`/home/ubuntu/wt/mx-iapetus` (branch `mx-iapetus-20261113`). Read `AGENTS.md` and `cambc-rules.yaml` first (tribute:
stun cancels it; locks; stun removes the next turn; the killer takes the bag; Prism +1.5 Focus per gem).
Do not commit, push, or touch `/home/ubuntu/cambc-autumn` (read-only) or other worktrees.

## Base
`./copybot variants/ia-prism variants/ia-stop`. `ia-prism` is D's final: v1 `stop_due` plus the audit fixes. It
reads 53.1 [52.6-53.6] over 40,800 held-out games and 53.3 on train. A/B against `variants/chy-ref`. Read D's
diff first: `research/mx-iapetus/patches/D-prism-final.diff` and its log `logs/D-prism.log`.

## Evidence
- Line D: rushing a stop early killed our stoppers. `stop_due` times the stop for the channel's last stoppable
  rounds and gained ~2.5-3 points.
- Line F's death audit on D v1 (`logs/F-audit.log`): the stop class (E) still costs **1.08 lives and 54 gems a game**.
  85% of it falls in lost games, and our lethal read was right at the commit in 70%. The enemy tribute was cancelled
  by our lock 342 times, by our stun 439, and by the channeller itself 252 times (to kill the stopper). A lock-only
  stop leaves the channeller its turn; a stun takes it.
- Line E: stops that only cancel let the enemy restart, and about as many land. Sending killers as well read level.
- The enemy channeller is usually a big-bag Prism (Focus 1000-3700) that one-shots a lone stopper.

## Task
Make the stop itself cost less and buy more, tied to the mechanics:
- **Who stops:** the stopper whose stop also takes the channeller's next turn (a stun), the one that survives the
  channeller's answer, or several arriving in the same round. Not the first body to come due.
- **How:** stun before lock when both are on hand. A lock lands at range 2 and also blocks the restart at that altar,
  so weigh that.
- **After the stop:** what the stunned turn buys. Allies in reach strike, a kill takes the whole bag, or the stopper
  leaves before the channeller acts.
- Measure in debug games: stop-class deaths and gems a game, our stoppers' survival, enemy restarts and landings,
  and kills of channellers.
- Keep it derived from the rules (turn order, stun, lock range, damage reads); no magic numbers. Keep fuel in check.

## Process
- A/B (train suite only):
  `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-iapetus && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/ia-stop variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mxi/train --name mx-iapetus-H-r<N>`
  in a tmux session named `mx-iapetus-H-r<N>` (no `--threads`). A 10,200-game read takes about 2-4 minutes. Wait with a
  background until-loop, never a foreground sleep. Kill only by tmux session name. Up to 6 train reads, one at a
  time. Debug runs (`--debug`, ladder 256 or `maps/suites/mxi/study`) for traces in `debug_block`. Run extract.mjs only
  with `--threads 8`, one extraction at a time, ≤1,000 games. Delete batches you've studied.
- Keep each version you A/B as `bots/variants/ia-stop-v<N>`. Log each step with times (`date -u`) to
  `research/mx-iapetus/logs/H-stop.log`.
- Before returning: spawn a read-only auditor subagent on your diff and fix what it finds; make sure the bot builds;
  play the smoke `py tools/ab.py variants/ia-stop variants/chy-ref --no-test-draft --fuel 200000` (256 ladder games, no
  failed games, no DRAFT-UNFINISHED / PLAN-CHECK). **Hard stop: report by 20:40 UTC.**
- Off limits: `draft/`, emblem choice, `bots/variants/chy-ref`, `ia-prism*`, `bots/charybdis`. Implementer G
  (`ia-duel`) works on the safety model's threat reads (tracking, turn windows); stay out of `model/safety`.
- Report: what you built, every read with CI and OOF, why each moved, the best version's path, what you'd try next.
