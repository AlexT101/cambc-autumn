"""The winner's conversion (mirror): from first reaching 1000 wealth (t0) to the win, split into assembly (no single
bag wins yet: score + bag < 1000 for every body) and finishing (some bag wins); in finishing, the share of the
winning-bag holder's rounds spent channelling a tribute, walking, and other. py convert.py ANALYSIS_DIR"""
import gzip, json, sys, statistics as st
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
def one(d):
    try:
        meta = json.loads((d / 'meta.json').read_text()); R = json.load(gzip.open(d / 'rounds.json.gz'))
    except Exception: return None
    w = meta['result']['winner']
    if w not in (0, 1): return None
    C = [c for c in R['champions'] if c['team'] == w]; n = len(R['round'])
    wealth = lambda i: R['gems'][w][i] + sum(c['gems'][i] for c in C if c['alive'][i])
    t0 = next((i for i in range(n) if wealth(i) >= 1000), None)
    if t0 is None: return None
    t1 = next((i for i in range(t0, n) if any(c['alive'][i] and R['gems'][w][i] + c['gems'][i] >= 1000 for c in C)), n - 1)
    chan = walk = other = 0
    for i in range(t1, n - 1):
        hs = [c for c in C if c['alive'][i] and R['gems'][w][i] + c['gems'][i] >= 1000]
        if not hs: other += 1; continue
        c = max(hs, key=lambda c: c['gems'][i])
        if c['chan'][i] == 2: chan += 1
        elif i + 1 < n and (c['x'][i + 1], c['y'][i + 1]) != (c['x'][i], c['y'][i]): walk += 1
        else: other += 1
    return (t1 - t0, n - 1 - t1, chan, walk, other)
if __name__ == '__main__':
    dirs = [p for p in Path(sys.argv[1]).iterdir() if (p / 'meta.json').exists()]
    with ProcessPoolExecutor(24) as ex: rows = [r for r in ex.map(one, dirs, chunksize=8) if r]
    print('games', len(rows))
    for k, name in enumerate(['assembly rounds', 'finishing rounds']):
        v = [r[k] for r in rows]; print(name, 'median', st.median(v), 'mean', round(st.mean(v), 1), 'quartiles', st.quantiles(v, n=4))
    tot = sum(r[1] for r in rows) or 1
    print('finishing: holder channelling %.0f%%, walking %.0f%%, other (no holder alive / still) %.0f%%' % tuple(100 * sum(r[k] for r in rows) / tot for k in (2, 3, 4)))
    for t in (50, 100, 200, 400):
        print(f'finishing > {t}: {100*sum(r[1]>t for r in rows)/len(rows):.1f}% of games, {100*sum(r[1] for r in rows if r[1]>t)/tot:.0f}% of finishing rounds')
