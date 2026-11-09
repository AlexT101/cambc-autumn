#!/bin/bash
# usage: run_ab.sh NAME CAND REF SUITE [extra ab.py args...]
cd /home/ubuntu/cambc-autumn/.claude/worktrees/ocean-removals
source /home/ubuntu/venv/bin/activate
export CAMBC_SLOTS=86 CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH
S=/tmp/claude-1000/-home-ubuntu-cambc-autumn/b97d3167-6ed0-42c1-a130-a3dd315c87de/scratchpad/gap
n=$1; c=$2; r=$3; s=$4; shift 4
python tools/ab.py $c $r --no-test-draft --suites /home/ubuntu/cambc-autumn/maps/suites/merged/$s --name $n "$@" > $S/log-$n.txt 2>&1
echo "done $n $?" >> $S/done.txt
