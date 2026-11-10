"""Verify the sealed ward arm and full498 base, then run one matched fuel condition."""
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
p.add_argument('arm', choices=['oc-wtile-498','oc-wbush-498','oc-wcamp-498','oc-wcampall-498','oc-wlate-498'])
p.add_argument('--fuel', type=int, choices=[100000,200000], default=100000)
p.add_argument('--jobs', type=int, default=4)
p.add_argument('--check', action='store_true')
p.add_argument('--screen-admission', type=Path, help='explicit admission of normal wlate after a positive audited200k screen')
a = p.parse_args()
expected = json.loads((T/'sources.json').read_text())
for name in (a.arm, 'oc-campsh-498'):
    root = R/'bots/variants'/name/'src'
    rows = [(str(p.relative_to(root)),hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(root.rglob('*')) if p.is_file()]
    actual = hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()
    if actual != expected[name]: sys.exit(f'{name}: frozen source changed ({actual})')
cmd = [sys.executable, str(R/'research/ideas-2026-11-09/freshgate-tools/fgate.py'), 'variants/'+a.arm, 'variants/oc-campsh-498', '--fish-body','Flp4','--mite-body','Mt3q','--jobs',str(a.jobs)]
if a.fuel != 100000: cmd += ['--fuel',str(a.fuel)]
if a.arm == 'oc-wlate-498':
    if a.fuel == 200000:
        # Bounded behavioral screen; no extension or normal-fuel run follows automatically.
        cmd += ['--max-seeds', '8', '--ci', '0', '--ahead', '0']
    else:
        if not a.screen_admission:
            sys.exit('wlate100k is held: positive audited200k screen and explicit admission required')
        admission = json.loads(a.screen_admission.read_text())
        proof_path = Path(admission['screen_proof'])
        raw = proof_path.read_bytes()
        if admission.get('authorized_by') != 'coordinator' or hashlib.sha256(raw).hexdigest() != admission.get('screen_sha256'):
            sys.exit('wlate100k: invalid explicit screen admission')
        proof = json.loads(raw)
        if not (proof.get('decision') == 'positive' and 1 <= proof.get('complete_blocks', 0) <= 8
                and proof.get('valid_terminal_stop') is True
                and proof.get('validated_cells') is True and proof.get('fuel') == 200000
                and proof.get('fresh_lower_pp', -1) > 0
                and proof.get('sources') == {name: expected[name] for name in (a.arm, 'oc-campsh-498')}):
            sys.exit('wlate100k: screen does not establish a valid positive fresh-map gain')
if a.check:
    print(json.dumps({'argv': cmd, 'sources': {name: expected[name] for name in (a.arm, 'oc-campsh-498')}}))
    sys.exit(0)
env = dict(os.environ,CAMBC_BIN=str(R/'tools/fastengine/runner/fastrunner'),FASTRUNNER_MODE='native')
os.chdir(R)
os.execve(sys.executable,cmd,env)
