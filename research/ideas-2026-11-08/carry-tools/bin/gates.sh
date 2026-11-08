#!/bin/bash
# gates.sh CAND : CAND (and CAND-td) against oc-base29 on own panel and varied suites (release builds).
B=/home/ubuntu/tmp-offload/carry/bin; L=/home/ubuntu/tmp-offload/carry/logs; C=$1
cd /home/ubuntu/cambc-autumn
if [ ! -e $L/maps.done ]; then
  $B/mkmaps.sh 1220000 1220039 --mix ladder-v2 && $B/merge.sh cr-panel-122 1220000 1220039 > $L/merge-panel.log || { touch $L/gates-$C.died; exit 1; }
  $B/mkmaps.sh 1220100 1220139 --mix varied && $B/merge.sh cr-varied-122 1220100 1220139 > $L/merge-varied.log || { touch $L/gates-$C.died; exit 1; }
  touch $L/maps.done
fi
M=maps/suites/merged
THR=20 $B/ab.sh vr-$C $C oc-base29 $M/cr-varied-122 --sprt 0.4975,0.50 --sprt-min-games 2000 --sprt-seed 1220001 & V=$!
pp=()
for r in "$C-dir $C-td oc-base29-td" "$C-ast $C-td gp-panel-astraeus-td" "b29-ast oc-base29-td gp-panel-astraeus-td" \
         "$C-pro $C-td gp-panel-proteus-td" "b29-pro oc-base29-td gp-panel-proteus-td"; do
  set -- $r
  if [ -e /home/ubuntu/cambc-autumn/replays/ab/pn-$1/summary.json ]; then continue; fi
  THR=20 $B/ab.sh pn-$1 $2 $3 $M/cr-panel-122 & pp+=($!)
  if [ ${#pp[@]} -ge 2 ]; then wait ${pp[0]}; pp=("${pp[@]:1}"); fi
done
wait "${pp[@]}" $V
source /home/ubuntu/venv/bin/activate
T=research/ideas-2026-11-08/tune3-tools/panel_sprt.py
python3 $T --p0 0.4975 --p1 0.50 --seed 1220003 --direct pn-$C-dir --paired pn-$C-ast:pn-b29-ast --paired pn-$C-pro:pn-b29-pro > $L/panel-nn-$C.txt 2>&1
python3 $T --p0 0.50 --p1 0.5025 --seed 1220003 --direct pn-$C-dir --paired pn-$C-ast:pn-b29-ast --paired pn-$C-pro:pn-b29-pro > $L/panel-h1-$C.txt 2>&1
touch $L/gates-$C.done
