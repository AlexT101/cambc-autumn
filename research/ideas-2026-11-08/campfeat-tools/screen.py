# Screen of new map features against a fitted draft model: the model's logits are a fixed offset, and only
# champion x new-feature weights are fitted (ridge LAM, per pick count toward a pooled fit), scored by the lab's
# map-grouped 5-fold CV. Paired per-map SE on the loss difference.
#   python screen.py PRED.txt MAPS.jsonl [LAM]      (PRED: model.mjs predict / cvdump-style rows)
import sys, json, numpy as np
pred, mapsf = sys.argv[1], sys.argv[2]; LAM = float(sys.argv[3]) if len(sys.argv) > 3 else 320
NEW = [('gem_groups', 'log1p'), ('one_gem_group', None), ('gold_groups', 'log1p'), ('one_gold_group', None),
       ('hv_compact', None), ('hv_rate', None), ('hv_val', 'log1p'), ('hv_share', None)]
SETS = {'all8': [0, 1, 2, 3, 4, 5, 6, 7], 'counts4': [0, 1, 2, 3], 'gem2': [0, 1], 'gold2': [2, 3], 'hv4': [4, 5, 6, 7],
        **{n: [k] for k, (n, _) in enumerate(NEW)}}
if len(sys.argv) > 4: SETS = {k: v for k, v in SETS.items() if k in sys.argv[4].split(',')}
# EXTRA=name:tf,name:tf...  a further set 'extra' of other maps.jsonl features (a positive control on a smaller model)
if len(sys.argv) > 5:
    ex = [(a.split(':')[0], (a.split(':') + [''])[1] or None) for a in sys.argv[5].split(',')]
    SETS['extra'] = list(range(len(NEW), len(NEW) + len(ex))); NEW = NEW + ex
raw = {}
for l in open(mapsf):
    r = json.loads(l)
    if r['picks'] not in (3, 4, 5): continue
    raw[r['key']] = [np.nan if r['f'].get(n) is None else np.log1p(max(r['f'][n], 0)) if tf == 'log1p' else np.log(max(r['f'][n], 1)) if tf == 'log' else r['f'][n] for n, tf in NEW]
keys = list(raw); Z = np.array([raw[k] for k in keys], float)
mu, sd = np.nanmean(Z, 0), np.nanstd(Z, 0); Z = np.nan_to_num(np.clip((Z - mu) / np.where(sd > 0, sd, 1), -4, 4)); zi = {k: i for i, k in enumerate(keys)}
K, P, A, B, W, E, F = [], [], [], [], [], [], []
for l in open(pred):
    x = l.split()
    K.append(zi[x[0]]); P.append(int(x[1])); W.append(int(x[2])); E.append(float(x[3]))
    a = np.zeros(12); a[[int(c) for c in x[4].split(',')]] += 1; a[[int(c) for c in x[5].split(',')]] -= 1; A.append(a); F.append(int(x[6]))
K, P, W, E, F, S = map(np.array, (K, P, W, E, F, A)); S = S.astype(np.float32)
print(f'{len(K)} games, {len(set(K.tolist()))} maps', flush=True)
def design(cols): return (S[:, :, None] * Z[K][:, None, cols].astype(np.float32)).reshape(len(K), -1)
def newton(X, y, off, lam, th0):
    th = th0.copy()
    for _ in range(30):
        e = off + X @ th; p = 1 / (1 + np.exp(-e)); g = X.T @ (p - y) + lam * (th - th0)
        H = (X * (p * (1 - p))[:, None]).T @ X + lam * np.eye(len(th)); d = np.linalg.solve(H, g); th -= d
        if np.abs(d).max() < 1e-7: break
    return th
def fit(X, m):
    th0 = newton(X[m], W[m], E[m], LAM, np.zeros(X.shape[1])); out = {}
    for p in (3, 4, 5):
        mm = m & (P == p); out[p] = newton(X[mm], W[mm], E[mm], LAM, th0)
    return out
def loss(e, y): return np.logaddexp(0, e) - y * e
base = loss(E, W)
for name, cols in SETS.items():
    X = design(cols); e = E.copy()
    for k in range(5):
        th = fit(X, F != k)
        for p in (3, 4, 5):
            t = (F == k) & (P == p); e[t] = E[t] + X[t] @ th[p]
    d = loss(e, W) - base
    pm = np.bincount(K, d, minlength=len(keys)); used = np.bincount(K, minlength=len(keys)) > 0
    se = pm[used].std() * np.sqrt(used.sum()) / len(K)
    print(f'{name:14s} cv loss diff {1e4 * d.mean():+7.2f} (1e-4) se {1e4 * se:.2f}', flush=True)
