#!/bin/bash
# check.sh BOT TAG: bench.py at 100M on def/wide/pool against oc-retest-clean, compared with the base (identity + fuel).
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
T=research/ideas-2026-11-05/fuel7-tools D=replays/fuel/ocfuel7/bench
KEEP=0 $T/bench.sh $1 $2 def wide pool > /dev/null 2>&1
for m in def wide pool; do echo "$m: $(python3 tools/fuel/bench.py compare $D/base-$m-100M.json $D/$2-$m-100M.json | head -2 | tr '\n' ' ')"; done
