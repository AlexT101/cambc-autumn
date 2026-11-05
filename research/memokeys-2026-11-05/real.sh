#!/bin/bash
# real.sh BOT TAG [MAPSFILE]: bench.py at the real budget vs astraeus-5b66bde on the maps listed (default fresh64.txt) into replays/fuel/mk/TAG
cd "$(dirname "$0")/../.."
source /home/ubuntu/venv/bin/activate
export PATH=$HOME/.cargo/bin:$PATH CAMBC_SLOTS=86 CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
out=$PWD/replays/fuel/mk
maps=${3:-research/memokeys-2026-11-05/fresh64.txt}
python tools/fuel/bench.py run "$1" --fuel 0 --opp variants/astraeus-5b66bde --maps $(cat $maps) --games $out/$2 --out $out/$2.json 2>&1 | tail -2
