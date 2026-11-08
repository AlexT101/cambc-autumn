#!/bin/bash
# arms.sh DIR FUELARGS NAME...: lab_arm.sh for each lab-NAME into replays/combatlab/reply/DIR, then the paired score
# against DIR's base arm (base-bb/aA/aB) and the fuel of our side.
cd /home/ubuntu/cambc-autumn
dir=replays/combatlab/reply/$1; fa=$2; shift 2
fr=replays/combatlab/reply/frames/val10k.jsonl
for n in "$@"; do
  research/reply-model/lab_arm.sh lab-$n $dir/$n $fr cand $fa
  echo "=== $n"
  python3 research/reply-model/score.py $fr $dir/$n-cA.jsonl $dir/base-bb.jsonl 0 $dir/$n-cB.jsonl $dir/base-bb.jsonl 1 \
    $dir/$n-aA.jsonl $dir/base-aA.jsonl 0 $dir/$n-aB.jsonl $dir/base-aB.jsonl 1 | grep -A3 pooled
  python3 research/reply-model/fuel.py $dir/$n-cA.jsonl 0 $dir/$n-aB.jsonl 1
done
echo allfinished
