"""unseen.py EXT: zone moments (pzone2.json) where the victim did not see the Prism on its last turn: bush? how long unseen? distance."""
import sys, json, collections, statistics as st
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/vfish/surv')
from tracelib import *
ext = sys.argv[1]; rows = json.load(open('/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/vfish/surv/pzone2.json'))
G = {gm.g['source'].split('/')[-1]: gm for gm in games(ext)}
C = collections.Counter(); ages = []; n = 0
for x in rows:
    gm = G[x['game']]; v = x['vid']; r = x['r']; tr = x['tr'] or r - 1
    pr = [i for i in gm.typ if gm.typ[i] == 'Prism' and gm.team[i] != gm.cand][0]
    c = gm.ch[v]; P = gm.ch[pr]
    saw = pr in c['sees'][tr - 1]
    n += 1
    if saw: C['saw the Prism at its turn start'] += 1; continue
    bushes = {tuple(t) for t in gm.map['bushes']}
    pp = (P['x'][tr - 1], P['y'][tr - 1]); me = gm.pos(v, tr)
    onbush = pp in bushes
    # rounds since the victim last saw the Prism
    age = None
    for k in range(1, 40):
        if tr - 1 - k < 0: break
        if pr in c['sees'][tr - 1 - k]: age = k; break
    ages.append(age if age is not None else 99)
    # did any ally see it
    ally_saw = any(pr in gm.ch[a]['sees'][tr - 1] for a in gm.ch if gm.team[a] == gm.cand and a != v and gm.ch[a]['alive'][tr - 1])
    mebush = me in bushes if me else False
    C[f"unseen: Prism on bush={onbush}"] += 1
    C[f"unseen: an ally saw it={ally_saw}"] += 1
    C[f"unseen: last seen {'1-2' if age and age <= 2 else '3-6' if age and age <= 6 else '7+ or never'} rounds before"] += 1
    C[f"unseen: dec={x['dec']}"] += 1
print(n, 'zone moments')
for k, v in sorted(C.items()): print(f"  {v:4d} {k}")
