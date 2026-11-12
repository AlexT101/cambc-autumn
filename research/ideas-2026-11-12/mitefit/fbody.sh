#!/bin/bash
# fbody.sh BODY...: calibrate bodies against v115/v116/v117 (ladder, 8 members), then fight, Vesper and macro stats
# on the v116 k1 run. Done-file logs/fbody-<last body>.done.
R=/home/ubuntu/cambc-autumn; M=/home/ubuntu/tmp-offload/mitefit; F=$R/research/ideas-2026-11-12/mitefit; cd $R; source /home/ubuntu/venv/bin/activate
for B in "$@"; do
  $F/calib.sh variants/charybdis-p3 variants/$B 1 8 & $F/calib.sh variants/c520-ps variants/$B 1 8 & $F/calib.sh variants/oc-dfuel-506 variants/$B 1 8 & wait
  RUN=mf-charybdis-p3-$B-ladder-k1
  $F/runstats.sh $RUN
  python3 tools/pooled.py 8 -- python3 $F/fstats.py local $M/ext/$RUN $M/fstats/$B.jsonl
  python3 tools/pooled.py 8 -- python3 $F/vstats.py local $M/ext/$RUN $M/vstats/$B.jsonl
done
touch $M/logs/fbody-${!#}.done
