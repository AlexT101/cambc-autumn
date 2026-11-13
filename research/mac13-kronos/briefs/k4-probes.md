# Brief k4: farm commitment and calibration probes (six small variants)

You are building probe variants of the Cambridge Battlecode C++ bot `charybdis` for the orchestrator of its macro
refactor. Read `/home/ubuntu/wt/mac13-kronos/AGENTS.md`, `cambc-rules.yaml`, and the study
`/home/ubuntu/wt/mac13-kronos/research/mac13-kronos/s1/README.md` (it is the evidence for these probes). Work ONLY in
`/home/ubuntu/wt/mac13-kronos`; do not touch `/home/ubuntu/cambc-autumn` or other worktrees; do not commit. Never edit
`bots/variants/chy-ref` or `bots/charybdis`. Off limits: `src/draft/`, emblem choices. Each variant:
`./copybot variants/chy-ref variants/NAME` (never copy `.cambc/`), then the edit.

## Evidence (s1)
70% of farm choices are switched away before paying, 109 a team-game before even arriving with nothing changed at
the group; ~1,000 tiles a team-game of displacement during abandoned choices did not move the champion toward its
next choice. Switches happen whatever the chosen value's margin at choice time; typical switch value ratios
(new/old at choice time): S->S 1.5, S->J 1.9, J->J 1.6. Crew joins (J) are priced with almost no hold and a damage
part, paid to the joiner only 18%; the middle band weighs 1.31 while it yields 0.44 of its price; the walk is priced
to the group centre (3-4 rounds more than to attack range) and the hold 1.3 rounds short.

## Variants
1. `k4-st2`: `economy/farm.cc` file-scope `stickiness` 1.2 -> 2.0 (the incumbent group's weight multiplier).
2. `k4-st3`: the same at 3.0.
3. `k4-commit`: a commitment rule instead of a multiplier: while our farm_group is a live or respawning group we
   have not yet reached (not within attack range of a live member / not on its tiles), a different group may replace
   it only if (a) the incumbent is no longer valid or no longer evaluated (taken, held by an ally or enemy, priced out
   by the loop's own tests), or (b) the challenger is a carry pick of a Prism ('G','L','Q','T') or a pick-up of a
   group cleared this turn, or (c) the challenger's value is at least 2.5x the incumbent's value this turn. Once we
   reach the group the ordinary choice (stickiness 1.2) applies. Implement it at the final pick in `farm_turn`
   (where `best` is compared and committed; find where the incumbent's value is known for this turn). Do not change
   other branches (bank, retreat, shop, chase, siege). Add a debug-only trace line `CMT <round> <id> kept|switch
   <old> <new>` when the rule decides.
4. `k4-join`: crew joins priced for the joiner: in the join ('J') value (`farm.cc` around the `part = strength *
   rounds / health` and `hold = carry ? cap_rounds : 0` lines, ~2071-2091), price the hold as the full capture time
   (capture_rounds) like a solo choice, and the gems as our expected share: the group's gems / (the claimers already
   on it + 1) instead of the damage part. Leave proposals ('C') and Monolith operations alone.
5. `k4-mid`: `params::mid_exposure` 1.3611484 -> 1.0 (no middle-band premium; keep every prune bound valid; the
   constants `exposure_most` etc. follow automatically if derived from it; check).
6. `k4-cal`: walk and hold calibration: the walk to a live group priced to attack range of its nearest member rather
   than to its centre (where the farm prices the trip for solo and crew choices, ~farm.cc:1893), and the hold priced
   at capture_time + 1 rounds plus 1 (the measured 6.6 against 5.4) - find `capture_rounds` (capture.cc:9) and make
   the farm's pricing use the measured hold without changing capture logic itself. If either half is impractical
   (prune bounds), do the hold half only and say so.

## Stop condition
1. All six build (release). 2. Spawn ONE read-only auditor subagent (tell it explicitly not to edit anything) for all
six diffs against this brief and the rules (prune bounds still valid, the commit rule cannot deadlock a champion on
an unreachable or invalid group, release builds unaffected by traces); fix what it finds.
3. Smoke each: `source ~/venv/bin/activate && cd /home/ubuntu/wt/mac13-kronos && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH python tools/ab.py variants/NAME variants/chy-ref --no-test-draft --fuel 200000 --name mac13-kronos-NAME-smoke`
(256 ladder games each; run them in parallel): no failed games, no DRAFT-UNFINISHED / PLAN-CHECK. For k4-commit also
one `--debug` smoke (`--name mac13-kronos-k4c-dbg`) and count CMT kept/switch per game.
4. Save diffs to `/home/ubuntu/wt/mac13-kronos/research/mac13-kronos/patches/NAME.diff`
(`diff -ru bots/variants/chy-ref/src bots/variants/NAME/src`). Return what changed per variant, auditor findings and
fixes, smoke results, CMT counts. Do not run large A/Bs. Work fast: these are probes; finish the simple ones (1, 2, 5)
first and write their diffs as soon as each builds, so the orchestrator can start testing them.
