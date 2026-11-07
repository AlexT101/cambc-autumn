#!/bin/bash
# Touch replays/tune/R/STOP once R's state has reached iteration N - 2 (two batches in flight), for each R.
N=$1; shift
for r in "$@"; do
  ( until [ "$(python3 -c "import json;print(json.load(open('/home/ubuntu/cambc-autumn/replays/tune/$r/state.json'))['k'])")" -ge $((N - 2)) ]; do sleep 3; done
    touch /home/ubuntu/cambc-autumn/replays/tune/$r/STOP ) &
done
wait
