#!/bin/bash
# queue.sh MAXJOBS "ARM SUITE [args]" ... : runs ab.sh jobs, at most MAXJOBS at once
max=$1; shift
D=/tmp/claude-1000/-home-ubuntu-cambc-autumn/3650a530-f591-417e-a0c5-31524a1e3260/scratchpad/kill
for job in "$@"; do
  while [ $(jobs -rp | wc -l) -ge $max ]; do sleep 20; done
  echo "$(date +%T) start $job" >> $D/queue.log
  ( $D/scripts/ab.sh $job; echo "$(date +%T) done $job" >> $D/queue.log ) &
  sleep 5
done
wait
