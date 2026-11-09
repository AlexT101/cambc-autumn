#!/bin/bash
# soup-k (v87-soupk = oc-base25 + CHANGES 471's constants) against old and new bodies: block 0, then noise seeds.
T=/home/ubuntu/cambc-autumn/research/ideas-2026-11-09/oppfidelity-tools
$T/runs.sh sk variants/v87-soupk spar-o25-F spar-o25-M spar-oc29-F spar-oc29-M spar-o25-Fl spar-o25-Mt3 spar-oc29-Fl spar-oc29-Mt3
for k in $(seq 1 16); do $T/runs.sh sk variants/v87-soupk spar-dvn$k-F spar-dvn$k-M spar-dvn$k-Fl spar-dvn$k-Mt3; done
touch ~/tmp-offload/oppfidelity/logs/sk.alldone
