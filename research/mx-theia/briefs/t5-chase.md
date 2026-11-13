# T5 `chase`: a chase pays for the farm it gives up

You are an implementation subagent for THEIA, the orchestrator of a macro refactor of our Cambridge Battlecode bot
`charybdis` (C++, compiled to WASM). Work only in the worktree `/home/ubuntu/wt/mx-theia` (branch
`mx-theia-20261113`). Do not commit, push, or touch any other worktree or `/home/ubuntu/cambc-autumn` (read-only
reference). Do not look at other worktrees under `/home/ubuntu/wt/`. Another implementer works in
`bots/variants/prem-*`: leave those alone.

Read first: `/home/ubuntu/wt/mx-theia/AGENTS.md`, `cambc-rules.yaml` (engine-verified rules), and the sources named below.

## Setup
- Reference bot (never edit): `bots/variants/chy-ref` (= charybdis 529).
- `cd /home/ubuntu/wt/mx-theia && ./copybot variants/chy-ref variants/chase-a` (never copy `.cambc/`).
- Build: `cd bots/variants/chase-a && cambc build` (debug) / `cambc build --release`. Debug output only inside
  `debug_block({ ... });` (plain printf changes the game).

## Why
charybdis's last big gain came from pricing one quantity the same way in every decision. An audit found that a
champion's round is priced two ways:
- The farm (economy/farm.cc farm_turn) prices a round by the rate of its best job: `best_value`, in gems a round,
  premium-inclusive for the Prism (a gem in its bag adds Focus and compounds).
- **Chase entry** (combat/fight.cc `prey`, ~968-975) ranks won, non-escaping targets by
  `turns / (life_value/gem_value + pair_gems + held)` and chases the best, with no comparison to what the same turns
  earn farming; `chase_with_guard` (bot.cc ~775) runs before `farm`.
- **The strike search** (bot.cc ~581, `intent.step_value = farm_step_value(world)`, farm.cc ~2688) prices a step at
  output x the map's mean gems per camp health x gem_value: no walking (~55% of alive time is walking), no premium.
So a 6-10 turn chase of an empty-handed enemy costs an early Prism (premium 1-3) more than it pays, and costs Cassi,
Issac or Willow (low farm rates) less than the bot assumes. Chasing is worth ~6 points by ablation, so the chase stays:
the change only decides it by the same price as the farm.

## Design
- Record each body's farm rate: the last farm_turn's chosen `best_value` (gems a round; check its units and that it is
  premium-inclusive), smoothed if it is noisy (e.g. an exponential average over recent farm turns, with a time
  constant you derive: a job's length, `capture_time` + a typical walk), in `Memory` or a static, with a cold-start
  value from `farm_step_value` until the first farm turn.
- **Chase**: a candidate is chased only when the kill's worth (the existing numerator: life value in gems + bag + held,
  with the bag priced as the killer receives it: for a keeping Prism killer, its premium applies to the bag it takes,
  via `prism_premium`) over the chase turns (the existing `turns`, plus the walk back if you can bound it cheaply)
  beats the body's farm rate. Keep `pressed` / `team_pressed` fights (already engaged) and any defence of our own
  carrier or capture exempt: the opportunity cost applies only to starting a chase.
- **Strike search**: use the same farm rate (gems a round) for `intent.step_value`, converted to the planner's units
  (it now multiplies by gem_value; keep the units consistent).
- Leave the fight simulation, the draft, emblems and the farm itself unchanged.

Build `chase-a` (both parts) and `chase-c` (chase entry only). Save diffs to `research/mx-theia/patches/chase-a.diff`
and `chase-c.diff`.

## Tracing
`debug_block` line when the opportunity cost refuses a candidate the reference would chase:
`CHASEX <round> <handle> <enemy index> <worth per turn> <farm rate>`; and once every 50 rounds per body
`FRATE <round> <handle> <farm rate>`.

## Audit, build, smoke (before returning)
1. Spawn a **read-only** auditor subagent (general-purpose; tell it explicitly: do not edit, create or delete any
   file) with this brief and your diff (`diff -ru bots/variants/chy-ref/src bots/variants/chase-a/src`), asking it to
   check: units (gems vs gold vs health), cold start, stale rates after death/recall/respawn, Cassi/Issac (two bodies,
   linked bags), the exemptions, the planner's step_value readers, fuel.
2. Fix what it finds.
3. Smoke each variant: `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-theia && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/chase-a variants/chy-ref --no-test-draft --fuel 200000 --name mx-theia-t5-smoke-a`
   (256 ladder games; same for chase-c with `-c`). Required: no failed games, no DRAFT-UNFINISHED / PLAN-CHECK.
   Report win rate, OOF counts and how often CHASEX fires per game in a debug build if cheap (a smoke, not a read: do
   not iterate on it). Run long commands in the background; while waiting, keep working or block on a bounded wait
   (e.g. a foreground `until` loop checking the log), and do not end your turn until you hand back: ending your turn
   ends your run.

## Stop condition
Return (SubagentHandback) when both variants build, pass the audit and the smoke. No 10k-game A/Bs, no constant
tuning, no other changes. Report what you changed (files, functions), the auditor's findings and your fixes, the smoke
results, and anything in the design you found wrong or risky.
