# Classifier two-sample test: can a model tell the ladder maps from generated ones on all features jointly?
#   python3 research/ideas-2026-11-12/ladderv3/c2st.py ladder=ladder170.jsonl v2=v2.jsonl v3=v3.jsonl [--reps N]
# Per-map KS tests (compare.py) check one feature at a time; this catches gaps in how features combine. Each rep draws
# as many generated maps as there are ladder maps, fits on 5 folds and scores out-of-fold AUC. The null is the same
# fit on two disjoint draws from one generated set, so a set that matches the ladder scores like the null.
import json, sys, os, collections
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import roc_auc_score

REPS = 20
if '--reps' in sys.argv:
    i = sys.argv.index('--reps'); REPS = int(sys.argv[i + 1]); del sys.argv[i:i + 2]
SETS = {}
for a in sys.argv[1:]:
    n, f = a.split('=', 1)
    SETS[n] = [json.loads(l) for l in open(f) if l.strip()]
# compare.py's module body runs a report on its own arguments: take only its definitions, which end before 'D = '.
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../mapgen-calib3-tools/compare.py')).read()
compare = type(sys)('compare'); compare.__dict__.update(collections=collections, np=np)
exec(src[src.index('MON = '):src.index('\nD = ')], compare.__dict__)

SKIP = ('sq_', 'pr_')


def feats(r):
    d, b, _, _ = compare.derive(r)
    x = {k: (-1.0 if v is None else float(v)) for k, v in d.items()}
    x.update({k: float(v) for k, v in b.items()})
    for k, v in r['f'].items():
        if k.startswith(SKIP) or isinstance(v, (dict, list)): continue
        x['f.' + k] = -1.0 if v is None else float(v)
    return x


M = {s: [feats(r) for r in rows] for s, rows in SETS.items()}
REF = list(SETS)[0]
KEYS = sorted(set.intersection(*(set(m[0]) for m in M.values())))
A = {s: np.array([[m[k] for k in KEYS] for m in rows]) for s, rows in M.items()}
n = len(A[REF])
MODELS = {
    'forest': lambda: RandomForestClassifier(n_estimators=300, min_samples_leaf=3, n_jobs=-1, random_state=0),
    'logistic': lambda: make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=2000)),
}


def auc(X0, X1, mk, seed, imp=None):
    X = np.vstack([X0, X1]); y = np.r_[np.zeros(len(X0)), np.ones(len(X1))]
    p = cross_val_predict(mk(), X, y, cv=StratifiedKFold(5, shuffle=True, random_state=seed), method='predict_proba')[:, 1]
    if imp is not None:
        m = mk().fit(X, y)
        if hasattr(m, 'feature_importances_'): imp += m.feature_importances_
    return roc_auc_score(y, p)


out = {}
for s in [k for k in A if k != REF]:
    G = A[s]
    for mn, mk in MODELS.items():
        rng = np.random.default_rng(1); real, null = [], []
        imp = np.zeros(len(KEYS))
        for i in range(REPS):
            idx = rng.permutation(len(G))
            real.append(auc(A[REF], G[idx[:n]], mk, i, imp if mn == 'forest' else None))
            null.append(auc(G[idx[n:2 * n]], G[idx[2 * n:3 * n]], mk, i))
        real, null = np.array(real), np.array(null)
        out[(s, mn)] = (real, null)
        print(f'{s:8s} {mn:9s} AUC {real.mean():.3f} (sd {real.std():.3f})   null {null.mean():.3f} (sd {null.std():.3f})', flush=True)
        if mn == 'forest':
            top = np.argsort(-imp)[:12]
            print('   top:', ', '.join(f'{KEYS[j]} {imp[j] / REPS:.3f}' for j in top), flush=True)
print(f'features {len(KEYS)}, ladder maps {n}, reps {REPS}')
