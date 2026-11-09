"""T's deny locks before round 600 that cancel no tribute: does the victim V contest that altar?
Per lock: V lock hits within 100 rounds, destroyed by V within 100, V tribute gems at that altar within 100 rounds after
placement (needs the lock gone) and in the 100 rounds before (demand for that altar)."""
import beh, json, sys, os, collections, statistics as st
from multiprocessing import Pool
import lockcut_run as L
def run(j):
    k, d, T = j
    try: meta, rd, ev = beh.load(d)
    except Exception: return (k, [])
    team = {c['id']: c['team'] for c in meta['champions']}
    starts = {}; trib = []  # (round, altar, team, gems)
    for e in ev:
        if e['k'] == 'tribute_start': starts[e['a']] = e
        if e['k'] == 'tribute_end' and e['a'] in starts: trib.append((e['r'], tuple(starts[e['a']]['altar']), team[e['a']], e.get('gems', 0)))
    out = []
    for i, e in enumerate(ev):
        if e['k'] != 'lock_place' or e['team'] != T or e['r'] >= 600: continue
        # a cancel at the same step means it cut a tribute: not a deny lock
        cut = any(f['k'] == 'tribute_cancel' and f.get('cause') == 'lock' and f['s'] == e['s'] for f in ev[i + 1:i + 6])
        if cut: continue
        a = tuple(e['to']); r = e['r']; hits = 0; destroyed = None
        for f in ev[i + 1:]:
            if f['r'] - r > 100: break
            if f['k'] == 'attack' and f.get('lock') and team.get(f['a']) != T and tuple(f['to']) == a: hits += 1
            if f['k'] == 'lock_destroyed' and f['team'] == T and tuple(f['at']) == a and destroyed is None: destroyed = f['r'] - r
        before = sum(g for (tr, ta, tt, g) in trib if ta == a and tt != T and r - 100 <= tr < r)
        after = sum(g for (tr, ta, tt, g) in trib if ta == a and tt != T and r < tr <= r + 100)
        out.append(dict(hits=hits, destroyed=destroyed is not None, before=before, after=after, win=int(meta['result']['winner'] == T)))
    return (k, out)
if __name__ == '__main__':
    jobs = []
    if '--live' in sys.argv: jobs += L.jl()
    for a in sys.argv[1:]:
        if a.startswith('--'): continue
        p, b = a.rsplit(':', 1); jobs += [(os.path.basename(p) + f'-T{b}', d, T) for _, d, T in L.jloc(p, int(b))]
    with Pool(32) as pool: res = pool.map(run, jobs, chunksize=8)
    G = collections.defaultdict(list); n = collections.Counter()
    for k, o in res: G[k] += o; n[k] += 1
    for k in sorted(G):
        X = G[k]
        if not X: print(k, 'none'); continue
        print(f"{k:22} deny locks/g {len(X)/n[k]:.2f}  hit by V {st.mean(x['hits']>0 for x in X):.2f}  destroyed<=100 {st.mean(x['destroyed'] for x in X):.2f}  "
              f"V gems there 100 before {st.mean(x['before'] for x in X):.1f} / after {st.mean(x['after'] for x in X):.1f}")
