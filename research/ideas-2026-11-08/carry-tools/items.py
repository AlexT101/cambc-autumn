import json, gzip, os, sys, collections, numpy as np
sys.path.insert(0, os.path.expanduser('~/tmp-offload/carry'))
from econ import load, H
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-08/spar-tools'); import live, local
RW = int(os.environ.get('RW', 300))
def f(d, team):
    meta = json.load(open(d + '/meta.json')); ch = {c['id']: c for c in meta['champions']}
    out = collections.Counter()
    for l in gzip.open(d + '/events.jsonl.gz'):
        e = json.loads(l)
        if e['r'] > RW: break
        if e['k'] == 'shop' and ch[e['a']]['team'] == team and 'items' in e:
            for it, n in e['items'].items():
                fam = it.split(' Shard')[0].split(' Emblem')[0]; out[(ch[e['a']]['name'], fam)] += n * (5 if 'Emblem' in it and 'Shard' not in it else 1)
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
        for nm, d in (('live', H + 'bigl/ana/' + ld), ('spar', H + 'spar/ana/' + S[k])):
            acc[(o, nm)] += f(d, ot); n[(o, nm)] += 1
for o in 'FM':
    keys = sorted(set(acc[(o, 'live')]) | set(acc[(o, 'spar')]), key=lambda k: -(acc[(o, 'live')][k] + acc[(o, 'spar')][k]))
    print(o, 'shard-equivalents per game by r%d (live / spar):' % RW)
    for k in keys[:22]: print(f'   {k[0][:10]:10s} {k[1]:12s} {acc[(o,"live")][k]/n[(o,"live")]:5.2f} / {acc[(o,"spar")][k]/n[(o,"spar")]:5.2f}')
