#!/usr/bin/env python3
"""split_sites.py SITES.jsonl BATCH...: CAND (bot 1) win % by the map's altar make-up (one tile, one 2-tile site,
other), from results.json and sites.mjs output (lines with file and name)."""
import json, math, os, sys, collections
kind = {}
for l in open(sys.argv[1]):
    if not l.startswith('{'): continue
    x = json.loads(l)
    k = 'one-tile' if x['altars'] == 1 else 'one-site-2' if x['sites'] == 1 and x['altars'] <= 2 else 'one-site-big' if x['sites'] == 1 else 'multi'
    kind[os.path.realpath(x['file'])] = k; kind[x['name']] = k
c = collections.Counter()
for b in sys.argv[2:]:
    for m in json.load(open(f'{b}/results.json'))['matches']:
        if m.get('winner') is None: continue
        p = os.path.realpath(m['map']); k = kind.get(p) or kind.get(os.path.basename(p)[:-7], '?')
        c[(k, 'n')] += 1; c[(k, 'w')] += m['winner'] == 0
for k in ('one-tile', 'one-site-2', 'one-site-big', 'multi', '?'):
    n, w = c[(k, 'n')], c[(k, 'w')]
    if n: print(f'  {k}: {100 * w / n:.1f}% of {n} (+-{196 * math.sqrt(0.25 / n):.1f})')
