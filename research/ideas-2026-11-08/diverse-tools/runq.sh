#!/bin/bash
# runq.sh QUEUE DONEFILE : play one queue of diverse-panel calibration runs (ladder suite, both sides, cand own draft
# unless its -td copy), skipping runs whose summary.json exists. QUEUE: noise | tune | td.
cd /home/ubuntu/cambc-autumn; source /home/ubuntu/venv/bin/activate
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
q=$1; done=$2; L=~/tmp-offload/diverse/logs; mkdir -p $L
VERS=${VERS:-"base23 base29 base27 s2-soupk27 base25 base26"}
run() {  # cand member name
  [ -f replays/ab/$3/summary.json ] && return
  python3 tools/ab.py variants/$1 variants/$2 --no-test-draft --suites ladder --name $3 --keep-replays 1 > $L/$3.log 2>&1 \
    || echo "FAIL $3" >> $L/failures
}
for v in $VERS; do
  c=oc-$v
  case $q in
    noise) for b in ${NOISE:-dvn1 dvn2 dvn3 dvn4}; do for o in F M; do run $c spar-$b-$o spar-c$v-$b$o; done; done ;;
    tune)  for b in dvoc6 dvanti6 dvagg dvpas dvgreed; do for o in F M; do run $c spar-$b-$o spar-c$v-$b$o; done; done ;;
    td)    for b in oc6 anti6 agg pas greed; do run $c dvp-$b-td dvp-c$v-${b}td; done
           for p in astraeus proteus; do run $c-td gp-panel-$p-td dvp-c${v}td-gp$p; done ;;
  esac
done
touch $done
