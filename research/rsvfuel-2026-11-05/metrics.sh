#!/bin/bash
# usage: metrics.sh NAME  -> rsvscratch/NAME.metrics (OOF, cut counts, by camp-group bucket)
. /home/ubuntu/cambc-autumn/.claude/worktrees/agent-a7617aa5334d83490/rsvscratch/env.sh
name=$1
dirs=$(ls -d replays/batch-*-ab-$name-fresh-*)
{
    echo "== $name"
    tail -n 4 rsvscratch/$name.log | head -n 2
    head -n 1 replays/ab/$name/summary.md 2>/dev/null
    echo "== oof_bot"
    python tools/fuel/oof_bot.py $dirs 2>&1 | tail -n 40
    echo "== shortcuts"
    python /home/ubuntu/cambc-autumn/replays/fuel/fc5/shortcuts.py $dirs 2>&1 | tail -n 40
    echo "== bymap"
    python rsvscratch/bymap.py replays/ab/$name 2>&1 | tail -n 20
} > rsvscratch/$name.metrics
