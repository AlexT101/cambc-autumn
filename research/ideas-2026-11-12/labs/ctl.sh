#!/bin/bash
# ctl.sh status | start | pause | resume | stop | kill | base BOTDIR
#   status: filler and round state.  start: launch the filler (if not running).  pause/resume: no new rounds / allow.
#   stop: the filler exits (a running round goes on).  kill: end the running round now (its process group; it is
#   marked failed and posted).  base: set BASE for the next round.
L=/home/ubuntu/tmp-offload/labs; R=/home/ubuntu/cambc-autumn
up() { [ -f $L/filler.pid ] && kill -0 $(cat $L/filler.pid) 2>/dev/null; }
cur() { for d in $L/rounds/*/; do [ -f $d/pid ] && [ ! -f $d/exit ] && kill -0 $(cat $d/pid) 2>/dev/null && echo ${d%/}; done; }
case $1 in
  status)
    up && echo "filler up, pid $(cat $L/filler.pid)" || echo "filler DOWN"
    echo "BASE $(cat $L/BASE); LIST $(grep -v '^#' $L/LIST | tr '\n' ' ')$( [ -f $L/PAUSE ] && echo '; PAUSED')"
    for d in $L/rounds/*/; do [ -f $d/round.json ] || continue
      echo "$(basename $d): $(python3 -c "import json;i=json.load(open('$d/round.json'));print(i['base'],i['created'])") exit=$(cat $d/exit 2>/dev/null || echo running)"
      tail -n 2 $d/events 2>/dev/null | sed 's/^/    /'; done
    tail -n 3 $L/filler.log ;;
  start) up && echo "already up" || { rm -f $L/STOP; cd $R && nohup setsid python3 $R/research/ideas-2026-11-12/labs/filler.py >> $L/filler.out 2>&1 < /dev/null & sleep 1; up && echo "started $(cat $L/filler.pid)"; } ;;
  pause) touch $L/PAUSE ;;
  resume) rm -f $L/PAUSE ;;
  stop) touch $L/STOP ;;
  kill) d=$(cur); [ -n "$d" ] || { echo "no round running"; exit 0; }
        echo "killed by ctl.sh" > $d/fail; kill -TERM -$(cat $d/pid); echo "sent TERM to round $(basename $d)'s group" ;;
  base) [ -d $R/$2/src ] || { echo "no $R/$2/src"; exit 1; }; echo $2 > $L/BASE; echo "BASE = $2" ;;
  *) sed -n 2,6p $0 ;;
esac
