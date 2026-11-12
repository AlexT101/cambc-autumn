"""Live r7, Mite's Vesper's kills of our bodies: every round of the last 8 before the death with the victim within 6
of her, classified at the round's start (index r-2) by whether the victim sees her, whether she is within its
basic-attack range, and what it did that round (hit her / hit another / nothing), with her damage to it that round."""
import sys, os, collections
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ml
RANGED = {'Vesper Vale', 'Prism', 'Stellar', 'Tavi', 'Willow', 'Cassi'}
def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))
def one(sd):
    g = ml.load(sd)
    if g is None: return None
    m = g['mite']; o = 1 - m; rd = g['rd']; bush = {tuple(b) for b in g['map']['bushes']}
    name = {c['id']: c['name'] for c in g['meta']['champions']}; team = {c['id']: c['team'] for c in g['meta']['champions']}
    C = {c['id']: c for c in rd['champions']}
    V = [c for c in name if team[c] == m and name[c] == 'Vesper Vale']
    if not V: return None
    v = V[0]; nR = len(rd['round'])
    def at(c, i):
        cc = C[c]
        return (cc['x'][i], cc['y'][i]) if 0 <= i < nR and cc['alive'][i] and cc['x'][i] is not None else None
    hitV = collections.defaultdict(float); act = collections.defaultdict(set)
    for e in g['ev']:
        if e['k'] in ('attack', 'cast') and e.get('dmg') and e['a'] == v:
            for t, d in e['dmg']: hitV[(t, e['r'])] += d
        if e['k'] == 'attack' and team.get(e.get('a')) == o: act[(e['a'], e['r'])].add('V' if e.get('tgt') == v else ('M' if team.get(e.get('tgt')) == m else 'camp'))
    T = collections.Counter()
    for e in g['ev']:
        if e['k'] != 'death' or e.get('by') != v or team.get(e.get('v')) != o or e.get('linked') is not None: continue
        x = e['v']; r = e['r']
        if r < 12: continue
        rng = 3 if name[x] in RANGED else 1
        for rr in range(r - 7, r + 1):
            i = rr - 2; p, q = at(x, i), at(v, i)
            if not p or not q or cheb(p, q) > 6: continue
            seen = v in (C[x]['sees'][i] or []); inr = cheb(p, q) <= rng
            a = act.get((x, rr), set()); did = 'hitV' if 'V' in a else ('hitM' if 'M' in a else ('camp' if a else 'none'))
            key = ('seen' if seen else ('unseen-bush' if q in bush else 'unseen')), ('inrange' if inr else 'out'), did
            T[key] += 1; T[key + ('dmg',)] += hitV[(x, rr)]; T['rounds'] += 1
    return T
if __name__ == '__main__':
    T = collections.Counter()
    with Pool(8) as P:
        for t in P.imap_unordered(one, ml.dirs('live'), chunksize=4):
            if t: T.update(t)
    n = T.pop('rounds'); dm = sum(v for k, v in T.items() if k[-1] == 'dmg')
    print(n, 'victim-rounds within 6 of her, last 8 rounds before her kills')
    for k in sorted((k for k in T if k[-1] != 'dmg'), key=lambda k: -T[k]):
        print(f'  {"/".join(k):28s} {T[k] / n:6.1%} of rounds, {T[k + ("dmg",)] / dm:6.1%} of her damage')
