"""Within-cell models of our win against the spar's live drafts. py fit.py LAB[,LAB2] [--feats a,b] [--lam ...]
Cells (map, side, opp, body) are fixed effects; terms: F92 score s, champion mains, champion x opp-champion, champion x map feature.
CV over maps: held-out cells refit their own FE with the other terms fixed."""
import sys, json, numpy as np, argparse, collections
sys.path.insert(0, '/home/ubuntu/tmp-offload/draftlive/scripts'); import load
ap = argparse.ArgumentParser(); ap.add_argument('labs'); ap.add_argument('--feats', default='')
ap.add_argument('--folds', type=int, default=8); ap.add_argument('--out', default='')
a = ap.parse_args()
R = [r for L in a.labs.split(',') for r in load.rows(L) if r['k'] >= 0]
CHN = ['Ryth','Vesp','Vend','C&I','Stel','Pris','Marc','Will','Ren','Varg','Tavi','HoR']
import sys as _s; _s.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-08/spar-tools'); import live
LD = live.drafts(); FULL = ["Ryth","Vesper Vale","Vendetta","Cassi & Issac","Stellar","Prism","Marcella","Willow","Ren","Varg","Tavi","Heart of Ruin"]
F92 = {m['name']: m for m in json.load(open(load.W / 'f92scores.json'))}
model = json.load(open('/home/ubuntu/tmp-offload/draft7/f92/model.json'))
feats = [f for f in a.feats.split(',') if f]
fidx = [model['features'].index(f) for f in feats]
cells = sorted({(r['map'], r['side'], r['opp'], r['body']) for r in R}); ci = {c: i for i, c in enumerate(cells)}
maps = sorted({r['map'] for r in R})
def opp_comp(r): return [FULL.index(p) for p in LD[(r['map'], r['side'], r['opp'])][0]]
# design blocks
def build(R):
    n = len(R); blocks = {}
    S = np.array([r['s'] for r in R]); blocks['s'] = S[:, None]
    X = np.zeros((n, 12))
    for i, r in enumerate(R): X[i, list(r['team'])] = 1
    # within pick count, the mains are identified only as differences: centre by pick count via cell FE (fine)
    blocks['main'] = X
    C = np.zeros((n, 144))
    for i, r in enumerate(R):
        for d in opp_comp(r): C[i, [c * 12 + d for c in r['team']]] = 1
    blocks['ctr'] = C
    if fidx:
        Z = np.array([[F92[r['map']]['z'][k] for k in fidx] for r in R])
        blocks['feat'] = (X[:, :, None] * Z[:, None, :]).reshape(n, -1)
    return blocks
B = build(R); y = np.array([r['win'] for r in R], float)
cid = np.array([ci[(r['map'], r['side'], r['opp'], r['body'])] for r in R]); mid = np.array([maps.index(r['map']) for r in R])
def fit(cols, lams, rows, fe_only_theta=None, iters=40):
    X = np.hstack([B[c] for c in cols])[rows] if cols else np.zeros((len(rows), 0))
    lam = np.concatenate([np.full(B[c].shape[1], l) for c, l in zip(cols, lams)]) if cols else np.zeros(0)
    cc = cid[rows]; uc, cinv = np.unique(cc, return_inverse=True); nc = len(uc); yy = y[rows]
    th = np.zeros(X.shape[1]) if fe_only_theta is None else fe_only_theta.copy(); fe = np.zeros(nc)
    for it in range(iters):
        z = X @ th + fe[cinv]; p = 1 / (1 + np.exp(-z)); w = p * (1 - p); g = yy - p
        # FE Newton (diagonal), small ridge 0.01
        gf = np.bincount(cinv, g, nc) - 0.01 * fe; hf = np.bincount(cinv, w, nc) + 0.01
        if fe_only_theta is None and X.shape[1]:
            # Schur complement: eliminate FE
            Xw = X * w[:, None]
            Hxx = X.T @ Xw + np.diag(lam)
            Hxf = np.zeros((X.shape[1], nc)); np.add.at(Hxf.T, cinv, Xw)
            gx = X.T @ g - lam * th
            Hs = Hxx - (Hxf / hf) @ Hxf.T; gs = gx - Hxf @ (gf / hf)
            dth = np.linalg.solve(Hs, gs); dfe = (gf - Hxf.T @ dth) / hf
            th += dth; fe += dfe
            if np.abs(dth).max() < 1e-7 and np.abs(dfe).max() < 1e-7: break
        else:
            fe += gf / hf
            if np.abs(gf / hf).max() < 1e-8: break
    z = X @ th + fe[cinv]; p = 1 / (1 + np.exp(-z))
    return th, p
