#!/bin/bash
# c25, lk600 and soup-k against the -Mt4 bodies (block 0 and noise seeds 1-16).
T=/home/ubuntu/cambc-autumn/research/ideas-2026-11-09/oppfidelity-tools
ms="spar-o25-Mt4 spar-oc29-Mt4"; for k in $(seq 1 16); do ms="$ms spar-dvn$k-Mt4"; done
$T/runs.sh c25 variants/oc-base25 $ms & $T/runs.sh lk600 variants/v87-lk-600 $ms & $T/runs.sh sk variants/v87-soupk $ms & wait
touch ~/tmp-offload/oppfidelity/logs/mt4.alldone
