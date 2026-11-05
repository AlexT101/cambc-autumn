#!/bin/bash
# cmp.sh A B: bench.py compare replays/fuel/integ/A-{default,wide,fresh}.json against B-*
cd /home/ubuntu/cambc-autumn/.claude/worktrees/agent-a257b2d79d7ff4d76
source /home/ubuntu/venv/bin/activate
for s in default wide fresh; do
    echo "== $s"
    python tools/fuel/bench.py compare replays/fuel/integ/$1-$s.json replays/fuel/integ/$2-$s.json 2>&1 | head -${3:-14}
done
