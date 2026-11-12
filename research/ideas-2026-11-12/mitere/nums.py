"""Live r7: healthy (>= 0.6), empty (bag < 10) bodies in contact (an enemy within 4), by numbers within 5 (enemies minus
the body and its mates), for Mite's side and ours: death within 10 rounds, and the enemy deaths within 5 of it."""
import sys, os, collections
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ml
def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))
def one(sd):
    g = ml.load(sd, events=False)
    if g is None: return None
    m = g['mite']; rd = g['rd']; C = {c['id']: c for c in rd['champions']}; team = {c['id']: c['team'] for c in g['meta']['champions']}
    name = {c['id']: c['name'] for c in g['meta']['champions']}
    nR = len(rd['round']); out = collections.Counter()
    ids = list(C)
    for i in range(0, nR - 11, 2):
        P = {c: (C[c]['x'][i], C[c]['y'][i]) for c in ids if C[c]['alive'][i] and C[c]['x'][i] is not None}
        for c, p in P.items():
            cc = C[c]
            if cc['hp'][i] < 0.6 * cc['maxHp'][i] or cc['gems'][i] >= 10: continue
            en = [x for x in P if team[x] != team[c]]
            if not en or min(cheb(p, P[x]) for x in en) > 4: continue
            d = sum(1 for x in en if cheb(p, P[x]) <= 5) - sum(1 for x in P if team[x] == team[c] and cheb(p, P[x]) <= 5)
            d = max(-2, min(2, d)); side = 'M' if team[c] == m else 'O'
            dies = any(not cc['alive'][i + k] for k in range(1, 11))
            kills = sum(1 for x in en if cheb(p, P[x]) <= 5 and any(not C[x]['alive'][i + k] for k in range(1, 11)))
            out[(side, d, 'n')] += 1; out[(side, d, 'die')] += dies; out[(side, d, 'kill')] += kills
            if side == 'M' and name[c] == 'Vesper Vale': out[(side + 'V', d, 'n')] += 1; out[(side + 'V', d, 'die')] += dies; out[(side + 'V', d, 'kill')] += kills
    return out
if __name__ == '__main__':
    T = collections.Counter()
    with Pool(8) as P:
        for o in P.imap_unordered(one, ml.dirs('live'), chunksize=4):
            if o: T.update(o)
    for side in ('M', 'MV', 'O'):
        for d in range(-2, 3):
            n = T[(side, d, 'n')]
            if n: print(f'{side:2s} enemies - own within 5 = {d:+d}: {n:6d} body-rounds; the body dies within 10: {T[(side,d,"die")]/n:.1%}; enemies within 5 die: {T[(side,d,"kill")]/n:.2f}')
