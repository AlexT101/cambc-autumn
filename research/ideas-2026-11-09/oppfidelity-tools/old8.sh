#!/bin/bash
# c25 and lk600 against the old bodies (block 0, seeds 1-8) with replays kept, for op600.py's old-body reading.
T=/home/ubuntu/cambc-autumn/research/ideas-2026-11-09/oppfidelity-tools
ms="spar-o25-F spar-o25-M spar-oc29-F spar-oc29-M"; for k in $(seq 1 8); do ms="$ms spar-dvn$k-F spar-dvn$k-M"; done
$T/runs.sh c25 variants/oc-base25 $ms & $T/runs.sh lk600 variants/v87-lk-600 $ms & wait
touch ~/tmp-offload/oppfidelity/logs/old8.alldone
