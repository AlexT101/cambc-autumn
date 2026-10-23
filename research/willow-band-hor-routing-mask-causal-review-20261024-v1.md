# Band HoR routing masks: qualified partial causal review

2026-10-24 UTC, Astra. **Partial finding preserved pending pure-file coordinate decoding; no gameplay repair is yet specified.** Read the Cambridge Battlecode rules, prior causal/source reviews, actual mask-trace source, `band-mask-trace-prefix-validation-v1.json` and `phase4-postrun-audit-v1.json`. No engine, build, new script or EXPERIMENTS edit.

Evidence root: `replays/willow-band-hor-routing-witness-20261023-v1/phase4-mask-trace/`. Original→recorder→trace equality is qualified through22:527 inputs,23 round hashes,6 phase-aware rollovers,66 matching trace segments and no mismatch in that prefix. Trace source aggregate is `28e64f631dfcb873338c63bebf52eb2d25bcad9da7c7c235c98b02ff06598852`. `trace-team-a.stdout` SHA-256 is `c985b86730f4ca512277d11b044a1b2d2cbaef8cfde8d7e61020b9fe66175dd2`. Later divergence is unqualified and unused. The stdout contains NULs; text searches require binary-as-text handling.

## Established before tile decoding

1. The selected economic target is source31/native-group31, centre `(46,42)`, four Gold clusters: native45 `(47,43)`,47 `(47,42)`,49 `(46,43)`,51 `(46,42)`. Group/claim remain31, crew/spell0, no zone, all74 groups evaluated. Native Wolf100 is **not** the selected target.
2. `BANDMEMBER` now proves source62/native-group62 contains native Wolf100 at `(13,33)`,1350HP. Its belief is observed at20, retains20 dates at21, and is observed again22. This resolves the prior warning against inferring the mapping from equal indices.
3. Every logged farm attack goal, adjacent goal, route goal and reused approach goal has the same serialized-word SHA-256 `4e0dc901f91767bb551d2644e9ed628f7a33723921aaacaf4626bbf525f01f51`. Goals are not the observed source of alternation. Walking-static masks are also identical across the three rounds.
4. Native camp occupancy has one nonzero chunk at20/22 and is completely empty21. Held belief-camp masks remain identical throughout, SHA `100f17661ae76872eafa988596488ba63c916ed7a8655077c6dece813cb9ce32`, and match the reused approach's camps. Farm-held vision20=22 but differs21. Coordinate decoding is needed to verify the exact camp/vision bit and isolate allied-occupancy deltas.

| Round | Qualified route/cache record | Accepted action |
|---|---|---|
| 20, start `(11,32)` | Attack/adjacent cache both reject **added-wall `(13,33)`**. Both live searches hit cap61 with61 layers and `exhausted=0`. Approach group31/range1 reuses slot`0x372dc0`, flips74, live-flips74, world/live version0. | Approach descent63→62, sole first step `(11,31)`, native-result1. |
| 21, start `(11,31)` | Attack route cache accepts `allowed-changes`, distance49, cap62; next distance48, sole first step `(11,32)`. | Native-result1, attack-search success. |
| 22, start `(11,32)` | Both live routes again reject added-wall `(13,33)` and hit cap61. Same approach slot/range/flips/version reused. | Approach descent63→62 to `(11,31)`, native-result1. |

The source's cache protocol matters: failed live searches return without replacing the older kept field. At21 that field is admissible under the new native wall mask; at20/22 its shorter-layer wall addition is explicitly rejected. This is evidence that the live cache **does notice** the Wolf blocker when present, not yet evidence of a broken cache invalidation test. The one-layer cap change cannot explain distance48 becoming unreachable at cap61 without an obstacle/model change.

Current source `occupied_into` uses native current-perspective camps; `live_camps` instead keeps believed-live members until camp belief versions change. Approach combines that belief mask with dash-kind static terrain and checks stable flips/mask for reuse. Live routing uses walking terrain plus native occupancy. Thus the qualified records strongly implicate an observation-dependent opening in the live obstacle model while the approach retains the Wolf. They do not establish that rebuilding a cache, increasing a cap, or attacking Wolf100 is the right repair.

No `route-avoid`, materialized-guard or bump masks occur; route-input records show no deferred guard, no bumps, and through`(-1,-1)`. These statements describe the logged current calls, not unobserved past lazy state. The cached approach's original built-walls mask is not emitted in20–22 because the field is reused. Its precise old static-wall composition must not be invented from a current native mask.

## Pending bounded file work

Root was asked to delegate a pure-file decoder for all62 BANDMASK records, preserving order and joining BANDMEMBER mappings. Verify chunk layout from source/SDK:84×84 map,11×11 real chunks, storage stride12; tile bit`(y&7)*8+(x&7)`. Need coordinate sets/deltas for goals, native camps, final route walls, allied occupancy, held belief/approach camps, vision and route-cache changed walls. In particular establish whether `(13,33)` disappears from the actor's vision/native walls21 yet stays in held approach camps, and whether allied changes affect the traversed choke. Do not synthesize missing approach-build masks or treat cache-XOR masks as direct successive-round differences.

After decoding, decide whether the narrow candidate is consistent actor-known camp obstacles for **farm travel** with fresh observed deaths opening tiles, rather than a goal or generic cache change. Preserve combat/dash semantics and require a source-known witness that exits the reversal and reaches productive work. No no-reverse rule, map selector, arbitrary target ban, or unbounded cap increase is justified here.
