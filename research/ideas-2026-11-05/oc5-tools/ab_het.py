"""Per-map heterogeneity of held-out A/Bs (cand win - 0.5 per map) on the draft-time features, and the per-map gain
the SPSA interaction fit predicts for the tuned move: dx . (g + W z). Usage: ab_het.py HET.json AB_NAME..."""
import json, sys
from pathlib import Path
from collections import defaultdict
import numpy as np
ROOT = Path('/home/ubuntu/cambc-autumn')
H = json.load(open(sys.argv[1])); FEATS = H['feats']; mu, sd = np.array(H['mu']), np.array(H['sd'])
F = json.load(open('/home/ubuntu/tmp-offload/tune5/mc/features.json'))
cfg = json.load(open(ROOT / 'replays/tune/oc5/config.json')); st = json.load(open(ROOT / 'replays/tune/oc5/state.json'))
spec = json.load(open(ROOT / 'bots/archives/ocean_tune5/src/tune.json')); d = dict(spec['floats'] + spec['ints'])
names = [r['name'] for r in H['rows']]
dx = np.array([st['x'][n] - (d[n] - cfg['params'][n][0]) / (cfg['params'][n][1] - cfg['params'][n][0]) for n in names])
G = np.array([np.mean(r['g']) for r in H['rows']]); W = np.array([r['W'] for r in H['rows']])
rng = np.random.default_rng(1)
for ab in sys.argv[2:]:
    per = defaultdict(list)
    for s in json.load(open(ROOT / 'replays/ab' / ab / 'summary.json'))['suites']:
        for m in json.load(open(ROOT / s['batch'] / 'results.json'))['matches']:
            p = Path(m['map']).resolve()
            key = str(p.relative_to(ROOT))
            per[key].append(1.0 if m['winner'] == 0 else 0.0 if m['winner'] == 1 else 0.5)
    ms = [m for m in per if m in F]
    y = np.array([np.mean(per[m]) - 0.5 for m in ms]); w = np.array([len(per[m]) for m in ms], float)
    Z = (np.array([[F[m][f] for f in FEATS] for m in ms]) - mu) / sd
    X = np.column_stack([np.ones(len(y)), Z]); Xw = X * w[:, None]
    A = np.linalg.inv(X.T @ Xw); b = A @ (Xw.T @ y); r = y - X @ b
    V = A @ ((X * (w * r)[:, None]).T @ (X * (w * r)[:, None])) @ A
    wald = b[1:] @ np.linalg.solve(V[1:, 1:], b[1:])
    nw = []
    for _ in range(300):
        Xp = np.column_stack([np.ones(len(y)), Z[rng.permutation(len(ms))]]); Xpw = Xp * w[:, None]
        Ap = np.linalg.inv(Xp.T @ Xpw); bp = Ap @ (Xpw.T @ y); rp = y - Xp @ bp
        Vp = Ap @ ((Xp * (w * rp)[:, None]).T @ (Xp * (w * rp)[:, None])) @ Ap
        nw.append(bp[1:] @ np.linalg.solve(Vp[1:, 1:], bp[1:]))
    pred = (W @ Z.T).T @ dx  # map-dependent part of the predicted score gain
    c = np.corrcoef(pred, y)[0, 1]
    # weighted slope of outcome on the prediction
    pw = pred - np.average(pred, weights=w); yw = y - np.average(y, weights=w)
    slope = (w * pw * yw).sum() / (w * pw * pw).sum(); res = yw - slope * pw
    se = np.sqrt((w ** 2 * pw ** 2 * res ** 2).sum()) / (w * pw * pw).sum()
    print(f'== {ab}: {int(w.sum())} games, {len(ms)} maps, mean {100 * np.average(y, weights=w):+.2f} pts; '
          f'Wald chi2({len(FEATS)}) {wald:.1f}, perm p {np.mean(np.array(nw) >= wald):.3f}')
    print('   slopes (pts/SD, t): ' + ', '.join(f'{f} {100 * b[j + 1]:+.2f} ({b[j + 1] / np.sqrt(V[j + 1, j + 1]):+.1f})' for j, f in enumerate(FEATS)))
    print(f'   outcome on SPSA-predicted map-dependent gain: corr {c:+.3f}, slope {slope:+.2f} (SE {se:.2f}; 0.6 expected if the fit is right)')
