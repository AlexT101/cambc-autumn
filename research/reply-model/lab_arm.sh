#!/bin/bash
# lab_arm.sh LABBOT OUTPREFIX FRAMES [base]: paired-lab runs. A candidate plays cA (vs base), cB (base vs it),
# aA (vs astraeus), aB (astraeus vs it); with "base" the base arm: bb, aA, aB.
set -e
cd /home/ubuntu/cambc-autumn
c=bots/variants/$1; out=$2; fr=$3; mode=$4; shift 4 || shift $#; extra="$@"
base=bots/variants/lab-rd-base; as=bots/variants/lab-astraeus-8c0343f
export FASTRUNNER_LIB=$PWD/tools/fastengine/runner/target-reply/hit/libfastrunner.so FASTRUNNER_ENGINE=wasm FASTRUNNER_MODE=native
run() { tools/fastengine/runner/fastrunner scenario $fr --bot-a $1 --bot-b $2 --rollouts 1 --rounds 30 --out $3.jsonl --lab --hitlog --turns \
  --marks 5,10,30 --jobs 80 --slot-dir .git/cambc-slots --slots 86 $extra > $3.log 2>&1; }
if [ "$mode" = base ]; then run $c $c $out-bb; else run $c $base $out-cA; run $base $c $out-cB; fi
run $c $as $out-aA; run $as $c $out-aB
echo finished
