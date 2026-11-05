"""Grid-fit the positioning rule's two thresholds on the discovery cohorts only.

Rule: engage iff a kill is available from an engage tile, or own health fraction > H and the
least dangerous engage tile's one-turn enemy reach is <= D x own effective HP.
Also fits the no-kill variant, the gem-adjusted health variant and, for reference only, a
gradient-boosted ceiling on richer turn-start features (scored on held-out cohorts).
"""
import argparse
import gzip
import json
from pathlib import Path

import numpy as np

import combat_rules as R
from combat_common import COHORTS, DISCOVERY


def arrays(src, names):
    out = {k: [] for k in ('ctx', 'hpf', 'h', 'danger', 'kill', 'y', 'rich')}
    for name in names:
        for line in gzip.open(Path(src) / f'{name}-tiles-v1.jsonl.gz', 'rt'):
            r = json.loads(line); x = r['x']
            c = R.contexts(x)
            if c is None:
                continue
            ctx, tiles = c
            st = x['tiles'][0]
            dmin = min(q['danger'] for q in tiles)
            out['ctx'].append(ctx); out['hpf'].append(x['hpf'])
            out['h'].append(x['ehpf'] * (0.65 if x['gems'] else 1))
            out['danger'].append(dmin); out['kill'].append(any(q['kill'] for q in tiles))
            out['y'].append(R.engaged(x, r['y']))
            out['rich'].append([['m1', 'm2', 'r'].index(ctx), x['type'], x['hpf'], x['ehpf'], x['gems'], x['gold'],
                                x['cd'][0], x['cd'][1], x['n_e'], x['n_a'], x['round'], dmin, st['danger'],
                                st['reach_n'], st['allies2'], st['ally_min'], st['home_now'],
                                min(q['danger'] for q in x['tiles']), len(x['tiles']), int(any(q['kill'] for q in tiles))])
    return {k: np.array(v) for k, v in out.items()}


def fit(a, hkey, use_kill):
    best = None
    for H in np.round(np.arange(0.20, 0.80, 0.01), 2):
        for D in np.round(np.arange(0.05, 0.80, 0.01), 2):
            pred = (a[hkey] > H) & (a['danger'] <= D)
            if use_kill:
                pred |= a['kill']
            ok = int((pred == a['y']).sum())
            if best is None or ok > best[0]:
                best = (ok, float(H), float(D))
    return best


def score(a, hkey, H, D, use_kill):
    pred = (a[hkey] > H) & (a['danger'] <= D)
    if use_kill:
        pred |= a['kill']
    res = {}
    for ctx in ('all', 'm1', 'm2', 'r'):
        m = np.ones(len(pred), bool) if ctx == 'all' else a['ctx'] == ctx
        y = a['y'][m]
        base = np.where(a['ctx'][m] == 'm2', False, True)
        res[ctx] = dict(n=int(m.sum()), correct=int((pred[m] == y).sum()), accuracy=round(float((pred[m] == y).mean()), 4),
                        baseline_correct=int((base == y).sum()), baseline=round(float((base == y).mean()), 4),
                        engage_rate=round(float(y.mean()), 4))
    return res


def main(src, out):
    if Path(out).exists():
        raise SystemExit(f'refusing to overwrite {out}')
    disc = arrays(src, [c[0] for c in COHORTS if c[0] in DISCOVERY])
    held = arrays(src, [c[0] for c in COHORTS if c[0] not in DISCOVERY])
    result = dict(schema=1, note='thresholds fit on discovery only; baseline = context majority (m2 decline, m1/r engage)')
    for label, hkey, use_kill in (('health_danger_kill', 'hpf', True), ('health_danger', 'hpf', False),
                                  ('gem_health_danger_kill', 'h', True)):
        ok, H, D = fit(disc, hkey, use_kill)
        result[label] = dict(H=H, D=D, health=hkey, kill_override=use_kill,
                             discovery=score(disc, hkey, H, D, use_kill), heldout=score(held, hkey, H, D, use_kill))
        print(label, H, D, result[label]['heldout']['all'], flush=True)
    from sklearn.ensemble import HistGradientBoostingClassifier
    g = HistGradientBoostingClassifier(max_iter=300, random_state=0).fit(disc['rich'], disc['y'])
    result['gbm_ceiling'] = dict(features=20, discovery=round(float(g.score(disc['rich'], disc['y'])), 4),
                                 heldout=round(float(g.score(held['rich'], held['y'])), 4))
    print('gbm', result['gbm_ceiling'], flush=True)
    Path(out).write_text(json.dumps(result, indent=1))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--src', default='replays/fish-combat')
    p.add_argument('out')
    a = p.parse_args()
    main(a.src, a.out)
