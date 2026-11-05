#!/bin/bash
# exact.sh BOT TAG: bench.py at 100M (default, wide, 52 fresh-193999 maps vs the ref) and the real budget (wide,
# fresh) into replays/fuel/oc/TAG-*.json
set -e
cd /home/ubuntu/cambc-autumn/.claude/worktrees/agent-abfd641d0547466f5
source /home/ubuntu/venv/bin/activate
export PATH=$HOME/.cargo/bin:$PATH CAMBC_SLOTS=40 CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
out=$PWD/replays/fuel/oc
mkdir -p $out
python tools/fuel/bench.py run "$1" --jobs 40 --games $out/$2-default --out $out/$2-default.json | tail -1
python tools/fuel/bench.py run "$1" --set wide --jobs 40 --games $out/$2-wide --out $out/$2-wide.json | tail -1
python tools/fuel/bench.py run "$1" --opp variants/astraeus-3076ffa --maps $(cat scratch/fresh52.txt) --jobs 40 --games $out/$2-fresh --out $out/$2-fresh.json | tail -1
python tools/fuel/bench.py run "$1" --set wide --fuel 0 --jobs 40 --games $out/$2-rwide --out $out/$2-rwide.json | tail -1
python tools/fuel/bench.py run "$1" --opp variants/astraeus-3076ffa --maps $(cat scratch/fresh52.txt) --fuel 0 --jobs 40 --games $out/$2-rfresh --out $out/$2-rfresh.json | tail -1
