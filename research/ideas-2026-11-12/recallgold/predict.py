"""How well can a bot predict an enemy's carried gold at a kept recall we cancel? (body side of our games)

    python3 predict.py EXTDIR

Features at the cancel: round, the victim's lifetime earned gold (hidden from bots; an upper bound for any earned
proxy), our own team's mean earned (readable: a symmetric proxy), rounds since the victim last stood on its spawn
(hidden), rounds since its last respawn (readable: liveness is public). Prints R^2 of carried gold on each.
"""
import sys, os, json, gzip, collections
from multiprocessing import Pool
import numpy as np


def one(d):
    try:
        meta = json.load(open(d + '/meta.json')); R = json.load(gzip.open(d + '/rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d + '/events.jsonl.gz', 'rt')]
    except Exception:
        return None
    names = [t['name'] for t in meta['teams']]; us = 0 if not names[0].startswith('rt-') else 1
    team = {c['id']: c['team'] for c in meta['champions']}
    ch = {c['id']: c for c in R['champions']}; rounds = R['round']; idx = {r: i for i, r in enumerate(rounds)}
    spawn = {0: set(), 1: set()}
    for a, c in ch.items(): spawn[team[a]].add((c['x'][0], c['y'][0]))
    for e in ev:
        if e['k'] == 'recall_end': spawn[team[e['a']]].add(tuple(e['to']))
        if e['k'] == 'respawn': spawn[team[e['a']]].add(tuple(e['at']))
    rows = []; prev = None
    ours = [a for a in ch if team[a] == us]
    for e in ev:
        if e['k'] == 'recall_cancel' and e.get('cause') in ('damage', 'stun') and e.get('left', 9) <= 3 and prev is not None \
                and prev['s'] == e['s'] and prev['k'] in ('attack', 'cast') and prev.get('a') in team \
                and team[prev['a']] == us and team[e['a']] != us:
            a = e['a']; i = idx.get(e['r'], idx.get(e['r'] - 1)); c = ch[a]
            last_sp = 0; last_resp = 0
            for j in range(i, -1, -1):
                if (c['x'][j], c['y'][j]) in spawn[team[a]] and c['alive'][j]: last_sp = rounds[j]; break
            for j in range(i, 0, -1):
                if c['alive'][j] and not c['alive'][j - 1]: last_resp = rounds[j]; break
            own_e = np.mean([ch[b]['earned'][i] for b in ours])
            items = sum(len(x) for x in [c['items'][i]]) if isinstance(c['items'][i], list) else 0
            rows.append((c['gold'][i], e['r'], c['earned'][i], own_e, e['r'] - last_sp, e['r'] - last_resp, e.get('gems', 0), c['earned'][i] - c['gold'][i], meta['champions'][a]['name'] if meta['champions'][a]['id']==a else ''))
        prev = e
    return rows


def r2(y, x):
    X = np.column_stack([np.ones_like(x), x]); b, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ b; return 1 - res.var() / y.var(), b


def main():
    root = sys.argv[1]
    dirs = [os.path.join(root, x) for x in os.listdir(root) if os.path.isfile(os.path.join(root, x, 'meta.json'))]
    with Pool(12) as pool: rows = [r for rs in pool.map(one, dirs, chunksize=8) if rs for r in rs]
    A = np.array([r[:8] for r in rows], dtype=float); y = A[:, 0]
    names = [r[8] for r in rows]
    print(f'{len(A)} body kept recalls cancelled by us; gold mean {y.mean():.1f} sd {y.std():.1f}')
    for k, name in [(1, 'round'), (2, 'victim earned (hidden)'), (3, 'our mean earned'), (4, 'rounds since on spawn (hidden)'),
                    (5, 'rounds since respawn'), (6, 'gems carried'), (7, 'spent = items+consumables (visible)')]:
        v, b = r2(y, A[:, k]); print(f'  {name:32s} R2={v:.3f}  gold ~ {b[0]:.1f} + {b[1]:.4f} x')
    v, b = r2(y, np.minimum(A[:, 4], 400)); print(f'  since spawn capped 400             R2={v:.3f}  gold ~ {b[0]:.1f} + {b[1]:.4f} x')
    # binned by our mean earned
    import collections as C
    by = C.defaultdict(list)
    for n_, g in zip(names, y): by[n_].append(g)
    for n_, g in sorted(by.items(), key=lambda t: -len(t[1])): print(f'  {n_:14s} n={len(g)} gold mean {np.mean(g):.0f} med {np.median(g):.0f}')
    for lo, hi in [(0, 1000), (1000, 2000), (2000, 3000), (3000, 99999)]:
        m = (A[:, 3] >= lo) & (A[:, 3] < hi); print(f'  our earned {lo}-{hi}: n={m.sum()} gold mean {y[m].mean():.0f} med {np.median(y[m]):.0f}')
    for lo, hi in [(0, 20), (20, 60), (60, 150), (150, 400), (400, 9999)]:
        m = (A[:, 4] >= lo) & (A[:, 4] < hi); print(f'  since spawn {lo}-{hi}: n={m.sum()} gold mean {y[m].mean():.0f} med {np.median(y[m]):.0f}')
    for lo, hi in [(0, 60), (60, 150), (150, 400), (400, 9999)]:
        m = (A[:, 5] >= lo) & (A[:, 5] < hi); print(f'  since respawn {lo}-{hi}: n={m.sum()} gold mean {y[m].mean():.0f} med {np.median(y[m]):.0f}')


if __name__ == '__main__': main()

