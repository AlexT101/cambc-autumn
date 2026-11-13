"""Against one opponent team: logistic regression of the other side's win on its picks, with team and cell (map,
opponent side) fixed effects; pick effects reported relative to the mean pick.   py draftopp.py ALL.tsv.gz"""
import gzip, json, sys, collections, numpy as np
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/fishr8')
from meta import CH
OPP = {'Fish': '1890540d-1ffc-4847-adbf-d0d08772f268', 'Mite': 'ee83f5e5-bcad-4923-86b4-b79ea6083d2e', 'BattleCats': '285f4eb5-e97f-4ea4-93c5-19e1590a1e5a', 'us': '547efb5b-57e5-4355-8501-3b331f506d62'}
rows = []
for l in gzip.open(sys.argv[1], 'rt'):
    f = l.rstrip('\n').split('\t')
    if len(f) != 11 or f[8] not in ('win', 'loss'): continue
    try: pa, pb = json.loads(f[9]), json.loads(f[10])
    except Exception: continue
    if not pa or not pb: continue
    rows.append(dict(map=f[3], ta=f[4], tb=f[5], aw=f[8] == 'win', pa=pa, pb=pb, kind=f[2]))
def fit(R, label):
    teams = sorted(t for t, n in collections.Counter(r['team'] for r in R).items() if n >= 30)
    R = [r for r in R if r['team'] in teams]
    cells = sorted(set(r['cell'] for r in R)); ci = {c: i for i, c in enumerate(cells)}
    A = np.zeros((len(R), 12 + len(teams) - 1 + len(cells)), dtype=np.float32); y = np.array([1.0 if r['win'] else 0.0 for r in R])
    for k, r in enumerate(R):
        for c in r['picks']: A[k, c] = 1
        ti = teams.index(r['team'])
        if ti: A[k, 12 + ti - 1] = 1
        A[k, 12 + len(teams) - 1 + ci[r['cell']]] = 1
    A = A.astype(np.float64); w = np.zeros(A.shape[1]); lam = 1.0
    for it in range(40):
        p = 1 / (1 + np.exp(-A @ w)); g = A.T @ (y - p) - lam * w
        H = A.T @ (A * (p * (1 - p))[:, None]) + lam * np.eye(len(w)); w += np.linalg.solve(H, g)
    se = np.sqrt(np.diag(np.linalg.inv(H))); base = np.mean(w[:12])
    cnt = collections.Counter(c for r in R for c in r['picks'])
    print(f'{label}: {len(R)} games, {len(teams)} teams, win {y.mean():.2f}')
    print('   ' + ' '.join(f'{CH[c]} {w[c]-base:+.2f}±{se[c]:.2f}({cnt[c]})' for c in np.argsort(-w[:12])))
for name, tid in OPP.items():
    R = []
    for r in rows:
        if r['ta'] == tid and r['tb'] != tid: R.append(dict(team=r['tb'], picks=r['pb'], win=not r['aw'], cell=(r['map'], 'a')))
        elif r['tb'] == tid and r['ta'] != tid: R.append(dict(team=r['ta'], picks=r['pa'], win=r['aw'], cell=(r['map'], 'b')))
    fit(R, f'against {name}')
