"""Fit and check enemy-order predictors on order_data.py's rows: P(enemy e acts before our observer o next round).

Compares "last read" (every enemy keeps the priority last read), worst case (an unsettled enemy at rank 0, a settled
one at its earliest) and logistic models: one on features any bot sees (static), one adding the enemy team's
reordering rates learned online in the match (a relaxation: it learns an opponent is static).

usage: venv/bin/python order_fit.py TRAIN.pkl [EVAL.pkl ...] [--top TEAMS]
Needs numpy. Train/test split by game hash (1/4 test). Prints calibration tables and writes the fitted weights to
order_fit.json next to the first pickle.
"""
import json
import pickle
import sys
import zlib

import numpy as np


def load(path):
    d = pickle.load(open(path, 'rb'))
    cols = d['cols']
    rows = d['rows']
    out = {}
    for i, c in enumerate(cols):
        vals = [r[i] for r in rows]
        if isinstance(vals[0], str):
            out[c] = np.array(vals, dtype=object)
        else:
            out[c] = np.array(vals, dtype=np.float64)
    return out


def team_slot(rank, others, starts):
    # World::slot: alternate, the larger team's extras last
    return np.where(rank < others, 2 * rank + np.where(starts > 0, 0, 1), others + rank)


def derive(D):
    n, n_obs, st = D['n'], D['n_obs'], D['starts_next']
    obs_slot = D['obs_slot_next']
    lr_slot = team_slot(D['lr_rank'], n_obs, st)
    wc_slot = team_slot(D['earliest'], n_obs, st)
    D['p_lr'] = (lr_slot < obs_slot).astype(float)
    D['p_wc'] = (wc_slot < obs_slot).astype(float)
    # enemy ranks before our slot: e is before o iff its rank < m
    m = np.zeros_like(n)
    for k in range(0, 8):
        m += ((k < n) & (team_slot(np.full_like(n, k), n_obs, st) < obs_slot)).astype(float)
    D['m'] = m
    D['y'] = D['y_before']
    return D


def smooth(a, b, prior, w):
    return (a + prior * w) / (b + w)


FEATS_STATIC = ['lr_before', 'lr_gap', 'lr_gap_after', 'm_frac', 'settled', 'earliest_before', 'dclose', 'n_ours4',
                'n_mates4', 'hp', 'low_ours', 'e_changed_last', 'cur_top', 'starts_next', 'obs_top']
FEATS_ONLINE = ['team_moved', 'team_up', 'team_top', 'e_moved', 'team_changed']


def features(D, online):
    lr_before = D['p_lr']
    m, lr = D['m'], D['lr_rank']
    F = {
        'lr_before': lr_before,
        # how many ranks it must climb to get before us (0 if already before), and how far ahead it is
        'lr_gap': np.clip(lr - m + 1, 0, 4) * (1 - lr_before),
        'lr_gap_after': np.clip(m - lr, 0, 4) * lr_before,
        'm_frac': m / np.maximum(1, D['n']),
        'settled': D['settled'],
        'earliest_before': D['p_wc'] * D['settled'],
        'dclose': (D['dmin'] <= 2).astype(float),
        'n_ours4': np.minimum(D['n_ours4'], 4),
        'n_mates4': np.minimum(D['n_mates4'], 4),
        'hp': D['hp'],
        'low_ours': D['low_ours'],
        'e_changed_last': D['e_changed_last'],
        'cur_top': (D['cur_rank'] == 0).astype(float),
        'starts_next': D['starts_next'],
        'obs_top': (D['obs_rank'] == 0).astype(float),
    }
    if online:
        F['team_moved'] = smooth(D['st_moved'], D['st_contact'], 0.3, 20)
        F['team_up'] = smooth(D['st_up'], D['st_contact'], 0.15, 20)
        F['team_top'] = smooth(D['st_top'], D['st_contact'], 0.4, 20)
        F['e_moved'] = smooth(D['es_moved'], D['es_contact'], 0.3, 10)
        F['team_changed'] = smooth(D['st_changed'], D['st_contact'], 0.3, 20)
    names = FEATS_STATIC + (FEATS_ONLINE if online else [])
    X = np.stack([F[k] for k in names], 1)
    # interactions with lr_before: the model is two models, one per last-read answer
    Xi = X * lr_before[:, None]
    X = np.concatenate([np.ones((len(X), 1)), X, Xi], 1)
    return X, ['1'] + names + ['lrb*' + k for k in names]


def fit_logistic(X, y, l2=1e-3, iters=30):
    w = np.zeros(X.shape[1])
    for _ in range(iters):
        z = X @ w
        p = 1 / (1 + np.exp(-z))
        g = X.T @ (p - y) / len(y) + l2 * w
        W = p * (1 - p)
        H = (X * W[:, None]).T @ X / len(y) + l2 * np.eye(X.shape[1])
        step = np.linalg.solve(H, g)
        w -= step
        if np.abs(step).max() < 1e-7:
            break
    return w


def predict(X, w):
    return 1 / (1 + np.exp(-(X @ w)))


