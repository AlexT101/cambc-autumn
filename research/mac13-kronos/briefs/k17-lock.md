# Brief k17: what the lock costs (two one-line probes)

You are building probe variants of the Cambridge Battlecode C++ bot `charybdis` for the orchestrator of its macro
refactor. Read `/home/ubuntu/wt/mac13-kronos/AGENTS.md` and `cambc-rules.yaml` (altar_locks, gems.tribute,
consumables). Work ONLY in `/home/ubuntu/wt/mac13-kronos`; do not touch `/home/ubuntu/cambc-autumn` or other
worktrees; do not commit. Never edit `bots/variants/chy-ref` or `bots/charybdis`. Off limits: `src/draft/`, emblem
choices. Each variant: `./copybot variants/chy-ref variants/NAME` (never copy `.cambc/`), then the edit.

## Why
k10-lockfirst (the lock bought before the shards, `shop()` in `bot.cc` ~327) lost 1.2 points on 10,240 games
although it raised our lock cancels of enemy tributes by half. Two explanations: the shards it delays, or the
"whatever the risk" walks it causes: a carried lock makes `holds_hard_stop` (`combat/fight.cc` ~1240) true for a
seen game-ending enemy channel, and `stop_game_ender` then walks in regardless of risk (losers' stop-ender
episodes end in the stopper's death 52% of the time). These probes separate the two.

## Variants
1. `k17-lockstop`: in `holds_hard_stop`, a carried lock no longer counts (only a ready stun does). Purchases,
   `place_lock` (in passing and in `stop_game_ender`'s act) and everything else unchanged.
2. `k17-nolock`: `shop()` never buys a lock (remove the `buy_lock()` call). Everything else unchanged.

## Stop condition
1. Both build (release). Save each diff to
`/home/ubuntu/wt/mac13-kronos/research/mac13-kronos/patches/NAME.diff` (`diff -ru bots/variants/chy-ref/src
bots/variants/NAME/src`) AS SOON AS IT BUILDS (the orchestrator screens from the diff's appearance).
2. Spawn ONE read-only auditor subagent (tell it explicitly not to edit anything) to check both diffs against this
brief (one change each, nothing else; release builds unaffected); fix what it finds.
3. Smoke each in parallel:
`source ~/venv/bin/activate && cd /home/ubuntu/wt/mac13-kronos && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH python tools/ab.py variants/NAME variants/chy-ref --no-test-draft --fuel 200000 --name mac13-kronos-NAME-smoke`
(256 ladder games each, in the background): no failed games, no DRAFT-UNFINISHED / PLAN-CHECK. Delete the smoke
batches afterwards. Return what changed, the auditor's findings and the smoke results. Be quick.
