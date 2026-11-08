#!/bin/bash
# Sequential rerun queue. Jobs: NAME TYPE CAND BASE SEED  (TYPE common|rare)
source /home/ubuntu/venv/bin/activate
cd /home/ubuntu/cambc-autumn
A=/home/ubuntu/tmp-offload/audit
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
log() { echo "$(date +%m-%d_%H:%M) $*" >> $A/driver.log; }
janitor() { while true; do find replays -maxdepth 2 -path 'replays/batch-*-ab-audit-*' -name '*.repl26a' -mmin +8 -delete 2>/dev/null; sleep 240; done; }
janitor & JPID=$!
trap "kill $JPID" EXIT
held() { # NAME CAND BASE
  py tools/ab.py $2 $3 --no-test-draft --suites maps/suites/merged/audit-p2a --name audit-$1-held > $A/$1-held.out 2>&1
  log "$1 HELD $(python3 -c "import json;s=json.load(open('replays/ab/audit-$1-held/summary.json'));print(s['games'],s['cand_win_pct'],s['ci95'])")"
}
while read -r NAME TYPE CAND BASE SEED; do
  [ -z "$NAME" ] && continue; [[ "$NAME" == \#* ]] && continue
  [ -f $A/$NAME.done ] && continue
  log "$NAME start $TYPE $CAND vs $BASE"
  if [ "$TYPE" = common ]; then
    py tools/ab.py $CAND $BASE --no-test-draft --fuel 200000 --suites maps/suites/merged/audit-p1 --sprt 0.50,0.5025 --sprt-seed $SEED --sprt-min-games 20000 --name audit-$NAME > $A/$NAME.out 2>&1
    R=$(python3 -c "import json;s=json.load(open('replays/ab/audit-$NAME/summary.json'));p=s['sprt'];print(s['games'],s['cand_win_pct'],s['ci95'],p.get('outcome'),p['llr'],'early',s['early_losses'])" 2>&1)
    log "$NAME SPRT $R"
    if echo "$R" | grep -q " H1 "; then held $NAME $CAND $BASE; fi
  else
    MIR=$BASE-mirror
    [ -d bots/$MIR ] || ./copybot $BASE $MIR >> $A/driver.log 2>&1
    for c in $(seq 1 24); do
      [ -d replays/ab/audit-mir-$(basename $BASE)-r$c ] || py tools/ab.py $MIR $BASE --no-test-draft --fuel 200000 --suites maps/suites/merged/audit-r$c --name audit-mir-$(basename $BASE)-r$c > $A/mir-$(basename $BASE)-r$c.out 2>&1
      py tools/ab.py $CAND $BASE --no-test-draft --fuel 200000 --suites maps/suites/merged/audit-r$c --name audit-$NAME-r$c > $A/$NAME-r$c.out 2>&1
      R=$(python3 $A/paired.py --cand replays/batch-*-ab-audit-$NAME-r*-audit-r* --mirror replays/batch-*-ab-audit-mir-$(basename $BASE)-r*-audit-r* 2>&1)
      log "$NAME paired after $c chunks: $R"
      echo "$R" > $A/$NAME.paired.json
      D=$(python3 -c "import json;r=json.load(open('$A/$NAME.paired.json'));lo,hi=r['ci95_pts'];print('H1' if lo>0 else 'LOSS' if hi<0 else 'NULL' if hi<0.1 else '')" 2>/dev/null)
      if [ -n "$D" ]; then log "$NAME paired decision $D"; [ "$D" = H1 ] && held $NAME $CAND $BASE; break; fi
    done
  fi
  touch $A/$NAME.done
done < $A/queue.txt
log "queue finished"
touch $A/driver.finished
