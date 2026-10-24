# Band HoR routing masks: source-only diagnostic

2026-10-23. Read AGENTS.md, the Cambridge Battlecode rules, the causal review, the preceding source review and replay harness documentation. Fresh exclusive child: `bots/variants/willow-band-hor-routing-masks-work`. No build, runtime, extraction, new tooling script, gameplay policy edit, release numbering, deletion, move, cache copy or root EXPERIMENTS edit. Canonical and preceding trace sources remain unchanged.

Source aggregates use `shasum -a 256 src/* | shasum -a 256` within each bot:

| Source | SHA-256 |
|---|---|
| Canonical `bots/hyperion` | `4db4eecbda37e23dbce0b162d2cf7441a3d32a554d6534cf196e3ffbedcdf2fd` |
| Immediate parent `willow-band-hor-routing-trace-work` | `46ab555f9637c1d5d86bcb7da1fa55bbf541515b023966d1e45ee8d2dc44e414` |
| Diagnostic child | `28e64f631dfcb873338c63bebf52eb2d25bcad9da7c7c235c98b02ff06598852` |
| `candidate-v1-vs-46ab.patch` | `8cacec2dfafb140816493368d661102228a3dcbc47b4b272d015783555a1287c` |
| `candidate-v1-vs-4db.patch` | `e3f3ec1ba06678700513d752cc08688748cd392c5044aa5493e168afbcad7c22` |

`parent-46ab-src/` and `candidate-src-v1/` each contain all 29 source files and match their corresponding bot byte for byte. The manifests list all 29 bot source paths and their SHA-256 hashes. Against 46ab, only `bot.cpp`, `pathing.cpp` and `pathing.h` differ: 114 insertions, 12 deletions. The no-index whitespace check produced no diagnostics. Diff exit 1 denotes differences, not a failed source check. These checks do not imply compilation or runtime qualification.

## Record and decoding

The preceding trace's bounded r17–22 records remain. Every new output record is bounded to cached physical team A, own index2, r20–22 inclusive. New code only reads existing objects inside debug_block or prints an actual branch's existing values. No new game-visible native import, native observation, field read, route/model evaluation, guard materialization, cache mutation or fuel gate is added. The original import predicates and their short-circuit order remain: the combined cache distance/goal test is separated only before the already-last goal equality test. `kept_steps` becomes a member to access cached diagnostic identity, with no data-layout change.

`BANDMASK <round> <kind> w W h H cw CW ch CH stride S words ...` emits every real 8x8 chunk as a 16-digit hexadecimal integer, ordered by chunk row then column. For tile `(x,y)`, use emitted word index `(y/8)*CW+x/8` and bit `(y%8)*8+x%8`, least significant bit first. Ignore bits outside W/H in the final chunks. No row-padding chunk is read. Storage reads use `bitboard::ptr()` and immutable `detail::layout()` metadata; the established `world.cpp` belief serializer uses the same layout. No export/test API is needed.

- `BANDMEMBER`: source index, native group handle, member index, native camp handle, public position/type and held belief state/version/health timestamps. It includes source31, source62, and groups having a member within Chebyshev distance12 of the farm entry position. The associated `farm-held-vision` board is the existing actor/ward vision cache.
- `farm-attack-goals`: actual final attack goals, after the existing refused-tile adjustment. `farm-adjacent-goals`: actual adjacent board, only when the existing adjacent-search argument is evaluated. It is logged before the existing off-zone transformation; `route-goals` is the actual transformed search input. The already-existing route result records disambiguate successive attack/adjacent searches by call order.
- `occupied-allies`, `occupied-enemies`, `occupied-native-camps`, `occupied-teleports`: the actual original native occupancy outputs before their next reuse. `occupied-static-walking`, `occupied-unfreed` and conditional `occupied-bumps` complete the components. No occupancy is reread for diagnostics. If route uses already-fresh blocked data, component logs occur at its earlier production, and `route-input blocked-fresh` identifies this path.
- `route-final-walls`: actual walls after through-tile freeing, danger/avoid processing, the original guard call, and self-tile freeing. `route-materialized-guard` reads only `guard_` after the original guard evaluation. `route-held-belief-camps` reads only an initialized existing live_camps cache, without refreshing it; its cache version and world version accompany `route-input`. Compare full boards offline to locate changed choke tiles and distinguish native occupancy from held belief, static terrain, guard, reservations and bumps.
- `BANDCACHE` reports the actual live-cache reuse/reject branch: empty, distance/layer/cap, changed goals, too many changed walls, added relevant wall, freed goal, or freed shortcut. `route-cache-changed-walls` is the already-produced XOR before the original positions_into call. It adds no comparison or native field read.
- `approach-reuse`: actual prepare_approach reuse for source31, with range, slot pointer, held flips, live flips/versions and ready-check identity; full held goals and camp mask follow. `approach-build` logs the already-produced source31 build goals/walls/camps and identity/version/range/layer cap before its original computation. A build record alone does not mean its search succeeded. Existing approach-unavailable plus the new admission-refused record distinguishes that existing admission branch where reached.

## Limits and next step

The child does not reconstruct an old approach wall board when its field is reused; it prints the actual retained goals/camps and cache identity. It does not refresh stale belief components, force deferred guards, dump uninitialized boards, or infer native truth from public layout. There are no findings about the causal tile until the emitted boards are inspected.

Source review, then original→recorder→this trace qualification through22, including phase-aware rollovers, host-call segments, action/state prefix and original play fuel, are required before using the new record causally. Source-only checks cannot establish fuel neutrality: paused diagnostics and turning a static cache helper into a member may still alter compiled scheduling/codegen. Root/Luna owns qualification and any tooling needed to decode or compare the exact masks.
