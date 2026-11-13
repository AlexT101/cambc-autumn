"""Prism encounters (Prisms within 6, r<600): per team-game, encounter rounds and allies of our Prism within 8 vs 9-14."""
import gzip, json, sys, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
def cheb(c, d, i):
    if c['x'][i] is None or d['x'][i] is None: return 99
    return max(abs(c['x'][i]-d['x'][i]), abs(c['y'][i]-d['y'][i]))
def g(d):
    meta = json.loads((d/'meta.json').read_text()); R = json.load(gzip.open(d/'rounds.json.gz'))
    names = {int(c['id']): c['name'] for c in meta['champions']}; team = {int(c['id']): int(c['team']) for c in meta['champions']}
    ch = {int(c['id']): c for c in R['champions']}
    pr = [i for i in ch if names[i] == 'Prism']
    if len(pr) != 2: return None
    out = collections.Counter(); n = min(600, len(ch[pr[0]]['x']))
    for i in range(n):
        A, B = ch[pr[0]], ch[pr[1]]
        if not (A['alive'][i] and B['alive'][i]) or cheb(A, B, i) > 6: continue
        out['rounds'] += 1
        for p in pr:
            P = ch[p]
            near = sum(1 for c in ch if team[c] == team[p] and c != p and ch[c]['alive'][i] and cheb(ch[c], P, i) <= 8)
            mid = sum(1 for c in ch if team[c] == team[p] and c != p and ch[c]['alive'][i] and 8 < cheb(ch[c], P, i) <= 14)
            out['near'] += near; out['mid'] += mid
    return out
if __name__ == '__main__':
    dirs = [d for d in Path(sys.argv[1]).iterdir() if (d/'meta.json').exists()]
    T = collections.Counter(); k = 0
    with ProcessPoolExecutor(32) as ex:
        for r in ex.map(g, dirs, chunksize=8):
            if r: T.update(r); k += 1
    print('two-Prism games', k, 'encounter rounds a game', round(T['rounds']/k, 1), 'allies within 8 per Prism-round', round(T['near']/(2*T['rounds']), 2), 'allies 9-14', round(T['mid']/(2*T['rounds']), 2))
