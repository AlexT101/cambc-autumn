# C5 `race`: the endgame tribute race

Worktree /home/ubuntu/wt/mx-rhea (branch mx-rhea-20261113). Read AGENTS.md and cambc-rules.yaml first (tribute,
altar_locks, abilities.stun, recall). Do not commit, push, touch other worktrees, `bots/charybdis`, or
`bots/variants/chy-ref` (frozen reference). Do not change draft/ or emblem/shard choices. Other implementers work in
other variants/ dirs: leave them alone.

## What decides these games (1,020 mirror games of chy-ref, `replays/ana-mirror`, scripts in research/mx-rhea/scripts/)
- A winning bag (a champion's bag + its team's score >= 1000) is held in 1,197 team-games; its holder wins 99% unless
  the other side also holds one at once. Both sides hold one at once in **174 games (17%)**, and those are a coin
  flip (51%): the race. (`winbag.py`, `endrace.py`, `endrace2.py`.)
- A winning tribute channels ceil(bag/10) turns, the whole bag (median 60, p75 82-121: mostly the Prism's bag).
  Damage does not cancel it; a stun does; a lock placed at that altar cancels every channel there and then blocks the
  other team's tributes there until 5 basic attacks remove it.
- In races each side starts 4.7-5.8 winning tributes a game. They end: stun 420 / 316 (winner / loser side),
  **manual cancel 310 / 393**, lock 156 / 104, completed 120 / 0. The loser side never even started one in 119 games.
- The 120 completed ones mostly ran with all or most enemies alive; the nearest enemy over the channel was 12+ tiles
  away in 40 and 7+ in 81: the winner tributes at an altar, at a time, the enemy cannot reach, not by winning a fight.
- Example 2d4e1d139c8ecdf9 (team 1, Prism #8, r535-570): our Prism holds a 1024-gem bag and goes B/E/R/K between spawn
  and the altar the enemy Prism stands at, and dies there at r570 (3742 -> 1735 hp in a turn); the enemy wins.

## The design (find out first, then build; each piece tied to a rule)
1. Measure why our side's winning tributes are cancelled manually (continue_tribute / tribute_safe / holds_hard_stop
   / game_ender in economy/bank.cc and combat/fight.cc; add debug lines if none say why) on races in debug games:
   `py tools/ab.py variants/chy-mirror variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mx-rhea/study3 --debug --keep-replays 0 --name mx-rhea-c5-base`
   (or reuse replays/batch-20261113-142221-ab-mx-rhea-mirror-study3, which is such a run; its stdout has the D lines).
   Only a stun, a lock or a kill stops a channel: a cancel because an enemy without a ready stun / lock / lethal
   damage by the channel's end comes near is a mechanism error.
2. The race arithmetic: our channel at altar X completes in b turns; it fails if an enemy able to stop it (a stunner
   whose stun is ready when it gets within range 4 of the channeller, a lock carrier within 2 of X, or lethal damage)
   arrives before then. Price each altar by that margin, using the beliefs and the turn order (double moves); start or
   keep the channel where it completes, choose the altar (and the holder, when two allies hold winning bags) with the
   best margin, not the nearest. When no altar works, the holder stays out of reach (spawn is safe) instead of standing at
   a guarded altar.
3. Denial: the enemy's channel is the mirror image: when an enemy channels a winning tribute, the cheapest stop is the
   one that arrives in time (a lock needs only to be within 2 of the altar, and it also blocks the retry; a stun needs a
   ready stun within 4). Check that our champions carry locks in races (10 gold, carry 1) and send the one that arrives
   in time.
Reuse the existing estimators (arrival, reach, safety); no new tuned constants. Build the pieces that step 1 shows
bind; report the split.

## Process
- `./copybot variants/chy-ref variants/c5-race` (copybot leaves out .cambc/), edit only there. Comment only
  counterintuitive behaviour, concisely. Add debug_block lines where the new logic decides.
- When it builds, spawn ONE read-only auditor subagent (general-purpose) with the diff and this brief: correctness, rule
  errors (channel length, stun/lock semantics, turn order), stale beliefs, fuel. Fix its findings.
- Smoke from the worktree (256 games, 0 failures, no DRAFT-UNFINISHED / PLAN-CHECK, OOF not up materially):
  `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-rhea && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/c5-race variants/chy-ref --no-test-draft --fuel 200000 --name mx-rhea-c5-smoke`
- Binding check: the same prefix with `py tools/ab.py variants/c5-race variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mx-rhea/study3 --debug --keep-replays 0 --name mx-rhea-bind-c5`,
  then `py research/mx-rhea/scripts/bind.py replays/batch-20261113-142221-ab-mx-rhea-mirror-study3 <that batch>`, and
  `py research/mx-rhea/scripts/endrace.py` on that batch extracted (`node tools/replay/extract.mjs <batch> --out /tmp/mx-rhea/ana-c5`)
  to compare the race outcomes for c5's side.
- Save the final diff (against chy-ref) to research/mx-rhea/patches/c5-race.diff. Delete your smoke batches under replays/
  (keep the bind-c5 batch for me).
- Stop and report: step 1's split, the design as built (file:line), auditor findings and fixes, smoke (win%, failures, OOF
  both sides), the bind.py output and race counts. Do not run larger A/Bs.
