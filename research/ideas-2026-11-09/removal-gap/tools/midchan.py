"""Our (T's) channels by bag band: share cancelled by enemy lock or stun, and by our own cancel."""
import beh, json, sys, os, collections
from multiprocessing import Pool
import lockcut_run as L
B = [(40, 100), (100, 138), (138, 200), (200, 10000)]
def run(j):
    k, d, T = j
    try: meta, rd, ev = beh.load(d)
    except Exception: return (k, None)
    team = {c['id']: c['team'] for c in meta['champions']}; c = collections.Counter(); open_ = {}
    for e in ev:
        if e['k'] == 'tribute_start' and team[e['a']] == T: open_[e['a']] = e['gems']
        if e['k'] in ('tribute_end', 'tribute_cancel') and e['a'] in open_:
            g = open_.pop(e['a']); b = next((x for x in B if x[0] <= g < x[1]), None)
            if b: c[(b, 'n')] += 1; c[(b, e['k'] == 'tribute_end' and 'end' or e.get('cause'))] += 1
    return (k, c)
if __name__ == '__main__':
    jobs = []
    if '--live' in sys.argv: jobs += L.jl()
    for a in sys.argv[1:]:
        if a.startswith('--'): continue
        p, b = a.rsplit(':', 1); jobs += [(os.path.basename(p) + f'-T{b}', d, T) for _, d, T in L.jloc(p, int(b))]
    with Pool(32) as pool: res = pool.map(run, jobs, chunksize=8)
    G = collections.defaultdict(collections.Counter)
    for k, c in res:
        if c: G[k].update(c)
    for k in sorted(G):
        print(k, ' | '.join(f"{b[0]}-{b[1]}: n {G[k][(b,'n')]} end {G[k][(b,'end')]/max(1,G[k][(b,'n')]):.2f} lock {G[k][(b,'lock')]/max(1,G[k][(b,'n')]):.2f} stun {G[k][(b,'stun')]/max(1,G[k][(b,'n')]):.2f}" for b in B))
