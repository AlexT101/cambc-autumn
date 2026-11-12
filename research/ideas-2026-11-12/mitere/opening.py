"""Opening: cohesion per 20-round bucket for the first 400 rounds, and the round the pack breaks (r7 live)."""
import ml, collections, fl
from multiprocessing import Pool
def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))
def one(sd):
    g = ml.load(sd, events=False)
    if g is None: return None
    C = g['rd']['champions']; nR = len(g['rd']['round']); name = {c['id']: c['name'] for c in g['meta']['champions']}
    res = {}
    for t in (0, 1):
        who = 'M' if t == g['mite'] else 'O'
        mine = [c for c in C if c['team'] == t]
        b = collections.defaultdict(list); big = collections.defaultdict(list)
        for i in range(0, min(nR, 400)):
            P = [(c['x'][i], c['y'][i]) for c in mine if c['alive'][i] and name[c['id']] != 'Issac']
            if len(P) < 2: continue
            n5 = [sum(1 for q in P if q != p and cheb(p, q) <= 5) for p in P]
            b[i // 20].append(sum(n5) / len(n5) / (len(P) - 1))  # share of mates within 5
            # largest clump within 5 of some body, as share of bodies
            big[i // 20].append(max(sum(1 for q in P if cheb(p, q) <= 5) for p in P) / len(P))
        brk = next((k * 20 for k in sorted(big) if fl.mean(big[k]) < 0.6 and k >= 1), None)
        res[who] = ({k: fl.mean(v) for k, v in b.items()}, {k: fl.mean(v) for k, v in big.items()}, brk, len(mine))
    res['earned100'] = {('M' if t == g['mite'] else 'O'): sum(c['earned'][min(99, nR - 1)] for c in C if c['team'] == t) for t in (0, 1)}
    return res
if __name__ == '__main__':
    R = []
    with Pool(8) as P:
        for o in P.imap_unordered(one, ml.dirs('live'), chunksize=4):
            if o: R.append(o)
    for who in ('M', 'O'):
        print(who, 'share of mates within 5 by 20-round bucket: ' + ' '.join(f'{k*20}:{fl.mean(o[who][0].get(k, float("nan")) for o in R if k in o[who][0]):.2f}' for k in range(20)))
        print(who, 'largest clump share:                      ' + ' '.join(f'{k*20}:{fl.mean(o[who][1].get(k) for o in R if k in o[who][1]):.2f}' for k in range(20)))
        br = [o[who][2] for o in R]
        print(who, 'pack break (largest clump < 60%) median round', fl.med([b for b in br if b is not None]), 'never', sum(1 for b in br if b is None), 'earned r100', fl.mean(o['earned100'][who] for o in R))
