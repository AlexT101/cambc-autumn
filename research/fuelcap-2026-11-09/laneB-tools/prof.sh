#!/bin/bash
# prof.sh BOT OUTDIR MAPLIST: per-site fuel profile of BOT (release, -g) vs ocean-16d6f78 at the real budget, both sides.
cd /home/ubuntu/cambc-autumn; source /home/ubuntu/venv/bin/activate
B=$1; O=$2; ML=$3
rm -rf $O; mkdir -p $O
CXXFLAGS=-g cambc build --release bots/$B > $O/build.log 2>&1 || { echo fail > $O/done; exit 1; }
cambc build --release bots/variants/ocean-16d6f78 >> $O/build.log 2>&1
export FASTRUNNER_FUELPROF=$O FASTRUNNER_MODE=native
i=0
for m in $(cat $ML); do
  i=$((i+1))
  tools/fastengine/runner-prof/fastrunner run --release $B variants/ocean-16d6f78 --map $m -o $O/g$i-a > $O/log$i-a 2>&1 &
  tools/fastengine/runner-prof/fastrunner run --release variants/ocean-16d6f78 $B --map $m -o $O/g$i-b > $O/log$i-b 2>&1 &
done
wait
cd tools/fuel/fuelprof && python3 ~/tmp-offload/fuelB/tools/symbolise_fn.py /home/ubuntu/cambc-autumn/bots/$B $O/p.json $O > $O/sym.log 2>&1
echo $? > $O/done
