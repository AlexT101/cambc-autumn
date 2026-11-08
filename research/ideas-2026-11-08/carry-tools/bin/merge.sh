#!/bin/bash
# merge.sh NAME LO HI [mono]: symlink fresh-LO..HI maps into maps/suites/merged/NAME (mono: Monolith maps only).
cd /home/ubuntu/cambc-autumn/maps/suites
python3 - "$@" <<'PY'
import json, os, sys
name, a, b = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]); mono = len(sys.argv) > 4
od = 'merged/' + name; os.makedirs(od, exist_ok=True); n = 0
for s in range(a, b + 1):
    d = f'fresh/fresh-{s}'
    for m in json.load(open(d + '/index.json'))['maps']:
        if mono and not (m['metrics'].get('monoliths') or 0) > 0: continue
        dst = os.path.join(od, m['file'])
        if not os.path.exists(os.path.join(d, m['file'])): continue
        if not os.path.lexists(dst): os.symlink('../../fresh/' + f'fresh-{s}/' + m['file'], dst)
        n += 1
print(name, n)
PY
