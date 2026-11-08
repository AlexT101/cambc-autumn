"""Per ready turn: which tile classes are in ward reach (other-cluster bush with new bush tiles, any other-cluster bush,
camp tile alive/dead, open) and what Mite did. python3 classes.py OUT.pkl CACHE_DIR... [--jobs N]"""
import sys, os, pickle, argparse
from multiprocessing import Pool
from mw import Game, pos, cheb


def one(path):
    try: g = Game(path)
    except Exception: return []
    camp_tiles = {c[1] for c in g.camps}; out = []; ward = {}; gid = os.path.basename(path)[:16]
    last_seen = {}; hp_prev = {}
    for t in g.turns:
        st = t['start']; me = st['me']; cid = me['id']; r = t['round']
        if not me['alive']: continue
        w = ward.get(cid); ready = (r >= w[1] + 10) if w else True
        p = pos(me); placed = None; pw = None; atk_camp = None; atk_champ = False; cast = False
        en_tiles = {pos(e) for e in st['enemies']}
        for a in t['actions']:
            k = a['kind']
            if k == 'Move' and placed is None: p = tuple(a['to'])
            if k == 'Place ward' and placed is None: placed = tuple(a['to']); pw = p
            if k == 'Attack':
                if tuple(a['to']) in camp_tiles: atk_camp = tuple(a['to'])
                else: atk_champ = True
            if k == 'Cast ability': cast = True
        end = t.get('end') or st
        if ready:
            q0 = pw or p; own = g.fov(q0); wv = g.fov(w[0], 6) if w else frozenset()
            alive_end = {(c['x'], c['y']) for c in end['camps']}
            alive_start = {(c['x'], c['y']) for c in st['camps']}
            mycl = g.bush_c.get(q0)
            cls = dict(bush_new=0, bush_any=0, camp_alive=0, camp_dead=0)
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    q = (q0[0] + dx, q0[1] + dy)
                    if not g.legal_ward(q): continue
                    if q in g.bushes and g.bush_c[q] != mycl:
                        cls['bush_any'] = 1
                        if q not in own and q not in wv: cls['bush_new'] = 1
                    if q in camp_tiles:
                        if q in alive_end: cls['camp_alive'] = 1
                        else: cls['camp_dead'] = 1
            wc = None
            if placed:
                wc = ('bush_own' if placed in g.bushes and g.bush_c[placed] == mycl else 'bush' if placed in g.bushes
                      else 'camp_alive' if placed in camp_tiles and placed in alive_end else 'camp_dead' if placed in camp_tiles else 'open')
            killed = len(alive_start - alive_end)
            out.append(dict(g=gid, r=r, cid=cid, type=g.name(cid), wc=wc, since_ready=r - (w[1] + 10 if w else 1),
                            atk_camp=atk_camp is not None, atk_champ=atk_champ, cast=cast, killed=killed,
                            n_en=len(st['enemies']), n_camps=len(alive_start), on_bush=q0 in g.bushes,
                            old_sees_me=bool(w) and q0 in wv, old_d=cheb(q0, w[0]) if w else 99,
                            hp=me['hp'] / me['maxHp'], gems=me['gems'], since_seen=r - last_seen.get(cid, -999),
                            hurt=me['hp'] < hp_prev.get(cid, me['hp']), on_spawn=q0 in g.own_spawn,
                            camp_in_view=sum(1 for c in camp_tiles if c in own), groups_cap=sum(1 for x in st['groups'] if x[2] in (0, 1)),
                            **cls))
        if placed: ward[cid] = (placed, r)
        if st['enemies']: last_seen[cid] = r
        hp_prev[cid] = me['hp']
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('out'); ap.add_argument('dirs', nargs='+'); ap.add_argument('--jobs', type=int, default=6)
    a = ap.parse_args()
    files = [os.path.join(d, f) for d in a.dirs for f in sorted(os.listdir(d)) if f.endswith('.json.gz')]
    R = []
    with Pool(a.jobs) as pool:
        for o in pool.imap_unordered(one, files, chunksize=2): R += o
    pickle.dump(R, open(a.out, 'wb')); print(len(files), len(R))
