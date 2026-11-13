"""Farm walk legs: between camp hits, how far champions walk, and whether swapping allies' targets saves walking.

    python3 legs.py EXTRACT_DIR [--rmax 400]
"""
import argparse, gzip, json, statistics
from collections import defaultdict
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
    champs = R['champions']
    nR = len(R['round'])
    camp_group = {c['id']: c['group'] for c in mp['camps']}
    gpos = defaultdict(list)
    for c in mp['camps']:
        gpos[c['group']].append((c['x'], c['y']))
    typ = {c['id']: c['name'] for c in meta['champions']}
    hits = defaultdict(dict)  # cid -> round -> group
    for e in ev:
        if e['k'] in ('attack', 'cast') and 'camp' in e and e['r'] <= rmax:
            hits[e['a']].setdefault(e['r'], camp_group.get(e['camp']))
    out = defaultdict(float)
    legs_by_team = {0: [], 1: []}
    for i, c in enumerate(champs):
        cid = c['id']
        h = hits[cid]
        last = None  # (round, group)
        rs = sorted(h)
        prev_r = 0
        for r in rs:
            g = h[r]
            s = prev_r + 1
            # leg from s to r (first hit at g)
            if r - s >= 1 and (last is None or last[1] != g):
                ok = True
                for ix in range(s - 1, r - 1):
                    if not c['alive'][ix]:
                        ok = False
                        break
                    if ix > s - 1 and cheb((c['x'][ix], c['y'][ix]), (c['x'][ix - 1], c['y'][ix - 1])) > 3:
                        ok = False
                        break
                if ok and s >= 2:
                    p = (c['x'][s - 2], c['y'][s - 2])
                    dist_t = min(cheb(p, q) for q in gpos[g])
                    legs_by_team[c['team']].append((s, r, p, g, cid, dist_t))
                    out['legs'] += 1
                    out['leg_rounds'] += r - s
                    out['leg_direct'] += dist_t
            last = (r, g)
            prev_r = r
    # swaps
    for t in (0, 1):
        L = sorted(legs_by_team[t])
        for a in range(len(L)):
            s1, r1, p1, g1, c1, d1 = L[a]
            for b in range(a + 1, len(L)):
                s2, r2, p2, g2, c2, d2 = L[b]
                if s2 - s1 > 2:
                    break
                if c1 == c2 or g1 == g2:
                    continue
                if typ[c1] in ('Willow',) or typ[c2] in ('Willow',):
                    continue
                x1 = min(cheb(p1, q) for q in gpos[g2])
                x2 = min(cheb(p2, q) for q in gpos[g1])
                save = (d1 + d2) - (x1 + x2)
                out['pairs'] += 1
                if save >= 4:
                    out['swap4'] += 1
                    out['swap4_save'] += save
                if save >= 8:
                    out['swap8'] += 1
    return dict(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dir')
    ap.add_argument('--rmax', type=int, default=400)
    a = ap.parse_args()
    dirs = [p.parent for p in Path(a.dir).glob('*/meta.json')]
    with ProcessPoolExecutor(16) as ex:
        rs = [r for r in ex.map(one, [(str(x), a.rmax) for x in dirs], chunksize=8) if r]
    tot = defaultdict(float)
    for r in rs:
        for k, v in r.items():
            tot[k] += v
    n = len(rs)
    print(f'{n} games, r<= {a.rmax}')
    for k, v in sorted(tot.items()):
        print(f'{k:14s} {v / n:10.2f} per game')
    print('mean leg rounds', tot['leg_rounds'] / tot['legs'], 'mean direct', tot['leg_direct'] / tot['legs'])


if __name__ == '__main__':
    main()
