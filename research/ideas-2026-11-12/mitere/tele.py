"""Teleport crystals (r7 live and ranked v2): hop geometry from round positions, walking saved, purpose."""
import ml, collections, fl
from multiprocessing import Pool
from feat import blockers, bfs
def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))
def one(sd):
    g = ml.load(sd)
    if g is None: return None
    C = {c['id']: c for c in g['rd']['champions']}; team = {c['id']: c['team'] for c in g['meta']['champions']}; name = {c['id']: c['name'] for c in g['meta']['champions']}
    mp = g['map']; blk = blockers(mp); alt = [tuple(a) for a in mp['altars']]
    sp = [((s['minX'] + s['maxX']) // 2, (s['minY'] + s['maxY']) // 2) for s in mp['spawn']]
    trib = collections.defaultdict(list); move = collections.defaultdict(list)
    for e in g['ev']:
        if e['k'] == 'tribute_start': trib[e['a']].append((e['r'], tuple(e['altar'])))
    out = []
    for e in g['ev']:
        if e['k'] != 'teleport_start': continue
        a = e['a']; r = e['r']; i = r - 2
        if i < 0: continue
        f = (C[a]['x'][i], C[a]['y'][i]) if C[a]['alive'][i] else None
        if f is None or f[0] is None: continue
        to = tuple(e['to'])
        wd = bfs(mp, blk, f, limit=60).get(to)
        bag = C[a]['gems'][i]
        # nearest altar distances (walk) before/after
        da_f = min(cheb(f, x) for x in alt); da_t = min(cheb(to, x) for x in alt)
        nxt = [t for t in trib[a] if r < t[0] <= r + 20]
        out.append(['M' if team[a] == g['mite'] else 'O', name[a], r, cheb(f, to), wd, bag, da_f, da_t, bool(nxt), g['mapname'], len(alt)])
    return out
if __name__ == '__main__':
    import sys
    srcs = sys.argv[1:] or ['live']
    R = []
    with Pool(8) as P:
        for o in P.imap_unordered(one, [d for s in srcs for d in ml.dirs(s)], chunksize=4):
            if o: R += o
    M = [x for x in R if x[0] == 'M']
    print('Mite teleports', len(M), 'hop cheb', collections.Counter(x[3] for x in M).most_common(5))
    print(' walk distance of the hop (None=unreachable within 60):', collections.Counter((min(x[4], 40) if x[4] is not None else None) for x in M).most_common(15))
    sv = [x[4] - 3 for x in M if x[4] is not None]
    print(' walk saved (walk - 3 channel turns) median', fl.med(sv), 'p25', fl.q(sv, .25), '; saved<=0:', sum(1 for s in sv if s <= 0))
    print(' toward altar (altar dist after < before):', sum(1 for x in M if x[7] < x[6]) / len(M), 'tribute within 20 rounds:', sum(x[8] for x in M) / len(M))
    for b0, b1 in ((0, 0), (1, 9), (10, 29), (30, 99), (100, 9999)):
        s = [x for x in M if b0 <= x[5] <= b1]
        print(f'  bag {b0}-{b1}: {len(s)} ({len(s)/len(M):.0%}); toward altar {sum(1 for x in s if x[7]<x[6])/max(1,len(s)):.2f}; tribute within 20 {sum(x[8] for x in s)/max(1,len(s)):.2f}; walk saved median {fl.med([x[4]-3 for x in s if x[4] is not None])}')
    print(' by type:', collections.Counter(x[1] for x in M).most_common())
