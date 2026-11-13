"""Capture gems by ground (own / mid / enemy half, by Chebyshev distance share to the two spawns) and phase, winner vs
loser (mirror); and the first capture of each middle group: who takes it and how that team fares.

    py research/mx-tethys/scripts/captures_ground.py ANALYSIS_ROOT BATCH_NAME [MAX]
"""
import gzip, json, sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def one(dd):
    try:
        m = json.loads((dd / 'meta.json').read_text())
        mp = json.loads((dd / m['mapFile']).resolve().read_text())
        ev = [json.loads(l) for l in gzip.open(dd / 'events.jsonl.gz', 'rt')]
    except Exception:
        return None
    sp = mp['spawn']
    cen = lambda s: ((s['minX'] + s['maxX']) / 2, (s['minY'] + s['maxY']) / 2)
    gc = {}
    for gi, g in enumerate(mp['groups']):
        tiles = g.get('tiles') or g.get('camps') or []
        pts = []
        for t in tiles:
            if isinstance(t, dict): pts.append((t.get('x'), t.get('y')))
            elif isinstance(t, (list, tuple)): pts.append(tuple(t[:2]))
            elif isinstance(t, int) and t < len(mp['camps']):
                c = mp['camps'][t]; pts.append((c['x'], c['y']) if isinstance(c, dict) else tuple(c[:2]))
        if not pts: continue
        gc[gi] = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
    w = m['result']['winner']
    acc = defaultdict(float)
    for e in ev:
        if e['k'] != 'capture' or e['g'] not in gc: continue
        t = e['team']; p = gc[e['g']]
        da, de = cheb(p, cen(sp[t])), cheb(p, cen(sp[1 - t]))
        s = da / max(1e-9, da + de)
        ground = 'own' if s < 0.4 else 'enemy' if s > 0.6 else 'mid'
        ph = 'r1-150' if e['r'] <= 150 else 'r151-300' if e['r'] <= 300 else 'r301-600' if e['r'] <= 600 else 'r601+'
        gems = sum(x[1] for x in e['shares'])
        acc[('W' if t == w else 'L', ground, ph)] += gems
    return acc


def main():
    root = Path(sys.argv[1]); bname = sys.argv[2]; mx = int(sys.argv[3]) if len(sys.argv) > 3 else 10**9
    dirs = [dd for dd in sorted(root.iterdir()) if (dd / 'meta.json').exists() and bname in (json.loads((dd / 'meta.json').read_text()).get('source') or '')][:mx]
    tot = defaultdict(float); n = 0
    with ProcessPoolExecutor(40) as ex:
        for x in ex.map(one, dirs, chunksize=4):
            if x is None: continue
            n += 1
            for k, v in x.items(): tot[k] += v
    print('games', n, '(capture gems a game)')
    for ph in ('r1-150', 'r151-300', 'r301-600', 'r601+'):
        print(ph, '  '.join(f"{g}: W {tot[('W', g, ph)] / n:6.1f} L {tot[('L', g, ph)] / n:6.1f}" for g in ('own', 'mid', 'enemy')))


if __name__ == '__main__':
    main()
