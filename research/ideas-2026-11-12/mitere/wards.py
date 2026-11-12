"""Wards (r7 live): rate per body, gap between a body's wards, tile kind, distance to altars / groups / enemies."""
import ml, collections, fl
from multiprocessing import Pool
def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))
def one(sd):
    g = ml.load(sd)
    if g is None: return None
    C = {c['id']: c for c in g['rd']['champions']}; team = {c['id']: c['team'] for c in g['meta']['champions']}; name = {c['id']: c['name'] for c in g['meta']['champions']}
    mp = g['map']; bush = set(map(tuple, mp['bushes'])); alt = [tuple(a) for a in mp['altars']]; gt = [tuple(q['tiles'][0]) for q in mp['groups']]
    last = {}; out = []
    for e in g['ev']:
        if e['k'] != 'ward': continue
        a = e['a']; r = e['r']; to = tuple(e['to']); i = r - 2
        if i < 0: continue
        who = 'M' if team[a] == g['mite'] else 'O'
        p = (C[a]['x'][i], C[a]['y'][i]) if C[a]['alive'][i] and C[a]['x'][i] is not None else to
        en = [(C[x]['x'][i], C[x]['y'][i]) for x in C if team[x] != team[a] and C[x]['alive'][i] and C[x]['x'][i] is not None]
        out.append([who, name[a], r, r - last.get(a, -999), to in bush, min(cheb(to, x) for x in alt), min(cheb(to, x) for x in gt),
                    min([cheb(p, x) for x in en] or [99]), C[a]['gems'][i], cheb(p, to)])
        last[a] = r
    return out, {('M' if t == g['mite'] else 'O'): sum(1 for c in C.values() if c['team'] == t) for t in (0, 1)}, len(g['rd']['round'])
if __name__ == '__main__':
    R = []; bodies = collections.Counter(); rounds = 0
    with Pool(8) as P:
        for o in P.imap_unordered(one, ml.dirs('live'), chunksize=4):
            if not o: continue
            R += o[0]; bodies.update({k: v * o[2] for k, v in o[1].items()}); rounds += o[2]
    for who in ('M', 'O'):
        s = [x for x in R if x[0] == who]
        gaps = [x[3] for x in s if x[3] < 900]
        print(f'{who}: wards {len(s)}, per body per 100 rounds {100*len(s)/bodies[who]:.2f}; gap p10/25/50/75 {fl.q(gaps,.1)}/{fl.q(gaps,.25)}/{fl.med(gaps)}/{fl.q(gaps,.75)}; gap==10: {sum(1 for x in gaps if x==10)/len(gaps):.0%}')
        print(f'   on bush {sum(x[4] for x in s)/len(s):.0%}; altar within 3 {sum(1 for x in s if x[5]<=3)/len(s):.0%}; group within 3 {sum(1 for x in s if x[6]<=3)/len(s):.0%}; enemy within 8 {sum(1 for x in s if x[7]<=8)/len(s):.0%}; '
              f'carrying {sum(1 for x in s if x[8]>0)/len(s):.0%}; placed at distance {collections.Counter(x[9] for x in s).most_common(3)}; round median {fl.med([x[2] for x in s])}')
        print('   by type per body-game: ' + ', '.join(f'{k} {v}' for k, v in collections.Counter(x[1] for x in s).most_common(8)))
