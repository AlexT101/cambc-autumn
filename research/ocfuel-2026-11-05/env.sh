#!/bin/bash
# Usage: scratch/env.sh CMD...  (runs CMD in the worktree with this campaign's environment)
source /home/ubuntu/venv/bin/activate
export PATH=$HOME/.cargo/bin:$PATH CAMBC_SLOTS=40 CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
cd /home/ubuntu/cambc-autumn/.claude/worktrees/agent-abfd641d0547466f5
exec "$@"
