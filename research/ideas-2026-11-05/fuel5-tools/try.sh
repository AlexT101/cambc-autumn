#!/bin/bash
# try.sh NAME MODES: bench bots/variants/oc-f5-NAME (made beforehand) vs oc-fuel4 at 100M and compare with oc-fuel4's own
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
n=$1; shift; modes=${*:-def}
replays/fuel/ocfuel5/bench.sh variants/oc-f5-$n $n $modes
for m in $modes; do
  case $m in real) f=wide-real;; *) f=$m-100M;; esac
  echo "== $n $m"; python3 tools/fuel/bench.py compare replays/fuel/ocfuel5/bench/base-$f.json replays/fuel/ocfuel5/bench/$n-$f.json | head -3
done
