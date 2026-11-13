"""Pick mirror games with a Prism on both sides that were close at r200 (tributed + carried within 15%).
Usage: py tt_select.py ANALYSIS_DIR [N]"""
import gzip, json, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path


def game(d):
    d = Path(d)
    try:
        meta = json.loads((d/'meta.json').read_text())
        if not all(any(c['name'] == 'Prism' and c['team'] == t for c in meta['champions']) for t in (0, 1)):
            return None
        R = json.load(gzip.open(d/'rounds.json.gz'))
    except Exception:
        return None
    out = {}
    for m in (200, 300):
        if m not in R['round']: return None
        i = R['round'].index(m)
        w = [R['gems'][t][i] + sum(c['gems'][i] for c in R['champions'] if c['team'] == t) for t in (0, 1)]
        out[m] = w
    return d.name, meta['map']['name'], meta['result']['winner'], meta['result']['rounds'], out, [c['name'] for c in meta['champions'] if c['team'] == 0]


if __name__ == '__main__':
    root = Path(sys.argv[1]); n = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    dirs = [p for p in root.iterdir() if (p/'meta.json').exists()]
    rows = []
    with ProcessPoolExecutor(24) as ex:
        for o in ex.map(game, dirs, chunksize=8):
            if o: rows.append(o)
    close = []
    for d, mp, w, r, o, picks in rows:
        a, b = o[200]
        if max(a, b) == 0 or abs(a - b) / max(a, b) > 0.15: continue
        a3, b3 = o[300]
        close.append((abs(a3 - b3) / max(1, a3, b3), d, mp, w, r, o, picks))
    print(len(rows), 'prism-both games;', len(close), 'close at r200')
    close.sort()
    for x in close[:n]:
        print(f'{x[1]} {x[2]:40s} win {x[3]} rounds {x[4]} r200 {x[5][200]} r300 {x[5][300]} {x[6]}')
