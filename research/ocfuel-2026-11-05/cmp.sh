#!/bin/bash
# cmp.sh A B: bench.py compare replays/fuel/oc/A-{default,wide,fresh}.json against B-*
cd /home/ubuntu/cambc-autumn/.claude/worktrees/agent-abfd641d0547466f5
source /home/ubuntu/venv/bin/activate
for s in default wide fresh; do
    echo "== $s"
    python tools/fuel/bench.py compare replays/fuel/oc/$1-$s.json replays/fuel/oc/$2-$s.json 2>&1 | head -${3:-14}
done
