"""Prize estimates: (1) the SPSA iteration fit's debiased interaction strength with a quadratic model, (2) the oc2
direction's step length conditioned on map features."""
import json, os
import numpy as np
from pathlib import Path
W = Path(os.environ.get('MAPCOND_DIR', '.'))
for run in ['oc2', 'oc3']:
    d = json.load(open(W / f'{run}-het.json')); it = json.load(open(W / f'{run}-iters.json'))
    Wt, Ws = np.array(d['W']), np.array(d['Wse']); T2 = (Wt / Ws) ** 2
    # score -> win-rate slope from the candidates' (mean score, win rate) pairs
    s = np.array([v for r in it['iters'] for v in r['means'].values()])
    hist = [json.loads(l) for l in open(f'/home/ubuntu/cambc-autumn/replays/tune/{run}/history.jsonl')]
    wr = np.array([v for h in hist for v in h['win'].values()]); sc = np.array([v for h in hist for v in h['mean'].values()])
    k = np.polyfit(sc, wr, 1)[0]
    # effective curvature: the run's gain in score over its displacement (gain = 1/2 h |dx|^2 if it reached the optimum)
    x0 = np.array(list(hist[0]['x'].values())); x1 = np.array(list(hist[-1]['x'].values()))
    m0 = np.mean([np.mean(list(h['mean'].values())) for h in hist[:100]]); m1 = np.mean([np.mean(list(h['mean'].values())) for h in hist[-300:]])
    dx2 = np.sum((x1 - x0) ** 2); h = 2 * max(m1 - m0, 1e-4) / dx2
    n = T2.size; ssq = np.sum(Wt ** 2 - Ws ** 2); ssq_se = np.sqrt(np.sum(2 * Ws ** 4 + 4 * np.maximum(Wt ** 2 - Ws ** 2, 0) * Ws ** 2))
    ub = max(ssq, 0) + 1.645 * ssq_se
    print(f'{run}: win per score {k:.2f}; score gain over run {m1 - m0:+.4f} over |dx|^2 {dx2:.3f} -> h {h:.3f}/unit^2 (x scaled)')
    print(f'   sum(T^2-1) over {n} interactions: {np.sum(T2 - 1):+.1f} (null SD {np.sqrt(2 * n):.0f}); debiased sum W^2 {ssq:+.3f} +- {ssq_se:.3f}, 95% UB {ub:.3f}')
    print(f'   prize of linear map-conditioning, all constants (z independent, var 1): estimate {100 * k * max(ssq, 0) / (2 * h):.2f} pts, 95% UB {100 * k * ub / (2 * h):.2f} pts of win rate')
    print(f'   for scale: one interaction at the median SE ({np.median(Ws):.3f}) = {100 * k * np.median(Ws) ** 2 / (2 * h):.3f} pts; the main-gradient RMS {np.sqrt(np.mean(np.array(d["g"]) ** 2)):.3f}')
# oc2 direction, quadratic step model: e(z) = gain at t=1; per-map optimum t_z, extra gain Var(e)/(4 e_mean)
R = json.load(open(W / 'ab-het.json'))
F = json.load(open(W / 'features.json'))
FEATS = ['log_area', 'picks', 'sym_rot', 'spawn_dist', 'camp_density', 'log_gems', 'big_share', 'contested', 'altars']
import glob
Z = np.array([[v[f] for f in FEATS] for k2, v in F.items() if k2.startswith('gen-') and '-509' in k2[:20] or False])
for name in ['oc2 direct (oct-a)', 'oc2 paired vs astraeus+proteus (oct-b)', 'oc3 direct (confirm)', 'oc3 direct (confirm2)']:
    b, se = np.array(R[name]['b']), np.array(R[name]['se'])
    S = np.corrcoef(Z.T)
    v = b[1:] @ S @ b[1:] - np.sum(se[1:] ** 2 * np.diag(S))   # debiased (ignores slope covariances)
    e = b[0]
    print(f'{name}: mean {100 * e:+.2f} pts, SD across maps of the predicted effect (debiased) {100 * np.sqrt(max(v, 0)):.2f} pts'
          + (f' -> step-length prize Var/(4 e) {100 * max(v, 0) / (4 * e):.2f} pts' if e > 0.01 else ''))
