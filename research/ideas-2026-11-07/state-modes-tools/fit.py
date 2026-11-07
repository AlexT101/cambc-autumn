# Intent-to-treat fit of the state-mode factorial: score ~ map-side control + per-cell level dummies.
# usage: fit.py KEYS.json BATCH_DIR[,BATCH_DIR..] [--mirror MIRROR_BATCH] [--json OUT]
import json, os, sys, argparse
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from draws import levels

STATES = ['even', 'ahead_solid', 'ahead_fragile', 'behind_soft', 'behind_deep']
KNOBS = ['retreat', 'recall', 'bank', 'gold']
if '--pass2' in sys.argv:
    sys.argv.remove('--pass2')
    STATES = ['even', 'ahead', 'behind']
    KNOBS = ['fight_risk', 'kill_value', 'bank', 'shop', 'camp']
S, K = len(STATES), len(KNOBS)

def load(batch):
    r = json.load(open(os.path.join(batch, 'results.json')))
    for m in r['matches'] if isinstance(r, dict) else r:
        if m.get('winner') is None and 'error' in json.dumps(m).lower():
            continue
        name = os.path.basename(m['map']).replace('.map26a', '')
        cand_a = m['order'][0] == 0
        w = m.get('winner')
        y = 0.5 if w is None else (1.0 if w == 0 else 0.0)
        yield name, cand_a, y, m.get('rounds')

ap = argparse.ArgumentParser()
ap.add_argument('keys'); ap.add_argument('batches'); ap.add_argument('--mirror'); ap.add_argument('--json')
a = ap.parse_args()
keys = {k['map']: k for k in json.load(open(a.keys))}
mirror = {}
if a.mirror:
    for name, b0_a, y, _ in load(a.mirror):  # bot 0 = oc-base19; a win for side A
        mirror[name] = y if b0_a else 1 - y
rows = []
for b in a.batches.split(','):
    for name, cand_a, y, rounds in load(b):
        if name not in keys: continue
        L = levels(keys[name], cand_a, S=S, K=K)
        c = mirror.get(name)
        side_ctrl = None if c is None else (c if cand_a else 1 - c)
        rows.append((name, cand_a, y, L, side_ctrl))
n = len(rows)
y = np.array([r[2] for r in rows])
print(f'games {n}, cand score {y.mean():.4f} +- {1.96 * y.std() / np.sqrt(n):.4f}')
use_ctrl = a.mirror is not None and all(r[4] is not None for r in rows)
cols, names = [np.ones(n)], ['const']
if use_ctrl:
    cols.append(np.array([r[4] for r in rows]) - 0.5); names.append('mirror_side_win')
for s in range(S):
    for k in range(K):
        lv = np.array([r[3][s][k] for r in rows])
        for v in (-1, 1):
            cols.append((lv == v).astype(float)); names.append(f'{STATES[s]}.{KNOBS[k]}{v:+d}')
X = np.stack(cols, 1)
beta, *_ = np.linalg.lstsq(X, y, rcond=None)
res = y - X @ beta
# Cluster-robust (by map) sandwich.
groups = {}
for i, r in enumerate(rows): groups.setdefault(r[0], []).append(i)
XtXi = np.linalg.inv(X.T @ X)
meat = np.zeros((X.shape[1], X.shape[1]))
for idx in groups.values():
    g = X[idx].T @ res[idx]; meat += np.outer(g, g)
V = XtXi @ meat @ XtXi
se = np.sqrt(np.diag(V))
print(f'R2 {1 - res.var() / y.var():.4f}  maps {len(groups)}  control {use_ctrl}')
out = {}
for i, nm in enumerate(names):
    out[nm] = (beta[i], se[i])
print(f"{'cell':24s} {'-1 vs 0':>16s} {'+1 vs 0':>16s} {'+1 vs -1':>16s}  best")
policy = {}
for s in range(S):
    for k in range(K):
        b = f'{STATES[s]}.{KNOBS[k]}'
        im, ip = names.index(b + '-1'), names.index(b + '+1')
        d = beta[ip] - beta[im]; sd = np.sqrt(V[ip, ip] + V[im, im] - 2 * V[ip, im])
        best = max([(0, 0.0), (-1, beta[im]), (1, beta[ip])], key=lambda t: t[1])
        policy[b] = best[0]
        print(f'{b:24s} {100*beta[im]:+6.2f} ({100*se[im]:4.2f}) {100*beta[ip]:+6.2f} ({100*se[ip]:4.2f}) {100*d:+6.2f} ({100*sd:4.2f})  {best[0]:+d} {100*best[1]:+.2f}')
if a.json:
    json.dump({'names': names, 'beta': beta.tolist(), 'V': V.tolist(), 'n': n}, open(a.json, 'w'))
