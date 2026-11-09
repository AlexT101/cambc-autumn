import pickle, sys, collections, numpy as np
res = pickle.load(open(sys.argv[1], 'rb'))
agg = collections.defaultdict(lambda: np.zeros(6)); n = len(res)
for g in res:
    for x in g['rows']:
        if not x['ours'] or not x['moved'] or not x['ng']: continue
        trail, lf, lt, nf, nt = x['ng']
        kind = ('L' if lf else '-') + ('N' if nf else '') + '>' + ('L' if lt else '-') + ('N' if nt else '')
        k = (kind, x['br'], trail[-1:] if trail else '?')
        agg[k] += [1, x['died_champ'], x['esc'] > 0, x['dealt'] > 0, x['gems'], x['H'] / max(1, x['maxH'])]
for k, a in sorted(agg.items(), key=lambda t: (t[0][0], -t[1][0])):
    if a[0] >= 15: print(f"{k[0]:7s} {k[1]} {k[2]}  {a[0]/n:6.3f}/game  died {a[1]/a[0]:.3f}  esc {a[2]/a[0]:.2f}  hit {a[3]/a[0]:.2f}  gems {a[4]/a[0]:5.1f}  hp {a[5]/a[0]:.2f}")
