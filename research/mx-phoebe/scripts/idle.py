"""Share of group-rounds (r<=RMAX) each group type spends alive and asleep (available, unworked), by side relative
to team A's view folded over both teams (own / mid / enemy), with the group's gems and gold.

    python3 idle.py EXTRACT_DIR [--rmax 600]
"""
import argparse, gzip, json
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

PRIMARY = ['Monolith', 'Golem', 'Elk', 'Wolf', 'Gem cluster', 'Gold cluster']


def gtype(types):
    for t in PRIMARY:
        if t in types:
            return t
    return '?'


def one(args):
    d, rmax = args
    d = Path(d)
    try:
        meta = json.loads((d / 'meta.json').read_text())
        mp = json.loads((d / meta['mapFile']).resolve().read_text())
        R = json.load(gzip.open(d / 'rounds.json.gz'))
    except Exception:
        return None
    G = {g['id']: g for g in mp['groups']}
    rows = defaultdict(list)
    for r in R['groups']:
        rows[r[1]].append(r)
    nR = min(rmax, len(R['round']))
    out = Counter()
    for g, rs in rows.items():
        if g not in G:
            continue
        rs.sort()
        t = gtype(G[g]['types'])
        side = G[g]['side']
        for j, r in enumerate(rs):
            r0 = r[0]
            if r0 > nR:
                break
            r1 = min(rs[j + 1][0] if j + 1 < len(rs) else nR + 1, nR + 1)
            span = r1 - r0
            st = 'asleep' if (r[2] == 1 and r[6] == 0) else 'awake' if r[2] == 1 else 'cleared' if r[2] == 2 else 'respawning'
            for team in (0, 1):
                rel = 'mid' if side == -1 else ('own' if side == team else 'enemy')
                out[(t, rel, st)] += span
                out[(t, rel, 'all')] += span
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dir')
    ap.add_argument('--rmax', type=int, default=600)
    a = ap.parse_args()
    dirs = [str(p.parent) for p in Path(a.dir).glob('*/meta.json')]
    tot = Counter()
    with ProcessPoolExecutor(16) as ex:
        for r in ex.map(one, [(x, a.rmax) for x in dirs], chunksize=8):
            if r:
                tot.update(r)
    print(f'r<={a.rmax}: % of group-rounds asleep / awake / cleared / respawning (own side; then mid)')
    for t in PRIMARY:
        for rel in ('own', 'mid'):
            n = tot[(t, rel, 'all')]
            if n:
                print(f"{t:12s} {rel:4s} " + ' '.join(f"{100 * tot[(t, rel, s)] / n:5.1f}" for s in ('asleep', 'awake', 'cleared', 'respawning')) + f"   group-rounds {n}")


if __name__ == '__main__':
    main()
