"""Nearest-ally Chebyshev distance per alive champion-round (off spawn), r<=RW: live opp vs spar bodies."""
import json, gzip, os, sys, collections, numpy as np
sys.path.insert(0, os.path.expanduser('~/tmp-offload/carry'))
from econ import load, H
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-08/spar-tools'); import live, local
RW = int(os.environ.get('RW', 200)); BODIES = sys.argv[1:] or ['o29:spar/ana']
def f(d, team):
    R = json.load(gzip.open(d + '/rounds.json.gz')); rr = R['round']; n = min(len(rr), np.searchsorted(rr, RW) + 1)
    cs = [c for c in R['champions'] if c['team'] == team]
    meta = json.load(open(d + '/meta.json')); name = {c['id']: c['name'] for c in meta['champions']}
    sp = {(c['x'][0], c['y'][0]) for c in cs}
    out = collections.defaultdict(list)
    for j in range(5, n):
        pts = [(c['x'][j], c['y'][j], c['id']) for c in cs if c['alive'][j] and (c['x'][j], c['y'][j]) not in sp]
        for x, y, i in pts:
            ds = [max(abs(x - x2), abs(y - y2)) for x2, y2, i2 in pts if i2 != i and not (name[i] in ('Cassi', 'Issac') and name[i2] in ('Cassi', 'Issac'))]
            if ds: out['all'].append(min(ds)); out[name[i]].append(min(ds))
    return out
L = load(H + 'bigl/ana', False); games = json.load(open(H + 'bigl/games.json')); liveg = {}
for mid, g in games.items():
    if g['version'] != 89 or mid not in L: continue
    liveg[(g['map'].replace('_', '-'), g['side'], live.OPP[g['opp_name']])] = (L[mid], g)
for spec in BODIES:
    body, ana = spec.split(':'); S = load(H + ana)
    acc = collections.defaultdict(lambda: collections.defaultdict(list))
    for o in 'FM':
        for mp, side, m in local.matches(f'spar-c27-{body}{o}'):
            k = os.path.basename(os.path.dirname(m['replay'])) + '/' + os.path.basename(m['replay']).split('.')[0]
            if k not in S or (mp, side, o) not in liveg: continue
            ot = 1 if side == 'a' else 0; ld, g = liveg[(mp, side, o)]
            srcs = [(body, H + ana + '/' + S[k], ot)] + ([('live', H + 'bigl/ana/' + ld, ot), ('us', H + 'bigl/ana/' + ld, 1 - ot)] if spec == BODIES[0] else [])
            for nm, d, t in srcs:
                for kk, v in f(d, t).items(): acc[(o, nm)][kk] += v
    for key, dd in sorted(acc.items()):
        a = np.array(dd['all'])
        print(key, f'median {np.median(a):.0f} <=2 {(a<=2).mean():.2f} <=4 {(a<=4).mean():.2f} >=9 {(a>=9).mean():.2f} |', ' '.join(f'{t[:6]} {np.median(dd[t]):.0f}/{(np.array(dd[t])<=4).mean():.2f}' for t in ('Vesper Vale', 'Marcella', 'Heart of Ruin', 'Vendetta', 'Cassi', 'Issac', 'Tavi', 'Willow') if len(dd[t]) > 500))
