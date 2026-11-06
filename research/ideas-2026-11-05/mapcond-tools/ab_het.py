"""Per-map heterogeneity of the tuned-vs-untuned effect in the held-out A/Bs of oc2 and oc3."""
import json, os
import numpy as np
from pathlib import Path
from collections import defaultdict
ROOT = Path('/home/ubuntu/cambc-autumn'); W = Path(os.environ.get('MAPCOND_DIR', '.'))
F = json.load(open(W / 'features.json'))
FEATS = ['log_area', 'picks', 'sym_rot', 'spawn_dist', 'camp_density', 'log_gems', 'big_share', 'contested', 'altars']
NPERM = int(os.environ.get('NPERM', 500))

def games(ab):
    s = json.load(open(ROOT / 'replays/ab' / ab / 'summary.json'))['suites'][0]
    r = json.load(open(ROOT / s['batch'] / 'results.json'))
    return {(Path(m['map']).name, tuple(m['order'])): (1.0 if m['winner'] == 0 else 0.0 if m['winner'] == 1 else 0.5) for m in r['matches']}

def direct(ab):
    g = games(ab); per = defaultdict(list)
    for (m, _), w in g.items(): per[m].append(w - 0.5)
    return per
def paired(abt, abb):
    t, b = games(abt), games(abb); per = defaultdict(list)
    for k in t:
        if k in b: per[k[0]].append(t[k] - b[k])
    return per
def merge(*pers):
    out = defaultdict(list)
    for p in pers:
        for m, v in p.items(): out[m] += v
    return out

C = {
 'oc2 direct (oct-a)': direct('oct-tuned-vs-base1'),
 'oc2 paired vs astraeus+proteus (oct-b)': merge(paired('oct-tuned-vs-astraeus', 'oct-base1-vs-astraeus'), paired('oct-tuned-vs-proteus', 'oct-base1-vs-proteus')),
 'oc2 mid direct (oct-c)': direct('oct-mid-vs-base1'),
 'oc3 direct (confirm)': direct('oc3-tuned3-vs-combo2-confirm'),
 'oc3 direct (confirm2)': direct('oc3-tuned3-vs-combo2-confirm2'),
 'oc3 direct (varied)': direct('oc3-tuned3-vs-combo2-varied'),
 'oc3 paired vs panel (pchk+p2)': merge(*[paired(f'oc3-{s}-tuned3-vs-{o}', f'oc3-{s}-combo2-vs-{o}') for s, o in
     [('pchk', 'panel-astraeus'), ('pchk', 'panel-proteus'), ('pchk', 'panel-demeter'), ('pchk', 'panel-ocean-td'), ('pchk', 'v67'), ('p2', 'panel-astraeus'), ('p2', 'panel-proteus')]]),
}
rng = np.random.default_rng(7)
def ols(Z, y, w):
    X = np.column_stack([np.ones(len(y)), Z]); Xw = X * w[:, None]
    A = np.linalg.inv(X.T @ Xw); b = A @ (Xw.T @ y); r = y - X @ b
    V = A @ ((X * (w * r)[:, None]).T @ (X * (w * r)[:, None])) @ A   # HC0, map-clustered
    return b, np.sqrt(np.diag(V)), V
res = {}
for name, per in C.items():
    ms = sorted(m for m in per if m in F)
    y = np.array([np.mean(per[m]) for m in ms]); w = np.array([len(per[m]) for m in ms], float)
    Z = np.array([[F[m][f] for f in FEATS] for m in ms]); Z = (Z - Z.mean(0)) / Z.std(0)
    b, se, V = ols(Z, y, w)
    wald = b[1:] @ np.linalg.solve(V[1:, 1:], b[1:])
    nw, nt = [], []
    for _ in range(NPERM):
        Zp = Z[rng.permutation(len(ms))]; bp, sp, Vp = ols(Zp, y, w)
        nw.append(bp[1:] @ np.linalg.solve(Vp[1:, 1:], bp[1:])); nt.append(np.abs(bp[1:] / sp[1:]).max())
    nw, nt = np.array(nw), np.array(nt)
    p = (1 + (nw >= wald).sum()) / (1 + NPERM)
    print(f'\n== {name}: {int(w.sum())} games on {len(ms)} maps, mean effect {100 * np.average(y, weights=w):+.2f} pts')
    print(f'   joint Wald chi2(9) {wald:.1f}, permutation p {p:.3f} (null median {np.median(nw):.1f}); max|t| {np.abs(b[1:] / se[1:]).max():.2f} (null 95% {np.percentile(nt, 95):.2f})')
    print('   slope per SD, pts: ' + '  '.join(f'{f} {100 * b[j + 1]:+.2f}({100 * se[j + 1]:.2f})' for j, f in enumerate(FEATS)))
    res[name] = {'b': b.tolist(), 'se': se.tolist(), 'wald': wald, 'p': p, 'n': int(w.sum()), 'maps': len(ms)}
json.dump(res, open(W / 'ab-het.json', 'w'), indent=1)
