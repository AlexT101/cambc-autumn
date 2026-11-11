#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../../.."
source /home/ubuntu/venv/bin/activate
export CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
kind=$1; bot=$2; name=$3; shift 3
out=replays/fuel/fuelD
mkdir -p "$out"
case "$kind" in
  own) args=(--set wide) ;;
  td) args=(--set wide --test-draft) ;;
  screen|dev|confirm) mapfile -t maps < "research/charybdis-fuelD/tools/maps-$kind.txt"; args=(--maps "${maps[@]}" --fuel 0) ;;
  coverage) mapfile -t maps < research/charybdis-fuelD/tools/maps-coverage.txt; args=(--maps "${maps[@]}" --test-draft) ;;
  *) exit 1 ;;
esac
python tools/fuel/bench.py run "$bot" --opp "${OPP:-variants/chary-fuelD-base}" "${args[@]}" --jobs 86 --out "$out/$name.json" "$@" > "$out/$name.log" 2>&1
