"""Cancelled historical protocol; --check inspects sources without playing."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
T = Path(__file__).resolve().parent
R = T.parents[2]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('arm', choices=['oc-rs8-498','oc-q1-498','oc-rs8q1-498'])
p.add_argument('--jobs', type=int, default=4)
p.add_argument('--check', action='store_true', help='inspect cancelled protocol only; never run games')
a = p.parse_args()
expected = json.loads((T/'sources.json').read_text())
for name in (a.arm, 'oc-campsh-498'):
    root = R/'bots/variants'/name/'src'
    rows = [(str(p.relative_to(root)),hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(root.rglob('*')) if p.is_file()]
    actual = hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()
    if actual != expected[name]: sys.exit(f'{name}: frozen source changed ({actual})')
cmd = [sys.executable, str(R/'research/ideas-2026-11-09/freshgate-tools/fgate.py'), 'variants/'+a.arm, 'variants/oc-campsh-498', '--fish-body','Flp4','--mite-body','Mt3q','--jobs',str(a.jobs)]
if a.check:
    print(json.dumps({'argv': cmd, 'sources': expected, 'status': 'cancelled by user'}))
    sys.exit(0)
sys.exit('Cancelled by explicit user instruction; no component-strength games or replacement run.')
