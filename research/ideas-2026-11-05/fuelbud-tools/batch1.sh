#!/bin/bash
T=/home/ubuntu/cambc-autumn/research/ideas-2026-11-05/fuelbud-tools
for v in p1 p2 g1 s1 s2 r1 r2; do
  $T/ab.sh variants/oc-fb-$v variants/oc-retest-clean fb-$v fuelbud-dev --sprt 0.50,0.51 &
done
wait
