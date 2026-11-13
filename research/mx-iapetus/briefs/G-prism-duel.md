# Line G: Prism duels and big-Focus threats (`ia-duel`)

You are an implementer for IAPETUS (orchestrator of the macro refactor of charybdis). Work in the worktree
`/home/ubuntu/wt/mx-iapetus` (branch `mx-iapetus-20261113`). Read `AGENTS.md` and `cambc-rules.yaml` first
(Prism: +1.5 Focus per carried gem; stun removes the next turn; the killer takes the bag).
Do not commit, push, or touch `/home/ubuntu/cambc-autumn` (read-only) or other worktrees.

## Base
`./copybot variants/ia-prism-v1 variants/ia-duel` (the current best: 53.3% [52.8-53.8] vs chy-ref over 40,800
held-out games; train 53.6 [52.6-54.5]). A/B against `variants/chy-ref`.

## Evidence (line D, `research/mx-iapetus/logs/D-prism.log`, NOTES.md)
After D's `stop_due`, our Prism still dies ~0.70 a game, mostly with big bags, in two classes:
- **T/B (endgame bank).** `closing` makes the Prism bank a 400-950 bag in a 40-95 turn channel. An enemy big-bag
  Prism (650-2400 gems, Focus 1000-3700) walks in from 6-8 tiles, often from out of sight, and kills it in one turn
  (one example: 4015 -> 1198 health in one turn, then dead). `tribute_safe` passed at the start.
- **R (duel lost to the first stun).** Our farming Prism spends stun and AoE on camps while an enemy Prism with both
  slots ready closes to 4, stuns, and AoEs through the lost turn.
- D's rule-level patches (a habit gate on long channels; keep the stun off camps; cancel to stun first) read level
  or lost. Caution that costs working time loses. D's diagnosis: the bot's **threat model** misjudges these enemies.
  It is not a missing caution rule.

## Task
1. Find out why the safety model (`model/safety.*`: `turns_to_kill_idle`, `stand_trade`, the fight simulation, the
   enemy beliefs in `model/world.cc`) misjudges big-Focus enemies. Candidates to check:
   - the enemy Prism's Focus and bag when last seen versus now (it keeps capturing while unseen; `drop_bag`,
     `update_scores`);
   - unseen enemies' reach (track horizon 3 rounds; `possible` boards);
   - the stun's lost turn in the damage bound (two strikes in a row);
   - ability readiness believed from cooldowns.
   Measure each in debug games: predicted versus actual damage taken in the turns before Prism deaths, and how often
   the model was blind to the killer.
2. Fix the model where it is wrong, so every decision that reads it (tribute safety, stands, retreats, farm exposure)
   becomes consistent. Valuation consistency has been the source of the gains; blanket caution has not.
   Keep fuel in check.
3. Measure the mechanism: Prism deaths and bag gems lost a game, Prism working time, tribute completions.

## Process
- A/B (train suite only; IAPETUS judges on other suites):
  `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-iapetus && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/ia-duel variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mxi/train --name mx-iapetus-G-r<N>`
  in a tmux session named `mx-iapetus-G-r<N>` (no `--threads`). A 10,200-game read takes about 2-4 minutes. Wait with a
  background until-loop, never a foreground sleep. Kill only by tmux session name. Up to 8 train reads, one at a
  time. Debug runs (`--debug`; `maps/suites/mxi/study` 1,020 maps or the ladder's 256) for traces in `debug_block`.
  extract.mjs always with `--threads 8`, one extraction at a time, at most ~1,000 games. Delete batches you've studied.
- Keep each version you A/B as `bots/variants/ia-duel-v<N>`. Log each step with times to
  `research/mx-iapetus/logs/G-duel.log`.
- Before returning: spawn a read-only auditor subagent on your diff and fix what it finds; make sure the bot builds;
  play the smoke `py tools/ab.py variants/ia-duel variants/chy-ref --no-test-draft --fuel 200000` (256 ladder games, no
  failed games, no DRAFT-UNFINISHED / PLAN-CHECK). Wrap up by about 20:30 UTC.
- Another implementer (F, `ia-audit`) audits the other bodies' deaths. Stay on the Prism and the threat model.
- Off limits: `draft/`, emblem choice, `bots/variants/chy-ref`, `ia-prism-v1`, `bots/charybdis`.
- Report: what the model got wrong (with numbers), what you changed, every read with CI and OOF, why each moved, the
  best version's path, and what you'd try next.
