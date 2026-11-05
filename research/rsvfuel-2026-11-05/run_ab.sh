#!/bin/bash
# usage: run_ab.sh NAME CAND FIRST LAST
. /home/ubuntu/cambc-autumn/.claude/worktrees/agent-a7617aa5334d83490/rsvscratch/env.sh
ab "$@"
echo done > rsvscratch/$1.done
