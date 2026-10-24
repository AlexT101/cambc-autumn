# Equal-ray escape refinement after the execution-only panel

2026-10-24. Source-only design and existing matched-result analysis. No implementation, build, game, new extraction or upstream inspection. Source invariant justifies an isolated experiment; no claim this omission caused any particular loss.

## The matched comparison limits the next change

Read latest `research/EXPERIMENTS.md` and source-reviewed execution control, then joined exact map/physical-side rows against v33 from:

- `provenance/khaos-v34-ladder-intake-20261024-v1/f475-v33-complete-output-v1/RESULT.json`:45/80, A22/B23;260 candidate play rollovers.
- `connected-escape-160-output-v1/RESULT.json` beneath the same intake: full escape37/80, A16/B21;289 rollovers.
- `connected-escape-execution-release-v1/RESULT.json`: execution-only38/80, A14/B24;265 rollovers. All native bot errors zero.

Execution-only gains9 baseline losses and loses16 baseline wins. Relative to full escape, it recovers6 wins (Collision B, Contest B, Lanes B, Big World B, Corridors B, Starfish A) and loses5 (Road of Riches B, Split A, Boss Battle B, Corridors A, Yellow Brick Road A). Thirteen baseline wins remain lost in both escape arms, including Elk Arena A. Restoring admission therefore does not recover the common-opponent result; it also changes cost/cache prewarming, so the comparison is not a pure admission-policy experiment.

The exact Elk trace already showed both original/full sources at r10 HoR4 HP790/camp-DPS60 choose leave=false and ordinary strike planning. Their first divergence is a rollover/action boundary, not a changed camp-admission result. The later loss cannot simply be assigned to admission. The Boss Battle allied-arrival hypothesis remains separate: its recorder now reproduces the original behavior, but private515–516 trace validation is still pending. Do not combine a fight-forecast change with this refinement.

## Concrete omission: one ray hides equivalent legal alternatives

Use parent **execution-only `fcdf6007cebc9c248f8866142b39be614d38c4e273c983083cdfc722eba500d1`**, tree `bots/variants/willow-v47-connected-escape-execution-work`. Keep original f475 admission and all current connected execution unchanged except the representation of equal straight witnesses.

`pathing.cpp:393–445 Pathing::camp_escape` scans eight straight rays. It replaces `out.ray` only for `k < out.steps`; equally short later witnesses are discarded. If no goal is geometrically nearer, that one ray is exact and no native field is built. `CampEscape::at` (roughly380–391) then labels only its points. `bot.cpp:303–325 camp_escape_step` intends to compare descending endpoints by exposure/camp cost/home distance, but can see only the cached ray's first step. Likewise `connected_camp_dash` (393–460) can compare only endpoints that happen to be on that ray. This is a real coverage restriction independent of any match explanation.

## Minimal implementation contract

1. Replace the single-ray witness with a compact eight-direction mask (or equivalently bounded fixed representation), retaining **all equally shortest** completely traversed rays. A new strictly shorter witness clears the old mask; an equal witness adds its direction. Do not retain a longer ray as though its length were the shortest distance.
2. Preserve the exactness proof: a free ray of lengthR reaches a goal, and the existing check finds no goal within Chebyshev R−1 of origin. Every point k steps along any retained ray has exact remaining distance R−k: a nearer goal from that point would imply a goal within R−1 of origin. No new search, threat query, field build or full-map scan is needed.
3. `at(p)` keeps the current invalid/exact/bounds/walls checks. For a ray-backed result, label a point only if delta from origin is precisely one retained king direction times integer k with0≤k≤R; return R−k. Preserve origin, goal/steps==0 and unreachable/exhausted semantics. All off-ray points—including other apparently useful goals—remain unknown. A small direction/distance check may replace the old length loop, but must reproduce every old single-ray label exactly. Do not derive distance from a nearby ray or connect two rays through an unchecked chord.
4. Preserve native-field mode distinctly (mask==0). A field fallback clears the mask and uses the existing label lookup; no approximate ray label may leak into it. Origin, complete current walls (including occupied tiles and guard) or goals changing invalidates the witness and clears/rebuilds the mask exactly as today. Moving origin requires fresh ray discovery; do not translate old rays to the new origin. Warm keys reuse only the same certified boards/origin.
5. Walk execution continues to use the existing damage/credible-enemy constraints and home tie-break. This exposes more equally short options to that ranking; it adds no no-enemy restriction, forced retreat, new veto or new fuel gate.
6. Dash scanning continues to use legal native landings and the existing bounded endpoint evaluation. A landing/followup receives a label only when genuinely on a retained ray or covered by the existing field. After an actual dash, `see_again`, fresh hazard/occupancy/guard/origin and existing followup revalidation remain mandatory. An old endpoint cannot authorize a new off-ray walk. Enemy appearance still uses the existing enemy-retreat handling. No new dash direction or damage formula is introduced.

The only new state is bounded direction membership; avoid heap allocation or a general route planner. Existing checked ray work is reused. More valid endpoints can naturally cause more already-existing Safety evaluations; measure that cost rather than claiming exact fuel equivalence. An optimization of `at` must preserve old labels before adding the newly justified ones.

## Small checks and practical comparison

Useful controlled geometry cases: one ray reproduces old labels; two equal free rays both descend; a third longer ray stays unknown; a blocked intermediate tile prevents inclusion; changing occupancy/guard/goals/origin invalidates the old mask; a geometrically nearer goal forces the existing field path; all-field and unreachable cases retain their old behavior; a dash endpoint off every retained ray stays unknown, and a post-dash topology change cannot reuse its old continuation. In a two-ray case, independently arrange the existing ranking to prefer the formerly discarded ray (lower exposure, or equal exposure nearer home). This is a meaningful positive coverage check without private public-replay state.

First stress comparisons can use Elk Arena A, Fracture A and Reverse Spiral A (known adverse source cells) plus Hooks A (an escape gain worth retaining), each against the same frozen v33 and parent execution-only, with exact parent rows reused. These map names are diagnostic selections, never gameplay conditions. Then the already-established40-map/both-side common-v33 frame gives the matched result; no individual stress loss should automatically block testing the combination or broader panel. Read first accepted divergence/actual escape activation before attributing wins or losses. A source-known positive equal-ray fixture demonstrates the intended mechanism even if a chosen game never invokes it.

No admission overhaul, ally-support forecast modification, speculative full path solver or blanket abandoning of productive routing is proposed. This narrow representation improvement can be tested while the separate Boss Battle trace resolves whether nearby allies are actually credited too early.
