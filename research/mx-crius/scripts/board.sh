#!/bin/bash
# All mx-crius A/Bs: name, win %, games, CI, OOF cand/ref
cd /home/ubuntu/wt/mx-crius
for d in replays/ab/mx-crius-*; do
  s=$d/summary.md
  if [ -f $s ]; then grep "^| \*\*total" $s | awk -F'|' -v n=$(basename $d) '{printf "%-28s %6s %6s %12s oof %s/%s\n", n,$3,$4,$5,$7,$8}'
  else printf "%-28s running\n" $(basename $d); fi
done
