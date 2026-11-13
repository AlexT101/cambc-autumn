#!/bin/bash
set -euo pipefail
cd /home/ubuntu/cambc-autumn
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
bot=$1
tag=$2
mode=$3
shift 3
args=()
case "$mode" in
  id) args=(--set wide);;
  cov) mapfile -t maps < research/fuel-527/maps-cov.txt; args=(--maps "${maps[@]}" --test-draft);;
  td) args=(--set wide --test-draft);;
  screen|dev|final) mapfile -t maps < "research/fuel-527/maps-$mode.txt"; args=(--maps "${maps[@]}" --fuel 0);;
esac
py tools/fuel/bench.py run "$bot" --opp "${OPP:-variants/chy-fuel527-base}" "${args[@]}" --jobs 86 \
  --games "$PWD/replays/fuel/chy527/$tag-games" --out "replays/fuel/chy527/$tag.json" "$@" \
  > "replays/fuel/chy527/$tag.log" 2>&1
