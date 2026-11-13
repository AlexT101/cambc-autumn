# Line D: the Prism's bag (`ia-prism`)

You are an implementer for IAPETUS (orchestrator of the macro refactor of charybdis). Work in the worktree
`/home/ubuntu/wt/mx-iapetus` (branch `mx-iapetus-20261113`). Read `AGENTS.md` and `cambc-rules.yaml` first.
Do not commit, push, or touch `/home/ubuntu/cambc-autumn` (read-only) or other worktrees.

## Base
Start from `bots/variants/ia-contest` (the current best: it beats chy-ref 51.1% [50.6-51.7] over 30,600 held-out
games): `./copybot variants/ia-contest variants/ia-prism`. A/B against `variants/chy-ref` as below; also compare
with ia-contest's own train numbers (v3 50.9, v4 50.3 on train).

## Problem (from the mirror, chy-ref vs itself, 1,020 games; scripts in `research/mx-iapetus/scripts/kills.py`,
`prism.py`, `prism2.py`, replays extracted at `replays/.an-mirror`)
- The killer takes the whole bag. Kills of 50+ gem bags move 246 gems a game from the loser against 37 from the
  winner; **the loser's Prism alone loses 180 gems a game** (the winner's 20), 128 of it in 300+ bags (0.21 such
  deaths a game against 0.02). Prism keeps every gem for Focus until its bag wins or the game closes
  (`economy/bank.cc keeps_gems`): it never tributes before its last bag; it carries 392 on average in winning teams
  and 201 in losing ones.
- The loser's 300+ Prism deaths (211): 150 of the 180 gems a game die within 8 tiles of an altar; bag + team wealth
  < 1000 in 164 (not the winning bag); approaching an altar over the last 15 rounds in 129; one or more allies dead
  in 122; no ally within 4 in 100; an enemy within 4 of that altar 15 rounds earlier in 135; full health 15 rounds
  earlier in 137.
- In ia-contest, Prism 51+ bag deaths are 0.458 vs 0.417 a game (slightly worse than chy-ref).

## Task
1. **Find out first** what the Prism is doing before those deaths: debug games (`--debug`, 2x fuel; traces in
   `debug_block`, output in replay zips `team-?.stdout`), the branch (`decision`), the farm target, the bank state
   (`keeps_gems`, `closing`, `banks_bag`), and why it walks where it dies. Is it heading to an altar to bank (why, if
   it keeps gems?), farming a group by an altar, retreating, recovering, shopping? Is the risk visible to the bot
   (enemies seen, allies dead) when it commits?
2. Then fix the cause with a rule tied to the mechanism. Directions to weigh (yours to choose or reject on evidence):
   - Price keeping against losing: Focus per gem kept against the bag's chance of being taken in the coming rounds
     (allies dead, enemies seen or able to reach it), instead of the binary keep-until-winning rule; a Prism whose bag
     is likely to be taken banks it (or the part that does not pay for itself) where the enemy isn't.
   - The altar and the moment: bank at the altar the enemy can't reach first (enemy arrival bounds: respawn timers,
     visible distance, last sightings), or wait for allies.
   - The team: allies' farm or guard choices covering the Prism's walk when its bag is big.
   Priors: installment banking at fixed points read level; early chunking lost heavily; "every design that adds
   caution has lost" (because it gives up working time). A change should cost the Prism little working time when it
   is not in danger.
3. Keep it derived from rules and measured quantities; no hand-picked constants unless measured.

## Process
- A/B (train suite only; IAPETUS judges on other suites):
  `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-iapetus && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/ia-prism variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mxi/train --name mx-iapetus-D-r<N>`
  in a tmux session named `mx-iapetus-D-r<N>` (no `--threads`). A 10,200-game read takes under a minute. Wait with a
  background until-loop, never a foreground sleep. Kill only by tmux session name. Up to 10 train reads, one at a
  time; pool 2-3 reads before calling a small difference. Debug smokes (ladder, 256 games, `--debug`) for traces.
  Delete replay batches you've studied.
- For each read find out why it moved (Prism bag deaths and gems lost, tribute counts, Prism working time, wins).
  Keep each version you A/B as `bots/variants/ia-prism-v<N>`.
- Log each step with times to `research/mx-iapetus/logs/D-prism.log`.
- Before returning: spawn a read-only auditor subagent on your diff and fix what it finds; make sure the bot builds;
  play the smoke `py tools/ab.py variants/ia-prism variants/chy-ref --no-test-draft --fuel 200000` (256 ladder games, no
  failed games, no DRAFT-UNFINISHED / PLAN-CHECK).
- Off limits: `draft/`, emblem choice, `bots/variants/chy-ref`, `bots/variants/ia-contest`, `bots/charybdis`.
- Report: what you found the Prism doing, what you built (files, mechanism), every read with CI and OOF, why each
  moved, the best version's path, and what you'd try next.
