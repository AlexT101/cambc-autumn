"""Held-out comparison of farm2 feature sets.

Fits payout and spawn logits separately on the training cohorts and scores the test cohorts,
for split A (model+third+fourth -> fifth, confirm) and split B (fifth -> model+third+fourth,
confirm). Unscoreable rows count as errors. Prints and optionally writes a JSON (never over an
existing file).

usage: farm2_explore.py SET[+SET...] [SET...] [--opt k=v] [--out FILE]
"""
import argparse
import json

import numpy as np

from farm2_features import featurizer
from farm2_lib import Design, fit, fmt, load, refuse, summary, wait_correct

SPLITS = {'A': (['model', 'third', 'fourth'], ['fifth', 'confirm']),
          'B': (['fifth'], ['model', 'third', 'fourth', 'confirm'])}


def run(data, sets, opts, l2=0.1, splits=('A', 'B'), verbose=True):
    fz = featurizer(sets, opts)
    out = {}
    for name in splits:
        train, test = SPLITS[name]
        res = {}; weights = {}
        tr = [r for c in train for r in data[c]]
        correct = {}
        for reason in ('payout', 'spawn'):
            d = Design([r for r in tr if r['x']['reason'] == reason], fz)
            w, ll, m = fit(d, l2)
            weights[reason] = dict(zip(d.keys, map(float, w)))
            for c in test:
                rows = [r for r in data[c] if r['x']['reason'] == reason]
                dt = Design(rows, fz, keys=d.keys)
                correct.setdefault(c, []).append((rows, dt.correct(w)))
        for c in test:
            rows = [r for rs, _ in correct[c] for r in rs]
            ok = np.concatenate([k for _, k in correct[c]])
            res[c] = summary(rows, ok)
        out[name] = dict(results=res, weights=weights)
        if verbose:
            for c, v in res.items():
                print(f'{"+".join(sets):>40} {name} {c:>7}: {fmt(v)}', flush=True)
    return out


def baseline(data, cohorts):
    out = {}
    for c in cohorts:
        out[c] = summary(data[c], wait_correct(data[c]))
        print(f'{"wait":>40}   {c:>7}: {fmt(out[c])}')
    return out


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('sets', nargs='+'); p.add_argument('--opt', action='append', default=[])
    p.add_argument('--l2', type=float, default=0.1); p.add_argument('--out')
    p.add_argument('--cohorts', default='model,third,fourth,fifth,confirm')
    a = p.parse_args()
    if a.out:
        refuse(a.out)
    opts = {k: float(v) for k, v in (o.split('=') for o in a.opt)}
    cohorts = a.cohorts.split(',')
    data = {c: load(c) for c in cohorts}
    for c in cohorts:
        missing = sum(r['e'] is None for r in data[c])
        if missing:
            raise SystemExit(f'{c}: {missing} rows lack extras')
    result = dict(baseline=baseline(data, cohorts), opts=opts, l2=a.l2, sets={})
    for s in a.sets:
        result['sets'][s] = run(data, s.split('+'), opts, a.l2)
    if a.out:
        with open(a.out, 'x') as f:
            json.dump(result, f, indent=1); f.write('\n')
