"""Surprise hits in games with both sides decoded: was the attacker in the victim's sight at the end of the victim's
last turn before the hit (and in any of the victim's teammates')? Also who saw the victim through a ward at the hit.

    python3 surprise.py OUT.pkl SIDE1_DIR SIDE2_DIR [--jobs N]   (same replays, one cache dir per side)
"""
import sys, os, pickle, argparse, bisect
from multiprocessing import Pool
from mw import Game, pos, cheb


def views(g):
    """champion id -> sorted [(step, set of visible enemy ids at that turn's end, own tile, alive)]"""
    V = {}
    for t in g.turns:
        e = t.get('end') or t['start']; me = e['me']
        V.setdefault(t['id'], []).append((t['step'], {x['id'] for x in e['enemies']}, pos(me) if 'x' in me else None))
    return V


def one(args):
    fa, fb = args
    try: A, B = Game(fa), Game(fb)
    except Exception: return []
    out = []
    for atk, vic in ((A, B), (B, A)):
        V = views(vic); steps = {k: [s for s, _, _ in v] for k, v in V.items()}
        team = list(V)
        for t in atk.turns:
            me = t['start']['me']
            if not me['alive']: continue
            for i, a in enumerate(t['actions']):
                if a['kind'] not in ('Attack', 'Cast ability') or not a.get('before'): continue
                b = a['before']; tgt = tuple(a['to'])
                tg = [e for e in b['enemies'] if pos(e) == tgt]
                if not tg: continue
                e = tg[0]; vid = e['id']
                if vid not in V: continue
                j = bisect.bisect_left(steps[vid], a['step']) - 1
                seen_self = j >= 0 and me['id'] in V[vid][j][1]
                seen_team = seen_self
                for o in team:
                    if o == vid: continue
                    k = bisect.bisect_left(steps[o], a['step']) - 1
                    if k >= 0 and me['id'] in V[o][k][1]: seen_team = True
                nxt = next((b2['before'] for b2 in t['actions'][i + 1:] if b2.get('before')), t.get('end'))
                killed = nxt is not None and all(x['id'] != vid for x in nxt['enemies']) and 'x' in nxt['me'] and pos(nxt['me']) == pos(b['me'])
                ap = pos(b['me'])
                out.append(dict(g=os.path.basename(fa)[:16], atk_bot=atk.d['bot'], vic_bot=vic.d['bot'], r=t['round'],
                                atype=atk.name(me['id']), vtype=vic.name(vid), kind=a['kind'], seen_self=seen_self,
                                seen_team=seen_team, a_bush=ap in atk.bushes, v_bush=tgt in atk.bushes,
                                ward_only=tgt not in atk.fov(ap), d=cheb(ap, tgt), killed=killed, thp=e['hp'] / e['maxHp']))
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('out'); ap.add_argument('a'); ap.add_argument('b'); ap.add_argument('--jobs', type=int, default=8)
    a = ap.parse_args()
    common = sorted(set(os.listdir(a.a)) & set(os.listdir(a.b)))
    R = []
    with Pool(a.jobs) as pool:
        for o in pool.imap_unordered(one, [(os.path.join(a.a, f), os.path.join(a.b, f)) for f in common], chunksize=2): R += o
    pickle.dump(R, open(a.out, 'wb')); print(len(common), len(R))
