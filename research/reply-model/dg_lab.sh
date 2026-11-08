#!/bin/bash
# dg_lab.sh NAME... : PLAN2 phase-2 paired lab arms on val10k (H 30, real fuel), base lab-dg-base (ocean 7fc160d6d).
# Each lab-NAME plays cA (vs base), cB (base vs it), aA (vs lab astraeus), aB (astraeus vs it), into
# replays/combatlab/dg/NAME-*.jsonl; NAME "base" plays bb, aA and aB. Then the paired score and our side's fuel.
cd /home/ubuntu/cambc-autumn
dir=replays/combatlab/dg; mkdir -p $dir
fr=replays/combatlab/reply/frames/val10k.jsonl
base=bots/variants/lab-dg-base; as=bots/variants/lab-astraeus-8c0343f
export FASTRUNNER_LIB=$PWD/tools/fastengine/runner/target-reply/hit/libfastrunner.so FASTRUNNER_ENGINE=wasm FASTRUNNER_MODE=native
run() { tools/fastengine/runner/fastrunner scenario $fr --bot-a $1 --bot-b $2 --rollouts 1 --rounds 30 --out $3.jsonl --lab --hitlog --turns \
  --marks 5,10,30 --jobs 80 --slot-dir .git/cambc-slots --slots 86 > $3.log 2>&1; }
for n in "$@"; do
  if [ "$n" = base ]; then run $base $base $dir/base-bb; run $base $as $dir/base-aA; run $as $base $dir/base-aB; continue; fi
  c=bots/variants/lab-$n
  run $c $base $dir/$n-cA; run $base $c $dir/$n-cB; run $c $as $dir/$n-aA; run $as $c $dir/$n-aB
  echo "=== $n"
  python3 research/reply-model/score.py $fr $dir/$n-cA.jsonl $dir/base-bb.jsonl 0 $dir/$n-cB.jsonl $dir/base-bb.jsonl 1 \
    $dir/$n-aA.jsonl $dir/base-aA.jsonl 0 $dir/$n-aB.jsonl $dir/base-aB.jsonl 1
  python3 research/reply-model/fuel.py $dir/$n-cA.jsonl 0 $dir/$n-cB.jsonl 1 $dir/$n-aA.jsonl 0 $dir/$n-aB.jsonl 1
done
echo allfinished
