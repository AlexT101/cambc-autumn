"""Ward tile choice: a conditional logit over the legal tiles within 2 of where the ward goes down.

    python3 tile.py CACHE_DIR... [--games N] [--jobs N]
"""
import sys, os, argparse, collections
import numpy as np
from multiprocessing import Pool
from scipy.optimize import minimize
from mw import Game, pos, cheb

FEAT = ['new', 'new_bush', 'bush', 'csize_log', 'camp_alive', 'camp_dead', 'camps_view', 'camps_new', 'd1', 'd2',
        'future', 'foe_dir', 'altar_view', 'en_bush_near', 'own_cluster', 'old_overlap']


def one(path):
    try: g = Game(path)
    except Exception: return []
    where = {}
    for t in g.turns:
        me = t['start']['me']
        if me['alive']: where[(me['id'], t['round'])] = pos(me)
    camp_tiles = {c[1] for c in g.camps}
    foe_c = np.mean(list(g.foe_spawn), axis=0); own_c = np.mean(list(g.own_spawn), axis=0)
    ax = foe_c - own_c; ax = ax / (np.linalg.norm(ax) or 1)
    out = []; ward = {}
    for t in g.turns:
        st = t['start']; me = st['me']; cid = me['id']; r = t['round']
        if not me['alive']: continue
        p = pos(me); placed = None; pw = None; blocked = set(); clean = True
        for a in t['actions']:
            if a['kind'] == 'Move' and placed is None: p = tuple(a['to'])
            if a['kind'] == 'Cast ability' and placed is None: clean = False
            if a['kind'] == 'Movement blocked' and placed is None: blocked.add(tuple(a['to']))
            if a['kind'] == 'Place ward' and placed is None: placed = tuple(a['to']); pw = p
        if placed is None: continue
        w = ward.get(cid); ward[cid] = (placed, r)
        if not clean or cheb(pw, placed) > 2: continue
        own = g.fov(pw); wv = g.fov(w[0], 6) if w else frozenset()
        alive_c = {(c['x'], c['y']) for c in (t.get('end') or st)['camps']}
        fut = [where.get((cid, r + k)) for k in range(1, 11)]; fut = [f for f in fut if f]
        en = [pos(e) for e in st['enemies']]
        rows = []; ch = -1
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                q = (pw[0] + dx, pw[1] + dy)
                if not g.legal_ward(q) or q in blocked: continue
                fv = g.fov(q, 6); nw = fv - own - wv
                cv = [c for c in camp_tiles if c in fv]
                f = dict(new=len(nw) / 10, new_bush=sum(1 for x in nw if x in g.bushes) / 10, bush=q in g.bushes,
                         csize_log=np.log1p(g.csize.get(g.bush_c.get(q), 0)) if q in g.bushes else 0,
                         camp_alive=q in camp_tiles and q in alive_c, camp_dead=q in camp_tiles and q not in alive_c,
                         camps_view=len(cv) / 5, camps_new=sum(1 for c in cv if c not in own) / 5,
                         d1=cheb(pw, q) == 1, d2=cheb(pw, q) == 2,
                         future=(sum(1 for f_ in fut if f_ in fv) / len(fut)) if fut else 0,
                         foe_dir=float(np.dot(np.array(q) - np.array(pw), ax)),
                         altar_view=sum(1 for a in g.altars if a in fv),
                         en_bush_near=0, own_cluster=q in g.bushes and g.bush_c.get(q) == g.bush_c.get(pw),
                         old_overlap=len(fv & wv) / 10)
                if q == placed: ch = len(rows)
                rows.append([float(f[k]) for k in FEAT])
        if ch >= 0 and len(rows) > 1:
            out.append((np.array(rows), ch, g.name(cid), placed in g.bushes))
    return out


def fit(data, feats):
    idx = [FEAT.index(f) for f in feats]
    X = [d[0][:, idx] for d in data]; y = [d[1] for d in data]

    def nll(b):
        s = 0; gr = np.zeros_like(b)
        for x, c in zip(X, y):
            u = x @ b; m = u.max(); e = np.exp(u - m); z = e.sum(); pr = e / z
            s -= u[c] - m - np.log(z); gr -= x[c] - pr @ x
        return s / len(X), gr / len(X)
    res = minimize(nll, np.zeros(len(idx)), jac=True, method='L-BFGS-B')
    b = res.x
    hit = np.mean([np.argmax(x @ b) == c for x, c in zip(X, y)])
    return b, res.fun, hit


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('dirs', nargs='+'); ap.add_argument('--games', type=int, default=120); ap.add_argument('--jobs', type=int, default=6)
    a = ap.parse_args()
    files = sorted(os.path.join(d, f) for d in a.dirs for f in os.listdir(d) if f.endswith('.json.gz'))[:a.games]
    D = []
    with Pool(a.jobs) as pool:
        for o in pool.imap_unordered(one, files): D += o
    tr = D[::2]; te = D[1::2]
    print(len(D), 'placements; random-tile hit', np.mean([1 / len(d[0]) for d in te]))
    for name, fs in [('new', ['new']), ('new+bush', ['new', 'new_bush', 'bush']), ('all', FEAT)]:
        b, l, h = fit(tr, fs)
        _, _, hte = fit(te, fs) if False else (None, None, np.mean([np.argmax(d[0][:, [FEAT.index(f) for f in fs]] @ b) == d[1] for d in te]))
        print(f'{name:10} train nll {l:.3f} hit {h:.3f} test hit {hte:.3f}')
        if name == 'all':
            for f, v in zip(fs, b): print(f'   {f:14} {v:+.3f}')
    # by bush/open ward
    b, _, _ = fit(tr, FEAT)
    for bb in (True, False):
        S = [d for d in te if d[3] == bb]
        print('test hit, ward on bush' if bb else 'test hit, open ward', len(S), np.mean([np.argmax(d[0] @ b) == d[1] for d in S]))
