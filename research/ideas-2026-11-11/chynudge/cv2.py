"""Is the residual opponent-specific? Transfer and pooled fits of fit.py's u + w blocks (our champion, our champion x
map feature) over the Fish, Mite and ocean games: py cv2.py [KW]"""
import os, sys, numpy as np, fit as F
W = F.W; NC = 12
def newton(X, y, off, pen, iters=25, chunk=40000):
    b = np.zeros(X.shape[1])
    for _ in range(iters):
        g = pen * b; H = np.diag(pen + 1e-8)
        for i in range(0, len(y), chunk):
            x = X[i:i + chunk].astype(np.float64); pr = 1 / (1 + np.exp(-(off[i:i + chunk] + x @ b)))
            g += x.T @ (pr - y[i:i + chunk]); H += (x * (pr * (1 - pr))[:, None]).T @ x
        step = np.linalg.solve(H, g); b -= step
        if np.abs(step).max() < 1e-7: break
    return b
def loss(X, y, off, b, chunk=40000):
    t = 0.0
    for i in range(0, len(y), chunk):
        e = off[i:i + chunk] + X[i:i + chunk].astype(np.float64) @ b; t += float(np.sum(np.logaddexp(0, e) - y[i:i + chunk] * e))
    return t / len(y)
if __name__ == '__main__':
    F.KW = int(sys.argv[1]) if len(sys.argv) > 1 else 25
    G = np.load(f'{W}/games.npz'); Z = G['Z']; fold = np.arange(len(Z)) * 2654435761 % 5
    R = {n: F.rows(G, o) for n, o in F.BOT.items()}; names = list(R)
    for lam in map(float, sys.argv[2:]):
        X = {}; 
        for n in names: X[n], pen, _ = F.design(R[n], Z, {'u': 16, 'w': lam})
        f = {n: fold[R[n]['key']] for n in names}
        # own: fitted on this bot's other folds. other: on the other two bots' other folds. pooled: all three bots' other folds.
        res = {n: {'own': [], 'other': [], 'pooled': []} for n in names}
        for k in range(5):
            b = {}
            for n in names:
                tr = f[n] != k; b[n] = newton(X[n][tr], R[n]['y'][tr], R[n]['off'][tr], pen)
            def stack(ns):
                return (np.vstack([X[n][f[n] != k] for n in ns]), np.concatenate([R[n]['y'][f[n] != k] for n in ns]), np.concatenate([R[n]['off'][f[n] != k] for n in ns]))
            bp = newton(*stack(names), pen)
            for n in names:
                te = f[n] == k; tr = ~te; Xt, yt, ot = X[n][te], R[n]['y'][te], R[n]['off'][te]
                b0 = newton(X[n][tr][:, :1], R[n]['y'][tr], R[n]['off'][tr], pen[:1]); base = loss(Xt[:, :1], yt, ot, b0)
                bo = newton(*stack([m for m in names if m != n]), pen)
                # the intercept is the bot's own strength offset: refit it alone on the bot's training folds
                def with_icpt(bb):
                    o2 = R[n]['off'] + X[n][:, 1:].astype(np.float64) @ bb[1:]
                    i0 = newton(X[n][tr][:, :1], R[n]['y'][tr], o2[tr], pen[:1]); return loss(Xt[:, :1], yt, o2[te], i0)
                res[n]['own'].append(1e4 * (loss(Xt, yt, ot, b[n]) - base)); res[n]['other'].append(1e4 * (with_icpt(bo) - base)); res[n]['pooled'].append(1e4 * (with_icpt(bp) - base))
        print(f'w penalty {lam}, {F.KW} features: held-out loss change (1e-4) against the model alone')
        for n in names: print(f'  {n:6s} ' + '  '.join(f'{kind} {np.mean(v):+7.2f}' for kind, v in res[n].items()), flush=True)
