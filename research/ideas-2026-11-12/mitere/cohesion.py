"""Packing: mates within 5 by round bucket and context, and which pairs travel together (r7 live, both teams)."""
import ml, collections, sys, itertools
from multiprocessing import Pool
def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))
def one(sd):
    g = ml.load(sd, events=False)
    if g is None: return None
    C = g['rd']['champions']; nR = len(g['rd']['round']); name = {c['id']: c['name'] for c in g['meta']['champions']}
    out = {'coh': collections.defaultdict(lambda: [0, 0]), 'pair': collections.defaultdict(lambda: [0, 0]), 'lead': collections.defaultdict(lambda: [0, 0])}
    for t in (0, 1):
        who = 'M' if t == g['mite'] else 'O'
        mine = [c for c in C if c['team'] == t]; en = [c for c in C if c['team'] != t]
        for i in range(0, nR, 2):
            P = {c['id']: (c['x'][i], c['y'][i]) for c in mine if c['alive'][i]}
            E = [(c['x'][i], c['y'][i]) for c in en if c['alive'][i]]
            for c in mine:
                if c['id'] not in P: continue
                p = P[c['id']]
                dE = min([cheb(p, e) for e in E] or [99])
                ctx = 'contact' if dE <= 6 else ('near' if dE <= 12 else 'quiet')
                n5 = sum(1 for k, q in P.items() if k != c['id'] and cheb(p, q) <= 5 and not {name[k], name[c['id']]} == {'Cassi', 'Issac'})
                rb = min(i // 200, 5)
                for key in ((who, ctx, rb), (who, ctx, 'all'), (who, 'all', rb), (who, 'all', 'all')):
                    out['coh'][key][0] += 1; out['coh'][key][1] += n5
            for a, b in itertools.combinations(sorted(P), 2):
                na, nb = sorted((name[a], name[b]))
                out['pair'][(who, na, nb)][0] += 1; out['pair'][(who, na, nb)][1] += cheb(P[a], P[b]) <= 5
    return {k: dict(v) for k, v in out.items()}
if __name__ == '__main__':
    ds = ml.dirs('live')
    tot = {'coh': collections.defaultdict(lambda: [0, 0]), 'pair': collections.defaultdict(lambda: [0, 0])}
    with Pool(8) as P:
        for o in P.imap_unordered(one, ds, chunksize=4):
            if not o: continue
            for k in ('coh', 'pair'):
                for kk, v in o[k].items(): tot[k][kk][0] += v[0]; tot[k][kk][1] += v[1]
    print('mates within 5 (C&I partner not counted), mean over alive bodies, every other round')
    for ctx in ('all', 'quiet', 'near', 'contact'):
        for who in ('M', 'O'):
            print(f'  {who} {ctx:>8}: ' + ' '.join(f'{("r"+str(rb*200)) if rb!="all" else "all"}:{tot["coh"][(who,ctx,rb)][1]/max(1,tot["coh"][(who,ctx,rb)][0]):.2f}' for rb in ('all', 0, 1, 2, 3, 4, 5)) +
                  f'  (share of rounds {tot["coh"][(who,ctx,"all")][0]/tot["coh"][(who,"all","all")][0]:.2f})')
    print('pairs within 5, share of rounds both alive (n rounds)')
    for who in ('M', 'O'):
        ps = sorted(((v[1] / v[0], k, v[0]) for k, v in tot['pair'].items() if k[0] == who and v[0] > 5000), reverse=True)
        print(f'  {who}: ' + '; '.join(f'{k[1]}+{k[2]} {s:.2f}' for s, k, n in ps[:14]))
