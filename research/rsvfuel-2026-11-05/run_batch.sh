#!/bin/bash
# usage: run_batch.sh BOT1 BOT2 MAPSDIR [extra run_batched args]
. /home/ubuntu/cambc-autumn/.claude/worktrees/agent-a7617aa5334d83490/rsvscratch/env.sh
export CAMBC_LOG_LIMIT=32000000
b1=$1 b2=$2 dir=$3
shift 3
python tools/run_batched.py $b1 $b2 --maps-dir $dir "$@"
