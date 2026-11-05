#!/bin/bash
# cmp.sh BASE TAG: bench.py compare of replays/fuel/mk/BASE-* and TAG-* (default, wide, fresh)
cd "$(dirname "$0")/../.."
source /home/ubuntu/venv/bin/activate
for s in default wide fresh; do echo "== $s"; python tools/fuel/bench.py compare replays/fuel/mk/$1-$s.json replays/fuel/mk/$2-$s.json 2>&1 | head -14; done
