#!/bin/bash
# autolaunch2.sh SUITE NAME...: launch each NAME's SUITE A/B once its smoke summary (mac13-argo-smoke-NAME) exists.
cd /home/ubuntu/wt/mac13-argo
SUITE=$1; shift
left="$*"
while [ -n "$left" ]; do
  next=""
  for p in $left; do
    if grep -q '| ladder' replays/ab/mac13-argo-smoke-$p/summary.md 2>/dev/null; then
      sleep 20  # the agent may still be writing its patch
      research/mac13-argo/ab.sh $p $SUITE $p --keep-replays 1; echo "launched $p $(date -u +%H:%M)"
    else next="$next $p"; fi
  done
  left=$(echo $next)
  [ -n "$left" ] && sleep 20
done
