#!/bin/bash
# cmp.sh BASE CAND: bench.py compare on the three sets exact.sh ran.
. /home/ubuntu/cambc-autumn/.claude/worktrees/agent-ab4ebc4c0ecb8a725/wfscratch/env.sh
out=$PWD/replays/fuel/wf
for s in default wide fresh; do
    echo "== $s"
    python tools/fuel/bench.py compare $out/$1-$s.json $out/$2-$s.json | tail -n 25
done
