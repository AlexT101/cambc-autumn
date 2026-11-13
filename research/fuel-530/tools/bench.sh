#!/bin/bash
set -euo pipefail
cd /home/ubuntu/wt/fuel-530
source /home/ubuntu/venv/bin/activate
export CAMBC_SLOTS=86 CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH
bot=$1; tag=$2; mode=$3; shift 3
args=()
case "$mode" in
  id) args=(--set wide);;
  td) args=(--set wide --test-draft);;
  dev|final|cov) mapfile -t maps < "research/fuel-530/maps-$mode.txt"; args=(--maps "${maps[@]}");;
esac
py tools/fuel/bench.py run "$bot" --opp "${OPP:-variants/chy-530}" "${args[@]}" --jobs 86 --games "$PWD/replays/fuel/f530/$tag-games" --out "replays/fuel/f530/$tag.json" "$@" > "replays/fuel/f530/$tag.log" 2>&1
