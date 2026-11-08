"""Per-turn and per-ward rows for one bot's side, from actor caches (tools/fish/extract.mjs).

    python3 events.py OUT.pkl CACHE_DIR [CACHE_DIR...] [--jobs 8]

turn rows: every alive turn of every champion, with its ward state and context; ward rows are the turns that place.
hit rows: every Attack / Cast at an enemy champion's tile, with whether only the actor's ward saw the target.
"""
import sys, os, pickle, argparse, collections
from multiprocessing import Pool
from mw import Game, pos, cheb, TYPES, RANGED


def near(ps, p):
    return min((cheb(p, q) for q in ps), default=99)


def one(path):
    try:
        g = Game(path)
    except Exception as e:
        return [], [], []
    T, Wd, Hit = [], [], []
    ward = {}       # champion id -> (tile, round placed)
    last_seen = {}  # champion id -> last round it saw any enemy
    seen_prev = {}  # champion id -> enemy ids seen at its previous turn start
    died = {}       # champion id -> last round it was dead
    hp_prev = {}
    camp_tiles = [c[1] for c in g.camps]
    gid = os.path.basename(path)[:16]
    for t in g.turns:
        st = t['start']; me = st['me']; cid = me['id']; r = t['round']
        if not me['alive']:
            died[cid] = r; continue
        p0 = pos(me)
        own0 = g.fov(p0)
        w = ward.get(cid)
        wv = g.fov(w[0], 6) if w else frozenset()
        en = st['enemies']
        en_ids = {e['id'] for e in en}
        dmin = min((cheb(p0, pos(e)) for e in en), default=99)
        ward_only0 = [e for e in en if pos(e) not in own0]
        lost = bool(seen_prev.get(cid)) and not en
        lost_ids = seen_prev.get(cid, set()) - en_ids
        ready_at = (w[1] + 10) if w else 1
        # walk the actions
        p = p0; placed = None; order = None; moved_before = 0; moved_after = 0; blocked2 = []
        for i, a in enumerate(t['actions']):
            k = a['kind']
            if k == 'Move':
                if placed is None: moved_before += 1
                else: moved_after += 1
                p = tuple(a['to'])
            elif k == 'Movement blocked' and cheb(p, a['to']) == 2 and placed is None:
                blocked2.append(tuple(a['to']))
            elif k == 'Place ward' and placed is None:
                placed = tuple(a['to']); order = i; pw = p
            elif k in ('Attack', 'Cast ability') and a.get('before'):
                b = a['before']; bp = pos(b['me']); tgt = tuple(a['to'])
                tg = [e for e in b['enemies'] if pos(e) == tgt]
                if tg:
                    e = tg[0]
                    ownb = g.fov(bp)
                    wcur = ward.get(cid) if placed is None else (placed, r)
                    nxt = next((b2['before'] for b2 in t['actions'][i + 1:] if b2.get('before')), t.get('end'))
                    killed = nxt is not None and all(x['id'] != e['id'] for x in nxt['enemies']) and 'x' in nxt['me'] and pos(nxt['me']) == bp
                    Hit.append(dict(g=gid, r=r, cid=cid, type=g.name(cid), kind=k, slot=a.get('slot'), killed=killed,
                                    tgt=e['id'], thp=e['hp'], tmax=e['maxHp'], tbush=tgt in g.bushes,
                                    ward_only=tgt not in ownb, d=cheb(bp, tgt),
                                    ward_new=placed is not None, w_d=cheb(wcur[0], tgt) if wcur else 99))
        end = t.get('end') or st
        en_end = end['enemies']
        pe = pos(end['me']) if end['me'].get('alive') else p
        row = dict(g=gid, side=g.side, r=r, cid=cid, type=g.name(cid), hp=me['hp'] / me['maxHp'], gems=me['gems'],
                   chan=me['channelType'], ready=r >= ready_at, since_ready=r - ready_at, has_ward=w is not None,
                   n_en=len(en), dmin=dmin, n_ward_only=len(ward_only0), lost=lost, n_lost=len(lost_ids),
                   since_seen=r - last_seen.get(cid, -999), since_dead=r - died.get(cid, -999),
                   on_spawn=p0 in g.own_spawn, on_bush=p0 in g.bushes, near_bush=near(g.bushes, p0) if g.bushes else 99,
                   old_w_d=cheb(p0, w[0]) if w else 99, placed=placed is not None, n_moves=moved_before + moved_after,
                   blocked2=len(blocked2), n_allies=sum(1 for a in st['allies'] if cheb(p0, pos(a)) <= 4),
                   d_altar=near(g.altars, p0), d_camp=near(camp_tiles, p0), W=g.W, H=g.H)
        if placed is not None:
            ownp = g.fov(pw); nv = g.fov(placed, 6)
            new = nv - ownp - wv
            gain_end = [e for e in en_end if pos(e) not in g.fov(pe)]
            new_en = [e for e in en_end if e['id'] not in en_ids]
            # where it went next: direction of the rest of the turn and of the next turns is filled in post
            row.update(w=placed, pw=pw, wd=cheb(pw, placed), w_bush=placed in g.bushes,
                       w_csize=g.csize.get(g.bush_c.get(placed), 0), w_same_cluster=placed in g.bushes and g.bush_c.get(placed) == g.bush_c.get(pw),
                       order=order, moved_before=moved_before, moved_after=moved_after,
                       new_tiles=len(new), new_bush=sum(1 for x in new if x in g.bushes), nv=len(nv),
                       new_camps=sum(1 for c in camp_tiles if c in new), new_altars=sum(1 for a in g.altars if a in nv - ownp),
                       w_d_altar=near(g.altars, placed), w_d_camp=near(camp_tiles, placed),
                       w_d_foe_spawn=near(g.foe_spawn, placed), w_d_own_spawn=near(g.own_spawn, placed),
                       p_d_foe_spawn=near(g.foe_spawn, pw), p_d_own_spawn=near(g.own_spawn, pw),
                       en_end=len(en_end), new_en=len(new_en), new_en_ward_only=sum(1 for e in new_en if pos(e) not in g.fov(pe)),
                       prev_w=w[0] if w else None, gap=r - w[1] if w else None)
            # Fish's tile rule: the legal tile within 2 adding the most bush tiles unseen by own sight and current ward
            best = -1; ties = []; rank_new = []
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    q = (pw[0] + dx, pw[1] + dy)
                    if not g.legal_ward(q) or q in blocked2: continue
                    fv = g.fov(q, 6) - ownp - wv
                    s = sum(1 for x in fv if x in g.bushes)
                    rank_new.append((len(fv), q))
                    if s > best: best, ties = s, [q]
                    elif s == best: ties.append(q)
            row.update(fish_best=best, fish_hit=placed in ties, fish_ties=len(ties),
                       maxnew_hit=placed in [q for n, q in rank_new if n == max(rank_new)[0]] if rank_new else False,
                       n_legal=len(rank_new))
            ward[cid] = (placed, r)
            Wd.append(row)
        T.append(row)
        if en: last_seen[cid] = r
        seen_prev[cid] = en_ids
    return T, Wd, Hit


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('out'); ap.add_argument('dirs', nargs='+'); ap.add_argument('--jobs', type=int, default=8)
    a = ap.parse_args()
    files = [os.path.join(d, f) for d in a.dirs for f in sorted(os.listdir(d)) if f.endswith('.json.gz')]
    T, Wd, Hit = [], [], []
    with Pool(a.jobs) as pool:
        for t, w, h in pool.imap_unordered(one, files, chunksize=4):
            T += t; Wd += w; Hit += h
    pickle.dump(dict(turns=T, wards=Wd, hits=Hit), open(a.out, 'wb'))
    print(len(files), len(T), len(Wd), len(Hit))
