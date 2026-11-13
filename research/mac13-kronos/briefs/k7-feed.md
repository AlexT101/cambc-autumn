# Brief k7: Prism hoard probes (four small variants)

You are building probe variants of the Cambridge Battlecode C++ bot `charybdis` for the orchestrator of its macro
refactor. Read `/home/ubuntu/wt/mac13-kronos/AGENTS.md` and `cambc-rules.yaml` (gems, tribute, capture, Prism).
Work ONLY in `/home/ubuntu/wt/mac13-kronos`; do not touch `/home/ubuntu/cambc-autumn` or other worktrees; do not
commit. Never edit `bots/variants/chy-ref` or `bots/charybdis`. Off limits: `src/draft/`, emblem choices. Each
variant: `./copybot variants/chy-ref variants/NAME` (never copy `.cambc/`), then the edit.

## Evidence
The Prism's carried gems (+1.5 Focus each) decide the game: forcing the Prism to bank at 150 / 300 gems lost
28% / 35% against the reference. 75% of Prism deaths are by the enemy Prism and the first Prism death decides 91%.
The Prism's income: its own clears and captures; hand-offs from allies (`leave_for_prism`,
`economy/capture.cc:475`, and the carry picks 'G'/'L'/'Q'/'T' in `economy/farm.cc`) bring only ~25 gems by round
300 against ~200 of its own. The farm values a kept gem's Focus by `carried_bonus` (`economy/capture.cc:163`). In the
endgame a Prism's giant channel (300+ gems, 30+ turns) completes 40% of the time when no enemy is within 8 at its
start, but only 3-9% with one or more enemies within 8; 76% of such attempts start with an enemy within 8.

## Variants
1. `k7-feed`: hand more cleared gem groups to the Prism. In `leave_for_prism`: (a) the unclaimed leave's window
   (`cambc::constants::capture_time` rounds from our first sight of the group cleared, the `remaining` computation
   and the `world.round - left.first >= capture_time` lapse test) becomes `carry_reach()`; (b) `carry_reach()`
   (`2 * capture_time`) becomes `3 * capture_time`, which also widens the farm's 'L' carry picks. Check that the
   lapse logic and the farm's prune bounds that use carry_reach stay consistent.
2. `k7-cb2`: `carried_bonus` returns twice its value (a named constant `kept_gem_weight = 2.0f`). Check every
   caller (farm prunes `keep_most` etc.) still bounds correctly.
3. `k7-cb05`: the same with 0.5.
4. `k7-quiet`: a Prism does not START a tribute channel longer than `params::tribute_window` turns while any enemy
   champion is visible to it within 8 tiles (Chebyshev) - unless the tribute is forced by the round limit
   (`rounds_left(world) <= channel + endgame_slack`, as `any_risk` has it). Find where a tribute is started
   (`submit_here` / `carry_bag` in `economy/bank.cc`) and add the test there for the Prism only; what it does instead
   is whatever the bank branch does when it cannot tribute here (waits / steps). It must not loop on a refused error.

## Stop condition
1. All four build (release). 2. Spawn ONE read-only auditor subagent (tell it explicitly not to edit anything) to
check the diffs against this brief (prune bounds, lapse logic, no change when the conditions are false, release
builds unaffected); fix what it finds. 3. Smoke each in parallel:
`source ~/venv/bin/activate && cd /home/ubuntu/wt/mac13-kronos && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH python tools/ab.py variants/NAME variants/chy-ref --no-test-draft --fuel 200000 --name mac13-kronos-NAME-smoke`
(256 ladder games each): no failed games, no DRAFT-UNFINISHED / PLAN-CHECK. Delete the smoke batches afterwards.
4. Save diffs to `/home/ubuntu/wt/mac13-kronos/research/mac13-kronos/patches/NAME.diff`
(`diff -ru bots/variants/chy-ref/src bots/variants/NAME/src`) as soon as each builds (do 2 and 3 first, then 4,
then 1); the orchestrator starts screening from the diff's appearance. Return what changed per variant, auditor
findings and fixes, smoke results. No large A/Bs.
