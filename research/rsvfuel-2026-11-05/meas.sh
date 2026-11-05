#!/bin/bash
# usage: meas.sh BOT TAG : the bot vs 5b66bde on maps/gen and the ladder maps, batch dirs listed in rsvscratch/TAG.dirs
cd /home/ubuntu/cambc-autumn/.claude/worktrees/agent-a7617aa5334d83490
: > rsvscratch/$2.dirs
for d in maps/gen maps; do
    rsvscratch/run_batch.sh $1 variants/astraeus-5b66bde $d > rsvscratch/$2.$(basename $d).log 2>&1
    grep -o "replays/batch-[0-9-]*" rsvscratch/$2.$(basename $d).log | tail -n 1 >> rsvscratch/$2.dirs
done
echo done > rsvscratch/$2.done
