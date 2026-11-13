#!/bin/bash
# prof.sh BOT OPP OUTDIR MAPLIST [FUEL]: per-site fuel profile (release, -g) of bots/BOT against bots/OPP, both sides.
cd /home/ubuntu/wt/mac13-hecate; source /home/ubuntu/venv/bin/activate
B=$1; P=$2; O=$3; ML=$4; F=${5:-200000}
R=/home/ubuntu/cambc-autumn/tools/fastengine/runner-prof/fastrunner
rm -rf $O; mkdir -p $O/heavy $O/oof
CXXFLAGS=-g cambc build --release bots/$B > $O/build.log 2>&1 || { echo fail > $O/done; exit 1; }
cambc build --release bots/$P >> $O/build.log 2>&1
export FASTRUNNER_FUELPROF=$O FASTRUNNER_MODE=native
i=0
for m in $(cat $ML); do
  i=$((i+1))
  $R run --release bots/$B bots/$P --map $m -o $O/g$i-a --fuel $F > $O/log$i-a 2>&1 &
  $R run --release bots/$P bots/$B --map $m -o $O/g$i-b --fuel $F > $O/log$i-b 2>&1 &
done
wait
cd /home/ubuntu/cambc-autumn/tools/fuel/fuelprof
python3 symbolise.py /home/ubuntu/wt/mac13-hecate/bots/$B $O/p.json $O > $O/sym.log 2>&1
python3 symbolise.py /home/ubuntu/wt/mac13-hecate/bots/$B $O/heavy.json $O/heavy >> $O/sym.log 2>&1
python3 symbolise.py /home/ubuntu/wt/mac13-hecate/bots/$B $O/oof.json $O/oof >> $O/sym.log 2>&1
echo $? > $O/done