def sel(P, cols, lams):
    """Cross-fitted choice: per map, the listed team with the best held-out predicted logit (cell FE cancel within a cell,
    so the mean predicted logit over the map's cells ranks teams); its realized win against the base team's (k = 0)."""
    z = np.log(P / (1 - P)); by = collections.defaultdict(list)
    for i, r in enumerate(R): by[(r['map'], r['k'])].append(i)
    ch = []; bs = []; same = 0
    for m in maps:
        ks = [k for (mm, k) in by if mm == m]
        # within-cell centred predictions
        best = max(ks, key=lambda k: np.mean([z[i] - cfe[cid[i]] for i in by[(m, k)]]))
        same += best == 0
        ch += [y[i] for i in by[(m, best)]]; bs += [y[i] for i in by[(m, 0)]]
    d = np.mean(ch) - np.mean(bs); se = np.sqrt((np.var(ch) + np.var(bs)) / len(ch))
    print(f'    select: same as base on {same}/{len(maps)} maps; chosen {np.mean(ch):.3f} vs base {np.mean(bs):.3f} ({d * 100:+.1f} ±{se * 100:.1f} pts, n {len(ch)})')
def cv(cols, lams, K=a.folds, seed=1270011):
    global cfe
    rng = np.random.default_rng(seed); fold = rng.permutation(len(maps)) % K
    ll = 0; P = np.zeros(len(R))
    for k in range(K):
        tr = np.where(fold[mid] != k)[0]; te = np.where(fold[mid] == k)[0]
        th, _ = fit(cols, lams, tr)
        _, p = fit(cols, lams, te, fe_only_theta=th)
        P[te] = p
    P = np.clip(P, 1e-4, 1 - 1e-4)
    zz = np.log(P / (1 - P)); cfe = np.bincount(cid, zz, len(cells)) / np.maximum(1, np.bincount(cid, None, len(cells)))
    ll = -np.mean(y * np.log(P) + (1 - y) * np.log(1 - P))
    return ll, P, fold
if __name__ == '__main__':
    print(len(R), 'games', len(cells), 'cells; win', y.mean().round(4))
    base = cv([], [])[0]
    import itertools; print('FE only', round(base, 5))
    for cols, lams in [(['s'], [1e-3]), (['main'], [10]), (['main'], [30]), (['s', 'main'], [1e-3, 10]), (['s', 'main'], [1e-3, 30]),
                       (['s', 'main', 'ctr'], [1e-3, 10, 30]), (['s', 'main', 'ctr'], [1e-3, 10, 100])] + \
                      ([(['s', 'main', 'feat'], [1e-3, 10, l]) for l in (30, 100, 300)] if fidx else []):
        ll, P, fold = cv(cols, lams); th, _ = fit(cols, lams, np.arange(len(R)))
        sel(P, cols, lams)
        print(cols, lams, 'cv', round(ll, 5), f'({(ll - base) * 1e4:+.1f}e-4)', 'beta_s' if 's' in cols else '', round(th[0], 3) if 's' in cols else '')
        if cols == ['s', 'main']:
            m = th[1:13]; m = m - m.mean(); print('   mains', ' '.join(f'{CHN[c]} {m[c]:+.2f}' for c in np.argsort(-m)))
