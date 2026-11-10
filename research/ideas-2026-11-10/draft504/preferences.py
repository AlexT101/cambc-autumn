"""Outcome-free opponent preferences and one-slope Ocean draft calibration."""
import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

CHAMPS = ['ryth', 'vesper_vale', 'vendetta', 'cassi_and_issac', 'stellar', 'prism',
          'marcella', 'willow', 'ren', 'varg', 'tavi', 'heart_of_ruin']
DISPLAY = ['Ryth', 'Vesper Vale', 'Vendetta', 'Cassi & Issac', 'Stellar', 'Prism',
           'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'Heart of Ruin']
RIDGES = (16., 64., 256.)


def fold(key):
    h = 2166136261
    for c in key:
        h = ((h ^ ord(c)) * 16777619) & 0xffffffff
    return h % 5


def weights(rows):
    """One unit per team/map, equally split over observed sides and repeats."""
    maps, sides, counts = defaultdict(set), defaultdict(set), Counter()
    for r in rows:
        t, m, s = r['team'], r['map_hash'], r['side']
        maps[t].add(m); sides[t, m].add(s); counts[t, m, s] += 1
    assert set(maps) == {'Fish', 'Mite'}
    # Total effective weight is 2 * maps-per-team, not the number of captures.
    effective = 2 * min(map(len, maps.values()))
    return np.array([effective / (2 * len(maps[r['team']]) * len(sides[r['team'], r['map_hash']]) *
                                 counts[r['team'], r['map_hash'], r['side']]) for r in rows])


def targets(rows):
    out = np.zeros((len(rows), len(CHAMPS)))
    for i, r in enumerate(rows):
        assert len(r['picks']) in (3, 4, 5) and len(set(r['picks'])) == len(r['picks'])
        for name in r['picks']:
            out[i, DISPLAY.index(name)] = 1
    return out


def flat(y, w):
    q = (w @ y + .5) / (w.sum() + 1.)
    return np.log(q / (1 - q)), q


def sigmoid(x):
    return np.exp(-np.logaddexp(0, -x))


def fit_logistic(x, y, w, offset, ridge):
    """Strictly convex ridge fit, jointly vectorized across champions."""
    beta = np.zeros((x.shape[1], y.shape[1]))
    eye = np.eye(x.shape[1])
    def objective(b):
        eta = offset + x @ b
        return np.sum(w[:, None] * (np.logaddexp(0, eta) - y * eta)) + ridge / 2 * np.sum(b * b)
    for _ in range(80):
        eta = offset + x @ beta; pr = sigmoid(eta)
        grad = x.T @ (w[:, None] * (pr - y)) + ridge * beta
        step = np.empty_like(beta)
        for c in range(y.shape[1]):
            h = x.T @ ((w * pr[:, c] * (1 - pr[:, c]))[:, None] * x) + ridge * eye
            step[:, c] = np.linalg.solve(h, grad[:, c])
        scale = 1.; old = objective(beta)
        while scale > 2 ** -30 and objective(beta - scale * step) > old:
            scale /= 2
        beta -= scale * step
        if np.max(np.abs(scale * step)) < 1e-9:
            return beta
    raise ValueError('Preference regression did not converge')


def standardized(features, model):
    out = []
    for k, (name, transform) in enumerate(zip(model['features'][:25], model['transforms'][:25])):
        v = features[name]
        if v is None or not np.isfinite(v):
            out.append(0.)
            continue
        if transform == 'log': v = np.log(max(v, 1))
        elif transform == 'log1p': v = np.log1p(max(v, 0))
        assert np.isfinite(v)
        out.append(float(np.clip((v - model['mean'][k]) / model['sd'][k], -4, 4)))
    return out


def preference_fit(rows, features, model):
    assert len(model['features']) == 92 and len(model['transforms']) == 92
    y, w = targets(rows), weights(rows)
    p = np.array([len(r['picks']) for r in rows])
    z = np.array([standardized(features[r['map_hash']]['f'], model) for r in rows])
    x = np.column_stack([(p[:, None] == np.array([3, 4, 5])).astype(float), z])
    folds = np.array([fold(r['map_hash']) for r in rows])
    cv = {}
    for ridge in RIDGES:
        loss = total = 0.
        for k in range(5):
            tr, te = folds != k, folds == k
            if not te.any(): continue
            wt, we = weights([r for r, keep in zip(rows, tr) if keep]), weights([r for r, keep in zip(rows, te) if keep])
            offset, _ = flat(y[tr], wt)
            beta = fit_logistic(x[tr], y[tr], wt, offset, ridge)
            eta = offset + x[te] @ beta
            loss += np.sum(we[:, None] * (np.logaddexp(0, eta) - y[te] * eta))
            total += we.sum() * len(CHAMPS)
        cv[ridge] = float(loss / total)
    ridge = min(RIDGES, key=lambda r: (round(cv[r], 12), -r))
    offset, q = flat(y, w)
    beta = fit_logistic(x, y, w, offset, ridge)
    diagnostics = {}
    for team in ('Fish', 'Mite'):
        diagnostics[team] = {}
        for count in (None, 3, 4, 5):
            mask = np.array([r['team'] == team and (count is None or len(r['picks']) == count) for r in rows])
            selected = [r for r, keep in zip(rows, mask) if keep]
            diagnostics[team]['overall' if count is None else str(count)] = {
                'drafts': len(selected), 'raw_counts': dict(Counter(c for r in selected for c in r['picks'])),
                'balanced_inclusion': (w[mask] @ y[mask] / w[mask].sum()).tolist()}
    # Columns of coefficients are B, then the actual F92's first 25 W entries.
    directions = {'flat': {}, 'conditional': {}}
    for p in (3, 4, 5):
        f = np.column_stack([offset, np.zeros((len(CHAMPS), 25))])
        c = np.column_stack([offset + beta[p - 3], beta[3:].T])
        for name, a in [('flat', f), ('conditional', c)]:
            a -= a.mean(axis=0)
            directions[name][p] = a.tolist()
    return {'directions': directions, 'conditional_ridge': ridge, 'archive_cv_logloss': cv,
            'flat_inclusion_balanced_smoothed': q.tolist(), 'flat_inclusion_balanced_raw': (w @ y / w.sum()).tolist(),
            'raw_pick_counts': dict(Counter(c for r in rows for c in r['picks'])),
            'effective_team_maps': float(w.sum()), 'normalization': {'features': model['features'][:25],
            'transforms': model['transforms'][:25], 'mean': model['mean'][:25], 'sd': model['sd'][:25]},
            'team_diagnostics': diagnostics,
            'folds': {str(k): len({r['map_hash'] for r in rows if fold(r['map_hash']) == k}) for k in range(5)}}


def normalize(direction, pool):
    variance = []
    for row in pool:
        a = np.array(direction[str(row['picks'])] if str(row['picks']) in direction else direction[row['picks']])
        values = a[:, 0] + a[:, 1:] @ np.array(row['z'][:25])
        p = row['picks']; n = len(values)
        # Two independent uniform p-subsets: exact variance of their score contrast.
        variance.append(2 * p * (n - p) / (n - 1) * np.var(values))
    scale = float(np.sqrt(np.mean(variance)))
    assert np.isfinite(scale) and scale > 0
    return {str(p): (np.array(a) / scale).tolist() for p, a in direction.items()}, scale


def direction_value(direction, row):
    a = np.asarray(direction[str(row['picks'])])
    v = a[:, 0] + a[:, 1:] @ np.asarray(row['z'][:25])
    return float((sum(v[c] for c in row['A']) if row['oursA'] else 0) -
                 (sum(v[c] for c in row['B']) if row['oursB'] else 0))


def slope(eta, d, y, keys):
    counts = Counter(keys)
    # Each map contributes one average log loss; duplicating captures/games cannot alter shrinkage.
    w = np.array([1. / counts[k] for k in keys])
    def grad(v): return float(np.sum(w * (sigmoid(eta + v * d) - y) * d) + v)
    if grad(0) >= 0: return 0.
    hi = 1.
    while grad(hi) < 0:
        hi *= 2
        assert hi < 2 ** 30
    lo = 0.
    for _ in range(80):
        mid = (lo + hi) / 2
        if grad(mid) < 0: lo = mid
        else: hi = mid
    return float((lo + hi) / 2)


def calibrate(pref, oof, pool, model):
    out = {'arms': {}, 'folds': {}}
    keys = [r['key'] for r in oof]
    assert len(oof) and all(r['fold'] == fold(r['key']) for r in oof)
    for k in range(5):
        out['folds'][k] = {'maps': len({r['key'] for r in oof if r['fold'] == k}),
                           'rows': sum(r['fold'] == k for r in oof)}
        assert out['folds'][k]['maps'] > 0
    for name, original in pref['directions'].items():
        direction, scale = normalize(original, pool)
        delta = np.array([direction_value(direction, r) for r in oof])
        lam = slope(np.array([r['eta'] for r in oof]), delta, np.array([r['y'] for r in oof]), keys)
        m = json.loads(json.dumps(model))
        for p in (3, 4, 5):
            a = np.array(direction[str(p)]) * lam
            th = m['picks'][str(p)]['theta']; lay = m['layout']
            for c in range(len(CHAMPS)):
                th[lay['B'] + c] += float(a[c, 0])
                for k in range(25): th[lay['W'] + c * lay['K'] + k] += float(a[c, k + 1])
        out['arms'][name] = {'lambda': lam, 'direction_scale': scale, 'direction': direction, 'model': m}
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--rows', type=Path, required=True)
    ap.add_argument('--features', type=Path, required=True); ap.add_argument('--model', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True); a = ap.parse_args()
    rows = [json.loads(s) for s in a.rows.read_text().splitlines() if s]
    result = preference_fit(rows, json.loads(a.features.read_text()), json.loads(a.model.read_text()))
    a.out.write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__': main()
