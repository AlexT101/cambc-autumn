#!/usr/bin/env python3
"""presence.py BATCH ANA: after the cook point (600/200), at each leader tribute start, the trailer's bodies within
3 and 8 of that altar, and the start's outcome; CAND-trailing vs REF-trailing."""
import json, gzip, os, sys, collections
B, ANA = sys.argv[1], sys.argv[2]
ix = json.load(open(f'{ANA}/index.json'))
src = {os.path.basename(g['source']): g['dir'] for g in ix['games']}
c = collections.Counter()
for f in sorted(os.listdir(B)):
    if not f.endswith('.repl26a') or f not in src: continue
    d = src[f]; cand = 0 if f[-10:-8] == '12' else 1
    m = json.load(open(f'{ANA}/{d}/meta.json'))
    R = json.load(gzip.open(f'{ANA}/{d}/rounds.json.gz'))
    team = {ch['id']: ch['team'] for ch in m['champions']}
    hit = t0 = None
    for i in range(len(R['round'])):
        for t in (0, 1):
            if R['gems'][1 - t][i] >= 600 and R['gems'][1 - t][i] - R['gems'][t][i] >= 200: hit = t
        if hit is not None: t0 = R['round'][i]; break
    if hit is None: continue
    who = 'cand' if hit == cand else 'ref'
    ri = {r: i for i, r in enumerate(R['round'])}
    ev = [json.loads(l) for l in gzip.open(f'{ANA}/{d}/events.jsonl.gz', 'rt')]
    ends = {}
    for e in ev:
        if e['k'] in ('tribute_end', 'tribute_cancel'): ends.setdefault(e['a'], []).append(e)
    for e in ev:
        if e['k'] != 'tribute_start' or e['r'] < t0 or team[e['a']] == hit: continue
        A = e['altar']; i = ri.get(e['r'] - 1, 0); n3 = n8 = 0
        for ch in R['champions']:
            if ch['team'] != hit or not ch['alive'][i] or ch['x'][i] is None: continue
            dd = max(abs(ch['x'][i] - A[0]), abs(ch['y'][i] - A[1])); n3 += dd <= 3; n8 += dd <= 8
        out = next((x for x in ends.get(e['a'], []) if x['s'] > e['s']), None)
        res = 'end' if out and out['k'] == 'tribute_end' else ('cancel:' + out.get('cause', '?') if out else 'none')
        c[(who, 'starts')] += 1; c[(who, 'gems')] += e['gems']; c[(who, res)] += 1
        c[(who, 'w3=%d' % min(n3, 2))] += 1; c[(who, 'w8=%d' % min(n8, 2))] += 1
for k in sorted({k[1] for k in c}):
    print(k, ' '.join(f'{w}={c[(w, k)]}' for w in ('cand', 'ref')))
