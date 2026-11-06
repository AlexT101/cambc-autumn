# Misspecification check of the draft model (draftfeat).
#   gbm.py plain  OUTDIR [--extra]                 GBM from scratch on map features x compositions
#   gbm.py resid  OUTDIR LOGITDIR [--extra]        Newton-step GBM on the logistic's residuals (its per-fold logits)
# Same map-grouped folds as model.mjs (hash(key) % 5); scored on wins. Writes oof.f32 (out-of-fold logits) and gains.json.
import json, sys, time, os
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

D = os.path.dirname(os.path.abspath(__file__))
mode, out = sys.argv[1], sys.argv[2]
extra = '--extra' in sys.argv
opt = lambda k, d=None: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
si = opt('--set', '0')
fold_list = [int(x) for x in opt('--folds', '0,1,2,3,4').split(',')]
group = opt('--group', 'all')  # all | mapD (map features, picks, A-B) | comp (picks, A, B: no map)
os.makedirs(out, exist_ok=True)
z = np.load(f'{D}/games.npz')
mi, picks, A, B, win = z['mi'], z['picks'].astype(np.float32), z['A'].astype(np.float32), z['B'].astype(np.float32), z['win'].astype(np.float64)
MF, mfold, fnames = z['MF'], z['mfold'], list(z['fnames'])
nm = 26 + (len(fnames) - 26 if extra else 0)  # 25 model features + altars_raw (+ extras)
MF = MF[:, :nm]
fold = mfold[mi]
N = len(win)
CH = ['Ryth', 'Vesp', 'Vend', 'Cass', 'Stel', 'Pris', 'Marc', 'Will', 'Ren', 'Varg', 'Tavi', 'HoR']
names = fnames[:nm] + ['picks'] + [f'A_{c}' for c in CH] + [f'B_{c}' for c in CH] + [f'D_{c}' for c in CH]


def design(a, b, side=None):
    X = np.concatenate([MF[mi].astype(np.float32), picks[:, None], a, b, a - b], axis=1)
    return X if side is None else np.concatenate([X, np.full((N, 1), side, np.float32)], axis=1)


softplus = lambda x: np.logaddexp(0, x)
loss_of = lambda e, y: softplus(e) - y * e

if mode == 'plain':
    X, Xs = design(A, B, 1.0), design(B, A, -1.0)
    names = names + ['side']
else:
    X = design(A, B)
    ids = json.load(open(f'{sys.argv[3]}/rows_s{si}.json'))
    assert list(ids) == list(z['ids']), 'logit rows out of order'
    F0 = {k: np.fromfile(f'{sys.argv[3]}/logits_s{si}_f{k}.f32', dtype=np.float32).astype(np.float64) for k in fold_list}
    cols = list(range(len(names)))
    if group == 'mapD': cols = [i for i, n in enumerate(names) if not n.startswith(('A_', 'B_'))]
    if group == 'comp': cols = [i for i, n in enumerate(names) if n == 'picks' or n.startswith(('A_', 'B_', 'D_'))]
    X = X[:, cols]; names = [names[i] for i in cols]; nmap_feat = sum(1 for n in names if n in fnames)

oof = np.zeros(N, np.float32)
gains = np.zeros(len(names))
pair_gain = {}
res = {'mode': mode, 'extra': extra, 'folds': []}
if mode == 'plain': nmap_feat = nm
for k in fold_list:
    t0 = time.time()
    tr_all = np.flatnonzero(fold != k)
    te = np.flatnonzero(fold == k)
    rng = np.random.default_rng(100 + k)
    vmaps = rng.random(len(MF)) < 0.12
    val = tr_all[vmaps[mi[tr_all]]]
    tr = tr_all[~vmaps[mi[tr_all]]]
    if mode == 'plain':
        Xtr = np.concatenate([X[tr], Xs[tr]]); ytr = np.concatenate([win[tr], 1 - win[tr]])
        m = HistGradientBoostingClassifier(learning_rate=0.1, max_iter=3000, max_leaf_nodes=63, min_samples_leaf=200, l2_regularization=1.0,
                                           early_stopping=True, n_iter_no_change=30, random_state=k)
        m.fit(Xtr, ytr, X_val=X[val], y_val=win[val])
        e = m.decision_function(X[te]).astype(np.float64)
        lr = None
        base = None
    else:
        f0 = F0[k]
        p = 1 / (1 + np.exp(-f0))
        w = p * (1 - p)
        t = (win - p) / w
        m = HistGradientBoostingRegressor(learning_rate=0.1, max_iter=2000, max_leaf_nodes=31, min_samples_leaf=1000, l2_regularization=1.0,
                                          early_stopping=True, n_iter_no_change=30, random_state=k)
        m.fit(X[tr], t[tr], sample_weight=w[tr], X_val=X[val], y_val=t[val], sample_weight_val=w[val])
        hv = m.predict(X[val])
        nus = [0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5]
        lv = [loss_of(f0[val] + nu * hv, win[val]).mean() for nu in nus]
        lr = nus[int(np.argmin(lv))]
        e = f0[te] + lr * m.predict(X[te])
        base = loss_of(f0[te], win[te]).mean()
    oof[te] = e
    l = loss_of(e, win[te]).mean()
    # Split gains: per feature, and per (map feature ancestor, champion split) / (champion ancestor, map feature split).
    for pr in m._predictors:
        nodes = pr[0].nodes
        anc = {0: []}
        for i in range(len(nodes)):
            nd = nodes[i]
            if nd['is_leaf']: continue
            f = int(nd['feature_idx'])
            gains[f] += nd['gain']
            for a in set(anc[i]):
                lo, hi = sorted((a, f))
                if (lo < nmap_feat) != (hi < nmap_feat) or True:
                    pair_gain[(a, f)] = pair_gain.get((a, f), 0) + nd['gain']
            anc[int(nd['left'])] = anc[i] + [f]
            anc[int(nd['right'])] = anc[i] + [f]
    fr = {'fold': k, 'n': len(te), 'loss': l, 'base': base, 'nu': lr, 'iters': m.n_iter_, 'sec': time.time() - t0}
    res['folds'].append(fr)
    print(json.dumps(fr), flush=True)
oof.tofile(f'{out}/oof.f32')
Nf = sum(f['n'] for f in res['folds'])
tot = sum(f['loss'] * f['n'] for f in res['folds']) / Nf
res['total'] = tot
if mode == 'resid': res['base_total'] = sum(f['base'] * f['n'] for f in res['folds']) / Nf
res['gain'] = sorted([(names[i], float(g)) for i, g in enumerate(gains)], key=lambda x: -x[1])
res['pair_gain'] = sorted([(names[a], names[b], float(g)) for (a, b), g in pair_gain.items()], key=lambda x: -x[2])[:200]
json.dump(res, open(f'{out}/gbm.json', 'w'), indent=1)
print('total', tot, res.get('base_total'))
print('top gains', res['gain'][:25])
print('top pairs', res['pair_gain'][:40])
