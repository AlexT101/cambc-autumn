#!/bin/bash
# Launch each pb2 probe's probe-suite A/B once its smoke summary exists; exits when all 10 are launched.
cd /home/ubuntu/wt/mac13-argo
while true; do
  n=0
  for d in bots/variants/pb2-*; do
    p=$(basename $d)
    if [ -f research/mac13-argo/logs/$p.log ]; then n=$((n+1)); continue; fi
    if [ -f replays/ab/mac13-argo-smoke-$p/summary.md ] && grep -q '| ladder' replays/ab/mac13-argo-smoke-$p/summary.md; then
      research/mac13-argo/ab.sh $p probe $p --keep-replays 0; echo "launched $p $(date -u +%H:%M)"; sleep 5
    fi
  done
  [ $n -ge 10 ] && break
  sleep 20
done
