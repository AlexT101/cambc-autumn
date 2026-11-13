"""At the round a team first reaches 1000 wealth: its tributed T, its Prism's bag B, the rest carried; and the
Prism's bag when the winning tribute completes. Winners only, Prism games.
    py excess.py ANALYSIS_DIR"""
import gzip, json, sys, statistics as st
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

def one(d):
    try:
        meta = json.loads((d / 'meta.json').read_text())
        R = json.load(gzip.open(d / 'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
    except Exception:
        return None
    w = meta['result']['winner']; n = len(R['round'])
    pr = [c for c in meta['champions'] if c['team'] == w and c['name'] == 'Prism']
    if not pr: return None
    pid = pr[0]['id']; C = R['champions']; pc = next(c for c in C if c['id'] == pid)
    for i in range(n):
        wl = R['gems'][w][i] + sum(c['gems'][i] for c in C if c['team'] == w and c['alive'][i])
        if wl >= 1000:
            first = i; break
    else:
        return None
    B = pc['gems'][first] if pc['alive'][first] else 0
    T = R['gems'][w][first]
    last = None
    for e in ev:
        if e['k'] == 'tribute_end' and e['a'] == pid: last = e
    fin = last['gems'] if last and last['r'] >= meta['result']['rounds'] - 1 else None
    # peak Prism bag between first and end
    peak = max((pc['gems'][i] for i in range(first, n) if pc['alive'][i]), default=0)
    return dict(T=T, B=B, need=1000 - T, fin=fin, peak=peak, wait=meta['result']['rounds'] - R['round'][first])

if __name__ == '__main__':
    root = Path(sys.argv[1])
    dirs = [p for p in root.iterdir() if (p / 'meta.json').exists()]
    with ProcessPoolExecutor(24) as ex:
        rows = [r for r in ex.map(one, dirs, chunksize=16) if r]
    q = lambda xs: (st.median(xs), [round(x) for x in st.quantiles(xs, n=4)])
    print('games', len(rows))
    print('T at 1000 wealth', q([r['T'] for r in rows]))
    print('Prism bag B then', q([r['B'] for r in rows]), ' need 1000-T', q([r['need'] for r in rows]))
    print('B >= need then:', sum(r['B'] >= r['need'] for r in rows))
    print('peak Prism bag after', q([r['peak'] for r in rows]))
    f = [r for r in rows if r['fin']]
    print('Prism ends the game with its tribute:', len(f), '; its bag then', q([r['fin'] for r in f]), '; need at first-1000', q([r['need'] for r in f]))
    print('excess (final Prism tribute - need at first 1000)', q([r['fin'] - r['need'] for r in f]))
    print('rounds first-1000 to end', q([r['wait'] for r in rows]))
