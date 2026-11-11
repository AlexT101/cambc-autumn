# E10 "yield": a dominated Prism keeps out of the dominant Prism's reach (bots/variants/yield)

Read /home/ubuntu/wt/macro-o4/research/macro-delphi/briefs/common.md (TMPDIR rule; output under
/home/ubuntu/wt/macro-o4/replays/delphi-smoke/yield/). Candidate dir `bots/variants/yield` (already a copy of
bots/charybdis). HARD DEADLINE: report by 22:25 UTC. Small change; skip the auditor if the diff is under ~50 lines.

## Why (charybdis mirror)
When the two Prisms come into contact (both alive, in sight within 8), the weaker one dies within 15 rounds:
- at a Focus ratio under 0.5: 36% of the time (844 episodes, 1.6 a game);
- at 0.5-0.8: 9%;
- near even: 6%.

The dominated Prism's death also hands its bag to the dominant one, so the game snowballs.

## Design (minimal)
In bot.cc `decide()`, the work steps already take an `avoid` board (`home_reach_avoid`, `prism_hold_seen`) passed
to `guard_work`. For our Prism only, add to that board every tile within 5 Chebyshev of each **visible** enemy Prism
whose Focus is at least twice ours. 5 is its unit-cast range 4, plus the one step it may take before our next turn.
- Skip tiles on our own spawn, since enemies cannot enter it.
- Use a static bitboard as the existing code does: `copy_into`, then OR.
- If the board would cover our own tile, still apply it, so steps lead out.

Also, when such an enemy Prism is visible, our Prism does not start a fight on it: find where its chase begins
(`chase_with_guard` / fight.cc prey) and skip that target for our Prism. Do this only if it is a one-line veto;
otherwise skip this part.

Debug trace: turns the zone applied (round, enemy Focus, ours, distance).

## Done when
It builds, two local games finish without bot errors, and the trace shows the zone applying. Report briefly.
