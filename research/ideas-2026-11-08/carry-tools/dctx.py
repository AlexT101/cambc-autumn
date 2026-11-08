"""Deaths by the victim's nearest-ally distance at death (r<=RW): live opp vs spar body vs us."""
import json, gzip, os, sys, collections, numpy as np
sys.path.insert(0, os.path.expanduser('~/tmp-offload/carry'))
from econ import load, H
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-08/spar-tools'); import live, local
RW = int(os.environ.get('RW', 600))
def f(d, team):
    meta = json.load(open(d + '/meta.json')); ch = {c['id']: c for c in meta['champions']}
    R = json.load(gzip.open(d + '/rounds.json.gz')); ri = {r: j for j, r in enumerate(R['round'])}; C = {c['id']: c for c in R['champions']}
    out = collections.Counter()
    for l in gzip.open(d + '/events.jsonl.gz'):
        e = json.loads(l)
        if e['r'] > RW: break
        if e['k'] != 'death' or 'linked' in e or ch[e['v']]['team'] != team: continue
        j = ri.get(e['r'] - 1, ri.get(e['r'])); x, y = e['at']
        ds = [max(abs(C[i]['x'][j] - x), abs(C[i]['y'][j] - y)) for i in C if i != e['v'] and C[i]['team'] == team and C[i]['alive'][j]
              and not (ch[i]['name'] in ('Cassi', 'Issac') and ch[e['v']]['name'] in ('Cassi', 'Issac'))]
        dm = min(ds) if ds else 99
        out['camp' if e.get('by') is None or e['by'] not in ch else ('iso' if dm >= 6 else 'near')] += 1
    return out
L = load(H + 'bigl/ana', False); S = load(H + 'spar/ana'); games = json.load(open(H + 'bigl/games.json')); liveg = {}
for mid, g in games.items():
    if g['version'] != 89 or mid not in L: continue
    liveg[(g['map'].replace('_', '-'), g['side'], live.OPP[g['opp_name']])] = (L[mid], g)
acc = collections.defaultdict(collections.Counter); n = collections.Counter()
for o in 'FM':
    for mp, side, m in local.matches(f'spar-c27-o29{o}'):
        k = os.path.basename(os.path.dirname(m['replay'])) + '/' + os.path.basename(m['replay']).split('.')[0]
        if k not in S or (mp, side, o) not in liveg: continue
        ot = 1 if side == 'a' else 0; ld, g = liveg[(mp, side, o)]
        for nm, d, t in (('live', H + 'bigl/ana/' + ld, ot), ('spar', H + 'spar/ana/' + S[k], ot), ('us', H + 'bigl/ana/' + ld, 1 - ot)):
            acc[(o, nm)] += f(d, t); n[(o, nm)] += 1
for k, c in sorted(acc.items()): print(k, ' '.join(f'{x} {c[x]/n[k]:.2f}' for x in ('iso', 'near', 'camp')))
