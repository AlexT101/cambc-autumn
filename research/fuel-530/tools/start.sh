#!/bin/bash
set -euo pipefail
cd /home/ubuntu/wt/fuel-530
node tools/mapgen/mapgen.mjs suite --out 'maps/suites/f530-dev/{seed}' --seed 61496000-61496001 --mix ladder-v4 --jobs 16 > research/fuel-530/results/mapgen-dev.log 2>&1
python3 - <<'PY'
from pathlib import Path
p=Path('maps/suites/f530-dev')
for f in p.glob('*/*.map26a'): f.rename(p/f.name)
Path('research/fuel-530/maps-dev.txt').write_text(''.join(str(f)+'\n' for f in sorted(p.glob('*.map26a'))))
PY
bash research/fuel-530/tools/bench.sh variants/chy-530 base-dev dev --fuel 0
