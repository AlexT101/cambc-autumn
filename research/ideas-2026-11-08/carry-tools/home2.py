"""Healthy (>=0.6) recalls carrying gems: did a shop follow on arrival, rounds to the next tribute, gems, gold at start."""
import json, gzip, os, sys, collections, numpy as np
sys.path.insert(0, os.path.expanduser('~/tmp-offload/carry'))
from econ import load, H
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-08/spar-tools'); import live, local
RW = int(os.environ.get('RW', 600))
def f(d, team):
    meta = json.load(open(d + '/meta.json')); ch = {c['id']: c for c in meta['champions']}
    R = json.load(gzip.open(d + '/rounds.json.gz')); ri = {r: j for j, r in enumerate(R['round'])}; C = {c['id']: c for c in R['champions']}
    ev = [json.loads(l) for l in gzip.open(d + '/events.jsonl.gz')]
    starts = {}; recs = []
    for idx, e in enumerate(ev):
        if e['r'] > RW: break
        a = e.get('a')
        if a is None or ch[a]['team'] != team: continue
        if e['k'] == 'recall_start':
            j = ri.get(e['r']); starts[a] = (C[a]['hp'][j] / max(1, C[a]['maxHp'][j]), e['gems'], C[a]['gold'][j], e['r']) if j is not None else None
        elif e['k'] == 'recall_end' and starts.get(a):
            hp, gm, gold, r0 = starts[a]
            if hp < 0.6 or e['gems'] == 0: continue
            shop = 0; trib = None; spent = 0
            for e2 in ev[idx + 1:]:
                if e2['r'] > e['r'] + 60: break
                if e2.get('a') != a: continue
                if e2['k'] == 'shop' and e2['r'] <= e['r'] + 1: shop = 1; spent += -e2['gold']
                if e2['k'] == 'tribute_start': trib = e2['r'] - e['r']; break
                if e2['k'] in ('death',): break
            recs.append((gm, gold, shop, spent, trib))
    return recs
if __name__ == '__main__':
    L = load(H + 'bigl/ana', False); S = load(H + 'spar/ana')
    games = json.load(open(H + 'bigl/games.json')); liveg = {}
    for mid, g in games.items():
        if g['version'] != 89 or mid not in L: continue
        liveg[(g['map'].replace('_', '-'), g['side'], live.OPP[g['opp_name']])] = (L[mid], g)
    acc = collections.defaultdict(list); n = collections.Counter()
    for o in 'FM':
        for mp, side, m in local.matches(f'spar-c27-o29{o}'):
            k = os.path.basename(os.path.dirname(m['replay'])) + '/' + os.path.basename(m['replay']).split('.')[0]
            if k not in S or (mp, side, o) not in liveg: continue
            ot = 1 if side == 'a' else 0; ld, g = liveg[(mp, side, o)]
            for nm, d, t in (('live', H + 'bigl/ana/' + ld, ot), ('spar', H + 'spar/ana/' + S[k], ot)):
                acc[(o, nm)] += f(d, t); n[(o, nm)] += 1
    for key, rs in sorted(acc.items()):
        a = np.array([(g, gd, s, sp, -1 if t is None else t) for g, gd, s, sp, t in rs], float)
        tr = a[a[:, 4] >= 0]
        print(key, f'n/g {len(a)/n[key]:.1f} gems {a[:,0].mean():.1f} gold@start {a[:,1].mean():.0f} shop {a[:,2].mean():.2f} spent {a[:,3].mean():.0f} trib-within-60 {len(tr)/len(a):.2f} rounds-to-trib {np.median(tr[:,4]) if len(tr) else -1:.0f}',
              'gold<30', f'{(a[:,1]<30).mean():.2f}', 'gems<10', f'{(a[:,0]<10).mean():.2f}')
