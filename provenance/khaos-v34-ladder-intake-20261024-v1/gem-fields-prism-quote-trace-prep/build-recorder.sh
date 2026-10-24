#!/bin/sh
set +e
ROOT=/Users/yufan/Desktop/Development/CambridgeBattlecode2026/willow-upstream-development
BASE=$ROOT/provenance/khaos-v34-ladder-intake-20261024-v1/gem-fields-prism-quote-trace-prep
WS=$ROOT/provenance/willow-pilgrimage-fuel-harness-v1/checkout-repo/replays/willow-pilgrimage-v47/ws
HAR=$ROOT/provenance/willow-pilgrimage-fuel-harness-v1/checkout-repo/tools/replay/harness
CAMBC=/Users/yufan/Desktop/Development/CambridgeBattlecode2026/current-autumn/tools/runtime/cambc-3.0.5/cambc
REL=$ROOT/provenance/willow-astraeus-clock-recovery-20261024-v1/workspace/bots/service-base-f7
WASM=$REL/.cambc/build-release/bot.wasm
REC=$WS/bots/gem-fields-f475-recorder
mkdir -p "$REC/src" "$BASE/logs"
cp "$REL/src/"* "$REC/src/" || exit 125
cp "$HAR/wrappers/harness_rec.h" "$REC/src/harness_rec.h" || exit 125
: > "$REC/RELEASE_CODE"
nice -n 19 env CMAKE_BUILD_PARALLEL_LEVEL=1 python3 "$HAR/gen_wrappers.py" --mode rec --wasm "$WASM" --sdk "$WS/sdk/cpp" --out "$REC/src/zz_harness.cpp" > "$BASE/logs/recorder-wrapper-zero.stdout.log" 2> "$BASE/logs/recorder-wrapper-zero.stderr.log"
status=$?; printf '%s\n' "$status" > "$BASE/logs/recorder-wrapper-zero.exit.txt"; [ "$status" -eq 0 ] || exit "$status"
(cd "$WS" && nice -n 19 env CMAKE_BUILD_PARALLEL_LEVEL=1 "$CAMBC" build bots/gem-fields-f475-recorder) > "$BASE/logs/recorder-build-zero.stdout.log" 2> "$BASE/logs/recorder-build-zero.stderr.log"
status=$?; printf '%s\n' "$status" > "$BASE/logs/recorder-build-zero.exit.txt"; [ "$status" -eq 0 ] || exit "$status"
nice -n 19 env CMAKE_BUILD_PARALLEL_LEVEL=1 python3 "$HAR/count_ops.py" "$REC/.cambc/build/bot.wasm" --split > "$REC/costs.json" 2> "$BASE/logs/recorder-count-zero.stderr.log"
status=$?; printf '%s\n' "$status" > "$BASE/logs/recorder-count-zero.exit.txt"; [ "$status" -eq 0 ] || exit "$status"
nice -n 19 env CMAKE_BUILD_PARALLEL_LEVEL=1 python3 "$HAR/gen_wrappers.py" --mode rec --wasm "$WASM" --sdk "$WS/sdk/cpp" --costs "$REC/costs.json" --out "$REC/src/zz_harness.cpp" > "$BASE/logs/recorder-wrapper-costed.stdout.log" 2> "$BASE/logs/recorder-wrapper-costed.stderr.log"
status=$?; printf '%s\n' "$status" > "$BASE/logs/recorder-wrapper-costed.exit.txt"; [ "$status" -eq 0 ] || exit "$status"
(cd "$WS" && nice -n 19 env CMAKE_BUILD_PARALLEL_LEVEL=1 "$CAMBC" build bots/gem-fields-f475-recorder) > "$BASE/logs/recorder-build-costed.stdout.log" 2> "$BASE/logs/recorder-build-costed.stderr.log"
status=$?; printf '%s\n' "$status" > "$BASE/logs/recorder-build-costed.exit.txt"; [ "$status" -eq 0 ] || exit "$status"
nice -n 19 env CMAKE_BUILD_PARALLEL_LEVEL=1 python3 "$HAR/count_ops.py" "$REC/.cambc/build/bot.wasm" --split > "$BASE/recorder-cost-verification.json" 2> "$BASE/logs/recorder-count-costed.stderr.log"
status=$?; printf '%s\n' "$status" > "$BASE/logs/recorder-count-costed.exit.txt"; [ "$status" -eq 0 ] || exit "$status"
cmp -s "$REC/costs.json" "$BASE/recorder-cost-verification.json"
status=$?; printf '%s\n' "$status" > "$BASE/logs/recorder-cost-repro.exit.txt"; exit "$status"
