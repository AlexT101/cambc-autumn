"""Verify the sealed Skirmish policy and full498 base, then run one matched fuel condition."""
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
p.add_argument('arm', choices=['oc-skirmish5-498'])
p.add_argument('--jobs', type=int, default=4)
a = p.parse_args()
expected = json.loads((T/'sources.json').read_text())
for name in (a.arm, 'oc-campsh-498'):
    root = R/'bots/variants'/name/'src'
    rows = [(str(p.relative_to(root)),hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(root.rglob('*')) if p.is_file()]
    actual = hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()
    if actual != expected[name]: sys.exit(f'{name}: frozen source changed ({actual})')
cmd = [sys.executable, str(R/'research/ideas-2026-11-09/freshgate-tools/fgate.py'), 'variants/'+a.arm, 'variants/oc-campsh-498', '--fish-body','Flp4','--mite-body','Mt3q','--jobs',str(a.jobs),'--seed','311']
env = dict(os.environ,CAMBC_BIN=str(R/'tools/fastengine/runner/fastrunner'),FASTRUNNER_MODE='native')
os.chdir(R)
os.execve(sys.executable,cmd,env)
