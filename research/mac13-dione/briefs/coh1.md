# coh1: one give-way verdict shared by farm, goal walks and retreat (charybdis macro, DIONE programme)

You are an implementation subagent for DIONE, an orchestrator improving the macro of the Cambridge Battlecode bot
charybdis. Work ONLY in the git worktree `/home/ubuntu/wt/mac13-dione` (branch `mac13-dione-20261113`). Never touch
`/home/ubuntu/cambc-autumn` (read only), other worktrees under `/home/ubuntu/wt/`, `bots/charybdis`, or
`bots/variants/chy-ref` (frozen reference: never edit). Do not commit; do not push. Read
`/home/ubuntu/wt/mac13-dione/AGENTS.md` and `cambc-rules.yaml` first (rules are engine-verified; C++ only; comment
only counterintuitive behaviour, concisely; `unity.cpp` includes every `.cc`).

## Setup
`cd /home/ubuntu/wt/mac13-dione && ./copybot variants/chy-ref variants/coh1` (never copy `.cambc/`). All edits go in
`bots/variants/coh1/src`. Python: `source ~/venv/bin/activate`. Fast runner prefix for every ab.py run:
`CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH`
(debug runs that need `team-?.stdout` traces work under fastrunner; only debug drawings need stock). Every A/B is
`py tools/ab.py variants/X variants/chy-ref --no-test-draft --fuel 200000 ...`; run long ones in a tmux session named
`mac13-dione-coh1-<tag>` and wait with background until-loops on `replays/ab/<name>/summary.json` (foreground sleep is
blocked; commands over ~3 min get backgrounded). Leave `--threads` off. Never use fgate.py, gates, live tests or other
opponents. Delete replay batches you no longer need (`replays/batch-*<name>*`; ~0.3 GB per 1k games). Off limits: the
draft (`draft/`, picks) and emblem choices.

## The problem (measured in the chy-ref mirror, 2x fuel)
- Champions walk ~55-60% of alive time. 31% of walked steps exceed the BFS path between leg ends, almost all in legs
  with an enemy within 9; pure farm legs with no enemy near waste 0%.
- The waste is farm <-> retreat ping-pong: ~59 F->R->F cycles a team-game (D-line branches, `bot.cc:764`
  `D <round> <handle> <branch> <farm_group> <claim>`), the retreat run median 1 turn, farm resumes median 2 turns;
  45 R->F->R with a farm interlude of <=10 turns, ~108 farm turns a team-game inside those interludes. The mixed
  legs (farm+retreat 6.4% of all walking, farm+retreat+other 2.5%, farm+chase+retreat 1.9%) carry the excess.
- Mechanism (from code): `decide()` (`bot.cc` ~378-560) asks `want_home` (`combat/fight.cc:597`: drawn_home (a pack's
  zone), camp_trapped / mono_trapped, camp_fled, Willow exposure, finish_heal, stand_lost_at) and retreats when it
  fires. Otherwise `guard_work` (`combat/guard.cc:857`) keeps the *next step* (radius 1, or a dash's) off tiles
  want_home would send us back from, and farm (`economy/farm.cc` `farm_turn`) keeps choosing its target with no
  dynamic enemy term (only crews and Monoliths look at enemies). So the best target near an enemy stays best, the
  step guard stalls the walk at the zone edge, an enemy step puts us inside, want_home fires, we retreat a step, farm
  sends us in again.
- Two earlier attempts in this programme read level (50% of 10k): `tp1` (trip pricing on a flood avoiding the step
  guard's enemy-reach tiles; it moved the farm-near-enemy waste only 1.6 points, because pure-farm legs already walk
  shortest paths), and `dz1` (a one-sided "kill zone" of burst-ready enemy Prisms priced into farm choice, goal
  walks, retreat and banking: ~70% fewer deaths near such Prisms, yet level, because the time saved went into standing
  still (still 9.1% vs 7.9% of time) rather than farm). Lesson: excluding a target is worthless unless the champion
  takes a productive alternative at once; and pricing a separate zone model does not remove the disagreement, since
  retreat still fires on its own predicates.
- Farm time is strongly leveraged: idling the farm branch 1 turn in 20 lost 7.6 points. Turns recovered from the
  ping-pong and spent on farm are worth a lot; turns turned into standing still are worth nothing.

## The design (make the decision layers agree)
The principle: a champion that is going to give way never walks in, and one that walks in has a plan.
1. **One give-way verdict.** Factor want_home's enemy-dependent predicates (drawn_home, stand_lost_at, and Willow's
   exposure test; leave the camp/heal ones as they are) into one function that answers "would I give way standing at
   tile p, given what can reach p before my next turn", usable for any tile, cached per turn. want_home calls it at
   our tile; nothing else changes want_home's answer at our tile.
