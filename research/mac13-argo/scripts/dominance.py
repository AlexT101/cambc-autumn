"""Prism Focus dominance over the enemy Prism (mirror): share of both-alive rounds by Focus ratio, the distance
between the Prisms there, and the game result; and in the 2x+ band whether the dominant Prism killed the other within
the next 60 rounds. py dominance.py ANALYSIS_DIR"""
import gzip, json, sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
def cheb(a, b): return max(abs(a[0]-b[0]), abs(a[1]-b[1]))
BANDS = [(0, 0.5), (0.5, 0.8), (0.8, 1.25), (1.25, 2), (2, 99)]
def one(d):
    try:
        meta = json.loads((d / 'meta.json').read_text()); R = json.load(gzip.open(d / 'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
    except Exception: return None
    C = R['champions']; name = {c['id']: c['name'] for c in meta['champions']}
    P = [c for c in C if name.get(c['id']) == 'Prism']
    if len(P) != 2 or P[0]['team'] == P[1]['team']: return None
    w = meta['result']['winner']
    kills = defaultdict(list)
    for e in ev:
        if e['k'] == 'death' and e.get('by') in (P[0]['id'], P[1]['id']) and e['v'] in (P[0]['id'], P[1]['id']): kills[e['by']].append(e['r'])
    out = []
    for a, b in ((P[0], P[1]), (P[1], P[0])):
        for i, r in enumerate(R['round']):
            if i % 5 or not (a['alive'][i] and b['alive'][i]) or not b['foc'][i]: continue
            x = a['foc'][i] / b['foc'][i]
            band = next(k for k, (lo, hi) in enumerate(BANDS) if lo <= x < hi)
            dd = cheb((a['x'][i], a['y'][i]), (b['x'][i], b['y'][i]))
            k = any(r < kr <= r + 60 for kr in kills[a['id']]); kd = any(r < kr <= r + 60 for kr in kills[b['id']])
            out.append((band, dd, a['team'] == w, k, kd, a['gems'][i], b['gems'][i]))
    return out
if __name__ == '__main__':
    root = Path(sys.argv[1]); dirs = [p for p in root.iterdir() if (p / 'meta.json').exists()]
    agg = defaultdict(lambda: [0, 0, 0, 0, 0, 0, 0, 0])
    with ProcessPoolExecutor(24) as ex:
        for rows in ex.map(one, dirs, chunksize=8):
            for band, dd, won, k, kd, ga, gb in rows or []:
                s = agg[band]; s[0] += 1; s[1] += dd; s[2] += won; s[3] += k; s[4] += kd; s[5] += ga; s[6] += gb; s[7] += dd <= 8
    for k, (lo, hi) in enumerate(BANDS):
        s = agg[k]; n = max(1, s[0])
        print(f'ratio {lo}-{hi}: {100*s[0]/sum(v[0] for v in agg.values()):.1f}% of rounds, dist {s[1]/n:.1f} (within 8 {100*s[7]/n:.0f}%), '
              f'game won {100*s[2]/n:.0f}%, kills it in 60r {100*s[3]/n:.1f}%, killed by it {100*s[4]/n:.1f}%, bags {s[5]/n:.0f}/{s[6]/n:.0f}')
    agg = defaultdict(lambda: [0, 0, 0, 0])
    with ProcessPoolExecutor(24) as ex:
        for rows in ex.map(one, dirs, chunksize=8):
            for band, dd, won, k, kd, ga, gb in rows or []:
                s = agg[(band, 0 if dd <= 6 else 1 if dd <= 12 else 2)]; s[0] += 1; s[1] += won; s[2] += k; s[3] += kd
    print('by distance between the Prisms (n rounds sampled every 5; won = game; kill/dies within 60 rounds):')
    for b, (lo, hi) in enumerate(BANDS):
        print(f'  {lo}-{hi}: ' + ' | '.join(f"d{['<=6','7-12','13+'][j]} n{agg[(b,j)][0]} won{100*agg[(b,j)][1]/max(1,agg[(b,j)][0]):.0f} kill{100*agg[(b,j)][2]/max(1,agg[(b,j)][0]):.1f} dies{100*agg[(b,j)][3]/max(1,agg[(b,j)][0]):.1f}" for j in range(3)))
