#!/bin/bash
# exact.sh BOT TAG: bench.py at 100M (default and wide sets, plus 64 fresh-192300 maps) into replays/fuel/crew/TAG-*.json
set -e
cd "$(dirname "$0")/../.."
export PATH=/home/ubuntu/venv/bin:$HOME/.cargo/bin:$PATH CAMBC_SLOTS=86
export CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
out=$PWD/replays/fuel/crew
mkdir -p $out
py=/home/ubuntu/venv/bin/python
$py tools/fuel/bench.py run "$1" --jobs 64 --games $out/$2-default --out $out/$2-default.json | tail -1
$py tools/fuel/bench.py run "$1" --set wide --jobs 64 --games $out/$2-wide --out $out/$2-wide.json | tail -1
$py tools/fuel/bench.py run "$1" --opp variants/astraeus-5b66bde --maps $(cat replays/cprof/maps.txt) --jobs 64 --games $out/$2-fresh --out $out/$2-fresh.json | tail -1
