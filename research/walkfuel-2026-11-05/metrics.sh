#!/bin/bash
# metrics.sh NAME: an A/B's OOF (oof_bot), gate cuts (shortcuts) and win % by camp-group bucket (bymap) into
# wfscratch/res/NAME.metrics, in the layout research/integ-2026-11-05/table.py reads; then its batch replays are deleted.
. /home/ubuntu/cambc-autumn/.claude/worktrees/agent-ab4ebc4c0ecb8a725/wfscratch/env.sh
name=$1
mkdir -p wfscratch/res
dirs=$(ls -d replays/batch-*-ab-$name-fresh-*)
{
    echo "== $name"
    tail -n 6 wfscratch/ab-$name.log
    echo "== oof_bot"
    python tools/fuel/oof_bot.py $dirs 2>&1 | tail -n 60
    echo "== shortcuts"
    python /home/ubuntu/cambc-autumn/replays/fuel/fc5/shortcuts.py $dirs 2>&1 | tail -n 10
    echo "== bymap"
    python wfscratch/bymap.py replays/ab/$name 2>&1 | tail -n 10
} > wfscratch/res/$name.metrics
[ -s wfscratch/res/$name.metrics ] && grep -q "== bymap" wfscratch/res/$name.metrics && rm -rf $dirs
echo done $name
