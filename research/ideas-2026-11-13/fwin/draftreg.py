"""Opponent champions against Fish r8: logistic regression of the opponent's win on its picks, with team and map
fixed effects (all rows since 11-12 14:00 with Fish's r8 draft).   py draftreg.py"""
import json, numpy as np, collections, sys
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/fishr8')
from meta import CH
R = [r for r in json.load(open('/home/ubuntu/tmp-offload/fwin/rows.json')) if r['r8'] and r['f_win'] is not None]
for r in R: r['team'] = 'us' if r['opp'] in ('stellar best girl', 'prism best fih') else r['opp']
teams = [t for t, n in collections.Counter(r['team'] for r in R).items() if n >= 30]
R = [r for r in R if r['team'] in teams]
maps = sorted(set(r['map'] for r in R))
def X(r):
    x = [1.0 if c in r['op_picks'] else 0.0 for c in range(12)]
    x += [1.0 if r['team'] == t else 0.0 for t in teams[1:]]
    x += [1.0 if (r['map'], r['f_side']) == m else 0.0 for m in [(m, s) for m in maps for s in 'ab']]
    return x
A = np.array([X(r) for r in R]); y = np.array([0.0 if r['f_win'] else 1.0 for r in R])
w = np.zeros(A.shape[1]); lam = 1.0
for it in range(60):   # Newton with an L2 ridge
    p = 1 / (1 + np.exp(-A @ w)); g = A.T @ (y - p) - lam * w
    H = A.T @ (A * (p * (1 - p))[:, None]) + lam * np.eye(len(w)); w += np.linalg.solve(H, g)
p = 1 / (1 + np.exp(-A @ w)); H = A.T @ (A * (p * (1 - p))[:, None]) + lam * np.eye(len(w)); se = np.sqrt(np.diag(np.linalg.inv(H)))
print(len(R), 'games,', len(teams), 'teams')
cnt = collections.Counter(c for r in R for c in r['op_picks'])
for c in np.argsort(-w[:12]):
    print(f'{CH[c]:10s} picked {cnt[c]:5d}  log-odds {w[c]:+.2f} ±{se[c]:.2f}')
