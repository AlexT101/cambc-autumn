# Brief k10: keep a lock for the game-ending channel (two small variants)

You are implementing a macro change to the Cambridge Battlecode C++ bot `charybdis` for the orchestrator of its macro
refactor. Read `/home/ubuntu/wt/mac13-kronos/AGENTS.md` and `cambc-rules.yaml` (win, gems.tribute, altar_locks,
economy.shop, consumables). Work ONLY in `/home/ubuntu/wt/mac13-kronos`; do not touch `/home/ubuntu/cambc-autumn` or
other worktrees; do not commit. Never edit `bots/variants/chy-ref` or `bots/charybdis`. Off limits: `src/draft/`,
emblem choices (which shards/emblems are bought must not change, only the order of the lock purchase relative to
them). Each variant: `./copybot variants/chy-ref variants/NAME` (never copy `.cambc/`), then the edit.

## Why
Most games end with one long winning channel (458 of 1,024 mirror games: a 200+-gem tribute, median 45 turns). A
lock placed within 2 of the altar cancels it (whole progress lost: the bag scores only on completion) and blocks the
enemy's tributes there until 5 basic attacks break it. During those channels, our champions SAW the channeller in
267 of 458 games (6,988 champion-rounds), yet only 8% of those rounds were in the stop-ender branch: 79% of the seers
carried no lock, and most have no stun. `holds_hard_stop` (`combat/fight.cc` ~1240), the trigger for
`stop_game_ender` ("into reach whatever the risk"), needs a ready stun or a carried lock; without one the seer only
fights as priced, and mostly farms, retreats or banks. Locks cost 10 gold and one is carried at a time; they are
bought on spawn or while dead in `shop()` (`bot.cc` ~327) AFTER shards (`buy_shards`), so they are bought only with
leftover gold; and `place_lock` (`economy/bank.cc` ~52) spends the carried lock in passing on our-side altars as
denial (no tribute to cancel). The giant winning channels are mostly at middle altars (362 of 458), not our side.

## Variants
1. `k10-lockfirst`: in `shop()`, buy the lock before the shards (a hard stop for a game-ending channel is worth more
   than one more shard; it costs 10 of a shard's 30). The crystal stays first. Nothing else changes.
2. `k10-lockres`: `k10-lockfirst` plus a reserve: while the enemy can end the game by tributing what it carries
   (`world.score.enemy` + the gems we believe its living champions carry, as `game_ender`'s `carried` computes it,
   >= `winning_gems`), `place_lock` does not spend our last carried lock on denial (the pass with no enemy tribute
   to cancel); cancelling a seen enemy tribute (pass 0) and `keep_guard_lock` (the altar guard's lock) are
   unchanged. Write the trigger as one small helper with a comment naming the rule it follows.

## Stop condition
1. Both build (release). 2. Spawn ONE read-only auditor subagent (tell it explicitly not to edit anything) to check
the diffs against this brief and the rules (no change to shard choices, only their order with the lock; no change
while the trigger is off; no thrown-error loops; release builds unaffected); fix what it finds.
3. Smoke each in parallel:
`source ~/venv/bin/activate && cd /home/ubuntu/wt/mac13-kronos && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH python tools/ab.py variants/NAME variants/chy-ref --no-test-draft --fuel 200000 --name mac13-kronos-NAME-smoke`
(256 ladder games each): no failed games, no DRAFT-UNFINISHED / PLAN-CHECK. Also one `--debug` smoke of k10-lockres
with debug-only trace lines `LOCKRES <round> <id> withheld` (the reserve withholding a denial lock) and report how
often it fires per game, plus how often an enemy-tribute cancel lock is placed per game (candidate vs chy-ref,
from the replays' events or a trace). Delete the smoke batches afterwards.
4. Save diffs to `/home/ubuntu/wt/mac13-kronos/research/mac13-kronos/patches/NAME.diff`
(`diff -ru bots/variants/chy-ref/src bots/variants/NAME/src`) as soon as each builds (the orchestrator starts
screening from the diff's appearance), then audit and smoke. Return what changed per variant, auditor findings and
fixes, smoke results and the firing rates. No large A/Bs.
