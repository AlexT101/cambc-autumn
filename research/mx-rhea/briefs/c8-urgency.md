# C8 `urgency`: stop a game-ender at the risk its clock justifies

Worktree /home/ubuntu/wt/mx-rhea (branch mx-rhea-20261113). Read AGENTS.md and cambc-rules.yaml first (tribute,
abilities.stun, altar_locks, rounds.champion_order). Do not commit, push, touch other worktrees, `bots/charybdis`, or
`bots/variants/chy-ref` (frozen reference). Do not change draft/ or emblem/shard choices. Another implementer works in
variants/c7-hunt: leave it alone.

## Why
- Branch E (`stop_game_ender`, combat/fight.cc ~1269, called from bot.cc ~664 when `game_ender()` finds a visible
  enemy whose tribute wins and `holds_hard_stop()` holds) walks "into reach ... whatever the risk". In the mirror
  (1,020 games of chy-ref, `replays/ana-mirror`, debug batch `replays/batch-20261113-142221-ab-mx-rhea-mirror-study3`
  with D lines in team-?.stdout): 28% of all deaths are on E; 138 of 404 deaths with 200+ gems had E in their last 10
  turns (113 of them with only the enemy holding a winning bag); 21% of first Prism deaths are a weaker Prism with a
  median 528 gems on E, and its team wins 7% (the first Prism death's team wins 8% overall).
- Hypothesis to test first: holds_hard_stop needs the ender to be channelling, and the bot (both sides) starts a
  tribute at most turn ends near an altar and cancels it next turn (482 of 703 manual cancels of winning channels were
  such one-turn channels, cancelled when want_home fired). So a holder near an altar reads as "channelling a winning
  tribute" every turn, and our champions charge it whatever the risk, though the channel would last ceil(bag/10)
  turns (median 60) and would be cancelled by its owner anyway.
- A channel with many turns left is not urgent: the game ends only when it completes; other stops (a later stun after
  cooldown 8, an ally's stun, a lock within 2 of the altar) can come before then.

## The design (find out first, then build)
1. Measure on the mirror's debug batch (and extracted replays; `research/mx-rhea/scripts/tt_follow.py`,
   tools/replay/analysis Game API): for E episodes, the ender's channel turns left when we committed, whether the
   ender's channel ended by our stop, by its own cancel, or completed, and whether our champion died within ~10 turns.
   Report the split.
2. Make the "whatever the risk" walk depend on the clock: it is justified when the channel lands before any later stop
   could (our next chance after a priced approach, an ally's stop: `ally_stops`, a lock). Otherwise the ender is fought
   as priced by the normal fight logic (prey / chase / want_home), i.e. we keep stopping it, but not into a lost fight.
   Derive every bound from the rules (channel_end_round, stun cooldown 8, turn order) and existing estimators; no new
   tuned constants.
Add debug_block lines where the new logic decides.

## Process
- `./copybot variants/chy-ref variants/c8-urgency`, edit only there. Comment only counterintuitive behaviour, concisely.
- When it builds, spawn ONE read-only auditor subagent (general-purpose) with the diff and this brief: rule errors
  (channel timing, stun/lock semantics, turn order), stale beliefs, fuel. Fix its findings.
- Env prefix: `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-rhea && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH`
- Smoke: `py tools/ab.py variants/c8-urgency variants/chy-ref --no-test-draft --fuel 200000 --name mx-rhea-c8-smoke` (256
  games; 0 failures, no DRAFT-UNFINISHED / PLAN-CHECK, OOF not up materially).
- Binding: `py tools/ab.py variants/c8-urgency variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mx-rhea/study3 --debug --keep-replays 0 --name mx-rhea-bind-c8`,
  then `py research/mx-rhea/scripts/bind.py replays/batch-20261113-142221-ab-mx-rhea-mirror-study3 <that batch>`, plus
  E-branch deaths per game for c8's side vs chy-ref's side (and `research/mx-rhea/scripts/prismdeath.py` on the
  extracted batch for first-Prism-death share).
- Save the final diff (against chy-ref) to research/mx-rhea/patches/c8-urgency.diff. Delete your smoke batches (keep bind-c8).
- Stop and report: step 1's split, the design as built (file:line), auditor findings and fixes, smoke (win%, failures,
  OOF both sides), bind.py output and the E-death counts. Do not run larger A/Bs.
