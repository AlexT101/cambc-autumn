#!/bin/bash
# prof.sh BOT OUTDIR MAPLIST: per-site fuel profile of bots/BOT (release, -g) vs variants/ocf-popp at the real budget, both sides.
cd /home/ubuntu/cambc-autumn; source /home/ubuntu/venv/bin/activate
B=$1; O=$2; ML=$3
rm -rf $O; mkdir -p $O/heavy $O/oof
CXXFLAGS=-g cambc build --release bots/$B > $O/build.log 2>&1 || { echo fail > $O/done; exit 1; }
cambc build --release bots/variants/ocf-popp >> $O/build.log 2>&1
export FASTRUNNER_FUELPROF=$O FASTRUNNER_MODE=native
i=0
for m in $(cat $ML); do
  i=$((i+1))
  tools/fastengine/runner-prof/fastrunner run --release bots/$B bots/variants/ocf-popp --map $m -o $O/g$i-a ${FUELARG} > $O/log$i-a 2>&1 &
  tools/fastengine/runner-prof/fastrunner run --release bots/variants/ocf-popp bots/$B --map $m -o $O/g$i-b ${FUELARG} > $O/log$i-b 2>&1 &
done
wait
cd tools/fuel/fuelprof && python3 ~/tmp-offload/fuelB/tools/symbolise_fn.py /home/ubuntu/cambc-autumn/bots/$B $O/p.json $O > $O/sym.log 2>&1
python3 ~/tmp-offload/fuelB/tools/symbolise_fn.py /home/ubuntu/cambc-autumn/bots/$B $O/heavy.json $O/heavy >> $O/sym.log 2>&1
python3 ~/tmp-offload/fuelB/tools/symbolise_fn.py /home/ubuntu/cambc-autumn/bots/$B $O/oof.json $O/oof >> $O/sym.log 2>&1
echo $? > $O/done
