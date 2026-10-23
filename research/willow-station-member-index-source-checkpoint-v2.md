# Willow station static camp-member index source checkpoint v2

2026-10-23. This source-only follow-up fixes cold pool growth after actual-source review. The c582 checkpoint and source remain preserved and unchanged as the superseded v1 snapshot. No build, test, engine, extraction, or profile was run.

## Pins

- Frozen source130 parent: `bots/variants/willow-prism-coordinated-work/src/`, aggregate SHA-256 `130a17af668a432a8a5582ec0736b1ef13c22e05245bc5742e472f3d02a620a5`.
- Superseded v1 child, unchanged: `bots/variants/willow-prism-station-member-index-work/src/`, aggregate SHA-256 `c58282cad1f05d1643f2db77a5e11a55f2bdab9637ff559cb0ba2db730664d89`.
- V2 child: `bots/variants/willow-prism-station-member-index-work-v2/src/`, aggregate SHA-256 `12f3a622d3907f31f32dd34e80e9436df75f84c59f2282c32fe6846b3b2840a9`.
- V2-only patch relative to v1: `research/willow-station-member-index-source-v2.patch`.
- V1 record remains `research/willow-station-member-index-source-checkpoint.md` and `research/willow-station-member-index-source.patch`.

The v1 8×8 lazy descriptor pages remain: at most 169 page pointers for a 100×100 map. That pointer directory is 676 bytes with 32-bit pointers (WASM32) or 1,352 bytes with 64-bit pointers, excluding vector control/allocation overhead; each touched page additionally allocates 64 range descriptors. Pages are created only when queried. The directory and page allocations are cold-query costs, not free.

The pool now checks `max_size()` and computes required capacity. It reserves only when necessary, growing to `max(required, safely-doubled-capacity)` (with a one-element minimum from zero capacity), then appends trivial references before publishing the range. This avoids repeatedly requesting exact incremental capacities and the resulting quadratic pool copying on common STL implementations. Pool reallocation/copying, pending-list allocations, and page costs remain cold-path overhead and are unmeasured.

All other v1 semantics are unchanged: `groups_near` still runs on every request; only the prescribed static member filter is cached; dynamic state is read afresh; order and floating-point operations are preserved; only Willow station calls use the index; fallback callers retain their original loop. `git diff --no-index --check` passed for the changed `world.cpp` relative to v1. Astra actual-source review is still required before runtime work. No compile, replay identity, fuel savings, or default-fuel effect is claimed.
