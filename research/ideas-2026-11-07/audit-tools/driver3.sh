#!/bin/bash
# Real-budget SPRT 0.50/0.5025 on unused pool audit-p3 (793001-793600), min 40,960 games.
source /home/ubuntu/venv/bin/activate
cd /home/ubuntu/cambc-autumn
A=/home/ubuntu/tmp-offload/audit
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
log() { echo "$(date +%m-%d_%H:%M) $*" >> $A/driver3.log; }
for r in 793001-793100 793101-793200 793201-793300 793301-793400 793401-793500 793501-793600; do
  node tools/mapgen/mapgen.mjs suite --seed $r --out 'maps/suites/fresh/fresh-{seed}' > $A/gen-$r.log 2>&1
done
M=$PWD/maps/suites/merged; rm -rf $M/audit-p3; mkdir -p $M/audit-p3
( cd $M/audit-p3 && for s in $(seq 793001 793600); do ln -s ../../fresh/fresh-$s/*.map26a . ; done )
log "p3 maps $(ls $M/audit-p3 | wc -l), broken $(find -L $M/audit-p3 -type l | wc -l)"
( while true; do find replays -maxdepth 2 -path 'replays/batch-*-ab-audit3-*' -name '*.repl26a' -mmin +8 -delete 2>/dev/null; sleep 240; done ) & JPID=$!
trap "kill $JPID" EXIT
while read -r NAME CAND BASE SEED; do
  [ -z "$NAME" ] && continue; [ -f $A/$NAME.done3 ] && continue
  log "$NAME start $CAND vs $BASE"
  py tools/ab.py $CAND $BASE --no-test-draft --suites maps/suites/merged/audit-p3 --sprt 0.50,0.5025 --sprt-seed $SEED --sprt-min-games 40960 --name audit3-$NAME > $A/$NAME.out3 2>&1
  log "$NAME REAL $(python3 -c "import json;s=json.load(open('replays/ab/audit3-$NAME/summary.json'));p=s['sprt'];print(s['games'],s['cand_win_pct'],s['ci95'],p.get('outcome'),p['llr'],'oof',s['oof'],'early',s['early_losses'])" 2>&1)"
  touch $A/$NAME.done3
done < $A/queue3.txt
log "queue3 finished"; touch $A/driver3.finished
