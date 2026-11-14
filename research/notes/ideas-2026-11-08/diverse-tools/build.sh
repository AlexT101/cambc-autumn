#!/bin/bash
# Rebuild the diverse-panel bodies (bots/variants is gitignored), from bots/variants/oc-tune3 (oc-base25 tunified):
#   dvp-{oc6,anti6,agg,pas,greed} and their -td copies, noise bodies dvp-n1..nN (seeds 1310001..), and the live-draft
#   copies spar-dv<body>-{F,M} the gate plays.      research/notes/ideas-2026-11-08/diverse-tools/build.sh [N=8]
cd /home/ubuntu/cambc-autumn; T=research/notes/ideas-2026-11-08; N=${1:-8}
python3 $T/diverse-tools/bodies.py oc6 anti6 agg pas greed $(for i in $(seq 1 $N); do echo n$((1310000 + i)); done)
for b in oc6 anti6 agg pas greed; do
  ./tools/copybot -f variants/dvp-$b variants/dvp-$b-td >/dev/null
  sed -i 's/^constexpr bool test_draft = false;/constexpr bool test_draft = true;/' bots/variants/dvp-$b-td/src/params.h
done
for b in oc6 anti6 agg pas greed $(for i in $(seq 1 $N); do echo n$i; done); do $T/spar-tools/makespar.sh variants/dvp-$b dv$b; done
