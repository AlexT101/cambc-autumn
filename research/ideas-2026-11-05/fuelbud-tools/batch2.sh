#!/bin/bash
T=/home/ubuntu/cambc-autumn/research/ideas-2026-11-05/fuelbud-tools
for v in c1 c2 sp4 r1; do
  $T/ab.sh variants/oc-fb-$v variants/oc-retest-clean fb2-$v fuelbud-dev &
done
wait
