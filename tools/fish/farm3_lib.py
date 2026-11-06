"""Shared scoring for the farm3 structural tests (FARM3.md).

Rows are farm2's (choice-v1 episodes, non-opening, label `hit`, joined with farm2 extras). The
reference model is the farm2 logit (farm2_features sets/opts), refitted on FIT and scored on HELD,
so every structural alternative is compared on the same rows and split. Unscoreable rows (label not
a candidate) stay in the denominator as errors.
"""
import copy
import gzip
import json
import math
from pathlib import Path

import numpy as np

from farm2_features import featurizer
from farm2_lib import Design, candidates, fit
from farm3_common import HP

FIT = ['model', 'confirm', 'third', 'fourth']
HELD = ['fifth', 'sixth']
FARM2_SETS = ['base', 'hp', 'rate', 'home', 'stale', 'crew', 'size']
FARM2_OPTS = {'gem_gold': 3.0, 'crew': 1.0}
MANIFESTS = {'model': 'research/fish-2026-11-05/manifest.json', 'confirm': 'research/fish-2026-11-05/confirmation-manifest.json',
             'third': 'research/fish-2026-11-05/third-manifest.json', 'fourth': 'research/fish-2026-11-05/fourth-manifest.json',
             'fifth': 'research/fish-2026-11-05/fifth-manifest.json', 'sixth': 'research/fish-2026-11-05/sixth-manifest.json',
             'seventh': 'research/fish-2026-11-05/seventh-manifest.json'}


OLD_CHOICE = {'model': 'replays/fish-model', 'third': 'replays/fish-third', 'fourth': 'replays/fish-fourth',
              'fifth': 'replays/fish-fifth', 'confirm': 'replays/fish-confirm-farm2', 'sixth': 'replays/fish-sixth'}


def cohort_paths(c):
    """Choice rows, farm2 extras, raw actor caches and manifest of a cohort. The six decoded cohorts
    use their existing files; any other cohort NAME uses replays/fish-farm3/NAME/{choice-v1,farm2-v3}
    built by the unchanged scripts, raw caches replays/fish-NAME and research/.../NAME-manifest.json."""
    if c in OLD_CHOICE:
        base = Path('replays/fish-farm2') / c
        extras = next((base / f'farm2-v{v}.jsonl.gz' for v in (3, 2, 1) if (base / f'farm2-v{v}.jsonl.gz').exists()), None)
        return dict(choice=Path(OLD_CHOICE[c]) / 'choice-v1.jsonl.gz', extras=extras, manifest=MANIFESTS[c],
                    raw='replays/fish-confirm' if c == 'confirm' else OLD_CHOICE[c])
    d = Path('replays/fish-farm3') / c
    return dict(choice=d / 'choice-v1.jsonl.gz', extras=d / 'farm2-v3.jsonl.gz', raw=f'replays/fish-{c}',
                manifest=f'research/fish-2026-11-05/{c}-manifest.json')


def manifest(cohort):
    return {e['sha256'][:16]: e for e in json.loads(Path(cohort_paths(cohort)['manifest']).read_text())}


def apply_team(r, o):
    """Copy of row r with team-memory overrides {group: [state, age, respawn, respawn_raw]} applied."""
    r = copy.deepcopy(r)
    for c in r['x']['candidates']:
        v = o.get(str(c['id']))
        if v is None:
            continue
        st, age, resp, raw = v
        ce = r['e']['candidates'][str(c['id'])]
        if st != c['state']:
            ce['hp_left'] = sum(HP[t] for t in c['types']) if st in (0, 1) else 0
            ce['awake'] = 0
        c['state'] = st; c['age'] = age; c['respawn'] = resp
        if raw is not None:
            ce['respawn_raw'] = raw
    return r


