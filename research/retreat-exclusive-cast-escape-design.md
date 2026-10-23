# Retreat casts versus an actual escape step

2026-10-23. Source-only prospective review of current main and `willow-upstream-presence-work`; no implementation, instrumentation, build or runtime. Public Lost World Prism291 is a motivating geometry example, **not** an authenticated execution of this source.

## Actual source contract

`retreat()` preserves CH97's sure basic kill first (for ranged, only when no other threat reaches the current tile or an escape dash still clears danger), then melee attacks/resets. It calls `cast_at_enemies(world, escape_step_value)` **before** safe banking, `dash_away`, `flee_camps` and `retreat_step`. There is no pre-cast selected escape endpoint.

In `abilities.cpp`, `enemy_cast` uses `min_value40 + walk210` for a walking-exclusive spell, unless native movement is already unavailable or its existing free-stun rule waives the walk price. A407-damage nonlethal AoE can therefore clear250 without comparing a specific move. This is a structural possibility, not proof that retreat selected the public291 spell. `Cast` currently retains aggregate worth/slot/target, not the distinction between raw damage, kill and interruption.

The remaining free-stun logic (called `keep_walk` in TODO history) does not prove full escape equivalence: it collects visible reaching enemies and tests stun coverage/immune status, not all tracked enemies, camp damage or actual walk endpoints. Do not remove or broaden it in this experiment. Preserve spell target order, strict value ties, Ren retaliation rejection, wake-risk exclusion and unseen-target treatment.

Separately, `retreat_step` has no stay candidate/current-damage floor: it sorts eligible neighbors and eventually falls back to `step_towards`. It can therefore select a neighbor with more immediate exposure than staying. That makes the public289 pattern prospectively plausible but does not identify its historical branch. Do not restore a dropped global escape comparator or rewrite station choice as part of this narrow pre-cast question.

`flee_camps` and `retreat_step` already inspect up to eight neighbors with existing Safety and the home field, but **after** the cast. `retreat_step` uses nonincreasing finite home distance and damage/home/gap ordering; `flee_camps` prices remaining camp exposure. Their work is not already available for free before a spell that consumes movement. An endpoint preview must be factored and reused, not followed by an identical second evaluation. `Pathing::blocked` includes camps, occupancy, pending landings and prior bumps; `try_move` additionally enforces the current guard and can reveal a previously hidden blocker. An open terrain tile alone is insufficient.

## Recommendation: diagnose a dominance case before choosing a gameplay arm

Do not change210, ban nonlethal casts, or add a general fight simulation. Prior experiments constrain the design: ranged carriers holding fire to retain movement lost47.9%; full retreat planning was level but2.5× OOF; strike retreat search reached52.6% at100M yet40.8% at the real budget with+135% OOF. A fresh49-tile search or two-turn enemy-chain redesign would repeat the cost problem.

The smallest useful prospective question is: **does the original retreat-selected exclusive cast buy only damage, while an original retreat-eligible, currently legal neighbor removes a credible threat that staying retains?** Require evidence of actual escape geometry, not a scalar trade between health points and a walk. A particularly clear first case is currently lethal stay versus a verified nonlethal/zero-hit endpoint; do not quietly widen this to every hurt carrier or every positive damage reduction. This criterion may not trigger public291: known turn order may let Prism act before Marcella again, and its corner limits later movement. Failure to trigger there is acceptable.

For one nominated current-source turn, record the original selected `Cast` before `execute`: slot, exclusivity, target, final worth/threshold, free-stun status, native walk/cast availability and fresh self health/shield. Retain already calculated per-target damage and value contributions for that selected target. Separate verified visible kills (including a legal basic follow-up), effective stun of a not-yet-denied activation, interruption of a tribute/kept recall/teleport, and raw nonlethal damage. Unknown-target contributions are not a proof of either a kill or no control; mark ambiguous and exclude them from the first intervention.

Then compare current tile with the original movement branch's eligible neighbors, retaining its constraints and tie order. At most eight neighbors plus current, not a board of future stations. Record native occupancy/visibility, blocked/bumped/guard rejection, finite home distance, current camps and per-enemy `Safety::blow`/`threats_at` contributions. Respect visible cooldowns, already-acted/next-turn timing and latest teleport destination semantics through Safety/Reach; do not derive timing anew from distance or use `avoid_within` alone as a safety certificate. Include stun-only hits and next camp phase, not just numerical damage. No promised allied damage, future heal or body tanking belongs in the safety result.

Instrumentation must observe existing work or use wholly private diagnostic state after preserving the decision inputs; an excluded print block is not permission to warm production Safety/Reach/Pathing caches. Extra SDK work requires the same harness-exclusion/callstream validation as earlier diagnostics. No public-source replay may be relabelled exact-current-source without identity/parity evidence. This note specifies evidence only and does not authorize new tooling or engine work.

## Conditional first child, if the evidence warrants one

Limit to generic `retreat`, no successful earlier self action, native walk available, an original selected **exclusive, nonlanding** cast whose complete known effect is raw nonlethal damage, and a proven retreat-selected escape endpoint. Leave interception, capture/bank ownership, ordinary strike/search, Willow-owned forced escape and all other spell callers unchanged. Exclude any actual kill, legal cast-plus-basic kill, effective control/channel interruption, ambiguous unseen target effect or special retaliatory side effect. Preserve existing offensive decisions where no legal better endpoint is proved.

For the first arm require the narrow stay-lethal / endpoint-no-hit certificate, with actual current health/shield and all credible modeled enemy and camp threats. This deliberately leaves less clear attrition trades unchanged and adds no tuned damage threshold. Query at most the original eight candidates and reuse their descriptor/results in fallback. Do not build another route field or evaluate another camp shortlist. Lazy Reach construction can still be costly; count it in qualification rather than describing nine endpoint checks as a fixed cheap instruction cost.

When admitted, execute the existing selected safe step first. A successful move makes the original exclusive cast illegal, so discard its descriptor and do not attempt it or another successful move. A refused move must not count as escape: refresh newly revealed information and reselect the original cast once before ordinary fallback; never reuse stale target/field references or spin across move/cast retries. The existing spell order resumes on fresh state, without permanently withholding a ready slot. This is a bounded escape-preservation experiment, not a new global action ranking.

## Cases where fighting should remain available

- A lethal hit removes the only pursuer, finishes a carrier, or opens an occupied escape; a cast-plus-basic kill must not be misclassified as chip damage.
- A stun or channel interruption wins a race or denies a real hostile activation. Marcella immunity and already-present stun change this value.
- The apparent exit is blocked, guarded, a camp exposure, a teleport landing or reachable by a hidden tracked enemy; or every legal step merely enters a worse pocket.
- No useful walk exists, native movement is spent, or holding position secures a protected bank/capture. Damage and a recall attempt can then be the best remaining actions.
- A melee attack can accompany movement, or a dash changes position. The proposed narrow exclusive-cast guard must not suppress these independent actions.

Disposition: **diagnosis needed; no gameplay child recommended yet**. The source exposes a plausible missing concrete comparison, but the historical episode does not establish its current frequency, safety improvement or benefit. Keep this separate from the main Willow qualification and the stationary-camp fallback diagnostic.
