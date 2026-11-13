"""Kill rate by the victim's commitment: per enemy-body-round within 6 of one of the killer team's bodies (r<=RMAX),
state = camp (victim hit a camp or was hit by one within the last 3 rounds), hold (standing on a cleared group's tile
of a hold in progress), tribute (channelling), free. Kills = champion kills (not camp) in that state.

    python3 killctx.py EXTRACT_DIR [--rmax 800]
"""
import argparse, gzip, json
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def one(args):
    d, rmax = args
    d = Path(d)
    try:
        meta = json.loads((d / 'meta.json').read_text())
        mp = json.loads((d / meta['mapFile']).resolve().read_text())
        R = json.load(gzip.open(d / 'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
    except Exception:
        return None
    ch = R['champions']
    nR = min(len(R['round']), rmax)
    idx = {c['id']: i for i, c in enumerate(ch)}
    typ = {c['id']: c['name'] for c in meta['champions']}
    camp_group = {c['id']: c['group'] for c in mp['camps']}
    gtiles = defaultdict(set)
    for c in mp['camps']:
        gtiles[c['group']].add((c['x'], c['y']))
    campr = defaultdict(set)  # cid -> rounds in camp contact
    trib = defaultdict(set)
    holds = defaultdict(set)  # round -> set of (team, tile)
    open_hold = {}
    open_trib = {}
    for e in ev:
        k = e['k']
        r = e['r']
        if k in ('attack', 'cast') and 'camp' in e:
            campr[e['a']].add(r)
        elif k == 'camp_attack':
            campr[e['tgt']].add(r)
        elif k == 'tribute_start':
            open_trib[e['a']] = r
        elif k in ('tribute_end', 'tribute_cancel'):
            s = open_trib.pop(e['a'], None)
            if s is not None:
                trib[e['a']].update(range(s, r + 1))
        elif k == 'capture_hold':
            open_hold.setdefault(e['g'], (r, e['team']))
        elif k == 'capture' or k == 'group_respawn':
            h = open_hold.pop(e['g'], None)
            if h:
                for rr in range(h[0], r + 1):
                    for t in gtiles[e['g']]:
                        holds[rr].add((h[1], t))
    kills = []
    for e in ev:
        if e['k'] == 'death' and 'camp' not in e and e.get('by') in idx and e['r'] <= nR and not e.get('linked'):
            kills.append((e['r'], e['v'], e['by']))
    out = Counter()

    def state(cid, ix):
        r = ix + 1
        c = ch[idx[cid]]
        p = (c['x'][ix], c['y'][ix])
        if r in trib[cid]:
            return 'tribute'
        if (c['team'], p) in holds[r]:
            return 'hold'
        if any(rr in campr[cid] for rr in range(r - 3, r + 1)):
            return 'camp'
        return 'free'
    killset = {(r, v) for r, v, b in kills}
    for ix in range(nR):
        for c in ch:
            if not c['alive'][ix] or c['x'][ix] is None:
                continue
            p = (c['x'][ix], c['y'][ix])
            near = any(o['team'] != c['team'] and o['alive'][ix] and o['x'][ix] is not None and cheb(p, (o['x'][ix], o['y'][ix])) <= 6 for o in ch)
            if not near:
                continue
            tn = typ[c['id']]
            tn = 'C&I' if tn in ('Cassi', 'Issac') else tn
            s = state(c['id'], ix)
            out[('exp', s)] += 1
            out[('exp', s, tn)] += 1
    for r, v, b in kills:
        ix = r - 2  # state the round before death
        if ix < 0:
            continue
        s = state(v, ix)
        tn = typ[v]
        tn = 'C&I' if tn in ('Cassi', 'Issac') else tn
        out[('kill', s)] += 1
        out[('kill', s, tn)] += 1
        out[('killer', typ[b])] += 1
    # encounters
    deaths_by = defaultdict(list)
    for r, v, b in kills:
        deaths_by[v].append(r)
    last_near = {}
    for ix in range(nR):
        for c in ch:
            if not c['alive'][ix] or c['x'][ix] is None:
                continue
            p = (c['x'][ix], c['y'][ix])
            near = [o for o in ch if o['team'] != c['team'] and o['alive'][ix] and o['x'][ix] is not None and cheb(p, (o['x'][ix], o['y'][ix])) <= 6]
            if not near:
                continue
            cid = c['id']
            if ix - last_near.get(cid, -100) >= 10:
                s0 = state(cid, ix)
                r = ix + 1
                died = any(r <= dr <= r + 15 for dr in deaths_by[cid])
                killed = any(any(r <= dr <= r + 15 for dr in deaths_by[o['id']]) for o in near)
                out[('enc', s0)] += 1
                out[('enc_died', s0)] += died
                out[('enc_kill', s0)] += killed
            last_near[cid] = ix
    out['games'] += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dir')
    ap.add_argument('--rmax', type=int, default=800)
    a = ap.parse_args()
    dirs = [str(p.parent) for p in Path(a.dir).glob('*/meta.json')]
    tot = Counter()
    with ProcessPoolExecutor(16) as ex:
        for r in ex.map(one, [(x, a.rmax) for x in dirs], chunksize=8):
            if r:
                tot.update(r)
    g = tot['games']
    print(f"{g} games, r<={a.rmax}; exposure = body-rounds within 6 of an enemy, per game; kills per 1000 exposure")
    for s in ('free', 'camp', 'hold', 'tribute'):
        e = tot[('exp', s)]
        k = tot[('kill', s)]
        print(f"{s:8s} exposure {e / g:7.1f} kills {k / g:5.2f}  rate {1000 * k / max(e, 1):6.2f}")
    print('encounter starts by own state: n/game, died within 15 %, killed an enemy present %')
    for s in ('free', 'camp', 'hold', 'tribute'):
        n = tot[('enc', s)]
        print(f"{s:8s} {n / g:6.1f}  died {100 * tot[('enc_died', s)] / max(n, 1):5.1f}%  killed {100 * tot[('enc_kill', s)] / max(n, 1):5.1f}%")
    for tn in ('C&I', 'Prism', 'Vesper Vale', 'Willow', 'Ryth'):
        print(tn, ' '.join(f"{s}:{tot[('exp', s, tn)] / g:.0f}/{1000 * tot[('kill', s, tn)] / max(tot[('exp', s, tn)], 1):.1f}" for s in ('free', 'camp', 'hold', 'tribute')))


if __name__ == '__main__':
    main()
