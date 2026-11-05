#!/usr/bin/env python3
"""split.py BATCH...: CAND (bot 1) win % by the map's altar count (one vs multi), from results.json and index.json."""
import json, os, sys, collections, math
c = collections.Counter(); alt = {}
for b in sys.argv[1:]:
    for m in json.load(open(f'{b}/results.json'))['matches']:
        p = os.path.realpath(m['map']); d = os.path.dirname(p)
        if d not in alt:
            ix = json.load(open(f'{d}/index.json')); ms = ix['maps']
            it = ms if isinstance(ms, list) else [dict(v, file=k) for k, v in ms.items()]
            alt[d] = {x['file'] if x['file'].endswith('.map26a') else x['file'] + '.map26a': x['metrics']['altars'] for x in it}
        k = 'one' if alt[d][os.path.basename(p)] == 1 else 'multi'
        if m.get('winner') is None: continue
        c[(k, 'n')] += 1; c[(k, 'w')] += m['winner'] == 0
for k in ('one', 'multi'):
    n, w = c[(k, 'n')], c[(k, 'w')]
    if n: print(k, f'{100 * w / n:.1f}% of {n} (+-{196 * math.sqrt(0.25 / n):.1f})')
