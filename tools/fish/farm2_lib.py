"""Shared loading, conditional-logit fitting and held-out scoring for the farm2 destination study.

Rows are choice-v1 episodes (non-opening, label status hit), optionally joined by (game, step)
with farm2_data's causal extras. Payout and spawn episodes get separate weights. Rows whose label
is not a candidate stay in the denominator as errors.
"""
import gzip
import json
import math
from pathlib import Path

import numpy as np

COHORTS = {
    'model': 'replays/fish-model', 'third': 'replays/fish-third', 'fourth': 'replays/fish-fourth',
    'fifth': 'replays/fish-fifth', 'confirm': 'replays/fish-confirm-farm2', 'sixth': 'replays/fish-sixth',
    'seventh': 'replays/fish-seventh',
}


def load(cohort, extras=True):
    d = Path(COHORTS[cohort])
    extra = {}
    base = Path('replays/fish-farm2') / cohort
    e = next((base / f'farm2-v{v}.jsonl.gz' for v in (3, 2, 1) if (base / f'farm2-v{v}.jsonl.gz').exists()), base / 'none')
    if extras and e.exists():
        with gzip.open(e, 'rt') as f:
            for line in f:
                r = json.loads(line)
                extra[r['game'], r['step']] = r['x']
    out = []
    with gzip.open(d / 'choice-v1.jsonl.gz', 'rt') as f:
        for line in f:
            r = json.loads(line)
            if r['x']['reason'] == 'opening' or r['y']['status'] != 'hit':
                continue
            r['cohort'] = cohort
            if extras:
                r['e'] = extra.get((r['game'], r['step']))
            out.append(r)
    return out


def candidates(x):
    own = x['own_group'] if x['reason'] == 'payout' else None
    return [c for c in x['candidates'] if c['walk'] < 999 and c['id'] != own]


class Design:
    """Stacked candidate features for one reason ('payout' or 'spawn')."""

    def __init__(self, rows, featurize, keys=None):
        F, ep, ids, labels, self_rows = [], [], [], [], []
        for r in rows:
            cs = candidates(r['x'])
            fs = featurize(r, cs)
            y = r['y']['targets'][0]
            idx = [c['id'] for c in cs]
            labels.append(idx.index(y) if y in idx else -1)
            self_rows.append(r)
            for c, f in zip(cs, fs):
                F.append(f); ep.append(len(labels) - 1); ids.append(c['id'])
        self.keys = keys or (sorted(F[0]) if F else [])
        self.X = np.array([[f.get(k, 0.0) for k in self.keys] for f in F], dtype=float).reshape(len(F), len(self.keys))
        self.ep = np.array(ep, dtype=int); self.ids = np.array(ids, dtype=int)
        self.labels = np.array(labels, dtype=int); self.rows = self_rows
        self.n = len(labels)
        self.start = np.searchsorted(self.ep, np.arange(self.n))
        self.count = np.bincount(self.ep, minlength=self.n)

    def scores(self, w):
        return self.X @ w

    def predict(self, w):
        s = self.scores(w); out = np.full(self.n, -1)
        for i in range(self.n):
            a, k = self.start[i], self.count[i]
            if k == 0:
                continue
            seg = s[a:a + k]; ids = self.ids[a:a + k]
            best = seg.max()
            out[i] = ids[seg >= best - 1e-12].min()
        return out

    def correct(self, w):
        p = self.predict(w)
        y = np.array([r['y']['targets'][0] for r in self.rows])
        return (p == y) & (self.labels >= 0)


def fit(design, l2=0.1, iters=60):
    ok = design.labels >= 0
    rows = np.flatnonzero(ok)
    sel = np.isin(design.ep, rows)
    X = design.X[sel]; ep = design.ep[sel]
    remap = -np.ones(design.n, dtype=int); remap[rows] = np.arange(len(rows)); e = remap[ep]
    m = len(rows); k = X.shape[1]
    yi = design.start[rows] + design.labels[rows]
    # index of label row within the selected X
    pos = np.cumsum(sel) - 1
    Xy = X[pos[yi]]
    def objective(w):
        s = X @ w
        mx = np.full(m, -np.inf); np.maximum.at(mx, e, s)
        p = np.exp(s - mx[e]); z = np.bincount(e, p, m)
        return float(np.sum(Xy @ w - mx - np.log(z))) - 0.5 * l2 * float(w @ w), p / z[e]

    w = np.zeros(k); obj, p = objective(w)
    for _ in range(iters):
        mu = np.zeros((m, k)); np.add.at(mu, e, X * p[:, None])
        g = Xy.sum(0) - mu.sum(0) - l2 * w
        H = -(X * p[:, None]).T @ X + mu.T @ mu - l2 * np.eye(k)
        step = np.linalg.solve(H, -g); t = 1.0
        while True:
            new, q = objective(w + t * step)
            if new >= obj - 1e-9 or t < 1e-6:
                break
            t /= 2
        w = w + t * step; done = abs(new - obj) < 1e-7; obj, p = new, q
        if done or np.abs(t * step).max() < 1e-8:
            break
    ll = obj + 0.5 * l2 * float(w @ w)
    return w, ll, m


def wait_correct(rows):
    out = []
    for r in rows:
        cs = r['x']['candidates']  # wait baseline over all groups, as routes_model.route('ready')
        p = min(cs, key=lambda c: (max(c['walk'], c['respawn']), c['id']))['id']
        out.append(p == r['y']['targets'][0])
    return np.array(out)


def summary(rows, correct):
    res = {}
    for reason in ('all', 'payout', 'spawn'):
        m = np.array([reason == 'all' or r['x']['reason'] == reason for r in rows])
        res[reason] = dict(correct=int(correct[m].sum()), n=int(m.sum()), accuracy=float(correct[m].mean()) if m.any() else None)
    return res


def fmt(res):
    return '  '.join(f"{k} {v['correct']}/{v['n']} {100 * v['accuracy']:.2f}%" for k, v in res.items() if v['n'])


def refuse(path):
    if Path(path).exists():
        raise SystemExit(f'refusing to overwrite {path}')


def logp(x):
    return math.log1p(max(0.0, x))
