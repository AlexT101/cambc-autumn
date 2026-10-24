# Isolated controls: first-fork review

2026-10-24. Read-only review of existing source, comparison receipts and accepted-input summaries. No replay decoding, builds, games, scripts or source changes. Willow-first ladder-manipulation batches remain excluded.

## Eight A: no adverse recall-only effect

`provenance/khaos-v34-ladder-intake-20261024-v1/comparison-eight-selfplay-vs-v47-recall.json` (SHA256 `13bc7fb9ca10b410c44fe07086be0d00ab7a5b7fd4d2948b665bfd08e5ace40f`) compares f475 A/f475 B with recall-only47 A/f475 B. All59,450 accepted inputs,2,001 round-start states and result A263/B993 at2000 agree. Raw replay identity is not claimed. The A-side loss already occurs in the unchanged baseline; it cannot be counted as a demonstrated harmful recall branch. The completed opposite-side game is a separate comparison, pending its requested comparator report.

Control source64d9c8fd is f475 plus the finishing-recall patch. Its intended semantic change requires ongoing recall, held capture, pack suppression by near payout, landing before payout, nonwinning top-up and the existing safe-exit predicates. Equality does not prove the guard was never evaluated, only that it produced no differing accepted behavior or state in this complete game.

## Starvation A: immediate route/cost fork

`comparison-starvation-v48-vs-walk-altar.json` (SHA256 `a532eb8a73c71218d21ca3e61258eef93e2eee7faaabb6c80930d9506c2bc7e5`) compares v48 A/f475 B with the isolated walk-altar-control A/f475 B. At input29, native step89, r1, Vesper1 at(2,48) moves to(3,47) under v48 versus(3,49) under the control. The first round-state mismatch is r2. Native results are A252/B1000 at1625 versus A1124/B304 at1893. Statistics round-count labels elsewhere are not substituted for these native result rounds.

The control c156da50 changes only `Pathing::centre_to_altar` relative to v48: it always attempts the draft walking-graph estimate; v48 skips that estimate for a dasher when crossable terrain exists. Compare `bots/Khaos_v34/src/pathing.cpp:90–95` with `bots/variants/willow-v48-walk-altar-control-work/src/pathing.cpp:90–94`. No new recall behavior differs between these two variants. The move is an observable fork, not yet proof which private branch caused it or why the later game diverged so much.

There are two distinct source effects:

- **Distance result:** the dasher's own field can produce a different camp-to-altar distance from the drafted walking graph.
- **Computation/cache state:** the first such query can build `to_any_altar` through `pathing.cpp:69–73,53–59`, including the goals board, field allocation and `FuelMeter`. The control may return a stored draft scalar instead. Existing fuel-dependent evaluation and route fallbacks can therefore differ even without a native fuel rollover.

A useful stronger restriction follows from first-turn economics. `farm` reads `bag` and `banks_bag` at `bot.cpp:1747–1748`; zero carried gems imply `banks_bag=false`, while `bag_rounds_left:683–684` returns the full remaining game horizon. `to_altar` is then null at1943. For a group that cannot win from its own payout (`wins=false`), the lookup at2193 is skipped and the ordinary trip/rate price does not use altar distance. The remaining lookup is the `too_late` deadline check at2274–2279. **If the examined groups have wins=false and both distances leave that check false, a changed numeric altar estimate cannot directly reorder their ordinary-farm values.** Cold cost, a resulting partial scan/route fallback, or another code-generation cost effect becomes the stronger explanation. Those conditions must be observed; do not assume every group is reachable or every deadline identical.

## Minimum diagnostic, not an authorized run

Limit any subsequent trusted trace to Vesper1 r1 in these two exact builds. Reproduce each native branch before interpreting instrumentation. Preserve actual call order and use existing values only:

1. At `centre_to_altar`: queried group; optional cache present on entry; whether the normal code selected draft lookup or own field; whether `any_altar_` was already present; returned steps. Do not query the alternate distance for logging.
2. At the calling farm branch: `bag,banks_bag,wins,left`, `steps,wait,clear_rounds`, the existing `too_late` result, and the current best group/value. This tests the numeric-deadline explanation.
3. At scan completion: `first,k,evaluated`, final best/shared/help target and existing shortcut label. At the first movement call: actual target and selected route/search/fallback site. This separates different target selection from different movement toward the same target.

Record any already-read fuel/gate result at the actual cutoff; do not add a new fuel query or recompute a short-circuited test. A native end-turn instead of rollover is insufficient to rule out the existing `fuel_ok` cutoffs (farm loop2176, field2249, route2405 onward). The precise first differing scalar or branch is needed before proposing an optimization or reverting a correct distance graph.

