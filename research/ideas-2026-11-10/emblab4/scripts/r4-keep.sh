#!/bin/bash
# A slot keeper (tools/emblab/slot_keeper.py) for lab $1's run process, once it starts.
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
until P=$(pgrep -f "^python3 tools/emblab/lab.py run --lab $1 " | head -1) && [ -n "$P" ]; do sleep 2; done
echo "keeper for job-$P ($(ps -o args= -p $P | cut -c1-60))"
CAMBC_SLOTS=86 python3 tools/emblab/slot_keeper.py job-$P 35 $P
