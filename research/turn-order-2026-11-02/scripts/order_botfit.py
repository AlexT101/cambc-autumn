"""The in-bot enemy-order predictor: order_fit.py's logistic model on the features ast-pred computes, fitted on
ladder and self-play rows together (each dataset weighted equally), checked on each dataset's held-out games.

P(enemy e acts before our slot next round), for an enemy whose next priority is not yet final (unsettled). A settled
enemy needs no model: its rank is bounded by the rules (earliest, latest) and last read is right 98-99%.

usage: venv/bin/python order_botfit.py LADDER.pkl SELF.pkl [MORE_EVAL.pkl ...]
Prints the C++ weight arrays for model/enemy_order.cc and calibration tables.
"""
import sys
import zlib

import numpy as np

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from order_fit import derive, fit_logistic, load, metrics, predict, reliability, smooth  # noqa: E402

STATIC = ['lr_before', 'lr_gap', 'lr_gap_after', 'm_frac', 'dclose', 'n_ours4', 'n_mates4', 'hp', 'low_ours',
          'cur_top', 'starts_next', 'obs_top']
ONLINE = ['team_changed']


def feats(D, online):
    lrb = D['p_lr']
    m, lr = D['m'], D['lr_rank']
    F = {
        'lr_before': lrb,
        'lr_gap': np.clip(lr - m + 1, 0, 4) * (1 - lrb),
        'lr_gap_after': np.clip(m - lr, 0, 4) * lrb,
        'm_frac': m / np.maximum(1, D['n']),
        'dclose': (D['dmin'] <= 2).astype(float),
        'n_ours4': np.minimum(D['n_ours4'], 4),
        'n_mates4': np.minimum(D['n_mates4'], 4),
        'hp': D['hp'],
        'low_ours': D['low_ours'],
        'cur_top': (D['cur_rank'] == 0).astype(float),
        'starts_next': D['starts_next'],
        'obs_top': (D['obs_rank'] == 0).astype(float),
        # an enemy team's priority changes per in-contact champion-round so far: prior 0.3 over 20
        'team_changed': smooth(D['st_changed'], D['st_contact'], 0.3, 20),
    }
    names = STATIC + (ONLINE if online else [])
    X = np.stack([F[k] for k in names], 1)
    X = np.concatenate([np.ones((len(X), 1)), X, X * lrb[:, None]], 1)
    return X


def main():
    paths = sys.argv[1:]
    sets = []
    for p in paths:
        D = derive(load(p))
        u = D['settled'] == 0
        D = {k: v[u] for k, v in D.items()}
        D['test'] = np.array([zlib.crc32(g.encode()) % 4 == 0 for g in D['game']])
        sets.append(D)
    for online in (False, True):
        Xs, ys, ws = [], [], []
        for D in sets[:2]:
            tr = ~D['test']
            X = feats(D, online)[tr]
            Xs.append(X)
            ys.append(D['y'][tr])
            ws.append(len(X))
        # equal weight per dataset: subsample the larger
        k = min(ws)
        rng = np.random.default_rng(1)
        Xl, yl = [], []
        for X, y in zip(Xs, ys):
            idx = rng.choice(len(X), k, replace=False) if len(X) > k else np.arange(len(X))
            Xl.append(X[idx])
            yl.append(y[idx])
        Xa, ya = np.concatenate(Xl), np.concatenate(yl)
        w = fit_logistic(Xa, ya)
        tag = 'online' if online else 'static'
        names = ['1'] + STATIC + (ONLINE if online else [])
        print(f'\n## {tag} weights (after: base terms; before: base + lr_before terms)')
        nf = len(names)
        print('constexpr float w_' + tag + '[2][%d] = {' % nf)
        print('    {' + ', '.join(f'{x:.4f}f' for x in w[:nf]) + '},')
        print('    {' + ', '.join(f'{x:.4f}f' for x in w[nf:]) + '},')
        print('};  // ' + ' '.join(names))
        for p, D in zip(paths, sets):
            for teams in ([None] + ([t for t in np.unique(D['team'])] if len(np.unique(D['team'])) <= 3 else [])):
                sel = D['test'] & ((D['team'] == teams) if teams is not None else True)
                y = D['y'][sel]
                pr = predict(feats(D, online), w)[sel]
                print(f'\n### {tag}: {p} {teams or "all"} test unsettled: {int(sel.sum())} rows, before {y.mean():.3f}')
                print('| predictor | Brier | log loss | accuracy | said after, was before | said before, was after |')
                print('|---|---|---|---|---|---|')
                for name, q in (('last read', D['p_lr'][sel]), ('worst case', D['p_wc'][sel]), ('model', pr)):
                    b, ll, a, uu, o = metrics(q, y)
                    print(f'| {name} | {b:.4f} | {ll:.3f} | {a:.3f} | {uu:.3f} | {o:.3f} |')
                print('reliability (bin, n, mean p, observed):')
                for a_, b_, n_, mp, oy in reliability(pr, y):
                    print(f'  [{a_:.2f},{b_:.2f}) {n_:8d} {mp:.3f} {oy:.3f}')
                # the kill-bid situation: last read says we precede, target low and close
                ks = sel & (D['p_lr'] == 0) & (D['hp'] < 0.3) & (D['dmin'] <= 2)
                if ks.sum() > 100:
                    print(f'kill-like (lr after, hp<0.3, within 2): n={int(ks.sum())} before={D["y"][ks].mean():.3f} '
                          f'model mean={predict(feats(D, online), w)[ks].mean():.3f}')


if __name__ == '__main__':
    main()
