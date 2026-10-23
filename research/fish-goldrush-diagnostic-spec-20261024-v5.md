# Fish Gold Rush: conditional two-turn diagnostic specification

2026-10-24 UTC. **Specification only; do not add instrumentation yet.** First review the seven forthcoming source-known Gold Rush mechanism-game outputs for replication. The source-unknown Fish public replay nominates a mechanism; it is not an execution fixture for substituting our current binary. Preserve v3/v4 reports and all existing evidence.

Read the Cambridge Battlecode rules and `tools/replay/harness/README.md`. Canonical `bots/astraeus/src/bot.cpp` SHA `3bef17ba3c88fe30d147fd9d2ce99881a05515f2940e6f4b251d4b9b3d8803d5`, `params.h` SHA `cae05ef905e7564822190fac5563833c81cce906ec46e03e4c5687427bb7475e`, `pathing.cpp` SHA `a3dd7e76421c88df98af01df330f6338a5d7b3003b2344d8c411b14842f77191`, `safety.cpp` SHA `07f6c2ca8e2f165fcb5e02c0998f818fc4a3ebb2ad33180f7fbda43d3df9c123`, `world.h` SHA `ab008858a8e274f0de115bae6ff9496f1d0b1c0249b37e83f41596586ba37ce8`. References below are those exact files under `bots/astraeus/src/`; the baseline aggregate remains `369742e3f54259c675c0d4b508a02c0c4517eef6e1cb3ef6f42fa776194180ea`. Re-anchor after any source change rather than trusting stale line numbers.

## Gate: use existing seven outputs first

For each game, retain its actual source aggregate, binary hash, build mode, physical side, both ordered drafts, replay/map/engine hashes and extractor receipt. Confirm the actor from its roster: do not assume actor1 on B. Distinguish canonical controls from candidate variants. Review only available extracted own-view/action outputs; do not start another run or decode to populate this table.

Classify an occurrence as an **observed reversal** when the same actor walks `p→q` and next own turn `q→p` with no intervening successful productive action by that actor. Keep its HP/bag, camp state, visible enemies and ally locations at both anchors. A second repetition strengthens the observation, but is not needed to nominate one diagnostic. Record real local round numbers: public22→23 is an example, not a gate requiring the same timing/coordinates. If the available export omits attempted actions or camp freshness, record that limitation rather than asserting no useful attempt occurred.

If none of the seven exhibits the pattern, report **no replication in these seven** and stop this diagnostic. That neither disproves the public observation nor authorizes instrumentation of all seven. If there is a source-known reversal, select one canonical occurrence and two consecutive own turns. Prefer a case with stable enemy positions/readiness, zero bag and the five-tile ally cutoff. A variant-only occurrence remains variant-specific. Ask the coordinator to assign any later implementation/execution to Luna under the single-worker rule; this document makes no such assignment.

## Tier 1: identify the branch before diagnosing a route

All records carry game/run identity, source hash, actor handle/type/team, round/turn, per-turn event ordinal, and occurrence id. Use a fixed two-turn selector in a diagnostic copy, never canonical gameplay. Keep a record of the turn-start native position and `world.me().pos`; a mismatch matters because pack formation uses the latter. Tag state/observation revision so pre-cancel, post-cancel and post-reveal records cannot be accidentally joined.

