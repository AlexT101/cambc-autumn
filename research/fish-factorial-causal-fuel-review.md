# Fish factorial: causal interpretation and next optimization

2026-10-23. Source/evidence review only; no gameplay edit, tooling, build or runtime. The opponent is the frozen roster emulator, not Fish's actual policy.

The authorized same-handler high-fuel comparison is `03-upstream-optional97-highfuel` (37c3) versus `05-current-teacher-optional97-highfuel` (b810), under `replays/fish-optional97-factorial-vs-emulator`. Luna verified identical full replay payloads per physical side: A `42a67d051e09c1efddcc1104f777ce9a94cea76aeccdda2722d8dd9d0f4c652f`; B `f28f664e1f60a0315fb7043436f2f7e71b26a7dee123f449d998f63280f9796e`. Candidate bot0 wins **both**, in893/1759 rounds. Runner `winner` is a bot index; physical order changes with `order`. The earlier B-loss description was wrong. The accidental folder04 throw-handler comparison remains an explicitly unplanned diagnostic, not a replacement for05.

Together with default-budget divergence, exact high-fuel convergence supports a budget-mediated integration effect in these two cells. It does not identify a helper, distinguish rollover from existing fuel-sensitive planning, or establish a general release gain. Increasing fuel also changes the emulator's operating condition. Keep the safe optional97 behavior.

The final reconciliation is `replays/fish-optional97-factorial-vs-emulator/winner-fuel-reconciliation.json`, SHA `fb564d02c0b8dfda8c3c7a404297c493f177f45a7e6bd5477f71185ccc9869ee` (human-readable companion `.md`). Summing its five candidate champion profiles on identical gameplay:

| Physical side | 37c3 recorded fuel | b810 recorded fuel | b810 extra | Extra / b810 | Extra / 37c3 |
|---|---:|---:|---:|---:|---:|
| A | 186,693,253 | 189,520,692 | 2,827,439 | 1.492% | 1.514% |
| B | 307,336,356 | 312,787,256 | 5,450,900 | 1.743% | 1.774% |

Thus “1.49–1.74%” is the reduction relative to current b810 fuel, not its overhead percentage relative to37c3. Every champion's total is higher in b810; differences between corresponding per-champion medians are506–711 fuel, p90 differences554–764, p99 differences232–734, and maxima differences3358–3447. These are differences of profile quantiles/maxima, not quantiles of paired per-turn differences. The small residual is measurable and worth reducing, but may not explain the broader competitive pattern. No individual helper's cost is isolated.

The audited default Boss result is37c3/native fbda2–0 versus b810/e9a9 0–2. Rollovers are2+2 for37c3 versus8+16 for b810; differing trajectories prevent treating that as a direct paired cost estimate. The first extracted event-list mismatches occur in round1 and involve different actors; they are not yet a same-actor causal action witness. Initial eight outcomes remain37c3 4–0/e9a9 0–4, and recomputed52-cell totals remain4c4 31–21, current Willow32–20, current teacher25–27, native fbda30–22. Do not infer handler activation from unmarked optional97 logs: successful handling suppresses the old exception message.

## First source candidate: inert pair bookkeeping

Nominate this only as a small measurable optimization, not as the established cause. In current `src/comms.cpp:77–92`, every actor scans the ally vector and rebuilds/reset-checks the P/W mailbox even when its immutable roster has no Willow. `send` scans again at230. Prism's `bot.cpp:5119` support admission also looks for an absent Willow. These operations cannot provide support service on the teacher roster. The matched `.fuel` data above measure the entire residual, not this seam's share. Root authorized a separate source-only cache/no-pair fast path; its actual patch still requires review and its saving remains unmeasured.

The narrow contract is to cache structural Prism/Willow indices after a successful World initialization, publishing the cache only after the complete roster scan. Cache indices/absence, not vector pointers or alive status. `World::update` retries partial initialization and clears the vectors (`world.cpp:1054–1068`); no incomplete roster may permanently certify absence. For a present pair, fetch its current alive/is_self/respawn fields every turn and preserve mailbox expiry, missed-turn, death and respawn semantics exactly. A dead Willow is not an absent Willow.

For a structurally absent pair, skip only support decoding/resetting and support publication; support requests/offers must remain false. **Do not bypass ordinary communications.** `comms.cpp:156` gates all sending on `support.read_round`. Preserve that read-success stamp at its existing point immediately after `read_bits`, before ordinary sighting/capture merge, either through an inert-mailbox stamp or an explicit ordinary read epoch. An end-of-receive stamp would change exception behavior. Do not reuse `state.last_round`, which also changes on writes and dates ordinary records. Preserve raw shared reads, ordinary field masks, `state.fresh`, sightings, bag/claim reminders, captures, stale checks and write behavior. Support bits must remain untouched on the absent-pair path. Reusing the same structural indices for the Prism admission check is reasonable only if it adds no new scan/API import.

## Measurement and stopping rule

First use the paired high-fuel per-actor fuel differences to size the residual on identical gameplay, including the tail and maximum, rather than comparing unrelated default-budget totals. If this bookkeeping explains only a small fraction, do not keep expanding the fast path. The next candidate is compiled code shape around the flattened `bank_gems` call into `willow_bank_heal_step` (`bot.cpp:776,824,4691`): non-Willow exits immediately, but its presence can affect inlining. That is a hypothesis requiring actual compiled/fuel evidence, not permission to remove banking or healing behavior.

A proposed optimization should preserve the existing fuel-benchmark replay payloads, the identical high-fuel Boss timelines, and ordinary shared-memory content/expiry across missed turns; a small Willow-present control must retain pair behavior. Then evaluate default-budget matched cells and broader qualification separately. Neither a tiny winner flip nor restored throwing is a release criterion. No new fuel gate, skipped safety import, new protocol or gameplay policy belongs in this optimization.
