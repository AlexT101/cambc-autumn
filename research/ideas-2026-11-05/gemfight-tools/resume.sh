#!/bin/bash
# Waits for the orphaned ab.py of full-v3b25p0, records it, drops its replays, then restarts runq.sh.
cd /home/ubuntu/cambc-autumn
T=research/ideas-2026-11-05/gemfight-tools
while kill -0 1286159 2>/dev/null; do sleep 5; done
echo "full-v3b25p0" >> $T/done.txt
echo "$(date -u +%H:%M) end full-v3b25p0 $(grep -m1 '\*\*total\*\*' replays/ab/gf-full-v3b25p0/summary.md)" >> $T/runq.log
for d in replays/batch-*-ab-gf-full-v3b25p0-*; do find "$d" -name "*.repl26a" -delete; done
exec $T/runq.sh
