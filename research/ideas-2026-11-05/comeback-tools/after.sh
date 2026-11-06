#!/bin/bash
# after.sh WAITQ NEXTQ PAR: run NEXTQ once the runner of WAITQ has exited (matched by its pid file).
cd /home/ubuntu/cambc-autumn
T=research/ideas-2026-11-05/comeback-tools
while [ -e $T/logs/$(basename $1).pid ] && kill -0 $(cat $T/logs/$(basename $1).pid) 2>/dev/null; do sleep 30; done
echo $$ > $T/logs/$(basename $2).pid
exec $T/runq.sh $T/$2 $3
