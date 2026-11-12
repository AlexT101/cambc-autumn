#!/bin/bash
# bodystats.sh RUN...: decode an ab run's replays into ~/tmp-offload/fishr8/ext/RUN and write mstats/fstats/vesper/
# traj/fishx stats to ~/tmp-offload/fishr8/stats/{m,f,v,t,x}-RUN.jsonl.
R=/home/ubuntu/cambc-autumn; H=/home/ubuntu/tmp-offload/fishr8; F=$R/research/ideas-2026-11-12/fishr8; M=$R/research/ideas-2026-11-12/mitefit; cd $R
for RUN in "$@"; do
  [ -f $H/stats/v-$RUN.jsonl ] && continue
  python3 tools/pooled.py 12 -- node tools/replay/extract.mjs $(ls -d replays/batch-*-ab-$RUN-*) --out $H/ext/$RUN --threads 12 > $H/logs/ext-$RUN.log 2>&1
  python3 $F/localrows.py $H/ext/$RUN $H/ext/$RUN/rows.json
  for s in "m $M/mstats.py live" "f $M/fstats.py live" "v $F/vesper.py" "t $F/traj.py" "x $F/fishx.py"; do
    set -- $s; k=$1; shift
    OMP_NUM_THREADS=8 python3 tools/pooled.py 8 -- python3 "$@" $H/ext/$RUN $H/ext/$RUN/rows.json $H/stats/$k-$RUN.jsonl >> $H/logs/ext-$RUN.log 2>&1
  done
done
