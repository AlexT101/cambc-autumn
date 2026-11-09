"""On rerun flip maps: per (map, order), the arm's (bot 0's) timed cuts, and the mirror's, by flip direction."""
import json, sys, os, collections, statistics as st
from multiprocessing import Pool
import beh, lockcut_run as L, firing
def key(stem):
    parts = stem.split('-', 1)[1].rsplit('-', 1)
    return (parts[0] + '.map26a', (0, 1) if parts[1].startswith('12') else (1, 0))
def collect(AD):
    idx = json.load(open(AD + '/index.json'))['games']; src = {g['dir']: os.path.basename(g['source']) for g in idx}
    with Pool(32) as p: res = [r for r in p.map(firing.run, L.jloc(AD, 0), chunksize=8) if r]
    return {key(src[d.rsplit('/', 1)[1]]): (timed, early) for d, T, timed, early in res}
if __name__ == '__main__':
    A, M, RA, RM = sys.argv[1:5]
    def lm(p): return {(os.path.basename(m['map']), tuple(m['order'])): m for m in json.load(open(p))['matches']}
    ra, rm = lm(RA), lm(RM); ca, cm = collect(A), collect(M)
    G = collections.defaultdict(list)
    for k in ra:
        if k not in rm or k not in ca or k not in cm: continue
        d = int(ra[k]['winner'] == 0) - int(rm[k]['winner'] == 0)
        lab = 'UP' if d > 0 else 'DN' if d < 0 else 'same'
        G[lab].append((ca[k], cm[k], ra[k]['rounds'], rm[k]['rounds']))
    for lab, X in G.items():
        ft = [x for x in X if x[0][0]]
        print(f"{lab:5} n={len(X)} arm timed cut in {len(ft)/len(X):.2f} (gems med {st.median([t[0] for x in ft for t in x[0][0]]) if ft else 0}); mirror bot0 timed cut {sum(1 for x in X if x[1][0])/len(X):.2f}; arm early cuts/g {st.mean(len(x[0][1]) for x in X):.2f} mirror {st.mean(len(x[1][1]) for x in X):.2f}")
