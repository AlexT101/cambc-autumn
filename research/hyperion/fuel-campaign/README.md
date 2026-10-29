# Fuel campaign, 2026-10-29

An orchestrated push on astraeus's fuel: ~35 worker agents in worktrees, merged in rounds with byte-identical 100M
benches and real-budget A/Bs. Shipped as CHANGES 214-230; results per round in EXPERIMENTS `## Fuel` ("Fuel round 1"
to "Fuel round 7", "Fuel phase 2"). Headline: out-of-fuel turns against hecate (test drafts) 11101 -> 7325 (-34%) at
m6; against a fixed 3938c0f reference (own drafts) ~-24% at m7, win rate level.

- [OPEN-ITEMS.md](OPEN-ITEMS.md): every worker's findings, profiles, open leads with estimates, and dropped attempts
  with numbers, in the order they came in. Read the sections for your area before starting: most obvious ideas were
  tried here.
- [BRIEF.md](BRIEF.md): the brief every worker got (rules of the work, how to measure, report format), with the
  phase 2 update at the end.
- [BASELINE.md](BASELINE.md): the frozen baseline's numbers (8ec2c4d).

Not in git: bench JSONs and A/B batches (`replays/fuel/orch/`, `replays/batch-*-ab-orch-*`), frozen bots
(`bots/variants/astraeus-m1` ... `m7`, `astraeus-8ec2c4d`), worker worktrees (`.claude/worktrees/`) and the session
scratchpad paths some items cite. Paths starting `MAIN/` mean the repository root.

Lessons that matter most for the next round:
- Exact (100M byte-identical) cuts can still raise real-budget out-of-fuel turns: always A/B, and check the turns a cut
  makes dearer, especially fight turns (CHANGES 222; OPEN-ITEMS "Phase 2 B").
- The fuel gates are real brakes even after the late-finish fix: removing any big one multiplied run-outs (FUEL-GATES).
- `farm_turn` is flattened: farm-loop changes shift codegen across every turn; measure the whole bench.
- Bench frozen copies, never the live `bots/astraeus` (`cambc run` rebuilds it per game).
- Tools: `tools/fuel/census` (where real-budget turns run out), `tools/fuel/oof_bot.py`, `tools/fuel/simprof`,
  `tools/cpu_slots.py` (concurrent benches share the cores).
