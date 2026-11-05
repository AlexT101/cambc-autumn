#!/bin/bash
# ml.sh BOT TAG [FUEL]: bench.py vs astraeus-5b66bde on fresh64 at FUEL (0: the real budget; default 100M) into replays/fuel/mk/TAG
cd "$(dirname "$0")/../.."
source /home/ubuntu/venv/bin/activate
export PATH=$HOME/.cargo/bin:$PATH CAMBC_SLOTS=86 CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
out=$PWD/replays/fuel/mk
fuel=()
[ -n "$3" ] && fuel=(--fuel "$3")
python tools/fuel/bench.py run "$1" "${fuel[@]}" --opp variants/astraeus-5b66bde --maps $(cat research/memokeys-2026-11-05/fresh64.txt) --games $out/$2 --out $out/$2.json 2>&1 | tail -2
