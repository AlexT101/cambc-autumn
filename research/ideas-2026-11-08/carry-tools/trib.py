import json, gzip, os, sys, collections, numpy as np
sys.path.insert(0, os.path.expanduser('~/tmp-offload/carry'))
from econ import load, H
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-08/spar-tools'); import live, local
RW = 600
def f(d, team):
    meta = json.load(open(d + '/meta.json')); ch = {c['id']: c for c in meta['champions']}
    t = []; dg = []
    for l in gzip.open(d + '/events.jsonl.gz'):
        e = json.loads(l)
        if e['r'] > RW: break
        if e['k'] == 'tribute_end' and ch[e['a']]['team'] == team: t.append(e['gems'])
        if e['k'] == 'death' and ch[e['v']]['team'] == team: dg.append(e['gems'])
    return t, dg
L = load(H + 'bigl/ana', False); S = load(H + 'spar/ana')
games = json.load(open(H + 'bigl/games.json')); liveg = {}
for mid, g in games.items():
    if g['version'] != 89 or mid not in L: continue
    liveg[(g['map'].replace('_', '-'), g['side'], live.OPP[g['opp_name']])] = (L[mid], g)
acc = collections.defaultdict(lambda: [[], [], 0])
for o in 'FM':
    for mp, side, m in local.matches(f'spar-c27-o29{o}'):
        k = os.path.basename(os.path.dirname(m['replay'])) + '/' + os.path.basename(m['replay']).split('.')[0]
        if k not in S or (mp, side, o) not in liveg: continue
        ot = 1 if side == 'a' else 0; ld, g = liveg[(mp, side, o)]
        for nm, d, t in (('live', H + 'bigl/ana/' + ld, ot), ('spar', H + 'spar/ana/' + S[k], ot), ('us', H + 'bigl/ana/' + ld, 1 - ot)):
            a, b = f(d, t); acc[(o, nm)][0] += a; acc[(o, nm)][1] += b; acc[(o, nm)][2] += 1
for key, (t, dg, n) in sorted(acc.items()):
    t = np.array(t); dg = np.array(dg)
    print(key, f'tributes/g {len(t)/n:.1f} mean bag {t.mean():.1f} median {np.median(t):.0f} p<25 {(t<25).mean():.2f} gems tributed/g {t.sum()/n:.0f} | deaths/g {len(dg)/n:.1f} gems lost/g {dg.sum()/n:.0f}')
