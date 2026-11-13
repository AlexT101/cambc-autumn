#!/bin/bash
set -euo pipefail
cd /home/ubuntu/wt/fuel-530
node tools/mapgen/mapgen.mjs suite --out 'maps/suites/f530-final/{seed}' --seed 61496020-61496049 --mix ladder-v4 --jobs 16 > research/fuel-530/results/mapgen-final.log 2>&1
python3 - <<'PY'
from pathlib import Path
p=Path('maps/suites/f530-final')
for d in sorted(p.iterdir()):
 if d.is_dir():
  for f in sorted(d.glob('*.map26a')): f.rename(p/f.name)
files=sorted(p.glob('*.map26a'))
small=[str(f) for f in files if any(f'-{seed}' in f.name for seed in range(61496020,61496026))]
assert len(files)==10200 and len(small)==2040, (len(files),len(small))
Path('research/fuel-530/maps-final.txt').write_text(''.join(f+'\n' for f in small))
Path('research/fuel-530/maps-final-release.txt').write_text(''.join(str(f)+'\n' for f in files))
PY
