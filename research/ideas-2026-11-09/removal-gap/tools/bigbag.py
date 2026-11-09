"""Rounds a living champion carries 150+ gems that do not win: enemies within 4 / 8 (mean), and the carrier's deaths
to champions per 100 such rounds, by carrier side (us = T)."""
import beh, json, sys, collections
from multiprocessing import Pool
import lockcut_run as L
def run(j):
    k, d, T = j
    try: meta, rd, ev = beh.load(d)
    except Exception: return (k, None)
    ch = rd['champions']; R = rd['round']; n = len(R); sc = rd['gems']
    dr = collections.defaultdict(set)
    for e in ev:
        if e['k'] == 'death' and e.get('by') is not None: dr[e['v']].add(e['r'])
    o = collections.Counter()
    for c in ch:
        s = 'us' if c['team'] == T else 'op'
        for i in range(n):
            g = c['gems'][i]
            if not c['alive'][i] or g < 150 or g + sc[c['team']][i] >= 1000 or c['x'][i] is None: continue
            o[(s, 'r')] += 1
            for x in ch:
                if x['team'] == c['team'] or not x['alive'][i] or x['x'][i] is None: continue
                dd = max(abs(x['x'][i] - c['x'][i]), abs(x['y'][i] - c['y'][i]))
                o[(s, 'e4')] += dd <= 4; o[(s, 'e8')] += dd <= 8
            o[(s, 'd')] += (R[i] + 1) in dr[c['id']] or R[i] in dr[c['id']]
    return (k, o)
if __name__ == '__main__':
    jobs = L.jl() + L.jloc(sys.argv[1], 1)
    with Pool(40) as p: res = p.map(run, jobs, chunksize=4)
    G = collections.defaultdict(collections.Counter); N = collections.Counter()
    for k, o in res:
        if o: G[k].update(o); N[k] += 1
    for k, o in G.items():
        for s in ('us', 'op'):
            r = max(1, o[(s, 'r')])
            print(f"{k:14} carrier={s} 150+ non-winning rounds {o[(s,'r')]/N[k]:.0f}/g  enemies<=4 {o[(s,'e4')]/r:.2f} <=8 {o[(s,'e8')]/r:.2f}  deaths/100 rounds {100*o[(s,'d')]/r:.2f}")