| Hook | Exact location | Required values already computed on the real path |
|---|---|---|
| Home decision | `bot.cpp:2849–2868`, `want_home` | Called-from context; current position, HP/maxHP; result plus one terminal reason: `on_spawn`, `low`, `outmatched`, `camp_trapped`, `willow_threat`, `no_seen_nonlethal`, or `stand`. Preserve ordered short-circuit evaluation at2855. For a reached stand branch, capture `lethal`, `pursued`, `linked`, `t.lost`, `t.self_falls`, requested approach horizon and result. Unreached tests are `not_evaluated`, not false. |
| Pack veto | `bot.cpp:2820`, `outmatched`; `2735–2749`, `in_pack_zone` | Query position; near/recent early-out; returned membership; first containing box index; whether `paying_soon` was actually evaluated and its result. This distinguishes “inside a box but allowed imminent payout” from true `outmatched`. |
| Recall choice | `bot.cpp:4151–4176`, `continue_recall` | Cached `home` result, initial channel timer, evaluated `threatened` / safe-tribute / `recall_outruns` results, keep/cancel outcome and exception/failure. Record which short-circuit operand stopped4152 and4166. Do not call every predicate merely to fill a row. |
| Dispatch | `bot.cpp:4895`, `4907–4910`, `4925–4927`, `4984–4989` | `home` reused versus recomputed; `mend`, `leave`, `support_retreat`; actual caller path `leave→retreat`, `support→retreat`, or `ordinary→farm`. Snapshot `memory.farm_group`, `claim`, `crew`, `banking`, `siege` at entry. Final decision character alone is insufficient. |
| Farm admission | `bot.cpp:1901–1906` | Holding-capture early return; evaluated bag-at-stake; whether zone was requested and pointer is non-null. Distinguish `bag_zero_not_requested` from `requested_no_boxes`. Capture previous farm group at1910 and selected group at2398; if a fallback is used, tag its actual branch. |
| Actual movement | `bot.cpp:4201–4236` retreat; farm1914–1928 and2416–2459; `pathing.cpp:526–541` | Caller/provenance tag, from/to, pathing stage, guard rejection versus native move success versus native hidden-blocker false versus caught native error. Include move attempt ordinal. A successful edge is not evidence that no earlier hidden-blocker attempt happened. |

The decisive Tier1 signature is `farm, bag_zero_not_requested, p→q` followed by `want_home.reason=outmatched, leave→retreat, q→p`. It establishes the branch mismatch in that source-known occurrence. It does not prove that excluding q improves play, that the retreat is wrong, or that the public submission used the same source.

## Tier 1 pack explanation: anchor, own ground and counted strength

Capture the actual pack build at `bot.cpp:2630–2637` and2641–2705, not a second diagnostic call that rebuilds it. Include `pz.frozen`, `pz.round`, whether built/reused, build anchor, frozen HP/maxHP/bag, query position, radius7, ally radius5, `hurt`, chosen ratio, our summed HP/output, threshold and box count. If `forget_pack_zone` causes a rebuild, give it a new build ordinal. A reused build must reference its original anchor/rows.

At `own_ground`2601–2604, capture the already-read ally/enemy spawn-field distances, their unreachable flags and returned boolean. Associate each call with its context (`pack`, `want_home pursuit`, other). This is a path-distance classification; “looks like our half” is not acceptable. Either field unreachable also returns true. No extra spawn-field construction solely for logging.

For each roster member, at most8 per side, retain handle/index, visible/alive, position, `pos_round`, `pos_source`, `stats_round`, health/maxHP, Strength/Focus, scale, and counted/excluded reason. Enemy exclusion reasons distinguish dead, age>1, near-enemy-spawn, or capacity. Ally membership distinguishes self, visible within5, outside5, or invisible/dead. For counted members capture the actual `output()` value; calculate any excluded-member hypothetical output offline instead of adding runtime work.

Retain the mapping from each compact subset bit to enemy handle. Record only accepted minimal outmatching subsets that actually produced boxes, with subset mask, health/output sums, product, box bounds, and the first box used by `in_pack_zone`. Preserve insertion order. No log of all255 rejected subsets is needed. In the three-enemy replication this is tiny; use a fixed hard storage bound compatible with the existing255-box bound and explicitly mark overflow/incomplete rather than silently truncating a needed proof. It is enough to retain the matched box plus its producing subset and the total count if the implementation cannot cheaply expose all boxes.

The public geometry predicts pair distances6/7 at `(13,11)` versus7/8 at `(12,10)`, and our HoR distance6 versus5. Under current own-ground ratio2, solo Vesper threshold123750 is below Fish Vesper/Vendetta281250; with HoR the threshold442500 exceeds all enemy pairs. These are **expected arithmetic checks**, not constants to instrument or a required exact result in a different source-known game. Record actual stats, field classification and membership so a mismatch falsifies the numeric prediction.

## Support availability is separate from pack credit

`pack_boxes` credits a nearby ally's amortized output; its membership check does not require that ally to be unstunned, free of a channel, ready to cast, in attack range of the relevant enemy, or pursuing the same goal. Do not present `counted=true` as support actually available.

From the already-observed `ChampionBelief` rows (`world.h:260–294`), retain `acted`, priority/rank/current-next metadata, `ready_round[2]`, `stun_pending`, channel/seen_channel/end-round, shield/turns and visible position. Include source age for every value. For our self, retain native post-cancel action state only where it is naturally read by the real decision; otherwise leave it unavailable until an existing state recorder supplies it. Ally claim/support intent can be retained only from reads already made on the path, with read round and source; missing is not unclaimed.