2. **Farm target choice uses the same verdict.** A target whose work tile (where we would stand to hit or hold; the
   approach's last tiles) gives way under the current enemy beliefs is not chosen *unless* a plan holds there (below).
   Not a price factor: the target is infeasible now, and farm picks its next best target in the same turn (farm already
   ranks targets; reuse that, do not add a second chooser). Make sure the prune bounds in farm_turn stay valid
   (excluding targets can only lower the best, never raise a bound).
3. **Repelled targets.** When retreat fires while we had a farm target, remember (in Memory) that target with the
   threat that repelled it (enemy ids and their last seen positions). Farm does not re-pick it while that threat is
   believed able to reach its work tile before we could finish its work, by the same give-way verdict on its believed
   position (an unseen enemy's reach grows one tile a round from where it was last seen: if you use that, cap it at the
   believed-position machinery the bot already has; read `model/` beliefs first). Lift the mark as soon as the verdict
   clears. Same verdict, so no new constants.
4. **A plan when walking in.** If farm does choose a target in or near an enemy's reach (because the verdict at its
   work tile says we do not give way there: we win the stand, or the hold outlasts what can reach us), then while we
   walk in and work, want_home should not flip on the same facts it already priced: give retreat hysteresis keyed on
   facts (new enemy seen, our health below what the verdict assumed, an enemy's Focus/bag grown), not on a counter.
5. **Goal walks.** The goal walk to a chosen target should not path through tiles where the verdict gives way when an
   equal-length (or slightly longer, bounded by what the target's value allows; derive the bound from farm's own rate
   pricing) route avoids them; otherwise the target was infeasible and step 2 already dropped it.
Keep everything else (strike search, chase, contest, carry/bank, Prism hold logic, Willow support) as it is unless
the diagnosis shows the ping-pong also lives there; if it does, apply the same verdict there in the same way.

## How to work
1. **Diagnose first** with a debug mirror (`--debug --suites maps/suites/mac13/study`: 1,024 maps = 2,048 games, ~5-10 min;
   ab.py has no game cap, so for a smaller batch make a suite directory of symlinks to a subset of the study maps). Add a
   `debug_block` trace naming which want_home predicate fires on each retreat turn, and the farm target before it. Find
   which predicates drive the F->R->F cycles, and whether the champion walked in or the enemy walked up. Design the
   verdict around what you find; report the breakdown. Scripts from earlier analysis you may reuse: `/tmp/dione/osc.py`
   (cycle counts from D lines; it reads `replays/.analysis-dione`, built by `node tools/replay/extract.mjs <batch>
   --out <dir> --threads 24`), `/tmp/dione/timeshare.py <analysis_dir> <cand_team_name>` (time shares per team).
2. Implement. Keep it fuel-aware: the verdict at many tiles must be cheap (cache per turn; evaluate only candidate
   work tiles farm actually considers, after its cheap prunes). OOF turns should not rise much over chy-ref
   (~600 per 10k games at 2x fuel).
3. When it builds and a 256-game smoke has no failed games, freeze a snapshot `./copybot variants/coh1 variants/coh1-s1`
   and message nothing; just continue (the orchestrator may A/B the snapshot).
4. Verify with a debug batch: F->R->F cycles a team-game should fall by at least half; time share of camp + capture
   (camp, on_camp_tile) should rise and `still` should not; deaths should not rise. If the freed turns go to standing
   still, find out why and fix it (that is the failure dz1 had).
5. Spawn a **read-only** auditor subagent (tell it explicitly: do not edit any file) to check your diff against this
   design and the rules for bugs (prune-bound validity, stale caches, wrong-team reads, fuel blowups, Memory fields not
   reset on death). Fix what it finds.
6. Final checks: builds; `py tools/ab.py variants/coh1 variants/chy-ref --no-test-draft --fuel 200000` (256 ladder games)
   with no failed games and no DRAFT-UNFINISHED / PLAN-CHECK. Save the diff:
   `diff -ruN -x .cambc bots/variants/chy-ref/src bots/variants/coh1/src > research/mac13-dione/patches/coh1.diff`.
   Kill any tmux sessions you started; delete your replay batches except the final smoke's summary.

## Stop condition and report
Stop when the final checks pass. Report (via your final message): what you changed (files, functions), the
diagnosis breakdown (which predicates drove the cycles), the verification numbers (cycles, time shares, deaths,
OOF before/after), the smoke result, the auditor's findings and fixes, and anything you suspect still leaks.
