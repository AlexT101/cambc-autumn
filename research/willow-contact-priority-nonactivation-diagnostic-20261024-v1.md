# Contact priority: nonactivation and minimum next check

2026-10-24. Source-only response to the exact f7 parent/candidate panel. Candidate `8e535de8da12fde3b5d2c0b03edb275790539b2a867f86cf985ed554ec44c2e7`. No implementation or runtime by this reviewer.

`provenance/willow-contact-priority-f7-20261024-v1/payload-comparison.json` now reports identical extracted events and round states for Elkring B and Pilgrimage A (and the separate no-Willow Gold Rush control). The runtime worker found no living Willow priority13 at round ends. This establishes no observed activation in that sampling; an actor setting13 then dying before round end needs separate exclusion. The raw replay-payload comparison is also separate from equality of extracted JSON. A larger win-rate panel is not the next useful test.

## Can the camp guard overreject?

Yes, structurally. `groups_near(p,map.max_camp_reach)` finds a group when **any member** is within the map-wide maximum range. `contact_camps_clear` then rejects the whole possibly-live group when it has any positive Strength. Thus it rejects both a range3 striker at distance4 on a map with maximum5, and a group whose nearby harmless cluster is far from its only damaging member. Neither geometry can transfer that group's camp attack onto Willow just by raising priority. This is a known conservative approximation, not evidence that the panel reached this gate.

Do not replace it with cached `camp_damage == 0`: that quantity already incorporates old-order tie winners. A sound geometric refinement would preserve the known-empty exemptions and reject only if some static member has positive Strength and `Chebyshev(endpoint,member.position) <= member.reach`. Use actual member ranges, not just the group's largest range around every member. No visibility/death assumption is needed to exclude a physically out-of-range member. Do not implement this refinement until a trace identifies meaningful camp-gate rejection; account for large-group scan cost if it becomes necessary. A static-only range veto would still reject public Elkring9,25 because Elk13 is only distance2 away; its known-clear/respawn exemption, not range tightening, decides admission there.

## First: one compiled positive state fixture

The existing Python `projected_order_fixture.py` demonstrates an independently sorted alternating schedule, but its central assertion compares equivalent expressions and it never invokes the production admission helper. It does not demonstrate candidate activation.

The minimum low-cost replacement is a C++ state fixture compiling the **unchanged production bodies** of `contact_camps_clear` and `recall_contact_priority`, automatically extracted and bound to the candidate source/file/function hashes. Thin mock World/Enemy/map/Strike interfaces are acceptable. Do not manually transcribe the branch predicates into a second implementation. The scope is production admission control flow, not SDK integration, native visibility acquisition or action execution. Record mocked dependencies explicitly; the range/readiness semantics remain separately verified against source.

Positive fixture inputs:

- Round101, own sideB, so B starts round102. Own three bodies ids3/4/5, Willow id5 with unchanged fallback7, allies at priorities8 and9. Enemy three bodies ids0/1/2, Ryth0 priority10, others0/−1. Include all roster bodies in ordering.
- Willow endpoint15,15; Ryth15,12, alive/currently visible/already acted, position/stats/priority rounds101, channel none. Matching start snapshot exists and is not stunned.
- Existing Strike dependency returns legal reach2 at102 and103: immediate distance3 misses, the one-approach term at distance2 hits. No nearby damaging group.
- An independent sorted-roster/alternating-turn oracle gives old Willow slot4, enemy slot1, new Willow slot0. The **actual candidate helper must return true**. A separate outer dispatch assertion should check that true applies13 only to the qualifying live/off-spawn/recalling/no-Wish/fallback<13 path; this can be a source-bound seam test rather than a synthetic copy of the condition.

Mutations should cover: known-live in-range camp rejection; a recent known-clear or future-respawn exemption returning true; respawn exactly next phase rejection; stale position/stats/priority, unacted enemy, channel, missing start snapshot and known stun rejection; opposite parity with enemy first rejection; unchanged-rank rejection; existing engaged/protect priorities unchanged. Add unequal-team/dead/tie cases to the independent scheduling oracle and call the production helper. A harmless-near/damaging-far group is a useful **expected current rejection** documenting the conservative camp approximation, not a request to silently change its expected policy.

A later short native probe can script Willow and Ryth into the same open geometry, call real `set_turn_order`, and verify13 plus next-round order. That is ideal for integration, but unnecessary to obtain the first source-bound positive control. No full-strength match or private public-game memory is required.

## Then: one bounded rejection trace on an existing source-known game

Use Elkring B candidate versus the same frozen v33 setup. Add debug-only counters/reasons at already-evaluated branches; do not query new state or calculate another safety model. The funnel is: live Willow → no-Wish/off-spawn/recalling context → fallback<13 → allied rank changes → fresh acted non-channel enemy → enemy-slot crossing → immediate/approach contact → matching unstunned snapshot → camp clearance → priority13.

Print the first small bounded set of helper nominations/rejections and one aggregate funnel summary, rather than a roster dump. A camp rejection row needs endpoint, first blocking group, group state/state_round/respawn_round, maximum query radius and whether the rejection follows live/unknown versus expired empty-state evidence. If already recorded contact/rank predicates never reach camp evaluation, do not add a geometry scan merely for logging. Only a second targeted inspection, if camp rejection dominates, needs static member coordinates/ranges for that one group. A context row may distinguish opportunistic recall being absent from fallback already being engaged; ordinary support-owned turns often do not start the tail recall.

Tracing can change fuel-dependent decisions, so validate accepted actions/status through the inspected prefix against the release candidate before assigning its rejection reason to that original prefix. This is a diagnostic run, not an improvement result. Gate counts and the compiled positive control should decide whether to adjust a specific admission restriction or shelve the arm; zero activation is not a reason to make multiple predicates permissive.
