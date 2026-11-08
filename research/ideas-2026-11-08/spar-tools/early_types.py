"""Early economy per opponent champion type: live v89 opponent against the spar body, same map/side/draft."""
import json, gzip, os, sys, collections, numpy as np
sys.path.insert(0, os.path.dirname(__file__)); import live, local
from fidelity import load, H, liveg, S, BODY, ANA
def per_type(d, team, rounds=(100, 200, 300)):
    meta = json.load(open(d + '/meta.json')); R = json.load(gzip.open(d + '/rounds.json.gz')); rr = np.array(R['round'])
    name = {c['id']: c['name'] for c in meta['champions']}; out = {}
    for c in R['champions']:
        if c['team'] != team: continue
        for r in rounds:
            i = min(np.searchsorted(rr, r), len(rr) - 1)
            out[(name[c['id']], r, 'gold')] = c['earned'][i]; out[(name[c['id']], r, 'gems')] = c['gems'][i]
            out[(name[c['id']], r, 'alive')] = c['alive'][i]
    return out
acc = collections.defaultdict(lambda: ([], []))
for o in 'FM':
    for mp, side, m in local.matches(f'spar-c27-{BODY}{o}'):
        k = os.path.basename(m['replay']).split('.')[0]
        if k not in S or (mp, side, o) not in liveg: continue
        t = 1 if side == 'a' else 0
        a = per_type(H + 'bigl/ana/' + liveg[(mp, side, o)], t); b = per_type(H + ANA + '/' + S[k], t)
        for key in a:
            if key in b: acc[(o,) + key][0].append(a[key]); acc[(o,) + key][1].append(b[key])
for key in sorted(acc):
    if key[3] != 'gold' or key[2] != 200: continue
    a, b = acc[key]
    print(f'{key[0]} {key[1]:14s} r{key[2]} earned gold: live {np.mean(a):6.0f}  spar {np.mean(b):6.0f}  ({100*(np.mean(a)/max(1,np.mean(b))-1):+.0f}%)  n {len(a)}')
