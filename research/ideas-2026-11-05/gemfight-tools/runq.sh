#!/bin/bash
# runq.sh: runs queue.txt's ab.py lines one at a time ("NAME CAND REF SUITES [EXTRA...]"), each once;
# lines starting with # are skipped; appended lines are picked up. Stops when queue is exhausted.
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
T=research/ideas-2026-11-05/gemfight-tools
touch $T/done.txt
while true; do
  line=$(grep -v '^#' $T/queue.txt | grep -v '^\s*$' | while read n rest; do grep -qx "$n" $T/done.txt || { echo "$n $rest"; break; }; done)
  [ -z "$line" ] && break
  set -- $line
  name=$1; cand=$2; ref=$3; suites=$4; shift 4
  echo "$(date -u +%H:%M) start $name" >> $T/runq.log
  py tools/ab.py $cand $ref --no-test-draft --suites $suites --name gf-$name "$@" > $T/logs/$name.log 2>&1
  # Disk is short: keep results.json and logs, drop the replays (batch dirs of this run only).
  for d in replays/batch-*-ab-gf-$name-*; do [ -d "$d" ] && find "$d" -name "*.repl26a" -delete; done
  echo "$name" >> $T/done.txt
  free=$(df --output=avail -BG / | tail -1 | tr -dc 0-9)
  if [ "$free" -lt 30 ]; then echo "$(date -u +%H:%M) PAUSED: disk ${free}G free" >> $T/runq.log; break; fi
  echo "$(date -u +%H:%M) end $name $(grep -m1 '\*\*total\*\*' replays/ab/gf-$name/summary.md)" >> $T/runq.log
done
echo "$(date -u +%H:%M) queue empty" >> $T/runq.log
