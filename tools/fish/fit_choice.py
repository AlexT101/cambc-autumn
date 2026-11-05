"""Fit the conditional-logit destination score (Newton, L2) on clean post-payout/spawn hits."""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from choice_model import candidates, features


def rows(paths):
    for p in paths:
        with gzip.open(p, 'rt') as f:
            for line in f:
                r = json.loads(line)
                if r['x']['reason'] != 'opening' and r['y']['status'] == 'hit':
                    yield r


def main(out, sources, l2):
    X, Y, keys = [], [], None
    for r in rows(sources):
        cs = candidates(r['x'])
        ids = [c['id'] for c in cs]
        if r['y']['targets'][0] not in ids:
            continue
        F = [features(r['x'], c) for c in cs]
        keys = keys or list(F[0])
        X.append(np.array([[f[k] for k in keys] for f in F]))
        Y.append(ids.index(r['y']['targets'][0]))
    w = np.zeros(len(keys))
    for _ in range(100):
        g = -l2 * w; H = -l2 * np.eye(len(keys)); ll = 0.0
        for x, y in zip(X, Y):
            s = x @ w; s -= s.max(); p = np.exp(s); p /= p.sum()
            ll += math.log(p[y]); mu = p @ x
            g += x[y] - mu; H -= (x * p[:, None]).T @ x - np.outer(mu, mu)
        step = np.linalg.solve(H, -g); w += step
        if np.abs(step).max() < 1e-9:
            break
    fit = dict(l2=l2, episodes=len(Y), log_likelihood=ll, weights=dict(zip(keys, map(float, w))),
               sources={p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in sources},
               code={p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ('tools/fish/choice_model.py', 'tools/fish/fit_choice.py')})
    with open(out, 'x') as f:
        json.dump(fit, f, indent=2); f.write('\n')
    print(len(Y), 'episodes, log-likelihood', round(ll, 1))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('out'); p.add_argument('sources', nargs='+'); p.add_argument('--l2', type=float, default=0.1)
    a = p.parse_args(); main(a.out, a.sources, a.l2)
