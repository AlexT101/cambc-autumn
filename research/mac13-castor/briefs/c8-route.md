# Brief C8: the farm's choice sees where a job leaves the champion (implementer, licence to iterate)

You are an implementation agent for the CASTOR macro programme on the Cambridge Battlecode bot `charybdis` (C++).
Work only in the worktree `/home/ubuntu/wt/mac13-castor` (branch `mac13-castor-20261113`; never push, never touch
`main` or `/home/ubuntu/cambc-autumn` except to read). Read `/home/ubuntu/wt/mac13-castor/AGENTS.md` first and follow
it (it says to read `cambc-rules.yaml`: do). The C++ API is `docs/api/cpp.md` and `sdk/cpp/cambc.h`.

## Setup
- `cd /home/ubuntu/wt/mac13-castor && ./copybot variants/c7a-pgem variants/c8-route` (never copy `.cambc/`). Edit only
  `bots/variants/c8-route/src`. Never edit `bots/variants/chy-ref` or `bots/charybdis`; other implementers work in
  other `bots/variants/c*` directories: don't touch them.
- Don't change drafts (`draft/` picks) or emblem choices.

## Why (measured)
Solo games (chy-ref against `bots/idle`, 1,024 study maps, no enemy at all) reach 1000 tributed gems at round 667 on
average, about the mirror's median winning-bag round (650): the enemy barely slows our farm, and a team whose economy
leads by 10-25% at r300 (no kills yet) wins 62%, by 25-50% 64%. In those solo games champions walk ~50% of their
rounds (empty to a camp 19%, with a bag to a camp 8%, to an altar 17%), hit camps 24% and hold captures 6%, while
56% of our own side's gem-weighted group-rounds sit asleep (monsters up, nobody there) and 87% of the enemy side's.
The Prism's walks to its next hit average 14.5 rounds.

The farm (`economy/farm.cc` `farm_turn`; `rate()` in `economy/camps.cc`) picks the job with the best
`rate = worth / (rounds x (1 + rounds / H))`, `H = cycle_horizon` = 100 rounds x max(1, map side / 50): a greedy
gems-a-round choice over one job, with a hand-set penalty on long ones. It does not see where the job leaves the
champion: a group in a dense pocket of groups (short walks onward) and an isolated one with the same rate score the
same, though the first leads to more work. For a renewal process (repeated jobs) the optimal greedy rule is not
worth / rounds but worth - rho x rounds + V(end), with rho the champion's attainable rate (its opportunity cost per
round) and V the value of the place the job ends (e.g. the best onward job from there: max_h worth_h - rho x
rounds(end -> h), counting h only if it will be up and unclaimed by arrival). The `1 + rounds / H` term is a stand-in
for this, without the place.

## The design
1. An onward value for ending a job at group g: from g's capture tiles, the best next job's net value at the
   champion's rate rho (worth - rho x (walk + clear + hold)), over groups that will be up when it gets there (respawn
   timers are known for seen groups, `World::camps[g]`) and not claimed by an ally (`comms::claim_of`), with walking
   distances between groups (static, precompute or cache lazily: groups x groups, cheap) and the champion's clear
   model (`fastest_clear` / `camp_output`). rho: the champion's own measured rate (the bot tracks income: shop.cc
   `income_rates`, `gem_income_rate`), or the best current job's rate, whichever you can justify; derive, don't pick.
2. Choose jobs by worth - rho x rounds + onward(g) instead of the rate with its (1 + rounds / H) penalty, keeping the
   farm's other terms (risk/exposure weights, crews, banking, carried Focus) as they are. Where the farm's pruning
   bounds assume the old form, keep them valid (bounds must stay upper bounds, or drop the prune).
3. Only one step of lookahead; keep it cheap (top candidates only if needed). Fuel matters only for not running out:
   A/Bs run at 2x fuel (200k a turn), but a turn that runs out loses its moves, so watch the out-of-fuel counts in
   the summaries and keep them near the reference's.

## Base
You build on `variants/c7a-pgem`, the programme's current best (chy-ref plus a derived premium on gems carried by a
keeping Prism, `prism_premium` in economy/capture.cc: train 52.8% (51.9-53.8), dev 53.1%, hold 52.7% against
chy-ref). Keep its changes. Your A/Bs are still against `variants/chy-ref`; your piece helps if your variant beats
52.8% on train by more than noise (~1 point at 10k games). Diff against the base for your patch
(`diff -ru bots/variants/c7a-pgem/src bots/variants/c8-route/src`), and also save the full diff against chy-ref.

## Measuring and iterating
- Farming speed: `source ~/venv/bin/activate && cd /home/ubuntu/wt/mac13-castor && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/solo.py variants/c8-route variants/c7a-pgem --name mac13-castor-c8-soloN --suites maps/suites/mac13/study --one-side --fuel 200000`
  (round to 1000 and collected @150/300/600, paired per map; `--debug` for traces). Target: several % faster.
- Win rate: `CAMBC_BIN=... FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/c8-route variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mac13/train --name mac13-castor-c8-trainN`
  (10,240 games, noise about +-1 point; the box is busy: 10-20 minutes). Iterate on `train` only (never `dev`,
  `hold`, `conf` or `x1`).
- Turn budgets: `tools/replay/turn_budget.py` on a debug batch after `node tools/replay/extract.mjs BATCH --out DIR`
  (set `CAMBC_ANALYSIS=DIR`); a copy that runs from this worktree is `research/mac13-castor/scripts/turn_budget.py`.
- Report every full solo and train reading, not only the best; keep each tested variant as a directory or saved
  diff. Debug traces: `debug_block({ printf(...); })` only. Run long commands in tmux sessions named
  `mac13-castor-c8-*`; foreground sleep is blocked. Don't end your run while a run you started is in flight.

## Before you return
1. Spawn a **read-only** auditor subagent (tell it explicitly not to edit anything) with the design and your diff
   (`diff -ru bots/variants/c7a-pgem/src bots/variants/c8-route/src`) to check it against the design and the rules
   for bugs. Fix what it finds.
2. Make sure the bot builds and passes the smoke:
   `CAMBC_BIN=... FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/c8-route variants/chy-ref --no-test-draft --fuel 200000 --name mac13-castor-c8-smoke`
   (256 ladder games): no failed games, no `DRAFT-UNFINISHED` / `PLAN-CHECK`.
3. Save the diff to `research/mac13-castor/patches/c8-route.diff`. Don't commit. Kill any tmux session you started.

Stop when the design is implemented, audited, builds and passes the smoke, with at least one full train reading of
the final variant. Return: what you changed (the onward value, rho's derivation, where the choice changed), every
solo and train reading, turn-budget changes (walking share), and anything you were unsure about.
