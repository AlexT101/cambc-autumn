#!/bin/bash
# noise.sh TAG:DIR... -- SEEDS : each bot against spar-dvn<k>-Mt2 and -Fl for each seed, 2 seeds at a time.
T=/home/ubuntu/cambc-autumn/research/notes/ideas-2026-11-09/oppfidelity-tools
bots=(); while [ "$1" != "--" ]; do bots+=("$1"); shift; done; shift
set -- "$@"
while [ $# -gt 0 ]; do
  ms=""; for k in $1 $2; do ms="$ms spar-dvn$k-Mt3 spar-dvn$k-Fl"; done; shift 2 2>/dev/null || shift
  for b in "${bots[@]}"; do $T/runs.sh ${b%%:*} ${b#*:} $ms & done; wait
done
touch ~/tmp-offload/oppfidelity/logs/noise-$(echo ${bots[@]} | md5sum | cut -c1-8).alldone
