#!/usr/bin/env python3
"""cooked_flow.py BATCH ANA [E_MIN GAP]: once a side is cooked, per game: gems the leader tributes, leader bags
the trailer kills, trailer deaths, trailer tributes, rounds left; for CAND-trailing vs REF-trailing games."""
import json, gzip, os, sys, collections
B, ANA = sys.argv[1], sys.argv[2]
E_MIN, GAP = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (600, 200)
ix = json.load(open(f'{ANA}/index.json'))
src = {os.path.basename(g['source']): g['dir'] for g in ix['games']}
c = collections.Counter()
for f in sorted(os.listdir(B)):
    if not f.endswith('.repl26a') or f not in src: continue
    d = src[f]; cand = 0 if f[-10:-8] == '12' else 1
    m = json.load(open(f'{ANA}/{d}/meta.json'))
    R = json.load(gzip.open(f'{ANA}/{d}/rounds.json.gz'))
    team = {ch['id']: ch['team'] for ch in m['champions']}
    t0 = hit = None
    for i in range(len(R['round'])):
        for t in (0, 1):
            if R['gems'][1 - t][i] >= E_MIN and R['gems'][1 - t][i] - R['gems'][t][i] >= GAP: hit = t
        if hit is not None: t0 = R['round'][i]; break
    if hit is None: continue
    who = 'cand' if hit == cand else 'ref'
    c[(who, 'n')] += 1; c[(who, 'won')] += m['result']['winner'] == hit
    c[(who, 'rounds_left')] += m['result']['rounds'] - t0
    for l in gzip.open(f'{ANA}/{d}/events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e['r'] < t0: continue
        k = e['k']
        if k == 'tribute_end': c[(who, 'lead_trib' if team[e['a']] != hit else 'trail_trib')] += e['gems']
        elif k == 'death':
            if team[e['v']] == hit: c[(who, 'trail_deaths')] += 1; c[(who, 'trail_bag_lost')] += e.get('gems', 0)
            else:
                c[(who, 'lead_deaths')] += 1
                if e.get('by') is not None and team.get(e['by']) == hit: c[(who, 'lead_bag_taken')] += e.get('gems', 0)
        elif k == 'tribute_cancel': c[(who, 'lead_cancel' if team[e['a']] != hit else 'trail_cancel', e.get('cause'))] += 1
keys = sorted({k[1:] for k in c}, key=str)
for k in keys:
    print(k, ' '.join(f"{w}={c[(w,) + k] / max(1, c[(w, 'n')]):.2f}" for w in ('cand', 'ref')))
print('n', c[('cand', 'n')], c[('ref', 'n')])
