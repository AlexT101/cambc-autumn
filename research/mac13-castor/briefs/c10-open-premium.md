# Brief C10: the Prism gem premium in the opening plan (implementer, licence to iterate)

Worktree `/home/ubuntu/wt/mac13-castor` (branch `mac13-castor-20261113`; never push, never touch `main` or
`/home/ubuntu/cambc-autumn` except to read). Follow `AGENTS.md` and `cambc-rules.yaml`. Don't change drafts (which
champions are picked) or emblem choices; the opening plan's group assignments are yours.

## Setup
`./copybot variants/c7-pgem variants/c10-open` (never copy `.cambc/`); edit only `bots/variants/c10-open/src`.
`variants/c7-pgem` (v4) is the programme's best: chy-ref plus `prism_premium` (economy/capture.cc): the worth of one
more gem in a keeping Prism's bag beyond itself, expm1(k x rho x H) (k: camp output per gem of Focus, rho: the team's
gems per output-round, H: rounds the bag stays kept), used wherever the bot decides who gets a group's gems (the
Prism's farm, `holder_value`, leave-for-Prism, handoffs, the allies' crew/claim pricing). Against chy-ref it reads
train 53.0% (52.0-53.9), dev 53.0%; earlier build c7a dev 53.1, hold 52.7, conf 52.7, x1 53.5. The gain comes from
consistency: the allies now value the Prism's gems as the Prism does, so the Prism holds 6-7 points more of the
team's gems at equal totals, its Focus is 13% higher at r300 and it dies first 28% of games instead of 40%.

## Why
One decision still values gems without the premium, and it runs exactly when the premium is largest (traced median
~3 extra gems a gem before r100, 1.8 at r100-199): the opening plan (`draft/open_plan.{h,cc}`, solved in the draft's
first turn; `economy/farm.cc` `open_plan_choice` follows its steps until round `params::open_plan::horizon` = 100,
weighted `params::open_plan::weight`). Its model values a capture as `gems + per_gold x gold x bonus` for the holder
and names as holder "the attendee with the best gold bonus" (open_plan.cc ~l.44 and ~l.187-196), so the plan sends
early gem groups' payouts to Vesper (gold bonus) or whoever, and plans bodies' routes accordingly; the Prism's own
plan does not seek gem groups for their Focus either.

## The design
1. In the plan's model, a capture's worth to body b is `gems x (1 + premium_b) + per_gold x gold x bonus_b`, where
   premium_b is the same derivation as `prism_premium` evaluated at the plan's state: zero for non-Prism bodies; for a
   Prism, k from its base stats (`raw_output` at base Focus and +1.5) and rho / H from the same priors `prism_premium`
   uses before any game data (`income_prior_gems`, `prior_rounds_per_gem`, the team's summed base `camp_output`; H to
   the win at that pace). Optionally let the premium fall with the plan's simulated Prism bag (it is non-increasing in
   gems). Share one helper with `prism_premium` if you can (the draft code may not see World; then factor the formula).
2. The holder is the attendee for whom the capture is worth most (not the best gold bonus), consistent with
   `value_holder`.
3. Check that the in-play follow (`open_plan_choice`, the farm's standing-choice weight) and `left_for_prism` don't
   fight the plan's new holders (e.g. an ally planned to clear a gem group the Prism will hold).
4. Draft precompute must still finish in the draft's first turn (10M): check headroom with
   `tools/draftlab/firstturn.py --need` (AGENTS.md "Draft precompute"); no DRAFT-UNFINISHED / PLAN-CHECK.

## Measuring and iterating
`source ~/venv/bin/activate && cd /home/ubuntu/wt/mac13-castor && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/c10-open variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mac13/train --name mac13-castor-c10-trainN`
(10,240 games, ~5-10 minutes, noise ~1 point). It helps if it beats v4's 53.0% on train by more than noise. Iterate on
`train` only (never `dev`, `hold`, `conf`, `x1`). Measure the Prism's share of team gems at r100/r150/r200
(`research/mac13-castor/scripts/bybot.py DIR` on an extract.mjs dir of the A/B's batch; `node tools/replay/extract.mjs
BATCH --out DIR`); debug traces with `--debug` (`debug_block({ printf(...); })` only, compare debug with debug).
Report every full train reading; keep each tested variant as a directory or saved diff. tmux sessions
`mac13-castor-c10-*`; no foreground sleep; don't end your run while a run you started is in flight.

## Before you return
1. A **read-only** auditor subagent (told explicitly not to edit anything) checks your diff
   (`diff -ru bots/variants/c7-pgem/src bots/variants/c10-open/src`) against this design and the rules. Fix what it
   finds.
2. Build and smoke: `CAMBC_BIN=... FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/c10-open variants/chy-ref --no-test-draft --fuel 200000 --name mac13-castor-c10-smoke`
   (256 ladder games): no failed games, no `DRAFT-UNFINISHED` / `PLAN-CHECK`.
3. Save `research/mac13-castor/patches/c10-open.diff` (against c7-pgem) and `c10-open-full.diff` (against chy-ref).
   Don't commit. Kill your tmux sessions.

Stop when implemented, audited, built, smoked, with at least one full train reading of the final variant. Return:
the changes, every train reading, the Prism's early share before/after, first-turn fuel headroom, doubts.
