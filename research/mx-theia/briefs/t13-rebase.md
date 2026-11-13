# T13 `denyfix-531`: port denyfix-a's additions onto main's charybdis 531

You are an implementation subagent for THEIA, the orchestrator of a macro refactor of our Cambridge Battlecode bot
`charybdis` (C++, compiled to WASM). Work only in the worktree `/home/ubuntu/wt/mx-theia` (branch
`mx-theia-20261113`). Do not commit, push, or touch any other worktree or `/home/ubuntu/cambc-autumn` (read-only
reference). Do not look at other worktrees under `/home/ubuntu/wt/`. Leave every existing `bots/variants/*` alone
except the one you create (another implementer works in `bots/variants/alarm-*`). Never edit `bots/variants/chy-531`.

Read first: `/home/ubuntu/wt/mx-theia/AGENTS.md`, `cambc-rules.yaml` (tribute, lock, stun, shared bytes), main's
CHANGES 530 and 531 (`git show c451e3387:research/hyperion/CHANGES.md`, entries "## 530" and "## 531").

## Situation
- Main has moved on. `bots/variants/chy-531` is a frozen copy of main's bots/charybdis at c451e3387 (= charybdis 531:
  530's `stop_due` stop timing + contest judgement, then a fuel-only pass). 530 read 52.9% against 529 at 100k fuel.
- Our `bots/variants/denyfix-a` (529 + scylla's tribute denial with only deny_late and deny_alarm on, + T9's fixes)
  read 52.5% pooled held-out against 529 at 2x fuel, 52.2 at 100k. Its patches: `research/mx-theia/patches/dnw-min.diff`
  (529 -> dnw-min), `research/mx-theia/patches/denyfix-a-vs-dnw-min.diff` (T9's fixes), `denyfix-a.diff` (529 ->
  denyfix-a). An overseer read of dnw-min against 530 at 100k gave 49.0% of 40,120: 530's `stop_due` already covers
  our late stop. So what can add is the rest.
- 530's core is `stop_due` (combat/fight.cc): a winning enemy tribute is stopped only when the rounds to its last stop
  are within our steps plus one ability cooldown; `ender_to_stop` remembers an unseen deferred ender; a stun on a
  not-yet-due winning channel is worth 0 (combat/abilities.cc).

## Task
`./copybot variants/chy-531 variants/denyfix-531` (never copy `.cambc/`), then port onto it the pieces of denyfix-a
that 531 lacks. **Keep 530's `stop_due` as the one stop-timing rule** (do not port deny_late's margin), unless you find
a concrete flaw in it, in which case state it with evidence and keep the change separate (a second variant). Port:
1. **deny_alarm**: a seer posts a seen winning tribute's altar and end round in the shared bytes so teammates out of
   its sight come in time; readers feed `ender_to_stop` / `stop_due` (the alarm is a sighting of a channel that cannot
   move). Keep the comms layout rules from denyfix-a (layout derived identically by every teammate; existing records
   unchanged).
2. **F1, the stun kept for the channeller** (a stun that cannot reach the channeller this turn is not spent elsewhere
   when its cooldown would not be back before the channel's last stop), expressed against stop_due's timing.
3. **F2, the pathing walk estimate** for the stopper's steps (fuel-gated), used where stop_due reads our steps, if
   stop_due's steps are Chebyshev.
4. **F3, remembered channels** where they add to `ender_to_stop` (e.g. where the alarm does not fit).
5. **F5, the gate on stun_worth / place_lock**, only where not redundant with 530's stun-value rule (530 zeroes a stun
   on a not-due winning channel; check whether turn-end `place_lock` is gated too; port only the missing part).
Do not port deny_hoards, deny_watch, lock_first (all off in denyfix-a) or F4. A dry merge of the branches conflicts in
bot.cc, bot_parts.h, combat/abilities.cc and economy/bank.cc: port by hand, reading both sides.

## Audit, build, smoke (before returning)
1. Spawn a **read-only** auditor subagent (general-purpose; tell it explicitly: do not edit, create or delete any
   file) with this brief and your diff (`diff -ru bots/variants/chy-531/src bots/variants/denyfix-531/src`): redundant
   or conflicting stop rules, comms layout, stop timing arithmetic, fuel.
2. Fix what it finds.
3. Smoke (256 ladder games, release): `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-theia && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/denyfix-531 variants/chy-531 --no-test-draft --fuel 200000 --name mx-theia-t13-smoke`.
   Required: no failed games, no DRAFT-UNFINISHED / PLAN-CHECK. Report win rate and OOF (a smoke, not a read). Run
   long commands in the background; while waiting, keep working or block on a bounded wait, and do not end your turn
   until you hand back: ending your turn ends your run. Delete your replay batches when done.

## Stop condition
Return (SubagentHandback) when denyfix-531 builds, passes the audit and the smoke, or by 20:40 UTC (check `date -u`)
with whatever is finished (say what is not). No 10k-game A/Bs. Report what you ported and what you left out and why
(especially anything 530 already does), the auditor's findings and fixes, and the smoke. Save the diff as
`research/mx-theia/patches/denyfix-531-vs-chy-531.diff`.
