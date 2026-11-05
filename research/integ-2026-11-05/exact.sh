#!/bin/bash
# exact.sh BOT TAG: bench.py at 100M (default and wide sets, plus 52 fresh-192300 maps vs 5b66bde) into replays/fuel/integ/TAG-*.json
set -e
cd /home/ubuntu/cambc-autumn/.claude/worktrees/agent-a257b2d79d7ff4d76
source /home/ubuntu/venv/bin/activate
export PATH=$HOME/.cargo/bin:$PATH CAMBC_SLOTS=86 CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
out=$PWD/replays/fuel/integ
mkdir -p $out
python tools/fuel/bench.py run "$1" --jobs 64 --games $out/$2-default --out $out/$2-default.json | tail -1
python tools/fuel/bench.py run "$1" --set wide --jobs 64 --games $out/$2-wide --out $out/$2-wide.json | tail -1
python tools/fuel/bench.py run "$1" --opp variants/astraeus-5b66bde --maps $(cat scratch/fresh50.txt) --jobs 64 --games $out/$2-fresh --out $out/$2-fresh.json | tail -1
