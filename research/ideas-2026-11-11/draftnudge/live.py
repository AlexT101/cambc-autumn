"""Observational read of our live scrims against Fish and Mite: within a (map, side) cell, did the teams we drafted
that sit closer to the opponent's preference win more?  win ~ version effect + cell effect + beta * score, where score
is the team's flat or conditional log-odds under the direction (nudge.py). Standard errors cluster on the map.
    py live.py WORK"""
import json, sys, collections, numpy as np
sys.argv = [sys.argv[0], 'x', sys.argv[1]]
import importlib.util, os
spec = importlib.util.spec_from_file_location('nudge', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nudge.py')); nudge = importlib.util.module_from_spec(spec); spec.loader.exec_module(nudge)
W = sys.argv[2]; nudge.W = W
D = json.load(open(f'{W}/directions.json'))
lf = {x['name'].replace('-', '_'): x for x in map(json.loads, open(nudge.LADDER_FEAT))}
G = [json.loads(l) for l in open('/home/ubuntu/cambc-autumn/research/ladder-scrims-2026-11-06/data/games.jsonl')]
G = [g for g in G if g.get('status') == 'finished' and g.get('our_picks') and g.get('opp_picks') and g['result'] in ('win', 'loss') and g['map'] in lf]
def score(name, g):
    p = len(g['our_picks']); db, dW = nudge.direction(D, name, p); z = nudge.zrow(lf[g['map']]['f'])[:nudge.KC]
    return sum(db[c] + (dW[c] @ z if dW is not None else 0) for c in (nudge.CH.index(x) for x in g['our_picks']))
def ols(X, y, cl):
    b, *_ = np.linalg.lstsq(X, y, rcond=None); r = y - X @ b; XtXi = np.linalg.pinv(X.T @ X); meat = np.zeros((X.shape[1],) * 2)
    for c in set(cl):
        i = cl == c; s = X[i].T @ r[i]; meat += np.outer(s, s)
    V = XtXi @ meat @ XtXi
    return b, np.sqrt(np.diag(V))
for tag, opp in (('Inte', 'Fish'), ('Mite', 'Mite')):
    gs = [g for g in G if g['opp_name'][:4] == tag]
    cells = collections.defaultdict(list)
    for g in gs: cells[(g['map'], g['side'])].append(g)
    multi = {k: v for k, v in cells.items() if len({tuple(sorted(g['our_picks'])) for g in v}) > 1}
    use = [g for v in multi.values() for g in v]
    print(f'\n== live scrims against {opp}: {len(gs)} games, {len(cells)} cells; {len(multi)} cells saw more than one of our teams ({len(use)} games) ==')
    y = np.array([float(g['result'] == 'win') for g in use]); vers = sorted({g['version'] for g in use}); ck = sorted(multi)
    ci = {k: i for i, k in enumerate(ck)}; cl = np.array([hash(g['map']) for g in use])
    F = np.zeros((len(use), len(vers) + len(ck)))
    for i, g in enumerate(use): F[i, vers.index(g['version'])] = 1; F[i, len(vers) + ci[(g['map'], g['side'])]] = 1
    # partial out version and cell effects
    def resid(v): b, *_ = np.linalg.lstsq(F, v, rcond=None); return v - F @ b
    ry = resid(y)
    for name in D:
        if (name[0] == 'F') != (opp == 'Fish'): pass
        s = np.array([score(name, g) for g in use]); rs = resid(s)
        b, se = ols(rs[:, None], ry, cl)
        print(f'  score {name} ({D[name]["team"][:5]} {D[name]["kind"]}): within-cell sd {rs.std():.2f} log-odds; beta {100 * b[0]:+.2f} ±{196 * se[0]:.2f} win points per unit of log-odds '
              f'(a one-sd move: {100 * b[0] * rs.std():+.2f} ±{196 * se[0] * rs.std():.2f} pts)')
    # per champion: our team holds c
    X = np.array([[float(c in g['our_picks']) for c in nudge.CH] for g in use]); RX = np.column_stack([resid(X[:, j]) for j in range(12)])
    keep = [j for j in range(12) if RX[:, j].std() > 0.03 and j != 3]
    b, se = ols(RX[:, keep], ry, cl)
    print('  per champion in our team (win points, others held fixed; ± 95%): ' + ', '.join(f'{nudge.CH[j]} {100 * b[i]:+.1f}±{196 * se[i]:.1f}' for i, j in sorted(enumerate(keep), key=lambda t: -b[t[0]])))
