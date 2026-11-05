"""Fit the farm2 destination logit: payout and spawn weights, on whole cohorts.

The fit JSON records the feature sets and options, so farm2_evaluate.py rebuilds the same features.
Refuses to overwrite.

usage: farm2_fit.py OUT COHORT[,COHORT...] --sets base+rate+... [--opt k=v] [--l2 0.1]
"""
import argparse
import hashlib
import json
from pathlib import Path

from farm2_features import featurizer
from farm2_lib import Design, fit, load, refuse

CODE = ['tools/fish/farm2_lib.py', 'tools/fish/farm2_features.py', 'tools/fish/farm2_fit.py', 'tools/fish/choice_model.py']


def main(out, cohorts, sets, opts, l2):
    refuse(out)
    rows = [r for c in cohorts for r in load(c)]
    missing = sum(r['e'] is None for r in rows)
    if missing:
        raise SystemExit(f'{missing} rows lack farm2 extras')
    fz = featurizer(sets, opts)
    result = dict(sets=sets, opts=opts, l2=l2, cohorts=cohorts, weights={}, episodes={}, log_likelihood={})
    for reason in ('payout', 'spawn'):
        d = Design([r for r in rows if r['x']['reason'] == reason], fz)
        w, ll, m = fit(d, l2)
        result['weights'][reason] = dict(zip(d.keys, map(float, w)))
        result['episodes'][reason] = m; result['log_likelihood'][reason] = ll
        print(reason, m, 'fitted episodes, log-likelihood', round(ll, 1))
    result['code'] = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in CODE}
    with open(out, 'x') as f:
        json.dump(result, f, indent=1); f.write('\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('out'); p.add_argument('cohorts'); p.add_argument('--sets', required=True)
    p.add_argument('--opt', action='append', default=[]); p.add_argument('--l2', type=float, default=0.1)
    a = p.parse_args()
    main(a.out, a.cohorts.split(','), a.sets.split('+'), {k: float(v) for k, v in (o.split('=') for o in a.opt)}, a.l2)