## Eight B: a movement fork, not yet a recall-policy witness

The subsequently completed `comparison-eight-selfplay-vs-v47-recall-B.json` finds the first difference at input10,371, r269, step42,785: Willow8 moves from(26,8) to(25,8) under f475 versus(25,9) under recall-only47. The first round-state difference is270. Native result changes from baseline A263/B993 at2000 to A1023/B338 at992; the statistics file labels991 completed rounds. This is a real B-side source effect, separate from the exact A-side control.

A successful new recall keep would normally be visible immediately as cancelled recall versus kept recall. Its new condition `round+channel<payout` makes the parent's `capture_recall` returnfalse before that helper's later `memory.banking=true` assignment (recall-control `bot.cpp:3346–3387`); parent then cancels. Thus the movement fork does not itself demonstrate the new keep action. It is consistent with additional computation or code generation changing an existing cutoff.

There is one important limit: exact game actions/round hashes do not establish equal private memory, shared posts or warm caches. A failed new guard may perform additional safety/tribute/reach work before falling through to the same cancel, and a cost-sensitive path could choose different private intent while emitting the same accepted actions. The false-guard plumbing does not directly write policy memory (`can_tribute_safely` takes const Memory), but its downstream costs and caches are not proved inert by this comparator.

After the higher-priority Starvation diagnosis, the smallest Eight diagnostic is Willow8 r269 in both exact builds: entry `memory.farm_group/claim/crew/banking`; channel and cached-home result; new pack-relaxation/rejection flags if executed; actual first-move callsite and goal; and that site's existing search/gate/fallback result. Include formation/support state only if the identified movement caller uses it. If entry private state already differs, locate its preceding update next; do not jump from a move difference to either a harmful recall policy or a generic compiler explanation. No whole-game trace or new gameplay experiment is requested here.

## Scope of current conclusions

The common-v33 cells are nontransitive: f4754/9 and v48 6/9, with StarvationA reversing against v33. The broader direct comparison is44/80 for v48. These results neither establish a broad release collapse nor settle matchup-specific regression. The Eight A comparison removes one apparent adverse recall witness; Starvation isolates a first-turn difference to the altar-lookup control but does not yet separate its numerical and fuel effects.

Gem Fields now has exact behavioral reproduction using local v48 A plus recorded opponent B:15,202 accepted inputs,544 round hashes and A429/B1077 at543 match. Official server source/version identity remains unverified. Its separately specified Prism crew-quote trace is now technically grounded in a reproducing artifact, but remains distinct from the Starvation first-turn diagnostic.

The subsequent **f475 A versus the same recorded B puppet also matches the downloaded Gem Fields game completely**:15,202 accepted inputs,544 round hashes and A429/B1077 at543, with no input/state fork. Receipt `comparison-gem-fields-f475-puppet-vs-original.json`, SHA256 `2f99fc65d61dd27149eba9098e1f9a33b37fb4bfea9294f9f3d7f01ec2442a01`; the direct v48/f475 puppet comparison is also retained. Thus this exact loss and its observed macro decisions are reproduced by both own archived releases; it is not an observed v48-specific behavior regression. No further artifact-identity work is needed for that conclusion, and no claim about official server binary identity follows.

## Conditional Starvation optimization: one-sided deadline proof

This is source verification of a proposed shape only; wait for the actual first-turn trace before selecting or implementing it. If the fork proves cold altar-field work causes an old fuel cutoff, `too_late` can potentially prove false using a finite drafted walking distance before materializing the exact dasher field.

The subset proof is concrete in v48 source. `draft.cpp:114–117` builds the altar field on `blocked_for_us` using every altar's `tribute_tiles`; `pathing.cpp:69–73` uses the same goals. `world.cpp:833–834` makes `dash_walls = blocked_for_us minus crossable`. At841–842, `landing_dash_walls` adds back only `crossable intersect harmful-camp neighbourhood`. Consequently both dash graphs retain every walking edge and goal; their shortest finite distance from the identical group centre cannot exceed a finite walking distance. Draft distances are stored as uint16 (`draft.cpp:83–88,130–132`), matching the uint16 unreachable sentinel (`util.h:399`); a missing draft plan yields nullopt (`world.cpp:671–674`).

Required semantics for the conditional shortcut:

- If `known.to_altar` is already populated, retain the current exact-cache path; no extra draft read is needed.
- Otherwise, only a present, finite drafted walking distance that makes the **same full deadline expression** fit (`<=left`) may returnfalse. Keep the existing expression's arithmetic/order and all other terms; no new threshold or fuel gate.
- Missing draft data, unreachable walking distance, or a bound that does not fit must use the unchanged exact `centre_to_altar` path. In particular, unreachable walking does not imply unreachable dash, and the current predicate deliberately treats exact unreachable as no deadline.
- **Never store this walking upper bound in `known.to_altar` or Pathing's centre-distance cache.** Those values later drive bag/chained-cycle prices at2192–2202 and must remain the corrected exact graph distances. Leave the cache unset on an early false proof. Do not mutate group context to pretend the exact field has been obtained.
- Keep this confined to the deadline test; retain current dash distance in actual bag/cycle pricing. No Safety/native query or dynamic occupancy assumption is introduced.

This preserves the numerical deadline decision under the current static-distance model while intentionally changing when expensive field work occurs. It does not certify real future travel, camp occupancy, dash cooldowns or altar availability—the original estimate abstracts those too—and it need not preserve fuel-sensitive gameplay byte-for-byte. The trace must first show that this cost path is the cause worth addressing.

Evidence index and build/source/replay pins: `provenance/khaos-v34-ladder-intake-20261024-v1/{CONTROL-RESULTS.md,IDENTITY-DIAGNOSTICS.md,IDENTITY-DIAGNOSTICS.json,isolated-control-build-result.json}`.

## Trusted Starvation r1 trace: opening mechanism identified

The subsequent recorder/tracer validation passes for both exact builds. Under `starvation-r1-trace-prep/`, v48 trace matches42/42 accepted inputs through r1 and all three round-start hashes0/1/2; walking control matches39/39 and those same boundary rounds. Each trace's host validation reports15/15 matching recorder segments, zero mismatches and zero rollover points. These are bounded-prefix validations, not claims about untraced later decisions. Read the parsed `traceFields.line` entries in the host JSON: raw `strings` can split a framed line, including the walking-control scan record.

| Observed r1 Vesper value | Full v48 | Walking-altar control |
|---|---:|---:|
| First checked altar distance, g13 | cold own field40 | draft scalar73 |
| g13 full deadline / remaining | 134 /1999, false | 167 /1999, false |
| Scan seed; total intended candidates | 12;14 | 12;14 |
| Completed loop iterations `k` | 2 | 5 |
| Final selected group; value | g13;0.085121 | g0;0.222850 |
| Selected approach steps | 83 | 49 |
| Selected centre | (63,41) | (35,75) |
| Final route search enabled | yes | yes |

Both have bag0, banks0 and short1000; neither uses a shared/help override. The control additionally evaluates g0/g1/g2 with deadline130/136/259, all below1999. Its risky g2 value0.359210 does not override affordable g0. Full v48 never produces those later completed quotes before ending its scan. With `k<evaluated`, this is the existing partial-evaluation path, not completion of all candidates. The records do not identify whether the terminal cutoff was the loop condition or the internal field-reserve break, nor record an exact fuel delta; do not invent either. `k=2` also need not mean no instruction of candidate3 ran.

This resolves the opening question: the corrected dash altar lookup caused cold field work during a deadline check whose answer was false in both builds, and farm evaluation stopped earlier with a substantially lower-valued incumbent. Vesper then routes normally toward a different chosen group, explaining the first accepted move difference. It is not a numeric deadline preference for g13 and not a same-target routing fallback. The paired source change plus validated branch evidence identifies this computation/coverage mechanism; it does not quantify field cost separately from code-generation overhead, nor prove that one opening move alone caused the entire match loss.

The already-reviewed isolated bound46c5b558 directly addresses the observed unnecessary work: drafted73 already proves g13 deadline167<=1999, permitting false without exact field construction while leaving corrected dash-based pricing intact. Its native result and warm-cost tradeoff remain separate tests. No additional trace is requested by this review.

Validation file pins at review time:

- `v48-trace-host-validation.json`: `5e03687f73419ec92666048726bb62be6f90aea0c0dd6df7b747bb6b3e3e25d3`.
- `walk-control-trace-host-validation.json`: `ac557831a1bda1c815cd7c4274a00735077462b83f66a7e9a590e36bdf53470a`.
- `v48-trace-prefix-validation.json`: `0e82c9cef300b322231943fe8934a7a9c9fc9aa40cc89425dcd25f75d392f981`.
- `walk-control-trace-prefix-validation.json`: `4275d49a3a3bc1422674b6dd3bc52974583bc0a3d8d8a23e847505f22d0f53e1`.
