#!/bin/bash
# Stop the scrim runner cleanly (STOP file) and relaunch it detached with our quota cap (~90/hour: reserve 10).
R=$(cd "$(dirname "$0")/.." && pwd); D=$R/research/ladder-scrims-2026-11-06/data
OLD=$(cat $D/run.lock 2>/dev/null)
if [ -n "$OLD" ] && kill -0 $OLD 2>/dev/null; then touch $D/STOP; while kill -0 $OLD 2>/dev/null; do sleep 2; done; fi
rm -f $D/STOP
cd $R; setsid nohup /home/ubuntu/venv/bin/python tools/ladder_scrims.py run --reserve 10 --pace 10 --inflight 16 --idle 30 --tick 5 >> $D/run.log 2>&1 < /dev/null &
sleep 5; cat $D/run.lock
