#!/bin/bash
# lprof.sh BOT OUTDIR MAPLIST: per-site fuel profile (tools/fuel/fuelprof) of bots/BOT (release, -g) against
# variants/chy-life at the real budget, both sides; OUTDIR/p.json (all turns), heavy.json (88k+), oof.json.
cd /home/ubuntu/cambc-autumn; source /home/ubuntu/venv/bin/activate
B=$1; O=$2; ML=$3
mkdir -p $O/heavy $O/oof
CXXFLAGS=-g cambc build --release bots/$B > $O/build.log 2>&1 || { echo fail > $O/done; exit 1; }
cambc build --release bots/variants/chy-life >> $O/build.log 2>&1
export FASTRUNNER_FUELPROF=$O FASTRUNNER_MODE=native
i=0
for m in $(cat $ML); do
  i=$((i+1))
  tools/fastengine/runner-prof/fastrunner run --release bots/$B bots/variants/chy-life --map $m -o $O/g$i-a > $O/log$i-a 2>&1 &
  tools/fastengine/runner-prof/fastrunner run --release bots/variants/chy-life bots/$B --map $m -o $O/g$i-b > $O/log$i-b 2>&1 &
done
wait
cd tools/fuel/fuelprof
for d in "" heavy oof; do python3 ~/tmp-offload/fuelB/tools/symbolise_fn.py /home/ubuntu/cambc-autumn/bots/$B $O/${d:-p}.json $O/$d >> $O/sym.log 2>&1; done
echo $? > $O/done
