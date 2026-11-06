"""Iteration-level heterogeneity of the SPSA gradient: diff_kp = sum_i D_kpi 2 c_ki (g_i[epoch] + sum_j W_ij zbar_kj)."""
import json, os, sys
import numpy as np
from pathlib import Path
W = Path(os.environ.get('MAPCOND_DIR', '.'))
F = json.load(open(W / 'features.json'))
FEATS = ['log_area', 'picks', 'sym_rot', 'spawn_dist', 'camp_density', 'log_gems', 'big_share', 'contested', 'altars']
run = sys.argv[1]; E = int(sys.argv[2]) if len(sys.argv) > 2 else 4; NPERM = int(__import__('os').environ.get('NPERM', 100))
d = json.load(open(W / f'{run}-iters.json'))
names, its = d['names'], d['iters']
K, P, N, J = len(its), len(its[0]['diffs']), len(names), len(FEATS)
# standardise over the games actually played (each map once per opponent: map-weighted)
allm = [Path(m).name for it in its for m in it['maps']]
Z = np.array([[F[m][f] for f in FEATS] for m in allm])
mu, sd = Z.mean(0), Z.std(0)
zb = np.array([((np.array([[F[Path(m).name][f] for f in FEATS] for m in it['maps']]) - mu) / sd).mean(0) for it in its])
print(f'{run}: {K} iterations x {P} pairs, {N} constants, {J} features; SD of an iteration mean (per-map SD 1):',
      ' '.join(f'{f}={s:.3f}' for f, s in zip(FEATS, zb.std(0))))
D = np.array([it['deltas'] for it in its], float)            # K,P,N
C = np.array([it['cn'] for it in its])[:, None, :] * 2        # K,1,N
y = np.array([it['diffs'] for it in its]).reshape(-1)        # K*P
B = D * C                                                    # K,P,N
ep = np.minimum((np.arange(K) * E) // K, E - 1)
def design(zb):
    main = np.zeros((K, P, N, E)); main[np.arange(K), :, :, ep] = B[np.arange(K)]
    inter = B[..., None] * zb[:, None, None, :]              # K,P,N,J
    return np.concatenate([main.reshape(K * P, N * E), inter.reshape(K * P, N * J)], 1)
def fit(X):
    A = X.T @ X
    Ai = np.linalg.inv(A)
    beta = Ai @ (X.T @ y)
    r = y - X @ beta
    s2 = r @ r / (len(y) - X.shape[1])
    return beta, np.sqrt(s2 * np.diag(Ai)), s2
X = design(zb)
beta, se, s2 = fit(X)
gm = beta[:N * E].reshape(N, E); gse = se[:N * E].reshape(N, E)
Wt = beta[N * E:].reshape(N, J); Wse = se[N * E:].reshape(N, J); T = Wt / Wse
print(f'residual SD of a pair difference {np.sqrt(s2):.4f}; raw SD {y.std():.4f}')
print(f'main effects, epoch {E-1} (last): |t|>2 for {(np.abs(gm[:, -1] / gse[:, -1]) > 2).sum()} of {N}; median SE g {np.median(gse):.3f}; median SE W {np.median(Wse):.3f}')
rng = np.random.default_rng(1)
null_counts2, null_counts3, null_max, null_ss = [], [], [], []
for _ in range(NPERM):
    b, s, _ = fit(design(zb[rng.permutation(K)]))
    t = np.abs(b[N * E:] / s[N * E:])
    null_counts2.append((t > 2).sum()); null_counts3.append((t > 3).sum()); null_max.append(t.max()); null_ss.append((t ** 2).sum())
nc2, nc3, nm = map(np.array, (null_counts2, null_counts3, null_max))
print(f'interactions |t|>2: {(np.abs(T) > 2).sum()} (null mean {nc2.mean():.1f}, 95% {np.percentile(nc2, 95):.0f}); '
      f'|t|>3: {(np.abs(T) > 3).sum()} (null mean {nc3.mean():.2f}, 95% {np.percentile(nc3, 95):.0f}); max |t| {np.abs(T).max():.2f} (null 95% {np.percentile(nm, 95):.2f})')
nss = np.array(null_ss); print(f'omnibus sum t^2 {np.sum(T ** 2):.0f} (null mean {nss.mean():.0f}, 95% {np.percentile(nss, 95):.0f}, p {(1 + (nss >= np.sum(T ** 2)).sum()) / (1 + len(nss)):.3f})')
print('per feature, count |t|>2:', ' '.join(f'{f}={(np.abs(T[:, j]) > 2).sum()}' for j, f in enumerate(FEATS)))
idx = np.dstack(np.unravel_index(np.argsort(-np.abs(T).ravel()), T.shape))[0][:12]
for i, j in idx:
    print(f'  {names[i]:30s} x {FEATS[j]:13s} W {Wt[i, j]:+.3f} +- {Wse[i, j]:.3f} (t {T[i, j]:+.2f}); g last epoch {gm[i, -1]:+.3f} +- {gse[i, -1]:.3f}')
# debiased sum of squares of W per constant (sum over features of W^2 - SE^2), for the prize
json.dump({'names': names, 'feats': FEATS, 'W': Wt.tolist(), 'Wse': Wse.tolist(), 'g': gm.tolist(), 'gse': gse.tolist(),
           'zb_sd': zb.std(0).tolist(), 'null_t2': nc2.tolist(), 'null_max': nm.tolist()}, open(W / f'{run}-het.json', 'w'))