def metrics(p, y):
    pc = np.clip(p, 1e-3, 1 - 1e-3)
    brier = np.mean((p - y) ** 2)
    ll = -np.mean(y * np.log(pc) + (1 - y) * np.log(1 - pc))
    acc = np.mean((p >= 0.5) == (y > 0.5))
    # missed "before" (said after, was before) and false alarms
    under = np.mean((p < 0.5) & (y > 0.5))
    over = np.mean((p >= 0.5) & (y < 0.5))
    return brier, ll, acc, under, over


def reliability(p, y, bins=(0, .05, .1, .2, .3, .4, .5, .6, .7, .8, .9, .95, 1.0001)):
    out = []
    for a, b in zip(bins[:-1], bins[1:]):
        s = (p >= a) & (p < b)
        if s.sum() >= 50:
            out.append((a, b, int(s.sum()), float(p[s].mean()), float(y[s].mean())))
    return out


def report(name, D, sel, preds):
    y = D['y'][sel]
    print(f'\n### {name}: {int(sel.sum())} rows, base rate before {y.mean():.3f}')
    print('| predictor | Brier | log loss | accuracy | said after, was before | said before, was after |')
    print('|---|---|---|---|---|---|')
    for k, p in preds.items():
        b, ll, a, u, o = metrics(p[sel], y)
        print(f'| {k} | {b:.4f} | {ll:.3f} | {a:.3f} | {u:.3f} | {o:.3f} |')


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    train = derive(load(args[0]))
    h = np.array([zlib.crc32(g.encode()) % 4 for g in train['game']])
    tr = h != 0
    res = {}
    for online in (False, True):
        X, names = features(train, online)
        w = fit_logistic(X[tr], train['y'][tr])
        res['online' if online else 'static'] = {'names': names, 'w': w.tolist()}
        train['p_' + ('on' if online else 'st')] = predict(X, w)
    preds = {'last read': train['p_lr'], 'worst case': train['p_wc'], 'model static': train['p_st'],
             'model online': train['p_on']}
    te = ~tr
    report('ladder test, all', train, te, preds)
    report('ladder test, unsettled', train, te & (train['settled'] == 0), preds)
    report('ladder test, settled', train, te & (train['settled'] == 1), preds)
    report('ladder test, unsettled, within 2', train, te & (train['settled'] == 0) & (train['dmin'] <= 2), preds)
    for k in ('model static', 'model online'):
        print(f'\nReliability, {k}, ladder test unsettled: (bin, n, mean p, observed)')
        for a, b, n, mp, oy in reliability(preds[k][te & (train['settled'] == 0)], train['y'][te & (train['settled'] == 0)]):
            print(f'  [{a:.2f},{b:.2f}) {n:8d} {mp:.3f} {oy:.3f}')
    # conditional rates of the two fixed rules
    for s in (0, 1):
        sel = te & (train['settled'] == s)
        for lab, p in (('last read', train['p_lr']), ('worst case', train['p_wc'])):
            for v in (0, 1):
                q = sel & (p == v)
                if q.sum():
                    print(f'settled={s} {lab} says {"before" if v else "after"}: {int(q.sum())} rows, before {train["y"][q].mean():.3f}')
    # per team (top teams by rows)
    teams, counts = np.unique(train['team'][te], return_counts=True)
    order = np.argsort(-counts)[:16]
    print('\n| team | rows (test, unsettled) | before | last read Brier | worst Brier | static Brier | online Brier | static under/over | online under/over |')
    print('|---|---|---|---|---|---|---|---|---|')
    for i in order:
        t = teams[i]
        sel = te & (train['team'] == t) & (train['settled'] == 0)
        if sel.sum() < 500:
            continue
        y = train['y'][sel]
        b = [metrics(preds[k][sel], y) for k in ('last read', 'worst case', 'model static', 'model online')]
        print(f'| {t} | {int(sel.sum())} | {y.mean():.3f} | {b[0][0]:.4f} | {b[1][0]:.4f} | {b[2][0]:.4f} | {b[3][0]:.4f} | '
              f'{b[2][3]:.3f}/{b[2][4]:.3f} | {b[3][3]:.3f}/{b[3][4]:.3f} |')
    for k in ('static', 'online'):
        print(f'\nweights {k}:')
        for n_, w_ in zip(res[k]['names'], res[k]['w']):
            print(f'  {n_:20s} {w_:+.3f}')
    for path in args[1:]:
        E = derive(load(path))
        for online in (False, True):
            X, _ = features(E, online)
            E['p_' + ('on' if online else 'st')] = predict(X, np.array(res['online' if online else 'static']['w']))
        pe = {'last read': E['p_lr'], 'worst case': E['p_wc'], 'model static': E['p_st'], 'model online': E['p_on']}
        for t in np.unique(E['team']):
            report(f'{path}: {t}, unsettled', E, (E['team'] == t) & (E['settled'] == 0), pe)
            report(f'{path}: {t}, settled', E, (E['team'] == t) & (E['settled'] == 1), pe)
            for k in ('model static', 'model online'):
                sel = (E['team'] == t) & (E['settled'] == 0)
                print(f'Reliability, {k}:')
                for a, b, n, mp, oy in reliability(pe[k][sel], E['y'][sel]):
                    print(f'  [{a:.2f},{b:.2f}) {n:8d} {mp:.3f} {oy:.3f}')
    json.dump(res, open(args[0].rsplit('.', 1)[0] + '.fit.json', 'w'), indent=1)


if __name__ == '__main__':
    main()
