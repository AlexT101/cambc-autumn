#!/bin/bash
# exact.sh BOT TAG: bench.py at 100M (default, wide, 64 fresh-192300 maps vs astraeus-5b66bde) into replays/fuel/mk/TAG-*.json
set -e
cd "$(dirname "$0")/../.."
source /home/ubuntu/venv/bin/activate
export PATH=$HOME/.cargo/bin:$PATH CAMBC_SLOTS=86 CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
out=$PWD/replays/fuel/mk
mkdir -p $out
python tools/fuel/bench.py run "$1" --games $out/$2-default --out $out/$2-default.json | tail -1
python tools/fuel/bench.py run "$1" --set wide --games $out/$2-wide --out $out/$2-wide.json | tail -1
python tools/fuel/bench.py run "$1" --opp variants/astraeus-5b66bde --maps $(cat research/memokeys-2026-11-05/fresh64.txt) --games $out/$2-fresh --out $out/$2-fresh.json | tail -1
