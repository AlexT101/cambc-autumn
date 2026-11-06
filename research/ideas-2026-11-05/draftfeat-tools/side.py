# side.py CVDIR SET: out-of-fold gain from a side term depending on the map (offset logistic on the set's logits).
import sys, json, numpy as np
D = '/tmp/claude-1000/-home-ubuntu-cambc-autumn/3650a530-f591-417e-a0c5-31524a1e3260/scratchpad/df'
cv, si = sys.argv[1], sys.argv[2]
z = np.load(f'{D}/games.npz'); mi = z['mi']; fold = z['mfold'][mi]; y = z['win'].astype(float); picks = z['picks']
s = json.load(open(f'{cv}/set{si}.json')); mean, sd = np.array(s['mean'][:25]), np.array(s['sd'][:25])
Z = (z['MF'][:, :25] - mean) / sd; Z = np.where(np.isfinite(Z), np.clip(Z, -4, 4), 0)
basis = {'linear': Z, 'quad': np.concatenate([Z, Z ** 2] + [Z[:, [i]] * Z[:, i + 1:] for i in range(25)], axis=1)}
L = lambda e, m: (np.logaddexp(0, e[m]) - y[m] * e[m]).mean()
for name, M in basis.items():
    X = np.concatenate([np.ones((len(M), 1)), M], axis=1)
    tot0 = tot1 = 0; per = []
    for k in range(5):
        f0 = np.fromfile(f'{cv}/logits_s{si}_f{k}.f32', dtype=np.float32).astype(float)
        e = f0.copy()
        for p in (3, 4, 5):
            tr = (fold != k) & (picks == p); te = (fold == k) & (picks == p)
            # map-level sufficient statistics would be cheaper; rows are fine at this size
            beta = np.zeros(X.shape[1]); Xm = X[mi[tr]]
            for it in range(8):
                pr = 1 / (1 + np.exp(-(f0[tr] + Xm @ beta)))
                g = Xm.T @ (pr - y[tr]) + 10.0 * beta; H = (Xm * (pr * (1 - pr))[:, None]).T @ Xm + 10.0 * np.eye(len(beta))
                beta -= np.linalg.solve(H, g)
            e[te] = f0[te] + X[mi[te]] @ beta
        te = fold == k
        per.append((L(e, te) - L(f0, te)) * 1e4)
    print(name, 'side x map change x1e4 per fold', [round(v, 2) for v in per], 'mean', round(np.mean(per), 2))
