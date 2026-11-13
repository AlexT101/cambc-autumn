# fc1: farm targets that hold (commitment and team assignment), charybdis macro, DIONE programme

You are an implementation subagent for DIONE, an orchestrator improving the macro of the Cambridge Battlecode bot
charybdis. Work ONLY in the git worktree `/home/ubuntu/wt/mac13-dione` (branch `mac13-dione-20261113`). Never touch
`/home/ubuntu/cambc-autumn` (read only), other worktrees under `/home/ubuntu/wt/`, `bots/charybdis`,
`bots/variants/chy-ref` (frozen reference: never edit), or `bots/variants/coh1*` (another agent's work). Do not commit;
do not push. Read `/home/ubuntu/wt/mac13-dione/AGENTS.md` and `cambc-rules.yaml` first (rules are engine-verified; C++
only; comment only counterintuitive behaviour, concisely; `unity.cpp` includes every `.cc`). Off limits: the draft
(`draft/`, picks) and emblem choices.

## Setup
`cd /home/ubuntu/wt/mac13-dione && ./copybot variants/chy-ref variants/fc1` (never copy `.cambc/`). Edit only
`bots/variants/fc1/src`. Python: `source ~/venv/bin/activate`. Fast-runner prefix for every ab.py run:
`CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH`
(`--debug` builds' `team-?.stdout` traces work under it). Every A/B is `py tools/ab.py variants/X variants/chy-ref
--no-test-draft --fuel 200000 ...`; run long ones in a tmux session named `mac13-dione-fc1-<tag>` and wait with
background until-loops on `replays/ab/<name>/summary.json` (foreground sleep is blocked; commands over ~3 min get
backgrounded). Name every run `mac13-dione-fc1-...` and only ever delete or kill things carrying exactly that prefix
(another agent's runs are named `mac13-dione-coh1-...`; do not match them). Leave `--threads` off. Never use fgate.py,
gates, live tests or other opponents. ab.py has no game cap: for a smaller debug batch make a suite directory of
symlinks to a subset of `maps/suites/mac13/study` maps (1,024 maps there = 2,048 games).

## The problem (measured in a 2x-fuel debug mirror of chy-ref, 200 games, D lines `bot.cc:764`:
`D <round> <handle> <branch> <farm_group> <claim>`; script `/tmp/dione/trips5.py`, reading
`replays/.analysis-dione`, an `extract.mjs` dir of that mirror)
A "trip" = a run of farm-branch (F) turns with the same farm_group. For non-Prism champions (~2,200-2,700 farm turns a
team-game): 28% of farm turns end in our own capture, 22% in an ally's (fine: the carry hands clears to the Prism),
5% the enemy took it, 11% end in a retreat, 9% hit camps then switched, and **14-17% of farm turns are walks toward a
target that is then abandoned without hitting it ("switched-walk", ~47 trips a team-game, ~8 turns each)**. Those
walks made only ~31% progress toward the target chosen next: ~200 wasted champion-turns a team-game for non-Prisms,
~40 for the Prism, together ~5% of all team turns. Idling the farm branch 1 turn in 20 lost 7.6 points, so farm turns
are strongly leveraged: recovering a few percent of team turns is worth several points.
Breakdown of the 47 abandoned trips (non-Prism, per team-game):
- a mate also targeted the same group at the switch: 22.5 (10.6 with that mate already on it and in sight when we
  started; 7.0 the mate joined later; 4.9 the mate was on it but out of our sight when we started);
- no mate on it: 24.2, of which the group was respawning the whole trip (state 3 throughout): ~20 overall, and alive and
  asleep throughout (state 1, awake 0): ~16 overall (the categories overlap the mate split);
- an ally was nearer the target than us at the switch in ~30 of 47.
So two failures: (1) duplicate targeting: two bodies walk at one group, and one gives way after walking; (2) target
instability: the greedy re-pick each turn (`economy/farm.cc` `farm_turn`, per-champion rate pricing, with crews in
`economy/crew.cc` and claims in `model/comms.{h,cc}`) abandons a target without new information (respawn waits,
asleep groups).

## The design
Principle: a champion's choice and its mates' choices should be consistent, so a walk once started is finished
unless information changes.
1. **Diagnose first.** In a debug build add a `debug_block` trace at each farm target change: old and new group,
   their rates (as farm_turn priced them this turn and, if you can, last turn), the old target's state and crew, and a
   cause tag (crew/claim change, a mate seen, state/respawn info changed, rate drift with no new information, threat).
   Run ~500-1,000 debug mirror games and tabulate causes by turns wasted. Report the table.
2. **Team-consistent assignment.** When choosing, account for mates who will be at the group first, from what they
   post (claims in the shared bytes) and what we see, and how many bodies the group's clear actually needs (the crew
   logic already sizes crews; make the choice use the same sizing so a body that crew sizing would send away never
   picks it). If a mate's claim beats ours (it is nearer / arrives first) and the crew does not need us, we do not
   pick it. Ties must break the same way on both sides (both mates must reach the same verdict from what each knows,
   e.g. by ETA then id), or the two will mirror each other. Charybdis lacks ocean's 507 comms slots (told tiles);
   porting them is allowed if the diagnosis shows unseen mates matter (they were ~5 of 47 trips).
3. **Commitment without sunk-cost errors.** Switching should happen when information changes (a state read, a mate's
   claim, an enemy, a respawn seen), not because noisy estimates drift each turn. Implement it as consistency: the
   rate of the current target and the alternative must be priced the same way (same respawn belief, same crew
   assumptions) each turn; where an estimate is uncertain (a respawn timer not seen, a group not in vision), keep the
   belief stable until an observation updates it. If you add hysteresis, derive its size from a measured quantity
   (e.g. the estimate's error), not a hand-picked constant.
4. **Respawn waits.** Walking to a respawning group is right only if we arrive no earlier than needed and the wait is
   priced into the rate; check that the respawn belief used in pricing is the one the switch later reacts to.
Keep everything else (retreat, strike search, carry/bank, Prism hold, Willow) unchanged. Keep the farm_turn prune
bounds valid (any exclusion may only lower a target's value; any added value must be inside the prune bounds).

## How to work
1. Diagnose (above). 2. Implement. Fuel: keep OOF turns near chy-ref's (~600 per 10k games at 2x fuel). 3. When it
first builds and a 256-game smoke has no failed games, freeze a snapshot `./copybot variants/fc1 variants/fc1-s1` and
continue. 4. Verify with a debug batch: switched-walk farm turns down by at least half, captured / camp time up, still
time not up, deaths not up (reuse `/tmp/dione/trips5.py` adapted to your analysis dir, and `/tmp/dione/timeshare.py
<analysis_dir> <cand_team_name>`; extract with `node tools/replay/extract.mjs <batch> --out <dir> --threads 24`).
5. Spawn a **read-only** auditor subagent (tell it explicitly: do not edit any file) to check your diff against this
design and the rules (prune-bound validity, symmetric tie-breaks, stale caches, comms layout overflow, Memory reset on
death, fuel). Fix what it finds. 6. Final: builds; `py tools/ab.py variants/fc1 variants/chy-ref --no-test-draft
--fuel 200000` (256 ladder games) with no failed games and no DRAFT-UNFINISHED / PLAN-CHECK. Save the diff:
`diff -ruN -x .cambc bots/variants/chy-ref/src bots/variants/fc1/src > research/mac13-dione/patches/fc1.diff`. Kill your
tmux sessions; delete your replay batches except summaries.

## Stop condition and report
Stop when the final checks pass. Report: what you changed (files, functions), the diagnosis table, verification
numbers before/after (switched-walk turns, time shares, deaths, OOF), the smoke result, the auditor's findings and
fixes, and suspected remaining leaks.
