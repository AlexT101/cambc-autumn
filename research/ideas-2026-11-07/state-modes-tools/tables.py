"""Tables by gem-lead bin from collect.py output. usage: tables.py SET.json [SET.json...]"""
import json, sys, math
import numpy as np

BINS = [-10**9, -300, -150, -50, 50, 150, 300, 10**9]
LAB = ['<-300', '-300..-150', '-150..-50', '-50..50', '50..150', '150..300', '>300']


def b(x):
    for k in range(len(BINS) - 1):
        if BINS[k] <= x < BINS[k + 1]:
            return k


def cmean(rows):
    """rows: list of (game, value). Mean and game-clustered SE."""
    if not rows:
        return float('nan'), float('nan'), 0
    v = np.array([r[1] for r in rows], float)
    g = [r[0] for r in rows]
    m = v.mean()
    s = {}
    for gi, x in zip(g, v):
        s[gi] = s.get(gi, 0) + (x - m)
    se = math.sqrt(sum(x * x for x in s.values())) / len(v)
    return m, se, len(set(g))


def fmt(m, se):
    return f'{m:7.1f}±{1.96*se:5.1f}' if not math.isnan(m) else '      -      '


def ols_cluster(X, y, g):
    X = np.asarray(X, float); y = np.asarray(y, float)
    XtX = np.linalg.inv(X.T @ X)
    beta = XtX @ X.T @ y
    e = y - X @ beta
    meat = np.zeros((X.shape[1], X.shape[1]))
    gs = {}
    for i, gi in enumerate(g):
        gs.setdefault(gi, []).append(i)
    for idx in gs.values():
        u = X[idx].T @ e[idx]
        meat += np.outer(u, u)
    V = XtX @ meat @ XtX
    return beta, np.sqrt(np.diag(V))


for path in sys.argv[1:]:
    games = json.load(open(path))
    print(f'\n######## {path}: {len(games)} games, win {np.mean([g["win"] for g in games])*100:.1f}%')
    rows = {k: {} for k in ['dl', 'farm', 'kill', 'camp', 'resid', 'dus', 'dthem', 'bdus', 'bdthem', 'bag', 'bag_t', 'max', 'max_t',
                            'far', 'far_t', 'nn', 'nn_t', 'hp', 'hp_t', 'win']}
    reg = []
    for gi, G in enumerate(games):
        for s in G['samples']:
            if s['r'] < 50:
                continue
            k = b(s['lead'])
            add = lambda key, v: rows[key].setdefault(k, []).append((gi, v))
            add('win', 100 * G['win'])
            be = s['beh']
            if be[0]:
                add('bag', be[0]['bag']); add('max', be[0]['maxbag']); add('far', 100 * be[0]['far']); add('hp', 100 * be[0]['hp'])
                if be[0]['nn'] is not None: add('nn', be[0]['nn'])
            if be[1]:
                add('bag_t', be[1]['bag']); add('max_t', be[1]['maxbag']); add('far_t', 100 * be[1]['far']); add('hp_t', 100 * be[1]['hp'])
                if be[1]['nn'] is not None: add('nn_t', be[1]['nn'])
            if s['dl'] is None or not s['full']:
                continue
            d = s['dl'] - s['lead']
            fu, ft, tu, tt, cu, ct = s['src']
            add('dl', d); add('farm', fu - ft); add('kill', 2 * (tu - tt)); add('camp', ct - cu)
            add('resid', d - (fu - ft) - 2 * (tu - tt) - (ct - cu))
            add('dus', s['dth'][0]); add('dthem', s['dth'][1]); add('bdus', s['bagd'][0]); add('bdthem', s['bagd'][1])
            reg.append((gi, G['opp'], s['r'], s['lead'], s['gold'], d, s['dth'][0], s['dth'][1]))
    print('lead bin      ' + ' '.join(f'{l:>13}' for l in LAB))
    for key, name in [('win', 'P(win)%'), ('dl', 'dLead/100r'), ('farm', ' farm diff'), ('kill', ' kill bags x2'), ('camp', ' camp losses'),
                      ('resid', ' residual'), ('dus', 'our deaths'), ('dthem', 'their deaths'), ('bdus', 'our 20+bag d'),
                      ('bdthem', 'their 20+ d'), ('bag', 'our carried'), ('bag_t', 'their carried'), ('max', 'our max bag'),
                      ('max_t', 'their max bag'), ('far', 'our far half%'), ('far_t', 'their far%'), ('nn', 'our nn dist'),
                      ('nn_t', 'their nn dist'), ('hp', 'our hp%'), ('hp_t', 'their hp%')]:
        cells = []
        for k in range(len(LAB)):
            m, se, ng = cmean(rows[key].get(k, []))
            cells.append(fmt(m, se))
        print(f'{name:13} ' + ' '.join(cells))
    print('games/bin     ' + ' '.join(f'{cmean(rows["win"].get(k, []))[2]:>13}' for k in range(len(LAB))))
    # Momentum regressions: dLead(100) on lead and gold lead (per 100 gems / 500 gold), opponent fixed effects.
    opps = sorted(set(r[1] for r in reg))
    for label, cols in [('lead', [3]), ('gold', [4]), ('lead+gold', [3, 4])]:
        X, y, g = [], [], []
        for r in reg:
            row = [r[c] / (100 if c == 3 else 500) for c in cols] + [1.0 if r[1] == o else 0.0 for o in opps]
            X.append(row); y.append(r[5]); g.append(r[0])
        beta, se = ols_cluster(X, y, g)
        print(f'  dLead100 ~ {label:10}: ' + ', '.join(f'{["lead/100","gold/500"][c-3]} {beta[i]:+.1f}±{1.96*se[i]:.1f}' for i, c in enumerate(cols)))
    for label, col in [('our deaths', 6), ('their deaths', 7)]:
        X, y, g = [], [], []
        for r in reg:
            X.append([r[3] / 100, r[4] / 500] + [1.0 if r[1] == o else 0.0 for o in opps]); y.append(r[col]); g.append(r[0])
        beta, se = ols_cluster(X, y, g)
        print(f'  {label}/100r ~ lead+gold: lead/100 {beta[0]:+.3f}±{1.96*se[0]:.3f}, gold/500 {beta[1]:+.3f}±{1.96*se[1]:.3f}')
