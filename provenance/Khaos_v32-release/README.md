# Khaos_v32 preparation

Khaos_v32 is a src-only clone of the frozen qualified candidate. Its canonical source aggregate is `db5b37d5e5c609c2c616d3a39c0f1eb7f5adebf401dcd1be8848e0eede237ab8` across 29 files. The clone was built with cambc 3.0.5 in Release mode, one build worker, and default runtime fuel. Raw and injected WASM outputs are byte-identical to the qualified candidate build.

The pinned CLI bundle contains exactly the 29 `src/` files; each archived member was SHA-256 checked against the prepared source directory. Bundle size is 222393 bytes and local SHA-256 is `46f92918e1745b9e12994b4ae58a326d4d7e2fea20ce089cf32c1d182630df5c`. It has not been submitted.

Qualification evidence recorded in `release.json`: 1,616 games, 825–791 overall; 602 five-pick games, 319–283; the fresh seed 2026102318 heldout set was 257–255. This supports retaining the logical candidate while keeping its fuel cost under review; it is not a superiority claim.

Submitted once via the pinned CLI as server version 43 using note `Khaos_v32 - Willow support on latest Hyperion`. Exact CLI response is in `submit-response.txt`; its SHA-256 is `5e8ecbf462d11e5a20b4bee5b54db92193cfeb9d4bf4fc5396b7e0015a396bde`. The CLI reported 222,393 uploaded bytes, equal to the prepared bundle size; the remote payload was not retrieved, so remote byte identity is not asserted.
