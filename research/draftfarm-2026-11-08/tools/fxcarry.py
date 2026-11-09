"""Per-champion gold earned (ours), cand minus mirror, and the share of team gold by the top-weighted body."""
import pickle, sys, collections, numpy as np
rows = pickle.load(open(sys.argv[1], 'rb'))
d = collections.defaultdict(lambda: [[], []])
team = [[], []]; top = [[], []]
for r in rows:
    C, B = r['C'].get('earned_by'), r['B'].get('earned_by')
    if not C or not B: continue
    tc = tb = 0; best = None
    for cid, (nm, ours, e2, e4) in C.items():
        if not ours or cid not in B: continue
        d[nm][0].append(e2 - B[cid][2]); d[nm][1].append(e4 - B[cid][3]); tc += e4; tb += B[cid][3]
    team[0].append(tc - tb)
for nm, (a, b) in sorted(d.items(), key=lambda x: -len(x[1][0])):
    print(f'{nm:14s} n {len(a):5d}  d earned r200 {np.mean(a):+6.1f}±{np.std(a)/np.sqrt(len(a)):.1f}  r400 {np.mean(b):+6.1f}±{np.std(b)/np.sqrt(len(b)):.1f}')
print('team d earned r400', np.mean(team[0]), '±', np.std(team[0]) / np.sqrt(len(team[0])))
