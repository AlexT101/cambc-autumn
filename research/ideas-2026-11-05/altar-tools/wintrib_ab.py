#!/usr/bin/env python3
"""wintrib_ab.py BATCH ANA: winning-bag tribute starts and outcomes per side (CAND = bot 1), plus games won by
sides that held a winning bag."""
import json, gzip, os, sys, collections
B, ANA = sys.argv[1], sys.argv[2]
ix = json.load(open(f'{ANA}/index.json'))
src = {os.path.basename(g['source']): g['dir'] for g in ix['games']}
c = collections.Counter()
for f in sorted(os.listdir(B)):
    if not f.endswith('.repl26a') or f not in src: continue
    d = src[f]; cand = 0 if f[-10:-8] == '12' else 1
    m = json.load(open(f'{ANA}/{d}/meta.json'))
    R = json.load(gzip.open(f'{ANA}/{d}/rounds.json.gz')); ri = {r: i for i, r in enumerate(R['round'])}
    team = {ch['id']: ch['team'] for ch in m['champions']}
    w = m['result']['winner']
    held = [False, False]
    for i in range(len(R['round'])):
        for t in (0, 1):
            best = max((ch['gems'][i] or 0) for ch in R['champions'] if ch['team'] == t)
            if R['gems'][t][i] + best >= 1000: held[t] = True
    for t in (0, 1):
        if held[t]:
            who = 'cand' if t == cand else 'ref'; c[(who, 'held')] += 1; c[(who, 'held_won')] += w == t
    ends = {}
    ev = [json.loads(l) for l in gzip.open(f'{ANA}/{d}/events.jsonl.gz', 'rt')]
    for e in ev:
        if e['k'] in ('tribute_end', 'tribute_cancel'): ends.setdefault(e['a'], []).append(e)
    for e in ev:
        if e['k'] != 'tribute_start': continue
        t = team[e['a']]; i = ri.get(e['r'] - 1, 0)
        if R['gems'][t][i] + e['gems'] < 1000: continue
        who = 'cand' if t == cand else 'ref'
        out = next((x for x in ends.get(e['a'], []) if x['s'] > e['s']), None)
        res = 'end' if out and out['k'] == 'tribute_end' else ('cancel:' + out.get('cause', '?') if out else 'none')
        c[(who, 'starts')] += 1; c[(who, res)] += 1
for k in sorted({k[1] for k in c}): print(k, ' '.join(f'{w}={c[(w, k)]}' for w in ('cand', 'ref')))
