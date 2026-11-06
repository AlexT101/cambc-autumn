#!/usr/bin/env python3
"""mkvar.py NAME key=value ...: bots/variants/oc-cb-NAME = oc-comeback-dev with params::comeback (or late::) constants set.
Keys are names in namespace comeback (e.g. def=1 mild=hunt|items bar=1.0); `late.c=1` sets params::late."""
import os, re, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
name, kv = sys.argv[1], sys.argv[2:]
dst = f'variants/oc-cb-{name}'
subprocess.run([f'{ROOT}/copybot', '-f', 'variants/oc-comeback-dev', dst], check=True, cwd=ROOT, stdout=subprocess.DEVNULL)
p = f'{ROOT}/bots/{dst}/src/params.h'
s = open(p).read()
names = {'pull': 'pull', 'hunt': 'hunt', 'deny': 'deny', 'items': 'items', 'ambush': 'ambush', 'hop': 'hop', 'snipe': 'snipe'}
for item in kv:
    k, v = item.split('=', 1)
    ns = 'comeback'
    if '.' in k: ns, k = k.split('.', 1)
    if k in ('mild', 'deep', 'hopeless', 'all'):
        v = ' | '.join(names[x] for x in v.split('|')) if v not in ('0', '') else '0'
    i = s.index(f'namespace {ns} {{')
    j = s.index(f'}} // namespace {ns}', i)
    body = s[i:j]
    keys = ('mild', 'deep', 'hopeless') if k == 'all' else (k,)
    for key in keys:
        pat = re.compile(r'(\b' + re.escape(key) + r' = )([^,;]+)')
        body, n = pat.subn(lambda m: m.group(1) + v, body, count=1)
        assert n == 1, (key, ns)
    s = s[:i] + body + s[j:]
open(p, 'w').write(s)
print(dst)
