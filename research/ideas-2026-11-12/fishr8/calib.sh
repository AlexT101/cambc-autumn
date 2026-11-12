#!/bin/bash
# calib.sh BOT BODY K0 K1 [SUITE]: mitefit/calib.sh with fishr8 paths: BOT (ours, metered 100k) against a body on
# maps/ (the 168 ranked maps; or SUITE), both sides, noise members K0..K1 (seed 1310000+k, salt k). Runs are
# replays/ab/fr-<bot>-<body>-<suite>-k<k>; done-file logs/calib-<bot>-<body>-<suite>-K0-K1.done.
B=$1; BODY=$2; K0=$3; K1=$4; SU=${5:-ladder}
R=/home/ubuntu/cambc-autumn; M=/home/ubuntu/tmp-offload/fishr8; cd $R
export CAMBC_BIN=$R/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native FGATE_RUNNER_LIB=$R/tools/fastengine/runner/target-rt/release/libfastrunner.so
export FASTRUNNER_LIB=$FGATE_RUNNER_LIB
bn=$(basename $B); on=$(basename $BODY); sn=$(basename $SU)
rt=0; grep -qs import_module bots/$BODY/src/experiment_config.h && rt=1
for k in $(seq $K0 $K1); do
  n=fr-$bn-$on-$sn-k$k
  [ -f replays/ab/$n/summary.json ] && continue
  if [ $rt = 1 ]; then
    cfg=$M/cfg/$sn-k$k.json
    [ -f $cfg ] || python3 - "$SU" $k $cfg <<'PY'
import json,sys,os,glob
su,k,out=sys.argv[1],int(sys.argv[2]),sys.argv[3]
d='maps' if su in ('ladder','ladder-all') else su
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
