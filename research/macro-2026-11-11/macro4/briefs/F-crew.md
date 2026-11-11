# Brief F: crew prices that follow arrival times (every comp)

You are an implementation subagent for the macro4 lead. Work ONLY in /home/ubuntu/wt/macro4 (git worktree, branch
macro4-20261111). Never touch other checkouts, never edit bots/variants/ocean-ref-b7c87cf, bots/ocean, or any
bots/variants/macro4-* other than your own, never write to any Claude memory directory, never run ab.py / fgate / A/B
tests, commit nothing. Read /home/ubuntu/wt/macro4/AGENTS.md and cambc-rules.yaml first.

## Candidate
`./copybot variants/macro4-hub2f variants/macro4-crew`; edit only bots/variants/macro4-crew/src. No draft/ or emblem
changes. hub2f is our best (55.5% vs ref on fresh suites).

## Why (measured, ocean mirrors)
A camp group's clear finishes when sum_i o_i * (t - a_i)+ reaches its health (a_i = when member i starts dealing).
Camps hit the nearest champion, so the first to arrive takes every hit until help comes. Joint clears are
sequential: the second dealer arrives 9.6 rounds late on Elk and 15.4 on Golem; joint Elk clears take 22 rounds and
800 damage vs 17.5 rounds and 584 solo. The proposer's crew price (economy/crew.cc plan_crew ~224-330,
share_damage ~204-222, and the farm loop's 'C' pricing in economy/farm.cc ~2150-2205) prices expected allies and
unseen claimers at full output from round 0, while the joiner side already prices claimers' delay
(farm.cc crew_work ~1132-1150, work_arrival ~1061-1130; model/crew_work.h earliest_work_delay). So proposers
over-value crews and walk into long solo phases. (Line numbers are approximate; read the code.)

## Design: make the proposer's price consistent with the joiner's
- plan_crew: give every member an arrival a_i (ours = our steps; expected allies via earliest_work_delay and, for an
  ally finishing a hold, its hold timer left; unseen claimers via whatever the joiner side uses for them). Compute the
  finish T from the schedule (piecewise: output accumulates as members arrive), drop members with a_i >= T.
- Damage taken: the solo phase's camp fire x (a_2 - a_1) on the first arriver, then the existing min_camp_damage at
  the crew's full output for the rest; share_damage weights each member by time present.
- The farm 'C' price: our share becomes our damage fraction of the group (not S/O), and its rounds become T.
- No new constants: arrivals come from fields and the existing dash/arrival models. Previous "assemble before waking"
  (wait until all arrive) LOST: do not add any waiting rule; this is pricing only.
Add `debug_block` lines prefixed `CREW` printing the schedule (a_i, T, solo damage) when a crew price is computed.
Keep fuel bounded.

## Done when
- Builds debug and `--release` (sequentially), 1-2 smoke games vs ocean-ref without errors.
- A read-only auditor (Explore or Plan) reviews your diff (correctness, fuel, magic numbers); fix what it finds.
- Final reply: design as built, diff summary, audit findings and fixes, CREW trace counts, and for one smoke map the
  joint-clear second-dealer lag before (hub2f) and after if you can measure it from the replays
  (see /home/ubuntu/wt/macro4-maps/scr/stagger.py, run it with python3 on an extracted analysis dir).
