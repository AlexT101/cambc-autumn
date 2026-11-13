# Line C: live territory in farm choice (`ia-territory`)

You are an implementer for IAPETUS (orchestrator of the macro refactor of charybdis). Work in the worktree
`/home/ubuntu/wt/mx-iapetus` (branch `mx-iapetus-20261113`). Read `AGENTS.md` and `cambc-rules.yaml` first.
Do not commit, push, or touch `/home/ubuntu/cambc-autumn` (read-only) or other worktrees.

## Problem
Farm choice (`economy/farm.cc farm_turn`) weighs every group by a **static** side-of-map factor: `home_ground`
(`economy/camps.cc`, `min(1, 2 d_e/(d_a+d_e))^home_power`, fixed per group from the spawn walks) and the middle band
(`mid_exposure`). Nothing reads where the enemies actually are: `ChampionBelief::respawn_earliest/latest` is written
in `model/world.cc` but never read by farm; visible enemies' and last sightings' distances never reach the worth.
In the mirror (chy-ref vs itself) the winner out-captures the loser by 107 gems a game, 56% of it in mid groups,
and enemy-half captures are ~0 for both. A team has 2+ bodies dead in ~16% of rounds (respawn takes 60), and
earlier traces found our survivors' farm targets don't change after we kill: we take the fight's own group but
don't use the window. Conversely a group on "our" half is weighted 1 even with the enemy team standing next to it.

Prior: `b4/farm-exposure` (EXPERIMENTS.md, "Batch 4") replaced `home_ground` with another **static** walk-race
weight and read level (49.6). Its hazard data: death risk per champion-round falls by a factor e per ~8-10 steps
of the margin D = d_enemy - d_ally (about a sight radius). Don't repeat a static rewrite; the new part is state.

## Design (yours to refine)
Make a group's exposure depend on who can actually contest it before we finish it:
- Per enemy body, an arrival bound at the group: dead -> rounds to its respawn plus its walk from the enemy spawn
  (use `respawn_earliest`); visible -> terrain distance (`model/enemy_reach`, `Pathing` fields); unseen -> from its
  last known tile (keep it honest: the plain lower bound "distance less rounds since" falls to 0 in a few rounds and
  then says nothing; use what the bot knows, e.g. ally sight coverage, or let unseen bodies fall back to the static
  side weight).
- Our finish: walk + kill + the 6-round capture (the bot already computes these terms).
- A group no enemy can reach before our finish is free whatever its side: its weight rises towards 1 (and the
  middle-band premium, which prices contest, may not apply). Where enemies can arrive first, keep today's static
  weight, or scale by the force arriving (bodies, or the stand's read) against ours.
- Start with the monotone version (only ever frees groups, provably safe ones), measure, then decide whether the
  other direction (discounting own-half groups an enemy force is next to) helps.
- Keep it derived from the rules and measured quantities: respawn time, walks, capture time, sight radius. No new
  hand-picked constants unless measured.
- Mind fuel: farm_turn has SIMD prunes that take the weight as at most 1 (`home_weights()`, `exposure_most`); a
  dynamic weight must keep their bounds valid (a weight above the bound breaks the prunes) or update them. Out-of-fuel
  turns must not rise much (check OOF in each summary).

First measure the opportunity in a few hundred debug games (`--debug`, 2x fuel): how often a group the static weight
discounts below ~0.5 is provably free, and the gems/gold in it. If that is tiny, say so and stop early.

## Process
- `./copybot variants/chy-ref variants/ia-territory`. Build, iterate there.
- A/B (train suite only; IAPETUS judges on others):
  `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-iapetus && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/ia-territory variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mxi/train --name mx-iapetus-C-r<N>`
  in a tmux session named `mx-iapetus-C-r<N>` (no `--threads`). Wait with a background until-loop, never a
  foreground sleep. Kill only by tmux session name. Up to 4 train reads (10,200 games each). Debug smokes on the
  ladder (no `--suites`, 256 games) are cheap for traces. Delete replay batches you've studied.
- For each read find out why it moved (replays: `tools/replay/`, `CAMBC_ANALYSIS=<dir>`; capture gems by side,
  deaths, mid/enemy-half captures, OOF). Keep each version you A/B as `bots/variants/ia-territory-v<N>`.
- Log each step with times to `research/mx-iapetus/logs/C-territory.log`.
- Before returning: spawn a read-only auditor subagent on your diff and fix what it finds; make sure the bot builds;
  play the smoke `py tools/ab.py variants/ia-territory variants/chy-ref --no-test-draft --fuel 200000` (256 ladder games,
  no failed games, no DRAFT-UNFINISHED / PLAN-CHECK).
- Off limits: `draft/`, emblem choice, `bots/variants/chy-ref`, `bots/charybdis`.
- Report: what you built (files, mechanism), every read with CI and OOF, why each moved, the best version's path, and
  what you'd try next.
