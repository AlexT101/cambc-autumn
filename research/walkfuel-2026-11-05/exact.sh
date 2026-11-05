#!/bin/bash
# exact.sh BOT TAG: bench.py at 100M (default and wide sets, plus the 52 fresh-192300 maps of
# research/integ-2026-11-05/fresh50.txt vs 5b66bde) into replays/fuel/wf/TAG-*.json; cmp.sh compares two tags.
set -e
. /home/ubuntu/cambc-autumn/.claude/worktrees/agent-ab4ebc4c0ecb8a725/wfscratch/env.sh
out=$PWD/replays/fuel/wf
mkdir -p $out
python tools/fuel/bench.py run "$1" --jobs 64 --games $out/$2-default --out $out/$2-default.json | tail -n 1
python tools/fuel/bench.py run "$1" --set wide --jobs 64 --games $out/$2-wide --out $out/$2-wide.json | tail -n 1
python tools/fuel/bench.py run "$1" --opp variants/astraeus-5b66bde --maps $(cat research/integ-2026-11-05/fresh50.txt) --jobs 64 --games $out/$2-fresh --out $out/$2-fresh.json | tail -n 1
echo done > $out/$2.done
