#!/bin/bash
# runstats.sh RUN...: decode an ab.py run's replays (replays/batch-*-ab-RUN-*) into ~/tmp-offload/mitefit/ext/RUN and
# write its per-game stats to ~/tmp-offload/mitefit/stats/RUN.jsonl (mstats.py local); then delete the raw replays.
R=/home/ubuntu/cambc-autumn; M=/home/ubuntu/tmp-offload/mitefit; cd $R; mkdir -p $M/ext $M/stats
for RUN in "$@"; do
  [ -f $M/stats/$RUN.jsonl ] && continue
  DIRS=$(ls -d replays/batch-*-ab-$RUN-* 2>/dev/null)
  python3 tools/pooled.py 12 -- node tools/replay/extract.mjs $DIRS --out $M/ext/$RUN --threads 12 > $M/logs/ext-$RUN.log 2>&1
  python3 tools/pooled.py 8 -- python3 research/ideas-2026-11-12/mitefit/mstats.py local $M/ext/$RUN $M/stats/$RUN.jsonl >> $M/logs/ext-$RUN.log 2>&1
done
