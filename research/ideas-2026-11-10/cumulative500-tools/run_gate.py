"""Cancelled historical protocol; --check inspects sources without playing."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

T = Path(__file__).resolve().parent
R = T.parents[2]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('arm', choices=['oc-wakecold-500'])
p.add_argument('--jobs', type=int, default=4)
p.add_argument('--check', action='store_true', help='verify seals and print command without playing')
a = p.parse_args()
expected = json.loads((T / 'sources.json').read_text())
for name in (a.arm, 'oc-wdash-494'):
    root = R / 'bots/variants' / name / 'src'
    rows = [(str(f.relative_to(root)), hashlib.sha256(f.read_bytes()).hexdigest())
            for f in sorted(root.rglob('*')) if f.is_file()]
    actual = hashlib.sha256(json.dumps(rows, separators=(',', ':')).encode()).hexdigest()
    if actual != expected[name]:
        sys.exit(f'{name}: frozen source changed ({actual})')
cmd = [sys.executable, str(R / 'research/ideas-2026-11-09/freshgate-tools/fgate.py'),
       'variants/' + a.arm, 'variants/oc-wdash-494', '--fish-body', 'Flp4',
       '--mite-body', 'Mt3q', '--jobs', str(a.jobs), '--seed', '319']
if a.check:
    print(json.dumps({'source_seals': expected, 'argv': cmd, 'fuel': 'default100k',
                      'scope': 'whole approved500 bundle versus494; no individual attribution'}))
    sys.exit(0)
sys.exit('Cancelled by explicit user instruction; no component-strength games or replacement run.')
