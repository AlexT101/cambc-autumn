#!/bin/bash
# panel.sh CAND TAG: CAND against the five panel members on panel-check-514510 (5,120 games each), in parallel.
cd /home/ubuntu/cambc-autumn/research/ideas-2026-11-05/fuelbud-tools
C=$1 T=$2
for m in variants/astraeus-now-1106:astraeus1106 variants/panel-proteus:proteus variants/panel-demeter:demeter variants/panel-ocean-td:ocean-td baselines/v67:v67; do
  ./ab.sh $C ${m%%:*} pchk-$T-vs-${m##*:} panel-check-514510 &
done
wait
