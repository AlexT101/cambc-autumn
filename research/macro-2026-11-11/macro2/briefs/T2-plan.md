# T2: chain lookahead in farm target selection (`bots/variants/macro2-plan`)

Read briefs/common.md (same folder) first and follow it. Candidate dir: `bots/variants/macro2-plan`, created with
`./copybot variants/ocean-ref-b7c87cf variants/macro2-plan`.

## Why
Measured on 512 ocean-vs-ocean games (and in solo games against an idle opponent): champions spend ~52-55% of their
alive time walking, ~17-25% hitting camps, ~5% holding captures. Walk legs average ~11 turns (camp->camp median 3,
spawn->camp median 11). Champions walk within 6 tiles of up, asleep, free groups at >=70% HP with small bags and no
enemy in sight ~109 times a team-game without hitting them (wolves 52, clusters 30). ~22 approaches a team-game are
abandoned. Idle time ~4.9%, half of it waiting by respawning groups.
Root cause (a hypothesis to act on): farm (`economy/farm.cc farm_turn`) is a one-job greedy argmax of
`rate(worth, trip + clear + capture + heal trips)` with rate = worth / (rounds * (1 + rounds/H)). It never values
where a job leaves the champion: a job ending next to other camps that will be up (or respawn) when it finishes is
worth more than an isolated one with the same one-job rate. A respawn-timed or on-the-way second job is invisible.

## Design (receding-horizon two-job chains)
1. For each first-job candidate g that the loop prices (solo, claimed-share and crew pricings as now), estimate its
   finish round t_g (now + trip + clear + capture/hold as the value already counts) and its end place (g's tiles /
   centre). Then find the best follow-up job h != g from there: h among the K nearest groups to g by walking
   distance (K small, ~8-12; derive from what keeps cost bounded), excluding groups claimed by allies (comms claims)
   and groups we cannot use (same filters farm already applies: reachability, too_late, monolith rules, etc.).
   Value h with the solo formula farm already uses (worth, trip from g's place, respawn wait if h is respawning at
   t_g + trip (a wait is just rounds; the max_wait skip should not apply to second jobs), clear, capture, heal trips
   given our health after g). Keep it cheap: reuse existing per-group quantities (worth, clear rounds, distances
   from pathing fields/centre fields) rather than re-running the whole per-group pricing.
2. Rank first jobs by the chain value `rate(worth_g' + worth_h, rounds_g + rounds_h)` where worth_g' is the worth
   the first job's current pricing gives us (our share for crews/claims) and rounds_g the rounds it currently uses.
   A candidate with no usable follow-up keeps its one-job value expressed the same way (so comparisons are fair:
   every candidate is scored as a chain of 1 or 2). Only the first job is committed; next turn re-plans (receding
   horizon), so stickiness/crew holds stay as they are (apply them to the chain value).
3. Keep banking turns (`farm_banking`, `from_altar_value`), the opening plan, sieges, monolith ops and crew
   proposals working; where the chain logic does not obviously fit (banking variant), leave the current logic.
4. Prune: evaluating chains for every group may be costly on 100-group maps; compute the chain only for the best
   M first-job candidates by one-job value (M ~ 6-10) plus the current farm_group, then take the best chain. Make M
   and K named constants in params.h with a one-line rationale.
5. Debug: add a debug_block trace (compiled out in release) printing, every ~50 rounds, the chosen chain (g, h,
   one-job value vs chain value) so the lead can inspect replays if needed.

## Not in scope
No changes to combat, banking thresholds, shopping, comms, the draft or emblems. No new params beyond M, K and any
needed discount. Don't retune existing constants.

## Done when
Builds; two or three local games against variants/ocean-ref-b7c87cf run to completion with no bot errors (one ladder
map, one generated map); the auditor's findings are addressed. Report: what you built, where, the cost bounds.
