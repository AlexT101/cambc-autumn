"""Camp supply use by phase: gem stock sitting idle (alive, asleep, full hp) by zone, respawning, empty.
py supply.py EXTRACT_DIR"""
import gzip, json, sys, os
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor

WIN = [(1, 100), (100, 200), (200, 300), (300, 500), (500, 800), (800, 2001)]


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def game(d):
    try:
        meta = json.loads((d / 'meta.json').read_text())
        R = json.load(gzip.open(d / 'rounds.json.gz'))
        mp = json.load(open(os.path.join(d, meta['mapFile'])))
    except Exception:
        return None
    n = len(R['round'])
    sp = [((s['minX'] + s['maxX']) / 2, (s['minY'] + s['maxY']) / 2) for s in mp['spawn']]
    gems = {}
    zone = {}
    fullhp = {}
    for g in mp['groups']:
        gems[g['id']] = g.get('gems', 0)
        t = g['tiles']
        c = (sum(x for x, _ in t) / len(t), sum(y for _, y in t) / len(t))
        d0, d1 = cheb(c, sp[0]), cheb(c, sp[1])
        s = d0 / max(1e-9, d0 + d1)
        z = 'A' if s < 0.4 else 'B' if s > 0.6 else 'M'
        hp = {'Wolf':1350,'Elk':2400,'Golem':5000,'Gem Cluster':120,'Gold Cluster':120,'Monolith':20000}
        H = sum(hp.get(t, 1000) for t in g['types'])
        cls = 'mono' if 'Monolith' in g['types'] else 'huge' if H > 8000 else 'clus' if all('Cluster' in t for t in g['types']) else 'beast'
        zone[g['id']] = z + ':' + cls
    # forward-fill group rows
    rows = defaultdict(list)
    for r in R['groups']:
        rows[r[1]].append(r)
    acc = defaultdict(float)  # (win, kind) -> gem-rounds
    for g, rs in rows.items():
        if g not in gems:
            continue
        full = rs[0][7]
        for k, r in enumerate(rs):
            start = r[0]
            end = rs[k + 1][0] if k + 1 < len(rs) else n + 1
            st, awake, hp = r[2], r[6], r[7]
            if st == 1 and awake == 0 and hp >= full:
                kind = 'idle' + zone[g]
            elif st == 1:
                kind = 'work'
            elif st == 2:
                kind = 'empty'
            elif st == 3:
                kind = 'resp'
            else:
                kind = 'unk'
            for wi, (a, b) in enumerate(WIN):
                lo, hi = max(a, start), min(b, end)
                if hi > lo:
                    acc[(wi, kind)] += (hi - lo) * gems[g]
    tot = sum(gems.values())
    return dict(acc), tot, n


def main():
    root = Path(sys.argv[1])
    dirs = [d for d in root.iterdir() if (d / 'meta.json').exists()]
    with ProcessPoolExecutor(32) as ex:
        res = [r for r in ex.map(game, dirs, chunksize=8) if r]
    print('games', len(res))
    kinds = ['idleM:clus','idleM:beast','idleM:huge','idleM:mono','idleA:clus','idleA:beast','idleA:huge','idleA:mono', 'work', 'empty', 'resp']
    print('window      ' + ' '.join(f'{k[4:]:>8}' for k in kinds), '(share of total gem stock-rounds, games alive in window)')
    for wi, (a, b) in enumerate(WIN):
        s = defaultdict(float); den = 0
        for acc, tot, n in res:
            if n < a:
                continue
            span = min(b, n + 1) - a
            den += tot * span
            for k in kinds:
                s[k] += acc.get((wi, k), 0)
        print(f'{a:4d}-{b:4d}  ' + ' '.join(f'{s[k]/max(1,den):8.3f}' for k in kinds))


if __name__ == '__main__':
    main()
