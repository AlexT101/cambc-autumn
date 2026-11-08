import json, gzip, os, sys, collections, numpy as np
sys.path.insert(0, os.path.expanduser('~/tmp-offload/carry'))
from econ import load, H
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-08/spar-tools'); import live, local
RS = [25, 50, 75, 100, 150, 200, 300, 400, 600]
def f(d, team):
    R = json.load(gzip.open(d + '/rounds.json.gz')); rr = np.array(R['round'])
    out = {}
    for r in RS:
        i = min(np.searchsorted(rr, r), len(rr) - 1)
        out[r] = (sum(c['earned'][i] for c in R['champions'] if c['team'] == team), R['gems'][team][i] + sum(c['gems'][i] for c in R['champions'] if c['team'] == team))
    return out
L = load(H + 'bigl/ana', False); S = load(H + 'spar/ana'); games = json.load(open(H + 'bigl/games.json')); liveg = {}
for mid, g in games.items():
    if g['version'] != 89 or mid not in L: continue
    liveg[(g['map'].replace('_', '-'), g['side'], live.OPP[g['opp_name']])] = (L[mid], g)
acc = collections.defaultdict(list)
for o in 'FM':
    for mp, side, m in local.matches(f'spar-c27-o29{o}'):
        k = os.path.basename(os.path.dirname(m['replay'])) + '/' + os.path.basename(m['replay']).split('.')[0]
        if k not in S or (mp, side, o) not in liveg: continue
        ot = 1 if side == 'a' else 0; ld, g = liveg[(mp, side, o)]
        for nm, d, t in (('live', H + 'bigl/ana/' + ld, ot), ('spar', H + 'spar/ana/' + S[k], ot), ('us-live', H + 'bigl/ana/' + ld, 1 - ot), ('us-spar', H + 'spar/ana/' + S[k], 1 - ot)):
            acc[(o, nm)].append(f(d, t))
for key, rs in sorted(acc.items()):
    print(key, 'gold:', ' '.join(f'r{r} {np.mean([x[r][0] for x in rs]):.0f}' for r in RS))
    print(key, 'gems owned:', ' '.join(f'r{r} {np.mean([x[r][1] for x in rs]):.0f}' for r in RS))
