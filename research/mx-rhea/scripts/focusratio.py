"""Prism Focus ratio (max/min of the two Prisms, both alive) at rounds 100..600 and the winner's share of the
higher Focus. Usage: py focusratio.py DIR"""
import gzip, json, sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
MARKS = (100, 150, 200, 300, 400, 500, 600)

def game(d):
    d = Path(d)
    try:
        meta = json.loads((d/'meta.json').read_text())
        R = json.load(gzip.open(d/'rounds.json.gz'))
    except Exception:
        return None
    ps = [c for c in R['champions'] if next(m['name'] for m in meta['champions'] if m['id'] == c['id']) == 'Prism']
    if len(ps) != 2: return None
    w = meta['result']['winner']
    rix = {r: i for i, r in enumerate(R['round'])}
    out = []
    for m in MARKS:
        i = rix.get(m)
        if i is None or not (ps[0]['alive'][i] and ps[1]['alive'][i]): continue
        f = [p['foc'][i] for p in ps]
        hi = 0 if f[0] >= f[1] else 1
        out.append((m, max(f) / max(1, min(f)), ps[hi]['team'] == w))
    return out

def main():
    dirs = [p for p in Path(sys.argv[1]).iterdir() if (p/'meta.json').exists()]
    T = defaultdict(list)
    with ProcessPoolExecutor(24) as ex:
        for o in ex.map(game, dirs, chunksize=4):
            for m, r, wins in (o or []): T[m].append((r, wins))
    for m in MARKS:
        rows = T[m]
        if not rows: continue
        for lo, hi in ((1, 1.2), (1.2, 1.5), (1.5, 2), (2, 99)):
            s = [w for r, w in rows if lo <= r < hi]
            print(f'r{m} ratio {lo}-{hi}: {len(s):4d} games ({100*len(s)/len(rows):3.0f}%), higher-Focus team wins {100*sum(s)/max(1,len(s)):3.0f}%')

if __name__ == '__main__':
    main()
