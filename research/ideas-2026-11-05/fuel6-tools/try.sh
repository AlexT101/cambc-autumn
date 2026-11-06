#!/bin/bash
# try.sh NAME [MODES]: bench bots/variants/oc-f6-NAME vs oc-fuel4 (default modes: wide pool real poolreal), then an.py
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
n=$1; shift; modes=${*:-wide pool real poolreal}
replays/fuel/ocfuel6/bench.sh variants/oc-f6-$n $n $modes
python3 research/ideas-2026-11-05/fuel6-tools/an.py $n
