#!/bin/bash
# calib.sh BOT BODY K0 K1 [SUITE]: BOT (our side, metered 100k) against a body on the ladder maps (or SUITE), both
# sides, once per noise member k in K0..K1 (seed 1310000+k, draft salt k; a body without the run-time import plays
# metered and without a config). Runs are replays/ab/mf-<bot>-<body>-<suite>-k<k>. Done-file per run.
B=$1; BODY=$2; K0=$3; K1=$4; SU=${5:-ladder}
R=/home/ubuntu/cambc-autumn; M=/home/ubuntu/tmp-offload/mitefit; cd $R
export CAMBC_BIN=$R/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native FGATE_RUNNER_LIB=$R/tools/fastengine/runner/target-rt/release/libfastrunner.so
export FASTRUNNER_LIB=$FGATE_RUNNER_LIB
bn=$(basename $B); on=$(basename $BODY); sn=$(basename $SU)
rt=0; grep -qs import_module bots/$BODY/src/experiment_config.h && rt=1
for k in $(seq $K0 $K1); do
  n=mf-$bn-$on-$sn-k$k
  [ -f replays/ab/$n/summary.json ] && continue
  if [ $rt = 1 ]; then
    cfg=$M/cfg/$sn-k$k.json
    [ -f $cfg ] || python3 - "$SU" $k $cfg <<'PY'
import json,sys,os,glob
su,k,out=sys.argv[1],int(sys.argv[2]),sys.argv[3]
d='maps' if su=='ladder' else su
stems=sorted(os.path.basename(p)[:-7] for p in glob.glob(d+'/*.map26a'))
json.dump({'schema':1,'opponent_index':1,'maps':{s:{'seed':1310000+k,'salt':k,'unmetered':True} for s in stems}},open(out,'w'))
PY
    python3 tools/ab.py $B $BODY --no-test-draft --suites $SU --name $n --keep-replays 0 --experiment-config $cfg --game-timeout 600 > $M/logs/$n.log 2>&1
  else
    python3 tools/ab.py $B $BODY --no-test-draft --suites $SU --name $n --keep-replays 0 > $M/logs/$n.log 2>&1
  fi
  echo "exit $?" >> $M/logs/$n.log
done
touch $M/logs/calib-$bn-$on-$sn-$K0-$K1.done
