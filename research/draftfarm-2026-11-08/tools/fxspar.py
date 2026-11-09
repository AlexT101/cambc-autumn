"""Paired early metrics on dgate runs: cand vs base against the same opponent, map and side. fxspar.py CANDTAG BASETAG MEMBERS..."""
import sys, os, json, pickle, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import fx
ct, bt = sys.argv[1], sys.argv[2]; mem = sys.argv[3:]
cm, bm = [], []
for m in mem:
    cm += [dict(x, run=m) for x in fx.matches(f'fxs-{ct}-{m}')]
    bm += [dict(x, run=m) for x in fx.matches(f'fxs-{bt}-{m}')]
dirs = fx.extract([m['replay'] for m in cm + bm])
base = {(m['run'], os.path.basename(m['map']), m['order'].index(0)): m for m in bm}
rows = []
for m in cm:
    us = m['order'].index(0); b = base.get((m['run'], os.path.basename(m['map']), us))
    if not b: continue
    dc, db = dirs.get(os.path.realpath(m['replay'])), dirs.get(os.path.realpath(b['replay']))
    if not dc or not db: continue
    try: C = fx.game(m, dc, us); B = fx.game(b, db, us)
    except Exception as e: continue
    for G in (C, B): G.pop('pos'); G.pop('rounds')
    C['win'] = m['winner'] == 0; B['win'] = b['winner'] == 0
    rows.append(dict(run=m['run'], map=os.path.basename(m['map']), C=C, B=B))
pickle.dump(rows, open(os.path.expanduser('~/tmp-offload/draftfarm/ana/fxspar.pkl'), 'wb'))
print(len(rows))
