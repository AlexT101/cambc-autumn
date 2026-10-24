#!/bin/sh
set +e
ROOT=/Users/yufan/Desktop/Development/CambridgeBattlecode2026/willow-upstream-development
BASE=$ROOT/provenance/khaos-v34-ladder-intake-20261024-v1/gem-fields-prism-quote-trace-prep
WS=$ROOT/provenance/willow-pilgrimage-fuel-harness-v1/checkout-repo/replays/willow-pilgrimage-v47/ws
HAR=$ROOT/provenance/willow-pilgrimage-fuel-harness-v1/checkout-repo/tools/replay/harness
CAMBC=/Users/yufan/Desktop/Development/CambridgeBattlecode2026/current-autumn/tools/runtime/cambc-3.0.5/cambc
REC=$WS/bots/gem-fields-f475-recorder
PATH=/Users/yufan/Library/Caches/cambc/wasi-sdk-33/bin:$PATH
export PATH
nice -n 19 env CMAKE_BUILD_PARALLEL_LEVEL=1 python3 "$HAR/count_ops.py" "$REC/.cambc/build/bot.wasm" --split > "$REC/costs.json" 2> "$BASE/logs/recorder-count-zero-v2.stderr.log"
status=$?; printf '%s\n' "$status" > "$BASE/logs/recorder-count-zero-v2.exit.txt"; [ "$status" -eq 0 ] || exit "$status"
REL=$ROOT/provenance/willow-astraeus-clock-recovery-20261024-v1/workspace/bots/service-base-f7
WASM=$REL/.cambc/build-release/bot.wasm
nice -n 19 env CMAKE_BUILD_PARALLEL_LEVEL=1 python3 "$HAR/gen_wrappers.py" --mode rec --wasm "$WASM" --sdk "$WS/sdk/cpp" --costs "$REC/costs.json" --out "$REC/src/zz_harness.cpp" > "$BASE/logs/recorder-wrapper-costed-v2.stdout.log" 2> "$BASE/logs/recorder-wrapper-costed-v2.stderr.log"
status=$?; printf '%s\n' "$status" > "$BASE/logs/recorder-wrapper-costed-v2.exit.txt"; [ "$status" -eq 0 ] || exit "$status"
(cd "$WS" && nice -n 19 env CMAKE_BUILD_PARALLEL_LEVEL=1 "$CAMBC" build bots/gem-fields-f475-recorder) > "$BASE/logs/recorder-build-costed-v2.stdout.log" 2> "$BASE/logs/recorder-build-costed-v2.stderr.log"
status=$?; printf '%s\n' "$status" > "$BASE/logs/recorder-build-costed-v2.exit.txt"; [ "$status" -eq 0 ] || exit "$status"
nice -n 19 env CMAKE_BUILD_PARALLEL_LEVEL=1 python3 "$HAR/count_ops.py" "$REC/.cambc/build/bot.wasm" --split > "$BASE/recorder-cost-verification-v2.json" 2> "$BASE/logs/recorder-count-costed-v2.stderr.log"
status=$?; printf '%s\n' "$status" > "$BASE/logs/recorder-count-costed-v2.exit.txt"; [ "$status" -eq 0 ] || exit "$status"
cmp -s "$REC/costs.json" "$BASE/recorder-cost-verification-v2.json"
status=$?; printf '%s\n' "$status" > "$BASE/logs/recorder-cost-repro-v2.exit.txt"; exit "$status"
