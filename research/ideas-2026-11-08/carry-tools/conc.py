import pickle, sys, collections, numpy as np
rows = pickle.load(open(sys.argv[1], 'rb'))
CAR = ['Vesper Vale', 'Marcella', 'Heart of Ruin', 'Vendetta', 'Prism']
def carry_of(f):
    ts = [k[7:] for k in f if k.startswith('earned_')]
    for c in CAR:
        if c in ts: return c
for side in ('live_opp', 'spar_opp'):
    X = []; Y = []
    for r in rows:
        f = r[side]; c = carry_of(f)
        if not c: continue
        tot = f['earned']; share = f['earned_' + c] / max(1, tot)
        X.append((tot, share)); Y.append(f['win'])
    X = np.array(X); Y = np.array(Y)
    Z = np.column_stack([np.ones(len(X)), (X[:, 0] - X[:, 0].mean()) / 100, (X[:, 1] - X[:, 1].mean()) * 10])
    b = np.linalg.lstsq(Z, Y, rcond=None)[0]; res = Y - Z @ b; cov = np.linalg.inv(Z.T @ Z) * res.var()
    se = np.sqrt(np.diag(cov))
    print(side, len(Y), 'mean share %.3f' % X[:, 1].mean(), 'LPM per 100 gold %.3f (se %.3f)' % (b[1], se[1]), '| per +0.1 carry share %.3f (se %.3f)' % (b[2], se[2]))
