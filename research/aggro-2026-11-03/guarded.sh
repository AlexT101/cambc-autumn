#!/bin/bash
# Runs queue4.sh with the given variants in its own process group; kills that group if MemAvailable < MIN_GB.
cd ~/cambc-autumn
MIN_GB=${MIN_GB:-40}
setsid ${QUEUE:-replays/aggro/queue4.sh} "$@" &
Q=$!
while kill -0 $Q 2>/dev/null; do
  a=$(awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo)
  echo "$(date -u +%H:%M:%S) avail ${a}G" >> ${MEMLOG:-replays/aggro/mem.log}
  if [ "$a" -lt "$MIN_GB" ]; then echo "$(date -u +%H:%M:%S) LOW MEMORY ${a}G: killing group $Q" | tee -a ${MEMLOG:-replays/aggro/mem.log}; kill -TERM -- -$Q; sleep 3; kill -KILL -- -$Q 2>/dev/null; exit 1; fi
  sleep 5
done
