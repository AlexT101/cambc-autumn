#!/bin/bash
T=/home/ubuntu/cambc-autumn/research/ideas-2026-11-05/fuelbud-tools
for f in loopbank loopnobank b125 b150; do
  $T/ab.sh variants/oc-fb-gv-$f variants/oc-fb-cap fb-gv-$f fuelbud-oracle --fuel 10000000 &
done
wait