def load_rows(c, team=False):
    """farm2_lib.load's rows (non-opening, label hit, farm2 extras joined) for cohort c; with
    team=True, the farm3_memory overrides applied (team-union memory)."""
    p = cohort_paths(c)
    extra = {}
    with gzip.open(p['extras'], 'rt') as f:
        for line in f:
            z = json.loads(line); extra[z['game'], z['step']] = z['x']
    over = {}
    if team:
        with gzip.open(Path('replays/fish-farm3') / c / 'team-v1.jsonl.gz', 'rt') as f:
            for line in f:
                z = json.loads(line); over[z['game'], z['step']] = z['o']
    out = []
    with gzip.open(p['choice'], 'rt') as f:
        for line in f:
            r = json.loads(line)
            if r['x']['reason'] == 'opening' or r['y']['status'] != 'hit':
                continue
            r['cohort'] = c; r['e'] = extra.get((r['game'], r['step']))
            if r['e'] is None:
                raise SystemExit(f'{c}: rows lack farm2 extras')
            if team:
                r = apply_team(r, over[r['game'], r['step']])
            out.append(r)
    return out


def rows_of(cohorts, team=False):
    out = []
    for c in cohorts:
        rs = load_rows(c, team)
        m = manifest(c)
        for r in rs:
            e = m.get(r['game'], {})
            r['map'] = e.get('map'); r['side'] = e.get('side'); r['unit'] = e.get('group') or e.get('match') or r['game']
        out += rs
    return out


def fit_farm2(rows, sets=FARM2_SETS, opts=FARM2_OPTS, extra=None, l2=0.1):
    """Logit weights per reason. `extra(r, cs) -> list of dicts` adds features."""
    fz = featurizer(sets, opts)
    run = fz if extra is None else (lambda r, cs: [a | b for a, b in zip(fz(r, cs), extra(r, cs))])
    weights = {}
    for reason in ('payout', 'spawn'):
        d = Design([r for r in rows if r['x']['reason'] == reason], run)
        w, _, _ = fit(d, l2)
        weights[reason] = dict(zip(d.keys, map(float, w)))
    return dict(sets=sets, opts=opts, weights=weights, l2=l2), run


def score_rows(rows, model, run):
    """Per row: (candidate ids, scores) under the logit `model`."""
    out = []
    for r in rows:
        cs = candidates(r['x'])
        fs = run(r, cs)
        w = model['weights'][r['x']['reason']]
        out.append(([c['id'] for c in cs], np.array([sum(w.get(k, 0.0) * v for k, v in f.items()) for f in fs])))
    return out


def argmax(ids, s):
    if not len(ids):
        return None
    best = s.max()
    return min(i for i, v in zip(ids, s) if v >= best - 1e-12)


def accuracy(rows, preds):
    res = {}
    for reason in ('all', 'payout', 'spawn'):
        m = [i for i, r in enumerate(rows) if reason == 'all' or r['x']['reason'] == reason]
        ok = sum(preds[i] == rows[i]['y']['targets'][0] for i in m)
        res[reason] = dict(correct=int(ok), n=len(m), accuracy=ok / len(m) if m else None)
    return res


def bootstrap(rows, a, b, n=10000, seed=0):
    """95% interval of accuracy(a) - accuracy(b), resampling match groups."""
    rng = np.random.default_rng(seed)
    units = sorted({r['unit'] for r in rows})
    idx = {u: k for k, u in enumerate(units)}
    num = np.zeros(len(units)); den = np.zeros(len(units))
    for r, x, y in zip(rows, a, b):
        t = r['y']['targets'][0]
        num[idx[r['unit']]] += (x == t) - (y == t); den[idx[r['unit']]] += 1
    draws = []
    for _ in range(n):
        p = rng.integers(0, len(units), len(units))
        draws.append(num[p].sum() / den[p].sum())
    return dict(units=len(units), lo=float(np.percentile(draws, 2.5)), hi=float(np.percentile(draws, 97.5)))


def fmt(res):
    return '  '.join(f"{k} {v['correct']}/{v['n']} {100 * v['accuracy']:.2f}%" for k, v in res.items() if v['n'])


def softmax_rank(ids, s, label):
    if label not in ids:
        return None
    order = sorted(range(len(ids)), key=lambda k: (-s[k], ids[k]))
    return [ids[k] for k in order].index(label)


def log1p(x):
    return math.log1p(max(0.0, x))
