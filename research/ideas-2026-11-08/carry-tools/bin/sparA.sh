#!/bin/bash
# Fidelity (oc-base27 vs spar-<body>-F/M, debug, replays kept) and spar_ab cand runs (debug, as spar-cbase29-* refs).
# sparA.sh CANDDIR BODYTAG
B=/home/ubuntu/tmp-offload/carry/bin; L=/home/ubuntu/tmp-offload/carry/logs; C=$1; T=$2
cd /home/ubuntu/cambc-autumn; S=research/ideas-2026-11-08/spar-tools
$S/makespar.sh variants/$C $T > $L/makespar-$T.log 2>&1
THR=43 $B/ab.sh spar-c27-${T}F oc-base27 spar-$T-F ladder --debug --keep-replays 0 & p1=$!
THR=43 $B/ab.sh spar-c27-${T}M oc-base27 spar-$T-M ladder --debug --keep-replays 0 & p2=$!
wait $p1 $p2
source /home/ubuntu/venv/bin/activate
ls -d replays/batch-*-ab-spar-c27-${T}[FM]-ladder > $L/fid-$T.batches
node tools/replay/extract.mjs $(cat $L/fid-$T.batches) --threads 16 --out /home/ubuntu/tmp-offload/carry/ana-$T > $L/extract-$T.log 2>&1
touch $L/fid-$T.done
for b in oc29 $(seq -f 'j%g' 1 12); do
  bb=$b; [ $b = oc29 ] && bb=o29
  for o in F M; do
    THR=43 $B/ab.sh spar-c$C-$bb$o $C spar-$b-$o ladder --debug --keep-replays 1 &
  done
  wait
done
python3 $S/spar_ab.py variants/$C variants/oc-base29 --no-run > $L/spar-ab-$C.txt 2>&1
touch $L/sparA-$C.done
