#!/bin/bash
set -euo pipefail
ROOT=/Users/yufan/Desktop/Development/CambridgeBattlecode2026/willow-upstream-development
HAR=$ROOT/provenance/willow-pilgrimage-fuel-harness-v1/checkout-repo/tools/replay/harness
WS=$ROOT/provenance/willow-pilgrimage-fuel-harness-v1/checkout-repo/replays/willow-pilgrimage-v47/ws
CAMBC=/Users/yufan/Desktop/Development/CambridgeBattlecode2026/current-autumn/tools/runtime/cambc-3.0.5/cambc
BASE=$ROOT/provenance/khaos-v34-ladder-intake-20261024-v1/starvation-r1-trace-prep
for pair in 'starvation-v48-release starvation-v48-recorder' 'starvation-walk-control-release starvation-walk-control-recorder'; do
  read -r release recorder <<< "$pair"
  mkdir -p "$WS/bots/$recorder/src"
  cp "$WS/bots/$release/src/"* "$WS/bots/$recorder/src/"
  cp "$HAR/wrappers/harness_rec.h" "$WS/bots/$recorder/src/harness_rec.h"
  : > "$WS/bots/$recorder/RELEASE_CODE"
  nice -n 19 env CMAKE_BUILD_PARALLEL_LEVEL=1 python3 "$HAR/gen_wrappers.py" --mode rec --wasm "$WS/bots/$release/.cambc/build-release/bot.wasm" --sdk "$WS/sdk/cpp" --out "$WS/bots/$recorder/src/zz_harness.cpp" > "$BASE/logs/$recorder-wrapper-zero.stdout.log" 2> "$BASE/logs/$recorder-wrapper-zero.stderr.log"
  (cd "$WS" && nice -n 19 env CMAKE_BUILD_PARALLEL_LEVEL=1 "$CAMBC" build "bots/$recorder") > "$BASE/logs/$recorder-build-zero.stdout.log" 2> "$BASE/logs/$recorder-build-zero.stderr.log"
  nice -n 19 env CMAKE_BUILD_PARALLEL_LEVEL=1 python3 "$HAR/count_ops.py" "$WS/bots/$recorder/.cambc/build/bot.wasm" --split > "$WS/bots/$recorder/costs.json"
  nice -n 19 env CMAKE_BUILD_PARALLEL_LEVEL=1 python3 "$HAR/gen_wrappers.py" --mode rec --wasm "$WS/bots/$release/.cambc/build-release/bot.wasm" --sdk "$WS/sdk/cpp" --costs "$WS/bots/$recorder/costs.json" --out "$WS/bots/$recorder/src/zz_harness.cpp" > "$BASE/logs/$recorder-wrapper-costed.stdout.log" 2> "$BASE/logs/$recorder-wrapper-costed.stderr.log"
  (cd "$WS" && nice -n 19 env CMAKE_BUILD_PARALLEL_LEVEL=1 "$CAMBC" build "bots/$recorder") > "$BASE/logs/$recorder-build-costed.stdout.log" 2> "$BASE/logs/$recorder-build-costed.stderr.log"
  nice -n 19 env CMAKE_BUILD_PARALLEL_LEVEL=1 python3 "$HAR/count_ops.py" "$WS/bots/$recorder/.cambc/build/bot.wasm" --split > "$BASE/$recorder-cost-verification.json"
done