Offline, report separately: pack-counted strength; geometric attack/spell distance; known ability readiness; channel/stun/timing restrictions; and whether a legal safe approach is actually established. HoR shield is self-only, its landing stun requires a legal dash, and Prism's ready spell does not cover a distant Vesper. Do not create a synthetic universal “ally available” boolean or change pack membership in this diagnostic. Enemy `turns_before_ours`/reach are captured only if Tier2 is needed and those functions execute normally; do not force fight evaluation after an early pack return.

## Tier 2 only if Tier 1 rejects the pack explanation

If `want_home` reaches `stand`, capture its existing parameters/result and natural `Safety::approach` / `threat_strike` calculations (`safety.cpp:1951`,805–865,2294 onward): enemy handle, observed acted/next slot, next ready round, one/two opportunities, strike reach, approach delay, included fight masks and lost/self-falls. Preserve `not_evaluated` when pack returned first. This distinguishes a temporal threat from a geometric pack veto; no new fight simulations are required just to populate fields.

If `leave=false` and farm itself chooses both directions, retain existing selected group/claim transitions, selected camp belief state and member health observation rounds, attack-in-range acceptance/refusal, and route stage. Narrow pathing checks to the two endpoints and selected goal: actual field/cache identity, already-read here/next distances, guard/avoid exclusion, live occupancy and remembered-camp membership when naturally queried, native attempt outcomes and state invalidations. Hook `try_move`526–541, `step_towards`544 onward and636–649, and `descend`652–656 only for the selected two turns. A false native move means a revealed hidden blocker; a guard rejection never calls the engine. Do not conflate the two or dump whole boards. If those bits were not read, mark unknown or derive later from the saved source-known snapshot under a separate worker grant.

Only this second outcome motivates comparing the Band route overlay. A confirmed `leave→retreat` before ordinary farm falsifies camp routing as the direct source of that reverse move, although routing may still affect the previous approach.

## Boundedness, fidelity and falsification

One selected game, one actor, two own turns. Default Tier1 only; at most16 roster rows per turn, one row per actual relevant predicate/build/branch, and a fixed cap of64 move-attempt records per turn. Cap exhaustion marks the occurrence incomplete and stops detailed recording, not gameplay. No full-match boards, full subset enumeration logs, additional decision queries or general-purpose tracing system. If implementation is later needed, Luna owns it in an isolated diagnostic copy/provenance directory.

Preserve call order, short-circuit behavior, caches, allocation behavior and fuel-dependent choices. Logging existing values can still change code generation/fuel. Prefer the established exact recorder/tracer approach only if compatible with this source/build; the repository's v38 harness is not automatically compatible with cb61. A debug run is diagnostic, not fuel-exact evidence. Require native accepted actions/states through the two decision turns to match the selected source-known original; record first divergence and stop causal attribution beyond it. Do not launch deterministic reruns for statistical confidence.

| Result | Consequence |
|---|---|
| No matching reversal in seven outputs | No replication here; do not instrument or claim hypothesis disproved globally. |
| Farm admitted q without zone; next turn pack predicate causes retreat | Supports pack/farm policy mismatch for this source-known occurrence. |
| Own-ground=false, ratio100, or actual threshold/subset does not outmatch | Falsifies v4's specific own-ground arithmetic explanation; inspect the actual reason. |
| HoR stays counted both turns, or another ally replaces it | Falsifies the five-tile support-cutoff component; pack reentry may still hold independently. |
| Return reason is stand/camp damage/low HP rather than outmatched | Reject pack as direct cause; use the reached predicate's recorded inputs. |
| Home=false and both moves are farm, or target/claim changes | Route/objective/coordination seam takes priority; do not tune retreat. |
| An intervening reveal, blocked move, new enemy cast/position, or state divergence changes the decision | The simple stable-state loop is incomplete; include that concrete change before proposing a fix. |
| Candidate merely stands idle rather than reversing | Not a demonstrated gain: require productive progress or justified staging without worse survival/production. |

The smallest useful next decision is whether the seven existing outputs contain a source-known instance. No instrumentation, new export, match, build or gameplay patch has been performed or authorized by this specification.
