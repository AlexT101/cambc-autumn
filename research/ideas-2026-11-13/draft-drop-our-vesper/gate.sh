#!/bin/bash
# gate.sh CAND FUEL FIRST N [extra fgate args] -> ~/tmp-offload/ddov/g-CAND-FUEL-FIRST.log, done-file .done
# fgate pool v4 against fr8-g25 (Fish r8 body) and mf-f9 (Mite body), REF variants/chy-525.
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
export CAMBC_SLOTS=86
C=$1; F=$2; J=$3; N=$4; shift 4
L=~/tmp-offload/ddov/g-$C-$F-$J
FA=""; [ "$F" != "100000" ] && FA="--fuel $F"
python tools/fgate.py variants/$C variants/chy-525 --pool v4 --fish-body fr8-g25 --mite-body mf-f9 $FA --first-batch $J --max-batches $N --ci 0 "$@" > $L.log 2>&1
echo $? > $L.done
