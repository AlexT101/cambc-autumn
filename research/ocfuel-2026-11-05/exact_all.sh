#!/bin/bash
# exact_all.sh TAG...: exact.sh variants/ast-TAG TAG for each
cd /home/ubuntu/cambc-autumn/.claude/worktrees/agent-abfd641d0547466f5
for v in "$@"; do scratch/exact.sh variants/ast-$v $v > scratch/res/exact-$v.log 2>&1; echo "$v rc=$?"; done
