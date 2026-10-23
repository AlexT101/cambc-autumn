# Fish roster emulator — source checkpoint

- Candidate: `bots/variants/hyperion-fish-roster-emulator-fbda803`
- Parent source: `bots/baselines/hyperion-upstream-fbda803`, aggregate `15dcd64d35c179a726c02d3e775b1e3f263f9a4c33b5a8c745e7b13f66dd802d`
- Candidate source aggregate: `10e5eeaabd57580f2ccd59240f36341209c2337fa9f190c8ea310b79943c90ac` (28 source files)
- Changed source files: `draft.cpp`
- Five-pick order: Vesper Vale, Vendetta, Heart of Ruin, Varg, Cassi & Issac (draft enum `[1, 2, 11, 9, 3]`).
- Three- and four-pick selection remain native fbda803 behavior. `test_draft=false`.
- This is only a roster emulator: no Fish policy, submission, or source identity is implied.
- No build or match was run.
- Frozen engine/tool preflight: `cambc 3.0.5`, CLI path `/Users/yufan/Desktop/Development/CambridgeBattlecode2026/current-autumn/tools/runtime/cambc-3.0.5/cambc`.

The source edit adds a five-pick-only early return from `draft_order`; four-pick logic and fallback/native three-pick logic are untouched.

## First comparison map identity check

The frozen public Fish replay maps decode to engine hashes `51ebf62356056f62` (Expanse, 80x80, five picks) and `c890c7d4607bc45c` (Big World, 100x100, five picks). Decoding local `maps/00expanse.map26a` and `maps/01big-world.map26a` with replay engine v1.0.3 produced the same respective hashes, so those local files match the downloaded replay maps. Local map file SHA-256 values are separately recorded by the eventual run setup. This is map identity only, not game/source identity.
