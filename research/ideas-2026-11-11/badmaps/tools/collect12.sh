#!/bin/bash
# waits for the chain (PID $1) then prints the mechanism table and the paired fresh-A results
L=/home/ubuntu/tmp-offload/badmaps/logs12; R=/home/ubuntu/cambc-autumn/replays
until [ -f $L/all.done ] || ! kill -0 $1 2>/dev/null; do sleep 20; done
[ -f $L/all.done ] || echo "CHAIN DIED before all.done"
cat $L/mech.txt | cut -c1-260
cd $R
for C in bm-pf-a bm-pf-b bm-pr bm-pfr bm-pfr-p; do for O in Mt3q Flp4; do
  [ -e ab/bm11-f200a-$C-$C-$O ] || ln -s bm11-f200a-$C-$O ab/bm11-f200a-$C-$C-$O
  for b in batch-*-ab-bm11-f200a-$C-$O-merged-a; do n=${b/bm11-f200a-$C-$O/bm11-f200a-$C-$C-$O}; [ -e $n ] || ln -s $b $n; done
done; done
cd /home/ubuntu/tmp-offload/badmaps/an
for C in bm-pf-a bm-pf-b bm-pr bm-pfr bm-pfr-p; do python3 paired.py f200a $C oc-dfuel-506 2>&1 | tail -4; done
grep -h 'Out-of-fuel' $L/bm11-f200a-*.log | cut -c1-120
