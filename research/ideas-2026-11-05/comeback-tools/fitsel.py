#!/usr/bin/env python3
"""fitsel.py ROWS.json [ARMS]: the learned selector (ii) from the random gambit logger. Outcome model: logistic regression
on the cook state and map features with arm interactions; the policy takes the arm of the highest predicted comeback.
Its value is estimated off-policy (inverse propensity, the logger's arms being uniform) on held-out maps (5-fold by
map), against the normal arm and each single arm on the same rows. ARMS: comma list of masks to choose among."""
import json, sys, glob, os, math
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold

rows = json.load(open(sys.argv[1]))
arms = [int(a) for a in sys.argv[2].split(',')] if len(sys.argv) > 2 else sorted({r['mask'] for r in rows})
rows = [r for r in rows if r['mask'] in arms]
meta = {}
for ix in glob.glob('maps/suites/fresh/fresh-5443*/index.json'):
    for m in json.load(open(ix))['maps']:
        meta[m['file'].replace('.map26a', '')] = m['metrics']
MK = ['area', 'altars', 'groups_side', 'gems_side', 'gold_side', 'spawn_dist', 'contested_share', 'bushes', 'picks',
      'walls', 'holes', 'camp_density', 'cluster_share', 'monoliths']

def feats(r):
    m = meta.get(r['map'], {})
    need = (1000 - r['us']) / max(1, 1000 - r['them'])
    return [r['round'] / 1000, (r['them'] - r['us']) / 300, math.log(max(need, 0.1)), r['us'] / 1000, r['them'] / 1000,
            1.0 if r['cand_a'] else 0.0] + [float(m.get(k) or 0) for k in MK]

X = np.array([feats(r) for r in rows]); X = (X - X.mean(0)) / (X.std(0) + 1e-9)
A = np.array([arms.index(r['mask']) for r in rows]); Y = np.array([r['won'] for r in rows]); G = [r['map'] for r in rows]
K = len(arms)

def design(X, a):
    oh = np.zeros((len(X), K)); oh[np.arange(len(X)), a] = 1
    inter = (oh[:, :, None] * X[:, None, :]).reshape(len(X), -1)
    return np.hstack([X, oh, inter])

for C in (0.01, 0.03, 0.1):
    pick = np.zeros(len(rows), int)
    for tr, te in GroupKFold(5).split(X, Y, G):
        lr = LogisticRegression(C=C, max_iter=2000).fit(design(X[tr], A[tr]), Y[tr])
        P = np.stack([lr.predict_proba(design(X[te], np.full(len(te), k)))[:, 1] for k in range(K)], 1)
        pick[te] = P.argmax(1)
    # IPS on the uniform logger: the policy's value = mean of Y over rows where it agrees with the logged arm.
    hit = pick == A
    v = Y[hit].mean(); se = math.sqrt(v * (1 - v) / hit.sum())
    share = np.bincount(pick, minlength=K) / len(pick)
    print(f'C {C}: policy comeback {100 * v:.1f} ± {196 * se / 100 * 100:.1f} (n agree {hit.sum()}), picks ' +
          ', '.join(f'{arms[k]}:{100 * share[k]:.0f}%' for k in range(K)))
for k in range(K):
    y = Y[A == k]; print(f'  arm {arms[k]}: {100 * y.mean():.1f} ± {196 * math.sqrt(y.mean() * (1 - y.mean()) / len(y)):.1f} (n {len(y)})')
