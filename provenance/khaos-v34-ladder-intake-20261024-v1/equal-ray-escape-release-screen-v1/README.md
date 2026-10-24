# Equal-ray Release screen (pending row review)

This arm is the source-reviewed equal-shortest-ray representation, built from aggregate `c1e19d45475ca18d2a74c344da8372d9112cc9215c8261eb4023b987db02b4e5`. `build-result.json` binds the isolated runtime copy and Release raw/injected WASM to the unchanged SDK/toolchain.

`ROWS.pending.tsv` and `ORDERED-ROWS.pending.json` describe 84 native-draft Release 100k-fuel games:

- 80 equal-ray versus frozen v33 cells: each of the 40 maps from the completed published-map panel, equal-ray on A and B.
- 4 equal-ray versus the exact connected-escape execution parent (`fcdf6007…`) stress cells, equal-ray on A, on Elk Arena, Fracture, Reverse Spiral, and Hooks.

The rows use explicit physical A/B runtime paths and candidate-side labels. Outputs were absent when rows were generated. This is a proposed diagnostic screen, not a release threshold. Do not execute before root review of the ordered rows.

The reviewed runtime command template is `nice -n 19 env CMAKE_BUILD_PARALLEL_LEVEL=1 PATH=/Users/yufan/Library/Caches/cambc/wasi-sdk-33/bin:$PATH /Users/yufan/Desktop/Development/CambridgeBattlecode2026/current-autumn/tools/runtime/cambc-3.0.5/cambc run-batch <absolute run-batch.pending.manifest> --jobs 8 --release --fuel-quantum 100000 --json --color never`, from the pinned primary runtime workspace. No game command has been run for these rows.
