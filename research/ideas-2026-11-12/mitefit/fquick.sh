#!/bin/bash
# fquick.sh BODY...: the v116 k1 run only (charybdis-p3 against BODY, 256 ladder games), then fight/Vesper/macro stats.
R=/home/ubuntu/cambc-autumn; M=/home/ubuntu/tmp-offload/mitefit; F=$R/research/ideas-2026-11-12/mitefit; cd $R; source /home/ubuntu/venv/bin/activate
for B in "$@"; do
  ( $F/calib.sh variants/charybdis-p3 variants/$B 1 1; RUN=mf-charybdis-p3-$B-ladder-k1; $F/runstats.sh $RUN
    python3 tools/pooled.py 8 -- python3 $F/fstats.py local $M/ext/$RUN $M/fstats/$B.jsonl
    python3 tools/pooled.py 8 -- python3 $F/vstats.py local $M/ext/$RUN $M/vstats/$B.jsonl ) &
done; wait
touch $M/logs/fquick-${!#}.done
