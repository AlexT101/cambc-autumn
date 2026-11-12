#!/bin/bash
# calrun.sh K0 K1 BODY...: calibrate bodies against v115-v118 (oc-dfuel-506, charybdis-p3, c520-ps, lab-emb6-c520-ps)
# on the 168 ranked maps (ladder-all), members K0..K1. Done-file ~/tmp-offload/fishr8/logs/calrun-<last body>.done.
F=/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/fishr8; K0=$1; K1=$2; shift 2
for B in "$@"; do
  for O in oc-dfuel-506 charybdis-p3 c520-ps lab-emb6-c520-ps; do $F/calib.sh variants/$O variants/$B $K0 $K1 ladder-all & done; wait
done
touch /home/ubuntu/tmp-offload/fishr8/logs/calrun-${!#}.done
