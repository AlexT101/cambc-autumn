"""Per ready turn: what the best ward tile within 2 would add, at the tile the ward goes down from (or, without one, the
turn's end tile). python3 gain.py OUT.pkl CACHE_DIR... [--jobs N]"""
import sys, os, pickle, argparse
from multiprocessing import Pool
from mw import Game, pos, cheb


def one(path):
    try: g = Game(path)
    except Exception: return []
    out = []; ward = {}; camp_tiles = {c[1] for c in g.camps}
    gid = os.path.basename(path)[:16]
    for t in g.turns:
        st = t['start']; me = st['me']; cid = me['id']; r = t['round']
        if not me['alive']: continue
        w = ward.get(cid); ready = (r >= w[1] + 10) if w else True
        p = pos(me); placed = None; pw = None
        for a in t['actions']:
            if a['kind'] == 'Move': p = tuple(a['to'])
            if a['kind'] == 'Place ward' and placed is None: placed = tuple(a['to']); pw = p
        if ready:
            q0 = pw or p
            own = g.fov(q0); wv = g.fov(w[0], 6) if w else frozenset()
            team = set()
            for c2, (wt, _) in ward.items():
                if c2 != cid: team |= g.fov(wt, 6)
            alive_c = {(c['x'], c['y']) for c in (t.get('end') or st)['camps']}
            best = dict(all=0, bush=0, team=0, camp=0, nocur=0)
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    q = (q0[0] + dx, q0[1] + dy)
                    if not g.legal_ward(q): continue
                    fv = g.fov(q, 6); nw = fv - own - wv
                    best['all'] = max(best['all'], len(nw))
                    best['bush'] = max(best['bush'], sum(1 for x in nw if x in g.bushes))
                    best['team'] = max(best['team'], len(nw - team))
                    best['nocur'] = max(best['nocur'], len(fv - own))
                    if q in camp_tiles: best['camp'] = max(best['camp'], 2 if q not in alive_c else 1)
            # what the current ward still sees of where we are
            out.append(dict(g=gid, r=r, cid=cid, type=g.name(cid), placed=placed is not None, w_bush=placed in g.bushes if placed else None,
                            w_camp=placed in camp_tiles if placed else None, since_ready=r - (w[1] + 10 if w else 1),
                            cur_sees_me=bool(w) and q0 in wv, old_d=cheb(q0, w[0]) if w else 99, n_en=len(st['enemies']),
                            **{'g_' + k: v for k, v in best.items()}))
        if placed: ward[cid] = (placed, r)
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('out'); ap.add_argument('dirs', nargs='+'); ap.add_argument('--jobs', type=int, default=8)
    a = ap.parse_args()
    files = [os.path.join(d, f) for d in a.dirs for f in sorted(os.listdir(d)) if f.endswith('.json.gz')]
    R = []
    with Pool(a.jobs) as pool:
        for o in pool.imap_unordered(one, files, chunksize=2): R += o
    pickle.dump(R, open(a.out, 'wb')); print(len(files), len(R))
