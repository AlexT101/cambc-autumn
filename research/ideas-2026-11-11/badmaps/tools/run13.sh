#!/bin/bash
# Dear-fall arms: phase 1 mechanism batch with replays (1,024 fresh maps), phase 2 fresh half A (5,120 maps), both at 200k.
cd /home/ubuntu/cambc-autumn
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
B=/home/ubuntu/tmp-offload/badmaps; L=$B/logs13; M=$B/maps11/merged-m
mkdir -p $L $B/extm
if [ ! -d $M ]; then mkdir -p $M; for s in 1212020 1212021 1212022 1212023; do for f in $B/maps11/fresh-$s/*.map26a; do ln -s $f $M/; done; done; fi
ARMS="bm-ps bm-psr bm-pr-p"
CANDS="bm-ps bm-psr bm-pr-p"
for C in $ARMS; do for O in Mt3q Flp4; do
  N=bm12-mech-$C-$O
  python3 tools/ab.py variants/$C variants/spar-dvn1-$O --no-test-draft --suites $M --name $N --fuel 200000 --keep-replays 0 > $L/$N.log 2>&1
done; done
(
  for C in $ARMS; do
    node tools/replay/extract.mjs replays/batch-*-ab-bm12-mech-$C-Mt3q-* replays/batch-*-ab-bm12-mech-$C-Flp4-* --threads 24 --out $B/extm/$C > $L/ext-$C.log 2>&1
  done
  node tools/replay/extract.mjs replays/batch-*-ab-bm12-mech-oc-dfuel-506-Mt3q-* replays/batch-*-ab-bm12-mech-oc-dfuel-506-Flp4-* --threads 24 --out $B/extm/base-full > $L/ext-base-full.log 2>&1
  python3 $B/an/prism3.py $B/extm base-full $ARMS > $L/mech.txt 2>&1
  touch $L/mech.done
) &
for C in $CANDS; do for O in Mt3q Flp4; do
  N=bm11-f200a-$C-$O
  python3 tools/ab.py variants/$C variants/spar-dvn1-$O --no-test-draft --suites $B/maps11/merged-a --name $N --fuel 200000 --keep-replays 1 > $L/$N.log 2>&1
done; done
touch $L/f200a.done
wait
touch $L/all.done
